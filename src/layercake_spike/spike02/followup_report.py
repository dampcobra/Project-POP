"""Reports for the depth-only follow-up round."""

from __future__ import annotations

from . import params
from .report02 import _ARC_CAVEAT, _SELF_INTERSECTION_CAVEAT


def build_followup_summary(result, mesh_reports, placements) -> dict:
    """Assemble `depth-followup-parameters.json`."""
    backing = params.DEPTH_FOLLOWUP_BACKING_MM
    cells = [
        {
            "depth_mm": c.depth,
            "clearance_mm": c.clearance,
            "label": c.label,
            "marker_count": i + 1,
            "child_thickness_mm": params.child_thickness(c.depth),
            "layers_engaged": round(c.depth / params.LAYER_HEIGHT_MM),
            "clean_layers_engaged": round(c.depth / params.LAYER_HEIGHT_MM) - 1,
            "support_floor_mm": c.floor.floor_mm,
            "support_floor_ok": c.floor.ok,
            "seated_top_mm": (backing - c.depth) + params.child_thickness(c.depth),
            "achieved_clearance_mm": c.outline["achieved_clearance_mm"],
            "visible_outline_area_mm2": c.outline["area_mm2"],
            "z_planes": c.z_planes.to_dict(),
        }
        for i, c in enumerate(result.cells)
    ]

    criteria = {
        "one_variable_only": len({c["clearance_mm"] for c in cells}) == 1,
        "support_continuous": all(c["support_floor_ok"] for c in cells),
        "seated_tops_flush": all(
            abs(c["seated_top_mm"] - (backing + params.H_VISIBLE_STEP_MM)) < 1e-9
            for c in cells
        ),
        "child_thickness_is_h_plus_d": all(
            abs(c["child_thickness_mm"] - (params.H_VISIBLE_STEP_MM + c["depth_mm"]))
            < 1e-12
            for c in cells
        ),
        "replicates_present": len(result.children)
        == len(cells) * params.DEPTH_FOLLOWUP_REPLICATES,
        "meshes_manifold": all(r.ok for r in mesh_reports),
    }

    return {
        "spike": "02 follow-up - recess depth sweep",
        "issue": "dampcobra/Project-POP#3",
        "round": 2,
        "question": "How deep should a registration recess be?",
        "acceptance_target": (
            "Positive registration during normal glue-up handling. NOT dry "
            "retention, and NOT a friction fit."
        ),
        "held_constant": {
            "clearance_mm": params.DEPTH_FOLLOWUP_CLEARANCE_MM,
            "clearance_rationale": (
                "Round 1 could not resolve clearance: nominally identical children "
                "felt different, so process variation is at least as large as the "
                "ladder step. Held at the process floor as a fixed condition, not "
                "chosen as an optimum."
            ),
            "shape": "12 x 12 mm square, identical to round 1 for comparability",
            "slicer_layer_height_mm": params.LAYER_HEIGHT_MM,
            "elephant_foot_compensation_mm": 0.15,
            "visible_step_height_mm": params.H_VISIBLE_STEP_MM,
        },
        "changed_from_round_1": {
            "backing_thickness_mm": backing,
            "previous_backing_mm": params.ROUND1_AS_PRINTED_BACKING_MM,
            "rationale": (
                "The artwork backing is H (0.8 mm), which cannot host a 0.8 mm "
                "recess -- the floor vanishes and the pipeline rejects it as a "
                "through-hole. The backing is structural and conceptually "
                "independent of the visible artwork colours, so thickening the "
                "fixture applies existing architecture rather than altering the Z "
                "model. H is unchanged and seated tops still finish flush."
            ),
        },
        "replicates_per_depth": params.DEPTH_FOLLOWUP_REPLICATES,
        "criteria": criteria,
        "pass": all(criteria.values()),
        "cells": cells,
        "derived_geometry_inspection": {
            "mode": "report_only",
            "thin_support_count": sum(
                1
                for f in result.derived_feature_findings
                if f.kind == "thin_derived_support"
            ),
            "corner_artifact_count": sum(
                1 for f in result.derived_feature_findings if f.kind == "corner_artifact"
            ),
        },
        "validation": {
            "tool_notes": [_SELF_INTERSECTION_CAVEAT, _ARC_CAVEAT],
            "bodies": [r.to_dict() for r in mesh_reports],
        },
        "plate_layout": [
            {"name": p.name, "dx": p.dx, "dy": p.dy, "dz": p.dz} for p in placements
        ],
        "measured_result": {
            "status": "measured, provisional",
            "default_recess_depth_mm": params.MEASURED_DEFAULT_DEPTH_MM,
            "default_recess_depth_layers": params.MEASURED_DEFAULT_DEPTH_LAYERS,
            "assessment": (
                "0.80 mm gives the best balance of positive guidance, resistance "
                "to rocking/tilting, and easy removal before glue. 0.40 and 0.60 "
                "are usable but feel less positively located; 1.00 is deeper than "
                "necessary and does not improve handling enough to justify it."
            ),
            "scope": (
                "Measured for one process: Bambu P1S, 0.20 mm layer height, "
                "0.15 mm elephant-foot compensation, 12 x 12 mm square seating "
                "footprint. A provisional default, not a universal constant."
            ),
            "layer_hypothesis": (
                "Expressed in layers the result is 4 engaged, 3 of them printed "
                "under normal conditions. If engagement count is the governing "
                "mechanism the preferred depth scales with layer height (0.64 mm "
                "at 0.16 mm layers, 1.12 mm at 0.28 mm). That is a hypothesis "
                "implied by the data, NOT a tested result -- only the 0.20 mm "
                "case has been measured."
            ),
            "clearance_status": (
                "0.05 mm remains a HELD process-floor value, not a proven "
                "fine-resolution optimum. Round 1 could not resolve clearance "
                "because process variation exceeded the ladder step, and round 2 "
                "held it fixed, so neither round measured it."
            ),
            "backing_consequence": {
                "min_backing_mm": params.MIN_BACKING_FOR_DEFAULT_DEPTH_MM,
                "note": (
                    "At H = 0.8 mm the artwork backing cannot host a 0.80 mm "
                    "recess: the floor would be zero and the pipeline refuses it. "
                    "Adopting this default requires the structural backing to be "
                    "decoupled from H in the product, not only in the test "
                    "fixture. Visible step heights are unaffected."
                ),
            },
            "per_depth": {
                "0.40": "usable, less positively located",
                "0.60": "usable, less positively located",
                "0.80": "PREFERRED - best balance",
                "1.00": "deeper than necessary; no worthwhile handling gain",
            },
        },
        "limitations": [
            "Recess variation is NOT replicated: one recess per depth. Only child "
            "variation is captured, by the three replicates.",
            "Clearance is held, not measured; this round says nothing new about it.",
            "The S1/S2 shape controls are deliberately not re-run.",
        ],
    }


def followup_to_markdown(summary: dict) -> str:
    """Andy's observation sheet for the depth sweep."""
    hc = summary["held_constant"]
    ch = summary["changed_from_round_1"]
    lines = [
        "# Spike 02 follow-up - recess depth sweep",
        "",
        f"**Question:** {summary['question']}",
        "",
        f"**Acceptance target:** {summary['acceptance_target']}",
        "",
        "## Held constant",
        "",
        f"- Clearance **{hc['clearance_mm']} mm**. {hc['clearance_rationale']}",
        f"- Shape: {hc['shape']}.",
        f"- **Print at {hc['slicer_layer_height_mm']} mm layer height** with "
        f"**{hc['elephant_foot_compensation_mm']} mm elephant-foot compensation**, "
        "as round 1. Changing either breaks comparability with the first results.",
        f"- Visible step height H = {hc['visible_step_height_mm']} mm.",
        "",
        "## Changed from round 1",
        "",
        f"Backing **{ch['previous_backing_mm']} -> {ch['backing_thickness_mm']} mm**. "
        + ch["rationale"],
        "",
        "## Cells",
        "",
        "| Depth (mm) | Label | Dimples on child | Child thickness (mm) | "
        "Layers engaged | Of those, printed normally | Support floor (mm) |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in summary["cells"]:
        lines.append(
            f"| {c['depth_mm']:.2f} | `{c['label']}` | {c['marker_count']} | "
            f"{c['child_thickness_mm']:.2f} | {c['layers_engaged']} | "
            f"{c['clean_layers_engaged']} | {c['support_floor_mm']:.2f} |"
        )

    lines += [
        "",
        "**Identifying the children.** Each carries engraved dimples on its top "
        "face; the count gives the depth (1 = 0.40, 2 = 0.60, 3 = 0.80, "
        "4 = 1.00 mm). They are engraved rather than raised so they cannot "
        "interfere with the flushness check.",
        "",
        "**Why the layer columns matter.** At a 0.20 mm layer height a 0.20 mm "
        "recess engaged exactly one layer -- the first one, which carries squish, "
        "elephant-foot compensation and bed-levelling error. No well-formed "
        "material did any registering at all, which is the likeliest explanation "
        "for round 1's result. Each step in this sweep adds one clean layer.",
        "",
        f"There are **{summary['replicates_per_depth']} identical children per "
        "depth**. Please test all three: spread between them is print variation, "
        "and in round 1 that was large enough to change a conclusion.",
        "",
        "## Physical observations - Andy",
        "",
        "| Depth | Rep | Insertion | Registration feel | Tilt / rock | "
        "Stays put during handling | Removal for dry fit | Notes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for c in summary["cells"]:
        for rep in range(1, summary["replicates_per_depth"] + 1):
            lines.append(f"| {c['depth_mm']:.2f} | {rep} |  |  |  |  |  |  |")

    lines += [
        "",
        "**Handling is the acceptance criterion, not dry retention.** A piece that "
        "locates accurately and stays put while the assembly is moved to glue-up "
        "is a pass, even if it lifts out when inverted. A piece needing force, or "
        "one that will not come back out for a dry fit, has gone past being a "
        "guide and become a press fit -- which the design principle rules out.",
        "",
        "## Decision",
        "",
        "| Question | Answer |",
        "|---|---|",
        "| Shallowest depth giving acceptable registration |  |",
        "| Deepest depth still comfortably a guide, not a press fit |  |",
        "| Proposed default recess depth |  |",
        "| Does the sweep bracket the answer, or is more depth still wanted? |  |",
        "",
        "## Limitations of this round",
        "",
    ]
    lines += [f"- {n}" for n in summary["limitations"]]
    lines += ["", "## Validation caveats", ""]
    lines += [f"- {n}" for n in summary["validation"]["tool_notes"]]

    mr = summary.get("measured_result")
    if mr:
        lines += [
            "",
            "---",
            "",
            "# Result (measured)",
            "",
            f"**Provisional default recess depth: {mr['default_recess_depth_mm']} mm** "
            f"({mr['default_recess_depth_layers']} layers at "
            f"{summary['held_constant']['slicer_layer_height_mm']} mm layer height).",
            "",
            mr["assessment"],
            "",
            "| Depth (mm) | Verdict |",
            "|---|---|",
        ]
        lines += [f"| {k} | {v} |" for k, v in mr["per_depth"].items()]
        lines += [
            "",
            f"**Scope.** {mr['scope']}",
            "",
            f"**Clearance.** {mr['clearance_status']}",
            "",
            f"**In layers.** {mr['layer_hypothesis']}",
            "",
            "**Consequence for the artwork backing.** "
            + mr["backing_consequence"]["note"]
            + f" Minimum backing for this default: "
            f"{mr['backing_consequence']['min_backing_mm']} mm.",
        ]
    return "\n".join(lines) + "\n"
