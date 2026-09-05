"""Polygon operations for canonical artwork.

A deliberately small adapter over Clipper2 (via `pyclipr`), holding only what
the canonical model needs: area, boolean combination, and containment nesting.

**There is no offset operation here, and that is the point.** Offsetting is how
a fabrication clearance is applied, and clearance has no place in canonical
artwork. Leaving the operation out means it cannot leak in by accident -- adding
it would be a visible change to this module rather than one more call site.

Separate from the spike's adapter by design. The product package never imports
`layercake_spike`, and the spike records what was actually built and measured
rather than what the product does. Clipper2 remains the choice for the same
reason Spike 01 chose it: it works on scaled 64-bit integers rather than floats,
so boolean results are robust without epsilon-chasing.

Rings are `list[tuple[float, float]]` with no repeated closing vertex. Outer
rings are counter-clockwise (positive area); holes are clockwise.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

import numpy as np
import pyclipr

Ring = list[tuple[float, float]]

#: Millimetre -> integer scale factor. 1e-6 mm precision.
SCALE = 1_000_000

_CLIP_TYPES = {
    "union": pyclipr.Union,
    "difference": pyclipr.Difference,
    "intersection": pyclipr.Intersection,
}


class NestedRing(NamedTuple):
    """An outer ring together with the holes directly inside it."""

    ring: Ring
    holes: list[Ring]


def area(ring: Sequence[tuple[float, float]]) -> float:
    """Signed shoelace area. Positive for counter-clockwise rings."""
    pts = list(ring)
    return 0.5 * sum(
        x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])
    )


def total_area(rings: Sequence[Ring]) -> float:
    """Net area of a ring set, treating clockwise rings as holes."""
    return sum(area(r) for r in rings)


def oriented(ring: Sequence[tuple[float, float]], *, ccw: bool) -> Ring:
    """Return `ring` wound counter-clockwise (ccw=True) or clockwise.

    Rings are authored counter-clockwise for readability, but under Clipper2's
    NonZero fill rule a hole must be wound opposite to its outer ring or it adds
    area instead of subtracting it. Normalising in one place keeps that out of
    every caller -- the same lesson as ADR 0001 decision 5.
    """
    pts = list(ring)
    return pts if (area(pts) > 0) == ccw else list(reversed(pts))


def _to_rings(paths) -> list[Ring]:
    return [[(float(x), float(y)) for x, y in p] for p in paths if len(p) >= 3]


def _clipper() -> pyclipr.Clipper:
    c = pyclipr.Clipper()
    c.scaleFactor = SCALE
    return c


def _add(c: pyclipr.Clipper, rings: Sequence[Ring], path_type) -> None:
    for ring in rings:
        if len(ring) >= 3:
            c.addPath(np.asarray(ring, dtype=float), path_type)


def boolean_op(
    subject: Sequence[Ring], clip: Sequence[Ring], op: str
) -> list[Ring]:
    """Boolean of `subject` against `clip`, as a flat list of rings.

    Holes come back oppositely wound; use `total_area` for the net result.
    """
    if op not in _CLIP_TYPES:
        raise ValueError(f"unknown boolean op {op!r}; expected {sorted(_CLIP_TYPES)}")
    c = _clipper()
    _add(c, subject, pyclipr.Subject)
    _add(c, clip, pyclipr.Clip)
    return _to_rings(c.execute(_CLIP_TYPES[op], pyclipr.FillRule.NonZero))


def boolean_tree(
    subject: Sequence[Ring], clip: Sequence[Ring], op: str
) -> list[NestedRing]:
    """Same as `boolean_op`, preserving outer/hole nesting."""
    if op not in _CLIP_TYPES:
        raise ValueError(f"unknown boolean op {op!r}; expected {sorted(_CLIP_TYPES)}")
    c = _clipper()
    _add(c, subject, pyclipr.Subject)
    _add(c, clip, pyclipr.Clip)
    tree = c.execute2(_CLIP_TYPES[op], pyclipr.FillRule.NonZero)

    out: list[NestedRing] = []

    def walk(node, depth: int) -> None:
        for child in node.children:
            ring = [(float(x), float(y)) for x, y in child.polygon]
            if depth % 2 == 0 and len(ring) >= 3:
                holes = [
                    [(float(x), float(y)) for x, y in g.polygon]
                    for g in child.children
                ]
                out.append(NestedRing(ring, [h for h in holes if len(h) >= 3]))
            walk(child, depth + 1)

    walk(tree, 0)
    return out


def encloses(outer: Ring, inner: Ring, tolerance: float) -> bool:
    """Whether `outer` fully contains `inner`.

    True when subtracting `outer` from `inner` leaves nothing: every part of the
    inner ring lies within the outer one.
    """
    left_over = boolean_op([inner], [outer], "difference")
    return abs(total_area(left_over)) <= tolerance
