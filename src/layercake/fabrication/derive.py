"""The canonical to fabrication derivation.

One entry point::

    derive(artwork, profile) -> FabricationResult

Stacking is obtained here rather than asked of the caller. It is deterministically
derivable from canonical containment, so taking it as an argument would put two
truths in play and invite them to disagree::

    artwork  ->  derive_stacking_order()  ->  fabrication derivation

What this does and does not do
------------------------------
It ends at a `FabricationResult`: bodies, the stacking order they were placed
from, and report-only findings. No meshes, no export, no plate layout, no slicer.

Nothing is written back. The canonical artwork and the stacking order are inputs
and stay exactly as they were -- asserted by test, not merely intended.

Derived geometry is **inspected, never repaired**. Spike 01's minimum-feature
cleanup belongs to canonical geometry, before derivation; running it over derived
geometry would erase the clearances that make the thing assemble. So the
inspection here is report-only, and its findings distinguish genuinely thin
support from the corner artefacts a morphological probe always produces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..canonical.artwork import CanonicalArtwork
from ..geometry import polygons as poly
from ..stacking import StackingOrder, derive_stacking_order
from .body import (
    FabricationBodies,
    FabricationBody,
    FabricationError,
)
from .geometry import erode, offset_rings
from .profile import FabricationProfile
from .strategy import SUPPORTED_CHILD, SupportedChildStrategy
from .zplan import body_z_extent, check_floor_is_sound


@dataclass(frozen=True)
class Finding:
    """One report-only observation about derived geometry.

    Never acted on automatically. `kind` separates a genuine defect from the
    artefacts a morphological probe produces by its nature.
    """

    kind: str
    region_id: str
    detail: str
    area_mm2: float = 0.0
    action: str = "reported_only"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "region_id": self.region_id,
            "detail": self.detail,
            "area_mm2": self.area_mm2,
            "action": self.action,
        }


@dataclass(frozen=True)
class FabricationResult:
    """Everything the derivation produced, and what it was placed from."""

    bodies: FabricationBodies
    stacking: StackingOrder
    profile: FabricationProfile
    strategy_name: str
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    # -- inspection -----------------------------------------------------------

    def body_for(self, region_id: str) -> FabricationBody:
        """The body realising a canonical region."""
        return self.bodies.body_for(region_id)

    def region_ids(self) -> tuple[str, ...]:
        return self.bodies.region_ids()

    def level_of(self, region_id: str) -> int:
        """The stacking level a region's body was placed at."""
        return self.stacking.level_of(region_id)

    def voids_of(self, region_id: str) -> tuple:
        """The genuine voids left open in a region's body."""
        return self.body_for(region_id).footprint.void_holes

    # -- registration freedom -------------------------------------------------

    def seating_path(self, ancestor: str, descendant: str) -> tuple[str, ...]:
        """The chain of regions seated one into the next, ancestor first.

        Read off the derived bodies rather than the artwork: the path is built
        from actual seating relationships, so each step is a body that hosts a
        pocket for the next.

            registration freedom is defined only along actual derived
            seating relationships.

            No seating relationship
                -> no registration-freedom value under this model.

        So a missing seating is not a zero. It raises, because the model has
        nothing to say rather than something to say that happens to be zero.
        Two siblings are the clearest example: they seat into the same parent,
        never into each other, and the question has no answer.

        This matters most for strategies that do not yet exist. An island insert
        seats into no pocket, but that must not be read as "no play" -- its
        location could be set by entirely different geometry, which has not been
        designed. Raising keeps that question open; returning zero would answer
        it wrongly and silently.

        Raises `FabricationError` if no chain of seatings leads from `ancestor`
        down to `descendant`.
        """
        for region_id in (ancestor, descendant):
            if region_id not in self.bodies.region_ids():
                raise FabricationError(f"no derived body for region {region_id!r}")

        chain = [descendant]
        seen = {descendant}
        current = descendant
        while current != ancestor:
            parent = self._host_of(current)
            if parent is None or parent in seen:
                raise FabricationError(
                    f"region {descendant!r} does not seat inside {ancestor!r}: "
                    "registration freedom accumulates along a parent/child "
                    "path, so it is only defined between an ancestor and a "
                    "descendant. Two siblings do not seat into each other and "
                    "contribute no play to one another."
                )
            seen.add(parent)
            chain.append(parent)
            current = parent
        return tuple(reversed(chain))

    def registration_freedom(self, ancestor: str, descendant: str) -> float:
        """Worst-case play of `descendant` relative to `ancestor`, per side, in mm.

            worst-case freedom  =  sum of the per-side seating clearances
                                   along that ancestry path

        Spike 02 measured this over two seatings and reported it as evidence.
        The meaning is unchanged here, only generalised: every seating on the
        path contributes its own per-side play, so error accumulates linearly
        with relief depth however deep the artwork goes.

        It is **ancestry-path accumulation, not stacking-level accumulation**.
        Siblings sit at the same level and contribute nothing to each other.

        Defined only where a seating path exists -- see `seating_path`. Where
        none does, this raises rather than returning zero: the model has no
        value to give, which is not the same as a value of zero.

        A region relative to itself is the one degenerate case: the path is
        real but has no seatings on it, so the freedom is genuinely 0.0.

        Note: the per-seating clearance is read from the profile, which is
        correct while every pocket is cut at the profile's clearance. Should a
        strategy ever vary clearance per pocket, that value belongs on `Pocket`
        and this should read it from there instead.
        """
        path = self.seating_path(ancestor, descendant)
        # Every consecutive pair on a seating path is a seating by
        # construction, so each contributes its per-side clearance. There is
        # deliberately no "and zero otherwise" branch here: a step that is not
        # a seating cannot be on the path at all.
        return self.profile.per_side_clearance.mm * (len(path) - 1)

    def _host_of(self, region_id: str) -> str | None:
        """The body whose pocket seats this region, or None if nothing seats it."""
        for body in self.bodies:
            if body.hosts(region_id):
                return body.region_id
        return None

    def thin_support_findings(self) -> tuple[Finding, ...]:
        """Findings that are genuine defects rather than probe artefacts."""
        return tuple(f for f in self.findings if f.kind == "thin_derived_support")

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy_name,
            "profile": self.profile.to_dict(),
            "stacking": self.stacking.to_dict(),
            "bodies": self.bodies.to_dict()["bodies"],
            "levels": {
                region_id: self.level_of(region_id)
                for region_id in self.bodies.region_ids()
            },
            "findings": [f.to_dict() for f in self.findings],
            "inspection_note": (
                "Derived geometry is inspected report-only and never repaired. "
                "Canonical minimum-feature cleanup applies to canonical geometry "
                "before derivation; running it here would erase the clearances "
                "under test. 'corner_artifact' findings are an artefact of the "
                "morphological probe, not defects."
            ),
        }


def derive(
    artwork: CanonicalArtwork,
    profile: FabricationProfile,
    *,
    strategy: SupportedChildStrategy = SUPPORTED_CHILD,
) -> FabricationResult:
    """Derive fabrication bodies from canonical artwork and a fabrication profile.

    Stacking order is derived internally from the artwork's containment.

    `strategy` decides how a child is supported. Only the supported-child
    strategy exists in this milestone; it is a parameter so that adding an
    island-insert strategy later is a new class rather than a rewrite. Artwork
    that is canonically valid but unbuildable under the chosen strategy raises
    `FabricationError` from the strategy, not from here.

    Raises `ProfileError` if the profile itself is unmanufacturable, and
    `FabricationError` if this artwork cannot be built under this strategy.
    """
    profile.validate()
    stacking = derive_stacking_order(artwork)

    bodies: list[FabricationBody] = []
    for region_id in sorted(artwork.regions):
        level = stacking.level_of(region_id)
        z = body_z_extent(level, profile)

        footprint = strategy.footprint_for(artwork, region_id)
        pockets = strategy.pockets_for(artwork, region_id, profile, footprint)

        if pockets:
            check_floor_is_sound(level, region_id, profile)

        bodies.append(
            FabricationBody(
                region_id=region_id, footprint=footprint, z=z, pockets=pockets
            )
        )

    result_bodies = FabricationBodies(bodies=tuple(bodies))
    return FabricationResult(
        bodies=result_bodies,
        stacking=stacking,
        profile=profile,
        strategy_name=strategy.name,
        findings=inspect_derived_geometry(result_bodies, profile),
    )


def inspect_derived_geometry(
    bodies: FabricationBodies, profile: FabricationProfile
) -> tuple[Finding, ...]:
    """Look for thin support in derived geometry. Report only; never repair.

    A morphological opening finds two different things and only one is a defect.
    It cannot reproduce an internal corner tighter than its own probe radius, so
    every concave corner registers -- and pocket corners are radiused by the
    clearance, all tighter than the probe. Those are `corner_artifact`. A genuine
    `thin_derived_support` is long as well as narrow, so it is distinguished by
    extending further than the minimum feature width in at least one direction.

    Spike 02 established this distinction after 23 findings on one coupon turned
    out to be 23 corner artefacts and zero defects.
    """
    minimum = profile.minimum_recess_floor.mm
    radius = minimum / 2.0
    findings: list[Finding] = []

    for body in bodies:
        support = poly.boolean_op(
            body.footprint.rings(),
            [list(p.footprint) for p in body.pockets],
            "difference",
        )
        if not support:
            continue

        opened = offset_rings(erode(support, radius), radius)
        slivers = (
            poly.boolean_op(support, opened, "difference") if opened else support
        )

        for sliver in slivers:
            sliver_area = abs(poly.area(sliver))
            if sliver_area <= _SLIVER_AREA_TOLERANCE:
                continue
            xs = [p[0] for p in sliver]
            ys = [p[1] for p in sliver]
            width, height = max(xs) - min(xs), max(ys) - min(ys)
            extent = max(width, height)

            # An offset round trip leaves a hairline sliver along every sloped
            # edge. Those are long, so an area floor alone lets them through and
            # a bounding box alone calls them thin support. Average width tells
            # them apart: noise measures a micron or so across, a real feature
            # measures tenths of a millimetre.
            if extent > 0 and sliver_area / extent < _NOISE_WIDTH_MM:
                continue

            corner = extent < minimum
            findings.append(
                Finding(
                    kind="corner_artifact" if corner else "thin_derived_support",
                    region_id=body.region_id,
                    detail=(
                        (
                            f"internal corner tighter than the {radius} mm probe; "
                            "a nozzle rounds this and nothing is lost"
                        )
                        if corner
                        else f"support thinner than {minimum} mm over a run"
                    )
                    + f" at x {min(xs):.3f}..{max(xs):.3f}, y {min(ys):.3f}..{max(ys):.3f}",
                    area_mm2=sliver_area,
                )
            )
    return tuple(findings)


#: Below this, a sliver is offset round-trip noise rather than a feature. An
#: area, deliberately not a reused length -- a Spike 01 lesson.
_SLIVER_AREA_TOLERANCE = 1e-3

#: Average width below which a sliver is a hairline along an edge rather than a
#: feature. Spike 01 filtered this noise by area alone, which works for a short
#: sliver; a long one hugging a sloped edge has enough area to pass that floor
#: while averaging a micron across. Ten microns sits an order of magnitude above
#: the noise and an order of magnitude below anything a 0.4 mm nozzle can build.
_NOISE_WIDTH_MM = 0.01
