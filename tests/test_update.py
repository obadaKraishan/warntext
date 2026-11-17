"""The weekly update against a small simulated archive. Every record is invented."""

import json
import re
from datetime import datetime, timezone

import pytest

from cap_samples import invented
from test_authorities import PAGE
from test_tables import COUNTY, record
from warntext import authorities as au
from warntext import backfill, probe, update

NWS = "w-nws.webmaster@noaa.gov"


class Resp:
    def __init__(self, content, status=200):
        self.content = content
        self.status = status
        self.seconds = 0.1

    def json(self):
        return json.loads(self.content)


class Budget:
    calls = 0
    nbytes = 0


class Server:
    """Answers OpenFEMA-style counts and pages from a list of records, and FEMA's list page."""

    def __init__(self, recs, fail_ne=False):
        self.recs = sorted(recs, key=lambda r: (r["sent"], r["id"]))
        self.budget = Budget()
        self.fail_ne = fail_ne
        self.urls = []

    def clock(self):
        return "2026-11-20T12:00:00.000Z"

    def _match(self, flt):
        ge = re.search(r"sent ge '([^']+)'", flt).group(1)
        lt = re.search(r"sent lt '([^']+)'", flt).group(1)
        out = [r for r in self.recs if ge <= r["sent"] < lt]
        if f"sender ne '{NWS}'" in flt:
            out = [r for r in out if r["sender"] != NWS]
        if f"sender eq '{NWS}'" in flt:
            out = [r for r in out if r["sender"] == NWS]
        return out

    def get(self, url, params=None):
        self.budget.calls += 1
        self.urls.append(url)
        if url == au.PAGE_URL:
            return Resp(PAGE.encode())
        assert url == probe.ENDPOINT
        flt = params["$filter"]
        if "$inlinecount" in params:
            if self.fail_ne and "sender ne" in flt:
                return Resp(b"timeout", status=503)
            n = len(self._match(flt))
            return Resp(json.dumps({"metadata": {"count": n}, probe.ENTITY: []}).encode())
        rows = self._match(flt)[params["$skip"] : params["$skip"] + params["$top"]]
        return Resp(json.dumps({"metadata": {}, probe.ENTITY: rows}).encode())


def rec(k, sent, code="CEM", sender=COUNTY, cog=101, **kw):
    xml = invented(identifier=f"EX-U{k}", sender=sender, sent=sent, code=code, **kw)
    return record(xml, f"u{k:02d}", cog=cog)


@pytest.fixture()
def world(tmp_path):
    old = [
        rec(1, "2026-11-10T10:00:00-05:00"),
        rec(2, "2026-11-12T10:00:00-05:00", code="RWT"),
        rec(3, "2026-11-12T11:00:00-05:00", sender=NWS, code="TOR"),
    ]
    new = [
        rec(4, "2026-11-15T10:00:00-05:00"),
        rec(
            5,
            "2026-11-16T10:47:12-05:00",
            code="CAE",
            description="Invented child alert, no details.",
        ),
        rec(
            6,
            "2026-11-17T09:00:00-05:00",
            msg_type="Cancel",
            references=f"{COUNTY},EX-U4,2026-11-15T10:00:00-05:00",
        ),
    ]
    raw = tmp_path / "raw"
    # The backfill, as S2 read it: the old records up to 2026-11-14.
    until0 = "2026-11-14T00:00:00.000Z"
    backfill.run(Server(old), {2026: 2}, until0, raw / "backfill")
    state = tmp_path / "raw" / "update-state.json"
    update.init_state(state, ["backfill"], {2026: 2}, until0)
    return {"old": old, "new": new, "raw": raw, "state": state, "tmp": tmp_path}


def test_default_until_waits_for_the_archive_s_day_of_delay():
    now = datetime(2026, 11, 20, 12, 34, tzinfo=timezone.utc)
    assert update.default_until(now) == "2026-11-19T11:00:00.000Z"


def test_year_pieces_cut_a_window_at_new_year():
    pieces = update.year_pieces("2026-12-30T00:00:00.000Z", "2027-01-02T00:00:00.000Z")
    assert [p[0] for p in pieces] == [2026, 2027]
    assert pieces[0][2] == "2027-01-01T00:00:00.000Z"


def test_a_state_is_started_once_and_must_exist(world, tmp_path):
    with pytest.raises(SystemExit, match="started once"):
        update.init_state(world["state"], ["backfill"], {2026: 2}, "x")
    with pytest.raises(SystemExit, match="does not exist"):
        update.read_state(tmp_path / "none.json")


def test_one_run_reads_the_window_rebuilds_checks_and_moves_the_state(world):
    server = Server(world["old"] + world["new"])
    until = "2026-11-18T00:00:00.000Z"
    s = update.run_update(
        server, world["state"], world["raw"], world["tmp"] / "t", world["tmp"] / "p", until=until
    )
    assert s["check"] == "passed", s["failures"]
    assert s["new_window"]["server_count"] == 3
    assert s["new_records"] == 3 and s["new_real_alerts"] == 3
    assert s["new_real_alerts_withheld"] == {"people_code": 1}
    assert s["look_back"]["server_count"] == s["look_back"]["local_count"] == 2
    assert s["look_back"]["pages_read_again"] == 0
    assert s["fema_list"]["authorities"] == 3
    state = update.read_state(world["state"])
    assert state["until"] == until
    assert state["raw_folders"] == ["backfill", "update-2026-11-18T00"]
    assert state["year_counts"] == {"2026": 5}
    assert state["fema_list"]["file"] == "alerting_authorities-2026-11-18.csv"
    # the cancel's reference to last week's alert is resolved: threads stay exact
    msgs = {
        r["message_id"]: r
        for c in ("alerts", "tests")
        for r in json_rows(world["tmp"] / "t" / c / "messages.parquet")
    }
    assert msgs["u06"]["thread_id"] == "u04"
    assert msgs["u05"]["times_rounded"] is True
    text = json.dumps(s)
    assert "Invented" not in text and COUNTY not in text


def json_rows(path):
    import pyarrow.parquet as pq

    return pq.read_table(path).to_pylist()


def test_late_records_are_read_again_and_counted_once(world):
    late = rec(7, "2026-11-13T08:00:00-05:00")
    server = Server(world["old"] + world["new"] + [late], fail_ne=True)
    s = update.run_update(
        server,
        world["state"],
        world["raw"],
        world["tmp"] / "t",
        world["tmp"] / "p",
        until="2026-11-18T00:00:00.000Z",
        fetch_list=False,
    )
    assert s["check"] == "passed", s["failures"]
    assert s["look_back"]["server_count"] == 3 and s["look_back"]["local_count"] == 2
    assert s["look_back"]["pages_read_again"] >= 1
    assert s["new_records"] == 4  # three in the window and one late; the two held once
    assert s["new_window"]["counts_taken"] == {"difference": 1}
    assert "fema_list" not in s


def test_a_window_that_ends_before_it_starts_is_refused(world):
    with pytest.raises(SystemExit, match="Nothing to read"):
        update.run_update(
            Server([]),
            world["state"],
            world["raw"],
            world["tmp"] / "t",
            world["tmp"] / "p",
            until="2026-11-13T00:00:00.000Z",
        )


def test_a_failing_check_leaves_the_state_where_it_was(world, monkeypatch):
    from warntext import check

    monkeypatch.setattr(check, "check", lambda *a, **k: ["invented failure"])
    s = update.run_update(
        Server(world["old"] + world["new"]),
        world["state"],
        world["raw"],
        world["tmp"] / "t",
        world["tmp"] / "p",
        until="2026-11-18T00:00:00.000Z",
        fetch_list=False,
    )
    assert s["check"] == "failed"
    assert update.read_state(world["state"])["until"] == "2026-11-14T00:00:00.000Z"


def test_rebuild_from_state_needs_no_request_and_keeps_the_state(world):
    server = Server(world["old"] + world["new"])
    update.run_update(
        server,
        world["state"],
        world["raw"],
        world["tmp"] / "t",
        world["tmp"] / "p",
        until="2026-11-18T00:00:00.000Z",
    )
    before = update.read_state(world["state"])
    r = update.rebuild_from_state(
        world["state"], world["raw"], world["tmp"] / "t2", world["tmp"] / "p2"
    )
    assert r["check"] == "passed" and r["records"] == 5
    assert r["fema_list"] == "alerting_authorities-2026-11-18.csv"
    assert update.read_state(world["state"]) == before
    import pyarrow.parquet as pq

    r3 = update.rebuild_from_state(
        world["state"], world["raw"], world["tmp"] / "t3", world["tmp"] / "p3", "3"
    )
    assert r3["check"] == "passed"
    versions = pq.read_table(world["tmp"] / "t3" / "alerts" / "codes.parquet").column(
        "codebook_version"
    )
    assert set(versions.to_pylist()) <= {"3"}
