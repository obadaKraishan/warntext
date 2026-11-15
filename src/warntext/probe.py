"""Cheap questions to the archive, answered on the server: counts and the oldest and newest times.

A count asks for one record with only its ``id`` (``$top=1``, ``$select=id``) and reads the
total from ``metadata.count`` (``$inlinecount=allpages``). On version 1 of the endpoint
``$top=0`` is ignored and returns 1,000 records, so it is never used.

Only fields the dataset page marks as searchable can be filtered: ``sent``, ``sender``,
``status``, ``msgType``, ``scope``, ``cogId``, the event codes and the geocodes, among others.
Language, event names, sender names, parameters (where the channels are named) and references
cannot be filtered and come from the sample.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ENDPOINT = "https://www.fema.gov/api/open/v1/IpawsArchivedAlerts"
ENTITY = "IpawsArchivedAlerts"

STATUS_VALUES = ("Actual", "Exercise", "System", "Test", "Draft")
MSGTYPE_VALUES = ("Alert", "Update", "Cancel", "Ack", "Error")


def year_filter(year: int) -> str:
    """Records sent in one calendar year (UTC)."""
    return f"sent ge '{year}-01-01T00:00:00.000Z' and sent lt '{year + 1}-01-01T00:00:00.000Z'"


def event_code_filter(code: str) -> str:
    """Records with ``code`` among their event codes (the form FEMA's own examples use)."""
    return f"contains(infos/eventCode/value,'{code}')"


def both(*filters: str | None) -> str | None:
    parts = [f"({f})" for f in filters if f]
    return " and ".join(parts) if parts else None


@dataclass(frozen=True)
class Count:
    name: str
    filter: str | None
    count: int
    seconds: float


def count(client: Any, filter_: str | None = None) -> tuple[int, float]:
    """The number of records that match ``filter_`` (all records when it is None)."""
    params: dict[str, Any] = {"$top": 1, "$inlinecount": "allpages", "$select": "id"}
    if filter_:
        params["$filter"] = filter_
    resp = client.get(ENDPOINT, params)
    if resp.status != 200:
        raise RuntimeError(f"Counting {filter_!r} answered HTTP {resp.status}.")
    data = resp.json()
    return int(data["metadata"]["count"]), resp.seconds


def edge_sent(client: Any, newest: bool = False) -> str:
    """The oldest (or newest) ``sent`` time in the archive."""
    params = {"$top": 1, "$select": "sent", "$orderby": f"sent {'desc' if newest else 'asc'}"}
    resp = client.get(ENDPOINT, params)
    if resp.status != 200:
        raise RuntimeError(
            f"Reading the {'newest' if newest else 'oldest'} time answered HTTP {resp.status}."
        )
    records = resp.json()[ENTITY]
    return records[0]["sent"]


def run_counts(client: Any, plan: Iterable[tuple[str, str | None]]) -> list[Count]:
    """Run each named count in ``plan`` in turn."""
    out = []
    for name, filter_ in plan:
        n, seconds = count(client, filter_)
        out.append(Count(name, filter_, n, round(seconds, 3)))
    return out


def year_plan(
    first: int, last: int, extra: str | None = None, prefix: str = "year"
) -> list[tuple[str, str | None]]:
    return [(f"{prefix}:{y}", both(year_filter(y), extra)) for y in range(first, last + 1)]


def save(path: Path | str, counts: list[Count], **facts: Any) -> None:
    """Write the counts (aggregates only) as JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"facts": facts, "counts": [asdict(c) for c in counts]}
    path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
