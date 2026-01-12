"""Collection data model and manager for SkillMeat."""

import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .artifact import Artifact, ArtifactType
from .mcp.metadata import MCPServerMetadata


@dataclass
class Collection:
    """Personal collection of Claude artifacts."""

    name: str
    version: str  # collection format version (e.g., "1.0.0")
    artifacts: List[Artifact]
    created: datetime
    updated: datetime
    mcp_servers: List[MCPServerMetadata] = field(default_factory=list)

    def __post_init__(self):
        """Validate collection configuration."""
        if not self.name:
            raise ValueError("Collection name cannot be empty")

    def find_artifact(
        self, name: str, artifact_type: Optional[ArtifactType] = None
    ) -> Optional[Artifact]:
        """Find artifact by name, optionally filtered by type.

        Args:
            name: The artifact name to search for
            artifact_type: Optional type filter

        Returns:
            The artifact if found, None otherwise

        Raises:
            ValueError: If name is ambiguous (multiple artifacts with same name but different types)
        """
        matches = []
        for artifact in self.artifacts:
            if artifact.name == name:
                if artifact_type is None:
                    matches.append(artifact)
                elif artifact.type == artifact_type:
                    return artifact

        if not matches:
            return None
        elif len(matches) == 1:
            return matches[0]
        else:
            # Multiple artifacts with same name but different types
            types = ", ".join([a.type.value for a in matches])
            raise ValueError(
                f"Ambiguous artifact name '{name}' matches multiple types: {types}. "
                f"Please specify type explicitly."
            )

    def add_artifact(self, artifact: Artifact) -> None:
        """Add artifact to collection (check for duplicates).

        Args:
            artifact: The artifact to add

        Raises:
            ValueError: If artifact with same composite key already exists
        """
        # Check composite key uniqueness
        for existing in self.artifacts:
            if existing.composite_key() == artifact.composite_key():
                raise ValueError(
                    f"Artifact '{artifact.name}' of type '{artifact.type.value}' "
                    f"already exists in collection."
                )
        self.artifacts.append(artifact)

    def remove_artifact(self, name: str, artifact_type: ArtifactType) -> bool:
        """Remove artifact by composite key.

        Args:
            name: Artifact name
            artifact_type: Artifact type

        Returns:
            True if removed, False if not found
        """
        for i, artifact in enumerate(self.artifacts):
            if artifact.name == name and artifact.type == artifact_type:
                self.artifacts.pop(i)
                return True
        return False

    def find_mcp_server(self, name: str) -> Optional[MCPServerMetadata]:
        """Find MCP server by name.

        Args:
            name: MCP server name

        Returns:
            MCPServerMetadata if found, None otherwise
        """
        for server in self.mcp_servers:
            if server.name == name:
                return server
        return None

    def add_mcp_server(self, server: MCPServerMetadata) -> None:
        """Add MCP server to collection.

        Args:
            server: MCPServerMetadata to add

        Raises:
            ValueError: If MCP server with same name already exists
        """
        existing = self.find_mcp_server(server.name)
        if existing is not None:
            raise ValueError(f"MCP server '{server.name}' already exists in collection")
        self.mcp_servers.append(server)

    def remove_mcp_server(self, name: str) -> bool:
        """Remove MCP server by name.

        Args:
            name: MCP server name

        Returns:
            True if removed, False if not found
        """
        for i, server in enumerate(self.mcp_servers):
            if server.name == name:
                self.mcp_servers.pop(i)
                return True
        return False

    def list_mcp_servers(self) -> List[MCPServerMetadata]:
        """List all MCP servers in the collection.

        Returns:
            List of MCPServerMetadata objects
        """
        return self.mcp_servers.copy()

    def get_mcp_server(self, name: str) -> Optional[MCPServerMetadata]:
        """Get MCP server by name (alias for find_mcp_server).

        Args:
            name: MCP server name

        Returns:
            MCPServerMetadata if found, None otherwise
        """
        return self.find_mcp_server(name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization."""
        result = {
            "collection": {
                "name": self.name,
                "version": self.version,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
            },
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }

        # Add MCP servers if present
        if self.mcp_servers:
            result["mcp_servers"] = [server.to_dict() for server in self.mcp_servers]

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Collection":
        """Create from dictionary (TOML deserialization)."""
        collection_data = data.get("collection", {})
        artifacts_data = data.get("artifacts", [])
        mcp_servers_data = data.get("mcp_servers", [])

        # Parse datetimes
        created = datetime.fromisoformat(collection_data["created"])
        updated = datetime.fromisoformat(collection_data["updated"])

        # Parse artifacts
        artifacts = [
            Artifact.from_dict(artifact_data) for artifact_data in artifacts_data
        ]

        # Parse MCP servers
        mcp_servers = [
            MCPServerMetadata.from_dict(server_data) for server_data in mcp_servers_data
        ]

        return cls(
            name=collection_data["name"],
            version=collection_data["version"],
            created=created,
            updated=updated,
            artifacts=artifacts,
            mcp_servers=mcp_servers,
        )


class CollectionManager:
    """Manages collection lifecycle and operations."""

    def __init__(self, config=None):
        """Initialize collection manager.

        Args:
            config: ConfigManager instance (creates default if None)
        """
        if config is None:
            from skillmeat.config import ConfigManager

            config = ConfigManager()
        self.config = config

        from skillmeat.storage.manifest import ManifestManager
        from skillmeat.storage.lockfile import LockManager

        self.manifest_mgr = ManifestManager()
        self.lock_mgr = LockManager()

    def init(self, name: str = "default") -> Collection:
        """Initialize new collection.

        Args:
            name: Collection name

        Returns:
            Newly created Collection object

        Raises:
            ValueError: Collection already exists
        """
        collection_path = self.config.get_collection_path(name)

        if collection_path.exists():
            raise ValueError(f"Collection '{name}' already exists at {collection_path}")

        # Create collection directory structure
        collection_path.mkdir(parents=True, exist_ok=True)
        (collection_path / "skills").mkdir(exist_ok=True)
        (collection_path / "commands").mkdir(exist_ok=True)
        (collection_path / "agents").mkdir(exist_ok=True)

        # Create empty collection
        collection = self.manifest_mgr.create_empty(collection_path, name)

        # Create empty lock file
        self.lock_mgr.write(collection_path, {})

        # Set as active if it's the default
        if name == "default":
            self.config.set_active_collection(name)

        return collection

    def list_collections(self) -> List[str]:
        """List all collection names.

        Returns:
            List of collection names
        """
        collections_dir = self.config.get_collections_dir()
        if not collections_dir.exists():
            return []

        return [
            d.name
            for d in collections_dir.iterdir()
            if d.is_dir() and (d / "collection.toml").exists()
        ]

    def get_active_collection_name(self) -> str:
        """Get currently active collection name.

        Returns:
            Active collection name
        """
        return self.config.get_active_collection()

    def switch_collection(self, name: str) -> None:
        """Switch active collection.

        Args:
            name: Collection name to switch to

        Raises:
            ValueError: Collection doesn't exist
        """
        if name not in self.list_collections():
            raise ValueError(f"Collection '{name}' does not exist")

        self.config.set_active_collection(name)

    def load_collection(self, name: Optional[str] = None) -> Collection:
        """Load collection from disk.

        Args:
            name: Collection name (uses active if None)

        Returns:
            Collection object

        Raises:
            ValueError: Collection not found
        """
        name = name or self.get_active_collection_name()
        collection_path = self.config.get_collection_path(name)

        if not collection_path.exists():
            raise ValueError(f"Collection '{name}' not found at {collection_path}")

        return self.manifest_mgr.read(collection_path)

    def save_collection(self, collection: Collection) -> None:
        """Save collection to disk.

        Args:
            collection: Collection to save
        """
        collection_path = self.config.get_collection_path(collection.name)
        collection.updated = datetime.utcnow()
        self.manifest_mgr.write(collection_path, collection)

    def delete_collection(self, name: str, confirm: bool = True) -> None:
        """Delete collection.

        Args:
            name: Collection name
            confirm: Require confirmation (safety check)

        Raises:
            ValueError: Collection not found or is active collection
        """
        if name == self.get_active_collection_name():
            raise ValueError(
                "Cannot delete active collection. Switch to another first."
            )

        collection_path = self.config.get_collection_path(name)
        if not collection_path.exists():
            raise ValueError(f"Collection '{name}' not found")

        # Safety check
        if confirm:
            raise ValueError("Use confirm=False to actually delete")

        # Delete collection directory
        shutil.rmtree(collection_path)

    def artifact_in_collection(
        self,
        name: str,
        artifact_type: str,
        source_link: Optional[str] = None,
        content_hash: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> tuple:
        """Check if artifact exists in collection.

        Performs membership check with priority-based matching:
        1. Exact source_link match (highest priority) -> "exact"
        2. Content hash match -> "hash"
        3. Name + type match (lowest priority) -> "name_type"
        4. No match -> "none"

        This method is optimized for performance when checking multiple
        artifacts. For bulk operations, consider caching the collection.

        Args:
            name: Artifact name to check (case-insensitive comparison)
            artifact_type: Artifact type (skill, command, agent, etc.)
            source_link: Optional source URL for exact matching
            content_hash: Optional content hash for hash matching
            collection_name: Collection name (uses active if None)

        Returns:
            Tuple of (in_collection: bool, matched_artifact_id: Optional[str], match_type: str)
            - in_collection: True if artifact found in collection
            - matched_artifact_id: ID of matched artifact (format: "type:name") or None
            - match_type: "exact" | "hash" | "name_type" | "none"

        Examples:
            >>> mgr = CollectionManager()
            >>> # Check by source link (exact match)
            >>> in_coll, matched_id, match_type = mgr.artifact_in_collection(
            ...     "canvas-design", "skill",
            ...     source_link="anthropics/skills/canvas-design"
            ... )
            >>> print(f"In collection: {in_coll}, Match: {match_type}")
            In collection: True, Match: exact

            >>> # Check by name only (name_type match)
            >>> in_coll, matched_id, match_type = mgr.artifact_in_collection(
            ...     "my-local-skill", "skill"
            ... )
            >>> print(f"In collection: {in_coll}, Match: {match_type}")
            In collection: True, Match: name_type
        """
        try:
            collection = self.load_collection(collection_name)
        except ValueError:
            # Collection doesn't exist - artifact not in collection
            return (False, None, "none")

        # Normalize inputs for case-insensitive comparison
        name_lower = name.lower()
        artifact_type_lower = artifact_type.lower()

        # Priority 1: Exact source_link match
        if source_link:
            source_link_normalized = source_link.strip().lower()
            for artifact in collection.artifacts:
                if artifact.upstream:
                    # Normalize stored upstream for comparison
                    upstream_normalized = artifact.upstream.strip().lower()
                    if upstream_normalized == source_link_normalized:
                        matched_id = f"{artifact.type.value}:{artifact.name}"
                        return (True, matched_id, "exact")

        # Priority 2: Content hash match (if hash provided)
        if content_hash:
            # Need to check lock file for content hashes
            try:
                collection_path = self.config.get_collection_path(
                    collection_name or self.get_active_collection_name()
                )
                lock_entries = self.lock_mgr.read(collection_path)

                for (entry_name, entry_type), lock_entry in lock_entries.items():
                    if lock_entry.content_hash == content_hash:
                        matched_id = f"{entry_type}:{entry_name}"
                        return (True, matched_id, "hash")
            except Exception:
                # If lock file read fails, continue with name+type matching
                pass

        # Priority 3: Name + type match (case-insensitive)
        for artifact in collection.artifacts:
            artifact_name_lower = artifact.name.lower()
            artifact_type_value_lower = artifact.type.value.lower()

            if (
                artifact_name_lower == name_lower
                and artifact_type_value_lower == artifact_type_lower
            ):
                matched_id = f"{artifact.type.value}:{artifact.name}"
                return (True, matched_id, "name_type")

        # No match found
        return (False, None, "none")

    def get_collection_membership_index(
        self, collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build an indexed structure for fast membership lookups.

        Creates lookup dictionaries for source_link, content_hash, and name+type
        to enable O(1) membership checks when processing many artifacts.

        Args:
            collection_name: Collection name (uses active if None)

        Returns:
            Dictionary with:
            - by_source: Dict mapping normalized source_link -> artifact_id
            - by_hash: Dict mapping content_hash -> artifact_id
            - by_name_type: Dict mapping (name_lower, type_lower) -> artifact_id
            - artifacts: List of (artifact_id, artifact) tuples

        Example:
            >>> mgr = CollectionManager()
            >>> index = mgr.get_collection_membership_index()
            >>> source = "anthropics/skills/canvas-design".lower()
            >>> if source in index["by_source"]:
            ...     print(f"Found: {index['by_source'][source]}")
        """
        result: Dict[str, Any] = {
            "by_source": {},
            "by_hash": {},
            "by_name_type": {},
            "artifacts": [],
        }

        try:
            collection = self.load_collection(collection_name)
        except ValueError:
            return result

        collection_path = self.config.get_collection_path(
            collection_name or self.get_active_collection_name()
        )

        # Build source link index
        for artifact in collection.artifacts:
            artifact_id = f"{artifact.type.value}:{artifact.name}"
            result["artifacts"].append((artifact_id, artifact))

            # Index by source
            if artifact.upstream:
                source_normalized = artifact.upstream.strip().lower()
                result["by_source"][source_normalized] = artifact_id

            # Index by name+type (case-insensitive)
            name_type_key = (artifact.name.lower(), artifact.type.value.lower())
            result["by_name_type"][name_type_key] = artifact_id

        # Build hash index from lock file
        try:
            lock_entries = self.lock_mgr.read(collection_path)
            for (entry_name, entry_type), lock_entry in lock_entries.items():
                if lock_entry.content_hash:
                    artifact_id = f"{entry_type}:{entry_name}"
                    result["by_hash"][lock_entry.content_hash] = artifact_id
        except Exception:
            # If lock file read fails, hash index remains empty
            pass

        return result

    def check_membership_batch(
        self,
        artifacts: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
    ) -> List[tuple]:
        """Check membership for multiple artifacts efficiently.

        Uses indexed lookups for O(n) total time complexity instead of
        O(n*m) when checking n artifacts against m collection entries.

        Args:
            artifacts: List of dicts with keys:
                - name: str (required)
                - artifact_type: str (required)
                - source_link: Optional[str]
                - content_hash: Optional[str]
            collection_name: Collection name (uses active if None)

        Returns:
            List of tuples (in_collection, matched_artifact_id, match_type)
            in same order as input artifacts.

        Performance:
            Target: <500ms for 100+ artifacts
        """
        # Build index once
        index = self.get_collection_membership_index(collection_name)
        results = []

        for artifact_data in artifacts:
            name = artifact_data.get("name", "")
            artifact_type = artifact_data.get("artifact_type", "")
            source_link = artifact_data.get("source_link")
            content_hash = artifact_data.get("content_hash")

            # Priority 1: Exact source_link match
            if source_link:
                source_normalized = source_link.strip().lower()
                if source_normalized in index["by_source"]:
                    matched_id = index["by_source"][source_normalized]
                    results.append((True, matched_id, "exact"))
                    continue

            # Priority 2: Content hash match
            if content_hash and content_hash in index["by_hash"]:
                matched_id = index["by_hash"][content_hash]
                results.append((True, matched_id, "hash"))
                continue

            # Priority 3: Name + type match
            name_type_key = (name.lower(), artifact_type.lower())
            if name_type_key in index["by_name_type"]:
                matched_id = index["by_name_type"][name_type_key]
                results.append((True, matched_id, "name_type"))
                continue

            # No match
            results.append((False, None, "none"))

        return results

    def link_duplicate(
        self,
        discovered_path: str,
        collection_artifact_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """Create link between discovered artifact and collection artifact.

        Adds discovered_path to the artifact's duplicate_links list in the
        collection manifest. This relationship tracks that the discovered
        artifact is a duplicate/copy of the collection artifact.

        This method is idempotent - calling it multiple times with the same
        arguments will not create duplicate entries.

        Args:
            discovered_path: Full filesystem path to the discovered artifact
            collection_artifact_id: ID of collection artifact (format: type:name)
            collection_name: Collection name (uses active if None)

        Returns:
            True if link was created or already exists, False if artifact not found

        Raises:
            ValueError: If collection_artifact_id format is invalid

        Example:
            >>> mgr = CollectionManager()
            >>> success = mgr.link_duplicate(
            ...     "/Users/me/.claude/skills/my-canvas",
            ...     "skill:canvas-design"
            ... )
            >>> print(f"Link created: {success}")
            Link created: True
        """
        import logging

        logger = logging.getLogger(__name__)

        # Parse artifact ID (format: type:name)
        if ":" not in collection_artifact_id:
            raise ValueError(
                f"Invalid artifact ID format '{collection_artifact_id}'. "
                "Expected 'type:name' format."
            )

        artifact_type, artifact_name = collection_artifact_id.split(":", 1)

        try:
            collection = self.load_collection(collection_name)
        except ValueError as e:
            logger.warning(f"Failed to load collection for duplicate linking: {e}")
            return False

        # Find the artifact in collection
        target_artifact = None
        for artifact in collection.artifacts:
            if (
                artifact.name.lower() == artifact_name.lower()
                and artifact.type.value.lower() == artifact_type.lower()
            ):
                target_artifact = artifact
                break

        if target_artifact is None:
            logger.warning(
                f"Artifact '{collection_artifact_id}' not found in collection "
                f"for duplicate linking"
            )
            return False

        # Initialize duplicate_links if not present (stored in metadata.extra)
        if "duplicate_links" not in target_artifact.metadata.extra:
            target_artifact.metadata.extra["duplicate_links"] = []

        # Check for existing link (idempotent)
        existing_links = target_artifact.metadata.extra["duplicate_links"]
        if discovered_path in existing_links:
            logger.debug(
                f"Duplicate link already exists: {discovered_path} -> "
                f"{collection_artifact_id}"
            )
            return True

        # Add the new link
        existing_links.append(discovered_path)
        target_artifact.metadata.extra["duplicate_links"] = existing_links

        # Save collection with updated artifact
        self.save_collection(collection)

        logger.info(
            f"Created duplicate link: {discovered_path} -> {collection_artifact_id}"
        )
        return True

    def get_duplicate_links(
        self,
        collection_artifact_id: str,
        collection_name: Optional[str] = None,
    ) -> List[str]:
        """Get all duplicate links for a collection artifact.

        Args:
            collection_artifact_id: ID of collection artifact (format: type:name)
            collection_name: Collection name (uses active if None)

        Returns:
            List of discovered paths linked to this artifact

        Raises:
            ValueError: If collection_artifact_id format is invalid
        """
        # Parse artifact ID (format: type:name)
        if ":" not in collection_artifact_id:
            raise ValueError(
                f"Invalid artifact ID format '{collection_artifact_id}'. "
                "Expected 'type:name' format."
            )

        artifact_type, artifact_name = collection_artifact_id.split(":", 1)

        try:
            collection = self.load_collection(collection_name)
        except ValueError:
            return []

        # Find the artifact in collection
        for artifact in collection.artifacts:
            if (
                artifact.name.lower() == artifact_name.lower()
                and artifact.type.value.lower() == artifact_type.lower()
            ):
                return artifact.metadata.extra.get("duplicate_links", [])

        return []

    def remove_duplicate_link(
        self,
        discovered_path: str,
        collection_artifact_id: str,
        collection_name: Optional[str] = None,
    ) -> bool:
        """Remove a duplicate link from a collection artifact.

        Args:
            discovered_path: Full filesystem path to remove
            collection_artifact_id: ID of collection artifact (format: type:name)
            collection_name: Collection name (uses active if None)

        Returns:
            True if link was removed, False if not found
        """
        import logging

        logger = logging.getLogger(__name__)

        # Parse artifact ID
        if ":" not in collection_artifact_id:
            raise ValueError(
                f"Invalid artifact ID format '{collection_artifact_id}'. "
                "Expected 'type:name' format."
            )

        artifact_type, artifact_name = collection_artifact_id.split(":", 1)

        try:
            collection = self.load_collection(collection_name)
        except ValueError:
            return False

        # Find the artifact
        for artifact in collection.artifacts:
            if (
                artifact.name.lower() == artifact_name.lower()
                and artifact.type.value.lower() == artifact_type.lower()
            ):
                links = artifact.metadata.extra.get("duplicate_links", [])
                if discovered_path in links:
                    links.remove(discovered_path)
                    artifact.metadata.extra["duplicate_links"] = links
                    self.save_collection(collection)
                    logger.info(
                        f"Removed duplicate link: {discovered_path} -> "
                        f"{collection_artifact_id}"
                    )
                    return True

        return False
