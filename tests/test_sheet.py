"""The hand sheet: the draw, the blind workbook, the key and the check, on invented texts."""

import pytest

from warntext import codes as cd
from warntext import codes_v3 as v3
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
    examples = [text for _, _, ex in sh.EDGE_CASES for text, _ in ex]
    assert len(sh.EDGE_CASES) == 15 and len(examples) == 28
    # The nine answers each come with one invented yes and one invented no.
    for _, _, ex in sh.EDGE_CASES[6:]:
        assert sorted(a.split(":")[0] for _, a in ex) == ["no", "yes"]
    assert all(text in cells for text in examples)
    assert all(f"{shows}." in cells for _, shows, _ in sh.EDGE_CASES)
    guide = paths["guide"].read_text(encoding="utf-8")
    assert guide.splitlines()[0] == "Judge only the words in the text. About a minute per row."
    assert all(d in guide for _, d, _, _ in sh.DEFINITIONS)
    # The settled definitions, word for word: version 3 adds the nine answers to four of them.
    assert sh.DEFINITIONS[2][1].endswith('(an opener such as "City of X:", or "from X County").')
    assert "not the source" in sh.DEFINITIONS[2][1] and "names no threat" in sh.DEFINITIONS[0][1]
    assert '"until lifted"' in sh.DEFINITIONS[4][1] and '"Oak Fire areas"' in sh.DEFINITIONS[5][1]
    assert sh.DEFINITIONS[1] == sh.DEFINITIONS_V2[1] and sh.DEFINITIONS[3] == sh.DEFINITIONS_V2[3]
    assert sh.EDGE_CASES[:6] == sh.EDGE_CASES_V2
    assert sh.DEFINITIONS[3][1].startswith("Any instruction or prohibition to the public, in any")
    assert sh.DEFINITIONS[1][1].endswith("what it can cause. No named hazard, no description.")
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


def test_the_check_counts_blanks_gives_yes_shares_directions_and_a_seeded_interval(tmp_path):
    key = {n: {"message_id": f"m{n}", "info_index": "0", "unit": "wea90"} for n in range(1, 7)}
    # The rules: hazard yes on rows 1 to 3; the person: yes on 1, 2 and 4, blank on 6.
    codes = [code(f"m{n}", "wea90", hazard=n <= 3) for n in range(1, 7)]
    answers = {n: [("yes" if n in (1, 2, 4) else "no")] + ["no"] * 5 for n in range(1, 6)}
    answers[6] = [""] + ["no"] * 5
    filled = sh.read_filled(filled_sheet(tmp_path / "f.xlsx", answers))
    r = sh.check(filled, key, codes, resamples=200, seed=4)
    h = r["codes"]["hazard"]
    # A blank answer is left out and counted, never read as "no" (it would agree with the rules).
    assert h["rows_blank"] == 1 and h["rows_coded"] == 5 and h["rows_not_coded"] == 0
    assert r["codes"]["guidance"]["rows_blank"] == 0
    assert h["person_yes_rules_no"] == 1 and h["person_no_rules_yes"] == 1
    assert h["rows_that_differ"] == [3, 4] and h["agreement"] == 0.6
    assert h["share_yes_person"] == 0.6 and h["share_yes_rules"] == 0.6
    assert r["bootstrap"] == {"resamples": 200, "seed": 4}
    assert h["interval"]["resamples"] == 200
    assert h["interval"]["low"] <= h["alpha"] <= h["interval"]["high"]
    assert sh.check(filled, key, codes, resamples=200, seed=4) == r  # the same seed, the same
    # Every value the same on both sides: no alpha, no interval, shares still given.
    same = sh.check(filled, key, [code(f"m{n}", "wea90") for n in range(1, 7)], resamples=20)
    assert same["codes"]["guidance"]["alpha"] is None
    assert same["codes"]["guidance"]["interval"]["low"] is None
    assert same["codes"]["guidance"]["share_yes_person"] == 0.0


def test_a_unit_the_rules_do_not_code_is_left_out_of_every_score_and_counted(tmp_path):
    key = {n: {"message_id": f"m{n}", "info_index": "0", "unit": "wea90"} for n in range(1, 5)}
    codes = [code(f"m{n}", "wea90", hazard=n <= 2) for n in range(1, 4)]
    codes.append(
        code(
            "m4",
            "wea90",
            coded=False,
            not_coded_reason="spanish_text",
            **{f: None for f in CODE_FIELDS},
        )
    )
    path = filled_sheet(
        tmp_path / "f.xlsx",
        {1: ["yes"] + ["no"] * 5, 2: ["yes"] + ["no"] * 5, 3: ["no"] * 6, 4: ["no"] * 6},
    )
    r = sh.check(sh.read_filled(path), key, codes)
    assert r["not_coded"] == {"rows": [4], "reasons": {"spanish_text": 1}}
    h = r["codes"]["hazard"]
    # Row 4 is neither a "no" of the rules (which would count as agreement) nor a difference.
    assert h["rows_coded"] == 3 and h["rows_not_coded"] == 1 and h["alpha"] == 1.0
    assert 4 not in h["rows_that_differ"] and sum(h["table"].values()) == 3
    rules = sh.rules_by_row(key, codes)
    assert rules[4] == dict.fromkeys(CODE_FIELDS) and rules[1]["hazard"] is True
    merged = {n: {**dict.fromkeys(CODE_FIELDS, False), "hazard": n <= 2} for n in range(1, 5)}
    merged[4]["hazard"] = True
    out = sh.check_consolidated(merged, key, codes)
    assert out["codes"]["hazard"]["rows_coded"] == 3 and out["codes"]["hazard"]["alpha"] == 1.0
    second_key = {n: {"earlier_row": str(n)} for n in range(1, 5)}
    rep = sh.repeat_check(merged, merged, second_key, rules)
    assert rep["codes"]["hazard"]["rows"] == 4 and rep["codes"]["hazard"]["rules_not_coded"] == 1
    assert rep["codes"]["hazard"]["first_agreed_with_rules"] == 3


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


def test_the_guide_in_docs_says_what_the_workbook_says():
    from pathlib import Path

    guide = (Path(__file__).parents[1] / "docs" / "hand-sheet-guide.md").read_text(encoding="utf-8")
    assert guide.splitlines()[0] == sh.GUIDE_FIRST_LINE
    for heading, definition, yes, no in sh.DEFINITIONS:
        assert f'| **{heading}** | {definition} | "{yes}" | "{no}" |' in guide
    for _, shows, examples in sh.EDGE_CASES:
        assert f"**{shows}.**" in guide
        for text, answer in examples:
            assert f'"{text}" {answer}' in guide


def test_every_invented_example_is_coded_by_version_2_as_version_2s_guide_says():
    field = dict(sh.CODES)
    for heading, _, yes, no in sh.DEFINITIONS_V2:
        assert cd.code_text(yes)[field[heading]], yes
        assert not cd.code_text(no)[field[heading]], no
    for column, _, examples in sh.EDGE_CASES_V2:
        for text, answer in examples:
            assert cd.code_text(text)[field[column]] is answer.startswith("yes: "), text
    # What the answers say in passing about another column.
    said = {
        "Updates at sampletoncounty.gov.": {"guidance": True},
        "No burning in Sampleton County until further notice.": {"time": True, "location": True},
        "Oak Road closed at Elm St.": {"hazard": True},
        "Sampleton County: boil water before use.": {"source_named": True},
    }
    for text, want in said.items():
        got = cd.code_text(text)
        assert {k: got[k] for k in want} == want, text


def test_every_invented_example_is_coded_by_version_3_as_the_guide_says():
    field = dict(sh.CODES)
    for heading, _, yes, no in sh.DEFINITIONS:
        assert v3.code_text(yes)[field[heading]], yes
        assert not v3.code_text(no)[field[heading]], no
    for column, _, examples in sh.EDGE_CASES:
        for text, answer in examples:
            assert v3.code_text(text)[field[column]] is answer.startswith("yes: "), text
    # What the answers say in passing about another column.
    said = {
        "Updates at sampletoncounty.gov.": {"guidance": True},
        "No burning in Sampleton County until further notice.": {"time": True, "location": True},
        "Oak Road closed at Elm St.": {"hazard": True},
        "Sampleton County: boil water before use.": {"source_named": True},
        "Gas will be shut off on Oak Road shortly; repairs will follow.": {"hazard": True},
        "A curfew is in effect from 9 PM to 6 AM.": {"guidance": True},
    }
    for text, want in said.items():
        got = v3.code_text(text)
        assert {k: got[k] for k in want} == want, text


def test_the_two_known_misses_of_version_2_stay_as_frozen():
    # The settled definitions say a place written only as the speaker is not a location, and a
    # promised update is not time, with or without its hour. Version 2 is frozen with two
    # narrow misses of them (codebook 2.2 and 2.3); a later version would fix them and flip
    # these asserts.
    assert cd.code_text("City of Sampleton: boil water before use.")["location"]
    assert cd.code_text("Water main break on Oak Road. Next update at 5 PM.")["time"]
    assert not cd.code_text("Water main break on Oak Road. An update will follow.")["time"]
    assert not cd.code_text("Sampleton County: boil water before use.")["location"]


def test_a_repeat_keeps_every_differing_row_adds_fillers_and_reorders():
    order = sh.repeat_order(keep=[3, 7, 9], others=range(1, 21), fillers=5, seed=11)
    assert len(order) == 8 and len(set(order)) == 8
    assert {3, 7, 9} <= set(order)
    assert order == sh.repeat_order([9, 3, 7], range(1, 21), 5, 11)  # seeded
    assert order != sorted(order)
    assert sh.repeat_order([3, 7, 9], range(1, 21), 5, 12) != order
    # A recheck copy is a repeat with no kept rows: a seeded subset in a new order.
    assert len(set(sh.repeat_order([], range(1, 101), 30, 4))) == 30
    with pytest.raises(ValueError, match="only 2 other rows"):
        sh.repeat_order([1], [1, 2, 3], fillers=3, seed=1)


def test_a_repeat_reads_the_same_texts_and_keeps_the_earlier_rows_out_of_the_workbook(tmp_path):
    messages, codes, texts = corpus(24)
    chosen = sh.draw(sh.candidates(messages, codes, texts), seed=3, total=6)
    first = sh.write(chosen, tmp_path / "first", "hand_sheet_2")
    key = sh.read_key(first["key"])
    items = sh.items_for_key(key, texts)
    assert [items[n] for n in sorted(items)] == chosen
    assert sh.texts_of_workbook(first["workbook"]) == {n: i.text for n, i in items.items()}
    order = sh.repeat_order([2, 5], set(key) - {2, 5, 6}, fillers=2, seed=8)
    second = sh.write([items[r] for r in order], tmp_path / "second", "pass", earlier_rows=order)
    new_key = sh.read_key(second["key"])
    assert [int(new_key[n]["earlier_row"]) for n in sorted(new_key)] == order
    visible = next(s for s in xlsx.read_workbook(second["workbook"]) if not s.hidden)
    assert [r[0] for _, r in visible.rows[1:]] == [str(n) for n in range(1, 5)]
    assert all(cell == "" for _, r in visible.rows[1:] for cell in r[2:])
    assert "earlier_row" not in {c for _, row in visible.rows for c in row}
    with pytest.raises(ValueError, match="one earlier row number per chosen text"):
        sh.write(chosen, tmp_path / "x", earlier_rows=[1])
    with pytest.raises(SystemExit, match=r"Rows \[1, 2, 3, 4, 5, 6\] of the key have no text"):
        sh.items_for_key(key, [])


def test_bootstrap_alpha_gives_an_interval_and_the_share_at_the_bar():
    pairs = [(True, True)] * 40 + [(False, False)] * 40 + [(True, False)] * 4
    out = sh.bootstrap_alpha(pairs, resamples=300, seed=2)
    assert out["low"] <= sh.alpha_nominal(pairs) <= out["high"]
    assert 0 < out["share_at_bar"] <= 1 and out["no_alpha"] == 0
    assert out == sh.bootstrap_alpha(pairs, resamples=300, seed=2)
    same = sh.bootstrap_alpha([(True, True)] * 5, resamples=10)
    assert same["low"] is None and same["no_alpha"] == 10
    assert sh.bootstrap_alpha([])["resamples"] == 0


def test_the_repeat_check_counts_where_the_second_pass_took_each_answer():
    no = dict.fromkeys(CODE_FIELDS, False)
    rules = {r: {**no, "hazard": True} for r in range(1, 5)}
    first = {r: {**no, "hazard": v} for r, v in {1: True, 2: False, 3: False, 4: True}.items()}
    second_key = {
        1: {"earlier_row": "3"},
        2: {"earlier_row": "1"},
        3: {"earlier_row": "4"},
        4: {"earlier_row": "2"},
    }
    second = {r: {**no, "hazard": v} for r, v in {1: True, 2: False, 3: True, 4: False}.items()}
    out = sh.repeat_check(first, second, second_key, rules)
    h = out["codes"]["hazard"]
    assert (h["first_differed_from_rules"], h["second_stood_by_first"]) == (2, 1)
    assert (h["second_sided_with_rules"], h["first_agreed_with_rules"]) == (1, 2)
    assert h["new_differences"] == 1 and h["passes_differ_rows"] == [1, 2]
    assert h["table"] == {
        "first_no_second_yes": 1,
        "first_yes_second_no": 1,
        "first_yes_second_yes": 1,
        "first_no_second_no": 1,
    }
    assert out["codes"]["time"]["agreement"] == 1 and out["codes"]["time"]["alpha"] is None
    with pytest.raises(SystemExit, match="Row 1 of the repeat"):
        sh.repeat_check(first, {1: {**no, "hazard": None}}, {1: second_key[1]}, rules)


def test_rules_by_row_reads_the_six_codes_for_each_key_row():
    key = {1: {"message_id": "a", "info_index": "0", "unit": "wea90"}}
    got = sh.rules_by_row(key, [code("a", "wea90", hazard=True)])
    assert got == {1: {**dict.fromkeys(CODE_FIELDS, False), "hazard": True}}
    with pytest.raises(SystemExit, match="no codes in the codes table"):
        sh.rules_by_row(key, [])


def test_the_resolution_list_is_blind_and_consolidates_the_answers(tmp_path):
    messages, codes, texts = corpus(24)
    chosen = sh.draw(sh.candidates(messages, codes, texts), seed=3, total=4)
    items = dict(enumerate(chosen, start=1))
    repeat_key = {n: {"earlier_row": str(10 + n)} for n in items}
    entries = sh.resolution_order({"hazard": [1, 3], "time": [3]}, seed=5)
    assert sorted(entries) == [(1, "hazard"), (3, "hazard"), (3, "time")]
    assert entries == sh.resolution_order({"time": [3], "hazard": [3, 1]}, seed=5)
    paths = sh.write_resolution(entries, items, repeat_key, tmp_path, "resolve")
    read = xlsx.read_workbook(paths["workbook"])
    assert [s.name for s in read if not s.hidden] == ["Resolution", "Definitions"]
    rows = read[0].rows
    assert rows[0][1][:6] == ("Row", "Text", "Code", "Definition", "Answer", "Note")
    cells = {c for _, row in rows for c in row}
    assert not cells & {"True", "False", "first", "second", "rules", "11", "13"}
    assert {"Hazard", "Time"} <= cells and sh.DEFINITIONS[4][1] in cells
    key = sh.read_key(paths["key"])
    assert [(int(k["repeat_row"]), k["code"]) for k in key.values()] == entries
    assert {k["earlier_row"] for k in key.values()} == {"11", "13"}
    assert sh.read_resolution(paths["workbook"]) == {1: None, 2: None, 3: None}
    # Filled: yes, no and the third choice; the rest of the first pass stands.
    filled = [
        list(c for c, _ in r) for r in sh.resolution_sheet([(items[r], f) for r, f in entries]).rows
    ]
    for n, answer in zip((1, 2, 3), sh.RESOLVE_CHOICES, strict=True):
        filled[n][4] = answer
    xlsx.write_workbook(
        tmp_path / "f.xlsx", xlsx.Sheet("Resolution", [[(c, sh._TEXT) for c in r] for r in filled])
    )
    answers = sh.read_resolution(tmp_path / "f.xlsx")
    assert list(answers.values()) == [True, False, sh.OPEN]
    first = {r: dict.fromkeys(CODE_FIELDS, False) for r in (11, 12, 13)}
    merged = sh.consolidate(first, answers, key)
    for n, k in key.items():
        assert merged[int(k["earlier_row"])][k["code"]] == answers[n]
    assert merged[12] == first[12]
    with pytest.raises(SystemExit, match="Row 1 of the resolution list has no answer"):
        sh.consolidate(first, {1: None}, key)
    filled[1][4] = "maybe"
    xlsx.write_workbook(
        tmp_path / "g.xlsx", xlsx.Sheet("Resolution", [[(c, sh._TEXT) for c in r] for r in filled])
    )
    with pytest.raises(SystemExit, match="other than the three"):
        sh.read_resolution(tmp_path / "g.xlsx")


def test_consolidated_answers_leave_open_ones_out_of_the_development_figure(tmp_path):
    key = {n: {"message_id": f"m{n}", "info_index": "0", "unit": "wea90"} for n in range(1, 7)}
    codes = [code(f"m{n}", "wea90", hazard=n <= 3) for n in range(1, 7)]
    merged = {n: dict.fromkeys(CODE_FIELDS, False) for n in range(1, 7)}
    for n in (1, 2):
        merged[n]["hazard"] = True
    merged[3]["hazard"] = sh.OPEN
    merged[4]["hazard"] = True
    out = sh.check_consolidated(merged, key, codes)
    h = out["codes"]["hazard"]
    assert out["figure"] == "development" and h["open"] == 1 and h["rows_coded"] == 5
    assert h["rows_that_differ"] == [4] and h["interval"]["resamples"] == 2000
    path = sh.write_consolidated(merged, tmp_path / "c.csv")
    lines = path.read_text().splitlines()
    assert lines[0].split(",")[:2] == ["row", "hazard"] and lines[3].startswith("3,open,no")


def test_sheet_3_opens_its_guide_with_the_days_only_hand_task(tmp_path):
    messages, codes, texts = corpus(24)
    chosen = sh.draw(sh.candidates(messages, codes, texts), seed=3, total=4)
    paths = sh.write(chosen, tmp_path, "hand_sheet_3", first_lines=sh.SHEET_3_FIRST_LINES)
    guide = paths["guide"].read_text(encoding="utf-8").splitlines()
    assert guide[0] == (
        "This sheet is the only hand task of its day. About a minute per row, in two or three "
        "sittings."
    )
    assert guide[1] == "Judge only the words in the text."
    definitions = xlsx.read_workbook(paths["workbook"])[1].rows
    assert [definitions[0][1][0], definitions[1][1][0]] == list(sh.SHEET_3_FIRST_LINES)
    # The rest of the guide is the sheet-2 guide, word for word.
    assert "\n".join(guide[2:]) == "\n".join(sh.guide_text().splitlines()[1:])
