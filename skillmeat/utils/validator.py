"""Artifact validation utilities and type normalization.

This module provides structural validation for artifact structures using the shared
ARTIFACT_SIGNATURES registry from the core artifact_detection module. It also
handles artifact type normalization and validation of type strings/enums.

Key Features:
- Structural Validation: Verifies artifacts meet structural requirements (file/directory
  type, manifest presence) based on shared signatures.
- Type Normalization: Converts various string representations and aliases to
  canonical ArtifactType enum members.
- Consistent Discovery: Uses extract_manifest_file() for case-insensitive manifest
  discovery across all artifact types.

Validation Approach:
1. Check path exists.
2. Verify path type (file vs directory) matches ARTIFACT_SIGNATURES requirements.
3. Find manifest file using extract_manifest_file() (case-insensitive).
4. Validate manifest exists (if required) and has non-empty content.

Example:
    >>> from skillmeat.utils.validator import ArtifactValidator, normalize_artifact_type
    >>> # Normalize type
    >>> artifact_type = normalize_artifact_type("mcp_server")
    >>> # Validate structure
    >>> result = ArtifactValidator.validate(Path("./my-skill"), artifact_type)
    >>> if result.is_valid:
    ...     print(f"Validated {result.artifact_type.value} successfully")
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from skillmeat.core.artifact_detection import (
    ARTIFACT_SIGNATURES,
    ArtifactType,
    extract_manifest_file,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Type Normalization Constants
# =============================================================================

# Backwards compatibility mappings for historical artifact type names
TYPE_ALIASES = {
    # MCP aliases (historical variations)
    "mcp_server": ArtifactType.MCP,
    "mcp-server": ArtifactType.MCP,
    "mcpserver": ArtifactType.MCP,
    # Add future aliases here as needed
}


# =============================================================================
# Type Validation and Normalization Functions
# =============================================================================


def normalize_artifact_type(type_value: Any) -> ArtifactType:
    """Normalize various artifact type representations to ArtifactType enum.

    Accepts ArtifactType enum instances, lowercase string names, snake_case
    variants, and historical aliases. Provides backwards compatibility for
    legacy type names (e.g., "mcp_server" → ArtifactType.MCP).

    Args:
        type_value: Type value to normalize. Can be:
            - ArtifactType enum instance
            - String matching enum value (e.g., "skill", "command")
            - Snake_case variant (e.g., "mcp_server")
            - Kebab-case variant (e.g., "mcp-server")

    Returns:
        Normalized ArtifactType enum instance

    Raises:
        ValueError: If type_value cannot be normalized to a valid ArtifactType

    Examples:
        >>> normalize_artifact_type("skill")
        <ArtifactType.SKILL: 'skill'>

        >>> normalize_artifact_type("COMMAND")
        <ArtifactType.COMMAND: 'command'>

        >>> normalize_artifact_type(ArtifactType.AGENT)
        <ArtifactType.AGENT: 'agent'>

        >>> normalize_artifact_type("mcp_server")  # Historical alias
        <ArtifactType.MCP: 'mcp'>

        >>> normalize_artifact_type("mcp-server")  # Kebab-case alias
        <ArtifactType.MCP: 'mcp'>

        >>> normalize_artifact_type("unknown")
        Traceback (most recent call last):
            ...
        ValueError: Invalid artifact type: 'unknown'. Valid types: skill, command, agent, hook, mcp, project_config, spec_file, rule_file, context_file, progress_template
    """
    # Already an ArtifactType enum - return as-is
    if isinstance(type_value, ArtifactType):
        return type_value

    # Convert to lowercase string for normalization
    if not isinstance(type_value, str):
        raise ValueError(
            f"Artifact type must be a string or ArtifactType enum, got {type(type_value).__name__}"
        )

    normalized_str = type_value.lower().strip()

    # Check historical aliases first (exact match)
    if normalized_str in TYPE_ALIASES:
        return TYPE_ALIASES[normalized_str]

    # Try to match against ArtifactType enum values
    try:
        return ArtifactType(normalized_str)
    except ValueError:
        pass

    # Build helpful error message with all valid types
    valid_types = ", ".join(t.value for t in ArtifactType)
    raise ValueError(
        f"Invalid artifact type: {type_value!r}. Valid types: {valid_types}"
    )


def validate_artifact_type(type_value: Any) -> bool:
    """Check if a value is a valid artifact type without raising exceptions.

    This is a non-throwing version of normalize_artifact_type() for use
    in validation contexts where you need a boolean result rather than
    an exception.

    Args:
        type_value: Type value to validate. Can be:
            - ArtifactType enum instance
            - String matching enum value (e.g., "skill", "command")
            - Snake_case variant (e.g., "mcp_server")
            - Kebab-case variant (e.g., "mcp-server")

    Returns:
        True if type_value can be normalized to a valid ArtifactType,
        False otherwise

    Examples:
        >>> validate_artifact_type("skill")
        True

        >>> validate_artifact_type(ArtifactType.COMMAND)
        True

        >>> validate_artifact_type("mcp_server")  # Historical alias
        True

        >>> validate_artifact_type("invalid")
        False

        >>> validate_artifact_type(123)  # Wrong type
        False

        >>> validate_artifact_type(None)
        False
    """
    try:
        normalize_artifact_type(type_value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


# =============================================================================
# Validation Result Data Class
# =============================================================================


@dataclass
class ValidationResult:
    """Result of artifact validation.

    Attributes:
        is_valid: Whether the artifact passed validation
        error_message: Description of validation failure (None if valid)
        artifact_type: The validated artifact type (None if invalid)
        deprecation_warning: Warning about deprecated patterns (None if not deprecated)
    """

    is_valid: bool
    error_message: Optional[str] = None
    artifact_type: Optional[ArtifactType] = None
    deprecation_warning: Optional[str] = None


def _validate_content_not_empty(file_path: Path, file_type: str) -> Optional[str]:
    """Validate that a file has non-empty content.

    Args:
        file_path: Path to the file to check
        file_type: Human-readable type name for error messages (e.g., "SKILL.md")

    Returns:
        Error message if content is empty or unreadable, None if valid
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            return f"{file_type} is empty"
        return None
    except Exception as e:
        return f"Failed to read {file_type}: {e}"


def _find_any_md_file(directory: Path) -> Optional[Path]:
    """Find any .md file in a directory.

    Used for COMMAND and AGENT validation when no specific manifest is found.
    Prefers manifest files (command.md, COMMAND.md, agent.md, AGENT.md) over
    other .md files.

    Args:
        directory: Directory to search

    Returns:
        Path to first .md file found, or None if no .md files exist
    """
    if not directory.is_dir():
        return None

    # Preferred manifest file names (case-insensitive search)
    preferred_names = {"command.md", "agent.md"}

    md_files = list(directory.glob("*.md"))
    if not md_files:
        return None

    # Try to find a preferred manifest first
    for md_file in md_files:
        if md_file.name.lower() in preferred_names:
            return md_file

    # Fall back to any .md file
    return md_files[0]


class ArtifactValidator:
    """Validates artifact structure based on type.

    Uses ARTIFACT_SIGNATURES registry for structural rules and
    extract_manifest_file() for case-insensitive manifest discovery.

    Supported artifact types:
        - SKILL: Directory with SKILL.md manifest (required)
        - COMMAND: .md file or directory with .md file(s)
        - AGENT: .md file or directory with .md file(s)
        - HOOK: Directory with settings.json configuration
        - MCP: Directory with .mcp.json or mcp.json configuration
    """

    @staticmethod
    def validate_skill(path: Path) -> ValidationResult:
        """Validate skill artifact structure.

        Checks that the path is a directory and contains a valid SKILL.md
        manifest (case-insensitive).

        Rules (from ARTIFACT_SIGNATURES[ArtifactType.SKILL]):
            - Must be a directory (is_directory=True)
            - Must contain manifest (requires_manifest=True)
            - Valid manifests: SKILL.md, skill.md
            - Manifest must have non-empty content

        Args:
            path: Path to skill directory

        Returns:
            ValidationResult with validation status and artifact type
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        sig = ARTIFACT_SIGNATURES[ArtifactType.SKILL]

        # Skills must be directories
        if not path.is_dir():
            return ValidationResult(
                is_valid=False,
                error_message=f"Skill path is not a directory: {path}",
            )

        # Find manifest using case-insensitive search
        manifest = extract_manifest_file(path, ArtifactType.SKILL)
        if manifest is None:
            # Build helpful error message with valid manifest names
            valid_names = ", ".join(sorted(sig.manifest_names))
            return ValidationResult(
                is_valid=False,
                error_message=f"Skill must contain SKILL.md in root (valid: {valid_names})",
            )

        # Validate content is non-empty
        error = _validate_content_not_empty(manifest, manifest.name)
        if error:
            return ValidationResult(is_valid=False, error_message=error)

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.SKILL,
        )

    @staticmethod
    def validate_command(path: Path) -> ValidationResult:
        """Validate command artifact structure.

        Commands can be either:
        1. A standalone .md file (file itself is the command)
        2. A directory containing one or more .md files (DEPRECATED)

        This flexibility exists because commands are often simple single-file
        artifacts, but may also be organized in directories for complex commands
        with supporting files.

        Requirements:
            - Must be a .md file OR a directory containing at least one .md file
            - The .md file must have non-empty content

        Deprecation:
            - Directory-based commands are deprecated; commands should be single .md files

        Args:
            path: Path to command file or directory

        Returns:
            ValidationResult with validation status and potential deprecation warning
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        deprecation_warning = None

        # Commands can be either a .md file or a directory with .md file(s)
        if path.is_file():
            if path.suffix.lower() != ".md":
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Command file must be a .md file: {path}",
                )
            command_file = path
        elif path.is_dir():
            # Directory-based commands are deprecated
            deprecation_warning = (
                "Directory-based commands are deprecated. "
                "Commands should be single .md files. "
                "Consider converting to file format."
            )
            logger.warning(
                f"Deprecated pattern detected: directory-based command at {path}"
            )

            # Try manifest first (case-insensitive), then any .md file
            command_file = extract_manifest_file(path, ArtifactType.COMMAND)
            if command_file is None:
                command_file = _find_any_md_file(path)
            if command_file is None:
                return ValidationResult(
                    is_valid=False,
                    error_message="Command directory must contain a .md file",
                )
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path type: {path}",
            )

        # Validate content is non-empty
        error = _validate_content_not_empty(command_file, "Command file")
        if error:
            return ValidationResult(is_valid=False, error_message=error)

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.COMMAND,
            deprecation_warning=deprecation_warning,
        )

    @staticmethod
    def validate_agent(path: Path) -> ValidationResult:
        """Validate agent artifact structure.

        Agents can be either:
        1. A standalone .md file (file itself is the agent prompt)
        2. A directory containing AGENT.md/agent.md or other .md files (DEPRECATED)

        This flexibility exists because agents are often simple single-file
        prompts, but may also be organized in directories for complex agents
        with supporting files.

        Requirements:
            - Must be a .md file OR a directory containing at least one .md file
            - Prefers AGENT.md/agent.md in directories (via extract_manifest_file)
            - The .md file must have non-empty content

        Deprecation:
            - Directory-based agents are deprecated; agents should be single .md files

        Args:
            path: Path to agent file or directory

        Returns:
            ValidationResult with validation status and potential deprecation warning
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        deprecation_warning = None

        # Agents can be either a .md file or a directory with .md file(s)
        if path.is_file():
            if path.suffix.lower() != ".md":
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Agent file must be a .md file: {path}",
                )
            agent_file = path
        elif path.is_dir():
            # Directory-based agents are deprecated
            deprecation_warning = (
                "Directory-based agents are deprecated. "
                "Agents should be single .md files. "
                "Consider converting to file format."
            )
            logger.warning(
                f"Deprecated pattern detected: directory-based agent at {path}"
            )

            # Try manifest first (case-insensitive for AGENT.md/agent.md)
            agent_file = extract_manifest_file(path, ArtifactType.AGENT)
            if agent_file is None:
                agent_file = _find_any_md_file(path)
            if agent_file is None:
                return ValidationResult(
                    is_valid=False,
                    error_message="Agent directory must contain a .md file",
                )
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path type: {path}",
            )

        # Validate content is non-empty
        error = _validate_content_not_empty(agent_file, "Agent file")
        if error:
            return ValidationResult(is_valid=False, error_message=error)

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.AGENT,
            deprecation_warning=deprecation_warning,
        )

    @staticmethod
    def validate_hook(path: Path) -> ValidationResult:
        """Validate hook artifact structure.

        Hooks are configuration-based artifacts that define event triggers
        for Claude Code. They require a settings.json configuration file.

        Rules (from ARTIFACT_SIGNATURES[ArtifactType.HOOK]):
            - Structure: Directory or file (typically directory)
            - Manifest: requires_manifest=False (but settings.json is canonical)
            - Valid manifests: settings.json
            - Manifest must have non-empty content

        Args:
            path: Path to hook directory or file

        Returns:
            ValidationResult with validation status and artifact type
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        sig = ARTIFACT_SIGNATURES[ArtifactType.HOOK]

        # Hooks are typically directories but can be represented differently
        # Check for manifest using case-insensitive search
        if path.is_dir():
            manifest = extract_manifest_file(path, ArtifactType.HOOK)
            if manifest is None:
                valid_names = ", ".join(sorted(sig.manifest_names))
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Hook directory must contain configuration file ({valid_names})",
                )
            config_file = manifest
        elif path.is_file():
            # Direct file reference (e.g., settings.json itself)
            if path.name.lower() not in {m.lower() for m in sig.manifest_names}:
                valid_names = ", ".join(sorted(sig.manifest_names))
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Hook file must be a configuration file ({valid_names}): {path.name}",
                )
            config_file = path
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path type: {path}",
            )

        # Validate content is non-empty
        error = _validate_content_not_empty(config_file, config_file.name)
        if error:
            return ValidationResult(is_valid=False, error_message=error)

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.HOOK,
        )

    @staticmethod
    def validate_mcp(path: Path) -> ValidationResult:
        """Validate MCP server artifact structure.

        MCP (Model Context Protocol) servers are configurations for external
        tool integrations. They require a .mcp.json or mcp.json configuration file.

        Rules (from ARTIFACT_SIGNATURES[ArtifactType.MCP]):
            - Structure: Directory or file (typically directory)
            - Manifest: requires_manifest=False (but .mcp.json is canonical)
            - Valid manifests: .mcp.json, mcp.json
            - Manifest must have non-empty content

        Args:
            path: Path to MCP directory or file

        Returns:
            ValidationResult with validation status and artifact type
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        sig = ARTIFACT_SIGNATURES[ArtifactType.MCP]

        # MCP configs are typically directories but can be files
        if path.is_dir():
            manifest = extract_manifest_file(path, ArtifactType.MCP)
            if manifest is None:
                valid_names = ", ".join(sorted(sig.manifest_names))
                return ValidationResult(
                    is_valid=False,
                    error_message=f"MCP directory must contain configuration file ({valid_names})",
                )
            config_file = manifest
        elif path.is_file():
            # Direct file reference (e.g., .mcp.json itself)
            if path.name.lower() not in {m.lower() for m in sig.manifest_names}:
                valid_names = ", ".join(sorted(sig.manifest_names))
                return ValidationResult(
                    is_valid=False,
                    error_message=f"MCP file must be a configuration file ({valid_names}): {path.name}",
                )
            config_file = path
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path type: {path}",
            )

        # Validate content is non-empty
        error = _validate_content_not_empty(config_file, config_file.name)
        if error:
            return ValidationResult(is_valid=False, error_message=error)

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.MCP,
        )

    @staticmethod
    def validate(path: Path, artifact_type: ArtifactType) -> ValidationResult:
        """Route to appropriate validator based on type.

        This is the main entry point for validation. It routes to the
        appropriate type-specific validator method.

        Args:
            path: Path to artifact
            artifact_type: Type of artifact to validate as

        Returns:
            ValidationResult with validation status

        Example:
            >>> result = ArtifactValidator.validate(Path("./my-skill"), ArtifactType.SKILL)
            >>> if not result.is_valid:
            ...     print(f"Validation failed: {result.error_message}")
        """
        validators = {
            ArtifactType.SKILL: ArtifactValidator.validate_skill,
            ArtifactType.COMMAND: ArtifactValidator.validate_command,
            ArtifactType.AGENT: ArtifactValidator.validate_agent,
            ArtifactType.HOOK: ArtifactValidator.validate_hook,
            ArtifactType.MCP: ArtifactValidator.validate_mcp,
        }

        validator = validators.get(artifact_type)
        if validator is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unknown or unsupported artifact type: {artifact_type}",
            )

        return validator(path)

    @staticmethod
    def detect_artifact_type(path: Path) -> Optional[ArtifactType]:
        """Auto-detect artifact type from filesystem structure.

        Uses ARTIFACT_SIGNATURES registry and extract_manifest_file() for
        consistent detection across the codebase. Detection follows priority
        order to handle ambiguous cases (e.g., directory with both SKILL.md
        and AGENT.md).

        Detection priority (first match wins):
            1. SKILL - Directory with SKILL.md/skill.md (case-insensitive)
            2. AGENT - Directory with AGENT.md/agent.md (case-insensitive)
            3. HOOK - Directory with settings.json
            4. MCP - Directory with .mcp.json/mcp.json
            5. COMMAND - .md file or directory with .md files (fallback)

        Args:
            path: Path to artifact (file or directory)

        Returns:
            Detected ArtifactType or None if cannot determine

        Example:
            >>> artifact_type = ArtifactValidator.detect_artifact_type(Path("./my-skill"))
            >>> if artifact_type == ArtifactType.SKILL:
            ...     print("Found a skill!")
        """
        if not path.exists():
            return None

        # Priority order for detection (most specific first)
        detection_order: List[ArtifactType] = [
            ArtifactType.SKILL,
            ArtifactType.AGENT,
            ArtifactType.HOOK,
            ArtifactType.MCP,
        ]

        # Check for manifest files in directories using shared detection
        if path.is_dir():
            for artifact_type in detection_order:
                manifest = extract_manifest_file(path, artifact_type)
                if manifest is not None:
                    return artifact_type

        # Check if it's a standalone .md file (COMMAND or AGENT)
        # Default to COMMAND for standalone .md files as per existing behavior
        if path.is_file() and path.suffix.lower() == ".md":
            return ArtifactType.COMMAND

        # Check if directory has any .md files (fallback to COMMAND)
        if path.is_dir():
            md_files = list(path.glob("*.md"))
            if md_files:
                return ArtifactType.COMMAND

        return None
