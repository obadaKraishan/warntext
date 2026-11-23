"""How to cite WarnText: the one definition the Kaggle page, the card, the README and the
citation file follow.

The citation is APA 7 for a data set, with the version of the release; the DOI of the code and
documents on Zenodo is added beside it once the archive exists.
"""

from __future__ import annotations

from datetime import datetime, timezone

AUTHOR_APA = "Kraishan, O."
FAMILY, GIVEN = "Kraishan", "Obada"
ORCID = "https://orcid.org/0009-0007-7180-8620"
TITLE = (
    "WarnText: A research corpus of the public emergency alert messages sent in the United States"
)
PUBLISHER = "Hugging Face"
URL = "https://huggingface.co/datasets/obadakr/warntext"
#: The year of release 0.1.0.
YEAR = 2026

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def bound_words(until: str) -> str:
    """A release's exclusive end in words, as the card, Kaggle, the README and the citation file
    write it: ``2026-11-14T17:00:00.000Z`` is "17:00 UTC on 14 November 2026"."""
    t = datetime.fromisoformat(until.replace("Z", "+00:00")).astimezone(timezone.utc)
    return f"{t:%H:%M} UTC on {t.day} {_MONTHS[t.month - 1]} {t.year}"


def apa(version: str, year: int = YEAR, markdown: bool = True) -> str:
    """The data set's citation (APA 7); the title in italics when ``markdown``."""
    title = f"*{TITLE}*" if markdown else TITLE
    return f"{AUTHOR_APA} ({year}). {title} (Version {version}) [Data set]. {PUBLISHER}. {URL}"


#: The code and documents on Zenodo: every version (resolves to the latest), and each release.
SOFTWARE_DOI = "10.5281/zenodo.24475949"
SOFTWARE_DOIS = {"0.1.0": "10.5281/zenodo.24475950"}
#: The date each release was published.
RELEASED = {"0.1.0": "2026-11-23"}


def bibtex(version: str, year: int = YEAR) -> str:
    """The data set's BibTeX entry (``@misc``, which every BibTeX style reads)."""
    fields = [
        ("author", f"{FAMILY}, {GIVEN}"),
        (
            "title",
            "{WarnText}: A research corpus of the public emergency alert messages sent in "
            "the {United States}",
        ),
        ("year", str(year)),
        ("version", version),
        ("publisher", PUBLISHER),
        ("note", "Data set"),
        ("url", URL),
    ]
    if version in RELEASED:
        fields.insert(3, ("date", RELEASED[version]))
    width = max(len(k) for k, _ in fields)
    body = ",\n".join(f"  {k.ljust(width)} = {{{v}}}" for k, v in fields)
    return f"@misc{{kraishan{year}warntext,\n{body}\n}}"


def software_sentence(version: str) -> str:
    """The card's sentence on the code and documents on Zenodo (all versions), with the
    release's date when it is known."""
    released = (
        f"Release {version} was published on {RELEASED[version]}. " if version in RELEASED else ""
    )
    return (
        f"{released}The code and documents that build the corpus (no data table) are archived on "
        f"Zenodo: https://doi.org/{SOFTWARE_DOI} (all versions; it resolves to the latest)."
    )
