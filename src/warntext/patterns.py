"""Find personal details in alert text by pattern. Names and counts only: no match is returned.

Some alerts are about people (missing children and adults, wanted suspects) and carry phone
numbers, car plates, ages and descriptions. These patterns decide which texts are withheld
(:mod:`warntext.privacy`) and check that no released text holds such a detail
(:mod:`warntext.check`, :mod:`warntext.release`). They are this project's one definition of a
personal detail: the build, the weekly update, both checks and the scan before going public all
read this module. They are deliberately broad and over-count rather than under-count. They never
identify anyone and never record or infer an attribute of a person: a description is looked for
only so that its text can be withheld, and only the name of the pattern that fired is kept.

Two kinds:

- **Detail patterns** (:data:`PATTERNS`): any one of them in a text withholds it. The first seven
  are the patterns of the first release, unchanged. The others were added so that the written
  form of a detail does not matter: a phone number in any form (``phone_any_form``,
  ``phone_seven``, ``phone_letters``, ``phone_international``), an email address in any form
  (``email_any_form``), an age or a height or weight in other forms (``age_any_form``,
  ``height_weight_any_form``). Each added pattern skips the places where the first ones already
  match, so its name marks what it adds.
- **A person described** (:data:`DESCRIBED`): a text that gives two or more of the elements of a
  description (:data:`DESCRIPTION_ELEMENTS`), with or without the cue words the detail patterns
  know. It is judged over all the text fields of a message together.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_I = re.IGNORECASE

# --- the first release's patterns, unchanged ---------------------------------------------

#: North American numbers: 555-0123, (555) 555-0123, 555.555.0123, 1-800-555-0123.
_PHONE = r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\d)"
_EMAIL = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
_AGE = (
    r"\b\d{1,3}\s*-?\s*(?:years?|yrs?)\s*-?\s*old\b|\b\d{1,3}\s*(?:yrs?|y/o|yoa)\b"
    r"|\bage[ds]?\s*:?\s*\d{1,3}\b"
)
_HEIGHT = r"\b\d\s*'\s*\d{1,2}\b|\b\d\s*(?:ft|feet|foot)\b"
_WEIGHT = r"\b\d{2,3}\s*(?:lbs?|pounds)\b"
_PLATE = (
    r"\b(?:license\s+plate|lic(?:ense)?\.?\s*(?:plate|tag)?|plates?|tags?)\b"
    r"\s*(?:#|no\.?|number|num\.?)?\s*:?\s*(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{1,8}\b"
)

# --- pieces of the added patterns ----------------------------------------------------------

#: One separator in a written number: spaces and line ends, dots, hyphens and other dashes,
#: the minus sign, slashes and underscores.
_S = r"[\s.\-\u2010-\u2015\u2212/_]"
#: Dashes of any kind, and a dot, as between the parts of a seven-digit number.
_D = r"[.\-\u2010-\u2015\u2212]"
#: North American shape: an area code and an exchange that start with 2 to 9.
_NANP = r"[2-9]\d\d"
_TOLL_FREE = r"8(?:00|88|77|66|55|44|33)"
_NUMBER_WORD = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
    r"eighty|ninety)(?:[\s-](?:one|two|three|four|five|six|seven|eight|nine))?"
)
_COLOR = (
    r"(?:black|white|red|blue|green|gr[ae]y|brown|tan|pink|purple|yellow|orange|maroon|navy|"
    r"beige|khaki|camo(?:uflage)?|dark|light|silver|gold)"
)
_GARMENT = (
    r"(?:shirt|t-shirt|tee|hoodie|hooded|sweatshirt|sweater|jacket|coat|jeans|pants|shorts|"
    r"sweatpants|leggings|shoes|sneakers|boots|sandals|hat|cap|beanie|dress|skirt|vest|"
    r"pajamas|uniform|top|blouse|backpack)s?"
)
_PERSON = r"(?:male|female|man|woman|boy|girl|juvenile|teen(?:ager)?|child|subject|suspect)"
_ORIGIN = (
    r"(?:white|black|hispanic|latino|latina|asian|caucasian|african[\s-]american|"
    r"native[\s-]american|biracial|indian)"
)
_MAKE = (
    r"(?:honda|toyota|ford|chevy|chevrolet|nissan|dodge|jeep|gmc|kia|hyundai|bmw|mercedes|"
    r"audi|volkswagen|vw|subaru|mazda|lexus|acura|buick|cadillac|chrysler|lincoln|infiniti|"
    r"mitsubishi|tesla|ram|pontiac|saturn|volvo)"
)
_VEHICLE = r"(?:car|sedan|suv|truck|pickup|van|minivan|coupe|motorcycle|vehicle|hatchback)"
#: A personal name as written in mixed case: two capitalized words, a middle initial allowed.
_NAME = r"(?-i:[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)"

#: Ten digits in any other written form: any separators (several, a line end, other dashes, a
#: slash) between the three parts; the area code in brackets with any separator or none; or one
#: or no separator in North American shape; with +1 or 1 before it or not. Not a run of digits
#: inside a word or a link's file name (after a letter, an underscore, a dash, a slash or "=",
#: or before a letter).
_PHONE_ANY = (
    rf"(?<![\w.\-/=])(?!{_PHONE})(?:\+?1{_S}{{0,3}})?"
    rf"(?:(?:\(\s*\d{{3}}\s*\){_S}{{0,3}}|\d{{3}}{_S}{{1,3}})\d{{3}}{_S}{{1,3}}\d{{4}}"
    rf"|\(\s*\d{{3}}\s*\){_S}{{0,3}}\d{{3}}{_S}{{0,3}}\d{{4}}"
    rf"|{_NANP}{_S}?{_NANP}{_S}?\d{{4}})(?![\w])"
)
#: Seven digits with a dot or a dash (a local number without its area code), or with a space
#: after a word that asks to call; not a span of clock times ("830-1130 am").
_NOT_AFTER = r"(?![\w\-\u2010-\u2015\u2212]|\.\d|\s*(?:a\.?m\b|p\.?m\b|hours?\b|hrs?\b))"
_PHONE_SEVEN = (
    rf"(?<![\w.,:/\-\u2010-\u2015\u2212]){_NANP}{_D}\d{{4}}{_NOT_AFTER}"
    r"|\b(?:call|dial|phone|tel|telephone|text|contact|number|line|hotline|fax)\b[:#.\s]{1,3}"
    rf"[2-9]\d\d\s\d{{4}}{_NOT_AFTER}"
)
#: Letters for digits: a toll-free area code then letters (1-800-INVENTED), or a number in
#: three parts joined by dashes or dots with letters in the last parts (555-HELP-NOW).
_PHONE_LETTERS = (
    rf"(?<![\w.])(?:\+?1{_D}?)?(?:\(\s*{_TOLL_FREE}\s*\)|{_TOLL_FREE}){_D}"
    rf"(?=[A-Za-z0-9.\-]*[A-Za-z])[A-Za-z0-9]{{3,4}}{_D}?[A-Za-z0-9]{{3,6}}\b"
    rf"|(?<![\w.])(?:1{_D})?(?![2-9]11\b){_NANP}{_D}(?=[A-Z0-9.\-]*[A-Z])[A-Z0-9]{{3,4}}{_D}"
    r"[A-Z0-9]{4,5}\b"
)
#: A number with a plus and another country code, eight digits or more.
_PHONE_INTERNATIONAL = (
    r"(?<![\w.])\+(?=(?:[\s.\-()]?\d){8})[2-9]\d{0,2}(?:[\s.\-]?\(?\d{1,4}\)?){2,5}(?!\d)"
)
_DOMAIN_END = r"(?:com|gov|org|net|edu|us|mil|info|biz|co)"
#: Email addresses in other forms: [at] or (at) with dots or [dot]; "email" then the word "at"
#: with the word "dot" (without "email" it is a web address read aloud). Not taken: spaces
#: around an @, or an @ with no domain ending, which alerts use for "at" ("info @ a web
#: address", "9am@a hall").
_EMAIL_ANY = (
    r"[\w.+-]+\s*(?:\[at\]|\(at\)|\{at\}|<at>)\s*[\w-]+"
    r"(?:\s*(?:\.|\[dot\]|\(dot\)|\bdot\b)\s*[\w-]+)+"
    rf"|\be-?mail\b[^.\n]{{0,30}}?\b[\w.+-]+\s+at\s+[\w-]+(?:\s+dot\s+[\w-]+)*\s+dot\s+"
    rf"{_DOMAIN_END}\b"
)
#: Ages in other forms: in words, "yo" and "y.o.", "years of age", months or weeks old, in his
#: or her twenties, a date of birth. Not an age limit ("21 years of age or older").
_AGE_ANY = (
    rf"\b{_NUMBER_WORD}[\s-]*(?:years?|yrs?|months?|weeks?)[\s-]*old\b"
    rf"|\bage[ds]?\s*:?\s*{_NUMBER_WORD}\b"
    r"|\b\d{1,3}\s*(?:yo|y\.\s?o\.?)(?![a-z])"
    rf"|\b(?:\d{{1,3}}|{_NUMBER_WORD})\s+years?\s+of\s+age\b"
    r"(?!\s*(?:or|and|&|&amp;|\+)\s*(?:older|over|above|up|younger|under|below))"
    r"|\b\d{1,2}[\s-]*(?:months?|mos?\.?|weeks?)[\s-]*old\b"
    r"|\bin\s+(?:his|her)\s+(?:early\s+|mid[\s-]+|late\s+)?(?:\d0'?s|twenties|thirties|"
    r"forties|fifties|sixties|seventies|eighties|teens)\b"
    r"|\b(?:d\.\s?o\.\s?b\.?|dob|date\s+of\s+birth|birth\s*date)\b"
    r"|\bborn\s+(?:on\s+)?(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+"
    r"\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|in\s+(?:19|20)\d\d)\b"
)
#: Heights and weights in other forms: 5-foot-10, 5ft10, curly quotes or primes, "inches
#: tall", in words with "tall", "weighs 150", 150-pound.
_HEIGHT_ANY = (
    r"\b\d\s*[-\u2010-\u2015]\s*(?:foot|feet|ft)\s*[-\u2010-\u2015]?\s*\d{1,2}\b"
    r"|\b\d\s*(?:\u2019|\u2032|`|\u00b4)\s*\d{1,2}\b"
    r"|\b\d\s*(?:ft|feet|foot)\.?\s*\d{1,2}\b"
    r"|\b\d{2}\s*inches\s+tall\b"
    rf"|\b{_NUMBER_WORD}\s+(?:feet|foot)\s+(?:tall|{_NUMBER_WORD}\b|\d)"
)
_WEIGHT_ANY = (
    r"\bweigh(?:s|ing|ed)?\s+(?:about\s+|approximately\s+|approx\.?\s+|around\s+|roughly\s+)?"
    r"\d{2,3}\b|\b\d{2,3}\s*[-\u2010-\u2015]\s*(?:pounds?|lbs?)\b|\b\d{2,3}\s*lbs?\."
    r"|\bweight\s*:?\s*\d{2,3}\b"
)

PATTERNS: dict[str, re.Pattern[str]] = {
    # The first release's seven, unchanged.
    "phone": re.compile(_PHONE),
    "plate": re.compile(_PLATE, _I),
    "age": re.compile(_AGE, _I),
    # Height or weight given as numbers: 5'7", 5 ft 7 in, 150 lbs, 150 pounds.
    "height_weight": re.compile(rf"{_HEIGHT}|{_WEIGHT}", _I),
    "email": re.compile(_EMAIL),
    # The phrase missing-person messages use for a last known place or time.
    "last_seen": re.compile(r"\blast\s+(?:seen|known|heard)\b", _I),
    # Words of messages about a person: missing, abducted, wanted, a suspect, a description,
    # clothing, and the named alert programs. They mark a message about someone even when it
    # gives no number; they also fire on some hazard messages ("suspect package"), by design.
    "person_words": re.compile(
        r"\b(?:missing|abduct\w*|kidnap\w*|endangered\s+(?:person|adult|child|juvenile)|"
        r"runaway|wanted\s+(?:for|by|in)|suspects?\b|described\s+as|wearing|"
        r"(?:amber|silver|blue|ashanti|feather|endangered\s+missing)\s+alert|"
        r"have\s+you\s+seen)",
        _I,
    ),
    # Added: a phone number or an email address in any written form; ages, heights and weights
    # in other forms. Each skips what the first seven already match where it can.
    "phone_any_form": re.compile(_PHONE_ANY),
    "phone_seven": re.compile(_PHONE_SEVEN, _I),
    "phone_letters": re.compile(_PHONE_LETTERS),
    "phone_international": re.compile(_PHONE_INTERNATIONAL),
    "email_any_form": re.compile(_EMAIL_ANY, _I),
    "age_any_form": re.compile(_AGE_ANY, _I),
    "height_weight_any_form": re.compile(rf"{_HEIGHT_ANY}|{_WEIGHT_ANY}", _I),
}
#: The patterns of the first release, which the added ones widen.
FIRST_RELEASE = ("phone", "plate", "age", "height_weight", "email", "last_seen", "person_words")
#: The patterns that find a phone number or an email address.
CONTACT = (
    "phone",
    "phone_any_form",
    "phone_seven",
    "phone_letters",
    "phone_international",
    "email",
    "email_any_form",
)

#: The name a message gets when its text describes a person.
DESCRIBED = "person_described"
#: The elements of a description of a person; two or more distinct ones describe someone.
DESCRIPTION_ELEMENTS: dict[str, re.Pattern[str]] = {
    "age": re.compile(rf"{_AGE}|{_AGE_ANY}", _I),
    "person": re.compile(
        rf"\b{_ORIGIN}\s+(?:non-hispanic\s+)?{_PERSON}\b|\b(?-i:[WBHA]/[MF])\b"
        rf"|\b{_PERSON}\b[^.\n]{{0,40}}\b(?:build|complexion|skin(?:ned)?|tattoos?|scars?|beard|"
        r"mustache|moustache|goatee|glasses|dreadlocks|braids|piercings?)\b"
        r"|\b(?:thin|slim|skinny|heavy|heavyset|stocky|medium|average|large|small|muscular)\s+"
        r"build\b",
        _I,
    ),
    "clothing": re.compile(
        rf"\bwearing\b|\b{_COLOR}(?:\s+(?:and|&|/)\s+{_COLOR})?\s+(?:\w+\s+)?{_GARMENT}\b", _I
    ),
    "height": re.compile(rf"{_HEIGHT}|{_HEIGHT_ANY}", _I),
    "weight": re.compile(rf"{_WEIGHT}|{_WEIGHT_ANY}", _I),
    "hair_eyes": re.compile(
        r"\b(?:blonde?|brown|black|red|auburn|gr[ae]y|white|dark|light|sandy|strawberry|curly|"
        r"straight|long|short|braided|bald)\s+hair\b|\bhair\s*:|\b(?:blue|brown|green|hazel|"
        r"gr[ae]y|black)\s+eyes\b|\beyes\s*:",
        _I,
    ),
    "name": re.compile(
        rf"\b(?:missing|last\s+seen|wanted|whereabouts|locate|looking\s+for|searching\s+for|"
        rf"search\s+for|seeking|have\s+you\s+seen|sought|identify)\b[^.\n]{{0,30}}\b{_NAME}\b"
        rf"|\b{_NAME}\b[^.\n]{{0,20}}\b(?:is\s+missing|was\s+last\s+seen|is\s+wanted|"
        r"has\s+been\s+missing)\b",
        _I,
    ),
    "medical": re.compile(
        r"\b(?:dementia|alzheimer\w*|autis\w*|non-?verbal|diabet\w*|medication|medical\s+"
        r"condition|mental(?:ly)?\s+(?:ill|health|disab\w*)|special\s+needs|cognitive\w*|"
        r"disabilit\w*|epilep\w*|schizophren\w*|bipolar|suicid\w*|memory\s+loss|seizures?)\b",
        _I,
    ),
    "vehicle": re.compile(
        rf"\b(?:driving|drives|drove|last\s+seen\s+in|fled\s+in|traveling\s+in|travelling\s+in|"
        rf"left\s+in|occupants?\s+of)\s+(?:an?\s+|the\s+)?(?:(?:19|20)\d\d\s+)?(?:{_COLOR}\s+)?"
        rf"(?:\w+\s+)?(?:{_MAKE}|{_VEHICLE})\b"
        rf"|\bin\s+an?\s+(?:(?:19|20)\d\d\s+|{_COLOR}\s+)(?:\w+\s+)?(?:{_MAKE}|{_VEHICLE})\b"
        rf"|\bin\s+an?\s+{_MAKE}\b|{_PLATE}",
        _I,
    ),
}


def description_elements(texts: Iterable[str | None]) -> set[str]:
    """Which elements of a description of a person the texts give (names only)."""
    found: set[str] = set()
    for t in texts:
        if not t:
            continue
        for name, p in DESCRIPTION_ELEMENTS.items():
            if name not in found and p.search(t):
                found.add(name)
    return found


def describes_person(texts: Iterable[str | None]) -> bool:
    """Whether the texts, read together, give two or more elements of a description."""
    return len(description_elements(texts)) >= 2


def count(text: str | None) -> dict[str, int]:
    """How many times each detail pattern occurs in ``text``, and whether it describes a person
    (``person_described``: 1 or 0)."""
    if not text:
        return dict.fromkeys([*PATTERNS, DESCRIBED], 0)
    out = {name: len(p.findall(text)) for name, p in PATTERNS.items()}
    out[DESCRIBED] = int(describes_person([text]))
    return out


def present(text: str | None) -> dict[str, bool]:
    """Whether each detail pattern occurs at least once in ``text``, and whether it describes a
    person."""
    return {name: n > 0 for name, n in count(text).items()}


def hits(texts: Iterable[str | None]) -> list[str]:
    """The names of the patterns found in any of the texts, ``person_described`` included when
    the texts together describe a person. Sorted; never the matched text."""
    texts = [t for t in texts if t]
    found = {name for t in texts for name, p in PATTERNS.items() if p.search(t)}
    if describes_person(texts):
        found.add(DESCRIBED)
    return sorted(found)


def has_contact(text: str | None) -> bool:
    """Whether ``text`` holds a phone number or an email address in any form."""
    return bool(text) and any(PATTERNS[name].search(text) for name in CONTACT)
