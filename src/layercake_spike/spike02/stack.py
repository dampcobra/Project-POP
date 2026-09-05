"""The representative three-level layered-relief stack.

    white backing  ->  red enclosing colour  ->  yellow enclosed island

Built from Spike 01's canonical partition -- the same `BACKING_RING`,
`B_OUTER_RING` and `C_RING` -- so the derivation is exercised against real
canonical artwork in which the island genuinely *is* a hole in the colour
enclosing it. That is the point: it is what makes the central architectural claim
checkable rather than asserted.

    canonical:    yellow is a hole in red
    fabrication:  red is SOLID beneath yellow, minus a shallow registration pocket

The child is placed from above into that pocket, so it never has to pass
laterally through a co-planar exact-size opening -- the failure that ended
Spike 01. Assumes visually opaque material; see ADR 0002.
"""

from __future__ import annotations

from dataclasses import dataclass

import trimesh

from .. import spec
from . import fabricate, params, solids

Ring = list[tuple[float, float]]


@dataclass
class Level:
    """One colour level of the stack."""

    name: str
    colour: str
    canonical_outer: Ring
    canonical_holes: list[Ring]
    fabrication_outer: Ring
    z: fabricate.ZPlanes
    mesh: trimesh.Trimesh
    recess: Ring | None
    recess_for: str | None
    floor: fabricate.FloorReport | None
    outline: dict | None


@dataclass
class StackResult:
    levels: list[Level]
    clearance: float
    depth: float

    @property
    def by_name(self) -> dict[str, Level]:
        return {lv.name: lv for lv in self.levels}

    @property
    def completed_tops(self) -> list[float]:
        return [lv.z.child_top for lv in self.levels]

    @property
    def cumulative_registration_freedom(self) -> float:
        """Worst-case play of the topmost child relative to the backing."""
        return fabricate.cumulative_registration_freedom(
            [self.clearance for lv in self.levels if lv.recess_for is not None]
        )


def build_stack(
    clearance: float = params.CONTROL_CLEARANCE_MM,
    depth: float = params.CONTROL_DEPTH_MM,
    backing: float = params.BACKING_THICKNESS_MM,
) -> StackResult:
    """Derive the white -> red -> yellow stack from Spike 01's canonical artwork.

    `backing` is an independent structural property, not derived from `H`
    (Session 01 decision). Pass `params.ROUND1_AS_PRINTED_BACKING_MM` to
    reproduce the article Andy printed in round 1.
    """
    h = params.H_VISIBLE_STEP_MM

    # --- level 1: white backing, sitting on the plate ------------------------
    white_thickness = backing
    white_z = fabricate.ZPlanes(
        support_top=0.0,
        recess_floor=0.0,
        child_bottom=0.0,
        child_top=white_thickness,
        child_thickness=white_thickness,
        depth=0.0,
        visible_step=white_thickness,
    )

    # red's canonical footprint drives white's recess
    red_canonical_outer = list(spec.B_OUTER_RING)
    red_recess = fabricate.derive_recess(red_canonical_outer, clearance)
    white_floor = fabricate.check_floor("white", "red", white_thickness, depth)

    wv, wf = solids.extrude_stepped(
        list(spec.BACKING_RING), white_thickness, [solids.Pocket(red_recess, depth)]
    )
    white = Level(
        name="white",
        colour="A",
        canonical_outer=list(spec.BACKING_RING),
        canonical_holes=[],
        fabrication_outer=list(spec.BACKING_RING),
        z=white_z,
        mesh=trimesh.Trimesh(vertices=wv, faces=wf, process=False),
        recess=red_recess,
        recess_for="red",
        floor=white_floor,
        outline=fabricate.visible_outline(
            red_canonical_outer, red_recess, nominal_clearance=clearance
        ),
    )

    # --- level 2: red, seated into white, hosting yellow ---------------------
    red_z = fabricate.z_planes(white_thickness, depth, h)

    # THE architectural step: the canonical hole is discarded, so red is solid
    # beneath yellow and only a shallow pocket is removed.
    red_fab_outer, red_fab_holes = fabricate.solidify_support(
        red_canonical_outer, [spec.C_RING]
    )
    assert red_fab_holes == []

    yellow_canonical_outer = list(spec.C_RING)
    yellow_recess = fabricate.derive_recess(yellow_canonical_outer, clearance)
    red_floor = fabricate.check_floor("red", "yellow", red_z.child_thickness, depth)

    rv, rf = solids.extrude_stepped(
        red_fab_outer, red_z.child_thickness, [solids.Pocket(yellow_recess, depth)]
    )
    rv = rv.copy()
    rv[:, 2] += red_z.child_bottom
    red = Level(
        name="red",
        colour="B",
        canonical_outer=red_canonical_outer,
        canonical_holes=[list(spec.C_RING)],
        fabrication_outer=red_fab_outer,
        z=red_z,
        mesh=trimesh.Trimesh(vertices=rv, faces=rf, process=False),
        recess=yellow_recess,
        recess_for="yellow",
        floor=red_floor,
        outline=fabricate.visible_outline(
            yellow_canonical_outer, yellow_recess, nominal_clearance=clearance
        ),
    )

    # --- level 3: yellow, seated into red ------------------------------------
    yellow_z = fabricate.z_planes(red_z.child_top, depth, h)
    yv, yf = solids.extrude_stepped(yellow_canonical_outer, yellow_z.child_thickness)
    yv = yv.copy()
    yv[:, 2] += yellow_z.child_bottom
    yellow = Level(
        name="yellow",
        colour="C",
        canonical_outer=yellow_canonical_outer,
        canonical_holes=[],
        fabrication_outer=yellow_canonical_outer,
        z=yellow_z,
        mesh=trimesh.Trimesh(vertices=yv, faces=yf, process=False),
        recess=None,
        recess_for=None,
        floor=None,
        outline=None,
    )

    return StackResult(levels=[white, red, yellow], clearance=clearance, depth=depth)
