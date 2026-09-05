"""The supported-child fabrication strategy.

**This module is the one place that decides a parent stays solid beneath its
children.** That is a strategy, not a property of what a fabrication body is::

    supported child   ->  parent remains solid beneath it
                      ->  shallow seating pocket            <- implemented here

    island insert     ->  genuine void remains
                      ->  child is a separate component     <- not implemented

The second may become a user-selectable choice later. Keeping every decision it
would need to change inside this module is what makes that addable without
dismantling the body model: `FabricationBody`, `Pocket` and `BodyFootprint` say
nothing about support being mandatory, and `derive` asks this module rather than
assuming.

So: nothing outside this module should assume that every child has support, that
every child has a pocket, or that every canonical child-hole is solidified.

Where artwork is canonically valid but cannot be built *under this strategy*, the
refusal is raised here -- at the strategy boundary -- so it is visibly a
consequence of the strategy rather than of the model.

    canonical-valid does not automatically imply fabrication-valid
    under the current strategy
"""

from __future__ import annotations

from dataclasses import dataclass

from ..canonical.artwork import CanonicalArtwork
from ..geometry import polygons as poly
from .body import BodyFootprint, FabricationError, Pocket, solidified_footprint
from .geometry import dilate
from .profile import FabricationProfile


@dataclass(frozen=True)
class SupportedChildStrategy:
    """Every child is supported: its parent stays solid beneath it.

    Named and instantiated rather than implied, so that adding a sibling
    strategy is a new class here plus a parameter on `derive`, not a rewrite.
    """

    name: str = "supported_child"

    description: str = (
        "A parent region remains solid beneath each child it contains, and the "
        "child seats into a shallow registration pocket. Canonical holes that "
        "host a child are solidified; holes with no child stay as genuine voids."
    )

    # -- what the body is made of --------------------------------------------

    def footprint_for(
        self, artwork: CanonicalArtwork, region_id: str
    ) -> BodyFootprint:
        """The plan shape of this region's body under this strategy.

        Child-hosting holes are solidified because *this strategy* supports its
        children. Genuine voids are kept. An island-insert strategy would keep
        the hosting hole open instead, and this is the method it would change.
        """
        return solidified_footprint(artwork, region_id)

    # -- what seats into it ---------------------------------------------------

    def pockets_for(
        self,
        artwork: CanonicalArtwork,
        region_id: str,
        profile: FabricationProfile,
        footprint: BodyFootprint,
    ) -> tuple[Pocket, ...]:
        """One registration pocket per child this region supports.

        The pocket is the child's **outer footprint** dilated by the profile's
        per-side clearance -- not its visible surface. A child physically
        occupies its whole outline; its own holes belong to its own body. Spike
        01's three-level glyph is what makes that distinction visible, and #8
        found the bug by getting it wrong.
        """
        clearance = profile.per_side_clearance.mm
        depth = profile.seating_depth.mm

        pockets: list[Pocket] = []
        for child in artwork.children_of(region_id):
            child_outline = artwork.outer_ring(child)
            recess = dilate(child_outline, clearance)
            self._check_pocket_clears_the_voids(region_id, child, recess, footprint)
            pockets.append(
                Pocket(
                    for_region=child,
                    footprint=tuple((float(x), float(y)) for x, y in recess),
                    depth_mm=depth,
                )
            )
        return tuple(pockets)

    # -- refusals, all raised at this boundary --------------------------------

    def _check_pocket_clears_the_voids(
        self,
        region_id: str,
        child: str,
        recess: list[tuple[float, float]],
        footprint: BodyFootprint,
    ) -> None:
        """A pocket must not run into a void, which would open it to the outside.

        A child adjacent to a genuine void can have its recess pushed into that
        void by the clearance, turning a blind pocket into an opening. Refused
        here: it is a consequence of applying this strategy at this clearance,
        not a defect in the artwork.
        """
        for index, void in enumerate(footprint.void_holes):
            shared = poly.boolean_op([list(recess)], [list(void)], "intersection")
            if abs(poly.total_area(shared)) > _AREA_TOLERANCE:
                raise FabricationError(
                    f"the pocket for {child!r} in region {region_id!r} runs into "
                    f"void {index}: the clearance pushes the recess into a hole, "
                    "so it would open out rather than stay a blind pocket. The "
                    "artwork is canonically valid; it cannot be built under the "
                    f"{self.name} strategy at this clearance."
                )


#: Area below which an overlap is numerical dust rather than a real intersection.
_AREA_TOLERANCE = 1e-9

#: The strategy this milestone builds with. A future island-insert strategy
#: becomes a sibling of this, selected by a parameter on `derive`.
SUPPORTED_CHILD = SupportedChildStrategy()
