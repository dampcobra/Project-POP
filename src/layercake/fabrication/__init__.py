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
    "Parameter",
    "ProfileError",
    "Provenance",
    "ProvenanceError",
]
