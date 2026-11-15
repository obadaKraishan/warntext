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

The functions here return names and reasons, never the matched text.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

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
    "EAS-STN-ID": re.compile(r"[A-Z0-9/ ._-]{1,8}", re.IGNORECASE),
    "EAS-Must-Carry": re.compile(r"(true|false|yes|no)", re.IGNORECASE),
    "BLOCKCHANNEL": re.compile(r"[A-Z]{2,10}", re.IGNORECASE),
    "WEAHandling": re.compile(r"[A-Za-z ]{3,40}"),
    "timezone": re.compile(r"[A-Za-z][A-Za-z0-9/_+-]{1,39}"),
    "EASHeader": re.compile(r"ZCZC-[A-Z]{3}-[A-Z]{3}(-\d{6})+\+\d{4}-\d{7}-[A-Z0-9/ ._-]{1,8}-?"),
}
#: Case variants seen in the archive, read as the allowed name.
PARAMETER_ALIASES = {"TimeZone": "timezone", "Timezone": "timezone"}
#: Parameters whose value is part of the message itself: kept in the text layer only.
TEXT_PARAMETERS = frozenset({"CMAMtext", "CMAMlongtext", "EASText", "ShortText", "EASDescription"})

#: The text fields of an info block, in the order the text tables hold them.
INFO_TEXT_FIELDS = ("event", "headline", "description", "instruction", "web")


def allowed_name(name: str) -> str | None:
    """The allow-listed name a parameter is kept under, or None."""
    name = PARAMETER_ALIASES.get(name, name)
    return name if name in ALLOWED_PARAMETERS else None


def split_parameters(params: Iterable[Pair]) -> tuple[list[Pair], list[Pair], list[str]]:
    """Split parameters into kept, text and dropped (names only for the dropped ones).

    An allow-listed parameter whose value does not have its allowed form is dropped and named
    as ``<name> (unexpected value)``, so the count shows it without the value.
    """
    kept: list[Pair] = []
    text: list[Pair] = []
    dropped: list[str] = []
    for p in params:
        name = allowed_name(p.name)
        if name is not None:
            if ALLOWED_PARAMETERS[name].fullmatch(p.value.strip()):
                kept.append(Pair(name=name, value=p.value.strip()))
            else:
                dropped.append(f"{name} (unexpected value)")
        elif p.name in TEXT_PARAMETERS:
            text.append(p)
        else:
            dropped.append(p.name)
    return kept, text, dropped


def info_texts(info: Info) -> list[str]:
    """Every piece of text in one info block that could reach a text table."""
    out = [getattr(info, f) for f in INFO_TEXT_FIELDS]
    out += [info.wea_short, info.wea_long]
    out += [p.value for p in info.parameters if p.name in TEXT_PARAMETERS]
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


def pattern_hits(m: Message) -> list[str]:
    """The names of the personal-detail patterns found in the message's text fields.

    The organization name and ``contact`` are not scanned: the name is the sender's, and
    ``contact`` is dropped anyway. Everything that could reach a text table is.
    """
    texts = []
    for i in m.infos:
        texts += [getattr(i, f) for f in INFO_TEXT_FIELDS]
        texts += [i.wea_short, i.wea_long]
        texts += [p.value for p in i.parameters if p.name in TEXT_PARAMETERS]
        texts += [a.description for a in i.areas]
        texts += [r.uri for r in i.resources]
    hits: set[str] = set()
    for t in texts:
        if t:
            hits |= {name for name, found in patterns.present(t).items() if found}
    return sorted(hits)


def withheld(m: Message) -> tuple[str | None, list[str]]:
    """Why the message's text is withheld (``people_code`` or ``personal_pattern``), or None.

    Returns the reason and the pattern names that fired (also for people codes, as counts).
    """
    hits = pattern_hits(m)
    if same_codes(m) & PEOPLE_CODES:
        return "people_code", hits
    if hits:
        return "personal_pattern", hits
    return None, hits
