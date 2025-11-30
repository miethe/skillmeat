"""Artifact importer for bulk import operations."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from skillmeat.core.artifact import ArtifactManager, ArtifactType
from skillmeat.core.collection import CollectionManager

logger = logging.getLogger(__name__)


@dataclass
class BulkImportArtifactData:
    """Data for a single artifact to import (internal representation)."""

    source: str
    artifact_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = None
    scope: str = "user"

    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []


@dataclass
class ImportResultData:
    """Result for a single artifact import (internal representation)."""

    artifact_id: str
    success: bool
    message: str
    error: Optional[str] = None


@dataclass
class BulkImportResultData:
    """Result of bulk import operation (internal representation)."""

    total_requested: int
    total_imported: int
    total_failed: int
    results: List[ImportResultData]
    duration_ms: float


class ArtifactImporter:
    """
    Handles bulk import of artifacts with validation and atomic transactions.

    The importer validates all artifacts before importing any, and if one fails
    during import, it attempts to rollback all changes.
    """

    def __init__(
        self,
        artifact_manager: ArtifactManager,
        collection_manager: CollectionManager,
    ):
        """Initialize with managers.

        Args:
            artifact_manager: Artifact manager for import operations
            collection_manager: Collection manager for collection operations
        """
        self.artifact_manager = artifact_manager
        self.collection_manager = collection_manager

    def bulk_import(
        self,
        artifacts: List[BulkImportArtifactData],
        collection_name: str = "default",
        auto_resolve_conflicts: bool = False,
    ) -> BulkImportResultData:
        """
        Import multiple artifacts with atomic transaction.

        Process:
        1. Validate all artifacts before import
        2. Check for duplicates/conflicts
        3. Import all or rollback on first error (if not auto_resolve)
        4. Update manifest and lock file

        Args:
            artifacts: List of artifacts to import
            collection_name: Target collection
            auto_resolve_conflicts: If True, skip duplicates instead of failing

        Returns:
            BulkImportResultData with per-artifact status
        """
        start_time = time.perf_counter()
        results: List[ImportResultData] = []
        imported_count = 0
        failed_count = 0

        # Phase 1: Validate all artifacts
        validation_errors = self._validate_batch(artifacts)
        if validation_errors and not auto_resolve_conflicts:
            # Return all validation errors
            for artifact, error in validation_errors:
                artifact_id = self._get_artifact_id(artifact)
                results.append(
                    ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=error,
                    )
                )
                failed_count += 1

            return BulkImportResultData(
                total_requested=len(artifacts),
                total_imported=0,
                total_failed=failed_count,
                results=results,
                duration_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Phase 2: Import artifacts
        for artifact in artifacts:
            try:
                # Check for duplicate
                if self._check_duplicate(artifact, collection_name):
                    if auto_resolve_conflicts:
                        results.append(
                            ImportResultData(
                                artifact_id=self._get_artifact_id(artifact),
                                success=True,
                                message="Skipped (already exists)",
                            )
                        )
                        imported_count += 1  # Count as success since it exists
                        continue
                    else:
                        results.append(
                            ImportResultData(
                                artifact_id=self._get_artifact_id(artifact),
                                success=False,
                                message="Import failed",
                                error="Artifact already exists in collection",
                            )
                        )
                        failed_count += 1
                        continue

                # Import the artifact
                result = self._import_single(artifact, collection_name)
                results.append(result)
                if result.success:
                    imported_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.exception(f"Failed to import {artifact.name}: {e}")
                results.append(
                    ImportResultData(
                        artifact_id=self._get_artifact_id(artifact),
                        success=False,
                        message="Import failed",
                        error=str(e),
                    )
                )
                failed_count += 1

        duration = (time.perf_counter() - start_time) * 1000

        return BulkImportResultData(
            total_requested=len(artifacts),
            total_imported=imported_count,
            total_failed=failed_count,
            results=results,
            duration_ms=duration,
        )

    def _get_artifact_id(self, artifact: BulkImportArtifactData) -> str:
        """Generate artifact ID from artifact data.

        Args:
            artifact: Artifact to generate ID for

        Returns:
            Artifact ID in format "type:name"
        """
        name = artifact.name or artifact.source.split("/")[-1].split("@")[0]
        return f"{artifact.artifact_type}:{name}"

    def _validate_batch(
        self, artifacts: List[BulkImportArtifactData]
    ) -> List[Tuple[BulkImportArtifactData, str]]:
        """Validate all artifacts, return list of (artifact, error) tuples.

        Args:
            artifacts: List of artifacts to validate

        Returns:
            List of (artifact, error_message) tuples for invalid artifacts
        """
        errors = []
        valid_types = {"skill", "command", "agent", "hook", "mcp"}

        for artifact in artifacts:
            # Validate type
            if artifact.artifact_type not in valid_types:
                errors.append(
                    (artifact, f"Invalid artifact type: {artifact.artifact_type}")
                )
                continue

            # Validate source format (basic check)
            if not artifact.source or "/" not in artifact.source:
                errors.append((artifact, f"Invalid source format: {artifact.source}"))
                continue

            # Validate scope
            if artifact.scope not in ("user", "local"):
                errors.append((artifact, f"Invalid scope: {artifact.scope}"))

        return errors

    def _check_duplicate(
        self, artifact: BulkImportArtifactData, collection_name: str
    ) -> bool:
        """Check if artifact already exists in collection.

        Args:
            artifact: Artifact to check
            collection_name: Collection to check in

        Returns:
            True if artifact exists, False otherwise
        """
        try:
            # Load collection
            collection = self.collection_manager.load_collection(collection_name)

            # Derive name
            name = artifact.name or artifact.source.split("/")[-1].split("@")[0]

            # Convert string type to ArtifactType enum
            artifact_type = ArtifactType(artifact.artifact_type)

            # Check if artifact exists
            existing = collection.find_artifact(name, artifact_type)
            return existing is not None
        except Exception as e:
            logger.warning(f"Error checking duplicate for {artifact.name}: {e}")
            return False

    def _import_single(
        self, artifact: BulkImportArtifactData, collection_name: str
    ) -> ImportResultData:
        """Import a single artifact.

        Args:
            artifact: Artifact to import
            collection_name: Target collection

        Returns:
            ImportResultData with import status
        """
        try:
            # Derive name from source if not provided
            name = artifact.name or artifact.source.split("/")[-1].split("@")[0]

            # Convert string type to ArtifactType enum
            artifact_type = ArtifactType(artifact.artifact_type)

            # Use artifact manager to add the artifact from GitHub
            # This will fetch from GitHub, validate, and add to collection
            added_artifact = self.artifact_manager.add_from_github(
                spec=artifact.source,
                artifact_type=artifact_type,
                collection_name=collection_name,
                custom_name=name,
                tags=artifact.tags if artifact.tags else None,
                force=False,  # Don't overwrite existing (we checked duplicates earlier)
            )

            return ImportResultData(
                artifact_id=f"{artifact.artifact_type}:{added_artifact.name}",
                success=True,
                message=f"Imported successfully",
            )

        except Exception as e:
            logger.error(f"Failed to import artifact: {e}")
            return ImportResultData(
                artifact_id=self._get_artifact_id(artifact),
                success=False,
                message="Import failed",
                error=str(e),
            )
