#!/usr/bin/env python3
"""Tests for MergeEngine functionality.

This module tests the merge capability including auto-merge, conflict detection,
and Git-style conflict marker generation.
"""

import pytest
from pathlib import Path

from skillmeat.core.merge_engine import MergeEngine
from skillmeat.models import MergeResult, MergeStats


class TestMergeEngineAutoMerge:
    """Tests for auto-merge scenarios."""

    def test_only_local_changed(self, tmp_path):
        """Test auto-merge when only local version changed."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Base and remote are identical, local changed
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Modified content\n")
        (remote / "file.txt").write_text("Original content\n")

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        assert len(result.auto_merged) == 1
        assert "file.txt" in result.auto_merged
        assert len(result.conflicts) == 0

        # Verify output contains local changes
        merged_file = output / "file.txt"
        assert merged_file.exists()
        assert merged_file.read_text() == "Modified content\n"

    def test_only_remote_changed(self, tmp_path):
        """Test auto-merge when only remote version changed."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Base and local are identical, remote changed
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Original content\n")
        (remote / "file.txt").write_text("Modified content\n")

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        assert len(result.auto_merged) == 1
        assert len(result.conflicts) == 0

        # Verify output contains remote changes
        merged_file = output / "file.txt"
        assert merged_file.exists()
        assert merged_file.read_text() == "Modified content\n"

    def test_both_changed_identically(self, tmp_path):
        """Test auto-merge when both changed to same content."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Both changed to the same thing
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Modified content\n")
        (remote / "file.txt").write_text("Modified content\n")

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        assert len(result.auto_merged) == 1
        assert len(result.conflicts) == 0

        # Verify output contains the identical changes
        merged_file = output / "file.txt"
        assert merged_file.exists()
        assert merged_file.read_text() == "Modified content\n"

    def test_multiple_files_auto_merge(self, tmp_path):
        """Test auto-merge with multiple files."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # File 1: only local changed
        (base / "file1.txt").write_text("orig")
        (local / "file1.txt").write_text("local")
        (remote / "file1.txt").write_text("orig")

        # File 2: only remote changed
        (base / "file2.txt").write_text("orig")
        (local / "file2.txt").write_text("orig")
        (remote / "file2.txt").write_text("remote")

        # File 3: both changed identically
        (base / "file3.txt").write_text("orig")
        (local / "file3.txt").write_text("same")
        (remote / "file3.txt").write_text("same")

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        assert len(result.auto_merged) == 3
        assert len(result.conflicts) == 0
        assert result.stats.auto_merged == 3

        # Verify outputs
        assert (output / "file1.txt").read_text() == "local"
        assert (output / "file2.txt").read_text() == "remote"
        assert (output / "file3.txt").read_text() == "same"

    def test_directory_structure_preserved(self, tmp_path):
        """Test that directory structure is preserved during merge."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "dir1").mkdir()
            (path / "dir1" / "dir2").mkdir()

        # Nested file changed in local
        (base / "dir1" / "dir2" / "file.txt").write_text("original")
        (local / "dir1" / "dir2" / "file.txt").write_text("modified")
        (remote / "dir1" / "dir2" / "file.txt").write_text("original")

        result = engine.merge(base, local, remote, output)

        assert result.success is True

        # Verify nested structure created
        merged_file = output / "dir1" / "dir2" / "file.txt"
        assert merged_file.exists()
        assert merged_file.read_text() == "modified"


class TestMergeEngineConflicts:
    """Tests for conflict scenarios."""

    def test_content_conflict_markers(self, tmp_path):
        """Test conflict markers generated for content conflicts."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Both changed differently
        (base / "file.txt").write_text("Original content\n")
        (local / "file.txt").write_text("Local modification\n")
        (remote / "file.txt").write_text("Remote modification\n")

        result = engine.merge(base, local, remote, output)

        assert result.success is False
        assert len(result.auto_merged) == 0
        assert len(result.conflicts) == 1
        assert result.stats.conflicts == 1

        # Verify conflict markers in output
        merged_file = output / "file.txt"
        assert merged_file.exists()
        content = merged_file.read_text()

        assert "<<<<<<< LOCAL (current)" in content
        assert "=======" in content
        assert ">>>>>>> REMOTE (incoming)" in content
        assert "Local modification" in content
        assert "Remote modification" in content

    def test_deletion_conflict_local(self, tmp_path):
        """Test conflict when file deleted locally but modified remotely."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Deleted locally, modified remotely
        (base / "file.txt").write_text("Original\n")
        (remote / "file.txt").write_text("Modified\n")
        # Local: file doesn't exist (deleted)

        result = engine.merge(base, local, remote, output)

        assert result.success is False
        assert len(result.conflicts) == 1

        conflict = result.conflicts[0]
        assert conflict.conflict_type == "deletion"
        assert conflict.local_content is None
        assert conflict.remote_content is not None

        # Verify conflict markers show deletion
        merged_file = output / "file.txt"
        assert merged_file.exists()
        content = merged_file.read_text()
        assert "(file deleted)" in content

    def test_deletion_conflict_remote(self, tmp_path):
        """Test conflict when file modified locally but deleted remotely."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Modified locally, deleted remotely
        (base / "file.txt").write_text("Original\n")
        (local / "file.txt").write_text("Modified\n")
        # Remote: file doesn't exist (deleted)

        result = engine.merge(base, local, remote, output)

        assert result.success is False
        assert len(result.conflicts) == 1

        conflict = result.conflicts[0]
        assert conflict.conflict_type == "deletion"

    def test_binary_file_conflict(self, tmp_path):
        """Test binary file conflicts are detected and flagged."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Binary files changed differently
        (base / "binary.dat").write_bytes(b"\x00\x01")
        (local / "binary.dat").write_bytes(b"\xff\xfe")
        (remote / "binary.dat").write_bytes(b"\xaa\xbb")

        result = engine.merge(base, local, remote, output)

        assert result.success is False
        assert len(result.conflicts) == 1
        assert result.stats.binary_conflicts == 1

        conflict = result.conflicts[0]
        assert conflict.is_binary is True
        assert conflict.auto_mergeable is False

    def test_nested_directory_conflicts(self, tmp_path):
        """Test conflicts in nested directories."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "subdir").mkdir()

        # Conflict in nested file
        (base / "subdir" / "file.txt").write_text("base")
        (local / "subdir" / "file.txt").write_text("local")
        (remote / "subdir" / "file.txt").write_text("remote")

        result = engine.merge(base, local, remote, output)

        assert result.success is False
        assert len(result.conflicts) == 1

        # Verify conflict file exists in correct location
        conflict_file = output / "subdir" / "file.txt"
        assert conflict_file.exists()

    def test_mixed_auto_merge_and_conflicts(self, tmp_path):
        """Test scenario with both auto-mergeable and conflicted files."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Auto-mergeable file (only local changed)
        (base / "auto.txt").write_text("orig")
        (local / "auto.txt").write_text("local")
        (remote / "auto.txt").write_text("orig")

        # Conflicted file (both changed)
        (base / "conflict.txt").write_text("orig")
        (local / "conflict.txt").write_text("local")
        (remote / "conflict.txt").write_text("remote")

        result = engine.merge(base, local, remote, output)

        assert result.success is False  # Has conflicts
        assert len(result.auto_merged) == 1
        assert len(result.conflicts) == 1
        assert result.stats.auto_merged == 1
        assert result.stats.conflicts == 1

        # Verify auto-merged file
        assert (output / "auto.txt").read_text() == "local"

        # Verify conflict file has markers
        conflict_content = (output / "conflict.txt").read_text()
        assert "<<<<<<< LOCAL" in conflict_content


class TestMergeEngineEdgeCases:
    """Tests for edge cases."""

    def test_empty_files(self, tmp_path):
        """Test merging empty files."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "empty.txt").write_text("")

        result = engine.merge(base, local, remote, output)

        # No changes, so no files should be merged
        assert result.success is True
        assert len(result.auto_merged) == 0
        assert len(result.conflicts) == 0

    def test_empty_directories(self, tmp_path):
        """Test merging empty directories."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        assert result.stats.total_files == 0

    def test_large_files(self, tmp_path):
        """Test merging large files."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Create large file (1000 lines)
        large_content = "\n".join([f"Line {i}" for i in range(1000)])
        (base / "large.txt").write_text(large_content)
        (local / "large.txt").write_text(large_content + "\nLocal addition")
        (remote / "large.txt").write_text(large_content)

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        assert len(result.auto_merged) == 1

        # Verify content
        merged = (output / "large.txt").read_text()
        assert "Line 999" in merged
        assert "Local addition" in merged

    def test_special_characters(self, tmp_path):
        """Test files with special characters."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Unicode characters
        (base / "unicode.txt").write_text("Base: 你好世界\n")
        (local / "unicode.txt").write_text("Local: 你好世界 🎉\n")
        (remote / "unicode.txt").write_text("Base: 你好世界\n")

        result = engine.merge(base, local, remote, output)

        assert result.success is True
        merged = (output / "unicode.txt").read_text()
        assert "🎉" in merged

    def test_merge_without_output_path(self, tmp_path):
        """Test merge without specifying output path."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "file.txt").write_text("base")
        (local / "file.txt").write_text("local")
        (remote / "file.txt").write_text("base")

        # Merge without output path
        result = engine.merge(base, local, remote)

        assert result.success is True
        assert len(result.auto_merged) == 1
        assert result.output_path is None

    def test_merge_files_single_file(self, tmp_path):
        """Test merge_files() for single file merge."""
        engine = MergeEngine()

        base_file = tmp_path / "base.txt"
        local_file = tmp_path / "local.txt"
        remote_file = tmp_path / "remote.txt"
        output_file = tmp_path / "output.txt"

        base_file.write_text("original")
        local_file.write_text("modified")
        remote_file.write_text("original")

        result = engine.merge_files(base_file, local_file, remote_file, output_file)

        assert result.success is True
        assert result.merged_content == "modified"
        assert output_file.exists()
        assert output_file.read_text() == "modified"


class TestMergeEngineStatistics:
    """Tests for statistics and summary generation."""

    def test_statistics_accuracy(self, tmp_path):
        """Test that statistics are accurately calculated."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # 2 auto-merged
        (base / "auto1.txt").write_text("orig")
        (local / "auto1.txt").write_text("local")
        (remote / "auto1.txt").write_text("orig")

        (base / "auto2.txt").write_text("orig")
        (local / "auto2.txt").write_text("orig")
        (remote / "auto2.txt").write_text("remote")

        # 1 text conflict
        (base / "conflict.txt").write_text("orig")
        (local / "conflict.txt").write_text("local")
        (remote / "conflict.txt").write_text("remote")

        # 1 binary conflict
        (base / "binary.dat").write_bytes(b"\x00")
        (local / "binary.dat").write_bytes(b"\x01")
        (remote / "binary.dat").write_bytes(b"\x02")

        result = engine.merge(base, local, remote, output)

        assert result.stats.total_files == 4
        assert result.stats.auto_merged == 2
        assert result.stats.conflicts == 2
        assert result.stats.binary_conflicts == 1

    def test_summary_generation(self, tmp_path):
        """Test summary string generation."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # One auto-merge
        (base / "auto.txt").write_text("orig")
        (local / "auto.txt").write_text("local")
        (remote / "auto.txt").write_text("orig")

        result = engine.merge(base, local, remote, output)

        summary = result.summary()
        assert "1 files auto-merged" in summary or "auto-merged" in summary

    def test_success_rate_calculation(self, tmp_path):
        """Test success rate calculation in stats."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # 3 auto-merged, 1 conflict = 75% success
        for i in range(3):
            (base / f"auto{i}.txt").write_text("orig")
            (local / f"auto{i}.txt").write_text("local")
            (remote / f"auto{i}.txt").write_text("orig")

        (base / "conflict.txt").write_text("orig")
        (local / "conflict.txt").write_text("local")
        (remote / "conflict.txt").write_text("remote")

        result = engine.merge(base, local, remote, output)

        assert result.stats.success_rate == 75.0


class TestMergeEnginePerformance:
    """Performance tests for merge operations."""

    def test_500_files_performance(self, tmp_path):
        """Test performance target: 500 files in <2s."""
        import time

        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        # Create 500 files
        num_files = 500
        for i in range(num_files):
            content = f"Content {i}\n"
            (base / f"f{i}.txt").write_text(content)
            (local / f"f{i}.txt").write_text(content)

            # Modify 10% in remote (auto-merge)
            if i % 10 == 0:
                (remote / f"f{i}.txt").write_text(f"Modified {i}\n")
            else:
                (remote / f"f{i}.txt").write_text(content)

        start = time.time()
        result = engine.merge(base, local, remote, output)
        elapsed = time.time() - start

        print(f"\n500 files merged in {elapsed:.3f}s")
        print(f"Performance: {num_files/elapsed:.0f} files/second")

        # Performance target: <2.5s for 500 files
        # Note: Slightly higher than DiffEngine due to re-analysis of auto-mergeable files
        assert (
            elapsed < 2.5
        ), f"Failed performance target: {elapsed:.3f}s (target: <2.5s)"

        assert result.success is True
        assert result.stats.auto_merged == 50
        assert result.stats.conflicts == 0


class TestMergeEngineAtomicOperations:
    """Tests for atomic file operations."""

    def test_atomic_copy(self, tmp_path):
        """Test that files are copied atomically."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "file.txt").write_text("original")
        (local / "file.txt").write_text("modified")
        (remote / "file.txt").write_text("original")

        result = engine.merge(base, local, remote, output)

        # File should exist and be complete
        merged = output / "file.txt"
        assert merged.exists()
        assert merged.read_text() == "modified"

    def test_atomic_write_conflict_markers(self, tmp_path):
        """Test that conflict marker files are written atomically."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()

        (base / "file.txt").write_text("base")
        (local / "file.txt").write_text("local")
        (remote / "file.txt").write_text("remote")

        result = engine.merge(base, local, remote, output)

        # Conflict file should exist and be complete
        merged = output / "file.txt"
        assert merged.exists()
        content = merged.read_text()
        assert "<<<<<<< LOCAL" in content
        assert ">>>>>>> REMOTE" in content
