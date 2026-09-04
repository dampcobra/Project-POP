"""Manufacturability cleanup: find features thinner than the nozzle, remove them.

Detection is a morphological opening -- shrink by half the minimum feature
width, then grow back by the same amount. Anything narrower than the threshold
vanishes on the shrink and never returns, so `original - opened` is exactly the
set of unmanufacturable slivers.

Policy for this spike, set by Andy in Session 0: **detect, report, remove**.
The tab must never reach mesh generation, and the removal must be recorded with
the threshold that caused it.

Architectural note -- why cleanup is topology-aware
---------------------------------------------------
The obvious implementation returns the opened geometry directly. That is wrong
here. Opening operates on *all* of a region's rings, so it also erodes the hole
where colour C sits, moving B's copy of the shared boundary by up to half the
minimum feature width while C's copy stays put. The result still looks fine in
a render and still slices, but the shared-boundary invariant is gone and the
two bodies no longer meet exactly.

So cleanup opens the **outer** ring only, then re-cuts the holes from the
authoritative region geometry with a boolean difference. Shared boundaries are
reinstated bit-exact by construction. This is a genuine finding of the spike:
manufacturability cleanup cannot be a dumb geometric filter -- it has to know
which boundaries are shared and leave them alone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from . import clipper, spec

Ring = list[tuple[float, float]]


@dataclass(frozen=True)
class Finding:
    """One manufacturability problem, and what was done about it."""

    region: str
    kind: str
    detail: str
    area_mm2: float
    min_feature_mm: float
    action: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_thin_features(
    rings: list[Ring], min_feature: float
) -> tuple[list[Ring], list[Ring]]:
    """Split `rings` into (opened geometry, slivers thinner than `min_feature`).

    The opening radius is half the feature width: a bar of width `w` survives a
    shrink of `w/2` only if `w >= min_feature`.
    """
    radius = min_feature / 2.0
    opened = clipper.offset(clipper.offset(rings, -radius), +radius)
    slivers = clipper.boolean_op(rings, opened, "difference") if opened else list(rings)
    return opened, slivers


def clean_region(
    outer: Ring,
    holes: list[Ring],
    min_feature: float = spec.MIN_FEATURE_MM,
    region_id: str = "?",
) -> tuple[Ring, list[Ring], list[Finding]]:
    """Clean one region, preserving its shared boundaries exactly.

    Returns `(cleaned_outer, cleaned_holes, findings)`. `cleaned_holes` are the
    authoritative hole rings re-cut into the cleaned outer, so a caller can rely
    on them being identical to the rings it passed in.
    """
    findings: list[Finding] = []

    opened, slivers = detect_thin_features([outer], min_feature)

    for sliver in slivers:
        a = abs(clipper.area(sliver))
        if a <= spec.SLIVER_AREA_EPS_MM2:
            continue  # numerical dust from the offset round trip, not a feature
        xs = [p[0] for p in sliver]
        ys = [p[1] for p in sliver]
        findings.append(
            Finding(
                region=region_id,
                kind="thin_feature",
                detail=(
                    f"feature thinner than {min_feature} mm at "
                    f"x {min(xs):.3f}..{max(xs):.3f}, y {min(ys):.3f}..{max(ys):.3f}"
                ),
                area_mm2=a,
                min_feature_mm=min_feature,
                action="removed",
            )
        )

    if not opened:
        findings.append(
            Finding(
                region=region_id,
                kind="region_erased",
                detail=f"whole region is thinner than {min_feature} mm",
                area_mm2=abs(clipper.area(outer)),
                min_feature_mm=min_feature,
                action="rejected",
            )
        )
        return list(outer), list(holes), findings

    # Largest ring is the region body; smaller ones would be fragments.
    cleaned_outer = max(opened, key=lambda r: abs(clipper.area(r)))
    for frag in opened:
        if frag is not cleaned_outer:
            findings.append(
                Finding(
                    region=region_id,
                    kind="fragment",
                    detail="region split into disconnected fragments by cleanup",
                    area_mm2=abs(clipper.area(frag)),
                    min_feature_mm=min_feature,
                    action="dropped",
                )
            )

    # Re-cut holes from the authoritative rings so shared boundaries are exact.
    cleaned_holes = _recut_holes(cleaned_outer, holes)
    return cleaned_outer, cleaned_holes, findings


def _recut_holes(outer: Ring, holes: list[Ring]) -> list[Ring]:
    """Reinstate `holes` inside `outer`, returned in their authored form.

    The difference confirms each hole still lies within the cleaned outer; the
    ring handed back is the original, so the shared boundary is bit-exact
    rather than a re-derived approximation.
    """
    if not holes:
        return []
    kept: list[Ring] = []
    for hole in holes:
        remaining = clipper.boolean_op([outer], [hole], "difference")
        if len(remaining) > 1:  # a hole was actually cut => it is inside
            kept.append(list(hole))
    return kept


@dataclass
class CleanupReport:
    """Report artefact for Issue #1's manufacturability cleanup requirement."""

    min_feature_mm: float
    policy: str
    findings: list[Finding]

    def to_dict(self) -> dict:
        return {
            "min_feature_mm": self.min_feature_mm,
            "policy": self.policy,
            "findings": [f.to_dict() for f in self.findings],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Manufacturability cleanup report",
            "",
            f"- **Minimum feature width:** {self.min_feature_mm} mm "
            "(0.4 mm nozzle assumption, not yet physically validated)",
            f"- **Detection method:** morphological opening at radius "
            f"{self.min_feature_mm / 2} mm (Clipper2 miter offset)",
            f"- **Reporting floor:** {spec.SLIVER_AREA_EPS_MM2} mm2 -- below this a "
            "sliver is offset round-trip noise, not a feature",
            f"- **Policy:** {self.policy}",
            "",
            "## Findings",
            "",
        ]
        if not self.findings:
            lines.append("No manufacturability problems detected.")
        else:
            lines += [
                "| Region | Kind | Area (mm2) | Action | Detail |",
                "|---|---|---|---|---|",
            ]
            lines += [
                f"| {f.region} | {f.kind} | {f.area_mm2:.4f} | {f.action} | {f.detail} |"
                for f in self.findings
            ]
        lines += [
            "",
            "## Shared-boundary safety",
            "",
            "Cleanup opens each region's **outer** ring only, then re-cuts holes",
            "from the authoritative region geometry. A naive opening would also",
            "erode shared boundaries, moving one region's copy of a boundary",
            "while its neighbour's stayed put. See `cleanup.py` for detail.",
        ]
        return "\n".join(lines) + "\n"
