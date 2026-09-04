"""A minimal seven-segment stroke font for coupon labels.

Labels exist so Andy can identify a test cell from the printed part without
referring back to slicer position. They only need digits, a decimal point and
three letters, so a full font is unnecessary -- axis-aligned rectangles are
enough, and they print cleanly at a 0.8 mm stroke (two extrusions of a 0.4 mm
nozzle).

Segments overlap at the corners, so each glyph's rectangles are unioned through
Clipper2 before use. That matters for more than tidiness: two raised features
that merely touch along an edge would put four faces on one mesh edge and break
manifoldness. Unioning first yields disjoint rings, some with enclosed voids --
a seven-segment "0" has one -- which is why `solids.Boss` supports holes.

    a
  f   b
    g
  e   c
    d
"""

from __future__ import annotations

from typing import NamedTuple

from .. import clipper

Ring = list[tuple[float, float]]

#: Glyph box width as a fraction of cap height.
_WIDTH_RATIO = 0.62

#: Gap between glyph boxes as a fraction of cap height.
_TRACKING_RATIO = 0.30

_SEGMENTS = "abcdefg"

#: Which segments are lit for each supported character.
#:
#: "D" is drawn as the lowercase seven-segment form (bcdeg) rather than the
#: uppercase one, because uppercase D would be identical to "0". "S" is
#: identical to "5" in this font, which is tolerable: S only ever appears as a
#: cell-code prefix and 5 only ever inside a decimal.
_GLYPHS: dict[str, str] = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgedc",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
    "C": "afed",
    "D": "bcdeg",
    "S": "afgcd",
    " ": "",
    ".": "",  # drawn separately as a square below the baseline row
}


class Glyph(NamedTuple):
    """One rendered character: disjoint outer rings, each with its voids."""

    char: str
    rings: list[tuple[Ring, list[Ring]]]
    advance: float


def _segment_rects(w: float, h: float, s: float) -> dict[str, Ring]:
    """Rectangles for each of the seven segments in a `w` x `h` glyph box."""

    def rect(x0: float, y0: float, x1: float, y1: float) -> Ring:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    mid_lo, mid_hi = (h - s) / 2.0, (h + s) / 2.0
    return {
        "a": rect(0.0, h - s, w, h),
        "b": rect(w - s, mid_lo, w, h),
        "c": rect(w - s, 0.0, w, mid_hi),
        "d": rect(0.0, 0.0, w, s),
        "e": rect(0.0, 0.0, s, mid_hi),
        "f": rect(0.0, mid_lo, s, h),
        "g": rect(0.0, mid_lo, w, mid_hi),
    }


def _translate(ring: Ring, dx: float, dy: float) -> Ring:
    return [(x + dx, y + dy) for x, y in ring]


def glyph(char: str, size: float, stroke: float) -> Glyph:
    """Render one character at the origin, cap height `size`."""
    if char not in _GLYPHS:
        raise ValueError(
            f"character {char!r} is not in the coupon label font; "
            f"supported: {''.join(sorted(_GLYPHS))!r}"
        )

    w, h, s = size * _WIDTH_RATIO, size, stroke
    advance = w + size * _TRACKING_RATIO

    if char == " ":
        return Glyph(char, [], advance)

    if char == ".":
        dot = [(0.0, 0.0), (s, 0.0), (s, s), (0.0, s)]
        return Glyph(char, [(dot, [])], s + size * _TRACKING_RATIO)

    rects = _segment_rects(w, h, s)
    lit = [rects[seg] for seg in _GLYPHS[char]]

    # Union so touching/overlapping segments become disjoint rings; a ring may
    # legitimately enclose a void (e.g. "0").
    merged = clipper.boolean_tree(lit, [], "union")
    return Glyph(char, [(list(n.ring), [list(h_) for h_ in n.holes]) for n in merged], advance)


def text_rings(
    text: str, x: float, y: float, size: float, stroke: float
) -> list[tuple[Ring, list[Ring]]]:
    """Render `text` with its baseline-left corner at `(x, y)`.

    Returns `[(outer_ring, [hole_rings...]), ...]`, ready to become `solids.Boss`
    entries. Rings from different characters never touch, because tracking leaves
    a gap between glyph boxes.
    """
    out: list[tuple[Ring, list[Ring]]] = []
    cursor = x
    for char in text:
        g = glyph(char, size, stroke)
        for ring, holes in g.rings:
            out.append(
                (
                    _translate(ring, cursor, y),
                    [_translate(h, cursor, y) for h in holes],
                )
            )
        cursor += g.advance
    return out


def text_width(text: str, size: float, stroke: float) -> float:
    """Advance width of `text`, for laying labels out beside their cells."""
    return sum(glyph(c, size, stroke).advance for c in text)


def text_bounds(
    text: str, x: float, y: float, size: float, stroke: float
) -> tuple[float, float, float, float]:
    """Bounding box `(x0, y0, x1, y1)` of rendered `text`."""
    rings = text_rings(text, x, y, size, stroke)
    if not rings:
        return (x, y, x, y)
    xs = [px for ring, _ in rings for px, _ in ring]
    ys = [py for ring, _ in rings for _, py in ring]
    return (min(xs), min(ys), max(xs), max(ys))
