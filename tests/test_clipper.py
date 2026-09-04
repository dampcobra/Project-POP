"""Contract tests for the Clipper2 adapter.

These pin down the behaviour the rest of the spike relies on, so swapping the
polygon backend later is a matter of making these pass again.
"""

import math

from layercake_spike import clipper

SQ10 = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
SQ_MID = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]


def test_difference_produces_outer_and_hole():
    out = clipper.boolean_op([SQ10], [SQ_MID], "difference")
    assert len(out) == 2
    # the hole comes back oppositely wound, so the *signed* sum is the net area
    assert math.isclose(clipper.total_area(out), 100.0 - 4.0, abs_tol=1e-6)


def test_boolean_tree_reports_containment():
    tree = clipper.boolean_tree([SQ10], [SQ_MID], "difference")
    assert len(tree) == 1
    assert len(tree[0].holes) == 1
    assert math.isclose(abs(clipper.area(tree[0].holes[0])), 4.0, abs_tol=1e-6)


def test_negative_offset_erases_a_thin_sliver():
    sliver = [(0.0, 0.0), (5.0, 0.0), (5.0, 0.15), (0.0, 0.15)]
    assert clipper.offset([sliver], -0.2) == []


def test_offset_roundtrip_preserves_a_fat_shape_within_tolerance():
    shrunk = clipper.offset([SQ10], -0.2)
    regrown = clipper.offset(shrunk, +0.2)
    assert math.isclose(abs(clipper.area(regrown[0])), 100.0, abs_tol=1e-3)


def test_union_merges_overlapping_shapes():
    other = [(8.0, 0.0), (14.0, 0.0), (14.0, 10.0), (8.0, 10.0)]
    out = clipper.boolean_op([SQ10], [other], "union")
    assert len(out) == 1
    assert math.isclose(abs(clipper.area(out[0])), 140.0, abs_tol=1e-6)


def test_intersection_area_is_the_overlap():
    out = clipper.boolean_op([SQ10], [SQ_MID], "intersection")
    assert math.isclose(sum(abs(clipper.area(r)) for r in out), 4.0, abs_tol=1e-6)


def test_area_sign_follows_winding():
    ccw = clipper.area(SQ10)
    cw = clipper.area(list(reversed(SQ10)))
    assert ccw > 0 and cw < 0 and math.isclose(ccw, -cw)
