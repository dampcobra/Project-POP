"""Tests for minimum-feature detection and removal.

`test_cleanup_preserves_the_shared_boundary_with_c_exactly` is the important
one: a naive morphological opening cleans the tab but also nibbles the shared
boundary with C, silently breaking the invariant the topology model exists to
guarantee.
"""

import math

from layercake_spike import cleanup, clipper, spec


def b_with_tab():
    return clipper.boolean_op([spec.B_OUTER_RING], [spec.TAB_RING], "union")[0]


def test_tab_is_detected_with_the_threshold_recorded():
    _, _, findings = cleanup.clean_region(
        b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B"
    )
    tabs = [f for f in findings if f.kind == "thin_feature"]
    assert len(tabs) == 1
    assert tabs[0].action == "removed"
    assert tabs[0].min_feature_mm == spec.MIN_FEATURE_MM
    assert math.isclose(tabs[0].area_mm2, 0.15 * 3.0, rel_tol=0.10), tabs[0].area_mm2


def test_tab_does_not_survive_into_cleaned_geometry():
    outer, _, _ = cleanup.clean_region(
        b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B"
    )
    assert max(x for x, _ in outer) <= 44.0 + 1e-6, "tab must be gone"


def test_cleanup_preserves_the_shared_boundary_with_c_exactly():
    _, holes, _ = cleanup.clean_region(
        b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B"
    )
    assert len(holes) == 1
    got = sorted((round(x, 9), round(y, 9)) for x, y in holes[0])
    want = sorted((round(x, 9), round(y, 9)) for x, y in spec.C_RING)
    assert got == want, "the shared boundary with C must be reinstated bit-exact"


def test_cleanup_preserves_the_reflex_notch_within_tolerance():
    outer, _, _ = cleanup.clean_region(
        b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B"
    )
    for want in spec.B_REFLEX_VERTICES:
        nearest = min(outer, key=lambda p: math.dist(p, want))
        assert math.dist(nearest, want) < 0.05, (want, nearest)


def test_cleanup_is_deterministic():
    a = cleanup.clean_region(b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B")
    b = cleanup.clean_region(b_with_tab(), [spec.C_RING], spec.MIN_FEATURE_MM, "B")
    assert a[0] == b[0] and a[1] == b[1]


def test_clean_geometry_reports_no_findings():
    _, _, findings = cleanup.clean_region(
        spec.B_OUTER_RING, [spec.C_RING], spec.MIN_FEATURE_MM, "B"
    )
    assert [f for f in findings if f.kind == "thin_feature"] == []


def test_area_is_preserved_apart_from_the_removed_tab():
    dirty = b_with_tab()
    outer, _, _ = cleanup.clean_region(dirty, [spec.C_RING], spec.MIN_FEATURE_MM, "B")
    lost = abs(clipper.area(dirty)) - abs(clipper.area(outer))
    assert math.isclose(lost, 0.15 * 3.0, abs_tol=0.05), lost
