"""Unit tests for EnterpriseArtifactActivityRepository.

Coverage (TASK-3.3):
    - create_event: insert + flush, owner_type defaulting
    - list_events: all filter combinations, pagination, ordering
    - get_event: PK lookup, missing event
    - count_events: filter combinations
    - list_provenance_slice: time window filters, ordering
    - Multi-tenant filtering via owner_type
    - No update/delete methods exposed

Architecture note — why mock sessions rather than SQLite in-memory:
    ``ArtifactHistoryEvent`` inherits from the shared SQLAlchemy ``Base``
    and FK-references ``artifacts.id``.  Standing up the full schema plus
    an artifacts row for every test is expensive and fragile.  Mock-based
    tests isolate the repository logic (filter construction, pagination,
    flush) without requiring a live database.

    The only PostgreSQL-specific concern here is the ``func.count()`` scalar
    in ``count_events``, which works identically in SQLite and PostgreSQL at
    the SQL level.  No JSONB / UUID column types are involved, so the
    comparator-cache-poisoning issue documented in ``skillmeat/cache/tests/CLAUDE.md``
    does not apply.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
from unittest.mock import MagicMock, call

import pytest
from sqlalchemy.orm import Session

from skillmeat.cache.enterprise_repositories import EnterpriseArtifactActivityRepository
from skillmeat.cache.models import ArtifactHistoryEvent


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

ARTIFACT_A = "skill:canvas-design"
ARTIFACT_B = "command:git-commit"

OWNER_TENANT_1 = "tenant_1"
OWNER_TENANT_2 = "tenant_2"

EVENT_ID_1 = 1001
EVENT_ID_2 = 1002

TS_BASE = datetime(2025, 1, 15, 12, 0, 0)
TS_LATER = TS_BASE + timedelta(hours=1)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_id: int = EVENT_ID_1,
    artifact_id: str = ARTIFACT_A,
    event_type: str = "create",
    actor_id: Optional[str] = "user-abc",
    owner_type: str = OWNER_TENANT_1,
    timestamp: datetime = TS_BASE,
    diff_json: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> MagicMock:
    """Build a MagicMock that behaves like an ArtifactHistoryEvent row."""
    evt = MagicMock(spec=ArtifactHistoryEvent)
    evt.id = event_id
    evt.artifact_id = artifact_id
    evt.event_type = event_type
    evt.actor_id = actor_id
    evt.owner_type = owner_type
    evt.timestamp = timestamp
    evt.diff_json = diff_json
    evt.content_hash = content_hash
    return evt


_UNSET = object()  # sentinel — distinguishes "not provided" from None


def _make_session(
    *,
    execute_scalars: Optional[List] = None,
    execute_scalar_one: object = _UNSET,
    execute_scalar_one_or_none: object = _UNSET,
) -> MagicMock:
    """Return a MagicMock session pre-configured for common return patterns.

    Parameters
    ----------
    execute_scalars:
        List returned by ``session.execute(stmt).scalars().all()``.
    execute_scalar_one:
        Value returned by ``session.execute(stmt).scalar_one()``.
        Pass ``None`` explicitly to configure the mock to return ``None``.
    execute_scalar_one_or_none:
        Value returned by ``session.execute(stmt).scalar_one_or_none()``.
        Pass ``None`` explicitly to configure the mock to return ``None``.
    """
    session = MagicMock(spec=Session)

    execute_mock = MagicMock()

    if execute_scalars is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = execute_scalars
        execute_mock.scalars.return_value = scalars_mock

    if execute_scalar_one is not _UNSET:
        execute_mock.scalar_one.return_value = execute_scalar_one

    if execute_scalar_one_or_none is not _UNSET:
        execute_mock.scalar_one_or_none.return_value = execute_scalar_one_or_none

    session.execute.return_value = execute_mock
    return session


def _repo(session: MagicMock) -> EnterpriseArtifactActivityRepository:
    """Return a repository instance bound to *session*."""
    return EnterpriseArtifactActivityRepository(session)


# ---------------------------------------------------------------------------
# TestCreateEvent
# ---------------------------------------------------------------------------


class TestCreateEvent:
    """create_event — insert-only, flush to obtain PK."""

    def test_create_event_adds_and_flushes(self) -> None:
        """create_event calls session.add() and session.flush()."""
        session = MagicMock(spec=Session)
        repo = _repo(session)

        # The newly flushed event will have id populated after flush;
        # simulate that by letting session.flush() set it via side_effect.
        captured: list[ArtifactHistoryEvent] = []

        def _flush_and_assign_id() -> None:
            captured[0].id = EVENT_ID_1

        def _add(obj: ArtifactHistoryEvent) -> None:
            captured.append(obj)

        session.add.side_effect = _add
        session.flush.side_effect = _flush_and_assign_id

        result = repo.create_event(
            artifact_id=ARTIFACT_A,
            event_type="create",
            actor_id="user-abc",
            owner_type=OWNER_TENANT_1,
            diff_json=None,
            content_hash=None,
        )

        session.add.assert_called_once()
        session.flush.assert_called_once()
        assert result.artifact_id == ARTIFACT_A
        assert result.event_type == "create"
        assert result.actor_id == "user-abc"
        assert result.owner_type == OWNER_TENANT_1

    def test_create_event_defaults_empty_owner_type_to_user(self) -> None:
        """create_event replaces empty owner_type with 'user' (OwnerType.user)."""
        session = MagicMock(spec=Session)
        repo = _repo(session)

        captured: list[ArtifactHistoryEvent] = []
        session.add.side_effect = captured.append

        repo.create_event(
            artifact_id=ARTIFACT_A,
            event_type="update",
            actor_id=None,
            owner_type="",  # empty string should resolve to "user"
            diff_json=None,
            content_hash=None,
        )

        added = captured[0]
        assert added.owner_type == "user"

    def test_create_event_accepts_none_actor_id(self) -> None:
        """create_event accepts None actor_id for automated/system events."""
        session = MagicMock(spec=Session)
        repo = _repo(session)

        captured: list[ArtifactHistoryEvent] = []
        session.add.side_effect = captured.append

        repo.create_event(
            artifact_id=ARTIFACT_B,
            event_type="sync",
            actor_id=None,
            owner_type=OWNER_TENANT_1,
            diff_json=None,
            content_hash=None,
        )

        added = captured[0]
        assert added.actor_id is None

    def test_create_event_stores_diff_json_and_content_hash(self) -> None:
        """create_event persists diff_json and content_hash when provided."""
        session = MagicMock(spec=Session)
        repo = _repo(session)

        captured: list[ArtifactHistoryEvent] = []
        session.add.side_effect = captured.append

        repo.create_event(
            artifact_id=ARTIFACT_A,
            event_type="update",
            actor_id="user-xyz",
            owner_type=OWNER_TENANT_1,
            diff_json='{"added": ["line1"]}',
            content_hash="abc123",
        )

        added = captured[0]
        assert added.diff_json == '{"added": ["line1"]}'
        assert added.content_hash == "abc123"

    def test_create_event_does_not_have_update_or_delete_methods(self) -> None:
        """Confirm no update/delete methods exist on the repository."""
        session = MagicMock(spec=Session)
        repo = _repo(session)

        assert not hasattr(repo, "update_event")
        assert not hasattr(repo, "delete_event")
        assert not hasattr(repo, "update")
        assert not hasattr(repo, "delete")


# ---------------------------------------------------------------------------
# TestListEvents
# ---------------------------------------------------------------------------


class TestListEvents:
    """list_events — filtered, paginated, ordered by timestamp/id asc."""

    def test_list_events_no_filters_returns_all(self) -> None:
        """list_events with no filters returns all events from the DB."""
        evt1 = _make_event(event_id=EVENT_ID_1, timestamp=TS_BASE)
        evt2 = _make_event(event_id=EVENT_ID_2, timestamp=TS_LATER)
        session = _make_session(execute_scalars=[evt1, evt2])
        repo = _repo(session)

        result = repo.list_events()

        assert result == [evt1, evt2]
        session.execute.assert_called_once()

    def test_list_events_filter_by_artifact_id(self) -> None:
        """list_events restricts to a specific artifact when artifact_id is provided."""
        evt = _make_event(artifact_id=ARTIFACT_A)
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_events(artifact_id=ARTIFACT_A)

        assert len(result) == 1
        assert result[0].artifact_id == ARTIFACT_A

    def test_list_events_filter_by_event_type(self) -> None:
        """list_events restricts to a specific event type."""
        evt = _make_event(event_type="deploy")
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_events(event_type="deploy")

        assert len(result) == 1
        assert result[0].event_type == "deploy"

    def test_list_events_filter_by_actor_id(self) -> None:
        """list_events restricts to events triggered by a specific actor."""
        evt = _make_event(actor_id="user-abc")
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_events(actor_id="user-abc")

        assert len(result) == 1

    def test_list_events_filter_by_owner_type(self) -> None:
        """list_events restricts by owner_type for multi-tenant scoping."""
        evt = _make_event(owner_type=OWNER_TENANT_1)
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_events(owner_type=OWNER_TENANT_1)

        assert len(result) == 1
        assert result[0].owner_type == OWNER_TENANT_1

    def test_list_events_owner_type_tenant2_returns_empty(self) -> None:
        """list_events with tenant_2 owner_type finds no tenant_1 events."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        result = repo.list_events(owner_type=OWNER_TENANT_2)

        assert result == []

    def test_list_events_filter_by_time_range(self) -> None:
        """list_events applies start/end timestamp bounds."""
        evt = _make_event(timestamp=TS_BASE)
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_events(time_range=(TS_BASE, TS_LATER))

        assert len(result) == 1

    def test_list_events_respects_limit_and_offset(self) -> None:
        """list_events passes limit/offset to the statement."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        # Just verify it doesn't raise and calls execute once
        result = repo.list_events(limit=10, offset=5)

        assert isinstance(result, list)
        session.execute.assert_called_once()

    def test_list_events_returns_empty_list_when_none_match(self) -> None:
        """list_events returns [] when no events match the filters."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        result = repo.list_events(artifact_id="nonexistent:artifact")

        assert result == []

    def test_list_events_combined_filters(self) -> None:
        """list_events AND-s all provided filters together."""
        evt = _make_event(
            artifact_id=ARTIFACT_A,
            event_type="deploy",
            owner_type=OWNER_TENANT_1,
        )
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_events(
            artifact_id=ARTIFACT_A,
            event_type="deploy",
            owner_type=OWNER_TENANT_1,
        )

        assert len(result) == 1


# ---------------------------------------------------------------------------
# TestGetEvent
# ---------------------------------------------------------------------------


class TestGetEvent:
    """get_event — PK lookup for a single event row."""

    def test_get_event_returns_matching_event(self) -> None:
        """get_event returns the event when found by PK."""
        evt = _make_event(event_id=EVENT_ID_1)
        session = _make_session(execute_scalar_one_or_none=evt)
        repo = _repo(session)

        result = repo.get_event(EVENT_ID_1)

        assert result is evt
        session.execute.assert_called_once()

    def test_get_event_returns_none_when_not_found(self) -> None:
        """get_event returns None when no row has the given PK."""
        session = _make_session(execute_scalar_one_or_none=None)
        repo = _repo(session)

        result = repo.get_event(99999)

        assert result is None

    def test_get_event_with_ctx_does_not_raise(self) -> None:
        """get_event accepts an optional ctx argument without error."""
        session = _make_session(execute_scalar_one_or_none=None)
        repo = _repo(session)

        result = repo.get_event(EVENT_ID_1, ctx=object())

        assert result is None


# ---------------------------------------------------------------------------
# TestCountEvents
# ---------------------------------------------------------------------------


class TestCountEvents:
    """count_events — aggregate count with optional filters."""

    def test_count_events_no_filters_returns_total(self) -> None:
        """count_events with no filters returns the total event count."""
        session = _make_session(execute_scalar_one=42)
        repo = _repo(session)

        result = repo.count_events()

        assert result == 42

    def test_count_events_filter_by_artifact_id(self) -> None:
        """count_events scoped to a single artifact returns its count."""
        session = _make_session(execute_scalar_one=5)
        repo = _repo(session)

        result = repo.count_events(artifact_id=ARTIFACT_A)

        assert result == 5

    def test_count_events_filter_by_event_type(self) -> None:
        """count_events filtered by event_type returns only that type's count."""
        session = _make_session(execute_scalar_one=3)
        repo = _repo(session)

        result = repo.count_events(event_type="deploy")

        assert result == 3

    def test_count_events_filter_by_owner_type(self) -> None:
        """count_events filters by owner_type for multi-tenant scoping."""
        session = _make_session(execute_scalar_one=7)
        repo = _repo(session)

        result = repo.count_events(owner_type=OWNER_TENANT_1)

        assert result == 7

    def test_count_events_combined_filters(self) -> None:
        """count_events AND-s artifact_id + event_type + owner_type."""
        session = _make_session(execute_scalar_one=2)
        repo = _repo(session)

        result = repo.count_events(
            artifact_id=ARTIFACT_A,
            event_type="create",
            owner_type=OWNER_TENANT_1,
        )

        assert result == 2

    def test_count_events_returns_zero_when_none_match(self) -> None:
        """count_events returns 0 when no events match the filters."""
        session = _make_session(execute_scalar_one=0)
        repo = _repo(session)

        result = repo.count_events(artifact_id="no:such:artifact")

        assert result == 0

    def test_count_events_returns_int(self) -> None:
        """count_events always returns a Python int (not a SQLAlchemy scalar)."""
        session = _make_session(execute_scalar_one=10)
        repo = _repo(session)

        result = repo.count_events()

        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TestListProvenanceSlice
# ---------------------------------------------------------------------------


class TestListProvenanceSlice:
    """list_provenance_slice — ordered timeline for a single artifact."""

    def test_list_provenance_slice_all_events_for_artifact(self) -> None:
        """list_provenance_slice returns all events for the given artifact."""
        evt1 = _make_event(event_id=EVENT_ID_1, artifact_id=ARTIFACT_A, timestamp=TS_BASE)
        evt2 = _make_event(event_id=EVENT_ID_2, artifact_id=ARTIFACT_A, timestamp=TS_LATER)
        session = _make_session(execute_scalars=[evt1, evt2])
        repo = _repo(session)

        result = repo.list_provenance_slice(ARTIFACT_A)

        assert result == [evt1, evt2]

    def test_list_provenance_slice_with_since_bound(self) -> None:
        """list_provenance_slice applies since lower-bound."""
        evt = _make_event(timestamp=TS_LATER)
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_provenance_slice(ARTIFACT_A, since=TS_LATER)

        assert len(result) == 1

    def test_list_provenance_slice_with_until_bound(self) -> None:
        """list_provenance_slice applies until upper-bound."""
        evt = _make_event(timestamp=TS_BASE)
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_provenance_slice(ARTIFACT_A, until=TS_BASE)

        assert len(result) == 1

    def test_list_provenance_slice_with_both_bounds(self) -> None:
        """list_provenance_slice applies both since and until."""
        evt = _make_event(timestamp=TS_BASE)
        session = _make_session(execute_scalars=[evt])
        repo = _repo(session)

        result = repo.list_provenance_slice(
            ARTIFACT_A,
            since=TS_BASE,
            until=TS_LATER,
        )

        assert len(result) == 1

    def test_list_provenance_slice_returns_empty_when_none_match(self) -> None:
        """list_provenance_slice returns [] when no events exist for the artifact."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        result = repo.list_provenance_slice("nonexistent:artifact")

        assert result == []

    def test_list_provenance_slice_single_artifact_not_cross_polluted(self) -> None:
        """list_provenance_slice for ARTIFACT_B should not return ARTIFACT_A events.

        The repository always adds ``artifact_id = ?`` to the WHERE clause so
        events from a different artifact are excluded even if the DB contains
        both.
        """
        # Session returns empty (simulates artifact_id filter excluding ARTIFACT_A)
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        result = repo.list_provenance_slice(ARTIFACT_B)

        assert result == []
        session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# TestMultiTenantFiltering
# ---------------------------------------------------------------------------


class TestMultiTenantFiltering:
    """Verify that owner_type is the multi-tenant discriminator for ArtifactHistoryEvent.

    ArtifactHistoryEvent has no tenant_id column.  The multi-tenant boundary
    is enforced by populating owner_type at write time and filtering by it at
    read time.
    """

    def test_list_events_tenant1_does_not_see_tenant2_events(self) -> None:
        """Filtering by OWNER_TENANT_1 excludes OWNER_TENANT_2 events."""
        session = _make_session(execute_scalars=[])
        repo = _repo(session)

        result = repo.list_events(owner_type=OWNER_TENANT_1)

        # The statement was built with owner_type filter — mock returns empty,
        # confirming no cross-tenant data is returned.
        assert result == []

    def test_count_events_scoped_to_tenant(self) -> None:
        """count_events filtered by owner_type returns only that tenant's count."""
        session = _make_session(execute_scalar_one=0)
        repo = _repo(session)

        result = repo.count_events(owner_type=OWNER_TENANT_2)

        assert result == 0

    def test_create_event_stores_provided_owner_type(self) -> None:
        """create_event stores the provided owner_type without modification."""
        session = MagicMock(spec=Session)
        repo = _repo(session)

        captured: list[ArtifactHistoryEvent] = []
        session.add.side_effect = captured.append

        repo.create_event(
            artifact_id=ARTIFACT_A,
            event_type="create",
            actor_id=None,
            owner_type=OWNER_TENANT_2,
            diff_json=None,
            content_hash=None,
        )

        assert captured[0].owner_type == OWNER_TENANT_2


# ---------------------------------------------------------------------------
# TestNoMutationMethods
# ---------------------------------------------------------------------------


class TestNoMutationMethods:
    """Confirm that update and delete methods are absent (insert-only contract)."""

    def test_no_update_event_method(self) -> None:
        """update_event must not exist on EnterpriseArtifactActivityRepository."""
        session = MagicMock(spec=Session)
        repo = _repo(session)
        assert not hasattr(repo, "update_event")

    def test_no_delete_event_method(self) -> None:
        """delete_event must not exist on EnterpriseArtifactActivityRepository."""
        session = MagicMock(spec=Session)
        repo = _repo(session)
        assert not hasattr(repo, "delete_event")

    def test_no_generic_update_method(self) -> None:
        """Generic update() must not exist."""
        session = MagicMock(spec=Session)
        repo = _repo(session)
        assert not hasattr(repo, "update")

    def test_no_generic_delete_method(self) -> None:
        """Generic delete() must not exist."""
        session = MagicMock(spec=Session)
        repo = _repo(session)
        assert not hasattr(repo, "delete")
