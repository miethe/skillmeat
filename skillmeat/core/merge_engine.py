"""Merge engine for combining three-way diffs with conflict resolution.

This module provides the MergeEngine class for performing intelligent merges
of file changes, automatically resolving simple cases and generating Git-style
conflict markers for complex conflicts.
"""

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from ..models import (
    ConflictMetadata,
    MergeResult,
    MergeStats,
    ThreeWayDiffResult,
)
from .diff_engine import DiffEngine


class MergeEngine:
    """Engine for merging file changes with conflict detection.

    The MergeEngine takes the output of a three-way diff and performs the
    actual merge operation, auto-merging simple cases and generating conflict
    markers for files that require manual resolution.

    Auto-merge strategies:
        - use_local: Copy local version to output
        - use_remote: Copy remote version to output
        - use_base: Copy base version to output
        - manual: Generate conflict markers (text) or flag conflict (binary)

    Example:
        >>> engine = MergeEngine()
        >>> result = engine.merge(
        ...     base_path=Path("base"),
        ...     local_path=Path("local"),
        ...     remote_path=Path("remote"),
        ...     output_path=Path("merged")
        ... )
        >>> if result.success:
        ...     print(f"Auto-merged {len(result.auto_merged)} files")
        ... else:
        ...     print(f"Conflicts in {len(result.conflicts)} files")
    """

    def __init__(self, ignore_patterns: Optional[List[str]] = None):
        """Initialize merge engine.

        Args:
            ignore_patterns: Optional list of patterns to ignore during merge
        """
        self.diff_engine = DiffEngine()
        self.ignore_patterns = ignore_patterns or []

    def merge(
        self,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        output_path: Optional[Path] = None,
    ) -> MergeResult:
        """Merge three versions of files/directories.

        Performs three-way merge using the DiffEngine to identify changes,
        then auto-merges simple cases and generates conflict markers for
        complex conflicts.

        Args:
            base_path: Path to base/ancestor version (common ancestor)
            local_path: Path to local modified version
            remote_path: Path to remote/upstream modified version
            output_path: Optional path to write merged results

        Returns:
            MergeResult with merge status, conflicts, and statistics

        Raises:
            FileNotFoundError: If any path doesn't exist
            NotADirectoryError: If any path is not a directory

        Example:
            >>> engine = MergeEngine()
            >>> result = engine.merge(
            ...     Path("base"), Path("local"), Path("remote"), Path("output")
            ... )
            >>> print(result.summary())
            "Merge successful: 10 files auto-merged"
        """
        # First perform three-way diff to identify conflicts
        diff_result = self.diff_engine.three_way_diff(
            base_path, local_path, remote_path, self.ignore_patterns
        )

        # Initialize result
        result = MergeResult(success=False)
        stats = MergeStats()

        # Count total files
        stats.total_files = len(diff_result.auto_mergeable) + len(diff_result.conflicts)

        # If output_path provided, create it
        if output_path:
            output_path.mkdir(parents=True, exist_ok=True)
            result.output_path = output_path

        # Process auto-mergeable files
        # For these, we need to re-analyze to get the metadata
        for file_path in diff_result.auto_mergeable:
            metadata = self.diff_engine._analyze_three_way_file(
                file_path, base_path, local_path, remote_path, self.ignore_patterns
            )
            if metadata and metadata.auto_mergeable:
                self._auto_merge_file(
                    metadata, base_path, local_path, remote_path, output_path
                )
                result.auto_merged.append(file_path)
                stats.auto_merged += 1

        # Process conflicts
        for metadata in diff_result.conflicts:
            if metadata.is_binary:
                # Binary conflict - cannot merge
                result.conflicts.append(metadata)
                stats.conflicts += 1
                stats.binary_conflicts += 1
            else:
                # Text conflict - generate markers
                self._handle_text_conflict(
                    metadata, base_path, local_path, remote_path, output_path
                )
                result.conflicts.append(metadata)
                stats.conflicts += 1

        # Set success based on whether we have conflicts
        result.success = len(result.conflicts) == 0
        result.stats = stats

        return result

    def merge_files(
        self,
        base_file: Path,
        local_file: Path,
        remote_file: Path,
        output_file: Optional[Path] = None,
    ) -> MergeResult:
        """Merge three versions of a single file.

        Convenience method for merging individual files instead of directories.
        Returns merged content in the result.

        Args:
            base_file: Path to base/ancestor version
            local_file: Path to local modified version
            remote_file: Path to remote/upstream modified version
            output_file: Optional path to write merged result

        Returns:
            MergeResult with merged_content populated

        Example:
            >>> result = engine.merge_files(
            ...     Path("base/file.txt"),
            ...     Path("local/file.txt"),
            ...     Path("remote/file.txt")
            ... )
            >>> if result.success:
            ...     print(result.merged_content)
        """
        # Create temporary directories for the three versions
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir) / "base"
            tmp_local = Path(tmpdir) / "local"
            tmp_remote = Path(tmpdir) / "remote"
            tmp_output = Path(tmpdir) / "output"

            for path in [tmp_base, tmp_local, tmp_remote, tmp_output]:
                path.mkdir()

            # Copy files to temporary directories
            filename = base_file.name if base_file.exists() else local_file.name
            if base_file.exists():
                shutil.copy2(base_file, tmp_base / filename)
            if local_file.exists():
                shutil.copy2(local_file, tmp_local / filename)
            if remote_file.exists():
                shutil.copy2(remote_file, tmp_remote / filename)

            # Perform merge
            result = self.merge(tmp_base, tmp_local, tmp_remote, tmp_output)

            # Read merged content if it was written
            merged_file = tmp_output / filename
            if merged_file.exists():
                try:
                    result.merged_content = merged_file.read_text(encoding="utf-8")
                except Exception:
                    # Binary file
                    result.merged_content = None

                # If output_file specified, copy the result
                if output_file:
                    shutil.copy2(merged_file, output_file)
                    result.output_path = output_file

            return result

    def _auto_merge_file(
        self,
        metadata: ConflictMetadata,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        output_path: Optional[Path],
    ) -> None:
        """Auto-merge a file using the recommended strategy.

        Args:
            metadata: Conflict metadata with merge strategy
            base_path: Base directory path
            local_path: Local directory path
            remote_path: Remote directory path
            output_path: Output directory path (optional)
        """
        if not output_path:
            return

        # Determine source based on merge strategy
        if metadata.merge_strategy == "use_local":
            source_path = local_path / metadata.file_path
        elif metadata.merge_strategy == "use_remote":
            source_path = remote_path / metadata.file_path
        elif metadata.merge_strategy == "use_base":
            source_path = base_path / metadata.file_path
        else:
            # Should not reach here for auto-mergeable files
            return

        # Copy file to output (if it exists)
        if source_path.exists():
            dest_path = output_path / metadata.file_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Use atomic write via temporary file
            self._atomic_copy(source_path, dest_path)

    def _handle_text_conflict(
        self,
        metadata: ConflictMetadata,
        base_path: Path,
        local_path: Path,
        remote_path: Path,
        output_path: Optional[Path],
    ) -> None:
        """Handle text file conflict by generating conflict markers.

        Args:
            metadata: Conflict metadata
            base_path: Base directory path
            local_path: Local directory path
            remote_path: Remote directory path
            output_path: Output directory path (optional)
        """
        if not output_path:
            return

        # Generate conflict markers
        conflict_content = self._generate_conflict_markers(metadata)

        # Write to output
        dest_path = output_path / metadata.file_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Use atomic write
        self._atomic_write(dest_path, conflict_content)

    def _generate_conflict_markers(self, conflict: ConflictMetadata) -> str:
        """Generate Git-style conflict markers for a file.

        Creates a merged file with conflict markers showing both versions:
            <<<<<<< LOCAL (current)
            [local content]
            =======
            [remote content]
            >>>>>>> REMOTE (incoming)

        Args:
            conflict: ConflictMetadata with local and remote content

        Returns:
            String with conflict markers

        Example:
            >>> markers = engine._generate_conflict_markers(conflict)
            >>> print(markers)
            <<<<<<< LOCAL (current)
            local changes
            =======
            remote changes
            >>>>>>> REMOTE (incoming)
        """
        lines = []

        # Start conflict marker
        lines.append("<<<<<<< LOCAL (current)")

        # Local content (or indicate deletion)
        if conflict.local_content is not None:
            # Remove trailing newline if present to avoid double newlines
            local = conflict.local_content.rstrip("\n")
            if local:
                lines.append(local)
        else:
            lines.append("(file deleted)")

        # Separator
        lines.append("=======")

        # Remote content (or indicate deletion)
        if conflict.remote_content is not None:
            # Remove trailing newline if present
            remote = conflict.remote_content.rstrip("\n")
            if remote:
                lines.append(remote)
        else:
            lines.append("(file deleted)")

        # End conflict marker
        lines.append(">>>>>>> REMOTE (incoming)")

        return "\n".join(lines) + "\n"

    def _atomic_copy(self, source: Path, dest: Path) -> None:
        """Copy file atomically using temporary file and rename.

        Args:
            source: Source file path
            dest: Destination file path
        """
        # Create temporary file in same directory as destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp"
        )

        try:
            # Copy content
            with open(tmp_fd, "wb") as tmp_file:
                with open(source, "rb") as src_file:
                    shutil.copyfileobj(src_file, tmp_file)

            # Atomic rename
            tmp_path_obj = Path(tmp_path)
            tmp_path_obj.replace(dest)
        except Exception:
            # Clean up temp file on error
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass
            raise

    def _atomic_write(self, dest: Path, content: str) -> None:
        """Write content atomically using temporary file and rename.

        Args:
            dest: Destination file path
            content: Content to write
        """
        # Create temporary file in same directory as destination
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp"
        )

        try:
            # Write content
            with open(tmp_fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(content)

            # Atomic rename
            tmp_path_obj = Path(tmp_path)
            tmp_path_obj.replace(dest)
        except Exception:
            # Clean up temp file on error
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass
            raise
