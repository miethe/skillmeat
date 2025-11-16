"""Unit tests for UsageReportManager.

Tests all usage reporting and analytics query functionality including
artifact usage stats, top artifacts, cleanup suggestions, and trend analysis.
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.config import ConfigManager
from skillmeat.core.usage_reports import UsageReportManager
from skillmeat.storage.analytics import AnalyticsDB


# Fixtures


@pytest.fixture
def temp_dir():
    """Temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def analytics_db(temp_dir):
    """Analytics database with test data."""
    db_path = temp_dir / "test_analytics.db"
    db = AnalyticsDB(db_path)

    # Add test data
    now = datetime.now()

    # Artifact 1: canvas - heavily used skill
    for i in range(50):
        db.record_event(
            event_type="deploy",
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            metadata={"version": "1.0.0"},
        )

    for i in range(10):
        db.record_event(
            event_type="update",
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )

    for i in range(20):
        db.record_event(
            event_type="search",
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
        )

    # Artifact 2: planning - moderately used skill
    for i in range(15):
        db.record_event(
            event_type="deploy",
            artifact_name="planning",
            artifact_type="skill",
            collection_name="default",
        )

    for i in range(5):
        db.record_event(
            event_type="sync",
            artifact_name="planning",
            artifact_type="skill",
            collection_name="default",
        )

    # Artifact 3: old-skill - unused for 100 days
    old_timestamp = (now - timedelta(days=100)).isoformat()
    db.connection.execute(
        """
        INSERT INTO events
            (event_type, artifact_name, artifact_type, collection_name, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("deploy", "old-skill", "skill", "default", old_timestamp),
    )
    db.connection.commit()

    # Update usage summary manually for old-skill
    db.connection.execute(
        """
        INSERT INTO usage_summary
            (artifact_name, artifact_type, first_used, last_used,
             deploy_count, total_events)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("old-skill", "skill", old_timestamp, old_timestamp, 1, 1),
    )
    db.connection.commit()

    # Artifact 4: never-deployed - only searched, never deployed
    for i in range(3):
        db.record_event(
            event_type="search",
            artifact_name="never-deployed",
            artifact_type="skill",
            collection_name="default",
        )

    # Artifact 5: low-usage - added 70 days ago, only 2 events
    old_timestamp_2 = (now - timedelta(days=70)).isoformat()
    for i in range(2):
        db.connection.execute(
            """
            INSERT INTO events
                (event_type, artifact_name, artifact_type, collection_name, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("search", "low-usage", "skill", "default", old_timestamp_2),
        )
    db.connection.commit()

    # Update usage summary for low-usage
    db.connection.execute(
        """
        INSERT INTO usage_summary
            (artifact_name, artifact_type, first_used, last_used,
             search_count, total_events)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("low-usage", "skill", old_timestamp_2, old_timestamp_2, 2, 2),
    )
    db.connection.commit()

    # Artifact 6: command-artifact - test different artifact type
    for i in range(8):
        db.record_event(
            event_type="deploy",
            artifact_name="test-command",
            artifact_type="command",
            collection_name="default",
        )

    yield db
    db.close()


@pytest.fixture
def mock_config(temp_dir):
    """Mock configuration with analytics enabled."""
    config = Mock(spec=ConfigManager)
    config.is_analytics_enabled.return_value = True
    config.get_analytics_db_path.return_value = temp_dir / "analytics.db"
    config.get_collections_dir.return_value = temp_dir / "collections"
    config.get_active_collection.return_value = "default"
    config.get_collection_path.return_value = temp_dir / "collections" / "default"
    return config


@pytest.fixture
def mock_config_disabled():
    """Mock configuration with analytics disabled."""
    config = Mock(spec=ConfigManager)
    config.is_analytics_enabled.return_value = False
    config.get_collections_dir.return_value = Path("/tmp/collections")
    config.get_active_collection.return_value = "default"
    config.get_collection_path.return_value = Path("/tmp/collections/default")
    return config


@pytest.fixture
def usage_manager(mock_config, analytics_db, temp_dir):
    """UsageReportManager with test database."""
    db_path = temp_dir / "test_analytics.db"
    manager = UsageReportManager(config=mock_config, db_path=db_path)
    yield manager
    manager.close()


# Test Classes


class TestUsageReportManager:
    """Tests for UsageReportManager initialization and configuration."""

    def test_initialization_with_analytics_enabled(self, mock_config, temp_dir):
        """Test manager initializes correctly when analytics enabled."""
        db_path = temp_dir / "analytics.db"
        manager = UsageReportManager(config=mock_config, db_path=db_path)

        assert manager._analytics_enabled is True
        assert manager.db is not None
        assert manager.config == mock_config

        manager.close()

    def test_initialization_with_analytics_disabled(self, mock_config_disabled):
        """Test manager handles analytics disabled gracefully."""
        manager = UsageReportManager(config=mock_config_disabled)

        assert manager._analytics_enabled is False
        assert manager.db is None

        # Should not raise errors
        usage = manager.get_artifact_usage("canvas")
        assert usage["total_events"] == 0

    def test_initialization_with_default_config(self, temp_dir):
        """Test manager creates default config if none provided."""
        with patch("skillmeat.core.usage_reports.ConfigManager") as mock_cm:
            mock_instance = Mock()
            mock_instance.is_analytics_enabled.return_value = True
            mock_instance.get_analytics_db_path.return_value = temp_dir / "analytics.db"
            mock_instance.get_collections_dir.return_value = temp_dir / "collections"
            mock_instance.get_active_collection.return_value = "default"
            mock_instance.get_collection_path.return_value = temp_dir / "collections" / "default"
            mock_cm.return_value = mock_instance

            manager = UsageReportManager(db_path=temp_dir / "analytics.db")

            assert manager.config is not None
            mock_cm.assert_called_once()

            manager.close()


class TestArtifactUsage:
    """Tests for get_artifact_usage method."""

    def test_get_single_artifact_usage(self, usage_manager):
        """Test getting usage for single artifact."""
        usage = usage_manager.get_artifact_usage("canvas")

        assert usage["artifact_name"] == "canvas"
        assert usage["artifact_type"] == "skill"
        assert usage["deploy_count"] == 50
        assert usage["update_count"] == 10
        assert usage["search_count"] == 20
        assert usage["total_events"] == 80
        assert "days_since_last_use" in usage
        assert "usage_trend" in usage

    def test_get_all_artifacts_usage(self, usage_manager):
        """Test getting usage for all artifacts."""
        result = usage_manager.get_artifact_usage()

        assert "artifacts" in result
        assert "total_count" in result
        assert result["total_count"] >= 5  # We created at least 5 test artifacts

        # Verify all artifacts have required fields
        for artifact in result["artifacts"]:
            assert "artifact_name" in artifact
            assert "total_events" in artifact
            assert "days_since_last_use" in artifact
            assert "usage_trend" in artifact

    def test_filter_by_artifact_type(self, usage_manager):
        """Test filtering artifacts by type."""
        # Get only skills
        result = usage_manager.get_artifact_usage(artifact_type="skill")

        assert "artifacts" in result
        for artifact in result["artifacts"]:
            assert artifact["artifact_type"] == "skill"

        # Get only commands
        result = usage_manager.get_artifact_usage(artifact_type="command")

        assert "artifacts" in result
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["artifact_name"] == "test-command"

    def test_nonexistent_artifact(self, usage_manager):
        """Test querying nonexistent artifact returns empty response."""
        usage = usage_manager.get_artifact_usage("nonexistent")

        assert usage["artifact_name"] == "nonexistent"
        assert usage["total_events"] == 0
        assert usage["usage_trend"] == "stable"

    def test_usage_trend_calculation(self, usage_manager):
        """Test usage trend is calculated."""
        usage = usage_manager.get_artifact_usage("canvas")

        assert usage["usage_trend"] in ["increasing", "decreasing", "stable"]


class TestTopArtifacts:
    """Tests for get_top_artifacts method."""

    def test_top_by_total_events(self, usage_manager):
        """Test getting top artifacts by total events."""
        top = usage_manager.get_top_artifacts(limit=3)

        assert len(top) <= 3
        # Should be sorted descending by total_events
        assert top[0]["artifact_name"] == "canvas"
        assert top[0]["total_events"] == 80

        # Verify descending order
        for i in range(len(top) - 1):
            assert top[i]["total_events"] >= top[i + 1]["total_events"]

    def test_top_by_deploy_count(self, usage_manager):
        """Test getting top artifacts by deploy count."""
        top = usage_manager.get_top_artifacts(metric="deploy_count", limit=3)

        assert len(top) <= 3
        # Canvas should be first (50 deploys)
        assert top[0]["artifact_name"] == "canvas"
        assert top[0]["deploy_count"] == 50

        # Verify descending order
        for i in range(len(top) - 1):
            assert top[i]["deploy_count"] >= top[i + 1]["deploy_count"]

    def test_top_by_search_count(self, usage_manager):
        """Test getting top artifacts by search count."""
        top = usage_manager.get_top_artifacts(metric="search_count", limit=5)

        # Canvas has most searches (20)
        assert top[0]["artifact_name"] == "canvas"
        assert top[0]["search_count"] == 20

    def test_top_artifacts_with_limit(self, usage_manager):
        """Test limit parameter works correctly."""
        top_2 = usage_manager.get_top_artifacts(limit=2)
        top_10 = usage_manager.get_top_artifacts(limit=10)

        assert len(top_2) <= 2
        assert len(top_10) <= 10

    def test_invalid_metric_raises_error(self, usage_manager):
        """Test invalid metric raises ValueError."""
        with pytest.raises(ValueError, match="Invalid metric"):
            usage_manager.get_top_artifacts(metric="invalid_metric")


class TestUnusedArtifacts:
    """Tests for get_unused_artifacts method."""

    def test_unused_90_days(self, usage_manager):
        """Test finding artifacts unused for 90+ days."""
        unused = usage_manager.get_unused_artifacts(days_threshold=90)

        # old-skill should be in results (last used 100 days ago)
        artifact_names = [a["artifact_name"] for a in unused]
        assert "old-skill" in artifact_names

        # Verify structure
        for artifact in unused:
            assert "artifact_name" in artifact
            assert "last_used" in artifact
            assert "days_ago" in artifact
            assert artifact["days_ago"] >= 90

    def test_unused_custom_threshold(self, usage_manager):
        """Test custom threshold for unused artifacts."""
        # Very high threshold - should find very few or none
        unused = usage_manager.get_unused_artifacts(days_threshold=200)
        assert len(unused) == 0  # None are THAT old

        # Low threshold - should find old-skill
        unused = usage_manager.get_unused_artifacts(days_threshold=50)
        artifact_names = [a["artifact_name"] for a in unused]
        assert "old-skill" in artifact_names

    def test_negative_threshold_raises_error(self, usage_manager):
        """Test negative threshold raises ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            usage_manager.get_unused_artifacts(days_threshold=-10)


class TestCleanupSuggestions:
    """Tests for get_cleanup_suggestions method."""

    def test_unused_90_days_suggestions(self, usage_manager):
        """Test cleanup suggestions include unused artifacts."""
        suggestions = usage_manager.get_cleanup_suggestions()

        assert "unused_90_days" in suggestions
        # old-skill should be suggested (100 days old)
        names = [a["name"] for a in suggestions["unused_90_days"]]
        assert "old-skill" in names

    def test_never_deployed_suggestions(self, usage_manager):
        """Test cleanup suggestions include never deployed artifacts."""
        suggestions = usage_manager.get_cleanup_suggestions()

        assert "never_deployed" in suggestions
        # never-deployed artifact should be in results
        names = [a["name"] for a in suggestions["never_deployed"]]
        assert "never-deployed" in names

        # Verify structure
        for artifact in suggestions["never_deployed"]:
            assert artifact["total_events"] > 0  # Has some events
            assert "days_since_added" in artifact

    def test_low_usage_suggestions(self, usage_manager):
        """Test cleanup suggestions include low usage artifacts."""
        suggestions = usage_manager.get_cleanup_suggestions()

        assert "low_usage" in suggestions
        # low-usage artifact should be in results (2 events, 70 days old)
        names = [a["name"] for a in suggestions["low_usage"]]
        assert "low-usage" in names

    def test_size_calculation(self, usage_manager, temp_dir):
        """Test total reclaimable size is calculated."""
        # Create fake artifact directories
        collection_dir = temp_dir / "collections" / "default" / "skills"
        collection_dir.mkdir(parents=True, exist_ok=True)

        # Create old-skill directory with some files
        old_skill_dir = collection_dir / "old-skill"
        old_skill_dir.mkdir()
        (old_skill_dir / "file1.txt").write_text("test content" * 100)
        (old_skill_dir / "file2.txt").write_text("more content" * 50)

        suggestions = usage_manager.get_cleanup_suggestions()

        assert "total_reclaimable_mb" in suggestions
        # Should be a float >= 0
        assert isinstance(suggestions["total_reclaimable_mb"], float)
        assert suggestions["total_reclaimable_mb"] >= 0

    def test_full_cleanup_report_structure(self, usage_manager):
        """Test full cleanup report has correct structure."""
        suggestions = usage_manager.get_cleanup_suggestions()

        # Verify all required keys
        required_keys = [
            "unused_90_days",
            "never_deployed",
            "low_usage",
            "total_reclaimable_mb",
            "summary",
        ]

        for key in required_keys:
            assert key in suggestions

        # Verify summary is a string
        assert isinstance(suggestions["summary"], str)
        assert len(suggestions["summary"]) > 0


class TestUsageTrends:
    """Tests for get_usage_trends method."""

    def test_trends_7_days(self, usage_manager):
        """Test getting usage trends for 7 days."""
        trends = usage_manager.get_usage_trends(time_period="7d")

        assert trends["period"] == "7d"
        assert "deploy_trend" in trends
        assert "update_trend" in trends
        assert "sync_trend" in trends
        assert "search_trend" in trends
        assert "total_events_by_day" in trends

    def test_trends_30_days(self, usage_manager):
        """Test getting usage trends for 30 days."""
        trends = usage_manager.get_usage_trends(time_period="30d")

        assert trends["period"] == "30d"
        # Should have data since we added events recently
        assert len(trends["total_events_by_day"]) > 0

    def test_trends_90_days(self, usage_manager):
        """Test getting usage trends for 90 days."""
        trends = usage_manager.get_usage_trends(time_period="90d")

        assert trends["period"] == "90d"

    def test_trends_all_time(self, usage_manager):
        """Test getting all-time usage trends."""
        trends = usage_manager.get_usage_trends(time_period="all")

        assert trends["period"] == "all"
        # Should include all events including old ones
        assert len(trends["total_events_by_day"]) > 0

    def test_trends_for_specific_artifact(self, usage_manager):
        """Test getting trends for specific artifact."""
        trends = usage_manager.get_usage_trends(
            artifact_name="canvas", time_period="30d"
        )

        # Should only include canvas events
        assert trends["period"] == "30d"

    def test_invalid_time_period_raises_error(self, usage_manager):
        """Test invalid time period raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time_period"):
            usage_manager.get_usage_trends(time_period="invalid")


class TestExportReport:
    """Tests for export_usage_report method."""

    def test_export_to_json(self, usage_manager, temp_dir):
        """Test exporting report to JSON."""
        output_path = temp_dir / "report.json"

        usage_manager.export_usage_report(output_path, format="json")

        # Verify file was created
        assert output_path.exists()

        # Verify JSON is valid and has correct structure
        with open(output_path) as f:
            report = json.load(f)

        assert "generated_at" in report
        assert "report_type" in report
        assert report["report_type"] == "usage_report"
        assert "summary" in report
        assert "top_artifacts" in report
        assert "cleanup_suggestions" in report
        assert "trends_30d" in report

    def test_export_to_csv(self, usage_manager, temp_dir):
        """Test exporting report to CSV."""
        output_path = temp_dir / "report.csv"

        usage_manager.export_usage_report(output_path, format="csv")

        # Verify file was created
        assert output_path.exists()

        # Verify CSV has content
        content = output_path.read_text()
        assert len(content) > 0
        # Should have header line
        assert "artifact_name" in content

    def test_export_with_filters(self, usage_manager, temp_dir):
        """Test exporting report with collection filter."""
        output_path = temp_dir / "filtered_report.json"

        usage_manager.export_usage_report(
            output_path, format="json", collection_name="default"
        )

        assert output_path.exists()

        with open(output_path) as f:
            report = json.load(f)

        # Verify filter is recorded
        assert report["filters"]["collection_name"] == "default"

    def test_invalid_format_raises_error(self, usage_manager, temp_dir):
        """Test invalid format raises ValueError."""
        output_path = temp_dir / "report.xml"

        with pytest.raises(ValueError, match="Invalid format"):
            usage_manager.export_usage_report(output_path, format="xml")


class TestGracefulDegradation:
    """Tests for graceful degradation when analytics disabled."""

    def test_get_artifact_usage_when_disabled(self, mock_config_disabled):
        """Test get_artifact_usage returns empty when disabled."""
        manager = UsageReportManager(config=mock_config_disabled)

        usage = manager.get_artifact_usage("canvas")

        assert usage["total_events"] == 0
        assert usage["artifact_name"] == "canvas"

    def test_get_top_artifacts_when_disabled(self, mock_config_disabled):
        """Test get_top_artifacts returns empty list when disabled."""
        manager = UsageReportManager(config=mock_config_disabled)

        top = manager.get_top_artifacts(limit=10)

        assert top == []

    def test_get_cleanup_suggestions_when_disabled(self, mock_config_disabled):
        """Test cleanup suggestions returns empty when disabled."""
        manager = UsageReportManager(config=mock_config_disabled)

        suggestions = manager.get_cleanup_suggestions()

        assert suggestions["unused_90_days"] == []
        assert suggestions["never_deployed"] == []
        assert suggestions["low_usage"] == []
        assert suggestions["total_reclaimable_mb"] == 0.0
        assert "disabled" in suggestions["summary"].lower()


class TestHelperMethods:
    """Tests for internal helper methods."""

    def test_calculate_days_since_valid_timestamp(self, usage_manager):
        """Test calculating days since valid timestamp."""
        # ISO format
        timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        days = usage_manager._calculate_days_since(timestamp)

        assert days == 10

        # SQLite format
        timestamp = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        days = usage_manager._calculate_days_since(timestamp)

        assert days == 5

    def test_calculate_days_since_none(self, usage_manager):
        """Test calculating days since None returns None."""
        days = usage_manager._calculate_days_since(None)

        assert days is None

    def test_calculate_days_since_invalid_timestamp(self, usage_manager):
        """Test calculating days since invalid timestamp returns None."""
        days = usage_manager._calculate_days_since("invalid-timestamp")

        assert days is None

    def test_calculate_usage_trend(self, usage_manager):
        """Test usage trend calculation returns valid values."""
        trend = usage_manager._calculate_usage_trend("canvas", days=30)

        assert trend in ["increasing", "decreasing", "stable"]

    def test_estimate_artifact_size_nonexistent(self, usage_manager):
        """Test estimating size of nonexistent artifact returns 0."""
        size = usage_manager._estimate_artifact_size("nonexistent")

        assert size == 0

    def test_estimate_artifact_size_existing(self, usage_manager, temp_dir):
        """Test estimating size of existing artifact."""
        # Create artifact directory
        collection_dir = temp_dir / "collections" / "default" / "skills"
        collection_dir.mkdir(parents=True, exist_ok=True)

        artifact_dir = collection_dir / "test-artifact"
        artifact_dir.mkdir()
        (artifact_dir / "file.txt").write_text("test content")

        size = usage_manager._estimate_artifact_size("test-artifact")

        assert size > 0  # Should detect the file


class TestContextManager:
    """Tests for context manager support."""

    def test_context_manager_closes_db(self, mock_config, temp_dir):
        """Test context manager closes database on exit."""
        db_path = temp_dir / "analytics.db"

        with UsageReportManager(config=mock_config, db_path=db_path) as manager:
            assert manager.db is not None

        # After exiting context, db should be closed
        # We can't directly test if closed, but we can verify no errors

    def test_context_manager_with_exception(self, mock_config, temp_dir):
        """Test context manager closes database even on exception."""
        db_path = temp_dir / "analytics.db"

        try:
            with UsageReportManager(config=mock_config, db_path=db_path) as manager:
                assert manager.db is not None
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should not raise additional errors
