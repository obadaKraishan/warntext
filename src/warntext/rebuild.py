"""Rebuild the text layer on one's own machine, from the record layer and FEMA's API.

The record layer is released everywhere; some of the text layer may not be. Anyone can rebuild
the text from the record layer: for every message whose text is not withheld, the message is
read again from OpenFEMA by its record id, parsed, checked against the privacy rules once more,
and written to ``text_federal`` or ``text_other`` by the sender kind in the record layer.
Messages are asked for a few at a time, one request after another, through the polite client.
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


def wanted(messages: Iterable[Mapping[str, Any]], kinds: set[str] | None) -> list[dict]:
    """The messages whose text may be rebuilt: not withheld, and of the kinds asked for."""
    out = []
    for m in messages:
        if m["text_withheld"]:
            continue
        if kinds is not None and m["sender_kind"] not in kinds:
            continue
        out.append(dict(m))
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
