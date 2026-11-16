"""The release pack and its own check, on invented messages."""

import json
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cap_samples import invented
from test_tables import BASE, COUNTY, record, run
from warntext import cli, release, tables
from warntext import codes as cd


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
    from warntext import codes as cd

    m = release.build_pack(
        tmp_path / "t", out, "0.1.0", "2026-11-14T17:00:00.000Z", "2026-11-15", cd.CODEBOOK_VERSION
    )
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
    assert "hazard" in names and "link" in names and "guidance" not in names
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
        cli.main(
            [
                *build,
                *("--out", str(out), "--version", "0.1.0", "--retrieved", "2026-11-15"),
                *("--codebook-version", cd.CODEBOOK_VERSION),
            ]
        )
        == 0
    )
    check = ["release", "check", "--pack", str(out), "--private", str(pack["tmp"] / "p")]
    assert cli.main([*check, "--state", str(state)]) == 0
    assert "Release pack check passed" in capsys.readouterr().out
    pq.write_table(pa.table({"x": [1]}), out / "alerts" / "text_other.parquet")
    assert cli.main([*check, "--state", str(state)]) == 1


def test_the_kaggle_mirror_holds_the_record_layer_and_codes_only(pack, tmp_path):
    out = tmp_path / "kaggle"
    meta = release.build_kaggle(pack["dir"], out)
    files = sorted(p.name for p in out.iterdir())
    assert "alerts-codes.parquet" in files and "alerts-messages.parquet" in files
    assert not any("text" in f for f in files)
    assert meta["licenses"] == [{"name": "other"}] and meta["isPrivate"] is True
    assert release.TERMS_URL in meta["description"]
    assert release.check_kaggle(out) == []
    shutil.copy(
        pack["dir"] / "alerts" / "text_federal.parquet", out / "alerts-text_federal.parquet"
    )
    assert any("holds no text" in f for f in release.check_kaggle(out))
    with pytest.raises(SystemExit, match="not empty"):
        release.build_kaggle(pack["dir"], out)


def test_code_status_covers_every_code_and_fills_the_card():
    status = release.code_status()
    from warntext.codes import CODE_FIELDS

    assert set(status) == set(CODE_FIELDS)
    assert status["hazard"]["status"] == "released"
    assert status["complete"]["status"] == "experimental"
    tables = release.code_tables()
    assert "| `hazard` | 0.86 |" in tables["code_alpha_table"]
    assert "`complete`" in tables["codes_left_out"] and "`hazard`" in tables["codes_released"]


def test_a_pack_is_refused_from_codes_of_another_version(pack, tmp_path):
    with pytest.raises(SystemExit, match="measured on version 0"):
        release.build_pack(pack["tmp"] / "t", tmp_path / "other", "0.1.0", "x", "y", "0")


def test_a_raw_tag_in_the_card_fails_the_check(pack):
    d = pack["dir"]
    args = (pack["senders"], pack["ids"], {2024: 4})
    readme = d / "README.md"
    text = readme.read_text()
    readme.write_text(text.replace("## How to cite", "## How to cite\n\nCite <title> here."))
    out = release.check_pack(d, *args)
    assert any("'<title>' is read as an HTML tag" in f for f in out)
    readme.write_text(text.replace("## How to cite", "## How to cite\n\nCite `<title>` here."))
    assert release.check_pack(d, *args) == []


def test_the_card_alone_is_written_again_and_the_data_files_stay(pack, capsys):
    d = pack["dir"]
    before = {f["path"]: (d / f["path"]).read_bytes() for f in pack["manifest"]["files"]}
    manifest = (d / "manifest.json").read_bytes()
    readme = d / "README.md"
    good = readme.read_text()
    readme.write_text("an older card")
    assert release.rewrite_card(d) is True
    assert readme.read_text() == good
    assert release.rewrite_card(d) is False
    assert {p: (d / p).read_bytes() for p in before} == before
    assert (d / "manifest.json").read_bytes() == manifest
    assert cli.main(["release", "card", "--pack", str(d)]) == 0
    assert "unchanged" in capsys.readouterr().out


def test_kaggle_title_and_subtitle_lengths_and_id_are_checked(pack, tmp_path):
    out = tmp_path / "kaggle"
    meta = release.build_kaggle(pack["dir"], out)
    assert len(meta["title"]) <= 50 and release.kaggle_metadata_problems(meta) == []
    long = dict(meta, title="WarnText: the public alert messages of the United States, as records")
    assert "the title has 68 characters; Kaggle takes 6 to 50." in " ".join(
        release.kaggle_metadata_problems(long)
    )
    short = dict(meta, subtitle="too short", id="someone/else")
    problems = release.kaggle_metadata_problems(short)
    assert any("subtitle has 9 characters" in p for p in problems)
    assert any("not obadakraishan/warntext" in p for p in problems)
    tagged = dict(meta, description=meta["description"] + " <b>bold</b>")
    assert any("'<b>'" in p for p in release.kaggle_metadata_problems(tagged))
    (out / "dataset-metadata.json").write_text(json.dumps(long))
    assert any("title has 68" in f for f in release.check_kaggle(out))
