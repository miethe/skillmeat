"""Core artifact data models and manager for SkillMeat."""

import logging
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from rich.prompt import Confirm

from skillmeat.utils.logging import redact_path

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps

# Import ArtifactType from the canonical detection module
from skillmeat.core.artifact_detection import ArtifactType


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
    origin: str  # "local", "github", or "marketplace"
    metadata: ArtifactMetadata
    added: datetime
    upstream: Optional[str] = None  # GitHub URL if from GitHub
    version_spec: Optional[str] = None  # "latest", "v1.0.0", "branch-name"
    resolved_sha: Optional[str] = None
    resolved_version: Optional[str] = None
    last_updated: Optional[datetime] = None
    discovered_at: Optional[datetime] = None  # When artifact was first discovered or last changed
    tags: List[str] = field(default_factory=list)
    origin_source: Optional[str] = None  # Platform type when origin="marketplace" (e.g., "github", "gitlab", "bitbucket")

    def __post_init__(self):
        """Validate artifact configuration.

        Security: This validation prevents path traversal attacks by ensuring
        artifact names cannot contain path separators or directory references.
        See security review CRITICAL-1 for details.
        """
        if not self.name:
            raise ValueError("Artifact name cannot be empty")

        # CRITICAL SECURITY: Prevent path traversal attacks
        # Artifact names must be simple identifiers without path components
        if "/" in self.name or "\\" in self.name:
            raise ValueError(
                f"Invalid artifact name '{self.name}': "
                "artifact names cannot contain path separators (/ or \\)"
            )

        if ".." in self.name:
            raise ValueError(
                f"Invalid artifact name '{self.name}': "
                "artifact names cannot contain parent directory references (..)"
            )

        # Prevent hidden/system files (security consideration)
        if self.name.startswith("."):
            raise ValueError(
                f"Invalid artifact name '{self.name}': "
                "artifact names cannot start with '.'"
            )

        if self.origin not in ("local", "github", "marketplace"):
            raise ValueError(
                f"Invalid origin: {self.origin}. Must be 'local', 'github', or 'marketplace'."
            )

        # Validate origin_source: only allowed when origin is "marketplace"
        valid_origin_sources = ("github", "gitlab", "bitbucket")
        if self.origin_source is not None:
            if self.origin != "marketplace":
                raise ValueError(
                    f"origin_source can only be set when origin is 'marketplace', "
                    f"but origin is '{self.origin}'"
                )
            if self.origin_source not in valid_origin_sources:
                raise ValueError(
                    f"Invalid origin_source: {self.origin_source}. "
                    f"Must be one of: {', '.join(valid_origin_sources)}"
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
        if self.discovered_at is not None:
            result["discovered_at"] = self.discovered_at.isoformat()
        if self.tags:
            result["tags"] = self.tags
        if self.origin_source is not None:
            result["origin_source"] = self.origin_source

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
        discovered_at = None
        if "discovered_at" in data and data["discovered_at"] is not None:
            discovered_at = datetime.fromisoformat(data["discovered_at"])

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
            discovered_at=discovered_at,
            tags=data.get("tags", []),
            origin_source=data.get("origin_source"),
        )


@dataclass
class UpdateFetchResult:
    """Result of fetching an update from upstream (before applying).

    This represents a fetched update cached in a temp workspace for inspection.
    """

    artifact: Artifact
    has_update: bool
    update_info: Optional[Any] = None  # UpdateInfo from sources.base
    fetch_result: Optional[Any] = None  # FetchResult from sources.base
    temp_workspace: Optional[Path] = None  # Persistent temp path for inspection
    error: Optional[str] = None  # Error message if fetch failed


@dataclass
class UpdateResult:
    """Result of attempting to update an artifact."""

    artifact: Artifact
    updated: bool
    status: str
    previous_version: Optional[str] = None
    new_version: Optional[str] = None
    previous_sha: Optional[str] = None
    new_sha: Optional[str] = None
    local_modifications: bool = False


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
                artifact_name = Path(parsed_spec.path).stem
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

        # Track remove event
        self._record_remove_event(
            artifact_name=artifact_name,
            artifact_type=artifact_type.value,
            collection_name=collection.name,
            reason="user_action",
            from_project=False,
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

    def fetch_update(
        self,
        artifact_name: str,
        artifact_type: Optional[ArtifactType] = None,
        collection_name: Optional[str] = None,
    ) -> UpdateFetchResult:
        """Fetch update from upstream and cache in temp workspace for inspection.

        This method fetches the latest version of an artifact from its upstream source
        and stores it in a persistent temporary workspace without applying the update.
        This allows inspection and comparison before deciding to apply changes.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type (required if ambiguous)
            collection_name: Collection name (uses active if None)

        Returns:
            UpdateFetchResult with fetch details and temp workspace path

        Raises:
            ValueError: Artifact not found or unsupported origin
        """
        import tempfile
        from skillmeat.sources.base import UpdateInfo

        # Load collection and find artifact
        try:
            collection = self.collection_mgr.load_collection(collection_name)
        except Exception as e:
            # Return error result if collection loading fails
            return UpdateFetchResult(
                artifact=None,
                has_update=False,
                error=f"Failed to load collection: {e}",
            )

        try:
            artifact = collection.find_artifact(artifact_name, artifact_type)
        except Exception as e:
            return UpdateFetchResult(
                artifact=None,
                has_update=False,
                error=f"Error finding artifact: {e}",
            )

        if not artifact:
            return UpdateFetchResult(
                artifact=None,
                has_update=False,
                error=f"Artifact '{artifact_name}' not found in collection",
            )

        # Only GitHub artifacts support updates
        if artifact.origin != "github":
            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                error=f"Artifact origin '{artifact.origin}' does not support upstream updates",
            )

        # Check if upstream reference exists
        if not artifact.upstream:
            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                error="Artifact does not have an upstream reference",
            )

        # Check for updates
        try:
            update_info = self.github_source.check_updates(artifact)
        except Exception as e:
            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                error=f"Failed to check for updates: {e}",
            )

        # No updates available
        if not update_info or not update_info.has_update:
            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                update_info=update_info,
            )

        # Create persistent temp workspace
        temp_workspace = None
        fetch_result = None

        try:
            # Create temp directory with descriptive prefix
            temp_workspace = Path(
                tempfile.mkdtemp(
                    prefix=f"skillmeat_update_{artifact.name}_{artifact.type.value}_"
                )
            )

            # Build spec for fetching updated version
            override_version = update_info.latest_sha or artifact.version_spec
            spec = self._build_spec_from_artifact(
                artifact, version_override=override_version
            )

            # Fetch the updated artifact to temp workspace
            # Note: GitHubSource.fetch creates its own temp dir inside,
            # so we copy the result to our persistent temp workspace
            fetch_result = self.github_source.fetch(spec, artifact.type)

            # Copy fetched artifact to persistent workspace for inspection
            workspace_artifact_path = temp_workspace / "artifact"
            self.filesystem_mgr.copy_artifact(
                fetch_result.artifact_path, workspace_artifact_path, artifact.type
            )

            # Update fetch_result to point to persistent workspace
            fetch_result.artifact_path = workspace_artifact_path

            logging.info(
                f"Fetched update for {artifact.type.value}/{artifact.name} "
                f"to {redact_path(temp_workspace)}"
            )

            return UpdateFetchResult(
                artifact=artifact,
                has_update=True,
                update_info=update_info,
                fetch_result=fetch_result,
                temp_workspace=temp_workspace,
            )

        except ValueError as e:
            # Validation or parsing errors
            error_msg = f"Invalid artifact source: {e}"
            logging.error(error_msg)

            # Clean up temp workspace on error
            if temp_workspace and temp_workspace.exists():
                shutil.rmtree(temp_workspace, ignore_errors=True)

            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                update_info=update_info,
                error=error_msg,
            )

        except requests.exceptions.RequestException as e:
            # Network failures
            error_msg = f"Network error while fetching update: {e}"
            logging.error(error_msg)

            # Clean up temp workspace on error
            if temp_workspace and temp_workspace.exists():
                shutil.rmtree(temp_workspace, ignore_errors=True)

            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                update_info=update_info,
                error=error_msg,
            )

        except PermissionError as e:
            # Permission issues
            error_msg = (
                f"Permission denied while fetching update: {e}. "
                "Check GitHub token configuration if accessing private repositories."
            )
            logging.error(error_msg)

            # Clean up temp workspace on error
            if temp_workspace and temp_workspace.exists():
                shutil.rmtree(temp_workspace, ignore_errors=True)

            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                update_info=update_info,
                error=error_msg,
            )

        except Exception as e:
            # Unexpected errors
            error_msg = f"Unexpected error while fetching update: {e}"
            logging.error(error_msg)

            # Clean up temp workspace on error
            if temp_workspace and temp_workspace.exists():
                shutil.rmtree(temp_workspace, ignore_errors=True)

            return UpdateFetchResult(
                artifact=artifact,
                has_update=False,
                update_info=update_info,
                error=error_msg,
            )

    def _show_update_preview(
        self,
        artifact_ref: str,
        current_path: Path,
        update_path: Path,
        strategy: str,
        console,
    ) -> Dict[str, Any]:
        """Show comprehensive preview of what update will change.

        Args:
            artifact_ref: Artifact reference (type/name)
            current_path: Path to current version
            update_path: Path to updated version
            strategy: Update strategy being used
            console: Rich console for output

        Returns:
            Dict with preview data including:
            - diff_result: DiffResult from DiffEngine
            - three_way_diff: Optional[ThreeWayDiffResult] for merge strategy
            - conflicts_detected: bool
            - can_auto_merge: bool
            - recommendation: str (recommended strategy)
            - recommendation_reason: str
        """
        from skillmeat.core.diff_engine import DiffEngine
        from skillmeat.core.merge_engine import MergeEngine

        diff_engine = DiffEngine()
        preview_data = {}

        # Generate diff between current and updated versions
        diff_result = diff_engine.diff_directories(current_path, update_path)
        preview_data["diff_result"] = diff_result

        # Show summary header
        console.print(f"\n[bold]Update Preview for {artifact_ref}[/bold]")
        console.print(f"Strategy: [cyan]{strategy}[/cyan]\n")

        # Summary statistics
        total_changes = (
            len(diff_result.files_added)
            + len(diff_result.files_removed)
            + len(diff_result.files_modified)
        )
        console.print(f"[bold]Summary:[/bold]")
        console.print(f"  Files changed: {total_changes}")
        console.print(f"  Files added: [green]{len(diff_result.files_added)}[/green]")
        console.print(f"  Files removed: [red]{len(diff_result.files_removed)}[/red]")
        console.print(
            f"  Files modified: [yellow]{len(diff_result.files_modified)}[/yellow]"
        )

        if diff_result.total_lines_added or diff_result.total_lines_removed:
            console.print(
                f"  Lines: [green]+{diff_result.total_lines_added}[/green] "
                f"[red]-{diff_result.total_lines_removed}[/red]"
            )

        # For merge strategy, show merge preview with conflict detection
        if strategy == "merge":
            console.print(f"\n[bold]Merge Analysis:[/bold]")
            merge_engine = MergeEngine()

            # Perform three-way diff to detect conflicts
            # Phase 0: Use current as base (base == local)
            three_way_diff = diff_engine.three_way_diff(
                base_path=current_path,
                local_path=current_path,
                remote_path=update_path,
            )
            preview_data["three_way_diff"] = three_way_diff

            auto_mergeable_count = len(three_way_diff.auto_mergeable)
            conflicts_count = len(three_way_diff.conflicts)

            console.print(
                f"  Auto-mergeable files: [green]{auto_mergeable_count}[/green]"
            )
            console.print(f"  Conflicted files: [yellow]{conflicts_count}[/yellow]")

            preview_data["conflicts_detected"] = conflicts_count > 0
            preview_data["can_auto_merge"] = conflicts_count == 0

            if conflicts_count > 0:
                console.print(
                    f"\n[yellow]Warning: {conflicts_count} files have conflicts:[/yellow]"
                )
                for conflict in three_way_diff.conflicts[:5]:
                    console.print(
                        f"  - {conflict.file_path} ({conflict.conflict_type})"
                    )
                if conflicts_count > 5:
                    console.print(f"  ... and {conflicts_count - 5} more")

                console.print(
                    f"\n[yellow]Files with conflicts will contain Git-style markers:[/yellow]"
                )
                console.print("  <<<<<<< LOCAL (current)")
                console.print("  [your local changes]")
                console.print("  =======")
                console.print("  [incoming upstream changes]")
                console.print("  >>>>>>> REMOTE (incoming)")
        else:
            preview_data["conflicts_detected"] = False
            preview_data["can_auto_merge"] = True

        # Show file details (limited)
        if diff_result.files_added:
            console.print(f"\n[bold]Added Files:[/bold]")
            for file in diff_result.files_added[:5]:
                console.print(f"  [green]+[/green] {file}")
            if len(diff_result.files_added) > 5:
                console.print(
                    f"  ... and {len(diff_result.files_added) - 5} more files"
                )

        if diff_result.files_removed:
            console.print(f"\n[bold]Removed Files:[/bold]")
            for file in diff_result.files_removed[:5]:
                console.print(f"  [red]-[/red] {file}")
            if len(diff_result.files_removed) > 5:
                console.print(
                    f"  ... and {len(diff_result.files_removed) - 5} more files"
                )

        if diff_result.files_modified:
            console.print(f"\n[bold]Modified Files:[/bold]")
            for file_diff in diff_result.files_modified[:5]:
                console.print(
                    f"  [yellow]M[/yellow] {file_diff.path} "
                    f"([green]+{file_diff.lines_added}[/green] "
                    f"[red]-{file_diff.lines_removed}[/red])"
                )
            if len(diff_result.files_modified) > 5:
                console.print(
                    f"  ... and {len(diff_result.files_modified) - 5} more files"
                )

        return preview_data

    def _recommend_strategy(
        self,
        diff_result,
        has_local_modifications: bool,
        three_way_diff=None,
    ) -> tuple:
        """Recommend update strategy based on changes.

        Args:
            diff_result: DiffResult from comparing current vs upstream
            has_local_modifications: Whether local modifications exist
            three_way_diff: Optional ThreeWayDiffResult if available

        Returns:
            Tuple of (strategy: str, reason: str)

        Logic:
        - No local modifications → "overwrite" (safe to replace)
        - Local mods + no conflicts → "merge" (auto-merge possible)
        - Local mods + conflicts → "prompt" (user decision needed)
        - Complex changes (many files) → "prompt" (review recommended)
        """
        # No local modifications - safe to overwrite
        if not has_local_modifications:
            return ("overwrite", "No local modifications detected - safe to replace")

        # Check if we have three-way diff info (merge strategy)
        if three_way_diff is not None:
            conflicts_count = len(three_way_diff.conflicts)

            if conflicts_count == 0:
                return (
                    "merge",
                    f"All {len(three_way_diff.auto_mergeable)} changes can auto-merge",
                )
            elif conflicts_count < 3:
                return (
                    "prompt",
                    f"{conflicts_count} conflicts detected - review recommended",
                )
            else:
                return (
                    "prompt",
                    f"{conflicts_count} conflicts detected - manual resolution required",
                )

        # Check complexity based on file counts
        total_changes = (
            len(diff_result.files_added)
            + len(diff_result.files_removed)
            + len(diff_result.files_modified)
        )

        if total_changes == 0:
            return ("overwrite", "No changes detected")

        if total_changes < 5:
            return (
                "merge",
                f"{total_changes} files changed - merge recommended",
            )

        if total_changes < 20:
            return (
                "prompt",
                f"{total_changes} files changed - review recommended",
            )

        return (
            "prompt",
            f"{total_changes} files changed - extensive changes require review",
        )

    def apply_update_strategy(
        self,
        fetch_result: UpdateFetchResult,
        strategy: str = "prompt",
        interactive: bool = True,
        auto_resolve: str = "abort",
        collection_name: Optional[str] = None,
    ) -> UpdateResult:
        """Apply update using specified strategy.

        Takes the result from fetch_update() and applies it using one of three strategies:
        - overwrite: Replace local artifact completely with upstream version
        - merge: Use MergeEngine to perform 3-way merge (Phase 0 implementation)
        - prompt: Show diff summary and ask user for confirmation before applying

        Args:
            fetch_result: Result from fetch_update() containing temp workspace
            strategy: Update strategy ("overwrite", "merge", or "prompt")
            interactive: Whether to prompt user (for prompt strategy)
            auto_resolve: How to handle conflicts in non-interactive mode
                         - "abort": Cancel update on conflicts (safe default)
                         - "ours": Keep local changes when conflicts occur
                         - "theirs": Take upstream changes when conflicts occur
            collection_name: Collection name (uses active if None)

        Returns:
            UpdateResult describing outcome

        Raises:
            ValueError: Invalid strategy or fetch_result has error or invalid auto_resolve
        """
        import logging
        from rich.console import Console
        from rich.prompt import Confirm

        console = Console()

        # Validate fetch result
        if fetch_result.error:
            raise ValueError(f"Cannot apply update: {fetch_result.error}")

        if not fetch_result.has_update:
            raise ValueError("No update available to apply")

        if not fetch_result.temp_workspace or not fetch_result.temp_workspace.exists():
            raise ValueError("Temp workspace not found in fetch result")

        artifact = fetch_result.artifact
        update_info = fetch_result.update_info

        # Validate strategy
        valid_strategies = {"overwrite", "merge", "prompt"}
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy '{strategy}'. Must be one of {valid_strategies}"
            )

        # Validate auto_resolve
        valid_auto_resolve = {"abort", "ours", "theirs"}
        if auto_resolve not in valid_auto_resolve:
            raise ValueError(
                f"Invalid auto_resolve '{auto_resolve}'. Must be one of {valid_auto_resolve}"
            )

        # Handle non-interactive mode with prompt strategy
        if not interactive and strategy == "prompt":
            # Convert to appropriate strategy based on auto_resolve
            if auto_resolve == "abort":
                logging.info(
                    "Non-interactive mode with 'prompt' strategy and 'abort' resolution: "
                    "Skipping update"
                )
                return UpdateResult(
                    artifact=artifact,
                    updated=False,
                    status="skipped_non_interactive",
                    previous_version=artifact.resolved_version,
                    new_version=artifact.resolved_version,
                    previous_sha=artifact.resolved_sha,
                    new_sha=artifact.resolved_sha,
                )
            elif auto_resolve == "theirs":
                # Take upstream - use overwrite strategy
                strategy = "overwrite"
                logging.info(
                    "Non-interactive mode: Converting 'prompt' to 'overwrite' "
                    "(taking upstream)"
                )
            elif auto_resolve == "ours":
                # Keep local - skip update
                logging.info(
                    "Non-interactive mode: Keeping local changes (skipping update)"
                )
                return UpdateResult(
                    artifact=artifact,
                    updated=False,
                    status="kept_local_non_interactive",
                    previous_version=artifact.resolved_version,
                    new_version=artifact.resolved_version,
                    previous_sha=artifact.resolved_sha,
                    new_sha=artifact.resolved_sha,
                )

        # Load collection and get artifact paths
        collection = self.collection_mgr.load_collection(collection_name)
        collection_path, artifact_path = self._get_artifact_paths(collection, artifact)

        # Store previous version info for result
        previous_version = artifact.resolved_version
        previous_sha = artifact.resolved_sha

        # Get upstream artifact from temp workspace
        upstream_path = fetch_result.temp_workspace / "artifact"
        if not upstream_path.exists():
            raise ValueError(f"Artifact not found in temp workspace: {upstream_path}")

        # Create snapshot before applying update (for rollback safety)
        snapshot = None
        try:
            snapshot = self._auto_snapshot(
                collection.name,
                artifact,
                f"Before {strategy} update of {artifact.type.value}/{artifact.name}",
            )
        except Exception as snapshot_error:
            # Snapshot creation failed - log warning but continue
            # Update will proceed without rollback safety net
            logging.warning(
                f"Failed to create snapshot before update: {snapshot_error}. "
                f"Proceeding without rollback capability."
            )

        try:
            # Apply strategy
            if strategy == "overwrite":
                success = self._apply_overwrite_strategy(
                    artifact_path, upstream_path, artifact
                )
                if not success:
                    return UpdateResult(
                        artifact=artifact,
                        updated=False,
                        status="overwrite_failed",
                        previous_version=previous_version,
                        new_version=previous_version,
                        previous_sha=previous_sha,
                        new_sha=previous_sha,
                    )

            elif strategy == "merge":
                success = self._apply_merge_strategy(
                    artifact_path, upstream_path, artifact, collection_path, console
                )
                if not success:
                    return UpdateResult(
                        artifact=artifact,
                        updated=False,
                        status="merge_failed",
                        previous_version=previous_version,
                        new_version=previous_version,
                        previous_sha=previous_sha,
                        new_sha=previous_sha,
                    )

            elif strategy == "prompt":
                success = self._apply_prompt_strategy(
                    artifact_path,
                    upstream_path,
                    artifact,
                    interactive,
                    console,
                )
                if not success:
                    return UpdateResult(
                        artifact=artifact,
                        updated=False,
                        status="user_cancelled",
                        previous_version=previous_version,
                        new_version=previous_version,
                        previous_sha=previous_sha,
                        new_sha=previous_sha,
                    )

            # Update artifact metadata
            artifact.resolved_sha = (
                update_info.latest_sha if update_info else artifact.resolved_sha
            )
            artifact.resolved_version = (
                update_info.latest_version if update_info else artifact.resolved_version
            )
            artifact.last_updated = datetime.utcnow()

            # Extract metadata from updated artifact
            try:
                from skillmeat.utils.metadata import extract_artifact_metadata

                artifact.metadata = extract_artifact_metadata(
                    artifact_path, artifact.type
                )
            except Exception as e:
                logging.warning(f"Could not extract metadata: {e}")

            # Save collection (atomic write of manifest)
            self.collection_mgr.save_collection(collection)

            # Update lock file (atomic write)
            new_hash = self.compute_content_hash(artifact_path)
            self.collection_mgr.lock_mgr.update_entry(
                collection_path,
                artifact.name,
                artifact.type,
                artifact.upstream,
                artifact.resolved_sha,
                artifact.resolved_version,
                new_hash,
            )

            # Clean up temp workspace on success
            if fetch_result.temp_workspace and fetch_result.temp_workspace.exists():
                shutil.rmtree(fetch_result.temp_workspace, ignore_errors=True)

            # Track successful update event
            self._record_update_event(
                artifact=artifact,
                strategy=strategy,
                version_before=previous_version,
                version_after=artifact.resolved_version,
                conflicts_detected=0,  # Would need to track this from merge
                rollback=False,
            )

            return UpdateResult(
                artifact=artifact,
                updated=True,
                status=f"{strategy}_applied",
                previous_version=previous_version,
                new_version=artifact.resolved_version,
                previous_sha=previous_sha,
                new_sha=artifact.resolved_sha,
            )

        except Exception as e:
            # Rollback on failure - restore from snapshot if available
            if snapshot is not None:
                logging.error(
                    f"Update failed: {e}. Rolling back to snapshot {snapshot.id}..."
                )

                try:
                    # Restore collection from snapshot (includes manifest, lock, and artifact files)
                    from skillmeat.storage.snapshot import SnapshotManager

                    snapshots_dir = self.collection_mgr.config.get_snapshots_dir()
                    snapshot_mgr = SnapshotManager(snapshots_dir)
                    snapshot_mgr.restore_snapshot(snapshot, collection_path)

                    logging.info(f"Successfully rolled back to snapshot {snapshot.id}")

                    # Track rollback event
                    self._record_update_event(
                        artifact=artifact,
                        strategy=strategy,
                        version_before=previous_version,
                        version_after=previous_version,  # Rolled back
                        conflicts_detected=0,
                        rollback=True,
                    )
                except Exception as rollback_error:
                    logging.error(
                        f"CRITICAL: Rollback failed: {rollback_error}. "
                        f"Collection may be in inconsistent state. "
                        f"Manual restore from snapshot {snapshot.id} required."
                    )
                    # Re-raise original exception with rollback error context
                    raise RuntimeError(
                        f"Update failed and rollback also failed. "
                        f"Original error: {e}. Rollback error: {rollback_error}. "
                        f"Manual restore from snapshot {snapshot.id} may be required."
                    ) from e
                finally:
                    # Always clean up temp workspace, even on rollback failure
                    if (
                        fetch_result.temp_workspace
                        and fetch_result.temp_workspace.exists()
                    ):
                        try:
                            shutil.rmtree(
                                fetch_result.temp_workspace, ignore_errors=True
                            )
                        except Exception as cleanup_error:
                            logging.warning(
                                f"Failed to clean up temp workspace: {cleanup_error}"
                            )
            else:
                # No snapshot available - cannot rollback
                logging.error(
                    f"Update failed: {e}. No snapshot available for rollback. "
                    f"Collection may be in inconsistent state."
                )

                # Clean up temp workspace
                if fetch_result.temp_workspace and fetch_result.temp_workspace.exists():
                    try:
                        shutil.rmtree(fetch_result.temp_workspace, ignore_errors=True)
                    except Exception as cleanup_error:
                        logging.warning(
                            f"Failed to clean up temp workspace: {cleanup_error}"
                        )

            # Re-raise original exception after rollback attempt
            raise

    def _apply_overwrite_strategy(
        self, local_path: Path, upstream_path: Path, artifact: Artifact
    ) -> bool:
        """Apply overwrite strategy - replace local with upstream.

        Args:
            local_path: Path to local artifact
            upstream_path: Path to upstream artifact
            artifact: Artifact being updated

        Returns:
            True if successful, False otherwise
        """
        import logging

        try:
            logging.info(
                f"Applying overwrite strategy for {artifact.type.value}/{artifact.name}"
            )

            # Use FilesystemManager for atomic copy
            self.filesystem_mgr.copy_artifact(upstream_path, local_path, artifact.type)

            logging.info(
                f"Successfully overwrote {artifact.type.value}/{artifact.name}"
            )
            return True

        except Exception as e:
            logging.error(f"Overwrite failed: {e}")
            return False

    def _apply_merge_strategy(
        self,
        local_path: Path,
        upstream_path: Path,
        artifact: Artifact,
        collection_path: Path,
        console,
    ) -> bool:
        """Apply merge strategy - use MergeEngine for 3-way merge.

        For Phase 0, uses simple 3-way merge logic:
        - Base: Current artifact in collection
        - Local: Current artifact in collection (same as base for now)
        - Remote: Upstream artifact from temp workspace

        Phase 1 will enhance this with proper base version tracking.

        Args:
            local_path: Path to local artifact
            upstream_path: Path to upstream artifact
            artifact: Artifact being updated
            collection_path: Path to collection root
            console: Rich console for output

        Returns:
            True if successful, False otherwise
        """
        import logging
        import tempfile
        from skillmeat.core.merge_engine import MergeEngine

        try:
            logging.info(
                f"Applying merge strategy for {artifact.type.value}/{artifact.name}"
            )

            # For Phase 0: base == local (no separate base version tracking yet)
            # This will be enhanced in Phase 1 with proper base version from snapshots
            console.print(
                f"[yellow]Note: Phase 0 merge uses current version as base. "
                f"Full 3-way merge with tracked base version coming in Phase 1.[/yellow]"
            )

            # Create merge engine
            merge_engine = MergeEngine()

            # Create temp directory for merge output
            with tempfile.TemporaryDirectory() as temp_dir:
                merge_output = Path(temp_dir) / "merged"

                # Perform 3-way merge
                # Base and local are the same (current artifact)
                merge_result = merge_engine.merge(
                    base_path=local_path,
                    local_path=local_path,
                    remote_path=upstream_path,
                    output_path=merge_output,
                )

                if merge_result.has_conflicts:
                    console.print(
                        f"[yellow]Merge resulted in {len(merge_result.conflicts)} conflicts.[/yellow]"
                    )
                    console.print(
                        f"[yellow]Conflict files will be preserved with markers.[/yellow]"
                    )

                # Log merge statistics
                console.print(f"[green]{merge_result.summary()}[/green]")

                # Copy merged result to local path
                self.filesystem_mgr.copy_artifact(
                    merge_output, local_path, artifact.type
                )

                logging.info(
                    f"Successfully merged {artifact.type.value}/{artifact.name}"
                )
                return True

        except Exception as e:
            logging.error(f"Merge failed: {e}")
            console.print(f"[red]Merge failed: {e}[/red]")
            return False

    def _apply_prompt_strategy(
        self,
        local_path: Path,
        upstream_path: Path,
        artifact: Artifact,
        interactive: bool,
        console,
    ) -> bool:
        """Apply prompt strategy - show diff and ask user for confirmation.

        Args:
            local_path: Path to local artifact
            upstream_path: Path to upstream artifact
            artifact: Artifact being updated
            interactive: Whether to prompt user
            console: Rich console for output

        Returns:
            True if user confirmed and update applied, False otherwise
        """
        import logging
        from skillmeat.core.diff_engine import DiffEngine
        from rich.prompt import Confirm

        try:
            logging.info(
                f"Applying prompt strategy for {artifact.type.value}/{artifact.name}"
            )

            # Show enhanced preview with conflict detection
            artifact_ref = f"{artifact.type.value}/{artifact.name}"
            preview_data = self._show_update_preview(
                artifact_ref=artifact_ref,
                current_path=local_path,
                update_path=upstream_path,
                strategy="prompt",
                console=console,
            )

            # Get strategy recommendation
            # Note: For prompt strategy, we don't have local modifications info here
            # so we use the diff result only
            recommended_strategy, reason = self._recommend_strategy(
                diff_result=preview_data["diff_result"],
                has_local_modifications=False,  # Assume no local mods for prompt
            )

            # Show recommendation
            if recommended_strategy != "prompt":
                console.print(
                    f"\n[bold]Recommendation:[/bold] [cyan]{recommended_strategy}[/cyan]"
                )
                console.print(f"  Reason: {reason}")

            # Prompt user if interactive
            if interactive:
                console.print()
                if not Confirm.ask(
                    f"Apply this update to {artifact.type.value}/{artifact.name}?",
                    default=False,
                ):
                    console.print("[yellow]Update cancelled by user.[/yellow]")
                    return False
            else:
                console.print("[yellow]Non-interactive mode: skipping update.[/yellow]")
                return False

            # User confirmed - apply overwrite
            console.print(f"[green]Applying update...[/green]")
            return self._apply_overwrite_strategy(local_path, upstream_path, artifact)

        except Exception as e:
            logging.error(f"Prompt strategy failed: {e}")
            console.print(f"[red]Error: {e}[/red]")
            return False

    def update(
        self,
        artifact_name: str,
        artifact_type: Optional[ArtifactType] = None,
        collection_name: Optional[str] = None,
        strategy: UpdateStrategy = UpdateStrategy.PROMPT,
    ) -> UpdateResult:
        """Update artifact from upstream or refresh local artifacts.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type (required if ambiguous)
            collection_name: Collection name (uses active if None)
            strategy: Update strategy (PROMPT, TAKE_UPSTREAM, KEEP_LOCAL)

        Returns:
            UpdateResult describing outcome

        Raises:
            ValueError: Artifact not found or unsupported origin
        """
        collection = self.collection_mgr.load_collection(collection_name)
        artifact = collection.find_artifact(artifact_name, artifact_type)

        if not artifact:
            raise ValueError(f"Artifact '{artifact_name}' not found")

        if artifact.origin == "github":
            return self._update_github_artifact(collection, artifact, strategy)
        if artifact.origin == "local":
            return self._refresh_local_artifact(collection, artifact)

        raise ValueError(f"Unsupported artifact origin: {artifact.origin}")

    def _update_github_artifact(
        self, collection, artifact: Artifact, strategy: UpdateStrategy
    ) -> UpdateResult:
        """Update GitHub-backed artifact."""
        if not artifact.upstream:
            return UpdateResult(
                artifact=artifact,
                updated=False,
                status="no_upstream",
                previous_version=artifact.resolved_version,
                new_version=artifact.resolved_version,
                previous_sha=artifact.resolved_sha,
                new_sha=artifact.resolved_sha,
            )

        collection_path, artifact_path = self._get_artifact_paths(collection, artifact)
        has_local_modifications = self._detect_local_modifications(
            collection_path, artifact, artifact_path
        )

        update_info = self.github_source.check_updates(artifact)
        if not update_info or not update_info.has_update:
            return UpdateResult(
                artifact=artifact,
                updated=False,
                status="up_to_date",
                previous_version=artifact.resolved_version,
                new_version=artifact.resolved_version,
                previous_sha=artifact.resolved_sha,
                new_sha=artifact.resolved_sha,
                local_modifications=has_local_modifications,
            )

        if has_local_modifications:
            if strategy == UpdateStrategy.KEEP_LOCAL:
                return UpdateResult(
                    artifact=artifact,
                    updated=False,
                    status="local_changes_kept",
                    previous_version=artifact.resolved_version,
                    new_version=artifact.resolved_version,
                    previous_sha=artifact.resolved_sha,
                    new_sha=artifact.resolved_sha,
                    local_modifications=True,
                )
            if strategy == UpdateStrategy.PROMPT:
                prompt = (
                    f"Local modifications detected for "
                    f"{artifact.type.value}/{artifact.name}. "
                    "Overwrite with upstream changes?"
                )
                if not Confirm.ask(prompt, default=False):
                    return UpdateResult(
                        artifact=artifact,
                        updated=False,
                        status="cancelled",
                        previous_version=artifact.resolved_version,
                        new_version=artifact.resolved_version,
                        previous_sha=artifact.resolved_sha,
                        new_sha=artifact.resolved_sha,
                        local_modifications=True,
                    )

        previous_version = artifact.resolved_version
        previous_sha = artifact.resolved_sha

        override_version = update_info.latest_sha or artifact.version_spec
        spec = self._build_spec_from_artifact(
            artifact, version_override=override_version
        )

        self._auto_snapshot(
            collection.name,
            artifact,
            f"Before updating {artifact.type.value}/{artifact.name}",
        )

        fetch_result = self.github_source.fetch(spec, artifact.type)

        self.filesystem_mgr.copy_artifact(
            fetch_result.artifact_path, artifact_path, artifact.type
        )

        artifact.metadata = fetch_result.metadata
        artifact.upstream = fetch_result.upstream_url or artifact.upstream
        artifact.resolved_sha = fetch_result.resolved_sha or update_info.latest_sha
        artifact.resolved_version = (
            fetch_result.resolved_version
            if fetch_result.resolved_version is not None
            else update_info.latest_version or artifact.resolved_version
        )
        artifact.last_updated = datetime.utcnow()

        self.collection_mgr.save_collection(collection)

        new_hash = self.compute_content_hash(artifact_path)
        self.collection_mgr.lock_mgr.update_entry(
            collection_path,
            artifact.name,
            artifact.type,
            artifact.upstream,
            artifact.resolved_sha,
            artifact.resolved_version,
            new_hash,
        )

        return UpdateResult(
            artifact=artifact,
            updated=True,
            status="updated_github",
            previous_version=previous_version,
            new_version=artifact.resolved_version,
            previous_sha=previous_sha,
            new_sha=artifact.resolved_sha,
            local_modifications=has_local_modifications,
        )

    def _refresh_local_artifact(self, collection, artifact: Artifact) -> UpdateResult:
        """Refresh metadata/hash for local artifacts."""
        collection_path, artifact_path = self._get_artifact_paths(collection, artifact)

        try:
            from skillmeat.utils.metadata import extract_artifact_metadata

            metadata = extract_artifact_metadata(artifact_path, artifact.type)
        except Exception:
            metadata = artifact.metadata

        previous_version = artifact.metadata.version

        self._auto_snapshot(
            collection.name,
            artifact,
            f"Before refreshing {artifact.type.value}/{artifact.name}",
        )

        artifact.metadata = metadata
        artifact.last_updated = datetime.utcnow()

        self.collection_mgr.save_collection(collection)

        new_hash = self.compute_content_hash(artifact_path)
        self.collection_mgr.lock_mgr.update_entry(
            collection_path,
            artifact.name,
            artifact.type,
            None,
            None,
            None,
            new_hash,
        )

        return UpdateResult(
            artifact=artifact,
            updated=True,
            status="refreshed_local",
            previous_version=previous_version,
            new_version=metadata.version,
        )

    def _get_artifact_paths(self, collection, artifact: Artifact) -> tuple[Path, Path]:
        """Return collection and artifact paths (validate existence)."""
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )
        artifact_path = collection_path / artifact.path

        if not artifact_path.exists():
            raise ValueError(
                f"Artifact files missing for {artifact.type.value}/{artifact.name}"
            )

        return collection_path, artifact_path

    def _detect_local_modifications(
        self, collection_path: Path, artifact: Artifact, artifact_path: Path
    ) -> bool:
        """Check if artifact has diverged from lock entry."""
        lock_entry = self.collection_mgr.lock_mgr.get_entry(
            collection_path, artifact.name, artifact.type
        )

        if not lock_entry:
            return False

        try:
            current_hash = self.compute_content_hash(artifact_path)
        except FileNotFoundError:
            return False

        return current_hash != lock_entry.content_hash

    def _build_spec_from_artifact(
        self, artifact: Artifact, version_override: Optional[str] = None
    ) -> str:
        """Reconstruct GitHub spec from stored upstream URL."""
        if not artifact.upstream:
            raise ValueError(
                f"Artifact '{artifact.name}' does not have an upstream reference"
            )

        parsed = urlparse(artifact.upstream)
        parts = parsed.path.strip("/").split("/")

        if len(parts) < 3 or parts[2] != "tree":
            raise ValueError(f"Unsupported upstream URL format: {artifact.upstream}")

        username, repo = parts[0], parts[1]
        path_parts = parts[4:] if len(parts) > 4 else []
        rel_path = "/".join(path_parts) if path_parts else ""
        version_spec = version_override or artifact.version_spec or "latest"

        if rel_path:
            return f"{username}/{repo}/{rel_path}@{version_spec}"
        return f"{username}/{repo}@{version_spec}"

    def _record_update_event(
        self,
        artifact: Artifact,
        strategy: str,
        version_before: Optional[str] = None,
        version_after: Optional[str] = None,
        conflicts_detected: int = 0,
        rollback: bool = False,
        user_choice: Optional[str] = None,
    ) -> None:
        """Record update event for analytics.

        Args:
            artifact: Artifact being updated
            strategy: Update strategy (overwrite, merge, prompt)
            version_before: Optional version before update
            version_after: Optional version after update
            conflicts_detected: Number of conflicts detected
            rollback: Whether update was rolled back
            user_choice: Optional user choice (proceed, cancel)
        """
        try:
            from skillmeat.core.analytics import EventTracker

            # Get collection name
            collection_name = "default"
            try:
                collection = self.collection_mgr.get_active_collection()
                collection_name = collection.name if collection else "default"
            except Exception:
                pass

            # Record update event
            with EventTracker() as tracker:
                tracker.track_update(
                    artifact_name=artifact.name,
                    artifact_type=artifact.type.value,
                    collection_name=collection_name,
                    strategy=strategy,
                    version_before=version_before,
                    version_after=version_after,
                    conflicts_detected=conflicts_detected,
                    user_choice=user_choice,
                    rollback=rollback,
                )

        except Exception as e:
            # Never fail update due to analytics
            logging.debug(f"Failed to record update analytics: {e}")

    def _record_remove_event(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        reason: str = "user_action",
        from_project: bool = False,
    ) -> None:
        """Record remove event for analytics.

        Args:
            artifact_name: Name of artifact being removed
            artifact_type: Type of artifact
            collection_name: Name of collection
            reason: Reason for removal (default: user_action)
            from_project: Whether removing from project (default: False)
        """
        try:
            from skillmeat.core.analytics import EventTracker

            # Record remove event
            with EventTracker() as tracker:
                tracker.track_remove(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    reason=reason,
                    from_project=from_project,
                )

        except Exception as e:
            # Never fail remove due to analytics
            logging.debug(f"Failed to record remove analytics: {e}")

    def _auto_snapshot(self, collection_name: str, artifact: Artifact, message: str):
        """Create safety snapshot before mutating artifact.

        Returns:
            Snapshot object if successful, None if snapshot creation failed
        """
        from skillmeat.core.version import VersionManager

        try:
            version_mgr = VersionManager(self.collection_mgr)
            snapshot = version_mgr.auto_snapshot(collection_name, message)
            return snapshot
        except Exception as e:
            # Snapshot best-effort; don't block updates if snapshot fails
            # But log warning so user knows rollback may not be available
            logging.warning(
                f"Failed to create snapshot before updating {artifact.name}: {e}. "
                "Rollback may not be available if update fails."
            )
            return None
