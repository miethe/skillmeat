"""Deployment tracking and management for SkillMeat."""

from dataclasses import dataclass
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
    """Tracks artifact deployment to a project."""

    artifact_name: str
    artifact_type: str  # Store as string for TOML serialization
    from_collection: str
    deployed_at: datetime
    artifact_path: Path  # Relative path within .claude/ (e.g., "commands/review.md")
    collection_sha: str  # SHA of artifact at deployment time
    local_modifications: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        return {
            "artifact_name": self.artifact_name,
            "artifact_type": self.artifact_type,
            "from_collection": self.from_collection,
            "deployed_at": self.deployed_at.isoformat(),
            "artifact_path": str(self.artifact_path),
            "collection_sha": self.collection_sha,
            "local_modifications": self.local_modifications,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deployment":
        """Create from dictionary (TOML deserialization)."""
        return cls(
            artifact_name=data["artifact_name"],
            artifact_type=data["artifact_type"],
            from_collection=data["from_collection"],
            deployed_at=datetime.fromisoformat(data["deployed_at"]),
            artifact_path=Path(data["artifact_path"]),
            collection_sha=data["collection_sha"],
            local_modifications=data.get("local_modifications", False),
        )


class DeploymentManager:
    """Manages artifact deployment to projects."""

    def __init__(self, collection_mgr=None):
        """Initialize deployment manager.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
        """
        if collection_mgr is None:
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager()

        self.collection_mgr = collection_mgr
        self.filesystem_mgr = FilesystemManager()

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

            # Compute content hash
            content_hash = compute_content_hash(dest_path)

            # Record deployment
            DeploymentTracker.record_deployment(
                project_path, artifact, collection.name, content_hash
            )

            # Create deployment object
            deployment = Deployment(
                artifact_name=artifact.name,
                artifact_type=artifact.type.value,
                from_collection=collection.name,
                deployed_at=datetime.now(),
                artifact_path=dest_path.relative_to(dest_base),
                collection_sha=content_hash,
                local_modifications=False,
            )
            deployments.append(deployment)

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
