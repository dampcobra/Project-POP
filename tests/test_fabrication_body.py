"""Tests for the fabrication body model (issue #8).

The central distinction, made explicit in the model rather than inferred later
from anonymous polygons:

    canonical hole that hosts a child  ->  solidified, with a registration pocket
    canonical hole with no child       ->  genuine void, stays a real hole

The Spike Glyph has no void, so the fixture that matters most here is new: one
parent carrying both kinds of hole at once.
"""

import ast
import dataclasses
import json
import math
from pathlib import Path

import pytest

from layercake.canonical import CanonicalArtwork, RegionSpec
from layercake.fabrication import body as fb
from layercake.geometry import polygons as poly
from layercake_spike import spec


def sq(x, y, size):
    return [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]


HOSTED_HOLE = sq(2.0, 2.0, 5.0)  # a child sits exactly here
VOID_HOLE = sq(12.0, 12.0, 4.0)  # nothing sits here


def both_kinds() -> CanonicalArtwork:
    """A parent with a child-hosting hole AND a genuine void. New for #8."""
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "red", sq(0.0, 0.0, 20.0), (HOSTED_HOLE, VOID_HOLE)),
            RegionSpec("K", "yellow", HOSTED_HOLE),
        ]
    )


def spike_glyph() -> CanonicalArtwork:
    return CanonicalArtwork.from_specs(
        [
            RegionSpec("A", "white", spec.BACKING_RING, (spec.B_OUTER_RING,)),
            RegionSpec("B", "red", spec.B_OUTER_RING, (spec.C_RING,)),
            RegionSpec("C", "yellow", spec.C_RING),
        ]
    )


def ring_area(ring) -> float:
    return abs(poly.area(list(ring)))


# --- the central distinction -------------------------------------------------


def test_a_child_hosting_hole_is_solidified_away():
    fp = fb.solidified_footprint(both_kinds(), "P")
    assert not any(
        math.isclose(ring_area(h), ring_area(HOSTED_HOLE), rel_tol=1e-9)
        for h in fp.void_holes
    ), "the hole K sits in must not survive as a hole"


def test_a_genuine_void_remains_a_real_hole():
    fp = fb.solidified_footprint(both_kinds(), "P")
    assert len(fp.void_holes) == 1
    assert math.isclose(ring_area(fp.void_holes[0]), 16.0, rel_tol=1e-9)


def test_the_footprint_area_shows_one_hole_filled_and_one_kept():
    fp = fb.solidified_footprint(both_kinds(), "P")
    # 20x20 outer, 5x5 hosted hole filled back in, 4x4 void still open
    assert math.isclose(fp.area_mm2, 400.0 - 16.0, rel_tol=1e-9)


def test_the_canonical_region_still_reports_both_holes():
    """Fabrication solidifies; canonical is untouched and still sees two holes."""
    art = both_kinds()
    assert len(art.regions["P"].holes) == 2
    fb.solidified_footprint(art, "P")
    assert len(art.regions["P"].holes) == 2


def test_no_through_hole_remains_where_a_child_seats():
    """The direct assertion available at this layer.

    The ticket says "Euler number check". Euler number is a property of a mesh,
    and a footprint here is rings of 2D points -- there is no mesh to read one
    from. The equivalent statement in this representation is that no hole of the
    fabrication footprint encloses the child's area, which is asserted directly.
    Spike 02 already asserts the Euler number on meshes; that belongs to #9.
    """
    fp = fb.solidified_footprint(both_kinds(), "P")
    for hole in fp.void_holes:
        covered = poly.boolean_op([list(HOSTED_HOLE)], [list(hole)], "intersection")
        assert abs(poly.total_area(covered)) < 1e-9


def test_a_void_does_enclose_its_own_area():
    fp = fb.solidified_footprint(both_kinds(), "P")
    covered = poly.boolean_op(
        [list(VOID_HOLE)], [list(fp.void_holes[0])], "intersection"
    )
    assert math.isclose(abs(poly.total_area(covered)), 16.0, rel_tol=1e-9)


def test_the_spike_glyph_has_no_voids():
    for region_id in ("A", "B", "C"):
        assert fb.solidified_footprint(spike_glyph(), region_id).void_holes == ()


def test_a_partly_covered_hole_leaving_an_annular_void_is_refused():
    """A child smaller than its hole leaves a void that is itself annular.

    Legal canonical artwork -- ADR 0003 allows voids -- but a flat list of hole
    rings cannot express a hole with a hole in it. Refused rather than silently
    mis-shaped. See the PR: this is a case for #9 to decide, not one to invent a
    representation for here.
    """
    art = CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "red", sq(0.0, 0.0, 20.0), (sq(2.0, 2.0, 8.0),)),
            RegionSpec("K", "yellow", sq(4.0, 4.0, 4.0)),  # inside, but smaller
        ]
    )
    with pytest.raises(fb.FabricationError, match="annular|partly"):
        fb.solidified_footprint(art, "P")


def test_a_child_touching_the_hole_edge_leaves_a_plain_void():
    """Partly covered but simply connected: this one is representable."""
    art = CanonicalArtwork.from_specs(
        [
            RegionSpec("P", "red", sq(0.0, 0.0, 20.0), (sq(2.0, 2.0, 8.0),)),
            RegionSpec("K", "yellow", [(2.0, 2.0), (10.0, 2.0), (10.0, 6.0), (2.0, 6.0)]),
        ]
    )
    fp = fb.solidified_footprint(art, "P")
    assert len(fp.void_holes) == 1
    assert math.isclose(ring_area(fp.void_holes[0]), 8.0 * 4.0, rel_tol=1e-9)


# --- traceability ------------------------------------------------------------


def a_body(**overrides) -> fb.FabricationBody:
    defaults = dict(
        region_id="P",
        footprint=fb.BodyFootprint(outer=tuple(sq(0.0, 0.0, 20.0))),
        z=fb.ZExtent(bottom_mm=0.0, top_mm=1.2),
        pockets=(
            fb.Pocket(for_region="K", footprint=tuple(HOSTED_HOLE), depth_mm=0.8),
        ),
    )
    defaults.update(overrides)
    return fb.FabricationBody(**defaults)


def test_a_body_names_the_canonical_region_it_realises():
    assert a_body().region_id == "P"


def test_region_to_body_and_body_to_region_are_both_queryable():
    bodies = fb.FabricationBodies(bodies=(a_body(), a_body(region_id="K", pockets=())))
    assert bodies.body_for("P").region_id == "P"
    assert bodies.region_ids() == ("K", "P")
    with pytest.raises(KeyError):
        bodies.body_for("nope")


def test_every_pocket_identifies_the_child_region_it_seats():
    body = a_body()
    assert body.hosted_regions() == ("K",)
    assert body.pocket_for("K").for_region == "K"
    assert body.hosts("K") and not body.hosts("Z")
    with pytest.raises(KeyError):
        body.pocket_for("Z")


def test_reporting_preserves_the_identifiers():
    d = fb.FabricationBodies(bodies=(a_body(),)).to_dict()
    json.dumps(d)
    entry = d["bodies"][0]
    assert entry["region_id"] == "P"
    assert entry["pockets"][0]["for_region"] == "K"
    assert entry["void_hole_count"] == 0


def test_reporting_names_voids_distinctly_from_pockets():
    body = a_body(
        footprint=fb.BodyFootprint(
            outer=tuple(sq(0.0, 0.0, 20.0)), void_holes=(tuple(VOID_HOLE),)
        )
    )
    d = body.to_dict()
    assert d["void_hole_count"] == 1
    assert [p["for_region"] for p in d["pockets"]] == ["K"]


# --- Z semantics -------------------------------------------------------------


def test_z_planes_are_named_quantities_not_tuple_positions():
    z = fb.ZExtent(bottom_mm=0.4, top_mm=1.6)
    assert z.bottom_mm == 0.4 and z.top_mm == 1.6
    assert math.isclose(z.thickness_mm, 1.2, abs_tol=1e-12)


def test_material_remaining_beneath_a_pocket_is_explicit():
    body = a_body(z=fb.ZExtent(bottom_mm=0.0, top_mm=1.2))
    assert math.isclose(body.floor_beneath("K"), 1.2 - 0.8, abs_tol=1e-12)


def test_the_floor_is_derived_so_it_cannot_disagree_with_the_body():
    body = a_body(z=fb.ZExtent(bottom_mm=0.0, top_mm=2.0))
    assert math.isclose(body.floor_beneath("K"), 1.2, abs_tol=1e-12)


def test_the_report_states_the_floor_beneath_each_pocket():
    d = a_body().to_dict()
    assert math.isclose(d["pockets"][0]["floor_mm"], 0.4, abs_tol=1e-12)


# --- invariants --------------------------------------------------------------


def test_a_pocket_depth_must_be_positive():
    with pytest.raises(fb.FabricationError, match="depth"):
        fb.Pocket(for_region="K", footprint=tuple(HOSTED_HOLE), depth_mm=0.0)


def test_a_pocket_must_name_a_child_region():
    with pytest.raises(fb.FabricationError, match="region"):
        fb.Pocket(for_region="", footprint=tuple(HOSTED_HOLE), depth_mm=0.4)


def test_a_body_cannot_carry_two_pockets_for_the_same_child():
    with pytest.raises(fb.FabricationError, match="more than one pocket"):
        a_body(
            pockets=(
                fb.Pocket(for_region="K", footprint=tuple(HOSTED_HOLE), depth_mm=0.4),
                fb.Pocket(for_region="K", footprint=tuple(VOID_HOLE), depth_mm=0.4),
            )
        )


def test_a_pocket_deeper_than_its_body_is_refused():
    with pytest.raises(fb.FabricationError, match="through|deeper"):
        a_body(
            z=fb.ZExtent(bottom_mm=0.0, top_mm=0.8),
            pockets=(
                fb.Pocket(for_region="K", footprint=tuple(HOSTED_HOLE), depth_mm=0.8),
            ),
        )


def test_a_pocket_exactly_as_deep_as_the_body_leaves_no_floor_and_is_refused():
    with pytest.raises(fb.FabricationError):
        a_body(
            z=fb.ZExtent(bottom_mm=0.0, top_mm=0.4),
            pockets=(
                fb.Pocket(for_region="K", footprint=tuple(HOSTED_HOLE), depth_mm=0.4),
            ),
        )


def test_a_body_must_have_positive_thickness():
    with pytest.raises(fb.FabricationError, match="above"):
        fb.ZExtent(bottom_mm=1.0, top_mm=1.0)
    with pytest.raises(fb.FabricationError, match="above"):
        fb.ZExtent(bottom_mm=1.0, top_mm=0.5)


def test_a_footprint_needs_a_real_outer_ring():
    with pytest.raises(fb.FabricationError, match="three"):
        fb.BodyFootprint(outer=((0.0, 0.0), (1.0, 1.0)))


def test_two_bodies_cannot_realise_the_same_region():
    with pytest.raises(fb.FabricationError, match="more than one body"):
        fb.FabricationBodies(bodies=(a_body(), a_body()))


def test_rings_must_be_immutable_tuples():
    with pytest.raises(fb.FabricationError, match="tuple"):
        fb.BodyFootprint(outer=sq(0.0, 0.0, 5.0))  # a list


# --- immutability ------------------------------------------------------------


def test_the_fabrication_types_are_frozen():
    body = a_body()
    for obj, attr, value in (
        (body, "region_id", "X"),
        (body.footprint, "outer", ()),
        (body.z, "top_mm", 9.0),
        (body.pockets[0], "depth_mm", 9.0),
    ):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, attr, value)


def test_body_collections_cannot_be_appended_to():
    bodies = fb.FabricationBodies(bodies=(a_body(),))
    with pytest.raises(AttributeError):
        bodies.bodies.append(a_body(region_id="Z"))  # type: ignore[attr-defined]


# --- role boundaries ---------------------------------------------------------


def test_nothing_is_written_back_into_canonical():
    art = both_kinds()
    reference = both_kinds()
    fb.solidified_footprint(art, "P")
    assert art == reference


def test_canonical_gained_no_fabrication_state():
    art = both_kinds()
    for name in dir(art):
        for word in ("pocket", "void", "body", "fabricat"):
            assert word not in name.lower(), name


def test_the_canonical_polygon_layer_still_has_no_offset():
    """#8 must not weaken the boundary #6 established."""
    assert not hasattr(poly, "offset")
    assert not any("offset" in n.lower() for n in dir(poly))


def test_fabrication_needed_no_offset_for_this_ticket():
    """Separating hosted holes from voids is boolean difference, not offset.

    Checks for an actual call, not the word: the module docstring says offset is
    deliberately unused, and a plain text search would trip over that.
    """
    tree = ast.parse(Path(fb.__file__).read_text(encoding="utf-8"))
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                called.add(func.attr)
            elif isinstance(func, ast.Name):
                called.add(func.id)
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert "spike" not in node.module
    assert not any("offset" in name.lower() for name in called), called


def test_canonical_does_not_import_fabrication():
    root = Path(CanonicalArtwork.__module__.replace(".", "/")).parent
    import layercake.canonical

    root = Path(layercake.canonical.__file__).parent
    offenders: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "fabrication" in node.module:
                    offenders.add(node.module)
    assert offenders == set(), offenders
