import json

import pytest

from warntext import backfill, durable, probe
from warntext.client import ResponseTooLarge

UNTIL = "2026-11-14T00:00:00.000Z"


class Resp:
    def __init__(self, body, status=200):
        self.content = body
        self.status = status
        self.seconds = 0.5


class FakeClient:
    """Answers pages from a list; an exception in the list is raised instead."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.params = []

    def get(self, url, params):
        assert url == probe.ENDPOINT
        self.params.append(params)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def clock(self):
        return "2026-11-15T15:00:00.000Z"


def body(n, start=0, year=2015):
    records = [
        {"id": f"id-{year}-{start + i:05d}", "sent": f"{year}-03-01T00:00:{i % 60:02d}Z"}
        for i in range(n)
    ]
    return json.dumps({"metadata": {}, probe.ENTITY: records}).encode()


def test_window_filter_leaves_out_the_weather_service_and_stops_at_until():
    f = backfill.window_filter(2026, UNTIL)
    assert "sender ne 'w-nws.webmaster@noaa.gov'" in f
    assert "sent lt '2026-11-14T00:00:00.000Z'" in f
    assert "sent lt '2016-01-01T00:00:00.000Z'" in backfill.window_filter(2015, UNTIL)


def test_years_until_ends_at_the_year_that_holds_the_bound():
    assert backfill.years_until(2011, UNTIL) == list(range(2011, 2027))
    assert backfill.years_until(2024, "2026-01-01T00:00:00.000Z") == [2024, 2025]


def test_run_reads_each_year_in_pages_and_writes_them_once(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient([Resp(body(3)), Resp(body(2, 3)), Resp(body(1, year=2016))])
    seen = []
    new = backfill.run(client, {2015: 5, 2016: 1}, UNTIL, raw, top=3, on_page=seen.append)
    assert [(x.year, x.skip, x.records) for x in new] == [(2015, 0, 3), (2015, 3, 2), (2016, 0, 1)]
    assert seen == new
    assert [p["$skip"] for p in client.params] == [0, 3, 0]
    assert all(p["$orderby"] == "sent asc, id asc" for p in client.params)
    lines = backfill.read_manifest(raw / "manifest.csv")
    assert lines[0].sha256 == durable.sha256_bytes(body(3))
    assert lines[0].first_sent <= lines[0].last_sent
    assert (raw / lines[0].file).read_bytes() == body(3)
    assert len(list(backfill.iter_records(raw))) == 6


def test_a_stopped_run_resumes_from_the_last_complete_page(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient([Resp(body(3)), RuntimeError("the drive went away")])
    with pytest.raises(RuntimeError, match="drive"):
        backfill.run(client, {2015: 7}, UNTIL, raw, top=3)
    again = FakeClient([Resp(body(3, 3)), Resp(body(1, 6))])
    new = backfill.run(again, {2015: 7}, UNTIL, raw, top=3)
    assert [p["$skip"] for p in again.params] == [3, 6]
    assert [x.skip for x in new] == [3, 6]
    assert backfill.run(FakeClient([]), {2015: 7}, UNTIL, raw, top=3) == []


def test_a_year_that_ends_short_is_not_read_again(tmp_path):
    raw = tmp_path / "raw"
    backfill.run(FakeClient([Resp(body(2))]), {2015: 4}, UNTIL, raw, top=3)
    assert backfill.run(FakeClient([]), {2015: 4}, UNTIL, raw, top=3) == []
    assert backfill.next_skip(backfill.read_manifest(raw / "manifest.csv"), 2015) == 2


def test_an_empty_year_makes_no_call(tmp_path):
    assert backfill.run(FakeClient([]), {2011: 0}, UNTIL, tmp_path / "raw") == []


def test_a_page_too_large_is_read_again_in_small_pages(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient([ResponseTooLarge("big"), Resp(body(2)), Resp(body(2, 2))])
    new = backfill.run(client, {2015: 4}, UNTIL, raw, top=4, small=2)
    assert [(p["$skip"], p["$top"]) for p in client.params] == [(0, 4), (0, 2), (2, 4)]
    assert [x.records for x in new] == [2, 2]


def test_a_failed_page_saves_nothing(tmp_path):
    with pytest.raises(RuntimeError, match="Nothing was saved"):
        backfill.run(FakeClient([Resp(b"", 500)]), {2015: 3}, UNTIL, tmp_path / "raw")
    assert not (tmp_path / "raw" / "manifest.csv").exists()


def test_iter_records_catches_a_changed_page(tmp_path):
    raw = tmp_path / "raw"
    backfill.run(FakeClient([Resp(body(2))]), {2015: 2}, UNTIL, raw, top=3)
    path = raw / backfill.read_manifest(raw / "manifest.csv")[0].file
    path.chmod(0o644)
    path.write_bytes(body(1))
    with pytest.raises(durable.WriteCheckFailed, match="SHA-256"):
        list(backfill.iter_records(raw))


def test_planned_calls_is_one_per_page():
    assert backfill.planned_calls({2011: 0, 2012: 1, 2013: 1000, 2014: 1001}) == 1 + 2 + 3
