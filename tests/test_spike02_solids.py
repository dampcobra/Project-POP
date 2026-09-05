"""Tests for the stepped extruder.

This is the one genuinely new mesh construction in Spike 02, so manifoldness is
asserted here directly, before anything else depends on it.
"""

import math

import pytest
import trimesh

from layercake_spike import validate
from layercake_spike.spike02 import solids

SQ20 = [(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)]
POCKET_A = [(4.0, 4.0), (9.0, 4.0), (9.0, 9.0), (4.0, 9.0)]  # 25 mm2
POCKET_B = [(12.0, 12.0), (16.0, 12.0), (16.0, 16.0), (12.0, 16.0)]  # 16 mm2
BOSS = [(2.0, 15.0), (6.0, 15.0), (6.0, 18.0), (2.0, 18.0)]  # 12 mm2


def mesh_of(footprint, thickness, pockets=(), bosses=()):
    v, f = solids.extrude_stepped(footprint, thickness, pockets, bosses)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def assert_sound(m, name="mesh"):
    r = validate.validate_mesh(name, m)
    assert r.watertight, name
    assert r.winding_consistent, name
    assert r.non_manifold_edges == 0, name
    assert r.self_intersections == 0, name
    assert m.volume > 0, name


def test_plain_prism_matches_spike01_behaviour():
    m = mesh_of(SQ20, 1.6)
    assert_sound(m, "plain")
    assert math.isclose(m.volume, 400.0 * 1.6, rel_tol=1e-9)
    assert m.euler_number == 2


def test_single_pocket_removes_exactly_its_volume():
    m = mesh_of(SQ20, 1.6, [solids.Pocket(POCKET_A, 0.4)])
    assert_sound(m, "one-pocket")
    assert math.isclose(m.volume, 400.0 * 1.6 - 25.0 * 0.4, rel_tol=1e-9)
    assert m.euler_number == 2, "a blind pocket is not a through-hole"


def test_pocket_floor_sits_at_thickness_minus_depth():
    t, d = 1.6, 0.4
    v, _ = solids.extrude_stepped(SQ20, t, [solids.Pocket(POCKET_A, d)])
    zs = sorted({round(float(z), 9) for z in v[:, 2]})
    assert zs == [0.0, round(t - d, 9), t]


def test_two_pockets_of_different_depths_in_one_body():
    m = mesh_of(SQ20, 1.6, [solids.Pocket(POCKET_A, 0.2), solids.Pocket(POCKET_B, 0.4)])
    assert_sound(m, "two-pockets")
    expected = 400.0 * 1.6 - 25.0 * 0.2 - 16.0 * 0.4
    assert math.isclose(m.volume, expected, rel_tol=1e-9)


def test_boss_adds_exactly_its_volume():
    m = mesh_of(SQ20, 1.6, (), [solids.Boss(BOSS, 0.6)])
    assert_sound(m, "one-boss")
    assert math.isclose(m.volume, 400.0 * 1.6 + 12.0 * 0.6, rel_tol=1e-9)
    assert m.euler_number == 2


def test_pockets_and_bosses_together():
    m = mesh_of(
        SQ20,
        1.6,
        [solids.Pocket(POCKET_A, 0.2), solids.Pocket(POCKET_B, 0.4)],
        [solids.Boss(BOSS, 0.6)],
    )
    assert_sound(m, "mixed")
    expected = 400.0 * 1.6 - 25.0 * 0.2 - 16.0 * 0.4 + 12.0 * 0.6
    assert math.isclose(m.volume, expected, rel_tol=1e-9)
    assert m.euler_number == 2


def test_concave_footprint_and_concave_pocket_stay_manifold():
    concave_fp = [
        (0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (12.0, 20.0),
        (12.0, 10.0), (8.0, 10.0), (8.0, 20.0), (0.0, 20.0),
    ]
    concave_pocket = [
        (2.0, 2.0), (10.0, 2.0), (10.0, 8.0), (7.0, 8.0),
        (7.0, 5.0), (5.0, 5.0), (5.0, 8.0), (2.0, 8.0),
    ]
    m = mesh_of(concave_fp, 1.6, [solids.Pocket(concave_pocket, 0.4)])
    assert_sound(m, "concave")


def test_pocket_deeper_than_the_body_is_rejected():
    with pytest.raises(ValueError, match="through-hole|deeper"):
        solids.extrude_stepped(SQ20, 0.4, [solids.Pocket(POCKET_A, 0.4)])
    with pytest.raises(ValueError, match="through-hole|deeper"):
        solids.extrude_stepped(SQ20, 0.4, [solids.Pocket(POCKET_A, 0.5)])


def test_overlapping_pockets_are_rejected_rather_than_silently_merged():
    overlapping = [(6.0, 6.0), (11.0, 6.0), (11.0, 11.0), (6.0, 11.0)]
    with pytest.raises(ValueError, match="overlap"):
        solids.extrude_stepped(
            SQ20, 1.6, [solids.Pocket(POCKET_A, 0.2), solids.Pocket(overlapping, 0.2)]
        )


def test_pocket_must_lie_inside_the_footprint():
    outside = [(25.0, 25.0), (30.0, 25.0), (30.0, 30.0), (25.0, 30.0)]
    with pytest.raises(ValueError, match="inside|contained"):
        solids.extrude_stepped(SQ20, 1.6, [solids.Pocket(outside, 0.2)])


def test_input_winding_is_normalised_so_callers_need_not_care():
    a = mesh_of(SQ20, 1.6, [solids.Pocket(POCKET_A, 0.4)])
    b = mesh_of(
        list(reversed(SQ20)), 1.6, [solids.Pocket(list(reversed(POCKET_A)), 0.4)]
    )
    assert math.isclose(a.volume, b.volume, rel_tol=1e-12)
    assert_sound(b, "reversed")


def test_boss_with_a_hole_keeps_the_void_and_stays_manifold():
    """A seven-segment '0' encloses a void; filling it would break the glyph."""
    ring = [(2.0, 2.0), (8.0, 2.0), (8.0, 10.0), (2.0, 10.0)]  # 48 mm2
    hole = [(3.5, 3.5), (6.5, 3.5), (6.5, 8.5), (3.5, 8.5)]  # 15 mm2
    m = mesh_of(SQ20, 1.6, (), [solids.Boss(ring, 0.6, (hole,))])
    assert_sound(m, "boss-with-hole")
    expected = 400.0 * 1.6 + (48.0 - 15.0) * 0.6
    assert math.isclose(m.volume, expected, rel_tol=1e-9)


def test_boss_hole_must_lie_inside_its_boss():
    ring = [(2.0, 2.0), (8.0, 2.0), (8.0, 10.0), (2.0, 10.0)]
    stray = [(12.0, 2.0), (14.0, 2.0), (14.0, 4.0), (12.0, 4.0)]
    with pytest.raises(ValueError, match="inside its boss"):
        solids.extrude_stepped(SQ20, 1.6, (), [solids.Boss(ring, 0.6, (stray,))])


def test_collinear_feature_boundaries_are_refused_not_silently_broken():
    """Glyphs on a shared baseline defeat the ear-clipping cap triangulator.

    Area still comes out right, so an area check would pass while caps and walls
    no longer correspond. The extruder must refuse rather than return it.
    """
    a = [(2.0, 2.0), (6.0, 2.0), (6.0, 8.0), (2.0, 8.0)]
    b = [(10.0, 2.0), (14.0, 2.0), (14.0, 8.0), (10.0, 8.0)]  # bottoms collinear
    with pytest.raises(ValueError, match="non-manifold|collinear"):
        solids.extrude_stepped(SQ20, 1.6, (), [solids.Boss(a, 0.6), solids.Boss(b, 0.6)])


def test_union_all_assembles_collinear_features_correctly():
    a = [(2.0, 2.0), (6.0, 2.0), (6.0, 8.0), (2.0, 8.0)]
    b = [(10.0, 2.0), (14.0, 2.0), (14.0, 8.0), (10.0, 8.0)]
    v, f = solids.extrude_stepped(SQ20, 1.6)
    body = trimesh.Trimesh(vertices=v, faces=f, process=False)
    merged = solids.union_all(
        [body, solids.prism(a, 1.6, 2.2), solids.prism(b, 1.6, 2.2)]
    )
    assert_sound(merged, "unioned")
    assert math.isclose(merged.volume, 400.0 * 1.6 + 24.0 * 0.6 * 2, rel_tol=1e-6)
