"""Heuristic detector for Claude Code artifacts in GitHub repositories.

Uses multi-signal scoring to identify potential artifacts with confidence levels.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set, Tuple

from skillmeat.api.schemas.marketplace import DetectedArtifact, HeuristicMatch

# Maximum raw score from all signals (10+20+5+15+15 = 65)
MAX_RAW_SCORE = 65


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
    ):
        """Initialize detector with optional custom configuration.

        Args:
            config: Optional custom detection configuration
            enable_frontmatter_detection: Enable frontmatter parsing for type detection
        """
        self.config = config or DetectionConfig()
        self.enable_frontmatter_detection = enable_frontmatter_detection

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

        matches: List[HeuristicMatch] = []

        # Analyze each directory
        for dir_path, files in dir_to_files.items():
            # Skip root directory
            if dir_path == ".":
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

            # Detect artifact type and score
            artifact_type, match_reasons, score_breakdown = self._score_directory(
                dir_path, files, root_hint, use_frontmatter
            )

            # Normalize raw score to 0-100 scale
            raw_score = score_breakdown["raw_total"]
            confidence_score = normalize_score(raw_score)

            # Only include if above threshold
            if confidence_score >= self.config.min_confidence:
                # Build complete breakdown dict with all signals and normalized score
                complete_breakdown = {
                    "dir_name_score": score_breakdown["dir_name_score"],
                    "manifest_score": score_breakdown["manifest_score"],
                    "extensions_score": score_breakdown["extensions_score"],
                    "parent_hint_score": score_breakdown["parent_hint_score"],
                    "frontmatter_score": score_breakdown["frontmatter_score"],
                    "depth_penalty": score_breakdown["depth_penalty"],
                    "raw_total": raw_score,
                    "normalized_score": confidence_score,
                }

                match = HeuristicMatch(
                    path=dir_path,
                    artifact_type=artifact_type.value if artifact_type else None,
                    confidence_score=confidence_score,
                    match_reasons=match_reasons,
                    dir_name_score=complete_breakdown["dir_name_score"],
                    manifest_score=complete_breakdown["manifest_score"],
                    extension_score=complete_breakdown["extensions_score"],
                    depth_penalty=complete_breakdown["depth_penalty"],
                    raw_score=raw_score,
                    breakdown=complete_breakdown,
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
    ) -> Tuple[Optional[ArtifactType], List[str], Dict[str, int]]:
        """Score a directory based on all available signals.

        Args:
            path: Directory path to score
            siblings: Set of filenames in this directory
            root_hint: Optional root hint for parent matching
            use_frontmatter: Enable frontmatter detection boost

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

        # Penalty: Directory depth
        depth_penalty = self._calculate_depth_penalty(path, root_hint)
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
        self, path: str, root_hint: Optional[str] = None
    ) -> int:
        """Calculate depth penalty for path.

        Args:
            path: Directory path
            root_hint: Optional root hint to adjust depth calculation

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

        return depth * self.config.depth_penalty

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
) -> List[DetectedArtifact]:
    """Convenience function to detect artifacts in a file tree.

    Args:
        file_tree: List of all file paths in the repository
        repo_url: GitHub repository URL
        ref: Branch/tag/SHA being scanned
        root_hint: Optional subdirectory to focus on
        detected_sha: Git commit SHA for version tracking
        enable_frontmatter_detection: Enable frontmatter parsing for type detection

    Returns:
        List of detected artifacts with confidence scores

    Example:
        >>> files = ["skills/my-skill/SKILL.md", "skills/my-skill/index.ts", "README.md"]
        >>> artifacts = detect_artifacts_in_tree(files, "https://github.com/user/repo")
        >>> print(artifacts[0].name, artifacts[0].confidence_score)
        my-skill 85
    """
    detector = HeuristicDetector(enable_frontmatter_detection=enable_frontmatter_detection)
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
