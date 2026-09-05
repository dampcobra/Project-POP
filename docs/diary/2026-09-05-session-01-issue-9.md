# Development diary — 2026-09-05 — Session 01, issue #9

**Branch:** `feat/9-fabrication-derivation`
**Ticket:** #9 — Canonical to fabrication derivation interface

## What this is

The join between the two halves built in #5–#8:

```
derive(artwork, profile) -> FabricationResult
```

Four modules, each with one job:

| module        | job                                                       |
| ------------- | --------------------------------------------------------- |
| `geometry.py` | clearance offsets — fabrication-side only                  |
| `zplan.py`    | where each stacking level sits vertically                  |
| `strategy.py` | **the one place** that decides a parent supports its child |
| `derive.py`   | the entry point, and report-only inspection                |

Stacking is derived inside `derive` rather than accepted as an argument. It
follows deterministically from canonical containment, so taking it from a caller
would put two truths in play and invite them to disagree.

## The conflict I have to flag

**Acceptance criterion 9 cannot be met as written**, and I have not papered over
it with an adapter.

It asks that every derived body be shown manifold under the existing validator,
*reusing the existing proven mesh machinery rather than inventing a second
implementation*. Those two halves are incompatible in the current architecture:

- the proven machinery is `layercake_spike.spike02.solids` and `validate`;
- the product package may not import the spike, asserted by
  `test_the_product_package_does_not_import_the_spike`;
- the product package has no mesh code of its own.

So reuse is architecturally forbidden and the only way to satisfy the letter of
the criterion is the duplication the criterion exists to prevent. Writing a
second extruder inside `layercake` under this ticket would be a significant
piece of unreviewed geometry code smuggled in as a test fixture.

What I did instead: `test_every_body_is_extrudable_as_a_closed_solid` asserts
every **precondition** a manifold extrusion needs — positive thickness, a
non-degenerate outer ring, no repeated vertices, each pocket strictly inside the
body, shallower than the body, disjoint from every other pocket, and not
overlapping any void. Meshing itself, and the manifold assertion over it, wants
its own ticket where the extruder can be reviewed as the substantial thing it is.

## The bug the tests found

Writing the deliberately-thin-support fixture — a child that all but fills its
parent, leaving a 0.15 mm land — exposed a real defect in my own `offset_rings`:

```
support   outer 400.000   hole -388.088     (a 0.15 mm annulus)
eroded    outer 384.162   hole -372.490     (still 0.15 mm wide)
```

A 0.2 mm erosion should have dissolved a 0.15 mm land completely. It did not,
because I added rings to Clipper one at a time. Clipper reads hole direction from
a ring's orientation, but only among rings offered **together**; added
separately, every ring becomes its own outer boundary and a hole shrinks when it
should grow. One `addPaths` call instead of a loop of `addPath`:

```
addPaths -> []      # correct: the land is gone
```

The consequence was not cosmetic. Erosion is how thin support is detected, so
every inspection of a body with a pocket or void was probing the wrong shape and
could not have reported a genuinely thin floor. All 360 pre-existing tests still
pass after the fix, so nothing else depended on the broken behaviour.

This is the third time in this project that a bug has surfaced only because a
fixture was built to be *hard* rather than representative — the same lesson as
#8's three-level glyph.

## Refining the thin-support classifier

The Spike Glyph initially reported two `thin_derived_support` findings on region
B. Both were false:

```
area 0.0114 mm² over a 10.9 mm run   ->  average width ~1 µm
area 0.0042 mm² over a 2.1 mm run    ->  average width ~2 µm
```

These are hairline slivers left along sloped edges by the offset round trip.
Spike 01 filtered that noise by **area**, which works for a short sliver; a long
one hugging a diagonal accumulates enough area to clear the floor, and then a
bounding-box test calls it thin support because it is long.

Average width — area over the longer bounding-box dimension — separates the two
by three orders of magnitude: noise measures microns across, a real feature
measures tenths of a millimetre. Ten microns as the threshold sits an order of
magnitude above the noise and an order of magnitude below anything a 0.4 mm
nozzle can build.

The glyph now reports 11 findings, all `corner_artifact`, zero defects — and the
thin-support fixture still reports its genuine one, which is what keeps the floor
honest rather than merely quiet.

## Design decisions

**Support is a strategy at a named point.** `SupportedChildStrategy` is the only
module that knows a parent stays solid beneath its children. A stand-in
island-insert strategy in the tests keeps the hole open and cuts no pocket —
the opposite choice on both counts — and needs no change to `FabricationBody`,
`Pocket` or `BodyFootprint`. That is the property Andy asked to protect after #8.

**Refusals are raised at the strategy boundary.** Artwork that is canonically
valid can be unbuildable *under this strategy*: a child close enough to a genuine
void that its clearance pushes the recess into it turns a blind pocket into an
opening. The message names the strategy, so it reads as a consequence of the
choice rather than a defect in the artwork.

**Clearance never touches canonical geometry.** `layercake.geometry.polygons`
still has no offset. A structural guard parses every module under
`layercake/canonical` and `layercake/geometry` and fails on an import of
`fabrication`, an import of `offset_rings`/`dilate`/`erode`, or a call to any of
them — parsed rather than grepped, so prose mentioning offset does not trip it
and an alias does not slip past.

**Z arithmetic is named quantities.** `level_top_mm`, `body_z_extent`,
`floor_beneath_pocket_mm`, `check_floor_is_sound`. A level's placement depends
only on the level, so siblings get identical Z whoever their parents are and peer
order — which exists only for reproducibility — can never become physical.

**Pockets come from the child's outer footprint.** The #8 discovery, guarded here
at the level that actually produces the geometry.

## The regression anchor

`test_spike_glyph_reproduces_the_spike_02_stack` checks the product's Z model
against the spike's own `z_planes`, which was written independently and validated
on a physical print — not against numbers transcribed from it. If either
implementation drifts, it fails.

One honest caveat, stated in the test: it is run at the **Spike 02 profile**, not
today's defaults. Session 01 deliberately moved backing (0.8 → 1.2) and seating
depth (0.2 → 0.80), so the current defaults produce 1.2 / 2.0 / 2.8 rather than
the printed 0.8 / 1.6 / 2.4, and should. What carried forward is the arithmetic,
not the numbers; the test states the printed profile explicitly and reproduces
the printed stack exactly.

## Result

365 tests pass, 43 of them new. Both spike pipelines unchanged and still PASS.
Nothing beyond #9 pulled forward.
