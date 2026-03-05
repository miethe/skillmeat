"""Local DB-backed implementation of IGroupRepository.

Delegates all persistence to the SQLAlchemy cache layer (``skillmeat.cache.models``).
Every method opens a session, performs its work, commits (for mutations), and closes
the session in a ``try/finally`` block — the same lifecycle pattern used by
``LocalArtifactRepository`` and the original ``groups.py`` router.

Design notes
------------
* Group IDs are hex UUID strings in the DB, but the ``IGroupRepository`` interface
  takes ``int``-typed ``group_id`` parameters.  The interface predates the string-key
  migration; we coerce via ``str(group_id)`` on the way in so existing callers that
  still pass integers continue to work.
* Manifest sync side-effects (``ManifestSyncService.sync_groups``) are preserved as
  best-effort calls wrapped in ``try/except`` — failures are logged as warnings and
  never propagate to the caller.
* All mutations are transactional: a rollback is issued on any unexpected error before
  re-raising as a ``RuntimeError`` or ``KeyError``/``ValueError``.
* No HTTPException is raised here — that is the router's responsibility.  The
  repository raises plain Python exceptions so it can be used outside an HTTP context.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import GroupArtifactDTO, GroupDTO
from skillmeat.core.interfaces.repositories import IGroupRepository

# ---------------------------------------------------------------------------
# Optional DB imports — graceful degradation when the cache module is absent
# (e.g. minimal test environments that skip DB setup).
# ---------------------------------------------------------------------------
try:
    from skillmeat.cache.models import (
        Artifact as _DBArtifact,
        Collection as _DBCollection,
        CollectionArtifact as _DBCollectionArtifact,
        Group as _DBGroup,
        GroupArtifact as _DBGroupArtifact,
        get_session as _get_db_session,
    )

    _db_available = True
except ImportError:  # pragma: no cover
    _get_db_session = None  # type: ignore[assignment]
    _DBArtifact = None  # type: ignore[assignment]
    _DBCollection = None  # type: ignore[assignment]
    _DBCollectionArtifact = None  # type: ignore[assignment]
    _DBGroup = None  # type: ignore[assignment]
    _DBGroupArtifact = None  # type: ignore[assignment]
    _db_available = False

logger = logging.getLogger(__name__)

__all__ = ["LocalGroupRepository"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _group_to_dto(group: Any, artifact_count: int = 0) -> GroupDTO:
    """Convert an ORM ``Group`` instance to a :class:`GroupDTO`.

    Args:
        group: SQLAlchemy ``Group`` ORM object.
        artifact_count: Pre-computed member count to avoid an extra query.

    Returns:
        Immutable :class:`GroupDTO`.
    """
    created = group.created_at
    updated = group.updated_at
    return GroupDTO(
        id=str(group.id),
        name=group.name,
        collection_id=str(group.collection_id),
        description=group.description,
        position=int(group.position or 0),
        artifact_count=artifact_count,
        created_at=created.isoformat() if created and hasattr(created, "isoformat") else (created if isinstance(created, str) else None),
        updated_at=updated.isoformat() if updated and hasattr(updated, "isoformat") else (updated if isinstance(updated, str) else None),
    )


def _group_artifact_to_dto(ga: Any) -> GroupArtifactDTO:
    """Convert an ORM ``GroupArtifact`` instance to a :class:`GroupArtifactDTO`.

    Args:
        ga: SQLAlchemy ``GroupArtifact`` ORM object.

    Returns:
        Immutable :class:`GroupArtifactDTO`.
    """
    added = ga.added_at
    return GroupArtifactDTO(
        group_id=str(ga.group_id),
        artifact_uuid=ga.artifact_uuid,
        position=int(ga.position or 0),
        added_at=added.isoformat() if added and hasattr(added, "isoformat") else (added if isinstance(added, str) else None),
    )


def _sync_groups_manifest(session: Any, collection_id: str) -> None:
    """Best-effort manifest sync — failure is logged but not propagated.

    Args:
        session: Active SQLAlchemy session (must still be open).
        collection_id: Collection whose group manifest to refresh.
    """
    try:
        from skillmeat.core.services.manifest_sync_service import ManifestSyncService

        ManifestSyncService().sync_groups(session, collection_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to sync groups to manifest: %s", exc)


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class LocalGroupRepository(IGroupRepository):
    """Local DB-backed implementation of :class:`IGroupRepository`.

    All operations delegate to the SQLAlchemy ORM via the singleton session
    returned by ``skillmeat.cache.models.get_session()``.
    """

    # ------------------------------------------------------------------
    # Single-item lookup
    # ------------------------------------------------------------------

    def get_with_artifacts(
        self,
        group_id: int,
        ctx: RequestContext | None = None,
    ) -> GroupDTO | None:
        """Return a group by ID with its current artifact count.

        Args:
            group_id: Integer (or string) primary key of the group.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            :class:`GroupDTO` when the group exists, ``None`` otherwise.
        """
        if not _db_available:
            logger.warning("DB not available — get_with_artifacts returning None")
            return None

        session = _get_db_session()
        try:
            group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            if not group:
                return None

            artifact_count = (
                session.query(_DBGroupArtifact)
                .filter_by(group_id=str(group_id))
                .count()
            )
            logger.debug("get_with_artifacts: group=%s count=%d", group_id, artifact_count)
            return _group_to_dto(group, artifact_count=artifact_count)
        except Exception as exc:
            logger.error("get_with_artifacts failed for group %s: %s", group_id, exc, exc_info=True)
            raise RuntimeError(f"Failed to fetch group {group_id}") from exc
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Collection queries
    # ------------------------------------------------------------------

    def list(
        self,
        collection_id: str,
        filters: dict[str, Any] | None = None,
        ctx: RequestContext | None = None,
    ) -> list[GroupDTO]:
        """Return all groups in *collection_id* ordered by position.

        Args:
            collection_id: Collection unique identifier.
            filters: Optional filter map.  Recognised keys:

                - ``"search"`` (``str``) — case-insensitive name substring filter.
                - ``"artifact_id"`` (``str``) — return only groups that contain
                  the artifact with this ``"type:name"`` id.

            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            List of :class:`GroupDTO` ordered by ``position`` ascending.

        Raises:
            KeyError: If *collection_id* does not exist.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            logger.warning("DB not available — list returning []")
            return []

        session = _get_db_session()
        try:
            collection = session.query(_DBCollection).filter_by(id=collection_id).first()
            if not collection:
                raise KeyError(f"Collection '{collection_id}' not found")

            query = session.query(_DBGroup).filter_by(collection_id=collection_id)

            flt = filters or {}
            search = flt.get("search")
            artifact_id = flt.get("artifact_id")

            if search:
                query = query.filter(_DBGroup.name.ilike(f"%{search}%"))

            if artifact_id:
                # Join through Artifact table to resolve type:name → uuid
                query = (
                    query.join(_DBGroupArtifact)
                    .join(
                        _DBArtifact,
                        _DBArtifact.uuid == _DBGroupArtifact.artifact_uuid,
                    )
                    .filter(_DBArtifact.id == artifact_id)
                )

            query = query.order_by(_DBGroup.position)
            groups = query.all()

            result: list[GroupDTO] = []
            for group in groups:
                count = (
                    session.query(_DBGroupArtifact)
                    .filter_by(group_id=group.id)
                    .count()
                )
                result.append(_group_to_dto(group, artifact_count=count))

            logger.debug(
                "list: collection=%s search=%r artifact_id=%r → %d groups",
                collection_id,
                search,
                artifact_id,
                len(result),
            )
            return result
        except KeyError:
            raise
        except Exception as exc:
            logger.error("list groups failed for collection %s: %s", collection_id, exc, exc_info=True)
            raise RuntimeError(f"Failed to list groups in collection {collection_id}") from exc
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Mutations — groups
    # ------------------------------------------------------------------

    def create(
        self,
        name: str,
        collection_id: str,
        description: str | None = None,
        position: int | None = None,
        ctx: RequestContext | None = None,
    ) -> GroupDTO:
        """Create a new group in *collection_id*.

        Args:
            name: Human-readable group name (must be unique within the collection).
            collection_id: Owning collection identifier.
            description: Optional group description.
            position: Explicit display position.  When ``None`` the group is
                appended at the end (``max_position + 1``).
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            The created :class:`GroupDTO`.

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If a group named *name* already exists in the collection.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            # Verify collection exists
            collection = session.query(_DBCollection).filter_by(id=collection_id).first()
            if not collection:
                raise KeyError(f"Collection '{collection_id}' not found")

            # Enforce unique name constraint within collection
            existing = (
                session.query(_DBGroup)
                .filter_by(collection_id=collection_id, name=name)
                .first()
            )
            if existing:
                raise ValueError(
                    f"Group '{name}' already exists in collection '{collection_id}'"
                )

            # Resolve position — append to end when not specified
            if position is None:
                max_pos = (
                    session.query(_DBGroup.position)
                    .filter_by(collection_id=collection_id)
                    .order_by(_DBGroup.position.desc())
                    .first()
                )
                position = (max_pos[0] + 1) if max_pos else 0

            group = _DBGroup(
                id=uuid.uuid4().hex,
                collection_id=collection_id,
                name=name,
                description=description,
                position=position,
            )
            session.add(group)
            session.commit()
            session.refresh(group)

            logger.info(
                "Created group '%s' (%s) in collection %s at position %d",
                name,
                group.id,
                collection_id,
                position,
            )

            _sync_groups_manifest(session, collection_id)
            return _group_to_dto(group, artifact_count=0)

        except (KeyError, ValueError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("create group failed: %s", exc, exc_info=True)
            raise RuntimeError("Failed to create group") from exc
        finally:
            session.close()

    def update(
        self,
        group_id: int,
        updates: dict[str, Any],
        ctx: RequestContext | None = None,
    ) -> GroupDTO:
        """Apply a partial update to an existing group's metadata.

        Args:
            group_id: Integer (or string) primary key of the group.
            updates: Map of field names to new values.  Recognised keys:
                ``name``, ``description``, ``tags``, ``color``, ``icon``,
                ``position``.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            The updated :class:`GroupDTO`.

        Raises:
            KeyError: If no group with *group_id* exists.
            ValueError: If the new name already exists in the same collection.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            if not group:
                raise KeyError(f"Group '{group_id}' not found")

            # Check name uniqueness when renaming
            new_name = updates.get("name")
            if new_name and new_name != group.name:
                conflict = (
                    session.query(_DBGroup)
                    .filter_by(collection_id=group.collection_id, name=new_name)
                    .first()
                )
                if conflict:
                    raise ValueError(
                        f"Group '{new_name}' already exists in collection '{group.collection_id}'"
                    )

            # Apply updates
            if "name" in updates and updates["name"] is not None:
                group.name = updates["name"]
            if "description" in updates:
                group.description = updates["description"]
            if "tags" in updates and updates["tags"] is not None:
                group.tags_json = json.dumps(updates["tags"])
            if "color" in updates and updates["color"] is not None:
                group.color = updates["color"]
            if "icon" in updates and updates["icon"] is not None:
                group.icon = updates["icon"]
            if "position" in updates and updates["position"] is not None:
                group.position = updates["position"]

            collection_id = group.collection_id
            session.commit()
            session.refresh(group)

            logger.info("Updated group %s", group_id)

            _sync_groups_manifest(session, collection_id)

            artifact_count = (
                session.query(_DBGroupArtifact)
                .filter_by(group_id=group.id)
                .count()
            )
            return _group_to_dto(group, artifact_count=artifact_count)

        except (KeyError, ValueError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("update group %s failed: %s", group_id, exc, exc_info=True)
            raise RuntimeError(f"Failed to update group {group_id}") from exc
        finally:
            session.close()

    def delete(
        self,
        group_id: int,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a group and all its artifact membership records.

        Args:
            group_id: Integer (or string) primary key of the group.
            ctx: Optional per-request metadata (unused by this backend).

        Raises:
            KeyError: If no group with *group_id* exists.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            if not group:
                raise KeyError(f"Group '{group_id}' not found")

            collection_id = group.collection_id
            session.delete(group)
            session.commit()

            logger.info("Deleted group %s", group_id)
            _sync_groups_manifest(session, collection_id)

        except KeyError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("delete group %s failed: %s", group_id, exc, exc_info=True)
            raise RuntimeError(f"Failed to delete group {group_id}") from exc
        finally:
            session.close()

    def copy_to_collection(
        self,
        group_id: int,
        target_collection_id: str,
        ctx: RequestContext | None = None,
    ) -> GroupDTO:
        """Duplicate a group (and its artifact memberships) into another collection.

        The new group name gets a ``" (Copy)"`` suffix.  If the target collection does
        not already have an artifact that belongs to the source group, the artifact's
        ``CollectionArtifact`` row is created so the copy is self-consistent.

        Args:
            group_id: Integer (or string) primary key of the source group.
            target_collection_id: Identifier of the destination collection.
            ctx: Optional per-request metadata (unused by this backend).

        Returns:
            The newly created :class:`GroupDTO` in the target collection.

        Raises:
            KeyError: If *group_id* or *target_collection_id* does not exist.
            ValueError: If a group with the derived copy name already exists in
                the target collection.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            source_group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            if not source_group:
                raise KeyError(f"Group '{group_id}' not found")

            target_collection = (
                session.query(_DBCollection)
                .filter_by(id=target_collection_id)
                .first()
            )
            if not target_collection:
                raise KeyError(f"Target collection '{target_collection_id}' not found")

            new_name = f"{source_group.name} (Copy)"
            if (
                session.query(_DBGroup)
                .filter_by(collection_id=target_collection_id, name=new_name)
                .first()
            ):
                raise ValueError(
                    f"Group '{new_name}' already exists in target collection '{target_collection_id}'"
                )

            # Determine append position in target collection
            max_pos = (
                session.query(_DBGroup.position)
                .filter_by(collection_id=target_collection_id)
                .order_by(_DBGroup.position.desc())
                .first()
            )
            new_position = (max_pos[0] + 1) if max_pos else 0

            new_group = _DBGroup(
                id=uuid.uuid4().hex,
                collection_id=target_collection_id,
                name=new_name,
                description=source_group.description,
                tags_json=source_group.tags_json or "[]",
                color=source_group.color,
                icon=source_group.icon,
                position=new_position,
            )
            session.add(new_group)
            session.flush()  # Materialise the new group ID before adding members

            # Copy artifact memberships
            source_members = (
                session.query(_DBGroupArtifact)
                .filter_by(group_id=str(group_id))
                .order_by(_DBGroupArtifact.position)
                .all()
            )

            # Pre-load existing artifact UUIDs in the target collection to avoid dupes
            existing_uuids: set[str] = {
                ca.artifact_uuid
                for ca in session.query(_DBCollectionArtifact)
                .filter_by(collection_id=target_collection_id)
                .all()
            }

            for source_ga in source_members:
                # Add artifact to target collection when not already present
                if source_ga.artifact_uuid not in existing_uuids:
                    session.add(
                        _DBCollectionArtifact(
                            collection_id=target_collection_id,
                            artifact_uuid=source_ga.artifact_uuid,
                            added_at=source_ga.added_at,
                        )
                    )
                    existing_uuids.add(source_ga.artifact_uuid)

                session.add(
                    _DBGroupArtifact(
                        group_id=new_group.id,
                        artifact_uuid=source_ga.artifact_uuid,
                        position=source_ga.position,
                    )
                )

            source_collection_id = source_group.collection_id
            session.commit()
            session.refresh(new_group)

            logger.info(
                "Copied group '%s' (%s) → '%s' (%s) in collection %s with %d artifacts",
                source_group.name,
                group_id,
                new_name,
                new_group.id,
                target_collection_id,
                len(source_members),
            )

            _sync_groups_manifest(session, target_collection_id)
            if source_collection_id != target_collection_id:
                _sync_groups_manifest(session, source_collection_id)

            return _group_to_dto(new_group, artifact_count=len(source_members))

        except (KeyError, ValueError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("copy_to_collection failed: %s", exc, exc_info=True)
            raise RuntimeError("Failed to copy group") from exc
        finally:
            session.close()

    def reorder_groups(
        self,
        collection_id: str,
        ordered_ids: list[int],
        ctx: RequestContext | None = None,
    ) -> None:
        """Bulk-set ``position`` for all groups in *collection_id*.

        The ``position`` of each group is set to its zero-based index in
        *ordered_ids*.

        Args:
            collection_id: Collection unique identifier.
            ordered_ids: Complete ordered list of group primary keys.
            ctx: Optional per-request metadata (unused by this backend).

        Raises:
            KeyError: If *collection_id* does not exist.
            ValueError: If *ordered_ids* does not include all groups in the
                collection.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            if not session.query(_DBCollection).filter_by(id=collection_id).first():
                raise KeyError(f"Collection '{collection_id}' not found")

            str_ids = [str(gid) for gid in ordered_ids]
            groups = (
                session.query(_DBGroup)
                .filter(_DBGroup.id.in_(str_ids))
                .all()
            )

            found = {g.id for g in groups}
            missing = set(str_ids) - found
            if missing:
                raise ValueError(
                    f"Groups not found in collection: {', '.join(sorted(missing))}"
                )

            # All groups in this collection must be covered
            total_in_collection = (
                session.query(_DBGroup)
                .filter_by(collection_id=collection_id)
                .count()
            )
            if len(ordered_ids) != total_in_collection:
                raise ValueError(
                    f"ordered_ids must contain all {total_in_collection} groups "
                    f"in collection '{collection_id}' (got {len(ordered_ids)})"
                )

            position_map = {sid: idx for idx, sid in enumerate(str_ids)}
            for group in groups:
                group.position = position_map[group.id]

            session.commit()
            logger.info("Reordered %d groups in collection %s", len(groups), collection_id)
            _sync_groups_manifest(session, collection_id)

        except (KeyError, ValueError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("reorder_groups failed: %s", exc, exc_info=True)
            raise RuntimeError("Failed to reorder groups") from exc
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Mutations — artifact membership
    # ------------------------------------------------------------------

    def add_artifacts(
        self,
        group_id: int,
        artifact_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> None:
        """Add one or more artifacts (by UUID) to a group.

        Artifacts already present in the group are silently skipped.  New
        artifacts are appended after existing members.

        Args:
            group_id: Integer (or string) primary key of the target group.
            artifact_uuids: List of stable artifact UUIDs to add.
            ctx: Optional per-request metadata (unused by this backend).

        Raises:
            KeyError: If *group_id* does not exist.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            if not group:
                raise KeyError(f"Group '{group_id}' not found")

            existing_uuids: set[str] = {
                ga.artifact_uuid
                for ga in session.query(_DBGroupArtifact)
                .filter_by(group_id=str(group_id))
                .all()
            }

            new_uuids = [u for u in artifact_uuids if u not in existing_uuids]
            if not new_uuids:
                logger.debug("add_artifacts: no new artifacts for group %s", group_id)
                return

            # Determine append start position
            max_pos = (
                session.query(_DBGroupArtifact.position)
                .filter_by(group_id=str(group_id))
                .order_by(_DBGroupArtifact.position.desc())
                .first()
            )
            start = (max_pos[0] + 1) if max_pos else 0

            for i, art_uuid in enumerate(new_uuids):
                session.add(
                    _DBGroupArtifact(
                        group_id=str(group_id),
                        artifact_uuid=art_uuid,
                        position=start + i,
                    )
                )

            session.commit()
            logger.info("Added %d artifacts to group %s", len(new_uuids), group_id)
            _sync_groups_manifest(session, group.collection_id)

        except KeyError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("add_artifacts to group %s failed: %s", group_id, exc, exc_info=True)
            raise RuntimeError(f"Failed to add artifacts to group {group_id}") from exc
        finally:
            session.close()

    def remove_artifact(
        self,
        group_id: int,
        artifact_uuid: str,
        ctx: RequestContext | None = None,
    ) -> None:
        """Remove a single artifact from a group and compact positions.

        Args:
            group_id: Integer (or string) primary key of the group.
            artifact_uuid: Stable artifact UUID to remove.
            ctx: Optional per-request metadata (unused by this backend).

        Raises:
            KeyError: If *group_id* does not exist or *artifact_uuid* is not
                a member of the group.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            group_artifact = (
                session.query(_DBGroupArtifact)
                .filter_by(group_id=str(group_id), artifact_uuid=artifact_uuid)
                .first()
            )
            if not group_artifact:
                raise KeyError(
                    f"Artifact '{artifact_uuid}' not found in group '{group_id}'"
                )

            removed_position = group_artifact.position
            group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            collection_id = group.collection_id if group else None

            session.delete(group_artifact)

            # Compact positions: shift down all members after the removed position
            session.query(_DBGroupArtifact).filter(
                _DBGroupArtifact.group_id == str(group_id),
                _DBGroupArtifact.position > removed_position,
            ).update({_DBGroupArtifact.position: _DBGroupArtifact.position - 1})

            session.commit()
            logger.info("Removed artifact %s from group %s", artifact_uuid, group_id)

            if collection_id:
                _sync_groups_manifest(session, collection_id)

        except KeyError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error(
                "remove_artifact %s from group %s failed: %s",
                artifact_uuid,
                group_id,
                exc,
                exc_info=True,
            )
            raise RuntimeError(f"Failed to remove artifact from group {group_id}") from exc
        finally:
            session.close()

    def update_artifact_position(
        self,
        group_id: int,
        artifact_uuid: str,
        position: int,
        ctx: RequestContext | None = None,
    ) -> None:
        """Update the display position of a single artifact within a group.

        Shifts other artifacts to fill the gap or make room, preserving
        a gapless zero-based ordering.

        Args:
            group_id: Integer (or string) primary key of the group.
            artifact_uuid: Stable artifact UUID whose position to update.
            position: New zero-based display position.
            ctx: Optional per-request metadata (unused by this backend).

        Raises:
            KeyError: If *group_id* does not exist or *artifact_uuid* is not
                a member of the group.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            group_artifact = (
                session.query(_DBGroupArtifact)
                .filter_by(group_id=str(group_id), artifact_uuid=artifact_uuid)
                .first()
            )
            if not group_artifact:
                raise KeyError(
                    f"Artifact '{artifact_uuid}' not found in group '{group_id}'"
                )

            old_position = group_artifact.position
            new_position = position

            if old_position != new_position:
                if new_position > old_position:
                    # Moving toward the end: shift up the items between old+1..new
                    session.query(_DBGroupArtifact).filter(
                        _DBGroupArtifact.group_id == str(group_id),
                        _DBGroupArtifact.position > old_position,
                        _DBGroupArtifact.position <= new_position,
                    ).update(
                        {_DBGroupArtifact.position: _DBGroupArtifact.position - 1}
                    )
                else:
                    # Moving toward the front: shift down the items between new..old-1
                    session.query(_DBGroupArtifact).filter(
                        _DBGroupArtifact.group_id == str(group_id),
                        _DBGroupArtifact.position >= new_position,
                        _DBGroupArtifact.position < old_position,
                    ).update(
                        {_DBGroupArtifact.position: _DBGroupArtifact.position + 1}
                    )

                group_artifact.position = new_position
                session.commit()
                session.refresh(group_artifact)

                logger.info(
                    "Updated artifact %s position in group %s: %d → %d",
                    artifact_uuid,
                    group_id,
                    old_position,
                    new_position,
                )

                group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
                if group:
                    _sync_groups_manifest(session, group.collection_id)

        except KeyError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error(
                "update_artifact_position %s in group %s failed: %s",
                artifact_uuid,
                group_id,
                exc,
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to update artifact position in group {group_id}"
            ) from exc
        finally:
            session.close()

    def reorder_artifacts(
        self,
        group_id: int,
        ordered_uuids: list[str],
        ctx: RequestContext | None = None,
    ) -> None:
        """Bulk-set positions for all artifacts in a group.

        The ``position`` of each membership record is set to the artifact's
        zero-based index in *ordered_uuids*.

        Args:
            group_id: Integer (or string) primary key of the group.
            ordered_uuids: Complete ordered list of artifact UUIDs.  Must
                include every current member of the group.
            ctx: Optional per-request metadata (unused by this backend).

        Raises:
            KeyError: If *group_id* does not exist.
            ValueError: If *ordered_uuids* does not cover all current members.
            RuntimeError: On unexpected database errors.
        """
        if not _db_available:
            raise RuntimeError("DB not available")

        session = _get_db_session()
        try:
            group = session.query(_DBGroup).filter_by(id=str(group_id)).first()
            if not group:
                raise KeyError(f"Group '{group_id}' not found")

            group_artifacts = (
                session.query(_DBGroupArtifact)
                .filter(
                    _DBGroupArtifact.group_id == str(group_id),
                    _DBGroupArtifact.artifact_uuid.in_(ordered_uuids),
                )
                .all()
            )

            found_uuids = {ga.artifact_uuid for ga in group_artifacts}
            missing = set(ordered_uuids) - found_uuids
            if missing:
                raise ValueError(
                    f"Artifacts not found in group {group_id}: {', '.join(sorted(missing))}"
                )

            position_map = {art_uuid: idx for idx, art_uuid in enumerate(ordered_uuids)}
            for ga in group_artifacts:
                new_pos = position_map.get(ga.artifact_uuid)
                if new_pos is not None:
                    ga.position = new_pos

            session.commit()
            logger.info(
                "Reordered %d artifacts in group %s", len(group_artifacts), group_id
            )
            _sync_groups_manifest(session, group.collection_id)

        except (KeyError, ValueError):
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            logger.error("reorder_artifacts in group %s failed: %s", group_id, exc, exc_info=True)
            raise RuntimeError(f"Failed to reorder artifacts in group {group_id}") from exc
        finally:
            session.close()
