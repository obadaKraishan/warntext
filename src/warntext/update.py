"""The weekly update: the new records since the last build, FEMA's list again, a rebuild, the check.

The state is a small JSON file kept next to the raw pages (on the maintainer's drive): the raw
folders read so far, the end of the last window (exclusive, UTC), the server's count per year,
and the date of FEMA's list in use. It holds no text, no sender value and no identifier: those
stay in the raw pages and the private files, which never leave the machine.

One run:

1. **The window.** From the state's end to ``until``: by default the newest whole hour that is at
   least 25 hours old, because OpenFEMA publishes the archive with a 24-hour delay.
2. **FEMA's list** of alerting authorities, read again (one request) and saved, dated, next to
   the state; the build uses it.
3. **The new records** of every sender but the weather service, counted on the server per year of
   the window and read by cursor into ``<raw root>/update-<until>/``, written once and checked.
4. **The look-back.** The server's count for the ``LOOKBACK_DAYS`` before the state's end is set
   against the local records of that range. When the server holds more (records the archive
   added late), the range is read again into ``late/``; records already held are dropped by
   their FEMA id at the build.
5. **The rebuild** from every raw folder, so that text groups, threads, references, sender kinds
   and organization names are exact: they depend on earlier weeks' raw values, which only the
   raw pages hold.
6. **The check.** The server's count is taken again for every year the run touched; the release
   check runs against those counts. The state moves forward only when the check passes.

The summary holds counts only.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from warntext import authorities as au
from warntext import backfill as bf
from warntext import check as ck
from warntext import probe, tables
from warntext.sample import NWS_SENDER

#: The days before the last window's end that each run counts again on the server.
LOOKBACK_DAYS = 7
#: OpenFEMA publishes the archive a day late; a window ends at least this long before the run.
DELAY = timedelta(hours=25)
STATE_VERSION = 1


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def default_until(now: datetime) -> str:
    """The newest whole hour at least ``DELAY`` before ``now``."""
    t = (now - DELAY).astimezone(timezone.utc)
    return iso(t.replace(minute=0, second=0, microsecond=0))


def range_filter(start: str, end: str, senders: str | None = bf.OTHER_SENDERS) -> str:
    window = f"(sent ge '{start}' and sent lt '{end}')"
    return f"{window} and ({senders})" if senders else window


def count_range(client: Any, start: str, end: str) -> tuple[int, str, int]:
    """The other senders' records sent in ``[start, end)``: (count, how, calls).

    Directly (``sender ne`` the weather service), or, when the server passes its time limit,
    as every sender minus the weather service's sender.
    """
    try:
        n, _ = probe.count(client, range_filter(start, end))
        return n, "direct", 1
    except RuntimeError:
        every, _ = probe.count(client, range_filter(start, end, senders=None))
        nws, _ = probe.count(client, range_filter(start, end, senders=f"sender eq '{NWS_SENDER}'"))
        return every - nws, "difference", 3


def year_pieces(start: str, end: str) -> list[tuple[int, str, str]]:
    """``[start, end)`` cut at each new year: (year, piece start, piece end)."""
    out = []
    a = parse(start)
    b = parse(end)
    while a < b:
        nxt = datetime(a.year + 1, 1, 1, tzinfo=timezone.utc)
        piece_end = min(nxt, b)
        out.append((a.year, iso(a), iso(piece_end)))
        a = piece_end
    return out


# --- state -------------------------------------------------------------------------------


def init_state(
    path: Path | str, raw_folders: list[str], year_counts: Mapping[int, int], until: str
) -> dict[str, Any]:
    """A new state file from the backfill: its raw folder(s), its bound and its year counts."""
    path = Path(path)
    if path.exists():
        raise SystemExit(f"{path} exists; a state is started once. Use it, or move it aside.")
    state = {
        "version": STATE_VERSION,
        "until": until,
        "raw_folders": list(raw_folders),
        "year_counts": {str(y): int(n) for y, n in sorted(year_counts.items())},
        "fema_list": {"file": None, "retrieved": au.SNAPSHOT_RETRIEVED},
        "runs": [],
    }
    write_state(path, state)
    return state


def read_state(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise SystemExit(
            f"{path} does not exist. Start it once with `warntext update --init` from the "
            "backfill's counts and raw folder."
        )
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("version") != STATE_VERSION:
        raise SystemExit(f"{path} has state version {state.get('version')}; expected 1.")
    return state


def write_state(path: Path | str, state: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


# --- records -----------------------------------------------------------------------------


def records(raw_root: Path | str, folders: Iterable[str]) -> Iterable[tuple[Any, dict]]:
    """Every record of the raw folders, each FEMA record id once (the first read wins)."""
    seen: set[str] = set()
    for folder in folders:
        path = Path(raw_root) / folder
        if not (path / "manifest.csv").exists():
            continue
        for line, rec in bf.iter_records(path):
            rid = str(rec.get("id"))
            if rid in seen:
                continue
            seen.add(rid)
            yield line, rec


def local_counts(
    raw_root: Path | str, folders: Iterable[str], start: str, end: str
) -> tuple[int, int]:
    """Records held locally (by FEMA id): all of them, and those sent in ``[start, end)``."""
    a, b = parse(start), parse(end)
    total = in_range = 0
    for _, rec in records(raw_root, folders):
        total += 1
        sent = rec.get("sent")
        if sent and a <= parse(sent) < b:
            in_range += 1
    return total, in_range


# --- one run -----------------------------------------------------------------------------


def run_update(
    client: Any,
    state_path: Path | str,
    raw_root: Path | str,
    out_dir: Path | str,
    private_dir: Path | str,
    until: str | None = None,
    now: datetime | None = None,
    fetch_list: bool = True,
) -> dict[str, Any]:
    """One weekly run. Returns the summary (counts only); moves the state on a passing check."""
    t0 = time.monotonic()
    calls0 = getattr(getattr(client, "budget", None), "calls", 0)
    bytes0 = getattr(getattr(client, "budget", None), "nbytes", 0)
    state = read_state(state_path)
    raw_root = Path(raw_root)
    start = state["until"]
    until = until or default_until(now or datetime.now(timezone.utc))
    if parse(until) <= parse(start):
        raise SystemExit(f"Nothing to read: the window would end at {until}, before {start}.")
    folder = "update-" + until[:13].replace(":", "")
    summary: dict[str, Any] = {"window": {"start": start, "until": until}, "folder": folder}

    # FEMA's list, again.
    fema = au.load()
    list_file = None
    if fetch_list:
        resp = client.get(au.PAGE_URL)
        if resp.status != 200:
            raise RuntimeError(f"FEMA's list answered HTTP {resp.status}; nothing was changed.")
        rows = au.parse_page(resp.content.decode("utf-8", errors="replace"))
        list_dir = Path(state_path).parent / "authorities"
        list_dir.mkdir(parents=True, exist_ok=True)
        list_file = list_dir / f"alerting_authorities-{until[:10]}.csv"
        list_file.write_text(au.to_csv(rows), encoding="utf-8")
        fresh = {a.cog_id: a for a in rows}
        summary["fema_list"] = {
            "authorities": len(fresh),
            "added_since_snapshot": len(set(fresh) - set(fema)),
            "gone_since_snapshot": len(set(fema) - set(fresh)),
            "type_changed": sum(1 for k in set(fresh) & set(fema) if fresh[k].type != fema[k].type),
        }
        fema = fresh

    # The new window, per year.
    expected_new: dict[int, int] = {}
    hows = Counter()
    for year, a, b in year_pieces(start, until):
        n, how, _ = count_range(client, a, b)
        expected_new[year] = n
        hows[how] += 1
    new_lines = []
    for year, a, b in year_pieces(start, until):
        if expected_new[year]:
            new_lines += bf.run(client, {year: expected_new[year]}, b, raw_root / folder, start=a)
    summary["new_window"] = {
        "server_count": sum(expected_new.values()),
        "pages": len(new_lines),
        "records_read": sum(x.records for x in new_lines),
        "counts_taken": dict(hows),
    }

    # The look-back: records the archive added late, before the last window's end.
    lb_start = iso(parse(start) - timedelta(days=LOOKBACK_DAYS))
    server_lb, _, _ = count_range(client, lb_start, start)
    before, local_lb = local_counts(raw_root, state["raw_folders"], lb_start, start)
    late_lines = []
    if server_lb > local_lb:
        for year, a, b in year_pieces(lb_start, start):
            late_lines += bf.run(client, {year: 10**9}, b, raw_root / folder / "late", start=a)
    summary["look_back"] = {
        "start": lb_start,
        "server_count": server_lb,
        "local_count": local_lb,
        "pages_read_again": len(late_lines),
    }

    # The rebuild from every raw folder.
    folders = list(state["raw_folders"])
    for f in (folder, f"{folder}/late"):
        if (raw_root / f / "manifest.csv").exists() and f not in folders:
            folders.append(f)
    build = tables.build(tables.parse_records(records(raw_root, folders)), fema=fema)
    written = tables.write(build, out_dir, private_dir)

    # The server's counts again for every year the run touched, then the check.
    year_counts = {int(y): n for y, n in state["year_counts"].items()}
    touched = sorted({y for y, _, _ in year_pieces(lb_start, until)})
    for year in touched:
        first, end = bf.year_bounds(year, until)
        n, _, _ = count_range(client, first, end)
        year_counts[year] = n
    failures = ck.check(
        build.tables,
        [x["sender"] for x in build.raw_senders],
        year_counts,
        build.raw_identifiers,
    )
    alerts = build.tables["alerts"]["messages"]
    new_ids = {
        r["message_id"]
        for c in tables.CONFIGS
        for r in build.tables[c]["messages"]
        if r["sent_utc"] is not None and r["sent_utc"] >= parse(start)
    }
    new_alerts = [r for r in alerts if r["message_id"] in new_ids]
    summary.update(
        {
            "records_before": before,
            "records_after": build.summary["records"],
            "new_records": build.summary["records"] - before,
            "new_messages": len(new_ids),
            "new_real_alerts": len(new_alerts),
            "new_tests": len(new_ids) - len(new_alerts),
            "new_real_alerts_withheld": dict(
                Counter(r["text_withheld"] for r in new_alerts if r["text_withheld"])
            ),
            "new_real_alerts_by_kind": dict(Counter(r["sender_kind"] for r in new_alerts)),
            "new_real_alerts_by_group": dict(Counter(r["event_group"] for r in new_alerts)),
            "new_authorities": len(
                {r["cog_id"] for r in alerts if r["message_id"] in new_ids}
                - {r["cog_id"] for r in alerts if r["message_id"] not in new_ids}
            ),
            "rows_written": written,
            "check": "passed" if not failures else "failed",
            "check_failures": len(failures),
            "calls": getattr(getattr(client, "budget", None), "calls", 0) - calls0,
            "bytes": getattr(getattr(client, "budget", None), "nbytes", 0) - bytes0,
            "seconds": round(time.monotonic() - t0, 1),
        }
    )
    if not failures:
        state["until"] = until
        state["raw_folders"] = folders
        state["year_counts"] = {str(y): n for y, n in sorted(year_counts.items())}
        state["fema_list"] = {
            "file": list_file.name if list_file else state["fema_list"]["file"],
            "retrieved": until[:10] if list_file else state["fema_list"]["retrieved"],
        }
        state["runs"].append(
            {
                "until": until,
                "new_records": summary["new_records"],
                "new_real_alerts": summary["new_real_alerts"],
                "calls": summary["calls"],
            }
        )
        write_state(state_path, state)
    summary["failures"] = failures
    return summary


def rebuild_from_state(
    state_path: Path | str, raw_root: Path | str, out_dir: Path | str, private_dir: Path | str
) -> dict[str, Any]:
    """Rebuild both layers from every raw folder the state lists, with no request.

    It uses the FEMA list the last run saved (or the packaged snapshot), and checks the tables
    against the state's year counts. The state is not changed.
    """
    state = read_state(state_path)
    fema = au.load()
    list_name = state.get("fema_list", {}).get("file")
    if list_name:
        path = Path(state_path).parent / "authorities" / list_name
        fema = au.parse_csv(path.read_text(encoding="utf-8"))
    build = tables.build(tables.parse_records(records(raw_root, state["raw_folders"])), fema=fema)
    written = tables.write(build, out_dir, private_dir)
    year_counts = {int(y): n for y, n in state["year_counts"].items()}
    failures = ck.check(
        build.tables, [x["sender"] for x in build.raw_senders], year_counts, build.raw_identifiers
    )
    return {
        "records": build.summary["records"],
        "fema_list": list_name or "packaged snapshot",
        "rows_written": written,
        "check": "passed" if not failures else "failed",
        "failures": failures,
        "summary": build.summary,
    }
