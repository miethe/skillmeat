"""Unit tests for LocalArtifactActivityRepository.

Tests cover:
- create_event with all fields populated
- create_event with optional fields as None
- list_events with no filters (returns all)
- list_events filtered by artifact_id
- list_events filtered by event_type
- list_events filtered by actor_id
- list_events filtered by owner_type
- list_events filtered by time_range
- list_events with combined filters
- list_events with limit and offset (pagination)
- get_event by valid ID
- get_event returns None for nonexistent ID
- count_events with no filters
- count_events filtered by artifact_id
- count_events filtered by event_type
- count_events filtered by owner_type
- list_provenance_slice for a single artifact
- list_provenance_slice with since/until time bounds
- immutability: no update or delete methods present

NOTE: Uses selective Table.create() in FK-dependency order because
Base.metadata.create_all() fails against SQLite for tables with
PostgreSQL-only column types (TSVECTOR, etc.).
See skillmeat/cache/tests/CLAUDE.md for details.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Generator

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.auth_types import OwnerType
from skillmeat.cache.models import (
    Artifact,
    ArtifactHistoryEvent,
    Base,
    Project,
)
from skillmeat.core.repositories.local_artifact_activity import (
    LocalArtifactActivityRepository,
)


# ---------------------------------------------------------------------------
# Tables needed in FK-dependency order (excludes TSVECTOR-bearing tables)
# ---------------------------------------------------------------------------

_TABLES_NEEDED = [
    "projects",
    "artifacts",
    "artifact_history_events",
]


# ---------------------------------------------------------------------------
# Module-level SQLite engine and session factory
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with only the activity-repo-related tables."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    meta = Base.metadata
    with eng.begin() as conn:
        for table_name in _TABLES_NEEDED:
            meta.tables[table_name].create(conn, checkfirst=True)

    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    """Fresh session that rolls back after each test for isolation."""
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    sess = Session_()
    yield sess
    sess.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def project(session: Session) -> Project:
    """Minimal Project row required by Artifact FK."""
    proj = Project(
        id="proj-activity-test",
        name="Activity test project",
        path="/tmp/activity-test",
        status="active",
    )
    session.add(proj)
    session.flush()
    return proj


@pytest.fixture()
def artifact(session: Session, project: Project) -> Artifact:
    """Minimal Artifact row required by ArtifactHistoryEvent FK."""
    art = Artifact(
        id="skill:activity-test-skill",
        project_id=project.id,
        name="activity-test-skill",
        type="skill",
    )
    session.add(art)
    session.flush()
    return art


@pytest.fixture()
def artifact2(session: Session, project: Project) -> Artifact:
    """Second artifact for cross-artifact filter tests."""
    art = Artifact(
        id="command:activity-test-command",
        project_id=project.id,
        name="activity-test-command",
        type="command",
    )
    session.add(art)
    session.flush()
    return art


@pytest.fixture()
def repo(session: Session) -> LocalArtifactActivityRepository:
    """Repository under test wired to the in-memory session."""
    return LocalArtifactActivityRepository(session=session)


# ---------------------------------------------------------------------------
# create_event
# ---------------------------------------------------------------------------


class TestCreateEvent:
    """Tests for LocalArtifactActivityRepository.create_event()."""

    def test_create_event_all_fields(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """create_event populates all columns correctly and returns the row."""
        event_obj = repo.create_event(
            artifact_id=artifact.id,
            event_type="create",
            actor_id="user-abc",
            owner_type=OwnerType.user.value,
            diff_json='{"before": null, "after": {"name": "activity-test-skill"}}',
            content_hash="a" * 64,
        )

        assert event_obj.id is not None
        assert event_obj.artifact_id == artifact.id
        assert event_obj.event_type == "create"
        assert event_obj.actor_id == "user-abc"
        assert event_obj.owner_type == OwnerType.user.value
        assert event_obj.diff_json is not None
        assert event_obj.content_hash == "a" * 64

    def test_create_event_nullable_fields_as_none(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """create_event accepts None for optional fields actor_id, diff_json, content_hash."""
        event_obj = repo.create_event(
            artifact_id=artifact.id,
            event_type="sync",
            actor_id=None,
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )

        assert event_obj.id is not None
        assert event_obj.actor_id is None
        assert event_obj.diff_json is None
        assert event_obj.content_hash is None

    def test_create_event_auto_timestamp(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """timestamp is auto-populated on flush."""
        event_obj = repo.create_event(
            artifact_id=artifact.id,
            event_type="update",
            actor_id=None,
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        assert event_obj.timestamp is not None

    def test_create_event_default_owner_type_when_empty(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """Passing empty string for owner_type falls back to OwnerType.user."""
        event_obj = repo.create_event(
            artifact_id=artifact.id,
            event_type="deploy",
            actor_id=None,
            owner_type="",
            diff_json=None,
            content_hash=None,
        )
        assert event_obj.owner_type == OwnerType.user.value

    def test_create_multiple_events_for_same_artifact(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """Multiple events can be created for the same artifact."""
        e1 = repo.create_event(
            artifact_id=artifact.id,
            event_type="create",
            actor_id="actor-1",
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        e2 = repo.create_event(
            artifact_id=artifact.id,
            event_type="update",
            actor_id="actor-1",
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        assert e1.id != e2.id


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


class TestListEvents:
    """Tests for LocalArtifactActivityRepository.list_events()."""

    @pytest.fixture(autouse=True)
    def seed_events(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
        artifact2: Artifact,
    ):
        """Insert a fixed set of events used across list_events tests."""
        base_ts = datetime(2024, 6, 1, 12, 0, 0)
        self._events = [
            repo.create_event(
                artifact_id=artifact.id,
                event_type="create",
                actor_id="user-alpha",
                owner_type=OwnerType.user.value,
                diff_json=None,
                content_hash=None,
            ),
            repo.create_event(
                artifact_id=artifact.id,
                event_type="update",
                actor_id="user-alpha",
                owner_type=OwnerType.user.value,
                diff_json='{"change": "v2"}',
                content_hash="b" * 64,
            ),
            repo.create_event(
                artifact_id=artifact.id,
                event_type="deploy",
                actor_id="user-beta",
                owner_type=OwnerType.user.value,
                diff_json=None,
                content_hash=None,
            ),
            repo.create_event(
                artifact_id=artifact2.id,
                event_type="create",
                actor_id="user-gamma",
                owner_type="team",
                diff_json=None,
                content_hash=None,
            ),
        ]

    def test_list_events_no_filter_returns_all(
        self, repo: LocalArtifactActivityRepository
    ):
        """list_events() with no filters returns all seeded events."""
        results = repo.list_events()
        assert len(results) >= 4

    def test_list_events_filter_by_artifact_id(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
        artifact2: Artifact,
    ):
        """Filter by artifact_id returns only events for that artifact."""
        results = repo.list_events(artifact_id=artifact.id)
        assert all(e.artifact_id == artifact.id for e in results)
        ids = {e.artifact_id for e in results}
        assert artifact2.id not in ids

    def test_list_events_filter_by_event_type(
        self, repo: LocalArtifactActivityRepository
    ):
        """Filter by event_type returns only matching events."""
        results = repo.list_events(event_type="create")
        assert all(e.event_type == "create" for e in results)
        assert len(results) >= 2  # one per artifact

    def test_list_events_filter_by_actor_id(
        self, repo: LocalArtifactActivityRepository
    ):
        """Filter by actor_id returns only events from that actor."""
        results = repo.list_events(actor_id="user-beta")
        assert all(e.actor_id == "user-beta" for e in results)
        assert len(results) >= 1

    def test_list_events_filter_by_owner_type(
        self, repo: LocalArtifactActivityRepository
    ):
        """Filter by owner_type restricts results correctly."""
        results = repo.list_events(owner_type="team")
        assert all(e.owner_type == "team" for e in results)
        assert len(results) >= 1

    def test_list_events_combined_filters(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """Multiple filters are AND-ed together."""
        results = repo.list_events(
            artifact_id=artifact.id,
            event_type="update",
        )
        assert all(
            e.artifact_id == artifact.id and e.event_type == "update"
            for e in results
        )

    def test_list_events_time_range_filter(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """time_range filter restricts to events within the window."""
        # Insert an event with a known far-future timestamp by directly
        # constructing the model (bypassing the repo's create_event which
        # uses the default utcnow).
        from skillmeat.cache.models import ArtifactHistoryEvent as _Evt

        future_ts = datetime(2099, 1, 1, 0, 0, 0)
        future_event = _Evt(
            artifact_id=artifact.id,
            event_type="sync",
            owner_type=OwnerType.user.value,
            timestamp=future_ts,
        )
        repo.session.add(future_event)
        repo.session.flush()

        # Query within a tight window that excludes the future event
        start = datetime(2024, 1, 1)
        end = datetime(2025, 1, 1)
        results = repo.list_events(
            artifact_id=artifact.id,
            time_range=(start, end),
        )
        for e in results:
            assert e.timestamp >= start
            assert e.timestamp <= end
        # The far-future event should not appear
        assert all(e.timestamp != future_ts for e in results)

    def test_list_events_pagination_limit(
        self, repo: LocalArtifactActivityRepository
    ):
        """limit parameter caps the number of returned events."""
        results = repo.list_events(limit=2)
        assert len(results) <= 2

    def test_list_events_pagination_offset(
        self, repo: LocalArtifactActivityRepository
    ):
        """offset parameter skips the correct number of leading events."""
        all_results = repo.list_events()
        offset_results = repo.list_events(offset=1)
        if len(all_results) > 1:
            assert offset_results[0].id == all_results[1].id

    def test_list_events_ordered_by_timestamp_then_id(
        self, repo: LocalArtifactActivityRepository, artifact: Artifact
    ):
        """Results are ordered by (timestamp asc, id asc)."""
        results = repo.list_events(artifact_id=artifact.id)
        for i in range(len(results) - 1):
            assert (results[i].timestamp, results[i].id) <= (
                results[i + 1].timestamp,
                results[i + 1].id,
            )


# ---------------------------------------------------------------------------
# get_event
# ---------------------------------------------------------------------------


class TestGetEvent:
    """Tests for LocalArtifactActivityRepository.get_event()."""

    def test_get_event_returns_correct_row(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """get_event() returns the exact row by primary key."""
        created = repo.create_event(
            artifact_id=artifact.id,
            event_type="undeploy",
            actor_id="user-z",
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        retrieved = repo.get_event(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.event_type == "undeploy"
        assert retrieved.actor_id == "user-z"

    def test_get_event_returns_none_for_missing_id(
        self, repo: LocalArtifactActivityRepository
    ):
        """get_event() returns None when the ID does not exist."""
        result = repo.get_event(999_999_999)
        assert result is None


# ---------------------------------------------------------------------------
# count_events
# ---------------------------------------------------------------------------


class TestCountEvents:
    """Tests for LocalArtifactActivityRepository.count_events()."""

    @pytest.fixture(autouse=True)
    def seed(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
        artifact2: Artifact,
    ):
        """Seed deterministic events for count tests."""
        for _ in range(3):
            repo.create_event(
                artifact_id=artifact.id,
                event_type="update",
                actor_id=None,
                owner_type=OwnerType.user.value,
                diff_json=None,
                content_hash=None,
            )
        repo.create_event(
            artifact_id=artifact2.id,
            event_type="deploy",
            actor_id=None,
            owner_type="team",
            diff_json=None,
            content_hash=None,
        )

    def test_count_all_events(self, repo: LocalArtifactActivityRepository):
        """count_events() with no filters counts all rows."""
        total = repo.count_events()
        assert total >= 4

    def test_count_by_artifact_id(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """count_events(artifact_id=...) counts only rows for that artifact."""
        count = repo.count_events(artifact_id=artifact.id)
        assert count >= 3

    def test_count_by_event_type(self, repo: LocalArtifactActivityRepository):
        """count_events(event_type=...) counts only rows of that type."""
        count = repo.count_events(event_type="update")
        assert count >= 3

    def test_count_by_owner_type(self, repo: LocalArtifactActivityRepository):
        """count_events(owner_type=...) counts only rows with that owner_type."""
        team_count = repo.count_events(owner_type="team")
        assert team_count >= 1

    def test_count_combined_filters(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """count_events with multiple filters AND-s them."""
        count = repo.count_events(
            artifact_id=artifact.id,
            event_type="update",
        )
        assert count >= 3

    def test_count_returns_zero_for_nonexistent_filter(
        self, repo: LocalArtifactActivityRepository
    ):
        """count_events returns 0 when no rows match."""
        count = repo.count_events(event_type="nonexistent_type_xyz")
        assert count == 0


# ---------------------------------------------------------------------------
# list_provenance_slice
# ---------------------------------------------------------------------------


class TestListProvenanceSlice:
    """Tests for LocalArtifactActivityRepository.list_provenance_slice()."""

    def test_provenance_slice_returns_only_target_artifact(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
        artifact2: Artifact,
    ):
        """list_provenance_slice() returns only events for the given artifact."""
        repo.create_event(
            artifact_id=artifact.id,
            event_type="create",
            actor_id=None,
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        repo.create_event(
            artifact_id=artifact2.id,
            event_type="create",
            actor_id=None,
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        results = repo.list_provenance_slice(artifact_id=artifact.id)
        assert all(e.artifact_id == artifact.id for e in results)

    def test_provenance_slice_no_time_bounds_returns_all(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """Without since/until, all events for the artifact are returned."""
        repo.create_event(
            artifact_id=artifact.id,
            event_type="sync",
            actor_id=None,
            owner_type=OwnerType.user.value,
            diff_json=None,
            content_hash=None,
        )
        results = repo.list_provenance_slice(artifact_id=artifact.id)
        assert len(results) >= 1

    def test_provenance_slice_with_since_bound(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """since= excludes events before the lower bound."""
        from skillmeat.cache.models import ArtifactHistoryEvent as _Evt

        old_ts = datetime(2020, 1, 1)
        new_ts = datetime(2024, 6, 15)

        old_event = _Evt(
            artifact_id=artifact.id,
            event_type="create",
            owner_type=OwnerType.user.value,
            timestamp=old_ts,
        )
        new_event = _Evt(
            artifact_id=artifact.id,
            event_type="update",
            owner_type=OwnerType.user.value,
            timestamp=new_ts,
        )
        repo.session.add(old_event)
        repo.session.add(new_event)
        repo.session.flush()

        cutoff = datetime(2023, 1, 1)
        results = repo.list_provenance_slice(
            artifact_id=artifact.id, since=cutoff
        )
        for e in results:
            assert e.timestamp >= cutoff

    def test_provenance_slice_with_until_bound(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """until= excludes events after the upper bound."""
        from skillmeat.cache.models import ArtifactHistoryEvent as _Evt

        early_ts = datetime(2022, 3, 1)
        late_ts = datetime(2025, 12, 31)

        early_event = _Evt(
            artifact_id=artifact.id,
            event_type="deploy",
            owner_type=OwnerType.user.value,
            timestamp=early_ts,
        )
        late_event = _Evt(
            artifact_id=artifact.id,
            event_type="undeploy",
            owner_type=OwnerType.user.value,
            timestamp=late_ts,
        )
        repo.session.add(early_event)
        repo.session.add(late_event)
        repo.session.flush()

        cutoff = datetime(2023, 1, 1)
        results = repo.list_provenance_slice(
            artifact_id=artifact.id, until=cutoff
        )
        for e in results:
            assert e.timestamp <= cutoff

    def test_provenance_slice_ordered_chronologically(
        self,
        repo: LocalArtifactActivityRepository,
        artifact: Artifact,
    ):
        """Results are ordered (timestamp asc, id asc)."""
        for _ in range(3):
            repo.create_event(
                artifact_id=artifact.id,
                event_type="sync",
                actor_id=None,
                owner_type=OwnerType.user.value,
                diff_json=None,
                content_hash=None,
            )
        results = repo.list_provenance_slice(artifact_id=artifact.id)
        for i in range(len(results) - 1):
            assert (results[i].timestamp, results[i].id) <= (
                results[i + 1].timestamp,
                results[i + 1].id,
            )

    def test_provenance_slice_empty_for_unknown_artifact(
        self, repo: LocalArtifactActivityRepository
    ):
        """list_provenance_slice() returns empty list for an unknown artifact."""
        results = repo.list_provenance_slice(artifact_id="nonexistent:artifact")
        assert results == []


# ---------------------------------------------------------------------------
# Immutability contract
# ---------------------------------------------------------------------------


class TestImmutability:
    """Verify the repository has no update or delete methods."""

    def test_no_update_method(self):
        """LocalArtifactActivityRepository does not expose an update method."""
        assert not hasattr(LocalArtifactActivityRepository, "update")
        assert not hasattr(LocalArtifactActivityRepository, "update_event")

    def test_no_delete_method(self):
        """LocalArtifactActivityRepository does not expose a delete method."""
        assert not hasattr(LocalArtifactActivityRepository, "delete")
        assert not hasattr(LocalArtifactActivityRepository, "delete_event")
