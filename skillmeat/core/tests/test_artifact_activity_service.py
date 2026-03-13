"""Unit tests for ArtifactActivityService.

Tests cover:

- record_event delegates to repository with all arguments
- record_event_fire_and_forget adds a callable to BackgroundTasks
- record_event_fire_and_forget catches repository exceptions and logs warning
- list_events delegates all filter arguments to repository
- get_event delegates to repository
- count_events delegates filter arguments to repository
- get_provenance_slice delegates to repository's list_provenance_slice
- compute_diff with changed keys
- compute_diff with added keys
- compute_diff with removed keys
- compute_diff with a mix of changed/added/removed keys
- compute_diff returns None for identical states
- compute_diff returns None for two empty dicts
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from skillmeat.core.bom.history import ArtifactActivityService


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_event(
    event_id: int = 1,
    artifact_id: str = "skill:canvas",
    event_type: str = "create",
) -> MagicMock:
    """Return a lightweight mock that looks like an ArtifactHistoryEvent."""
    evt = MagicMock()
    evt.id = event_id
    evt.artifact_id = artifact_id
    evt.event_type = event_type
    return evt


@pytest.fixture()
def mock_repo() -> MagicMock:
    """Return a MagicMock configured with the IArtifactActivityRepository surface."""
    repo = MagicMock()
    # Default return values for the most common calls
    repo.create_event.return_value = _make_event()
    repo.list_events.return_value = []
    repo.get_event.return_value = None
    repo.count_events.return_value = 0
    repo.list_provenance_slice.return_value = []
    return repo


@pytest.fixture()
def svc(mock_repo: MagicMock) -> ArtifactActivityService:
    return ArtifactActivityService(repository=mock_repo)


# ---------------------------------------------------------------------------
# record_event
# ---------------------------------------------------------------------------


class TestRecordEvent:
    def test_delegates_all_args(self, svc: ArtifactActivityService, mock_repo: MagicMock) -> None:
        event = _make_event(artifact_id="command:git-log", event_type="deploy")
        mock_repo.create_event.return_value = event

        result = svc.record_event(
            artifact_id="command:git-log",
            event_type="deploy",
            actor_id="user-42",
            owner_type="org",
            diff_json='{"changed":{}}',
            content_hash="abc123",
        )

        mock_repo.create_event.assert_called_once_with(
            artifact_id="command:git-log",
            event_type="deploy",
            actor_id="user-42",
            owner_type="org",
            diff_json='{"changed":{}}',
            content_hash="abc123",
        )
        assert result is event

    def test_defaults_for_optional_params(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        svc.record_event(artifact_id="skill:canvas", event_type="create")

        mock_repo.create_event.assert_called_once_with(
            artifact_id="skill:canvas",
            event_type="create",
            actor_id=None,
            owner_type="user",
            diff_json=None,
            content_hash=None,
        )

    def test_returns_repository_result(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        sentinel = _make_event(event_id=99)
        mock_repo.create_event.return_value = sentinel
        result = svc.record_event(artifact_id="agent:planner", event_type="update")
        assert result is sentinel


# ---------------------------------------------------------------------------
# record_event_fire_and_forget
# ---------------------------------------------------------------------------


class TestRecordEventFireAndForget:
    def test_adds_task_to_background_tasks(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        bg = MagicMock()  # stand-in for starlette.background.BackgroundTasks

        svc.record_event_fire_and_forget(
            background_tasks=bg,
            artifact_id="skill:canvas",
            event_type="create",
        )

        bg.add_task.assert_called_once()
        # The added task must be a callable
        task_fn = bg.add_task.call_args[0][0]
        assert callable(task_fn)

    def test_background_task_calls_record_event(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        bg = MagicMock()

        svc.record_event_fire_and_forget(
            background_tasks=bg,
            artifact_id="skill:canvas",
            event_type="sync",
            actor_id="sys",
            owner_type="system",
            diff_json='{"changed":{}}',
            content_hash="deadbeef",
        )

        # Execute the task inline to verify it calls the repo
        task_fn = bg.add_task.call_args[0][0]
        task_fn()

        mock_repo.create_event.assert_called_once_with(
            artifact_id="skill:canvas",
            event_type="sync",
            actor_id="sys",
            owner_type="system",
            diff_json='{"changed":{}}',
            content_hash="deadbeef",
        )

    def test_catches_exception_and_logs_warning(
        self, svc: ArtifactActivityService, mock_repo: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_repo.create_event.side_effect = RuntimeError("db unavailable")
        bg = MagicMock()

        svc.record_event_fire_and_forget(
            background_tasks=bg,
            artifact_id="skill:canvas",
            event_type="delete",
        )

        task_fn = bg.add_task.call_args[0][0]

        with caplog.at_level(logging.WARNING, logger="skillmeat.core.bom.history"):
            # Must NOT raise
            task_fn()

        assert any("db unavailable" in r.message or "db unavailable" in str(r.exc_info) for r in caplog.records), (
            "Expected warning log containing exception info"
        )

    def test_returns_none_immediately(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        bg = MagicMock()
        result = svc.record_event_fire_and_forget(
            background_tasks=bg,
            artifact_id="skill:canvas",
            event_type="create",
        )
        assert result is None


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------


class TestListEvents:
    def test_delegates_no_filters(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        mock_repo.list_events.return_value = []
        result = svc.list_events()
        mock_repo.list_events.assert_called_once_with(
            artifact_id=None,
            event_type=None,
            actor_id=None,
            owner_type=None,
            time_range=None,
            limit=100,
            offset=0,
        )
        assert result == []

    def test_delegates_all_filters(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        later = datetime(2026, 6, 1, tzinfo=timezone.utc)
        mock_repo.list_events.return_value = [_make_event()]

        result = svc.list_events(
            artifact_id="skill:canvas",
            event_type="deploy",
            actor_id="user-1",
            owner_type="org",
            time_range=(now, later),
            limit=50,
            offset=10,
        )

        mock_repo.list_events.assert_called_once_with(
            artifact_id="skill:canvas",
            event_type="deploy",
            actor_id="user-1",
            owner_type="org",
            time_range=(now, later),
            limit=50,
            offset=10,
        )
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_event
# ---------------------------------------------------------------------------


class TestGetEvent:
    def test_returns_event_when_found(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        evt = _make_event(event_id=7)
        mock_repo.get_event.return_value = evt
        result = svc.get_event(7)
        mock_repo.get_event.assert_called_once_with(7)
        assert result is evt

    def test_returns_none_when_not_found(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        mock_repo.get_event.return_value = None
        result = svc.get_event(9999)
        assert result is None


# ---------------------------------------------------------------------------
# count_events
# ---------------------------------------------------------------------------


class TestCountEvents:
    def test_delegates_no_filters(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        mock_repo.count_events.return_value = 42
        result = svc.count_events()
        mock_repo.count_events.assert_called_once_with(
            artifact_id=None,
            event_type=None,
            owner_type=None,
        )
        assert result == 42

    def test_delegates_with_filters(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        mock_repo.count_events.return_value = 3
        result = svc.count_events(
            artifact_id="skill:canvas",
            event_type="deploy",
            owner_type="user",
        )
        mock_repo.count_events.assert_called_once_with(
            artifact_id="skill:canvas",
            event_type="deploy",
            owner_type="user",
        )
        assert result == 3


# ---------------------------------------------------------------------------
# get_provenance_slice
# ---------------------------------------------------------------------------


class TestGetProvenanceSlice:
    def test_delegates_to_list_provenance_slice(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        since = datetime(2026, 1, 1, tzinfo=timezone.utc)
        until = datetime(2026, 12, 31, tzinfo=timezone.utc)
        events = [_make_event(event_id=i) for i in range(3)]
        mock_repo.list_provenance_slice.return_value = events

        result = svc.get_provenance_slice("skill:canvas", since=since, until=until)

        mock_repo.list_provenance_slice.assert_called_once_with(
            artifact_id="skill:canvas",
            since=since,
            until=until,
        )
        assert result is events

    def test_delegates_without_time_bounds(
        self, svc: ArtifactActivityService, mock_repo: MagicMock
    ) -> None:
        mock_repo.list_provenance_slice.return_value = []
        svc.get_provenance_slice("agent:planner")
        mock_repo.list_provenance_slice.assert_called_once_with(
            artifact_id="agent:planner",
            since=None,
            until=None,
        )


# ---------------------------------------------------------------------------
# compute_diff (static method)
# ---------------------------------------------------------------------------


class TestComputeDiff:
    def test_changed_keys(self) -> None:
        before = {"version": "1.0", "name": "canvas"}
        after = {"version": "2.0", "name": "canvas"}
        result = ArtifactActivityService.compute_diff(before, after)
        assert result is not None
        data = json.loads(result)
        assert "changed" in data
        assert data["changed"]["version"] == {"old": "1.0", "new": "2.0"}
        assert "name" not in data.get("changed", {})
        assert "added" not in data
        assert "removed" not in data

    def test_added_keys(self) -> None:
        before: dict = {"name": "canvas"}
        after = {"name": "canvas", "description": "a skill"}
        result = ArtifactActivityService.compute_diff(before, after)
        assert result is not None
        data = json.loads(result)
        assert "added" in data
        assert data["added"]["description"] == "a skill"
        assert "changed" not in data
        assert "removed" not in data

    def test_removed_keys(self) -> None:
        before = {"name": "canvas", "deprecated": True}
        after = {"name": "canvas"}
        result = ArtifactActivityService.compute_diff(before, after)
        assert result is not None
        data = json.loads(result)
        assert "removed" in data
        assert data["removed"]["deprecated"] is True
        assert "changed" not in data
        assert "added" not in data

    def test_mixed_changes(self) -> None:
        before = {"version": "1.0", "author": "alice", "legacy": "yes"}
        after = {"version": "2.0", "author": "alice", "license": "MIT"}
        result = ArtifactActivityService.compute_diff(before, after)
        assert result is not None
        data = json.loads(result)
        assert data["changed"]["version"] == {"old": "1.0", "new": "2.0"}
        assert data["added"]["license"] == "MIT"
        assert data["removed"]["legacy"] == "yes"
        # unchanged key 'author' must not appear
        assert "author" not in data.get("changed", {})
        assert "author" not in data.get("added", {})
        assert "author" not in data.get("removed", {})

    def test_identical_states_return_none(self) -> None:
        state = {"version": "1.0", "name": "canvas", "tags": ["a", "b"]}
        result = ArtifactActivityService.compute_diff(state, state.copy())
        assert result is None

    def test_both_empty_return_none(self) -> None:
        result = ArtifactActivityService.compute_diff({}, {})
        assert result is None

    def test_output_is_compact_json(self) -> None:
        before = {"x": 1}
        after = {"x": 2}
        result = ArtifactActivityService.compute_diff(before, after)
        assert result is not None
        # Compact JSON uses no spaces after separators
        assert " " not in result

    def test_non_serialisable_values_handled(self) -> None:
        """compute_diff must not raise for non-trivially-serialisable values."""
        before = {"ts": datetime(2026, 1, 1)}
        after = {"ts": datetime(2026, 6, 1)}
        result = ArtifactActivityService.compute_diff(before, after)
        assert result is not None
        # Should produce valid JSON (datetime coerced via default=str)
        data = json.loads(result)
        assert "changed" in data
