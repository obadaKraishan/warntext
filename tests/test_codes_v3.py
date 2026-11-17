"""Codebook version 3: each change against version 3 without it, on invented messages only."""

import pytest

from warntext import codes as v2
from warntext import codes_v3 as v3
from warntext.codes import Context


def with_and_without(change, text, field, ctx=None):
    """The field as version 3 codes it, and as version 3 without ``change`` codes it."""
    full = v3.Rules().code_text(text, ctx)[field]
    without = v3.Rules(v3.ALL - {change}).code_text(text, ctx)[field]
    return full, without


#: (change, invented text, field, version 3's answer); without the change it is the opposite.
CASES = [
    ("cut", "Flood Warning for Exville County\nNWS has issued a flood warning.", "location", True),
    (
        "opener_from",
        "Wildfire Warning from Exville County Sheriff's Office: go now",
        "hazard",
        True,
    ),
    ("initials", "MANDATORY EVACUATION in Oak Hills: leave by Elm Road.", "source_named", False),
    ("initials", "DAM FAILURE- EVACUATE NOW", "source_named", False),
    ("bare_fire", "WEA notice for brush fire near Oak Ridge:", "hazard", True),
    (
        "verb_case",
        "Oakdale Fire Evacuation Order lowered to a warning for Elm Road.",
        "hazard",
        True,
    ),
    (
        "signature",
        "Landline phones are down - Cell phones to 911 still work",
        "source_named",
        False,
    ),
    ("signature", "ROADS ARE ICY - DRIVE SLOWLY", "source_named", False),
    ("stamp", "EXSD 6/1 2:10 PM: Oak Road closed at Elm St.", "source_named", True),
    ("place_acronym", "Sampleton County OES", "source_named", True),
    ("place_acronym", "Sampleton County OES", "location", False),
    ("lines", "Flood Warning\nNWS; Exville area\nMove to higher ground", "source_named", True),
    ("by", "Siren test by Sampleton Co EMA at noon.", "source_named", True),
    ("start_org", "EXC Health Officer has an order asking for supplies.", "source_named", True),
    ("start_org", "Exville sheriff issuing evacuations north of Oak Road", "source_named", True),
    ("bare_place", "Exville: boil water before use on Oak Road.", "source_named", True),
    ("message_opener", "Sampleton Boro message. Leave Oak Road now.", "source_named", True),
    ("alert_system", "Alert Exville - water main break reported", "source_named", True),
    ("traffic_alone", "Obey all traffic laws and drive with care.", "hazard", False),
    ("hazard_words", "Lake water is rising near Oak Road.", "hazard", True),
    ("hazard_words", "Planned demolition of the old mill at noon.", "hazard", True),
    ("hazard_words", "LE activity near Elm St. Stay inside.", "hazard", True),
    ("caused", "Curfew for Exville Parish due to Tropical Storm Exia.", "hazard_description", True),
    ("extent", "Dam failure is imminent below Oak Lake.", "hazard_description", True),
    ("extent", "Phone outage in various areas of Exville.", "hazard_description", True),
    (
        "extent",
        "Potential for a debris flow to affect homes near Oak Creek.",
        "hazard_description",
        True,
    ),
    ("on_roads", "Exville is seeing flooding over roadways tonight.", "hazard_description", True),
    ("caution", "Caution with travel tonight due to ice.", "guidance", True),
    ("verbs", "Disperse from the park now.", "guidance", True),
    ("verbs", "Store water in case of an outage.", "guidance", True),
    ("verbs", "The sheriff is issuing evacuations for Oak Hills.", "guidance", True),
    ("verbs", "Northbound traffic is detoured onto Elm St.", "guidance", True),
    ("now_in_effect", "A warning to leave Oak Hills is now in effect.", "time", True),
    ("about", "The siren on Oak Road will sound in about 30 minutes.", "time", True),
    ("about", "Heavy rain throughout the night in Exville.", "time", True),
    ("while", "Avoid Oak Road while crews repair the main.", "time", True),
    ("immediate_help", "If you need immediate assistance, call 911.", "time", False),
    (
        "caps_clauses",
        "BRUSH FIRE IN OAKVILLE AND ELMTON. Visit exville.gov for more.",
        "location",
        True,
    ),
    ("roads", "Avoid I 69 northbound near mile markers 30 to 32.", "location", True),
    ("roads", "Crash at S 4th & Elm. Use another route.", "location", True),
    ("roads", "Full closure on IH35W due to a crash.", "location", True),
    ("not_places", "Test of Wireless Emergency Alerts", "location", False),
    ("not_places", "PHONE OUTAGE IN VARIOUS AREAS", "location", False),
    ("particles", "Brush fire near El Oakito. Leave now.", "location", True),
]


@pytest.mark.parametrize(("change", "text", "field", "answer"), CASES)
def test_each_change_moves_its_code_and_only_with_the_change(change, text, field, answer):
    full, without = with_and_without(change, text, field)
    assert full is answer
    assert without is (not answer)


def test_alert_system_names_and_place_words_are_not_locations():
    ctx = Context(place_words=frozenset({"exville"}))
    full, without = with_and_without(
        "alert_system", "Alert Exville - water main break", "location", ctx
    )
    assert (full, without) == (False, True)
    ctx = Context(place_words=frozenset({"winter", "weather"}))
    text = "Winter weather advisory: 2 inches of snow tonight."
    assert with_and_without("place_words", text, "location", ctx) == (False, True)
    # A message title is no alert system's name.
    assert v3.Rules().code_text("Travel Alert: I-20 closed.")["source_named"] is False


def test_what_waits_for_an_answer_keeps_version_2s_reading():
    text = "Curfew in effect from 10 PM tonight."
    assert v3.Rules().code_text(text)["hazard"] is True
    assert v3.Rules(v3.ALL | {"orders"}).code_text(text)["hazard"] is False
    # A police department named only as the actor is not read as the speaker.
    assert (
        v3.Rules().code_text("Exville Police are at the scene on Oak Road.")["source_named"]
        is v2.code_text("Exville Police are at the scene on Oak Road.")["source_named"]
    )
    assert {n for n, _, _ in v3.HELD}.isdisjoint(v3.ALL)


def test_the_language_check_finds_other_languages_and_keeps_english():
    assert v3.language("Toque de queda en efecto. Quedese en casa. Curfew in effect 7PM-5AM.") == (
        "spanish_text"
    )
    assert not v2.looks_spanish("Toque de queda en efecto. Quedese en casa. Curfew in effect.")
    assert v3.language(
        "Veuillez quitter la zone maintenant. Le feu est proche de votre maison."
    ) == ("other_language")
    assert v3.language("Xin vui lòng di tản khỏi khu vực này ngay bây giờ.") == "other_language"
    assert v3.language("請立即撤離該地區") == "other_language"
    english = (
        "Evacuate now from Calle Real and El Camino. Leave the area and go to the shelter at the "
        "school. En espanol: exville.gov/es"
    )
    assert v3.language(english) is None
    assert v3.language("Yolo") is None and v3.language("") is None
    unit = v3.code_unit("wea90", "Veuillez quitter la zone maintenant, le feu est proche.")
    assert (unit.coded, unit.not_coded_reason) == (False, "other_language")
    assert v3.code_unit("wea90", "Toque de queda en efecto. Quedese en casa.").not_coded_reason == (
        "spanish_text"
    )
    assert v3.code_unit("wea90", "  ").not_coded_reason == "empty"
    assert v3.code_unit("wea90", "Leave now.", spanish=True).not_coded_reason == "spanish_block"
    plain = v3.Rules(v3.ALL - {"lang"}).code_unit("wea90", "Toque de queda en efecto. Quedese.")
    assert plain.coded


TEXTS = [text for _, text, _, _ in CASES] + [
    "Gas leak on Oak Road. Avoid the area.",
    "Sampleton County OEM: boil water before use.",
    "Police activity near Oak Road. Avoid the area.",
    "This is the Exville Fire Department. A brush fire is moving east. Leave Zone B now.",
    "LEE FIRE: Grass fire on Elm Road, 20 acres, spreading. Evacuate until further notice.",
    "SCSO: shelter in place at 100 block of Main St. Updates at exville.gov.",
]


@pytest.mark.parametrize("text", TEXTS)
def test_version_3_with_no_change_is_version_2(text):
    ctx = Context(organization="Exville County", place_words=frozenset({"exville", "oakdale"}))
    assert v3.Rules(()).code_text(text, ctx) == v2.code_text(text, ctx)
    assert v3.Rules(()).code_unit("full", text, ctx) == v2.code_unit("full", text, ctx)


def test_the_changes_are_named_once_and_unknown_ones_are_refused():
    names = [n for n, _, _ in v3.CHANGES]
    assert len(names) == len(set(names)) and v3.CODEBOOK_VERSION == "3"
    assert {f for _, f, _ in v3.CHANGES} <= {
        "language",
        "source",
        "hazard",
        "hazard_description",
        "guidance",
        "time",
        "location",
    }
    with pytest.raises(ValueError, match="Unknown changes"):
        v3.Rules({"no_such_change"})
    assert v3.code_text("Gas leak on Oak Road.")["hazard"] is True
    assert set(v3.code_text("Leave now.")) == set(v2.CODE_FIELDS)
