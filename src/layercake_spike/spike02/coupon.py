"""The labelled clearance/depth test coupon.

One fixture body carries a registration recess per test cell plus raised
lettering beside it; each cell's child prints as a separate loose piece.

Cells sit far apart on the fixture. That is deliberate: the land between two
recesses is support material, and Spike 02's earlier flat-mosaic reading failed
precisely because edge-adjacent recesses leave no room for one. Layered relief
does not have that problem, and the coupon must not reintroduce it by crowding.

The fixture's own support is deliberately thicker than the artwork's visible step
height so floor thickness cannot confound the fit measurement (Issue #3
decision 6). The fixture is a test article; its visible step height is irrelevant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import trimesh

from .. import cleanup, clipper
from . import fabricate, font, params, solids

Ring = list[tuple[float, float]]

# --- cell shapes ------------------------------------------------------------


def _rounded_square(size: float, radius: float) -> Ring:
    """A square with generously radiused corners, via a round-join dilation."""
    inner = size - 2 * radius
    core = [(0.0, 0.0), (inner, 0.0), (inner, inner), (0.0, inner)]
    grown = clipper.offset([core], radius, join="round")
    return max(grown, key=lambda r: abs(clipper.area(r)))


#: The simple repeated shape used for every cell of the 3x2 matrix.
SIMPLE: Ring = [(0.0, 0.0), (12.0, 0.0), (12.0, 12.0), (0.0, 12.0)]

#: Asymmetric shape with a reflex notch. The notch forces a tongue of support
#: material into the concavity, which the recess dilation thins by 2 x clearance.
CONCAVE: Ring = [
    (0.0, 0.0),
    (14.0, 0.0),
    (14.0, 14.0),
    (9.0, 14.0),
    (9.0, 6.0),
    (5.0, 6.0),
    (5.0, 11.0),
    (0.0, 11.0),
]

#: Generously radiused corners. Paired with CONCAVE at the same clearance and
#: depth, this separates "bound on a sharp corner" from "insufficient face
#: clearance" as failure modes -- a 0.4 mm nozzle cannot cut a sharp internal
#: corner, so a sharp-cornered child can bind while its faces still have room.
RADIUSED: Ring = _rounded_square(12.0, 2.0)

SHAPES: dict[str, Ring] = {
    "simple": SIMPLE,
    "concave": CONCAVE,
    "radiused": RADIUSED,
}

# --- layout -----------------------------------------------------------------

MARGIN_MM = 7.0
CELL_PITCH_X_MM = 36.0
CELL_PITCH_Y_MM = 28.0
CELLS_PER_ROW = 4
LABEL_GAP_MM = 1.6


def _translate(ring: Ring, dx: float, dy: float) -> Ring:
    return [(x + dx, y + dy) for x, y in ring]


def _bounds(ring: Ring) -> tuple[float, float, float, float]:
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


@dataclass
class CellPlacement:
    """One cell as laid out on the fixture."""

    cell: params.Cell
    origin: tuple[float, float]
    canonical_footprint: Ring
    recess: Ring
    z_planes: fabricate.ZPlanes
    outline: dict
    floor: fabricate.FloorReport


@dataclass
class CouponResult:
    fixture_mesh: trimesh.Trimesh
    children: dict[str, trimesh.Trimesh]
    placements: list[CellPlacement]
    fixture_footprint: Ring
    fixture_thickness: float
    derived_feature_findings: list[cleanup.Finding] = field(default_factory=list)

    @property
    def floor_reports(self) -> list[fabricate.FloorReport]:
        return [p.floor for p in self.placements]


def _cell_origin(index: int) -> tuple[float, float]:
    col, row = index % CELLS_PER_ROW, index // CELLS_PER_ROW
    return (
        MARGIN_MM + col * CELL_PITCH_X_MM,
        MARGIN_MM + row * CELL_PITCH_Y_MM,
    )


def _fixture_size(placements: list[CellPlacement]) -> tuple[float, float]:
    rows = (len(params.CELLS) + CELLS_PER_ROW - 1) // CELLS_PER_ROW
    return (
        2 * MARGIN_MM + CELLS_PER_ROW * CELL_PITCH_X_MM,
        2 * MARGIN_MM + rows * CELL_PITCH_Y_MM,
    )


def build_coupon() -> CouponResult:
    """Build the fixture and every loose child piece."""
    thickness = params.FIXTURE_SUPPORT_MM
    placements: list[CellPlacement] = []
    pockets: list[solids.Pocket] = []
    bosses: list[solids.Boss] = []

    label_solids: list[trimesh.Trimesh] = []

    for i, cell in enumerate(params.CELLS):
        ox, oy = _cell_origin(i)
        canonical = _translate(SHAPES[cell.shape_key], ox, oy)

        # derived fabrication geometry -- canonical is never modified
        recess = fabricate.derive_recess(canonical, cell.clearance)
        pockets.append(solids.Pocket(recess, cell.depth))

        z = fabricate.z_planes(thickness, cell.depth)
        outline = fabricate.visible_outline(
            canonical, recess, nominal_clearance=cell.clearance
        )
        floor = fabricate.check_floor(
            "coupon_fixture", cell.cell_id, thickness, cell.depth
        )

        _, y0, _, _ = _bounds(recess)
        label_y = y0 - LABEL_GAP_MM - params.LABEL_SIZE_MM
        for ring, holes in font.text_rings(
            cell.label, ox, label_y, params.LABEL_SIZE_MM, params.LABEL_STROKE_MM
        ):
            # Glyphs share a text baseline, so their boundaries are collinear and
            # cannot go through the cap triangulator as bosses. They are unioned
            # on instead -- see solids.union_all.
            label_solids.append(
                solids.prism(
                    ring, thickness, thickness + params.LABEL_BOSS_MM, holes
                )
            )

        placements.append(
            CellPlacement(cell, (ox, oy), canonical, recess, z, outline, floor)
        )

    width, height = _fixture_size(placements)
    footprint: Ring = [(0.0, 0.0), (width, 0.0), (width, height), (0.0, height)]

    v, f = solids.extrude_stepped(footprint, thickness, pockets, bosses)
    fixture = solids.union_all(
        [trimesh.Trimesh(vertices=v, faces=f, process=False), *label_solids]
    )

    children: dict[str, trimesh.Trimesh] = {}
    for p in placements:
        cv, cf = solids.extrude_stepped(p.canonical_footprint, p.cell.thickness)
        children[p.cell.cell_id] = trimesh.Trimesh(vertices=cv, faces=cf, process=False)

    return CouponResult(
        fixture_mesh=fixture,
        children=children,
        placements=placements,
        fixture_footprint=footprint,
        fixture_thickness=thickness,
        derived_feature_findings=inspect_derived_support(footprint, pockets),
    )


def inspect_derived_support(
    footprint: Ring, pockets: list[solids.Pocket]
) -> list[cleanup.Finding]:
    """Report thin features in the derived support, without changing anything.

    Issue #3 pipeline rule: Spike 01's 0.4 mm minimum-feature cleanup belongs to
    canonical geometry. Running it over derived geometry would erase the very
    clearances under test. But not looking at all is worse -- dilating a recess
    thins any support tongue protruding into a concavity of the child by twice
    the clearance, and an unprintable tongue would otherwise reach the plate
    unnoticed. So this measures and reports; it never mutates.
    """
    support = clipper.boolean_op([footprint], [p.ring for p in pockets], "difference")
    if not support:
        return []
    _, slivers = cleanup.detect_thin_features(support, params.MIN_SUPPORT_FEATURE_MM)
    findings: list[cleanup.Finding] = []
    for sliver in slivers:
        area = abs(clipper.area(sliver))
        if area <= 1e-3:
            continue
        x0, y0, x1, y1 = _bounds(sliver)
        findings.append(
            cleanup.Finding(
                region="coupon_fixture_support",
                kind="thin_derived_support",
                detail=(
                    f"derived support thinner than {params.MIN_SUPPORT_FEATURE_MM} mm "
                    f"at x {x0:.3f}..{x1:.3f}, y {y0:.3f}..{y1:.3f}"
                ),
                area_mm2=area,
                min_feature_mm=params.MIN_SUPPORT_FEATURE_MM,
                action="reported_only",
            )
        )
    return findings
