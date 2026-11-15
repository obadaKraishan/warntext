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


def body(n, start=0, year=2015, same_second=False):
    """``n`` invented records, one a second from ``start`` (or all in the same second)."""
    records = [
        {
            "id": f"id-{year}-{start + i:05d}",
            "sent": f"{year}-03-01T00:{(0 if same_second else start + i) // 60:02d}:"
            f"{(0 if same_second else start + i) % 60:02d}.000Z",
        }
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


def test_run_reads_each_year_by_cursor_and_writes_pages_once(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient([Resp(body(3)), Resp(body(2, 3)), Resp(body(1, year=2016))])
    seen = []
    new = backfill.run(client, {2015: 5, 2016: 1}, UNTIL, raw, top=3, on_page=seen.append)
    assert [(x.year, x.page, x.records) for x in new] == [(2015, 0, 3), (2015, 1, 2), (2016, 0, 1)]
    assert seen == new
    first, second, third = client.params
    assert "sent ge '2015-01-01T00:00:00.000Z'" in first["$filter"]
    assert first["$skip"] == 0
    # the second page starts at the last time read and skips the one record read at that time
    assert "sent ge '2015-03-01T00:00:02.000Z'" in second["$filter"]
    assert second["$skip"] == 1
    assert "sent ge '2016-01-01T00:00:00.000Z'" in third["$filter"]
    assert all(p["$orderby"] == "sent asc, id asc" for p in client.params)
    lines = backfill.read_manifest(raw / "manifest.csv")
    assert lines[0].sha256 == durable.sha256_bytes(body(3))
    assert lines[0].first_sent <= lines[0].last_sent
    assert (raw / lines[0].file).read_bytes() == body(3)
    assert len(list(backfill.iter_records(raw))) == 6


def test_records_in_the_same_second_are_skipped_across_pages(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient(
        [Resp(body(3, same_second=True)), Resp(body(3, 3, same_second=True)), Resp(body(1, 9))]
    )
    backfill.run(client, {2015: 7}, UNTIL, raw, top=3)
    assert [p["$skip"] for p in client.params] == [0, 3, 6]
    assert backfill.read_manifest(raw / "manifest.csv")[1].last_seen == 6


def test_a_stopped_run_resumes_after_the_last_page(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient([Resp(body(3)), RuntimeError("the drive went away")])
    with pytest.raises(RuntimeError, match="drive"):
        backfill.run(client, {2015: 7}, UNTIL, raw, top=3)
    again = FakeClient([Resp(body(3, 3)), Resp(body(1, 6))])
    new = backfill.run(again, {2015: 7}, UNTIL, raw, top=3)
    assert [p["$skip"] for p in again.params] == [1, 1]
    assert [x.page for x in new] == [1, 2]
    assert backfill.run(FakeClient([]), {2015: 7}, UNTIL, raw, top=3) == []


def test_a_year_that_ends_short_is_not_read_again(tmp_path):
    raw = tmp_path / "raw"
    backfill.run(FakeClient([Resp(body(2))]), {2015: 4}, UNTIL, raw, top=3)
    assert backfill.run(FakeClient([]), {2015: 4}, UNTIL, raw, top=3) == []
    at = backfill.cursor(backfill.read_manifest(raw / "manifest.csv"), 2015, UNTIL)
    assert at.finished
    assert at.read == 2


def test_an_empty_year_makes_no_call(tmp_path):
    assert backfill.run(FakeClient([]), {2011: 0}, UNTIL, tmp_path / "raw") == []


def test_a_page_too_large_is_read_again_as_a_small_page(tmp_path):
    raw = tmp_path / "raw"
    client = FakeClient([ResponseTooLarge("big"), Resp(body(2)), Resp(body(2, 2))])
    new = backfill.run(client, {2015: 4}, UNTIL, raw, top=4, small=2)
    assert [(p["$skip"], p["$top"]) for p in client.params] == [(0, 4), (0, 2), (1, 4)]
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


def test_count_plan_direct_and_difference():
    direct = backfill.count_plan([2015], UNTIL, "direct")
    assert direct == [("other:2015", backfill.window_filter(2015, UNTIL))]
    diff = dict(backfill.count_plan([2026], UNTIL, "difference"))
    assert "sender" not in diff["all:2026"]
    assert "sent lt '2026-11-14T00:00:00.000Z'" in diff["all:2026"]
    assert "sender eq 'w-nws.webmaster@noaa.gov'" in diff["nws:2026"]
    with pytest.raises(ValueError, match="Unknown count method"):
        backfill.count_plan([2015], UNTIL, "guess")


def test_year_counts_prefers_direct_and_falls_back_to_the_difference():
    entries = [
        {"name": "other:2014", "count": None},
        {"name": "other:2015", "count": 7},
        {"name": "all:2014", "count": 100},
        {"name": "nws:2014", "count": 90},
        {"name": "all:2015", "count": 50},
        {"name": "nws:2015", "count": 40},
        {"name": "all:2016", "count": 5},
    ]
    assert backfill.year_counts(entries) == {2014: (10, "difference"), 2015: (7, "direct")}
