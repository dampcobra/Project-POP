"""Spike 02 experimental parameters.

Layered-relief construction: successive colour bodies are assembled vertically,
each child seated from above into a shallow registration recess in the colour
supporting it.

Terminology, per Issue #3 decision 8
------------------------------------
**Visible step height** (`H`) is how far a completed colour level stands above the
one below it. **Layer height** means the slicer parameter and nothing else. The
two are never used interchangeably here; conflating them in an FDM context is how
a 0.8 mm artwork step gets read as an impossible 0.8 mm slicer layer.

Z model
-------
For visible step height `H` and seating depth `D`:

    child physical thickness = H + D
    recess floor            = supporting body top - D
    new completed top       = supporting body top + H

The useful property is that completed tops are **invariant in D** — with H = 0.8
the three-level stack finishes at 0.8 / 1.6 / 2.4 mm whether D is 0.2 or 0.4. That
makes D a free experimental variable that does not disturb the visible result.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- process conditions -----------------------------------------------------

#: Slicer layer height the coupon is designed for. Every Z dimension below is a
#: whole number of these, so the slicer cannot quantise a feature into a depth
#: other than the one under test.
LAYER_HEIGHT_MM: float = 0.2

#: Nominal visible step height of one completed colour level.
H_VISIBLE_STEP_MM: float = 0.8

# --- experimental variables -------------------------------------------------

#: Per-side (radial) fabrication clearance. The recess is dilated outward by this
#: amount from the child's canonical seating footprint; the child is never shrunk.
CLEARANCES_MM: tuple[float, ...] = (0.05, 0.10, 0.20)

#: Seating depth of a child into its supporting body.
DEPTHS_MM: tuple[float, ...] = (0.20, 0.40)

# --- fixed geometry ---------------------------------------------------------

#: Support thickness of the clearance/depth test fixture.
#:
#: Deliberately thicker than H so that floor thickness cannot confound the fit
#: experiment (Issue #3 decision 6). At 1.6 mm the worst-case floor under a
#: 0.4 mm recess is 1.2 mm -- six layers -- which prints without question.
#: The fixture is a test article; its own visible step height is irrelevant.
FIXTURE_SUPPORT_MM: float = 1.6

#: Backing thickness for the representative three-level artwork stack. Kept at H
#: so the intended 0.8 / 1.6 / 2.4 mm result is genuinely validated.
STACK_BACKING_MM: float = 0.8

#: Height of raised label lettering on the fixture.
LABEL_BOSS_MM: float = 0.6

#: Stroke width of label lettering: two 0.4 mm extrusions, so it resolves on FDM.
LABEL_STROKE_MM: float = 0.8

#: Cap height of label lettering.
LABEL_SIZE_MM: float = 3.0

# --- shape-control cell settings --------------------------------------------

#: The asymmetric/concave and radiused-corner control cells hold clearance and
#: depth fixed at a mid-matrix setting so shape is the only variable between
#: them. Radiused vs concave at the same setting is what separates "bound on a
#: corner" from "insufficient face clearance" as failure modes.
CONTROL_CLEARANCE_MM: float = 0.10
CONTROL_DEPTH_MM: float = 0.20


def child_thickness(depth: float, h: float = H_VISIBLE_STEP_MM) -> float:
    """Physical thickness of a child that seats `depth` and shows `h`."""
    return h + depth


@dataclass(frozen=True)
class Cell:
    """One test cell: a recess in the fixture and the child that seats into it."""

    cell_id: str
    kind: str  # "matrix" | "shape_control"
    clearance: float
    depth: float
    shape_key: str
    label: str

    @property
    def thickness(self) -> float:
        return child_thickness(self.depth)


def _label(clearance: float, depth: float) -> str:
    """Human-readable cell label, e.g. "C.05 D.20".

    The leading zero is dropped so the lettering stays short enough to sit beside
    a cell without crowding it.
    """
    c = f"{clearance:.2f}".lstrip("0")  # 0.05 -> .05
    d = f"{depth:.2f}".lstrip("0")
    return f"C{c} D{d}"


def _build_cells() -> tuple[Cell, ...]:
    cells: list[Cell] = []
    for depth in DEPTHS_MM:
        for clearance in CLEARANCES_MM:
            cid = f"m_c{int(round(clearance * 100)):03d}_d{int(round(depth * 100)):03d}"
            cells.append(
                Cell(
                    cell_id=cid,
                    kind="matrix",
                    clearance=clearance,
                    depth=depth,
                    shape_key="simple",
                    label=_label(clearance, depth),
                )
            )
    for shape_key, tag in (("concave", "S1"), ("radiused", "S2")):
        cells.append(
            Cell(
                cell_id=f"s_{shape_key}",
                kind="shape_control",
                clearance=CONTROL_CLEARANCE_MM,
                depth=CONTROL_DEPTH_MM,
                shape_key=shape_key,
                label=f"{tag} {_label(CONTROL_CLEARANCE_MM, CONTROL_DEPTH_MM)}",
            )
        )
    return tuple(cells)


#: Every test cell on the coupon: the 3x2 clearance/depth matrix on one repeated
#: simple shape, plus two shape-control cells at a fixed mid-matrix setting.
CELLS: tuple[Cell, ...] = _build_cells()
