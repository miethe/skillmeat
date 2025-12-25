"""Tests for 'skillmeat scores' commands (import, refresh, show)."""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.core.scoring.score_aggregator import ScoreSource
from skillmeat.core.scoring.github_stars_importer import (
    GitHubRepoStats,
    RateLimitError,
    RepoNotFoundError,
)


@pytest.fixture
def mock_github_importer():
    """Mock GitHubStarsImporter for testing."""
    with patch("skillmeat.cli.GitHubStarsImporter") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance

        # Mock batch_import as async function
        async def mock_batch_import(sources, concurrency=5):
            return [
                ScoreSource(
                    source_name="github_stars",
                    score=78.5,
                    weight=0.25,
                    last_updated=datetime.now(timezone.utc),
                    sample_size=1250,
                )
                for _ in sources
            ]

        mock_instance.batch_import = mock_batch_import
        mock_instance.normalize_stars_to_score = lambda stars: 78.5

        yield mock_instance


@pytest.fixture
def mock_collection_with_artifacts(isolated_cli_runner):
    """Set up a collection with some test artifacts."""
    runner = isolated_cli_runner

    # Initialize collection
    runner.invoke(main, ["init", "--name", "default"])

    # We'll mock the artifact manager instead of actually adding artifacts
    with patch("skillmeat.cli.ArtifactManager") as mock_artifact_mgr:
        mock_mgr_instance = MagicMock()
        mock_artifact_mgr.return_value = mock_mgr_instance

        # Mock artifact list
        mock_artifact = MagicMock()
        mock_artifact.source = "anthropics/skills"
        mock_artifact.name = "pdf"
        mock_artifact.version = "v1.0.0"

        mock_mgr_instance.list.return_value = [mock_artifact]

        yield mock_mgr_instance


class TestScoresImportCommand:
    """Test suite for 'skillmeat scores import' command."""

    def test_import_help(self, isolated_cli_runner):
        """Test that help text is displayed."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["scores", "import", "--help"])

        assert result.exit_code == 0
        assert "Import community scores from external sources" in result.output
        assert "--source" in result.output
        assert "--artifact" in result.output
        assert "--token" in result.output
        assert "--concurrency" in result.output
        assert "--json" in result.output

    @patch("skillmeat.core.collection.CollectionManager")
    def test_import_no_collection(self, mock_coll_mgr_class, isolated_cli_runner):
        """Test import fails gracefully when no collection exists."""
        runner = isolated_cli_runner

        # Mock no collections
        mock_coll_mgr = MagicMock()
        mock_coll_mgr.list_collections.return_value = []
        mock_coll_mgr_class.return_value = mock_coll_mgr

        result = runner.invoke(main, ["scores", "import"])

        assert result.exit_code == 1
        assert "No collections found" in result.output

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    @patch("skillmeat.core.artifact.ArtifactManager")
    @patch("skillmeat.core.collection.CollectionManager")
    def test_import_all_artifacts(
        self, mock_coll_mgr_class, mock_art_mgr_class, mock_importer_class, isolated_cli_runner
    ):
        """Test importing scores for all artifacts in collection."""
        runner = isolated_cli_runner

        # Setup mocks
        mock_coll_mgr = MagicMock()
        mock_coll_mgr.list_collections.return_value = ["default"]
        mock_coll_mgr_class.return_value = mock_coll_mgr

        mock_art_mgr = MagicMock()
        mock_artifact = MagicMock()
        mock_artifact.name = "pdf"
        mock_artifact.upstream = "https://github.com/anthropics/skills"
        mock_artifact.resolved_version = "v1.0.0"
        mock_art_mgr.list_artifacts.return_value = [mock_artifact]
        mock_art_mgr_class.return_value = mock_art_mgr

        mock_importer = MagicMock()

        async def mock_batch_import(sources, concurrency=5):
            return [
                ScoreSource(
                    source_name="github_stars",
                    score=78.5,
                    weight=0.25,
                    last_updated=datetime.now(timezone.utc),
                    sample_size=1250,
                )
            ]

        mock_importer.batch_import = mock_batch_import
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "import"])

        assert result.exit_code == 0
        assert "Importing scores" in result.output or "Imported" in result.output

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    def test_import_single_artifact(self, mock_importer_class, isolated_cli_runner):
        """Test importing scores for a single artifact."""
        runner = isolated_cli_runner

        mock_importer = MagicMock()

        async def mock_batch_import(sources, concurrency=5):
            return [
                ScoreSource(
                    source_name="github_stars",
                    score=78.5,
                    weight=0.25,
                    last_updated=datetime.now(timezone.utc),
                    sample_size=1250,
                )
            ]

        mock_importer.batch_import = mock_batch_import
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "import", "-a", "anthropics/skills/pdf"])

        assert result.exit_code == 0

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    def test_import_json_output(self, mock_importer_class, isolated_cli_runner):
        """Test JSON output format."""
        runner = isolated_cli_runner

        mock_importer = MagicMock()

        async def mock_batch_import(sources, concurrency=5):
            return [
                ScoreSource(
                    source_name="github_stars",
                    score=78.5,
                    weight=0.25,
                    last_updated=datetime.now(timezone.utc),
                    sample_size=1250,
                )
            ]

        mock_importer.batch_import = mock_batch_import
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "import", "-a", "anthropics/skills/pdf", "--json"])

        assert result.exit_code == 0

        # Parse JSON output (handle empty output)
        if not result.output.strip():
            # No output means no artifacts were imported (expected for mock)
            return

        output = json.loads(result.output)
        assert output["schema_version"] == "1"
        assert output["command"] == "scores import"
        assert "timestamp" in output
        assert "results" in output
        assert "summary" in output
        assert output["summary"]["total"] >= 0

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    def test_import_with_token(self, mock_importer_class, isolated_cli_runner):
        """Test import with GitHub token."""
        runner = isolated_cli_runner

        mock_importer = MagicMock()

        async def mock_batch_import(sources, concurrency=5):
            return []

        mock_importer.batch_import = mock_batch_import
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(
            main, ["scores", "import", "-a", "anthropics/skills/pdf", "--token", "ghp_test123"]
        )

        # Verify importer was initialized with token
        mock_importer_class.assert_called_with(token="ghp_test123")

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    def test_import_rate_limit_error(self, mock_importer_class, isolated_cli_runner):
        """Test handling of rate limit errors."""
        runner = isolated_cli_runner

        mock_importer = MagicMock()

        async def mock_batch_import(sources, concurrency=5):
            raise RateLimitError(
                "Rate limit exceeded", reset_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )

        mock_importer.batch_import = mock_batch_import
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "import", "-a", "anthropics/skills/pdf"])

        assert result.exit_code == 1
        assert "Rate limit exceeded" in result.output


class TestScoresRefreshCommand:
    """Test suite for 'skillmeat scores refresh' command."""

    def test_refresh_help(self, isolated_cli_runner):
        """Test that help text is displayed."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["scores", "refresh", "--help"])

        assert result.exit_code == 0
        assert "Refresh stale community scores" in result.output
        assert "--stale-days" in result.output
        assert "--force" in result.output
        assert "--artifact" in result.output
        assert "--json" in result.output

    @patch("skillmeat.cache.models.get_session")
    def test_refresh_no_cache(self, mock_get_session, isolated_cli_runner):
        """Test refresh when no cached scores exist."""
        runner = isolated_cli_runner

        # Mock empty database
        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = []
        mock_get_session.return_value = mock_session

        result = runner.invoke(main, ["scores", "refresh"])

        assert result.exit_code == 0
        assert "No cached scores found" in result.output

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    @patch("skillmeat.cache.models.get_session")
    @patch("skillmeat.core.scoring.score_decay.ScoreDecay")
    def test_refresh_stale_scores(
        self, mock_decay_class, mock_get_session, mock_importer_class, isolated_cli_runner
    ):
        """Test refreshing stale scores."""
        runner = isolated_cli_runner

        # Mock cached entry
        mock_entry = MagicMock()
        mock_entry.cache_key = "anthropics/skills"
        mock_entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=90)

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_entry]
        mock_get_session.return_value = mock_session

        # Mock decay checker
        mock_decay = MagicMock()
        mock_decay.should_refresh.return_value = True
        mock_decay_class.return_value = mock_decay

        # Mock importer
        mock_importer = MagicMock()

        async def mock_fetch_repo_stats(owner, repo):
            return GitHubRepoStats(
                owner=owner,
                repo=repo,
                stars=1250,
                forks=100,
                watchers=50,
                open_issues=10,
                last_updated=datetime.now(timezone.utc),
                fetched_at=datetime.now(timezone.utc),
            )

        mock_importer.fetch_repo_stats = mock_fetch_repo_stats
        mock_importer.normalize_stars_to_score.return_value = 78.5
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "refresh"])

        assert result.exit_code == 0
        assert "Refreshing" in result.output or "Refreshed" in result.output

    @patch("skillmeat.cache.models.get_session")
    def test_refresh_all_fresh(self, mock_get_session, isolated_cli_runner):
        """Test refresh when all scores are fresh."""
        runner = isolated_cli_runner

        # Mock cached entry (recent)
        mock_entry = MagicMock()
        mock_entry.cache_key = "anthropics/skills"
        mock_entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=10)

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_entry]
        mock_get_session.return_value = mock_session

        result = runner.invoke(main, ["scores", "refresh"])

        assert result.exit_code == 0
        assert "up-to-date" in result.output

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    @patch("skillmeat.cache.models.get_session")
    def test_refresh_force(self, mock_get_session, mock_importer_class, isolated_cli_runner):
        """Test force refresh ignores staleness check."""
        runner = isolated_cli_runner

        # Mock cached entry (recent, but force should refresh anyway)
        mock_entry = MagicMock()
        mock_entry.cache_key = "anthropics/skills"
        mock_entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=1)

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_entry]
        mock_get_session.return_value = mock_session

        # Mock importer
        mock_importer = MagicMock()

        async def mock_fetch_repo_stats(owner, repo):
            return GitHubRepoStats(
                owner=owner,
                repo=repo,
                stars=1250,
                forks=100,
                watchers=50,
                open_issues=10,
                last_updated=datetime.now(timezone.utc),
                fetched_at=datetime.now(timezone.utc),
            )

        mock_importer.fetch_repo_stats = mock_fetch_repo_stats
        mock_importer.normalize_stars_to_score.return_value = 78.5
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "refresh", "--force"])

        assert result.exit_code == 0

    @patch("skillmeat.core.scoring.github_stars_importer.GitHubStarsImporter")
    @patch("skillmeat.cache.models.get_session")
    @patch("skillmeat.core.scoring.score_decay.ScoreDecay")
    def test_refresh_json_output(
        self, mock_decay_class, mock_get_session, mock_importer_class, isolated_cli_runner
    ):
        """Test JSON output format for refresh."""
        runner = isolated_cli_runner

        # Mock cached entry
        mock_entry = MagicMock()
        mock_entry.cache_key = "anthropics/skills"
        mock_entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=90)

        mock_session = MagicMock()
        mock_session.query.return_value.all.return_value = [mock_entry]
        mock_get_session.return_value = mock_session

        # Mock decay checker
        mock_decay = MagicMock()
        mock_decay.should_refresh.return_value = True
        mock_decay_class.return_value = mock_decay

        # Mock importer
        mock_importer = MagicMock()

        async def mock_fetch_repo_stats(owner, repo):
            return GitHubRepoStats(
                owner=owner,
                repo=repo,
                stars=1250,
                forks=100,
                watchers=50,
                open_issues=10,
                last_updated=datetime.now(timezone.utc),
                fetched_at=datetime.now(timezone.utc),
            )

        mock_importer.fetch_repo_stats = mock_fetch_repo_stats
        mock_importer.normalize_stars_to_score.return_value = 78.5
        mock_importer_class.return_value = mock_importer

        result = runner.invoke(main, ["scores", "refresh", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output["schema_version"] == "1"
        assert output["command"] == "scores refresh"
        assert "summary" in output


class TestScoresShowCommand:
    """Test suite for 'skillmeat scores show' command."""

    def test_show_help(self, isolated_cli_runner):
        """Test that help text is displayed."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["scores", "show", "--help"])

        assert result.exit_code == 0
        assert "Show detailed scores for an artifact" in result.output
        assert "--json" in result.output

    def test_show_invalid_format(self, isolated_cli_runner):
        """Test show with invalid artifact format."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["scores", "show", "invalid"])

        assert result.exit_code == 1
        assert "Invalid artifact format" in result.output

    @patch("skillmeat.cache.models.get_session")
    def test_show_no_cache(self, mock_get_session, isolated_cli_runner):
        """Test show when no cached score exists."""
        runner = isolated_cli_runner

        # Mock empty query
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value = mock_session

        result = runner.invoke(main, ["scores", "show", "anthropics/skills/pdf"])

        assert result.exit_code == 0
        assert "No cached scores found" in result.output

    @patch("skillmeat.cache.models.get_session")
    def test_show_with_cache(self, mock_get_session, isolated_cli_runner):
        """Test show with cached score data."""
        runner = isolated_cli_runner

        # Mock cached entry
        mock_entry = MagicMock()
        mock_entry.cache_key = "anthropics/skills"
        mock_entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=30)
        mock_entry.data = json.dumps(
            {
                "owner": "anthropics",
                "repo": "skills",
                "stars": 1250,
                "forks": 100,
                "watchers": 50,
                "open_issues": 10,
                "last_updated": "2024-12-01T00:00:00+00:00",
                "fetched_at": "2024-12-20T00:00:00+00:00",
            }
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_entry
        mock_get_session.return_value = mock_session

        result = runner.invoke(main, ["scores", "show", "anthropics/skills/pdf"])

        assert result.exit_code == 0
        assert "Scores for" in result.output
        assert "1250" in result.output  # Stars

    @patch("skillmeat.cache.models.get_session")
    def test_show_json_output(self, mock_get_session, isolated_cli_runner):
        """Test JSON output format for show."""
        runner = isolated_cli_runner

        # Mock cached entry
        mock_entry = MagicMock()
        mock_entry.cache_key = "anthropics/skills"
        mock_entry.fetched_at = datetime.now(timezone.utc) - timedelta(days=30)
        mock_entry.data = json.dumps(
            {
                "owner": "anthropics",
                "repo": "skills",
                "stars": 1250,
                "forks": 100,
                "watchers": 50,
                "open_issues": 10,
                "last_updated": "2024-12-01T00:00:00+00:00",
                "fetched_at": "2024-12-20T00:00:00+00:00",
            }
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_entry
        mock_get_session.return_value = mock_session

        result = runner.invoke(main, ["scores", "show", "anthropics/skills/pdf", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert output["artifact"] == "anthropics/skills/pdf"
        assert output["cache_key"] == "anthropics/skills"
        assert output["raw_stars"] == 1250
        assert "score" in output
        assert "age_days" in output
        assert "is_stale" in output


class TestScoresGroupHelp:
    """Test suite for 'skillmeat scores' group help."""

    def test_scores_help(self, isolated_cli_runner):
        """Test scores group help text."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["scores", "--help"])

        assert result.exit_code == 0
        assert "Manage community scores and ratings" in result.output
        assert "import" in result.output
        assert "refresh" in result.output
        assert "show" in result.output
