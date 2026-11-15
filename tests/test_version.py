import re

import warntext


def test_version_is_a_pep440_string():
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+)?", warntext.__version__)
