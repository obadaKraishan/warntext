"""FEMA's list of IPAWS alerting authorities: the official names and types of the senders.

FEMA publishes the organizations that hold IPAWS alerting authority on its page "IPAWS Alerting
Authorities - Agencies and Organizations" (data.gov identifier FEMA-0333, licensed as a work of
the U.S. government). Each row gives the authority's IPAWS identifier, which is the archive's
``cogId``, its name, its state, its FEMA region and its type (Local, State, Tribal, Territory,
Federal, Military, National).

WarnText keeps a dated snapshot of the list in the package (``alerting_authorities.csv``) so that
every build is reproducible, and uses it in two ways:

- **organization names**: an authority on the list is named as FEMA names it (when the name
  passes the same checks as every released name), instead of by the senders' own ``senderName``;
- **sender kinds**: FEMA's type is the first evidence. Federal and Military read as ``federal``,
  National as ``other``, and the rest by their own name. The rule's own reading is kept beside it
  (``sender_kind_rule``), and authorities missing from the list keep the rule's kind.

Hand overrides (:mod:`warntext.senders`) still come last.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from importlib import resources

#: The page the snapshot was read from.
PAGE_URL = (
    "https://www.fema.gov/emergency-managers/practitioners/integrated-public-alert-warning-system/"
    "public-safety-officials/alerting-authorities/agencies-organizations"
)
#: The tracked snapshot, its date on FEMA's page, and when it was read.
SNAPSHOT_FILE = "alerting_authorities.csv"
SNAPSHOT_PAGE_UPDATED = "2026-11-12"
SNAPSHOT_RETRIEVED = "2026-11-15"
COLUMNS = ["cog_id", "name", "state", "fema_region", "type"]

#: FEMA's authority types, read as WarnText's sender kinds.
TYPE_TO_KIND = {
    "Local": "local",
    "State": "state",
    "Tribal": "tribal",
    "Territory": "territorial",
    "Federal": "federal",
    "Military": "federal",
    "National": "other",
}
_HEADER = {
    "ipaws alerting authority id": "cog_id",
    "ipaws alerting authority name": "name",
    "state/province": "state",
    "fema region": "fema_region",
    "alerting authority type": "type",
}


@dataclass(frozen=True)
class Authority:
    cog_id: int
    name: str
    state: str
    fema_region: str
    type: str

    @property
    def kind(self) -> str | None:
        """The sender kind FEMA's type gives, or None for a type WarnText does not know."""
        return TYPE_TO_KIND.get(self.type)


class _Tables(HTMLParser):
    """Collects the cells of every HTML table, row by row (text only)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_page(html: str) -> list[Authority]:
    """Read the authorities from FEMA's page. Raises ``ValueError`` when the table is not there.

    The table is found by its header; every row must have five cells and a numeric identifier,
    and no identifier may appear twice.
    """
    p = _Tables()
    p.feed(html)
    start = None
    for k, row in enumerate(p.rows):
        names = [_HEADER.get(unescape(c).replace("﻿", "").strip().lower()) for c in row]
        if names == COLUMNS:
            start = k
            break
    if start is None:
        raise ValueError(
            "The page has no table with the columns IPAWS Alerting Authority ID, Name, "
            "State/Province, FEMA Region and Alerting Authority Type; FEMA may have changed it."
        )
    out: dict[int, Authority] = {}
    for n, row in enumerate(p.rows[start + 1 :], start=1):
        if len(row) != 5:
            continue
        cog, name, state, region, kind = (unescape(c).strip() for c in row)
        if not cog.isdigit():
            raise ValueError(f"Row {n} of FEMA's table has an identifier that is not a number.")
        if int(cog) in out:
            raise ValueError(f"Row {n} of FEMA's table repeats identifier {cog}.")
        out[int(cog)] = Authority(int(cog), name, state, region, kind)
    if not out:
        raise ValueError("FEMA's table of alerting authorities has no rows.")
    return [out[k] for k in sorted(out)]


def to_csv(rows: list[Authority]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    for a in rows:
        w.writerow([a.cog_id, a.name, a.state, a.fema_region, a.type])
    return buf.getvalue()


def parse_csv(text: str) -> dict[int, Authority]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != COLUMNS:
        raise ValueError(f"{SNAPSHOT_FILE}: the header must be {','.join(COLUMNS)}.")
    out = {}
    for row in reader:
        a = Authority(
            int(row["cog_id"]), row["name"], row["state"], row["fema_region"], row["type"]
        )
        out[a.cog_id] = a
    return out


def load() -> dict[int, Authority]:
    """The tracked snapshot of FEMA's list, by identifier."""
    text = resources.files("warntext").joinpath(SNAPSHOT_FILE).read_text(encoding="utf-8")
    return parse_csv(text)
