# Spike 01 — Exact geometry specification ("Spike Glyph")

Required artefact for [Issue #1](https://github.com/dampcobra/Project-POP/issues/1).

All coordinates are **exact vector coordinates in millimetres**, authored directly.
Nothing here is derived from a raster image, and no image processing is involved
at any point in the pipeline.

The authoritative machine-readable copy is `src/layercake_spike/spec.py`; this
document and that module are kept in step by `tests/test_spec.py`, which asserts
the properties claimed below rather than trusting them.

## Origin and registration

Model origin `(0, 0, 0)` is the badge's bottom-left corner at the underside of
the backing. **Every exported body uses this origin and is never translated**, so
co-registration is a property of the pipeline rather than a post-export
correction. Bodies are exported as separate STL files intended to be imported
together at the same origin.

## Z bands

| Band | Z min | Z max | Thickness | Contents |
|---|---|---|---|---|
| Backing | 0.0 | 0.8 | 0.8 mm | Colour A |
| Artwork | 0.8 | 2.0 | 1.2 mm | Colours B and C |

MVP geometry is flat mosaic/inlay: there is exactly one artwork band, no
variable relief and no height-map behaviour. B and C occupy the *same* band —
C is a hole in B, never a layer stacked on top of it.

## Colour A — structural backing

Continuous 50 × 50 mm footprint, Z 0.0 → 0.8 mm.

| # | x | y |
|---|---|---|
| 1 | 0.0 | 0.0 |
| 2 | 50.0 | 0.0 |
| 3 | 50.0 | 50.0 |
| 4 | 0.0 | 50.0 |

A is treated as a structural concept, independent of the visible artwork
colours, even though a future workflow might reuse the same physical filament.

## Colour B — foreground region

Irregular polygon registered to the backing, Z 0.8 → 2.0 mm. Counter-clockwise,
no repeated closing vertex.

| # | x | y | Note |
|---|---|---|---|
| 1 | 8.0 | 8.0 | |
| 2 | 41.0 | 6.0 | |
| 3 | 44.0 | 14.0 | |
| 4 | 44.0 | 17.0 | vertical run — exact anchor for the undersized tab |
| 5 | 42.0 | 30.0 | |
| 6 | 38.0 | 40.0 | |
| 7 | 30.0 | 40.0 | notch shoulder (convex) |
| 8 | 26.0 | 26.0 | **reflex** — notch apex, right corner |
| 9 | 24.0 | 26.0 | **reflex** — notch apex, left corner |
| 10 | 20.0 | 40.0 | notch shoulder (convex) |
| 11 | 12.0 | 38.0 | |

Area 966.000 mm². Contains one hole: colour C.

### Note on the reflex-vertex count

Issue #1 asks for "a V-shaped concave notch with **two** reflex vertices". A
geometrically pure V cut into a straight edge produces exactly **one** reflex
vertex — the apex. Both shoulders are necessarily convex: making a shoulder
reflex would require the boundary to turn clockwise there, meaning the material
overhangs the notch, which is neither intended nor printable.

The apex is therefore truncated with a 2 mm flat between (26,26) and (24,26).
This reads unmistakably as a V, stays printable, and delivers the two reflex
vertices the issue calls for. Both are asserted by
`test_b_has_exactly_two_reflex_vertices`.

## Colour C — enclosed island

8 × 8 mm square, fully enclosed within B, Z 0.8 → 2.0 mm.

| # | x | y |
|---|---|---|
| 1 | 14.0 | 12.0 |
| 2 | 22.0 | 12.0 |
| 3 | 22.0 | 20.0 |
| 4 | 14.0 | 20.0 |

Area 64.000 mm². Minimum clearance to B's outer boundary is **4.355644 mm**
(the "approximately 4 mm of B around it" the issue asks for), measured at the
lower-left corner.

C occupies a literal hole in B across the whole artwork band and is exported as
an independent solid body on the shared origin. It is anchored by resting on
the backing over 100 % of its 64 mm² footprint.

## Deliberately undersized feature

Axis-aligned tab, unioned into B **before** cleanup runs so the cleanup stage
has something real to detect.

| # | x | y |
|---|---|---|
| 1 | 43.5 | 15.425 |
| 2 | 47.0 | 15.425 |
| 3 | 47.0 | 15.575 |
| 4 | 43.5 | 15.575 |

- Width **0.150 mm** — below the 0.4 mm nozzle assumption, so unmanufacturable.
- Protrudes **3.000 mm** beyond B's `x = 44.0` edge.
- Overlaps 0.5 mm into B so the union is numerically robust.

This feature is expected to be **detected and removed**, never to reach an STL.

## Tolerances

| Name | Value | Purpose |
|---|---|---|
| `EPS` | 1e-6 mm | Vertex coincidence / snapping; gap and overlap tolerance |
| `CLIPPER_SCALE` | 1e6 | Clipper2 integer grid — 1e-6 mm resolution, matching `EPS` |
| `MIN_FEATURE_MM` | 0.4 mm | Minimum manufacturable width (0.4 mm nozzle assumption) |
| `SLIVER_AREA_EPS_MM2` | 1e-3 mm² | Floor below which a cleanup sliver is offset round-trip noise |

`SLIVER_AREA_EPS_MM2` is deliberately separate from `EPS`: one is a length, the
other an area. An offset round trip on the 1e-6 mm grid sheds roughly 1e-4 mm²
of spurious area from a ring of this perimeter, so the floor sits an order of
magnitude above that noise and about 450× below the 0.45 mm² test tab.

## Derived quantities (asserted by tests)

| Quantity | Value |
|---|---|
| A volume | 2000.000 mm³ |
| B volume (island excluded) | 1082.400 mm³ |
| C volume | 76.800 mm³ |
| B outer area before cleanup (with tab) | 966.450 mm² |
| B outer area after cleanup | 965.999993 mm² |
| Area removed by cleanup | 0.450 mm² (= 0.15 × 3.0) |
| Shared edges between B and C | 4 |
