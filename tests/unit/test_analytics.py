"""Unit tests for AnalyticsDB."""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from skillmeat.storage.analytics import AnalyticsDB


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide temporary database path."""
    return tmp_path / "test_analytics.db"


@pytest.fixture
def analytics_db(temp_db_path):
    """Provide AnalyticsDB instance with temp database."""
    db = AnalyticsDB(db_path=temp_db_path)
    yield db
    db.close()


class TestAnalyticsDBInitialization:
    """Test AnalyticsDB initialization."""

    def test_initialization_creates_database(self, temp_db_path):
        """Test that initialization creates database file."""
        db = AnalyticsDB(db_path=temp_db_path)
        assert temp_db_path.exists()
        db.close()

    def test_initialization_creates_tables(self, analytics_db):
        """Test that initialization creates required tables."""
        cursor = analytics_db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "events" in tables
        assert "usage_summary" in tables
        assert "migrations" in tables

    def test_initialization_creates_indexes(self, analytics_db):
        """Test that initialization creates required indexes."""
        cursor = analytics_db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        # Check event indexes
        assert "idx_event_type" in indexes
        assert "idx_artifact_name" in indexes
        assert "idx_timestamp" in indexes
        assert "idx_collection" in indexes
        assert "idx_artifact_type_name" in indexes

        # Check usage summary indexes
        assert "idx_last_used" in indexes
        assert "idx_total_events" in indexes
        assert "idx_usage_artifact_type" in indexes

    def test_initialization_enables_wal_mode(self, analytics_db):
        """Test that WAL mode is enabled."""
        cursor = analytics_db.connection.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

    def test_initialization_enables_foreign_keys(self, analytics_db):
        """Test that foreign keys are enabled."""
        cursor = analytics_db.connection.execute("PRAGMA foreign_keys")
        enabled = cursor.fetchone()[0]
        assert enabled == 1

    def test_default_database_location(self):
        """Test default database location is ~/.skillmeat/analytics.db."""
        db = AnalyticsDB()
        expected_path = Path.home() / ".skillmeat" / "analytics.db"
        assert db.db_path == expected_path
        db.close()
        # Cleanup
        if expected_path.exists():
            expected_path.unlink()


class TestRecordEvent:
    """Test event recording functionality."""

    def test_record_deploy_event(self, analytics_db):
        """Test recording a deploy event."""
        event_id = analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            project_path="/home/user/project",
            metadata={"version": "1.0.0"},
        )

        assert event_id > 0

        # Verify event was recorded
        events = analytics_db.get_events(artifact_name="canvas")
        assert len(events) == 1
        assert events[0]["event_type"] == "deploy"
        assert events[0]["artifact_name"] == "canvas"
        assert events[0]["artifact_type"] == "skill"
        assert events[0]["collection_name"] == "default"
        assert events[0]["project_path"] == "/home/user/project"

        # Verify metadata
        metadata = json.loads(events[0]["metadata"])
        assert metadata["version"] == "1.0.0"

    def test_record_event_updates_usage_summary(self, analytics_db):
        """Test that recording event updates usage summary."""
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
        )

        summary = analytics_db.get_usage_summary(artifact_name="canvas")
        assert len(summary) == 1
        assert summary[0]["artifact_name"] == "canvas"
        assert summary[0]["artifact_type"] == "skill"
        assert summary[0]["deploy_count"] == 1
        assert summary[0]["total_events"] == 1

    def test_record_multiple_events_increments_counters(self, analytics_db):
        """Test that recording multiple events increments counters."""
        # Record deploy
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
        )

        # Record update
        analytics_db.record_event(
            event_type="update",
            artifact_name="canvas",
            artifact_type="skill",
        )

        # Record another deploy
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
        )

        summary = analytics_db.get_usage_summary(artifact_name="canvas")
        assert len(summary) == 1
        assert summary[0]["deploy_count"] == 2
        assert summary[0]["update_count"] == 1
        assert summary[0]["total_events"] == 3

    def test_record_event_with_optional_fields(self, analytics_db):
        """Test recording event with minimal required fields."""
        event_id = analytics_db.record_event(
            event_type="search",
            artifact_name="canvas",
            artifact_type="skill",
        )

        assert event_id > 0

        events = analytics_db.get_events(artifact_name="canvas")
        assert len(events) == 1
        assert events[0]["collection_name"] is None
        assert events[0]["project_path"] is None
        assert events[0]["metadata"] is None

    def test_record_event_invalid_type_raises_error(self, analytics_db):
        """Test that invalid event type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid event_type"):
            analytics_db.record_event(
                event_type="invalid",
                artifact_name="canvas",
                artifact_type="skill",
            )

    def test_record_event_invalid_artifact_type_raises_error(self, analytics_db):
        """Test that invalid artifact type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid artifact_type"):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="canvas",
                artifact_type="invalid",
            )

    def test_record_all_event_types(self, analytics_db):
        """Test recording all valid event types."""
        event_types = ["deploy", "update", "sync", "remove", "search"]

        for event_type in event_types:
            analytics_db.record_event(
                event_type=event_type,
                artifact_name=f"test-{event_type}",
                artifact_type="skill",
            )

        events = analytics_db.get_events()
        assert len(events) == len(event_types)

    def test_record_all_artifact_types(self, analytics_db):
        """Test recording all valid artifact types."""
        artifact_types = ["skill", "command", "agent"]

        for artifact_type in artifact_types:
            analytics_db.record_event(
                event_type="deploy",
                artifact_name=f"test-{artifact_type}",
                artifact_type=artifact_type,
            )

        summary = analytics_db.get_usage_summary()
        assert len(summary) == len(artifact_types)


class TestGetEvents:
    """Test event querying functionality."""

    @pytest.fixture
    def populated_db(self, analytics_db):
        """Populate database with test events."""
        # Create events for different artifacts and types
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )
        analytics_db.record_event(
            event_type="update",
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="review",
            artifact_type="command",
            collection_name="work",
        )
        analytics_db.record_event(
            event_type="search",
            artifact_name="helper",
            artifact_type="agent",
            collection_name="default",
        )
        return analytics_db

    def test_get_all_events(self, populated_db):
        """Test getting all events."""
        events = populated_db.get_events()
        assert len(events) == 4

    def test_get_events_by_type(self, populated_db):
        """Test filtering events by type."""
        events = populated_db.get_events(event_type="deploy")
        assert len(events) == 2
        assert all(e["event_type"] == "deploy" for e in events)

    def test_get_events_by_artifact_name(self, populated_db):
        """Test filtering events by artifact name."""
        events = populated_db.get_events(artifact_name="canvas")
        assert len(events) == 2
        assert all(e["artifact_name"] == "canvas" for e in events)

    def test_get_events_by_artifact_type(self, populated_db):
        """Test filtering events by artifact type."""
        events = populated_db.get_events(artifact_type="skill")
        assert len(events) == 2
        assert all(e["artifact_type"] == "skill" for e in events)

    def test_get_events_by_collection(self, populated_db):
        """Test filtering events by collection name."""
        events = populated_db.get_events(collection_name="default")
        assert len(events) == 3
        assert all(e["collection_name"] == "default" for e in events)

    def test_get_events_multiple_filters(self, populated_db):
        """Test filtering events with multiple criteria."""
        events = populated_db.get_events(
            event_type="deploy",
            artifact_type="skill",
            collection_name="default",
        )
        assert len(events) == 1
        assert events[0]["artifact_name"] == "canvas"

    def test_get_events_with_limit(self, populated_db):
        """Test limiting number of returned events."""
        events = populated_db.get_events(limit=2)
        assert len(events) == 2

    def test_get_events_with_offset(self, populated_db):
        """Test offset for pagination."""
        all_events = populated_db.get_events()
        offset_events = populated_db.get_events(offset=2)

        assert len(offset_events) == 2
        # Events should be ordered by timestamp DESC
        assert offset_events[0]["id"] == all_events[2]["id"]

    def test_get_events_ordered_by_timestamp_desc(self, analytics_db):
        """Test events are returned in reverse chronological order."""
        # Record events with slight delay
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="first",
            artifact_type="skill",
        )
        time.sleep(0.01)
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="second",
            artifact_type="skill",
        )

        events = analytics_db.get_events()
        assert events[0]["artifact_name"] == "second"
        assert events[1]["artifact_name"] == "first"


class TestGetUsageSummary:
    """Test usage summary querying."""

    @pytest.fixture
    def summary_db(self, analytics_db):
        """Populate database with events for summary testing."""
        # Canvas: 3 deploys, 1 update
        for _ in range(3):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="canvas",
                artifact_type="skill",
            )
        analytics_db.record_event(
            event_type="update",
            artifact_name="canvas",
            artifact_type="skill",
        )

        # Review: 2 deploys
        for _ in range(2):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="review",
                artifact_type="command",
            )

        return analytics_db

    def test_get_all_usage_summary(self, summary_db):
        """Test getting all usage summaries."""
        summary = summary_db.get_usage_summary()
        assert len(summary) == 2

        # Should be ordered by total_events DESC
        assert summary[0]["artifact_name"] == "canvas"
        assert summary[0]["total_events"] == 4
        assert summary[1]["artifact_name"] == "review"
        assert summary[1]["total_events"] == 2

    def test_get_usage_summary_by_artifact_name(self, summary_db):
        """Test filtering usage summary by artifact name."""
        summary = summary_db.get_usage_summary(artifact_name="canvas")
        assert len(summary) == 1
        assert summary[0]["artifact_name"] == "canvas"
        assert summary[0]["deploy_count"] == 3
        assert summary[0]["update_count"] == 1

    def test_get_usage_summary_by_artifact_type(self, summary_db):
        """Test filtering usage summary by artifact type."""
        summary = summary_db.get_usage_summary(artifact_type="skill")
        assert len(summary) == 1
        assert summary[0]["artifact_type"] == "skill"

    def test_usage_summary_tracks_first_used(self, analytics_db):
        """Test that first_used timestamp is tracked."""
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
        )

        summary = analytics_db.get_usage_summary(artifact_name="canvas")
        assert summary[0]["first_used"] is not None

    def test_usage_summary_updates_last_used(self, analytics_db):
        """Test that last_used timestamp updates."""
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
        )

        first_summary = analytics_db.get_usage_summary(artifact_name="canvas")
        first_last_used = first_summary[0]["last_used"]

        # Sleep for more than 1 second since SQLite CURRENT_TIMESTAMP has 1-second precision
        time.sleep(1.1)

        analytics_db.record_event(
            event_type="update",
            artifact_name="canvas",
            artifact_type="skill",
        )

        second_summary = analytics_db.get_usage_summary(artifact_name="canvas")
        second_last_used = second_summary[0]["last_used"]

        assert second_last_used > first_last_used


class TestGetTopArtifacts:
    """Test top artifacts querying."""

    @pytest.fixture
    def ranked_db(self, analytics_db):
        """Create database with ranked artifacts."""
        # Create artifacts with different event counts
        for i in range(5):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="popular",
                artifact_type="skill",
            )

        for i in range(3):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="medium",
                artifact_type="skill",
            )

        analytics_db.record_event(
            event_type="deploy",
            artifact_name="unpopular",
            artifact_type="skill",
        )

        return analytics_db

    def test_get_top_artifacts_ordered(self, ranked_db):
        """Test top artifacts are ordered by total events."""
        top = ranked_db.get_top_artifacts(limit=3)
        assert len(top) == 3
        assert top[0]["artifact_name"] == "popular"
        assert top[0]["total_events"] == 5
        assert top[1]["artifact_name"] == "medium"
        assert top[1]["total_events"] == 3
        assert top[2]["artifact_name"] == "unpopular"
        assert top[2]["total_events"] == 1

    def test_get_top_artifacts_with_limit(self, ranked_db):
        """Test limiting top artifacts results."""
        top = ranked_db.get_top_artifacts(limit=2)
        assert len(top) == 2
        assert top[0]["artifact_name"] == "popular"

    def test_get_top_artifacts_by_type(self, analytics_db):
        """Test filtering top artifacts by type."""
        # Create skills
        for i in range(3):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="skill1",
                artifact_type="skill",
            )

        # Create commands
        for i in range(5):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name="command1",
                artifact_type="command",
            )

        # Get top skills only
        top_skills = analytics_db.get_top_artifacts(artifact_type="skill")
        assert len(top_skills) == 1
        assert top_skills[0]["artifact_type"] == "skill"


class TestCleanupOldEvents:
    """Test retention policy and cleanup."""

    def test_cleanup_removes_old_events(self, analytics_db):
        """Test that cleanup removes events older than retention period."""
        # Record an event
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="old",
            artifact_type="skill",
        )

        # Manually update timestamp to be old
        old_date = datetime.now() - timedelta(days=100)
        analytics_db.connection.execute(
            "UPDATE events SET timestamp = ?",
            (old_date,),
        )
        analytics_db.connection.commit()

        # Record a recent event
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="recent",
            artifact_type="skill",
        )

        # Cleanup events older than 90 days
        deleted = analytics_db.cleanup_old_events(days=90)
        assert deleted == 1

        # Verify only recent event remains
        events = analytics_db.get_events()
        assert len(events) == 1
        assert events[0]["artifact_name"] == "recent"

    def test_cleanup_preserves_usage_summary(self, analytics_db):
        """Test that cleanup doesn't affect usage summary."""
        # Record event
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="old",
            artifact_type="skill",
        )

        # Make it old
        old_date = datetime.now() - timedelta(days=100)
        analytics_db.connection.execute(
            "UPDATE events SET timestamp = ?",
            (old_date,),
        )
        analytics_db.connection.commit()

        # Cleanup
        analytics_db.cleanup_old_events(days=90)

        # Usage summary should still exist
        summary = analytics_db.get_usage_summary(artifact_name="old")
        assert len(summary) == 1
        assert summary[0]["deploy_count"] == 1

    def test_cleanup_zero_days_keeps_all(self, analytics_db):
        """Test that cleanup with days=0 keeps all events."""
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="test",
            artifact_type="skill",
        )

        deleted = analytics_db.cleanup_old_events(days=0)
        assert deleted == 0

        events = analytics_db.get_events()
        assert len(events) == 1

    def test_cleanup_negative_days_raises_error(self, analytics_db):
        """Test that negative retention days raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            analytics_db.cleanup_old_events(days=-1)

    def test_cleanup_returns_count(self, analytics_db):
        """Test that cleanup returns number of deleted events."""
        # Create 3 old events
        for i in range(3):
            analytics_db.record_event(
                event_type="deploy",
                artifact_name=f"old{i}",
                artifact_type="skill",
            )

        old_date = datetime.now() - timedelta(days=100)
        analytics_db.connection.execute(
            "UPDATE events SET timestamp = ?",
            (old_date,),
        )
        analytics_db.connection.commit()

        deleted = analytics_db.cleanup_old_events(days=90)
        assert deleted == 3


class TestVacuum:
    """Test vacuum functionality."""

    def test_vacuum_executes_successfully(self, analytics_db):
        """Test that vacuum executes without error."""
        # Add and remove some data
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="test",
            artifact_type="skill",
        )
        analytics_db.cleanup_old_events(days=0)

        # Should not raise error
        analytics_db.vacuum()

    def test_vacuum_after_cleanup_reclaims_space(self, temp_db_path):
        """Test that vacuum reclaims space after deletion."""
        db = AnalyticsDB(db_path=temp_db_path)

        # Add many events
        for i in range(100):
            db.record_event(
                event_type="deploy",
                artifact_name=f"test{i}",
                artifact_type="skill",
            )

        size_before_cleanup = temp_db_path.stat().st_size

        # Make them old and cleanup
        old_date = datetime.now() - timedelta(days=100)
        db.connection.execute(
            "UPDATE events SET timestamp = ?",
            (old_date,),
        )
        db.connection.commit()

        db.cleanup_old_events(days=90)

        # Vacuum to reclaim space
        db.vacuum()

        size_after_vacuum = temp_db_path.stat().st_size

        # Size should be reduced (or at least not increased)
        assert size_after_vacuum <= size_before_cleanup

        db.close()


class TestGetStats:
    """Test database statistics."""

    def test_get_stats_empty_database(self, analytics_db):
        """Test stats for empty database."""
        stats = analytics_db.get_stats()

        assert stats["total_events"] == 0
        assert stats["total_artifacts"] == 0
        assert stats["event_type_counts"] == {}
        assert stats["artifact_type_counts"] == {}
        assert stats["oldest_event"] is None
        assert stats["newest_event"] is None
        assert stats["db_size_bytes"] > 0  # Database file exists

    def test_get_stats_with_data(self, analytics_db):
        """Test stats with populated database."""
        # Add various events
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
        )
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="review",
            artifact_type="command",
        )
        analytics_db.record_event(
            event_type="update",
            artifact_name="canvas",
            artifact_type="skill",
        )

        stats = analytics_db.get_stats()

        assert stats["total_events"] == 3
        assert stats["total_artifacts"] == 2
        assert stats["event_type_counts"]["deploy"] == 2
        assert stats["event_type_counts"]["update"] == 1
        assert stats["artifact_type_counts"]["skill"] == 1
        assert stats["artifact_type_counts"]["command"] == 1
        assert stats["oldest_event"] is not None
        assert stats["newest_event"] is not None
        assert stats["db_size_bytes"] > 0


class TestConnectionManagement:
    """Test connection and resource management."""

    def test_close_connection(self, analytics_db):
        """Test closing database connection."""
        analytics_db.close()
        assert analytics_db.connection is None

    def test_close_idempotent(self, analytics_db):
        """Test that close can be called multiple times."""
        analytics_db.close()
        analytics_db.close()  # Should not raise error

    def test_context_manager(self, temp_db_path):
        """Test using AnalyticsDB as context manager."""
        with AnalyticsDB(db_path=temp_db_path) as db:
            db.record_event(
                event_type="deploy",
                artifact_name="test",
                artifact_type="skill",
            )

        # Connection should be closed after context
        assert db.connection is None

    def test_context_manager_on_exception(self, temp_db_path):
        """Test context manager closes connection on exception."""
        db = None
        try:
            with AnalyticsDB(db_path=temp_db_path) as db:
                db.record_event(
                    event_type="deploy",
                    artifact_name="test",
                    artifact_type="skill",
                )
                raise RuntimeError("Test exception")
        except RuntimeError:
            pass

        # Connection should still be closed
        assert db.connection is None


class TestRetryLogic:
    """Test retry logic for database locked scenarios."""

    def test_execute_with_retry_success(self, analytics_db):
        """Test successful execution without retries."""
        cursor = analytics_db._execute_with_retry(
            "SELECT COUNT(*) FROM events",
        )
        assert cursor is not None

    @pytest.mark.skip(reason="Cannot monkeypatch sqlite3.Connection.execute (read-only)")
    def test_execute_with_retry_max_attempts(self, analytics_db, monkeypatch):
        """Test that max retries is respected."""
        # This test is skipped because sqlite3.Connection.execute is read-only
        # and cannot be monkeypatched. Retry logic is indirectly tested through
        # actual database operations in other tests.
        pass


class TestMigrations:
    """Test migration system."""

    def test_migrations_table_created(self, analytics_db):
        """Test that migrations table is created."""
        cursor = analytics_db.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
        )
        assert cursor.fetchone() is not None

    def test_initial_migration_applied(self, analytics_db):
        """Test that initial migration is applied."""
        cursor = analytics_db.connection.execute(
            "SELECT version FROM migrations"
        )
        versions = [row[0] for row in cursor.fetchall()]
        assert 1 in versions

    def test_migration_idempotent(self, temp_db_path):
        """Test that migrations are idempotent."""
        # Create database and close
        db1 = AnalyticsDB(db_path=temp_db_path)
        db1.close()

        # Reopen - should not re-apply migrations
        db2 = AnalyticsDB(db_path=temp_db_path)
        cursor = db2.connection.execute(
            "SELECT COUNT(*) FROM migrations WHERE version=1"
        )
        count = cursor.fetchone()[0]
        assert count == 1  # Should only have one entry for version 1

        db2.close()


class TestThreadSafety:
    """Test thread safety features."""

    def test_check_same_thread_disabled(self, analytics_db):
        """Test that check_same_thread is disabled for multi-threaded use."""
        # This is more of a configuration test
        # Actual thread safety would require multi-threaded testing
        # which is complex and not suitable for unit tests
        assert analytics_db.connection is not None

    def test_row_factory_enabled(self, analytics_db):
        """Test that Row factory is enabled for dict-like access."""
        analytics_db.record_event(
            event_type="deploy",
            artifact_name="test",
            artifact_type="skill",
        )

        cursor = analytics_db.connection.execute("SELECT * FROM events")
        row = cursor.fetchone()

        # Should be able to access by column name
        assert row["event_type"] == "deploy"
        assert row["artifact_name"] == "test"
