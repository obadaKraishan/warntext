"""The release pack: the first release's files, built from the local tables, and its own check.

The first release holds, for both configurations (real alerts and tests):

- the record layer: ``messages``, ``infos``, ``areas``, ``references``, ``threads``;
- the released content codes (``codes``, real alerts only), without the experimental ones;
- the federal senders' text, ``text_federal``.

It never holds ``text_other`` (the other senders' text waits on the rights answer), the private
files, or anything raw. ``build_pack`` writes the files, a manifest (rows, bytes and SHA-256 per
file) and the dataset card; ``check_pack`` runs on the pack's own folder and fails, loudly, on a
file that should not be there, an experimental code, a file that does not match the manifest, a
card without its license fields, and everything the release check of the tables fails on.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from importlib import resources
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from warntext import __version__, durable
from warntext import check as ck
from warntext.probe import ENDPOINT
from warntext.tables import CONFIGS, RECORD_TABLES

#: The tables of the first release, in each configuration's folder.
RELEASED_TABLES = (*RECORD_TABLES, "text_federal")
#: Codes the codebook marks experimental (trust level C): left out of the release.
EXPERIMENTAL_CODES = (
    "hazard_description",
    "hazard_characteristics",
    "hazard_impacts",
    "time_impact",
    "time_action",
    "time_expiry",
    "loc_road",
    "loc_landmark",
    "loc_zone",
)
ALLOWED_FILES = {"README.md", "manifest.json"}
TERMS_URL = "https://www.fema.gov/about/openfema/terms-conditions"
CARD_TEMPLATE = "dataset_card.md"


def _mb(n: int) -> str:
    return f"{n / 1_000_000:.1f}"


def build_pack(
    tables_dir: Path | str,
    out_dir: Path | str,
    version: str,
    until: str,
    retrieved: str,
) -> dict[str, Any]:
    """Write the release files, the manifest and the card to ``out_dir`` (which must be new)."""
    tables_dir, out_dir = Path(tables_dir), Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} is not empty; a pack is built once into a new folder.")
    files = []
    for config in CONFIGS:
        (out_dir / config).mkdir(parents=True, exist_ok=True)
        for name in RELEASED_TABLES:
            src = tables_dir / config / f"{name}.parquet"
            if not src.exists():
                raise SystemExit(f"{src} is missing; run `warntext build` or `warntext update`.")
            table = pq.read_table(src)
            if name == "codes":
                if table.num_rows == 0:
                    continue  # tests carry no codes
                keep = [c for c in table.column_names if c not in EXPERIMENTAL_CODES]
                table = table.select(keep)
            dest = out_dir / config / f"{name}.parquet"
            pq.write_table(table, dest, compression="zstd")
            data = dest.read_bytes()
            files.append(
                {
                    "path": f"{config}/{name}.parquet",
                    "rows": table.num_rows,
                    "bytes": len(data),
                    "sha256": durable.sha256_bytes(data),
                }
            )
    manifest = {
        "name": "WarnText",
        "facts": pack_facts(out_dir),
        "version": version,
        "built_with": f"warntext {__version__}",
        "source": ENDPOINT,
        "records_sent_before": until,
        "retrieved": retrieved,
        "text_tables": ["text_federal"],
        "experimental_codes_left_out": list(EXPERIMENTAL_CODES),
        "files": files,
        "rows": sum(f["rows"] for f in files),
        "bytes": sum(f["bytes"] for f in files),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")
    (out_dir / "README.md").write_text(card(manifest), encoding="utf-8")
    return manifest


def pack_facts(pack_dir: Path) -> dict[str, int]:
    """Counts the card states: messages, authorities, what is withheld or rounded."""
    alerts = pq.read_table(
        pack_dir / "alerts" / "messages.parquet",
        columns=["message_id", "cog_id", "text_withheld", "times_rounded"],
    ).to_pylist()
    tests = pq.read_metadata(pack_dir / "tests" / "messages.parquet").num_rows
    federal = pq.read_table(pack_dir / "alerts" / "text_federal.parquet", columns=["message_id"])
    return {
        "real_alerts": len(alerts),
        "tests": tests,
        "authorities_with_real_alerts": len({r["cog_id"] for r in alerts}),
        "withheld": sum(1 for r in alerts if r["text_withheld"]),
        "withheld_people_code": sum(1 for r in alerts if r["text_withheld"] == "people_code"),
        "rounded": sum(1 for r in alerts if r["times_rounded"]),
        "federal_text_alerts": len(set(federal.column("message_id").to_pylist())),
    }


def card(manifest: Mapping[str, Any]) -> str:
    """The dataset card: the tracked template with the pack's measured sizes filled in."""
    template = resources.files("warntext").joinpath(CARD_TEMPLATE).read_text(encoding="utf-8")
    by = {f["path"]: f for f in manifest["files"]}
    values = {
        "version": manifest["version"],
        "until": manifest["records_sent_before"][:10],
        "retrieved": manifest["retrieved"],
        "total_rows": f"{manifest['rows']:,}",
        "total_mb": _mb(manifest["bytes"]),
        "terms_url": TERMS_URL,
    }
    for key, n in manifest.get("facts", {}).items():
        values[key] = f"{n:,}"
    for path, f in by.items():
        key = path.replace("/", "_").replace(".parquet", "")
        values[f"{key}_rows"] = f"{f['rows']:,}"
        values[f"{key}_mb"] = _mb(f["bytes"])
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), template)


def card_metadata_problems(text: str) -> list[str]:
    """What the card's YAML header lacks for Hugging Face (license fields, configs)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["the card has no YAML header"]
    head = m.group(1)
    out = []
    if not re.search(r"^license: other$", head, re.M):
        out.append("license must be 'other' (the data are under OpenFEMA's terms)")
    if not re.search(r"^license_name: \S+", head, re.M):
        out.append("license_name is missing")
    if f"license_link: {TERMS_URL}" not in head:
        out.append(f"license_link must be {TERMS_URL}")
    if "{{" in text:
        out.append("the card still holds a placeholder")
    for name in RELEASED_TABLES:
        if f"config_name: {name}" not in head:
            out.append(f"no config for {name}")
    return out


def check_pack(
    pack_dir: Path | str,
    sender_values: list[str],
    identifiers: list[str],
    server_counts: Mapping[int, int] | None,
) -> list[str]:
    """Every rule the pack must pass; returns the failures (empty when it passes)."""
    pack_dir = Path(pack_dir)
    fail: list[str] = []
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"{manifest_path} is missing; build the pack with `warntext release build`."]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    listed = {f["path"]: f for f in manifest["files"]}
    for path in sorted(p for p in pack_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(pack_dir).as_posix()
        if rel in ALLOWED_FILES:
            continue
        parts = rel.split("/")
        name = parts[-1].removesuffix(".parquet")
        if name.startswith("text_") and name != "text_federal":
            fail.append(f"{rel}: a text table other than text_federal may not be released.")
        elif len(parts) != 2 or parts[0] not in CONFIGS or name not in RELEASED_TABLES:
            fail.append(f"{rel}: not a file of the release; remove it.")
        elif rel not in listed:
            fail.append(f"{rel}: not in the manifest.")
        else:
            data = path.read_bytes()
            if durable.sha256_bytes(data) != listed[rel]["sha256"]:
                fail.append(f"{rel}: does not match its SHA-256 in the manifest.")
            if pq.read_metadata(path).num_rows != listed[rel]["rows"]:
                fail.append(f"{rel}: its row count differs from the manifest's.")
    for rel in listed:
        if not (pack_dir / rel).exists():
            fail.append(f"{rel}: in the manifest but missing.")
    codes = pack_dir / "alerts" / "codes.parquet"
    if codes.exists():
        left = sorted(set(pq.read_schema(codes).names) & set(EXPERIMENTAL_CODES))
        if left:
            fail.append(f"alerts/codes.parquet: experimental codes are in it: {left}.")
    readme = pack_dir / "README.md"
    if not readme.exists():
        fail.append("README.md (the dataset card) is missing.")
    else:
        fail += [f"README.md: {p}" for p in card_metadata_problems(readme.read_text("utf-8"))]
    # The tables' release check, on the released tables only (anything else is flagged above).
    loaded: dict[str, dict[str, list]] = {}
    for config in CONFIGS:
        loaded[config] = {"text_other": []}
        for name in RELEASED_TABLES:
            path = pack_dir / config / f"{name}.parquet"
            loaded[config][name] = pq.read_table(path).to_pylist() if path.exists() else []
    fail += ck.check(loaded, sender_values, server_counts, identifiers)
    return fail
