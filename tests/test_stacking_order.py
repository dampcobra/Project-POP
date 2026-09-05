"""Tests for stacking order derivation (issue #7).

Stacking order is **derived** from canonical containment, never authored and
never stored back into the canonical model. Containment depth is the physical
level: regions nested one deeper sit one level higher.

The load-bearing semantic is that **siblings are peers**. Two islands inside the
same parent occupy the same physical level; neither sits above the other. They
are ordered within that level only so output is reproducible, and that ordering
carries no physical meaning at all.
"""

import dataclasses
import json

import pytest

from layercake.canonical import artwork as ca
from layercake.canonical import stacking as st
from layercake_spike import spec

SQ = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


def _square(x0, y0, size):
    return [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size)]


def spike_glyph() -> ca.CanonicalArtwork:
    return ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("A", "white", spec.BACKING_RING, (spec.B_OUTER_RING,)),
            ca.RegionSpec("B", "red", spec.B_OUTER_RING, (spec.C_RING,)),
            ca.RegionSpec("C", "yellow", spec.C_RING),
        ]
    )


# --- the Spike Glyph ---------------------------------------------------------


def test_the_spike_glyph_derives_backing_foreground_island():
    order = st.derive_stacking_order(spike_glyph())
    assert [lv.peers for lv in order.levels] == [("A",), ("B",), ("C",)]
    assert order.level_of("A") == 0
    assert order.level_of("B") == 1
    assert order.level_of("C") == 2


def test_the_derived_order_renders_the_intended_shape():
    text = st.derive_stacking_order(spike_glyph()).describe()
    assert text.splitlines() == [
        "level 0: A",
        "level 1: B",
        "level 2: C",
    ]


def test_level_matches_canonical_containment_depth():
    art = spike_glyph()
    order = st.derive_stacking_order(art)
    for rid in art.regions:
        assert order.level_of(rid) == art.containment_depth(rid)


# --- arbitrary nesting depth -------------------------------------------------


def test_arbitrary_nesting_depth_works():
    specs = []
    for i in range(6):
        size = 60 - i * 8
        outer = _square(i * 4.0, i * 4.0, size)
        inner = _square((i + 1) * 4.0, (i + 1) * 4.0, 60 - (i + 1) * 8)
        holes = (inner,) if i < 5 else ()
        specs.append(ca.RegionSpec(f"r{i}", f"c{i}", outer, holes))
    order = st.derive_stacking_order(ca.CanonicalArtwork.from_specs(specs))
    assert len(order) == 6
    assert [lv.peers for lv in order.levels] == [(f"r{i}",) for i in range(6)]


def test_a_single_region_is_one_level():
    art = ca.CanonicalArtwork.from_specs([ca.RegionSpec("only", "red", SQ)])
    order = st.derive_stacking_order(art)
    assert len(order) == 1
    assert order.levels[0].peers == ("only",)


# --- siblings are peers ------------------------------------------------------


def siblings_artwork() -> ca.CanonicalArtwork:
    """One parent, two islands. The islands are peers, not a stack."""
    kid_a = _square(1.0, 1.0, 3.0)
    kid_b = _square(6.0, 6.0, 3.0)
    return ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("parent", "red", SQ, (kid_a, kid_b)),
            ca.RegionSpec("kid_a", "yellow", kid_a),
            ca.RegionSpec("kid_b", "blue", kid_b),
        ]
    )


def test_siblings_occupy_the_same_physical_level():
    order = st.derive_stacking_order(siblings_artwork())
    assert len(order) == 2
    assert order.levels[1].peers == ("kid_a", "kid_b")
    assert order.level_of("kid_a") == order.level_of("kid_b") == 1


def test_peers_of_reports_co_level_regions():
    order = st.derive_stacking_order(siblings_artwork())
    assert order.peers_of("kid_a") == ("kid_a", "kid_b")
    assert order.peers_of("parent") == ("parent",)


def test_disjoint_top_level_regions_are_peers_at_level_zero():
    art = ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("left", "red", _square(0.0, 0.0, 5.0)),
            ca.RegionSpec("right", "blue", _square(20.0, 0.0, 5.0)),
        ]
    )
    order = st.derive_stacking_order(art)
    assert len(order) == 1
    assert order.levels[0].peers == ("left", "right")


def test_peer_order_carries_no_physical_meaning():
    """Ordering within a level exists only so output is reproducible.

    Nothing in the structure says one peer is above another: they share a level
    index, and that is the only physical statement made about them.
    """
    order = st.derive_stacking_order(siblings_artwork())
    level = order.levels[1]
    assert order.level_of("kid_a") == order.level_of("kid_b") == level.index
    assert order.is_peer_of("kid_a", "kid_b")
    assert not order.is_peer_of("kid_a", "parent")


# --- determinism -------------------------------------------------------------


def test_the_same_artwork_derives_identically_every_time():
    art = spike_glyph()
    assert st.derive_stacking_order(art) == st.derive_stacking_order(art)


def test_authoring_order_does_not_change_the_result():
    """Equivalent artwork authored in a different region order derives the same."""
    kid_a = _square(1.0, 1.0, 3.0)
    kid_b = _square(6.0, 6.0, 3.0)
    forward = [
        ca.RegionSpec("parent", "red", SQ, (kid_a, kid_b)),
        ca.RegionSpec("kid_a", "yellow", kid_a),
        ca.RegionSpec("kid_b", "blue", kid_b),
    ]
    shuffled = [forward[2], forward[0], forward[1]]
    assert st.derive_stacking_order(
        ca.CanonicalArtwork.from_specs(forward)
    ) == st.derive_stacking_order(ca.CanonicalArtwork.from_specs(shuffled))


def test_the_tie_break_is_region_id_not_geometry():
    """A larger sibling must not sort first just because it is larger."""
    big = _square(1.0, 1.0, 7.0)  # id sorts second, area is larger
    small = _square(20.0, 20.0, 2.0)  # disjoint, so both are level 0 peers
    art = ca.CanonicalArtwork.from_specs(
        [
            ca.RegionSpec("zzz_big", "red", big),
            ca.RegionSpec("aaa_small", "blue", small),
        ]
    )
    order = st.derive_stacking_order(art)
    assert order.levels[0].peers == ("aaa_small", "zzz_big")


def test_the_tie_break_is_not_declaration_order():
    a = _square(0.0, 0.0, 3.0)
    b = _square(10.0, 0.0, 3.0)
    declared_b_first = ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("b", "x", b), ca.RegionSpec("a", "y", a)]
    )
    assert st.derive_stacking_order(declared_b_first).levels[0].peers == ("a", "b")


# --- inconsistent containment ------------------------------------------------


def mutually_enclosing() -> ca.CanonicalArtwork:
    """Two regions with identical footprints enclose each other.

    This is the only way a cycle is reachable through the public API, and the
    artwork is already invalid: `validate()` reports 100% overlap. The cycle is
    a symptom of that, not an independent failure mode.
    """
    return ca.CanonicalArtwork.from_specs(
        [ca.RegionSpec("P", "red", SQ), ca.RegionSpec("Q", "blue", list(SQ))]
    )


def test_a_cycle_is_actually_reachable_through_the_public_api():
    art = mutually_enclosing()
    assert art.parent_of("P") == "Q" and art.parent_of("Q") == "P"
    assert art.roots() == ()


def test_such_artwork_is_already_invalid_as_a_visible_partition():
    assert not mutually_enclosing().validate().ok


def test_deriving_a_stacking_order_from_a_cycle_raises():
    with pytest.raises(st.StackingError) as e:
        st.derive_stacking_order(mutually_enclosing())
    msg = str(e.value)
    assert "P" in msg and "Q" in msg
    assert "cycle" in msg.lower()


def test_containment_depth_raises_on_a_cycle_instead_of_hanging():
    """Found by #7: the walk in `ancestors_of` had no cycle guard."""
    art = mutually_enclosing()
    with pytest.raises(ca.ArtworkError, match="cycle"):
        art.ancestors_of("P")
    with pytest.raises(ca.ArtworkError, match="cycle"):
        art.containment_depth("P")


# --- the derived structure ---------------------------------------------------


def test_the_result_is_immutable():
    order = st.derive_stacking_order(spike_glyph())
    with pytest.raises(dataclasses.FrozenInstanceError):
        order.levels = ()  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        order.levels[0].index = 5  # type: ignore[misc]
    with pytest.raises(AttributeError):
        order.levels[0].peers.append("X")  # type: ignore[attr-defined]


def test_nothing_is_written_back_into_the_canonical_model():
    art = spike_glyph()
    reference = spike_glyph()
    st.derive_stacking_order(art)
    assert art == reference


def test_the_canonical_model_gained_no_stacking_state():
    art = spike_glyph()
    for name in dir(art):
        assert "stack" not in name.lower(), name
        assert "level" not in name.lower(), name
    for f in dataclasses.fields(ca.Region):
        assert "stack" not in f.name.lower() and "level" not in f.name.lower()


def test_lookup_by_level_and_by_region():
    order = st.derive_stacking_order(spike_glyph())
    assert order.peers_at(1) == ("B",)
    assert order.region_ids() == ("A", "B", "C")
    with pytest.raises(KeyError):
        order.level_of("nope")
    with pytest.raises(IndexError):
        order.peers_at(99)


def test_the_result_is_json_safe_and_explicit():
    d = st.derive_stacking_order(spike_glyph()).to_dict()
    json.dumps(d)
    assert d["levels"] == [
        {"index": 0, "peers": ["A"]},
        {"index": 1, "peers": ["B"]},
        {"index": 2, "peers": ["C"]},
    ]
    assert "peer order" in d["note"].lower() or "reproduc" in d["note"].lower()


# --- scope -------------------------------------------------------------------

_FABRICATION_WORDS = (
    "thickness", "clearance", "seating", "recess", "backing", "pocket",
    "solid", "material", "profile", "_mm", "height", "depth_mm",
)


def test_stacking_carries_no_fabrication_concerns():
    order = st.derive_stacking_order(spike_glyph())
    names = [n for n in dir(order) if not n.startswith("_")]
    names += [n for n in dir(st) if not n.startswith("_")]
    for name in names:
        for word in _FABRICATION_WORDS:
            assert word not in name.lower(), name
