"""Tests for fabrication derivation.

The load-bearing assertions here are that derivation never mutates canonical
geometry, and that a canonical hole becomes a *filled* support with a shallow
pocket -- the architectural decision recorded in ADR 0002.
"""

import copy
import math

import pytest
from shapely.geometry import Point, Polygon

from layercake_spike import spec
from layercake_spike.spike02 import fabricate, params

SQ10 = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


#: Clipper2 approximates each corner arc with chords, so the achieved separation
#: falls a sagitta short of nominal -- about 0.4 um at these radii. That is ~1000x
#: finer than a 0.4 mm nozzle and 100x finer than the smallest clearance under
#: test, so it is reported rather than chased. Tightening arcTolerance to remove
#: it costs ~7500 vertices per corner set, which is not a usable mesh.
ARC_TOL_MM = 1e-3


def test_recess_is_larger_than_the_child_by_the_requested_per_side_clearance():
    for c in params.CLEARANCES_MM:
        recess = fabricate.derive_recess(SQ10, c)
        child_p, recess_p = Polygon(SQ10), Polygon(recess)
        assert recess_p.contains(child_p)
        # round join gives a true radial dilation: separation is c everywhere
        gap = child_p.exterior.distance(recess_p.exterior)
        assert math.isclose(gap, c, abs_tol=ARC_TOL_MM), (c, gap)


def test_round_join_radiuses_recess_corners_rather_than_mitring_them():
    c = 0.20
    recess = fabricate.derive_recess(SQ10, c)
    # a mitred square would stay 4 vertices; a radial dilation rounds the corners
    assert len(recess) > 8
    # no recess vertex is further from the child than c -- a mitre would spike to
    # c*sqrt(2) on the diagonal, handing out more clearance than was asked for
    child = Polygon(SQ10)
    worst = max(child.exterior.distance(Point(p)) for p in recess)
    assert worst <= c + ARC_TOL_MM, worst


def test_achieved_clearance_is_reported_not_assumed():
    c = 0.20
    recess = fabricate.derive_recess(SQ10, c)
    outline = fabricate.visible_outline(SQ10, recess, nominal_clearance=c)
    assert outline["nominal_clearance_mm"] == c
    assert outline["achieved_clearance_mm"] <= c
    assert math.isclose(outline["achieved_clearance_mm"], c, abs_tol=ARC_TOL_MM)


def test_derivation_does_not_mutate_the_canonical_child():
    original = copy.deepcopy(SQ10)
    fabricate.derive_recess(SQ10, 0.2)
    assert SQ10 == original


def test_z_planes_reproduce_the_intended_three_level_result():
    for d in params.DEPTHS_MM:
        # the as-printed round-1 backing, so this pins the known-good result
        white_top = params.ROUND1_AS_PRINTED_BACKING_MM
        red = fabricate.z_planes(white_top, d)
        yellow = fabricate.z_planes(red.child_top, d)
        assert math.isclose(white_top, 0.8, abs_tol=1e-12)
        assert math.isclose(red.child_top, 1.6, abs_tol=1e-12)
        assert math.isclose(yellow.child_top, 2.4, abs_tol=1e-12)
        # completed tops are invariant in D; only the seating changes
        assert math.isclose(red.recess_floor, 0.8 - d, abs_tol=1e-12)
        assert math.isclose(red.child_bottom, red.recess_floor, abs_tol=1e-12)
        assert math.isclose(red.child_thickness, 0.8 + d, abs_tol=1e-12)


def test_solidify_support_discards_the_canonical_hole():
    """ADR 0002: canonical containment does not require a fabrication through-hole."""
    outer, holes = fabricate.solidify_support(spec.B_OUTER_RING, [spec.C_RING])
    assert holes == [], "the canonical hole must be filled in fabrication geometry"
    assert math.isclose(
        abs(fabricate.ring_area(outer)), abs(fabricate.ring_area(spec.B_OUTER_RING)),
        abs_tol=1e-9,
    )


def test_solidify_support_leaves_canonical_geometry_untouched():
    before_outer = copy.deepcopy(spec.B_OUTER_RING)
    before_hole = copy.deepcopy(spec.C_RING)
    fabricate.solidify_support(spec.B_OUTER_RING, [spec.C_RING])
    assert spec.B_OUTER_RING == before_outer
    assert spec.C_RING == before_hole


def test_floor_check_accepts_a_shallow_pocket_and_rejects_a_through_hole():
    ok = fabricate.check_floor("red", "yellow", thickness=1.0, depth=0.2)
    assert ok.ok and math.isclose(ok.floor_mm, 0.8, abs_tol=1e-12)

    bad = fabricate.check_floor("red", "yellow", thickness=0.2, depth=0.2)
    assert not bad.ok and bad.floor_mm <= 0


def test_registration_freedom_is_per_side_clearance_and_accumulates():
    assert fabricate.registration_freedom(0.10) == 0.10
    # yellow relative to white through two seatings
    assert math.isclose(
        fabricate.cumulative_registration_freedom([0.10, 0.20]), 0.30, abs_tol=1e-12
    )


def test_visible_outline_width_equals_clearance_and_reports_its_area():
    c = 0.20
    recess = fabricate.derive_recess(SQ10, c)
    outline = fabricate.visible_outline(SQ10, recess, nominal_clearance=c)
    assert math.isclose(outline["width_mm"], c, abs_tol=ARC_TOL_MM)
    # the exposed support ring is roughly perimeter x clearance
    assert math.isclose(outline["area_mm2"], 40.0 * c, rel_tol=0.10), outline


def test_zero_or_negative_clearance_is_rejected():
    for bad in (0.0, -0.1):
        with pytest.raises(ValueError, match="positive"):
            fabricate.derive_recess(SQ10, bad)
