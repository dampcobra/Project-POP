# ADR 0001 — Canonical geometry architecture following Spike 01

- **Status:** Accepted — decisions 1–7 confirmed by physical validation;
  decision 8 revised
- **Date:** 2026-09-04
- **Session:** 0 — Product Definition & MVP
- **Deciders:** Andy (Product Owner), Elara/ChatGPT (PM & Architect), Claude (Developer)
- **Supersedes:** none
- **Related:** [Issue #1](https://github.com/dampcobra/Project-POP/issues/1) ·
  PR #2 · [`docs/spike-01/conclusion.md`](../spike-01/conclusion.md) ·
  [`docs/spike-01/geometry-spec.md`](../spike-01/geometry-spec.md)

### Revision history

| Date | Change |
|---|---|
| 2026-09-04 | Accepted on software evidence. Decisions 7–8 provisional pending physical validation. |
| 2026-09-04 | Physical validation complete. **Spike 01 marked PASS.** Decisions 1–7 confirmed; decision 6 strengthened with print evidence; **decision 8 revised** — full-depth zero-clearance island insertion rejected by physical testing. |
| 2026-09-04 | Decision 8 restated to Product Owner intent: finished artwork is **flat mosaic with flush top surfaces**; registration recesses generalise to any supporting body, not islands only. Corrects an earlier reading of the freehand sketch that implied proud islands. **No variable relief is adopted.** |

Revision is permitted here because decision 8 was recorded as explicitly
provisional pending this evidence. Decisions 1–7 are unchanged in substance;
where they gained supporting evidence, that is noted in place.

## Context

Before committing to application architecture or UI, Spike 01 tested the
highest-risk assumption in Project POP: that a partitioned artwork can be
represented with shared topology, cleaned for manufacturability, extruded into
independent registered colour bodies, and exported as valid manifold STL.

The spike built the "Spike Glyph" — a 50 × 50 mm badge with a structural
backing, an irregular foreground carrying a concave V-notch, an enclosed island
occupying a literal hole in the foreground, and a deliberately unmanufacturable
0.15 mm tab. All five software pass criteria passed across 55 tests.

**Spike 01 subsequently passed slicer and physical validation.** All three bodies
imported into Bambu Studio at the correct shared position with no geometry-repair
warnings and sliced successfully; the print completed with backing and foreground
clean. The island would not fit its zero-clearance opening — a fabrication-geometry
finding, not a topology failure, and the evidence behind decisions 6 and 8 below.

This ADR records the architectural decisions that follow. Full evidence and
reasoning are in the spike conclusion; this document is the durable decision
record.

---

## Decisions

### 1. Shared-vertex / shared-edge topology is sufficient for MVP. No DCEL yet.

A canonical partition in which every region's rings are interned through a
single vertex table, with undirected edges keyed on the sorted index pair, is
adequate for the MVP geometry model. A full doubly-connected edge list is not
justified at this stage.

Because interning is shared, two regions meeting along a boundary resolve to
*the same vertex indices*. Adjacency becomes a fact recorded in the model rather
than a float comparison performed downstream — which is what makes "shared
boundaries are data, not coincidence" a checkable property. Shared-edge metadata
is first-class, so migration to a richer model remains open.

**Revisit when any of these arrives:**

- interactive region editing, where incremental local updates beat rebuilding
  the partition;
- islands nested inside islands, or more than two regions meeting at a vertex,
  where ordered edge incidence around a vertex starts to matter;
- non-prismatic geometry (see decision 6's consequence about 2D validation).

None is on the MVP path.

### 2. Clipper2 via `pyclipr` is the geometry/boolean library for the spike.

Clipper2 2.0.1, accessed through `pyclipr` 0.1.8, provides booleans, offsets and
containment. Its integer-backed arithmetic on a 1e-6 mm grid removed
epsilon-chasing from the boolean and containment code entirely, and containment
came directly from `PolyTreeD` nesting rather than point-in-polygon heuristics.

Note for anyone reading the original issue: there is **no `clipper2` package on
PyPI**, and `pyclipper` is Clipper *1*, not Clipper2.

**Scope of this decision:** it commits the spike, not the product. The library is
held behind a thin adapter (`clipper.py`) precisely so it stays replaceable. This
choice is tied to the Python spike stack and does not bind the final Layercake
application stack.

### 3. Manufacturability cleanup must be topology-aware.

Cleanup may not be implemented as a standalone geometric filter between
vectorisation and meshing. It must know which boundaries are shared and treat
them as immutable.

Minimum-feature cleanup is a morphological opening. Applied naively to all of a
region's rings it **silently destroys shared boundaries** — eroding one region's
copy of a shared boundary by up to half the feature width while its neighbour's
copy stays put. The result still renders correctly, still slices, and still
passes every per-body manifold check. The failure is invisible in exactly the
artefacts one would use to look for it.

The implemented policy opens each region's **outer ring only**, then re-cuts
holes from the authoritative region geometry, reinstating shared boundaries
bit-exact.

**This constraint generalises.** Any future geometry-modifying operation —
smoothing, simplification, small-hole removal, corner rounding — carries the same
hazard and needs the same treatment.

### 4. Cleaned geometry becomes canonical after manufacturability processing.

The canonical model has a defined lifecycle: **authored → cleaned → canonical**,
with exactly one generation of geometry live at a time. Authored and cleaned
coordinates must never be interned into the same vertex table without an explicit
snap step.

Cleanup perturbs boundaries by up to 3e-6 mm — three steps of the Clipper2
integer grid. Small, and in the spike both reflex vertices and the vertex count
came through untouched, but it **exceeds the 1e-6 mm vertex-snapping epsilon**.
Mixing generations would therefore resolve one corner to two vertex ids and split
a shared boundary silently. This is a class of bug no type system will catch, so
it is recorded as an architectural rule rather than left to care.

### 5. Winding ownership must be centralised.

Ring orientation is an invariant enforced at a single boundary, not a convention
documented in comments. Rings are authored counter-clockwise for readability;
normalisation to the orientation each consumer requires happens in one place.

Clipper2's NonZero fill rule requires holes wound opposite to their outer ring.
Getting this wrong does not raise an error — it silently *adds* the hole's area
instead of subtracting it. In the spike this produced a foreground area of
1030 mm² instead of 966 mm² and a spurious 64 mm² overlap, with no exception and
no visible defect, and cost a real debugging cycle.

**Corollary:** tolerances need dimensions. A length epsilon must not be used to
filter an area. Filtering cleanup slivers with the 1e-6 mm coordinate epsilon
against an area reported 8e-6 mm² of offset round-trip noise as a real
manufacturability defect. A tolerance policy needs distinct values per dimension
— lengths, areas, angles — not one global epsilon.

### 6. Exact coincident boundaries remain canonical. Clearance belongs in export profiles.

*Confirmed by physical validation.*

Adjacent regions meet at mathematically identical coordinates: zero clearance,
zero interference. This is the canonical representation and it does not change.

Where physical validation shows a boundary allowance is needed, it is applied at
**export time as derived fabrication geometry** — never in the canonical model.
Baking a clearance into the model would break the shared-boundary invariant that
decision 1 exists to establish, and would couple the canonical geometry to a
particular slicer's behaviour, violating Layercake's slicer-agnostic principle.

**Physical evidence (2026-09-04).** The print settled both halves of this.
Zero clearance is *correct canonically* — the shared boundary validated at
0.0 mm² gap and overlap, and the bodies sliced with no repair warnings. Zero
clearance is *unusable for assembly* — the island would not fit its opening,
because coincident surfaces leave no room for extrusion width, elephant's foot or
ordinary print tolerance.

So clearance has moved from hypothetical to **required**, with a measured reason,
while its architectural home is unchanged. Its value is a manufacturing parameter
— a function of nozzle, material, printer and tolerance appetite — which is
exactly why it belongs in an export profile rather than the artwork. The value
itself is not yet established; the spike proves only that zero is wrong.

This is the decision the physical test was most likely to overturn, and it held.

**Consequence to watch:** inter-body interference is currently checked in 2D via
band gap/overlap validation. That is exact for the flat-mosaic MVP, where every
body is a straight prism — but the equivalence **stops holding the moment
variable relief or non-prismatic geometry arrives**, at which point a genuine 3D
interference check becomes necessary.

### 7. STL bodies are separate and co-registered. Material assignment is downstream.

*Confirmed by slicer validation.*

MVP 3D export is separate, co-registered STL bodies sharing one origin, with no
per-body translation applied — co-registration is a property of the pipeline
rather than a post-export correction.

**Slicer evidence (2026-09-04).** All three bodies imported into Bambu Studio at
the correct shared position with **no geometry-repair warnings**, and sliced
successfully. Exporting without per-body translation is therefore sufficient for
co-registration in a real slicer, and the manifold guarantees held outside our own
validation code.

Layercake owns manufacturable geometry. Filament and material assignment belong
to the downstream slicer. Bambu Studio is Andy's validation slicer, **not an
architectural dependency**, and no Bambu/AMS-specific project format is
generated.

**Validation-tooling consequence, recorded so it is not forgotten:** trimesh is
the selected manifold validator and covers watertightness, winding consistency
and Euler number honestly. It has **no self-intersection test**. Because Issue #1
makes zero self-intersections a pass criterion, the spike implements its own
triangle-triangle checker rather than report a check it never ran. That checker
is **not cross-checked against an independent validator**, is O(n²), and treats
touching as non-intersecting. Adding a second validator before this informs
production architecture is an open question.

### 8. Full-depth zero-clearance insertion is REJECTED. Shallow registration recesses to be investigated. — REVISED 2026-09-04

**Previously (superseded):** an enclosed island exported as an independent body
rests on the backing over 100 % of its footprint, held by inter-layer adhesion
with no mechanical interlock. The open question was whether adhesion alone would
be secure enough.

**Rejected by physical testing.** The question never arose, because the island
could not be inserted at all. Modelling an island as a full-depth plug occupying a
zero-clearance hole through the entire artwork band does not survive contact with
a real printer.

The rejected model bundled two separate problems:

1. **No manufacturing clearance** — addressed architecturally by decision 6.
2. **Full-depth press fit** — even with clearance, a plug spanning the full
   artwork band asks the island to be a friction-fit mechanical joint. The
   artwork only needs the island to be *positioned*.

#### Replacement concept to investigate next — shallow registration recesses

Product Owner intent following physical validation. **Recorded as intent, not as
an accepted design — it is unbuilt and untested, and is deliberately not
implemented in PR #2.**

1. The structural backing remains continuous. Registration recesses must never
   become **full-depth holes**.
2. A recess is slightly larger in XY than the piece it locates, by a
   **configurable fabrication clearance**.
3. **Canonical artwork boundaries remain mathematically exact.** Recess clearance
   belongs only to derived fabrication geometry.
4. Piece thickness and seating depth are related: an inserted piece must include
   the material that sits inside its recess, so its visible top surface finishes
   at the intended common artwork Z height.
5. The finished MVP artwork remains a **flat mosaic**. This does **not**
   introduce variable relief.
6. Recess depth, XY clearance and minimum supporting thickness are fabrication
   parameters still requiring physical experimentation. Any figures quoted here
   illustrate the concept rather than establish production defaults.
7. **Not to be implemented in PR #2.** Investigate in a subsequent spike.

Principles 3 and 5 are load-bearing and are decision 6 restated for this case.
The recess model changes what is *derived at export*; it must not change what the
canonical model holds, and the finished artwork stays a flat mosaic of exact
boundaries.

This reframes an island from a structural part to a located inlay, moving the
mechanical job from press fit to adhesive.

#### The finished surface stays flat mosaic

Product Owner clarification, authoritative over any reading of the freehand
sketch:

**The MVP finished artwork remains a flat mosaic.** Every artwork colour's
visible top surface finishes at the same nominal Z height. Registration recesses
do **not** introduce variable relief, and no proud or raised island is adopted.

A recess is a seating feature *below* the visible surface, not a change *to* the
visible surface. A piece is made thicker by exactly the depth it seats, so what
shows above the surrounding artwork is unchanged:

> **piece thickness = visible artwork height + its seating depth**

Illustrative stack-up — concept, **not** production defaults (see principle 6):

| Element | Value |
|---|---|
| Structural backing | 0.8 mm |
| Visible artwork height | 0.8 mm |
| Registration recess depth | 0.2 mm |
| Inserted piece thickness | 1.0 mm (0.2 mm seated + 0.8 mm visible) |
| Finished top surface | flush with the surrounding artwork |

#### Recesses generalise — not an island-only mechanism

A shallow registration recess is a property of **any supporting body locating a
separately assembled piece above it**, not a special case for enclosed islands:

- the structural backing may carry a recess locating the main artwork body;
- the main artwork body may carry a recess locating an enclosed island.

Their purpose is assembly registration and glue-up — not friction fitting, not
mechanical interlocking.

#### Open questions for the next spike

- **Where is clearance applied?** Growing the recess, shrinking the piece, or
  splitting the allowance are three strategies with different visible gap widths
  on the finished piece.
- **Minimum supporting thickness.** A recess floor is a printed horizontal web
  spanning a cavity — a different manufacturability case from a vertical wall.
  Principle 1 requires the floor to exist; principle 6 leaves its thickness open.
- **Principle 4 through a chain of seatings.** Thickness is measured from the
  common artwork top Z down to that piece's own recess floor. A piece seated in a
  body that is itself seated has a higher recess floor and is correspondingly
  thinner than the single-seating illustration. Worth stating explicitly so the
  illustrative 1.0 mm is not carried across to the nested case by assumption.
- **What bonds to what?** Geometrically a located piece's bond face is its recess
  floor in the supporting body.

#### Minimum-feature policy — still provisional

Unchanged and still open. Current policy is *detect, report, remove
deterministically* before mesh generation, at a 0.4 mm threshold taken from
nozzle diameter as an assumption, not a measurement.

**The print did not test it.** The tab was removed before export, so the
threshold's correctness was never physically exercised. Whether removal is right
— against enlargement, or surfacing a choice to the user — remains unresolved; a
decorative tab and a structural one may warrant different answers.

This part of decision 8 still awaits evidence and should be revised when it
arrives.

---

## Consequences

**Positive**

- Shared boundaries are established by construction, so no gap/overlap
  reconciliation pass is needed between colour regions.
- Manifoldness is structural rather than repaired: caps and walls are generated
  from one shared index set, so every wall edge is traversed exactly twice.
- The geometry backend sits behind an adapter and stays replaceable.
- Layercake remains slicer-agnostic; nothing in the canonical model knows about
  Bambu Studio.
- Pass/fail criteria are machine-checkable, not matters of visual judgement.

**Negative / accepted costs**

- Cleanup is more complex than a geometric filter, and every future
  geometry-modifying operation inherits that complexity (decision 3).
- The authored → cleaned → canonical lifecycle must be respected by discipline;
  violations fail silently (decision 4).
- Self-intersection validation rests on project-written code that has not been
  independently corroborated (decision 7).
- The 2D-validation-implies-3D-correctness equivalence is a standing constraint
  on the geometry model, not a permanent property (decision 6).

**Deferred**

- DCEL migration (decision 1).
- Final application stack — Python was chosen for spike velocity only.
- **Export clearance profiles — no longer optional.** Physical validation showed
  zero-clearance assembly does not work, so a fabrication-geometry stage is now
  required work rather than a contingency (decisions 6 and 8).
- **Registration recess model** — Product Owner intent, unbuilt and untested,
  generalised across supporting relationships rather than island-only
  (decision 8).
- Resolution of the minimum-feature policy, which the print did not exercise
  (decision 8).

Because clearance and recesses are derived at export and never enter the
canonical model, this is **additive work rather than rework**. The topology
proved out by the spike is unaffected — which is the practical payoff of
decision 6.

---

## Status of supporting evidence

| Evidence | State |
|---|---|
| Software pass criteria (5/5), 55 tests | Complete — PR #2 |
| Manifold validation, 3 bodies | Complete — `artefacts/validation-report.md` |
| Numeric gap/overlap validation | Complete — 0.0 mm² each, tolerance 1e-6 mm |
| Bambu Studio import/slice evidence | **Complete** — 3/3 imported at shared position, no repair warnings, sliced successfully |
| Physical print and observations | **Complete** — printed cleanly; island would not fit zero-clearance opening |

**Spike 01: PASS.**

Decisions 1–7 stand on completed software, slicer and physical evidence.
Decision 8 has been revised: full-depth zero-clearance island insertion is
rejected on physical evidence, and the registration-recess direction that
replaces it is recorded as intent to investigate, not as an accepted design.
The minimum-feature policy within decision 8 remains provisional and untested.

Photographic evidence is committed alongside the spike documentation:
[`physical-print.jpg`](../spike-01/physical-print.jpg) (the printed badge, island
resting unseated on its opening) and
[`recess-concept.jpg`](../spike-01/recess-concept.jpg) (freehand cross-section of
the proposed construction).

The freehand sketch is indicative only. Where its proportions and the Product
Owner clarification differ, **the clarification governs**. A revised annotated
cross-section is expected and is **not yet in the repository**; add it as
`docs/spike-01/recess-concept-annotated.jpg` and reference it here when
available.
