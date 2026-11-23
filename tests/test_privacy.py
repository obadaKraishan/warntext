"""The privacy rules on invented messages (phone numbers in the 555-01xx fiction range)."""

import pytest

from cap_samples import invented
from warntext import cap, privacy
from warntext.schema import Pair


def msg(**kw):
    return cap.parse_xml(invented(**kw))


def test_people_codes_are_always_withheld_even_without_details():
    for code in ("CAE", "MEP", "BLU", "LEW"):
        reason, hits = privacy.withheld(msg(code=code, description="Invented, no details."))
        assert reason == "people_code"
        assert hits == []


def test_a_hazard_message_with_a_personal_detail_is_withheld_by_pattern():
    reason, hits = privacy.withheld(
        msg(code="CEM", description="Invented. Call 555-555-0123 for help.")
    )
    assert reason == "personal_pattern"
    assert hits == ["phone"]
    reason, hits = privacy.withheld(
        msg(code="LAE", headline="Invented", description="Last seen near the invented park.")
    )
    assert (reason, hits) == ("personal_pattern", ["last_seen"])


def test_patterns_are_found_in_phone_texts_and_area_descriptions_too():
    m = msg(code="CEM", parameters=(("CMAMtext", "Invented: plate ABC1234 seen"),))
    assert privacy.withheld(m) == ("personal_pattern", ["plate"])


def test_a_number_in_another_written_form_is_withheld_by_the_pattern_rule():
    m = msg(code="CEM", description="Invented. Call 5555550123 for help.")
    assert privacy.withheld(m) == ("personal_pattern", ["phone_any_form"])
    m = msg(code="CEM", description="Invented.", instruction="Call 555-0123.")
    assert privacy.withheld(m) == ("personal_pattern", ["phone_seven"])


def test_a_description_without_cue_words_is_withheld_and_coarsened():
    m = msg(
        code="LAE",
        headline="Invented: police seek a white male",
        description="Invented: in a red hoodie near the example park.",
    )
    reason, hits = privacy.withheld(m)
    assert (reason, hits) == ("person_described", ["person_described"])
    assert privacy.coarsened(reason, hits, about_missing=False)
    # a detail pattern is named first; the description still coarsens the times
    m = msg(code="LAE", headline="Invented: a white male", description="In a red hoodie; 555-0123.")
    reason, hits = privacy.withheld(m)
    assert reason == "personal_pattern" and "person_described" in hits
    assert privacy.coarsened(reason, hits, about_missing=False)
    assert not privacy.coarsened("personal_pattern", ["phone"], about_missing=False)
    assert privacy.coarsened(None, [], about_missing=True)
    assert privacy.coarsened("people_code", [], about_missing=False)


def test_audience_and_resource_descriptions_are_scanned_too():
    xml = invented(code="CEM", description="Invented.").replace(
        "<category>", "<audience>Invented: call 5555550123</audience><category>"
    )
    assert privacy.withheld(cap.parse_xml(xml)) == ("personal_pattern", ["phone_any_form"])


def test_a_plain_hazard_message_keeps_its_text():
    assert privacy.withheld(msg(code="EVI", description="Invented evacuation order.")) == (
        None,
        [],
    )


def test_the_organization_name_and_contact_do_not_trigger_the_rule():
    m = msg(code="FRW", contact="Invented Desk 555-555-0199", sender_name="Example 555 Agency")
    assert privacy.withheld(m) == (None, [])


def test_parameters_are_split_into_kept_text_and_dropped():
    params = [
        Pair(name="EAS-ORG", value="CIV"),
        Pair(name="BLOCKCHANNEL", value="EAS"),
        Pair(name="TimeZone", value="America/Chicago"),
        Pair(name="WEAHandling", value="Imminent Threat"),
        Pair(name="EASHeader", value="ZCZC-CIV-CEM-048201+0100-1231515-EXAMPLE1-"),
        Pair(name="CMAMtext", value="Invented phone text"),
        Pair(name="EASText", value="Invented broadcast text"),
        Pair(name="UserName", value="invented.user"),
        Pair(name="Email", value="invented@example.org"),
        Pair(name="AssignedAddress", value="invented"),
        Pair(name="EAS-ORG", value="Invented free text"),
        Pair(name="BLOCKCHANNEL", value=" "),
        Pair(name="EAS-STN-ID", value="ABC,1,XY"),
    ]
    kept, text, dropped = privacy.split_parameters(params)
    assert [p.name for p in kept] == [
        "EAS-ORG",
        "BLOCKCHANNEL",
        "timezone",
        "WEAHandling",
        "EASHeader",
        "EAS-STN-ID",
    ]
    assert [p.name for p in text] == ["CMAMtext", "EASText"]
    assert dropped == [
        "UserName",
        "Email",
        "AssignedAddress",
        "EAS-ORG (unexpected value)",
        "BLOCKCHANNEL (empty)",
    ]
    # a dropped value never comes back from the split
    assert all("invented" not in d for d in dropped)


def test_allowed_name_reads_case_variants():
    assert privacy.allowed_name("TimeZone") == "timezone"
    assert privacy.allowed_name("WeaHandling") == "WEAHandling"
    assert privacy.allowed_name("UserName") is None
    assert privacy.is_text_parameter("CmamLongText")
    assert not privacy.is_text_parameter("UserName")


def test_message_texts_cover_the_dropped_fields():
    m = msg(contact="Invented contact", note="Invented note")
    texts = privacy.message_texts(m)
    assert "Invented contact" in texts
    assert "Invented note" in texts


def test_people_times_round_down_to_the_hour():
    from datetime import datetime, timezone

    assert privacy.hour_floor("2024-05-01T10:47:12-05:00") == "2024-05-01T10:00:00-05:00"
    assert privacy.hour_floor("2024-05-01T23:59:59.999Z") == "2024-05-01T23:00:00Z"
    assert privacy.hour_floor("2024-05-01T10:00:00") == "2024-05-01T10:00:00"
    assert privacy.hour_floor("not a time") is None
    assert privacy.hour_floor(None) is None
    t = datetime(2024, 5, 1, 15, 47, 12, 500, tzinfo=timezone.utc)
    assert privacy.hour_floor_utc(t) == datetime(2024, 5, 1, 15, tzinfo=timezone.utc)
    assert privacy.hour_floor_utc(None) is None
    assert privacy.finer_than_hour("2024-05-01T10:47:00-05:00")
    assert privacy.finer_than_hour("2024-05-01T10:00:01Z")
    assert privacy.finer_than_hour("2024-05-01T10:00:00.250Z")
    assert not privacy.finer_than_hour("2024-05-01T10:00:00.000Z")
    assert not privacy.finer_than_hour("2024-05-01T10:00:00-05:00")
    assert privacy.finer_than_hour("tomorrow")
    assert privacy.finer_than_hour(t)
    assert not privacy.finer_than_hour(privacy.hour_floor_utc(t))
    assert not privacy.finer_than_hour(None)


def test_area_codes_keep_the_county_and_eas_headers_the_hour():
    assert privacy.county_only("348201") == "048201"
    assert privacy.county_only("048201") == "048201"
    assert privacy.county_only("TXZ213") == "TXZ213"
    assert privacy.has_part_digit("348201") and not privacy.has_part_digit("048201")
    header = "ZCZC-CIV-CEM-348201-048157+0100-3191547-EXAMPLE1-"
    assert privacy.eas_header_finer(header) == (True, True)
    coarse = privacy.coarsen_eas_header(header)
    assert coarse == "ZCZC-CIV-CEM-048201-048157+0100-3191500-EXAMPLE1-"
    assert privacy.eas_header_finer(coarse) == (False, False)
    assert privacy.coarsen_eas_header("not a header") == "not a header"
    assert privacy.eas_header_finer("not a header") == (False, False)


def test_messages_about_a_missing_person_in_either_language():
    english = cap.parse_xml(invented(description="Silver Alert for an invented man."))
    spanish = cap.parse_xml(
        invented(language="es-US", description="Hombre desaparecido, visto por última vez ayer.")
    )
    plain = cap.parse_xml(invented(description="Missing water service on Oak Road."))
    assert privacy.about_missing_person(english)
    assert privacy.about_missing_person(spanish)
    assert not privacy.about_missing_person(plain)


# --- the removal list ----------------------------------------------------------------------

INVENTED_ID = "0a1b2c3d-0000-4000-8000-00000000abcd"


def test_the_tracked_removal_list_is_empty_and_reads():
    from importlib import resources

    text = resources.files("warntext").joinpath(privacy.REMOVALS_FILE).read_text("utf-8")
    assert text == "record_id,added,request\n"
    assert privacy.load_removals() == frozenset()


def test_a_removal_entry_reads_and_a_bad_one_is_refused():
    head = "record_id,added,request\n"
    ok = privacy.read_removals(head + f"{INVENTED_ID},2026-11-23,issue 7\n")
    assert ok == frozenset({INVENTED_ID})
    bad = {
        "record id must be FEMA's": f"{INVENTED_ID.upper()},2026-11-23,issue 7\n",
        "date it was added": f"{INVENTED_ID},23 Nov 2026,issue 7\n",
        "never by a person's name": f"{INVENTED_ID},2026-11-23,request by a.person@example.org\n",
        "already listed": f"{INVENTED_ID},2026-11-23,issue 7\n{INVENTED_ID},2026-11-24,issue 8\n",
    }
    for message, rows in bad.items():
        with pytest.raises(SystemExit, match=message):
            privacy.read_removals(head + rows)
    with pytest.raises(SystemExit, match="the header must be"):
        privacy.read_removals("id,added\n")


def test_a_message_is_on_the_list_by_any_of_its_copies_record_ids():
    listed = frozenset({INVENTED_ID})
    assert privacy.on_removal_list({"message_id": "x", "record_ids": ["x", INVENTED_ID]}, listed)
    assert privacy.on_removal_list({"message_id": INVENTED_ID}, listed)
    assert not privacy.on_removal_list({"message_id": "x", "record_ids": ["x"]}, listed)
    assert not privacy.on_removal_list({}, listed)
