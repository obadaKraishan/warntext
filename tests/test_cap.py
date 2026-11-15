import pytest

from cap_samples import (
    BLOCKED_PHONES,
    CANCEL_WITHOUT_REFERENCES,
    CAP11,
    EMPTY_ELEMENTS,
    ENTITY_EXPANSION,
    MALFORMED,
    MISSING_FIELDS,
    NS11,
    NS12,
    UPDATE,
    WEA_TWO_LANGUAGES,
    WEATHER_SERVICE,
    WRONG_ROOT,
)
from warntext import cap
from warntext.schema import Pair, Reference


def test_header_fields_are_read_as_given():
    m = cap.parse_xml(WEA_TWO_LANGUAGES, record_id="r1", cog_id=999001)
    assert (m.record_id, m.cog_id, m.xmlns) == ("r1", 999001, NS12)
    assert m.identifier == "EX-0001"
    assert m.sender == "example-county-oem@example.org"
    assert m.sent == "2024-05-01T10:15:00-05:00"
    assert (m.status, m.msg_type, m.scope) == ("Actual", "Alert", "Public")
    assert m.source == "Example County OEM"
    assert m.codes == ("IPAWSv1.0",)
    assert m.references == ()
    assert m.problems == ()
    assert not m.signed


def test_each_language_block_is_kept_with_its_phone_texts():
    m = cap.parse_xml(WEA_TWO_LANGUAGES)
    en, es = m.infos
    assert (en.language, es.language) == ("en-US", "es-US")
    assert en.language_given
    assert en.event == "Civil Emergency Message"
    assert en.event_codes == (Pair(name="SAME", value="CEM"),)
    assert (en.urgency, en.severity, en.certainty) == ("Immediate", "Severe", "Observed")
    assert en.response_types == ("Shelter",)
    assert en.sender_name == "Example County Office of Emergency Management"
    assert en.headline == "Invented test headline"
    assert en.instruction == "Invented instruction to stay indoors."
    assert en.wea_short == "Invented short phone text."
    assert en.wea_long == "Invented long phone text."
    assert es.wea_short == "Texto corto inventado."
    assert es.wea_long is None


def test_areas_geocodes_polygons_and_resources():
    en = cap.parse_xml(WEA_TWO_LANGUAGES).infos[0]
    (area,) = en.areas
    assert area.description == "Example County"
    assert area.polygons == ("30.0,-97.0 30.1,-97.0 30.1,-97.1 30.0,-97.0",)
    assert area.geocodes == (Pair(name="SAME", value="099001"),)
    (res,) = en.resources
    assert res.description == "EAS Broadcast Content"
    assert res.size == 1234
    assert res.has_embedded_content
    assert "derefUri" not in res.model_dump()


def test_channels_from_parameters():
    ch = cap.parse_xml(WEA_TWO_LANGUAGES).channels
    assert (ch.wea, ch.eas, ch.nwem, ch.public) == (True, True, True, True)
    assert ch.blocked == ()


def test_blockchannel_turns_channels_off():
    ch = cap.parse_xml(BLOCKED_PHONES).channels
    assert ch.blocked == ("CMAS", "PUBLIC")
    assert not ch.wea
    assert not ch.public
    assert ch.eas


def test_weather_service_message_is_eas_only_and_signed():
    m = cap.parse_xml(WEATHER_SERVICE)
    assert m.signed
    (info,) = m.infos
    assert info.language == "en-US"
    assert not info.language_given
    assert info.areas[0].geocodes == (Pair(name="UGC", value="XXZ001"),)
    assert (m.channels.wea, m.channels.eas, m.channels.nwem) == (False, True, False)
    assert "missing source" not in m.problems


def test_update_references_are_split_and_a_broken_one_is_counted():
    m = cap.parse_xml(UPDATE)
    assert m.msg_type == "Update"
    assert m.references == (
        Reference(
            sender="example-county-oem@example.org",
            identifier="EX-0000",
            sent="2024-05-01T09:00:00-05:00",
        ),
        Reference(
            sender="example-county-oem@example.org",
            identifier="EX-0001a",
            sent="2024-05-01T09:30:00-05:00",
        ),
    )
    assert m.references_unparsed == ("broken-entry",)
    assert m.incidents == ("INC-1", "INC-2")
    assert "1 reference(s) not in sender,identifier,sent form" in m.problems


def test_cancel_without_references_is_a_problem():
    assert "Cancel without references" in cap.parse_xml(CANCEL_WITHOUT_REFERENCES).problems


def test_cap11_reads_the_same_and_keeps_its_namespace():
    m = cap.parse_xml(CAP11)
    assert m.xmlns == NS11
    assert m.infos[0].language == "es-US"


def test_missing_fields_are_listed_by_name():
    m = cap.parse_xml(MISSING_FIELDS)
    assert m.problems == (
        "missing sender",
        "missing sent",
        "missing msgType",
        "missing scope",
        "no info block",
    )


def test_empty_elements_are_empty_strings_not_missing():
    (info,) = cap.parse_xml(EMPTY_ELEMENTS).infos
    assert info.event == ""
    assert info.headline == ""
    assert info.description is None


def test_malformed_xml_is_refused_in_plain_words():
    with pytest.raises(cap.CapParseError, match="record r9: originalMessage is not well-formed"):
        cap.parse_xml(MALFORMED, record_id="r9")


def test_a_document_that_is_not_an_alert_is_refused():
    with pytest.raises(cap.CapParseError, match="root element is <feed>"):
        cap.parse_xml(WRONG_ROOT)


def test_entity_expansion_is_refused():
    with pytest.raises(cap.CapParseError, match="refused for safety"):
        cap.parse_xml(ENTITY_EXPANSION)


def test_parse_record_uses_the_original_message():
    m = cap.parse_record({"id": "r2", "cogId": 5, "originalMessage": WEATHER_SERVICE})
    assert (m.record_id, m.cog_id, m.identifier) == ("r2", 5, "EX-NWS-1")
    m = cap.parse_record({"id": "r3", "cogId": "x", "originalMessage": WEATHER_SERVICE})
    assert m.cog_id is None


def test_parse_record_refuses_an_empty_message():
    with pytest.raises(cap.CapParseError, match="originalMessage is empty"):
        cap.parse_record({"id": "r4", "originalMessage": ""})


def test_parse_references_handles_empty_and_bad_input():
    assert cap.parse_references(None) == ((), ())
    good, bad = cap.parse_references("a,b,c a,,c")
    assert good == (Reference(sender="a", identifier="b", sent="c"),)
    assert bad == ("a,,c",)


def test_models_are_frozen_and_refuse_unknown_fields():
    m = cap.parse_xml(WEATHER_SERVICE)
    with pytest.raises(ValueError):
        m.status = "Test"
    with pytest.raises(ValueError):
        Pair(name="a", value="b", extra="c")


def test_resource_size_that_is_not_a_number_is_none():
    xml = WEA_TWO_LANGUAGES.replace("<size>1234</size>", "<size>big</size>")
    assert cap.parse_xml(xml).infos[0].resources[0].size is None
