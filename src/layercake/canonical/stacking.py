"""Stacking order, derived from canonical containment.

A canonical artwork says which regions enclose which. That already contains the
vertical arrangement: a region nested one level deeper sits one level higher. So
stacking order is **derived**, never authored -- there is no layer index to keep
in step with the geometry, and no second place for the truth to live.

Lives under `canonical` because it is a statement about canonical topology
alone. No fabrication input reaches it: no thickness, no seating depth, no
profile. Turning a level into a Z position is fabrication's job (#9).

Siblings are peers
------------------
The load-bearing semantic. Two islands inside the same parent occupy the **same
physical level**; neither sits above the other, and nothing here says otherwise.

They are ordered within their level by region id, purely so that output is
reproducible run to run. That ordering is **not a physical claim**. Deliberately
not derived from geometry, area, declaration order or dictionary iteration
order, all of which would either vary between runs or imply a height that does
not exist.

Nothing is written back into the canonical model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .artwork import CanonicalArtwork

_PEER_ORDER_NOTE = (
    "Regions within a level are peers at the same physical height. Their order "
    "is by region id, for reproducible output only, and does not mean one sits "
    "above another."
)


class StackingError(ValueError):
    """Containment from which no stacking order can be derived."""


@dataclass(frozen=True)
class StackingLevel:
    """One physical level of the stack.

    `index` is the only physical statement: 0 is the bottom, and each step up is
    one level higher. `peers` are the regions at that height -- co-located
    vertically, ordered by id for reproducibility rather than by any property of
    the artwork.
    """

    index: int
    peers: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"index": self.index, "peers": list(self.peers)}


@dataclass(frozen=True)
class StackingOrder:
    """The derived vertical arrangement of a canonical artwork.

    Levels are ordered bottom-up, so `levels[0]` is the bottom. Position in the
    tuple and `StackingLevel.index` agree, but the index is stated explicitly
    rather than left implicit in a list position.
    """

    levels: tuple[StackingLevel, ...]

    def __len__(self) -> int:
        return len(self.levels)

    def level_of(self, region_id: str) -> int:
        """The physical level this region sits at. 0 is the bottom."""
        for level in self.levels:
            if region_id in level.peers:
                return level.index
        raise KeyError(f"{region_id!r} is not in this stacking order")

    def peers_at(self, index: int) -> tuple[str, ...]:
        """Every region at a given level."""
        return self.levels[index].peers

    def peers_of(self, region_id: str) -> tuple[str, ...]:
        """Every region sharing this one's level, including itself."""
        return self.peers_at(self.level_of(region_id))

    def is_peer_of(self, first: str, second: str) -> bool:
        """Whether two regions sit at the same physical level."""
        return self.level_of(first) == self.level_of(second)

    def region_ids(self) -> tuple[str, ...]:
        """Every region in the order, bottom level first."""
        return tuple(rid for level in self.levels for rid in level.peers)

    def describe(self) -> str:
        """A plain rendering, one line per level."""
        return "\n".join(
            f"level {level.index}: {', '.join(level.peers)}" for level in self.levels
        )

    def to_dict(self) -> dict:
        return {
            "levels": [level.to_dict() for level in self.levels],
            "note": _PEER_ORDER_NOTE,
        }


def derive_stacking_order(artwork: "CanonicalArtwork") -> StackingOrder:
    """Derive the stacking order of a canonical artwork from its containment.

    Walks outward from the regions nothing encloses, one level per step. Region
    ids are sorted at every step, so the result depends on the artwork and not on
    the order it happened to be authored or stored in.

    Raises `StackingError` if any region cannot be placed. A region is only
    unreachable when it takes part in a containment cycle -- regions that
    mutually enclose each other, which requires identical footprints and which
    `CanonicalArtwork.validate()` already reports as overlapping. The cycle is a
    symptom of artwork that is not a visible partition, and is refused here
    rather than resolved into an arbitrary order.
    """
    placed: dict[str, int] = {}
    levels: list[StackingLevel] = []

    frontier = tuple(sorted(artwork.roots()))
    index = 0
    while frontier:
        levels.append(StackingLevel(index=index, peers=frontier))
        for region_id in frontier:
            placed[region_id] = index
        frontier = tuple(
            sorted(
                child
                for region_id in frontier
                for child in artwork.children_of(region_id)
            )
        )
        index += 1

    unplaced = sorted(set(artwork.regions) - set(placed))
    if unplaced:
        raise StackingError(
            f"cannot derive a stacking order: {', '.join(unplaced)} take part in "
            "a containment cycle, so no region among them is beneath the others. "
            "Regions that enclose each other have identical footprints, which "
            "CanonicalArtwork.validate() reports as overlapping -- the artwork is "
            "not a visible partition."
        )

    return StackingOrder(levels=tuple(levels))
