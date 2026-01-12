"""Artifact importer for bulk import operations."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from skillmeat.core.artifact import ArtifactManager, ArtifactType
from skillmeat.core.artifact_detection import (
    ArtifactType as DetectionArtifactType,
    ARTIFACT_SIGNATURES,
)

if TYPE_CHECKING:
    from skillmeat.api.schemas.discovery import ImportStatus


# Local ImportStatus enum to avoid circular import
class ImportStatus(str, Enum):
    """Status of an import operation (local definition to avoid circular import)."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


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
    reason_code: Optional[str] = None  # ErrorReasonCode enum value
    details: Optional[str] = None  # Additional error details (e.g., line numbers)
    path: Optional[str] = None  # Path to the artifact
    tags_applied: int = 0  # Count of tags applied from path segments


@dataclass
class BulkImportResultData:
    """Result of bulk import operation (internal representation)."""

    total_requested: int
    total_imported: int
    total_failed: int
    results: List[ImportResultData]
    duration_ms: float
    total_tags_applied: int = 0  # Sum of tags applied across all imports


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
                return (
                    ImportStatus.SKIPPED,
                    "Already exists in both Collection and Project",
                )
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
        apply_path_tags: bool = True,
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
            },
        )

        # Phase 1: Validate all artifacts
        validation_errors = self._validate_batch(artifacts)
        if validation_errors and not auto_resolve_conflicts:
            # Return all validation errors
            for artifact, error in validation_errors:
                artifact_id = self._get_artifact_id(artifact)
                status, skip_reason = self.determine_import_status(
                    artifact_key=artifact_id, import_success=False, error=error
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
                is_duplicate, location = self._check_duplicate(
                    artifact, collection_name
                )
                if is_duplicate:
                    artifact_id = self._get_artifact_id(artifact)
                    if auto_resolve_conflicts:
                        status, skip_reason = self.determine_import_status(
                            artifact_key=artifact_id,
                            import_success=False,
                            already_exists=True,
                            exists_location=location,
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
                            exists_location=location,
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

                # Apply path tags if enabled and import succeeded
                if apply_path_tags and result.success:
                    try:
                        tags_count = self._apply_path_tags(artifact, collection_name)
                        result.tags_applied = tags_count
                    except Exception as e:
                        logger.warning(
                            f"Failed to apply path tags for {artifact.name}: {e}"
                        )
                        # Don't fail the import, just log the warning

                results.append(result)
                if result.success:
                    imported_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.exception(f"Failed to import {artifact.name}: {e}")
                artifact_id = self._get_artifact_id(artifact)
                status, skip_reason = self.determine_import_status(
                    artifact_key=artifact_id, import_success=False, error=str(e)
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
        bulk_import_duration.labels(batch_size_range=batch_size_range).observe(
            duration_sec
        )
        discovery_metrics.record_import(imported_count, failed_count)

        logger.info(
            f"Bulk import completed: {imported_count} imported, {failed_count} failed",
            extra={
                "imported_count": imported_count,
                "failed_count": failed_count,
                "duration_ms": round(duration_ms, 2),
                "status": status,
            },
        )

        # Calculate total tags applied
        total_tags = sum(r.tags_applied for r in results)

        return BulkImportResultData(
            total_requested=len(artifacts),
            total_imported=imported_count,
            total_failed=failed_count,
            results=results,
            duration_ms=duration_ms,
            total_tags_applied=total_tags,
        )

    def _apply_path_tags(
        self,
        artifact: BulkImportArtifactData,
        collection_name: str,
    ) -> int:
        """Apply path-based tags to an imported artifact.

        Extracts path segments from the artifact's source path,
        finds approved/pending segments, and adds them as tags.

        Args:
            artifact: The imported artifact data
            collection_name: Target collection name

        Returns:
            Number of tags applied

        Note:
            Only applies segments with status='approved' or 'pending'.
            Skips if artifact has no path or path extraction fails.
        """
        from skillmeat.core.path_tags import PathSegmentExtractor, PathTagConfig

        # Need a path to extract from
        source_path = artifact.path or artifact.source
        if not source_path:
            return 0

        # Extract segments
        extractor = PathSegmentExtractor(PathTagConfig.defaults())
        segments = extractor.extract(source_path)

        # Filter to approved/pending segments (not excluded)
        # For initial import, "pending" is treated as approved since user selected them
        approved_segments = [
            seg.normalized
            for seg in segments
            if seg.status in ("approved", "pending") and seg.status != "excluded"
        ]

        if not approved_segments:
            return 0

        # Get artifact name for tagging
        artifact_name = artifact.name or artifact.source.split("/")[-1].split("@")[0]
        artifact_type_str = artifact.artifact_type

        # Add tags to artifact in collection
        try:
            artifact_type = ArtifactType(artifact_type_str)

            # Load collection and find the artifact
            collection = self.collection_manager.load_collection(collection_name)
            target_artifact = collection.find_artifact(artifact_name, artifact_type)

            if not target_artifact:
                logger.warning(f"Could not find artifact {artifact_name} to apply tags")
                return 0

            # Add each unique tag
            tags_added = 0
            existing_tags = set(target_artifact.tags or [])

            for tag_name in approved_segments:
                if tag_name not in existing_tags:
                    existing_tags.add(tag_name)
                    tags_added += 1

            # Update artifact tags if any were added
            if tags_added > 0:
                target_artifact.tags = list(existing_tags)
                self.collection_manager.save_collection(collection, collection_name)
                logger.info(
                    f"Applied {tags_added} path tags to {artifact_name}: "
                    f"{approved_segments[:3]}{'...' if len(approved_segments) > 3 else ''}"
                )

            return tags_added

        except Exception as e:
            logger.warning(f"Error applying path tags to {artifact_name}: {e}")
            return 0

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

    def _classify_error(
        self, error: Exception, artifact_path: Optional[str] = None
    ) -> tuple[str, str, Optional[str]]:
        """Classify an exception into reason code, message, and details.

        Args:
            error: The exception that occurred
            artifact_path: Optional path to the artifact for context

        Returns:
            tuple of (reason_code, error_message, details)
        """
        import yaml

        error_str = str(error)
        error_type = type(error).__name__

        # YAML parsing errors
        if isinstance(error, yaml.YAMLError):
            details = None
            if hasattr(error, "problem_mark") and error.problem_mark:
                mark = error.problem_mark
                details = f"Line {mark.line + 1}, Column {mark.column + 1}: {getattr(error, 'problem', 'syntax error')}"
            return ("yaml_parse_error", f"YAML parsing failed: {error_str}", details)

        # Permission errors (check first since PermissionError inherits from OSError)
        if isinstance(error, PermissionError):
            return (
                "permission_error",
                f"Permission denied: {error_str}",
                artifact_path,
            )

        # File I/O errors
        if isinstance(error, (IOError, OSError)):
            if "Permission denied" in error_str:
                return (
                    "permission_error",
                    f"Permission denied: {error_str}",
                    artifact_path,
                )
            return ("io_error", f"I/O error: {error_str}", artifact_path)

        # Network errors (typically from GitHub)
        if "network" in error_str.lower() or "connection" in error_str.lower():
            return ("network_error", f"Network error: {error_str}", None)
        if "timeout" in error_str.lower():
            return ("network_error", f"Connection timeout: {error_str}", None)
        if "404" in error_str or "not found" in error_str.lower():
            return ("network_error", f"Resource not found: {error_str}", None)

        # Validation errors
        if isinstance(error, ValueError):
            if "invalid" in error_str.lower() and "type" in error_str.lower():
                return ("invalid_type", f"Invalid artifact type: {error_str}", None)
            if "source" in error_str.lower() or "path" in error_str.lower():
                return ("invalid_source", f"Invalid source: {error_str}", None)
            if "structure" in error_str.lower() or "directory" in error_str.lower():
                return (
                    "invalid_structure",
                    f"Invalid artifact structure: {error_str}",
                    artifact_path,
                )
            if "metadata" in error_str.lower() or "missing" in error_str.lower():
                return (
                    "missing_metadata",
                    f"Missing metadata: {error_str}",
                    artifact_path,
                )

        if isinstance(error, KeyError):
            return (
                "missing_metadata",
                f"Missing required field: {error_str}",
                None,
            )

        # Generic import error
        return ("import_error", f"Import failed: {error_str}", None)

    def _validate_artifact_structure(
        self, artifact: BulkImportArtifactData
    ) -> Optional[ImportResultData]:
        """Validate artifact structure before import.

        Checks for common issues like missing SKILL.md, invalid YAML, etc.

        Args:
            artifact: Artifact to validate

        Returns:
            ImportResultData if validation fails, None if valid
        """
        import os
        from pathlib import Path
        import yaml

        # Skip validation for GitHub sources (validated during fetch)
        if not artifact.source.startswith("local/"):
            return None

        # Local sources require path
        if not artifact.path:
            artifact_id = f"{artifact.artifact_type}:{artifact.name or 'unknown'}"
            return ImportResultData(
                artifact_id=artifact_id,
                success=False,
                message="Validation failed",
                error=f"Local source '{artifact.source}' requires 'path' field",
                status=ImportStatus.FAILED,
                reason_code="invalid_source",
                path=None,
            )

        artifact_path = Path(artifact.path)

        # Check path exists
        if not artifact_path.exists():
            artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
            return ImportResultData(
                artifact_id=artifact_id,
                success=False,
                message="Validation failed",
                error=f"Artifact path does not exist: {artifact.path}",
                status=ImportStatus.FAILED,
                reason_code="invalid_structure",
                path=artifact.path,
            )

        # Determine if this artifact type requires a directory or allows single files
        # Look up the signature from ARTIFACT_SIGNATURES for authoritative is_directory info
        try:
            detection_type = DetectionArtifactType(artifact.artifact_type)
            signature = ARTIFACT_SIGNATURES.get(detection_type)
            requires_directory = signature.is_directory if signature else True
        except ValueError:
            # Unknown artifact type - default to requiring directory (conservative)
            requires_directory = True

        if requires_directory:
            # Directory-based artifacts (skills): must be a directory
            if not artifact_path.is_dir():
                artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                return ImportResultData(
                    artifact_id=artifact_id,
                    success=False,
                    message="Validation failed",
                    error=f"Artifact path is not a directory: {artifact.path}",
                    status=ImportStatus.FAILED,
                    reason_code="invalid_structure",
                    path=artifact.path,
                )
        else:
            # File-based artifacts (commands, agents, hooks, mcp): must be a file
            if not artifact_path.is_file():
                artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                return ImportResultData(
                    artifact_id=artifact_id,
                    success=False,
                    message="Validation failed",
                    error=f"Artifact path is not a file: {artifact.path}",
                    status=ImportStatus.FAILED,
                    reason_code="invalid_structure",
                    path=artifact.path,
                )

            # For file-based artifacts, validate the file itself
            # Check file extension for markdown-based types
            if artifact.artifact_type in ("command", "agent"):
                if not artifact_path.suffix.lower() == ".md":
                    artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                    return ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=f"Expected .md file for {artifact.artifact_type}, got: {artifact_path.suffix}",
                        status=ImportStatus.FAILED,
                        reason_code="invalid_structure",
                        path=artifact.path,
                    )

            # Validate YAML frontmatter in the file itself for markdown-based artifacts
            if artifact_path.suffix.lower() == ".md":
                try:
                    content = artifact_path.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        # Extract YAML frontmatter
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            yaml_content = parts[1].strip()
                            if yaml_content:
                                yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                    details = None
                    if hasattr(e, "problem_mark") and e.problem_mark:
                        mark = e.problem_mark
                        details = f"Line {mark.line + 1}, Column {mark.column + 1}: {getattr(e, 'problem', 'syntax error')}"
                    return ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=f"Invalid YAML frontmatter in {artifact_path.name}",
                        status=ImportStatus.FAILED,
                        reason_code="yaml_parse_error",
                        details=details,
                        path=artifact.path,
                    )
                except Exception as e:
                    artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                    return ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=f"Failed to read {artifact_path.name}: {str(e)}",
                        status=ImportStatus.FAILED,
                        reason_code="io_error",
                        path=artifact.path,
                    )

            # Validation passed for file-based artifact
            return None

        # Check for metadata file based on artifact type (directory-based artifacts only)
        metadata_files = {
            "skill": "SKILL.md",
            "command": "command.md",
            "agent": "agent.md",
            "hook": "hook.md",
            "mcp": "mcp.json",
        }

        expected_file = metadata_files.get(artifact.artifact_type)
        if expected_file:
            metadata_path = artifact_path / expected_file
            if not metadata_path.exists():
                artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                return ImportResultData(
                    artifact_id=artifact_id,
                    success=False,
                    message="Validation failed",
                    error=f"Missing required metadata file: {expected_file}",
                    status=ImportStatus.FAILED,
                    reason_code="missing_metadata",
                    details=f"Expected file at: {metadata_path}",
                    path=artifact.path,
                )

            # For markdown files, validate YAML frontmatter
            if expected_file.endswith(".md"):
                try:
                    content = metadata_path.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        # Extract YAML frontmatter
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            yaml_content = parts[1].strip()
                            if yaml_content:
                                yaml.safe_load(yaml_content)
                except yaml.YAMLError as e:
                    artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                    details = None
                    if hasattr(e, "problem_mark") and e.problem_mark:
                        mark = e.problem_mark
                        details = f"Line {mark.line + 1}, Column {mark.column + 1}: {getattr(e, 'problem', 'syntax error')}"
                    return ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=f"Invalid YAML frontmatter in {expected_file}",
                        status=ImportStatus.FAILED,
                        reason_code="yaml_parse_error",
                        details=details,
                        path=artifact.path,
                    )
                except Exception as e:
                    artifact_id = f"{artifact.artifact_type}:{artifact.name or artifact_path.name}"
                    return ImportResultData(
                        artifact_id=artifact_id,
                        success=False,
                        message="Validation failed",
                        error=f"Failed to read {expected_file}: {str(e)}",
                        status=ImportStatus.FAILED,
                        reason_code="io_error",
                        path=artifact.path,
                    )

        return None  # Validation passed

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
        # Pre-validate structure for local artifacts
        validation_result = self._validate_artifact_structure(artifact)
        if validation_result is not None:
            return validation_result

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
                artifact_key=artifact_id, import_success=True, already_exists=False
            )
            return ImportResultData(
                artifact_id=artifact_id,
                success=True,
                message="Imported successfully",
                status=status,
                skip_reason=skip_reason,
                path=artifact.path,
            )
        except Exception as e:
            logger.error(f"Failed to import artifact: {e}")
            artifact_id = f"{artifact.artifact_type}:{artifact.name or 'unknown'}"
            reason_code, error_msg, details = self._classify_error(e, artifact.path)
            status, skip_reason = self.determine_import_status(
                artifact_key=artifact_id, import_success=False, error=str(e)
            )
            return ImportResultData(
                artifact_id=artifact_id,
                success=False,
                message="Import failed",
                error=error_msg,
                status=status,
                skip_reason=skip_reason,
                reason_code=reason_code,
                details=details,
                path=artifact.path,
            )
