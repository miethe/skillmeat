"""Unit tests for metadata extraction utilities."""

import pytest
import yaml
from pathlib import Path

from skillmeat.utils.metadata import extract_yaml_frontmatter


class TestExtractYamlFrontmatter:
    """Test extract_yaml_frontmatter function."""

    def test_extract_simple_frontmatter(self, tmp_path):
        """Test extracting simple YAML frontmatter."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test Artifact
description: A test artifact
---

# Content here
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert metadata["title"] == "Test Artifact"
        assert metadata["description"] == "A test artifact"

    def test_extract_complex_frontmatter(self, tmp_path):
        """Test extracting complex YAML frontmatter with lists and nested structures."""
        test_file = tmp_path / "test.md"
        content = """---
title: Complex Artifact
description: A complex artifact
author: Test Author
license: MIT
version: 1.0.0
tags:
  - python
  - coding
  - testing
dependencies:
  - dep1
  - dep2
metadata:
  custom_field: value
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert metadata["title"] == "Complex Artifact"
        assert metadata["author"] == "Test Author"
        assert metadata["tags"] == ["python", "coding", "testing"]
        assert metadata["dependencies"] == ["dep1", "dep2"]
        assert metadata["metadata"]["custom_field"] == "value"

    def test_no_frontmatter_returns_none(self, tmp_path):
        """Test that file without frontmatter returns None."""
        test_file = tmp_path / "test.md"
        content = """# Just a normal markdown file

With no frontmatter.
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is None

    def test_frontmatter_not_at_start_returns_none(self, tmp_path):
        """Test that frontmatter not at start of file returns None."""
        test_file = tmp_path / "test.md"
        content = """Some content before

---
title: Test
---

More content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is None

    def test_incomplete_frontmatter_returns_none(self, tmp_path):
        """Test that incomplete frontmatter returns None."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test
description: Missing closing delimiter
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is None

    def test_empty_frontmatter(self, tmp_path):
        """Test empty frontmatter."""
        test_file = tmp_path / "test.md"
        content = """---
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        # Empty YAML should return None (not a dict)
        assert metadata is None

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Test that invalid YAML raises error."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test
invalid: [broken yaml
---

# Content
"""
        test_file.write_text(content)

        with pytest.raises(yaml.YAMLError):
            extract_yaml_frontmatter(test_file)

    def test_nonexistent_file_raises_error(self, tmp_path):
        """Test that non-existent file raises error."""
        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            extract_yaml_frontmatter(nonexistent)

    def test_frontmatter_with_extra_dashes(self, tmp_path):
        """Test frontmatter with extra dashes in delimiter."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert metadata["title"] == "Test"

    def test_frontmatter_with_spaces(self, tmp_path):
        """Test frontmatter with spaces around delimiters."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test
description: With spaces
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert metadata["title"] == "Test"

    def test_multiline_values(self, tmp_path):
        """Test frontmatter with multiline values."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test
description: |
  This is a multiline
  description that spans
  multiple lines.
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert "multiline" in metadata["description"]
        assert "multiple lines" in metadata["description"]

    def test_quoted_values(self, tmp_path):
        """Test frontmatter with quoted values."""
        test_file = tmp_path / "test.md"
        content = """---
title: "Test: With Colon"
description: 'Single quoted'
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert metadata["title"] == "Test: With Colon"
        assert metadata["description"] == "Single quoted"

    def test_boolean_and_numeric_values(self, tmp_path):
        """Test frontmatter with boolean and numeric values."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test
enabled: true
version: 1.5
count: 42
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert metadata["enabled"] is True
        assert metadata["version"] == 1.5
        assert metadata["count"] == 42

    def test_unicode_in_frontmatter(self, tmp_path):
        """Test frontmatter with Unicode characters."""
        test_file = tmp_path / "test.md"
        content = """---
title: Test 世界
author: François
description: Testing Unicode 🎉
---

# Content
"""
        test_file.write_text(content)

        metadata = extract_yaml_frontmatter(test_file)
        assert metadata is not None
        assert "世界" in metadata["title"]
        assert metadata["author"] == "François"
        assert "🎉" in metadata["description"]
