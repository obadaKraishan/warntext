import json

import pytest

from warntext import durable, probe, sample


def test_stratum_filter_splits_by_sender():
    nws = sample.stratum_filter(2015, "nws")
    other = sample.stratum_filter(2015, "other")
    assert "sender eq 'w-nws.webmaster@noaa.gov'" in nws
    assert "sender ne 'w-nws.webmaster@noaa.gov'" in other
    assert probe.year_filter(2015) in nws
    with pytest.raises(ValueError, match="Unknown sender kind"):
        sample.stratum_filter(2015, "weather")


def test_plan_is_seeded_repeatable_and_inside_each_stratum():
    strata = [sample.Stratum(2015, "nws", 1000), sample.Stratum(2015, "other", 95)]
    a = sample.plan_pages(strata, pages=3, page_size=10, seed=7)
    b = sample.plan_pages(strata, pages=3, page_size=10, seed=7)
    c = sample.plan_pages(strata, pages=3, page_size=10, seed=8)
    assert a == b
    assert a != c
    assert len(a) == 6
    for p in a:
        assert p.skip % 10 == 0
        assert p.skip + p.top <= (1000 if p.kind == "nws" else 95)
    assert len({p.skip for p in a if p.kind == "nws"}) == 3


def test_plan_reads_a_small_stratum_whole_and_skips_an_empty_one():
    strata = [sample.Stratum(2012, "other", 6), sample.Stratum(2024, "nws", 0)]
    assert sample.plan_pages(strata, pages=5, page_size=10, seed=1) == [
        sample.Page(2012, "other", 0, 6)
    ]


def test_plan_takes_every_block_when_there_are_few():
    pages = sample.plan_pages([sample.Stratum(2013, "other", 25)], pages=5, page_size=10, seed=1)
    assert [p.skip for p in pages] == [0, 10]


def test_changing_one_stratum_does_not_move_the_others():
    a = sample.plan_pages([sample.Stratum(2015, "nws", 1000)], 3, 10, 7)
    b = sample.plan_pages(
        [sample.Stratum(2014, "nws", 5000), sample.Stratum(2015, "nws", 1000)], 3, 10, 7
    )
    assert a == [p for p in b if p.year == 2015]


def test_weights_are_stratum_size_over_drawn():
    strata = [sample.Stratum(2015, "nws", 1000), sample.Stratum(2015, "other", 50)]
    w = sample.weights(strata, {(2015, "nws"): 20, (2015, "other"): 0})
    assert w == {(2015, "nws"): 50.0}


class Resp:
    def __init__(self, body, status=200):
        self.content = body
        self.status = status
        self.seconds = 0.4


class FakeClient:
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.params = []

    def get(self, url, params):
        self.params.append(params)
        return self.bodies.pop(0)

    def clock(self):
        return "2026-11-15T00:00:00.000Z"


def body(n):
    return json.dumps({"metadata": {}, probe.ENTITY: [{"id": str(i)} for i in range(n)]}).encode()


def test_run_writes_raw_pages_once_and_resumes(tmp_path):
    raw, manifest = tmp_path / "raw", tmp_path / "manifest.csv"
    pages = [sample.Page(2015, "nws", 0, 2), sample.Page(2015, "other", 10, 2)]
    client = FakeClient([Resp(body(2)), Resp(body(1))])
    new = sample.run(client, pages, raw, manifest)
    assert [r.records for r in new] == [2, 1]
    assert client.params[0]["$orderby"] == sample.ORDERBY
    assert client.params[1]["$skip"] == 10
    assert (raw / pages[0].name).read_bytes() == body(2)
    assert sample.run(FakeClient([]), pages, raw, manifest) == []
    lines = sample.read_manifest(manifest)
    assert lines[1].sha256 == durable.sha256_bytes(body(1))
    assert isinstance(lines[0].seconds, float)
    records = list(sample.iter_records(raw, manifest))
    assert len(records) == 3
    assert records[2][0].kind == "other"


def test_a_failed_page_saves_nothing(tmp_path):
    client = FakeClient([Resp(b"", status=500)])
    with pytest.raises(RuntimeError, match="Nothing was saved"):
        sample.run(client, [sample.Page(2015, "nws", 0, 2)], tmp_path / "raw", tmp_path / "m.csv")
    assert not (tmp_path / "m.csv").exists()


def test_iter_records_catches_a_changed_file(tmp_path):
    raw, manifest = tmp_path / "raw", tmp_path / "manifest.csv"
    page = sample.Page(2015, "nws", 0, 2)
    sample.run(FakeClient([Resp(body(2))]), [page], raw, manifest)
    path = raw / page.name
    path.chmod(0o644)
    path.write_bytes(body(3))
    with pytest.raises(durable.WriteCheckFailed, match="Fetch it again"):
        list(sample.iter_records(raw, manifest))


def test_read_manifest_of_a_missing_file_is_empty(tmp_path):
    assert sample.read_manifest(tmp_path / "none.csv") == []
