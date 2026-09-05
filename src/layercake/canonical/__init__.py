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

__all__ = [
    "ArtworkError",
    "ArtworkValidation",
    "CanonicalArtwork",
    "DEFAULT_TOLERANCE",
    "Edge",
    "Region",
    "RegionSpec",
]
