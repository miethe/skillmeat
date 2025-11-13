"""Core artifact data models and manager for SkillMeat."""

import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps


class ArtifactType(str, Enum):
    """Types of Claude artifacts."""

    SKILL = "skill"
    COMMAND = "command"
    AGENT = "agent"
    # Future: MCP = "mcp", HOOK = "hook"


class UpdateStrategy(str, Enum):
    """Strategies for updating artifacts with local modifications."""

    PROMPT = "prompt"  # Default: ask user what to do
    TAKE_UPSTREAM = "upstream"  # Always take upstream (lose local changes)
    KEEP_LOCAL = "local"  # Keep local modifications (skip update)
    # Phase 2: MERGE = "merge"  # 3-way merge (deferred)


@dataclass
class ArtifactMetadata:
    """Metadata extracted from artifact files (SKILL.md, COMMAND.md, AGENT.md)."""

    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result = {}
        if self.title is not None:
            result["title"] = self.title
        if self.description is not None:
            result["description"] = self.description
        if self.author is not None:
            result["author"] = self.author
        if self.license is not None:
            result["license"] = self.license
        if self.version is not None:
            result["version"] = self.version
        if self.tags:
            result["tags"] = self.tags
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.extra:
            result["extra"] = self.extra
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactMetadata":
        """Create from dictionary (TOML deserialization)."""
        return cls(
            title=data.get("title"),
            description=data.get("description"),
            author=data.get("author"),
            license=data.get("license"),
            version=data.get("version"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", []),
            extra=data.get("extra", {}),
        )


@dataclass
class Artifact:
    """Unified artifact representation."""

    name: str
    type: ArtifactType
    path: str  # relative to collection root (e.g., "skills/python-skill/")
    origin: str  # "local" or "github"
    metadata: ArtifactMetadata
    added: datetime
    upstream: Optional[str] = None  # GitHub URL if from GitHub
    version_spec: Optional[str] = None  # "latest", "v1.0.0", "branch-name"
    resolved_sha: Optional[str] = None
    resolved_version: Optional[str] = None
    last_updated: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate artifact configuration."""
        if not self.name:
            raise ValueError("Artifact name cannot be empty")
        if self.origin not in ("local", "github"):
            raise ValueError(
                f"Invalid origin: {self.origin}. Must be 'local' or 'github'."
            )
        # Ensure type is ArtifactType enum
        if isinstance(self.type, str):
            self.type = ArtifactType(self.type)

    def composite_key(self) -> tuple:
        """Return unique composite key (name, type)."""
        return (self.name, self.type.value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result = {
            "name": self.name,
            "type": self.type.value,
            "path": self.path,
            "origin": self.origin,
            "added": self.added.isoformat(),
        }

        # Add metadata if present
        metadata_dict = self.metadata.to_dict()
        if metadata_dict:
            result["metadata"] = metadata_dict

        # Add optional fields
        if self.upstream is not None:
            result["upstream"] = self.upstream
        if self.version_spec is not None:
            result["version_spec"] = self.version_spec
        if self.resolved_sha is not None:
            result["resolved_sha"] = self.resolved_sha
        if self.resolved_version is not None:
            result["resolved_version"] = self.resolved_version
        if self.last_updated is not None:
            result["last_updated"] = self.last_updated.isoformat()
        if self.tags:
            result["tags"] = self.tags

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Create from dictionary (TOML deserialization)."""
        # Parse metadata
        metadata_data = data.get("metadata", {})
        metadata = ArtifactMetadata.from_dict(metadata_data)

        # Parse datetimes
        added = datetime.fromisoformat(data["added"])
        last_updated = None
        if "last_updated" in data and data["last_updated"] is not None:
            last_updated = datetime.fromisoformat(data["last_updated"])

        return cls(
            name=data["name"],
            type=ArtifactType(data["type"]),
            path=data["path"],
            origin=data["origin"],
            metadata=metadata,
            added=added,
            upstream=data.get("upstream"),
            version_spec=data.get("version_spec"),
            resolved_sha=data.get("resolved_sha"),
            resolved_version=data.get("resolved_version"),
            last_updated=last_updated,
            tags=data.get("tags", []),
        )


class ArtifactManager:
    """Manages artifacts within collections."""

    def __init__(self, collection_mgr=None):
        """Initialize artifact manager.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
        """
        if collection_mgr is None:
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager()

        self.collection_mgr = collection_mgr
        config = self.collection_mgr.config
        github_token = config.get("settings.github-token")

        from skillmeat.sources.github import GitHubSource
        from skillmeat.sources.local import LocalSource
        from skillmeat.utils.filesystem import FilesystemManager, compute_content_hash
        from skillmeat.utils.validator import ArtifactValidator

        self.github_source = GitHubSource(github_token)
        self.local_source = LocalSource()
        self.filesystem_mgr = FilesystemManager()
        self.validator = ArtifactValidator()
        self.compute_content_hash = compute_content_hash

    def add_from_github(
        self,
        spec: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str] = None,
        custom_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        force: bool = False,
    ) -> Artifact:
        """Add artifact from GitHub.

        Args:
            spec: GitHub spec (e.g., "username/repo/path@version")
            artifact_type: Type of artifact
            collection_name: Target collection (uses active if None)
            custom_name: Custom artifact name (derives from spec if None)
            tags: Optional tags to add
            force: If True, overwrite existing artifact

        Returns:
            Added Artifact object

        Raises:
            ValueError: Invalid spec or artifact already exists (when force=False)
            RuntimeError: Fetch or validation failed
        """
        from skillmeat.sources.github import ArtifactSpec

        # Load collection
        collection = self.collection_mgr.load_collection(collection_name)

        # Fetch from GitHub
        fetch_result = self.github_source.fetch(spec, artifact_type)

        # Determine artifact name
        if custom_name:
            artifact_name = custom_name
        else:
            # Extract name from spec (last path component)
            parsed_spec = ArtifactSpec.parse(spec)
            if parsed_spec.path:
                artifact_name = Path(parsed_spec.path).name
            else:
                # If no path, use repo name
                artifact_name = parsed_spec.repo

        # Check for duplicates (composite key)
        existing = collection.find_artifact(artifact_name, artifact_type)
        if existing:
            if force:
                # Remove existing artifact before adding new one
                self.remove(artifact_name, artifact_type, collection_name)
                # Reload collection after removal
                collection = self.collection_mgr.load_collection(collection_name)
            else:
                raise ValueError(
                    f"Artifact '{artifact_name}' of type '{artifact_type.value}' already exists in collection"
                )

        # Determine storage path within collection
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )
        if artifact_type == ArtifactType.SKILL:
            artifact_storage_path = collection_path / "skills" / artifact_name
        elif artifact_type == ArtifactType.COMMAND:
            artifact_storage_path = collection_path / "commands" / f"{artifact_name}.md"
        elif artifact_type == ArtifactType.AGENT:
            artifact_storage_path = collection_path / "agents" / f"{artifact_name}.md"
        else:
            raise ValueError(f"Unsupported artifact type: {artifact_type}")

        # Copy artifact to collection
        self.filesystem_mgr.copy_artifact(
            fetch_result.artifact_path, artifact_storage_path, artifact_type
        )

        # Create Artifact object
        artifact = Artifact(
            name=artifact_name,
            type=artifact_type,
            path=str(artifact_storage_path.relative_to(collection_path)),
            origin="github",
            metadata=fetch_result.metadata,
            added=datetime.utcnow(),
            upstream=fetch_result.upstream_url,
            version_spec=ArtifactSpec.parse(spec).version,
            resolved_sha=fetch_result.resolved_sha,
            resolved_version=fetch_result.resolved_version,
            tags=tags or [],
        )

        # Add to collection
        collection.add_artifact(artifact)
        self.collection_mgr.save_collection(collection)

        # Update lock file
        content_hash = self.compute_content_hash(artifact_storage_path)
        self.collection_mgr.lock_mgr.update_entry(
            collection_path,
            artifact.name,
            artifact.type,
            artifact.upstream,
            artifact.resolved_sha,
            artifact.resolved_version,
            content_hash,
        )

        return artifact

    def add_from_local(
        self,
        path: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str] = None,
        custom_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        force: bool = False,
    ) -> Artifact:
        """Add artifact from local filesystem.

        Args:
            path: Local path to artifact
            artifact_type: Type of artifact
            collection_name: Target collection (uses active if None)
            custom_name: Custom artifact name (derives from path if None)
            tags: Optional tags to add
            force: If True, overwrite existing artifact

        Returns:
            Added Artifact object

        Raises:
            ValueError: Invalid path or artifact already exists (when force=False)
            RuntimeError: Fetch or validation failed
        """
        # Load collection
        collection = self.collection_mgr.load_collection(collection_name)

        # Fetch from local
        fetch_result = self.local_source.fetch(path, artifact_type)

        # Determine artifact name
        if custom_name:
            artifact_name = custom_name
        else:
            artifact_name = Path(path).stem

        # Check for duplicates
        existing = collection.find_artifact(artifact_name, artifact_type)
        if existing:
            if force:
                # Remove existing artifact before adding new one
                self.remove(artifact_name, artifact_type, collection_name)
                # Reload collection after removal
                collection = self.collection_mgr.load_collection(collection_name)
            else:
                raise ValueError(
                    f"Artifact '{artifact_name}' of type '{artifact_type.value}' already exists"
                )

        # Determine storage path
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )
        if artifact_type == ArtifactType.SKILL:
            artifact_storage_path = collection_path / "skills" / artifact_name
        elif artifact_type == ArtifactType.COMMAND:
            artifact_storage_path = collection_path / "commands" / f"{artifact_name}.md"
        elif artifact_type == ArtifactType.AGENT:
            artifact_storage_path = collection_path / "agents" / f"{artifact_name}.md"
        else:
            raise ValueError(f"Unsupported artifact type: {artifact_type}")

        # Copy artifact to collection
        self.filesystem_mgr.copy_artifact(
            fetch_result.artifact_path, artifact_storage_path, artifact_type
        )

        # Create Artifact object (no upstream)
        artifact = Artifact(
            name=artifact_name,
            type=artifact_type,
            path=str(artifact_storage_path.relative_to(collection_path)),
            origin="local",
            metadata=fetch_result.metadata,
            added=datetime.utcnow(),
            tags=tags or [],
        )

        # Add to collection
        collection.add_artifact(artifact)
        self.collection_mgr.save_collection(collection)

        # Update lock file
        content_hash = self.compute_content_hash(artifact_storage_path)
        self.collection_mgr.lock_mgr.update_entry(
            collection_path,
            artifact.name,
            artifact.type,
            None,  # No upstream
            None,  # No SHA
            None,  # No version
            content_hash,
        )

        return artifact

    def remove(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str] = None,
    ) -> None:
        """Remove artifact from collection.

        Args:
            artifact_name: Name of artifact to remove
            artifact_type: Type of artifact
            collection_name: Collection name (uses active if None)

        Raises:
            ValueError: Artifact not found
        """
        # Create auto-snapshot before removal
        from skillmeat.core.version import VersionManager

        version_mgr = VersionManager(self.collection_mgr)
        version_mgr.auto_snapshot(
            collection_name, f"Before removing {artifact_type.value}/{artifact_name}"
        )

        collection = self.collection_mgr.load_collection(collection_name)

        # Find artifact
        artifact = collection.find_artifact(artifact_name, artifact_type)
        if not artifact:
            raise ValueError(
                f"Artifact '{artifact_name}' of type '{artifact_type.value}' not found"
            )

        # Remove from filesystem
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )
        artifact_path = collection_path / artifact.path
        self.filesystem_mgr.remove_artifact(artifact_path)

        # Remove from collection
        collection.remove_artifact(artifact_name, artifact_type)
        self.collection_mgr.save_collection(collection)

        # Remove from lock file
        self.collection_mgr.lock_mgr.remove_entry(
            collection_path, artifact_name, artifact_type
        )

    def list_artifacts(
        self,
        collection_name: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Artifact]:
        """List artifacts with optional filters.

        Args:
            collection_name: Collection name (uses active if None)
            artifact_type: Filter by type
            tags: Filter by tags (any match)

        Returns:
            List of matching artifacts
        """
        collection = self.collection_mgr.load_collection(collection_name)

        artifacts = collection.artifacts

        # Filter by type
        if artifact_type:
            artifacts = [a for a in artifacts if a.type == artifact_type]

        # Filter by tags
        if tags:
            artifacts = [a for a in artifacts if any(tag in a.tags for tag in tags)]

        return artifacts

    def show(
        self,
        artifact_name: str,
        artifact_type: Optional[ArtifactType] = None,
        collection_name: Optional[str] = None,
    ) -> Artifact:
        """Get detailed artifact information.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type (required if name is ambiguous)
            collection_name: Collection name (uses active if None)

        Returns:
            Artifact object

        Raises:
            ValueError: Artifact not found or name ambiguous
        """
        collection = self.collection_mgr.load_collection(collection_name)
        artifact = collection.find_artifact(artifact_name, artifact_type)

        if not artifact:
            raise ValueError(f"Artifact '{artifact_name}' not found")

        return artifact

    def check_updates(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Check all artifacts for updates.

        Args:
            collection_name: Collection name (uses active if None)

        Returns:
            Dict mapping artifact composite key to UpdateInfo
        """
        from skillmeat.sources.base import UpdateInfo

        collection = self.collection_mgr.load_collection(collection_name)
        updates = {}

        for artifact in collection.artifacts:
            if artifact.origin == "github":
                update_info = self.github_source.check_updates(artifact)
                if update_info and update_info.has_update:
                    key = f"{artifact.name}::{artifact.type.value}"
                    updates[key] = update_info

        return updates

    def update(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        collection_name: Optional[str] = None,
        strategy: UpdateStrategy = UpdateStrategy.PROMPT,
    ) -> Artifact:
        """Update artifact from upstream.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type
            collection_name: Collection name (uses active if None)
            strategy: Update strategy (PROMPT, TAKE_UPSTREAM, KEEP_LOCAL)

        Returns:
            Updated Artifact object

        Raises:
            ValueError: Artifact not found or no upstream
            RuntimeError: Update failed
            NotImplementedError: Update functionality (deferred to Phase 5)
        """
        # Implementation deferred to Phase 5 (complex logic with prompts)
        raise NotImplementedError("Update functionality will be implemented in Phase 5")
