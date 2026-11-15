"""The release check: every rule the release depends on, tested on the built tables.

It fails, loudly, when:
- a year's count of archive records differs from the server's count for that year;
- a withheld message has text in any text table, or area shapes in the area table;
- a parameter that is not on the allow-list (or a value not in its allowed form) appears;
- a raw sender value appears: an address anywhere, or an account name in the record layer;
- a cell of the record layer matches a personal-detail pattern (the record layer holds no text,
  so such a match means text has leaked into it);
- a text table holds a message of the wrong sender kind, or a message that does not exist;
- an id is duplicated (messages, record ids, language blocks, areas, references, threads, text
  rows);
- a row lacks its source or its FEMA record id.

Failures name the table, the rule and the ids or counts involved, never a cell's text.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from warntext import patterns, privacy
from warntext.tables import CONFIGS, RECORD_TABLES, TEXT_TABLES

_EMAIL = patterns.PATTERNS["email"]


def load(tables_dir: Path | str) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Every table of every configuration, as lists of rows."""
    tables_dir = Path(tables_dir)
    out: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for c in CONFIGS:
        out[c] = {}
        for name in RECORD_TABLES + TEXT_TABLES:
            path = tables_dir / c / f"{name}.parquet"
            out[c][name] = pq.read_table(path).to_pylist() if path.exists() else []
    return out


def _dupes(keys: Iterable[Any]) -> list[Any]:
    return [k for k, n in Counter(keys).items() if n > 1]


def _cells(row: Mapping[str, Any]) -> Iterable[str]:
    for value in row.values():
        if isinstance(value, list):
            for v in value:
                if isinstance(v, str):
                    yield v
        elif isinstance(value, str):
            yield value


def check(
    tables: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    sender_values: Iterable[str],
    server_counts: Mapping[int, int] | None,
) -> list[str]:
    """Run every rule; return the failures (empty when the tables pass)."""
    fail: list[str] = []
    messages = [r for c in CONFIGS for r in tables[c]["messages"]]
    by_id = {r["message_id"]: r for r in messages}

    # Counts against the server, per year.
    if server_counts is not None:
        local: Counter = Counter()
        for r in messages:
            local[r["year"]] += r["archive_copies"]
        for year in sorted(set(server_counts) | {y for y in local if y is not None}):
            if local.get(year, 0) != server_counts.get(year, 0):
                fail.append(
                    f"counts: {year} has {local.get(year, 0):,} records in the tables and "
                    f"{server_counts.get(year, 0):,} on the server."
                )

    # Withheld messages have no text and no shapes.
    withheld = {r["message_id"] for r in messages if r["text_withheld"]}
    for c in CONFIGS:
        for name in TEXT_TABLES:
            bad = sorted({r["message_id"] for r in tables[c][name]} & withheld)
            if bad:
                fail.append(f"{c}/{name}: {len(bad)} withheld message(s) have text: {bad[:5]}")
        shaped = sorted(
            {
                r["message_id"]
                for r in tables[c]["areas"]
                if r["message_id"] in withheld and (r["polygons"] or r["circles"])
            }
        )
        if shaped:
            fail.append(f"{c}/areas: {len(shaped)} withheld message(s) keep shapes: {shaped[:5]}")

    # Parameters: allow-listed names, in their allowed form.
    for c in CONFIGS:
        names: Counter = Counter()
        for r in tables[c]["infos"]:
            for name, value in zip(r["parameter_names"], r["parameter_values"], strict=True):
                rule = privacy.ALLOWED_PARAMETERS.get(name)
                if rule is None:
                    names[name] += 1
                elif not rule.fullmatch(value):
                    names[f"{name} (unexpected value)"] += 1
        if names:
            fail.append(f"{c}/infos: parameters outside the allow-list: {dict(names)}")

    # Raw sender values. An address (with "@") may appear nowhere, not even inside a text. A
    # value with four letters or more (an account or user name) may appear nowhere in the
    # record layer, except in the station-code parameters, which some senders also use as
    # their sender value. Values of digits only are left out: some sending systems put the
    # message's own number in the sender field, so they equal its released identifier.
    addresses, named = sender_sets(sender_values)
    station = {"EAS-STN-ID", "EASHeader"}
    for c in CONFIGS:
        for name in RECORD_TABLES + TEXT_TABLES:
            record = name in RECORD_TABLES
            hits = 0
            for row in tables[c][name]:
                station_values = set()
                if name == "infos":
                    pairs = zip(row["parameter_names"], row["parameter_values"], strict=True)
                    station_values = {v.casefold() for n, v in pairs if n in station}
                for cell in _cells(row):
                    folded = cell.casefold()
                    bad = folded in addresses or any(
                        e.casefold() in addresses for e in _EMAIL.findall(cell)
                    )
                    if record and folded in named and folded not in station_values:
                        bad = True
                    hits += bad
            if hits:
                fail.append(f"{c}/{name}: {hits} cell(s) hold a raw sender value.")

    # The record layer holds no text: no cell may match a personal-detail pattern.
    for c in CONFIGS:
        for name in RECORD_TABLES:
            found: Counter = Counter()
            for row in tables[c][name]:
                for cell in _cells(row):
                    for pattern, hit in patterns.present(cell).items():
                        if hit:
                            found[pattern] += 1
            if found:
                fail.append(f"{c}/{name}: cells match personal-detail patterns: {dict(found)}")

    # Text tables: the right sender kind, and messages that exist.
    for c in CONFIGS:
        for name in TEXT_TABLES:
            wrong = missing = 0
            for r in tables[c][name]:
                m = by_id.get(r["message_id"])
                if m is None:
                    missing += 1
                    continue
                federal = m["sender_kind"] == "federal"
                if federal != (name == "text_federal") or r["sender_kind"] != m["sender_kind"]:
                    wrong += 1
            if wrong:
                fail.append(f"{c}/{name}: {wrong} row(s) of the wrong sender kind.")
            if missing:
                fail.append(f"{c}/{name}: {missing} row(s) for messages not in the tables.")

    # Duplicated ids.
    keys = {
        "messages.message_id": [r["message_id"] for r in messages],
        "messages.record_ids": [x for r in messages for x in r["record_ids"]],
        "infos": [(r["message_id"], r["info_index"]) for c in CONFIGS for r in tables[c]["infos"]],
        "areas": [
            (r["message_id"], r["info_index"], r["area_index"])
            for c in CONFIGS
            for r in tables[c]["areas"]
        ],
        "references": [
            (r["message_id"], r["ref_index"]) for c in CONFIGS for r in tables[c]["references"]
        ],
        "threads": [r["thread_id"] for c in CONFIGS for r in tables[c]["threads"]],
        "text rows": [
            (r["message_id"], r["info_index"])
            for c in CONFIGS
            for name in TEXT_TABLES
            for r in tables[c][name]
        ],
    }
    for what, values in keys.items():
        dupes = _dupes(values)
        if dupes:
            fail.append(f"{what}: {len(dupes)} duplicated id(s): {dupes[:5]}")

    # Source and record id on every row.
    for c in CONFIGS:
        for name in RECORD_TABLES + TEXT_TABLES:
            bad = sum(1 for r in tables[c][name] if not r.get("source") or not r.get("record_id"))
            if bad:
                fail.append(f"{c}/{name}: {bad} row(s) without a source or a record id.")
    return fail


def sender_sets(values: Iterable[str]) -> tuple[set[str], set[str]]:
    """Raw sender values split into addresses and names (four letters or more), case-folded."""
    addresses, named = set(), set()
    for v in values:
        if not v:
            continue
        folded = v.casefold()
        if "@" in folded:
            addresses.add(folded)
        elif sum(ch.isalpha() for ch in folded) >= 4:
            named.add(folded)
    return addresses, named


def read_sender_values(private_dir: Path | str) -> list[str]:
    path = Path(private_dir) / "sender_values.json"
    return [x["sender"] for x in json.loads(path.read_text(encoding="utf-8"))]
