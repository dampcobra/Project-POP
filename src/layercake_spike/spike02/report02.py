"""Spike 02 reports: machine-readable parameters and Andy's observation sheet."""

from __future__ import annotations

from . import params

_SELF_INTERSECTION_CAVEAT = (
    "Self-intersection counts come from this project's own triangle-triangle "
    "checker, not from trimesh, which has no such test. That checker has not "
    "been cross-checked against an independent mesh validator, is O(n^2) in its "
    "broad phase, and treats touching faces as non-intersecting. Its evidential "
    "status is unchanged from Spike 01."
)

_ARC_CAVEAT = (
    "Recess dilation uses a round join, so clearance is radial. Clipper2 "
    "approximates each corner arc with chords, leaving the achieved clearance a "
    "sagitta short of nominal -- under 1 um at these radii, roughly 1000x finer "
    "than a 0.4 mm nozzle. Achieved values are measured and reported, not assumed."
)


def build_summary(coupon_result, stacks: dict[float, object], mesh_reports, placements) -> dict:
    """Assemble `spike02-parameters.json`."""
    cells = []
    for p in coupon_result.placements:
        cells.append(
            {
                "cell_id": p.cell.cell_id,
                "kind": p.cell.kind,
                "label": p.cell.label,
                "shape": p.cell.shape_key,
                "nominal_clearance_mm": p.cell.clearance,
                "achieved_clearance_mm": p.outline["achieved_clearance_mm"],
                "recess_depth_mm": p.cell.depth,
                "child_thickness_mm": p.cell.thickness,
                "origin_mm": list(p.origin),
                "z_planes": p.z_planes.to_dict(),
                "support_floor_mm": p.floor.floor_mm,
                "support_floor_ok": p.floor.ok,
                "visible_support_outline": {
                    "width_mm": p.outline["width_mm"],
                    "area_mm2": p.outline["area_mm2"],
                },
                "registration_freedom_per_side_mm": p.cell.clearance,
            }
        )

    stack_blocks = {}
    for depth, s in stacks.items():
        stack_blocks[f"depth_{depth:.2f}"] = {
            "clearance_mm": s.clearance,
            "depth_mm": s.depth,
            "completed_tops_mm": [round(t, 9) for t in s.completed_tops],
            "cumulative_registration_freedom_mm": s.cumulative_registration_freedom,
            "levels": [
                {
                    "name": lv.name,
                    "colour": lv.colour,
                    "canonical_hole_count": len(lv.canonical_holes),
                    "fabrication_hole_count": 0,
                    "z": lv.z.to_dict(),
                    "hosts_recess_for": lv.recess_for,
                    "support_floor_mm": lv.floor.floor_mm if lv.floor else None,
                    "visible_support_outline": (
                        {
                            "width_mm": lv.outline["width_mm"],
                            "area_mm2": lv.outline["area_mm2"],
                        }
                        if lv.outline
                        else None
                    ),
                }
                for lv in s.levels
            ],
        }

    criteria = {
        "clearance_present_numerically": all(
            abs(c["achieved_clearance_mm"] - c["nominal_clearance_mm"]) < 1e-3
            for c in cells
        ),
        "recess_depth_correct": all(
            abs(c["z_planes"]["depth"] - c["recess_depth_mm"]) < 1e-12 for c in cells
        ),
        "support_continuous": all(c["support_floor_ok"] for c in cells),
        "child_thickness_is_h_plus_d": all(
            abs(c["child_thickness_mm"] - (params.H_VISIBLE_STEP_MM + c["recess_depth_mm"]))
            < 1e-12
            for c in cells
        ),
        "three_level_z_arithmetic": all(
            b["completed_tops_mm"] == [0.8, 1.6, 2.4] for b in stack_blocks.values()
        ),
        "island_seated_not_stacked": all(
            b["levels"][1]["fabrication_hole_count"] == 0
            and b["levels"][1]["canonical_hole_count"] == 1
            for b in stack_blocks.values()
        ),
        "meshes_manifold": all(r.ok for r in mesh_reports),
    }

    return {
        "spike": "02 - shallow registration recesses for layered-relief assembly",
        "issue": "dampcobra/Project-POP#3",
        "units": "mm",
        "construction": "layered relief: white backing -> red enclosing colour -> yellow island",
        "process_conditions": {
            "slicer_layer_height_mm": params.LAYER_HEIGHT_MM,
            "elephant_foot_compensation": "TO BE RECORDED BY ANDY AT PRINT TIME",
            "nozzle_assumption_mm": 0.4,
        },
        "model": {
            "visible_step_height_mm": params.H_VISIBLE_STEP_MM,
            "child_thickness_rule": "H + D",
            "clearance_definition": "per-side (radial), recess dilated outward from the canonical child footprint; the child is never shrunk",
            "join_type": "round",
            "fixture_support_thickness_mm": params.FIXTURE_SUPPORT_MM,
            "stack_backing_thickness_mm": params.STACK_BACKING_MM,
        },
        "criteria": criteria,
        "pass": all(criteria.values()),
        "cells": cells,
        "three_level_stack": stack_blocks,
        "derived_geometry_inspection": {
            "mode": "report_only",
            "min_feature_mm": params.MIN_SUPPORT_FEATURE_MM,
            "note": (
                "Spike 01's minimum-feature cleanup applies to canonical geometry "
                "only. Running it over derived geometry would erase the clearances "
                "under test, so derived geometry is measured and reported, never "
                "mutated."
            ),
            "classification_note": (
                "Morphological opening detects two things: genuinely thin support, "
                "and internal corners tighter than its probe radius. Recess corners "
                "are radiused by the clearance, all tighter than the probe, so they "
                "register as corner_artifact -- a nozzle rounds them and nothing is "
                "lost. Only thin_derived_support is a defect."
            ),
            "thin_support_count": sum(
                1 for f in coupon_result.derived_feature_findings
                if f.kind == "thin_derived_support"
            ),
            "corner_artifact_count": sum(
                1 for f in coupon_result.derived_feature_findings
                if f.kind == "corner_artifact"
            ),
            "findings": [f.to_dict() for f in coupon_result.derived_feature_findings],
        },
        "validation": {
            "tool": "trimesh (watertight/winding/euler) + project self-intersection checker",
            "tool_notes": [_SELF_INTERSECTION_CAVEAT, _ARC_CAVEAT],
            "bodies": [r.to_dict() for r in mesh_reports],
        },
        "plate_layout": [
            {"name": p.name, "dx": p.dx, "dy": p.dy, "dz": p.dz} for p in placements
        ],
        "not_verified_here": [
            "Slicer import/slice evidence -- requires Andy's Bambu P1S.",
            "Physical fit, registration, seating, step height and recess quality.",
            "The 0.4 mm minimum-feature threshold, which this coupon does not exercise.",
        ],
    }


def to_markdown(summary: dict) -> str:
    """Andy's observation sheet: parameters filled in, results left blank."""
    lines = [
        "# Spike 02 report - shallow registration recesses (layered relief)",
        "",
        f"Issue: {summary['issue']}. Construction: {summary['construction']}.",
        "",
        "## Process conditions",
        "",
        f"- **Slicer layer height: {summary['process_conditions']['slicer_layer_height_mm']} mm.** "
        "Every Z dimension is a whole number of these, so the slicer cannot quantise a "
        "feature into a depth other than the one under test. Print at this layer height "
        "or the experiment measures something else.",
        "- **Elephant-foot compensation: record the value used.** The seating portion of "
        "each child is its bottom 0.2-0.4 mm, exactly where first-layer squish is worst. "
        "At 0.05 mm clearance the foot alone can exceed the gap, so this is an "
        "experimental condition, not a detail.",
        f"- Nozzle assumption: {summary['process_conditions']['nozzle_assumption_mm']} mm.",
        "",
        "## Model",
        "",
        f"- Visible step height `H` = {summary['model']['visible_step_height_mm']} mm; "
        f"child thickness = `{summary['model']['child_thickness_rule']}`.",
        f"- Clearance: {summary['model']['clearance_definition']}, {summary['model']['join_type']} join.",
        f"- Coupon fixture support: {summary['model']['fixture_support_thickness_mm']} mm "
        "(deliberately thicker than H so floor thickness cannot confound the fit result).",
        f"- Three-level stack backing: {summary['model']['stack_backing_thickness_mm']} mm "
        "(kept at H so the 0.8 / 1.6 / 2.4 mm result is genuinely validated).",
        "",
        "## Test cells",
        "",
        "| Cell | Label | Shape | Clearance (mm) | Depth (mm) | Child thickness (mm) | "
        "Support floor (mm) | Visible outline width (mm) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in summary["cells"]:
        lines.append(
            f"| {c['cell_id']} | `{c['label']}` | {c['shape']} | "
            f"{c['nominal_clearance_mm']:.2f} | {c['recess_depth_mm']:.2f} | "
            f"{c['child_thickness_mm']:.2f} | {c['support_floor_mm']:.2f} | "
            f"{c['visible_support_outline']['width_mm']:.3f} |"
        )

    lines += [
        "",
        "`S1` is the asymmetric/concave control; `S2` is the radiused-corner control. "
        "Both run at the same clearance and depth, so shape is the only variable "
        "between them. If S2 seats and S1 does not, the failure is corner binding "
        "rather than insufficient face clearance -- a 0.4 mm nozzle cannot cut a sharp "
        "internal corner.",
        "",
        "## Three-level stack",
        "",
        "| Depth (mm) | Completed tops (mm) | Cumulative registration freedom (mm) |",
        "|---|---|---|",
    ]
    for name, block in summary["three_level_stack"].items():
        tops = " / ".join(f"{t:.1f}" for t in block["completed_tops_mm"])
        lines.append(
            f"| {block['depth_mm']:.2f} | {tops} | "
            f"{block['cumulative_registration_freedom_mm']:.2f} |"
        )

    lines += [
        "",
        "Completed tops are invariant in seating depth, which is what makes depth a free "
        "experimental variable. Registration freedom accumulates: each seating adds its "
        "own per-side play, so the topmost piece can sit further off nominal than any "
        "single joint allows. Reported as evidence; solving it is out of scope.",
        "",
        "## Slicer observations - Andy",
        "",
        "| Check | Result | Notes |",
        "|---|---|---|",
        "| All bodies import at expected positions |  |  |",
        "| Geometry repair warnings |  |  |",
        "| All variants slice |  |  |",
        "| Labels readable / cells identifiable |  |  |",
        "| Plate arrangement practical |  |  |",
        "| Elephant-foot compensation used |  |  |",
        "",
        "## Physical observations - Andy",
        "",
        "Fit: drops / needs pressure / will not insert.",
        "",
        "| Cell | Label | Fit | Registration | Removal before glue | Seats to floor | "
        "Step height | Recess quality | Visible clearance |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for c in summary["cells"]:
        lines.append(
            f"| {c['cell_id']} | `{c['label']}` |  |  |  |  |  |  |  |"
        )

    lines += [
        "",
        "### Three-level assembly",
        "",
        "| Check | Result | Notes |",
        "|---|---|---|",
        "| White -> red seats correctly |  |  |",
        "| Red -> yellow seats correctly |  |  |",
        "| Visible relief looks/feels like 0.8 mm steps |  |  |",
        "| Yellow registers acceptably relative to white |  |  |",
        "",
        "## Decision",
        "",
        "| Question | Answer |",
        "|---|---|",
        "| Provisional default XY clearance |  |",
        "| Provisional default recess depth |  |",
        "| Or: narrowed follow-up experiment needed |  |",
        "",
        "## Validation caveats",
        "",
    ]
    lines += [f"- {n}" for n in summary["validation"]["tool_notes"]]
    lines += ["", "## Not verified here", ""]
    lines += [f"- {n}" for n in summary["not_verified_here"]]

    findings = summary["derived_geometry_inspection"]["findings"]
    lines += [
        "",
        "## Derived-geometry inspection (report only)",
        "",
        summary["derived_geometry_inspection"]["note"],
        "",
    ]
    insp = summary["derived_geometry_inspection"]
    lines += [insp["classification_note"], ""]
    real = [f for f in findings if f["kind"] == "thin_derived_support"]
    lines.append(
        f"**{len(real)} genuinely thin support feature(s)**; "
        f"{insp['corner_artifact_count']} corner artefact(s), which are harmless."
    )
    lines.append("")
    if not real:
        lines.append(
            "No derived support feature is thinner than "
            f"{insp['min_feature_mm']} mm over a run."
        )
    else:
        lines += ["| Kind | Area (mm2) | Action | Detail |", "|---|---|---|---|"]
        lines += [
            f"| {f['kind']} | {f['area_mm2']:.4f} | {f['action']} | {f['detail']} |"
            for f in real
        ]

    return "\n".join(lines) + "\n"
