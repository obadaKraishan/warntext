"""The release pack and its own check, on invented messages."""

import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cap_samples import invented
from test_tables import BASE, COUNTY, record, run
from warntext import cli, release, tables


@pytest.fixture()
def pack(tmp_path):
    recs = [
        record(invented(identifier="EX-1", sender=COUNTY), "r01"),
        record(invented(identifier="EX-2", sender=COUNTY, code="CAE"), "r02"),
        record(
            invented(identifier="EX-3", sender=BASE, sender_name="Example Air Force Base"),
            "r03",
            cog=202,
        ),
        record(invented(identifier="EX-4", sender=COUNTY, code="RWT"), "r04"),
    ]
    b = run(recs)
    tables.write(b, tmp_path / "t", tmp_path / "p")
    out = tmp_path / "pack"
    m = release.build_pack(tmp_path / "t", out, "0.1.0", "2026-11-14T17:00:00.000Z", "2026-11-15")
    senders = [x["sender"] for x in b.raw_senders]
    return {
        "dir": out,
        "manifest": m,
        "senders": senders,
        "ids": b.raw_identifiers,
        "tmp": tmp_path,
    }


def test_the_pack_holds_the_record_layer_released_codes_and_federal_text_only(pack):
    paths = {f["path"] for f in pack["manifest"]["files"]}
    assert "alerts/text_federal.parquet" in paths and "tests/text_federal.parquet" in paths
    assert not any("text_other" in p for p in paths)
    assert "tests/codes.parquet" not in paths  # tests carry no codes
    names = pq.read_schema(pack["dir"] / "alerts" / "codes.parquet").names
    assert not set(names) & set(release.EXPERIMENTAL_CODES)
    assert "hazard" in names and "guidance" in names
    assert pack["manifest"]["facts"]["real_alerts"] == 3
    assert pack["manifest"]["facts"]["federal_text_alerts"] == 1


def test_the_card_is_filled_and_carries_the_license_fields(pack):
    text = (pack["dir"] / "README.md").read_text()
    assert release.card_metadata_problems(text) == []
    assert "{{" not in text and "2026-11-15" in text and "not an alerting service" in text
    assert "license_link: https://www.fema.gov/about/openfema/terms-conditions" in text
    assert release.card_metadata_problems("no header") == ["the card has no YAML header"]
    bad = text.replace("license: other", "license: cc-by-4.0").replace("config_name: codes", "x")
    problems = release.card_metadata_problems(bad)
    assert any("license must be 'other'" in p for p in problems)
    assert "no config for codes" in problems


def test_a_clean_pack_passes_and_each_wrong_file_fails(pack):
    d = pack["dir"]
    args = (pack["senders"], pack["ids"], {2024: 4})
    assert release.check_pack(d, *args) == []
    shutil.copy(pack["tmp"] / "t" / "alerts" / "text_other.parquet", d / "alerts")
    (d / "notes.txt").write_text("x")
    out = release.check_pack(d, *args)
    assert any("text_other.parquet: a text table other than text_federal" in f for f in out)
    assert any("notes.txt: not a file of the release" in f for f in out)


def test_an_experimental_code_or_a_changed_file_fails(pack):
    d = pack["dir"]
    args = (pack["senders"], pack["ids"], {2024: 4})
    codes = pq.read_table(pack["tmp"] / "t" / "alerts" / "codes.parquet")
    pq.write_table(codes, d / "alerts" / "codes.parquet")
    out = release.check_pack(d, *args)
    assert any("experimental codes are in it" in f for f in out)
    assert any("alerts/codes.parquet: does not match its SHA-256" in f for f in out)
    (d / "tests" / "threads.parquet").unlink()
    assert any("missing" in f for f in release.check_pack(d, *args))
    (d / "manifest.json").unlink()
    assert "missing" in release.check_pack(d, *args)[0]


def test_a_pack_is_built_once_into_a_new_folder(pack):
    with pytest.raises(SystemExit, match="not empty"):
        release.build_pack(pack["tmp"] / "t", pack["dir"], "0.1.0", "x", "y")
    with pytest.raises(SystemExit, match="is missing"):
        release.build_pack(pack["tmp"] / "none", pack["tmp"] / "new", "0.1.0", "x", "y")


def test_release_commands(pack, tmp_path, capsys):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"until": "2026-11-14T17:00:00.000Z", "year_counts": {"2024": 4}}))
    out = tmp_path / "pack2"
    build = ["release", "build", "--tables", str(pack["tmp"] / "t"), "--state", str(state)]
    assert (
        cli.main([*build, "--out", str(out), "--version", "0.1.0", "--retrieved", "2026-11-15"])
        == 0
    )
    check = ["release", "check", "--pack", str(out), "--private", str(pack["tmp"] / "p")]
    assert cli.main([*check, "--state", str(state)]) == 0
    assert "Release pack check passed" in capsys.readouterr().out
    pq.write_table(pa.table({"x": [1]}), out / "alerts" / "text_other.parquet")
    assert cli.main([*check, "--state", str(state)]) == 1
