"""Unit tests for manifest extractors.

Tests manifest extraction functions for all artifact types:
- extract_skill_manifest: SKILL.md with frontmatter
- extract_command_manifest: command.yaml/yml, COMMAND.md fallback
- extract_agent_manifest: agent.yaml/yml, AGENT.md fallback
- extract_hook_manifest: hook.yaml/yml, HOOK.md fallback
- extract_mcp_manifest: mcp.json, package.json fallback
- extract_deep_search_text: Full-text indexing
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from skillmeat.core.manifest_extractors import (
    extract_skill_manifest,
    extract_command_manifest,
    extract_agent_manifest,
    extract_hook_manifest,
    extract_mcp_manifest,
    extract_manifest,
)


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


class TestExtractCommandManifest:
    """Test command manifest extraction from command.yaml/yml or COMMAND.md."""

    def test_command_yaml(self, tmp_path: Path) -> None:
        """Test extraction from valid command.yaml file."""
        cmd_dir = tmp_path / "my-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text(
            """name: my-command
description: A useful command
tools:
  - Read
  - Write
  - Bash
model: sonnet
template: |
  Execute this task:
  {{ task }}
""",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result["title"] == "my-command"
        assert result["description"] == "A useful command"
        assert result["tags"] == []  # Commands don't have tags
        assert result["raw_metadata"]["tools"] == ["Read", "Write", "Bash"]
        assert result["raw_metadata"]["model"] == "sonnet"
        assert "Execute this task" in result["raw_metadata"]["template"]

    def test_command_yml(self, tmp_path: Path) -> None:
        """Test extraction from command.yml variant."""
        cmd_dir = tmp_path / "my-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.yml").write_text(
            """name: yml-command
description: Command with .yml extension
model: opus
""",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result["title"] == "yml-command"
        assert result["description"] == "Command with .yml extension"
        assert result["raw_metadata"]["model"] == "opus"

    def test_command_yaml_precedence_over_yml(self, tmp_path: Path) -> None:
        """Test that command.yaml takes precedence over command.yml."""
        cmd_dir = tmp_path / "my-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text(
            "name: yaml-wins\ndescription: From YAML",
            encoding="utf-8",
        )
        (cmd_dir / "command.yml").write_text(
            "name: yml-loses\ndescription: From YML",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result["title"] == "yaml-wins"
        assert result["description"] == "From YAML"

    def test_command_md_fallback(self, tmp_path: Path) -> None:
        """Test fallback to COMMAND.md when no YAML exists."""
        cmd_dir = tmp_path / "my-command"
        cmd_dir.mkdir()

        (cmd_dir / "COMMAND.md").write_text(
            """---
name: markdown-command
description: Defined in markdown frontmatter
model: haiku
---

# Command Documentation

This command does something useful.
""",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result["title"] == "markdown-command"
        assert result["description"] == "Defined in markdown frontmatter"
        assert result["raw_metadata"]["model"] == "haiku"

    def test_command_md_lowercase_fallback(self, tmp_path: Path) -> None:
        """Test fallback to command.md (lowercase)."""
        cmd_dir = tmp_path / "my-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.md").write_text(
            """---
name: lowercase-md
description: Lowercase markdown file
---
""",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result["title"] == "lowercase-md"

    def test_command_missing_file(self, tmp_path: Path) -> None:
        """Test handling when no manifest file exists in directory."""
        cmd_dir = tmp_path / "empty-command"
        cmd_dir.mkdir()

        result = extract_command_manifest(cmd_dir)

        assert result == {}

    def test_command_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test handling of nonexistent directory."""
        nonexistent = tmp_path / "does-not-exist"

        result = extract_command_manifest(nonexistent)

        assert result == {}

    def test_command_file_path_directly(self, tmp_path: Path) -> None:
        """Test passing file path directly instead of directory."""
        yaml_file = tmp_path / "command.yaml"
        yaml_file.write_text(
            "name: direct-file\ndescription: Direct file path",
            encoding="utf-8",
        )

        result = extract_command_manifest(yaml_file)

        assert result["title"] == "direct-file"
        assert result["description"] == "Direct file path"

    def test_command_malformed_yaml(self, tmp_path: Path) -> None:
        """Test handling of malformed YAML content."""
        cmd_dir = tmp_path / "bad-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text(
            """name: valid
invalid:: yaml:: here
description: [unclosed bracket
""",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        # Malformed YAML returns empty dict
        assert result == {}

    def test_command_yaml_not_dict(self, tmp_path: Path) -> None:
        """Test handling when YAML parses to non-dict (e.g., list)."""
        cmd_dir = tmp_path / "list-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text(
            """- item1
- item2
- item3
""",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result == {}

    def test_command_directory_input(self, tmp_path: Path) -> None:
        """Test that directory path triggers manifest file discovery."""
        cmd_dir = tmp_path / "discover-command"
        cmd_dir.mkdir()

        # Create nested structure to ensure we're not reading wrong files
        (cmd_dir / "command.yaml").write_text(
            "name: discovered\ndescription: Found via directory",
            encoding="utf-8",
        )
        (cmd_dir / "other.yaml").write_text(
            "name: ignored\ndescription: Should not be read",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        assert result["title"] == "discovered"
        assert result["description"] == "Found via directory"

    def test_command_unsupported_extension(self, tmp_path: Path) -> None:
        """Test handling of unsupported file extension."""
        txt_file = tmp_path / "command.txt"
        txt_file.write_text("name: txt-file", encoding="utf-8")

        result = extract_command_manifest(txt_file)

        assert result == {}

    def test_command_uses_title_key_fallback(self, tmp_path: Path) -> None:
        """Test that 'title' key works as fallback for 'name'."""
        cmd_dir = tmp_path / "titled-command"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text(
            "title: title-based-command\ndescription: Uses title instead of name",
            encoding="utf-8",
        )

        result = extract_command_manifest(cmd_dir)

        # name is checked first, then title
        assert result["title"] == "title-based-command"

    def test_command_empty_yaml(self, tmp_path: Path) -> None:
        """Test handling of empty YAML file."""
        cmd_dir = tmp_path / "empty-yaml"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text("", encoding="utf-8")

        result = extract_command_manifest(cmd_dir)

        assert result == {}

    def test_command_whitespace_only_yaml(self, tmp_path: Path) -> None:
        """Test handling of whitespace-only YAML file."""
        cmd_dir = tmp_path / "whitespace-yaml"
        cmd_dir.mkdir()

        (cmd_dir / "command.yaml").write_text("   \n\t\n   ", encoding="utf-8")

        result = extract_command_manifest(cmd_dir)

        assert result == {}


class TestExtractAgentManifest:
    """Test agent manifest extraction from agent.yaml/yml or AGENT.md."""

    def test_agent_yaml(self, tmp_path: Path) -> None:
        """Test extraction from valid agent.yaml file."""
        agent_dir = tmp_path / "my-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yaml").write_text(
            """name: code-reviewer
description: Reviews code for quality and best practices
model: opus
tools:
  - Read
  - Grep
  - Glob
system_prompt: |
  You are an expert code reviewer.
""",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result["title"] == "code-reviewer"
        assert result["description"] == "Reviews code for quality and best practices"
        assert result["tags"] == []  # Agents don't have tags
        assert result["raw_metadata"]["model"] == "opus"
        assert result["raw_metadata"]["tools"] == ["Read", "Grep", "Glob"]
        assert "expert code reviewer" in result["raw_metadata"]["system_prompt"]

    def test_agent_yml(self, tmp_path: Path) -> None:
        """Test extraction from agent.yml variant."""
        agent_dir = tmp_path / "my-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yml").write_text(
            """name: yml-agent
description: Agent defined with .yml extension
model: sonnet
""",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result["title"] == "yml-agent"
        assert result["description"] == "Agent defined with .yml extension"
        assert result["raw_metadata"]["model"] == "sonnet"

    def test_agent_yaml_precedence_over_yml(self, tmp_path: Path) -> None:
        """Test that agent.yaml takes precedence over agent.yml."""
        agent_dir = tmp_path / "my-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yaml").write_text(
            "name: yaml-agent\ndescription: From YAML",
            encoding="utf-8",
        )
        (agent_dir / "agent.yml").write_text(
            "name: yml-agent\ndescription: From YML",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result["title"] == "yaml-agent"

    def test_agent_md_fallback(self, tmp_path: Path) -> None:
        """Test fallback to AGENT.md when no YAML exists."""
        agent_dir = tmp_path / "my-agent"
        agent_dir.mkdir()

        (agent_dir / "AGENT.md").write_text(
            """---
name: markdown-agent
description: Agent defined in markdown
model: haiku
---

# Agent Documentation

This agent helps with tasks.
""",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result["title"] == "markdown-agent"
        assert result["description"] == "Agent defined in markdown"

    def test_agent_md_lowercase_fallback(self, tmp_path: Path) -> None:
        """Test fallback to agent.md (lowercase)."""
        agent_dir = tmp_path / "my-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.md").write_text(
            """---
name: lowercase-agent
description: Lowercase markdown
---
""",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result["title"] == "lowercase-agent"

    def test_agent_missing_file(self, tmp_path: Path) -> None:
        """Test handling when no manifest file exists in directory."""
        agent_dir = tmp_path / "empty-agent"
        agent_dir.mkdir()

        result = extract_agent_manifest(agent_dir)

        assert result == {}

    def test_agent_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test handling of nonexistent directory."""
        nonexistent = tmp_path / "does-not-exist"

        result = extract_agent_manifest(nonexistent)

        assert result == {}

    def test_agent_malformed_yaml(self, tmp_path: Path) -> None:
        """Test handling of malformed YAML content."""
        agent_dir = tmp_path / "bad-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yaml").write_text(
            """name: broken
tools: [Read, Write
description: unclosed bracket above
""",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result == {}

    def test_agent_yaml_not_dict(self, tmp_path: Path) -> None:
        """Test handling when YAML parses to non-dict."""
        agent_dir = tmp_path / "list-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yaml").write_text(
            "- agent1\n- agent2",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result == {}

    def test_agent_file_path_directly(self, tmp_path: Path) -> None:
        """Test passing file path directly instead of directory."""
        yaml_file = tmp_path / "agent.yaml"
        yaml_file.write_text(
            "name: direct-agent\ndescription: Direct path",
            encoding="utf-8",
        )

        result = extract_agent_manifest(yaml_file)

        assert result["title"] == "direct-agent"

    def test_agent_uses_title_key_fallback(self, tmp_path: Path) -> None:
        """Test that 'title' key works as fallback for 'name'."""
        agent_dir = tmp_path / "titled-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yaml").write_text(
            "title: title-agent\ndescription: Uses title key",
            encoding="utf-8",
        )

        result = extract_agent_manifest(agent_dir)

        assert result["title"] == "title-agent"

    def test_agent_empty_yaml(self, tmp_path: Path) -> None:
        """Test handling of empty YAML file."""
        agent_dir = tmp_path / "empty-agent"
        agent_dir.mkdir()

        (agent_dir / "agent.yaml").write_text("", encoding="utf-8")

        result = extract_agent_manifest(agent_dir)

        assert result == {}


class TestExtractHookManifest:
    """Test hook manifest extraction from hook.yaml/yml or HOOK.md."""

    def test_hook_yaml(self, tmp_path: Path) -> None:
        """Test extraction from valid hook.yaml file."""
        hook_dir = tmp_path / "pre-commit"
        hook_dir.mkdir()

        (hook_dir / "hook.yaml").write_text(
            """name: pre-commit
description: Runs before commits to validate code
event: pre_commit
script: ./run-tests.sh
timeout: 30
""",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result["title"] == "pre-commit"
        assert result["description"] == "Runs before commits to validate code"
        assert result["tags"] == []  # Hooks don't have tags
        assert result["raw_metadata"]["event"] == "pre_commit"
        assert result["raw_metadata"]["script"] == "./run-tests.sh"
        assert result["raw_metadata"]["timeout"] == 30

    def test_hook_yml(self, tmp_path: Path) -> None:
        """Test extraction from hook.yml variant."""
        hook_dir = tmp_path / "post-push"
        hook_dir.mkdir()

        (hook_dir / "hook.yml").write_text(
            """name: post-push
description: Hook with .yml extension
events:
  - post_push
  - post_merge
command: deploy.sh
""",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result["title"] == "post-push"
        assert result["description"] == "Hook with .yml extension"
        assert result["raw_metadata"]["events"] == ["post_push", "post_merge"]

    def test_hook_yaml_precedence_over_yml(self, tmp_path: Path) -> None:
        """Test that hook.yaml takes precedence over hook.yml."""
        hook_dir = tmp_path / "my-hook"
        hook_dir.mkdir()

        (hook_dir / "hook.yaml").write_text(
            "name: yaml-hook\ndescription: From YAML",
            encoding="utf-8",
        )
        (hook_dir / "hook.yml").write_text(
            "name: yml-hook\ndescription: From YML",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result["title"] == "yaml-hook"

    def test_hook_md_fallback(self, tmp_path: Path) -> None:
        """Test fallback to HOOK.md when no YAML exists."""
        hook_dir = tmp_path / "my-hook"
        hook_dir.mkdir()

        (hook_dir / "HOOK.md").write_text(
            """---
name: markdown-hook
description: Hook defined in markdown
event: pre_push
---

# Hook Documentation
""",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result["title"] == "markdown-hook"
        assert result["description"] == "Hook defined in markdown"

    def test_hook_md_lowercase_fallback(self, tmp_path: Path) -> None:
        """Test fallback to hook.md (lowercase)."""
        hook_dir = tmp_path / "my-hook"
        hook_dir.mkdir()

        (hook_dir / "hook.md").write_text(
            """---
name: lowercase-hook
description: Lowercase markdown
---
""",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result["title"] == "lowercase-hook"

    def test_hook_missing_file(self, tmp_path: Path) -> None:
        """Test handling when no manifest file exists in directory."""
        hook_dir = tmp_path / "empty-hook"
        hook_dir.mkdir()

        result = extract_hook_manifest(hook_dir)

        assert result == {}

    def test_hook_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test handling of nonexistent directory."""
        nonexistent = tmp_path / "does-not-exist"

        result = extract_hook_manifest(nonexistent)

        assert result == {}

    def test_hook_malformed_yaml(self, tmp_path: Path) -> None:
        """Test handling of malformed YAML content."""
        hook_dir = tmp_path / "bad-hook"
        hook_dir.mkdir()

        (hook_dir / "hook.yaml").write_text(
            """name: broken
events: [pre_commit, post_commit
description: unclosed bracket
invalid:: colons:: here
""",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result == {}

    def test_hook_yaml_not_dict(self, tmp_path: Path) -> None:
        """Test handling when YAML parses to non-dict."""
        hook_dir = tmp_path / "list-hook"
        hook_dir.mkdir()

        (hook_dir / "hook.yaml").write_text(
            "- pre_commit\n- post_commit",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result == {}

    def test_hook_file_path_directly(self, tmp_path: Path) -> None:
        """Test passing file path directly instead of directory."""
        yaml_file = tmp_path / "hook.yaml"
        yaml_file.write_text(
            "name: direct-hook\ndescription: Direct path",
            encoding="utf-8",
        )

        result = extract_hook_manifest(yaml_file)

        assert result["title"] == "direct-hook"

    def test_hook_uses_title_key_fallback(self, tmp_path: Path) -> None:
        """Test that 'title' key works as fallback for 'name'."""
        hook_dir = tmp_path / "titled-hook"
        hook_dir.mkdir()

        (hook_dir / "hook.yaml").write_text(
            "title: title-hook\ndescription: Uses title key",
            encoding="utf-8",
        )

        result = extract_hook_manifest(hook_dir)

        assert result["title"] == "title-hook"

    def test_hook_empty_yaml(self, tmp_path: Path) -> None:
        """Test handling of empty YAML file."""
        hook_dir = tmp_path / "empty-hook"
        hook_dir.mkdir()

        (hook_dir / "hook.yaml").write_text("", encoding="utf-8")

        result = extract_hook_manifest(hook_dir)

        assert result == {}

    def test_hook_unsupported_extension(self, tmp_path: Path) -> None:
        """Test handling of unsupported file extension."""
        txt_file = tmp_path / "hook.txt"
        txt_file.write_text("name: txt-hook", encoding="utf-8")

        result = extract_hook_manifest(txt_file)

        assert result == {}


class TestExtractMcpManifest:
    """Test MCP manifest extraction from mcp.json or package.json."""

    def test_mcp_json(self, tmp_path: Path) -> None:
        """Test extraction from valid mcp.json file."""
        mcp_dir = tmp_path / "my-mcp-server"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            """{
    "name": "my-mcp-server",
    "description": "Provides context tools for file operations",
    "version": "1.0.0",
    "tools": ["read_file", "write_file", "list_directory"],
    "keywords": ["files", "filesystem", "io"]
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "my-mcp-server"
        assert result["description"] == "Provides context tools for file operations"
        assert result["tags"] == ["files", "filesystem", "io"]
        assert result["raw_metadata"]["version"] == "1.0.0"
        assert result["raw_metadata"]["tools"] == ["read_file", "write_file", "list_directory"]

    def test_mcp_json_with_tags_key(self, tmp_path: Path) -> None:
        """Test that 'tags' key also works for tag extraction."""
        mcp_dir = tmp_path / "tagged-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            """{
    "name": "tagged-server",
    "description": "Server with tags",
    "tags": ["database", "sql", "postgres"]
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["tags"] == ["database", "sql", "postgres"]

    def test_mcp_keywords_precedence_over_tags(self, tmp_path: Path) -> None:
        """Test that 'keywords' takes precedence over 'tags'."""
        mcp_dir = tmp_path / "both-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            """{
    "name": "both-server",
    "keywords": ["keyword1", "keyword2"],
    "tags": ["tag1", "tag2"]
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        # keywords is checked first in tags_keys
        assert result["tags"] == ["keyword1", "keyword2"]

    def test_mcp_package_json_fallback(self, tmp_path: Path) -> None:
        """Test fallback to package.json when no mcp.json exists."""
        mcp_dir = tmp_path / "npm-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "package.json").write_text(
            """{
    "name": "@company/mcp-server",
    "version": "2.0.0",
    "description": "MCP server from npm package",
    "keywords": ["mcp", "context", "protocol"],
    "main": "dist/index.js",
    "scripts": {
        "build": "tsc"
    }
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "@company/mcp-server"
        assert result["description"] == "MCP server from npm package"
        assert result["tags"] == ["mcp", "context", "protocol"]
        assert result["raw_metadata"]["version"] == "2.0.0"

    def test_mcp_json_precedence_over_package_json(self, tmp_path: Path) -> None:
        """Test that mcp.json takes precedence over package.json."""
        mcp_dir = tmp_path / "both-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            '{"name": "mcp-wins", "description": "From mcp.json"}',
            encoding="utf-8",
        )
        (mcp_dir / "package.json").write_text(
            '{"name": "package-loses", "description": "From package.json"}',
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "mcp-wins"
        assert result["description"] == "From mcp.json"

    def test_mcp_missing_file(self, tmp_path: Path) -> None:
        """Test handling when no manifest file exists in directory."""
        mcp_dir = tmp_path / "empty-mcp"
        mcp_dir.mkdir()

        result = extract_mcp_manifest(mcp_dir)

        assert result == {}

    def test_mcp_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test handling of nonexistent directory."""
        nonexistent = tmp_path / "does-not-exist"

        result = extract_mcp_manifest(nonexistent)

        assert result == {}

    def test_mcp_malformed_json(self, tmp_path: Path) -> None:
        """Test handling of malformed JSON content."""
        mcp_dir = tmp_path / "bad-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            '{"name": "broken", "description": "unclosed',
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result == {}

    def test_mcp_json_not_dict(self, tmp_path: Path) -> None:
        """Test handling when JSON parses to non-dict (e.g., array)."""
        mcp_dir = tmp_path / "array-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            '["item1", "item2", "item3"]',
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result == {}

    def test_mcp_file_path_directly(self, tmp_path: Path) -> None:
        """Test passing file path directly instead of directory."""
        json_file = tmp_path / "mcp.json"
        json_file.write_text(
            '{"name": "direct-mcp", "description": "Direct path"}',
            encoding="utf-8",
        )

        result = extract_mcp_manifest(json_file)

        assert result["title"] == "direct-mcp"
        assert result["description"] == "Direct path"

    def test_mcp_keywords_as_tags(self, tmp_path: Path) -> None:
        """Test that npm 'keywords' field is extracted as tags."""
        mcp_dir = tmp_path / "npm-style"
        mcp_dir.mkdir()

        (mcp_dir / "package.json").write_text(
            """{
    "name": "npm-mcp",
    "description": "NPM style package",
    "keywords": ["mcp", "server", "tools", "context-protocol"]
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["tags"] == ["mcp", "server", "tools", "context-protocol"]

    def test_mcp_empty_json(self, tmp_path: Path) -> None:
        """Test handling of empty JSON file."""
        mcp_dir = tmp_path / "empty-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text("", encoding="utf-8")

        result = extract_mcp_manifest(mcp_dir)

        assert result == {}

    def test_mcp_empty_object(self, tmp_path: Path) -> None:
        """Test handling of empty JSON object."""
        mcp_dir = tmp_path / "empty-obj"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text("{}", encoding="utf-8")

        result = extract_mcp_manifest(mcp_dir)

        # Returns standardized output with None/empty values
        assert result["title"] is None
        assert result["description"] is None
        assert result["tags"] == []
        assert result["raw_metadata"] == {}

    def test_mcp_unicode_content(self, tmp_path: Path) -> None:
        """Test handling of Unicode content in JSON."""
        mcp_dir = tmp_path / "unicode-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            """{
    "name": "unicode-server",
    "description": "Handles unicode: cafe, , "
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "unicode-server"
        assert "cafe" in result["description"]

    def test_mcp_numeric_values(self, tmp_path: Path) -> None:
        """Test that numeric values are converted to strings."""
        mcp_dir = tmp_path / "numeric-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text(
            '{"name": 123, "description": 456}',
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "123"
        assert result["description"] == "456"

    def test_mcp_nested_directory(self, tmp_path: Path) -> None:
        """Test extraction from nested directory structure."""
        mcp_dir = tmp_path / "nested" / "mcp-server"
        mcp_dir.mkdir(parents=True)

        (mcp_dir / "mcp.json").write_text(
            '{"name": "nested-mcp", "description": "In nested dir"}',
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "nested-mcp"

    def test_mcp_whitespace_json(self, tmp_path: Path) -> None:
        """Test handling of whitespace-only JSON file."""
        mcp_dir = tmp_path / "whitespace-mcp"
        mcp_dir.mkdir()

        (mcp_dir / "mcp.json").write_text("   \n\t\n   ", encoding="utf-8")

        result = extract_mcp_manifest(mcp_dir)

        assert result == {}

    def test_mcp_package_json_with_full_npm_structure(self, tmp_path: Path) -> None:
        """Test package.json with full npm structure is handled correctly."""
        mcp_dir = tmp_path / "full-npm"
        mcp_dir.mkdir()

        (mcp_dir / "package.json").write_text(
            """{
    "name": "@org/mcp-database",
    "version": "3.1.4",
    "description": "Database MCP server with PostgreSQL support",
    "main": "dist/index.js",
    "types": "dist/index.d.ts",
    "bin": {
        "mcp-db": "dist/cli.js"
    },
    "scripts": {
        "build": "tsc",
        "test": "jest",
        "start": "node dist/index.js"
    },
    "keywords": ["mcp", "database", "postgresql", "sql"],
    "author": "Developer Name",
    "license": "MIT",
    "dependencies": {
        "pg": "^8.0.0"
    },
    "devDependencies": {
        "typescript": "^5.0.0"
    }
}""",
            encoding="utf-8",
        )

        result = extract_mcp_manifest(mcp_dir)

        assert result["title"] == "@org/mcp-database"
        assert result["description"] == "Database MCP server with PostgreSQL support"
        assert result["tags"] == ["mcp", "database", "postgresql", "sql"]
        # All fields preserved in raw_metadata
        assert result["raw_metadata"]["version"] == "3.1.4"
        assert result["raw_metadata"]["author"] == "Developer Name"
        assert "pg" in result["raw_metadata"]["dependencies"]


class TestExtractManifestDispatcher:
    """Test the extract_manifest dispatcher function."""

    def test_dispatch_to_skill(self, tmp_path: Path) -> None:
        """Test that 'skill' type dispatches to extract_skill_manifest."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text(
            """---
title: Dispatched Skill
description: Via dispatcher
---
""",
            encoding="utf-8",
        )

        result = extract_manifest("skill", skill_file)

        assert result["title"] == "Dispatched Skill"
        assert result["description"] == "Via dispatcher"

    def test_dispatch_to_command(self, tmp_path: Path) -> None:
        """Test that 'command' type dispatches to extract_command_manifest."""
        cmd_dir = tmp_path / "cmd"
        cmd_dir.mkdir()
        (cmd_dir / "command.yaml").write_text(
            "name: dispatched-cmd\ndescription: Via dispatcher",
            encoding="utf-8",
        )

        result = extract_manifest("command", cmd_dir)

        assert result["title"] == "dispatched-cmd"

    def test_dispatch_to_agent(self, tmp_path: Path) -> None:
        """Test that 'agent' type dispatches to extract_agent_manifest."""
        agent_dir = tmp_path / "agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text(
            "name: dispatched-agent\ndescription: Via dispatcher",
            encoding="utf-8",
        )

        result = extract_manifest("agent", agent_dir)

        assert result["title"] == "dispatched-agent"

    def test_dispatch_to_hook(self, tmp_path: Path) -> None:
        """Test that 'hook' type dispatches to extract_hook_manifest."""
        hook_dir = tmp_path / "hook"
        hook_dir.mkdir()
        (hook_dir / "hook.yaml").write_text(
            "name: dispatched-hook\ndescription: Via dispatcher",
            encoding="utf-8",
        )

        result = extract_manifest("hook", hook_dir)

        assert result["title"] == "dispatched-hook"

    def test_dispatch_to_mcp(self, tmp_path: Path) -> None:
        """Test that 'mcp' type dispatches to extract_mcp_manifest."""
        mcp_dir = tmp_path / "mcp"
        mcp_dir.mkdir()
        (mcp_dir / "mcp.json").write_text(
            '{"name": "dispatched-mcp", "description": "Via dispatcher"}',
            encoding="utf-8",
        )

        result = extract_manifest("mcp", mcp_dir)

        assert result["title"] == "dispatched-mcp"

    def test_dispatch_case_insensitive(self, tmp_path: Path) -> None:
        """Test that artifact type is case-insensitive."""
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\ntitle: Case Test\n---", encoding="utf-8")

        result_upper = extract_manifest("SKILL", skill_file)
        result_mixed = extract_manifest("Skill", skill_file)

        assert result_upper["title"] == "Case Test"
        assert result_mixed["title"] == "Case Test"

    def test_dispatch_unknown_type(self, tmp_path: Path) -> None:
        """Test that unknown artifact type returns empty dict."""
        result = extract_manifest("unknown", tmp_path)

        assert result == {}

    def test_dispatch_empty_type(self, tmp_path: Path) -> None:
        """Test that empty artifact type returns empty dict."""
        result = extract_manifest("", tmp_path)

        assert result == {}
