# Spike 01 — Conclusion

**Issue:** [dampcobra/Project-POP#1](https://github.com/dampcobra/Project-POP/issues/1)
**Date:** 2026-09-04
**Status: PASS — complete.** Software, slicer and physical validation all done.

---

## Verdict

**Spike 01 passes. The proposed topology approach is viable. Do not escalate to a
full DCEL yet.**

Geometry, slicing and printing all succeeded. Physical assembly did not: the
island would not fit its zero-clearance opening. That is a **fabrication-geometry
finding, not a topology failure** — and it is the single most valuable thing the
spike produced, because it could only have been found by printing.

A shared-vertex / shared-edge boundary representation backed by Clipper2 handled
every case Issue #1 put to it — shared boundaries, reflex geometry, containment,
island export, sub-nozzle feature removal and watertight mesh generation — with
no case where the simpler model ran out of expressive power.

All five software pass criteria pass:

| Criterion | Result | Evidence |
|---|---|---|
| Shared boundaries | PASS | Overlap 0.0 mm², gap 0.0 mm², tolerance 1e-6 mm |
| Concave geometry | PASS | Both reflex vertices survive bit-exact; meshes watertight |
| Island / containment | PASS | C is a hole in B, exported independently, 100 % contact with backing |
| Minimum feature handling | PASS | 0.15 mm tab detected (0.450 mm²) and removed before mesh generation |
| Manifold validity | PASS | 3/3 bodies watertight, 0 non-manifold edges, 0 self-intersections |
| Slicer validation | PASS | All 3 bodies imported at correct shared position; no repair warnings; sliced successfully |
| Physical validation | PASS with finding | Printed cleanly; assembly revealed the clearance requirement below |

Reproduce with `python -m layercake_spike`; artefacts land in `artefacts/`.

---

## Physical validation

Performed by Andy on 2026-09-04 using Bambu Studio as the validation slicer.
Bambu Studio remains a validation tool, not an architectural dependency.

### Slicer

- All three STL bodies imported successfully.
- **No geometry-repair warnings** — the manifold guarantees held up in a real
  slicer, not just under trimesh.
- Bodies registered correctly at the shared origin, confirming that exporting
  without per-body translation is sufficient for co-registration.
- Slicing completed successfully.

### Print

- The print completed successfully.
- The backing (A) and the main foreground (B) printed cleanly, including the
  concave V-notch and the boundary left where the undersized tab was removed.
- **The island (C) would not physically fit into its zero-clearance opening.**

### What that proves

Mathematically coincident boundaries are correct as *canonical artwork geometry*
and insufficient as *fabrication geometry*. Two surfaces at identical coordinates
have no room for extrusion width, thermal expansion, elephant's foot or ordinary
print tolerance, so the parts interfere on assembly.

This vindicates the architecture rather than contradicting it. ADR 0001
decision 6 already held that clearance belongs in export as derived fabrication
geometry and never in the canonical model. What changed is that clearance moved
from *hypothetical* to *required*, with a measured reason.

### Evidence

| File | What it shows |
|---|---|
| [`physical-print.jpg`](physical-print.jpg) | The printed badge. White backing, red foreground with the V-notch and a clean edge where the tab was removed, and the yellow island sitting proud in its opening rather than seated. |
| [`recess-concept.jpg`](recess-concept.jpg) | Andy's cross-section sketch of the proposed construction: continuous white backing, red artwork above it, yellow island located in a shallow recess and standing proud of the red. |

---

## What the spike actually proved

### Shared boundaries fall out of construction, not detection

The load-bearing decision is that every region's rings are interned through a
single `VertexTable`. Because interning is shared, B's hole ring and C's outer
ring resolve to *the same vertex indices*. The adjacency is then a fact in the
model rather than something to rediscover by comparing floats later.

`EdgeTable` keys undirected edges on the sorted index pair, so the B/C boundary
is 4 edge records each naming both regions — not 8 records that happen to
coincide. This satisfies the issue's "shared-edge metadata must be first-class"
requirement and is the natural hinge point for a later migration to a richer
topology model.

Numerically: the artwork band shows **0.0 mm² overlap and 0.0 mm² gap** against
a 1e-6 mm tolerance, measured with Clipper2 booleans rather than by eye, as the
issue requires.

### Clipper2 was the right backend

Integer-backed arithmetic on a 1e-6 mm grid meant no epsilon-chasing anywhere in
the boolean or containment code. Containment came free from `PolyTreeD` nesting
rather than from point-in-polygon heuristics. `pyclipr` 0.1.8 wraps Clipper2
2.0.1 and installed cleanly on Windows/Python 3.13.

### Manifoldness is cheaper to construct than to repair

The extruder builds bottom and top caps from one earcut triangulation over a
shared index set, then generates walls from the same indices. Every wall edge is
consequently traversed exactly twice in opposite directions, so watertightness is
structural rather than something a repair pass has to rescue. All three bodies
came out watertight on the first run, and B's Euler number of 0 correctly
reflects its single through-hole.

---

## Architectural implications discovered

These are the findings that should shape Layercake's architecture. They are the
real output of the spike.

### 1. Manufacturability cleanup must be topology-aware — highest-impact finding

The obvious implementation of minimum-feature cleanup is a morphological opening
(shrink by half the feature width, grow back) applied to a region's geometry.
Applied naively **it silently destroys shared boundaries.**

Opening operates on all of a region's rings, so it erodes the hole where C sits
by up to 0.2 mm while C's own outer ring stays put. The result still renders
fine, still slices, and still passes every per-body manifold check — but B and C
no longer meet, and the failure is invisible in exactly the artefacts you would
use to look for it.

The pipeline therefore opens each region's **outer ring only**, then re-cuts holes
from the authoritative geometry, reinstating shared boundaries bit-exact.
`test_cleanup_preserves_the_shared_boundary_with_c_exactly` locks this in.

**Implication for Layercake:** cleanup cannot be a standalone geometric filter
sitting between vectorisation and meshing. It needs to know which boundaries are
shared and treat them as immutable. Any future cleanup operation — smoothing,
simplification, small-hole removal, corner rounding — carries the same hazard and
needs the same treatment.

### 2. Cleaned geometry must *replace* authored geometry as canonical

Cleanup perturbs B's outer boundary by up to **3e-6 mm** (three steps of the
Clipper2 integer grid). Tiny, and both reflex vertices plus the vertex count came
through untouched — but 3e-6 mm exceeds the 1e-6 mm vertex-snapping epsilon.

So authored and cleaned coordinates must never be interned into the same vertex
table without an explicit snap step, or the same corner would resolve to two
vertex ids and a shared boundary would silently split. The pipeline avoids this
by rebuilding the partition wholly from cleaned geometry.

**Implication:** the canonical model needs a defined lifecycle — authored →
cleaned → canonical — with one generation of geometry live at a time. Mixing
generations is a class of bug the type system will not catch.

### 3. Winding discipline needs one owner

Rings are authored counter-clockwise for readability, but Clipper2's NonZero fill
rule requires holes wound opposite to their outer ring. Getting this wrong does
not error — it silently *adds* the island's area instead of subtracting it. It
cost a real debugging cycle during this spike (B's area came out 1030 mm² instead
of 966 mm², and the band validation reported a 64 mm² overlap).

Normalisation now lives in one place (`Partition.solid_rings`) so no caller has to
remember. **Implication:** treat winding as an invariant enforced at a boundary,
not a convention documented in a comment.

### 4. `SLIVER_AREA_EPS_MM2` — areas need an area-dimensioned tolerance

Filtering cleanup slivers with the coordinate epsilon (1e-6 mm) against an area
produced a false positive: 8e-6 mm² of offset round-trip noise at a shallow-angle
vertex reported as a manufacturability defect. A separate area threshold
(1e-3 mm²) fixed it.

**Implication:** a tolerance policy needs distinct values per dimension —
lengths, areas, angles — rather than one global epsilon reused wherever a
comparison is needed.

### 5. Full-depth island insertion is rejected — REVISED after physical testing

**Original hypothesis (now disproved):** C rests on the backing over 100 % of its
64 mm² footprint, held by inter-layer adhesion with no mechanical interlock. The
open question was whether adhesion alone would be secure enough.

**What the print showed:** the question never arose, because the island could not
be inserted at all. Modelling an island as a full-depth plug occupying a
zero-clearance hole through the entire artwork band does not survive contact with
a real printer.

Two separate problems were bundled together in that model:

1. **No manufacturing clearance** — see finding 6.
2. **Full-depth press fit** — even with clearance, a plug spanning the full
   1.2 mm artwork band asks the island to be a friction-fit mechanical joint,
   which is not what the artwork needs. It only needs to be *positioned*.

**Direction agreed with Andy (to be investigated next, deliberately not
implemented in this spike):**

1. A continuous structural backing remains underneath the entire artwork.
2. Main colour bodies sit on that backing.
3. Where an enclosed island needs positioning, the surrounding colour body
   carries a **shallow registration recess**, not a through-hole.
4. The recess is larger than the inserted piece by a **configurable
   manufacturing clearance**.
5. The recess is an assembly and positioning guide, **not a friction fit**.
6. Final pieces are glued to the backing.
7. Canonical artwork geometry stays exact; registration clearance is **derived
   fabrication geometry** and must not alter canonical topology.

This reframes the island from a structural part to a located inlay, and moves the
mechanical job from press fit to adhesive.

**What the construction sketch settles** (`recess-concept.jpg`, a cross-section
through the badge):

- The backing is continuous and full width. The main colour body sits on it,
  also full width — **no through-hole**.
- The recess is a shallow pocket in the *top* of the main colour body, so its
  floor is main-body material. The island therefore rests on **B, not on the
  backing** — a change from the spike, where C sat directly on A.
- **The island stands proud of the surrounding colour.** It is not flush: the
  sketch shows the island's top surface above the main body's top surface, with
  only its lower portion seated in the pocket. Island thickness is therefore
  *greater* than recess depth, and the artwork gains visible relief at island
  boundaries.

**Open geometry questions still to settle before implementation:**

- **Recess depth as a parameter.** Depth is now independent of island thickness
  rather than derived from it, so it needs its own rule — deep enough to locate
  the piece reliably, shallow enough to leave a sound floor.
- **Where clearance is applied.** Growing the recess, shrinking the island, or
  splitting the allowance between them are three different fabrication
  strategies with different visible gap widths on the finished piece.
- **Does the recess floor need its own minimum-thickness rule?** It becomes a
  thin horizontal web of B, subject to the same manufacturability limits as any
  other feature — and unlike a vertical wall, it is a printed floor spanning a
  cavity.
- **What bonds to what.** Andy's model says pieces are glued to the backing, but
  geometrically the island bonds to the *recess floor*, which is main-body
  material. Worth confirming that is intended.
- **Does the raised island change the colour model?** Standing proud means the
  artwork is no longer strictly flat mosaic within a single band. This is still
  fixed-height-per-region, not variable relief, but the "one artwork band"
  assumption in the current spec would need revisiting.

### 6. Exact coincidence is canonical; clearance is derived — CONFIRMED by physical testing

**Original position:** B and C meet at mathematically identical coordinates. Any
boundary allowance belongs in export as a per-slicer profile, never in the
canonical model, because putting it in the model would break the shared-boundary
invariant the spike exists to establish.

**The print confirmed both halves of this.** Zero clearance is correct for
canonical geometry — the shared boundary validated at 0.0 mm² gap and overlap,
and the bodies sliced without a single repair warning. Zero clearance is also
unusable for physical assembly, as the island demonstrated.

The architectural split therefore holds and is now evidence-backed:

- **Canonical model:** exact coincident boundaries. Unchanged. This is what makes
  shared boundaries checkable and keeps Layercake slicer-agnostic.
- **Fabrication geometry:** derived at export by applying a configurable
  clearance. Never fed back into the canonical model.

The clearance value is a manufacturing parameter — a function of nozzle, material,
printer and tolerance appetite — which is precisely why it belongs in an export
profile rather than the artwork. Its value is not yet established; the spike only
proves that zero is wrong.

### 7. Issue #1's reflex-vertex requirement was geometrically unsatisfiable as written

A pure V notch has one reflex vertex, not two; both shoulders are necessarily
convex. Resolved by truncating the apex with a 2 mm flat. Recorded here because
the resolution changed the test geometry, and the spec (`geometry-spec.md`)
carries the reasoning.

---

## Validation robustness — stated limitations

These are real gaps. None blocks the verdict; all should be understood before
this code informs production decisions.

### trimesh does not detect self-intersections

trimesh is the selected validation tool and covers watertightness, winding
consistency, the volume test and the Euler number well. It has **no**
self-intersection test — `trimesh.repair` handles holes, winding and normals,
not faces passing through one another.

Issue #1 requires zero self-intersections as a pass criterion, so reporting that
box ticked on trimesh's say-so would have been reporting a check never run.
The spike therefore implements its own triangle-triangle checker (AABB broad
phase, separating-axis narrow phase). Every report records which tool produced
which result.

**Limitations of that checker:**

- **Not independently cross-checked.** Its "0 self-intersections" result has
  been validated against unit tests including a deliberately crossing pair, but
  not against an independent validator such as MeshLab, admesh or Netfabb. A
  second opinion would materially raise confidence.
- **O(n²) broad phase.** Fine at spike scale (60 faces); not a production
  algorithm. Needs a spatial index before it meets real meshes.
- **Touching is not intersecting.** Coplanar contact and edge grazing are
  treated as non-intersecting — right for co-registered bodies whose walls meet
  exactly, but it means a genuinely degenerate touch will not be flagged.

### Validation is per-body; inter-body interference is checked in 2D

Whether two separate bodies interpenetrate is not a property of either mesh.
It is checked instead by the 2D band validation (`Partition.validate_band`),
which is exact for the flat-mosaic MVP case where all geometry in a band is a
straight prism. **That equivalence stops holding the moment variable relief or
non-prismatic geometry arrives**, and inter-body interference would then need a
genuine 3D check.

### The 0.4 mm minimum feature width is an assumption, not a measurement

Taken from the nozzle diameter per the issue. The print did not exercise it: the
tab was removed before export, so the threshold's correctness was never put to a
physical test. Whether 0.4 mm is right, and whether removal beats enlargement,
remains provisional.

---

## Open questions for Andy and Elara

1. **Clearance value and strategy.** How much clearance, and applied where —
   grow the recess, shrink the island, or split the allowance? This is now a
   live question rather than a hypothetical one.
2. **Recess geometry.** The four questions listed under finding 5: recess depth
   versus island thickness, which surface is the datum, where clearance is
   applied, and whether the recess floor needs its own minimum-thickness rule.
3. **Minimum-feature policy.** Removal is implemented per Andy's Session 0
   decision, and the print did not test the threshold. Is silent removal right
   for production, or should it be surfaced to the user with a choice
   (remove / enlarge / keep and warn)? A decorative tab and a structural one
   want different answers.
4. **Independent mesh validation.** Worth adding a second validator to
   cross-check self-intersection results before this becomes production
   architecture?

---

## Verified by physical validation

Both outstanding items are now complete.

- **Bambu Studio import/slice evidence** — done. All three bodies imported at the
  correct shared position, no geometry-repair warnings, sliced successfully.
- **Physical print and observations** — done. Backing and foreground printed
  cleanly; the island would not fit its zero-clearance opening.

## Still not verified

- **Self-intersection results have not been independently corroborated.** The
  slicer reporting no repair warnings is meaningful supporting evidence — a real
  production slicer found nothing wrong with the meshes — but Bambu Studio is not
  a mesh validator and this is not a substitute for cross-checking against
  MeshLab, admesh or Netfabb.
- **The 0.4 mm minimum feature threshold** was not physically exercised.
- **The recess construction model is unbuilt and untested.** It is a direction
  agreed from a sketch, not a validated design.

---

## Recommendation

Proceed to application architecture on this topology model. Carry findings 1–3
into the design as invariants rather than conventions.

**Next piece of work, separate from this spike:** a fabrication-geometry stage
that derives registration recesses and clearance from the canonical model at
export time. The canonical topology proved out here is unaffected by it — that is
the point of keeping clearance out of the model — so this is additive work rather
than a rework. It is deliberately **not** implemented in PR #2.

Revisit DCEL only if one of these arrives:

- interactive region editing, where incremental local updates beat rebuilding
  the partition;
- islands nested inside islands, or more than two regions meeting at a vertex,
  where ordered edge incidence around a vertex starts to matter;
- non-prismatic geometry, which breaks the 2D-validation-implies-3D-correctness
  equivalence this spike relies on.

None of these is on the MVP path.
