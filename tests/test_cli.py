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
