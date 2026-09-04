# Spike 02 report - shallow registration recesses (layered relief)

Issue: dampcobra/Project-POP#3. Construction: layered relief: white backing -> red enclosing colour -> yellow island.

## Process conditions

- **Slicer layer height: 0.2 mm.** Every Z dimension is a whole number of these, so the slicer cannot quantise a feature into a depth other than the one under test. Print at this layer height or the experiment measures something else.
- **Elephant-foot compensation: record the value used.** The seating portion of each child is its bottom 0.2-0.4 mm, exactly where first-layer squish is worst. At 0.05 mm clearance the foot alone can exceed the gap, so this is an experimental condition, not a detail.
- Nozzle assumption: 0.4 mm.

## Model

- Visible step height `H` = 0.8 mm; child thickness = `H + D`.
- Clearance: per-side (radial), recess dilated outward from the canonical child footprint; the child is never shrunk, round join.
- Coupon fixture support: 1.6 mm (deliberately thicker than H so floor thickness cannot confound the fit result).
- Three-level stack backing: 0.8 mm (kept at H so the 0.8 / 1.6 / 2.4 mm result is genuinely validated).

## Test cells

| Cell | Label | Shape | Clearance (mm) | Depth (mm) | Child thickness (mm) | Support floor (mm) | Visible outline width (mm) |
|---|---|---|---|---|---|---|---|
| m_c005_d020 | `C.05 D.20` | simple | 0.05 | 0.20 | 1.00 | 1.40 | 0.050 |
| m_c010_d020 | `C.10 D.20` | simple | 0.10 | 0.20 | 1.00 | 1.40 | 0.100 |
| m_c020_d020 | `C.20 D.20` | simple | 0.20 | 0.20 | 1.00 | 1.40 | 0.200 |
| m_c005_d040 | `C.05 D.40` | simple | 0.05 | 0.40 | 1.20 | 1.20 | 0.050 |
| m_c010_d040 | `C.10 D.40` | simple | 0.10 | 0.40 | 1.20 | 1.20 | 0.100 |
| m_c020_d040 | `C.20 D.40` | simple | 0.20 | 0.40 | 1.20 | 1.20 | 0.200 |
| s_concave | `S1 C.10 D.20` | concave | 0.10 | 0.20 | 1.00 | 1.40 | 0.100 |
| s_radiused | `S2 C.10 D.20` | radiused | 0.10 | 0.20 | 1.00 | 1.40 | 0.100 |

`S1` is the asymmetric/concave control; `S2` is the radiused-corner control. Both run at the same clearance and depth, so shape is the only variable between them. If S2 seats and S1 does not, the failure is corner binding rather than insufficient face clearance -- a 0.4 mm nozzle cannot cut a sharp internal corner.

## Three-level stack

| Depth (mm) | Completed tops (mm) | Cumulative registration freedom (mm) |
|---|---|---|
| 0.20 | 0.8 / 1.6 / 2.4 | 0.20 |
| 0.40 | 0.8 / 1.6 / 2.4 | 0.20 |

Completed tops are invariant in seating depth, which is what makes depth a free experimental variable. Registration freedom accumulates: each seating adds its own per-side play, so the topmost piece can sit further off nominal than any single joint allows. Reported as evidence; solving it is out of scope.

## Slicer observations - Andy

| Check | Result | Notes |
|---|---|---|
| All bodies import at expected positions |  |  |
| Geometry repair warnings |  |  |
| All variants slice |  |  |
| Labels readable / cells identifiable |  |  |
| Plate arrangement practical |  |  |
| Elephant-foot compensation used |  |  |

## Physical observations - Andy

Fit: drops / needs pressure / will not insert.

| Cell | Label | Fit | Registration | Removal before glue | Seats to floor | Step height | Recess quality | Visible clearance |
|---|---|---|---|---|---|---|---|---|
| m_c005_d020 | `C.05 D.20` |  |  |  |  |  |  |  |
| m_c010_d020 | `C.10 D.20` |  |  |  |  |  |  |  |
| m_c020_d020 | `C.20 D.20` |  |  |  |  |  |  |  |
| m_c005_d040 | `C.05 D.40` |  |  |  |  |  |  |  |
| m_c010_d040 | `C.10 D.40` |  |  |  |  |  |  |  |
| m_c020_d040 | `C.20 D.40` |  |  |  |  |  |  |  |
| s_concave | `S1 C.10 D.20` |  |  |  |  |  |  |  |
| s_radiused | `S2 C.10 D.20` |  |  |  |  |  |  |  |

### Three-level assembly

| Check | Result | Notes |
|---|---|---|
| White -> red seats correctly |  |  |
| Red -> yellow seats correctly |  |  |
| Visible relief looks/feels like 0.8 mm steps |  |  |
| Yellow registers acceptably relative to white |  |  |

## Decision

| Question | Answer |
|---|---|
| Provisional default XY clearance |  |
| Provisional default recess depth |  |
| Or: narrowed follow-up experiment needed |  |

## Validation caveats

- Self-intersection counts come from this project's own triangle-triangle checker, not from trimesh, which has no such test. That checker has not been cross-checked against an independent mesh validator, is O(n^2) in its broad phase, and treats touching faces as non-intersecting. Its evidential status is unchanged from Spike 01.
- Recess dilation uses a round join, so clearance is radial. Clipper2 approximates each corner arc with chords, leaving the achieved clearance a sagitta short of nominal -- under 1 um at these radii, roughly 1000x finer than a 0.4 mm nozzle. Achieved values are measured and reported, not assumed.

## Not verified here

- Slicer import/slice evidence -- requires Andy's Bambu P1S.
- Physical fit, registration, seating, step height and recess quality.
- The 0.4 mm minimum-feature threshold, which this coupon does not exercise.

## Derived-geometry inspection (report only)

Spike 01's minimum-feature cleanup applies to canonical geometry only. Running it over derived geometry would erase the clearances under test, so derived geometry is measured and reported, never mutated.

Morphological opening detects two things: genuinely thin support, and internal corners tighter than its probe radius. Recess corners are radiused by the clearance, all tighter than the probe, so they register as corner_artifact -- a nozzle rounds them and nothing is lost. Only thin_derived_support is a defect.

**0 genuinely thin support feature(s)**; 23 corner artefact(s), which are harmless.

No derived support feature is thinner than 0.4 mm over a run.
