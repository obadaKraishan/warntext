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
