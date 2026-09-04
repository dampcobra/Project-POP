"""Per-body manifold validation.

What trimesh actually gives us
------------------------------
trimesh is the selected validation tool for this spike (Andy, Session 0). It
covers watertightness, winding consistency, the volume test and the Euler
number honestly and cheaply.

It does **not** detect self-intersections. There is no `is_self_intersecting`
or equivalent; `trimesh.repair` deals with holes, winding and normals, not
with faces that pass through one another. Issue #1 requires zero
self-intersections as a pass criterion, so leaving that box ticked on
trimesh's say-so would be reporting a check we never ran.

`self_intersections()` below is therefore our own implementation: an AABB
broad phase followed by an exact separating-axis narrow phase, skipping face
pairs that legitimately share a vertex. Every `MeshReport` carries a
`tool_notes` entry recording this split so no downstream reader mistakes it
for a trimesh result.

Limitations of our checker, stated plainly:

- It is O(n^2) in the broad phase. Fine for spike-scale meshes (thousands of
  faces), not for production meshes.
- Faces that merely touch -- coplanar contact, or an edge grazing another
  face -- are treated as non-intersecting. That is the right call for
  co-registered bodies whose walls meet exactly, but it means a genuine
  degenerate touch will not be flagged.
- It says nothing about whether two *separate* bodies interpenetrate. That is
  checked in the 2D partition validation instead (`Partition.validate_band`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import trimesh

TRIMESH_NOTE = (
    "trimesh covers watertightness, winding consistency and Euler number. "
    "trimesh has no self-intersection test, so self-intersection here is "
    "measured by this project's own triangle-triangle checker, not by trimesh."
)

TOUCHING_NOTE = (
    "Faces that only touch (coplanar contact or edge grazing) are not counted "
    "as self-intersections."
)


def _tri_intersects(t0: np.ndarray, t1: np.ndarray, eps: float = 1e-9) -> bool:
    """Exact separating-axis test for two triangles in 3D.

    Returns False when the triangles merely touch, which is what we want for
    walls that meet exactly at a shared boundary.
    """
    axes = []
    e0 = [t0[1] - t0[0], t0[2] - t0[1], t0[0] - t0[2]]
    e1 = [t1[1] - t1[0], t1[2] - t1[1], t1[0] - t1[2]]

    n0 = np.cross(e0[0], -e0[2])
    n1 = np.cross(e1[0], -e1[2])
    axes.append(n0)
    axes.append(n1)
    for a in e0:
        for b in e1:
            axes.append(np.cross(a, b))

    for axis in axes:
        norm = np.linalg.norm(axis)
        if norm < eps:
            continue  # degenerate axis, carries no separation information
        axis = axis / norm
        p0 = t0 @ axis
        p1 = t1 @ axis
        # Strict gap => separated. Touching (gap == 0) counts as separated.
        if p0.min() >= p1.max() - eps or p1.min() >= p0.max() - eps:
            return False
    return True


def self_intersections(mesh: trimesh.Trimesh, eps: float = 1e-9) -> list[tuple[int, int]]:
    """Face-index pairs whose triangles genuinely pass through each other.

    Our own implementation -- trimesh has no equivalent. Face pairs sharing a
    vertex are skipped, since neighbouring faces always touch by construction.
    """
    faces = np.asarray(mesh.faces)
    verts = np.asarray(mesh.vertices)
    if len(faces) == 0:
        return []

    tris = verts[faces]
    lows = tris.min(axis=1)
    highs = tris.max(axis=1)

    hits: list[tuple[int, int]] = []
    n = len(faces)
    for i in range(n):
        # broad phase: vectorised AABB overlap against all later faces
        j0 = i + 1
        if j0 >= n:
            break
        overlap = np.all(
            (lows[j0:] <= highs[i] + eps) & (highs[j0:] >= lows[i] - eps), axis=1
        )
        for offset in np.nonzero(overlap)[0]:
            j = j0 + int(offset)
            if set(faces[i]) & set(faces[j]):
                continue  # adjacent faces share a vertex: touching is expected
            if _tri_intersects(tris[i], tris[j], eps):
                hits.append((i, j))
    return hits


def non_manifold_edge_count(mesh: trimesh.Trimesh) -> int:
    """Edges not used by exactly two faces."""
    faces = np.asarray(mesh.faces)
    if len(faces) == 0:
        return 0
    edges = np.sort(faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int((counts != 2).sum())


@dataclass
class MeshReport:
    """Per-body manifold validation result, as required by Issue #1."""

    body: str
    watertight: bool
    winding_consistent: bool
    is_volume: bool
    euler_number: int
    non_manifold_edges: int
    self_intersections: int
    volume: float
    face_count: int
    vertex_count: int
    bounds: list[list[float]]
    tool_notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.watertight
            and self.winding_consistent
            and self.non_manifold_edges == 0
            and self.self_intersections == 0
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ok"] = self.ok
        return d


def validate_mesh(name: str, mesh: trimesh.Trimesh) -> MeshReport:
    """Audit one body. See the module docstring for what each tool covers."""
    return MeshReport(
        body=name,
        watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),
        is_volume=bool(mesh.is_volume),
        euler_number=int(mesh.euler_number),
        non_manifold_edges=non_manifold_edge_count(mesh),
        self_intersections=len(self_intersections(mesh)),
        volume=float(mesh.volume),
        face_count=int(len(mesh.faces)),
        vertex_count=int(len(mesh.vertices)),
        bounds=[[float(v) for v in row] for row in mesh.bounds],
        tool_notes=[TRIMESH_NOTE, TOUCHING_NOTE],
    )


def reports_to_markdown(reports: list[MeshReport]) -> str:
    """Render the per-body manifold validation report artefact."""
    lines = [
        "# Per-body manifold validation report",
        "",
        "| Body | Watertight | Winding | Volume test | Euler | Non-manifold edges | "
        "Self-intersections | Volume (mm3) | Faces | Pass |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in reports:
        lines.append(
            f"| {r.body} | {r.watertight} | {r.winding_consistent} | {r.is_volume} | "
            f"{r.euler_number} | {r.non_manifold_edges} | {r.self_intersections} | "
            f"{r.volume:.4f} | {r.face_count} | {'PASS' if r.ok else 'FAIL'} |"
        )
    lines += [
        "",
        "## Bounding boxes (shared origin)",
        "",
        "| Body | X min..max | Y min..max | Z min..max |",
        "|---|---|---|---|",
    ]
    for r in reports:
        (x0, y0, z0), (x1, y1, z1) = r.bounds
        lines.append(
            f"| {r.body} | {x0:.3f}..{x1:.3f} | {y0:.3f}..{y1:.3f} | {z0:.3f}..{z1:.3f} |"
        )
    lines += [
        "",
        "## Tool coverage and limitations",
        "",
        f"- {TRIMESH_NOTE}",
        f"- {TOUCHING_NOTE}",
        "- The self-intersection checker is O(n^2) in its broad phase: adequate at "
        "spike scale, not a production algorithm.",
        "- Interpenetration *between* separate bodies is not a mesh property and is "
        "checked in 2D by the partition band validation instead.",
    ]
    return "\n".join(lines) + "\n"
