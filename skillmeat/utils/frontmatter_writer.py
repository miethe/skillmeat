"""Utilities for updating YAML frontmatter in markdown files.

Provides safe, atomic updates to specific fields in YAML frontmatter
without destroying the rest of the file content. Used by TagWriteService
to persist tag renames/deletes to SKILL.md/COMMAND.md files.
"""

import logging
import re
from pathlib import Path
from typing import Any, List

import yaml

from skillmeat.utils.filesystem import atomic_write

logger = logging.getLogger(__name__)

# Frontmatter regex — matches --- delimited YAML block at start of file
_FRONTMATTER_RE = re.compile(
    r"^(\ufeff?)---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)",
    re.DOTALL,
)


def update_frontmatter_field(
    file_path: Path,
    field_name: str,
    new_value: Any,
) -> bool:
    """Update a single field in a markdown file's YAML frontmatter.

    Preserves all other frontmatter fields and the markdown body.
    Uses atomic_write for safety.

    Args:
        file_path: Path to the markdown file
        field_name: Name of the frontmatter field to update
        new_value: New value for the field

    Returns:
        True if file was updated, False if no frontmatter found or field unchanged
    """
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return False

    content = file_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        logger.debug(f"No frontmatter found in {file_path}")
        return False

    bom = match.group(1)
    yaml_text = match.group(2)

    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse frontmatter in {file_path}: {e}")
        return False

    # Check if update is needed
    if frontmatter.get(field_name) == new_value:
        return False

    frontmatter[field_name] = new_value

    # Re-serialize frontmatter
    new_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip("\n")

    # Reconstruct the file
    rest_of_file = content[match.end() :]
    new_content = f"{bom}---\n{new_yaml}\n---\n{rest_of_file}"

    atomic_write(new_content, file_path)
    logger.info(f"Updated {field_name} in {file_path}")
    return True


def rename_tag_in_frontmatter(
    file_path: Path,
    old_name: str,
    new_name: str,
) -> bool:
    """Replace a tag name in a file's frontmatter tags list.

    Args:
        file_path: Path to the markdown file
        old_name: Tag name to replace
        new_name: New tag name

    Returns:
        True if a tag was renamed, False if old_name not found in tags
    """
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return False

    content = file_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return False

    bom = match.group(1)
    yaml_text = match.group(2)

    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return False

    tags = frontmatter.get("tags", [])
    if not isinstance(tags, list) or old_name not in tags:
        return False

    # Replace old tag with new, preserving order, avoiding duplicates
    new_tags = []
    for tag in tags:
        if tag == old_name:
            if new_name not in new_tags:
                new_tags.append(new_name)
        else:
            new_tags.append(tag)

    frontmatter["tags"] = new_tags

    new_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip("\n")

    rest_of_file = content[match.end() :]
    new_content = f"{bom}---\n{new_yaml}\n---\n{rest_of_file}"

    atomic_write(new_content, file_path)
    logger.info(f"Renamed tag '{old_name}' -> '{new_name}' in {file_path}")
    return True


def remove_tag_from_frontmatter(
    file_path: Path,
    tag_name: str,
) -> bool:
    """Remove a tag from a file's frontmatter tags list.

    Args:
        file_path: Path to the markdown file
        tag_name: Tag name to remove

    Returns:
        True if tag was removed, False if tag not found in tags
    """
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return False

    content = file_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return False

    bom = match.group(1)
    yaml_text = match.group(2)

    try:
        frontmatter = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return False

    tags = frontmatter.get("tags", [])
    if not isinstance(tags, list) or tag_name not in tags:
        return False

    frontmatter["tags"] = [t for t in tags if t != tag_name]

    new_yaml = yaml.dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip("\n")

    rest_of_file = content[match.end() :]
    new_content = f"{bom}---\n{new_yaml}\n---\n{rest_of_file}"

    atomic_write(new_content, file_path)
    logger.info(f"Removed tag '{tag_name}' from {file_path}")
    return True
