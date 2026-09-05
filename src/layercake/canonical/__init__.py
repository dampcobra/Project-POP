"""Canonical artwork: what the piece is, independent of how it is made."""

from .artwork import (
    ArtworkError,
    ArtworkValidation,
    CanonicalArtwork,
    DEFAULT_TOLERANCE,
    Edge,
    Region,
    RegionSpec,
)
from .stacking import (
    StackingError,
    StackingLevel,
    StackingOrder,
    derive_stacking_order,
)

__all__ = [
    "ArtworkError",
    "ArtworkValidation",
    "CanonicalArtwork",
    "DEFAULT_TOLERANCE",
    "Edge",
    "Region",
    "RegionSpec",
    "StackingError",
    "StackingLevel",
    "StackingOrder",
    "derive_stacking_order",
]
