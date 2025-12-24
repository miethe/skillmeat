"""Tests for GitHub stars importer.

This module tests the GitHubStarsImporter class for fetching GitHub repository
statistics and converting them to ScoreSource objects.
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.orm import Session

from skillmeat.cache.models import GitHubRepoCache, create_tables, get_session
from skillmeat.core.scoring.github_stars_importer import (
    GitHubAPIError,
    GitHubRepoStats,
    GitHubStarsImporter,
    RateLimitError,
    RepoNotFoundError,
)
from skillmeat.core.scoring.score_aggregator import ScoreSource


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def importer():
    """Create GitHubStarsImporter instance for testing."""
    return GitHubStarsImporter(token="test_token", cache_ttl_hours=1)


@pytest.fixture
def mock_repo_data():
    """Mock GitHub API response data."""
    return {
        "stargazers_count": 150,
        "forks_count": 25,
        "watchers_count": 10,
        "open_issues_count": 5,
        "updated_at": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def db_session(tmp_path):
    """Create test database session."""
    db_path = tmp_path / "test_cache.db"
    create_tables(db_path)
    session = get_session(db_path)
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# Test Star Normalization
# =============================================================================


class TestStarNormalization:
    """Tests for star count normalization to 0-100 score."""

    def test_normalize_zero_stars(self, importer):
        """Test normalization of 0 stars."""
        assert importer.normalize_stars_to_score(0) == 0.0

    def test_normalize_ten_stars(self, importer):
        """Test normalization of 10 stars."""
        score = importer.normalize_stars_to_score(10)
        assert 39.0 <= score <= 41.0  # Approximately 40

    def test_normalize_hundred_stars(self, importer):
        """Test normalization of 100 stars."""
        score = importer.normalize_stars_to_score(100)
        assert 59.0 <= score <= 61.0  # Approximately 60

    def test_normalize_thousand_stars(self, importer):
        """Test normalization of 1000 stars."""
        score = importer.normalize_stars_to_score(1000)
        assert 79.0 <= score <= 81.0  # Approximately 80

    def test_normalize_ten_thousand_stars(self, importer):
        """Test normalization of 10000 stars."""
        score = importer.normalize_stars_to_score(10000)
        assert score <= 95.0  # Capped at 95

    def test_normalize_huge_star_count(self, importer):
        """Test normalization of very high star counts."""
        score = importer.normalize_stars_to_score(100000)
        assert score <= 95.0  # Capped at 95

    def test_normalize_negative_stars(self, importer):
        """Test normalization of negative star count."""
        assert importer.normalize_stars_to_score(-10) == 0.0


# =============================================================================
# Test Artifact Source Parsing
# =============================================================================


class TestArtifactSourceParsing:
    """Tests for parsing artifact sources to extract owner/repo."""

    def test_parse_simple_github_source(self, importer):
        """Test parsing simple GitHub source."""
        result = importer._parse_artifact_source("anthropics/skills")
        assert result == ("anthropics", "skills")

    def test_parse_github_source_with_path(self, importer):
        """Test parsing GitHub source with path."""
        result = importer._parse_artifact_source("anthropics/skills/pdf")
        assert result == ("anthropics", "skills")

    def test_parse_github_source_with_nested_path(self, importer):
        """Test parsing GitHub source with nested path."""
        result = importer._parse_artifact_source("user/repo/path/to/artifact")
        assert result == ("user", "repo")

    def test_parse_github_source_with_version(self, importer):
        """Test parsing GitHub source with version."""
        result = importer._parse_artifact_source("user/repo/path@v1.0.0")
        assert result == ("user", "repo")

    def test_parse_github_source_with_sha(self, importer):
        """Test parsing GitHub source with commit SHA."""
        result = importer._parse_artifact_source("user/repo@abc123")
        assert result == ("user", "repo")

    def test_parse_absolute_path(self, importer):
        """Test parsing absolute filesystem path."""
        result = importer._parse_artifact_source("/local/path/to/artifact")
        assert result is None

    def test_parse_relative_path(self, importer):
        """Test parsing relative filesystem path."""
        result = importer._parse_artifact_source("./local/path")
        assert result is None

    def test_parse_home_path(self, importer):
        """Test parsing home directory path."""
        result = importer._parse_artifact_source("~/skills/canvas")
        assert result is None

    def test_parse_single_component(self, importer):
        """Test parsing source with single component."""
        result = importer._parse_artifact_source("justname")
        assert result is None

    def test_parse_empty_owner(self, importer):
        """Test parsing source with empty owner."""
        result = importer._parse_artifact_source("/repo/path")
        assert result is None

    def test_parse_empty_repo(self, importer):
        """Test parsing source with empty repo."""
        result = importer._parse_artifact_source("owner//path")
        assert result is None


# =============================================================================
# Test GitHub API Fetching
# =============================================================================


class TestFetchRepoStats:
    """Tests for fetching repository statistics from GitHub API."""

    @pytest.mark.asyncio
    async def test_fetch_repo_stats_success(self, importer, mock_repo_data):
        """Test successful repository stats fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = mock_repo_data
        mock_response.headers = {
            "X-RateLimit-Remaining": "4999",
            "X-RateLimit-Reset": "1640000000",
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            stats = await importer.fetch_repo_stats("anthropics", "skills")

            assert stats.owner == "anthropics"
            assert stats.repo == "skills"
            assert stats.stars == 150
            assert stats.forks == 25
            assert stats.watchers == 10
            assert stats.open_issues == 5
            assert isinstance(stats.last_updated, datetime)
            assert isinstance(stats.fetched_at, datetime)

    @pytest.mark.asyncio
    async def test_fetch_repo_stats_not_found(self, importer):
        """Test fetching stats for non-existent repository."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.is_success = False

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(RepoNotFoundError):
                await importer.fetch_repo_stats("nonexistent", "repo")

    @pytest.mark.asyncio
    async def test_fetch_repo_stats_rate_limit(self, importer):
        """Test fetching stats when rate limited."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.is_success = False
        mock_response.headers = {
            "X-RateLimit-Reset": str(int(datetime.now(timezone.utc).timestamp()) + 3600),
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(RateLimitError) as exc_info:
                await importer.fetch_repo_stats("owner", "repo")

            assert isinstance(exc_info.value.reset_at, datetime)

    @pytest.mark.asyncio
    async def test_fetch_repo_stats_api_error(self, importer):
        """Test fetching stats with API error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.is_success = False
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(GitHubAPIError):
                await importer.fetch_repo_stats("owner", "repo")

    @pytest.mark.asyncio
    async def test_fetch_repo_stats_network_error_retry(self, importer):
        """Test network error with retry logic."""
        # First two calls fail, third succeeds
        mock_repo_data = {
            "stargazers_count": 100,
            "forks_count": 10,
            "watchers_count": 5,
            "open_issues_count": 2,
            "updated_at": "2025-01-15T10:00:00Z",
        }

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.is_success = True
        mock_success_response.json.return_value = mock_repo_data
        mock_success_response.headers = {"X-RateLimit-Remaining": "5000"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # First call: timeout, second call: network error, third call: success
            mock_client.get = AsyncMock(
                side_effect=[
                    httpx.TimeoutException("Timeout"),
                    httpx.NetworkError("Network error"),
                    mock_success_response,
                ]
            )
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                stats = await importer.fetch_repo_stats("owner", "repo")

            assert stats.stars == 100

    @pytest.mark.asyncio
    async def test_fetch_repo_stats_max_retries_exceeded(self, importer):
        """Test network error exceeding max retries."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(GitHubAPIError):
                    await importer.fetch_repo_stats("owner", "repo")


# =============================================================================
# Test Caching
# =============================================================================


class TestCaching:
    """Tests for cache behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_api(self, importer, mock_repo_data):
        """Test cache miss triggers API fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = mock_repo_data
        mock_response.headers = {"X-RateLimit-Remaining": "5000"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # Patch cache methods to ensure cache miss
            with patch.object(importer, "_get_cached_stats", return_value=None):
                with patch.object(importer, "_cache_stats") as mock_cache:
                    stats = await importer.fetch_repo_stats("owner", "repo")

                    # Verify API was called
                    mock_client.get.assert_called_once()
                    # Verify result was cached
                    mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_api(self, importer):
        """Test cache hit skips API call."""
        cached_stats = GitHubRepoStats(
            owner="owner",
            repo="repo",
            stars=100,
            forks=10,
            watchers=5,
            open_issues=2,
            last_updated=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )

        with patch.object(importer, "_get_cached_stats", return_value=cached_stats):
            with patch("httpx.AsyncClient") as mock_client_class:
                stats = await importer.fetch_repo_stats("owner", "repo")

                # Verify API was NOT called
                mock_client_class.assert_not_called()
                # Verify cached stats returned
                assert stats.stars == 100

    @pytest.mark.asyncio
    async def test_cache_expiry_fetches_new_data(self, importer, mock_repo_data):
        """Test expired cache triggers new API fetch."""
        # Create expired cache entry (2 hours old, TTL is 1 hour)
        expired_stats = GitHubRepoStats(
            owner="owner",
            repo="repo",
            stars=50,
            forks=5,
            watchers=2,
            open_issues=1,
            last_updated=datetime.now(timezone.utc) - timedelta(hours=2),
            fetched_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = mock_repo_data
        mock_response.headers = {"X-RateLimit-Remaining": "5000"}

        # First call returns expired cache, subsequent calls return None (cache miss)
        cache_calls = [expired_stats, None]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.object(
                importer, "_get_cached_stats", side_effect=cache_calls
            ):
                with patch.object(importer, "_cache_stats"):
                    stats = await importer.fetch_repo_stats("owner", "repo")

                    # Verify new stats fetched
                    assert stats.stars == 150  # From mock_repo_data, not expired cache


# =============================================================================
# Test Import for Artifact
# =============================================================================


class TestImportForArtifact:
    """Tests for importing stats for a single artifact."""

    @pytest.mark.asyncio
    async def test_import_for_github_artifact(self, importer, mock_repo_data):
        """Test importing for GitHub artifact source."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = mock_repo_data
        mock_response.headers = {"X-RateLimit-Remaining": "5000"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.object(importer, "_get_cached_stats", return_value=None):
                with patch.object(importer, "_cache_stats"):
                    score_source = await importer.import_for_artifact(
                        "anthropics/skills/pdf"
                    )

                    assert isinstance(score_source, ScoreSource)
                    assert score_source.source_name == "github_stars"
                    assert 0 <= score_source.score <= 100
                    assert score_source.weight == 0.25
                    assert score_source.sample_size == 150  # Star count
                    assert isinstance(score_source.last_updated, datetime)

    @pytest.mark.asyncio
    async def test_import_for_non_github_source(self, importer):
        """Test importing for non-GitHub source returns None."""
        result = await importer.import_for_artifact("/local/path/to/skill")
        assert result is None

    @pytest.mark.asyncio
    async def test_import_for_nonexistent_repo(self, importer):
        """Test importing for non-existent repo returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.is_success = False

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.object(importer, "_get_cached_stats", return_value=None):
                result = await importer.import_for_artifact("owner/nonexistent")
                assert result is None


# =============================================================================
# Test Batch Import
# =============================================================================


class TestBatchImport:
    """Tests for batch importing stats for multiple artifacts."""

    @pytest.mark.asyncio
    async def test_batch_import_multiple_artifacts(self, importer, mock_repo_data):
        """Test batch import for multiple GitHub artifacts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = mock_repo_data
        mock_response.headers = {"X-RateLimit-Remaining": "5000"}

        sources = [
            "anthropics/skills/pdf",
            "user/repo/skill",
            "/local/path",  # Will be skipped
        ]

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch.object(importer, "_get_cached_stats", return_value=None):
                with patch.object(importer, "_cache_stats"):
                    results = await importer.batch_import(sources, concurrency=2)

                    # Should have 2 results (GitHub sources only)
                    assert len(results) == 2
                    assert all(isinstance(r, ScoreSource) for r in results)

    @pytest.mark.asyncio
    async def test_batch_import_empty_list(self, importer):
        """Test batch import with empty source list."""
        results = await importer.batch_import([], concurrency=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_import_handles_errors(self, importer):
        """Test batch import continues after errors."""
        sources = ["good/repo", "bad/repo", "another/good"]

        async def mock_import(source):
            if source == "bad/repo":
                raise GitHubAPIError("API error")
            return ScoreSource(
                source_name="github_stars",
                score=75.0,
                weight=0.25,
                last_updated=datetime.now(timezone.utc),
                sample_size=100,
            )

        with patch.object(importer, "import_for_artifact", side_effect=mock_import):
            results = await importer.batch_import(sources, concurrency=3)

            # Should have 2 successful results (good repos)
            assert len(results) == 2


# =============================================================================
# Test Integration with Database
# =============================================================================


class TestDatabaseIntegration:
    """Tests for database cache integration."""

    def test_cache_round_trip(self, importer, db_session):
        """Test caching and retrieving stats from database."""
        stats = GitHubRepoStats(
            owner="test_owner",
            repo="test_repo",
            stars=250,
            forks=30,
            watchers=15,
            open_issues=8,
            last_updated=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )

        # Patch get_session to use test database
        with patch(
            "skillmeat.core.scoring.github_stars_importer.get_session",
            return_value=db_session,
        ):
            # Cache stats
            importer._cache_stats(stats)

            # Retrieve from cache
            cached = importer._get_cached_stats("test_owner", "test_repo")

            assert cached is not None
            assert cached.owner == "test_owner"
            assert cached.repo == "test_repo"
            assert cached.stars == 250
            assert cached.forks == 30

    def test_cache_upsert(self, importer, db_session):
        """Test cache entry is updated on re-cache."""
        stats1 = GitHubRepoStats(
            owner="test",
            repo="repo",
            stars=100,
            forks=10,
            watchers=5,
            open_issues=2,
            last_updated=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )

        stats2 = GitHubRepoStats(
            owner="test",
            repo="repo",
            stars=200,  # Updated
            forks=20,
            watchers=10,
            open_issues=5,
            last_updated=datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
        )

        with patch(
            "skillmeat.core.scoring.github_stars_importer.get_session",
            return_value=db_session,
        ):
            # Cache first version
            importer._cache_stats(stats1)

            # Cache second version (should update)
            importer._cache_stats(stats2)

            # Retrieve from cache
            cached = importer._get_cached_stats("test", "repo")

            assert cached.stars == 200  # Updated value
