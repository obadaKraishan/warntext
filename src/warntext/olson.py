"""This corpus beside the published numbers of Olson et al. (2024), as aggregates only.

Olson, Sutton, Cain and Waugh (2024), "A decade of wireless emergency alerts: A longitudinal
assessment of message content", *Journal of Contingencies and Crisis Management* 32, e12518,
coded the non-weather-service Wireless Emergency Alerts that FEMA gave them for June 2012 to
April 2022 (10,873 messages). After removing missing-person and AMBER alerts, tests and demos,
updates and cancels, and Spanish messages, and counting an alert whose 90- and 360-character
texts are identical once (as a 90-character message), they kept 6,080 texts: 4,207 at 90
characters and 1,873 at 360.

:func:`compare` applies the same filters to the WarnText tables, step by step, and puts the
shares of the rule-based codes beside the published shares. Nothing here reads or prints text:
it works on the record layer (messages and codes) only.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

#: The published counts and shares (percent; 90-character, 360-character, all). From Tables 2 to
#: 7 of the article; ``None`` where a cell is not published. Two printed cells are inconsistent
#: in the article and are noted in ``NOTES``.
PUBLISHED: dict[str, Any] = {
    "corpus": 10873,
    "final": 6080,
    "final_90": 4207,
    "final_360": 1873,
    "contents": {
        "hazard": (70.3, 80.6, 73.5),
        "hazard_description": (16.7, 33.5, 21.9),
        "location": (81.2, 91.5, 84.4),
        "time": (32.8, 53.5, 39.2),
        "source_named": (26.6, 52.1, 34.5),
        "guidance": (64.0, 88.0, 71.4),
        "complete": (2.9, 21.1, 8.5),
        "link": (21.5, 33.4, 24.1),
    },
    "location_kinds": {
        "loc_boundary": (56.0, 75.4, 61.9),
        "loc_road": (29.5, 41.3, 33.1),
        "loc_landmark": (27.4, 33.3, 29.2),
        "loc_vague_or_none": (18.6, 8.6, 15.5),
        "loc_zone": (1.6, 2.3, 1.8),
    },
    "time_kinds": {
        "time_impact": (17.2, 30.7, 21.4),
        "time_action": (11.2, 19.2, 13.6),
        "time_expiry": (14.5, 20.6, 16.4),
    },
    "categories": {
        "wildfire": 32.0,
        "public_safety": 17.6,
        "law_enforcement": 15.9,
        "public_health": 14.2,
        "atmospheric": 12.1,
        "technological": 4.2,
        "other_unknown": 3.2,
        "geophysical": 0.9,
    },
    "senders": {
        "county": 71.5,
        "state": 15.3,
        "city": 8.2,
        "other": 3.4,
        "city_and_county": 1.5,
        "town": 0.03,
    },
}
NOTES = {
    "link": "The 90-character link cell is printed as 625 (21.5%); 625 of 4,207 is 14.9%.",
    "complete": "The 360-character complete cell is printed as 1,329; the share 21.1% fits 396.",
}
START = datetime(2012, 6, 1, tzinfo=timezone.utc)
END = datetime(2022, 5, 1, tzinfo=timezone.utc)
#: Codes Olson et al. removed as missing-person and AMBER alerts; LEW and BLU stayed in theirs.
MISSING_CODES = frozenset({"CAE", "MEP"})
PEOPLE_CODES = frozenset({"CAE", "MEP", "LEW", "BLU"})


def _english_units(codes: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, dict]]:
    """For each message, its first English block's units, by unit name."""
    by_msg: dict[str, dict[int, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for r in codes:
        if (r["language"] or "").lower().startswith("en"):
            by_msg[r["message_id"]][r["info_index"]][r["unit"]] = r
    return {m: blocks[min(blocks)] for m, blocks in by_msg.items()}


def sender_group(kind: str | None, authority_type: str | None, name: str | None) -> str:
    """Olson et al.'s sender groups (county, state, city, city and county, town, other)."""
    if kind == "state" or authority_type == "State":
        return "state"
    if kind != "local":
        return "other"
    n = (name or "").lower()
    if re.search(r"city\s+(?:and|&)\s+county|city-county|consolidated", n):
        return "city_and_county"
    if re.search(r"\b(?:county|parish|borough)\b", n):
        return "county"
    if re.search(r"\b(?:city|municipal)\b", n):
        return "city"
    if re.search(r"\b(?:town|township|village)\b", n):
        return "town"
    return "other"


def _share(rows: list[dict], field: str) -> float | None:
    vals = [r[field] for r in rows if r.get(field) is not None]
    return round(100 * sum(bool(v) for v in vals) / len(vals), 1) if vals else None


def compare(
    messages: list[dict[str, Any]],
    codes: list[dict[str, Any]],
    people: str = "missing",
    unique_texts: bool = False,
) -> dict[str, Any]:
    """The filter steps and the shares beside Olson et al.'s.

    ``people`` is ``missing`` (remove CAE and MEP and any message about a missing person, as
    Olson et al. describe) or ``all`` (remove all four people codes). With ``unique_texts``, one
    message per text group is kept (re-sends counted once), which Olson et al. did not do.
    """
    units = _english_units(codes)
    steps: list[tuple[str, int]] = [("all messages (weather service already out)", len(messages))]
    m = [r for r in messages if r["len_wea_short"] is not None or r["len_wea_long"] is not None]
    steps.append(("phone alerts (a 90- or 360-character text)", len(m)))
    m = [r for r in m if r["sent_utc"] is not None and START <= r["sent_utc"] < END]
    steps.append(("sent June 2012 to April 2022", len(m)))
    steps.append(("  their corpus", PUBLISHED["corpus"]))

    def about_test(r: dict) -> bool:
        u = units.get(r["message_id"], {})
        return any(x.get("about_test") for x in u.values())

    m = [r for r in m if r["config"] == "alerts" and not about_test(r)]
    steps.append(("no tests or demos (by code, or a test's words)", len(m)))
    drop = MISSING_CODES if people == "missing" else PEOPLE_CODES

    def about_missing(r: dict) -> bool:
        u = units.get(r["message_id"], {})
        return any(x.get("about_missing_person") for x in u.values())

    m = [
        r
        for r in m
        if not set(r["event_codes"]) & drop and not (people == "missing" and about_missing(r))
    ]
    steps.append(
        (
            "no missing-person or AMBER alerts"
            if people == "missing"
            else "no alerts with a people code (CAE, MEP, LEW, BLU)",
            len(m),
        )
    )
    m = [r for r in m if r["msg_type"] == "Alert"]
    steps.append(("alerts only (no updates or cancels)", len(m)))

    def english_phone(r: dict) -> bool:
        u = units.get(r["message_id"], {})
        return any(u.get(k, {}).get("coded") for k in ("wea90", "wea360"))

    m = [r for r in m if english_phone(r)]
    steps.append(("English (a coded English phone text)", len(m)))
    if unique_texts:
        seen, kept = set(), []
        for r in sorted(m, key=lambda x: (x["sent_utc"], x["message_id"])):
            key = r["text_group"] or r["message_id"]
            if key not in seen:
                seen.add(key)
                kept.append(r)
        m = kept
        steps.append(("one message per text group (re-sends once)", len(m)))
    u90: list[dict] = []
    u360: list[dict] = []
    same = 0
    msg_of: dict[int, dict] = {}
    for r in m:
        u = units[r["message_id"]]
        a, b = u.get("wea90"), u.get("wea360")
        if a and a["coded"]:
            u90.append(a)
            msg_of[id(a)] = r
        if b and b["coded"]:
            if b["same_as_wea90"] and a and a["coded"]:
                same += 1
            else:
                u360.append(b)
                msg_of[id(b)] = r
    steps.append(("  identical 90 and 360 texts counted once (as 90)", same))
    steps.append(("texts at 90 characters", len(u90)))
    steps.append(("  theirs at 90", PUBLISHED["final_90"]))
    steps.append(("texts at 360 characters", len(u360)))
    steps.append(("  theirs at 360", PUBLISHED["final_360"]))
    steps.append(("texts in all", len(u90) + len(u360)))
    steps.append(("  theirs in all", PUBLISHED["final"]))
    allu = u90 + u360
    table: dict[str, dict[str, Any]] = {}
    for group in ("contents", "location_kinds", "time_kinds"):
        for field, pub in PUBLISHED[group].items():
            ours = (_share(u90, field), _share(u360, field), _share(allu, field))
            table[field] = {"published": pub, "ours": ours, "group": group}
    cats = Counter(x["hazard_category"] for x in allu)
    categories = {
        c: {"published": p, "ours": round(100 * cats[c] / len(allu), 1) if allu else None}
        for c, p in PUBLISHED["categories"].items()
    }
    senders = Counter(
        sender_group(
            msg_of[id(x)]["sender_kind"],
            msg_of[id(x)]["authority_type"],
            msg_of[id(x)]["organization"],
        )
        for x in allu
    )
    sender_table = {
        g: {"published": p, "ours": round(100 * senders[g] / len(allu), 1) if allu else None}
        for g, p in PUBLISHED["senders"].items()
    }
    actions = [x["n_actions"] for x in allu if x["guidance"]]
    return {
        "people_filter": people,
        "unique_texts": unique_texts,
        "steps": steps,
        "shares": table,
        "categories": categories,
        "senders": sender_table,
        "actions_when_guidance": {
            "mean": round(sum(actions) / len(actions), 2) if actions else None,
            "distribution": dict(sorted(Counter(min(a, 5) for a in actions).items())),
        },
        "notes": NOTES,
    }


def gaps(result: Mapping[str, Any], points: float = 5.0) -> list[str]:
    """The shares that differ from the published ones by more than ``points``."""
    out = []
    for field, row in result["shares"].items():
        for label, pub, ours in zip(
            ("90", "360", "all"), row["published"], row["ours"], strict=True
        ):
            if pub is not None and ours is not None and abs(ours - pub) > points:
                out.append(f"{field} ({label}): ours {ours}, theirs {pub}")
    for name in ("categories", "senders"):
        for key, row in result[name].items():
            if row["ours"] is not None and abs(row["ours"] - row["published"]) > points:
                out.append(f"{name} {key}: ours {row['ours']}, theirs {row['published']}")
    return out


def markdown(result: Mapping[str, Any]) -> str:
    """The comparison as Markdown tables (aggregates only)."""
    lines = ["| step | messages |", "|---|---:|"]
    lines += [f"| {name} | {n:,} |" for name, n in result["steps"]]
    lines += ["", "| code | 90 ours | 90 theirs | 360 ours | 360 theirs | all ours | all theirs |"]
    lines += ["|---|---:|---:|---:|---:|---:|---:|"]
    for field, row in result["shares"].items():
        o, p = row["ours"], row["published"]
        cells = [f"{o[k]} | {p[k] if p[k] is not None else '-'}" for k in range(3)]
        lines.append(f"| {field} | " + " | ".join(cells) + " |")
    lines += ["", "| hazard category | ours | theirs |", "|---|---:|---:|"]
    lines += [f"| {c} | {r['ours']} | {r['published']} |" for c, r in result["categories"].items()]
    lines += ["", "| sender | ours | theirs |", "|---|---:|---:|"]
    lines += [f"| {c} | {r['ours']} | {r['published']} |" for c, r in result["senders"].items()]
    return "\n".join(lines) + "\n"
