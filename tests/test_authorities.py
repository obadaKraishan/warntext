"""FEMA's list of alerting authorities: parsing the page, the snapshot, and its use in a build."""

import pytest

from cap_samples import invented
from test_tables import COUNTY, Line, record
from warntext import authorities as au
from warntext import tables

PAGE = """<html><body><p>Last updated Nov 12, 2026</p><table>
<tr><th>﻿IPAWS Alerting Authority ID</th><th>IPAWS Alerting Authority Name</th>
<th>State/Province</th><th>FEMA Region</th><th>Alerting Authority Type</th></tr>
<tr><td>900101</td><td>Example County Office of Emergency Management</td><td>TX</td>
<td>Region 6</td><td>Local</td></tr>
<tr><td>900102</td><td>Example State Emergency Management &amp; Homeland Security</td><td>TX</td>
<td>Region 6</td><td>State</td></tr>
<tr><td>900103</td><td>Example Proving Ground</td><td>TX</td><td>Region 6</td><td>Military</td></tr>
</table></body></html>"""


def test_the_page_parses_by_its_header():
    rows = au.parse_page(PAGE)
    assert [a.cog_id for a in rows] == [900101, 900102, 900103]
    assert rows[1].name == "Example State Emergency Management & Homeland Security"
    assert [a.kind for a in rows] == ["local", "state", "federal"]
    assert au.parse_csv(au.to_csv(rows)) == {a.cog_id: a for a in rows}


def test_a_changed_or_broken_page_is_refused():
    with pytest.raises(ValueError, match="FEMA may have changed it"):
        au.parse_page("<table><tr><th>ID</th><th>Name</th></tr></table>")
    with pytest.raises(ValueError, match="repeats identifier"):
        au.parse_page(PAGE.replace("900102", "900101"))
    with pytest.raises(ValueError, match="not a number"):
        au.parse_page(PAGE.replace("900103", "90010X"))
    with pytest.raises(ValueError, match="no rows"):
        au.parse_page(PAGE.split("<tr><td>")[0] + "</table>")
    with pytest.raises(ValueError, match="the header must be"):
        au.parse_csv("id,name\n1,x\n")


def test_the_tracked_snapshot_loads():
    fema = au.load()
    assert len(fema) > 2000
    assert {a.type for a in fema.values()} <= set(au.TYPE_TO_KIND)
    assert all(a.cog_id == k for k, a in fema.items())


def test_fema_type_and_name_come_first_and_the_rule_kind_stays_beside_them():
    fema = {a.cog_id: a for a in au.parse_page(PAGE)}
    # the rule reads this sender as local; FEMA lists the authority as State
    msg = invented(identifier="EX-F1", sender=COUNTY, sender_name="Example Sheriff's Office")
    base = invented(identifier="EX-F2", sender=COUNTY, sender_name="Example Base Fire")
    unlisted = invented(identifier="EX-F3", sender=COUNTY)
    b = tables.build(
        tables.parse_records(
            (Line(), r)
            for r in [
                record(msg, "f1", cog=900102),
                record(base, "f2", cog=900103),
                record(unlisted, "f3", cog=101),
            ]
        ),
        overrides={},
        fema=fema,
    )
    rows = {r["message_id"]: r for c in b.tables.values() for r in c["messages"]}
    assert rows["f1"]["sender_kind"] == "state"
    assert rows["f1"]["sender_kind_source"] == "fema_list"
    assert rows["f1"]["sender_kind_rule"] == "local"
    assert rows["f1"]["authority_type"] == "State"
    assert rows["f1"]["organization"] == "Example State Emergency Management & Homeland Security"
    assert rows["f1"]["organization_source"] == "fema_list"
    assert rows["f2"]["sender_kind"] == "federal"  # Military reads as federal
    assert rows["f2"]["organization"] == "Example Proving Ground"  # official: no word needed
    assert rows["f3"]["sender_kind_source"] != "fema_list"
    assert rows["f3"]["authority_type"] is None
    assert rows["f3"]["organization_source"] == "sender_name"
    s = b.summary["fema_list"]
    assert s["archive_authorities_listed"] == 2
    assert s["kind_agrees_authorities"] == 0
    assert s["fema_type_to_rule_kind_authorities"]["State->local"] == 1
    # the text of the authority FEMA lists as Military goes to the federal table
    assert {r["message_id"] for r in b.tables["alerts"]["text_federal"]} == {"f2"}


def test_an_official_name_still_fails_the_person_and_address_checks():
    assert tables.org_name_check("Example Proving Ground", set(), official=True) is None
    assert tables.org_name_check("Example Proving Ground", set()) == "no_organization_word"
    assert tables.org_name_check("Jane Doe", set(), official=True) == "person_shaped"
    assert tables.org_name_check("x@example.org", set(), official=True) == "address_or_number"
