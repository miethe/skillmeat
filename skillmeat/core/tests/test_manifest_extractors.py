"""Unit tests for manifest extractors.

Tests the extract_skill_manifest function including frontmatter parsing,
fallback to H1 headings, tag extraction, and error handling.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from skillmeat.core.manifest_extractors import extract_skill_manifest


class TestExtractSkillManifest:
    """Test skill manifest extraction from SKILL.md files."""

    def test_full_frontmatter(self, tmp_path: Path) -> None:
        """Test extraction with complete frontmatter."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: My Awesome Skill
description: Does something useful
tags: [automation, productivity]
version: 1.0.0
---

# My Awesome Skill

Content here...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "My Awesome Skill"
        assert result["description"] == "Does something useful"
        assert result["tags"] == ["automation", "productivity"]
        assert result["raw_metadata"]["version"] == "1.0.0"

    def test_frontmatter_title_only(self, tmp_path: Path) -> None:
        """Test extraction with minimal frontmatter (title only)."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Simple Skill
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "Simple Skill"
        assert result["description"] is None
        assert result["tags"] == []

    def test_no_frontmatter_fallback_to_h1(self, tmp_path: Path) -> None:
        """Test fallback to H1 heading when no frontmatter present."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """# My Skill From Heading

This skill does things.
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "My Skill From Heading"
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_frontmatter_no_title_fallback_to_h1(self, tmp_path: Path) -> None:
        """Test fallback to H1 when frontmatter exists but has no title."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
description: A useful skill
tags: [tools]
---

# Heading Title

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "Heading Title"
        assert result["description"] == "A useful skill"
        assert result["tags"] == ["tools"]

    def test_missing_file(self, tmp_path: Path) -> None:
        """Test handling of missing file."""
        nonexistent = tmp_path / "nonexistent" / "SKILL.md"

        result = extract_skill_manifest(nonexistent)

        assert result["title"] is None
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_directory_instead_of_file(self, tmp_path: Path) -> None:
        """Test handling when path is a directory."""
        result = extract_skill_manifest(tmp_path)

        assert result["title"] is None
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty file."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("", encoding="utf-8")

        result = extract_skill_manifest(skill_file)

        assert result["title"] is None
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_whitespace_only_file(self, tmp_path: Path) -> None:
        """Test handling of whitespace-only file."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("   \n\t\n  ", encoding="utf-8")

        result = extract_skill_manifest(skill_file)

        assert result["title"] is None
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        """Test handling of malformed YAML frontmatter."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Valid Title
tags: [unclosed bracket
invalid:: yaml:: here
---

# Fallback Title

Content...
""",
            encoding="utf-8",
        )

        # Should log warning but not raise, returns partial data
        result = extract_skill_manifest(skill_file)

        # Falls back to H1 since frontmatter is invalid
        assert result["title"] == "Fallback Title"
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_unclosed_frontmatter(self, tmp_path: Path) -> None:
        """Test handling of unclosed frontmatter delimiter."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Never Closed

# Heading

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        # No valid frontmatter, falls back to H1
        assert result["title"] == "Heading"
        assert result["raw_metadata"] == {}

    def test_tags_as_comma_string(self, tmp_path: Path) -> None:
        """Test tags provided as comma-separated string."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Tagged Skill
tags: automation, productivity, tools
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == ["automation", "productivity", "tools"]

    def test_tags_as_single_value(self, tmp_path: Path) -> None:
        """Test single tag value."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Single Tag Skill
tags: automation
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == ["automation"]

    def test_tags_empty_list(self, tmp_path: Path) -> None:
        """Test empty tags list."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: No Tags Skill
tags: []
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == []

    def test_tags_with_none_values(self, tmp_path: Path) -> None:
        """Test tags list containing None values."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Mixed Tags
tags:
  - valid
  -
  - another
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        # None/empty values should be filtered out
        assert result["tags"] == ["valid", "another"]

    def test_numeric_values_converted(self, tmp_path: Path) -> None:
        """Test that numeric values are converted to strings."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: 42
tags: [1, 2, 3]
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "42"
        assert result["tags"] == ["1", "2", "3"]

    def test_raw_metadata_preserved(self, tmp_path: Path) -> None:
        """Test that all frontmatter fields are preserved in raw_metadata."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Full Metadata
description: Complete skill
tags: [a, b]
version: 2.0.0
author: test-user
custom_field: custom_value
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["raw_metadata"]["title"] == "Full Metadata"
        assert result["raw_metadata"]["version"] == "2.0.0"
        assert result["raw_metadata"]["author"] == "test-user"
        assert result["raw_metadata"]["custom_field"] == "custom_value"

    def test_frontmatter_not_at_start(self, tmp_path: Path) -> None:
        """Test that frontmatter must be at file start."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """Some text before frontmatter

---
title: Not Valid Frontmatter
---

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        # No valid frontmatter at start
        assert result["title"] is None  # No H1 heading either
        assert result["raw_metadata"] == {}

    def test_h1_with_leading_whitespace(self, tmp_path: Path) -> None:
        """Test H1 extraction handles leading whitespace."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """
   # Indented Heading

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "Indented Heading"

    def test_multiple_h1_uses_first(self, tmp_path: Path) -> None:
        """Test that first H1 is used when multiple exist."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """# First Heading

Some content

# Second Heading

More content
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "First Heading"

    def test_unicode_content(self, tmp_path: Path) -> None:
        """Test handling of Unicode content."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Unicode Skill
description: Handles emoji and special chars
tags: [internationalization, i18n]
---

Content with Unicode: cafe, ,
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "Unicode Skill"
        assert result["description"] == "Handles emoji and special chars"

    def test_empty_frontmatter(self, tmp_path: Path) -> None:
        """Test handling of empty frontmatter block."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
---

# Heading After Empty Frontmatter

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["title"] == "Heading After Empty Frontmatter"
        assert result["raw_metadata"] == {}

    def test_frontmatter_yaml_not_dict(self, tmp_path: Path) -> None:
        """Test handling when YAML parses to non-dict (e.g., list)."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
- item1
- item2
---

# Heading

Content...
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        # Non-dict frontmatter is ignored
        assert result["title"] == "Heading"
        assert result["raw_metadata"] == {}


class TestTagExtractionEdgeCases:
    """Test edge cases in tag extraction."""

    def test_empty_string_tags(self, tmp_path: Path) -> None:
        """Test that empty string tags are filtered."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Test
tags: ["", "valid", "", "another"]
---
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == ["valid", "another"]

    def test_whitespace_only_tags(self, tmp_path: Path) -> None:
        """Test that whitespace-only tags are filtered."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Test
tags: ["  ", "valid", "   "]
---
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == ["valid"]

    def test_tags_empty_string(self, tmp_path: Path) -> None:
        """Test tags as empty string."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Test
tags: ""
---
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == []

    def test_tags_whitespace_string(self, tmp_path: Path) -> None:
        """Test tags as whitespace-only string."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Test
tags: "   "
---
""",
            encoding="utf-8",
        )

        result = extract_skill_manifest(skill_file)

        assert result["tags"] == []


class TestErrorLogging:
    """Test that appropriate logging occurs for error conditions."""

    def test_missing_file_logs_error(self, tmp_path: Path, caplog) -> None:
        """Test that missing file logs error."""
        import logging

        with caplog.at_level(logging.ERROR):
            extract_skill_manifest(tmp_path / "missing.md")

        assert "not found" in caplog.text.lower()

    def test_malformed_yaml_logs_warning(self, tmp_path: Path, caplog) -> None:
        """Test that malformed YAML logs warning."""
        import logging

        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
invalid:: yaml:: content
---
""",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING):
            extract_skill_manifest(skill_file)

        assert "malformed" in caplog.text.lower() or "yaml" in caplog.text.lower()

    def test_unclosed_frontmatter_logs_warning(self, tmp_path: Path, caplog) -> None:
        """Test that unclosed frontmatter logs warning."""
        import logging

        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Never Closed
""",
            encoding="utf-8",
        )

        with caplog.at_level(logging.WARNING):
            extract_skill_manifest(skill_file)

        assert "closing" in caplog.text.lower() or "delimiter" in caplog.text.lower()


class TestExtractDeepSearchText:
    """Test deep search text extraction from artifact directories."""

    def test_extract_deep_search_text_basic(self, tmp_path: Path) -> None:
        """Test basic extraction with .md and .py files."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        # Create test artifact directory with various files
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create markdown file
        (skill_dir / "README.md").write_text(
            "# Test Skill\n\nThis is a test skill for deep search.",
            encoding="utf-8",
        )

        # Create Python file
        (skill_dir / "script.py").write_text(
            'def hello():\n    """Say hello."""\n    print("Hello world")',
            encoding="utf-8",
        )

        # Create YAML file
        (skill_dir / "config.yaml").write_text(
            "name: test\nversion: 1.0.0",
            encoding="utf-8",
        )

        text, files = extract_deep_search_text(skill_dir)

        # Verify all files were indexed
        assert len(files) == 3
        assert "README.md" in files
        assert "script.py" in files
        assert "config.yaml" in files

        # Verify content was extracted and normalized
        assert "Test Skill" in text
        assert "test skill for deep search" in text
        assert "Say hello" in text
        assert "Hello world" in text
        assert "version: 1.0.0" in text

        # Verify whitespace is normalized (no multiple spaces/newlines)
        assert "\n\n" not in text
        assert "  " not in text

    def test_extract_deep_search_text_skips_large_files(self, tmp_path: Path) -> None:
        """Test that files >100KB are skipped."""
        from skillmeat.core.manifest_extractors import (
            extract_deep_search_text,
            MAX_FILE_SIZE_BYTES,
        )

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create a small file that will be indexed
        (skill_dir / "small.md").write_text("Small file content", encoding="utf-8")

        # Create a large file that should be skipped
        large_content = "x" * (MAX_FILE_SIZE_BYTES + 1000)
        (skill_dir / "large.md").write_text(large_content, encoding="utf-8")

        text, files = extract_deep_search_text(skill_dir)

        # Only small file should be indexed
        assert len(files) == 1
        assert "small.md" in files
        assert "large.md" not in files

        # Only small file content should be in text
        assert "Small file content" in text
        assert len(text) < 100  # Much smaller than large file

    def test_extract_deep_search_text_skips_binary(self, tmp_path: Path) -> None:
        """Test that binary files (with null bytes) are skipped."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create a text file
        (skill_dir / "text.txt").write_text("Plain text file", encoding="utf-8")

        # Create a binary file with null bytes
        binary_file = skill_dir / "binary.bin"
        with open(binary_file, "wb") as f:
            f.write(b"Some text\x00\x00\x00binary data")

        # Create another file with .py extension but binary content
        binary_py = skill_dir / "compiled.py"
        with open(binary_py, "wb") as f:
            f.write(b"\x00\x01\x02\x03binary python")

        text, files = extract_deep_search_text(skill_dir)

        # Only text file should be indexed
        assert len(files) == 1
        assert "text.txt" in files
        assert "binary.bin" not in files
        assert "compiled.py" not in files

        # Only text file content in result
        assert "Plain text file" in text
        assert "binary data" not in text

    def test_extract_deep_search_text_truncates_total(self, tmp_path: Path) -> None:
        """Test that total content is truncated at 1MB with marker."""
        from skillmeat.core.manifest_extractors import (
            extract_deep_search_text,
            MAX_TOTAL_TEXT_BYTES,
            MAX_FILE_SIZE_BYTES,
        )

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create multiple files that together exceed 1MB
        # Each file is 80KB (under MAX_FILE_SIZE_BYTES), so 15 files = 1.2MB total
        chunk_size = 80_000
        num_files = 15
        assert chunk_size < MAX_FILE_SIZE_BYTES  # Ensure files will be indexed
        assert (
            chunk_size * num_files > MAX_TOTAL_TEXT_BYTES
        )  # Ensure total exceeds limit

        for i in range(num_files):
            content = f"File {i}: " + ("x" * chunk_size)
            (skill_dir / f"file{i:02d}.txt").write_text(content, encoding="utf-8")

        text, files = extract_deep_search_text(skill_dir)

        # Some files should be indexed (but not all)
        assert len(files) >= 1  # At least some files indexed
        assert len(files) < num_files  # Not all files indexed (due to limit)

        # Total text should be at or near the limit
        text_bytes = len(text.encode("utf-8"))
        assert text_bytes <= MAX_TOTAL_TEXT_BYTES

        # Should have truncation marker at the end
        assert text.endswith("...[truncated]")

    def test_extract_deep_search_text_empty_directory(self, tmp_path: Path) -> None:
        """Test that empty directory returns empty string and empty list."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()

        text, files = extract_deep_search_text(skill_dir)

        assert text == ""
        assert files == []

    def test_extract_deep_search_text_nested_files(self, tmp_path: Path) -> None:
        """Test that recursive glob works for nested directory structure."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "nested-skill"
        skill_dir.mkdir()

        # Create nested directory structure
        (skill_dir / "SKILL.md").write_text("# Main Skill", encoding="utf-8")

        subdir = skill_dir / "docs"
        subdir.mkdir()
        (subdir / "guide.md").write_text("User guide content", encoding="utf-8")

        deep_dir = subdir / "examples"
        deep_dir.mkdir()
        (deep_dir / "example.py").write_text("# Example code", encoding="utf-8")

        text, files = extract_deep_search_text(skill_dir)

        # All nested files should be indexed
        assert len(files) == 3
        assert "SKILL.md" in files
        assert (
            "docs/guide.md" in files or "docs\\guide.md" in files
        )  # Handle Windows paths
        assert (
            "docs/examples/example.py" in files or "docs\\examples\\example.py" in files
        )

        # All content should be extracted
        assert "Main Skill" in text
        assert "User guide content" in text
        assert "Example code" in text

    def test_extract_deep_search_text_no_indexable_files(self, tmp_path: Path) -> None:
        """Test directory with only non-indexable file extensions."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create files with extensions not in INDEXABLE_PATTERNS
        (skill_dir / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (skill_dir / "data.db").write_bytes(b"SQLite format 3\x00")
        (skill_dir / "archive.zip").write_bytes(b"PK\x03\x04")

        text, files = extract_deep_search_text(skill_dir)

        assert text == ""
        assert files == []

    def test_extract_deep_search_text_mixed_encodings(self, tmp_path: Path) -> None:
        """Test handling of files with encoding errors."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create a file with valid UTF-8
        (skill_dir / "valid.txt").write_text("Valid UTF-8 content", encoding="utf-8")

        # Create a file with invalid UTF-8 bytes (but not null bytes, so not binary)
        invalid_file = skill_dir / "invalid.txt"
        with open(invalid_file, "wb") as f:
            # Latin-1 encoded text that's invalid UTF-8
            f.write(b"Some text \xff\xfe here")

        text, files = extract_deep_search_text(skill_dir)

        # Both files should be indexed (errors='replace' handles invalid UTF-8)
        assert len(files) == 2
        assert "valid.txt" in files
        assert "invalid.txt" in files

        # Valid content should be present
        assert "Valid UTF-8 content" in text

    def test_extract_deep_search_text_nonexistent_directory(
        self, tmp_path: Path
    ) -> None:
        """Test handling of nonexistent directory."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        nonexistent = tmp_path / "does-not-exist"

        text, files = extract_deep_search_text(nonexistent)

        assert text == ""
        assert files == []

    def test_extract_deep_search_text_file_not_directory(self, tmp_path: Path) -> None:
        """Test handling when path is a file instead of directory."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        # Create a file instead of directory
        file_path = tmp_path / "file.txt"
        file_path.write_text("Not a directory", encoding="utf-8")

        text, files = extract_deep_search_text(file_path)

        assert text == ""
        assert files == []

    def test_extract_deep_search_text_whitespace_normalization(
        self, tmp_path: Path
    ) -> None:
        """Test that whitespace normalization works correctly."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create file with excessive whitespace
        (skill_dir / "whitespace.md").write_text(
            "Multiple    spaces\n\n\nMultiple\n\nnewlines\t\ttabs",
            encoding="utf-8",
        )

        text, files = extract_deep_search_text(skill_dir)

        # All whitespace should be normalized to single spaces
        assert "Multiple spaces" in text
        assert "Multiple newlines tabs" in text
        assert "    " not in text  # No multiple spaces
        assert "\n" not in text  # No newlines
        assert "\t" not in text  # No tabs

    def test_extract_deep_search_text_empty_files_excluded(
        self, tmp_path: Path
    ) -> None:
        """Test that empty or whitespace-only files don't contribute to output."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create empty file
        (skill_dir / "empty.txt").write_text("", encoding="utf-8")

        # Create whitespace-only file
        (skill_dir / "whitespace.md").write_text("   \n\t\n   ", encoding="utf-8")

        # Create file with actual content
        (skill_dir / "content.py").write_text("print('hello')", encoding="utf-8")

        text, files = extract_deep_search_text(skill_dir)

        # Only the file with content should be indexed
        assert len(files) == 1
        assert "content.py" in files

        assert "hello" in text
        assert len(text) < 50  # Should be short, just the one file

    def test_extract_deep_search_text_respects_indexable_patterns(
        self, tmp_path: Path
    ) -> None:
        """Test that only files matching INDEXABLE_PATTERNS are processed."""
        from skillmeat.core.manifest_extractors import extract_deep_search_text

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create files with indexable extensions
        (skill_dir / "doc.md").write_text("Markdown content", encoding="utf-8")
        (skill_dir / "config.yaml").write_text("yaml: content", encoding="utf-8")
        (skill_dir / "data.json").write_text('{"key": "value"}', encoding="utf-8")
        (skill_dir / "readme.txt").write_text("Text file", encoding="utf-8")
        (skill_dir / "script.py").write_text("# Python", encoding="utf-8")
        (skill_dir / "app.ts").write_text("// TypeScript", encoding="utf-8")
        (skill_dir / "app.js").write_text("// JavaScript", encoding="utf-8")

        # Create files with non-indexable extensions
        (skill_dir / "data.csv").write_text("col1,col2", encoding="utf-8")
        (skill_dir / "style.css").write_text("body { }", encoding="utf-8")
        (skill_dir / "page.html").write_text("<html></html>", encoding="utf-8")

        text, files = extract_deep_search_text(skill_dir)

        # Only indexable files should be present
        indexable_count = 7  # md, yaml, json, txt, py, ts, js
        assert len(files) == indexable_count

        # Verify indexable content is present
        assert "Markdown content" in text
        assert "yaml: content" in text
        assert '"key": "value"' in text
        assert "Text file" in text
        assert "Python" in text
        assert "TypeScript" in text
        assert "JavaScript" in text

        # Verify non-indexable content is not present
        assert "col1,col2" not in text
        assert "body { }" not in text
        assert "<html>" not in text
