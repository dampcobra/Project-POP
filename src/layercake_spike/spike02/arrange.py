"""Two arrangements of the same bodies: one to inspect, one to print.

The co-registered assembly places every body at its true assembly Z, which is
what you want in a slicer to check registration and step heights. It is not
printable: children sit inside their recesses, well above the plate.

The plate layout drops every body to Z=0 and shelf-packs them so nothing
overlaps, which is what you want to actually print the coupon and its loose
pieces.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import trimesh

#: Gap left between parts on the plate, in mm.
PLATE_GAP_MM = 6.0

#: Usable bed for the validation printer (Bambu P1S is 256 mm square). Used only
#: to warn if the layout will not fit; nothing here is printer-specific.
BED_MM = 256.0


@dataclass
class Placement:
    name: str
    dx: float
    dy: float
    dz: float


def translated(mesh: trimesh.Trimesh, dx: float, dy: float, dz: float) -> trimesh.Trimesh:
    """A copy of `mesh` moved by the given offset."""
    v = np.asarray(mesh.vertices).copy()
    v[:, 0] += dx
    v[:, 1] += dy
    v[:, 2] += dz
    return trimesh.Trimesh(vertices=v, faces=np.asarray(mesh.faces).copy(), process=False)


def assembly(bodies: dict[str, trimesh.Trimesh]) -> trimesh.Trimesh:
    """Every body at its true assembly position, concatenated for inspection."""
    return trimesh.util.concatenate(list(bodies.values()))


def plate_layout(
    bodies: dict[str, trimesh.Trimesh], gap: float = PLATE_GAP_MM
) -> tuple[trimesh.Trimesh, list[Placement]]:
    """Shelf-pack bodies onto the plate at Z=0, largest first.

    Returns the concatenated layout and the placement of each body, so the report
    can tell Andy where each piece is.
    """
    order = sorted(
        bodies.items(),
        key=lambda kv: -(kv[1].bounds[1][1] - kv[1].bounds[0][1]),
    )

    placements: list[Placement] = []
    laid: list[trimesh.Trimesh] = []

    cursor_x, shelf_y, shelf_h = gap, gap, 0.0
    for name, mesh in order:
        lo, hi = mesh.bounds
        w, h = hi[0] - lo[0], hi[1] - lo[1]
        if cursor_x + w + gap > BED_MM and laid:
            cursor_x = gap
            shelf_y += shelf_h + gap
            shelf_h = 0.0
        dx = cursor_x - lo[0]
        dy = shelf_y - lo[1]
        dz = -lo[2]  # drop to the plate
        laid.append(translated(mesh, dx, dy, dz))
        placements.append(Placement(name, dx, dy, dz))
        cursor_x += w + gap
        shelf_h = max(shelf_h, h)

    return trimesh.util.concatenate(laid), placements


def layout_extent(mesh: trimesh.Trimesh) -> tuple[float, float]:
    lo, hi = mesh.bounds
    return float(hi[0] - lo[0]), float(hi[1] - lo[1])
