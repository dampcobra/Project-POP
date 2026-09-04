Implements #1.

**Spike 01: PASS.** Software, slicer and physical validation all complete.

**Do not merge without Andy's say-so.**

## Verdict

**The proposed topology approach is viable. Do not escalate to a full DCEL yet.**

A shared-vertex / shared-edge model backed by Clipper2 handled every case the
issue put to it, with no point where the simpler model ran out of expressive
power. All software pass criteria pass (55 tests green), the bodies sliced
without repair warnings, and the print completed.

Physical assembly did not: **the island would not fit its zero-clearance
opening.** That is a fabrication-geometry finding, not a topology failure, and
it is the most valuable thing the spike produced — it could only have been found
by printing. Details below.

| Criterion | Result | Evidence |
|---|---|---|
| Shared boundaries | PASS | Overlap 0.0 mm², gap 0.0 mm², tolerance 1e-6 mm, measured numerically |
| Concave geometry | PASS | Both reflex vertices survive bit-exact; meshes watertight |
| Island / containment | PASS (topology) | C is a hole in B, exported independently. Topologically correct; the *physical* full-depth insertion model it implied was rejected on print — see below |
| Minimum feature handling | PASS | 0.15 mm tab detected (0.450 mm²) and removed before mesh generation |
| Manifold validity | PASS | 3/3 bodies watertight, 0 non-manifold edges, 0 self-intersections |
| Slicer validation | PASS | 3/3 imported at correct shared position; no repair warnings; sliced |
| Physical validation | PASS with finding | Printed cleanly; assembly revealed the clearance requirement |

Run `python -m layercake_spike`; artefacts land in `artefacts/` (committed).

## Physical validation outcome

**Slicer.** All three bodies imported into Bambu Studio at the correct shared
position with **no geometry-repair warnings**, and sliced successfully. The
manifold guarantees held outside our own validation code, and exporting with no
per-body translation proved sufficient for co-registration.

**Print.** Completed. Backing and foreground printed cleanly, including the
concave notch and the edge left where the undersized tab was removed.

**Finding.** The island would not fit its zero-clearance opening. Coincident
surfaces leave no room for extrusion width, elephant's foot or ordinary print
tolerance.

This **vindicated ADR 0001 decision 6 rather than contradicting it**: clearance
was already assigned to export as derived fabrication geometry and never to the
canonical model. It moved from hypothetical to required, with a measured reason.
That was the decision most likely to be overturned by printing, and it held —
so this is additive work, not rework.

**Rejected:** full-depth zero-clearance island insertion. It bundled two
problems — no clearance, and asking the island to be a friction-fit joint when it
only needs positioning.

**Direction agreed, deliberately NOT implemented in this PR:** continuous backing
under the whole artwork, main colour bodies on the backing, a **shallow
registration recess** in the surrounding body rather than a through-hole, sized
larger than the insert by a configurable clearance, acting as a positioning guide
rather than a friction fit, with pieces glued. Canonical artwork geometry stays
exact; clearance is derived at export. Recorded as intent in ADR 0001 decision 8,
with the open geometry questions it raises.

## What is here

One commit per pipeline stage, each with its tests:

`spec` (exact mm coordinates) → `clipper` (Clipper2 adapter) → `topology`
(canonical partition) → `cleanup` (manufacturability) → `extrude` (watertight
meshing) → `validate` (manifold audit) → `svgdebug` → `reports`/`cli` → docs.

The core idea: every region's rings are interned through **one shared vertex
table**, so B's hole ring and C's outer ring resolve to the *same vertex
indices*. The adjacency is a fact in the model rather than a float comparison
performed later. Shared edges are single records naming both incident regions.

## Limitations and unresolved questions

Flagging these prominently as requested.

### Validation robustness

- **trimesh has no self-intersection test.** It covers watertightness, winding
  and Euler number well, but `trimesh.repair` handles holes and normals, not
  faces passing through one another. Since #1 makes zero self-intersections a
  pass criterion, ticking that box on trimesh's say-so would have meant
  reporting a check we never ran. There is therefore a **project-written**
  triangle-triangle checker (AABB broad phase + separating-axis narrow phase),
  and every report records which tool produced which result.
- **That checker is not independently cross-checked.** It passes unit tests
  including a deliberately crossing pair, but has not been validated against
  MeshLab, admesh or Netfabb. Its "0 self-intersections" result is the weakest
  claim in this PR. **Open question: add a second validator before this informs
  production architecture?**
- **O(n²) broad phase.** Fine at 60 faces; not a production algorithm.
- **Touching is not intersecting.** Right for co-registered bodies whose walls
  meet exactly, but a genuinely degenerate touch would not be flagged.
- **Inter-body interference is checked in 2D, not 3D.** Exact for the flat-mosaic
  MVP where every body is a straight prism — but that equivalence **breaks the
  moment variable relief arrives**.
- **The 0.4 mm minimum feature width is still an assumption.** The print did
  **not** exercise it — the tab was removed before export, so the threshold was
  never physically tested. Whether 0.4 mm is right, and whether removal beats
  enlargement, remains open.
- **Slicer success is not mesh validation.** Bambu Studio reporting no repair
  warnings is meaningful supporting evidence, but it is not a substitute for
  cross-checking self-intersection results against MeshLab, admesh or Netfabb.

### Architectural findings that should shape Layercake

1. **Cleanup must be topology-aware.** A morphological opening applied naively
   **silently destroys shared boundaries** — it erodes B's copy of the C boundary
   while C's stays put. The geometry still renders, still slices, and still passes
   every per-body manifold check. The failure is invisible in exactly the
   artefacts you would use to look for it. Cleanup now opens outer rings only and
   re-cuts holes from authoritative geometry.
2. **Cleaned geometry must replace authored geometry as canonical.** Cleanup
   perturbs the outer boundary by up to 3e-6 mm — three Clipper2 grid steps, but
   above the 1e-6 mm snapping epsilon. Interning both generations into one vertex
   table would split a shared boundary silently. The canonical model needs a
   defined authored → cleaned → canonical lifecycle.
3. **Winding needs one owner.** Clipper2's NonZero rule requires holes wound
   opposite to their outer ring; getting it wrong silently *adds* area instead of
   subtracting it (cost a real debugging cycle — B measured 1030 mm² instead of
   966). Now enforced in one place.
4. **Tolerances need dimensions.** Filtering slivers by area using the *length*
   epsilon produced a false positive. Areas need an area-dimensioned threshold.
5. **Full-depth island insertion is rejected** — by physical testing, not by
   analysis. Superseded by the registration-recess direction above.
6. **Exact coincidence is canonical; clearance is derived at export.** Confirmed
   by the print. B and C meet at identical coordinates in the model, and the
   fabrication allowance belongs in an export profile, never in the canonical
   geometry.

### Spec issue found

#1 asks for "a V-shaped concave notch with **two** reflex vertices". A pure V
yields exactly **one** — the apex; both shoulders are necessarily convex, and
making one reflex would require the material to overhang the notch. Caught by the
first test written, before implementation. Resolved by truncating the apex with a
2 mm flat, which reads as a V and gives two reflex vertices. Reasoning is in
`docs/spike-01/geometry-spec.md`.

### Library note

There is **no `clipper2` package on PyPI**. `pyclipper` is Clipper *1*. This uses
`pyclipr` 0.1.8, which wraps Clipper2 2.0.1.

## Completed — Andy

- [x] Bambu Studio import/slice evidence — 3/3 imported at the correct shared
      position, no geometry-repair warnings, sliced successfully.
- [x] Physical print and observations — printed cleanly; island would not fit its
      zero-clearance opening.

Photographs are held by Andy and are not committed to this repository; the
physical-validation write-up is from Andy's description of them.

## Open questions for Andy / Elara

1. **Clearance value and strategy** — how much, and applied where (grow the
   recess, shrink the island, or split the allowance)? Now live rather than
   hypothetical.
2. **Recess geometry** — depth vs island thickness, which surface is the datum,
   and whether the recess floor needs its own minimum-thickness rule. Note a
   shallow recess means the island rests on the surrounding body, not the
   backing — a change from this spike.
3. **Minimum-feature policy** — the print did not test the 0.4 mm threshold. Is
   silent removal right, or should the user get a choice?
4. Add an independent mesh validator to cross-check self-intersection results?

Full write-up: `docs/spike-01/conclusion.md`. Decision record:
`docs/adr/0001-spike-01-canonical-geometry-architecture.md`. Session notes:
`docs/diary/2026-09-04-session-0.md`.

Closes #1.
