"""Fabrication bodies: the physical article a canonical region becomes.

Canonical artwork says what colour is *visible* where. A fabrication body says
what material actually exists, and the two are deliberately not the same shape
(ADR 0002 decision 2, ADR 0003 decision 4).

The distinction this module makes explicit
------------------------------------------
A canonical region's hole means one of two quite different things, and which one
it is has to be *stated* in the model rather than rediscovered later from an
anonymous polygon::

    hole that hosts a child   ->  solidified: the body is solid beneath the
                                  child, carrying a shallow registration Pocket
                                  that names the child it seats

    hole with no child        ->  a genuine void: it stays a real hole in the
                                  body, because nothing covers it and something
                                  beneath it shows through

So `BodyFootprint.void_holes` holds only the second kind. The first kind is gone
from the footprint by the time a body exists, and survives as a `Pocket` that
carries the identity of the child it is for.

Roles
-----
``canonical`` visible 2D artwork and containment; ``stacking`` relative vertical
level; here, physical body, pockets, Z planes and remaining material. Nothing is
written back into canonical or stacking.

Scope
-----
This module defines what a correct body *is*. Building the full set from an
artwork, a stacking order and a profile is issue #9. `solidified_footprint` is
the one helper here, because the hosted-vs-void distinction is the substance of
this ticket and needs to be executable rather than described.

No offset operation is needed or used: separating a hosted hole from a void is
boolean difference. Clearance geometry -- dilating a child's footprint to make
the pocket it seats into -- belongs to the derivation in #9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..geometry import polygons as poly

if TYPE_CHECKING:  # pragma: no cover
    from ..canonical.artwork import CanonicalArtwork

#: A closed ring of points, immutable so a body cannot be reshaped after the fact.
FabRing = tuple[tuple[float, float], ...]

#: Area below which a leftover piece of a hole is numerical dust rather than a
#: void. Matches the canonical coincidence tolerance in spirit: an area, so it is
#: expressed as one rather than reusing a length (a Spike 01 lesson).
_AREA_TOLERANCE = 1e-9


class FabricationError(ValueError):
    """A fabrication body that could not be built, or does not hold together."""


def _check_ring(ring: object, what: str) -> FabRing:
    if not isinstance(ring, tuple):
        raise FabricationError(
            f"{what} must be a tuple of points, got {type(ring).__name__}: a "
            "mutable sequence would let the body change after construction"
        )
    if len(ring) < 3:
        raise FabricationError(f"{what} needs at least three points, got {len(ring)}")
    return ring  # type: ignore[return-value]


@dataclass(frozen=True)
class ZExtent:
    """Where a body sits vertically. Named planes, not tuple positions."""

    bottom_mm: float
    top_mm: float

    def __post_init__(self) -> None:
        if self.top_mm <= self.bottom_mm:
            raise FabricationError(
                f"a body's top ({self.top_mm} mm) must be above its bottom "
                f"({self.bottom_mm} mm)"
            )

    @property
    def thickness_mm(self) -> float:
        """How much material the body spans vertically."""
        return self.top_mm - self.bottom_mm

    def to_dict(self) -> dict:
        return {
            "bottom_mm": self.bottom_mm,
            "top_mm": self.top_mm,
            "thickness_mm": self.thickness_mm,
        }


@dataclass(frozen=True)
class Pocket:
    """A shallow registration recess, seating one named child region.

    A pocket is not an anonymous polygon in a list: it knows which canonical
    region it is for, so a body can be traced back to the artwork that produced
    it and forward to the piece that seats into it.

    `depth_mm` is measured down from the top of the body hosting it. The material
    left beneath is not stored here -- `FabricationBody.floor_beneath` derives it
    from the body's own thickness, so the two cannot disagree.
    """

    for_region: str
    footprint: FabRing
    depth_mm: float

    def __post_init__(self) -> None:
        if not self.for_region:
            raise FabricationError("a pocket must name the child region it seats")
        _check_ring(self.footprint, f"pocket footprint for {self.for_region!r}")
        if self.depth_mm <= 0:
            raise FabricationError(
                f"pocket depth for {self.for_region!r} must be positive, got "
                f"{self.depth_mm} mm"
            )

    def to_dict(self) -> dict:
        return {
            "for_region": self.for_region,
            "depth_mm": self.depth_mm,
            "footprint_area_mm2": abs(poly.area(list(self.footprint))),
        }


@dataclass(frozen=True)
class BodyFootprint:
    """The plan shape of a body: its outline, and the voids that stay open.

    `void_holes` are **only** genuine voids -- holes no child occupies. A hole
    that hosts a child has already been solidified away and is represented by a
    `Pocket` instead. Nothing here is anonymous about which is which.
    """

    outer: FabRing
    void_holes: tuple[FabRing, ...] = ()

    def __post_init__(self) -> None:
        _check_ring(self.outer, "body outer ring")
        if not isinstance(self.void_holes, tuple):
            raise FabricationError("void_holes must be a tuple")
        for index, hole in enumerate(self.void_holes):
            _check_ring(hole, f"void hole {index}")

    @property
    def area_mm2(self) -> float:
        """Plan area of material: outline less the voids that stay open."""
        return abs(poly.area(list(self.outer))) - sum(
            abs(poly.area(list(h))) for h in self.void_holes
        )

    def rings(self) -> list[list[tuple[float, float]]]:
        """Outline and voids, wound for boolean use."""
        rings = [poly.oriented(list(self.outer), ccw=True)]
        rings += [poly.oriented(list(h), ccw=False) for h in self.void_holes]
        return rings


@dataclass(frozen=True)
class FabricationBody:
    """The physical body realising one canonical region."""

    region_id: str
    footprint: BodyFootprint
    z: ZExtent
    pockets: tuple[Pocket, ...] = ()

    def __post_init__(self) -> None:
        if not self.region_id:
            raise FabricationError("a body must name the region it realises")
        if not isinstance(self.pockets, tuple):
            raise FabricationError("pockets must be a tuple")

        seen: set[str] = set()
        for pocket in self.pockets:
            if pocket.for_region in seen:
                raise FabricationError(
                    f"{self.region_id!r} carries more than one pocket for "
                    f"{pocket.for_region!r}: a child seats in one place"
                )
            seen.add(pocket.for_region)

            floor = self.z.thickness_mm - pocket.depth_mm
            if floor <= 0:
                raise FabricationError(
                    f"pocket for {pocket.for_region!r} is {pocket.depth_mm} mm "
                    f"deep in a {self.z.thickness_mm} mm body, leaving "
                    f"{floor} mm beneath it. A registration pocket is a recess, "
                    "not a through-hole -- support must remain continuous."
                )

    # -- traceability ---------------------------------------------------------

    def hosted_regions(self) -> tuple[str, ...]:
        """Every child region this body seats, in id order."""
        return tuple(sorted(p.for_region for p in self.pockets))

    def hosts(self, region_id: str) -> bool:
        return any(p.for_region == region_id for p in self.pockets)

    def pocket_for(self, region_id: str) -> Pocket:
        for pocket in self.pockets:
            if pocket.for_region == region_id:
                return pocket
        raise KeyError(f"{self.region_id!r} has no pocket for {region_id!r}")

    # -- material -------------------------------------------------------------

    def floor_beneath(self, region_id: str) -> float:
        """Material left under the pocket seating `region_id`, in mm.

        Derived from the body's own thickness rather than stored, so it cannot
        drift out of step with the body it describes.
        """
        return self.z.thickness_mm - self.pocket_for(region_id).depth_mm

    def to_dict(self) -> dict:
        return {
            "region_id": self.region_id,
            "z": self.z.to_dict(),
            "footprint_area_mm2": self.footprint.area_mm2,
            "void_hole_count": len(self.footprint.void_holes),
            "pockets": [
                {**p.to_dict(), "floor_mm": self.floor_beneath(p.for_region)}
                for p in self.pockets
            ],
        }


@dataclass(frozen=True)
class FabricationBodies:
    """Every body of one artwork, queryable by the region each realises."""

    bodies: tuple[FabricationBody, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.bodies, tuple):
            raise FabricationError("bodies must be a tuple")
        seen: set[str] = set()
        for body in self.bodies:
            if body.region_id in seen:
                raise FabricationError(
                    f"more than one body realises region {body.region_id!r}"
                )
            seen.add(body.region_id)

    def __len__(self) -> int:
        return len(self.bodies)

    def __iter__(self):
        return iter(self.bodies)

    def body_for(self, region_id: str) -> FabricationBody:
        """The body realising a canonical region."""
        for body in self.bodies:
            if body.region_id == region_id:
                return body
        raise KeyError(f"no body realises region {region_id!r}")

    def region_ids(self) -> tuple[str, ...]:
        return tuple(sorted(b.region_id for b in self.bodies))

    def to_dict(self) -> dict:
        return {"bodies": [b.to_dict() for b in self.bodies]}


def solidified_footprint(
    artwork: "CanonicalArtwork", region_id: str
) -> BodyFootprint:
    """The plan shape of the body realising `region_id`.

    Canonical holes occupied by a child region are **filled**: the body is solid
    beneath its children, and the child seats into a shallow pocket instead
    (ADR 0002 decision 2). Holes nothing occupies are **kept**: they are genuine
    voids, and something beneath them shows through.

    Uses boolean difference only. No offset, and therefore no clearance -- the
    canonical polygon layer has none by design, and dilating a child's footprint
    into a pocket is the derivation's job in #9.
    """
    region = artwork.regions[region_id]
    # A child occupies its whole OUTER boundary, not its visible surface. Using
    # the visible surface would let a grandchild's area leak back through as a
    # false void: the island sits inside the foreground's hole, and the backing's
    # hole is filled by the foreground's full extent regardless.
    children = [
        [artwork.outer_ring(child)] for child in artwork.children_of(region_id)
    ]

    void_holes: list[FabRing] = []
    for index, hole in enumerate(region.holes):
        hole_ring = poly.oriented(artwork.vertices.coords_of(hole), ccw=True)

        remaining = [hole_ring]
        for child in children:
            remaining = poly.boolean_op(remaining, child, "difference")
            if not remaining:
                break
        if abs(poly.total_area(remaining)) <= _AREA_TOLERANCE:
            continue  # fully occupied by children: solidified away

        nested = poly.boolean_tree([hole_ring], _flatten(children), "difference")
        for piece in nested:
            if piece.holes:
                raise FabricationError(
                    f"hole {index} of region {region_id!r} is only partly covered "
                    "by its children, leaving a void with a hole in it. A body "
                    "footprint holds a flat list of void rings and cannot express "
                    "an annular void, so this is refused rather than mis-shaped."
                )
            void_holes.append(tuple((float(x), float(y)) for x, y in piece.ring))

    return BodyFootprint(
        outer=tuple(
            (float(x), float(y))
            for x, y in artwork.vertices.coords_of(region.outer)
        ),
        void_holes=tuple(void_holes),
    )


def _flatten(ring_sets):
    return [ring for rings in ring_sets for ring in rings]
