"""Heuristic detector for Claude Code artifacts in GitHub repositories.

Uses multi-signal scoring to identify potential artifacts with confidence levels.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from skillmeat.api.schemas.marketplace import DetectedArtifact, HeuristicMatch

logger = logging.getLogger(__name__)

# Maximum raw score from all signals (10+20+5+15+15+25+30 = 120)
# dir_name(10) + manifest(20) + extensions(5) + parent_hint(15) + frontmatter(15)
# + container_hint(25) + frontmatter_type(30)
MAX_RAW_SCORE = 120

# Mapping from container directory names to artifact types
CONTAINER_TYPE_MAPPING: Dict[str, "ArtifactType"] = (
    {}
)  # Populated after ArtifactType is defined


def normalize_score(raw_score: int) -> int:
    """Normalize raw score to 0-100 scale.

    Args:
        raw_score: Raw score from signal accumulation

    Returns:
        Normalized score clamped between 0 and 100

    Examples:
        >>> normalize_score(65)
        100
        >>> normalize_score(30)
        46
        >>> normalize_score(0)
        0
    """
    if raw_score <= 0:
        return 0
    if raw_score >= MAX_RAW_SCORE:
        return 100
    return round((raw_score / MAX_RAW_SCORE) * 100)


class ArtifactType(str, Enum):
    """Supported artifact types."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    MCP_SERVER = "mcp_server"
    HOOK = "hook"


# Populate the container type mapping after ArtifactType is defined
# Only plural forms are containers; singular forms can be artifact names
CONTAINER_TYPE_MAPPING.update(
    {
        "commands": ArtifactType.COMMAND,
        "agents": ArtifactType.AGENT,
        "skills": ArtifactType.SKILL,
        "hooks": ArtifactType.HOOK,
        "mcp": ArtifactType.MCP_SERVER,
        "mcp-servers": ArtifactType.MCP_SERVER,
        "servers": ArtifactType.MCP_SERVER,
    }
)


@dataclass
class DetectionConfig:
    """Configuration for artifact detection heuristics."""

    # Directory name patterns for each artifact type
    dir_patterns: Dict[ArtifactType, Set[str]] = field(
        default_factory=lambda: {
            ArtifactType.SKILL: {"skills", "skill", "claude-skills"},
            ArtifactType.COMMAND: {"commands", "command", "claude-commands"},
            ArtifactType.AGENT: {"agents", "agent", "claude-agents"},
            ArtifactType.MCP_SERVER: {"mcp", "mcp-servers", "servers"},
            ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
        }
    )

    # Manifest filenames for each artifact type
    manifest_files: Dict[ArtifactType, Set[str]] = field(
        default_factory=lambda: {
            ArtifactType.SKILL: {"SKILL.md", "skill.md"},
            ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
            ArtifactType.AGENT: {"AGENT.md", "agent.md"},
            ArtifactType.MCP_SERVER: {"MCP.md", "mcp.md", "server.json"},
            ArtifactType.HOOK: {"HOOK.md", "hook.md", "hooks.json"},
        }
    )

    # Expected file extensions for artifacts
    expected_extensions: Set[str] = field(
        default_factory=lambda: {".md", ".py", ".ts", ".js", ".json", ".yaml", ".yml"}
    )

    # Minimum confidence threshold for detection
    min_confidence: int = 30

    # Maximum directory depth to scan
    max_depth: int = 10

    # Base depth penalty per level
    depth_penalty: int = 1

    # Score weights for each signal
    dir_name_weight: int = 10
    manifest_weight: int = 20
    extension_weight: int = 5
    parent_hint_weight: int = 15
    frontmatter_weight: int = 15
    container_hint_weight: int = 25  # Bonus when detected type matches container hint
    frontmatter_type_weight: int = (
        30  # Strong signal when frontmatter contains type field
    )


class HeuristicDetector:
    """Detects Claude Code artifacts using multi-signal scoring heuristics.

    Example:
        >>> detector = HeuristicDetector()
        >>> matches = detector.analyze_paths(file_paths, base_url="https://github.com/user/repo")
        >>> for match in matches:
        ...     if match.confidence_score >= 50:
        ...         print(f"Found {match.artifact_type}: {match.path} ({match.confidence_score}%)")
    """

    def __init__(
        self,
        config: Optional[DetectionConfig] = None,
        enable_frontmatter_detection: bool = False,
        manual_mappings: Optional[Dict[str, str]] = None,
    ):
        """Initialize detector with optional custom configuration.

        Args:
            config: Optional custom detection configuration
            enable_frontmatter_detection: Enable frontmatter parsing for type detection
            manual_mappings: Optional directory-to-artifact-type mappings for manual
                override. Format: {"path/to/dir": "skill", "another/path": "command"}.
                Valid artifact types: "skill", "command", "agent", "mcp_server", "hook".
                When provided, directories matching these paths (or inheriting from them)
                will use the specified artifact type, bypassing heuristic detection.
                Confidence scores vary by inheritance depth: exact match=95, depth=1=92,
                depth=2=89, depth=3+=86 (minimum). This ensures manual mappings always
                beat heuristic detection (max ~80) while still reflecting match quality.
        """
        self.config = config or DetectionConfig()
        self.enable_frontmatter_detection = enable_frontmatter_detection
        self.manual_mappings = manual_mappings or {}

        # Normalize manual mappings: strip trailing slashes, use forward slashes
        self._normalized_mappings: Dict[str, ArtifactType] = {}
        for path, type_str in self.manual_mappings.items():
            normalized_path = path.rstrip("/").replace("\\", "/")
            artifact_type = self._string_to_artifact_type(type_str)
            if artifact_type:
                self._normalized_mappings[normalized_path] = artifact_type
            else:
                logger.warning(
                    "Invalid artifact type '%s' in manual mapping for path '%s'",
                    type_str,
                    path,
                )

        if self.manual_mappings:
            logger.debug(
                "HeuristicDetector initialized with %d manual mapping(s): %s",
                len(self.manual_mappings),
                list(self.manual_mappings.keys()),
            )

    def _string_to_artifact_type(self, type_str: str) -> Optional[ArtifactType]:
        """Convert string to ArtifactType enum.

        Args:
            type_str: String representation of artifact type (case-insensitive)

        Returns:
            ArtifactType enum value or None if invalid

        Examples:
            >>> detector._string_to_artifact_type("skill")
            ArtifactType.SKILL
            >>> detector._string_to_artifact_type("mcp_server")
            ArtifactType.MCP_SERVER
            >>> detector._string_to_artifact_type("invalid")
            None
        """
        type_mapping = {
            "skill": ArtifactType.SKILL,
            "command": ArtifactType.COMMAND,
            "agent": ArtifactType.AGENT,
            "mcp_server": ArtifactType.MCP_SERVER,
            "mcp-server": ArtifactType.MCP_SERVER,
            "hook": ArtifactType.HOOK,
        }
        return type_mapping.get(type_str.lower().strip())

    def _check_manual_mapping(
        self, dir_path: str
    ) -> Optional[Tuple[ArtifactType, str, int]]:
        """Check if a directory path matches any manual mapping with hierarchical inheritance.

        Supports hierarchical matching with inheritance depth tracking:
        1. Exact match: path exactly equals a mapping key (depth 0)
        2. Parent match: path's parent matches a mapping key (depth 1)
        3. Grandparent match: path's grandparent matches (depth 2)
        4. And so on up the hierarchy...

        The MOST SPECIFIC (longest) matching path is returned. For example, if both
        "skills" and "skills/canvas" are mapped, path "skills/canvas/nested" will
        match "skills/canvas" (depth 1), not "skills" (depth 2).

        Matching is case-sensitive and uses forward slashes for paths.

        Args:
            dir_path: Directory path to check (e.g., "skills/my-skill/nested")

        Returns:
            Tuple of (ArtifactType, match_type, inheritance_depth) if matched:
            - match_type: "exact" or "inherited"
            - inheritance_depth: 0 for exact match, 1+ for parent/ancestor matches
            Returns None if no match.

        Examples:
            With mappings {"skills": "skill", "skills/canvas": "command"}:
            >>> detector._check_manual_mapping("skills")
            (ArtifactType.SKILL, "exact", 0)
            >>> detector._check_manual_mapping("skills/canvas")
            (ArtifactType.COMMAND, "exact", 0)
            >>> detector._check_manual_mapping("skills/canvas/nested")
            (ArtifactType.COMMAND, "inherited", 1)
            >>> detector._check_manual_mapping("skills/canvas/nested/deep")
            (ArtifactType.COMMAND, "inherited", 2)
            >>> detector._check_manual_mapping("skills/other")
            (ArtifactType.SKILL, "inherited", 1)
            >>> detector._check_manual_mapping("skills/other/nested")
            (ArtifactType.SKILL, "inherited", 2)
            >>> detector._check_manual_mapping("my-skills")
            None
            >>> detector._check_manual_mapping("skillset")
            None
            >>> detector._check_manual_mapping("other/skills")
            None
        """
        if not self._normalized_mappings:
            return None

        # Normalize input path
        normalized_path = dir_path.rstrip("/").replace("\\", "/")

        # Check for exact match first (highest priority, depth 0)
        if normalized_path in self._normalized_mappings:
            return (self._normalized_mappings[normalized_path], "exact", 0)

        # Walk up the path hierarchy to find the most specific (longest) parent match
        # Split path into parts and progressively check shorter prefixes
        path_parts = normalized_path.split("/")

        # Start from immediate parent (len - 1) down to root (1 part)
        # This ensures we find the MOST SPECIFIC match first
        for depth in range(1, len(path_parts)):
            # Build ancestor path by taking all parts except the last 'depth' parts
            ancestor_parts = path_parts[: len(path_parts) - depth]
            ancestor_path = "/".join(ancestor_parts)

            if ancestor_path in self._normalized_mappings:
                return (
                    self._normalized_mappings[ancestor_path],
                    "inherited",
                    depth,
                )

        return None

    def _is_plugin_directory(
        self, dir_path: str, dir_to_files: Dict[str, Set[str]]
    ) -> bool:
        """Detect if a directory is a plugin (contains multiple entity-type subdirectories).

        A plugin is a directory that contains 2 or more entity-type subdirectories
        (commands/, agents/, skills/, hooks/, rules/, mcp/). This indicates the
        directory is a collection of related artifacts rather than a single entity.

        Example plugin structure::

            my-plugin/
            ├── commands/      <- entity-type directory
            │   └── deploy/
            └── agents/        <- entity-type directory
                └── helper/

        Args:
            dir_path: Path to check (e.g., "my-plugin")
            dir_to_files: Map of all directories to their files

        Returns:
            True if directory contains 2+ entity-type subdirectories
        """
        entity_type_names = {"commands", "agents", "skills", "hooks", "rules", "mcp"}

        child_dirs: set[str] = set()
        for path in dir_to_files.keys():
            if path.startswith(dir_path + "/"):
                relative = path[len(dir_path) + 1 :]
                first_part = relative.split("/")[0].lower()
                if first_part in entity_type_names:
                    child_dirs.add(first_part)

        return len(child_dirs) >= 2

    def _get_container_type(
        self, dir_path: str, dir_to_files: Dict[str, Set[str]]  # noqa: ARG002
    ) -> Optional[ArtifactType]:
        """Get the artifact type implied by a container directory name.

        Entity-type directories (commands/, agents/, skills/, hooks/, rules/, mcp/)
        are organizational containers that hold multiple entities. They should not
        be detected as artifacts themselves, but their type should be propagated
        to child directories.

        Example::

            skills/          <- container (type=SKILL, should be skipped)
            ├── my-skill/    <- actual entity (inherits type hint from parent)
            └── other-skill/ <- actual entity (inherits type hint from parent)

        Args:
            dir_path: Path to check (e.g., "plugin/commands")
            dir_to_files: Map of all directories to their files (reserved for future use)

        Returns:
            ArtifactType if directory is a container, None otherwise
        """
        # dir_to_files kept for API consistency with _is_plugin_directory
        posix_path = PurePosixPath(dir_path)
        dir_name = posix_path.name.lower()

        # Return the artifact type for this container, or None if not a container
        return CONTAINER_TYPE_MAPPING.get(dir_name)

    def _is_container_directory(
        self, dir_path: str, dir_to_files: Dict[str, Set[str]]
    ) -> bool:
        """Detect if a directory is an entity-type container (not an entity itself).

        This is a convenience wrapper around _get_container_type for backward compatibility.

        Args:
            dir_path: Path to check (e.g., "plugin/commands")
            dir_to_files: Map of all directories to their files

        Returns:
            True if directory is a container (e.g., "commands/", "skills/")
        """
        return self._get_container_type(dir_path, dir_to_files) is not None

    def _compute_organization_path(
        self, artifact_path: str, container_dir: Optional[str]
    ) -> Optional[str]:
        """Extract path segments between container and artifact.

        Computes the organizational path that exists between a container directory
        (like "commands/", "skills/") and the actual artifact directory. This helps
        track how artifacts are organized within containers.

        Args:
            artifact_path: Full path to the artifact (e.g., "commands/dev/execute-phase")
            container_dir: Path to the container directory (e.g., "commands"), or None

        Returns:
            Path segments between container and artifact, or None if:
            - No container directory
            - Artifact is directly in container (no intermediate path)

        Examples:
            >>> detector._compute_organization_path("commands/dev/execute-phase", "commands")
            'dev'
            >>> detector._compute_organization_path("commands/test", "commands")
            None  # Directly in container
            >>> detector._compute_organization_path("commands/dev/subgroup/my-cmd", "commands")
            'dev/subgroup'
            >>> detector._compute_organization_path("agents/ui-ux/ui-designer", "agents")
            'ui-ux'
            >>> detector._compute_organization_path("skills/planning", "skills")
            None  # planning IS the artifact, directly in container
            >>> detector._compute_organization_path("standalone/my-skill", None)
            None  # No container
        """
        if container_dir is None:
            return None

        # Ensure artifact_path starts with container_dir
        if not artifact_path.startswith(container_dir + "/"):
            return None

        # Get the path relative to container
        # e.g., "commands/dev/execute-phase" -> "dev/execute-phase"
        relative_path = artifact_path[len(container_dir) + 1 :]

        # Split into parts
        parts = relative_path.split("/")

        # If only one part, artifact is directly in container (no intermediate path)
        if len(parts) <= 1:
            return None

        # The last part is the artifact name, everything before is organization
        # e.g., ["dev", "execute-phase"] -> "dev"
        # e.g., ["dev", "subgroup", "my-cmd"] -> "dev/subgroup"
        organization_parts = parts[:-1]

        return "/".join(organization_parts) if organization_parts else None

    def _detect_single_file_artifacts(
        self,
        dir_to_files: Dict[str, Set[str]],
        container_types: Dict[str, ArtifactType],
        root_hint: Optional[str],
    ) -> List[HeuristicMatch]:
        """Detect single-file artifacts (.md files) directly in or nested under containers.

        Claude Code conventions:
        - Skills: Always directory-based (SKILL.md + supporting files)
        - Commands: Often single .md file (the command prompt itself)
        - Agents: Often single .md file (the agent definition)

        Args:
            dir_to_files: Mapping of directories to their files
            container_types: Mapping of container paths to their artifact types
            root_hint: Optional path filter

        Returns:
            List of HeuristicMatch for detected single-file artifacts
        """
        matches: List[HeuristicMatch] = []

        # Build effective container types including manual mappings
        # This allows .md files under manually-mapped directories to be detected
        effective_container_types = dict(container_types)

        # Add manual mappings as additional container types (for non-Skill types)
        for mapped_path, mapped_type in self._normalized_mappings.items():
            if mapped_type != ArtifactType.SKILL:
                effective_container_types[mapped_path] = mapped_type
                logger.debug(
                    "Added manual mapping '%s' -> '%s' to effective container types "
                    "for single-file detection",
                    mapped_path,
                    mapped_type.value,
                )

        # Skip files to exclude from single-file detection
        excluded_files = {
            "readme.md",
            "changelog.md",
            "license.md",
            "contributing.md",
            "skill.md",
            "command.md",
            "agent.md",
            "mcp.md",
            "hook.md",  # manifest files
        }

        # Bug Fix 1: Identify artifact directories (directories with manifest files)
        # Files inside these directories should NOT be detected as single-file artifacts
        manifest_files = {"skill.md", "command.md", "agent.md", "hook.md", "mcp.md"}
        artifact_dirs: Set[str] = set()
        for dir_path, files in dir_to_files.items():
            if any(f.lower() in manifest_files for f in files):
                artifact_dirs.add(dir_path)

        # Process all directories to find single-file artifacts
        for dir_path, files in dir_to_files.items():
            # Apply root hint filtering
            if root_hint and not dir_path.startswith(root_hint):
                continue

            # Bug Fix 1: Skip if this directory is INSIDE an artifact directory
            # (unless it's a nested container like skills/my-skill/commands/)
            is_inside_artifact = False
            for artifact_dir in artifact_dirs:
                if dir_path.startswith(artifact_dir + "/"):
                    # Check if there's a container directory between artifact and this path
                    relative = dir_path[len(artifact_dir) + 1 :]
                    first_segment = relative.split("/")[0].lower()
                    if first_segment not in CONTAINER_TYPE_MAPPING:
                        is_inside_artifact = True
                        break

            if is_inside_artifact:
                continue  # Skip - this is a file inside an artifact, not a standalone

            # Find container context for this directory
            # Use effective_container_types which includes manual mappings
            container_type: Optional[ArtifactType] = None
            container_dir: Optional[str] = None
            is_manual_mapping = False

            # Check if this IS a container (or manual mapping)
            if dir_path in effective_container_types:
                container_type = effective_container_types[dir_path]
                container_dir = dir_path
                is_manual_mapping = dir_path in self._normalized_mappings
            else:
                # Check if inside a container (or manual mapping)
                # Find the most specific (longest) matching container
                best_match_path: Optional[str] = None
                best_match_type: Optional[ArtifactType] = None
                for c_path, c_type in effective_container_types.items():
                    if dir_path.startswith(c_path + "/"):
                        if best_match_path is None or len(c_path) > len(best_match_path):
                            best_match_path = c_path
                            best_match_type = c_type

                if best_match_path is not None:
                    container_type = best_match_type
                    container_dir = best_match_path
                    is_manual_mapping = best_match_path in self._normalized_mappings

            if container_type is None:
                continue  # Not in a container context

            # Skills cannot be single-file artifacts - they must be directories with SKILL.md
            # See Claude Code conventions (lines 297-299): Skills are ALWAYS directory-based
            if container_type == ArtifactType.SKILL:
                continue

            # Check if directory has a manifest file (then it's directory-based, skip)
            has_manifest = any(
                f.lower() in {"skill.md", "command.md", "agent.md", "mcp.md", "hook.md"}
                for f in files
            )
            if has_manifest:
                continue  # Will be handled by directory-based detection

            # Detect single-file artifacts
            for filename in files:
                if not filename.lower().endswith(".md"):
                    continue
                if filename.lower() in excluded_files:
                    continue

                artifact_path = f"{dir_path}/{filename}"

                # Compute organization path for single-file artifact
                # For single files, the artifact IS the file, not the directory
                # So organization path is the path from container to the file's parent directory
                if dir_path == container_dir:
                    organization_path = None  # Directly in container
                else:
                    # For single-file: commands/git/cm.md
                    # container_dir = "commands", dir_path = "commands/git"
                    # organization_path should be "git"
                    # container_dir is guaranteed non-None here (checked above)
                    relative_path = dir_path[len(container_dir) + 1 :]  # type: ignore[arg-type]
                    organization_path = relative_path if relative_path else None

                # Bug Fix 2: Apply depth penalty to single-file confidence
                # Calculate depth relative to container
                depth = len(PurePosixPath(dir_path).parts)
                container_depth = (
                    len(PurePosixPath(container_dir).parts) if container_dir else 0
                )
                relative_depth = depth - container_depth

                # Base confidence for single-file artifacts
                # Manual mappings get higher confidence (consistent with directory-based manual mappings)
                if is_manual_mapping:
                    # Manual mapping confidence: same formula as directory-based
                    # depth=0: 95, depth=1: 92, depth=2: 89, depth=3+: 86
                    confidence = max(86, 95 - (relative_depth * 3))
                else:
                    # Heuristic-based confidence
                    # Direct in container gets higher score, deeper gets penalty
                    if relative_depth == 0:
                        confidence = 75  # Directly in container
                    elif relative_depth == 1:
                        confidence = 70  # One level deep (e.g., commands/git/cm.md)
                    else:
                        # Each additional level reduces confidence
                        depth_penalty = (relative_depth - 1) * 5
                        confidence = max(50, 70 - depth_penalty)

                # Calculate depth penalty for breakdown
                single_file_depth_penalty = (
                    max(0, (relative_depth - 1) * 5) if relative_depth > 1 else 0
                )

                match_reasons = [
                    f"Single-file {container_type.value} in container",
                    f"Container: {container_dir}/",
                    f"File: {filename}",
                ]
                if is_manual_mapping:
                    match_reasons.insert(0, f"Manual mapping (depth={relative_depth})")
                if single_file_depth_penalty > 0 and not is_manual_mapping:
                    match_reasons.append(
                        f"Depth penalty (-{single_file_depth_penalty})"
                    )

                # Build breakdown dict
                breakdown_dict: Dict[str, Any] = {
                    "dir_name_score": 0,
                    "manifest_score": 0,
                    "extensions_score": 5,
                    "parent_hint_score": 0,
                    "frontmatter_score": 0,
                    "container_hint_score": self.config.container_hint_weight,
                    "depth_penalty": single_file_depth_penalty if not is_manual_mapping else 0,
                    "raw_total": self.config.container_hint_weight + 5,
                    "normalized_score": confidence,
                    "single_file_detection": True,
                }

                # Add manual mapping metadata if applicable
                metadata: Optional[Dict[str, Any]] = None
                if is_manual_mapping:
                    metadata = {
                        "is_manual_mapping": True,
                        "match_type": "inherited" if relative_depth > 0 else "exact",
                        "inheritance_depth": relative_depth,
                        "confidence_reason": (
                            f"Manual mapping single-file (depth={relative_depth}, "
                            f"score={confidence})"
                        ),
                    }

                match = HeuristicMatch(
                    path=artifact_path,
                    artifact_type=container_type.value,
                    confidence_score=confidence,
                    organization_path=organization_path,
                    match_reasons=match_reasons,
                    # Score breakdown for single-file artifacts
                    dir_name_score=0,
                    manifest_score=0,
                    extension_score=5,  # .md extension
                    depth_penalty=single_file_depth_penalty if not is_manual_mapping else 0,
                    raw_score=self.config.container_hint_weight + 5,
                    breakdown=breakdown_dict,
                    metadata=metadata,
                )
                matches.append(match)

        return matches

    def _is_single_file_grouping_directory(
        self,
        dir_path: str,
        files: Set[str],
        container_types: Dict[str, ArtifactType],
    ) -> bool:
        """Check if a directory is a grouping directory for single-file artifacts.

        A grouping directory is a non-container directory inside a typed container
        that contains only .md files (single-file artifacts) and no manifest files.
        Example: commands/git/ containing cm.md, cp.md, pr.md

        These directories should not be detected as directory-based artifacts
        because their contents are already detected as single-file artifacts.

        Args:
            dir_path: Path to check
            files: Set of filenames in this directory
            container_types: Mapping of container paths to artifact types

        Returns:
            True if this is a grouping directory for single-file artifacts
        """
        # Check if this directory is inside a container
        is_inside_container = False
        for c_path in container_types:
            if dir_path.startswith(c_path + "/"):
                is_inside_container = True
                break

        if not is_inside_container:
            return False

        # Check if it has any manifest files
        manifest_files = {"skill.md", "command.md", "agent.md", "mcp.md", "hook.md"}
        has_manifest = any(f.lower() in manifest_files for f in files)
        if has_manifest:
            return False  # Has manifest, treat as directory-based

        # Check if all files (except excluded) are .md files
        excluded_files = {"readme.md", "changelog.md", "license.md", "contributing.md"}

        artifact_md_files = [
            f
            for f in files
            if f.lower().endswith(".md") and f.lower() not in excluded_files
        ]

        # If there are .md files that would be detected as single-file artifacts,
        # and no other significant files, this is a grouping directory
        if artifact_md_files:
            # Check if there are any non-.md files (except common non-artifact files)
            other_files = [f for f in files if not f.lower().endswith(".md")]
            # If only .md files (or common non-artifact files), it's a grouping dir
            if not other_files:
                return True

        return False

    def analyze_paths(
        self,
        paths: List[str],
        base_url: str,
        root_hint: Optional[str] = None,
        enable_frontmatter_detection: Optional[bool] = None,
    ) -> List[HeuristicMatch]:
        """Analyze a list of file paths and return heuristic matches.

        Args:
            paths: List of file paths relative to repository root
            base_url: Base URL for the repository (for upstream_url generation)
            root_hint: Optional subdirectory to focus scanning on
            enable_frontmatter_detection: Override instance-level frontmatter detection

        Returns:
            List of HeuristicMatch objects sorted by confidence (highest first)
        """
        use_frontmatter = (
            enable_frontmatter_detection
            if enable_frontmatter_detection is not None
            else self.enable_frontmatter_detection
        )
        # Group files by parent directory to identify potential artifact folders
        dir_to_files: Dict[str, Set[str]] = {}
        for path in paths:
            posix_path = PurePosixPath(path)
            parent = str(posix_path.parent)
            filename = posix_path.name

            if parent not in dir_to_files:
                dir_to_files[parent] = set()
            dir_to_files[parent].add(filename)

        # Build a mapping of container directories to their artifact types
        # This allows us to propagate type hints to child directories
        # We need to check all ancestor paths, not just directories with files
        container_types: Dict[str, ArtifactType] = {}
        for dir_path in dir_to_files.keys():
            # Check this directory
            container_type = self._get_container_type(dir_path, dir_to_files)
            if container_type is not None:
                container_types[dir_path] = container_type

            # Also check all ancestor directories in this path
            # This handles cases like plugin/commands/cmd where plugin/commands
            # has no files directly but is still a container
            posix_path = PurePosixPath(dir_path)
            for i in range(1, len(posix_path.parts)):
                ancestor = str(PurePosixPath(*posix_path.parts[:i]))
                if ancestor not in container_types:
                    ancestor_container_type = self._get_container_type(
                        ancestor, dir_to_files
                    )
                    if ancestor_container_type is not None:
                        container_types[ancestor] = ancestor_container_type

        matches: List[HeuristicMatch] = []

        # Detect single-file artifacts inside containers
        single_file_matches = self._detect_single_file_artifacts(
            dir_to_files, container_types, root_hint
        )
        matches.extend(single_file_matches)

        # Analyze each directory
        for dir_path, files in dir_to_files.items():
            # Skip root directory
            if dir_path == ".":
                continue

            # Skip if container directory (containers themselves are not artifacts)
            if self._is_container_directory(dir_path, dir_to_files):
                continue

            # Skip if this is a "grouping directory" for single-file artifacts
            # A grouping directory has no manifest but contains only .md files
            # inside a typed container (e.g., commands/git/ with cm.md, cp.md)
            if self._is_single_file_grouping_directory(
                dir_path, files, container_types
            ):
                continue

            # Skip if too deep
            depth = len(PurePosixPath(dir_path).parts)
            if depth > self.config.max_depth:
                continue

            # Apply root hint filtering if provided
            if root_hint:
                # Only consider paths under root_hint
                if not dir_path.startswith(root_hint):
                    continue

            # Determine container hint from parent directory
            # Check if any ancestor is a container directory
            container_hint: Optional[ArtifactType] = None
            container_dir: Optional[str] = (
                None  # Track the container path for organization_path
            )
            posix_path = PurePosixPath(dir_path)
            for i in range(len(posix_path.parts) - 1, 0, -1):
                # Build ancestor path
                ancestor = str(PurePosixPath(*posix_path.parts[:i]))
                if ancestor in container_types:
                    container_hint = container_types[ancestor]
                    container_dir = ancestor
                    break

            # Check for manual mapping override FIRST
            manual_mapping_result = self._check_manual_mapping(dir_path)
            manual_mapping_info: Optional[Dict[str, Any]] = None
            if manual_mapping_result is not None:
                mapped_type, match_type, inheritance_depth = manual_mapping_result

                # Check if directory has a SKILL.md manifest
                has_skill_manifest = any(f.lower() == "skill.md" for f in files)

                # For non-Skill types with manual mapping, directories themselves are NOT artifacts
                # Only Skills are directory-based; all other types are single .md files
                # The directory mapping indicates that .md files INSIDE should inherit the type
                if mapped_type != ArtifactType.SKILL:
                    if not has_skill_manifest:
                        logger.debug(
                            "Skipping directory %s as artifact: non-Skill type '%s' "
                            "requires single .md files, not directories",
                            dir_path,
                            mapped_type.value,
                        )
                        continue  # Skip - this directory is not a valid artifact
                else:
                    # For Skill types, SKILL.md is required for directory to be an artifact
                    if not has_skill_manifest:
                        logger.debug(
                            "Skipping directory %s as artifact: Skill type requires "
                            "SKILL.md manifest",
                            dir_path,
                        )
                        continue  # Skip - no manifest means not a valid skill

                # Manual mapping overrides heuristic detection
                artifact_type = mapped_type

                # Calculate confidence based on match type and inheritance depth
                # Formula: confidence = max(86, 95 - (inheritance_depth * 3))
                # - Exact match (depth=0): 95
                # - Inherited depth=1: 92
                # - Inherited depth=2: 89
                # - Inherited depth=3+: 86 (minimum for manual mapping)
                confidence_score = max(86, 95 - (inheritance_depth * 3))

                # Build confidence reason for transparency
                if match_type == "exact":
                    confidence_reason = "Manual mapping exact match (95)"
                else:
                    confidence_reason = (
                        f"Manual mapping inherited from ancestor "
                        f"(depth={inheritance_depth}, score={confidence_score})"
                    )

                raw_score = MAX_RAW_SCORE  # Max raw score for manual mappings
                match_reasons = [
                    f"Manual mapping ({match_type} match, depth={inheritance_depth}): "
                    f"{mapped_type.value}",
                    confidence_reason,
                ]
                score_breakdown = {
                    "dir_name_score": 0,
                    "manifest_score": 0,
                    "extensions_score": 0,
                    "parent_hint_score": 0,
                    "frontmatter_score": 0,
                    "container_hint_score": 0,
                    "depth_penalty": 0,
                    "raw_total": raw_score,
                }
                # Store manual mapping info separately (not in breakdown which requires int values)
                manual_mapping_info = {
                    "is_manual_mapping": True,
                    "match_type": match_type,
                    "inheritance_depth": inheritance_depth,
                    "confidence_reason": confidence_reason,
                }
                logger.debug(
                    "Manual mapping applied to %s: type=%s, match=%s, depth=%d, confidence=%d",
                    dir_path,
                    mapped_type.value,
                    match_type,
                    inheritance_depth,
                    confidence_score,
                )
            else:
                # No manual mapping - use heuristic detection
                # Detect artifact type and score
                artifact_type, match_reasons, score_breakdown = self._score_directory(
                    dir_path, files, root_hint, use_frontmatter, container_hint
                )

                # Normalize raw score to 0-100 scale
                raw_score = score_breakdown["raw_total"]
                confidence_score = normalize_score(raw_score)

            # Bug Fix 3: Validate flat structure for commands/hooks/agents
            # These artifact types should be flat - nested subdirs reduce confidence
            if artifact_type in (
                ArtifactType.COMMAND,
                ArtifactType.HOOK,
                ArtifactType.AGENT,
            ):
                allowed_nested = {"tests", "test", "__tests__", "lib", "dist", "build"}
                for other_dir in dir_to_files.keys():
                    if other_dir.startswith(dir_path + "/"):
                        # This is a nested directory
                        nested_name = (
                            other_dir[len(dir_path) + 1 :].split("/")[0].lower()
                        )
                        if nested_name not in allowed_nested:
                            # Apply penalty - this might not be a valid flat artifact
                            confidence_score = max(
                                self.config.min_confidence, confidence_score - 15
                            )
                            match_reasons.append(
                                f"Unexpected nested directory: {nested_name} (-15)"
                            )
                            break

            # Only include if above threshold
            if confidence_score >= self.config.min_confidence:
                # Build complete breakdown dict with all signals and normalized score
                complete_breakdown = {
                    "dir_name_score": score_breakdown["dir_name_score"],
                    "manifest_score": score_breakdown["manifest_score"],
                    "extensions_score": score_breakdown["extensions_score"],
                    "parent_hint_score": score_breakdown["parent_hint_score"],
                    "frontmatter_score": score_breakdown["frontmatter_score"],
                    "container_hint_score": score_breakdown["container_hint_score"],
                    "depth_penalty": score_breakdown["depth_penalty"],
                    "raw_total": raw_score,
                    "normalized_score": confidence_score,
                }

                # Compute organization path between container and artifact
                organization_path = self._compute_organization_path(
                    dir_path, container_dir
                )

                match = HeuristicMatch(
                    path=dir_path,
                    artifact_type=artifact_type.value if artifact_type else None,
                    confidence_score=confidence_score,
                    organization_path=organization_path,
                    match_reasons=match_reasons,
                    dir_name_score=complete_breakdown["dir_name_score"],
                    manifest_score=complete_breakdown["manifest_score"],
                    extension_score=complete_breakdown["extensions_score"],
                    depth_penalty=complete_breakdown["depth_penalty"],
                    raw_score=raw_score,
                    breakdown=complete_breakdown,
                    metadata=manual_mapping_info,  # None if not manually mapped
                )
                matches.append(match)

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence_score, reverse=True)

        return matches

    def detect_artifact_type(self, path: str) -> Tuple[Optional[ArtifactType], int]:
        """Detect artifact type and score for a single path.

        Args:
            path: Path to analyze

        Returns:
            Tuple of (artifact_type, confidence_score)
        """
        # For single path, create a minimal analysis
        artifact_type, _, score_breakdown = self._score_directory(path, set(), None)
        raw_score = score_breakdown["raw_total"]
        confidence_score = normalize_score(raw_score)
        return artifact_type, confidence_score

    def _score_directory(
        self,
        path: str,
        siblings: Set[str],
        root_hint: Optional[str] = None,
        use_frontmatter: bool = False,
        container_hint: Optional[ArtifactType] = None,
    ) -> Tuple[Optional[ArtifactType], List[str], Dict[str, int]]:
        """Score a directory based on all available signals.

        Args:
            path: Directory path to score
            siblings: Set of filenames in this directory
            root_hint: Optional root hint for parent matching
            use_frontmatter: Enable frontmatter detection boost
            container_hint: Optional artifact type hint from parent container directory

        Returns:
            Tuple of (artifact_type, match_reasons, score_breakdown)
            where score_breakdown contains individual signal scores and raw_total
        """
        total_score = 0
        match_reasons: List[str] = []
        artifact_type: Optional[ArtifactType] = None

        # Score breakdown for debugging and transparency
        breakdown = {
            "dir_name_score": 0,
            "manifest_score": 0,
            "extensions_score": 0,
            "parent_hint_score": 0,
            "frontmatter_score": 0,
            "container_hint_score": 0,
            "depth_penalty": 0,
            "raw_total": 0,
        }

        # Signal 1: Directory name matching
        dir_name_type, dir_name_score = self._score_dir_name(path)
        if dir_name_type:
            total_score += dir_name_score
            breakdown["dir_name_score"] = dir_name_score
            artifact_type = dir_name_type
            match_reasons.append(
                f"Directory name matches {dir_name_type.value} pattern (+{dir_name_score})"
            )

        # Signal 2: Manifest presence
        manifest_type, manifest_score = self._score_manifest(path, siblings)
        if manifest_type:
            total_score += manifest_score
            breakdown["manifest_score"] = manifest_score
            # Manifest is stronger signal - override artifact_type if different
            if artifact_type and artifact_type != manifest_type:
                # Conflicting signals - use manifest as authoritative
                artifact_type = manifest_type
                match_reasons.append(
                    f"Manifest overrides type to {manifest_type.value} (+{manifest_score})"
                )
            else:
                artifact_type = manifest_type
                match_reasons.append(f"Contains manifest file (+{manifest_score})")

        # Signal 3: File extensions
        extension_score = self._score_extensions(path, siblings)
        if extension_score > 0:
            total_score += extension_score
            breakdown["extensions_score"] = extension_score
            match_reasons.append(
                f"Contains expected file extensions (+{extension_score})"
            )

        # Signal 4: Parent hint bonus
        parent_hint_score = self._score_parent_hint(path, artifact_type)
        if parent_hint_score > 0:
            total_score += parent_hint_score
            breakdown["parent_hint_score"] = parent_hint_score
            match_reasons.append(f"Parent directory hint bonus (+{parent_hint_score})")

        # Signal 5: Frontmatter detection (if enabled)
        if use_frontmatter:
            # Look for .md files that might contain frontmatter
            md_files = [f for f in siblings if f.endswith(".md")]
            for md_file in md_files:
                # NOTE: We can only boost confidence here since we don't have file contents
                # Full frontmatter parsing would require fetching file content
                # For now, presence of README.md or SKILL.md boosts confidence when frontmatter is enabled
                if md_file.lower() in (
                    "readme.md",
                    "skill.md",
                    "command.md",
                    "agent.md",
                ):
                    total_score += self.config.frontmatter_weight
                    breakdown["frontmatter_score"] = self.config.frontmatter_weight
                    match_reasons.append(f"frontmatter_candidate:{md_file}")
                    break

        # Signal 6: Container hint bonus
        # If this directory is inside a container (e.g., skills/my-skill inside skills/)
        # and the detected type matches the container type, add a bonus
        if container_hint is not None and artifact_type is not None:
            if artifact_type == container_hint:
                total_score += self.config.container_hint_weight
                breakdown["container_hint_score"] = self.config.container_hint_weight
                match_reasons.append(
                    f"Type matches container hint ({container_hint.value}) "
                    f"(+{self.config.container_hint_weight})"
                )
        elif container_hint is not None and artifact_type is None:
            # If no type detected yet but we have a container hint, use it as weak signal
            # This helps detect artifacts that only have file extensions but are inside
            # a typed container directory
            artifact_type = container_hint
            # Give a smaller bonus since we're inferring the type
            container_bonus = self.config.container_hint_weight // 2
            total_score += container_bonus
            breakdown["container_hint_score"] = container_bonus
            match_reasons.append(
                f"Type inferred from container ({container_hint.value}) (+{container_bonus})"
            )

        # Penalty: Directory depth
        # Pass container_hint to reduce penalty for artifacts inside typed containers
        depth_penalty = self._calculate_depth_penalty(path, root_hint, container_hint)
        total_score -= depth_penalty
        breakdown["depth_penalty"] = depth_penalty
        if depth_penalty > 0:
            match_reasons.append(f"Depth penalty (-{depth_penalty})")

        # Ensure score is non-negative
        total_score = max(0, total_score)

        # Add raw total to breakdown
        breakdown["raw_total"] = total_score

        return artifact_type, match_reasons, breakdown

    def _parse_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Parse YAML frontmatter from markdown content.

        Looks for frontmatter delimited by --- markers at start of file.
        Returns dict with keys like 'type', 'artifact-type', 'skill', etc.

        Args:
            content: File content string

        Returns:
            Parsed frontmatter dict or None if not found/invalid
        """
        import yaml

        if not content.startswith("---"):
            return None

        # Find closing ---
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return None

        frontmatter_str = content[3:end_idx].strip()
        try:
            return yaml.safe_load(frontmatter_str)
        except yaml.YAMLError:
            return None

    def _parse_manifest_frontmatter(self, content: str) -> Optional[str]:
        """Parse YAML frontmatter and extract artifact type.

        Parses YAML frontmatter (--- delimited at start of file) and returns
        the value of the 'type' field if present, normalized to lowercase.

        Args:
            content: File content string

        Returns:
            Normalized type value (lowercase) or None if:
            - No frontmatter (file doesn't start with ---)
            - Empty frontmatter (--- followed immediately by ---)
            - Malformed YAML between delimiters
            - No 'type' field in valid frontmatter

        Examples:
            >>> detector._parse_manifest_frontmatter("---\\ntype: skill\\n---\\n# Content")
            'skill'
            >>> detector._parse_manifest_frontmatter("---\\ntype: COMMAND\\n---")
            'command'
            >>> detector._parse_manifest_frontmatter("# No frontmatter")
            None
            >>> detector._parse_manifest_frontmatter("---\\n---")
            None
        """
        frontmatter = self._parse_frontmatter(content)
        if frontmatter is None:
            return None

        # Empty frontmatter case (parsed as None by yaml.safe_load)
        if not isinstance(frontmatter, dict):
            return None

        # Look for 'type' field
        type_value = frontmatter.get("type")
        if type_value is None:
            return None

        # Normalize to lowercase string
        if isinstance(type_value, str):
            return type_value.lower().strip()

        return None

    def _frontmatter_type_to_artifact_type(
        self, frontmatter_type: str
    ) -> Optional[ArtifactType]:
        """Convert frontmatter type string to ArtifactType enum.

        Args:
            frontmatter_type: Type string from frontmatter (lowercase)

        Returns:
            Matching ArtifactType or None if no match
        """
        type_mapping = {
            "skill": ArtifactType.SKILL,
            "command": ArtifactType.COMMAND,
            "agent": ArtifactType.AGENT,
            "mcp_server": ArtifactType.MCP_SERVER,
            "mcp-server": ArtifactType.MCP_SERVER,
            "mcpserver": ArtifactType.MCP_SERVER,
            "mcp": ArtifactType.MCP_SERVER,
            "hook": ArtifactType.HOOK,
        }
        return type_mapping.get(frontmatter_type)

    def _score_manifest_with_content(
        self,
        path: str,
        siblings: Set[str],
        file_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[ArtifactType], int, Optional[str]]:
        """Score based on manifest file presence and frontmatter type.

        Extended version of _score_manifest that also parses frontmatter
        to extract artifact type when file contents are available.

        Args:
            path: Directory path
            siblings: Set of filenames in the directory
            file_contents: Optional dict mapping filename to file content

        Returns:
            Tuple of (artifact_type, score, frontmatter_type)
            - artifact_type: Detected type from manifest name or frontmatter
            - score: Base manifest score (not including frontmatter bonus)
            - frontmatter_type: Type extracted from frontmatter (if any)
        """
        manifest_type: Optional[ArtifactType] = None
        manifest_score = 0
        frontmatter_type: Optional[str] = None

        # First check manifest file presence
        for artifact_type, manifest_names in self.config.manifest_files.items():
            matching_manifests = siblings & manifest_names
            if matching_manifests:
                manifest_type = artifact_type
                manifest_score = self.config.manifest_weight

                # If we have file contents, try to parse frontmatter
                if file_contents:
                    for manifest_file in matching_manifests:
                        if manifest_file in file_contents:
                            content = file_contents[manifest_file]
                            frontmatter_type = self._parse_manifest_frontmatter(content)
                            if frontmatter_type:
                                break  # Found type, no need to check other manifests

                break  # Found a manifest match

        return manifest_type, manifest_score, frontmatter_type

    def score_directory_with_content(
        self,
        path: str,
        siblings: Set[str],
        file_contents: Optional[Dict[str, str]] = None,
        root_hint: Optional[str] = None,
        container_hint: Optional[ArtifactType] = None,
    ) -> Tuple[Optional[ArtifactType], List[str], Dict[str, int]]:
        """Score a directory with optional file content for frontmatter parsing.

        This method extends _score_directory to support frontmatter type detection
        when manifest file contents are provided. If frontmatter type is found and
        contradicts directory signals, frontmatter wins (strongest signal).

        Args:
            path: Directory path to score
            siblings: Set of filenames in this directory
            file_contents: Optional dict mapping filename to content for frontmatter parsing
            root_hint: Optional root hint for parent matching
            container_hint: Optional artifact type hint from parent container directory

        Returns:
            Tuple of (artifact_type, match_reasons, score_breakdown)
        """
        # Start with basic scoring
        artifact_type, match_reasons, breakdown = self._score_directory(
            path,
            siblings,
            root_hint,
            use_frontmatter=False,
            container_hint=container_hint,
        )

        # Initialize frontmatter_type_score in breakdown
        breakdown["frontmatter_type_score"] = 0

        # If we have file contents, try to get frontmatter type
        if file_contents:
            _, _, frontmatter_type = self._score_manifest_with_content(
                path, siblings, file_contents
            )

            if frontmatter_type:
                frontmatter_artifact_type = self._frontmatter_type_to_artifact_type(
                    frontmatter_type
                )

                if frontmatter_artifact_type:
                    # Add frontmatter type bonus
                    breakdown["frontmatter_type_score"] = (
                        self.config.frontmatter_type_weight
                    )
                    breakdown["raw_total"] += self.config.frontmatter_type_weight
                    match_reasons.append(
                        f"Frontmatter type: {frontmatter_type} "
                        f"(+{self.config.frontmatter_type_weight})"
                    )

                    # If frontmatter type contradicts directory signals, frontmatter wins
                    if artifact_type and artifact_type != frontmatter_artifact_type:
                        match_reasons.append(
                            f"Frontmatter type '{frontmatter_type}' overrides "
                            f"directory-based type '{artifact_type.value}'"
                        )
                        artifact_type = frontmatter_artifact_type
                    elif not artifact_type:
                        artifact_type = frontmatter_artifact_type

        return artifact_type, match_reasons, breakdown

    def _score_dir_name(self, path: str) -> Tuple[Optional[ArtifactType], int]:
        """Score based on directory name matching.

        Args:
            path: Directory path to check

        Returns:
            Tuple of (artifact_type, score)
        """
        posix_path = PurePosixPath(path)
        dir_name = posix_path.name.lower()

        # Check each artifact type's directory patterns
        for artifact_type, patterns in self.config.dir_patterns.items():
            if dir_name in patterns:
                return artifact_type, self.config.dir_name_weight

        # Check if parent directory matches (e.g., path is "skills/my-skill")
        if len(posix_path.parts) >= 2:
            parent_name = posix_path.parts[-2].lower()
            for artifact_type, patterns in self.config.dir_patterns.items():
                if parent_name in patterns:
                    # Parent match is weaker signal
                    return artifact_type, self.config.dir_name_weight // 2

        return None, 0

    def _score_manifest(
        self, path: str, siblings: Set[str]
    ) -> Tuple[Optional[ArtifactType], int]:
        """Score based on manifest file presence.

        Args:
            path: Directory path
            siblings: Set of filenames in the directory

        Returns:
            Tuple of (artifact_type, score)
        """
        for artifact_type, manifest_names in self.config.manifest_files.items():
            # Check if any manifest file exists in siblings
            if siblings & manifest_names:  # Set intersection
                return artifact_type, self.config.manifest_weight

        return None, 0

    def _score_extensions(self, path: str, siblings: Set[str]) -> int:
        """Score based on file extensions.

        Args:
            path: Directory path
            siblings: Set of filenames in the directory

        Returns:
            Extension score
        """
        # Count how many files have expected extensions
        matching_extensions = sum(
            1
            for filename in siblings
            if PurePosixPath(filename).suffix in self.config.expected_extensions
        )

        # Score proportional to matching files (capped at extension_weight)
        if matching_extensions > 0:
            return min(self.config.extension_weight, matching_extensions)

        return 0

    def _score_parent_hint(
        self, path: str, artifact_type: Optional[ArtifactType]
    ) -> int:
        """Score based on parent directory hint.

        Args:
            path: Directory path
            artifact_type: Detected artifact type (if any)

        Returns:
            Parent hint bonus score
        """
        if not artifact_type:
            return 0

        posix_path = PurePosixPath(path)

        # Check if any parent directory matches common patterns
        # Examples: "claude-skills", "anthropic-skills", etc.
        for part in posix_path.parts:
            part_lower = part.lower()

            # Check for common artifact collection patterns
            common_patterns = [
                "claude",
                "anthropic",
                "artifacts",
                f"{artifact_type.value}s",
                artifact_type.value,
            ]

            # Also check directory patterns for this artifact type
            if artifact_type in self.config.dir_patterns:
                common_patterns.extend(self.config.dir_patterns[artifact_type])

            if any(pattern in part_lower for pattern in common_patterns):
                return self.config.parent_hint_weight

        return 0

    def _calculate_depth_penalty(
        self,
        path: str,
        root_hint: Optional[str] = None,
        container_hint: Optional[ArtifactType] = None,
    ) -> int:
        """Calculate depth penalty for path.

        When an artifact is inside a typed container (e.g., commands/, skills/),
        depth penalty is reduced to avoid unfairly penalizing deeply nested
        artifacts that are properly organized within a container hierarchy.

        Args:
            path: Directory path
            root_hint: Optional root hint to adjust depth calculation
            container_hint: If present, indicates artifact is inside a typed container
                           and depth penalty should be reduced

        Returns:
            Depth penalty score
        """
        posix_path = PurePosixPath(path)

        # Adjust depth based on root_hint
        if root_hint:
            root_parts = PurePosixPath(root_hint).parts
            path_parts = posix_path.parts

            # If path is under root_hint, calculate depth from root_hint
            if (
                len(path_parts) >= len(root_parts)
                and path_parts[: len(root_parts)] == root_parts
            ):
                depth = len(path_parts) - len(root_parts)
            else:
                depth = len(path_parts)
        else:
            depth = len(posix_path.parts)

        base_penalty = depth * self.config.depth_penalty

        # When inside a typed container, reduce depth penalty by 50%
        # This ensures artifacts like commands/dev/subgroup/my-cmd don't get
        # unfairly penalized for being properly organized in a container hierarchy
        if container_hint is not None:
            return base_penalty // 2

        return base_penalty

    def matches_to_artifacts(
        self,
        matches: List[HeuristicMatch],
        base_url: str,
        detected_sha: Optional[str] = None,
    ) -> List[DetectedArtifact]:
        """Convert heuristic matches to detected artifact objects.

        Filters out low-confidence matches and deduplicates.

        Args:
            matches: List of heuristic matches
            base_url: Base URL for repository
            detected_sha: Git commit SHA for version tracking

        Returns:
            List of detected artifacts
        """
        artifacts: List[DetectedArtifact] = []
        seen_paths: Set[str] = set()

        for match in matches:
            # Skip if below confidence threshold
            if match.confidence_score < self.config.min_confidence:
                continue

            # Skip if no artifact type detected
            if not match.artifact_type:
                continue

            # Skip duplicates
            if match.path in seen_paths:
                continue

            seen_paths.add(match.path)

            # Extract artifact name from path
            posix_path = PurePosixPath(match.path)
            name = posix_path.name

            # Strip .md extension for single-file artifact types (Commands, Agents, Hooks)
            # These are often single .md files and should not include the extension in the name
            single_file_types = (
                ArtifactType.COMMAND,
                ArtifactType.AGENT,
                ArtifactType.HOOK,
            )
            if match.artifact_type in single_file_types and name.endswith(".md"):
                name = name[:-3]

            # Construct upstream URL
            upstream_url = f"{base_url.rstrip('/')}/tree/main/{match.path}"

            artifact = DetectedArtifact(
                artifact_type=match.artifact_type,
                name=name,
                path=match.path,
                upstream_url=upstream_url,
                confidence_score=match.confidence_score,
                detected_sha=detected_sha,
                detected_version=None,  # Will be extracted later from manifest
                raw_score=match.raw_score,
                score_breakdown=match.breakdown,
                metadata={
                    "match_reasons": match.match_reasons,
                    "dir_name_score": match.dir_name_score,
                    "manifest_score": match.manifest_score,
                    "extension_score": match.extension_score,
                    "depth_penalty": match.depth_penalty,
                },
            )

            artifacts.append(artifact)

        return artifacts


def detect_artifacts_in_tree(
    file_tree: List[str],
    repo_url: str,
    ref: str = "main",
    root_hint: Optional[str] = None,
    detected_sha: Optional[str] = None,
    enable_frontmatter_detection: bool = False,
    manual_mappings: Optional[Dict[str, str]] = None,
) -> List[DetectedArtifact]:
    """Convenience function to detect artifacts in a file tree.

    Args:
        file_tree: List of all file paths in the repository
        repo_url: GitHub repository URL
        ref: Branch/tag/SHA being scanned
        root_hint: Optional subdirectory to focus on
        detected_sha: Git commit SHA for version tracking
        enable_frontmatter_detection: Enable frontmatter parsing for type detection
        manual_mappings: Optional directory-to-artifact-type mappings for manual
            override. Format: {"path/to/dir": "skill", "another/path": "command"}.
            Valid artifact types: "skill", "command", "agent", "mcp_server", "hook".
            When provided, directories matching these paths (or inheriting from them)
            will use the specified artifact type, bypassing heuristic detection.
            Confidence scores: exact match=95, depth=1=92, depth=2=89, depth=3+=86.

    Returns:
        List of detected artifacts with confidence scores

    Example:
        >>> files = ["skills/my-skill/SKILL.md", "skills/my-skill/index.ts", "README.md"]
        >>> artifacts = detect_artifacts_in_tree(files, "https://github.com/user/repo")
        >>> print(artifacts[0].name, artifacts[0].confidence_score)
        my-skill 85

        >>> # With manual mappings
        >>> artifacts = detect_artifacts_in_tree(
        ...     files,
        ...     "https://github.com/user/repo",
        ...     manual_mappings={"custom/path": "skill"}
        ... )
    """
    detector = HeuristicDetector(
        enable_frontmatter_detection=enable_frontmatter_detection,
        manual_mappings=manual_mappings,
    )
    matches = detector.analyze_paths(file_tree, base_url=repo_url, root_hint=root_hint)
    return detector.matches_to_artifacts(
        matches, base_url=repo_url, detected_sha=detected_sha
    )


if __name__ == "__main__":
    # Quick validation
    test_files = [
        "skills/canvas-design/SKILL.md",
        "skills/canvas-design/index.ts",
        "skills/canvas-design/package.json",
        "commands/deploy/COMMAND.md",
        "commands/deploy/deploy.py",
        "agents/helper/AGENT.md",
        "agents/helper/agent.ts",
        "mcp/server-tools/MCP.md",
        "mcp/server-tools/server.json",
        "src/utils/helpers.py",
        "README.md",
        "LICENSE",
    ]

    artifacts = detect_artifacts_in_tree(
        test_files,
        "https://github.com/test/repo",
        detected_sha="abc123",
    )

    print(f"Detected {len(artifacts)} artifacts:")
    for a in artifacts:
        print(
            f"  - {a.artifact_type}: {a.name} (score: {a.confidence_score}%, path: {a.path})"
        )

    print("\nDetection details:")
    detector = HeuristicDetector()
    matches = detector.analyze_paths(
        test_files, base_url="https://github.com/test/repo"
    )
    for match in matches[:5]:  # Show top 5
        print(f"\n{match.path} ({match.confidence_score}%):")
        for reason in match.match_reasons:
            print(f"  - {reason}")
