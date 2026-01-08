"""Version management and snapshot operations for SkillMeat collections."""

import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.prompt import Confirm

from skillmeat.core.diff_engine import DiffEngine
from skillmeat.core.merge_engine import MergeEngine
from skillmeat.models import (
    ConflictMetadata,
    RollbackAuditEntry,
    RollbackResult,
    RollbackSafetyAnalysis,
)
from skillmeat.storage.snapshot import Snapshot, SnapshotManager

# TOML libraries (Python 3.11+ has tomllib built-in)
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w

console = Console()


class RollbackAuditTrail:
    """Manages rollback audit history for collections.

    Stores detailed audit logs of all rollback operations in per-collection
    TOML files for debugging and history tracking. Each collection has its own
    audit file at: {storage_path}/{collection_name}_rollback_audit.toml

    Attributes:
        storage_path: Directory to store audit logs (e.g., ~/.skillmeat/audit/)
    """

    def __init__(self, storage_path: Path):
        """Initialize audit trail.

        Args:
            storage_path: Path to store audit log files

        Example:
            >>> audit_trail = RollbackAuditTrail(Path.home() / ".skillmeat" / "audit")
            >>> entry = RollbackAuditEntry(...)
            >>> audit_trail.record(entry)
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _get_audit_file(self, collection_name: str) -> Path:
        """Get path to audit file for collection.

        Args:
            collection_name: Collection name

        Returns:
            Path to TOML audit file
        """
        return self.storage_path / f"{collection_name}_rollback_audit.toml"

    def record(self, entry: RollbackAuditEntry) -> None:
        """Record a rollback operation.

        Appends the audit entry to the collection's audit log file. Creates
        the file if it doesn't exist.

        Args:
            entry: RollbackAuditEntry to record

        Example:
            >>> entry = RollbackAuditEntry(
            ...     id="rb_20241216_123456",
            ...     timestamp=datetime.now(),
            ...     collection_name="default",
            ...     source_snapshot_id="snap_abc123",
            ...     target_snapshot_id="snap_def456",
            ...     operation_type="intelligent",
            ...     files_merged=["skill.md"],
            ...     success=True,
            ... )
            >>> audit_trail.record(entry)
        """
        audit_file = self._get_audit_file(entry.collection_name)

        # Load existing entries
        existing_entries = []
        if audit_file.exists():
            with open(audit_file, "rb") as f:
                data = tomllib.load(f)
                existing_entries = data.get("entries", [])

        # Append new entry
        existing_entries.append(entry.to_dict())

        # Write back to file
        audit_data = {"entries": existing_entries}
        with open(audit_file, "wb") as f:
            tomli_w.dump(audit_data, f)

    def get_history(
        self,
        collection_name: str,
        limit: int = 50,
    ) -> List[RollbackAuditEntry]:
        """Get rollback history for collection.

        Retrieves audit entries for the specified collection, newest first.

        Args:
            collection_name: Collection name
            limit: Maximum number of entries to return (default 50)

        Returns:
            List of RollbackAuditEntry objects, newest first

        Example:
            >>> history = audit_trail.get_history("default", limit=10)
            >>> for entry in history:
            ...     print(f"{entry.timestamp}: {entry.operation_type} -> {entry.success}")
        """
        audit_file = self._get_audit_file(collection_name)

        if not audit_file.exists():
            return []

        with open(audit_file, "rb") as f:
            data = tomllib.load(f)
            entries_data = data.get("entries", [])

        # Convert to RollbackAuditEntry objects
        entries = [RollbackAuditEntry.from_dict(e) for e in entries_data]

        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_entry(self, entry_id: str) -> Optional[RollbackAuditEntry]:
        """Get specific audit entry by ID.

        Searches all audit files for the entry with the specified ID.

        Args:
            entry_id: Unique audit entry ID

        Returns:
            RollbackAuditEntry if found, None otherwise

        Example:
            >>> entry = audit_trail.get_entry("rb_20241216_123456")
            >>> if entry:
            ...     print(f"Found entry for {entry.collection_name}")
        """
        # Search all audit files
        for audit_file in self.storage_path.glob("*_rollback_audit.toml"):
            with open(audit_file, "rb") as f:
                data = tomllib.load(f)
                entries_data = data.get("entries", [])

            for entry_data in entries_data:
                if entry_data.get("id") == entry_id:
                    return RollbackAuditEntry.from_dict(entry_data)

        return None


class VersionManager:
    """Manages collection versioning and snapshots."""

    def __init__(
        self,
        collection_mgr=None,
        snapshot_mgr: Optional[SnapshotManager] = None,
        audit_trail: Optional[RollbackAuditTrail] = None,
    ):
        """Initialize version manager.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
            snapshot_mgr: SnapshotManager instance (creates default if None)
            audit_trail: RollbackAuditTrail instance (creates default if None)
        """
        if collection_mgr is None:
            from skillmeat.core.collection import CollectionManager

            collection_mgr = CollectionManager()

        self.collection_mgr = collection_mgr

        if snapshot_mgr is None:
            snapshots_dir = self.collection_mgr.config.get_snapshots_dir()
            self.snapshot_mgr = SnapshotManager(snapshots_dir)
        else:
            self.snapshot_mgr = snapshot_mgr

        if audit_trail is None:
            # Create default audit trail in ~/.skillmeat/audit/
            audit_dir = Path.home() / ".skillmeat" / "audit"
            self.audit_trail = RollbackAuditTrail(audit_dir)
        else:
            self.audit_trail = audit_trail

    def create_snapshot(
        self,
        collection_name: Optional[str] = None,
        message: str = "Manual snapshot",
    ) -> Snapshot:
        """Create collection snapshot.

        Args:
            collection_name: Collection name (uses active if None)
            message: Snapshot description

        Returns:
            Created Snapshot object

        Raises:
            ValueError: Collection not found
            RuntimeError: Snapshot creation failed
        """
        # Get collection name
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        # Get collection path
        collection_path = self.collection_mgr.config.get_collection_path(
            collection_name
        )

        if not collection_path.exists():
            raise ValueError(f"Collection '{collection_name}' not found")

        console.print(f"[blue]Creating snapshot of '{collection_name}'...[/blue]")

        # Create snapshot
        snapshot = self.snapshot_mgr.create_snapshot(
            collection_path, collection_name, message
        )

        console.print(f"[green][/green] Snapshot created: {snapshot.id}")
        console.print(f"  Message: {snapshot.message}")
        console.print(f"  Artifacts: {snapshot.artifact_count}")

        return snapshot

    def list_snapshots(
        self,
        collection_name: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Snapshot], Optional[str]]:
        """List snapshots with cursor-based pagination.

        Args:
            collection_name: Collection name (uses active if None)
            limit: Maximum snapshots to return (default 50, max 100)
            cursor: Pagination cursor (snapshot ID to start after)

        Returns:
            Tuple of (snapshots, next_cursor)
            - snapshots: List of Snapshot objects, sorted newest first
            - next_cursor: ID of last snapshot if more exist, None otherwise

        Raises:
            ValueError: If limit is out of bounds or cursor is invalid

        Example:
            >>> # Get first page
            >>> snapshots, cursor = version_mgr.list_snapshots(limit=20)
            >>> # Get next page
            >>> more_snapshots, next_cursor = version_mgr.list_snapshots(limit=20, cursor=cursor)
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        return self.snapshot_mgr.list_snapshots(
            collection_name, limit=limit, cursor=cursor
        )

    def get_snapshot(
        self,
        snapshot_id: str,
        collection_name: Optional[str] = None,
    ) -> Optional[Snapshot]:
        """Get specific snapshot by ID.

        Args:
            snapshot_id: Snapshot ID
            collection_name: Collection name (uses active if None)

        Returns:
            Snapshot if found, None otherwise
        """
        # Get all snapshots (iterate through pages if needed)
        cursor = None
        while True:
            snapshots, next_cursor = self.list_snapshots(
                collection_name, limit=100, cursor=cursor
            )

            # Search current page
            for snapshot in snapshots:
                if snapshot.id == snapshot_id:
                    return snapshot

            # If no more pages, snapshot not found
            if next_cursor is None:
                break

            cursor = next_cursor

        return None

    def rollback(
        self,
        snapshot_id: str,
        collection_name: Optional[str] = None,
        confirm: bool = True,
    ) -> None:
        """Rollback to snapshot.

        Args:
            snapshot_id: Snapshot ID to restore
            collection_name: Collection name (uses active if None)
            confirm: Require user confirmation (default True)

        Raises:
            ValueError: Snapshot not found or user cancelled
            RuntimeError: Rollback failed
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        # Get snapshot
        snapshot = self.get_snapshot(snapshot_id, collection_name)
        if not snapshot:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        # Confirm with user
        if confirm:
            console.print(
                "[yellow]Warning:[/yellow] Rolling back to snapshot will replace current collection"
            )
            console.print(f"  Snapshot: {snapshot.id}")
            console.print(
                f"  Created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            console.print(f"  Message: {snapshot.message}")

            if not Confirm.ask("Proceed with rollback?"):
                raise ValueError("Rollback cancelled by user")

        # Create safety snapshot first
        console.print("[blue]Creating safety snapshot before rollback...[/blue]")
        safety_snapshot = self.auto_snapshot(collection_name, "Before rollback")

        # Perform rollback
        collection_path = self.collection_mgr.config.get_collection_path(
            collection_name
        )
        console.print(f"[blue]Restoring snapshot {snapshot.id}...[/blue]")

        # Track rollback operation
        rollback_success = False
        rollback_error = None

        try:
            self.snapshot_mgr.restore_snapshot(snapshot, collection_path)
            console.print(f"[green]✓[/green] Successfully rolled back to {snapshot.id}")
            rollback_success = True
        except Exception as e:
            console.print(f"[red]Error during rollback:[/red] {e}")
            rollback_error = str(e)
            raise
        finally:
            # Record audit entry
            audit_entry = RollbackAuditEntry(
                id=f"rb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(),
                collection_name=collection_name,
                source_snapshot_id=safety_snapshot.id,
                target_snapshot_id=snapshot_id,
                operation_type="simple",
                files_restored=["(all files)"],  # Simple rollback restores everything
                preserve_changes_enabled=False,
                success=rollback_success,
                error=rollback_error,
            )
            self.audit_trail.record(audit_entry)

    def analyze_rollback_safety(
        self,
        snapshot_id: str,
        collection_name: Optional[str] = None,
    ) -> RollbackSafetyAnalysis:
        """Analyze whether rollback is safe before attempting.

        Performs a dry-run analysis to detect potential conflicts BEFORE
        attempting rollback. This helps users understand what will happen
        and avoid data loss from bad rollbacks.

        Checks:
        1. Snapshot exists and is valid
        2. Local changes that would conflict with rollback
        3. Files that would be lost vs preserved
        4. Estimated conflict count

        Args:
            snapshot_id: Snapshot ID to analyze
            collection_name: Collection name (uses active if None)

        Returns:
            RollbackSafetyAnalysis with detailed breakdown

        Example:
            >>> analysis = version_mgr.analyze_rollback_safety("snapshot123")
            >>> if analysis.is_safe:
            ...     print(f"Safe to rollback: {analysis.summary()}")
            >>> else:
            ...     print(f"Conflicts: {len(analysis.files_with_conflicts)}")
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        # Check if snapshot exists
        snapshot = self.get_snapshot(snapshot_id, collection_name)
        if not snapshot:
            return RollbackSafetyAnalysis(
                is_safe=False,
                snapshot_id=snapshot_id,
                snapshot_exists=False,
            )

        # Get collection path
        collection_path = self.collection_mgr.config.get_collection_path(
            collection_name
        )

        if not collection_path.exists():
            return RollbackSafetyAnalysis(
                is_safe=False,
                snapshot_id=snapshot_id,
                snapshot_exists=True,
                warnings=[f"Collection '{collection_name}' not found"],
            )

        # Extract target snapshot to temp directory for comparison
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_snapshot = Path(tmpdir) / "snapshot"
            tmp_snapshot.mkdir()

            try:
                # Extract snapshot
                self.snapshot_mgr.restore_snapshot(snapshot, tmp_snapshot)

                # Perform three-way diff to detect conflicts
                # In rollback context:
                # - base = target snapshot (what we're rolling back to)
                # - local = current collection state (with user's uncommitted changes)
                # - remote = target snapshot (same as base for rollback)
                diff_engine = DiffEngine()
                diff_result = diff_engine.three_way_diff(
                    base_path=tmp_snapshot,
                    local_path=collection_path,
                    remote_path=tmp_snapshot,  # Remote is same as base for rollback
                )

                # Analyze results
                local_changes_count = len(diff_result.auto_mergeable) + len(
                    diff_result.conflicts
                )
                conflicts = [c.file_path for c in diff_result.conflicts]
                safe_to_restore = diff_result.auto_mergeable
                files_to_merge = [
                    c.file_path for c in diff_result.conflicts if c.auto_mergeable
                ]

                # Determine if rollback is safe
                is_safe = len(conflicts) == 0

                # Build analysis
                analysis = RollbackSafetyAnalysis(
                    is_safe=is_safe,
                    snapshot_id=snapshot_id,
                    snapshot_exists=True,
                    local_changes_detected=local_changes_count,
                    files_with_conflicts=conflicts,
                    files_safe_to_restore=safe_to_restore,
                    files_to_merge=files_to_merge,
                )

                # Add warnings for binary conflicts
                binary_conflicts = [c for c in diff_result.conflicts if c.is_binary]
                if binary_conflicts:
                    analysis.warnings.append(
                        f"{len(binary_conflicts)} binary file(s) have conflicts and cannot be auto-merged"
                    )

                # Warn about local changes that will be lost
                if not is_safe and local_changes_count > 0:
                    analysis.warnings.append(
                        f"{local_changes_count} local changes detected - some may be lost during rollback"
                    )

                return analysis

            except Exception as e:
                return RollbackSafetyAnalysis(
                    is_safe=False,
                    snapshot_id=snapshot_id,
                    snapshot_exists=True,
                    warnings=[f"Analysis failed: {str(e)}"],
                )

    def intelligent_rollback(
        self,
        snapshot_id: str,
        collection_name: Optional[str] = None,
        preserve_changes: bool = True,
        selective_paths: Optional[List[str]] = None,
        confirm: bool = True,
    ) -> RollbackResult:
        """Rollback to snapshot with intelligent change preservation.

        This method performs a three-way merge during rollback to preserve
        uncommitted local changes where possible. It uses:
        - Base: target snapshot state
        - Local: current collection state (with user's uncommitted changes)
        - Remote: target snapshot state (what we're rolling back to)

        Args:
            snapshot_id: Snapshot ID to restore
            collection_name: Collection name (uses active if None)
            preserve_changes: Try to preserve local changes via merge (default True)
            selective_paths: Only rollback specific file paths (None = rollback all)
            confirm: Require user confirmation (default True)

        Returns:
            RollbackResult with detailed information about the rollback

        Raises:
            ValueError: Snapshot not found or user cancelled
            RuntimeError: Rollback failed

        Example:
            >>> result = version_mgr.intelligent_rollback("snapshot123")
            >>> if result.has_conflicts:
            ...     print(f"Conflicts in: {[c.file_path for c in result.conflicts]}")
            >>> print(result.summary())
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        # Get snapshot
        snapshot = self.get_snapshot(snapshot_id, collection_name)
        if not snapshot:
            return RollbackResult(
                success=False,
                snapshot_id=snapshot_id,
                error=f"Snapshot '{snapshot_id}' not found",
            )

        # Get collection path
        collection_path = self.collection_mgr.config.get_collection_path(
            collection_name
        )

        if not collection_path.exists():
            return RollbackResult(
                success=False,
                snapshot_id=snapshot_id,
                error=f"Collection '{collection_name}' not found",
            )

        # Analyze rollback safety first (if preserve_changes=True)
        safety_analysis = None
        if preserve_changes:
            console.print("[blue]Analyzing rollback safety...[/blue]")
            safety_analysis = self.analyze_rollback_safety(snapshot_id, collection_name)

            # Show analysis results
            if not safety_analysis.is_safe:
                console.print(
                    f"[yellow]Warning: {len(safety_analysis.files_with_conflicts)} potential conflicts detected[/yellow]"
                )
                for warning in safety_analysis.warnings:
                    console.print(f"  [yellow]-[/yellow] {warning}")

                if safety_analysis.files_with_conflicts:
                    console.print("  Files with conflicts:")
                    for file_path in safety_analysis.files_with_conflicts[:5]:
                        console.print(f"    - {file_path}")
                    if len(safety_analysis.files_with_conflicts) > 5:
                        console.print(
                            f"    ... and {len(safety_analysis.files_with_conflicts) - 5} more"
                        )
            elif safety_analysis.local_changes_detected > 0:
                console.print(
                    f"[green]Safe to rollback: {safety_analysis.local_changes_detected} local changes will be merged[/green]"
                )
            else:
                console.print(
                    "[green]Safe to rollback: no local changes detected[/green]"
                )

        # If preserve_changes=False, use simple rollback
        if not preserve_changes:
            console.print(
                "[blue]Performing simple rollback (no change preservation)...[/blue]"
            )
            try:
                self.rollback(snapshot_id, collection_name, confirm)
                return RollbackResult(
                    success=True,
                    snapshot_id=snapshot_id,
                    files_restored=[
                        "(all files)"
                    ],  # Simple rollback restores everything
                )
            except Exception as e:
                return RollbackResult(
                    success=False,
                    snapshot_id=snapshot_id,
                    error=str(e),
                )

        # Confirm with user
        if confirm:
            console.print(
                "[yellow]Intelligent rollback:[/yellow] Will attempt to preserve your uncommitted changes"
            )
            console.print(f"  Snapshot: {snapshot.id}")
            console.print(
                f"  Created: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            console.print(f"  Message: {snapshot.message}")
            if selective_paths:
                console.print(f"  Selective rollback: {len(selective_paths)} paths")

            if not Confirm.ask("Proceed with intelligent rollback?"):
                return RollbackResult(
                    success=False,
                    snapshot_id=snapshot_id,
                    error="Rollback cancelled by user",
                )

        # Create safety snapshot first
        console.print("[blue]Creating safety snapshot before rollback...[/blue]")
        safety_snapshot = self.auto_snapshot(
            collection_name, "Before intelligent rollback"
        )

        # Use temporary directories for three-way merge
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_base = Path(tmpdir) / "base"
            tmp_local = Path(tmpdir) / "local"
            tmp_merged = Path(tmpdir) / "merged"

            tmp_base.mkdir()
            tmp_local.mkdir()
            tmp_merged.mkdir()

            try:
                # Extract target snapshot to base (this is both base and remote in our case)
                console.print(f"[blue]Extracting snapshot {snapshot.id}...[/blue]")
                self.snapshot_mgr.restore_snapshot(snapshot, tmp_base)

                # Copy current state to local
                console.print("[blue]Analyzing current state...[/blue]")
                if selective_paths:
                    # Only copy selective paths
                    for rel_path_str in selective_paths:
                        source = collection_path / rel_path_str
                        if source.exists():
                            dest = tmp_local / rel_path_str
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            if source.is_dir():
                                shutil.copytree(source, dest)
                            else:
                                shutil.copy2(source, dest)
                else:
                    # Copy entire collection
                    shutil.copytree(collection_path, tmp_local, dirs_exist_ok=True)

                # Detect changes using DiffEngine
                console.print("[blue]Detecting local changes...[/blue]")
                diff_engine = DiffEngine()
                diff_result = diff_engine.three_way_diff(
                    base_path=tmp_base,
                    local_path=tmp_local,
                    remote_path=tmp_base,  # Remote is same as base (rolling back to snapshot)
                )

                # If no local changes, simple restore
                if not diff_result.has_conflicts and not diff_result.auto_mergeable:
                    console.print(
                        "[green]No local changes detected, performing simple restore...[/green]"
                    )
                    self.snapshot_mgr.restore_snapshot(snapshot, collection_path)
                    return RollbackResult(
                        success=True,
                        snapshot_id=snapshot_id,
                        files_restored=["(all files)"],
                        safety_snapshot_id=safety_snapshot.id,
                    )

                # Perform three-way merge
                console.print(
                    f"[blue]Merging changes: {diff_result.stats.files_changed} changed, "
                    f"{diff_result.stats.files_conflicted} conflicts...[/blue]"
                )
                merge_engine = MergeEngine()
                merge_result = merge_engine.merge(
                    base_path=tmp_base,
                    local_path=tmp_local,
                    remote_path=tmp_base,  # Remote is same as base
                    output_path=tmp_merged,
                )

                # Apply merged results to collection
                console.print("[blue]Applying merged changes...[/blue]")

                # First, restore snapshot (gets us to target state)
                self.snapshot_mgr.restore_snapshot(snapshot, collection_path)

                # Then, overlay merged changes (preserves user's local changes)
                if tmp_merged.exists():
                    for item in tmp_merged.rglob("*"):
                        if item.is_file():
                            rel_path = item.relative_to(tmp_merged)
                            dest = collection_path / rel_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, dest)

                # Build result
                result = RollbackResult(
                    success=merge_result.success,
                    snapshot_id=snapshot_id,
                    files_merged=merge_result.auto_merged,
                    conflicts=[c for c in merge_result.conflicts],
                    safety_snapshot_id=safety_snapshot.id,
                )

                # Report results
                if result.has_conflicts:
                    console.print(
                        f"[yellow]Rollback completed with {len(result.conflicts)} conflicts[/yellow]"
                    )
                    console.print("  Files with conflicts:")
                    for conflict in result.conflicts:
                        console.print(f"    - {conflict.file_path}")
                    console.print("\n  Please resolve conflicts manually.")
                else:
                    console.print(
                        f"[green]Intelligent rollback successful: {len(result.files_merged)} files merged[/green]"
                    )

                # Record audit entry
                operation_type = "selective" if selective_paths else "intelligent"
                audit_entry = RollbackAuditEntry(
                    id=f"rb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now(),
                    collection_name=collection_name,
                    source_snapshot_id=safety_snapshot.id,
                    target_snapshot_id=snapshot_id,
                    operation_type=operation_type,
                    files_restored=result.files_restored,
                    files_merged=result.files_merged,
                    conflicts_pending=[c.file_path for c in result.conflicts],
                    preserve_changes_enabled=preserve_changes,
                    selective_paths=selective_paths,
                    success=result.success,
                )
                self.audit_trail.record(audit_entry)

                return result

            except Exception as e:
                console.print(f"[red]Error during intelligent rollback:[/red] {e}")

                # Record failed audit entry
                operation_type = "selective" if selective_paths else "intelligent"
                audit_entry = RollbackAuditEntry(
                    id=f"rb_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    timestamp=datetime.now(),
                    collection_name=collection_name,
                    source_snapshot_id=safety_snapshot.id,
                    target_snapshot_id=snapshot_id,
                    operation_type=operation_type,
                    preserve_changes_enabled=preserve_changes,
                    selective_paths=selective_paths,
                    success=False,
                    error=str(e),
                )
                self.audit_trail.record(audit_entry)

                return RollbackResult(
                    success=False,
                    snapshot_id=snapshot_id,
                    safety_snapshot_id=safety_snapshot.id,
                    error=str(e),
                )

    def auto_snapshot(
        self,
        collection_name: Optional[str] = None,
        message: str = "Automatic snapshot",
    ) -> Snapshot:
        """Create automatic snapshot before destructive operations.

        This is quieter than create_snapshot() - no console output.

        Args:
            collection_name: Collection name (uses active if None)
            message: Snapshot description

        Returns:
            Created Snapshot object

        Raises:
            ValueError: Collection not found
            RuntimeError: Snapshot creation failed
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        collection_path = self.collection_mgr.config.get_collection_path(
            collection_name
        )

        if not collection_path.exists():
            raise ValueError(f"Collection '{collection_name}' not found")

        # Create snapshot quietly (no console output)
        snapshot = self.snapshot_mgr.create_snapshot(
            collection_path, collection_name, f"[auto] {message}"
        )

        return snapshot

    def cleanup_snapshots(
        self,
        collection_name: Optional[str] = None,
        keep_count: int = 10,
    ) -> List[Snapshot]:
        """Remove old snapshots.

        Args:
            collection_name: Collection name (uses active if None)
            keep_count: Number of snapshots to keep

        Returns:
            List of deleted snapshots
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        deleted = self.snapshot_mgr.cleanup_old_snapshots(collection_name, keep_count)

        if deleted:
            console.print(f"[green][/green] Cleaned up {len(deleted)} old snapshot(s)")

        return deleted

    def delete_snapshot(
        self,
        snapshot_id: str,
        collection_name: Optional[str] = None,
    ) -> None:
        """Delete specific snapshot.

        Args:
            snapshot_id: Snapshot ID to delete
            collection_name: Collection name (uses active if None)

        Raises:
            ValueError: Snapshot not found
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        snapshot = self.get_snapshot(snapshot_id, collection_name)
        if not snapshot:
            raise ValueError(f"Snapshot '{snapshot_id}' not found")

        self.snapshot_mgr.delete_snapshot(snapshot)
        console.print(f"[green][/green] Deleted snapshot {snapshot_id}")
