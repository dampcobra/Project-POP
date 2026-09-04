"""Tests for manifold validation.

`test_self_intersection_is_detected_where_trimesh_reports_nothing` is the
honesty test: it fails if we ever quietly downgrade self-intersection checking
to whatever trimesh happens to offer.
"""

import numpy as np
import trimesh

from layercake_spike import validate


def test_clean_box_validates_ok():
    r = validate.validate_mesh("box", trimesh.creation.box(extents=[1, 1, 1]))
    assert r.watertight and r.non_manifold_edges == 0 and r.self_intersections == 0
    assert r.ok


def test_open_mesh_is_flagged_not_ok():
    m = trimesh.creation.box(extents=[1, 1, 1])
    torn = trimesh.Trimesh(m.vertices, m.faces[:-2], process=False)
    r = validate.validate_mesh("torn", torn)
    assert not r.watertight
    assert r.non_manifold_edges > 0
    assert not r.ok


def test_self_intersection_is_detected_where_trimesh_reports_nothing():
    # Two crossing triangles. trimesh's watertight/winding checks say nothing
    # useful about this; our own checker must fire.
    v = np.array(
        [
            [0.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [0.0, 4.0, 0.0],
            [1.0, 1.0, -2.0],
            [1.0, 1.0, 2.0],
            [3.0, 1.0, 0.0],
        ]
    )
    m = trimesh.Trimesh(vertices=v, faces=np.array([[0, 1, 2], [3, 4, 5]]), process=False)
    assert len(validate.self_intersections(m)) == 1


def test_adjacent_triangles_are_not_false_positives():
    assert validate.self_intersections(trimesh.creation.box(extents=[1, 1, 1])) == []


def test_a_real_extruded_body_has_no_self_intersections():
    from layercake_spike import extrude, spec

    v, f = extrude.extrude(spec.B_OUTER_RING, [spec.C_RING], *spec.Z_ARTWORK)
    m = trimesh.Trimesh(vertices=v, faces=f, process=False)
    assert validate.self_intersections(m) == []


def test_report_always_discloses_the_trimesh_limitation():
    r = validate.validate_mesh("box", trimesh.creation.box(extents=[1, 1, 1]))
    assert any(
        "self-intersection" in n.lower() and "trimesh" in n.lower() for n in r.tool_notes
    )


def test_report_is_json_safe():
    import json

    r = validate.validate_mesh("box", trimesh.creation.box(extents=[1, 1, 1]))
    json.dumps(r.to_dict())
