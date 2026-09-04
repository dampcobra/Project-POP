"""Spike 02 parameters assert their own experimental soundness.

The layer-height multiple checks matter: the slicer quantises every Z feature to
a layer boundary, so a recess depth that is not a whole number of layers would
silently become a different depth than the one under test.
"""

import math

from layercake_spike.spike02 import params


def _is_layer_multiple(value: float) -> bool:
    n = value / params.LAYER_HEIGHT_MM
    return math.isclose(n, round(n), abs_tol=1e-9)


def test_terminology_visible_step_height_is_not_layer_height():
    assert params.H_VISIBLE_STEP_MM == 0.8
    assert params.LAYER_HEIGHT_MM == 0.2
    assert params.H_VISIBLE_STEP_MM != params.LAYER_HEIGHT_MM


def test_clearance_and_depth_matrix_matches_the_ticket():
    assert params.CLEARANCES_MM == (0.05, 0.10, 0.20)
    assert params.DEPTHS_MM == (0.20, 0.40)


def test_child_thickness_is_h_plus_d():
    for d in params.DEPTHS_MM:
        assert math.isclose(params.child_thickness(d), 0.8 + d, abs_tol=1e-12)


def test_every_z_dimension_is_a_whole_number_of_layers():
    dims = {
        "H": params.H_VISIBLE_STEP_MM,
        "fixture_support": params.FIXTURE_SUPPORT_MM,
        "stack_backing": params.STACK_BACKING_MM,
        "label_boss": params.LABEL_BOSS_MM,
    }
    for d in params.DEPTHS_MM:
        dims[f"depth_{d}"] = d
        dims[f"child_{d}"] = params.child_thickness(d)
    for name, value in dims.items():
        assert _is_layer_multiple(value), f"{name}={value} is not a layer multiple"


def test_fixture_support_is_thick_enough_not_to_confound_the_fit_experiment():
    worst_floor = params.FIXTURE_SUPPORT_MM - max(params.DEPTHS_MM)
    assert worst_floor >= 1.0, worst_floor


def test_matrix_has_six_cells_plus_two_shape_controls():
    matrix = [c for c in params.CELLS if c.kind == "matrix"]
    controls = [c for c in params.CELLS if c.kind == "shape_control"]
    assert len(matrix) == 6
    assert {(c.clearance, c.depth) for c in matrix} == {
        (c, d) for c in params.CLEARANCES_MM for d in params.DEPTHS_MM
    }
    assert {c.shape_key for c in controls} == {"concave", "radiused"}


def test_matrix_cells_all_use_the_same_simple_shape():
    assert {c.shape_key for c in params.CELLS if c.kind == "matrix"} == {"simple"}


def test_cell_ids_and_labels_are_unique_and_label_the_parameters():
    assert len({c.cell_id for c in params.CELLS}) == len(params.CELLS)
    assert len({c.label for c in params.CELLS}) == len(params.CELLS)
    for c in params.CELLS:
        # the label must let Andy identify both parameters without the slicer
        assert f"C{c.clearance:.2f}".replace("C0", "C") in c.label
        assert f"D{c.depth:.2f}".replace("D0", "D") in c.label


def test_shape_controls_use_a_documented_mid_matrix_setting():
    for c in params.CELLS:
        if c.kind == "shape_control":
            assert c.clearance == params.CONTROL_CLEARANCE_MM
            assert c.depth == params.CONTROL_DEPTH_MM
    assert params.CONTROL_CLEARANCE_MM in params.CLEARANCES_MM
    assert params.CONTROL_DEPTH_MM in params.DEPTHS_MM
