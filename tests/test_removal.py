"""A removal applied to a built version, and its proof, on invented versions only."""

import json

import pyarrow.parquet as pq
import pytest

from cap_samples import invented
from test_release import as_version
from test_tables import BASE, COUNTY, Line, record
from warntext import access, cli, durable, release, removal, tables

#: Invented FEMA record ids (the removal list takes record ids of this shape only).
A, B, C, D = (f"00000000-0000-4000-8000-00000000000{n}" for n in range(1, 5))
POLYGON = "38.0,-90.0 38.1,-90.0 38.1,-90.1 38.0,-90.0"


def _records():
    return [
        record(invented(identifier="EX-1", sender=COUNTY, polygon=POLYGON), A),
        record(invented(identifier="EX-2", sender=COUNTY, code="CAE"), B),
        record(
            invented(identifier="EX-3", sender=BASE, sender_name="Example Air Force Base"),
            C,
            cog=202,
        ),
        record(invented(identifier="EX-4", sender=COUNTY, code="RWT"), D),
    ]


def _version(tmp_path, name, removals=(), version="0.2.0"):
    b = tables.build(
        tables.parse_records((Line(), r) for r in _records()), removals=frozenset(removals)
    )
    tables.write(b, tmp_path / f"t-{name}", tmp_path / f"p-{name}")
    as_version(tmp_path / f"t-{name}", "3")
    out = tmp_path / name
    release.build_pack(
        tmp_path / f"t-{name}", out, version, "2026-11-25T12:00:00.000Z", "2026-11-26", "3"
    )
    return out, b


def _check(pack, b, removals):
    senders = [x["sender"] for x in b.raw_senders]
    return release.check_pack(pack, senders, b.raw_identifiers, {2024: 4}, removals)


def _rows(pack):
    m = json.loads((pack / "manifest.json").read_text())
    return {f["path"]: pq.read_table(pack / f["path"]).to_pylist() for f in m["files"]}


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0"])
def test_a_version_rebuilt_with_the_list_equals_a_fresh_build_with_it(tmp_path, version):
    built, b = _version(tmp_path, "old", version=version)
    fresh, _ = _version(tmp_path, "fresh", removals={A, C}, version=version)
    m = removal.apply(built, tmp_path / "new", {A, C})
    assert _rows(tmp_path / "new") == _rows(fresh)  # every row of every table
    assert m["facts"] == json.loads((fresh / "manifest.json").read_text())["facts"]
    assert m["removal_list_applied"] == {"entries": 2, "messages_listed": 2, "newly_withheld": 2}
    assert _check(tmp_path / "new", b, {A, C}) == []
    assert _check(built, b, {A, C})  # the old version fails once the list names them
    fresh_m = json.loads((fresh / "manifest.json").read_text())
    if version == "0.2.0":
        assert [f["sha256"] for f in m["access_files"]] == [
            f["sha256"] for f in fresh_m["access_files"]
        ]
    else:
        assert "access_files" not in m


def test_the_proof_finds_only_the_removed_text_changed(tmp_path):
    built, _ = _version(tmp_path, "old")
    removal.apply(built, tmp_path / "new", {A})
    p = removal.proof(built, tmp_path / "new", {A})
    assert p["proved"] and p["messages_listed"] == 1 and p["problems"] == []
    changed = {f["path"]: f for f in p["files"] if not f["same_hash"]}
    assert set(changed) == {
        "alerts/messages.parquet",
        "alerts/areas.parquet",
        "alerts/text_other.parquet",
    }
    assert changed["alerts/messages.parquet"]["fields_changed"] == [
        "shapes_withheld",
        "text_withheld",
    ]
    assert set(changed["alerts/areas.parquet"]["fields_changed"]) == {
        "circles",
        "polygons",
        "shapes_withheld",
    }
    assert p["text_rows_left_out"] == 1
    layer = {f["path"]: f for f in p["access_files"]}
    assert layer["fields.csv"]["same_hash"] and layer["codebook.csv"]["same_hash"]
    assert layer[access.START_HERE]["rows_differ"] == 1
    assert layer["tests/messages.csv.gz"]["same_hash"]
    assert p["card_lines_changed"] > 0


def test_the_proof_fails_on_any_other_change(tmp_path):
    built, _ = _version(tmp_path, "old")
    new = tmp_path / "new"
    removal.apply(built, new, {A})
    # Another message's row changed as well: the proof must say so.
    path = new / "alerts" / "messages.parquet"
    t = pq.read_table(path).to_pylist()
    for r in t:
        if r["message_id"] == C:
            r["year"] = 1999
    pq.write_table(pq.read_table(path).from_pylist(t, schema=pq.read_schema(path)), path)
    p = removal.proof(built, new, {A})
    assert not p["proved"]
    assert any("a row of a message not on the list differs" in x for x in p["problems"])


def test_the_proof_fails_when_a_listed_text_row_stays_or_a_code_moves(tmp_path):
    built, _ = _version(tmp_path, "old")
    new = tmp_path / "new"
    removal.apply(built, new, {A})
    (new / "alerts" / "text_other.parquet").write_bytes(
        (built / "alerts" / "text_other.parquet").read_bytes()
    )
    codes = new / "alerts" / "codes.parquet"
    rows = pq.read_table(codes).to_pylist()
    rows[0]["link"] = not rows[0]["link"]
    pq.write_table(pq.read_table(codes).from_pylist(rows, schema=pq.read_schema(codes)), codes)
    m = json.loads((new / "manifest.json").read_text())
    for f in m["files"]:
        f["sha256"] = durable.sha256_file(new / f["path"])
    (new / "manifest.json").write_text(json.dumps(m))
    p = removal.proof(built, new, {A})
    assert not p["proved"]
    assert any("changed, but a removal never changes this table" in x for x in p["problems"])


def test_a_message_already_withheld_keeps_its_reason(tmp_path):
    built, _ = _version(tmp_path, "old")
    m = removal.apply(built, tmp_path / "new", {B})  # B has a people code
    assert m["removal_list_applied"]["newly_withheld"] == 0
    rows = pq.read_table(tmp_path / "new" / "alerts" / "messages.parquet").to_pylist()
    assert {r["message_id"]: r["text_withheld"] for r in rows}[B] == "people_code"
    assert removal.proof(built, tmp_path / "new", {B})["parquet_changed"] == 0


def test_a_recreation_is_recorded_and_the_card_dates_it(tmp_path):
    built, _ = _version(tmp_path, "old")
    m = removal.apply(
        built,
        tmp_path / "new",
        {A},
        {"date": "2027-01-05", "versions": ["0.1.0", "0.2.0", "0.2.9"]},
    )
    assert m["recreated"] == [{"date": "2027-01-05", "versions": ["0.1.0", "0.2.0", "0.2.9"]}]
    card = " ".join((tmp_path / "new" / "README.md").read_text().split())
    assert "On 5 January 2027 the dataset was deleted and created again" in card
    with pytest.raises(SystemExit, match="not empty"):
        removal.apply(built, tmp_path / "new", {A})


def test_the_commands_rebuild_and_prove(tmp_path, capsys):
    built, _ = _version(tmp_path, "old")
    listing = tmp_path / "removals.csv"
    listing.write_text(f"record_id,added,request\n{A},2026-11-26,issue 1\n")
    new, proof = tmp_path / "new", tmp_path / "proof.json"
    assert (
        cli.main(
            [
                *("release", "remove", "--pack", str(built)),
                *("--out", str(new), "--removals", str(listing)),
            ]
        )
        == 0
    )
    assert "1 newly withheld" in capsys.readouterr().out
    args = ["release", "removal-proof", "--old", str(built), "--new", str(new)]
    assert cli.main([*args, "--removals", str(listing), "--out", str(proof)]) == 0
    assert "Proved: only the removed text changed." in capsys.readouterr().out
    assert json.loads(proof.read_text())["proved"]
    bad = ["release", "remove", "--pack", str(built), "--out", str(tmp_path / "x")]
    assert cli.main([*bad, "--recreated-on", "2027-01-05"]) == 2


def test_the_shrink_limit(tmp_path, capsys):
    old = {
        "version": "0.2.0",
        "rows": 1100,
        "files": [
            {"path": "alerts/messages.parquet", "rows": 100},
            {"path": "alerts/text_other.parquet", "rows": 1000},
        ],
    }
    same = {**old, "version": "0.2.1"}
    assert release.shrink_problems(same, old) == []
    fewer_text = {**same, "files": [old["files"][0], {**old["files"][1], "rows": 990}]}
    assert release.shrink_problems(fewer_text, old) == []  # 10 rows: within the floor
    much_fewer = {**same, "files": [old["files"][0], {**old["files"][1], "rows": 900}]}
    assert "a text table may lose at most" in release.shrink_problems(much_fewer, old)[0]
    one_less = {**same, "files": [{**old["files"][0], "rows": 99}, old["files"][1]]}
    assert "never loses rows" in release.shrink_problems(one_less, old)[0]
    gone = {**same, "files": [old["files"][0]]}
    assert "but not in 0.2.1" in release.shrink_problems(gone, old)[0]
    for name, m in (("old", old), ("new", much_fewer)):
        (tmp_path / name).mkdir()
        (tmp_path / name / "manifest.json").write_text(json.dumps({**m, "rows": 1000}))
    args = ["release", "shrink", "--pack", str(tmp_path / "new"), "--previous"]
    assert cli.main([*args, str(tmp_path / "old")]) == 1
    assert "past the shrink limit" in capsys.readouterr().out
