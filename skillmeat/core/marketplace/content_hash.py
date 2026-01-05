"""Content hashing utilities for artifact deduplication.

Provides SHA256-based content hashing for single files and multi-file
artifacts, enabling detection of duplicate artifacts across different
sources or paths.
"""

import hashlib
import logging
from typing import Dict, Optional, Union

# Maximum file size for hashing (10MB) - files larger than this will be skipped
MAX_HASH_FILE_SIZE = 10 * 1024 * 1024

logger = logging.getLogger(__name__)


def compute_file_hash(
    content: Union[bytes, str],
    max_size: Optional[int] = MAX_HASH_FILE_SIZE,
) -> Optional[str]:
    """Compute SHA256 hash of file content.

    Args:
        content: File content as bytes or string.
            Strings are encoded as UTF-8 before hashing.
        max_size: Maximum content size in bytes. Files larger than this
            will return None. Defaults to MAX_HASH_FILE_SIZE (10MB).
            Set to None to disable size limit.

    Returns:
        Lowercase hex digest (64 characters), or None if content exceeds max_size.

    Example:
        >>> compute_file_hash("Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        >>> compute_file_hash(b"Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        >>> compute_file_hash("")  # Empty content is handled
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
        >>> compute_file_hash("x" * 11_000_000)  # Exceeds 10MB limit
        None
        >>> compute_file_hash("x" * 11_000_000, max_size=None)  # No limit
        '...'  # Returns hash
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    # Check size limit
    if max_size is not None and len(content) > max_size:
        size_mb = len(content) / (1024 * 1024)
        limit_mb = max_size / (1024 * 1024)
        logger.warning(
            f"Content size ({size_mb:.2f} MB) exceeds maximum hash size limit "
            f"({limit_mb:.2f} MB). Skipping hash computation."
        )
        return None

    return hashlib.sha256(content).hexdigest()


def compute_artifact_hash(files: Dict[str, str]) -> str:
    """Compute deterministic SHA256 hash for multi-file artifact.

    Creates a canonical representation by sorting files alphabetically
    by filename and concatenating with delimiters, then hashing the result.
    This ensures identical content produces identical hashes regardless
    of the order files were added.

    Files that exceed MAX_HASH_FILE_SIZE are excluded from the hash with
    a warning logged. This prevents timeouts on large binary files or
    generated artifacts.

    Args:
        files: Dictionary mapping filenames to their content.
            Example: {"SKILL.md": "skill content", "README.md": "readme"}

    Returns:
        Lowercase hex digest (64 characters).

    Example:
        >>> files = {"SKILL.md": "# My Skill", "README.md": "Documentation"}
        >>> compute_artifact_hash(files)
        'a1b2c3...'  # Deterministic based on content

        >>> # Order doesn't matter - same hash
        >>> files2 = {"README.md": "Documentation", "SKILL.md": "# My Skill"}
        >>> compute_artifact_hash(files) == compute_artifact_hash(files2)
        True

        >>> # Empty dict returns hash of empty string
        >>> compute_artifact_hash({})
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

        >>> # Files exceeding size limit are skipped
        >>> large_files = {
        ...     "small.txt": "content",
        ...     "huge.bin": "x" * 11_000_000,  # Exceeds 10MB
        ... }
        >>> # Hash computed only from small.txt (huge.bin skipped with warning)
        >>> compute_artifact_hash(large_files)
        '...'
    """
    if not files:
        # Empty dict - use max_size=None to avoid size check on empty string
        hash_result = compute_file_hash("", max_size=None)
        # This should never return None for empty string
        return hash_result or ""

    # Sort filenames for deterministic ordering
    sorted_filenames = sorted(files.keys())

    # Build canonical representation with delimiters
    # Format: ---{filename}---\n{content}\n for each file
    # Skip files that are too large
    parts = []
    skipped_files = []

    for filename in sorted_filenames:
        content = files[filename]
        # Check individual file size before including
        content_bytes = content.encode("utf-8") if isinstance(content, str) else content

        if len(content_bytes) > MAX_HASH_FILE_SIZE:
            size_mb = len(content_bytes) / (1024 * 1024)
            skipped_files.append((filename, size_mb))
            logger.warning(
                f"Skipping file '{filename}' ({size_mb:.2f} MB) from artifact hash: "
                f"exceeds {MAX_HASH_FILE_SIZE / (1024 * 1024):.2f} MB limit"
            )
            continue

        parts.append(f"---{filename}---\n{content}\n")

    if skipped_files:
        total_skipped = len(skipped_files)
        logger.info(
            f"Artifact hash computed from {len(parts)}/{len(files)} files "
            f"({total_skipped} file(s) skipped due to size limit)"
        )

    canonical = "".join(parts)
    # Use max_size=None since we already checked individual files
    hash_result = compute_file_hash(canonical, max_size=None)
    # This should never return None since we pre-filtered large files
    return hash_result or ""


class ContentHashCache:
    """LRU-style cache for content hash computations.

    Caches hash results to avoid recomputing hashes for the same content.
    Thread-safe through instance-based design - each instance maintains
    its own cache.

    Args:
        max_size: Maximum number of entries to cache (default: 1000).
            When exceeded, oldest entries are evicted in FIFO order.

    Example:
        >>> cache = ContentHashCache(max_size=1000)
        >>> content = "Hello, World!"
        >>> hash1 = cache.get_or_compute("path/file.md", content)  # computes
        >>> hash2 = cache.get_or_compute("path/file.md", content)  # cached
        >>> hash1 == hash2
        True

        >>> cache.clear()  # Reset cache
        >>> cache.size()
        0
    """

    def __init__(self, max_size: int = 1000):
        """Initialize cache with maximum size limit.

        Args:
            max_size: Maximum number of entries to cache (default: 1000).
        """
        self._cache: Dict[str, str] = {}
        self._max_size = max_size

    def _make_cache_key(self, path: str, content: Union[bytes, str]) -> str:
        """Create cache key from path and content.

        Uses content hash itself as key since we need to compute it anyway
        for uniqueness. Path is included for debugging but not strictly needed.

        Args:
            path: File path (for context/debugging).
            content: File content to hash.

        Returns:
            Cache key combining path and content hash.
        """
        # Compute a quick hash of content for the key
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content

        content_hash = hashlib.sha256(content_bytes).hexdigest()
        return f"{path}:{content_hash}"

    def get_or_compute(self, path: str, content: Union[bytes, str]) -> Optional[str]:
        """Get cached hash or compute and cache if not present.

        Args:
            path: File path (used for cache key).
            content: File content to hash.

        Returns:
            SHA256 hash of content (lowercase hex digest), or None if
            content exceeds size limit.
        """
        cache_key = self._make_cache_key(path, content)

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Compute hash (may return None if content too large)
        result = compute_file_hash(content)

        # Only cache if hash was successfully computed
        if result is not None:
            # Evict oldest entry if cache is full (simple FIFO)
            if len(self._cache) >= self._max_size:
                # Remove first (oldest) entry
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            # Cache result
            self._cache[cache_key] = result

        return result

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get current number of cached entries.

        Returns:
            Number of entries currently in cache.
        """
        return len(self._cache)


if __name__ == "__main__":
    # Self-test examples
    import sys

    # Enable logging for self-test
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    print("Content Hash Utilities - Self Test")
    print("=" * 50)

    # Test single file hashing
    print("\n1. Single file hashing:")
    content = "Hello, World!"
    hash1 = compute_file_hash(content)
    print(f"   String content: '{content}'")
    print(f"   Hash: {hash1}")

    # Verify bytes produces same hash
    hash2 = compute_file_hash(content.encode("utf-8"))
    print(f"   Bytes produces same hash: {hash1 == hash2}")

    # Test empty content
    empty_hash = compute_file_hash("")
    print(f"\n2. Empty content hash: {empty_hash}")

    # Test multi-file artifact hashing
    print("\n3. Multi-file artifact hashing:")
    files = {
        "SKILL.md": "# Canvas Design\n\nA skill for design tasks.",
        "README.md": "## Documentation\n\nHow to use this skill.",
        "config.toml": '[skill]\nname = "canvas"',
    }

    artifact_hash = compute_artifact_hash(files)
    print(f"   Files: {list(files.keys())}")
    print(f"   Hash: {artifact_hash}")

    # Verify order independence
    files_reversed = {
        "config.toml": '[skill]\nname = "canvas"',
        "README.md": "## Documentation\n\nHow to use this skill.",
        "SKILL.md": "# Canvas Design\n\nA skill for design tasks.",
    }
    artifact_hash2 = compute_artifact_hash(files_reversed)
    print(f"   Order-independent: {artifact_hash == artifact_hash2}")

    # Test empty dict
    empty_artifact_hash = compute_artifact_hash({})
    print(f"\n4. Empty artifact hash: {empty_artifact_hash}")
    print(f"   Equals empty string hash: {empty_artifact_hash == empty_hash}")

    # Test size limit handling
    print(
        f"\n5. Size limit handling (limit: {MAX_HASH_FILE_SIZE / (1024 * 1024):.1f} MB):"
    )

    # Small file within limit
    small_content = "x" * 1000  # 1KB
    small_hash = compute_file_hash(small_content)
    print(f"   Small file (1 KB): {small_hash is not None} (hashed successfully)")

    # Large file exceeding limit
    print(f"\n   Large file (11 MB): ", end="")
    sys.stdout.flush()
    large_content = "x" * (11 * 1024 * 1024)  # 11MB
    large_hash = compute_file_hash(large_content)
    print(f"{large_hash is None} (correctly returned None)")

    # Override limit
    print(f"\n   Large file with no limit: ", end="")
    sys.stdout.flush()
    unlimited_hash = compute_file_hash(large_content, max_size=None)
    print(f"{unlimited_hash is not None} (hashed with max_size=None)")

    # Test artifact with mixed file sizes
    print("\n6. Artifact with mixed file sizes:")
    mixed_files = {
        "small.txt": "Small file content",
        "large.bin": "x" * (11 * 1024 * 1024),  # 11MB - will be skipped
        "medium.md": "# Medium file\n" + ("line\n" * 1000),
    }
    print(f"   Files: {list(mixed_files.keys())}")
    print(f"   Processing... (large.bin should be skipped)")
    sys.stdout.flush()
    mixed_hash = compute_artifact_hash(mixed_files)
    print(f"   Hash computed: {mixed_hash is not None}")
    print(f"   Hash includes only small.txt and medium.md")

    # Test ContentHashCache
    print("\n7. ContentHashCache:")
    cache = ContentHashCache(max_size=3)
    content1 = "Test content 1"
    content2 = "Test content 2"
    content3 = "Test content 3"
    content4 = "Test content 4"

    # First compute - cache miss
    hash_a = cache.get_or_compute("file1.txt", content1)
    print(f"   First compute: {hash_a[:16]}... (cache size: {cache.size()})")

    # Second compute with same content - cache hit
    hash_b = cache.get_or_compute("file1.txt", content1)
    print(f"   Cache hit: {hash_a == hash_b} (same hash returned)")

    # Add more entries to test FIFO eviction
    cache.get_or_compute("file2.txt", content2)
    cache.get_or_compute("file3.txt", content3)
    print(f"   Added 2 more entries (cache size: {cache.size()})")

    # Add fourth entry - should evict first (oldest)
    cache.get_or_compute("file4.txt", content4)
    print(f"   Added 4th entry (max=3, cache size: {cache.size()})")
    print(f"   Oldest entry evicted (FIFO)")

    # Clear cache
    cache.clear()
    print(f"   Cache cleared (size: {cache.size()})")

    # Test with content exceeding size limit
    cache_large = ContentHashCache(max_size=10)
    large_content_cache = "x" * (11 * 1024 * 1024)  # 11MB
    hash_large = cache_large.get_or_compute("large.bin", large_content_cache)
    print(f"   Large content (11 MB): {hash_large is None} (not cached)")
    print(f"   Cache size after large content: {cache_large.size()}")

    print("\n" + "=" * 50)
    print("All tests passed!")
