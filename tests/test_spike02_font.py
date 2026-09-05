"""Tests for the coupon label font.

Disjointness is the load-bearing property: two raised features that merely touch
along an edge would put four faces on one mesh edge and break manifoldness.
"""

import math

import pytest
from shapely.geometry import Polygon

from layercake_spike.spike02 import font, params

ALPHABET = "0123456789CDS. "


def _polys(rings):
    return [Polygon(r, holes) for r, holes in rings]


def test_every_label_character_renders():
    for ch in ALPHABET:
        g = font.glyph(ch, 3.0, 0.8)
        assert g.advance > 0
        if ch != " ":
            assert g.rings, ch


def test_unknown_character_is_rejected_rather_than_silently_dropped():
    with pytest.raises(ValueError, match="not in the coupon label font"):
        font.glyph("Z", 3.0, 0.8)


def test_glyph_rings_are_valid_and_pairwise_disjoint():
    for ch in ALPHABET:
        polys = _polys(font.glyph(ch, 3.0, 0.8).rings)
        for p in polys:
            assert p.is_valid, ch
            assert p.area > 0, ch
        for i, a in enumerate(polys):
            for b in polys[i + 1 :]:
                assert a.intersection(b).area < 1e-12, ch


def test_zero_encloses_a_void_so_it_does_not_read_as_a_filled_block():
    rings = font.glyph("0", 3.0, 0.8).rings
    assert len(rings) == 1
    _, holes = rings[0]
    assert len(holes) == 1, "a seven-segment 0 must keep its centre void"


def test_eight_and_zero_are_distinguishable():
    zero = font.glyph("0", 3.0, 0.8)
    eight = font.glyph("8", 3.0, 0.8)
    zero_area = sum(Polygon(r, h).area for r, h in zero.rings)
    eight_area = sum(Polygon(r, h).area for r, h in eight.rings)
    assert eight_area > zero_area, "8 lights the middle bar, 0 does not"


def test_d_is_not_identical_to_zero():
    d = sum(Polygon(r, h).area for r, h in font.glyph("D", 3.0, 0.8).rings)
    z = sum(Polygon(r, h).area for r, h in font.glyph("0", 3.0, 0.8).rings)
    assert not math.isclose(d, z, rel_tol=1e-6)


def test_text_rings_never_touch_between_characters():
    polys = _polys(font.text_rings("C.05 D.20", 0.0, 0.0, 3.0, 0.8))
    for i, a in enumerate(polys):
        for b in polys[i + 1 :]:
            assert a.intersection(b).area < 1e-12
            assert not a.touches(b), "touching rings would break mesh manifoldness"


def test_text_scales_with_size_and_respects_stroke_width():
    x0, y0, x1, y1 = font.text_bounds("8", 0.0, 0.0, 3.0, 0.8)
    assert math.isclose(y1 - y0, 3.0, abs_tol=1e-9)
    x0b, y0b, x1b, y1b = font.text_bounds("8", 0.0, 0.0, 6.0, 0.8)
    assert math.isclose(y1b - y0b, 6.0, abs_tol=1e-9)
    assert (x1b - x0b) > (x1 - x0)


def test_stroke_width_is_two_extrusions_wide_at_the_coupon_setting():
    assert params.LABEL_STROKE_MM == 0.8  # 2 x 0.4 mm nozzle
    x0, _, x1, _ = font.text_bounds("1", 0.0, 0.0, params.LABEL_SIZE_MM, params.LABEL_STROKE_MM)
    assert math.isclose(x1 - x0, params.LABEL_STROKE_MM, abs_tol=1e-9)


def test_every_cell_label_renders_without_an_unknown_character():
    for cell in params.CELLS:
        rings = font.text_rings(cell.label, 0.0, 0.0, 3.0, 0.8)
        assert rings, cell.label


def test_text_is_placed_at_the_requested_origin():
    x0, y0, _, _ = font.text_bounds("8", 5.0, 7.0, 3.0, 0.8)
    assert math.isclose(x0, 5.0, abs_tol=1e-9)
    assert math.isclose(y0, 7.0, abs_tol=1e-9)
