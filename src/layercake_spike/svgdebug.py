"""Debug SVG render of a partition.

Purpose is inspection, not presentation. Shared edges are drawn in a
contrasting colour on top of the region outlines, so a gap or an overlap shows
up as a boundary that is drawn once instead of twice. Reflex vertices are
ringed so the concave notch can be checked at a glance.

The numeric gap/overlap check in `Partition.validate_band` remains the actual
pass criterion -- Issue #1 is explicit that visual inspection alone is not
enough. This render is how a human confirms the numbers describe the shape
they expected.
"""

from __future__ import annotations

from pathlib import Path

from . import spec
from .topology import Partition

Ring = list[tuple[float, float]]

_MARGIN_MM = 5.0
_PX_PER_MM = 12.0

# Distinct hues; the palette is indexed by position, so a fourth colour needs
# no code change.
_FILLS = ["#dfe6ee", "#f3c9a4", "#9fd3c7", "#c9a4f3", "#f3a4c1"]
_STROKES = ["#5b6b7f", "#b3652a", "#2f7d6c", "#6b2fb3", "#b32f63"]


def _reflex_vertices(ring: Ring) -> list[tuple[float, float]]:
    out = []
    for i, cur in enumerate(ring):
        prv, nxt = ring[i - 1], ring[(i + 1) % len(ring)]
        cross = (cur[0] - prv[0]) * (nxt[1] - cur[1]) - (cur[1] - prv[1]) * (
            nxt[0] - cur[0]
        )
        if cross < 0:
            out.append(cur)
    return out


def render(partition: Partition, path: str | Path, *, highlight_shared: bool = True) -> str:
    """Write a debug SVG for `partition` and return the markup."""
    xs = [x for x, _ in partition.vertices.coords]
    ys = [y for _, y in partition.vertices.coords]
    x0, x1 = min(xs) - _MARGIN_MM, max(xs) + _MARGIN_MM
    y0, y1 = min(ys) - _MARGIN_MM, max(ys) + _MARGIN_MM
    w_mm, h_mm = x1 - x0, y1 - y0

    def sx(x: float) -> float:
        return (x - x0) * _PX_PER_MM

    def sy(y: float) -> float:
        return (y1 - y) * _PX_PER_MM  # flip: SVG y grows downward

    def d_of(ring: Ring) -> str:
        head = f"M {sx(ring[0][0]):.3f} {sy(ring[0][1]):.3f}"
        rest = " ".join(f"L {sx(x):.3f} {sy(y):.3f}" for x, y in ring[1:])
        return f"{head} {rest} Z"

    w_px, h_px = w_mm * _PX_PER_MM, h_mm * _PX_PER_MM
    out: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_px:.0f}" '
        f'height="{h_px:.0f}" viewBox="0 0 {w_px:.3f} {h_px:.3f}">',
        "<style>",
        "  .grid { stroke: #e2e2e2; stroke-width: 0.5; }",
        "  .grid-major { stroke: #c4c4c4; stroke-width: 1; }",
        "  .shared-edge { stroke: #d81b60; stroke-width: 3.5; stroke-linecap: round; }",
        "  .vertex { fill: #333; }",
        "  .reflex { fill: none; stroke: #d81b60; stroke-width: 1.6; }",
        "  text { font: 11px system-ui, sans-serif; fill: #333; }",
        "</style>",
        f'<rect width="{w_px:.3f}" height="{h_px:.3f}" fill="#ffffff"/>',
        "<g class=\"grid-layer\">",
    ]

    # 10 mm grid, heavier every 10 mm from the origin
    step = 10.0
    gx = step * (int(x0 // step))
    while gx <= x1:
        cls = "grid-major" if abs(gx % 50.0) < 1e-9 else "grid"
        out.append(
            f'<line class="{cls}" x1="{sx(gx):.3f}" y1="0" '
            f'x2="{sx(gx):.3f}" y2="{h_px:.3f}"/>'
        )
        gx += step
    gy = step * (int(y0 // step))
    while gy <= y1:
        cls = "grid-major" if abs(gy % 50.0) < 1e-9 else "grid"
        out.append(
            f'<line class="{cls}" x1="0" y1="{sy(gy):.3f}" '
            f'x2="{w_px:.3f}" y2="{sy(gy):.3f}"/>'
        )
        gy += step
    out.append("</g>")

    # Regions, back band first so the artwork band draws on top.
    order = sorted(partition.regions.values(), key=lambda r: (r.z_min, r.rid))
    for i, region in enumerate(order):
        fill = _FILLS[i % len(_FILLS)]
        stroke = _STROKES[i % len(_STROKES)]
        rings = [partition.vertices.ring_coords(region.outer)]
        rings += [partition.vertices.ring_coords(h) for h in region.holes]
        d = " ".join(d_of(r) for r in rings)
        out.append(
            f'<path data-region="{region.rid}" data-colour="{region.colour}" '
            f'data-z="{region.z_min}-{region.z_max}" d="{d}" fill="{fill}" '
            f'fill-opacity="0.75" fill-rule="evenodd" stroke="{stroke}" '
            f'stroke-width="1.4"/>'
        )

    # Shared edges on top, so a missing one is obvious.
    if highlight_shared:
        out.append('<g class="shared-edges">')
        for edge, regions in sorted(partition.shared_edges().items()):
            ax, ay = partition.vertices.coords[edge.a]
            bx, by = partition.vertices.coords[edge.b]
            out.append(
                f'<line class="shared-edge" data-regions="{",".join(regions)}" '
                f'x1="{sx(ax):.3f}" y1="{sy(ay):.3f}" '
                f'x2="{sx(bx):.3f}" y2="{sy(by):.3f}"/>'
            )
        out.append("</g>")

    # Vertices, with reflex ones ringed.
    out.append('<g class="vertices">')
    for x, y in partition.vertices.coords:
        out.append(f'<circle class="vertex" cx="{sx(x):.3f}" cy="{sy(y):.3f}" r="2"/>')
    for region in partition.regions.values():
        for ring in [region.outer, *region.holes]:
            for x, y in _reflex_vertices(partition.vertices.ring_coords(ring)):
                out.append(
                    f'<circle class="reflex" cx="{sx(x):.3f}" cy="{sy(y):.3f}" r="6"/>'
                )
    out.append("</g>")

    # Legend
    out.append(f'<g class="legend" transform="translate(8,{h_px - 8:.3f})">')
    out.append(
        '<text y="-52">Spike Glyph debug render &#8212; grid 10 mm, '
        "heavy lines 50 mm</text>"
    )
    for i, region in enumerate(order):
        out.append(
            f'<text y="{-38 + i * 14}">&#9632; {region.rid} '
            f"(colour {region.colour}, Z {region.z_min}–{region.z_max} mm)</text>"
        )
    out.append('<text y="4" fill="#d81b60">&#9632; shared edges / reflex vertices</text>')
    out.append("</g>")
    out.append("</svg>")

    svg = "\n".join(out) + "\n"
    Path(path).write_text(svg, encoding="utf-8")
    return svg
