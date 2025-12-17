"""Deployment tracking and management for SkillMeat."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.prompt import Confirm

from skillmeat.core.artifact import Artifact, ArtifactType
from skillmeat.utils.filesystem import FilesystemManager, compute_content_hash

console = Console()


@dataclass
class Deployment:
    """Tracks artifact deployment to a project with version tracking."""

    # Core identification
    artifact_name: str
    artifact_type: str  # Store as string for TOML serialization
    from_collection: str

    # Deployment metadata
    deployed_at: datetime
    artifact_path: Path  # Relative path within .claude/ (e.g., "commands/review.md")

    # Version tracking (ADR-004)
    content_hash: str  # SHA-256 hash of artifact content at deployment time
    local_modifications: bool = False

    # Optional version tracking fields
    parent_hash: Optional[str] = None  # Hash of parent version (if deployed from collection)
    version_lineage: List[str] = field(default_factory=list)  # Array of version hashes (newest first)
    last_modified_check: Optional[datetime] = None  # Last drift check timestamp
    modification_detected_at: Optional[datetime] = None  # When modification was first detected
    merge_base_snapshot: Optional[str] = None  # Content hash (SHA-256) used as merge base for 3-way merges

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
            result["modification_detected_at"] = self.modification_detected_at.isoformat()

        if self.merge_base_snapshot:
            result["merge_base_snapshot"] = self.merge_base_snapshot

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
            modification_detected_at = datetime.fromisoformat(data["modification_detected_at"])

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

    def deploy_artifacts(
        self,
        artifact_names: List[str],
        collection_name: Optional[str] = None,
        project_path: Optional[Path] = None,
        artifact_type: Optional[ArtifactType] = None,
    ) -> List[Deployment]:
        """Deploy specified artifacts to project.

        Args:
            artifact_names: List of artifact names to deploy
            collection_name: Source collection (uses active if None)
            project_path: Project directory (uses CWD if None)
            artifact_type: Filter artifacts by type (if ambiguous names)

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

        deployments = []

        for artifact_name in artifact_names:
            # Find artifact
            artifact = collection.find_artifact(artifact_name, artifact_type)
            if not artifact:
                console.print(
                    f"[yellow]Warning:[/yellow] Artifact '{artifact_name}' not found, skipping"
                )
                continue

            # Determine source and destination paths
            source_path = collection_path / artifact.path
            dest_base = project_path / ".claude"

            if artifact.type == ArtifactType.SKILL:
                dest_path = dest_base / "skills" / artifact.name
            elif artifact.type == ArtifactType.COMMAND:
                dest_path = dest_base / "commands" / f"{artifact.name}.md"
            elif artifact.type == ArtifactType.AGENT:
                dest_path = dest_base / "agents" / f"{artifact.name}.md"

            # Check if destination exists and prompt for overwrite
            if dest_path.exists():
                console.print(f"[yellow]Warning:[/yellow] {dest_path} already exists")
                if not Confirm.ask(f"Overwrite {artifact.name}?"):
                    console.print(f"[yellow]Skipped:[/yellow] {artifact.name}")
                    continue

            # Copy artifact
            try:
                self.filesystem_mgr.copy_artifact(source_path, dest_path, artifact.type)
                console.print(
                    f"[green][/green] Deployed {artifact.type.value}/{artifact.name}"
                )
            except Exception as e:
                console.print(f"[red]Error deploying {artifact.name}:[/red] {e}")
                continue

            # Compute content hash (becomes merge base for future three-way merges)
            content_hash = compute_content_hash(dest_path)

            # Record deployment
            DeploymentTracker.record_deployment(
                project_path, artifact, collection.name, content_hash
            )

            # Create deployment object
            # Set merge_base_snapshot to content_hash at deployment time
            # This hash becomes the baseline for future three-way merges
            deployment = Deployment(
                artifact_name=artifact.name,
                artifact_type=artifact.type.value,
                from_collection=collection.name,
                deployed_at=datetime.now(),
                artifact_path=dest_path.relative_to(dest_base),
                content_hash=content_hash,
                local_modifications=False,
                merge_base_snapshot=content_hash,  # Store baseline for merge tracking
            )
            deployments.append(deployment)

            # Track deploy event
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
                console.print(f"[yellow]Warning: Failed to create auto-snapshot: {e}[/yellow]")

        return deployments

    def deploy_all(
        self, collection_name: Optional[str] = None, project_path: Optional[Path] = None
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
        return self.deploy_artifacts(artifact_names, collection_name, project_path)

    def undeploy(
        self,
        artifact_name: str,
        artifact_type: ArtifactType,
        project_path: Optional[Path] = None,
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

        # Get deployment record
        deployment = DeploymentTracker.get_deployment(
            project_path, artifact_name, artifact_type.value
        )

        if not deployment:
            raise ValueError(
                f"Artifact '{artifact_name}' is not deployed to this project"
            )

        # Remove files
        artifact_path = project_path / ".claude" / deployment.artifact_path
        if artifact_path.exists():
            self.filesystem_mgr.remove_artifact(artifact_path)
            console.print(
                f"[green][/green] Removed {artifact_type.value}/{artifact_name}"
            )

        # Remove deployment record
        DeploymentTracker.remove_deployment(
            project_path, artifact_name, artifact_type.value
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

    def list_deployments(self, project_path: Optional[Path] = None) -> List[Deployment]:
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

        return DeploymentTracker.read_deployments(project_path)

    def check_deployment_status(
        self, project_path: Optional[Path] = None
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

        deployments = DeploymentTracker.read_deployments(project_path)
        status = {}

        for deployment in deployments:
            key = f"{deployment.artifact_name}::{deployment.artifact_type}"

            # Check for local modifications
            if DeploymentTracker.detect_modifications(
                project_path, deployment.artifact_name, deployment.artifact_type
            ):
                status[key] = "modified"
            else:
                status[key] = "synced"

            # TODO: Check for upstream updates (requires collection loading)
            # This will be expanded in later phases

        return status

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
