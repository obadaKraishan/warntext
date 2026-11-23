"""Rebuild the text layer on one's own machine, from the record layer and FEMA's API.

The record layer is released everywhere (the Kaggle mirror holds it without text). Anyone can
rebuild the text from it: for every message whose text is not withheld, the message is read
again from OpenFEMA by its record id, parsed, checked against the privacy rules once more, and
written to ``text_federal`` or ``text_other`` by the sender kind in the record layer. A message
the privacy rules withhold is never read or written. A message whose text is already in the
folder given (a release's configuration folder holds its text tables) is reported as already in
the release and not read again. Messages are asked for a few at a time, one request after
another, through the polite client.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from warntext import cap, privacy
from warntext.probe import ENDPOINT, ENTITY
from warntext.tables import SCHEMAS, TEXT_TABLES, text_row, text_table_for

#: Record ids per request. Twenty ids keep the query string short.
BATCH = 20


@dataclass
class _First:
    record_id: str
    retrieved_at: str


@dataclass
class _Unit:
    message_id: str
    first: _First
    kind: str


def id_filter(ids: Iterable[str]) -> str:
    return " or ".join(f"id eq '{i}'" for i in ids)


def wanted(
    messages: Iterable[Mapping[str, Any]],
    kinds: set[str] | None,
    removals: Iterable[str] | None = None,
) -> list[dict]:
    """The messages whose text may be rebuilt: not withheld, not on the removal list (by
    default the tracked list), and of the kinds asked for."""
    removal_ids = privacy.load_removals() if removals is None else frozenset(removals)
    out = []
    for m in messages:
        if m["text_withheld"] or privacy.on_removal_list(m, removal_ids):
            continue
        if kinds is not None and m["sender_kind"] not in kinds:
            continue
        out.append(dict(m))
    return out


def released_ids(records_dir: Path | str) -> set[str]:
    """The messages whose text rows are already in the folder (a release's text tables)."""
    out: set[str] = set()
    for name in TEXT_TABLES:
        path = Path(records_dir) / f"{name}.parquet"
        if path.exists():
            out |= set(pq.read_table(path, columns=["message_id"]).column(0).to_pylist())
    return out


def plan(
    messages: Iterable[Mapping[str, Any]],
    kinds: set[str] | None,
    released: set[str],
    ids: set[str] | None = None,
    removals: Iterable[str] | None = None,
) -> dict[str, list[dict]]:
    """What a rebuild would do with each message: ``withheld``, ``already``, ``read``, ``other``.

    ``withheld``: the privacy rules withhold its text, or the removal list (by default the
    tracked list, read now, so an older release's records cannot bring a removed text back)
    names it, so it is never read. ``already``: its text is in the release. ``read``: it is read
    from FEMA. ``other``: a sender kind not asked for. With ``ids``, only those messages are
    planned.
    """
    removal_ids = privacy.load_removals() if removals is None else frozenset(removals)
    out: dict[str, list[dict]] = {"withheld": [], "already": [], "read": [], "other": []}
    for m in messages:
        if ids is not None and m["message_id"] not in ids:
            continue
        if m["text_withheld"] or privacy.on_removal_list(m, removal_ids):
            out["withheld"].append(dict(m))
        elif kinds is not None and m["sender_kind"] not in kinds:
            out["other"].append(dict(m))
        elif m["message_id"] in released:
            out["already"].append(dict(m))
        else:
            out["read"].append(dict(m))
    return out


def rebuild(
    client: Any, messages: list[Mapping[str, Any]], batch: int = BATCH
) -> tuple[dict[str, list[dict]], Counter]:
    """Fetch and parse each message; return the text rows by table and the counts."""
    out: dict[str, list[dict]] = {t: [] for t in TEXT_TABLES}
    stats: Counter = Counter()
    for start in range(0, len(messages), batch):
        chunk = messages[start : start + batch]
        params = {
            "$filter": id_filter(m["record_id"] for m in chunk),
            "$select": "id,sent,originalMessage",
            "$top": len(chunk),
        }
        resp = client.get(ENDPOINT, params)
        if resp.status != 200:
            raise RuntimeError(
                f"Asking for {len(chunk)} records answered HTTP {resp.status}. Nothing was "
                "written; run the command again later."
            )
        found = {r["id"]: r for r in resp.json()[ENTITY]}
        when = client.clock()
        for m in chunk:
            rec = found.get(m["record_id"])
            if rec is None:
                stats["not_found"] += 1
                continue
            try:
                parsed = cap.parse_record(rec)
            except cap.CapParseError:
                stats["unparsed"] += 1
                continue
            reason, _ = privacy.withheld(parsed)
            if reason is not None or privacy.about_missing_person(parsed):
                stats["withheld_now"] += 1
                continue
            unit = _Unit(m["message_id"], _First(m["record_id"], when), m["sender_kind"])
            table = text_table_for(m["sender_kind"])
            for k, info in enumerate(parsed.infos):
                out[table].append(text_row(unit, info, k))
            stats["rebuilt"] += 1
    return out, stats


def write(rows: Mapping[str, list[dict]], out_dir: Path | str) -> dict[str, int]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, table_rows in rows.items():
        table = pa.Table.from_pylist(table_rows, schema=SCHEMAS[name])
        pq.write_table(table, out_dir / f"{name}.parquet", compression="zstd")
        counts[name] = len(table_rows)
    return counts
