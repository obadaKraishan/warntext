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

from warntext import __version__, hfpage
from warntext import authorities as au
from warntext import backfill as bf
from warntext import check as ck
from warntext import client as cl
from warntext import olson as ol
from warntext import probe as pr
from warntext import profile as pf
from warntext import rebuild as rb
from warntext import release as rl
from warntext import sample as sm
from warntext import sheet as sh
from warntext import tables as tb
from warntext import update as up

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
    """Rebuild the text layer from the record layer, reading each message from FEMA's API.

    Withheld messages are never read; messages whose text is already in the folder are reported
    as already in the release and not read again. Prints counts (and, with --ids, each id's fate).
    """
    messages = pq.read_table(Path(args.records) / "messages.parquet").to_pylist()
    kinds = set(args.kinds.split(",")) if args.kinds else None
    ids = set(args.ids.split(",")) if args.ids else None
    todo = rb.plan(messages, kinds, rb.released_ids(args.records), ids)
    if args.limit:
        todo["read"] = todo["read"][: args.limit]
    if ids is not None:
        known = {m["message_id"] for m in messages}
        fate = {m["message_id"]: what for what, ms in todo.items() for m in ms}
        words = {
            "withheld": "withheld by the privacy rules: not read",
            "already": "already in the release: not read again",
            "read": "to read from FEMA",
            "other": "a sender kind not asked for: not read",
        }
        for i in sorted(ids):
            print(f"  {i}: {words[fate[i]] if i in fate else 'not in the record layer'}")
        if ids - known:
            print(f"{len(ids - known)} id(s) are not in {args.records}.")
    print(
        f"Withheld (not read): {len(todo['withheld'])}; already in the release: "
        f"{len(todo['already'])}; other kinds: {len(todo['other'])}; to read: {len(todo['read'])}."
    )
    if not todo["read"]:
        print("Nothing to read from FEMA; no request was made.")
        return 0
    c = _client(args)
    need = -(-len(todo["read"]) // args.batch)
    left = c.budget.max_calls - c.budget.calls
    if need > left:
        print(f"Rebuilding needs {need} calls but only {left} are left under the cap.")
        return 2
    rows, stats = rb.rebuild(c, todo["read"], batch=args.batch)
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


def _first_lines(args: argparse.Namespace) -> tuple[str, ...]:
    """The guide's opening lines a sheet command was given (the sheet-2 line by default)."""
    if args.sheet_3_opening:
        return sh.SHEET_3_FIRST_LINES
    return tuple(args.first_line) if args.first_line else (sh.GUIDE_FIRST_LINE,)


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
    left_out = 0
    if args.exclude_key:
        keys = [row for path in args.exclude_key for row in sh.read_key(path).values()]
        used_groups, used_texts = sh.used_by(keys, groups, texts)
        before = len(items)
        items = sh.without_used(items, groups, used_groups, used_texts)
        left_out = before - len(items)
    items = sh.one_per_text_group(items, groups, args.seed)
    chosen = sh.draw(items, args.seed, args.rows)
    first_lines = _first_lines(args)
    paths = sh.write(chosen, args.out, args.name, first_lines=first_lines)
    made = {
        "seed": args.seed,
        "candidates": len(items),
        "earlier_keys": len(args.exclude_key or []),
        "units_left_out_as_used": left_out,
        **sh.strata(chosen),
    }
    (Path(args.out) / f"{args.name}_strata.json").write_text(
        json.dumps(made, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"{made['rows']} texts on the sheet from {len(items):,} candidates "
        f"({left_out:,} units left out as used by an earlier sheet); by unit "
        f"{made['by_unit']}; workbook {paths['workbook']}, key {paths['key']}, "
        f"guide {paths['guide']}."
    )
    return 0


def cmd_sheet_repeat(args: argparse.Namespace) -> int:
    """A blind second pass over an earlier sheet's rows: the rows that differed from the rules
    (from that sheet's check), plus fillers, in a new order with new row ids. Counts only."""
    key = sh.read_key(args.key)
    keep: set[int] = set()
    if args.keep_from:
        result = json.loads(Path(args.keep_from).read_text(encoding="utf-8"))
        for r in result["codes"].values():
            keep |= set(r["rows_that_differ"])
    leave_out = set(args.leave_out or [])
    if keep & leave_out:
        raise SystemExit(f"Rows {sorted(keep & leave_out)} are both kept and left out.")
    others = set(key) - keep - leave_out
    order = sh.repeat_order(keep, others, args.fillers, args.seed)
    tables = Path(args.tables) / "alerts"
    texts = []
    for name in ("text_federal", "text_other"):
        texts += pq.read_table(tables / f"{name}.parquet").to_pylist()
    items = sh.items_for_key({r: key[r] for r in order}, texts)
    same = None
    if args.check_against:
        earlier = sh.texts_of_workbook(args.check_against)
        same = sum(earlier.get(r) == items[r].text for r in order)
        if same != len(order):
            raise SystemExit(
                f"{len(order) - same} texts differ from the earlier workbook's; nothing written."
            )
    chosen = [items[r] for r in order]
    first_lines = _first_lines(args)
    paths = sh.write(chosen, args.out, args.name, earlier_rows=order, first_lines=first_lines)
    made = {
        "seed": args.seed,
        "earlier_key": Path(args.key).name,
        "rows": len(order),
        "kept_rows": len(keep),
        "fillers": args.fillers,
        "left_out": sorted(leave_out),
        "texts_same_as_earlier_workbook": same,
        **sh.strata(chosen),
    }
    (Path(args.out) / f"{args.name}_strata.json").write_text(
        json.dumps(made, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"{len(order)} rows ({len(keep)} kept, {args.fillers} fillers, {len(leave_out)} left "
        f"out); texts the same as the earlier workbook's: {same}; by unit {made['by_unit']}; "
        f"workbook {paths['workbook']}, key {paths['key']}."
    )
    return 0


def cmd_sheet_repeat_check(args: argparse.Namespace) -> int:
    """One person's two passes over the same texts: consistency per code, and where the second
    pass took the differing answers. Counts and row numbers only."""
    first = sh.read_filled(args.first)
    second = sh.read_filled(args.second)
    second_key = sh.read_key(args.second_key)
    codes = pq.read_table(Path(args.tables) / "alerts" / "codes.parquet").to_pylist()
    earlier_key = sh.read_key(args.first_key)
    rules = sh.rules_by_row(
        {int(k["earlier_row"]): earlier_key[int(k["earlier_row"])] for k in second_key.values()},
        codes,
    )
    result = sh.repeat_check(first, second, second_key, rules)
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for field, r in result["codes"].items():
        a = "n/a" if r["alpha"] is None else f"{r['alpha']:.2f}"
        print(
            f"{field}: {r['rows']} rows, the two passes agree {r['agreement']}, alpha {a}; of "
            f"{r['first_differed_from_rules']} answers that differed from the rules, "
            f"{r['second_stood_by_first']} stood and {r['second_sided_with_rules']} turned; "
            f"{r['new_differences']} new differences"
        )
    return 0


def cmd_sheet_resolve(args: argparse.Namespace) -> int:
    """The resolution list: every answer where the two passes differ, blind to both passes and
    to the rules. Counts only."""
    result = json.loads(Path(args.repeat_check).read_text(encoding="utf-8"))
    passes_differ = {f: r["passes_differ_rows"] for f, r in result["codes"].items()}
    entries = sh.resolution_order(passes_differ, args.seed)
    repeat_key = sh.read_key(args.repeat_key)
    tables = Path(args.tables) / "alerts"
    texts = []
    for name in ("text_federal", "text_other"):
        texts += pq.read_table(tables / f"{name}.parquet").to_pylist()
    rows = sorted({row for row, _ in entries})
    items = sh.items_for_key({r: repeat_key[r] for r in rows}, texts)
    if args.check_against:
        earlier = sh.texts_of_workbook(args.check_against)
        differ = sum(earlier.get(r) != items[r].text for r in rows)
        if differ:
            raise SystemExit(f"{differ} texts differ from the repeat workbook's; nothing written.")
    paths = sh.write_resolution(entries, items, repeat_key, args.out, args.name)
    by_code = {f: len(v) for f, v in passes_differ.items()}
    print(
        f"{len(entries)} answers to resolve, in {len(rows)} texts; by code {by_code}; "
        f"workbook {paths['workbook']}, key {paths['key']}."
    )
    return 0


def cmd_sheet_consolidate(args: argparse.Namespace) -> int:
    """The consolidated answers of a sheet (first pass, with the resolution where the two passes
    differed), and the rules of each table against them: development figures. Counts only."""
    first = sh.read_filled(args.first)
    key = sh.read_key(args.key)
    merged = sh.consolidate(
        first, sh.read_resolution(args.resolution), sh.read_key(args.resolution_key)
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sh.write_consolidated(merged, out / "consolidated.csv")
    results = {}
    for item in args.tables:
        label, _, path = item.partition("=")
        codes = pq.read_table(Path(path) / "alerts" / "codes.parquet").to_pylist()
        results[label] = sh.check_consolidated(merged, key, codes)
    (out / "consolidated_check.json").write_text(
        json.dumps(results, indent=1) + "\n", encoding="utf-8"
    )
    for label, r in results.items():
        line = ", ".join(
            f"{f} {'n/a' if c['alpha'] is None else format(c['alpha'], '.2f')}"
            for f, c in r["codes"].items()
        )
        print(f"{label} (development figure): {line}")
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


def cmd_update(args: argparse.Namespace) -> int:
    """The weekly update (or, with --init, the state it starts from). Prints counts only."""
    if args.init:
        counts, until = read_year_counts(args.counts or [])
        up.init_state(args.state, args.init, {y: n for y, (n, _) in counts.items()}, until)
        print(f"State started at {args.state}: raw {args.init}, window end {until}.")
        return 0
    if args.rebuild:
        result = up.rebuild_from_state(
            args.state, args.raw_root, args.out, args.private, args.codebook_version
        )
        failures = result.pop("failures")
        build_summary = result.pop("summary")
        out = Path(args.summary)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(build_summary, indent=1, default=str) + "\n", encoding="utf-8")
        print(
            f"Rebuilt {result['records']:,} records from the state's raw folders (no request), "
            f"FEMA list {result['fema_list']}; check {result['check']}. Summary in {out}."
        )
        for f in failures:
            print(f"  FAIL {f}")
        return 0 if not failures else 1
    c = _client(args)
    summary = up.run_update(
        c,
        args.state,
        args.raw_root,
        args.out,
        args.private,
        until=args.until,
        fetch_list=not args.no_list,
    )
    failures = summary.pop("failures")
    out = Path(args.summary)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(
        f"Window {summary['window']['start']} to {summary['window']['until']}: "
        f"{summary['new_records']:,} new records, {summary['new_real_alerts']:,} new real alerts; "
        f"{summary['calls']} calls; check {summary['check']}. Summary in {out}."
    )
    for f in failures:
        print(f"  FAIL {f}")
    return 0 if not failures else 1


def cmd_release_build(args: argparse.Namespace) -> int:
    """Build the release pack (record layer, released codes, the text layer) from the tables."""
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    kinds = tuple(k.strip() for k in args.text_kinds.split(",") if k.strip())
    m = rl.build_pack(
        args.tables,
        args.out,
        args.version,
        state["until"],
        args.retrieved,
        args.codebook_version,
        text_kinds=kinds,
    )
    kaggle = Path(f"{args.out.rstrip('/')}-kaggle")
    rl.build_kaggle(args.out, kaggle)
    print(
        f"Pack {args.version} in {args.out}: {len(m['files'])} files, {m['rows']:,} rows, "
        f"{m['bytes'] / 1_000_000:.1f} MB; records sent before {state['until']}."
    )
    return 0


def cmd_release_card(args: argparse.Namespace) -> int:
    """A card-only fix: the pack's README.md written again; data files and manifest untouched."""
    changed = rl.rewrite_card(args.pack)
    manifest = json.loads((Path(args.pack) / "manifest.json").read_text(encoding="utf-8"))
    tables = rl.pack_tables(manifest.get("text_kinds", rl.FEDERAL_ONLY))
    readme = (Path(args.pack) / "README.md").read_text("utf-8")
    problems = rl.card_metadata_problems(readme, tables, manifest.get("rows"))
    print(
        f"README.md in {args.pack} written again from the template and the manifest "
        f"({'changed' if changed else 'unchanged'}); the data files and the manifest were not "
        "touched."
    )
    for p in problems:
        print(f"  FAIL README.md: {p}")
    return 1 if problems else 0


def cmd_release_check(args: argparse.Namespace) -> int:
    """The pack's own check: its files, its card, and the release check of its tables."""
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    counts = {int(y): n for y, n in state["year_counts"].items()}
    failures = rl.check_pack(
        args.pack, ck.read_sender_values(args.private), ck.read_identifiers(args.private), counts
    )
    kaggle = Path(f"{str(args.pack).rstrip('/')}-kaggle")
    if kaggle.exists():
        failures += rl.check_kaggle(kaggle)
    if failures:
        print(f"RELEASE PACK CHECK FAILED: {len(failures)} problem(s).")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print(
        "Release pack check passed: files, manifest, card, the release check of its tables, "
        "and the Kaggle mirror's folder."
    )
    return 0


def cmd_page_visibility(args: argparse.Namespace) -> int:
    """Whether the dataset is public, asked with no credentials at all. Exits 0 as expected."""
    try:
        state, status = hfpage.visibility(args.dataset)
    except hfpage.PageCheckError as exc:
        print(f"SIGNED-OUT CHECK FAILED, nothing could be told: {exc}")
        return 2
    print(
        f"Signed out (no token, no cookie, no netrc): {args.dataset} answered HTTP {status}: "
        f"{state}."
    )
    if state != args.expect.replace("-", " "):
        print(f"STOP: {args.dataset} is {state}, and this step expects it {args.expect}.")
        return 1
    return 0


def cmd_page_headings(args: argparse.Namespace) -> int:
    """The card's headings against the rendered page's, in order, down to the last one."""
    card = Path(args.card).read_text(encoding="utf-8")
    if args.page:
        html = Path(args.page).read_text(encoding="utf-8")
    else:
        try:
            r = hfpage.signed_out_get(args.url)
        except hfpage.PageCheckError as exc:
            print(f"SIGNED-OUT CHECK FAILED: {exc}")
            return 2
        if r.status_code != 200:
            print(f"STOP: {args.url} answered HTTP {r.status_code} signed out; nothing to compare.")
            return 1
        html = r.text
    want = hfpage.card_headings(card)
    problems = hfpage.heading_problems(card, html)
    missing = sum(p.startswith("not on the page") for p in problems)
    last = want[-1] if want else None
    shown = "shown" if last and not any(repr(last) in p for p in problems) else "NOT SHOWN"
    print(f"The card has {len(want)} headings; the page shows {len(want) - missing}.")
    print(f"The last heading, {last!r}: {shown}.")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 1 if problems else 0


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
    p.add_argument("--name", default="hand_sheet", help="file names: NAME.xlsx, NAME_key.csv ...")
    p.add_argument(
        "--exclude-key",
        action="append",
        help="an earlier sheet's key: its text groups and texts are left out (repeatable)",
    )
    p.add_argument("--first-line", action="append", help="the guide's opening lines (repeatable)")
    p.add_argument(
        "--sheet-3-opening", action="store_true", help="open the guide with SHEET_3_FIRST_LINES"
    )
    p.set_defaults(func=cmd_sheet)

    p = sub.add_parser(
        "sheet-repeat", help="a blind second pass over an earlier sheet's rows (local files)"
    )
    p.add_argument("--key", required=True, help="the earlier sheet's key")
    p.add_argument("--tables", required=True, help="the tables the earlier sheet was drawn from")
    p.add_argument("--keep-from", help="the earlier sheet's check: every row that differed is kept")
    p.add_argument("--leave-out", type=int, action="append", help="an earlier row to leave out")
    p.add_argument("--fillers", type=int, required=True, help="other rows drawn at random")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--check-against", help="the earlier workbook: its texts must be the same")
    p.add_argument("--out", required=True, help="a folder under data/interim (never tracked)")
    p.add_argument("--name", required=True, help="file names: NAME.xlsx, NAME_key.csv ...")
    p.add_argument("--first-line", action="append", help="the guide's opening lines (repeatable)")
    p.add_argument(
        "--sheet-3-opening", action="store_true", help="open the guide with SHEET_3_FIRST_LINES"
    )
    p.set_defaults(func=cmd_sheet_repeat)

    p = sub.add_parser(
        "sheet-repeat-check", help="one person's two passes: consistency and where answers went"
    )
    p.add_argument("--first", required=True, help="the earlier sheet, filled")
    p.add_argument("--first-key", required=True, help="the earlier sheet's key")
    p.add_argument("--second", required=True, help="the repeat, filled")
    p.add_argument("--second-key", required=True, help="the repeat's key (with earlier_row)")
    p.add_argument("--tables", required=True, help="the rules' tables the earlier sheet scored")
    p.add_argument("--out", required=True, help="JSON file for the result (counts, row numbers)")
    p.set_defaults(func=cmd_sheet_repeat_check)

    p = sub.add_parser("sheet-resolve", help="the resolution list where two passes differ")
    p.add_argument("--repeat-check", required=True, help="sheet-repeat-check's result")
    p.add_argument("--repeat-key", required=True, help="the repeat's key")
    p.add_argument("--tables", required=True, help="the tables the sheets were drawn from")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--check-against", help="the repeat workbook: its texts must be the same")
    p.add_argument("--out", required=True, help="a folder under data/interim (never tracked)")
    p.add_argument("--name", required=True, help="file names: NAME.xlsx and NAME_key.csv")
    p.set_defaults(func=cmd_sheet_resolve)

    p = sub.add_parser(
        "sheet-consolidate", help="consolidated answers and the rules against them (development)"
    )
    p.add_argument("--first", required=True, help="the sheet, filled (first pass)")
    p.add_argument("--key", required=True, help="the sheet's key")
    p.add_argument("--resolution", required=True, help="the resolution list, filled")
    p.add_argument("--resolution-key", required=True)
    p.add_argument(
        "--tables", action="append", required=True, help="LABEL=PATH of a build (repeatable)"
    )
    p.add_argument("--out", required=True, help="a folder under data/interim (never tracked)")
    p.set_defaults(func=cmd_sheet_consolidate)

    p = sub.add_parser("sheet-check", help="alpha per code between a filled sheet and the rules")
    p.add_argument("--sheet", required=True, help="the filled hand_sheet.xlsx")
    p.add_argument("--key", required=True, help="hand_sheet_key.csv")
    p.add_argument("--tables", required=True)
    p.add_argument("--out", help="JSON file for the result (counts and row numbers only)")
    p.set_defaults(func=cmd_sheet_check)

    p = sub.add_parser("update", help="the weekly update: new records, FEMA's list, rebuild, check")
    p.add_argument("--state", required=True, help="the state file (next to the raw pages)")
    p.add_argument("--raw-root", default="data/raw", help="the folder that holds the raw folders")
    p.add_argument("--out", default="data/interim/tables")
    p.add_argument("--private", default="data/interim/private")
    p.add_argument("--summary", default="data/interim/update/summary.json")
    p.add_argument("--until", help="exclusive UTC end (default: the newest hour 25 h old)")
    p.add_argument("--no-list", action="store_true", help="keep the packaged FEMA list")
    p.add_argument(
        "--rebuild", action="store_true", help="rebuild from the state's raw folders, no request"
    )
    p.add_argument(
        "--codebook-version",
        default=tb.CODEBOOK_VERSIONS[0],
        choices=tb.CODEBOOK_VERSIONS,
        help="with --rebuild: the content codes' rules (3 is a draft, built into its own folder)",
    )
    p.add_argument("--init", nargs="+", help="start the state from these raw folders, no calls")
    p.add_argument("--counts", nargs="*", help="with --init: backfill-counts files")
    _client_options(p, since_required=False, max_calls=30, max_bytes=100_000_000)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("release", help="the release pack: build it, or check it")
    rsub = p.add_subparsers(dest="release_command", required=True)
    q = rsub.add_parser("build", help="write the pack: record layer, released codes, text layer")
    q.add_argument("--tables", default="data/interim/tables")
    q.add_argument("--state", default="data/raw/update-state.json", help="for the records' end")
    q.add_argument("--out", required=True, help="a new folder under data/release/")
    q.add_argument("--version", required=True)
    q.add_argument("--retrieved", required=True, help="the access date to cite (YYYY-MM-DD)")
    q.add_argument(
        "--codebook-version",
        default=rl.CODE_STATUS_VERSION,
        help="the codes' version the release statuses were measured on",
    )
    q.add_argument(
        "--text-kinds",
        default=",".join(rl.TEXT_KINDS),
        help="sender kinds whose text is released (default: %(default)s; 'federal' builds the "
        "federal text only)",
    )
    q.set_defaults(func=cmd_release_build)
    q = rsub.add_parser("card", help="a card-only fix: README.md again, data files untouched")
    q.add_argument("--pack", required=True)
    q.set_defaults(func=cmd_release_card)
    q = rsub.add_parser("check", help="the pack's own check (exits 1 on any failure)")
    q.add_argument("--pack", required=True)
    q.add_argument("--private", default="data/interim/private")
    q.add_argument("--state", default="data/raw/update-state.json", help="for the year counts")
    q.set_defaults(func=cmd_release_check)

    p = sub.add_parser("page", help="checks of the dataset page on Hugging Face (signed out)")
    psub = p.add_subparsers(dest="page_command", required=True)
    q = psub.add_parser("visibility", help="public or not, asked with no credentials at all")
    q.add_argument("--dataset", default="obadakr/warntext")
    q.add_argument("--expect", required=True, choices=("public", "not-public"))
    q.set_defaults(func=cmd_page_visibility)
    q = psub.add_parser("headings", help="the card's headings on the rendered page, in order")
    q.add_argument("--card", required=True, help="the pack's README.md")
    where = q.add_mutually_exclusive_group(required=True)
    where.add_argument("--url", help="the page, read signed out")
    where.add_argument("--page", help="a saved copy of the page (HTML)")
    q.set_defaults(func=cmd_page_headings)

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
