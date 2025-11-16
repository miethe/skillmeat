"""Bundle import engine with conflict resolution and analytics tracking.

Handles importing artifact bundles into collections with comprehensive validation,
conflict resolution, and rollback support.
"""

import logging
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

from rich.console import Console

from skillmeat.core.artifact import Artifact, ArtifactManager, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.sharing.strategies import (
    ConflictDecision,
    ConflictResolution,
    ImportStrategy,
    get_strategy,
)
from skillmeat.core.sharing.validator import BundleValidator, ValidationResult
from skillmeat.utils.filesystem import FilesystemManager

logger = logging.getLogger(__name__)


@dataclass
class ImportedArtifact:
    """Represents an artifact that was imported."""

    name: str
    type: str
    resolution: str  # "imported", "forked", "skipped", "merged"
    new_name: Optional[str] = None  # For forked artifacts
    reason: Optional[str] = None


@dataclass
class ImportResult:
    """Result of bundle import operation."""

    success: bool
    imported_count: int = 0
    skipped_count: int = 0
    forked_count: int = 0
    merged_count: int = 0
    artifacts: List[ImportedArtifact] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    bundle_hash: Optional[str] = None
    import_time: Optional[datetime] = None

    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.success:
            return (
                f"Import successful: {self.imported_count + self.merged_count + self.forked_count} "
                f"artifacts imported, {self.skipped_count} skipped"
            )
        else:
            return f"Import failed: {len(self.errors)} errors"


class BundleImporter:
    """Handles importing artifact bundles into collections.

    Features:
    - Comprehensive validation before import
    - Conflict resolution with multiple strategies
    - Atomic operations (all or nothing)
    - Rollback support on failure
    - Analytics tracking
    - Idempotent imports (same bundle = same result)
    """

    def __init__(
        self,
        collection_mgr: Optional[CollectionManager] = None,
        artifact_mgr: Optional[ArtifactManager] = None,
        validator: Optional[BundleValidator] = None,
        filesystem_mgr: Optional[FilesystemManager] = None,
    ):
        """Initialize bundle importer.

        Args:
            collection_mgr: CollectionManager instance
            artifact_mgr: ArtifactManager instance
            validator: BundleValidator instance
            filesystem_mgr: FilesystemManager instance
        """
        self.collection_mgr = collection_mgr or CollectionManager()
        self.artifact_mgr = artifact_mgr or ArtifactManager(self.collection_mgr)
        self.validator = validator or BundleValidator()
        self.filesystem_mgr = filesystem_mgr or FilesystemManager()

    def import_bundle(
        self,
        bundle_path: Path,
        collection_name: Optional[str] = None,
        strategy: str = "interactive",
        dry_run: bool = False,
        force: bool = False,
        expected_hash: Optional[str] = None,
        verify_signature: bool = True,
        require_signature: bool = False,
        console: Optional[Console] = None,
    ) -> ImportResult:
        """Import bundle into collection.

        Args:
            bundle_path: Path to bundle ZIP file
            collection_name: Target collection (uses active if None)
            strategy: Import strategy ("merge", "fork", "skip", "interactive")
            dry_run: If True, only validate and show what would be imported
            force: If True, skip some validation checks
            expected_hash: Optional bundle hash for verification
            verify_signature: If True, verify bundle signature if present
            require_signature: If True, fail if bundle is unsigned
            console: Optional Rich console for output

        Returns:
            ImportResult with import details

        Raises:
            ValueError: If validation fails or collection not found
        """
        if console is None:
            console = Console()

        import_start = datetime.now()
        result = ImportResult(success=False, import_time=import_start)

        # Step 1: Validate bundle
        console.print("[cyan]Validating bundle...[/cyan]")
        validation = self.validator.validate(bundle_path, expected_hash)

        if not validation.is_valid:
            result.errors.append("Bundle validation failed")
            for issue in validation.get_errors():
                result.errors.append(str(issue))
            for issue in validation.get_warnings():
                result.warnings.append(str(issue))
            
            if not force:
                console.print("[red]Bundle validation failed. Use --force to override.[/red]")
                return result

        result.bundle_hash = validation.bundle_hash

        # Show validation warnings
        if validation.has_warnings():
            console.print("[yellow]Validation warnings:[/yellow]")
            for warning in validation.get_warnings():
                console.print(f"  - {warning}")

        console.print(f"[green]Bundle validated:[/green] {validation.summary()}")

        # Step 1.5: Verify signature if present
        if verify_signature or require_signature:
            console.print("[cyan]Verifying bundle signature...[/cyan]")

            from skillmeat.core.signing import BundleVerifier, KeyManager

            key_manager = KeyManager()
            verifier = BundleVerifier(key_manager)

            # Read manifest from bundle
            import zipfile

            with zipfile.ZipFile(bundle_path, "r") as zf:
                manifest_data = __import__("json").loads(
                    zf.read("manifest.json")
                )

            verification = verifier.verify_bundle(
                validation.bundle_hash, manifest_data, require_signature
            )

            if verification.valid:
                console.print(f"[green]{verification.summary()}[/green]")
            elif verification.status.value == "unsigned" and not require_signature:
                console.print(f"[yellow]{verification.summary()}[/yellow]")
            else:
                console.print(f"[red]{verification.summary()}[/red]")
                if not force:
                    result.errors.append(f"Signature verification failed: {verification.message}")
                    return result
                else:
                    result.warnings.append(
                        f"Signature verification failed but continuing due to --force: {verification.message}"
                    )

        # Step 2: Load target collection
        try:
            collection = self.collection_mgr.load_collection(collection_name)
            collection_name = collection.name
        except Exception as e:
            result.errors.append(f"Failed to load collection: {e}")
            console.print(f"[red]Error loading collection: {e}[/red]")
            return result

        # Step 3: Extract and analyze bundle
        temp_extract_dir = None
        try:
            temp_extract_dir = Path(tempfile.mkdtemp(prefix="skillmeat_import_"))
            
            console.print(f"[cyan]Extracting bundle to temporary workspace...[/cyan]")
            self._extract_bundle(bundle_path, temp_extract_dir)

            # Load manifest
            manifest_path = temp_extract_dir / "bundle.toml"
            manifest_data = self._load_manifest(manifest_path)

            # Step 4: Detect conflicts
            console.print("[cyan]Analyzing artifacts and detecting conflicts...[/cyan]")
            conflicts, non_conflicts = self._detect_conflicts(
                manifest_data, collection
            )

            if conflicts:
                console.print(
                    f"[yellow]Found {len(conflicts)} conflicts with existing artifacts[/yellow]"
                )
            console.print(
                f"[green]{len(non_conflicts)} new artifacts to import[/green]"
            )

            # Get import strategy
            import_strategy = get_strategy(strategy, interactive=not dry_run)

            # Step 5: Resolve conflicts
            decisions: List[ConflictDecision] = []
            if conflicts:
                console.print(
                    f"\n[cyan]Resolving conflicts using '{import_strategy.name()}' strategy...[/cyan]"
                )
                for existing, imported in conflicts:
                    decision = import_strategy.resolve_conflict(
                        existing, imported, console
                    )
                    decisions.append(decision)

                    # Show decision
                    if decision.resolution == ConflictResolution.MERGE:
                        console.print(
                            f"  [yellow]Merge:[/yellow] {existing.type.value}/{existing.name}"
                        )
                    elif decision.resolution == ConflictResolution.FORK:
                        console.print(
                            f"  [cyan]Fork:[/cyan] {existing.type.value}/{existing.name} "
                            f"-> {decision.new_name}"
                        )
                    elif decision.resolution == ConflictResolution.SKIP:
                        console.print(
                            f"  [gray]Skip:[/gray] {existing.type.value}/{existing.name}"
                        )

            # Dry run: show what would happen and exit
            if dry_run:
                console.print("\n[cyan]Dry run mode - no changes made[/cyan]")
                console.print(f"Would import: {len(non_conflicts)} new artifacts")
                console.print(f"Would merge: {sum(1 for d in decisions if d.resolution == ConflictResolution.MERGE)}")
                console.print(f"Would fork: {sum(1 for d in decisions if d.resolution == ConflictResolution.FORK)}")
                console.print(f"Would skip: {sum(1 for d in decisions if d.resolution == ConflictResolution.SKIP)}")
                result.success = True
                return result

            # Step 6: Create snapshot before import (for rollback)
            snapshot = None
            try:
                from skillmeat.core.version import VersionManager

                version_mgr = VersionManager(self.collection_mgr)
                snapshot = version_mgr.auto_snapshot(
                    collection_name,
                    f"Before importing bundle {bundle_path.name}",
                )
                console.print(
                    f"[green]Created snapshot {snapshot.id} for rollback safety[/green]"
                )
            except Exception as e:
                logger.warning(f"Failed to create snapshot: {e}")
                result.warnings.append(f"Snapshot creation failed: {e}")

            # Step 7: Execute import
            try:
                console.print("\n[cyan]Importing artifacts...[/cyan]")
                
                # Import non-conflicting artifacts
                for artifact_data in non_conflicts:
                    try:
                        self._import_artifact(
                            artifact_data,
                            temp_extract_dir,
                            collection,
                            console,
                        )
                        result.imported_count += 1
                        result.artifacts.append(
                            ImportedArtifact(
                                name=artifact_data["name"],
                                type=artifact_data["type"],
                                resolution="imported",
                            )
                        )
                    except Exception as e:
                        error_msg = (
                            f"Failed to import {artifact_data['type']}/{artifact_data['name']}: {e}"
                        )
                        result.errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
                        raise  # Trigger rollback

                # Apply conflict resolutions
                for decision in decisions:
                    try:
                        self._apply_conflict_resolution(
                            decision,
                            manifest_data,
                            temp_extract_dir,
                            collection,
                            result,
                            console,
                        )
                    except Exception as e:
                        error_msg = (
                            f"Failed to resolve conflict for "
                            f"{decision.artifact_type.value}/{decision.artifact_name}: {e}"
                        )
                        result.errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
                        raise  # Trigger rollback

                # Success - save collection
                self.collection_mgr.save_collection(collection)
                result.success = True

                console.print(
                    f"\n[green]Import completed successfully![/green]"
                )
                console.print(f"  Imported: {result.imported_count}")
                console.print(f"  Merged: {result.merged_count}")
                console.print(f"  Forked: {result.forked_count}")
                console.print(f"  Skipped: {result.skipped_count}")

                # Record analytics
                self._record_import_analytics(
                    bundle_path,
                    collection_name,
                    result,
                    manifest_data,
                )

            except Exception as e:
                # Rollback on failure
                logger.error(f"Import failed: {e}", exc_info=True)
                result.errors.append(f"Import failed: {e}")

                if snapshot:
                    console.print(
                        f"\n[red]Import failed. Rolling back to snapshot {snapshot.id}...[/red]"
                    )
                    try:
                        from skillmeat.storage.snapshot import SnapshotManager

                        config = self.collection_mgr.config
                        snapshots_dir = config.get_snapshots_dir()
                        snapshot_mgr = SnapshotManager(snapshots_dir)
                        collection_path = config.get_collection_path(collection_name)
                        snapshot_mgr.restore_snapshot(snapshot, collection_path)
                        console.print("[green]Rollback successful[/green]")
                    except Exception as rollback_error:
                        logger.error(f"Rollback failed: {rollback_error}", exc_info=True)
                        result.errors.append(f"Rollback failed: {rollback_error}")
                        console.print(
                            f"[red]CRITICAL: Rollback failed: {rollback_error}[/red]"
                        )
                else:
                    console.print(
                        "[red]No snapshot available for rollback. "
                        "Collection may be in inconsistent state.[/red]"
                    )

        finally:
            # Clean up temp directory
            if temp_extract_dir and temp_extract_dir.exists():
                try:
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory: {e}")

        return result

    def _extract_bundle(self, bundle_path: Path, extract_dir: Path) -> None:
        """Extract bundle ZIP to directory.

        Args:
            bundle_path: Path to bundle ZIP
            extract_dir: Target extraction directory

        Raises:
            zipfile.BadZipFile: If ZIP is invalid
        """
        with zipfile.ZipFile(bundle_path, "r") as zf:
            zf.extractall(extract_dir)

    def _load_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        """Load and parse bundle manifest.

        Args:
            manifest_path: Path to bundle.toml

        Returns:
            Parsed manifest data

        Raises:
            FileNotFoundError: If manifest doesn't exist
            ValueError: If manifest is invalid
        """
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "rb") as f:
            return TOML_LOADS(f.read().decode("utf-8"))

    def _detect_conflicts(
        self, manifest_data: Dict[str, Any], collection: Collection
    ) -> tuple[List[tuple[Artifact, dict]], List[dict]]:
        """Detect conflicts between bundle and collection.

        Args:
            manifest_data: Parsed bundle manifest
            collection: Target collection

        Returns:
            Tuple of (conflicts, non_conflicts)
            - conflicts: List of (existing_artifact, imported_artifact_data)
            - non_conflicts: List of imported_artifact_data
        """
        conflicts = []
        non_conflicts = []

        artifacts = manifest_data.get("artifacts", [])
        for artifact_data in artifacts:
            artifact_name = artifact_data["name"]
            artifact_type = ArtifactType(artifact_data["type"])

            # Check if exists
            existing = collection.find_artifact(artifact_name, artifact_type)

            if existing:
                conflicts.append((existing, artifact_data))
            else:
                non_conflicts.append(artifact_data)

        return conflicts, non_conflicts

    def _import_artifact(
        self,
        artifact_data: dict,
        bundle_dir: Path,
        collection: Collection,
        console: Console,
    ) -> None:
        """Import single artifact into collection.

        Args:
            artifact_data: Artifact data from manifest
            bundle_dir: Extracted bundle directory
            collection: Target collection
            console: Rich console for output

        Raises:
            ValueError: If import fails
        """
        artifact_name = artifact_data["name"]
        artifact_type = ArtifactType(artifact_data["type"])
        artifact_path_rel = artifact_data["path"]

        # Source path in bundle
        source_path = bundle_dir / artifact_path_rel

        if not source_path.exists():
            raise ValueError(
                f"Artifact files not found in bundle: {artifact_path_rel}"
            )

        # Destination path in collection
        collection_path = self.collection_mgr.config.get_collection_path(
            collection.name
        )
        
        if artifact_type == ArtifactType.SKILL:
            dest_path = collection_path / "skills" / artifact_name
        elif artifact_type == ArtifactType.COMMAND:
            dest_path = collection_path / "commands" / f"{artifact_name}.md"
        elif artifact_type == ArtifactType.AGENT:
            dest_path = collection_path / "agents" / f"{artifact_name}.md"
        else:
            raise ValueError(f"Unsupported artifact type: {artifact_type}")

        # Copy artifact
        self.filesystem_mgr.copy_artifact(source_path, dest_path, artifact_type)

        # Extract metadata
        from skillmeat.utils.metadata import extract_artifact_metadata

        metadata = extract_artifact_metadata(dest_path, artifact_type)

        # Create Artifact object
        artifact = Artifact(
            name=artifact_name,
            type=artifact_type,
            path=str(dest_path.relative_to(collection_path)),
            origin=artifact_data.get("origin", "local"),
            metadata=metadata,
            added=datetime.utcnow(),
            upstream=artifact_data.get("upstream"),
            version_spec=artifact_data.get("version_spec"),
            resolved_sha=artifact_data.get("resolved_sha"),
            resolved_version=artifact_data.get("resolved_version"),
            tags=artifact_data.get("tags", []),
        )

        # Add to collection
        collection.add_artifact(artifact)

        # Update lock file
        from skillmeat.utils.filesystem import compute_content_hash

        content_hash = compute_content_hash(dest_path)
        self.collection_mgr.lock_mgr.update_entry(
            collection_path,
            artifact.name,
            artifact.type,
            artifact.upstream,
            artifact.resolved_sha,
            artifact.resolved_version,
            content_hash,
        )

        console.print(
            f"  [green]Imported:[/green] {artifact_type.value}/{artifact_name}"
        )

    def _apply_conflict_resolution(
        self,
        decision: ConflictDecision,
        manifest_data: Dict[str, Any],
        bundle_dir: Path,
        collection: Collection,
        result: ImportResult,
        console: Console,
    ) -> None:
        """Apply conflict resolution decision.

        Args:
            decision: ConflictDecision indicating how to resolve
            manifest_data: Bundle manifest
            bundle_dir: Extracted bundle directory
            collection: Target collection
            result: ImportResult to update
            console: Rich console for output
        """
        # Find artifact data in manifest
        artifact_data = None
        for artifact in manifest_data.get("artifacts", []):
            if (
                artifact["name"] == decision.artifact_name
                and ArtifactType(artifact["type"]) == decision.artifact_type
            ):
                artifact_data = artifact
                break

        if not artifact_data:
            raise ValueError(
                f"Artifact {decision.artifact_type.value}/{decision.artifact_name} "
                "not found in manifest"
            )

        if decision.resolution == ConflictResolution.SKIP:
            result.skipped_count += 1
            result.artifacts.append(
                ImportedArtifact(
                    name=decision.artifact_name,
                    type=decision.artifact_type.value,
                    resolution="skipped",
                    reason=decision.reason,
                )
            )
            console.print(
                f"  [gray]Skipped:[/gray] {decision.artifact_type.value}/{decision.artifact_name}"
            )

        elif decision.resolution == ConflictResolution.MERGE:
            # Remove existing, then import
            self.artifact_mgr.remove(
                decision.artifact_name,
                decision.artifact_type,
                collection.name,
            )
            # Reload collection after removal
            collection = self.collection_mgr.load_collection(collection.name)
            
            # Import
            self._import_artifact(artifact_data, bundle_dir, collection, console)
            result.merged_count += 1
            result.artifacts.append(
                ImportedArtifact(
                    name=decision.artifact_name,
                    type=decision.artifact_type.value,
                    resolution="merged",
                    reason=decision.reason,
                )
            )

        elif decision.resolution == ConflictResolution.FORK:
            # Import with new name
            original_name = artifact_data["name"]
            artifact_data["name"] = decision.new_name
            
            try:
                self._import_artifact(artifact_data, bundle_dir, collection, console)
                result.forked_count += 1
                result.artifacts.append(
                    ImportedArtifact(
                        name=original_name,
                        type=decision.artifact_type.value,
                        resolution="forked",
                        new_name=decision.new_name,
                        reason=decision.reason,
                    )
                )
            finally:
                # Restore original name
                artifact_data["name"] = original_name

    def _record_import_analytics(
        self,
        bundle_path: Path,
        collection_name: str,
        result: ImportResult,
        manifest_data: Dict[str, Any],
    ) -> None:
        """Record import operation in analytics.

        Args:
            bundle_path: Path to bundle file
            collection_name: Name of target collection
            result: Import result
            manifest_data: Bundle manifest
        """
        try:
            from skillmeat.core.analytics import EventTracker

            bundle_name = manifest_data.get("bundle", {}).get("name", "unknown")

            with EventTracker() as tracker:
                # Record import event for each artifact
                for imported_artifact in result.artifacts:
                    if imported_artifact.resolution != "skipped":
                        tracker.track_event(
                            event_type="import",
                            artifact_name=imported_artifact.new_name or imported_artifact.name,
                            artifact_type=imported_artifact.type,
                            collection_name=collection_name,
                            metadata={
                                "bundle_name": bundle_name,
                                "bundle_hash": result.bundle_hash,
                                "resolution": imported_artifact.resolution,
                                "original_name": imported_artifact.name,
                            },
                        )

        except Exception as e:
            logger.debug(f"Failed to record import analytics: {e}")
