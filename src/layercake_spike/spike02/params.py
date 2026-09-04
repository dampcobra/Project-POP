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

# --- depth-only follow-up ---------------------------------------------------
#
# Round 1 established that the shallow-registration concept works and that
# D = 0.20 mm is too shallow. The mechanism is visible in the layer arithmetic:
# at a 0.20 mm layer height, a 0.20 mm recess engages exactly ONE layer -- the
# first one, which carries squish, elephant-foot compensation and bed-levelling
# error. No well-formed material does any registering at all. D = 0.40 mm brings
# one clean layer into play, which is why it felt better.
#
# Round 1 could not resolve clearance: all six matrix children are the same
# nominal square, yet nominally identical prints felt different, so process
# variation is at least as large as the ladder step. Clearance is therefore held
# at the process floor here and treated as a fixed condition, not a variable.
#
# The acceptance target is positive registration during normal glue-up handling
# -- not dry retention, and not a friction fit.

#: Recess depths under test: 2, 3, 4 and 5 layers at a 0.20 mm layer height.
#: Deliberately brackets the expected optimum. Every previous round ended with
#: "I wish I had more", so this one includes a depth expected to be too deep.
DEPTH_FOLLOWUP_DEPTHS: tuple[float, ...] = (0.40, 0.60, 0.80, 1.00)

#: Structural backing for the follow-up fixture.
#:
#: The artwork backing is H (0.8 mm), which cannot host a 0.8 mm recess -- the
#: floor would vanish and the pipeline rejects it as a through-hole. The backing
#: is a *structural* member, conceptually independent of the visible artwork
#: colours (Issue #1), so thickening it is applying existing architecture rather
#: than changing the Z model. At 1.6 mm the floor is 0.6 mm even at D = 1.00.
DEPTH_FOLLOWUP_BACKING_MM: float = 1.6

#: Held constant at the process floor. Round 1 showed the process cannot hold a
#: distinction finer than this, so it is a fixed condition, not a chosen optimum.
DEPTH_FOLLOWUP_CLEARANCE_MM: float = 0.05

#: Identical children per depth, so print variation shows up as spread within a
#: depth rather than masquerading as a difference between depths.
DEPTH_FOLLOWUP_REPLICATES: int = 3

#: Depth identification marker engraved into a child's top face.
#:
#: Engraved, not raised: a proud marker would stand above the artwork surface and
#: spoil the flushness judgement that is part of the assessment. The count of
#: markers encodes the depth, which is readable on a square piece that has no
#: inherent orientation.
MARKER_DEPTH_MM: float = 0.4
MARKER_SIZE_MM: float = 1.6

# --- measured result (round 2) ----------------------------------------------

#: Provisional measured default recess depth, from Spike 02 round 2.
#:
#: Andy's assessment: 0.80 mm gives the best balance of positive guidance,
#: resistance to rocking/tilting, and easy removal before glue. 0.40 and 0.60 are
#: usable but feel less positively located; 1.00 is deeper than necessary and
#: does not improve handling enough to justify it.
#:
#: SCOPE. Measured for one process: Bambu P1S, 0.20 mm layer height, 0.15 mm
#: elephant-foot compensation, PLA, 12 x 12 mm square seating footprint. It is a
#: provisional default, not a universal constant.
MEASURED_DEFAULT_DEPTH_MM: float = 0.80

#: The same result expressed in layers, which is the form likelier to transfer.
#:
#: Round 1 showed the failure at 0.20 mm was that the recess engaged only the
#: first printed layer. If engagement count is the governing mechanism, then the
#: preferred depth scales with layer height rather than being fixed in mm --
#: 0.64 mm at 0.16 mm layers, 1.12 mm at 0.28 mm. That is a **hypothesis implied
#: by the data, not a tested result**; only the 0.20 mm case has been measured.
MEASURED_DEFAULT_DEPTH_LAYERS: int = 4

#: Minimum structural backing thickness needed to host the measured default.
#:
#: Consequence worth stating plainly: at H = 0.8 mm the *artwork* backing cannot
#: host a 0.80 mm recess -- the floor would be zero and the pipeline refuses it.
#: Adopting this default therefore requires the structural backing to be
#: decoupled from H in the product, not just in the test fixture. 1.2 mm leaves a
#: two-layer floor; 1.6 mm leaves four.
MIN_BACKING_FOR_DEFAULT_DEPTH_MM: float = 1.2

#: Clearance remains a HELD process-floor value, not a measured optimum.
#:
#: Round 1 could not resolve clearance: nominally identical children felt
#: different, so process variation is at least as large as the ladder step.
#: Round 2 held it fixed and therefore says nothing new about it. Recorded
#: separately from the depth result so the two are not read with equal
#: confidence.
HELD_CLEARANCE_MM: float = 0.05

# --- derived-geometry inspection --------------------------------------------

#: Minimum feature width used when *inspecting* derived fabrication geometry.
#:
#: Same 0.4 mm nozzle assumption as Spike 01's canonical cleanup, but applied in
#: report-only mode: derived geometry is never mutated, because the clearances
#: under test are themselves far below this threshold and cleanup would erase the
#: experiment (Issue #3 pipeline rule).
MIN_SUPPORT_FEATURE_MM: float = 0.4


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
