"""Artifact discovery service for SkillMeat.

This module provides functionality to scan .claude/ directories and discover
existing artifacts that can be imported into the collection.

Detection Flow:
    1. Container name (directory) → get_artifact_type_from_container() provides type hint
    2. Shared detector → detect_artifact() validates artifact with confidence score
    3. DiscoveredArtifact → metadata extraction and result packaging

Artifact Detection:
    This module uses the unified artifact_detection module (Phase 1) for all
    artifact type detection. The detect_artifact() function provides:
    - Consistent detection logic across the codebase
    - Confidence-based validation (0-100% scale)
    - Heuristic mode for flexible discovery scenarios
    - Support for nested artifacts (commands/agents)

Supported Artifact Types:
    Artifact types are derived from ArtifactType.primary_types() and their
    detection rules are defined in ARTIFACT_SIGNATURES (see artifact_detection.py):
    - Skills: Directory with SKILL.md manifest
    - Commands: Single .md file or directory with COMMAND.md (directory pattern deprecated)
    - Agents: Single .md file or directory with AGENT.md (directory pattern deprecated)
    - Hooks: Directory with HOOK.md manifest
    - MCPs: Directory with MCP.md or mcp.json manifest

Timestamp Tracking:
    Discovery tracks when artifacts are first discovered and when they change:
    - discovered_at: ISO 8601 timestamp when artifact first seen or content changed
    - Timestamps are preserved in collection manifest between discovery runs
    - Changes are detected via content hash comparison with lockfile
    - New/modified artifacts get current timestamp; unchanged preserve original
"""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from skillmeat.core.artifact_detection import (
    ARTIFACT_SIGNATURES,
    ArtifactType,
    DetectionError,
    DetectionResult,
    MANIFEST_FILES,
    detect_artifact,
    extract_manifest_file,
    get_artifact_type_from_container,
)
from skillmeat.core.discovery_metrics import (
    discovery_artifacts_found,
    discovery_errors_total,
    discovery_metrics,
    discovery_scan_duration,
    discovery_scans_total,
    log_performance,
)
from skillmeat.core.skip_preferences import SkipPreferenceManager, build_artifact_key
from skillmeat.utils.metadata import extract_yaml_frontmatter
from skillmeat.utils.filesystem import compute_content_hash

if TYPE_CHECKING:
    from skillmeat.core.collection import Collection

logger = logging.getLogger(__name__)

# Deprecation warning messages for legacy artifact patterns
DEPRECATION_WARNINGS = {
    "directory_command": (
        "DEPRECATED: Directory-based command artifacts will no longer be supported. "
        "Location: {path}. "
        "Recommended: Move to single .md file (e.g., .claude/commands/my-command.md). "
        "Migration guide: docs/migration/deprecated-artifact-patterns.md"
    ),
    "directory_agent": (
        "DEPRECATED: Directory-based agent artifacts will no longer be supported. "
        "Location: {path}. "
        "Recommended: Move to single .md file (e.g., .claude/agents/my-agent.md). "
        "Migration guide: docs/migration/deprecated-artifact-patterns.md"
    ),
}


class DiscoveryRequest(BaseModel):
    """Request model for artifact discovery.

    Attributes:
        scan_path: Optional path to scan. Defaults to collection artifacts directory.
    """

    scan_path: Optional[str] = None


class CollectionStatusInfo(BaseModel):
    """Collection membership status for a discovered artifact.

    Provides detailed information about whether an artifact exists
    in the collection and how it was matched.

    Attributes:
        in_collection: Whether the artifact exists in the collection
        match_type: How the artifact was matched:
            - "exact": Source link exact match
            - "hash": Content hash match
            - "name_type": Name + type match
            - "none": No match found
        matched_artifact_id: ID of matched artifact (format: type:name) or None
    """

    in_collection: bool = False
    match_type: str = "none"  # "exact" | "hash" | "name_type" | "none"
    matched_artifact_id: Optional[str] = None


class CollectionMatchInfo(BaseModel):
    """Hash-based collection matching result for a discovered artifact.

    Provides detailed information about how an artifact matches against
    the collection using content hash and name+type matching.

    Attributes:
        type: Type of match found:
            - "exact": Content hash exact match (confidence: 1.0)
            - "hash": Legacy alias for exact hash match (confidence: 1.0)
            - "name_type": Name and type match but different content (confidence: 0.85)
            - "none": No match found (confidence: 0.0)
        matched_artifact_id: ID of matched artifact if found (format: type:name)
        matched_name: Name of the matched artifact
        confidence: Confidence score (0.0-1.0) indicating match quality
    """

    type: str = "none"  # "exact" | "hash" | "name_type" | "none"
    matched_artifact_id: Optional[str] = None
    matched_name: Optional[str] = None
    confidence: float = 0.0  # 0.0-1.0


class DiscoveredArtifact(BaseModel):
    """Metadata about a discovered artifact.

    Attributes:
        type: Artifact type (skill, command, agent, hook, mcp)
        name: Artifact name
        source: Optional source URL (GitHub, local, etc.)
        version: Optional version string
        scope: Optional scope (user or local)
        tags: Optional list of tags
        description: Optional description
        path: Full path to artifact directory
        discovered_at: Timestamp when artifact was discovered
        skip_reason: Optional reason why artifact is skipped (only set when include_skipped=True)
        collection_status: Collection membership status (populated when collection context provided)
        content_hash: SHA256 content hash of the artifact for deduplication
        collection_match: Hash-based collection matching result with confidence score
    """

    type: str
    name: str
    source: Optional[str] = None
    version: Optional[str] = None
    scope: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None
    path: str
    discovered_at: datetime
    skip_reason: Optional[str] = None
    collection_status: Optional[CollectionStatusInfo] = None
    content_hash: Optional[str] = None
    collection_match: Optional[CollectionMatchInfo] = None


class DiscoveryResult(BaseModel):
    """Result of artifact discovery scan.

    Attributes:
        discovered_count: Total number of artifacts discovered
        importable_count: Number of artifacts not yet imported (filtered by manifest)
        artifacts: List of discovered artifacts (filtered if manifest provided)
        skipped_artifacts: List of artifacts that were skipped (only populated when include_skipped=True)
        errors: List of error messages for artifacts that failed discovery
        scan_duration_ms: Time taken to complete scan in milliseconds
    """

    discovered_count: int
    importable_count: int
    artifacts: List[DiscoveredArtifact]
    skipped_artifacts: List[DiscoveredArtifact] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    scan_duration_ms: float


class ArtifactDiscoveryService:
    """Service for discovering artifacts in .claude/ directories or collection artifacts.

    This service uses the shared artifact_detection module (Phase 1) for consistent
    artifact type detection across the SkillMeat codebase.

    Scan Modes:
        - project mode: Scans .claude/ subdirectories (skills/, commands/, agents/, hooks/, mcp/)
        - collection mode: Scans collection/artifacts/ subdirectories (legacy)
        - auto mode: Detects mode based on directory structure

    Supported Artifact Types:
        Derived from ArtifactType.primary_types() enum:
        - Skills: Directory with SKILL.md manifest
        - Commands: Single .md file or directory with COMMAND.md
        - Agents: Single .md file or directory with AGENT.md
        - Hooks: Directory with HOOK.md manifest
        - MCPs: Directory with MCP.md or mcp.json manifest

    Nested Artifact Discovery:
        For artifact types that support nesting (commands, agents), the service
        recursively traverses subdirectories up to a maximum depth of 3 levels.
        Only types with allowed_nesting=True in ARTIFACT_SIGNATURES support this.

    Detection Strategy:
        Uses detect_artifact() in heuristic mode with 50% confidence threshold
        for flexible discovery of edge cases while maintaining accuracy.

    Performance Target:
        <2 seconds for 50+ artifacts
    """

    supported_types: List[str] = [t.value for t in ArtifactType.primary_types()]

    def __init__(self, base_path: Path, scan_mode: str = "auto"):
        """Initialize the discovery service.

        Args:
            base_path: Base path to scan (project root or collection root)
            scan_mode: Scan mode - "project" (.claude/), "collection" (artifacts/), or "auto" (detect)
        """
        self.base_path = base_path
        self.scan_mode = scan_mode

        # Auto-detect mode based on directory structure
        if scan_mode == "auto":
            if (base_path / ".claude").exists():
                self.scan_mode = "project"
                self.artifacts_base = base_path / ".claude"
            elif (base_path / "artifacts").exists():
                self.scan_mode = "collection"
                self.artifacts_base = base_path / "artifacts"
            else:
                # Default to project mode
                self.scan_mode = "project"
                self.artifacts_base = base_path / ".claude"
        elif scan_mode == "project":
            self.artifacts_base = base_path / ".claude"
        else:  # collection
            self.artifacts_base = base_path / "artifacts"

        # Maintain backward compatibility with collection_path attribute
        self.collection_path = base_path
        self.artifacts_path = self.artifacts_base

    def _get_artifact_timestamp(
        self,
        artifact_path: Path,
        artifact_name: str,
        artifact_type: str,
        manifest: Optional["Collection"] = None,
    ) -> datetime:
        """Get discovery timestamp for artifact.

        Determines if artifact is new, modified, or unchanged by checking:
        1. Content hash against lockfile (if available)
        2. Existing timestamp in manifest (if artifact unchanged)

        Args:
            artifact_path: Path to artifact directory or file
            artifact_name: Artifact name
            artifact_type: Artifact type
            manifest: Optional Collection manifest for timestamp lookup

        Returns:
            ISO 8601 timestamp - current if new/modified, preserved if unchanged
        """
        now = datetime.now(timezone.utc)

        # Compute current content hash
        try:
            current_hash = compute_content_hash(artifact_path)
        except Exception as e:
            logger.debug(f"Failed to compute hash for {artifact_path}: {e}")
            # If we can't compute hash, treat as new
            return now

        # Check lockfile for existing hash
        try:
            from skillmeat.storage.lockfile import LockManager

            lock_mgr = LockManager()
            lock_entries = lock_mgr.read(self.base_path)
            lock_key = (artifact_name, artifact_type)

            if lock_key in lock_entries:
                lock_entry = lock_entries[lock_key]
                if lock_entry.content_hash == current_hash:
                    # Unchanged: Preserve existing timestamp from manifest
                    if manifest:
                        try:
                            existing = manifest.find_artifact(
                                artifact_name, ArtifactType(artifact_type)
                            )
                            if existing and hasattr(existing, "discovered_at"):
                                logger.debug(
                                    f"Artifact {artifact_name} unchanged, preserving timestamp"
                                )
                                return existing.discovered_at
                        except (ValueError, AttributeError) as e:
                            logger.debug(
                                f"Could not find existing timestamp for {artifact_name}: {e}"
                            )
                else:
                    # Modified: Use current timestamp
                    logger.debug(
                        f"Artifact {artifact_name} modified (hash changed), updating timestamp"
                    )
                    return now
        except Exception as e:
            logger.debug(f"Error checking lockfile for {artifact_name}: {e}")

        # New artifact or no lockfile: Use current timestamp
        return now

    @log_performance("discovery_scan")
    def discover_artifacts(
        self,
        manifest: Optional["Collection"] = None,
        project_path: Optional[Path] = None,
        include_skipped: bool = False,
        collection_name: Optional[str] = None,
        include_collection_status: bool = True,
    ) -> DiscoveryResult:
        """Scan artifacts directory and discover all artifacts.

        This method recursively scans the artifacts directory, detects
        artifact types, extracts metadata, validates structure, and optionally
        checks collection membership status for each artifact.

        Errors during individual artifact processing are collected but
        do not fail the entire scan.

        Args:
            manifest: Optional Collection manifest to filter already-imported artifacts.
                     If provided, only artifacts not in manifest.artifacts are returned.
            project_path: Optional path to the project root for skip preference filtering.
                         If provided, artifacts in the skip list will be filtered out.
            include_skipped: If True and project_path is provided, include skipped artifacts
                            in a separate list with their skip reasons. Default: False.
            collection_name: Optional collection name for membership checking.
                            If provided (or defaulted to active), each artifact's
                            collection_status will be populated.
            include_collection_status: Whether to populate collection_status for each
                            artifact. Default: True. Set to False for faster scans
                            when collection membership is not needed.

        Returns:
            DiscoveryResult with discovered artifacts, error list, and metrics.
            The `discovered_count` field shows total artifacts found.
            The `importable_count` field shows artifacts not yet imported (filtered).
            The `artifacts` list contains only importable artifacts if manifest provided.
            The `skipped_artifacts` list contains skipped artifacts if include_skipped=True.
            Each artifact's `collection_status` field will be populated if
            include_collection_status=True.
        """
        start_time = time.time()
        discovered_artifacts: List[DiscoveredArtifact] = []
        errors: List[str] = []

        # Initialize collection membership index for efficient batch checking
        collection_membership_index = None
        if include_collection_status:
            try:
                from skillmeat.core.collection import CollectionManager

                collection_mgr = CollectionManager()
                collection_membership_index = collection_mgr.get_collection_membership_index(
                    collection_name
                )
                logger.debug(
                    f"Loaded collection membership index: "
                    f"{len(collection_membership_index.get('by_source', {}))} sources, "
                    f"{len(collection_membership_index.get('by_hash', {}))} hashes, "
                    f"{len(collection_membership_index.get('by_name_type', {}))} name+type entries"
                )
            except Exception as e:
                logger.warning(f"Could not load collection membership index: {e}")
                # Continue without membership checking

        logger.info(
            "Starting artifact discovery",
            extra={
                "path": str(self.base_path),
                "scan_mode": self.scan_mode,
                "artifacts_base": str(self.artifacts_base),
            },
        )

        # Validate artifacts directory exists
        if not self.artifacts_base.exists():
            error_msg = (
                f"Artifacts directory not found: {self.artifacts_base} "
                f"(scan_mode={self.scan_mode})"
            )
            logger.warning(error_msg)
            errors.append(error_msg)
            discovery_scans_total.labels(status="no_artifacts_dir").inc()

            return DiscoveryResult(
                discovered_count=0,
                importable_count=0,
                artifacts=[],
                skipped_artifacts=[],
                errors=errors,
                scan_duration_ms=(time.time() - start_time) * 1000,
            )

        # Scan each artifact type directory
        try:
            for type_dir in self.artifacts_base.iterdir():
                if not type_dir.is_dir():
                    continue

                # Determine artifact type from directory name
                artifact_type = self._normalize_type_from_dirname(type_dir.name)
                if artifact_type not in self.supported_types:
                    logger.debug(f"Skipping unsupported directory: {type_dir.name}")
                    continue

                # Scan artifacts in this type directory
                try:
                    type_artifacts = self._scan_type_directory(
                        type_dir, artifact_type, errors, manifest,
                        collection_membership_index
                    )
                    discovered_artifacts.extend(type_artifacts)
                except PermissionError as e:
                    error_msg = f"Permission denied accessing {type_dir}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error scanning {type_dir}: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

        except PermissionError as e:
            error_msg = f"Permission denied accessing artifacts directory: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error during artifact discovery: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

        # Filter artifacts based on existence check
        # Strategy: Use pre-scan check to filter out artifacts already in both locations
        # Fall back to legacy manifest-based filtering if manifest provided
        importable_artifacts = []
        filtered_count = 0

        for artifact in discovered_artifacts:
            artifact_key = f"{artifact.type}:{artifact.name}"

            # Use the new check_artifact_exists for comprehensive filtering
            existence = self.check_artifact_exists(artifact_key, manifest)

            # Filter logic:
            # - If in both Collection and Project: exclude (fully installed)
            # - If in Collection only: include (user might want to deploy to Project)
            # - If in Project only: include (user might want to add to Collection)
            # - If in neither: include (new artifact)
            should_include = existence["location"] != "both"

            # Legacy compatibility: If manifest provided and artifact in collection,
            # consider it as potentially importable to project
            if should_include:
                importable_artifacts.append(artifact)
            else:
                filtered_count += 1
                logger.debug(
                    f"Filtered out {artifact_key} (exists in both Collection and Project)"
                )

        # Log filtering summary
        if filtered_count > 0:
            logger.info(
                f"Filtered {filtered_count} artifacts that exist in both Collection and Project",
                extra={
                    "total_discovered": len(discovered_artifacts),
                    "importable": len(importable_artifacts),
                    "filtered": filtered_count,
                },
            )

        # Filter by skip preferences if project_path provided
        skipped_artifacts = []
        skip_start_time = time.time()

        if project_path:
            try:
                skip_mgr = SkipPreferenceManager(project_path)
                pre_skip_count = len(importable_artifacts)
                filtered_importable = []

                for artifact in importable_artifacts:
                    artifact_key = build_artifact_key(artifact.type, artifact.name)

                    if skip_mgr.is_skipped(artifact_key):
                        if include_skipped:
                            # Get skip preference to add reason
                            skip_pref = skip_mgr.get_skip_by_key(artifact_key)
                            if skip_pref:
                                artifact.skip_reason = skip_pref.skip_reason
                            skipped_artifacts.append(artifact)
                        logger.debug(f"Filtered skipped artifact: {artifact_key}")
                    else:
                        filtered_importable.append(artifact)

                # Update importable_artifacts with filtered list
                skip_filtered_count = pre_skip_count - len(filtered_importable)
                importable_artifacts = filtered_importable

                # Log skip filtering performance
                skip_duration_ms = (time.time() - skip_start_time) * 1000

                if skip_filtered_count > 0:
                    logger.info(
                        f"Filtered {skip_filtered_count} skipped artifacts in {skip_duration_ms:.2f}ms",
                        extra={
                            "skip_filtered_count": skip_filtered_count,
                            "remaining_importable": len(importable_artifacts),
                            "skip_duration_ms": round(skip_duration_ms, 2),
                        },
                    )
                else:
                    logger.debug(
                        f"Skip preference check completed in {skip_duration_ms:.2f}ms (no skipped artifacts)"
                    )

            except Exception as e:
                error_msg = f"Failed to load skip preferences: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)
                # Continue without skip filtering if there's an error

        # Early return if all artifacts are filtered out
        if len(importable_artifacts) == 0 and len(discovered_artifacts) > 0:
            logger.info(
                f"All {len(discovered_artifacts)} discovered artifacts already exist in "
                f"Collection and/or Project or are skipped. Nothing to import."
            )

        # Calculate scan duration
        scan_duration_ms = (time.time() - start_time) * 1000
        scan_duration_sec = scan_duration_ms / 1000

        # Record metrics
        discovery_scans_total.labels(
            status="success" if not errors else "partial_success"
        ).inc()
        discovery_artifacts_found.set(len(discovered_artifacts))
        discovery_scan_duration.observe(scan_duration_sec)
        discovery_metrics.record_scan(len(discovered_artifacts), scan_duration_ms)

        logger.info(
            f"Discovery scan completed: {len(discovered_artifacts)} artifacts found, "
            f"{len(importable_artifacts)} importable, {len(skipped_artifacts)} skipped in {scan_duration_ms:.2f}ms",
            extra={
                "discovered_count": len(discovered_artifacts),
                "importable_count": len(importable_artifacts),
                "skipped_count": len(skipped_artifacts),
                "error_count": len(errors),
                "duration_ms": round(scan_duration_ms, 2),
            },
        )

        return DiscoveryResult(
            discovered_count=len(discovered_artifacts),
            importable_count=len(importable_artifacts),
            artifacts=importable_artifacts,
            skipped_artifacts=skipped_artifacts,
            errors=errors,
            scan_duration_ms=scan_duration_ms,
        )

    def _check_collection_membership(
        self,
        name: str,
        artifact_type: str,
        source_link: Optional[str],
        membership_index: Dict[str, Any],
    ) -> CollectionStatusInfo:
        """Check collection membership using pre-built index.

        Performs O(1) membership lookup using the indexed structure.
        Matching priority:
        1. Exact source_link match -> "exact"
        2. Name + type match -> "name_type"
        3. No match -> "none"

        Note: Hash matching requires content hash from the discovered artifact,
        which is computed elsewhere. This method focuses on source and name+type.

        Args:
            name: Artifact name
            artifact_type: Artifact type (skill, command, etc.)
            source_link: Optional source URL
            membership_index: Pre-built index from get_collection_membership_index()

        Returns:
            CollectionStatusInfo with in_collection, match_type, matched_artifact_id
        """
        # Priority 1: Exact source_link match
        if source_link:
            source_normalized = source_link.strip().lower()
            if source_normalized in membership_index.get("by_source", {}):
                matched_id = membership_index["by_source"][source_normalized]
                return CollectionStatusInfo(
                    in_collection=True,
                    match_type="exact",
                    matched_artifact_id=matched_id,
                )

        # Priority 2: Name + type match (case-insensitive)
        name_type_key = (name.lower(), artifact_type.lower())
        if name_type_key in membership_index.get("by_name_type", {}):
            matched_id = membership_index["by_name_type"][name_type_key]
            return CollectionStatusInfo(
                in_collection=True,
                match_type="name_type",
                matched_artifact_id=matched_id,
            )

        # No match found
        return CollectionStatusInfo(
            in_collection=False,
            match_type="none",
            matched_artifact_id=None,
        )

    def _compute_collection_match(
        self,
        content_hash: Optional[str],
        name: str,
        artifact_type: str,
        membership_index: Dict[str, Any],
    ) -> CollectionMatchInfo:
        """Compute hash-based collection match with confidence score.

        Performs matching against collection using content hash and name+type
        with confidence scoring:
        1. Exact hash match -> "exact" (confidence: 1.0)
        2. Name + type match -> "name_type" (confidence: 0.85)
        3. No match -> "none" (confidence: 0.0)

        Args:
            content_hash: SHA256 content hash of the discovered artifact
            name: Artifact name
            artifact_type: Artifact type (skill, command, etc.)
            membership_index: Pre-built index from get_collection_membership_index()

        Returns:
            CollectionMatchInfo with type, matched_artifact_id, matched_name, confidence
        """
        # Priority 1: Exact hash match (highest confidence)
        if content_hash and content_hash in membership_index.get("by_hash", {}):
            matched_id = membership_index["by_hash"][content_hash]
            # Extract name from matched_id (format: "type:name")
            matched_name = matched_id.split(":", 1)[-1] if ":" in matched_id else matched_id
            return CollectionMatchInfo(
                type="exact",
                matched_artifact_id=matched_id,
                matched_name=matched_name,
                confidence=1.0,
            )

        # Priority 2: Name + type match (moderate confidence)
        name_type_key = (name.lower(), artifact_type.lower())
        if name_type_key in membership_index.get("by_name_type", {}):
            matched_id = membership_index["by_name_type"][name_type_key]
            matched_name = matched_id.split(":", 1)[-1] if ":" in matched_id else matched_id
            return CollectionMatchInfo(
                type="name_type",
                matched_artifact_id=matched_id,
                matched_name=matched_name,
                confidence=0.85,
            )

        # No match found
        return CollectionMatchInfo(
            type="none",
            matched_artifact_id=None,
            matched_name=None,
            confidence=0.0,
        )

    def _scan_type_directory(
        self,
        type_dir: Path,
        artifact_type: str,
        errors: List[str],
        manifest: Optional["Collection"] = None,
        collection_membership_index: Optional[Dict[str, Any]] = None,
    ) -> List[DiscoveredArtifact]:
        """Scan a single artifact type directory.

        Args:
            type_dir: Path to artifact type directory (e.g., skills/)
            artifact_type: Type of artifacts in this directory
            errors: List to append errors to
            manifest: Optional Collection manifest for timestamp preservation
            collection_membership_index: Optional pre-built membership index for
                efficient O(1) collection membership lookups.

        Returns:
            List of discovered artifacts in this directory
        """
        discovered = []

        # Use scandir for efficient directory traversal
        import os

        try:
            with os.scandir(type_dir) as entries:
                for entry in entries:
                    # Skip hidden files/directories
                    if entry.name.startswith("."):
                        continue

                    artifact_path = Path(entry.path)

                    # Try to detect and process artifact
                    try:
                        detected_type = self._detect_artifact_type(artifact_path)

                        # If detection failed or type mismatch, skip
                        if detected_type is None:
                            logger.debug(
                                f"Could not detect artifact type: {artifact_path}"
                            )
                            continue

                        # Validate artifact structure
                        if not self._validate_artifact(artifact_path, detected_type):
                            error_msg = f"Invalid artifact structure: {artifact_path}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                            continue

                        # Check for deprecated patterns (logs warning but continues)
                        self._check_deprecation(artifact_path, detected_type)

                        # Extract metadata
                        metadata = self._extract_artifact_metadata(
                            artifact_path, detected_type
                        )

                        # Get artifact name
                        artifact_name = metadata.get("name", artifact_path.stem)

                        # Get timestamp (preserves existing if unchanged)
                        discovered_at = self._get_artifact_timestamp(
                            artifact_path, artifact_name, detected_type, manifest
                        )

                        # Compute content hash for deduplication
                        content_hash = None
                        try:
                            content_hash = compute_content_hash(artifact_path)
                        except Exception as hash_err:
                            logger.debug(
                                f"Failed to compute content hash for {artifact_path}: {hash_err}"
                            )

                        # Determine collection membership status
                        collection_status = None
                        collection_match = None
                        if collection_membership_index is not None:
                            collection_status = self._check_collection_membership(
                                artifact_name,
                                detected_type,
                                metadata.get("source"),
                                collection_membership_index,
                            )
                            # Compute hash-based match with confidence score
                            collection_match = self._compute_collection_match(
                                content_hash,
                                artifact_name,
                                detected_type,
                                collection_membership_index,
                            )

                        # Create DiscoveredArtifact
                        artifact = DiscoveredArtifact(
                            type=detected_type,
                            name=artifact_name,
                            source=metadata.get("source"),
                            version=metadata.get("version"),
                            scope=metadata.get("scope"),
                            tags=metadata.get("tags", []),
                            description=metadata.get("description"),
                            path=str(artifact_path),
                            discovered_at=discovered_at,
                            collection_status=collection_status,
                            content_hash=content_hash,
                            collection_match=collection_match,
                        )

                        discovered.append(artifact)
                        logger.debug(
                            f"Discovered {detected_type}: {artifact.name} "
                            f"(in_collection={collection_status.in_collection if collection_status else 'N/A'}, "
                            f"hash_match={collection_match.type if collection_match else 'N/A'}, "
                            f"confidence={collection_match.confidence if collection_match else 'N/A'})"
                        )

                    except Exception as e:
                        error_msg = f"Error processing {artifact_path}: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)

        except PermissionError as e:
            error_msg = f"Permission denied scanning {type_dir}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

        # Scan for nested artifacts (only for types that support nesting)
        nested = self._discover_nested_artifacts(
            type_dir, artifact_type, errors
        )
        discovered.extend(nested)

        return discovered

    def _discover_nested_artifacts(
        self,
        container_path: Path,
        container_type: str,
        errors: List[str],
        max_depth: int = 3,
    ) -> List[DiscoveredArtifact]:
        """Recursively discover nested artifacts in subdirectories.

        This method traverses subdirectories to find artifacts nested within
        container directories. Only artifact types with allowed_nesting=True
        in ARTIFACT_SIGNATURES support nesting (e.g., commands, agents).

        Recursive Traversal:
            - Starts from subdirectories of container_path (top-level already scanned)
            - Recursively descends up to max_depth levels (default 3)
            - Skips hidden files/directories (starting with '.')
            - Processes both single-file (.md) and directory-based artifacts
            - Collects errors without failing entire scan

        Nesting Support:
            Checks ARTIFACT_SIGNATURES[artifact_type].allowed_nesting before
            recursing. Skills, hooks, and MCPs do not support nesting and will
            return empty list immediately.

        Args:
            container_path: Path to container directory (e.g., .claude/commands/)
            container_type: Normalized artifact type (e.g., "command")
            errors: List to append errors to (modified in-place)
            max_depth: Maximum recursion depth to prevent infinite loops (default 3)

        Returns:
            List of discovered nested artifacts (empty if type doesn't support nesting)
        """
        discovered: List[DiscoveredArtifact] = []

        # Check if this artifact type supports nesting
        try:
            artifact_type_enum = ArtifactType(container_type)
            signature = ARTIFACT_SIGNATURES.get(artifact_type_enum)
            if not signature or not signature.allowed_nesting:
                return discovered
        except ValueError:
            return discovered

        def _scan_recursive(current_path: Path, depth: int) -> None:
            if depth > max_depth:
                return

            try:
                for entry in current_path.iterdir():
                    if entry.name.startswith("."):
                        continue

                    if entry.is_file() and entry.suffix.lower() == ".md":
                        # Potential single-file artifact
                        try:
                            detected_type = self._detect_artifact_type(entry)
                            if detected_type is None:
                                continue
                            if detected_type == container_type:
                                metadata = self._extract_artifact_metadata(
                                    entry, detected_type
                                )
                                artifact = DiscoveredArtifact(
                                    type=detected_type,
                                    name=metadata.get("name", entry.stem),
                                    source=metadata.get("source"),
                                    version=metadata.get("version"),
                                    scope=metadata.get("scope"),
                                    tags=metadata.get("tags", []),
                                    description=metadata.get("description"),
                                    path=str(entry),
                                    discovered_at=datetime.utcnow(),
                                )
                                discovered.append(artifact)
                                logger.debug(
                                    f"Discovered nested {detected_type}: "
                                    f"{artifact.name} at depth {depth}"
                                )
                        except Exception as e:
                            error_msg = f"Error processing nested artifact {entry}: {e}"
                            logger.warning(error_msg)
                            errors.append(error_msg)

                    elif entry.is_dir():
                        # Recurse into subdirectory
                        _scan_recursive(entry, depth + 1)

            except PermissionError as e:
                error_msg = f"Permission denied scanning {current_path}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        # Start recursion from subdirectories only (top-level already scanned)
        try:
            for subdir in container_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    _scan_recursive(subdir, 1)
        except PermissionError as e:
            error_msg = f"Permission denied accessing {container_path}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

        return discovered

    def _detect_artifact_type(self, artifact_path: Path) -> Optional[str]:
        """Detect artifact type using shared detection module.

        Uses the unified detect_artifact() function from artifact_detection module
        for consistent detection across the codebase.

        Detection Flow:
            1. Extract container type hint from parent directory name
            2. Call detect_artifact() in heuristic mode for flexible detection
            3. Apply 50% confidence threshold to filter low-confidence results
            4. Return artifact type string or None

        Heuristic Mode:
            Discovery uses heuristic mode (vs strict mode) to handle edge cases
            like nested artifacts, legacy patterns, and ambiguous structures.
            The 50% confidence threshold ensures we only accept reasonably
            confident detections while remaining flexible.

        Args:
            artifact_path: Path to potential artifact

        Returns:
            Artifact type string (e.g., "skill", "command"), or None if not detected
        """
        try:
            # Get container type hint from parent directory
            parent_name = artifact_path.parent.name
            container_type = None
            artifact_type_from_parent = get_artifact_type_from_container(parent_name)
            if artifact_type_from_parent:
                container_type = parent_name

            # Use shared detector in heuristic mode for discovery
            # We use heuristic mode because discovery needs to handle edge cases
            result = detect_artifact(
                artifact_path,
                container_type=container_type,
                mode="heuristic",
            )

            # Only return type if confidence is sufficient (>=50)
            if result.confidence >= 50:
                return result.artifact_type.value

            logger.debug(
                f"Low confidence detection for {artifact_path}: "
                f"{result.confidence}% ({', '.join(result.detection_reasons)})"
            )
            return None

        except DetectionError as e:
            logger.debug(f"Detection error for {artifact_path}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Unexpected error detecting {artifact_path}: {e}")
            return None

    def _extract_artifact_metadata(
        self, artifact_path: Path, artifact_type: str
    ) -> Dict[str, Any]:
        """Extract metadata from artifact frontmatter.

        Reads the appropriate metadata file (SKILL.md, COMMAND.md, etc.)
        and extracts YAML frontmatter.

        Args:
            artifact_path: Path to artifact directory or file
            artifact_type: Type of artifact

        Returns:
            Dictionary of extracted metadata (normalized)
        """
        metadata: Dict[str, Any] = {}

        # Determine metadata file path
        metadata_file = self._find_metadata_file(artifact_path, artifact_type)

        if metadata_file is None or not metadata_file.exists():
            logger.debug(f"No metadata file found for {artifact_path}")
            return metadata

        # Extract YAML frontmatter
        try:
            yaml_data = extract_yaml_frontmatter(metadata_file)
            if yaml_data:
                # Extract name first (needed for synthetic source)
                name = yaml_data.get("name", yaml_data.get("title", artifact_path.stem))

                # Extract source, with fallback to synthetic local source
                source = yaml_data.get("source", yaml_data.get("upstream"))
                if not source:
                    # Generate synthetic local source for artifacts without GitHub source
                    source = f"local/{artifact_type}/{name}"
                    logger.debug(f"Generated synthetic local source: {source}")

                # Normalize metadata fields
                metadata = {
                    "name": name,
                    "description": yaml_data.get("description"),
                    "source": source,
                    "version": yaml_data.get("version"),
                    "scope": yaml_data.get("scope"),
                    "tags": yaml_data.get("tags", []),
                    "author": yaml_data.get("author"),
                    "license": yaml_data.get("license"),
                }

                # Remove None values
                metadata = {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            error_msg = f"Failed to extract frontmatter from {metadata_file}: {e}"
            logger.warning(error_msg)
            # Don't fail - just log warning and return empty metadata

        return metadata

    def _find_metadata_file(
        self, artifact_path: Path, artifact_type: str
    ) -> Optional[Path]:
        """Find the metadata file for an artifact.

        Uses extract_manifest_file() from shared artifact_detection module for
        primary artifact types (skill, command, agent, hook, mcp). Falls back
        to legacy logic for backward compatibility.

        Manifest File Resolution:
            - Skills: SKILL.md in directory
            - Commands: command.md file itself (if single file) or COMMAND.md/command.md in directory
            - Agents: agent.md file itself (if single file) or AGENT.md/agent.md in directory
            - Hooks: HOOK.md or hook.md in directory
            - MCPs: MCP.md in directory

        Args:
            artifact_path: Path to artifact (file or directory)
            artifact_type: Type of artifact (e.g., "skill", "command")

        Returns:
            Path to metadata file, or None if not found
        """
        # Try to use shared module for primary types
        try:
            artifact_type_enum = ArtifactType(artifact_type)
            manifest_path = extract_manifest_file(artifact_path, artifact_type_enum)
            if manifest_path:
                return manifest_path
        except ValueError:
            # Not a valid ArtifactType enum value, fall through to legacy logic
            pass

        # Legacy fallback for backwards compatibility
        if artifact_type == "skill":
            if artifact_path.is_dir():
                return artifact_path / "SKILL.md"
        elif artifact_type == "command":
            if artifact_path.is_file() and artifact_path.suffix == ".md":
                return artifact_path
            elif artifact_path.is_dir():
                if (artifact_path / "COMMAND.md").exists():
                    return artifact_path / "COMMAND.md"
                if (artifact_path / "command.md").exists():
                    return artifact_path / "command.md"
        elif artifact_type == "agent":
            if artifact_path.is_file() and artifact_path.suffix == ".md":
                return artifact_path
            elif artifact_path.is_dir():
                if (artifact_path / "AGENT.md").exists():
                    return artifact_path / "AGENT.md"
                if (artifact_path / "agent.md").exists():
                    return artifact_path / "agent.md"
        elif artifact_type == "hook":
            if artifact_path.is_dir():
                if (artifact_path / "HOOK.md").exists():
                    return artifact_path / "HOOK.md"
                if (artifact_path / "hook.md").exists():
                    return artifact_path / "hook.md"
        elif artifact_type == "mcp":
            if artifact_path.is_dir():
                if (artifact_path / "MCP.md").exists():
                    return artifact_path / "MCP.md"

        return None

    def _validate_artifact(self, artifact_path: Path, artifact_type: str) -> bool:
        """Validate artifact structure.

        Checks that required files exist and frontmatter is valid.

        Args:
            artifact_path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            True if valid, False otherwise
        """
        # Check that metadata file exists
        metadata_file = self._find_metadata_file(artifact_path, artifact_type)
        if metadata_file is None or not metadata_file.exists():
            return False

        # Try to parse frontmatter (validation)
        try:
            _ = extract_yaml_frontmatter(metadata_file)
            # Valid if we can parse it (even if empty)
            return True
        except Exception as e:
            logger.debug(f"Frontmatter validation failed for {metadata_file}: {e}")
            return False

    def check_artifact_exists(
        self,
        artifact_key: str,  # Format: "type:name" (e.g., "skill:canvas-design")
        manifest: Optional["Collection"] = None,
    ) -> Dict[str, Any]:
        """
        Check if an artifact exists in Collection and/or Project.

        Args:
            artifact_key: Artifact identifier in "type:name" format
            manifest: Optional manifest to check against (uses self.manifest if not provided)

        Returns:
            dict with keys:
            - exists_in_collection: bool
            - exists_in_project: bool
            - collection_path: Optional[str] - path if exists in collection
            - project_path: Optional[str] - path if exists in project
            - location: str - "collection", "project", "both", or "none"
        """
        # Parse artifact_key
        try:
            artifact_type, artifact_name = artifact_key.split(":", 1)
        except ValueError:
            logger.warning(
                f"Invalid artifact_key format: {artifact_key}. Expected 'type:name'"
            )
            return {
                "exists_in_collection": False,
                "exists_in_project": False,
                "collection_path": None,
                "project_path": None,
                "location": "none",
            }

        # Initialize result
        exists_in_collection = False
        exists_in_project = False
        collection_path = None
        project_path = None

        # Check Collection
        try:
            # Get collection base path
            from skillmeat.config import ConfigManager

            config = ConfigManager()
            collection_name = config.get_active_collection()
            collection_base = config.get_collection_path(collection_name)

            # Check collection artifacts directory
            # Format: ~/.skillmeat/collections/{collection_name}/artifacts/{type}s/{name}/
            collection_artifact_dir = (
                collection_base / "artifacts" / f"{artifact_type}s" / artifact_name
            )

            if collection_artifact_dir.exists() and collection_artifact_dir.is_dir():
                exists_in_collection = True
                collection_path = str(collection_artifact_dir)
                logger.debug(
                    f"Artifact {artifact_key} found in collection at {collection_path}"
                )
            else:
                # Fallback: Check manifest if provided
                if manifest:
                    try:
                        artifact_type_enum = ArtifactType(artifact_type)
                        found = manifest.find_artifact(
                            artifact_name, artifact_type_enum
                        )
                        if found:
                            exists_in_collection = True
                            # Construct path from manifest
                            collection_path = str(collection_base / found.path)
                            logger.debug(f"Artifact {artifact_key} found in manifest")
                    except ValueError:
                        # Invalid artifact type
                        logger.debug(f"Invalid artifact type in key: {artifact_type}")
                    except Exception as e:
                        # Corrupt manifest or other error
                        logger.warning(
                            f"Error checking manifest for {artifact_key}: {e}"
                        )
        except PermissionError as e:
            logger.warning(
                f"Permission denied accessing collection for {artifact_key}: {e}"
            )
        except Exception as e:
            logger.warning(f"Error checking collection for {artifact_key}: {e}")

        # Check Project
        try:
            # Format: {self.base_path}/.claude/{type}s/{name}/
            project_artifact_dir = (
                self.base_path / ".claude" / f"{artifact_type}s" / artifact_name
            )

            if project_artifact_dir.exists() and project_artifact_dir.is_dir():
                exists_in_project = True
                project_path = str(project_artifact_dir)
                logger.debug(
                    f"Artifact {artifact_key} found in project at {project_path}"
                )
        except PermissionError as e:
            logger.warning(
                f"Permission denied accessing project for {artifact_key}: {e}"
            )
        except Exception as e:
            logger.warning(f"Error checking project for {artifact_key}: {e}")

        # Determine location
        if exists_in_collection and exists_in_project:
            location = "both"
        elif exists_in_collection:
            location = "collection"
        elif exists_in_project:
            location = "project"
        else:
            location = "none"

        return {
            "exists_in_collection": exists_in_collection,
            "exists_in_project": exists_in_project,
            "collection_path": collection_path,
            "project_path": project_path,
            "location": location,
        }

    def _normalize_type_from_dirname(self, dirname: str) -> str:
        """Normalize directory name to artifact type using shared detection module.

        Args:
            dirname: Directory name (e.g., "skills", "commands", "subagents")

        Returns:
            Normalized artifact type (e.g., "skill", "command", "agent")
        """
        artifact_type = get_artifact_type_from_container(dirname)
        if artifact_type:
            return artifact_type.value
        # Fallback: Remove trailing 's' for plural directory names
        dirname_lower = dirname.lower()
        if dirname_lower.endswith("s") and len(dirname_lower) > 1:
            return dirname_lower[:-1]
        return dirname_lower

    def _check_deprecation(
        self, artifact_path: Path, artifact_type: str
    ) -> Optional[str]:
        """Check for deprecated artifact patterns and log warning.

        Per ARTIFACT_SIGNATURES, commands and agents should be single .md files,
        not directories. Directory-based patterns are legacy and deprecated.

        Deprecated Patterns:
            - Directory-based commands (should be single .md file)
            - Directory-based agents (should be single .md file)

        These patterns are still detected and processed for backward compatibility,
        but will be removed in a future version. Users should migrate to single
        .md file format per migration guide.

        Args:
            artifact_path: Path to artifact
            artifact_type: Detected artifact type

        Returns:
            Deprecation warning message if deprecated pattern found, None otherwise
        """
        # Check for directory-based commands (deprecated)
        if artifact_type == "command" and artifact_path.is_dir():
            warning = DEPRECATION_WARNINGS["directory_command"].format(
                path=artifact_path
            )
            logger.warning(warning)
            return warning

        # Check for directory-based agents (deprecated)
        if artifact_type == "agent" and artifact_path.is_dir():
            warning = DEPRECATION_WARNINGS["directory_agent"].format(path=artifact_path)
            logger.warning(warning)
            return warning

        return None
