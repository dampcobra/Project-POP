# Project-POP

Development codename for Layercake, a tool for converting images into limited-colour layered geometry suitable for multicolour 3D printing and other physical fabrication methods.

Currently in Session 0 — Product Definition & MVP.

## Spike 01 — Canonical topology and manifold STL export

An engineering spike ([Issue #1](https://github.com/dampcobra/Project-POP/issues/1))
de-risking the highest-risk assumption before any application architecture: that a
partitioned artwork can be represented with shared topology, cleaned for
manufacturability, extruded into independent registered colour bodies, and
exported as valid STL.

Not production code, and deliberately narrow: no UI, no raster import, no colour
quantisation, no typography, no variable relief.

### Running it

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"    # Windows
.venv/Scripts/python.exe -m pytest                     # 55 tests
.venv/Scripts/python.exe -m layercake_spike            # writes artefacts/
```

Exit code is 0 only if every pass criterion in Issue #1 holds.

### Artefacts

| File | What it is |
|---|---|
| `A_backing.stl`, `B_foreground.stl`, `C_island.stl` | Separate, co-registered bodies on a shared origin |
| `topology-dump.json` | Shared vertices, edges, adjacency, containment |
| `debug.svg` | Debug render with shared edges and reflex vertices highlighted |
| `cleanup-report.md` | Minimum-feature detection, threshold, and action taken |
| `validation-report.md` | Per-body manifold validation, with tool coverage limits |
| `spike-summary.json` | Machine-readable pass/fail against Issue #1's criteria |

## Spike 02 — Shallow registration recesses (layered relief)

[Issue #3](https://github.com/dampcobra/Project-POP/issues/3). Replaces the
construction Spike 01 physically rejected with **layered relief**: each colour
body seats from above into a shallow registration recess in the colour below it.

```bash
.venv/Scripts/python.exe -m layercake_spike.spike02   # writes artefacts/spike02/
```

Produces a labelled FDM coupon testing three per-side clearances against two
recess depths, plus concave and radiused-corner shape controls and a
representative white → red → yellow three-level stack. See
[`docs/spike-02/notes.md`](docs/spike-02/notes.md) and
[ADR 0002](docs/adr/0002-layered-relief-registration-recesses.md).

### Documentation

- [`docs/adr/`](docs/adr) — architecture decision records
- [`docs/spike-01/geometry-spec.md`](docs/spike-01/geometry-spec.md) — exact mm coordinates
- [`docs/spike-01/conclusion.md`](docs/spike-01/conclusion.md) — verdict, architectural implications, stated limitations
- [`docs/diary/`](docs/diary) — development diary

### Stack

Python 3.13 · Clipper2 2.0.1 via `pyclipr` (booleans, offsets, containment) ·
`mapbox-earcut` (triangulation) · `trimesh` (mesh validation and STL export) ·
`shapely` (test assertions only).

Python was chosen for spike velocity and **does not commit the final Layercake
application stack**.
