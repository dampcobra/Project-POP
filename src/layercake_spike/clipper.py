"""Thin adapter over Clipper2 (via pyclipr).

Everything the spike needs from a polygon library lives behind this module, so
Clipper2 stays replaceable. Clipper2 is robust because it works on scaled
64-bit integers rather than floats; `spec.CLIPPER_SCALE` fixes that precision
at 1e-6 mm, matching `spec.EPS`.

Rings are plain `list[tuple[float, float]]` with no repeated closing vertex.
Outer rings are counter-clockwise (positive area); holes are clockwise.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
import pyclipr

from . import spec

Ring = list[tuple[float, float]]

_SCALE = int(spec.CLIPPER_SCALE)
_MITER_LIMIT = 8.0

_CLIP_TYPES = {
    "union": pyclipr.Union,
    "difference": pyclipr.Difference,
    "intersection": pyclipr.Intersection,
}


class NestedRing(NamedTuple):
    """An outer ring together with the holes directly inside it."""

    ring: Ring
    holes: list[Ring]


def area(ring: Ring) -> float:
    """Signed shoelace area. Positive for counter-clockwise rings."""
    return 0.5 * sum(
        x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1])
    )


def _to_rings(paths) -> list[Ring]:
    return [[(float(x), float(y)) for x, y in path] for path in paths if len(path) >= 3]


def _new_clipper() -> pyclipr.Clipper:
    c = pyclipr.Clipper()
    c.scaleFactor = _SCALE
    return c


def _add(c: pyclipr.Clipper, rings: list[Ring], path_type) -> None:
    for ring in rings:
        if len(ring) >= 3:
            c.addPath(np.asarray(ring, dtype=float), path_type)


def boolean_op(subject: list[Ring], clip: list[Ring], op: str) -> list[Ring]:
    """Boolean of `subject` against `clip`, returned as a flat list of rings.

    Holes come back as separate, oppositely-wound rings. Use `boolean_tree`
    when the outer/hole nesting matters.
    """
    if op not in _CLIP_TYPES:
        raise ValueError(f"unknown boolean op {op!r}; expected one of {sorted(_CLIP_TYPES)}")
    c = _new_clipper()
    _add(c, subject, pyclipr.Subject)
    _add(c, clip, pyclipr.Clip)
    return _to_rings(c.execute(_CLIP_TYPES[op], pyclipr.FillRule.NonZero))


def boolean_tree(subject: list[Ring], clip: list[Ring], op: str) -> list[NestedRing]:
    """Same as `boolean_op` but preserving containment as a nesting tree.

    Only the first two levels are returned (outer ring plus its immediate
    holes). Islands nested inside holes appear as their own top-level entries,
    which is what the spike's containment analysis wants.
    """
    if op not in _CLIP_TYPES:
        raise ValueError(f"unknown boolean op {op!r}; expected one of {sorted(_CLIP_TYPES)}")
    c = _new_clipper()
    _add(c, subject, pyclipr.Subject)
    _add(c, clip, pyclipr.Clip)
    tree = c.execute2(_CLIP_TYPES[op], pyclipr.FillRule.NonZero)

    out: list[NestedRing] = []

    def walk(node, depth: int) -> None:
        for child in node.children:
            ring = [(float(x), float(y)) for x, y in child.polygon]
            if depth % 2 == 0:  # even depth => an outer ring
                holes = [
                    [(float(x), float(y)) for x, y in g.polygon]
                    for g in child.children
                ]
                if len(ring) >= 3:
                    out.append(NestedRing(ring, [h for h in holes if len(h) >= 3]))
            walk(child, depth + 1)

    walk(tree, 0)
    return out


_JOIN_TYPES = {
    "miter": pyclipr.JoinType.Miter,
    "round": pyclipr.JoinType.Round,
}


def offset(rings: list[Ring], delta: float, join: str = "miter") -> list[Ring]:
    """Offset `rings` by `delta` mm. Negative shrinks, positive grows.

    `join="miter"` (the default) keeps sharp corners through a shrink/grow round
    trip, which is what manufacturability cleanup needs -- a morphological opening
    must not quietly reshape the artwork.

    `join="round"` gives a true radial offset: the result is the Minkowski sum
    with a disc, so the boundary separation is exactly `delta` everywhere
    including at corners. That is the right semantics for a fabrication
    clearance, where a mitre spike would give more clearance on the diagonal
    than was asked for.
    """
    if not rings:
        return []
    if join not in _JOIN_TYPES:
        raise ValueError(f"unknown join {join!r}; expected one of {sorted(_JOIN_TYPES)}")
    o = pyclipr.ClipperOffset()
    o.scaleFactor = _SCALE
    o.miterLimit = _MITER_LIMIT
    for ring in rings:
        if len(ring) >= 3:
            o.addPath(
                np.asarray(ring, dtype=float),
                _JOIN_TYPES[join],
                pyclipr.EndType.Polygon,
            )
    return _to_rings(o.execute(delta))


def total_area(rings: list[Ring]) -> float:
    """Net area of a ring set, treating clockwise rings as holes."""
    return sum(area(r) for r in rings)
