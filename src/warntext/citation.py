"""How to cite WarnText: the one definition the Kaggle page, the card, the README and the
citation file follow.

The citation is APA 7 for a data set, with the version of the release; the DOI of the code and
documents on Zenodo is added beside it once the archive exists.
"""

from __future__ import annotations

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


def apa(version: str, year: int = YEAR, markdown: bool = True) -> str:
    """The data set's citation (APA 7); the title in italics when ``markdown``."""
    title = f"*{TITLE}*" if markdown else TITLE
    return f"{AUTHOR_APA} ({year}). {title} (Version {version}) [Data set]. {PUBLISHER}. {URL}"
