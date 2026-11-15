"""Who sent a message, at the level of the organization, by rule.

Every message is classified as sent by a ``federal``, ``state``, ``local``, ``tribal`` or
``territorial`` authority, by ``other`` bodies (universities, companies, hospitals, utilities)
or by an ``unknown`` one. The rule reads, in this order:

1. the sender's organization name (``senderName`` in the language blocks), by keyword;
2. the internet domain of the ``sender`` value, when it has one (``.mil``, known federal
   domains, state domains such as ``ca.gov`` or ``state.tx.us``, local forms such as
   ``co.<name>.<st>.us``, tribal ``-nsn.gov`` domains, territorial domains);
3. a weaker reading of the name: an emergency agency's words without a state's name are read
   as local.

A message's own evidence is then pooled by FEMA's identifier for the alerting authority (the
Collaborative Operating Group, ``cogId``): each authority takes the kind most of its messages
point to, and every message of that authority carries it. Federal needs at least half of all
the authority's messages. An authority that nothing above places takes the kind its footprint
suggests (one county: local; whole-state codes: state), which is the least sure step and never
gives federal. ``unknown`` stays unknown and is treated as not federal everywhere, so a message
is only ever counted as federal on positive evidence.

The raw ``sender`` value is used here and in duplicate and reference matching only. It never
enters a release table; :func:`address_shape` describes it by pattern without returning it.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

KINDS = ("federal", "state", "local", "tribal", "territorial", "other", "unknown")

STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}
TERRITORIES = {
    "PR": "Puerto Rico",
    "GU": "Guam",
    "VI": "Virgin Islands",
    "AS": "American Samoa",
    "MP": "Northern Mariana Islands",
}

# --- names -------------------------------------------------------------------------------

_LOCAL_WORDS = re.compile(
    r"\b(count(y|ies)|parish|borough|city|cities|town|township|twp|village|municipal(ity)?|"
    r"municipio|sheriff'?s?|police department|police dept|fire department|fire district|"
    r"fire rescue|fire protection|communications district|911|e911|dispatch|consolidated|"
    r"metro(politan)?|regional|water district|utility district|school district|airport|"
    r"port of|harbor|levee|flood control district|public works|ems)\b",
    re.IGNORECASE,
)
_TRIBAL_WORDS = re.compile(
    r"\b(tribes?|tribal|nation|band of|rancheria|indian community|indians|pueblo of|"
    r"first nations?|native village|reservation)\b",
    re.IGNORECASE,
)
_FEDERAL_WORDS = re.compile(
    r"\b(national weather service|noaa|fema|federal|u\.?\s?s\.? army|us army|army corps|"
    r"corps of engineers|usace|u\.?\s?s\.? geological|usgs|national park|national forest|"
    r"forest service|air force|air base|naval|navy|marine corps|coast guard|joint base|"
    r"department of energy|national laboratory|bureau of reclamation|"
    r"bureau of land management|bureau of indian affairs|tennessee valley authority|"
    r"department of homeland security|veterans affairs|u\.?\s?s\.? department)\b",
    re.IGNORECASE,
)
_OTHER_WORDS = re.compile(
    r"\b(universit(y|ies)|college|campus|inc|llc|corp(oration)?|company|hospital|"
    r"medical center|health system|electric|power|energy center|generating station|"
    r"nuclear plant|railroad|railway)\b",
    re.IGNORECASE,
)
_STATE_WORDS = re.compile(
    r"\b(state of|commonwealth of|state police|highway patrol|state patrol|"
    r"department of public safety|bureau of investigation|governor'?s? office|"
    r"office of emergency services|emergency management agency|"
    r"division of emergency management|department of emergency management|"
    r"emergency management division|homeland security and emergency management)\b",
    re.IGNORECASE,
)
_STATE_NAME = re.compile(
    r"^\s*(the\s+)?(" + "|".join(sorted(STATES.values(), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_TERRITORY_NAME = re.compile(
    r"\b(" + "|".join(TERRITORIES.values()) + r"|usvi|cnmi)\b",
    re.IGNORECASE,
)
_NOT_FEDERAL_NATIONAL = re.compile(r"\bnational guard\b", re.IGNORECASE)
#: Cities whose names start with a state's name.
_CITY_LIKE_STATE = re.compile(r"^\s*(virginia beach|indiana borough)\b", re.IGNORECASE)


def kind_from_name(name: str | None) -> str | None:
    """The kind an organization name points to, or None when no rule fits.

    Local words win over state names ("Texas County"), and tribal words over everything but
    local words ("Pueblo County" is a county, "Pueblo of Acoma" a tribe). "National Guard"
    units are state forces, so they do not count as federal.
    """
    if not name or not name.strip():
        return None
    text = name.strip()
    if _CITY_LIKE_STATE.search(text):
        return "local"
    if _TERRITORY_NAME.search(text) and not _FEDERAL_WORDS.search(text):
        return "local" if _LOCAL_WORDS.search(text) else "territorial"
    if _LOCAL_WORDS.search(text):
        return "local"
    if _TRIBAL_WORDS.search(text):
        return "tribal"
    if _FEDERAL_WORDS.search(text) and not _NOT_FEDERAL_NATIONAL.search(text):
        return "federal"
    if _OTHER_WORDS.search(text):
        return "other"
    if _STATE_WORDS.search(text) or _STATE_NAME.search(text):
        return "state"
    return None


# --- domains -----------------------------------------------------------------------------

#: Federal domains seen among IPAWS senders or likely to be (matched as a suffix).
FEDERAL_DOMAINS = frozenset(
    {
        "noaa.gov",
        "weather.gov",
        "fema.gov",
        "fema.dhs.gov",
        "dhs.gov",
        "usgs.gov",
        "doi.gov",
        "nps.gov",
        "fws.gov",
        "blm.gov",
        "usbr.gov",
        "bia.gov",
        "usda.gov",
        "fs.fed.us",
        "energy.gov",
        "doe.gov",
        "nnsa.doe.gov",
        "epa.gov",
        "nasa.gov",
        "nrc.gov",
        "va.gov",
        "hhs.gov",
        "cdc.gov",
        "ihs.gov",
        "fbi.gov",
        "usdoj.gov",
        "dot.gov",
        "faa.gov",
        "tva.gov",
        "usps.gov",
        "uscg.mil",
        "ornl.gov",
        "lanl.gov",
        "llnl.gov",
        "sandia.gov",
        "inl.gov",
        "pnnl.gov",
        "anl.gov",
        "bnl.gov",
        "srs.gov",
        "hanford.gov",
        "nv.doe.gov",
    }
)
_STATE_DOMAINS = {
    "alabama.gov",
    "alaska.gov",
    "az.gov",
    "arkansas.gov",
    "ca.gov",
    "colorado.gov",
    "ct.gov",
    "delaware.gov",
    "de.gov",
    "dc.gov",
    "myflorida.com",
    "fl.gov",
    "florida.gov",
    "ga.gov",
    "georgia.gov",
    "hawaii.gov",
    "idaho.gov",
    "illinois.gov",
    "in.gov",
    "iowa.gov",
    "ks.gov",
    "kansas.gov",
    "ky.gov",
    "la.gov",
    "maine.gov",
    "maryland.gov",
    "md.gov",
    "mass.gov",
    "michigan.gov",
    "mn.gov",
    "state.mn.us",
    "ms.gov",
    "mo.gov",
    "mt.gov",
    "nebraska.gov",
    "nv.gov",
    "nh.gov",
    "nj.gov",
    "nm.gov",
    "ny.gov",
    "nc.gov",
    "ncdps.gov",
    "nd.gov",
    "ohio.gov",
    "ok.gov",
    "oklahoma.gov",
    "oregon.gov",
    "pa.gov",
    "ri.gov",
    "sc.gov",
    "sd.gov",
    "tn.gov",
    "texas.gov",
    "utah.gov",
    "vermont.gov",
    "virginia.gov",
    "wa.gov",
    "wv.gov",
    "wisconsin.gov",
    "wi.gov",
    "wyo.gov",
    "wyoming.gov",
}
_TERRITORY_DOMAINS = {"pr.gov", "guam.gov", "vi.gov", "as.gov", "gov.mp", "cnmi.gov", "gov.gu"}
_TERRITORY_TLDS = {"pr", "gu", "vi", "as", "mp"}
_STATE_CODES = {c.lower() for c in STATES}
_LOCAL_US = re.compile(
    r"(^|\.)(co|ci|city|town|twp|vil|village|county|cnty)\.[a-z0-9-]+\.[a-z]{2}\.us$"
)
_STATE_US = re.compile(r"(^|\.)state\.([a-z]{2})\.us$")


#: Generic top-level domains seen among senders, or likely; any two letters is a country's.
_GENERIC_TLDS = frozenset(
    {"gov", "com", "org", "net", "edu", "mil", "info", "biz", "int", "pro", "app", "cloud"}
    | {"online", "site", "tech", "email", "alert", "alerts", "io", "systems", "services"}
)


def domain_of(sender: str | None) -> str | None:
    """The lower-case internet domain of a sender value, or None when it has none."""
    if not sender:
        return None
    value = sender.strip().lower()
    host = value.rsplit("@", 1)[1] if "@" in value else value
    host = host.strip(".")
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", host):
        return None
    if re.fullmatch(r"[0-9.]+", host):
        return None  # an IP address names a machine, not an organization
    tld = host.rsplit(".", 1)[1]
    if not (tld in _GENERIC_TLDS or re.fullmatch(r"[a-z]{2}", tld)):
        return None  # no known top-level domain: a dotted user name, not a host
    return host


def _suffix(domain: str, names: Iterable[str]) -> bool:
    return any(domain == n or domain.endswith("." + n) for n in names)


def kind_from_domain(domain: str | None) -> str | None:
    """The kind an internet domain points to, or None (vendors, mail services, unknown)."""
    if not domain:
        return None
    if domain.endswith(".mil") or _suffix(domain, FEDERAL_DOMAINS):
        return "federal"
    if domain.endswith("-nsn.gov") or domain.endswith(".nsn.us"):
        return "tribal"
    tld = domain.rsplit(".", 1)[-1]
    if _suffix(domain, _TERRITORY_DOMAINS) or tld in _TERRITORY_TLDS:
        return "territorial"
    if _LOCAL_US.search(domain):
        return "local"
    if _STATE_US.search(domain) or _suffix(domain, _STATE_DOMAINS):
        return "state"
    if tld == "us":
        parts = domain.split(".")
        # <name>.<st>.us is a locality (cities, counties, schools); <st>.us is a state.
        if len(parts) == 2 and parts[0] in _STATE_CODES:
            return "state"
        if len(parts) >= 3 and parts[-2] in _STATE_CODES:
            return "other" if "k12" in parts else "local"
    if tld == "gov":
        # A .gov domain that is not federal, state, tribal or territorial is almost always a
        # county or a city ("<name>county.gov", "cityof<name>.gov", "<name><st>.gov").
        return "local"
    if tld == "edu":
        return "other"
    return None


# --- the pooled rule ---------------------------------------------------------------------

_AGENCY_WORDS = re.compile(
    r"\b(emergency management|emergency services|homeland security|emergency operations|"
    r"office of emergency|oem|ema|eoc|public safety|emergency communications|"
    r"emergency preparedness)\b",
    re.IGNORECASE,
)


def weak_kind_from_name(name: str | None) -> str | None:
    """A weaker reading of a name the main rule cannot place: ``local`` for an emergency
    agency's words without a state's or territory's name ("Sampleton Emergency Management"),
    since state agencies nearly always carry their state's name. Never federal."""
    if not name or kind_from_name(name) is not None:
        return None
    if _AGENCY_WORDS.search(name) and not _TERRITORY_NAME.search(name):
        return "local"
    return None


@dataclass(frozen=True)
class Evidence:
    """What one message says about its sender's kind, and from where.

    ``area`` describes the message's footprint (``one_county``, ``whole_state``, ``several``)
    and is used only for an authority that no name or domain places.
    """

    by_name: str | None
    by_domain: str | None
    by_weak_name: str | None = None
    area: str | None = None

    @property
    def kind(self) -> str | None:
        return self.by_name or self.by_domain or self.by_weak_name

    @property
    def source(self) -> str:
        if self.by_name:
            return "name"
        if self.by_domain:
            return "domain"
        if self.by_weak_name:
            return "name_weak"
        return "none"


def evidence(
    sender: str | None, sender_names: Iterable[str | None], area: str | None = None
) -> Evidence:
    names = [n for n in sender_names if n and n.strip()]
    by_name = next((k for k in map(kind_from_name, names) if k), None)
    weak = next((k for k in map(weak_kind_from_name, names) if k), None)
    return Evidence(
        by_name=by_name,
        by_domain=kind_from_domain(domain_of(sender)),
        by_weak_name=weak,
        area=area,
    )


def footprint(n_counties: int, whole_state: bool) -> str | None:
    """A message's footprint from its SAME codes, for :class:`Evidence`."""
    if whole_state:
        return "whole_state"
    if n_counties == 1:
        return "one_county"
    if n_counties > 1:
        return "several"
    return None


@dataclass(frozen=True)
class Authority:
    """The kind given to one alerting authority, with how much of its evidence agrees."""

    kind: str
    messages: int
    agreeing: int
    source: str


def _by_area(members: list[tuple[str, Evidence]]) -> str | None:
    areas = Counter(ev.area for _, ev in members if ev.area)
    total = sum(areas.values())
    if not total:
        return None
    if areas["one_county"] / total >= 0.9:
        return "local"
    if areas["whole_state"] / total >= 0.5:
        return "state"
    return None


def pool(items: Iterable[tuple[int | None, str, Evidence]]) -> dict[str, Authority]:
    """Give each authority one kind from its messages' evidence.

    ``items`` holds ``(cog_id, message_id, evidence)``. Messages without a ``cogId`` are pooled
    by themselves. The kind most messages point to wins; a tie gives ``unknown``. Federal needs
    more: at least half of all the authority's messages must point to it, or the authority is
    ``unknown``, because federal text is the part of the corpus that can be released. An
    authority that no name or domain places takes the kind its footprint suggests (``local``
    when nine in ten of its messages cover one county, ``state`` when half cover a whole
    state), and otherwise stays ``unknown``. Returns the authority for each message id.
    """
    groups: dict[str, list[tuple[str, Evidence]]] = defaultdict(list)
    for cog, mid, ev in items:
        groups[f"cog:{cog}" if cog is not None else f"msg:{mid}"].append((mid, ev))
    out: dict[str, Authority] = {}
    for members in groups.values():
        votes = Counter(ev.kind for _, ev in members if ev.kind)
        sources = Counter(ev.source for _, ev in members if ev.kind)
        ranked = votes.most_common(2)
        if not ranked:
            area = _by_area(members)
            kind, agreeing, source = (area, 0, "area") if area else ("unknown", 0, "none")
        elif len(ranked) == 2 and ranked[0][1] == ranked[1][1]:
            kind, agreeing, source = "unknown", 0, "tie"
        else:
            kind, agreeing = ranked[0]
            source = sources.most_common(1)[0][0]
            if kind == "federal" and agreeing * 2 < len(members):
                kind, source = "unknown", "federal_minority"
        authority = Authority(kind, len(members), agreeing, source)
        for mid, _ in members:
            out[mid] = authority
    return out


# --- shapes of sender values, by pattern -------------------------------------------------

_ROLE_WORDS = re.compile(
    r"(alert|warn|notif|notice|emerg|ema\b|oem|eoc|ipaws|cap|wea|eas|dispatch|911|admin|info|"
    r"noreply|no-reply|donotreply|public|safety|county|city|police|sheriff|fire|office|"
    r"system|ops|operations|center|centre|duty|watch|desk|comm|message|broadcast|mass|"
    r"everbridge|rave|hyper|omnilert|regroup|codered|onsolve|nixle|genasys|alertus|"
    r"web|mail|team|group|staff|support|service|help|contact|news|media|pio|dept|agency)",
    re.IGNORECASE,
)
_FIRST_LAST = re.compile(r"^[a-z]{2,}(?:[._-][a-z]+)?[._-][a-z]{2,}\d{0,3}$", re.IGNORECASE)
_INITIAL_NAME = re.compile(r"^[a-z][._-]?[a-z]{3,}\d{0,3}$", re.IGNORECASE)


def address_shape(sender: str | None) -> str:
    """Describe a sender value by its form, never returning any part of it.

    - ``not_address``: no ``@`` (except a bare ``first.last`` user name, which is
      ``first_last``);
    - ``role``: the part before ``@`` holds a role or system word (alerts, ema, dispatch,
      noreply, a vendor name ...);
    - ``first_last``: two or three words joined by a dot, dash or underscore, none of them a
      role word: the usual form of a named employee's address;
    - ``initial_name``: one letter and a word, or one word of four letters or more: often a
      named employee's address, sometimes not;
    - ``other_address``: anything else with ``@``.
    """
    if not sender:
        return "not_address"
    if "@" not in sender:
        # A user name written without a domain ("first.last") is still a person's.
        value = sender.strip()
        if _FIRST_LAST.match(value) and not _ROLE_WORDS.search(value) and not domain_of(value):
            return "first_last"
        return "not_address"
    local = sender.strip().rsplit("@", 1)[0]
    if _ROLE_WORDS.search(local):
        return "role"
    if _FIRST_LAST.match(local):
        return "first_last"
    if _INITIAL_NAME.match(local):
        return "initial_name"
    return "other_address"


PERSON_SHAPES = frozenset({"first_last", "initial_name"})
