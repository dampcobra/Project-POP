# Spike 01 — Canonical Topology & Manifold STL Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that a partitioned artwork can be represented with shared topology, cleaned for manufacturability, extruded into independent registered colour bodies, and exported as valid manifold STL files.

**Architecture:** A canonical `Partition` holds one deduplicated vertex table and one undirected edge table shared by all regions, so an adjacency between two regions is a *single* edge record referencing both — shared boundaries are data, not coincidence. Clipper2 (via `pyclipr`) provides robust integer-backed boolean/offset operations; containment comes from its `PolyTreeD`. Regions are extruded to meshes by a hand-written ring extruder (earcut caps + per-edge wall quads) so manifoldness is a property we control and can prove, then independently audited with trimesh plus our own triangle-triangle self-intersection checker.

**Tech Stack:** Python 3.13, `pyclipr` 0.1.8 (Clipper2 2.0.1), `shapely` 2.1.2 (assertions/measurement only), `mapbox-earcut` 2.0.0 (cap triangulation), `trimesh` 5.1.0 (mesh validation + STL write), `numpy`, `pytest`.

**Spec:** GitHub issue dampcobra/Project-POP#1 — "Spike: Prove canonical topology and manifold STL export". The issue is authoritative; this plan argues from it.

## Global Constraints

- Units are millimetres throughout. All geometry is authored from exact vector coordinates; **no raster input anywhere**.
- Shared origin for every exported body: model origin (0,0,0) = badge bottom-left-front corner. No per-body translation on export.
- Colour A backing: 50.0 x 50.0 mm footprint, Z 0.0 -> 0.8.
- Artwork band: Z 0.8 -> 2.0 (1.2 mm thick). B and C both occupy exactly this band.
- C is a **hole in B** across the artwork band, exported as an independent body. Never stacked on B.
- Minimum manufacturable feature width: **0.4 mm** (0.4 mm nozzle assumption for this spike).
- Undersized-feature policy (Andy, Session 0): **detect, report, remove deterministically** before final geometry generation.
- Geometric epsilon for coincidence/snap: **1e-6 mm**. Clipper2 scale factor **1e6** (integer precision 1e-6 mm).
- Manifold validation tool: **trimesh**, first-line. Self-intersection is NOT covered by trimesh — this must be implemented separately and the limitation documented explicitly, never hidden.
- Colour-count agnostic: no code may hard-code "3 colours" or "4 colours". A, B, C are data.
- Out of scope, do not build: UI, raster import, colour quantisation, typography, variable relief, 3MF, interactive editing.

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, deps, pytest config |
| `src/layercake_spike/spec.py` | The Spike Glyph: exact mm coordinates + band constants. Single source of truth. No logic. |
| `src/layercake_spike/topology.py` | `Vertex`/`Edge`/`Region`/`Partition`. Shared vertex+edge tables, adjacency, containment, gap/overlap validation. |
| `src/layercake_spike/clipper.py` | Thin `pyclipr` adapter: boolean ops, offsets, PolyTreeD -> ring nesting. Keeps Clipper2 replaceable. |
| `src/layercake_spike/cleanup.py` | Min-feature detection (morphological opening) + topology-preserving deterministic removal. |
| `src/layercake_spike/extrude.py` | Rings (outer + holes) + z-range -> watertight triangle mesh. |
| `src/layercake_spike/validate.py` | trimesh manifold audit + own triangle-triangle self-intersection checker. |
| `src/layercake_spike/svgdebug.py` | Debug SVG render of the partition with boundaries visible. |
| `src/layercake_spike/reports.py` | Topology dump, cleanup report, validation report (JSON + Markdown). |
| `src/layercake_spike/cli.py` | `python -m layercake_spike` -> writes every artefact to `artefacts/`. |
| `tests/test_*.py` | One test module per source module. |
| `docs/spike-01/geometry-spec.md` | Human-readable exact geometry specification (required artefact). |
| `docs/spike-01/conclusion.md` | Spike conclusion + architectural implications (required artefact). |
| `docs/diary/2026-09-04-session-0.md` | Development diary for this session. |

---

## The Spike Glyph — exact coordinates (mm)

**Colour A — structural backing.** Rectangle `(0,0) (50,0) (50,50) (0,50)`, Z 0.0 -> 0.8.

**Colour B — foreground region**, Z 0.8 -> 2.0. Outer ring, CCW:

| # | x | y | note |
|---|---|---|---|
| 1 | 8.0 | 8.0 | |
| 2 | 41.0 | 6.0 | |
| 3 | 44.0 | 14.0 | |
| 4 | 44.0 | 17.0 | vertical run — exact tab anchor |
| 5 | 42.0 | 30.0 | |
| 6 | 38.0 | 40.0 | |
| 7 | 30.0 | 40.0 | **reflex** — notch shoulder |
| 8 | 25.0 | 26.0 | notch apex (V bottom) |
| 9 | 20.0 | 40.0 | **reflex** — notch shoulder |
| 10 | 12.0 | 38.0 | |

**Colour C — enclosed island.** Square `(14,12) (22,12) (22,20) (14,20)`, Z 0.8 -> 2.0. Appears as a hole ring in B and as an independent body.

**Undersized tab.** Axis-aligned rectangle `(43.5, 15.425) (47.0, 15.425) (47.0, 15.575) (43.5, 15.575)`. Width 0.150 mm; protrudes 3.000 mm beyond B's x=44.0 edge; overlaps 0.5 mm into B for a robust union. Unioned into B *before* cleanup so cleanup has something to find.

---

### Task 1: Scaffold + geometry spec

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/layercake_spike/__init__.py`, `src/layercake_spike/spec.py`
- Test: `tests/test_spec.py`

**Interfaces:**
- Produces: `spec.BACKING_RING: list[tuple[float,float]]`, `spec.B_OUTER_RING`, `spec.C_RING`, `spec.TAB_RING`, `spec.Z_BACKING=(0.0,0.8)`, `spec.Z_ARTWORK=(0.8,2.0)`, `spec.MIN_FEATURE_MM=0.4`, `spec.EPS=1e-6`, `spec.CLIPPER_SCALE=1e6`

- [ ] **Step 1: Write the failing test** — `tests/test_spec.py` asserts the spec's *claimed* properties really hold, so the coordinates cannot drift silently.

```python
import math
from shapely.geometry import Polygon
from layercake_spike import spec

def _signed_area(ring):
    return 0.5 * sum(x0 * y1 - x1 * y0
                     for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]))

def test_rings_are_ccw_and_simple():
    for name, ring in [("B", spec.B_OUTER_RING), ("C", spec.C_RING),
                       ("A", spec.BACKING_RING), ("tab", spec.TAB_RING)]:
        assert _signed_area(ring) > 0, f"{name} must be counter-clockwise"
        assert Polygon(ring).is_valid, f"{name} must be a simple polygon"

def test_b_has_exactly_two_reflex_vertices():
    ring = spec.B_OUTER_RING
    reflex = []
    for i, cur in enumerate(ring):
        prv, nxt = ring[i - 1], ring[(i + 1) % len(ring)]
        cross = ((cur[0] - prv[0]) * (nxt[1] - cur[1])
                 - (cur[1] - prv[1]) * (nxt[0] - cur[0]))
        if cross < 0:                      # CCW ring => negative cross is reflex
            reflex.append(cur)
    assert reflex == [(30.0, 40.0), (20.0, 40.0)], reflex

def test_c_is_fully_enclosed_with_about_4mm_of_b_around_it():
    b, c = Polygon(spec.B_OUTER_RING), Polygon(spec.C_RING)
    assert b.contains(c)
    clearance = c.exterior.distance(b.exterior)
    assert 3.5 <= clearance <= 6.0, clearance

def test_tab_is_undersized_and_3mm_long():
    xs = [p[0] for p in spec.TAB_RING]
    ys = [p[1] for p in spec.TAB_RING]
    assert math.isclose(max(ys) - min(ys), 0.15, abs_tol=1e-9)   # width
    assert math.isclose(max(xs) - 44.0, 3.0, abs_tol=1e-9)       # protrusion
    assert max(ys) - min(ys) < spec.MIN_FEATURE_MM               # deliberately unmanufacturable

def test_bands_are_flat_mosaic_not_stacked():
    assert spec.Z_BACKING == (0.0, 0.8)
    assert spec.Z_ARTWORK == (0.8, 2.0)     # B and C share this band; C never sits on B
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest tests/test_spec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'layercake_spike'`

- [ ] **Step 3: Write `spec.py`** with the coordinate table above, plus `pyproject.toml` (setuptools, `src` layout, pytest `testpaths=tests`) and a `.gitignore` covering `.venv/`, `__pycache__/`, `*.pyc`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pip install -e . && .venv/Scripts/python.exe -m pytest tests/test_spec.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore src tests
git commit -m "feat(spike): add Spike Glyph exact geometry specification"
```

---

### Task 2: Clipper2 adapter

**Files:**
- Create: `src/layercake_spike/clipper.py`
- Test: `tests/test_clipper.py`

**Interfaces:**
- Consumes: `spec.CLIPPER_SCALE`
- Produces:
  - `Ring = list[tuple[float, float]]`
  - `boolean_op(subject: list[Ring], clip: list[Ring], op: str) -> list[Ring]` where `op` in `{"union","difference","intersection"}`
  - `boolean_tree(subject, clip, op) -> list[NestedRing]` with `NestedRing = namedtuple("NestedRing", "ring holes")`
  - `offset(rings: list[Ring], delta: float) -> list[Ring]` (miter join, miter limit 8.0)
  - `area(ring: Ring) -> float` (signed)

- [ ] **Step 1: Write the failing test**

```python
import math
from layercake_spike import clipper

SQ10 = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
SQ_MID = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]

def test_difference_produces_outer_and_hole():
    out = clipper.boolean_op([SQ10], [SQ_MID], "difference")
    assert len(out) == 2
    assert math.isclose(sum(abs(clipper.area(r)) for r in out), 100.0 - 4.0, abs_tol=1e-6)

def test_boolean_tree_reports_containment():
    tree = clipper.boolean_tree([SQ10], [SQ_MID], "difference")
    assert len(tree) == 1
    assert len(tree[0].holes) == 1
    assert math.isclose(abs(clipper.area(tree[0].holes[0])), 4.0, abs_tol=1e-6)

def test_negative_offset_erases_a_thin_sliver():
    sliver = [(0.0, 0.0), (5.0, 0.0), (5.0, 0.15), (0.0, 0.15)]
    assert clipper.offset([sliver], -0.2) == []

def test_offset_roundtrip_preserves_a_fat_shape_within_tolerance():
    shrunk = clipper.offset([SQ10], -0.2)
    regrown = clipper.offset(shrunk, +0.2)
    assert math.isclose(abs(clipper.area(regrown[0])), 100.0, abs_tol=1e-3)
```

- [ ] **Step 2: Run to verify it fails.** Run: `.venv/Scripts/python.exe -m pytest tests/test_clipper.py -v`. Expected: FAIL — no module `clipper`.

- [ ] **Step 3: Implement `clipper.py`.** Wrap `pyclipr.Clipper` with `scaleFactor = int(spec.CLIPPER_SCALE)`, `FillRule.NonZero`, `pyclipr.Subject`/`pyclipr.Clip` path types. `boolean_tree` uses `execute2()` and walks `PolyTreeD` children to build `NestedRing`. `offset` uses `pyclipr.ClipperOffset` with `JoinType.Miter`, `EndType.Polygon`, `miterLimit=8.0`. `area` is the shoelace formula.

- [ ] **Step 4: Run to verify pass.** Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/clipper.py tests/test_clipper.py
git commit -m "feat(spike): add Clipper2 adapter for booleans, offsets and containment"
```

---

### Task 3: Canonical topology with first-class shared boundaries

**Files:**
- Create: `src/layercake_spike/topology.py`
- Test: `tests/test_topology.py`

**Interfaces:**
- Consumes: `clipper.boolean_tree`, `clipper.area`, `spec.EPS`
- Produces:
  - `VertexTable` with `.add(x, y) -> int` (epsilon-snapping dedup), `.coords -> list[tuple[float,float]]`
  - `Edge(a: int, b: int)` — key is `(min,max)` so an adjacency is one record
  - `Region(rid: str, colour: str, z: tuple[float,float], outer: list[int], holes: list[list[int]])`
  - `Partition.build(regions_geom: dict[str, dict]) -> Partition`
  - `Partition.shared_edges() -> dict[Edge, list[str]]` — edges with >1 incident region
  - `Partition.containment() -> dict[str, list[str]]` — region -> regions it encloses
  - `Partition.validate_band(z: tuple[float,float], universe: Ring) -> BandReport` with `.overlap_area`, `.gap_area`, `.ok`
  - `Partition.to_dump() -> dict` (JSON-safe topology dump)

- [ ] **Step 1: Write the failing test.** The central assertion is that B's hole ring and C's outer ring are the *same vertex indices* — that is what makes the shared boundary data rather than coincidence.

```python
import math
from layercake_spike import spec, topology

def build():
    return topology.Partition.build({
        "A": dict(colour="A", z=spec.Z_BACKING, outer=spec.BACKING_RING, holes=[]),
        "B": dict(colour="B", z=spec.Z_ARTWORK, outer=spec.B_OUTER_RING, holes=[spec.C_RING]),
        "C": dict(colour="C", z=spec.Z_ARTWORK, outer=spec.C_RING, holes=[]),
    })

def test_vertex_table_deduplicates_coincident_points():
    vt = topology.VertexTable(eps=spec.EPS)
    assert vt.add(1.0, 2.0) == vt.add(1.0 + 1e-9, 2.0 - 1e-9)
    assert vt.add(1.0, 2.5) != vt.add(1.0, 2.0)

def test_b_hole_and_c_outer_are_the_same_shared_vertices():
    p = build()
    b_hole = set(p.regions["B"].holes[0])
    c_outer = set(p.regions["C"].outer)
    assert b_hole == c_outer, "shared boundary must be one set of vertices, not two copies"

def test_shared_edges_are_single_records_naming_both_regions():
    p = build()
    shared = p.shared_edges()
    assert len(shared) == 4, "the C square contributes exactly 4 shared edges"
    for edge, regions in shared.items():
        assert sorted(regions) == ["B", "C"]

def test_containment_reports_c_inside_b():
    p = build()
    assert p.containment()["B"] == ["C"]
    assert p.containment()["C"] == []

def test_artwork_band_has_no_overlap_and_no_unintended_gap():
    p = build()
    r = p.validate_band(spec.Z_ARTWORK, universe=spec.B_OUTER_RING)
    assert r.overlap_area < spec.EPS, r.overlap_area
    assert r.gap_area < spec.EPS, r.gap_area
    assert r.ok
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL — no module `topology`.

- [ ] **Step 3: Implement `topology.py`.** `VertexTable` keys a dict on `(round(x/eps), round(y/eps))`. `Partition.build` interns every ring through the shared table, so a hole ring authored from the same coordinates as another region's outer ring resolves to identical indices — the shared boundary falls out of interning, by construction. `shared_edges` counts incident regions per undirected edge key. `containment` uses `clipper.boolean_tree`. `validate_band` computes pairwise intersection area (overlap) and `universe - union(regions)` area (gap) via Clipper2.

- [ ] **Step 4: Run to verify pass.** Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/topology.py tests/test_topology.py
git commit -m "feat(spike): add canonical partition with first-class shared edges"
```

---

### Task 4: Manufacturability cleanup

**Files:**
- Create: `src/layercake_spike/cleanup.py`
- Test: `tests/test_cleanup.py`

**Interfaces:**
- Consumes: `clipper.offset`, `clipper.boolean_op`, `clipper.area`, `spec.MIN_FEATURE_MM`
- Produces:
  - `Finding(region: str, kind: str, detail: str, area_mm2: float, action: str)`
  - `clean_region(outer: Ring, holes: list[Ring], min_feature: float, region_id: str) -> tuple[Ring, list[Ring], list[Finding]]`
  - `CleanupReport` with `.findings`, `.min_feature`, `.policy`, `.to_markdown()`, `.to_dict()`

**Design note for the implementer — read this before coding.** Detection is a morphological opening: `opened = offset(offset(rings, -min_feature/2), +min_feature/2)`. Anything in `original - opened` is thinner than `min_feature`. The naive move is to return `opened` as the cleaned geometry — **do not**. Opening also nibbles the shared boundary with C, which silently destroys the shared-edge invariant Task 3 just established. Instead: open the **outer** ring only, then rebuild holes by `difference(opened_outer, [C_ring])` so C's boundary is reinstated exactly. The test below locks this in.

- [ ] **Step 1: Write the failing test**

```python
import math
from layercake_spike import spec, clipper, cleanup

def b_with_tab():
    return clipper.boolean_op([spec.B_OUTER_RING], [spec.TAB_RING], "union")[0]

def test_tab_is_detected_with_the_threshold_recorded():
    _, _, findings = cleanup.clean_region(b_with_tab(), [spec.C_RING],
                                          spec.MIN_FEATURE_MM, "B")
    tabs = [f for f in findings if f.kind == "thin_feature"]
    assert len(tabs) == 1
    assert tabs[0].action == "removed"
    assert math.isclose(tabs[0].area_mm2, 0.15 * 3.0, rel_tol=0.05), tabs[0].area_mm2

def test_tab_does_not_survive_into_cleaned_geometry():
    outer, _, _ = cleanup.clean_region(b_with_tab(), [spec.C_RING],
                                       spec.MIN_FEATURE_MM, "B")
    assert max(x for x, _ in outer) <= 44.0 + 1e-6, "tab must be gone"

def test_cleanup_preserves_the_shared_boundary_with_c_exactly():
    _, holes, _ = cleanup.clean_region(b_with_tab(), [spec.C_RING],
                                       spec.MIN_FEATURE_MM, "B")
    assert len(holes) == 1
    assert sorted(round(v, 9) for pt in holes[0] for v in pt) == \
           sorted(round(v, 9) for pt in spec.C_RING for v in pt)

def test_cleanup_preserves_the_reflex_notch_within_tolerance():
    outer, _, _ = cleanup.clean_region(b_with_tab(), [spec.C_RING],
                                       spec.MIN_FEATURE_MM, "B")
    apex = min(outer, key=lambda p: abs(p[0] - 25.0) + abs(p[1] - 26.0))
    assert math.dist(apex, (25.0, 26.0)) < 0.05, apex

def test_cleanup_is_deterministic():
    a = cleanup.clean_region(b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B")
    b = cleanup.clean_region(b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B")
    assert a[0] == b[0] and a[1] == b[1]
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL — no module `cleanup`.

- [ ] **Step 3: Implement `cleanup.py`** per the design note.

- [ ] **Step 4: Run to verify pass.** Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/cleanup.py tests/test_cleanup.py
git commit -m "feat(spike): detect and deterministically remove sub-nozzle features"
```

---

### Task 5: Ring extrusion to watertight mesh

**Files:**
- Create: `src/layercake_spike/extrude.py`
- Test: `tests/test_extrude.py`

**Interfaces:**
- Consumes: `mapbox_earcut`, `numpy`
- Produces: `extrude(outer: Ring, holes: list[Ring], z0: float, z1: float) -> tuple[np.ndarray, np.ndarray]` returning `(vertices Nx3, faces Mx3)`

**Design note.** Build bottom cap at `z0` and top cap at `z1` from one earcut triangulation, reversing winding on the bottom. Walls: for each ring (outer CCW, holes CW), each consecutive vertex pair emits two triangles. Every wall edge is then used exactly twice with opposite orientation, which is what makes the result watertight. Do not deduplicate vertices between caps and walls — reuse the same index set for both so no seam appears.

- [ ] **Step 1: Write the failing test**

```python
import math
import numpy as np
import trimesh
from layercake_spike import spec, extrude

def test_simple_box_is_watertight_with_correct_volume():
    sq = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    v, f = extrude.extrude(sq, [], 0.0, 3.0)
    m = trimesh.Trimesh(vertices=v, faces=f, process=False)
    assert m.is_watertight and m.is_winding_consistent
    assert math.isclose(m.volume, 12.0, rel_tol=1e-9)

def test_ring_with_hole_is_watertight_and_volume_excludes_the_hole():
    outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    hole = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]
    v, f = extrude.extrude(outer, [hole], 0.0, 1.0)
    m = trimesh.Trimesh(vertices=v, faces=f, process=False)
    assert m.is_watertight
    assert math.isclose(m.volume, 96.0, rel_tol=1e-9)

def test_concave_notch_survives_extrusion():
    v, f = extrude.extrude(spec.B_OUTER_RING, [], *spec.Z_ARTWORK)
    m = trimesh.Trimesh(vertices=v, faces=f, process=False)
    assert m.is_watertight and m.volume > 0
    assert np.isclose(v[:, 2].min(), 0.8) and np.isclose(v[:, 2].max(), 2.0)
    assert any(np.allclose(p[:2], (25.0, 26.0)) for p in v), "notch apex must survive"

def test_euler_number_is_two_for_a_solid_without_through_holes():
    sq = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    v, f = extrude.extrude(sq, [], 0.0, 1.0)
    assert trimesh.Trimesh(vertices=v, faces=f, process=False).euler_number == 2
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL — no module `extrude`.

- [ ] **Step 3: Implement `extrude.py`** per the design note.

- [ ] **Step 4: Run to verify pass.** Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/extrude.py tests/test_extrude.py
git commit -m "feat(spike): add watertight ring extruder with hole support"
```

---

### Task 6: Manifold validation, including the trimesh self-intersection gap

**Files:**
- Create: `src/layercake_spike/validate.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `trimesh`, `numpy`
- Produces:
  - `self_intersections(mesh) -> list[tuple[int,int]]` — our own checker; broad phase on AABB overlap, narrow phase exact triangle-triangle, skipping pairs sharing a vertex index
  - `MeshReport(body: str, watertight: bool, winding_consistent: bool, is_volume: bool, euler_number: int, non_manifold_edges: int, self_intersections: int, volume: float, bounds: list, tool_notes: list[str])`
  - `validate_mesh(name: str, mesh) -> MeshReport`
  - `.ok` property — true only when watertight, winding-consistent, zero non-manifold edges, zero self-intersections

**Design note — this is the honesty requirement.** `trimesh` exposes `is_watertight`, `is_winding_consistent`, `is_volume` and `euler_number`, but has **no** self-intersection test. `MeshReport.tool_notes` must record that in every report we emit, and `self_intersections` must be our own implementation, not a trimesh call dressed up as one. Non-manifold edge count = edges whose incident-face count != 2.

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
import trimesh
from layercake_spike import validate

def test_clean_box_validates_ok():
    r = validate.validate_mesh("box", trimesh.creation.box(extents=[1, 1, 1]))
    assert r.watertight and r.non_manifold_edges == 0 and r.self_intersections == 0
    assert r.ok

def test_open_mesh_is_flagged_not_ok():
    m = trimesh.creation.box(extents=[1, 1, 1])
    torn = trimesh.Trimesh(m.vertices, m.faces[:-2], process=False)
    r = validate.validate_mesh("torn", torn)
    assert not r.watertight and not r.ok

def test_self_intersection_is_detected_where_trimesh_reports_nothing():
    # two crossing triangles: watertight checks say nothing, our checker must fire
    v = np.array([[0., 0., 0.], [4., 0., 0.], [0., 4., 0.],
                  [1., 1., -2.], [1., 1., 2.], [3., 1., 0.]])
    m = trimesh.Trimesh(vertices=v, faces=np.array([[0, 1, 2], [3, 4, 5]]), process=False)
    assert len(validate.self_intersections(m)) == 1

def test_adjacent_triangles_are_not_false_positives():
    m = trimesh.creation.box(extents=[1, 1, 1])
    assert validate.self_intersections(m) == []

def test_report_always_discloses_the_trimesh_limitation():
    r = validate.validate_mesh("box", trimesh.creation.box(extents=[1, 1, 1]))
    assert any("self-intersection" in n.lower() and "trimesh" in n.lower()
               for n in r.tool_notes)
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL — no module `validate`.

- [ ] **Step 3: Implement `validate.py`.** Narrow phase: separating-axis test on the candidate axes for two triangles, treating coplanar-touching as non-intersecting.

- [ ] **Step 4: Run to verify pass.** Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/validate.py tests/test_validate.py
git commit -m "feat(spike): add manifold validation with own self-intersection checker"
```

---

### Task 7: Debug SVG render

**Files:**
- Create: `src/layercake_spike/svgdebug.py`
- Test: `tests/test_svgdebug.py`

**Interfaces:**
- Consumes: `topology.Partition`
- Produces: `render(partition, path, *, highlight_shared=True) -> str` — writes SVG, returns the markup

Requirements: y-axis flipped to screen space, per-region fill with distinct hues, region boundaries stroked, **shared edges stroked in a contrasting colour and heavier weight** so gaps/overlaps are inspectable, vertices drawn as dots, 10 mm grid, legend.

- [ ] **Step 1: Write the failing test**

```python
from layercake_spike import spec, topology, svgdebug

def test_svg_contains_every_region_and_marks_shared_edges(tmp_path):
    p = topology.Partition.build({
        "A": dict(colour="A", z=spec.Z_BACKING, outer=spec.BACKING_RING, holes=[]),
        "B": dict(colour="B", z=spec.Z_ARTWORK, outer=spec.B_OUTER_RING, holes=[spec.C_RING]),
        "C": dict(colour="C", z=spec.Z_ARTWORK, outer=spec.C_RING, holes=[]),
    })
    out = tmp_path / "debug.svg"
    svg = svgdebug.render(p, out)
    assert out.exists()
    assert svg.startswith("<?xml")
    for rid in ("A", "B", "C"):
        assert f'data-region="{rid}"' in svg
    assert 'class="shared-edge"' in svg
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL — no module `svgdebug`.
- [ ] **Step 3: Implement `svgdebug.py`.**
- [ ] **Step 4: Run to verify pass.** Expected: 1 passed.
- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/svgdebug.py tests/test_svgdebug.py
git commit -m "feat(spike): add debug SVG render with shared-edge highlighting"
```

---

### Task 8: Reports, CLI and artefact generation

**Files:**
- Create: `src/layercake_spike/reports.py`, `src/layercake_spike/cli.py`, `src/layercake_spike/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `cli.run(outdir: Path) -> int` — builds the partition, cleans, extrudes, validates, writes artefacts; returns non-zero if any pass/fail criterion fails.

Artefacts written to `artefacts/`: `A_backing.stl`, `B_foreground.stl`, `C_island.stl`, `topology-dump.json`, `debug.svg`, `cleanup-report.md`, `validation-report.md`, `spike-summary.json`.

- [ ] **Step 1: Write the failing test**

```python
import json
import trimesh
from layercake_spike import cli

def test_full_run_emits_every_required_artefact(tmp_path):
    assert cli.run(tmp_path) == 0
    for name in ["A_backing.stl", "B_foreground.stl", "C_island.stl",
                 "topology-dump.json", "debug.svg",
                 "cleanup-report.md", "validation-report.md", "spike-summary.json"]:
        assert (tmp_path / name).exists(), name

def test_every_exported_body_is_manifold(tmp_path):
    cli.run(tmp_path)
    for name in ["A_backing.stl", "B_foreground.stl", "C_island.stl"]:
        m = trimesh.load(tmp_path / name)
        assert m.is_watertight and m.is_winding_consistent, name

def test_bodies_are_co_registered_on_a_shared_origin(tmp_path):
    cli.run(tmp_path)
    a = trimesh.load(tmp_path / "A_backing.stl")
    b = trimesh.load(tmp_path / "B_foreground.stl")
    c = trimesh.load(tmp_path / "C_island.stl")
    assert abs(a.bounds[0][2] - 0.0) < 1e-6 and abs(a.bounds[1][2] - 0.8) < 1e-6
    for m in (b, c):
        assert abs(m.bounds[0][2] - 0.8) < 1e-6 and abs(m.bounds[1][2] - 2.0) < 1e-6
    assert c.bounds[0][0] >= b.bounds[0][0] and c.bounds[1][0] <= b.bounds[1][0]

def test_b_and_c_do_not_overlap_in_the_artwork_band(tmp_path):
    cli.run(tmp_path)
    s = json.loads((tmp_path / "spike-summary.json").read_text())
    assert s["band_validation"]["artwork"]["overlap_area"] < 1e-6
    assert s["band_validation"]["artwork"]["gap_area"] < 1e-6

def test_summary_records_the_removed_tab_and_the_validation_caveat(tmp_path):
    cli.run(tmp_path)
    s = json.loads((tmp_path / "spike-summary.json").read_text())
    assert s["cleanup"]["findings"][0]["action"] == "removed"
    assert s["cleanup"]["min_feature_mm"] == 0.4
    assert any("trimesh" in n.lower() for n in s["validation"]["tool_notes"])
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL — no module `cli`.
- [ ] **Step 3: Implement `reports.py`, `cli.py`, `__main__.py`.**
- [ ] **Step 4: Run the full suite.** Run `.venv/Scripts/python.exe -m pytest -v` then `.venv/Scripts/python.exe -m layercake_spike`. Expected: all pass, artefacts written, exit 0.
- [ ] **Step 5: Commit**

```bash
git add src/layercake_spike/reports.py src/layercake_spike/cli.py src/layercake_spike/__main__.py tests/test_cli.py artefacts
git commit -m "feat(spike): add reports, CLI and full artefact generation"
```

---

### Task 9: Documentation, diary, PR

**Files:**
- Create: `docs/spike-01/geometry-spec.md`, `docs/spike-01/conclusion.md`, `docs/diary/2026-09-04-session-0.md`
- Modify: `README.md`

- [ ] **Step 1:** Write `geometry-spec.md` — the coordinate tables above, band definitions, tab definition, tolerances, and the shared-origin statement.
- [ ] **Step 2:** Write `conclusion.md` — verdict on whether shared-vertex/shared-edge + Clipper2 is sufficient, every architectural implication found (especially cleanup-vs-shared-boundary), self-intersection tooling limits, and what remains for Andy (Bambu Studio slice evidence, physical print).
- [ ] **Step 3:** Write the Session 0 diary entry.
- [ ] **Step 4:** Update `README.md` with a short "Spike 01" section and how to run it.
- [ ] **Step 5: Commit and open the PR**

```bash
git add docs README.md
git commit -m "docs(spike): add geometry spec, spike conclusion and session diary"
git push -u origin spike/1-canonical-topology-stl
gh pr create --base main --title "Spike 01: canonical topology and manifold STL export (#1)" --body-file docs/spike-01/pr-body.md
```

**Do not merge the PR.** Andy merges after Bambu Studio and physical validation.

---

## Self-Review

**Spec coverage** — every Issue #1 required artefact maps to a task: exact coordinates (T1, T9), topology dump (T3, T8), debug SVG (T7), cleanup report (T4, T8), separate co-registered STLs (T5, T8), per-body manifold report (T6, T8), conclusion (T9). Slicer import evidence and the physical print are Andy's, flagged in T9 and the PR body. Every pass/fail criterion has a test: shared boundaries (T3), concave geometry (T5), island/containment (T3, T8), minimum feature (T4), manifold validity (T6, T8), registration (T8).

**Placeholder scan** — no TBDs; every code step carries real code.

**Type consistency** — `Ring = list[tuple[float,float]]` is used identically across `clipper`, `cleanup`, `extrude`, `svgdebug`. `clean_region` returns `(outer, holes, findings)` in T4 and is consumed that way in T8. `validate_mesh` returns `MeshReport` in T6 and is consumed that way in T8.

**Known risk carried into execution** — Task 4's miter-join opening may perturb the notch apex; the test bounds that at 0.05 mm. If it exceeds tolerance, that is a genuine spike finding and belongs in `conclusion.md`, not a silent tolerance loosening.
