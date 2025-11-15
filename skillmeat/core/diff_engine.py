"""Diff engine for comparing artifacts during update/sync operations.

This module provides comprehensive diff capabilities for comparing files
and directories, detecting changes, and generating unified diffs.
"""

import difflib
import fnmatch
import hashlib
from pathlib import Path
from typing import List, Optional, Set

from ..models import (
    FileDiff,
    DiffResult,
    ConflictMetadata,
    ThreeWayDiffResult,
    DiffStats,
)


# Default patterns to ignore during directory comparison
DEFAULT_IGNORE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".gitignore",
    "node_modules",
    ".DS_Store",
    "*.swp",
    "*.swo",
    "*.swn",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "*.egg-info",
    "dist",
    "build",
]


class DiffEngine:
    """Engine for comparing files and directories.

    This class provides methods to:
    - Compare individual files (text and binary)
    - Compare directory structures recursively
    - Generate unified diffs for text files
    - Respect ignore patterns (gitignore-style)
    - Provide detailed statistics on changes
    """

    def __init__(self):
        """Initialize the DiffEngine."""
        pass

    def diff_files(self, source_file: Path, target_file: Path) -> FileDiff:
        """Compare two individual files.

        Detects whether files are text or binary and generates appropriate
        diff information. For text files, creates unified diff. For binary
        files, only reports if they differ.

        Args:
            source_file: Path to source file
            target_file: Path to target file

        Returns:
            FileDiff object containing comparison results

        Raises:
            FileNotFoundError: If either file doesn't exist
        """
        # Validate files exist
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        if not target_file.exists():
            raise FileNotFoundError(f"Target file not found: {target_file}")

        # Get relative path (use target file name)
        rel_path = target_file.name

        # Check if files are identical using hash comparison (fast path)
        if self._files_identical(source_file, target_file):
            return FileDiff(
                path=rel_path,
                status="unchanged",
                lines_added=0,
                lines_removed=0,
                unified_diff=None,
            )

        # Determine if files are text or binary
        is_source_text = self._is_text_file(source_file)
        is_target_text = self._is_text_file(target_file)

        # If either file is binary, can't generate unified diff
        if not is_source_text or not is_target_text:
            return FileDiff(
                path=rel_path,
                status="binary",
                lines_added=0,
                lines_removed=0,
                unified_diff="Binary files differ",
            )

        # Generate unified diff for text files
        try:
            with open(source_file, "r", encoding="utf-8", errors="replace") as f:
                source_lines = f.readlines()
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                target_lines = f.readlines()

            # Generate unified diff
            diff = difflib.unified_diff(
                source_lines,
                target_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                lineterm="",
            )
            diff_text = "\n".join(diff)

            # Count added and removed lines
            lines_added = 0
            lines_removed = 0
            for line in diff_text.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    lines_added += 1
                elif line.startswith("-") and not line.startswith("---"):
                    lines_removed += 1

            return FileDiff(
                path=rel_path,
                status="modified",
                lines_added=lines_added,
                lines_removed=lines_removed,
                unified_diff=diff_text if diff_text else None,
            )

        except Exception as e:
            # If we can't read as text, treat as binary
            return FileDiff(
                path=rel_path,
                status="binary",
                lines_added=0,
                lines_removed=0,
                unified_diff=f"Error reading files: {str(e)}",
            )

    def diff_directories(
        self,
        source_path: Path,
        target_path: Path,
        ignore_patterns: Optional[List[str]] = None,
    ) -> DiffResult:
        """Compare two directory structures recursively.

        Identifies files that are added, removed, modified, or unchanged.
        Respects ignore patterns (gitignore-style) to skip certain files
        and directories.

        Args:
            source_path: Source directory path
            target_path: Target directory path
            ignore_patterns: Optional list of patterns to ignore (extends defaults)

        Returns:
            DiffResult object containing comprehensive comparison results

        Raises:
            NotADirectoryError: If either path is not a directory
            FileNotFoundError: If either directory doesn't exist
        """
        # Validate directories exist
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_path}")
        if not target_path.exists():
            raise FileNotFoundError(f"Target directory not found: {target_path}")

        if not source_path.is_dir():
            raise NotADirectoryError(f"Source path is not a directory: {source_path}")
        if not target_path.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {target_path}")

        # Merge ignore patterns with defaults
        patterns = DEFAULT_IGNORE_PATTERNS.copy()
        if ignore_patterns:
            patterns.extend(ignore_patterns)

        # Build file sets for both directories
        source_files = self._collect_files(source_path, patterns)
        target_files = self._collect_files(target_path, patterns)

        # Initialize result
        result = DiffResult(source_path=source_path, target_path=target_path)

        # Find added files (in target but not in source)
        added_files = target_files - source_files
        result.files_added = sorted(added_files)

        # Find removed files (in source but not in target)
        removed_files = source_files - target_files
        result.files_removed = sorted(removed_files)

        # Find potentially modified files (in both)
        common_files = source_files & target_files

        # Compare each common file
        for rel_path in sorted(common_files):
            source_file = source_path / rel_path
            target_file = target_path / rel_path

            # Skip if either path is not a file (e.g., became a directory)
            if not source_file.is_file() or not target_file.is_file():
                continue

            try:
                file_diff = self.diff_files(source_file, target_file)

                # Update path to use relative path
                file_diff.path = rel_path

                if file_diff.status == "unchanged":
                    result.files_unchanged.append(rel_path)
                else:
                    result.files_modified.append(file_diff)
                    result.total_lines_added += file_diff.lines_added
                    result.total_lines_removed += file_diff.lines_removed

            except Exception:
                # If comparison fails, skip this file
                continue

        return result

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if a file is text (not binary).

        Uses null byte detection - if file contains null bytes in the first
        8KB, it's considered binary.

        Args:
            file_path: Path to file to check

        Returns:
            True if file appears to be text, False if binary
        """
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(8192)

            # Check for null bytes (strong indicator of binary)
            if b"\x00" in chunk:
                return False

            # Check if chunk is valid UTF-8
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                # Try other common encodings
                try:
                    chunk.decode("latin-1")
                    return True
                except UnicodeDecodeError:
                    return False

        except Exception:
            return False

    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files are identical using hash comparison.

        This is faster than reading full content for large files.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if files are identical, False otherwise
        """
        # Quick check: if sizes differ, files are different
        if file1.stat().st_size != file2.stat().st_size:
            return False

        # Compare using SHA-256 hash
        return self._file_hash(file1) == self._file_hash(file2)

    def _file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _should_ignore(self, path: Path, base_path: Path, patterns: List[str]) -> bool:
        """Check if a path should be ignored based on patterns.

        Supports gitignore-style patterns using fnmatch.

        Args:
            path: Path to check
            base_path: Base directory path (for relative path calculation)
            patterns: List of patterns to match against

        Returns:
            True if path should be ignored, False otherwise
        """
        # Get relative path components
        try:
            rel_path = path.relative_to(base_path)
        except ValueError:
            # If path is not relative to base_path, don't ignore
            return False

        # Check path components and full path against patterns
        parts = rel_path.parts
        for pattern in patterns:
            # Check if any directory component matches
            for part in parts:
                if fnmatch.fnmatch(part, pattern):
                    return True

            # Check full relative path
            if fnmatch.fnmatch(str(rel_path), pattern):
                return True
            if fnmatch.fnmatch(str(rel_path), f"*/{pattern}"):
                return True
            if fnmatch.fnmatch(str(rel_path), f"{pattern}/*"):
                return True

        return False

    def _collect_files(self, directory: Path, ignore_patterns: List[str]) -> Set[str]:
        """Collect all files in a directory recursively.

        Respects ignore patterns and returns relative paths.

        Args:
            directory: Directory to scan
            ignore_patterns: Patterns to ignore

        Returns:
            Set of relative file paths
        """
        files = set()

        for item in directory.rglob("*"):
            # Skip if should be ignored
            if self._should_ignore(item, directory, ignore_patterns):
                continue

            # Only include files, not directories
            if item.is_file():
                try:
                    rel_path = str(item.relative_to(directory))
                    files.add(rel_path)
                except ValueError:
                    continue

        return files

    def three_way_diff(
        self,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        ignore_patterns: Optional[List[str]] = None,
    ) -> ThreeWayDiffResult:
        """Perform three-way diff for merge conflict detection.

        Compares base, local, and remote versions to identify:
        - Auto-mergeable changes (only one version changed)
        - Conflicts requiring manual resolution (both versions changed)
        - Deletions and additions

        Three-way diff logic:
        - If base == local == remote: NO CHANGE (unchanged)
        - If base == local, remote changed: AUTO-MERGE (use remote)
        - If base == remote, local changed: AUTO-MERGE (use local)
        - If base != local != remote: CONFLICT (manual resolution)
        - If file deleted in one version: CONFLICT (user decides)
        - If file added in both with different content: CONFLICT

        Args:
            base_path: Path to base/ancestor version (common ancestor)
            local_path: Path to local modified version
            remote_path: Path to remote/upstream modified version
            ignore_patterns: Optional list of patterns to ignore (extends defaults)

        Returns:
            ThreeWayDiffResult with auto_mergeable files and conflicts

        Raises:
            FileNotFoundError: If any path doesn't exist
            NotADirectoryError: If any path is not a directory

        Example:
            >>> engine = DiffEngine()
            >>> result = engine.three_way_diff(
            ...     Path("base"), Path("local"), Path("remote")
            ... )
            >>> print(f"Auto-mergeable: {len(result.auto_mergeable)}")
            >>> print(f"Conflicts: {len(result.conflicts)}")
        """
        # Validate paths exist
        for path, name in [
            (base_path, "base"),
            (local_path, "local"),
            (remote_path, "remote"),
        ]:
            if not path.exists():
                raise FileNotFoundError(f"{name.capitalize()} path not found: {path}")
            if not path.is_dir():
                raise NotADirectoryError(
                    f"{name.capitalize()} path is not a directory: {path}"
                )

        # Merge ignore patterns with defaults
        patterns = DEFAULT_IGNORE_PATTERNS.copy()
        if ignore_patterns:
            patterns.extend(ignore_patterns)

        # Collect files from all three versions
        base_files = self._collect_files(base_path, patterns)
        local_files = self._collect_files(local_path, patterns)
        remote_files = self._collect_files(remote_path, patterns)

        # Get all unique files across all versions
        all_files = base_files | local_files | remote_files

        # Initialize result
        result = ThreeWayDiffResult(
            base_path=base_path, local_path=local_path, remote_path=remote_path
        )

        stats = DiffStats()
        stats.files_compared = len(all_files)

        # Analyze each file
        for rel_path in sorted(all_files):
            conflict_or_merge = self._analyze_three_way_file(
                rel_path, base_path, local_path, remote_path, patterns
            )

            if conflict_or_merge is None:
                # No change
                stats.files_unchanged += 1
            elif isinstance(conflict_or_merge, ConflictMetadata):
                # Conflict detected
                if conflict_or_merge.auto_mergeable:
                    result.auto_mergeable.append(rel_path)
                    stats.auto_mergeable += 1
                    stats.files_changed += 1
                else:
                    result.conflicts.append(conflict_or_merge)
                    stats.files_conflicted += 1
            else:
                # Should not reach here
                pass

        result.stats = stats
        return result

    def _analyze_three_way_file(
        self,
        rel_path: str,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        ignore_patterns: List[str],
    ) -> Optional[ConflictMetadata]:
        """Analyze a single file in three-way diff.

        Args:
            rel_path: Relative path to the file
            base_path: Base directory path
            local_path: Local directory path
            remote_path: Remote directory path
            ignore_patterns: Patterns to ignore

        Returns:
            ConflictMetadata if changes/conflicts detected, None if unchanged
        """
        base_file = base_path / rel_path
        local_file = local_path / rel_path
        remote_file = remote_path / rel_path

        # Check which versions exist
        base_exists = base_file.exists() and base_file.is_file()
        local_exists = local_file.exists() and local_file.is_file()
        remote_exists = remote_file.exists() and remote_file.is_file()

        # Case 1: File doesn't exist in base (newly added)
        if not base_exists:
            if local_exists and remote_exists:
                # Added in both versions - check if identical
                if self._files_identical(local_file, remote_file):
                    # Same content added in both - auto-merge
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="add_add",
                        base_content=None,
                        local_content=self._read_file_safe(local_file),
                        remote_content=self._read_file_safe(remote_file),
                        auto_mergeable=True,
                        merge_strategy="use_local",  # Both are same
                        is_binary=not self._is_text_file(local_file),
                    )
                else:
                    # Different content added - conflict
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="add_add",
                        base_content=None,
                        local_content=self._read_file_safe(local_file),
                        remote_content=self._read_file_safe(remote_file),
                        auto_mergeable=False,
                        merge_strategy="manual",
                        is_binary=not self._is_text_file(local_file),
                    )
            elif local_exists and not remote_exists:
                # Only added locally - auto-merge (use local)
                return ConflictMetadata(
                    file_path=rel_path,
                    conflict_type="content",
                    base_content=None,
                    local_content=self._read_file_safe(local_file),
                    remote_content=None,
                    auto_mergeable=True,
                    merge_strategy="use_local",
                    is_binary=not self._is_text_file(local_file),
                )
            elif remote_exists and not local_exists:
                # Only added remotely - auto-merge (use remote)
                return ConflictMetadata(
                    file_path=rel_path,
                    conflict_type="content",
                    base_content=None,
                    local_content=None,
                    remote_content=self._read_file_safe(remote_file),
                    auto_mergeable=True,
                    merge_strategy="use_remote",
                    is_binary=not self._is_text_file(remote_file),
                )
            else:
                # Should not happen (file in all_files but doesn't exist anywhere)
                return None

        # Case 2: File exists in base
        else:
            base_content = self._read_file_safe(base_file)
            local_content = self._read_file_safe(local_file) if local_exists else None
            remote_content = (
                self._read_file_safe(remote_file) if remote_exists else None
            )

            # Check if binary
            is_binary = not self._is_text_file(base_file)

            # Sub-case: File deleted in both versions
            if not local_exists and not remote_exists:
                # Both deleted - auto-merge (delete)
                return ConflictMetadata(
                    file_path=rel_path,
                    conflict_type="deletion",
                    base_content=base_content,
                    local_content=None,
                    remote_content=None,
                    auto_mergeable=True,
                    merge_strategy="use_local",  # Both agree on deletion
                    is_binary=is_binary,
                )

            # Sub-case: File deleted locally but modified remotely
            if not local_exists and remote_exists:
                if self._files_identical(base_file, remote_file):
                    # Remote unchanged, local deleted - auto-merge (delete)
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="deletion",
                        base_content=base_content,
                        local_content=None,
                        remote_content=remote_content,
                        auto_mergeable=True,
                        merge_strategy="use_local",
                        is_binary=is_binary,
                    )
                else:
                    # Remote modified, local deleted - conflict
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="deletion",
                        base_content=base_content,
                        local_content=None,
                        remote_content=remote_content,
                        auto_mergeable=False,
                        merge_strategy="manual",
                        is_binary=is_binary,
                    )

            # Sub-case: File deleted remotely but modified locally
            if not remote_exists and local_exists:
                if self._files_identical(base_file, local_file):
                    # Local unchanged, remote deleted - auto-merge (delete)
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="deletion",
                        base_content=base_content,
                        local_content=local_content,
                        remote_content=None,
                        auto_mergeable=True,
                        merge_strategy="use_remote",
                        is_binary=is_binary,
                    )
                else:
                    # Local modified, remote deleted - conflict
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="deletion",
                        base_content=base_content,
                        local_content=local_content,
                        remote_content=None,
                        auto_mergeable=False,
                        merge_strategy="manual",
                        is_binary=is_binary,
                    )

            # Sub-case: File exists in all three versions
            if local_exists and remote_exists:
                # Check all three for equality
                base_local_same = self._files_identical(base_file, local_file)
                base_remote_same = self._files_identical(base_file, remote_file)
                local_remote_same = self._files_identical(local_file, remote_file)

                # No changes at all
                if base_local_same and base_remote_same:
                    return None

                # Only remote changed
                if base_local_same and not base_remote_same:
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="content",
                        base_content=base_content,
                        local_content=local_content,
                        remote_content=remote_content,
                        auto_mergeable=True,
                        merge_strategy="use_remote",
                        is_binary=is_binary,
                    )

                # Only local changed
                if base_remote_same and not base_local_same:
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="content",
                        base_content=base_content,
                        local_content=local_content,
                        remote_content=remote_content,
                        auto_mergeable=True,
                        merge_strategy="use_local",
                        is_binary=is_binary,
                    )

                # Both changed - check if they changed to the same thing
                if local_remote_same:
                    # Both changed identically - auto-merge
                    return ConflictMetadata(
                        file_path=rel_path,
                        conflict_type="both_modified",
                        base_content=base_content,
                        local_content=local_content,
                        remote_content=remote_content,
                        auto_mergeable=True,
                        merge_strategy="use_local",  # Both are same
                        is_binary=is_binary,
                    )

                # Both changed differently - conflict
                return ConflictMetadata(
                    file_path=rel_path,
                    conflict_type="both_modified",
                    base_content=base_content,
                    local_content=local_content,
                    remote_content=remote_content,
                    auto_mergeable=False,
                    merge_strategy="manual",
                    is_binary=is_binary,
                )

        return None

    def _read_file_safe(self, file_path: Path) -> Optional[str]:
        """Safely read file content, returning None for binary files.

        Args:
            file_path: Path to file

        Returns:
            File content as string, or None if binary or unreadable
        """
        if not file_path.exists():
            return None

        try:
            # Check if binary first
            if not self._is_text_file(file_path):
                return None

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None
