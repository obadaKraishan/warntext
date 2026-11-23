"""The Kaggle mirror's cover image, drawn by code (standard library only).

Exactly 560 by 280 pixels: Kaggle's command line crops a 560 by 280 header from the top left
corner (and a 280 by 280 thumbnail at x = 140), so what matters sits in the top left. The name
is drawn there from a small built-in pixel font, with a short rule under it; below, three
abstract alert cards (a colored edge, a heading bar and two lines each) stand for the messages.
No word from any alert is drawn.

``python -m warntext.cover OUT.png`` writes it; the tracked copy is ``kaggle_cover.png`` next to
this file, and a test checks that this code draws exactly its pixels.
"""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 560, 280
TRACKED = Path(__file__).with_name("kaggle_cover.png")

PAPER = (247, 245, 240)
INK = (31, 41, 55)
CARD = (255, 255, 255)
EDGE = (214, 209, 200)
HEADING = (55, 65, 81)
LINE = (176, 181, 189)
#: The cards' colored edges: an amber, a red and a teal.
ACCENTS = ((217, 119, 6), (185, 28, 28), (15, 118, 110))

#: 5 by 7 glyphs for the letters of the name.
GLYPHS = {
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "n": ("00000", "00000", "10110", "11001", "10001", "10001", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
}
NAME = "WarnText"
SCALE = 6
LEFT, TOP = 28, 26

#: Each card: its width, and its heading bar's and two lines' lengths as shares of its inside.
CARDS = ((504, 0.34, 0.88, 0.62), (468, 0.28, 0.80, 0.70), (432, 0.40, 0.74, 0.52))
CARD_HEIGHT, CARD_GAP = 44, 9


def _canvas() -> list[bytearray]:
    return [bytearray(bytes(PAPER) * WIDTH) for _ in range(HEIGHT)]


def _rect(img: list[bytearray], x0: int, y0: int, x1: int, y1: int, rgb: tuple[int, ...]) -> None:
    """Fill the pixels x0 <= x < x1, y0 <= y < y1 (clipped to the canvas)."""
    x0, x1 = max(0, x0), min(WIDTH, x1)
    for y in range(max(0, y0), min(HEIGHT, y1)):
        img[y][3 * x0 : 3 * x1] = bytes(rgb) * (x1 - x0)


def _name(img: list[bytearray], left: int, top: int) -> tuple[int, int]:
    """Draw the name from (left, top); return its right edge and the y below it."""
    x = left
    for k, ch in enumerate(NAME):
        for r, row in enumerate(GLYPHS[ch]):
            for c, bit in enumerate(row):
                if bit == "1":
                    px, py = x + c * SCALE, top + r * SCALE
                    _rect(img, px, py, px + SCALE, py + SCALE, INK)
        x += 5 * SCALE + (SCALE if k < len(NAME) - 1 else 0)
    return x, top + 7 * SCALE


def draw() -> list[bytearray]:
    """The cover's pixels, row by row (RGB)."""
    img = _canvas()
    _, below = _name(img, LEFT, TOP)
    _rect(img, LEFT, below + 12, LEFT + 84, below + 16, ACCENTS[0])  # a short rule under the name
    y = below + 34
    for (width, head, first, second), accent in zip(CARDS, ACCENTS, strict=True):
        x0, x1, y1 = LEFT, LEFT + width, y + CARD_HEIGHT
        _rect(img, x0, y, x1, y1, EDGE)  # a one-pixel border
        _rect(img, x0 + 1, y + 1, x1 - 1, y1 - 1, CARD)
        _rect(img, x0 + 1, y + 1, x0 + 9, y1 - 1, accent)  # the colored edge
        inside = x1 - x0 - 34
        _rect(img, x0 + 22, y + 9, x0 + 22 + round(inside * head), y + 16, HEADING)
        _rect(img, x0 + 22, y + 23, x0 + 22 + round(inside * first), y + 27, LINE)
        _rect(img, x0 + 22, y + 32, x0 + 22 + round(inside * second), y + 36, LINE)
        y = y1 + CARD_GAP
    return img


def png(img: list[bytearray]) -> bytes:
    """An 8-bit RGB PNG of the rows, no filter, zlib level 9."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(b"\x00" + bytes(row) for row in img)
    header = struct.pack(">IIBBBBB", len(img[0]) // 3, len(img), 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def png_size(data: bytes) -> tuple[int, int] | None:
    """The width and height a PNG's header gives, or None when ``data`` is not a PNG."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def read_png(data: bytes) -> tuple[tuple[int, int], bytes]:
    """The size and the raw scanlines of a PNG this module wrote (for the test)."""
    if png_size(data) is None:
        raise ValueError("not a PNG")
    pos, size, idat = 8, (0, 0), b""
    while pos < len(data):
        (n,) = struct.unpack(">I", data[pos : pos + 4])
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + n]
        if kind == b"IHDR":
            size = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    return size, zlib.decompress(idat)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    out = Path(args[0]) if args else TRACKED
    out.write_bytes(png(draw()))
    print(f"Wrote {out} ({WIDTH} x {HEIGHT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
