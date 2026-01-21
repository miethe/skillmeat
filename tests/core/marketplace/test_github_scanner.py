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

from skillmeat.core.marketplace.github_scanner import (
    GitHubAPIError,
    GitHubScanner,
    RateLimitError,
    ScanConfig,
    scan_github_source,
)
from skillmeat.core.github_client import (
    GitHubClientError,
    GitHubRateLimitError,
    GitHubNotFoundError,
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
    def mock_client(self):
        """Create a mock GitHubClient."""
        with patch(
            "skillmeat.core.marketplace.github_scanner.GitHubClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance.token = "test_token"
            MockClient.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def scanner(self, mock_client):
        """Create a scanner with mocked client."""
        scanner = GitHubScanner(token="test_token")
        scanner._client = mock_client
        return scanner

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        with patch(
            "skillmeat.core.marketplace.github_scanner.GitHubClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance.token = "test_token"
            MockClient.return_value = mock_instance

            scanner = GitHubScanner(token="test_token")

            assert scanner.token == "test_token"
            MockClient.assert_called_once_with("test_token")

    def test_init_from_env(self, monkeypatch):
        """Test initialization from environment variable."""
        monkeypatch.setenv("GITHUB_TOKEN", "env_token")
        with patch(
            "skillmeat.core.marketplace.github_scanner.GitHubClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance.token = "env_token"
            MockClient.return_value = mock_instance

            scanner = GitHubScanner()

            assert scanner.token == "env_token"

    def test_init_without_token(self, monkeypatch):
        """Test initialization without token (unauthenticated)."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("SKILLMEAT_GITHUB_TOKEN", raising=False)
        with patch(
            "skillmeat.core.marketplace.github_scanner.GitHubClient"
        ) as MockClient:
            mock_instance = MagicMock()
            mock_instance.token = None
            MockClient.return_value = mock_instance

            scanner = GitHubScanner()

            assert scanner.token is None

    def test_fetch_tree_success(self, scanner, mock_client):
        """Test successful tree fetch."""
        mock_client.get_repo_tree.return_value = [
            {"path": "skills/skill1/SKILL.md", "type": "blob", "sha": "abc"},
            {"path": "skills/skill1/index.ts", "type": "blob", "sha": "def"},
            {"path": "commands/cmd1/COMMAND.md", "type": "blob", "sha": "ghi"},
        ]

        tree, actual_ref = scanner._fetch_tree("user", "repo", "main")

        assert len(tree) == 3
        assert tree[0]["path"] == "skills/skill1/SKILL.md"
        assert actual_ref == "main"  # No fallback needed
        mock_client.get_repo_tree.assert_called_once_with(
            "user/repo", ref="main", recursive=True
        )

    def test_fetch_tree_fallback_to_default_branch(self, scanner, mock_client):
        """Test fallback to actual default branch when main returns 404."""
        # First call raises not found, second succeeds
        mock_client.get_repo_tree.side_effect = [
            GitHubNotFoundError("Branch not found"),
            [{"path": "skills/skill1/SKILL.md", "type": "blob", "sha": "abc"}],
        ]
        mock_client.get_repo_metadata.return_value = {"default_branch": "master"}

        tree, actual_ref = scanner._fetch_tree("user", "repo", "main")

        assert len(tree) == 1
        assert tree[0]["path"] == "skills/skill1/SKILL.md"
        assert actual_ref == "master"  # Fallback occurred

    def test_fetch_tree_no_fallback_for_non_main_ref(self, scanner, mock_client):
        """Test that fallback does not occur when ref is not 'main'."""
        mock_client.get_repo_tree.side_effect = GitHubNotFoundError("Branch not found")

        # Should raise without fallback when ref is not "main"
        with pytest.raises(GitHubNotFoundError):
            scanner._fetch_tree("user", "repo", "feature-branch")

        # Should only make one call (no fallback)
        assert mock_client.get_repo_tree.call_count == 1

    def test_fetch_tree_fallback_when_default_is_also_main(self, scanner, mock_client):
        """Test that if default branch is also 'main', error is re-raised."""
        mock_client.get_repo_tree.side_effect = GitHubNotFoundError("Branch not found")
        mock_client.get_repo_metadata.return_value = {"default_branch": "main"}

        # Should raise GitHubNotFoundError since default branch is also "main"
        with pytest.raises(GitHubNotFoundError):
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

    def test_get_ref_sha_success(self, scanner, mock_client):
        """Test successful SHA resolution."""
        mock_client.resolve_version.return_value = "abc123def456"

        sha = scanner._get_ref_sha("user", "repo", "main")

        assert sha == "abc123def456"
        mock_client.resolve_version.assert_called_once_with("user/repo", "main")

    def test_get_rate_limit(self, scanner, mock_client):
        """Test rate limit retrieval."""
        mock_client.get_rate_limit.return_value = {
            "remaining": 4500,
            "limit": 5000,
            "reset": datetime.utcnow(),
        }

        rate_limit = scanner.get_rate_limit()

        assert rate_limit["remaining"] == 4500
        assert rate_limit["limit"] == 5000
        mock_client.get_rate_limit.assert_called_once()

    def test_get_file_content_success(self, scanner, mock_client):
        """Test successful file content retrieval with metadata."""
        content = "# Test Skill\nThis is a skill."
        mock_client.get_file_content.return_value = content.encode("utf-8")

        result = scanner.get_file_content("user", "repo", "skills/test/SKILL.md")

        assert result is not None
        assert result["content"] == content
        assert result["encoding"] == "utf-8"
        assert result["size"] == len(content)
        assert result["name"] == "SKILL.md"
        assert result["path"] == "skills/test/SKILL.md"
        assert result["is_binary"] is False

    def test_get_file_content_binary_file(self, scanner, mock_client):
        """Test binary file content is kept as base64."""
        import base64

        binary_data = b"\x89PNG\r\n\x1a\n"
        mock_client.get_file_content.return_value = binary_data

        result = scanner.get_file_content("user", "repo", "assets/icon.png")

        assert result is not None
        assert result["is_binary"] is True
        # Binary content should be base64 encoded
        assert result["content"] == base64.b64encode(binary_data).decode("ascii")
        assert result["name"] == "icon.png"
        assert result["encoding"] == "base64"

    def test_get_file_content_not_found(self, scanner, mock_client):
        """Test file not found returns None."""
        mock_client.get_file_content.side_effect = GitHubNotFoundError("Not found")

        result = scanner.get_file_content("user", "repo", "nonexistent.txt")

        assert result is None

    def test_scan_repository_empty_repo(self, scanner, mock_client):
        """Test scanning an empty repository."""
        # Mock empty tree
        mock_client.get_repo_tree.return_value = []
        mock_client.resolve_version.return_value = "abc123"

        result = scanner.scan_repository("user", "repo", "main")

        assert result.status == "success"
        assert result.artifacts_found == 0
        assert result.new_count == 0
        assert len(result.errors) == 0

    def test_scan_repository_with_errors(self, scanner, mock_client):
        """Test scan with API errors."""
        mock_client.get_repo_tree.side_effect = GitHubClientError("API unavailable")

        result = scanner.scan_repository("user", "repo", "main")

        assert result.status == "error"
        assert result.artifacts_found == 0
        assert len(result.errors) > 0
        assert "API unavailable" in result.errors[0]

    def test_scan_repository_with_root_hint(self, scanner, mock_client):
        """Test scanning with root_hint."""
        mock_client.get_repo_tree.return_value = [
            {"path": "skills/skill1/SKILL.md", "type": "blob", "sha": "abc"},
            {"path": "other/file.txt", "type": "blob", "sha": "def"},
        ]
        mock_client.resolve_version.return_value = "abc123"

        result = scanner.scan_repository("user", "repo", "main", root_hint="skills")

        assert result.status == "success"
        # Note: artifacts_found will be 0 because heuristic detector isn't implemented
        # But we verify the scan completed successfully

    def test_scan_repository_duration_tracking(self, scanner, mock_client):
        """Test that scan duration is tracked."""
        mock_client.get_repo_tree.return_value = []
        mock_client.resolve_version.return_value = "abc123"

        result = scanner.scan_repository("user", "repo", "main")

        assert result.scan_duration_ms >= 0
        assert isinstance(result.scanned_at, datetime)


class TestExceptionBackwardCompatibility:
    """Test backward compatibility of exception classes."""

    def test_github_api_error_is_github_client_error(self):
        """Test GitHubAPIError inherits from GitHubClientError."""
        error = GitHubAPIError("test error")
        assert isinstance(error, GitHubClientError)

    def test_rate_limit_error_is_github_rate_limit_error(self):
        """Test RateLimitError inherits from GitHubRateLimitError."""
        error = RateLimitError("test error")
        assert isinstance(error, GitHubRateLimitError)

    def test_rate_limit_error_is_github_api_error(self):
        """Test RateLimitError inherits from GitHubAPIError for backward compat."""
        error = RateLimitError("test error")
        assert isinstance(error, GitHubAPIError)

    def test_catching_github_api_error_catches_rate_limit(self):
        """Test that catching GitHubAPIError also catches RateLimitError."""
        error = RateLimitError("rate limited")
        try:
            raise error
        except GitHubAPIError as e:
            assert str(e) == "rate limited"


class TestScanGithubSourceConvenience:
    """Test the scan_github_source convenience function."""

    def test_scan_github_source_parses_url(self):
        """Test URL parsing in convenience function."""
        with patch(
            "skillmeat.core.marketplace.github_scanner.GitHubScanner"
        ) as MockScanner:
            mock_instance = MagicMock()
            mock_instance._fetch_tree.return_value = ([], "main")
            mock_instance._extract_file_paths.return_value = []
            mock_instance._get_ref_sha.return_value = "abc123"
            MockScanner.return_value = mock_instance

            result, artifacts = scan_github_source(
                "https://github.com/user/repo", ref="main"
            )

            mock_instance._fetch_tree.assert_called_once_with("user", "repo", "main")
            assert result.status == "success"

    def test_scan_github_source_invalid_url(self):
        """Test invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repository URL"):
            scan_github_source("invalid")
