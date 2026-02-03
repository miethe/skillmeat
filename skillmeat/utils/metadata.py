"""Metadata extraction utilities for SkillMeat.

This module provides utilities for extracting and parsing metadata from
artifact content files, including YAML frontmatter extraction and tool
name normalization.
"""

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import yaml

# Note: We intentionally do NOT import from skillmeat.core.* at module level
# to avoid circular imports. This module is imported by skillmeat.core.search
# which is imported by skillmeat.core.__init__.py

if TYPE_CHECKING:
    from skillmeat.core.artifact import Artifact, ArtifactMetadata, LinkedArtifactReference
    from skillmeat.core.artifact_detection import ArtifactType
    from skillmeat.core.github_client import GitHubClient

logger = logging.getLogger(__name__)

# =============================================================================
# Tool Name Normalization
# =============================================================================

# Valid Tool enum values - these match the Tool enum in skillmeat.core.enums
# We duplicate them here to avoid circular import dependency
_VALID_TOOL_VALUES = {
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    "NotebookEdit",
    "Bash",
    "KillShell",
    "AskUserQuestion",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "Task",
    "TaskOutput",
    "Skill",
    "EnterPlanMode",
    "ExitPlanMode",
}

# Mapping of common tool name variations to canonical Tool enum values
_TOOL_NAME_ALIASES: Dict[str, str] = {
    # Lowercase mappings
    "read": "Read",
    "write": "Write",
    "edit": "Edit",
    "multiedit": "MultiEdit",
    "multi_edit": "MultiEdit",
    "multi-edit": "MultiEdit",
    "glob": "Glob",
    "grep": "Grep",
    "notebookedit": "NotebookEdit",
    "notebook_edit": "NotebookEdit",
    "notebook-edit": "NotebookEdit",
    "bash": "Bash",
    "killshell": "KillShell",
    "kill_shell": "KillShell",
    "kill-shell": "KillShell",
    "askuserquestion": "AskUserQuestion",
    "ask_user_question": "AskUserQuestion",
    "ask-user-question": "AskUserQuestion",
    "todowrite": "TodoWrite",
    "todo_write": "TodoWrite",
    "todo-write": "TodoWrite",
    "webfetch": "WebFetch",
    "web_fetch": "WebFetch",
    "web-fetch": "WebFetch",
    "websearch": "WebSearch",
    "web_search": "WebSearch",
    "web-search": "WebSearch",
    "task": "Task",
    "taskoutput": "TaskOutput",
    "task_output": "TaskOutput",
    "task-output": "TaskOutput",
    "skill": "Skill",
    "enterplanmode": "EnterPlanMode",
    "enter_plan_mode": "EnterPlanMode",
    "enter-plan-mode": "EnterPlanMode",
    "exitplanmode": "ExitPlanMode",
    "exit_plan_mode": "ExitPlanMode",
    "exit-plan-mode": "ExitPlanMode",
}


def _normalize_tool_name(tool_name: str) -> Optional[str]:
    """Normalize a single tool name to match Tool enum values.

    Args:
        tool_name: Tool name in any case or format.

    Returns:
        Normalized tool name matching Tool enum value, or None if invalid.

    Examples:
        >>> _normalize_tool_name("bash")
        'Bash'
        >>> _normalize_tool_name("WebFetch")
        'WebFetch'
        >>> _normalize_tool_name("web-fetch")
        'WebFetch'
        >>> _normalize_tool_name("invalid_tool")
        None
    """
    if not tool_name or not isinstance(tool_name, str):
        return None

    stripped = tool_name.strip()
    if not stripped:
        return None

    # Check if already a valid Tool enum value (case-sensitive match)
    if stripped in _VALID_TOOL_VALUES:
        return stripped

    # Check alias mapping (case-insensitive)
    normalized = _TOOL_NAME_ALIASES.get(stripped.lower())
    if normalized:
        return normalized

    # Try direct case-insensitive match against Tool enum values
    lower_stripped = stripped.lower()
    for valid_value in _VALID_TOOL_VALUES:
        if valid_value.lower() == lower_stripped:
            return valid_value

    logger.debug(f"Unknown tool name: {tool_name}")
    return None


def _normalize_tools(tools_value: Union[str, List[str], None]) -> List[str]:
    """Normalize tools field to a list of valid Tool enum value strings.

    Handles multiple input formats:
    - Comma-separated string: "Bash,Read,Write"
    - YAML array: ["Bash", "Read", "Write"]
    - Single value: "Bash"
    - None or empty: returns []

    Invalid tool names are logged as warnings and skipped.

    Args:
        tools_value: Tools value from frontmatter (string, list, or None).

    Returns:
        List of normalized tool names matching Tool enum values.

    Examples:
        >>> _normalize_tools("Bash,Read,Write")
        ['Bash', 'Read', 'Write']
        >>> _normalize_tools(["bash", "web-fetch"])
        ['Bash', 'WebFetch']
        >>> _normalize_tools("Bash")
        ['Bash']
        >>> _normalize_tools(None)
        []
    """
    if tools_value is None:
        return []

    # Convert to list
    if isinstance(tools_value, str):
        # Handle comma-separated string
        if "," in tools_value:
            raw_tools = [t.strip() for t in tools_value.split(",")]
        else:
            raw_tools = [tools_value.strip()]
    elif isinstance(tools_value, list):
        raw_tools = [str(t).strip() for t in tools_value if t is not None]
    else:
        logger.warning(f"Unexpected tools value type: {type(tools_value)}")
        return []

    # Normalize each tool name
    normalized = []
    for raw_tool in raw_tools:
        if not raw_tool:
            continue
        norm = _normalize_tool_name(raw_tool)
        if norm:
            normalized.append(norm)
        else:
            logger.warning(f"Skipping unknown tool: {raw_tool}")

    return normalized


# =============================================================================
# Frontmatter Extraction
# =============================================================================

# Known frontmatter fields for artifact metadata
_KNOWN_FIELDS = {
    "name",
    "description",
    "tools",
    "allowed-tools",
    "allowedTools",
    "disallowedTools",
    "disallowed-tools",
    "model",
    "permissionMode",
    "permission-mode",
    "skills",
    "hooks",
    "user-invocable",
    "userInvocable",
    # Standard metadata fields
    "title",
    "author",
    "license",
    "version",
    "tags",
    "dependencies",
}

# Regex pattern for frontmatter extraction
# Handles BOM characters and various whitespace patterns
_FRONTMATTER_PATTERN = re.compile(
    r"^\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)",
    re.DOTALL,
)


def populate_metadata_from_frontmatter(
    metadata: "ArtifactMetadata",
    frontmatter: Dict[str, Any],
) -> "ArtifactMetadata":
    """Populate artifact metadata from parsed frontmatter.

    Updates an ArtifactMetadata instance with values extracted from frontmatter.
    Validates tool names against the Tool enum and tracks both valid and invalid
    tools for debugging purposes.

    Args:
        metadata: ArtifactMetadata instance to populate.
        frontmatter: Dictionary from extract_frontmatter() containing parsed
            frontmatter fields (name, description, tools, etc.).

    Returns:
        The same ArtifactMetadata instance with updated fields. Returns
        unchanged if frontmatter is None or empty.

    Note:
        - Valid tools are converted to Tool enum objects in metadata.tools
        - Invalid tool names are tracked in metadata.extra['unknown_tools']
        - Original tool names are cached in metadata.extra['frontmatter_tools']
        - Full frontmatter is cached in metadata.extra['frontmatter']

    Examples:
        >>> from skillmeat.core.artifact import ArtifactMetadata
        >>> metadata = ArtifactMetadata()
        >>> frontmatter = {
        ...     'description': 'A useful skill',
        ...     'tools': ['Bash', 'Read', 'InvalidTool']
        ... }
        >>> populate_metadata_from_frontmatter(metadata, frontmatter)
        >>> metadata.description
        'A useful skill'
        >>> [t.value for t in metadata.tools]
        ['Bash', 'Read']
        >>> metadata.extra['unknown_tools']
        ['InvalidTool']
    """
    # Import at function level to avoid circular imports
    from skillmeat.core.artifact import ArtifactMetadata
    from skillmeat.core.enums import Tool

    if not frontmatter:
        return metadata

    # Ensure extra dict exists
    if metadata.extra is None:
        metadata.extra = {}

    # Cache full frontmatter for reference
    metadata.extra["frontmatter"] = frontmatter

    # Set description if present and not already set
    if "description" in frontmatter and frontmatter["description"]:
        metadata.description = str(frontmatter["description"])

    # Process tools field
    tools_list = frontmatter.get("tools", [])
    if tools_list:
        # Cache original tool names from frontmatter
        if isinstance(tools_list, list):
            metadata.extra["frontmatter_tools"] = list(tools_list)
        else:
            metadata.extra["frontmatter_tools"] = [tools_list]

        # Validate and convert to Tool enum objects
        valid_tools: List["Tool"] = []
        unknown_tools: List[str] = []

        for tool_name in tools_list:
            if not tool_name:
                continue

            # Normalize the tool name
            normalized = _normalize_tool_name(str(tool_name))

            if normalized:
                try:
                    tool_enum = Tool(normalized)
                    valid_tools.append(tool_enum)
                except ValueError:
                    # Should not happen since _normalize_tool_name validates
                    unknown_tools.append(str(tool_name))
            else:
                unknown_tools.append(str(tool_name))

        # Set validated tools on metadata
        metadata.tools = valid_tools

        # Track unknown tools for debugging
        if unknown_tools:
            metadata.extra["unknown_tools"] = unknown_tools

    # Copy other standard metadata fields if present
    if "title" in frontmatter and frontmatter["title"]:
        metadata.title = str(frontmatter["title"])

    if "author" in frontmatter and frontmatter["author"]:
        metadata.author = str(frontmatter["author"])

    if "license" in frontmatter and frontmatter["license"]:
        metadata.license = str(frontmatter["license"])

    if "version" in frontmatter and frontmatter["version"]:
        metadata.version = str(frontmatter["version"])

    if "tags" in frontmatter and frontmatter["tags"]:
        tags = frontmatter["tags"]
        if isinstance(tags, list):
            metadata.tags = [str(t) for t in tags if t]
        elif isinstance(tags, str):
            metadata.tags = [t.strip() for t in tags.split(",") if t.strip()]

    if "dependencies" in frontmatter and frontmatter["dependencies"]:
        deps = frontmatter["dependencies"]
        if isinstance(deps, list):
            metadata.dependencies = [str(d) for d in deps if d]
        elif isinstance(deps, str):
            metadata.dependencies = [d.strip() for d in deps.split(",") if d.strip()]

    return metadata


def extract_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from artifact content string.

    Parses YAML frontmatter delimited by `---` at the start of the file.
    Handles various edge cases including:
    - BOM (Byte Order Mark) characters at file start
    - Different line endings (CRLF, LF)
    - Various indentation styles
    - Unicode characters in values

    Malformed YAML is handled gracefully with warnings logged.

    Args:
        content: Full content of artifact file as string.

    Returns:
        Dictionary containing extracted frontmatter fields:
        - name: Artifact name (if present)
        - description: Artifact description (if present)
        - tools: Normalized list of tools (from tools or allowed-tools)
        - disallowedTools: List of disallowed tools (if present)
        - model: Model specification (if present)
        - permissionMode: Permission mode (if present)
        - skills: List of skill references (if present)
        - hooks: Hook configuration (if present)
        - userInvocable: Boolean for user invocability (if present)
        - extra: Dict of any additional frontmatter fields

        Returns empty dict if no frontmatter found or content is empty.

    Examples:
        >>> content = '''---
        ... name: my-skill
        ... description: A useful skill
        ... tools: Bash,Read,Write
        ... ---
        ... # Content here
        ... '''
        >>> result = extract_frontmatter(content)
        >>> result['name']
        'my-skill'
        >>> result['tools']
        ['Bash', 'Read', 'Write']
    """
    if not content:
        return {}

    # Handle string that might have leading whitespace before BOM
    stripped = content.lstrip()
    if not stripped:
        return {}

    # Try to match frontmatter pattern
    match = _FRONTMATTER_PATTERN.match(content)
    if not match:
        # Also try with stripped content (handles whitespace before ---)
        match = _FRONTMATTER_PATTERN.match(stripped)

    if not match:
        logger.debug("No YAML frontmatter found in content")
        return {}

    yaml_content = match.group(1)

    # Parse YAML
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML frontmatter: {e}")
        # Try to extract partial data from malformed YAML
        return _extract_partial_frontmatter(yaml_content)

    if not isinstance(data, dict):
        logger.warning(f"YAML frontmatter is not a dictionary: {type(data)}")
        return {}

    # Build result with normalized fields
    result: Dict[str, Any] = {}

    # Standard fields
    if "name" in data:
        result["name"] = str(data["name"])
    if "description" in data:
        result["description"] = str(data["description"])

    # Tools - check multiple possible field names
    # Preserve original tool names for populate_metadata_from_frontmatter to validate
    # and track unknown tools
    tools_value = (
        data.get("tools") or data.get("allowed-tools") or data.get("allowedTools")
    )
    if tools_value is not None:
        # Normalize to list but preserve original names for validation
        if isinstance(tools_value, str):
            if "," in tools_value:
                result["tools"] = [
                    t.strip() for t in tools_value.split(",") if t.strip()
                ]
            else:
                result["tools"] = [tools_value.strip()] if tools_value.strip() else []
        elif isinstance(tools_value, list):
            result["tools"] = [str(t).strip() for t in tools_value if t is not None]
        else:
            result["tools"] = []

    # Disallowed tools
    disallowed = data.get("disallowedTools") or data.get("disallowed-tools")
    if disallowed is not None:
        result["disallowedTools"] = _normalize_tools(disallowed)

    # Model
    if "model" in data:
        result["model"] = str(data["model"])

    # Permission mode
    perm_mode = data.get("permissionMode") or data.get("permission-mode")
    if perm_mode is not None:
        result["permissionMode"] = str(perm_mode)

    # Skills
    if "skills" in data:
        skills = data["skills"]
        if isinstance(skills, list):
            result["skills"] = [str(s) for s in skills if s]
        elif isinstance(skills, str):
            result["skills"] = [s.strip() for s in skills.split(",") if s.strip()]

    # Hooks
    if "hooks" in data:
        result["hooks"] = data["hooks"]

    # User invocable
    user_inv = data.get("user-invocable") or data.get("userInvocable")
    if user_inv is not None:
        if isinstance(user_inv, bool):
            result["userInvocable"] = user_inv
        elif isinstance(user_inv, str):
            result["userInvocable"] = user_inv.lower() in ("true", "yes", "1")

    # Standard metadata fields
    for field in ("title", "author", "license", "version"):
        if field in data:
            result[field] = str(data[field])

    # Tags
    if "tags" in data:
        tags = data["tags"]
        if isinstance(tags, list):
            result["tags"] = [str(t) for t in tags if t]
        elif isinstance(tags, str):
            result["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    # Dependencies
    if "dependencies" in data:
        deps = data["dependencies"]
        if isinstance(deps, list):
            result["dependencies"] = [str(d) for d in deps if d]
        elif isinstance(deps, str):
            result["dependencies"] = [d.strip() for d in deps.split(",") if d.strip()]

    # Collect any extra fields
    extra = {}
    for key, value in data.items():
        # Normalize key for comparison
        key_lower = key.lower().replace("-", "").replace("_", "")
        known_lower = {
            k.lower().replace("-", "").replace("_", "") for k in _KNOWN_FIELDS
        }
        if key_lower not in known_lower:
            extra[key] = value

    if extra:
        result["extra"] = extra

    return result


def _extract_partial_frontmatter(yaml_content: str) -> Dict[str, Any]:
    """Attempt to extract partial data from malformed YAML.

    Uses simple line-by-line parsing to extract key-value pairs
    when full YAML parsing fails.

    Args:
        yaml_content: The YAML content that failed to parse.

    Returns:
        Dictionary with any successfully extracted fields.
    """
    result: Dict[str, Any] = {}
    extra: Dict[str, Any] = {}

    for line in yaml_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Try to extract simple key: value pairs
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if not key:
                continue

            # Remove quotes if present
            if (
                value
                and value[0] in ('"', "'")
                and len(value) > 1
                and value[-1] == value[0]
            ):
                value = value[1:-1]

            # Map known fields
            key_lower = key.lower()
            if key_lower == "name":
                result["name"] = value
            elif key_lower == "description":
                result["description"] = value
            elif key_lower in ("tools", "allowed-tools", "allowedtools"):
                result["tools"] = _normalize_tools(value)
            elif key_lower == "model":
                result["model"] = value
            elif value:
                extra[key] = value

    if extra:
        result["extra"] = extra

    return result


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


def find_metadata_file(path: Path, artifact_type: "ArtifactType") -> Optional[Path]:
    """Find the metadata file for an artifact.

    Args:
        path: Path to artifact (file or directory)
        artifact_type: Type of artifact

    Returns:
        Path to metadata file, or None if not found
    """
    # Import at runtime to avoid circular imports
    from skillmeat.core.artifact_detection import ArtifactType

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
    path: Path, artifact_type: "ArtifactType"
) -> "ArtifactMetadata":
    """Extract metadata from artifact files.

    For SKILL: Read SKILL.md YAML frontmatter
    For COMMAND: Read command.md YAML frontmatter
    For AGENT: Read agent.md YAML frontmatter

    This function uses enhanced frontmatter extraction that:
    - Normalizes tool names to match Tool enum values
    - Caches full frontmatter in metadata.extra['frontmatter']
    - Tracks unknown tools in metadata.extra['unknown_tools']
    - Auto-populates description from frontmatter

    Args:
        path: Path to artifact (file or directory)
        artifact_type: Type of artifact

    Returns:
        ArtifactMetadata with extracted metadata

    Raises:
        FileNotFoundError: If metadata file not found
    """
    # Import at runtime to avoid circular imports
    from skillmeat.core.artifact import ArtifactMetadata

    metadata_file = find_metadata_file(path, artifact_type)
    if metadata_file is None:
        # Return empty metadata if no metadata file found
        return ArtifactMetadata()

    # Read file content for frontmatter extraction
    try:
        content = metadata_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read metadata file {metadata_file}: {e}")
        return ArtifactMetadata()

    # Build base metadata
    metadata = ArtifactMetadata()

    # Use enhanced frontmatter extraction for tools and other fields
    try:
        frontmatter = extract_frontmatter(content)
        if frontmatter:
            # Populate metadata from frontmatter (handles tools normalization,
            # description, and caches full frontmatter in extra)
            metadata = populate_metadata_from_frontmatter(metadata, frontmatter)
    except Exception as e:
        logger.warning(f"Frontmatter extraction failed for {metadata_file}: {e}")
        # Continue with basic metadata extraction below

    # Fall back to basic YAML extraction if enhanced extraction didn't populate
    # or for fields not handled by populate_metadata_from_frontmatter
    try:
        yaml_data = extract_yaml_frontmatter(metadata_file)
    except Exception:
        yaml_data = None

    if yaml_data:
        # Only set fields if not already populated from frontmatter
        if not metadata.title:
            metadata.title = yaml_data.get("title")
        if not metadata.description:
            metadata.description = yaml_data.get("description")
        if not metadata.author:
            metadata.author = yaml_data.get("author")
        if not metadata.license:
            metadata.license = yaml_data.get("license")
        if not metadata.version:
            metadata.version = yaml_data.get("version")
        if not metadata.tags:
            metadata.tags = yaml_data.get("tags", [])
        if not metadata.dependencies:
            metadata.dependencies = yaml_data.get("dependencies", [])

        # Merge extra fields (don't overwrite existing)
        known_fields = {
            "title",
            "description",
            "author",
            "license",
            "version",
            "tags",
            "dependencies",
            # Fields handled by populate_metadata_from_frontmatter
            "tools",
            "allowed-tools",
            "allowedTools",
        }
        yaml_extra = {k: v for k, v in yaml_data.items() if k not in known_fields}
        if yaml_extra:
            if metadata.extra is None:
                metadata.extra = {}
            for k, v in yaml_extra.items():
                if k not in metadata.extra:
                    metadata.extra[k] = v

    # If no description from frontmatter or YAML, try to extract from content
    if not metadata.description:
        # Remove YAML frontmatter from content for description extraction
        body_content = content
        if content.startswith("---"):
            lines = content.split("\n")
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    body_content = "\n".join(lines[i + 1 :])
                    break
        metadata.description = extract_description_from_content(body_content)

    return metadata


# =============================================================================
# Content-Based Metadata Extraction
# =============================================================================


def extract_metadata_from_content(
    content: str,
    artifact_type: "ArtifactType",
) -> "ArtifactMetadata":
    """Extract metadata from raw file content using the frontmatter pipeline.

    Content-source-agnostic: works with content from GitHub API, local files,
    or any other source. Delegates to the existing extract_frontmatter() +
    populate_metadata_from_frontmatter() pipeline for structured extraction,
    with a fallback to body-text description extraction when frontmatter
    does not provide a description.

    Args:
        content: Raw markdown file content (may include YAML frontmatter).
        artifact_type: Type of artifact being extracted (used for future
            type-specific extraction logic).

    Returns:
        ArtifactMetadata instance populated with any extracted fields.
        Returns an empty ArtifactMetadata if content is empty or contains
        no extractable metadata.

    Examples:
        >>> from skillmeat.core.artifact_detection import ArtifactType
        >>> content = '''---
        ... description: A useful skill
        ... tools: [Bash, Read]
        ... ---
        ... # My Skill
        ... '''
        >>> metadata = extract_metadata_from_content(content, ArtifactType.SKILL)
        >>> metadata.description
        'A useful skill'
    """
    # Import at function level to avoid circular imports
    from skillmeat.core.artifact import ArtifactMetadata

    if not content or not content.strip():
        logger.debug("Empty content provided to extract_metadata_from_content")
        return ArtifactMetadata()

    metadata = ArtifactMetadata()

    # Step 1: Extract frontmatter and populate metadata
    try:
        frontmatter = extract_frontmatter(content)
        if frontmatter:
            metadata = populate_metadata_from_frontmatter(metadata, frontmatter)
            logger.debug(
                "Extracted frontmatter metadata",
                extra={"has_description": metadata.description is not None},
            )
    except Exception as e:
        logger.warning(f"Frontmatter extraction failed: {e}")

    # Step 2: Fallback description from body text if frontmatter had none
    if not metadata.description:
        body_content = content
        # Strip frontmatter block to get body text
        stripped = content.lstrip()
        if stripped.startswith("---"):
            lines = stripped.split("\n")
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    body_content = "\n".join(lines[i + 1 :])
                    break
        fallback_desc = extract_description_from_content(body_content)
        if fallback_desc:
            metadata.description = fallback_desc
            logger.debug("Used body-text fallback for description")

    return metadata


def fetch_and_extract_github_metadata(
    client: "GitHubClient",
    owner: str,
    repo: str,
    path: str,
    artifact_type: "ArtifactType",
    ref: str = "HEAD",
) -> Optional["ArtifactMetadata"]:
    """Fetch artifact metadata from GitHub, handling both files and directories.

    For single-file paths (ending in .md): fetches the file directly via
    the GitHub API and extracts metadata from its content.

    For directory paths: probes for type-appropriate metadata files
    (SKILL.md, AGENT.md, COMMAND.md, etc.) and extracts metadata from
    the first one found.

    Args:
        client: GitHubClient instance for GitHub API access.
        owner: GitHub repository owner (username or organization).
        repo: GitHub repository name.
        path: Path within the repository. Can be a file path ending in .md
            or a directory path.
        artifact_type: Type of artifact to extract metadata for. Determines
            which candidate metadata files to look for in directory paths.
        ref: Git ref (branch, tag, SHA, or "HEAD"). Defaults to "HEAD",
            which resolves to the repository's default branch.

    Returns:
        ArtifactMetadata populated from the first successfully fetched and
        parsed metadata file, or None if no metadata could be extracted
        (file not found, empty content, or all candidates exhausted).

    Examples:
        >>> from skillmeat.core.github_client import GitHubClient
        >>> from skillmeat.core.artifact_detection import ArtifactType
        >>> client = GitHubClient()
        >>> # Single-file artifact (agent or command)
        >>> meta = fetch_and_extract_github_metadata(
        ...     client, "user", "repo", "agents/my-agent.md", ArtifactType.AGENT
        ... )
        >>> # Directory artifact (skill)
        >>> meta = fetch_and_extract_github_metadata(
        ...     client, "user", "repo", "skills/canvas", ArtifactType.SKILL
        ... )
    """
    # Import at function level to avoid circular imports
    from skillmeat.core.artifact_detection import ArtifactType
    from skillmeat.core.github_client import GitHubClientError, GitHubNotFoundError

    # Normalize ref: treat "HEAD" and "latest" as None (default branch)
    ref_param: Optional[str] = ref if ref not in ("HEAD", "latest") else None
    owner_repo = f"{owner}/{repo}"

    def _fetch_content(file_path: str) -> Optional[str]:
        """Fetch and decode file content, returning None on not-found."""
        try:
            content_bytes = client.get_file_content(
                owner_repo, file_path, ref=ref_param
            )
            return content_bytes.decode("utf-8")
        except GitHubNotFoundError:
            logger.debug(f"File not found: {file_path} in {owner_repo}")
            return None
        except GitHubClientError as e:
            logger.warning(
                f"Failed to fetch {file_path} from {owner_repo}: {e.message}"
            )
            return None
        except Exception as e:
            logger.warning(
                f"Unexpected error fetching {file_path} from {owner_repo}: {e}"
            )
            return None

    # --- Single-file path (e.g., agents/my-agent.md) ---
    if path.endswith(".md"):
        logger.debug(f"Fetching single-file metadata: {path} from {owner_repo}")
        content = _fetch_content(path)
        if content:
            return extract_metadata_from_content(content, artifact_type)
        return None

    # --- Directory path: probe for type-appropriate metadata files ---
    candidate_map: Dict[str, List[str]] = {
        "skill": ["SKILL.md", "README.md"],
        "agent": ["AGENT.md", "README.md"],
        "command": ["COMMAND.md", "README.md"],
        "hook": ["HOOK.md", "README.md"],
    }

    # Get the artifact type value as a string for lookup
    type_value = (
        artifact_type.value
        if hasattr(artifact_type, "value")
        else str(artifact_type)
    )
    candidates = candidate_map.get(
        type_value,
        ["SKILL.md", "COMMAND.md", "AGENT.md", "README.md"],
    )

    logger.debug(
        f"Probing directory {path} in {owner_repo} for metadata files: {candidates}"
    )

    for filename in candidates:
        file_path = f"{path}/{filename}" if path else filename
        content = _fetch_content(file_path)
        if content:
            metadata = extract_metadata_from_content(content, artifact_type)
            logger.debug(f"Extracted metadata from {file_path}")
            return metadata

    logger.debug(
        f"No metadata file found for {path} in {owner_repo} "
        f"(tried {candidates})"
    )
    return None


# =============================================================================
# Artifact Linking Functions
# =============================================================================


def extract_artifact_references(
    frontmatter: Dict[str, Any],
    artifact_type: "ArtifactType",
) -> Dict[str, List[str]]:
    """Extract artifact references from frontmatter.

    Identifies references to other artifacts based on artifact type:
    - Agents: 'skills' field indicates required skills
    - Skills/Agents: 'tools' field indicates tool dependencies (handled separately)
    - Skills: 'agent' field indicates which agent this skill enables

    Args:
        frontmatter: Parsed frontmatter dictionary
        artifact_type: Type of the artifact (SKILL, AGENT, COMMAND, etc.)

    Returns:
        Dict with keys 'requires', 'enables', 'related' containing lists of
        reference names to match against collection artifacts.

    Example:
        >>> from skillmeat.core.artifact_detection import ArtifactType
        >>> extract_artifact_references(
        ...     {'skills': ['code-review', 'testing']},
        ...     ArtifactType.AGENT
        ... )
        {'requires': ['code-review', 'testing'], 'enables': [], 'related': []}
    """
    # Import at function level to avoid circular imports
    from skillmeat.core.artifact_detection import ArtifactType

    references: Dict[str, List[str]] = {"requires": [], "enables": [], "related": []}

    if not frontmatter:
        return references

    # Agent-specific: skills field indicates "requires"
    if artifact_type == ArtifactType.AGENT:
        skills = frontmatter.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif isinstance(skills, list):
            skills = [str(s).strip() for s in skills if s]
        else:
            skills = []
        references["requires"].extend(skills)

    # Skill-specific: agent field indicates "enables"
    if artifact_type == ArtifactType.SKILL:
        agent = frontmatter.get("agent")
        if agent:
            if isinstance(agent, str):
                references["enables"].append(agent.strip())
            elif isinstance(agent, list):
                references["enables"].extend([str(a).strip() for a in agent if a])

    # Any artifact: related field indicates "related"
    related = frontmatter.get("related", [])
    if isinstance(related, str):
        related = [r.strip() for r in related.split(",") if r.strip()]
    elif isinstance(related, list):
        related = [str(r).strip() for r in related if r]
    else:
        related = []
    references["related"].extend(related)

    return references


def match_artifact_reference(
    reference: str,
    source_artifacts: List["Artifact"],
    artifact_type: Optional["ArtifactType"] = None,
) -> Optional["Artifact"]:
    """Match artifact reference to a collection artifact.

    Tries matching in order:
    1. Exact name match (case-insensitive)
    2. Plural/singular form match (skill <-> skills)
    3. Hyphen/underscore normalization
    4. Type-filtered match if artifact_type specified

    Args:
        reference: Reference name to match (e.g., "code-review")
        source_artifacts: List of artifacts to search
        artifact_type: Optional type filter for the match

    Returns:
        Matched Artifact or None if no match found.

    Example:
        >>> # Assuming artifacts contains an artifact named 'code-review'
        >>> match_artifact_reference("Code-Review", artifacts)
        <Artifact name='code-review'>
    """
    if not reference or not source_artifacts:
        return None

    reference_lower = reference.lower().strip()
    if not reference_lower:
        return None

    # Filter by type if specified
    candidates = source_artifacts
    if artifact_type:
        candidates = [a for a in source_artifacts if a.type == artifact_type]

    if not candidates:
        return None

    # 1. Exact name match (case-insensitive)
    for artifact in candidates:
        if artifact.name.lower() == reference_lower:
            return artifact

    # 2. Plural/singular form match
    singular = reference_lower.rstrip("s")
    plural = (
        reference_lower + "s" if not reference_lower.endswith("s") else reference_lower
    )

    for artifact in candidates:
        artifact_name_lower = artifact.name.lower()
        if artifact_name_lower == singular or artifact_name_lower == plural:
            return artifact

    # 3. Hyphen/underscore normalization
    # Normalize both reference and artifact names to use same separator
    def normalize_separators(name: str) -> str:
        return name.replace("-", "_").replace(" ", "_")

    normalized_ref = normalize_separators(reference_lower)
    for artifact in candidates:
        artifact_normalized = normalize_separators(artifact.name.lower())
        if artifact_normalized == normalized_ref:
            return artifact

    return None


def create_linked_artifact_reference(
    target_artifact: "Artifact",
    link_type: str = "requires",
    source_name: Optional[str] = None,
) -> "LinkedArtifactReference":
    """Create a LinkedArtifactReference from a matched artifact.

    Args:
        target_artifact: The matched artifact to link to
        link_type: Type of relationship (requires, enables, related)
        source_name: Optional source identifier

    Returns:
        LinkedArtifactReference instance

    Example:
        >>> # Assuming target_artifact is a valid Artifact
        >>> link = create_linked_artifact_reference(target_artifact, 'requires')
        >>> link.link_type
        'requires'
    """
    # Import at function level to avoid circular imports
    from skillmeat.core.artifact import LinkedArtifactReference

    # Get artifact_id - may be stored as 'id' attribute or derive from name/type
    artifact_id = getattr(target_artifact, "id", None)
    if artifact_id is None:
        # Generate a composite identifier if no id attribute exists
        artifact_id = f"{target_artifact.type.value}::{target_artifact.name}"

    # Get origin/source from artifact if not provided
    if source_name is None:
        source_name = getattr(target_artifact, "origin", None)

    return LinkedArtifactReference(
        artifact_id=artifact_id,
        artifact_name=target_artifact.name,
        artifact_type=target_artifact.type,
        source_name=source_name,
        link_type=link_type,
    )


def resolve_artifact_references(
    frontmatter: Dict[str, Any],
    artifact_type: "ArtifactType",
    available_artifacts: List["Artifact"],
    source_name: Optional[str] = None,
) -> Tuple[List["LinkedArtifactReference"], List[str]]:
    """Extract and resolve artifact references from frontmatter.

    This is the main entry point for the linking logic. It:
    1. Extracts references from frontmatter based on artifact type
    2. Attempts to match each reference to available artifacts
    3. Returns both matched links and unmatched reference names

    Args:
        frontmatter: Parsed frontmatter dictionary
        artifact_type: Type of the source artifact
        available_artifacts: List of artifacts to match against
        source_name: Optional source identifier for links

    Returns:
        Tuple of (linked_artifacts, unlinked_references)
        - linked_artifacts: List of successfully matched LinkedArtifactReference
        - unlinked_references: List of reference names that couldn't be matched

    Example:
        >>> from skillmeat.core.artifact_detection import ArtifactType
        >>> linked, unlinked = resolve_artifact_references(
        ...     {'skills': ['code-review', 'unknown-skill']},
        ...     ArtifactType.AGENT,
        ...     collection_artifacts
        ... )
        >>> len(linked)
        1
        >>> unlinked
        ['unknown-skill']
    """
    # Import at function level to avoid circular imports
    from skillmeat.core.artifact import LinkedArtifactReference
    from skillmeat.core.artifact_detection import ArtifactType

    linked_artifacts: List[LinkedArtifactReference] = []
    unlinked_references: List[str] = []

    if not frontmatter or not available_artifacts:
        return linked_artifacts, unlinked_references

    # Extract references by type
    references = extract_artifact_references(frontmatter, artifact_type)

    # Process each link type
    for link_type, ref_names in references.items():
        for ref_name in ref_names:
            if not ref_name:
                continue

            # Determine expected artifact type for matching
            expected_type: Optional[ArtifactType] = None
            if link_type == "requires" and artifact_type == ArtifactType.AGENT:
                expected_type = ArtifactType.SKILL
            elif link_type == "enables" and artifact_type == ArtifactType.SKILL:
                expected_type = ArtifactType.AGENT

            # Try to match
            matched = match_artifact_reference(
                ref_name, available_artifacts, expected_type
            )

            if matched:
                link = create_linked_artifact_reference(matched, link_type, source_name)
                linked_artifacts.append(link)
            else:
                unlinked_references.append(ref_name)

    return linked_artifacts, unlinked_references
