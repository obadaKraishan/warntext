"""Build the WarnText tables from the raw backfill, in two layers.

**The record layer** holds no message text: ``messages`` (one row per message), ``infos`` (one
row per language block), ``areas``, ``references`` and ``threads``. **The text layer** holds the
text, keyed by message id and language block, in two tables: ``text_federal`` for messages
from federal senders and ``text_other`` for everyone else (state, local, tribal, territorial,
other and unknown senders). Each table is written for two configurations: ``alerts`` (real
alerts) and ``tests`` (tests and demonstrations, and anything not sent as ``Actual``).

The unit is the message: archive copies (the same CAP sender, identifier and sent time) become
one row, whose ``message_id`` is the FEMA record id of its first copy; ``record_ids`` lists
them all. Every row carries the endpoint it came from (``source``) and a FEMA record id.

The raw ``sender`` value never reaches a table: the sender appears only as the alerting
authority, keyed by FEMA's identifier (``cog_id``), with its organization name and a sender kind.
There is no account key. Raw CAP identifiers never reach a table either: rows, references,
threads and text groups are keyed by FEMA's record ids. Raw sender values and identifiers are
written only to private files the release check reads.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from warntext import authorities as au
from warntext import backfill, cap, measures, patterns, privacy
from warntext import codes as cd
from warntext import senders as sd
from warntext.probe import ENDPOINT
from warntext.sample import NWS_SENDER
from warntext.schema import Info, Message

CONFIGS = ("alerts", "tests")
RECORD_TABLES = ("messages", "infos", "areas", "references", "threads", "codes")
TEXT_TABLES = ("text_federal", "text_other")
#: Fields of a language block measured for length and presence.
LENGTH_FIELDS = ("event", "headline", "description", "instruction", "web", "wea_short", "wea_long")

S = pa.string()
LS = pa.list_(pa.string())
INT = pa.int64()
B = pa.bool_()
F = pa.float64()
TS = pa.timestamp("ms", tz="UTC")

SCHEMAS: dict[str, pa.Schema] = {
    "messages": pa.schema(
        [
            ("message_id", S),
            ("record_id", S),
            ("record_ids", LS),
            ("archive_copies", INT),
            ("source", S),
            ("retrieved_at", S),
            ("config", S),
            ("sent", S),
            ("sent_utc", TS),
            ("year", INT),
            ("times_rounded", B),
            ("status", S),
            ("msg_type", S),
            ("scope", S),
            ("codes", LS),
            ("xmlns", S),
            ("signed", B),
            ("cog_id", INT),
            ("organization", S),
            ("organization_source", S),
            ("sender_kind", S),
            ("sender_kind_source", S),
            ("sender_kind_rule", S),
            ("authority_type", S),
            ("event_codes", LS),
            ("event_code", S),
            ("event_group", S),
            ("hazard", S),
            ("languages", LS),
            ("n_infos", INT),
            ("channel_wea", B),
            ("channel_eas", B),
            ("channel_nwem", B),
            ("channel_public", B),
            ("blocked_channels", LS),
            ("wea_handling", S),
            ("n_areas", INT),
            ("n_polygons", INT),
            ("n_circles", INT),
            ("same_geocodes", LS),
            ("states", LS),
            ("counties", LS),
            ("n_states", INT),
            ("n_counties", INT),
            ("references_count", INT),
            ("references_unparsed", INT),
            ("references_resolved", INT),
            ("thread_id", S),
            ("thread_position", INT),
            ("text_group", S),
            ("text_group_size", INT),
            ("text_withheld", S),
            ("withheld_patterns", LS),
            ("shapes_withheld", B),
            ("has_text", B),
            ("len_headline", INT),
            ("len_description", INT),
            ("len_instruction", INT),
            ("len_wea_short", INT),
            ("len_wea_long", INT),
            ("has_link", B),
            ("has_phone", B),
            ("caps_share", F),
            ("wea_short_over_limit", B),
            ("wea_long_over_limit", B),
            ("parameters_dropped", INT),
            ("contact_dropped", B),
            ("parse_ok", B),
            ("parse_problems", LS),
            ("crosscheck_mismatches", LS),
        ]
    ),
    "infos": pa.schema(
        [
            ("message_id", S),
            ("info_index", INT),
            ("record_id", S),
            ("source", S),
            ("language", S),
            ("language_given", B),
            ("categories", LS),
            ("response_types", LS),
            ("urgency", S),
            ("severity", S),
            ("certainty", S),
            ("event_code_names", LS),
            ("event_code_values", LS),
            ("effective", S),
            ("onset", S),
            ("expires", S),
            ("times_rounded", B),
            ("parameter_names", LS),
            ("parameter_values", LS),
            ("n_resources", INT),
            ("resource_mime_types", LS),
            ("resource_sizes", pa.list_(INT)),
            ("has_embedded_resource", B),
            ("n_areas", INT),
        ]
        + [(f"len_{f}", INT) for f in LENGTH_FIELDS]
        + [
            ("has_link", B),
            ("has_phone", B),
            ("caps_share", F),
        ]
    ),
    "areas": pa.schema(
        [
            ("message_id", S),
            ("info_index", INT),
            ("area_index", INT),
            ("record_id", S),
            ("source", S),
            ("n_polygons", INT),
            ("n_circles", INT),
            ("polygons", LS),
            ("circles", LS),
            ("shapes_withheld", B),
            ("geocode_names", LS),
            ("geocode_values", LS),
            ("altitude", S),
            ("ceiling", S),
        ]
    ),
    "references": pa.schema(
        [
            ("message_id", S),
            ("ref_index", INT),
            ("record_id", S),
            ("source", S),
            ("ref_sent", S),
            ("times_rounded", B),
            ("resolved", B),
            ("resolved_by", S),
            ("ref_message_id", S),
            ("ref_msg_type", S),
            ("ref_same_authority", B),
            ("ref_weather_service", B),
        ]
    ),
    "threads": pa.schema(
        [
            ("thread_id", S),
            ("record_id", S),
            ("source", S),
            ("first_sent_utc", TS),
            ("last_sent_utc", TS),
            ("times_rounded", B),
            ("n_messages", INT),
            ("n_alerts", INT),
            ("n_updates", INT),
            ("n_cancels", INT),
            ("shape", S),
            ("event_code", S),
            ("cog_id", INT),
            ("sender_kind", S),
            ("mixed_configs", B),
        ]
    ),
}
_CODE_TYPES = {"n_actions": INT, "n_abbreviations": INT, "link_kinds": LS}
_CODE_TYPES.update({"hazard_category": S, "hazard_category_source": S})
SCHEMAS["codes"] = pa.schema(
    [
        ("message_id", S),
        ("info_index", INT),
        ("unit", S),
        ("record_id", S),
        ("source", S),
        ("codebook_version", S),
        ("language", S),
        ("coded", B),
        ("not_coded_reason", S),
        ("length", INT),
        ("same_as_wea90", B),
    ]
    + [(f, _CODE_TYPES.get(f, B)) for f in cd.CODE_FIELDS]
)
_TEXT_SCHEMA = pa.schema(
    [
        ("message_id", S),
        ("info_index", INT),
        ("record_id", S),
        ("source", S),
        ("retrieved_at", S),
        ("sender_kind", S),
        ("language", S),
        ("event", S),
        ("headline", S),
        ("description", S),
        ("instruction", S),
        ("web", S),
        ("audience", S),
        ("wea_short", S),
        ("wea_long", S),
        ("text_parameter_names", LS),
        ("text_parameter_values", LS),
        ("area_descriptions", LS),
        ("resource_descriptions", LS),
        ("resource_uris", LS),
    ]
)
SCHEMAS["text_federal"] = _TEXT_SCHEMA
SCHEMAS["text_other"] = _TEXT_SCHEMA
#: The private table of the exact times of messages with a people code (never released).
PEOPLE_TIMES_SCHEMA = pa.schema(
    [("message_id", S), ("table", S), ("index", INT), ("field", S), ("value", S)]
)


# --- small helpers -----------------------------------------------------------------------


def _utc(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _strip(value: str | None) -> str:
    return (value or "").strip()


def triple(sender: str | None, identifier: str | None, sent: str | None) -> tuple[str, str, str]:
    return (_strip(sender), _strip(identifier), _strip(sent))


def same_codes(m: Message | None) -> list[str]:
    """The message's SAME event codes, in order, without repeats."""
    if m is None:
        return []
    out: list[str] = []
    for i in m.infos:
        for p in i.event_codes:
            v = p.value.strip().upper()
            if p.name.strip().upper() == "SAME" and v and v not in out:
                out.append(v)
    return out


def text_of(m: Message) -> str:
    """Every text field of the message, joined, for fingerprints. Never written out."""
    parts = []
    for i in m.infos:
        parts += [getattr(i, f) or "" for f in ("headline", "description", "instruction")]
        parts += [i.wea_short or "", i.wea_long or ""]
        parts += [p.value for p in i.parameters if privacy.is_text_parameter(p.name)]
    return " ".join(" ".join(parts).lower().split())


def fingerprint(m: Message | None) -> str | None:
    if m is None:
        return None
    text = text_of(m)
    return hashlib.sha256(text.encode()).hexdigest() if text else None


_EMAIL = patterns.PATTERNS["email"]


_ORG_WORDS = re.compile(
    r"\b(emergency|management|office|department|dept|agency|alert|warning|services?|center|"
    r"authority|commission|district|division|bureau|council|ema|oem|eoc|county|city|state|"
    r"police|sheriff|fire|safety|security|government|public|national|service|operations|"
    r"administration|program|system|network|team|unit|command|base|park|university|college)\b",
    re.IGNORECASE,
)
_PERSON_NAME = re.compile(r"^[A-Z][a-z]+(\s[A-Z]\.?)?\s[A-Z][a-z'-]+$")


_ACRONYM = re.compile(r"^[A-Z][A-Z0-9&-]{1,11}$")


def org_name_check(name: str, raw_senders: set[str], official: bool = False) -> str | None:
    """Why an organization name may not be released (a reason), or None when it may.

    A name must look like an organization's: it holds an organization word (office, county,
    police, emergency ...), a word the sender-kind rule reads, or it is one acronym. A name
    shaped like a person's ("Jane Doe", "Sgt. Jane Doe") is never released. An ``official``
    name (from FEMA's list of alerting authorities) needs no organization word, since the list
    itself says it is an organization; every other check still applies.
    """
    if not 3 <= len(name) <= 120:
        return "length"
    if "@" in name or _EMAIL.search(name) or patterns.PATTERNS["phone"].search(name):
        return "address_or_number"
    if name.casefold() in raw_senders:
        return "equals_a_sender_value"
    if _PERSON_NAME.match(name) and not _ORG_WORDS.search(name):
        return "person_shaped"
    if official:
        return None
    organization_like = (
        _ORG_WORDS.search(name)
        or sd.kind_from_name(name) is not None
        or sd.weak_kind_from_name(name) is not None
        or _ACRONYM.match(name)
    )
    if not organization_like:
        return "no_organization_word"
    return None


# --- parsing -----------------------------------------------------------------------------


@dataclass
class Parsed:
    """One archive record after parsing. ``message`` is None when the XML cannot be read."""

    record_id: str
    retrieved_at: str
    sent_utc: str
    sender: str
    identifier: str
    sent: str
    status: str | None
    msg_type: str | None
    scope: str | None
    cog_id: int | None
    message: Message | None
    error: str | None
    mismatches: list[str]


def error_kind(exc: Exception) -> str:
    text = str(exc)
    if "is empty" in text:
        return "empty"
    if "not well-formed" in text:
        return "not_well_formed"
    if "refused for safety" in text:
        return "refused_xml_feature"
    if "root element" in text:
        return "wrong_root"
    return "other"


def crosscheck(m: Message, rec: Mapping[str, Any]) -> list[str]:
    """OpenFEMA's fields that disagree with what the parser read from the XML."""
    out = []
    for ours, theirs in (
        ("identifier", "identifier"),
        ("sender", "sender"),
        ("status", "status"),
        ("msg_type", "msgType"),
        ("scope", "scope"),
    ):
        if (getattr(m, ours) or "") != (rec.get(theirs) or ""):
            out.append(theirs)
    a, b = _utc(m.sent), _utc(rec.get("sent"))
    if a is None or b is None or abs((a - b).total_seconds()) > 1:
        out.append("sent_utc")
    ours_codes = sorted(p.value for i in m.infos for p in i.event_codes)
    theirs_codes = sorted(
        str(d.get("value")) for i in (rec.get("info") or []) for d in (i.get("eventCode") or [])
    )
    if ours_codes != theirs_codes:
        out.append("eventCode")
    if len(m.infos) != len(rec.get("info") or []):
        out.append("info_count")
    return out


def parse_one(rec: Mapping[str, Any], retrieved_at: str) -> Parsed:
    cog = rec.get("cogId")
    try:
        m = cap.parse_record(rec)
        error, mismatches = None, crosscheck(m, rec)
    except cap.CapParseError as exc:
        m, error, mismatches = None, error_kind(exc), []
    src = m
    return Parsed(
        record_id=str(rec.get("id")),
        retrieved_at=retrieved_at,
        sent_utc=rec.get("sent") or "",
        sender=(src.sender if src else rec.get("sender")) or "",
        identifier=(src.identifier if src else rec.get("identifier")) or "",
        sent=(src.sent if src else rec.get("sent")) or "",
        status=src.status if src else rec.get("status"),
        msg_type=src.msg_type if src else rec.get("msgType"),
        scope=src.scope if src else rec.get("scope"),
        cog_id=cog if isinstance(cog, int) else None,
        message=m,
        error=error,
        mismatches=mismatches,
    )


def parse_records(items: Iterable[tuple[Any, Mapping[str, Any]]]) -> list[Parsed]:
    """Parse ``(manifest_line, record)`` pairs; each line gives the retrieval time."""
    return [parse_one(rec, line.fetched_at) for line, rec in items]


# --- the build ---------------------------------------------------------------------------


@dataclass
class Unit:
    """One message: its first archive copy, the other copies' ids, and what the rules gave."""

    first: Parsed
    record_ids: list[str]
    message_id: str = ""
    codes: list[str] = field(default_factory=list)
    group: str = "none"
    config: str = "alerts"
    kind: str = "unknown"
    kind_source: str = "none"
    by_name: str | None = None
    by_domain: str | None = None
    organization: str | None = None
    organization_source: str | None = None
    kind_rule: str = "unknown"
    authority_type: str | None = None
    withheld: str | None = None
    hits: list[str] = field(default_factory=list)
    text_group: str | None = None
    text_group_size: int | None = None
    thread_id: str | None = None
    thread_position: int | None = None


def _union_find(ids: Iterable[str]) -> tuple[dict[str, str], Any, Any]:
    parent = {i: i for i in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    return parent, find, union


def thread_shape(types: Counter) -> str:
    alerts, updates, cancels = types["Alert"], types["Update"], types["Cancel"]
    n = sum(types.values())
    if alerts == 0:
        return "no_alert"
    if updates == 0 and cancels == 0:
        return "alert_only" if n == 1 else "alerts_only"
    if updates == 0:
        return "alert_and_cancel"
    if cancels == 0:
        return "alert_and_updates"
    return "alert_updates_and_cancel"


@dataclass
class Build:
    units: list[Unit]
    tables: dict[str, dict[str, list[dict]]]
    summary: dict[str, Any]
    raw_senders: list[dict[str, Any]]
    #: Raw CAP identifiers (of messages and of the messages they reference). They are never
    #: released: rows are keyed by FEMA's record id. The release check reads them to make sure.
    raw_identifiers: list[str] = field(default_factory=list)
    #: The exact times that the record layer rounds down to the hour for messages with a people
    #: code. Private: written next to the raw sender values, never released.
    people_times: list[dict[str, Any]] = field(default_factory=list)


def _primary(m: Message) -> Info | None:
    for i in m.infos:
        if i.language.lower().startswith("en"):
            return i
    return m.infos[0] if m.infos else None


def info_measure_texts(i: Info) -> list[str | None]:
    out = [i.headline, i.description, i.instruction, i.wea_short, i.wea_long]
    out += [p.value for p in i.parameters if privacy.is_text_parameter(p.name)]
    return out


def text_row(u: Unit, i: Info, index: int) -> dict[str, Any]:
    """One text-layer row for a language block."""
    text_params = [p for p in i.parameters if privacy.is_text_parameter(p.name)]
    text_params = [p for p in text_params if p.name not in ("CMAMtext", "CMAMlongtext")]
    return {
        "message_id": u.message_id,
        "info_index": index,
        "record_id": u.first.record_id,
        "source": ENDPOINT,
        "retrieved_at": u.first.retrieved_at,
        "sender_kind": u.kind,
        "language": i.language,
        "event": i.event,
        "headline": i.headline,
        "description": i.description,
        "instruction": i.instruction,
        "web": i.web,
        "audience": i.audience,
        "wea_short": i.wea_short,
        "wea_long": i.wea_long,
        "text_parameter_names": [p.name for p in text_params],
        "text_parameter_values": [p.value for p in text_params],
        "area_descriptions": [a.description or "" for a in i.areas],
        "resource_descriptions": [r.description or "" for r in i.resources],
        "resource_uris": [r.uri or "" for r in i.resources],
    }


def fema_summary(units: list[Unit], fema: Mapping[int, au.Authority]) -> dict[str, Any]:
    """How the archive's authorities meet FEMA's list, and how often the two kinds agree."""
    first: dict[int, Unit] = {}
    msgs: Counter = Counter()
    real: Counter = Counter()
    for u in units:
        if u.first.cog_id is None:
            continue
        first.setdefault(u.first.cog_id, u)
        msgs[u.first.cog_id] += 1
        real[u.first.cog_id] += u.config == "alerts"
    listed = [c for c in first if c in fema]
    cross: Counter = Counter()
    cross_real: Counter = Counter()
    for c in listed:
        key = f"{fema[c].type}->{first[c].kind_rule}"
        cross[key] += 1
        cross_real[key] += real[c]
    agree = [c for c in listed if fema[c].kind == first[c].kind_rule]
    real_listed = sum(real[c] for c in listed)
    return {
        "snapshot": {
            "page": au.PAGE_URL,
            "page_last_updated": au.SNAPSHOT_PAGE_UPDATED,
            "retrieved": au.SNAPSHOT_RETRIEVED,
            "authorities_listed": len(fema),
            "by_type": dict(Counter(a.type for a in fema.values())),
        },
        "archive_authorities": len(first),
        "archive_authorities_listed": len(listed),
        "messages_listed": sum(msgs[c] for c in listed),
        "messages": sum(msgs.values()),
        "real_alerts_listed": real_listed,
        "real_alerts": sum(real.values()),
        "kind_agrees_authorities": len(agree),
        "kind_agrees_real_alerts": sum(real[c] for c in agree),
        "fema_type_to_rule_kind_authorities": dict(cross.most_common()),
        "fema_type_to_rule_kind_real_alerts": dict(cross_real.most_common()),
    }


def _people(u: Unit) -> bool:
    """Whether a message's times are rounded to the hour: it carries a people code."""
    return u.withheld == "people_code"


def _exact(message_id: str, table: str, index: int | None, name: str, value: str) -> dict:
    return {"message_id": message_id, "table": table, "index": index, "field": name, "value": value}


def _info_times(u: Unit, k: int, i: Info, people_times: list[dict]) -> dict[str, Any]:
    """A language block's times, rounded to the hour (exact values kept privately) for people."""
    out: dict[str, Any] = {"times_rounded": _people(u)}
    for name in ("effective", "onset", "expires"):
        value = getattr(i, name)
        if _people(u) and value:
            people_times.append(_exact(u.message_id, "infos", k, name, value))
            value = privacy.hour_floor(value)
        out[name] = value
    return out


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().split())


def code_rows(u: Unit, i: Info, k: int) -> list[dict[str, Any]]:
    """The codes of one language block's units (record layer: codes only, never text).

    Units are the 90-character phone text, the 360-character phone text and the full text
    (headline, description, instruction); a unit the block does not have gets no row.
    """
    spanish = i.language.lower().startswith("es")
    texts = {
        "wea90": i.wea_short,
        "wea360": i.wea_long,
        "full": cd.full_text(i.headline, i.description, i.instruction),
    }
    ctx = cd.Context(
        organization=u.organization,
        place_words=cd.place_words_of(a.description for a in i.areas),
        event_codes=tuple(u.codes),
        block_text="\n".join(t for t in texts.values() if t and t.strip()),
    )
    rows = []
    for unit, text in texts.items():
        if not text or not text.strip():
            continue
        c = cd.code_unit(unit, text, ctx, spanish=spanish)
        row = {
            "message_id": u.message_id,
            "info_index": k,
            "unit": unit,
            "record_id": u.first.record_id,
            "source": ENDPOINT,
            "codebook_version": cd.CODEBOOK_VERSION,
            "language": i.language,
            "coded": c.coded,
            "not_coded_reason": c.not_coded_reason,
            "length": c.length,
            "same_as_wea90": (
                _norm(text) == _norm(i.wea_short) if unit == "wea360" and i.wea_short else None
            ),
        }
        row.update({f: c.values.get(f) for f in cd.CODE_FIELDS})
        rows.append(row)
    return rows


def text_table_for(kind: str) -> str:
    return "text_federal" if kind == "federal" else "text_other"


def build(
    parsed: list[Parsed],
    overrides: Mapping[int, sd.Override] | None = None,
    fema: Mapping[int, au.Authority] | None = None,
) -> Build:
    """Apply every rule to the parsed records and return the rows of every table.

    ``overrides`` are the hand overrides by alerting authority, and ``fema`` is FEMA's list of
    alerting authorities; by default both are the tracked files shipped with the package
    (:func:`warntext.senders.load_overrides`, :func:`warntext.authorities.load`).
    """
    overrides = sd.load_overrides() if overrides is None else overrides
    fema = au.load() if fema is None else fema
    summary: dict[str, Any] = {"records": len(parsed)}

    # Parse errors and the cross-check, per record.
    summary["parse_errors_by_kind"] = dict(Counter(p.error for p in parsed if p.error))
    summary["crosscheck_records"] = sum(1 for p in parsed if p.message is not None)
    summary["crosscheck_mismatches_by_field"] = dict(
        Counter(f for p in parsed for f in p.mismatches)
    )
    summary["parse_problems"] = dict(
        Counter(
            re.sub(r"\d+", "N", prob)
            for p in parsed
            if p.message is not None
            for prob in p.message.problems
        )
    )

    # Archive copies: one unit per CAP triple, in archive order (sent, then id).
    units_by_triple: dict[tuple[str, str, str], Unit] = {}
    for p in parsed:
        key = triple(p.sender, p.identifier, p.sent)
        if key in units_by_triple:
            units_by_triple[key].record_ids.append(p.record_id)
        else:
            units_by_triple[key] = Unit(first=p, record_ids=[p.record_id])
    units = list(units_by_triple.values())
    for u in units:
        u.message_id = u.first.record_id
    copies = Counter(len(u.record_ids) for u in units)
    summary["messages"] = len(units)
    summary["archive_copies"] = {
        "messages_with_copies": sum(n for k, n in copies.items() if k > 1),
        "extra_records": sum((k - 1) * n for k, n in copies.items()),
        "copies_per_message": {str(k): n for k, n in sorted(copies.items())},
    }

    # Codes, groups and configurations.
    for u in units:
        m = u.first.message
        u.codes = same_codes(m)
        u.group = measures.event_group(u.codes)
        not_actual = (u.first.status or "") != "Actual"
        u.config = "tests" if u.group == "test_or_demo" or not_actual else "alerts"

    # Sender kinds, pooled by alerting authority.
    ev = {}
    for u in units:
        m = u.first.message
        names = [i.sender_name for i in m.infos] if m else []
        geos = [
            g.value.strip()
            for i in (m.infos if m else ())
            for a in i.areas
            for g in a.geocodes
            if g.name.strip().upper() == "SAME"
        ]
        _, counties = measures.places(geos)
        whole = any(re.fullmatch(r"\d{3}000", g) for g in geos)
        area = sd.footprint(len(counties), whole)
        ev[u.message_id] = sd.evidence(u.first.sender, names, area)
    authorities = sd.pool((u.first.cog_id, u.message_id, ev[u.message_id]) for u in units)
    for u in units:
        a = authorities[u.message_id]
        u.kind, u.kind_source, u.kind_rule = a.kind, a.source, a.kind
        u.by_name, u.by_domain = ev[u.message_id].by_name, ev[u.message_id].by_domain
    # FEMA's list of alerting authorities: its type is the first evidence for the kind.
    for u in units:
        listed = fema.get(u.first.cog_id) if u.first.cog_id is not None else None
        if listed is not None:
            u.authority_type = listed.type
            if listed.kind is not None:
                u.kind, u.kind_source = listed.kind, "fema_list"
    summary["fema_list"] = fema_summary(units, fema)
    # Hand overrides, by authority: the only exception to "by rule".
    touched: Counter = Counter()
    for u in units:
        o = overrides.get(u.first.cog_id) if u.first.cog_id is not None else None
        if o is not None:
            touched[(o.cog_id, u.kind, o.kind)] += 1
            u.kind, u.kind_source = o.kind, "override"
    changes: Counter = Counter()
    for (_, rule_kind, hand_kind), n in touched.items():
        changes[f"{rule_kind}->{hand_kind}"] += n
    summary["kind_overrides"] = {
        "authorities_listed": len(overrides),
        "authorities_seen": len({k[0] for k in touched}),
        "messages": sum(touched.values()),
        "kind_before_to_override_kind": dict(changes),
    }

    # Organization names, by authority.
    raw_sender_set = {u.first.sender.casefold() for u in units if u.first.sender}
    names_by_group: dict[str, Counter] = defaultdict(Counter)
    rejected: Counter = Counter()
    for u in units:
        gkey = f"cog:{u.first.cog_id}" if u.first.cog_id is not None else f"msg:{u.message_id}"
        m = u.first.message
        for i in m.infos if m else ():
            if i.sender_name and i.sender_name.strip():
                names_by_group[gkey][" ".join(i.sender_name.split())] += 1
                break
    chosen: dict[str, str | None] = {}
    for gkey, counter in names_by_group.items():
        chosen[gkey] = None
        for name, _ in counter.most_common():
            reason = org_name_check(name, raw_sender_set)
            if reason is None:
                chosen[gkey] = name
                break
            rejected[reason] += 1
    official_refused: Counter = Counter()
    for u in units:
        gkey = f"cog:{u.first.cog_id}" if u.first.cog_id is not None else f"msg:{u.message_id}"
        u.organization = chosen.get(gkey)
        u.organization_source = "sender_name" if u.organization else None
        listed = fema.get(u.first.cog_id) if u.first.cog_id is not None else None
        if listed is not None:
            reason = org_name_check(listed.name, raw_sender_set, official=True)
            if reason is None:
                u.organization, u.organization_source = listed.name, "fema_list"
            else:
                official_refused[reason] += 1
        o = overrides.get(u.first.cog_id) if u.first.cog_id is not None else None
        if o is not None and o.organization:
            reason = org_name_check(o.organization, raw_sender_set)
            if reason is not None:
                raise ValueError(
                    f"{sd.OVERRIDES_FILE}: the organization name for cog_id {o.cog_id} is "
                    f"refused ({reason}); give the organization's official name."
                )
            u.organization, u.organization_source = o.organization, "override"
    summary["organization_names"] = {
        "authorities": len({k for k in names_by_group if k.startswith("cog:")}),
        "authorities_with_a_name": sum(1 for k, v in chosen.items() if k.startswith("cog:") and v),
        "candidate_names_rejected_by_reason": dict(rejected),
        "messages_without_organization": sum(1 for u in units if not u.organization),
        "messages_by_name_source": dict(Counter(u.organization_source for u in units)),
        "fema_names_refused_messages_by_reason": dict(official_refused),
    }

    # The people rule.
    for u in units:
        m = u.first.message
        if m is None:
            u.withheld, u.hits = "unparsed", []
        else:
            u.withheld, u.hits = privacy.withheld(m)

    # Re-sends: the same text from the same sender under another identifier.
    groups: dict[tuple[str, str], list[Unit]] = defaultdict(list)
    for u in units:
        fp = fingerprint(u.first.message)
        if fp:
            groups[(u.first.sender, fp)].append(u)
    for members in groups.values():
        for u in members:
            u.text_group = members[0].message_id
            u.text_group_size = len(members)
    sizes = Counter(len(v) for v in groups.values())
    summary["text_groups"] = {
        "messages_with_text": sum(len(v) for v in groups.values()),
        "groups": len(groups),
        "groups_of_2_or_more": sum(n for k, n in sizes.items() if k > 1),
        "messages_in_groups_of_2_or_more": sum(k * n for k, n in sizes.items() if k > 1),
        "largest_group": max(sizes) if sizes else 0,
        "by_event_group": dict(Counter(u.group for v in groups.values() if len(v) > 1 for u in v)),
    }
    ident_reuse = Counter((u.first.sender, u.first.identifier) for u in units)
    summary["identifier_reused_with_another_sent_time"] = sum(
        n for n in ident_reuse.values() if n > 1
    )

    # References and threads.
    exact = {triple(u.first.sender, u.first.identifier, u.first.sent): u for u in units}
    by_utc: dict[tuple[str, str, float], Unit] = {}
    by_ident: dict[tuple[str, str], list[Unit]] = defaultdict(list)
    for u in units:
        t = _utc(u.first.sent)
        if t is not None:
            by_utc[(_strip(u.first.sender), _strip(u.first.identifier), t.timestamp())] = u
        by_ident[(_strip(u.first.sender), _strip(u.first.identifier))].append(u)
    ref_rows: list[dict] = []
    people_times: list[dict[str, Any]] = []
    resolved_pairs: list[tuple[str, str]] = []
    ref_stats: Counter = Counter()
    by_id = {u.message_id: u for u in units}
    for u in units:
        m = u.first.message
        for k, ref in enumerate(m.references if m else ()):
            key = triple(ref.sender, ref.identifier, ref.sent)
            weather = key[0].lower() == NWS_SENDER
            target, how = exact.get(key), "exact"
            if target is None:
                t = _utc(ref.sent)
                target = by_utc.get((key[0], key[1], t.timestamp())) if t else None
                how = "same_time_other_form"
            if target is None:
                cands = by_ident.get((key[0], key[1]), [])
                target = cands[0] if len(cands) == 1 else None
                how = "sender_and_identifier"
            if target is not None and target.message_id == u.message_id:
                target, how = None, "self"
            if target is None:
                if how != "self":
                    how = "weather_service" if weather else "not_in_archive"
                ref_stats[f"unresolved:{how}"] += 1
            else:
                ref_stats[how] += 1
                resolved_pairs.append((u.message_id, target.message_id))
            ref_people = _people(u) or (target is not None and _people(target))
            if ref_people and ref.sent:
                people_times.append(_exact(u.message_id, "references", k, "ref_sent", ref.sent))
            ref_rows.append(
                {
                    "message_id": u.message_id,
                    "ref_index": k,
                    "record_id": u.first.record_id,
                    "source": ENDPOINT,
                    "ref_sent": privacy.hour_floor(ref.sent) if ref_people else ref.sent,
                    "times_rounded": ref_people,
                    "resolved": target is not None,
                    "resolved_by": how if target is not None else None,
                    "ref_message_id": target.message_id if target else None,
                    "ref_msg_type": target.first.msg_type if target else None,
                    "ref_same_authority": (
                        target.first.cog_id == u.first.cog_id if target else None
                    ),
                    "ref_weather_service": weather,
                }
            )
    summary["references"] = {
        "messages_with_references": sum(
            1 for u in units if u.first.message and u.first.message.references
        ),
        "references": len(ref_rows),
        "by_resolution": dict(ref_stats),
        "unparsed_entries": sum(
            len(u.first.message.references_unparsed) for u in units if u.first.message
        ),
    }
    _, find, union = _union_find(by_id)
    for a, b in resolved_pairs:
        union(a, b)
    members: dict[str, list[Unit]] = defaultdict(list)
    for u in units:
        members[find(u.message_id)].append(u)
    thread_rows: dict[str, list[dict]] = {c: [] for c in CONFIGS}
    shapes: Counter = Counter()
    shapes_alerts: Counter = Counter()
    for group in members.values():
        group.sort(key=lambda x: (x.first.sent_utc, x.message_id))
        tid = group[0].message_id
        for pos, u in enumerate(group):
            u.thread_id, u.thread_position = tid, pos
        types = Counter(u.first.msg_type for u in group)
        shape = thread_shape(types)
        shapes[shape] += 1
        configs = {u.config for u in group}
        if group[0].config == "alerts":
            shapes_alerts[shape] += 1
        first_t, last_t = _utc(group[0].first.sent_utc), _utc(group[-1].first.sent_utc)
        thread_people = any(_people(x) for x in group)
        if thread_people:
            first_t, last_t = privacy.hour_floor_utc(first_t), privacy.hour_floor_utc(last_t)
        row = {
            "thread_id": tid,
            "record_id": group[0].first.record_id,
            "source": ENDPOINT,
            "first_sent_utc": first_t,
            "last_sent_utc": last_t,
            "times_rounded": thread_people,
            "n_messages": len(group),
            "n_alerts": types["Alert"],
            "n_updates": types["Update"],
            "n_cancels": types["Cancel"],
            "shape": shape,
            "event_code": group[0].codes[0] if group[0].codes else None,
            "cog_id": group[0].first.cog_id,
            "sender_kind": group[0].kind,
            "mixed_configs": len(configs) > 1,
        }
        thread_rows[group[0].config].append(row)
    summary["threads"] = {
        "threads": len(members),
        "shapes": dict(shapes),
        "shapes_real_alerts": dict(shapes_alerts),
        "threads_of_2_or_more": sum(1 for g in members.values() if len(g) > 1),
        "mixed_configs": sum(1 for g in members.values() if len({u.config for u in g}) > 1),
        "largest": max(len(g) for g in members.values()) if members else 0,
    }

    # Rows.
    resolved_by_message = Counter(r["message_id"] for r in ref_rows if r["resolved"])
    tables: dict[str, dict[str, list[dict]]] = {
        c: {t: [] for t in RECORD_TABLES + TEXT_TABLES} for c in CONFIGS
    }
    for c in CONFIGS:
        tables[c]["threads"] = thread_rows[c]
    for row in ref_rows:
        tables[by_id[row["message_id"]].config]["references"].append(row)
    params_kept: Counter = Counter()
    params_dropped: Counter = Counter()
    params_text: Counter = Counter()
    dropped_message_fields: Counter = Counter()
    for u in units:
        t = tables[u.config]
        m = u.first.message
        withheld = u.withheld is not None
        if m is not None:
            for name in ("note", "source", "addresses", "restriction", "incidents"):
                if getattr(m, name):
                    dropped_message_fields[name] += 1
        infos = m.infos if m else ()
        n_dropped = 0
        contact = False
        geos: list[str] = []
        n_areas = n_polys = n_circles = 0
        wea_handling = None
        for k, i in enumerate(infos):
            kept, text_params, dropped = privacy.split_parameters(i.parameters)
            params_kept.update(p.name for p in kept)
            params_text.update(p.name for p in text_params)
            params_dropped.update(dropped)
            n_dropped += len(dropped)
            contact = contact or bool(i.contact)
            if i.audience:
                dropped_message_fields["audience (text layer)"] += 1
            for p in kept:
                if p.name == "WEAHandling" and wea_handling is None:
                    wea_handling = p.value
            texts = info_measure_texts(i)
            row = {
                "message_id": u.message_id,
                "info_index": k,
                "record_id": u.first.record_id,
                "source": ENDPOINT,
                "language": i.language,
                "language_given": i.language_given,
                "categories": list(i.categories),
                "response_types": list(i.response_types),
                "urgency": i.urgency,
                "severity": i.severity,
                "certainty": i.certainty,
                "event_code_names": [p.name for p in i.event_codes],
                "event_code_values": [p.value for p in i.event_codes],
                **_info_times(u, k, i, people_times),
                "parameter_names": [p.name for p in kept],
                "parameter_values": [p.value for p in kept],
                "n_resources": len(i.resources),
                "resource_mime_types": [r.mime_type or "" for r in i.resources],
                "resource_sizes": [r.size for r in i.resources],
                "has_embedded_resource": any(r.has_embedded_content for r in i.resources),
                "n_areas": len(i.areas),
                "has_link": measures.has_link([*texts, i.web]),
                "has_phone": measures.has_phone(texts),
                "caps_share": measures.caps_share(texts),
            }
            for f in LENGTH_FIELDS:
                row[f"len_{f}"] = measures.length(getattr(i, f))
            t["infos"].append(row)
            for j, a in enumerate(i.areas):
                n_areas += 1
                n_polys += len(a.polygons)
                n_circles += len(a.circles)
                geos += [g.value.strip() for g in a.geocodes if g.name.strip().upper() == "SAME"]
                t["areas"].append(
                    {
                        "message_id": u.message_id,
                        "info_index": k,
                        "area_index": j,
                        "record_id": u.first.record_id,
                        "source": ENDPOINT,
                        "n_polygons": len(a.polygons),
                        "n_circles": len(a.circles),
                        "polygons": None if withheld else list(a.polygons),
                        "circles": None if withheld else list(a.circles),
                        "shapes_withheld": withheld and bool(a.polygons or a.circles),
                        "geocode_names": [g.name for g in a.geocodes],
                        "geocode_values": [g.value for g in a.geocodes],
                        "altitude": a.altitude,
                        "ceiling": a.ceiling,
                    }
                )
            if not withheld:
                t[text_table_for(u.kind)].append(text_row(u, i, k))
            if u.config == "alerts":
                t["codes"].extend(code_rows(u, i, k))
        same_geos = sorted(set(geos))
        states, counties = measures.places(same_geos)
        p = _primary(m) if m else None
        ptexts = info_measure_texts(p) if p else []
        resolved = resolved_by_message[u.message_id]
        sent_utc = _utc(u.first.sent_utc)
        sent = u.first.sent or None
        rounded = _people(u)
        if rounded:
            if sent:
                people_times.append(_exact(u.message_id, "messages", None, "sent", sent))
            if sent_utc is not None:
                people_times.append(
                    _exact(u.message_id, "messages", None, "sent_utc", u.first.sent_utc)
                )
            sent, sent_utc_out = privacy.hour_floor(sent), privacy.hour_floor_utc(sent_utc)
        else:
            sent_utc_out = sent_utc
        t["messages"].append(
            {
                "message_id": u.message_id,
                "record_id": u.first.record_id,
                "record_ids": list(u.record_ids),
                "archive_copies": len(u.record_ids),
                "source": ENDPOINT,
                "retrieved_at": u.first.retrieved_at,
                "config": u.config,
                "sent": sent,
                "sent_utc": sent_utc_out,
                "year": sent_utc.year if sent_utc else None,
                "times_rounded": rounded,
                "status": u.first.status,
                "msg_type": u.first.msg_type,
                "scope": u.first.scope,
                "codes": list(m.codes) if m else [],
                "xmlns": m.xmlns if m else None,
                "signed": m.signed if m else None,
                "cog_id": u.first.cog_id,
                "organization": u.organization,
                "organization_source": u.organization_source,
                "sender_kind": u.kind,
                "sender_kind_source": u.kind_source,
                "sender_kind_rule": u.kind_rule,
                "authority_type": u.authority_type,
                "event_codes": u.codes,
                "event_code": u.codes[0] if u.codes else None,
                "event_group": u.group,
                "hazard": measures.hazard(u.codes[0]) if u.codes else None,
                "languages": [i.language for i in infos],
                "n_infos": len(infos),
                "channel_wea": m.channels.wea if m else None,
                "channel_eas": m.channels.eas if m else None,
                "channel_nwem": m.channels.nwem if m else None,
                "channel_public": m.channels.public if m else None,
                "blocked_channels": list(m.channels.blocked) if m else [],
                "wea_handling": wea_handling,
                "n_areas": n_areas,
                "n_polygons": n_polys,
                "n_circles": n_circles,
                "same_geocodes": same_geos,
                "states": states,
                "counties": counties,
                "n_states": len(states),
                "n_counties": len(counties),
                "references_count": len(m.references) if m else 0,
                "references_unparsed": len(m.references_unparsed) if m else 0,
                "references_resolved": resolved,
                "thread_id": u.thread_id,
                "thread_position": u.thread_position,
                "text_group": u.text_group,
                "text_group_size": u.text_group_size,
                "text_withheld": u.withheld,
                "withheld_patterns": list(u.hits),
                "shapes_withheld": withheld and (n_polys + n_circles) > 0,
                "has_text": bool(text_of(m)) if m else False,
                "len_headline": measures.length(p.headline) if p else None,
                "len_description": measures.length(p.description) if p else None,
                "len_instruction": measures.length(p.instruction) if p else None,
                "len_wea_short": measures.length(p.wea_short) if p else None,
                "len_wea_long": measures.length(p.wea_long) if p else None,
                "has_link": measures.has_link(ptexts + ([p.web] if p else [])),
                "has_phone": measures.has_phone(ptexts),
                "caps_share": measures.caps_share(ptexts),
                "wea_short_over_limit": (
                    (len(p.wea_short) > measures.WEA_LIMITS["wea_short"])
                    if p and p.wea_short is not None
                    else None
                ),
                "wea_long_over_limit": (
                    (len(p.wea_long) > measures.WEA_LIMITS["wea_long"])
                    if p and p.wea_long is not None
                    else None
                ),
                "parameters_dropped": n_dropped,
                "contact_dropped": contact,
                "parse_ok": m is not None,
                "parse_problems": list(m.problems) if m else [f"unparsed: {u.first.error}"],
                "crosscheck_mismatches": list(u.first.mismatches),
            }
        )
    summary["parameters"] = {
        "kept_by_name": dict(params_kept.most_common()),
        "text_layer_by_name": dict(params_text.most_common()),
        "dropped_by_name": dict(params_dropped.most_common()),
    }
    summary["dropped_fields"] = {
        "contact_messages": sum(
            1 for c in CONFIGS for r in tables[c]["messages"] if r["contact_dropped"]
        ),
        **dict(dropped_message_fields),
    }
    raw_identifiers = sorted(
        {_strip(u.first.identifier) for u in units if _strip(u.first.identifier)}
        | {
            _strip(ref.identifier)
            for u in units
            if u.first.message
            for ref in u.first.message.references
            if _strip(ref.identifier)
        }
    )
    summary["raw_identifiers_kept_private"] = len(raw_identifiers)
    cogs_by_sender: dict[str, set[int]] = defaultdict(set)
    for u in units:
        if u.first.sender:
            cogs_by_sender[u.first.sender]
            if u.first.cog_id is not None:
                cogs_by_sender[u.first.sender].add(u.first.cog_id)
    raw_senders = [
        {"sender": snd, "cog_ids": sorted(cogs)} for snd, cogs in sorted(cogs_by_sender.items())
    ]
    summary["people_times"] = {
        "messages_rounded": sum(1 for u in units if _people(u)),
        "exact_values_kept_private": len(people_times),
        "by_field": dict(Counter(f"{x['table']}.{x['field']}" for x in people_times)),
    }
    b = Build(
        units=units,
        tables=tables,
        summary=summary,
        raw_senders=raw_senders,
        raw_identifiers=raw_identifiers,
        people_times=people_times,
    )
    from warntext.describe import describe

    summary.update(describe(b))
    return b


def write(b: Build, out_dir: Path | str, private_dir: Path | str) -> dict[str, int]:
    """Write every table as Parquet (one folder per configuration) and the private files.

    Returns the number of rows written per ``<config>/<table>``.
    """
    out_dir, private_dir = Path(out_dir), Path(private_dir)
    counts = {}
    for c in CONFIGS:
        (out_dir / c).mkdir(parents=True, exist_ok=True)
        for name in RECORD_TABLES + TEXT_TABLES:
            rows = b.tables[c][name]
            table = pa.Table.from_pylist(rows, schema=SCHEMAS[name])
            pq.write_table(table, out_dir / c / f"{name}.parquet", compression="zstd")
            counts[f"{c}/{name}"] = len(rows)
    private_dir.mkdir(parents=True, exist_ok=True)
    (private_dir / "sender_values.json").write_text(
        json.dumps(b.raw_senders, indent=0) + "\n", encoding="utf-8"
    )
    (private_dir / "identifiers.json").write_text(
        json.dumps(b.raw_identifiers, indent=0) + "\n", encoding="utf-8"
    )
    pq.write_table(
        pa.Table.from_pylist(b.people_times, schema=PEOPLE_TIMES_SCHEMA),
        private_dir / "people_times.parquet",
        compression="zstd",
    )
    return counts


def build_from_raw(raw_dir: Path | str) -> Build:
    return build(parse_records(backfill.iter_records(raw_dir)))


def median(values: Iterable[int | None]) -> float | None:
    v = [x for x in values if x is not None]
    return statistics.median(v) if v else None
