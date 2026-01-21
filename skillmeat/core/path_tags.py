"""Path-based tag extraction dataclasses for SkillMeat.

Provides core dataclasses for extracting semantic tags from artifact paths.
Path segments like "anthropics/skills/data-processing/csv-parser" can be
transformed into meaningful tags like ["data-processing", "csv-parser"].

This module contains:
- PathTagConfig: Configuration for path-based tag extraction
- ExtractedSegment: A single extracted path segment with status

Example Usage:
    >>> # Default config
    >>> config = PathTagConfig.defaults()
    >>> config.max_depth
    3

    >>> # Custom config from JSON
    >>> config = PathTagConfig.from_json('{"enabled": true, "max_depth": 2}')
    >>> config.max_depth
    2

    >>> # Extracted segment
    >>> seg = ExtractedSegment(
    ...     segment="05-data-ai",
    ...     normalized="data-ai",
    ...     status="pending"
    ... )
    >>> seg.normalized
    'data-ai'
"""

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Literal, Optional


# ===========================
# Default Configuration Values
# ===========================

# Default exclude patterns for common directories and pure numbers
DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    r"^\d+$",  # Pure numbers (e.g., "01", "123")
    r"^(src|lib|test|docs|examples|__pycache__|node_modules)$",  # Common code directories
    # Filesystem paths that are not semantically meaningful
    r"^(Users|home|var|tmp|opt|usr|etc|mnt|dev|bin|sbin)$",  # Unix system paths
    r"^(homelab|development|workspace|projects|repos|code)$",  # Common dev directories
    r"^(\.claude|\.git|\.github|\.vscode|\.idea)$",  # Hidden/config directories
    # Short generic names (2 chars or less, except abbreviations)
    r"^[a-z]{1,2}$",  # Single/double letter segments
]


# ===========================
# PathTagConfig Dataclass
# ===========================


@dataclass
class PathTagConfig:
    """Configuration for path-based tag extraction.

    Controls how path segments are analyzed and transformed into tags.
    Supports JSON serialization for storage and transfer.

    Attributes:
        enabled: Whether path-based tag extraction is enabled.
        skip_segments: Indices of path segments to skip (e.g., [0] to skip root).
        max_depth: Maximum number of segments to extract as tags.
        normalize_numbers: Remove numeric prefixes like "05-" or "01_".
        exclude_patterns: Regex patterns for segments to exclude.

    Example:
        >>> # Create with defaults
        >>> config = PathTagConfig.defaults()
        >>> config.enabled
        True
        >>> config.max_depth
        3

        >>> # Custom config
        >>> config = PathTagConfig(
        ...     enabled=True,
        ...     skip_segments=[0, 1],
        ...     max_depth=2,
        ...     normalize_numbers=True,
        ...     exclude_patterns=[r"^test$"]
        ... )

        >>> # JSON round-trip
        >>> json_str = config.to_json()
        >>> restored = PathTagConfig.from_json(json_str)
        >>> restored.max_depth == config.max_depth
        True
    """

    enabled: bool = True
    skip_segments: list[int] = field(default_factory=list)
    max_depth: int = 3
    normalize_numbers: bool = True
    exclude_patterns: list[str] = field(default_factory=list)

    @classmethod
    def defaults(cls) -> "PathTagConfig":
        """Create instance with recommended default values.

        Returns:
            PathTagConfig with sensible defaults including standard
            exclude patterns for common directories.

        Example:
            >>> config = PathTagConfig.defaults()
            >>> config.enabled
            True
            >>> config.max_depth
            3
            >>> len(config.exclude_patterns) > 0
            True
        """
        return cls(
            enabled=True,
            skip_segments=[],
            max_depth=3,
            normalize_numbers=True,
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS.copy(),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "PathTagConfig":
        """Deserialize PathTagConfig from JSON string.

        Merges provided JSON values with defaults - any fields not specified
        in the JSON will use default values.

        Args:
            json_str: JSON string containing config fields.

        Returns:
            PathTagConfig instance with values from JSON merged with defaults.

        Raises:
            ValueError: If JSON is malformed or contains invalid field types.

        Example:
            >>> config = PathTagConfig.from_json('{"max_depth": 5}')
            >>> config.max_depth
            5
            >>> config.enabled  # Uses default
            True

            >>> config = PathTagConfig.from_json('{"enabled": false, "skip_segments": [0, 1]}')
            >>> config.enabled
            False
            >>> config.skip_segments
            [0, 1]
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"JSON must be an object/dict, got {type(data).__name__}")

        # Start with defaults and override with provided values
        defaults = cls.defaults()

        # Validate and extract each field
        enabled = data.get("enabled", defaults.enabled)
        if not isinstance(enabled, bool):
            raise ValueError(
                f"'enabled' must be a boolean, got {type(enabled).__name__}"
            )

        skip_segments = data.get("skip_segments", defaults.skip_segments)
        if not isinstance(skip_segments, list):
            raise ValueError(
                f"'skip_segments' must be a list, got {type(skip_segments).__name__}"
            )
        if not all(isinstance(x, int) for x in skip_segments):
            raise ValueError("'skip_segments' must contain only integers")

        max_depth = data.get("max_depth", defaults.max_depth)
        if not isinstance(max_depth, int):
            raise ValueError(
                f"'max_depth' must be an integer, got {type(max_depth).__name__}"
            )
        if max_depth < 1:
            raise ValueError("'max_depth' must be at least 1")

        normalize_numbers = data.get("normalize_numbers", defaults.normalize_numbers)
        if not isinstance(normalize_numbers, bool):
            raise ValueError(
                f"'normalize_numbers' must be a boolean, got {type(normalize_numbers).__name__}"
            )

        exclude_patterns = data.get("exclude_patterns", defaults.exclude_patterns)
        if not isinstance(exclude_patterns, list):
            raise ValueError(
                f"'exclude_patterns' must be a list, got {type(exclude_patterns).__name__}"
            )
        if not all(isinstance(x, str) for x in exclude_patterns):
            raise ValueError("'exclude_patterns' must contain only strings")

        return cls(
            enabled=enabled,
            skip_segments=skip_segments,
            max_depth=max_depth,
            normalize_numbers=normalize_numbers,
            exclude_patterns=exclude_patterns,
        )

    def to_json(self) -> str:
        """Serialize PathTagConfig to JSON string.

        Returns:
            JSON string representation of this config.

        Example:
            >>> config = PathTagConfig(enabled=True, max_depth=5)
            >>> json_str = config.to_json()
            >>> '"max_depth": 5' in json_str
            True
        """
        return json.dumps(asdict(self), indent=2)


# ===========================
# ExtractedSegment Dataclass
# ===========================


# Status literal type for extracted segments
SegmentStatus = Literal["pending", "approved", "rejected", "excluded"]


@dataclass
class ExtractedSegment:
    """A single extracted path segment with normalization status.

    Represents a segment extracted from an artifact path, tracking both
    the original value and normalized form along with approval status.

    Attributes:
        segment: Original segment value from path.
        normalized: Value after normalization rules applied.
        status: Processing status - one of "pending", "approved",
            "rejected", or "excluded".
        reason: Why segment was excluded or rejected (if applicable).

    Example:
        >>> seg = ExtractedSegment(
        ...     segment="05-data-ai",
        ...     normalized="data-ai",
        ...     status="pending"
        ... )
        >>> seg.segment
        '05-data-ai'
        >>> seg.normalized
        'data-ai'
        >>> seg.status
        'pending'

        >>> # Excluded segment with reason
        >>> seg = ExtractedSegment(
        ...     segment="node_modules",
        ...     normalized="node_modules",
        ...     status="excluded",
        ...     reason="Matched exclude pattern: common directories"
        ... )
        >>> seg.reason
        'Matched exclude pattern: common directories'
    """

    segment: str
    normalized: str
    status: SegmentStatus
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate status value after initialization."""
        valid_statuses = {"pending", "approved", "rejected", "excluded"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )

    def to_dict(self) -> dict[str, Optional[str]]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with segment, normalized, status, and reason fields.

        Example:
            >>> seg = ExtractedSegment("foo", "foo", "pending")
            >>> seg.to_dict()
            {'segment': 'foo', 'normalized': 'foo', 'status': 'pending', 'reason': None}
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Optional[str]]) -> "ExtractedSegment":
        """Create ExtractedSegment from dictionary.

        Args:
            data: Dictionary with segment, normalized, status, and
                optional reason fields.

        Returns:
            ExtractedSegment instance.

        Raises:
            ValueError: If required fields are missing or invalid.

        Example:
            >>> data = {"segment": "foo", "normalized": "foo", "status": "pending"}
            >>> seg = ExtractedSegment.from_dict(data)
            >>> seg.segment
            'foo'
        """
        required_fields = ["segment", "normalized", "status"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: '{field_name}'")

        return cls(
            segment=str(data["segment"]),
            normalized=str(data["normalized"]),
            status=data["status"],  # type: ignore[arg-type]
            reason=data.get("reason"),
        )


# ===========================
# PathSegmentExtractor Class
# ===========================


class PathSegmentExtractor:
    """Extract and normalize path segments for tag generation.

    The extractor processes file paths to extract meaningful segments
    that can be used as tags. It applies normalization rules and
    filters based on configuration.

    Algorithm:
    1. Split path by '/' and remove filename (last segment)
    2. Apply skip_segments (remove first N segments)
    3. Apply max_depth (keep only first N segments after skip)
    4. For each remaining segment:
       - Normalize (apply normalize_numbers rules)
       - Check exclude_patterns regex
       - Assign status: 'excluded' if matched pattern, else 'pending'
    5. Return list of ExtractedSegment objects

    Example:
        >>> config = PathTagConfig.defaults()
        >>> extractor = PathSegmentExtractor(config)
        >>> result = extractor.extract("categories/05-data-ai/ai-engineer.md")
        >>> [s.normalized for s in result if s.status != "excluded"]
        ['categories', 'data-ai']

        >>> # With skip_segments
        >>> config = PathTagConfig(skip_segments=[0], max_depth=2)
        >>> extractor = PathSegmentExtractor(config)
        >>> result = extractor.extract("root/categories/05-data-ai/file.md")
        >>> [s.normalized for s in result]
        ['categories', '05-data-ai']
    """

    # Regex pattern for normalizing numeric prefixes (e.g., "05-data-ai" -> "data-ai")
    _NUMBER_PREFIX_PATTERN = re.compile(r"^(\d+)[-_](.+)$")

    def __init__(self, config: PathTagConfig | None = None) -> None:
        """Initialize extractor with optional config.

        Args:
            config: Configuration for extraction behavior. If None,
                uses PathTagConfig.defaults().

        Raises:
            ValueError: If any exclude_pattern is an invalid regex.

        Example:
            >>> extractor = PathSegmentExtractor()  # Uses defaults
            >>> extractor = PathSegmentExtractor(PathTagConfig(max_depth=5))
        """
        self._config = config if config is not None else PathTagConfig.defaults()
        self._compiled_patterns: list[re.Pattern[str]] = []

        # Pre-compile exclude patterns for performance
        for pattern in self._config.exclude_patterns:
            try:
                self._compiled_patterns.append(re.compile(pattern))
            except re.error as e:
                raise ValueError(
                    f"Invalid regex pattern '{pattern}': {e}. "
                    "Please provide a valid regular expression."
                ) from e

    @property
    def config(self) -> PathTagConfig:
        """Get the current configuration.

        Returns:
            The PathTagConfig used by this extractor.
        """
        return self._config

    def _normalize_segment(self, segment: str) -> str:
        """Normalize a segment by removing numeric prefixes if configured.

        Args:
            segment: The original path segment.

        Returns:
            Normalized segment with numeric prefix removed if applicable.

        Example:
            >>> extractor = PathSegmentExtractor(PathTagConfig(normalize_numbers=True))
            >>> extractor._normalize_segment("05-data-ai")
            'data-ai'
            >>> extractor._normalize_segment("01_foundations")
            'foundations'
            >>> extractor._normalize_segment("v1.2")
            'v1.2'
        """
        if not self._config.normalize_numbers:
            return segment

        match = self._NUMBER_PREFIX_PATTERN.match(segment)
        if match:
            return match.group(2)
        return segment

    def _check_exclusion(self, normalized: str) -> tuple[bool, str | None]:
        """Check if a normalized segment matches any exclude pattern.

        Args:
            normalized: The normalized segment value to check.

        Returns:
            Tuple of (is_excluded, reason). If excluded, reason contains
            the pattern that matched.

        Example:
            >>> extractor = PathSegmentExtractor()
            >>> extractor._check_exclusion("node_modules")
            (True, "Matched exclude pattern: '^(src|lib|test|docs|examples|__pycache__|node_modules)$'")
            >>> extractor._check_exclusion("my-feature")
            (False, None)
        """
        for compiled, pattern_str in zip(
            self._compiled_patterns, self._config.exclude_patterns
        ):
            if compiled.search(normalized):
                return True, f"Matched exclude pattern: '{pattern_str}'"
        return False, None

    def extract(self, path: str) -> list[ExtractedSegment]:
        """Extract segments from path according to config rules.

        Processes the given path to extract meaningful directory segments,
        applying normalization and exclusion rules from the configuration.

        Args:
            path: File path to extract segments from. Can use forward
                slashes on all platforms.

        Returns:
            List of ExtractedSegment objects, each with original segment,
            normalized value, and status ('pending' or 'excluded').

        Example:
            >>> config = PathTagConfig.defaults()
            >>> extractor = PathSegmentExtractor(config)

            >>> # Basic extraction
            >>> result = extractor.extract("categories/05-data-ai/ai-engineer.md")
            >>> [(s.segment, s.normalized, s.status) for s in result]
            [('categories', 'categories', 'pending'), ('05-data-ai', 'data-ai', 'pending')]

            >>> # Empty path
            >>> extractor.extract("")
            []

            >>> # Single segment (just filename)
            >>> extractor.extract("file.md")
            []

            >>> # With exclusions
            >>> result = extractor.extract("src/lib/my-feature/file.md")
            >>> [s.status for s in result]
            ['excluded', 'excluded', 'pending']
        """
        # Handle empty path
        if not path:
            return []

        # Handle max_depth=0 edge case
        if self._config.max_depth == 0:
            return []

        # Split path and remove filename (last segment)
        segments = path.split("/")

        # Filter out empty segments (handles leading/trailing slashes)
        segments = [s for s in segments if s]

        # If only one segment or less, it's just a filename - no directories
        if len(segments) <= 1:
            return []

        # Remove the filename (last segment)
        directory_segments = segments[:-1]

        # Apply skip_segments (remove segments at specified indices)
        # Convert skip_segments to a set for O(1) lookup
        skip_indices = set(self._config.skip_segments)

        # Filter out skipped segments while preserving order
        filtered_segments = [
            seg for i, seg in enumerate(directory_segments) if i not in skip_indices
        ]

        # If no segments remain after skipping, return empty list
        if not filtered_segments:
            return []

        # Apply max_depth (keep only first N segments)
        filtered_segments = filtered_segments[: self._config.max_depth]

        # Process each segment
        result: list[ExtractedSegment] = []
        for segment in filtered_segments:
            # Normalize the segment
            normalized = self._normalize_segment(segment)

            # Check exclusion patterns
            is_excluded, reason = self._check_exclusion(normalized)

            # Create ExtractedSegment with appropriate status
            result.append(
                ExtractedSegment(
                    segment=segment,
                    normalized=normalized,
                    status="excluded" if is_excluded else "pending",
                    reason=reason,
                )
            )

        return result
