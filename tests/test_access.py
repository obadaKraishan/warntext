"""The easy-access layer (0.2.0 on), on invented messages: the files, their check, the Kaggle
copies without words, the field catalogue, the card's Start here, and 0.1.0's card unchanged."""

import csv
import gzip
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from cap_samples import invented
from test_release import as_version
from test_tables import BASE, COUNTY, record, run
from warntext import access, fields, release, tables, xlsx

FIXTURE = Path(__file__).parent / "fixtures" / "release_0.1.0"


def _pack(tmp_path, version="0.2.0"):
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
    as_version(tmp_path / "t", "3")
    out = tmp_path / version
    m = release.build_pack(
        tmp_path / "t", out, version, "2026-11-25T12:00:00.000Z", "2026-11-26", "3"
    )
    release.build_kaggle(out, tmp_path / f"{version}-kaggle")
    return {
        "dir": out,
        "kaggle": tmp_path / f"{version}-kaggle",
        "manifest": m,
        "senders": [x["sender"] for x in b.raw_senders],
        "ids": b.raw_identifiers,
        "counts": {2024: len(recs)},
    }


@pytest.fixture()
def pack(tmp_path):
    return _pack(tmp_path)


def _check(pack):
    return release.check_pack(pack["dir"], pack["senders"], pack["ids"], pack["counts"])


def _rows(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def test_a_version_from_0_2_0_carries_the_layer_and_passes_its_check(pack):
    m = pack["manifest"]
    names = [f["path"] for f in m["access_files"]]
    assert names[:4] == [access.START_HERE, access.XLSX_WHOLE, "fields.csv", "codebook.csv"]
    assert names[4:] == [f["path"].replace(".parquet", ".csv.gz") for f in m["files"]]
    assert m["access"]["workbook"] == "whole" and m["access"]["start_here_rows"] == 4
    assert m["rows"] == sum(f["rows"] for f in m["files"])  # the Parquet rows only
    assert _check(pack) == []
    assert release.check_kaggle(pack["kaggle"], m) == []


def test_0_1_0_carries_no_layer_and_renders_its_published_card_byte_for_byte(tmp_path):
    assert not release.has_access_layer("0.1.0") and release.has_access_layer("0.2.1")
    manifest = json.loads((FIXTURE / "manifest.json").read_text())
    assert "access_files" not in manifest
    assert release.card(manifest) == (FIXTURE / "README.md").read_text()
    with pytest.raises(SystemExit, match="not a version"):
        release.version_tuple("0.2.x")


def test_the_start_here_file_holds_every_message_and_words_only_where_released(pack):
    rows = _rows(pack["dir"] / access.START_HERE)
    header, body = rows[0], rows[1:]
    assert header[: len(pq.read_schema(pack["dir"] / "alerts" / "messages.parquet").names)] == (
        tables.SCHEMAS["messages"].names
    )
    assert header[-len(fields.START_HERE_ADDED) :] == list(fields.START_HERE_ADDED)
    status = {r[header.index("message_id")]: r[header.index("text_status")] for r in body}
    assert sorted(status.values()) == ["released", "released", "released", "withheld"]
    for r in body:
        words = [r[header.index(c)] for c in ("headline", "description", "wea_short", "credit")]
        if r[header.index("text_status")] == "withheld":
            assert not any(words) and r[header.index("text_withheld")] == "people_code"
        else:
            assert r[header.index("credit")].startswith("Message by ")
    configs = [r[header.index("config")] for r in body]
    assert configs == sorted(configs)  # real alerts first, then tests
    assert {r[header.index("times_rounded")] for r in body} <= {"0", "1"}


def test_every_csv_equals_its_parquet_table_and_a_changed_cell_fails_the_check(pack):
    gz = pack["dir"] / "alerts" / "messages.csv.gz"
    table = pq.read_table(pack["dir"] / "alerts" / "messages.parquet")
    rows = _rows(gz)
    assert rows[0] == table.column_names and len(rows) == table.num_rows + 1
    assert rows[1][table.column_names.index("sent_utc")].endswith("Z")
    # A changed cell: written again with its manifest hash updated, the row comparison finds it.
    rows[1][table.column_names.index("year")] = "1999"
    access.write_csv(gz, rows[0], rows[1:])
    m = pack["manifest"]
    entry = next(f for f in m["access_files"] if f["path"] == "alerts/messages.csv.gz")
    entry["sha256"] = release.durable.sha256_file(gz)
    (pack["dir"] / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    assert any("row 1 differs" in f for f in _check(pack))


def test_a_file_that_differs_from_the_manifest_or_is_missing_fails(pack):
    (pack["dir"] / "fields.csv").write_text("table,column\n")
    assert any("fields.csv: does not match" in f for f in _check(pack))
    (pack["dir"] / "fields.csv").unlink()
    assert any("fields.csv: in the manifest but missing" in f for f in _check(pack))


def test_a_layer_left_out_of_a_0_2_version_fails(pack):
    m = dict(pack["manifest"])
    for f in m.pop("access_files"):
        (pack["dir"] / f["path"]).unlink()
    (pack["dir"] / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    assert any("lists no easy-access files" in f for f in _check(pack))


def test_words_for_a_withheld_message_fail_the_check(pack):
    path = pack["dir"] / access.START_HERE
    rows = _rows(path)
    h = rows[0]
    for r in rows[1:]:
        if r[h.index("text_status")] == "withheld":
            r[h.index("headline")] = "Invented words"
    access.write_csv(path, h, rows[1:])
    found = access._start_here_privacy(h, rows[1:])
    assert any("carry words for a message whose text is not released" in f for f in found)


def test_the_workbook_holds_the_same_rows_with_a_read_me_and_fields(pack):
    path = pack["dir"] / access.XLSX_WHOLE
    sheets = xlsx.read_workbook(path)
    assert [s.name for s in sheets] == ["Read me", "Messages", "Fields"]
    readme = " ".join(c for _, row in sheets[0].rows for c in row)
    assert "not an alerting service" in readme and "not endorsed by FEMA" in readme
    assert "WarnText" in readme and "(Version 0.2.0) [Data set]" in readme
    csv_rows = _rows(pack["dir"] / access.START_HERE)
    data = list(xlsx.read_data_rows(path, 2))
    assert data[0] == csv_rows[0] and len(data) == len(csv_rows)
    fields_rows = list(xlsx.read_data_rows(path, 3))
    assert fields_rows[0] == list(access.FIELDS_HEADER)


def test_a_workbook_past_the_limit_becomes_a_named_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(access, "XLSX_MAX_BYTES", 10)
    monkeypatch.setattr(access, "SAMPLE_ROWS", 2)
    p = _pack(tmp_path)
    assert p["manifest"]["access"]["workbook"] == "sample"
    assert not (p["dir"] / access.XLSX_WHOLE).exists()
    data = list(xlsx.read_data_rows(p["dir"] / access.XLSX_SAMPLE, 2))
    assert len(data) == 3  # the header and two rows
    readme = " ".join(
        c for _, row in xlsx.read_workbook(p["dir"] / access.XLSX_SAMPLE)[0].rows for c in row
    )
    assert "sample of 2 of the 4 messages" in readme
    assert _check(p) == []
    assert release.check_kaggle(p["kaggle"], p["manifest"]) == []


def test_excel_limits_are_enforced(tmp_path):
    with pytest.raises(xlsx.WorkbookError, match=r"over Excel's 32,767"):
        xlsx.write_data_workbook(
            tmp_path / "x.xlsx", (xlsx.DataSheet("S", [["a"], ["x" * 32_768]]),)
        )
    long = [["h"], ["x" * 32_768]]
    found = access._same(tmp_path / "none.csv", ["h"], iter(long[1:]), "none.csv")
    assert found == ["none.csv: missing."]


def test_fields_csv_describes_every_column_with_its_parquet_type(pack):
    rows = _rows(pack["dir"] / "fields.csv")
    assert rows[0] == list(access.FIELDS_HEADER)
    by = {(r[0], r[1]): r for r in rows[1:]}
    for f in pack["manifest"]["files"]:
        name = f["path"].split("/")[1].removesuffix(".parquet")
        for col in pq.read_schema(pack["dir"] / f["path"]):
            row = by[(name, col.name)]
            assert row[2] == fields.type_words(col.type) and row[3]
    assert by[("messages", "times_rounded")][2] == "yes or no (in CSV: 1 or 0)"
    assert by[("text_other", "headline")][5] == fields.HF_ONLY
    assert by[("start_here", "headline")][5] == fields.HF_ONLY
    assert by[("start_here", "text_status")][5] == fields.HF_AND_KAGGLE


def test_the_catalogue_covers_every_column_of_every_table_and_no_other():
    want = set()
    for name, schema in tables.SCHEMAS.items():
        for col in schema.names:
            want.add((fields.catalogue_table(name), col))
    for col, _ in release.CREDIT_COLUMNS:
        want.add(("text", col))
    want |= {("start_here", c) for c in fields.START_HERE_ADDED}
    assert set(fields.CATALOGUE) == want
    assert all(meaning for meaning, _ in fields.CATALOGUE.values())
    with pytest.raises(SystemExit, match=r"no entry for messages\.nope"):
        fields.entry("messages", "nope")
    with pytest.raises(SystemExit, match="No plain words"):
        fields.type_words(release.pa.binary())


def test_codebook_csv_gives_the_six_content_codes_with_their_status(pack):
    rows = _rows(pack["dir"] / "codebook.csv")
    assert rows[0] == list(access.CODEBOOK_HEADER)
    by = {r[0]: r for r in rows[1:]}
    assert list(by) == list(release.CONTENT_CODES)
    assert by["time"][4] == "validated" and by["time"][5] == "yes"
    assert by["location"][4] == "validated" and by["location"][5] == "yes"
    for code in ("hazard", "hazard_description", "source_named", "guidance"):
        assert by[code][4] == "experimental" and by[code][5] == "no"
    assert by["time"][6] == "0.9146" and by["time"][8] == "1.00"
    with pytest.raises(SystemExit, match="No content-code definitions"):
        access.codebook_rows("1", [])


def test_the_kaggle_copies_hold_no_words(pack):
    k = pack["kaggle"]
    names = sorted(p.name for p in k.iterdir())
    assert "README.md" not in names and access.START_HERE in names
    assert not any("text" in n for n in names)
    header = _rows(k / access.START_HERE)[0]
    assert "text_status" in header and "headline" not in header and "credit" not in header
    assert (k / "fields.csv").read_bytes() == (pack["dir"] / "fields.csv").read_bytes()
    meta = json.loads((k / "dataset-metadata.json").read_text())
    paths = [r["path"] for r in meta["resources"]]
    assert paths[0] == access.START_HERE and set(paths) == set(names) - {
        "dataset-metadata.json",
        "dataset-cover-image.png",
    }
    # A word column in a Kaggle file fails the check.
    rows = _rows(pack["dir"] / access.START_HERE)
    access.write_csv(k / access.START_HERE, rows[0], rows[1:])
    assert any("kaggle/00_start_here" in f for f in release.check_kaggle(k, pack["manifest"]))


def test_the_card_opens_with_start_here_and_its_configs_point_at_parquet_only(pack):
    card = (pack["dir"] / "README.md").read_text()
    assert (
        card.index("## Start here")
        < card.index("## What WarnText is")
        < card.index("## What it is not")
    )
    head = card.split("\n---\n", 1)[0]
    paths = [line.split("path: ")[1] for line in head.splitlines() if "path: " in line]
    assert paths and all(p.endswith(".parquet") for p in paths)
    assert 'read.csv("alerts/messages.csv.gz")' in card
    assert 'pd.read_parquet(f"alerts/{t}.parquet")' in card
    flat = " ".join(card.split())
    assert "**When a request concerns a person**" in flat
    assert "is a minor release, tagged `v0.2.0`" in flat
    assert "codebook version 3" in card
    assert release.card_metadata_problems(card, release.pack_tables(release.TEXT_KINDS)) == []


def test_a_weekly_version_says_it_is_a_commit_and_a_recreation_is_dated(pack):
    m = {**pack["manifest"], "version": "0.2.3"}
    flat = " ".join(release.card(m).split())
    assert "is a weekly version: a commit on `main`, not tagged" in flat
    m["recreated"] = [{"date": "2027-01-05", "versions": ["0.1.0", "0.2.0", "0.2.9"]}]
    text = " ".join(release.card(m).split())
    assert "On 5 January 2027 the dataset was deleted and created again" in text
    assert "0.1.0, 0.2.0, 0.2.9" in text


def test_the_kaggle_description_opens_with_its_own_start_here(pack):
    meta = json.loads((pack["kaggle"] / "dataset-metadata.json").read_text())
    text = meta["description"]
    assert "## Start here" in text and "no words" in text
    assert "alerts-messages.csv.gz" in text and "alerts/messages.csv.gz" not in text
    assert release.kaggle_metadata_problems(meta) == []


def test_cells_are_written_as_the_card_says():
    from datetime import datetime, timezone

    t = datetime(2026, 11, 14, 16, 59, tzinfo=timezone.utc)
    assert access.cell(True) == "1" and access.cell(False) == "0" and access.cell(None) == ""
    assert access.cell(["a", "b"]) == "a; b" and access.cell(t) == "2026-11-14T16:59:00Z"
    assert access.cell(t.replace(microsecond=250000)) == "2026-11-14T16:59:00.250Z"
    assert access.cell(0.5) == "0.5" and access.cell(3) == "3"


def test_the_same_pack_gives_the_same_bytes(tmp_path):
    a = _pack(tmp_path / "a")
    b = _pack(tmp_path / "b")
    for f in a["manifest"]["access_files"]:
        g = next(x for x in b["manifest"]["access_files"] if x["path"] == f["path"])
        assert f["sha256"] == g["sha256"], f["path"]


def test_the_release_check_cli_reads_the_layer(pack, tmp_path, capsys):
    from warntext import cli

    state = tmp_path / "state.json"
    state.write_text(json.dumps({"year_counts": {"2024": 4}}))
    shutil.copytree(pack["dir"].parent / "p", tmp_path / "priv", dirs_exist_ok=True)
    code = cli.main(
        [
            *("release", "check", "--pack", str(pack["dir"])),
            *("--private", str(tmp_path / "priv"), "--state", str(state)),
        ]
    )
    assert code == 0, capsys.readouterr().out
