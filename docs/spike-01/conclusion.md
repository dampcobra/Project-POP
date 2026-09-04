# Spike 01 — Conclusion

**Issue:** [dampcobra/Project-POP#1](https://github.com/dampcobra/Project-POP/issues/1)
**Date:** 2026-09-04
**Status:** Software portion complete and passing. Slicer and physical validation outstanding (Andy).

---

## Verdict

**The proposed topology approach is viable. Do not escalate to a full DCEL yet.**

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

Reproduce with `python -m layercake_spike`; artefacts land in `artefacts/`.

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

### 5. Island anchoring is adhesion only

C rests on the backing over 100 % of its 64 mm² footprint, which satisfies the
issue's containment criterion. But there is **no mechanical interlock** — no
dovetail, lip or keying. The island is held by inter-layer adhesion to A alone.

That is very likely fine at 8 × 8 mm. It is much less obviously fine for a small
island, a tall artwork band, or a material pairing with poor interlayer bonding.
**This is the item most worth watching in physical validation.**

### 6. No clearance or interference allowance is applied

B and C meet at mathematically identical coordinates — zero clearance, zero
interference. This is the correct default for multi-material printing, where the
slicer is expected to handle coincident surfaces, and it keeps Layercake
slicer-agnostic.

Whether it is correct *in practice* is a Bambu Studio question, and it is the
second thing worth watching physically. If a boundary allowance turns out to be
needed, it belongs in export as a per-slicer profile, **not** in the canonical
model — putting it in the model would break the shared-boundary invariant this
spike exists to establish.

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

Taken from the nozzle diameter per the issue. Whether 0.4 mm is the right
threshold — and whether removal is the right action versus enlargement — is
exactly what physical validation should inform.

---

## Open questions for Andy and Elara

1. **Minimum-feature policy.** Removal is implemented per Andy's Session 0
   decision. Is silent removal right for production, or should it be surfaced to
   the user with a choice (remove / enlarge / keep and warn)? A tab that is
   decorative and a tab that is structural want different answers.
2. **Boundary allowance.** Should export gain an optional per-slicer clearance
   profile, or stay at exact coincidence? Depends on the Bambu Studio result.
3. **Island anchoring.** Is adhesion-only anchoring acceptable, or should
   Layercake generate mechanical keying for small islands? Depends on the print.
4. **Independent mesh validation.** Worth adding a second validator to
   cross-check self-intersection results before this becomes production
   architecture?

---

## Not verified in this spike

- **Bambu Studio import/slice evidence** — requires Andy's validation slicer.
  The STLs are in `artefacts/`; the check is that all three import at the correct
  shared position and slice with no geometry-repair warnings.
- **Physical print photograph and observations** — requires a physical print.
  Watch particularly: boundary quality between B and C, whether the island is
  mechanically secure, and that the removed tab leaves a sensible edge.

Until both are done, the verdict above covers the geometry pipeline only.

---

## Recommendation

Proceed to application architecture on this topology model. Carry findings 1–3
into the design as invariants rather than conventions. Revisit DCEL only if one
of these arrives:

- interactive region editing, where incremental local updates beat rebuilding
  the partition;
- islands nested inside islands, or more than two regions meeting at a vertex,
  where ordered edge incidence around a vertex starts to matter;
- non-prismatic geometry, which breaks the 2D-validation-implies-3D-correctness
  equivalence this spike relies on.

None of these is on the MVP path.
