import json

import pytest

from warntext import probe


class Resp:
    def __init__(self, data, status=200, seconds=0.5):
        self._data = data
        self.status = status
        self.seconds = seconds

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, answers):
        self.answers = list(answers)
        self.params = []

    def get(self, url, params):
        assert url == probe.ENDPOINT
        self.params.append(params)
        return self.answers.pop(0)


def test_year_filter_covers_one_calendar_year():
    assert probe.year_filter(2015) == (
        "sent ge '2015-01-01T00:00:00.000Z' and sent lt '2016-01-01T00:00:00.000Z'"
    )


def test_event_code_filter_uses_the_hierarchical_path():
    assert probe.event_code_filter("CAE") == "contains(infos/eventCode/value,'CAE')"


def test_both_joins_filters_and_skips_empty_ones():
    assert probe.both("a eq 1", None, "b eq 2") == "(a eq 1) and (b eq 2)"
    assert probe.both(None) is None


def test_count_asks_for_one_id_and_reads_the_total():
    client = FakeClient([Resp({"metadata": {"count": 42}, probe.ENTITY: [{"id": "x"}]})])
    n, seconds = probe.count(client, "status eq 'Actual'")
    assert (n, seconds) == (42, 0.5)
    params = client.params[0]
    assert params["$top"] == 1
    assert params["$select"] == "id"
    assert params["$inlinecount"] == "allpages"
    assert params["$filter"] == "status eq 'Actual'"


def test_count_without_a_filter_sends_none():
    client = FakeClient([Resp({"metadata": {"count": 7}})])
    probe.count(client)
    assert "$filter" not in client.params[0]


def test_count_refuses_an_error_answer():
    client = FakeClient([Resp({}, status=400)])
    with pytest.raises(RuntimeError, match="HTTP 400"):
        probe.count(client, "bad")


def test_edge_sent_reads_the_first_record():
    client = FakeClient([Resp({probe.ENTITY: [{"sent": "2012-06-01T00:00:00.000Z"}]})])
    assert probe.edge_sent(client) == "2012-06-01T00:00:00.000Z"
    assert client.params[0]["$orderby"] == "sent asc"


def test_edge_sent_newest_orders_descending_and_refuses_errors():
    client = FakeClient([Resp({}, status=500)])
    with pytest.raises(RuntimeError, match="newest"):
        probe.edge_sent(client, newest=True)
    assert client.params[0]["$orderby"] == "sent desc"


def test_run_counts_and_save(tmp_path):
    client = FakeClient([Resp({"metadata": {"count": n}}) for n in (3, 4)])
    plan = probe.year_plan(2012, 2013, extra="status eq 'Actual'")
    assert plan[0][0] == "year:2012"
    assert "status eq 'Actual'" in plan[0][1]
    counts = probe.run_counts(client, plan)
    assert [c.count for c in counts] == [3, 4]
    out = tmp_path / "probe.json"
    probe.save(out, counts, total=7)
    saved = json.loads(out.read_text())
    assert saved["facts"] == {"total": 7}
    assert saved["counts"][1]["name"] == "year:2013"


class Raises:
    def __init__(self, exc):
        self.exc = exc

    def get(self, url, params):
        raise self.exc


def test_run_counts_records_a_timeout_and_goes_on(tmp_path):
    from warntext.client import SourceBlocked

    out = tmp_path / "p.json"
    counts = probe.run_counts(Raises(SourceBlocked(503, "slow")), [("status:Actual", "x")], out)
    assert counts[0].count is None
    assert counts[0].error == "HTTP 503"
    assert json.loads(out.read_text())["counts"][0]["error"] == "HTTP 503"


def test_run_counts_records_an_error_answer():
    client = FakeClient([Resp({}, status=400)])
    (c,) = probe.run_counts(client, [("bad", "x")])
    assert "HTTP 400" in c.error


def test_run_counts_stops_on_a_block_or_a_cap():
    from warntext.client import CapReached, SourceBlocked

    with pytest.raises(SourceBlocked):
        probe.run_counts(Raises(SourceBlocked(403, "blocked")), [("a", None)])
    with pytest.raises(CapReached):
        probe.run_counts(Raises(CapReached("cap")), [("a", None)])
