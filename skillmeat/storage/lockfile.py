"""Lock file management for SkillMeat collections."""

import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from ..core.artifact import ArtifactType
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
class LockEntry:
    """Lock file entry for reproducibility."""

    name: str
    type: str  # artifact type
    upstream: Optional[str]
    resolved_sha: Optional[str]
    resolved_version: Optional[str]
    content_hash: str  # For detecting local modifications
    fetched: datetime


class LockManager:
    """Manages collection.lock files."""

    LOCK_FILENAME = "collection.lock"

    def read(self, collection_path: Path) -> Dict[Tuple[str, str], LockEntry]:
        """Read collection.lock and return dict keyed by (name, type).

        Args:
            collection_path: Path to collection directory

        Returns:
            Dictionary mapping (name, type) to LockEntry

        Raises:
            FileNotFoundError: If collection.lock doesn't exist
            ValueError: If TOML is corrupted
        """
        lock_file = collection_path / self.LOCK_FILENAME

        if not lock_file.exists():
            # Return empty dict if lock doesn't exist yet
            return {}

        try:
            with open(lock_file, "rb") as f:
                content = f.read()
                data = TOML_LOADS(content.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse collection.lock: {e}")

        lock_data = data.get("lock", {})
        entries_data = lock_data.get("entries", {})

        entries = {}
        for composite_key, entry_data in entries_data.items():
            # Parse composite key "name::type"
            name, artifact_type = composite_key.split("::", 1)

            # Parse fetched datetime
            fetched = datetime.fromisoformat(entry_data["fetched"])

            entry = LockEntry(
                name=name,
                type=artifact_type,
                upstream=entry_data.get("upstream"),
                resolved_sha=entry_data.get("resolved_sha"),
                resolved_version=entry_data.get("resolved_version"),
                content_hash=entry_data["content_hash"],
                fetched=fetched,
            )
            entries[(name, artifact_type)] = entry

        return entries

    def write(
        self, collection_path: Path, entries: Dict[Tuple[str, str], LockEntry]
    ) -> None:
        """Write lock entries to collection.lock.

        Args:
            collection_path: Path to collection directory
            entries: Dictionary mapping (name, type) to LockEntry

        Raises:
            IOError: If write operation fails
        """
        lock_file = collection_path / self.LOCK_FILENAME

        # Build TOML structure
        entries_dict = {}
        for (name, artifact_type), entry in entries.items():
            # Use composite key "name::type"
            composite_key = f"{name}::{artifact_type}"

            entry_dict = {
                "content_hash": entry.content_hash,
                "fetched": entry.fetched.isoformat(),
            }

            if entry.upstream is not None:
                entry_dict["upstream"] = entry.upstream
            if entry.resolved_sha is not None:
                entry_dict["resolved_sha"] = entry.resolved_sha
            if entry.resolved_version is not None:
                entry_dict["resolved_version"] = entry.resolved_version

            entries_dict[composite_key] = entry_dict

        data = {"lock": {"version": "1.0.0", "entries": entries_dict}}

        # Serialize and write atomically
        toml_content = TOML_DUMPS(data)
        atomic_write(toml_content, lock_file)

    def update_entry(
        self,
        collection_path: Path,
        name: str,
        artifact_type: ArtifactType,
        upstream: Optional[str],
        resolved_sha: Optional[str],
        resolved_version: Optional[str],
        content_hash: str,
    ) -> None:
        """Update single lock entry.

        Args:
            collection_path: Path to collection directory
            name: Artifact name
            artifact_type: Artifact type
            upstream: Upstream URL
            resolved_sha: Resolved commit SHA
            resolved_version: Resolved version tag
            content_hash: Content hash

        Raises:
            IOError: If write operation fails
        """
        # Read existing entries
        entries = self.read(collection_path)

        # Update entry
        entry = LockEntry(
            name=name,
            type=artifact_type.value,
            upstream=upstream,
            resolved_sha=resolved_sha,
            resolved_version=resolved_version,
            content_hash=content_hash,
            fetched=datetime.utcnow(),
        )
        entries[(name, artifact_type.value)] = entry

        # Write back
        self.write(collection_path, entries)

    def get_entry(
        self, collection_path: Path, name: str, artifact_type: ArtifactType
    ) -> Optional[LockEntry]:
        """Get lock entry by composite key.

        Args:
            collection_path: Path to collection directory
            name: Artifact name
            artifact_type: Artifact type

        Returns:
            LockEntry if found, None otherwise
        """
        entries = self.read(collection_path)
        return entries.get((name, artifact_type.value))

    def remove_entry(
        self, collection_path: Path, name: str, artifact_type: ArtifactType
    ) -> None:
        """Remove lock entry by composite key.

        Args:
            collection_path: Path to collection directory
            name: Artifact name
            artifact_type: Artifact type
        """
        entries = self.read(collection_path)
        entries.pop((name, artifact_type.value), None)
        self.write(collection_path, entries)
