"""
Content parsers for SkillMeat artifacts.

This module provides parsers for various content formats used in artifacts,
particularly markdown files with YAML frontmatter.
"""

from .markdown_parser import (
    ParseResult,
    parse_markdown_with_frontmatter,
    extract_title,
    extract_metadata,
)

__all__ = [
    "ParseResult",
    "parse_markdown_with_frontmatter",
    "extract_title",
    "extract_metadata",
]
