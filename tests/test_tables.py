"""The table builder on invented archive records. No real alert text anywhere."""

from datetime import datetime, timezone

import pyarrow.parquet as pq
import pytest

from cap_samples import invented
from warntext import cap, tables

COUNTY = "alerts@example-county.example.gov"
BASE = "alerts@district.example.army.mil"
PERSON = "jane.doe@example-city.example.gov"


class Line:
    fetched_at = "2026-11-15T15:00:00.000Z"


def record(xml, rid, cog=101):
    """An archive record as OpenFEMA serves it, with its fields read from the invented XML."""
    m = cap.parse_xml(xml)
    sent = datetime.fromisoformat(m.sent).astimezone(timezone.utc)
    return {
        "id": rid,
        "sent": sent.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "sender": m.sender,
        "identifier": m.identifier,
        "status": m.status,
        "msgType": m.msg_type,
        "scope": m.scope,
        "cogId": cog,
        "info": [{"eventCode": [{"value": p.value} for p in i.event_codes]} for i in m.infos],
        "originalMessage": xml,
    }


def run(records):
    return tables.build(tables.parse_records((Line(), r) for r in records))


def every_cell(b):
    for config in b.tables.values():
        for rows in config.values():
            for row in rows:
                for value in row.values():
                    if isinstance(value, list):
                        yield from (str(v) for v in value)
                    elif value is not None:
                        yield str(value)


@pytest.fixture()
def corpus():
    alert = invented(identifier="EX-1", sender=COUNTY, sent="2024-05-01T10:00:00-05:00")
    update = invented(
        identifier="EX-2",
        sender=COUNTY,
        sent="2024-05-01T11:00:00-05:00",
        msg_type="Update",
        description="Invented update text.",
        references=f"{COUNTY},EX-1,2024-05-01T10:00:00-05:00",
    )
    cancel = invented(
        identifier="EX-3",
        sender=COUNTY,
        sent="2024-05-01T12:00:00-05:00",
        msg_type="Cancel",
        description="Invented all clear.",
        # the same time as the alert, written in UTC: resolves by time
        references=f"{COUNTY},EX-1,2024-05-01T15:00:00Z "
        "w-nws.webmaster@noaa.gov,NWS-1,2024-05-01T09:00:00-05:00",
    )
    resend = invented(identifier="EX-4", sender=COUNTY, sent="2024-05-01T13:00:00-05:00")
    child = invented(
        identifier="EX-5",
        sender=COUNTY,
        code="CAE",
        description="Invented child alert, no details.",
        polygon="30.0,-97.0 30.1,-97.0 30.1,-97.1 30.0,-97.0",
    )
    flagged = invented(
        identifier="EX-6",
        sender=COUNTY,
        code="CEM",
        description="Invented. Call 555-555-0123.",
    )
    federal = invented(
        identifier="EX-7",
        sender=BASE,
        code="EVI",
        sender_name="Example Air Force Base",
        description="Invented base evacuation.",
    )
    test = invented(identifier="EX-8", sender=COUNTY, code="RWT", description="Invented test.")
    staff = invented(
        identifier=f"EX-9-{PERSON}",
        sender=PERSON,
        code="FRW",
        sender_name="Jane Doe",
        description="Invented fire text.",
        parameters=(("EAS-ORG", "CIV"), ("UserName", "invented.user"), ("CMAMtext", "Invented")),
        contact="Invented contact",
    )
    records = [
        record(alert, "r01"),
        record(alert, "r02"),  # an archive copy of the alert
        record(update, "r03"),
        record(cancel, "r04"),
        record(resend, "r05"),
        record(child, "r06"),
        record(flagged, "r07"),
        record(federal, "r08", cog=202),
        record(test, "r09"),
        record(staff, "r10", cog=303),
        {
            "id": "r11",
            "sent": "2024-06-01T00:00:00.000Z",
            "sender": COUNTY,
            "cogId": 101,
            "identifier": "EX-10",
            "status": "Actual",
            "msgType": "Alert",
            "scope": "Public",
            "originalMessage": "<alert><unclosed></alert>",
        },
    ]
    return run(records)


def by_id(b, table="messages"):
    return {r["message_id"]: r for c in b.tables.values() for r in c[table]}


def test_archive_copies_collapse_into_one_message(corpus):
    msgs = by_id(corpus)
    assert msgs["r01"]["record_ids"] == ["r01", "r02"]
    assert msgs["r01"]["archive_copies"] == 2
    assert "r02" not in msgs
    assert corpus.summary["archive_copies"]["extra_records"] == 1


def test_resends_share_a_text_group(corpus):
    msgs = by_id(corpus)
    assert msgs["r05"]["text_group"] == msgs["r01"]["text_group"] == "r01"
    assert msgs["r05"]["text_group_size"] == 2
    assert msgs["r03"]["text_group_size"] == 1


def test_threads_from_references(corpus):
    msgs = by_id(corpus)
    assert msgs["r03"]["thread_id"] == msgs["r04"]["thread_id"] == "r01"
    assert [msgs[x]["thread_position"] for x in ("r01", "r03", "r04")] == [0, 1, 2]
    threads = by_id_threads(corpus)
    assert threads["r01"]["shape"] == "alert_updates_and_cancel"
    assert threads["r05"]["shape"] == "alert_only"
    refs = corpus.summary["references"]["by_resolution"]
    assert refs == {
        "exact": 1,
        "same_time_other_form": 1,
        "unresolved:weather_service": 1,
    }
    rows = [r for c in corpus.tables.values() for r in c["references"]]
    assert all("@" not in str(r["ref_identifier"]) for r in rows)
    assert {r["ref_weather_service"] for r in rows} == {True, False}


def by_id_threads(b):
    return {r["thread_id"]: r for c in b.tables.values() for r in c["threads"]}


def test_people_codes_and_patterns_withhold_text_and_shapes(corpus):
    msgs = by_id(corpus)
    assert msgs["r06"]["text_withheld"] == "people_code"
    assert msgs["r06"]["shapes_withheld"] is True
    assert msgs["r07"]["text_withheld"] == "personal_pattern"
    assert msgs["r07"]["withheld_patterns"] == ["phone"]
    assert msgs["r07"]["has_phone"] is True
    text_ids = {
        r["message_id"] for c in corpus.tables.values() for t in tables.TEXT_TABLES for r in c[t]
    }
    assert not text_ids & {"r06", "r07", "r11"}
    areas = [r for c in corpus.tables.values() for r in c["areas"] if r["message_id"] == "r06"]
    assert areas and all(a["polygons"] is None for a in areas)
    assert areas[0]["n_polygons"] == 1


def test_text_goes_to_the_table_of_its_sender_kind(corpus):
    msgs = by_id(corpus)
    assert msgs["r08"]["sender_kind"] == "federal"
    assert msgs["r01"]["sender_kind"] == "local"
    federal = {r["message_id"] for r in corpus.tables["alerts"]["text_federal"]}
    other = {r["message_id"] for r in corpus.tables["alerts"]["text_other"]}
    assert federal == {"r08"}
    assert {"r01", "r03", "r04", "r05", "r10"} <= other


def test_tests_have_their_own_configuration(corpus):
    assert [r["message_id"] for r in corpus.tables["tests"]["messages"]] == ["r09"]
    assert by_id(corpus)["r09"]["config"] == "tests"


def test_an_unreadable_record_keeps_its_row_without_text(corpus):
    row = by_id(corpus)["r11"]
    assert row["parse_ok"] is False
    assert row["text_withheld"] == "unparsed"
    assert row["year"] == 2024
    assert corpus.summary["parse_errors_by_kind"] == {"not_well_formed": 1}


def test_staff_details_never_reach_a_table(corpus):
    row = by_id(corpus)["r10"]
    assert row["identifier"] is None
    assert row["identifier_withheld"] is True
    assert row["contact_dropped"] is True
    assert row["parameters_dropped"] == 1
    assert row["organization"] is None  # a person-shaped name is not released
    info = next(r for r in corpus.tables["alerts"]["infos"] if r["message_id"] == "r10")
    assert info["parameter_names"] == ["EAS-ORG"]
    cells = set(every_cell(corpus))
    assert not any(PERSON in c or COUNTY in c or BASE in c for c in cells)
    assert not any("invented.user" in c or "Invented contact" in c for c in cells)
    assert corpus.summary["parameters"]["dropped_by_name"] == {"UserName": 1}
    assert corpus.summary["organization_names"]["candidate_names_rejected_by_reason"] == {
        "person_shaped": 1
    }


def test_measures_on_the_rows(corpus):
    row = by_id(corpus)["r01"]
    assert row["len_headline"] == len("Invented headline")
    assert row["states"] == ["TX"]
    assert row["counties"] == ["48201"]
    assert row["caps_share"] is not None
    assert row["crosscheck_mismatches"] == []


def test_every_row_has_its_source_and_a_record_id(corpus):
    for config in corpus.tables.values():
        for rows in config.values():
            for row in rows:
                assert row["source"] == tables.ENDPOINT
                assert row["record_id"]


def test_write_produces_parquet_and_a_private_sender_file(corpus, tmp_path):
    counts = tables.write(corpus, tmp_path / "tables", tmp_path / "private")
    assert counts["alerts/messages"] == len(corpus.tables["alerts"]["messages"])
    t = pq.read_table(tmp_path / "tables" / "alerts" / "messages.parquet")
    assert t.num_rows == counts["alerts/messages"]
    assert (tmp_path / "tables" / "tests" / "text_other.parquet").exists()
    assert COUNTY in (tmp_path / "private" / "sender_values.json").read_text()


def test_org_name_check_reasons():
    assert tables.org_name_check("Example County OEM", set()) is None
    assert tables.org_name_check("Jane Doe", set()) == "person_shaped"
    assert tables.org_name_check("x@example.org", set()) == "address_or_number"
    assert tables.org_name_check("Example Unit", {"example unit"}) == "equals_a_sender_value"
    assert tables.org_name_check("ab", set()) == "length"
    assert tables.org_name_check("Sgt. Jane Doe", set()) == "no_organization_word"
    assert tables.org_name_check("Sampleton", set()) == "no_organization_word"
    assert tables.org_name_check("EXAMPLE-EMA", set()) is None
    assert tables.org_name_check("Sampleton Police", set()) is None


def test_thread_shapes():
    from collections import Counter

    assert tables.thread_shape(Counter({"Update": 1})) == "no_alert"
    assert tables.thread_shape(Counter({"Alert": 2})) == "alerts_only"
    assert tables.thread_shape(Counter({"Alert": 1, "Cancel": 1})) == "alert_and_cancel"
    assert tables.thread_shape(Counter({"Alert": 1, "Update": 2})) == "alert_and_updates"
