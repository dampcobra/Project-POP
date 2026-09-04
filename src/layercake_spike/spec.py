"""The Spike Glyph: exact vector geometry for Issue #1, in millimetres.

Single source of truth for the spike's test artwork. Authored directly as
vector coordinates -- deliberately never derived from a raster image.

Layout (viewed from +Z, origin at the badge's bottom-left corner):

    Colour A   50 x 50 mm structural backing,        Z 0.0 -> 0.8
    Colour B   irregular foreground with a V notch,  Z 0.8 -> 2.0
    Colour C   square island inside B,               Z 0.8 -> 2.0

B and C occupy the *same* Z band. C is a hole in B, not a layer stacked on
top of it, so the two bodies meet at a shared vertical boundary surface.
"""

from __future__ import annotations

Ring = list[tuple[float, float]]

# --- tolerances and thresholds ---------------------------------------------

#: Coincidence tolerance for treating two authored points as one vertex.
EPS: float = 1e-6

#: Clipper2 works on 64-bit integers; this is the mm -> integer scale factor,
#: giving 1e-6 mm precision, matching EPS.
CLIPPER_SCALE: float = 1e6

#: Minimum manufacturable feature width. 0.4 mm nozzle assumption for this
#: spike, per Issue #1. Not yet validated against physical prints.
MIN_FEATURE_MM: float = 0.4

# --- Z bands ---------------------------------------------------------------

#: Structural backing band.
Z_BACKING: tuple[float, float] = (0.0, 0.8)

#: Artwork band. Every visible colour region lives here; MVP geometry is flat
#: mosaic/inlay, so there is exactly one artwork band and no variable relief.
Z_ARTWORK: tuple[float, float] = (0.8, 2.0)

# --- rings (all counter-clockwise, no repeated closing vertex) --------------

#: Colour A -- continuous structural backing under the whole badge.
BACKING_RING: Ring = [
    (0.0, 0.0),
    (50.0, 0.0),
    (50.0, 50.0),
    (0.0, 50.0),
]

#: Colour B -- irregular foreground region with a V-shaped notch.
#:
#: Note on reflex count. Issue #1 asks for "a V-shaped concave notch with two
#: reflex vertices". A geometrically pure V cut into a straight edge yields
#: exactly *one* reflex vertex -- the apex; both shoulders are necessarily
#: convex, and making a shoulder reflex would require the material to overhang
#: the notch. The apex is therefore truncated with a 2 mm flat, which reads as
#: a V, keeps the geometry printable, and gives the two reflex vertices the
#: issue calls for: (26,26) and (24,26).
#:
#: The run from (44,14) to (44,17) is deliberately vertical so the undersized
#: tab has an exact axis-aligned anchor.
B_OUTER_RING: Ring = [
    (8.0, 8.0),
    (41.0, 6.0),
    (44.0, 14.0),
    (44.0, 17.0),
    (42.0, 30.0),
    (38.0, 40.0),
    (30.0, 40.0),  # notch shoulder (convex)
    (26.0, 26.0),  # reflex -- notch apex, right corner of the flat
    (24.0, 26.0),  # reflex -- notch apex, left corner of the flat
    (20.0, 40.0),  # notch shoulder (convex)
    (12.0, 38.0),
]

#: The two reflex vertices of B, in ring order. Referenced by tests and by the
#: extrusion checks that prove concave geometry survives processing.
B_REFLEX_VERTICES: Ring = [(26.0, 26.0), (24.0, 26.0)]

#: Colour C -- enclosed island. 8 x 8 mm square, roughly 4 mm of B all round.
C_RING: Ring = [
    (14.0, 12.0),
    (22.0, 12.0),
    (22.0, 20.0),
    (14.0, 20.0),
]

#: Deliberately unmanufacturable tab: 0.150 mm wide, protruding 3.000 mm past
#: B's x=44.0 edge, overlapping 0.5 mm into B so the union is robust.
#: Unioned into B *before* cleanup runs, so cleanup has something to catch.
TAB_RING: Ring = [
    (43.5, 15.425),
    (47.0, 15.425),
    (47.0, 15.575),
    (43.5, 15.575),
]

#: Region definitions in the form Partition.build() consumes. The pipeline is
#: colour-count agnostic: adding a fourth colour means adding an entry here,
#: not changing code.
REGIONS: dict[str, dict] = {
    "A": dict(colour="A", z=Z_BACKING, outer=BACKING_RING, holes=[]),
    "B": dict(colour="B", z=Z_ARTWORK, outer=B_OUTER_RING, holes=[C_RING]),
    "C": dict(colour="C", z=Z_ARTWORK, outer=C_RING, holes=[]),
}

#: Human-readable body names used for STL filenames.
BODY_FILENAMES: dict[str, str] = {
    "A": "A_backing.stl",
    "B": "B_foreground.stl",
    "C": "C_island.stl",
}
