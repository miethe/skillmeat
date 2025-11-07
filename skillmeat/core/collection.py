"""Collection data model for SkillMeat."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .artifact import Artifact, ArtifactType


@dataclass
class Collection:
    """Personal collection of Claude artifacts."""

    name: str
    version: str  # collection format version (e.g., "1.0.0")
    artifacts: List[Artifact]
    created: datetime
    updated: datetime

    def __post_init__(self):
        """Validate collection configuration."""
        if not self.name:
            raise ValueError("Collection name cannot be empty")

    def find_artifact(
        self, name: str, artifact_type: Optional[ArtifactType] = None
    ) -> Optional[Artifact]:
        """Find artifact by name, optionally filtered by type.

        Args:
            name: The artifact name to search for
            artifact_type: Optional type filter

        Returns:
            The artifact if found, None otherwise

        Raises:
            ValueError: If name is ambiguous (multiple artifacts with same name but different types)
        """
        matches = []
        for artifact in self.artifacts:
            if artifact.name == name:
                if artifact_type is None:
                    matches.append(artifact)
                elif artifact.type == artifact_type:
                    return artifact

        if not matches:
            return None
        elif len(matches) == 1:
            return matches[0]
        else:
            # Multiple artifacts with same name but different types
            types = ", ".join([a.type.value for a in matches])
            raise ValueError(
                f"Ambiguous artifact name '{name}' matches multiple types: {types}. "
                f"Please specify type explicitly."
            )

    def add_artifact(self, artifact: Artifact) -> None:
        """Add artifact to collection (check for duplicates).

        Args:
            artifact: The artifact to add

        Raises:
            ValueError: If artifact with same composite key already exists
        """
        # Check composite key uniqueness
        for existing in self.artifacts:
            if existing.composite_key() == artifact.composite_key():
                raise ValueError(
                    f"Artifact '{artifact.name}' of type '{artifact.type.value}' "
                    f"already exists in collection."
                )
        self.artifacts.append(artifact)

    def remove_artifact(self, name: str, artifact_type: ArtifactType) -> bool:
        """Remove artifact by composite key.

        Args:
            name: Artifact name
            artifact_type: Artifact type

        Returns:
            True if removed, False if not found
        """
        for i, artifact in enumerate(self.artifacts):
            if artifact.name == name and artifact.type == artifact_type:
                self.artifacts.pop(i)
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        return {
            "collection": {
                "name": self.name,
                "version": self.version,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
            },
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collection":
        """Create from dictionary (TOML deserialization)."""
        collection_data = data.get("collection", {})
        artifacts_data = data.get("artifacts", [])

        # Parse datetimes
        created = datetime.fromisoformat(collection_data["created"])
        updated = datetime.fromisoformat(collection_data["updated"])

        # Parse artifacts
        artifacts = [
            Artifact.from_dict(artifact_data) for artifact_data in artifacts_data
        ]

        return cls(
            name=collection_data["name"],
            version=collection_data["version"],
            created=created,
            updated=updated,
            artifacts=artifacts,
        )
