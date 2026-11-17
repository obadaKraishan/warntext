"""The table builder on invented archive records. No real alert text anywhere."""

import json
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
    assert all("ref_identifier" not in r for r in rows)
    assert msgs["r03"]["references_resolved"] == 1
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
    assert "identifier" not in row
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
    assert "EX-1" in json.loads((tmp_path / "private" / "identifiers.json").read_text())


def test_no_table_holds_a_sender_value_an_account_key_or_a_raw_identifier():
    for name, schema in tables.SCHEMAS.items():
        for column in schema.names:
            assert "sender" not in column or column.startswith("sender_kind"), (name, column)
            assert "account" not in column, (name, column)
            assert "identifier" not in column, (name, column)


def test_raw_identifiers_appear_in_no_cell(corpus):
    cells = set(every_cell(corpus))
    assert "EX-1" in corpus.raw_identifiers
    assert "NWS-1" in corpus.raw_identifiers  # a referenced message's identifier
    assert not cells & set(corpus.raw_identifiers)


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


def test_a_hand_override_sets_the_authority_kind_and_name():
    from warntext import senders

    relay = invented(
        identifier="EX-R1",
        sender=COUNTY,
        code="CAE",
        sender_name="Sampleton Police Department",
        description="Invented relay text.",
    )
    plain = invented(identifier="EX-R2", sender=COUNTY, sent="2024-05-02T10:00:00-05:00")
    again = invented(identifier="EX-R3", sender=COUNTY, code="CAE", description="Invented.")
    overrides = {
        707: senders.Override(707, "other", "Example Relay Center", "Invented relay."),
    }
    b = tables.build(
        tables.parse_records(
            (Line(), r)
            for r in [record(relay, "q1", cog=707), record(plain, "q2"), record(again, "q3", 707)]
        ),
        overrides=overrides,
    )
    rows = {r["message_id"]: r for c in b.tables.values() for r in c["messages"]}
    assert rows["q1"]["sender_kind"] == "other"
    assert rows["q1"]["sender_kind_source"] == "override"
    assert rows["q1"]["organization"] == "Example Relay Center"
    assert rows["q2"]["sender_kind"] == "local"
    assert b.summary["kind_overrides"]["messages"] == 2
    assert b.summary["kind_overrides"]["kind_before_to_override_kind"] == {"local->other": 2}
    # a person-shaped name in the override file is refused
    bad = {707: senders.Override(707, "other", "Jane Doe", "Invented.")}
    with pytest.raises(ValueError, match="refused"):
        tables.build(tables.parse_records((Line(), r) for r in [record(relay, "q1", cog=707)]), bad)


def test_people_code_rows_keep_only_the_hour_and_the_exact_time_stays_private(tmp_path):
    child = invented(
        identifier="EX-P1",
        sender=COUNTY,
        code="CAE",
        sent="2024-05-01T10:47:12-05:00",
        description="Invented child alert, no details.",
    )
    cancel = invented(
        identifier="EX-P2",
        sender=COUNTY,
        code="CAE",
        msg_type="Cancel",
        sent="2024-05-01T12:31:05-05:00",
        description="Invented cancel.",
        references=f"{COUNTY},EX-P1,2024-05-01T10:47:12-05:00",
    )
    hazard = invented(identifier="EX-H1", sender=COUNTY, sent="2024-05-01T10:47:12-05:00")
    b = run([record(child, "p1"), record(cancel, "p2"), record(hazard, "h1")])
    rows = by_id(b)
    assert rows["p1"]["sent"] == "2024-05-01T10:00:00-05:00"
    assert rows["p1"]["sent_utc"] == datetime(2024, 5, 1, 15, tzinfo=timezone.utc)
    assert rows["p1"]["times_rounded"] is True
    assert rows["p1"]["counties"] == ["48201"]  # the county stays
    assert rows["h1"]["sent"] == "2024-05-01T10:47:12-05:00"  # other rows keep the exact time
    assert rows["h1"]["times_rounded"] is False
    ref = next(r for c in b.tables.values() for r in c["references"] if r["message_id"] == "p2")
    assert ref["ref_sent"] == "2024-05-01T10:00:00-05:00"
    assert ref["ref_message_id"] == "p1"
    thread = by_id_threads(b)["p1"]
    assert thread["times_rounded"] is True
    assert thread["last_sent_utc"] == datetime(2024, 5, 1, 17, tzinfo=timezone.utc)
    exact = {(x["message_id"], x["table"], x["field"]): x["value"] for x in b.people_times}
    assert exact[("p1", "messages", "sent")] == "2024-05-01T10:47:12-05:00"
    assert exact[("p2", "references", "ref_sent")] == "2024-05-01T10:47:12-05:00"
    assert not any(x["message_id"] == "h1" for x in b.people_times)
    tables.write(b, tmp_path / "t", tmp_path / "private")
    private = pq.read_table(tmp_path / "private" / "people_times.parquet").to_pylist()
    assert len(private) == len(b.people_times)
    released = pq.read_table(tmp_path / "t" / "alerts" / "messages.parquet").to_pylist()
    assert "2024-05-01T10:47:12-05:00" not in {r["sent"] for r in released if r["times_rounded"]}


def test_a_described_person_keeps_only_the_hour_and_the_county(tmp_path):
    seek = invented(
        identifier="EX-D1",
        sender=COUNTY,
        code="LAE",
        sent="2024-05-01T10:47:12-05:00",
        headline="Invented: police seek a white male",
        description="Invented: in a red hoodie near the example park.",
        geocodes=("148201",),
    )
    hazard = invented(identifier="EX-H2", sender=COUNTY, sent="2024-05-01T10:47:12-05:00")
    b = run([record(seek, "d1"), record(hazard, "h2")])
    rows = by_id(b)
    assert rows["d1"]["text_withheld"] == "person_described"
    assert rows["d1"]["withheld_patterns"] == ["person_described"]
    assert rows["d1"]["about_missing_person"] is False
    assert rows["d1"]["times_rounded"] is True
    assert rows["d1"]["sent"] == "2024-05-01T10:00:00-05:00"
    assert rows["d1"]["same_geocodes"] == ["048201"]
    assert rows["h2"]["sent"] == "2024-05-01T10:47:12-05:00"
    exact = {(x["message_id"], x["field"]) for x in b.people_times}
    assert ("d1", "sent") in exact
    text_ids = {
        r["message_id"] for c in b.tables.values() for t in tables.TEXT_TABLES for r in c[t]
    }
    assert "d1" not in text_ids and "h2" in text_ids
    assert b.summary["people_treatment"]["withheld_only_as_describing_a_person"] == 1


def test_codes_rows_for_real_alerts_only_withheld_ones_too_and_without_text(corpus):
    rows = corpus.tables["alerts"]["codes"]
    assert corpus.tables["tests"]["codes"] == []
    ids = {r["message_id"] for r in rows}
    assert "r06" in ids  # the child alert is withheld, but its codes are computed
    assert "r09" not in ids  # a test
    assert {r["unit"] for r in rows} <= {"wea90", "wea360", "full"}
    from warntext import codes as cd

    assert all(r["codebook_version"] == cd.CODEBOOK_VERSION and r["record_id"] for r in rows)
    texts = {
        v
        for c in corpus.tables["alerts"]["text_other"]
        for k, v in c.items()
        if k in ("headline", "description", "instruction") and v
    }
    cells = {v for r in rows for v in r.values() if isinstance(v, str)} | {
        x for r in rows for x in (r["link_kinds"] or [])
    }
    assert not cells & texts
    full = next(r for r in rows if r["message_id"] == "r01" and r["unit"] == "full")
    assert full["coded"] is True and isinstance(full["guidance"], bool)


def test_missing_person_and_people_code_rows_keep_the_hour_and_the_county_only():
    header = "ZCZC-CIV-CEM-348201+0100-1221547-EXAMPLE1-"
    spanish = invented(
        identifier="EX-M1",
        sender=COUNTY,
        code="CEM",
        language="es-US",
        sent="2024-05-01T10:47:12-05:00",
        description="Hombre desaparecido, visto por última vez cerca de Oak Road.",
        geocodes=("348201",),
        parameters=(("EAS-ORG", "CIV"), ("EASHeader", header)),
        polygon="30.0,-97.0 30.1,-97.0 30.1,-97.1 30.0,-97.0",
    )
    child = invented(
        identifier="EX-M2",
        sender=COUNTY,
        code="CAE",
        sent="2024-05-01T11:47:12-05:00",
        geocodes=("448201", "048157"),
    )
    hazard = invented(
        identifier="EX-M3",
        sender=COUNTY,
        sent="2024-05-01T12:47:12-05:00",
        geocodes=("548201",),
        parameters=(("EAS-ORG", "CIV"), ("EASHeader", header)),
    )
    b = run([record(spanish, "m1"), record(child, "m2"), record(hazard, "m3")])
    rows = by_id(b)
    m1 = rows["m1"]
    assert m1["text_withheld"] == "missing_person" and m1["about_missing_person"]
    assert m1["sent"] == "2024-05-01T10:00:00-05:00" and m1["times_rounded"]
    assert m1["same_geocodes"] == ["048201"] and m1["counties"] == ["48201"]
    assert not any(r["message_id"] == "m1" for c in b.tables.values() for r in c["text_other"])
    area = next(r for r in b.tables["alerts"]["areas"] if r["message_id"] == "m1")
    assert area["geocode_values"] == ["048201"] and area["polygons"] is None
    info = next(r for r in b.tables["alerts"]["infos"] if r["message_id"] == "m1")
    assert "ZCZC-CIV-CEM-048201+0100-1221500-EXAMPLE1-" in info["parameter_values"]
    assert rows["m2"]["same_geocodes"] == ["048157", "048201"]
    # an ordinary hazard alert keeps its part-of-county digit and its exact header
    assert rows["m3"]["same_geocodes"] == ["548201"] and not rows["m3"]["times_rounded"]
    info3 = next(r for r in b.tables["alerts"]["infos"] if r["message_id"] == "m3")
    assert header in info3["parameter_values"]
    t = b.summary["people_treatment"]
    assert t["withheld_only_as_missing_person"] == 1
    assert t["part_digits_set_to_county"] == 2 and t["messages_with_a_part_digit"] == 2
    assert t["eas_headers_coarsened"] == 1
    private = {(x["message_id"], x["field"]): x["value"] for x in b.people_times}
    assert private[("m1", "EASHeader")] == header


def test_a_build_codes_with_the_codebook_version_it_is_given():
    from warntext import codes as cd
    from warntext import codes_v3

    rec = record(
        invented(
            identifier="EX-V3",
            sender=COUNTY,
            sent="2021-05-01T10:00:00-05:00",
            headline="Invented headline",
            parameters=(("CMAMtext", "Obey all traffic laws and drive with care."),),
        ),
        "rv3",
    )
    by_version = {}
    for version in ("2", "3"):
        b = tables.build(tables.parse_records([(Line(), rec)]), codebook_version=version)
        rows = {r["unit"]: r for r in b.tables["alerts"]["codes"]}
        assert {r["codebook_version"] for r in rows.values()} == {version}
        by_version[version] = rows["wea90"]["hazard"]
    assert by_version == {"2": True, "3": False}
    assert tables.coder("2") is cd and tables.coder("3") is codes_v3
    with pytest.raises(ValueError, match="cannot be built"):
        tables.coder("1")
