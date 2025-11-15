"""Data models for SkillMeat.

This module contains dataclasses and models used throughout the SkillMeat
application for representing artifacts, diffs, and other core entities.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Literal


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
