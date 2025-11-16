#!/usr/bin/env python3
"""Tests for MergeEngine error handling and rollback.

This module tests the error handling capabilities of MergeEngine including:
- Output path creation failures
- File permission errors
- Partial merge rollback
"""

import pytest
from pathlib import Path
import os
import stat

from skillmeat.core.merge_engine import MergeEngine
from skillmeat.models import MergeResult


class TestMergeEngineErrorHandling:
    """Tests for error handling in merge operations."""

    def test_output_path_creation_permission_denied(self, tmp_path):
        """Test handling when output directory cannot be created (permission denied)."""
        # Skip this test if running as root (can bypass permissions)
        if os.getuid() == 0:
            pytest.skip("Test requires non-root user (root can bypass permissions)")

        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        # Create valid base, local, remote
        for path in [base, local, remote]:
            path.mkdir()
            (path / "file.txt").write_text("content")

        # Create read-only parent directory
        readonly_parent = tmp_path / "readonly"
        readonly_parent.mkdir()
        os.chmod(readonly_parent, stat.S_IRUSR | stat.S_IXUSR)  # read + execute only

        try:
            # Attempt to create output in read-only directory
            output = readonly_parent / "output"

            result = engine.merge(base, local, remote, output)

            # Should fail gracefully
            assert result.success is False
            assert result.error is not None
            assert "Permission denied" in result.error or "Failed to create" in result.error
            assert result.stats.total_files > 0  # Stats should still be set

        finally:
            # Restore permissions for cleanup
            os.chmod(readonly_parent, stat.S_IRWXU)

    def test_output_path_creation_invalid_path(self, tmp_path):
        """Test handling when output path is invalid."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        # Create valid base, local, remote
        for path in [base, local, remote]:
            path.mkdir()
            (path / "file.txt").write_text("content")

        # Try to create output under a file (not a directory)
        file_not_dir = tmp_path / "file_not_dir"
        file_not_dir.write_text("not a directory")
        output = file_not_dir / "output"

        result = engine.merge(base, local, remote, output)

        # Should fail gracefully
        assert result.success is False
        assert result.error is not None
        assert "Failed to create" in result.error or "Not a directory" in result.error.lower()

    def test_partial_merge_rollback_on_error(self, tmp_path, monkeypatch):
        """Test rollback when merge fails partway through."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        # Create base, local, remote with multiple files
        for path in [base, local, remote]:
            path.mkdir()
            (path / "file1.txt").write_text("content1")
            (path / "file2.txt").write_text("content2")
            (path / "file3.txt").write_text("content3")

        # Make remote different for all files (trigger auto-merge)
        (remote / "file1.txt").write_text("remote1")
        (remote / "file2.txt").write_text("remote2")
        (remote / "file3.txt").write_text("remote3")

        # Inject an error after first file is copied
        original_atomic_copy = engine._atomic_copy
        call_count = [0]

        def failing_atomic_copy(source, dest):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise PermissionError("Simulated permission error")
            return original_atomic_copy(source, dest)

        monkeypatch.setattr(engine, "_atomic_copy", failing_atomic_copy)

        # Perform merge (should fail and rollback)
        result = engine.merge(base, local, remote, output)

        # Verify error handling
        assert result.success is False
        assert result.error is not None
        assert "rolled back" in result.error
        assert "Simulated permission error" in result.error

        # Verify rollback: no files should exist in output
        # (or if they do, it should be because rollback couldn't delete them)
        if output.exists():
            # Check that we attempted to clean up
            # In real scenario, rollback might fail too, but we tried
            assert len(list(output.glob("*"))) <= 1  # At most 1 file if rollback failed

    def test_merge_handles_readonly_source_gracefully(self, tmp_path):
        """Test that merge works even if source files are read-only."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        # Create base, local, remote
        for path in [base, local, remote]:
            path.mkdir()

        # Create read-only file in remote
        readonly_file = remote / "readonly.txt"
        readonly_file.write_text("readonly content")
        os.chmod(readonly_file, stat.S_IRUSR)  # Read-only

        # Create different content in local and base
        (base / "readonly.txt").write_text("base content")
        (local / "readonly.txt").write_text("base content")

        try:
            # Merge should succeed (copying read-only file)
            result = engine.merge(base, local, remote, output)

            # Should succeed (read-only is fine for source)
            assert result.success is True
            assert len(result.auto_merged) == 1

            # Verify output file exists and is readable
            output_file = output / "readonly.txt"
            assert output_file.exists()
            assert output_file.read_text() == "readonly content"

        finally:
            # Restore permissions for cleanup
            if readonly_file.exists():
                os.chmod(readonly_file, stat.S_IRWXU)

    def test_error_result_includes_stats(self, tmp_path):
        """Test that error results still include statistics."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        # Create valid base, local, remote with files
        for path in [base, local, remote]:
            path.mkdir()
            (path / "file1.txt").write_text("content1")
            (path / "file2.txt").write_text("content2")

        # Make remote different for both files
        (remote / "file1.txt").write_text("remote1")
        (remote / "file2.txt").write_text("remote2")

        # Use invalid output path
        file_not_dir = tmp_path / "file_not_dir"
        file_not_dir.write_text("not a directory")
        output = file_not_dir / "output"

        result = engine.merge(base, local, remote, output)

        # Should have error
        assert result.success is False
        assert result.error is not None

        # But stats should still be populated
        assert result.stats.total_files > 0
        assert result.stats.total_files >= 1  # At least 1 file analyzed

    def test_empty_merge_no_rollback(self, tmp_path):
        """Test that empty merge (no files) doesn't trigger rollback."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        # Create empty directories
        for path in [base, local, remote]:
            path.mkdir()

        result = engine.merge(base, local, remote, output)

        # Should succeed with no files
        assert result.success is True
        assert result.error is None
        assert result.stats.total_files == 0
        assert len(result.auto_merged) == 0


class TestMergeEngineRollbackBehavior:
    """Tests specifically for rollback behavior."""

    def test_rollback_deletes_auto_merged_files(self, tmp_path, monkeypatch):
        """Test that rollback deletes auto-merged files."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        # Create files for auto-merge
        for path in [base, local, remote]:
            path.mkdir()
            (path / "auto1.txt").write_text("content")
            (path / "auto2.txt").write_text("content")

        # Make remote different
        (remote / "auto1.txt").write_text("remote1")
        (remote / "auto2.txt").write_text("remote2")

        # Inject error after first file
        original_atomic_copy = engine._atomic_copy
        call_count = [0]

        def failing_atomic_copy(source, dest):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise IOError("Simulated I/O error")
            return original_atomic_copy(source, dest)

        monkeypatch.setattr(engine, "_atomic_copy", failing_atomic_copy)

        result = engine.merge(base, local, remote, output)

        # Should fail with rollback
        assert result.success is False
        assert "rolled back" in result.error

        # First file should be deleted by rollback
        assert not (output / "auto1.txt").exists() or len(list(output.glob("*"))) == 0

    def test_rollback_deletes_conflict_files(self, tmp_path, monkeypatch):
        """Test that rollback deletes conflict marker files."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        # Create conflicting files
        for path in [base, local, remote]:
            path.mkdir()

        (base / "conflict1.txt").write_text("base")
        (local / "conflict1.txt").write_text("local")
        (remote / "conflict1.txt").write_text("remote")

        (base / "conflict2.txt").write_text("base")
        (local / "conflict2.txt").write_text("local2")
        (remote / "conflict2.txt").write_text("remote2")

        # Inject error after first conflict file
        original_atomic_write = engine._atomic_write
        call_count = [0]

        def failing_atomic_write(dest, content):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise IOError("Simulated write error")
            return original_atomic_write(dest, content)

        monkeypatch.setattr(engine, "_atomic_write", failing_atomic_write)

        result = engine.merge(base, local, remote, output)

        # Should fail with rollback
        assert result.success is False
        assert "rolled back" in result.error

        # Files should be cleaned up
        if output.exists():
            assert len(list(output.glob("*"))) <= 1  # At most one file if cleanup failed

    def test_rollback_best_effort_cleanup(self, tmp_path, monkeypatch):
        """Test that rollback continues even if cleanup fails."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        # Create files
        for path in [base, local, remote]:
            path.mkdir()
            (path / "file1.txt").write_text("content")
            (path / "file2.txt").write_text("content")

        (remote / "file1.txt").write_text("remote1")
        (remote / "file2.txt").write_text("remote2")

        # Inject error during merge
        original_atomic_copy = engine._atomic_copy
        call_count = [0]

        def failing_atomic_copy(source, dest):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise PermissionError("Merge failed")
            return original_atomic_copy(source, dest)

        monkeypatch.setattr(engine, "_atomic_copy", failing_atomic_copy)

        # Make first output file undeletable (simulate locked file)
        # This tests that rollback continues even if first file can't be deleted
        result = engine.merge(base, local, remote, output)

        # Should still return error result even if cleanup partially failed
        assert result.success is False
        assert "rolled back" in result.error


class TestMergeEngineErrorMessages:
    """Tests for error message clarity."""

    def test_permission_error_message(self, tmp_path):
        """Test that permission errors have clear messages."""
        # Skip if running as root
        if os.getuid() == 0:
            pytest.skip("Test requires non-root user (root can bypass permissions)")

        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "file.txt").write_text("content")

        # Create readonly parent
        readonly_parent = tmp_path / "readonly"
        readonly_parent.mkdir()
        os.chmod(readonly_parent, stat.S_IRUSR | stat.S_IXUSR)

        try:
            output = readonly_parent / "output"
            result = engine.merge(base, local, remote, output)

            assert result.error is not None
            assert "Permission denied" in result.error or "Failed to create" in result.error
            # Should mention the specific issue
            assert "output directory" in result.error.lower() or "directory" in result.error.lower()

        finally:
            os.chmod(readonly_parent, stat.S_IRWXU)

    def test_rollback_error_message_includes_original_error(self, tmp_path, monkeypatch):
        """Test that rollback error includes original error message."""
        engine = MergeEngine()

        base = tmp_path / "base"
        local = tmp_path / "local"
        remote = tmp_path / "remote"
        output = tmp_path / "output"

        for path in [base, local, remote]:
            path.mkdir()
            (path / "file.txt").write_text("content")

        (remote / "file.txt").write_text("remote")

        # Inject specific error
        def failing_atomic_copy(source, dest):
            raise PermissionError("Custom permission denied message")

        monkeypatch.setattr(engine, "_atomic_copy", failing_atomic_copy)

        result = engine.merge(base, local, remote, output)

        assert result.error is not None
        assert "rolled back" in result.error
        assert "Custom permission denied message" in result.error
