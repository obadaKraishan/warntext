"""The hand sheet: the draw, the blind workbook, the key and the check, on invented texts."""

import pytest

from warntext import sheet as sh
from warntext import xlsx

CODE_FIELDS = [f for _, f in sh.CODES]


def message(mid, year=2021, **kw):
    row = {
        "message_id": mid,
        "record_id": f"rec-{mid}",
        "config": "alerts",
        "msg_type": "Alert",
        "text_withheld": None,
        "year": year,
        "text_group": mid,
    }
    row.update(kw)
    return row


def code(mid, unit, category="wildfire", **kw):
    row = {
        "message_id": mid,
        "info_index": 0,
        "unit": unit,
        "coded": True,
        "language": "en-US",
        "about_test": False,
        "about_missing_person": False,
        "same_as_wea90": None,
        "hazard_category": category,
    }
    row.update({f: False for f in CODE_FIELDS})
    row.update(kw)
    return row


def text(mid, short="Invented short text.", long="Invented long text.", head="Head"):
    return {
        "message_id": mid,
        "info_index": 0,
        "wea_short": short,
        "wea_long": long,
        "headline": head,
        "description": f"Invented description {mid}.",
        "instruction": None,
    }


def corpus(n=60):
    messages, codes, texts = [], [], []
    cats = ["wildfire", "public_safety", "law_enforcement", "atmospheric"]
    for k in range(n):
        mid = f"m{k:03d}"
        messages.append(message(mid, year=2016 if k % 2 else 2022))
        for unit in ("wea90", "wea360", "full"):
            codes.append(code(mid, unit, cats[k % 4]))
        texts.append(text(mid, short=f"Invented short {mid}.", long=f"Invented long {mid}."))
    return messages, codes, texts


def test_candidates_leave_out_what_may_not_go_on_the_sheet():
    messages = [
        message("a"),
        message("w", text_withheld="people_code"),
        message("c", msg_type="Cancel"),
        message("t", config="tests"),
    ]
    codes = [
        code("a", "wea90"),
        code("a", "wea360", same_as_wea90=True),
        code("a", "full", about_test=True),
        code("w", "wea90"),
        code("c", "wea90"),
        code("t", "wea90"),
    ]
    texts = [text("a"), text("c"), text("t")]
    items = sh.candidates(messages, codes, texts)
    assert [(i.message_id, i.unit) for i in items] == [("a", "wea90")]
    long = [text("a", head="x" * (sh.MAX_FULL + 1))]
    assert sh.candidates([message("a")], [code("a", "full")], long) == []


def test_the_draw_is_stratified_seeded_and_one_unit_per_message():
    messages, codes, texts = corpus()
    items = sh.candidates(messages, codes, texts)
    chosen = sh.draw(items, seed=7, total=30)
    assert len(chosen) == 30
    assert len({i.message_id for i in chosen}) == 30
    made = sh.strata(chosen)
    assert set(made["by_unit"]) == {"wea90", "wea360", "full"}
    assert max(made["by_unit"].values()) - min(made["by_unit"].values()) <= 2
    assert set(made["by_period"]) == {"before_2020", "2020_on"}
    assert len(made["by_category"]) == 4
    assert [i.message_id for i in sh.draw(items, seed=7, total=30)] == [
        i.message_id for i in chosen
    ]


def test_one_message_per_text_group():
    messages, codes, texts = corpus(4)
    items = sh.candidates(messages, codes, texts)
    groups = {"m000": "g", "m001": "g", "m002": "m002", "m003": "m003"}
    kept = sh.one_per_text_group(items, groups, seed=1)
    assert len({i.message_id for i in kept}) == 3


def test_allocation_gives_every_cell_one_and_never_more_than_it_has():
    out = sh._allocate({"a": 100, "b": 4, "c": 1, "d": 0}, 10)
    assert sum(out.values()) == 10 and out["c"] == 1 and "d" not in out and out["b"] <= 4


def test_the_workbook_is_blind_and_the_key_is_apart(tmp_path):
    messages, codes, texts = corpus(24)
    chosen = sh.draw(sh.candidates(messages, codes, texts), seed=3, total=6)
    assert len(chosen) == 6
    paths = sh.write(chosen, tmp_path)
    visible = next(s for s in xlsx.read_workbook(paths["workbook"]) if not s.hidden)
    header = visible.rows[0][1]
    assert header[:2] == ("Row", "Text") and "Note" in header
    cells = {c for _, row in visible.rows for c in row}
    assert not any(c in cells for c in ("wildfire", "True", "False", "m000"))
    key = sh.read_key(paths["key"])
    assert set(key) == set(range(1, 7))


def test_the_workbook_carries_the_settled_definitions_and_a_plain_text_guide(tmp_path):
    messages, codes, texts = corpus(24)
    chosen = sh.draw(sh.candidates(messages, codes, texts), seed=3, total=6)
    paths = sh.write(chosen, tmp_path, "hand_sheet_2")
    assert [p.name for p in paths.values()] == [
        "hand_sheet_2.xlsx",
        "hand_sheet_2_key.csv",
        "hand_sheet_2_guide.txt",
    ]
    read = xlsx.read_workbook(paths["workbook"])
    assert [(s.name, s.hidden) for s in read] == [
        ("Hand sheet", False),
        ("Definitions", False),
        (xlsx.CHOICES_SHEET, True),
    ]
    definitions = read[1].rows
    assert definitions[0][1] == (sh.GUIDE_FIRST_LINE,)
    cells = {c for _, row in definitions for c in row}
    assert [h for h, *_ in sh.DEFINITIONS] == [h for h, _ in sh.CODES]
    assert all(d in cells for _, d, _, _ in sh.DEFINITIONS)
    assert sum(text in cells for text, _, _ in sh.EDGE_CASES) == 3
    guide = paths["guide"].read_text(encoding="utf-8")
    assert guide.splitlines()[0] == "Judge only the words in the text. About a minute per row."
    assert all(d in guide for _, d, _, _ in sh.DEFINITIONS)
    # The settled definitions, word for word.
    assert sh.DEFINITIONS[2][1].endswith('(an opener such as "City of X:", or "from X County").')
    assert sh.DEFINITIONS[3][1].startswith("Any instruction or prohibition to the public, in any")
    # sheet-check reads the first sheet, whatever follows it.
    assert sh.read_filled(paths["workbook"]) == {n: dict.fromkeys(CODE_FIELDS) for n in range(1, 7)}


def test_a_later_sheet_leaves_out_the_text_groups_and_texts_already_used(tmp_path):
    messages, codes, texts = corpus(40)
    messages[1]["text_group"] = "m000"  # a re-send of m000
    texts[2]["wea_short"] = texts[0]["wea_short"]  # m002 repeats m000's text
    groups = {m["message_id"]: m["text_group"] for m in messages}
    key = [{"message_id": "m000", "info_index": "0", "unit": "wea90"}]
    used_groups, used_texts = sh.used_by(key, groups, texts)
    assert used_groups == {"m000"} and used_texts == {"invented short m000."}
    items = sh.without_used(sh.candidates(messages, codes, texts), groups, used_groups, used_texts)
    assert not any(i.message_id in ("m000", "m001") for i in items)
    assert not any(i.message_id == "m002" and i.unit == "wea90" for i in items)
    assert any(i.message_id == "m002" and i.unit == "full" for i in items)


def filled_sheet(path, values):
    head = [("Row", sh._HEAD), ("Text", sh._HEAD)] + [(h, sh._HEAD) for h, _ in sh.CODES]
    rows = [head]
    for n, vals in values.items():
        rows.append([(str(n), sh._TEXT), ("Invented.", sh._TEXT)] + [(v, sh._OPEN) for v in vals])
    xlsx.write_workbook(path, xlsx.Sheet(name="Hand sheet", rows=rows))
    return path


def test_alpha_nominal():
    assert sh.alpha_nominal([(1, 1), (1, 1), (0, 0), (0, 1)]) == pytest.approx(0.5333, abs=1e-4)
    assert sh.alpha_nominal([(1, 1), (0, 0)]) == 1.0
    assert sh.alpha_nominal([(1, 1), (1, 1)]) is None
    assert sh.alpha_nominal([]) is None


def test_the_check_reports_alpha_and_row_numbers_only(tmp_path):
    key = {
        1: {"message_id": "a", "info_index": "0", "unit": "wea90"},
        2: {"message_id": "b", "info_index": "0", "unit": "wea90"},
        3: {"message_id": "c", "info_index": "0", "unit": "full"},
    }
    codes = [
        code("a", "wea90", hazard=True, guidance=True),
        code("b", "wea90", hazard=False),
        code("c", "full", hazard=True),
    ]
    path = filled_sheet(
        tmp_path / "f.xlsx",
        {1: ["yes", "no", "no", "yes", "no", "no"], 2: ["yes"] + ["no"] * 5, 3: ["yes"] + [""] * 5},
    )
    filled = sh.read_filled(path)
    assert filled[3]["guidance"] is None
    r = sh.check(filled, key, codes)
    assert r["codes"]["hazard"]["rows_that_differ"] == [2]
    assert r["codes"]["hazard"]["rows_coded"] == 3
    assert r["codes"]["guidance"]["rows_coded"] == 2
    assert r["codes"]["guidance"]["alpha"] == 1.0 and r["codes"]["guidance"]["passes"]
    with pytest.raises(SystemExit, match="no codes in the codes table"):
        sh.check(filled, {**key, 4: {"message_id": "z", "info_index": "0", "unit": "x"}}, codes)


def test_a_filled_sheet_with_a_wrong_value_or_column_is_refused(tmp_path):
    bad = filled_sheet(tmp_path / "b.xlsx", {1: ["maybe"] + ["no"] * 5})
    with pytest.raises(SystemExit, match="other than yes or no"):
        sh.read_filled(bad)
    rows = [[("Row", sh._HEAD), ("Text", sh._HEAD)]]
    xlsx.write_workbook(tmp_path / "c.xlsx", xlsx.Sheet(name="Hand sheet", rows=rows))
    with pytest.raises(SystemExit, match="is missing"):
        sh.read_filled(tmp_path / "c.xlsx")


def test_periods_take_their_share_and_lend_rows_when_short():
    assert sh._allocate_shares({"before_2020": 500, "2020_on": 900}, 100) == {
        "before_2020": 40,
        "2020_on": 60,
    }
    assert sh._allocate_shares({"before_2020": 10, "2020_on": 900}, 100) == {
        "before_2020": 10,
        "2020_on": 90,
    }
