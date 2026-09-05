# Development diary — 2026-09-05 — Session 01, issue #7

**Branch:** `feat/7-stacking-order`
**Ticket:** #7 — Derive deterministic stacking order from canonical containment

## What this is

`layercake.canonical.stacking` — `derive_stacking_order(artwork) -> StackingOrder`.

Containment already contains the vertical arrangement, so stacking order is
derived rather than authored. Nothing is written back into `CanonicalArtwork`,
which gained no Z, no layer index and no stacking field.

```
level 0: A
level 1: B
level 2: C
```

## The cycle question, answered by probing rather than reasoning

The brief asked me to assess whether a cycle is actually representable through
the public API before writing a test for it, and not to invent an API to make
the test possible. Three findings, all from probing the merged #6 code:

**A cycle is genuinely reachable.** Two regions with *identical footprints*
enclose each other, so each becomes the other's parent:

```
parents: {'P': 'Q', 'Q': 'P'}
roots  : ()
```

No artificial API needed, so the acceptance criterion stands as written.

**Such artwork is already invalid.** `validate()` reports 100 % overlap. The
cycle is a *symptom* of artwork that is not a visible partition, not an
independent failure mode — which is worth saying in the error message so a
reader is pointed at the real problem.

**#6's `ancestors_of` would hang forever on it.** The parent walk had no cycle
guard, so `ancestors_of` and `containment_depth` loop indefinitely. Verified with
a bounded manual walk rather than by running it.

That last one is a defect, not a design question, so I fixed it: the walk now
raises `ArtworkError`. A hang is strictly worse than an exception, and
`containment_depth` is exactly what a naive stacking derivation would reach for.

## Design decisions

**A small typed structure, not a list whose position means height.**
`StackingOrder` holds `StackingLevel(index, peers)`. Position in the tuple and
`index` agree, but the index is stated rather than implied, so a consumer that
slices or filters cannot silently lose the meaning.

**`peers`, not `regions`.** The name carries the semantic the brief was most
concerned about: co-level regions are peers, and nothing says one is above
another. `is_peer_of` makes the relationship directly askable, and the level
index is the only physical statement in the structure.

**The derivation never calls `containment_depth`.** It walks outward from
`roots()`, one level per step, sorting ids at every step. Two reasons: it is
inherently deterministic, and it detects cycles for free — a region taking part
in a cycle always has a parent, so it is never reached from a root and falls out
as unplaced. No separate cycle-detection pass, and no dependency on the walk I
had just found could hang.

**Tie-break is region id, and only region id.** Not declaration order, not
dictionary iteration order, not area or any other geometric value. Tests pin
each of those: a larger sibling with a later-sorting id must still come second,
and artwork authored in a different order must derive identically.

**Placed under `canonical/`.** It is a statement about canonical topology alone —
no thickness, no seating depth, no profile reaches it. Turning a level index into
a Z position is #9's job. A guard test asserts no fabrication vocabulary appears
in the module.

## Result

274 tests pass, 23 of them new. Both spike pipelines unchanged and still PASS.
Nothing from #8 or #9 pulled forward.
