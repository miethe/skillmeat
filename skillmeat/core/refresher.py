"""Data models and core refresher for Collection Artifact Refresh feature.

This module provides the core data structures for refreshing artifact metadata
from GitHub sources. It includes result types for individual and batch refresh
operations, refresh mode configuration, field mapping for metadata updates,
and the CollectionRefresher class that orchestrates metadata extraction and updates.

Tasks: BE-101, BE-102, BE-103, BE-104, BE-105, BE-106, BE-107, BE-108, BE-109,
       BE-111, BE-112
"""

import fnmatch
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from skillmeat.storage.snapshot import SnapshotManager

from skillmeat.core.artifact import Artifact, ArtifactMetadata
from skillmeat.core.artifact_detection import ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.github_client import (
    GitHubClient,
    GitHubClientError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    get_github_client,
)
from skillmeat.core.github_metadata import (
    GitHubMetadata,
    GitHubMetadataExtractor,
    GitHubSourceSpec,
)
from skillmeat.models import DriftDetectionResult
from skillmeat.sources.base import UpdateInfo


class RefreshMode(str, Enum):
    """Mode for artifact refresh operations.

    Determines what level of refresh to perform on artifacts.

    Attributes:
        METADATA_ONLY: Only update metadata fields (description, tags, etc.)
                      without changing version or content.
        CHECK_ONLY: Detect available updates without applying changes.
                   Useful for dry-run or preview operations.
        SYNC: Full synchronization including version updates and content
              changes from upstream source.
    """

    METADATA_ONLY = "metadata_only"
    CHECK_ONLY = "check_only"
    SYNC = "sync"


# Field mapping configuration for artifact refresh operations.
# Maps artifact fields to their corresponding GitHub metadata fields.
# Used to determine which fields to update during refresh.
#
# Keys are artifact field names (as stored in collection metadata).
# Values are GitHub API field names (from repository metadata).
REFRESH_FIELD_MAPPING: Dict[str, str] = {
    "description": "description",  # artifact.metadata.description -> github.description
    "tags": "topics",  # artifact.tags -> github.topics
    "author": "author",  # artifact.author -> github.owner (mapped to author)
    "license": "license",  # artifact.license -> github.license.spdx_id
    # NOTE: origin_source is NOT refreshed - it's a platform type (github/gitlab/bitbucket)
    # set during import, not a field that comes from GitHub metadata. The upstream field
    # already stores the full GitHub URL.
}

# Set of all valid refreshable field names for validation
REFRESHABLE_FIELDS = frozenset(REFRESH_FIELD_MAPPING.keys())


def validate_fields(
    fields: Optional[List[str]],
    strict: bool = True,
) -> Tuple[List[str], List[str]]:
    """Validate field names for refresh operations.

    Args:
        fields: List of field names to validate (None = all fields valid)
        strict: If True, raise ValueError on invalid fields. If False, return
               invalid fields for logging/warning.

    Returns:
        Tuple of (valid_fields, invalid_fields) where:
        - valid_fields: List of validated field names (case-normalized)
        - invalid_fields: List of invalid field names

    Raises:
        ValueError: If any invalid fields found and strict=True

    Example:
        >>> validate_fields(["description", "tags"])
        (["description", "tags"], [])

        >>> validate_fields(["description", "invalid"])
        ValueError: Invalid field names: invalid. Valid fields: author, description, license, tags

        >>> validate_fields(["DESCRIPTION", "Tags"])  # Case-insensitive
        (["description", "tags"], [])
    """
    # If no fields specified, all fields are valid
    if fields is None:
        return list(REFRESHABLE_FIELDS), []

    # Normalize to lowercase for case-insensitive matching
    field_map = {f.lower(): f for f in REFRESHABLE_FIELDS}

    valid_fields = []
    invalid_fields = []

    for field in fields:
        normalized = field.lower().strip()
        if normalized in field_map:
            # Use the canonical field name (not the user-provided casing)
            valid_fields.append(field_map[normalized])
        else:
            invalid_fields.append(field)

    if invalid_fields and strict:
        # Build error message with suggestions
        valid_list = ", ".join(sorted(REFRESHABLE_FIELDS))
        error_msg = (
            f"Invalid field name(s): {', '.join(invalid_fields)}. "
            f"Valid fields: {valid_list}"
        )

        # Add closest match suggestions for typos
        suggestions = []
        for invalid_field in invalid_fields:
            closest = _find_closest_field(invalid_field)
            if closest:
                suggestions.append(f"'{invalid_field}' -> did you mean '{closest}'?")

        if suggestions:
            error_msg += f"\n\nSuggestions: {'; '.join(suggestions)}"

        raise ValueError(error_msg)

    return valid_fields, invalid_fields


def _find_closest_field(field_name: str) -> Optional[str]:
    """Find the closest matching valid field name using simple distance heuristic.

    Args:
        field_name: Invalid field name to find match for

    Returns:
        Closest valid field name, or None if no close match found

    Example:
        >>> _find_closest_field("descriptio")
        "description"
        >>> _find_closest_field("tgs")
        "tags"
    """
    field_lower = field_name.lower()

    # Simple heuristics for common typos:
    # 1. Prefix match (e.g., "desc" -> "description")
    # 2. Contains match (e.g., "icense" -> "license")
    # 3. Levenshtein distance (basic implementation)

    candidates = []

    for valid_field in REFRESHABLE_FIELDS:
        score = 0

        # Exact prefix match (highest priority)
        if valid_field.startswith(field_lower):
            score = 100 - len(valid_field) + len(field_lower)
        # Field contains input
        elif field_lower in valid_field:
            score = 50 - len(valid_field) + len(field_lower)
        # Input contains field (e.g., "tagss" -> "tags")
        elif valid_field in field_lower:
            score = 40
        else:
            # Simple character overlap score
            overlap = sum(1 for c in field_lower if c in valid_field)
            if overlap > len(field_lower) * 0.5:  # >50% character overlap
                score = overlap

        if score > 0:
            candidates.append((score, valid_field))

    if not candidates:
        return None

    # Return highest scoring match
    candidates.sort(reverse=True)
    return candidates[0][1]


@dataclass
class UpdateAvailableResult:
    """Result for checking if an update is available for a single artifact.

    Tracks the outcome of an update check operation, comparing the artifact's
    current SHA with the upstream SHA to determine if an update is available.
    When an update is available, optionally includes drift detection details
    from SyncManager.check_drift() for three-way merge analysis.

    Attributes:
        artifact_id: Unique identifier for the artifact (format: "type:name").
        artifact_name: Human-readable name of the artifact.
        current_sha: Current resolved SHA of the artifact (or version if SHA not stored).
        upstream_sha: Latest SHA from upstream GitHub source.
        update_available: Whether an update is available (SHAs differ).
        reason: Human-readable explanation of the result
               (e.g., "SHA mismatch", "No upstream data", "No GitHub source").
        drift_info: Optional DriftDetectionResult with detailed field-level changes
                   when drift is detected via SyncManager.check_drift().
        has_local_changes: Whether local modifications exist in the project
                          deployment that might conflict with the update.
        merge_strategy: Suggested action for handling the update:
                       - "safe_update": No local changes, update can be applied safely
                       - "review_required": Local changes exist but no conflict
                       - "conflict": Both local and upstream changed (three-way conflict)
                       - "no_update": No update available

    Example:
        >>> result = UpdateAvailableResult(
        ...     artifact_id="skill:canvas",
        ...     artifact_name="canvas",
        ...     current_sha="abc123",
        ...     upstream_sha="def456",
        ...     update_available=True,
        ...     reason="SHA mismatch",
        ...     has_local_changes=False,
        ...     merge_strategy="safe_update"
        ... )
    """

    artifact_id: str
    artifact_name: str
    current_sha: Optional[str] = None
    upstream_sha: Optional[str] = None
    update_available: bool = False
    reason: Optional[str] = None
    drift_info: Optional[DriftDetectionResult] = None
    has_local_changes: bool = False
    merge_strategy: str = "no_update"

    def __post_init__(self):
        """Validate merge_strategy value."""
        valid_strategies = {"safe_update", "review_required", "conflict", "no_update"}
        if self.merge_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid merge_strategy '{self.merge_strategy}'. "
                f"Must be one of {valid_strategies}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON/TOML serialization.
        """
        result: Dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "artifact_name": self.artifact_name,
            "current_sha": self.current_sha,
            "upstream_sha": self.upstream_sha,
            "update_available": self.update_available,
            "reason": self.reason,
            "has_local_changes": self.has_local_changes,
            "merge_strategy": self.merge_strategy,
        }
        # Include drift_info only if present (avoid serializing None)
        if self.drift_info is not None:
            result["drift_info"] = {
                "artifact_name": self.drift_info.artifact_name,
                "artifact_type": self.drift_info.artifact_type,
                "drift_type": self.drift_info.drift_type,
                "collection_sha": self.drift_info.collection_sha,
                "project_sha": self.drift_info.project_sha,
                "recommendation": self.drift_info.recommendation,
                "change_origin": self.drift_info.change_origin,
                "baseline_hash": self.drift_info.baseline_hash,
                "current_hash": self.drift_info.current_hash,
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateAvailableResult":
        """Create instance from dictionary.

        Args:
            data: Dictionary with UpdateAvailableResult fields.

        Returns:
            New UpdateAvailableResult instance.
        """
        # Reconstruct DriftDetectionResult if present
        drift_info = None
        if data.get("drift_info"):
            drift_data = data["drift_info"]
            drift_info = DriftDetectionResult(
                artifact_name=drift_data["artifact_name"],
                artifact_type=drift_data["artifact_type"],
                drift_type=drift_data["drift_type"],
                collection_sha=drift_data.get("collection_sha"),
                project_sha=drift_data.get("project_sha"),
                recommendation=drift_data.get("recommendation", "review_manually"),
                change_origin=drift_data.get("change_origin"),
                baseline_hash=drift_data.get("baseline_hash"),
                current_hash=drift_data.get("current_hash"),
            )

        return cls(
            artifact_id=data["artifact_id"],
            artifact_name=data["artifact_name"],
            current_sha=data.get("current_sha"),
            upstream_sha=data.get("upstream_sha"),
            update_available=data.get("update_available", False),
            reason=data.get("reason"),
            drift_info=drift_info,
            has_local_changes=data.get("has_local_changes", False),
            merge_strategy=data.get("merge_strategy", "no_update"),
        )


@dataclass
class RefreshEntryResult:
    """Result for refreshing a single artifact.

    Tracks the outcome of a refresh operation on a single artifact,
    including what changed, old/new values, and timing information.

    Attributes:
        artifact_id: Unique identifier for the artifact (format: "type:name").
        status: Outcome of the refresh operation:
            - "refreshed": Artifact was updated with new metadata.
            - "unchanged": Artifact metadata matches upstream (no changes needed).
            - "skipped": Artifact was skipped (e.g., no GitHub source).
            - "error": Refresh failed with an error.
        changes: List of ALL field names that differ from upstream, including
                both applied and non-applied fields when using field whitelist.
                This provides complete visibility into what has changed upstream.
        old_values: Previous values for ALL changed fields (None if no changes).
        new_values: New values for ALL changed fields (None if no changes).
                   When field whitelist is used, this includes non-whitelisted
                   fields for informational purposes.
        error: Error message if status is "error", None otherwise.
        reason: Human-readable explanation for skip/error status or filtering
               (e.g., "No GitHub source", "Rate limited", "Filtered by whitelist").
        duration_ms: Time taken to refresh this artifact in milliseconds.

    Example:
        >>> result = RefreshEntryResult(
        ...     artifact_id="skill:canvas",
        ...     status="refreshed",
        ...     changes=["description", "tags"],
        ...     old_values={"description": "Old desc", "tags": []},
        ...     new_values={"description": "New desc", "tags": ["design"]},
        ...     duration_ms=150.5
        ... )
    """

    artifact_id: str
    status: str
    changes: List[str] = field(default_factory=list)
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    reason: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON/TOML serialization.
        """
        return {
            "artifact_id": self.artifact_id,
            "status": self.status,
            "changes": self.changes,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "error": self.error,
            "reason": self.reason,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RefreshEntryResult":
        """Create instance from dictionary.

        Args:
            data: Dictionary with RefreshEntryResult fields.

        Returns:
            New RefreshEntryResult instance.
        """
        return cls(
            artifact_id=data["artifact_id"],
            status=data["status"],
            changes=data.get("changes", []),
            old_values=data.get("old_values"),
            new_values=data.get("new_values"),
            error=data.get("error"),
            reason=data.get("reason"),
            duration_ms=data.get("duration_ms", 0.0),
        )


@dataclass
class RefreshResult:
    """Aggregated result for collection refresh operation.

    Contains summary statistics and individual results for a batch
    refresh operation on multiple artifacts.

    Attributes:
        refreshed_count: Number of artifacts successfully updated.
        unchanged_count: Number of artifacts with no changes needed.
        skipped_count: Number of artifacts skipped (e.g., no source).
        error_count: Number of artifacts that failed with errors.
        entries: List of individual RefreshEntryResult for each artifact.
        duration_ms: Total time for the refresh operation in milliseconds.
        snapshot_id: Optional ID of pre-refresh snapshot created for rollback.

    Properties:
        total_processed: Total number of artifacts processed (sum of all counts).
        success_rate: Percentage of successful operations (refreshed + unchanged).

    Example:
        >>> result = RefreshResult(
        ...     refreshed_count=5,
        ...     unchanged_count=10,
        ...     skipped_count=2,
        ...     error_count=1,
        ...     entries=[...],
        ...     duration_ms=2500.0,
        ...     snapshot_id="20250122-103045-123456"
        ... )
        >>> result.total_processed
        18
        >>> result.success_rate
        83.33
    """

    refreshed_count: int = 0
    unchanged_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    entries: List[RefreshEntryResult] = field(default_factory=list)
    duration_ms: float = 0.0
    snapshot_id: Optional[str] = None

    @property
    def total_processed(self) -> int:
        """Total number of artifacts processed.

        Returns:
            Sum of refreshed, unchanged, skipped, and error counts.
        """
        return (
            self.refreshed_count
            + self.unchanged_count
            + self.skipped_count
            + self.error_count
        )

    @property
    def success_rate(self) -> float:
        """Percentage of successful operations.

        Success is defined as artifacts that were either refreshed
        (updated with new metadata) or unchanged (already up-to-date).
        Skipped and error artifacts are not counted as successful.

        Returns:
            Success rate as a percentage (0.0 to 100.0).
            Returns 0.0 if no artifacts were processed.
        """
        total = self.total_processed
        if total == 0:
            return 0.0
        successful = self.refreshed_count + self.unchanged_count
        return round((successful / total) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON/TOML serialization.
        """
        return {
            "refreshed_count": self.refreshed_count,
            "unchanged_count": self.unchanged_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "entries": [e.to_dict() for e in self.entries],
            "duration_ms": self.duration_ms,
            "snapshot_id": self.snapshot_id,
            "total_processed": self.total_processed,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RefreshResult":
        """Create instance from dictionary.

        Args:
            data: Dictionary with RefreshResult fields.

        Returns:
            New RefreshResult instance.
        """
        entries = [RefreshEntryResult.from_dict(e) for e in data.get("entries", [])]
        return cls(
            refreshed_count=data.get("refreshed_count", 0),
            unchanged_count=data.get("unchanged_count", 0),
            skipped_count=data.get("skipped_count", 0),
            error_count=data.get("error_count", 0),
            entries=entries,
            duration_ms=data.get("duration_ms", 0.0),
            snapshot_id=data.get("snapshot_id"),
        )


class CollectionRefresher:
    """Refreshes artifact metadata from upstream GitHub sources.

    This class orchestrates metadata extraction and updates for collection
    artifacts, supporting dry-run previews and detailed change tracking.

    The refresher can operate in different modes:
    - METADATA_ONLY: Only update metadata fields (description, tags, etc.)
    - CHECK_ONLY: Detect available updates without applying changes (dry-run)
    - SYNC: Full synchronization including version updates

    Attributes:
        _collection_manager: Manager for collection operations
        _metadata_extractor: Extractor for GitHub metadata (lazy initialized)
        _github_client: GitHub API client (lazy initialized)
        _logger: Logger instance for this class

    Example:
        >>> from skillmeat.core.collection import CollectionManager
        >>> from skillmeat.core.refresher import CollectionRefresher, RefreshMode
        >>>
        >>> manager = CollectionManager()
        >>> refresher = CollectionRefresher(manager)
        >>>
        >>> # Check what would change (dry-run)
        >>> result = refresher.refresh(mode=RefreshMode.CHECK_ONLY)
        >>> print(f"Would update {result.refreshed_count} artifacts")
        >>>
        >>> # Apply metadata updates
        >>> result = refresher.refresh(mode=RefreshMode.METADATA_ONLY)
    """

    def __init__(
        self,
        collection_manager: CollectionManager,
        metadata_extractor: Optional[GitHubMetadataExtractor] = None,
        github_client: Optional[GitHubClient] = None,
        snapshot_manager: Optional["SnapshotManager"] = None,
    ):
        """Initialize the refresher with required dependencies.

        Args:
            collection_manager: Manager for collection operations
            metadata_extractor: Extractor for GitHub metadata (created lazily if None)
            github_client: GitHub API client (created lazily if None)
            snapshot_manager: Manager for snapshot operations (optional, for rollback support)
        """
        self._collection_manager = collection_manager
        self._metadata_extractor = metadata_extractor
        self._github_client = github_client
        self._snapshot_manager = snapshot_manager
        self._logger = logging.getLogger(__name__)

    @property
    def metadata_extractor(self) -> GitHubMetadataExtractor:
        """Lazy initialization of metadata extractor.

        Returns:
            GitHubMetadataExtractor instance configured with GitHub client
        """
        if self._metadata_extractor is None:
            from skillmeat.core.cache import MetadataCache

            cache = MetadataCache()
            self._metadata_extractor = GitHubMetadataExtractor(cache)
        return self._metadata_extractor

    @property
    def github_client(self) -> GitHubClient:
        """Lazy initialization of GitHub client.

        Returns:
            GitHubClient instance with token resolution
        """
        if self._github_client is None:
            self._github_client = get_github_client()
        return self._github_client

    def _parse_source_spec(self, source: str) -> Optional[GitHubSourceSpec]:
        """Parse artifact source into GitHubSourceSpec.

        Parses the artifact source string into its component parts for
        GitHub API access. Supports multiple formats:
        - Short format: owner/repo/path/to/artifact
        - Versioned: owner/repo/path@v1.0.0 or @abc1234 (SHA)
        - HTTPS: https://github.com/owner/repo/tree/main/path

        Args:
            source: Source string like "owner/repo/path/to/artifact" or
                    "owner/repo/path@v1.0.0"

        Returns:
            GitHubSourceSpec if valid GitHub source, None if source is not
            a valid GitHub reference (e.g., local path, empty string)

        Raises:
            ValueError: If source format is invalid but appears to be a
                       GitHub reference (e.g., malformed URL)

        Example:
            >>> refresher._parse_source_spec("anthropics/skills/canvas-design")
            GitHubSourceSpec(owner='anthropics', repo='skills', path='canvas-design', version='latest')

            >>> refresher._parse_source_spec("user/repo/skill@v1.0.0")
            GitHubSourceSpec(owner='user', repo='repo', path='skill', version='v1.0.0')

            >>> refresher._parse_source_spec("/local/path")
            None
        """
        if not source or not source.strip():
            return None

        source = source.strip()

        # Skip local paths (absolute or relative)
        if source.startswith("/") or source.startswith("./") or source.startswith(".."):
            return None

        # Use the metadata extractor's parse method which handles all formats
        try:
            return self.metadata_extractor.parse_github_url(source)
        except ValueError as e:
            # Check if it looks like a GitHub reference but is malformed
            if source.startswith("https://github.com/") or source.count("/") >= 2:
                # Looks like a GitHub reference but invalid
                raise ValueError(f"Invalid GitHub source format: {source}. {e}")
            # Doesn't look like GitHub, return None
            return None

    def _fetch_upstream_metadata(
        self, spec: GitHubSourceSpec
    ) -> Optional[GitHubMetadata]:
        """Fetch metadata from GitHub for a single artifact.

        Retrieves metadata from the GitHub API including:
        - YAML frontmatter from artifact markdown files (SKILL.md, etc.)
        - Repository metadata (topics, license, description)

        Args:
            spec: Parsed GitHub source specification with owner, repo, path

        Returns:
            GitHubMetadata if successful, None if not found or error occurred

        Note:
            Errors are logged but not raised. Returns None on:
            - Rate limit exceeded (logs warning)
            - Repository/file not found (logs debug)
            - Network or other errors (logs error)

        Example:
            >>> spec = GitHubSourceSpec(
            ...     owner="anthropics", repo="skills",
            ...     path="canvas-design", version="latest"
            ... )
            >>> metadata = refresher._fetch_upstream_metadata(spec)
            >>> if metadata:
            ...     print(f"Description: {metadata.description}")
        """
        # Build source string from spec
        source = f"{spec.owner}/{spec.repo}"
        if spec.path:
            source += f"/{spec.path}"
        if spec.version and spec.version != "latest":
            source += f"@{spec.version}"

        self._logger.debug(f"Fetching upstream metadata for: {source}")

        try:
            metadata = self.metadata_extractor.fetch_metadata(source)
            self._logger.debug(
                f"Successfully fetched metadata for {source}",
                extra={
                    "has_title": metadata.title is not None,
                    "has_description": metadata.description is not None,
                    "topics_count": len(metadata.topics),
                },
            )
            return metadata

        except GitHubRateLimitError as e:
            self._logger.warning(
                f"GitHub API rate limit exceeded while fetching metadata for {source}: "
                f"{e.message}. Reset at: {e.reset_at}"
            )
            return None

        except GitHubNotFoundError as e:
            self._logger.debug(f"GitHub source not found: {source}. {e.message}")
            return None

        except GitHubClientError as e:
            self._logger.error(
                f"GitHub client error fetching metadata for {source}: {e.message}"
            )
            return None

        except ValueError as e:
            self._logger.error(f"Invalid source specification {source}: {e}")
            return None

        except Exception as e:
            self._logger.error(
                f"Unexpected error fetching metadata for {source}: {e}",
                exc_info=True,
            )
            return None

    def _detect_changes(
        self,
        artifact: Artifact,
        upstream: GitHubMetadata,
        fields: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Compare artifact metadata with upstream, detect changes.

        Compares the current artifact metadata with freshly fetched upstream
        metadata and identifies which fields have changed. Uses the
        REFRESH_FIELD_MAPPING to map between artifact and GitHub fields.

        Always detects changes for ALL fields regardless of the fields parameter.
        The fields parameter is used later by _apply_updates() to filter which
        changes actually get applied.

        Args:
            artifact: Current artifact to compare
            upstream: Fresh metadata from GitHub
            fields: Optional list of fields to apply (used for filtering during
                   apply, not during detection). If None, all changed fields
                   will be applied.

        Returns:
            Tuple of (old_values, new_values) dictionaries containing only
            the fields that actually changed. Empty dicts if no changes.

        Note:
            - Handles None vs empty list comparisons correctly
            - Tags are compared as sorted lists for consistency
            - License is normalized to lowercase for comparison
            - Always detects ALL changes for reporting purposes

        Example:
            >>> old, new = refresher._detect_changes(artifact, upstream)
            >>> if old:
            ...     print(f"Changed fields: {list(old.keys())}")
            ...     for field, old_val in old.items():
            ...         print(f"  {field}: {old_val} -> {new[field]}")
        """
        old_values: Dict[str, Any] = {}
        new_values: Dict[str, Any] = {}

        # Always check ALL fields to detect and report all changes
        # The fields parameter is used later by _apply_updates() to filter
        fields_to_check = list(REFRESH_FIELD_MAPPING.keys())

        for artifact_field in fields_to_check:
            if artifact_field not in REFRESH_FIELD_MAPPING:
                self._logger.warning(
                    f"Unknown field '{artifact_field}' not in REFRESH_FIELD_MAPPING"
                )
                continue

            github_field = REFRESH_FIELD_MAPPING[artifact_field]

            # Get current value from artifact
            current_value = self._get_artifact_field_value(artifact, artifact_field)

            # Get upstream value from GitHub metadata
            upstream_value = self._get_upstream_field_value(upstream, github_field)

            # Compare values (with normalization)
            if self._values_differ(current_value, upstream_value, artifact_field):
                old_values[artifact_field] = current_value
                new_values[artifact_field] = upstream_value

        return old_values, new_values

    def _get_artifact_field_value(self, artifact: Artifact, field_name: str) -> Any:
        """Extract field value from artifact based on field name.

        Args:
            artifact: Artifact to extract value from
            field_name: Name of the field (from REFRESH_FIELD_MAPPING keys)

        Returns:
            Current value of the field, or None if not set
        """
        if field_name == "description":
            return artifact.metadata.description
        elif field_name == "tags":
            return artifact.tags or []
        elif field_name == "author":
            return artifact.metadata.author
        elif field_name == "license":
            return artifact.metadata.license
        elif field_name == "origin_source":
            return artifact.origin_source
        else:
            self._logger.warning(f"Unknown artifact field: {field_name}")
            return None

    def _get_upstream_field_value(
        self, upstream: GitHubMetadata, field_name: str
    ) -> Any:
        """Extract field value from GitHub metadata based on field name.

        Args:
            upstream: GitHub metadata to extract value from
            field_name: Name of the field (from REFRESH_FIELD_MAPPING values)

        Returns:
            Upstream value of the field, or None if not set
        """
        if field_name == "description":
            return upstream.description
        elif field_name == "topics":
            return upstream.topics or []
        elif field_name == "author":
            return upstream.author
        elif field_name == "license":
            return upstream.license
        elif field_name == "url":
            return upstream.url
        else:
            self._logger.warning(f"Unknown GitHub metadata field: {field_name}")
            return None

    def _values_differ(self, current: Any, upstream: Any, field_name: str) -> bool:
        """Check if two values are different, with field-specific normalization.

        Args:
            current: Current value from artifact
            upstream: Upstream value from GitHub
            field_name: Field name for type-specific comparison

        Returns:
            True if values differ, False if they are equivalent
        """
        # Handle None vs empty string/list equivalence
        if current is None and upstream is None:
            return False

        # For tags/lists, compare sorted lists
        if field_name == "tags":
            current_list = sorted(current) if current else []
            upstream_list = sorted(upstream) if upstream else []
            return current_list != upstream_list

        # For license, normalize case
        if field_name == "license":
            current_norm = current.lower() if current else None
            upstream_norm = upstream.lower() if upstream else None
            return current_norm != upstream_norm

        # For strings, treat None and empty string as equivalent
        if isinstance(current, str) or isinstance(upstream, str):
            current_norm = current if current else None
            upstream_norm = upstream if upstream else None
            return current_norm != upstream_norm

        # Default comparison
        return current != upstream

    def _apply_updates(
        self,
        artifact: Artifact,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        fields: Optional[List[str]] = None,
    ) -> Artifact:
        """Apply metadata updates to artifact (in-memory, does not persist).

        Updates the artifact's metadata fields with new values from upstream.
        This method modifies the artifact in place but does not persist
        changes to disk - the caller is responsible for saving.

        When fields parameter is provided, only applies updates for the
        whitelisted fields. Other fields are skipped even if they have changes.

        Args:
            artifact: Artifact to update (modified in place)
            old_values: Previous values (for validation/logging)
            new_values: New values to apply
            fields: Optional list of field names to apply. If None, all fields
                   in new_values are applied. If provided, only whitelisted
                   fields are applied.

        Returns:
            Updated artifact (same instance, modified in place)

        Note:
            Only fields present in new_values are updated. Other fields
            remain unchanged. When fields parameter is provided, non-whitelisted
            fields are skipped even if present in new_values.

        Example:
            >>> old = {"description": "Old desc", "tags": []}
            >>> new = {"description": "New desc", "tags": ["python"]}
            >>> updated = refresher._apply_updates(artifact, old, new)
            >>> assert updated.metadata.description == "New desc"
            >>> assert updated.tags == ["python"]
            >>>
            >>> # Selective update: only description
            >>> updated = refresher._apply_updates(artifact, old, new, fields=["description"])
            >>> assert updated.metadata.description == "New desc"
            >>> assert updated.tags == []  # tags not updated
        """
        for field_name, new_value in new_values.items():
            # Skip non-whitelisted fields if whitelist provided
            if fields is not None and field_name not in fields:
                self._logger.debug(
                    f"Skipping {artifact.name}.{field_name}: not in whitelist {fields}"
                )
                continue
            old_value = old_values.get(field_name)
            self._logger.debug(
                f"Updating {artifact.name}.{field_name}: "
                f"{old_value!r} -> {new_value!r}"
            )

            if field_name == "description":
                artifact.metadata.description = new_value
            elif field_name == "tags":
                # Replace artifact tags entirely
                artifact.tags = new_value if new_value else []
            elif field_name == "author":
                artifact.metadata.author = new_value
            elif field_name == "license":
                artifact.metadata.license = new_value
            elif field_name == "origin_source":
                # Only update origin_source if artifact origin is "marketplace"
                if artifact.origin == "marketplace":
                    artifact.origin_source = new_value
                else:
                    self._logger.warning(
                        f"Cannot set origin_source on artifact with origin "
                        f"'{artifact.origin}' - only 'marketplace' artifacts "
                        "support origin_source"
                    )
            else:
                self._logger.warning(
                    f"Unknown field '{field_name}' in updates - skipping"
                )

        return artifact

    def refresh_metadata(
        self,
        artifact: Artifact,
        mode: RefreshMode = RefreshMode.METADATA_ONLY,
        dry_run: bool = False,
        fields: Optional[List[str]] = None,
    ) -> RefreshEntryResult:
        """Refresh metadata for a single artifact from upstream GitHub.

        This is the main refresh operation for a single artifact that orchestrates:
        parse -> fetch -> detect -> apply

        The refresh process:
        1. Validates artifact has a GitHub source
        2. Parses the source specification
        3. Fetches upstream metadata from GitHub
        4. Detects changes between current and upstream metadata
        5. Applies updates (unless dry_run or CHECK_ONLY mode)

        Args:
            artifact: Artifact to refresh
            mode: Refresh mode determining behavior:
                - METADATA_ONLY: Update metadata fields without version changes
                - CHECK_ONLY: Detect changes but don't apply them
                - SYNC: Full synchronization (reserved for future use)
            dry_run: If True, detect changes but don't apply them (overrides mode)
            fields: Optional list of fields to refresh. If None, refreshes all
                   fields defined in REFRESH_FIELD_MAPPING.

        Returns:
            RefreshEntryResult with status and change details:
            - status="refreshed": Changes were applied (or would be in dry-run)
            - status="unchanged": No changes detected
            - status="skipped": Artifact has no GitHub source
            - status="error": An error occurred during refresh

        Example:
            >>> refresher = CollectionRefresher(collection_manager)
            >>> # Preview changes without applying
            >>> result = refresher.refresh_metadata(artifact, dry_run=True)
            >>> if result.status == "refreshed":
            ...     print(f"Would change: {result.changes}")
            ...     for field in result.changes:
            ...         print(f"  {field}: {result.old_values[field]} -> {result.new_values[field]}")
            >>>
            >>> # Apply changes
            >>> result = refresher.refresh_metadata(artifact)
            >>> if result.status == "refreshed":
            ...     print(f"Updated {len(result.changes)} fields")
        """
        start_time = time.perf_counter()
        artifact_id = f"{artifact.type.value}:{artifact.name}"

        self._logger.debug(
            f"Starting metadata refresh for {artifact_id}",
            extra={"mode": mode.value, "dry_run": dry_run, "fields": fields},
        )

        # Validate field names if provided
        try:
            validated_fields, _ = validate_fields(fields, strict=True)
            # Use validated fields (normalized) for the rest of the operation
            fields = validated_fields if fields else None
        except ValueError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._logger.error(f"Field validation failed for {artifact_id}: {e}")
            return RefreshEntryResult(
                artifact_id=artifact_id,
                status="error",
                changes=[],
                error=str(e),
                duration_ms=duration_ms,
            )

        # 1. Determine GitHub source URL based on origin type
        # - origin="github": Direct GitHub artifact, source URL in `upstream`
        # - origin="marketplace" + origin_source="github": Marketplace artifact from GitHub
        # - origin="local": Skip (no upstream source)
        source_url: Optional[str] = None

        if artifact.origin == "github":
            # Direct GitHub artifact - use upstream field
            source_url = artifact.upstream
        elif artifact.origin == "marketplace" and artifact.origin_source == "github":
            # Marketplace artifact from GitHub - use upstream field
            source_url = artifact.upstream
        # origin="local" or marketplace from non-GitHub sources: source_url stays None

        if not source_url:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._logger.debug(
                f"Skipping {artifact_id}: No GitHub source "
                f"(origin={artifact.origin}, origin_source={artifact.origin_source}, "
                f"upstream={artifact.upstream})"
            )
            return RefreshEntryResult(
                artifact_id=artifact_id,
                status="skipped",
                changes=[],
                reason="No GitHub source",
                duration_ms=duration_ms,
            )

        # 2. Parse source spec
        try:
            spec = self._parse_source_spec(source_url)
            if spec is None:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._logger.debug(
                    f"Skipping {artifact_id}: Invalid source format ({source_url})"
                )
                return RefreshEntryResult(
                    artifact_id=artifact_id,
                    status="skipped",
                    changes=[],
                    reason="Invalid source format",
                    duration_ms=duration_ms,
                )
        except ValueError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._logger.error(f"Error parsing source for {artifact_id}: {e}")
            return RefreshEntryResult(
                artifact_id=artifact_id,
                status="error",
                changes=[],
                error=str(e),
                duration_ms=duration_ms,
            )

        # 3. Fetch upstream metadata
        upstream = self._fetch_upstream_metadata(spec)
        if upstream is None:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._logger.debug(f"Failed to fetch upstream metadata for {artifact_id}")
            return RefreshEntryResult(
                artifact_id=artifact_id,
                status="error",
                changes=[],
                error="Failed to fetch upstream metadata",
                duration_ms=duration_ms,
            )

        # 4. Detect changes
        old_values, new_values = self._detect_changes(artifact, upstream, fields)

        if not new_values:
            # No changes detected
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._logger.debug(f"No changes detected for {artifact_id}")
            return RefreshEntryResult(
                artifact_id=artifact_id,
                status="unchanged",
                changes=[],
                duration_ms=duration_ms,
            )

        # 5. For CHECK_ONLY mode or dry_run, report changes without applying
        if mode == RefreshMode.CHECK_ONLY or dry_run:
            duration_ms = (time.perf_counter() - start_time) * 1000
            reason = "Dry run - changes not applied" if dry_run else "Check only"
            self._logger.debug(
                f"Detected changes for {artifact_id} ({reason}): "
                f"{list(new_values.keys())}"
            )
            return RefreshEntryResult(
                artifact_id=artifact_id,
                status="refreshed",
                changes=list(new_values.keys()),
                old_values=old_values,
                new_values=new_values,
                reason=reason,
                duration_ms=duration_ms,
            )

        # 6. Apply updates (in-memory)
        self._apply_updates(artifact, old_values, new_values, fields)

        duration_ms = (time.perf_counter() - start_time) * 1000
        self._logger.debug(
            f"Refreshed {artifact_id}: updated {list(new_values.keys())} "
            f"in {duration_ms:.2f}ms"
        )

        return RefreshEntryResult(
            artifact_id=artifact_id,
            status="refreshed",
            changes=list(new_values.keys()),
            old_values=old_values,
            new_values=new_values,
            duration_ms=duration_ms,
        )

    def _filter_artifacts(
        self,
        artifacts: List[Artifact],
        artifact_filter: Optional[Dict[str, Any]],
    ) -> List[Artifact]:
        """Filter artifacts based on provided filter criteria.

        Args:
            artifacts: List of artifacts to filter
            artifact_filter: Optional filter dict with keys:
                - type: ArtifactType or str to filter by type
                - name: str pattern to filter by name (supports glob)

        Returns:
            Filtered list of artifacts matching all criteria
        """
        if not artifact_filter:
            return artifacts

        filtered = artifacts

        # Filter by type
        type_filter = artifact_filter.get("type")
        if type_filter is not None:
            # Convert string to ArtifactType if needed
            if isinstance(type_filter, str):
                try:
                    type_filter = ArtifactType(type_filter)
                except ValueError:
                    self._logger.warning(f"Invalid artifact type filter: {type_filter}")
                    type_filter = None

            if type_filter is not None:
                filtered = [a for a in filtered if a.type == type_filter]
                self._logger.debug(
                    f"Type filter '{type_filter.value}' matched {len(filtered)} artifacts"
                )

        # Filter by name pattern (supports glob)
        name_pattern = artifact_filter.get("name")
        if name_pattern:
            filtered = [a for a in filtered if fnmatch.fnmatch(a.name, name_pattern)]
            self._logger.debug(
                f"Name filter '{name_pattern}' matched {len(filtered)} artifacts"
            )

        return filtered

    def refresh_collection(
        self,
        collection_name: Optional[str] = None,
        mode: RefreshMode = RefreshMode.METADATA_ONLY,
        dry_run: bool = False,
        fields: Optional[List[str]] = None,
        artifact_filter: Optional[Dict[str, Any]] = None,
        create_snapshot_before_refresh: bool = True,
    ) -> RefreshResult:
        """Refresh metadata for all artifacts in a collection.

        Iterates through all artifacts in the specified collection and refreshes
        their metadata from upstream GitHub sources. Supports filtering, dry-run
        mode, and field-specific updates.

        Args:
            collection_name: Name of collection to refresh (None = default collection)
            mode: Refresh mode for all artifacts:
                - METADATA_ONLY: Update metadata fields without version changes
                - CHECK_ONLY: Detect changes but don't apply them
                - SYNC: Full synchronization (reserved for future use)
            dry_run: If True, detect changes without applying them
            fields: Fields to refresh (None = all mapped fields)
            artifact_filter: Optional filter dict with keys:
                - type: ArtifactType or str to filter by type
                - name: str pattern to filter by name (supports glob)
            create_snapshot_before_refresh: If True, create a snapshot of collection
                state before applying refresh changes. Defaults to True for rollback
                support. Set to False to skip snapshot creation.

        Returns:
            RefreshResult with aggregated counts and per-artifact results:
            - refreshed_count: Number of artifacts successfully updated
            - unchanged_count: Number of artifacts with no changes needed
            - skipped_count: Number of artifacts skipped (e.g., no GitHub source)
            - error_count: Number of artifacts that failed with errors
            - entries: List of RefreshEntryResult for each processed artifact
            - duration_ms: Total time for the operation

        Raises:
            ValueError: If collection cannot be loaded (e.g., not found)

        Example:
            >>> refresher = CollectionRefresher(collection_manager)
            >>> # Preview all changes
            >>> result = refresher.refresh_collection(dry_run=True)
            >>> print(f"Would refresh {result.refreshed_count} artifacts")
            >>>
            >>> # Refresh only skills
            >>> result = refresher.refresh_collection(
            ...     artifact_filter={"type": "skill"}
            ... )
            >>>
            >>> # Refresh by name pattern
            >>> result = refresher.refresh_collection(
            ...     artifact_filter={"name": "canvas-*"}
            ... )
        """
        start_time = time.perf_counter()
        display_name = collection_name or "default"

        self._logger.debug(
            f"Starting collection refresh for: {display_name}",
            extra={
                "mode": mode.value,
                "dry_run": dry_run,
                "fields": fields,
                "filter": artifact_filter,
            },
        )

        # Validate field names if provided
        try:
            validated_fields, _ = validate_fields(fields, strict=True)
            # Use validated fields (normalized) for the rest of the operation
            fields = validated_fields if fields else None
        except ValueError as e:
            self._logger.error(
                f"Field validation failed for collection {display_name}: {e}"
            )
            raise

        # Initialize result
        result = RefreshResult(
            refreshed_count=0,
            unchanged_count=0,
            skipped_count=0,
            error_count=0,
            entries=[],
            duration_ms=0.0,
        )

        # 1. Load collection
        try:
            collection = self._collection_manager.load_collection(collection_name)
            self._logger.debug(
                f"Loaded collection '{collection.name}' with "
                f"{len(collection.artifacts)} artifacts"
            )
        except ValueError as e:
            self._logger.error(f"Failed to load collection '{display_name}': {e}")
            raise
        except Exception as e:
            self._logger.error(
                f"Unexpected error loading collection '{display_name}': {e}",
                exc_info=True,
            )
            raise ValueError(f"Failed to load collection: {e}") from e

        # 2. Get and filter artifacts
        artifacts = collection.artifacts
        if artifact_filter:
            artifacts = self._filter_artifacts(artifacts, artifact_filter)
            self._logger.debug(
                f"Filter applied: {len(artifacts)} of "
                f"{len(collection.artifacts)} artifacts selected"
            )

        if not artifacts:
            self._logger.info(
                f"No artifacts to refresh in collection '{collection.name}'"
            )
            result.duration_ms = (time.perf_counter() - start_time) * 1000
            return result

        self._logger.info(
            f"Refreshing {len(artifacts)} artifacts in collection '{collection.name}'"
        )

        # 3. Create snapshot before refresh if requested (and not dry_run)
        snapshot_id: Optional[str] = None
        if (
            create_snapshot_before_refresh
            and not dry_run
            and mode != RefreshMode.CHECK_ONLY
            and self._snapshot_manager is not None
        ):
            try:
                from datetime import datetime

                timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                snapshot_message = f"pre-refresh-{timestamp}"

                # Get collection path from config
                collection_path = self._collection_manager.config.get_collection_path(
                    collection.name
                )

                self._logger.info(
                    f"Creating snapshot before refresh: {snapshot_message}"
                )

                snapshot = self._snapshot_manager.create_snapshot(
                    collection_path=collection_path,
                    collection_name=collection.name,
                    message=snapshot_message,
                )

                snapshot_id = snapshot.id
                self._logger.info(
                    f"Snapshot created successfully: {snapshot_id} "
                    f"({snapshot.artifact_count} artifacts)"
                )

            except Exception as e:
                # Log warning but continue with refresh
                # Snapshot failure shouldn't block the refresh operation
                self._logger.warning(
                    f"Failed to create pre-refresh snapshot: {e}. "
                    "Continuing with refresh without rollback support.",
                    exc_info=True,
                )

        # 4. Track whether any artifact was actually modified
        any_modified = False

        # 5. Iterate and refresh each artifact
        for artifact in artifacts:
            artifact_id = f"{artifact.type.value}:{artifact.name}"

            try:
                self._logger.debug(f"Processing artifact: {artifact_id}")

                entry_result = self.refresh_metadata(
                    artifact=artifact,
                    mode=mode,
                    dry_run=dry_run,
                    fields=fields,
                )

                # Update counts based on status
                if entry_result.status == "refreshed":
                    result.refreshed_count += 1
                    # Only mark as modified if not dry_run and not CHECK_ONLY
                    if not dry_run and mode != RefreshMode.CHECK_ONLY:
                        any_modified = True
                elif entry_result.status == "unchanged":
                    result.unchanged_count += 1
                elif entry_result.status == "skipped":
                    result.skipped_count += 1
                elif entry_result.status == "error":
                    result.error_count += 1

                result.entries.append(entry_result)

            except GitHubRateLimitError as e:
                # Rate limit - log warning and record error but continue
                self._logger.warning(
                    f"Rate limit hit while refreshing {artifact_id}: {e.message}"
                )
                result.error_count += 1
                result.entries.append(
                    RefreshEntryResult(
                        artifact_id=artifact_id,
                        status="error",
                        changes=[],
                        error=f"Rate limit exceeded: {e.message}",
                        reason="GitHub API rate limit",
                    )
                )

            except Exception as e:
                # Unexpected error - log and continue processing
                self._logger.error(
                    f"Error refreshing artifact {artifact_id}: {e}",
                    exc_info=True,
                )
                result.error_count += 1
                result.entries.append(
                    RefreshEntryResult(
                        artifact_id=artifact_id,
                        status="error",
                        changes=[],
                        error=str(e),
                        reason="Unexpected error during refresh",
                    )
                )

        # 5. Save collection if changes were made (and not dry_run)
        if any_modified and not dry_run:
            try:
                self._logger.debug(f"Saving collection '{collection.name}'")
                self._collection_manager.save_collection(collection)
                self._logger.debug(f"Collection '{collection.name}' saved successfully")
            except Exception as e:
                self._logger.error(
                    f"Failed to save collection '{collection.name}': {e}",
                    exc_info=True,
                )
                # Don't raise - we've already modified artifacts in memory
                # Log the error but return the results showing what was refreshed

        # 6. Calculate total duration and set snapshot_id
        result.duration_ms = (time.perf_counter() - start_time) * 1000
        result.snapshot_id = snapshot_id

        # 7. Log summary
        self._logger.info(
            f"Refresh complete for collection '{collection.name}': "
            f"{result.refreshed_count} refreshed, "
            f"{result.unchanged_count} unchanged, "
            f"{result.skipped_count} skipped, "
            f"{result.error_count} errors "
            f"({result.duration_ms:.2f}ms)"
        )

        return result

    def check_updates(
        self,
        collection_name: Optional[str] = None,
        artifact_filter: Optional[Dict[str, Any]] = None,
        project_path: Optional["Path"] = None,
    ) -> List[UpdateAvailableResult]:
        """Check for available updates for all artifacts in a collection.

        Compares each artifact's current resolved SHA with the upstream SHA
        from GitHub to determine if updates are available. Does not apply
        any changes - this is a read-only check operation.

        When project_path is provided, integrates with SyncManager.check_drift()
        to provide detailed field-level change information and merge strategy
        recommendations based on three-way comparison (BE-402).

        For each artifact with a GitHub source:
        1. Parse the source spec to get owner/repo/path/version
        2. Fetch current upstream SHA using GitHubClient.resolve_version()
        3. Compare with artifact.resolved_sha (or artifact.version if SHA not stored)
        4. If update available and project_path provided, check drift via SyncManager
        5. Return update availability status with drift info and merge strategy

        Args:
            collection_name: Name of collection to check (None = default collection)
            artifact_filter: Optional filter dict with keys:
                - type: ArtifactType or str to filter by type
                - name: str pattern to filter by name (supports glob)
            project_path: Optional path to project where artifacts are deployed.
                         When provided, enables drift detection via SyncManager
                         to include has_local_changes and merge_strategy fields.

        Returns:
            List of UpdateAvailableResult objects, one per artifact, containing:
            - artifact_id: Artifact identifier (e.g., "skill:canvas")
            - artifact_name: Human-readable name
            - current_sha: Current SHA stored in artifact
            - upstream_sha: Latest SHA from upstream
            - update_available: True if SHAs differ
            - reason: Explanation of result
            - drift_info: DriftDetectionResult if project_path provided and drift detected
            - has_local_changes: Whether local modifications exist in project
            - merge_strategy: Recommended action ("safe_update", "review_required",
                             "conflict", "no_update")

        Raises:
            ValueError: If collection cannot be loaded

        Example:
            >>> refresher = CollectionRefresher(collection_manager)
            >>> # Simple update check (no drift detection)
            >>> updates = refresher.check_updates()
            >>> for result in updates:
            ...     if result.update_available:
            ...         print(f"Update available: {result.artifact_name}")
            ...         print(f"  Current: {result.current_sha[:7]}")
            ...         print(f"  Upstream: {result.upstream_sha[:7]}")
            >>>
            >>> # With drift detection for deployed project
            >>> updates = refresher.check_updates(
            ...     project_path=Path("/path/to/project")
            ... )
            >>> for result in updates:
            ...     if result.update_available:
            ...         print(f"Update: {result.artifact_name}")
            ...         print(f"  Local changes: {result.has_local_changes}")
            ...         print(f"  Strategy: {result.merge_strategy}")
        """
        display_name = collection_name or "default"

        self._logger.debug(
            f"Checking for updates in collection: {display_name}",
            extra={"filter": artifact_filter},
        )

        results: List[UpdateAvailableResult] = []

        # 1. Load collection
        try:
            collection = self._collection_manager.load_collection(collection_name)
            self._logger.debug(
                f"Loaded collection '{collection.name}' with "
                f"{len(collection.artifacts)} artifacts"
            )
        except ValueError as e:
            self._logger.error(f"Failed to load collection '{display_name}': {e}")
            raise
        except Exception as e:
            self._logger.error(
                f"Unexpected error loading collection '{display_name}': {e}",
                exc_info=True,
            )
            raise ValueError(f"Failed to load collection: {e}") from e

        # 2. Get and filter artifacts
        artifacts = collection.artifacts
        if artifact_filter:
            artifacts = self._filter_artifacts(artifacts, artifact_filter)
            self._logger.debug(
                f"Filter applied: {len(artifacts)} of "
                f"{len(collection.artifacts)} artifacts selected"
            )

        if not artifacts:
            self._logger.info(
                f"No artifacts to check in collection '{collection.name}'"
            )
            return results

        self._logger.info(
            f"Checking updates for {len(artifacts)} artifacts in "
            f"collection '{collection.name}'"
        )

        # 3. Pre-fetch drift results if project_path provided (BE-402)
        # This avoids calling check_drift() for each artifact individually
        drift_results_map: Dict[Tuple[str, str], DriftDetectionResult] = {}
        if project_path:
            from pathlib import Path

            project_path_resolved = (
                Path(project_path) if isinstance(project_path, str) else project_path
            )

            try:
                from skillmeat.core.sync import SyncManager

                sync_manager = SyncManager(
                    collection_manager=self._collection_manager,
                )
                drift_results = sync_manager.check_drift(project_path_resolved)

                # Build lookup map by (artifact_name, artifact_type)
                for drift in drift_results:
                    key = (drift.artifact_name, drift.artifact_type)
                    drift_results_map[key] = drift

                self._logger.debug(
                    f"Pre-fetched drift results for {len(drift_results_map)} artifacts"
                )

            except ImportError:
                self._logger.debug(
                    "SyncManager not available, skipping drift detection"
                )
            except Exception as e:
                self._logger.warning(
                    f"Failed to check drift for project: {e}. "
                    "Continuing without drift detection."
                )

        # 4. Check each artifact
        for artifact in artifacts:
            result = self._check_artifact_update(artifact, drift_results_map)
            results.append(result)

        # 5. Log summary
        updates_available = sum(1 for r in results if r.update_available)
        skipped = sum(1 for r in results if r.reason and "No GitHub source" in r.reason)
        errors = sum(1 for r in results if r.reason and "Error" in r.reason)
        with_local_changes = sum(1 for r in results if r.has_local_changes)

        self._logger.info(
            f"Update check complete for collection '{collection.name}': "
            f"{updates_available} updates available, "
            f"{len(results) - updates_available - skipped - errors} up-to-date, "
            f"{skipped} skipped, {errors} errors"
            + (f", {with_local_changes} with local changes" if project_path else "")
        )

        return results

    def _check_artifact_update(
        self,
        artifact: Artifact,
        drift_results_map: Optional[Dict[Tuple[str, str], DriftDetectionResult]] = None,
    ) -> UpdateAvailableResult:
        """Check if an update is available for a single artifact.

        Compares the artifact's current resolved SHA with the upstream SHA
        to determine if an update is available. When drift_results_map is
        provided, enriches the result with drift detection info (BE-402).

        Args:
            artifact: Artifact to check for updates
            drift_results_map: Optional map of (artifact_name, artifact_type) to
                              DriftDetectionResult from SyncManager.check_drift().
                              When provided and update is available, the result
                              will include drift_info, has_local_changes, and
                              merge_strategy fields.

        Returns:
            UpdateAvailableResult with update status, details, and drift info
        """
        artifact_id = f"{artifact.type.value}:{artifact.name}"

        # 1. Determine GitHub source URL based on origin type
        source_url: Optional[str] = None

        if artifact.origin == "github":
            source_url = artifact.upstream
        elif artifact.origin == "marketplace" and artifact.origin_source == "github":
            source_url = artifact.upstream

        if not source_url:
            self._logger.debug(
                f"Skipping {artifact_id}: No GitHub source "
                f"(origin={artifact.origin}, origin_source={artifact.origin_source})"
            )
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=artifact.resolved_sha,
                upstream_sha=None,
                update_available=False,
                reason="No GitHub source",
                merge_strategy="no_update",
            )

        # 2. Parse source spec
        try:
            spec = self._parse_source_spec(source_url)
            if spec is None:
                self._logger.debug(
                    f"Skipping {artifact_id}: Invalid source format ({source_url})"
                )
                return UpdateAvailableResult(
                    artifact_id=artifact_id,
                    artifact_name=artifact.name,
                    current_sha=artifact.resolved_sha,
                    upstream_sha=None,
                    update_available=False,
                    reason="Invalid source format",
                    merge_strategy="no_update",
                )
        except ValueError as e:
            self._logger.error(f"Error parsing source for {artifact_id}: {e}")
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=artifact.resolved_sha,
                upstream_sha=None,
                update_available=False,
                reason=f"Error parsing source: {e}",
                merge_strategy="no_update",
            )

        # 3. Get current SHA (use resolved_sha if available, else version)
        current_sha = artifact.resolved_sha or artifact.version_spec

        # 4. Fetch upstream SHA using GitHubClient
        try:
            owner_repo = f"{spec.owner}/{spec.repo}"
            version = spec.version or "latest"

            self._logger.debug(
                f"Resolving upstream version for {artifact_id}: "
                f"{owner_repo}@{version}"
            )

            upstream_sha = self.github_client.resolve_version(owner_repo, version)

            self._logger.debug(
                f"Resolved upstream SHA for {artifact_id}: {upstream_sha[:7]}..."
            )

        except GitHubRateLimitError as e:
            self._logger.warning(
                f"Rate limit exceeded checking {artifact_id}: {e.message}"
            )
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=current_sha,
                upstream_sha=None,
                update_available=False,
                reason="Error: Rate limit exceeded",
                merge_strategy="no_update",
            )

        except GitHubNotFoundError as e:
            self._logger.warning(
                f"GitHub resource not found for {artifact_id}: {e.message}"
            )
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=current_sha,
                upstream_sha=None,
                update_available=False,
                reason="Error: Upstream not found",
                merge_strategy="no_update",
            )

        except GitHubClientError as e:
            self._logger.error(f"GitHub error checking {artifact_id}: {e.message}")
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=current_sha,
                upstream_sha=None,
                update_available=False,
                reason=f"Error: {e.message}",
                merge_strategy="no_update",
            )

        except Exception as e:
            self._logger.error(
                f"Unexpected error checking {artifact_id}: {e}",
                exc_info=True,
            )
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=current_sha,
                upstream_sha=None,
                update_available=False,
                reason=f"Error: {e}",
                merge_strategy="no_update",
            )

        # 5. Compare SHAs
        if not current_sha:
            # No current SHA stored - consider update available
            self._logger.debug(
                f"{artifact_id}: No current SHA stored, update available"
            )
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=None,
                upstream_sha=upstream_sha,
                update_available=True,
                reason="No current SHA stored",
                merge_strategy="safe_update",  # No local state to conflict with
            )

        # Compare SHAs (case-insensitive, handle short SHAs)
        current_normalized = current_sha.lower()
        upstream_normalized = upstream_sha.lower()

        # Handle short SHA comparison
        if len(current_normalized) < 40 and len(upstream_normalized) >= 40:
            # Current is short SHA, compare prefix
            update_available = not upstream_normalized.startswith(current_normalized)
        elif len(upstream_normalized) < 40 and len(current_normalized) >= 40:
            # Upstream is short SHA, compare prefix
            update_available = not current_normalized.startswith(upstream_normalized)
        else:
            # Both are same length, direct comparison
            update_available = current_normalized != upstream_normalized

        if update_available:
            self._logger.debug(
                f"{artifact_id}: Update available "
                f"(current={current_sha[:7]}..., upstream={upstream_sha[:7]}...)"
            )
            reason = "SHA mismatch"
        else:
            self._logger.debug(f"{artifact_id}: Up to date")
            reason = "Up to date"
            return UpdateAvailableResult(
                artifact_id=artifact_id,
                artifact_name=artifact.name,
                current_sha=current_sha,
                upstream_sha=upstream_sha,
                update_available=False,
                reason=reason,
                merge_strategy="no_update",
            )

        # 6. If update available and drift_results_map provided, enrich with drift info (BE-402)
        drift_info: Optional[DriftDetectionResult] = None
        has_local_changes = False
        merge_strategy = "safe_update"  # Default: assume safe update

        if drift_results_map:
            # Look up drift result for this artifact
            drift_key = (artifact.name, artifact.type.value)
            artifact_drift = drift_results_map.get(drift_key)

            if artifact_drift:
                drift_info = artifact_drift
                has_local_changes = artifact_drift.drift_type in (
                    "modified",
                    "conflict",
                )
                merge_strategy = self._determine_merge_strategy(artifact_drift)

                self._logger.debug(
                    f"{artifact_id}: Drift detected - type={artifact_drift.drift_type}, "
                    f"has_local_changes={has_local_changes}, "
                    f"merge_strategy={merge_strategy}"
                )
            else:
                # No drift info for this artifact - may not be deployed
                self._logger.debug(
                    f"{artifact_id}: No drift info available (artifact may not be deployed)"
                )

        return UpdateAvailableResult(
            artifact_id=artifact_id,
            artifact_name=artifact.name,
            current_sha=current_sha,
            upstream_sha=upstream_sha,
            update_available=True,
            reason=reason,
            drift_info=drift_info,
            has_local_changes=has_local_changes,
            merge_strategy=merge_strategy,
        )

    def _determine_merge_strategy(self, drift: DriftDetectionResult) -> str:
        """Determine merge strategy based on drift detection result.

        Maps DriftDetectionResult.drift_type to a merge strategy recommendation
        that indicates how the update should be handled.

        Args:
            drift: DriftDetectionResult from SyncManager.check_drift()

        Returns:
            Merge strategy string:
            - "safe_update": No local changes, update can proceed safely
            - "review_required": Local changes exist but no conflict
            - "conflict": Both local and upstream changed (three-way conflict)
            - "no_update": No update available or artifact removed

        Strategy mapping:
            - "outdated" -> "safe_update": Collection changed, project unchanged
            - "modified" -> "review_required": Project changed, may want to preserve
            - "conflict" -> "conflict": Both changed, manual resolution needed
            - "added" -> "safe_update": New in collection, can deploy
            - "removed" -> "no_update": Artifact removed upstream
            - "version_mismatch" -> "review_required": Version differs, check intent
        """
        strategy_map = {
            "outdated": "safe_update",  # Collection changed, project unchanged
            "modified": "review_required",  # Project has local changes
            "conflict": "conflict",  # Both changed - needs resolution
            "added": "safe_update",  # New artifact - can deploy
            "removed": "no_update",  # Artifact removed upstream
            "version_mismatch": "review_required",  # Version differs
        }

        strategy = strategy_map.get(drift.drift_type, "review_required")

        self._logger.debug(
            f"Mapped drift_type '{drift.drift_type}' to merge_strategy '{strategy}'"
        )

        return strategy
