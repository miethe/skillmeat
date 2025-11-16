"""Tests for analytics CLI commands."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main


class TestAnalyticsUsageCommand:
    """Test suite for analytics usage command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_usage_data(self):
        """Provide mock usage data."""
        return {
            "artifacts": [
                {
                    "artifact_name": "canvas",
                    "artifact_type": "skill",
                    "first_used": datetime.now() - timedelta(days=30),
                    "last_used": datetime.now() - timedelta(days=2),
                    "deploy_count": 50,
                    "update_count": 10,
                    "sync_count": 5,
                    "remove_count": 0,
                    "search_count": 3,
                    "total_events": 68,
                    "days_since_last_use": 2,
                    "usage_trend": "increasing",
                },
                {
                    "artifact_name": "planning",
                    "artifact_type": "skill",
                    "first_used": datetime.now() - timedelta(days=20),
                    "last_used": datetime.now() - timedelta(days=1),
                    "deploy_count": 15,
                    "update_count": 5,
                    "sync_count": 2,
                    "remove_count": 0,
                    "search_count": 1,
                    "total_events": 23,
                    "days_since_last_use": 1,
                    "usage_trend": "stable",
                },
            ],
            "total_count": 2,
        }

    def test_usage_analytics_disabled(self, cli_runner):
        """Test usage command when analytics is disabled."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = False
            mock_config_class.return_value = mock_config

            result = cli_runner.invoke(main, ["analytics", "usage"])

            assert result.exit_code == 2
            assert "Analytics is disabled" in result.output

    def test_usage_all_artifacts_table_format(self, cli_runner, mock_usage_data):
        """Test usage command displays all artifacts in table format."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_artifact_usage.return_value = mock_usage_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "usage"])

            assert result.exit_code == 0
            assert "Artifact Usage Statistics" in result.output
            assert "canvas" in result.output
            assert "planning" in result.output

    def test_usage_single_artifact(self, cli_runner, mock_usage_data):
        """Test usage command for single artifact."""
        single_artifact = mock_usage_data["artifacts"][0]

        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_artifact_usage.return_value = single_artifact
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "usage", "canvas"])

            assert result.exit_code == 0
            assert "canvas" in result.output

    def test_usage_json_format(self, cli_runner, mock_usage_data):
        """Test usage command with JSON output format."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_artifact_usage.return_value = mock_usage_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "usage", "--format", "json"])

            assert result.exit_code == 0
            # Validate JSON output
            output_data = json.loads(result.output)
            assert "artifacts" in output_data
            assert len(output_data["artifacts"]) == 2

    def test_usage_no_data(self, cli_runner):
        """Test usage command when no data is available."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_artifact_usage.return_value = {"artifacts": []}
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "usage"])

            assert result.exit_code == 0
            assert "No usage data available" in result.output

    def test_usage_filter_by_type(self, cli_runner, mock_usage_data):
        """Test usage command with type filter."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_artifact_usage.return_value = mock_usage_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "usage", "--type", "skill"])

            assert result.exit_code == 0
            mock_manager.get_artifact_usage.assert_called_once()
            call_args = mock_manager.get_artifact_usage.call_args
            assert call_args.kwargs["artifact_type"] == "skill"


class TestAnalyticsTopCommand:
    """Test suite for analytics top command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_top_artifacts(self):
        """Provide mock top artifacts data."""
        return [
            {
                "artifact_name": "canvas",
                "artifact_type": "skill",
                "total_events": 80,
                "deploy_count": 50,
                "update_count": 10,
            },
            {
                "artifact_name": "planning",
                "artifact_type": "skill",
                "total_events": 20,
                "deploy_count": 15,
                "update_count": 5,
            },
        ]

    def test_top_default(self, cli_runner, mock_top_artifacts):
        """Test top command with default parameters."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_top_artifacts.return_value = mock_top_artifacts
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "top"])

            assert result.exit_code == 0
            assert "Top" in result.output and "Artifacts" in result.output
            assert "canvas" in result.output

    def test_top_with_limit(self, cli_runner, mock_top_artifacts):
        """Test top command with custom limit."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_top_artifacts.return_value = mock_top_artifacts
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "top", "--limit", "5"])

            assert result.exit_code == 0
            mock_manager.get_top_artifacts.assert_called_once()
            call_args = mock_manager.get_top_artifacts.call_args
            assert call_args.kwargs["limit"] == 5

    def test_top_with_metric(self, cli_runner, mock_top_artifacts):
        """Test top command with custom metric."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_top_artifacts.return_value = mock_top_artifacts
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main, ["analytics", "top", "--metric", "deploy_count"]
            )

            assert result.exit_code == 0
            mock_manager.get_top_artifacts.assert_called_once()
            call_args = mock_manager.get_top_artifacts.call_args
            assert call_args.kwargs["metric"] == "deploy_count"

    def test_top_json_format(self, cli_runner, mock_top_artifacts):
        """Test top command with JSON output."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_top_artifacts.return_value = mock_top_artifacts
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "top", "--format", "json"])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert "top_artifacts" in output_data
            assert len(output_data["top_artifacts"]) == 2

    def test_top_no_data(self, cli_runner):
        """Test top command when no data is available."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_top_artifacts.return_value = []
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "top"])

            assert result.exit_code == 0
            assert "No usage data available" in result.output


class TestAnalyticsCleanupCommand:
    """Test suite for analytics cleanup command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_cleanup_suggestions(self):
        """Provide mock cleanup suggestions data."""
        return {
            "unused_90_days": [
                {"name": "old-skill", "type": "skill", "days_ago": 100},
            ],
            "never_deployed": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "days_since_added": 60,
                    "total_events": 3,
                },
            ],
            "low_usage": [
                {"name": "low-skill", "type": "skill", "total_events": 2},
            ],
            "total_reclaimable_mb": 15.3,
            "summary": "3 artifacts can be cleaned up.",
        }

    def test_cleanup_default(self, cli_runner, mock_cleanup_suggestions):
        """Test cleanup command with default parameters."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_cleanup_suggestions.return_value = mock_cleanup_suggestions
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "cleanup"])

            assert result.exit_code == 0
            assert "Cleanup Suggestions" in result.output
            assert "old-skill" in result.output
            assert "15.3" in result.output and "MB" in result.output

    def test_cleanup_no_suggestions(self, cli_runner):
        """Test cleanup command when no cleanup suggestions."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_cleanup_suggestions.return_value = {
                "unused_90_days": [],
                "never_deployed": [],
                "low_usage": [],
            }
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "cleanup"])

            assert result.exit_code == 0
            assert "No cleanup suggestions" in result.output

    def test_cleanup_json_format(self, cli_runner, mock_cleanup_suggestions):
        """Test cleanup command with JSON output."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_cleanup_suggestions.return_value = mock_cleanup_suggestions
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main, ["analytics", "cleanup", "--format", "json"]
            )

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert "unused_90_days" in output_data
            assert output_data["total_reclaimable_mb"] == 15.3


class TestAnalyticsTrendsCommand:
    """Test suite for analytics trends command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_trends_data(self):
        """Provide mock trends data."""
        return {
            "period": "30d",
            "deploy_trend": [
                {"date": "2025-11-01", "count": 5},
                {"date": "2025-11-02", "count": 8},
            ],
            "update_trend": [
                {"date": "2025-11-01", "count": 2},
                {"date": "2025-11-02", "count": 3},
            ],
            "sync_trend": [],
            "search_trend": [],
            "total_events_by_day": {
                "2025-11-01": 7,
                "2025-11-02": 11,
            },
        }

    def test_trends_default(self, cli_runner, mock_trends_data):
        """Test trends command with default parameters."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_usage_trends.return_value = mock_trends_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "trends"])

            assert result.exit_code == 0
            assert "Usage Trends" in result.output

    def test_trends_specific_artifact(self, cli_runner, mock_trends_data):
        """Test trends command for specific artifact."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_usage_trends.return_value = mock_trends_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "trends", "canvas"])

            assert result.exit_code == 0
            assert "canvas" in result.output
            mock_manager.get_usage_trends.assert_called_once()

    def test_trends_custom_period(self, cli_runner, mock_trends_data):
        """Test trends command with custom period."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_usage_trends.return_value = mock_trends_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "trends", "--period", "7d"])

            assert result.exit_code == 0
            mock_manager.get_usage_trends.assert_called_once()
            call_args = mock_manager.get_usage_trends.call_args
            assert call_args.kwargs["time_period"] == "7d"

    def test_trends_json_format(self, cli_runner, mock_trends_data):
        """Test trends command with JSON output."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.get_usage_trends.return_value = mock_trends_data
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "trends", "--format", "json"])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert "period" in output_data
            assert output_data["period"] == "30d"


class TestAnalyticsExportCommand:
    """Test suite for analytics export command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_export_json_default(self, cli_runner):
        """Test export command with default JSON format."""
        with cli_runner.isolated_filesystem():
            with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
                "skillmeat.core.usage_reports.UsageReportManager"
            ) as mock_manager_class:
                mock_config = MagicMock()
                mock_config.is_analytics_enabled.return_value = True
                mock_config_class.return_value = mock_config

                mock_manager = MagicMock()
                mock_manager.export_usage_report.return_value = None
                mock_manager_class.return_value = mock_manager

                # Create output file
                Path("report.json").write_text('{"test": "data"}')

                result = cli_runner.invoke(
                    main, ["analytics", "export", "report.json"]
                )

                assert result.exit_code == 0
                assert "Report exported successfully" in result.output
                assert "report.json" in result.output

    def test_export_csv_format(self, cli_runner):
        """Test export command with CSV format."""
        with cli_runner.isolated_filesystem():
            with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
                "skillmeat.core.usage_reports.UsageReportManager"
            ) as mock_manager_class:
                mock_config = MagicMock()
                mock_config.is_analytics_enabled.return_value = True
                mock_config_class.return_value = mock_config

                mock_manager = MagicMock()
                mock_manager.export_usage_report.return_value = None
                mock_manager_class.return_value = mock_manager

                # Create output file
                Path("report.csv").write_text("test,data\n")

                result = cli_runner.invoke(
                    main, ["analytics", "export", "report.csv", "--format", "csv"]
                )

                assert result.exit_code == 0
                assert "Report exported successfully" in result.output
                assert "CSV" in result.output


class TestAnalyticsStatsCommand:
    """Test suite for analytics stats command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_db_stats(self):
        """Provide mock database statistics."""
        return {
            "total_events": 1234,
            "unique_artifacts": 56,
            "earliest_event": "2025-01-15T10:00:00",
            "latest_event": "2025-11-16T15:30:00",
            "events_by_type": {
                "deploy": 512,
                "update": 234,
                "sync": 345,
                "search": 143,
            },
        }

    def test_stats_display(self, cli_runner, mock_db_stats):
        """Test stats command displays database statistics."""
        with cli_runner.isolated_filesystem():
            with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
                "skillmeat.core.usage_reports.UsageReportManager"
            ) as mock_manager_class:
                mock_config = MagicMock()
                mock_config.is_analytics_enabled.return_value = True
                mock_config.get_analytics_db_path.return_value = Path("analytics.db")
                mock_config_class.return_value = mock_config

                mock_manager = MagicMock()
                mock_manager.db.get_stats.return_value = mock_db_stats
                mock_manager_class.return_value = mock_manager

                # Create fake db file
                Path("analytics.db").write_text("fake db")

                result = cli_runner.invoke(main, ["analytics", "stats"])

                assert result.exit_code == 0
                assert "Analytics Database Statistics" in result.output
                # Rich adds formatting codes, so check for the numbers separately
                assert "1" in result.output and "234" in result.output
                assert "56" in result.output

    def test_stats_empty_database(self, cli_runner):
        """Test stats command with empty database."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.db.get_stats.return_value = {"total_events": 0}
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(main, ["analytics", "stats"])

            assert result.exit_code == 0
            assert "Analytics database is empty" in result.output


class TestAnalyticsClearCommand:
    """Test suite for analytics clear command."""

    @pytest.fixture
    def cli_runner(self):
        """Provide CLI test runner."""
        return CliRunner()

    def test_clear_with_confirmation(self, cli_runner):
        """Test clear command with confirmation."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config.get.return_value = 365
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.db.get_stats.return_value = {"total_events": 1000}
            mock_manager.db.delete_events_before.return_value = 456
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main, ["analytics", "clear", "--older-than-days", "180", "--confirm"]
            )

            assert result.exit_code == 0
            assert "Deleted" in result.output and "456" in result.output and "events" in result.output

    def test_clear_empty_database(self, cli_runner):
        """Test clear command with empty database."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.db.get_stats.return_value = {"total_events": 0}
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main, ["analytics", "clear", "--older-than-days", "90", "--confirm"]
            )

            assert result.exit_code == 0
            assert "Analytics database is empty" in result.output

    def test_clear_no_matches(self, cli_runner):
        """Test clear command when no events match criteria."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config.get.return_value = 365
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.db.get_stats.return_value = {"total_events": 100}
            mock_manager.db.delete_events_before.return_value = 0
            mock_manager_class.return_value = mock_manager

            result = cli_runner.invoke(
                main, ["analytics", "clear", "--older-than-days", "365", "--confirm"]
            )

            assert result.exit_code == 0
            assert "No events matched" in result.output

    def test_clear_without_confirm_flag(self, cli_runner):
        """Test clear command requires user confirmation without --confirm."""
        with patch("skillmeat.cli.ConfigManager") as mock_config_class, patch(
            "skillmeat.core.usage_reports.UsageReportManager"
        ) as mock_manager_class:
            mock_config = MagicMock()
            mock_config.is_analytics_enabled.return_value = True
            mock_config.get.return_value = 365
            mock_config_class.return_value = mock_config

            mock_manager = MagicMock()
            mock_manager.db.get_stats.return_value = {"total_events": 1000}
            mock_manager_class.return_value = mock_manager

            # Provide 'n' as input to decline confirmation
            result = cli_runner.invoke(
                main, ["analytics", "clear", "--older-than-days", "90"], input="n\n"
            )

            assert result.exit_code == 0
            assert "Operation cancelled" in result.output


class TestAnalyticsHelpers:
    """Test suite for analytics helper functions."""

    def test_create_sparkline_empty(self):
        """Test sparkline creation with empty values."""
        from skillmeat.cli import _create_sparkline

        result = _create_sparkline([])
        assert result == ""

    def test_create_sparkline_flat(self):
        """Test sparkline creation with flat values."""
        from skillmeat.cli import _create_sparkline

        result = _create_sparkline([5, 5, 5, 5])
        assert len(result) == 4
        # All same character for flat line
        assert len(set(result)) == 1

    def test_create_sparkline_varying(self):
        """Test sparkline creation with varying values."""
        from skillmeat.cli import _create_sparkline

        result = _create_sparkline([1, 2, 3, 4, 5])
        assert len(result) == 5
        # Should have different characters for varying values
        assert len(set(result)) > 1
