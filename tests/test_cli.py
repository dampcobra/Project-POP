"""End-to-end tests: the artefacts Issue #1 asks for, and the criteria they must meet."""

import json

import trimesh

from layercake_spike import cli

BODIES = ["A_backing.stl", "B_foreground.stl", "C_island.stl"]


def test_full_run_emits_every_required_artefact(tmp_path):
    assert cli.run(tmp_path) == 0
    for name in [
        *BODIES,
        "topology-dump.json",
        "debug.svg",
        "cleanup-report.md",
        "validation-report.md",
        "spike-summary.json",
    ]:
        assert (tmp_path / name).exists(), name


def test_every_exported_body_is_manifold(tmp_path):
    cli.run(tmp_path)
    for name in BODIES:
        m = trimesh.load(tmp_path / name)
        assert m.is_watertight, name
        assert m.is_winding_consistent, name
        assert m.volume > 0, name


def test_bodies_are_co_registered_on_a_shared_origin(tmp_path):
    cli.run(tmp_path)
    a = trimesh.load(tmp_path / "A_backing.stl")
    b = trimesh.load(tmp_path / "B_foreground.stl")
    c = trimesh.load(tmp_path / "C_island.stl")

    assert abs(a.bounds[0][2] - 0.0) < 1e-6 and abs(a.bounds[1][2] - 0.8) < 1e-6
    for m, name in ((b, "B"), (c, "C")):
        assert abs(m.bounds[0][2] - 0.8) < 1e-6, name
        assert abs(m.bounds[1][2] - 2.0) < 1e-6, name

    # C sits inside B's footprint, at the same origin -- no per-body translation
    assert c.bounds[0][0] >= b.bounds[0][0] and c.bounds[1][0] <= b.bounds[1][0]
    assert c.bounds[0][1] >= b.bounds[0][1] and c.bounds[1][1] <= b.bounds[1][1]


def test_b_and_c_do_not_overlap_in_the_artwork_band(tmp_path):
    cli.run(tmp_path)
    s = json.loads((tmp_path / "spike-summary.json").read_text())
    band = s["band_validation"]["artwork"]
    assert band["overlap_area"] < 1e-6, band
    assert band["gap_area"] < 1e-6, band
    assert band["ok"]


def test_summary_records_the_removed_tab_and_the_validation_caveat(tmp_path):
    cli.run(tmp_path)
    s = json.loads((tmp_path / "spike-summary.json").read_text())
    tabs = [f for f in s["cleanup"]["findings"] if f["kind"] == "thin_feature"]
    assert len(tabs) == 1
    assert tabs[0]["action"] == "removed"
    assert s["cleanup"]["min_feature_mm"] == 0.4
    assert any("trimesh" in n.lower() for n in s["validation"]["tool_notes"])


def test_the_island_stays_anchored_to_the_backing(tmp_path):
    """C must sit directly on A, or it prints as a loose part."""
    cli.run(tmp_path)
    s = json.loads((tmp_path / "spike-summary.json").read_text())
    anchor = s["island_anchoring"]["C"]
    assert anchor["rests_on"] == "A"
    assert anchor["contact_area_mm2"] > 0
    assert anchor["ok"]


def test_reported_volumes_match_the_specified_geometry(tmp_path):
    cli.run(tmp_path)
    s = json.loads((tmp_path / "spike-summary.json").read_text())
    vols = {b["body"]: b["volume"] for b in s["validation"]["bodies"]}
    assert abs(vols["A"] - 50.0 * 50.0 * 0.8) < 1e-6
    assert abs(vols["C"] - 8.0 * 8.0 * 1.2) < 1e-6


def test_run_is_deterministic_across_invocations(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    cli.run(a)
    cli.run(b)
    for name in BODIES:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_the_topology_dump_records_the_shared_boundary(tmp_path):
    cli.run(tmp_path)
    dump = json.loads((tmp_path / "topology-dump.json").read_text())
    assert dump["counts"]["shared_edges"] == 4
    assert dump["regions"]["B"]["contains"] == ["C"]
    assert dump["regions"]["B"]["adjacent_to"] == ["C"]
