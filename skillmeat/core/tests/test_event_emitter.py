"""Unit tests for skillmeat.core.bom.event_emitter.

Tests cover:
- emit_activity_event creates an ArtifactHistoryEvent row in the DB
- emit_activity_event silently catches exceptions (never re-raises)
- All valid event_type values are accepted
- Invalid event_type is rejected with a warning (no DB write)
- background_tasks path defers the write correctly
- session=None path opens its own session
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# In-memory SQLite fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sqlite_engine():
    """Create an in-memory SQLite engine with the full ORM schema."""
    from skillmeat.cache.models import Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(sqlite_engine):
    """Yield a fresh session for each test, rolling back afterwards."""
    SessionFactory = sessionmaker(bind=sqlite_engine)
    session = SessionFactory()
    yield session
    session.rollback()
    session.close()


def _seed_artifact(session: Session, artifact_id: str = "skill:test-skill") -> None:
    """Insert a minimal Artifact row so FK constraint on ArtifactHistoryEvent is satisfied."""
    from skillmeat.cache.models import Artifact, Project

    # Project first (Artifact has FK to projects.id)
    if not session.query(Project).filter_by(id="test-proj").first():
        session.add(
            Project(
                id="test-proj",
                name="test-proj",
                path="/tmp/test-proj",
            )
        )

    # Artifact
    if not session.query(Artifact).filter_by(id=artifact_id).first():
        artifact_type, artifact_name = artifact_id.split(":", 1)
        session.add(
            Artifact(
                id=artifact_id,
                project_id="test-proj",
                name=artifact_name,
                type=artifact_type,
            )
        )

    session.commit()


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


class TestEmitActivityEventCreatesRow:
    """emit_activity_event inserts an ArtifactHistoryEvent when the session is provided."""

    def test_create_event_written_to_db(self, db_session: Session) -> None:
        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        _seed_artifact(db_session, "skill:my-skill")

        emit_activity_event(
            session=db_session,
            artifact_id="skill:my-skill",
            event_type="create",
        )

        rows = db_session.query(ArtifactHistoryEvent).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.artifact_id == "skill:my-skill"
        assert row.event_type == "create"
        assert row.owner_type == "user"
        assert row.actor_id is None

    def test_actor_id_and_content_hash_stored(self, db_session: Session) -> None:
        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        _seed_artifact(db_session, "command:my-cmd")

        emit_activity_event(
            session=db_session,
            artifact_id="command:my-cmd",
            event_type="update",
            actor_id="user-abc",
            content_hash="a" * 64,
        )

        row = db_session.query(ArtifactHistoryEvent).filter_by(
            artifact_id="command:my-cmd"
        ).first()
        assert row is not None
        assert row.actor_id == "user-abc"
        assert row.content_hash == "a" * 64

    def test_diff_json_stored(self, db_session: Session) -> None:
        import json

        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        _seed_artifact(db_session, "agent:my-agent")
        diff = json.dumps({"added": ["file.md"], "removed": []})

        emit_activity_event(
            session=db_session,
            artifact_id="agent:my-agent",
            event_type="sync",
            diff_json=diff,
        )

        row = db_session.query(ArtifactHistoryEvent).filter_by(
            artifact_id="agent:my-agent"
        ).first()
        assert row is not None
        assert row.diff_json == diff

    def test_timestamp_set(self, db_session: Session) -> None:
        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        _seed_artifact(db_session, "skill:ts-skill")
        before = datetime.utcnow()
        emit_activity_event(
            session=db_session,
            artifact_id="skill:ts-skill",
            event_type="deploy",
        )
        after = datetime.utcnow()

        row = db_session.query(ArtifactHistoryEvent).filter_by(
            artifact_id="skill:ts-skill"
        ).first()
        assert row is not None
        assert before <= row.timestamp <= after


# ---------------------------------------------------------------------------
# All valid event_type values
# ---------------------------------------------------------------------------


class TestAllValidEventTypes:
    """Every valid event_type should produce a row without errors."""

    @pytest.mark.parametrize(
        "event_type",
        ["create", "update", "delete", "deploy", "undeploy", "sync"],
    )
    def test_valid_event_type(
        self, db_session: Session, event_type: str
    ) -> None:
        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        artifact_id = f"skill:artifact-for-{event_type}"
        _seed_artifact(db_session, artifact_id)

        emit_activity_event(
            session=db_session,
            artifact_id=artifact_id,
            event_type=event_type,
        )

        row = db_session.query(ArtifactHistoryEvent).filter_by(
            artifact_id=artifact_id
        ).first()
        assert row is not None, f"No row found for event_type={event_type!r}"
        assert row.event_type == event_type


# ---------------------------------------------------------------------------
# Invalid event_type — rejected silently
# ---------------------------------------------------------------------------


class TestInvalidEventType:
    """Invalid event_type values are logged and no DB write occurs."""

    def test_invalid_event_type_no_write(
        self, db_session: Session, caplog: pytest.LogCaptureFixture
    ) -> None:
        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        _seed_artifact(db_session, "skill:invalid-evt")

        with caplog.at_level(logging.WARNING, logger="skillmeat.core.bom.event_emitter"):
            emit_activity_event(
                session=db_session,
                artifact_id="skill:invalid-evt",
                event_type="nonexistent_event",
            )

        rows = db_session.query(ArtifactHistoryEvent).filter_by(
            artifact_id="skill:invalid-evt"
        ).all()
        assert rows == []
        assert any("nonexistent_event" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Exception safety — never propagates
# ---------------------------------------------------------------------------


class TestExceptionSafety:
    """A failing DB write must never propagate to the caller."""

    def test_session_write_failure_is_swallowed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from skillmeat.core.bom.event_emitter import emit_activity_event

        bad_session = MagicMock()
        bad_session.add.side_effect = RuntimeError("boom")

        with caplog.at_level(logging.WARNING, logger="skillmeat.core.bom.event_emitter"):
            # Must not raise
            emit_activity_event(
                session=bad_session,
                artifact_id="skill:any",
                event_type="create",
            )

        assert any("failed to record" in r.message for r in caplog.records)

    def test_standalone_session_failure_is_swallowed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from skillmeat.core.bom.event_emitter import emit_activity_event

        with patch(
            "skillmeat.core.bom.event_emitter._emit_with_new_session",
            side_effect=Exception("db gone"),
        ):
            with caplog.at_level(
                logging.WARNING, logger="skillmeat.core.bom.event_emitter"
            ):
                emit_activity_event(
                    artifact_id="skill:any",
                    event_type="deploy",
                )

        assert any("failed to record" in r.message for r in caplog.records)

    def test_background_task_failure_is_swallowed(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from skillmeat.core.bom.event_emitter import _background_emit

        with patch(
            "skillmeat.core.bom.event_emitter._emit_with_new_session",
            side_effect=Exception("db gone"),
        ):
            with caplog.at_level(
                logging.WARNING, logger="skillmeat.core.bom.event_emitter"
            ):
                _background_emit(
                    artifact_id="skill:any",
                    event_type="deploy",
                    actor_id=None,
                    owner_type="user",
                    diff_json=None,
                    content_hash=None,
                )

        assert any("failed to record" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# BackgroundTasks path
# ---------------------------------------------------------------------------


class TestBackgroundTasksPath:
    """When background_tasks is provided the write is deferred, not immediate."""

    def test_write_deferred_to_background(self, db_session: Session) -> None:
        from skillmeat.core.bom.event_emitter import emit_activity_event

        mock_bt = MagicMock()

        emit_activity_event(
            session=db_session,
            artifact_id="skill:bg-skill",
            event_type="deploy",
            actor_id="user-1",
            background_tasks=mock_bt,
        )

        # BackgroundTasks.add_task must have been called once
        mock_bt.add_task.assert_called_once()
        args, kwargs = mock_bt.add_task.call_args
        # First positional arg is the callable
        assert callable(args[0])
        # Keyword args should carry our event parameters
        assert kwargs["artifact_id"] == "skill:bg-skill"
        assert kwargs["event_type"] == "deploy"
        assert kwargs["actor_id"] == "user-1"

    def test_background_tasks_takes_priority_over_session(
        self, db_session: Session
    ) -> None:
        """background_tasks wins even when session is also provided."""
        from skillmeat.cache.models import ArtifactHistoryEvent
        from skillmeat.core.bom.event_emitter import emit_activity_event

        mock_bt = MagicMock()

        emit_activity_event(
            session=db_session,
            artifact_id="skill:bg-skill-2",
            event_type="undeploy",
            background_tasks=mock_bt,
        )

        # No immediate DB write — the session path was bypassed
        rows = db_session.query(ArtifactHistoryEvent).filter_by(
            artifact_id="skill:bg-skill-2"
        ).all()
        assert rows == []
        mock_bt.add_task.assert_called_once()


# ---------------------------------------------------------------------------
# Standalone (no session, no background_tasks)
# ---------------------------------------------------------------------------


class TestStandaloneSessionPath:
    """When no session and no background_tasks are given, a new session is opened."""

    def test_standalone_calls_emit_with_new_session(self) -> None:
        from skillmeat.core.bom.event_emitter import emit_activity_event

        with patch(
            "skillmeat.core.bom.event_emitter._emit_with_new_session"
        ) as mock_emit:
            emit_activity_event(
                artifact_id="skill:solo",
                event_type="create",
                actor_id="sys",
            )

        mock_emit.assert_called_once_with(
            artifact_id="skill:solo",
            event_type="create",
            actor_id="sys",
            owner_type="user",
            diff_json=None,
            content_hash=None,
        )
