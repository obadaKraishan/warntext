"""What the archive holds, measured on the sample, as aggregates only.

Each sampled record carries its stratum's weight (records in the archive over records drawn), so
weighted shares estimate the whole archive; unweighted counts describe the sample. No message
text leaves this module: only codes, field names, lengths, pattern counts and counts of
fingerprints (hashes used to find duplicates, never written out).
"""

from __future__ import annotations

import hashlib
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from warntext import cap, patterns
from warntext.schema import Message

TEXT_FIELDS = ("headline", "description", "instruction", "wea_short", "wea_long")
#: SAME event codes for messages about people (FEMA's IPAWS event-code glossary).
PEOPLE_CODES = {
    "CAE": "Child Abduction Emergency",
    "MEP": "Missing and Endangered Persons",
    "BLU": "Blue Alert",
    "LEW": "Law Enforcement Warning",
}
#: Codes whose messages may be about people, depending on the case.
MAYBE_PEOPLE_CODES = {"LAE": "Local Area Emergency", "CEM": "Civil Emergency Message"}
NWS_CUTOVER = "2023-08-01"
#: Non-weather SAME codes in FEMA's "Event Code Descriptions for Use with IPAWS" (February
#: 2021). It says the weather codes "are reserved for the National Weather Service".
TEST_CODES = frozenset({"RWT", "RMT", "DMO", "NPT", "NMN"})
ADMIN_CODES = frozenset({"ADR"})
NON_WEATHER_HAZARD_CODES = frozenset(
    {
        "AVA",
        "AVW",
        "CDW",
        "CEM",
        "EQW",
        "EVI",
        "FRW",
        "HMW",
        "LAE",
        "NUW",
        "RHW",
        "SPW",
        "TOE",
        "VOW",
        "EAN",
        "NIC",
    }
)


def event_group(code: str | None) -> str:
    """Group a SAME event code: test or demo, about people, administrative, non-weather
    hazard, weather (every other code), or none."""
    if not code:
        return "none"
    if code in TEST_CODES:
        return "test_or_demo"
    if code in PEOPLE_CODES:
        return "about_people"
    if code in ADMIN_CODES:
        return "administrative"
    if code in NON_WEATHER_HAZARD_CODES:
        return "non_weather_hazard"
    return "weather"


#: Vendor parameters that may name the sending agency's staff or their addresses.
STAFF_PARAMETERS = frozenset(
    {"UserName", "Email", "Email To", "SMS", "AssignedAddress", "DA Page Customer ID"}
)
#: Character limits of the two phone texts (47 CFR 10.430).
WEA_LIMITS = {"wea_short": 90, "wea_long": 360}


@dataclass(frozen=True)
class Row:
    year: int
    kind: str
    page: int
    weight: float
    message: Message | None
    error: str | None = None


def build_rows(
    records: Iterable[tuple[Any, Mapping[str, Any]]], stratum_counts: Mapping[tuple[int, str], int]
) -> list[Row]:
    """Parse each ``(manifest_line, record)`` and attach its stratum weight."""
    items = list(records)
    drawn = Counter((line.year, line.kind) for line, _ in items)
    rows = []
    for line, record in items:
        weight = stratum_counts[(line.year, line.kind)] / drawn[(line.year, line.kind)]
        try:
            rows.append(Row(line.year, line.kind, line.skip, weight, cap.parse_record(record)))
        except cap.CapParseError as exc:
            reason = str(exc).split(": ", 1)[-1].split(" (", 1)[0]
            rows.append(Row(line.year, line.kind, line.skip, weight, None, reason))
    return rows


def _utc_seconds(value: str | None) -> float | None:
    from datetime import datetime

    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def crosscheck(items: Iterable[tuple[Any, Mapping[str, Any]]]) -> dict[str, Any]:
    """Compare what the parser reads from the XML with OpenFEMA's own JSON fields.

    Counts mismatches per field and kind of sender; a record that cannot be parsed counts once
    under ``unparsed``.
    """
    fields = (
        ("identifier", "identifier"),
        ("sender", "sender"),
        ("status", "status"),
        ("msg_type", "msgType"),
        ("scope", "scope"),
    )
    n = 0
    mismatches: Counter = Counter()
    for line, rec in items:
        n += 1
        try:
            m = cap.parse_record(rec)
        except cap.CapParseError:
            mismatches[f"{line.kind}:unparsed"] += 1
            continue
        for ours, theirs in fields:
            if (getattr(m, ours) or "") != (rec.get(theirs) or ""):
                mismatches[f"{line.kind}:{theirs}"] += 1
        a, b = _utc_seconds(m.sent), _utc_seconds(rec.get("sent"))
        if a is None or b is None or abs(a - b) > 1:
            mismatches[f"{line.kind}:sent_utc"] += 1
        ours_codes = sorted(p.value for i in m.infos for p in i.event_codes)
        theirs_codes = sorted(
            str(d.get("value")) for i in (rec.get("info") or []) for d in (i.get("eventCode") or [])
        )
        if ours_codes != theirs_codes:
            mismatches[f"{line.kind}:eventCode"] += 1
        if len(m.infos) != len(rec.get("info") or []):
            mismatches[f"{line.kind}:info_count"] += 1
    return {"records": n, "mismatches": dict(mismatches)}


def _share(counter: Mapping[Any, float], total: float, digits: int = 4) -> dict:
    return {str(k): round(v / total, digits) for k, v in counter.items()} if total else {}


def weighted(rows: Iterable[Row], key) -> dict[str, Any]:
    """Weighted shares and unweighted counts of ``key(row)`` (skipping None)."""
    w: Counter = Counter()
    n: Counter = Counter()
    for r in rows:
        k = key(r)
        if k is None:
            continue
        w[k] += r.weight
        n[k] += 1
    total = sum(w.values())
    order = [k for k, _ in w.most_common()]
    return {
        "weighted_share": {str(k): round(w[k] / total, 4) for k in order} if total else {},
        "sample_count": {str(k): n[k] for k in order},
        "estimated_records": {str(k): round(w[k]) for k in order},
    }


def _texts(m: Message, field: str) -> list[str | None]:
    return [getattr(i, field) for i in m.infos]


def _all_text(m: Message) -> str:
    return "\n".join(t for i in m.infos for f in TEXT_FIELDS if (t := getattr(i, f)))


def _same_code(m: Message) -> str | None:
    for i in m.infos:
        for p in i.event_codes:
            if p.name == "SAME" and p.value.strip():
                return p.value.strip().upper()
    return None


def _fingerprint(m: Message) -> str:
    text = " ".join(_all_text(m).lower().split())
    return hashlib.sha256(text.encode()).hexdigest()


def _lengths(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    values = sorted(values)
    return {
        "n": len(values),
        "mean": round(statistics.fmean(values), 1),
        "median": statistics.median(values),
        "p90": values[min(len(values) - 1, int(0.9 * len(values)))],
        "max": values[-1],
    }


def text_fields(rows: list[Row]) -> dict[str, Any]:
    """Per field and kind: how often it is missing or empty, and its length in characters."""
    out: dict[str, Any] = {}
    for kind in ("nws", "other"):
        part = [r for r in rows if r.message and r.kind == kind]
        total_w = sum(r.weight for r in part)
        out[kind] = {}
        for field in TEXT_FIELDS:
            missing_w = empty_w = 0.0
            lengths = []
            over_w = 0.0
            for r in part:
                values = _texts(r.message, field)
                present = [v for v in values if v is not None]
                if not present:
                    missing_w += r.weight
                elif not any(v.strip() for v in present):
                    empty_w += r.weight
                else:
                    longest = max(len(v.strip()) for v in present if v.strip())
                    lengths.append(longest)
                    if field in WEA_LIMITS and longest > WEA_LIMITS[field]:
                        over_w += r.weight
            out[kind][field] = {
                "missing_share": round(missing_w / total_w, 4) if total_w else None,
                "empty_share": round(empty_w / total_w, 4) if total_w else None,
                "length_chars": _lengths(lengths),
            }
            if field in WEA_LIMITS:
                out[kind][field]["over_limit_share"] = (
                    round(over_w / total_w, 4) if total_w else None
                )
    return out


def contacts(rows: list[Row]) -> dict[str, Any]:
    """Details about the senders' own staff: shapes and shares only, never the values."""
    out: dict[str, Any] = {}
    for kind in ("nws", "other"):
        part = [r for r in rows if r.message and r.kind == kind]
        total_w = sum(r.weight for r in part)
        tld: Counter = Counter()
        staff_w = contact_w = contact_detail_w = param_detail_w = 0.0
        email_like = 0.0
        for r in part:
            m = r.message
            sender = (m.sender or "").strip()
            if patterns.PATTERNS["email"].fullmatch(sender):
                email_like += r.weight
                tld[sender.rsplit(".", 1)[-1].lower()] += r.weight
            names = {p.name for i in m.infos for p in i.parameters}
            if names & STAFF_PARAMETERS:
                staff_w += r.weight
            other_values = " ".join(
                p.value
                for i in m.infos
                for p in i.parameters
                if p.name not in (cap.WEA_SHORT, cap.WEA_LONG)
            )
            found = patterns.count(other_values)
            if found["email"] or found["phone"]:
                param_detail_w += r.weight
            contact = " ".join(i.contact for i in m.infos if i.contact)
            if contact.strip():
                contact_w += r.weight
                found = patterns.count(contact)
                if found["email"] or found["phone"]:
                    contact_detail_w += r.weight

        def share(w: float, total: float = total_w) -> float | None:
            return round(w / total, 4) if total else None

        out[kind] = {
            "distinct_senders_in_sample": len({r.message.sender for r in part}),
            "distinct_cog_ids_in_sample": len({r.message.cog_id for r in part}),
            "sender_email_like_share": share(email_like),
            "sender_tld_share": _share(tld, email_like) if email_like else {},
            "staff_parameter_share": share(staff_w),
            "parameter_with_email_or_phone_share": share(param_detail_w),
            "contact_present_share": share(contact_w),
            "contact_with_email_or_phone_share": share(contact_detail_w),
        }
    return out


def duplicates(rows: list[Row]) -> dict[str, Any]:
    """Duplicates inside each sampled page (records next to each other in time).

    - ``same_identifier``: the same identifier twice (the same message archived twice);
    - ``same_text_other_identifier``: identical text under another identifier from the same
      sender (sent again, or once per channel or language);
    - ``same_sender_and_sent``: the same sender and sent time under another identifier.
    """
    out: dict[str, Any] = {}
    for kind in ("nws", "other"):
        pages: dict[tuple[int, int], list[Message]] = defaultdict(list)
        for r in rows:
            if r.message and r.kind == kind:
                pages[(r.year, r.page)].append(r.message)
        same_id = same_text = same_sent = records = 0
        for msgs in pages.values():
            records += len(msgs)
            ids = Counter(m.identifier for m in msgs)
            same_id += sum(c - 1 for c in ids.values() if c > 1)
            seen_text: dict[tuple, set] = defaultdict(set)
            seen_sent: dict[tuple, set] = defaultdict(set)
            for m in msgs:
                if _all_text(m):
                    seen_text[(m.sender, _fingerprint(m))].add(m.identifier)
                seen_sent[(m.sender, m.sent)].add(m.identifier)
            same_text += sum(len(v) - 1 for v in seen_text.values() if len(v) > 1)
            same_sent += sum(len(v) - 1 for v in seen_sent.values() if len(v) > 1)
        out[kind] = {
            "records": records,
            "pages": len(pages),
            "same_identifier": same_id,
            "same_text_other_identifier": same_text,
            "same_sender_and_sent": same_sent,
        }
    return out


def chains(rows: list[Row]) -> dict[str, Any]:
    """References: who carries them, how many, and whether they parse."""
    out: dict[str, Any] = {}
    for kind in ("nws", "other"):
        part = [r for r in rows if r.message and r.kind == kind]
        by_type: dict[str, dict[str, float]] = defaultdict(lambda: {"w": 0.0, "with_refs": 0.0})
        n_refs = Counter()
        unparsed = 0
        for r in part:
            m = r.message
            t = m.msg_type or "(missing)"
            by_type[t]["w"] += r.weight
            if m.references:
                by_type[t]["with_refs"] += r.weight
            n_refs[min(len(m.references), 5)] += 1
            unparsed += len(m.references_unparsed)
        out[kind] = {
            "share_with_references_by_type": {
                t: round(v["with_refs"] / v["w"], 4) for t, v in by_type.items() if v["w"]
            },
            "references_per_message_sample": {
                ("5+" if k == 5 else str(k)): v for k, v in sorted(n_refs.items())
            },
            "unparsed_references": unparsed,
        }
    return out


def people(rows: list[Row]) -> dict[str, Any]:
    """Alerts about people: shares by event code and personal-detail counts by pattern."""
    part = [r for r in rows if r.message]
    total_w = sum(r.weight for r in part)
    other_w = sum(r.weight for r in part if r.kind == "other")
    out: dict[str, Any] = {"codes": {}, "patterns": {}}
    groups = {**PEOPLE_CODES, **MAYBE_PEOPLE_CODES}
    for code in groups:
        sel = [r for r in part if _same_code(r.message) == code]
        w = sum(r.weight for r in sel)
        out["codes"][code] = {
            "name": groups[code],
            "sample_count": len(sel),
            "estimated_records": round(w),
            "share_of_archive": round(w / total_w, 5) if total_w else None,
            "share_of_non_nws": round(w / other_w, 4) if other_w else None,
        }
    selections = {
        "people_codes": lambda r: _same_code(r.message) in PEOPLE_CODES,
        "all_non_nws": lambda r: r.kind == "other",
        "non_nws_other_codes": lambda r: (
            r.kind == "other"
            and event_group(_same_code(r.message)) not in ("about_people", "test_or_demo")
        ),
    }
    for label, keep in selections.items():
        sel = [r for r in part if keep(r)]
        any_w: Counter = Counter()
        occurrences: Counter = Counter()
        for r in sel:
            found = patterns.count(_all_text(r.message))
            for name, n in found.items():
                occurrences[name] += n
                if n:
                    any_w[name] += r.weight
        sel_w = sum(r.weight for r in sel)
        out["patterns"][label] = {
            "sample_messages": len(sel),
            "share_with_pattern": {k: round(any_w[k] / sel_w, 4) for k in patterns.PATTERNS}
            if sel_w
            else {},
            "occurrences_in_sample": {k: occurrences[k] for k in patterns.PATTERNS},
        }
    return out


def structure(rows: list[Row]) -> dict[str, Any]:
    """Which parameters, geocodes and shapes the messages carry (names only), by kind."""
    out: dict[str, Any] = {}
    for kind in ("nws", "other"):
        part = [r.message for r in rows if r.message and r.kind == kind]
        n = len(part)
        params: Counter = Counter()
        geos: Counter = Counter()
        shapes: Counter = Counter()
        for m in part:
            params.update({p.name for i in m.infos for p in i.parameters})
            geos.update({g.name for i in m.infos for a in i.areas for g in a.geocodes})
            if any(a.polygons for i in m.infos for a in i.areas):
                shapes["polygon"] += 1
            if any(a.circles for i in m.infos for a in i.areas):
                shapes["circle"] += 1
            if m.signed:
                shapes["signed"] += 1
            if any(res.has_embedded_content for i in m.infos for res in i.resources):
                shapes["embedded_audio_or_file"] += 1
        out[kind] = {
            "messages": n,
            "parameter_names_share": _share(params, n),
            "geocode_names_share": _share(geos, n),
            "other_share": _share(shapes, n),
        }
    return out


def summarize(rows: list[Row]) -> dict[str, Any]:
    ok = [r for r in rows if r.message]
    m = lambda f: lambda r: f(r.message) if r.message else None  # noqa: E731
    out: dict[str, Any] = {
        "sample_records": len(rows),
        "parsed": len(ok),
        "parse_errors": dict(Counter(r.error for r in rows if r.error)),
        "problems": dict(Counter(p for r in ok for p in r.message.problems).most_common()),
        "kind": weighted(rows, lambda r: r.kind),
        "status": weighted(rows, m(lambda x: x.status)),
        "msg_type": weighted(rows, m(lambda x: x.msg_type)),
        "scope": weighted(rows, m(lambda x: x.scope)),
        "xmlns": weighted(rows, m(lambda x: x.xmlns)),
        "infos_per_message": weighted(rows, m(lambda x: min(len(x.infos), 3))),
        "languages": weighted(rows, m(lambda x: "+".join(sorted({i.language for i in x.infos})))),
        "language_element_given": weighted(
            rows, m(lambda x: all(i.language_given for i in x.infos))
        ),
        "channels": weighted(
            rows,
            m(
                lambda x: (
                    "+".join(n for n in ("wea", "eas", "nwem") if getattr(x.channels, n)) or "none"
                )
            ),
        ),
        "blocked": weighted(rows, m(lambda x: "+".join(x.channels.blocked) or "none")),
        "event_code_top30": {},
        "event_group": weighted(rows, m(lambda x: event_group(_same_code(x)))),
        "event_group_nws": weighted(
            [r for r in rows if r.kind == "nws"], m(lambda x: event_group(_same_code(x)))
        ),
        "event_group_other": weighted(
            [r for r in rows if r.kind == "other"], m(lambda x: event_group(_same_code(x)))
        ),
        "text_fields": text_fields(rows),
        "duplicates": duplicates(rows),
        "contacts": contacts(rows),
        "chains": chains(rows),
        "people": people(rows),
        "structure": structure(rows),
    }
    for label, sel in (
        ("all", ok),
        ("nws", [r for r in ok if r.kind == "nws"]),
        ("other", [r for r in ok if r.kind == "other"]),
        (
            "nws_from_2023_08",
            [r for r in ok if r.kind == "nws" and (r.message.sent or "") >= NWS_CUTOVER],
        ),
    ):
        codes = weighted(sel, lambda r: _same_code(r.message) or "(none)")
        top = list(codes["weighted_share"])[:30]
        out["event_code_top30"][label] = {
            k: {
                "weighted_share": codes["weighted_share"][k],
                "sample_count": codes["sample_count"][k],
            }
            for k in top
        }
    for kind in ("nws", "other"):
        sel = [r for r in rows if r.kind == kind]
        out[f"channels_{kind}"] = weighted(
            sel,
            m(
                lambda x: (
                    "+".join(n for n in ("wea", "eas", "nwem") if getattr(x.channels, n)) or "none"
                )
            ),
        )
        out[f"status_{kind}"] = weighted(sel, m(lambda x: x.status))
        out[f"msg_type_{kind}"] = weighted(sel, m(lambda x: x.msg_type))
        out[f"languages_{kind}"] = weighted(
            sel, m(lambda x: "+".join(sorted({i.language for i in x.infos})))
        )
    return out
