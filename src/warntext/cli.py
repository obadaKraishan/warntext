"""The ``warntext`` command line.

Every command that talks to OpenFEMA uses the polite client: the session's calls and bytes are
counted from the usage log since ``--since``, and the run stops at the caps.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from warntext import __version__
from warntext import backfill as bf
from warntext import client as cl
from warntext import probe as pr
from warntext import profile as pf
from warntext import sample as sm

NWS_FILTER = f"sender eq '{sm.NWS_SENDER}'"


def _client(args: argparse.Namespace) -> cl.OpenFemaClient:
    log = cl.UsageLog(args.log)
    budget = cl.Budget.from_log(
        log.rows(), since=args.since, max_calls=args.max_calls, max_bytes=args.max_bytes
    )
    extra = {}
    if getattr(args, "max_response_mb", None):
        extra["max_response_bytes"] = int(args.max_response_mb * 1_000_000)
    return cl.OpenFemaClient(
        log=log, budget=budget, min_interval=args.min_interval, max_retries=args.retries, **extra
    )


def cmd_counts(args: argparse.Namespace) -> int:
    """Count records per year, overall and for the weather service's sender."""
    c = _client(args)
    plan = pr.year_plan(args.first, args.last)
    plan += pr.year_plan(args.first, args.last, extra=NWS_FILTER, prefix="nws_year")
    counts = pr.run_counts(c, plan, save_to=args.out, run_at=cl.now_utc())
    failed = [x.name for x in counts if x.count is None]
    print(f"{len(counts) - len(failed)} counts saved to {args.out}; {c.budget.calls} calls so far.")
    if failed:
        print(f"Not answered: {', '.join(failed)}. Run again later for these.")
    return 1 if failed else 0


def strata_from_counts(path: Path | str) -> list[sm.Stratum]:
    """Strata (year by kind of sender) from a ``counts`` file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))["counts"]
    year = {int(c["name"].split(":")[1]): c["count"] for c in data if c["name"].startswith("year:")}
    nws = {
        int(c["name"].split(":")[1]): c["count"] for c in data if c["name"].startswith("nws_year:")
    }
    missing = sorted(y for y in year if y not in nws or year[y] is None or nws[y] is None)
    if missing:
        raise SystemExit(f"{path}: counts are missing for {missing}; run `warntext counts` again.")
    out = []
    for y in sorted(year):
        out += [sm.Stratum(y, "nws", nws[y]), sm.Stratum(y, "other", year[y] - nws[y])]
    return out


def cmd_plan(args: argparse.Namespace) -> int:
    strata = [s for s in strata_from_counts(args.counts) if args.first <= s.year <= args.last]
    pages = sm.plan_pages(strata, args.pages, args.page_size, args.seed)
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} exists. A plan is written once; choose another name.")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": args.seed,
        "pages_per_stratum": args.pages,
        "page_size": args.page_size,
        "strata": [s.__dict__ for s in strata],
        "pages": [p.__dict__ for p in pages],
    }
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"{len(pages)} pages, {sum(p.top for p in pages)} records planned in {out}.")
    return 0


def _load_plan(path: Path | str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def cmd_sample(args: argparse.Namespace) -> int:
    plan = _load_plan(args.plan)
    pages = [sm.Page(**p) for p in plan["pages"]]
    raw = Path(args.raw)
    new = sm.run(_client(args), pages, raw, raw / "manifest.csv")
    print(f"{len(new)} pages fetched now; {len(sm.read_manifest(raw / 'manifest.csv'))} in all.")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    plan = _load_plan(args.plan)
    counts = {(s["year"], s["kind"]): s["count"] for s in plan["strata"]}
    raw = Path(args.raw)
    items = list(sm.iter_records(raw, raw / "manifest.csv"))
    rows = pf.build_rows(items, counts)
    summary = pf.summarize(rows)
    summary["crosscheck_with_openfema_fields"] = pf.crosscheck(items)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    print(f"Profile of {len(rows)} records (aggregates only) written to {out}.")
    return 0


def cmd_backfill_counts(args: argparse.Namespace) -> int:
    """The server's count per year of records from senders other than the weather service."""
    c = _client(args)
    years = bf.years_until(args.first, args.until)
    plan = [(f"other:{y}", bf.window_filter(y, args.until)) for y in years]
    counts = pr.run_counts(c, plan, save_to=args.out, run_at=cl.now_utc(), until=args.until)
    failed = [x.name for x in counts if x.count is None]
    total = sum(x.count or 0 for x in counts)
    print(f"{len(counts) - len(failed)} yearly counts ({total:,} records) saved to {args.out}.")
    if failed:
        print(f"Not answered: {', '.join(failed)}. Run again later for these.")
    return 1 if failed else 0


def read_year_counts(path: Path | str) -> tuple[dict[int, int], str]:
    """The yearly counts and the ``until`` bound from a ``backfill-counts`` file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    counts = {}
    for c in data["counts"]:
        if c["count"] is None:
            raise SystemExit(f"{path}: {c['name']} has no count; run `warntext backfill-counts`.")
        counts[int(c["name"].split(":")[1])] = c["count"]
    return counts, data["facts"]["until"]


def cmd_backfill(args: argparse.Namespace) -> int:
    """Read every page of the other senders' records to the raw folder (resumable)."""
    expected, until = read_year_counts(args.counts)
    c = _client(args)
    raw = Path(args.raw)
    done = bf.read_manifest(raw / "manifest.csv")
    need = bf.planned_calls(expected) - len(done)
    left = c.budget.max_calls - c.budget.calls
    if need + args.reserve > left:
        print(
            f"The backfill needs about {need} more calls and {args.reserve} are kept for the "
            f"checks after it, but only {left} are left under the cap. Nothing was fetched."
        )
        return 2

    def show(line: bf.PageLine) -> None:
        print(
            f"{line.year} skip {line.skip}: {line.records} records, {line.bytes:,} bytes, "
            f"{line.seconds:.1f} s; {c.budget.calls} calls, {c.budget.nbytes:,} bytes so far",
            flush=True,
        )

    new = bf.run(c, expected, until, raw, on_page=show)
    lines = bf.read_manifest(raw / "manifest.csv")
    got = sum(x.records for x in lines)
    print(f"{len(new)} pages fetched now; {len(lines)} pages and {got:,} records in all.")
    return 0


def _client_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("--log", default="data/usage_log.csv", help="request log (CSV)")
    p.add_argument("--since", required=True, help="UTC start of the session, for the caps")
    p.add_argument("--max-calls", type=int, default=cl.DEFAULT_MAX_CALLS)
    p.add_argument("--max-bytes", type=int, default=cl.DEFAULT_MAX_BYTES)
    p.add_argument("--min-interval", type=float, default=3.5, help="seconds between requests")
    p.add_argument("--retries", type=int, default=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warntext",
        description="Build and check the WarnText corpus of public alert messages.",
    )
    parser.add_argument("--version", action="version", version=f"warntext {__version__}")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("counts", help="count records per year, overall and for the NWS sender")
    p.add_argument("--first", type=int, default=2011)
    p.add_argument("--last", type=int, required=True)
    p.add_argument("--out", required=True)
    _client_options(p)
    p.set_defaults(func=cmd_counts)

    p = sub.add_parser("plan", help="draw a seeded sample plan from a counts file")
    p.add_argument("--counts", required=True)
    p.add_argument("--first", type=int, default=2012)
    p.add_argument("--last", type=int, required=True)
    p.add_argument("--pages", type=int, default=7, help="pages per stratum")
    p.add_argument("--page-size", type=int, default=14)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("sample", help="fetch the planned pages to the raw folder (resumable)")
    p.add_argument("--plan", required=True)
    p.add_argument("--raw", required=True)
    _client_options(p)
    p.set_defaults(func=cmd_sample)

    p = sub.add_parser(
        "backfill-counts", help="count the other senders' records per year, up to --until"
    )
    p.add_argument("--first", type=int, default=2011)
    p.add_argument("--until", required=True, help="exclusive UTC bound (ISO time)")
    p.add_argument("--out", required=True)
    _client_options(p)
    p.set_defaults(func=cmd_backfill_counts)

    p = sub.add_parser("backfill", help="read the other senders' records to the raw folder")
    p.add_argument("--counts", required=True, help="a backfill-counts file taken before the run")
    p.add_argument("--raw", required=True)
    p.add_argument("--reserve", type=int, default=20, help="calls kept for the checks after it")
    p.add_argument("--max-response-mb", type=float, default=100.0)
    _client_options(p)
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("profile", help="aggregate the sample (no text)")
    p.add_argument("--plan", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_profile)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)
