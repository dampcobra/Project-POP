Implements the software portion of #3.

**Do not merge** — the depth question is still open. Round 1 is physically
validated; round 2 artefacts are ready to print.

**Round 1 physical result: concept PASS.** Pieces guide into position without
locking, and the three-level stack assembles. `D = 0.20 mm` too shallow,
`0.40 mm` better, still wanting more — which is what round 2 answers.

## What this is

Spike 01 physically rejected full-depth zero-clearance insertion. This replaces
it with **layered relief**: each colour body seats **from above** into a shallow
registration recess in the colour supporting it.

```
white backing  ->  red enclosing colour  ->  yellow enclosed island
       0.8              1.6                        2.4 mm
```

All software criteria pass; **163 tests green**, including Spike 01's 55
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


---

# Round 2 — depth-only follow-up

Added to this PR rather than opened as a new spike. Full write-up:
`docs/spike-02/round-2-depth-sweep.md`.

## Why 0.20 mm failed, mechanically

At a 0.20 mm layer height a 0.20 mm recess engages **exactly one layer — the
first one**, which carries squish, elephant-foot compensation and bed-levelling
error. No well-formed material does any registering at all. Each step below adds
one clean layer.

| D (mm) | Child thickness | Layers engaged | Clean layers | Support floor | Dimples |
|---|---|---|---|---|---|
| 0.40 | 1.20 | 2 | 1 | 1.20 | 1 |
| 0.60 | 1.40 | 3 | 2 | 1.00 | 2 |
| 0.80 | 1.60 | 4 | 3 | 0.80 | 3 |
| 1.00 | 1.80 | 5 | 4 | 0.60 | 4 |

Seated tops all finish at **2.40 mm** — flush, invariant in depth.

## What changed, and why it had to

**Backing 0.8 → 1.6 mm.** A 0.8 mm backing cannot host a 0.8 mm recess: the floor
vanishes and the pipeline correctly refuses it as a through-hole. Verified
against the code before proposing the change. The backing is structural and
conceptually independent of the visible artwork colours, so thickening the
*fixture* applies existing architecture rather than altering the Z model. `H` is
unchanged. The middle body needs no change — its thickness is `H + D`, so its
floor stays 0.80 mm at every depth.

**Sweep extended to 1.00 mm** so it brackets the answer rather than ending where
Andy still wants more.

**Clearance held at 0.05 mm as a fixed condition**, not carried forward as a
chosen optimum: round 1's six matrix children are the same nominal square, yet
nominally identical prints felt different, so process variation is at least as
large as the ladder step.

**Three identical children per depth**, so print variation shows as spread within
a depth instead of masquerading as a difference between depths.

**Children carry engraved dimples**, count encoding depth — engraved rather than
raised so they cannot interfere with the flushness check.

## A latent bug this round exposed in Spike 01 code

Building the `D.80` label failed: a seven-segment `8` has **two holes whose side
edges are collinear**, and earcut merges their boundary segments. Round 1 never
hit it because its labels only use `0`, `1`, `2` and `5`.

Same class as the round-1 finding, but in `extrude` — the older path, which had no
closure guard. `extrude` now **verifies its own output is closed**, with a
regression test using the exact failing geometry. Spike 01's own artwork is
unaffected (one hole) and its 55 tests pass unchanged, but the bug was real and
**latent since Spike 01**: any artwork with two similarly arranged holes would
have produced a quietly open mesh.

## Round 2 artefacts

`artefacts/spike02/depth-followup/` — fixture, 12 children, co-registered
assembly, plate layout (230 × 51 mm), debug SVG, validation report, parameters
JSON, and `depth-followup-report.md` as the observation sheet.

## Round 2 outstanding — Andy

- [ ] Print at **0.20 mm layers with 0.15 mm elephant-foot compensation** — same
      as round 1, or comparability is lost.
- [ ] Test all three replicates per depth.
- [ ] Record against the acceptance target: **positive registration during normal
      glue-up handling**, not dry retention and not a friction fit.

## Round 2 limitations

- Recess variation is **not** replicated — one recess per depth; only child
  variation is captured.
- Clearance is held, not measured; this round says nothing new about it.
- S1/S2 not re-run, by decision.
