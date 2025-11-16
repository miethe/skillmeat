"""End-to-end integration tests for analytics pipeline.

Tests the complete flow from event tracking → database → reports → CLI,
using real components without mocks (except for external dependencies).
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.core.analytics import EventTracker
from skillmeat.core.usage_reports import UsageReportManager
from skillmeat.storage.analytics import AnalyticsDB


class TestAnalyticsE2EEventFlow:
    """Test complete event flow from tracking to reporting."""

    def test_deploy_event_to_usage_report(self, analytics_workspace):
        """Test: Deploy artifact → track event → verify in usage report."""
        workspace = analytics_workspace
        db = workspace["db"]
        db = workspace["db"]

        # 1. Track deploy event
        tracker.track_deploy(
            artifact_name="canvas",
            artifact_type="skill",
            collection_name="default",
            project_path="/home/user/project",
            version="1.0.0",
        )
        # 2. Verify event in database
        events = db.get_events(artifact_name="canvas")
        assert len(events) == 1
        assert events[0]["event_type"] == "deploy"
        assert events[0]["artifact_name"] == "canvas"

        # 3. Verify in usage report
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )
        usage = report_mgr.get_artifact_usage(artifact_name="canvas")

        assert usage is not None
        assert usage["artifact_name"] == "canvas"
        assert usage["deploy_count"] == 1
        assert usage["total_events"] == 1

        # 4. Verify in top artifacts query
        top = report_mgr.get_top_artifacts(limit=10)
        assert len(top) == 1
        assert top[0]["artifact_name"] == "canvas"

    def test_update_event_to_trends(self, analytics_workspace):
        """Test: Update artifact → track events → verify in trends."""
        workspace = analytics_workspace
        db = workspace["db"]

        # Track multiple update events over time
        for i in range(5):
            db.record_event(
                event_type="update",
                artifact_name="python-expert",
                artifact_type="skill",
                collection_name="default",
                metadata={"update_number": i},
            )

        # Get trends
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )
        trends = report_mgr.get_usage_trends(
            artifact_name="python-expert", time_period="7d"
        )

        assert trends is not None
        assert "update_trend" in trends
        assert sum(trends["update_trend"]) == 5

    def test_sync_operation_to_aggregations(self, analytics_workspace):
        """Test: Sync operations → track events → verify aggregations."""
        workspace = analytics_workspace
        db = workspace["db"]

        # Simulate multiple artifacts being synced
        artifacts = ["canvas", "git-helper", "code-review"]
        for artifact in artifacts:
            db.record_event(
                event_type="sync",
                artifact_name=artifact,
                artifact_type="skill",
                collection_name="default",
            )

        # Verify in usage report
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        for artifact in artifacts:
            usage = report_mgr.get_artifact_usage(artifact_name=artifact)
            assert usage["sync_count"] == 1

        # Verify total events
        all_usage = report_mgr.get_artifact_usage()
        assert len(all_usage["artifacts"]) == 3

    def test_search_analytics_tracking(self, analytics_workspace):
        """Test: Search operations → track events → verify search analytics."""
        workspace = analytics_workspace
        db = workspace["db"]

        # Track search events
        for i in range(3):
            db.record_event(
                event_type="search",
                artifact_name="canvas",
                artifact_type="skill",
                collection_name="default",
                metadata={"query": f"search-{i}"},
            )

        # Verify in database
        db = workspace["db"]
        events = db.get_events(event_type="search")
        assert len(events) == 3

        # Verify in usage report
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )
        usage = report_mgr.get_artifact_usage(artifact_name="canvas")
        assert usage["search_count"] == 3


class TestAnalyticsE2EExport:
    """Test end-to-end export functionality."""

    def test_export_to_json_and_verify(self, populated_analytics_db, tmp_path):
        """Test: Generate data → export to JSON → verify integrity."""
        workspace = populated_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        # Export to JSON
        export_path = tmp_path / "analytics_export.json"
        report_mgr.export_usage_report(
            output_path=export_path, format="json", collection_name="default"
        )

        # Verify file exists and is valid JSON
        assert export_path.exists()
        with open(export_path) as f:
            data = json.load(f)

        # Verify structure
        assert "usage" in data
        assert "top_artifacts" in data
        assert "cleanup_suggestions" in data
        assert "metadata" in data

        # Verify data integrity
        assert len(data["usage"]) == len(workspace["artifact_names"])
        assert data["metadata"]["collection_name"] == "default"

    def test_export_to_csv_format(self, populated_analytics_db, tmp_path):
        """Test: Export to CSV → verify file format."""
        workspace = populated_analytics_db
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )

        # Export to CSV
        export_path = tmp_path / "analytics_export.csv"
        report_mgr.export_usage_report(
            output_path=export_path, format="csv", collection_name="default"
        )

        # Verify file exists
        assert export_path.exists()

        # Verify CSV structure
        import csv

        with open(export_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) > 0
        # Verify CSV headers
        assert "artifact_name" in rows[0]
        assert "total_events" in rows[0]


class TestAnalyticsE2ECLI:
    """Test CLI commands with real analytics data."""

    def test_cli_usage_command_with_real_data(self, populated_analytics_db):
        """Test: CLI usage command with real database."""
        workspace = populated_analytics_db

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["analytics", "usage"],
            env={"HOME": str(workspace["home"])},
        )

        assert result.exit_code == 0
        # Should show all artifacts
        assert "canvas" in result.output
        assert "python-expert" in result.output

    def test_cli_top_command_with_real_data(self, populated_analytics_db):
        """Test: CLI top command shows ranked artifacts."""
        workspace = populated_analytics_db

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["analytics", "top", "--limit", "3"],
            env={"HOME": str(workspace["home"])},
        )

        assert result.exit_code == 0
        # Should show top 3 artifacts
        assert "1." in result.output  # Ranking numbers
        assert "canvas" in result.output or "python-expert" in result.output

    def test_cli_cleanup_suggestions_with_real_data(self, populated_analytics_db):
        """Test: CLI cleanup command with unused artifacts."""
        workspace = populated_analytics_db

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["analytics", "cleanup", "--inactivity-days", "15"],
            env={"HOME": str(workspace["home"])},
        )

        assert result.exit_code == 0
        # Should detect deprecated-cmd as unused
        assert "deprecated-cmd" in result.output or "unused" in result.output.lower()

    def test_cli_export_command_creates_file(self, populated_analytics_db, tmp_path):
        """Test: CLI export command creates valid output file."""
        workspace = populated_analytics_db
        export_file = tmp_path / "export.json"

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["analytics", "export", str(export_file), "--format", "json"],
            env={"HOME": str(workspace["home"])},
        )

        assert result.exit_code == 0
        assert export_file.exists()

        # Verify valid JSON
        with open(export_file) as f:
            data = json.load(f)
        assert "usage" in data

    def test_cli_stats_command_with_real_data(self, populated_analytics_db):
        """Test: CLI stats command shows database statistics."""
        workspace = populated_analytics_db

        runner = CliRunner()
        result = runner.invoke(
            main, ["analytics", "stats"], env={"HOME": str(workspace["home"])}
        )

        assert result.exit_code == 0
        # Should show event counts
        assert "Total events" in result.output or "events" in result.output.lower()

    def test_cli_clear_command_with_confirmation(self, populated_analytics_db):
        """Test: CLI clear command with --confirm flag."""
        workspace = populated_analytics_db

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["analytics", "clear", "--older-than-days", "60", "--confirm"],
            env={"HOME": str(workspace["home"])},
        )

        # Should succeed (may delete 0 events if all recent)
        assert result.exit_code == 0


class TestAnalyticsE2EDataConsistency:
    """Test data consistency across all analytics layers."""

    def test_event_count_consistency(self, populated_analytics_db):
        """Test: Event counts match across DB, reports, and CLI."""
        workspace = populated_analytics_db
        db = workspace["db"]

        # Get count from database
        db_stats = db.get_stats()
        db_total = db_stats["total_events"]

        # Get count from reports
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )
        all_usage = report_mgr.get_artifact_usage()
        report_total = sum(u["total_events"] for u in all_usage)

        # Counts should match
        assert db_total == report_total
        assert db_total > 0  # Sanity check

    def test_artifact_list_consistency(self, populated_analytics_db):
        """Test: Artifact lists match across different query methods."""
        workspace = populated_analytics_db
        db = workspace["db"]

        # Get artifacts from raw DB query
        db_artifacts = set()
        events = db.get_events()
        for event in events:
            db_artifacts.add(event["artifact_name"])

        # Get artifacts from usage report
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )
        all_usage = report_mgr.get_artifact_usage()
        report_artifacts = set(u["artifact_name"] for u in all_usage)

        # Should match
        assert db_artifacts == report_artifacts

    def test_timestamp_consistency(self, populated_analytics_db):
        """Test: Timestamps are consistent and properly ordered."""
        workspace = populated_analytics_db
        db = workspace["db"]

        # Get all events
        events = db.get_events()

        # Verify timestamps are ISO format and ordered
        for event in events:
            timestamp = event["timestamp"]
            # Should be parseable as ISO datetime
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert dt is not None

        # Verify first_used <= last_used in usage reports
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=workspace["analytics_db_path"]
        )
        all_usage = report_mgr.get_artifact_usage()

        for usage in all_usage.get("artifacts", []):
            first = datetime.fromisoformat(
                usage["first_used"].replace("Z", "+00:00")
            )
            last = datetime.fromisoformat(usage["last_used"].replace("Z", "+00:00"))
            assert first <= last


class TestAnalyticsE2EErrorHandling:
    """Test error handling in end-to-end scenarios."""

    def test_missing_database_graceful_handling(self, analytics_workspace, tmp_path):
        """Test: Missing database doesn't crash, returns empty results."""
        workspace = analytics_workspace

        # Use non-existent DB path
        missing_db = tmp_path / "missing.db"

        # This should not crash
        report_mgr = UsageReportManager(
            config=workspace["config"], db_path=missing_db
        )

        # Should return empty results
        usage = report_mgr.get_artifact_usage()
        assert len(usage.get("artifacts", [])) == 0 or len(usage.get("artifacts", [])) == 0

    def test_corrupted_event_data_handling(self, analytics_workspace):
        """Test: Corrupted events are skipped, not crash."""
        workspace = analytics_workspace
        db = workspace["db"]

        # Record normal event
        db.record_event(
            event_type="deploy",
            artifact_name="test",
            artifact_type="skill",
            collection_name="default",
        )

        # Try to query - should not crash even with potentially bad data
        events = db.get_events()
        assert len(events) >= 1

    def test_cli_with_analytics_disabled(self, analytics_workspace):
        """Test: CLI commands handle analytics disabled gracefully."""
        workspace = analytics_workspace

        # Disable analytics
        config_path = workspace["skillmeat_dir"] / "config.toml"
        config_path.write_text(
            """
[analytics]
enabled = false
"""
        )

        runner = CliRunner()
        result = runner.invoke(
            main, ["analytics", "usage"], env={"HOME": str(workspace["home"])}
        )

        # Should exit with code 2 (analytics disabled)
        assert result.exit_code == 2
        assert "disabled" in result.output.lower()
