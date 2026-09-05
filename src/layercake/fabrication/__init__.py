"""Fabrication: turning canonical artwork into manufacturable bodies."""

from .body import (
    BodyFootprint,
    FabricationBodies,
    FabricationBody,
    FabricationError,
    Pocket,
    ZExtent,
    solidified_footprint,
)
from .strategy import SUPPORTED_CHILD, SupportedChildStrategy
from .derive import Finding, FabricationResult, derive, inspect_derived_geometry
from .geometry import ClearanceError, dilate, erode, offset_rings
from .profile import (
    FabricationProfile,
    Parameter,
    ProfileError,
    Provenance,
    ProvenanceError,
)

__all__ = [
    "BodyFootprint",
    "FabricationBodies",
    "FabricationBody",
    "FabricationError",
    "FabricationProfile",
    "Pocket",
    "ZExtent",
    "solidified_footprint",
    "ClearanceError",
    "FabricationResult",
    "Finding",
    "SUPPORTED_CHILD",
    "SupportedChildStrategy",
    "derive",
    "dilate",
    "erode",
    "inspect_derived_geometry",
    "offset_rings",
    "Parameter",
    "ProfileError",
    "Provenance",
    "ProvenanceError",
]
