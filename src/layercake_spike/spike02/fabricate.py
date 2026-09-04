"""Fabrication derivation: canonical artwork in, physical bodies out.

Spike 01 established that canonical artwork boundaries are mathematically exact
and that physical clearance belongs to derived fabrication geometry. This module
is that derivation step. Nothing here mutates canonical geometry; every function
takes canonical rings and returns new ones.

Two rules do the real work.

Canonical containment is not a fabrication through-hole
-------------------------------------------------------
In canonical topology an island is a **hole** in the colour enclosing it. In
layered-relief fabrication the supporting body is made **solid** beneath the
child and only a shallow registration pocket is removed::

    fabrication_support = solid supporting footprint - shallow derived child recess

The child visually replaces that supporting material once assembled. This assumes
**visually opaque material**; translucent behaviour is a future constraint and is
outside Spike 02. Recorded as ADR 0002.

Clearance is a radial dilation of the recess
--------------------------------------------
The recess is the child's canonical seating footprint dilated outward by the
per-side clearance, with a **round** join so the separation is exactly the
requested clearance everywhere -- including at corners, where a mitre would give
more clearance on the diagonal than was asked for. The child is never shrunk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import NamedTuple, Sequence

from .. import clipper
from . import params

Ring = list[tuple[float, float]]


def ring_area(ring: Ring) -> float:
    """Signed area of a ring."""
    return clipper.area(ring)


# --- clearance --------------------------------------------------------------


def derive_recess(child_footprint: Ring, clearance: float) -> Ring:
    """Derive the registration recess for a child's seating footprint.

    Returns a **new** ring; the input is not modified. Round join, so the
    boundary separation is a true radial `clearance` everywhere.
    """
    if clearance <= 0:
        raise ValueError(f"clearance must be positive, got {clearance}")
    grown = clipper.offset([list(child_footprint)], clearance, join="round")
    if not grown:
        raise ValueError("recess derivation produced no geometry")
    return max(grown, key=lambda r: abs(clipper.area(r)))


def visible_outline(
    child_footprint: Ring, recess: Ring, nominal_clearance: float | None = None
) -> dict:
    """The band of supporting colour left visible around a seated child.

    This is what a viewer actually sees around each piece: a `clearance`-wide
    outline in the supporting colour. Reported so Andy can judge it physically.

    `achieved_clearance_mm` is measured from the derived geometry rather than
    assumed. Clipper2 approximates corner arcs with chords, so the achieved
    separation falls a sagitta short of nominal -- around 0.4 um at these radii,
    some 1000x finer than a 0.4 mm nozzle. It is reported rather than hidden;
    removing it would cost thousands of vertices per corner for no physical gain.
    """
    ring = clipper.boolean_op([recess], [list(child_footprint)], "difference")
    achieved = _min_separation(child_footprint, recess)
    out = {
        "width_mm": achieved,
        "achieved_clearance_mm": achieved,
        "area_mm2": abs(clipper.total_area(ring)),
        "child_area_mm2": abs(clipper.area(child_footprint)),
        "recess_area_mm2": abs(clipper.area(recess)),
    }
    if nominal_clearance is not None:
        out["nominal_clearance_mm"] = nominal_clearance
        out["arc_shortfall_mm"] = nominal_clearance - achieved
    return out


def _min_separation(inner: Ring, outer: Ring) -> float:
    """Smallest distance from any inner vertex to the outer boundary."""
    best = float("inf")
    n = len(outer)
    for px, py in inner:
        for i in range(n):
            ax, ay = outer[i]
            bx, by = outer[(i + 1) % n]
            dx, dy = bx - ax, by - ay
            seg = dx * dx + dy * dy
            t = 0.0 if seg == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg))
            qx, qy = ax + t * dx, ay + t * dy
            best = min(best, ((px - qx) ** 2 + (py - qy) ** 2) ** 0.5)
    return best


# --- Z model ----------------------------------------------------------------


class ZPlanes(NamedTuple):
    """The Z planes of one seating relationship."""

    support_top: float
    recess_floor: float
    child_bottom: float
    child_top: float
    child_thickness: float
    depth: float
    visible_step: float

    def to_dict(self) -> dict:
        return self._asdict()


def z_planes(
    support_top: float, depth: float, h: float = params.H_VISIBLE_STEP_MM
) -> ZPlanes:
    """Z planes for a child seating `depth` into a support topped at `support_top`.

    The completed top is `support_top + h` regardless of `depth`, which is what
    makes seating depth a free experimental variable.
    """
    floor = support_top - depth
    thickness = params.child_thickness(depth, h)
    return ZPlanes(
        support_top=support_top,
        recess_floor=floor,
        child_bottom=floor,
        child_top=floor + thickness,
        child_thickness=thickness,
        depth=depth,
        visible_step=h,
    )


# --- support solidification -------------------------------------------------


def solidify_support(
    outer: Ring, canonical_holes: Sequence[Ring]
) -> tuple[Ring, list[Ring]]:
    """Make a supporting body solid beneath the children it hosts.

    Canonical holes are **discarded**: in layered relief the child seats into a
    shallow pocket from above rather than passing through a co-planar opening, so
    the support stays structurally continuous underneath. Returns copies; the
    canonical rings are untouched.
    """
    return list(outer), []


# --- floor checks -----------------------------------------------------------


@dataclass(frozen=True)
class FloorReport:
    """Remaining support thickness beneath one recess."""

    body: str
    feature: str
    thickness_mm: float
    depth_mm: float
    floor_mm: float
    ok: bool

    def to_dict(self) -> dict:
        return asdict(self)


def check_floor(body: str, feature: str, thickness: float, depth: float) -> FloorReport:
    """Remaining material under a pocket. A non-positive floor is a through-hole."""
    floor = thickness - depth
    return FloorReport(
        body=body,
        feature=feature,
        thickness_mm=thickness,
        depth_mm=depth,
        floor_mm=floor,
        ok=floor > 0,
    )


# --- registration -----------------------------------------------------------


def registration_freedom(clearance: float) -> float:
    """How far a child can shift within its recess, per side, in mm."""
    return clearance


def cumulative_registration_freedom(clearances: Sequence[float]) -> float:
    """Worst-case positional error of the topmost child relative to the base.

    Each seating contributes its own per-side play, so error accumulates
    linearly with relief depth. Measured and reported for evidence; solving it is
    out of scope for this spike.
    """
    return sum(registration_freedom(c) for c in clearances)
