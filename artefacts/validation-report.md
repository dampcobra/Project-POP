# Per-body manifold validation report

| Body | Watertight | Winding | Volume test | Euler | Non-manifold edges | Self-intersections | Volume (mm3) | Faces | Pass |
|---|---|---|---|---|---|---|---|---|---|
| A | True | True | True | 2 | 0 | 0 | 2000.0000 | 12 | PASS |
| B | True | True | True | 0 | 0 | 0 | 1082.4000 | 60 | PASS |
| C | True | True | True | 2 | 0 | 0 | 76.8000 | 12 | PASS |

## Bounding boxes (shared origin)

| Body | X min..max | Y min..max | Z min..max |
|---|---|---|---|
| A | 0.000..50.000 | 0.000..50.000 | 0.000..0.800 |
| B | 8.000..44.000 | 6.000..40.000 | 0.800..2.000 |
| C | 14.000..22.000 | 12.000..20.000 | 0.800..2.000 |

## Tool coverage and limitations

- trimesh covers watertightness, winding consistency and Euler number. trimesh has no self-intersection test, so self-intersection here is measured by this project's own triangle-triangle checker, not by trimesh.
- Faces that only touch (coplanar contact or edge grazing) are not counted as self-intersections.
- The self-intersection checker is O(n^2) in its broad phase: adequate at spike scale, not a production algorithm.
- Interpenetration *between* separate bodies is not a mesh property and is checked in 2D by the partition band validation instead.
