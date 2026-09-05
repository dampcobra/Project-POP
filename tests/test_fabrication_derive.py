"""Tests for the canonical to fabrication derivation (issue #9).

    derive(artwork, profile) -> FabricationResult

The interesting properties are not "does it run" but the boundaries it holds:

- stacking is derived here, never supplied, so there is only one truth about it;
- support is a *strategy* at a named point, not a law of the body model;
- clearance exists on the fabrication side and nowhere else;
- canonical artwork goes in and comes out untouched;
- derived geometry is inspected and never repaired.

The strongest anchor in the file is `test_spike_glyph_reproduces_the_spike_02_stack`,
which checks the product's Z arithmetic against the spike's independent
implementation rather than against numbers copied out of it.
"""

import ast
import copy
import inspect
import json
from pathlib import Path

import pytest

from layercake.canonical import CanonicalArtwork, RegionSpec
from layercake.fabrication import (
    SUPPORTED_CHILD,
    FabricationError,
    FabricationProfile,
    FabricationResult,
    SupportedChildStrategy,
    derive,
    inspect_derived_geometry,
)
from layercake.fabrication import zplan
from layercake.geometry import polygons as poly
from layercake_spike import spec
from layercake_spike.spike02 import fabricate as spike_fabricate
from layercake_spike.spike02 import params as spike_params


def sq(x, y, size):
    return [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]


def spike_glyph() -> CanonicalArtwork:
    """Spike 01's three-level glyph: backing, foreground, island."""
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("A", "white", spec.BACKING_RING, (spec.B_OUTER_RING,)),
            RegionSpec("B", "red", spec.B_OUTER_RING, (spec.C_RING,)),
            RegionSpec("C", "yellow", spec.C_RING),
        ]
    )


def siblings() -> CanonicalArtwork:
    """One parent, two children side by side. Neither contains the other."""
    left, right = sq(2.0, 2.0, 4.0), sq(12.0, 2.0, 4.0)
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "white", sq(0.0, 0.0, 20.0), (left, right)),
            RegionSpec("L", "red", left),
            RegionSpec("R", "blue", right),
        ]
    )


def four_deep() -> CanonicalArtwork:
    """Deeper nesting than the Spike Glyph, to show levels are not capped at 3."""
    rings = [sq(1.0 * n, 1.0 * n, 20.0 - 2.0 * n) for n in range(4)]
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("R0", "white", rings[0], (rings[1],)),
            RegionSpec("R1", "red", rings[1], (rings[2],)),
            RegionSpec("R2", "blue", rings[2], (rings[3],)),
            RegionSpec("R3", "yellow", rings[3]),
        ]
    )


def child_beside_a_void() -> CanonicalArtwork:
    """A child so close to a genuine void that its clearance runs into it."""
    child = sq(2.0, 2.0, 5.0)
    void = sq(7.02, 2.0, 4.0)  # a 0.02 mm land, narrower than the clearance
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "white", sq(0.0, 0.0, 20.0), (child, void)),
            RegionSpec("K", "yellow", child),
        ]
    )


def thin_support() -> CanonicalArtwork:
    """A child that all but fills its parent, leaving a hairline of support."""
    child = sq(0.2, 0.2, 19.6)
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "white", sq(0.0, 0.0, 20.0), (child,)),
            RegionSpec("K", "yellow", child),
        ]
    )


def spike_02_profile() -> FabricationProfile:
    """The profile Spike 02 was actually printed at.

    Session 01 moved the *defaults* (backing 0.8 -> 1.2, seating 0.2 -> 0.80), so
    the literal Spike 02 stack is reproduced by stating that profile rather than
    by expecting today's defaults to still produce it. Setting it out here is the
    point: the arithmetic is what carried forward, not the numbers.
    """
    return (
        FabricationProfile.default()
        .with_backing_thickness(spike_params.ROUND1_AS_PRINTED_BACKING_MM)
        .with_visible_step_height(spike_params.H_VISIBLE_STEP_MM)
        .with_seating_depth(0.2)
    )


# --- the interface itself ----------------------------------------------------


def test_derive_takes_artwork_and_profile_and_nothing_about_stacking():
    """Stacking is derived internally. A caller cannot supply a competing one."""
    names = set(inspect.signature(derive).parameters)
    assert names == {"artwork", "profile", "strategy"}
    assert not any("stack" in name for name in names)


def test_stacking_in_the_result_is_the_one_derived_from_the_artwork():
    from layercake.stacking import derive_stacking_order

    artwork = spike_glyph()
    result = derive(artwork, FabricationProfile.default())
    assert result.stacking == derive_stacking_order(artwork)


def test_derive_returns_a_result_carrying_what_it_was_built_from():
    result = derive(spike_glyph(), FabricationProfile.default())
    assert isinstance(result, FabricationResult)
    assert result.strategy_name == "supported_child"
    assert result.region_ids() == ("A", "B", "C")
    assert result.profile is not None


def test_the_result_is_frozen():
    result = derive(spike_glyph(), FabricationProfile.default())
    with pytest.raises(Exception):
        result.strategy_name = "something_else"


# --- point 11: canonical artwork is an input, not a scratchpad ---------------


def test_canonical_artwork_is_unchanged_by_derivation():
    artwork = spike_glyph()
    before = copy.deepcopy(artwork.to_dump())

    derive(artwork, FabricationProfile.default())

    assert artwork.to_dump() == before


def test_the_artwork_is_unchanged_even_when_derivation_fails():
    artwork = child_beside_a_void()
    before = copy.deepcopy(artwork.to_dump())

    with pytest.raises(FabricationError):
        derive(artwork, FabricationProfile.default())

    assert artwork.to_dump() == before


# --- point 2: supported child is a strategy, not a law -----------------------


def test_the_strategy_is_named_and_reported():
    assert SUPPORTED_CHILD.name == "supported_child"
    result = derive(spike_glyph(), FabricationProfile.default())
    assert result.to_dict()["strategy"] == "supported_child"


def test_an_alternative_strategy_can_be_supplied_without_touching_the_body_model():
    """Stand-in for a future island-insert strategy.

    It keeps the hosting hole open and cuts no pocket -- the opposite of the
    supported-child choice on both counts. It needs no change to
    `FabricationBody`, `Pocket` or `BodyFootprint`, which is the property under
    test: support is not baked into what a body is.
    """

    class KeepTheHoleOpen(SupportedChildStrategy):
        def footprint_for(self, artwork, region_id):
            from layercake.fabrication.body import BodyFootprint

            return BodyFootprint(
                outer=tuple(artwork.outer_ring(region_id)),
                void_holes=tuple(
                    tuple(artwork.outer_ring(child))
                    for child in artwork.children_of(region_id)
                ),
            )

        def pockets_for(self, artwork, region_id, profile, footprint):
            return ()

    result = derive(
        spike_glyph(),
        FabricationProfile.default(),
        strategy=KeepTheHoleOpen(name="island_insert_stand_in"),
    )
    assert result.strategy_name == "island_insert_stand_in"
    assert result.body_for("A").pockets == ()
    assert len(result.voids_of("A")) == 1  # the hole stayed open


def test_canonical_valid_artwork_can_still_be_unbuildable_under_this_strategy():
    """The refusal names the strategy, so it reads as a consequence of it."""
    artwork = child_beside_a_void()
    artwork.validate()  # canonically fine

    with pytest.raises(FabricationError) as excinfo:
        derive(artwork, FabricationProfile.default())

    message = str(excinfo.value)
    assert "supported_child" in message
    assert "void" in message


def test_the_refusal_is_raised_at_the_strategy_boundary():
    """Not from `derive`, so the strategy stays the thing responsible."""
    artwork = child_beside_a_void()
    profile = FabricationProfile.default()
    with pytest.raises(FabricationError):
        SUPPORTED_CHILD.pockets_for(
            artwork, "P", profile, SUPPORTED_CHILD.footprint_for(artwork, "P")
        )


# --- point 4: pockets come from the outer footprint, not the visible surface -


def test_a_pocket_is_the_childs_outer_footprint_plus_clearance():
    """The #8 regression, guarded at the level that produces the geometry.

    B's *visible* surface excludes the island C. Its *outer* footprint includes
    it. A pocket cut from the visible surface would leave a false island of
    support standing in the middle of A's recess.
    """
    profile = FabricationProfile.default()
    result = derive(spike_glyph(), profile)

    pocket = result.body_for("A").pocket_for("B")
    outer_area = abs(poly.area(list(spec.B_OUTER_RING)))
    visible_area = outer_area - abs(poly.area(list(spec.C_RING)))

    assert abs(poly.area(list(pocket.footprint))) > outer_area
    assert abs(poly.area(list(pocket.footprint))) > visible_area * 1.05


def test_the_pocket_fully_covers_the_child_it_seats():
    result = derive(spike_glyph(), FabricationProfile.default())
    pocket = result.body_for("A").pocket_for("B")

    outside = poly.boolean_op(
        [list(spec.B_OUTER_RING)], [list(pocket.footprint)], "difference"
    )
    assert abs(poly.total_area(outside)) < 1e-6


def test_the_clearance_grows_the_pocket_not_the_child():
    """ADR 0002 decision 3: the allowance is applied to the recess."""
    loose = derive(
        spike_glyph(), FabricationProfile.default().with_per_side_clearance(0.2)
    )
    tight = derive(
        spike_glyph(), FabricationProfile.default().with_per_side_clearance(0.05)
    )

    assert abs(poly.area(list(loose.body_for("A").pocket_for("B").footprint))) > abs(
        poly.area(list(tight.body_for("A").pocket_for("B").footprint))
    )
    # the child body itself is identical at both clearances
    assert loose.body_for("B").footprint == tight.body_for("B").footprint


def test_every_child_gets_exactly_one_pocket_in_its_parent():
    result = derive(four_deep(), FabricationProfile.default())
    assert result.body_for("R0").hosted_regions() == ("R1",)
    assert result.body_for("R1").hosted_regions() == ("R2",)
    assert result.body_for("R2").hosted_regions() == ("R3",)
    assert result.body_for("R3").pockets == ()


# --- point 3: clearance is fabrication-only ----------------------------------


def test_the_shared_polygon_layer_still_has_no_offset():
    assert not [n for n in dir(poly) if "offset" in n or "dilate" in n]


def test_canonical_and_shared_geometry_do_not_reach_clearance_machinery():
    """Structural guard: an offset must not appear below the fabrication line.

    Checked by parsing rather than grepping, so a docstring mentioning offset
    does not trip it and an aliased import does not slip past it.
    """
    import layercake.canonical
    import layercake.geometry

    banned = {"offset_rings", "dilate", "erode"}
    offenders: list[str] = []

    for package in (layercake.canonical, layercake.geometry):
        for path in Path(package.__file__).parent.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "fabrication" in node.module:
                        offenders.append(f"{path.name}: imports {node.module}")
                    if any(a.name in banned for a in node.names):
                        offenders.append(f"{path.name}: imports {node.names[0].name}")
                elif isinstance(node, ast.Call):
                    name = getattr(node.func, "attr", None) or getattr(
                        node.func, "id", None
                    )
                    if name in banned:
                        offenders.append(f"{path.name}: calls {name}")

    assert offenders == [], offenders


# --- point 5: Z arithmetic is explicit, and refuses rather than guesses -------


def test_z_is_built_from_named_helpers():
    profile = FabricationProfile.default()
    assert zplan.level_top_mm(0, profile) == pytest.approx(
        profile.backing_thickness.mm
    )
    assert zplan.level_top_mm(2, profile) == pytest.approx(
        profile.backing_thickness.mm + 2 * profile.visible_step_height.mm
    )


def test_each_level_shows_exactly_one_visible_step():
    profile = FabricationProfile.default()
    result = derive(spike_glyph(), profile)
    tops = [result.body_for(r).z.top_mm for r in ("A", "B", "C")]

    steps = [b - a for a, b in zip(tops, tops[1:])]
    assert steps == pytest.approx([profile.visible_step_height.mm] * 2)


def test_completed_tops_are_invariant_in_seating_depth():
    """The Spike 02 property, carried into the product."""
    shallow = derive(spike_glyph(), spike_02_profile().with_seating_depth(0.2))
    deep = derive(spike_glyph(), spike_02_profile().with_seating_depth(0.4))

    for region in ("A", "B", "C"):
        assert shallow.body_for(region).z.top_mm == pytest.approx(
            deep.body_for(region).z.top_mm
        )
    assert deep.body_for("B").z.bottom_mm < shallow.body_for("B").z.bottom_mm


def test_a_recess_deeper_than_its_floor_is_refused_not_built():
    """A through-hole where a blind pocket was asked for. Raise, don't produce.

    Exercised against the helper directly, because `derive` validates the
    profile first and a valid profile cannot reach this state: it already
    requires the backing to host the seating depth plus a positive floor. The
    guard is kept anyway -- it is the last thing standing between a bad profile
    and geometry that looks plausible and is not.
    """
    unvalidated = (
        FabricationProfile.default()
        .with_backing_thickness(0.8)
        .with_seating_depth(0.8)
        .with_minimum_recess_floor(0.0)
    )
    with pytest.raises(FabricationError) as excinfo:
        zplan.check_floor_is_sound(0, "A", unvalidated)
    assert "through-hole" in str(excinfo.value)


def test_a_floor_under_the_profile_minimum_is_refused():
    """Reachable through `derive`: the profile is manufacturable, this stack isn't.

    A 0.2 mm visible step leaves only 0.2 mm under the recess in every body
    above the backing, which is under the 0.4 mm minimum. The profile itself
    passes validation -- only stacking it reveals the problem.
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
        derive(spike_glyph(), profile)
    assert "minimum" in str(excinfo.value)
    assert "'B'" in str(excinfo.value)


def test_the_default_profile_leaves_a_sound_floor_everywhere():
    profile = FabricationProfile.default()
    result = derive(spike_glyph(), profile)
    for region in ("A", "B"):
        body = result.body_for(region)
        floor = body.floor_beneath(body.hosted_regions()[0])
        assert floor >= profile.minimum_recess_floor.mm - 1e-9


def test_a_negative_level_is_refused():
    with pytest.raises(FabricationError):
        zplan.level_top_mm(-1, FabricationProfile.default())


# --- point 6: siblings, and peer order never becoming physical ---------------


def test_siblings_sit_at_the_same_level_and_the_same_height():
    result = derive(siblings(), FabricationProfile.default())
    assert result.level_of("L") == result.level_of("R") == 1
    assert result.body_for("L").z == result.body_for("R").z


def test_peer_order_does_not_change_any_geometry():
    """Peer order exists for reproducible output. It must not reach the Z model."""
    result = derive(siblings(), FabricationProfile.default())
    peers = result.stacking.levels[1].peers
    assert peers == ("L", "R")  # deterministic, and irrelevant below

    z_by_region = {r: result.body_for(r).z for r in ("L", "R")}
    assert z_by_region["L"] == z_by_region["R"]


def test_nesting_is_not_capped_at_three_levels():
    result = derive(four_deep(), FabricationProfile.default())
    assert [result.level_of(f"R{n}") for n in range(4)] == [0, 1, 2, 3]

    profile = FabricationProfile.default()
    assert result.body_for("R3").z.top_mm == pytest.approx(
        profile.backing_thickness.mm + 3 * profile.visible_step_height.mm
    )


# --- point 7: the result is explicitly inspectable ---------------------------


def test_the_result_answers_the_questions_it_is_meant_to():
    result = derive(spike_glyph(), FabricationProfile.default())

    assert result.body_for("B").region_id == "B"
    assert result.level_of("B") == 1
    assert result.body_for("A").hosts("B")
    assert result.voids_of("A") == ()
    assert result.body_for("C").z.thickness_mm > 0


def test_the_result_serialises_to_json_keeping_identities():
    dumped = derive(spike_glyph(), FabricationProfile.default()).to_dict()
    text = json.dumps(dumped)

    assert "supported_child" in text
    assert dumped["levels"] == {"A": 0, "B": 1, "C": 2}
    assert dumped["bodies"][0]["region_id"] == "A"
    assert "findings" in dumped


def test_the_result_carries_no_export_or_slicer_concerns():
    dumped = derive(spike_glyph(), FabricationProfile.default()).to_dict()

    # The profile is excluded: its parameters carry prose explaining *why* a
    # value is what it is, and some of that reasoning is about slicer layer
    # quantisation. What matters is that the derived output itself carries none.
    derived = {k: v for k, v in dumped.items() if k != "profile"}
    text = json.dumps(derived).lower()
    for word in ("stl", "3mf", "plate", "slicer", "filament", "gcode", "mesh"):
        assert word not in text, word


# --- point 8: inspected, never repaired --------------------------------------


def test_derived_geometry_is_not_modified_by_inspection():
    result = derive(spike_glyph(), FabricationProfile.default())
    before = result.bodies.to_dict()

    inspect_derived_geometry(result.bodies, result.profile)

    assert result.bodies.to_dict() == before


def test_every_finding_says_it_was_only_reported():
    result = derive(spike_glyph(), FabricationProfile.default())
    assert result.findings  # the glyph does produce some
    assert {f.action for f in result.findings} == {"reported_only"}


def test_the_spike_glyph_produces_corner_artefacts_and_no_genuine_defect():
    """Spike 02's lesson: a morphological probe reports its own corners.

    Every one of the glyph's findings is an internal corner tighter than the
    probe, which a nozzle rounds and nothing is lost by. None is thin support.
    """
    result = derive(spike_glyph(), FabricationProfile.default())
    assert {f.kind for f in result.findings} == {"corner_artifact"}
    assert result.thin_support_findings() == ()


def test_genuinely_thin_support_is_still_reported():
    """The counterpart: the noise floor must not be hiding real defects."""
    result = derive(thin_support(), FabricationProfile.default())
    thin = result.thin_support_findings()
    assert thin, [f.kind for f in result.findings]
    assert thin[0].region_id == "P"
    assert "thinner" in thin[0].detail


def test_thin_support_is_reported_rather_than_refused():
    """Report-only means derivation still completes and returns bodies."""
    result = derive(thin_support(), FabricationProfile.default())
    assert result.region_ids() == ("K", "P")
    assert result.body_for("P").footprint.outer


def test_a_hairline_sliver_along_a_sloped_edge_is_not_called_thin_support():
    """The offset round trip leaves micron-wide slivers on every sloped edge.

    An area floor alone passes a long one; a bounding box alone calls it thin
    support. Average width separates them, and the glyph's sloped outline is the
    case that found this.
    """
    result = derive(spike_glyph(), FabricationProfile.default())
    for finding in result.findings:
        assert finding.area_mm2 > 0


# --- point 9: derived bodies satisfy the preconditions for a manifold solid ---


def test_every_body_is_extrudable_as_a_closed_solid():
    """Checked as preconditions on the footprint, not by building a mesh.

    The proven mesh machinery lives in the spike, which the product package is
    forbidden to import, and the product has no mesh code of its own. Rather than
    duplicate an extruder to satisfy a criterion that exists to prevent exactly
    that duplication, #9's acceptance was amended to require these preconditions
    -- everything an extrusion needs to be true before it runs -- and mesh
    manifoldness was deferred to issue #19, along with the decision on whether to
    promote the Spike 02 extruder into the product rather than rewrite it.
    """
    result = derive(four_deep(), FabricationProfile.default())

    for body in result.bodies:
        assert body.z.thickness_mm > 0
        assert len(body.footprint.outer) >= 3
        assert abs(poly.area(list(body.footprint.outer))) > 0

        for pocket in body.pockets:
            assert 0 < pocket.depth_mm < body.z.thickness_mm

            outside = poly.boolean_op(
                [list(pocket.footprint)], [list(body.footprint.outer)], "difference"
            )
            assert abs(poly.total_area(outside)) < 1e-6, "pocket escapes the body"

            for void in body.footprint.void_holes:
                overlap = poly.boolean_op(
                    [list(pocket.footprint)], [list(void)], "intersection"
                )
                assert abs(poly.total_area(overlap)) < 1e-9


def test_pockets_in_one_body_do_not_overlap_each_other():
    result = derive(siblings(), FabricationProfile.default())
    left, right = result.body_for("P").pockets
    overlap = poly.boolean_op(
        [list(left.footprint)], [list(right.footprint)], "intersection"
    )
    assert abs(poly.total_area(overlap)) < 1e-9


def test_no_ring_in_a_derived_body_is_degenerate():
    result = derive(spike_glyph(), FabricationProfile.default())
    for body in result.bodies:
        rings = [body.footprint.outer, *body.footprint.void_holes]
        rings += [p.footprint for p in body.pockets]
        for ring in rings:
            assert len(ring) >= 3
            assert len(set(ring)) == len(ring), "repeated vertex in a derived ring"


# --- point 10: the regression anchor -----------------------------------------


def test_spike_glyph_reproduces_the_spike_02_stack():
    """The load-bearing test in this file.

    The product's Z model is checked against the spike's own `z_planes`, which
    was written independently and validated on a physical print. Not against
    numbers transcribed from it -- if either implementation drifts, this fails.

    Stated at the Spike 02 profile rather than today's defaults: Session 01
    deliberately moved backing (0.8 -> 1.2) and seating depth (0.2 -> 0.80), so
    the defaults no longer produce the printed numbers, and should not.
    """
    profile = spike_02_profile()
    result = derive(spike_glyph(), profile)

    h = spike_params.H_VISIBLE_STEP_MM
    white = spike_params.ROUND1_AS_PRINTED_BACKING_MM
    depth = 0.2

    red = spike_fabricate.z_planes(white, depth, h)
    yellow = spike_fabricate.z_planes(red.child_top, depth, h)

    assert result.body_for("A").z.bottom_mm == pytest.approx(0.0)
    assert result.body_for("A").z.top_mm == pytest.approx(white)

    assert result.body_for("B").z.bottom_mm == pytest.approx(red.child_bottom)
    assert result.body_for("B").z.top_mm == pytest.approx(red.child_top)
    assert result.body_for("B").z.thickness_mm == pytest.approx(red.child_thickness)

    assert result.body_for("C").z.bottom_mm == pytest.approx(yellow.child_bottom)
    assert result.body_for("C").z.top_mm == pytest.approx(yellow.child_top)

    # and the printed numbers themselves, spelled out
    assert [result.body_for(r).z.top_mm for r in ("A", "B", "C")] == pytest.approx(
        [0.8, 1.6, 2.4]
    )


def test_spike_glyph_reproduces_the_spike_02_structure():
    """Three bodies, each hosting the next, no voids anywhere."""
    result = derive(spike_glyph(), spike_02_profile())

    assert result.region_ids() == ("A", "B", "C")
    assert [result.level_of(r) for r in ("A", "B", "C")] == [0, 1, 2]
    assert result.body_for("A").hosted_regions() == ("B",)
    assert result.body_for("B").hosted_regions() == ("C",)
    assert result.body_for("C").pockets == ()
    assert all(result.voids_of(r) == () for r in ("A", "B", "C"))


def test_spike_glyph_areas_match_the_canonical_artwork():
    """Solidification is not allowed to lose or invent plan area."""
    result = derive(spike_glyph(), spike_02_profile())

    assert abs(poly.area(list(result.body_for("A").footprint.outer))) == pytest.approx(
        abs(poly.area(list(spec.BACKING_RING)))
    )
    assert abs(poly.area(list(result.body_for("B").footprint.outer))) == pytest.approx(
        abs(poly.area(list(spec.B_OUTER_RING)))
    )
    assert abs(poly.area(list(result.body_for("C").footprint.outer))) == pytest.approx(
        abs(poly.area(list(spec.C_RING)))
    )


# --- determinism -------------------------------------------------------------


def test_derivation_is_deterministic():
    a = derive(spike_glyph(), FabricationProfile.default()).to_dict()
    b = derive(spike_glyph(), FabricationProfile.default()).to_dict()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_an_unmanufacturable_profile_is_refused_before_any_geometry():
    from layercake.fabrication import ProfileError

    with pytest.raises((ProfileError, FabricationError)):
        derive(spike_glyph(), FabricationProfile.default().with_visible_step_height(0.0))
