"""Manifest management for SkillMeat collections."""

import sys
from datetime import datetime
from pathlib import Path

from ..core.collection import Collection
from ..utils.filesystem import atomic_write

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps


class ManifestManager:
    """Manages collection.toml files."""

    MANIFEST_FILENAME = "collection.toml"

    def read(self, collection_path: Path) -> Collection:
        """Read collection.toml and return Collection object.

        Args:
            collection_path: Path to collection directory

        Returns:
            Collection object

        Raises:
            FileNotFoundError: If collection.toml doesn't exist
            ValueError: If TOML is corrupted or invalid
        """
        manifest_file = collection_path / self.MANIFEST_FILENAME

        if not manifest_file.exists():
            raise FileNotFoundError(
                f"Collection manifest not found: {manifest_file}. "
                f"Run 'skillmeat init' to create a collection."
            )

        try:
            with open(manifest_file, "rb") as f:
                content = f.read()
                data = TOML_LOADS(content.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse collection.toml: {e}")

        return Collection.from_dict(data)

    def write(self, collection_path: Path, collection: Collection) -> None:
        """Write Collection object to collection.toml.

        Args:
            collection_path: Path to collection directory
            collection: Collection object to write

        Raises:
            IOError: If write operation fails
        """
        manifest_file = collection_path / self.MANIFEST_FILENAME

        # Update the collection's updated timestamp
        collection.updated = datetime.utcnow()

        # Serialize to TOML
        data = collection.to_dict()
        toml_content = TOML_DUMPS(data)

        # Write atomically
        atomic_write(toml_content, manifest_file)

    def exists(self, collection_path: Path) -> bool:
        """Check if collection.toml exists.

        Args:
            collection_path: Path to collection directory

        Returns:
            True if manifest exists, False otherwise
        """
        manifest_file = collection_path / self.MANIFEST_FILENAME
        return manifest_file.exists()

    def create_empty(self, collection_path: Path, name: str) -> Collection:
        """Create new empty collection.toml.

        Args:
            collection_path: Path to collection directory
            name: Collection name

        Returns:
            Newly created Collection object

        Raises:
            FileExistsError: If collection.toml already exists
            IOError: If write operation fails
        """
        if self.exists(collection_path):
            raise FileExistsError(
                f"Collection already exists at {collection_path}. "
                f"Use 'skillmeat list' to view artifacts."
            )

        # Create collection directory
        collection_path.mkdir(parents=True, exist_ok=True)

        # Create type-specific directories
        (collection_path / "skills").mkdir(exist_ok=True)
        (collection_path / "commands").mkdir(exist_ok=True)
        (collection_path / "agents").mkdir(exist_ok=True)
        (collection_path / "workflows").mkdir(exist_ok=True)

        # Create empty collection
        now = datetime.utcnow()
        collection = Collection(
            name=name,
            version="1.0.0",
            artifacts=[],
            created=now,
            updated=now,
        )

        # Write to disk
        self.write(collection_path, collection)

        return collection
