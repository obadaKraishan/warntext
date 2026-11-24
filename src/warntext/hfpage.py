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
- :func:`history_problems` checks that every commit any ref of the dataset reaches (branches,
  tags, the Hub's conversion refs, pull requests) holds only released files, so that no
  superseded build can be downloaded by its commit; :func:`fetch_history` lists them signed out.

Nothing here reads or sends a token.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
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


# --- the dataset's history: every commit any ref reaches holds released files only ----------

#: Files any commit may hold besides the released data: the card (its wording may change), the
#: manifest (one of the released versions', by git blob id) and the Hub's own attributes file.
CARD_FILE = "README.md"
MANIFEST_FILE = "manifest.json"
HUB_FILES = frozenset({".gitattributes"})
#: The Hub's ref kinds, as its API names them; a conversion ref holds the Hub's own copies of
#: the data files under other paths, so its files are checked by SHA-256 alone.
REF_KINDS = ("branches", "converts", "tags", "pullRequests")


def git_blob_id(data: bytes) -> str:
    """The git blob id of a file's bytes (how the Hub names a file that is not in LFS)."""
    import hashlib

    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def history_problems(
    listing: Mapping[str, Any], manifests: Sequence[tuple[Mapping[str, Any], str]]
) -> list[str]:
    """Each file of a commit that some ref reaches and that no released version holds.

    ``listing`` is ``{"refs": {ref: {"kind": ..., "commits": [commit ids]}}, "commits": {commit
    id: {"files": [{"path", "sha256", "blob_id"}]}}}`` (``sha256`` is the LFS hash, None for a
    file not in LFS). ``manifests`` are the released versions' manifests, each with its git blob
    id. A data file must be a released one by path and SHA-256 (by SHA-256 alone in a conversion
    ref); ``manifest.json`` must be a released manifest; the card and ``.gitattributes`` may be
    any. Messages name commits, refs and paths only; nothing is downloaded or read.
    """
    pairs = {(f["path"], f["sha256"]) for m, _ in manifests for f in m["files"]}
    hashes = {sha for _, sha in pairs}
    blobs = {blob for _, blob in manifests}
    refs = listing.get("refs") or {}
    if not refs:
        return ["no ref is listed: the listing is empty or the dataset has no branch"]
    found: dict[tuple[str, str], set[str]] = {}
    problems = []
    for ref, entry in sorted(refs.items()):
        converted = entry.get("kind") in ("converts", "convert")
        for commit in entry.get("commits") or []:
            files = (listing.get("commits") or {}).get(commit)
            if files is None:
                problems.append(f"{ref} reaches {commit[:8]}, whose files are not listed")
                continue
            for f in files.get("files") or []:
                path, sha = f["path"], f.get("sha256")
                if path == CARD_FILE or path in HUB_FILES:
                    continue
                if path == MANIFEST_FILE:
                    ok = f.get("blob_id") in blobs
                elif converted:
                    ok = sha is not None and sha in hashes
                else:
                    ok = (path, sha) in pairs
                if not ok:
                    found.setdefault((commit, path), set()).add(ref)
    for (commit, path), by in sorted(found.items()):
        problems.append(
            f"{commit[:8]} holds {path}, which no released version has (reached from "
            f"{', '.join(sorted(by))})"
        )
    return problems


def _pages(url: str, session: Any) -> list[Any]:
    """Every page of a listing the Hub's API pages by its Link header, signed out."""
    out: list[Any] = []
    while url:
        r = signed_out_get(url, session)
        if r.status_code != 200:
            raise PageCheckError(f"{url} answered HTTP {r.status_code} signed out.")
        out.extend(r.json())
        url = (r.links.get("next") or {}).get("url")
    return out


def fetch_history(dataset: str, session: Any = None) -> dict[str, Any]:
    """The listing :func:`history_problems` reads, asked signed out (a public dataset only)."""
    from urllib.parse import quote

    s = session if session is not None else signed_out_session()
    base = f"{SITE}/api/datasets/{dataset}"
    r = signed_out_get(f"{base}/refs?include_prs=1", s)
    if r.status_code != 200:
        raise PageCheckError(f"{base}/refs answered HTTP {r.status_code} signed out.")
    listing: dict[str, Any] = {"refs": {}, "commits": {}}
    for kind in REF_KINDS:
        for ref in r.json().get(kind) or []:
            name = ref["ref"]
            commits = [c["id"] for c in _pages(f"{base}/commits/{quote(name, safe='')}", s)]
            listing["refs"][name] = {
                "kind": kind,
                "target": ref.get("targetCommit"),
                "commits": commits,
            }
            for c in commits:
                if c in listing["commits"]:
                    continue
                tree = _pages(f"{base}/tree/{c}?recursive=true&expand=true", s)
                listing["commits"][c] = {
                    "files": [
                        {
                            "path": e["path"],
                            "sha256": (e.get("lfs") or {}).get("oid"),
                            "blob_id": e.get("oid"),
                        }
                        for e in tree
                        if e.get("type") == "file"
                    ]
                }
    return listing
