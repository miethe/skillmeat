"""Manifest extractors for artifact types.

This module provides specialized extractors for each artifact type's manifest
file. Each extractor reads the manifest file, parses its content, and returns
a standardized metadata dictionary.

Standardized Output Format:
    {
        "title": str | None,    # Artifact name/title (None if not found)
        "description": str | None,  # What the artifact does (None if not found)
        "tags": List[str],      # Tags/categories (empty list if not found)
        "raw_metadata": dict,   # Original parsed metadata for type-specific fields
    }

File Format Priority:
    - YAML artifacts (command, agent, hook): .yaml first, then .yml, then .md fallback
    - Skill artifacts: SKILL.md only (markdown with YAML frontmatter)
    - MCP artifacts: mcp.json first, then package.json fallback

Error Handling:
    - Always returns standardized dict structure (even on errors)
    - Uses None for missing title/description, empty list for tags
    - Logs warnings for missing files or parse failures
    - Uses yaml.safe_load for security
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Callable

import yaml

from skillmeat.core.parsers import parse_markdown_with_frontmatter, extract_title

logger = logging.getLogger(__name__)

# Deep search indexing constants (configurable via environment variables)
MAX_FILE_SIZE_BYTES = int(os.getenv("DEEP_INDEX_MAX_FILE_SIZE", 100_000))  # 100KB
MAX_TOTAL_TEXT_BYTES = int(os.getenv("DEEP_INDEX_MAX_TOTAL", 1_000_000))  # 1MB
INDEXABLE_PATTERNS = ["*.md", "*.yaml", "*.yml", "*.json", "*.txt", "*.py", "*.ts", "*.js"]


def _parse_yaml_file(file_path: Path) -> dict[str, Any] | None:
    """Parse a YAML file and return its contents.

    Args:
        file_path: Path to the YAML file.

    Returns:
        Parsed YAML as a dictionary, or None if parsing fails.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return data
        logger.warning(f"YAML content is not a dictionary: {file_path}")
        return None
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML file {file_path}: {e}")
        return None
    except OSError as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
        return None


def _parse_markdown_frontmatter(file_path: Path) -> dict[str, Any] | None:
    """Parse YAML frontmatter from a markdown file.

    Args:
        file_path: Path to the markdown file.

    Returns:
        Parsed frontmatter as a dictionary, or None if parsing fails.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        result = parse_markdown_with_frontmatter(content)
        return result.frontmatter
    except Exception as e:
        logger.warning(f"Failed to parse markdown frontmatter from {file_path}: {e}")
        return None


def _find_yaml_or_md_file(
    directory: Path,
    yaml_names: list[str],
    md_names: list[str],
) -> Path | None:
    """Find the first existing file from the given name priorities.

    Args:
        directory: Directory to search in.
        yaml_names: List of YAML file names to try (in priority order).
        md_names: List of markdown file names to try as fallback.

    Returns:
        Path to the first existing file, or None if none found.
    """
    # Try YAML files first
    for name in yaml_names:
        path = directory / name
        if path.exists():
            return path

    # Fall back to markdown files
    for name in md_names:
        path = directory / name
        if path.exists():
            return path

    return None


def _build_standardized_output(
    raw_metadata: dict[str, Any] | None,
    title_keys: list[str],
    description_keys: list[str],
    tags_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Build standardized output from raw metadata.

    Args:
        raw_metadata: Parsed metadata from file.
        title_keys: Keys to try for title extraction (in priority order).
        description_keys: Keys to try for description extraction.
        tags_keys: Keys to try for tags extraction (optional).

    Returns:
        Standardized metadata dictionary with title, description, tags, raw_metadata.
        Always returns all 4 keys, using None for missing values.
    """
    # Extract title (None if not found)
    title = None
    if raw_metadata:
        for key in title_keys:
            if key in raw_metadata and raw_metadata[key]:
                title = str(raw_metadata[key])
                break

    # Extract description (None if not found)
    description = None
    if raw_metadata:
        for key in description_keys:
            if key in raw_metadata and raw_metadata[key]:
                description = str(raw_metadata[key])
                break

    # Extract tags (empty list if not found)
    tags: list[str] = []
    if raw_metadata and tags_keys:
        for key in tags_keys:
            if key in raw_metadata and raw_metadata[key]:
                tag_value = raw_metadata[key]
                if isinstance(tag_value, list):
                    # Filter out empty/whitespace values
                    tags = [str(t) for t in tag_value if t and str(t).strip()]
                elif isinstance(tag_value, str):
                    tags = [t.strip() for t in tag_value.split(",") if t.strip()]
                break

    return {
        "title": title,
        "description": description,
        "tags": tags,
        "raw_metadata": raw_metadata or {},
    }


def extract_skill_manifest(file_path: Path) -> dict[str, Any]:
    """Extract metadata from a SKILL.md manifest file.

    Skills use markdown files with YAML frontmatter. The SKILL.md file
    is the canonical manifest file for skill artifacts.

    Title extraction priority:
        1. frontmatter['title'] or frontmatter['name']
        2. First H1 heading (# Title) in content
        3. None if neither found

    Args:
        file_path: Path to the SKILL.md file or skill directory.

    Returns:
        Standardized metadata dict with title, description, tags, raw_metadata.
        Always returns all 4 keys, even on error (with None/empty values).

    Example:
        >>> result = extract_skill_manifest(Path("my-skill/SKILL.md"))
        >>> result["title"]
        'My Skill'
        >>> result["description"]
        'Does useful things'
    """
    # If given a directory, look for SKILL.md
    if file_path.is_dir():
        file_path = file_path / "SKILL.md"

    # Return empty structure if file doesn't exist
    if not file_path.exists():
        logger.error(f"SKILL.md not found: {file_path}")
        return {
            "title": None,
            "description": None,
            "tags": [],
            "raw_metadata": {},
        }

    # Parse markdown with frontmatter
    try:
        content = file_path.read_text(encoding="utf-8")
        result = parse_markdown_with_frontmatter(content)
        frontmatter = result.frontmatter
        body_content = result.content
    except Exception as e:
        # Parse failed - try to extract H1 from raw content anyway
        logger.warning(f"Failed to parse SKILL.md {file_path}: {e}")
        try:
            raw_content = file_path.read_text(encoding="utf-8")
            h1_title = extract_title(raw_content, None)
            return {
                "title": h1_title,
                "description": None,
                "tags": [],
                "raw_metadata": {},
            }
        except Exception:
            return {
                "title": None,
                "description": None,
                "tags": [],
                "raw_metadata": {},
            }

    # Check for unclosed frontmatter (starts with --- but no valid frontmatter)
    if frontmatter is None and content.strip().startswith("---"):
        # File has opening delimiter but no closing or invalid YAML
        logger.warning(f"Unclosed or invalid frontmatter delimiter in {file_path}")

    # Validate frontmatter is a dict (YAML could parse to list or other types)
    if frontmatter is not None and not isinstance(frontmatter, dict):
        logger.warning(f"Frontmatter is not a dictionary in {file_path}, treating as no frontmatter")
        frontmatter = None

    # Build standardized output from frontmatter
    output = _build_standardized_output(
        raw_metadata=frontmatter,
        title_keys=["title", "name"],
        description_keys=["description", "purpose"],
        tags_keys=["tags", "categories"],
    )

    # If title not in frontmatter, try H1 heading fallback
    if not output["title"]:
        h1_title = extract_title(body_content, frontmatter)
        if h1_title:
            output["title"] = h1_title

    return output


def extract_command_manifest(file_path: Path) -> dict[str, Any]:
    """Extract metadata from a command manifest file.

    Commands can be defined in:
    - command.yaml / command.yml (preferred)
    - COMMAND.md (fallback, uses frontmatter)

    Expected YAML format:
        name: my-command
        description: Does something
        tools: [Read, Write, Bash]  # optional
        model: sonnet  # optional
        template: ...  # optional

    Args:
        file_path: Path to the command manifest file or command directory.

    Returns:
        Standardized metadata dict with title, description, tags, raw_metadata.
        Returns empty dict if parsing fails.

    Example:
        >>> result = extract_command_manifest(Path("commands/my-command"))
        >>> result["title"]
        'my-command'
        >>> result["raw_metadata"]["tools"]
        ['Read', 'Write', 'Bash']
    """
    # If given a directory, find the manifest file
    if file_path.is_dir():
        found = _find_yaml_or_md_file(
            file_path,
            yaml_names=["command.yaml", "command.yml"],
            md_names=["COMMAND.md", "command.md"],
        )
        if not found:
            logger.warning(f"No command manifest found in: {file_path}")
            return {}
        file_path = found

    if not file_path.exists():
        logger.warning(f"Command manifest not found: {file_path}")
        return {}

    # Parse based on file extension
    if file_path.suffix in (".yaml", ".yml"):
        raw_metadata = _parse_yaml_file(file_path)
    elif file_path.suffix == ".md":
        raw_metadata = _parse_markdown_frontmatter(file_path)
    else:
        logger.warning(f"Unsupported command manifest format: {file_path}")
        return {}

    if not raw_metadata:
        return {}

    return _build_standardized_output(
        raw_metadata=raw_metadata,
        title_keys=["name", "title"],
        description_keys=["description"],
        tags_keys=None,  # Commands don't typically have tags
    )


def extract_agent_manifest(file_path: Path) -> dict[str, Any]:
    """Extract metadata from an agent manifest file.

    Agents can be defined in:
    - agent.yaml / agent.yml (preferred)
    - AGENT.md / agent.md (fallback, uses frontmatter)

    Expected YAML format:
        name: my-agent
        description: Agent description
        model: sonnet  # optional
        tools: [Read, Write, Bash]  # optional

    Args:
        file_path: Path to the agent manifest file or agent directory.

    Returns:
        Standardized metadata dict with title, description, tags, raw_metadata.
        Returns empty dict if parsing fails.

    Example:
        >>> result = extract_agent_manifest(Path("agents/my-agent"))
        >>> result["title"]
        'my-agent'
        >>> result["raw_metadata"]["model"]
        'sonnet'
    """
    # If given a directory, find the manifest file
    if file_path.is_dir():
        found = _find_yaml_or_md_file(
            file_path,
            yaml_names=["agent.yaml", "agent.yml"],
            md_names=["AGENT.md", "agent.md"],
        )
        if not found:
            logger.warning(f"No agent manifest found in: {file_path}")
            return {}
        file_path = found

    if not file_path.exists():
        logger.warning(f"Agent manifest not found: {file_path}")
        return {}

    # Parse based on file extension
    if file_path.suffix in (".yaml", ".yml"):
        raw_metadata = _parse_yaml_file(file_path)
    elif file_path.suffix == ".md":
        raw_metadata = _parse_markdown_frontmatter(file_path)
    else:
        logger.warning(f"Unsupported agent manifest format: {file_path}")
        return {}

    if not raw_metadata:
        return {}

    return _build_standardized_output(
        raw_metadata=raw_metadata,
        title_keys=["name", "title"],
        description_keys=["description"],
        tags_keys=None,  # Agents don't typically have tags
    )


def extract_hook_manifest(file_path: Path) -> dict[str, Any]:
    """Extract metadata from a hook manifest file.

    Hooks can be defined in:
    - hook.yaml / hook.yml (YAML preferred)
    - HOOK.md / hook.md (fallback, uses frontmatter)

    Expected YAML format:
        name: pre-commit
        description: Runs before commits
        event: pre_commit  # or events: [pre_commit, post_commit]
        script: ./run-tests.sh  # optional
        command: pytest  # optional

    Args:
        file_path: Path to the hook manifest file or hook directory.

    Returns:
        Standardized metadata dict with title, description, tags, raw_metadata.
        Returns empty dict if parsing fails.

    Example:
        >>> result = extract_hook_manifest(Path("hooks/pre-commit"))
        >>> result["title"]
        'pre-commit'
        >>> result["raw_metadata"]["event"]
        'pre_commit'
    """
    # If given a directory, find the manifest file
    if file_path.is_dir():
        # Hooks primarily use YAML, but can fall back to markdown
        found = _find_yaml_or_md_file(
            file_path,
            yaml_names=["hook.yaml", "hook.yml"],
            md_names=["HOOK.md", "hook.md"],
        )
        if not found:
            logger.warning(f"No hook manifest found in: {file_path}")
            return {}
        file_path = found

    if not file_path.exists():
        logger.warning(f"Hook manifest not found: {file_path}")
        return {}

    # Parse based on file extension
    if file_path.suffix in (".yaml", ".yml"):
        raw_metadata = _parse_yaml_file(file_path)
    elif file_path.suffix == ".md":
        raw_metadata = _parse_markdown_frontmatter(file_path)
    else:
        logger.warning(f"Unsupported hook manifest format: {file_path}")
        return {}

    if not raw_metadata:
        return {}

    return _build_standardized_output(
        raw_metadata=raw_metadata,
        title_keys=["name", "title"],
        description_keys=["description"],
        tags_keys=None,  # Hooks don't typically have tags
    )


def extract_mcp_manifest(file_path: Path) -> dict[str, Any]:
    """Extract metadata from an MCP manifest file.

    MCP (Model Context Protocol) servers can be defined in:
    - mcp.json (preferred)
    - package.json (fallback, uses npm package format)

    Expected mcp.json format:
        {
            "name": "my-mcp-server",
            "description": "Provides context tools",
            "tools": ["tool1", "tool2"]
        }

    Args:
        file_path: Path to the MCP manifest file or MCP directory.

    Returns:
        Standardized metadata dict with title, description, tags, raw_metadata.
        Returns empty dict if parsing fails.

    Example:
        >>> result = extract_mcp_manifest(Path("mcp/my-server"))
        >>> result["title"]
        'my-mcp-server'
    """
    import json

    # If given a directory, find the manifest file
    if file_path.is_dir():
        for name in ["mcp.json", "package.json"]:
            path = file_path / name
            if path.exists():
                file_path = path
                break
        else:
            logger.warning(f"No MCP manifest found in: {file_path}")
            return {}

    if not file_path.exists():
        logger.warning(f"MCP manifest not found: {file_path}")
        return {}

    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            logger.warning(f"MCP manifest is not a dictionary: {file_path}")
            return {}
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON file {file_path}: {e}")
        return {}
    except OSError as e:
        logger.warning(f"Failed to read file {file_path}: {e}")
        return {}

    return _build_standardized_output(
        raw_metadata=data,
        title_keys=["name"],
        description_keys=["description"],
        tags_keys=["keywords", "tags"],  # npm uses "keywords"
    )


# Type to extractor mapping for convenience
MANIFEST_EXTRACTORS: dict[str, Callable[[Path], dict[str, Any]]] = {
    "skill": extract_skill_manifest,
    "command": extract_command_manifest,
    "agent": extract_agent_manifest,
    "hook": extract_hook_manifest,
    "mcp": extract_mcp_manifest,
}


def extract_manifest(artifact_type: str, file_path: Path) -> dict[str, Any]:
    """Extract manifest metadata based on artifact type.

    Convenience function that dispatches to the appropriate type-specific
    extractor based on the artifact type.

    Args:
        artifact_type: One of "skill", "command", "agent", "hook", "mcp".
        file_path: Path to the manifest file or artifact directory.

    Returns:
        Standardized metadata dict with title, description, tags, raw_metadata.
        Returns empty dict if type is unknown or parsing fails.

    Example:
        >>> result = extract_manifest("skill", Path("my-skill"))
        >>> result["title"]
        'My Skill'
    """
    extractor = MANIFEST_EXTRACTORS.get(artifact_type.lower())
    if not extractor:
        logger.warning(f"Unknown artifact type: {artifact_type}")
        return {}
    return extractor(file_path)


def _is_binary_file(file_path: Path) -> bool:
    """Check if file appears to be binary by looking for null bytes.

    Reads the first 1KB of a file and checks for null bytes, which
    typically indicate binary content.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if file appears to be binary or cannot be read, False otherwise.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except OSError:
        return True  # Treat unreadable files as binary


def extract_deep_search_text(artifact_dir: Path) -> tuple[str, list[str]]:
    """Extract searchable text from all files in artifact directory.

    Recursively scans the artifact directory for indexable files and extracts
    their text content for full-text search indexing.

    Indexable file patterns: ['*.md', '*.yaml', '*.yml', '*.json', '*.txt', '*.py', '*.ts', '*.js']

    Args:
        artifact_dir: Path to the artifact directory to index.

    Returns:
        Tuple of (concatenated_text, list_of_indexed_files):
        - concatenated_text: All file contents joined with spaces, normalized
        - list_of_indexed_files: Relative paths of files that were indexed

    Notes:
        - Skips files >100KB (MAX_FILE_SIZE_BYTES)
        - Skips binary files (detected by null bytes in first 1KB)
        - Normalizes whitespace (collapse multiple spaces/newlines)
        - Total text capped at 1MB (MAX_TOTAL_TEXT_BYTES)

    Example:
        >>> text, files = extract_deep_search_text(Path("my-skill"))
        >>> len(files)
        3
        >>> "SKILL.md" in files[0]
        True
    """
    if not artifact_dir.is_dir():
        logger.warning(f"Artifact directory does not exist: {artifact_dir}")
        return ("", [])

    indexed_files: list[str] = []
    text_parts: list[str] = []
    total_bytes = 0

    # Collect all matching files from all patterns
    all_files: set[Path] = set()
    for pattern in INDEXABLE_PATTERNS:
        all_files.update(artifact_dir.rglob(pattern))

    # Sort for deterministic ordering
    sorted_files = sorted(all_files)

    for file_path in sorted_files:
        # Check if we've reached the total size limit
        if total_bytes >= MAX_TOTAL_TEXT_BYTES:
            logger.debug(
                f"Reached total text limit ({MAX_TOTAL_TEXT_BYTES} bytes), "
                f"stopping indexing at {len(indexed_files)} files"
            )
            break

        # Skip files that are too large
        try:
            file_size = file_path.stat().st_size
        except OSError as e:
            logger.debug(f"Cannot stat file {file_path}: {e}")
            continue

        if file_size > MAX_FILE_SIZE_BYTES:
            logger.debug(
                f"Skipping large file {file_path} ({file_size} bytes > {MAX_FILE_SIZE_BYTES})"
            )
            continue

        # Skip binary files
        if _is_binary_file(file_path):
            logger.debug(f"Skipping binary file: {file_path}")
            continue

        # Read and process the file
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.debug(f"Cannot read file {file_path}: {e}")
            continue

        # Normalize whitespace: collapse multiple spaces/newlines to single space
        normalized = re.sub(r"\s+", " ", content).strip()

        if normalized:
            # Check if adding this content would exceed the limit
            content_bytes = len(normalized.encode("utf-8"))
            if total_bytes + content_bytes > MAX_TOTAL_TEXT_BYTES:
                # Truncate to fit remaining space
                remaining_bytes = MAX_TOTAL_TEXT_BYTES - total_bytes
                # Approximate character count (may not be exact for multi-byte chars)
                truncated = normalized[:remaining_bytes]
                text_parts.append(truncated)
                total_bytes += len(truncated.encode("utf-8"))
                relative_path = str(file_path.relative_to(artifact_dir))
                indexed_files.append(relative_path)
                logger.debug(f"Indexed (truncated): {relative_path}")
                break
            else:
                text_parts.append(normalized)
                total_bytes += content_bytes
                relative_path = str(file_path.relative_to(artifact_dir))
                indexed_files.append(relative_path)
                logger.debug(f"Indexed: {relative_path} ({content_bytes} bytes)")

    # Join all text parts with spaces
    full_text = " ".join(text_parts)

    # Final truncation check and add marker if truncated
    if total_bytes >= MAX_TOTAL_TEXT_BYTES:
        # Ensure we don't exceed and add truncation marker
        full_text_bytes = full_text.encode("utf-8")
        if len(full_text_bytes) > MAX_TOTAL_TEXT_BYTES:
            # Truncate and add marker
            truncation_marker = "...[truncated]"
            max_content_bytes = MAX_TOTAL_TEXT_BYTES - len(truncation_marker.encode("utf-8"))
            # Simple truncation (may break multi-byte chars, but errors='replace' handles it)
            truncated_bytes = full_text_bytes[:max_content_bytes]
            full_text = truncated_bytes.decode("utf-8", errors="replace") + truncation_marker

    return (full_text, indexed_files)
