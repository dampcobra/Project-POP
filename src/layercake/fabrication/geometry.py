"""Clearance geometry. Fabrication only.

Offsetting a boundary is how a physical fit allowance is applied, so it belongs
on this side of the line and nowhere else. `layercake.geometry.polygons` -- the
shared layer canonical artwork uses -- deliberately has no offset operation, and
that stays true: this module is where the operation lives, and canonical code
must not reach it.

Round joins, per ADR 0002 decision 3. A round join is a true radial offset, so
the separation is the requested clearance everywhere including at corners. A
mitre would hand out `c * sqrt(2)` on a diagonal -- more than was asked for, and
unlike anything a nozzle produces.

Arc chording leaves the achieved separation a fraction of a micron short of
nominal. Spike 02 measured it at ~0.4 um and established that tightening it costs
thousands of vertices per corner for a 1000x smaller error than the nozzle, so
the default stands.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pyclipr

from ..geometry.polygons import Ring, area

#: Millimetre -> integer scale, matching the canonical layer: 1e-6 mm precision.
SCALE = 1_000_000

_JOINS = {"round": pyclipr.JoinType.Round, "miter": pyclipr.JoinType.Miter}
_MITER_LIMIT = 8.0


class ClearanceError(ValueError):
    """A clearance that cannot be applied to the geometry given."""


def offset_rings(
    rings: Sequence[Ring], delta_mm: float, join: str = "round"
) -> list[Ring]:
    """Offset rings by `delta_mm`. Positive grows, negative shrinks.

    Negative offsets are how minimum-feature inspection probes derived geometry;
    positive offsets are how a clearance is applied.
    """
    if join not in _JOINS:
        raise ClearanceError(f"unknown join {join!r}; expected one of {sorted(_JOINS)}")
    if not rings:
        return []
    o = pyclipr.ClipperOffset()
    o.scaleFactor = SCALE
    o.miterLimit = _MITER_LIMIT

    # One group, not one group per ring. Clipper reads hole direction from a
    # ring's orientation, but only among rings offered together: added
    # separately, every ring is its own outer boundary and a hole shrinks when
    # it should grow. An annulus then keeps its width under erosion instead of
    # dissolving, and a thin land goes unreported.
    paths = [np.asarray(ring, dtype=float) for ring in rings if len(ring) >= 3]
    if not paths:
        return []
    o.addPaths(paths, _JOINS[join], pyclipr.EndType.Polygon)

    return [
        [(float(x), float(y)) for x, y in path]
        for path in o.execute(delta_mm)
        if len(path) >= 3
    ]


def dilate(ring: Ring, clearance_mm: float) -> Ring:
    """Grow a child's footprint outward by a per-side clearance.

    This is the pocket a child seats into: its own outline plus room to fit.
    The canonical child is never shrunk to manufacture a fit -- ADR 0002
    decision 3 -- so the allowance is always applied here, to the recess.
    """
    if clearance_mm <= 0:
        raise ClearanceError(
            f"clearance must be positive, got {clearance_mm} mm. A zero-clearance "
            "recess is what Spike 01 proved will not physically assemble."
        )
    grown = offset_rings([list(ring)], clearance_mm, join="round")
    if not grown:
        raise ClearanceError("dilating the footprint produced no geometry")
    return max(grown, key=lambda r: abs(area(r)))


def erode(rings: Sequence[Ring], amount_mm: float) -> list[Ring]:
    """Shrink rings inward. Used only to probe for thin features, never to alter."""
    if amount_mm <= 0:
        raise ClearanceError(f"erosion must be positive, got {amount_mm} mm")
    return offset_rings(rings, -amount_mm, join="round")
