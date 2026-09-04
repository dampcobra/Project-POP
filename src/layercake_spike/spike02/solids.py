"""Prisms carrying shallow top pockets and raised bosses, manifold by construction.

Spike 01 established that manifoldness is cheaper to build than to repair: emit
caps and walls from one shared index set so every boundary edge is traversed
exactly twice in opposite directions. This extends the same argument to the two
features Spike 02 needs.

The solid is::

    footprint x [0, t]
      minus  pocket_i x (t - d_i, t]      -- shallow registration recesses
      plus   boss_j   x (t, t + h_j]      -- raised label lettering

and its boundary is:

===========================  ==========================================
surface                      normal
===========================  ==========================================
bottom cap, footprint @ 0    -Z
outer walls, footprint       outward, 0 -> t
top cap, footprint - pockets - bosses @ t   +Z
pocket floor @ t - d         +Z   (top of the material under the pocket)
pocket walls                 into the pocket, t - d -> t
boss cap @ t + h             +Z
boss walls                   outward, t -> t + h
===========================  ==========================================

Count any ring edge: a footprint edge bounds the bottom cap and the outer wall at
z=0, and the top cap and the outer wall at z=t. A pocket edge bounds the top cap
and the pocket wall at z=t, and the pocket floor and the pocket wall at z=t-d. A
boss edge likewise. Two uses each, opposite orientation -- closed two-manifold.

Pockets and bosses must be disjoint from each other and contained in the
footprint. Rather than silently union overlapping features (which would produce
correct-looking geometry with a wrong pocket depth somewhere), overlaps are
rejected.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

import mapbox_earcut
import numpy as np
import trimesh

from .. import clipper
from ..extrude import _dedupe_closing_vertex, _oriented, _signed_area
from ..extrude import extrude as _extrude

Ring = list[tuple[float, float]]

_AREA_EPS = 1e-9

#: Coincidence tolerance for interning mesh vertices, matching Spike 01's EPS.
_VERTEX_EPS = 1e-6


class Pocket(NamedTuple):
    """A shallow recess cut `depth` mm down from the body's top surface."""

    ring: Ring
    depth: float


class Boss(NamedTuple):
    """Material raised `height` mm above the body's top surface.

    `holes` are voids through the raised material, needed for lettering: a
    seven-segment "0" encloses a rectangular void, and filling it in would make
    the glyph unreadable. A hole's floor is the body's own top surface.
    """

    ring: Ring
    height: float
    holes: tuple[Ring, ...] = ()


def _prepare(ring: Ring, *, ccw: bool) -> Ring:
    return _oriented(_dedupe_closing_vertex(ring), ccw=ccw)


def _triangulate(outer: Ring, holes: Sequence[Ring]) -> tuple[np.ndarray, np.ndarray]:
    """Earcut a polygon with holes; returns (points Nx2, triangles Mx3)."""
    points: list[tuple[float, float]] = list(outer)
    ring_ends: list[int] = [len(points)]
    for hole in holes:
        points.extend(hole)
        ring_ends.append(len(points))
    verts = np.asarray(points, dtype=np.float64)
    tris = mapbox_earcut.triangulate_float64(
        verts, np.asarray(ring_ends, dtype=np.uint32)
    )
    return verts, tris.reshape(-1, 3)


def _validate_features(
    footprint: Ring, thickness: float, pockets: Sequence[Pocket], bosses: Sequence[Boss]
) -> None:
    for p in pockets:
        if p.depth <= 0:
            raise ValueError(f"pocket depth must be positive, got {p.depth}")
        if p.depth >= thickness:
            raise ValueError(
                f"pocket depth {p.depth} would make a through-hole in a "
                f"{thickness} mm body; support must remain continuous"
            )
    for b in bosses:
        if b.height <= 0:
            raise ValueError(f"boss height must be positive, got {b.height}")
        for h in b.holes:
            outside = clipper.boolean_op([h], [b.ring], "difference")
            if abs(clipper.total_area(outside)) > _AREA_EPS:
                raise ValueError("boss hole is not fully contained inside its boss")

    features = [("pocket", p.ring) for p in pockets] + [("boss", b.ring) for b in bosses]

    for kind, ring in features:
        outside = clipper.boolean_op([ring], [footprint], "difference")
        if abs(clipper.total_area(outside)) > _AREA_EPS:
            raise ValueError(f"{kind} is not fully contained inside the footprint")

    for i, (kind_a, ring_a) in enumerate(features):
        for kind_b, ring_b in features[i + 1 :]:
            shared = clipper.boolean_op([ring_a], [ring_b], "intersection")
            if abs(clipper.total_area(shared)) > _AREA_EPS:
                raise ValueError(
                    f"{kind_a} and {kind_b} overlap; features must be disjoint so "
                    "each keeps the depth or height it was given"
                )


def extrude_stepped(
    footprint: Ring,
    thickness: float,
    pockets: Sequence[Pocket] = (),
    bosses: Sequence[Boss] = (),
) -> tuple[np.ndarray, np.ndarray]:
    """Extrude `footprint` to `thickness`, sinking `pockets` and raising `bosses`.

    Returns `(vertices Nx3, faces Mx3)` forming a closed, outward-oriented,
    two-manifold surface. Input winding is normalised, so callers need not care.
    """
    if thickness <= 0:
        raise ValueError(f"thickness must be positive, got {thickness}")

    footprint = _prepare(footprint, ccw=True)
    pockets = [Pocket(_prepare(p.ring, ccw=True), p.depth) for p in pockets]
    bosses = [
        Boss(
            _prepare(b.ring, ccw=True),
            b.height,
            tuple(_prepare(h, ccw=True) for h in b.holes),
        )
        for b in bosses
    ]

    _validate_features(footprint, thickness, pockets, bosses)

    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []

    # Caps and walls must reference the *same* vertex where they meet, or the
    # shared edge is duplicated and the surface is not closed. Interning on
    # position guarantees that without the caller tracking index ranges.
    index: dict[tuple[int, int, int], int] = {}

    def vid(x: float, y: float, z: float) -> int:
        key = (round(x / _VERTEX_EPS), round(y / _VERTEX_EPS), round(z / _VERTEX_EPS))
        got = index.get(key)
        if got is None:
            got = len(vertices)
            index[key] = got
            vertices.append((float(x), float(y), float(z)))
        return got

    def emit_cap(outer: Ring, holes: Sequence[Ring], z: float, up: bool) -> None:
        pts, tris = _triangulate(outer, [_prepare(h, ccw=False) for h in holes])
        ids = [vid(x, y, z) for x, y in pts]
        for a, b, c in tris:
            tri = (ids[int(a)], ids[int(b)], ids[int(c)])
            faces.append(tri if up else (tri[2], tri[1], tri[0]))

    def emit_wall(ring: Ring, z_lo: float, z_hi: float, outward: bool) -> None:
        """Wall between two Z planes. `outward` faces away from the ring interior."""
        lo = [vid(x, y, z_lo) for x, y in ring]
        hi = [vid(x, y, z_hi) for x, y in ring]
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            if outward:
                faces.append((lo[i], lo[j], hi[j]))
                faces.append((lo[i], hi[j], hi[i]))
            else:
                faces.append((lo[i], hi[j], lo[j]))
                faces.append((lo[i], hi[i], hi[j]))

    top_holes = [p.ring for p in pockets] + [b.ring for b in bosses]

    # bottom cap: normal -Z
    emit_cap(footprint, [], 0.0, up=False)
    # outer walls
    emit_wall(footprint, 0.0, thickness, outward=True)
    # top cap, with pockets and bosses removed: normal +Z
    emit_cap(footprint, top_holes, thickness, up=True)

    for p in pockets:
        floor = thickness - p.depth
        # the floor is the top of the material below the pocket, so it faces +Z
        emit_cap(p.ring, [], floor, up=True)
        # pocket walls face into the cavity, i.e. inward relative to the ring
        emit_wall(p.ring, floor, thickness, outward=False)

    for b in bosses:
        top = thickness + b.height
        # cap of the raised material, voids removed
        emit_cap(b.ring, list(b.holes), top, up=True)
        emit_wall(b.ring, thickness, top, outward=True)
        for hole in b.holes:
            # the void's floor is the body's own top surface, and its wall faces
            # into the void
            emit_cap(hole, [], thickness, up=True)
            emit_wall(hole, thickness, top, outward=False)

    verts = np.asarray(vertices, dtype=np.float64)
    tris = np.asarray(faces, dtype=np.int64)
    _assert_closed(tris)
    return verts, tris


def _assert_closed(faces: np.ndarray) -> None:
    """Refuse to return a surface that is not closed.

    The cap triangulator is an ear-clipper, not a *constrained* triangulator. It
    is free to merge collinear boundary segments -- and when two features in the
    same cap have collinear edges (every glyph on a shared text baseline does),
    it emits one long cap edge instead of the separate feature edges the walls
    were built from. Area comes out right, so the fault is invisible to an area
    check, but caps and walls no longer correspond and the surface is open.

    Rather than hand back geometry that only looks correct, fail here. Callers
    with collinear features should assemble those parts with a boolean union
    instead (see `union_all`).
    """
    if len(faces) == 0:
        raise ValueError("no faces generated")
    edges = np.sort(faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    bad = int((counts != 2).sum())
    if bad:
        raise ValueError(
            f"stepped extrusion produced {bad} non-manifold edge(s). This usually "
            "means two features in the same cap have collinear boundaries, which "
            "the ear-clipping triangulator may merge. Assemble those parts with "
            "union_all() instead."
        )


def footprint_area(ring: Ring) -> float:
    """Absolute area of a ring, for volume assertions and reports."""
    return abs(_signed_area(ring))


def prism(
    outer: Ring, z0: float, z1: float, holes: Sequence[Ring] = ()
) -> "trimesh.Trimesh":
    """A plain prism between two Z planes, optionally with through-holes."""
    v, f = _extrude(outer, [list(h) for h in holes], z0, z1)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def union_all(meshes: Sequence["trimesh.Trimesh"]) -> "trimesh.Trimesh":
    """Union meshes into one guaranteed-manifold solid.

    Used where a body cannot be built manifold-by-construction in one pass --
    label lettering, whose glyphs sit on a shared baseline and so present the
    collinear-boundary case `_assert_closed` refuses. manifold3d is a
    manifoldness-preserving boolean engine, so this is a guarantee rather than a
    repair pass: the result is verified by the project's own validator either way.
    """
    if not meshes:
        raise ValueError("nothing to union")
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(list(meshes), engine="manifold")
