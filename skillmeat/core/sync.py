"""Sync manager for SkillMeat.

This module provides synchronization capabilities between collections and
deployed projects, including drift detection and deployment tracking.
"""

import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from skillmeat.utils.logging import redact_path
from skillmeat.models import (
    DeploymentRecord,
    DeploymentMetadata,
    DriftDetectionResult,
    SyncResult,
    ArtifactSyncResult,
)

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages synchronization between collections and project deployments.

    Tracks deployment metadata, detects drift, and provides sync operations
    for keeping collections and projects in sync.
    """

    def __init__(self, collection_manager=None, artifact_manager=None, snapshot_manager=None):
        """Initialize SyncManager.

        Args:
            collection_manager: Optional CollectionManager instance
            artifact_manager: Optional ArtifactManager instance
            snapshot_manager: Optional SnapshotManager for rollback support
        """
        self.collection_mgr = collection_manager
        self.artifact_mgr = artifact_manager
        self.snapshot_mgr = snapshot_manager

    def check_drift(
        self,
        project_path: Path,
        collection_name: Optional[str] = None,
    ) -> List[DriftDetectionResult]:
        """Check for drift between deployed and collection versions.

        Compares the deployment metadata (.skillmeat-deployed.toml) with
        the current state of the collection to detect changes.

        Args:
            project_path: Path to project root (contains .claude/)
            collection_name: Optional collection name override

        Returns:
            List of DriftDetectionResult objects describing detected drift

        Raises:
            ValueError: If project path doesn't exist or is invalid
        """
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Load deployment metadata
        metadata = self._load_deployment_metadata(project_path)
        if not metadata:
            logger.info(f"No deployment metadata found at {redact_path(project_path)}")
            return []

        # Use collection from metadata if not specified
        if not collection_name:
            collection_name = metadata.collection

        # Get artifacts from collection
        collection_artifacts = self._get_collection_artifacts(collection_name)

        drift_results = []

        # Check each deployed artifact for drift
        for deployed in metadata.artifacts:
            # Find artifact in collection
            collection_artifact = self._find_artifact(
                collection_artifacts, deployed.name, deployed.artifact_type
            )

            if not collection_artifact:
                # Artifact removed from collection
                drift_results.append(
                    DriftDetectionResult(
                        artifact_name=deployed.name,
                        artifact_type=deployed.artifact_type,
                        drift_type="removed",
                        collection_sha=None,
                        project_sha=deployed.sha,
                        collection_version=None,
                        project_version=deployed.version,
                        last_deployed=deployed.deployed_at,
                        recommendation="remove_from_project",
                    )
                )
                continue

            # Compute current collection SHA
            collection_sha = self._compute_artifact_hash(collection_artifact["path"])

            # Compute current project SHA (check if project has local modifications)
            project_artifact_path = self._get_project_artifact_path(
                project_path, deployed.name, deployed.artifact_type
            )
            current_project_sha = deployed.sha  # Default to deployed SHA
            if project_artifact_path and project_artifact_path.exists():
                current_project_sha = self._compute_artifact_hash(project_artifact_path)

            # Three-way conflict detection:
            # - deployed.sha is the "base" (what was deployed)
            # - collection_sha is "upstream" (current collection state)
            # - current_project_sha is "local" (current project state)

            collection_changed = collection_sha != deployed.sha
            project_changed = current_project_sha != deployed.sha

            if collection_changed or project_changed:
                # Determine drift type
                if collection_changed and project_changed:
                    # CONFLICT: Both collection and project changed since deployment
                    drift_type = "conflict"
                    recommendation = "review_manually"
                elif collection_changed:
                    # Collection changed, project unchanged (simple update available)
                    drift_type = "outdated"
                    recommendation = "pull_from_collection"
                else:
                    # Project changed, collection unchanged (local modifications only)
                    drift_type = "modified"
                    recommendation = "push_to_collection"

                drift_results.append(
                    DriftDetectionResult(
                        artifact_name=deployed.name,
                        artifact_type=deployed.artifact_type,
                        drift_type=drift_type,
                        collection_sha=collection_sha,
                        project_sha=current_project_sha,
                        collection_version=collection_artifact.get("version"),
                        project_version=deployed.version,
                        last_deployed=deployed.deployed_at,
                        recommendation=recommendation,
                    )
                )

        # Check for new artifacts in collection not yet deployed
        for artifact in collection_artifacts:
            if not self._is_deployed(artifact, metadata):
                drift_results.append(
                    DriftDetectionResult(
                        artifact_name=artifact["name"],
                        artifact_type=artifact["type"],
                        drift_type="added",
                        collection_sha=self._compute_artifact_hash(artifact["path"]),
                        project_sha=None,
                        collection_version=artifact.get("version"),
                        project_version=None,
                        last_deployed=None,
                        recommendation="deploy_to_project",
                    )
                )

        return drift_results

    def _compute_artifact_hash(self, artifact_path: Path) -> str:
        """Compute SHA-256 hash of artifact directory.

        Hashes all files in the artifact directory to create a content hash
        that can be used to detect changes.

        Args:
            artifact_path: Path to artifact directory

        Returns:
            SHA-256 hash as hexadecimal string

        Raises:
            ValueError: If artifact path doesn't exist
        """
        if not artifact_path.exists():
            raise ValueError(f"Artifact path does not exist: {artifact_path}")

        hasher = hashlib.sha256()

        # Hash all files in artifact directory (sorted for consistency)
        file_paths = sorted(artifact_path.rglob("*"))
        for file_path in file_paths:
            if file_path.is_file():
                # Hash relative path
                rel_path = file_path.relative_to(artifact_path)
                hasher.update(str(rel_path).encode("utf-8"))

                # Hash file contents
                try:
                    hasher.update(file_path.read_bytes())
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not read {redact_path(file_path)}: {e}")
                    continue

        return hasher.hexdigest()

    def _load_deployment_metadata(
        self, project_path: Path
    ) -> Optional[DeploymentMetadata]:
        """Load .skillmeat-deployed.toml from project.

        Args:
            project_path: Path to project root

        Returns:
            DeploymentMetadata object or None if file doesn't exist
        """
        metadata_file = project_path / ".claude" / ".skillmeat-deployed.toml"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "rb") as f:
                data = tomllib.load(f)

            # Parse deployment section
            deployment = data.get("deployment", {})
            collection = deployment.get("collection", "default")
            deployed_at = deployment.get("deployed-at", "")
            skillmeat_version = deployment.get("skillmeat-version", "unknown")

            # Parse artifacts
            artifacts = []
            for artifact_data in data.get("artifacts", []):
                artifacts.append(
                    DeploymentRecord(
                        name=artifact_data["name"],
                        artifact_type=artifact_data["type"],
                        source=artifact_data["source"],
                        version=artifact_data["version"],
                        sha=artifact_data["sha"],
                        deployed_at=artifact_data["deployed-at"],
                        deployed_from=artifact_data["deployed-from"],
                    )
                )

            return DeploymentMetadata(
                collection=collection,
                deployed_at=deployed_at,
                skillmeat_version=skillmeat_version,
                artifacts=artifacts,
            )

        except Exception as e:
            logger.warning(f"Failed to load deployment metadata: {e}")
            return None

    def _save_deployment_metadata(
        self, metadata_file: Path, metadata: DeploymentMetadata
    ) -> None:
        """Save deployment metadata to .skillmeat-deployed.toml.

        Args:
            metadata_file: Path to metadata file
            metadata: DeploymentMetadata to save

        Raises:
            OSError: If file cannot be written
        """
        # Ensure .claude directory exists
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        # Build TOML structure
        toml_data = {
            "deployment": {
                "collection": metadata.collection,
                "deployed-at": metadata.deployed_at,
                "skillmeat-version": metadata.skillmeat_version,
            },
            "artifacts": [],
        }

        for artifact in metadata.artifacts:
            toml_data["artifacts"].append(
                {
                    "name": artifact.name,
                    "type": artifact.artifact_type,
                    "source": artifact.source,
                    "version": artifact.version,
                    "sha": artifact.sha,
                    "deployed-at": artifact.deployed_at,
                    "deployed-from": artifact.deployed_from,
                }
            )

        # Write TOML file
        try:
            import tomli_w
        except ImportError:
            raise ImportError(
                "tomli_w is required for writing TOML files. "
                "Install with: pip install tomli-w"
            )

        with open(metadata_file, "wb") as f:
            tomli_w.dump(toml_data, f)

    def update_deployment_metadata(
        self,
        project_path: Path,
        artifact_name: str,
        artifact_type: str,
        collection_path: Path,
        collection_name: str = "default",
    ) -> None:
        """Update .skillmeat-deployed.toml after deployment.

        Records or updates the deployment metadata for a single artifact.

        Args:
            project_path: Path to project root
            artifact_name: Name of deployed artifact
            artifact_type: Type of artifact (skill, command, agent)
            collection_path: Path to collection root
            collection_name: Name of collection

        Raises:
            ValueError: If artifact or collection path doesn't exist
        """
        metadata_file = project_path / ".claude" / ".skillmeat-deployed.toml"

        # Load existing or create new
        metadata = self._load_deployment_metadata(project_path)
        if not metadata:
            metadata = DeploymentMetadata(
                collection=collection_name,
                deployed_at=datetime.utcnow().isoformat() + "Z",
                skillmeat_version="0.2.0-alpha",
                artifacts=[],
            )

        # Compute hash
        # Convert artifact type to plural form for directory name
        artifact_type_plural = self._get_artifact_type_plural(artifact_type)
        artifact_path = collection_path / artifact_type_plural / artifact_name
        if not artifact_path.exists():
            raise ValueError(f"Artifact path does not exist: {artifact_path}")

        sha = self._compute_artifact_hash(artifact_path)

        # Get artifact metadata (source, version)
        source = self._get_artifact_source(artifact_path)
        version = self._get_artifact_version(artifact_path)

        # Create or update record
        now = datetime.utcnow().isoformat() + "Z"
        record = DeploymentRecord(
            name=artifact_name,
            artifact_type=artifact_type,
            source=source,
            version=version,
            sha=sha,
            deployed_at=now,
            deployed_from=str(collection_path),
        )

        # Replace existing or append
        existing_idx = None
        for i, existing in enumerate(metadata.artifacts):
            if (
                existing.name == artifact_name
                and existing.artifact_type == artifact_type
            ):
                existing_idx = i
                break

        if existing_idx is not None:
            metadata.artifacts[existing_idx] = record
        else:
            metadata.artifacts.append(record)

        # Update deployment timestamp
        metadata.deployed_at = now

        # Save to file
        self._save_deployment_metadata(metadata_file, metadata)

    def _get_collection_artifacts(self, collection_name: str) -> List[Dict[str, Any]]:
        """Get list of artifacts from collection.

        Args:
            collection_name: Name of collection

        Returns:
            List of artifact dictionaries with name, type, path, version
        """
        if not self.collection_mgr:
            logger.warning("No collection manager provided")
            return []

        try:
            # Get collection path
            collection = self.collection_mgr.load_collection(collection_name)
            collection_path = collection.path

            artifacts = []

            # Scan for artifacts (skills, commands, agents, etc.)
            # For now, only skills are supported
            skills_dir = collection_path / "skills"
            if skills_dir.exists():
                for skill_path in skills_dir.iterdir():
                    if skill_path.is_dir():
                        artifacts.append(
                            {
                                "name": skill_path.name,
                                "type": "skill",
                                "path": skill_path,
                                "version": self._get_artifact_version(skill_path),
                            }
                        )

            return artifacts

        except Exception as e:
            logger.error(f"Failed to get collection artifacts: {e}")
            return []

    def _find_artifact(
        self,
        artifacts: List[Dict[str, Any]],
        name: str,
        artifact_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Find artifact in list by name and type.

        Args:
            artifacts: List of artifact dictionaries
            name: Artifact name
            artifact_type: Artifact type

        Returns:
            Artifact dictionary or None if not found
        """
        for artifact in artifacts:
            if artifact["name"] == name and artifact["type"] == artifact_type:
                return artifact
        return None

    def _is_deployed(
        self, artifact: Dict[str, Any], metadata: DeploymentMetadata
    ) -> bool:
        """Check if artifact is already deployed.

        Args:
            artifact: Artifact dictionary
            metadata: Deployment metadata

        Returns:
            True if artifact is in deployment metadata
        """
        for deployed in metadata.artifacts:
            if (
                deployed.name == artifact["name"]
                and deployed.artifact_type == artifact["type"]
            ):
                return True
        return False

    def _recommend_sync_direction(
        self, collection_artifact: Dict[str, Any], deployed: DeploymentRecord
    ) -> str:
        """Recommend sync direction based on artifact state.

        Args:
            collection_artifact: Artifact from collection
            deployed: Deployed artifact record

        Returns:
            Recommendation string
        """
        # For now, always recommend pulling from collection (push direction)
        # Phase 3+ will add more sophisticated logic
        return "push_from_collection"

    def _get_artifact_type_plural(self, artifact_type: str) -> str:
        """Convert artifact type to plural form for directory names.

        Args:
            artifact_type: Singular artifact type (e.g., "skill")

        Returns:
            Plural form (e.g., "skills")
        """
        # Map singular to plural
        plural_map = {
            "skill": "skills",
            "command": "commands",
            "agent": "agents",
            "hook": "hooks",
            "mcp": "mcps",
        }
        return plural_map.get(artifact_type, artifact_type + "s")

    def _get_artifact_source(self, artifact_path: Path) -> str:
        """Get artifact source identifier.

        Args:
            artifact_path: Path to artifact

        Returns:
            Source identifier (e.g., "local:/path" or "github:user/repo")
        """
        # Try to read from metadata or lock file
        # For now, return local path
        return f"local:{artifact_path}"

    def _get_artifact_version(self, artifact_path: Path) -> str:
        """Get artifact version.

        Args:
            artifact_path: Path to artifact

        Returns:
            Version string or "unknown"
        """
        # Try to extract from metadata file
        try:
            from skillmeat.utils.metadata import (
                find_metadata_file,
                extract_artifact_metadata,
            )
            from skillmeat.models import ArtifactType

            # Determine artifact type from path structure
            # For now, assume it's a skill
            artifact_type = ArtifactType.SKILL

            metadata_file = find_metadata_file(artifact_path, artifact_type)
            if metadata_file:
                metadata = extract_artifact_metadata(metadata_file)
                return metadata.get("version", "unknown")
        except Exception:
            pass

        return "unknown"

    def sync_from_project_with_rollback(
        self,
        project_path: Path,
        artifact_names: Optional[List[str]] = None,
        strategy: str = "prompt",
        dry_run: bool = False,
        interactive: bool = True,
    ) -> SyncResult:
        """Pull artifacts from project with automatic rollback on failure.

        Creates a snapshot before sync and can rollback if sync fails.
        This is a wrapper around sync_from_project() with safety guarantees.

        Args:
            project_path: Path to project root
            artifact_names: Specific artifacts to sync (None = all drifted)
            strategy: Sync strategy ("overwrite", "merge", "fork", "prompt")
            dry_run: Preview what would be synced without making changes
            interactive: Show preview and ask for confirmation

        Returns:
            SyncResult with status and list of synced artifacts

        Raises:
            ValueError: If project path doesn't exist or invalid strategy
        """
        # If no snapshot manager, fall back to regular sync
        if not self.snapshot_mgr or dry_run:
            return self.sync_from_project(
                project_path=project_path,
                artifact_names=artifact_names,
                strategy=strategy,
                dry_run=dry_run,
                interactive=interactive,
            )

        # Get collection info from metadata
        metadata = self._load_deployment_metadata(project_path)
        if not metadata:
            # No metadata, proceed without snapshot
            logger.warning("No deployment metadata, proceeding without snapshot")
            return self.sync_from_project(
                project_path=project_path,
                artifact_names=artifact_names,
                strategy=strategy,
                dry_run=dry_run,
                interactive=interactive,
            )

        collection_name = metadata.collection

        # Get collection path
        if not self.collection_mgr:
            # No collection manager, proceed without snapshot
            logger.warning("No collection manager, proceeding without snapshot")
            return self.sync_from_project(
                project_path=project_path,
                artifact_names=artifact_names,
                strategy=strategy,
                dry_run=dry_run,
                interactive=interactive,
            )

        try:
            collection = self.collection_mgr.load_collection(collection_name)
            collection_path = collection.path
        except Exception as e:
            logger.warning(f"Failed to get collection path: {e}")
            return self.sync_from_project(
                project_path=project_path,
                artifact_names=artifact_names,
                strategy=strategy,
                dry_run=dry_run,
                interactive=interactive,
            )

        # Create snapshot before sync
        logger.info(f"Creating snapshot before sync pull")
        try:
            snapshot = self.snapshot_mgr.create_snapshot(
                collection_path=collection_path,
                collection_name=collection_name,
                message="Pre-sync snapshot (automatic)",
            )
            logger.info(f"Created snapshot: {snapshot.id}")
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            # Offer to proceed without snapshot
            if interactive:
                from rich.console import Console
                from rich.prompt import Confirm

                console = Console()
                console.print(
                    f"[yellow]Warning: Failed to create snapshot: {e}[/yellow]"
                )
                if not Confirm.ask("Proceed without snapshot protection?", default=False):
                    return SyncResult(
                        status="cancelled",
                        message="Sync cancelled (snapshot creation failed)",
                        artifacts_synced=[],
                    )
            snapshot = None

        # Perform sync
        try:
            result = self.sync_from_project(
                project_path=project_path,
                artifact_names=artifact_names,
                strategy=strategy,
                dry_run=dry_run,
                interactive=interactive,
            )

            # Handle partial success or failure
            if result.status == "partial" and interactive and snapshot:
                from rich.console import Console
                from rich.prompt import Confirm

                console = Console()
                console.print(
                    f"\n[yellow]Warning: Sync completed with {len(result.conflicts)} conflicts[/yellow]"
                )
                console.print(f"Synced: {len(result.artifacts_synced)} artifacts")
                console.print(f"Conflicts: {len(result.conflicts)} artifacts")

                if Confirm.ask("\n[bold]Rollback to pre-sync state?[/bold]", default=False):
                    logger.info("User requested rollback")
                    self.snapshot_mgr.restore_snapshot(snapshot, collection_path)
                    return SyncResult(
                        status="cancelled",
                        message="Sync rolled back due to conflicts",
                        artifacts_synced=[],
                    )

            return result

        except Exception as e:
            # Automatic rollback on error
            logger.error(f"Sync failed with error: {e}")

            if snapshot:
                logger.info("Automatically rolling back to pre-sync snapshot")
                try:
                    self.snapshot_mgr.restore_snapshot(snapshot, collection_path)
                    logger.info("Rollback successful")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                    raise ValueError(
                        f"Sync failed and rollback also failed. "
                        f"Sync error: {e}. Rollback error: {rollback_error}"
                    )

                raise ValueError(f"Sync failed and was rolled back: {e}")
            else:
                raise

    def validate_sync_preconditions(
        self, project_path: Path, collection_name: Optional[str] = None
    ) -> List[str]:
        """Validate that sync can proceed.

        Performs pre-flight checks to ensure sync operations can complete
        successfully, returning a list of issues if any are found.

        Args:
            project_path: Path to project root
            collection_name: Optional collection name to validate

        Returns:
            List of issue messages (empty if all checks pass)
        """
        issues = []

        # Check project path exists
        if not project_path.exists():
            issues.append(
                f"Project path does not exist: {project_path}\n"
                "  Ensure you're pointing to a valid project directory."
            )
            return issues  # Can't continue other checks

        # Check for deployment metadata
        metadata_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        if not metadata_file.exists():
            issues.append(
                "No deployment metadata found (.skillmeat-deployed.toml).\n"
                "  This project hasn't been deployed yet. Deploy artifacts first with:\n"
                "    skillmeat deploy <artifact> <project-path>"
            )

        # Check collection manager available
        if not self.collection_mgr:
            issues.append(
                "Collection manager not initialized.\n"
                "  Initialize a collection first with:\n"
                "    skillmeat init --collection default"
            )
        else:
            # Check collection exists
            metadata = self._load_deployment_metadata(project_path)
            if metadata:
                coll_name = collection_name or metadata.collection
                try:
                    collection = self.collection_mgr.get_collection(coll_name)
                    if not collection or not collection.path.exists():
                        issues.append(
                            f"Collection '{coll_name}' not found or path does not exist.\n"
                            f"  Create the collection or deploy from a different collection."
                        )
                except Exception as e:
                    issues.append(
                        f"Error accessing collection '{coll_name}': {e}\n"
                        f"  Verify collection exists and is accessible."
                    )

        # Check .claude directory exists
        claude_dir = project_path / ".claude"
        if not claude_dir.exists():
            issues.append(
                "Project does not have a .claude directory.\n"
                "  This doesn't appear to be a valid Claude project."
            )

        return issues

    def sync_from_project(
        self,
        project_path: Path,
        artifact_names: Optional[List[str]] = None,
        strategy: str = "prompt",  # "overwrite", "merge", "fork", "prompt"
        dry_run: bool = False,
        interactive: bool = True,
    ) -> SyncResult:
        """Pull artifacts from project to collection.

        Syncs modified artifacts from a project back to the collection.
        Useful for capturing local changes made to deployed artifacts.

        Args:
            project_path: Path to project root
            artifact_names: Specific artifacts to sync (None = all drifted)
            strategy: Sync strategy ("overwrite", "merge", "fork", "prompt")
            dry_run: Preview what would be synced without making changes
            interactive: Show preview and ask for confirmation

        Returns:
            SyncResult with status and list of synced artifacts

        Raises:
            ValueError: If project path doesn't exist, invalid strategy, or
                       pre-flight checks fail
        """
        # Pre-flight validation (basic checks only)
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        # Validate strategy
        valid_strategies = {"overwrite", "merge", "fork", "prompt"}
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid strategy '{strategy}'. Must be one of: {', '.join(valid_strategies)}"
            )

        # Log sync start
        logger.info(
            "Sync pull started",
            extra={
                "project_path": str(project_path),
                "strategy": strategy,
                "dry_run": dry_run,
                "interactive": interactive,
                "artifact_filter": artifact_names or "all",
            },
        )

        # Step 1: Detect drift
        drift_results = self.check_drift(project_path)
        logger.debug(f"Detected {len(drift_results)} total drift items")

        # Filter to specified artifacts if provided
        if artifact_names:
            drift_results = [
                d for d in drift_results if d.artifact_name in artifact_names
            ]
            logger.debug(
                f"Filtered to {len(drift_results)} artifacts matching filter: {artifact_names}"
            )

        # Filter to pullable drift (modified artifacts only)
        # Don't pull "added" (new in collection) or "removed" (deleted from collection)
        # For "modified" drift, check if project has local modifications
        pullable_drift = []
        for drift in drift_results:
            if drift.drift_type == "modified":
                # Get project artifact path
                project_artifact_path = self._get_project_artifact_path(
                    project_path, drift.artifact_name, drift.artifact_type
                )
                if project_artifact_path and project_artifact_path.exists():
                    # Compute current project SHA
                    current_project_sha = self._compute_artifact_hash(
                        project_artifact_path
                    )
                    # Compare with deployed SHA (drift.project_sha)
                    # If they differ, project has local modifications to pull
                    if current_project_sha != drift.project_sha:
                        pullable_drift.append(drift)
                        logger.debug(
                            f"Artifact {drift.artifact_name} has local modifications "
                            f"(deployed: {drift.project_sha[:12]}..., "
                            f"current: {current_project_sha[:12]}...)"
                        )

        logger.info(f"Found {len(pullable_drift)} artifacts with pullable changes")

        if not pullable_drift:
            logger.info("No artifacts to pull from project")
            return SyncResult(
                status="no_changes",
                message="No artifacts to pull from project",
                artifacts_synced=[],
            )

        # Step 2: Show preview
        if interactive and not dry_run:
            logger.debug("Showing sync preview to user")
            self._show_sync_preview(pullable_drift, strategy)
            if not self._confirm_sync(drift_results=pullable_drift, strategy=strategy):
                logger.info("Sync cancelled by user")
                return SyncResult(
                    status="cancelled",
                    message="Sync cancelled by user",
                    artifacts_synced=[],
                )

        if dry_run:
            logger.info(f"Dry-run: Would sync {len(pullable_drift)} artifacts")
            return SyncResult(
                status="dry_run",
                message=f"Would sync {len(pullable_drift)} artifacts from project",
                artifacts_synced=[d.artifact_name for d in pullable_drift],
            )

        # Step 3: Sync each artifact
        logger.info(f"Starting sync of {len(pullable_drift)} artifacts")
        synced_artifacts = []
        conflicts = []

        # Use progress bar for operations with >3 artifacts
        if len(pullable_drift) > 3 and not dry_run:
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=None,  # Use default console
            ) as progress:
                task = progress.add_task(
                    f"Syncing {len(pullable_drift)} artifacts...",
                    total=len(pullable_drift)
                )

                for drift in pullable_drift:
                    logger.debug(
                        f"Syncing artifact {drift.artifact_name} ({drift.artifact_type}) "
                        f"with strategy: {strategy}"
                    )
                    result = self._sync_artifact(
                        project_path=project_path,
                        drift=drift,
                        strategy=strategy,
                        interactive=interactive,
                    )

                    if result.success:
                        synced_artifacts.append(result.artifact_name)
                        logger.info(f"Successfully synced {result.artifact_name}")
                    elif result.has_conflict:
                        conflicts.append(result)
                        logger.warning(
                            f"Conflict in {result.artifact_name}: {len(result.conflict_files)} files"
                        )

                    progress.advance(task)
        else:
            # No progress bar for small operations
            for drift in pullable_drift:
                logger.debug(
                    f"Syncing artifact {drift.artifact_name} ({drift.artifact_type}) "
                    f"with strategy: {strategy}"
                )
                result = self._sync_artifact(
                    project_path=project_path,
                    drift=drift,
                    strategy=strategy,
                    interactive=interactive,
                )

                if result.success:
                    synced_artifacts.append(result.artifact_name)
                    logger.info(f"Successfully synced {result.artifact_name}")
                elif result.has_conflict:
                    conflicts.append(result)
                    logger.warning(
                        f"Conflict in {result.artifact_name}: {len(result.conflict_files)} files"
                    )

        # Step 4: Update lock files (if collection manager available)
        if synced_artifacts and self.collection_mgr:
            try:
                logger.debug(f"Updating collection lock for {len(synced_artifacts)} artifacts")
                self._update_collection_lock(synced_artifacts, drift_results)
            except Exception as e:
                logger.warning(f"Failed to update collection lock: {e}")

        # Step 5: Record analytics event (stub for P4-002)
        if synced_artifacts:
            self._record_sync_event("pull", synced_artifacts)

        # Determine final status
        if not synced_artifacts and conflicts:
            status = "partial"
            message = f"Sync completed with {len(conflicts)} conflicts"
        elif synced_artifacts and conflicts:
            status = "partial"
            message = (
                f"Synced {len(synced_artifacts)} artifacts, {len(conflicts)} conflicts"
            )
        elif synced_artifacts:
            status = "success"
            message = (
                f"Successfully synced {len(synced_artifacts)} artifacts from project"
            )
        else:
            status = "no_changes"
            message = "No artifacts were synced"

        # Log completion
        logger.info(
            "Sync pull completed",
            extra={
                "status": status,
                "synced_count": len(synced_artifacts),
                "conflict_count": len(conflicts),
            },
        )

        return SyncResult(
            status=status,
            artifacts_synced=synced_artifacts,
            conflicts=conflicts,
            message=message,
        )

    def _get_project_artifact_path(
        self, project_path: Path, artifact_name: str, artifact_type: str
    ) -> Optional[Path]:
        """Get path to artifact in project.

        Args:
            project_path: Path to project root
            artifact_name: Name of artifact
            artifact_type: Type of artifact

        Returns:
            Path to artifact or None if not found
        """
        # Convert type to plural for directory name
        artifact_type_plural = self._get_artifact_type_plural(artifact_type)

        # Check in .claude directory
        artifact_path = project_path / ".claude" / artifact_type_plural / artifact_name
        if artifact_path.exists():
            return artifact_path

        return None

    def _sync_artifact(
        self,
        project_path: Path,
        drift: DriftDetectionResult,
        strategy: str,
        interactive: bool,
    ) -> ArtifactSyncResult:
        """Sync individual artifact from project to collection.

        Args:
            project_path: Path to project root
            drift: DriftDetectionResult for this artifact
            strategy: Sync strategy to use
            interactive: Whether to prompt for user input

        Returns:
            ArtifactSyncResult indicating success/failure
        """
        artifact_name = drift.artifact_name
        artifact_type = drift.artifact_type

        # Get paths
        project_artifact_path = self._get_project_artifact_path(
            project_path, artifact_name, artifact_type
        )
        if not project_artifact_path:
            result = ArtifactSyncResult(
                artifact_name=artifact_name,
                success=False,
                error=f"Artifact not found in project: {artifact_name}",
            )
            # Track failed sync
            self._record_artifact_sync_event(
                artifact_name, artifact_type, strategy, "error",
                project_path=project_path,
                sha_before=drift.collection_sha,
                error_message=result.error,
            )
            return result

        # Get collection path
        if not self.collection_mgr:
            result = ArtifactSyncResult(
                artifact_name=artifact_name,
                success=False,
                error="Collection manager not available",
            )
            # Track failed sync
            self._record_artifact_sync_event(
                artifact_name, artifact_type, strategy, "error",
                project_path=project_path,
                error_message=result.error,
            )
            return result

        try:
            # Get collection from drift metadata
            metadata = self._load_deployment_metadata(project_path)
            collection_name = metadata.collection if metadata else "default"

            collection = self.collection_mgr.load_collection(collection_name)
            collection_path = collection.path

            artifact_type_plural = self._get_artifact_type_plural(artifact_type)
            collection_artifact_path = (
                collection_path / artifact_type_plural / artifact_name
            )

            # Apply strategy
            if strategy == "prompt" and interactive:
                # Ask user which strategy to use
                from rich.console import Console
                from rich.prompt import Prompt

                console = Console()
                console.print(
                    f"\n[yellow]Artifact:[/yellow] {artifact_name} ({artifact_type})"
                )
                console.print("[yellow]Choose sync strategy:[/yellow]")
                console.print(
                    "  1. Overwrite - Replace collection with project version"
                )
                console.print(
                    "  2. Merge - Attempt to merge changes (may produce conflicts)"
                )
                console.print("  3. Fork - Create new artifact in collection")
                console.print("  4. Skip - Don't sync this artifact")

                choice = Prompt.ask(
                    "Strategy", choices=["1", "2", "3", "4"], default="1"
                )

                strategy_map = {
                    "1": "overwrite",
                    "2": "merge",
                    "3": "fork",
                    "4": "skip",
                }
                strategy = strategy_map[choice]

            if strategy == "skip":
                result = ArtifactSyncResult(
                    artifact_name=artifact_name, success=False, error="Skipped by user"
                )
                # Track cancelled sync
                self._record_artifact_sync_event(
                    artifact_name, artifact_type, strategy, "cancelled",
                    project_path=project_path,
                    sha_before=drift.collection_sha,
                    sha_after=drift.project_sha,
                )
                return result

            # Execute strategy and track event
            conflicts_count = 0
            if strategy == "overwrite":
                self._sync_overwrite(project_artifact_path, collection_artifact_path)
            elif strategy == "merge":
                merge_result = self._sync_merge(
                    project_artifact_path, collection_artifact_path, artifact_name
                )
                if merge_result.has_conflict:
                    conflicts_count = len(merge_result.conflict_files)
                    # Track sync with conflicts
                    self._record_artifact_sync_event(
                        artifact_name, artifact_type, strategy, "conflict",
                        project_path=project_path,
                        sha_before=drift.collection_sha,
                        sha_after=drift.project_sha,
                        conflicts_detected=conflicts_count,
                    )
                    return ArtifactSyncResult(
                        artifact_name=artifact_name,
                        success=True,  # Merge completed, but has conflicts
                        has_conflict=True,
                        conflict_files=merge_result.conflict_files,
                    )
            elif strategy == "fork":
                self._sync_fork(
                    project_artifact_path, collection_path, artifact_name, artifact_type
                )
            else:
                result = ArtifactSyncResult(
                    artifact_name=artifact_name,
                    success=False,
                    error=f"Unknown strategy: {strategy}",
                )
                # Track error
                self._record_artifact_sync_event(
                    artifact_name, artifact_type, strategy, "error",
                    project_path=project_path,
                    error_message=result.error,
                )
                return result

            # Track successful sync
            self._record_artifact_sync_event(
                artifact_name, artifact_type, strategy, "success",
                project_path=project_path,
                sha_before=drift.collection_sha,
                sha_after=drift.project_sha,
                conflicts_detected=conflicts_count,
            )

            return ArtifactSyncResult(artifact_name=artifact_name, success=True)

        except Exception as e:
            logger.error(f"Failed to sync artifact {artifact_name}: {e}")
            # Track error
            self._record_artifact_sync_event(
                artifact_name, artifact_type, strategy, "error",
                project_path=project_path,
                sha_before=drift.collection_sha,
                error_message=str(e),
            )
            return ArtifactSyncResult(
                artifact_name=artifact_name, success=False, error=str(e)
            )

    def _sync_overwrite(
        self, project_artifact_path: Path, collection_artifact_path: Path
    ) -> None:
        """Replace collection artifact with project version.

        Args:
            project_artifact_path: Path to artifact in project
            collection_artifact_path: Path to artifact in collection
        """
        import shutil

        # Remove old collection artifact if it exists
        if collection_artifact_path.exists():
            shutil.rmtree(collection_artifact_path)

        # Copy project artifact to collection
        shutil.copytree(project_artifact_path, collection_artifact_path)

    def _sync_merge(
        self,
        project_artifact_path: Path,
        collection_artifact_path: Path,
        artifact_name: str,
    ) -> ArtifactSyncResult:
        """Merge project changes into collection artifact.

        Uses three-way merge with deployed version as base.

        Args:
            project_artifact_path: Path to artifact in project
            collection_artifact_path: Path to artifact in collection
            artifact_name: Name of artifact

        Returns:
            ArtifactSyncResult with merge status
        """
        from skillmeat.core.merge_engine import MergeEngine

        merge_engine = MergeEngine()

        # For now, use collection as base (no true three-way merge)
        # P3-004 will add base version tracking
        # Use project as "remote" and collection as "local"
        merge_result = merge_engine.merge(
            base_path=collection_artifact_path,  # Base = current collection
            local_path=collection_artifact_path,  # Local = collection
            remote_path=project_artifact_path,  # Remote = project
            output_path=collection_artifact_path,  # Output = collection (in-place)
        )

        return ArtifactSyncResult(
            artifact_name=artifact_name,
            success=merge_result.success or not merge_result.has_conflicts,
            has_conflict=merge_result.has_conflicts,
            conflict_files=[c.file_path for c in merge_result.conflicts],
        )

    def _sync_fork(
        self,
        project_artifact_path: Path,
        collection_path: Path,
        artifact_name: str,
        artifact_type: str,
    ) -> Path:
        """Create new artifact in collection with -fork suffix.

        Args:
            project_artifact_path: Path to artifact in project
            collection_path: Path to collection root
            artifact_name: Original artifact name
            artifact_type: Artifact type

        Returns:
            Path to forked artifact
        """
        import shutil

        # Create forked name
        forked_name = f"{artifact_name}-fork"

        # Get target path
        artifact_type_plural = self._get_artifact_type_plural(artifact_type)
        forked_path = collection_path / artifact_type_plural / forked_name

        # Copy project artifact as new artifact
        shutil.copytree(project_artifact_path, forked_path)

        # Update metadata to indicate fork (if metadata file exists)
        try:
            from skillmeat.utils.metadata import (
                find_metadata_file,
                extract_artifact_metadata,
            )
            from skillmeat.models import ArtifactType

            artifact_type_enum = ArtifactType.SKILL  # For now, assume skill
            metadata_file = find_metadata_file(forked_path, artifact_type_enum)
            if metadata_file:
                metadata = extract_artifact_metadata(metadata_file)
                # Update title if it exists
                if "title" in metadata:
                    metadata["title"] += " (Forked)"
                # Write back would require YAML writer - skip for now
        except Exception as e:
            logger.warning(f"Could not update forked artifact metadata: {e}")

        return forked_path

    def _show_sync_preview(
        self, drift_results: List[DriftDetectionResult], strategy: str
    ) -> None:
        """Show preview of sync operation.

        Args:
            drift_results: List of drift results to be synced
            strategy: Sync strategy to be used
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()

        console.print("\n[bold]Sync Pull Preview[/bold]")
        console.print(f"Strategy: [cyan]{strategy}[/cyan]\n")

        console.print(
            f"Will pull [cyan]{len(drift_results)}[/cyan] artifacts from project to collection:\n"
        )

        # Show table of artifacts
        table = Table(show_header=True, header_style="bold")
        table.add_column("Artifact", style="cyan")
        table.add_column("Type")
        table.add_column("Project SHA", style="yellow")
        table.add_column("Collection SHA", style="green")

        for drift in drift_results[:10]:  # Show first 10
            table.add_row(
                drift.artifact_name,
                drift.artifact_type,
                (drift.project_sha[:12] + "..." if drift.project_sha else "N/A"),
                (drift.collection_sha[:12] + "..." if drift.collection_sha else "N/A"),
            )

        console.print(table)

        if len(drift_results) > 10:
            console.print(f"\n... and {len(drift_results) - 10} more\n")

        if strategy == "merge":
            console.print("[yellow]Note: Merge strategy may produce conflicts[/yellow]")
            console.print(
                "[yellow]Conflicts will be marked with Git-style markers[/yellow]\n"
            )

    def _confirm_sync(self, drift_results: List[DriftDetectionResult] = None, strategy: str = "prompt") -> bool:
        """Confirm sync operation with user.

        Args:
            drift_results: Optional drift results for additional context
            strategy: Sync strategy being used

        Returns:
            True if user confirms, False otherwise
        """
        from rich.console import Console
        from rich.prompt import Confirm

        console = Console()

        # Show warnings
        console.print("\n[bold yellow]⚠  Warning: This will modify your collection[/bold yellow]")

        if drift_results:
            console.print(f"Artifacts to sync: [cyan]{len(drift_results)}[/cyan]")

        if strategy == "overwrite":
            console.print("[yellow]Strategy: overwrite - Collection versions will be replaced[/yellow]")
        elif strategy == "merge":
            console.print("[yellow]Strategy: merge - May produce conflicts requiring manual resolution[/yellow]")
        elif strategy == "fork":
            console.print("[cyan]Strategy: fork - Will create new artifacts with -fork suffix[/cyan]")

        # Ask for confirmation
        return Confirm.ask("\n[bold]Proceed with sync?[/bold]", default=True)

    def _update_collection_lock(
        self, synced_artifacts: List[str], drift_results: List[DriftDetectionResult]
    ) -> None:
        """Update collection lock file after sync.

        Args:
            synced_artifacts: List of artifact names that were synced
            drift_results: Original drift results
        """
        if not self.collection_mgr:
            return

        # For each synced artifact, update the lock file
        for artifact_name in synced_artifacts:
            # Find drift result for this artifact
            drift = next(
                (d for d in drift_results if d.artifact_name == artifact_name), None
            )
            if not drift:
                continue

            try:
                # Get collection path
                metadata = self._load_deployment_metadata(Path("."))
                collection_name = metadata.collection if metadata else "default"
                collection = self.collection_mgr.load_collection(collection_name)

                # Compute new hash
                artifact_type_plural = self._get_artifact_type_plural(
                    drift.artifact_type
                )
                artifact_path = collection.path / artifact_type_plural / artifact_name
                new_sha = self._compute_artifact_hash(artifact_path)

                # Update lock file
                if hasattr(self.collection_mgr, "lock_mgr"):
                    self.collection_mgr.lock_mgr.update_entry(
                        artifact_name=artifact_name,
                        artifact_type=drift.artifact_type,
                        resolved_sha=new_sha,
                        resolved_version=drift.project_version or "unknown",
                    )
            except Exception as e:
                logger.warning(f"Failed to update lock for {artifact_name}: {e}")

    def _record_artifact_sync_event(
        self,
        artifact_name: str,
        artifact_type: str,
        sync_type: str,
        result: str,
        project_path: Optional[Path] = None,
        sha_before: Optional[str] = None,
        sha_after: Optional[str] = None,
        conflicts_detected: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """Record individual artifact sync event for analytics.

        Args:
            artifact_name: Name of artifact synced
            artifact_type: Type of artifact (skill, command, agent)
            sync_type: Type of sync (overwrite, merge, fork)
            result: Result of sync (success, conflict, error, cancelled)
            project_path: Optional path to project
            sha_before: Optional SHA before sync
            sha_after: Optional SHA after sync
            conflicts_detected: Number of conflicts detected (default: 0)
            error_message: Optional error message if result is error
        """
        try:
            from skillmeat.core.analytics import EventTracker

            # Get collection name from collection manager
            collection_name = None
            if self.collection_mgr:
                try:
                    collection = self.collection_mgr.get_active_collection()
                    collection_name = collection.name if collection else "default"
                except Exception:
                    collection_name = "default"

            # Record sync event
            with EventTracker() as tracker:
                tracker.track_sync(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type,
                    collection_name=collection_name or "default",
                    sync_type=sync_type,
                    result=result,
                    project_path=str(project_path) if project_path else None,
                    sha_before=sha_before,
                    sha_after=sha_after,
                    conflicts_detected=conflicts_detected,
                    error_message=error_message,
                )

        except Exception as e:
            # Never fail sync due to analytics
            logger.debug(f"Failed to record sync analytics: {e}")

    def _record_sync_event(self, sync_type: str, artifact_names: List[str]) -> None:
        """Record sync event for analytics (legacy method for batch tracking).

        Args:
            sync_type: Type of sync ("pull" or "push")
            artifact_names: List of artifact names synced
        """
        # This method is now mostly for logging - individual events are
        # tracked per-artifact in _record_artifact_sync_event
        logger.info(f"Sync {sync_type}: {len(artifact_names)} artifacts")
