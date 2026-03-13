"""Thin helper for emitting artifact activity events from mutation boundaries.

This module provides a single public function, ``emit_activity_event``, that
creates an ``ArtifactHistoryEvent`` row in the cache database.  It is designed
to be called **after** a primary mutation succeeds, and it is always wrapped in
a try/except so that any failure is logged but never propagates to the caller.

Design constraints
------------------
* **Fire-and-forget safety** — the caller's mutation must never fail because of
  an activity-recording failure.  Every code path that touches the DB is inside
  a try/except.
* **No service dependency injection** — the helper imports directly from
  ``skillmeat.cache.models`` and the standard library.  There is no DI
  container and no circular-import risk.
* **Synchronous by default** — the helper uses a regular SQLAlchemy session.
  For FastAPI contexts a ``background_tasks`` parameter is provided so the DB
  write can be deferred to after the response is sent.

Usage at call sites::

    from skillmeat.core.bom.event_emitter import emit_activity_event

    # After a successful artifact creation:
    emit_activity_event(
        session=session,
        artifact_id=artifact_id,
        event_type="create",
        actor_id=current_user_id,   # str or None for system events
        owner_type="user",           # defaults to "user" when omitted
        content_hash=artifact_hash, # optional
    )

    # With auth_context — owner_type is resolved automatically:
    emit_activity_event(
        session=session,
        artifact_id=artifact_id,
        event_type="create",
        actor_id=auth_context.user_id,
        auth_context=auth_context,  # tenant_id → "enterprise", team_id → "team"
    )

    # In a FastAPI route using BackgroundTasks (deferred, non-blocking):
    emit_activity_event(
        session=None,               # session is opened internally
        artifact_id=artifact_id,
        event_type="deploy",
        background_tasks=background_tasks,
    )

Valid ``event_type`` values: ``'create'``, ``'update'``, ``'delete'``,
``'deploy'``, ``'undeploy'``, ``'sync'``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from fastapi import BackgroundTasks
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Valid event types — must match the CHECK constraint in ArtifactHistoryEvent.
_VALID_EVENT_TYPES = frozenset({"create", "update", "delete", "deploy", "undeploy", "sync"})


def _resolve_owner_type(auth_context: object, default: str) -> str:
    """Derive the owner_type string from an auth context object.

    Checks attributes in priority order (most-specific scope wins):

    1. ``tenant_id`` present and truthy → ``"enterprise"``
    2. ``team_id`` present and truthy  → ``"team"``
    3. Otherwise                        → *default* (typically ``"user"``)

    Uses ``getattr`` with ``None`` defaults so the function works safely with
    any object shape — including plain ``MagicMock`` instances in tests.

    Args:
        auth_context: Any object that may carry ``tenant_id`` or ``team_id``
                      attributes.  ``None`` is not accepted here; callers must
                      guard against ``None`` before calling this function.
        default: Fallback owner_type string when no scope attribute is found.

    Returns:
        One of ``"enterprise"``, ``"team"``, or *default*.
    """
    if getattr(auth_context, "tenant_id", None):
        return "enterprise"
    if getattr(auth_context, "team_id", None):
        return "team"
    return default


def _write_event(
    session: "Session",
    artifact_id: str,
    event_type: str,
    actor_id: Optional[str],
    owner_type: str,
    diff_json: Optional[str],
    content_hash: Optional[str],
) -> None:
    """Insert a single ArtifactHistoryEvent row into *session*.

    The caller is responsible for committing the session.  This function only
    adds the object; it does not commit or close the session so that it remains
    compatible with both standalone sessions and per-request session patterns.

    Args:
        session: Open SQLAlchemy session to use for the insert.
        artifact_id: Artifact identifier string (e.g. ``"skill:my-skill"``).
        event_type: Lifecycle event type (one of ``_VALID_EVENT_TYPES``).
        actor_id: Opaque user/service identifier; ``None`` for system events.
        owner_type: Owner context at event time (default ``"user"``).
        diff_json: Optional JSON-serialised diff payload.
        content_hash: Optional SHA-256 content hash of the artifact.
    """
    # Import inside function to avoid circular imports at module load time.
    from skillmeat.cache.models import ArtifactHistoryEvent

    event = ArtifactHistoryEvent(
        artifact_id=artifact_id,
        event_type=event_type,
        actor_id=actor_id,
        owner_type=owner_type,
        timestamp=datetime.utcnow(),
        diff_json=diff_json,
        content_hash=content_hash,
    )
    session.add(event)
    session.commit()


def _emit_with_new_session(
    artifact_id: str,
    event_type: str,
    actor_id: Optional[str],
    owner_type: str,
    diff_json: Optional[str],
    content_hash: Optional[str],
) -> None:
    """Open a fresh session, write the event, and close the session.

    Used when the caller does not have an open session available (e.g. in
    background task contexts or synchronous non-request code).
    """
    from skillmeat.cache.models import get_session

    session = get_session()
    try:
        _write_event(
            session=session,
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=owner_type,
            diff_json=diff_json,
            content_hash=content_hash,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def emit_activity_event(
    *,
    artifact_id: str,
    event_type: str,
    session: Optional["Session"] = None,
    actor_id: Optional[str] = None,
    owner_type: str = "user",
    auth_context: Optional[object] = None,
    diff_json: Optional[str] = None,
    content_hash: Optional[str] = None,
    background_tasks: Optional["BackgroundTasks"] = None,
) -> None:
    """Record an artifact lifecycle event in the activity history table.

    This function is designed to be called after a primary mutation succeeds.
    All failures are caught and logged as warnings; the exception is never
    re-raised so the caller's mutation path remains unaffected.

    When *background_tasks* is provided the DB write is enqueued as a FastAPI
    background task (runs after the response is sent).  When *session* is
    provided it is used directly and the caller is responsible for its
    lifecycle.  When neither is provided a new session is opened, used, and
    closed inside this call.

    When *auth_context* is provided the ``owner_type`` is resolved from it
    automatically, overriding the *owner_type* parameter:

    * ``auth_context.tenant_id`` truthy → ``"enterprise"``
    * ``auth_context.team_id`` truthy   → ``"team"``
    * Otherwise                         → the *owner_type* parameter value

    This avoids a hard dependency on ``OwnershipResolver`` and keeps this
    module self-contained.

    Args:
        artifact_id: Artifact identifier string (e.g. ``"skill:my-skill"``).
        event_type: One of ``'create'``, ``'update'``, ``'delete'``,
                    ``'deploy'``, ``'undeploy'``, ``'sync'``.
        session: Optional open SQLAlchemy session.  When supplied the event is
                 written synchronously into this session and committed.
        actor_id: Opaque user/system identifier; ``None`` for automated events.
        owner_type: Owner context at event time.  Defaults to ``"user"``.
                    Ignored when *auth_context* resolves a more-specific scope.
        auth_context: Optional auth context object.  When provided the
                      ``owner_type`` is resolved from its ``tenant_id`` and
                      ``team_id`` attributes via ``getattr`` (safe for any
                      object shape).
        diff_json: Optional JSON string describing what changed.
        content_hash: Optional SHA-256 hash of the artifact content at event
                      time.
        background_tasks: Optional FastAPI ``BackgroundTasks`` instance.  When
                          provided the DB write is deferred to a background task
                          so the HTTP response is not delayed.

    Examples:
        After a successful create in a router with a per-request session::

            emit_activity_event(
                session=db_session,
                artifact_id=artifact_id,
                event_type="create",
                actor_id=auth_context.user_id,
                auth_context=auth_context,
            )

        After a deploy using BackgroundTasks (non-blocking)::

            emit_activity_event(
                artifact_id=artifact_id,
                event_type="deploy",
                actor_id=auth_context.user_id,
                auth_context=auth_context,
                background_tasks=background_tasks,
            )
    """
    # Resolve owner_type from auth_context when provided.
    if auth_context is not None:
        owner_type = _resolve_owner_type(auth_context, default=owner_type)
    if event_type not in _VALID_EVENT_TYPES:
        logger.warning(
            "emit_activity_event: ignoring unknown event_type=%r for artifact_id=%r",
            event_type,
            artifact_id,
        )
        return

    if background_tasks is not None:
        # Defer the DB write to after the response is sent.
        background_tasks.add_task(
            _background_emit,
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=owner_type,
            diff_json=diff_json,
            content_hash=content_hash,
        )
        return

    if session is not None:
        # Write synchronously into the caller-supplied session.
        try:
            _write_event(
                session=session,
                artifact_id=artifact_id,
                event_type=event_type,
                actor_id=actor_id,
                owner_type=owner_type,
                diff_json=diff_json,
                content_hash=content_hash,
            )
        except Exception as exc:
            logger.warning(
                "emit_activity_event: failed to record %r event for artifact %r "
                "(using caller session): %s",
                event_type,
                artifact_id,
                exc,
                exc_info=True,
            )
        return

    # No session and no background_tasks — open a fresh session.
    try:
        _emit_with_new_session(
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=owner_type,
            diff_json=diff_json,
            content_hash=content_hash,
        )
    except Exception as exc:
        logger.warning(
            "emit_activity_event: failed to record %r event for artifact %r "
            "(standalone session): %s",
            event_type,
            artifact_id,
            exc,
            exc_info=True,
        )


def _background_emit(
    *,
    artifact_id: str,
    event_type: str,
    actor_id: Optional[str],
    owner_type: str,
    diff_json: Optional[str],
    content_hash: Optional[str],
) -> None:
    """Internal helper used as a FastAPI BackgroundTasks target.

    Opens its own session so it runs safely outside the request-scoped
    session that closed when the response was sent.
    """
    try:
        _emit_with_new_session(
            artifact_id=artifact_id,
            event_type=event_type,
            actor_id=actor_id,
            owner_type=owner_type,
            diff_json=diff_json,
            content_hash=content_hash,
        )
    except Exception as exc:
        logger.warning(
            "emit_activity_event (background): failed to record %r event for artifact %r: %s",
            event_type,
            artifact_id,
            exc,
            exc_info=True,
        )
