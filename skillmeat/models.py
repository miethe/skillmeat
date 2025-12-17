"""Data models for SkillMeat.

This module contains dataclasses and models used throughout the SkillMeat
application for representing artifacts, diffs, and other core entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Dict, Literal, Any

if TYPE_CHECKING:
    from skillmeat.storage.snapshot import Snapshot


class SyncDirection(Enum):
    """Direction of sync operation."""

    UPSTREAM_TO_COLLECTION = "upstream_to_collection"  # GitHub → collection
    COLLECTION_TO_PROJECT = "collection_to_project"  # collection → project
    PROJECT_TO_COLLECTION = "project_to_collection"  # project → collection
    BIDIRECTIONAL = "bidirectional"  # Two-way sync


@dataclass
class FileDiff:
    """Difference information for a single file.

    Attributes:
        path: Relative path of the file
        status: One of "added", "removed", "modified", "unchanged", "binary"
        lines_added: Number of lines added (text files only)
        lines_removed: Number of lines removed (text files only)
        unified_diff: Unified diff output for text files, None for binary
    """

    path: str
    status: str
    lines_added: int = 0
    lines_removed: int = 0
    unified_diff: Optional[str] = None

    def __post_init__(self):
        """Validate status value."""
        valid_statuses = {"added", "removed", "modified", "unchanged", "binary"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {valid_statuses}"
            )


@dataclass
class DiffResult:
    """Result of a diff operation between two paths.

    Attributes:
        source_path: Source directory/file path
        target_path: Target directory/file path
        files_added: List of file paths added in target
        files_removed: List of file paths removed from source
        files_modified: List of FileDiff objects for modified files
        files_unchanged: List of file paths that are unchanged
        total_lines_added: Total lines added across all text files
        total_lines_removed: Total lines removed across all text files
    """

    source_path: Path
    target_path: Path
    files_added: List[str] = field(default_factory=list)
    files_removed: List[str] = field(default_factory=list)
    files_modified: List[FileDiff] = field(default_factory=list)
    files_unchanged: List[str] = field(default_factory=list)
    total_lines_added: int = 0
    total_lines_removed: int = 0

    @property
    def has_changes(self) -> bool:
        """Return True if any files changed."""
        return bool(self.files_added or self.files_removed or self.files_modified)

    @property
    def total_files_changed(self) -> int:
        """Return total number of files that changed."""
        return (
            len(self.files_added) + len(self.files_removed) + len(self.files_modified)
        )

    def summary(self) -> str:
        """Generate a human-readable summary of the diff."""
        if not self.has_changes:
            return "No changes detected"

        parts = []
        if self.files_added:
            parts.append(f"{len(self.files_added)} added")
        if self.files_removed:
            parts.append(f"{len(self.files_removed)} removed")
        if self.files_modified:
            parts.append(f"{len(self.files_modified)} modified")

        summary = ", ".join(parts)
        if self.total_lines_added or self.total_lines_removed:
            summary += f" (+{self.total_lines_added} -{self.total_lines_removed} lines)"

        return summary


@dataclass
class ConflictMetadata:
    """Metadata for a merge conflict in three-way diff.

    Represents a file that has conflicting changes between local and remote
    versions, requiring manual resolution or automatic merge strategy.

    Attributes:
        file_path: Relative path to the conflicting file
        conflict_type: Type of conflict detected
        base_content: Content from base/ancestor version (None if file didn't exist)
        local_content: Content from local version (None if deleted locally)
        remote_content: Content from remote version (None if deleted remotely)
        auto_mergeable: Whether this conflict can be auto-merged
        merge_strategy: Recommended merge strategy if auto_mergeable
        is_binary: Whether the file is binary (cannot show content diff)
    """

    file_path: str
    conflict_type: Literal[
        "content",  # Content differs in both versions
        "deletion",  # Deleted in one version, modified in other
        "both_modified",  # Modified differently in both versions
        "add_add",  # Added in both versions with different content
    ]
    base_content: Optional[str] = None
    local_content: Optional[str] = None
    remote_content: Optional[str] = None
    auto_mergeable: bool = False
    merge_strategy: Optional[
        Literal["use_local", "use_remote", "use_base", "manual"]
    ] = None
    is_binary: bool = False

    def __post_init__(self):
        """Validate conflict metadata."""
        valid_types = {"content", "deletion", "both_modified", "add_add"}
        if self.conflict_type not in valid_types:
            raise ValueError(
                f"Invalid conflict_type '{self.conflict_type}'. "
                f"Must be one of {valid_types}"
            )

        valid_strategies = {"use_local", "use_remote", "use_base", "manual", None}
        if self.merge_strategy not in valid_strategies:
            raise ValueError(
                f"Invalid merge_strategy '{self.merge_strategy}'. "
                f"Must be one of {valid_strategies}"
            )


@dataclass
class DiffStats:
    """Statistics about a diff operation.

    Attributes:
        files_compared: Total number of files compared
        files_unchanged: Number of files with no changes
        files_changed: Number of files with changes
        files_conflicted: Number of files with conflicts (three-way only)
        auto_mergeable: Number of files that can auto-merge (three-way only)
        lines_added: Total lines added across all files
        lines_removed: Total lines removed across all files
    """

    files_compared: int = 0
    files_unchanged: int = 0
    files_changed: int = 0
    files_conflicted: int = 0
    auto_mergeable: int = 0
    lines_added: int = 0
    lines_removed: int = 0

    @property
    def total_files(self) -> int:
        """Return total number of files."""
        return self.files_compared

    @property
    def has_conflicts(self) -> bool:
        """Return True if any conflicts exist."""
        return self.files_conflicted > 0

    def summary(self) -> str:
        """Generate a human-readable summary."""
        parts = []
        if self.files_unchanged > 0:
            parts.append(f"{self.files_unchanged} unchanged")
        if self.files_changed > 0:
            parts.append(f"{self.files_changed} changed")
        if self.files_conflicted > 0:
            parts.append(f"{self.files_conflicted} conflicted")
        if self.auto_mergeable > 0:
            parts.append(f"{self.auto_mergeable} auto-mergeable")

        summary = ", ".join(parts) if parts else "No changes"

        if self.lines_added or self.lines_removed:
            summary += f" (+{self.lines_added} -{self.lines_removed} lines)"

        return summary


@dataclass
class ThreeWayDiffResult:
    """Result of a three-way diff operation.

    Contains files that can be auto-merged and files requiring manual
    conflict resolution.

    Attributes:
        base_path: Path to base/ancestor version
        local_path: Path to local version
        remote_path: Path to remote version
        auto_mergeable: List of file paths that can be auto-merged
        conflicts: List of ConflictMetadata for files requiring resolution
        stats: Statistics about the three-way diff
    """

    base_path: Path
    local_path: Path
    remote_path: Path
    auto_mergeable: List[str] = field(default_factory=list)
    conflicts: List[ConflictMetadata] = field(default_factory=list)
    stats: DiffStats = field(default_factory=DiffStats)

    @property
    def has_conflicts(self) -> bool:
        """Return True if any conflicts exist."""
        return len(self.conflicts) > 0

    @property
    def can_auto_merge(self) -> bool:
        """Return True if all changes can be auto-merged."""
        return not self.has_conflicts

    @property
    def total_files(self) -> int:
        """Return total number of files analyzed."""
        return len(self.auto_mergeable) + len(self.conflicts)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        if not self.has_conflicts and not self.auto_mergeable:
            return "No changes detected"

        parts = []
        if self.auto_mergeable:
            parts.append(f"{len(self.auto_mergeable)} auto-mergeable")
        if self.conflicts:
            parts.append(f"{len(self.conflicts)} conflicts")

        return ", ".join(parts)


@dataclass
class MergeStats:
    """Statistics for a merge operation.

    Attributes:
        total_files: Total number of files involved in merge
        auto_merged: Number of files successfully auto-merged
        conflicts: Number of files with unresolved conflicts
        binary_conflicts: Number of binary files with conflicts
    """

    total_files: int = 0
    auto_merged: int = 0
    conflicts: int = 0
    binary_conflicts: int = 0

    @property
    def has_conflicts(self) -> bool:
        """Return True if any conflicts exist."""
        return self.conflicts > 0

    @property
    def success_rate(self) -> float:
        """Return percentage of files successfully auto-merged."""
        if self.total_files == 0:
            return 100.0
        return (self.auto_merged / self.total_files) * 100

    def summary(self) -> str:
        """Generate a human-readable summary."""
        if self.total_files == 0:
            return "No files to merge"

        parts = []
        if self.auto_merged > 0:
            parts.append(f"{self.auto_merged} auto-merged")
        if self.conflicts > 0:
            parts.append(f"{self.conflicts} conflicts")
        if self.binary_conflicts > 0:
            parts.append(f"{self.binary_conflicts} binary conflicts")

        summary = ", ".join(parts) if parts else "No changes"
        summary += f" ({self.success_rate:.1f}% success)"

        return summary


@dataclass
class MergeResult:
    """Result of a merge operation.

    Attributes:
        success: True if fully auto-merged, False if conflicts exist
        merged_content: Merged content for single file merges (may include markers)
        conflicts: List of unresolved conflicts
        auto_merged: List of successfully auto-merged file paths
        stats: Statistics about the merge operation
        output_path: Path where merged results were written (if applicable)
        error: Error message if merge failed (None if successful)
    """

    success: bool
    merged_content: Optional[str] = None
    conflicts: List[ConflictMetadata] = field(default_factory=list)
    auto_merged: List[str] = field(default_factory=list)
    stats: MergeStats = field(default_factory=MergeStats)
    output_path: Optional[Path] = None
    error: Optional[str] = None

    @property
    def has_conflicts(self) -> bool:
        """Return True if any conflicts exist."""
        return len(self.conflicts) > 0

    @property
    def total_files(self) -> int:
        """Return total number of files processed."""
        return len(self.auto_merged) + len(self.conflicts)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        if self.success:
            return f"Merge successful: {len(self.auto_merged)} files auto-merged"

        parts = []
        if self.auto_merged:
            parts.append(f"{len(self.auto_merged)} auto-merged")
        if self.conflicts:
            parts.append(f"{len(self.conflicts)} conflicts")

        return "Merge completed with " + ", ".join(parts)


@dataclass
class SearchCacheEntry:
    """Cache entry for cross-project search index.

    Attributes:
        index: List of project index dictionaries
        created_at: Timestamp when cache entry was created
        ttl: Time-to-live in seconds (default 60s)
    """

    index: List[Dict[str, Any]]
    created_at: float  # time.time() timestamp
    ttl: float = 60.0

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if cache entry is expired
        """
        import time

        return time.time() - self.created_at > self.ttl


@dataclass
class SearchMatch:
    """Single artifact search result match.

    Attributes:
        artifact_name: Name of the artifact
        artifact_type: Type of artifact (skill, command, agent)
        score: Relevance score (higher is better)
        match_type: Where the match was found ("metadata", "content", or "both")
        context: Snippet showing match context
        line_number: Line number for content matches (None for metadata matches)
        metadata: Artifact metadata dictionary
        project_path: Path to project containing this artifact (for cross-project search)
    """

    artifact_name: str
    artifact_type: str  # ArtifactType.value
    score: float
    match_type: str  # "metadata", "content", or "both"
    context: str
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    project_path: Optional[Path] = None

    def __post_init__(self):
        """Validate match type."""
        valid_types = {"metadata", "content", "both"}
        if self.match_type not in valid_types:
            raise ValueError(
                f"Invalid match_type '{self.match_type}'. Must be one of {valid_types}"
            )


@dataclass
class SearchResult:
    """Result of a search operation across collection artifacts.

    Attributes:
        query: Original search query string
        matches: List of SearchMatch objects ordered by relevance score
        total_count: Total number of matches found
        search_time: Time taken to perform search in seconds
        used_ripgrep: Whether ripgrep was used for content search
        search_type: Type of search performed ("metadata", "content", or "both")
    """

    query: str
    matches: List[SearchMatch] = field(default_factory=list)
    total_count: int = 0
    search_time: float = 0.0
    used_ripgrep: bool = False
    search_type: str = "both"

    @property
    def has_matches(self) -> bool:
        """Return True if any matches were found."""
        return self.total_count > 0

    def summary(self) -> str:
        """Generate a human-readable summary of search results."""
        if not self.has_matches:
            return f"No results found for '{self.query}'"

        parts = []
        parts.append(f"{self.total_count} result{'s' if self.total_count != 1 else ''}")
        parts.append(f"in {self.search_time:.2f}s")

        if self.used_ripgrep:
            parts.append("(ripgrep)")
        else:
            parts.append("(python)")

        return " ".join(parts)


@dataclass
class ArtifactFingerprint:
    """Fingerprint for duplicate detection.

    Attributes:
        artifact_path: Path to artifact directory
        artifact_name: Name of the artifact
        artifact_type: Type of artifact (skill, command, agent)
        content_hash: SHA256 hash of all file contents
        metadata_hash: Hash of title/description
        structure_hash: Hash of file tree structure
        title: Artifact title from metadata
        description: Artifact description from metadata
        tags: List of tags from metadata
        file_count: Number of files in artifact
        total_size: Total size of all files in bytes
    """

    artifact_path: Path
    artifact_name: str
    artifact_type: str
    content_hash: str
    metadata_hash: str
    structure_hash: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    file_count: int = 0
    total_size: int = 0

    def compute_similarity(self, other: "ArtifactFingerprint") -> float:
        """Calculate similarity score (0.0 to 1.0).

        Uses weighted multi-factor comparison:
        - Content match (50%): Exact content hash match
        - Structure match (20%): File tree structure match
        - Metadata match (20%): Title, description, tag similarity
        - File count similarity (10%): Relative file count similarity

        Args:
            other: Another ArtifactFingerprint to compare

        Returns:
            Similarity score from 0.0 (no similarity) to 1.0 (identical)
        """
        score = 0.0

        # Exact content match (highest weight: 50%)
        if self.content_hash == other.content_hash:
            score += 0.5

        # Structure match (20%)
        if self.structure_hash == other.structure_hash:
            score += 0.2

        # Metadata match (20%)
        metadata_score = self._compare_metadata(other)
        score += metadata_score * 0.2

        # File count similarity (10%)
        if self.file_count > 0 and other.file_count > 0:
            count_similarity = min(self.file_count, other.file_count) / max(
                self.file_count, other.file_count
            )
            score += count_similarity * 0.1

        return score

    def _compare_metadata(self, other: "ArtifactFingerprint") -> float:
        """Compare metadata fields (0.0 to 1.0).

        Args:
            other: Another ArtifactFingerprint to compare

        Returns:
            Metadata similarity score from 0.0 to 1.0
        """
        score = 0.0
        count = 0

        # Title similarity (exact match only for simplicity)
        if self.title and other.title:
            score += 1.0 if self.title.lower() == other.title.lower() else 0.0
            count += 1

        # Description similarity (exact match)
        if self.description and other.description:
            score += (
                1.0 if self.description.lower() == other.description.lower() else 0.0
            )
            count += 1

        # Tag overlap (Jaccard similarity)
        if self.tags and other.tags:
            self_tags = set(t.lower() for t in self.tags)
            other_tags = set(t.lower() for t in other.tags)
            if self_tags or other_tags:
                jaccard = len(self_tags & other_tags) / len(self_tags | other_tags)
                score += jaccard
                count += 1

        return score / count if count > 0 else 0.0


@dataclass
class DuplicatePair:
    """Pair of potentially duplicate artifacts.

    Attributes:
        artifact1_path: Path to first artifact
        artifact1_name: Name of first artifact
        artifact2_path: Path to second artifact
        artifact2_name: Name of second artifact
        similarity_score: Similarity score (0.0 to 1.0)
        match_reasons: List of reasons why artifacts are similar
    """

    artifact1_path: Path
    artifact1_name: str
    artifact2_path: Path
    artifact2_name: str
    similarity_score: float
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class DeploymentRecord:
    """Tracks artifact deployment to a project.

    Attributes:
        name: Name of the deployed artifact
        artifact_type: Type of artifact (skill, command, agent)
        source: Source identifier (e.g., "github:user/repo/path")
        version: Version string (e.g., "1.2.0", "latest")
        sha: Content hash from collection at deployment time
        deployed_at: ISO 8601 timestamp of deployment
        deployed_from: Collection path the artifact was deployed from
    """

    name: str
    artifact_type: str  # ArtifactType.value
    source: str
    version: str
    sha: str
    deployed_at: str  # ISO 8601 timestamp
    deployed_from: str  # Path as string for TOML serialization


@dataclass
class DeploymentMetadata:
    """Metadata for .skillmeat-deployed.toml file.

    Attributes:
        collection: Name of the collection artifacts were deployed from
        deployed_at: ISO 8601 timestamp of last deployment
        skillmeat_version: SkillMeat version used for deployment
        artifacts: List of DeploymentRecord objects
    """

    collection: str
    deployed_at: str  # ISO 8601 timestamp
    skillmeat_version: str
    artifacts: List[DeploymentRecord] = field(default_factory=list)


@dataclass
class DriftDetectionResult:
    """Result of drift detection between collection and project.

    Attributes:
        artifact_name: Name of the artifact
        artifact_type: Type of artifact (skill, command, agent)
        drift_type: Type of drift detected
        collection_sha: SHA from collection (None if removed)
        project_sha: SHA from project (None if added)
        collection_version: Version in collection (None if removed)
        project_version: Version in project (None if added)
        last_deployed: ISO 8601 timestamp of last deployment (None if never deployed)
        recommendation: Recommended sync action
    """

    artifact_name: str
    artifact_type: str  # ArtifactType.value
    drift_type: Literal[
        "modified",  # Artifact modified in project only (local changes)
        "outdated",  # Artifact modified in collection only (upstream changes)
        "conflict",  # Both project and collection modified (three-way conflict)
        "added",  # Artifact added to collection (not in project)
        "removed",  # Artifact removed from collection
        "version_mismatch",  # Version changed but content may be same
    ]
    collection_sha: Optional[str] = None
    project_sha: Optional[str] = None
    collection_version: Optional[str] = None
    project_version: Optional[str] = None
    last_deployed: Optional[str] = None  # ISO 8601 timestamp
    recommendation: str = "review_manually"  # Default recommendation

    def __post_init__(self):
        """Validate drift type."""
        valid_types = {
            "modified",
            "outdated",
            "conflict",
            "added",
            "removed",
            "version_mismatch",
        }
        if self.drift_type not in valid_types:
            raise ValueError(
                f"Invalid drift_type '{self.drift_type}'. Must be one of {valid_types}"
            )


@dataclass
class ArtifactSyncResult:
    """Result of syncing individual artifact.

    Attributes:
        artifact_name: Name of the artifact
        success: True if sync succeeded
        has_conflict: True if conflicts were encountered
        error: Error message if sync failed (None if successful)
        conflict_files: List of files with conflicts
    """

    artifact_name: str
    success: bool
    has_conflict: bool = False
    error: Optional[str] = None
    conflict_files: List[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of sync operation.

    Attributes:
        status: Status of sync operation
        artifacts_synced: List of artifact names that were synced
        conflicts: List of ArtifactSyncResult for artifacts with conflicts
        message: Human-readable message about the sync
    """

    status: str  # "success", "partial", "cancelled", "no_changes", "dry_run"
    artifacts_synced: List[str] = field(default_factory=list)
    conflicts: List[Any] = field(default_factory=list)
    message: str = ""

    def __post_init__(self):
        """Validate status value."""
        valid_statuses = {"success", "partial", "cancelled", "no_changes", "dry_run"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {valid_statuses}"
            )


@dataclass
class MergeSafetyAnalysis:
    """Pre-merge safety analysis result.

    Attributes:
        can_auto_merge: Whether merge can be performed automatically
        files_to_merge: List of file paths that will be merged
        auto_mergeable_count: Number of files that can auto-merge
        conflict_count: Number of files with conflicts
        conflicts: List of conflict metadata for files requiring resolution
        warnings: List of warning messages about the merge
    """

    can_auto_merge: bool
    files_to_merge: List[str] = field(default_factory=list)
    auto_mergeable_count: int = 0
    conflict_count: int = 0
    conflicts: List[ConflictMetadata] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        """Return True if merge is safe (auto-mergeable with no conflicts)."""
        return self.can_auto_merge and self.conflict_count == 0


@dataclass
class VersionMergeResult:
    """Result of version merge operation.

    Attributes:
        success: True if merge completed successfully
        merge_result: MergeResult from merge engine (None if merge failed)
        pre_merge_snapshot_id: ID of safety snapshot created before merge
        post_merge_snapshot_id: ID of snapshot created after successful merge
        files_merged: List of file paths that were merged
        conflicts: List of conflict metadata for unresolved conflicts
        error: Error message if merge failed (None if successful)
    """

    success: bool
    merge_result: Optional[MergeResult] = None
    pre_merge_snapshot_id: Optional[str] = None
    post_merge_snapshot_id: Optional[str] = None
    files_merged: List[str] = field(default_factory=list)
    conflicts: List[ConflictMetadata] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class MergePreview:
    """Preview of merge operation without executing.

    Attributes:
        base_snapshot_id: ID of base/ancestor snapshot
        remote_snapshot_id: ID of remote snapshot to merge
        files_changed: List of file paths that differ between versions
        files_added: List of file paths added in remote
        files_removed: List of file paths removed in remote
        potential_conflicts: List of conflict metadata for potential conflicts
        can_auto_merge: Whether merge can be performed automatically
    """

    base_snapshot_id: str
    remote_snapshot_id: str
    files_changed: List[str] = field(default_factory=list)
    files_added: List[str] = field(default_factory=list)
    files_removed: List[str] = field(default_factory=list)
    potential_conflicts: List[ConflictMetadata] = field(default_factory=list)
    can_auto_merge: bool = True


@dataclass
class RollbackSafetyAnalysis:
    """Pre-rollback safety analysis result.

    Attributes:
        is_safe: True if rollback can proceed without conflicts
        snapshot_id: ID of the snapshot to rollback to
        snapshot_exists: True if snapshot was found
        local_changes_detected: Number of files changed since snapshot
        files_with_conflicts: List of file paths with potential conflicts
        files_safe_to_restore: List of file paths that can be safely restored
        files_to_merge: List of file paths requiring merge
        warnings: List of warning messages about the rollback
    """

    is_safe: bool
    snapshot_id: str
    snapshot_exists: bool = True
    local_changes_detected: int = 0
    files_with_conflicts: List[str] = field(default_factory=list)
    files_safe_to_restore: List[str] = field(default_factory=list)
    files_to_merge: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Human-readable summary of the rollback safety analysis
        """
        if not self.snapshot_exists:
            return f"Snapshot '{self.snapshot_id}' not found"

        if not self.local_changes_detected:
            return f"Safe to rollback: {len(self.files_safe_to_restore)} files (no local changes)"

        if self.is_safe:
            return (
                f"Safe to rollback: {len(self.files_safe_to_restore)} files can be restored, "
                f"{len(self.files_to_merge)} files will be merged"
            )

        return (
            f"Conflicts detected: {len(self.files_with_conflicts)} files need resolution, "
            f"{len(self.files_to_merge)} files will be merged"
        )


@dataclass
class RollbackResult:
    """Result of an intelligent rollback operation.

    Attributes:
        success: True if rollback completed successfully
        snapshot_id: ID of the snapshot rolled back to
        files_restored: List of files that were directly restored from snapshot
        files_merged: List of files where changes were preserved via merge
        conflicts: List of ConflictMetadata for files requiring manual resolution
        safety_snapshot_id: ID of pre-rollback safety snapshot (None if not created)
        error: Error message if rollback failed (None if successful)
    """

    success: bool
    snapshot_id: str
    files_restored: List[str] = field(default_factory=list)
    files_merged: List[str] = field(default_factory=list)
    conflicts: List[ConflictMetadata] = field(default_factory=list)
    safety_snapshot_id: Optional[str] = None
    error: Optional[str] = None

    @property
    def has_conflicts(self) -> bool:
        """Return True if any conflicts exist."""
        return len(self.conflicts) > 0

    @property
    def total_files(self) -> int:
        """Return total number of files processed."""
        return len(self.files_restored) + len(self.files_merged)

    def summary(self) -> str:
        """Generate a human-readable summary of the rollback."""
        if not self.success:
            return f"Rollback failed: {self.error or 'Unknown error'}"

        parts = []
        if self.files_restored:
            parts.append(f"{len(self.files_restored)} restored")
        if self.files_merged:
            parts.append(f"{len(self.files_merged)} merged")
        if self.conflicts:
            parts.append(f"{len(self.conflicts)} conflicts")

        summary = ", ".join(parts) if parts else "No changes"

        if self.has_conflicts:
            summary += " (manual resolution required)"

        return summary


@dataclass
class SyncMergeStrategy:
    """Configuration for sync merge behavior.

    Attributes:
        direction: Direction of sync operation
        auto_merge: Attempt auto-merge for conflicts (default True)
        prefer_source: If conflict, prefer source (incoming) version
        prefer_target: If conflict, prefer target (current) version
        create_backup: Create snapshot before sync (default True)
        skip_conflicts: Skip conflicting files instead of failing
        conflict_action: How to handle conflicts (fail/skip/prompt/auto)
    """

    direction: SyncDirection
    auto_merge: bool = True
    prefer_source: bool = False
    prefer_target: bool = False
    create_backup: bool = True
    skip_conflicts: bool = False
    conflict_action: Literal["fail", "skip", "prompt", "auto"] = "prompt"

    def __post_init__(self):
        """Validate strategy configuration."""
        # Can't prefer both source and target
        if self.prefer_source and self.prefer_target:
            raise ValueError(
                "Cannot prefer both source and target - choose one or neither"
            )

        # Validate conflict_action
        valid_actions = {"fail", "skip", "prompt", "auto"}
        if self.conflict_action not in valid_actions:
            raise ValueError(
                f"Invalid conflict_action '{self.conflict_action}'. "
                f"Must be one of {valid_actions}"
            )


@dataclass
class PaginatedSnapshots:
    """Paginated snapshot listing result.

    Attributes:
        items: List of Snapshot objects for current page
        next_cursor: Cursor for next page (None if no more results)
        has_more: True if more snapshots exist after this page
        total_count: Total number of snapshots (None if not computed)
    """

    items: List["Snapshot"] = field(default_factory=list)
    next_cursor: Optional[str] = None
    has_more: bool = False
    total_count: Optional[int] = None


@dataclass
class RollbackAuditEntry:
    """Audit trail entry for a rollback operation.

    Records detailed metadata about rollback operations for debugging and history
    tracking. Used by RollbackAuditTrail to maintain per-collection audit logs.

    Attributes:
        id: Unique ID for this audit entry (e.g., "rb_20241216_123456")
        timestamp: When this rollback occurred
        collection_name: Name of the collection that was rolled back
        source_snapshot_id: Snapshot we rolled back FROM (safety snapshot)
        target_snapshot_id: Snapshot we rolled back TO
        operation_type: Type of rollback performed
        files_restored: List of files directly restored from snapshot
        files_merged: List of files merged to preserve changes
        conflicts_resolved: List of conflict files successfully resolved
        conflicts_pending: List of conflict files requiring manual resolution
        preserve_changes_enabled: Whether intelligent rollback was used
        selective_paths: List of selective file paths (None = full rollback)
        success: True if rollback completed successfully
        error: Error message if rollback failed (None if successful)
        metadata: Additional metadata for debugging or extensions
    """

    id: str
    timestamp: datetime
    collection_name: str
    source_snapshot_id: str
    target_snapshot_id: str
    operation_type: Literal["simple", "intelligent", "selective"]
    files_restored: List[str] = field(default_factory=list)
    files_merged: List[str] = field(default_factory=list)
    conflicts_resolved: List[str] = field(default_factory=list)
    conflicts_pending: List[str] = field(default_factory=list)
    preserve_changes_enabled: bool = False
    selective_paths: Optional[List[str]] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for TOML serialization
        """
        data = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "collection_name": self.collection_name,
            "source_snapshot_id": self.source_snapshot_id,
            "target_snapshot_id": self.target_snapshot_id,
            "operation_type": self.operation_type,
            "files_restored": self.files_restored,
            "files_merged": self.files_merged,
            "conflicts_resolved": self.conflicts_resolved,
            "conflicts_pending": self.conflicts_pending,
            "preserve_changes_enabled": self.preserve_changes_enabled,
            "success": self.success,
        }

        # Add optional fields only if they're not None (TOML doesn't support None)
        if self.selective_paths is not None:
            data["selective_paths"] = self.selective_paths
        if self.error is not None:
            data["error"] = self.error
        if self.metadata:
            data["metadata"] = self.metadata

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RollbackAuditEntry":
        """Create from dictionary.

        Args:
            data: Dictionary representation (typically from TOML)

        Returns:
            RollbackAuditEntry instance
        """
        # Parse timestamp back to datetime
        timestamp_str = data.get("timestamp")
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        else:
            timestamp = timestamp_str  # Already datetime

        return cls(
            id=data["id"],
            timestamp=timestamp,
            collection_name=data["collection_name"],
            source_snapshot_id=data["source_snapshot_id"],
            target_snapshot_id=data["target_snapshot_id"],
            operation_type=data["operation_type"],
            files_restored=data.get("files_restored", []),
            files_merged=data.get("files_merged", []),
            conflicts_resolved=data.get("conflicts_resolved", []),
            conflicts_pending=data.get("conflicts_pending", []),
            preserve_changes_enabled=data.get("preserve_changes_enabled", False),
            selective_paths=data.get("selective_paths"),
            success=data.get("success", True),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )
