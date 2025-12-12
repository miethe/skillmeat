"""Import coordinator for mapping upstream artifacts to local collection.

Handles the process of importing artifacts from marketplace catalog
entries to the user's local collection.
"""

import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ImportStatus(str, Enum):
    """Status of an import operation."""

    PENDING = "pending"
    SUCCESS = "success"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    ERROR = "error"


class ConflictStrategy(str, Enum):
    """Strategy for handling import conflicts."""

    SKIP = "skip"  # Skip conflicting artifacts
    OVERWRITE = "overwrite"  # Overwrite existing
    RENAME = "rename"  # Rename with suffix


@dataclass
class ImportEntry:
    """A single entry in an import operation."""

    catalog_entry_id: str
    artifact_type: str
    name: str
    upstream_url: str
    status: ImportStatus = ImportStatus.PENDING
    error_message: Optional[str] = None
    local_path: Optional[str] = None
    conflict_with: Optional[str] = None


@dataclass
class ImportResult:
    """Result of an import operation."""

    import_id: str
    source_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    entries: List[ImportEntry] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.SUCCESS)

    @property
    def skipped_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.SKIPPED)

    @property
    def conflict_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.CONFLICT)

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.entries if e.status == ImportStatus.ERROR)

    @property
    def summary(self) -> Dict[str, int]:
        return {
            "total": len(self.entries),
            "success": self.success_count,
            "skipped": self.skipped_count,
            "conflict": self.conflict_count,
            "error": self.error_count,
        }


class ImportCoordinator:
    """Coordinates importing artifacts from catalog to local collection.

    Handles conflict detection, strategy application, and import tracking.

    Example:
        >>> coordinator = ImportCoordinator(collection_path)
        >>> result = coordinator.import_entries(catalog_entries, source_id)
        >>> print(f"Imported {result.success_count} artifacts")
    """

    def __init__(
        self,
        collection_path: Optional[Path] = None,
    ):
        """Initialize coordinator with collection path.

        Args:
            collection_path: Path to collection root (~/.skillmeat/collection)
        """
        self.collection_path = (
            collection_path or Path.home() / ".skillmeat" / "collection"
        )

    def import_entries(
        self,
        entries: List[Dict],
        source_id: str,
        strategy: ConflictStrategy = ConflictStrategy.SKIP,
    ) -> ImportResult:
        """Import catalog entries to local collection.

        Args:
            entries: List of catalog entry dicts to import
                Each should have: id, artifact_type, name, upstream_url, path
            source_id: ID of the marketplace source
            strategy: Conflict resolution strategy

        Returns:
            ImportResult with status for each entry
        """
        import_id = str(uuid.uuid4())
        # Use timezone-aware UTC datetime
        now = (
            datetime.now(timezone.utc)
            if sys.version_info >= (3, 11)
            else datetime.utcnow()
        )
        result = ImportResult(
            import_id=import_id,
            source_id=source_id,
            started_at=now,
        )

        # Get existing artifacts to detect conflicts
        existing = self._get_existing_artifacts()

        for entry_data in entries:
            entry = ImportEntry(
                catalog_entry_id=entry_data.get("id", ""),
                artifact_type=entry_data.get("artifact_type", ""),
                name=entry_data.get("name", ""),
                upstream_url=entry_data.get("upstream_url", ""),
            )

            try:
                self._process_entry(entry, existing, strategy)
            except Exception as e:
                entry.status = ImportStatus.ERROR
                entry.error_message = str(e)
                logger.error(f"Import error for {entry.name}: {e}")

            result.entries.append(entry)

        # Use timezone-aware UTC datetime
        result.completed_at = (
            datetime.now(timezone.utc)
            if sys.version_info >= (3, 11)
            else datetime.utcnow()
        )

        logger.info(
            f"Import {import_id} completed: "
            f"{result.success_count} success, {result.skipped_count} skipped, "
            f"{result.conflict_count} conflicts, {result.error_count} errors"
        )

        return result

    def _process_entry(
        self,
        entry: ImportEntry,
        existing: Dict[str, str],
        strategy: ConflictStrategy,
    ) -> None:
        """Process a single import entry."""
        # Generate local artifact key
        artifact_key = f"{entry.artifact_type}:{entry.name}"

        # Check for conflicts
        if artifact_key in existing:
            entry.conflict_with = existing[artifact_key]

            if strategy == ConflictStrategy.SKIP:
                entry.status = ImportStatus.SKIPPED
                logger.debug(
                    f"Skipping {entry.name}: conflict with {entry.conflict_with}"
                )
                return

            elif strategy == ConflictStrategy.RENAME:
                # Generate unique name
                counter = 1
                new_name = f"{entry.name}-{counter}"
                new_key = f"{entry.artifact_type}:{new_name}"
                while new_key in existing:
                    counter += 1
                    new_name = f"{entry.name}-{counter}"
                    new_key = f"{entry.artifact_type}:{new_name}"
                entry.name = new_name
                artifact_key = new_key

            # OVERWRITE: Continue with import (will replace)

        # Compute local path
        entry.local_path = self._compute_local_path(entry.artifact_type, entry.name)

        # Mark as success (actual file operations would happen here)
        # In a full implementation, this would:
        # 1. Download artifact files from upstream_url
        # 2. Write to local_path
        # 3. Update manifest
        entry.status = ImportStatus.SUCCESS
        logger.debug(f"Imported {entry.name} to {entry.local_path}")

    def _get_existing_artifacts(self) -> Dict[str, str]:
        """Get existing artifacts in collection.

        Returns:
            Dict mapping "type:name" to local path
        """
        existing: Dict[str, str] = {}

        artifacts_path = self.collection_path / "artifacts"
        if not artifacts_path.exists():
            # Try old structure (skills/, commands/, agents/ directly in collection_path)
            for type_dir_name in ["skills", "commands", "agents"]:
                type_dir = self.collection_path / type_dir_name
                if type_dir.exists() and type_dir.is_dir():
                    artifact_type = type_dir_name.rstrip("s")  # Remove trailing 's'
                    for artifact_dir in type_dir.iterdir():
                        if not artifact_dir.is_dir():
                            continue
                        name = artifact_dir.name
                        key = f"{artifact_type}:{name}"
                        existing[key] = str(artifact_dir)
            return existing

        for type_dir in artifacts_path.iterdir():
            if not type_dir.is_dir():
                continue

            artifact_type = type_dir.name.rstrip("s")  # Remove trailing 's'

            for artifact_dir in type_dir.iterdir():
                if not artifact_dir.is_dir():
                    continue

                name = artifact_dir.name
                key = f"{artifact_type}:{name}"
                existing[key] = str(artifact_dir)

        return existing

    def _compute_local_path(self, artifact_type: str, name: str) -> str:
        """Compute local path for an artifact."""
        # Normalize artifact type for directory (ensure plural)
        if not artifact_type.endswith("s"):
            type_dir = artifact_type + "s"
        else:
            type_dir = artifact_type

        # Check if using new structure (artifacts/) or old structure
        artifacts_path = self.collection_path / "artifacts"
        if artifacts_path.exists():
            return str(artifacts_path / type_dir / name)
        else:
            # Use old structure for backward compatibility
            return str(self.collection_path / type_dir / name)

    def check_conflicts(
        self,
        entries: List[Dict],
    ) -> List[Tuple[str, str, str]]:
        """Check for conflicts without importing.

        Args:
            entries: List of catalog entry dicts

        Returns:
            List of (entry_id, name, existing_path) tuples for conflicts
        """
        existing = self._get_existing_artifacts()
        conflicts = []

        for entry in entries:
            artifact_key = f"{entry.get('artifact_type', '')}:{entry.get('name', '')}"
            if artifact_key in existing:
                conflicts.append(
                    (
                        entry.get("id", ""),
                        entry.get("name", ""),
                        existing[artifact_key],
                    )
                )

        return conflicts


def import_from_catalog(
    entries: List[Dict],
    source_id: str,
    strategy: str = "skip",
    collection_path: Optional[Path] = None,
) -> ImportResult:
    """Convenience function to import catalog entries.

    Args:
        entries: Catalog entries to import
        source_id: Marketplace source ID
        strategy: Conflict strategy ("skip", "overwrite", "rename")
        collection_path: Optional collection path override

    Returns:
        ImportResult with status
    """
    strat = ConflictStrategy(strategy)
    coordinator = ImportCoordinator(collection_path)
    return coordinator.import_entries(entries, source_id, strat)


if __name__ == "__main__":
    import tempfile

    # Create temp collection
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = Path(tmpdir) / "collection"

        # Create existing artifact (old structure)
        existing_path = collection_path / "skills" / "existing-skill"
        existing_path.mkdir(parents=True)
        (existing_path / "SKILL.md").write_text("# Existing Skill")

        # Test entries
        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "new-skill",
                "upstream_url": "https://github.com/user/repo/skills/new-skill",
            },
            {
                "id": "e2",
                "artifact_type": "skill",
                "name": "existing-skill",  # Conflict!
                "upstream_url": "https://github.com/user/repo/skills/existing-skill",
            },
            {
                "id": "e3",
                "artifact_type": "command",
                "name": "my-command",
                "upstream_url": "https://github.com/user/repo/commands/my-command",
            },
        ]

        # Test skip strategy
        result = import_from_catalog(entries, "source-123", "skip", collection_path)

        print("Import Results (skip strategy):")
        print(f"  Summary: {result.summary}")
        for entry in result.entries:
            print(f"  - {entry.name}: {entry.status.value}")
            if entry.conflict_with:
                print(f"    Conflict with: {entry.conflict_with}")

        print()

        # Test rename strategy
        result2 = import_from_catalog(entries, "source-123", "rename", collection_path)

        print("Import Results (rename strategy):")
        print(f"  Summary: {result2.summary}")
        for entry in result2.entries:
            print(f"  - {entry.name}: {entry.status.value}")
            if entry.local_path:
                print(f"    Path: {entry.local_path}")

        print()

        # Test conflict checking
        coordinator = ImportCoordinator(collection_path)
        conflicts = coordinator.check_conflicts(entries)

        print(f"Conflicts found: {len(conflicts)}")
        for entry_id, name, existing_path in conflicts:
            print(f"  - {name} (ID: {entry_id}) conflicts with {existing_path}")
