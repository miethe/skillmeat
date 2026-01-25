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
