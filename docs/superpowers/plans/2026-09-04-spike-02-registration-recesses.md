# Spike 02 — Shallow Registration Recesses (Layered Relief) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Prove the layered-relief construction model — successive colour bodies assembled vertically, each child seated from above into a shallow registration recess in its supporting colour — and generate a labelled FDM test coupon that establishes usable XY clearance and recess depth.

**Architecture:** Spike 02 is a new `layercake_spike.spike02` subpackage. It consumes Spike 01's canonical topology unchanged and adds a **fabrication derivation** layer on top: canonical artwork geometry in, derived fabrication bodies out. The central derivation is that a canonical hole becomes a *filled* support with a shallow pocket. Meshing extends Spike 01's construct-don't-repair approach to prisms carrying top pockets and raised bosses, so manifoldness stays structural.

**Tech Stack:** As Spike 01 — Python 3.13, `pyclipr` (Clipper2 2.0.1), `mapbox-earcut`, `trimesh`, `numpy`, `pytest`.

**Spec:** GitHub issue dampcobra/Project-POP#3 (revised, layered-relief). Two review comments on that issue record the technical analysis and the decisions taken.

## Global Constraints

- **Terminology:** `H` is **visible step height**. "Layer height" refers only to the slicer parameter (0.20 mm for this coupon). Never use "layer height" for artwork Z.
- `H = 0.8 mm`. Child physical thickness `= H + D`. Recess cut down `D` from the supporting body's top.
- Three-level target: completed tops at **0.8 / 1.6 / 2.4 mm**, invariant in `D`.
- Per-side clearances under test: **0.05, 0.10, 0.20 mm**. Recess depths: **0.20, 0.40 mm**.
- **Clearance = recess derived by dilating the child's canonical seating footprint outward, per side, with ROUND joins** (true radial). The child's canonical geometry is never shrunk.
- **Canonical containment ≠ fabrication through-hole.** `fabrication_support = solid supporting footprint − shallow derived child recess`. Assumes visually opaque material.
- Canonical artwork geometry is never mutated by derivation.
- Spike 01's 0.4 mm minimum-feature cleanup applies to **canonical geometry only**. On derived geometry it runs **report-only** and never mutates.
- Slicer layer height 0.20 mm: every Z dimension must be an integer multiple.
- No elephant-foot chamfers. Recorded as an experimental condition instead.
- Support must remain continuous: every recess floor thickness > 0, no through-holes.
- All Spike 01 tests remain green. Spike 01 modules are not modified.
- Out of scope: flat/inlay mode, UI, raster import, colour quantisation, typography, AMS/3MF, adhesive study, self-intersection validator optimisation.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/layercake_spike/spike02/params.py` | Every experimental parameter and the cell matrix. Single source of truth. |
| `src/layercake_spike/spike02/fabricate.py` | Fabrication derivation: recess dilation, child thickness, Z planes, support solidification, floor checks. |
| `src/layercake_spike/spike02/solids.py` | `extrude_stepped()` — prism with top pockets and raised bosses, manifold by construction. |
| `src/layercake_spike/spike02/font.py` | Minimal rectangle stroke font for coupon labels. |
| `src/layercake_spike/spike02/coupon.py` | Cell layout, fixture body, child bodies, labels. |
| `src/layercake_spike/spike02/stack.py` | The three-level white→red→yellow artwork stack from Spike 01's canonical partition. |
| `src/layercake_spike/spike02/arrange.py` | Co-registered assembly vs plate-laid print arrangements. |
| `src/layercake_spike/spike02/svgdebug02.py` | Canonical footprint vs derived recess boundary render. |
| `src/layercake_spike/spike02/report02.py` | Parameter/measurement JSON + human-readable observation sheet. |
| `src/layercake_spike/spike02/cli02.py` | `python -m layercake_spike.spike02` → `artefacts/spike02/`. |
| `tests/test_spike02_*.py` | One module per source module. |
| `docs/adr/0002-layered-relief-registration-recesses.md` | New ADR. |
| `docs/spike-02/report.md` | Human-readable spike report with Andy's observation tables. |

---

### Task 1: Parameters and the cell matrix

**Files:** Create `src/layercake_spike/spike02/__init__.py`, `params.py`; Test `tests/test_spike02_params.py`

**Interfaces produced:**
- `H_VISIBLE_STEP_MM = 0.8`, `LAYER_HEIGHT_MM = 0.2`, `CLEARANCES_MM = (0.05, 0.10, 0.20)`, `DEPTHS_MM = (0.20, 0.40)`
- `FIXTURE_SUPPORT_MM = 1.6` (thicker than H so floor thickness does not confound fit)
- `STACK_BACKING_MM = 0.8` (three-level case keeps H)
- `Cell(cell_id, clearance, depth, shape_key, label)` and `CELLS: tuple[Cell, ...]`
- `child_thickness(depth) -> float`

- [ ] **Step 1: failing test** — assert 3×2 matrix plus the two special cells; assert every Z dimension is an integer multiple of `LAYER_HEIGHT_MM`; assert `child_thickness(d) == H + d`; assert fixture floor under the deepest recess ≥ 1.0 mm.
- [ ] **Step 2:** run, expect ModuleNotFoundError.
- [ ] **Step 3:** implement `params.py`.
- [ ] **Step 4:** run, expect pass.
- [ ] **Step 5:** commit `feat(spike02): add experimental parameters and cell matrix`.

---

### Task 2: `extrude_stepped` — prisms with pockets and bosses

**Files:** Create `src/layercake_spike/spike02/solids.py`; Test `tests/test_spike02_solids.py`

**Interfaces produced:**
- `Pocket(ring: Ring, depth: float)`, `Boss(ring: Ring, height: float)`
- `extrude_stepped(footprint: Ring, thickness: float, pockets: Sequence[Pocket] = (), bosses: Sequence[Boss] = ()) -> (vertices, faces)`

**Design note.** The solid is `footprint × [0, t]`, minus each pocket over `(t−d, t]`, plus each boss over `(t, t+h]`. Boundary surfaces:

- bottom cap: `footprint` at `z=0`, normal −Z
- outer walls: `footprint` ring, `0 → t`
- top cap: `footprint − pockets − bosses` at `z=t`, normal +Z
- per pocket: floor at `z=t−d` (normal +Z) and walls `t−d → t`
- per boss: cap at `z=t+h` (normal +Z) and walls `t → t+h`

Every ring edge is then used exactly twice with opposite orientation, so the result is watertight by construction — the same argument as Spike 01's extruder. Pockets and bosses must not overlap each other or the footprint boundary; union them with Clipper2 before use and assert disjointness.

- [ ] **Step 1: failing test** — plain prism volume; prism with one pocket (volume = `A·t − A_p·d`); pocket floor Z correct; prism with one boss (volume = `A·t + A_b·h`); pockets of differing depths in one body; watertight + winding-consistent + zero non-manifold edges under Spike 01's `validate` for every case; Euler number 2 (no through-holes).
- [ ] **Step 2:** run, expect fail.
- [ ] **Step 3:** implement.
- [ ] **Step 4:** run, expect pass.
- [ ] **Step 5:** commit `feat(spike02): add stepped extruder for pockets and bosses`.

---

### Task 3: Fabrication derivation

**Files:** Create `src/layercake_spike/spike02/fabricate.py`; Test `tests/test_spike02_fabricate.py`

**Interfaces produced:**
- `derive_recess(child_footprint: Ring, clearance: float) -> Ring` — Clipper2 offset, **round join**
- `ZPlanes(support_top, recess_floor, child_bottom, child_top)` and `z_planes(support_top, depth, h) -> ZPlanes`
- `solidify_support(outer: Ring, canonical_holes: list[Ring]) -> Ring` — discards canonical holes
- `FloorReport(body, pocket_id, floor_mm, ok)` and `check_floors(thickness, pockets) -> list[FloorReport]`
- `registration_freedom(clearance) -> float` — per-side play
- `visible_outline(child: Ring, recess: Ring) -> dict` — width and area of exposed support colour

- [ ] **Step 1: failing test** —
  - recess area > child area; minimum boundary separation equals `clearance` within tolerance (round join ⇒ true radial);
  - the input child ring object is unchanged after derivation (no mutation);
  - `z_planes` reproduces 0.8/1.6/2.4 for both depths;
  - `solidify_support` returns an outer with no holes and area equal to the canonical outer;
  - `check_floors` rejects a pocket deeper than the body and accepts a valid one;
  - `visible_outline` width equals `clearance`.
- [ ] **Step 2–4:** red, implement, green.
- [ ] **Step 5:** commit `feat(spike02): add fabrication derivation from canonical geometry`.

---

### Task 4: Label font

**Files:** Create `src/layercake_spike/spike02/font.py`; Test `tests/test_spike02_font.py`

**Interfaces produced:** `text_rings(text: str, x: float, y: float, size: float, stroke: float) -> list[Ring]`

**Design note.** Axis-aligned rectangle strokes only — 7-segment digits plus a small block-letter set (`C D R X . / - =` and what the labels need). Overlapping rectangles are unioned via Clipper2 so glyphs emerge as clean disjoint rings; overlapping bosses would otherwise break manifoldness. Stroke 0.8 mm (two extrusions at 0.4 mm) so it resolves on FDM.

- [ ] **Step 1: failing test** — every character in the label alphabet produces ≥1 ring; rings are disjoint and non-self-intersecting; bounding box scales with `size`; stroke width honoured; unknown character raises.
- [ ] **Step 2–4:** red, implement, green.
- [ ] **Step 5:** commit `feat(spike02): add rectangle stroke font for coupon labels`.

---

### Task 5: Coupon

**Files:** Create `src/layercake_spike/spike02/coupon.py`; Test `tests/test_spike02_coupon.py`

**Interfaces produced:**
- `SHAPES: dict[str, Ring]` — `simple`, `concave` (asymmetric with a reflex notch), `radiused` (generously rounded corners)
- `build_coupon() -> CouponResult` with `.fixture_mesh`, `.children: dict[cell_id, mesh]`, `.cells`, `.floor_reports`, `.derived_feature_report`

**Design note.** Fixture is one `extrude_stepped` body: recess pockets per cell, label bosses beside each cell. Cells laid on a grid with generous separation so recesses never merge (the flat-mosaic land problem does not arise here, and must not be reintroduced). Minimum-feature detection runs **report-only** over derived recesses.

- [ ] **Step 1: failing test** — 8 cells; fixture watertight and Euler 2; every child watertight; each child's thickness `H + D`; every floor > 0 and no through-hole; child fits its recess with the requested clearance; derived-feature report present and non-mutating; the `concave` shape has ≥1 reflex vertex; the `radiused` shape has no vertex sharper than a stated threshold.
- [ ] **Step 2–4:** red, implement, green.
- [ ] **Step 5:** commit `feat(spike02): add labelled clearance/depth test coupon`.

---

### Task 6: Three-level artwork stack

**Files:** Create `src/layercake_spike/spike02/stack.py`; Test `tests/test_spike02_stack.py`

**Design note.** Uses Spike 01's canonical partition directly — `spec.BACKING_RING`, `spec.B_OUTER_RING`, `spec.C_RING` — so the derivation is exercised against real canonical artwork in which C *is* a hole in B. White carries a recess for red; red is **solidified** (canonical hole discarded) and carries a recess for yellow; yellow is a plain prism.

- [ ] **Step 1: failing test** —
  - completed tops resolve to 0.8 / 1.6 / 2.4 for both depths;
  - red's fabrication body has **no through-hole** where yellow sits (Euler number 2) and its material there equals `thickness − D`;
  - yellow never passes laterally through a co-planar exact-size hole: yellow's bottom Z equals red's recess floor, strictly above red's bottom;
  - all three bodies watertight, zero non-manifold edges, zero self-intersections;
  - Spike 01's canonical partition is unchanged after derivation;
  - cumulative registration freedom = sum of per-level clearances.
- [ ] **Step 2–4:** red, implement, green.
- [ ] **Step 5:** commit `feat(spike02): add three-level layered-relief artwork stack`.

---

### Task 7: Arrangements, SVG, reports, CLI

**Files:** Create `arrange.py`, `svgdebug02.py`, `report02.py`, `cli02.py`, `__main__.py`; Test `tests/test_spike02_cli.py`

**Interfaces produced:** `cli02.run(outdir) -> int`

Artefacts to `artefacts/spike02/`: `coupon_fixture.stl`, `coupon_child_<cell>.stl` (×8), `stack_white.stl`, `stack_red.stl`, `stack_yellow.stl`, `assembly_coregistered.stl`, `plate_layout.stl`, `debug-recesses.svg`, `spike02-parameters.json`, `spike02-report.md`.

- [ ] **Step 1: failing test** — every artefact written; every STL watertight on reload; assembly bodies at true Z; plate layout has all bodies at `z=0` and non-overlapping in XY; parameters JSON records layer height, fixture support thickness, per-cell Z planes, registration freedom (per level and cumulative), visible outline width/area, floor thicknesses, derived-feature report and the self-intersection tool caveat; report markdown contains an empty observation table per cell; exit 0.
- [ ] **Step 2–4:** red, implement, green.
- [ ] **Step 5:** commit `feat(spike02): add arrangements, debug SVG, reports and CLI`.

---

### Task 8: ADR 0002, diary, README, PR

- [ ] **Step 1:** `docs/adr/0002-layered-relief-registration-recesses.md` — layered relief as the primary construction; canonical containment ≠ fabrication through-hole, with the opaque-material assumption; clearance is derived fabrication geometry with round-join radial semantics; cleanup scope rule; Z model `H + D`; what it supersedes/clarifies in ADR 0001 decision 8; flat/inlay recorded as a separate future fabrication mode.
- [ ] **Step 2:** update `docs/adr/README.md` index and ADR 0001 with a forward pointer (no rewriting of its history).
- [ ] **Step 3:** `docs/spike-02/report.md` — parameters, artefacts, and Andy's blank observation tables for slicer and physical validation.
- [ ] **Step 4:** diary entry; README section.
- [ ] **Step 5:** full suite, run CLI, commit, push, open PR. **Do not merge.**

---

## Self-Review

**Spec coverage** — clearance matrix (T1, T5), recess depth (T1, T5), three-level stack (T6), shape coverage incl. radiused corner-binding control (T5), labels on the support (T4, T5), supporting-thickness reporting (T3, T5), pipeline rule report-only (T3, T5), all artefacts (T7), all listed software validations (T3, T5, T6, T7), ADR routing (T8), diary (T8).

**Decisions incorporated** — round joins (T3), 0.2 mm layer-height multiples (T1), no chamfers (recorded, not built), report-only min-feature (T3/T5), thicker fixture support (T1), H = 0.8 stack (T6), cumulative registration freedom (T6/T7), terminology (throughout), visible support outline (T3/T7).

**Type consistency** — `Ring = list[tuple[float,float]]` throughout, matching Spike 01. `extrude_stepped` returns `(vertices, faces)` like Spike 01's `extrude`. Meshes are `trimesh.Trimesh` and validated by Spike 01's `validate.validate_mesh` unchanged.

**Risk** — `extrude_stepped` is the one genuinely new mesh construction. Its manifoldness is asserted directly in T2 before anything depends on it.
