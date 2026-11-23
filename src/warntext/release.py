"""The release pack: a release's files, built from the local tables, and its own check.

A release holds, for both configurations (real alerts and tests):

- the record layer: ``messages``, ``infos``, ``areas``, ``references``, ``threads``;
- the released content codes (``codes``, real alerts only), without the experimental ones;
- the text layer of the sender kinds the build is asked for: ``text_federal`` (federal senders)
  and ``text_other`` (state, local, tribal, territorial and unknown-kind senders), each row with
  its credit (FEMA's dataset and the alerting authority). ``--text-kinds federal`` builds a pack
  with the federal text only, as before.

A withheld message never has text in it, whatever the kinds. It never holds the private files
or anything raw. ``build_pack`` writes the files, a manifest (rows, bytes and SHA-256 per file)
and the dataset card; ``check_pack`` runs on the pack's own folder and fails, loudly, on a file
that should not be there, an experimental code, a file that does not match the manifest, a card
without its license fields or with a raw HTML tag, a text row without its credit or of a kind the
pack does not release, a text row for a message any privacy rule withholds, a personal-detail
pattern or missing-person wording in released text, and everything the release check of the
tables fails on.
"""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Iterable, Mapping
from importlib import resources
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from warntext import __version__, citation, cover, durable, hfpage, kaggle_meta, patterns, privacy
from warntext import check as ck
from warntext.probe import ENDPOINT
from warntext.tables import CONFIGS, RECORD_TABLES, SCHEMAS, TEXT_TABLES

#: Every table a pack can hold, in each configuration's folder.
RELEASED_TABLES = (*RECORD_TABLES, *TEXT_TABLES)
#: The sender kinds whose text a pack holds by default. The one national authority's kind
#: (``other``) is not among them: its text is left out.
TEXT_KINDS = ("federal", "state", "local", "tribal", "territorial", "unknown")
#: The setting for a pack with the federal senders' text only.
FEDERAL_ONLY = ("federal",)
#: The source every text row credits, with the alerting authority.
CREDIT_SOURCE = "FEMA OpenFEMA Dataset: IPAWS Archived Alerts - v1"
#: The columns the release adds to each text row: the alerting authority and the credit line.
CREDIT_COLUMNS = (("cog_id", pa.int64()), ("organization", pa.string()), ("credit", pa.string()))
#: The message-text fields of a text row (the fields the re-scan reads).
TEXT_FIELDS = (
    "event",
    "headline",
    "description",
    "instruction",
    "web",
    "audience",
    "wea_short",
    "wea_long",
    "text_parameter_values",
    "area_descriptions",
    "resource_descriptions",
    "resource_uris",
)
CODE_STATUS_FILE = "code_status.csv"
#: The codebook version a pack is built with by default: the version whose statuses (and hand-
#: sheet alphas) release 0.1.0 carries. A pack is built only from codes of the version whose
#: statuses it uses, so new rules never reach a release unchecked.
CODE_STATUS_VERSION = "1"
#: The six content codes from the warning literature, checked against a coder's hand sheets.
CONTENT_CODES = ("hazard", "hazard_description", "source_named", "guidance", "time", "location")


def _status_rows() -> list[dict[str, str]]:
    import csv
    import io

    text = resources.files("warntext").joinpath(CODE_STATUS_FILE).read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def status_versions() -> tuple[str, ...]:
    """The codebook versions that ``code_status.csv`` holds statuses for."""
    return tuple(dict.fromkeys(r["codebook_version"] for r in _status_rows()))


def code_status(version: str = CODE_STATUS_VERSION) -> dict[str, dict[str, str]]:
    """Each code's trust level, hand-sheet figures and release status for one codebook version
    (tracked file, one row per version and code)."""
    if version not in status_versions():
        raise SystemExit(
            f"{CODE_STATUS_FILE} holds no statuses for codebook version {version!r} (it holds "
            f"{', '.join(status_versions())}); score that version and add its rows first."
        )
    rows = {r["code"]: r for r in _status_rows() if r["codebook_version"] == version}
    from warntext.codes import CODE_FIELDS

    missing = sorted(set(CODE_FIELDS) - set(rows))
    unknown = sorted(set(rows) - set(CODE_FIELDS))
    bad = sorted(c for c, r in rows.items() if r["status"] not in ("released", "experimental"))
    if missing or unknown or bad:
        raise ValueError(
            f"{CODE_STATUS_FILE}, version {version}: give every code one row with status released "
            f"or experimental (missing {missing}, unknown {unknown}, bad status {bad})."
        )
    return rows


def experimental_codes(version: str = CODE_STATUS_VERSION) -> tuple[str, ...]:
    """The codes a pack of this codebook version leaves out (trust C, or not validated)."""
    return tuple(c for c, r in code_status(version).items() if r["status"] == "experimental")


def manifest_version(manifest: Mapping[str, Any]) -> str:
    """The codebook version a pack's statuses are of (release 0.1.0's manifest names none: 1)."""
    return str(manifest.get("codebook_version", "1"))


#: Version 1's experimental codes (release 0.1.0): left out of its release.
EXPERIMENTAL_CODES = experimental_codes(CODE_STATUS_VERSION)
ALLOWED_FILES = {"README.md", "manifest.json"}
TERMS_URL = "https://www.fema.gov/about/openfema/terms-conditions"
CARD_TEMPLATE = "dataset_card.md"


def _mb(n: int) -> str:
    return f"{n / 1_000_000:.1f}"


#: Hugging Face's ``size_categories``, by the dataset's rows in all.
SIZE_CATEGORIES = (
    (1_000, "n<1K"),
    (10_000, "1K<n<10K"),
    (100_000, "10K<n<100K"),
    (1_000_000, "100K<n<1M"),
    (10_000_000, "1M<n<10M"),
    (100_000_000, "10M<n<100M"),
    (1_000_000_000, "100M<n<1B"),
    (10_000_000_000, "1B<n<10B"),
    (100_000_000_000, "10B<n<100B"),
    (1_000_000_000_000, "100B<n<1T"),
)


def size_category(rows: int) -> str:
    """Hugging Face's ``size_categories`` value for a dataset of ``rows`` rows in all."""
    for bound, name in SIZE_CATEGORIES:
        if rows < bound:
            return name
    return "n>1T"


def text_tables_for(kinds: tuple[str, ...] | list[str]) -> list[str]:
    """The text tables a pack with these sender kinds holds."""
    kinds = list(kinds)
    unknown = sorted(set(kinds) - set(TEXT_KINDS) - {"other"})
    if "federal" not in kinds or unknown:
        raise SystemExit(
            f"Text kinds {kinds}: give federal and any of {', '.join(TEXT_KINDS[1:])} "
            f"(unknown: {unknown})."
        )
    return ["text_federal"] + (["text_other"] if set(kinds) - {"federal"} else [])


def pack_tables(kinds: tuple[str, ...] | list[str]) -> list[str]:
    """Every table a pack with these text kinds holds: the record layer, then its text tables."""
    return [*RECORD_TABLES, *text_tables_for(kinds)]


def expected_schema(name: str, version: str = CODE_STATUS_VERSION) -> pa.Schema:
    """The schema a released table must have (codes without the version's experimental
    columns)."""
    base = SCHEMAS[name]
    if name == "codes":
        left_out = experimental_codes(version)
        return pa.schema([f for f in base if f.name not in left_out])
    if name in TEXT_TABLES:
        fields = list(base)
        at = base.get_field_index("sender_kind") + 1
        fields[at:at] = [pa.field(n, t) for n, t in CREDIT_COLUMNS]
        return pa.schema(fields)
    return base


def credit_line(cog_id: int | None, organization: str | None) -> str | None:
    """The credit a text row carries: the alerting authority, then FEMA's dataset.

    Where the organization name is blank (by the maintainer's review, or unknown), the credit
    carries FEMA's identifier only.
    """
    if cog_id is None:
        return None
    who = (
        f"{organization} (IPAWS alerting authority, FEMA ID {cog_id})"
        if organization
        else f"IPAWS alerting authority FEMA ID {cog_id}"
    )
    return f"Message by {who}; from {CREDIT_SOURCE}"


def release_view(
    text: pa.Table, messages: list[dict[str, Any]], kinds: tuple[str, ...] | list[str]
) -> pa.Table:
    """A text table as released: the rows of the asked kinds, each with its credit columns."""
    by_id = {m["message_id"]: m for m in messages}
    rows = []
    for r in text.to_pylist():
        if r["sender_kind"] not in kinds:
            continue
        m = by_id.get(r["message_id"], {})
        r["cog_id"] = m.get("cog_id")
        r["organization"] = m.get("organization") or None
        r["credit"] = credit_line(r["cog_id"], r["organization"])
        rows.append(r)
    fields = list(text.schema)
    at = text.schema.get_field_index("sender_kind") + 1
    fields[at:at] = [pa.field(n, t) for n, t in CREDIT_COLUMNS]
    return pa.Table.from_pylist(rows, schema=pa.schema(fields))


def build_pack(
    tables_dir: Path | str,
    out_dir: Path | str,
    version: str,
    until: str,
    retrieved: str,
    codebook_version: str = CODE_STATUS_VERSION,
    text_kinds: tuple[str, ...] | list[str] = TEXT_KINDS,
    codes_from: Path | str | None = None,
) -> dict[str, Any]:
    """Write the release files, the manifest and the card to ``out_dir`` (which must be new).

    The tables' codes must be of ``codebook_version``, the version the statuses were measured on.
    ``text_kinds`` are the sender kinds whose text is released (``FEDERAL_ONLY`` for the federal
    text alone). ``codes_from`` takes the ``codes`` tables from another build's folder (a build
    of the statuses' codebook version) while the record and text layers come from
    ``tables_dir``; its coded units must be exactly the units of ``tables_dir``'s messages.
    """
    tables_dir, out_dir = Path(tables_dir), Path(out_dir)
    text_tables = text_tables_for(text_kinds)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} is not empty; a pack is built once into a new folder.")
    left_out = experimental_codes(codebook_version)  # stops if the version has no statuses
    stale_on_removal_list(tables_dir)
    codes_dir = Path(codes_from) if codes_from is not None else tables_dir
    if codes_from is not None:
        same_units(tables_dir, codes_dir)
    codes_path = codes_dir / "alerts" / "codes.parquet"
    if codes_path.exists():
        found = set(pq.read_table(codes_path, columns=["codebook_version"]).column(0).to_pylist())
        if found and found != {codebook_version}:
            raise SystemExit(
                f"{codes_path} holds codebook version(s) {sorted(found)}, but the release statuses "
                f"were measured on version {codebook_version}. Build the pack from tables of that "
                "version, or score the new version and update code_status.csv first."
            )
    files = []
    for config in CONFIGS:
        (out_dir / config).mkdir(parents=True, exist_ok=True)
        messages: list[dict[str, Any]] = []
        for name in (*RECORD_TABLES, *text_tables):
            src = (codes_dir if name == "codes" else tables_dir) / config / f"{name}.parquet"
            if not src.exists():
                raise SystemExit(f"{src} is missing; run `warntext build` or `warntext update`.")
            table = pq.read_table(src)
            if name == "messages":
                messages = table.select(["message_id", "cog_id", "organization"]).to_pylist()
            if name == "codes":
                if table.num_rows == 0:
                    continue  # tests carry no codes
                keep = [c for c in table.column_names if c not in left_out]
                table = table.select(keep)
            if name in TEXT_TABLES:
                table = release_view(table, messages, text_kinds)
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
        "facts": pack_facts(out_dir, text_tables, text_kinds),
        "version": version,
        "built_with": f"warntext {__version__}",
        "source": ENDPOINT,
        "records_sent_before": until,
        "retrieved": retrieved,
        "text_tables": text_tables,
        "text_kinds": list(text_kinds),
        "codebook_version": codebook_version,
        "experimental_codes_left_out": list(left_out),
        "files": files,
        "rows": sum(f["rows"] for f in files),
        "bytes": sum(f["bytes"] for f in files),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")
    (out_dir / "README.md").write_text(card(manifest), encoding="utf-8")
    return manifest


def stale_on_removal_list(tables_dir: Path | str, removals: Iterable[str] | None = None) -> None:
    """Stop unless every message the removal list names is withheld in the tables (tables
    built before an entry was added must be rebuilt before a pack is made from them)."""
    removal_ids = privacy.load_removals() if removals is None else frozenset(removals)
    if not removal_ids:
        return
    for config in CONFIGS:
        path = Path(tables_dir) / config / "messages.parquet"
        if not path.exists():
            continue
        rows = pq.read_table(path, columns=["message_id", "record_ids", "text_withheld"])
        stale = sum(
            1
            for m in rows.to_pylist()
            if not m["text_withheld"] and privacy.on_removal_list(m, removal_ids)
        )
        if stale:
            raise SystemExit(
                f"{path}: {stale} message(s) on the removal list are not withheld; rebuild the "
                "tables (`warntext update --rebuild`) before the pack."
            )


#: The columns that key a coded unit.
UNIT_KEY = ("message_id", "info_index", "unit")


def same_units(tables_dir: Path | str, codes_dir: Path | str) -> None:
    """Stop unless the ``codes`` of ``codes_dir`` code exactly the units the ``codes`` of
    ``tables_dir`` code (the same messages, language blocks and units), in both configurations,
    and every coded message is in ``tables_dir``'s messages."""
    for config in CONFIGS:
        mine = Path(tables_dir) / config / "codes.parquet"
        theirs = Path(codes_dir) / config / "codes.parquet"
        if not theirs.exists():
            raise SystemExit(f"{theirs} is missing; give the folder of a full build.")
        keys = {
            tuple(r.values()) for r in pq.read_table(theirs, columns=list(UNIT_KEY)).to_pylist()
        }
        if mine.exists():
            want = {
                tuple(r.values()) for r in pq.read_table(mine, columns=list(UNIT_KEY)).to_pylist()
            }
            if keys != want:
                raise SystemExit(
                    f"{theirs} codes {len(keys):,} units and {mine} {len(want):,}, "
                    f"{len(keys ^ want):,} different: build both from the same records."
                )
        ids = set(
            pq.read_table(Path(tables_dir) / config / "messages.parquet", columns=["message_id"])
            .column(0)
            .to_pylist()
        )
        stray = {k[0] for k in keys} - ids
        if stray:
            raise SystemExit(
                f"{theirs}: {len(stray):,} coded message(s) are not in {tables_dir}'s messages."
            )


def pack_facts(
    pack_dir: Path,
    text_tables: list[str] | None = None,
    kinds: tuple[str, ...] | list[str] = FEDERAL_ONLY,
) -> dict[str, int]:
    """Counts the card states: messages, authorities, what is withheld or rounded, what has text.

    Every real alert is withheld, has text, or has none in the archive (``no_text_alerts``; most
    are cancellations with no information block, ``no_text_cancels``); every test is withheld,
    has text, or has none here (of a kind whose text the pack leaves out, or with no words).
    """
    text_tables = text_tables or ["text_federal"]
    columns = ["message_id", "cog_id", "text_withheld", "times_rounded", "sender_kind"]
    columns += ["msg_type", "n_infos"]
    alerts = pq.read_table(pack_dir / "alerts" / "messages.parquet", columns=columns).to_pylist()
    tests = pq.read_table(pack_dir / "tests" / "messages.parquet", columns=columns).to_pylist()

    def with_text(config: str, names: list[str]) -> set[str]:
        out: set[str] = set()
        for name in names:
            path = pack_dir / config / f"{name}.parquet"
            out |= set(pq.read_table(path, columns=["message_id"]).column(0).to_pylist())
        return out

    alert_text, test_text = with_text("alerts", text_tables), with_text("tests", text_tables)
    no_text = [r for r in alerts if not r["text_withheld"] and r["message_id"] not in alert_text]
    test_none = [r for r in tests if not r["text_withheld"] and r["message_id"] not in test_text]
    return {
        "real_alerts": len(alerts),
        "tests": len(tests),
        "authorities_with_real_alerts": len({r["cog_id"] for r in alerts}),
        "withheld": sum(1 for r in alerts if r["text_withheld"]),
        "withheld_people_code": sum(1 for r in alerts if r["text_withheld"] == "people_code"),
        "withheld_personal_pattern": sum(
            1 for r in alerts if r["text_withheld"] == "personal_pattern"
        ),
        "withheld_missing_person": sum(1 for r in alerts if r["text_withheld"] == "missing_person"),
        "withheld_person_described": sum(
            1 for r in alerts if r["text_withheld"] == "person_described"
        ),
        "withheld_removed": sum(1 for r in alerts if r["text_withheld"] == privacy.REMOVED),
        "tests_removed": sum(1 for r in tests if r["text_withheld"] == privacy.REMOVED),
        "rounded": sum(1 for r in alerts if r["times_rounded"]),
        "federal_text_alerts": len(with_text("alerts", ["text_federal"])),
        "text_alerts": len(alert_text),
        "no_text_alerts": len(no_text),
        "no_text_cancels": sum(
            1 for r in no_text if r["msg_type"] == "Cancel" and not r["n_infos"]
        ),
        "text_tests": len(test_text),
        "tests_withheld": sum(1 for r in tests if r["text_withheld"]),
        "tests_no_text": len(test_none),
        "tests_kind_left_out": sum(1 for r in test_none if r["sender_kind"] not in kinds),
    }


#: The reading of what is left after a pack was built: a seeded random sample of released texts
#: read for a phone number or an email address, a description of a person, and a private
#: individual named without being described. Counts only; measured once per version.
PRIVACY_READING: dict[str, Any] = {
    "version": "0.1.0",
    "alerts": 300,
    "tests": 100,
    "seed": 20261121,
    "rounds": 1,
    "contact": 0,
    "described": 0,
    "named": 0,
}


def privacy_reading_sentence(reading: Mapping[str, Any] = PRIVACY_READING) -> str:
    """The card's sentence on the reading of released text, or a plain note that none was made."""
    if not reading:
        return "No reading of a sample of the released text has been made for this version."
    rounds = reading["rounds"]
    how = (
        "read once"
        if rounds == 1
        else f"read in the last of {rounds} rounds (after each earlier round the patterns were "
        "widened and the pack rebuilt)"
    )
    return (
        f"After this version was built, a random sample of {reading['alerts']:,} released "
        f"alert texts and {reading['tests']:,} released test texts was {how}: "
        f"{reading['contact']} held a phone number or an email address, {reading['described']} "
        f"described a person, and {reading['named']} named a private individual without "
        "describing them (officials who sign or speak are not counted). A sample this size can "
        "miss a rare form, so the rules can still let one through; the removal route below is "
        "there for that."
    )


def card(manifest: Mapping[str, Any]) -> str:
    """The dataset card: the tracked template with the pack's measured sizes filled in."""
    template = resources.files("warntext").joinpath(CARD_TEMPLATE).read_text(encoding="utf-8")
    by = {f["path"]: f for f in manifest["files"]}
    values = {
        "version": manifest["version"],
        "until": citation.bound_words(manifest["records_sent_before"]),
        "retrieved": manifest["retrieved"],
        "total_rows": f"{manifest['rows']:,}",
        "total_mb": _mb(manifest["bytes"]),
        "terms_url": TERMS_URL,
        "citation": citation.apa(manifest["version"]),
        "bibtex": citation.bibtex(manifest["version"]),
        "software_sentence": citation.software_sentence(manifest["version"]),
    }
    for key, n in manifest.get("facts", {}).items():
        values[key] = f"{n:,}"
    version = manifest_version(manifest)
    values.update(code_tables(version))
    values["codes_section"] = codes_section(version, values)
    values["language_limit"] = LANGUAGE_LIMIT[version]
    values.update(text_sections(manifest))
    values["size_category"] = size_category(manifest["rows"])
    values.update(text_sentences(manifest.get("facts", {})))
    values["privacy_reading"] = privacy_reading_sentence()
    for path, f in by.items():
        key = path.replace("/", "_").replace(".parquet", "")
        values[f"{key}_rows"] = f"{f['rows']:,}"
        values[f"{key}_mb"] = _mb(f["bytes"])
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), template)


#: What each text table holds, for the card.
TEXT_TABLE_WORDS = {
    "text_federal": "the text of federal senders' messages",
    "text_other": (
        "the text of state, local, tribal, territorial and unknown-kind senders' messages"
    ),
}


def text_sections(manifest: Mapping[str, Any]) -> dict[str, str]:
    """The card's text-table configs (YAML) and size rows, for the tables this pack holds."""
    by = {f["path"]: f for f in manifest["files"]}
    configs, rows = [], []
    for name in manifest.get("text_tables", ["text_federal"]):
        configs += [f"- config_name: {name}", "  data_files:"]
        cells = []
        for config in CONFIGS:
            path = f"{config}/{name}.parquet"
            if path in by:
                configs += [f"  - split: {config}", f"    path: {path}"]
                cells.append(f"{by[path]['rows']:,}")
            else:
                cells.append("")
        rows.append(f"| `{name}` | {cells[0]} | {cells[1]} | {TEXT_TABLE_WORDS[name]} |")
    return {"text_configs": "\n".join(configs), "text_size_rows": "\n".join(rows)}


def text_sentences(facts: Mapping[str, int]) -> dict[str, str]:
    """The card's sentences that make the counts add up: alerts and tests without text."""
    n, cancels = facts.get("no_text_alerts", 0), facts.get("no_text_cancels", 0)
    if not n:
        alerts = ""
    elif cancels == n:
        alerts = (
            f"The other {n:,} real alerts carry no words in the archive: each is a cancellation "
            "with no information block, which only points to the message it cancels."
        )
    else:
        alerts = (
            f"The other {n:,} real alerts carry no words in the archive ({cancels:,} of them "
            "cancellations with no information block, which only point to the message they "
            "cancel)."
        )
    none, left = facts.get("tests_no_text", 0), facts.get("tests_kind_left_out", 0)
    tests = f"Of the {facts.get('tests', 0):,} tests, {facts.get('tests_withheld', 0):,} have their"
    tests += " text withheld by the same rules"
    if none and left == none:
        tests += f", and {none:,} are of a sender kind whose text this version leaves out."
    elif none:
        tests += (
            f", and {none:,} have no text here ({left:,} of a sender kind whose text this "
            "version leaves out)."
        )
    else:
        tests += "."
    removed, removed_tests = facts.get("withheld_removed", 0), facts.get("tests_removed", 0)
    removal = ""
    if removed or removed_tests:
        removal = (
            f" In this version {removed:,} real alert(s) and {removed_tests:,} test(s) have their "
            "text withheld only because a removal was asked for."
        )
    return {
        "no_text_sentence": alerts,
        "tests_text_sentence": tests,
        "removed_sentence": removal,
    }


def code_tables(version: str = CODE_STATUS_VERSION) -> dict[str, str]:
    """The card's code tables and lists for one codebook version, from the tracked status file.

    Version 1's table gives the first hand sheet's alpha and agreement. From version 3 on, each
    content code has both figures of the rule for release, each with its 95% interval: alpha
    against the rules on the version's blind sheet, and the coder's consistency with himself on
    the recheck copy; ``validated`` marks the content codes released."""
    status = code_status(version)
    if version == "1":
        sheet = [
            f"| `{c}` | {r['hand_sheet_alpha']} | {r['hand_sheet_agreement']} | {r['status']} |"
            for c, r in status.items()
            if r["hand_sheet_alpha"]
        ]
        table = ["| code | alpha | agreement | in this release |", "|---|---:|---:|---|", *sheet]
    else:
        table = [
            "| code | alpha on the sheet | 95% interval | the coder's consistency | 95% interval "
            "| in this release |",
            "|---|---:|---|---:|---|---|",
        ]
        for c in CONTENT_CODES:
            r = status[c]
            word = "validated" if r["status"] == "released" else "experimental"
            table.append(
                f"| `{c}` | {r['hand_sheet_alpha']} | {r['alpha_low']} to {r['alpha_high']} "
                f"| {r['recheck_alpha']} | {r['recheck_low']} to {r['recheck_high']} | {word} |"
            )
    released = [f"`{c}`" for c, r in status.items() if r["status"] == "released"]
    left = [f"`{c}`" for c, r in status.items() if r["status"] == "experimental"]
    validated = [f"`{c}`" for c in CONTENT_CODES if status[c]["status"] == "released"]
    mechanical = [f"`{c}`" for c, r in status.items() if r["status"] == "released"]
    mechanical = [c for c in mechanical if c not in validated]
    return {
        "code_alpha_table": "\n".join(table),
        "codes_released": ", ".join(released),
        "codes_left_out": ", ".join(left),
        "codes_validated": ", ".join(validated) or "none",
        "codes_mechanical": ", ".join(mechanical),
    }


#: The card's "Codes" section for each codebook version, a template of its own.
CODES_SECTION_FILE = "card_codes_v{version}.md"
#: The card's Limits bullet on the rules' language check, by codebook version.
LANGUAGE_LIMIT = {
    "1": "- **The language check finds Spanish only.** A text in another language under an "
    "English label\n  is coded as English.",
    "3": "- **The language check is by rule.** A text written mostly in another script, or with "
    "enough common\n  words of Spanish or of another language often sent beside English, is not "
    "coded; a short\n  text in another language can still be coded as English.",
}


def codes_section(version: str, values: Mapping[str, str]) -> str:
    """The card's "Codes" section for a codebook version, with its placeholders filled."""
    name = CODES_SECTION_FILE.format(version=version)
    path = resources.files("warntext").joinpath(name)
    if not path.is_file():
        raise SystemExit(
            f"{name} is missing: write the card's Codes section for version {version}."
        )
    text = path.read_text(encoding="utf-8").rstrip("\n")
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values.get(m.group(1), m.group(0)), text)


def card_metadata_problems(
    text: str, tables: list[str] | tuple[str, ...] | None = None, rows: int | None = None
) -> list[str]:
    """What the card's YAML header lacks for Hugging Face (license fields, configs), and raw tags.

    ``tables`` are the pack's tables (the record layer and its text tables); each needs a config,
    and no other text table may have one.
    """
    tables = list(tables) if tables is not None else pack_tables(TEXT_KINDS)
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
    if re.search(r"\{\{\w+\}\}", text):  # a BibTeX title's {{Name} is not one
        out.append("the card still holds a placeholder")
    if rows is not None and f"size_categories:\n- {size_category(rows)}\n" not in head + "\n":
        out.append(f"size_categories must be {size_category(rows)}, for {rows:,} rows in all")
    for name in tables:
        if f"config_name: {name}" not in head:
            out.append(f"no config for {name}")
    for name in sorted(set(TEXT_TABLES) - set(tables)):
        if f"config_name: {name}" in head:
            out.append(f"a config for {name}, which this pack does not hold")
    out += hfpage.tag_problems("the card", text)
    return out


def rewrite_card(pack_dir: Path | str) -> bool:
    """A card-only fix: README.md written again from the template and the pack's own files.

    The facts the card states are measured again from the pack's data files (which the check
    holds to the manifest by hash), so a card can state a count the manifest of an earlier build
    does not list; a count the manifest does list must agree. The data files and the manifest
    are not touched. Returns whether the card changed.
    """
    pack_dir = Path(pack_dir)
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    kinds = manifest.get("text_kinds", list(FEDERAL_ONLY))
    measured = pack_facts(pack_dir, manifest.get("text_tables"), kinds)
    listed = manifest.get("facts", {})
    differ = sorted(k for k in set(listed) & set(measured) if listed[k] != measured[k])
    if differ:
        raise SystemExit(
            f"The manifest's facts {differ} differ from the pack's files; rebuild the pack "
            "instead of rewriting its card."
        )
    readme = pack_dir / "README.md"
    before = readme.read_text(encoding="utf-8") if readme.exists() else None
    text = card({**manifest, "facts": {**listed, **measured}})
    readme.write_text(text, encoding="utf-8")
    return text != before


def check_pack(
    pack_dir: Path | str,
    sender_values: list[str],
    identifiers: list[str],
    server_counts: Mapping[int, int] | None,
    removals: Iterable[str] | None = None,
) -> list[str]:
    """Every rule the pack must pass; returns the failures (empty when it passes).

    ``removals`` (by default the tracked removal list) are read now, so a pack built before an
    entry was added fails."""
    pack_dir = Path(pack_dir)
    fail: list[str] = []
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"{manifest_path} is missing; build the pack with `warntext release build`."]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    text_tables = list(manifest.get("text_tables", ["text_federal"]))
    kinds = list(manifest.get("text_kinds", FEDERAL_ONLY))
    version = manifest_version(manifest)
    if text_tables != text_tables_for(kinds):
        fail.append(f"manifest.json: text tables {text_tables} do not match the kinds {kinds}.")
    tables = [*RECORD_TABLES, *text_tables]
    listed = {f["path"]: f for f in manifest["files"]}
    readable: set[str] = set()
    for path in sorted(p for p in pack_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(pack_dir).as_posix()
        if rel in ALLOWED_FILES:
            continue
        parts = rel.split("/")
        name = parts[-1].removesuffix(".parquet")
        if name.startswith("text_") and name not in text_tables:
            fail.append(
                f"{rel}: a text table this pack does not release (its manifest releases "
                f"{', '.join(text_tables)})."
            )
        elif len(parts) != 2 or parts[0] not in CONFIGS or name not in tables:
            fail.append(f"{rel}: not a file of the release; remove it.")
        elif rel not in listed:
            fail.append(f"{rel}: not in the manifest.")
        else:
            data = path.read_bytes()
            if durable.sha256_bytes(data) != listed[rel]["sha256"]:
                fail.append(f"{rel}: does not match its SHA-256 in the manifest.")
            if pq.read_metadata(path).num_rows != listed[rel]["rows"]:
                fail.append(f"{rel}: its row count differs from the manifest's.")
            if not pq.read_schema(path).equals(
                expected_schema(name, version), check_metadata=False
            ):
                fail.append(f"{rel}: its columns are not those of a released {name} table.")
            else:
                readable.add(rel)
    for rel in listed:
        if not (pack_dir / rel).exists():
            fail.append(f"{rel}: in the manifest but missing.")
    codes = pack_dir / "alerts" / "codes.parquet"
    if codes.exists():
        left = sorted(set(pq.read_schema(codes).names) & set(experimental_codes(version)))
        if left:
            fail.append(f"alerts/codes.parquet: experimental codes are in it: {left}.")
    readme = pack_dir / "README.md"
    if not readme.exists():
        fail.append("README.md (the dataset card) is missing.")
    else:
        problems = card_metadata_problems(readme.read_text("utf-8"), tables, manifest.get("rows"))
        fail += [f"README.md: {p}" for p in problems]
    # The tables' release check, on everything in the pack (stray files are flagged above).
    loaded: dict[str, dict[str, list]] = {}
    for config in CONFIGS:
        loaded[config] = {}
        for name in RELEASED_TABLES:
            rel = f"{config}/{name}.parquet"
            path = pack_dir / rel
            loaded[config][name] = pq.read_table(path).to_pylist() if rel in readable else []
    fail += ck.check(loaded, sender_values, server_counts, identifiers, removals)
    fail += text_problems(loaded, kinds, removals)
    return fail


#: The privacy rules a message's text can be withheld by, each read from its record-layer row.
WITHHOLDING_RULES = {
    "a people code": lambda m: bool(set(m.get("event_codes") or []) & privacy.PEOPLE_CODES),
    "the missing-person rule": lambda m: bool(m.get("about_missing_person")),
    "the pattern rule": lambda m: bool(m.get("withheld_patterns")),
    "the description rule": lambda m: privacy.DESCRIBED in (m.get("withheld_patterns") or []),
    "the withheld flag": lambda m: bool(m.get("text_withheld")),
}


def text_problems(
    tables: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    kinds: list[str] | tuple[str, ...],
    removals: Iterable[str] | None = None,
) -> list[str]:
    """The text layer's own rules, in both splits; counts and rule names only, never text.

    - no text row for a message that any privacy rule withholds (a people code, the
      missing-person rule, the pattern rule) or that the removal list names (``removals``, by
      default the tracked list), and every such message is marked withheld;
    - every text row of a released kind, with its credit: the message's alerting authority
      (FEMA's identifier and the released organization name) and the credit line;
    - no personal-detail pattern (a phone number or an email address in any form, the rest)
      and no missing-person wording in any released text field, and no message whose released
      text fields, read together, describe a person.
    """
    fail: list[str] = []
    removal_ids = privacy.load_removals() if removals is None else frozenset(removals)
    rules = {
        **WITHHOLDING_RULES,
        "the removal list": lambda m: privacy.on_removal_list(m, removal_ids),
    }
    for config in CONFIGS:
        messages = {m["message_id"]: m for m in tables[config].get("messages", [])}
        unmarked = sum(
            1
            for m in messages.values()
            if not m.get("text_withheld") and any(rule(m) for rule in rules.values())
        )
        if unmarked:
            fail.append(
                f"{config}/messages: {unmarked} message(s) meet a privacy rule but are not marked "
                "withheld; rebuild the tables."
            )
        for name in TEXT_TABLES:
            rows = tables[config].get(name, [])
            if not rows:
                continue
            for label, rule in rules.items():
                n = sum(1 for r in rows if rule(messages.get(r["message_id"], {})))
                if n:
                    fail.append(
                        f"{config}/{name}: {n} text row(s) for messages withheld by {label}."
                    )
            wrong_kind = sum(1 for r in rows if r.get("sender_kind") not in kinds)
            if wrong_kind:
                fail.append(
                    f"{config}/{name}: {wrong_kind} row(s) of a kind this pack does not "
                    f"release (it releases {', '.join(kinds)})."
                )
            no_credit = 0
            for r in rows:
                m = messages.get(r["message_id"], {})
                want = credit_line(m.get("cog_id"), m.get("organization") or None)
                if (
                    not r.get("credit")
                    or r.get("credit") != want
                    or r.get("cog_id") != m.get("cog_id")
                    or (r.get("organization") or None) != (m.get("organization") or None)
                ):
                    no_credit += 1
            if no_credit:
                fail.append(
                    f"{config}/{name}: {no_credit} row(s) without their credit (the alerting "
                    "authority's FEMA ID and released name, and the credit line)."
                )
            found: dict[str, int] = {}
            by_message: dict[str, list[str]] = {}
            for r in rows:
                for field in TEXT_FIELDS:
                    value = r.get(field)
                    for cell in value if isinstance(value, list) else [value]:
                        if not isinstance(cell, str) or not cell:
                            continue
                        by_message.setdefault(r["message_id"], []).append(cell)
                        hits = [p for p, hit in patterns.present(cell).items() if hit]
                        if privacy.MISSING_PERSON.search(cell):
                            hits.append("missing_person")
                        for h in hits:
                            found[f"{field}:{h}"] = found.get(f"{field}:{h}", 0) + 1
            if found:
                fail.append(
                    f"{config}/{name}: released text matches personal-detail patterns or "
                    f"missing-person wording: {found}"
                )
            described = sum(1 for cells in by_message.values() if patterns.describes_person(cells))
            if described:
                fail.append(
                    f"{config}/{name}: the released text of {described} message(s) describes a "
                    "person (two or more elements of a description)."
                )
    return fail


# --- the Kaggle mirror: the record layer and the codes, no text ---------------------------

KAGGLE_ID = kaggle_meta.KAGGLE_ID
KAGGLE_TABLES = RECORD_TABLES
#: Kaggle's limits, which its command line enforces only when the dataset is created.
KAGGLE_TITLE = kaggle_meta.KAGGLE_TITLE
KAGGLE_SUBTITLE = kaggle_meta.KAGGLE_SUBTITLE


def _kaggle_metadata(pack_dir: Path) -> dict[str, Any]:
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    card = (pack_dir / "README.md").read_text(encoding="utf-8")
    return kaggle_meta.metadata(manifest, card, KAGGLE_TABLES)


def _write_kaggle_page(pack_dir: Path, out_dir: Path) -> dict[str, Any]:
    """Write the folder's metadata and cover; return the metadata."""
    meta = _kaggle_metadata(pack_dir)
    (out_dir / kaggle_meta.METADATA_NAME).write_text(json.dumps(meta, indent=1) + "\n", "utf-8")
    (out_dir / kaggle_meta.COVER_NAME).write_bytes(cover.png(cover.draw()))
    return meta


def build_kaggle(pack_dir: Path | str, out_dir: Path | str) -> dict[str, Any]:
    """The Kaggle mirror's folder: flat copies of the record-layer files, its metadata, cover.

    It holds no text table: the mirror carries the record layer and the released codes only, and
    points to the Hugging Face dataset for the text.
    """
    pack_dir, out_dir = Path(pack_dir), Path(out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"{out_dir} is not empty; the mirror's folder is built once.")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    for f in kaggle_meta.kaggle_files(manifest, KAGGLE_TABLES):
        shutil.copyfile(pack_dir / f["path"], out_dir / f["flat"])
    return _write_kaggle_page(pack_dir, out_dir)


def _kaggle_data_problems(out_dir: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Every mirror file present and equal to the pack's file by SHA-256."""
    fail = []
    for f in kaggle_meta.kaggle_files(manifest, KAGGLE_TABLES):
        path = out_dir / f["flat"]
        if not path.exists():
            fail.append(f"kaggle/{f['flat']} is missing; the pack has {f['path']}.")
        elif durable.sha256_file(path) != f["sha256"]:
            fail.append(
                f"kaggle/{f['flat']} differs from the pack's {f['path']} (SHA-256); the mirror's "
                "data files are copies of the pack's and are never rebuilt."
            )
    return fail


def rewrite_kaggle(pack_dir: Path | str, out_dir: Path | str) -> dict[str, bool]:
    """The mirror's metadata and cover written again; its data files are checked, not touched.

    Stops before writing when a data file differs from the pack's manifest, and checks them again
    after. Returns which of the two files changed.
    """
    pack_dir, out_dir = Path(pack_dir), Path(out_dir)
    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    bad = _kaggle_data_problems(out_dir, manifest)
    if bad:
        raise SystemExit("Nothing was written: " + " ".join(bad))
    names = (kaggle_meta.METADATA_NAME, kaggle_meta.COVER_NAME)
    before = {n: (out_dir / n).read_bytes() if (out_dir / n).exists() else None for n in names}
    _write_kaggle_page(pack_dir, out_dir)
    bad = _kaggle_data_problems(out_dir, manifest)
    if bad:  # pragma: no cover - the data files are only read above
        raise SystemExit("A data file changed while the metadata was written: " + " ".join(bad))
    return {n: (out_dir / n).read_bytes() != before[n] for n in names}


def check_kaggle(out_dir: Path | str, manifest: Mapping[str, Any] | None = None) -> list[str]:
    """The mirror holds record-layer files, its metadata and its cover only; with the pack's
    manifest, every data file is the pack's own by SHA-256."""
    out_dir = Path(out_dir)
    fail = []
    for path in sorted(p for p in out_dir.rglob("*") if p.is_file()):
        name = path.name
        if name in (kaggle_meta.METADATA_NAME, kaggle_meta.COVER_NAME):
            continue
        base = name.removesuffix(".parquet")
        config, _, table = base.partition("-")
        if config not in CONFIGS or table not in KAGGLE_TABLES or not name.endswith(".parquet"):
            fail.append(f"kaggle/{name}: not a record-layer file; the mirror holds no text.")
    meta_path = out_dir / kaggle_meta.METADATA_NAME
    if not meta_path.exists():
        fail.append(f"kaggle/{kaggle_meta.METADATA_NAME} is missing.")
    else:
        fail += kaggle_metadata_problems(json.loads(meta_path.read_text(encoding="utf-8")))
    fail += kaggle_meta.cover_problems(out_dir / kaggle_meta.COVER_NAME)
    if manifest is not None:
        fail += _kaggle_data_problems(out_dir, manifest)
    return fail


def kaggle_metadata_problems(meta: Mapping[str, Any]) -> list[str]:
    """The mirror's metadata: Kaggle's lengths, its id, the description's headings and "How to
    cite", tags from Kaggle's list, the update frequency, the sources, no raw tag."""
    return kaggle_meta.problems(meta)
