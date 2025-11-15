"""Data models for SkillMeat.

This module contains dataclasses and models used throughout the SkillMeat
application for representing artifacts, diffs, and other core entities.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict


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
