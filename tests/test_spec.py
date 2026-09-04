"""The Spike Glyph specification asserts things about itself.

These tests exist so the coordinates in `spec.py` cannot drift away from the
properties Issue #1 requires them to have (reflex vertices, containment,
an undersized tab) without something going red.
"""

import math

from shapely.geometry import Polygon

from layercake_spike import spec


def _signed_area(ring):
    return 0.5 * sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1])
    )


def test_rings_are_ccw_and_simple():
    for name, ring in [
        ("B", spec.B_OUTER_RING),
        ("C", spec.C_RING),
        ("A", spec.BACKING_RING),
        ("tab", spec.TAB_RING),
    ]:
        assert _signed_area(ring) > 0, f"{name} must be counter-clockwise"
        assert Polygon(ring).is_valid, f"{name} must be a simple polygon"


def test_b_has_exactly_two_reflex_vertices():
    ring = spec.B_OUTER_RING
    reflex = []
    for i, cur in enumerate(ring):
        prv, nxt = ring[i - 1], ring[(i + 1) % len(ring)]
        cross = (cur[0] - prv[0]) * (nxt[1] - cur[1]) - (cur[1] - prv[1]) * (
            nxt[0] - cur[0]
        )
        if cross < 0:  # CCW ring => negative cross product is a reflex vertex
            reflex.append(cur)
    assert reflex == spec.B_REFLEX_VERTICES, reflex


def test_c_is_fully_enclosed_with_about_4mm_of_b_around_it():
    b, c = Polygon(spec.B_OUTER_RING), Polygon(spec.C_RING)
    assert b.contains(c)
    clearance = c.exterior.distance(b.exterior)
    assert 3.5 <= clearance <= 6.0, clearance


def test_tab_is_undersized_and_3mm_long():
    xs = [p[0] for p in spec.TAB_RING]
    ys = [p[1] for p in spec.TAB_RING]
    assert math.isclose(max(ys) - min(ys), 0.15, abs_tol=1e-9)  # width
    assert math.isclose(max(xs) - 44.0, 3.0, abs_tol=1e-9)  # protrusion beyond B
    assert max(ys) - min(ys) < spec.MIN_FEATURE_MM  # deliberately unmanufacturable


def test_bands_are_flat_mosaic_not_stacked():
    assert spec.Z_BACKING == (0.0, 0.8)
    assert spec.Z_ARTWORK == (0.8, 2.0)  # B and C share this band; C never sits on B
