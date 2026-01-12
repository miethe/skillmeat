"""Deployment tracking storage for SkillMeat."""

import sys
from pathlib import Path
from typing import List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from skillmeat.core.artifact import Artifact
from skillmeat.core.deployment import Deployment
from skillmeat.utils.filesystem import compute_content_hash


class DeploymentTracker:
    """Tracks artifact deployments in .skillmeat-deployed.toml"""

    DEPLOYMENT_FILE = ".skillmeat-deployed.toml"

    @staticmethod
    def get_deployment_file_path(project_path: Path) -> Path:
        """Get path to deployment tracking file."""
        return project_path / ".claude" / DeploymentTracker.DEPLOYMENT_FILE

    @staticmethod
    def read_deployments(project_path: Path) -> List[Deployment]:
        """Read all deployment records.

        Args:
            project_path: Project root directory

        Returns:
            List of Deployment objects (empty if file doesn't exist)
        """
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)

        if not deployment_file.exists():
            return []

        with open(deployment_file, "rb") as f:
            data = tomllib.load(f)

        deployments = []
        for deployment_data in data.get("deployed", []):
            deployments.append(Deployment.from_dict(deployment_data))

        return deployments

    @staticmethod
    def write_deployments(project_path: Path, deployments: List[Deployment]) -> None:
        """Write deployment records.

        Args:
            project_path: Project root directory
            deployments: List of Deployment objects to write
        """
        deployment_file = DeploymentTracker.get_deployment_file_path(project_path)

        # Ensure .claude directory exists
        deployment_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to TOML format
        data = {"deployed": [d.to_dict() for d in deployments]}

        # Write atomically
        with open(deployment_file, "wb") as f:
            tomli_w.dump(data, f)

    @staticmethod
    def record_deployment(
        project_path: Path,
        artifact: Artifact,
        collection_name: str,
        collection_sha: str,
    ) -> None:
        """Record new deployment or update existing.

        Args:
            project_path: Project root directory
            artifact: Artifact being deployed
            collection_name: Source collection name
            collection_sha: SHA of artifact content
        """
        from datetime import datetime

        deployments = DeploymentTracker.read_deployments(project_path)

        # Determine artifact path within .claude/
        if artifact.type.value == "skill":
            artifact_path = Path(f"skills/{artifact.name}")
        elif artifact.type.value == "command":
            artifact_path = Path(f"commands/{artifact.name}.md")
        elif artifact.type.value == "agent":
            artifact_path = Path(f"agents/{artifact.name}.md")
        elif artifact.type.value == "hook":
            artifact_path = Path(f"hooks/{artifact.name}.md")
        elif artifact.type.value == "mcp":
            artifact_path = Path(f"mcp/{artifact.name}")
        else:
            raise ValueError(f"Unknown artifact type: {artifact.type.value}")

        # Check if deployment already exists (update it)
        existing = None
        for i, dep in enumerate(deployments):
            if (
                dep.artifact_name == artifact.name
                and dep.artifact_type == artifact.type.value
            ):
                existing = i
                break

        deployment = Deployment(
            artifact_name=artifact.name,
            artifact_type=artifact.type.value,
            from_collection=collection_name,
            deployed_at=datetime.now(),
            artifact_path=artifact_path,
            content_hash=collection_sha,
            local_modifications=False,
            merge_base_snapshot=collection_sha,  # Store baseline for merge tracking
        )

        if existing is not None:
            deployments[existing] = deployment
        else:
            deployments.append(deployment)

        DeploymentTracker.write_deployments(project_path, deployments)

    @staticmethod
    def get_deployment(
        project_path: Path, artifact_name: str, artifact_type: str
    ) -> Optional[Deployment]:
        """Get specific deployment record.

        Args:
            project_path: Project root directory
            artifact_name: Artifact name
            artifact_type: Artifact type

        Returns:
            Deployment object or None if not found
        """
        deployments = DeploymentTracker.read_deployments(project_path)

        for dep in deployments:
            if (
                dep.artifact_name == artifact_name
                and dep.artifact_type == artifact_type
            ):
                return dep

        return None

    @staticmethod
    def remove_deployment(
        project_path: Path, artifact_name: str, artifact_type: str
    ) -> None:
        """Remove deployment record.

        Args:
            project_path: Project root directory
            artifact_name: Artifact name
            artifact_type: Artifact type
        """
        deployments = DeploymentTracker.read_deployments(project_path)

        # Filter out the deployment
        deployments = [
            d
            for d in deployments
            if not (
                d.artifact_name == artifact_name and d.artifact_type == artifact_type
            )
        ]

        DeploymentTracker.write_deployments(project_path, deployments)

    @staticmethod
    def detect_modifications(
        project_path: Path, artifact_name: str, artifact_type: str
    ) -> bool:
        """Check if deployed artifact has local modifications.

        Args:
            project_path: Project root directory
            artifact_name: Artifact name
            artifact_type: Artifact type

        Returns:
            True if modified, False otherwise
        """
        deployment = DeploymentTracker.get_deployment(
            project_path, artifact_name, artifact_type
        )

        if not deployment:
            return False

        # Get current content hash
        artifact_full_path = project_path / ".claude" / deployment.artifact_path
        if not artifact_full_path.exists():
            return False

        current_hash = compute_content_hash(artifact_full_path)

        # Compare with deployment SHA
        return current_hash != deployment.collection_sha
