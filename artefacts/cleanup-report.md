# Manufacturability cleanup report

- **Minimum feature width:** 0.4 mm (0.4 mm nozzle assumption, not yet physically validated)
- **Detection method:** morphological opening at radius 0.2 mm (Clipper2 miter offset)
- **Reporting floor:** 0.001 mm2 -- below this a sliver is offset round-trip noise, not a feature
- **Policy:** detect, report, and remove deterministically before mesh generation

## Findings

| Region | Kind | Area (mm2) | Action | Detail |
|---|---|---|---|---|
| B | thin_feature | 0.4500 | removed | feature thinner than 0.4 mm at x 44.000..47.000, y 15.425..15.575 |

## Shared-boundary safety

Cleanup opens each region's **outer** ring only, then re-cuts holes
from the authoritative region geometry. A naive opening would also
erode shared boundaries, moving one region's copy of a boundary
while its neighbour's stayed put. See `cleanup.py` for detail.
