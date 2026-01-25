"""Clone target configuration for efficient artifact indexing.

This module provides the CloneTarget dataclass which stores pre-computed
clone configuration for rapid re-indexing of artifact sources. The configuration
determines the optimal strategy for fetching artifact metadata based on the
number and distribution of artifacts in a repository.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Literal, Optional

if TYPE_CHECKING:
    from skillmeat.api.schemas.marketplace import DetectedArtifact
    from skillmeat.cache.models import MarketplaceSource


# Manifest file patterns for each artifact type
# Order indicates priority - first match wins
MANIFEST_PATTERNS: dict[str, list[str]] = {
    "skill": ["SKILL.md"],  # Skills use markdown with YAML frontmatter
    "command": [
        "command.yaml",
        "command.yml",
        "COMMAND.md",
    ],  # YAML preferred, MD fallback
    "agent": ["agent.yaml", "agent.yml", "AGENT.md"],  # YAML preferred, MD fallback
    "hook": ["hook.yaml", "hook.yml"],  # Hooks are always YAML
    "mcp": ["mcp.json", "package.json"],  # mcp.json preferred, package.json fallback
}


@dataclass
class CloneTarget:
    """Pre-computed clone configuration for efficient artifact re-indexing.

    Stores the optimal cloning strategy and patterns computed during initial
    source detection. This enables rapid re-indexing without recomputing
    the strategy each time.

    Strategies:
        api: Use GitHub API for small operations (<3 artifacts).
            Most efficient for tiny repos; avoids clone overhead entirely.
            Makes one API call per manifest file.

        sparse_manifest: Clone only manifest files for medium operations (3-20 artifacts).
            Fetches individual manifest files (SKILL.md, command.yaml, etc.)
            via sparse checkout. Patterns target specific files.
            Example: [".claude/skills/foo/SKILL.md", ".claude/skills/bar/SKILL.md"]

        sparse_directory: Clone artifact directories for large operations (>20 artifacts)
            or when deep indexing is needed. Clones the common ancestor directory
            containing all artifacts, never the entire repository.
            Example: [".claude/**"] for artifacts in .claude/skills/, .claude/commands/

    Attributes:
        strategy: The indexing strategy to use ("api", "sparse_manifest", "sparse_directory")
        sparse_patterns: Sparse-checkout patterns for git clone operations.
            For sparse_manifest: specific file paths like ".claude/skills/foo/SKILL.md"
            For sparse_directory: glob patterns like ".claude/**"
            Empty for api strategy.
        artifacts_root: Common ancestor path of all artifacts, if one exists.
            Example: ".claude/skills" if all artifacts are under that path.
            None if artifacts are scattered across multiple directories.
        artifact_paths: List of paths to all detected artifacts.
            Example: [".claude/skills/foo", ".claude/skills/bar"]
        tree_sha: SHA of the repository tree when this configuration was computed.
            Used for cache invalidation - if tree SHA changes, recompute.
        computed_at: Timestamp (with timezone) when this configuration was computed.
    """

    strategy: Literal["api", "sparse_manifest", "sparse_directory"]
    sparse_patterns: List[str] = field(default_factory=list)
    artifacts_root: Optional[str] = None
    artifact_paths: List[str] = field(default_factory=list)
    tree_sha: str = ""
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate strategy is one of the allowed values."""
        valid_strategies = ("api", "sparse_manifest", "sparse_directory")
        if self.strategy not in valid_strategies:
            raise ValueError(
                f"strategy must be one of {valid_strategies}, got '{self.strategy}'"
            )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation with datetime as ISO format string.
        """
        return {
            "strategy": self.strategy,
            "sparse_patterns": self.sparse_patterns,
            "artifacts_root": self.artifacts_root,
            "artifact_paths": self.artifact_paths,
            "tree_sha": self.tree_sha,
            "computed_at": self.computed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> CloneTarget:
        """Construct CloneTarget from a dictionary.

        Args:
            data: Dictionary containing CloneTarget fields.
                The computed_at field should be an ISO format datetime string.

        Returns:
            CloneTarget instance.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If strategy is invalid or datetime parsing fails.
        """
        computed_at = data.get("computed_at")
        if computed_at is not None:
            if isinstance(computed_at, str):
                # Handle ISO format with potential 'Z' suffix
                computed_at = datetime.fromisoformat(computed_at.replace("Z", "+00:00"))
            elif not isinstance(computed_at, datetime):
                raise ValueError(
                    f"computed_at must be a datetime or ISO string, got {type(computed_at)}"
                )
        else:
            computed_at = datetime.now(timezone.utc)

        return cls(
            strategy=data["strategy"],
            sparse_patterns=data.get("sparse_patterns", []),
            artifacts_root=data.get("artifacts_root"),
            artifact_paths=data.get("artifact_paths", []),
            tree_sha=data.get("tree_sha", ""),
            computed_at=computed_at,
        )

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation of this CloneTarget.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> CloneTarget:
        """Deserialize from JSON string.

        Args:
            json_str: JSON string containing CloneTarget data.

        Returns:
            CloneTarget instance.

        Raises:
            json.JSONDecodeError: If JSON is malformed.
            KeyError: If required fields are missing.
            ValueError: If strategy is invalid or datetime parsing fails.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


def should_reindex(source: "MarketplaceSource", current_tree_sha: str) -> bool:
    """Determine if source needs re-indexing based on tree SHA comparison.

    Compares the cached tree SHA from the source's CloneTarget against the
    current repository tree SHA to determine if re-indexing is necessary.
    This enables skipping expensive git clones when the repository tree
    has not changed since the last indexing operation.

    Args:
        source: MarketplaceSource with cached clone_target property.
            The clone_target attribute is a deserialized CloneTarget instance
            containing the tree_sha from the last indexing operation.
        current_tree_sha: Current SHA of the repository tree from GitHub API.
            Obtained via GitHub API call to get latest tree state.

    Returns:
        True if re-indexing is needed (first index or tree changed).
        False if tree is unchanged and cached data is still valid.

    Examples:
        >>> # First indexing (no cached clone_target)
        >>> should_reindex(source_without_cache, "abc123")
        True

        >>> # Tree unchanged
        >>> source.clone_target.tree_sha
        'abc123'
        >>> should_reindex(source, "abc123")
        False

        >>> # Tree changed
        >>> source.clone_target.tree_sha
        'abc123'
        >>> should_reindex(source, "def456")
        True
    """
    # If no cached clone_target exists, this is the first indexing
    if source.clone_target is None:
        return True

    # Compare cached tree SHA with current tree SHA
    if source.clone_target.tree_sha != current_tree_sha:
        return True

    # Tree unchanged - skip expensive clone
    return False


def compute_clone_metadata(
    artifacts: List["DetectedArtifact"],
    tree_sha: str,
) -> dict:
    """Compute clone configuration metadata from detected artifacts.

    Analyzes the distribution of artifacts within a repository to determine
    the optimal cloning strategy and generate appropriate sparse checkout patterns.

    Args:
        artifacts: List of detected artifacts with path and artifact_type attributes.
        tree_sha: SHA of the repository tree for cache invalidation.

    Returns:
        Dictionary suitable for constructing CloneTarget:
            - artifacts_root: Common ancestor path of all artifacts, or None if
              no common path exists (scattered artifacts) or empty list.
            - artifact_paths: List of paths to all detected artifacts.
            - sparse_patterns: Patterns for sparse checkout, format depends on
              intended strategy:
                - For sparse_manifest: specific file paths like
                  ".claude/skills/foo/SKILL.md"
                - For sparse_directory: glob patterns like ".claude/skills/**"

    Examples:
        >>> # Empty list
        >>> compute_clone_metadata([], "abc123")
        {'artifacts_root': None, 'artifact_paths': [], 'sparse_patterns': []}

        >>> # Single artifact
        >>> compute_clone_metadata([artifact], "abc123")  # artifact.path = ".claude/skills/foo"
        {'artifacts_root': '.claude/skills', 'artifact_paths': ['.claude/skills/foo'], ...}

        >>> # Multiple artifacts with common root
        >>> compute_clone_metadata([a1, a2], "abc123")
        # a1.path = ".claude/skills/foo", a2.path = ".claude/skills/bar"
        {'artifacts_root': '.claude/skills', ...}

        >>> # Scattered artifacts (no common root)
        >>> compute_clone_metadata([a1, a2], "abc123")
        # a1.path = ".claude/skills/foo", a2.path = "tools/bar"
        {'artifacts_root': None, ...}
    """
    # Handle empty artifact list
    if not artifacts:
        return {
            "artifacts_root": None,
            "artifact_paths": [],
            "sparse_patterns": [],
        }

    # Extract artifact paths
    artifact_paths = [artifact.path for artifact in artifacts]

    # Compute common ancestor path
    artifacts_root: Optional[str] = None

    if len(artifacts) == 1:
        # Single artifact: use parent directory as root
        parent = os.path.dirname(artifact_paths[0])
        artifacts_root = parent if parent else None
    else:
        # Multiple artifacts: find common path
        try:
            # os.path.commonpath raises ValueError if paths have no common prefix
            # or if mixing absolute and relative paths
            common = os.path.commonpath(artifact_paths)
            # Only use if it's a meaningful common directory (not empty string)
            # and not a file path itself (should be a directory)
            if common:
                # Check if common path is a directory (doesn't end with a file extension pattern)
                # or is one of the artifact paths (meaning artifacts are at the same level)
                if common in artifact_paths:
                    # Common path is an artifact itself, use its parent
                    parent = os.path.dirname(common)
                    artifacts_root = parent if parent else None
                else:
                    artifacts_root = common
        except ValueError:
            # No common path (e.g., different root directories)
            artifacts_root = None

    # Generate sparse patterns
    sparse_patterns: List[str] = []

    for artifact in artifacts:
        artifact_type = artifact.artifact_type
        manifest_files = MANIFEST_PATTERNS.get(artifact_type)

        if manifest_files:
            # Use first manifest pattern (highest priority) for sparse_manifest strategy
            manifest_file = manifest_files[0]
            # Create specific manifest path pattern for sparse_manifest strategy
            manifest_path = os.path.join(artifact.path, manifest_file)
            # Normalize path separators for consistency
            manifest_path = manifest_path.replace(os.sep, "/")
            sparse_patterns.append(manifest_path)
        else:
            # Unknown artifact type: include entire artifact directory
            dir_pattern = artifact.path.replace(os.sep, "/")
            if not dir_pattern.endswith("/**"):
                dir_pattern = f"{dir_pattern}/**"
            sparse_patterns.append(dir_pattern)

    return {
        "artifacts_root": artifacts_root,
        "artifact_paths": artifact_paths,
        "sparse_patterns": sparse_patterns,
    }


def select_indexing_strategy(
    source: "MarketplaceSource",
    artifacts: List["DetectedArtifact"],
) -> Literal["api", "sparse_manifest", "sparse_directory"]:
    """Select the optimal indexing strategy based on artifact count and distribution.

    Determines whether to use direct GitHub API calls, sparse manifest cloning,
    or sparse directory cloning based on the number of artifacts and their
    layout within the repository.

    Strategy Selection Logic:
        - <3 artifacts: 'api' - Clone overhead not worth it for small counts.
          Direct API calls are more efficient.
        - 3-20 artifacts: 'sparse_manifest' - Clone only manifest files
          (SKILL.md, command.yaml, etc.) for moderate efficiency gains.
        - >20 artifacts with common root: 'sparse_directory' - Clone the
          common ancestor directory containing all artifacts.
        - >20 artifacts scattered: 'sparse_manifest' - Fall back to manifest
          cloning as directory cloning would fetch too much.

    Args:
        source: MarketplaceSource being indexed. Reserved for future use
            (e.g., force overrides, source-specific configuration).
        artifacts: List of detected artifacts to index.

    Returns:
        One of:
            - 'api': Use GitHub API for each artifact (small repos)
            - 'sparse_manifest': Clone only manifest files (medium repos)
            - 'sparse_directory': Clone common artifact directory (large repos)

    Note:
        This function never returns a strategy that would clone the full
        repository. Safety is prioritized over optimization.

    Examples:
        >>> select_indexing_strategy(source, [])  # Empty
        'api'

        >>> select_indexing_strategy(source, [a1, a2])  # 2 artifacts
        'api'

        >>> select_indexing_strategy(source, artifacts_3_to_20)  # 3-20 artifacts
        'sparse_manifest'

        >>> select_indexing_strategy(source, artifacts_25_common_root)  # >20, common root
        'sparse_directory'

        >>> select_indexing_strategy(source, artifacts_25_scattered)  # >20, no common root
        'sparse_manifest'
    """
    # Note: source parameter is reserved for future use (force overrides, etc.)
    # Currently unused but part of the function signature for extensibility
    _ = source

    artifact_count = len(artifacts)

    # Small repos: API is more efficient than clone overhead
    if artifact_count < 3:
        return "api"

    # Medium repos: Sparse manifest cloning provides good efficiency
    if artifact_count <= 20:
        return "sparse_manifest"

    # Large repos: Check if artifacts have a common root for directory cloning
    # Use empty tree_sha since we only need artifacts_root from the metadata
    metadata = compute_clone_metadata(artifacts, tree_sha="")
    artifacts_root = metadata.get("artifacts_root")

    if artifacts_root:
        # Artifacts share a common ancestor - directory cloning is efficient
        return "sparse_directory"
    else:
        # Artifacts are scattered - manifest cloning is safer
        # Directory cloning would fetch too much unrelated content
        return "sparse_manifest"


def get_changed_artifacts(
    cached_target: Optional[CloneTarget],
    current_artifacts: List["DetectedArtifact"],
) -> List["DetectedArtifact"]:
    """Identify artifacts that changed since last indexing.

    Compares the cached artifact paths from a previous indexing run against
    the currently detected artifacts to determine which artifacts need
    re-indexing. This enables incremental updates by skipping artifacts
    that haven't changed.

    The comparison is based on artifact paths only. We cannot detect file
    content changes without cloning, so tree_sha comparison (via should_reindex)
    handles that case at a higher level.

    Args:
        cached_target: Previously cached CloneTarget from last indexing run.
            None indicates this is the first-time indexing.
        current_artifacts: Currently detected artifacts from the repository.

    Returns:
        List of artifacts that are new or potentially modified and need
        re-indexing. For first-time indexing, returns all current_artifacts.

    Examples:
        >>> # First-time indexing (no cache)
        >>> get_changed_artifacts(None, [a1, a2])
        [a1, a2]  # All artifacts are new

        >>> # No changes (all artifacts cached)
        >>> cached = CloneTarget(artifact_paths=[".claude/skills/foo", ".claude/skills/bar"], ...)
        >>> current = [DetectedArtifact(path=".claude/skills/foo"), DetectedArtifact(path=".claude/skills/bar")]
        >>> get_changed_artifacts(cached, current)
        []  # No new artifacts

        >>> # New artifact added
        >>> cached = CloneTarget(artifact_paths=[".claude/skills/foo", ".claude/skills/bar"], ...)
        >>> current = [
        ...     DetectedArtifact(path=".claude/skills/foo"),
        ...     DetectedArtifact(path=".claude/skills/bar"),
        ...     DetectedArtifact(path=".claude/skills/baz")
        ... ]
        >>> get_changed_artifacts(cached, current)
        [DetectedArtifact(path=".claude/skills/baz")]  # Only the new artifact

        >>> # Artifact removed (returned list will be empty)
        >>> cached = CloneTarget(artifact_paths=[".claude/skills/foo", ".claude/skills/bar"], ...)
        >>> current = [DetectedArtifact(path=".claude/skills/foo")]
        >>> get_changed_artifacts(cached, current)
        []  # foo was already indexed (bar's removal doesn't create "changed" artifacts)
    """
    # First-time indexing - all artifacts are new
    if cached_target is None:
        return current_artifacts

    # Build set of cached paths for O(1) lookup
    cached_paths = set(cached_target.artifact_paths)

    # Find artifacts not in cache (new artifacts)
    changed: List["DetectedArtifact"] = []
    for artifact in current_artifacts:
        if artifact.path not in cached_paths:
            changed.append(artifact)

    return changed


def get_sparse_checkout_patterns(
    strategy: Literal["api", "sparse_manifest", "sparse_directory"],
    artifacts: List["DetectedArtifact"],
    artifacts_root: Optional[str],
) -> List[str]:
    """Generate sparse-checkout patterns for git based on the indexing strategy.

    Produces git sparse-checkout patterns optimized for each strategy. These
    patterns are passed to `git sparse-checkout set` to limit which files
    are fetched during clone operations.

    Args:
        strategy: The indexing strategy determining pattern format.
            - "api": No cloning needed, returns empty list.
            - "sparse_manifest": Returns specific manifest file paths.
            - "sparse_directory": Returns directory glob patterns.
        artifacts: List of detected artifacts with path and artifact_type.
        artifacts_root: Common ancestor path of all artifacts, or None if
            artifacts are scattered across multiple directories.

    Returns:
        List of sparse-checkout patterns for git:
            - "api": Empty list (no cloning)
            - "sparse_manifest": Specific manifest paths like
              [".claude/skills/foo/SKILL.md", ".claude/skills/bar/SKILL.md"]
            - "sparse_directory": Directory globs like [".claude/**"]

    Safety:
        This function never returns patterns that would clone the full
        repository (e.g., "**" alone). If artifacts_root is None for
        sparse_directory strategy, it falls back to sparse_manifest patterns.

    Examples:
        >>> # API strategy - no cloning needed
        >>> get_sparse_checkout_patterns("api", artifacts, ".claude/skills")
        []

        >>> # Sparse manifest - individual manifest files
        >>> get_sparse_checkout_patterns("sparse_manifest", artifacts, ".claude/skills")
        ['.claude/skills/foo/SKILL.md', '.claude/skills/bar/command.yaml']

        >>> # Sparse directory with common root
        >>> get_sparse_checkout_patterns("sparse_directory", artifacts, ".claude/skills")
        ['.claude/skills/**']

        >>> # Sparse directory with multiple roots
        >>> get_sparse_checkout_patterns("sparse_directory", artifacts, None)
        ['.claude/skills/**', '.codex/agents/**']  # Falls back to per-root patterns

        >>> # Sparse directory fallback to manifest when no root
        >>> get_sparse_checkout_patterns("sparse_directory", scattered_artifacts, None)
        ['path/to/skill1/SKILL.md', 'other/path/agent/agent.yaml']
    """
    # API strategy: no cloning needed
    if strategy == "api":
        return []

    # Empty artifacts: nothing to clone
    if not artifacts:
        return []

    # Sparse manifest strategy: return individual manifest file paths
    if strategy == "sparse_manifest":
        return _generate_manifest_patterns(artifacts)

    # Sparse directory strategy
    if strategy == "sparse_directory":
        if artifacts_root is not None:
            # Single common root - return root/** pattern
            root_pattern = artifacts_root.replace(os.sep, "/")
            if not root_pattern.endswith("/**"):
                root_pattern = f"{root_pattern}/**"
            return [root_pattern]

        # No common root - check for multiple distinct roots
        roots = _find_artifact_roots(artifacts)

        if roots:
            # Multiple distinct roots - return pattern for each
            patterns = []
            for root in roots:
                root_pattern = root.replace(os.sep, "/")
                if not root_pattern.endswith("/**"):
                    root_pattern = f"{root_pattern}/**"
                patterns.append(root_pattern)
            return patterns

        # Scattered artifacts with no identifiable roots - fall back to manifest patterns
        # This is safer than generating overly broad patterns
        return _generate_manifest_patterns(artifacts)

    # Unknown strategy (should not happen due to type hints)
    return []


def get_deep_sparse_patterns(artifacts: List["DetectedArtifact"]) -> List[str]:
    """Generate patterns for full artifact directory clone (deep indexing).

    Unlike get_sparse_checkout_patterns() which returns only manifest files,
    this returns patterns that clone entire artifact directories for deep
    content indexing.

    Args:
        artifacts: List of detected artifacts with path attribute.

    Returns:
        List of sparse-checkout patterns like ['{artifact.path}/**' for each artifact].
        These patterns clone all files in each artifact's directory.

    Example:
        >>> artifacts = [DetectedArtifact(path=".claude/skills/foo"), ...]
        >>> get_deep_sparse_patterns(artifacts)
        ['.claude/skills/foo/**', '.claude/skills/bar/**']
    """
    # Handle empty list case
    if not artifacts:
        return []

    patterns: List[str] = []
    seen: set[str] = set()

    for artifact in artifacts:
        # Normalize path separators to forward slashes (for both Unix and Windows)
        path = artifact.path.replace("\\", "/").replace(os.sep, "/")

        # Generate directory pattern
        if not path.endswith("/**"):
            dir_pattern = f"{path}/**"
        else:
            dir_pattern = path

        # Deduplicate patterns
        if dir_pattern not in seen:
            patterns.append(dir_pattern)
            seen.add(dir_pattern)

    return patterns


def _generate_manifest_patterns(artifacts: List["DetectedArtifact"]) -> List[str]:
    """Generate sparse-checkout patterns for individual manifest files.

    For each artifact, generates a pattern pointing to its manifest file
    based on MANIFEST_PATTERNS. Uses the highest priority manifest file
    for each artifact type.

    Args:
        artifacts: List of detected artifacts with path and artifact_type.

    Returns:
        List of specific manifest file paths, normalized with forward slashes.
        Example: [".claude/skills/foo/SKILL.md", ".claude/commands/bar/command.yaml"]
    """
    patterns: List[str] = []

    for artifact in artifacts:
        artifact_type = artifact.artifact_type
        manifest_files = MANIFEST_PATTERNS.get(artifact_type)

        if manifest_files:
            # Use first manifest pattern (highest priority)
            manifest_file = manifest_files[0]
            manifest_path = os.path.join(artifact.path, manifest_file)
            # Normalize to forward slashes for git
            manifest_path = manifest_path.replace(os.sep, "/")
            patterns.append(manifest_path)
        else:
            # Unknown artifact type: include entire artifact directory
            dir_pattern = artifact.path.replace(os.sep, "/")
            if not dir_pattern.endswith("/**"):
                dir_pattern = f"{dir_pattern}/**"
            patterns.append(dir_pattern)

    return patterns


def _find_artifact_roots(artifacts: List["DetectedArtifact"]) -> List[str]:
    """Find distinct root directories containing artifacts.

    Groups artifacts by their top-level container directories and returns
    the unique roots. This handles cases where artifacts are spread across
    multiple distinct directories (e.g., .claude/ and .codex/).

    Args:
        artifacts: List of detected artifacts with path attribute.

    Returns:
        List of distinct root directory paths, or empty list if artifacts
        have no identifiable common structure.
        Example: [".claude/skills", ".codex/agents"]
    """
    if not artifacts:
        return []

    # Group artifacts by their parent directories
    parent_dirs: dict[str, List[str]] = {}

    for artifact in artifacts:
        path = artifact.path.replace(os.sep, "/")
        parts = path.split("/")

        # Find the container directory (typically 2 levels deep like .claude/skills)
        if len(parts) >= 2:
            # Use first two directory levels as root identifier
            root = "/".join(parts[:2])
            if root not in parent_dirs:
                parent_dirs[root] = []
            parent_dirs[root].append(path)
        elif len(parts) == 1:
            # Single-level path - use as-is
            root = parts[0]
            if root not in parent_dirs:
                parent_dirs[root] = []
            parent_dirs[root].append(path)

    # Return roots that have at least one artifact
    roots = [root for root in parent_dirs.keys() if parent_dirs[root]]

    # Sort for deterministic output
    return sorted(roots)
