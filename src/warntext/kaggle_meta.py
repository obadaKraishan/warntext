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

from warntext import authorities, hfpage
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
#: "not specified" until the weekly update really runs (no schedule is promised).
UPDATE_FREQUENCY = "not specified"
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
_SPLITS = {
    "alerts": "Real alerts",
    "tests": "Tests and demonstrations",
}


def flat_name(path: str) -> str:
    """The Kaggle file name of a pack path: ``alerts/messages.parquet`` -> ``alerts-messages``."""
    config, name = path.removesuffix(".parquet").split("/")
    return f"{config}-{name}.parquet"


def file_description(flat: str) -> str:
    """One description per Kaggle file, from its split and table (no text in any file)."""
    split, _, table = flat.removesuffix(".parquet").partition("-")
    return f"{_SPLITS[split]}. {_TABLES[table]} No message text."


def card_section(card: str, heading: str) -> str:
    """The body of the card's ``## heading`` section, up to the next second-level heading."""
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", card, re.M | re.S)
    if not m:
        raise SystemExit(
            f"The pack's card has no '## {heading}' section; rebuild the card with "
            "`warntext release card` before writing the Kaggle folder."
        )
    return m.group(1).strip()


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
    before = str(manifest["records_sent_before"])[:10]
    lines = [
        f"# WarnText {manifest['version']}: the record layer",
        "",
        card_box(card),
        "",
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
        *(f"| `{f['flat']}` | {f['rows']:,} | {file_description(f['flat'])} |" for f in files),
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
        card_section(card, "How to cite"),
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
        f"{manifest['records_sent_before']}. This product uses the Federal Emergency Management "
        "Agency's OpenFEMA API, but is not endorsed by FEMA.\n"
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
        "expectedUpdateFrequency": UPDATE_FREQUENCY,
        "userSpecifiedSources": sources(manifest),
        "resources": [
            {"path": f["flat"], "description": file_description(f["flat"])}
            for f in kaggle_files(manifest, tables)
        ],
    }


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
    if found != list(HEADINGS):
        out.append(
            f"kaggle/{name}: the description's headings are {found}; they must be "
            f"{list(HEADINGS)}, in that order (write the folder again with "
            "`warntext release kaggle-meta`)."
        )
    elif not re.search(r"^## How to cite\n+(?!## )\S", text, re.M):
        out.append(f"kaggle/{name}: the description's 'How to cite' section is empty.")
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
    if meta.get("expectedUpdateFrequency") != UPDATE_FREQUENCY:
        out.append(
            f"kaggle/{name}: the update frequency is {meta.get('expectedUpdateFrequency')!r}, "
            f"not {UPDATE_FREQUENCY!r} (no schedule is promised before the weekly update runs)."
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
