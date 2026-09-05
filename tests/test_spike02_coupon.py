"""Tests for the labelled test coupon."""

import math

import pytest
from shapely.geometry import Polygon

from layercake_spike import validate
from layercake_spike.spike02 import coupon, params

RESULT = coupon.build_coupon()


def _reflex_count(ring):
    n = 0
    for i, cur in enumerate(ring):
        prv, nxt = ring[i - 1], ring[(i + 1) % len(ring)]
        cross = (cur[0] - prv[0]) * (nxt[1] - cur[1]) - (cur[1] - prv[1]) * (
            nxt[0] - cur[0]
        )
        if cross < 0:
            n += 1
    return n


def test_every_cell_is_placed():
    assert len(RESULT.placements) == len(params.CELLS) == 8
    assert set(RESULT.children) == {c.cell_id for c in params.CELLS}


def test_fixture_is_manifold_with_no_through_holes():
    r = validate.validate_mesh("coupon_fixture", RESULT.fixture_mesh)
    assert r.watertight and r.winding_consistent
    assert r.non_manifold_edges == 0
    assert r.self_intersections == 0
    assert RESULT.fixture_mesh.volume > 0


def test_every_child_is_manifold_and_h_plus_d_thick():
    for p in RESULT.placements:
        m = RESULT.children[p.cell.cell_id]
        r = validate.validate_mesh(p.cell.cell_id, m)
        assert r.watertight and r.non_manifold_edges == 0, p.cell.cell_id
        height = m.bounds[1][2] - m.bounds[0][2]
        assert math.isclose(
            height, params.H_VISIBLE_STEP_MM + p.cell.depth, abs_tol=1e-9
        ), p.cell.cell_id


def test_support_remains_continuous_under_every_recess():
    for f in RESULT.floor_reports:
        assert f.ok, f
        assert f.floor_mm >= 1.0, f  # thick fixture must not confound the fit test


def test_each_child_fits_its_recess_with_the_requested_clearance():
    for p in RESULT.placements:
        child, recess = Polygon(p.canonical_footprint), Polygon(p.recess)
        assert recess.contains(child), p.cell.cell_id
        assert math.isclose(
            p.outline["achieved_clearance_mm"], p.cell.clearance, abs_tol=1e-3
        ), p.cell.cell_id


def test_recesses_never_overlap_each_other():
    polys = [Polygon(p.recess) for p in RESULT.placements]
    for i, a in enumerate(polys):
        for b in polys[i + 1 :]:
            assert a.intersection(b).area < 1e-12


def test_derivation_leaves_canonical_shapes_untouched():
    assert coupon.SHAPES["simple"] == coupon.SIMPLE
    assert coupon.SIMPLE == [(0.0, 0.0), (12.0, 0.0), (12.0, 12.0), (0.0, 12.0)]


def test_concave_control_really_is_concave():
    assert _reflex_count(coupon.CONCAVE) >= 1


def test_radiused_control_has_no_sharp_corners():
    ring = coupon.RADIUSED
    worst = 0.0
    for i, cur in enumerate(ring):
        prv, nxt = ring[i - 1], ring[(i + 1) % len(ring)]
        v1 = (cur[0] - prv[0], cur[1] - prv[1])
        v2 = (nxt[0] - cur[0], nxt[1] - cur[1])
        a1 = math.atan2(v1[1], v1[0])
        a2 = math.atan2(v2[1], v2[0])
        turn = abs(math.degrees((a2 - a1 + math.pi) % (2 * math.pi) - math.pi))
        worst = max(worst, turn)
    assert worst < 30.0, f"radiused control still turns {worst:.1f} deg at a vertex"


def test_shape_controls_share_one_setting_so_shape_is_the_only_variable():
    controls = [p for p in RESULT.placements if p.cell.kind == "shape_control"]
    assert len({(p.cell.clearance, p.cell.depth) for p in controls}) == 1


def test_derived_support_inspection_reports_without_mutating():
    for f in RESULT.derived_feature_findings:
        assert f.action == "reported_only"
    # the fixture geometry itself is unchanged by inspection
    assert RESULT.fixture_mesh.is_watertight


def test_visible_support_outline_is_reported_per_cell():
    for p in RESULT.placements:
        assert p.outline["area_mm2"] > 0
        assert math.isclose(
            p.outline["nominal_clearance_mm"], p.cell.clearance, abs_tol=1e-12
        )


def test_coupon_fits_a_p1s_bed():
    x0, y0, x1, y1 = (
        min(p[0] for p in RESULT.fixture_footprint),
        min(p[1] for p in RESULT.fixture_footprint),
        max(p[0] for p in RESULT.fixture_footprint),
        max(p[1] for p in RESULT.fixture_footprint),
    )
    assert (x1 - x0) <= 250.0 and (y1 - y0) <= 250.0


def test_recess_corner_artefacts_are_not_reported_as_thin_support():
    """Opening flags internal corners tighter than its probe, not just thin runs.

    Recess corners are radiused by the clearance (0.05-0.20 mm), all tighter than
    the 0.2 mm probe, so every one trips the detector. Reporting them as defects
    would bury a real finding among dozens of harmless ones.
    """
    kinds = {f.kind for f in RESULT.derived_feature_findings}
    assert kinds <= {"corner_artifact", "thin_derived_support"}
    real = [f for f in RESULT.derived_feature_findings if f.kind == "thin_derived_support"]
    assert real == [], [f.detail for f in real]
