# Per-body manifold validation report

| Body | Watertight | Winding | Volume test | Euler | Non-manifold edges | Self-intersections | Volume (mm3) | Faces | Pass |
|---|---|---|---|---|---|---|---|---|---|
| coupon_child_m_c005_d020 | True | True | True | 2 | 0 | 0 | 144.0000 | 12 | PASS |
| coupon_child_m_c005_d040 | True | True | True | 2 | 0 | 0 | 172.8000 | 12 | PASS |
| coupon_child_m_c010_d020 | True | True | True | 2 | 0 | 0 | 144.0000 | 12 | PASS |
| coupon_child_m_c010_d040 | True | True | True | 2 | 0 | 0 | 172.8000 | 12 | PASS |
| coupon_child_m_c020_d020 | True | True | True | 2 | 0 | 0 | 144.0000 | 12 | PASS |
| coupon_child_m_c020_d040 | True | True | True | 2 | 0 | 0 | 172.8000 | 12 | PASS |
| coupon_child_s_concave | True | True | True | 2 | 0 | 0 | 149.0000 | 28 | PASS |
| coupon_child_s_radiused | True | True | True | 2 | 0 | 0 | 140.5338 | 220 | PASS |
| coupon_fixture | True | True | True | 2 | 0 | 0 | 17513.4104 | 4704 | PASS |
| stack_red | True | True | True | 2 | 0 | 0 | 952.5537 | 264 | PASS |
| stack_white | True | True | True | 2 | 0 | 0 | 1803.8710 | 356 | PASS |
| stack_yellow | True | True | True | 2 | 0 | 0 | 64.0000 | 12 | PASS |

## Bounding boxes (shared origin)

| Body | X min..max | Y min..max | Z min..max |
|---|---|---|---|
| coupon_child_m_c005_d020 | 7.000..19.000 | 7.000..19.000 | 0.000..1.000 |
| coupon_child_m_c005_d040 | 115.000..127.000 | 7.000..19.000 | 0.000..1.200 |
| coupon_child_m_c010_d020 | 43.000..55.000 | 7.000..19.000 | 0.000..1.000 |
| coupon_child_m_c010_d040 | 7.000..19.000 | 35.000..47.000 | 0.000..1.200 |
| coupon_child_m_c020_d020 | 79.000..91.000 | 7.000..19.000 | 0.000..1.000 |
| coupon_child_m_c020_d040 | 43.000..55.000 | 35.000..47.000 | 0.000..1.200 |
| coupon_child_s_concave | 79.000..93.000 | 35.000..49.000 | 0.000..1.000 |
| coupon_child_s_radiused | 113.000..125.000 | 33.000..45.000 | 0.000..1.000 |
| coupon_fixture | 0.000..158.000 | 0.000..70.000 | 0.000..2.200 |
| stack_red | 8.000..44.000 | 6.000..40.000 | 0.600..1.600 |
| stack_white | 0.000..50.000 | 0.000..50.000 | 0.000..0.800 |
| stack_yellow | 14.000..22.000 | 12.000..20.000 | 1.400..2.400 |

## Tool coverage and limitations

- trimesh covers watertightness, winding consistency and Euler number. trimesh has no self-intersection test, so self-intersection here is measured by this project's own triangle-triangle checker, not by trimesh.
- Faces that only touch (coplanar contact or edge grazing) are not counted as self-intersections.
- The self-intersection checker is O(n^2) in its broad phase: adequate at spike scale, not a production algorithm.
- Interpenetration *between* separate bodies is not a mesh property and is checked in 2D by the partition band validation instead.
