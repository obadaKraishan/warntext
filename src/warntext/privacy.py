"""The privacy rules, applied by code to every message. No hand review.

1. **Alerts about people keep their row and lose their text.** A message whose event codes
   include one of the four people codes (CAE, MEP, BLU, LEW) is withheld, always. Any other
   message is withheld when one of the personal-detail patterns (:mod:`warntext.patterns`)
   finds something in any of its text fields. Withholding too much is accepted; the reason is
   kept on the row (``text_withheld``), with the names of the patterns that fired.
2. **A withheld message has no text anywhere**: not in either text table, and its area shapes
   (polygons and circles, which can mark a single address) are left out of the area table too.
   Its counts, codes, times, places by county, lengths and flags stay.
3. **Parameters are allow-listed.** A parameter is kept in the record layer only if its name is
   in :data:`ALLOWED_PARAMETERS` and its value has the form that name allows; free-text
   parameters that are part of the message (the phone texts and the broadcast texts) go to the
   text layer; every other parameter is dropped, by name, everywhere. Vendor and staff
   parameters such as ``UserName``, ``Email`` or ``AssignedAddress`` are never kept.
4. **``contact`` is dropped everywhere**, as are the message-level ``note``, ``source`` and
   ``addresses`` fields, which some senders fill with an operator's name or address.
5. **Messages with a people code keep only the hour and the county.** In the record layer their
   sent, effective, onset and expiry times (and the times of references and threads that touch
   them, and the time in their EAS header) are rounded down to the hour; their area codes keep
   the county without the part-of-county digit. The exact values stay in a private local table.
   The date and the county already point to an event; the minute and the part of a county add
   little to that, and the hour of day is kept as a research variable.
6. **A message about a missing person is treated the same way,** whatever its event code: its
   text and shapes are withheld (reason ``missing_person`` when no other rule withheld it), its
   times are rounded to the hour and its area codes keep the county only.
7. **A message whose text describes a person is treated as rule 6 says,** with or without the
   cue words the patterns know: two or more elements of a description
   (:data:`warntext.patterns.DESCRIPTION_ELEMENTS`) in its text fields read together. Its
   text and shapes are withheld (reason ``person_described`` when no detail pattern and no
   people code withheld it), and its times and places are coarsened as for a missing person;
   the name ``person_described`` is kept in ``withheld_patterns``. The phone numbers and email
   addresses in any written form extend rule 1 (text withheld).

The functions here return names and reasons, never the matched text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime

from warntext import patterns
from warntext.schema import Info, Message, Pair

#: SAME event codes for messages about people (FEMA's IPAWS event-code glossary).
PEOPLE_CODES = frozenset({"CAE", "MEP", "BLU", "LEW"})

#: Parameters kept in the record layer, each with the form its value must have. Each is
#: documented by the IPAWS CAP profile or the EAS-CAP implementation guide, holds a code or a
#: number rather than free text, and cannot name a person:
#: - ``EAS-ORG``: the EAS originator code (civil authority, broadcaster, weather service,
#:   primary entry point);
#: - ``EAS-STN-ID``: the eight-character EAS station identifier of the originator;
#: - ``EAS-Must-Carry``: whether broadcasters must relay the message;
#: - ``BLOCKCHANNEL``: a channel the message must not go to;
#: - ``WEAHandling``: the class a phone alert is sent under (Imminent Threat, Public Safety,
#:   Presidential, AMBER);
#: - ``timezone``: the time zone named for the message's local times;
#: - ``EASHeader``: the SAME header (originator, event, locations, duration, time, station),
#:   kept only in its standard form, which holds codes only.
ALLOWED_PARAMETERS: dict[str, re.Pattern[str]] = {
    "EAS-ORG": re.compile(r"(EAS|CIV|WXR|PEP)"),
    "EAS-STN-ID": re.compile(r"[A-Z0-9/ ,._-]{1,8}", re.IGNORECASE),
    "EAS-Must-Carry": re.compile(r"(true|false|yes|no)", re.IGNORECASE),
    "BLOCKCHANNEL": re.compile(r"[A-Z]{2,10}", re.IGNORECASE),
    "WEAHandling": re.compile(r"[A-Za-z ]{3,40}"),
    "timezone": re.compile(r"[A-Za-z][A-Za-z0-9/_+-]{1,39}"),
    "EASHeader": re.compile(r"ZCZC-[A-Z]{3}-[A-Z]{3}(-\d{6})+\+\d{4}-\d{7}-[A-Z0-9/ ._-]{1,8}-?"),
}
#: Allowed names by their case-folded form: senders write ``TimeZone`` or ``WeaHandling`` too.
_ALLOWED_FOLDED = {name.casefold(): name for name in ALLOWED_PARAMETERS}
#: Parameters whose value is part of the message itself: kept in the text layer only.
TEXT_PARAMETERS = frozenset({"CMAMtext", "CMAMlongtext", "EASText", "ShortText", "EASDescription"})
_TEXT_FOLDED = {name.casefold() for name in TEXT_PARAMETERS}


def is_text_parameter(name: str) -> bool:
    """Whether a parameter holds part of the message's text, in any letter case."""
    return name.casefold() in _TEXT_FOLDED


#: The text fields of an info block, in the order the text tables hold them.
INFO_TEXT_FIELDS = ("event", "headline", "description", "instruction", "web")


def allowed_name(name: str) -> str | None:
    """The allow-listed name a parameter is kept under (in any letter case), or None."""
    return _ALLOWED_FOLDED.get(name.casefold())


def split_parameters(params: Iterable[Pair]) -> tuple[list[Pair], list[Pair], list[str]]:
    """Split parameters into kept, text and dropped (names only for the dropped ones).

    An allow-listed parameter whose value does not have its allowed form is dropped and named
    as ``<name> (unexpected value)``, or ``<name> (empty)`` when it has no value, so the count
    shows it without the value.
    """
    kept: list[Pair] = []
    text: list[Pair] = []
    dropped: list[str] = []
    for p in params:
        name = allowed_name(p.name)
        if name is not None:
            if not p.value.strip():
                dropped.append(f"{name} (empty)")
            elif ALLOWED_PARAMETERS[name].fullmatch(p.value.strip()):
                kept.append(Pair(name=name, value=p.value.strip()))
            else:
                dropped.append(f"{name} (unexpected value)")
        elif is_text_parameter(p.name):
            text.append(p)
        else:
            dropped.append(p.name)
    return kept, text, dropped


def info_texts(info: Info) -> list[str]:
    """Every piece of text in one info block that could reach a text table."""
    out = [getattr(info, f) for f in INFO_TEXT_FIELDS]
    out += [info.wea_short, info.wea_long]
    out += [p.value for p in info.parameters if is_text_parameter(p.name)]
    out += [a.description for a in info.areas]
    out += [r.description for r in info.resources] + [r.uri for r in info.resources]
    out += [info.contact, info.sender_name]
    return [t for t in out if t]


def message_texts(m: Message) -> list[str]:
    """All text of a message, including the fields that are always dropped."""
    out = [t for i in m.infos for t in info_texts(i)]
    out += [t for t in (m.note, m.source, m.addresses) if t]
    return out


def same_codes(m: Message) -> set[str]:
    return {
        p.value.strip().upper()
        for i in m.infos
        for p in i.event_codes
        if p.name.upper() == "SAME" and p.value.strip()
    }


def scan_texts(m: Message) -> list[str]:
    """Every text field of a message that could reach a text table, as the patterns read them.

    The organization name and ``contact`` are not scanned: the name is the sender's, and
    ``contact`` is dropped anyway. Everything that could reach a text table is, ``audience`` and
    the resource descriptions included.
    """
    texts: list[str | None] = []
    for i in m.infos:
        texts += [getattr(i, f) for f in INFO_TEXT_FIELDS]
        texts += [i.audience, i.wea_short, i.wea_long]
        texts += [p.value for p in i.parameters if is_text_parameter(p.name)]
        texts += [a.description for a in i.areas]
        texts += [r.description for r in i.resources] + [r.uri for r in i.resources]
    return [t for t in texts if t]


def pattern_hits(m: Message) -> list[str]:
    """The names of the personal-detail patterns found in the message's text fields, and
    ``person_described`` when those fields, read together, describe a person."""
    return patterns.hits(scan_texts(m))


#: The name of the description rule in ``withheld_patterns``.
DESCRIBED = patterns.DESCRIBED


def withheld(m: Message) -> tuple[str | None, list[str]]:
    """Why the message's text is withheld (``people_code``, ``personal_pattern`` or
    ``person_described``), or None.

    Returns the reason and the pattern names that fired (also for people codes, as counts). A
    detail pattern is named before a description; either way a description's times and places
    are coarsened (:func:`coarsened`).
    """
    hits = pattern_hits(m)
    if same_codes(m) & PEOPLE_CODES:
        return "people_code", hits
    if any(h != DESCRIBED for h in hits):
        return "personal_pattern", hits
    if hits:
        return "person_described", hits
    return None, hits


def coarsened(reason: str | None, hits: Iterable[str], about_missing: bool) -> bool:
    """Whether a message keeps only the hour and the county: a people code, a message about a
    missing person, or a message whose text describes a person."""
    return reason == "people_code" or about_missing or DESCRIBED in hits


# --- messages about a missing person -----------------------------------------------------

#: Words of a message about a missing person: in English (the words the content codes'
#: ``about_missing_person`` flag reads) and in Spanish.
_MISSING_EN = (
    r"\bmissing\b(?!\s+(?:pets?|dogs?|cats?|animals?|horses?|livestock|cattle|water|power|"
    r"service|data|information|items?|packages?|mail))|\bendangered\s+(?:missing|person|adult|"
    r"child|juvenile)|\b(?:silver|amber|ashanti|feather|endangered\s+missing)\s+alert|"
    r"\bhave\s+you\s+seen\b|\blast\s+seen\b|\bwas\s+reported\s+missing\b|\bgone\s+missing\b"
)
_MISSING_ES = (
    r"\bdesaparecid[oa]s?\b|\bvist[oa]\s+por\s+[u\u00fa]ltima\s+vez\b|"
    r"\balerta\s+(?:amber|plateada)\b|\b(?:lo|la)\s+ha\s+visto\b"
)
MISSING_PERSON_EN = re.compile(_MISSING_EN, re.IGNORECASE)
MISSING_PERSON = re.compile(_MISSING_EN + "|" + _MISSING_ES, re.IGNORECASE)


def about_missing_person(m: Message) -> bool:
    """Whether any text of the message (any language block) is about a missing person."""
    return any(MISSING_PERSON.search(t) for t in message_texts(m))


# --- times and places of messages about people -------------------------------------------

_CAP_TIME = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$")


def hour_floor(value: str | None) -> str | None:
    """A CAP time rounded down to the hour, in its own offset; None when it is not a time.

    ``2024-05-01T10:47:12-05:00`` becomes ``2024-05-01T10:00:00-05:00``. A value that does not
    read as a time is dropped rather than released as it is.
    """
    if value is None:
        return None
    m = _CAP_TIME.match(value.strip())
    if not m:
        return None
    return f"{m.group(1)}:00:00{m.group(5) or ''}"


def hour_floor_utc(t: datetime | None) -> datetime | None:
    return None if t is None else t.replace(minute=0, second=0, microsecond=0)


def finer_than_hour(value: str | datetime | None) -> bool:
    """Whether a released time says more than its hour (a text that is not a time does too)."""
    if value is None:
        return False
    if isinstance(value, datetime):
        return bool(value.minute or value.second or value.microsecond)
    m = _CAP_TIME.match(str(value).strip())
    if not m:
        return True
    fraction = (m.group(4) or ".0").strip(".0")
    return m.group(2) != "00" or m.group(3) != "00" or bool(fraction)


#: Geocode names whose values are six-digit ``PSSCCC`` codes (part of county, state, county).
PART_DIGIT_GEOCODES = frozenset({"SAME", "FIPS6"})
_SIX = re.compile(r"\d{6}")


def county_only(code: str) -> str:
    """A ``PSSCCC`` area code with the part-of-county digit set to 0 (the county only)."""
    value = code.strip()
    return "0" + value[1:] if _SIX.fullmatch(value) else code


def has_part_digit(code: str) -> bool:
    value = code.strip()
    return bool(_SIX.fullmatch(value)) and value[0] != "0"


_EAS_HEADER = re.compile(
    r"^(ZCZC-[A-Z]{3}-[A-Z]{3})((?:-\d{6})+)(\+\d{4})-(\d{3})(\d{2})(\d{2})(-.*)$"
)


def coarsen_eas_header(value: str) -> str:
    """An EAS header with its area codes at county level and its issue time to the hour.

    ``ZCZC-CIV-CAE-148201+0100-3191547-EXAMPLE1-`` becomes
    ``ZCZC-CIV-CAE-048201+0100-3191500-EXAMPLE1-``. A header not in the standard form is
    returned as it is (the parameter allow-list drops such values anyway).
    """
    m = _EAS_HEADER.match(value.strip())
    if not m:
        return value
    places = "".join("-" + county_only(c) for c in m.group(2).split("-") if c)
    return f"{m.group(1)}{places}{m.group(3)}-{m.group(4)}{m.group(5)}00{m.group(7)}"


def eas_header_finer(value: str) -> tuple[bool, bool]:
    """Whether an EAS header holds a part-of-county digit, and a time finer than the hour."""
    m = _EAS_HEADER.match(value.strip())
    if not m:
        return False, False
    part = any(has_part_digit(c) for c in m.group(2).split("-") if c)
    return part, m.group(6) != "00"
