# ADR 0003 — Canonical artwork uses visible-surface semantics

- **Status:** Accepted
- **Date:** 2026-09-05
- **Session:** 01 — product model
- **Deciders:** Andy (Product Owner), Elara/ChatGPT (PM & Architect), Claude (Developer)
- **Supersedes:** nothing. Reinforces [ADR 0002](0002-layered-relief-registration-recesses.md) decision 2.
- **Related:** [Issue #6](https://github.com/dampcobra/Project-POP/issues/6) ·
  [Issue #8](https://github.com/dampcobra/Project-POP/issues/8) ·
  [Issue #9](https://github.com/dampcobra/Project-POP/issues/9)

## Context

Issue #6 removes fabrication concerns from the canonical model. Taking Z out
exposed a question the spike had never had to answer:

> **Does a canonical region's area mean "this colour is VISIBLE here", or "this
> colour's MATERIAL is here"?**

Spike 01 never faced it because `Partition.containment()` filtered by Z band,
skipping any pair of regions in different bands. The backing and the foreground
were therefore never compared, and their shared footprint was invisible to
validation.

With Z gone, the two readings diverge — and the Spike Glyph as authored in
Spike 01 turns out to use **both at once**:

| Relationship | Authored as | Implied reading |
|---|---|---|
| foreground ⊃ island | foreground **has a hole** where the island sits | visible |
| backing ⊃ foreground | backing has **no hole** where the foreground sits | material |

Under a single consistent rule the second case reports the backing overlapping
the foreground by 902 mm² and the island by 64 mm².

The visible reading was then tested against the Spike Glyph and tiles it exactly:

```
visible areas:  backing 1534.0 + foreground 902.0 + island 64.0 = 2500.0
badge area                                                      = 2500.0
overlap 0.000   void 0.000
```

## Decisions

### 1. Canonical regions form a non-overlapping visible partition.

A canonical artwork describes **what colour is visible at each point of the
finished 2D artwork**. Every point shows exactly one colour. Two regions
claiming the same area is an error at any nesting depth, not only between
siblings.

### 2. A parent is canonically absent wherever a visible child covers it.

If a child region covers part of its parent, the parent has a hole there. The
parent's canonical area is what remains *visible* of it.

### 3. Genuine void remains canonically absent.

A hole with no region occupying it is legal artwork — background, showing
whatever lies beneath. It is **reported, not rejected**: `void_area` is surfaced
by validation so it is visible, but it does not fail the artwork.

### 4. Hidden support beneath a child is a fabrication concern.

Material that exists under a visible region — the solid backing beneath the
foreground, the solidified support beneath an island — is introduced
**downstream**, at fabrication derivation. It **must not** be represented as
overlapping canonical artwork.

Authoring a solid backing beneath the foreground, as Spike 01 did, is now a
validation error rather than a way of saying "there is material under there".

### 5. Containment is canonical topology; material continuation is fabrication.

Containment stays in the canonical model — it is a fact about the artwork, and
it is what issue #7 derives a stacking order from. **Material
continuation/solidification belongs to #8 and #9.**

This reinforces ADR 0002 decision 2 rather than changing it. That decision has
fabrication *solidify* a support beneath its child, which is only a meaningful
operation because the parent is canonically **absent** there. Under material
semantics `solidify_support` would have nothing to do.

### 6. Canonical artwork represents opaque visible colour.

Layercake **does not model colour contribution through translucency or
underlying material layers.** That is deliberately outside the product model.

The visible result comes from the explicit surface colours themselves. Hidden
supporting material may exist for fabrication, but it **must not alter the
canonical colour semantics** — a colour is an opaque identity, not a
contribution to be combined with what sits beneath it.

ADR 0002 decision 2 already assumed visually opaque material for the specific
case of an island covering its support. This raises that from a local assumption
to a **product principle**: there is no translucency model anywhere, and adding
one would be a change to this decision rather than a feature addition.

## Consequences

**Positive**

- Canonical artwork is a genuine partition, which is what Issue #1 called it,
  and gap/overlap validation over it is meaningful across the whole surface.
- `solidify_support` (ADR 0002 decision 2) has a coherent job.
- Void (#8) is coherent: a hole with nothing in it shows what is beneath.
- The canonical/fabrication boundary is sharper — canonical says what is seen,
  fabrication says what material exists.

**Negative / accepted costs**

- **The Spike Glyph fixture changed.** The backing gains a hole where the
  foreground sits.
- **The Spike Glyph's shared-edge count changed from 4 to 15** — the foreground's
  full 11-vertex boundary is now a genuine shared boundary with the backing, plus
  the island's 4. This is **not a regression**: the old count was an artefact of
  Z-band filtering, not a product invariant. Issue #6's acceptance criterion
  requiring the same count as Spike 01 was **amended**, and the new count is
  explicitly documented and tested.
- Artwork that relied on overlapping regions to express layering must be
  re-authored. Nothing outside the spike did.

**Deferred**

- Material continuation and solidification (#8, #9).
- Stacking order derivation (#7), which consumes the containment this model
  exposes.
- Any translucency or colour-mixing model. Out of scope by decision 6, and it
  would supersede this ADR rather than extend it.

## Status of supporting evidence

| Evidence | State |
|---|---|
| Visible partition tiles the Spike Glyph exactly (1534 + 902 + 64 = 2500) | Verified in software |
| Containment survives the change: backing → foreground → island | Verified in software |
| Overlap detected between ancestor and descendant, not only siblings | Verified in software |
| Void reported and not rejected | Verified in software |
| Opaque colour: no translucency concept in the model | Asserted by test |
| Physical behaviour of an opaque colour model | Consistent with Spike 01 and 02 prints, which used opaque PLA throughout; no translucent material has been printed |
