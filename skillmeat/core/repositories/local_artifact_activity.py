"""SQLAlchemy-backed implementation of IArtifactActivityRepository.

Stores :class:`~skillmeat.cache.models.ArtifactHistoryEvent` rows in the
local SQLite cache database.  Events are immutable once written — this
repository intentionally exposes no ``update`` or ``delete`` methods.

Design notes
------------
* Uses SQLAlchemy 1.x ``session.query()`` style to match the other local
  repositories in this package (``local_artifact.py``,
  ``local_deployment.py``, etc.).  Do **not** convert to 2.x ``select()``
  style — the local/enterprise divergence is intentional.  See
  ``skillmeat/cache/CLAUDE.md``.
* The caller (API router or service) owns the session lifecycle and is
  responsible for calling ``session.commit()`` after mutations.  This
  repository only calls ``session.flush()`` to obtain generated primary keys.
* ``owner_type`` defaults to :attr:`~skillmeat.cache.auth_types.OwnerType.user`
  when the caller passes an empty string.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from skillmeat.cache.auth_types import OwnerType
from skillmeat.cache.models import ArtifactHistoryEvent
from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.repositories import IArtifactActivityRepository

logger = logging.getLogger(__name__)

__all__ = ["LocalArtifactActivityRepository"]


class LocalArtifactActivityRepository(IArtifactActivityRepository):
    """``IArtifactActivityRepository`` backed by the local SQLite cache DB.

    Args:
        session: A live :class:`sqlalchemy.orm.Session` bound to the local
            SQLite database.  The session lifecycle is owned by the caller.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Mutations (insert-only)
    # ------------------------------------------------------------------

    def create_event(
        self,
        artifact_id: str,
        event_type: str,
        actor_id: Optional[str],
        owner_type: str,
        diff_json: Optional[str],
        content_hash: Optional[str],
        ctx: Optional[RequestContext] = None,
    ) -> ArtifactHistoryEvent:
        """Append a new lifecycle event to the activity log.

        Args:
            artifact_id: Primary key of the artifact (``"type:name"`` format).
            event_type: One of ``'create'``, ``'update'``, ``'delete'``,
                ``'deploy'``, ``'undeploy'``, or ``'sync'``.
            actor_id: Opaque identifier for the user or system that triggered
                the event; ``None`` for automated/system events.
            owner_type: Owner context string at the time of the event.
                Defaults to :attr:`~skillmeat.cache.auth_types.OwnerType.user`
                when empty.
            diff_json: JSON-serialised diff payload, or ``None``.
            content_hash: SHA-256 hex digest of artifact content, or ``None``.
            ctx: Optional per-request metadata (unused in this backend).

        Returns:
            The newly flushed
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` instance
            with ``id`` populated.
        """
        resolved_owner_type = owner_type or OwnerType.user.value
        event = ArtifactHistoryEvent(
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=resolved_owner_type,
            diff_json=diff_json,
            content_hash=content_hash,
        )
        self.session.add(event)
        self.session.flush()
        logger.debug(
            "create_event: id=%s artifact_id=%s event_type=%s",
            event.id,
            artifact_id,
            event_type,
        )
        return event

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_events(
        self,
        artifact_id: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        owner_type: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 100,
        offset: int = 0,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactHistoryEvent]:
        """Return a filtered, paginated slice of activity events.

        All filter arguments are optional and combinable (AND-ed together).

        Args:
            artifact_id: Restrict to events for this artifact primary key.
            event_type: Restrict to events of this type.
            actor_id: Restrict to events triggered by this actor.
            owner_type: Restrict to events with this owner context.
            time_range: ``(start, end)`` inclusive window in UTC.
            limit: Maximum number of rows to return (default 100).
            offset: Number of rows to skip for pagination (default 0).
            ctx: Optional per-request metadata (unused in this backend).

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` ordered
            by ``timestamp`` ascending, then ``id`` ascending.
        """
        query = self.session.query(ArtifactHistoryEvent)

        if artifact_id is not None:
            query = query.filter(ArtifactHistoryEvent.artifact_id == artifact_id)
        if event_type is not None:
            query = query.filter(ArtifactHistoryEvent.event_type == event_type)
        if actor_id is not None:
            query = query.filter(ArtifactHistoryEvent.actor_id == actor_id)
        if owner_type is not None:
            query = query.filter(ArtifactHistoryEvent.owner_type == owner_type)
        if time_range is not None:
            start, end = time_range
            query = query.filter(ArtifactHistoryEvent.timestamp >= start)
            query = query.filter(ArtifactHistoryEvent.timestamp <= end)

        query = (
            query.order_by(
                ArtifactHistoryEvent.timestamp.asc(),
                ArtifactHistoryEvent.id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return query.all()

    def get_event(
        self,
        event_id: int,
        ctx: Optional[RequestContext] = None,
    ) -> Optional[ArtifactHistoryEvent]:
        """Return a single event by its integer primary key.

        Args:
            event_id: Auto-increment primary key of the event row.
            ctx: Optional per-request metadata (unused in this backend).

        Returns:
            The matching :class:`~skillmeat.cache.models.ArtifactHistoryEvent`
            when found, ``None`` otherwise.
        """
        return (
            self.session.query(ArtifactHistoryEvent)
            .filter(ArtifactHistoryEvent.id == event_id)
            .first()
        )

    def count_events(
        self,
        artifact_id: Optional[str] = None,
        event_type: Optional[str] = None,
        owner_type: Optional[str] = None,
        ctx: Optional[RequestContext] = None,
    ) -> int:
        """Return the count of events matching the given filters.

        Args:
            artifact_id: Restrict count to events for this artifact.
            event_type: Restrict count to events of this type.
            owner_type: Restrict count to events with this owner context.
            ctx: Optional per-request metadata (unused in this backend).

        Returns:
            Non-negative integer count of matching event rows.
        """
        query = self.session.query(ArtifactHistoryEvent)

        if artifact_id is not None:
            query = query.filter(ArtifactHistoryEvent.artifact_id == artifact_id)
        if event_type is not None:
            query = query.filter(ArtifactHistoryEvent.event_type == event_type)
        if owner_type is not None:
            query = query.filter(ArtifactHistoryEvent.owner_type == owner_type)

        return query.count()

    def list_provenance_slice(
        self,
        artifact_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        ctx: Optional[RequestContext] = None,
    ) -> List[ArtifactHistoryEvent]:
        """Return the ordered provenance timeline for a single artifact.

        Args:
            artifact_id: Primary key of the artifact whose provenance is
                requested.
            since: Lower bound (inclusive) of the time window in UTC.
                When ``None``, no lower bound is applied.
            until: Upper bound (inclusive) of the time window in UTC.
                When ``None``, no upper bound is applied.
            ctx: Optional per-request metadata (unused in this backend).

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` ordered
            by ``timestamp`` ascending, then ``id`` ascending.
        """
        query = self.session.query(ArtifactHistoryEvent).filter(
            ArtifactHistoryEvent.artifact_id == artifact_id
        )

        if since is not None:
            query = query.filter(ArtifactHistoryEvent.timestamp >= since)
        if until is not None:
            query = query.filter(ArtifactHistoryEvent.timestamp <= until)

        return query.order_by(
            ArtifactHistoryEvent.timestamp.asc(),
            ArtifactHistoryEvent.id.asc(),
        ).all()
