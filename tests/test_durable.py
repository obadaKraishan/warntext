import hashlib
import stat

import pytest

from warntext import durable


def test_write_once_writes_checks_and_makes_read_only(tmp_path):
    dest = tmp_path / "raw" / "page.json"
    digest = durable.write_once(dest, b'{"a": 1}')
    assert dest.read_bytes() == b'{"a": 1}'
    assert digest == hashlib.sha256(b'{"a": 1}').hexdigest()
    assert not dest.stat().st_mode & stat.S_IWUSR
    assert not list(dest.parent.glob(".*.tmp"))


def test_write_once_refuses_an_existing_file(tmp_path):
    dest = tmp_path / "page.json"
    durable.write_once(dest, b"one")
    with pytest.raises(FileExistsError, match="written once"):
        durable.write_once(dest, b"two")
    assert dest.read_bytes() == b"one"


def test_write_once_catches_a_file_that_differs_on_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(durable, "sha256_file", lambda path: "0" * 64)
    with pytest.raises(durable.WriteCheckFailed, match="drive is still connected"):
        durable.write_once(tmp_path / "page.json", b"data")


def test_flush_fd_falls_back_to_fsync(tmp_path, monkeypatch):
    calls = []

    class NoFullSync:
        F_FULLFSYNC = 51

        @staticmethod
        def fcntl(fd, op):
            raise OSError("not supported")

    monkeypatch.setattr(durable, "fcntl", NoFullSync)
    monkeypatch.setattr(durable.os, "fsync", lambda fd: calls.append(fd))
    with (tmp_path / "f").open("wb") as fh:
        durable.flush_fd(fh.fileno())
    assert len(calls) == 1
