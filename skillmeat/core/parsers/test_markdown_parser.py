"""
Tests for markdown parser with frontmatter support.
"""

import datetime

import pytest

from skillmeat.core.parsers.markdown_parser import (
    FrontmatterParseError,
    ParseResult,
    extract_metadata,
    extract_title,
    parse_markdown_with_frontmatter,
)


class TestParseMarkdownWithFrontmatter:
    """Tests for parse_markdown_with_frontmatter function."""

    def test_parse_with_valid_frontmatter(self):
        """Test parsing markdown with valid YAML frontmatter."""
        content = """---
title: Test Document
version: 1.0.0
tags:
  - test
  - example
---
# Hello World

This is the content.
"""
        result = parse_markdown_with_frontmatter(content)

        assert result.frontmatter is not None
        assert result.frontmatter["title"] == "Test Document"
        assert result.frontmatter["version"] == "1.0.0"
        assert result.frontmatter["tags"] == ["test", "example"]
        assert result.content.strip().startswith("# Hello World")
        assert result.raw == content

    def test_parse_without_frontmatter(self):
        """Test parsing markdown without frontmatter."""
        content = """# Hello World

This is just regular markdown content.
"""
        result = parse_markdown_with_frontmatter(content)

        assert result.frontmatter is None
        assert result.content == content
        assert result.raw == content

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        result = parse_markdown_with_frontmatter("")

        assert result.frontmatter is None
        assert result.content == ""
        assert result.raw == ""

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only content."""
        result = parse_markdown_with_frontmatter("   \n  \n  ")

        assert result.frontmatter is None
        assert result.content == ""

    def test_parse_empty_frontmatter(self):
        """Test parsing with empty frontmatter block."""
        content = """---
---
# Content

Body text.
"""
        result = parse_markdown_with_frontmatter(content)

        # Empty frontmatter should return None (or empty dict)
        assert result.frontmatter is None or result.frontmatter == {}
        assert "# Content" in result.content

    def test_parse_only_frontmatter(self):
        """Test parsing content with only frontmatter, no body."""
        content = """---
title: Just Frontmatter
---
"""
        result = parse_markdown_with_frontmatter(content)

        assert result.frontmatter is not None
        assert result.frontmatter["title"] == "Just Frontmatter"
        assert result.content.strip() == ""

    def test_parse_invalid_yaml_raises_error(self):
        """Test that invalid YAML in frontmatter raises error."""
        content = """---
title: Test
invalid: yaml: syntax: here
---
Content
"""
        with pytest.raises(FrontmatterParseError):
            parse_markdown_with_frontmatter(content)

    def test_parse_unclosed_frontmatter(self):
        """Test parsing with opening delimiter but no closing."""
        content = """---
title: Test
# This looks like content but no closing delimiter
"""
        result = parse_markdown_with_frontmatter(content)

        # Should treat as no frontmatter
        assert result.frontmatter is None
        assert result.content == content

    def test_parse_frontmatter_with_dashes_in_content(self):
        """Test that dashes in content don't interfere with parsing."""
        content = """---
title: Test
---
# Content

Here's some text with dashes:
- List item 1
- List item 2

---

More content after a horizontal rule.
"""
        result = parse_markdown_with_frontmatter(content)

        assert result.frontmatter is not None
        assert result.frontmatter["title"] == "Test"
        # Content should include the list and HR
        assert "- List item 1" in result.content
        assert "More content after a horizontal rule" in result.content

    def test_parse_frontmatter_with_leading_whitespace(self):
        """Test frontmatter with leading whitespace before delimiter."""
        content = """  ---
title: Test
---
Content
"""
        result = parse_markdown_with_frontmatter(content)

        assert result.frontmatter is not None
        assert result.frontmatter["title"] == "Test"

    def test_parse_complex_yaml_types(self):
        """Test frontmatter with complex YAML types."""
        content = """---
title: Complex Types
count: 42
enabled: true
ratio: 3.14
null_value: null
references:
  - path/to/file1.py
  - path/to/file2.py
metadata:
  author: John Doe
  created: 2025-12-14
---
Content
"""
        result = parse_markdown_with_frontmatter(content)

        assert result.frontmatter is not None
        assert result.frontmatter["count"] == 42
        assert result.frontmatter["enabled"] is True
        assert result.frontmatter["ratio"] == 3.14
        assert result.frontmatter["null_value"] is None
        assert isinstance(result.frontmatter["references"], list)
        assert isinstance(result.frontmatter["metadata"], dict)


class TestExtractTitle:
    """Tests for extract_title function."""

    def test_extract_title_from_frontmatter(self):
        """Test extracting title from frontmatter."""
        content = "Some content without heading"
        frontmatter = {"title": "Frontmatter Title"}

        title = extract_title(content, frontmatter)
        assert title == "Frontmatter Title"

    def test_extract_title_from_h1(self):
        """Test extracting title from first H1 heading."""
        content = """# H1 Heading

Some content here.

## H2 Heading
"""
        title = extract_title(content)
        assert title == "H1 Heading"

    def test_extract_title_frontmatter_priority(self):
        """Test that frontmatter title takes priority over H1."""
        content = "# H1 Heading in Content"
        frontmatter = {"title": "Frontmatter Title"}

        title = extract_title(content, frontmatter)
        assert title == "Frontmatter Title"

    def test_extract_title_no_title_found(self):
        """Test when no title is found."""
        content = "## H2 Heading\n\nNo H1 here."
        title = extract_title(content)
        assert title is None

    def test_extract_title_h1_with_whitespace(self):
        """Test H1 extraction with various whitespace."""
        content = """
# Title with Leading Newlines

Content
"""
        title = extract_title(content)
        assert title == "Title with Leading Newlines"

    def test_extract_title_h1_with_multiple_spaces(self):
        """Test H1 with multiple spaces after #."""
        content = "#    Title With Spaces"
        title = extract_title(content)
        assert title == "Title With Spaces"

    def test_extract_title_empty_frontmatter_title(self):
        """Test when frontmatter title is empty string."""
        content = "# H1 Title"
        frontmatter = {"title": ""}

        # Empty string in frontmatter should fall back to H1
        title = extract_title(content, frontmatter)
        # Implementation may vary - either None or H1
        assert title is None or title == "H1 Title"

    def test_extract_title_non_string_frontmatter(self):
        """Test when frontmatter title is not a string."""
        content = "# H1 Title"
        frontmatter = {"title": 123}  # Invalid type

        title = extract_title(content, frontmatter)
        # Should fall back to H1 since frontmatter title is invalid
        assert title == "H1 Title"


class TestExtractMetadata:
    """Tests for extract_metadata function."""

    def test_extract_metadata_full(self):
        """Test extracting all metadata fields."""
        content = """---
title: Test Document
purpose: Testing metadata extraction
version: 1.0.0
references:
  - path/to/file1.py
  - path/to/file2.py
last_verified: 2025-12-14
---
# Content
"""
        metadata = extract_metadata(content)

        assert metadata["title"] == "Test Document"
        assert metadata["purpose"] == "Testing metadata extraction"
        assert metadata["version"] == "1.0.0"
        assert metadata["references"] == ["path/to/file1.py", "path/to/file2.py"]
        # PyYAML parses YYYY-MM-DD as datetime.date object
        assert metadata["last_verified"] == datetime.date(2025, 12, 14)

    def test_extract_metadata_minimal(self):
        """Test extracting metadata with only title."""
        content = "# Just a Title\n\nSome content."
        metadata = extract_metadata(content)

        assert metadata["title"] == "Just a Title"
        assert metadata["purpose"] is None
        assert metadata["version"] is None
        assert metadata["references"] is None
        assert metadata["last_verified"] is None

    def test_extract_metadata_no_metadata(self):
        """Test extracting from content with no metadata."""
        content = "Just plain text, no title or frontmatter."
        metadata = extract_metadata(content)

        # All fields should be None
        assert all(value is None for value in metadata.values())

    def test_extract_metadata_invalid_frontmatter(self):
        """Test extracting metadata when frontmatter is invalid."""
        content = """---
invalid: yaml: syntax
---
Content
"""
        metadata = extract_metadata(content)

        # Should return all None values gracefully
        assert all(value is None for value in metadata.values())

    def test_extract_metadata_partial_frontmatter(self):
        """Test extracting metadata with partial frontmatter."""
        content = """---
title: Partial Metadata
version: 2.0.0
---
Content
"""
        metadata = extract_metadata(content)

        assert metadata["title"] == "Partial Metadata"
        assert metadata["version"] == "2.0.0"
        assert metadata["purpose"] is None
        assert metadata["references"] is None
        assert metadata["last_verified"] is None
