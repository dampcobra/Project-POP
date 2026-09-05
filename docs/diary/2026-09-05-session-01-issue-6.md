# Development diary — 2026-09-05 — Session 01, issue #6

**Branch:** `feat/6-canonical-artwork-model`
**Ticket:** #6 — Canonical artwork model: fabrication-free, Z-free and colour-count agnostic

## What this is

`layercake.canonical` — a set of coloured 2D regions and the containment between
them, carrying no Z, no thickness, no clearance, no seating depth and no backing.

Spike 01's two load-bearing invariants carry over unchanged: rings interned
through one vertex table, and an undirected edge keyed on its sorted index pair
so a shared boundary is one record naming both regions.

## Removing Z exposed a product question

Taking Z out of the model surfaced something the spike had never had to answer:

> Does a canonical region's area mean **this colour is visible here**, or **this
> colour's material is here**?

Spike 01 never chose. `Partition.containment()` filtered by Z band
(`topology.py:206`), skipping any pair in different bands — so the backing and
the foreground were never compared. Their shared footprint was invisible to
validation.

The Spike Glyph as authored turned out to use **both conventions at once**: the
foreground had a hole where the island sits (visible), while the backing had no
hole where the foreground sits (material). Under one consistent rule the second
case reports 902 mm² of overlap.

I stopped and brought it back rather than picking one, per the #6 brief. Before
doing so I tested the visible reading, because a recommendation with a number
behind it is more useful than a question:

```
visible areas:  backing 1534.0 + foreground 902.0 + island 64.0 = 2500.0
badge area                                                      = 2500.0
overlap 0.000   void 0.000
```

It tiles exactly.

## The decision

Andy and Elara chose **visible-surface semantics**, recorded as
[ADR 0003](../adr/0003-canonical-artwork-visible-surface-semantics.md), together
with a second product principle: canonical artwork represents **opaque** visible
colour, with no modelling of contribution through translucency or underlying
material.

That second point is worth having written down. ADR 0002 decision 2 already
assumed opaque material for the narrow case of an island covering its support;
ADR 0003 raises it to a product principle, so adding a translucency model would
supersede a decision rather than extend a feature.

## Consequences carried through

- The backing gains a hole where the foreground sits.
- **Shared edges 4 → 15.** Not a regression: the foreground's full 11-vertex
  boundary is now a genuine shared boundary with the backing, plus the island's
  4. The old count was an artefact of Z-band filtering.
- Issue #6's acceptance criterion was amended on the ticket itself, with the
  reasoning, so the board does not carry a criterion we knowingly cannot meet.
- The changed count is asserted explicitly, broken down by region pair, rather
  than left as a bare number.

## Design decisions

**Containment is a nesting tree, not a flat relation.** `parent_of` gives the
*smallest* enclosing region, so the Spike Glyph resolves to backing → foreground
→ island. `contains()` remains available for transitive questions, and
`containment_depth()` is exposed for #7 to build a stacking order on. Deriving
the order itself is that ticket's job and is not started here.

**The canonical polygon adapter has no offset operation at all.** Offsetting is
how a clearance is applied, so leaving the operation out means clearance cannot
leak into canonical without someone visibly adding it. There is a test asserting
its absence.

**Overlap is an error at any depth; void is legal and reported.** A visible
partition admits no overlap between ancestor and descendant either — which is
precisely what makes "material underneath" inexpressible canonically, as ADR 0003
decision 4 requires.

**A separate product-side geometry adapter.** `layercake/geometry/polygons.py`
duplicates a little of the spike's Clipper2 wrapper, because the product package
may not import the spike (#5). Same rationale Andy already endorsed for the
parameter copies: the spike records what was built, the product records what the
product does.

## Mistakes worth recording

My fabrication-word guard initially failed on `containment_depth` — matching a
bare `"depth"`. A false positive, but a useful one: it proved the guard was
actually looking. Narrowed to `seating_depth` / `recess_depth`, with a comment
saying why a bare `depth` is wrong.

## Result

242 tests pass, 32 of them new. Both spike pipelines unchanged and still PASS.
Nothing from #7 pulled forward.
