"""Project metadata storage for SkillMeat.

This module provides storage and management for project metadata including
name, description, and creation timestamp.
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


@dataclass
class ProjectMetadata:
    """Project metadata including name, description, and timestamps."""

    path: str  # Absolute path to project directory
    name: str  # Project name
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization.

        Returns:
            Dictionary representation of project metadata
        """
        result = {
            "path": self.path,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }

        if self.description:
            result["description"] = self.description

        if self.updated_at:
            result["updated_at"] = self.updated_at.isoformat()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectMetadata":
        """Create from dictionary (TOML deserialization).

        Args:
            data: Dictionary with project metadata

        Returns:
            ProjectMetadata instance
        """
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = None
        if "updated_at" in data:
            updated_at = datetime.fromisoformat(data["updated_at"])

        return cls(
            path=data["path"],
            name=data["name"],
            description=data.get("description"),
            created_at=created_at,
            updated_at=updated_at,
        )


class ProjectMetadataStorage:
    """Storage layer for project metadata.

    Manages project metadata in .claude/.skillmeat-project.toml files.
    This is separate from deployment tracking and stores project-level
    information like name and description.
    """

    METADATA_FILE = ".skillmeat-project.toml"

    @staticmethod
    def get_metadata_file_path(project_path: Path) -> Path:
        """Get path to project metadata file.

        Args:
            project_path: Absolute path to project directory

        Returns:
            Path to .skillmeat-project.toml file
        """
        return project_path / ".claude" / ProjectMetadataStorage.METADATA_FILE

    @staticmethod
    def read_metadata(project_path: Path) -> Optional[ProjectMetadata]:
        """Read project metadata.

        Args:
            project_path: Absolute path to project directory

        Returns:
            ProjectMetadata object or None if metadata file doesn't exist
        """
        metadata_file = ProjectMetadataStorage.get_metadata_file_path(project_path)

        if not metadata_file.exists():
            return None

        with open(metadata_file, "rb") as f:
            data = tomllib.load(f)

        return ProjectMetadata.from_dict(data.get("project", {}))

    @staticmethod
    def write_metadata(project_path: Path, metadata: ProjectMetadata) -> None:
        """Write project metadata.

        Args:
            project_path: Absolute path to project directory
            metadata: ProjectMetadata object to write
        """
        metadata_file = ProjectMetadataStorage.get_metadata_file_path(project_path)

        # Ensure .claude directory exists
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to TOML format
        data = {"project": metadata.to_dict()}

        # Write atomically
        with open(metadata_file, "wb") as f:
            tomli_w.dump(data, f)

    @staticmethod
    def create_metadata(
        project_path: Path,
        name: str,
        description: Optional[str] = None,
    ) -> ProjectMetadata:
        """Create new project metadata.

        Args:
            project_path: Absolute path to project directory
            name: Project name
            description: Optional project description

        Returns:
            Created ProjectMetadata object
        """
        metadata = ProjectMetadata(
            path=str(project_path),
            name=name,
            description=description,
            created_at=datetime.now(),
        )

        ProjectMetadataStorage.write_metadata(project_path, metadata)
        return metadata

    @staticmethod
    def update_metadata(
        project_path: Path,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[ProjectMetadata]:
        """Update existing project metadata.

        Args:
            project_path: Absolute path to project directory
            name: New project name (optional)
            description: New project description (optional)

        Returns:
            Updated ProjectMetadata object or None if metadata doesn't exist
        """
        metadata = ProjectMetadataStorage.read_metadata(project_path)

        if metadata is None:
            return None

        # Update fields
        if name is not None:
            metadata.name = name

        if description is not None:
            metadata.description = description

        metadata.updated_at = datetime.now()

        ProjectMetadataStorage.write_metadata(project_path, metadata)
        return metadata

    @staticmethod
    def delete_metadata(project_path: Path) -> bool:
        """Delete project metadata file.

        Args:
            project_path: Absolute path to project directory

        Returns:
            True if metadata file was deleted, False if it didn't exist
        """
        metadata_file = ProjectMetadataStorage.get_metadata_file_path(project_path)

        if metadata_file.exists():
            metadata_file.unlink()
            return True

        return False

    @staticmethod
    def exists(project_path: Path) -> bool:
        """Check if project metadata exists.

        Args:
            project_path: Absolute path to project directory

        Returns:
            True if metadata file exists, False otherwise
        """
        metadata_file = ProjectMetadataStorage.get_metadata_file_path(project_path)
        return metadata_file.exists()
