"""Unit tests for content hashing utilities.

Tests content-based deduplication via SHA256 hashing of files and artifacts.
"""

import hashlib
import logging
from unittest.mock import patch

import pytest

from skillmeat.core.marketplace.content_hash import (
    MAX_HASH_FILE_SIZE,
    ContentHashCache,
    compute_artifact_hash,
    compute_file_hash,
)


# Test fixtures
@pytest.fixture
def sample_content():
    """Provide sample content for testing."""
    return {
        "simple": "Hello, World!",
        "empty": "",
        "unicode": "Hello, 世界! 🌍",
        "multiline": "Line 1\nLine 2\nLine 3",
    }


@pytest.fixture
def sample_files():
    """Provide sample file dictionaries for artifact hashing."""
    return {
        "single": {
            "SKILL.md": "# My Skill\n\nContent here.",
        },
        "multiple": {
            "SKILL.md": "# Canvas Design\n\nA skill for design tasks.",
            "README.md": "## Documentation\n\nHow to use this skill.",
            "config.toml": '[skill]\nname = "canvas"',
        },
        "empty": {},
    }


# compute_file_hash() tests
class TestComputeFileHash:
    """Test suite for compute_file_hash function."""

    def test_string_input_produces_correct_hash(self):
        """Test that string input produces correct SHA256 hex digest."""
        content = "Hello, World!"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result = compute_file_hash(content)

        assert result == expected
        assert len(result) == 64  # SHA256 produces 64 hex characters
        assert result.islower()  # Should be lowercase

    def test_bytes_input_produces_same_hash(self):
        """Test that bytes input produces same result as string."""
        content_str = "Hello, World!"
        content_bytes = content_str.encode("utf-8")

        hash_str = compute_file_hash(content_str)
        hash_bytes = compute_file_hash(content_bytes)

        assert hash_str == hash_bytes

    def test_empty_string_returns_hash(self):
        """Test that empty string is hashed correctly."""
        result = compute_file_hash("")

        # Known SHA256 hash of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_deterministic_same_input_same_output(self):
        """Test that same input always produces same output."""
        content = "Test content for determinism"

        hash1 = compute_file_hash(content)
        hash2 = compute_file_hash(content)
        hash3 = compute_file_hash(content)

        assert hash1 == hash2 == hash3

    def test_different_content_different_hash(self):
        """Test that different content produces different hashes."""
        content1 = "Content A"
        content2 = "Content B"

        hash1 = compute_file_hash(content1)
        hash2 = compute_file_hash(content2)

        assert hash1 != hash2

    def test_unicode_content(self, sample_content):
        """Test handling of Unicode characters."""
        unicode_content = sample_content["unicode"]
        result = compute_file_hash(unicode_content)

        assert result is not None
        assert len(result) == 64

        # Verify it's the same as manually encoding
        expected = hashlib.sha256(unicode_content.encode("utf-8")).hexdigest()
        assert result == expected

    @pytest.mark.parametrize(
        "size_bytes,should_succeed",
        [
            (1_000, True),  # 1KB - well under limit
            (1_000_000, True),  # 1MB - under limit
            (10 * 1024 * 1024 - 1000, True),  # Just under 10MB limit
            (10 * 1024 * 1024, True),  # Exactly at 10MB limit
            (10 * 1024 * 1024 + 1, False),  # Just over 10MB limit
            (11 * 1024 * 1024, False),  # 11MB - over limit
        ],
    )
    def test_size_limits(self, size_bytes, should_succeed):
        """Test that size limits are enforced correctly."""
        content = "x" * size_bytes

        result = compute_file_hash(content)

        if should_succeed:
            assert result is not None
            assert len(result) == 64
        else:
            assert result is None

    def test_oversized_content_logs_warning(self, caplog):
        """Test that oversized content logs warning message."""
        large_content = "x" * (11 * 1024 * 1024)  # 11MB

        with caplog.at_level(logging.WARNING):
            result = compute_file_hash(large_content)

        assert result is None
        assert len(caplog.records) == 1
        assert "exceeds maximum hash size limit" in caplog.text
        assert "11.00 MB" in caplog.text
        assert "10.00 MB" in caplog.text

    def test_custom_max_size_parameter(self):
        """Test that custom max_size parameter is respected."""
        content = "x" * 1000  # 1KB content

        # With default limit (10MB) - should succeed
        result_default = compute_file_hash(content)
        assert result_default is not None

        # With custom small limit (500 bytes) - should fail
        result_custom = compute_file_hash(content, max_size=500)
        assert result_custom is None

        # With custom large limit (2000 bytes) - should succeed
        result_large = compute_file_hash(content, max_size=2000)
        assert result_large is not None
        assert result_large == result_default  # Same hash

    def test_max_size_none_disables_limit(self):
        """Test that max_size=None disables size checking."""
        large_content = "x" * (11 * 1024 * 1024)  # 11MB - normally too large

        result = compute_file_hash(large_content, max_size=None)

        assert result is not None
        assert len(result) == 64

    def test_multiline_content(self, sample_content):
        """Test handling of multiline content."""
        multiline = sample_content["multiline"]
        result = compute_file_hash(multiline)

        assert result is not None
        # Verify newlines are preserved in hash
        expected = hashlib.sha256(multiline.encode("utf-8")).hexdigest()
        assert result == expected


# compute_artifact_hash() tests
class TestComputeArtifactHash:
    """Test suite for compute_artifact_hash function."""

    def test_single_file_hash(self, sample_files):
        """Test hashing artifact with single file."""
        single_file = sample_files["single"]

        result = compute_artifact_hash(single_file)

        assert result is not None
        assert len(result) == 64
        assert result.islower()

    def test_multiple_files_deterministic(self, sample_files):
        """Test that multiple files produce deterministic hash."""
        multiple_files = sample_files["multiple"]

        hash1 = compute_artifact_hash(multiple_files)
        hash2 = compute_artifact_hash(multiple_files)

        assert hash1 == hash2

    def test_empty_dict_returns_empty_string_hash(self, sample_files):
        """Test that empty dict returns hash of empty string."""
        empty_files = sample_files["empty"]

        result = compute_artifact_hash(empty_files)

        # Should match empty string hash
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_order_independence(self):
        """Test that file order doesn't affect hash (sorted by filename)."""
        files_order1 = {
            "a.txt": "Content A",
            "b.txt": "Content B",
            "c.txt": "Content C",
        }

        files_order2 = {
            "c.txt": "Content C",
            "a.txt": "Content A",
            "b.txt": "Content B",
        }

        files_order3 = {
            "b.txt": "Content B",
            "c.txt": "Content C",
            "a.txt": "Content A",
        }

        hash1 = compute_artifact_hash(files_order1)
        hash2 = compute_artifact_hash(files_order2)
        hash3 = compute_artifact_hash(files_order3)

        assert hash1 == hash2 == hash3

    def test_filename_affects_hash(self):
        """Test that changing filename changes hash (even with same content)."""
        files1 = {"file.txt": "Same content"}
        files2 = {"other.txt": "Same content"}

        hash1 = compute_artifact_hash(files1)
        hash2 = compute_artifact_hash(files2)

        assert hash1 != hash2

    def test_content_affects_hash(self):
        """Test that changing content changes hash."""
        files1 = {"file.txt": "Content A"}
        files2 = {"file.txt": "Content B"}

        hash1 = compute_artifact_hash(files1)
        hash2 = compute_artifact_hash(files2)

        assert hash1 != hash2

    def test_mixed_large_small_files_skips_large(self, caplog):
        """Test that large files are skipped with warning."""
        mixed_files = {
            "small.txt": "Small content",
            "huge.bin": "x" * (11 * 1024 * 1024),  # 11MB - exceeds limit
            "medium.md": "Medium content",
        }

        with caplog.at_level(logging.WARNING):
            result = compute_artifact_hash(mixed_files)

        # Should return a hash (from small files only)
        assert result is not None
        assert len(result) == 64

        # Should log warning about skipping large file
        assert len(caplog.records) >= 1
        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("huge.bin" in msg for msg in warning_messages)
        assert any("11.00 MB" in msg for msg in warning_messages)

    def test_all_files_too_large_returns_empty_hash(self, caplog):
        """Test artifact with all files exceeding limit."""
        all_large = {
            "large1.bin": "x" * (11 * 1024 * 1024),
            "large2.bin": "y" * (12 * 1024 * 1024),
        }

        with caplog.at_level(logging.INFO):
            result = compute_artifact_hash(all_large)

        # Should return hash of empty string (all files skipped)
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

        # Should log info about skipped files
        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("0/2 files" in msg for msg in info_messages)

    def test_hash_includes_delimiters(self):
        """Test that hash format includes filename delimiters."""
        files = {"test.txt": "content"}

        # Manually construct expected canonical format
        canonical = "---test.txt---\ncontent\n"
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        result = compute_artifact_hash(files)

        assert result == expected

    def test_sorting_by_filename(self):
        """Test that files are sorted alphabetically by filename."""
        # Create files in specific order to verify sorting
        files = {
            "z-last.txt": "Z",
            "a-first.txt": "A",
            "m-middle.txt": "M",
        }

        # Expected canonical form (sorted: a, m, z)
        canonical = "---a-first.txt---\nA\n---m-middle.txt---\nM\n---z-last.txt---\nZ\n"
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        result = compute_artifact_hash(files)

        assert result == expected

    def test_unicode_filenames_and_content(self):
        """Test handling of Unicode in filenames and content."""
        files = {
            "file_世界.txt": "Content with unicode: 🌍",
            "normal.txt": "Regular content",
        }

        result = compute_artifact_hash(files)

        assert result is not None
        assert len(result) == 64

    def test_very_long_filenames(self):
        """Test handling of very long filenames."""
        long_filename = "a" * 500 + ".txt"  # 500 character filename
        files = {long_filename: "content"}

        result = compute_artifact_hash(files)

        assert result is not None
        assert len(result) == 64


# ContentHashCache tests
class TestContentHashCache:
    """Test suite for ContentHashCache class."""

    def test_initialization_default_size(self):
        """Test cache initializes with default max size."""
        cache = ContentHashCache()

        assert cache.size() == 0
        assert cache._max_size == 1000  # Default

    def test_initialization_custom_size(self):
        """Test cache initializes with custom max size."""
        cache = ContentHashCache(max_size=100)

        assert cache.size() == 0
        assert cache._max_size == 100

    def test_cache_miss_computes_hash(self):
        """Test that cache miss computes and caches hash."""
        cache = ContentHashCache()
        content = "Test content"

        result = cache.get_or_compute("file.txt", content)

        assert result is not None
        assert len(result) == 64
        assert cache.size() == 1

    def test_cache_hit_returns_same_hash(self):
        """Test that cache hit returns same hash without recomputing."""
        cache = ContentHashCache()
        content = "Test content"

        # First call - cache miss
        hash1 = cache.get_or_compute("file.txt", content)

        # Second call - cache hit
        hash2 = cache.get_or_compute("file.txt", content)

        assert hash1 == hash2
        assert cache.size() == 1  # Only one entry

    def test_different_paths_same_content_different_cache_entries(self):
        """Test that different paths with same content create separate entries."""
        cache = ContentHashCache()
        content = "Same content"

        hash1 = cache.get_or_compute("path1/file.txt", content)
        hash2 = cache.get_or_compute("path2/file.txt", content)

        assert hash1 == hash2  # Hashes are same (same content)
        assert cache.size() == 2  # But cached separately (different paths)

    def test_same_path_different_content_different_cache_entries(self):
        """Test that same path with different content creates new entry."""
        cache = ContentHashCache()
        path = "file.txt"

        hash1 = cache.get_or_compute(path, "Content 1")
        hash2 = cache.get_or_compute(path, "Content 2")

        assert hash1 != hash2  # Different hashes
        assert cache.size() == 2  # Separate cache entries

    def test_max_size_eviction_fifo(self):
        """Test that cache evicts oldest entry when max size exceeded (FIFO)."""
        cache = ContentHashCache(max_size=3)

        # Add 3 entries (fill cache)
        hash1 = cache.get_or_compute("file1.txt", "Content 1")
        hash2 = cache.get_or_compute("file2.txt", "Content 2")
        hash3 = cache.get_or_compute("file3.txt", "Content 3")

        assert cache.size() == 3

        # Add 4th entry - should evict first (oldest)
        hash4 = cache.get_or_compute("file4.txt", "Content 4")

        assert cache.size() == 3  # Still at max

        # First entry should be evicted - recompute will create new entry
        hash1_recompute = cache.get_or_compute("file1.txt", "Content 1")
        assert hash1 == hash1_recompute  # Same content = same hash
        assert cache.size() == 3  # Size stays at max (evicted file2)

    def test_clear_removes_all_entries(self):
        """Test that clear() removes all cached entries."""
        cache = ContentHashCache()

        # Add multiple entries
        cache.get_or_compute("file1.txt", "Content 1")
        cache.get_or_compute("file2.txt", "Content 2")
        cache.get_or_compute("file3.txt", "Content 3")

        assert cache.size() == 3

        # Clear cache
        cache.clear()

        assert cache.size() == 0

    def test_size_returns_current_count(self):
        """Test that size() returns current number of entries."""
        cache = ContentHashCache()

        assert cache.size() == 0

        cache.get_or_compute("file1.txt", "Content 1")
        assert cache.size() == 1

        cache.get_or_compute("file2.txt", "Content 2")
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0

    def test_none_results_not_cached(self):
        """Test that None results (oversized content) are not cached."""
        cache = ContentHashCache()
        large_content = "x" * (11 * 1024 * 1024)  # 11MB - exceeds limit

        result = cache.get_or_compute("large.bin", large_content)

        assert result is None
        assert cache.size() == 0  # Not cached

    def test_cache_key_includes_content_hash(self):
        """Test that cache key is based on content, not just path."""
        cache = ContentHashCache()

        # Same path, different content
        hash1 = cache.get_or_compute("file.txt", "Content A")
        hash2 = cache.get_or_compute("file.txt", "Content B")

        # Should create two different cache entries
        assert hash1 != hash2
        assert cache.size() == 2

    def test_bytes_and_string_content_cached_identically(self):
        """Test that bytes and string versions of same content use same cache entry."""
        cache = ContentHashCache()
        content_str = "Test content"
        content_bytes = content_str.encode("utf-8")

        # Get hash for string
        hash_str = cache.get_or_compute("file.txt", content_str)

        # Get hash for bytes (should hit the same cache entry)
        hash_bytes = cache.get_or_compute("file.txt", content_bytes)

        # Hashes should be the same (same content)
        assert hash_str == hash_bytes

        # Should use same cache entry (cache key is based on content hash)
        assert cache.size() == 1


# Edge cases and integration tests
class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_binary_like_strings(self):
        """Test handling of binary-like string content."""
        binary_like = "\x00\x01\x02\xFF\xFE\xFD"

        result = compute_file_hash(binary_like)

        assert result is not None
        assert len(result) == 64

    def test_very_long_content_under_limit(self):
        """Test handling of large content just under the limit."""
        # 9.9 MB - just under 10MB limit
        large_content = "x" * int(9.9 * 1024 * 1024)

        result = compute_file_hash(large_content)

        assert result is not None
        assert len(result) == 64

    def test_artifact_with_single_file_vs_direct_hash(self):
        """Test that artifact hash differs from direct file hash (includes delimiter)."""
        content = "Test content"
        files = {"file.txt": content}

        direct_hash = compute_file_hash(content)
        artifact_hash = compute_artifact_hash(files)

        # Hashes should differ because artifact hash includes filename delimiter
        assert direct_hash != artifact_hash

    def test_cache_with_unicode_path(self):
        """Test cache with Unicode characters in path."""
        cache = ContentHashCache()
        unicode_path = "files/文件_🌍.txt"
        content = "Content"

        result = cache.get_or_compute(unicode_path, content)

        assert result is not None
        assert cache.size() == 1

    @pytest.mark.parametrize(
        "content,expected_none",
        [
            ("", False),  # Empty - should hash
            ("small", False),  # Small - should hash
            ("x" * (10 * 1024 * 1024), False),  # Exactly at limit - should hash
            ("x" * (10 * 1024 * 1024 + 1), True),  # Over limit - should return None
        ],
    )
    def test_boundary_conditions(self, content, expected_none):
        """Test boundary conditions around size limit."""
        result = compute_file_hash(content)

        if expected_none:
            assert result is None
        else:
            assert result is not None
            assert len(result) == 64

    def test_artifact_hash_with_empty_file_content(self):
        """Test artifact hash with files containing empty strings."""
        files = {
            "empty.txt": "",
            "content.txt": "Has content",
            "also_empty.txt": "",
        }

        result = compute_artifact_hash(files)

        assert result is not None
        assert len(result) == 64

    def test_cache_eviction_order(self):
        """Test that cache evicts entries in FIFO order."""
        cache = ContentHashCache(max_size=2)

        # Add entries in order: A, B
        cache.get_or_compute("A.txt", "Content A")
        cache.get_or_compute("B.txt", "Content B")
        assert cache.size() == 2

        # Add C - should evict A (first in)
        cache.get_or_compute("C.txt", "Content C")
        assert cache.size() == 2

        # Recomputing A should work (was evicted)
        cache.get_or_compute("A.txt", "Content A")
        assert cache.size() == 2  # Evicts B

        # Recomputing C should still work (not evicted)
        hash_c1 = cache.get_or_compute("C.txt", "Content C")
        hash_c2 = cache.get_or_compute("C.txt", "Content C")
        assert hash_c1 == hash_c2

    def test_newline_variations(self):
        """Test that different newline styles produce different hashes."""
        content_lf = "Line 1\nLine 2"
        content_crlf = "Line 1\r\nLine 2"

        hash_lf = compute_file_hash(content_lf)
        hash_crlf = compute_file_hash(content_crlf)

        # Different newlines = different hashes
        assert hash_lf != hash_crlf

    def test_whitespace_sensitivity(self):
        """Test that hash is sensitive to whitespace differences."""
        content1 = "word1 word2"
        content2 = "word1  word2"  # Double space

        hash1 = compute_file_hash(content1)
        hash2 = compute_file_hash(content2)

        assert hash1 != hash2
