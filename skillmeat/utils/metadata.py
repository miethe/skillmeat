"""Metadata extraction utilities for SkillMeat."""

import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def extract_yaml_frontmatter(file_path: Path) -> Optional[Dict[str, Any]]:
    """Extract YAML frontmatter from markdown file.

    Looks for YAML frontmatter delimited by --- at the start of the file:
    ---
    title: My Artifact
    description: Does something
    ---

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary of frontmatter data, or None if no frontmatter found

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match YAML frontmatter: --- ... ---
    # Must be at start of file
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return None

    yaml_content = match.group(1)

    try:
        data = yaml.safe_load(yaml_content)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML frontmatter in {file_path}: {e}")
