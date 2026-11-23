"""The Kaggle mirror's page (description, tags, sources, cover) and its checks, on invented
messages."""

import json
import re

import pyarrow.parquet as pq
import pytest

from test_release import _build
from warntext import cli, cover, kaggle_meta, release


@pytest.fixture()
def pack(tmp_path):
    return _build(tmp_path)


def _mirror(pack):
    out = pack["tmp"] / "pack-kaggle"
    meta = release.build_kaggle(pack["dir"], out)
    return out, meta


def test_the_tracked_cover_is_what_the_code_draws_at_560_by_280():
    data = cover.TRACKED.read_bytes()
    assert cover.png_size(data) == (560, 280)
    size, raw = cover.read_png(data)
    assert size == (560, 280)
    assert raw == b"".join(b"\x00" + bytes(row) for row in cover.draw())
    assert cover.png(cover.draw()) == data
    assert cover.png_size(b"not a png at all, just words") is None
    with pytest.raises(ValueError, match="not a PNG"):
        cover.read_png(b"GIF89a")


def test_the_name_sits_in_the_top_left_corner():
    img = cover.draw()
    ink = bytes(cover.INK)
    # The name's ink is inside the top left quarter; nothing is drawn in ink below the name.
    rows = [y for y, row in enumerate(img) if ink in bytes(row)]
    cols = [x for y in rows for x in range(cover.WIDTH) if bytes(img[y][3 * x : 3 * x + 3]) == ink]
    assert min(rows) >= cover.TOP and max(rows) < cover.TOP + 7 * cover.SCALE < 140
    assert min(cols) == cover.LEFT and max(cols) < cover.WIDTH // 2 + 40


def test_cover_main_writes_a_png(tmp_path, capsys):
    out = tmp_path / "cover.png"
    assert cover.main([str(out)]) == 0
    assert out.read_bytes() == cover.TRACKED.read_bytes()
    assert "560 x 280" in capsys.readouterr().out


def test_the_mirror_page_has_its_headings_tags_sources_and_cover(pack):
    out, meta = _mirror(pack)
    assert kaggle_meta.headings(meta["description"]) == list(kaggle_meta.HEADINGS)
    assert meta["keywords"] == list(kaggle_meta.KAGGLE_TAGS)
    assert meta["expectedUpdateFrequency"] == "not specified"
    assert kaggle_meta.SOURCE_ENDPOINT in meta["userSpecifiedSources"]
    assert "retrieved 2026-11-15 (UTC)" in meta["userSpecifiedSources"]
    assert len(meta["title"]) <= 50 and "doi" not in {k.lower() for k in meta}
    assert (out / kaggle_meta.COVER_NAME).read_bytes() == cover.TRACKED.read_bytes()
    files = sorted(p.name for p in out.iterdir() if p.suffix == ".parquet")
    assert sorted(r["path"] for r in meta["resources"]) == files
    assert all(r["description"].endswith("No message text.") for r in meta["resources"])
    assert release.check_kaggle(out, pack["manifest"]) == []


def test_how_to_cite_and_the_other_sections_are_the_cards_own(pack):
    _, meta = _mirror(pack)
    card = (pack["dir"] / "README.md").read_text()
    for card_heading, heading in kaggle_meta.FROM_CARD:
        body = kaggle_meta.card_section(card, card_heading)
        assert f"## {heading}\n{body}\n" in meta["description"]
    assert kaggle_meta.card_box(card) in meta["description"]
    assert "never message text" in meta["description"]


def test_the_description_holds_no_message_text(pack):
    _, meta = _mirror(pack)
    page = meta["description"] + meta["userSpecifiedSources"]
    page += " ".join(r["description"] for r in meta["resources"])
    values = set()
    for split in ("alerts", "tests"):
        for name in ("text_federal", "text_other"):
            for row in pq.read_table(pack["dir"] / split / f"{name}.parquet").to_pylist():
                values |= {v for v in row.values() if isinstance(v, str) and len(v) >= 12}
    leaked = [v for v in values if v in page and not v.startswith(("http", "FEMA OpenFEMA"))]
    assert leaked == []


def test_each_problem_of_the_metadata_is_named(pack):
    _, meta = _mirror(pack)
    assert kaggle_meta.problems(meta) == []

    def one(**change):
        return " ".join(kaggle_meta.problems(dict(meta, **change)))

    assert "not on the list of Kaggle tags" in one(keywords=["emergency alerts", "government"])
    assert "no tags" in one(keywords=[])
    assert "given twice" in one(keywords=["government", "government"])
    assert "'weekly', not 'not specified'" in one(expectedUpdateFrequency="weekly")
    assert "blanks the sources" in one(userSpecifiedSources="")
    assert "license" in one(licenses=[{"name": "CC0-1.0"}])
    assert "has no description" in one(resources=[{"path": "alerts-messages.parquet"}])
    no_cite = meta["description"].replace("## How to cite", "## How to quote")
    assert "headings are" in one(description=no_cite)
    empty = re.sub(
        r"## How to cite\n.*?(?=## Links)", "## How to cite\n", meta["description"], flags=re.S
    )
    assert "'How to cite' section is empty" in one(description=empty)
    assert "the cap is" in one(description=meta["description"] + "x" * 20_000)
    assert "'<b>'" in one(description=meta["description"] + " <b>bold</b>")


def test_a_cover_of_another_size_or_none_fails_the_check(pack):
    out, _ = _mirror(pack)
    path = out / kaggle_meta.COVER_NAME
    img = [row[: 3 * 280] for row in cover.draw()]
    path.write_bytes(cover.png(img))
    assert any("(280, 280)" in f for f in release.check_kaggle(out))
    path.write_bytes(b"not an image")
    assert any("not a PNG" in f for f in release.check_kaggle(out))
    path.unlink()
    assert any("is missing" in f for f in release.check_kaggle(out))


def test_the_metadata_and_cover_are_written_again_and_the_data_files_stay(pack, capsys):
    out, _ = _mirror(pack)
    data = {p.name: p.read_bytes() for p in out.iterdir() if p.suffix == ".parquet"}
    meta_path = out / kaggle_meta.METADATA_NAME
    meta_path.write_text(json.dumps({"title": "an older page"}))
    (out / kaggle_meta.COVER_NAME).unlink()
    changed = release.rewrite_kaggle(pack["dir"], out)
    assert changed == {kaggle_meta.METADATA_NAME: True, kaggle_meta.COVER_NAME: True}
    assert release.rewrite_kaggle(pack["dir"], out) == dict.fromkeys(changed, False)
    assert {p.name: p.read_bytes() for p in out.iterdir() if p.suffix == ".parquet"} == data
    assert cli.main(["release", "kaggle-meta", "--pack", str(pack["dir"])]) == 0
    said = capsys.readouterr().out
    assert "dataset-metadata.json unchanged" in said and "not touched" in said


def test_the_doi_added_to_the_card_reaches_the_kaggle_page(pack):
    out, _ = _mirror(pack)
    readme = pack["dir"] / "README.md"
    card = readme.read_text()
    readme.write_text(card.replace("## How to cite\n", "## How to cite\nDOI: 10.5281/zenodo.123\n"))
    release.rewrite_kaggle(pack["dir"], out)
    meta = json.loads((out / kaggle_meta.METADATA_NAME).read_text())
    assert "## How to cite\nDOI: 10.5281/zenodo.123\n" in meta["description"]


def test_a_data_file_that_differs_stops_the_rewrite_and_fails_the_check(pack):
    out, _ = _mirror(pack)
    meta_before = (out / kaggle_meta.METADATA_NAME).read_bytes()
    target = out / "alerts-messages.parquet"
    target.write_bytes(target.read_bytes() + b"\0")
    with pytest.raises(SystemExit, match=r"Nothing was written: kaggle/alerts-messages\.parquet"):
        release.rewrite_kaggle(pack["dir"], out)
    assert (out / kaggle_meta.METADATA_NAME).read_bytes() == meta_before
    assert any("differs from the pack" in f for f in release.check_kaggle(out, pack["manifest"]))
    target.unlink()
    assert any("is missing" in f for f in release.check_kaggle(out, pack["manifest"]))


def test_a_card_without_a_section_or_box_is_refused(pack):
    card = (pack["dir"] / "README.md").read_text()
    with pytest.raises(SystemExit, match="no '## Limits' section"):
        kaggle_meta.card_section(card.replace("## Limits", "## Bounds"), "Limits")
    with pytest.raises(SystemExit, match="no opening paragraph"):
        kaggle_meta.card_box(card.replace("# WarnText\n", "# Something\n"))


def test_the_command_stops_on_a_data_file_that_differs(pack):
    out, _ = _mirror(pack)
    target = out / "alerts-codes.parquet"
    target.write_bytes(target.read_bytes() + b"\0")
    with pytest.raises(SystemExit, match=r"alerts-codes\.parquet differs"):
        cli.main(["release", "kaggle-meta", "--pack", str(pack["dir"])])
