"""Unified artifact detection module for SkillMeat.

This module provides the canonical source of truth for:
- ArtifactType enum (all artifact types in one place)
- DetectionResult dataclass (detection outcomes)
- ArtifactSignature dataclass (structural rules per type)
- Container alias registries (normalize directory names)
- Detection functions (infer type, detect artifacts)

All modules that need artifact type information should import from here.
This eliminates duplicate enum definitions and ensures consistent detection
across local discovery, marketplace heuristics, and validators.

Example:
    >>> from skillmeat.core.artifact_detection import (
    ...     ArtifactType,
    ...     DetectionResult,
    ...     detect_artifact,
    ... )
    >>> result = detect_artifact(Path("./skills/my-skill"))
    >>> result.artifact_type
    <ArtifactType.SKILL: 'skill'>
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Literal, Optional, Set

# =============================================================================
# Public API Exports
# =============================================================================

__all__ = [
    # Enums
    "ArtifactType",
    "CompositeType",
    # Data classes
    "DetectionResult",
    "ArtifactSignature",
    "ContainerConfig",
    # Exceptions
    "DetectionError",
    "InvalidContainerError",
    "InvalidArtifactTypeError",
    # Registries
    "ARTIFACT_SIGNATURES",
    "CONTAINER_ALIASES",
    "CONTAINER_TO_TYPE",
    "MANIFEST_FILES",
    "CANONICAL_CONTAINERS",
    # Functions
    "normalize_container_name",
    "get_artifact_type_from_container",
    "infer_artifact_type",
    "detect_artifact",
    "extract_manifest_file",
]

# =============================================================================
# Enums
# =============================================================================


class ArtifactType(str, Enum):
    """Canonical artifact type enum for SkillMeat.

    This enum extends both str and Enum to enable:
    - Direct JSON serialization (ArtifactType.SKILL == "skill")
    - String comparison (artifact.type == "skill")
    - Backwards compatibility with existing string-based code

    Primary artifact types (deployable Claude Code extensions):
        SKILL: Skills are directories containing SKILL.md and supporting files
        COMMAND: Single-file slash commands (.md files)
        AGENT: Single-file agent prompts (.md files)
        HOOK: Hook configurations (file-based)
        MCP: Model Context Protocol server configurations

    Composite artifact types (deployable multi-artifact bundles):
        COMPOSITE: A deployable package that groups multiple artifact types.
                   The specific composite variant is determined by CompositeType
                   (e.g., PLUGIN). COMPOSITE is deployable — it maps to a
                   directory structure and can be installed into a project.
                   Reserved future variants: STACK (multi-tool stack),
                   SUITE (curated workflow suite) — not yet implemented.

    Context entity types (non-deployable, for project management):
        PROJECT_CONFIG: CLAUDE.md project configuration files
        SPEC_FILE: Specification documents in .claude/specs/
        RULE_FILE: Rule files in .claude/rules/
        CONTEXT_FILE: Context documents in .claude/context/
        PROGRESS_TEMPLATE: Progress tracking templates in .claude/progress/

    Example:
        >>> ArtifactType.SKILL.value
        'skill'
        >>> ArtifactType("command")
        <ArtifactType.COMMAND: 'command'>
        >>> str(ArtifactType.AGENT)
        'agent'
        >>> ArtifactType.COMPOSITE in ArtifactType.deployable_types()
        True
    """

    # Primary artifact types
    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    HOOK = "hook"
    MCP = "mcp"
    WORKFLOW = "workflow"

    # Composite artifact types (composite-artifact-infrastructure-v1)
    COMPOSITE = "composite"

    # Context entity types (agent-context-entities-v1)
    PROJECT_CONFIG = "project_config"
    SPEC_FILE = "spec_file"
    RULE_FILE = "rule_file"
    CONTEXT_FILE = "context_file"
    PROGRESS_TEMPLATE = "progress_template"

    @classmethod
    def primary_types(cls) -> List["ArtifactType"]:
        """Return list of primary (deployable, single-artifact) types."""
        return [cls.SKILL, cls.COMMAND, cls.AGENT, cls.HOOK, cls.MCP, cls.WORKFLOW]

    @classmethod
    def composite_types(cls) -> List["ArtifactType"]:
        """Return list of composite (multi-artifact bundle) types.

        Composite artifacts are deployable packages that group multiple
        artifact types together. The variant behaviour within this category
        is controlled by CompositeType (e.g., CompositeType.PLUGIN).
        """
        return [cls.COMPOSITE]

    @classmethod
    def deployable_types(cls) -> List["ArtifactType"]:
        """Return all types that can be deployed to a project.

        Includes both primary artifact types and composite types.
        Context entity types are explicitly excluded because they are
        non-deployable project-management constructs.
        """
        return cls.primary_types() + cls.composite_types()

    @classmethod
    def context_types(cls) -> List["ArtifactType"]:
        """Return list of context entity types (non-deployable)."""
        return [
            cls.PROJECT_CONFIG,
            cls.SPEC_FILE,
            cls.RULE_FILE,
            cls.CONTEXT_FILE,
            cls.PROGRESS_TEMPLATE,
        ]


class CompositeType(str, Enum):
    """Variant classifier for COMPOSITE artifacts.

    When an artifact has ArtifactType.COMPOSITE, this enum specifies
    which kind of composite it is and therefore how it should be
    installed, displayed, and resolved.

    Variants:
        PLUGIN: A curated bundle of skills, commands, agents, and/or
                hooks that are distributed and deployed as a unit.
                This is the initial supported composite variant.

    Reserved for future use (not yet implemented):
        STACK: A multi-tool stack declaration (infrastructure-level).
        SUITE: A curated workflow suite (end-to-end use-case bundle).

    Example:
        >>> CompositeType.PLUGIN.value
        'plugin'
        >>> CompositeType("plugin")
        <CompositeType.PLUGIN: 'plugin'>
    """

    PLUGIN = "plugin"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DetectionResult:
    """Result of artifact detection operation.

    Contains all information about a detected artifact, including
    the type, confidence level, and reasons for the detection.

    Attributes:
        artifact_type: The detected artifact type
        name: The artifact name (derived from path or manifest)
        path: Absolute or relative path to the artifact
        container_type: Container directory name (e.g., "skills", "commands")
        detection_mode: "strict" for exact rule matches, "heuristic" for fuzzy
        confidence: Detection confidence 0-100 (100 = certain)
        manifest_file: Path to manifest file if found (e.g., SKILL.md)
        metadata: Additional metadata extracted from manifest
        detection_reasons: List of reasons supporting this detection
        deprecation_warning: Warning message if using deprecated patterns

    Example:
        >>> result = DetectionResult(
        ...     artifact_type=ArtifactType.SKILL,
        ...     name="my-skill",
        ...     path="/path/to/skills/my-skill",
        ...     container_type="skills",
        ...     detection_mode="strict",
        ...     confidence=100,
        ...     manifest_file="SKILL.md",
        ...     detection_reasons=["Found SKILL.md manifest", "In skills/ directory"]
        ... )
        >>> result.is_confident
        True
    """

    artifact_type: ArtifactType
    name: str
    path: str
    container_type: str
    detection_mode: Literal["strict", "heuristic"]
    confidence: int
    manifest_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    detection_reasons: List[str] = field(default_factory=list)
    deprecation_warning: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if not 0 <= self.confidence <= 100:
            raise ValueError(f"Confidence must be 0-100, got {self.confidence}")

    @property
    def is_confident(self) -> bool:
        """Return True if confidence is above threshold (80+)."""
        return self.confidence >= 80

    @property
    def is_strict(self) -> bool:
        """Return True if detection was in strict mode."""
        return self.detection_mode == "strict"


@dataclass
class ArtifactSignature:
    """Defines structural rules for detecting an artifact type.

    Each artifact type has a signature that describes:
    - Which container directories it can appear in
    - Whether it's a directory or file
    - What manifest files it requires or allows
    - Whether it can be nested inside other artifacts

    These signatures are used by detection functions to identify
    artifact types from filesystem structure.

    Attributes:
        artifact_type: The artifact type this signature describes
        container_names: Valid container directory names (e.g., {"skills", "skill"})
        is_directory: True if artifact is a directory (skills), False if file (commands)
        requires_manifest: True if artifact must have a manifest file
        manifest_names: Valid manifest file names (e.g., {"SKILL.md", "skill.md"})
        allowed_nesting: True if artifacts can be nested (e.g., commands in subdirs)

    Example:
        >>> sig = ArtifactSignature(
        ...     artifact_type=ArtifactType.SKILL,
        ...     container_names={"skills", "skill", "claude-skills"},
        ...     is_directory=True,
        ...     requires_manifest=True,
        ...     manifest_names={"SKILL.md", "skill.md"},
        ...     allowed_nesting=False
        ... )
        >>> sig.matches_container("skills")
        True
    """

    artifact_type: ArtifactType
    container_names: Set[str]
    is_directory: bool
    requires_manifest: bool
    manifest_names: Set[str] = field(default_factory=set)
    allowed_nesting: bool = False

    def matches_container(self, name: str) -> bool:
        """Check if container name matches this signature (case-insensitive)."""
        return name.lower() in {n.lower() for n in self.container_names}

    def matches_manifest(self, filename: str) -> bool:
        """Check if filename matches a valid manifest name (case-insensitive)."""
        return filename.lower() in {m.lower() for m in self.manifest_names}


@dataclass(frozen=True)
class ContainerConfig:
    """Configuration for an artifact type's container.

    Defines the canonical container name and all recognized aliases
    for a specific artifact type. This enables consistent normalization
    across different naming conventions used in various contexts.

    Attributes:
        canonical_name: The official container directory name (e.g., "skills")
        aliases: Frozenset of all recognized names including canonical
                 (e.g., {"skills", "skill", "SKILL.md"})

    Example:
        >>> config = ContainerConfig(
        ...     canonical_name="skills",
        ...     aliases=frozenset({"skills", "skill", "SKILL.md"})
        ... )
        >>> "skill" in config.aliases
        True
    """

    canonical_name: str
    aliases: FrozenSet[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        """Ensure canonical name is always in aliases."""
        if self.canonical_name not in self.aliases:
            # Since frozen, we need to use object.__setattr__
            object.__setattr__(
                self,
                "aliases",
                frozenset(self.aliases | {self.canonical_name}),
            )


# =============================================================================
# Exceptions
# =============================================================================


class DetectionError(Exception):
    """Base exception for artifact detection failures.

    This is the parent class for all detection-related exceptions,
    allowing callers to catch all detection errors with a single
    except clause if desired.

    Example:
        >>> try:
        ...     normalize_container_name("invalid", ArtifactType.SKILL)
        ... except DetectionError as e:
        ...     print(f"Detection failed: {e}")
    """

    pass


class InvalidContainerError(DetectionError):
    """Raised when a container name is not recognized for an artifact type.

    This exception is raised by normalize_container_name() when the provided
    container name does not match any known alias for the specified artifact type.

    Attributes:
        container_name: The invalid container name that was provided
        artifact_type: The artifact type being normalized for
        valid_aliases: Set of valid container aliases for this artifact type

    Example:
        >>> raise InvalidContainerError(
        ...     container_name="invalid_dir",
        ...     artifact_type=ArtifactType.SKILL,
        ...     valid_aliases={"skills", "skill", "SKILL.md"}
        ... )
        InvalidContainerError: Invalid container name 'invalid_dir' for artifact type 'skill'. Valid aliases: SKILL.md, skill, skills
    """

    def __init__(
        self,
        container_name: str,
        artifact_type: ArtifactType,
        valid_aliases: Set[str],
    ) -> None:
        """Initialize InvalidContainerError.

        Args:
            container_name: The container name that failed validation
            artifact_type: The artifact type context for the error
            valid_aliases: Set of valid alias names for reference
        """
        self.container_name = container_name
        self.artifact_type = artifact_type
        self.valid_aliases = valid_aliases
        super().__init__(
            f"Invalid container name '{container_name}' for artifact type "
            f"'{artifact_type.value}'. Valid aliases: {', '.join(sorted(valid_aliases))}"
        )


class InvalidArtifactTypeError(DetectionError):
    """Raised when an invalid artifact type value is provided.

    This exception is raised when attempting to use an artifact type
    string that doesn't correspond to any valid ArtifactType enum value.

    Attributes:
        type_value: The invalid type value that was provided
        valid_types: List of valid artifact type values for reference

    Example:
        >>> raise InvalidArtifactTypeError("unknown_type")
        InvalidArtifactTypeError: Invalid artifact type 'unknown_type'. Valid types: agent, command, hook, mcp_server, skill
    """

    def __init__(
        self,
        type_value: str,
        valid_types: Optional[List[str]] = None,
    ) -> None:
        """Initialize InvalidArtifactTypeError.

        Args:
            type_value: The invalid type string that failed validation
            valid_types: Optional list of valid types; defaults to all ArtifactType values
        """
        self.type_value = type_value
        self.valid_types = valid_types or [t.value for t in ArtifactType]
        super().__init__(
            f"Invalid artifact type '{type_value}'. "
            f"Valid types: {', '.join(sorted(self.valid_types))}"
        )


# =============================================================================
# Registries
# =============================================================================

ARTIFACT_SIGNATURES: Dict[ArtifactType, ArtifactSignature] = {
    ArtifactType.SKILL: ArtifactSignature(
        artifact_type=ArtifactType.SKILL,
        container_names={"skills", "skill", "claude-skills"},
        is_directory=True,
        requires_manifest=True,
        manifest_names={"SKILL.md", "skill.md"},
        allowed_nesting=False,
    ),
    ArtifactType.COMMAND: ArtifactSignature(
        artifact_type=ArtifactType.COMMAND,
        container_names={"commands", "command", "claude-commands"},
        is_directory=False,
        requires_manifest=False,
        manifest_names={"COMMAND.md", "command.md"},
        allowed_nesting=True,
    ),
    ArtifactType.AGENT: ArtifactSignature(
        artifact_type=ArtifactType.AGENT,
        container_names={"agents", "agent", "subagents", "claude-agents"},
        is_directory=False,
        requires_manifest=False,
        manifest_names={"AGENT.md", "agent.md"},
        allowed_nesting=True,
    ),
    ArtifactType.HOOK: ArtifactSignature(
        artifact_type=ArtifactType.HOOK,
        container_names={"hooks", "hook", "claude-hooks"},
        is_directory=True,  # Hooks are directory-based artifacts
        requires_manifest=False,  # No specific manifest required
        manifest_names={"settings.json"},  # Optional config file
        allowed_nesting=False,
    ),
    ArtifactType.MCP: ArtifactSignature(
        artifact_type=ArtifactType.MCP,
        container_names={"mcp", "mcp-servers", "servers", "mcp_servers", "claude-mcp"},
        is_directory=False,
        requires_manifest=False,
        manifest_names={".mcp.json", "mcp.json"},
        allowed_nesting=False,
    ),
    ArtifactType.WORKFLOW: ArtifactSignature(
        artifact_type=ArtifactType.WORKFLOW,
        container_names={"workflows", "workflow", "claude-workflows"},
        is_directory=True,  # Workflows are directory-based artifacts
        requires_manifest=True,
        manifest_names={"WORKFLOW.yaml", "WORKFLOW.json", "workflow.yaml", "workflow.json"},
        allowed_nesting=False,
    ),
    ArtifactType.COMPOSITE: ArtifactSignature(
        artifact_type=ArtifactType.COMPOSITE,
        container_names={"composites", "composite", "plugins", "plugin", "claude-composites"},
        is_directory=True,  # Composites are directory-based (contain multiple artifacts)
        requires_manifest=True,
        manifest_names={"COMPOSITE.md", "composite.md", "PLUGIN.md", "plugin.md"},
        allowed_nesting=False,
    ),
}

# Container directory name aliases - maps ArtifactType to all valid directory names
CONTAINER_ALIASES: Dict[ArtifactType, Set[str]] = {
    ArtifactType.SKILL: {"skills", "skill", "claude-skills"},
    ArtifactType.COMMAND: {"commands", "command", "claude-commands"},
    ArtifactType.AGENT: {"agents", "agent", "subagents", "claude-agents"},
    ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
    ArtifactType.MCP: {"mcp", "mcp-servers", "servers", "mcp_servers", "claude-mcp"},
    ArtifactType.WORKFLOW: {"workflows", "workflow", "claude-workflows"},
    ArtifactType.COMPOSITE: {"composites", "composite", "plugins", "plugin", "claude-composites"},
}

# Reverse lookup: container name -> ArtifactType (lowercase for case-insensitive matching)
CONTAINER_TO_TYPE: Dict[str, ArtifactType] = {}
for _artifact_type, _aliases in CONTAINER_ALIASES.items():
    for _alias in _aliases:
        CONTAINER_TO_TYPE[_alias.lower()] = _artifact_type

# Valid manifest file names per type
MANIFEST_FILES: Dict[ArtifactType, Set[str]] = {
    ArtifactType.SKILL: {"SKILL.md", "skill.md"},
    ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
    ArtifactType.AGENT: {"AGENT.md", "agent.md"},
    ArtifactType.HOOK: {"settings.json"},
    ArtifactType.MCP: {".mcp.json", "mcp.json"},
    ArtifactType.WORKFLOW: {"WORKFLOW.yaml", "WORKFLOW.json", "workflow.yaml", "workflow.json"},
    ArtifactType.COMPOSITE: {"COMPOSITE.md", "composite.md", "PLUGIN.md", "plugin.md"},
}

# Canonical (preferred) container names
CANONICAL_CONTAINERS: Dict[ArtifactType, str] = {
    ArtifactType.SKILL: "skills",
    ArtifactType.COMMAND: "commands",
    ArtifactType.AGENT: "agents",
    ArtifactType.HOOK: "hooks",
    ArtifactType.MCP: "mcp",
    ArtifactType.WORKFLOW: "workflows",
    ArtifactType.COMPOSITE: "composites",
}


# =============================================================================
# Functions
# =============================================================================


def normalize_container_name(
    name: str, artifact_type: Optional[ArtifactType] = None
) -> str:
    """Normalize a container directory name to its canonical form.

    Takes any recognized container alias and returns the canonical container name.
    Supports case-insensitive matching.

    Args:
        name: Container name to normalize (e.g., "SKILLS", "subagents", "mcp-servers")
        artifact_type: Optional artifact type to validate against. If provided,
                      validates that the container name is valid for this type.

    Returns:
        Canonical container name (e.g., "skills", "agents", "mcp")

    Raises:
        InvalidContainerError: If name is not recognized for the given artifact type,
                              or if no artifact type provided and name is not recognized
                              for any type.

    Examples:
        >>> normalize_container_name("SKILLS")
        'skills'
        >>> normalize_container_name("subagents", ArtifactType.AGENT)
        'agents'
        >>> normalize_container_name("mcp-servers")
        'mcp'
        >>> normalize_container_name("invalid", ArtifactType.SKILL)
        InvalidContainerError: Invalid container name 'invalid' for artifact type 'skill'...
    """
    name_lower = name.lower()

    # If artifact_type specified, check only that type's aliases
    if artifact_type is not None:
        aliases = CONTAINER_ALIASES.get(artifact_type, set())
        aliases_lower = {a.lower() for a in aliases}
        if name_lower in aliases_lower:
            return CANONICAL_CONTAINERS[artifact_type]
        raise InvalidContainerError(name, artifact_type, aliases)

    # No type specified - search all aliases
    matched_type = CONTAINER_TO_TYPE.get(name_lower)
    if matched_type is not None:
        return CANONICAL_CONTAINERS[matched_type]

    # Not found in any type
    all_aliases: Set[str] = set()
    aliases_set: Set[str]
    for aliases_set in CONTAINER_ALIASES.values():
        all_aliases.update(aliases_set)
    # We need to pick a type for the error - use SKILL as default since it's most common
    raise InvalidContainerError(name, ArtifactType.SKILL, all_aliases)


def get_artifact_type_from_container(container_name: str) -> Optional[ArtifactType]:
    """Get artifact type from container directory name.

    Args:
        container_name: Container directory name (case-insensitive)

    Returns:
        ArtifactType if recognized, None otherwise

    Examples:
        >>> get_artifact_type_from_container("skills")
        <ArtifactType.SKILL: 'skill'>
        >>> get_artifact_type_from_container("subagents")
        <ArtifactType.AGENT: 'agent'>
        >>> get_artifact_type_from_container("unknown")
        None
    """
    return CONTAINER_TO_TYPE.get(container_name.lower())


def infer_artifact_type(path: Path | str) -> Optional[ArtifactType]:
    """Infer artifact type from filesystem path.

    Detection priority:
    1. Check for manifest files (SKILL.md, COMMAND.md, AGENT.md, etc.)
    2. Check parent directory name against container aliases
    3. Check file extension patterns

    Args:
        path: Path to artifact (file or directory)

    Returns:
        Inferred ArtifactType or None if cannot determine

    Examples:
        >>> infer_artifact_type(Path("./skills/my-skill"))  # Has SKILL.md
        <ArtifactType.SKILL: 'skill'>
        >>> infer_artifact_type(Path("./commands/do-thing.md"))
        <ArtifactType.COMMAND: 'command'>
        >>> infer_artifact_type(Path("./random/file.txt"))
        None
    """
    path = Path(path) if not isinstance(path, Path) else path

    # 1. Check for manifest files in directory
    if path.is_dir():
        for artifact_type, manifest_names in MANIFEST_FILES.items():
            for manifest in manifest_names:
                if (path / manifest).exists():
                    return artifact_type

    # 2. Check all ancestor directory names (handles any nesting depth)
    current = path.parent
    depth = 0
    max_ancestor_depth = 10  # Prevent infinite loops
    while current and current != current.parent and depth < max_ancestor_depth:
        ancestor_name = current.name.lower()
        if ancestor_name in CONTAINER_TO_TYPE:
            artifact_type = CONTAINER_TO_TYPE[ancestor_name]
            # For depth 0 (direct parent), always allow
            if depth == 0:
                return artifact_type
            # For deeper nesting, only allow if nesting is permitted for this type
            sig = ARTIFACT_SIGNATURES.get(artifact_type)
            if sig and sig.allowed_nesting:
                return artifact_type
            # For skills (not allowed_nesting), direct child only (depth 0)
            # So we don't return here for skills at depth > 0
        current = current.parent
        depth += 1

    # 3. Check if this looks like a command/agent based on file structure
    # Commands and agents are .md files that aren't manifest files
    if path.is_file() and path.suffix.lower() == ".md":
        # Check if parent matches any container type
        # Already handled above, so this would be ambiguous - return None
        pass

    return None


def extract_manifest_file(
    path: Path | str, artifact_type: ArtifactType
) -> Optional[Path]:
    """Find manifest file for artifact.

    Performs case-insensitive search for valid manifest files
    within the artifact directory.

    Args:
        path: Path to artifact directory or file
        artifact_type: Type to search manifest for

    Returns:
        Path to manifest file if found, None otherwise

    Examples:
        >>> extract_manifest_file(Path("./skills/my-skill"), ArtifactType.SKILL)
        PosixPath('./skills/my-skill/SKILL.md')
        >>> extract_manifest_file(Path("./commands/cmd.md"), ArtifactType.COMMAND)
        None  # Commands are files, not directories with manifests
    """
    path = Path(path) if not isinstance(path, Path) else path

    # Get the directory to search
    search_dir = path if path.is_dir() else path.parent

    # Get valid manifest names for this type
    manifest_names = MANIFEST_FILES.get(artifact_type, set())
    if not manifest_names:
        return None

    # Case-insensitive search
    manifest_names_lower = {m.lower() for m in manifest_names}

    try:
        for item in search_dir.iterdir():
            if item.is_file() and item.name.lower() in manifest_names_lower:
                return item
    except (OSError, PermissionError):
        # Directory might not exist or be inaccessible
        return None

    return None


def detect_artifact(
    path: Path | str,
    container_type: Optional[str] = None,
    mode: Literal["strict", "heuristic"] = "strict",
) -> DetectionResult:
    """Detect artifact type and build detection result.

    Main detection function that analyzes a path and returns
    comprehensive detection information including type, confidence,
    and reasoning.

    Args:
        path: Path to artifact (file or directory)
        container_type: Optional container name hint (e.g., "skills", "subagents")
        mode: Detection mode:
              - "strict": Requires high confidence (70+) or raises DetectionError
              - "heuristic": Returns best guess with confidence 0-100

    Returns:
        DetectionResult with all detection details

    Raises:
        DetectionError: In strict mode if artifact cannot be confidently detected

    Examples:
        >>> result = detect_artifact(Path("./skills/my-skill"))
        >>> result.artifact_type
        <ArtifactType.SKILL: 'skill'>
        >>> result.confidence
        100

        >>> result = detect_artifact(Path("./random/file"), mode="heuristic")
        >>> result.confidence  # Low confidence
        0
    """
    path = Path(path) if not isinstance(path, Path) else path
    reasons: List[str] = []
    confidence = 0
    artifact_type: Optional[ArtifactType] = None
    manifest_path: Optional[Path] = None

    # 1. Use container_type hint if provided
    if container_type:
        artifact_type = get_artifact_type_from_container(container_type)
        if artifact_type:
            reasons.append(
                f"Container type '{container_type}' maps to {artifact_type.value}"
            )
            confidence += 30

    # 2. Infer from path if not determined
    if not artifact_type:
        artifact_type = infer_artifact_type(path)
        if artifact_type:
            reasons.append(f"Inferred type '{artifact_type.value}' from path structure")
            confidence += 40

    # 3. Check for manifest file
    if artifact_type:
        manifest_path = extract_manifest_file(path, artifact_type)
        if manifest_path:
            reasons.append(f"Found manifest file: {manifest_path.name}")
            confidence += 40

    # 4. Check signature rules
    if artifact_type:
        sig = ARTIFACT_SIGNATURES.get(artifact_type)
        if sig:
            # Directory/file structure check
            path_exists = path.exists()
            if path_exists:
                if sig.is_directory == path.is_dir():
                    structure_type = "directory" if sig.is_directory else "file"
                    reasons.append(f"Structure matches: {structure_type}")
                    confidence += 20
                    # Bonus confidence for types that don't require manifests
                    # (they rely entirely on path/structure matching)
                    if not sig.requires_manifest:
                        confidence += 20
                        reasons.append(
                            f"Type '{artifact_type.value}' does not require manifest"
                        )
                else:
                    expected = "directory" if sig.is_directory else "file"
                    actual = "directory" if path.is_dir() else "file"
                    reasons.append(
                        f"Structure mismatch: expected {expected}, got {actual}"
                    )
                    confidence -= 20

            # Manifest requirement check
            if sig.requires_manifest and not manifest_path:
                reasons.append("Missing required manifest file")
                confidence -= 30

    # 5. Handle detection failure
    if not artifact_type:
        if mode == "strict":
            raise DetectionError(f"Cannot detect artifact type for path: {path}")
        confidence = 0
        artifact_type = ArtifactType.SKILL  # Default for heuristic mode
        reasons.append("Could not determine type, defaulting to skill")

    # 6. Strict mode: must meet confidence threshold or fail
    if mode == "strict":
        if confidence < 70:
            raise DetectionError(
                f"Strict detection failed for {path} (confidence={confidence}): "
                f"{', '.join(reasons)}"
            )
        confidence = 100  # Strict mode reports 100% when rules pass

    # 7. Clamp confidence to 0-100
    confidence = max(0, min(100, confidence))

    # 8. Determine container type for result
    result_container = container_type
    if not result_container and artifact_type:
        result_container = CANONICAL_CONTAINERS.get(artifact_type, "unknown")

    return DetectionResult(
        artifact_type=artifact_type,
        name=path.stem if path.is_file() else path.name,
        path=str(path),
        container_type=result_container or "unknown",
        detection_mode=mode,
        confidence=confidence,
        manifest_file=str(manifest_path) if manifest_path else None,
        detection_reasons=reasons,
    )
