"""Aggregates of a build, for the method, the data card and the report. Counts only.

Nothing here returns text from a message or a raw sender value: kinds, shapes, reasons, codes,
pattern names, lengths and counts.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from typing import Any

from warntext import senders as sd


def _median(values: list[float | int | None]) -> float | None:
    v = [x for x in values if x is not None]
    return round(statistics.median(v), 4) if v else None


def _share(n: int, total: int) -> float | None:
    return round(n / total, 4) if total else None


def describe(b: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    units = b.units
    rows = {r["message_id"]: r for c in b.tables.values() for r in c["messages"]}
    alerts = [r for r in rows.values() if r["config"] == "alerts"]

    years_records: Counter = Counter()
    years_messages: Counter = Counter()
    for r in rows.values():
        years_records[r["year"]] += r["archive_copies"]
        years_messages[r["year"]] += 1
    out["records_by_year"] = {str(k): v for k, v in sorted(years_records.items(), key=str)}
    out["messages_by_year"] = {str(k): v for k, v in sorted(years_messages.items(), key=str)}
    out["messages_by_config"] = dict(Counter(r["config"] for r in rows.values()))
    out["event_groups"] = {
        c: dict(Counter(r["event_group"] for r in rows.values() if r["config"] == c))
        for c in ("alerts", "tests")
    }
    out["hazards_real_alerts"] = dict(Counter(r["hazard"] for r in alerts).most_common())
    out["status_not_actual"] = dict(
        Counter(r["status"] for r in rows.values() if r["status"] != "Actual")
    )
    out["msg_types"] = {
        c: dict(Counter(r["msg_type"] for r in rows.values() if r["config"] == c))
        for c in ("alerts", "tests")
    }

    # Sender kinds.
    kinds: dict[str, Any] = {}
    for c in ("alerts", "tests", "all"):
        sel = [r for r in rows.values() if c == "all" or r["config"] == c]
        kinds[f"messages_{c}"] = dict(Counter(r["sender_kind"] for r in sel))
    by_cog: dict[Any, str] = {}
    for u in units:
        if u.first.cog_id is not None:
            by_cog[u.first.cog_id] = u.kind
    kinds["authorities"] = dict(Counter(by_cog.values()))
    kinds["authorities_total"] = len(by_cog)
    kinds["messages_without_cog_id"] = sum(1 for u in units if u.first.cog_id is None)
    kinds["source_of_kind_messages"] = dict(Counter(u.kind_source for u in units))
    both = [(u.by_name, u.by_domain) for u in units if u.by_name and u.by_domain]
    kinds["name_and_domain_both_present"] = len(both)
    kinds["name_and_domain_agree"] = sum(1 for a, d in both if a == d)
    kinds["name_and_domain_disagree_pairs"] = {
        f"{a}|{d}": n for (a, d), n in Counter(x for x in both if x[0] != x[1]).most_common(12)
    }
    agree = []
    for u in units:
        if u.first.cog_id is None:
            continue
        mine = u.by_name or u.by_domain
        if mine:
            agree.append(mine == u.kind)
    kinds["messages_whose_own_evidence_matches_their_authority"] = _share(sum(agree), len(agree))
    kinds["messages_with_no_own_evidence"] = sum(1 for u in units if not (u.by_name or u.by_domain))
    out["sender_kinds"] = kinds

    # Sender values by shape (never the values).
    values: dict[str, str] = {}
    for u in units:
        if u.first.sender:
            values[u.first.sender] = sd.address_shape(u.first.sender)
    shapes_values = Counter(values.values())
    shapes_messages = Counter(sd.address_shape(u.first.sender) for u in units)
    out["sender_values"] = {
        "distinct": len(values),
        "shapes_of_distinct_values": dict(shapes_values),
        "shapes_by_message": dict(shapes_messages),
        "person_shaped_distinct": sum(n for k, n in shapes_values.items() if k in sd.PERSON_SHAPES),
        "person_shaped_messages": sum(
            n for k, n in shapes_messages.items() if k in sd.PERSON_SHAPES
        ),
        "with_at_sign_share_of_distinct": _share(
            sum(n for k, n in shapes_values.items() if k != "not_address"), len(values)
        ),
        "values_per_authority_median": _median([len(v) for v in _values_per_cog(units).values()]),
        "authorities_with_more_than_one_value": sum(
            1 for v in _values_per_cog(units).values() if len(v) > 1
        ),
        "values_in_more_than_one_authority": sum(
            1 for v in _cogs_per_value(units).values() if len(v) > 1
        ),
    }

    # The people rule.
    people: dict[str, Any] = {}
    for c in ("alerts", "tests"):
        sel = [r for r in rows.values() if r["config"] == c]
        people[f"withheld_{c}"] = dict(
            Counter(r["text_withheld"] for r in sel if r["text_withheld"])
        )
        people[f"messages_{c}"] = len(sel)
    pat = [r for r in rows.values() if r["text_withheld"] == "personal_pattern"]
    people["by_pattern_personal_pattern"] = dict(
        Counter(p for r in pat for p in r["withheld_patterns"])
    )
    people["single_pattern_personal_pattern"] = dict(
        Counter(r["withheld_patterns"][0] for r in pat if len(r["withheld_patterns"]) == 1)
    )
    people["personal_pattern_by_event_group"] = dict(Counter(r["event_group"] for r in pat))
    people["personal_pattern_by_hazard_real_alerts"] = dict(
        Counter(r["hazard"] for r in pat if r["config"] == "alerts").most_common()
    )
    code = [r for r in rows.values() if r["text_withheld"] == "people_code"]
    people["people_code_by_code"] = dict(Counter(r["event_code"] for r in code))
    people["people_code_patterns_present"] = dict(
        Counter(p for r in code for p in r["withheld_patterns"])
    )
    hz = [r for r in alerts if r["event_group"] == "non_weather_hazard"]
    people["non_weather_hazard_real_alerts"] = len(hz)
    people["non_weather_hazard_withheld"] = sum(1 for r in hz if r["text_withheld"])
    people["shapes_withheld_messages"] = sum(1 for r in rows.values() if r["shapes_withheld"])
    people["narrower_rule_estimate"] = _narrower(pat)
    out["people_rule"] = people

    # The text layer.
    text: dict[str, Any] = {}
    for c, tables in b.tables.items():
        for name in ("text_federal", "text_other"):
            text[f"{c}/{name}_rows"] = len(tables[name])
            text[f"{c}/{name}_messages"] = len({r["message_id"] for r in tables[name]})
    text["real_alerts_with_text"] = sum(1 for r in alerts if not r["text_withheld"])
    out["text_layer"] = text

    # Languages and channels.
    out["languages_real_alerts"] = dict(
        Counter("+".join(sorted(set(r["languages"]))) or "none" for r in alerts).most_common(12)
    )
    out["channels_real_alerts"] = {
        "wea": sum(1 for r in alerts if r["channel_wea"]),
        "eas": sum(1 for r in alerts if r["channel_eas"]),
        "nwem": sum(1 for r in alerts if r["channel_nwem"]),
        "public": sum(1 for r in alerts if r["channel_public"]),
        "messages": len(alerts),
        "wea_handling": dict(Counter(r["wea_handling"] for r in alerts if r["wea_handling"])),
    }

    # Measures on real alerts (all language blocks).
    infos = [i for i in b.tables["alerts"]["infos"]]
    meas: dict[str, Any] = {"info_rows": len(infos)}
    for f in ("event", "headline", "description", "instruction", "web", "wea_short", "wea_long"):
        vals = [i[f"len_{f}"] for i in infos]
        meas[f"{f}_present_share"] = _share(sum(1 for v in vals if v), len(vals))
        meas[f"{f}_median_length"] = _median([v for v in vals if v])
        meas[f"{f}_max_length"] = max((v for v in vals if v is not None), default=None)
    meas["has_link_share"] = _share(sum(1 for i in infos if i["has_link"]), len(infos))
    meas["has_phone_share"] = _share(sum(1 for i in infos if i["has_phone"]), len(infos))
    meas["caps_share_median"] = _median([i["caps_share"] for i in infos])
    meas["caps_share_over_0_9"] = sum(1 for i in infos if (i["caps_share"] or 0) > 0.9)
    meas["wea_short_over_90"] = sum(1 for r in alerts if r["wea_short_over_limit"])
    meas["wea_long_over_360"] = sum(1 for r in alerts if r["wea_long_over_limit"])
    meas["areas_median"] = _median([r["n_areas"] for r in alerts])
    meas["messages_without_same_geocode"] = sum(1 for r in alerts if not r["same_geocodes"])
    meas["states_per_message"] = dict(Counter(min(r["n_states"], 3) for r in alerts))
    meas["counties_median"] = _median([r["n_counties"] for r in alerts])
    meas["states_seen"] = len({s for r in alerts for s in r["states"]})
    meas["with_polygon"] = sum(1 for r in alerts if r["n_polygons"])
    meas["with_circle"] = sum(1 for r in alerts if r["n_circles"])
    out["measures_real_alerts"] = meas
    return out


def _values_per_cog(units: list[Any]) -> dict[Any, set[str]]:
    out: dict[Any, set[str]] = defaultdict(set)
    for u in units:
        if u.first.cog_id is not None and u.first.sender:
            out[u.first.cog_id].add(u.first.sender)
    return out


def _cogs_per_value(units: list[Any]) -> dict[str, set[Any]]:
    out: dict[str, set[Any]] = defaultdict(set)
    for u in units:
        if u.first.cog_id is not None and u.first.sender:
            out[u.first.sender].add(u.first.cog_id)
    return out


def _narrower(pattern_rows: list[dict[str, Any]]) -> dict[str, int]:
    """How many pattern-withheld messages a narrower rule would release, for the report.

    The narrower rule withholds only messages with a person-describing pattern (an age, a
    height or weight, a plate or "last seen"), or with two or more patterns of any kind; a
    phone number or an email address alone (an agency's hotline) would not withhold.
    """
    describing = {"age", "height_weight", "plate", "last_seen"}
    kept = released = 0
    for r in pattern_rows:
        hits = set(r["withheld_patterns"])
        if hits & describing or len(hits) > 1:
            kept += 1
        else:
            released += 1
    return {"still_withheld": kept, "would_keep_text": released}
