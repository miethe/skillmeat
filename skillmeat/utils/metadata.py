"""Metadata extraction utilities for SkillMeat."""

import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from skillmeat.core.artifact import ArtifactMetadata, ArtifactType


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


def extract_description_from_content(content: str) -> Optional[str]:
    """Extract description from markdown content.

    Extracts the first non-header paragraph from content.

    Args:
        content: Markdown content (after frontmatter)

    Returns:
        First paragraph as description, or None if not found
    """
    if not content.strip():
        return None

    for line in content.split("\n"):
        line = line.strip()
        # Skip markdown headers and empty lines
        if line and not line.startswith("#"):
            # Limit to 200 chars
            return line[:200]

    return None


def find_metadata_file(path: Path, artifact_type: ArtifactType) -> Optional[Path]:
    """Find the metadata file for an artifact.

    Args:
        path: Path to artifact (file or directory)
        artifact_type: Type of artifact

    Returns:
        Path to metadata file, or None if not found
    """
    if artifact_type == ArtifactType.SKILL:
        # Skills must be directories with SKILL.md
        if path.is_dir():
            skill_md = path / "SKILL.md"
            if skill_md.exists():
                return skill_md
        return None

    elif artifact_type == ArtifactType.COMMAND:
        # Commands can be a .md file or directory with command.md
        if path.is_file() and path.suffix == ".md":
            return path
        elif path.is_dir():
            command_md = path / "command.md"
            if command_md.exists():
                return command_md
            # Fallback to any .md file
            md_files = list(path.glob("*.md"))
            if md_files:
                return md_files[0]
        return None

    elif artifact_type == ArtifactType.AGENT:
        # Agents can be a .md file or directory with AGENT.md/agent.md
        if path.is_file() and path.suffix == ".md":
            return path
        elif path.is_dir():
            agent_md_upper = path / "AGENT.md"
            agent_md_lower = path / "agent.md"
            if agent_md_upper.exists():
                return agent_md_upper
            elif agent_md_lower.exists():
                return agent_md_lower
            # Fallback to any .md file
            md_files = list(path.glob("*.md"))
            if md_files:
                return md_files[0]
        return None

    return None


def extract_artifact_metadata(
    path: Path, artifact_type: ArtifactType
) -> ArtifactMetadata:
    """Extract metadata from artifact files.

    For SKILL: Read SKILL.md YAML frontmatter
    For COMMAND: Read command.md YAML frontmatter
    For AGENT: Read agent.md YAML frontmatter

    Args:
        path: Path to artifact (file or directory)
        artifact_type: Type of artifact

    Returns:
        ArtifactMetadata with extracted metadata

    Raises:
        FileNotFoundError: If metadata file not found
    """
    metadata_file = find_metadata_file(path, artifact_type)
    if metadata_file is None:
        # Return empty metadata if no metadata file found
        return ArtifactMetadata()

    # Extract YAML frontmatter
    try:
        yaml_data = extract_yaml_frontmatter(metadata_file)
    except Exception:
        yaml_data = None

    # Read content for description extraction
    try:
        content = metadata_file.read_text(encoding="utf-8")
        # Remove YAML frontmatter from content
        if content.startswith("---"):
            # Find closing ---
            lines = content.split("\n")
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    content = "\n".join(lines[i + 1 :])
                    break
    except Exception:
        content = ""

    # Build metadata
    metadata = ArtifactMetadata()

    if yaml_data:
        metadata.title = yaml_data.get("title")
        metadata.description = yaml_data.get("description")
        metadata.author = yaml_data.get("author")
        metadata.license = yaml_data.get("license")
        metadata.version = yaml_data.get("version")
        metadata.tags = yaml_data.get("tags", [])
        metadata.dependencies = yaml_data.get("dependencies", [])

        # Store any extra fields
        known_fields = {
            "title",
            "description",
            "author",
            "license",
            "version",
            "tags",
            "dependencies",
        }
        metadata.extra = {k: v for k, v in yaml_data.items() if k not in known_fields}

    # If no description from YAML, try to extract from content
    if not metadata.description:
        metadata.description = extract_description_from_content(content)

    return metadata
