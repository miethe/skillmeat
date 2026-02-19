"""Deployment tracking and management for SkillMeat."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.prompt import Confirm

from skillmeat.core.artifact import Artifact, ArtifactType
from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import (
    DEFAULT_ARTIFACT_PATH_MAP,
    DEFAULT_PROFILE_ROOT_DIR,
    DeploymentPathProfile,
    default_profile,
    normalize_profile,
    resolve_artifact_path,
    resolve_deployment_path,
    resolve_profile_root,
)
from skillmeat.utils.filesystem import FilesystemManager, compute_content_hash

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class Deployment:
    """Tracks artifact deployment to a project with version tracking."""

    # Core identification
    artifact_name: str
    artifact_type: str  # Store as string for TOML serialization
    from_collection: str

    # Deployment metadata
    deployed_at: datetime
    artifact_path: Path  # Relative path within profile root (e.g., "commands/review.md")

    # Version tracking (ADR-004)
    content_hash: str  # SHA-256 hash of artifact content at deployment time
    local_modifications: bool = False

    # Optional version tracking fields
    parent_hash: Optional[str] = (
        None  # Hash of parent version (if deployed from collection)
    )
    version_lineage: List[str] = field(
        default_factory=list
    )  # Array of version hashes (newest first)
    last_modified_check: Optional[datetime] = None  # Last drift check timestamp
    modification_detected_at: Optional[datetime] = (
        None  # When modification was first detected
    )
    merge_base_snapshot: Optional[str] = (
        None  # Content hash (SHA-256) used as merge base for 3-way merges
    )
    deployment_profile_id: Optional[str] = None
    platform: Optional[Platform] = None
    profile_root_dir: Optional[str] = None

    # Stable cross-context identity (ADR-007); optional — absent when artifact not yet in cache
    artifact_uuid: Optional[str] = None

    # Deprecated field for backward compatibility
    collection_sha: Optional[str] = None  # Deprecated: use content_hash instead

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result = {
            "artifact_name": self.artifact_name,
            "artifact_type": self.artifact_type,
            "from_collection": self.from_collection,
            "deployed_at": self.deployed_at.isoformat(),
            "artifact_path": str(self.artifact_path),
            "content_hash": self.content_hash,
            "local_modifications": self.local_modifications,
        }

        # Add optional fields if present
        if self.parent_hash:
            result["parent_hash"] = self.parent_hash

        if self.version_lineage:
            result["version_lineage"] = self.version_lineage

        if self.last_modified_check:
            result["last_modified_check"] = self.last_modified_check.isoformat()

        if self.modification_detected_at:
            result["modification_detected_at"] = (
                self.modification_detected_at.isoformat()
            )

        if self.merge_base_snapshot:
            result["merge_base_snapshot"] = self.merge_base_snapshot
        if self.deployment_profile_id:
            result["deployment_profile_id"] = self.deployment_profile_id
        if self.platform:
            result["platform"] = (
                self.platform.value
                if isinstance(self.platform, Platform)
                else str(self.platform)
            )
        if self.profile_root_dir:
            result["profile_root_dir"] = self.profile_root_dir
        if self.artifact_uuid is not None:
            result["artifact_uuid"] = self.artifact_uuid

        # Keep collection_sha for backward compatibility (same as content_hash)
        result["collection_sha"] = self.content_hash

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deployment":
        """Create from dictionary (TOML deserialization).

        Supports backward compatibility with old deployment records.
        """
        # Handle backward compatibility: use collection_sha if content_hash missing
        content_hash = data.get("content_hash") or data.get("collection_sha")
        if not content_hash:
            raise ValueError("Deployment record missing content_hash or collection_sha")

        # Parse optional datetime fields
        last_modified_check = None
        if "last_modified_check" in data:
            last_modified_check = datetime.fromisoformat(data["last_modified_check"])

        modification_detected_at = None
        if "modification_detected_at" in data:
            modification_detected_at = datetime.fromisoformat(
                data["modification_detected_at"]
            )

        # Handle version_lineage: initialize with content_hash if not present
        version_lineage = data.get("version_lineage")
        if version_lineage is None:
            version_lineage = [content_hash]

        return cls(
            artifact_name=data["artifact_name"],
            artifact_type=data["artifact_type"],
            from_collection=data["from_collection"],
            deployed_at=datetime.fromisoformat(data["deployed_at"]),
            artifact_path=Path(data["artifact_path"]),
            content_hash=content_hash,
            local_modifications=data.get("local_modifications", False),
            parent_hash=data.get("parent_hash"),
            version_lineage=version_lineage,
            last_modified_check=last_modified_check,
            modification_detected_at=modification_detected_at,
            merge_base_snapshot=data.get("merge_base_snapshot"),
            deployment_profile_id=data.get("deployment_profile_id"),
            platform=(
                Platform(data["platform"])
                if data.get("platform") is not None
                else None
            ),
            profile_root_dir=data.get("profile_root_dir"),
            artifact_uuid=data.get("artifact_uuid"),  # ADR-007; absent in old files
            collection_sha=data.get("collection_sha"),  # Keep for backward compat
        )


class DeploymentManager:
    """Manages artifact deployment to projects."""

    def __init__(self, collection_mgr=None, version_mgr=None):
        """Initialize deployment manager.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
            version_mgr: VersionManager instance for automatic version capture
        """
        if collection_mgr is None:
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager()

        self.collection_mgr = collection_mgr
        self.filesystem_mgr = FilesystemManager()

        # Lazy initialize VersionManager if not provided
        self._version_mgr = version_mgr

    @property
    def version_mgr(self):
        """Lazy-load VersionManager on first access."""
        if self._version_mgr is None:
            from skillmeat.core.version import VersionManager

            self._version_mgr = VersionManager(collection_mgr=self.collection_mgr)
        return self._version_mgr

    def _fallback_profile(self, profile_id: Optional[str]) -> DeploymentPathProfile:
        """Build a deterministic profile when cache profile metadata is unavailable."""
        if not profile_id or profile_id == "claude_code":
            return default_profile()

        platform_map = {
            "claude_code": Platform.CLAUDE_CODE,
            "codex": Platform.CODEX,
            "gemini": Platform.GEMINI,
            "cursor": Platform.CURSOR,
        }
        platform = platform_map.get(profile_id, Platform.OTHER)
        root_dir = (
            {
                "claude_code": ".claude",
                "codex": ".codex",
                "gemini": ".gemini",
                "cursor": ".cursor",
            }.get(profile_id)
            or f".{profile_id}"
        )
        return DeploymentPathProfile(
            profile_id=profile_id,
            platform=platform,
            root_dir=root_dir,
            artifact_path_map=DEFAULT_ARTIFACT_PATH_MAP.copy(),
        )

    def _resolve_target_profiles(
        self,
        project_path: Path,
        profile_id: Optional[str] = None,
        all_profiles: bool = False,
    ) -> List[DeploymentPathProfile]:
        """Resolve deployment profiles for a project with backward-compat fallback."""
        try:
            import uuid

            from skillmeat.cache.models import Project, get_session
            from skillmeat.cache.repositories import DeploymentProfileRepository

            resolved_project_path = Path(project_path).resolve()
            session = get_session()
            try:
                project = (
                    session.query(Project)
                    .filter(Project.path == str(resolved_project_path))
                    .first()
                )
                if project is None:
                    project = Project(
                        id=uuid.uuid4().hex,
                        name=resolved_project_path.name,
                        path=str(resolved_project_path),
                        status="active",
                    )
                    session.add(project)
                    session.commit()
                    session.refresh(project)
            finally:
                session.close()

            repo = DeploymentProfileRepository()
            if all_profiles:
                profiles = repo.list_all_profiles(project.id)
                if not profiles:
                    profiles = [repo.ensure_default_claude_profile(project.id)]
            elif profile_id:
                profile = repo.read_by_project_and_profile_id(project.id, profile_id)
                if not profile:
                    raise ValueError(
                        f"Deployment profile '{profile_id}' not found for project"
                    )
                profiles = [profile]
            else:
                primary = repo.get_primary_profile(project.id)
                if primary is None:
                    primary = repo.ensure_default_claude_profile(project.id)
                profiles = [primary]

            return [normalize_profile(profile) for profile in profiles]
        except Exception as exc:
            logger.debug(
                "Falling back to implicit profile resolution for %s: %s",
                project_path,
                exc,
            )
            if all_profiles:
                return [default_profile()]
            return [self._fallback_profile(profile_id)]

    def deploy_artifacts(
        self,
        artifact_names: List[str],
        collection_name: Optional[str] = None,
        project_path: Optional[Path] = None,
        artifact_type: Optional[ArtifactType] = None,
        overwrite: bool = False,
        dest_path: Optional[str] = None,
        profile_id: Optional[str] = None,
        all_profiles: bool = False,
    ) -> List[Deployment]:
        """Deploy specified artifacts to project.

        Args:
            artifact_names: List of artifact names to deploy
            collection_name: Source collection (uses active if None)
            project_path: Project directory (uses CWD if None)
            artifact_type: Filter artifacts by type (if ambiguous names)
            overwrite: If True, skip interactive prompt and overwrite existing artifacts
            dest_path: Custom destination path relative to project root
                (e.g., '.claude/skills/dev/'). If provided, artifact will be
                deployed to {dest_path}/{artifact_name}/. Should be pre-validated.
            profile_id: Optional deployment profile identifier.
            all_profiles: Deploy to all project profiles if True.

        Returns:
            List of Deployment objects

        Raises:
            ValueError: Artifact not found or ambiguous name
        """
        from skillmeat.storage.deployment import DeploymentTracker

        # Load collection
        collection = self.collection_mgr.load_collection(collection_name)
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )

        # Resolve project path
        if project_path is None:
            project_path = Path.cwd()
        else:
            project_path = Path(project_path).resolve()

        # Backward compatibility: ensure default profile metadata exists.
        self._resolve_target_profiles(project_path=project_path)

        deployments: List[Deployment] = []
        profiles = self._resolve_target_profiles(
            project_path=project_path,
            profile_id=profile_id,
            all_profiles=all_profiles,
        )

        for artifact_name in artifact_names:
            # Find artifact
            artifact = collection.find_artifact(artifact_name, artifact_type)
            if not artifact:
                console.print(
                    f"[yellow]Warning:[/yellow] Artifact '{artifact_name}' not found, skipping"
                )
                continue

            source_path = collection_path / artifact.path
            for profile in profiles:
                dest_base = resolve_profile_root(project_path, profile=profile)

                if dest_path:
                    if artifact.type in (ArtifactType.SKILL, ArtifactType.MCP, ArtifactType.COMPOSITE):
                        final_dest_path = project_path / dest_path / artifact.name
                    else:
                        final_dest_path = (
                            project_path / dest_path / f"{artifact.name}.md"
                        )
                else:
                    final_dest_path = resolve_artifact_path(
                        artifact_name=artifact.name,
                        artifact_type=artifact.type.value,
                        project_path=project_path,
                        profile=profile,
                    )

                try:
                    final_dest_path.resolve(strict=False).relative_to(
                        project_path.resolve()
                    )
                except ValueError:
                    raise ValueError(
                        f"Destination path '{final_dest_path}' is outside project directory"
                    )

                if final_dest_path.exists():
                    console.print(
                        f"[yellow]Warning:[/yellow] {final_dest_path} already exists"
                    )
                    if not overwrite:
                        prompt_name = f"{artifact.name} ({profile.profile_id})"
                        if not Confirm.ask(f"Overwrite {prompt_name}?"):
                            console.print(f"[yellow]Skipped:[/yellow] {prompt_name}")
                            continue

                try:
                    self.filesystem_mgr.copy_artifact(
                        source_path, final_dest_path, artifact.type
                    )
                    console.print(
                        f"[green][/green] Deployed {artifact.type.value}/{artifact.name} -> {profile.profile_id}"
                    )
                except Exception as e:
                    console.print(
                        f"[red]Error deploying {artifact.name} ({profile.profile_id}):[/red] {e}"
                    )
                    continue

                content_hash = compute_content_hash(final_dest_path)

                try:
                    artifact_path = final_dest_path.resolve(strict=False).relative_to(
                        dest_base
                    )
                except ValueError:
                    artifact_path = final_dest_path.resolve(strict=False).relative_to(
                        project_path.resolve()
                    )

                artifact_uuid = self._lookup_artifact_uuid(
                    artifact_name=artifact.name,
                    artifact_type=artifact.type.value,
                    project_path=project_path,
                )
                DeploymentTracker.record_deployment(
                    project_path=project_path,
                    artifact=artifact,
                    collection_name=collection.name,
                    collection_sha=content_hash,
                    deployment_profile_id=profile.profile_id,
                    platform=profile.platform.value,
                    profile_root_dir=profile.root_dir,
                    artifact_path=artifact_path,
                    artifact_path_map=dict(profile.artifact_path_map),
                    artifact_uuid=artifact_uuid,
                )

                self._record_deployment_version(
                    artifact_name=artifact.name,
                    artifact_type=artifact.type.value,
                    project_path=project_path,
                    content_hash=content_hash,
                )

                deployment = Deployment(
                    artifact_name=artifact.name,
                    artifact_type=artifact.type.value,
                    from_collection=collection.name,
                    deployed_at=datetime.now(),
                    artifact_path=artifact_path,
                    content_hash=content_hash,
                    local_modifications=False,
                    merge_base_snapshot=content_hash,
                    deployment_profile_id=profile.profile_id,
                    platform=profile.platform,
                    profile_root_dir=profile.root_dir,
                )
                deployments.append(deployment)

                self._record_deploy_event(
                    artifact_name=artifact.name,
                    artifact_type=artifact.type.value,
                    collection_name=collection.name,
                    project_path=project_path,
                    version=artifact.metadata.version,
                    sha=content_hash,
                    success=True,
                )

        # Capture version snapshot after successful deployment (SVCV-003)
        if deployments:
            try:
                # Create descriptive message for the snapshot
                artifact_list = ", ".join([d.artifact_name for d in deployments[:3]])
                if len(deployments) > 3:
                    artifact_list += f" and {len(deployments) - 3} more"

                message = f"Auto-deploy: {artifact_list} to {project_path} at {datetime.now().isoformat()}"

                console.print(f"[dim]Creating snapshot after deployment...[/dim]")
                snapshot = self.version_mgr.auto_snapshot(
                    collection_name=collection.name,
                    message=message,
                )
                console.print(f"[dim]Snapshot created: {snapshot.id}[/dim]")
            except Exception as e:
                # Never fail deploy due to snapshot failure
                console.print(
                    f"[yellow]Warning: Failed to create auto-snapshot: {e}[/yellow]"
                )

        return deployments

    def deploy_all(
        self,
        collection_name: Optional[str] = None,
        project_path: Optional[Path] = None,
        profile_id: Optional[str] = None,
        all_profiles: bool = False,
    ) -> List[Deployment]:
        """Deploy entire collection to project.

        Args:
            collection_name: Source collection (uses active if None)
            project_path: Project directory (uses CWD if None)

        Returns:
            List of Deployment objects
        """
        collection = self.collection_mgr.load_collection(collection_name)
        artifact_names = [a.name for a in collection.artifacts]
        return self.deploy_artifacts(
            artifact_names,
            collection_name,
            project_path,
            profile_id=profile_id,
            all_profiles=all_profiles,
        )

    def undeploy(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        project_path: Optional[Path] = None,
        profile_id: Optional[str] = None,
    ) -> None:
        """Remove artifact from project.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type
            project_path: Project directory (uses CWD if None)
        """
        from skillmeat.storage.deployment import DeploymentTracker

        if project_path is None:
            project_path = Path.cwd()
        else:
            project_path = Path(project_path).resolve()

        # Backward compatibility: ensure default profile metadata exists.
        self._resolve_target_profiles(project_path=project_path, profile_id=profile_id)

        # Get deployment record
        deployment = DeploymentTracker.get_deployment(
            project_path,
            artifact_name,
            artifact_type.value,
            profile_id=profile_id,
        )

        if not deployment:
            raise ValueError(
                f"Artifact '{artifact_name}' is not deployed to this project"
            )

        # Remove files
        artifact_path = resolve_deployment_path(
            deployment_relative_path=deployment.artifact_path,
            project_path=project_path,
            profile=DeploymentPathProfile(
                profile_id=deployment.deployment_profile_id or "claude_code",
                root_dir=deployment.profile_root_dir or DEFAULT_PROFILE_ROOT_DIR,
            ),
        )
        if artifact_path.exists():
            self.filesystem_mgr.remove_artifact(artifact_path)
            console.print(
                f"[green][/green] Removed {artifact_type.value}/{artifact_name}"
            )

        # Remove deployment record
        DeploymentTracker.remove_deployment(
            project_path,
            artifact_name,
            artifact_type.value,
            profile_id=profile_id or deployment.deployment_profile_id,
        )

        # Track remove event (from project)
        try:
            from skillmeat.core.analytics import EventTracker

            with EventTracker() as tracker:
                tracker.track_remove(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type.value,
                    collection_name=deployment.from_collection,
                    reason="user_action",
                    from_project=True,
                )
        except Exception as e:
            # Never fail undeploy due to analytics
            console.print(f"[dim]Debug: Failed to record remove analytics: {e}[/dim]")

    def list_deployments(
        self,
        project_path: Optional[Path] = None,
        profile_id: Optional[str] = None,
    ) -> List[Deployment]:
        """List all deployed artifacts in project.

        Args:
            project_path: Project directory (uses CWD if None)

        Returns:
            List of Deployment objects
        """
        from skillmeat.storage.deployment import DeploymentTracker

        if project_path is None:
            project_path = Path.cwd()
        else:
            project_path = Path(project_path).resolve()

        deployments = DeploymentTracker.read_deployments(
            project_path, profile_root_dir=None
        )
        if profile_id is None:
            return deployments
        return [
            deployment
            for deployment in deployments
            if (deployment.deployment_profile_id or "claude_code") == profile_id
        ]

    def check_deployment_status(
        self,
        project_path: Optional[Path] = None,
        profile_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Check sync status of deployed artifacts.

        Args:
            project_path: Project directory (uses CWD if None)

        Returns:
            Dict mapping artifact key to status: "synced", "modified", "outdated"
        """
        from skillmeat.storage.deployment import DeploymentTracker

        if project_path is None:
            project_path = Path.cwd()
        else:
            project_path = Path(project_path).resolve()

        deployments = DeploymentTracker.read_deployments(
            project_path, profile_root_dir=None
        )
        if profile_id:
            deployments = [
                d
                for d in deployments
                if (d.deployment_profile_id or "claude_code") == profile_id
            ]

        base_key_counts: Dict[str, int] = {}
        for deployment in deployments:
            base_key = f"{deployment.artifact_name}::{deployment.artifact_type}"
            base_key_counts[base_key] = base_key_counts.get(base_key, 0) + 1

        status: Dict[str, str] = {}

        for deployment in deployments:
            base_key = f"{deployment.artifact_name}::{deployment.artifact_type}"
            if base_key_counts[base_key] > 1:
                profile_key = deployment.deployment_profile_id or "claude_code"
                key = f"{base_key}::{profile_key}"
            else:
                key = base_key

            # Check for local modifications
            if DeploymentTracker.detect_modifications(
                project_path,
                deployment.artifact_name,
                deployment.artifact_type,
                profile_id=deployment.deployment_profile_id,
            ):
                status[key] = "modified"
            else:
                status[key] = "synced"

            # TODO: Check for upstream updates (requires collection loading)
            # This will be expanded in later phases

        return status

    def _record_deployment_version(
        self,
        artifact_name: str,
        artifact_type: str,
        project_path: Path,
        content_hash: str,
    ) -> None:
        """Record artifact version in cache database for deployment.

        Creates an ArtifactVersion record with:
        - parent_hash = NULL (root version)
        - change_origin = 'deployment'
        - version_lineage = [content_hash]

        Args:
            artifact_name: Name of artifact deployed
            artifact_type: Type of artifact
            project_path: Path to project
            content_hash: SHA-256 hash of deployed artifact content
        """
        try:
            from skillmeat.cache.models import Artifact as CacheArtifact
            from skillmeat.cache.models import get_session
            from skillmeat.core.version_tracking import create_deployment_version

            session = get_session()
            try:
                # Find or create Artifact record in cache
                # Use composite key: project_path + artifact_name + artifact_type
                artifact_id = f"{project_path}::{artifact_name}::{artifact_type}"

                cache_artifact = (
                    session.query(CacheArtifact)
                    .filter_by(
                        name=artifact_name,
                        type=artifact_type,
                    )
                    .join(CacheArtifact.project)
                    .filter_by(path=str(project_path))
                    .first()
                )

                if not cache_artifact:
                    # Artifact not in cache yet - version tracking will be added
                    # when cache is populated by cache manager
                    console.print(
                        f"[dim]Note: Artifact {artifact_name} not in cache yet, "
                        "skipping version tracking[/dim]"
                    )
                    return

                # Create version record
                create_deployment_version(
                    session=session,
                    artifact_id=cache_artifact.id,
                    content_hash=content_hash,
                )
                session.commit()

                console.print(
                    f"[dim]Version tracked: {artifact_name} "
                    f"({content_hash[:8]}...) origin=deployment[/dim]"
                )

            finally:
                session.close()

        except Exception as e:
            # Never fail deploy due to version tracking
            console.print(
                f"[yellow]Warning: Failed to record deployment version: {e}[/yellow]"
            )

    def _record_deploy_event(
        self,
        artifact_name: str,
        artifact_type: str,
        collection_name: str,
        project_path: Path,
        version: Optional[str] = None,
        sha: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Record deploy event for analytics.

        Args:
            artifact_name: Name of artifact deployed
            artifact_type: Type of artifact
            collection_name: Name of collection
            project_path: Path to project
            version: Optional artifact version
            sha: Optional artifact SHA
            success: Whether deployment succeeded
        """
        try:
            from skillmeat.core.analytics import EventTracker

            with EventTracker() as tracker:
                tracker.track_deploy(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection_name,
                    project_path=str(project_path),
                    version=version,
                    sha=sha,
                    success=success,
                )

        except Exception as e:
            # Never fail deploy due to analytics
            console.print(f"[dim]Debug: Failed to record deploy analytics: {e}[/dim]")

    def _lookup_artifact_uuid(
        self,
        artifact_name: str,
        artifact_type: str,
        project_path: Path,
    ) -> Optional[str]:
        """Look up the stable UUID for an artifact from the DB cache.

        Queries the cache Artifact model using the project path + name + type composite
        key.  Returns None (never raises) when the artifact is not yet cached so callers
        can always omit the field gracefully.

        Args:
            artifact_name: Artifact name
            artifact_type: Artifact type string (e.g. "skill")
            project_path: Resolved project root directory

        Returns:
            32-char hex UUID string from CachedArtifact.uuid, or None if not found
        """
        try:
            from skillmeat.cache.models import Artifact as CacheArtifact
            from skillmeat.cache.models import get_session

            session = get_session()
            try:
                cache_artifact = (
                    session.query(CacheArtifact)
                    .filter_by(
                        name=artifact_name,
                        type=artifact_type,
                    )
                    .join(CacheArtifact.project)
                    .filter_by(path=str(project_path))
                    .first()
                )
                if cache_artifact is not None:
                    return cache_artifact.uuid
            finally:
                session.close()
        except Exception as e:
            logger.debug(
                "UUID lookup failed for %s/%s in %s: %s",
                artifact_type,
                artifact_name,
                project_path,
                e,
            )
        return None
