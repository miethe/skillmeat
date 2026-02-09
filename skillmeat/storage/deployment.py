"""Deployment tracking storage for SkillMeat."""

import sys
from pathlib import Path
from typing import Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

from skillmeat.core.artifact import Artifact
from skillmeat.core.deployment import Deployment
from skillmeat.core.path_resolver import (
    DEFAULT_ARTIFACT_PATH_MAP,
    DEFAULT_PROFILE_ROOT_DIR,
    DeploymentPathProfile,
    resolve_config_path,
    resolve_deployment_path,
)
from skillmeat.utils.filesystem import compute_content_hash


class DeploymentTracker:
    """Tracks artifact deployments in .skillmeat-deployed.toml"""

    DEPLOYMENT_FILE = ".skillmeat-deployed.toml"

    @staticmethod
    def get_deployment_file_path(
        project_path: Path,
        profile_root_dir: str = DEFAULT_PROFILE_ROOT_DIR,
    ) -> Path:
        """Get path to deployment tracking file."""
        return resolve_config_path(
            project_path=project_path,
            profile=DeploymentPathProfile(root_dir=profile_root_dir),
            filename=DeploymentTracker.DEPLOYMENT_FILE,
        )

    @staticmethod
    def read_deployments(
        project_path: Path,
        profile_root_dir: Optional[str] = None,
    ) -> List[Deployment]:
        """Read all deployment records.

        Args:
            project_path: Project root directory

        Returns:
            List of Deployment objects (empty if file doesn't exist)
        """
        project_path = Path(project_path).resolve()
        deployment_files: List[Path] = []
        if profile_root_dir:
            deployment_files.append(
                DeploymentTracker.get_deployment_file_path(
                    project_path, profile_root_dir=profile_root_dir
                )
            )
        else:
            deployment_files.append(
                DeploymentTracker.get_deployment_file_path(
                    project_path, profile_root_dir=DEFAULT_PROFILE_ROOT_DIR
                )
            )
            for profile_dir in project_path.glob(".*"):
                if not profile_dir.is_dir():
                    continue
                deployment_file = profile_dir / DeploymentTracker.DEPLOYMENT_FILE
                if deployment_file.exists() and deployment_file not in deployment_files:
                    deployment_files.append(deployment_file)

        deployments: List[Deployment] = []
        for deployment_file in deployment_files:
            if not deployment_file.exists():
                continue
            with open(deployment_file, "rb") as f:
                data = tomllib.load(f)
            for deployment_data in data.get("deployed", []):
                deployments.append(Deployment.from_dict(deployment_data))
        return deployments

    @staticmethod
    def write_deployments(
        project_path: Path,
        deployments: List[Deployment],
        profile_root_dir: Optional[str] = None,
    ) -> None:
        """Write deployment records.

        Args:
            project_path: Project root directory
            deployments: List of Deployment objects to write
        """
        project_path = Path(project_path).resolve()
        grouped: Dict[str, List[Deployment]] = {}

        if profile_root_dir:
            grouped[profile_root_dir] = deployments
        else:
            for deployment in deployments:
                root_dir = deployment.profile_root_dir or DEFAULT_PROFILE_ROOT_DIR
                grouped.setdefault(root_dir, []).append(deployment)
            if not deployments:
                grouped[DEFAULT_PROFILE_ROOT_DIR] = []

        roots_to_write = set(grouped.keys())
        if not profile_root_dir:
            existing_roots = {
                profile_dir.name
                for profile_dir in project_path.glob(".*")
                if profile_dir.is_dir()
                and (profile_dir / DeploymentTracker.DEPLOYMENT_FILE).exists()
            }
            roots_to_write.update(existing_roots)

        for root_dir in roots_to_write:
            root_deployments = grouped.get(root_dir, [])
            deployment_file = DeploymentTracker.get_deployment_file_path(
                project_path, profile_root_dir=root_dir
            )
            if not root_deployments and deployment_file.exists():
                deployment_file.unlink()
                continue
            deployment_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"deployed": [d.to_dict() for d in root_deployments]}
            with open(deployment_file, "wb") as f:
                tomli_w.dump(data, f)

    @staticmethod
    def record_deployment(
        project_path: Path,
        artifact: Artifact,
        collection_name: str,
        collection_sha: str,
        deployment_profile_id: Optional[str] = None,
        platform: Optional[str] = None,
        profile_root_dir: str = DEFAULT_PROFILE_ROOT_DIR,
        artifact_path: Optional[Path] = None,
        artifact_path_map: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record new deployment or update existing.

        Args:
            project_path: Project root directory
            artifact: Artifact being deployed
            collection_name: Source collection name
            collection_sha: SHA of artifact content
        """
        from datetime import datetime

        deployments = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)

        if artifact_path is None:
            path_map = DEFAULT_ARTIFACT_PATH_MAP.copy()
            path_map.update(artifact_path_map or {})
            base = path_map.get(artifact.type.value)
            if not base:
                raise ValueError(f"Unknown artifact type: {artifact.type.value}")
            if artifact.type.value in {"skill", "mcp"}:
                artifact_path = Path(base) / artifact.name
            else:
                artifact_path = Path(base) / f"{artifact.name}.md"

        # Check if deployment already exists (update it)
        existing = None
        for i, dep in enumerate(deployments):
            if (
                dep.artifact_name == artifact.name
                and dep.artifact_type == artifact.type.value
                and (dep.deployment_profile_id or "claude_code")
                == (deployment_profile_id or "claude_code")
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
            deployment_profile_id=deployment_profile_id,
            platform=platform,
            profile_root_dir=profile_root_dir,
        )

        if existing is not None:
            deployments[existing] = deployment
        else:
            deployments.append(deployment)

        DeploymentTracker.write_deployments(project_path, deployments)

    @staticmethod
    def get_deployment(
        project_path: Path,
        artifact_name: str,
        artifact_type: str,
        profile_id: Optional[str] = None,
    ) -> Optional[Deployment]:
        """Get specific deployment record.

        Args:
            project_path: Project root directory
            artifact_name: Artifact name
            artifact_type: Artifact type

        Returns:
            Deployment object or None if not found
        """
        deployments = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)

        for dep in deployments:
            if (
                dep.artifact_name == artifact_name
                and dep.artifact_type == artifact_type
                and (
                    profile_id is None
                    or (dep.deployment_profile_id or "claude_code") == profile_id
                )
            ):
                return dep

        return None

    @staticmethod
    def remove_deployment(
        project_path: Path,
        artifact_name: str,
        artifact_type: str,
        profile_id: Optional[str] = None,
    ) -> None:
        """Remove deployment record.

        Args:
            project_path: Project root directory
            artifact_name: Artifact name
            artifact_type: Artifact type
        """
        deployments = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)

        # Filter out the deployment
        deployments = [
            d
            for d in deployments
            if not (
                d.artifact_name == artifact_name and d.artifact_type == artifact_type
                and (
                    profile_id is None
                    or (d.deployment_profile_id or "claude_code") == profile_id
                )
            )
        ]

        DeploymentTracker.write_deployments(project_path, deployments)

    @staticmethod
    def detect_modifications(
        project_path: Path,
        artifact_name: str,
        artifact_type: str,
        profile_id: Optional[str] = None,
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
            project_path,
            artifact_name,
            artifact_type,
            profile_id=profile_id,
        )

        if not deployment:
            return False

        # Get current content hash
        artifact_full_path = resolve_deployment_path(
            deployment_relative_path=deployment.artifact_path,
            project_path=project_path,
            profile=DeploymentPathProfile(
                profile_id=deployment.deployment_profile_id or "claude_code",
                root_dir=deployment.profile_root_dir or DEFAULT_PROFILE_ROOT_DIR,
            ),
        )
        if not artifact_full_path.exists():
            return False

        current_hash = compute_content_hash(artifact_full_path)

        # Compare with deployment SHA
        return current_hash != deployment.collection_sha
