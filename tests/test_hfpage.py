"""The checks of the dataset page: signed out means no credentials, headings, raw tags."""

import pytest
import requests

from warntext import cli, hfpage

CARD = """---
license: other
---

# Example

Some words.

## First part

```bash
# not a heading
```

## `codes` and **more**

### Last one
"""

PAGE = """<html><body><h1>Site name</h1>
<h1 class="x"><a href="#e"><span></span></a><span>Example</span></h1>
<h2><span>First part</span></h2><h2><span>codes and more</span></h2>
<h3><span>Last one</span></h3><h2>Files</h2></body></html>"""


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload
        self.text = "<html></html>"

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON")
        return self._payload


class FakeSession:
    """A signed-out session whose send() answers as told and records what it was given."""

    def __init__(self, answer):
        self.real = hfpage.signed_out_session()
        self.answer = answer
        self.sent = []

    def prepare_request(self, request):
        return self.real.prepare_request(request)

    def send(self, prepared, **kw):
        self.sent.append(prepared)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_public_and_not_public_are_told_apart_and_anything_else_fails_loudly():
    assert hfpage.visibility("x/y", FakeSession(FakeResponse(200, {"private": False}))) == (
        "public",
        200,
    )
    assert hfpage.visibility("x/y", FakeSession(FakeResponse(401))) == ("not public", 401)
    assert hfpage.visibility("x/y", FakeSession(FakeResponse(404))) == ("not public", 404)
    for answer, words in (
        (FakeResponse(500), "HTTP 500"),
        (FakeResponse(200), "without JSON"),
        (FakeResponse(200, {"private": True}), "private is True"),
        (FakeResponse(200, {}), "private is None"),
        (requests.ConnectionError("down"), "could not reach"),
    ):
        with pytest.raises(hfpage.PageCheckError, match=words):
            hfpage.visibility("x/y", FakeSession(answer))


def test_a_signed_out_request_carries_no_credentials_even_with_a_netrc_and_a_token(
    tmp_path, monkeypatch
):
    netrc = tmp_path / "netrc"
    netrc.write_text("machine huggingface.co login someone password not-a-real-secret\n")
    netrc.chmod(0o600)
    monkeypatch.setenv("NETRC", str(netrc))
    monkeypatch.setenv("HF_TOKEN", "not-a-real-token")
    fake = FakeSession(FakeResponse(401))
    hfpage.visibility("x/y", fake)
    sent = fake.sent[0]
    assert not [h for h in sent.headers if h.lower() in hfpage.CREDENTIAL_HEADERS]
    assert sent.headers["User-Agent"].startswith("warntext/")
    # A plain session would have read the netrc login; this one does not.
    plain = requests.Session().prepare_request(requests.Request("GET", "https://huggingface.co/"))
    assert "Authorization" in plain.headers


def test_a_request_that_would_carry_credentials_is_refused_before_it_is_sent():
    fake = FakeSession(FakeResponse(200, {"private": False}))
    fake.real.headers["Authorization"] = "Bearer x"
    with pytest.raises(hfpage.PageCheckError, match="carry"):
        hfpage.visibility("x/y", fake)
    assert fake.sent == []


def test_card_headings_skip_code_and_the_front_matter():
    assert hfpage.card_headings(CARD) == ["Example", "First part", "codes and more", "Last one"]


def test_every_heading_shown_in_order_passes():
    assert hfpage.page_headings(PAGE)[:2] == ["Site name", "Example"]
    assert hfpage.heading_problems(CARD, PAGE) == []


def test_a_cut_off_page_or_a_changed_order_fails():
    cut = PAGE.split("<h3>")[0]
    assert hfpage.heading_problems(CARD, cut) == ["not on the page: 'Last one'"]
    swapped = PAGE.replace("First part", "TMP").replace("codes and more", "First part")
    swapped = swapped.replace("TMP", "codes and more")
    assert any("out of order" in p for p in hfpage.heading_problems(CARD, swapped))
    assert hfpage.heading_problems("no headings at all", PAGE) == ["the card has no headings"]


def test_raw_tags_outside_code_are_found_and_code_and_autolinks_are_not():
    text = (
        "---\nx: <y>\n---\n\nAn <title> here.\n\n`<code>` is fine, <https://example.org> too.\n"
        "```\n<pre>\n```\n<!-- a comment -->\n</div>\n"
    )
    found = hfpage.raw_tags(text)
    assert [t for _, t in found] == ["<title>", "<!--", "</div>"]
    assert found[0][0] == 5
    assert hfpage.tag_problems("README.md", "plain words") == []
    assert "line 5" in hfpage.tag_problems("README.md", text)[0]


def test_the_commands(tmp_path, monkeypatch, capsys):
    card = tmp_path / "README.md"
    card.write_text(CARD)
    page = tmp_path / "page.html"
    page.write_text(PAGE)
    assert cli.main(["page", "headings", "--card", str(card), "--page", str(page)]) == 0
    assert "The last heading, 'Last one': shown." in capsys.readouterr().out
    page.write_text(PAGE.split("<h3>")[0])
    assert cli.main(["page", "headings", "--card", str(card), "--page", str(page)]) == 1
    assert "NOT SHOWN" in capsys.readouterr().out

    answers = iter([("not public", 401), ("public", 200)])
    monkeypatch.setattr(hfpage, "visibility", lambda d: next(answers))
    assert cli.main(["page", "visibility", "--expect", "not-public"]) == 0
    assert cli.main(["page", "visibility", "--expect", "not-public"]) == 1
    assert "STOP" in capsys.readouterr().out

    def down(dataset):
        raise hfpage.PageCheckError("could not reach it")

    monkeypatch.setattr(hfpage, "visibility", down)
    assert cli.main(["page", "visibility", "--expect", "public"]) == 2

    monkeypatch.setattr(hfpage, "signed_out_get", lambda url: FakeResponse(401))
    assert cli.main(["page", "headings", "--card", str(card), "--url", "https://x"]) == 1

    def unreachable(url):
        raise hfpage.PageCheckError("could not reach it")

    monkeypatch.setattr(hfpage, "signed_out_get", unreachable)
    assert cli.main(["page", "headings", "--card", str(card), "--url", "https://x"]) == 2


# --- the dataset's history ---------------------------------------------------------------

DATA = {"alerts/messages.parquet": "a" * 64, "alerts/text_other.parquet": "b" * 64}
MANIFEST = {
    "version": "9.9.9",
    "files": [{"path": p, "sha256": h} for p, h in DATA.items()],
}
MANIFEST_BLOB = "c" * 40


def commit(files):
    return {"files": [{"path": p, "sha256": s, "blob_id": b} for p, s, b in files]}


def released_commit():
    return commit(
        [
            (".gitattributes", None, "d" * 40),
            ("README.md", None, "e" * 40),
            ("manifest.json", None, MANIFEST_BLOB),
            *((p, h, "f" * 40) for p, h in DATA.items()),
        ]
    )


def test_a_history_of_released_files_passes_and_an_old_build_fails():
    good = {
        "refs": {
            "refs/heads/main": {"kind": "branches", "commits": ["1" * 40]},
            "refs/tags/v9.9.9": {"kind": "tags", "commits": ["1" * 40]},
        },
        "commits": {"1" * 40: released_commit()},
    }
    assert hfpage.history_problems(good, [(MANIFEST, MANIFEST_BLOB)]) == []
    # An older commit, reached from the tag only, holds a superseded text file and manifest.
    old = commit(
        [
            ("alerts/text_other.parquet", "9" * 64, "f" * 40),
            ("manifest.json", None, "8" * 40),
            ("README.md", None, "7" * 40),
        ]
    )
    bad = {
        "refs": {
            "refs/heads/main": {"kind": "branches", "commits": ["1" * 40]},
            "refs/tags/v9.9.9": {"kind": "tags", "commits": ["1" * 40, "2" * 40]},
        },
        "commits": {"1" * 40: released_commit(), "2" * 40: old},
    }
    problems = hfpage.history_problems(bad, [(MANIFEST, MANIFEST_BLOB)])
    assert problems == [
        "22222222 holds alerts/text_other.parquet, which no released version has (reached "
        "from refs/tags/v9.9.9)",
        "22222222 holds manifest.json, which no released version has (reached from "
        "refs/tags/v9.9.9)",
    ]
    # A released file under another path counts only in the Hub's conversion ref.
    moved = commit([("other/place.parquet", "a" * 64, "f" * 40)])
    for kind, fails in (("converts", False), ("branches", True), ("pullRequests", True)):
        listing = {
            "refs": {"refs/x": {"kind": kind, "commits": ["3" * 40]}},
            "commits": {"3" * 40: moved},
        }
        assert bool(hfpage.history_problems(listing, [(MANIFEST, MANIFEST_BLOB)])) is fails
    copy_unknown = commit([("messages/alerts/0000.parquet", "6" * 64, "f" * 40)])
    listing = {
        "refs": {"refs/convert/parquet": {"kind": "converts", "commits": ["4" * 40]}},
        "commits": {"4" * 40: copy_unknown},
    }
    assert (
        "no released version has"
        in hfpage.history_problems(listing, [(MANIFEST, MANIFEST_BLOB)])[0]
    )


def test_the_history_accepts_the_easy_access_files_by_hash_or_by_git_blob():
    layered = {
        **MANIFEST,
        "access_files": [
            {"path": "00_start_here_messages.csv", "sha256": "c" * 64},
            {"path": "fields.csv", "sha256": "d" * 64},
        ],
        "access_blobs": {"fields.csv": "e" * 40, "00_start_here_messages.csv": "b" * 40},
    }
    files = commit(
        [
            ("00_start_here_messages.csv", "c" * 64, "f" * 40),  # in LFS, by SHA-256
            ("fields.csv", None, "e" * 40),  # a regular file, by its git blob id
        ]
    )
    listing = {
        "refs": {"refs/pr/1": {"kind": "pullRequests", "commits": ["5" * 40]}},
        "commits": {"5" * 40: files},
    }
    assert hfpage.history_problems(listing, [(layered, MANIFEST_BLOB)]) == []
    other = commit([("fields.csv", None, "0" * 40)])
    listing["commits"]["5" * 40] = other
    assert "holds fields.csv" in hfpage.history_problems(listing, [(layered, MANIFEST_BLOB)])[0]


def test_a_history_check_needs_refs_and_every_commits_files_and_reads_several_versions():
    assert hfpage.history_problems({}, [(MANIFEST, MANIFEST_BLOB)])[0].startswith("no ref")
    unlisted = {"refs": {"refs/heads/main": {"kind": "branches", "commits": ["5" * 40]}}}
    assert (
        "whose files are not listed"
        in hfpage.history_problems(unlisted, [(MANIFEST, MANIFEST_BLOB)])[0]
    )
    # A later version keeps the earlier version's commit in its history: both are released.
    later = {
        "version": "9.9.10",
        "files": [{"path": "alerts/messages.parquet", "sha256": "0" * 64}],
    }
    listing = {
        "refs": {"refs/heads/main": {"kind": "branches", "commits": ["6" * 40, "1" * 40]}},
        "commits": {
            "6" * 40: commit(
                [("alerts/messages.parquet", "0" * 64, "f" * 40), ("manifest.json", None, "b" * 40)]
            ),
            "1" * 40: released_commit(),
        },
    }
    both = [(MANIFEST, MANIFEST_BLOB), (later, "b" * 40)]
    assert hfpage.history_problems(listing, both) == []
    assert len(hfpage.history_problems(listing, both[1:])) == 3  # the earlier version's files


class PagedSession(FakeSession):
    """Answers by URL, with a Link header for the next page where one is given."""

    def __init__(self, pages):
        super().__init__(None)
        self.pages = pages

    def send(self, prepared, **kw):
        self.sent.append(prepared)
        payload, nxt = self.pages[prepared.url]
        r = FakeResponse(200, payload)
        r.links = {"next": {"url": nxt}} if nxt else {}
        return r


def test_the_history_is_fetched_signed_out_page_by_page():
    base = "https://huggingface.co/api/datasets/x/y"
    c = "1" * 40
    tree = [
        {"type": "directory", "path": "alerts", "oid": "x"},
        {
            "type": "file",
            "path": "alerts/messages.parquet",
            "oid": "f" * 40,
            "lfs": {"oid": "a" * 64},
        },
    ]
    pages = {
        f"{base}/refs?include_prs=1": (
            {
                "branches": [{"ref": "refs/heads/main", "targetCommit": c}],
                "converts": [],
                "tags": [],
            },
            None,
        ),
        f"{base}/commits/refs%2Fheads%2Fmain": ([{"id": c}], None),
        f"{base}/tree/{c}?recursive=true&expand=true": (tree[:1], f"{base}/tree/{c}?cursor=2"),
        f"{base}/tree/{c}?cursor=2": (
            [*tree[1:], {"type": "file", "path": "README.md", "oid": "e" * 40}],
            None,
        ),
    }
    s = PagedSession(pages)
    listing = hfpage.fetch_history("x/y", session=s)
    assert listing["refs"]["refs/heads/main"]["commits"] == [c]
    assert listing["commits"][c]["files"] == [
        {"path": "alerts/messages.parquet", "sha256": "a" * 64, "blob_id": "f" * 40},
        {"path": "README.md", "sha256": None, "blob_id": "e" * 40},
    ]
    assert all("authorization" not in {k.lower() for k in p.headers} for p in s.sent)
    bad = FakeSession(FakeResponse(401, {}))
    with pytest.raises(hfpage.PageCheckError, match="HTTP 401"):
        hfpage.fetch_history("x/y", session=bad)


def test_the_history_command_reads_a_listing_and_says_what_it_found(tmp_path, capsys):
    import json

    pack = tmp_path / "pack"
    pack.mkdir()
    data = json.dumps(MANIFEST).encode()
    (pack / "manifest.json").write_bytes(data)
    blob = hfpage.git_blob_id(data)
    assert blob == __import__("hashlib").sha1(b"blob %d\0" % len(data) + data).hexdigest()
    good = {
        "refs": {
            "refs/heads/main": {"kind": "branches", "target": "1" * 40, "commits": ["1" * 40]}
        },
        "commits": {
            "1" * 40: commit(
                [("manifest.json", None, blob), ("alerts/messages.parquet", "a" * 64, "f" * 40)]
            )
        },
    }
    path = tmp_path / "listing.json"
    path.write_text(json.dumps(good))
    args = ["page", "history", "--dataset", "x/y", "--pack", str(pack), "--listing", str(path)]
    assert cli.main(args) == 0
    out = capsys.readouterr().out
    assert "1 ref(s) (refs/heads/main -> 11111111), 1 commit(s) reached, 2 file entries" in out
    assert "History passed" in out and "released versions: 9.9.9" in out
    good["commits"]["1" * 40]["files"].append(
        {"path": "alerts/old.parquet", "sha256": "9" * 64, "blob_id": "f" * 40}
    )
    path.write_text(json.dumps(good))
    assert cli.main(args) == 1
    assert "11111111 holds alerts/old.parquet" in capsys.readouterr().out
