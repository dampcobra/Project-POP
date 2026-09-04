"""End-to-end tests: the artefacts Issue #3 asks for."""

import json

import pytest
import trimesh

from layercake_spike.spike02 import cli02, params


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("spike02")
    code = cli02.run(out)
    return out, code


def test_run_passes_and_writes_every_required_artefact(built):
    out, code = built
    assert code == 0
    required = [
        "coupon_fixture.stl",
        "assembly_coregistered.stl",
        "plate_layout.stl",
        "debug-recesses.svg",
        "validation-report.md",
        "spike02-parameters.json",
        "spike02-report.md",
        "stack_white.stl",
        "stack_red.stl",
        "stack_yellow.stl",
    ]
    for name in required:
        assert (out / name).exists(), name
    for cell in params.CELLS:
        assert (out / f"coupon_child_{cell.cell_id}.stl").exists(), cell.cell_id


def test_every_exported_body_reloads_watertight(built):
    out, _ = built
    for path in sorted(out.glob("*.stl")):
        if path.name in ("assembly_coregistered.stl", "plate_layout.stl"):
            continue  # multi-body concatenations
        m = trimesh.load(path)
        assert m.is_watertight, path.name
        assert m.is_winding_consistent, path.name


def test_plate_layout_is_printable(built):
    out, _ = built
    plate = trimesh.load(out / "plate_layout.stl")
    assert abs(plate.bounds[0][2]) < 1e-6, "everything must sit on the plate"
    w = plate.bounds[1][0] - plate.bounds[0][0]
    h = plate.bounds[1][1] - plate.bounds[0][1]
    assert w <= 256.0 and h <= 256.0, (w, h)


def test_assembly_places_bodies_at_true_z(built):
    out, _ = built
    asm = trimesh.load(out / "assembly_coregistered.stl")
    # STL stores float32, so reloaded coordinates carry ~1e-7 of rounding
    assert abs(asm.bounds[0][2]) < 1e-4
    # the tallest thing in the assembly is the three-level stack finishing at 2.4
    assert abs(asm.bounds[1][2] - 2.4) < 1e-4, asm.bounds[1][2]


def test_assembly_seats_each_child_at_its_recess_floor(built):
    out, _ = built
    fixture_top = params.FIXTURE_SUPPORT_MM
    for cell in params.CELLS:
        child = trimesh.load(out / f"coupon_child_{cell.cell_id}.stl")
        # exported loose, the child sits on the plate...
        assert abs(child.bounds[0][2]) < 1e-4, cell.cell_id
        # ...and seating it drops it to the recess floor, finishing flush at H
        seated_top = (fixture_top - cell.depth) + cell.thickness
        assert abs(seated_top - (fixture_top + params.H_VISIBLE_STEP_MM)) < 1e-9


def test_summary_records_the_z_model_and_criteria(built):
    out, _ = built
    s = json.loads((out / "spike02-parameters.json").read_text())
    assert s["pass"]
    assert all(s["criteria"].values()), s["criteria"]
    assert s["process_conditions"]["slicer_layer_height_mm"] == 0.2
    assert s["model"]["child_thickness_rule"] == "H + D"
    assert s["model"]["join_type"] == "round"
    for block in s["three_level_stack"].values():
        assert block["completed_tops_mm"] == [0.8, 1.6, 2.4]


def test_summary_records_registration_freedom_and_visible_outline(built):
    out, _ = built
    s = json.loads((out / "spike02-parameters.json").read_text())
    for c in s["cells"]:
        assert c["registration_freedom_per_side_mm"] == c["nominal_clearance_mm"]
        assert c["visible_support_outline"]["area_mm2"] > 0
    for block in s["three_level_stack"].values():
        assert block["cumulative_registration_freedom_mm"] > block["clearance_mm"]


def test_summary_keeps_the_self_intersection_caveat(built):
    out, _ = built
    s = json.loads((out / "spike02-parameters.json").read_text())
    notes = " ".join(s["validation"]["tool_notes"]).lower()
    assert "trimesh" in notes and "no such test" in notes
    assert "not been cross-checked" in notes


def test_derived_geometry_is_inspected_not_mutated(built):
    out, _ = built
    s = json.loads((out / "spike02-parameters.json").read_text())
    insp = s["derived_geometry_inspection"]
    assert insp["mode"] == "report_only"
    for f in insp["findings"]:
        assert f["action"] == "reported_only"


def test_island_is_seated_not_stacked(built):
    out, _ = built
    s = json.loads((out / "spike02-parameters.json").read_text())
    for block in s["three_level_stack"].values():
        red = block["levels"][1]
        assert red["canonical_hole_count"] == 1
        assert red["fabrication_hole_count"] == 0


def test_report_gives_andy_blank_observation_tables(built):
    out, _ = built
    text = (out / "spike02-report.md").read_text(encoding="utf-8")
    assert "Physical observations - Andy" in text
    assert "Elephant-foot compensation" in text
    assert "Slicer layer height" in text
    for cell in params.CELLS:
        assert cell.cell_id in text


def test_depth_followup_artefacts_are_written(built):
    out, _ = built
    fu = out / "depth-followup"
    for name in [
        "depth_followup_fixture.stl",
        "assembly_coregistered.stl",
        "plate_layout.stl",
        "debug-recesses.svg",
        "validation-report.md",
        "depth-followup-parameters.json",
        "depth-followup-report.md",
    ]:
        assert (fu / name).exists(), name
    children = sorted(fu.glob("depth_child_*.stl"))
    assert len(children) == 4 * params.DEPTH_FOLLOWUP_REPLICATES


def test_depth_followup_children_reload_watertight_with_right_thicknesses(built):
    out, _ = built
    fu = out / "depth-followup"
    seen = {}
    for path in sorted(fu.glob("depth_child_*.stl")):
        m = trimesh.load(path)
        assert m.is_watertight, path.name
        h = round(float(m.bounds[1][2] - m.bounds[0][2]), 3)
        seen.setdefault(h, 0)
        seen[h] += 1
    expected = {
        round(params.H_VISIBLE_STEP_MM + d, 3): params.DEPTH_FOLLOWUP_REPLICATES
        for d in params.DEPTH_FOLLOWUP_DEPTHS
    }
    assert seen == expected, seen


def test_depth_followup_summary_holds_one_variable(built):
    out, _ = built
    s = json.loads(
        (out / "depth-followup" / "depth-followup-parameters.json").read_text()
    )
    assert s["pass"]
    assert all(s["criteria"].values()), s["criteria"]
    assert len({c["clearance_mm"] for c in s["cells"]}) == 1
    assert [c["depth_mm"] for c in s["cells"]] == [0.40, 0.60, 0.80, 1.00]
    assert s["changed_from_round_1"]["backing_thickness_mm"] == 1.6
    assert "glue-up handling" in s["acceptance_target"]


def test_depth_followup_report_asks_the_right_question(built):
    out, _ = built
    text = (out / "depth-followup" / "depth-followup-report.md").read_text(
        encoding="utf-8"
    )
    assert "Stays put during handling" in text
    assert "not dry retention" in text.lower()
    assert "0.15 mm elephant-foot compensation" in text
    for d in (0.40, 0.60, 0.80, 1.00):
        assert f"| {d:.2f} |" in text
