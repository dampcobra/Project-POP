# Spike 02 round 2 — depth-only follow-up

**Result: `D = 0.80 mm` is the provisional measured default recess depth.**

Round 1 settled the concept and left one question: **how deep should a
registration recess be?** Andy preferred more depth at every level tested, so
this round swept depth alone. It is answered below.

Continues [`notes.md`](notes.md). Architecture: [ADR 0002](../adr/0002-layered-relief-registration-recesses.md).
Andy's observation sheet is generated as
`artefacts/spike02/depth-followup/depth-followup-report.md`.

## Round 1 physical results

Andy, Bambu P1S, 0.20 mm layer height, 0.15 mm elephant-foot compensation, dry
assembly only.

**Concept PASS.** Pieces are guided into position without becoming friction-fit,
and the three-level white → red → yellow stack assembles correctly.

- `D = 0.20 mm` too shallow; `D = 0.40 mm` noticeably better; still wants more.
- Preferred clearance direction: `0.05 mm`.
- S1/S2 shape comparison inconclusive — depth dominated.

### Why 0.20 mm failed, mechanically

At a 0.20 mm layer height a 0.20 mm recess engages **exactly one layer — the
first one**, which carries squish, elephant-foot compensation and bed-levelling
error. No well-formed material does any registering at all. `D = 0.40 mm` brings
one clean layer into play, which is why it felt better, and the pattern predicts
continued improvement with diminishing returns.

| D | Layers engaged | Printed under normal conditions |
|---|---|---|
| 0.20 | 1 | **0** |
| 0.40 | 2 | 1 |
| 0.60 | 3 | 2 |
| 0.80 | 4 | 3 |
| 1.00 | 5 | 4 |

The threshold is therefore **process-relative, not absolute**: at 0.08 mm layers,
0.20 mm would behave differently.

### Why the clearance result is weaker than it looks

All six round-1 matrix children are the **same nominal 12 × 12 square** — only
the recesses differ. Andy observed that nominally identical prints felt
different, which means **process variation is at least as large as the ladder
step**. The experiment's resolution is coarser than the thing it measured, so
"0.05 mm preferred" reads more honestly as *"everything available was loose; the
tightest was least bad."*

Clearance is therefore **held** at 0.05 mm in round 2 as a fixed condition, not
carried forward as a chosen optimum.

### Why S1/S2 was doubly confounded

Depth dominated, as Andy and Elara concluded. It was also run at `c = 0.10 mm`
with everything loose — and corner binding **needs interference to manifest**.
The control ran at the wrong end of the clearance range to test its own
hypothesis. Not re-run in round 2, by decision.

## Round 2 design

One variable. Four depths bracketing the expected optimum, three identical
children each.

| D (mm) | Child thickness | Layers engaged | Clean layers | Support floor | Dimples on child |
|---|---|---|---|---|---|
| 0.40 | 1.20 | 2 | 1 | 1.20 | 1 |
| 0.60 | 1.40 | 3 | 2 | 1.00 | 2 |
| 0.80 | 1.60 | 4 | 3 | 0.80 | 3 |
| 1.00 | 1.80 | 5 | 4 | 0.60 | 4 |

Seated tops all finish at **2.40 mm** — flush, invariant in depth, as the Z model
requires.

### The backing had to change: 0.8 → 1.6 mm

The artwork backing is `H`, and a 0.8 mm body **cannot host a 0.8 mm recess** —
the floor vanishes and the pipeline refuses it as a through-hole. Verified
against the code:

```
D=0.40  backing floor +0.40 mm   ok
D=0.60  backing floor +0.20 mm   ok
D=0.80  backing floor  0.00 mm   REFUSED - would make a through-hole
```

Without this change the proposed sweep would have terminated at a value the code
will not generate.

The backing is a **structural** member, conceptually independent of the visible
artwork colours (Issue #1), so thickening the *fixture* applies existing
architecture rather than altering the Z model. `H` is unchanged and seated tops
still finish flush.

The **middle body needs no such change**: its thickness is `H + D`, so it grows
with depth and its floor under the island stays 0.80 mm at every depth. Only the
backing is pinned.

### Identifying the children

Twelve loose pieces of four thicknesses. Each carries **engraved dimples** on its
top face, the count encoding depth. Engraved rather than raised so they cannot
interfere with the flushness check, and placed on a diagonal so no two share an
edge line — collinear features in one cap defeat the triangulator.

### Acceptance target

**Positive registration during normal glue-up handling** — not dry retention, and
not a friction fit.

Depth buys *retention and tilt resistance*; XY accuracy is set by *clearance* and
is unchanged by depth. A piece that locates accurately and stays put while the
assembly is moved is a pass even if it lifts out when inverted. A piece needing
force, or that will not come back out for a dry fit, has gone past being a guide.

## A latent bug this round exposed

Building the `D.80` label hit a mesh failure in **Spike 01's** `extrude`: a
seven-segment `8` has **two holes whose side edges are collinear**, and earcut
merges their boundary segments. Round 1 never saw it because its labels only use
`0`, `1`, `2` and `5`.

Same class as the round-1 finding, but in the older, unguarded code path. Fixed:

- `extrude` now **verifies its own output is closed** and raises otherwise, with
  a regression test using the exact `8` geometry that failed.
- Label lettering is assembled as a union of plain segment boxes, sidestepping
  the triangulator entirely.

Spike 01's own geometry is unaffected — its one-hole case is fine and all 55 of
its tests pass unchanged. But the bug was real and had been **latent since Spike
01**: any artwork with two holes in a similar arrangement would have produced a
quietly open mesh.

## Artefacts

`artefacts/spike02/depth-followup/` — fixture, 12 children, co-registered
assembly, plate layout (230 × 51 mm), debug SVG, validation report, parameters
JSON, and `depth-followup-report.md` as the observation sheet.

## Round 2 physical result

Andy, Bambu P1S, 0.20 mm layer height, 0.15 mm elephant-foot compensation, dry
assembly.

| Depth (mm) | Verdict |
|---|---|
| 0.40 | Usable, less positively located |
| 0.60 | Usable, less positively located |
| **0.80** | **PREFERRED** — best balance of positive guidance, resistance to rocking/tilting, and easy removal before glue |
| 1.00 | Deeper than necessary; no worthwhile handling gain |

**Recorded as the provisional measured default: 0.80 mm.**

### Scope of that number

Measured for **one process**: Bambu P1S, 0.20 mm layer height, 0.15 mm
elephant-foot compensation, 12 × 12 mm square seating footprint. A provisional
default for that process, **not a universal constant**.

### In layers — the form likelier to transfer

0.80 mm at 0.20 mm layers is **4 layers engaged, 3 printed under normal
conditions**. Round 1 showed the 0.20 mm failure was that the recess engaged only
the first printed layer. If engagement count is the governing mechanism,
preferred depth scales with layer height:

| Layer height | 4-layer equivalent |
|---|---|
| 0.12 mm | 0.48 mm |
| 0.16 mm | 0.64 mm |
| **0.20 mm** | **0.80 mm — measured** |
| 0.28 mm | 1.12 mm |

**This is a hypothesis implied by the data, not a tested result.** Only the
0.20 mm case has been measured. Recorded because it is the practically useful
form, and flagged because it has not been checked.

### Clearance is still not a measured value

`0.05 mm` remains a **held process-floor value, not a proven fine-resolution
optimum.** Round 1 could not resolve clearance — nominally identical children
felt different, so process variation is at least as large as the ladder step —
and round 2 held it fixed. Neither round measured it.

Deliberately weaker language than the depth result carries: the two should not be
read with equal confidence.

### Consequence: the artwork backing must be decoupled from H

At `H = 0.8 mm` the **artwork** backing cannot host a 0.80 mm recess — the floor
would be zero and the pipeline refuses it as a through-hole. Adopting this
default requires the structural backing to be thicker than the visible step
height in the *product*, not only in the test fixture:

| Backing | Floor under a 0.80 mm recess |
|---|---|
| 0.8 mm (= H) | 0.00 mm — rejected |
| 1.2 mm | 0.40 mm (2 layers) — minimum |
| 1.6 mm | 0.80 mm (4 layers) |

Consistent with the backing already being a structural member conceptually
independent of the visible artwork colours (Issue #1). Visible step heights are
unaffected — only base thickness and overall stack height change. **Middle bodies
need no change**: their thickness is `H + D`, so it grows with depth and their
floor stays at `H` regardless.

> **Adopted 2026-09-05 (Session 01).** The backing is now an independent
> parameter with its own rule — `deepest recess + minimum floor` = 1.2 mm — and
> no longer inherits `H`. The demo stack consequently finishes at
> 1.2 / 2.0 / 2.8 mm; visible steps are unchanged at `H` each. The round-1
> as-printed 0.8 mm configuration is preserved as
> `ROUND1_AS_PRINTED_BACKING_MM` and remains reproducible. See ADR 0002
> decision 8 and `docs/diary/2026-09-05-session-01.md`.

## Limitations of this round

- **Recess variation is not replicated** — one recess per depth. Only child
  variation is captured, by the three replicates.
- Clearance is held, not measured; this round says nothing new about it.
- S1/S2 not re-run, by decision.
- Results remain conditional on the printer setup: 0.20 mm layers, 0.15 mm
  elephant-foot compensation. Changing either breaks comparability with round 1.
