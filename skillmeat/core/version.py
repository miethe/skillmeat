"""Version management and snapshot operations for SkillMeat collections."""

from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.prompt import Confirm

from skillmeat.storage.snapshot import Snapshot, SnapshotManager

console = Console()


class VersionManager:
    """Manages collection versioning and snapshots."""

    def __init__(
        self,
        collection_mgr=None,
        snapshot_mgr: Optional[SnapshotManager] = None,
    ):
        """Initialize version manager.

        Args:
            collection_mgr: CollectionManager instance (creates default if None)
            snapshot_mgr: SnapshotManager instance (creates default if None)
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
    ) -> List[Snapshot]:
        """List all snapshots for collection.

        Args:
            collection_name: Collection name (uses active if None)

        Returns:
            List of snapshots, newest first
        """
        if collection_name is None:
            collection_name = self.collection_mgr.get_active_collection_name()

        return self.snapshot_mgr.list_snapshots(collection_name)

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
        snapshots = self.list_snapshots(collection_name)
        for snapshot in snapshots:
            if snapshot.id == snapshot_id:
                return snapshot
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
        self.auto_snapshot(collection_name, "Before rollback")

        # Perform rollback
        collection_path = self.collection_mgr.config.get_collection_path(
            collection_name
        )
        console.print(f"[blue]Restoring snapshot {snapshot.id}...[/blue]")

        try:
            self.snapshot_mgr.restore_snapshot(snapshot, collection_path)
            console.print(f"[green][/green] Successfully rolled back to {snapshot.id}")
        except Exception as e:
            console.print(f"[red]Error during rollback:[/red] {e}")
            raise

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
