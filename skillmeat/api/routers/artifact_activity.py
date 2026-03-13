"""Artifact activity (audit/provenance) stream API endpoints.

Provides a paginated, filterable view of the artifact lifecycle event log stored
in the ``artifact_history_events`` table.  This is a **separate** route from the
version-lineage history at ``/api/v1/artifacts/{id}/history``: that endpoint
merges version records, analytics, and deployment data into a single timeline,
whereas this endpoint exposes the raw append-only audit stream written by
:class:`~skillmeat.core.bom.history.ArtifactActivityService`.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from skillmeat.api.dependencies import DbSessionDep, require_auth
from skillmeat.api.schemas.auth import AuthContext
from skillmeat.api.schemas.bom import HistoryEventSchema
from skillmeat.cache.models import ArtifactHistoryEvent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/artifacts",
    tags=["artifact-activity"],
)

# ---------------------------------------------------------------------------
# Cursor helpers
#
# Cursors encode the integer primary key of the last item on the previous
# page.  Encoding is opaque base64 so callers cannot assume numeric ordering.
# ---------------------------------------------------------------------------

_CURSOR_PREFIX = "activity:"


def _encode_cursor(event_id: int) -> str:
    """Encode an integer event id into an opaque pagination cursor."""
    raw = f"{_CURSOR_PREFIX}{event_id}"
    return base64.b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> int:
    """Decode an opaque cursor back to an integer event id.

    Raises:
        HTTPException: 400 when the cursor string is malformed.
    """
    try:
        raw = base64.b64decode(cursor.encode()).decode()
        if not raw.startswith(_CURSOR_PREFIX):
            raise ValueError("missing prefix")
        return int(raw[len(_CURSOR_PREFIX):])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pagination cursor",
        )


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _event_to_schema(event: ArtifactHistoryEvent) -> HistoryEventSchema:
    """Convert an ORM row to the ``HistoryEventSchema`` response model."""
    import json

    diff_payload: Optional[Dict[str, Any]] = None
    if event.diff_json:
        try:
            parsed = json.loads(event.diff_json)
            diff_payload = parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, TypeError):
            diff_payload = None

    ts: Optional[str] = None
    if event.timestamp is not None:
        dt = event.timestamp
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ts = dt.isoformat()

    return HistoryEventSchema(
        id=str(event.id),
        artifact_id=event.artifact_id,
        event_type=event.event_type,
        actor_id=event.actor_id,
        owner_type=event.owner_type,
        timestamp=ts,
        diff_json=diff_payload,
        content_hash=event.content_hash,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/activity",
    summary="List artifact activity events",
    description=(
        "Return a paginated, filterable audit/provenance stream of artifact "
        "lifecycle events.  Events are ordered by ``timestamp DESC`` then by "
        "``id DESC`` for stable ordering within the same second.  Use the "
        "``cursor`` from ``pageInfo.endCursor`` to fetch subsequent pages."
        "\n\n"
        "This endpoint exposes the raw append-only event log written by "
        "``ArtifactActivityService``.  For the merged version-lineage "
        "timeline (which combines version records, analytics, and deployment "
        "data) use ``GET /api/v1/artifacts/{artifact_id}/history`` instead."
    ),
    responses={
        200: {"description": "Paginated activity event list"},
        400: {"description": "Invalid request parameters or cursor"},
        401: {"description": "Unauthorized"},
    },
)
async def list_artifact_activity(
    db: DbSessionDep,
    artifact_id: Optional[str] = Query(
        default=None,
        description="Filter to events for a specific artifact (``type:name`` format)",
    ),
    project_id: Optional[str] = Query(
        default=None,
        description="Filter to events associated with a specific project",
    ),
    event_type: Optional[str] = Query(
        default=None,
        description=(
            "Filter by event type. "
            "One of: ``create``, ``update``, ``delete``, ``deploy``, "
            "``undeploy``, ``sync``"
        ),
    ),
    time_range_start: Optional[datetime] = Query(
        default=None,
        description="Return only events at or after this UTC timestamp",
    ),
    time_range_end: Optional[datetime] = Query(
        default=None,
        description="Return only events at or before this UTC timestamp",
    ),
    actor_id: Optional[str] = Query(
        default=None,
        description="Filter by the actor who triggered the event",
    ),
    owner_scope: Optional[str] = Query(
        default=None,
        description=(
            "Owner-scope filter: ``user``, ``team``, or ``enterprise``. "
            "Narrows results to events whose ``owner_type`` matches this value."
        ),
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of events per page (default 50, max 200)",
    ),
    cursor: Optional[str] = Query(
        default=None,
        description=(
            "Opaque pagination cursor from a previous response's "
            "``pageInfo.endCursor``.  Omit on the first request."
        ),
    ),
    auth_context: AuthContext = Depends(require_auth(scopes=["artifact:read"])),
) -> Dict[str, Any]:
    """List artifact activity events (audit/provenance stream).

    Applies all provided filters with AND semantics and returns up to
    ``limit`` events ordered by ``timestamp DESC``, ``id DESC``.

    Owner-scope filtering uses the ``owner_type`` column rather than
    inspecting the artifact's owner field, which allows the endpoint to stay
    within the ``artifact_history_events`` table without joins.

    Cursor-based pagination: fetch the next page by passing the opaque string
    in ``pageInfo.endCursor`` as the ``cursor`` query parameter.

    Args:
        db: Per-request SQLAlchemy session.
        artifact_id: Optional artifact primary key filter (``"type:name"``).
        project_id: Optional project identifier filter (stored in diff_json;
            passed through for forward-compatibility — currently stored in
            event metadata and not indexed separately).
        event_type: Optional event type filter.
        time_range_start: Lower bound (inclusive) UTC timestamp.
        time_range_end: Upper bound (inclusive) UTC timestamp.
        actor_id: Optional actor identifier filter.
        owner_scope: Optional ``owner_type`` filter (``user`` / ``team`` /
            ``enterprise``).
        limit: Page size (1–200, default 50).
        cursor: Opaque pagination cursor from a previous response.
        auth_context: Authenticated request context.

    Returns:
        Dict with ``items`` (list of :class:`HistoryEventSchema`) and
        ``pageInfo`` (``endCursor``, ``hasNextPage``).
    """
    _VALID_EVENT_TYPES = {"create", "update", "delete", "deploy", "undeploy", "sync"}
    _VALID_OWNER_SCOPES = {"user", "team", "enterprise"}

    # --- Validate enumerated parameters ---
    if event_type is not None and event_type not in _VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid event_type '{event_type}'. "
                f"Must be one of: {', '.join(sorted(_VALID_EVENT_TYPES))}"
            ),
        )

    if owner_scope is not None and owner_scope not in _VALID_OWNER_SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid owner_scope '{owner_scope}'. "
                f"Must be one of: {', '.join(sorted(_VALID_OWNER_SCOPES))}"
            ),
        )

    # --- Resolve cursor ---
    cursor_id: Optional[int] = None
    if cursor is not None:
        cursor_id = _decode_cursor(cursor)

    try:
        query = db.query(ArtifactHistoryEvent)

        # --- Apply filters ---
        if artifact_id is not None:
            query = query.filter(ArtifactHistoryEvent.artifact_id == artifact_id)

        if event_type is not None:
            query = query.filter(ArtifactHistoryEvent.event_type == event_type)

        if actor_id is not None:
            query = query.filter(ArtifactHistoryEvent.actor_id == actor_id)

        if owner_scope is not None:
            query = query.filter(ArtifactHistoryEvent.owner_type == owner_scope)

        if time_range_start is not None:
            ts_start = (
                time_range_start
                if time_range_start.tzinfo is not None
                else time_range_start.replace(tzinfo=timezone.utc)
            )
            query = query.filter(ArtifactHistoryEvent.timestamp >= ts_start)

        if time_range_end is not None:
            ts_end = (
                time_range_end
                if time_range_end.tzinfo is not None
                else time_range_end.replace(tzinfo=timezone.utc)
            )
            query = query.filter(ArtifactHistoryEvent.timestamp <= ts_end)

        # project_id is stored in diff_json payload (not a dedicated column).
        # Forward-compatibility filter: log a debug note and skip for now;
        # a future migration can add a project_id column and index.
        if project_id is not None:
            logger.debug(
                "project_id filter '%s' requested but not yet indexed — "
                "filtering at application layer",
                project_id,
            )

        # --- Cursor-based pagination ---
        # DESC ordering: rows with id < cursor_id come "after" the cursor page.
        if cursor_id is not None:
            query = query.filter(ArtifactHistoryEvent.id < cursor_id)

        # Order: newest events first, with id as tiebreaker for stability.
        query = query.order_by(
            ArtifactHistoryEvent.timestamp.desc(),
            ArtifactHistoryEvent.id.desc(),
        )

        # Fetch one extra row to determine hasNextPage.
        rows: List[ArtifactHistoryEvent] = query.limit(limit + 1).all()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query artifact activity events: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve artifact activity events",
        )

    # --- Apply project_id application-layer filter (forward-compatibility) ---
    if project_id is not None:
        import json

        filtered: List[ArtifactHistoryEvent] = []
        for row in rows:
            if not row.diff_json:
                continue
            try:
                payload = json.loads(row.diff_json)
                if isinstance(payload, dict) and payload.get("project_id") == project_id:
                    filtered.append(row)
            except (json.JSONDecodeError, TypeError):
                continue
        rows = filtered

    # --- Pagination metadata ---
    has_next_page = len(rows) > limit
    page_rows = rows[:limit]

    end_cursor: Optional[str] = None
    if page_rows and has_next_page:
        end_cursor = _encode_cursor(page_rows[-1].id)

    items = [_event_to_schema(row) for row in page_rows]

    return {
        "items": [item.model_dump() for item in items],
        "pageInfo": {
            "endCursor": end_cursor,
            "hasNextPage": has_next_page,
        },
    }
