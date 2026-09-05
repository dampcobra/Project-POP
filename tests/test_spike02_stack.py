"""Tests for the three-level layered-relief stack.

The central assertion is that a canonical hole becomes a *filled* support with a
shallow pocket -- ADR 0002. That is what makes the child seatable from above
instead of having to pass laterally through a co-planar opening, which is the
failure that ended Spike 01.
"""

import copy
import math

import pytest

from layercake_spike import spec, validate
from layercake_spike.spike02 import params, stack


@pytest.fixture(scope="module")
def built():
    return {d: stack.build_stack(depth=d) for d in params.DEPTHS_MM}


def test_completed_tops_step_by_h_from_the_backing_for_every_depth(built):
    """The Z model is a *relationship*, not the literals a 0.8 mm backing gave.

    Backing is an independent property since Session 01, so pinning 0.8/1.6/2.4
    here would re-couple the two through the test suite. The as-printed literals
    are pinned separately, against the as-printed backing.
    """
    backing = params.BACKING_THICKNESS_MM
    h = params.H_VISIBLE_STEP_MM
    for depth, s in built.items():
        tops = [round(t, 9) for t in s.completed_tops]
        assert tops == [
            round(backing, 9),
            round(backing + h, 9),
            round(backing + 2 * h, 9),
        ], (depth, tops)


def test_child_thickness_follows_h_plus_d(built):
    for depth, s in built.items():
        for name in ("red", "yellow"):
            lv = s.by_name[name]
            assert math.isclose(lv.z.child_thickness, 0.8 + depth, abs_tol=1e-12)
            height = lv.mesh.bounds[1][2] - lv.mesh.bounds[0][2]
            assert math.isclose(height, 0.8 + depth, abs_tol=1e-9), name


def test_red_has_no_through_hole_where_yellow_sits(built):
    """Canonical containment must not force a fabrication through-hole."""
    for depth, s in built.items():
        red = s.by_name["red"]
        assert red.canonical_holes, "canonically, yellow IS a hole in red"
        assert red.fabrication_outer is not None
        assert red.mesh.euler_number == 2, (
            f"euler {red.mesh.euler_number}: red must be solid under yellow, "
            "carrying only a blind pocket"
        )


def test_red_material_under_yellow_is_thickness_minus_depth(built):
    for depth, s in built.items():
        red = s.by_name["red"]
        assert math.isclose(red.floor.floor_mm, 0.8, abs_tol=1e-12), depth
        assert red.floor.ok


def test_yellow_is_seated_from_above_not_passed_through(built):
    for depth, s in built.items():
        red, yellow = s.by_name["red"], s.by_name["yellow"]
        recess_floor = red.z.child_top - depth
        assert math.isclose(yellow.z.child_bottom, recess_floor, abs_tol=1e-12)
        # strictly above red's own underside: it never reaches the backing
        assert yellow.z.child_bottom > red.z.child_bottom
        assert yellow.mesh.bounds[0][2] > red.mesh.bounds[0][2]


def test_support_remains_continuous_at_every_level(built):
    for depth, s in built.items():
        for lv in s.levels:
            if lv.floor is not None:
                assert lv.floor.ok, (depth, lv.name)
                assert lv.floor.floor_mm > 0


def test_every_body_is_manifold(built):
    for depth, s in built.items():
        for lv in s.levels:
            r = validate.validate_mesh(lv.name, lv.mesh)
            assert r.watertight, (depth, lv.name)
            assert r.winding_consistent, (depth, lv.name)
            assert r.non_manifold_edges == 0, (depth, lv.name)
            assert r.self_intersections == 0, (depth, lv.name)


def test_spike01_canonical_geometry_is_not_mutated_by_derivation():
    before = (
        copy.deepcopy(spec.BACKING_RING),
        copy.deepcopy(spec.B_OUTER_RING),
        copy.deepcopy(spec.C_RING),
    )
    stack.build_stack()
    assert (spec.BACKING_RING, spec.B_OUTER_RING, spec.C_RING) == before


def test_cumulative_registration_freedom_accumulates_with_depth(built):
    s = stack.build_stack(clearance=0.10)
    # two seatings: red into white, yellow into red
    assert math.isclose(s.cumulative_registration_freedom, 0.20, abs_tol=1e-12)


def test_recess_clearance_is_present_at_every_seating(built):
    for depth, s in built.items():
        for name in ("white", "red"):
            lv = s.by_name[name]
            assert math.isclose(
                lv.outline["achieved_clearance_mm"], s.clearance, abs_tol=1e-3
            ), (depth, name)
            assert lv.outline["area_mm2"] > 0


def test_visible_step_is_h_at_every_level(built):
    for depth, s in built.items():
        tops = s.completed_tops
        assert math.isclose(tops[1] - tops[0], params.H_VISIBLE_STEP_MM, abs_tol=1e-12)
        assert math.isclose(tops[2] - tops[1], params.H_VISIBLE_STEP_MM, abs_tol=1e-12)


# --- backing decoupled from H (Session 01) -----------------------------------


def test_stack_takes_its_backing_as_a_parameter():
    s = stack.build_stack(backing=1.6)
    assert math.isclose(s.by_name["white"].z.child_thickness, 1.6, abs_tol=1e-12)


def test_visible_steps_are_h_regardless_of_backing_thickness():
    """Decoupling must not disturb the artwork: every step stays H."""
    for backing in (0.8, 1.2, 1.6, 2.0):
        s = stack.build_stack(backing=backing, depth=0.20)
        tops = s.completed_tops
        assert math.isclose(tops[0], backing, abs_tol=1e-12), backing
        assert math.isclose(tops[1] - tops[0], params.H_VISIBLE_STEP_MM, abs_tol=1e-12)
        assert math.isclose(tops[2] - tops[1], params.H_VISIBLE_STEP_MM, abs_tol=1e-12)


def test_default_backing_can_host_the_measured_default_depth():
    """The coupled 0.8 mm backing could not; that is why it was decoupled."""
    s = stack.build_stack(depth=params.MEASURED_DEFAULT_DEPTH_MM)
    white = s.by_name["white"]
    assert white.floor.ok
    assert white.floor.floor_mm >= params.MIN_RECESS_FLOOR_MM - 1e-9


def test_the_old_coupled_backing_still_cannot_host_it():
    with pytest.raises(ValueError, match="through-hole"):
        stack.build_stack(
            backing=params.ROUND1_AS_PRINTED_BACKING_MM,
            depth=params.MEASURED_DEFAULT_DEPTH_MM,
        )


def test_round_1_as_printed_geometry_is_still_reproducible():
    """The printed three-level article must stay derivable from the code."""
    s = stack.build_stack(
        backing=params.ROUND1_AS_PRINTED_BACKING_MM,
        clearance=0.10,
        depth=0.20,
    )
    assert [round(t, 9) for t in s.completed_tops] == [0.8, 1.6, 2.4]
