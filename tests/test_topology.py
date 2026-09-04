"""Tests for the canonical partition.

The load-bearing assertion in this module is
`test_b_hole_and_c_outer_are_the_same_shared_vertices`: it is what makes
"shared boundaries are data, not coincidence" a checkable property rather
than a slogan.
"""

from layercake_spike import spec, topology


def build():
    return topology.Partition.build(spec.REGIONS)


def test_vertex_table_deduplicates_coincident_points():
    vt = topology.VertexTable(eps=spec.EPS)
    assert vt.add(1.0, 2.0) == vt.add(1.0 + 1e-9, 2.0 - 1e-9)
    assert vt.add(1.0, 2.5) != vt.add(1.0, 2.0)


def test_b_hole_and_c_outer_are_the_same_shared_vertices():
    p = build()
    b_hole = set(p.regions["B"].holes[0])
    c_outer = set(p.regions["C"].outer)
    assert b_hole == c_outer, "shared boundary must be one set of vertices, not two copies"


def test_shared_edges_are_single_records_naming_both_regions():
    p = build()
    shared = p.shared_edges()
    assert len(shared) == 4, "the C square contributes exactly 4 shared edges"
    for _edge, regions in shared.items():
        assert sorted(regions) == ["B", "C"]


def test_containment_reports_c_inside_b():
    p = build()
    c = p.containment()
    assert c["B"] == ["C"]
    assert c["C"] == []
    assert c["A"] == []  # A is a different Z band; containment is per band


def test_artwork_band_has_no_overlap_and_no_unintended_gap():
    p = build()
    r = p.validate_band(spec.Z_ARTWORK, universe=spec.B_OUTER_RING)
    assert r.overlap_area < spec.EPS, r.overlap_area
    assert r.gap_area < spec.EPS, r.gap_area
    assert r.ok


def test_overlap_is_detected_when_regions_genuinely_collide():
    bad = {
        "B": dict(colour="B", z=spec.Z_ARTWORK, outer=spec.B_OUTER_RING, holes=[]),
        "C": dict(colour="C", z=spec.Z_ARTWORK, outer=spec.C_RING, holes=[]),
    }
    p = topology.Partition.build(bad)  # B has no hole, so C sits on top of B
    r = p.validate_band(spec.Z_ARTWORK, universe=spec.B_OUTER_RING)
    assert r.overlap_area > 60.0, r.overlap_area  # the whole 8x8 island overlaps
    assert not r.ok


def test_gap_is_detected_when_a_region_is_missing():
    partial = {
        "B": dict(colour="B", z=spec.Z_ARTWORK, outer=spec.B_OUTER_RING, holes=[spec.C_RING]),
    }
    p = topology.Partition.build(partial)  # C never supplied -> a real hole
    r = p.validate_band(spec.Z_ARTWORK, universe=spec.B_OUTER_RING)
    assert r.gap_area > 60.0, r.gap_area
    assert not r.ok


def test_dump_is_json_safe_and_records_adjacency():
    import json

    dump = build().to_dump()
    json.dumps(dump)  # must not raise
    assert dump["counts"]["vertices"] > 0
    assert dump["counts"]["shared_edges"] == 4
    assert dump["regions"]["B"]["hole_count"] == 1
    assert {"B", "C"} == set(dump["shared_edges"][0]["regions"])
