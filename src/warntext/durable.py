"""Writes that reach the disk before the next step relies on them.

A file the operating system has accepted can still sit in memory, or in the drive's own cache,
for some seconds. If an external drive loses its USB connection in that time, the file is lost
although the run has moved on. These helpers flush a file, and the folder that names it, to the
device: on macOS with ``F_FULLFSYNC``, which also empties the drive's cache, and elsewhere with
``fsync``. :func:`write_once` then reads the file back and compares its SHA-256, so a raw file
that did not reach the disk whole is caught at once.
"""

from __future__ import annotations

import errno
import hashlib
import os
from pathlib import Path
from typing import IO, Any

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl
    fcntl = None  # type: ignore[assignment]

_FOLDER_SKIP = {errno.EINVAL, errno.ENOTSUP, errno.EBADF, errno.EACCES}


class WriteCheckFailed(OSError):
    """A file read back from the disk does not match what was written."""


def flush_fd(fd: int) -> None:
    """Flush one open file descriptor to the device."""
    full = getattr(fcntl, "F_FULLFSYNC", None) if fcntl is not None else None
    if full is not None:
        try:
            fcntl.fcntl(fd, full)
            return
        except OSError:
            pass  # a file system without it (some network shares): fall back to fsync
    os.fsync(fd)


def flush_file(fh: IO[Any]) -> None:
    """Flush an open file object: Python's buffer, then the operating system's."""
    fh.flush()
    flush_fd(fh.fileno())


def flush_folder(path: Path | str) -> None:
    """Flush a folder's entries, so a rename inside it is on the disk.

    Skipped where folders cannot be opened or flushed (Windows, some network shares).
    """
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:  # pragma: no cover - Windows cannot open a folder
        return
    try:
        flush_fd(fd)
    except OSError as exc:  # pragma: no cover - depends on the file system
        if exc.errno not in _FOLDER_SKIP:
            raise
    finally:
        os.close(fd)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_once(dest: Path | str, data: bytes) -> str:
    """Write ``data`` to ``dest`` once, flush it, make it read-only and check it on disk.

    ``dest`` must not exist: raw files are written once and never replaced. The data go to a
    temporary file in the same folder first, so a failed write never leaves half a file under
    the final name. Returns the SHA-256 of the file as read back from the disk.
    """
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(f"{dest} exists. Raw files are written once and never replaced.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.tmp")
    with tmp.open("wb") as fh:
        fh.write(data)
        flush_file(fh)
    tmp.rename(dest)
    dest.chmod(0o444)
    flush_folder(dest.parent)
    expected = sha256_bytes(data)
    found = sha256_file(dest)
    if found != expected:
        raise WriteCheckFailed(
            f"{dest} does not match what was written (SHA-256 {found[:12]} on disk, "
            f"{expected[:12]} expected). Check that the drive is still connected, then fetch "
            "this page again under a new name."
        )
    return found
