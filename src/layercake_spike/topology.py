"""The canonical partition: one artwork, shared boundaries as first-class data.

The central design decision of this spike. Rather than vectorising each colour
independently and hoping the results line up, every region's rings are interned
through a single `VertexTable`. Two regions that meet along a boundary end up
referencing *the same vertex indices*, so the adjacency is a fact recorded in
the model, not a numerical coincidence that has to be rediscovered later.

`EdgeTable` then keys undirected edges on the sorted index pair, so a shared
boundary is one record naming both incident regions. That is the "shared-edge
metadata is first-class" requirement from Issue #1, and it is what a future
migration to a richer topology model (DCEL or similar) would build on.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import NamedTuple

from . import clipper, spec

Ring = list[tuple[float, float]]
IndexRing = list[int]


class Edge(NamedTuple):
    """An undirected edge, canonicalised so (a,b) and (b,a) are one key."""

    a: int
    b: int

    @staticmethod
    def of(u: int, v: int) -> "Edge":
        return Edge(u, v) if u <= v else Edge(v, u)


def _oriented(ring: Ring, *, ccw: bool) -> Ring:
    """Return `ring` wound counter-clockwise (ccw=True) or clockwise."""
    is_ccw = clipper.area(ring) > 0
    return list(ring) if is_ccw == ccw else list(reversed(ring))


class VertexTable:
    """Interns 2D points, snapping anything within `eps` onto one vertex id."""

    def __init__(self, eps: float = spec.EPS) -> None:
        self._eps = eps
        self._index: dict[tuple[int, int], int] = {}
        self.coords: list[tuple[float, float]] = []

    def _key(self, x: float, y: float) -> tuple[int, int]:
        return (round(x / self._eps), round(y / self._eps))

    def add(self, x: float, y: float) -> int:
        key = self._key(x, y)
        vid = self._index.get(key)
        if vid is None:
            vid = len(self.coords)
            self._index[key] = vid
            self.coords.append((float(x), float(y)))
        return vid

    def intern_ring(self, ring: Ring) -> IndexRing:
        return [self.add(x, y) for x, y in ring]

    def ring_coords(self, ring: IndexRing) -> Ring:
        return [self.coords[i] for i in ring]

    def __len__(self) -> int:
        return len(self.coords)


@dataclass
class Region:
    """One colour region in one Z band, described by interned vertex indices."""

    rid: str
    colour: str
    z: tuple[float, float]
    outer: IndexRing
    holes: list[IndexRing] = field(default_factory=list)

    @property
    def z_min(self) -> float:
        return self.z[0]

    @property
    def z_max(self) -> float:
        return self.z[1]


class BandReport(NamedTuple):
    """Numeric proof that a Z band is a clean partition."""

    band: tuple[float, float]
    region_ids: list[str]
    overlap_area: float
    gap_area: float
    universe_area: float
    covered_area: float
    tolerance: float

    @property
    def ok(self) -> bool:
        return self.overlap_area < self.tolerance and self.gap_area < self.tolerance

    def to_dict(self) -> dict:
        return {
            "band": list(self.band),
            "regions": self.region_ids,
            "overlap_area": self.overlap_area,
            "gap_area": self.gap_area,
            "universe_area": self.universe_area,
            "covered_area": self.covered_area,
            "tolerance": self.tolerance,
            "ok": self.ok,
        }


class Partition:
    """A whole partitioned artwork: shared vertices, shared edges, regions."""

    def __init__(self, vertices: VertexTable, regions: dict[str, Region]) -> None:
        self.vertices = vertices
        self.regions = regions

    # -- construction -------------------------------------------------------

    @classmethod
    def build(cls, regions_geom: dict[str, dict], eps: float = spec.EPS) -> "Partition":
        """Intern every region's rings through one shared vertex table.

        Because interning is shared, a hole ring authored from the same
        coordinates as another region's outer ring resolves to identical vertex
        indices. The shared boundary is therefore established by construction
        rather than detected after the fact.
        """
        vt = VertexTable(eps=eps)
        regions: dict[str, Region] = {}
        for rid, geom in regions_geom.items():
            regions[rid] = Region(
                rid=rid,
                colour=geom["colour"],
                z=tuple(geom["z"]),
                outer=vt.intern_ring(geom["outer"]),
                holes=[vt.intern_ring(h) for h in geom.get("holes", [])],
            )
        return cls(vt, regions)

    # -- topology queries ---------------------------------------------------

    def rings_of(self, rid: str) -> list[IndexRing]:
        r = self.regions[rid]
        return [r.outer, *r.holes]

    def solid_rings(self, rid: str) -> list[Ring]:
        """A region's rings as coordinates, wound so booleans read them right.

        Rings are authored counter-clockwise for readability, but under
        Clipper2's NonZero fill rule a hole must be wound *opposite* to its
        outer ring or it adds area instead of subtracting it. Normalising here
        keeps that detail out of every caller.
        """
        r = self.regions[rid]
        rings = [_oriented(self.vertices.ring_coords(r.outer), ccw=True)]
        rings += [
            _oriented(self.vertices.ring_coords(h), ccw=False) for h in r.holes
        ]
        return rings

    def edge_table(self) -> dict[Edge, list[str]]:
        """Every undirected edge mapped to the regions incident to it."""
        table: dict[Edge, set[str]] = defaultdict(set)
        for rid in self.regions:
            for ring in self.rings_of(rid):
                for u, v in zip(ring, ring[1:] + ring[:1]):
                    table[Edge.of(u, v)].add(rid)
        return {e: sorted(rs) for e, rs in table.items()}

    def shared_edges(self) -> dict[Edge, list[str]]:
        """Edges belonging to more than one region -- the shared boundaries."""
        return {e: rs for e, rs in self.edge_table().items() if len(rs) > 1}

    def adjacency(self) -> dict[str, list[str]]:
        """Region -> regions it shares at least one edge with."""
        adj: dict[str, set[str]] = {rid: set() for rid in self.regions}
        for regions in self.shared_edges().values():
            for a in regions:
                for b in regions:
                    if a != b:
                        adj[a].add(b)
        return {rid: sorted(v) for rid, v in adj.items()}

    def containment(self) -> dict[str, list[str]]:
        """Region -> regions geometrically enclosed by it, within the same band.

        Uses Clipper2's nesting tree rather than point-in-polygon guessing, so
        the answer comes from the same robust integer arithmetic as the
        booleans.
        """
        out: dict[str, list[str]] = {rid: [] for rid in self.regions}
        for outer_id, outer in self.regions.items():
            outer_ring = self.vertices.ring_coords(outer.outer)
            for inner_id, inner in self.regions.items():
                if inner_id == outer_id or inner.z != outer.z:
                    continue
                inner_ring = self.vertices.ring_coords(inner.outer)
                # inner is contained if subtracting it from outer leaves a hole
                tree = clipper.boolean_tree([outer_ring], [inner_ring], "difference")
                if len(tree) == 1 and len(tree[0].holes) == 1:
                    out[outer_id].append(inner_id)
        return {k: sorted(v) for k, v in out.items()}

    # -- validation ---------------------------------------------------------

    def regions_in_band(self, z: tuple[float, float]) -> list[str]:
        return sorted(rid for rid, r in self.regions.items() if r.z == tuple(z))

    def validate_band(
        self,
        z: tuple[float, float],
        universe: Ring,
        tolerance: float = spec.EPS,
    ) -> BandReport:
        """Numerically check a band is a clean partition of `universe`.

        Overlap: total pairwise intersection area between regions' solid areas.
        Gap: area of `universe` not covered by any region.

        Deliberately numeric with an explicit tolerance -- Issue #1 requires
        this rather than visual inspection of the debug SVG.
        """
        rids = self.regions_in_band(z)

        solids = {rid: self.solid_rings(rid) for rid in rids}

        overlap = 0.0
        for i, a in enumerate(rids):
            for b in rids[i + 1 :]:
                inter = clipper.boolean_op(solids[a], solids[b], "intersection")
                overlap += abs(clipper.total_area(inter))

        covered: list[Ring] = []
        for rid in rids:
            covered = (
                clipper.boolean_op(covered, solids[rid], "union") if covered else solids[rid]
            )

        gap_rings = clipper.boolean_op([universe], covered, "difference") if covered else [universe]
        gap = abs(clipper.total_area(gap_rings))

        return BandReport(
            band=tuple(z),
            region_ids=rids,
            overlap_area=overlap,
            gap_area=gap,
            universe_area=abs(clipper.area(universe)),
            covered_area=abs(clipper.total_area(covered)) if covered else 0.0,
            tolerance=tolerance,
        )

    # -- debug output -------------------------------------------------------

    def to_dump(self) -> dict:
        """JSON-safe topology dump: vertices, edges, adjacency, containment."""
        edges = self.edge_table()
        shared = self.shared_edges()
        containment = self.containment()
        adjacency = self.adjacency()

        return {
            "counts": {
                "vertices": len(self.vertices),
                "regions": len(self.regions),
                "edges": len(edges),
                "shared_edges": len(shared),
            },
            "vertices": [
                {"id": i, "x": x, "y": y} for i, (x, y) in enumerate(self.vertices.coords)
            ],
            "regions": {
                rid: {
                    "colour": r.colour,
                    "z_min": r.z_min,
                    "z_max": r.z_max,
                    "outer": r.outer,
                    "holes": r.holes,
                    "hole_count": len(r.holes),
                    "adjacent_to": adjacency[rid],
                    "contains": containment[rid],
                }
                for rid, r in self.regions.items()
            },
            "shared_edges": [
                {
                    "a": e.a,
                    "b": e.b,
                    "a_xy": list(self.vertices.coords[e.a]),
                    "b_xy": list(self.vertices.coords[e.b]),
                    "regions": rs,
                }
                for e, rs in sorted(shared.items())
            ],
        }
