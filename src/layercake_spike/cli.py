"""The spike pipeline end to end, writing every artefact Issue #1 asks for.

Pipeline order matters and mirrors the architecture under test:

    author exact vectors
      -> union in the deliberately undersized tab
      -> build the canonical partition (shared vertices and edges)
      -> validate the band numerically (gap / overlap)
      -> manufacturability cleanup (detect, report, remove)
      -> rebuild the partition from cleaned geometry
      -> extrude each region into its own body
      -> validate each body for manifoldness
      -> export separate, co-registered STLs

Cleanup runs *before* mesh generation, so an unmanufacturable feature can
never reach an STL. Bodies are never translated, so a shared origin is a
property of the pipeline rather than something to check afterwards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import trimesh

from . import cleanup, clipper, extrude, reports, spec, svgdebug, topology, validate


def _dirty_b_outer() -> list[tuple[float, float]]:
    """B with the deliberately undersized tab fused on."""
    merged = clipper.boolean_op([spec.B_OUTER_RING], [spec.TAB_RING], "union")
    return max(merged, key=lambda r: abs(clipper.area(r)))


def _island_anchoring(partition: topology.Partition) -> dict:
    """Check every artwork island rests on the band below it.

    An island exported as its own body is only mechanically secure if it sits
    directly on the backing. This is 2D contact area, not a mesh property, so
    it belongs here rather than in the manifold validation.
    """
    out: dict[str, dict] = {}
    artwork = partition.regions_in_band(spec.Z_ARTWORK)
    backing = partition.regions_in_band(spec.Z_BACKING)
    if not backing:
        return out

    base_id = backing[0]
    base_rings = partition.solid_rings(base_id)

    for rid in artwork:
        contained_by = [
            other
            for other, kids in partition.containment().items()
            if rid in kids
        ]
        if not contained_by:
            continue  # not an island; it is a top-level region
        contact = clipper.boolean_op(partition.solid_rings(rid), base_rings, "intersection")
        area = abs(clipper.total_area(contact))
        own_area = abs(clipper.total_area(partition.solid_rings(rid)))
        out[rid] = {
            "rests_on": base_id,
            "enclosed_by": contained_by,
            "contact_area_mm2": area,
            "own_area_mm2": own_area,
            "contact_fraction": (area / own_area) if own_area else 0.0,
            "ok": area > 0 and abs(area - own_area) < spec.EPS,
            "note": (
                "Island is exported as an independent body. It is held by resting on "
                "the backing over its whole footprint; there is no mechanical "
                "interlock, so adhesion to the backing is what secures it."
            ),
        }
    return out


def run(outdir: str | Path) -> int:
    """Run the whole spike. Returns 0 if every pass criterion holds."""
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Author geometry, with the undersized tab deliberately present.
    dirty_b = _dirty_b_outer()

    # 2. Manufacturability cleanup, before any mesh is generated.
    clean_b, clean_b_holes, findings = cleanup.clean_region(
        dirty_b, [spec.C_RING], spec.MIN_FEATURE_MM, "B"
    )
    cleanup_report = cleanup.CleanupReport(
        min_feature_mm=spec.MIN_FEATURE_MM,
        policy="detect, report, and remove deterministically before mesh generation",
        findings=findings,
    )

    # 3. Canonical partition from the cleaned geometry.
    partition = topology.Partition.build(
        {
            "A": dict(colour="A", z=spec.Z_BACKING, outer=spec.BACKING_RING, holes=[]),
            "B": dict(colour="B", z=spec.Z_ARTWORK, outer=clean_b, holes=clean_b_holes),
            "C": dict(colour="C", z=spec.Z_ARTWORK, outer=spec.C_RING, holes=[]),
        }
    )

    # 4. Numeric partition validation, per band.
    bands = {
        "backing": partition.validate_band(spec.Z_BACKING, universe=spec.BACKING_RING),
        "artwork": partition.validate_band(spec.Z_ARTWORK, universe=clean_b),
    }

    # 5. Extrude each region into its own body, on the shared origin.
    meshes: dict[str, trimesh.Trimesh] = {}
    for rid, region in partition.regions.items():
        outer = partition.vertices.ring_coords(region.outer)
        holes = [partition.vertices.ring_coords(h) for h in region.holes]
        v, f = extrude.extrude(outer, holes, region.z_min, region.z_max)
        meshes[rid] = trimesh.Trimesh(vertices=v, faces=f, process=False)

    # 6. Per-body manifold validation.
    mesh_reports = [validate.validate_mesh(rid, meshes[rid]) for rid in sorted(meshes)]

    # 7. Export separate, co-registered STLs. No translation is applied.
    for rid, mesh in meshes.items():
        mesh.export(out / spec.BODY_FILENAMES[rid], file_type="stl")

    anchoring = _island_anchoring(partition)

    # 8. Artefacts.
    (out / "topology-dump.json").write_text(
        json.dumps(partition.to_dump(), indent=2), encoding="utf-8"
    )
    svgdebug.render(partition, out / "debug.svg")
    (out / "cleanup-report.md").write_text(cleanup_report.to_markdown(), encoding="utf-8")
    (out / "validation-report.md").write_text(
        validate.reports_to_markdown(mesh_reports), encoding="utf-8"
    )

    summary = reports.build_summary(
        cleanup_report=cleanup_report,
        bands=bands,
        mesh_reports=mesh_reports,
        anchoring=anchoring,
    )
    (out / "spike-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return 0 if summary["pass"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Layercake Spike 01.")
    parser.add_argument(
        "-o",
        "--outdir",
        default="artefacts",
        help="directory to write artefacts into (default: artefacts)",
    )
    args = parser.parse_args(argv)
    code = run(args.outdir)
    status = "PASS" if code == 0 else "FAIL"
    print(f"Spike 01: {status}. Artefacts written to {Path(args.outdir).resolve()}")
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
