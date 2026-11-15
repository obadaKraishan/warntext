import pytest

from warntext import __version__, cli


def test_version_flag_prints_the_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_no_arguments_prints_help(capsys):
    assert cli.main([]) == 0
    assert "usage: warntext" in capsys.readouterr().out
