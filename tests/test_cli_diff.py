"""Tests for CLI diff commands."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


class TestDiffFiles:
    """Test suite for diff files command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_diff_files_identical(self, cli_runner):
        """Test diff files command with identical files."""
        with cli_runner.isolated_filesystem():
            # Create identical files
            Path("file1.txt").write_text("line1\nline2\nline3\n")
            Path("file2.txt").write_text("line1\nline2\nline3\n")

            result = cli_runner.invoke(main, ["diff", "files", "file1.txt", "file2.txt"])

            assert result.exit_code == 0
            assert "identical" in result.output.lower()

    def test_diff_files_different(self, cli_runner):
        """Test diff files command with different files."""
        with cli_runner.isolated_filesystem():
            # Create different files
            Path("file1.txt").write_text("line1\nline2\n")
            Path("file2.txt").write_text("line1\nline3\n")

            result = cli_runner.invoke(main, ["diff", "files", "file1.txt", "file2.txt"])

            assert result.exit_code == 0
            # Should show changes (line2 removed, line3 added)
            assert "line2" in result.output or "line3" in result.output or "Lines added" in result.output

    def test_diff_files_nonexistent(self, cli_runner):
        """Test diff files command with non-existent file."""
        with cli_runner.isolated_filesystem():
            Path("file1.txt").write_text("content\n")

            result = cli_runner.invoke(main, ["diff", "files", "file1.txt", "nonexistent.txt"])

            # Click returns exit code 2 for invalid paths
            assert result.exit_code == 2
            assert "does not exist" in result.output.lower() or "error" in result.output.lower()

    def test_diff_files_with_color_option(self, cli_runner):
        """Test diff files command with --no-color option."""
        with cli_runner.isolated_filesystem():
            Path("file1.txt").write_text("line1\n")
            Path("file2.txt").write_text("line2\n")

            result = cli_runner.invoke(
                main, ["diff", "files", "file1.txt", "file2.txt", "--no-color"]
            )

            assert result.exit_code == 0

    def test_diff_files_binary(self, cli_runner):
        """Test diff files command with binary files."""
        with cli_runner.isolated_filesystem():
            # Create binary files with different content
            Path("file1.bin").write_bytes(b"\x00\x01\x02\x03")
            Path("file2.bin").write_bytes(b"\x00\x01\x02\x04")

            result = cli_runner.invoke(main, ["diff", "files", "file1.bin", "file2.bin"])

            assert result.exit_code == 0
            assert "binary" in result.output.lower() or "Binary" in result.output


class TestDiffDirs:
    """Test suite for diff dirs command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_diff_dirs_identical(self, cli_runner):
        """Test diff dirs command with identical directories."""
        with cli_runner.isolated_filesystem():
            # Create identical directories
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            Path("dir1/file.txt").write_text("content\n")
            Path("dir2/file.txt").write_text("content\n")

            result = cli_runner.invoke(main, ["diff", "dirs", "dir1", "dir2"])

            assert result.exit_code == 0
            assert "Diff Summary" in result.output

    def test_diff_dirs_added_file(self, cli_runner):
        """Test diff dirs command with added files."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            Path("dir2/new_file.txt").write_text("new content\n")

            result = cli_runner.invoke(main, ["diff", "dirs", "dir1", "dir2"])

            assert result.exit_code == 0
            assert "new_file.txt" in result.output or "Files Added" in result.output

    def test_diff_dirs_removed_file(self, cli_runner):
        """Test diff dirs command with removed files."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            Path("dir1/old_file.txt").write_text("old content\n")

            result = cli_runner.invoke(main, ["diff", "dirs", "dir1", "dir2"])

            assert result.exit_code == 0
            assert "old_file.txt" in result.output or "Files Removed" in result.output

    def test_diff_dirs_modified_file(self, cli_runner):
        """Test diff dirs command with modified files."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            Path("dir1/file.txt").write_text("old content\n")
            Path("dir2/file.txt").write_text("new content\n")

            result = cli_runner.invoke(main, ["diff", "dirs", "dir1", "dir2"])

            assert result.exit_code == 0
            assert "file.txt" in result.output or "Files Modified" in result.output

    def test_diff_dirs_with_ignore_pattern(self, cli_runner):
        """Test diff dirs command with --ignore option."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            Path("dir1/file.txt").write_text("content\n")
            Path("dir1/file.pyc").write_bytes(b"bytecode")
            Path("dir2/file.txt").write_text("content\n")

            result = cli_runner.invoke(
                main, ["diff", "dirs", "dir1", "dir2", "--ignore", "*.pyc"]
            )

            assert result.exit_code == 0

    def test_diff_dirs_with_limit(self, cli_runner):
        """Test diff dirs command with --limit option."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            # Create many files
            for i in range(150):
                Path(f"dir1/file{i}.txt").write_text(f"content {i}\n")
                Path(f"dir2/file{i}.txt").write_text(f"modified {i}\n")

            result = cli_runner.invoke(
                main, ["diff", "dirs", "dir1", "dir2", "--limit", "50"]
            )

            assert result.exit_code == 0
            # Check for key phrases (with ANSI codes stripped if needed)
            assert "Showing" in result.output and ("50" in result.output and "150" in result.output)

    def test_diff_dirs_stats_only(self, cli_runner):
        """Test diff dirs command with --stats-only option."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()
            Path("dir2").mkdir()
            Path("dir1/file1.txt").write_text("content\n")
            Path("dir2/file2.txt").write_text("content\n")

            result = cli_runner.invoke(
                main, ["diff", "dirs", "dir1", "dir2", "--stats-only"]
            )

            assert result.exit_code == 0
            assert "Diff Summary" in result.output
            # Should NOT show individual file listings
            # (but we can't easily test negative assertion on this)

    def test_diff_dirs_nonexistent(self, cli_runner):
        """Test diff dirs command with non-existent directory."""
        with cli_runner.isolated_filesystem():
            Path("dir1").mkdir()

            result = cli_runner.invoke(main, ["diff", "dirs", "dir1", "nonexistent"])

            # Click returns exit code 2 for invalid paths
            assert result.exit_code == 2
            assert "does not exist" in result.output.lower() or "error" in result.output.lower()


class TestDiffThreeWay:
    """Test suite for diff three-way command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_diff_three_way_no_changes(self, cli_runner):
        """Test three-way diff with no changes."""
        with cli_runner.isolated_filesystem():
            # Create identical directories
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file.txt").write_text("content\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote"]
            )

            assert result.exit_code == 0
            assert "Three-Way Diff Summary" in result.output

    def test_diff_three_way_local_only_change(self, cli_runner):
        """Test three-way diff with local-only change (auto-mergeable)."""
        with cli_runner.isolated_filesystem():
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file.txt").write_text("content\n")

            # Modify local only
            Path("local/file.txt").write_text("local change\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote"]
            )

            assert result.exit_code == 0
            assert "Auto-mergeable" in result.output

    def test_diff_three_way_remote_only_change(self, cli_runner):
        """Test three-way diff with remote-only change (auto-mergeable)."""
        with cli_runner.isolated_filesystem():
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file.txt").write_text("content\n")

            # Modify remote only
            Path("remote/file.txt").write_text("remote change\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote"]
            )

            assert result.exit_code == 0
            assert "Auto-mergeable" in result.output

    def test_diff_three_way_both_modified_conflict(self, cli_runner):
        """Test three-way diff with both modified (conflict)."""
        with cli_runner.isolated_filesystem():
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file.txt").write_text("content\n")

            # Modify both differently
            Path("local/file.txt").write_text("local change\n")
            Path("remote/file.txt").write_text("remote change\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote"]
            )

            assert result.exit_code == 0
            assert "Conflicts" in result.output

    def test_diff_three_way_conflicts_only(self, cli_runner):
        """Test three-way diff with --conflicts-only flag."""
        with cli_runner.isolated_filesystem():
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file1.txt").write_text("content\n")
                Path(f"{dirname}/file2.txt").write_text("content\n")

            # Local-only change (auto-mergeable)
            Path("local/file1.txt").write_text("local change\n")

            # Both modified (conflict)
            Path("local/file2.txt").write_text("local change\n")
            Path("remote/file2.txt").write_text("remote change\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote", "--conflicts-only"]
            )

            assert result.exit_code == 0
            # Should show only conflicts, not auto-mergeable
            assert "file2.txt" in result.output or "Conflicts" in result.output

    def test_diff_three_way_with_ignore(self, cli_runner):
        """Test three-way diff with --ignore option."""
        with cli_runner.isolated_filesystem():
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file.txt").write_text("content\n")
                Path(f"{dirname}/ignored.pyc").write_bytes(b"bytecode")

            result = cli_runner.invoke(
                main,
                ["diff", "three-way", "base", "local", "remote", "--ignore", "*.pyc"],
            )

            assert result.exit_code == 0

    def test_diff_three_way_nonexistent(self, cli_runner):
        """Test three-way diff with non-existent directory."""
        with cli_runner.isolated_filesystem():
            Path("base").mkdir()
            Path("local").mkdir()

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "nonexistent"]
            )

            # Click returns exit code 2 for invalid paths
            assert result.exit_code == 2
            assert "does not exist" in result.output.lower() or "error" in result.output.lower()

    def test_diff_three_way_deletion_conflict(self, cli_runner):
        """Test three-way diff with deletion conflict."""
        with cli_runner.isolated_filesystem():
            for dirname in ["base", "local", "remote"]:
                Path(dirname).mkdir()
                Path(f"{dirname}/file.txt").write_text("content\n")

            # Delete locally, modify remotely -> conflict
            Path("local/file.txt").unlink()
            Path("remote/file.txt").write_text("remote change\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote"]
            )

            assert result.exit_code == 0
            assert "Conflicts" in result.output


class TestDiffCommandGroup:
    """Test suite for diff command group."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_diff_help(self, cli_runner):
        """Test diff command help output."""
        result = cli_runner.invoke(main, ["diff", "--help"])

        assert result.exit_code == 0
        assert "Compare artifacts and detect changes" in result.output
        assert "files" in result.output
        assert "dirs" in result.output
        assert "three-way" in result.output

    def test_diff_files_help(self, cli_runner):
        """Test diff files command help output."""
        result = cli_runner.invoke(main, ["diff", "files", "--help"])

        assert result.exit_code == 0
        assert "Compare two files" in result.output
        assert "--context" in result.output
        assert "--color" in result.output

    def test_diff_dirs_help(self, cli_runner):
        """Test diff dirs command help output."""
        result = cli_runner.invoke(main, ["diff", "dirs", "--help"])

        assert result.exit_code == 0
        assert "Compare two directories" in result.output
        assert "--ignore" in result.output
        assert "--limit" in result.output
        assert "--stats-only" in result.output

    def test_diff_three_way_help(self, cli_runner):
        """Test diff three-way command help output."""
        result = cli_runner.invoke(main, ["diff", "three-way", "--help"])

        assert result.exit_code == 0
        assert "three-way diff" in result.output.lower()
        assert "--ignore" in result.output
        assert "--conflicts-only" in result.output


class TestDiffEdgeCases:
    """Test suite for diff command edge cases."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_diff_files_empty_files(self, cli_runner):
        """Test diff files with empty files."""
        with cli_runner.isolated_filesystem():
            Path("empty1.txt").write_text("")
            Path("empty2.txt").write_text("")

            result = cli_runner.invoke(main, ["diff", "files", "empty1.txt", "empty2.txt"])

            assert result.exit_code == 0
            assert "identical" in result.output.lower()

    def test_diff_files_one_empty(self, cli_runner):
        """Test diff files with one empty file."""
        with cli_runner.isolated_filesystem():
            Path("empty.txt").write_text("")
            Path("nonempty.txt").write_text("content\n")

            result = cli_runner.invoke(main, ["diff", "files", "empty.txt", "nonempty.txt"])

            assert result.exit_code == 0

    def test_diff_dirs_empty_directories(self, cli_runner):
        """Test diff dirs with empty directories."""
        with cli_runner.isolated_filesystem():
            Path("empty1").mkdir()
            Path("empty2").mkdir()

            result = cli_runner.invoke(main, ["diff", "dirs", "empty1", "empty2"])

            assert result.exit_code == 0

    def test_diff_dirs_nested_structure(self, cli_runner):
        """Test diff dirs with nested directory structure."""
        with cli_runner.isolated_filesystem():
            Path("dir1/sub1/sub2").mkdir(parents=True)
            Path("dir2/sub1/sub2").mkdir(parents=True)
            Path("dir1/sub1/sub2/file.txt").write_text("content\n")
            Path("dir2/sub1/sub2/file.txt").write_text("different\n")

            result = cli_runner.invoke(main, ["diff", "dirs", "dir1", "dir2"])

            assert result.exit_code == 0
            assert "file.txt" in result.output or "Modified" in result.output

    def test_diff_three_way_file_added_in_both(self, cli_runner):
        """Test three-way diff with file added in both versions."""
        with cli_runner.isolated_filesystem():
            Path("base").mkdir()
            Path("local").mkdir()
            Path("remote").mkdir()

            # Add same file in both with different content
            Path("local/new_file.txt").write_text("local version\n")
            Path("remote/new_file.txt").write_text("remote version\n")

            result = cli_runner.invoke(
                main, ["diff", "three-way", "base", "local", "remote"]
            )

            assert result.exit_code == 0
            # This should be a conflict
            assert "Conflicts" in result.output or "new_file.txt" in result.output
