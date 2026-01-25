"""Integration tests for deep indexing functionality.

This test suite verifies the deep search text extraction from artifact directories,
including file type filtering, size limits, binary detection, and recursive traversal.

Test Coverage:
    - Extraction of all supported file types (.md, .yaml, .json, .py, .ts, etc.)
    - Skipping of files exceeding size limits (>100KB)
    - Detection and skipping of binary files
    - Truncation at total text limit (1MB)
    - Handling of deeply nested directory structures
    - Whitespace normalization
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillmeat.core.manifest_extractors import (
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_TEXT_BYTES,
    extract_deep_search_text,
)


# =============================================================================
# Deep Indexing Tests
# =============================================================================


def test_deep_indexing_extracts_all_file_types(tmp_path: Path) -> None:
    """Verify deep indexing extracts text from all supported file types.

    Creates an artifact directory with various file types (.md, .yaml, .json,
    .py, .ts) and verifies all are included in the extracted text.
    """
    # Create artifact directory
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create files of different types with identifiable content
    test_files = {
        "README.md": "# Readme Content\n\nThis is markdown",
        "config.yaml": "key: yaml_value\nlist:\n  - item1",
        "data.json": '{"json_key": "json_value"}',
        "script.py": "def python_function():\n    return 'python'",
        "code.ts": "function typescript() { return 'ts'; }",
        "notes.txt": "Plain text notes here",
        "module.js": "export const js = 'javascript';",
    }

    for filename, content in test_files.items():
        (artifact_dir / filename).write_text(content, encoding="utf-8")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify all files were indexed
    assert len(indexed_files) == len(test_files), f"Expected {len(test_files)} files, got {len(indexed_files)}"

    # Verify each file type is represented
    indexed_basenames = {Path(f).name for f in indexed_files}
    for filename in test_files.keys():
        assert filename in indexed_basenames, f"File {filename} was not indexed"

    # Verify content is in the result (whitespace normalized)
    assert "Readme Content" in result_text
    assert "yaml_value" in result_text
    assert "json_value" in result_text
    assert "python_function" in result_text
    assert "typescript" in result_text
    assert "Plain text notes" in result_text
    assert "javascript" in result_text


def test_deep_indexing_skips_large_files(tmp_path: Path) -> None:
    """Verify files exceeding MAX_FILE_SIZE_BYTES are skipped.

    Creates a file larger than 100KB and verifies it's not included in
    the deep_search_text extraction.
    """
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create a small file that should be indexed
    small_file = artifact_dir / "small.md"
    small_content = "This should be indexed"
    small_file.write_text(small_content, encoding="utf-8")

    # Create a large file exceeding the limit
    large_file = artifact_dir / "large.md"
    # Generate content > 100KB
    large_content = "x" * (MAX_FILE_SIZE_BYTES + 1000)
    large_file.write_text(large_content, encoding="utf-8")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify only small file was indexed
    assert len(indexed_files) == 1, f"Expected 1 file indexed, got {len(indexed_files)}"
    assert "small.md" in indexed_files[0]
    assert "large.md" not in str(indexed_files)

    # Verify small file content is present
    assert small_content in result_text
    # Verify large file content is NOT present (check a unique segment)
    assert "x" * 1000 not in result_text


def test_deep_indexing_skips_binary_files(tmp_path: Path) -> None:
    """Verify binary files (with null bytes) are skipped.

    Creates a file with null bytes and verifies it's not included in the
    deep_search_text extraction.
    """
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create a text file that should be indexed
    text_file = artifact_dir / "text.md"
    text_content = "This is text content"
    text_file.write_text(text_content, encoding="utf-8")

    # Create a binary file with null bytes (simulated binary data)
    binary_file = artifact_dir / "binary.md"
    binary_content = b"Some text\x00\x01\x02Binary data here\x00\xff"
    binary_file.write_bytes(binary_content)

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify only text file was indexed
    assert len(indexed_files) == 1, f"Expected 1 file indexed, got {len(indexed_files)}"
    assert "text.md" in indexed_files[0]
    assert "binary.md" not in str(indexed_files)

    # Verify text file content is present
    assert text_content in result_text


def test_deep_indexing_truncates_at_limit(tmp_path: Path) -> None:
    """Verify truncation occurs when total text exceeds MAX_TOTAL_TEXT_BYTES.

    Creates enough content to exceed 1MB limit and verifies truncation
    with marker.
    """
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create multiple files that together exceed the limit
    num_files = 15
    # Each file ~100KB (just under individual limit)
    content_per_file = "x" * (MAX_FILE_SIZE_BYTES - 100)

    for i in range(num_files):
        file_path = artifact_dir / f"file_{i:02d}.md"
        file_path.write_text(content_per_file, encoding="utf-8")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify truncation occurred
    result_bytes = len(result_text.encode("utf-8"))
    # Should be at or near the limit (within reasonable tolerance)
    assert result_bytes <= MAX_TOTAL_TEXT_BYTES + 100, (
        f"Result size {result_bytes} exceeds limit {MAX_TOTAL_TEXT_BYTES}"
    )

    # Verify truncation marker is present
    assert "...[truncated]" in result_text or result_bytes >= MAX_TOTAL_TEXT_BYTES - 1000

    # Verify not all files were fully indexed
    assert len(indexed_files) < num_files, "Expected some files to be skipped due to limit"


def test_deep_indexing_handles_nested_structure(tmp_path: Path) -> None:
    """Verify recursive extraction works with deeply nested directories.

    Creates a deeply nested directory structure and verifies files at all
    levels are extracted correctly.
    """
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create nested structure
    nested_files = {
        "root.md": "Root level content",
        "level1/file1.md": "Level 1 content",
        "level1/level2/file2.md": "Level 2 content",
        "level1/level2/level3/file3.md": "Level 3 content",
        "level1/level2/level3/level4/file4.md": "Level 4 content",
        "level1/level2/level3/level4/level5/file5.md": "Level 5 content",
    }

    for rel_path, content in nested_files.items():
        file_path = artifact_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify all files were indexed
    assert len(indexed_files) == len(nested_files), (
        f"Expected {len(nested_files)} files, got {len(indexed_files)}"
    )

    # Verify content from all levels is present
    for content in nested_files.values():
        assert content in result_text, f"Content '{content}' not found in result"

    # Verify relative paths are correct
    for rel_path in nested_files.keys():
        assert any(rel_path in indexed_file for indexed_file in indexed_files), (
            f"Path {rel_path} not found in indexed files"
        )


def test_deep_indexing_normalizes_whitespace(tmp_path: Path) -> None:
    """Verify whitespace normalization collapses multiple spaces/newlines.

    Creates files with various whitespace patterns and verifies they are
    normalized to single spaces in the output.
    """
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create file with excessive whitespace
    file_path = artifact_dir / "whitespace.md"
    content_with_whitespace = """
    # Title


    Multiple    spaces     and


    newlines.

    Tabs\t\there\t\ttoo.
    """
    file_path.write_text(content_with_whitespace, encoding="utf-8")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify file was indexed
    assert len(indexed_files) == 1

    # Verify whitespace is normalized (no consecutive spaces/newlines)
    assert "  " not in result_text, "Found consecutive spaces in normalized text"
    assert "\n" not in result_text, "Found newlines in normalized text"
    assert "\t" not in result_text, "Found tabs in normalized text"

    # Verify content is still present (just normalized)
    assert "Title" in result_text
    assert "Multiple spaces and newlines" in result_text
    assert "Tabs here too" in result_text


def test_deep_indexing_handles_empty_directory(tmp_path: Path) -> None:
    """Verify graceful handling of empty artifact directory."""
    artifact_dir = tmp_path / "empty-artifact"
    artifact_dir.mkdir()

    # Extract from empty directory
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify empty results
    assert result_text == ""
    assert indexed_files == []


def test_deep_indexing_handles_nonexistent_directory(tmp_path: Path) -> None:
    """Verify graceful handling when artifact directory doesn't exist."""
    nonexistent_dir = tmp_path / "does-not-exist"

    # Extract from nonexistent directory
    result_text, indexed_files = extract_deep_search_text(nonexistent_dir)

    # Verify empty results with no errors
    assert result_text == ""
    assert indexed_files == []


def test_deep_indexing_handles_unsupported_file_types(tmp_path: Path) -> None:
    """Verify unsupported file types are not indexed.

    Creates files with extensions not in INDEXABLE_PATTERNS and verifies
    they are ignored.
    """
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create supported file
    supported = artifact_dir / "supported.md"
    supported.write_text("This should be indexed", encoding="utf-8")

    # Create unsupported files
    unsupported_files = [
        "image.png",
        "binary.exe",
        "archive.zip",
        "data.db",
    ]

    for filename in unsupported_files:
        (artifact_dir / filename).write_bytes(b"binary data")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify only supported file was indexed
    assert len(indexed_files) == 1
    assert "supported.md" in indexed_files[0]

    # Verify unsupported files are not in results
    for filename in unsupported_files:
        assert filename not in str(indexed_files)


def test_deep_indexing_handles_utf8_content(tmp_path: Path) -> None:
    """Verify proper handling of UTF-8 encoded content with special characters."""
    artifact_dir = tmp_path / "test-artifact"
    artifact_dir.mkdir()

    # Create file with UTF-8 content (emoji, unicode)
    file_path = artifact_dir / "unicode.md"
    unicode_content = "Hello 世界 🌍 Ñoño café"
    file_path.write_text(unicode_content, encoding="utf-8")

    # Extract deep search text
    result_text, indexed_files = extract_deep_search_text(artifact_dir)

    # Verify file was indexed
    assert len(indexed_files) == 1

    # Verify UTF-8 content is preserved
    assert "Hello" in result_text
    assert "世界" in result_text
    assert "🌍" in result_text
    assert "Ñoño" in result_text
    assert "café" in result_text
