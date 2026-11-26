"""The Kaggle mirror's page: its description, tags, sources, file descriptions and cover.

The mirror holds the record layer and the released codes, never message text. Its description
is built from the pack's manifest and from sections lifted from the pack's own card (the opening
box, "What it is not", "Alerts about people", "Limits", "Terms that users must follow" and "How
to cite"), so a change to the card template reaches the Kaggle page the next time this folder is
written, the DOI included.

**What the command line can set.** ``kaggle datasets create`` sends the title, subtitle,
description, license and tags; the sources, the update frequency and the cover image go only
through ``kaggle datasets metadata --update``, which sends this same file (and the cover, by its
name next to it) and blanks the sources when the file has none. Kaggle keeps no file
description sent by the command line, and its Authors, Coverage, Collection methodology and
Citations fields are set on the website only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from warntext import access, authorities, citation, hfpage
from warntext.cover import HEIGHT, WIDTH, png_size

KAGGLE_ID = "obadakraishan/warntext"
TITLE = "WarnText: US public alert records"
SUBTITLE = "The record layer and content codes of US public alert messages (IPAWS)"
#: Kaggle's limits, which its command line enforces only when the dataset is created.
KAGGLE_TITLE = (6, 50)
KAGGLE_SUBTITLE = (20, 80)
HF_URL = "https://huggingface.co/datasets/obadakr/warntext"
REPO_URL = "https://github.com/obadaKraishan/warntext"
REMOVAL_URL = f"{REPO_URL}/issues/new/choose"
KAGGLE_INPUT = "/kaggle/input/warntext"
SOURCE_ENDPOINT = "https://www.fema.gov/api/open/v1/IpawsArchivedAlerts"

#: The description's second-level headings, in this order.
HEADINGS = (
    "What WarnText is",
    "What it is not",
    "What is inside",
    "Load one table",
    "Alerts about people",
    "Limits",
    "Terms that users must follow",
    "How to cite",
    "Links",
)
#: The headings of a version with the easy-access layer (0.2.0 on): "Start here" first.
HEADINGS_LAYERED = ("Start here", *HEADINGS)
#: Sections lifted word for word from the pack's card (heading on the card, heading here).
FROM_CARD = (
    ("What it is not", "What it is not"),
    ("Alerts about people", "Alerts about people"),
    ("Limits", "Limits"),
    ("Terms that users must follow", "Terms that users must follow"),
    ("How to cite", "How to cite"),
)
#: Kaggle publishes no length limit for a description; this is the project's own cap.
DESCRIPTION_MAX = 20_000
#: "not specified" for release 0.1.0 (no schedule was promised then); from 0.2.0 the mirror is
#: refreshed by hand about once a month.
UPDATE_FREQUENCY = "not specified"
UPDATE_FREQUENCY_LAYERED = "monthly"
#: Kaggle's tags, each seen as a tag on public Kaggle datasets in Kaggle's own dataset listing
#: (2026-11-23). Kaggle refuses a whole metadata update over one keyword that is not one of its
#: tags, so the check fails on any other keyword.
KAGGLE_TAGS = ("public safety", "natural disasters", "government", "social science", "tabular")
#: The name the Kaggle CLI looks for next to dataset-metadata.json (and never uploads as a file).
COVER_NAME = "dataset-cover-image.png"
METADATA_NAME = "dataset-metadata.json"

_TABLES = {
    "messages": "One row per message: its alerting authority (FEMA's identifier and the "
    "organization's name), the kind of sender, its time, status, type and event codes, its "
    "places (area codes, states, counties), the channels it asked for, and measures of its text.",
    "infos": "One row per language block of a message: categories, urgency, severity and "
    "certainty, its times, and the parameters the release allows.",
    "areas": "One row per area block: area codes, and the shapes where the privacy rules allow "
    "them.",
    "references": "One row per link from an update or a cancellation to an earlier message, "
    "and whether it was resolved.",
    "threads": "One row per alert with its updates and cancellations: first and last time, "
    "number of messages.",
    "codes": "One row per text unit of a real alert (the 90- and 360-character phone texts "
    "and the full text): the codes this version releases. The six content codes are "
    "experimental in this version and left out.",
}
#: The codes file's description from codebook version 3 on: which content codes are validated.
_CODES_V3 = (
    "One row per text unit of a real alert (the 90- and 360-character phone texts and the full "
    "text): the codes this version releases, among them the content codes validated against a "
    "coder's blind sheet ({validated}); the other content codes are experimental and left out."
)
_SPLITS = {
    "alerts": "Real alerts",
    "tests": "Tests and demonstrations",
}


def flat_name(path: str) -> str:
    """The Kaggle file name of a pack path: ``alerts/messages.parquet`` -> ``alerts-messages``."""
    config, name = path.removesuffix(".parquet").split("/")
    return f"{config}-{name}.parquet"


#: The easy-access files' descriptions on Kaggle.
_LAYER = {
    access.START_HERE: "Start here: every message of this version, real alerts and tests "
    "together (config says which), one row each, with text_status. No message words: the words "
    "are in the Hugging Face copy.",
    access.XLSX_WHOLE: "The start-here rows as an Excel workbook, with a Read me sheet and a "
    "Fields sheet. No message words.",
    access.XLSX_SAMPLE: "A seeded sample of 1,000 start-here rows as an Excel workbook (the whole "
    "table is too large for one), with a Read me sheet and a Fields sheet. No message words.",
    access.FIELDS_FILE: "Every column of every table: its type, meaning and allowed values.",
    access.CODEBOOK_FILE: "The six content codes: their definitions, which are validated, and "
    "the two figures of the rule for release.",
}


def file_description(flat: str, version: str = "1") -> str:
    """One description per Kaggle file, from its split and table (no text in any file); the
    codes file's names the content codes validated in its codebook ``version``."""
    if flat in _LAYER:
        return _LAYER[flat]
    if flat.endswith(".csv.gz"):
        base = flat.removesuffix(".csv.gz")
        return f"{file_description(base + '.parquet', version)} As a gzipped CSV."
    split, _, table = flat.removesuffix(".parquet").partition("-")
    words = _TABLES[table]
    if table == "codes" and version != "1":
        from warntext import release

        status = release.code_status(version)
        validated = [c for c in release.CONTENT_CODES if status[c]["status"] == "released"]
        words = _CODES_V3.format(validated=", ".join(f"`{c}`" for c in validated) or "none")
    return f"{_SPLITS[split]}. {words} No message text."


def card_section(card: str, heading: str) -> str:
    """The body of the card's ``## heading`` section, up to the next second-level heading."""
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", card, re.M | re.S)
    if not m:
        raise SystemExit(
            f"The pack's card has no '## {heading}' section; rebuild the card with "
            "`warntext release card` before writing the Kaggle folder."
        )
    return m.group(1).strip()


def how_to_cite(manifest: Mapping[str, Any], card: str) -> str:
    """WarnText's own citation first, then the card's "How to cite" (FEMA's credit) under it.
    Once the card opens that section with the citation itself, it is not given twice."""
    section = card_section(card, "How to cite")
    if citation.TITLE in section:
        return section
    return f"{citation.apa(manifest['version'], citation.year_of(dict(manifest)))}\n\n{section}"


def card_box(card: str) -> str:
    """The card's opening box: the first paragraph after its title."""
    m = re.search(r"^# WarnText\n\n(.+?)\n\n", card, re.M | re.S)
    if not m:
        raise SystemExit("The pack's card has no opening paragraph under '# WarnText'.")
    return m.group(1).strip()


def kaggle_files(manifest: Mapping[str, Any], tables: tuple[str, ...]) -> list[dict[str, Any]]:
    """The manifest's entries of the mirror's files, with their flat names."""
    out = []
    for f in manifest["files"]:
        table = f["path"].removesuffix(".parquet").split("/")[1]
        if table in tables:
            out.append({**f, "flat": flat_name(f["path"])})
    return out


def description(manifest: Mapping[str, Any], card: str, tables: tuple[str, ...]) -> str:
    """The Kaggle description in Markdown, with the headings of ``HEADINGS``."""
    facts = manifest["facts"]
    files = kaggle_files(manifest, tables)
    rows = sum(f["rows"] for f in files)
    size = sum(f["bytes"] for f in files)
    before = citation.bound_words(str(manifest["records_sent_before"]))
    layered = bool(manifest.get("access_files"))
    lines = [
        f"# WarnText {manifest['version']}: the record layer",
        "",
        card_box(card),
        "",
        *([access.start_here_section(manifest, kaggle=True), ""] if layered else []),
        "## What WarnText is",
        "WarnText is a research corpus of the public alert messages that US federal, state, "
        "local, tribal and territorial alerting authorities sent through the Integrated Public "
        "Alert and Warning System (IPAWS), read from FEMA's OpenFEMA dataset \"IPAWS Archived "
        f'Alerts" (version 1). Version {manifest["version"]} holds every message in that '
        "archive from senders other than the National Weather Service, sent before "
        f"{before}: **{facts['real_alerts']:,} real alerts** from "
        f"{facts['authorities_with_real_alerts']:,} alerting authorities and "
        f"**{facts['tests']:,} tests and demonstrations**.",
        "",
        "**This Kaggle mirror holds the record layer and the released codes only, never "
        "message text.** The text layer (for the alerts that are not about people), the full "
        f"dataset card, the terms and the removal route are on Hugging Face ({HF_URL}); the "
        f"code, the method, the schema and the codebook are on GitHub ({REPO_URL}).",
        "",
        "## What it is not",
        card_section(card, "What it is not"),
        "",
        "## What is inside",
        "| file | rows | what it holds |",
        "|---|---:|---|",
        *(
            f"| `{r['path']}` | {r['rows']:,} | {r['description']} |"
            for r in resources(manifest, tables)
        ),
        "",
        f"In all {rows:,} rows, {size / 1_000_000:.1f} MB as Parquet. Every table carries FEMA's "
        "record id (`record_id`); messages, language blocks, areas, references and codes join "
        "on `message_id`. The text tables (`text_federal`, `text_other`) are on Hugging Face "
        "only; anyone can rebuild the text of the messages that are not withheld from FEMA's "
        "API by record id with the project's `warntext text` command.",
        "",
        "## Load one table",
        "```python",
        "import pandas as pd",
        "",
        f'messages = pd.read_parquet("{KAGGLE_INPUT}/alerts-messages.parquet")',
        f'codes = pd.read_parquet("{KAGGLE_INPUT}/alerts-codes.parquet")',
        'print(len(messages), "real alerts")',
        "```",
        "",
        "## Alerts about people",
        card_section(card, "Alerts about people"),
        "",
        "## Limits",
        card_section(card, "Limits"),
        "",
        "## Terms that users must follow",
        card_section(card, "Terms that users must follow"),
        "",
        "## How to cite",
        how_to_cite(manifest, card),
        "",
        "## Links",
        f"- The dataset with its text layer and card (Hugging Face): {HF_URL}",
        f"- The code, method, schema and codebook (GitHub): {REPO_URL}",
        f"- Ask for a message's text to be removed: {REMOVAL_URL}",
        f"- The source: FEMA's OpenFEMA dataset IPAWS Archived Alerts, {SOURCE_ENDPOINT}",
    ]
    return "\n".join(lines) + "\n"


def sources(manifest: Mapping[str, Any]) -> str:
    """Provenance > Sources on Kaggle (``userSpecifiedSources``; sent with every update)."""
    return (
        "- **The alert messages:** FEMA OpenFEMA Dataset: IPAWS Archived Alerts - v1 "
        f"({SOURCE_ENDPOINT}), retrieved {manifest['retrieved']} (UTC); records sent before "
        f"{citation.bound_words(str(manifest['records_sent_before']))}. This product uses the "
        "Federal Emergency Management Agency's OpenFEMA API, but is not endorsed by FEMA.\n"
        "- **The kinds of sender:** FEMA's list of IPAWS alerting authorities "
        f"({authorities.PAGE_URL}), as its page stood on {authorities.SNAPSHOT_PAGE_UPDATED}, "
        f"read {authorities.SNAPSHOT_RETRIEVED}."
    )


def metadata(manifest: Mapping[str, Any], card: str, tables: tuple[str, ...]) -> dict[str, Any]:
    """The mirror's ``dataset-metadata.json``."""
    return {
        "title": TITLE,
        "id": KAGGLE_ID,
        "subtitle": SUBTITLE,
        "description": description(manifest, card, tables),
        "isPrivate": True,
        "licenses": [{"name": "other"}],
        "keywords": list(KAGGLE_TAGS),
        "expectedUpdateFrequency": (
            UPDATE_FREQUENCY_LAYERED if manifest.get("access_files") else UPDATE_FREQUENCY
        ),
        "userSpecifiedSources": sources(manifest),
        "resources": [
            {"path": r["path"], "description": r["description"]}
            for r in resources(manifest, tables)
        ],
    }


def resources(manifest: Mapping[str, Any], tables: tuple[str, ...]) -> list[dict[str, Any]]:
    """The mirror's files in the order a reader meets them: the start-here file, the workbook
    and the two catalogues first, then each table's Parquet file and its gzipped CSV."""
    version = str(manifest.get("codebook_version", "1"))
    layer = access.kaggle_files(manifest, tables)
    top = [n for n in layer if not n.endswith(".csv.gz")]
    by = {f["path"]: f for f in manifest.get("access_files") or []}
    out = [{"path": n, "rows": by[n]["rows"]} for n in top]
    for f in kaggle_files(manifest, tables):
        out.append({"path": f["flat"], "rows": f["rows"]})
        gz = f["flat"].replace(".parquet", ".csv.gz")
        if gz in layer:
            out.append({"path": gz, "rows": f["rows"]})
    for r in out:
        r["description"] = file_description(r["path"], version)
    return out


def headings(text: str) -> list[str]:
    """The second-level headings of a Markdown text, outside code blocks."""
    out, code = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            code = not code
        elif not code and line.startswith("## "):
            out.append(line[3:].strip())
    return out


def problems(meta: Mapping[str, Any]) -> list[str]:
    """Everything Kaggle or this project asks of the metadata, one plain message per problem."""
    name = METADATA_NAME
    out = []
    for field, (low, high) in (("title", KAGGLE_TITLE), ("subtitle", KAGGLE_SUBTITLE)):
        n = len(meta.get(field) or "")
        if not low <= n <= high:
            out.append(
                f"kaggle/{name}: the {field} has {n} characters; Kaggle takes {low} to {high}."
            )
    if meta.get("id") != KAGGLE_ID:
        out.append(f"kaggle/{name}: the id is {meta.get('id')!r}, not {KAGGLE_ID}.")
    text = meta.get("description") or ""
    out += hfpage.tag_problems(f"kaggle/{name} description", text)
    if len(text) > DESCRIPTION_MAX:
        out.append(
            f"kaggle/{name}: the description has {len(text):,} characters; the cap is "
            f"{DESCRIPTION_MAX:,}."
        )
    found = headings(text)
    want = list(HEADINGS_LAYERED if "Start here" in found else HEADINGS)
    if found != want:
        out.append(
            f"kaggle/{name}: the description's headings are {found}; they must be "
            f"{want}, in that order (write the folder again with "
            "`warntext release kaggle-meta`)."
        )
    elif not re.search(r"^## How to cite\n+(?!## )\S", text, re.M):
        out.append(f"kaggle/{name}: the description's 'How to cite' section is empty.")
    elif not re.search(
        rf"^## How to cite\n+{re.escape(citation.AUTHOR_APA)} \(\d{{4}}\)\. .*"
        rf"\(Version [^)]+\) \[Data set\]\. .*{re.escape(citation.URL)}",
        text,
        re.M,
    ):
        out.append(
            f"kaggle/{name}: the description's 'How to cite' does not open with WarnText's own "
            "citation (author, year, title, version, Hugging Face address)."
        )
    keywords = list(meta.get("keywords") or [])
    if not keywords:
        out.append(f"kaggle/{name}: no tags; give at least one of {list(KAGGLE_TAGS)}.")
    unknown = [k for k in keywords if k not in KAGGLE_TAGS]
    if unknown:
        out.append(
            f"kaggle/{name}: the tags {unknown} are not on the list of Kaggle tags checked for "
            f"this mirror ({list(KAGGLE_TAGS)}); Kaggle refuses a whole update over one unknown "
            "tag."
        )
    if len(set(keywords)) != len(keywords):
        out.append(f"kaggle/{name}: a tag is given twice.")
    frequency = UPDATE_FREQUENCY_LAYERED if "Start here" in found else UPDATE_FREQUENCY
    if meta.get("expectedUpdateFrequency") != frequency:
        out.append(
            f"kaggle/{name}: the update frequency is {meta.get('expectedUpdateFrequency')!r}, "
            f"not {frequency!r} (0.1.0 promised no schedule; from 0.2.0 the mirror is refreshed "
            "by hand about once a month)."
        )
    src = meta.get("userSpecifiedSources") or ""
    if SOURCE_ENDPOINT not in src:
        out.append(
            f"kaggle/{name}: the sources do not name the OpenFEMA endpoint; an update without "
            "them blanks the sources on Kaggle."
        )
    if meta.get("licenses") != [{"name": "other"}]:
        out.append(f"kaggle/{name}: the license is {meta.get('licenses')!r}, not 'other'.")
    for r in meta.get("resources") or []:
        if not (r.get("description") or "").strip():
            out.append(f"kaggle/{name}: the file {r.get('path')} has no description.")
    return out


def cover_problems(path: Path) -> list[str]:
    """The cover must be a PNG of exactly 560 by 280 pixels (Kaggle's crop is fixed)."""
    if not path.exists():
        return [f"kaggle/{COVER_NAME} is missing; write it with `warntext release kaggle-meta`."]
    size = png_size(path.read_bytes())
    if size != (WIDTH, HEIGHT):
        return [
            f"kaggle/{COVER_NAME}: the image is {size or 'not a PNG'}; it must be a PNG of "
            f"{WIDTH} by {HEIGHT} pixels, because Kaggle crops it from the top left corner."
        ]
    return []


#: What a metadata update takes from the pack; the title, subtitle and license must already be
#: the pack's, and the visibility is the live page's, given explicitly.
FROM_PACK = (
    "description",
    "keywords",
    "expectedUpdateFrequency",
    "userSpecifiedSources",
    "resources",
)


def update_settings(
    live: Mapping[str, Any], meta: Mapping[str, Any], private: bool
) -> tuple[dict[str, Any], list[str]]:
    """The file for ``kaggle datasets metadata --update``, from the live settings (as
    ``kaggle datasets metadata`` downloads them, wrapped in ``info`` or not) and the pack's.

    The update sends every field, and a missing ``isPrivate`` makes the dataset public, so the
    visibility is given by the caller (checked signed out) and must agree with the live settings,
    which leave ``isPrivate`` out when it is false. A tag added on the website stays.
    """
    info = live.get("info") or live
    problems = []
    live_private = bool(info.get("isPrivate", False))
    if live_private != private:
        problems.append(
            f"the live settings say the dataset is {'private' if live_private else 'public'}, "
            f"and this update was asked for a {'private' if private else 'public'} one; "
            "nothing is sent."
        )
    for field in ("title", "subtitle"):
        if info.get(field) != meta.get(field):
            problems.append(
                f"the live {field} is {info.get(field)!r}, not the pack's {meta.get(field)!r}; "
                "change it on the website or in the pack first."
            )
    live_licenses = [lic.get("name") for lic in info.get("licenses") or []]
    if live_licenses != [lic["name"] for lic in meta["licenses"]]:
        problems.append(f"the live license is {live_licenses}, not the pack's.")
    out = {
        "id": meta["id"],
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "isPrivate": private,
        "licenses": meta["licenses"],
        **{k: meta[k] for k in FROM_PACK},
    }
    out["keywords"] = list(dict.fromkeys([*meta["keywords"], *(info.get("keywords") or [])]))
    if info.get("collaborators"):
        out["collaborators"] = info["collaborators"]
    return out, problems
