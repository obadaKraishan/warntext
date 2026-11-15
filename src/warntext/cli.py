"""The ``warntext`` command line."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from warntext import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="warntext",
        description="Build and check the WarnText corpus of public alert messages.",
    )
    parser.add_argument("--version", action="version", version=f"warntext {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
