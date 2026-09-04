Implements the software portion of #3.

**Do not merge** — slicer and physical validation are outstanding while Andy's
printer is occupied.

## What this is

Spike 01 physically rejected full-depth zero-clearance insertion. This replaces
it with **layered relief**: each colour body seats **from above** into a shallow
registration recess in the colour supporting it.

```
white backing  ->  red enclosing colour  ->  yellow enclosed island
       0.8              1.6                        2.4 mm
```

All software criteria pass; **137 tests green**, including Spike 01's 55
unchanged.

| Criterion | Result |
|---|---|
| Requested per-side clearance present numerically | PASS — achieved within 1 µm of nominal on all 8 cells |
| Recess depth correct | PASS |
| Support continuous beneath every recess, no through-holes | PASS — worst floor 1.20 mm |
| Child thickness follows `H + D` | PASS |
| Three-level Z arithmetic 0.8 / 1.6 / 2.4 | PASS at both depths |
| Enclosed island seated from above, not stacked | PASS |
| All meshes manifold | PASS |
| Spike 01 tests still green | PASS |

Run `python -m layercake_spike.spike02`; artefacts land in `artefacts/spike02/`
(committed). Coupon plate footprint is 214 × 110 mm, comfortably inside a P1S bed.

## The architectural decision — ADR 0002

**Canonical containment does not require a fabrication through-hole.**

Canonically an island *is* a hole in the colour enclosing it (Spike 01 asserts
exactly that). In layered relief the supporting body is made **solid** beneath
the child, with only a shallow pocket removed:

```
fabrication_support = solid supporting footprint − shallow derived child recess
```

Canonical topology is unchanged. This **breaks the 1:1 region↔body
correspondence** that held throughout Spike 01, and assumes **visually opaque
material** — translucent behaviour is a future constraint, out of scope here.

ADR 0002 also records: clearance as radial derived geometry (round join,
canonical never shrunk); the `H + D` Z model; cleanup scope; flat/inlay as a
separate future mode; and process conditions as part of the experiment.

ADR 0001 is **not rewritten**. Decisions 1–7 stand; only decision 8's *direction*
is superseded, with a mapping table in ADR 0002.

## The coupon

3 clearances (0.05 / 0.10 / 0.20 mm) × 2 depths (0.20 / 0.40 mm) on one repeated
shape, plus two shape controls at a fixed mid-matrix setting:

- **S1 concave** — asymmetric with a reflex notch
- **S2 radiused** — generously rounded corners

Both run at identical clearance and depth, so shape is the only variable. **If S2
seats and S1 does not, the failure is corner binding rather than insufficient
face clearance** — a 0.4 mm nozzle cannot cut a sharp internal corner. That
distinction changes what Layercake should do about it, which is why the control
pair is there.

Labels are raised on the fixture beside each cell, so neither the visible top nor
the seating face of an insert is compromised.

## Findings worth reviewing

### 1. The ear-clipping triangulator is not a *constrained* triangulator

Spike 01's "manifold by construction" argument holds only if the cap
triangulation reproduces each feature boundary as its own edges. Earcut **merges
collinear boundaries** between separate features — every glyph on a text baseline
is that case.

The failure is quiet: triangulated **area is still correct**, so an area check
passes while caps and walls no longer correspond and the surface is open.

Fixed two ways: `extrude_stepped` now **verifies its own output is closed** and
raises otherwise, so it can never hand back geometry that merely looks right; and
label lettering is assembled with a `manifold3d` boolean union. That is a
guarantee, not a repair pass, and the result is checked by our own validator
either way.

**This is a caveat on ADR 0001's principle**: construction is only as sound as
the triangulator underneath it, so the construction must check itself.

### 2. Morphological opening flags tight corners, not just thin features

Opening cannot reproduce an internal corner tighter than its probe radius. Recess
corners are radiused by the clearance (0.05–0.20 mm), all tighter than the 0.2 mm
probe, so **all 23 findings on this coupon are corner artefacts and zero are
genuinely thin support**. Findings are now classified — reporting them
undifferentiated would bury a real defect among harmless ones.

The same property applies to Spike 01's canonical cleanup.

### 3. "Per-side clearance" is under-specified without a join type

A mitre join hands out `c√2` on a diagonal — more than requested, and unlike
anything a nozzle produces. Round join is a true radial offset. Cost is arc
chording: 0.4 µm short of nominal. Tightening it costs ~7500 vertices per corner
set for a 1000× smaller error than the nozzle, so achieved clearance is
**measured and reported** rather than assumed.

## Limitations, stated

- **Self-intersection results are unchanged in evidential status.** Still the
  project's own checker, still uncorroborated against an independent validator,
  still O(n²) and blind to degenerate touching. Deliberately not strengthened.
- **Elephant's foot is uncontrolled by design.** No chamfers, per decision. The
  seating portion is the child's bottom 0.2–0.4 mm, exactly where squish is
  worst, so at 0.05 mm clearance the foot alone can exceed the gap. **The
  compensation value used must be recorded or that cell is uninterpretable.**
- **Layer height matters.** Every Z dimension is a whole multiple of 0.20 mm.
  Printing at another layer height silently changes the depth under test.
- **Registration error accumulates** — 0.20 mm through two seatings at 0.10 mm.
  Reported per level and cumulatively; solving it is out of scope, but it bounds
  practical relief depth for four colours.
- **The 0.4 mm minimum-feature threshold** is still an assumption; this coupon
  does not exercise it.
- Parameters throughout are experimental inputs, **not production defaults**.

## Changes to Spike 01 code

One additive change only: `clipper.offset` gained an optional `join` argument,
defaulting to the existing mitre behaviour. Everything else in Spike 01 is
untouched and its 55 tests pass unchanged.

New dependency: `manifold3d`, for the label union (see finding 1).

## Outstanding — Andy

- [ ] Bambu Studio import/slice, label readability, plate practicality.
- [ ] Physical fit, registration, dry-fit removal, seating, step height, recess
      quality, visible clearance — per cell.
- [ ] Assemble the three-level white → red → yellow case.
- [ ] Record layer height and elephant-foot compensation used.

`artefacts/spike02/spike02-report.md` is the observation sheet, with blank tables
per cell ready to fill in.

Full notes: `docs/spike-02/notes.md`. Architecture:
`docs/adr/0002-layered-relief-registration-recesses.md`. Session notes:
`docs/diary/2026-09-04-session-0-spike-02.md`.
