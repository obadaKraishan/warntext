"""Read every record from senders other than the National Weather Service, once, to the drive.

The archive is read year by year (UTC), ordered by ``sent`` and ``id``, in pages of ``top``
records. Records sent at or after ``until`` are left for the weekly update, so the backfill is
a fixed snapshot whose counts can be checked against the server's.

Pages are cut by a cursor rather than a deep ``$skip``: each page starts at the ``sent`` time
of the last record read (``sent ge``) and skips only the records already read at that same
time. The server then reads forward from that time instead of counting from the start of the
year, which matters here because the weather service's records, which the filter leaves out,
are 98% of every year until 2023.

Each answer is written once to the raw folder, flushed and checked on disk, and a manifest line
records its year, cursor, size, record count, SHA-256 and the time it was read. The manifest
holds no message text. A stopped run starts again after the last page in the manifest, so
nothing is downloaded twice. A page whose answer is larger than the client's per-answer guard
is read again as a smaller page at the same cursor.
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


def year_bounds(year: int, until: str) -> tuple[str, str]:
    """The first instant of ``year`` and the earlier of the next year's and ``until``."""
    return f"{year}-01-01T00:00:00.000Z", min(f"{year + 1}-01-01T00:00:00.000Z", until)


def window_filter(
    year: int, until: str, start: str | None = None, senders: str | None = OTHER_SENDERS
) -> str:
    """Records sent in ``year`` (UTC), from ``start`` and before ``until``, by ``senders``.

    ``senders`` is the other senders by default; None gives every sender.
    """
    first, end = year_bounds(year, until)
    window = f"(sent ge '{start or first}' and sent lt '{end}')"
    return f"{window} and ({senders})" if senders else window


NWS_ONLY = f"sender eq '{NWS_SENDER}'"


def count_plan(years: Iterable[int], until: str, method: str) -> list[tuple[str, str]]:
    """Named counts for each year: ``other:<y>`` directly, or ``all:<y>`` and ``nws:<y>``.

    The direct count filters on ``sender ne``, which the server must check record by record;
    in the years when the weather service sent about 400,000 records it can pass the server's
    60-second limit. The difference uses two indexed counts instead: every sender, and the
    weather service's sender alone.
    """
    if method == "direct":
        return [(f"other:{y}", window_filter(y, until)) for y in years]
    if method == "difference":
        out = []
        for y in years:
            out.append((f"all:{y}", window_filter(y, until, senders=None)))
            out.append((f"nws:{y}", window_filter(y, until, senders=NWS_ONLY)))
        return out
    raise ValueError(f"Unknown count method {method!r}; use direct or difference.")


def year_counts(entries: Iterable[dict[str, Any]]) -> dict[int, tuple[int, str]]:
    """The other senders' count per year, and how it was taken, from saved count entries.

    A direct count is used where there is one; otherwise every sender's count minus the
    weather service's. Years with neither are left out.
    """
    direct: dict[int, int] = {}
    parts: dict[tuple[str, int], int] = {}
    for e in entries:
        if e.get("count") is None:
            continue
        kind, year = e["name"].split(":")
        if kind == "other":
            direct[int(year)] = e["count"]
        else:
            parts[(kind, int(year))] = e["count"]
    out = {y: (n, "direct") for y, n in direct.items()}
    for (kind, y), n in parts.items():
        if kind == "all" and y not in out and ("nws", y) in parts:
            out[y] = (n - parts[("nws", y)], "difference")
    return dict(sorted(out.items()))


def years_until(first: int, until: str) -> list[int]:
    """The years from ``first`` to the year that holds ``until`` (an exclusive bound)."""
    last = int(until[:4])
    if until[4:] <= "-01-01T00:00:00.000Z":
        last -= 1
    return list(range(first, last + 1))


@dataclass(frozen=True)
class PageLine:
    """One manifest line. No message text.

    ``cursor_sent`` and ``cursor_skip`` say where the page started; ``last_sent`` is the
    newest ``sent`` in the page and ``last_seen`` how many records at that time have been read
    so far in the year, which is where the next page starts.
    """

    year: int
    page: int
    cursor_sent: str
    cursor_skip: int
    top: int
    records: int
    bytes: int
    sha256: str
    file: str
    fetched_at: str
    seconds: float
    first_sent: str
    last_sent: str
    last_seen: int


def page_name(year: int, page: int, top: int) -> str:
    return f"other-{year}-p{page:03d}-top{top:04d}.json"


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


@dataclass(frozen=True)
class Cursor:
    """Where the next page of a year starts, and how much of the year is read."""

    page: int
    sent: str
    skip: int
    read: int
    finished: bool


def cursor(lines: Iterable[PageLine], year: int, until: str, start: str | None = None) -> Cursor:
    """The next page of ``year`` after the pages already in the manifest.

    ``start`` (an ISO time in UTC) makes the first page begin there instead of at the year's
    first instant, for a window such as a weekly update's.
    """
    mine = sorted((x for x in lines if x.year == year), key=lambda x: x.page)
    read = sum(x.records for x in mine)
    if not mine:
        first = year_bounds(year, until)[0]
        return Cursor(0, max(first, start) if start else first, 0, 0, False)
    last = mine[-1]
    if last.records < last.top:
        return Cursor(last.page + 1, last.last_sent, last.last_seen, read, True)
    return Cursor(last.page + 1, last.last_sent, last.last_seen, read, False)


def fetch_page(client: Any, year: int, at: Cursor, top: int, until: str, raw_dir: Path) -> PageLine:
    """Read one page and write the answer, exactly as it came, to ``raw_dir``."""
    params = {
        "$filter": window_filter(year, until, at.sent),
        "$orderby": ORDERBY,
        "$skip": at.skip,
        "$top": top,
    }
    resp = client.get(ENDPOINT, params)
    if resp.status != 200:
        raise RuntimeError(
            f"Year {year}, page {at.page}: the server answered HTTP {resp.status}. Nothing was "
            "saved; run the backfill again later and it resumes here."
        )
    records = json.loads(resp.content)[ENTITY]
    name = page_name(year, at.page, top)
    digest = durable.write_once(raw_dir / name, resp.content)
    sents = [r.get("sent") or "" for r in records]
    last = max(sents) if sents else at.sent
    seen = sum(1 for s in sents if s == last)
    if last == at.sent:
        seen += at.skip
    return PageLine(
        year=year,
        page=at.page,
        cursor_sent=at.sent,
        cursor_skip=at.skip,
        top=top,
        records=len(records),
        bytes=len(resp.content),
        sha256=digest,
        file=name,
        fetched_at=client.clock(),
        seconds=round(resp.seconds, 3),
        first_sent=min(sents) if sents else "",
        last_sent=last,
        last_seen=seen,
    )


def run(
    client: Any,
    expected: dict[int, int],
    until: str,
    raw_dir: Path | str,
    top: int = PAGE_SIZE,
    small: int = SMALL_PAGE,
    on_page: Any = None,
    start: str | None = None,
) -> list[PageLine]:
    """Read every page not yet in the manifest, year by year. Returns the new manifest lines.

    ``expected`` holds the server's count per year, taken before the run. A year is read until
    a page comes back short or the expected count is read. Each new line is added to the
    manifest as soon as its page is safe on disk.
    """
    raw_dir = Path(raw_dir)
    manifest = raw_dir / "manifest.csv"
    lines = read_manifest(manifest)
    new: list[PageLine] = []
    for year in sorted(expected):
        while True:
            at = cursor(lines, year, until, start)
            if at.finished or at.read >= expected[year]:
                break
            try:
                line = fetch_page(client, year, at, top, until, raw_dir)
            except ResponseTooLarge:
                line = fetch_page(client, year, at, small, until, raw_dir)
            append_manifest(manifest, line)
            lines.append(line)
            new.append(line)
            if on_page is not None:
                on_page(line)
    return new


def planned_calls(expected: dict[int, int], top: int = PAGE_SIZE) -> int:
    """Calls the backfill needs if no page is too large: one per page."""
    return sum(math.ceil(n / top) for n in expected.values() if n > 0)


def iter_records(raw_dir: Path | str) -> Iterable[tuple[PageLine, dict]]:
    """Every record in the backfill with its page's manifest line, checked against its SHA-256."""
    raw_dir = Path(raw_dir)
    for line in sorted(read_manifest(raw_dir / "manifest.csv"), key=lambda x: (x.year, x.page)):
        data = (raw_dir / line.file).read_bytes()
        if durable.sha256_bytes(data) != line.sha256:
            raise durable.WriteCheckFailed(
                f"{line.file} no longer matches its SHA-256 in the manifest. Check the drive, "
                "then move the file aside and run the backfill again to fetch that page."
            )
        for record in json.loads(data)[ENTITY]:
            yield line, record
