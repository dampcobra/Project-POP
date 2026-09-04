"""Aggregate the spike's pass/fail criteria into one machine-readable summary."""

from __future__ import annotations

from . import spec
from .cleanup import CleanupReport
from .topology import BandReport
from .validate import MeshReport


def build_summary(
    *,
    cleanup_report: CleanupReport,
    bands: dict[str, BandReport],
    mesh_reports: list[MeshReport],
    anchoring: dict,
) -> dict:
    """Assemble `spike-summary.json`.

    Criterion names track the "Pass / fail criteria" headings in Issue #1, so
    the artefact can be read straight against the issue.
    """
    tab_findings = [f for f in cleanup_report.findings if f.kind == "thin_feature"]

    criteria = {
        "shared_boundaries": all(b.ok for b in bands.values()),
        "concave_geometry": all(r.ok for r in mesh_reports),
        "island_containment": all(a["ok"] for a in anchoring.values()) if anchoring else False,
        "minimum_feature_handling": bool(tab_findings)
        and all(f.action in ("removed", "rejected") for f in tab_findings),
        "manifold_validity": all(r.ok for r in mesh_reports),
    }

    return {
        "spike": "01 - canonical topology and manifold STL export",
        "issue": "dampcobra/Project-POP#1",
        "units": "mm",
        "tolerances": {
            "eps_mm": spec.EPS,
            "clipper_scale": spec.CLIPPER_SCALE,
            "sliver_area_eps_mm2": spec.SLIVER_AREA_EPS_MM2,
        },
        "criteria": criteria,
        "pass": all(criteria.values()),
        "band_validation": {name: b.to_dict() for name, b in bands.items()},
        "cleanup": cleanup_report.to_dict(),
        "island_anchoring": anchoring,
        "validation": {
            "tool": "trimesh (watertight/winding/euler) + project self-intersection checker",
            "tool_notes": mesh_reports[0].tool_notes if mesh_reports else [],
            "bodies": [r.to_dict() for r in mesh_reports],
        },
        "not_verified_here": [
            "Bambu Studio import/slice evidence -- requires Andy's validation slicer.",
            "Physical print observations -- requires a physical print.",
            "Self-intersection results come from this project's own checker, since "
            "trimesh has no such test; it has not been cross-checked against an "
            "independent mesh validator.",
        ],
    }
