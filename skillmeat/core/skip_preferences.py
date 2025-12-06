"""Skip preferences schema for Smart Import & Discovery feature.

Provides Pydantic models for managing user skip preferences for artifacts
during discovery and import operations. Skip preferences are stored in
.claude/.skillmeat_skip_prefs.toml at the project level.

Schema Design:
- Per-project skip list storage
- Thread-safe file operations via manager (implemented in DIS-2.2)
- Collision-resistant artifact keys (type:name format)
- ISO 8601 datetime stamps for audit trails
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# Version compatibility for TOML parsing
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# ===========================
# Constants
# ===========================

# Default skip preferences file location (relative to project .claude/ directory)
SKIP_PREFS_FILENAME = ".skillmeat_skip_prefs.toml"

# Default skip preferences file path (will be .claude/.skillmeat_skip_prefs.toml)
# Manager will resolve this relative to project root
SKIP_PREFS_RELATIVE_PATH = f".claude/{SKIP_PREFS_FILENAME}"

# Current skip preferences file format version
SKIP_PREFS_VERSION = "1.0.0"


# ===========================
# Skip Preference Models
# ===========================


class SkipPreference(BaseModel):
    """Single skip preference entry for an artifact.

    Represents a user's decision to skip importing a specific artifact
    during discovery operations. Each skip is identified by a unique
    artifact_key in the format "type:name" to prevent collisions between
    different artifact types with the same name.

    Examples:
        - "skill:canvas-design" - Skip the canvas-design skill
        - "command:my-command" - Skip the my-command command
        - "agent:code-reviewer" - Skip the code-reviewer agent
    """

    artifact_key: str = Field(
        ...,
        description="Unique artifact identifier in format 'type:name'",
        examples=["skill:canvas-design", "command:my-command", "agent:code-reviewer"],
        min_length=3,  # Minimum: "a:b"
    )
    skip_reason: str = Field(
        ...,
        description="Human-readable reason for skipping this artifact",
        examples=[
            "Already in collection",
            "Not needed for this project",
            "Using alternative implementation",
            "Incompatible with project requirements",
        ],
        min_length=1,
    )
    added_date: datetime = Field(
        ...,
        description="When this skip preference was added (ISO 8601 format)",
        examples=["2025-12-04T10:00:00Z"],
    )

    @field_validator("artifact_key")
    @classmethod
    def validate_artifact_key(cls, v: str) -> str:
        """Validate artifact_key format is 'type:name'.

        Ensures the artifact key follows the standard format with exactly
        one colon separator and non-empty type and name components.

        Args:
            v: The artifact_key value to validate

        Returns:
            The validated artifact_key

        Raises:
            ValueError: If format is invalid
        """
        if ":" not in v:
            raise ValueError("artifact_key must be in format 'type:name'")

        parts = v.split(":", 1)  # Split on first colon only
        artifact_type, artifact_name = parts

        if not artifact_type or not artifact_name:
            raise ValueError("Both type and name must be non-empty in artifact_key")

        # Validate artifact type is one of the known types
        allowed_types = ["skill", "command", "agent", "hook", "mcp"]
        if artifact_type not in allowed_types:
            raise ValueError(
                f"artifact_type must be one of {allowed_types}, got '{artifact_type}'"
            )

        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "artifact_key": "skill:canvas-design",
                "skip_reason": "Already in collection",
                "added_date": "2025-12-04T10:00:00Z",
            }
        }
    }


class SkipPreferenceMetadata(BaseModel):
    """Metadata for the skip preferences file.

    Tracks file format version and last update timestamp for
    future compatibility and audit purposes.
    """

    version: str = Field(
        default=SKIP_PREFS_VERSION,
        description="Skip preferences file format version",
        examples=["1.0.0"],
    )
    last_updated: datetime = Field(
        ...,
        description="When the file was last modified (ISO 8601 format)",
        examples=["2025-12-04T10:00:00Z"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "version": "1.0.0",
                "last_updated": "2025-12-04T10:00:00Z",
            }
        }
    }


class SkipPreferenceFile(BaseModel):
    """Complete skip preferences file structure.

    Represents the entire .claude/.skillmeat_skip_prefs.toml file,
    including metadata and all skip entries. This model is used for
    both reading and writing the TOML file.

    The file structure maps to TOML as:

    ```toml
    [metadata]
    version = "1.0.0"
    last_updated = "2025-12-04T10:00:00Z"

    [[skips]]
    artifact_key = "skill:canvas-design"
    skip_reason = "Already in collection"
    added_date = "2025-12-04T10:00:00Z"

    [[skips]]
    artifact_key = "command:my-command"
    skip_reason = "Not needed for this project"
    added_date = "2025-12-04T11:00:00Z"
    ```

    Thread Safety:
        File operations using this model should be wrapped in appropriate
        locking mechanisms (to be implemented in manager class).
    """

    metadata: SkipPreferenceMetadata = Field(
        ...,
        description="File metadata including version and last update timestamp",
    )
    skips: List[SkipPreference] = Field(
        default_factory=list,
        description="List of skip preferences",
    )

    @field_validator("skips")
    @classmethod
    def validate_no_duplicates(cls, v: List[SkipPreference]) -> List[SkipPreference]:
        """Ensure no duplicate artifact_key entries.

        Args:
            v: List of skip preferences

        Returns:
            The validated list

        Raises:
            ValueError: If duplicate artifact_keys are found
        """
        artifact_keys = [skip.artifact_key for skip in v]
        duplicates = [key for key in artifact_keys if artifact_keys.count(key) > 1]

        if duplicates:
            unique_duplicates = list(set(duplicates))
            raise ValueError(
                f"Duplicate artifact_key entries found: {unique_duplicates}"
            )

        return v

    def get_skip_by_key(self, artifact_key: str) -> Optional[SkipPreference]:
        """Get skip preference by artifact_key.

        Args:
            artifact_key: The artifact key to look up (format: "type:name")

        Returns:
            The SkipPreference if found, None otherwise
        """
        for skip in self.skips:
            if skip.artifact_key == artifact_key:
                return skip
        return None

    def has_skip(self, artifact_key: str) -> bool:
        """Check if an artifact is in the skip list.

        Args:
            artifact_key: The artifact key to check (format: "type:name")

        Returns:
            True if artifact is skipped, False otherwise
        """
        return self.get_skip_by_key(artifact_key) is not None

    def add_skip(
        self,
        artifact_key: str,
        skip_reason: str,
        added_date: Optional[datetime] = None,
    ) -> SkipPreference:
        """Add a new skip preference.

        Args:
            artifact_key: The artifact key (format: "type:name")
            skip_reason: Human-readable reason for skipping
            added_date: When skip was added (defaults to now)

        Returns:
            The newly created SkipPreference

        Raises:
            ValueError: If artifact_key already exists in skip list
        """
        if self.has_skip(artifact_key):
            raise ValueError(f"Skip preference for '{artifact_key}' already exists")

        if added_date is None:
            added_date = datetime.utcnow()

        skip = SkipPreference(
            artifact_key=artifact_key,
            skip_reason=skip_reason,
            added_date=added_date,
        )
        self.skips.append(skip)
        self.metadata.last_updated = datetime.utcnow()

        return skip

    def remove_skip(self, artifact_key: str) -> bool:
        """Remove a skip preference by artifact_key.

        Args:
            artifact_key: The artifact key to remove (format: "type:name")

        Returns:
            True if skip was removed, False if not found
        """
        original_count = len(self.skips)
        self.skips = [skip for skip in self.skips if skip.artifact_key != artifact_key]

        if len(self.skips) < original_count:
            self.metadata.last_updated = datetime.utcnow()
            return True

        return False

    def clear_all(self) -> int:
        """Clear all skip preferences.

        Returns:
            Number of skips that were removed
        """
        count = len(self.skips)
        self.skips = []
        self.metadata.last_updated = datetime.utcnow()
        return count

    model_config = {
        "json_schema_extra": {
            "example": {
                "metadata": {
                    "version": "1.0.0",
                    "last_updated": "2025-12-04T10:00:00Z",
                },
                "skips": [
                    {
                        "artifact_key": "skill:canvas-design",
                        "skip_reason": "Already in collection",
                        "added_date": "2025-12-04T10:00:00Z",
                    },
                    {
                        "artifact_key": "command:my-command",
                        "skip_reason": "Not needed for this project",
                        "added_date": "2025-12-04T11:00:00Z",
                    },
                ],
            }
        }
    }

    @classmethod
    def create_empty(cls) -> "SkipPreferenceFile":
        """Create an empty skip preferences file with current metadata.

        Returns:
            A new SkipPreferenceFile with no skips
        """
        return cls(
            metadata=SkipPreferenceMetadata(
                version=SKIP_PREFS_VERSION,
                last_updated=datetime.utcnow(),
            ),
            skips=[],
        )


# ===========================
# Helper Functions
# ===========================


def build_artifact_key(artifact_type: str, artifact_name: str) -> str:
    """Build a standardized artifact key from type and name.

    Args:
        artifact_type: The artifact type (skill, command, agent, hook, mcp)
        artifact_name: The artifact name

    Returns:
        Formatted artifact_key in "type:name" format

    Examples:
        >>> build_artifact_key("skill", "canvas-design")
        "skill:canvas-design"
    """
    return f"{artifact_type}:{artifact_name}"


def parse_artifact_key(artifact_key: str) -> tuple[str, str]:
    """Parse an artifact key into type and name components.

    Args:
        artifact_key: The artifact key in "type:name" format

    Returns:
        Tuple of (artifact_type, artifact_name)

    Raises:
        ValueError: If format is invalid

    Examples:
        >>> parse_artifact_key("skill:canvas-design")
        ("skill", "canvas-design")
    """
    if ":" not in artifact_key:
        raise ValueError("artifact_key must be in format 'type:name'")

    parts = artifact_key.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Invalid artifact_key format")

    return parts[0], parts[1]


# ===========================
# Skip Preference Manager
# ===========================


import logging
import threading
import tomli_w

logger = logging.getLogger(__name__)


class SkipPreferenceManager:
    """Thread-safe manager for skip preference CRUD operations.

    Provides atomic file operations for managing user skip preferences
    at the project level. All file operations are protected by a lock
    to ensure thread safety during concurrent access.

    File Location:
        .claude/.skillmeat_skip_prefs.toml (relative to project root)

    Thread Safety:
        - All file read/write operations are protected by threading.Lock
        - Atomic writes using temp file + rename pattern
        - Graceful handling of missing/corrupt files

    Examples:
        >>> manager = SkipPreferenceManager(Path("/path/to/project"))
        >>> manager.add_skip("skill:canvas-design", "Already in collection")
        >>> manager.is_skipped("skill:canvas-design")
        True
        >>> manager.remove_skip("skill:canvas-design")
        True
    """

    def __init__(self, project_path: Path):
        """Initialize skip preference manager.

        Args:
            project_path: Path to the project root directory
                          (parent of .claude/ directory)
        """
        self.project_path = Path(project_path)
        self._lock = threading.Lock()

    def _get_skip_prefs_path(self) -> Path:
        """Get path to skip preferences file.

        Returns:
            Path to .claude/.skillmeat_skip_prefs.toml
        """
        return self.project_path / SKIP_PREFS_RELATIVE_PATH

    def load_skip_prefs(self) -> SkipPreferenceFile:
        """Load skip preferences from file.

        Creates an empty file if it doesn't exist. Handles corrupt
        files gracefully by logging a warning and returning empty file.

        Returns:
            SkipPreferenceFile object with current preferences

        Thread Safety:
            Protected by lock to prevent concurrent reads during writes
        """
        with self._lock:
            prefs_path = self._get_skip_prefs_path()

            # File doesn't exist - return empty file
            if not prefs_path.exists():
                logger.debug(
                    f"Skip preferences file not found at {prefs_path}, "
                    "returning empty file"
                )
                return SkipPreferenceFile.create_empty()

            # Try to load and parse file
            try:
                with open(prefs_path, "rb") as f:
                    data = tomllib.load(f)

                # Parse metadata
                metadata_data = data.get("metadata", {})
                metadata = SkipPreferenceMetadata(
                    version=metadata_data.get("version", SKIP_PREFS_VERSION),
                    last_updated=datetime.fromisoformat(
                        metadata_data.get("last_updated", datetime.utcnow().isoformat())
                    ),
                )

                # Parse skips
                skips_data = data.get("skips", [])
                skips = [
                    SkipPreference(
                        artifact_key=skip["artifact_key"],
                        skip_reason=skip["skip_reason"],
                        added_date=datetime.fromisoformat(skip["added_date"]),
                    )
                    for skip in skips_data
                ]

                return SkipPreferenceFile(metadata=metadata, skips=skips)

            except Exception as e:
                logger.warning(
                    f"Failed to load skip preferences from {prefs_path}: {e}. "
                    "Returning empty file."
                )
                return SkipPreferenceFile.create_empty()

    def save_skip_prefs(self, prefs: SkipPreferenceFile) -> None:
        """Save skip preferences to file atomically.

        Uses temp file + rename pattern for atomic writes to prevent
        corruption during concurrent access or system failures.

        Args:
            prefs: SkipPreferenceFile to save

        Raises:
            OSError: If file cannot be written (permissions, disk full, etc.)

        Thread Safety:
            Protected by lock to prevent concurrent writes
        """
        with self._lock:
            prefs_path = self._get_skip_prefs_path()

            # Ensure .claude directory exists
            prefs_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data for TOML serialization
            data = {
                "metadata": {
                    "version": prefs.metadata.version,
                    "last_updated": prefs.metadata.last_updated.isoformat(),
                },
                "skips": [
                    {
                        "artifact_key": skip.artifact_key,
                        "skip_reason": skip.skip_reason,
                        "added_date": skip.added_date.isoformat(),
                    }
                    for skip in prefs.skips
                ],
            }

            # Atomic write: temp file + rename
            temp_path = prefs_path.with_suffix(".tmp")
            try:
                with open(temp_path, "wb") as f:
                    tomli_w.dump(data, f)

                # Atomic rename (overwrites existing file on POSIX systems)
                temp_path.replace(prefs_path)
                logger.debug(f"Saved skip preferences to {prefs_path}")

            except Exception as e:
                # Clean up temp file if write failed
                if temp_path.exists():
                    temp_path.unlink()
                raise OSError(f"Failed to save skip preferences: {e}") from e

    def add_skip(self, artifact_key: str, reason: str) -> SkipPreference:
        """Add a skip preference for an artifact.

        Args:
            artifact_key: Artifact identifier in "type:name" format
            reason: Human-readable reason for skipping

        Returns:
            The newly created SkipPreference

        Raises:
            ValueError: If artifact_key is invalid or already exists

        Thread Safety:
            Atomic operation - load, modify, save within lock
        """
        prefs = self.load_skip_prefs()

        try:
            skip = prefs.add_skip(artifact_key, reason)
            self.save_skip_prefs(prefs)
            logger.info(f"Added skip preference for '{artifact_key}': {reason}")
            return skip

        except ValueError as e:
            logger.error(f"Failed to add skip preference for '{artifact_key}': {e}")
            raise

    def remove_skip(self, artifact_key: str) -> bool:
        """Remove a skip preference by artifact_key.

        Args:
            artifact_key: Artifact identifier in "type:name" format

        Returns:
            True if skip was removed, False if not found

        Thread Safety:
            Atomic operation - load, modify, save within lock
        """
        prefs = self.load_skip_prefs()
        removed = prefs.remove_skip(artifact_key)

        if removed:
            self.save_skip_prefs(prefs)
            logger.info(f"Removed skip preference for '{artifact_key}'")
        else:
            logger.debug(f"No skip preference found for '{artifact_key}'")

        return removed

    def is_skipped(self, artifact_key: str) -> bool:
        """Check if an artifact is in the skip list.

        Args:
            artifact_key: Artifact identifier in "type:name" format

        Returns:
            True if artifact is skipped, False otherwise

        Thread Safety:
            Read-only operation protected by lock
        """
        prefs = self.load_skip_prefs()
        return prefs.has_skip(artifact_key)

    def get_skip_by_key(self, artifact_key: str) -> Optional[SkipPreference]:
        """Get skip preference for a specific artifact.

        Args:
            artifact_key: Artifact identifier in "type:name" format

        Returns:
            SkipPreference if found, None otherwise

        Thread Safety:
            Read-only operation protected by lock
        """
        prefs = self.load_skip_prefs()
        return prefs.get_skip_by_key(artifact_key)

    def get_skipped_list(self) -> List[SkipPreference]:
        """Get all skip preferences.

        Returns:
            List of SkipPreference objects (empty list if no skips)

        Thread Safety:
            Read-only operation protected by lock
        """
        prefs = self.load_skip_prefs()
        return prefs.skips.copy()  # Return copy to prevent external modification

    def clear_skips(self) -> int:
        """Clear all skip preferences.

        Returns:
            Number of skip preferences that were removed

        Thread Safety:
            Atomic operation - load, clear, save within lock
        """
        prefs = self.load_skip_prefs()
        count = prefs.clear_all()

        if count > 0:
            self.save_skip_prefs(prefs)
            logger.info(f"Cleared {count} skip preference(s)")
        else:
            logger.debug("No skip preferences to clear")

        return count
