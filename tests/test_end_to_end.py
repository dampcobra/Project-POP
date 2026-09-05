"""End-to-end canonical to fabrication tests (issue #10).

This is a proof ticket, not another layer. Everything #5-#9 built has only ever
been driven by one 50 x 50 mm badge with one island: three levels, one shape
family, no sibling, no fourth colour, no genuine void. Those are ordinary
artwork, not edge cases, and until something drives them the model is only
asserted to work.

Two fixtures, chosen to combine behaviours rather than isolate them:

    the plaque   A(white)                    level 0, plus a genuine void
                 +- B(red)                   level 1
                    +- C1(blue)              level 2   } siblings
                    |  +- D(white)           level 3   }
                    +- C2(yellow)            level 2   }

    the chain    E0 -> E1 -> E2 -> E3 -> E4  five levels, no branching

The plaque carries nesting past three levels, siblings, a hole hosting nothing,
and four colours across five regions -- one colour reused, so that colour count
and region count are visibly not the same question. The chain exists only to
make registration freedom at depth read unambiguously.

The ticket's own standard is architectural: if these tests need awkward
bypasses, special cases or knowledge of internals, the interface is wrong. See
the dev diary for what that turned up.
"""

import copy
import json

import pytest

from layercake.canonical import CanonicalArtwork, RegionSpec
from layercake.fabrication import (
    FabricationError,
    FabricationProfile,
    ProfileError,
    derive,
)
from layercake.geometry import polygons as poly


def sq(x, y, w, h=None):
    h = w if h is None else h
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


# --- the plaque --------------------------------------------------------------

PLAQUE = sq(0.0, 0.0, 60.0)
VOID = sq(48.0, 48.0, 8.0)  # a hole in the plaque that hosts nothing at all
FOREGROUND = sq(6.0, 6.0, 36.0)
LEFT = sq(10.0, 10.0, 14.0)
RIGHT = sq(28.0, 10.0, 10.0)
INSET = sq(13.0, 13.0, 8.0)


def plaque() -> CanonicalArtwork:
    """Four levels, two siblings, one genuine void, four colours.

    `D` is white again, the same colour as the root. Nothing about the
    derivation should notice: colour is a property of a region, not an identity.
    """
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("A", "white", PLAQUE, (FOREGROUND, VOID)),
            RegionSpec("B", "red", FOREGROUND, (LEFT, RIGHT)),
            RegionSpec("C1", "blue", LEFT, (INSET,)),
            RegionSpec("C2", "yellow", RIGHT),
            RegionSpec("D", "white", INSET),
        ]
    )


def plaque_declared_differently() -> CanonicalArtwork:
    """The same artwork, specs given in a different order. Continues #7."""
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("D", "white", INSET),
            RegionSpec("C2", "yellow", RIGHT),
            RegionSpec("B", "red", FOREGROUND, (RIGHT, LEFT)),
            RegionSpec("A", "white", PLAQUE, (VOID, FOREGROUND)),
            RegionSpec("C1", "blue", LEFT, (INSET,)),
        ]
    )


# --- the chain ---------------------------------------------------------------

CHAIN_RINGS = [sq(4.0 * n, 4.0 * n, 40.0 - 8.0 * n) for n in range(5)]
CHAIN_COLOURS = ["white", "red", "blue", "white", "red"]


def chain() -> CanonicalArtwork:
    """Five levels, strictly linear. Built for the freedom accumulation test."""
    specs = []
    for n, (ring, colour) in enumerate(zip(CHAIN_RINGS, CHAIN_COLOURS)):
        holes = (CHAIN_RINGS[n + 1],) if n + 1 < len(CHAIN_RINGS) else ()
        specs.append(RegionSpec(f"E{n}", colour, ring, holes))
    return CanonicalArtwork.from_specs(specs)


def ring_area(ring) -> float:
    return abs(poly.area(list(ring)))


# --- nesting deeper than three levels ----------------------------------------


def test_the_plaque_derives_four_levels():
    result = derive(plaque(), FabricationProfile.default())
    assert result.region_ids() == ("A", "B", "C1", "C2", "D")
    assert [result.level_of(r) for r in ("A", "B", "C1", "C2", "D")] == [0, 1, 2, 2, 3]


def test_the_chain_derives_five_levels():
    result = derive(chain(), FabricationProfile.default())
    assert [result.level_of(f"E{n}") for n in range(5)] == [0, 1, 2, 3, 4]


def test_every_level_of_the_plaque_is_physically_correct():
    """Not that the IDs exist -- that each body is placed and cut correctly.

    Walks the whole stack: Z extent, one visible step per level, the pockets
    each parent actually cuts, and the floor left under each of them.
    """
    profile = FabricationProfile.default()
    result = derive(plaque(), profile)

    h = profile.visible_step_height.mm
    backing = profile.backing_thickness.mm
    depth = profile.seating_depth.mm
    minimum = profile.minimum_recess_floor.mm

    expected_pockets = {
        "A": ("B",),
        "B": ("C1", "C2"),
        "C1": ("D",),
        "C2": (),
        "D": (),
    }

    for region_id, hosted in expected_pockets.items():
        body = result.body_for(region_id)
        level = result.level_of(region_id)

        # placed at exactly one visible step per completed level
        assert body.z.top_mm == pytest.approx(backing + level * h)
        assert body.z.bottom_mm == pytest.approx(
            0.0 if level == 0 else body.z.top_mm - h - depth
        )

        # cuts a pocket for each child it hosts, and for nothing else
        assert body.hosted_regions() == hosted

        for child in hosted:
            pocket = body.pocket_for(child)
            assert pocket.depth_mm == pytest.approx(depth)
            floor = body.floor_beneath(child)
            assert floor == pytest.approx(body.z.thickness_mm - depth)
            assert floor >= minimum - 1e-9


def test_the_visible_step_stays_h_all_the_way_up_the_chain():
    profile = FabricationProfile.default()
    result = derive(chain(), profile)

    tops = [result.body_for(f"E{n}").z.top_mm for n in range(5)]
    steps = [b - a for a, b in zip(tops, tops[1:])]
    assert steps == pytest.approx([profile.visible_step_height.mm] * 4)


def test_the_visible_step_is_h_whatever_the_backing_and_seating_depth():
    profile = (
        FabricationProfile.default()
        .with_backing_thickness(2.0)
        .with_seating_depth(0.4)
    )
    result = derive(chain(), profile)

    tops = [result.body_for(f"E{n}").z.top_mm for n in range(5)]
    assert [b - a for a, b in zip(tops, tops[1:])] == pytest.approx(
        [profile.visible_step_height.mm] * 4
    )
    assert result.body_for("E0").z.top_mm == pytest.approx(2.0)


# --- siblings ----------------------------------------------------------------


def test_siblings_share_a_level_and_a_z_extent():
    result = derive(plaque(), FabricationProfile.default())
    assert result.level_of("C1") == result.level_of("C2") == 2
    assert result.body_for("C1").z == result.body_for("C2").z


def test_siblings_get_their_own_pockets_in_the_shared_parent():
    result = derive(plaque(), FabricationProfile.default())
    parent = result.body_for("B")

    assert parent.hosted_regions() == ("C1", "C2")
    left, right = parent.pocket_for("C1"), parent.pocket_for("C2")
    assert left.footprint != right.footprint

    overlap = poly.boolean_op(
        [list(left.footprint)], [list(right.footprint)], "intersection"
    )
    assert abs(poly.total_area(overlap)) < 1e-9


def test_a_childless_sibling_cuts_no_pocket():
    """C2 has no children, so its body is plain. C1, its peer, hosts one."""
    result = derive(plaque(), FabricationProfile.default())
    assert result.body_for("C2").pockets == ()
    assert result.body_for("C1").hosted_regions() == ("D",)


# --- a genuine void, all the way through -------------------------------------


def test_a_hole_hosting_nothing_survives_derivation_as_a_void():
    """canonical hole with no child -> derive() -> FabricationBody.void_holes"""
    artwork = plaque()
    assert artwork.validate().void_area == pytest.approx(ring_area(VOID))

    result = derive(artwork, FabricationProfile.default())
    voids = result.voids_of("A")

    assert len(voids) == 1
    assert ring_area(voids[0]) == pytest.approx(ring_area(VOID))


def test_the_void_is_not_confused_with_the_hole_that_hosts_a_child():
    """A has two canonical holes. Exactly one of them becomes a void."""
    result = derive(plaque(), FabricationProfile.default())
    body = result.body_for("A")

    assert body.hosted_regions() == ("B",)  # the foreground hole, solidified
    assert len(body.footprint.void_holes) == 1  # the empty hole, kept

    # the void is where the void was, not where the child is
    void = body.footprint.void_holes[0]
    assert abs(poly.total_area(
        poly.boolean_op([list(void)], [list(FOREGROUND)], "intersection")
    )) < 1e-9
    assert abs(poly.total_area(
        poly.boolean_op([list(void)], [list(body.pocket_for("B").footprint)],
                        "intersection")
    )) < 1e-9


def test_the_void_is_open_through_the_whole_body():
    """A void is a hole in the plan shape, so it passes through the extrusion.

    A pocket is not: it stops at its floor. The distinction is what makes one a
    through-void and the other a blind recess.
    """
    result = derive(plaque(), FabricationProfile.default())
    body = result.body_for("A")

    assert body.pocket_for("B").depth_mm < body.z.thickness_mm
    assert body.floor_beneath("B") > 0
    # nothing in the model gives a void a depth: it is simply absent material
    assert not hasattr(body.footprint.void_holes[0], "depth_mm")


def test_child_hosting_holes_are_solidified_at_every_level():
    """Under the supported-child strategy, no body keeps a hole it hosts into."""
    result = derive(plaque(), FabricationProfile.default())
    for region_id in ("B", "C1"):
        body = result.body_for(region_id)
        assert body.hosted_regions()
        assert body.footprint.void_holes == ()


# --- four colours ------------------------------------------------------------


def test_four_colours_across_five_regions():
    artwork = plaque()
    assert artwork.colours() == ("white", "red", "blue", "yellow")
    assert len(artwork.regions) == 5
    assert artwork.regions_with_colour("white") == ("A", "D")


def test_the_derivation_does_not_care_how_many_colours_there_are():
    """Colour-count agnosticism, shown rather than asserted about.

    Recolouring every region -- to one colour, to five distinct colours -- must
    not move a single body. If the derivation consulted colour anywhere, this
    would fail.
    """
    baseline = derive(plaque(), FabricationProfile.default()).to_dict()

    def recoloured(colours: dict[str, str]) -> dict:
        artwork = CanonicalArtwork.from_specs(
            [
                RegionSpec("A", colours["A"], PLAQUE, (FOREGROUND, VOID)),
                RegionSpec("B", colours["B"], FOREGROUND, (LEFT, RIGHT)),
                RegionSpec("C1", colours["C1"], LEFT, (INSET,)),
                RegionSpec("C2", colours["C2"], RIGHT),
                RegionSpec("D", colours["D"], INSET),
            ]
        )
        return derive(artwork, FabricationProfile.default()).to_dict()

    monochrome = recoloured({r: "grey" for r in ("A", "B", "C1", "C2", "D")})
    five_way = recoloured(
        dict(zip(("A", "B", "C1", "C2", "D"), ("c1", "c2", "c3", "c4", "c5")))
    )

    assert monochrome == baseline
    assert five_way == baseline


def test_no_colour_count_limit_exists_in_the_pipeline():
    """Eight regions, eight colours. Nothing caps this at four."""
    rings = [sq(3.0 * n, 3.0 * n, 60.0 - 6.0 * n) for n in range(8)]
    specs = []
    for n, ring in enumerate(rings):
        holes = (rings[n + 1],) if n + 1 < len(rings) else ()
        specs.append(RegionSpec(f"L{n}", f"colour_{n}", ring, holes))

    artwork = CanonicalArtwork.from_specs(specs)
    assert len(artwork.colours()) == 8

    result = derive(artwork, FabricationProfile.default())
    assert [result.level_of(f"L{n}") for n in range(8)] == list(range(8))


# --- cumulative registration freedom at arbitrary depth ----------------------


def test_freedom_accumulates_one_clearance_per_seating_along_the_chain():
    """The Spike 02 meaning, generalised past its two seatings.

        worst-case freedom  =  sum of the per-side seating clearances
                               along that ancestry path
    """
    profile = FabricationProfile.default()
    result = derive(chain(), profile)
    c = profile.per_side_clearance.mm

    for depth in range(5):
        assert result.registration_freedom("E0", f"E{depth}") == pytest.approx(
            depth * c
        )

    # and between any two points on the path, not only from the root
    assert result.registration_freedom("E1", "E4") == pytest.approx(3 * c)
    assert result.registration_freedom("E3", "E4") == pytest.approx(c)


def test_freedom_follows_the_actual_ancestry_path_in_branching_artwork():
    profile = FabricationProfile.default()
    result = derive(plaque(), profile)
    c = profile.per_side_clearance.mm

    assert result.seating_path("A", "D") == ("A", "B", "C1", "D")
    assert result.registration_freedom("A", "D") == pytest.approx(3 * c)
    assert result.registration_freedom("A", "C2") == pytest.approx(2 * c)
    assert result.registration_freedom("B", "D") == pytest.approx(2 * c)


def test_siblings_contribute_no_freedom_to_one_another():
    """Ancestry-path accumulation, not stacking-level accumulation.

    C1 and C2 sit at the same level and seat into the same parent. Neither seats
    into the other, so the question has no answer and is refused rather than
    silently returning a number.
    """
    result = derive(plaque(), FabricationProfile.default())

    for a, b in (("C1", "C2"), ("C2", "C1")):
        with pytest.raises(FabricationError) as excinfo:
            result.registration_freedom(a, b)
        message = str(excinfo.value).lower()
        assert "sibling" in message
        assert "path" in message


def test_a_region_has_no_freedom_relative_to_itself():
    result = derive(plaque(), FabricationProfile.default())
    assert result.registration_freedom("D", "D") == pytest.approx(0.0)


def test_freedom_scales_with_the_profile_clearance():
    tight = derive(chain(), FabricationProfile.default().with_per_side_clearance(0.05))
    loose = derive(chain(), FabricationProfile.default().with_per_side_clearance(0.20))

    assert tight.registration_freedom("E0", "E4") == pytest.approx(0.20)
    assert loose.registration_freedom("E0", "E4") == pytest.approx(0.80)


def test_asking_about_an_unknown_region_is_refused():
    result = derive(plaque(), FabricationProfile.default())
    with pytest.raises(FabricationError) as excinfo:
        result.registration_freedom("A", "nope")
    assert "nope" in str(excinfo.value)


def test_the_reported_freedom_matches_the_clearance_actually_cut():
    """Ties the number to the geometry rather than to the profile alone.

    Each pocket is the child's outer footprint grown by the per-side clearance,
    so the pocket is larger by that much on every side. Checked here because
    `registration_freedom` reads the clearance from the profile, and this is
    what makes that reading trustworthy.
    """
    profile = FabricationProfile.default()
    result = derive(plaque(), profile)
    c = profile.per_side_clearance.mm

    # the child, grown by the clearance, is exactly the pocket
    from layercake.fabrication import dilate

    for parent, child, ring in (("A", "B", FOREGROUND), ("C1", "D", INSET)):
        pocket = result.body_for(parent).pocket_for(child)
        assert ring_area(pocket.footprint) == pytest.approx(
            ring_area(dilate(ring, c)), rel=1e-9
        )


# --- profile failures, with actionable errors --------------------------------


def test_a_backing_too_thin_for_its_recess_says_so():
    """Names the quantity, its value, what it must host, and what it needs."""
    profile = (
        FabricationProfile.default()
        .with_backing_thickness(1.0)
        .with_seating_depth(0.8)
        .with_minimum_recess_floor(0.4)
    )
    with pytest.raises(ProfileError) as excinfo:
        derive(plaque(), profile)

    message = str(excinfo.value).lower()
    assert "backing" in message
    assert "1.0" in message  # the offending value
    assert "0.8" in message  # what it has to host
    assert "1.2" in message  # what it would need
    assert "floor" in message


def test_a_dimension_that_is_not_a_layer_multiple_says_which_and_why():
    """0.75 mm at a 0.2 mm layer height is 3.75 layers -- unbuildable as asked."""
    profile = FabricationProfile.default().with_seating_depth(0.75)

    with pytest.raises(ProfileError) as excinfo:
        derive(plaque(), profile)

    message = str(excinfo.value).lower()
    assert "seating depth" in message  # which quantity
    assert "0.75" in message  # its value
    assert "0.2" in message  # the layer height it must divide by
    assert "layer" in message  # why it is invalid
    assert "3.75" in message  # the non-whole result


def test_a_body_too_thin_to_host_its_recess_is_refused_during_derivation():
    """The profile is manufacturable; this stack is not. Names the region.

    A 0.2 mm visible step leaves only 0.2 mm under every recess above the
    backing, which is under the minimum floor. Nothing about the profile alone
    reveals it -- only stacking artwork does.
    """
    profile = (
        FabricationProfile.default()
        .with_visible_step_height(0.2)
        .with_backing_thickness(1.2)
        .with_seating_depth(0.8)
        .with_minimum_recess_floor(0.4)
    )
    profile.validate()

    with pytest.raises(FabricationError) as excinfo:
        derive(plaque(), profile)

    message = str(excinfo.value)
    assert "'B'" in message  # which region
    assert "0.2" in message  # what it would leave
    assert "0.4" in message  # the minimum it fails
    assert "minimum" in message.lower()


def test_a_failing_profile_produces_no_partial_result():
    profile = FabricationProfile.default().with_seating_depth(0.75)
    with pytest.raises(ProfileError):
        derive(plaque(), profile)


# --- canonical artwork is unchanged, in every case ---------------------------


@pytest.mark.parametrize("fixture", [plaque, chain])
def test_canonical_artwork_is_unchanged_by_derivation(fixture):
    artwork = fixture()
    before = copy.deepcopy(artwork.to_dump())

    derive(artwork, FabricationProfile.default())

    assert artwork.to_dump() == before


@pytest.mark.parametrize(
    "profile_change",
    [
        lambda p: p.with_seating_depth(0.75),  # not a layer multiple
        lambda p: p.with_backing_thickness(1.0).with_seating_depth(0.8),  # too thin
        lambda p: p.with_visible_step_height(0.2).with_seating_depth(0.8),  # thin floor
    ],
)
def test_canonical_artwork_is_unchanged_when_derivation_fails(profile_change):
    artwork = plaque()
    before = copy.deepcopy(artwork.to_dump())

    with pytest.raises((ProfileError, FabricationError)):
        derive(artwork, profile_change(FabricationProfile.default()))

    assert artwork.to_dump() == before


def test_repeated_derivation_does_not_disturb_the_artwork():
    artwork = plaque()
    before = copy.deepcopy(artwork.to_dump())
    for _ in range(5):
        derive(artwork, FabricationProfile.default())
    assert artwork.to_dump() == before


# --- determinism -------------------------------------------------------------


def dumped(result) -> str:
    return json.dumps(result.to_dict(), sort_keys=True)


@pytest.mark.parametrize("fixture", [plaque, chain])
def test_repeated_derivation_produces_an_identical_result(fixture):
    """The whole inspectable result, not just the body count."""
    profile = FabricationProfile.default()
    first = dumped(derive(fixture(), profile))
    for _ in range(4):
        assert dumped(derive(fixture(), profile)) == first


def test_declaration_order_does_not_change_the_derived_result():
    """Continues #7's determinism principle through to fabrication.

    The same artwork, with the specs and the hole lists given in a different
    order, must derive to the same bodies -- same levels, same Z, same pockets,
    same findings, in the same order.
    """
    profile = FabricationProfile.default()
    assert dumped(derive(plaque(), profile)) == dumped(
        derive(plaque_declared_differently(), profile)
    )


def canonical_geometry(artwork) -> dict:
    """Everything about an artwork that is not an internal identifier."""
    return {
        region_id: (
            artwork.regions[region_id].colour,
            tuple(tuple(p) for p in artwork.outer_ring(region_id)),
            frozenset(tuple(tuple(p) for p in ring)
                      for ring in artwork.region_rings(region_id)),
            artwork.children_of(region_id),
            artwork.parent_of(region_id),
        )
        for region_id in sorted(artwork.regions)
    }


def test_declaration_order_does_not_change_the_canonical_artwork_either():
    """The geometry and topology match. Two internal orderings deliberately need not.

    Canonical artwork keeps declaration order in two places, and both are
    internal identity rather than content:

    - **vertex numbering** -- points are interned as first seen, so the same
      point gets a different id if the specs are given in another order;
    - **hole order** within `region_rings`, which follows the order the holes
      were declared in;
    - **colour order** from `colours()`, which is documented as first-seen and
      so is order-dependent by design.

    None of them reaches the derived result: `test_declaration_order_does_not_change
    _the_derived_result` compares the complete `FabricationResult` and it is
    identical. The coordinates, the set of rings, adjacency, containment,
    and every count match too, and so does the set of colours.

    Stated explicitly because a reader diffing two dumps would otherwise
    reasonably expect them to be byte-identical, and because the honest place to
    record the limit of the #7 determinism guarantee is a test rather than
    a comment.
    """
    a, b = plaque(), plaque_declared_differently()

    assert canonical_geometry(a) == canonical_geometry(b)
    assert a.adjacency() == b.adjacency()
    assert set(a.colours()) == set(b.colours())
    assert a.to_dump()["counts"] == b.to_dump()["counts"]

    assert a.to_dump() != b.to_dump()  # the interning, and only the interning


def test_findings_are_reported_in_a_stable_order():
    profile = FabricationProfile.default()
    runs = [
        [(f.kind, f.region_id, round(f.area_mm2, 9)) for f in derive(plaque(), profile).findings]
        for _ in range(3)
    ]
    assert runs[0] == runs[1] == runs[2]


# --- the milestone boundary holds -------------------------------------------


def test_the_derived_bodies_still_satisfy_the_extrusion_preconditions():
    """#9's agreed boundary, on artwork the spikes never saw.

    Mesh manifoldness itself remains deferred to #19; these are the
    preconditions standing in for it, checked here on four- and five-level
    artwork with siblings and a genuine void.
    """
    for fixture in (plaque, chain):
        result = derive(fixture(), FabricationProfile.default())
        for body in result.bodies:
            assert body.z.thickness_mm > 0
            assert len(body.footprint.outer) >= 3
            assert len(set(body.footprint.outer)) == len(body.footprint.outer)

            for pocket in body.pockets:
                assert 0 < pocket.depth_mm < body.z.thickness_mm
                assert body.floor_beneath(pocket.for_region) > 0

                outside = poly.boolean_op(
                    [list(pocket.footprint)], [list(body.footprint.outer)], "difference"
                )
                assert abs(poly.total_area(outside)) < 1e-6

                for void in body.footprint.void_holes:
                    overlap = poly.boolean_op(
                        [list(pocket.footprint)], [list(void)], "intersection"
                    )
                    assert abs(poly.total_area(overlap)) < 1e-9


def test_the_new_artwork_reports_no_genuine_thin_support():
    """Corner artefacts are expected. A defect on ordinary artwork would not be."""
    for fixture in (plaque, chain):
        result = derive(fixture(), FabricationProfile.default())
        assert result.thin_support_findings() == ()
        assert {f.action for f in result.findings} <= {"reported_only"}


def test_the_result_still_carries_no_export_or_slicer_concerns():
    dumped_result = derive(plaque(), FabricationProfile.default()).to_dict()
    derived = {k: v for k, v in dumped_result.items() if k != "profile"}
    text = json.dumps(derived).lower()
    for word in ("stl", "3mf", "plate", "slicer", "filament", "gcode", "mesh"):
        assert word not in text, word


def test_the_known_annular_void_refusal_still_stands():
    """Scope boundary, demonstrated rather than solved.

    A child smaller than its hole leaves a hole with a hole in it, which
    `BodyFootprint`'s flat ring list cannot express. #8 refused it deliberately
    and #10 does not widen scope to fix it -- this only shows the refusal is
    still clear, and still a refusal rather than mis-shaped geometry.
    """
    hole = sq(10.0, 10.0, 20.0)
    smaller_child = sq(14.0, 14.0, 12.0)
    artwork = CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "white", sq(0.0, 0.0, 40.0), (hole,)),
            RegionSpec("K", "red", smaller_child),
        ]
    )

    with pytest.raises(FabricationError) as excinfo:
        derive(artwork, FabricationProfile.default())

    message = str(excinfo.value)
    assert "'P'" in message  # which region
    assert "annular" in message  # what shape it would need
    assert "refused rather than mis-shaped" in message  # and that it is a refusal
