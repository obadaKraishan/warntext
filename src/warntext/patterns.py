"""Count personal details in alert text by pattern. Counts only: no match is ever returned.

Some alerts are about people (missing children and adults, wanted suspects) and carry phone
numbers, car plates, ages and descriptions. These patterns measure how often such details
appear, so the privacy options can be weighed with numbers. They are deliberately simple and
over-count rather than under-count; they never identify anyone, and no pattern tries to infer
an attribute of a person (there is no pattern for race, sex or any other trait).
"""

from __future__ import annotations

import re

PATTERNS: dict[str, re.Pattern[str]] = {
    # North American numbers: 555-0123, (555) 555-0123, 555.555.0123, 1-800-555-0123.
    "phone": re.compile(
        r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?!\d)"
    ),
    # A plate or tag word followed by a short letters-and-digits token that has a digit.
    "plate": re.compile(
        r"\b(?:license\s+plate|lic(?:ense)?\.?\s*(?:plate|tag)?|plates?|tags?)\b"
        r"\s*(?:#|no\.?|number|num\.?)?\s*:?\s*(?=[A-Z0-9-]*\d)[A-Z0-9][A-Z0-9-]{1,8}\b",
        re.IGNORECASE,
    ),
    # Ages: "12 years old", "12-year-old", "12 yrs", "12 y/o", "age 12", "aged 12".
    "age": re.compile(
        r"\b\d{1,3}\s*-?\s*(?:years?|yrs?)\s*-?\s*old\b|\b\d{1,3}\s*(?:yrs?|y/o|yoa)\b"
        r"|\bage[ds]?\s*:?\s*\d{1,3}\b",
        re.IGNORECASE,
    ),
    # Height or weight given as numbers: 5'7", 5 ft 7 in, 150 lbs, 150 pounds.
    "height_weight": re.compile(
        r"\b\d\s*'\s*\d{1,2}\b|\b\d\s*(?:ft|feet|foot)\b|\b\d{2,3}\s*(?:lbs?|pounds)\b",
        re.IGNORECASE,
    ),
    # The phrase missing-person messages use for a last known place or time.
    "last_seen": re.compile(r"\blast\s+(?:seen|known|heard)\b", re.IGNORECASE),
}


def count(text: str | None) -> dict[str, int]:
    """How many times each pattern occurs in ``text``."""
    if not text:
        return dict.fromkeys(PATTERNS, 0)
    return {name: len(p.findall(text)) for name, p in PATTERNS.items()}


def present(text: str | None) -> dict[str, bool]:
    """Whether each pattern occurs at least once in ``text``."""
    return {name: n > 0 for name, n in count(text).items()}
