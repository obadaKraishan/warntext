"""A seeded, repeatable sample of the archive, saved raw to the drive.

The archive is split into strata by year and by kind of sender: the National Weather Service
(``sender eq 'w-nws.webmaster@noaa.gov'``, about 98% of all records) and every other sender.
In each stratum the records are ordered by ``sent`` and cut into blocks of ``page_size``; a
seeded draw picks ``pages`` blocks, and each block is read with one call (``$skip`` and
``$top``). Every record in a stratum has the same chance of being drawn, and a record's weight
is its stratum's size over the number drawn from it.

Each answer is written once to the raw folder, flushed and checked on disk, and a manifest
line records where it is, how many records it holds and its SHA-256. The manifest holds no
message text. A run can be repeated: pages already in the manifest are not fetched again.
"""

from __future__ import annotations

import csv
import json
import random
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from warntext import durable
from warntext.probe import ENDPOINT, ENTITY, year_filter

NWS_SENDER = "w-nws.webmaster@noaa.gov"
KINDS = ("nws", "other")
#: ``id`` breaks ties between records sent in the same second, so a page is the same each time.
ORDERBY = "sent asc, id asc"


@dataclass(frozen=True)
class Stratum:
    year: int
    kind: str
    count: int


@dataclass(frozen=True)
class Page:
    year: int
    kind: str
    skip: int
    top: int

    @property
    def name(self) -> str:
        return f"{self.year}-{self.kind}-skip{self.skip:07d}.json"


@dataclass(frozen=True)
class PageRecord:
    """One manifest line. No message text."""

    year: int
    kind: str
    skip: int
    top: int
    records: int
    bytes: int
    sha256: str
    file: str
    fetched_at: str
    seconds: float


def stratum_filter(year: int, kind: str) -> str:
    if kind not in KINDS:
        raise ValueError(f"Unknown sender kind {kind!r}; use one of {', '.join(KINDS)}.")
    op = "eq" if kind == "nws" else "ne"
    return f"({year_filter(year)}) and (sender {op} '{NWS_SENDER}')"


def plan_pages(strata: Iterable[Stratum], pages: int, page_size: int, seed: int) -> list[Page]:
    """Pick ``pages`` blocks of ``page_size`` records in each stratum, by a seeded draw.

    A stratum smaller than one block is read whole in one page. Each stratum has its own random
    stream, so changing one stratum's count does not move the pages drawn in the others.
    """
    out: list[Page] = []
    for s in strata:
        if s.count <= 0:
            continue
        if s.count <= page_size:
            out.append(Page(s.year, s.kind, 0, s.count))
            continue
        blocks = s.count // page_size
        rng = random.Random(f"{seed}:{s.year}:{s.kind}")
        for block in sorted(rng.sample(range(blocks), min(pages, blocks))):
            out.append(Page(s.year, s.kind, block * page_size, page_size))
    return out


def weights(strata: Iterable[Stratum], drawn: Mapping[tuple[int, str], int]) -> dict:
    """Each stratum's weight: records in the archive per record in the sample."""
    out = {}
    for s in strata:
        n = drawn.get((s.year, s.kind), 0)
        if n:
            out[(s.year, s.kind)] = s.count / n
    return out


def read_manifest(path: Path | str) -> list[PageRecord]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    types = {f.name: f.type for f in fields(PageRecord)}
    out = []
    for row in rows:
        kw: dict[str, Any] = {}
        for key, value in row.items():
            kind = types[key]
            kw[key] = int(value) if kind == "int" else float(value) if kind == "float" else value
        out.append(PageRecord(**kw))
    return out


def append_manifest(path: Path | str, record: PageRecord) -> None:
    path = Path(path)
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[f.name for f in fields(PageRecord)])
        if new:
            writer.writeheader()
        writer.writerow(asdict(record))
        durable.flush_file(fh)


def fetch_page(client: Any, page: Page, raw_dir: Path) -> PageRecord:
    """Read one page and write the answer, as it came, to ``raw_dir``."""
    params = {
        "$filter": stratum_filter(page.year, page.kind),
        "$orderby": ORDERBY,
        "$skip": page.skip,
        "$top": page.top,
    }
    resp = client.get(ENDPOINT, params)
    if resp.status != 200:
        raise RuntimeError(
            f"Page {page.name} answered HTTP {resp.status}. Nothing was saved; check the filter "
            "and try again later."
        )
    records = json.loads(resp.content)[ENTITY]
    dest = raw_dir / page.name
    digest = durable.write_once(dest, resp.content)
    return PageRecord(
        page.year,
        page.kind,
        page.skip,
        page.top,
        len(records),
        len(resp.content),
        digest,
        page.name,
        client.clock(),
        round(resp.seconds, 3),
    )


def run(client: Any, pages: Iterable[Page], raw_dir: Path | str, manifest: Path | str) -> list:
    """Fetch every page not yet in the manifest. Returns the new manifest lines."""
    raw_dir = Path(raw_dir)
    done = {(r.year, r.kind, r.skip) for r in read_manifest(manifest)}
    new = []
    for page in pages:
        if (page.year, page.kind, page.skip) in done:
            continue
        record = fetch_page(client, page, raw_dir)
        append_manifest(manifest, record)
        new.append(record)
    return new


def iter_records(raw_dir: Path | str, manifest: Path | str) -> Iterable[tuple[PageRecord, dict]]:
    """Every sampled record with the manifest line of its page, checked against its SHA-256."""
    raw_dir = Path(raw_dir)
    for line in read_manifest(manifest):
        data = (raw_dir / line.file).read_bytes()
        if durable.sha256_bytes(data) != line.sha256:
            raise durable.WriteCheckFailed(
                f"{line.file} no longer matches its SHA-256 in the manifest. Fetch it again."
            )
        for record in json.loads(data)[ENTITY]:
            yield line, record
