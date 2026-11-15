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

from warntext import senders as sd

CODEBOOK_VERSION = "1"
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
    r"agua|fuego|incendio|polic[ií]a|n[uú]mero|m[aá]s|informaci[oó]n|hasta|nuevo)\b"
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
_ACRONYM_ENDING = re.compile(r"\b[A-Z]{1,5}(?:SO|PD|FD|OEM|EMA|DEM|OES|FPD|DPS|EMS)\b")
#: Short agency forms that are only read as a source after a place name ("Sampleton PD") or in
#: the message's opener or signature, since "SO" is also a word in an all-caps text.
_ACRONYM_BARE = re.compile(r"\b(?:PD|SO|FD|EMS|EM|DPS|SD|PSO|OEM|EMA)\b")
_NAME_THEN_BARE = re.compile(r"\b[A-Z][a-z]{2,}\s+(?:PD|SO|FD|EMS|EM|DPS|OEM|EMA)\b")
_JURISDICTION = _rx(
    r"\b(?:county|parish|borough|city|town|township|village|state|tribe|tribal|nation|"
    r"university|campus|base)\b"
)
_ALERT_WORDS = _rx(
    r"\b(?:alert|warning|watch|order|notice|advisory|update|emergency|evacuat\w*|test|"
    r"statement|message|information)\b"
)
_OPENER = re.compile(
    r"^\W*([A-Z][\w.'&/-]*(?:\s+[A-Za-z][\w.'&/-]*){0,7})\s*(?::|-{1,2}|\u2013|\u2014)\s"
)
_SIGNATURE = re.compile(r"(?:^|\s)(?:-{1,2}|\u2013|\u2014|~)\s*([A-Z][\w.'& /-]{2,70}?)\s*\.?\s*$")
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


def organization_words(name: str | None) -> list[str]:
    """The distinctive words of an organization's name (place names, mostly), lowercased."""
    if not name:
        return []
    words = re.findall(r"[A-Za-z][A-Za-z'.-]+", name)
    return [w.lower() for w in words if len(w) >= 3 and not _GENERIC_NAME_WORDS.match(w)]


def find_source(text: str, ctx: Context) -> list[tuple[int, int]]:
    """Spans of the text that name the organization giving the message."""
    spans: list[tuple[int, int]] = []
    spans += [m.span() for m in _AGENCY.finditer(text)]
    spans += [m.span() for m in _ACRONYM_KNOWN.finditer(text)]
    spans += [m.span() for m in _ACRONYM_ENDING.finditer(text) if len(m.group(0)) >= 3]
    spans += [m.span() for m in _NAME_THEN_BARE.finditer(text)]
    for rx in (_OPENER, _SIGNATURE):
        m = rx.search(text)
        if not m:
            continue
        head = m.group(1)
        if (
            _AGENCY.search(head)
            or _ACRONYM_KNOWN.search(head)
            or _ACRONYM_ENDING.search(head)
            or _ACRONYM_BARE.search(head)
            or (_JURISDICTION.search(head) and not _ALERT_WORDS.search(head))
        ):
            spans.append(m.span(1))
    words = organization_words(ctx.organization)
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
                rf"{re.escape(w)}\W+(?:county|city|parish|borough|town)\W+(?:{_AGENCY.pattern}|"
                r"oem|ema|eoc|so|pd|fd|government|officials)",
                window,
                IC | VB,
            ):
                spans.append((m.start(), m.end()))
    return _merge(spans)


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
        r"wildland\s+fires?|fires?|red\s+flag|fire\s+weather)\b"
    ),
    "technological": _rx(
        r"\b(?:(?:structure|house|building|vehicle|industrial|plant|commercial|apartment|"
        r"warehouse|chemical|tire|oil|refinery)\s+fires?|explosions?|gas\s+leaks?|natural\s+gas|"
        r"chemical\s+(?:leak|release|spill|incident|plume)|hazardous\s+materials?|haz-?mats?|"
        r"toxic\s+(?:gas|fumes|chemicals?|smoke|release)|ammonia|chlorine|derail\w*|"
        r"(?:dam|levee)\s+(?:failure|break|breach|collapse)|dam\s+failure|"
        r"(?:bridge|building|structure)\s+collapse|radiological|radiation|nuclear|"
        r"oil\s+spill|pipeline|carbon\s+monoxide|gas\s+main|power\s+plant\s+(?:incident|"
        r"emergency))\b"
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
        r"criminal\s+activity)\b"
    ),
    "public_health": _rx(
        r"\b(?:covid(?:-?19)?|coronavirus|pandemic|outbreak|virus|vaccin\w+|flu|influenza|"
        r"measles|mpox|monkeypox|air\s+quality|unhealthy\s+air|public\s+health\s+(?:emergency|"
        r"order|advisory)|overdoses?|fentanyl|e\.\s?coli|rabies|west\s+nile|opioids?|"
        r"testing\s+site|stay\s+at\s+home\s+order|stay-at-home|quarantine|isolation\s+order)\b"
    ),
    "public_safety": _rx(
        r"\b(?:911|9-1-1)\s+(?:outage|service|is\s+down|not\s+working|problems?|issues?|"
        r"disruption|unavailable)|\b(?:phone|telephone|landline|cell|cellular)\s+(?:outages?|"
        r"service|disruption)|\boutages?\b|\bpower\s+(?:outages?|failure)|\bblackouts?\b|"
        r"\bwater\s+(?:main\s+break|outage|service|pressure|shortage|emergency|"
        r"contamination|restrictions?)|\bboil\s+(?:water|order|advisory|notice)|"
        r"\bdo\s+not\s+drink\b|\btraffic\s+(?:accident|crash|incident|delays?|hazard|"
        r"signals?)|\b(?:crash|collision|accident)\b|\bsewage\b|\bfuel\s+shortage\b"
    ),
    "atmospheric": _rx(
        r"\b(?:flash\s+floods?|floods?|flooding|tornado(?:es)?|thunderstorms?|storms?|"
        r"severe\s+weather|hurricanes?|tropical\s+storms?|typhoons?|storm\s+surge|"
        r"high\s+winds?|winds?|winter\s+storms?|snow|blizzard|ice|icy|freez\w+|"
        r"extreme\s+cold|wind\s+chill|extreme\s+heat|excessive\s+heat|heat\s+wave|heat|"
        r"dust\s+storm|haboob|fog|hail|heavy\s+rain|rain|lightning|tsunami|monsoon|"
        r"rip\s+currents?|high\s+surf)\b"
    ),
    "geophysical": _rx(
        r"\b(?:earthquakes?|quakes?|aftershocks?|shaking|landslides?|mudslides?|mud\s+slides?|"
        r"debris\s+flows?|rock\s?slides?|rock\s?falls?|avalanches?|sinkholes?|volcan\w+|"
        r"eruptions?|lahars?|ash\s?fall)\b"
    ),
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
    r"has\s+(?:started|begun|crossed|jumped|breached|failed))\b"
)
_IMPACTS = _rx(
    r"\b(?:damage[ds]?|destroy(?:ed|ing)?|injur(?:y|ies|ed)|fatalit(?:y|ies)|deaths?|"
    r"power\s+(?:outages?|shut[- ]?offs?|loss)|without\s+(?:power|water|service|phone)|"
    r"loss\s+of\s+(?:power|water|service|life)|"
    r"(?:roads?|streets?|highways?|bridges?|lanes?)\s+(?:are\s+|is\s+|will\s+be\s+)?"
    r"(?:closed|blocked|impassable|flooded|washed\s+out)|closures?|impassable|"
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
    r"throw\s+away|treat|filter|drink|bring\s+in|return|consider|ensure|make\s+sure"
)
_VERB = _rx(rf"\b(?:{_VERBS})\b")
_NOUN_GUIDANCE = _rx(
    r"\b(?:evacuation\s+(?:order|warning|notice)s?|mandatory\s+evacuations?|"
    r"voluntary\s+evacuations?|shelter[- ]in[- ]place|boil\s+(?:water\s+)?(?:notice|advisory|"
    r"order)|do\s+not\s+drink|stay[- ]at[- ]home\s+order|lockdown\s+order|"
    r"curfew\s+(?:is\s+)?in\s+effect)\b"
)
_LEAD_IN = _rx(
    r"(?:^|please|kindly|should|must|need\s+to|needs\s+to|have\s+to|has\s+to|"
    r"(?:asked|urged|advised|encouraged|ordered|told|requested|required|reminded|directed|"
    r"instructed|recommended)\s+to|to|and|or|then|also|now|immediately|"
    r"\bif\b[^.!?]{0,80},|\bwhen\b[^.!?]{0,80},|\bwhile\b[^.!?]{0,80},)\s*$"
)
_INFO_VERBS = _rx(
    r"^(?:check|visit|go\s+to|monitor|listen|tune\s+in|tune\s+to|follow|sign\s+up|register|"
    r"watch|look)\b"
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
            listed = last_end is not None and clause[last_end : m.start()].strip() in (",", "")
            if before and not listed and not _LEAD_IN.search(before):
                continue
            last_end = m.end()
            action = " ".join(m.group(0).lower().split())
            action = re.sub(r"^don'?t\b", "do not", action)
            if action not in found:
                found.append(action)
    for m in _NOUN_GUIDANCE.finditer(text):
        action = " ".join(m.group(0).lower().split())
        if not any(action.startswith(a) or a.startswith(action) for a in found):
            found.append(action)
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
    r"\b(?:\d{1,2}/\d{1,2}(?:/\d{2,4})?|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|"
    r"dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?)\b"
)
_DURATION = _rx(
    r"\b(?:for|over|within|in)\s+(?:the\s+)?(?:next\s+)?(?:\d+|one|two|three|several|few)\s*"
    r"(?:-\s*\d+\s*)?(?:minutes?|mins?|hours?|hrs?|days?)\b|"
    r"\bnext\s+(?:\d+|few|several|one|two)\s+(?:minutes?|hours?|days?)\b"
)
_NOW = _rx(
    r"\b(?:now|immediately|right\s+away|asap|as\s+soon\s+as\s+possible|at\s+once|"
    r"without\s+delay|effective\s+immediately)\b"
)
_NOT_NOW = _rx(
    r"\bnow\s+(?:open|opened|closed|lifted|over|contained|clear|safe|reopened|been|in\s+effect|"
    r"available|back|cancel+ed|resolved|restored|expired)\b|\bimmediate\s+(?:area|vicinity)\b"
)
_EXPIRY = _rx(
    r"\b(?:expires?|expired|expiration|until\s+further\s+notice|in\s+effect\s+until|"
    r"remains?\s+in\s+effect|valid\s+(?:until|through)|will\s+be\s+lifted|"
    r"(?:is|has\s+been|was)\s+lifted|next\s+update|updates?\s+(?:will|at|by|to\s+follow)|"
    r"more\s+information\s+(?:will|to\s+follow))\b"
)
_UNTIL = _rx(r"\buntil\b")
_IMPACT = _rx(
    r"\b(?:expected\s+(?:to|at|by|around|between|within|later|soon|overnight|tonight)|"
    r"arriv\w+|approaching|imminent|will\s+(?:begin|start|last|continue|end|reach|impact|affect|"
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
    r"\b(?:county|counties|parish(?:es)?|borough|city\s+of|town\s+of|township|village\s+of|"
    r"city\s+limits|unincorporated|subdivisions?|downtown|neighborhood\s+of|"
    r"(?:north|south|east|west|northern|southern|eastern|western|central|northeast|northwest|"
    r"southeast|southwest)\s+(?:part|portion|side|half|end|section|parts)|"
    r"zip\s+codes?|\d{5}(?:,\s*\d{5})+)\b"
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
    r"intersection|crossroads)\b"
)
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
_VAGUE = _rx(
    r"\b(?:in\s+your\s+area|in\s+the\s+area|your\s+area|this\s+area|near\s+you|"
    r"the\s+affected\s+areas?|affected\s+areas?|nearby|your\s+location|local\s+area|"
    r"surrounding\s+area|the\s+vicinity)\b"
)


def location_kinds(text: str, place_words: Iterable[str] = ()) -> dict[str, bool]:
    """The kinds of location a text names (the source's own name already blanked)."""
    boundary = bool(_BOUNDARY.search(text) or _STATE_NAMES.search(text))
    if not boundary:
        for w in place_words:
            if re.search(rf"\b{re.escape(w)}\b", text, IC):
                boundary = True
                break
    mixed = sum(ch.isupper() for ch in text) < 0.6 * max(1, sum(ch.isalpha() for ch in text))
    named = any(not _ROAD_GENERIC.match(m.group(1)) for m in _ROAD_NAMED.finditer(text))
    caps_named = any(not _ROAD_GENERIC.match(m.group(1)) for m in _ROAD_SUFFIX_CAPS.finditer(text))
    road = bool(
        named
        or _ROAD_NUMBERED.search(text)
        or (_ROAD_SUFFIX_MIXED.search(text) if mixed else caps_named)
        or _BETWEEN.search(text)
    )
    landmark = bool(_LANDMARK.search(text))
    zone = bool(_ZONE.search(text) or (_ZONE_ID.search(text) and _ZONE_CONTEXT.search(text)))
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
)


def code_text(text: str, ctx: Context | None = None) -> dict[str, Any]:
    """Every code for one English text."""
    ctx = ctx or Context()
    spans = find_source(text, ctx)
    rest = blank(text, spans)
    category, cat_source = hazard_category(rest, ctx.event_codes)
    chars = bool(_CHARACTERISTICS.search(rest))
    impacts = bool(_IMPACTS.search(rest))
    actions = guidance_actions(rest)
    protective = [a for a in actions if not _INFO_VERBS.match(a)]
    info = [a for a in actions if _INFO_VERBS.match(a)]
    times = time_kinds(rest)
    places = location_kinds(rest, ctx.place_words)
    links = link_kinds(text)
    n_abbr = abbreviations(text)
    letters = [ch for ch in text if ch.isalpha()]
    caps = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0.0
    out: dict[str, Any] = {
        "hazard": has_hazard(rest),
        "hazard_category": category,
        "hazard_category_source": cat_source,
        "hazard_description": chars or impacts,
        "hazard_characteristics": chars,
        "hazard_impacts": impacts,
        "source_named": bool(spans),
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
    r"location|locations|evacuation|immediate|vicinity|region|district|community)$"
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
