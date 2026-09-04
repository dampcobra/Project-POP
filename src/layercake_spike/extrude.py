"""Turn a polygon-with-holes into a watertight prism.

Manifoldness is built in rather than repaired afterwards. Each boundary vertex
appears exactly twice in the mesh -- once on the bottom cap at `z0`, once on the
top cap at `z1` -- and the walls are generated from the same index set the caps
use. Every wall edge is therefore traversed exactly twice in opposite
directions, which is the condition for a closed two-manifold surface.

Winding convention: outer rings counter-clockwise, holes clockwise, both
normalised on input so callers do not have to care. With that convention the
same wall-quad formula produces outward-facing normals for outer rings and
inward-facing normals for holes, which is exactly right -- a hole's wall faces
into the cavity.
"""

from __future__ import annotations

import mapbox_earcut
import numpy as np

Ring = list[tuple[float, float]]


def _signed_area(ring: Ring) -> float:
    return 0.5 * sum(
        x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1])
    )


def _oriented(ring: Ring, *, ccw: bool) -> Ring:
    return list(ring) if (_signed_area(ring) > 0) == ccw else list(reversed(ring))


def _dedupe_closing_vertex(ring: Ring, eps: float = 1e-12) -> Ring:
    """Drop a repeated final vertex if the caller closed the ring explicitly."""
    if len(ring) >= 2 and abs(ring[0][0] - ring[-1][0]) < eps and abs(ring[0][1] - ring[-1][1]) < eps:
        return list(ring[:-1])
    return list(ring)


def triangulate(outer: Ring, holes: list[Ring]) -> tuple[np.ndarray, np.ndarray]:
    """Triangulate a polygon with holes. Returns (points Nx2, triangles Mx3).

    Uses earcut, which handles the reflex vertices of the V-notch and the
    island cavity without needing a constrained Delaunay triangulator.
    """
    outer = _oriented(_dedupe_closing_vertex(outer), ccw=True)
    holes = [_oriented(_dedupe_closing_vertex(h), ccw=False) for h in holes]

    points: list[tuple[float, float]] = list(outer)
    ring_ends: list[int] = [len(points)]
    for hole in holes:
        points.extend(hole)
        ring_ends.append(len(points))

    verts = np.asarray(points, dtype=np.float64)
    tris = mapbox_earcut.triangulate_float64(verts, np.asarray(ring_ends, dtype=np.uint32))
    return verts, tris.reshape(-1, 3)


def extrude(
    outer: Ring, holes: list[Ring], z0: float, z1: float
) -> tuple[np.ndarray, np.ndarray]:
    """Extrude a polygon-with-holes between `z0` and `z1`.

    Returns `(vertices Nx3, faces Mx3)` forming a closed, outward-oriented,
    two-manifold surface.
    """
    if z1 <= z0:
        raise ValueError(f"z1 ({z1}) must be above z0 ({z0})")

    points2d, cap_tris = triangulate(outer, holes)
    n = len(points2d)

    # Vertices 0..n-1 are the bottom cap, n..2n-1 the top cap, index-aligned.
    vertices = np.vstack(
        [
            np.column_stack([points2d, np.full(n, z0)]),
            np.column_stack([points2d, np.full(n, z1)]),
        ]
    )

    faces: list[tuple[int, int, int]] = []

    # Bottom cap: reversed winding so its normal points down (-Z).
    faces.extend((int(c), int(b), int(a)) for a, b, c in cap_tris)
    # Top cap: as triangulated, normal points up (+Z).
    faces.extend((int(a) + n, int(b) + n, int(c) + n) for a, b, c in cap_tris)

    # Walls, one quad per boundary edge, split into two triangles.
    # Ring vertices occupy contiguous index runs in the order triangulate()
    # laid them out, so the offsets can be recomputed the same way.
    rings = [_oriented(_dedupe_closing_vertex(outer), ccw=True)]
    rings += [_oriented(_dedupe_closing_vertex(h), ccw=False) for h in holes]

    start = 0
    for ring in rings:
        count = len(ring)
        for i in range(count):
            a = start + i
            b = start + (i + 1) % count
            # a,b bottom; a+n,b+n top. Wound so the normal faces out of the solid.
            faces.append((a, b, b + n))
            faces.append((a, b + n, a + n))
        start += count

    tris = np.asarray(faces, dtype=np.int64)
    _assert_closed(tris)
    return vertices, tris


def _assert_closed(faces: np.ndarray) -> None:
    """Refuse to return a surface that is not closed.

    Earcut is an ear-clipper, not a *constrained* triangulator: where two rings
    in the same cap have collinear boundaries it may merge their boundary
    segments. Area still comes out right, so the fault is invisible to an area
    check, but the caps no longer share edges with the walls and the surface is
    open. Spike 02 hit this with two holes whose side edges lined up.

    Watertightness is this module's whole promise, so it is checked rather than
    assumed.
    """
    edges = np.sort(faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    bad = int((counts != 2).sum())
    if bad:
        raise ValueError(
            f"extrusion produced {bad} non-manifold edge(s); this usually means "
            "two rings in the same cap have collinear boundaries, which the "
            "ear-clipping triangulator may merge"
        )
