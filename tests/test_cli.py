import json

import pytest

from cap_samples import WEA_TWO_LANGUAGES, WEATHER_SERVICE
from warntext import __version__, cli, probe, sample


def test_version_flag_prints_the_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_arguments_prints_help(capsys):
    assert cli.main([]) == 0
    assert "usage: warntext" in capsys.readouterr().out


def counts_file(tmp_path, nws_2013=900):
    data = {
        "counts": [
            {"name": "year:2012", "count": 120},
            {"name": "year:2013", "count": 1000},
            {"name": "nws_year:2012", "count": 100},
            {"name": "nws_year:2013", "count": nws_2013},
        ]
    }
    path = tmp_path / "counts.json"
    path.write_text(json.dumps(data))
    return path


def test_strata_from_counts_splits_each_year(tmp_path):
    strata = cli.strata_from_counts(counts_file(tmp_path))
    assert strata == [
        sample.Stratum(2012, "nws", 100),
        sample.Stratum(2012, "other", 20),
        sample.Stratum(2013, "nws", 900),
        sample.Stratum(2013, "other", 100),
    ]


def test_strata_from_counts_refuses_missing_counts(tmp_path):
    with pytest.raises(SystemExit, match="counts are missing"):
        cli.strata_from_counts(counts_file(tmp_path, nws_2013=None))


def test_plan_writes_once(tmp_path, capsys):
    out = tmp_path / "plan.json"
    argv = ["plan", "--counts", str(counts_file(tmp_path)), "--last", "2013", "--seed", "3"]
    argv += ["--pages", "2", "--page-size", "10", "--out", str(out)]
    assert cli.main(argv) == 0
    plan = json.loads(out.read_text())
    assert plan["seed"] == 3
    assert len(plan["pages"]) == 8
    assert "pages" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="written once"):
        cli.main(argv)


class FakeClient:
    def __init__(self, answers):
        self.answers = list(answers)
        self.budget = type("B", (), {"calls": 0})()

    def get(self, url, params):
        self.budget.calls += 1
        return self.answers.pop(0)

    def clock(self):
        return "2026-11-15T00:00:00.000Z"


class Resp:
    def __init__(self, data, status=200):
        self._data = data
        self.content = json.dumps(data).encode()
        self.status = status
        self.seconds = 0.2

    def json(self):
        return self._data


def test_counts_saves_and_reports_unanswered(tmp_path, monkeypatch, capsys):
    answers = [Resp({"metadata": {"count": 5}}), Resp({}, status=500)]
    monkeypatch.setattr(cli, "_client", lambda args: FakeClient(answers))
    out = tmp_path / "c.json"
    argv = ["counts", "--first", "2020", "--last", "2020", "--out", str(out), "--since", "x"]
    assert cli.main(argv) == 1
    saved = json.loads(out.read_text())["counts"]
    assert saved[0]["count"] == 5
    assert saved[1]["count"] is None
    assert "Not answered: nws_year:2020" in capsys.readouterr().out


def test_nws_counts_prints_each_count_beside_its_exact_filter(tmp_path, monkeypatch, capsys):
    answers = [Resp({"metadata": {"count": n}}) for n in (769, 309, 12)] + [Resp({}, status=503)]
    monkeypatch.setattr(cli, "_client", lambda args: FakeClient(answers))
    out = tmp_path / "nws.json"
    until = "2023-10-02T17:00:00.000Z"
    argv = ["nws-counts", "--first-month", "2023-08", "--until", until, "--years", "2023"]
    assert cli.main([*argv, "--out", str(out), "--since", "x"]) == 1  # one count not answered
    printed = capsys.readouterr().out
    assert "nws_month:2023-08\t769\t$filter=(sent ge '2023-08-01T00:00:00.000Z' and sent lt " in (
        printed
    )
    assert "(sent ge '2023-10-01T00:00:00.000Z' and sent lt '2023-10-02T17:00:00.000Z')" in printed
    assert "(sender eq 'w-nws.webmaster@noaa.gov')" in printed
    assert "nws_year:2023\tnot answered" in printed
    saved = json.loads(out.read_text())
    assert [c["count"] for c in saved["counts"]] == [769, 309, 12, None]
    assert saved["facts"]["until"] == until
    with pytest.raises(SystemExit, match="more than --max-calls 2"):
        cli.main([*argv, "--out", str(out), "--since", "x", "--max-calls", "2"])


def test_sample_then_profile(tmp_path, monkeypatch, capsys):
    plan = {
        "strata": [
            {"year": 2015, "kind": "nws", "count": 50},
            {"year": 2015, "kind": "other", "count": 4},
        ],
        "pages": [
            {"year": 2015, "kind": "nws", "skip": 0, "top": 1},
            {"year": 2015, "kind": "other", "skip": 0, "top": 1},
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    bodies = [
        Resp({probe.ENTITY: [{"id": "n1", "originalMessage": WEATHER_SERVICE}]}),
        Resp({probe.ENTITY: [{"id": "o1", "originalMessage": WEA_TWO_LANGUAGES}]}),
    ]
    monkeypatch.setattr(cli, "_client", lambda args: FakeClient(bodies))
    raw = tmp_path / "raw"
    argv = ["sample", "--plan", str(plan_path), "--raw", str(raw), "--since", "x"]
    assert cli.main(argv) == 0
    assert "2 pages fetched now" in capsys.readouterr().out
    out = tmp_path / "profile.json"
    argv = ["profile", "--plan", str(plan_path), "--raw", str(raw), "--out", str(out)]
    assert cli.main(argv) == 0
    prof = json.loads(out.read_text())
    assert prof["kind"]["estimated_records"] == {"nws": 50, "other": 4}
    assert "Invented" not in out.read_text()


def test_client_reads_the_caps_from_the_log(tmp_path):
    log = tmp_path / "log.csv"
    log.write_text(
        "time,method,host,path,query,status,bytes,seconds\n"
        "2026-11-15T01:00:00.000Z,GET,www.fema.gov,/x,,200,10,0.1\n"
    )
    args = cli.build_parser().parse_args(
        [
            "sample",
            "--plan",
            "p",
            "--raw",
            "r",
            "--since",
            "2026-11-15T00:00:00Z",
            "--log",
            str(log),
        ]
    )
    c = cli._client(args)
    assert (c.budget.calls, c.budget.nbytes) == (1, 10)
    assert c.min_interval == 3.5


def backfill_counts_file(tmp_path, name, counts, until="2013-01-01T00:00:00.000Z"):
    path = tmp_path / name
    path.write_text(json.dumps({"facts": {"until": until}, "counts": counts}))
    return path


def test_read_year_counts_merges_files_and_refuses_mixed_bounds(tmp_path):
    a = backfill_counts_file(tmp_path, "a.json", [{"name": "other:2011", "count": 5}])
    b = backfill_counts_file(
        tmp_path, "b.json", [{"name": "all:2012", "count": 9}, {"name": "nws:2012", "count": 4}]
    )
    counts, until = cli.read_year_counts([a, b])
    assert counts == {2011: (5, "direct"), 2012: (5, "difference")}
    assert until == "2013-01-01T00:00:00.000Z"
    c = backfill_counts_file(tmp_path, "c.json", [], until="2014-01-01T00:00:00.000Z")
    with pytest.raises(SystemExit, match="different --until"):
        cli.read_year_counts([a, c])


def test_backfill_refuses_to_start_without_every_years_count(tmp_path):
    a = backfill_counts_file(tmp_path, "a.json", [{"name": "other:2012", "count": 5}])
    args = ["backfill", "--counts", str(a), "--raw", str(tmp_path / "raw"), "--since", "x"]
    with pytest.raises(SystemExit, match="No count for"):
        cli.main([*args, "--first", "2011", "--log", str(tmp_path / "log.csv")])


def test_backfill_stops_before_a_call_when_the_cap_is_too_small(tmp_path, capsys):
    a = backfill_counts_file(tmp_path, "a.json", [{"name": "other:2012", "count": 5000}])
    code = cli.main(
        [
            "backfill",
            "--counts",
            str(a),
            "--first",
            "2012",
            "--raw",
            str(tmp_path / "raw"),
            "--since",
            "2026-01-01T00:00:00.000Z",
            "--log",
            str(tmp_path / "log.csv"),
            "--max-calls",
            "15",
        ]
    )
    assert code == 2
    assert "Nothing was fetched" in capsys.readouterr().out
    assert not (tmp_path / "raw").exists()


def test_backfill_prints_one_line_per_page_without_text(tmp_path, capsys, monkeypatch):
    from warntext import client as cl

    class Resp:
        status = 200
        seconds = 0.2
        content = json.dumps(
            {"metadata": {}, probe.ENTITY: [{"id": "a", "sent": "2012-07-01T00:00:00.000Z"}]}
        ).encode()

    class Fake:
        budget = cl.Budget(max_calls=50)

        def get(self, url, params):
            self.budget.record(10)
            return Resp()

        def clock(self):
            return "2026-11-15T15:00:00.000Z"

    monkeypatch.setattr(cli, "_client", lambda args: Fake())
    a = backfill_counts_file(tmp_path, "a.json", [{"name": "other:2012", "count": 1}])
    raw = tmp_path / "raw"
    args = ["backfill", "--counts", str(a), "--first", "2012", "--raw", str(raw), "--since", "x"]
    assert cli.main(args) == 0
    out = capsys.readouterr().out
    assert "2012 page 0: 1 records" in out
    assert "1 pages and 1 records in all" in out


def test_build_and_text_commands_end_to_end(tmp_path, capsys, monkeypatch):
    from cap_samples import invented
    from test_check_rebuild import FakeClient, Resp
    from test_tables import COUNTY, record
    from warntext import backfill
    from warntext import client as cl

    rec = record(invented(identifier="EX-1", sender=COUNTY), "r01")

    class PageResp:
        status = 200
        seconds = 0.1
        content = json.dumps({"metadata": {}, probe.ENTITY: [rec]}).encode()

    class PageClient:
        def get(self, url, params):
            return PageResp()

        def clock(self):
            return "2026-11-15T15:00:00.000Z"

    raw = tmp_path / "raw"
    backfill.run(PageClient(), {2024: 1}, "2026-11-14T00:00:00.000Z", raw)
    out = tmp_path / "tables"
    args = ["build", "--raw", str(raw), "--out", str(out), "--private", str(tmp_path / "p")]
    assert cli.main([*args, "--summary", str(tmp_path / "summary.json")]) == 0
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["messages"] == 1
    assert "Invented" not in (tmp_path / "summary.json").read_text()

    fake = FakeClient([Resp([rec])])
    fake.budget = cl.Budget(max_calls=10)
    monkeypatch.setattr(cli, "_client", lambda a: fake)
    capsys.readouterr()
    rebuilt = tmp_path / "rebuilt"
    # The tables' folder holds r01's text: it is already in the release, and nothing is read.
    args = ["text", "--records", str(out / "alerts"), "--out", str(rebuilt)]
    assert cli.main([*args, "--ids", "r01,r99"]) == 0
    said = capsys.readouterr().out
    assert "r01: already in the release: not read again" in said
    assert "r99: not in the record layer" in said and "no request was made" in said
    assert len(fake.answers) == 1 and not rebuilt.exists()  # the one answer is still unread
    # A record layer without text (as on the Kaggle mirror): r01 is read from FEMA.
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "messages.parquet").write_bytes((out / "alerts" / "messages.parquet").read_bytes())
    args = ["text", "--records", str(bare), "--out", str(rebuilt)]
    assert cli.main([*args, "--limit", "5", "--ids", "r01"]) == 0
    said = capsys.readouterr().out
    assert "r01: to read from FEMA" in said and "'rebuilt': 1" in said
    assert (rebuilt / "text_other.parquet").exists()
    fake.budget = cl.Budget(max_calls=0)
    assert cli.main(args) == 2


def test_text_needs_no_session_start_and_allows_a_full_rebuild():
    args = cli.build_parser().parse_args(["text", "--records", "r", "--out", "o"])
    assert args.since.endswith("Z")
    assert args.max_calls == 5000
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["backfill", "--counts", "c", "--raw", "r"])


def test_authorities_writes_the_snapshot_from_one_request(tmp_path, monkeypatch, capsys):
    from test_authorities import PAGE

    class Page:
        status = 200
        content = PAGE.encode()

    class One:
        def __init__(self, answer):
            self.answer, self.calls = answer, 0

        def get(self, url, params=None):
            self.calls += 1
            return self.answer

    fake = One(Page())
    monkeypatch.setattr(cli, "_client", lambda args: fake)
    out = tmp_path / "aa.csv"
    assert cli.main(["authorities", "--out", str(out)]) == 0
    assert fake.calls == 1
    assert out.read_text().startswith("cog_id,name,state,fema_region,type\n900101,")
    assert "3 alerting authorities" in capsys.readouterr().out
    Page.status = 503
    assert cli.main(["authorities", "--out", str(tmp_path / "x.csv")]) == 1
    assert not (tmp_path / "x.csv").exists()


def test_compare_olson_writes_aggregates(tmp_path, capsys):
    from cap_samples import invented
    from test_tables import COUNTY, record, run
    from warntext import tables

    xml = invented(identifier="EX-1", sender=COUNTY, parameters=(("CMAMtext", "Leave now"),))
    b = run([record(xml, "r01")])
    tables.write(b, tmp_path / "t", tmp_path / "p")
    assert cli.main(["compare-olson", "--tables", str(tmp_path / "t"), "--out", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "olson_compare.json").read_text())
    assert set(data) == {"main", "all_people_codes_out", "unique_texts"}
    assert "texts (theirs 6,080)" in capsys.readouterr().out
    assert "Leave now" not in (tmp_path / "olson_compare.md").read_text()


def test_sheet_and_sheet_check_commands(tmp_path, capsys):
    from cap_samples import invented
    from test_sheet import filled_sheet
    from test_tables import COUNTY, record, run
    from warntext import sheet as sh
    from warntext import tables, xlsx

    recs = [
        record(
            invented(
                identifier=f"EX-{k}",
                sender=COUNTY,
                sent=f"2021-05-0{k}T10:00:00-05:00",
                headline=f"Invented headline {k}",
                parameters=(("CMAMtext", f"Brush fire {k}. Leave now."),),
            ),
            f"r0{k}",
        )
        for k in range(1, 5)
    ]
    tables.write(run(recs), tmp_path / "t", tmp_path / "p")
    out = tmp_path / "sheet"
    assert (
        cli.main(
            [
                "sheet",
                "--tables",
                str(tmp_path / "t"),
                "--out",
                str(out),
                "--seed",
                "5",
                "--rows",
                "4",
                "--sheet-3-opening",
            ]
        )
        == 0
    )
    assert "texts on the sheet" in capsys.readouterr().out
    guide = (out / "hand_sheet_guide.txt").read_text(encoding="utf-8")
    assert guide.startswith("This sheet is the only hand task of its day.")
    key = out / "hand_sheet_key.csv"
    assert key.exists() and (out / "hand_sheet.xlsx").exists()
    filled = filled_sheet(tmp_path / "filled.xlsx", {n: ["yes"] * 6 for n in range(1, 5)})
    res = tmp_path / "check.json"
    args = [
        "sheet-check",
        "--sheet",
        str(filled),
        "--key",
        str(key),
        "--tables",
        str(tmp_path / "t"),
    ]
    assert cli.main([*args, "--out", str(res), "--resamples", "50", "--seed", "3"]) == 0
    printed = capsys.readouterr().out
    assert "hazard: 4 rows scored (0 blank, 0 not coded by the rules)" in printed
    assert "Brush fire" not in printed and "[" not in printed  # counts only, no row list
    assert "50 bootstrap resamples, seed 3" in printed
    checked = json.loads(res.read_text())
    assert checked["rows_in_key"] == 4 and checked["bootstrap"] == {"resamples": 50, "seed": 3}

    # A blind second pass: the rows that differed, fillers, a row left out; texts as before.
    differed = tmp_path / "differed.json"
    differed.write_text(json.dumps({"codes": {"hazard": {"rows_that_differ": [2]}}}))
    repeat = [
        "sheet-repeat",
        "--key",
        str(key),
        "--tables",
        str(tmp_path / "t"),
        "--keep-from",
        str(differed),
        "--leave-out",
        "4",
        "--fillers",
        "1",
        "--seed",
        "9",
        "--first-line",
        "Invented opening line.",
        "--check-against",
        str(out / "hand_sheet.xlsx"),
        "--out",
        str(tmp_path / "pass2"),
        "--name",
        "second_pass",
    ]
    assert cli.main(repeat) == 0
    printed = capsys.readouterr().out
    assert "2 rows (1 kept, 1 fillers, 1 left out)" in printed and "Brush fire" not in printed
    new_key = sh.read_key(tmp_path / "pass2" / "second_pass_key.csv")
    earlier = sorted(int(k["earlier_row"]) for k in new_key.values())
    assert 2 in earlier and 4 not in earlier and len(earlier) == 2
    old_texts = sh.texts_of_workbook(out / "hand_sheet.xlsx")
    new_texts = sh.texts_of_workbook(tmp_path / "pass2" / "second_pass.xlsx")
    assert {new_texts[n] for n in new_key} == {old_texts[e] for e in earlier}
    assert (tmp_path / "pass2" / "second_pass_guide.txt").read_text().startswith("Invented opening")
    made = json.loads((tmp_path / "pass2" / "second_pass_strata.json").read_text())
    assert made["texts_same_as_earlier_workbook"] == 2 and made["left_out"] == [4]
    # A row both kept and left out, or a text that is not the earlier workbook's, stops it.
    with pytest.raises(SystemExit, match="both kept and left out"):
        cli.main([*repeat[:7], "--leave-out", "2", *repeat[9:]])
    other = filled_sheet(tmp_path / "other.xlsx", {n: [""] * 6 for n in range(1, 5)})
    with pytest.raises(SystemExit, match="differ from the earlier workbook"):
        cli.main([*repeat[:-5], str(other), repeat[-4], str(tmp_path / "p3"), *repeat[-2:]])
    assert not (tmp_path / "p3").exists()

    # Both passes scored against each other and the rules (counts and row numbers only).
    second = filled_sheet(tmp_path / "second.xlsx", {n: ["no"] * 6 for n in range(1, 3)})
    both = tmp_path / "both.json"
    check2 = [
        "sheet-repeat-check",
        "--first",
        str(filled),
        "--first-key",
        str(key),
        "--second",
        str(second),
        "--second-key",
        str(tmp_path / "pass2" / "second_pass_key.csv"),
        "--tables",
        str(tmp_path / "t"),
        "--out",
        str(both),
    ]
    assert cli.main([*check2, "--check-texts", "--resamples", "40", "--seed", "4"]) == 0
    printed = capsys.readouterr().out
    head = "hazard: 2 rows (0 blank in the first pass, 0 in the second), the two passes agree 0.0"
    assert head in printed and "Brush fire" not in printed
    assert "Texts the same as the earlier workbook's rows: 2 of 2." in printed
    assert "[" not in printed  # no row list on screen
    scored = json.loads(both.read_text())
    assert scored["codes"]["hazard"]["passes_differ_rows"] == [1, 2]
    assert scored["bootstrap"] == {"resamples": 40, "seed": 4}
    assert scored["texts_same_as_earlier_workbook"] == 2
    # A repeat whose texts are not the earlier rows' is not scored.
    wrong = [*check2[:6], str(tmp_path / "pass2" / "second_pass.xlsx"), *check2[7:-1]]
    with pytest.raises(SystemExit, match="texts differ from the earlier workbook's rows"):
        cli.main([*wrong, str(tmp_path / "never.json"), "--check-texts"])
    assert not (tmp_path / "never.json").exists()
    assert cli.main(check2) == 0
    capsys.readouterr()
    resolve = [
        "sheet-resolve",
        "--repeat-check",
        str(both),
        "--repeat-key",
        str(tmp_path / "pass2" / "second_pass_key.csv"),
        "--tables",
        str(tmp_path / "t"),
        "--seed",
        "3",
        "--check-against",
        str(tmp_path / "pass2" / "second_pass.xlsx"),
        "--out",
        str(tmp_path / "resolve"),
        "--name",
        "resolve",
    ]
    assert cli.main(resolve) == 0
    printed = capsys.readouterr().out
    assert "answers to resolve, in 2 texts" in printed and "Brush fire" not in printed
    assert len(sh.read_key(tmp_path / "resolve" / "resolve_key.csv")) >= 2
    with pytest.raises(SystemExit, match="differ from the repeat workbook"):
        cli.main([*resolve[:-5], str(other), *resolve[-4:]])
    # Consolidated answers: the resolution filled with "no" everywhere.
    res_dir = tmp_path / "resolve"
    rows = [[c for c, _ in r] for r in sh.resolution_sheet([]).rows]
    n_res = len(sh.read_key(res_dir / "resolve_key.csv"))
    rows += [[str(n), "", "", "", "no", ""] for n in range(1, n_res + 1)]
    xlsx.write_workbook(
        res_dir / "filled.xlsx",
        xlsx.Sheet("Resolution", [[(c, sh._TEXT) for c in r] for r in rows]),
    )
    consolidate = [
        "sheet-consolidate",
        "--first",
        str(filled),
        "--key",
        str(key),
        "--resolution",
        str(res_dir / "filled.xlsx"),
        "--resolution-key",
        str(res_dir / "resolve_key.csv"),
        "--tables",
        f"v={tmp_path / 't'}",
        "--out",
        str(tmp_path / "cons"),
    ]
    assert cli.main(consolidate) == 0
    assert "v (development figure): hazard" in capsys.readouterr().out
    data = json.loads((tmp_path / "cons" / "consolidated_check.json").read_text())
    assert data["v"]["figure"] == "development" and data["v"]["rows_in_key"] == 4
    assert (tmp_path / "cons" / "consolidated.csv").exists()


def test_update_command_starts_the_state_then_runs(tmp_path, monkeypatch, capsys):
    from test_update import Server, rec
    from warntext import backfill

    old = [rec(1, "2026-11-10T10:00:00-05:00")]
    new = [rec(4, "2026-11-15T10:00:00-05:00")]
    raw = tmp_path / "raw"
    backfill.run(Server(old), {2026: 1}, "2026-11-14T00:00:00.000Z", raw / "backfill")
    counts = tmp_path / "counts.json"
    counts.write_text(
        json.dumps(
            {
                "facts": {"until": "2026-11-14T00:00:00.000Z"},
                "counts": [{"name": "other:2026", "count": 1}],
            }
        )
    )
    state = raw / "update-state.json"
    init = ["update", "--state", str(state), "--init", "backfill", "--counts", str(counts)]
    assert cli.main(init) == 0
    monkeypatch.setattr(cli, "_client", lambda args: Server(old + new))
    args = ["update", "--state", str(state), "--raw-root", str(raw), "--until"]
    args += ["2026-11-18T00:00:00.000Z", "--out", str(tmp_path / "t"), "--private"]
    args += [str(tmp_path / "p"), "--summary", str(tmp_path / "s.json")]
    assert cli.main(args) == 2  # the codebook version is always named
    assert "Give --codebook-version" in capsys.readouterr().out
    assert cli.main([*args, "--codebook-version", "3"]) == 0
    printed = capsys.readouterr().out
    assert "1 new records" in printed and "check passed" in printed
    assert json.loads((tmp_path / "s.json").read_text())["new_real_alerts"] == 1
    again = ["update", "--state", str(state), "--raw-root", str(raw), "--rebuild", "--out"]
    again += [str(tmp_path / "t2"), "--private", str(tmp_path / "p2")]
    again += ["--codebook-version", "3"]
    assert cli.main([*again, "--summary", str(tmp_path / "b.json")]) == 0
    assert "no request" in capsys.readouterr().out
