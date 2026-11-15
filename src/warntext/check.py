"""The release check: every rule the release depends on, tested on the built tables.

It fails, loudly, when:
- a year's count of archive records differs from the server's count for that year;
- a withheld message has text in any text table, or area shapes in the area table;
- a parameter that is not on the allow-list (or a value not in its allowed form) appears;
- a raw sender value appears: an address anywhere, or an account name in the record layer;
- a raw CAP identifier appears anywhere, as a cell or inside one (rows are keyed by FEMA's
  record ids instead);
- a message with a people code (or a reference or thread that touches one) carries a time
  finer than the hour, in a time field or in its EAS header;
- a message about a missing person (or a reference or thread that touches one) carries a time
  finer than the hour;
- a message with a people code or about a missing person carries a part-of-county digit in an
  area code (SAME or FIPS6, in `messages`, `areas` or its EAS header);
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
import re
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from warntext import patterns, privacy
from warntext.tables import CONFIGS, RECORD_TABLES, TEXT_TABLES

_EMAIL = patterns.PATTERNS["email"]
#: Columns whose values are WarnText's own fixed words, never message text.
VOCABULARY = frozenset(
    {
        "config",
        "sender_kind",
        "sender_kind_source",
        "sender_kind_rule",
        "authority_type",
        "organization_source",
        "unit",
        "codebook_version",
        "not_coded_reason",
        "hazard_category",
        "hazard_category_source",
        "link_kinds",
        "event_group",
        "hazard",
        "text_withheld",
        "withheld_patterns",
        "shape",
        "resolved_by",
        "parse_problems",
        "crosscheck_mismatches",
    }
)
#: Columns of names and allow-listed codes, where words about a person can be an
#: organization's own name or a standard class.
NAMES_AND_CODES = frozenset({"organization", "wea_handling", "parameter_values"})


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


#: What splits a cell into tokens when looking for a raw identifier inside it (spaces, and the
#: separators of links and lists). Identifiers themselves hold letters, digits, ``.-_:``.
_TOKEN_SPLIT = re.compile(r"[\s/?&=#,;\"'<>()\[\]{}|]+")


def check(
    tables: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    sender_values: Iterable[str],
    server_counts: Mapping[int, int] | None,
    identifiers: Iterable[str] = (),
) -> list[str]:
    """Run every rule; return the failures (empty when the tables pass).

    ``identifiers`` are the raw CAP identifiers from the private file; none may appear.
    """
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
    # their sender value. Values of digits only are left out here: some sending systems put
    # the message's own number in the sender field, and those numbers are raw identifiers,
    # which the identifier rule below covers.
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

    # Raw CAP identifiers: none may appear, as a whole cell or as a token inside one.
    ids = {i.strip().casefold() for i in identifiers if i and i.strip()}
    if ids:
        for c in CONFIGS:
            for name in RECORD_TABLES + TEXT_TABLES:
                hits = 0
                for row in tables[c][name]:
                    for cell in _cells(row):
                        folded = cell.strip().casefold()
                        if folded in ids or any(t in ids for t in _TOKEN_SPLIT.split(folded)):
                            hits += 1
                if hits:
                    fail.append(f"{c}/{name}: {hits} cell(s) hold a raw CAP identifier.")

    # Messages with a people code, and messages about a missing person, carry no time finer than
    # the hour (nor do the references and threads that touch them), and keep the county only.
    people = {r["message_id"] for r in messages if r["text_withheld"] == "people_code"}
    missing = {r["message_id"] for r in messages if r.get("about_missing_person")}
    for label, ids in (("people-code", people), ("missing-person", missing)):
        threads = {r["thread_id"] for r in messages if r["message_id"] in ids}
        for c in CONFIGS:
            exact = _exact_times(tables[c], ids, threads)
            if exact:
                fail.append(
                    f"{c}: {label} rows hold times finer than the hour: {dict(exact)}. "
                    "Rebuild the tables; the exact times belong in the private table only."
                )
    coarse = people | missing
    for c in CONFIGS:
        parts = _part_digits(tables[c], coarse)
        if parts:
            fail.append(
                f"{c}: people-code or missing-person rows hold a part-of-county digit: "
                f"{dict(parts)}. Rebuild the tables; these rows keep the county only."
            )

    # The record layer holds no text: no cell may match a personal-detail pattern. WarnText's own
    # vocabulary (``missing_person``) is not scanned, and the words about a person are not
    # looked for in organization names or allow-listed codes ("AMBER Alert" is a phone-alert
    # class, and child-alert programs name themselves so); the detail patterns still are.
    for c in CONFIGS:
        for name in RECORD_TABLES:
            found: Counter = Counter()
            for row in tables[c][name]:
                for column, value in row.items():
                    if column in VOCABULARY:
                        continue
                    values = value if isinstance(value, list) else [value]
                    for cell in values:
                        if not isinstance(cell, str):
                            continue
                        for pattern, hit in patterns.present(cell).items():
                            if hit and not (
                                pattern == "person_words" and column in NAMES_AND_CODES
                            ):
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
        "codes": [
            (r["message_id"], r["info_index"], r["unit"])
            for c in CONFIGS
            for r in tables[c].get("codes", [])
        ],
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


def _exact_times(
    tables: Mapping[str, list[dict[str, Any]]], ids: set[str], threads: set[str]
) -> Counter:
    """Time cells finer than the hour on the rows that touch ``ids``, by table and column."""
    exact: Counter = Counter()
    fields = (
        ("messages", ("sent", "sent_utc"), lambda r: r["message_id"] in ids),
        ("infos", ("effective", "onset", "expires"), lambda r: r["message_id"] in ids),
        (
            "references",
            ("ref_sent",),
            lambda r: r["message_id"] in ids or r["ref_message_id"] in ids,
        ),
        ("threads", ("first_sent_utc", "last_sent_utc"), lambda r: r["thread_id"] in threads),
    )
    for name, columns, touches in fields:
        for r in tables[name]:
            if touches(r):
                for col in columns:
                    if privacy.finer_than_hour(r.get(col)):
                        exact[f"{name}.{col}"] += 1
    for r in tables["infos"]:
        if r["message_id"] in ids:
            for n, v in zip(r["parameter_names"], r["parameter_values"], strict=True):
                if n == "EASHeader" and privacy.eas_header_finer(v)[1]:
                    exact["infos.EASHeader"] += 1
    return exact


def _part_digits(tables: Mapping[str, list[dict[str, Any]]], ids: set[str]) -> Counter:
    """Area codes with a part-of-county digit on the rows of ``ids``, by where they are."""
    found: Counter = Counter()
    for r in tables["messages"]:
        if r["message_id"] in ids:
            found["messages.same_geocodes"] += sum(
                privacy.has_part_digit(g) for g in r["same_geocodes"]
            )
    for r in tables["areas"]:
        if r["message_id"] in ids:
            for n, v in zip(r["geocode_names"], r["geocode_values"], strict=True):
                if n.strip().upper() in privacy.PART_DIGIT_GEOCODES and privacy.has_part_digit(v):
                    found["areas.geocode_values"] += 1
    for r in tables["infos"]:
        if r["message_id"] in ids:
            for n, v in zip(r["parameter_names"], r["parameter_values"], strict=True):
                if n == "EASHeader" and privacy.eas_header_finer(v)[0]:
                    found["infos.EASHeader"] += 1
    return +found


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


def read_identifiers(private_dir: Path | str) -> list[str]:
    """The raw CAP identifiers the build kept privately. A build always writes the file."""
    path = Path(private_dir) / "identifiers.json"
    if not path.exists():
        raise SystemExit(
            f"{path} is missing, so raw identifiers cannot be checked. Run `warntext build` "
            "again; it writes this private file next to the tables."
        )
    return list(json.loads(path.read_text(encoding="utf-8")))
