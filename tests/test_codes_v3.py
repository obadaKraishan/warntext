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
    # The answers to the nine open definitions (codebook section 9).
    ("orders", "A curfew is in effect from 9 PM to 6 AM.", "hazard", False),
    ("orders", "Burn ban in Exville County.", "hazard", False),
    ("orders", "Boil water notice for Exville until further notice.", "hazard", False),
    ("orders", "Citywide curfew tonight from 9 PM.", "guidance", True),
    ("kind_label", "The police event on Oak Road is over.", "hazard", True),
    ("kind_label", "Traffic emergency on Elm Road.", "hazard", True),
    ("kind_label", "Medical emergency at the Exville fairgrounds.", "hazard", True),
    ("message_label", "Health advisory for Exville residents.", "hazard", False),
    ("shut_off", "Gas will be shut off on Oak Road shortly; repairs will follow.", "hazard", True),
    (
        "responders",
        "Suspicious package on Elm Street was safely removed.",
        "hazard_description",
        False,
    ),
    (
        "still_works",
        "Landline 911 is down in Exville. Cell phones can still call 911.",
        "guidance",
        False,
    ),
    (
        "order_changed",
        "The evacuation order for Oak Hills was lowered to a warning at 3 PM.",
        "time",
        False,
    ),
    (
        "order_changed",
        "The order for Oak Road is now a warning; crews are still at work.",
        "time",
        False,
    ),
    ("time_word", "Heavy rain will continue over Exville.", "time", False),
    ("time_word", "Storms are expected to move into Exville.", "time", False),
    ("hazard_names", "Residents near the Oak Fire must leave now.", "location", False),
    ("named_landmark", "Stay away from the river tonight.", "location", False),
    ("named_landmark", "Shelter open at the high school.", "location", False),
    ("district_name", "Crane work in progress Downtown Exville. Stay away.", "location", True),
    ("dotted", "Due to T.S. Exia, parish curfew in effect tonight.", "hazard_description", True),
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


#: The answers to the nine open definitions (codebook section 9), with their invented examples
#: and a few more of the same kinds: (answer, field, invented text, the answer it settles).
ANSWERS = [
    (1, "time", "The evacuation order for Oak Hills was lowered to a warning at 3 PM.", False),
    (
        1,
        "time",
        "The boil water notice for Exville is no longer in effect as of 6 PM Friday.",
        False,
    ),
    (2, "time", "The gas leak on Elm Street is over. You may go home.", False),
    (3, "time", "A smoke advisory remains in place for Exville.", False),
    (3, "time", "Bridge work in progress on Oak Road.", False),
    (3, "time", "Oak Road is closed until further notice.", True),
    (3, "time", "Shelter in place until the order is lifted.", True),
    (4, "hazard", "The police event on Oak Road is over.", True),
    (4, "hazard", "Police activity on Oak Road. Avoid the area.", True),
    (4, "hazard", "Traffic emergency on Elm Road.", True),
    (4, "hazard", "Hazmat incident on Route 9.", True),
    (4, "hazard", "An incident on Route 9 has been cleared.", False),
    (4, "hazard", "An emergency in Exville. Stay inside.", False),
    (4, "hazard", "A situation downtown. Avoid the area.", False),
    (4, "hazard", "Traffic alert for Elm Road.", False),
    (5, "hazard", "Gas will be shut off on Oak Road shortly; repairs will follow.", True),
    (
        5,
        "hazard_description",
        "Gas will be shut off on Oak Road shortly; repairs will follow.",
        False,
    ),
    (5, "hazard_description", "Brush fire near Oak Road. Crews are on scene.", False),
    (6, "source_named", "Exville Police are at the scene on Oak Road.", False),
    (
        6,
        "source_named",
        "Exville County will offer free flu shots at the fairgrounds on Saturday.",
        False,
    ),
    (6, "source_named", "Exville Police ask residents to stay inside.", True),
    (7, "guidance", "Landline 911 is down in Exville. Cell phones can still reach 911.", False),
    (7, "guidance", "Landline 911 is down in Exville. Use a cell phone to call 911.", True),
    (8, "location", "Some Oak Fire areas must leave now.", False),
    (8, "location", "All residents must leave downtown now.", False),
    (8, "location", "All residents must leave downtown Exville now.", True),
    (9, "hazard", "Burn ban because of extreme fire danger.", True),
    (9, "hazard", "Stay-at-home order for Exville County.", False),
    (9, "hazard", "Water main break on Oak Road. Boil water before use.", True),
    (9, "hazard", "Oak Road closed at Elm St.", True),
    (9, "guidance", "Burn ban in Exville County.", True),
    (9, "guidance", "Stay-at-home order for Exville County.", True),
]


@pytest.mark.parametrize(("answer", "field", "text", "settled"), ANSWERS)
def test_version_3_reads_each_answer_as_settled(answer, field, text, settled):
    assert v3.Rules().code_text(text)[field] is settled, (answer, text)


def test_the_senders_own_name_is_the_source_only_where_written_as_the_speaker():
    county, police = (
        Context(organization="Exville County"),
        Context(organization="Exville Police Department"),
    )
    acting = [
        ("Exville County will offer free flu shots at the fairgrounds on Saturday.", county),
        ("Flooding on Oak Road in Exville County. Avoid the area.", county),
        ("Crash on Oak Road. EPD is on scene.", police),
    ]
    for text, ctx in acting:
        assert with_and_without("own_name", text, "source_named", ctx) == (False, True), text
    speaking = [
        ("Exville County: boil water before use.", county),
        ("Message from Exville County: boil water before use.", county),
        ("Exville County asks residents to conserve water.", county),
        ("Flooding on Oak Road. Avoid the area. - Exville County", county),
        ("Crash on Oak Road. EPD advises drivers to avoid it.", police),
        ("Crash on Oak Road.\nEPD", police),
    ]
    for text, ctx in speaking:
        assert v3.Rules().code_text(text, ctx)["source_named"] is True, text
    assert v3.HELD == ()


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
