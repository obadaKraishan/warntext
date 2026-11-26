"""A removal applied to a version already built, and the proof that only the removed text changed.

When a removal request concerns a person, the dataset is deleted and created again, holding the
tagged releases and the latest weekly version, each rebuilt with the removal applied. A version
is "rebuilt" here from its own files, not from the raw pages: the code that built it may have
changed since, and only its own files say exactly what it held. ``apply`` does to a built version
exactly what the build does to a message on the removal list:

- its text rows leave ``text_federal`` and ``text_other``;
- in ``messages``, ``text_withheld`` becomes ``removed_on_request`` where no other reason applied,
  and ``shapes_withheld`` is set where it has shapes;
- in ``areas``, its polygons and circles are left out (``shapes_withheld`` set where it had any);
- every other table and row is untouched (a file with no listed message is copied byte for byte);
- the easy-access layer, the manifest's facts and the card are derived again from the new files.

``proof`` sets the new version against the old one: every file the same by SHA-256, or, where it
holds a listed message's rows, every other row the same (by a hash of the row) and the listed
rows changed only in those fields. It returns counts, paths and field names, never a cell.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from warntext import access, durable, privacy
from warntext.tables import CONFIGS, TEXT_TABLES

#: The fields a removal may change, by table (text tables lose the rows instead).
MAY_CHANGE = {
    "messages": {"text_withheld", "shapes_withheld"},
    "areas": {"polygons", "circles", "shapes_withheld"},
}


def _row_hash(row: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()


def listed_messages(pack_dir: Path, removals: Iterable[str]) -> set[str]:
    """The message ids of a version that the removal list names (by any archive copy's id)."""
    ids = frozenset(removals)
    out: set[str] = set()
    for config in CONFIGS:
        path = Path(pack_dir) / config / "messages.parquet"
        for m in pq.read_table(path, columns=["message_id", "record_ids"]).to_pylist():
            if privacy.on_removal_list(m, ids):
                out.add(m["message_id"])
    return out


def _apply_table(name: str, table: pa.Table, newly: set[str], listed: set[str]) -> pa.Table:
    rows = table.to_pylist()
    if name in TEXT_TABLES:
        rows = [r for r in rows if r["message_id"] not in listed]
    elif name == "messages":
        for r in rows:
            if r["message_id"] in newly:
                r["text_withheld"] = privacy.REMOVED
                r["shapes_withheld"] = (r["n_polygons"] or 0) + (r["n_circles"] or 0) > 0
    elif name == "areas":
        for r in rows:
            if r["message_id"] in newly:
                r["shapes_withheld"] = bool(r["polygons"] or r["circles"])
                r["polygons"], r["circles"] = None, None
    return pa.Table.from_pylist(rows, schema=table.schema)


def apply(
    pack_dir: Path | str,
    out_dir: Path | str,
    removals: Iterable[str],
    recreated: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``pack_dir``'s version with the removal list applied to ``out_dir`` (a new folder).

    ``recreated`` (``{"date": ..., "versions": [...]}``) is recorded in the manifest, and the card
    of a version from 0.2.0 says the dataset was created again on that date."""
    from warntext import release

    pack_dir, out_dir = Path(pack_dir), Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} is not empty; a version is rebuilt once into a new folder.")
    removals = frozenset(removals)
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    listed = listed_messages(pack_dir, removals)
    newly: set[str] = set()
    for config in CONFIGS:
        rows = pq.read_table(
            pack_dir / config / "messages.parquet", columns=["message_id", "text_withheld"]
        )
        newly |= {
            r["message_id"]
            for r in rows.to_pylist()
            if r["message_id"] in listed and not r["text_withheld"]
        }
    files = []
    for f in manifest["files"]:
        src, dest = pack_dir / f["path"], out_dir / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        name = f["path"].split("/")[1].removesuffix(".parquet")
        ids = (
            set(pq.read_table(src, columns=["message_id"]).column(0).to_pylist())
            if name != "threads"
            else set()
        )
        if ids & listed and (name in TEXT_TABLES or (name in MAY_CHANGE and ids & newly)):
            table = _apply_table(name, pq.read_table(src), newly, listed)
            pq.write_table(table, dest, compression="zstd")
            rows = table.num_rows
        else:
            shutil.copyfile(src, dest)
            rows = f["rows"]
        data = dest.read_bytes()
        files.append(
            {
                "path": f["path"],
                "rows": rows,
                "bytes": len(data),
                "sha256": durable.sha256_bytes(data),
            }
        )
    new = {k: v for k, v in manifest.items() if k not in ("access_files", "access")}
    new["files"] = files
    new["rows"] = sum(f["rows"] for f in files)
    new["bytes"] = sum(f["bytes"] for f in files)
    new["facts"] = release.pack_facts(out_dir, manifest["text_tables"], manifest["text_kinds"])
    new["removal_list_applied"] = {
        "entries": len(removals),
        "messages_listed": len(listed),
        "newly_withheld": len(newly),
    }
    if recreated:
        new["recreated"] = [*manifest.get("recreated", []), dict(recreated)]
    if manifest.get("access_files"):
        new["access_files"], new["access"] = access.build(out_dir, new)
    keys = list(manifest)  # the old manifest's order, then anything new
    ordered = {k: new[k] for k in keys if k in new}
    ordered.update({k: v for k, v in new.items() if k not in ordered})
    (out_dir / "manifest.json").write_text(json.dumps(ordered, indent=1) + "\n", "utf-8")
    (out_dir / "README.md").write_text(release.card(ordered), encoding="utf-8")
    return ordered


def _key(name: str, row: Mapping[str, Any]) -> tuple:
    for keys in (
        ("message_id", "info_index", "area_index"),
        ("message_id", "ref_index"),
        ("message_id", "info_index", "unit"),
        ("message_id", "info_index"),
        ("thread_id",),
        ("message_id",),
    ):
        if all(k in row for k in keys):
            return tuple(row[k] for k in keys)
    raise ValueError(name)


def proof(old_dir: Path | str, new_dir: Path | str, removals: Iterable[str]) -> dict[str, Any]:
    """Whether only the removed text changed between two builds of one version (counts only)."""
    old_dir, new_dir = Path(old_dir), Path(new_dir)
    old = json.loads((old_dir / "manifest.json").read_text(encoding="utf-8"))
    new = json.loads((new_dir / "manifest.json").read_text(encoding="utf-8"))
    removals = frozenset(removals)
    listed = listed_messages(old_dir, removals)
    problems: list[str] = []
    out: dict[str, Any] = {"version": old["version"], "messages_listed": len(listed), "files": []}
    for k in ("version", "codebook_version", "records_sent_before", "text_tables", "text_kinds"):
        if old.get(k) != new.get(k):
            problems.append(f"manifest.json: {k} differs ({old.get(k)!r} -> {new.get(k)!r}).")
    if [f["path"] for f in old["files"]] != [f["path"] for f in new["files"]]:
        problems.append("manifest.json: the two versions list different Parquet files.")
    by_new = {f["path"]: f for f in new["files"]}
    for f in old["files"]:
        g = by_new.get(f["path"])
        if g is None:
            continue
        entry = {
            "path": f["path"],
            "same_hash": f["sha256"] == g["sha256"],
            "rows_left_out": 0,
            "rows_changed": 0,
            "fields_changed": [],
        }
        if not entry["same_hash"]:
            name = f["path"].split("/")[1].removesuffix(".parquet")
            a = pq.read_table(old_dir / f["path"]).to_pylist()
            b = pq.read_table(new_dir / f["path"]).to_pylist()
            keep_a = [r for r in a if r.get("message_id") not in listed]
            keep_b = [r for r in b if r.get("message_id") not in listed]
            if [_row_hash(r) for r in keep_a] != [_row_hash(r) for r in keep_b]:
                problems.append(f"{f['path']}: a row of a message not on the list differs.")
            gone_a = {_key(name, r): r for r in a if r.get("message_id") in listed}
            gone_b = {_key(name, r): r for r in b if r.get("message_id") in listed}
            if name in TEXT_TABLES:
                entry["rows_left_out"] = len(gone_a) - len(gone_b)
                if gone_b:
                    problems.append(
                        f"{f['path']}: {len(gone_b)} text row(s) of a listed message are still "
                        "in it."
                    )
            elif name in MAY_CHANGE:
                if set(gone_a) != set(gone_b):
                    problems.append(
                        f"{f['path']}: the listed messages' rows are not the same rows."
                    )
                changed: set[str] = set()
                for key, r in gone_a.items():
                    s = gone_b.get(key, {})
                    diff = {c for c in r if r[c] != s.get(c)}
                    if diff:
                        entry["rows_changed"] += 1
                        changed |= diff
                entry["fields_changed"] = sorted(changed)
                other = sorted(changed - MAY_CHANGE[name])
                if other:
                    problems.append(f"{f['path']}: fields a removal never changes differ: {other}.")
            else:
                problems.append(f"{f['path']}: changed, but a removal never changes this table.")
        out["files"].append(entry)
    out["parquet_same_by_hash"] = sum(1 for e in out["files"] if e["same_hash"])
    out["parquet_changed"] = sum(1 for e in out["files"] if not e["same_hash"])
    out["text_rows_left_out"] = sum(e["rows_left_out"] for e in out["files"])
    layer = _layer_proof(old, new, old_dir, new_dir, listed)
    out["access_files"] = layer["files"]
    problems += layer["problems"]
    out["card_lines_changed"] = _lines_changed(old_dir / "README.md", new_dir / "README.md")
    out["problems"] = problems
    out["proved"] = not problems
    return out


def _layer_proof(
    old: Mapping[str, Any], new: Mapping[str, Any], old_dir: Path, new_dir: Path, listed: set[str]
) -> dict[str, Any]:
    """The easy-access files: the catalogues the same by hash, every CSV the same except the rows
    of listed messages (the release check holds each to its Parquet table and the workbook to
    the start-here CSV)."""
    files, problems = [], []
    a = {f["path"]: f for f in old.get("access_files") or []}
    b = {f["path"]: f for f in new.get("access_files") or []}
    if list(a) != list(b):
        problems.append("manifest.json: the two versions list different easy-access files.")
    for path, f in a.items():
        g = b.get(path)
        if g is None:
            continue
        entry = {"path": path, "same_hash": f["sha256"] == g["sha256"], "rows_differ": 0}
        if not entry["same_hash"] and path.endswith((".csv", ".csv.gz")):
            ra, rb = list(access.read_csv(old_dir / path)), list(access.read_csv(new_dir / path))
            if ra[:1] != rb[:1]:
                problems.append(f"{path}: its header differs.")
            elif "message_id" not in ra[0]:
                problems.append(f"{path}: changed, but it holds no message's rows.")
            else:
                at = ra[0].index("message_id")
                keep_a = [r for r in ra[1:] if r[at] not in listed]
                keep_b = [r for r in rb[1:] if r[at] not in listed]
                if keep_a != keep_b:
                    problems.append(f"{path}: a row of a message not on the list differs.")
                entry["rows_differ"] = (len(ra) - len(keep_a)) - 1
        elif not entry["same_hash"] and path in (access.FIELDS_FILE, access.CODEBOOK_FILE):
            problems.append(f"{path}: changed, but a removal never changes it.")
        files.append(entry)
    return {"files": files, "problems": problems}


def _lines_changed(a: Path, b: Path) -> int:
    import difflib

    x = a.read_text(encoding="utf-8").splitlines()
    y = b.read_text(encoding="utf-8").splitlines()
    return sum(
        1
        for line in difflib.unified_diff(x, y, lineterm="", n=0)
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    )
