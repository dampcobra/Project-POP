"""Spike 02 pipeline, writing every artefact Issue #3 asks for."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import trimesh

from .. import validate
from . import arrange, coupon, params, report02, stack, svgdebug02


def run(outdir: str | Path) -> int:
    """Build the coupon and stack, validate, write artefacts. 0 if all criteria hold."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    result = coupon.build_coupon()
    stacks = {d: stack.build_stack(depth=d) for d in params.DEPTHS_MM}

    # the printed three-level article uses the control depth
    printed = stacks[params.CONTROL_DEPTH_MM]

    bodies: dict[str, trimesh.Trimesh] = {"coupon_fixture": result.fixture_mesh}
    for cell_id, mesh in result.children.items():
        bodies[f"coupon_child_{cell_id}"] = mesh
    for lv in printed.levels:
        bodies[f"stack_{lv.name}"] = lv.mesh

    for name, mesh in bodies.items():
        mesh.export(out / f"{name}.stl", file_type="stl")

    # co-registered assembly: children lowered into their recesses
    seated: dict[str, trimesh.Trimesh] = {"coupon_fixture": result.fixture_mesh}
    for p in result.placements:
        child = result.children[p.cell.cell_id]
        seated[f"coupon_child_{p.cell.cell_id}"] = arrange.translated(
            child, 0.0, 0.0, p.z_planes.recess_floor
        )
    for lv in printed.levels:
        seated[f"stack_{lv.name}"] = lv.mesh
    arrange.assembly(seated).export(out / "assembly_coregistered.stl", file_type="stl")

    plate, placements = arrange.plate_layout(bodies)
    plate.export(out / "plate_layout.stl", file_type="stl")

    pairs = [
        (p.cell.label, p.canonical_footprint, p.recess, p.cell.clearance)
        for p in result.placements
    ]
    svgdebug02.render_pairs(pairs, out / "debug-recesses.svg")

    mesh_reports = [validate.validate_mesh(n, m) for n, m in sorted(bodies.items())]
    (out / "validation-report.md").write_text(
        validate.reports_to_markdown(mesh_reports), encoding="utf-8"
    )

    summary = report02.build_summary(result, stacks, mesh_reports, placements)
    (out / "spike02-parameters.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (out / "spike02-report.md").write_text(
        report02.to_markdown(summary), encoding="utf-8"
    )

    return 0 if summary["pass"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Layercake Spike 02.")
    parser.add_argument("-o", "--outdir", default="artefacts/spike02")
    args = parser.parse_args(argv)
    code = run(args.outdir)
    print(
        f"Spike 02: {'PASS' if code == 0 else 'FAIL'}. "
        f"Artefacts written to {Path(args.outdir).resolve()}"
    )
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
