"""ArtifactActivityService — service layer for artifact activity / audit-log events.

This module provides ``ArtifactActivityService``, a thin orchestration layer
over :class:`~skillmeat.core.interfaces.repositories.IArtifactActivityRepository`.

Design notes
------------
* **Fire-and-forget write path**: ``record_event_fire_and_forget`` wraps the
  synchronous ``record_event`` in a FastAPI ``BackgroundTasks`` callback so
  that activity writes never block an API response.  Failures are logged as
  warnings and silently swallowed to preserve the caller's happy path.
* **No FastAPI at module level**: ``BackgroundTasks`` is imported only under
  ``TYPE_CHECKING`` so that the service can be used from CLI code without
  pulling in Starlette/FastAPI.
* **Diff computation**: ``compute_diff`` computes a compact, human-readable
  JSON diff between two artifact state dicts.  It returns ``None`` for
  identical states and a JSON string otherwise.
* The service owns no session lifecycle — callers must commit after
  ``record_event`` if they need the event persisted immediately.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from skillmeat.core.interfaces.repositories import IArtifactActivityRepository

if TYPE_CHECKING:
    from starlette.background import BackgroundTasks

    from skillmeat.cache.models import ArtifactHistoryEvent

logger = logging.getLogger(__name__)

__all__ = ["ArtifactActivityService"]


class ArtifactActivityService:
    """Service layer for artifact activity / audit-log events.

    Wraps an :class:`~skillmeat.core.interfaces.repositories.IArtifactActivityRepository`
    and adds:

    - A convenience ``record_event`` write method with sensible defaults.
    - A ``record_event_fire_and_forget`` variant for FastAPI
      :class:`~starlette.background.BackgroundTasks`.
    - A ``compute_diff`` utility for producing compact JSON diffs between
      two artifact state snapshots.
    - Delegating read methods (``list_events``, ``get_event``,
      ``count_events``, ``get_provenance_slice``) that pass arguments
      through to the underlying repository unchanged.

    Args:
        repository: Concrete implementation of
            :class:`~skillmeat.core.interfaces.repositories.IArtifactActivityRepository`.
    """

    def __init__(self, repository: IArtifactActivityRepository) -> None:
        self._repo = repository

    # ------------------------------------------------------------------
    # Primary write method
    # ------------------------------------------------------------------

    def record_event(
        self,
        artifact_id: str,
        event_type: str,
        actor_id: Optional[str] = None,
        owner_type: str = "user",
        diff_json: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> "ArtifactHistoryEvent":
        """Append a new lifecycle event and return the created row.

        Delegates directly to
        :meth:`~skillmeat.core.interfaces.repositories.IArtifactActivityRepository.create_event`.
        The caller is responsible for committing the session when
        immediate durability is needed.

        Args:
            artifact_id: Primary key of the artifact (``"type:name"`` format).
            event_type: One of ``'create'``, ``'update'``, ``'delete'``,
                ``'deploy'``, ``'undeploy'``, or ``'sync'``.
            actor_id: Opaque identifier for the triggering user or system;
                ``None`` for automated / system events.
            owner_type: Owner context string at event time (default ``"user"``).
            diff_json: JSON-serialised diff payload, or ``None``.
            content_hash: SHA-256 hex digest of artifact content, or ``None``.

        Returns:
            The newly created
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` instance
            with its ``id`` populated after flush.
        """
        return self._repo.create_event(
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=owner_type,
            diff_json=diff_json,
            content_hash=content_hash,
        )

    # ------------------------------------------------------------------
    # Fire-and-forget write method
    # ------------------------------------------------------------------

    def record_event_fire_and_forget(
        self,
        background_tasks: "BackgroundTasks",
        artifact_id: str,
        event_type: str,
        actor_id: Optional[str] = None,
        owner_type: str = "user",
        diff_json: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> None:
        """Schedule an activity event write as a background task.

        Adds a callback to *background_tasks* that calls :meth:`record_event`
        after the HTTP response has been sent.  Any exception raised inside
        the callback is caught, logged at ``WARNING`` level, and silently
        discarded so that failures in the activity log never propagate to the
        caller.

        This method returns immediately and does **not** block the caller.

        Args:
            background_tasks: FastAPI / Starlette
                :class:`~starlette.background.BackgroundTasks` instance
                provided by the dependency injection system.
            artifact_id: Primary key of the artifact (``"type:name"`` format).
            event_type: One of ``'create'``, ``'update'``, ``'delete'``,
                ``'deploy'``, ``'undeploy'``, or ``'sync'``.
            actor_id: Opaque identifier for the triggering user or system;
                ``None`` for automated / system events.
            owner_type: Owner context string at event time (default ``"user"``).
            diff_json: JSON-serialised diff payload, or ``None``.
            content_hash: SHA-256 hex digest of artifact content, or ``None``.
        """

        def _write() -> None:
            try:
                self.record_event(
                    artifact_id=artifact_id,
                    event_type=event_type,
                    actor_id=actor_id,
                    owner_type=owner_type,
                    diff_json=diff_json,
                    content_hash=content_hash,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "record_event_fire_and_forget failed for artifact_id=%r "
                    "event_type=%r: %s",
                    artifact_id,
                    event_type,
                    exc,
                    exc_info=True,
                )

        background_tasks.add_task(_write)

    # ------------------------------------------------------------------
    # Read delegates
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
    ) -> "List[ArtifactHistoryEvent]":
        """Return a filtered, paginated slice of activity events.

        Delegates to the underlying repository unchanged.  All filter
        arguments are optional and AND-ed together.

        Args:
            artifact_id: Restrict to events for this artifact primary key.
            event_type: Restrict to events of this type.
            actor_id: Restrict to events triggered by this actor.
            owner_type: Restrict to events with this owner context.
            time_range: ``(start, end)`` inclusive UTC window.
            limit: Maximum rows to return (default 100).
            offset: Rows to skip for pagination (default 0).

        Returns:
            Ordered list of
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` instances.
        """
        return self._repo.list_events(
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=owner_type,
            time_range=time_range,
            limit=limit,
            offset=offset,
        )

    def get_event(self, event_id: int) -> "Optional[ArtifactHistoryEvent]":
        """Return a single event by its integer primary key.

        Args:
            event_id: Auto-increment primary key of the event row.

        Returns:
            The matching
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` or
            ``None`` when not found.
        """
        return self._repo.get_event(event_id)

    def count_events(
        self,
        artifact_id: Optional[str] = None,
        event_type: Optional[str] = None,
        owner_type: Optional[str] = None,
    ) -> int:
        """Return the count of events matching the given filters.

        Args:
            artifact_id: Restrict count to events for this artifact.
            event_type: Restrict count to events of this type.
            owner_type: Restrict count to events with this owner context.

        Returns:
            Non-negative integer count of matching event rows.
        """
        return self._repo.count_events(
            artifact_id=artifact_id,
            event_type=event_type,
            owner_type=owner_type,
        )

    def get_provenance_slice(
        self,
        artifact_id: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> "List[ArtifactHistoryEvent]":
        """Return the ordered provenance timeline for a single artifact.

        Delegates to the underlying repository's ``list_provenance_slice``
        method.

        Args:
            artifact_id: Primary key of the artifact whose provenance is
                requested.
            since: Lower bound (inclusive) UTC timestamp; ``None`` for no
                lower bound.
            until: Upper bound (inclusive) UTC timestamp; ``None`` for no
                upper bound.

        Returns:
            A (possibly empty) list of
            :class:`~skillmeat.cache.models.ArtifactHistoryEvent` ordered
            by ``timestamp`` ascending, then ``id`` ascending.
        """
        return self._repo.list_provenance_slice(
            artifact_id=artifact_id,
            since=since,
            until=until,
        )

    # ------------------------------------------------------------------
    # Diff utility
    # ------------------------------------------------------------------

    @staticmethod
    def compute_diff(
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
    ) -> Optional[str]:
        """Compute a compact JSON diff between two artifact state snapshots.

        Compares *before_state* and *after_state* at the top-level key
        granularity and returns a JSON string describing the delta, or
        ``None`` when the states are identical.

        Output format::

            {
                "changed": {"key": {"old": <before_value>, "new": <after_value>}},
                "added":   {"key": <after_value>},
                "removed": {"key": <before_value>}
            }

        Only sections with at least one entry are included in the output.

        Args:
            before_state: Snapshot of the artifact state before the change.
            after_state: Snapshot of the artifact state after the change.

        Returns:
            Compact JSON string describing the diff, or ``None`` if the
            states are identical (no changed, added, or removed keys).
        """
        changed: Dict[str, Any] = {}
        added: Dict[str, Any] = {}
        removed: Dict[str, Any] = {}

        all_keys = set(before_state) | set(after_state)
        for key in all_keys:
            in_before = key in before_state
            in_after = key in after_state

            if in_before and in_after:
                old_val = before_state[key]
                new_val = after_state[key]
                if old_val != new_val:
                    changed[key] = {"old": old_val, "new": new_val}
            elif in_after:
                added[key] = after_state[key]
            else:
                removed[key] = before_state[key]

        if not changed and not added and not removed:
            return None

        diff: Dict[str, Any] = {}
        if changed:
            diff["changed"] = changed
        if added:
            diff["added"] = added
        if removed:
            diff["removed"] = removed

        return json.dumps(diff, separators=(",", ":"), default=str)
