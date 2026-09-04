Implements the software portion of #1.

**Do not merge yet** — Bambu Studio slice evidence and the physical print are
outstanding and are Andy's to produce.

## Verdict

**The proposed topology approach is viable. Do not escalate to a full DCEL yet.**

A shared-vertex / shared-edge model backed by Clipper2 handled every case the
issue put to it, with no point where the simpler model ran out of expressive
power. All five software pass criteria pass; 55 tests green.

| Criterion | Result | Evidence |
|---|---|---|
| Shared boundaries | PASS | Overlap 0.0 mm², gap 0.0 mm², tolerance 1e-6 mm, measured numerically |
| Concave geometry | PASS | Both reflex vertices survive bit-exact; meshes watertight |
| Island / containment | PASS | C is a hole in B, exported independently, 100 % contact with backing |
| Minimum feature handling | PASS | 0.15 mm tab detected (0.450 mm²) and removed before mesh generation |
| Manifold validity | PASS | 3/3 bodies watertight, 0 non-manifold edges, 0 self-intersections |

Run `python -m layercake_spike`; artefacts land in `artefacts/` (committed).

## What is here

Nine commits, one per pipeline stage, each with its tests:

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
- **The 0.4 mm minimum feature width is an assumption**, taken from the nozzle
  diameter. Physical validation should inform whether it is right, and whether
  removal beats enlargement.

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
5. **Island anchoring is adhesion only** — no mechanical interlock. Probably fine
   at 8 × 8 mm; the thing most worth watching in the physical print.
6. **No clearance/interference allowance is applied.** B and C meet at identical
   coordinates. If an allowance turns out to be needed, it belongs in export as a
   per-slicer profile, never in the canonical model.

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

## Outstanding — Andy

- [ ] Bambu Studio import/slice evidence: all three STLs import at the correct
      shared position and slice without geometry-repair warnings.
- [ ] Physical print photograph and observations. Watch: boundary quality between
      B and C, whether the island is mechanically secure, and that the removed tab
      leaves a sensible edge.

## Open questions for Andy / Elara

1. Is silent removal the right production policy for undersized features, or
   should the user get a choice (remove / enlarge / keep and warn)?
2. Should export gain an optional per-slicer clearance profile, or stay at exact
   coincidence?
3. Is adhesion-only island anchoring acceptable, or should Layercake generate
   mechanical keying for small islands?
4. Add an independent mesh validator to cross-check self-intersection results?

Full write-up: `docs/spike-01/conclusion.md`. Session notes:
`docs/diary/2026-09-04-session-0.md`.

Closes #1 once slicer and physical validation are complete.
