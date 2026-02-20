"""Heuristic detector for Claude Code artifacts in GitHub repositories.

Uses multi-signal scoring to identify potential artifacts with confidence levels.

Architecture Overview (Phase 3 Refactor):
-----------------------------------------
This module implements a two-layer detection architecture that separates concerns
between baseline type detection (shared across all artifact sources) and
marketplace-specific scoring signals (unique to GitHub repository scanning).

**Why Two Layers?**
The shared `artifact_detection` module provides universal type inference that works
for local directories, GitHub repos, and future sources. This module extends that
baseline with marketplace-specific heuristics (depth penalty, parent hints, etc.)
that are unique to scanning unstructured GitHub repositories.

1. **Baseline Detection** (via `skillmeat.core.artifact_detection`):
   - Container name matching: "skills/", "commands/" → infer type
   - Manifest detection: SKILL.md, COMMAND.md → detect and validate type
   - Path structure inference: Uses canonical container names and aliases
   - Provides: ArtifactType, base confidence (0-50 pts), detection reasons

2. **Marketplace-Specific Signals** (unique to GitHub scanning):
   - Extension scoring (5 pts): Count files with expected extensions (.md, .py, .ts)
   - Parent hint scoring (15 pts): Boost for paths containing "claude", "anthropic"
   - Frontmatter presence (15 pts): README.md/SKILL.md presence boost
   - Container hint bonus (25 pts): Extra confidence when type matches container
   - Frontmatter type (30 pts): Parse YAML frontmatter for explicit type field
   - Depth penalty: Penalize deeply nested paths (reduced 50% inside containers)

Scoring Formula (8 signals, MAX_RAW_SCORE = 160):
------------------------------------------------
Baseline signals (from artifact_detection):
  - dir_name: 10 pts (container/directory name matching)
  - manifest: 20 pts (SKILL.md, COMMAND.md presence)
  - skill_manifest_bonus: 40 pts (SKILL.md definitive marker for Skills)

Marketplace signals (GitHub-specific):
  - extensions: 5 pts (expected file types present)
  - parent_hint: 15 pts (ancestor paths match patterns)
  - frontmatter: 15 pts (documentation file presence)
  - container_hint: 25 pts (type matches parent container)
  - frontmatter_type: 30 pts (explicit type in YAML frontmatter)

Final confidence = normalize(raw_score) → 0-100 scale

Usage Example:
-------------
    >>> from skillmeat.core.marketplace.heuristic_detector import detect_artifacts_in_tree
    >>>
    >>> # Scan repository file tree
    >>> files = ["skills/my-skill/SKILL.md", "skills/my-skill/index.ts"]
    >>> artifacts = detect_artifacts_in_tree(
    ...     files,
    ...     repo_url="https://github.com/user/repo",
    ...     detected_sha="abc123"
    ... )
    >>>
    >>> # Results with confidence scores
    >>> for artifact in artifacts:
    ...     print(f"{artifact.name}: {artifact.confidence_score}% ({artifact.artifact_type})")
    my-skill: 85% (skill)

    >>> # With manual directory mappings (overrides heuristics)
    >>> artifacts = detect_artifacts_in_tree(
    ...     files,
    ...     repo_url="https://github.com/user/repo",
    ...     manual_mappings={"custom/path": "skill"}  # Force type for directory
    ... )

Shared Detection Module:
-----------------------
This module delegates baseline detection to `skillmeat.core.artifact_detection`:
  - ARTIFACT_SIGNATURES: Type detection patterns
  - CANONICAL_CONTAINERS: Standard container names (skills/, commands/)
  - CONTAINER_ALIASES: Alternative names (skill → skills mapping)
  - get_artifact_type_from_container(): Container → type inference
  - infer_artifact_type(): Multi-signal type detection
  - detect_artifact(): Full detection with confidence

Migration Notes:
---------------
Developers familiar with the pre-Phase-3 code should note:
  - Detection logic is now split: baseline (shared) + marketplace (this file)
  - Signal weights unchanged: same confidence scores as before
  - score_directory_v2() is the new entry point using refactored architecture
  - Legacy _score_directory() remains for backwards compatibility
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from skillmeat.api.schemas.marketplace import DetectedArtifact, HeuristicMatch
from skillmeat.core.artifact_detection import (
    ARTIFACT_SIGNATURES,
    CANONICAL_CONTAINERS,
    CONTAINER_ALIASES,
    CONTAINER_TO_TYPE,
    ArtifactType,
    DetectionResult,
    detect_artifact,
    extract_manifest_file,
    get_artifact_type_from_container,
    infer_artifact_type,
    normalize_container_name,
)

logger = logging.getLogger(__name__)

# Maximum raw score from all signals (10+20+40+5+15+15+25+30 = 160)
# dir_name(10) + manifest(20) + skill_manifest_bonus(40) + extensions(5)
# + parent_hint(15) + frontmatter(15) + container_hint(25) + frontmatter_type(30)
MAX_RAW_SCORE = 160

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


# Populate the container type mapping using imported ArtifactType
# Only plural forms are containers; singular forms can be artifact names
CONTAINER_TYPE_MAPPING.update(
    {
        "commands": ArtifactType.COMMAND,
        "agents": ArtifactType.AGENT,
        "skills": ArtifactType.SKILL,
        "hooks": ArtifactType.HOOK,
        "mcp": ArtifactType.MCP,
        "mcp-servers": ArtifactType.MCP,
        "servers": ArtifactType.MCP,
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
            ArtifactType.MCP: {"mcp", "mcp-servers", "servers"},
            ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
        }
    )

    # Manifest filenames for each artifact type
    manifest_files: Dict[ArtifactType, Set[str]] = field(
        default_factory=lambda: {
            ArtifactType.SKILL: {"SKILL.md", "skill.md"},
            ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
            ArtifactType.AGENT: {"AGENT.md", "agent.md"},
            ArtifactType.MCP: {"MCP.md", "mcp.md", "server.json"},
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
    skill_manifest_bonus: int = 40  # Extra bonus when SKILL.md detected for Skill type


class HeuristicDetector:
    """Detects Claude Code artifacts using multi-signal scoring heuristics.

    This class implements the marketplace-specific detection layer that extends
    baseline artifact detection with GitHub repository scanning heuristics.

    Architecture:
        1. Baseline detection via shared artifact_detection module
        2. Marketplace-specific signals layered on top
        3. Optional manual directory mappings for overrides

    Initialization:
        config (DetectionConfig): Custom scoring weights and thresholds
        enable_frontmatter_detection (bool): Parse YAML frontmatter for type hints
        manual_mappings (dict): Directory → artifact type overrides

    Key Methods:
        - analyze_paths(): Main entry point - scan file tree, return matches
        - score_directory_v2(): New architecture entry point (baseline + marketplace)
        - _get_baseline_detection(): Extract baseline signals from shared module
        - _calculate_marketplace_confidence(): Apply marketplace-specific signals

    Example:
        >>> detector = HeuristicDetector()
        >>> matches = detector.analyze_paths(file_paths, base_url="https://github.com/user/repo")
        >>> for match in matches:
        ...     if match.confidence_score >= 50:
        ...         print(f"Found {match.artifact_type}: {match.path} ({match.confidence_score}%)")

        >>> # With manual mappings
        >>> detector = HeuristicDetector(manual_mappings={"custom/dir": "skill"})
        >>> matches = detector.analyze_paths(file_paths, base_url="...")
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
            >>> detector._string_to_artifact_type("mcp")
            ArtifactType.MCP
            >>> detector._string_to_artifact_type("invalid")
            None
        """
        type_mapping = {
            "skill": ArtifactType.SKILL,
            "command": ArtifactType.COMMAND,
            "agent": ArtifactType.AGENT,
            "mcp": ArtifactType.MCP,
            "mcp_server": ArtifactType.MCP,  # Legacy alias
            "mcp-server": ArtifactType.MCP,  # Legacy alias
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

    def _detect_plugin_directories(
        self,
        dir_to_files: Dict[str, Set[str]],
        root_hint: Optional[str],
    ) -> Tuple[List[HeuristicMatch], Set[str]]:
        """Detect composite/plugin directories from the file tree.

        Detection signals, in priority order:

        1. ``plugin.json`` at directory root — definitive composite signal (confidence 95)
        2. ``COMPOSITE.md`` or ``PLUGIN.md`` at directory root — strong composite
           signal (confidence 90)
        3. Two or more entity-type subdirectories (skills/, commands/, agents/, hooks/,
           mcp/) — heuristic composite signal (confidence 70)

        Detected plugin directories are returned alongside a set of their paths so
        that ``analyze_paths()`` can exclude descendant paths from individual-artifact
        detection (avoiding double-counting).

        Args:
            dir_to_files: Mapping of directory paths to the set of filenames in each.
            root_hint: Optional path prefix filter; directories outside this prefix
                are skipped.

        Returns:
            A 2-tuple of:
            - ``matches``: ``HeuristicMatch`` objects for each detected plugin
              directory, with ``artifact_type == "composite"``.
            - ``plugin_dirs``: Set of plugin directory paths detected, used by the
              caller to suppress individual-artifact detection of descendants.
        """
        matches: List[HeuristicMatch] = []
        plugin_dirs: Set[str] = set()

        for dir_path, files in dir_to_files.items():
            # Skip root
            if dir_path == ".":
                continue

            # Apply root hint filtering
            if root_hint and not dir_path.startswith(root_hint):
                continue

            # Skip deep paths
            depth = len(PurePosixPath(dir_path).parts)
            if depth > self.config.max_depth:
                continue

            # Check the file names in this directory (lower-cased for comparison)
            lower_files = {f.lower() for f in files}

            # Signal 1: plugin.json — definitive manifest
            has_plugin_json = "plugin.json" in lower_files

            # Signal 2: COMPOSITE.md or PLUGIN.md — strong manifest signal
            has_composite_manifest = bool(
                lower_files & {"composite.md", "plugin.md", "composite.json"}
            )

            # Signal 3: Multiple entity-type subdirectories
            is_heuristic_plugin = self._is_plugin_directory(dir_path, dir_to_files)

            if not (has_plugin_json or has_composite_manifest or is_heuristic_plugin):
                continue

            # Determine confidence and match reasons
            if has_plugin_json:
                confidence = 95
                primary_reason = "plugin.json manifest found at directory root (95)"
                signal = "plugin_json"
            elif has_composite_manifest:
                manifest_name = next(
                    f for f in files if f.lower() in {"composite.md", "plugin.md", "composite.json"}
                )
                confidence = 90
                primary_reason = (
                    f"{manifest_name} manifest found at directory root (90)"
                )
                signal = "composite_manifest"
            else:
                confidence = 70
                primary_reason = (
                    "Multiple entity-type subdirectories detected (skills/, commands/, "
                    "agents/, hooks/, mcp/) — heuristic composite signal (70)"
                )
                signal = "multi_type_dirs"

            match_reasons = [primary_reason]
            if has_plugin_json and has_composite_manifest:
                match_reasons.append(
                    "Additional composite manifest file also present"
                )

            logger.debug(
                "Plugin detected at %s: signal=%s, confidence=%d",
                dir_path,
                signal,
                confidence,
            )

            # raw_score stores the unnormalized total (0-MAX_RAW_SCORE scale).
            # manifest_score, dir_name_score, extension_score are individual signal
            # contributions constrained to 0-100 by the HeuristicMatch schema.
            # For composites we represent the composite manifest contribution as the
            # normalized confidence value, which fits within the le=100 bound.
            raw_score = MAX_RAW_SCORE if confidence >= 90 else round(
                (confidence / 100) * MAX_RAW_SCORE
            )
            score_breakdown = {
                "dir_name_score": 0,
                "manifest_score": confidence,  # normalized representation
                "skill_manifest_bonus": 0,
                "extensions_score": 0,
                "parent_hint_score": 0,
                "frontmatter_score": 0,
                "container_hint_score": 0,
                "depth_penalty": 0,
                "raw_total": raw_score,
                "normalized_score": confidence,
            }

            match = HeuristicMatch(
                path=dir_path,
                artifact_type=ArtifactType.COMPOSITE.value,
                confidence_score=confidence,
                organization_path=None,
                match_reasons=match_reasons,
                dir_name_score=0,
                manifest_score=confidence,  # individual signal score (le=100)
                extension_score=0,
                depth_penalty=0,
                raw_score=raw_score,
                breakdown=score_breakdown,
                metadata={
                    "is_plugin": True,
                    "plugin_signal": signal,
                    "has_plugin_json": has_plugin_json,
                    "has_composite_manifest": has_composite_manifest,
                    "is_heuristic_plugin": is_heuristic_plugin,
                },
            )
            matches.append(match)
            plugin_dirs.add(dir_path)

        matches.sort(key=lambda m: m.confidence_score, reverse=True)
        return matches, plugin_dirs

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
                        if best_match_path is None or len(c_path) > len(
                            best_match_path
                        ):
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
                    "depth_penalty": (
                        single_file_depth_penalty if not is_manual_mapping else 0
                    ),
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
                    depth_penalty=(
                        single_file_depth_penalty if not is_manual_mapping else 0
                    ),
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

        # Detect composite/plugin directories FIRST.
        # This establishes which directories are plugins so their descendant paths can
        # be excluded from individual-artifact detection (avoids double-counting members
        # as standalone artifacts while the plugin itself is also returned).
        plugin_matches, plugin_dirs = self._detect_plugin_directories(
            dir_to_files, root_hint
        )
        matches.extend(plugin_matches)

        if plugin_dirs:
            logger.debug(
                "Plugin detection found %d composite(s): %s",
                len(plugin_dirs),
                sorted(plugin_dirs),
            )

        # Detect single-file artifacts inside containers, then filter out any that
        # live inside a detected plugin directory (they are plugin members, not
        # standalone artifacts).
        single_file_matches = self._detect_single_file_artifacts(
            dir_to_files, container_types, root_hint
        )
        for sfm in single_file_matches:
            sfm_dir = str(PurePosixPath(sfm.path).parent)
            if plugin_dirs and any(
                sfm_dir == pd or sfm_dir.startswith(pd + "/")
                for pd in plugin_dirs
            ):
                logger.debug(
                    "Skipping single-file artifact %s: inside plugin directory",
                    sfm.path,
                )
                continue
            matches.append(sfm)

        # Analyze each directory
        for dir_path, files in dir_to_files.items():
            # Skip root directory
            if dir_path == ".":
                continue

            # Skip if container directory (containers themselves are not artifacts)
            if self._is_container_directory(dir_path, dir_to_files):
                continue

            # Skip if this directory IS a detected plugin (already added above)
            if dir_path in plugin_dirs:
                continue

            # Skip if this directory is INSIDE a detected plugin.
            # Plugin member artifacts are expressed through the composite; emitting
            # them separately would create duplicate entries and inflate counts.
            if any(
                dir_path == pd or dir_path.startswith(pd + "/")
                for pd in plugin_dirs
            ):
                logger.debug(
                    "Skipping %s: descendant of plugin directory", dir_path
                )
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
                    "skill_manifest_bonus": score_breakdown.get(
                        "skill_manifest_bonus", 0
                    ),
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
            "skill_manifest_bonus": 0,
            "extensions_score": 0,
            "parent_hint_score": 0,
            "frontmatter_score": 0,
            "container_hint_score": 0,
            "standalone_bonus": 0,
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

        # Signal 2b: Skill manifest bonus
        # SKILL.md is a definitive marker for skill artifacts - give extra weight
        if manifest_type == ArtifactType.SKILL:
            has_skill_md = any(f.lower() == "skill.md" for f in siblings)
            if has_skill_md:
                total_score += self.config.skill_manifest_bonus
                breakdown["skill_manifest_bonus"] = self.config.skill_manifest_bonus
                match_reasons.append(
                    f"SKILL.md definitive marker (+{self.config.skill_manifest_bonus})"
                )

        # Signal 3: File extensions
        extension_score = self._score_extensions(path, siblings)
        if extension_score > 0:
            total_score += extension_score
            breakdown["extensions_score"] = extension_score
            match_reasons.append(
                f"Contains expected file extensions (+{extension_score})"
            )

        # Signal 4: Container hint inference (if type unknown)
        # IMPORTANT: This must run BEFORE parent hint scoring so that artifact_type
        # is set when we check parent directories. Otherwise, hooks and other artifacts
        # that rely solely on container_hint would miss the +15 parent hint bonus.
        if container_hint is not None and artifact_type is None:
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

        # Signal 5: Parent hint bonus
        # Now artifact_type may be set from container_hint inference above
        parent_hint_score = self._score_parent_hint(path, artifact_type)
        if parent_hint_score > 0:
            total_score += parent_hint_score
            breakdown["parent_hint_score"] = parent_hint_score
            match_reasons.append(f"Parent directory hint bonus (+{parent_hint_score})")

        # Signal 6: Frontmatter detection (if enabled)
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

        # Signal 7: Container hint match bonus (when type already detected)
        # If this directory is inside a container (e.g., skills/my-skill inside skills/)
        # and the detected type matches the container type, add full bonus
        # NOTE: Only give full bonus if type was NOT inferred from container (already got 12 pts)
        if container_hint is not None and artifact_type is not None:
            if (
                artifact_type == container_hint
                and breakdown["container_hint_score"] == 0
            ):
                total_score += self.config.container_hint_weight
                breakdown["container_hint_score"] = self.config.container_hint_weight
                match_reasons.append(
                    f"Type matches container hint ({container_hint.value}) "
                    f"(+{self.config.container_hint_weight})"
                )

        # Signal 8: Standalone artifact bonus
        # If manifest detected but no container context, give standalone bonus
        # This ensures root-level artifacts with manifests score above threshold
        if (
            artifact_type is not None
            and container_hint is None
            and breakdown["manifest_score"] > 0
        ):
            standalone_bonus = self.config.container_hint_weight  # 25 pts
            total_score += standalone_bonus
            breakdown["standalone_bonus"] = standalone_bonus
            match_reasons.append(
                f"Standalone artifact with manifest (+{standalone_bonus})"
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
            "mcp": ArtifactType.MCP,
            "mcp_server": ArtifactType.MCP,  # Legacy alias
            "mcp-server": ArtifactType.MCP,  # Legacy alias
            "mcpserver": ArtifactType.MCP,  # Legacy alias
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

    def score_directory_v2(
        self,
        path: str,
        siblings: Set[str],
        root_hint: Optional[str] = None,
        container_hint: Optional[ArtifactType] = None,
        container_type: Optional[str] = None,
        use_frontmatter: bool = False,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[ArtifactType], List[str], Dict[str, int]]:
        """Score a directory using the refactored baseline + marketplace architecture.

        This method implements the Phase 3 refactored scoring architecture that
        separates baseline detection (via shared module) from marketplace-specific
        signals. It provides the same output format as the original _score_directory
        for backwards compatibility.

        The refactored architecture:
        1. **Baseline Detection**: Uses shared artifact_detection module functions
           (get_artifact_type_from_container, extract_manifest_file patterns)
           to provide type inference and base confidence.

        2. **Marketplace Signals**: Applies marketplace-specific signals on top
           of baseline (extensions, parent hint, frontmatter, container bonus,
           depth penalty).

        Args:
            path: Directory path to score
            siblings: Set of filenames in this directory
            root_hint: Optional root hint for depth calculation
            container_hint: Optional ArtifactType hint from parent container
            container_type: Optional container directory name (e.g., "skills")
            use_frontmatter: Enable frontmatter presence boost
            file_contents: Optional dict mapping filename to content for
                          frontmatter type parsing

        Returns:
            Tuple of (artifact_type, match_reasons, score_breakdown):
            - artifact_type: Detected ArtifactType or None
            - match_reasons: List of reasons explaining the detection
            - score_breakdown: Dict with individual signal scores and raw_total

        Example:
            >>> detector.score_directory_v2(
            ...     "skills/my-skill",
            ...     {"SKILL.md", "index.ts", "README.md"},
            ...     container_hint=ArtifactType.SKILL,
            ...     use_frontmatter=True
            ... )
            (ArtifactType.SKILL, [...], {"dir_name_score": 5, "manifest_score": 20, ...})

        Note:
            This method is equivalent to calling _get_baseline_detection() followed
            by _calculate_marketplace_confidence(), but provides a simpler interface
            for callers that don't need the intermediate baseline result.
        """
        # Step 1: Get baseline detection from shared module
        baseline_type, baseline_confidence, baseline_reasons = (
            self._get_baseline_detection(
                path,
                siblings,
                container_type=container_type,
            )
        )

        # Step 2: Apply marketplace-specific signals
        (
            final_type,
            _raw_score,
            all_reasons,
            breakdown,
        ) = self._calculate_marketplace_confidence(
            baseline_type=baseline_type,
            baseline_confidence=baseline_confidence,
            baseline_reasons=baseline_reasons,
            path=path,
            siblings=siblings,
            root_hint=root_hint,
            container_hint=container_hint,
            use_frontmatter=use_frontmatter,
            file_contents=file_contents,
        )

        return final_type, all_reasons, breakdown

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
        self, _path: str, siblings: Set[str]
    ) -> Tuple[Optional[ArtifactType], int]:
        """Score based on manifest file presence.

        Args:
            _path: Directory path (unused but kept for API consistency)
            siblings: Set of filenames in the directory

        Returns:
            Tuple of (artifact_type, score)
        """
        for artifact_type, manifest_names in self.config.manifest_files.items():
            # Check if any manifest file exists in siblings
            if siblings & manifest_names:  # Set intersection
                return artifact_type, self.config.manifest_weight

        return None, 0

    def _score_extensions(self, _path: str, siblings: Set[str]) -> int:
        """Score based on file extensions.

        Args:
            _path: Directory path (unused but kept for API consistency)
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

    # =========================================================================
    # Phase 3 Refactor: Baseline + Marketplace Signal Architecture
    # =========================================================================

    def _get_baseline_detection(
        self,
        path: str,
        siblings: Set[str],
        container_type: Optional[str] = None,
    ) -> Tuple[Optional[ArtifactType], int, List[str]]:
        """Get baseline artifact detection using shared detection module.

        This method bridges the marketplace heuristic detector with the shared
        artifact_detection module. It provides baseline type inference and
        confidence from the unified detection system.

        **Shared Module Integration:**
        This method uses functions imported from `skillmeat.core.artifact_detection`:
          - get_artifact_type_from_container(): Maps container names to types
          - ARTIFACT_SIGNATURES: Detection patterns used by shared module
          - DetectionResult: Shared detection result format

        **Baseline Detection Signals (4 signals, max 30 pts):**
        1. Container type hint (10 pts): Parent directory name → type inference
        2. Directory name matching (10 pts): Directory itself matches container pattern
        3. Parent directory matching (5 pts): Weaker signal when parent matches
        4. Manifest file presence (20 pts): SKILL.md, COMMAND.md, etc.

        Args:
            path: Directory path to analyze (e.g., "skills/my-skill")
            siblings: Set of filenames in the directory
            container_type: Optional container type hint from parent directory
                           (e.g., "skills" when analyzing skills/my-skill)

        Returns:
            Tuple of (artifact_type, baseline_confidence, detection_reasons):
            - artifact_type: Detected ArtifactType or None
            - baseline_confidence: Raw confidence points from baseline signals (0-50)
            - detection_reasons: List of reasons explaining the detection

        Note:
            Baseline confidence is intentionally capped at ~30-50 points to leave
            room for marketplace-specific signals to contribute the remaining
            70-90 points (extensions, parent hint, frontmatter, container bonus).

        Example:
            >>> detector._get_baseline_detection(
            ...     "skills/my-skill",
            ...     {"SKILL.md", "index.ts"},
            ...     container_type="skills"
            ... )
            (ArtifactType.SKILL, 30, ["Container type 'skills' maps to skill", "Found manifest: SKILL.md"])
        """
        reasons: List[str] = []
        confidence = 0
        artifact_type: Optional[ArtifactType] = None

        # Signal 1: Container type hint (if provided)
        # Uses shared module's get_artifact_type_from_container
        if container_type:
            inferred_type = get_artifact_type_from_container(container_type)
            if inferred_type:
                artifact_type = inferred_type
                confidence += self.config.dir_name_weight  # 10 pts
                reasons.append(
                    f"Container type '{container_type}' maps to {inferred_type.value} "
                    f"(+{self.config.dir_name_weight})"
                )

        # Signal 2: Directory name matching (check path structure)
        posix_path = PurePosixPath(path)
        dir_name = posix_path.name.lower()

        # Check if directory name itself matches a container pattern
        if not artifact_type:
            dir_type = get_artifact_type_from_container(dir_name)
            if dir_type:
                artifact_type = dir_type
                confidence += self.config.dir_name_weight  # 10 pts
                reasons.append(
                    f"Directory name '{dir_name}' matches {dir_type.value} pattern "
                    f"(+{self.config.dir_name_weight})"
                )

        # Signal 3: Parent directory matching (for paths like skills/my-skill)
        if not artifact_type and len(posix_path.parts) >= 2:
            parent_name = posix_path.parts[-2].lower()
            parent_type = get_artifact_type_from_container(parent_name)
            if parent_type:
                artifact_type = parent_type
                # Parent match is weaker signal (half weight)
                half_weight = self.config.dir_name_weight // 2
                confidence += half_weight  # 5 pts
                reasons.append(
                    f"Parent directory '{parent_name}' matches {parent_type.value} pattern "
                    f"(+{half_weight})"
                )

        # Signal 4: Manifest file detection
        # Check siblings for manifest files using shared module's patterns
        for artifact_t, manifest_names in self.config.manifest_files.items():
            matching_manifests = {s.lower() for s in siblings} & {
                m.lower() for m in manifest_names
            }
            if matching_manifests:
                # Manifest overrides type if different (stronger signal)
                if artifact_type and artifact_type != artifact_t:
                    reasons.append(
                        f"Manifest overrides type to {artifact_t.value} "
                        f"(+{self.config.manifest_weight})"
                    )
                else:
                    reasons.append(
                        f"Found manifest file: {list(matching_manifests)[0]} "
                        f"(+{self.config.manifest_weight})"
                    )
                artifact_type = artifact_t
                confidence += self.config.manifest_weight  # 20 pts
                break

        logger.debug(
            "Baseline detection for '%s': type=%s, confidence=%d, reasons=%s",
            path,
            artifact_type.value if artifact_type else None,
            confidence,
            reasons,
        )

        return artifact_type, confidence, reasons

    def _calculate_marketplace_confidence(
        self,
        baseline_type: Optional[ArtifactType],
        baseline_confidence: int,
        baseline_reasons: List[str],
        path: str,
        siblings: Set[str],
        root_hint: Optional[str] = None,
        container_hint: Optional[ArtifactType] = None,
        use_frontmatter: bool = False,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> Tuple[Optional[ArtifactType], int, List[str], Dict[str, int]]:
        """Calculate marketplace-specific confidence on top of baseline detection.

        This method applies marketplace-specific signals that are unique to
        GitHub repository scanning. These signals complement the baseline detection
        with repository-specific heuristics that help identify artifacts in
        unstructured GitHub repositories.

        **Marketplace-Specific Signals (7 signals, max 90 pts):**

        1. **Extension scoring** (max 5 pts): Count files with expected extensions
           (.md, .py, .ts, .js, .json, .yaml, .yml). Helps distinguish artifact
           directories from empty/readme-only folders.

        2. **Container hint inference** (12 pts): If no artifact type detected yet,
           infer type from container hint. This MUST run before parent hint scoring
           so artifacts inside typed containers (e.g., hooks/my-hook) get the
           parent hint bonus.

        3. **Parent hint scoring** (15 pts): Check ancestor directories for
           patterns like "claude", "anthropic", "artifacts", or artifact type names.
           Boosts confidence when artifacts are in recognizable collection structures.
           Now artifact_type may be set from container_hint inference above.

        4. **Frontmatter presence** (15 pts): When use_frontmatter=True, boost
           confidence if README.md, SKILL.md, etc. are present. Indicates
           well-documented artifacts.

        5. **Container hint match bonus** (25 pts): Add bonus when detected type
           matches the container type hint (e.g., skill inside skills/).
           Only applied if type was NOT inferred from container (already got 12 pts).

        6. **Frontmatter type detection** (30 pts): If file_contents provided,
           parse YAML frontmatter for explicit type field. When present, this
           overrides other type signals (highest confidence signal).

        7. **Depth penalty** (variable): Subtract penalty based on path depth.
           Reduced 50% when inside a typed container to avoid unfairly penalizing
           properly organized nested artifacts.

        **Signal Weight Rationale:**
        - Container hint (25 pts) is strongest marketplace signal - explicit structure
        - Frontmatter type (30 pts) is authoritative when present - explicit metadata
        - Parent/frontmatter (15 pts each) are moderate signals - helpful but not definitive
        - Extensions (5 pts) is weakest - just confirms presence of files

        Args:
            baseline_type: Artifact type from baseline detection (may be None)
            baseline_confidence: Confidence points from baseline detection
            baseline_reasons: Detection reasons from baseline
            path: Directory path being analyzed
            siblings: Set of filenames in the directory
            root_hint: Optional path prefix for depth calculation
            container_hint: Artifact type hint from parent container directory
            use_frontmatter: Enable frontmatter presence boost
            file_contents: Optional dict of filename -> content for frontmatter parsing

        Returns:
            Tuple of (final_type, raw_score, all_reasons, score_breakdown):
            - final_type: Final artifact type (may change from baseline)
            - raw_score: Total raw score before normalization (0-120)
            - all_reasons: Combined baseline + marketplace reasons
            - score_breakdown: Dict with individual signal scores

        Example:
            >>> detector._calculate_marketplace_confidence(
            ...     ArtifactType.SKILL, 30, ["Found manifest"],
            ...     "skills/my-skill", {"SKILL.md", "index.ts", "README.md"},
            ...     container_hint=ArtifactType.SKILL, use_frontmatter=True
            ... )
            (ArtifactType.SKILL, 75, [...], {"dir_name_score": 10, "manifest_score": 20, ...})
        """
        # Initialize with baseline values
        artifact_type = baseline_type
        total_score = baseline_confidence
        reasons = list(baseline_reasons)  # Copy to avoid mutation

        # Initialize breakdown - extract baseline signals from reasons
        breakdown: Dict[str, int] = {
            "dir_name_score": 0,
            "manifest_score": 0,
            "skill_manifest_bonus": 0,
            "extensions_score": 0,
            "parent_hint_score": 0,
            "frontmatter_score": 0,
            "container_hint_score": 0,
            "frontmatter_type_score": 0,
            "depth_penalty": 0,
            "raw_total": 0,
        }

        # Parse baseline reasons to populate breakdown
        for reason in baseline_reasons:
            if (
                "Container type" in reason
                or "Directory name" in reason
                or "Parent directory" in reason
            ):
                # Extract score from reason string
                if f"(+{self.config.dir_name_weight})" in reason:
                    breakdown["dir_name_score"] = self.config.dir_name_weight
                elif f"(+{self.config.dir_name_weight // 2})" in reason:
                    breakdown["dir_name_score"] = self.config.dir_name_weight // 2
            elif "manifest" in reason.lower():
                breakdown["manifest_score"] = self.config.manifest_weight

        # =====================================================================
        # Skill Manifest Bonus (40 pts)
        # =====================================================================
        # SKILL.md is a definitive marker for skill artifacts - give extra weight
        # This ensures Skills with SKILL.md score significantly higher
        if baseline_type == ArtifactType.SKILL:
            has_skill_md = any(f.lower() == "skill.md" for f in siblings)
            if has_skill_md:
                total_score += self.config.skill_manifest_bonus
                breakdown["skill_manifest_bonus"] = self.config.skill_manifest_bonus
                reasons.append(
                    f"SKILL.md definitive marker (+{self.config.skill_manifest_bonus})"
                )

        # =====================================================================
        # Marketplace-Specific Signal 1: Extension Scoring (max 5 pts)
        # =====================================================================
        # Counts files with expected extensions (.md, .py, .ts, .js, .json, .yaml)
        # Helps distinguish artifact directories from empty/readme-only folders
        extension_score = self._score_extensions(path, siblings)
        if extension_score > 0:
            total_score += extension_score
            breakdown["extensions_score"] = extension_score
            reasons.append(f"Contains expected file extensions (+{extension_score})")

        # =====================================================================
        # Marketplace-Specific Signal 2: Container Hint Inference (12 pts)
        # =====================================================================
        # IMPORTANT: This must run BEFORE parent hint scoring so that artifact_type
        # is set when we check parent directories. Otherwise, hooks and other artifacts
        # that rely solely on container_hint would miss the +15 parent hint bonus.
        if container_hint is not None and artifact_type is None:
            # No type detected yet - infer from container (weaker signal)
            artifact_type = container_hint
            container_bonus = self.config.container_hint_weight // 2  # 12 pts
            total_score += container_bonus
            breakdown["container_hint_score"] = container_bonus
            reasons.append(
                f"Type inferred from container ({container_hint.value}) (+{container_bonus})"
            )

        # =====================================================================
        # Marketplace-Specific Signal 3: Parent Hint Scoring (15 pts)
        # =====================================================================
        # Boosts confidence when ancestor paths contain "claude", "anthropic",
        # "artifacts", or artifact type names (e.g., "skills", "commands")
        # Now artifact_type may be set from container_hint inference above
        parent_hint_score = self._score_parent_hint(path, artifact_type)
        if parent_hint_score > 0:
            total_score += parent_hint_score
            breakdown["parent_hint_score"] = parent_hint_score
            reasons.append(f"Parent directory hint bonus (+{parent_hint_score})")

        # =====================================================================
        # Marketplace-Specific Signal 4: Frontmatter Presence (15 pts)
        # =====================================================================
        # When enabled, boosts confidence if README.md/SKILL.md/etc. present
        # Indicates well-documented artifacts
        if use_frontmatter:
            md_files = [f for f in siblings if f.lower().endswith(".md")]
            for md_file in md_files:
                if md_file.lower() in (
                    "readme.md",
                    "skill.md",
                    "command.md",
                    "agent.md",
                ):
                    total_score += self.config.frontmatter_weight
                    breakdown["frontmatter_score"] = self.config.frontmatter_weight
                    reasons.append(f"frontmatter_candidate:{md_file}")
                    break

        # =====================================================================
        # Marketplace-Specific Signal 5: Container Hint Match Bonus (25 pts)
        # =====================================================================
        # Strongest marketplace signal - adds 25 pts when detected type matches
        # container type (e.g., skill inside skills/)
        # NOTE: Only give full bonus if type was NOT inferred from container (already got 12 pts)
        if container_hint is not None and artifact_type is not None:
            if (
                artifact_type == container_hint
                and breakdown["container_hint_score"] == 0
            ):
                # Type matches container - full bonus
                total_score += self.config.container_hint_weight
                breakdown["container_hint_score"] = self.config.container_hint_weight
                reasons.append(
                    f"Type matches container hint ({container_hint.value}) "
                    f"(+{self.config.container_hint_weight})"
                )

        # =====================================================================
        # Marketplace-Specific Signal 6: Frontmatter Type Detection
        # =====================================================================
        if file_contents:
            _, _, frontmatter_type = self._score_manifest_with_content(
                path, siblings, file_contents
            )
            if frontmatter_type:
                frontmatter_artifact_type = self._frontmatter_type_to_artifact_type(
                    frontmatter_type
                )
                if frontmatter_artifact_type:
                    total_score += self.config.frontmatter_type_weight
                    breakdown["frontmatter_type_score"] = (
                        self.config.frontmatter_type_weight
                    )
                    reasons.append(
                        f"Frontmatter type: {frontmatter_type} "
                        f"(+{self.config.frontmatter_type_weight})"
                    )
                    # Frontmatter type overrides other signals
                    if artifact_type and artifact_type != frontmatter_artifact_type:
                        reasons.append(
                            f"Frontmatter type '{frontmatter_type}' overrides "
                            f"directory-based type '{artifact_type.value}'"
                        )
                    artifact_type = frontmatter_artifact_type

        # =====================================================================
        # Depth Penalty (marketplace-specific depth handling)
        # =====================================================================
        # Penalize deeply nested paths to prefer artifacts at shallower depths
        # HOWEVER: Reduce penalty 50% when inside typed containers (container_hint set)
        # This avoids unfairly penalizing properly organized nested artifacts like:
        #   commands/dev/subgroup/my-cmd (depth=4 but properly organized)
        # vs unorganized deeply nested paths without container context
        depth_penalty = self._calculate_depth_penalty(path, root_hint, container_hint)
        total_score -= depth_penalty
        breakdown["depth_penalty"] = depth_penalty
        if depth_penalty > 0:
            reasons.append(f"Depth penalty (-{depth_penalty})")

        # Ensure score is non-negative
        total_score = max(0, total_score)
        breakdown["raw_total"] = total_score

        logger.debug(
            "Marketplace confidence for '%s': type=%s, raw_score=%d, breakdown=%s",
            path,
            artifact_type.value if artifact_type else None,
            total_score,
            breakdown,
        )

        return artifact_type, total_score, reasons, breakdown

    def matches_to_artifacts(
        self,
        matches: List[HeuristicMatch],
        base_url: str,
        detected_sha: Optional[str] = None,
        ref: str = "main",
    ) -> List[DetectedArtifact]:
        """Convert heuristic matches to detected artifact objects.

        Filters out low-confidence matches and deduplicates.

        Args:
            matches: List of heuristic matches
            base_url: Base URL for repository
            detected_sha: Git commit SHA for version tracking
            ref: Branch/tag/SHA for upstream URL construction

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
            upstream_url = f"{base_url.rstrip('/')}/tree/{ref}/{match.path}"

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
        matches, base_url=repo_url, detected_sha=detected_sha, ref=ref
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
