"""The privacy rules on invented messages (phone numbers in the 555-01xx fiction range)."""

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
    ]
    kept, text, dropped = privacy.split_parameters(params)
    assert [p.name for p in kept] == [
        "EAS-ORG",
        "BLOCKCHANNEL",
        "timezone",
        "WEAHandling",
        "EASHeader",
    ]
    assert [p.name for p in text] == ["CMAMtext", "EASText"]
    assert dropped == ["UserName", "Email", "AssignedAddress", "EAS-ORG (unexpected value)"]
    # a dropped value never comes back from the split
    assert all("invented" not in d for d in dropped)


def test_allowed_name_reads_case_variants():
    assert privacy.allowed_name("TimeZone") == "timezone"
    assert privacy.allowed_name("UserName") is None


def test_message_texts_cover_the_dropped_fields():
    m = msg(contact="Invented contact", note="Invented note")
    texts = privacy.message_texts(m)
    assert "Invented contact" in texts
    assert "Invented note" in texts
