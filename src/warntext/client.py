"""Polite HTTP access to OpenFEMA.

Every request:
- carries the project's User-Agent, with a contact URL and never an email address;
- waits for the previous request to finish (the client is strictly sequential) and keeps a
  minimum interval between requests;
- backs off on HTTP 429 and 5xx, honoring ``Retry-After``, and gives up after a few tries;
- counts against one call cap and one byte cap for the whole session (retries count too);
- is read as a stream and stopped as soon as it is larger than the per-response limit, so a
  mistaken URL can never pull a bulk file;
- adds one line to the usage log: time, method, host, path, query, status, bytes and seconds.
  The log never holds a response body.

An HTTP 403 means the source has blocked us. The client raises :class:`SourceBlocked` and the
caller stops; it never retries or works around a block.
"""

from __future__ import annotations

import csv
import json
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

import requests

from warntext import __version__, durable

CONTACT_URL = "https://github.com/obadaKraishan"
LOG_FIELDS = ["time", "method", "host", "path", "query", "status", "bytes", "seconds"]

#: Session limits: at most 400 calls and 300 MB in all, unless a prompt says otherwise.
DEFAULT_MAX_CALLS = 400
DEFAULT_MAX_BYTES = 300_000_000
#: No single answer may be larger than this. The bulk files are never downloaded.
DEFAULT_MAX_RESPONSE_BYTES = 25_000_000

#: Characters left as they are in a query string, so the log reads like the documentation.
_QUERY_SAFE = "$'(),:"


class SourceBlocked(RuntimeError):
    """The source answered 403, or kept failing after every retry. Stop using it."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class CapReached(RuntimeError):
    """The next request would go over the call cap or the byte cap."""


class ResponseTooLarge(RuntimeError):
    """An answer was larger than the per-response limit; reading stopped."""

    def __init__(self, message: str, nbytes: int = 0) -> None:
        super().__init__(message)
        self.nbytes = nbytes


def user_agent() -> str:
    """The User-Agent sent with every request."""
    return f"warntext/{__version__} ({CONTACT_URL}) python-requests/{requests.__version__}"


def now_utc() -> str:
    """UTC time with milliseconds."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_url(url: str, params: Mapping[str, Any] | None = None) -> str:
    """Join ``params`` to ``url`` with spaces as ``%20`` (OData filters contain spaces)."""
    if not params:
        return url
    return f"{url}?{urlencode(dict(params), quote_via=quote, safe=_QUERY_SAFE)}"


class UsageLog:
    """Append-only CSV of request metadata. It never holds response bodies."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(
        self, when: str, method: str, url: str, status: int, nbytes: int, seconds: float
    ) -> None:
        parts = urlsplit(url)
        new = not self.path.exists() or self.path.stat().st_size == 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if new:
                writer.writerow(LOG_FIELDS)
            writer.writerow(
                [
                    when,
                    method,
                    parts.netloc,
                    parts.path,
                    parts.query,
                    status,
                    nbytes,
                    f"{seconds:.3f}",
                ]
            )
            durable.flush_file(fh)

    def rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with self.path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))


@dataclass
class Budget:
    """One call cap and one byte cap for every request in a session."""

    max_calls: int = DEFAULT_MAX_CALLS
    max_bytes: int = DEFAULT_MAX_BYTES
    calls: int = 0
    nbytes: int = 0

    @classmethod
    def from_log(
        cls,
        rows: Iterable[dict[str, str]],
        since: str,
        max_calls: int = DEFAULT_MAX_CALLS,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> Budget:
        """Start from the calls already logged since ``since`` (an ISO time in UTC)."""
        budget = cls(max_calls=max_calls, max_bytes=max_bytes)
        for row in rows:
            if row["time"] >= since:
                budget.record(int(row["bytes"] or 0))
        return budget

    @property
    def bytes_left(self) -> int:
        return max(self.max_bytes - self.nbytes, 0)

    def check_call(self) -> None:
        if self.calls >= self.max_calls:
            raise CapReached(
                f"The call cap ({self.max_calls:,}) is reached. Stop here, or ask for a higher cap."
            )
        if self.nbytes >= self.max_bytes:
            raise CapReached(
                f"The byte cap ({self.max_bytes:,}) is reached. Stop here, or ask for a higher cap."
            )

    def record(self, nbytes: int) -> None:
        self.calls += 1
        self.nbytes += nbytes


@dataclass(frozen=True)
class Response:
    """A finished answer: status, headers and the whole body (already size-checked)."""

    url: str
    status: int
    headers: Mapping[str, str]
    content: bytes
    seconds: float

    def json(self) -> Any:
        return json.loads(self.content)


@dataclass
class OpenFemaClient:
    """A sequential HTTP client for OpenFEMA. Pass a fake ``session`` in tests."""

    log: UsageLog
    budget: Budget = field(default_factory=Budget)
    session: Any = None
    sleep: Callable[[float], None] = time.sleep
    monotonic: Callable[[], float] = time.monotonic
    clock: Callable[[], str] = now_utc
    max_retries: int = 4
    base_delay: float = 5.0
    timeout: float = 120.0
    min_interval: float = 1.0
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    _last_end: float | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def _headers(self, method: str) -> dict[str, str]:
        encoding = "identity" if method == "HEAD" else "gzip"
        return {"User-Agent": user_agent(), "Accept-Encoding": encoding}

    def _pace(self) -> None:
        """Keep at least ``min_interval`` seconds between one answer and the next request."""
        if self.min_interval and self._last_end is not None:
            wait = self._last_end + self.min_interval - self.monotonic()
            if wait > 0:
                self.sleep(wait)

    def _delay(self, headers: Mapping[str, str], attempt: int) -> float:
        retry_after = headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 1.0)
            except ValueError:
                pass
        return self.base_delay * (2**attempt)

    def _read(self, resp: Any, limit: int) -> bytes:
        declared = resp.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise ResponseTooLarge(f"The server says the answer is {int(declared):,} bytes.")
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            total += len(chunk)
            if total > limit:
                raise ResponseTooLarge(
                    f"The answer passed {limit:,} bytes; reading stopped.", total
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def request(self, method: str, url: str, params: Mapping[str, Any] | None = None) -> Response:
        full = build_url(url, params)
        last_status = 0
        for attempt in range(self.max_retries + 1):
            self.budget.check_call()
            self._pace()
            when = self.clock()
            start = self.monotonic()
            status, body, headers = 0, b"", {}
            try:
                resp = self.session.request(
                    method, full, headers=self._headers(method), timeout=self.timeout, stream=True
                )
            except (requests.ConnectionError, requests.Timeout):
                resp = None
            try:
                if resp is not None:
                    status, headers = resp.status_code, dict(resp.headers)
                    if method != "HEAD":
                        limit = min(self.max_response_bytes, self.budget.bytes_left)
                        body = self._read(resp, limit)
            except ResponseTooLarge as exc:
                self._finish(when, method, full, status, exc.nbytes, start)
                raise ResponseTooLarge(f"{full}: {exc} Nothing was saved.", exc.nbytes) from exc
            finally:
                if resp is not None:
                    resp.close()
            self._finish(when, method, full, status, len(body), start)
            if status == 403:
                raise SourceBlocked(403, f"{full} answered 403 (blocked). Stop using this source.")
            if status == 0 or status == 429 or status >= 500:
                last_status = status
                if attempt < self.max_retries:
                    self.sleep(self._delay(headers, attempt))
                    continue
                break
            return Response(full, status, headers, body, self.monotonic() - start)
        what = "a network error" if last_status == 0 else f"HTTP {last_status}"
        raise SourceBlocked(
            last_status, f"{full} kept failing ({what}) after {self.max_retries + 1} tries."
        )

    def _finish(
        self, when: str, method: str, url: str, status: int, nbytes: int, start: float
    ) -> None:
        end = self.monotonic()
        self._last_end = end
        self.log.append(when, method, url, status, nbytes, end - start)
        self.budget.record(nbytes)

    def get(self, url: str, params: Mapping[str, Any] | None = None) -> Response:
        return self.request("GET", url, params)

    def get_json(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        resp = self.get(url, params)
        if resp.status != 200:
            raise RuntimeError(f"{resp.url} answered HTTP {resp.status}; expected 200.")
        return resp.json()

    def head(self, url: str) -> Response:
        """A HEAD request: the headers only, never the body."""
        return self.request("HEAD", url)
