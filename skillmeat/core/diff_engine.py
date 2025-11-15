"""Diff engine for comparing artifacts during update/sync operations.

This module provides comprehensive diff capabilities for comparing files
and directories, detecting changes, and generating unified diffs.
"""

import difflib
import fnmatch
import hashlib
from pathlib import Path
from typing import List, Optional, Set

from ..models import FileDiff, DiffResult


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
        self, base_path: Path, local_path: Path, upstream_path: Path
    ) -> None:
        """Perform three-way diff for merge conflict detection.

        Args:
            base_path: Base/original version path
            local_path: Local modified version path
            upstream_path: Upstream modified version path

        Raises:
            NotImplementedError: Will be implemented in Phase 1 P1-002
        """
        raise NotImplementedError(
            "DiffEngine.three_way_diff() will be implemented in Phase 1 P1-002"
        )
