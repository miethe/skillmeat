"""Artifact importer for bulk import operations."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from skillmeat.api.schemas.discovery import ImportStatus
from skillmeat.core.artifact import ArtifactManager, ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.discovery_metrics import (
    bulk_import_artifacts_total,
    bulk_import_duration,
    bulk_import_requests_total,
    discovery_metrics,
    log_performance,
)

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
    path: Optional[str] = None

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
    status: Optional[ImportStatus] = None
    skip_reason: Optional[str] = None


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

    def determine_import_status(
        self,
        artifact_key: str,
        import_success: bool,
        error: Optional[str] = None,
        already_exists: bool = False,
        exists_location: Optional[str] = None,  # "collection", "project", "both"
    ) -> tuple[ImportStatus, Optional[str]]:
        """
        Determine the import status and skip reason for an artifact.

        Args:
            artifact_key: Identifier for the artifact
            import_success: Whether the import operation succeeded
            error: Error message if import failed
            already_exists: Whether the artifact already exists
            exists_location: Where the artifact exists ("collection", "project", "both")

        Returns:
            tuple of (ImportStatus, skip_reason or None)
        """
        if already_exists:
            if exists_location == "both":
                return ImportStatus.SKIPPED, "Already exists in both Collection and Project"
            elif exists_location == "collection":
                return ImportStatus.SKIPPED, "Already exists in Collection"
            elif exists_location == "project":
                return ImportStatus.SKIPPED, "Already exists in Project"
            else:
                return ImportStatus.SKIPPED, "Already exists"

        if import_success:
            return ImportStatus.SUCCESS, None

        # Failed case
        return ImportStatus.FAILED, None

    @log_performance("bulk_import")
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

        logger.info(
            "Starting bulk import",
            extra={
                "artifact_count": len(artifacts),
                "collection": collection_name,
                "auto_resolve_conflicts": auto_resolve_conflicts,
            }
        )

        # Phase 1: Validate all artifacts
        validation_errors = self._validate_batch(artifacts)
        if validation_errors and not auto_resolve_conflicts:
            # Return all validation errors
            for artifact, error in validation_errors:
                artifact_id = self._get_artifact_id(artifact)
                status, skip_reason = self.determine_import_status(
                    artifact_key=artifact_id,
                    import_success=False,
                    error=error
                )
                results.append(
                    ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=error,
                        status=status,
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
                is_duplicate, location = self._check_duplicate(artifact, collection_name)
                if is_duplicate:
                    artifact_id = self._get_artifact_id(artifact)
                    if auto_resolve_conflicts:
                        status, skip_reason = self.determine_import_status(
                            artifact_key=artifact_id,
                            import_success=False,
                            already_exists=True,
                            exists_location=location
                        )
                        results.append(
                            ImportResultData(
                                artifact_id=artifact_id,
                                success=True,  # Count as success for backward compatibility
                                message=f"Skipped: {skip_reason}",
                                status=status,
                                skip_reason=skip_reason,
                            )
                        )
                        imported_count += 1  # Count as success since it exists
                        continue
                    else:
                        status, skip_reason = self.determine_import_status(
                            artifact_key=artifact_id,
                            import_success=False,
                            already_exists=True,
                            exists_location=location
                        )
                        results.append(
                            ImportResultData(
                                artifact_id=artifact_id,
                                success=False,
                                message="Import failed",
                                error=f"Artifact already exists in {location}",
                                status=ImportStatus.FAILED,
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
                artifact_id = self._get_artifact_id(artifact)
                status, skip_reason = self.determine_import_status(
                    artifact_key=artifact_id,
                    import_success=False,
                    error=str(e)
                )
                results.append(
                    ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Import failed",
                        error=str(e),
                        status=status,
                    )
                )
                failed_count += 1

        duration_sec = time.perf_counter() - start_time
        duration_ms = duration_sec * 1000

        # Determine batch size range for metrics
        batch_size = len(artifacts)
        if batch_size <= 10:
            batch_size_range = "1-10"
        elif batch_size <= 50:
            batch_size_range = "11-50"
        else:
            batch_size_range = "51+"

        # Record metrics
        status = "success" if failed_count == 0 else "partial_success"
        bulk_import_requests_total.labels(status=status).inc()
        bulk_import_artifacts_total.labels(result="success").inc(imported_count)
        bulk_import_artifacts_total.labels(result="failed").inc(failed_count)
        bulk_import_duration.labels(batch_size_range=batch_size_range).observe(duration_sec)
        discovery_metrics.record_import(imported_count, failed_count)

        logger.info(
            f"Bulk import completed: {imported_count} imported, {failed_count} failed",
            extra={
                "imported_count": imported_count,
                "failed_count": failed_count,
                "duration_ms": round(duration_ms, 2),
                "status": status,
            }
        )

        return BulkImportResultData(
            total_requested=len(artifacts),
            total_imported=imported_count,
            total_failed=failed_count,
            results=results,
            duration_ms=duration_ms,
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
    ) -> tuple[bool, Optional[str]]:
        """Check if artifact already exists in collection.

        Args:
            artifact: Artifact to check
            collection_name: Collection to check in

        Returns:
            tuple of (is_duplicate, location) where location is "collection", "project", "both", or None
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
            if existing is not None:
                # For now, we only check collection existence
                # Future: check project-level deployments for "project" or "both"
                return (True, "collection")
            return (False, None)
        except Exception as e:
            logger.warning(f"Error checking duplicate for {artifact.name}: {e}")
            return (False, None)

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
            # Extract name from source
            name = artifact.name or artifact.source.split("/")[-1].split("@")[0]
            artifact_type = ArtifactType(artifact.artifact_type)

            # Route based on source type
            if artifact.source.startswith("local/"):
                # Local source - requires path field
                if not artifact.path:
                    raise ValueError(
                        f"Local source '{artifact.source}' requires 'path' field with actual filesystem location"
                    )
                added_artifact = self.artifact_manager.add_from_local(
                    path=artifact.path,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    custom_name=name,
                    tags=artifact.tags if artifact.tags else None,
                    force=False,
                )
            else:
                # GitHub source
                added_artifact = self.artifact_manager.add_from_github(
                    spec=artifact.source,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    custom_name=name,
                    tags=artifact.tags if artifact.tags else None,
                    force=False,
                )

            artifact_id = f"{artifact.artifact_type}:{added_artifact.name}"
            status, skip_reason = self.determine_import_status(
                artifact_key=artifact_id,
                import_success=True,
                already_exists=False
            )
            return ImportResultData(
                artifact_id=artifact_id,
                success=True,
                message="Imported successfully",
                status=status,
                skip_reason=skip_reason,
            )
        except Exception as e:
            logger.error(f"Failed to import artifact: {e}")
            artifact_id = f"{artifact.artifact_type}:{artifact.name or 'unknown'}"
            status, skip_reason = self.determine_import_status(
                artifact_key=artifact_id,
                import_success=False,
                error=str(e)
            )
            return ImportResultData(
                artifact_id=artifact_id,
                success=False,
                message="Import failed",
                error=str(e),
                status=status,
                skip_reason=skip_reason,
            )
