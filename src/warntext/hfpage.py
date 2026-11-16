"""Checks of the dataset's page on Hugging Face, for the maintainer's publish steps.

- :func:`visibility` asks the Hub whether the dataset is public **with no credentials at all**:
  no token header, no cookie, and a session that ignores the environment (so no ``~/.netrc``
  login and no stored token can slip in). It answers ``public`` or ``not public`` (a private
  dataset and a missing one look the same signed out), and raises on any other answer or on no
  answer, so a failed check is never mistaken for a passing one.
- :func:`heading_problems` compares the card's headings with the headings of the page as the
  Hub renders it, in order, down to the last one. A raw HTML tag in a card can hide everything
  after it on the rendered page while the source looks complete.
- :func:`raw_tags` finds what a Markdown renderer would read as raw HTML, outside code; the
  release check fails on any.

Nothing here reads or sends a token.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

import requests

from warntext import __version__

SITE = "https://huggingface.co"
USER_AGENT = f"warntext/{__version__} (https://github.com/obadaKraishan) python-requests"
TIMEOUT = 60
#: The headers a signed-out request may never carry.
CREDENTIAL_HEADERS = ("authorization", "cookie", "proxy-authorization")


class PageCheckError(RuntimeError):
    """The Hub could not be asked, or answered in a way the check cannot read."""


def signed_out_session() -> requests.Session:
    """A session that carries no credentials and reads none from the environment."""
    s = requests.Session()
    s.trust_env = False  # no ~/.netrc, no proxy logins, nothing from the environment
    s.auth = None
    s.headers = requests.structures.CaseInsensitiveDict({"User-Agent": USER_AGENT})
    return s


def signed_out_get(url: str, session: Any = None) -> requests.Response:
    """GET ``url`` with no credentials; refuses to send a request that carries any."""
    s = session if session is not None else signed_out_session()
    prepared = s.prepare_request(requests.Request("GET", url))
    carried = [h for h in prepared.headers if h.lower() in CREDENTIAL_HEADERS]
    if carried:
        raise PageCheckError(f"the request would carry {carried}; a signed-out check sends none.")
    try:
        return s.send(prepared, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        raise PageCheckError(f"could not reach {url}: {type(exc).__name__}") from exc


def visibility(dataset: str, session: Any = None) -> tuple[str, int]:
    """``("public", 200)`` or ``("not public", 401 or 404)``, asked signed out.

    Raises :class:`PageCheckError` on any other status, on no answer, or on a 200 that does not
    say the dataset is public.
    """
    url = f"{SITE}/api/datasets/{dataset}"
    r = signed_out_get(url, session)
    if r.status_code in (401, 404):
        return "not public", r.status_code
    if r.status_code != 200:
        raise PageCheckError(f"{url} answered HTTP {r.status_code}; the check cannot tell.")
    try:
        private = r.json().get("private")
    except ValueError as exc:
        raise PageCheckError(f"{url} answered 200 without JSON; the check cannot tell.") from exc
    if private is not False:
        raise PageCheckError(f"{url} answered 200 signed out, but private is {private!r}.")
    return "public", 200


# --- the card's headings, in the source and on the rendered page ---------------------------

_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_ATX = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_CODE_SPAN = re.compile(r"(`+)(?:(?!\n[ \t]*\n).)+?\1", re.S)
_RAW_TAG = re.compile(
    r"<(?![A-Za-z][A-Za-z0-9+.-]*:)/?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>|<!--|<\?|<![A-Za-z]"
)


def _outside_code(text: str) -> tuple[list[str], int]:
    """The Markdown body's lines with fenced code blanked, and the front matter's line count."""
    m = _FRONT.match(text)
    start = m.end() if m else 0
    kept, fence = [], ""
    for line in text[start:].split("\n"):
        f = _FENCE.match(line)
        if fence:
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= len(fence):
                fence = ""
            kept.append("")
        elif f:
            fence = f.group(1)
            kept.append("")
        else:
            kept.append(line)
    return kept, text[:start].count("\n")


def _plain(text: str) -> str:
    """A heading's words as a reader sees them: no backticks, emphasis marks or link targets."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*]", "", text)
    return " ".join(text.split())


def card_headings(text: str) -> list[str]:
    """The card's headings (levels 1 to 6), in order, outside code and the front matter."""
    lines, _ = _outside_code(text)
    return [_plain(m.group(2)) for line in lines if (m := _ATX.match(line))]


class _Headings(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.open: list[Any] | None = None
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if re.fullmatch(r"h[1-6]", tag) and self.open is None:
            self.open = [tag, ""]

    def handle_endtag(self, tag: str) -> None:
        if self.open is not None and tag == self.open[0]:
            self.found.append(" ".join(self.open[1].split()))
            self.open = None

    def handle_data(self, data: str) -> None:
        if self.open is not None:
            self.open[1] += data


def page_headings(html: str) -> list[str]:
    """The text of every h1 to h6 element of a page, in order."""
    p = _Headings()
    p.feed(html)
    p.close()
    return p.found


def heading_problems(card: str, html: str) -> list[str]:
    """Each card heading missing from the page, or shown out of order; empty when all are shown.

    The page has headings of its own (the site's), so the card's must appear among them as a
    sequence in the same order, the last one included.
    """
    want = card_headings(card)
    if not want:
        return ["the card has no headings"]
    found = page_headings(html)
    problems = [f"not on the page: {w!r}" for w in want if w not in found]
    if not problems:
        at = 0
        for w in want:
            try:
                at = found.index(w, at) + 1
            except ValueError:
                problems.append(f"out of order on the page: {w!r}")
    return problems


def raw_tags(text: str) -> list[tuple[int, str]]:
    """What a Markdown renderer would read as raw HTML, outside code: (line, tag) pairs.

    The Hub renders a card's raw HTML, so a placeholder written as ``<name>`` opens an element
    that can hide the rest of the card. Code spans, fenced code and autolinks
    (``<https://...>``) are fine; the front matter is not Markdown and is skipped.
    """
    lines, before = _outside_code(text)
    body = _CODE_SPAN.sub(lambda s: re.sub(r"[^\n]", " ", s.group(0)), "\n".join(lines))
    return [
        (before + body.count("\n", 0, tag.start()) + 1, tag.group(0))
        for tag in _RAW_TAG.finditer(body)
    ]


def tag_problems(name: str, text: str) -> list[str]:
    """One problem per raw tag in ``text``."""
    return [
        f"{name} line {line}: {tag!r} is read as an HTML tag on Hugging Face and can hide the "
        "text after it; write it in words or in backticks."
        for line, tag in raw_tags(text)
    ]
