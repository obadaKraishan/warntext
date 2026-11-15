from dataclasses import dataclass

import pytest

from cap_samples import MALFORMED, UPDATE, WEA_TWO_LANGUAGES, WEATHER_SERVICE, alert
from warntext import profile


@dataclass(frozen=True)
class Line:
    year: int
    kind: str
    skip: int


PEOPLE_ALERT = alert(
    """
<identifier>EX-P1</identifier><sender>example-state-police@example.org</sender>
<sent>2024-06-01T10:00:00-05:00</sent><status>Actual</status><msgType>Alert</msgType>
<scope>Public</scope>
<info><event>Child Abduction Emergency</event>
<eventCode><valueName>SAME</valueName><value>CAE</value></eventCode>
<description>Invented case: a 9-year-old, last seen near an invented park, plate ABC1234.
Call 202-555-0100.</description>
<parameter><valueName>CMAMtext</valueName><value>Invented short text.</value></parameter>
<area><areaDesc>Example State</areaDesc></area></info>
"""
)


def rows():
    records = [
        (Line(2024, "other", 0), {"id": "a", "originalMessage": WEA_TWO_LANGUAGES}),
        (Line(2024, "other", 0), {"id": "b", "originalMessage": WEA_TWO_LANGUAGES}),
        (Line(2024, "other", 0), {"id": "c", "originalMessage": UPDATE}),
        (Line(2024, "other", 14), {"id": "d", "originalMessage": PEOPLE_ALERT}),
        (Line(2015, "nws", 0), {"id": "e", "originalMessage": WEATHER_SERVICE}),
        (Line(2015, "nws", 0), {"id": "f", "originalMessage": MALFORMED}),
    ]
    return profile.build_rows(records, {(2024, "other"): 40, (2015, "nws"): 1000})


def test_weights_are_stratum_size_over_drawn_and_errors_are_kept():
    r = rows()
    assert [x.weight for x in r] == [10, 10, 10, 10, 500, 500]
    assert r[-1].message is None
    assert r[-1].error == "originalMessage is not well-formed XML"


def test_weighted_shares_estimate_the_archive():
    kinds = profile.weighted(rows(), lambda r: r.kind)
    assert kinds["sample_count"] == {"nws": 2, "other": 4}
    assert kinds["estimated_records"] == {"nws": 1000, "other": 40}
    assert kinds["weighted_share"]["nws"] == pytest.approx(1000 / 1040, abs=1e-4)


def test_text_fields_missing_empty_and_lengths():
    t = profile.text_fields(rows())
    assert t["nws"]["headline"]["missing_share"] == 1.0
    other = t["other"]
    assert other["wea_short"]["missing_share"] == 0.0
    assert other["wea_long"]["missing_share"] == 0.25
    assert other["headline"]["length_chars"]["max"] == len("Invented test headline")


def test_duplicates_inside_a_page():
    d = profile.duplicates(rows())["other"]
    assert d["records"] == 4
    assert d["pages"] == 2
    assert d["same_identifier"] == 1
    assert d["same_text_other_identifier"] == 0
    assert d["same_sender_and_sent"] == 1


def test_chains_report_references_by_message_type():
    c = profile.chains(rows())["other"]
    assert c["share_with_references_by_type"] == {"Alert": 0.0, "Update": 1.0}
    assert c["unparsed_references"] == 1
    assert c["references_per_message_sample"]["2"] == 1


def test_people_codes_and_patterns_are_counts_only():
    p = profile.people(rows())
    assert p["codes"]["CAE"]["sample_count"] == 1
    assert p["codes"]["CAE"]["share_of_non_nws"] == 0.25
    found = p["patterns"]["people_codes"]
    assert found["sample_messages"] == 1
    assert found["share_with_pattern"] == {
        "phone": 1.0,
        "plate": 1.0,
        "age": 1.0,
        "height_weight": 0.0,
        "last_seen": 1.0,
    }
    assert "ABC1234" not in repr(p)


def test_structure_names_parameters_and_shapes():
    s = profile.structure(rows())
    assert s["other"]["parameter_names_share"]["CMAMtext"] == 1.0
    assert s["nws"]["other_share"]["signed"] == 1.0
    assert s["other"]["other_share"]["embedded_audio_or_file"] == 0.75


def test_summarize_holds_every_section_and_no_text():
    out = profile.summarize(rows())
    assert out["sample_records"] == 6
    assert out["parsed"] == 5
    assert out["parse_errors"] == {"originalMessage is not well-formed XML": 1}
    assert out["event_code_top30"]["other"]["CEM"]["sample_count"] == 3
    assert out["channels_other"]["sample_count"]["wea+eas+nwem"] == 3
    assert out["languages"]["sample_count"]["en-US+es-US"] == 2
    assert "Invented" not in repr(out)
