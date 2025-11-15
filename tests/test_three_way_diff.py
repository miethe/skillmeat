#!/usr/bin/env python3
"""Tests for three-way diff functionality in DiffEngine.

This module tests the three-way diff capability for merge conflict detection,
including auto-mergeable changes and manual conflict scenarios.
"""

import pytest
from pathlib import Path

from skillmeat.core.diff_engine import DiffEngine
from skillmeat.models import ConflictMetadata, ThreeWayDiffResult


class TestThreeWayDiffBasic:
    """Basic three-way diff functionality tests."""

    def test_no_changes(self, tmp_path):
        """Test when all three versions are identical."""
        engine = DiffEngine()

        # Create identical directories
        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "file.txt").write_text("Same content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 0
        assert result.stats.files_unchanged == 1
        assert result.can_auto_merge is True
        assert result.has_conflicts is False

    def test_only_remote_changed(self, tmp_path):
        """Test auto-merge when only remote version changed."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Base and local are identical, remote changed
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Original content\n")
        (remote / "file.txt").write_text("Modified content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "file.txt" in result.auto_mergeable
        assert len(result.conflicts) == 0
        assert result.stats.auto_mergeable == 1
        assert result.can_auto_merge is True

        # Check merge strategy
        assert len(result.conflicts) == 0  # Should be in auto_mergeable

    def test_only_local_changed(self, tmp_path):
        """Test auto-merge when only local version changed."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Base and remote are identical, local changed
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Modified content\n")
        (remote / "file.txt").write_text("Original content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "file.txt" in result.auto_mergeable
        assert len(result.conflicts) == 0
        assert result.stats.auto_mergeable == 1

    def test_both_changed_identically(self, tmp_path):
        """Test auto-merge when both changed to same content."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Both changed to the same thing
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Modified content\n")
        (remote / "file.txt").write_text("Modified content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "file.txt" in result.auto_mergeable
        assert len(result.conflicts) == 0
        assert result.stats.auto_mergeable == 1

    def test_both_changed_differently(self, tmp_path):
        """Test conflict when both changed to different content."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Both changed differently
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Local modification\n")
        (remote / "file.txt").write_text("Remote modification\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 1
        assert result.stats.files_conflicted == 1
        assert result.has_conflicts is True
        assert result.can_auto_merge is False

        conflict = result.conflicts[0]
        assert conflict.file_path == "file.txt"
        assert conflict.conflict_type == "both_modified"
        assert conflict.auto_mergeable is False
        assert conflict.merge_strategy == "manual"


class TestThreeWayDiffDeletions:
    """Tests for file deletion scenarios."""

    def test_deleted_in_both(self, tmp_path):
        """Test auto-merge when file deleted in both versions."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # File exists in base, deleted in both local and remote
        (base / "file.txt").write_text("Content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "file.txt" in result.auto_mergeable
        assert len(result.conflicts) == 0

    def test_deleted_locally_unchanged_remotely(self, tmp_path):
        """Test auto-merge when deleted locally and remote unchanged."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # File in base and remote (unchanged), deleted locally
        (base / "file.txt").write_text("Content\n")
        (remote / "file.txt").write_text("Content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "file.txt" in result.auto_mergeable
        assert len(result.conflicts) == 0

    def test_deleted_locally_modified_remotely(self, tmp_path):
        """Test conflict when deleted locally but modified remotely."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Deleted locally, modified remotely
        (base / "file.txt").write_text("Original\n")
        (remote / "file.txt").write_text("Modified\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 1
        assert result.has_conflicts is True

        conflict = result.conflicts[0]
        assert conflict.file_path == "file.txt"
        assert conflict.conflict_type == "deletion"
        assert conflict.auto_mergeable is False
        assert conflict.local_content is None
        assert conflict.remote_content is not None

    def test_modified_locally_deleted_remotely(self, tmp_path):
        """Test conflict when modified locally but deleted remotely."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Modified locally, deleted remotely
        (base / "file.txt").write_text("Original\n")
        (local / "file.txt").write_text("Modified\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 1

        conflict = result.conflicts[0]
        assert conflict.conflict_type == "deletion"
        assert conflict.local_content is not None
        assert conflict.remote_content is None

    def test_deleted_remotely_unchanged_locally(self, tmp_path):
        """Test auto-merge when deleted remotely and local unchanged."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # File in base and local (unchanged), deleted remotely
        (base / "file.txt").write_text("Content\n")
        (local / "file.txt").write_text("Content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "file.txt" in result.auto_mergeable


class TestThreeWayDiffAdditions:
    """Tests for file addition scenarios."""

    def test_added_only_locally(self, tmp_path):
        """Test auto-merge when file added only locally."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # File only in local
        (local / "new.txt").write_text("New file\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "new.txt" in result.auto_mergeable
        assert len(result.conflicts) == 0

    def test_added_only_remotely(self, tmp_path):
        """Test auto-merge when file added only remotely."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # File only in remote
        (remote / "new.txt").write_text("New file\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "new.txt" in result.auto_mergeable

    def test_added_in_both_identical(self, tmp_path):
        """Test auto-merge when same file added in both versions."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Same file added in both
        (local / "new.txt").write_text("New content\n")
        (remote / "new.txt").write_text("New content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "new.txt" in result.auto_mergeable

    def test_added_in_both_different(self, tmp_path):
        """Test conflict when different files added in both versions."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Different files added
        (local / "new.txt").write_text("Local content\n")
        (remote / "new.txt").write_text("Remote content\n")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 1

        conflict = result.conflicts[0]
        assert conflict.conflict_type == "add_add"
        assert conflict.auto_mergeable is False
        assert conflict.base_content is None


class TestThreeWayDiffBinaryFiles:
    """Tests for binary file handling."""

    def test_binary_file_no_change(self, tmp_path):
        """Test binary file with no changes."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Create identical binary files
        binary_content = b"\x00\x01\x02\x03\xff"
        for path in [base, local, remote]:
            (path / "binary.dat").write_bytes(binary_content)

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 0
        assert result.stats.files_unchanged == 1

    def test_binary_file_changed_remotely(self, tmp_path):
        """Test binary file changed only remotely."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Binary file changed remotely
        (base / "binary.dat").write_bytes(b"\x00\x01")
        (local / "binary.dat").write_bytes(b"\x00\x01")
        (remote / "binary.dat").write_bytes(b"\xff\xfe")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "binary.dat" in result.auto_mergeable

    def test_binary_file_conflict(self, tmp_path):
        """Test binary file changed in both versions."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Binary file changed differently in both
        (base / "binary.dat").write_bytes(b"\x00\x01")
        (local / "binary.dat").write_bytes(b"\xff\xfe")
        (remote / "binary.dat").write_bytes(b"\xaa\xbb")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 1

        conflict = result.conflicts[0]
        assert conflict.is_binary is True
        assert conflict.base_content is None  # Binary files don't have text content


class TestThreeWayDiffEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_directories(self, tmp_path):
        """Test with empty directories."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 0
        assert len(result.conflicts) == 0
        assert result.stats.files_compared == 0
        assert result.summary() == "No changes detected"

    def test_empty_files(self, tmp_path):
        """Test with empty files."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "empty.txt").write_text("")

        result = engine.three_way_diff(base, local, remote)

        assert result.stats.files_unchanged == 1

    def test_ignore_patterns(self, tmp_path):
        """Test that ignore patterns are respected."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "keep.txt").write_text("keep")
            (path / "ignore.pyc").write_text("ignore")

        # Modify keep.txt in remote
        (remote / "keep.txt").write_text("modified")

        result = engine.three_way_diff(base, local, remote)

        # Should only see keep.txt, not ignore.pyc
        assert result.stats.files_compared == 1
        assert len(result.auto_mergeable) == 1
        assert "keep.txt" in result.auto_mergeable

    def test_custom_ignore_patterns(self, tmp_path):
        """Test custom ignore patterns."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "keep.txt").write_text("keep")
            (path / "custom.ignore").write_text("ignore")

        result = engine.three_way_diff(
            base, local, remote, ignore_patterns=["*.ignore"]
        )

        # Should only see keep.txt
        assert result.stats.files_compared == 1

    def test_nested_directories(self, tmp_path):
        """Test with nested directory structures."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "dir1").mkdir()
            (path / "dir1" / "dir2").mkdir()
            (path / "dir1" / "dir2" / "file.txt").write_text("content")

        # Modify in remote
        (remote / "dir1" / "dir2" / "file.txt").write_text("modified")

        result = engine.three_way_diff(base, local, remote)

        assert len(result.auto_mergeable) == 1
        assert "dir1/dir2/file.txt" in result.auto_mergeable

    def test_path_validation(self, tmp_path):
        """Test path validation errors."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "nonexistent"

        base.mkdir()
        local.mkdir()

        # Test nonexistent path
        with pytest.raises(FileNotFoundError, match="Remote path not found"):
            engine.three_way_diff(base, local, remote)

        # Test file instead of directory
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a directory")

        with pytest.raises(NotADirectoryError, match="not a directory"):
            engine.three_way_diff(base, local, file_path)


class TestThreeWayDiffStatistics:
    """Tests for statistics and summary generation."""

    def test_statistics_accuracy(self, tmp_path):
        """Test that statistics are accurately calculated."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # 1 unchanged
        (base / "unchanged.txt").write_text("same")
        (local / "unchanged.txt").write_text("same")
        (remote / "unchanged.txt").write_text("same")

        # 1 auto-mergeable (remote changed)
        (base / "auto.txt").write_text("original")
        (local / "auto.txt").write_text("original")
        (remote / "auto.txt").write_text("modified")

        # 1 conflict
        (base / "conflict.txt").write_text("original")
        (local / "conflict.txt").write_text("local")
        (remote / "conflict.txt").write_text("remote")

        result = engine.three_way_diff(base, local, remote)

        assert result.stats.files_compared == 3
        assert result.stats.files_unchanged == 1
        assert result.stats.auto_mergeable == 1
        assert result.stats.files_conflicted == 1
        assert result.total_files == 2  # auto + conflict

    def test_summary_generation(self, tmp_path):
        """Test summary string generation."""
        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Add one auto-mergeable and one conflict
        (base / "auto.txt").write_text("orig")
        (local / "auto.txt").write_text("orig")
        (remote / "auto.txt").write_text("mod")

        (base / "conflict.txt").write_text("orig")
        (local / "conflict.txt").write_text("local")
        (remote / "conflict.txt").write_text("remote")

        result = engine.three_way_diff(base, local, remote)

        summary = result.summary()
        assert "1 auto-mergeable" in summary
        assert "1 conflicts" in summary


class TestThreeWayDiffPerformance:
    """Performance tests for three-way diff."""

    def test_large_directory(self, tmp_path):
        """Test performance with many files."""
        import time

        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Create 100 files
        num_files = 100
        for i in range(num_files):
            content = f"File {i} content\nLine 2\n"
            (base / f"file_{i:03d}.txt").write_text(content)
            (local / f"file_{i:03d}.txt").write_text(content)
            (remote / f"file_{i:03d}.txt").write_text(content)

        # Modify every 10th file in remote
        for i in range(0, num_files, 10):
            (remote / f"file_{i:03d}.txt").write_text(f"Modified {i}\n")

        start = time.time()
        result = engine.three_way_diff(base, local, remote)
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 2.0, f"Three-way diff took {elapsed:.3f}s (target: <2s)"

        # Verify results
        assert result.stats.files_compared == num_files
        assert len(result.auto_mergeable) == 10  # Every 10th file
        assert len(result.conflicts) == 0

    def test_performance_500_files(self, tmp_path):
        """Test performance target: 500 files in <2s."""
        import time

        engine = DiffEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        # Create 500 files to match PRD requirement
        num_files = 500
        for i in range(num_files):
            content = f"Content {i}\n"
            (base / f"f{i}.txt").write_text(content)
            (local / f"f{i}.txt").write_text(content)

            # Modify 10% in remote
            if i % 10 == 0:
                (remote / f"f{i}.txt").write_text(f"Modified {i}\n")
            else:
                (remote / f"f{i}.txt").write_text(content)

        start = time.time()
        result = engine.three_way_diff(base, local, remote)
        elapsed = time.time() - start

        print(f"\n500 files processed in {elapsed:.3f}s")
        print(f"Performance: {num_files/elapsed:.0f} files/second")

        # PRD requirement: <2s for 500 files
        assert elapsed < 2.0, f"Failed performance target: {elapsed:.3f}s (target: <2s)"

        assert result.stats.files_compared == num_files
        assert len(result.auto_mergeable) == 50
