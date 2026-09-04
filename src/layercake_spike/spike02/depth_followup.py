"""The depth-only follow-up coupon.

Round 1 of Spike 02 settled the concept and left one question open: how deep
should a registration recess be? Andy preferred more depth at every level tested,
so this round holds everything else fixed and sweeps depth alone across a range
that brackets the expected answer.

What is held fixed, and why it matters
--------------------------------------
- **Clearance at 0.05 mm.** Round 1 could not resolve clearance: all six matrix
  children were the same nominal square, yet nominally identical prints felt
  different. Process variation is therefore at least as large as the ladder step,
  so clearance is a fixed condition here rather than a variable.
- **Shape.** The same 12 x 12 square as round 1, so results are directly
  comparable. Changing it would introduce a second variable.
- **Process conditions.** 0.20 mm layer height, 0.15 mm elephant-foot
  compensation, as round 1.

What changed, and why it had to
-------------------------------
The backing is thickened from 0.8 mm to 1.6 mm. The artwork backing is `H`, and a
0.8 mm body cannot host a 0.8 mm recess -- the floor vanishes and the pipeline
rejects it as a through-hole. The backing is a *structural* member, conceptually
independent of the visible artwork colours, so thickening the test fixture
applies existing architecture rather than altering the Z model. `H` is unchanged
and seated tops still finish flush.

Depth identification
--------------------
Twelve loose children of four thicknesses need telling apart. Markers are
**engraved**, not raised: a proud marker would stand above the artwork surface
and spoil the flushness judgement. Their *count* encodes the depth, which stays
readable on a square piece that has no inherent orientation, and they are placed
on a diagonal so no two share an edge line -- collinear features in one cap
defeat the ear-clipping triangulator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import trimesh

from .. import cleanup
from . import coupon, fabricate, font, params, solids

Ring = list[tuple[float, float]]

#: Same shape as round 1, so the two rounds are directly comparable.
FOLLOWUP_SHAPE: Ring = list(coupon.SIMPLE)

CELL_PITCH_X_MM = 36.0
MARGIN_MM = 7.0
LABEL_GAP_MM = 1.6


def footprint_area() -> float:
    return solids.footprint_area(FOLLOWUP_SHAPE)


def _marker_rings(depth_index: int) -> list[Ring]:
    """`depth_index + 1` square dimples along a diagonal of the child.

    Diagonal placement keeps every dimple off every other dimple's edge lines.
    Two features sharing a boundary line in one cap would let the ear-clipping
    triangulator merge their boundaries, which opens the surface.
    """
    size = params.MARKER_SIZE_MM
    step = 2.5
    start = 2.0
    rings: list[Ring] = []
    for i in range(depth_index + 1):
        x = start + i * step
        y = start + i * step
        rings.append([(x, y), (x + size, y), (x + size, y + size), (x, y + size)])
    return rings


@dataclass
class FollowupCell:
    depth: float
    clearance: float
    origin: tuple[float, float]
    canonical_footprint_local: Ring
    canonical_footprint: Ring
    recess: Ring
    z_planes: fabricate.ZPlanes
    floor: fabricate.FloorReport
    outline: dict
    label: str


@dataclass
class FollowupChild:
    child_id: str
    depth: float
    replicate: int
    thickness: float
    marker_count: int
    mesh: trimesh.Trimesh


@dataclass
class FollowupResult:
    fixture_mesh: trimesh.Trimesh
    fixture_footprint: Ring
    fixture_thickness: float
    cells: list[FollowupCell]
    children: list[FollowupChild]
    derived_feature_findings: list[cleanup.Finding] = field(default_factory=list)


def _label_for(depth: float) -> str:
    d = f"{depth:.2f}".lstrip("0") or "0"
    c = f"{params.DEPTH_FOLLOWUP_CLEARANCE_MM:.2f}".lstrip("0")
    return f"D{d} C{c}"


def build_depth_followup() -> FollowupResult:
    """Build the depth-sweep fixture and its replicate children."""
    thickness = params.DEPTH_FOLLOWUP_BACKING_MM
    clearance = params.DEPTH_FOLLOWUP_CLEARANCE_MM

    cells: list[FollowupCell] = []
    pockets: list[solids.Pocket] = []
    label_solids: list[trimesh.Trimesh] = []

    for i, depth in enumerate(params.DEPTH_FOLLOWUP_DEPTHS):
        ox = MARGIN_MM + i * CELL_PITCH_X_MM
        oy = MARGIN_MM + params.LABEL_SIZE_MM + LABEL_GAP_MM
        canonical = coupon._translate(FOLLOWUP_SHAPE, ox, oy)
        recess = fabricate.derive_recess(canonical, clearance)
        pockets.append(solids.Pocket(recess, depth))

        label = _label_for(depth)
        label_solids.extend(
            solids.text_solids(
                font.text_segment_rects(
                    label, ox, MARGIN_MM, params.LABEL_SIZE_MM, params.LABEL_STROKE_MM
                ),
                thickness,
                thickness + params.LABEL_BOSS_MM,
            )
        )

        cells.append(
            FollowupCell(
                depth=depth,
                clearance=clearance,
                origin=(ox, oy),
                canonical_footprint_local=list(FOLLOWUP_SHAPE),
                canonical_footprint=canonical,
                recess=recess,
                z_planes=fabricate.z_planes(thickness, depth),
                floor=fabricate.check_floor(
                    "depth_followup_fixture", f"d{depth:.2f}", thickness, depth
                ),
                outline=fabricate.visible_outline(
                    canonical, recess, nominal_clearance=clearance
                ),
                label=label,
            )
        )

    width = 2 * MARGIN_MM + len(params.DEPTH_FOLLOWUP_DEPTHS) * CELL_PITCH_X_MM
    height = 2 * MARGIN_MM + params.LABEL_SIZE_MM + LABEL_GAP_MM + 14.0
    footprint: Ring = [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)]

    v, f = solids.extrude_stepped(footprint, thickness, pockets)
    fixture = solids.union_all(
        [trimesh.Trimesh(vertices=v, faces=f, process=False), *label_solids]
    )

    children: list[FollowupChild] = []
    for i, depth in enumerate(params.DEPTH_FOLLOWUP_DEPTHS):
        child_thickness = params.child_thickness(depth)
        markers = [solids.Pocket(r, params.MARKER_DEPTH_MM) for r in _marker_rings(i)]
        cv, cf = solids.extrude_stepped(FOLLOWUP_SHAPE, child_thickness, markers)
        mesh = trimesh.Trimesh(vertices=cv, faces=cf, process=False)
        for rep in range(1, params.DEPTH_FOLLOWUP_REPLICATES + 1):
            children.append(
                FollowupChild(
                    child_id=f"d{int(round(depth * 100)):03d}_r{rep}",
                    depth=depth,
                    replicate=rep,
                    thickness=child_thickness,
                    marker_count=i + 1,
                    mesh=mesh.copy(),
                )
            )

    return FollowupResult(
        fixture_mesh=fixture,
        fixture_footprint=footprint,
        fixture_thickness=thickness,
        cells=cells,
        children=children,
        derived_feature_findings=coupon.inspect_derived_support(footprint, pockets),
    )
