"""Rule-based content codes for alert texts (codebook version 1, ``docs/codebook.md``).

Each unit of text (the 90-character phone text, the 360-character phone text, or the full text:
headline, description and instruction) is coded on its own, by rules that need no model. The
variables follow the warning literature: the five contents of the Warning Response Model
(hazard, location, time, source, guidance) and the kinds of location and time as Olson et al.
(2024) coded them; hazard description, split into characteristics and impacts as in Kuligowski
et al. (2023), who also add abbreviations and the words that trigger evacuation; and a hazard
category from the Warning Lexicon's groups (Sutton et al. 2024). The definitions are this
project's own words; the codebook cites each paper.

The rules return codes only (yes or no, counts, kinds, a category), never the words they matched,
so the codes may sit in the record layer even for messages whose text is withheld.

How a unit is read:
1. **Source first.** The organization named in the text (the authority's own name, an agency
   phrase, an agency acronym, or a jurisdiction that opens or signs the message) is found first
   and blanked out, so that "Fire Department" is not read as a fire, nor "Sampleton County
   Sheriff" as a place.
2. **Clauses.** The rest is split into clauses at sentence ends, line breaks, colons, dashes and
   bullets. A guidance verb counts when it opens a clause, follows "please", "should", "must",
   "asked to" and the like, follows "and" or "or" after another action, or follows an "if ...,"
   condition.
3. **Each variable** is then a set of patterns over the blanked text (see each function).

Every rule has a stated limit in the codebook. The rules are tested on invented messages only.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from warntext import privacy
from warntext import senders as sd

CODEBOOK_VERSION = "2"
UNITS = ("wea90", "wea360", "full")
CATEGORIES = (
    "wildfire",
    "public_safety",
    "law_enforcement",
    "public_health",
    "atmospheric",
    "technological",
    "geophysical",
    "other_unknown",
)

IC = re.IGNORECASE
VB = re.VERBOSE


def _rx(pattern: str, flags: int = IC) -> re.Pattern[str]:
    return re.compile(pattern, flags)


# --- language ----------------------------------------------------------------------------

_ES = _rx(
    r"\b(el|la|los|las|del|que|por|para|una|est[aá]|se|con|al|su|sus|usted|ustedes|"
    r"evac[uú]e|ahora|zona|condado|ciudad|inmediatamente|alerta|aviso|refugio|lugar|hogar|"
    r"agua|fuego|incendio|polic[ií]a|n[uú]mero|m[aá]s|informaci[oó]n|hasta|nuevo|orden|"
    r"resguardo|humo|nocivo|inmediato|suroeste|sureste|noroeste|noreste|evacuaci[oó]n|desalojo|"
    r"carretera|cerrad[oa]|peligro|tormenta|inundaci[oó]n|calle|avenida|personas|residentes)\b"
)
_EN = _rx(
    r"\b(the|and|of|to|in|for|is|are|your|you|this|on|at|be|will|please|area|now|all|"
    r"residents|county|city|fire|police|evacuate|shelter|stay|avoid|until|from|with|near)\b"
)


def looks_spanish(text: str) -> bool:
    """Whether a text reads as Spanish: more Spanish function words than English ones."""
    es, en = len(_ES.findall(text)), len(_EN.findall(text))
    return es >= 3 and es > en


# --- source ------------------------------------------------------------------------------

_AGENCY = _rx(
    r"""\b(?:
      sheriff'?s?\s+(?:office|dept\.?|department)
     |(?:county|parish|city)\s+sheriff
     |police\s+(?:department|dept\.?|bureau|chief)
     |(?:city|county|state|tribal|campus|university|transit|capitol|metro)\s+police
     |fire\s+(?:department|dept\.?|rescue|district|authority|marshal|protection\s+district)
     |office\s+of\s+emergency\s+(?:management|services|preparedness)
     |(?:department|division|office|bureau|agency)\s+of\s+(?:emergency|public|homeland|health|
        transportation|water|environmental|natural)\s+\w+(?:\s+(?:management|services|safety))?
     |emergency\s+(?:management|services|operations\s+center|communications)
        (?:\s+(?:agency|office|department|division|district))?
     |homeland\s+security
     |public\s+(?:health|safety|works|utilities)(?:\s+(?:department|dept\.?|office|division))?
     |health\s+(?:department|dept\.?|district|authority)
     |water\s+(?:district|department|authority|utility|company|board)
     |utilit(?:y|ies)\s+(?:district|department|commission|board)
     |(?:national\s+)?weather\s+service
     |highway\s+patrol|state\s+patrol|state\s+police|state\s+troopers?
     |unified\s+command|incident\s+command
     |forest\s+service|park\s+service|national\s+guard|coast\s+guard|red\s+cross
     |shakealert|usgs|fema|noaa|cal\s?fire
     |911\s+(?:center|dispatch|communications)|communications\s+center|dispatch\s+center
    )\b""",
    IC | VB,
)
#: Agency acronyms: a known list, and endings such as ``-SO`` (sheriff's office), ``-PD``,
#: ``-FD``, ``-OEM``, ``-EMA`` on a longer capitalized token.
_ACRONYM_KNOWN = re.compile(
    r"\b(?:OEM|OES|EMA|EOC|DEM|DES|HSEM|OHSEM|DPS|DOT|DPW|DOH|CHP|NWS|FEMA|USGS|NOAA|DHS|"
    r"FBI|ATF|CDC|EPA|PSPS|CALFIRE|NYCEM|CBP|TSA|USACE|TVA)\b"
)
_ACRONYM_ENDING = re.compile(r"\b[A-Z]{1,5}(?:SO|PD|FD|OEM|EMA|DEM|OES|FPD|DPS|EMS|EM)\b")
#: Short agency forms that are only read as a source after a place name ("Sampleton PD") or in
#: the message's opener or signature, since "SO" is also a word in an all-caps text.
_ACRONYM_BARE = re.compile(r"\b(?:PD|SO|FD|EMS|EM|DPS|SD|PSO|OEM|EMA)\b")
_NAME_THEN_BARE = re.compile(r"\b[A-Z][a-z]{2,}\s+(?:PD|SO|FD|EMS|EM|DPS|OEM|EMA)\b")
_JURISDICTION = _rx(
    r"\b(?:county|parish|borough|city|town|township|twp|cnty|village|state|tribe|tribal|nation|"
    r"university|campus|base)\b|[a-z]County\b"
)
#: Agency words that name a speaker when they stand as the opener or the subject ("Sheriff:",
#: "LEE POLICE:", "Southampton Twp emergency officials recommend ...").
_AGENCY_HEAD = _rx(
    r"\b(?:sheriff'?s?|police|fire|rescue|ems|officials|ofc|office|dept|department|authority|"
    r"government|govt|management|emergency\s+services|dispatch|911)\b|\w+911\b"
)
#: Initials: a short all-caps token, or a mixed token with two capitals or more ("RivCo",
#: "MAGovt", "AlertRivCo", "SRQCounty"), never one tied to a web address.
_INITIALS = re.compile(r"\b(?:[A-Z]{2,6}[0-9]*|[A-Z][a-z]*[A-Z][A-Za-z0-9]*)\b(?![.]\w)")
_ALERT_WORDS = _rx(
    r"\b(?:alert|warning|watch|order|notice|advisory|update|emergency|evacuat\w*|evac|test|"
    r"statement|message|information)\b"
)
_LEAD_STAMP = r"^\W*(?:[\d./:-]+\s*(?:[AaPp][Mm])?\s+){0,2}"
_OPENER = re.compile(
    _LEAD_STAMP
    + r"([A-Z][\w.'&/-]*(?:\s+[A-Za-z][\w.'&/-]*){0,7})\s*(?::|-{1,2}|\u2013|\u2014)(?:\s|$)"
)
#: An opener joined to the text by a bare dash: "Ionia911-Lake ...", "GDOT-Road ...".
_OPENER_TIGHT = re.compile(_LEAD_STAMP + r"([A-Z][A-Za-z]*(?:911|[A-Z]{2,})[A-Za-z0-9]*)[:\-]\S")
#: Initials or an agency word that starts the text as its speaker: "MAGovt Alert ...",
#: "NCEM ...", "THE DOUGLAS COUNTY SHERIFFS OFC ADV ...".
_PREFIX_ALERT = re.compile(_LEAD_STAMP + r"([A-Z][A-Za-z]*[A-Z][A-Za-z0-9]*)\s+(?i:alerts?)\b")
_SIGNATURE = re.compile(r"(?:^|\s)(?:-{1,2}|\u2013|\u2014|~)\s*([A-Z][\w.'& /-]{2,70}?)\s*\.?\s*$")
_STATE_OF = _rx(r"\bstate\s+of\s+(?:emergency|disaster)\b")
_NAME = r"[A-Z][\w.'&-]*(?:\s+(?:of\s+|and\s+|&\s+)?[A-Z][\w.'&-]*){0,6}"
#: A speaker named in the text: "This is ...", "Message from ...", or "... urges residents".
_SPEAKER = re.compile(
    rf"\b(?i:this\s+is|message\s+from|from|on\s+behalf\s+of)\s+(?:(?i:the)\s+)?({_NAME})"
)
_SPEAKER_VERB = re.compile(
    rf"\b({_NAME})\s+(?i:(?:is\s+|has\s+|have\s+)?(?:advis|urg|ask|report|issu|announc|recommend|"
    r"order|request|say|encourag|remind|confirm|declar)\w*)\b"
)
#: A speaker announced by its message: "X County Sheriff's Office with an important message".
_SPEAKER_WITH = re.compile(
    rf"\b({_NAME})\s+(?i:with\s+(?:an?\s+)?(?:important|emergency|urgent)\s+(?:message|update|"
    r"alert|notice))"
)
#: An agency word joined to the text by a colon with no space: "Sheriff:Valley Center ...".
_OPENER_AGENCY_TIGHT = re.compile(
    _LEAD_STAMP + r"([A-Z][A-Za-z']*(?:\s+[A-Z][A-Za-z']*)?)\s*:(?=\S)"
)
#: The text's own subject speaking: its first words, then a speaker verb ("OTTAWA HAS ISSUED",
#: "CTA is suspending", "UCPD ordering", "... SHERIFFS OFC ADV").
_SUBJECT_SPEAKS = re.compile(
    _LEAD_STAMP + r"(?:(?i:the)\s+)?([A-Z][\w.'&-]*(?:\s+[A-Za-z][\w.'&-]*){0,6}?)\s+"
    r"(?i:(?:(?:is|are)\s+(?:advis|urg|ask|request|warn|suspend|notify|remind|order|recommend)\w*ing"
    r"|(?:has|have)\s+(?:issu|order|declar|recommend|request|suspend|announc|advis|urg|ask)\w*"
    r"|(?:advis|urg|ask|request|suspend|notif|remind|order|recommend|announc|declar)\w*(?:s|ing)"
    r"|adv|issues))\b"
)
_GENERIC_SPEAKER = _rx(
    r"^(?:police|officials|authorities|deputies|officers|firefighters|crews|residents|everyone|"
    r"you|we|they|people|the\s+public|emergency\s+officials|all|this|a|an|the)$"
)
#: A place name before an agency word, in mixed case: "Exampleville Police".
_PLACE_AGENCY = re.compile(
    r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,2})\s+(?:Police|Sheriff|Fire\s+Rescue|Rescue|"
    r"EMS|Emergency\s+Management|Emergency\s+Services|Public\s+Works|Utilities|Health)\b"
)
_NOT_A_PLACE = _rx(
    r"^(?:call|contact|notify|tell|local|area|the|your|our|alert|warning|if|when|and|or|by|"
    r"from|with|nearest|nearby|state|county|city|town|public|please|emergency|police|fire|"
    r"sheriff|this|that|all|any|no|not|for|to|at|in|on|of|an|a)$"
)
_GENERIC_NAME_WORDS = _rx(
    r"^(?:the|of|and|for|county|city|town|township|village|borough|parish|state|office|"
    r"emergency|management|department|dept|services?|agency|division|public|safety|"
    r"homeland|security|police|sheriff'?s?|fire|rescue|district|authority|government|"
    r"commission|operations|center|communications|911|alert|alerts|alerting|warning|"
    r"system|program|unit|base|joint|national|united|states|us|u\.s\.)$"
)


@dataclass(frozen=True)
class Context:
    """What the coder may know about a message besides the unit's own text.

    ``organization`` is the authority's name (FEMA's or the sender's own); ``place_words``
    are distinctive words of the message's area descriptions, used to see a place named in the
    text; ``event_codes`` are the SAME codes, used only for the hazard category.
    """

    organization: str | None = None
    place_words: frozenset[str] = frozenset()
    event_codes: tuple[str, ...] = ()
    #: The whole language block's text (all its units), for the hazard category only: the
    #: category describes the event that prompted the message, so a unit that names no hazard
    #: takes the category its message's other texts name.
    block_text: str = ""


def organization_words(name: str | None) -> list[str]:
    """The distinctive words of an organization's name (place names, mostly), lowercased."""
    if not name:
        return []
    words = re.findall(r"[A-Za-z][A-Za-z'.-]+", name)
    return [w.lower() for w in words if len(w) >= 3 and not _GENERIC_NAME_WORDS.match(w)]


def speaker_spans(text: str, ctx: Context) -> list[tuple[int, int]]:
    """Spans that name the organization speaking: opener, signature, speaker cues, a subject with
    a speaker verb, initials that start the text, and the authority's own name or initials.

    An agency only mentioned ("FEMA assistance", "the bomb squad removed it") is not the
    speaker, and a web address alone names no one.
    """
    spans: list[tuple[int, int]] = []
    for rx in (_OPENER, _SIGNATURE):
        m = rx.search(text)
        if m and (_names_an_organization(m.group(1), opener=True) or _speaker_head(m.group(1))):
            spans.append(_organization_part(m.group(1), m.start(1)))
    for rx in (_OPENER_TIGHT, _PREFIX_ALERT):
        m = rx.search(text)
        if m and _initials_ok(m.group(1)):
            spans.append(m.span(1))
    m = _OPENER_AGENCY_TIGHT.search(text)
    if m and _AGENCY_HEAD.search(m.group(1)):
        spans.append(m.span(1))
    for rx in (_SPEAKER, _SPEAKER_WITH):
        for m in rx.finditer(text):
            name = m.group(1)
            if (
                _names_an_organization(name)
                or _speaker_head(name, strict=True)
                or re.search(r"(?i)\b(?:alerts?|notifications?|system|program)$", name)
            ):
                spans.append(_organization_part(name, m.start(1)))
    m = _SUBJECT_SPEAKS.search(text)
    if m:
        subject = m.group(1).strip()
        named_body = _AGENCY_HEAD.search(subject) or _JURISDICTION.search(subject)
        if not (
            _GENERIC_SPEAKER.match(subject)
            or (_ALERT_WORDS.search(subject) and not named_body)
            or any(rx.search(subject) for rx in HAZARD_WORDS.values())
            or _ROAD_WORDS.search(subject)
        ):
            spans.append(m.span(1))
    for m in _SPEAKER_VERB.finditer(text):
        if _names_an_organization(m.group(1)) or _speaker_head(m.group(1), strict=True):
            spans.append(_organization_part(m.group(1), m.start(1)))
    first = re.match(_LEAD_STAMP + r"(?:(?i:the)\s+)?([^\s:]+(?:\s+[^\s:]+){0,5})", text)
    if first:
        head = first.group(1)
        lead = re.match(r"\S+", head)
        if lead and (
            _ACRONYM_KNOWN.fullmatch(lead.group(0)) or _ACRONYM_ENDING.fullmatch(lead.group(0))
        ):
            spans.append((first.start(1), first.start(1) + lead.end()))
        elif re.match(rf"(?:{_AGENCY.pattern})", head, IC | VB):
            spans.append((first.start(1), first.end(1)))
    if ctx.organization:
        full = re.search(re.escape(ctx.organization), text, IC)
        if full:
            spans.append(full.span())
        initials = "".join(
            w[0] for w in re.findall(r"[A-Za-z]+", ctx.organization) if w[0].isupper()
        )
        if len(initials) >= 3:
            spans += [m.span() for m in re.finditer(rf"\b{re.escape(initials)}\b", text)]
    return _merge(spans)


def _initials_ok(token: str) -> bool:
    """Initials that can name a speaker: not a channel's name, a common word, an alert word or a
    hazard word ("EAS", "NOW", "ALERT" and "FLOOD" are not a speaker's initials)."""
    return not (
        token.upper() in _NOT_ACRONYMS
        or _ALERT_WORDS.fullmatch(token)
        or any(rx.fullmatch(token) for rx in HAZARD_WORDS.values())
    )


def _speaker_head(name: str, strict: bool = False) -> bool:
    """An opener or subject that names a speaker by an agency word or by initials.

    With ``strict`` (a name found mid-text), an all-caps name counts only by an agency word:
    in an all-caps text every short word looks like initials.
    """
    if _STATE_OF.search(name):
        return False
    if _AGENCY_HEAD.search(name):
        return True
    if strict and name.isupper():
        return False
    for w in re.findall(r"[A-Za-z0-9]+", name):
        if _INITIALS.fullmatch(w) and _initials_ok(w):
            return True
    return False
    if _AGENCY_HEAD.search(name):
        return True
    for w in re.findall(r"[A-Za-z0-9]+", name):
        if (
            _INITIALS.fullmatch(w)
            and w.upper() not in _NOT_ACRONYMS
            and not _ALERT_WORDS.fullmatch(w)
            and not any(rx.fullmatch(w) for rx in HAZARD_WORDS.values())
        ):
            return True
    return False


def find_source(text: str, ctx: Context) -> list[tuple[int, int]]:
    """Spans of the text that name any organization: blanked before the other codes read it.

    This is wider than the speaker (:func:`speaker_spans`): an agency only mentioned ("the fire
    department has contained it") is still not a fire, nor a place.
    """
    spans: list[tuple[int, int]] = []
    spans += [m.span() for m in _AGENCY.finditer(text)]
    spans += [m.span() for m in _ACRONYM_KNOWN.finditer(text)]
    spans += [m.span() for m in _ACRONYM_ENDING.finditer(text) if len(m.group(0)) >= 3]
    spans += [m.span() for m in _NAME_THEN_BARE.finditer(text)]
    for rx in (_OPENER, _SIGNATURE):
        m = rx.search(text)
        if not m:
            continue
        if _names_an_organization(m.group(1), opener=True):
            spans.append(_organization_part(m.group(1), m.start(1)))
    for rx in (_SPEAKER, _SPEAKER_VERB):
        for m in rx.finditer(text):
            if _names_an_organization(m.group(1)):
                spans.append(_organization_part(m.group(1), m.start(1)))
    for m in _PLACE_AGENCY.finditer(text):
        if not _NOT_A_PLACE.match(m.group(1).split()[0]):
            spans.append(m.span())
    spans += speaker_spans(text, ctx)
    words = organization_words(ctx.organization) + sorted(ctx.place_words)
    if ctx.organization:
        full = re.search(re.escape(ctx.organization), text, IC)
        if full:
            spans.append(full.span())
        initials = "".join(
            w[0] for w in re.findall(r"[A-Za-z]+", ctx.organization) if w[0].isupper()
        )
        if len(initials) >= 3:
            spans += [m.span() for m in re.finditer(rf"\b{re.escape(initials)}\b", text)]
    for w in words:
        # The authority's own place word next to an agency or jurisdiction word.
        for m in re.finditer(rf"\b{re.escape(w)}\b", text, IC):
            window = text[m.start() : m.end() + 40]
            if re.match(
                rf"{re.escape(w)}\W+(?:\w+\W+){{0,2}}?(?:{_AGENCY.pattern})",
                window,
                IC | VB,
            ) or re.match(
                rf"{re.escape(w)}\W+(?:(?:county|city|parish|borough|town)\W+)?(?:{_AGENCY.pattern}|"
                r"oem|ema|eoc|so|pd|fd|police|sheriff|government|officials)\b",
                window,
                IC | VB,
            ):
                spans.append((m.start(), m.end()))
    return _merge(spans)


def _names_an_organization(name: str, opener: bool = False) -> bool:
    """Whether a name holds an agency phrase or acronym, or names a jurisdiction.

    An opener ("Sampleton County Evacuation Order:") names its jurisdiction as the sender
    unless it is a declaration ("State of Emergency"); elsewhere a jurisdiction must stand
    without alert words ("Sampleton County" after "This is").
    """
    if _AGENCY.search(name) or _ACRONYM_KNOWN.search(name) or _ACRONYM_ENDING.search(name):
        return True
    if opener and _ACRONYM_BARE.search(name):
        return True
    if not _JURISDICTION.search(name) or _STATE_OF.search(name):
        return False
    return opener or not _ALERT_WORDS.search(name)


def jurisdiction_opener(text: str) -> bool:
    """Whether the text opens with a jurisdiction's name and no agency ("Sampleton County: ...").

    Such an opener names both the sender and the area, so it counts as a source and as a
    boundary location; an agency's name ("Sampleton County OEM:") counts only as a source.
    """
    m = _OPENER.search(text)
    if not m or not _JURISDICTION.search(m.group(1)) or _STATE_OF.search(m.group(1)):
        return False
    head = m.group(1)
    return not (
        _AGENCY.search(head)
        or _ACRONYM_KNOWN.search(head)
        or _ACRONYM_ENDING.search(head)
        or _ACRONYM_BARE.search(head)
    )


def _organization_part(name: str, start: int) -> tuple[int, int]:
    """The span of a name up to its last agency, acronym or jurisdiction word.

    "Sampleton County Flood Warning" gives "Sampleton County": the hazard and alert words after
    the organization stay in the text for the other codes.
    """
    ends = [
        m.end()
        for rx in (
            _AGENCY,
            _ACRONYM_KNOWN,
            _ACRONYM_ENDING,
            _ACRONYM_BARE,
            _JURISDICTION,
            _AGENCY_HEAD,
        )
        for m in rx.finditer(name)
    ]
    ends += [
        m.end()
        for m in _INITIALS.finditer(name)
        if m.group(0).upper() not in _NOT_ACRONYMS
        and not _ALERT_WORDS.fullmatch(m.group(0))
        and not any(rx.fullmatch(m.group(0)) for rx in HAZARD_WORDS.values())
    ]
    return (start, start + (max(ends) if ends else len(name)))


def _merge(spans: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def blank(text: str, spans: Iterable[tuple[int, int]]) -> str:
    """The text with the spans replaced by spaces (positions kept)."""
    chars = list(text)
    for a, b in spans:
        for k in range(a, b):
            chars[k] = " "
    return "".join(chars)


# --- hazards and their category ----------------------------------------------------------

HAZARD_WORDS: dict[str, re.Pattern[str]] = {
    "wildfire": _rx(
        r"\b(?:wild\s?fires?|brush\s?fires?|grass\s?fires?|forest\s+fires?|vegetation\s+fires?|"
        r"wildland\s+fires?|fires?|red\s+flag|fire\s+weather|burn\s+bans?|fire\s+(?:danger|ban)|"
        r"burn(?:ing)?\s+restrictions|prescribed\s+burns?|controlled\s+burns?)\b"
    ),
    "technological": _rx(
        r"\b(?:(?:structure|house|building|vehicle|industrial|plant|commercial|apartment|"
        r"warehouse|chemical|tire|oil|refinery)\s+fires?|explosions?|gas\s+leaks?|natural\s+gas|"
        r"chemical\s+(?:leak|release|spill|incident|plume)|hazardous\s+materials?|haz-?mats?|"
        r"toxic\s+(?:gas|fumes|chemicals?|smoke|release)|ammonia|chlorine|derail\w*|"
        r"(?:dam|levee)\s+(?:failure|break|breach|collapse)|dam\s+failure|"
        r"(?:bridge|building|structure)\s+collapse|radiological|radiation|nuclear|"
        r"oil\s+spill|pipeline|carbon\s+monoxide|gas\s+main|power\s+plant\s+(?:incident|"
        r"emergency)|dam\s+(?:release|overtopping|is\s+failing|may\s+fail|failing|emergency)|"
        r"gas\s+(?:line|odor|smell|release)|propane|fuel\s+(?:leak|spill)|"
        r"(?:diesel|fuel|oil|gas|chemical|ammonia|chlorine|sewage)\s+(?:release|spill|leak)s?)\b"
    ),
    "law_enforcement": _rx(
        r"\b(?:police\s+(?:activity|situation|incident|operation|presence)|law\s+enforcement\s+"
        r"(?:activity|operation|situation|incident)|active\s+(?:shooter|threat|assailant)|"
        r"shooters?|shootings?|shots\s+fired|gunfire|gunman|armed|barricaded|hostages?|"
        r"manhunt|(?:a|the|armed|male|female)\s+suspects?|suspects\b|suspect\s+(?:is|was|has|"
        r"vehicle|described|fled|last|remains)|fugitives?|escaped\s+(?:inmates?|prisoners?)|curfews?|"
        r"bomb\s+threats?|bombs?|suspicious\s+(?:package|device|item|person|vehicle)|"
        r"civil\s+(?:unrest|disturbance)|riots?|protests?|looting|lockdown|lock\s+down|"
        r"standoff|swat|homicide|stabbing|carjacking|pursuit|dangerous\s+person|"
        r"criminal\s+activity|crimes?|criminals?|law\s+enforcement\s+presence|"
        r"police\s+(?:chase|search|standoff))\b"
    ),
    "public_health": _rx(
        r"\b(?:covid(?:-?19)?|coronavirus|pandemic|outbreak|virus|vaccin\w+|flu|influenza|"
        r"measles|mpox|monkeypox|air\s+quality|unhealthy\s+air|public\s+health\s+(?:emergency|"
        r"order|advisory)|overdoses?|fentanyl|e\.\s?coli|rabies|west\s+nile|opioids?|"
        r"testing\s+site|stay\s+at\s+home\s+order|stay-at-home|quarantine|isolation\s+order|"
        r"health\s+(?:alert|advisory|emergency|warning|order))\b"
    ),
    "public_safety": _rx(
        r"\b(?:911|9-1-1)\s+(?:outage|service|is\s+down|not\s+working|problems?|issues?|"
        r"disruption|unavailable)|\b(?:phone|telephone|landline|cell|cellular)\s+(?:outages?|"
        r"service|disruption)|\boutages?\b|\bpower\s+(?:outages?|failure)|\bblackouts?\b|"
        r"\bwater\s+(?:main\s+break|outage|service|pressure|shortage|emergency|"
        r"contamination|restrictions?)|\bboil\s+(?:water|order|advisory|notice)|"
        r"\bdo\s+not\s+drink\b|\btraffic\b|\b(?:crash|collision|accident)\b|\bsewage\b|"
        r"\bfuel\s+shortage\b|\b(?:roads?|roadways?|highways?|bridges?|lanes?|streets?)\s+"
        r"(?:is\s+|are\s+|will\s+be\s+|have\s+been\s+)?closed\b|\b(?:road|lane|bridge|street|"
        r"highway)\s+closures?\b|\bwater\s+(?:conservation|advisory|notice|alert|quality|leak|"
        r"line|system|break)|\bno\s+water\b|\bpower\s+(?:shut[- ]?offs?|lines?\s+down)|"
        r"\bdowned\s+(?:power\s+)?(?:lines?|poles?|wires?|trees?)\b|\bpsps\b|"
        r"\b(?:interstate\s*\d+|i-?\s?\d+|us-?\s?\d+|sr-?\s?\d+|sh\s?-?\d+|hwy\.?\s?-?\d+|"
        r"highway\s+\d+|route\s+\d+|[a-z]{1,3}-\d{1,4})\b(?:\s+\S+){0,4}?\s+closed\b|"
        r"\ball\s+lanes\s+(?:are\s+)?(?:closed|blocked)\b|\bsuspend\w*\s+(?:\S+\s+){0,4}?service\b|"
        r"\bservice\s+(?:is\s+)?(?:suspended|suspension|disruption|interruption)\b"
    ),
    "atmospheric": _rx(
        r"\b(?:flash\s+floods?|floods?|flooding|tornado(?:es)?|thunderstorms?|storms?|"
        r"severe\s+weather|hurricanes?|tropical\s+storms?|typhoons?|storm\s+surge|"
        r"high\s+winds?|winds?|winter\s+storms?|snow|blizzard|ice\s+storms?|black\s+ice|"
        r"thin\s+ice|ice\s+jams?|icy|freez\w+|"
        r"extreme\s+cold|wind\s+chill|extreme\s+heat|excessive\s+heat|heat\s+wave|heat|"
        r"dust\s+storm|haboob|fog|hail|heavy\s+rain|rain|lightning|tsunami|monsoon|"
        r"rip\s+currents?|high\s+surf|(?:winter|cold|hot|extreme|inclement)\s+weather|"
        r"weather\s+(?:emergency|warning|alert))\b"
    ),
    "geophysical": _rx(
        r"\b(?:earthquakes?|quakes?|aftershocks?|shaking|landslides?|mudslides?|mud\s+slides?|"
        r"debris\s+flows?|rock\s?slides?|rock\s?falls?|avalanches?|sinkholes?|volcan\w+|"
        r"eruptions?|lahars?|ash\s?fall)\b"
    ),
}
#: Words that point to a category's domain without naming a hazard ("police are searching",
#: "water service"): used for the category only, after hazard words and before event codes.
CATEGORY_CUES: dict[str, re.Pattern[str]] = {
    "law_enforcement": _rx(r"\b(?:police|sheriff|deputies|officers|law\s+enforcement|swat)\b"),
    "public_safety": _rx(
        r"\b(?:water\s+(?:service|main|pressure|system|supply)|electric(?:ity|al)?\s+service|"
        r"power|phone\s+lines|road\s+work|detour)\b"
    ),
    "public_health": _rx(r"\b(?:health|vaccin\w*|clinic|testing)\b"),
    "wildfire": _rx(r"\b(?:smoke|evacuation\s+zones?|red\s+flag)\b"),
}
#: Hazard categories from SAME event codes, used when no hazard word decides.
CODE_CATEGORY = {
    "FRW": "wildfire",
    "EQW": "geophysical",
    "AVW": "geophysical",
    "AVA": "geophysical",
    "VOW": "geophysical",
    "HMW": "technological",
    "NUW": "technological",
    "RHW": "technological",
    "TOE": "public_safety",
    "LEW": "law_enforcement",
    "BLU": "law_enforcement",
    "CAE": "law_enforcement",
    "MEP": "law_enforcement",
}
#: When words of several categories tie, the one first in this order wins.
_TIE_ORDER = (
    "technological",
    "law_enforcement",
    "wildfire",
    "geophysical",
    "public_health",
    "public_safety",
    "atmospheric",
)
_WEATHER_CODE = re.compile(r"^[A-Z]{3}$")


def code_category(code: str) -> str | None:
    if code in CODE_CATEGORY:
        return CODE_CATEGORY[code]
    from warntext.measures import HAZARDS

    if HAZARDS.get(code, "").startswith("weather_"):
        return "atmospheric"
    return None


def hazard_category(text: str, codes: Iterable[str]) -> tuple[str, str]:
    """The hazard category and how it was decided (``words``, ``code`` or ``none``).

    Words decide first: the category with the most hazard words wins; on a tie, the event
    code's category if it is among the tied ones, else the fixed order. Without hazard words,
    the event code decides (FRW wildfire, EQW geophysical, HMW technological, weather codes
    atmospheric ...). Otherwise ``other_unknown``.
    """
    counts = {c: len(rx.findall(text)) for c, rx in HAZARD_WORDS.items()}
    # A specific fire (structure, vehicle ...) is technological, not a wildfire: do not count
    # its "fire" again as a wildfire word.
    if counts["technological"]:
        specific = len(re.findall(r"\b\w+\s+fires?\b", text, IC))
        counts["wildfire"] = max(0, counts["wildfire"] - specific)
    by_code = [c for c in (code_category(x) for x in codes) if c]
    best = max(counts.values())
    if best:
        tied = [c for c in _TIE_ORDER if counts[c] == best]
        for c in by_code:
            if c in tied:
                return c, "words"
        return tied[0], "words"
    if by_code:
        return by_code[0], "code"
    return "other_unknown", "none"


def has_hazard(text: str) -> bool:
    return any(rx.search(text) for rx in HAZARD_WORDS.values())


_CHARACTERISTICS = _rx(
    r"\b(?:fast[- ]moving|rapidly|quickly|spreading|spreads?|growing|"
    r"moving\s+(?:north|south|east|west|toward|towards|in|into|quickly)|"
    r"heading\s+(?:north|south|east|west|toward|towards)|advancing|out\s+of\s+control|"
    r"uncontained|contained|containment|\d[\d,.]*\s*acres?|acres|\d+\s*(?:mph|miles\s+per\s+hour|"
    r"knots)|gusts?|sustained\s+winds|\d+(?:\.\d+)?\s*(?:inches|inch|feet)\b|magnitude|"
    r"intensity|plume|smoke|flames|large|major|massive|significant|dangerous|extreme|intense|"
    r"strong|deadly|toxic|explosive|flammable|rising|risen|swift(?:ly)?|"
    r"has\s+(?:started|begun|crossed|jumped|breached|failed)|serious|severe\s+threat|threat\s+to|"
    r"poor\s+(?:road\s+)?conditions|worsen\w*|deteriorat\w*|ha(?:s|ve)\s+passed|"
    r"moved\s+(?:out|away|on|east|west|north|south)|(?:safely\s+)?removed|stage\s+\d|"
    r"(?:more|additional)\s+(?:rain|rainfall|snow|storms?|showers)|release\s+into|"
    r"into\s+(?:the\s+)?(?:\w+\s+){0,2}(?:river|creek|lake|bay|stream|waterway|harbor|sewer|"
    r"storm\s+drains?)s?|"
    r"(?:is|are)\s+(?:permitted|exempt|allowed|prohibited|banned))\b"
)
_IMPACTS = _rx(
    r"\b(?:damage[ds]?|destroy(?:ed|ing)?|injur(?:y|ies|ed)|fatalit(?:y|ies)|deaths?|"
    r"power\s+(?:outages?|shut[- ]?offs?|loss)|without\s+(?:power|water|service|phone)|"
    r"loss\s+of\s+(?:power|water|service|life)|"
    r"(?:roads?|roadways?|streets?|highways?|bridges?|lanes?|rd|hwy|ramps?)\s+(?:\S+\s+){0,3}?"
    r"(?:are\s+|is\s+|will\s+be\s+)?(?:closed|blocked|impassable|flooded|washed\s+out|opening|"
    r"reopen\w*)|closures?|impassable|closed\s+due\s+to|backups?|may\s+not\s+be\s+able\s+to|"
    r"(?:interstate\s*\d+|i-?\s?\d+|us-?\s?\d+|sr-?\s?\d+|hwy\.?\s?-?\d+|highway\s+\d+)"
    r"(?:\s+\S+){0,4}?\s+closed|"
    r"contaminat\w*|unsafe|not\s+safe|downed\s+(?:trees|power\s+lines|lines)|trapped|"
    r"stranded|disrupt\w*|unable\s+to\s+(?:call|reach|dial|connect)|"
    r"cannot\s+(?:call|reach|dial)|(?:may|could|can|will)\s+(?:cause|result|lead|affect|"
    r"impact|threaten)|life[- ]threatening|threat\s+to\s+(?:life|property))\b"
)


# --- guidance ----------------------------------------------------------------------------

#: Protective actions and their opening verbs. Grounded in the Warning Lexicon's action groups
#: (shelter, evacuate, protect, decontaminate, refrain, avoid, obtain, listen, rearrange,
#: contact) and the verbs that open its protective-action statements.
_VERBS = (
    r"evacuate|leave|shelter(?=\s+in\b|\s*-\s*in\b|\s+indoors|\s+inside|\s+immediately|"
    r"\s+now|\s+where|\s+until|\s+at\s+once)|stay|remain|avoid|do\s+not\s+\w+|"
    r"don'?t\s+\w+|never\s+\w+|"
    r"move|go|get\s+(?:out|inside|indoors|to|away|ready|off)|seek|take\s+(?:shelter|cover|"
    r"action|precautions|steps|immediate)|lock|close|shut|turn\s+(?:off|around)|seal|cover|"
    r"drop|hold\s+on|protect|wear|boil|conserve|limit|reduce|restrict|use|call|contact|dial|"
    r"text|report|check|visit|go\s+to|monitor|listen|tune\s+in|tune\s+to|follow|prepare|"
    r"be\s+(?:prepared|ready|alert|aware|cautious|careful|vigilant|safe|set)|get\s+ready|plan|"
    r"bring|pack|secure|wait|delay|keep|find|look|watch|unplug|wash|clean|run|hide|fight|"
    r"head\s+(?:to|inside|indoors)|proceed|relocate|clear\s+(?:the|out)|vacate|exit|"
    r"sign\s+up|register|allow|yield|exercise\s+caution|use\s+caution|drive|slow\s+down|"
    r"remove|charge|stock\s+up|fill|gather|notify|refrain|dispose|discard|"
    r"throw\s+away|treat|filter|drink|bring\s+in|return|consider|ensure|make\s+sure|"
    r"evac(?=\s+(?:to|now|immediately|the|all|north|south|east|west|if))|merge\s+(?:left|right)|"
    r"travel\s+(?:cautiously|carefully|slowly|safely|with\s+caution)"
)
_VERB = _rx(rf"\b(?:{_VERBS})\b")
_NOUN_GUIDANCE = _rx(
    r"\b(?:evacuation\s+(?:order|warning|notice)s?|mandatory\s+evacuations?|"
    r"voluntary\s+evacuations?|shelter[- ]in[- ]place|boil\s+(?:water\s+)?(?:notice|advisory|"
    r"order)|do\s+not\s+drink|stay[- ]at[- ]home\s+order|lockdown\s+order|"
    r"curfew\s+(?:is\s+)?in\s+effect|evacuations?\s+(?:is\s+|are\s+|has\s+been\s+|"
    r"have\s+been\s+)?(?:required|ordered|recommended|advised|mandatory|underway|in\s+effect|"
    r"in\s+progress)|(?:immediate|precautionary|recommended)\s+evacuations?|"
    r"evac\s+(?:order|warning|notice)s?|(?:mandatory|immediate|voluntary)\s+(?:\w+\s+){1,2}"
    r"evacuations?|evacuation\s+immediate|level\s*(?:1|2|3|one|two|three)\s*(?:\(?\s*(?:be\s+ready|"
    r"be\s+set|go)\s*\)?\s*)?evacuations?|burn\s+bans?|fire\s+bans?|no\s+(?:outdoor\s+)?burning|"
    r"no\s+(?:swimming|entry|parking|fireworks|open\s+(?:fires?|flames?))|"
    r"(?:water|burn|watering|outdoor\s+water)\s+restrictions?|detours?)\b"
)
#: A pointer to more information: a cue word, then a web address in the same clause.
_INFO_LINK = _rx(
    r"\b(?:updates?|info(?:rmation)?|details|status|map|maps|visit|see|check|go\s+to|follow|"
    r"monitor|sign\s+up|register)\b[^.!?]{0,60}?(?:https?://|www\.|\b[\w-]+\.(?:gov|org|com|net|us)\b)"
)
#: A clause that ends an order: its order words are not an instruction any more.
_ENDED = _rx(
    r"\b(?:lifted|cancel+ed|no\s+longer\s+in\s+effect|has\s+ended|have\s+ended|expired|reduced|"
    r"downgraded|rescinded|all\s+clear)\b"
)
#: Instructions strong enough to count wherever they stand in a clause ("Residents near Oak
#: Creek evacuate now"): a protective verb with its object or its adverb.
_STRONG = _rx(
    r"\b(?:evacuate(?!d)|avoid\s+(?:the|this|all|any|travel|area|downtown)|boil\s+(?:your\s+|"
    r"all\s+|tap\s+)?water|seek\s+shelter|take\s+(?:shelter|cover)|shelter\s+in\s+place|"
    r"stay\s+(?:away|indoors|inside|home|off|out|clear|in\s+place)|remain\s+(?:indoors|inside|"
    r"home|in\s+place|sheltered)|lock\s+(?:your\s+)?doors|close\s+(?:your\s+|all\s+)?"
    r"(?:windows|doors)|turn\s+around|move\s+to\s+higher\s+ground|go\s+(?:indoors|inside)|"
    r"get\s+(?:inside|indoors)|conserve\s+water|do\s+not\s+(?:drink|use|enter|travel|drive|go|"
    r"approach|touch|return)|leave\s+(?:the\s+area|now|immediately|your\s+home)|"
    r"(?:find|use|take|seek)\s+(?:an?\s+)?alternate\s+routes?|merge\s+(?:left|right)|"
    r"call\s+911)\b"
)
_AFTER_BEING = _rx(r"\b(?:to\s+be|been|being|was|were|is|are|not)\s*$")
_LEAD_IN = _rx(
    r"(?:^|please|kindly|should|must|need\s+to|needs\s+to|have\s+to|has\s+to|"
    r"(?:asked|urged|advised|encouraged|ordered|told|requested|required|reminded|directed|"
    r"instructed|recommended)\s+to|to|also|now|immediately|"
    r"\bfor\s+(?:more\s+)?(?:\w+\s+)?(?:info\w*|assistance|help|questions|updates|details)\b[^.!?]{0,40}|"
    r"\blevel\s+\w+\s*[(\-:]?|"
    r"\b(?:if|when|while|unless)\b[^.!?]{0,80}|,?\s*\bbut|"
    r"\b(?:residents|everyone|people|public|citizens|drivers|motorists|those|anyone|customers|"
    r"students|staff|homeowners|occupants|individuals|visitors|travelers|you|all)\b[^.!?]{0,60})"
    r"\s*$"
)
_INFO_VERBS = _rx(
    r"^(?:check|visit|go\s+to|monitor|listen|tune\s+in|tune\s+to|follow|sign\s+up|register|"
    r"watch|look|information\s+link)\b"
)
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\n+|\s+[-\u2013\u2014•|]\s+|^[-\u2013\u2014•]\s*")


def clauses(text: str) -> list[str]:
    return [
        c.strip(" \t\"'()*•-\u2013\u2014") for c in _CLAUSE_SPLIT.split(text) if c and c.strip()
    ]


def guidance_actions(text: str) -> list[str]:
    """The protective actions a text asks for, one entry per distinct action (normalized).

    A verb counts where an instruction can start: at the start of a clause, after a lead-in
    ("please", "should", "asked to", "and", an "if ...," condition), or after a comma that
    follows another action in the same clause ("Drop, cover, hold on").
    """
    found: list[str] = []
    for clause in clauses(text):
        last_end = None
        for m in _VERB.finditer(clause):
            before = clause[: m.start()].strip().lower()
            between = clause[last_end : m.start()].strip().lower() if last_end is not None else None
            listed = between is not None and between in (",", "", "and", "or", "then", ", and")
            if before and not listed and not _LEAD_IN.search(before):
                continue
            last_end = m.end()
            action = " ".join(m.group(0).lower().split())
            action = re.sub(r"^don'?t\b", "do not", action)
            if action not in found:
                found.append(action)
    for m in _STRONG.finditer(text):
        if _AFTER_BEING.search(text[max(0, m.start() - 12) : m.start()].lower()):
            continue
        v = _VERB.match(m.group(0))
        action = " ".join((v.group(0) if v else m.group(0).split()[0]).lower().split())
        if action not in found:
            found.append(action)
    for clause in clauses(text):
        if _ENDED.search(clause):
            continue
        for m in _NOUN_GUIDANCE.finditer(clause):
            action = " ".join(m.group(0).lower().split())
            if not any(action.startswith(a) or a.startswith(action) for a in found):
                found.append(action)
    if _INFO_LINK.search(text) and "visit" not in found and "check" not in found:
        found.append("information link")
    return found


# --- time --------------------------------------------------------------------------------

_CLOCK = _rx(
    r"\b(?:\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)(?=\W|$)|\d{1,2}:\d{2}|"
    r"\d{4}\s*(?:hrs|hours|hrs\.)|noon|midnight)"
)
_DAY = _rx(
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tonight|tomorrow|today|"
    r"this\s+(?:morning|afternoon|evening|weekend)|overnight)\b"
)
_DATE = _rx(
    r"(?<![\d./])(?:(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])(?:/\d{2,4})?(?![\d/])"
    r"(?!\s*(?:mile|mi\b|inch|in\b|of\s+a\s+mile))|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|"
    r"sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b)"
)
_DURATION = _rx(
    r"\b(?:for|over|within|in)\s+(?:the\s+)?(?:next\s+)?(?:\d+|one|two|three|several|few)\s*"
    r"(?:-\s*\d+\s*)?(?:minutes?|mins?|hours?|hrs?|days?)\b|"
    r"\bnext\s+(?:\d+|few|several|one|two)\s+(?:minutes?|hours?|days?)\b"
)
_NOW = _rx(
    r"\b(?:now|immediately|immediate(?!\s+(?:area|vicinity|family|families|surroundings))|"
    r"right\s+away|asap|as\s+soon\s+as\s+possible|at\s+once|without\s+delay|"
    r"effective\s+immediately|at\s+a\s+moment'?s\s+notice)\b"
)
#: "At this time" is time only as the time of an instruction ("avoid travel at this time").
_AT_THIS_TIME = _rx(r"\bat\s+this\s+time\b")
_NOT_NOW = _rx(
    r"\bnow\s+(?:open|opened|closed|lifted|over|contained|clear|safe|reopened|been|in\s+effect|"
    r"available|back|cancel+ed|resolved|restored|expired)\b|\bimmediate\s+(?:area|vicinity)\b"
)
_EXPIRY = _rx(
    r"\b(?:expires?|expired|expiration|until\s+further\s+notice|in\s+effect\s+until|"
    r"remains?\s+in\s+effect\s+(?:until|through|till)|valid\s+(?:until|through)|"
    r"will\s+be\s+lifted|next\s+update|updates?\s+(?:will|at|by|to\s+follow)|"
    r"more\s+information\s+(?:will|to\s+follow))\b"
)
_UNTIL = _rx(r"\b(?:until|till|til)\b")
_IMPACT = _rx(
    r"\b(?:expected\s+(?:to|at|by|around|between|within|later|soon|overnight|tonight)|"
    r"(?:opening|reopen\w*|clear\w*|expected|end\w*|lift\w*)\s+(?:very\s+)?soon|"
    r"will\s+(?:begin|start|last|continue|end|reach|impact|affect|"
    r"arrive|move|hit|occur)|begin(?:s|ning)?\s+(?:at|around|by|tonight|today|tomorrow|this|on|"
    r"shortly)|starting\s+(?:at|around|tonight|today|tomorrow|this|on)|"
    r"through\s+(?:tonight|today|tomorrow|the\s+(?:morning|afternoon|evening|weekend|night|day)|"
    r"\w+day)|later\s+(?:today|tonight|this))\b"
)


def time_kinds(text: str) -> dict[str, bool]:
    """The three kinds of time: until impact, time to act, and expiry."""
    out = {"time_impact": False, "time_action": False, "time_expiry": False}
    if _NOW.search(_NOT_NOW.sub(" ", text)):
        out["time_action"] = True
    if _EXPIRY.search(text):
        out["time_expiry"] = True
    if _IMPACT.search(text):
        out["time_impact"] = True
    for clause in clauses(text):
        acts = bool(guidance_actions(clause))
        absolute = bool(
            _CLOCK.search(clause)
            or _DAY.search(clause)
            or _DATE.search(clause)
            or _DURATION.search(clause)
        )
        if acts and _AT_THIS_TIME.search(clause):
            out["time_action"] = True
        if _UNTIL.search(clause):
            if acts and not _EXPIRY.search(clause):
                out["time_action"] = True
            else:
                out["time_expiry"] = True
        elif acts and (absolute or re.search(r"\bbefore\b", clause, IC)):
            out["time_action"] = True
        elif absolute and not _EXPIRY.search(clause):
            out["time_impact"] = True
    return out


# --- location ----------------------------------------------------------------------------

_BOUNDARY = _rx(
    r"\b(?:city\s+of\s+\w+|town\s+of\s+\w+|village\s+of\s+\w+|neighborhood\s+of\s+\w+|"
    r"zip\s+codes?\s+\d|\d{5}(?:,\s*\d{5})+)\b"
)
#: A named county, parish, borough or township: a name before the word, never "the county".
_NAMED_JURISDICTION = _rx(
    r"\b([a-z][\w.'-]*)\s+(?:county|counties|parish|borough|township|twp|cnty|co\.)(?=\W|$)"
)
_JURISDICTION_GENERIC = _rx(
    r"^(?:the|this|that|your|our|entire|each|every|a|an|all|surrounding|neighboring|nearby|"
    r"whole|same|other|its|their|in|of|for|and|to|at|on|from)$"
)
#: Names before a word that marks a populated place or a named burn area.
_NAMED_AREA = re.compile(
    r"\b([A-Z][a-z]+(?:\s+(?:and\s+)?[A-Z][a-z]+){0,3})\s+(?i:residents|area|community|"
    r"neighborhoods?|subdivisions?|burn\s+(?:area|scar))\b"
)
_STATE_NAMES = _rx(r"\b(?:" + "|".join(sorted(sd.STATES.values(), key=len, reverse=True)) + r")\b")
#: A named road: a word before a road word ("Sampleton Road"), unless that word is generic.
_ROAD_NAMED = _rx(
    r"\b([a-z0-9][\w'.-]*)\s+(?:road|rd|street|avenue|ave|boulevard|blvd|highway|hwy|"
    r"parkway|pkwy|freeway|fwy|expressway|expy|turnpike|bypass|pike)\b"
)
_ROAD_GENERIC = _rx(
    r"^(?:the|a|an|all|any|local|area|major|closed|flooded|icy|your|our|this|that|these|"
    r"those|county|state|city|nearby|affected|surrounding|on|off|of|to|in|from|and|or|"
    r"secondary|back|dirt|gravel|private|public|some|many|several|other|alternate|open|"
    r"slick|wet|impassable|blocked|damaged|nearest|busy|multiple)$"
)
_ROAD_NUMBERED = _rx(
    r"\b(?:interstate\s*\d+|i-\s?\d+|us-?\s?\d+|u\.s\.\s+\d+|sr-?\s?\d+|state\s+route\s+\d+|"
    r"state\s+road\s+\d+|route\s+\d+|rte\.?\s*\d+|county\s+road\s+\w+|cr\s?-?\d+|"
    r"fm\s?-?\d+|hwy\.?\s?-?\d+|highway\s+\d+|mile\s+marker|mm\s*\d+|exit\s+\d+|"
    r"intersection|crossroads|exit\s+ramp|on-?ramp|off-?ramp)\b"
)
#: Numbered roads in other forms: "SH359", "SH 359", "M-30", "I40", "K-10".
_ROAD_CODE = re.compile(r"\b(?:(?:SH|SR|US|FM|RM|STH|CTH)\s?-?\d{1,4}[A-Z]?|[IMK]-?\d{1,3})\b")
_ROAD_SUFFIX_MIXED = re.compile(
    r"\b[A-Z][a-z]+\s+(?:St|Dr|Ln|Ct|Cir|Way|Trl|Trail|Pl|Loop|Court|Circle|Place|Lane|"
    r"Drive)\b\.?"
)
_ROAD_SUFFIX_CAPS = re.compile(r"\b([A-Z]{3,})\s+(?:ST|DR|LN|CT|AVE|RD|BLVD|HWY|LANE|DRIVE)\b")
_BETWEEN = _rx(
    r"\bbetween\s+[a-z0-9][\w.'-]*(?:\s+[a-z0-9][\w.'-]*)?\s+(?:and|&)\s+[a-z0-9][\w.'-]*"
    r"\s+(?:road|rd|street|st|avenue|ave|blvd|highway|hwy|drive|dr|lane|ln|way|parkway|pkwy)\b"
)
_LANDMARK = _rx(
    r"\b(?:schools?|elementary|middle\s+school|high\s+school|campus|universit(?:y|ies)|"
    r"college|parks?|mall|plaza|shopping\s+center|hospital|medical\s+center|church|airport|"
    r"station|depot|stadium|arena|fairgrounds?|library|courthouse|city\s+hall|"
    r"community\s+center|recreation\s+center|civic\s+center|marina|beach(?:es)?|pier|harbor|"
    r"river|creek|lake|reservoir|dam|canal|bay|mountain|mount|ridge|canyon|valley|hills?|"
    r"forest|refinery|plant|factory|warehouse|apartments?|hotel|motel|gas\s+station|"
    r"bridge|tunnel|landfill|cemetery|golf\s+course|trailhead|campground|rail\s?yard|"
    r"terminal|shopping\s+mall|air\s+base)\b"
)
_ZONE = re.compile(
    r"\b(?i:zones?)\s+(?!(?:OF|IN|IS|AND|THE|TO|ARE|FOR|AT|ON|OR|AS|IT|BE|WILL)\b)"
    r"(?:[A-Z]{1,3}\d{0,4}|\d{1,4}[A-Z]?)\b|(?i:zonehaven|genasys\s+protect)"
)
_ZONE_ID = re.compile(
    r"\b(?!(?:US|SR|FM|CR|COVID|HWY|RT|RTE|EXIT|MM|SARS|PM|AM)-)[A-Z]{2,5}-[A-Z]?\d{1,4}[A-Z]?\b"
)
_ZONE_CONTEXT = _rx(r"\bzones?\b|\bevacuat")
#: A lettered evacuation level or zone: "Level A", "Zone B" (a number is a stage, not a zone).
_ZONE_LETTER = re.compile(r"\b(?i:level|zone)\s+[A-Z]\b(?![-\w])")
#: A road-looking name that is a fire's or an incident's name ("Old Trail Fire").
_NAMED_FIRE = _rx(r"^\s+(?:fire|complex|incident)\b")
#: A capitalized name after a locative word, in a mixed-case text: "residents of Sampleton".
_NAMED_PLACE = re.compile(
    r"\b(?i:in|near|of|around|outside|throughout|across|within|for|from|at|into|toward|towards|"
    r"avoid|leave|evacuate|enter|entering|visiting)"
    r"\s+(?:(?i:the)\s+)?(?:(?i:north|south|east|west|northern|southern|eastern|western|central|"
    r"downtown|greater|unincorporated|old)\s+)?([A-Z][a-z]{2,}(?:[\s-][A-Z][a-z]{2,}){0,2})\b"
)
_NOT_A_PLACE_NAME = _rx(
    r"^(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|"
    r"april|may|june|july|august|september|october|november|december|zone|zones|level|phase|"
    r"stage|area|areas|road|county|city|town|the|this|that|these|those|your|our|all|effect|"
    r"local|civil|affected|surrounding|entire|whole|burn|impacted|danger|hazard|staging|service|"
    r"coverage|outage|flood|storm|fire|evacuation|evacuated|nearby|other|any|each|"
    r"place|shelter|evacuation|evacuations|order|warning|alert|alerts|emergency|police|fire|"
    r"sheriff|department|office|information|updates?|details|today|tonight|tomorrow|now|"
    r"further|notice|english|spanish|facebook|twitter|nixle|everbridge|codered|instagram|"
    r"home|homes|residents|public|safety|health|water|power|traffic|state|national|federal|"
    r"order|immediately|advance|addition|response|support|regards|reference|accordance|"
    r"progress|case|order|time|minutes|hours|preparation)$"
)
_BLOCK_OF = _rx(r"\b\d+\s+block\s+of\b")
#: The same in an all-caps text, where only the word's own kind can tell a name.
_CAPS_PLACE = re.compile(
    r"\b(?:IN|NEAR|OF|AROUND|OUTSIDE|THROUGHOUT|ACROSS|WITHIN|FOR|FROM|INTO|TOWARD)\s+(?:THE\s+)?"
    r"(?:(?:NORTH|SOUTH|EAST|WEST|NORTHERN|SOUTHERN|EASTERN|WESTERN|CENTRAL|DOWNTOWN)\s+)?"
    r"([A-Z]{4,})\b"
)
_VAGUE = _rx(
    r"\b(?:in\s+your\s+area|in\s+the\s+area|your\s+area|this\s+area|near\s+you|"
    r"the\s+affected\s+areas?|affected\s+areas?|nearby|your\s+location|local\s+area|"
    r"surrounding\s+area|the\s+vicinity)\b"
)


def location_kinds(text: str, place_words: Iterable[str] = ()) -> dict[str, bool]:
    """The kinds of location a text names (the source's own name already blanked)."""
    mixed = sum(ch.isupper() for ch in text) < 0.6 * max(1, sum(ch.isalpha() for ch in text))
    boundary = bool(_BOUNDARY.search(text) or _STATE_NAMES.search(text))
    if not boundary:
        boundary = any(
            not _JURISDICTION_GENERIC.match(m.group(1)) for m in _NAMED_JURISDICTION.finditer(text)
        )
    if not boundary and mixed:
        for m in _NAMED_AREA.finditer(text):
            first = m.group(1).split()[0]
            if not _NOT_A_PLACE_NAME.match(first) and not _ALERT_WORDS.fullmatch(first):
                boundary = True
                break
    if not boundary:
        for w in place_words:
            if re.search(rf"\b{re.escape(w)}\b", text, IC):
                boundary = True
                break
    if not boundary and mixed:
        for m in _NAMED_PLACE.finditer(text):
            first = m.group(1).split()[0].split("-")[0]
            if not _NOT_A_PLACE_NAME.match(first) and not _ROAD_WORDS.fullmatch(first):
                boundary = True
                break
    if not boundary and not mixed:
        for m in _CAPS_PLACE.finditer(text):
            w = m.group(1)
            if not (
                _NOT_A_PLACE_NAME.match(w)
                or _ROAD_WORDS.fullmatch(w)
                or _EN.fullmatch(w)
                or _VERB.fullmatch(w)
                or _ALERT_WORDS.fullmatch(w)
                or _LANDMARK.fullmatch(w)
                or w.upper() in _NOT_ACRONYMS
                or any(rx.fullmatch(w) for rx in HAZARD_WORDS.values())
            ):
                boundary = True
                break
    named = any(not _ROAD_GENERIC.match(m.group(1)) for m in _ROAD_NAMED.finditer(text))
    caps_named = any(not _ROAD_GENERIC.match(m.group(1)) for m in _ROAD_SUFFIX_CAPS.finditer(text))
    suffix = [
        m for m in _ROAD_SUFFIX_MIXED.finditer(text) if not _NAMED_FIRE.match(text[m.end() :])
    ]
    road = bool(
        named
        or _ROAD_NUMBERED.search(text)
        or _ROAD_CODE.search(text)
        or (bool(suffix) if mixed else caps_named)
        or _BETWEEN.search(text)
        or _BLOCK_OF.search(text)
    )
    landmark = bool(_LANDMARK.search(text))
    zone = bool(
        _ZONE.search(text)
        or (_ZONE_ID.search(text) and _ZONE_CONTEXT.search(text))
        or (_ZONE_LETTER.search(text) and _ZONE_CONTEXT.search(text))
    )
    out = {
        "loc_boundary": boundary,
        "loc_road": road,
        "loc_landmark": landmark,
        "loc_zone": zone,
    }
    out["location"] = any(out.values())
    out["loc_vague_or_none"] = not out["location"] or bool(_VAGUE.search(text))
    if out["location"]:
        out["loc_vague_or_none"] = False
    return out


# --- links, abbreviations, evacuation words ----------------------------------------------

_URL = _rx(
    r"\b(?:https?://)?(?:www\.)?((?:[a-z0-9-]+\.)+(?:gov|com|org|net|us|edu|mil|info|ly|co|io|"
    r"me|cc|health|alert|ca|gl|at|in|link))(?:/[^\s]*)?",
)
_SHORTENERS = frozenset(
    {
        "bit.ly",
        "tinyurl.com",
        "ow.ly",
        "t.co",
        "goo.gl",
        "is.gd",
        "buff.ly",
        "rb.gy",
        "cutt.ly",
        "tiny.cc",
        "shorturl.at",
        "bitly.com",
        "lnkd.in",
        "rebrand.ly",
        "t.ly",
    }
)
_SOCIAL = frozenset(
    {"facebook.com", "twitter.com", "x.com", "instagram.com", "nextdoor.com", "youtube.com"}
)
LINK_KINDS = ("shortener", "social", "gov", "org", "com", "net", "us", "edu", "mil", "other")


def link_kinds(text: str) -> list[str]:
    """The kinds of web address in a text, by host: a shortener, social media, else the ending."""
    out: list[str] = []
    for m in _URL.finditer(text):
        host = m.group(1).lower()
        if re.fullmatch(r"(?:[a-z]\.)+[a-z]", host):  # "a.m.", "p.m.", "u.s."
            continue
        if host.startswith("www."):
            host = host[4:]
        if host in _SHORTENERS:
            kind = "shortener"
        elif any(host == s or host.endswith("." + s) for s in _SOCIAL):
            kind = "social"
        else:
            tld = host.rsplit(".", 1)[-1]
            kind = tld if tld in ("gov", "org", "com", "net", "us", "edu", "mil") else "other"
        if kind not in out:
            out.append(kind)
    return out


_TIME_ZONES = re.compile(r"\b(?:PST|PDT|MST|MDT|CST|CDT|EST|EDT|AKST|AKDT|HST|HDT)\b")
_ABBREVIATIONS = _rx(
    r"\b(?:co\.|rd\.|ave\.|blvd\.?|hwy\.?|dept\.?|twp\.?|mt\.|ft\.|approx\.?|info|evac|govt|"
    r"ofc|hrs|pkwy|jct|asap|pls|ppl|w/|b/c|esp\.)(?=\W|$)"
)
_CAPS_TOKEN = re.compile(r"\b[A-Z]{2,6}s?\b")
_NOT_ACRONYMS = frozenset(
    [
        "I",
        "A",
        "AM",
        "PM",
        "OK",
        "TV",
        "US",
        "USA",
        "NO",
        "ON",
        "IN",
        "AT",
        "TO",
        "IS",
        "IT",
        "OR",
        "BY",
        "AN",
        "AS",
        "WE",
        "BE",
        "DO",
        "IF",
        "OF",
        "UP",
        "GO",
        "SO",
        "HE",
        "ME",
        "MY",
        "NOW",
        "ALL",
        "AND",
        "THE",
        "YOU",
        "ARE",
        "OUT",
        "OFF",
        "FOR",
        "NOT",
        "NEW",
        "YES",
        "ONE",
        "TWO",
        "SET",
        "RUN",
        "USE",
        "GET",
        "HAS",
        "HAD",
        "ITS",
        "OUR",
        "AREA",
        "STAY",
        "LEAVE",
        "AVOID",
        "ALERT",
        "ORDER",
        "ZONE",
        "CLEAR",
        "SAFE",
        "TEST",
        "FIRE",
        "FLOOD",
        "WATER",
        "BOIL",
        "ROAD",
        "HOME",
        "HELP",
        "CALL",
        "ONLY",
        "STOP",
        "LOCK",
        "HIDE",
        "FIGHT",
        "DROP",
        "COVER",
        "HOLD",
        "READY",
        "ROADS",
        "HOMES",
        "THIS",
        "THAT",
        "WITH",
        "FROM",
        "WILL",
        "YOUR",
        "ARE",
        "WAS",
        "WERE",
        "BEEN",
        "HAVE",
        "MUST",
        "DONT",
        "INTO",
        "NEAR",
        "LEFT",
        "EAST",
        "WEST",
        "NORTH",
        "SOUTH",
        "SMOKE",
        "GAS",
        "LEAK",
        "OPEN",
        "SHUT",
        "GAME",
        "OVER",
        "DAY",
        "WEEK",
        "TODAY",
        "CITY",
        "TOWN",
        "STATE",
        "NEWS",
        "INFO",
        "WARN",
        "AWAY",
        "BACK",
        "MOVE",
        "TAKE",
        "SEEK",
        "HIGH",
        "LOW",
        "RISK",
        "DRIVE",
        "DRINK",
        "LIVE",
        "LIFE",
        "ALSO",
        "EAS",
        "WEA",
        "IPAWS",
        "CMAS",
        "NWEM",
    ]
)
_DIRECTIONS = re.compile(r"\b(?:NB|SB|EB|WB)\b")


def abbreviations(text: str) -> int:
    """How many abbreviations or acronyms a text uses (agency initials, short forms, zones)."""
    letters = [ch for ch in text if ch.isalpha()]
    caps = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0.0
    n = len(_TIME_ZONES.findall(text)) + len(_ABBREVIATIONS.findall(text))
    n += len(_DIRECTIONS.findall(text))
    known = [m.group(0) for m in _ACRONYM_KNOWN.finditer(text)]
    known += [m.group(0) for m in _ACRONYM_ENDING.finditer(text) if len(m.group(0)) >= 3]
    if caps < 0.5:
        tokens = [t for t in _CAPS_TOKEN.findall(text) if t.rstrip("s") not in _NOT_ACRONYMS]
        tokens = [
            t for t in tokens if not _TIME_ZONES.fullmatch(t) and not _DIRECTIONS.fullmatch(t)
        ]
        n += len(tokens)
    else:
        n += len(known)
    return n


EVAC_SCHEMES = {
    "evac_warning_order": _rx(
        r"\bevac(?:uation)?\s+(?:warnings?|orders?)\b|\b(?:warning|order)s?\s+to\s+evacuate\b"
    ),
    "evac_levels": _rx(r"\blevel\s*(?:1|2|3|one|two|three|i{1,3})\b"),
    "evac_ready_set_go": _rx(
        r"\bready[,\s-]+set[,\s-]+go\b|\b(?:be|get)\s+set\b|\b(?:ready|set|go)\s+"
        r"(?:status|level|order|stage)\b|\bgo\s+now\b(?=.*\b(?:ready|set|level)\b)"
    ),
    "evac_voluntary_mandatory": _rx(r"\b(?:voluntary|mandatory)\b"),
    "evac_pre_evacuation": _rx(r"\bpre-?\s?evacuat\w*\b"),
}
_EVAC = _rx(r"\bevac\w*")


def evacuation_terms(text: str) -> dict[str, bool]:
    """Which evacuation-stage wordings a text uses (several can apply)."""
    evac = bool(_EVAC.search(text))
    out = {}
    for name, rx in EVAC_SCHEMES.items():
        hit = bool(rx.search(text))
        if name in ("evac_levels", "evac_voluntary_mandatory", "evac_ready_set_go"):
            hit = hit and evac
        out[name] = hit
    out["evac_terms"] = any(out.values())
    return out


#: Words of a message about a missing person (Olson et al. removed these whatever their code).
#: The words the privacy rule reads too (English only here: Spanish units are not coded).
_MISSING_PERSON = privacy.MISSING_PERSON_EN


#: Words of a test, drill or exercise sent under a real event code (Olson et al. removed tests
#: and demonstrations whatever their code).
_ABOUT_TEST = _rx(
    r"\bthis\s+is\s+(?:only\s+)?a\s+test\b|\btest(?:ing)?\s+(?:message|alert|of\s+the|only)\b|"
    r"\b(?:a|this)\s+(?:drill|exercise)\b|\bno\s+action\s+(?:is\s+)?(?:required|needed|necessary)\b|"
    r"\bdisregard\b|\bsent\s+in\s+error\b|\bonly\s+a\s+test\b|"
    r"\btesting\s+(?:ipaws|wea|eas|cmas|the\s+\w+\s+(?:alert|warning|notification)\s+system)\b|"
    r"\b(?:ipaws|wea|eas|cmas)\s+test(?:ing)?\b|\btest\s+#\s?\d"
)


# --- one unit ----------------------------------------------------------------------------


@dataclass
class UnitCodes:
    """The codes of one unit. ``coded`` is False for Spanish or empty units (codes are None)."""

    unit: str
    length: int
    coded: bool
    not_coded_reason: str | None = None
    values: dict[str, Any] = field(default_factory=dict)


#: Every code a coded unit carries, in table order.
CODE_FIELDS = (
    "hazard",
    "hazard_category",
    "hazard_category_source",
    "hazard_description",
    "hazard_characteristics",
    "hazard_impacts",
    "source_named",
    "guidance",
    "n_actions",
    "guidance_protective",
    "guidance_information",
    "time",
    "time_impact",
    "time_action",
    "time_expiry",
    "location",
    "loc_boundary",
    "loc_road",
    "loc_landmark",
    "loc_zone",
    "loc_vague_or_none",
    "link",
    "link_kinds",
    "abbreviations",
    "n_abbreviations",
    "all_caps",
    "evac_terms",
    "evac_warning_order",
    "evac_levels",
    "evac_ready_set_go",
    "evac_voluntary_mandatory",
    "evac_pre_evacuation",
    "complete",
    "about_missing_person",
    "about_test",
)


def code_text(text: str, ctx: Context | None = None) -> dict[str, Any]:
    """Every code for one English text."""
    ctx = ctx or Context()
    spans = find_source(text, ctx)
    rest = blank(text, spans)
    category, cat_source = hazard_category(rest, ctx.event_codes)
    block_rest = rest
    if cat_source != "words" and ctx.block_text and ctx.block_text != text:
        block_rest = blank(ctx.block_text, find_source(ctx.block_text, ctx))
        block_category, block_source = hazard_category(block_rest, ctx.event_codes)
        if block_source == "words":
            category, cat_source = block_category, "message_words"
    if cat_source not in ("words", "message_words"):
        for cue_category, rx in CATEGORY_CUES.items():
            if rx.search(block_rest):
                category, cat_source = cue_category, "cue_words"
                break
    named_hazard = has_hazard(rest)
    hazard_spans = [m.span() for rx in HAZARD_WORDS.values() for m in rx.finditer(rest)]
    distinct = {rest[a:b].lower() for a, b in hazard_spans}
    # A description is said about a named hazard, beyond its name: the hazard's own name (a
    # "power outage") is not its impact, unless another hazard is named beside it.
    described = rest if len(distinct) > 1 else blank(rest, hazard_spans)
    chars = named_hazard and bool(_CHARACTERISTICS.search(described))
    impacts = named_hazard and bool(_IMPACTS.search(described))
    actions = guidance_actions(rest)
    protective = [a for a in actions if not _INFO_VERBS.match(a)]
    info = [a for a in actions if _INFO_VERBS.match(a)]
    times = time_kinds(rest)
    places = location_kinds(rest, ctx.place_words | place_words_of([ctx.organization]))
    links = link_kinds(text)
    n_abbr = abbreviations(text)
    letters = [ch for ch in text if ch.isalpha()]
    caps = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0.0
    out: dict[str, Any] = {
        "hazard": named_hazard,
        "hazard_category": category,
        "hazard_category_source": cat_source,
        "hazard_description": chars or impacts,
        "hazard_characteristics": chars,
        "hazard_impacts": impacts,
        "source_named": bool(speaker_spans(text, ctx)),
        "guidance": bool(actions),
        "n_actions": len(actions),
        "guidance_protective": bool(protective),
        "guidance_information": bool(info),
        "time": any(times.values()),
        **times,
        **places,
        "link": bool(links),
        "link_kinds": links,
        "abbreviations": n_abbr > 0,
        "n_abbreviations": n_abbr,
        "all_caps": caps > 0.9,
        **evacuation_terms(rest),
        "about_missing_person": bool(_MISSING_PERSON.search(text)),
        "about_test": bool(_ABOUT_TEST.search(text)),
    }
    out["complete"] = all(
        out[k] for k in ("hazard", "location", "time", "source_named", "guidance")
    )
    return {k: out[k] for k in CODE_FIELDS}


def code_unit(unit: str, text: str | None, ctx: Context | None = None, spanish: bool = False):
    """Code one unit, or say why not (``empty``, ``spanish_block``, ``spanish_text``)."""
    text = text or ""
    if not text.strip():
        return UnitCodes(unit, len(text), False, "empty")
    if spanish:
        return UnitCodes(unit, len(text), False, "spanish_block")
    if looks_spanish(text):
        return UnitCodes(unit, len(text), False, "spanish_text")
    return UnitCodes(unit, len(text), True, None, code_text(text, ctx))


def full_text(headline: str | None, description: str | None, instruction: str | None) -> str:
    """The full-text unit: headline, description and instruction, one per line."""
    return "\n".join(t.strip() for t in (headline, description, instruction) if t and t.strip())


_PLACE_STOP = _rx(
    r"^(?:county|counties|city|town|township|village|borough|parish|area|areas|polygon|"
    r"portion|portions|part|parts|north|south|east|west|northern|southern|eastern|western|"
    r"central|the|and|of|in|near|all|zone|zones|zip|code|codes|state|entire|statewide|"
    r"including|including|within|miles?|radius|around|unincorporated|affected|alert|"
    r"location|locations|evacuation|immediate|vicinity|region|district|community|ground|grounds|"
    r"proving|range|management|services?|office|department|agency|division|authority|"
    r"government|commission|center|operations|communications|security|homeland|police|"
    r"sheriff|fire|rescue|emergency|public|safety|health|water|utilit(?:y|ies)|systems?|"
    r"program|alerts?|warning|notifications?|united|national|regional|metro|metropolitan|"
    r"joint|consolidated|unified|nation|tribe|tribal|band|indians|reservation|university|"
    r"college|campus|school|schools|airport|base|army|navy|force|marine|guard|corps)$"
)


_ROAD_WORDS = _rx(
    r"road|roads|street|streets|avenue|boulevard|highway|highways|parkway|freeway|"
    r"expressway|turnpike|lane|drive|route|interstate"
)


def place_words_of(area_descriptions: Iterable[str | None]) -> frozenset[str]:
    """Distinctive words of a message's area descriptions (place names, mostly), lowercased.

    Generic words (county, area, north ...), hazard words, guidance verbs, road and landmark
    words and common English words are left out, so that only names remain.
    """
    out = set()
    for d in area_descriptions:
        for w in re.findall(r"[A-Za-z][A-Za-z'.-]{3,}", d or ""):
            w = w.strip(".'-")
            if len(w) < 4 or _PLACE_STOP.match(w) or _EN.fullmatch(w) or _VERB.fullmatch(w):
                continue
            if any(rx.fullmatch(w) for rx in HAZARD_WORDS.values()):
                continue
            if _LANDMARK.fullmatch(w) or _ROAD_GENERIC.match(w) or _ROAD_WORDS.fullmatch(w):
                continue
            out.add(w.lower())
    return frozenset(out)
