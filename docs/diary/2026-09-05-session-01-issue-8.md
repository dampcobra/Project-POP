# Development diary — 2026-09-05 — Session 01, issue #8

**Branch:** `feat/8-fabrication-bodies`
**Ticket:** #8 — Region to fabrication body relationships

## What this is

`layercake.fabrication.body` — the fabrication-side domain model. What a correct
body *is*, not how to build a set of them from an artwork; that is #9.

The central distinction is stated in the model rather than left to be inferred
from anonymous polygons:

```
hole that hosts a child  ->  solidified away, and a Pocket naming that child
hole with no child       ->  a genuine void, kept as a real hole
```

`BodyFootprint.void_holes` holds only the second kind. The first is gone from the
footprint and survives as a `Pocket` carrying the identity of the child it seats.

## Two flagged points, assessed before building

**Offset is not needed for #8.** Separating a hosted hole from a void is boolean
difference — subtract what the children occupy and see what is left. Verified
before writing anything:

```
h1 (hosts K)   uncovered area = 0.000
h2 (void)      uncovered area = 16.000
```

So the canonical geometry boundary stays exactly as #6 left it, untouched. The
operation that *does* need offset is dilating a child's footprint into the pocket
it seats in — clearance geometry, which belongs to #9. A test asserts this module
calls nothing named offset, checking for a real call rather than the word, since
the docstring says offset is deliberately unused.

**Euler number is not available at this layer.** A footprint here is rings of 2D
points; there is no mesh to read an Euler number from. The direct equivalent is
asserted instead: no hole of the fabrication footprint encloses the child's area,
and a void's hole does enclose its own. Spike 02 already asserts Euler numbers on
meshes, and that is where the mesh-level version belongs — #9.

## The bug worth recording

My first implementation subtracted each child's **visible surface** rather than
its **outer boundary**. The Spike Glyph caught it immediately: the backing
reported a 64 mm² void.

The island sits inside the foreground's hole, so the foreground's *visible*
surface excludes it — subtracting that from the backing's hole left the island's
area behind as a false void two levels up. A child body physically occupies its
whole outer footprint; its own holes are that child's business, handled at its
own level.

A one-line fix, but only visible because the fixture had three levels of nesting.
A two-level test would have passed.

## Design decisions

**A pocket is a typed concept, not a polygon in a list.** `Pocket.for_region`
names the canonical region it seats, so a body traces back to the artwork and
forward to the piece that drops into it. `hosted_regions()`, `hosts()` and
`pocket_for()` make the relationship directly askable, and `to_dict()` keeps the
identifiers rather than reducing everything to geometry.

**The floor beneath a pocket is derived, not stored.**
`FabricationBody.floor_beneath(region_id)` computes it from the body's own
thickness, so the two cannot drift apart. Same reasoning as #5's derived
provenance and #7's derived level.

**Z is named quantities.** `ZExtent(bottom_mm, top_mm)` with a `thickness_mm`
property — no tuple positions, no arithmetic at call sites.

**Invariants enforced, continuing #6 and #7.** Two pockets for one child, a
pocket at least as deep as its body, a body with no positive thickness, a ring
given as a mutable list or with fewer than three points, and two bodies claiming
the same region are all refused at construction.

## A case the model does not cover, deliberately

A child *smaller* than its hole leaves a void that is itself annular — a hole
with a hole in it. That is legal canonical artwork, since ADR 0003 allows voids,
but `void_holes` is a flat list of rings and cannot express it.

Refused with a clear message rather than silently mis-shaped. Flagged for #9 to
decide: either the representation gains nesting, or such artwork is rejected
earlier. The simply-connected partial case — a child touching one edge of its
hole — *is* handled, and has a test.

## Result

322 tests pass, 34 of them new. Both spike pipelines unchanged and still PASS.
Nothing from #9 pulled forward.
