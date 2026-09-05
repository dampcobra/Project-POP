# Spike 02 follow-up - recess depth sweep

**Question:** How deep should a registration recess be?

**Acceptance target:** Positive registration during normal glue-up handling. NOT dry retention, and NOT a friction fit.

## Held constant

- Clearance **0.05 mm**. Round 1 could not resolve clearance: nominally identical children felt different, so process variation is at least as large as the ladder step. Held at the process floor as a fixed condition, not chosen as an optimum.
- Shape: 12 x 12 mm square, identical to round 1 for comparability.
- **Print at 0.2 mm layer height** with **0.15 mm elephant-foot compensation**, as round 1. Changing either breaks comparability with the first results.
- Visible step height H = 0.8 mm.

## Changed from round 1

Backing **0.8 -> 1.6 mm**. The artwork backing is H (0.8 mm), which cannot host a 0.8 mm recess -- the floor vanishes and the pipeline rejects it as a through-hole. The backing is structural and conceptually independent of the visible artwork colours, so thickening the fixture applies existing architecture rather than altering the Z model. H is unchanged and seated tops still finish flush.

## Cells

| Depth (mm) | Label | Dimples on child | Child thickness (mm) | Layers engaged | Of those, printed normally | Support floor (mm) |
|---|---|---|---|---|---|---|
| 0.40 | `D.40 C.05` | 1 | 1.20 | 2 | 1 | 1.20 |
| 0.60 | `D.60 C.05` | 2 | 1.40 | 3 | 2 | 1.00 |
| 0.80 | `D.80 C.05` | 3 | 1.60 | 4 | 3 | 0.80 |
| 1.00 | `D1.00 C.05` | 4 | 1.80 | 5 | 4 | 0.60 |

**Identifying the children.** Each carries engraved dimples on its top face; the count gives the depth (1 = 0.40, 2 = 0.60, 3 = 0.80, 4 = 1.00 mm). They are engraved rather than raised so they cannot interfere with the flushness check.

**Why the layer columns matter.** At a 0.20 mm layer height a 0.20 mm recess engaged exactly one layer -- the first one, which carries squish, elephant-foot compensation and bed-levelling error. No well-formed material did any registering at all, which is the likeliest explanation for round 1's result. Each step in this sweep adds one clean layer.

There are **3 identical children per depth**. Please test all three: spread between them is print variation, and in round 1 that was large enough to change a conclusion.

## Physical observations - Andy

| Depth | Rep | Insertion | Registration feel | Tilt / rock | Stays put during handling | Removal for dry fit | Notes |
|---|---|---|---|---|---|---|---|
| 0.40 | 1 |  |  |  |  |  |  |
| 0.40 | 2 |  |  |  |  |  |  |
| 0.40 | 3 |  |  |  |  |  |  |
| 0.60 | 1 |  |  |  |  |  |  |
| 0.60 | 2 |  |  |  |  |  |  |
| 0.60 | 3 |  |  |  |  |  |  |
| 0.80 | 1 |  |  |  |  |  |  |
| 0.80 | 2 |  |  |  |  |  |  |
| 0.80 | 3 |  |  |  |  |  |  |
| 1.00 | 1 |  |  |  |  |  |  |
| 1.00 | 2 |  |  |  |  |  |  |
| 1.00 | 3 |  |  |  |  |  |  |

**Handling is the acceptance criterion, not dry retention.** A piece that locates accurately and stays put while the assembly is moved to glue-up is a pass, even if it lifts out when inverted. A piece needing force, or one that will not come back out for a dry fit, has gone past being a guide and become a press fit -- which the design principle rules out.

## Decision

| Question | Answer |
|---|---|
| Shallowest depth giving acceptable registration |  |
| Deepest depth still comfortably a guide, not a press fit |  |
| Proposed default recess depth |  |
| Does the sweep bracket the answer, or is more depth still wanted? |  |

## Limitations of this round

- Recess variation is NOT replicated: one recess per depth. Only child variation is captured, by the three replicates.
- Clearance is held, not measured; this round says nothing new about it.
- The S1/S2 shape controls are deliberately not re-run.

## Validation caveats

- Self-intersection counts come from this project's own triangle-triangle checker, not from trimesh, which has no such test. That checker has not been cross-checked against an independent mesh validator, is O(n^2) in its broad phase, and treats touching faces as non-intersecting. Its evidential status is unchanged from Spike 01.
- Recess dilation uses a round join, so clearance is radial. Clipper2 approximates each corner arc with chords, leaving the achieved clearance a sagitta short of nominal -- under 1 um at these radii, roughly 1000x finer than a 0.4 mm nozzle. Achieved values are measured and reported, not assumed.

---

# Result (measured)

**Provisional default recess depth: 0.8 mm** (4 layers at 0.2 mm layer height).

0.80 mm gives the best balance of positive guidance, resistance to rocking/tilting, and easy removal before glue. 0.40 and 0.60 are usable but feel less positively located; 1.00 is deeper than necessary and does not improve handling enough to justify it.

| Depth (mm) | Verdict |
|---|---|
| 0.40 | usable, less positively located |
| 0.60 | usable, less positively located |
| 0.80 | PREFERRED - best balance |
| 1.00 | deeper than necessary; no worthwhile handling gain |

**Scope.** Measured for one process: Bambu P1S, 0.20 mm layer height, 0.15 mm elephant-foot compensation, 12 x 12 mm square seating footprint. A provisional default, not a universal constant.

**Clearance.** 0.05 mm remains a HELD process-floor value, not a proven fine-resolution optimum. Round 1 could not resolve clearance because process variation exceeded the ladder step, and round 2 held it fixed, so neither round measured it.

**In layers.** Expressed in layers the result is 4 engaged, 3 of them printed under normal conditions. If engagement count is the governing mechanism the preferred depth scales with layer height (0.64 mm at 0.16 mm layers, 1.12 mm at 0.28 mm). That is a hypothesis implied by the data, NOT a tested result -- only the 0.20 mm case has been measured.

**Consequence for the artwork backing.** At H = 0.8 mm the artwork backing cannot host a 0.80 mm recess: the floor would be zero and the pipeline refuses it. Adopting this default requires the structural backing to be decoupled from H in the product, not only in the test fixture. Visible step heights are unaffected. Minimum backing for this default: 1.2 mm.
