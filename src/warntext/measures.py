"""Measures that need no model: lengths, presence, flags, capital letters, places, hazards.

Flags say that something is there (a link, a phone number); they never carry the value. States
and counties come from the SAME area codes (``PSSCCC``: part of county, state FIPS, county
FIPS; ``000`` for a whole state).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from warntext import patterns
from warntext.profile import ADMIN_CODES, NON_WEATHER_HAZARD_CODES, PEOPLE_CODES, TEST_CODES

#: Character limits of the two phone texts (47 CFR 10.430).
WEA_LIMITS = {"wea_short": 90, "wea_long": 360}

LINK = re.compile(
    r"\bhttps?://\S+|\bwww\.\S+|\b[a-z0-9-]+(\.[a-z0-9-]+)*\.(gov|com|org|net|us|edu|info|mil)"
    r"(/\S*)?\b",
    re.IGNORECASE,
)

STATE_FIPS = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}

#: A finer hazard list from the SAME event codes. Non-weather codes follow FEMA's "Event Code
#: Descriptions for Use with IPAWS"; weather codes (reserved for the weather service, but used
#: by some other senders) are grouped by kind of weather.
HAZARDS = {
    "AVA": "avalanche",
    "AVW": "avalanche",
    "CDW": "civil_danger",
    "CEM": "civil_emergency",
    "EQW": "earthquake",
    "EVI": "evacuation",
    "FRW": "fire",
    "HMW": "hazardous_materials",
    "LAE": "local_area_emergency",
    "NUW": "nuclear_plant",
    "RHW": "radiological",
    "SPW": "shelter_in_place",
    "TOE": "telephone_outage",
    "VOW": "volcano",
    "EAN": "national_emergency",
    "NIC": "national_emergency",
    "CAE": "child_abduction",
    "MEP": "missing_person",
    "BLU": "law_enforcement_officer",
    "LEW": "law_enforcement",
    "ADR": "administrative",
    "RWT": "test",
    "RMT": "test",
    "NPT": "test",
    "NMN": "test",
    "DMO": "demo",
    "TOR": "weather_tornado",
    "TOA": "weather_tornado",
    "SVR": "weather_thunderstorm",
    "SVA": "weather_thunderstorm",
    "SVS": "weather_thunderstorm",
    "SQW": "weather_wind",
    "HWW": "weather_wind",
    "HWA": "weather_wind",
    "EWW": "weather_wind",
    "FFW": "weather_flood",
    "FFA": "weather_flood",
    "FFS": "weather_flood",
    "FLW": "weather_flood",
    "FLA": "weather_flood",
    "FLS": "weather_flood",
    "WSW": "weather_winter",
    "WSA": "weather_winter",
    "BZW": "weather_winter",
    "HUW": "weather_tropical",
    "HUA": "weather_tropical",
    "TRW": "weather_tropical",
    "TRA": "weather_tropical",
    "HLS": "weather_tropical",
    "SSW": "weather_tropical",
    "SSA": "weather_tropical",
    "TSW": "weather_tsunami",
    "TSA": "weather_tsunami",
    "DSW": "weather_dust",
    "FWW": "weather_fire",
    "SPS": "weather_statement",
    "SMW": "weather_marine",
}


def event_group(codes: Iterable[str]) -> str:
    """The message's group from its SAME codes; a test code anywhere makes it a test."""
    codes = [c for c in codes if c]
    if not codes:
        return "none"
    if any(c in TEST_CODES for c in codes):
        return "test_or_demo"
    if any(c in PEOPLE_CODES for c in codes):
        return "about_people"
    if all(c in ADMIN_CODES for c in codes):
        return "administrative"
    if any(c in NON_WEATHER_HAZARD_CODES for c in codes):
        return "non_weather_hazard"
    if any(c in ADMIN_CODES for c in codes):
        return "administrative"
    return "weather"


def hazard(code: str | None) -> str | None:
    if not code:
        return None
    return HAZARDS.get(code, "weather_other" if code.isalpha() and len(code) == 3 else "unknown")


def length(text: str | None) -> int | None:
    """Characters in a field, or None when the field is absent."""
    return None if text is None else len(text)


def caps_share(texts: Iterable[str | None]) -> float | None:
    """Share of capital letters among the letters of the texts, or None without letters."""
    letters = upper = 0
    for t in texts:
        for ch in t or "":
            if ch.isalpha():
                letters += 1
                upper += ch.isupper()
    return round(upper / letters, 4) if letters else None


def has_link(texts: Iterable[str | None]) -> bool:
    return any(LINK.search(t) for t in texts if t)


def has_phone(texts: Iterable[str | None]) -> bool:
    return any(patterns.PATTERNS["phone"].search(t) for t in texts if t)


def places(same_codes: Iterable[str]) -> tuple[list[str], list[str]]:
    """States (postal codes) and counties (5-digit FIPS) named by SAME area codes.

    A code whose state part is not a state or territory (marine areas, mistakes) is left out;
    ``SS000`` names a whole state and adds no county.
    """
    states: set[str] = set()
    counties: set[str] = set()
    for code in same_codes:
        code = code.strip()
        if not re.fullmatch(r"\d{6}", code):
            continue
        st, county = code[1:3], code[3:]
        if st not in STATE_FIPS:
            continue
        states.add(STATE_FIPS[st])
        if county != "000":
            counties.add(st + county)
    return sorted(states), sorted(counties)
