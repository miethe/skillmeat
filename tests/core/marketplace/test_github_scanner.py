"""Tests for GitHub repository scanner.

Tests cover:
- Repository scanning pipeline
- GitHub API interactions with mocking
- Rate limiting and retry logic
- Error handling
- Edge cases (empty repos, timeouts, malformed responses)
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from skillmeat.core.marketplace.github_scanner import (
    GitHubAPIError,
    GitHubScanner,
    RateLimitError,
    ScanConfig,
    scan_github_source,
)


class TestScanConfig:
    """Test suite for ScanConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ScanConfig()
        assert config.timeout == 60
        assert config.max_files == 5000
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert config.cache_ttl_seconds == 300

    def test_custom_config(self):
        """Test custom configuration."""
        config = ScanConfig(
            timeout=30,
            max_files=1000,
            retry_count=5,
            retry_delay=2.0,
        )
        assert config.timeout == 30
        assert config.max_files == 1000
        assert config.retry_count == 5
        assert config.retry_delay == 2.0


class TestGitHubScanner:
    """Test suite for GitHubScanner."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock requests session."""
        session = MagicMock()
        session.headers = {}
        return session

    @pytest.fixture
    def scanner(self, mock_session):
        """Create a scanner with mocked session."""
        scanner = GitHubScanner(token="test_token")
        scanner.session = mock_session
        return scanner

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        scanner = GitHubScanner(token="test_token")
        assert scanner.token == "test_token"
        assert "Authorization" in scanner.session.headers

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        scanner = GitHubScanner()
        assert scanner.token == "env_token"

    def test_init_without_token(self, monkeypatch):
        """Test initialization without token (unauthenticated)."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("SKILLMEAT_GITHUB_TOKEN", raising=False)
        scanner = GitHubScanner()
        assert scanner.token is None

    def test_fetch_tree_success(self, scanner, mock_session):
        """Test successful tree fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "tree": [
                {"path": "skills/skill1/SKILL.md", "type": "blob"},
                {"path": "skills/skill1/index.ts", "type": "blob"},
                {"path": "commands/cmd1/COMMAND.md", "type": "blob"},
            ]
        }
        mock_session.get.return_value = mock_response

        tree = scanner._fetch_tree("user", "repo", "main")

        assert len(tree) == 3
        assert tree[0]["path"] == "skills/skill1/SKILL.md"
        mock_session.get.assert_called_once()

    def test_fetch_tree_invalid_response(self, scanner, mock_session):
        """Test handling of invalid tree response."""
        mock_response = Mock()
        mock_response.json.return_value = {"error": "Not found"}
        mock_session.get.return_value = mock_response

        with pytest.raises(GitHubAPIError, match="Invalid tree response"):
            scanner._fetch_tree("user", "repo", "main")

    def test_extract_file_paths_no_filter(self, scanner):
        """Test path extraction without filtering."""
        tree = [
            {"path": "skills/skill1/SKILL.md", "type": "blob"},
            {"path": "README.md", "type": "blob"},
            {"path": "src/utils.py", "type": "blob"},
            {"path": "skills", "type": "tree"},  # Should be filtered out
        ]

        paths = scanner._extract_file_paths(tree)

        assert len(paths) == 3
        assert "skills/skill1/SKILL.md" in paths
        assert "README.md" in paths
        assert "src/utils.py" in paths
        assert "skills" not in paths  # Tree entry should be excluded

    def test_extract_file_paths_with_root_hint(self, scanner):
        """Test path extraction with root_hint filter."""
        tree = [
            {"path": "skills/skill1/SKILL.md", "type": "blob"},
            {"path": "skills/skill2/SKILL.md", "type": "blob"},
            {"path": "commands/cmd1/COMMAND.md", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ]

        paths = scanner._extract_file_paths(tree, root_hint="skills")

        assert len(paths) == 2
        assert "skills/skill1/SKILL.md" in paths
        assert "skills/skill2/SKILL.md" in paths
        assert "commands/cmd1/COMMAND.md" not in paths
        assert "README.md" not in paths

    def test_extract_file_paths_max_files_limit(self, scanner):
        """Test that file list is truncated at max_files."""
        scanner.config.max_files = 10
        tree = [{"path": f"file{i}.txt", "type": "blob"} for i in range(100)]

        paths = scanner._extract_file_paths(tree)

        assert len(paths) == 10

    def test_get_ref_sha_success(self, scanner, mock_session):
        """Test successful SHA resolution."""
        mock_response = Mock()
        mock_response.json.return_value = {"sha": "abc123def456"}
        mock_session.get.return_value = mock_response

        sha = scanner._get_ref_sha("user", "repo", "main")

        assert sha == "abc123def456"
        mock_session.get.assert_called_once()

    def test_request_with_retry_success(self, scanner, mock_session):
        """Test successful request on first try."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response

        response = scanner._request_with_retry("https://api.github.com/test")

        assert response == mock_response
        mock_session.get.assert_called_once()

    def test_request_with_retry_transient_failure(self, scanner, mock_session):
        """Test retry on transient failure."""
        # First call fails, second succeeds
        failed_response = Mock()
        failed_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "Timeout"
        )

        success_response = Mock()
        success_response.status_code = 200
        success_response.raise_for_status = Mock()

        mock_session.get.side_effect = [failed_response, success_response]

        response = scanner._request_with_retry("https://api.github.com/test")

        assert response == success_response
        assert mock_session.get.call_count == 2

    def test_request_with_retry_rate_limit_403(self, scanner, mock_session):
        """Test handling of 403 rate limit with reset time."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 30),  # 30 seconds from now
        }
        mock_session.get.return_value = mock_response

        with pytest.raises(RateLimitError, match="Rate limited"):
            scanner._request_with_retry("https://api.github.com/test")

    def test_request_with_retry_rate_limit_429(self, scanner, mock_session):
        """Test handling of 429 rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}
        mock_session.get.return_value = mock_response

        with pytest.raises(RateLimitError, match="Rate limited for 120s"):
            scanner._request_with_retry("https://api.github.com/test")

    def test_request_with_retry_max_retries_exceeded(self, scanner, mock_session):
        """Test failure after max retries."""
        scanner.config.retry_count = 2
        mock_session.get.side_effect = requests.exceptions.RequestException("Error")

        with pytest.raises(GitHubAPIError, match="failed after 2 attempts"):
            scanner._request_with_retry("https://api.github.com/test")

        assert mock_session.get.call_count == 2

    def test_get_file_content_success(self, scanner, mock_session):
        """Test successful file content retrieval."""
        import base64

        content = "# Test Skill\nThis is a skill."
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        mock_response = Mock()
        mock_response.json.return_value = {
            "content": encoded,
            "encoding": "base64",
        }
        mock_session.get.return_value = mock_response

        result = scanner.get_file_content("user", "repo", "skills/test/SKILL.md")

        assert result == content

    def test_get_file_content_no_encoding(self, scanner, mock_session):
        """Test file content retrieval without encoding."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "content": "plain text content",
        }
        mock_session.get.return_value = mock_response

        result = scanner.get_file_content("user", "repo", "README.md")

        assert result == "plain text content"

    def test_scan_repository_empty_repo(self, scanner, mock_session):
        """Test scanning an empty repository."""
        # Mock empty tree
        tree_response = Mock()
        tree_response.json.return_value = {"tree": []}
        tree_response.raise_for_status = Mock()

        # Mock commit SHA
        commit_response = Mock()
        commit_response.json.return_value = {"sha": "abc123"}
        commit_response.raise_for_status = Mock()

        mock_session.get.side_effect = [tree_response, commit_response]

        result = scanner.scan_repository("user", "repo", "main")

        assert result.status == "success"
        assert result.artifacts_found == 0
        assert result.new_count == 0
        assert len(result.errors) == 0

    def test_scan_repository_with_errors(self, scanner, mock_session):
        """Test scan with API errors."""
        mock_session.get.side_effect = requests.exceptions.RequestException(
            "API unavailable"
        )

        result = scanner.scan_repository("user", "repo", "main")

        assert result.status == "error"
        assert result.artifacts_found == 0
        assert len(result.errors) > 0
        assert "API unavailable" in result.errors[0]

    def test_scan_repository_with_root_hint(self, scanner, mock_session):
        """Test scanning with root_hint."""
        tree_response = Mock()
        tree_response.json.return_value = {
            "tree": [
                {"path": "skills/skill1/SKILL.md", "type": "blob"},
                {"path": "other/file.txt", "type": "blob"},
            ]
        }
        tree_response.raise_for_status = Mock()

        commit_response = Mock()
        commit_response.json.return_value = {"sha": "abc123"}
        commit_response.raise_for_status = Mock()

        mock_session.get.side_effect = [tree_response, commit_response]

        result = scanner.scan_repository("user", "repo", "main", root_hint="skills")

        assert result.status == "success"
        # Note: artifacts_found will be 0 because heuristic detector isn't implemented
        # But we verify the scan completed successfully

    def test_scan_repository_duration_tracking(self, scanner, mock_session):
        """Test that scan duration is tracked."""
        tree_response = Mock()
        tree_response.json.return_value = {"tree": []}
        tree_response.raise_for_status = Mock()

        commit_response = Mock()
        commit_response.json.return_value = {"sha": "abc123"}
        commit_response.raise_for_status = Mock()

        mock_session.get.side_effect = [tree_response, commit_response]

        result = scanner.scan_repository("user", "repo", "main")

        assert result.scan_duration_ms >= 0
        assert isinstance(result.scanned_at, datetime)


class TestScanGitHubSource:
    """Test suite for scan_github_source convenience function."""

    def test_parse_valid_url(self):
        """Test parsing a valid GitHub URL."""
        with patch.object(GitHubScanner, "_fetch_tree") as mock_fetch_tree:
            with patch.object(GitHubScanner, "_extract_file_paths") as mock_extract:
                with patch.object(GitHubScanner, "_get_ref_sha") as mock_get_sha:
                    mock_fetch_tree.return_value = []
                    mock_extract.return_value = []
                    mock_get_sha.return_value = "abc123"

                    result, artifacts = scan_github_source(
                        "https://github.com/anthropics/quickstarts"
                    )

                    assert result.status == "success"
                    assert isinstance(artifacts, list)
                    mock_fetch_tree.assert_called_once_with(
                        "anthropics", "quickstarts", "main"
                    )

    def test_parse_url_with_git_suffix(self):
        """Test parsing URL with .git suffix."""
        with patch.object(GitHubScanner, "_fetch_tree") as mock_fetch_tree:
            with patch.object(GitHubScanner, "_extract_file_paths") as mock_extract:
                with patch.object(GitHubScanner, "_get_ref_sha") as mock_get_sha:
                    mock_fetch_tree.return_value = []
                    mock_extract.return_value = []
                    mock_get_sha.return_value = "abc123"

                    result, artifacts = scan_github_source(
                        "https://github.com/user/repo.git"
                    )

                    assert result.status == "success"
                    mock_fetch_tree.assert_called_once_with("user", "repo", "main")

    def test_parse_invalid_url(self):
        """Test handling of invalid URL."""
        with pytest.raises(ValueError, match="Invalid repository URL"):
            scan_github_source("not-a-url")

    def test_with_custom_ref(self):
        """Test scanning with custom ref."""
        with patch.object(GitHubScanner, "_fetch_tree") as mock_fetch_tree:
            with patch.object(GitHubScanner, "_extract_file_paths") as mock_extract:
                with patch.object(GitHubScanner, "_get_ref_sha") as mock_get_sha:
                    mock_fetch_tree.return_value = []
                    mock_extract.return_value = []
                    mock_get_sha.return_value = "def456"

                    result, artifacts = scan_github_source(
                        "https://github.com/user/repo", ref="v1.0.0"
                    )

                    mock_fetch_tree.assert_called_once_with("user", "repo", "v1.0.0")

    def test_with_root_hint(self):
        """Test scanning with root_hint."""
        with patch.object(GitHubScanner, "_fetch_tree") as mock_fetch_tree:
            with patch.object(GitHubScanner, "_extract_file_paths") as mock_extract:
                with patch.object(GitHubScanner, "_get_ref_sha") as mock_get_sha:
                    mock_fetch_tree.return_value = []
                    mock_extract.return_value = []
                    mock_get_sha.return_value = "abc123"

                    result, artifacts = scan_github_source(
                        "https://github.com/user/repo", root_hint="skills"
                    )

                    mock_extract.assert_called_once()
                    call_args = mock_extract.call_args
                    assert call_args[0][1] == "skills"  # root_hint argument


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_github_api_error_exception(self):
        """Test GitHubAPIError exception."""
        error = GitHubAPIError("API call failed")
        assert str(error) == "API call failed"
        assert isinstance(error, Exception)

    def test_rate_limit_error_exception(self):
        """Test RateLimitError exception."""
        error = RateLimitError("Rate limited")
        assert str(error) == "Rate limited"
        assert isinstance(error, GitHubAPIError)

    def test_network_timeout(self):
        """Test handling of network timeout."""
        scanner = GitHubScanner()
        scanner.config.retry_count = 1

        with patch.object(
            scanner.session,
            "get",
            side_effect=requests.exceptions.Timeout("Timeout"),
        ):
            with pytest.raises(GitHubAPIError, match="failed after"):
                scanner._request_with_retry("https://api.github.com/test")

    def test_connection_error(self):
        """Test handling of connection error."""
        scanner = GitHubScanner()
        scanner.config.retry_count = 1

        with patch.object(
            scanner.session,
            "get",
            side_effect=requests.exceptions.ConnectionError("Connection failed"),
        ):
            with pytest.raises(GitHubAPIError, match="failed after"):
                scanner._request_with_retry("https://api.github.com/test")


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_empty_tree_response(self):
        """Test handling of empty tree response."""
        scanner = GitHubScanner()
        with patch.object(scanner.session, "get") as mock_get:
            tree_response = Mock()
            tree_response.json.return_value = {"tree": []}
            tree_response.raise_for_status = Mock()

            commit_response = Mock()
            commit_response.json.return_value = {"sha": "abc123"}
            commit_response.raise_for_status = Mock()

            mock_get.side_effect = [tree_response, commit_response]

            result = scanner.scan_repository("user", "empty-repo", "main")

            assert result.status == "success"
            assert result.artifacts_found == 0

    def test_malformed_json_response(self):
        """Test handling of malformed JSON response."""
        scanner = GitHubScanner()
        with patch.object(scanner.session, "get") as mock_get:
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response

            with pytest.raises(GitHubAPIError):
                scanner._fetch_tree("user", "repo", "main")

    def test_unicode_paths(self):
        """Test handling of unicode characters in paths."""
        scanner = GitHubScanner()
        tree = [
            {"path": "skills/日本語/SKILL.md", "type": "blob"},
            {"path": "skills/émoji/SKILL.md", "type": "blob"},
        ]

        paths = scanner._extract_file_paths(tree)

        assert len(paths) == 2
        assert "skills/日本語/SKILL.md" in paths
        assert "skills/émoji/SKILL.md" in paths

    def test_very_deep_paths(self):
        """Test handling of very deep directory paths."""
        scanner = GitHubScanner()
        tree = [
            {
                "path": "a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/q/r/s/t/u/v/w/x/y/z/SKILL.md",
                "type": "blob",
            }
        ]

        paths = scanner._extract_file_paths(tree)

        assert len(paths) == 1

    def test_special_characters_in_paths(self):
        """Test handling of special characters in paths."""
        scanner = GitHubScanner()
        tree = [
            {"path": "skills/my-skill (v2)/SKILL.md", "type": "blob"},
            {"path": "skills/skill-with-#hash/SKILL.md", "type": "blob"},
        ]

        paths = scanner._extract_file_paths(tree)

        assert len(paths) == 2
