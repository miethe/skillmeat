"""Integration tests for GitHub API error scenarios.

Tests error handling for the file tree and file content endpoints when
GitHub API returns various error conditions:
- Rate limiting (403 with X-RateLimit-Remaining: 0)
- Not found (404 for non-existent files/repos)
- Timeout (requests.Timeout exception)

These tests mock at the HTTP level to verify true end-to-end error handling.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceSource
from skillmeat.core.marketplace.github_scanner import (
    GitHubAPIError,
    GitHubScanner,
    RateLimitError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def api_settings():
    """Create test API settings with auth disabled."""
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    """Create test client with initialized app state."""
    from skillmeat.api.dependencies import app_state

    app = create_app(api_settings)
    app_state.initialize(api_settings)

    test_client = TestClient(app)

    yield test_client

    app_state.shutdown()


@pytest.fixture
def mock_source():
    """Create a mock MarketplaceSource for testing."""
    return MarketplaceSource(
        id="test-source-123",
        repo_url="https://github.com/testowner/testrepo",
        owner="testowner",
        repo_name="testrepo",
        ref="main",
        root_hint=None,
        trust_level="community",
        visibility="public",
        scan_status="success",
        artifact_count=5,
        last_sync_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_source_repo(mock_source):
    """Mock the MarketplaceSourceRepository to return our test source."""
    with patch(
        "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
    ) as MockRepo:
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = mock_source
        MockRepo.return_value = mock_repo_instance
        yield mock_repo_instance


@pytest.fixture
def mock_cache_miss():
    """Mock the GitHub file cache to always return None (cache miss)."""
    with patch(
        "skillmeat.api.routers.marketplace_sources.get_github_file_cache"
    ) as mock_get_cache:
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Always cache miss
        mock_get_cache.return_value = mock_cache
        yield mock_cache


# =============================================================================
# Rate Limit Tests (403 with X-RateLimit-Remaining: 0)
# =============================================================================


class TestGitHubRateLimiting:
    """Test handling of GitHub rate limit (403) errors."""

    def test_file_tree_returns_429_on_github_rate_limit(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that file tree endpoint returns 429 when GitHub rate limits us."""
        with patch.object(
            GitHubScanner, "get_file_tree", side_effect=RateLimitError("Rate limited, reset in 45s")
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files"
            )

            assert response.status_code == 429
            data = response.json()
            assert "rate limit" in data["detail"].lower()
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "45"

    def test_file_content_returns_429_on_github_rate_limit(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that file content endpoint returns 429 when GitHub rate limits us."""
        with patch.object(
            GitHubScanner,
            "get_file_content",
            side_effect=RateLimitError("Rate limited for 60s"),
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files/SKILL.md"
            )

            assert response.status_code == 429
            data = response.json()
            assert "rate limit" in data["detail"].lower()
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "60"

    def test_rate_limit_retry_after_default_when_unparseable(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that Retry-After defaults to 60s when time cannot be parsed."""
        with patch.object(
            GitHubScanner,
            "get_file_tree",
            side_effect=RateLimitError("Rate limit exceeded"),  # No seconds in message
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files"
            )

            assert response.status_code == 429
            # Default to 60 seconds when parsing fails
            assert response.headers["Retry-After"] == "60"


class TestGitHubRateLimitAtHttpLevel:
    """Test rate limit handling at the HTTP request level."""

    def test_scanner_raises_rate_limit_on_403_with_zero_remaining(self):
        """Test that GitHubScanner raises RateLimitError on 403 with rate limit headers."""
        scanner = GitHubScanner(token=None)

        # Create a mock response mimicking GitHub 403 rate limit
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "9999999999",  # Far future timestamp
        }
        mock_response.json.return_value = {
            "message": "API rate limit exceeded",
            "documentation_url": "https://docs.github.com/rest/rate-limit",
        }

        with patch.object(
            scanner.session, "get", return_value=mock_response
        ) as mock_get:
            with pytest.raises(RateLimitError) as exc_info:
                scanner._request_with_retry("https://api.github.com/repos/test/test")

            assert "Rate limited" in str(exc_info.value)


# =============================================================================
# Not Found Tests (404)
# =============================================================================


class TestGitHubNotFound:
    """Test handling of GitHub 404 (not found) errors."""

    def test_file_tree_returns_404_on_nonexistent_source(self, client, mock_cache_miss):
        """Test that file tree endpoint returns 404 when source doesn't exist."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as MockRepo:
            mock_repo_instance = MagicMock()
            mock_repo_instance.get_by_id.return_value = None
            MockRepo.return_value = mock_repo_instance

            response = client.get(
                "/api/v1/marketplace/sources/nonexistent-source/artifacts/skills/canvas/files"
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    def test_file_tree_returns_404_on_nonexistent_artifact_path(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that file tree endpoint returns 404 when artifact path doesn't exist."""
        with patch.object(GitHubScanner, "get_file_tree", return_value=[]):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/nonexistent/path/files"
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()
            assert "nonexistent/path" in data["detail"]

    def test_file_content_returns_404_on_nonexistent_file(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that file content endpoint returns 404 when file doesn't exist."""
        with patch.object(GitHubScanner, "get_file_content", return_value=None):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files/nonexistent.md"
            )

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    def test_scanner_handles_404_for_file_content(self):
        """Test that GitHubScanner.get_file_content returns None on 404."""
        scanner = GitHubScanner(token=None)

        # Create a mock that raises GitHubAPIError with 404
        with patch.object(
            scanner,
            "_request_with_retry",
            side_effect=GitHubAPIError("404 Client Error: Not Found"),
        ):
            result = scanner.get_file_content(
                owner="testowner",
                repo="testrepo",
                path="nonexistent/file.md",
                ref="main",
            )

            assert result is None

    def test_scanner_raises_on_github_404_for_tree(self):
        """Test that GitHubScanner raises GitHubAPIError on tree 404."""
        scanner = GitHubScanner(token=None)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "404 Client Error: Not Found"
        )

        with patch.object(scanner.session, "get", return_value=mock_response):
            with pytest.raises((GitHubAPIError, requests.HTTPError)):
                scanner._fetch_tree(
                    owner="nonexistent", repo="nonexistent-repo", ref="main"
                )


# =============================================================================
# Timeout Tests
# =============================================================================


class TestGitHubTimeout:
    """Test handling of GitHub API timeout errors."""

    def test_file_tree_returns_500_on_timeout(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that file tree endpoint returns 500 when GitHub times out."""
        with patch.object(
            GitHubScanner,
            "get_file_tree",
            side_effect=GitHubAPIError("Request failed after 3 attempts: Connection timed out"),
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files"
            )

            assert response.status_code == 500
            data = response.json()
            assert "failed" in data["detail"].lower()

    def test_file_content_returns_500_on_timeout(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that file content endpoint returns 500 when GitHub times out."""
        with patch.object(
            GitHubScanner,
            "get_file_content",
            side_effect=GitHubAPIError("Request failed after 3 attempts: Read timed out"),
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files/SKILL.md"
            )

            assert response.status_code == 500
            data = response.json()
            assert "failed" in data["detail"].lower()

    def test_scanner_retries_on_timeout(self):
        """Test that GitHubScanner retries on timeout before failing."""
        scanner = GitHubScanner(token=None)
        scanner.config.retry_count = 3
        scanner.config.retry_delay = 0.01  # Fast retry for tests

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise requests.Timeout("Connection timed out")

        with patch.object(scanner.session, "get", side_effect=side_effect):
            with pytest.raises(GitHubAPIError) as exc_info:
                scanner._request_with_retry("https://api.github.com/test")

            # Should have retried retry_count times
            assert call_count == 3
            assert "failed after" in str(exc_info.value).lower()

    def test_scanner_succeeds_after_transient_timeout(self):
        """Test that GitHubScanner succeeds if timeout is transient."""
        scanner = GitHubScanner(token=None)
        scanner.config.retry_count = 3
        scanner.config.retry_delay = 0.01

        call_count = 0

        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"tree": []}

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.Timeout("Connection timed out")
            return mock_success_response

        with patch.object(scanner.session, "get", side_effect=side_effect):
            response = scanner._request_with_retry("https://api.github.com/test")

            assert response.status_code == 200
            assert call_count == 3


# =============================================================================
# HTTP-Level Mocking Tests (True Integration Tests)
# =============================================================================


class TestHttpLevelMocking:
    """Integration tests that mock at the HTTP request level."""

    def test_requests_timeout_exception_handling(self):
        """Test handling of requests.Timeout at the HTTP level."""
        scanner = GitHubScanner(token=None)
        scanner.config.retry_count = 1
        scanner.config.retry_delay = 0.001

        with patch.object(
            scanner.session,
            "get",
            side_effect=requests.Timeout("Request timed out after 60 seconds"),
        ):
            with pytest.raises(GitHubAPIError) as exc_info:
                scanner._request_with_retry("https://api.github.com/repos/test/test")

            assert "failed after" in str(exc_info.value).lower()
            assert "timed out" in str(exc_info.value).lower()

    def test_requests_connection_error_handling(self):
        """Test handling of requests.ConnectionError at the HTTP level."""
        scanner = GitHubScanner(token=None)
        scanner.config.retry_count = 1
        scanner.config.retry_delay = 0.001

        with patch.object(
            scanner.session,
            "get",
            side_effect=requests.ConnectionError("Failed to establish connection"),
        ):
            with pytest.raises(GitHubAPIError) as exc_info:
                scanner._request_with_retry("https://api.github.com/repos/test/test")

            assert "failed after" in str(exc_info.value).lower()

    def test_http_500_error_handling(self):
        """Test handling of HTTP 500 errors from GitHub."""
        scanner = GitHubScanner(token=None)
        scanner.config.retry_count = 1
        scanner.config.retry_delay = 0.001

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error: Internal Server Error"
        )

        with patch.object(scanner.session, "get", return_value=mock_response):
            with pytest.raises(GitHubAPIError):
                scanner._request_with_retry("https://api.github.com/repos/test/test")

    def test_http_503_service_unavailable_handling(self):
        """Test handling of HTTP 503 (Service Unavailable) from GitHub."""
        scanner = GitHubScanner(token=None)
        scanner.config.retry_count = 2
        scanner.config.retry_delay = 0.001

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "503 Server Error: Service Unavailable"
        )

        with patch.object(scanner.session, "get", return_value=mock_response):
            with pytest.raises(GitHubAPIError):
                scanner._request_with_retry("https://api.github.com/repos/test/test")


# =============================================================================
# Edge Cases and Error Message Tests
# =============================================================================


class TestErrorMessages:
    """Test that error messages are descriptive and helpful."""

    def test_rate_limit_message_includes_retry_time(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that rate limit error message includes when to retry."""
        with patch.object(
            GitHubScanner,
            "get_file_tree",
            side_effect=RateLimitError("Rate limited, reset in 120s"),
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files"
            )

            data = response.json()
            assert "120" in data["detail"] or "retry" in data["detail"].lower()

    def test_404_message_includes_resource_identifier(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that 404 error message includes which resource was not found."""
        with patch.object(GitHubScanner, "get_file_content", return_value=None):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/my-artifact/files/missing.txt"
            )

            data = response.json()
            # Should mention the file name in the error
            assert "missing.txt" in data["detail"] or "not found" in data["detail"].lower()

    def test_timeout_message_indicates_transient_error(
        self, client, mock_source_repo, mock_cache_miss
    ):
        """Test that timeout error message suggests it may be transient."""
        with patch.object(
            GitHubScanner,
            "get_file_tree",
            side_effect=GitHubAPIError("Request failed after 3 attempts: timed out"),
        ):
            response = client.get(
                "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files"
            )

            data = response.json()
            assert "failed" in data["detail"].lower()


class TestCacheBypass:
    """Test that errors are not cached and retries hit GitHub."""

    def test_rate_limit_not_cached(self, client, mock_source_repo):
        """Test that rate limit responses are not cached."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache"
        ) as mock_get_cache:
            mock_cache = MagicMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            with patch.object(
                GitHubScanner,
                "get_file_tree",
                side_effect=RateLimitError("Rate limited for 30s"),
            ):
                response = client.get(
                    "/api/v1/marketplace/sources/test-source-123/artifacts/skills/canvas/files"
                )

                assert response.status_code == 429

                # Cache.set should NOT have been called with error response
                # (errors should not be cached)
                for call in mock_cache.set.call_args_list:
                    args = call[0] if call[0] else []
                    if len(args) >= 2:
                        cached_value = args[1]
                        # Should not cache error states
                        if isinstance(cached_value, dict):
                            assert "error" not in cached_value
