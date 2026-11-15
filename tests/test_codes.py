"""The rule-based content codes (codebook version 1), on invented alert texts only.

Every text here is invented for the test: no place, agency or road named is real.
"""

import pytest

from warntext import codes as cd

ORG = cd.Context(organization="Sampleton County Office of Emergency Management")


def code(text, ctx=None):
    return cd.code_text(text, ctx)


# --- language ----------------------------------------------------------------------------


def test_spanish_units_are_flagged_not_coded():
    assert cd.looks_spanish("Alerta: evacúe la zona ahora. Información en el sitio del condado.")
    assert not cd.looks_spanish("Evacuate the area now. Information at the county website.")
    u = cd.code_unit("wea90", "Evacúe la zona ahora por el incendio en el condado.")
    assert (u.coded, u.not_coded_reason, u.values) == (False, "spanish_text", {})
    assert cd.code_unit("wea90", "Leave now", spanish=True).not_coded_reason == "spanish_block"
    assert cd.code_unit("wea90", "  ").not_coded_reason == "empty"
    assert cd.code_unit("wea90", "Leave the area now.").coded


# --- source ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Sampleton County OEM: Boil water before drinking.",
        "Brush fire near Oak Road. Leave now. -Sampleton PD",
        "The Sampleton Fire Department asks residents to avoid the area.",
        "Earthquake detected. Drop, cover, hold on. -Example ShakeAlert",
        "Sampleton County: shelter in place now.",
    ],
)
def test_source_is_found(text):
    assert code(text)["source_named"]


@pytest.mark.parametrize(
    "text",
    [
        "Police activity near Oak Road. Avoid the area.",  # "police" alone names no one
        "Evacuation Order: leave now.",  # an opener without a jurisdiction or agency
        "State of Emergency: stay home.",
    ],
)
def test_no_source_without_a_named_organization(text):
    assert not code(text)["source_named"]


def test_the_authority_name_and_its_initials_count_as_source():
    assert code("Message from the Sampleton County Office of Emergency Management.", ORG)[
        "source_named"
    ]
    assert code("SCOEM: shelter in place now.", ORG)["source_named"]
    assert code("Sampleton Emergency Management: leave now.", ORG)["source_named"]


def test_the_source_is_blanked_before_other_codes():
    # "Fire Department" is the source, not a fire; "Sampleton County" is in the source.
    c = code("Sampleton County Fire Department: all clear.")
    assert c["source_named"] and not c["hazard"] and not c["loc_boundary"]


# --- hazard and category -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("A brush fire is spreading near Oak Road.", "wildfire"),
        ("Structure fire and explosion at the plant.", "technological"),
        ("Gas leak reported. Leave the building.", "technological"),
        ("Active shooter reported. Lock doors.", "law_enforcement"),
        ("A suspect is armed. Stay inside.", "law_enforcement"),
        ("Covid-19 testing site opens today.", "public_health"),
        ("911 outage in the county. Call 555-0100 instead.", "public_safety"),
        ("Boil water notice for the city.", "public_safety"),
        ("Flash flood on Oak Creek. Move to higher ground.", "atmospheric"),
        ("Earthquake! Drop, cover, hold on.", "geophysical"),
        ("Please read this invented message.", "other_unknown"),
    ],
)
def test_hazard_category_from_words(text, category):
    assert code(text)["hazard_category"] == category


def test_category_falls_back_to_the_event_code_then_other():
    ctx = cd.Context(event_codes=("HMW",))
    c = code("Shelter in place now.", ctx)
    assert (c["hazard"], c["hazard_category"], c["hazard_category_source"]) == (
        False,
        "technological",
        "code",
    )
    assert code("Shelter in place now.", cd.Context(event_codes=("FFW",)))["hazard_category"] == (
        "atmospheric"
    )
    assert code("Shelter in place now.")["hazard_category_source"] == "none"


def test_if_you_suspect_is_not_a_suspect():
    assert code("If you suspect a gas leak, leave.")["hazard_category"] == "technological"


def test_hazard_description_characteristics_and_impacts():
    c = code("Fast-moving brush fire, 200 acres. Roads are closed.")
    assert c["hazard_characteristics"] and c["hazard_impacts"] and c["hazard_description"]
    c = code("Brush fire near Oak Road.")
    assert not c["hazard_description"]


# --- guidance ----------------------------------------------------------------------------


def test_guidance_actions_and_their_count():
    assert cd.guidance_actions("Drop, cover, hold on. Protect yourself.") == [
        "drop",
        "cover",
        "hold on",
        "protect",
    ]
    assert cd.guidance_actions("Lock doors and stay inside.") == ["lock", "stay"]
    assert cd.guidance_actions("Residents are urged to evacuate now.") == ["evacuate"]
    assert cd.guidance_actions("If you are near Oak Creek, move to higher ground.") == ["move"]
    assert cd.guidance_actions("Please don't drive through water.") == ["do not drive"]
    assert cd.guidance_actions("Evacuate now. Evacuate immediately.") == ["evacuate"]


def test_guidance_nouns_count_and_shelter_needs_its_action_form():
    assert cd.guidance_actions("Evacuation order for Zone A.") == ["evacuation order"]
    assert cd.guidance_actions("Shelter in place now.") == ["shelter"]
    assert cd.guidance_actions("Shelter is open at the invented school.") == []
    assert cd.guidance_actions("The fire is close to homes.") == []


def test_information_seeking_is_kept_apart_from_protective_action():
    c = code("Visit example.gov for updates.")
    assert c["guidance"] and c["guidance_information"] and not c["guidance_protective"]
    c = code("Leave now and check example.gov.")
    assert c["guidance_protective"] and c["guidance_information"] and c["n_actions"] == 2


# --- time --------------------------------------------------------------------------------


def test_time_kinds():
    assert code("Leave now.")["time_action"]
    assert code("Shelter in place until 5 PM.")["time_action"]
    assert not code("Shelter in place until 5 PM.")["time_expiry"]
    assert code("Boil water notice until further notice.")["time_expiry"]
    assert code("The road is closed until 6 AM.")["time_expiry"]
    assert code("Heavy rain expected to arrive tonight.")["time_impact"]
    assert code("Smoke will continue through the weekend.")["time_impact"]
    c = code("The shelter is now open. All clear.")
    assert not c["time"]  # "now open" is not a time to act
    assert not code("Avoid the immediate area.")["time_action"]


# --- location ----------------------------------------------------------------------------


def test_location_kinds():
    assert code("Fire in the northern part of Sampleton County.")["loc_boundary"]
    assert code("Crash on Oak Road. Avoid.")["loc_road"]
    assert code("Crash on I-55 at exit 12.")["loc_road"]
    assert code("CRASH NEAR OAK ST. AVOID.")["loc_road"]
    assert not code("Avoid the roads. Stay home.")["loc_road"]
    assert not code("Do not drive through water.")["loc_road"]
    assert code("Gas leak near Sampleton High School.")["loc_landmark"]
    assert code("Evacuate zones SAM-E012 and SAM-E013.")["loc_zone"]
    assert code("Evacuate Zone A now.")["loc_zone"]
    assert not code("Covid-19 vaccines are available.")["loc_zone"]
    c = code("Police activity in your area. Stay inside.")
    assert not c["location"] and c["loc_vague_or_none"]


def test_place_words_from_area_descriptions():
    words = cd.place_words_of(["Sampleton, TX", "Northern portion of Exampleville"])
    assert words == {"sampleton", "exampleville"}
    ctx = cd.Context(place_words=words)
    assert code("Water main break in Exampleville. Boil water.", ctx)["loc_boundary"]


# --- links, abbreviations, evacuation words, completeness --------------------------------


def test_link_kinds():
    assert cd.link_kinds("See bit.ly/abc or https://www.sampleton.gov/x") == ["shortener", "gov"]
    assert cd.link_kinds("facebook.com/sampleton") == ["social"]
    assert cd.link_kinds("Leave at 5 p.m. today") == []


def test_abbreviations():
    assert cd.abbreviations("Sampleton OEM says avoid Hwy 9 until 5 PM PDT.") >= 3
    assert cd.abbreviations("Leave the area NOW.") == 0  # emphasis, not an acronym
    # all caps: only known forms and agency endings count
    assert cd.abbreviations("LEAVE THE AREA NOW. -SCSO") == 1
    assert code("LEAVE THE AREA NOW. -SCSO")["source_named"]
    assert code("LEAVE THE AREA SO YOU ARE SAFE.")["source_named"] is False


def test_evacuation_wordings():
    e = cd.evacuation_terms("Evacuation Warning for Zone B; Level 2 BE SET. Voluntary evacuation.")
    assert e["evac_warning_order"] and e["evac_levels"] and e["evac_ready_set_go"]
    assert e["evac_voluntary_mandatory"] and not e["evac_pre_evacuation"]
    assert cd.evacuation_terms("Pre-evacuation notice for Oak Creek.")["evac_pre_evacuation"]
    assert not cd.evacuation_terms("Mandatory water restrictions.")["evac_terms"]


def test_completeness_needs_all_five():
    full = "Sampleton County OEM: Brush fire on Oak Road. Evacuate now."
    c = code(full)
    assert (c["hazard"], c["location"], c["time"], c["source_named"], c["guidance"]) == (
        True,
        True,
        True,
        True,
        True,
    )
    assert c["complete"]
    assert not code("Brush fire on Oak Road. Evacuate now.")["complete"]  # no source


def test_codes_never_hold_text():
    c = code("Sampleton County OEM: Brush fire on Oak Road. Evacuate now. bit.ly/x")
    for value in c.values():
        if isinstance(value, str):
            assert value in cd.CATEGORIES or value in ("words", "code", "none")
        if isinstance(value, list):
            assert set(value) <= set(cd.LINK_KINDS)


def test_full_text_joins_the_three_fields():
    assert cd.full_text("Head", None, " Do this. ") == "Head\nDo this."


def test_about_missing_person():
    assert code("Silver Alert for an invented man, last seen near Oak Road.")[
        "about_missing_person"
    ]
    assert code("Have you seen this invented child?")["about_missing_person"]
    assert not code("Missing water service on Oak Road.")["about_missing_person"]
