"""Bundle data models for SkillMeat artifact sharing.

This module defines the core data structures for .skillmeat-pack bundles,
which are used to package and distribute artifacts across teams.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.artifact import ArtifactType


@dataclass
class BundleArtifact:
    """Represents a single artifact within a bundle.

    Attributes:
        type: Type of artifact (skill, command, agent)
        name: Artifact name
        version: Artifact version string
        scope: Scope (user or local)
        path: Relative path within bundle archive
        files: List of file paths relative to artifact root
        hash: SHA-256 hash of artifact contents
        metadata: Optional artifact metadata dictionary
    """

    type: str  # ArtifactType.value
    name: str
    version: str
    scope: str
    path: str  # Relative path in bundle (e.g., "artifacts/my-skill/")
    files: List[str]  # List of files relative to path
    hash: str  # SHA-256 hash
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate artifact data."""
        if self.type not in [t.value for t in ArtifactType]:
            raise ValueError(
                f"Invalid artifact type '{self.type}'. "
                f"Must be one of: {[t.value for t in ArtifactType]}"
            )

        if self.scope not in ("user", "local"):
            raise ValueError(
                f"Invalid scope '{self.scope}'. Must be 'user' or 'local'"
            )

        if not self.hash.startswith("sha256:"):
            raise ValueError(
                f"Hash must be in format 'sha256:...' but got: {self.hash}"
            )

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest serialization."""
        return {
            "type": self.type,
            "name": self.name,
            "version": self.version,
            "scope": self.scope,
            "path": self.path,
            "files": self.files,
            "hash": self.hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BundleArtifact":
        """Create from dictionary (manifest deserialization)."""
        return cls(
            type=data["type"],
            name=data["name"],
            version=data.get("version", "unknown"),
            scope=data.get("scope", "user"),
            path=data["path"],
            files=data.get("files", []),
            hash=data["hash"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class BundleMetadata:
    """Metadata for a bundle.

    Attributes:
        name: Bundle name (identifier)
        description: Human-readable description
        author: Author name or email
        created_at: ISO 8601 timestamp of bundle creation
        version: Bundle version (semver recommended)
        license: License identifier (e.g., "MIT", "Apache-2.0")
        tags: List of tags for categorization
        homepage: Optional URL to project homepage
        repository: Optional URL to source repository
    """

    name: str
    description: str
    author: str
    created_at: str  # ISO 8601 timestamp
    version: str = "1.0.0"
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None

    def __post_init__(self):
        """Validate metadata."""
        if not self.name:
            raise ValueError("Bundle name cannot be empty")

        if not self.description:
            raise ValueError("Bundle description cannot be empty")

        if not self.author:
            raise ValueError("Bundle author cannot be empty")

        # Validate ISO 8601 timestamp format
        try:
            datetime.fromisoformat(self.created_at)
        except ValueError as e:
            raise ValueError(
                f"created_at must be ISO 8601 format: {e}"
            ) from e

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest serialization."""
        result = {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "version": self.version,
            "license": self.license,
        }

        if self.tags:
            result["tags"] = self.tags

        if self.homepage:
            result["homepage"] = self.homepage

        if self.repository:
            result["repository"] = self.repository

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "BundleMetadata":
        """Create from dictionary (manifest deserialization)."""
        return cls(
            name=data["name"],
            description=data["description"],
            author=data["author"],
            created_at=data["created_at"],
            version=data.get("version", "1.0.0"),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
        )


@dataclass
class Bundle:
    """Represents a complete .skillmeat-pack bundle.

    A bundle is a ZIP archive containing:
    - manifest.json: Bundle metadata and artifact listing
    - artifacts/: Directory containing artifact files

    Attributes:
        metadata: Bundle metadata
        artifacts: List of artifacts in the bundle
        dependencies: List of bundle dependencies (other bundles required)
        bundle_hash: SHA-256 hash of entire bundle contents
        bundle_path: Optional path to bundle file on disk
    """

    metadata: BundleMetadata
    artifacts: List[BundleArtifact] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    bundle_hash: Optional[str] = None
    bundle_path: Optional[Path] = None

    def __post_init__(self):
        """Validate bundle data."""
        if self.bundle_hash and not self.bundle_hash.startswith("sha256:"):
            raise ValueError(
                f"bundle_hash must be in format 'sha256:...' but got: {self.bundle_hash}"
            )

    @property
    def artifact_count(self) -> int:
        """Return number of artifacts in bundle."""
        return len(self.artifacts)

    @property
    def total_files(self) -> int:
        """Return total number of files across all artifacts."""
        return sum(len(artifact.files) for artifact in self.artifacts)

    def find_artifact(self, name: str, artifact_type: Optional[str] = None) -> Optional[BundleArtifact]:
        """Find artifact by name and optional type.

        Args:
            name: Artifact name to find
            artifact_type: Optional type to filter by

        Returns:
            BundleArtifact if found, None otherwise
        """
        for artifact in self.artifacts:
            if artifact.name == name:
                if artifact_type is None or artifact.type == artifact_type:
                    return artifact
        return None

    def get_artifacts_by_type(self, artifact_type: str) -> List[BundleArtifact]:
        """Get all artifacts of a specific type.

        Args:
            artifact_type: Type to filter by (skill, command, agent)

        Returns:
            List of matching artifacts
        """
        return [a for a in self.artifacts if a.type == artifact_type]

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest serialization."""
        return {
            "version": "1.0",  # Manifest format version
            "name": self.metadata.name,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "created_at": self.metadata.created_at,
            "license": self.metadata.license,
            "tags": self.metadata.tags,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "dependencies": self.dependencies,
            "bundle_hash": self.bundle_hash or "",
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Bundle":
        """Create from dictionary (manifest deserialization)."""
        metadata = BundleMetadata(
            name=data["name"],
            description=data["description"],
            author=data["author"],
            created_at=data["created_at"],
            version=data.get("version", "1.0.0"),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
        )

        artifacts = [
            BundleArtifact.from_dict(artifact_data)
            for artifact_data in data.get("artifacts", [])
        ]

        return cls(
            metadata=metadata,
            artifacts=artifacts,
            dependencies=data.get("dependencies", []),
            bundle_hash=data.get("bundle_hash"),
        )
