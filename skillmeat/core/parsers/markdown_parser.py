"""
Markdown parser with YAML frontmatter support.

Extracts structured metadata from markdown files used in SkillMeat artifacts.
"""

import re
import sys
from dataclasses import dataclass
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import yaml


@dataclass
class ParseResult:
    """Result of parsing markdown content with optional frontmatter.

    Attributes:
        frontmatter: Parsed YAML frontmatter as dict, or None if not present
        content: Body content (everything after frontmatter)
        raw: Original raw content
    """

    frontmatter: dict[str, Any] | None
    content: str
    raw: str


class FrontmatterParseError(Exception):
    """Error parsing YAML frontmatter."""

    pass


def parse_markdown_with_frontmatter(content: str) -> ParseResult:
    """
    Parse markdown content and extract YAML frontmatter.

    Frontmatter is expected to be at the start of the file, delimited by
    lines containing exactly '---':

        ---
        title: My Document
        version: 1.0.0
        ---
        # Content starts here

    Args:
        content: Raw markdown content

    Returns:
        ParseResult with frontmatter (dict or None) and body content

    Raises:
        FrontmatterParseError: If frontmatter exists but YAML is invalid
    """
    if not content or not content.strip():
        return ParseResult(frontmatter=None, content="", raw=content)

    # Check for frontmatter delimiter at start
    # Must start with exactly '---' (possibly with leading whitespace)
    lines = content.split("\n")
    first_line = lines[0].strip()

    if first_line != "---":
        # No frontmatter present
        return ParseResult(frontmatter=None, content=content, raw=content)

    # Find closing delimiter
    closing_delimiter_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_delimiter_idx = i
            break

    if closing_delimiter_idx is None:
        # Opening delimiter but no closing - treat as no frontmatter
        return ParseResult(frontmatter=None, content=content, raw=content)

    # Extract frontmatter content between delimiters
    frontmatter_lines = lines[1:closing_delimiter_idx]
    frontmatter_text = "\n".join(frontmatter_lines)

    # Parse YAML
    try:
        frontmatter_dict = yaml.safe_load(frontmatter_text)
        # yaml.safe_load returns None for empty content
        if frontmatter_dict is None:
            frontmatter_dict = {}
    except yaml.YAMLError as e:
        raise FrontmatterParseError(f"Invalid YAML in frontmatter: {e}")

    # Extract body content (everything after closing delimiter)
    body_lines = lines[closing_delimiter_idx + 1 :]
    body_content = "\n".join(body_lines).lstrip("\n")

    return ParseResult(
        frontmatter=frontmatter_dict if frontmatter_dict else None,
        content=body_content,
        raw=content,
    )


def extract_title(
    content: str, frontmatter: dict[str, Any] | None = None
) -> str | None:
    """
    Extract title from frontmatter 'title' field or first H1 heading.

    Priority:
        1. frontmatter['title'] if present
        2. First H1 heading (# Title) in content
        3. None if neither found

    Args:
        content: Markdown body content
        frontmatter: Parsed frontmatter dict (optional)

    Returns:
        Extracted title string, or None if not found
    """
    # Check frontmatter first
    if frontmatter and "title" in frontmatter:
        title = frontmatter["title"]
        if title and isinstance(title, str):
            return title.strip()

    # Check for first H1 heading in content
    # Match: # Title or #Title (with optional leading whitespace)
    h1_pattern = re.compile(r"^\s*#\s+(.+)$", re.MULTILINE)
    match = h1_pattern.search(content)
    if match:
        return match.group(1).strip()

    return None


def extract_metadata(content: str) -> dict[str, Any]:
    """
    Extract common metadata from markdown content.

    Extracts:
        - title: From frontmatter or first H1
        - purpose: From frontmatter
        - version: From frontmatter
        - references: From frontmatter (list of file paths)
        - last_verified: From frontmatter (ISO date string)

    Args:
        content: Raw markdown content (with or without frontmatter)

    Returns:
        Dict with extracted metadata fields (None for missing fields)
    """
    try:
        result = parse_markdown_with_frontmatter(content)
    except FrontmatterParseError:
        # If frontmatter parsing fails, return minimal metadata
        return {
            "title": None,
            "purpose": None,
            "version": None,
            "references": None,
            "last_verified": None,
        }

    frontmatter = result.frontmatter or {}

    # Extract title (frontmatter or H1)
    title = extract_title(result.content, frontmatter)

    # Extract other fields from frontmatter
    return {
        "title": title,
        "purpose": frontmatter.get("purpose"),
        "version": frontmatter.get("version"),
        "references": frontmatter.get("references"),
        "last_verified": frontmatter.get("last_verified"),
    }
