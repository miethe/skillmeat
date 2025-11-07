"""Collection data model and manager for SkillMeat."""

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
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


class CollectionManager:
    """Manages collection lifecycle and operations."""

    def __init__(self, config=None):
        """Initialize collection manager.

        Args:
            config: ConfigManager instance (creates default if None)
        """
        if config is None:
            from skillmeat.config import ConfigManager

            config = ConfigManager()
        self.config = config

        from skillmeat.storage.manifest import ManifestManager
        from skillmeat.storage.lockfile import LockManager

        self.manifest_mgr = ManifestManager()
        self.lock_mgr = LockManager()

    def init(self, name: str = "default") -> Collection:
        """Initialize new collection.

        Args:
            name: Collection name

        Returns:
            Newly created Collection object

        Raises:
            ValueError: Collection already exists
        """
        collection_path = self.config.get_collection_path(name)

        if collection_path.exists():
            raise ValueError(f"Collection '{name}' already exists at {collection_path}")

        # Create collection directory structure
        collection_path.mkdir(parents=True, exist_ok=True)
        (collection_path / "skills").mkdir(exist_ok=True)
        (collection_path / "commands").mkdir(exist_ok=True)
        (collection_path / "agents").mkdir(exist_ok=True)

        # Create empty collection
        collection = self.manifest_mgr.create_empty(collection_path, name)

        # Create empty lock file
        self.lock_mgr.write(collection_path, {})

        # Set as active if it's the default
        if name == "default":
            self.config.set_active_collection(name)

        return collection

    def list_collections(self) -> List[str]:
        """List all collection names.

        Returns:
            List of collection names
        """
        collections_dir = self.config.get_collections_dir()
        if not collections_dir.exists():
            return []

        return [
            d.name
            for d in collections_dir.iterdir()
            if d.is_dir() and (d / "collection.toml").exists()
        ]

    def get_active_collection_name(self) -> str:
        """Get currently active collection name.

        Returns:
            Active collection name
        """
        return self.config.get_active_collection()

    def switch_collection(self, name: str) -> None:
        """Switch active collection.

        Args:
            name: Collection name to switch to

        Raises:
            ValueError: Collection doesn't exist
        """
        if name not in self.list_collections():
            raise ValueError(f"Collection '{name}' does not exist")

        self.config.set_active_collection(name)

    def load_collection(self, name: Optional[str] = None) -> Collection:
        """Load collection from disk.

        Args:
            name: Collection name (uses active if None)

        Returns:
            Collection object

        Raises:
            ValueError: Collection not found
        """
        name = name or self.get_active_collection_name()
        collection_path = self.config.get_collection_path(name)

        if not collection_path.exists():
            raise ValueError(f"Collection '{name}' not found at {collection_path}")

        return self.manifest_mgr.read(collection_path)

    def save_collection(self, collection: Collection) -> None:
        """Save collection to disk.

        Args:
            collection: Collection to save
        """
        collection_path = self.config.get_collection_path(collection.name)
        collection.updated = datetime.utcnow()
        self.manifest_mgr.write(collection_path, collection)

    def delete_collection(self, name: str, confirm: bool = True) -> None:
        """Delete collection.

        Args:
            name: Collection name
            confirm: Require confirmation (safety check)

        Raises:
            ValueError: Collection not found or is active collection
        """
        if name == self.get_active_collection_name():
            raise ValueError(
                "Cannot delete active collection. Switch to another first."
            )

        collection_path = self.config.get_collection_path(name)
        if not collection_path.exists():
            raise ValueError(f"Collection '{name}' not found")

        # Safety check
        if confirm:
            raise ValueError("Use confirm=False to actually delete")

        # Delete collection directory
        shutil.rmtree(collection_path)
