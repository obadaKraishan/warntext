"""Read every record from senders other than the National Weather Service, once, to the drive.

The archive is read year by year (UTC), ordered by ``sent`` and ``id``, in pages of ``top``
records (``$skip`` and ``$top``). Records sent at or after ``until`` are left for the weekly
update, so the backfill is a fixed snapshot whose counts can be checked against the server's.

Each answer is written once to the raw folder, flushed and checked on disk, and a manifest line
records its year, offset, size, record count, SHA-256 and the time it was read. The manifest
holds no message text. A stopped run starts again from the first page that is not in the
manifest, so nothing is downloaded twice. A page whose answer is larger than the client's
per-answer guard is read again as smaller pages at the same offset.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from warntext import durable
from warntext.client import ResponseTooLarge
from warntext.probe import ENDPOINT, ENTITY
from warntext.sample import NWS_SENDER, ORDERBY

PAGE_SIZE = 500
#: Pages too large for the guard are read again as pages of this many records.
SMALL_PAGE = 100
OTHER_SENDERS = f"sender ne '{NWS_SENDER}'"


def window_filter(year: int, until: str) -> str:
    """Records sent in ``year`` (UTC) and before ``until``."""
    start = f"{year}-01-01T00:00:00.000Z"
    end = min(f"{year + 1}-01-01T00:00:00.000Z", until)
    return f"(sent ge '{start}' and sent lt '{end}') and ({OTHER_SENDERS})"


def years_until(first: int, until: str) -> list[int]:
    """The years from ``first`` to the year that holds ``until`` (exclusive bound)."""
    last = int(until[:4])
    if until[4:] <= "-01-01T00:00:00.000Z":
        last -= 1
    return list(range(first, last + 1))


@dataclass(frozen=True)
class PageLine:
    """One manifest line. No message text."""

    year: int
    skip: int
    top: int
    records: int
    bytes: int
    sha256: str
    file: str
    fetched_at: str
    seconds: float
    first_sent: str
    last_sent: str


def page_name(year: int, skip: int, top: int) -> str:
    return f"other-{year}-skip{skip:06d}-top{top:04d}.json"


def read_manifest(path: Path | str) -> list[PageLine]:
    path = Path(path)
    if not path.exists():
        return []
    types = {f.name: f.type for f in fields(PageLine)}
    out = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            kw: dict[str, Any] = {}
            for key, value in row.items():
                kind = types[key]
                cast = int if kind == "int" else float if kind == "float" else str
                kw[key] = cast(value)
            out.append(PageLine(**kw))
    return out


def append_manifest(path: Path | str, line: PageLine) -> None:
    path = Path(path)
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[f.name for f in fields(PageLine)])
        if new:
            writer.writeheader()
        writer.writerow(asdict(line))
        durable.flush_file(fh)


def next_skip(lines: Iterable[PageLine], year: int) -> int:
    """The first offset in ``year`` that no complete page covers yet.

    Pages are read in order, so the covered records form one run from offset 0; a page that
    held fewer records than asked for ends the year.
    """
    covered = 0
    for line in sorted((x for x in lines if x.year == year), key=lambda x: x.skip):
        if line.skip != covered:
            break
        covered += line.records
        if line.records < line.top:
            break
    return covered


def year_done(lines: Iterable[PageLine], year: int, expected: int) -> bool:
    return next_skip(lines, year) >= expected


def fetch_page(client: Any, year: int, skip: int, top: int, until: str, raw_dir: Path) -> PageLine:
    """Read one page and write the answer, exactly as it came, to ``raw_dir``."""
    params = {
        "$filter": window_filter(year, until),
        "$orderby": ORDERBY,
        "$skip": skip,
        "$top": top,
    }
    resp = client.get(ENDPOINT, params)
    if resp.status != 200:
        raise RuntimeError(
            f"Year {year}, offset {skip}: the server answered HTTP {resp.status}. Nothing was "
            "saved; run the backfill again later and it resumes here."
        )
    records = json.loads(resp.content)[ENTITY]
    name = page_name(year, skip, top)
    digest = durable.write_once(raw_dir / name, resp.content)
    sents = [r.get("sent") or "" for r in records]
    return PageLine(
        year=year,
        skip=skip,
        top=top,
        records=len(records),
        bytes=len(resp.content),
        sha256=digest,
        file=name,
        fetched_at=client.clock(),
        seconds=round(resp.seconds, 3),
        first_sent=min(sents) if sents else "",
        last_sent=max(sents) if sents else "",
    )


def run(
    client: Any,
    expected: dict[int, int],
    until: str,
    raw_dir: Path | str,
    top: int = PAGE_SIZE,
    small: int = SMALL_PAGE,
    on_page: Any = None,
) -> list[PageLine]:
    """Read every page not yet in the manifest, year by year. Returns the new manifest lines.

    ``expected`` holds the server's count per year, taken before the run; a year is read until
    a page comes back short or the expected count is covered. Each new line is added to the
    manifest as soon as its page is safe on disk.
    """
    raw_dir = Path(raw_dir)
    manifest = raw_dir / "manifest.csv"
    lines = read_manifest(manifest)
    new: list[PageLine] = []
    for year in sorted(expected):
        skip = next_skip(lines, year)
        while True:
            done_short = any(
                x.year == year and x.records < x.top and x.skip + x.records == skip for x in lines
            )
            if done_short or (skip >= expected[year] and skip > 0) or expected[year] == 0:
                break
            try:
                line = fetch_page(client, year, skip, top, until, raw_dir)
            except ResponseTooLarge:
                line = fetch_page(client, year, skip, small, until, raw_dir)
            append_manifest(manifest, line)
            lines.append(line)
            new.append(line)
            if on_page is not None:
                on_page(line)
            skip += line.records
            if line.records < line.top:
                break
    return new


def planned_calls(expected: dict[int, int], top: int = PAGE_SIZE) -> int:
    """Calls the backfill needs if no page is too large: one per page, at least one per year."""
    return sum(max(1, math.ceil(n / top)) for n in expected.values() if n > 0)


def iter_records(raw_dir: Path | str) -> Iterable[tuple[PageLine, dict]]:
    """Every record in the backfill with its page's manifest line, checked against its SHA-256."""
    raw_dir = Path(raw_dir)
    for line in sorted(read_manifest(raw_dir / "manifest.csv"), key=lambda x: (x.year, x.skip)):
        data = (raw_dir / line.file).read_bytes()
        if durable.sha256_bytes(data) != line.sha256:
            raise durable.WriteCheckFailed(
                f"{line.file} no longer matches its SHA-256 in the manifest. Check the drive, "
                "then move the file aside and run the backfill again to fetch that page."
            )
        for record in json.loads(data)[ENTITY]:
            yield line, record
