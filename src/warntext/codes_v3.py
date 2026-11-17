"""Rule-based content codes, codebook version 3 (DRAFT, ``docs/codebook.md`` section 9).

Version 3 is version 2 (:mod:`warntext.codes`, frozen) with the changes in ``CHANGES``. Each
names a general pattern found on the first two hand sheets (both development sets now), and each
is tested on invented messages. Version 2's code is not changed: this module reuses its patterns
and replaces only the functions that change. A build selects the version (``tables.code_rows``).

``Rules(changes)`` codes with any subset of the changes, so that the effect of each one on the
corpus can be counted by leaving it out. ``code_unit`` and ``code_text`` use them all.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

from warntext import codes as v2
from warntext.codes import IC, VB, Context, UnitCodes, _rx, blank, clauses

CODEBOOK_VERSION = "3"

#: Every change from version 2: (name, the code it is about, what it does).
CHANGES: tuple[tuple[str, str, str], ...] = (
    ("lang", "language", "texts not in English are found in general, not only Spanish"),
    ("cut", "source", "a speaker's name never runs across a line break or a sentence end"),
    ("opener_from", "source", "in an opener 'X Alert from Y:', only Y is the organization"),
    ("initials", "source", "initials have a lowercase letter or are a short non-word"),
    ("bare_fire", "source", "a bare 'Fire' after a fire's qualifier ('brush fire') is a fire"),
    ("verb_case", "source", "a capitalized 'Order' after a name is a noun, not a speaking verb"),
    ("signature", "source", "a closing '- X' with a verb or a function word is no signature"),
    ("stamp", "source", "initials, then a date or time, then a colon open the text; '-SD'"),
    ("place_acronym", "source", "'<Place> County OES' is one organization, never a place"),
    ("lines", "source", "each line of the full text may open with a speaker; ';' too"),
    ("by", "source", "'issued by', 'sent by', 'test by' ... name the speaker"),
    ("start_org", "source", "a name and an agency word or acronym that start the text"),
    ("bare_place", "source", "a bare place opener ('Sampleton:') is written as the speaker"),
    ("message_opener", "source", "'Sampleton Boro message.' opens the text with its speaker"),
    ("alert_system", "location", "'Alert Sampleton' is an alert system's name, not a place"),
    ("traffic_alone", "hazard", "'traffic' alone ('obey traffic laws') names no hazard"),
    ("hazard_words", "hazard", "rising water, floodgates, demolition, 'LE activity', 'T.S. X'"),
    ("caused", "hazard_description", "a closure or curfew due to a named hazard is its impact"),
    ("extent", "hazard_description", "imminent, widespread, in various areas, 'to affect'"),
    ("on_roads", "hazard_description", "flooding (water, ice ...) over or on the roads"),
    ("caution", "guidance", "a clause that opens with 'caution' or 'careful' instructs"),
    ("verbs", "guidance", "disperse, store; evacuations issued or ordered; detoured"),
    ("now_in_effect", "time", "'now in effect' is time"),
    ("about", "time", "'in about 30 minutes', 'throughout the night'"),
    ("while", "time", "an instruction 'while' something lasts gives how long"),
    ("immediate_help", "time", "'immediate assistance' or 'immediate danger' is not time"),
    ("caps_clauses", "location", "all-caps clauses of a mixed text are read for place names"),
    ("roads", "location", "'IH 35', 'I 69', mile markers, intersections 'X @ Y', 'at X & Y'"),
    ("place_words", "location", "alert and season words of the area descriptions are no places"),
    ("not_places", "location", "'Wireless', 'various' and like words are not place names"),
    ("particles", "location", "place names may start with El, La, Los, St., Mt., Ft. ..."),
)
ALL = frozenset(name for name, _, _ in CHANGES)
#: Changes written but held back: each waits for an answer on an open definition, so version 3
#: keeps version 2's answer there. They can be switched on to count what they would move.
HELD: tuple[tuple[str, str, str], ...] = (
    (
        "orders",
        "hazard",
        "an order or ban alone (curfew, stay-at-home order, burn ban) is no hazard",
    ),
)
KNOWN = ALL | frozenset(name for name, _, _ in HELD)

# --- language ----------------------------------------------------------------------------

#: Common words of the languages most often sent beside English in this corpus, beyond
#: Spanish: words that are not also English words. Other scripts are found by script.
_LANGUAGE_WORDS = {
    "es": {
        "el",
        "la",
        "los",
        "las",
        "del",
        "que",
        "por",
        "para",
        "una",
        "uno",
        "esta",
        "este",
        "estos",
        "con",
        "al",
        "su",
        "sus",
        "usted",
        "ustedes",
        "ahora",
        "zona",
        "condado",
        "ciudad",
        "inmediatamente",
        "alerta",
        "aviso",
        "refugio",
        "lugar",
        "hogar",
        "agua",
        "fuego",
        "incendio",
        "policia",
        "numero",
        "mas",
        "informacion",
        "hasta",
        "nuevo",
        "orden",
        "humo",
        "evacuacion",
        "carretera",
        "cerrado",
        "cerrada",
        "peligro",
        "tormenta",
        "inundacion",
        "calle",
        "avenida",
        "personas",
        "residentes",
        "de",
        "en",
        "y",
        "es",
        "son",
        "casa",
        "debe",
        "deben",
        "debemos",
        "favor",
        "hay",
        "pide",
        "urgencia",
        "estado",
        "emergencia",
        "toque",
        "queda",
        "quedese",
        "permanecer",
        "seguimos",
        "ayuda",
        "prevenir",
        "si",
        "sin",
        "desde",
        "entre",
        "sobre",
        "muy",
        "todo",
        "todos",
        "ser",
        "cuando",
        "donde",
        "como",
        "le",
        "lo",
        "se",
        "hoy",
        "manana",
        "noche",
        "salga",
        "evacue",
        "evite",
        "llame",
        "visite",
        "puede",
        "pueden",
        "tiene",
        "tienen",
    },
    "fr": {
        "le",
        "les",
        "des",
        "du",
        "et",
        "est",
        "une",
        "pour",
        "dans",
        "avec",
        "sur",
        "aux",
        "vous",
        "nous",
        "cette",
        "qui",
        "ne",
        "pas",
        "sont",
        "votre",
        "vos",
        "veuillez",
        "maintenant",
        "jusqu",
        "eau",
        "feu",
        "rester",
        "quitter",
    },
    "pt": {
        "os",
        "da",
        "do",
        "das",
        "dos",
        "em",
        "um",
        "uma",
        "para",
        "com",
        "nao",
        "voce",
        "agora",
        "casa",
        "fogo",
        "rua",
    },
    "vi": {
        "va",
        "cua",
        "cac",
        "nhung",
        "cho",
        "trong",
        "khong",
        "duoc",
        "la",
        "co",
        "nguoi",
        "khu",
        "vuc",
        "nay",
        "hay",
        "xin",
        "nha",
        "tai",
        "voi",
        "tu",
        "den",
    },
    "tl": {"ang", "ng", "mga", "sa", "ay", "ito", "mula", "kayo", "po", "lamang"},
    "ht": {"nan", "pou", "ak", "yo", "ki", "li", "pa", "gen", "tanpri", "moun", "nou", "kay"},
}
#: English words, for the share: common words of alerts. A text is not English when its other
#: language's words outnumber these clearly.
_ENGLISH_WORDS = frozenset(
    [
        "the",
        "and",
        "of",
        "to",
        "in",
        "for",
        "is",
        "are",
        "your",
        "you",
        "this",
        "on",
        "at",
        "be",
        "will",
        "please",
        "area",
        "now",
        "all",
        "residents",
        "county",
        "city",
        "fire",
        "police",
        "evacuate",
        "shelter",
        "stay",
        "avoid",
        "until",
        "from",
        "with",
        "near",
        "a",
        "an",
        "it",
        "or",
        "as",
        "by",
        "if",
        "not",
        "do",
        "no",
        "we",
        "our",
        "has",
        "have",
        "was",
        "were",
        "can",
        "may",
        "should",
        "must",
        "due",
        "road",
        "street",
        "water",
        "home",
        "information",
        "more",
        "call",
        "visit",
        "warning",
        "alert",
        "emergency",
        "order",
        "notice",
        "update",
        "leave",
        "immediately",
        "safe",
        "safety",
        "public",
        "stay",
        "go",
        "follow",
        "people",
        "flood",
        "storm",
        "power",
        "closed",
        "open",
        "there",
        "their",
        "they",
        "that",
        "these",
        "those",
        "what",
        "when",
        "where",
        "who",
        "which",
        "been",
        "being",
        "into",
        "out",
        "up",
        "down",
        "off",
        "over",
        "under",
        "about",
        "after",
        "before",
        "during",
        "between",
        "through",
        "north",
        "south",
        "east",
        "west",
        "curfew",
        "effect",
        "still",
    ]
)
_OTHER_SCRIPT_SHARE = 0.3
_OTHER_WORDS_MIN = 3
_OTHER_SHARE = 0.4


def _plain(word: str) -> str:
    """A word without its accents, lowercased ("evacuación" -> "evacuacion")."""
    folded = unicodedata.normalize("NFKD", word.lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch)).replace("đ", "d")


def language(text: str) -> str | None:
    """None for an English text; otherwise why it is not English: ``spanish_text``, or
    ``other_language`` (another language's words, or mostly another script).

    A text written mostly in a script other than Latin is not English. A text in Latin script is
    not English when at least three words of one other language occur and they make at least
    40% of that language's and English's common words together, so a Spanish place name or a
    short "En español" line in an English text keeps it English.
    """
    letters = [ch for ch in text if ch.isalpha()]
    if letters:
        other = sum(not unicodedata.name(ch, "").startswith("LATIN") for ch in letters)
        if other / len(letters) >= _OTHER_SCRIPT_SHARE:
            return "other_language"
    words = [_plain(w) for w in re.findall(r"[^\W\d_]+", text)]
    english = sum(w in _ENGLISH_WORDS for w in words)
    best, best_n = None, 0
    for lang, vocab in _LANGUAGE_WORDS.items():
        n = sum(w in vocab and w not in _ENGLISH_WORDS for w in words)
        if n > best_n:
            best, best_n = lang, n
    if best and best_n >= _OTHER_WORDS_MIN and best_n / (best_n + english) >= _OTHER_SHARE:
        return "spanish_text" if best == "es" else "other_language"
    return None


# --- patterns new in version 3 -----------------------------------------------------------

_ABBREVIATIONS = frozenset(
    [
        "co",
        "st",
        "mt",
        "ft",
        "dept",
        "twp",
        "inc",
        "jr",
        "sr",
        "ave",
        "rd",
        "blvd",
        "hwy",
        "govt",
        "cnty",
        "sgt",
        "lt",
        "capt",
        "dr",
        "mr",
        "ms",
        "mrs",
        "no",
        "vs",
        "jct",
        "pkwy",
        "ln",
        "ct",
        "cir",
        "pt",
        "bldg",
    ]
)
_BREAK = re.compile(r"\n|[.!?](?=\s)")
_INITIALS3 = re.compile(
    r"\b(?:[A-Z]{2,6}[0-9]*|[A-Z][a-z]+[A-Z][A-Za-z0-9]*|[A-Z]{2,}[a-z][A-Za-z0-9]*)\b(?![.]\w)"
)
#: Capitalized words that are words, not initials, in an opener ("SEVERE", "URGENT").
_CAPS_WORDS = frozenset(
    [
        "SEVERE",
        "FLASH",
        "URGENT",
        "BREACH",
        "ATTENTION",
        "IMPORTANT",
        "SPECIAL",
        "PUBLIC",
        "LOCAL",
        "ACTIVE",
        "ENDED",
        "LIFTED",
        "CLEAR",
        "CANCEL",
        "CLOSED",
        "CLOSURE",
        "CLOSURES",
        "TRAFFIC",
        "CRASH",
        "LEVEL",
        "ZONE",
        "ZONES",
        "STAGE",
        "PHASE",
        "BOIL",
        "WATER",
        "POWER",
        "OUTAGE",
        "ROAD",
        "ROADS",
        "LANE",
        "LANES",
        "AREA",
        "AREAS",
        "NEW",
        "FINAL",
        "BRUSH",
        "GRASS",
        "SMOKE",
        "HEAT",
        "COLD",
        "WIND",
        "SNOW",
        "STORM",
        "FLOOD",
        "FIRE",
        "ICE",
        "FOG",
        "DUST",
        "HIGH",
        "LOW",
        "EXTREME",
        "DANGER",
        "CAUTION",
        "ORDER",
        "ORDERS",
        "NOTICE",
        "WARNING",
        "WATCH",
        "ALERT",
        "UPDATE",
        "DRILL",
        "TEST",
        "REAL",
        "LIVE",
        "MAJOR",
        "MINOR",
        "LARGE",
        "SMALL",
        "HEAVY",
        "RAIN",
        "HAIL",
        "MANDATORY",
        "VOLUNTARY",
        "IMMEDIATE",
        "PREPARE",
        "MONITOR",
        "AVOID",
        "LEAVE",
        "STAY",
        "SEEK",
        "TAKE",
    ]
)
_FIRE_AS_HAZARD = _rx(
    r"\b(?:veg|vegetation|brush|grass|wild|wildland|forest|structure|house|building|vehicle|car|"
    r"trash|working|commercial|apartment|warehouse|chemical|tire|oil|refinery|large|small|"
    r"major|new)\s+fire\b"
)
_SIGNATURE_WORDS = _rx(
    r"\b(?:to|is|are|was|were|still|will|be|has|have|had|can|may|not|now|works?|working|call|"
    r"dial|in|on|at|for|with|if|when|please|use)\b"
)
_ACRONYM_ENDING3 = re.compile(r"\b[A-Z]{1,5}(?:SO|PD|FD|OEM|EMA|DEM|OES|FPD|DPS|EMS|EM|SD)\b")
_STAMPED = re.compile(
    r"^\W*([A-Z][A-Za-z0-9]{1,9})\s+[\d/.-]{3,10}(?:\s+\d{1,2}(?::\d{2})?\s*(?:[AaPp]\.?[Mm]\.?)?)?"
    r"\s*:"
)
_AGENCY_ACRONYM = r"(?:OES|OEM|EMA|EM|EOC|DES|DEM|HSEM|SO|PD|FD|EMS|SD|DPS|ESD|EMD)"
_PLACE_ACRONYM = re.compile(
    r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,2}\s+(?:County|Co\.?|Cnty|City|Parish|Borough|"
    rf"Boro|Twp\.?|Township|Town|Village)\s+{_AGENCY_ACRONYM})\b"
)
_OPENER3 = re.compile(
    v2._LEAD_STAMP
    + r"([A-Z][\w.'&/-]*(?:[ \t]+[A-Za-z0-9][\w.'&/-]*){0,7})[ \t]*(?::|;|-{1,2}|\u2013|\u2014)"
    r"(?:\s|$)"
)
_SPEAKER_BY = re.compile(
    r"\b(?i:(?:issued|sent|authorized|provided|ordered|requested|declared|test(?:ing)?|alert|"
    rf"message|notification|update)\s+by)\s+(?:(?i:the)\s+)?({v2._NAME})"
)
_AGENCY3 = _rx(
    rf"(?:{v2._AGENCY.pattern})|\b(?:health\s+officer|medical\s+officer|fire\s+chief|"
    r"police\s+chief|county\s+executive|emergency\s+manager|city\s+manager)\b",
    IC | VB,
)
_JURISDICTION_WORD = (
    r"(?:County|Co\.?|Cnty|City|Parish|Borough|Boro|Twp\.?|Township|Town|Village|Tribe|Nation)"
)
_START_ORG = re.compile(
    v2._LEAD_STAMP + r"((?:[A-Z]{2,6}|[A-Z][a-z]+)(?:\s+(?:[A-Z][a-z]+|Co\.))?\s+"
    r"(?i:health\s+officer|sheriff'?s?(?:\s+office)?|police(?:\s+department)?|fire\s+department|"
    r"emergency\s+management)|"
    rf"[A-Z][a-z]{{2,}}(?:\s+[A-Z][a-z]+)?\s+{_JURISDICTION_WORD}\s+{_AGENCY_ACRONYM})\b"
    # Only as the speaker: an opener's punctuation or a speaking verb follows ("... Police are
    # at the scene" names the police as the actor, which the definitions do not settle).
    r"(?=\s*(?:[:\-\u2013\u2014.]|(?i:has\s+(?:an?\s+)?(?:order|issued|ordered)|is\s+(?:issuing|"
    r"ordering|advising|asking|urging)|issu\w*|order\w*|advis\w*|urg\w*|ask\w*|announc\w*|"
    r"declar\w*|request\w*|recommend\w*)\b))"
)
_SUBJECT_VERB3 = re.compile(
    v2._LEAD_STAMP + r"(?:(?i:the)\s+)?([A-Z][\w.'&-]*(?:\s+[A-Za-z][\w.'&-]*){0,4}?)\s+"
    r"(?i:issuing|ordering|announcing|declaring|requesting|urging|advising|asking)\b"
)
_MESSAGE_OPENER = re.compile(
    v2._LEAD_STAMP
    + r"((?:[A-Z][A-Za-z]+\s+){1,3}(?:Borough|Boro|County|Co\.|City|Parish|Twp|Township|Town|"
    r"Village|Tribe|Nation|EM|OEM|EMA|OES))\s+(?i:message|notification|alert|update|notice|"
    r"advisory|announcement)\s*[.:]"
)
_BARE_PLACE = re.compile(v2._LEAD_STAMP + r"([A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,2})\s*:(?:\s|$)")
_OPENER_WORDS = _rx(
    r"^(?:attention|reminder|important|urgent|correction|note|notice|info|update|breaking|new|"
    r"final|details|location|where|when|what|why|who|please|english|spanish|translation|"
    r"subject|re|fwd|from|to|reason|cause|status|action|actions|instructions?|message|"
    r"advisory|statement|summary|description|headline|event|incident|alert|warning|watch|"
    r"order|test|drill|exercise|now|tonight|today|tomorrow|update|updates|issued|effective|"
    r"expires|until|sender|source|contact|phone|more|visit|see|what|response|resources|"
    r"shelters?|road|roads|traffic|weather|forecast|safety|tips?|reminders?|caution|danger)$"
)
_ALERT_SYSTEM = re.compile(
    v2._LEAD_STAMP + r"((?:Alert\s+[A-Z][\w'-]+(?:\s+[A-Z][\w'-]+)?)|(?:[A-Z][\w'-]+\s+Alerts))"
    r"(?=\s*(?:[:\-\u2013\u2014|]|$))"
)
_ORDERS = _rx(
    r"\b(?:curfews?|stay[- ]at[- ]home(?:\s+orders?)?|isolation\s+orders?|"
    r"quarantine(?:\s+orders?)?|vaccin\w+|testing\s+sites?|burn\s+bans?|"
    r"burn(?:ing)?\s+restrictions|fire\s+bans?)\b"
)
#: "Traffic" alone is not a threat: "obey traffic laws", "traffic control".
_TRAFFIC = _rx(r"\btraffic\b")
_HAZARD_EXTRA = _rx(
    r"\b(?:rising\s+water|(?:water|lake|river|creek|stream)\s+(?:levels?\s+)?(?:is|are)\s+"
    r"rising|high\s+water|flood\s?gates?|spillway\s+releases?|demolition|implosion|"
    r"demo\s+(?:in\s+progress|work|operations)|LE\s+(?:activity|presence|operation|situation)|"
    r"T\.\s?S\.\s+[A-Z][a-z]+)\b"
)
_EFFECT = _rx(
    r"\b(?:closed|closures?|closing|curfews?|cancel+(?:ed|ations?)|outages?|delays?|delayed|"
    r"shut\s?downs?|suspended)\b"
)
_CAUSE = _rx(r"\b(?:due\s+to|because\s+of|caused\s+by)\b")
_EXTENT = _rx(
    r"\b(?:imminent|widespread|in\s+(?:various|several|multiple|many|numerous)\s+(?:areas|"
    r"locations|parts|places|neighborhoods|communities))\b"
)
_TO_AFFECT = _rx(r"\bto\s+(?:affect|impact|reach|threaten|hit|damage)\b")
_ON_ROADS = _rx(
    r"\b(?:flooding|flood\s?waters?|water|snow|ice|debris|mud)\s+(?:over|on|across|covering)\s+"
    r"(?:the\s+|some\s+|many\s+|several\s+|area\s+|local\s+)?(?:roads?|roadways?|streets?|"
    r"highways?|bridges?|lanes?)\b"
)
_CAUTION = _rx(
    r"^(?:caution|careful|be\s+careful|use\s+caution|extreme\s+caution|exercise\s+caution)\b"
)
_VERB3 = _rx(rf"\b(?:{v2._VERBS}|disperse|store)\b")
_NOUN_GUIDANCE3 = _rx(
    rf"(?:{v2._NOUN_GUIDANCE.pattern})|\b(?:(?:issu\w+|order\w*|calling\s+for|call\s+for)\s+"
    r"(?:\w+\s+){0,2}evacuations?|detoured)\b"
)
_NOT_NOW3 = _rx(
    r"\bnow\s+(?:open|opened|closed|lifted|over|contained|clear|safe|reopened|been|available|"
    r"back|cancel+ed|resolved|restored|expired)\b|\bimmediate\s+(?:area|vicinity)\b"
)
_IMMEDIATE_HELP = _rx(
    r"\bimmediate\s+(?:assistance|help|attention|medical|danger|threat|response|needs?|care|"
    r"emergency|risk)\b"
)
_DURATION3 = _rx(
    r"\b(?:for|over|within|in)\s+(?:the\s+)?(?:next\s+)?(?:about|approximately|around|roughly|"
    r"nearly|up\s+to|less\s+than|over)\s+(?:\d+|one|two|three|several|few)\s*"
    r"(?:-\s*\d+\s*)?(?:minutes?|mins?|hours?|hrs?|days?)\b|"
    r"\bthroughout\s+the\s+(?:night|day|morning|afternoon|evening|weekend)\b"
)
_WHILE = _rx(r"\b(?:while|as\s+long\s+as)\b")
_ROADS3 = re.compile(
    r"\b(?:IH\s?-?\d{1,3}[A-Z]?|I\s\d{1,3}(?!\s*(?:am|pm|AM|PM|a\.m|p\.m))|"
    r"(?i:mile\s+markers?))\b|"
    r"\b[A-Z][A-Za-z0-9]{1,15}\s*@\s*[A-Z][A-Za-z0-9]{1,15}\b|"
    r"\b(?i:at|near|on)\s+(?:[NSEW]\.?\s+)?(?:\d+(?:st|nd|rd|th)|[A-Z][a-z]+)\s*(?:&|@)\s*"
    r"(?:[NSEW]\.?\s+)?(?:\d+(?:st|nd|rd|th)|[A-Z][a-z]+)\b"
)
#: Words of an area description that are not place names: alert words and season words.
_NOT_PLACE_WORDS = _rx(
    r"^(?:winter|summer|spring|autumn|weather|advisory|warning|watch|alert|alerts|statement|"
    r"emergency|evacuation|notice|update|message|test|warnings|advisories|watches|special|"
    r"severe|flood|flash|storm|storms|fire|wind|heat|cold|freeze|frost|hazard|hazards)$"
)
_NOT_PLACES3 = _rx(
    r"^(?:wireless|various|several|multiple|many|some|certain|numerous|select|outlying|rural|"
    r"low|lying|alert|alerts|system|systems|emergency|cell|cellular|landline|phone|phones|"
    r"internet|radio|television|tv|test|testing)$"
)
_NAMED_PLACE3 = re.compile(
    r"\b(?i:in|near|of|around|outside|throughout|across|within|for|from|at|into|toward|towards|"
    r"avoid|leave|evacuate|enter|entering|visiting)"
    r"\s+(?:(?i:the)\s+)?(?:(?i:north|south|east|west|northern|southern|eastern|western|central|"
    r"downtown|greater|unincorporated|old)\s+)?"
    r"((?:El|La|Las|Los|Le|De|Du|St\.?|Mt\.?|Ft\.?|Pt\.?)\s+[A-Z][a-z]{2,}(?:[\s-][A-Z][a-z]{2,}){0,2})"
)


class Rules:
    """The version 3 rules, with any subset of the changes (all by default)."""

    def __init__(self, changes: Iterable[str] = ALL):
        self.ch = frozenset(changes)
        unknown = self.ch - KNOWN
        if unknown:
            raise ValueError(f"Unknown changes: {sorted(unknown)}")

    def on(self, name: str) -> bool:
        return name in self.ch

    # --- source --------------------------------------------------------------------------

    def _segment(self, name: str, start: int, keep: str) -> tuple[str, int]:
        """The part of a name on one line and in one sentence: the last part (an opener, a
        subject) or the first (after a cue such as "from")."""
        if not self.on("cut"):
            return name, start
        cuts = []
        for m in _BREAK.finditer(name):
            if m.group(0) != "\n":
                word = re.search(r"([A-Za-z.]+)$", name[: m.start()])
                w = word.group(1).lower() if word else ""
                if w in _ABBREVIATIONS or len(w) == 1 or "." in w:
                    continue
            cuts.append((m.start(), m.end()))
        if not cuts:
            return name, start
        if keep == "first":
            return name[: cuts[0][0]].rstrip(), start
        rest = name[cuts[-1][1] :]
        lead = len(rest) - len(rest.lstrip())
        return rest.strip(), start + cuts[-1][1] + lead

    def _initials(self) -> re.Pattern[str]:
        return _INITIALS3 if self.on("initials") else v2._INITIALS

    def _initials_ok(self, token: str) -> bool:
        if not v2._initials_ok(token):
            return False
        if self.on("initials"):
            low = token.lower()
            if token.upper() in _CAPS_WORDS or low in _ENGLISH_WORDS:
                return False
            if v2._VERB.fullmatch(token) or v2._NOT_A_PLACE_NAME.match(token):
                return False
        return True

    def _speaker_head(self, name: str, strict: bool = False) -> bool:
        if v2._STATE_OF.search(name):
            return False
        heads = [m.group(0).lower() for m in v2._AGENCY_HEAD.finditer(name)]
        fire_only = bool(heads) and all(h == "fire" for h in heads)
        if heads and not (self.on("bare_fire") and fire_only and _FIRE_AS_HAZARD.search(name)):
            return True
        if self.on("start_org") and _AGENCY3.search(name):
            return True
        if strict and name.isupper():
            return False
        if self.on("initials"):
            name = blank(
                name, [m.span() for rx in v2.HAZARD_WORDS.values() for m in rx.finditer(name)]
            )
        for w in re.findall(r"[A-Za-z0-9]+", name):
            if self._initials().fullmatch(w) and self._initials_ok(w):
                return True
        return False

    def _acronym_ending(self) -> re.Pattern[str]:
        return _ACRONYM_ENDING3 if self.on("stamp") else v2._ACRONYM_ENDING

    def _names_an_organization(self, name: str, opener: bool = False) -> bool:
        if self._acronym_ending().search(name):
            return True
        if self.on("message_opener") and re.search(r"\b(?:Boro|Co\.)(?=\W|$)", name):
            return True
        return v2._names_an_organization(name, opener)

    def _organization_part(self, name: str, start: int) -> tuple[int, int]:
        a, b = v2._organization_part(name, start)
        if self.on("initials"):
            # The span ends at the last organization word, never at an ordinary word in caps.
            ends = [
                m.end()
                for rx in (
                    v2._AGENCY,
                    v2._ACRONYM_KNOWN,
                    self._acronym_ending(),
                    v2._ACRONYM_BARE,
                    v2._JURISDICTION,
                    v2._AGENCY_HEAD,
                )
                for m in rx.finditer(name)
            ]
            ends += [
                m.end()
                for m in _INITIALS3.finditer(name)
                if self._initials_ok(m.group(0))
                and not v2._ALERT_WORDS.fullmatch(m.group(0))
                and not any(rx.fullmatch(m.group(0)) for rx in v2.HAZARD_WORDS.values())
            ]
            of = re.match(
                r"(?i)(?:city|town|village|county|borough|township|parish)\s+of\s+[A-Za-z][\w'-]*"
                r"(?:\s+[A-Z][\w'-]*)?",
                name,
            )
            if of:
                ends.append(of.end())
            b = start + (max(ends) if ends else len(name))
        if self.on("opener_from"):
            m = re.search(r"(?i)\s(?:from|by)\s+(?:the\s+)?", name)
            if m and m.end() < b - start:
                a = start + m.end()
        return a, b

    def _openers(self, text: str) -> list[tuple[str, int, bool]]:
        """Openers (name, start, first line?) at the start of the text and, with ``lines``, of
        each later line."""
        rx = _OPENER3 if self.on("lines") or self.on("cut") else v2._OPENER
        out = []
        m = rx.search(text)
        if m:
            out.append((m.group(1), m.start(1), True))
        if self.on("lines"):
            for line in re.finditer(r"\n([^\n]+)", text):
                m = rx.search(line.group(1))
                if m:
                    out.append((m.group(1), line.start(1) + m.start(1), False))
        return out

    def speaker_spans(self, text: str, ctx: Context) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for name, start, first in self._openers(text):
            name, start = self._segment(name, start, "last")
            if not name:
                continue
            if (
                (first and self._names_an_organization(name, opener=True))
                or (not first and self._names_an_organization(name))
                or (first and self._speaker_head(name))
            ):
                spans.append(self._organization_part(name, start))
        m = v2._SIGNATURE.search(text)
        if m and not (self.on("signature") and _SIGNATURE_WORDS.search(m.group(1))):
            name, start = self._segment(m.group(1), m.start(1), "first")
            strict = self.on("signature")
            if self._names_an_organization(name, opener=True) or self._speaker_head(name, strict):
                spans.append(self._organization_part(name, start))
        for rx in (v2._OPENER_TIGHT, v2._PREFIX_ALERT):
            m = rx.search(text)
            if m and self._initials_ok(m.group(1)):
                spans.append(m.span(1))
        m = v2._OPENER_AGENCY_TIGHT.search(text)
        if m and v2._AGENCY_HEAD.search(m.group(1)):
            spans.append(m.span(1))
        cues = [v2._SPEAKER, v2._SPEAKER_WITH] + ([_SPEAKER_BY] if self.on("by") else [])
        for rx in cues:
            for m in rx.finditer(text):
                keep = "last" if rx is v2._SPEAKER_WITH else "first"
                name, start = self._segment(m.group(1), m.start(1), keep)
                if (
                    self._names_an_organization(name)
                    or self._speaker_head(name, strict=True)
                    or re.search(r"(?i)\b(?:alerts?|notifications?|system|program)$", name)
                ):
                    spans.append(self._organization_part(name, start))
        m = v2._SUBJECT_SPEAKS.search(text)
        if not m and self.on("start_org"):
            m = _SUBJECT_VERB3.search(text)
        if m:
            subject, s_start = self._segment(m.group(1).strip(), m.start(1), "last")
            named_body = v2._AGENCY_HEAD.search(subject) or v2._JURISDICTION.search(subject)
            if subject and not (
                v2._GENERIC_SPEAKER.match(subject)
                or (v2._ALERT_WORDS.search(subject) and not named_body)
                or any(rx.search(subject) for rx in v2.HAZARD_WORDS.values())
                or v2._ROAD_WORDS.search(subject)
                or (self.on("bare_fire") and _FIRE_AS_HAZARD.search(subject))
            ):
                spans.append((s_start, s_start + len(subject)))
        mixed = sum(ch.isupper() for ch in text) < 0.6 * max(1, sum(ch.isalpha() for ch in text))
        for m in v2._SPEAKER_VERB.finditer(text):
            if self.on("verb_case") and mixed and text[m.end(1) :].lstrip()[:1].isupper():
                continue
            name, start = self._segment(m.group(1), m.start(1), "last")
            if self._names_an_organization(name) or self._speaker_head(name, strict=True):
                spans.append(self._organization_part(name, start))
        first = re.match(v2._LEAD_STAMP + r"(?:(?i:the)\s+)?([^\s:]+(?:\s+[^\s:]+){0,5})", text)
        if first:
            head = first.group(1)
            lead = re.match(r"\S+", head)
            if lead and (
                v2._ACRONYM_KNOWN.fullmatch(
                    lead.group(0).rstrip(";") if self.on("lines") else lead.group(0)
                )
                or self._acronym_ending().fullmatch(lead.group(0))
            ):
                spans.append((first.start(1), first.start(1) + lead.end()))
            elif re.match(rf"(?:{v2._AGENCY.pattern})", head, IC | VB):
                spans.append((first.start(1), first.end(1)))
        spans += self._new_speakers(text)
        if ctx.organization:
            full = re.search(re.escape(ctx.organization), text, IC)
            if full:
                spans.append(full.span())
            initials = "".join(
                w[0] for w in re.findall(r"[A-Za-z]+", ctx.organization) if w[0].isupper()
            )
            if len(initials) >= 3:
                spans += [m.span() for m in re.finditer(rf"\b{re.escape(initials)}\b", text)]
        return v2._merge(spans)

    def _new_speakers(self, text: str) -> list[tuple[int, int]]:
        """Speakers only version 3 reads: a stamped opener, a place-and-acronym organization
        that opens the text or stands alone on a line, a name and an agency word at the start,
        a message opener, and a bare place opener."""
        spans = []
        if self.on("stamp"):
            m = _STAMPED.match(text)
            if m and (
                v2._ACRONYM_KNOWN.fullmatch(m.group(1))
                or _ACRONYM_ENDING3.fullmatch(m.group(1))
                or (_INITIALS3.fullmatch(m.group(1)) and self._initials_ok(m.group(1)))
            ):
                spans.append(m.span(1))
        if self.on("place_acronym"):
            for line in re.finditer(r"[^\n]+", text):
                m = _PLACE_ACRONYM.search(line.group(0))
                body = line.group(0).strip(" .:-")
                if m and (m.start() <= 3 or m.group(1) == body):
                    spans.append((line.start() + m.start(1), line.start() + m.end(1)))
            for line in re.finditer(r"[^\n]+", text):
                body = line.group(0).strip(" .:-")
                if body and v2._AGENCY.fullmatch(body):
                    spans.append((line.start(), line.end()))
        if self.on("start_org"):
            m = _START_ORG.match(text)
            if m:
                spans.append(m.span(1))
        if self.on("message_opener"):
            m = _MESSAGE_OPENER.match(text)
            if m:
                spans.append(m.span(1))
        if self.on("alert_system"):
            m = _ALERT_SYSTEM.match(text)
            if m and self._system_name(m.group(1)):
                spans.append(m.span(1))
        if self.on("bare_place"):
            m = _BARE_PLACE.match(text)
            if m and self._bare_place(m.group(1)):
                spans.append(m.span(1))
        return spans

    def _system_name(self, name: str) -> bool:
        """An alert system's name: "Alert" and a name, or a name and "Alerts", where the name
        could be a place's (not a generic, alert or hazard word, nor a jurisdiction's)."""
        words = re.sub(r"(?i)\balerts?\b", " ", name)
        return not v2._JURISDICTION.search(name) and self._bare_place(" ".join(words.split()))

    @staticmethod
    def _bare_place(name: str) -> bool:
        for w in re.split(r"[ -]", name):
            if (
                _OPENER_WORDS.match(w)
                or v2._NOT_A_PLACE_NAME.match(w)
                or v2._ALERT_WORDS.fullmatch(w)
                or v2._EN.fullmatch(w)
                or v2._VERB.fullmatch(w)
                or v2._ROAD_WORDS.fullmatch(w)
                or v2._LANDMARK.fullmatch(w)
                or any(rx.fullmatch(w) for rx in v2.HAZARD_WORDS.values())
            ):
                return False
        return not v2._ROAD_SUFFIX_MIXED.search(name)

    def find_source(self, text: str, ctx: Context) -> list[tuple[int, int]]:
        """Every organization named, blanked before the other codes read the text."""
        spans: list[tuple[int, int]] = []
        spans += [m.span() for m in v2._AGENCY.finditer(text)]
        spans += [m.span() for m in v2._ACRONYM_KNOWN.finditer(text)]
        spans += [m.span() for m in self._acronym_ending().finditer(text) if len(m.group(0)) >= 3]
        spans += [m.span() for m in v2._NAME_THEN_BARE.finditer(text)]
        if self.on("place_acronym"):
            spans += [m.span(1) for m in _PLACE_ACRONYM.finditer(text)]
        if self.on("alert_system"):
            m = _ALERT_SYSTEM.match(text)
            if m and self._system_name(m.group(1)):
                spans.append(m.span(1))
        for name, start, _first in self._openers(text)[:1]:
            name, start = self._segment(name, start, "last")
            if name and self._names_an_organization(name, opener=True):
                spans.append(self._organization_part(name, start))
        m = v2._SIGNATURE.search(text)
        if m and not (self.on("signature") and _SIGNATURE_WORDS.search(m.group(1))):
            name, start = self._segment(m.group(1), m.start(1), "first")
            if self._names_an_organization(name, opener=True):
                spans.append(self._organization_part(name, start))
        for rx in (v2._SPEAKER, v2._SPEAKER_VERB):
            for m in rx.finditer(text):
                keep = "first" if rx is v2._SPEAKER else "last"
                name, start = self._segment(m.group(1), m.start(1), keep)
                if self._names_an_organization(name):
                    spans.append(self._organization_part(name, start))
        for m in v2._PLACE_AGENCY.finditer(text):
            if not v2._NOT_A_PLACE.match(m.group(1).split()[0]):
                spans.append(m.span())
        spans += self.speaker_spans(text, ctx)
        words = v2.organization_words(ctx.organization) + sorted(ctx.place_words)
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
            for m in re.finditer(rf"\b{re.escape(w)}\b", text, IC):
                window = text[m.start() : m.end() + 40]
                if re.match(
                    rf"{re.escape(w)}\W+(?:\w+\W+){{0,2}}?(?:{v2._AGENCY.pattern})",
                    window,
                    IC | VB,
                ) or re.match(
                    rf"{re.escape(w)}\W+(?:(?:county|city|parish|borough|town)\W+)?"
                    rf"(?:{v2._AGENCY.pattern}|oem|ema|eoc|so|pd|fd|police|sheriff|government|"
                    r"officials)\b",
                    window,
                    IC | VB,
                ):
                    spans.append((m.start(), m.end()))
        return v2._merge(spans)

    # --- hazard and its description ------------------------------------------------------

    def hazard_spans(self, rest: str) -> list[tuple[int, int]]:
        spans = [m.span() for rx in v2.HAZARD_WORDS.values() for m in rx.finditer(rest)]
        if self.on("hazard_words"):
            spans += [m.span() for m in _HAZARD_EXTRA.finditer(rest)]
        alone = []
        if self.on("traffic_alone"):
            alone += [m.span() for m in _TRAFFIC.finditer(rest)]
        if self.on("orders"):
            alone += [m.span() for m in _ORDERS.finditer(rest)]
        if alone:
            spans = [s for s in spans if not any(a <= s[0] and s[1] <= b for a, b in alone)]
        return spans

    def _caused(self, rest: str) -> bool:
        for clause in clauses(rest):
            if not _EFFECT.search(clause):
                continue
            for m in _CAUSE.finditer(clause):
                if self.hazard_spans(clause[m.end() : m.end() + 60]):
                    return True
        return False

    # --- guidance --------------------------------------------------------------------------

    def guidance_actions(self, text: str) -> list[str]:
        verb = _VERB3 if self.on("verbs") else v2._VERB
        noun = _NOUN_GUIDANCE3 if self.on("verbs") else v2._NOUN_GUIDANCE
        found: list[str] = []
        for clause in clauses(text):
            last_end = None
            for m in verb.finditer(clause):
                before = clause[: m.start()].strip().lower()
                between = (
                    clause[last_end : m.start()].strip().lower() if last_end is not None else None
                )
                listed = between is not None and between in (",", "", "and", "or", "then", ", and")
                if before and not listed and not v2._LEAD_IN.search(before):
                    continue
                last_end = m.end()
                action = " ".join(m.group(0).lower().split())
                action = re.sub(r"^don'?t\b", "do not", action)
                if action not in found:
                    found.append(action)
            if self.on("caution") and _CAUTION.search(clause) and "caution" not in found:
                found.append("caution")
        for m in v2._STRONG.finditer(text):
            if v2._AFTER_BEING.search(text[max(0, m.start() - 12) : m.start()].lower()):
                continue
            v = verb.match(m.group(0))
            action = " ".join((v.group(0) if v else m.group(0).split()[0]).lower().split())
            if action not in found:
                found.append(action)
        for clause in clauses(text):
            if v2._ENDED.search(clause):
                continue
            for m in noun.finditer(clause):
                action = " ".join(m.group(0).lower().split())
                if not any(action.startswith(a) or a.startswith(action) for a in found):
                    found.append(action)
        if v2._INFO_LINK.search(text) and "visit" not in found and "check" not in found:
            found.append("information link")
        return found

    # --- time ----------------------------------------------------------------------------

    def time_kinds(self, text: str) -> dict[str, bool]:
        out = {"time_impact": False, "time_action": False, "time_expiry": False}
        not_now = _NOT_NOW3 if self.on("now_in_effect") else v2._NOT_NOW
        probe = not_now.sub(" ", text)
        if self.on("immediate_help"):
            probe = _IMMEDIATE_HELP.sub(" ", probe)
        if v2._NOW.search(probe):
            out["time_action"] = True
        if v2._EXPIRY.search(text):
            out["time_expiry"] = True
        if v2._IMPACT.search(text):
            out["time_impact"] = True
        for clause in clauses(text):
            acts = bool(self.guidance_actions(clause))
            absolute = bool(
                v2._CLOCK.search(clause)
                or v2._DAY.search(clause)
                or v2._DATE.search(clause)
                or v2._DURATION.search(clause)
                or (self.on("about") and _DURATION3.search(clause))
            )
            if acts and v2._AT_THIS_TIME.search(clause):
                out["time_action"] = True
            if v2._UNTIL.search(clause):
                if acts and not v2._EXPIRY.search(clause):
                    out["time_action"] = True
                else:
                    out["time_expiry"] = True
            elif acts and (
                (self.on("while") and _WHILE.search(clause))
                or absolute
                or re.search(r"\bbefore\b", v2._BEFORE_USE.sub(" ", clause), IC)
            ):
                out["time_action"] = True
            elif absolute and not v2._EXPIRY.search(clause) and not v2._PAST_EVENT.search(clause):
                out["time_impact"] = True
        return out

    # --- location ------------------------------------------------------------------------

    def _not_a_place(self, w: str) -> bool:
        return bool(
            v2._NOT_A_PLACE_NAME.match(w) or (self.on("not_places") and _NOT_PLACES3.match(w))
        )

    def _caps_place(self, text: str) -> bool:
        for m in v2._CAPS_PLACE.finditer(text):
            w = m.group(1)
            if not (
                self._not_a_place(w)
                or v2._ROAD_WORDS.fullmatch(w)
                or v2._EN.fullmatch(w)
                or v2._VERB.fullmatch(w)
                or v2._ALERT_WORDS.fullmatch(w)
                or v2._LANDMARK.fullmatch(w)
                or w.upper() in v2._NOT_ACRONYMS
                or any(rx.fullmatch(w) for rx in v2.HAZARD_WORDS.values())
            ):
                return True
        return False

    def location_kinds(self, text: str, place_words: Iterable[str] = ()) -> dict[str, bool]:
        mixed = sum(ch.isupper() for ch in text) < 0.6 * max(1, sum(ch.isalpha() for ch in text))
        boundary = bool(v2._BOUNDARY.search(text) or v2._STATE_NAMES.search(text))
        if not boundary:
            boundary = any(
                not v2._JURISDICTION_GENERIC.match(m.group(1))
                for m in v2._NAMED_JURISDICTION.finditer(text)
            )
        if not boundary and mixed:
            for m in v2._NAMED_AREA.finditer(text):
                first = m.group(1).split()[0]
                if not self._not_a_place(first) and not v2._ALERT_WORDS.fullmatch(first):
                    boundary = True
                    break
        if not boundary:
            for w in place_words:
                if re.search(rf"\b{re.escape(w)}\b", text, IC):
                    boundary = True
                    break
        if not boundary and mixed:
            for m in v2._NAMED_PLACE.finditer(text):
                first = m.group(1).split()[0].split("-")[0]
                if not self._not_a_place(first) and not v2._ROAD_WORDS.fullmatch(first):
                    boundary = True
                    break
        if not boundary and mixed and self.on("particles"):
            boundary = bool(_NAMED_PLACE3.search(text))
        if not boundary and not mixed:
            boundary = self._caps_place(text)
        if not boundary and mixed and self.on("caps_clauses"):
            for clause in clauses(text):
                letters = [ch for ch in clause if ch.isalpha()]
                caps = bool(letters) and all(ch.isupper() for ch in letters)
                if len(clause.split()) >= 2 and caps and self._caps_place(clause):
                    boundary = True
                    break
        named = any(not v2._ROAD_GENERIC.match(m.group(1)) for m in v2._ROAD_NAMED.finditer(text))
        caps_named = any(
            not v2._ROAD_GENERIC.match(m.group(1)) for m in v2._ROAD_SUFFIX_CAPS.finditer(text)
        )
        suffix = [
            m
            for m in v2._ROAD_SUFFIX_MIXED.finditer(text)
            if not v2._NAMED_FIRE.match(text[m.end() :])
        ]
        road = bool(
            named
            or v2._ROAD_NUMBERED.search(text)
            or v2._ROAD_CODE.search(text)
            or (bool(suffix) if mixed else caps_named)
            or v2._BETWEEN.search(text)
            or v2._BLOCK_OF.search(text)
            or (self.on("roads") and _ROADS3.search(text))
        )
        landmark = bool(v2._LANDMARK.search(text))
        zone = bool(
            v2._ZONE.search(text)
            or (v2._ZONE_ID.search(text) and v2._ZONE_CONTEXT.search(text))
            or (v2._ZONE_LETTER.search(text) and v2._ZONE_CONTEXT.search(text))
        )
        out = {
            "loc_boundary": boundary,
            "loc_road": road,
            "loc_landmark": landmark,
            "loc_zone": zone,
        }
        out["location"] = any(out.values())
        out["loc_vague_or_none"] = not out["location"] or bool(v2._VAGUE.search(text))
        if out["location"]:
            out["loc_vague_or_none"] = False
        return out

    # --- one unit ------------------------------------------------------------------------

    def code_text(self, text: str, ctx: Context | None = None) -> dict[str, Any]:
        """Every code for one English text (the fields of version 2, in its order)."""
        ctx = ctx or Context()
        rest = blank(text, self.find_source(text, ctx))
        category, cat_source = v2.hazard_category(rest, ctx.event_codes)
        block_rest = rest
        if cat_source != "words" and ctx.block_text and ctx.block_text != text:
            block_rest = blank(ctx.block_text, self.find_source(ctx.block_text, ctx))
            block_category, block_source = v2.hazard_category(block_rest, ctx.event_codes)
            if block_source == "words":
                category, cat_source = block_category, "message_words"
        if cat_source not in ("words", "message_words"):
            for cue_category, rx in v2.CATEGORY_CUES.items():
                if rx.search(block_rest):
                    category, cat_source = cue_category, "cue_words"
                    break
        hazard_spans = self.hazard_spans(rest)
        named_hazard = bool(hazard_spans)
        distinct = {rest[a:b].lower() for a, b in hazard_spans}
        described = rest if len(distinct) > 1 else blank(rest, hazard_spans)
        chars = named_hazard and bool(
            v2._CHARACTERISTICS.search(described)
            or (self.on("extent") and _EXTENT.search(described))
        )
        impacts = named_hazard and bool(
            v2._IMPACTS.search(described)
            or (self.on("caused") and self._caused(rest))
            or (self.on("extent") and _TO_AFFECT.search(described))
            or (self.on("on_roads") and _ON_ROADS.search(rest))
        )
        actions = self.guidance_actions(rest)
        protective = [a for a in actions if not v2._INFO_VERBS.match(a)]
        info = [a for a in actions if v2._INFO_VERBS.match(a)]
        times = self.time_kinds(rest)
        words = ctx.place_words | v2.place_words_of([ctx.organization])
        if self.on("place_words"):
            words = frozenset(w for w in words if not _NOT_PLACE_WORDS.match(w))
        places = self.location_kinds(rest, words)
        links = v2.link_kinds(text)
        n_abbr = v2.abbreviations(text)
        letters = [ch for ch in text if ch.isalpha()]
        caps = sum(ch.isupper() for ch in letters) / len(letters) if letters else 0.0
        out: dict[str, Any] = {
            "hazard": named_hazard,
            "hazard_category": category,
            "hazard_category_source": cat_source,
            "hazard_description": chars or impacts,
            "hazard_characteristics": chars,
            "hazard_impacts": impacts,
            "source_named": bool(self.speaker_spans(text, ctx)),
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
            **v2.evacuation_terms(rest),
            "about_missing_person": bool(v2._MISSING_PERSON.search(text)),
            "about_test": bool(v2._ABOUT_TEST.search(text)),
        }
        out["complete"] = all(
            out[k] for k in ("hazard", "location", "time", "source_named", "guidance")
        )
        return {k: out[k] for k in v2.CODE_FIELDS}

    def code_unit(
        self, unit: str, text: str | None, ctx: Context | None = None, spanish: bool = False
    ) -> UnitCodes:
        """Code one unit, or say why not (``empty``, ``spanish_block``, ``spanish_text``,
        ``other_language``)."""
        text = text or ""
        if not text.strip():
            return UnitCodes(unit, len(text), False, "empty")
        if spanish:
            return UnitCodes(unit, len(text), False, "spanish_block")
        reason = (
            language(text)
            if self.on("lang")
            else ("spanish_text" if v2.looks_spanish(text) else None)
        )
        if reason:
            return UnitCodes(unit, len(text), False, reason)
        return UnitCodes(unit, len(text), True, None, self.code_text(text, ctx))


_ALL_RULES = Rules()


def code_text(text: str, ctx: Context | None = None) -> dict[str, Any]:
    return _ALL_RULES.code_text(text, ctx)


def code_unit(unit: str, text: str | None, ctx: Context | None = None, spanish: bool = False):
    return _ALL_RULES.code_unit(unit, text, ctx, spanish)
