"""Where each stacking level sits vertically.

The arithmetic is small but easy to get wrong in a way that looks plausible, so
every step is a named quantity rather than an expression at a call site.

Three rules, each independent of the others -- which is the point, and was the
substance of the Session 01 backing decoupling:

- the **visible step** between one completed level and the next is `H`;
- the **backing thickness** is its own structural property, *not* `H`;
- the **seating depth** a child sinks into its support is its own value, *not*
  the visible step height.

From those::

    top of level n     = backing + n * H          (levels above 0 step by H)
    bottom of level n  = top - H - seating depth  (it sinks into its support)
    top of level 0     = backing thickness        (it sits on the plate)

A level's placement therefore depends only on the level. Two regions at the same
stacking level get identical Z whoever their parents are, so sibling peer order
-- which exists only for reproducibility -- can never become a physical
difference.
"""

from __future__ import annotations

from .body import FabricationError, ZExtent
from .profile import FabricationProfile


def level_top_mm(level: int, profile: FabricationProfile) -> float:
    """The finished top surface of a completed stacking level.

    Level 0 finishes at the backing thickness; every level above adds one
    visible step.
    """
    if level < 0:
        raise FabricationError(f"stacking level must be non-negative, got {level}")
    return profile.backing_thickness.mm + level * profile.visible_step_height.mm


def body_z_extent(level: int, profile: FabricationProfile) -> ZExtent:
    """The vertical extent of a body at a given stacking level.

    Level 0 is the backing: it sits on the plate and spans its own thickness.
    Above that, a body is `H + seating depth` thick -- it shows `H` and sinks the
    rest into the level below, so its top lands exactly one visible step higher.
    """
    top = level_top_mm(level, profile)
    if level == 0:
        return ZExtent(bottom_mm=0.0, top_mm=top)
    thickness = profile.visible_step_height.mm + profile.seating_depth.mm
    return ZExtent(bottom_mm=top - thickness, top_mm=top)


def floor_beneath_pocket_mm(level: int, profile: FabricationProfile) -> float:
    """Material left under a pocket cut into a body at `level`."""
    return body_z_extent(level, profile).thickness_mm - profile.seating_depth.mm


def check_floor_is_sound(
    level: int, region_id: str, profile: FabricationProfile
) -> float:
    """Confirm a body at `level` can host a pocket and still stand up.

    Raises rather than producing geometry with too little -- or no -- material
    under a recess. The minimum is the profile's, which is an engineering choice
    that has never been physically validated (issue #11), not a measured value.
    """
    floor = floor_beneath_pocket_mm(level, profile)
    minimum = profile.minimum_recess_floor.mm

    if floor <= 0:
        raise FabricationError(
            f"region {region_id!r} at level {level} would have {floor:.4g} mm "
            f"beneath its pocket: a {profile.seating_depth.mm} mm recess in a "
            f"{body_z_extent(level, profile).thickness_mm:.4g} mm body is a "
            "through-hole, not a recess. Support must remain continuous."
        )
    if floor < minimum - _FLOOR_TOLERANCE:
        raise FabricationError(
            f"region {region_id!r} at level {level} would leave {floor:.4g} mm "
            f"beneath its pocket, under the profile minimum of {minimum} mm. "
            "Either the backing is too thin for this seating depth, or the "
            "minimum floor is set higher than this profile can satisfy."
        )
    return floor


#: Absorbs binary floating point in the floor comparison: 1.2 - 0.8 is
#: 0.39999999999999991, which must not read as under a 0.4 mm minimum.
_FLOOR_TOLERANCE = 1e-9
