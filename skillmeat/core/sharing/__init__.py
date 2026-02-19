"""Team sharing functionality for SkillMeat bundles.

This module provides bundle creation, validation, and distribution
functionality for sharing SkillMeat artifacts across teams.
"""

# Bundle creation and inspection
from skillmeat.core.sharing.bundle import (
    Bundle,
    BundleArtifact,
    BundleMetadata,
    CompositeBundleError,
    export_composite_bundle,
)
from skillmeat.core.sharing.builder import (
    BundleBuilder,
    BundleValidationError,
    inspect_bundle,
)
from skillmeat.core.sharing.manifest import (
    BundleManifest,
    ManifestValidator,
    ValidationResult,
    ValidationError,
)
from skillmeat.core.sharing.hasher import BundleHasher, FileHasher

__all__ = [
    # Bundle models
    "Bundle",
    "BundleArtifact",
    "BundleMetadata",
    # Composite bundle export
    "CompositeBundleError",
    "export_composite_bundle",
    # Bundle builder
    "BundleBuilder",
    "BundleValidationError",
    "inspect_bundle",
    # Manifest
    "BundleManifest",
    "ManifestValidator",
    "ValidationResult",
    "ValidationError",
    # Hashing
    "BundleHasher",
    "FileHasher",
]
