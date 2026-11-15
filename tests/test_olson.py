"""The comparison with Olson et al.'s published numbers, on invented rows (no text)."""

from datetime import datetime, timezone

from warntext import olson

T = datetime(2020, 7, 1, tzinfo=timezone.utc)


def msg(mid, **kw):
    row = {
        "message_id": mid,
        "len_wea_short": 80,
        "len_wea_long": None,
        "sent_utc": T,
        "config": "alerts",
        "event_codes": ["CEM"],
        "msg_type": "Alert",
        "text_group": mid,
        "sender_kind": "local",
        "authority_type": "Local",
        "organization": "Sampleton County Office of Emergency Management",
    }
    row.update(kw)
    return row


def unit(mid, name, coded=True, same=None, **codes):
    row = {
        "message_id": mid,
        "info_index": 0,
        "unit": name,
        "language": "en-US",
        "coded": coded,
        "same_as_wea90": same,
        "about_missing_person": False,
        "hazard_category": "wildfire",
        "n_actions": 1,
        "guidance": True,
    }
    for f in ("contents", "location_kinds", "time_kinds"):
        for k in olson.PUBLISHED[f]:
            row.setdefault(k, False)
    row.update(codes)
    return row


def test_the_filters_in_order_and_identical_texts_once():
    messages = [
        msg("a"),
        msg("b", len_wea_long=200),
        msg("c", config="tests"),
        msg("d", event_codes=["CAE"]),
        msg("e", msg_type="Cancel"),
        msg("f", sent_utc=datetime(2023, 1, 1, tzinfo=timezone.utc)),
        msg("g", len_wea_short=None),
        msg("h", event_codes=["LEW"]),
        msg("i", text_group="a"),
    ]
    codes = [
        unit("a", "wea90", hazard=True),
        unit("b", "wea90"),
        unit("b", "wea360", same=True),
        unit("h", "wea90"),
        unit("i", "wea90", hazard=True),
    ]
    r = olson.compare(messages, codes)
    steps = dict(r["steps"])
    assert steps["phone alerts (a 90- or 360-character text)"] == 8
    assert steps["sent June 2012 to April 2022"] == 7
    assert steps["no tests or demos"] == 6
    assert steps["no missing-person or AMBER alerts"] == 5  # LEW stays, as in the article
    assert steps["alerts only (no updates or cancels)"] == 4
    assert steps["  identical 90 and 360 texts counted once (as 90)"] == 1
    assert steps["texts in all"] == 4
    assert r["shares"]["hazard"]["ours"][0] == 50.0
    assert r["senders"]["county"]["ours"] == 100.0
    every = dict(olson.compare(messages, codes, people="all")["steps"])
    assert every["no alerts with a people code (CAE, MEP, LEW, BLU)"] == 4
    unique = dict(olson.compare(messages, codes, unique_texts=True)["steps"])
    assert unique["one message per text group (re-sends once)"] == 3


def test_sender_groups_and_gaps():
    assert olson.sender_group("state", "State", "x") == "state"
    assert olson.sender_group("local", "Local", "City and County of Sampleton") == "city_and_county"
    assert olson.sender_group("local", "Local", "City of Sampleton") == "city"
    assert olson.sender_group("local", "Local", "Town of Sampleton") == "town"
    assert olson.sender_group("tribal", "Tribal", "Sampleton Tribe") == "other"
    r = olson.compare([msg("a")], [unit("a", "wea90", hazard=True)])
    assert any(g.startswith("hazard (90)") for g in olson.gaps(r))
    assert "| hazard |" in olson.markdown(r)
