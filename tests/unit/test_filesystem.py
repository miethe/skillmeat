"""Unit tests for filesystem utilities."""

import pytest
from pathlib import Path

from skillmeat.utils.filesystem import compute_content_hash, atomic_write


class TestComputeContentHash:
    """Test compute_content_hash function."""

    def test_hash_simple_file(self, tmp_path):
        """Test hashing a simple file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!")

        hash1 = compute_content_hash(test_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex digest

        # Same content should produce same hash
        hash2 = compute_content_hash(test_file)
        assert hash1 == hash2

    def test_hash_binary_file(self, tmp_path):
        """Test hashing a binary file."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        hash1 = compute_content_hash(test_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_hash_different_content(self, tmp_path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        hash1 = compute_content_hash(file1)
        hash2 = compute_content_hash(file2)

        assert hash1 != hash2

    def test_hash_directory(self, tmp_path):
        """Test hashing a directory."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        (dir_path / "file1.txt").write_text("File 1")
        (dir_path / "file2.txt").write_text("File 2")

        subdir = dir_path / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("File 3")

        hash1 = compute_content_hash(dir_path)
        assert isinstance(hash1, str)
        assert len(hash1) == 64

        # Same directory should produce same hash
        hash2 = compute_content_hash(dir_path)
        assert hash1 == hash2

    def test_hash_directory_order_independent(self, tmp_path):
        """Test that directory hash is consistent regardless of creation order."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()

        # Create files in one order
        (dir1 / "a.txt").write_text("A")
        (dir1 / "b.txt").write_text("B")
        (dir1 / "c.txt").write_text("C")

        hash1 = compute_content_hash(dir1)

        dir2 = tmp_path / "dir2"
        dir2.mkdir()

        # Create same files in different order
        (dir2 / "c.txt").write_text("C")
        (dir2 / "a.txt").write_text("A")
        (dir2 / "b.txt").write_text("B")

        hash2 = compute_content_hash(dir2)

        # Hashes should be the same (sorted internally)
        assert hash1 == hash2

    def test_hash_directory_structure_matters(self, tmp_path):
        """Test that directory structure affects hash."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        (dir1 / "file.txt").write_text("Content")

        dir2 = tmp_path / "dir2"
        dir2.mkdir()
        subdir = dir2 / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("Content")

        hash1 = compute_content_hash(dir1)
        hash2 = compute_content_hash(dir2)

        # Different structure should produce different hash
        assert hash1 != hash2

    def test_hash_nonexistent_raises_error(self, tmp_path):
        """Test that hashing non-existent path raises error."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            compute_content_hash(nonexistent)

    def test_hash_large_file(self, tmp_path):
        """Test hashing a large file (tests chunking)."""
        large_file = tmp_path / "large.txt"

        # Create file larger than chunk size (8192 bytes)
        content = "x" * 100000
        large_file.write_text(content)

        hash1 = compute_content_hash(large_file)
        assert isinstance(hash1, str)
        assert len(hash1) == 64


class TestAtomicWrite:
    """Test atomic_write function."""

    def test_write_new_file(self, tmp_path):
        """Test writing to a new file."""
        dest = tmp_path / "test.txt"
        content = "Hello, world!"

        atomic_write(content, dest)

        assert dest.exists()
        assert dest.read_text() == content

    def test_write_overwrites_existing(self, tmp_path):
        """Test writing overwrites existing file."""
        dest = tmp_path / "test.txt"
        dest.write_text("Old content")

        new_content = "New content"
        atomic_write(new_content, dest)

        assert dest.read_text() == new_content

    def test_write_creates_parent_directory(self, tmp_path):
        """Test that parent directory is created if missing."""
        dest = tmp_path / "subdir" / "nested" / "test.txt"

        atomic_write("Content", dest)

        assert dest.exists()
        assert dest.read_text() == "Content"

    def test_write_multiline_content(self, tmp_path):
        """Test writing multiline content."""
        dest = tmp_path / "test.txt"
        content = "Line 1\nLine 2\nLine 3\n"

        atomic_write(content, dest)

        assert dest.read_text() == content

    def test_write_unicode_content(self, tmp_path):
        """Test writing Unicode content."""
        dest = tmp_path / "test.txt"
        content = "Hello, 世界! 🌍"

        atomic_write(content, dest)

        assert dest.read_text() == content

    def test_write_empty_content(self, tmp_path):
        """Test writing empty content."""
        dest = tmp_path / "test.txt"
        atomic_write("", dest)

        assert dest.exists()
        assert dest.read_text() == ""

    def test_write_is_atomic(self, tmp_path):
        """Test that write is atomic (no partial writes)."""
        dest = tmp_path / "test.txt"
        dest.write_text("Original")

        # Write should complete fully or not at all
        large_content = "x" * 100000
        atomic_write(large_content, dest)

        # File should have complete new content
        assert dest.read_text() == large_content

    def test_no_temp_files_left_behind(self, tmp_path):
        """Test that no temporary files are left in directory."""
        dest = tmp_path / "test.txt"

        atomic_write("Content", dest)

        # Check no .tmp files left
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

        # Check no hidden temp files left
        hidden_files = list(tmp_path.glob(".*"))
        assert len(hidden_files) == 0
