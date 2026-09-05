"""Tests for the product fabrication profile (issue #5).

Two properties carry most of the weight here.

**Evidence level is data, not prose.** Session 01 established that these values
are not equally trustworthy -- one is measured, one is held because it could not
be resolved, one is an untested engineering choice. That was previously
maintained by docstrings and a test that grepped them.

**Numerically equal is not semantically equal.** Visible step height, seating
depth and the round-1 as-printed backing are all currently 0.8 mm. That is a
coincidence, and it is exactly the trap Session 01 removed for backing-vs-H.
"""

import ast
import math
from pathlib import Path

import pytest

from layercake.fabrication import profile as fp


# --- shape -------------------------------------------------------------------


def test_profile_holds_every_parameter_the_ticket_lists():
    p = fp.FabricationProfile.default()
    assert {q.name for q in p.parameters()} == {
        "visible_step_height",
        "seating_depth",
        "per_side_clearance",
        "minimum_recess_floor",
        "backing_thickness",
        "layer_height",
        "offset_join",
    }


def test_every_parameter_carries_an_evidence_level_and_a_scope_note():
    for q in fp.FabricationProfile.default().parameters():
        assert isinstance(q.evidence, fp.Evidence), q.name
        assert q.scope and q.scope.strip(), q.name


def test_profile_is_immutable():
    p = fp.FabricationProfile.default()
    with pytest.raises(Exception):
        p.visible_step_height = fp.Parameter(  # type: ignore[misc]
            "visible_step_height", 9.9, fp.Evidence.MEASURED, "nope"
        )


# --- Session 01 values -------------------------------------------------------


def test_default_profile_reproduces_the_session_01_values():
    p = fp.FabricationProfile.default()
    assert p.visible_step_height.mm == 0.8
    assert p.seating_depth.mm == 0.80
    assert p.per_side_clearance.mm == 0.05
    assert p.minimum_recess_floor.mm == 0.40
    assert p.backing_thickness.mm == 1.2
    assert p.layer_height.mm == 0.20
    assert p.offset_join.value == "round"


def test_evidence_levels_match_what_session_01_established():
    p = fp.FabricationProfile.default()
    assert p.seating_depth.evidence is fp.Evidence.MEASURED
    assert p.per_side_clearance.evidence is fp.Evidence.HELD
    assert p.minimum_recess_floor.evidence is fp.Evidence.ENGINEERING_CHOICE


def test_backing_inherits_the_weakest_evidence_of_its_inputs():
    """Derived from a measured depth and an untested floor: the floor governs."""
    p = fp.FabricationProfile.default()
    assert p.backing_thickness.evidence is fp.Evidence.ENGINEERING_CHOICE
    assert set(p.backing_thickness.derived_from) == {
        "seating_depth",
        "minimum_recess_floor",
    }


# --- numerically equal, semantically distinct --------------------------------


def test_visible_step_height_and_seating_depth_are_not_interchangeable():
    p = fp.FabricationProfile.default()
    assert p.visible_step_height.mm == p.seating_depth.mm  # the coincidence
    assert p.visible_step_height != p.seating_depth  # but not the same thing


def test_changing_visible_step_height_does_not_disturb_seating_or_backing():
    """Nothing may quietly derive one from the other because they happen to match."""
    p = fp.FabricationProfile.default().with_visible_step_height(1.4)
    assert p.visible_step_height.mm == 1.4
    assert p.seating_depth.mm == 0.80
    assert p.minimum_recess_floor.mm == 0.40
    assert p.backing_thickness.mm == 1.2
    p.validate()  # still a sound profile


def test_changing_seating_depth_does_disturb_the_backing_requirement():
    """The real dependency must still be real."""
    deep = fp.FabricationProfile.default().with_seating_depth(1.00)
    with pytest.raises(fp.ProfileError, match="backing"):
        deep.validate()
    ok = deep.with_backing_thickness(1.4)
    ok.validate()


def test_parameters_with_equal_values_but_different_names_are_not_equal():
    a = fp.Parameter("visible_step_height", 0.8, fp.Evidence.MEASURED, "x")
    b = fp.Parameter("seating_depth", 0.8, fp.Evidence.MEASURED, "x")
    assert a.mm == b.mm
    assert a != b


# --- validation --------------------------------------------------------------


def test_backing_too_thin_names_both_contributing_values():
    bad = fp.FabricationProfile.default().with_backing_thickness(1.0)
    with pytest.raises(fp.ProfileError) as e:
        bad.validate()
    msg = str(e.value)
    assert "0.8" in msg and "0.4" in msg  # seating depth and minimum floor
    assert "1.2" in msg  # what it needs
    assert "backing" in msg.lower()


def test_backing_exactly_at_the_minimum_is_accepted():
    fp.FabricationProfile.default().validate()


def test_every_z_dimension_must_be_a_whole_number_of_layers():
    bad = fp.FabricationProfile.default().with_visible_step_height(0.75)
    with pytest.raises(fp.ProfileError) as e:
        bad.validate()
    msg = str(e.value)
    assert "visible step height" in msg.lower() or "visible_step_height" in msg
    assert "0.75" in msg and "0.2" in msg


def test_clearance_is_not_treated_as_a_z_dimension():
    """0.05 mm is not a layer multiple, and must not be required to be."""
    p = fp.FabricationProfile.default()
    assert not p.per_side_clearance.is_z_dimension
    assert not math.isclose(p.per_side_clearance.mm / p.layer_height.mm, 0.25 * 4)
    p.validate()


def test_z_dimensions_are_the_ones_the_slicer_quantises():
    p = fp.FabricationProfile.default()
    z = {q.name for q in p.parameters() if q.is_z_dimension}
    assert z == {
        "visible_step_height",
        "seating_depth",
        "minimum_recess_floor",
        "backing_thickness",
    }


def test_non_positive_values_are_rejected():
    for setter in ("with_seating_depth", "with_visible_step_height"):
        bad = getattr(fp.FabricationProfile.default(), setter)(0.0)
        with pytest.raises(fp.ProfileError):
            bad.validate()


# --- reporting ---------------------------------------------------------------


def test_report_carries_evidence_levels_so_a_reader_can_see_what_is_measured():
    p = fp.FabricationProfile.default()
    d = p.to_dict()
    assert d["parameters"]["seating_depth"]["evidence"] == "measured"
    assert d["parameters"]["per_side_clearance"]["evidence"] == "held"
    assert d["parameters"]["minimum_recess_floor"]["evidence"] == "engineering_choice"
    for entry in d["parameters"].values():
        assert entry["scope"]


def test_markdown_report_states_evidence_and_flags_what_is_not_measured():
    md = fp.FabricationProfile.default().to_markdown()
    assert "measured" in md
    assert "engineering_choice" in md or "engineering choice" in md
    assert "0.80" in md and "0.40" in md


def test_report_is_json_safe():
    import json

    json.dumps(fp.FabricationProfile.default().to_dict())


# --- product/spike separation ------------------------------------------------


def _imported_modules(pkg_root: Path) -> set[str]:
    found: set[str] = set()
    for path in pkg_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)
    return found


def test_the_product_package_does_not_import_the_spike():
    root = Path(fp.__file__).resolve().parents[2] / "layercake"
    assert root.is_dir(), root
    offenders = {m for m in _imported_modules(root) if "layercake_spike" in m}
    assert offenders == set(), offenders
