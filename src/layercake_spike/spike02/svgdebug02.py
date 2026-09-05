"""Debug SVG: canonical seating footprints against derived recess boundaries.

The whole point of the fabrication-derivation layer is that canonical geometry is
exact and clearance lives only in derived geometry. This render puts the two
boundaries side by side so that separation is visible rather than merely
asserted -- the derived recess should stand off the canonical footprint by the
per-side clearance, everywhere, with no crossing.

The numeric checks remain the pass criterion; this is how a human confirms the
numbers describe the shape they expected.
"""

from __future__ import annotations

from pathlib import Path

Ring = list[tuple[float, float]]

_PX_PER_MM = 6.0
_MARGIN_MM = 6.0


def _bounds(rings: list[Ring]) -> tuple[float, float, float, float]:
    xs = [x for r in rings for x, _ in r]
    ys = [y for r in rings for _, y in r]
    return min(xs), min(ys), max(xs), max(ys)


def render_pairs(
    pairs: list[tuple[str, Ring, Ring, float]],
    path: str | Path,
    title: str = "Spike 02 - canonical footprint vs derived recess",
) -> str:
    """Render `(label, canonical, recess, clearance)` pairs and write an SVG."""
    rings = [r for _, c, r, _ in pairs for r in (c, r)]
    x0, y0, x1, y1 = _bounds(rings)
    x0 -= _MARGIN_MM
    y0 -= _MARGIN_MM * 2
    x1 += _MARGIN_MM
    y1 += _MARGIN_MM
    w_px = (x1 - x0) * _PX_PER_MM
    h_px = (y1 - y0) * _PX_PER_MM

    def sx(x: float) -> float:
        return (x - x0) * _PX_PER_MM

    def sy(y: float) -> float:
        return (y1 - y) * _PX_PER_MM

    def d_of(ring: Ring) -> str:
        head = f"M {sx(ring[0][0]):.3f} {sy(ring[0][1]):.3f}"
        rest = " ".join(f"L {sx(x):.3f} {sy(y):.3f}" for x, y in ring[1:])
        return f"{head} {rest} Z"

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_px:.0f}" '
        f'height="{h_px:.0f}" viewBox="0 0 {w_px:.3f} {h_px:.3f}">',
        "<style>",
        "  .canonical { fill: #f3c9a4; fill-opacity: .85; stroke: #b3652a; stroke-width: 1.2; }",
        "  .recess { fill: none; stroke: #d81b60; stroke-width: 1.6; stroke-dasharray: 5 3; }",
        "  text { font: 10px system-ui, sans-serif; fill: #333; }",
        "  .title { font-size: 13px; font-weight: 600; }",
        "</style>",
        f'<rect width="{w_px:.3f}" height="{h_px:.3f}" fill="#ffffff"/>',
        f'<text class="title" x="8" y="18">{title}</text>',
        '<text x="8" y="34">solid = canonical seating footprint &#183; '
        'dashed = derived recess (dilated by the per-side clearance)</text>',
    ]

    for label, canonical, recess, clearance in pairs:
        out.append(
            f'<path class="canonical" data-cell="{label}" d="{d_of(canonical)}"/>'
        )
        out.append(
            f'<path class="recess" data-cell="{label}" '
            f'data-clearance="{clearance}" d="{d_of(recess)}"/>'
        )
        cx0, cy0, _, _ = _bounds([canonical])
        out.append(
            f'<text x="{sx(cx0):.3f}" y="{sy(cy0) + 14:.3f}">{label} '
            f"(c={clearance:.2f} mm)</text>"
        )

    out.append("</svg>")
    svg = "\n".join(out) + "\n"
    Path(path).write_text(svg, encoding="utf-8")
    return svg
