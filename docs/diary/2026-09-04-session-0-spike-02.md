# Development diary — 2026-09-04 — Session 0, Spike 02

**Work:** Issue #3 — Spike 02: shallow registration recesses for layered-relief assembly
**Branch:** `spike/3-registration-recesses`

## The ticket changed under review, for a good reason

Issue #3 was first written as a **flat mosaic**: all colour bodies co-planar
peers, seating directly into one continuous backing, finishing at a common Z.

Technical review found that model could not fix the failure it was written to
fix. Growing the *backing* recess creates clearance between a piece and the
backing, but none between a piece and its **lateral neighbour** — which is
exactly where Spike 01's interference was. And because adjacent canonical
boundaries are coincident (measured at 0.0 mm), the land between two adjacent
recesses has zero nominal width and cannot carry a printable wall.

That review established the flat-mosaic reading had inadvertently changed the
intended construction. Andy clarified: the real model is **layered relief**, with
each child seated from above into a shallow recess. Both blockers disappear,
because the child descends into a pocket instead of passing through a co-planar
opening.

Both reviews are posted on Issue #3 as project history — the first one documents
why the correction was made.

## Findings from building it

**The ear-clipping triangulator is not a constrained triangulator.** Spike 01's
"manifold by construction" argument holds only if the cap triangulation
reproduces each feature boundary as its own edges. Earcut merges *collinear*
boundaries between separate features — which is every glyph on a text baseline.
The failure is quiet: triangulated area is still correct, so an area check
passes while caps and walls no longer correspond and the surface is open.

Fixed two ways: `extrude_stepped` now verifies its own output is closed and
raises otherwise, so it can never return geometry that merely looks right; and
label lettering is assembled with a `manifold3d` boolean union instead. Worth
recording as a caveat on the ADR 0001 principle — construction is only as sound
as the triangulator underneath it.

**Morphological opening flags tight corners, not just thin features.** It cannot
reproduce an internal corner tighter than its probe radius, so every concave
corner of the support registers as a sliver. Recess corners are radiused by the
clearance, all tighter than the probe, so all 23 findings on the coupon are
corner artefacts and none is real. Findings are now classified; reporting them
undifferentiated would bury a genuine defect among harmless ones. The same
property applies to Spike 01's canonical cleanup.

**"Per-side clearance" is under-specified without a join type.** A mitre join
hands out `c√2` on a diagonal, unlike anything a nozzle produces. Round join is
a true radial offset. Its cost is arc chording — 0.4 µm short of nominal, and
tightening it would cost ~7500 vertices per corner set for a 1000× smaller error
than the nozzle. Achieved clearance is therefore measured and reported, not
assumed.

## Mistakes caught by tests

- The cell label builder silently dropped the `D`, producing `C.05 .20`. The
  test only checked the clearance substring, so it passed. Tightened the test.
- An assembly-bounds assertion expected the fixture height when the tallest body
  in the assembly is the three-level stack at 2.4 mm. The code was right; the
  assertion was wrong.

## Result

137 tests green, including Spike 01's 55 unchanged. All software criteria pass.
Coupon plate footprint 214 × 110 mm, comfortably inside a P1S bed.

ADR 0002 records layered relief, and in particular that **canonical containment
does not require a fabrication through-hole** — the enclosing body is solid
beneath its island, carrying only a blind pocket. That breaks the 1:1
region↔body correspondence that held throughout Spike 01, and assumes opaque
material.

## Outstanding

Slicer and physical validation — Andy, once the printer frees up. The coupon
exists to choose a provisional XY clearance and recess depth, or to narrow the
follow-up experiment.

---

Round 1 physical results and the depth follow-up are recorded in
`docs/spike-02/round-2-depth-sweep.md`. Headlines: concept PASS; the D=0.20
failure is explained by that recess engaging only the first printed layer; the
clearance ladder was unresolvable because process variation exceeded its step
size; the proposed 0.80 mm sweep would have been a through-hole in a 0.8 mm
backing, fixed by thickening the fixture; and building the D.80 label exposed a
latent two-collinear-holes bug in Spike 01 extrude, now guarded with a
regression test. 163 tests green.

---

## Round 2 result — 0.80 mm

Andy swept the four depths on the P1S at 0.20 mm layers with 0.15 mm
elephant-foot compensation. **`D = 0.80 mm` is the sweet spot**: best balance of
positive guidance, resistance to rocking and tilting, and easy removal before
glue. 0.40 and 0.60 are usable but feel less positively located; 1.00 is deeper
than necessary and does not earn its extra material.

Recorded as the **provisional measured default**, scoped explicitly to the tested
process. Not a universal constant — one printer, one layer height, one
elephant-foot setting, one seating footprint.

Bracketing the sweep to 1.00 mm was worth it. Every earlier round had ended with
"I wish I had more", and this one did not: the answer is inside the range, so
there is no third round.

**Clearance wording deliberately kept weaker than the depth result.** 0.05 mm is
a *held process-floor value*, not a proven fine-resolution optimum. Round 1 could
not resolve it because process variation exceeded the ladder step, and round 2
held it fixed. Neither round measured it. The two numbers now sit in the same ADR
and it matters that they are not read with equal confidence.

## The consequence nobody had spotted yet

Adopting 0.80 mm has a product implication beyond the test fixture: **at
`H = 0.8 mm` the artwork backing cannot host a 0.80 mm recess.** The floor would
be zero and the pipeline refuses it as a through-hole — the same check that
caught Elara's proposed 0.80 mm sweep earlier.

So the structural backing has to be decoupled from the visible step height in the
*product*, not only in the test fixture. 1.2 mm is the minimum for a two-layer
floor; 1.6 mm gives four. Visible step heights are unaffected — only base
thickness and overall stack height change. Middle bodies need nothing: their
thickness is `H + D`, so it grows with depth and their floor stays at `H`.

Consistent with the backing already being defined as a structural member
conceptually independent of the visible artwork colours, so this is applying
existing architecture rather than a new decision — but it does need saying out
loud before anyone builds artwork on a 0.8 mm base.

## Recorded in code, not just prose

`MEASURED_DEFAULT_DEPTH_MM`, its layer-count equivalent, the minimum backing it
implies, and `HELD_CLEARANCE_MM` all live in `params.py` with their provenance,
so the generated JSON and the observation sheet carry the result too and it
cannot drift silently. Five tests pin them, including one asserting that a 0.8 mm
backing genuinely cannot host the default.

170 tests green. ADR 0002 gains decision 8.
