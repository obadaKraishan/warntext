"""The release check and the text rebuild, on invented messages and mocked answers."""

import copy
import json

import pytest

from cap_samples import invented
from test_tables import BASE, COUNTY, record, run
from warntext import check, cli, privacy, probe, rebuild, tables


@pytest.fixture()
def built():
    records = [
        record(invented(identifier="EX-1", sender=COUNTY), "r01"),
        record(invented(identifier="EX-2", sender=COUNTY, code="CAE"), "r02"),
        record(
            invented(identifier="EX-3", sender=BASE, sender_name="Example Air Force Base"),
            "r03",
            cog=202,
        ),
        record(invented(identifier="EX-4", sender=COUNTY, code="RWT"), "r04"),
    ]
    b = run(records)
    return b.tables, [x["sender"] for x in b.raw_senders]


def test_clean_tables_pass(built):
    t, senders = built
    assert check.check(t, senders, {2024: 4}) == []


def test_a_count_that_differs_from_the_server_fails(built):
    t, senders = built
    out = check.check(t, senders, {2024: 5, 2023: 1})
    assert any("2024 has 4 records" in f for f in out)
    assert any("2023 has 0 records" in f for f in out)


def test_text_of_a_withheld_message_fails(built):
    t, senders = built
    t = copy.deepcopy(t)
    good = t["alerts"]["text_other"][0]
    t["alerts"]["text_other"].append({**good, "message_id": "r02"})
    out = check.check(t, senders, None)
    assert any("withheld message(s) have text" in f for f in out)
    area = next(a for a in t["alerts"]["areas"] if a["message_id"] == "r02")
    area["polygons"] = ["1,1 2,2 1,1"]
    assert any("keep shapes" in f for f in check.check(t, senders, None))


def test_a_dropped_parameter_fails(built):
    t, senders = built
    t = copy.deepcopy(t)
    info = t["alerts"]["infos"][0]
    info["parameter_names"] = [*info["parameter_names"], "UserName", "EAS-ORG"]
    info["parameter_values"] = [*info["parameter_values"], "invented", "free text"]
    out = check.check(t, senders, None)
    assert any("'UserName': 1" in f and "EAS-ORG (unexpected value)" in f for f in out)


def test_a_raw_sender_value_anywhere_fails(built):
    t, senders = built
    t = copy.deepcopy(t)
    t["alerts"]["messages"][0]["organization"] = COUNTY.upper()
    t["alerts"]["text_other"][0]["description"] = f"Invented, write to {COUNTY}."
    out = check.check(t, senders, None)
    assert any("alerts/messages: 1 cell(s) hold a raw sender value" in f for f in out)
    assert any("alerts/text_other: 1 cell(s)" in f for f in out)


def test_a_text_row_of_the_wrong_kind_or_message_fails(built):
    t, senders = built
    t = copy.deepcopy(t)
    row = t["alerts"]["text_federal"][0]
    t["alerts"]["text_other"].append(dict(row))
    t["alerts"]["text_federal"].append({**row, "message_id": "nope", "info_index": 9})
    out = check.check(t, senders, None)
    assert any("text_other: 1 row(s) of the wrong sender kind" in f for f in out)
    assert any("not in the tables" in f for f in out)
    assert any("text rows: 1 duplicated" in f for f in out)


def test_duplicated_ids_and_missing_sources_fail(built):
    t, senders = built
    t = copy.deepcopy(t)
    t["tests"]["messages"].append(dict(t["alerts"]["messages"][0]))
    t["alerts"]["threads"][0]["source"] = None
    out = check.check(t, senders, None)
    assert any("messages.message_id: 1 duplicated" in f for f in out)
    assert any("messages.record_ids: 1 duplicated" in f for f in out)
    assert any("without a source" in f for f in out)


def test_the_check_command_reads_parquet_and_fails_loudly(built, tmp_path, capsys):
    t, senders = built
    b = tables.Build(units=[], tables=t, summary={}, raw_senders=[{"sender": s} for s in senders])
    tables.write(b, tmp_path / "tables", tmp_path / "private")
    counts = tmp_path / "counts.json"
    counts.write_text(
        json.dumps(
            {
                "facts": {"until": "2025-01-01T00:00:00.000Z"},
                "counts": [{"name": "other:2024", "count": 4}],
            }
        )
    )
    args = ["check", "--tables", str(tmp_path / "tables"), "--private", str(tmp_path / "private")]
    assert cli.main([*args, "--counts", str(counts)]) == 0
    assert "Release check passed" in capsys.readouterr().out
    counts.write_text(counts.read_text().replace('"count": 4', '"count": 3'))
    assert cli.main([*args, "--counts", str(counts)]) == 1
    assert "RELEASE CHECK FAILED" in capsys.readouterr().out


class Resp:
    def __init__(self, records, status=200):
        self.status = status
        self.content = json.dumps({"metadata": {}, probe.ENTITY: records}).encode()

    def json(self):
        return json.loads(self.content)


class FakeClient:
    def __init__(self, answers):
        self.answers = list(answers)
        self.params = []

    def get(self, url, params):
        self.params.append(params)
        return self.answers.pop(0)

    def clock(self):
        return "2026-11-16T00:00:00.000Z"


def test_rebuild_reads_by_record_id_and_skips_withheld(built):
    t, _ = built
    messages = [r for c in t.values() for r in c["messages"]]
    todo = rebuild.wanted(messages, None)
    assert {m["message_id"] for m in todo} == {"r01", "r03", "r04"}
    assert {m["message_id"] for m in rebuild.wanted(messages, {"federal"})} == {"r03"}
    recs = {
        "r01": record(invented(identifier="EX-1", sender=COUNTY), "r01"),
        "r03": record(
            invented(identifier="EX-3", sender=BASE, sender_name="Example Air Force Base"), "r03"
        ),
        # the source now holds a phone number in this one: it is withheld again
        "r04": record(
            invented(identifier="EX-4", sender=COUNTY, code="RWT", description="Call 555-555-0100"),
            "r04",
        ),
    }
    todo = sorted(todo, key=lambda m: m["message_id"])
    client = FakeClient([Resp([recs["r01"], recs["r03"]]), Resp([recs["r04"]])])
    rows, stats = rebuild.rebuild(client, todo, batch=2)
    assert client.params[0]["$filter"] == "id eq 'r01' or id eq 'r03'"
    assert client.params[0]["$select"] == "id,sent,originalMessage"
    assert stats == {"rebuilt": 2, "withheld_now": 1}
    assert [r["message_id"] for r in rows["text_federal"]] == ["r03"]
    assert [r["message_id"] for r in rows["text_other"]] == ["r01"]
    local = next(r for r in t["alerts"]["text_other"] if r["message_id"] == "r01")
    again = rows["text_other"][0]
    assert {k: v for k, v in again.items() if k != "retrieved_at"} == {
        k: v for k, v in local.items() if k != "retrieved_at"
    }


def test_rebuild_counts_missing_and_unreadable_and_stops_on_errors(built):
    t, _ = built
    todo = [m for m in rebuild.wanted(t["alerts"]["messages"], None) if m["message_id"] == "r01"]
    broken = {"id": "r01", "originalMessage": "<alert"}
    _, stats = rebuild.rebuild(FakeClient([Resp([broken])]), todo)
    assert stats == {"unparsed": 1}
    _, stats = rebuild.rebuild(FakeClient([Resp([])]), todo)
    assert stats == {"not_found": 1}
    with pytest.raises(RuntimeError, match="Nothing was written"):
        rebuild.rebuild(FakeClient([Resp([], status=500)]), todo)


def test_rebuild_write(tmp_path):
    counts = rebuild.write({"text_federal": [], "text_other": []}, tmp_path / "out")
    assert counts == {"text_federal": 0, "text_other": 0}
    assert (tmp_path / "out" / "text_other.parquet").exists()


def test_text_leaking_into_the_record_layer_fails(built):
    t, senders = built
    t = copy.deepcopy(t)
    t["alerts"]["infos"][0]["parameter_names"] = ["timezone"]
    t["alerts"]["infos"][0]["parameter_values"] = ["Call 555-555-0123"]
    out = check.check(t, senders, None)
    assert any("alerts/infos: cells match personal-detail patterns: {'phone': 1}" in f for f in out)


def test_sender_values_are_checked_by_their_form(built):
    t, senders = built
    t = copy.deepcopy(t)
    senders = [*senders, "98765", "EXAMPLE1", "Example County"]
    # a numeric sender value equal to a message's number is not a leak
    t["alerts"]["messages"][0]["event_codes"] = ["98765"]
    # a station code used as the sender value is allowed in its parameter
    info = t["alerts"]["infos"][0]
    info["parameter_names"] = [*info["parameter_names"], "EAS-STN-ID"]
    info["parameter_values"] = [*info["parameter_values"], "EXAMPLE1"]
    # a place name used as the sender value may appear in the text layer
    t["alerts"]["text_other"][0]["area_descriptions"] = ["Example County"]
    assert check.check(t, senders, None) == []
    t["alerts"]["references"].append(
        {**t["alerts"]["messages"][0], "ref_index": 0, "ref_message_id": "EXAMPLE1"}
    )
    out = check.check(t, senders, None)
    assert any("alerts/references: 1 cell(s) hold a raw sender value" in f for f in out)


def test_sender_sets_split_addresses_and_names():
    addresses, named = check.sender_sets(["A@Example.org", "12345", "AB-1", "Example1", ""])
    assert addresses == {"a@example.org"}
    assert named == {"example1"}


def test_own_vocabulary_and_program_names_are_not_leaks(built):
    t, senders = built
    t = copy.deepcopy(t)
    m = t["alerts"]["messages"][0]
    m["hazard"] = "missing_person"
    m["wea_handling"] = "AMBER Alert"
    m["organization"] = "Example Center for Missing Children"
    assert check.check(t, senders, None) == []
    m["organization"] = "Example Center 555-555-0123"
    out = check.check(t, senders, None)
    assert any("{'phone': 1}" in f for f in out)


def test_a_raw_identifier_in_any_cell_fails(built):
    t, senders = built
    ids = ["EX-1", "EX-2", "EX-3", "EX-4"]
    assert check.check(t, senders, None, ids) == []
    t = copy.deepcopy(t)
    t["alerts"]["messages"][0]["event_codes"] = ["EX-3"]
    t["alerts"]["text_other"][0]["web"] = "https://example.gov/alert?id=ex-4&x=1"
    out = check.check(t, senders, None, ids)
    assert any("alerts/messages: 1 cell(s) hold a raw CAP identifier" in f for f in out)
    assert any("alerts/text_other: 1 cell(s) hold a raw CAP identifier" in f for f in out)


def test_an_exact_people_code_time_fails(built):
    from datetime import datetime, timezone

    t, senders = built
    t = copy.deepcopy(t)
    child = next(r for r in t["alerts"]["messages"] if r["message_id"] == "r02")
    assert child["text_withheld"] == "people_code" and child["times_rounded"]
    assert check.check(t, senders, None) == []
    child["sent"] = "2024-05-01T10:15:00-05:00"
    child["sent_utc"] = datetime(2024, 5, 1, 15, 15, tzinfo=timezone.utc)
    info = next(r for r in t["alerts"]["infos"] if r["message_id"] == "r02")
    info["expires"] = "2024-05-01T11:15:00-05:00"
    thread = next(r for r in t["alerts"]["threads"] if r["thread_id"] == child["thread_id"])
    thread["first_sent_utc"] = child["sent_utc"]
    out = check.check(t, senders, None)
    assert any(
        "people-code rows hold times finer than the hour" in f
        and "'messages.sent': 1" in f
        and "'messages.sent_utc': 1" in f
        and "'infos.expires': 1" in f
        and "'threads.first_sent_utc': 1" in f
        for f in out
    )
    # a hazard alert keeps its exact time
    other = next(r for r in t["alerts"]["messages"] if r["message_id"] == "r01")
    assert privacy.finer_than_hour(other["sent"])


def test_the_check_command_needs_the_private_identifier_file(tmp_path):
    with pytest.raises(SystemExit, match=r"identifiers\.json is missing"):
        check.read_identifiers(tmp_path)


def test_a_part_digit_or_an_exact_time_on_a_people_or_missing_person_row_fails(built):
    t, senders = built
    t = copy.deepcopy(t)
    child = next(r for r in t["alerts"]["messages"] if r["message_id"] == "r02")
    child["same_geocodes"] = ["348201"]
    out = check.check(t, senders, None)
    assert any("hold a part-of-county digit" in f and "messages.same_geocodes" in f for f in out)
    t = copy.deepcopy(built[0])
    hazard = next(r for r in t["alerts"]["messages"] if r["message_id"] == "r01")
    assert check.check(t, senders, None) == []  # an ordinary alert keeps its exact time
    hazard["about_missing_person"] = True
    out = check.check(t, senders, None)
    assert any("missing-person rows hold times finer than the hour" in f for f in out)
    t = copy.deepcopy(built[0])
    info = next(r for r in t["alerts"]["infos"] if r["message_id"] == "r02")
    info["parameter_names"] = [*info["parameter_names"], "EASHeader"]
    info["parameter_values"] = [*info["parameter_values"], "ZCZC-CIV-CAE-348201+0100-1221547-X-"]
    out = check.check(t, senders, None)
    assert any("'infos.EASHeader': 1" in f and "finer than the hour" in f for f in out)
    assert any("'infos.EASHeader': 1" in f and "part-of-county" in f for f in out)
