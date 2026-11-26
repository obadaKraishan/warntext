"""The easy-access layer: plain files beside the Parquet tables, for readers who do not use Parquet.

Every version from 0.2.0 holds, on top of its Parquet files (which stay the full release):

- ``00_start_here_messages.csv``: the ``messages`` table, real alerts and tests together (its
  ``config`` column says which), with the words of each message's first language block where the
  text is released and empty cells where it is withheld (``text_status`` says which);
- ``00_start_here_messages.xlsx``: the same rows in a workbook with a Read me sheet and a Fields
  sheet (or, past about 100 MB, a seeded sample of 1,000 rows whose name says so);
- ``fields.csv``: every column of every table, with its type, meaning and allowed values;
- ``codebook.csv``: the six content codes of the version's codebook, with each code's
  definition, status and the two figures of the rule for release;
- a gzipped CSV of every Parquet file, beside it (``alerts/messages.csv.gz``).

The CSV files are plain UTF-8 with a header row: a list's items joined with ``"; "``, yes and no
as 1 and 0, times in UTC as ``YYYY-MM-DDTHH:MM:SSZ``, and an empty cell for no value. The Kaggle
mirror carries the same files without any words (its start-here file and workbook leave the
word columns out, and it holds no text table).

``build`` writes the files and returns their manifest entries; ``problems`` checks them against
the pack's Parquet files row for row, so a CSV can never say what its table does not.
"""

from __future__ import annotations

import csv
import gzip
import io
import random
import shutil
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from warntext import citation, durable, fields, patterns, privacy, xlsx
from warntext.tables import CONFIGS

START_HERE = "00_start_here_messages.csv"
XLSX_WHOLE = "00_start_here_messages.xlsx"
XLSX_SAMPLE = "00_start_here_messages_sample_1000.xlsx"
FIELDS_FILE = "fields.csv"
CODEBOOK_FILE = "codebook.csv"
#: Past this size the workbook becomes a seeded sample.
XLSX_MAX_BYTES = 100_000_000
SAMPLE_ROWS = 1_000
SAMPLE_SEED = 20261126
#: How the list items of a CSV cell are joined.
LIST_JOIN = "; "
#: The words the start-here file takes from the first released language block, and their names.
TEXT_FROM_BLOCK = {
    "text_language": "language",
    "headline": "headline",
    "description": "description",
    "instruction": "instruction",
    "wea_short": "wea_short",
    "wea_long": "wea_long",
    "credit": "credit",
}
FIELDS_HEADER = ("table", "column", "type", "meaning", "allowed_values", "where")
CODEBOOK_HEADER = (
    "code",
    "codebook_version",
    "label",
    "definition",
    "status",
    "in_codes_table",
    "alpha_on_sheet",
    "alpha_95_interval",
    "coder_consistency",
    "consistency_95_interval",
)
#: The six content codes' labels and definitions under codebook version 3 (``docs/codebook.md``
#: section 9; the hand-sheet guide's words, without its examples).
CONTENT_DEFINITIONS = {
    "3": {
        "hazard": (
            "Hazard",
            "The threat or event is named. A generic event word counts only with a word that "
            "gives its kind; a word for the message itself (alert, advisory, notice, warning) is "
            "never the hazard; an action, or an order or ban that names no threat, is guidance, "
            "not a hazard. A closure or an outage that is itself the event is a hazard.",
        ),
        "hazard_description": (
            "Hazard description",
            "Anything said about the hazard beyond its name: what it is doing, how big, how "
            "fast, where it is heading, how dangerous, what it can cause. No named hazard, no "
            "description.",
        ),
        "source_named": (
            "Source",
            "The organization that speaks is named, in words or by its usual initials, as the "
            "sender or as the one saying, issuing, advising, asking, warning or reporting. An "
            "organization that only acts is not the source; a web address alone is not; a place "
            "name counts only when it is written as the speaker.",
        ),
        "guidance": (
            "Guidance",
            "Any instruction or prohibition to the public, in any form, and telling people where "
            "to get information.",
        ),
        "time": (
            "Time",
            "When the danger comes, when to act, until when it lasts, or for how long: a time "
            "expression for something still to come, to do or to last (a clock time or date "
            "ahead, a duration, a time word for acting, or an explicit open end). Verbs of state "
            "alone are not time, nor is the time at which something already happened.",
        ),
        "location": (
            "Location",
            "A named place at any level: a city, county, neighborhood, road, intersection, "
            "landmark or zone, with a proper name, a numbered or lettered zone, a road name or "
            "number, or an address. A generic word is not a location, nor is an area named only "
            "after the hazard.",
        ),
    }
}


# --- rendering ---------------------------------------------------------------------------


def _time(t: datetime) -> str:
    t = t.astimezone(timezone.utc)
    ms = f".{t.microsecond // 1000:03d}" if t.microsecond else ""
    return f"{t:%Y-%m-%dT%H:%M:%S}{ms}Z"


def cell(value: Any) -> str:
    """A value as a CSV cell writes it."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (list, tuple)):
        return LIST_JOIN.join(cell(v) for v in value)
    if isinstance(value, datetime):
        return _time(value)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _workbook_value(value: Any) -> Any:
    """A value as the workbook writes it: numbers as numbers, the rest as the CSV's text."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    return cell(value)


def _rows(table: pa.Table) -> Iterator[list[str]]:
    for r in table.to_pylist():
        yield [cell(r[c]) for c in table.column_names]


def write_csv(path: Path, header: Iterable[str], rows: Iterable[list[str]]) -> int:
    """Write a CSV file (gzipped when the name ends in ``.gz``, with no time in its header, so
    the same rows give the same bytes). Returns the data rows written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    if path.name.endswith(".gz"):
        with (
            path.open("wb") as raw,
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz,
            io.TextIOWrapper(gz, encoding="utf-8", newline="") as text,
        ):
            w = csv.writer(text)
            w.writerow(list(header))
            for row in rows:
                w.writerow(row)
                n += 1
        return n
    with path.open("w", encoding="utf-8", newline="") as text:
        w = csv.writer(text)
        w.writerow(list(header))
        for row in rows:
            w.writerow(row)
            n += 1
    return n


def read_csv(path: Path) -> Iterator[list[str]]:
    """The rows of a CSV file the layer wrote (gzipped or not), the header first."""
    if path.name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", newline="") as text:
            yield from csv.reader(text)
    else:
        with path.open(encoding="utf-8", newline="") as text:
            yield from csv.reader(text)


# --- the start-here table ----------------------------------------------------------------


def text_status(message: Mapping[str, Any], has_row: bool, kinds: Iterable[str]) -> str:
    """Whether the start-here file carries a message's words, and if not, why."""
    if message.get("text_withheld"):
        return "withheld"
    if has_row:
        return "released"
    if message.get("sender_kind") not in set(kinds):
        return "sender kind left out"
    return "no text in the archive"


def start_here(
    pack_dir: Path, text_tables: Iterable[str], kinds: Iterable[str], with_text: bool = True
) -> tuple[list[str], list[list[Any]], list[pa.DataType]]:
    """The start-here table: header, rows (values, not yet cells) and each column's type.

    Real alerts first, then tests; within each, the messages table's own order. The words come
    from the first released language block (the lowest ``info_index`` with a text row)."""
    kinds = list(kinds)
    schema = pq.read_schema(pack_dir / "alerts" / "messages.parquet")
    added = list(fields.START_HERE_ADDED if with_text else ("text_status",))
    header = [*schema.names, *added]
    types = [*schema.types, *[pa.string()] * len(added)]
    rows: list[list[Any]] = []
    for config in CONFIGS:
        first: dict[str, dict[str, Any]] = {}
        for name in text_tables:
            path = pack_dir / config / f"{name}.parquet"
            if not path.exists():
                continue
            for r in pq.read_table(path).to_pylist():
                held = first.get(r["message_id"])
                if held is None or r["info_index"] < held["info_index"]:
                    first[r["message_id"]] = r
        for m in pq.read_table(pack_dir / config / "messages.parquet").to_pylist():
            block = first.get(m["message_id"])
            status = text_status(m, block is not None, kinds)
            row = [m[c] for c in schema.names] + [status]
            if with_text:
                for column in fields.START_HERE_TEXT:
                    value = (
                        block.get(TEXT_FROM_BLOCK[column])
                        if block and status == "released"
                        else None
                    )
                    row.append(value)
            rows.append(row)
    return header, rows, types


# --- fields.csv and codebook.csv ---------------------------------------------------------


def fields_rows(pack_dir: Path, tables: Iterable[str]) -> list[list[str]]:
    """``fields.csv``: every column of every Parquet table in the pack, then the start-here
    file's columns (types from the Parquet schemas)."""
    out = []
    for name in tables:
        path = pack_dir / "alerts" / f"{name}.parquet"
        if not path.exists():
            continue
        where = fields.HF_ONLY if name.startswith("text_") else fields.HF_AND_KAGGLE
        for f in pq.read_schema(path):
            meaning, values = fields.entry(name, f.name)
            out.append([name, f.name, fields.type_words(f.type), meaning, values, where])
    schema = pq.read_schema(pack_dir / "alerts" / "messages.parquet")
    for f in schema:
        meaning, values = fields.entry("messages", f.name)
        out.append(
            ["start_here", f.name, fields.type_words(f.type), meaning, values, fields.HF_AND_KAGGLE]
        )
    for column in fields.START_HERE_ADDED:
        meaning, values = fields.entry("start_here", column)
        where = fields.HF_ONLY if column in fields.START_HERE_TEXT else fields.HF_AND_KAGGLE
        out.append(["start_here", column, "text", meaning, values, where])
    return out


def codebook_rows(version: str, released_columns: Iterable[str]) -> list[list[str]]:
    """``codebook.csv``: the six content codes of a codebook version, with their statuses."""
    from warntext import release

    if version not in CONTENT_DEFINITIONS:
        raise SystemExit(
            f"No content-code definitions for codebook version {version} in access.py; write "
            "them (from docs/codebook.md) before building its easy-access layer."
        )
    status = release.code_status(version)
    columns = set(released_columns)
    out = []
    for code in release.CONTENT_CODES:
        label, definition = CONTENT_DEFINITIONS[version][code]
        r = status[code]
        interval = f"{r['alpha_low']} to {r['alpha_high']}" if r.get("alpha_low") else ""
        recheck = f"{r['recheck_low']} to {r['recheck_high']}" if r.get("recheck_low") else ""
        out.append(
            [
                code,
                version,
                label,
                definition,
                "validated" if r["status"] == "released" else "experimental",
                "yes" if code in columns else "no",
                r.get("hand_sheet_alpha") or "",
                interval,
                r.get("recheck_alpha") or "",
                recheck,
            ]
        )
    return out


# --- the workbook ------------------------------------------------------------------------


def read_me_rows(
    manifest: Mapping[str, Any], rows: int, sample: bool, kaggle: bool
) -> list[list[str]]:
    """The workbook's Read me sheet, one sentence or quotation a row."""
    from warntext import release

    version = manifest["version"]
    what = (
        f"A seeded random sample of {SAMPLE_ROWS:,} of the {rows:,} messages (seed "
        f"{SAMPLE_SEED}): the whole table is too large for a workbook. The whole table is "
        f"{START_HERE}."
        if sample
        else f"Every message of this version: {rows:,} rows, the same as {START_HERE}."
    )
    words = (
        "This copy holds no message words: the Kaggle mirror carries the record layer only. "
        "The words are in the Hugging Face copy (https://huggingface.co/datasets/obadakr/warntext)."
        if kaggle
        else "Where a message's text is released, its first language block's words follow in the "
        "last columns; where it is withheld, text_status says so and those cells are empty "
        "(text_withheld gives the reason)."
    )
    lines = [
        [f"WarnText {version}: the messages table, one row per message"],
        [""],
        [
            "A research record, not an alerting service. WarnText runs at least a day behind the "
            "source and must never be used to receive or pass on warnings."
        ],
        [""],
        [
            "US public alert messages sent through the Integrated Public Alert and Warning System "
            "(IPAWS), read from FEMA's OpenFEMA dataset IPAWS Archived Alerts (version 1), from "
            "senders other than the National Weather Service, sent before "
            f"{citation.bound_words(str(manifest['records_sent_before']))}. The config column "
            "says whether a row is a real alert (alerts) or a test (tests)."
        ],
        [what],
        [words],
        [
            "Cells: 1 is yes and 0 is no; an empty cell has no value; a list's items are joined "
            "with a semicolon and a space; times are in UTC. The Fields sheet gives every "
            "column's meaning, type and allowed values."
        ],
        [""],
        ["The terms that users must follow (OpenFEMA's, " + release.TERMS_URL + "):"],
        [
            "By accessing OpenFEMA datasets, you agree that the data will be used solely for "
            "statistical research or as a reporting record. Further you agree not to reidentify "
            "nor attempt to reidentify the individuals whose data is aggregated. You also agree "
            "not to publish or release any facts that may lead to the identification of "
            "individuals who are the subject of the data."
        ],
        [
            "This product uses the Federal Emergency Management Agency\u2019s OpenFEMA API, but is "
            "not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the data or "
            "analyses derived from these data after the data have been retrieved from the "
            "Agency's website(s)."
        ],
        [
            "Do not try to identify anyone named or described in a message, and do not join this "
            "data to other sources to do so."
        ],
        [""],
        ["How to cite:"],
        [citation.apa(version, citation.year_of(dict(manifest)), markdown=False)],
        [
            "Cite the source too: Federal Emergency Management Agency (FEMA), OpenFEMA Dataset: "
            "IPAWS Archived Alerts - v1. Retrieved from "
            f"https://www.fema.gov/api/open/v1/IpawsArchivedAlerts on {manifest['retrieved']} "
            "(UTC)."
        ],
    ]
    return lines


def write_workbook(
    out_dir: Path,
    manifest: Mapping[str, Any],
    header: list[str],
    rows: list[list[Any]],
    field_rows: list[list[str]],
    kaggle: bool = False,
) -> tuple[Path, bool, list[int]]:
    """The workbook: the whole table, or past ``XLSX_MAX_BYTES`` a seeded sample. Returns its
    path, whether it is the sample, and the indexes of the rows it holds."""

    def write(name: str, picked: list[int], sample: bool) -> Path:
        path = out_dir / name
        data = ([_workbook_value(v) for v in rows[i]] for i in picked)
        xlsx.write_data_workbook(
            path,
            (
                xlsx.DataSheet(
                    "Read me",
                    read_me_rows(manifest, len(rows), sample, kaggle),
                    header=False,
                    widths=(120,),
                ),
                xlsx.DataSheet("Messages", _chain([header], data)),
                xlsx.DataSheet("Fields", _chain([list(FIELDS_HEADER)], field_rows)),
            ),
        )
        return path

    every = list(range(len(rows)))
    path = write(XLSX_WHOLE, every, False)
    if path.stat().st_size <= XLSX_MAX_BYTES:
        return path, False, every
    path.unlink()
    picked = sorted(random.Random(SAMPLE_SEED).sample(every, min(SAMPLE_ROWS, len(every))))
    return write(XLSX_SAMPLE, picked, True), True, picked


def _chain(first: list, rest: Iterable) -> Iterator:
    yield from first
    yield from rest


# --- build -------------------------------------------------------------------------------


def _entry(pack_dir: Path, path: Path, rows: int) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(pack_dir).as_posix(),
        "rows": rows,
        "bytes": len(data),
        "sha256": durable.sha256_bytes(data),
    }


def _longest(rows: Iterable[list[str]]) -> int:
    return max((len(c) for r in rows for c in r), default=0)


def build(
    pack_dir: Path, manifest: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Write the layer into a pack whose Parquet files and manifest entries exist; return the
    manifest's ``access_files`` (in the order a reader meets them) and its ``access`` facts."""
    pack_dir = Path(pack_dir)
    text_tables = list(manifest["text_tables"])
    kinds = list(manifest["text_kinds"])
    tables = [f["path"].split("/")[1].removesuffix(".parquet") for f in manifest["files"]]
    tables = list(dict.fromkeys(tables))
    header, values, _ = start_here(pack_dir, text_tables, kinds)
    cells = [[cell(v) for v in r] for r in values]
    entries = []
    n = write_csv(pack_dir / START_HERE, header, cells)
    entries.append(_entry(pack_dir, pack_dir / START_HERE, n))
    field_rows = fields_rows(pack_dir, tables)
    book, sample, picked = write_workbook(pack_dir, manifest, header, values, field_rows)
    entries.append(_entry(pack_dir, book, len(picked)))
    n = write_csv(pack_dir / FIELDS_FILE, FIELDS_HEADER, field_rows)
    entries.append(_entry(pack_dir, pack_dir / FIELDS_FILE, n))
    codes = pq.read_schema(pack_dir / "alerts" / "codes.parquet").names
    rows = codebook_rows(str(manifest["codebook_version"]), codes)
    n = write_csv(pack_dir / CODEBOOK_FILE, CODEBOOK_HEADER, rows)
    entries.append(_entry(pack_dir, pack_dir / CODEBOOK_FILE, n))
    longest = _longest(cells)
    separator = 0
    for f in manifest["files"]:
        table = pq.read_table(pack_dir / f["path"])
        gz = pack_dir / f["path"].replace(".parquet", ".csv.gz")
        n = write_csv(gz, table.column_names, _rows(table))
        entries.append(_entry(pack_dir, gz, n))
        separator += _items_with_separator(table)
    facts = {
        "start_here_rows": len(cells),
        "start_here_columns": len(header),
        "start_here_longest_cell": longest,
        "workbook": "sample" if sample else "whole",
        "workbook_rows": len(picked),
        "list_items_holding_the_separator": separator,
    }
    return entries, facts


def _items_with_separator(table: pa.Table) -> int:
    """List items that themselves hold the CSV's list separator (their CSV cell cannot be split
    back exactly; the Parquet file holds them as they are)."""
    n = 0
    for name, t in zip(table.column_names, table.schema.types, strict=True):
        if pa.types.is_list(t):
            for v in table.column(name).to_pylist():
                n += sum(1 for x in v or [] if isinstance(x, str) and LIST_JOIN in x)
    return n


# --- check -------------------------------------------------------------------------------


def _same(path: Path, header: list[str], rows: Iterable[list[str]], label: str) -> list[str]:
    """The CSV file holds exactly this header and these rows."""
    if not path.exists():
        return [f"{label}: missing."]
    got = read_csv(path)
    if next(got, None) != header:
        return [f"{label}: its header differs from its table's columns."]
    for n, (a, b) in enumerate(zip_longest(got, rows), start=1):
        if a is None or b is None:
            return [f"{label}: it holds a different number of rows from its table."]
        if a != b:
            return [f"{label}: row {n} differs from its table (rebuild the pack)."]
    return []


def _lines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def problems(pack_dir: Path | str, manifest: Mapping[str, Any]) -> list[str]:
    """Every rule the layer must pass (counts and file names only, never a cell's words)."""
    pack_dir = Path(pack_dir)
    fail: list[str] = []
    listed = manifest.get("access_files") or []
    if not listed:
        return []
    names = [f["path"] for f in listed]
    want = [START_HERE]
    book = XLSX_SAMPLE if (manifest.get("access") or {}).get("workbook") == "sample" else XLSX_WHOLE
    want += [book, FIELDS_FILE, CODEBOOK_FILE]
    want += [f["path"].replace(".parquet", ".csv.gz") for f in manifest["files"]]
    if names != want:
        fail.append(f"manifest.json: access_files are {names}, not the layer's files {want}.")
    for f in listed:
        path = pack_dir / f["path"]
        if not path.exists():
            fail.append(f"{f['path']}: in the manifest but missing.")
        elif durable.sha256_file(path) != f["sha256"]:
            fail.append(f"{f['path']}: does not match its SHA-256 in the manifest.")
    if fail:
        return fail
    text_tables = list(manifest["text_tables"])
    kinds = list(manifest["text_kinds"])
    tables = list(
        dict.fromkeys(f["path"].split("/")[1].removesuffix(".parquet") for f in manifest["files"])
    )
    header, values, _ = start_here(pack_dir, text_tables, kinds)
    cells = [[cell(v) for v in r] for r in values]
    fail += _same(pack_dir / START_HERE, header, iter(cells), START_HERE)
    if len(cells) + 1 > xlsx.MAX_ROWS:
        fail.append(f"{START_HERE}: {len(cells):,} rows, over Excel's {xlsx.MAX_ROWS:,}.")
    long = sum(1 for r in cells for c in r if len(c) > xlsx.MAX_CELL)
    if long:
        fail.append(f"{START_HERE}: {long} cell(s) over Excel's {xlsx.MAX_CELL:,} characters.")
    fail += _start_here_privacy(header, cells)
    field_rows = fields_rows(pack_dir, tables)
    fail += _same(pack_dir / FIELDS_FILE, list(FIELDS_HEADER), iter(field_rows), FIELDS_FILE)
    codes = pq.read_schema(pack_dir / "alerts" / "codes.parquet").names
    rows = codebook_rows(str(manifest["codebook_version"]), codes)
    fail += _same(pack_dir / CODEBOOK_FILE, list(CODEBOOK_HEADER), iter(rows), CODEBOOK_FILE)
    fail += _workbook_problems(pack_dir / book, header, cells, book == XLSX_SAMPLE)
    for f in manifest["files"]:
        table = pq.read_table(pack_dir / f["path"])
        gz = f["path"].replace(".parquet", ".csv.gz")
        fail += _same(pack_dir / gz, table.column_names, _rows(table), gz)
    return fail


def _workbook_problems(
    path: Path, header: list[str], cells: list[list[str]], sample: bool
) -> list[str]:
    picked = (
        sorted(random.Random(SAMPLE_SEED).sample(range(len(cells)), min(SAMPLE_ROWS, len(cells))))
        if sample
        else range(len(cells))
    )
    rows = xlsx.read_data_rows(path, 2)
    if [_lines(c) for c in next(rows, [])] != header:
        return [f"{path.name}: the Messages sheet's header differs from {START_HERE}'s."]
    for n, (got, i) in enumerate(zip_longest(rows, picked), start=1):
        if got is None or i is None:
            return [f"{path.name}: the Messages sheet holds a different number of rows."]
        want = [_lines(c) for c in cells[i]]
        got = got + [""] * (len(want) - len(got))
        if got != want:
            return [f"{path.name}: row {n} of the Messages sheet differs from {START_HERE}."]
    return []


def _start_here_privacy(header: list[str], cells: list[list[str]]) -> list[str]:
    """No words for a withheld message; no personal-detail pattern or missing-person wording in
    the words the file carries (the text tables' own scan, read again here)."""
    fail = []
    at = {
        c: header.index(c)
        for c in ("text_status", "text_withheld", *fields.START_HERE_TEXT)
        if c in header
    }
    words = [
        at[c] for c in fields.START_HERE_TEXT if c in at and c not in ("text_language", "credit")
    ]
    leaked = 0
    found: dict[str, int] = {}
    for r in cells:
        if r[at["text_status"]] != "released":
            leaked += any(r[i] for i in words)
            continue
        if r[at["text_withheld"]]:
            leaked += 1
        for i in words:
            if not r[i]:
                continue
            hits = [p for p, hit in patterns.present(r[i]).items() if hit]
            if privacy.MISSING_PERSON.search(r[i]):
                hits.append("missing_person")
            for h in hits:
                found[f"{header[i]}:{h}"] = found.get(f"{header[i]}:{h}", 0) + 1
    if leaked:
        fail.append(
            f"{START_HERE}: {leaked} row(s) carry words for a message whose text is not released."
        )
    if found:
        fail.append(f"{START_HERE}: its words match personal-detail patterns: {found}")
    return fail


# --- the Kaggle mirror's copies (no words) ------------------------------------------------


def kaggle_name(path: str) -> str:
    """A pack path's Kaggle file name: ``alerts/messages.csv.gz`` -> ``alerts-messages.csv.gz``."""
    return path.replace("/", "-")


def kaggle_files(manifest: Mapping[str, Any], record_tables: Iterable[str]) -> list[str]:
    """The layer's Kaggle file names, in order: the start-here file, the workbook, the two
    catalogues, then the record layer's gzipped CSVs."""
    tables = set(record_tables)
    out = []
    for f in manifest.get("access_files") or []:
        table = f["path"].split("/")[-1].split(".")[0]
        if "/" not in f["path"]:
            out.append(f["path"])
        elif table in tables:
            out.append(kaggle_name(f["path"]))
    return out


def build_kaggle(
    pack_dir: Path, out_dir: Path, manifest: Mapping[str, Any], record_tables: Iterable[str]
) -> list[str]:
    """The mirror's copies of the layer: the start-here file and workbook without the word
    columns, the two catalogues and the record layer's gzipped CSVs as they are."""
    pack_dir, out_dir = Path(pack_dir), Path(out_dir)
    if not manifest.get("access_files"):
        return []
    header, values, _ = start_here(pack_dir, manifest["text_tables"], manifest["text_kinds"], False)
    cells = [[cell(v) for v in r] for r in values]
    write_csv(out_dir / START_HERE, header, cells)
    field_rows = [r for r in read_csv(pack_dir / FIELDS_FILE)][1:]
    write_workbook(out_dir, manifest, header, values, field_rows, kaggle=True)
    names = kaggle_files(manifest, record_tables)
    for name in names:
        if name in (START_HERE, XLSX_WHOLE, XLSX_SAMPLE):
            continue
        source = name if name in (FIELDS_FILE, CODEBOOK_FILE) else name.replace("-", "/", 1)
        shutil.copyfile(pack_dir / source, out_dir / name)
    return names


def kaggle_problems(
    pack_dir: Path, out_dir: Path, manifest: Mapping[str, Any], record_tables: Iterable[str]
) -> list[str]:
    """The mirror's layer: every file present; the start-here file and workbook equal to the
    pack's without the word columns; the other files the pack's own by SHA-256; no word column."""
    pack_dir, out_dir = Path(pack_dir), Path(out_dir)
    if not manifest.get("access_files"):
        return []
    fail = []
    names = kaggle_files(manifest, record_tables)
    for name in names:
        if not (out_dir / name).exists():
            fail.append(f"kaggle/{name}: missing.")
    if fail:
        return fail
    header, values, _ = start_here(pack_dir, manifest["text_tables"], manifest["text_kinds"], False)
    cells = [[cell(v) for v in r] for r in values]
    fail += _same(out_dir / START_HERE, header, iter(cells), f"kaggle/{START_HERE}")
    book = next(n for n in names if n.endswith(".xlsx"))
    fail += _workbook_problems(out_dir / book, header, cells, book == XLSX_SAMPLE)
    words = set(fields.START_HERE_TEXT)
    for name in names:
        if name in (START_HERE, book):
            continue
        source = name if name in (FIELDS_FILE, CODEBOOK_FILE) else name.replace("-", "/", 1)
        if durable.sha256_file(out_dir / name) != durable.sha256_file(pack_dir / source):
            fail.append(f"kaggle/{name}: differs from the pack's {source}.")
        if name.endswith(".csv.gz"):
            columns = set(next(read_csv(out_dir / name)))
            if columns & (words | {"headline", "description", "instruction"}):
                fail.append(f"kaggle/{name}: holds a word column; the mirror holds no text.")
    return fail


# --- the "Start here" section of the card and of the Kaggle description --------------------

KAGGLE_INPUT = "/kaggle/input/warntext"


def start_here_section(manifest: Mapping[str, Any], kaggle: bool = False) -> str:
    """The "Start here" section (Markdown, its heading included) for the card or, with
    ``kaggle``, for the Kaggle description (flat file names, no words)."""
    facts = manifest.get("access") or {}
    book = XLSX_SAMPLE if facts.get("workbook") == "sample" else XLSX_WHOLE
    rows = facts.get("start_here_rows", 0)

    def at(path: str) -> str:
        return kaggle_name(path) if kaggle else path

    if kaggle:
        look = (
            f"- **To look at the messages in a spreadsheet:** `{START_HERE}`: every message of "
            f"this version ({rows:,} rows, real alerts and tests together; `config` says which), "
            "with `text_status`, but **no words**: this mirror holds no message text. The words "
            "of the messages that are not withheld are in the Hugging Face copy "
            "(https://huggingface.co/datasets/obadakr/warntext). The same rows in Excel: "
            f"`{book}`, with a Read me sheet and a Fields sheet."
        )
        where = (
            f"On Kaggle the files are in `{KAGGLE_INPUT}/` (or use the Download button); "
            "each name is the split and the table (`alerts-messages.parquet`)."
        )
    else:
        look = (
            f"- **To look at the messages in a spreadsheet:** `{START_HERE}`: every message of "
            f"this version ({rows:,} rows, real alerts and tests together; `config` says which), "
            "with the words of its first language block where its text is released. The same "
            f"rows in Excel: `{book}`, with a Read me sheet and a Fields sheet."
        )
        where = (
            "Every file is on the Files and versions tab, or download them all with "
            "`hf download obadakr/warntext --repo-type dataset --local-dir warntext`."
        )
    if book == XLSX_SAMPLE:
        look += f" The workbook holds a seeded sample of {SAMPLE_ROWS:,} rows; the CSV holds all."
    m, k, r = at("alerts/messages"), at("alerts/codes"), at("alerts/references")
    lines = [
        "## Start here",
        "**Which file.**",
        look,
        f"- **For analysis:** the Parquet files (`{at('alerts/messages.parquet')}` and the rest), "
        "the full release. Parquet is a compressed format for tables that keeps each column's "
        "type, and R, Python and DuckDB read it directly. Every Parquet file also comes as a "
        f"gzipped CSV beside it (`{at('alerts/messages.csv.gz')}`).",
        f"- **What a column means:** `{FIELDS_FILE}` (every column of every table: its type, "
        f"meaning and allowed values). **The content codes:** `{CODEBOOK_FILE}` (the six codes, "
        "their definitions, and which are validated).",
        "",
        where,
        "",
        "**Opening the files.**",
        f"- **Excel:** open `{book}`. For a CSV file, use Data > From Text/CSV and choose UTF-8 "
        "(opening it with a double-click can garble accented letters).",
        "- **SPSS:** File > Import Data > CSV Data, on a CSV file (a `.csv.gz` file opens with "
        "any unzip tool first).",
        '- **Stata:** `import delimited using "messages.csv", varnames(1) encoding(utf-8) '
        "bindquote(strict)`, on an unzipped CSV file.",
        f'- **R:** `read.csv("{m}.csv.gz")` reads a gzipped CSV as it is; '
        f'`arrow::read_parquet("{m}.parquet")` reads a Parquet file.',
        f'- **Python:** `pandas.read_parquet("{m}.parquet")`, or `pandas.read_csv("{m}.csv.gz")`.',
        "",
        "In the CSV files and the workbook, 1 is yes and 0 is no, an empty cell has no value, a "
        'list\'s items are joined with "; ", and times are in UTC.'
        + (
            ""
            if kaggle
            else ' A few list items of the text tables hold "; " themselves; the Parquet files '
            "keep every item apart."
        ),
        "",
        "**What a withheld text looks like.** A message whose text is withheld keeps its row in "
        "`messages`, with the reason in `text_withheld` (for example `people_code`), and has no "
        + (
            "row in the text tables on Hugging Face; in the start-here file its `text_status` is "
            "`withheld`."
            if kaggle
            else "row in `text_federal` or `text_other`; in the start-here file its "
            "`text_status` is `withheld` and its word columns are empty."
        ),
        "",
        "**Joining the tables** (real alerts; the same for the tests). In R:",
        "",
        "```r",
        f'm <- read.csv("{m}.csv.gz"); k <- read.csv("{k}.csv.gz"); r <- read.csv("{r}.csv.gz")',
        'coded <- merge(m, k, by = "message_id", suffixes = c("", ".code"))',
        'linked <- merge(r, m, by.x = "ref_message_id", by.y = "message_id", '
        'suffixes = c("", ".earlier"))',
        "```",
        "",
        "In Python:",
        "",
        "```python",
        'import pandas as pd; m, k, r = (pd.read_parquet(f"'
        + (at("alerts/") if not kaggle else "alerts-")
        + '{t}.parquet") for t in ("messages", "codes", "references"))',
        'coded = m.merge(k, on="message_id", suffixes=("", "_code"))',
        'linked = r.merge(m, left_on="ref_message_id", right_on="message_id", '
        'suffixes=("", "_earlier"))',
        "```",
        "",
        "`coded` has one row per coded text unit, with its message's columns; `linked` has one "
        "row per link from an update or a cancellation, with the earlier message it points to.",
    ]
    return "\n".join(lines)
