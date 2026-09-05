# Per-body manifold validation report

| Body | Watertight | Winding | Volume test | Euler | Non-manifold edges | Self-intersections | Volume (mm3) | Faces | Pass |
|---|---|---|---|---|---|---|---|---|---|
| depth_child_d040_r1 | True | True | True | 2 | 0 | 0 | 171.7760 | 28 | PASS |
| depth_child_d040_r2 | True | True | True | 2 | 0 | 0 | 171.7760 | 28 | PASS |
| depth_child_d040_r3 | True | True | True | 2 | 0 | 0 | 171.7760 | 28 | PASS |
| depth_child_d060_r1 | True | True | True | 2 | 0 | 0 | 199.5520 | 44 | PASS |
| depth_child_d060_r2 | True | True | True | 2 | 0 | 0 | 199.5520 | 44 | PASS |
| depth_child_d060_r3 | True | True | True | 2 | 0 | 0 | 199.5520 | 44 | PASS |
| depth_child_d080_r1 | True | True | True | 2 | 0 | 0 | 227.3280 | 60 | PASS |
| depth_child_d080_r2 | True | True | True | 2 | 0 | 0 | 227.3280 | 60 | PASS |
| depth_child_d080_r3 | True | True | True | 2 | 0 | 0 | 227.3280 | 60 | PASS |
| depth_child_d100_r1 | True | True | True | 2 | 0 | 0 | 255.1040 | 76 | PASS |
| depth_child_d100_r2 | True | True | True | 2 | 0 | 0 | 255.1040 | 76 | PASS |
| depth_child_d100_r3 | True | True | True | 2 | 0 | 0 | 255.1040 | 76 | PASS |
| depth_followup_fixture | True | True | True | 2 | 0 | 0 | 7904.9601 | 2776 | PASS |

## Bounding boxes (shared origin)

| Body | X min..max | Y min..max | Z min..max |
|---|---|---|---|
| depth_child_d040_r1 | 0.000..12.000 | 0.000..12.000 | 0.000..1.200 |
| depth_child_d040_r2 | 0.000..12.000 | 0.000..12.000 | 0.000..1.200 |
| depth_child_d040_r3 | 0.000..12.000 | 0.000..12.000 | 0.000..1.200 |
| depth_child_d060_r1 | 0.000..12.000 | 0.000..12.000 | 0.000..1.400 |
| depth_child_d060_r2 | 0.000..12.000 | 0.000..12.000 | 0.000..1.400 |
| depth_child_d060_r3 | 0.000..12.000 | 0.000..12.000 | 0.000..1.400 |
| depth_child_d080_r1 | 0.000..12.000 | 0.000..12.000 | 0.000..1.600 |
| depth_child_d080_r2 | 0.000..12.000 | 0.000..12.000 | 0.000..1.600 |
| depth_child_d080_r3 | 0.000..12.000 | 0.000..12.000 | 0.000..1.600 |
| depth_child_d100_r1 | 0.000..12.000 | 0.000..12.000 | 0.000..1.800 |
| depth_child_d100_r2 | 0.000..12.000 | 0.000..12.000 | 0.000..1.800 |
| depth_child_d100_r3 | 0.000..12.000 | 0.000..12.000 | 0.000..1.800 |
| depth_followup_fixture | 0.000..158.000 | 0.000..32.600 | 0.000..2.200 |

## Tool coverage and limitations

- trimesh covers watertightness, winding consistency and Euler number. trimesh has no self-intersection test, so self-intersection here is measured by this project's own triangle-triangle checker, not by trimesh.
- Faces that only touch (coplanar contact or edge grazing) are not counted as self-intersections.
- The self-intersection checker is O(n^2) in its broad phase: adequate at spike scale, not a production algorithm.
- Interpenetration *between* separate bodies is not a mesh property and is checked in 2D by the partition band validation instead.
