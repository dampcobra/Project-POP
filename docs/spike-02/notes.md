# Spike 02 — software notes

**Issue:** [dampcobra/Project-POP#3](https://github.com/dampcobra/Project-POP/issues/3)
**Date:** 2026-09-04
**Status:** Round 1 physically validated — **concept PASS**. Round 2 (depth sweep) artefacts ready to print.

Architecture is recorded in [ADR 0002](../adr/0002-layered-relief-registration-recesses.md).
Andy's observation sheet is generated as `artefacts/spike02/spike02-report.md`.

## Running it

```bash
.venv/Scripts/python.exe -m pytest                    # 163 tests
.venv/Scripts/python.exe -m layercake_spike.spike02   # writes artefacts/spike02/
```

Exit code is 0 only if every software criterion holds.

## What was built

| Module | Responsibility |
|---|---|
| `spike02/params.py` | Every experimental parameter and the cell matrix |
| `spike02/solids.py` | `extrude_stepped` — prisms with shallow pockets and raised bosses |
| `spike02/fabricate.py` | Canonical → fabrication derivation: recesses, Z planes, floors |
| `spike02/coupon.py` | The labelled 3×2 clearance/depth coupon plus two shape controls |
| `spike02/stack.py` | The three-level white → red → yellow artwork stack |
| `spike02/font.py` | Rectangle stroke font for on-part labels |
| `spike02/arrange.py` | Co-registered assembly and plate-laid print arrangements |

Spike 01's modules are untouched apart from one additive change: `clipper.offset`
gained an optional `join` argument, defaulting to the existing mitre behaviour.

## Software results

All criteria pass:

| Criterion | Result |
|---|---|
| Requested per-side clearance present numerically | PASS — achieved within 1 µm of nominal on all 8 cells |
| Recess depth correct | PASS |
| Support continuous beneath every recess | PASS — worst floor 1.20 mm |
| Child thickness follows `H + D` | PASS |
| Three-level Z arithmetic 0.8 / 1.6 / 2.4 | PASS at both depths |
| Enclosed island seated from above, not stacked | PASS |
| All meshes manifold | PASS |
| Spike 01 tests still green | PASS — 55 of the 137 |

Coupon plate footprint is 214 × 110 mm, comfortably inside a P1S bed.

## Findings worth carrying forward

### 1. The ear-clipping triangulator is not a *constrained* triangulator

`extrude_stepped` builds caps and walls from one shared index set, as Spike 01
established. That argument holds only if the cap triangulation reproduces each
feature boundary as its own edges — and earcut does not guarantee it. Where two
features in the same cap have **collinear boundaries**, it merges their boundary
segments into one long edge.

Every glyph on a text baseline is exactly that case. The failure is quiet: the
triangulated **area is still correct**, so an area check passes while caps and
walls no longer correspond and the surface is open.

Two consequences, both now in the code:

- `extrude_stepped` **verifies its own output is closed** and raises otherwise.
  It can no longer return geometry that merely looks right.
- Label lettering is assembled with a `manifold3d` boolean union instead. That is
  a guarantee, not a repair pass — the result is checked by our own validator
  either way.

This is a caveat on ADR 0001's "manifold by construction" principle: construction
is only as sound as the triangulator underneath it, so the construction must
check itself.

### 2. Morphological opening flags tight corners, not just thin features

Opening cannot reproduce an internal corner tighter than its own probe radius, so
every concave corner of the support registers as a sliver. Recess corners are
radiused by the clearance (0.05–0.20 mm), all tighter than the 0.2 mm probe, so
all 23 findings on this coupon are corner artefacts and **zero** are genuinely
thin support.

Reporting them undifferentiated would bury a real defect among harmless ones, so
findings are classified: a genuine thin feature extends further than the minimum
feature width in at least one direction; a corner artefact does not.

Worth remembering wherever minimum-feature detection is used — including Spike
01's canonical cleanup, which has the same property.

### 3. Clearance semantics need a join type

"Per-side clearance" is under-specified without one. A mitre join hands out `c√2`
on a diagonal — more than requested, and unlike anything a nozzle produces. Round
join gives a true radial offset and radiuses recess corners by `c`, which is
closer to reality.

The cost is arc chording: achieved clearance falls a sagitta short of nominal,
about 0.4 µm here. Tightening `arcTolerance` to remove it costs ~7500 vertices
per corner set — an unusable mesh for a 1000× smaller error than the nozzle. So
the default stands and **achieved clearance is measured and reported** rather
than assumed.

### 4. Registration error accumulates

Each seating contributes its own per-side play. Through two seatings at 0.10 mm,
the topmost piece can sit 0.20 mm off nominal relative to the backing. Reported
per level and cumulatively; solving it is out of scope, but it bounds how many
stacked levels stay practical for a four-colour artwork.

## Not verified here

- **Slicer import/slice evidence** — outstanding, Andy.
- **Physical fit, registration, seating, step height, recess quality** —
  outstanding, Andy. The whole point of the coupon.
- **Self-intersection results** still come from the project's own checker, which
  remains uncorroborated against an independent validator, O(n²) in its broad
  phase, and blind to degenerate touching. Its evidential status is unchanged
  from Spike 01 and has deliberately not been strengthened.
- **The 0.4 mm minimum-feature threshold** is still an assumption; this coupon
  does not exercise it.
- **Elephant's foot** is expected to dominate the low-clearance cells. It is
  uncontrolled by design (no chamfers, per decision); the compensation value used
  must be recorded or the 0.05 mm result is uninterpretable.

## What the physical run should settle

1. A provisional default XY clearance and recess depth — or a clearly narrowed
   follow-up experiment.
2. Whether the `S1` concave control and `S2` radiused control behave
   differently. They run at identical clearance and depth, so if `S2` seats and
   `S1` does not, the failure is **corner binding** rather than insufficient face
   clearance — a distinction that changes what Layercake should do about it.
3. Whether the visible support-colour outline around each seated child is
   acceptable at normal viewing distance. Its width is exactly the clearance, so
   this trades directly against fit.

---

Round 2 (depth sweep) continues in [round-2-depth-sweep.md](round-2-depth-sweep.md).
