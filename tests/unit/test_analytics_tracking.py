"""Unit tests for analytics event tracking (P4-002)."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.analytics import EventBuffer, EventTracker
from skillmeat.storage.analytics import AnalyticsDB


class TestEventBuffer:
    """Test EventBuffer class for buffering failed events."""

    def test_buffer_initialization(self):
        """Test buffer initializes with correct max size."""
        buffer = EventBuffer(max_size=50)
        assert len(buffer) == 0
        assert buffer.max_size == 50

    def test_add_event_to_buffer(self):
        """Test adding event to buffer."""
        buffer = EventBuffer()
        buffer.add(
            event_type="deploy",
            artifact_name="test-skill",
            artifact_type="skill",
            collection_name="default",
        )

        assert len(buffer) == 1

    def test_buffer_max_size_enforcement(self):
        """Test buffer enforces max size."""
        buffer = EventBuffer(max_size=3)

        for i in range(5):
            buffer.add(
                event_type="deploy",
                artifact_name=f"skill-{i}",
                artifact_type="skill",
            )

        # Should only keep last 3 events
        assert len(buffer) == 3

    def test_get_pending_events(self):
        """Test retrieving pending events."""
        buffer = EventBuffer()
        buffer.add(
            event_type="deploy",
            artifact_name="skill-1",
            artifact_type="skill",
        )
        buffer.add(
            event_type="update",
            artifact_name="skill-2",
            artifact_type="skill",
        )

        pending = buffer.get_pending()
        assert len(pending) == 2
        assert all(isinstance(event_id, int) and isinstance(event, dict) for event_id, event in pending)

    def test_mark_success_removes_event(self):
        """Test marking event as successful removes it from buffer."""
        buffer = EventBuffer()
        buffer.add(
            event_type="deploy",
            artifact_name="test-skill",
            artifact_type="skill",
        )

        pending = buffer.get_pending()
        event_id, _ = pending[0]

        buffer.mark_success(event_id)
        assert len(buffer) == 0

    def test_mark_failure_increments_retry_count(self):
        """Test marking event as failed increments retry count."""
        buffer = EventBuffer()
        buffer.add(
            event_type="deploy",
            artifact_name="test-skill",
            artifact_type="skill",
        )

        pending = buffer.get_pending()
        event_id, _ = pending[0]

        # First failure
        should_retry = buffer.mark_failure(event_id)
        assert should_retry is True
        assert buffer.get_retry_count(event_id) == 1
        assert len(buffer) == 1

    def test_mark_failure_max_retries_removes_event(self):
        """Test event is removed after max retries."""
        buffer = EventBuffer()
        buffer.add(
            event_type="deploy",
            artifact_name="test-skill",
            artifact_type="skill",
        )

        pending = buffer.get_pending()
        event_id, _ = pending[0]

        # Exhaust retries
        for i in range(3):
            should_retry = buffer.mark_failure(event_id)
            if i < 2:
                assert should_retry is True
            else:
                assert should_retry is False

        # Event should be removed after max retries
        assert len(buffer) == 0

    def test_clear_buffer(self):
        """Test clearing all buffered events."""
        buffer = EventBuffer()
        for i in range(5):
            buffer.add(
                event_type="deploy",
                artifact_name=f"skill-{i}",
                artifact_type="skill",
            )

        assert len(buffer) == 5

        buffer.clear()
        assert len(buffer) == 0


class TestEventTrackerInitialization:
    """Test EventTracker initialization and configuration."""

    def test_tracker_initialized_when_analytics_enabled(self, tmp_path):
        """Test tracker initializes successfully when analytics enabled."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.return_value = tmp_path / "analytics.db"

            tracker = EventTracker()
            assert tracker._enabled is True
            assert tracker.db is not None

    def test_tracker_disabled_when_analytics_disabled(self):
        """Test tracker is disabled when analytics disabled in config."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = False

            tracker = EventTracker()
            assert tracker._enabled is False
            assert tracker.db is None

    def test_tracker_graceful_degradation_on_db_error(self):
        """Test tracker gracefully degrades when database unavailable."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.side_effect = Exception("DB error")

            tracker = EventTracker()
            assert tracker._enabled is False
            assert tracker.db is None


class TestEventTracking:
    """Test event tracking methods."""

    @pytest.fixture
    def mock_tracker(self):
        """Create EventTracker with mocked database."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.return_value = Path(tempfile.mkdtemp()) / "test.db"

            tracker = EventTracker(config_manager=config_instance)
            tracker.db = Mock(spec=AnalyticsDB)
            tracker._enabled = True

            yield tracker

    def test_track_deploy_event(self, mock_tracker):
        """Test tracking deploy event."""
        result = mock_tracker.track_deploy(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            project_path="/home/user/project",
            version="1.0.0",
            sha="abc123",
            success=True,
        )

        assert result is True
        mock_tracker.db.record_event.assert_called_once()
        call_args = mock_tracker.db.record_event.call_args[1]
        assert call_args["event_type"] == "deploy"
        assert call_args["artifact_name"] == "canvas"
        assert call_args["metadata"]["success"] is True
        assert call_args["metadata"]["version"] == "1.0.0"

    def test_track_update_event(self, mock_tracker):
        """Test tracking update event."""
        result = mock_tracker.track_update(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            strategy="overwrite",
            version_before="1.0.0",
            version_after="1.1.0",
            conflicts_detected=0,
            rollback=False,
        )

        assert result is True
        mock_tracker.db.record_event.assert_called_once()
        call_args = mock_tracker.db.record_event.call_args[1]
        assert call_args["event_type"] == "update"
        assert call_args["metadata"]["strategy"] == "overwrite"
        assert call_args["metadata"]["version_before"] == "1.0.0"
        assert call_args["metadata"]["version_after"] == "1.1.0"

    def test_track_sync_event(self, mock_tracker):
        """Test tracking sync event."""
        result = mock_tracker.track_sync(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            sync_type="overwrite",
            result="success",
            sha_before="old123",
            sha_after="new456",
            conflicts_detected=0,
        )

        assert result is True
        mock_tracker.db.record_event.assert_called_once()
        call_args = mock_tracker.db.record_event.call_args[1]
        assert call_args["event_type"] == "sync"
        assert call_args["metadata"]["sync_type"] == "overwrite"
        assert call_args["metadata"]["result"] == "success"

    def test_track_remove_event(self, mock_tracker):
        """Test tracking remove event."""
        result = mock_tracker.track_remove(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            reason="user_action",
            from_project=False,
        )

        assert result is True
        mock_tracker.db.record_event.assert_called_once()
        call_args = mock_tracker.db.record_event.call_args[1]
        assert call_args["event_type"] == "remove"
        assert call_args["metadata"]["reason"] == "user_action"
        assert call_args["metadata"]["from_project"] is False

    def test_track_search_event(self, mock_tracker):
        """Test tracking search event."""
        result = mock_tracker.track_search(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            query="design patterns",
            search_type="both",
            score=8.5,
            rank=1,
            total_results=5,
        )

        assert result is True
        mock_tracker.db.record_event.assert_called_once()
        call_args = mock_tracker.db.record_event.call_args[1]
        assert call_args["event_type"] == "search"
        assert call_args["metadata"]["query"] == "design patterns"
        assert call_args["metadata"]["score"] == 8.5
        assert call_args["metadata"]["rank"] == 1

    def test_tracking_returns_false_when_disabled(self):
        """Test tracking returns False when analytics disabled."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = False

            tracker = EventTracker()
            result = tracker.track_deploy(
                artifact_name="canvas",
                artifact_type="skill",
                collection_name="default",
            )

            assert result is False


class TestPathRedaction:
    """Test privacy-safe path redaction."""

    @pytest.fixture
    def tracker(self):
        """Create EventTracker for testing path redaction."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = False

            yield EventTracker(config_manager=config_instance)

    def test_redact_path_under_home(self, tracker):
        """Test path redaction for paths under home directory."""
        home = Path.home()
        test_path = str(home / "projects" / "myapp")

        redacted = tracker._redact_path(test_path)
        assert redacted == "~/projects/myapp"

    def test_redact_path_outside_home(self, tracker):
        """Test path redaction for paths outside home returns filename."""
        test_path = "/opt/system/myapp"

        redacted = tracker._redact_path(test_path)
        assert redacted == "myapp"

    def test_redact_path_none(self, tracker):
        """Test redacting None returns None."""
        assert tracker._redact_path(None) is None

    def test_redact_paths_in_metadata(self, tracker):
        """Test recursive path redaction in metadata dict."""
        home = Path.home()
        metadata = {
            "project_path": str(home / "projects" / "app"),
            "nested": {
                "path": "/opt/system/file.txt",
            },
            "version": "1.0.0",
        }

        redacted = tracker._redact_paths(metadata)
        assert redacted["project_path"] == "~/projects/app"
        assert redacted["nested"]["path"] == "file.txt"
        assert redacted["version"] == "1.0.0"

    def test_redact_paths_none(self, tracker):
        """Test redacting None metadata returns None."""
        assert tracker._redact_paths(None) is None


class TestRetryLogic:
    """Test retry logic and buffering."""

    @pytest.fixture
    def tracker_with_failing_db(self):
        """Create tracker with database that fails initially."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.return_value = Path(tempfile.mkdtemp()) / "test.db"

            tracker = EventTracker(config_manager=config_instance)
            tracker.db = Mock(spec=AnalyticsDB)
            tracker._enabled = True

            yield tracker

    def test_retry_on_database_error(self, tracker_with_failing_db):
        """Test event is retried on database error."""
        # Make first 2 attempts fail, 3rd succeed
        tracker_with_failing_db.db.record_event.side_effect = [
            Exception("DB locked"),
            Exception("DB locked"),
            None,  # Success on 3rd attempt
        ]

        result = tracker_with_failing_db.track_deploy(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )

        # Should succeed after retries
        assert result is True
        assert tracker_with_failing_db.db.record_event.call_count == 3

    def test_event_buffered_after_max_retries(self, tracker_with_failing_db):
        """Test event is buffered after exhausting retries."""
        # All attempts fail
        tracker_with_failing_db.db.record_event.side_effect = Exception("DB locked")

        result = tracker_with_failing_db.track_deploy(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )

        # Should fail and buffer event
        assert result is False
        assert len(tracker_with_failing_db._buffer) == 1
        assert tracker_with_failing_db.db.record_event.call_count == 3  # Max retries

    def test_retry_buffered_events(self, tracker_with_failing_db):
        """Test retrying buffered events."""
        # Fail first, then succeed
        tracker_with_failing_db.db.record_event.side_effect = [
            Exception("DB locked"),
            Exception("DB locked"),
            Exception("DB locked"),
            None,  # Success on retry
        ]

        # First call will buffer event
        result1 = tracker_with_failing_db.track_deploy(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )
        assert result1 is False
        assert len(tracker_with_failing_db._buffer) == 1

        # Retry buffered events
        success_count = tracker_with_failing_db.retry_buffered_events()

        assert success_count == 1
        assert len(tracker_with_failing_db._buffer) == 0


class TestContextManager:
    """Test EventTracker context manager."""

    def test_context_manager_closes_connection(self):
        """Test context manager closes database connection."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.return_value = Path(tempfile.mkdtemp()) / "test.db"

            mock_db = Mock(spec=AnalyticsDB)

            with EventTracker(config_manager=config_instance) as tracker:
                tracker.db = mock_db
                tracker._enabled = True
                pass  # Do nothing, just test context manager

            # After exiting context, db.close() should have been called
            mock_db.close.assert_called_once()

    def test_context_manager_retries_buffered_on_close(self):
        """Test context manager retries buffered events on close."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.return_value = Path(tempfile.mkdtemp()) / "test.db"

            mock_db = Mock(spec=AnalyticsDB)

            with EventTracker(config_manager=config_instance) as tracker:
                tracker.db = mock_db
                tracker._enabled = True

                # Add event to buffer
                tracker._buffer.add(
                    event_type="deploy",
                    artifact_name="test",
                    artifact_type="skill",
                )

            # Should have attempted to retry buffered events
            # (Will call db.record_event in retry_buffered_events)
            mock_db.record_event.assert_called()


class TestGracefulDegradation:
    """Test graceful degradation on errors."""

    def test_never_fails_primary_operation(self):
        """Test event tracking never fails the primary operation."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = True
            config_instance.get_analytics_db_path.return_value = Path(tempfile.mkdtemp()) / "test.db"

            tracker = EventTracker(config_manager=config_instance)
            tracker.db = Mock(spec=AnalyticsDB)
            tracker._enabled = True

            # Make database raise exception
            tracker.db.record_event.side_effect = Exception("Critical DB error")

            # Should not raise exception, just return False and buffer
            try:
                result = tracker.track_deploy(
                    artifact_name="canvas",
                    artifact_type="skill",
                    collection_name="default",
                )
                # Should fail gracefully
                assert result is False
            except Exception:
                pytest.fail("Event tracking should not raise exceptions")

    def test_buffer_size_reported(self):
        """Test buffer size can be queried."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = False

            tracker = EventTracker(config_manager=config_instance)
            tracker._buffer.add(
                event_type="deploy",
                artifact_name="test",
                artifact_type="skill",
            )

            assert tracker.get_buffer_size() == 1

    def test_buffer_can_be_cleared(self):
        """Test buffer can be manually cleared."""
        with patch("skillmeat.config.ConfigManager") as mock_config:
            config_instance = mock_config.return_value
            config_instance.is_analytics_enabled.return_value = False

            tracker = EventTracker(config_manager=config_instance)
            tracker._buffer.add(
                event_type="deploy",
                artifact_name="test",
                artifact_type="skill",
            )

            assert tracker.get_buffer_size() == 1

            tracker.clear_buffer()
            assert tracker.get_buffer_size() == 0
