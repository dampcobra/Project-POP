# ADR 0002 — Layered-relief construction and registration recesses

- **Status:** Accepted for the software model; the fabrication parameters it
  carries remain provisional pending Spike 02 physical validation
- **Date:** 2026-09-04
- **Session:** 0 — Product Definition & MVP
- **Deciders:** Andy (Product Owner), Elara/ChatGPT (PM & Architect), Claude (Developer)
- **Supersedes:** the construction detail of [ADR 0001](0001-spike-01-canonical-geometry-architecture.md)
  decision 8. ADR 0001 decisions 1–7 stand unchanged.
- **Related:** [Issue #3](https://github.com/dampcobra/Project-POP/issues/3) ·
  [Issue #1](https://github.com/dampcobra/Project-POP/issues/1) ·
  `docs/spike-02/notes.md`

## Context

Spike 01 physically rejected full-depth zero-clearance island insertion: the
island could not pass laterally through a co-planar exact-size opening. ADR 0001
decision 8 recorded "shallow registration recesses" as a direction to
investigate, explicitly as intent rather than an accepted design.

Turning that intent into Issue #3 surfaced a genuine ambiguity. The ticket was
first written as a **flat mosaic** — all colour bodies co-planar peers seating
directly into one continuous backing, finishing at a common Z. Technical review
found that model unbuildable for the case it was meant to fix:

- growing the *backing* recess creates clearance between a piece and the
  backing, but none between a piece and its **lateral neighbour**, which is
  where Spike 01's interference actually was;
- canonical boundaries between adjacent colours are coincident (measured at
  0.0 mm), so the land between two adjacent recesses has zero nominal width and
  cannot carry a printable wall.

That review established that Andy and Elara's intended construction had been
inadvertently changed. The Product Owner then clarified the real model:
**layered relief**, in which each child colour seats **from above** into a
shallow recess in the colour supporting it. Because the child descends into a
pocket rather than passing through a co-planar opening, both blockers disappear.

This ADR records the architecture that follows. The full technical analysis, and
the decisions taken against it, are in the two review comments on Issue #3.

---

## Decisions

### 1. Layered relief is the primary MVP construction model.

Successive colour bodies are assembled vertically:

    white backing  ->  red enclosing colour  ->  yellow enclosed island

Each child is placed from above into a shallow registration recess in the body
below it. Recesses are **assembly and glue-up guides, not friction fits and not
mechanical interlocks**.

Registration recesses generalise to **any supporting relationship** — the
backing locating the main artwork body, the main body locating an island. They
are not an island-only mechanism.

### 2. Canonical containment does not require a fabrication through-hole.

**The central architectural decision of this spike.**

In canonical topology an island is a **hole** in the colour enclosing it — Spike
01 asserts exactly this (`b_hole == c_outer`). In layered-relief fabrication the
supporting body is instead made **solid** beneath the child, with only a shallow
registration pocket removed:

    fabrication_support = solid supporting footprint - shallow derived child recess

The canonical child/hole relationship in artwork topology is **unchanged**. The
child visually replaces the supporting material once assembled.

This breaks the 1:1 correspondence between canonical regions and fabrication
bodies that held throughout Spike 01, where a hole was a real through-hole. Any
future code that assumes region↔body identity is now wrong.

**Assumption: visually opaque material.** With opaque filament the covered
supporting material cannot be seen and the substitution is invisible.
Translucent-material behaviour is a **future constraint**, out of scope for
Spike 02, and would need revisiting before Layercake supports translucent
filaments.

### 3. Clearance is derived fabrication geometry, applied radially to the recess.

Canonical artwork boundaries remain mathematically exact — ADR 0001 decision 6,
unchanged and now doubly load-bearing. Physical fit clearance exists **only** in
derived fabrication geometry and never mutates canonical topology.

The recess is the child's canonical seating footprint dilated **outward** by a
configurable **per-side (radial)** clearance. **The canonical child is never
shrunk to manufacture a fit.**

Dilation uses a **round join**, giving a true radial offset so the separation is
the requested clearance everywhere. A mitre join would hand out clearance up to
`c√2` on a diagonal — more than was asked for, and unrepresentative of what the
printer produces, since a nozzle cannot cut a sharp internal corner anyway.

Achieved clearance is **measured from the derived geometry and reported**, not
assumed: arc chording leaves it under a micron short of nominal, which is
recorded rather than hidden.

### 4. Z model: child thickness is `H + D`.

For visible step height `H` and seating depth `D`:

    child physical thickness = H + D
    recess floor             = supporting body top - D
    new completed top        = supporting body top + H

Completed tops are therefore **invariant in `D`** — with `H = 0.8 mm` the
three-level stack finishes at 0.8 / 1.6 / 2.4 mm whether `D` is 0.2 or 0.4 mm.
That makes seating depth a free experimental variable that does not disturb the
visible artwork, which is what allows Spike 02 to test depth at all.

The support beneath every recess must remain continuous: **a recess is never a
through-hole**, and a non-positive floor is rejected rather than exported.

### 5. Manufacturability cleanup applies to canonical geometry only.

ADR 0001 decision 3 established that cleanup must be topology-aware. This
narrows *where* it runs: Spike 01's minimum-feature cleanup operates on
**canonical artwork geometry, before fabrication derivation**.

It must **never** run over derived geometry. The clearances under test
(0.05–0.20 mm) are far below the 0.4 mm minimum-feature threshold, so cleanup
would erase the experiment itself.

Derived geometry is instead **inspected in report-only mode** and never mutated.
Not looking at all would be worse: dilating a recess thins any support tongue
protruding into a concavity of the child by twice the clearance, and an
unprintable tongue would otherwise reach the plate unnoticed.

### 6. Flat/inlay output is a separate future fabrication mode.

A mode in which all colours finish at one common Z remains a desirable Layercake
option. It is **explicitly not** layered relief and must not be conflated with
it: the review above showed it raises its own unsolved problem — adjacent
co-planar colours have coincident canonical boundaries, so there is no room for
a separating land between their recesses.

Recorded here as a distinct future fabrication mode with its own open question,
not as a variant of this decision.

### 7. Process conditions are part of the experiment, not incidental.

Two printer-side conditions materially change the achieved result and must be
recorded alongside any measurement:

- **Slicer layer height.** The slicer quantises a pocket floor to a layer
  boundary. Every Z dimension is designed as a whole multiple of **0.20 mm**;
  printing at another layer height silently changes the depth under test.
- **Elephant-foot compensation.** A child's seating portion is its bottom
  0.2–0.4 mm, exactly where first-layer squish is worst. At 0.05 mm clearance
  the foot alone can exceed the gap. No chamfers are applied in Spike 02; the
  compensation value used is recorded as an experimental condition instead.

Recess depth, XY clearance and minimum supporting thickness remain **fabrication
parameters requiring physical experimentation**. Figures used in Spike 02
illustrate the concept; they are not production defaults.

---

## Consequences

**Positive**

- The construction that Spike 01 physically rejected is replaced by one whose
  fit problem is removed by geometry rather than by tightening a tolerance.
- ADR 0001's canonical model is untouched. Clearance and recesses are derived at
  export, so this is additive work rather than rework.
- Seating depth can be varied without disturbing the visible artwork.
- Registration recesses generalise across supporting relationships, so a
  four-colour stack needs no new mechanism.

**Negative / accepted costs**

- **Region↔body is no longer 1:1** (decision 2). Canonical topology and
  fabrication geometry must be reasoned about separately from here on.
- The opaque-material assumption is now load-bearing (decision 2).
- **Registration error accumulates linearly with relief depth**: each seating
  contributes its own per-side play, so the topmost piece can sit further off
  nominal than any single joint allows. Measured and reported by Spike 02;
  solving it is deferred, and it bounds how many stacked levels stay practical.
- Results are conditional on printer setup (decision 7), so a clearance number
  from this spike is not automatically portable to another machine.

**Deferred**

- Provisional default XY clearance and recess depth — pending physical results.
- Minimum supporting thickness as a production rule.
- Flat/inlay mode and its separating-land problem (decision 6).
- Translucent-material behaviour (decision 2).
- Cumulative registration error.

---

## Relationship to ADR 0001

ADR 0001 remains historically accurate and is **not** rewritten. Specifically:

| ADR 0001 | Status after this ADR |
|---|---|
| Decisions 1–5 (topology, Clipper2, cleanup, lifecycle, winding) | Unchanged |
| Decision 6 (exact canonical boundaries; clearance derived) | Unchanged and reinforced — decision 3 here is its application |
| Decision 7 (separate co-registered STL bodies) | Unchanged |
| Decision 8, rejection of full-depth zero-clearance insertion | Unchanged — still rejected |
| Decision 8, "shallow registration recess" direction | **Superseded** by decisions 1–4 here, which replace intent with a specified model |
| Decision 8, minimum-feature policy still provisional | Unchanged — still provisional, still untested |

---

## Status of supporting evidence

| Evidence | State |
|---|---|
| Z arithmetic, `H + D`, tops at 0.8/1.6/2.4 for both depths | Verified in software |
| Canonical hole → solid support with blind pocket | Verified in software (Euler number 2 on the enclosing body) |
| Clearance present numerically, canonical unmutated | Verified in software |
| Support continuous beneath every recess | Verified in software |
| Meshes manifold | Verified by the Spike 01 validator, with its stated limitations |
| Slicer import/slice evidence | **Outstanding — Andy (printer occupied)** |
| Physical fit, registration, seating, step height, recess quality | **Outstanding — Andy** |

Decisions 1–6 stand on the software model and on the Spike 01 physical result
that motivated them. The **parameter values** they carry — clearance, depth,
supporting thickness — are provisional until Spike 02's physical validation is
complete, at which point this ADR should be revised with the measured defaults.
