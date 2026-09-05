"""Canonical artwork: what the piece *is*, not how it will be made.

A canonical artwork is a set of coloured 2D regions and the containment between
them. It carries **no Z, no thickness, no clearance, no seating depth and no
backing** -- every one of those is a consequence of a fabrication profile rather
than a property of the artwork, and Session 01 showed how easily such a value
looks like a relationship once it is sitting in the model (ADR 0002, backing
inheriting `H`).

Two Spike 01 invariants carry over unchanged, because they are what make shared
boundaries checkable rather than coincidental:

- every region's rings are interned through **one** vertex table, so two regions
  meeting along a boundary reference the *same* vertex indices;
- an undirected edge is keyed on its sorted index pair, so a shared boundary is
  one record naming both incident regions rather than two copies that happen to
  coincide.

Containment without Z
---------------------
Spike 01 computed containment per Z band, skipping any pair in different bands.
With Z gone it is purely geometric, which makes it a full nesting tree: in the
Spike Glyph the backing now contains the foreground, which contains the island.
That relationship is the raw material a stacking order is derived from
(issue #7); this module exposes it and stops there.

Visible-surface semantics (ADR 0003)
------------------------------------
A region's area is **where that colour is seen**, not where its material is. The
regions form a non-overlapping visible partition: every point of the artwork
shows exactly one colour, so a parent is canonically *absent* wherever a visible
child covers it.

Two regions claiming the same area is an error at any nesting depth, not only
between siblings. Hidden support beneath a visible region -- the solid backing
under the foreground, the material under an island -- is a **fabrication**
concern introduced downstream (#8, #9), never expressed as overlapping canonical
artwork.

A hole with no region in it is **not** an error: it is a void, legal artwork
showing whatever is beneath, reported rather than rejected (#8).

Colour here is an **opaque identity**. Layercake does not model colour
contribution through translucency or underlying material; the visible result
comes from the explicit surface colours themselves (ADR 0003 decision 6).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Iterable, Mapping, NamedTuple, Sequence

from ..geometry import polygons as poly

Ring = list[tuple[float, float]]
IndexRing = tuple[int, ...]

#: Coincidence tolerance for treating two authored points as one vertex, and the
#: default numeric tolerance for gap/overlap validation. Matches Spike 01.
DEFAULT_TOLERANCE = 1e-6


class ArtworkError(ValueError):
    """Canonical artwork that is not well formed."""


class Edge(NamedTuple):
    """An undirected edge, canonicalised so (a,b) and (b,a) are one key."""

    a: int
    b: int

    @staticmethod
    def of(u: int, v: int) -> "Edge":
        return Edge(u, v) if u <= v else Edge(v, u)


@dataclass(frozen=True)
class RegionSpec:
    """One authored region: its boundary, its colour, and any holes."""

    region_id: str
    colour: str
    outer: Sequence[tuple[float, float]]
    holes: tuple[Sequence[tuple[float, float]], ...] = ()


@dataclass(frozen=True)
class Region:
    """One region of the canonical artwork, in interned vertex indices."""

    region_id: str
    colour: str
    outer: IndexRing
    holes: tuple[IndexRing, ...] = ()

    def rings(self) -> tuple[IndexRing, ...]:
        return (self.outer, *self.holes)


class Overlap(NamedTuple):
    """Two regions claiming the same area."""

    first: str
    second: str
    area: float

    def __str__(self) -> str:
        return f"{self.first} and {self.second} overlap by {self.area:.6g} mm2"


class ArtworkValidation(NamedTuple):
    """Numeric result of checking an artwork, with an explicit tolerance."""

    overlap_area: float
    void_area: float
    overlaps: tuple[Overlap, ...]
    tolerance: float

    @property
    def ok(self) -> bool:
        """Overlaps are errors. Voids are legal and merely reported."""
        return self.overlap_area <= self.tolerance

    def to_dict(self) -> dict:
        return {
            "overlap_area": self.overlap_area,
            "void_area": self.void_area,
            "overlaps": [
                {"regions": [o.first, o.second], "area": o.area} for o in self.overlaps
            ],
            "tolerance": self.tolerance,
            "ok": self.ok,
        }


class _VertexInterner:
    """Mutable builder: snaps points within `tolerance` onto one vertex id.

    Private and short-lived. It exists only while an artwork is being built and
    is never published -- the finished artwork holds an immutable `VertexTable`
    instead, so nothing downstream can add a vertex to a completed model.
    """

    def __init__(self, tolerance: float = DEFAULT_TOLERANCE) -> None:
        self._tolerance = tolerance
        self._index: dict[tuple[int, int], int] = {}
        self._coords: list[tuple[float, float]] = []

    def add(self, x: float, y: float) -> int:
        key = (round(x / self._tolerance), round(y / self._tolerance))
        vid = self._index.get(key)
        if vid is None:
            vid = len(self._coords)
            self._index[key] = vid
            self._coords.append((float(x), float(y)))
        return vid

    def intern(self, ring: Sequence[tuple[float, float]]) -> IndexRing:
        return tuple(self.add(x, y) for x, y in ring)

    def finish(self) -> "VertexTable":
        return VertexTable(coords=tuple(self._coords))


@dataclass(frozen=True)
class VertexTable:
    """The vertices of a finished artwork. Immutable by structure.

    Deliberately offers no way to add a vertex: interning happens in
    `_VertexInterner` during construction, and what the artwork publishes is
    this read-only value. `coords` is a tuple, and `coords_of` hands back a
    fresh list each call so a caller cannot reach the stored data through it.
    """

    coords: tuple[tuple[float, float], ...]

    def coords_of(self, ring: IndexRing) -> Ring:
        """The coordinates of a ring, as a new list the caller may modify."""
        return [self.coords[i] for i in ring]

    def __len__(self) -> int:
        return len(self.coords)


@dataclass(frozen=True)
class CanonicalArtwork:
    """A partitioned artwork: coloured regions and the containment between them.

    **Immutable by structure, not by convention.** A frozen dataclass alone would
    not be enough: it prevents rebinding the attributes but not reaching through
    them. So the regions and the containment are published as read-only mappings,
    `Region` is frozen with tuple rings, and the vertex data is a `VertexTable`
    with no way to add to it. Construction uses a mutable interner internally and
    never publishes it.

    Not hashable, because it holds mappings. Nothing needs to hash an artwork,
    and equality -- which is what the no-mutation tests rely on -- works fine.
    """

    vertices: VertexTable
    regions: Mapping[str, Region]
    tolerance: float = DEFAULT_TOLERANCE
    _parents: Mapping[str, str | None] = field(
        default_factory=lambda: MappingProxyType({}), repr=False
    )

    # -- construction ---------------------------------------------------------

    @classmethod
    def from_specs(
        cls,
        specs: Iterable[RegionSpec],
        tolerance: float = DEFAULT_TOLERANCE,
    ) -> "CanonicalArtwork":
        """Build an artwork, interning every ring through one vertex table.

        Because interning is shared, a hole authored from the same coordinates as
        another region's boundary resolves to identical vertex indices. The
        shared boundary is established by construction rather than detected
        afterwards. Input rings are never modified.
        """
        interner = _VertexInterner(tolerance)
        built: dict[str, Region] = {}

        for spec in specs:
            if spec.region_id in built:
                raise ArtworkError(f"duplicate region id {spec.region_id!r}")
            outer = _clean(spec.outer, spec.region_id, "outer")
            holes = tuple(
                _clean(h, spec.region_id, "hole") for h in spec.holes
            )
            built[spec.region_id] = Region(
                region_id=spec.region_id,
                colour=spec.colour,
                outer=interner.intern(outer),
                holes=tuple(interner.intern(h) for h in holes),
            )

        # Everything mutable stays local. The instance is built once, complete,
        # from read-only views -- no post-construction patching.
        vertices = interner.finish()
        return cls(
            vertices=vertices,
            regions=MappingProxyType(built),
            tolerance=tolerance,
            _parents=MappingProxyType(_compute_parents(vertices, built, tolerance)),
        )

    # -- geometry access ------------------------------------------------------

    def outer_ring(self, region_id: str) -> Ring:
        """A region's boundary, ignoring its holes."""
        return self.vertices.coords_of(self.regions[region_id].outer)

    def region_rings(self, region_id: str) -> list[Ring]:
        """A region's visible surface: outer boundary plus holes, wound for booleans.

        Canonical regions are visible coloured surface, not fabrication material
        (ADR 0003). What comes back is where this colour is *seen*: the boundary
        with any area covered by a child removed.
        """
        region = self.regions[region_id]
        rings = [poly.oriented(self.vertices.coords_of(region.outer), ccw=True)]
        rings += [
            poly.oriented(self.vertices.coords_of(h), ccw=False) for h in region.holes
        ]
        return rings

    def region_area(self, region_id: str) -> float:
        """The visible area of this colour, holes excluded."""
        return abs(poly.total_area(self.region_rings(region_id)))

    def colours(self) -> tuple[str, ...]:
        """Every colour used, in first-seen order. Any number is fine."""
        seen: dict[str, None] = {}
        for r in self.regions.values():
            seen.setdefault(r.colour, None)
        return tuple(seen)

    def regions_with_colour(self, colour: str) -> tuple[str, ...]:
        """A colour may be used by any number of regions."""
        return tuple(r.region_id for r in self.regions.values() if r.colour == colour)

    # -- topology -------------------------------------------------------------

    def edge_table(self) -> dict[Edge, tuple[str, ...]]:
        """Every undirected edge mapped to the regions incident to it."""
        table: dict[Edge, set[str]] = defaultdict(set)
        for region in self.regions.values():
            for ring in region.rings():
                for u, v in zip(ring, ring[1:] + ring[:1]):
                    table[Edge.of(u, v)].add(region.region_id)
        return {e: tuple(sorted(rs)) for e, rs in table.items()}

    def shared_edges(self) -> dict[Edge, tuple[str, ...]]:
        """Edges belonging to more than one region -- the shared boundaries."""
        return {e: rs for e, rs in self.edge_table().items() if len(rs) > 1}

    def adjacency(self) -> dict[str, tuple[str, ...]]:
        """Region -> regions it shares at least one edge with."""
        adj: dict[str, set[str]] = {rid: set() for rid in self.regions}
        for regions in self.shared_edges().values():
            for a in regions:
                for b in regions:
                    if a != b:
                        adj[a].add(b)
        return {rid: tuple(sorted(v)) for rid, v in adj.items()}

    # -- containment ----------------------------------------------------------

    def contains(self, outer_id: str, inner_id: str) -> bool:
        """Whether `outer_id` geometrically encloses `inner_id`, at any depth."""
        if outer_id == inner_id:
            return False
        return poly.encloses(
            self.outer_ring(outer_id), self.outer_ring(inner_id), self.tolerance
        )

    def parent_of(self, region_id: str) -> str | None:
        """The region directly enclosing this one, or None at the top level."""
        return self._parents[region_id]

    def children_of(self, region_id: str) -> tuple[str, ...]:
        """Regions directly enclosed by this one."""
        return tuple(
            sorted(r for r, p in self._parents.items() if p == region_id)
        )

    def roots(self) -> tuple[str, ...]:
        """Regions enclosed by nothing."""
        return tuple(sorted(r for r, p in self._parents.items() if p is None))

    def ancestors_of(self, region_id: str) -> tuple[str, ...]:
        """Enclosing regions, innermost first."""
        out: list[str] = []
        current = self._parents[region_id]
        while current is not None:
            out.append(current)
            current = self._parents[current]
        return tuple(out)

    def containment_depth(self, region_id: str) -> int:
        """How many regions enclose this one. Roots are 0.

        Exposed for issue #7 to derive a stacking order from. This module states
        the nesting; turning it into an order is that ticket's job.
        """
        return len(self.ancestors_of(region_id))

    # -- validation -----------------------------------------------------------

    def validate(self, tolerance: float | None = None) -> ArtworkValidation:
        """Check numerically that no two regions claim the same area.

        Overlap is an error: a point of the artwork cannot be two colours.
        Void -- a hole with no region in it -- is legal and reported, per #8.
        """
        tol = self.tolerance if tolerance is None else tolerance

        surfaces = {rid: self.region_rings(rid) for rid in self.regions}
        ids = sorted(self.regions)

        overlaps: list[Overlap] = []
        total_overlap = 0.0
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                shared = poly.boolean_op(surfaces[a], surfaces[b], "intersection")
                overlap = abs(poly.total_area(shared))
                if overlap > tol:
                    overlaps.append(Overlap(a, b, overlap))
                total_overlap += overlap

        void = 0.0
        for rid, region in self.regions.items():
            for hole in region.holes:
                hole_ring = poly.oriented(self.vertices.coords_of(hole), ccw=True)
                occupants = [
                    surfaces[child]
                    for child in self.regions
                    if child != rid
                ]
                remaining: list[Ring] = [hole_ring]
                for occupant in occupants:
                    remaining = poly.boolean_op(remaining, occupant, "difference")
                    if not remaining:
                        break
                void += abs(poly.total_area(remaining))

        return ArtworkValidation(
            overlap_area=total_overlap,
            void_area=void,
            overlaps=tuple(overlaps),
            tolerance=tol,
        )

    # -- debug output ---------------------------------------------------------

    def to_dump(self) -> dict:
        """JSON-safe topology dump: vertices, edges, adjacency, containment."""
        edges = self.edge_table()
        shared = self.shared_edges()
        adjacency = self.adjacency()
        return {
            "counts": {
                "vertices": len(self.vertices),
                "regions": len(self.regions),
                "colours": len(self.colours()),
                "edges": len(edges),
                "shared_edges": len(shared),
            },
            "vertices": [
                {"id": i, "x": x, "y": y}
                for i, (x, y) in enumerate(self.vertices.coords)
            ],
            "regions": {
                rid: {
                    "colour": r.colour,
                    "outer": list(r.outer),
                    "holes": [list(h) for h in r.holes],
                    "hole_count": len(r.holes),
                    "adjacent_to": list(adjacency[rid]),
                    "parent": self.parent_of(rid),
                    "children": list(self.children_of(rid)),
                    "containment_depth": self.containment_depth(rid),
                }
                for rid, r in self.regions.items()
            },
            "shared_edges": [
                {
                    "a": e.a,
                    "b": e.b,
                    "a_xy": list(self.vertices.coords[e.a]),
                    "b_xy": list(self.vertices.coords[e.b]),
                    "regions": list(rs),
                }
                for e, rs in sorted(shared.items())
            ],
        }


def _compute_parents(
    vertices: VertexTable,
    regions: Mapping[str, Region],
    tolerance: float,
) -> dict[str, str | None]:
    """Direct parent of each region: the smallest region enclosing it.

    Module level rather than a method, so a finished artwork can be constructed
    complete in one call instead of being patched after the fact.
    """
    outers = {rid: vertices.coords_of(r.outer) for rid, r in regions.items()}
    areas = {rid: abs(poly.area(ring)) for rid, ring in outers.items()}

    parents: dict[str, str | None] = {}
    for inner in regions:
        enclosing = [
            outer
            for outer in regions
            if outer != inner and poly.encloses(outers[outer], outers[inner], tolerance)
        ]
        parents[inner] = (
            min(enclosing, key=lambda r: (areas[r], r)) if enclosing else None
        )
    return parents


def _clean(
    ring: Sequence[tuple[float, float]], region_id: str, what: str
) -> Ring:
    """Copy a ring, drop a repeated closing vertex, and reject degenerates."""
    pts = [(float(x), float(y)) for x, y in ring]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        raise ArtworkError(
            f"{region_id} {what} ring needs at least 3 distinct points, got {len(pts)}"
        )
    if abs(poly.area(pts)) <= 0.0:
        raise ArtworkError(f"{region_id} {what} ring has zero area")
    return pts
