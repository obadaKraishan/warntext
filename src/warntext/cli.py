"""The ``warntext`` command line.

Every command that talks to OpenFEMA uses the polite client: the session's calls and bytes are
counted from the usage log since ``--since``, and the run stops at the caps.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import pyarrow.parquet as pq

from warntext import __version__
from warntext import authorities as au
from warntext import backfill as bf
from warntext import check as ck
from warntext import client as cl
from warntext import olson as ol
from warntext import probe as pr
from warntext import profile as pf
from warntext import rebuild as rb
from warntext import sample as sm
from warntext import sheet as sh
from warntext import tables as tb

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
    if args.years:
        years = [y for y in years if y in {int(x) for x in args.years.split(",")}]
    plan = bf.count_plan(years, args.until, args.method)
    counts = pr.run_counts(
        c, plan, save_to=args.out, run_at=cl.now_utc(), until=args.until, method=args.method
    )
    failed = [x.name for x in counts if x.count is None]
    print(f"{len(counts) - len(failed)} counts saved to {args.out}; {c.budget.calls} calls so far.")
    if failed:
        print(f"Not answered: {', '.join(failed)}. Try --method difference for these years.")
    return 1 if failed else 0


def read_year_counts(paths: Sequence[Path | str]) -> tuple[dict[int, tuple[int, str]], str]:
    """The other senders' count per year (and how it was taken) and the ``until`` bound.

    Reads one or more ``backfill-counts`` files; they must share the same ``until``.
    """
    entries: list[dict] = []
    untils = set()
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        entries += data["counts"]
        untils.add(data["facts"]["until"])
    if len(untils) != 1:
        raise SystemExit(f"The count files use different --until bounds ({sorted(untils)}).")
    return bf.year_counts(entries), untils.pop()


def cmd_backfill(args: argparse.Namespace) -> int:
    """Read every page of the other senders' records to the raw folder (resumable)."""
    counts, until = read_year_counts(args.counts)
    years = bf.years_until(args.first, until)
    missing = [y for y in years if y not in counts]
    if missing:
        raise SystemExit(f"No count for {missing}; run `warntext backfill-counts` for them.")
    expected = {y: counts[y][0] for y in years}
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
            f"{line.year} page {line.page}: {line.records} records, {line.bytes:,} bytes, "
            f"{line.seconds:.1f} s; {c.budget.calls} calls, {c.budget.nbytes:,} bytes so far",
            flush=True,
        )

    new = bf.run(c, expected, until, raw, on_page=show)
    lines = bf.read_manifest(raw / "manifest.csv")
    got = sum(x.records for x in lines)
    print(f"{len(new)} pages fetched now; {len(lines)} pages and {got:,} records in all.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Parse the backfill and write both layers as Parquet, with a summary of aggregates."""
    b = tb.build_from_raw(args.raw)
    counts = tb.write(b, args.out, args.private)
    b.summary["rows_written"] = counts
    out = Path(args.summary)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(b.summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(
        f"{b.summary['records']:,} records, {b.summary['messages']:,} messages; tables in "
        f"{args.out}, summary (aggregates only) in {out}."
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """The release check. Exits 1, loudly, on any failure."""
    server = None
    if args.counts:
        counts, _ = read_year_counts(args.counts)
        server = {y: n for y, (n, _how) in counts.items()}
    failures = ck.check(
        ck.load(args.tables),
        ck.read_sender_values(args.private),
        server,
        ck.read_identifiers(args.private),
    )
    if failures:
        print(f"RELEASE CHECK FAILED: {len(failures)} problem(s).")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print(
        "Release check passed: counts, withheld text, parameters, sender values, raw "
        "identifiers, people-code times, sender kinds, ids, sources."
    )
    return 0


def cmd_text(args: argparse.Namespace) -> int:
    """Rebuild the text layer from the record layer, reading each message from FEMA's API."""
    messages = pq.read_table(Path(args.records) / "messages.parquet").to_pylist()
    kinds = set(args.kinds.split(",")) if args.kinds else None
    todo = rb.wanted(messages, kinds)
    if args.ids:
        keep = set(args.ids.split(","))
        todo = [m for m in todo if m["message_id"] in keep]
    if args.limit:
        todo = todo[: args.limit]
    c = _client(args)
    need = -(-len(todo) // args.batch)
    left = c.budget.max_calls - c.budget.calls
    if need > left:
        print(f"Rebuilding needs {need} calls but only {left} are left under the cap.")
        return 2
    rows, stats = rb.rebuild(c, todo, batch=args.batch)
    counts = rb.write(rows, args.out)
    print(f"{dict(stats)}; rows written: {counts}; {c.budget.calls} calls so far.")
    return 0


def cmd_authorities(args: argparse.Namespace) -> int:
    """Read FEMA's list of alerting authorities (one request) and write it as the snapshot CSV."""
    c = _client(args)
    resp = c.get(au.PAGE_URL)
    if resp.status != 200:
        print(f"FEMA's page answered HTTP {resp.status}; the snapshot was not changed.")
        return 1
    rows = au.parse_page(resp.content.decode("utf-8", errors="replace"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(au.to_csv(rows), encoding="utf-8")
    print(
        f"{len(rows):,} alerting authorities written to {out}. Update SNAPSHOT_PAGE_UPDATED and "
        "SNAPSHOT_RETRIEVED in warntext/authorities.py if this replaces the tracked snapshot."
    )
    return 0


def cmd_compare_olson(args: argparse.Namespace) -> int:
    """Apply Olson et al.'s filters to the tables and set the shares beside theirs."""
    tables = Path(args.tables)
    messages = []
    for c in ("alerts", "tests"):
        messages += pq.read_table(tables / c / "messages.parquet").to_pylist()
    codes = pq.read_table(tables / "alerts" / "codes.parquet").to_pylist()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    variants = {
        "main": {"people": "missing", "unique_texts": False},
        "all_people_codes_out": {"people": "all", "unique_texts": False},
        "unique_texts": {"people": "missing", "unique_texts": True},
    }
    results = {name: ol.compare(messages, codes, **kw) for name, kw in variants.items()}
    for r in results.values():
        r["gaps_over_5_points"] = ol.gaps(r)
    (out / "olson_compare.json").write_text(
        json.dumps(results, indent=1, default=str) + "\n", encoding="utf-8"
    )
    (out / "olson_compare.md").write_text(
        "\n".join(f"## {name}\n\n{ol.markdown(r)}" for name, r in results.items()),
        encoding="utf-8",
    )
    main_steps = dict(results["main"]["steps"])
    print(
        f"{main_steps['texts in all']:,} texts (theirs 6,080); "
        f"{len(results['main']['gaps_over_5_points'])} shares differ by more than 5 points; "
        f"aggregates in {out}."
    )
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    """Draw the hand sheet (blind workbook and key) from the local tables. Prints counts only."""
    tables = Path(args.tables) / "alerts"
    messages = pq.read_table(tables / "messages.parquet").to_pylist()
    codes = pq.read_table(tables / "codes.parquet").to_pylist()
    texts = []
    for name in ("text_federal", "text_other"):
        texts += pq.read_table(tables / f"{name}.parquet").to_pylist()
    items = sh.candidates(messages, codes, texts)
    groups = {m["message_id"]: m["text_group"] for m in messages}
    items = sh.one_per_text_group(items, groups, args.seed)
    chosen = sh.draw(items, args.seed, args.rows)
    paths = sh.write(chosen, args.out)
    made = {"seed": args.seed, "candidates": len(items), **sh.strata(chosen)}
    (Path(args.out) / "hand_sheet_strata.json").write_text(
        json.dumps(made, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"{made['rows']} texts on the sheet from {len(items):,} candidates; by unit "
        f"{made['by_unit']}; workbook {paths['workbook']}, key {paths['key']}."
    )
    return 0


def cmd_sheet_check(args: argparse.Namespace) -> int:
    """Compare a filled hand sheet with the rules: alpha per code and the rows that differ."""
    filled = sh.read_filled(args.sheet)
    key = sh.read_key(args.key)
    codes = pq.read_table(Path(args.tables) / "alerts" / "codes.parquet").to_pylist()
    result = sh.check(filled, key, codes)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for field, r in result["codes"].items():
        a = "n/a" if r["alpha"] is None else f"{r['alpha']:.2f}"
        mark = "meets" if r["passes"] else "below"
        print(
            f"{field}: {r['rows_coded']} rows, agreement {r['agreement']}, alpha {a} "
            f"({mark} {sh.BAR:.2f}); rows that differ: {r['rows_that_differ']}"
        )
    return 0


def _client_options(
    p: argparse.ArgumentParser,
    since_required: bool = True,
    max_calls: int = cl.DEFAULT_MAX_CALLS,
    max_bytes: int = cl.DEFAULT_MAX_BYTES,
) -> None:
    p.add_argument("--log", default="data/usage_log.csv", help="request log (CSV)")
    p.add_argument(
        "--since",
        required=since_required,
        default=None if since_required else cl.now_utc(),
        help="UTC start of the session, for the caps" + ("" if since_required else " (now)"),
    )
    p.add_argument("--max-calls", type=int, default=max_calls)
    p.add_argument("--max-bytes", type=int, default=max_bytes)
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
    p.add_argument("--years", help="only these years, comma-separated")
    p.add_argument("--method", choices=["direct", "difference"], default="direct")
    p.add_argument("--out", required=True)
    _client_options(p)
    p.set_defaults(func=cmd_backfill_counts)

    p = sub.add_parser("backfill", help="read the other senders' records to the raw folder")
    p.add_argument(
        "--counts", required=True, nargs="+", help="backfill-counts files taken before the run"
    )
    p.add_argument("--first", type=int, default=2011)
    p.add_argument("--raw", required=True)
    p.add_argument("--reserve", type=int, default=20, help="calls kept for the checks after it")
    p.add_argument("--max-response-mb", type=float, default=100.0)
    _client_options(p)
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("build", help="parse the backfill and write both layers as Parquet")
    p.add_argument("--raw", required=True)
    p.add_argument("--out", required=True, help="folder for the tables")
    p.add_argument("--private", required=True, help="folder for the private sender file")
    p.add_argument("--summary", required=True, help="JSON file of aggregates")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("check", help="the release check (exits 1 on any failure)")
    p.add_argument("--tables", required=True)
    p.add_argument("--private", required=True)
    p.add_argument("--counts", nargs="*", help="backfill-counts files taken after the run")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("text", help="rebuild the text layer from the record layer and the API")
    p.add_argument("--records", required=True, help="a configuration folder of the record layer")
    p.add_argument("--out", required=True)
    p.add_argument("--kinds", help="sender kinds to rebuild, comma-separated (default: all)")
    p.add_argument("--ids", help="only these message ids, comma-separated")
    p.add_argument("--limit", type=int, help="at most this many messages")
    p.add_argument("--batch", type=int, default=rb.BATCH, help="record ids per request")
    # A full rebuild of the real alerts is about 1,800 requests of 20 ids.
    _client_options(p, since_required=False, max_calls=5000, max_bytes=5_000_000_000)
    p.set_defaults(func=cmd_text)

    p = sub.add_parser("authorities", help="read FEMA's list of alerting authorities to a CSV")
    p.add_argument("--out", required=True)
    _client_options(p, since_required=False, max_calls=5, max_bytes=5_000_000)
    p.set_defaults(func=cmd_authorities)

    p = sub.add_parser(
        "compare-olson", help="this corpus beside Olson et al.'s published shares (aggregates)"
    )
    p.add_argument("--tables", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_compare_olson)

    p = sub.add_parser("sheet", help="draw the blind hand sheet and its key (local files)")
    p.add_argument("--tables", required=True)
    p.add_argument("--out", required=True, help="a folder under data/interim (never tracked)")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--rows", type=int, default=sh.ROWS)
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser("sheet-check", help="alpha per code between a filled sheet and the rules")
    p.add_argument("--sheet", required=True, help="the filled hand_sheet.xlsx")
    p.add_argument("--key", required=True, help="hand_sheet_key.csv")
    p.add_argument("--tables", required=True)
    p.add_argument("--out", help="JSON file for the result (counts and row numbers only)")
    p.set_defaults(func=cmd_sheet_check)

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
