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
    """One count. ``count`` is None and ``error`` says why when the server could not answer."""

    name: str
    filter: str | None
    count: int | None
    seconds: float
    error: str | None = None


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


def run_counts(
    client: Any,
    plan: Iterable[tuple[str, str | None]],
    save_to: Path | str | None = None,
    **facts: Any,
) -> list[Count]:
    """Run each named count in ``plan`` in turn, saving after each one when ``save_to`` is set.

    A count the server cannot answer (for example a 503 after its 60-second timeout on a field
    it cannot search quickly) is recorded with its error and the run goes on; a block (403) or
    a cap still stops the run.
    """
    from warntext.client import CapReached, SourceBlocked

    out: list[Count] = []
    for name, filter_ in plan:
        try:
            n, seconds = count(client, filter_)
            out.append(Count(name, filter_, n, round(seconds, 3)))
        except SourceBlocked as exc:
            if exc.status == 403:
                raise
            out.append(Count(name, filter_, None, 0.0, f"HTTP {exc.status}"))
        except RuntimeError as exc:
            if isinstance(exc, CapReached):
                raise
            out.append(Count(name, filter_, None, 0.0, str(exc)))
        if save_to is not None:
            save(save_to, out, **facts)
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
