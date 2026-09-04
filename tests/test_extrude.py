"""Tests for ring extrusion.

Watertightness is asserted directly rather than inferred, because it is the
property the whole spike turns on.
"""

import math

import numpy as np
import trimesh

from layercake_spike import extrude, spec

SQ2 = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]


def mesh_of(outer, holes, z0, z1):
    v, f = extrude.extrude(outer, holes, z0, z1)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def test_simple_box_is_watertight_with_correct_volume():
    m = mesh_of(SQ2, [], 0.0, 3.0)
    assert m.is_watertight and m.is_winding_consistent
    assert math.isclose(m.volume, 12.0, rel_tol=1e-9)


def test_ring_with_hole_is_watertight_and_volume_excludes_the_hole():
    outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    hole = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]
    m = mesh_of(outer, [hole], 0.0, 1.0)
    assert m.is_watertight
    assert math.isclose(m.volume, 96.0, rel_tol=1e-9)


def test_concave_notch_survives_extrusion():
    v, f = extrude.extrude(spec.B_OUTER_RING, [], *spec.Z_ARTWORK)
    m = trimesh.Trimesh(vertices=v, faces=f, process=False)
    assert m.is_watertight and m.volume > 0
    assert np.isclose(v[:, 2].min(), 0.8) and np.isclose(v[:, 2].max(), 2.0)
    for want in spec.B_REFLEX_VERTICES:
        assert any(np.allclose(p[:2], want) for p in v), f"{want} must survive"


def test_euler_number_is_two_for_a_solid_without_through_holes():
    assert mesh_of(SQ2, [], 0.0, 1.0).euler_number == 2


def test_euler_number_is_zero_for_a_solid_with_one_through_hole():
    outer = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    hole = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]
    assert mesh_of(outer, [hole], 0.0, 1.0).euler_number == 0


def test_the_full_b_region_with_its_c_hole_is_watertight():
    m = mesh_of(spec.B_OUTER_RING, [spec.C_RING], *spec.Z_ARTWORK)
    assert m.is_watertight and m.is_winding_consistent
    assert m.volume > 0
    # B's volume must exclude the island it hosts
    solid = mesh_of(spec.B_OUTER_RING, [], *spec.Z_ARTWORK)
    assert math.isclose(solid.volume - m.volume, 8.0 * 8.0 * 1.2, rel_tol=1e-9)


def test_normals_point_outward():
    m = mesh_of(SQ2, [], 0.0, 1.0)
    assert m.volume > 0, "negative volume means inverted winding"
    assert m.is_volume


def test_input_winding_is_normalised_so_callers_need_not_care():
    a = mesh_of(SQ2, [], 0.0, 1.0)
    b = mesh_of(list(reversed(SQ2)), [], 0.0, 1.0)
    assert math.isclose(a.volume, b.volume, rel_tol=1e-12)
