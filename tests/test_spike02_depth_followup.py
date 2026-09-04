"""Tests for the depth-only follow-up coupon.

The follow-up answers one question: how deep should a registration recess be?
Everything else is held fixed, so the tests are mostly about *not* varying
things -- clearance, shape, and process conditions must be identical across
cells or the result is not a depth measurement.
"""

import math

import pytest
from shapely.geometry import Polygon

from layercake_spike import validate
from layercake_spike.spike02 import depth_followup as df
from layercake_spike.spike02 import params


@pytest.fixture(scope="module")
def built():
    return df.build_depth_followup()


def _is_layer_multiple(v: float) -> bool:
    n = v / params.LAYER_HEIGHT_MM
    return math.isclose(n, round(n), abs_tol=1e-9)


# --- parameters -------------------------------------------------------------


def test_depths_bracket_the_expected_optimum():
    assert params.DEPTH_FOLLOWUP_DEPTHS == (0.40, 0.60, 0.80, 1.00)


def test_backing_is_thickened_so_depth_is_the_only_variable():
    """A 0.8 mm backing cannot host a 0.8 mm recess: the floor would vanish."""
    assert params.DEPTH_FOLLOWUP_BACKING_MM == 1.6
    worst = params.DEPTH_FOLLOWUP_BACKING_MM - max(params.DEPTH_FOLLOWUP_DEPTHS)
    assert worst >= 0.4, worst  # at least two layers of floor at the deepest cell


def test_the_previous_backing_could_not_have_run_this_experiment():
    assert params.STACK_BACKING_MM - 0.80 <= 0.0


def test_clearance_is_held_at_the_process_floor():
    assert params.DEPTH_FOLLOWUP_CLEARANCE_MM == 0.05
    assert params.DEPTH_FOLLOWUP_REPLICATES == 3


def test_every_z_dimension_is_a_whole_number_of_layers():
    dims = {"backing": params.DEPTH_FOLLOWUP_BACKING_MM, "marker": params.MARKER_DEPTH_MM}
    for d in params.DEPTH_FOLLOWUP_DEPTHS:
        dims[f"depth_{d}"] = d
        dims[f"child_{d}"] = params.child_thickness(d)
    for name, v in dims.items():
        assert _is_layer_multiple(v), f"{name}={v}"


# --- geometry ---------------------------------------------------------------


def test_one_cell_per_depth_and_three_children_each(built):
    assert len(built.cells) == 4
    assert len(built.children) == 12
    for cell in built.cells:
        reps = [c for c in built.children if c.depth == cell.depth]
        assert len(reps) == params.DEPTH_FOLLOWUP_REPLICATES, cell.depth


def test_every_cell_uses_the_same_clearance_and_shape(built):
    assert {c.clearance for c in built.cells} == {params.DEPTH_FOLLOWUP_CLEARANCE_MM}
    assert {tuple(c.canonical_footprint_local) for c in built.cells} == {
        tuple(df.FOLLOWUP_SHAPE)
    }


def test_child_thickness_follows_h_plus_d(built):
    for child in built.children:
        expected = params.H_VISIBLE_STEP_MM + child.depth
        assert math.isclose(child.thickness, expected, abs_tol=1e-12)
        height = child.mesh.bounds[1][2] - child.mesh.bounds[0][2]
        assert math.isclose(height, expected, abs_tol=1e-9)


def test_seated_tops_finish_flush_at_backing_plus_h(built):
    backing = params.DEPTH_FOLLOWUP_BACKING_MM
    for cell in built.cells:
        seated_top = (backing - cell.depth) + params.child_thickness(cell.depth)
        assert math.isclose(
            seated_top, backing + params.H_VISIBLE_STEP_MM, abs_tol=1e-12
        ), cell.depth


def test_support_stays_continuous_at_every_depth(built):
    for cell in built.cells:
        assert cell.floor.ok, cell.depth
        assert cell.floor.floor_mm >= 0.4, (cell.depth, cell.floor.floor_mm)


def test_replicates_within_a_depth_are_geometrically_identical(built):
    for depth in params.DEPTH_FOLLOWUP_DEPTHS:
        reps = [c for c in built.children if c.depth == depth]
        volumes = [round(c.mesh.volume, 9) for c in reps]
        assert len(set(volumes)) == 1, (depth, volumes)


def test_children_of_different_depths_are_distinguishable_by_marker_count(built):
    counts = {c.depth: c.marker_count for c in built.children}
    assert counts == {0.40: 1, 0.60: 2, 0.80: 3, 1.00: 4}


def test_markers_are_engraved_so_flushness_is_not_compromised(built):
    """A proud marker would sit above the artwork surface and spoil the check."""
    for child in built.children:
        top = child.mesh.bounds[1][2] - child.mesh.bounds[0][2]
        assert math.isclose(top, child.thickness, abs_tol=1e-9), child.depth
        assert child.mesh.volume < df.footprint_area() * child.thickness


def test_marker_never_breaks_through_the_thinnest_child(built):
    thinnest = params.child_thickness(min(params.DEPTH_FOLLOWUP_DEPTHS))
    assert params.MARKER_DEPTH_MM < thinnest


# --- meshes -----------------------------------------------------------------


def test_fixture_is_manifold_with_no_through_holes(built):
    r = validate.validate_mesh("depth_followup_fixture", built.fixture_mesh)
    assert r.watertight and r.winding_consistent
    assert r.non_manifold_edges == 0
    assert r.self_intersections == 0


def test_every_child_is_manifold(built):
    for child in built.children:
        r = validate.validate_mesh(child.child_id, child.mesh)
        assert r.watertight, child.child_id
        assert r.non_manifold_edges == 0, child.child_id
        assert r.self_intersections == 0, child.child_id


def test_recesses_do_not_overlap(built):
    polys = [Polygon(c.recess) for c in built.cells]
    for i, a in enumerate(polys):
        for b in polys[i + 1 :]:
            assert a.intersection(b).area < 1e-12


def test_each_child_fits_its_recess_with_the_held_clearance(built):
    for cell in built.cells:
        child = Polygon(cell.canonical_footprint)
        recess = Polygon(cell.recess)
        assert recess.contains(child)
        assert math.isclose(
            cell.outline["achieved_clearance_mm"],
            params.DEPTH_FOLLOWUP_CLEARANCE_MM,
            abs_tol=1e-3,
        )


def test_derived_support_inspection_finds_no_real_thin_feature(built):
    real = [f for f in built.derived_feature_findings if f.kind == "thin_derived_support"]
    assert real == [], [f.detail for f in real]


def test_coupon_fits_the_bed(built):
    lo, hi = built.fixture_mesh.bounds
    assert (hi[0] - lo[0]) <= 250.0 and (hi[1] - lo[1]) <= 250.0
