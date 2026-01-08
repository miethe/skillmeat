"""Snapshot management for SkillMeat collections."""

import shutil
import sys
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.filesystem import atomic_write

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

TOML_DUMPS = tomli_w.dumps


@dataclass
class Snapshot:
    """Collection snapshot metadata."""

    id: str  # timestamp-based ID
    timestamp: datetime
    message: str
    collection_name: str
    artifact_count: int
    tarball_path: Path


class SnapshotManager:
    """Manages collection snapshots."""

    SNAPSHOTS_FILENAME = "snapshots.toml"

    def __init__(self, snapshots_dir: Path):
        """Initialize snapshot manager.

        Args:
            snapshots_dir: Base directory for all snapshots (e.g., ~/.skillmeat/snapshots/)
        """
        self.snapshots_dir = snapshots_dir
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _get_collection_snapshots_dir(self, collection_name: str) -> Path:
        """Get snapshots directory for a specific collection."""
        return self.snapshots_dir / collection_name

    def _get_snapshots_metadata_file(self, collection_name: str) -> Path:
        """Get path to snapshots.toml for a collection."""
        return (
            self._get_collection_snapshots_dir(collection_name)
            / self.SNAPSHOTS_FILENAME
        )

    def _read_metadata(self, collection_name: str) -> Dict[str, Any]:
        """Read snapshots metadata from TOML."""
        metadata_file = self._get_snapshots_metadata_file(collection_name)

        if not metadata_file.exists():
            return {"snapshots": []}

        try:
            with open(metadata_file, "rb") as f:
                content = f.read()
                return TOML_LOADS(content.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse snapshots metadata: {e}")

    def _write_metadata(self, collection_name: str, data: Dict[str, Any]) -> None:
        """Write snapshots metadata to TOML."""
        metadata_file = self._get_snapshots_metadata_file(collection_name)
        metadata_file.parent.mkdir(parents=True, exist_ok=True)

        toml_content = TOML_DUMPS(data)
        atomic_write(toml_content, metadata_file)

    def create_snapshot(
        self, collection_path: Path, collection_name: str, message: str
    ) -> Snapshot:
        """Create tarball snapshot of collection.

        Args:
            collection_path: Path to collection directory
            collection_name: Name of collection
            message: Snapshot description

        Returns:
            Snapshot object

        Raises:
            FileNotFoundError: If collection doesn't exist
            IOError: If snapshot creation fails
        """
        if not collection_path.exists():
            raise FileNotFoundError(f"Collection not found: {collection_path}")

        # Create snapshot ID from timestamp (include microseconds for uniqueness)
        now = datetime.utcnow()
        snapshot_id = now.strftime("%Y%m%d-%H%M%S-%f")

        # Create collection snapshots directory
        snapshots_dir = self._get_collection_snapshots_dir(collection_name)
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Create tarball
        tarball_path = snapshots_dir / f"{snapshot_id}.tar.gz"

        try:
            with tarfile.open(tarball_path, "w:gz") as tar:
                tar.add(collection_path, arcname=collection_name)
        except Exception as e:
            # Clean up partial tarball on error
            if tarball_path.exists():
                tarball_path.unlink()
            raise IOError(f"Failed to create snapshot tarball: {e}")

        # Count artifacts (count files in type directories)
        artifact_count = 0
        for type_dir in ["skills", "commands", "agents"]:
            type_path = collection_path / type_dir
            if type_path.exists():
                artifact_count += sum(1 for _ in type_path.iterdir())

        # Create snapshot object
        snapshot = Snapshot(
            id=snapshot_id,
            timestamp=now,
            message=message,
            collection_name=collection_name,
            artifact_count=artifact_count,
            tarball_path=tarball_path,
        )

        # Update metadata
        metadata = self._read_metadata(collection_name)
        metadata["snapshots"] = metadata.get("snapshots", [])
        metadata["snapshots"].append(
            {
                "id": snapshot.id,
                "timestamp": snapshot.timestamp.isoformat(),
                "message": snapshot.message,
                "artifact_count": snapshot.artifact_count,
                "tarball_path": str(snapshot.tarball_path),
            }
        )
        self._write_metadata(collection_name, metadata)

        return snapshot

    def get_snapshot(
        self, snapshot_id: str, collection_name: Optional[str] = None
    ) -> Optional[Snapshot]:
        """Get a specific snapshot by ID.

        Args:
            snapshot_id: Snapshot ID to retrieve
            collection_name: Optional collection name (searches all if not specified)

        Returns:
            Snapshot object or None if not found
        """
        # If collection_name specified, search only that collection
        if collection_name:
            metadata = self._read_metadata(collection_name)
            snapshots_data = metadata.get("snapshots", [])

            for snapshot_data in snapshots_data:
                if snapshot_data["id"] == snapshot_id:
                    return Snapshot(
                        id=snapshot_data["id"],
                        timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
                        message=snapshot_data["message"],
                        collection_name=collection_name,
                        artifact_count=snapshot_data["artifact_count"],
                        tarball_path=Path(snapshot_data["tarball_path"]),
                    )
            return None

        # Search all collections
        for collection_dir in self.snapshots_dir.iterdir():
            if not collection_dir.is_dir():
                continue

            collection_name = collection_dir.name
            snapshot = self.get_snapshot(snapshot_id, collection_name)
            if snapshot:
                return snapshot

        return None

    def list_snapshots(
        self,
        collection_name: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Snapshot], Optional[str]]:
        """List snapshots for collection with cursor-based pagination.

        Args:
            collection_name: Name of collection
            limit: Maximum number of snapshots to return (default 50, max 100)
            cursor: Pagination cursor (snapshot ID to start after)

        Returns:
            Tuple of (snapshots, next_cursor)
            - snapshots: List of Snapshot objects, sorted newest first
            - next_cursor: ID of last snapshot if more exist, None otherwise

        Raises:
            ValueError: If limit is out of bounds or cursor is invalid
        """
        # Validate and cap limit
        if limit < 1:
            raise ValueError("limit must be at least 1")
        limit = min(limit, 100)  # Cap at 100

        # Get all snapshots
        metadata = self._read_metadata(collection_name)
        snapshots_data = metadata.get("snapshots", [])

        snapshots = []
        for snapshot_data in snapshots_data:
            snapshot = Snapshot(
                id=snapshot_data["id"],
                timestamp=datetime.fromisoformat(snapshot_data["timestamp"]),
                message=snapshot_data["message"],
                collection_name=collection_name,
                artifact_count=snapshot_data["artifact_count"],
                tarball_path=Path(snapshot_data["tarball_path"]),
            )
            snapshots.append(snapshot)

        # Sort by timestamp, newest first
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)

        # Apply cursor-based pagination
        if cursor:
            # Find the cursor position
            cursor_idx = None
            for idx, snapshot in enumerate(snapshots):
                if snapshot.id == cursor:
                    cursor_idx = idx
                    break

            if cursor_idx is None:
                raise ValueError(f"Invalid cursor: snapshot '{cursor}' not found")

            # Return items after cursor
            snapshots = snapshots[cursor_idx + 1 :]

        # Apply limit and determine next cursor
        has_more = len(snapshots) > limit
        result_snapshots = snapshots[:limit]
        next_cursor = result_snapshots[-1].id if has_more and result_snapshots else None

        return result_snapshots, next_cursor

    def restore_snapshot(self, snapshot: Snapshot, collection_path: Path) -> None:
        """Restore collection from snapshot.

        WARNING: This is a destructive operation that replaces the collection directory!

        Args:
            snapshot: Snapshot to restore
            collection_path: Target path for restored collection

        Raises:
            FileNotFoundError: If snapshot tarball doesn't exist
            IOError: If restore operation fails
        """
        if not snapshot.tarball_path.exists():
            raise FileNotFoundError(
                f"Snapshot tarball not found: {snapshot.tarball_path}"
            )

        # Remove existing collection directory if it exists
        if collection_path.exists():
            shutil.rmtree(collection_path)

        # Extract tarball to parent directory
        # (tarball contains collection_name as root, so extract to parent)
        parent_path = collection_path.parent
        parent_path.mkdir(parents=True, exist_ok=True)

        try:
            with tarfile.open(snapshot.tarball_path, "r:gz") as tar:
                tar.extractall(parent_path)

            # The tarball was created with arcname=collection_name, so it extracts to parent/collection_name
            # If collection_path.name != snapshot.collection_name, we need to rename
            extracted_path = parent_path / snapshot.collection_name
            if extracted_path != collection_path and extracted_path.exists():
                extracted_path.rename(collection_path)
        except Exception as e:
            raise IOError(f"Failed to restore snapshot: {e}")

    def delete_snapshot(self, snapshot: Snapshot) -> None:
        """Delete snapshot tarball and metadata.

        Args:
            snapshot: Snapshot to delete

        Raises:
            IOError: If deletion fails
        """
        # Delete tarball
        if snapshot.tarball_path.exists():
            snapshot.tarball_path.unlink()

        # Update metadata
        metadata = self._read_metadata(snapshot.collection_name)
        metadata["snapshots"] = [
            s for s in metadata.get("snapshots", []) if s["id"] != snapshot.id
        ]
        self._write_metadata(snapshot.collection_name, metadata)

    def cleanup_old_snapshots(
        self, collection_name: str, keep_count: int = 10
    ) -> List[Snapshot]:
        """Delete old snapshots, keeping most recent {keep_count}.

        Args:
            collection_name: Name of collection
            keep_count: Number of snapshots to keep

        Returns:
            List of deleted snapshots
        """
        # Get all snapshots by requesting with large limit to ensure we get all
        # This is acceptable for cleanup since we need to see the full list anyway
        all_snapshots = []
        cursor = None
        while True:
            snapshots, next_cursor = self.list_snapshots(
                collection_name, limit=100, cursor=cursor
            )
            all_snapshots.extend(snapshots)

            if next_cursor is None:
                break

            cursor = next_cursor

        # Snapshots are already sorted newest first
        if len(all_snapshots) <= keep_count:
            return []

        # Delete old snapshots
        snapshots_to_delete = all_snapshots[keep_count:]
        for snapshot in snapshots_to_delete:
            self.delete_snapshot(snapshot)

        return snapshots_to_delete
