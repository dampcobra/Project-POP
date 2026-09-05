"""Tests for the canonical artwork model (issue #6).

The model describes **what the artwork is**, not how it will be manufactured.
No Z, no thickness, no clearance, no seating depth, no backing.

Spike 01's topology invariants carry over unchanged: vertices interned through
one table, and a shared boundary as a single edge record naming both incident
regions rather than two copies that happen to coincide.
"""

import copy
import dataclasses
import math

import pytest

from layercake.canonical import artwork as ca

# The Spike Glyph, imported from the spike so the coordinates are not duplicated.
# Tests may depend on both packages; the product package may not (see #5).
from layercake_spike import spec

SQ = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
INNER = [(3.0, 3.0), (7.0, 3.0), (7.0, 7.0), (3.0, 7.0)]


def spike_glyph() -> ca.CanonicalArtwork:
    """The Spike Glyph expressed in the canonical model.

    Visible-surface semantics (ADR 0003): a parent is canonically absent
    wherever a visible child covers it. So the backing has a hole where the
    foreground sits, just as the foreground has one where the island sits.

    Spike 01 authored the backing solid, because Z-band filtering meant the
    overlap was never compared. That is the one substantive change here.
    """
    return ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("A", "white", spec.BACKING_RING, (spec.B_OUTER_RING,)),
            ca.RegionSpec("B", "red", spec.B_OUTER_RING, (spec.C_RING,)),
            ca.RegionSpec("C", "yellow", spec.C_RING),
        ]
    )


# --- fabrication-free --------------------------------------------------------

#: Words that would signal a fabrication concern leaking into the model.
#: Deliberately not a bare "depth": `containment_depth` is topology -- how many
#: regions enclose this one -- and has nothing to do with a seating depth.
_FABRICATION_WORDS = (
    "z_", "_z", "thickness", "clearance", "seating", "seating_depth",
    "recess", "recess_depth", "backing", "layer_height", "floor", "pocket",
)


def _field_names(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def test_the_model_carries_no_fabrication_concerns():
    for cls in (ca.RegionSpec, ca.Region):
        for name in _field_names(cls):
            for word in _FABRICATION_WORDS:
                assert word not in name.lower(), f"{cls.__name__}.{name}"


def test_the_artwork_type_exposes_no_fabrication_attributes():
    art = spike_glyph()
    for attr in dir(art):
        if attr.startswith("_"):
            continue
        for word in _FABRICATION_WORDS:
            assert word not in attr.lower(), attr


#: Words that would signal a translucency or colour-mixing model creeping in.
#: ADR 0003: canonical artwork is opaque visible colour. The visible result
#: comes from the explicit surface colours, never from contribution through a
#: region to material beneath it.
_TRANSLUCENCY_WORDS = (
    "opacity", "alpha", "translucen", "transparen", "blend", "composite",
    "underlying", "showthrough", "show_through", "tint",
)


def test_the_model_has_no_translucency_or_colour_mixing_concept():
    art = spike_glyph()
    surfaces = [n for n in dir(art) if not n.startswith("_")]
    surfaces += [f.name for f in dataclasses.fields(ca.Region)]
    surfaces += [f.name for f in dataclasses.fields(ca.RegionSpec)]
    for name in surfaces:
        for word in _TRANSLUCENCY_WORDS:
            assert word not in name.lower(), name


def test_a_colour_is_an_opaque_identity_not_a_contribution():
    """Two regions of one colour are the same colour, with nothing to combine."""
    art = spike_glyph()
    assert art.regions["C"].colour == "yellow"
    # a colour is a plain label: no channels, no coverage, nothing to mix
    assert isinstance(art.regions["C"].colour, str)


def test_the_canonical_package_never_offsets_geometry():
    """Offsetting is how clearance is applied. It has no place in canonical.

    The canonical polygon adapter deliberately provides no offset operation, so
    a fabrication clearance cannot leak in without someone adding one.
    """
    from layercake.geometry import polygons

    assert not hasattr(polygons, "offset")
    assert not any("offset" in n.lower() for n in dir(polygons))


# --- Spike 01 topology invariants --------------------------------------------


def test_vertices_are_interned_through_one_table():
    art = spike_glyph()
    b_hole = set(art.regions["B"].holes[0])
    c_outer = set(art.regions["C"].outer)
    assert b_hole == c_outer, "a shared boundary must be one set of vertices"


def test_shared_edges_are_single_records_naming_both_regions():
    shared = spike_glyph().shared_edges()
    for _edge, regions in shared.items():
        assert len(regions) == 2
        assert sorted(regions) in (["A", "B"], ["B", "C"])


def test_the_shared_edge_count_changed_from_spike_01_and_that_is_correct():
    """Spike 01 saw 4 shared edges. The Spike Glyph has 15.

    Not a regression. Spike 01 authored the backing solid beneath the
    foreground and never compared them, because `Partition.containment()`
    filtered by Z band. Under visible-surface semantics (ADR 0003) the backing
    is canonically absent where the foreground covers it, so the foreground's
    whole boundary is now a genuine shared boundary.

    The old count was an artefact of Z-band filtering, not a product invariant.
    """
    from layercake_spike import topology as spike_topology

    spike = spike_topology.Partition.build(spec.REGIONS)
    assert len(spike.shared_edges()) == 4, "what the spike saw"

    shared = spike_glyph().shared_edges()
    pairs = [tuple(sorted(r)) for r in shared.values()]
    assert pairs.count(("A", "B")) == len(spec.B_OUTER_RING) == 11
    assert pairs.count(("B", "C")) == len(spec.C_RING) == 4
    assert len(shared) == 15


def test_adjacency_reports_regions_that_share_a_boundary():
    adj = spike_glyph().adjacency()
    assert adj["A"] == ("B",)
    assert adj["B"] == ("A", "C")
    assert adj["C"] == ("B",)


def test_epsilon_snapping_still_merges_coincident_points():
    art = ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("a", "x", SQ),
            ca.RegionSpec("b", "y", [(p[0] + 1e-9, p[1] - 1e-9) for p in INNER]),
            ca.RegionSpec("c", "z", INNER),
        ]
    )
    assert set(art.regions["b"].outer) == set(art.regions["c"].outer)


# --- containment, Z-free -----------------------------------------------------


def test_containment_is_a_nesting_tree_with_direct_parents():
    art = spike_glyph()
    assert art.parent_of("C") == "B"
    assert art.parent_of("B") == "A"
    assert art.parent_of("A") is None
    assert art.children_of("A") == ("B",)
    assert art.children_of("B") == ("C",)
    assert art.children_of("C") == ()


def test_containment_is_no_longer_z_filtered_and_that_is_the_point():
    """Spike 01 hid A-contains-B behind a Z-band filter.

    `Partition.containment()` skipped any pair in different Z bands, so the
    backing appeared to contain nothing. With Z gone the relationship is purely
    geometric, and A containing B is exactly the nesting #7 needs to derive a
    stacking order from.
    """
    from layercake_spike import topology as spike_topology

    spike = spike_topology.Partition.build(spec.REGIONS).containment()
    assert spike["A"] == [], "Spike 01 saw no containment for the backing"

    art = spike_glyph()
    assert art.children_of("A") == ("B",), "the product model does see it"


def test_transitive_containment_is_available_but_distinct_from_direct():
    art = spike_glyph()
    assert art.contains("A", "C") is True  # geometrically
    assert art.children_of("A") == ("B",)  # but C is not a direct child
    assert art.ancestors_of("C") == ("B", "A")


def test_depth_is_available_for_stacking_order_to_build_on():
    """#6 exposes the topology; #7 turns it into an order."""
    art = spike_glyph()
    assert art.containment_depth("A") == 0
    assert art.containment_depth("B") == 1
    assert art.containment_depth("C") == 2


def test_siblings_are_reported_as_peers():
    art = ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("parent", "red", SQ, (INNER, [(8.0, 8.0), (9.0, 8.0), (9.0, 9.0), (8.0, 9.0)])),
            ca.RegionSpec("kid1", "yellow", INNER),
            ca.RegionSpec("kid2", "blue", [(8.0, 8.0), (9.0, 8.0), (9.0, 9.0), (8.0, 9.0)]),
        ]
    )
    assert set(art.children_of("parent")) == {"kid1", "kid2"}
    assert art.containment_depth("kid1") == art.containment_depth("kid2") == 1


def test_disjoint_top_level_regions_are_supported():
    far = [(20.0, 20.0), (25.0, 20.0), (25.0, 25.0), (20.0, 25.0)]
    art = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("a", "red", SQ), ca.RegionSpec("b", "blue", far)]
    )
    assert art.parent_of("a") is None and art.parent_of("b") is None
    assert art.roots() == ("a", "b")


# --- colour-count agnostic ---------------------------------------------------


def test_any_number_of_colours_is_data_not_code():
    rings = [
        [(x, 0.0), (x + 1.0, 0.0), (x + 1.0, 1.0), (x, 1.0)] for x in range(6)
    ]
    art = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec(f"r{i}", f"colour{i}", r) for i, r in enumerate(rings)]
    )
    assert len(art.colours()) == 6
    art.validate()


def test_several_regions_may_share_one_colour():
    a = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    b = [(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)]
    art = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("one", "yellow", a), ca.RegionSpec("two", "yellow", b)]
    )
    assert art.colours() == ("yellow",)
    assert set(art.regions_with_colour("yellow")) == {"one", "two"}


# --- immutability ------------------------------------------------------------


def test_artwork_is_not_mutated_by_inspection():
    art = spike_glyph()
    before = copy.deepcopy(art)
    art.shared_edges()
    art.adjacency()
    art.containment_depth("C")
    art.validate()
    art.to_dump()
    assert art == before


def test_regions_are_frozen():
    art = spike_glyph()
    with pytest.raises(Exception):
        art.regions["B"].colour = "green"  # type: ignore[misc]


def test_input_rings_are_not_mutated():
    original = copy.deepcopy(spec.B_OUTER_RING)
    spike_glyph()
    assert spec.B_OUTER_RING == original


# --- numeric validation ------------------------------------------------------


def test_a_clean_artwork_validates_with_no_overlap():
    r = spike_glyph().validate()
    assert r.ok
    assert r.overlap_area < r.tolerance
    assert r.tolerance > 0


def test_the_visible_partition_tiles_the_artwork_exactly():
    """ADR 0003: every point of the artwork shows exactly one colour."""
    art = spike_glyph()
    visible = {rid: art.solid_area(rid) for rid in art.regions}
    assert math.isclose(visible["A"], 1534.0, rel_tol=1e-9)
    assert math.isclose(visible["B"], 902.0, rel_tol=1e-9)
    assert math.isclose(visible["C"], 64.0, rel_tol=1e-9)
    # 50 x 50 badge, covered once and only once
    assert math.isclose(sum(visible.values()), 2500.0, rel_tol=1e-9)
    r = art.validate()
    assert r.overlap_area < r.tolerance and r.void_area < r.tolerance


def test_overlap_is_detected_when_two_colours_claim_the_same_area():
    """The island sits on the enclosing colour instead of in a hole."""
    art = ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("B", "red", spec.B_OUTER_RING),  # no hole for C
            ca.RegionSpec("C", "yellow", spec.C_RING),
        ]
    )
    r = art.validate()
    assert not r.ok
    assert math.isclose(r.overlap_area, 64.0, rel_tol=1e-6)
    assert "B" in str(r.overlaps[0]) and "C" in str(r.overlaps[0])


def test_material_beneath_a_child_is_not_expressible_as_canonical_overlap():
    """ADR 0003: hidden support is a fabrication concern, introduced downstream.

    Authoring the backing solid beneath the foreground -- as Spike 01 did -- is
    now a validation error, not a way to say "there is material under there".
    Material continuation belongs to #8/#9.
    """
    art = ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("A", "white", spec.BACKING_RING),  # solid, no hole for B
            ca.RegionSpec("B", "red", spec.B_OUTER_RING, (spec.C_RING,)),
            ca.RegionSpec("C", "yellow", spec.C_RING),
        ]
    )
    r = art.validate()
    assert not r.ok
    overlapping = {tuple(sorted((o.first, o.second))) for o in r.overlaps}
    assert ("A", "B") in overlapping and ("A", "C") in overlapping


def test_overlap_is_an_error_between_ancestors_too_not_only_siblings():
    """A visible partition admits no overlap at all, at any nesting depth."""
    art = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("outer", "red", SQ), ca.RegionSpec("inner", "blue", INNER)]
    )
    assert art.parent_of("inner") == "outer"  # a real ancestor relationship
    assert not art.validate().ok  # and still an overlap error


def test_a_hole_with_no_child_is_a_void_and_is_reported_not_an_error():
    """Per #8 a genuine void is legal artwork; it is surfaced, not rejected."""
    art = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("B", "red", SQ, (INNER,))]  # nothing occupies the hole
    )
    r = art.validate()
    assert r.ok, "a void is legal"
    assert math.isclose(r.void_area, 16.0, rel_tol=1e-6)


def test_a_filled_hole_reports_no_void():
    art = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("B", "red", SQ, (INNER,)), ca.RegionSpec("C", "blue", INNER)]
    )
    r = art.validate()
    assert r.ok
    assert r.void_area < r.tolerance


def test_tolerance_is_explicit_and_configurable():
    art = spike_glyph()
    assert art.validate(tolerance=1e-9).ok
    assert art.validate().tolerance == ca.DEFAULT_TOLERANCE


def test_duplicate_region_ids_are_rejected():
    with pytest.raises(ca.ArtworkError, match="duplicate"):
        ca.CanonicalArtwork.from_specs(
            [ca.RegionSpec("x", "red", SQ), ca.RegionSpec("x", "blue", INNER)]
        )


def test_a_degenerate_ring_is_rejected():
    with pytest.raises(ca.ArtworkError):
        ca.CanonicalArtwork.from_specs(
            [ca.RegionSpec("x", "red", [(0.0, 0.0), (1.0, 1.0)])]
        )


# --- dump --------------------------------------------------------------------


def test_dump_is_json_safe_and_records_the_topology():
    import json

    dump = spike_glyph().to_dump()
    json.dumps(dump)
    assert dump["counts"]["regions"] == 3
    assert dump["counts"]["shared_edges"] == 15  # see ADR 0003
    assert dump["regions"]["B"]["parent"] == "A"
    assert dump["regions"]["B"]["children"] == ["C"]
    assert dump["regions"]["B"]["colour"] == "red"
    assert "z" not in json.dumps(dump["regions"]["B"]).lower().replace("size", "")
