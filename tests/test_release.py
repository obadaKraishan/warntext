"""The release pack and its own check, on invented messages."""

import json
import re
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cap_samples import invented
from test_tables import BASE, COUNTY, record, run
from warntext import cli, release, tables

#: The codebook version whose statuses release 0.1.0 carries. The invented records are coded by
#: the current rules and labeled version 1 here: these tests are about the pack, not the codes.
V1 = "1"


def as_version(tables_dir, version):
    """Label a test build's codes as ``version`` (the label the release statuses go by)."""
    path = tables_dir / "alerts" / "codes.parquet"
    t = pq.read_table(path)
    i = t.schema.get_field_index("codebook_version")
    column = pa.array([version] * t.num_rows, t.schema.field(i).type)
    pq.write_table(t.set_column(i, t.schema.field(i), column), path)


def _build(tmp_path, kinds=release.TEXT_KINDS, extra=()):
    recs = [
        record(invented(identifier="EX-1", sender=COUNTY), "r01"),
        record(invented(identifier="EX-2", sender=COUNTY, code="CAE"), "r02"),
        record(
            invented(identifier="EX-3", sender=BASE, sender_name="Example Air Force Base"),
            "r03",
            cog=202,
        ),
        record(invented(identifier="EX-4", sender=COUNTY, code="RWT"), "r04"),
        *extra,
    ]
    b = run(recs)
    tables.write(b, tmp_path / "t", tmp_path / "p")
    as_version(tmp_path / "t", V1)
    out = tmp_path / "pack"
    m = release.build_pack(
        tmp_path / "t",
        out,
        "0.1.0",
        "2026-11-14T17:00:00.000Z",
        "2026-11-15",
        V1,
        text_kinds=kinds,
    )
    senders = [x["sender"] for x in b.raw_senders]
    return {
        "dir": out,
        "manifest": m,
        "senders": senders,
        "ids": b.raw_identifiers,
        "tmp": tmp_path,
        "counts": {2024: len(recs)},
    }


@pytest.fixture()
def pack(tmp_path):
    return _build(tmp_path)


@pytest.fixture()
def federal_pack(tmp_path):
    return _build(tmp_path, kinds=release.FEDERAL_ONLY)


def test_the_pack_holds_the_record_layer_released_codes_and_both_text_tables(pack):
    paths = {f["path"] for f in pack["manifest"]["files"]}
    for name in ("text_federal", "text_other"):
        assert f"alerts/{name}.parquet" in paths and f"tests/{name}.parquet" in paths
    assert pack["manifest"]["text_tables"] == ["text_federal", "text_other"]
    assert pack["manifest"]["text_kinds"] == list(release.TEXT_KINDS)
    assert "tests/codes.parquet" not in paths  # tests carry no codes
    names = pq.read_schema(pack["dir"] / "alerts" / "codes.parquet").names
    assert not set(names) & set(release.EXPERIMENTAL_CODES)
    assert "link" in names and "hazard_category" in names and "guidance" not in names
    assert "hazard" not in names
    facts = pack["manifest"]["facts"]
    assert facts["real_alerts"] == 3 and facts["federal_text_alerts"] == 1
    assert facts["text_alerts"] == 2 and facts["text_tests"] == 1  # the CAE alert has none
    assert facts["withheld"] == facts["withheld_people_code"] == 1


def test_every_text_row_carries_its_credit(pack):
    other = pq.read_table(pack["dir"] / "alerts" / "text_other.parquet").to_pylist()
    federal = pq.read_table(pack["dir"] / "alerts" / "text_federal.parquet").to_pylist()
    names = pq.read_schema(pack["dir"] / "alerts" / "text_other.parquet").names
    assert names[names.index("sender_kind") + 1 : names.index("sender_kind") + 4] == [
        "cog_id",
        "organization",
        "credit",
    ]
    for r in other + federal:
        assert r["credit"] == release.credit_line(r["cog_id"], r["organization"])
        assert r["credit"].endswith("from FEMA OpenFEMA Dataset: IPAWS Archived Alerts - v1")
    assert federal[0]["cog_id"] == 202
    assert release.credit_line(7, None) == (
        "Message by IPAWS alerting authority FEMA ID 7; from "
        "FEMA OpenFEMA Dataset: IPAWS Archived Alerts - v1"
    )
    assert release.credit_line(7, "Example County") == (
        "Message by Example County (IPAWS alerting authority, FEMA ID 7); from "
        "FEMA OpenFEMA Dataset: IPAWS Archived Alerts - v1"
    )
    assert release.credit_line(None, "x") is None


def test_the_federal_only_setting_builds_the_old_pack(federal_pack):
    paths = {f["path"] for f in federal_pack["manifest"]["files"]}
    assert "alerts/text_federal.parquet" in paths and not any("text_other" in p for p in paths)
    assert federal_pack["manifest"]["text_tables"] == ["text_federal"]
    text = (federal_pack["dir"] / "README.md").read_text()
    assert "config_name: text_other" not in text
    assert (
        release.check_pack(
            federal_pack["dir"],
            federal_pack["senders"],
            federal_pack["ids"],
            federal_pack["counts"],
        )
        == []
    )
    with pytest.raises(SystemExit, match="give federal"):
        release.text_tables_for(("state",))
    with pytest.raises(SystemExit, match="unknown"):
        release.text_tables_for(("federal", "county"))


def test_the_card_is_filled_and_carries_the_license_fields(pack):
    text = (pack["dir"] / "README.md").read_text()
    assert release.card_metadata_problems(text) == []
    assert "config_name: text_other" in text and "path: tests/text_other.parquet" in text
    federal = release.pack_tables(release.FEDERAL_ONLY)
    assert "a config for text_other, which this pack does not hold" in (
        release.card_metadata_problems(text, federal)
    )
    assert not re.search(r"\{\{\w+\}\}", text)  # no placeholder left
    assert "2026-11-15" in text and "not an alerting service" in text
    assert "license_link: https://www.fema.gov/about/openfema/terms-conditions" in text
    assert release.card_metadata_problems("no header") == ["the card has no YAML header"]
    bad = text.replace("license: other", "license: cc-by-4.0").replace("config_name: codes", "x")
    problems = release.card_metadata_problems(bad)
    assert any("license must be 'other'" in p for p in problems)
    assert "no config for codes" in problems


def test_a_clean_pack_passes_and_each_wrong_file_fails(federal_pack):
    d = federal_pack["dir"]
    args = (federal_pack["senders"], federal_pack["ids"], federal_pack["counts"])
    assert release.check_pack(d, *args) == []
    shutil.copy(federal_pack["tmp"] / "t" / "alerts" / "text_other.parquet", d / "alerts")
    (d / "notes.txt").write_text("x")
    out = release.check_pack(d, *args)
    assert any("text_other.parquet: a text table this pack does not release" in f for f in out)
    assert any("notes.txt: not a file of the release" in f for f in out)


def test_a_text_row_without_its_credit_or_of_another_kind_fails(pack):
    d = pack["dir"]
    args = (pack["senders"], pack["ids"], pack["counts"])
    assert release.check_pack(d, *args) == []
    path = d / "alerts" / "text_other.parquet"
    rows = pq.read_table(path).to_pylist()
    schema = pq.read_schema(path)
    rows[0]["credit"] = None
    tables_ = {c: {n: [] for n in release.RELEASED_TABLES} for c in tables.CONFIGS}
    tables_["alerts"]["messages"] = pq.read_table(d / "alerts" / "messages.parquet").to_pylist()
    tables_["alerts"]["text_other"] = rows
    out = release.text_problems(tables_, release.TEXT_KINDS)
    assert any("without their credit" in f for f in out)
    rows[0]["credit"] = release.credit_line(rows[0]["cog_id"], rows[0]["organization"])
    rows[0]["cog_id"] = 999
    assert any("without their credit" in f for f in release.text_problems(tables_, ["federal"]))
    assert any(
        "of a kind this pack does not release" in f
        for f in release.text_problems(tables_, ["federal"])
    )
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    out = release.check_pack(d, *args)
    assert any("alerts/text_other.parquet: does not match its SHA-256" in f for f in out)
    assert any("without their credit" in f for f in out)
    pq.write_table(pa.table({"x": [1]}), path)
    assert any(
        "columns are not those of a released text_other" in f
        for f in (release.check_pack(d, *args))
    )


def test_text_for_a_message_any_privacy_rule_withholds_fails_in_either_split(pack):
    d = pack["dir"]
    for config in ("alerts", "tests"):
        messages = pq.read_table(d / config / "messages.parquet").to_pylist()
        text = pq.read_table(d / config / "text_other.parquet").to_pylist()
        target = next(m for m in messages if m["message_id"] == text[0]["message_id"])
        assert not target["text_withheld"]
        for field, value, label in (
            ("event_codes", ["CAE"], "a people code"),
            ("about_missing_person", True, "the missing-person rule"),
            ("withheld_patterns", ["phone"], "the pattern rule"),
            ("withheld_patterns", ["person_described"], "the description rule"),
            ("text_withheld", "personal_pattern", "the withheld flag"),
        ):
            changed = [dict(m, **{field: value}) if m is target else m for m in messages]
            tables_ = {c: {n: [] for n in release.RELEASED_TABLES} for c in tables.CONFIGS}
            tables_[config]["messages"] = changed
            tables_[config]["text_other"] = text
            out = release.text_problems(tables_, release.TEXT_KINDS)
            assert any(
                f"{config}/text_other: 1 text row(s) for messages withheld by {label}" in f
                for f in out
            ), (field, out)
            if field != "text_withheld":
                assert any("meet a privacy rule but are not marked withheld" in f for f in out)


def test_personal_details_or_missing_person_words_in_released_text_fail(pack):
    d = pack["dir"]
    messages = pq.read_table(d / "alerts" / "messages.parquet").to_pylist()
    text = pq.read_table(d / "alerts" / "text_other.parquet").to_pylist()
    tables_ = {c: {n: [] for n in release.RELEASED_TABLES} for c in tables.CONFIGS}
    tables_["alerts"]["messages"] = messages
    for field, value, hit in (
        ("description", "Call 555-555-0142 for details.", "description:phone"),
        ("audience", "Have you seen this man?", "audience:missing_person"),
        ("resource_descriptions", ["Last seen near the park"], "resource_descriptions:last_seen"),
    ):
        tables_["alerts"]["text_other"] = [dict(text[0], **{field: value})]
        out = release.text_problems(tables_, release.TEXT_KINDS)
        assert any("released text matches personal-detail patterns" in f and hit in f for f in out)
    tables_["alerts"]["text_other"] = text
    assert release.text_problems(tables_, release.TEXT_KINDS) == []


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
                *("--codebook-version", V1),
            ]
        )
        == 0
    )
    check = ["release", "check", "--pack", str(out), "--private", str(pack["tmp"] / "p")]
    assert cli.main([*check, "--state", str(state)]) == 0
    assert "Release pack check passed" in capsys.readouterr().out
    pq.write_table(pa.table({"x": [1]}), out / "alerts" / "text_other.parquet")
    assert cli.main([*check, "--state", str(state)]) == 1
    old = tmp_path / "pack-federal"
    assert (
        cli.main(
            [
                *build,
                *("--out", str(old), "--version", "0.1.0", "--retrieved", "2026-11-15"),
                *("--codebook-version", V1, "--text-kinds", "federal"),
            ]
        )
        == 0
    )
    assert not (old / "alerts" / "text_other.parquet").exists()


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
    # No content code of the six is released: hazard is experimental on the second sheet's bound.
    six = ("hazard", "hazard_description", "source_named", "guidance", "time", "location")
    assert all(status[c]["status"] == "experimental" for c in six)
    assert status["hazard_category"]["status"] == "released"
    assert status["link"]["status"] == status["about_test"]["status"] == "released"
    tables = release.code_tables()
    assert "| `hazard` | 0.86 | 0.94 | experimental |" in tables["code_alpha_table"]
    assert "`hazard`" in tables["codes_left_out"] and "`hazard`" not in tables["codes_released"]
    assert "`hazard_category`" in tables["codes_released"]


def test_version_3s_statuses_release_time_and_location_with_both_figures():
    from warntext.codes import CODE_FIELDS

    assert release.status_versions() == ("1", "3")
    v1, v3 = release.code_status("1"), release.code_status("3")
    assert set(v3) == set(CODE_FIELDS) and v1 == release.code_status()
    # The second half of the rule: only time and location pass both figures.
    assert {c for c in release.CONTENT_CODES if v3[c]["status"] == "released"} == {
        "time",
        "location",
    }
    for c in release.CONTENT_CODES:
        r = v3[c]
        assert all(r[k] for k in ("hand_sheet_alpha", "alpha_low", "alpha_high", "recheck_alpha"))
        passes = float(r["hand_sheet_alpha"]) >= 0.8 and float(r["recheck_alpha"]) >= 0.8
        assert passes == (r["status"] == "released")
        assert not v1[c]["recheck_alpha"]  # version 1 never had a recheck
    # Parts of a code are not on the sheets: they stay experimental, as do trust C codes.
    for c in ("loc_boundary", "loc_vague_or_none", "time_expiry", "loc_road", "complete"):
        assert v3[c]["status"] == "experimental"
    mechanical = [c for c, r in v1.items() if r["status"] == "released"]
    assert all(v3[c]["status"] == "released" for c in mechanical)
    assert set(release.experimental_codes("3")) == set(release.EXPERIMENTAL_CODES) - {
        "time",
        "location",
    }
    tables = release.code_tables("3")
    assert (
        "| `time` | 0.9146 | 0.82 to 0.9796 | 1.00 | 1.00 to 1.00 | validated |"
        in (tables["code_alpha_table"])
    )
    assert (
        "| `hazard` | 0.73 | 0.5813 to 0.8688 | 0.7579 | 0.4503 to 1.00 | experimental |"
        in (tables["code_alpha_table"])
    )
    assert tables["codes_validated"] == "`time`, `location`"
    assert "`time`" not in tables["codes_mechanical"] and "`link`" in tables["codes_mechanical"]
    with pytest.raises(SystemExit, match="no statuses for codebook version '2'"):
        release.code_status("2")


def test_a_version_3_pack_carries_time_and_location_and_its_own_card(pack, tmp_path):
    as_version(pack["tmp"] / "t", "3")
    out = tmp_path / "pack-v3"
    m = release.build_pack(
        pack["tmp"] / "t", out, "0.2.0", "2026-11-21T17:00:00.000Z", "2026-11-22", "3"
    )
    assert m["codebook_version"] == "3" and "time" not in m["experimental_codes_left_out"]
    names = pq.read_schema(out / "alerts" / "codes.parquet").names
    assert "time" in names and "location" in names and "hazard" not in names
    card = (out / "README.md").read_text()
    assert (
        "codebook version 3" in card and "**Validated content codes in this version: `time`" in card
    )
    assert "| `location` | 0.8003 | 0.6388 to 0.9234 | 1.00 | 1.00 to 1.00 | validated |" in card
    assert "about one text in ten" in card and "No validated content code" not in card
    assert "The language check is by rule." in card and "finds Spanish only" not in card
    assert release.check_pack(out, pack["senders"], pack["ids"], {2024: 4}) == []
    # Version 1's pack: its own section, and a manifest without the version reads as version 1.
    v1_card = (pack["dir"] / "README.md").read_text()
    assert "**No validated content code is in this version.**" in v1_card
    assert "finds Spanish only" in v1_card and "codebook version 3" not in v1_card
    old = {k: v for k, v in pack["manifest"].items() if k != "codebook_version"}
    assert release.card(old) == release.card(pack["manifest"])
    # A version 1 pack's columns fail a check that reads its manifest as version 3.
    manifest = json.loads((pack["dir"] / "manifest.json").read_text())
    (pack["dir"] / "manifest.json").write_text(json.dumps({**manifest, "codebook_version": "3"}))
    assert any(
        "columns are not those" in f
        for f in release.check_pack(pack["dir"], pack["senders"], pack["ids"], {2024: 4})
    )


def test_a_pack_is_refused_from_codes_of_another_version(pack, tmp_path):
    with pytest.raises(SystemExit, match="no statuses for codebook version '0'"):
        release.build_pack(pack["tmp"] / "t", tmp_path / "other", "0.1.0", "x", "y", "0")
    # Version 3 has statuses, but these tables' codes are labeled version 1.
    with pytest.raises(SystemExit, match="measured on version 3"):
        release.build_pack(pack["tmp"] / "t", tmp_path / "other", "0.1.0", "x", "y", "3")


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


def test_the_size_tag_follows_the_rows_in_all(pack):
    assert release.size_category(999) == "n<1K"
    assert release.size_category(1_000) == "1K<n<10K"
    assert release.size_category(99_999) == "10K<n<100K"
    assert release.size_category(500_139) == "100K<n<1M"
    assert release.size_category(10**13) == "n>1T"
    text = (pack["dir"] / "README.md").read_text()
    rows = pack["manifest"]["rows"]
    assert f"size_categories:\n- {release.size_category(rows)}\n" in text
    assert release.card_metadata_problems(text, None, rows) == []
    wrong = text.replace(f"- {release.size_category(rows)}\n", "- 100K<n<1M\n", 1)
    assert any(
        "size_categories must be" in p for p in release.card_metadata_problems(wrong, None, rows)
    )


def test_the_card_makes_the_counts_add_up(tmp_path):
    # An invented cancellation with no information block: no text, not withheld.
    cancel = re.sub(
        r"<info>.*</info>",
        "",
        invented(identifier="EX-5", sender=COUNTY, msg_type="Cancel"),
        flags=re.S,
    )
    b = _build(tmp_path, extra=[record(cancel, "r05")])
    f = b["manifest"]["facts"]
    assert f["real_alerts"] == f["withheld"] + f["text_alerts"] + f["no_text_alerts"]
    assert f["no_text_alerts"] == f["no_text_cancels"] == 1
    assert f["tests"] == f["tests_withheld"] + f["text_tests"] + f["tests_no_text"]
    text = (b["dir"] / "README.md").read_text()
    assert "The other 1 real alerts carry no words in the archive: each is a cancellation" in text
    assert "Of the 1 tests, 0 have their text withheld by the same rules." in text
    s = release.text_sentences(
        {
            "no_text_alerts": 5,
            "no_text_cancels": 3,
            "tests": 9,
            "tests_withheld": 2,
            "tests_no_text": 4,
            "tests_kind_left_out": 1,
        }
    )
    assert "(3 of them cancellations" in s["no_text_sentence"]
    assert "4 have no text here (1 of a sender kind" in s["tests_text_sentence"]
    s = release.text_sentences(
        {"tests": 3, "tests_withheld": 1, "tests_no_text": 2, "tests_kind_left_out": 2}
    )
    assert s["no_text_sentence"] == ""
    assert s["tests_text_sentence"].endswith(
        "2 are of a sender kind whose text this version leaves out."
    )


def test_a_card_rewrite_measures_new_facts_and_refuses_a_manifest_that_disagrees(pack):
    d = pack["dir"]
    m = json.loads((d / "manifest.json").read_text())
    good = (d / "README.md").read_text()
    older = dict(m, facts={k: v for k, v in m["facts"].items() if k != "tests_withheld"})
    (d / "manifest.json").write_text(json.dumps(older, indent=1) + "\n")
    assert release.rewrite_card(d) is False  # the same card, the missing count measured again
    assert (d / "README.md").read_text() == good
    wrong = dict(m, facts=dict(m["facts"], text_alerts=99))
    (d / "manifest.json").write_text(json.dumps(wrong, indent=1) + "\n")
    with pytest.raises(SystemExit, match="differ from the pack's files"):
        release.rewrite_card(d)


def test_any_written_form_of_a_number_or_a_description_in_released_text_fails(pack):
    d = pack["dir"]
    for config in ("alerts", "tests"):
        messages = pq.read_table(d / config / "messages.parquet").to_pylist()
        text = pq.read_table(d / config / "text_other.parquet").to_pylist()
        tables_ = {c: {n: [] for n in release.RELEASED_TABLES} for c in tables.CONFIGS}
        tables_[config]["messages"] = messages
        for field, value, hit in (
            ("description", "Invented: call 5555550123 now.", "description:phone_any_form"),
            ("wea_short", "Invented: call 555-0123 now.", "wea_short:phone_seven"),
            ("instruction", "Invented: call 1-800-555-HELP.", "instruction:phone_letters"),
            ("web", "Invented: tips[at]example[dot]org", "web:email_any_form"),
            ("headline", "Invented: a twelve-year-old", "headline:age_any_form"),
        ):
            tables_[config]["text_other"] = [dict(text[0], **{field: value})]
            out = release.text_problems(tables_, release.TEXT_KINDS)
            assert any(hit in f for f in out), (config, field, out)
        # a description split over two fields of one message, with no cue word in either
        two = dict(
            text[0],
            headline="Invented: police seek a white male",
            description="Invented: in a red hoodie near the example park.",
        )
        tables_[config]["text_other"] = [two]
        out = release.text_problems(tables_, release.TEXT_KINDS)
        assert any("describes a person" in f for f in out), out
        tables_[config]["text_other"] = [dict(two, description="Invented: near the park.")]
        assert release.text_problems(tables_, release.TEXT_KINDS) == []


def test_codes_from_another_build_of_the_same_units(pack, tmp_path):
    # the same records built twice: the codes of one, the record and text layers of the other
    other = tmp_path / "other"
    shutil.copytree(pack["tmp"] / "t", other)
    m = release.build_pack(
        pack["tmp"] / "t",
        tmp_path / "pack3",
        "0.1.0",
        "2026-11-14T17:00:00.000Z",
        "2026-11-15",
        V1,
        codes_from=other,
    )
    assert {f["path"]: f["sha256"] for f in m["files"]} == {
        f["path"]: f["sha256"] for f in pack["manifest"]["files"]
    }
    codes = pq.read_table(other / "alerts" / "codes.parquet")
    pq.write_table(codes.slice(1), other / "alerts" / "codes.parquet")
    with pytest.raises(SystemExit, match="different: build both from the same records"):
        release.build_pack(
            pack["tmp"] / "t",
            tmp_path / "pack4",
            "0.1.0",
            "x",
            "y",
            V1,
            codes_from=other,
        )
    with pytest.raises(SystemExit, match="is missing"):
        release.build_pack(
            pack["tmp"] / "t",
            tmp_path / "pack5",
            "0.1.0",
            "x",
            "y",
            V1,
            codes_from=tmp_path / "none",
        )


def test_the_card_says_what_is_withheld_and_the_reading_of_what_is_left(pack):
    text = (pack["dir"] / "README.md").read_text(encoding="utf-8")
    assert "**What is withheld:**" in text
    assert "a phone number or an email address in any written form" in text
    assert "rules miss cases" in text
    assert not re.search(r"\{\{\w+\}\}", text)
    assert release.privacy_reading_sentence({}).startswith("No reading")
    reading = {"alerts": 300, "tests": 100, "contact": 0, "described": 0, "named": 2, "rounds": 2}
    sentence = release.privacy_reading_sentence(reading)
    assert "300 released alert texts and 100 released test texts" in sentence
    assert "was read in the last of 2 rounds" in sentence
    assert "was read once: 0 held" in release.privacy_reading_sentence(release.PRIVACY_READING)
    assert "300 released alert texts and 100 released test texts" in text
    assert "0 held a phone number or an email address, 0 described a person" in sentence
    assert "and 2 named a private individual" in sentence


def test_a_removal_takes_the_text_row_keeps_the_record_row_and_a_stale_pack_fails(pack, tmp_path):
    # Invented records: the first (a county's alert with text) is asked to be removed.
    ids = {
        m["message_id"]
        for m in pq.read_table(pack["dir"] / "alerts" / "text_other.parquet").to_pylist()
    }
    target = sorted(ids)[0]
    listed = frozenset({target})
    # The pack built before the entry fails its check now: the record row is not marked
    # withheld and its text row is still there.
    out = release.check_pack(pack["dir"], pack["senders"], pack["ids"], {2024: 4}, listed)
    assert any("on the removal list are not withheld" in f for f in out)
    assert any("not marked withheld" in f for f in out)
    assert any("text row(s) for messages withheld by the removal list" in f for f in out)
    with pytest.raises(SystemExit, match="on the removal list are not withheld"):
        release.stale_on_removal_list(pack["tmp"] / "t", listed)
    # A build that reads the list: the text row leaves, the record row stays.
    from cap_samples import invented
    from test_tables import BASE, COUNTY, record

    recs = [
        record(invented(identifier="EX-1", sender=COUNTY), target),
        record(invented(identifier="EX-2", sender=COUNTY, code="CAE"), "r02"),
        record(invented(identifier="EX-3", sender=BASE), "r03", cog=202),
    ]
    b = tables.build(
        tables.parse_records(
            (type("L", (), {"fetched_at": "2026-11-15T15:00:00.000Z"})(), r) for r in recs
        ),
        removals=listed | {"r02"},
    )
    messages = {m["message_id"]: m for m in b.tables["alerts"]["messages"]}
    assert messages[target]["text_withheld"] == "removed_on_request"
    assert messages["r02"]["text_withheld"] == "people_code"  # the earlier reason is kept
    assert messages["r03"]["text_withheld"] is None
    text_ids = {
        r["message_id"] for t in ("text_federal", "text_other") for r in b.tables["alerts"][t]
    }
    assert target not in text_ids and "r03" in text_ids
    assert any(r["message_id"] == target for r in b.tables["alerts"]["infos"])
    assert any(r["message_id"] == target for r in b.tables["alerts"]["codes"])
    assert b.summary["removal_list"] == {
        "entries": 2,
        "messages_listed": 2,
        "withheld_only_by_the_list": 1,
        "entries_not_in_the_records": 0,
    }
    # (the build's rows carry no credit columns yet; only the withholding rules are asked here)
    problems = release.text_problems(b.tables, release.TEXT_KINDS, listed)
    assert not [f for f in problems if "removal list" in f or "not marked withheld" in f]
    assert release.text_sentences({"withheld_removed": 1})["removed_sentence"].startswith(
        " In this version 1 real alert(s) and 0 test(s)"
    )
    assert release.text_sentences({})["removed_sentence"] == ""


def test_warntext_text_never_reads_a_listed_message_again():
    from warntext import rebuild

    messages = [
        {"message_id": "a", "record_ids": ["a"], "text_withheld": None, "sender_kind": "local"},
        {"message_id": "b", "record_ids": ["b"], "text_withheld": None, "sender_kind": "local"},
    ]
    planned = rebuild.plan(messages, None, set(), removals={"a"})
    assert [m["message_id"] for m in planned["withheld"]] == ["a"]
    assert [m["message_id"] for m in planned["read"]] == ["b"]
    assert [m["message_id"] for m in rebuild.wanted(messages, None, removals={"a"})] == ["b"]
    assert len(rebuild.wanted(messages, None)) == 2  # the tracked list is empty


def test_the_cards_updates_say_the_dataset_was_re_created(pack):
    card = (pack["dir"] / "README.md").read_text()
    updates = card[card.index("## Updates") :]
    assert "On 24 November 2026 the dataset was re-created with a single version" in " ".join(
        updates.split()
    )
    assert "the files of release 0.1.0 are unchanged (the same hashes)." in " ".join(
        updates.split()
    )
