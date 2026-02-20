"""Write-through service: syncs DB state back to collection.toml.

This service reads group and tag state from the DB cache and writes a full
snapshot into ``collection.toml``.  The DB is authoritative at runtime; the
TOML file is a persistent backup that survives cache rebuilds.

Design decisions:
- **Full snapshot on every write** — no incremental patches, no drift.
- **Failures are non-fatal** — write-through errors are logged but never
  propagate to the caller.  The API request that triggered the mutation
  still succeeds even if the TOML write fails.
- **Thread safety** — delegated to ``CollectionManager`` (RLock + atomic_write).
"""

import logging
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ManifestSyncService:
    """Write-through service: syncs DB state back to collection.toml."""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_collection_path(
        self,
        session: Session,
        collection_id: str,
    ) -> Optional[Path]:
        """Return the filesystem path for a collection given its DB ID.

        The DB ``Collection.name`` field maps 1-to-1 with the directory name
        used by ``ConfigManager.get_collection_path(name)``.

        Args:
            session: Active SQLAlchemy session.
            collection_id: Primary key of the collection row.

        Returns:
            Resolved ``Path`` or ``None`` if the collection row is missing.
        """
        # Lazy import to avoid circular dependencies at module load time.
        from skillmeat.cache.models import Collection as DBCollection
        from skillmeat.config import ConfigManager

        db_collection = (
            session.query(DBCollection).filter_by(id=collection_id).first()
        )
        if db_collection is None:
            logger.warning(
                f"manifest_sync: collection '{collection_id}' not found in DB; "
                "skipping TOML write"
            )
            return None

        config = ConfigManager()
        return config.get_collection_path(db_collection.name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_groups(self, session: Session, collection_id: str) -> None:
        """Read all groups for a collection from DB and write them to collection.toml.

        Performs a full snapshot replacement of the ``groups`` section in
        ``collection.toml``.  Member names are resolved by joining
        ``group_artifacts`` → ``artifacts`` to obtain the canonical
        ``type:name`` identifier stored as ``Artifact.id``.

        Args:
            session: Active SQLAlchemy session (read-only; no commit performed).
            collection_id: Primary key of the collection whose groups to sync.
        """
        try:
            self._sync_groups_inner(session, collection_id)
        except Exception as exc:
            logger.error(
                f"manifest_sync: failed to sync groups for collection "
                f"'{collection_id}': {exc}",
                exc_info=True,
            )

    def _sync_groups_inner(self, session: Session, collection_id: str) -> None:
        from skillmeat.cache.models import Artifact, Group, GroupArtifact
        from skillmeat.core.collection import GroupDefinition
        from skillmeat.core.collection import CollectionManager

        collection_path = self._resolve_collection_path(session, collection_id)
        if collection_path is None:
            return

        if not (collection_path / "collection.toml").exists():
            logger.debug(
                f"manifest_sync: collection.toml missing at {collection_path}; "
                "skipping group sync"
            )
            return

        # Query all groups ordered by position.
        groups: List[Group] = (
            session.query(Group)
            .filter_by(collection_id=collection_id)
            .order_by(Group.position)
            .all()
        )

        group_definitions: List[GroupDefinition] = []
        for group in groups:
            # Resolve member artifact IDs (type:name strings) via join.
            rows = (
                session.query(Artifact.id)
                .join(
                    GroupArtifact,
                    GroupArtifact.artifact_uuid == Artifact.uuid,
                )
                .filter(GroupArtifact.group_id == group.id)
                .order_by(GroupArtifact.position)
                .all()
            )
            member_ids: List[str] = [row[0] for row in rows if row[0] is not None]

            group_definitions.append(
                GroupDefinition(
                    name=group.name,
                    description=group.description or "",
                    color=group.color or "",
                    icon=group.icon or "",
                    position=group.position,
                    members=member_ids,
                )
            )

        # Load → patch → save via CollectionManager (handles RLock + atomic write).
        collection_mgr = CollectionManager()
        collection = collection_mgr.manifest_mgr.read(collection_path)
        collection.groups = group_definitions
        collection_mgr.manifest_mgr.write(collection_path, collection)

        logger.info(
            f"manifest_sync: wrote {len(group_definitions)} group(s) to "
            f"{collection_path / 'collection.toml'}"
        )

    def sync_tag_definitions(self, session: Session, collection_id: str) -> None:
        """Read all tags from DB and write their definitions to collection.toml.

        Performs a full snapshot replacement of the ``tag_definitions`` section
        in ``collection.toml``.  Tags are workspace-scoped (not per-collection
        in the DB), so all Tag rows are written regardless of which collection
        triggered the sync.

        Args:
            session: Active SQLAlchemy session (read-only; no commit performed).
            collection_id: Primary key of the collection whose TOML to update.
        """
        try:
            self._sync_tag_definitions_inner(session, collection_id)
        except Exception as exc:
            logger.error(
                f"manifest_sync: failed to sync tag definitions for collection "
                f"'{collection_id}': {exc}",
                exc_info=True,
            )

    def _sync_tag_definitions_inner(
        self, session: Session, collection_id: str
    ) -> None:
        from skillmeat.cache.models import Tag
        from skillmeat.core.collection import TagDefinition
        from skillmeat.core.collection import CollectionManager

        collection_path = self._resolve_collection_path(session, collection_id)
        if collection_path is None:
            return

        if not (collection_path / "collection.toml").exists():
            logger.debug(
                f"manifest_sync: collection.toml missing at {collection_path}; "
                "skipping tag definition sync"
            )
            return

        # Query all tags ordered by name for deterministic output.
        tags: List[Tag] = session.query(Tag).order_by(Tag.name).all()

        tag_definitions: List[TagDefinition] = [
            TagDefinition(
                name=tag.name,
                slug=tag.slug,
                color=tag.color or "",
                # The Tag model has no description column; default to empty string.
                description="",
            )
            for tag in tags
        ]

        collection_mgr = CollectionManager()
        collection = collection_mgr.manifest_mgr.read(collection_path)
        collection.tag_definitions = tag_definitions
        collection_mgr.manifest_mgr.write(collection_path, collection)

        logger.info(
            f"manifest_sync: wrote {len(tag_definitions)} tag definition(s) to "
            f"{collection_path / 'collection.toml'}"
        )
