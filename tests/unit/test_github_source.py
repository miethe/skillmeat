"""Tests for GitHub source."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.sources.github import ArtifactSpec, GitHubClient, GitHubSource


class TestGitHubClient:
    """Test GitHubClient functionality."""

    def test_init_with_token(self):
        """Test initializing client with token."""
        client = GitHubClient(github_token="test_token")
        assert client.token == "test_token"
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "token test_token"

    def test_init_without_token(self):
        """Test initializing client without token."""
        with patch.dict("os.environ", {}, clear=True):
            client = GitHubClient()
            assert client.token is None

    @patch("skillmeat.sources.github.requests.Session.get")
    def test_resolve_version_latest(self, mock_get):
        """Test resolving 'latest' version."""
        # Mock API responses
        repo_response = Mock()
        repo_response.json.return_value = {"default_branch": "main"}
        repo_response.raise_for_status = Mock()

        commit_response = Mock()
        commit_response.json.return_value = {"sha": "abc123"}
        commit_response.raise_for_status = Mock()

        mock_get.side_effect = [repo_response, commit_response]

        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills@latest")
        sha, version = client.resolve_version(spec)

        assert sha == "abc123"
        assert version is None
        assert mock_get.call_count == 2

    @patch("skillmeat.sources.github.requests.Session.get")
    def test_resolve_version_tag(self, mock_get):
        """Test resolving version tag."""
        tag_response = Mock()
        tag_response.json.return_value = {"object": {"sha": "def456"}}
        tag_response.raise_for_status = Mock()

        mock_get.return_value = tag_response

        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills@v1.0.0")
        sha, version = client.resolve_version(spec)

        assert sha == "def456"
        assert version == "v1.0.0"

    @patch("skillmeat.sources.github.requests.Session.get")
    def test_resolve_version_sha(self, mock_get):
        """Test resolving commit SHA."""
        commit_response = Mock()
        commit_response.json.return_value = {"sha": "abc123def456"}
        commit_response.raise_for_status = Mock()

        mock_get.return_value = commit_response

        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills@abc123def456")
        sha, version = client.resolve_version(spec)

        assert sha == "abc123def456"
        assert version is None

    @patch("skillmeat.sources.github.requests.Session.get")
    def test_resolve_version_branch(self, mock_get):
        """Test resolving branch name."""
        commit_response = Mock()
        commit_response.json.return_value = {"sha": "ghi789"}
        commit_response.raise_for_status = Mock()

        mock_get.return_value = commit_response

        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills@develop")
        sha, version = client.resolve_version(spec)

        assert sha == "ghi789"
        assert version is None

    @patch("skillmeat.sources.github.requests.Session.get")
    def test_resolve_version_tag_not_found(self, mock_get):
        """Test resolving non-existent tag."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=Mock(status_code=404)
        )

        mock_get.return_value = mock_response

        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills@v99.99.99")

        with pytest.raises(RuntimeError, match="not found"):
            client.resolve_version(spec)

    @patch("skillmeat.sources.github.requests.Session.get")
    def test_resolve_version_retry_on_error(self, mock_get):
        """Test retry logic on network errors."""
        # First call fails, second succeeds
        error_response = Mock()
        error_response.raise_for_status.side_effect = (
            requests.exceptions.RequestException("Network error")
        )

        success_response = Mock()
        success_response.json.return_value = {"sha": "abc123"}
        success_response.raise_for_status = Mock()

        # Need to mock both the repo and commit calls
        mock_get.side_effect = [
            Mock(
                json=lambda: {"default_branch": "main"}, raise_for_status=lambda: None
            ),
            error_response,
            success_response,
        ]

        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills@latest")

        with patch("time.sleep"):  # Mock sleep to speed up test
            sha, version = client.resolve_version(spec)

        assert sha == "abc123"

    def test_get_upstream_url_with_path(self):
        """Test constructing upstream URL with path."""
        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills/python")
        url = client.get_upstream_url(spec, "abc123")

        assert url == "https://github.com/anthropics/skills/tree/abc123/python"

    def test_get_upstream_url_without_path(self):
        """Test constructing upstream URL without path."""
        client = GitHubClient()
        spec = ArtifactSpec.parse("anthropics/skills")
        url = client.get_upstream_url(spec, "abc123")

        assert url == "https://github.com/anthropics/skills/tree/abc123"


class TestGitHubSource:
    """Test GitHubSource functionality."""

    @patch("skillmeat.sources.github.GitHubClient.resolve_version")
    @patch("skillmeat.sources.github.GitHubClient.clone_repo")
    @patch("skillmeat.sources.github.ArtifactValidator.validate")
    @patch("skillmeat.sources.github.extract_artifact_metadata")
    def test_fetch_skill(
        self, mock_extract, mock_validate, mock_clone, mock_resolve, tmp_path
    ):
        """Test fetching a skill from GitHub."""
        # Setup mocks
        mock_resolve.return_value = ("abc123", "v1.0.0")

        def clone_side_effect(spec, dest_dir, sha):
            # Create fake skill structure
            skill_dir = dest_dir / spec.artifact_path
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("# Test Skill")

        mock_clone.side_effect = clone_side_effect

        mock_validate.return_value = Mock(is_valid=True)
        mock_extract.return_value = ArtifactMetadata(title="Test Skill")

        # Test fetch
        source = GitHubSource()
        result = source.fetch("anthropics/skills/test", ArtifactType.SKILL)

        assert result.metadata.title == "Test Skill"
        assert result.resolved_sha == "abc123"
        assert result.resolved_version == "v1.0.0"
        assert result.upstream_url is not None
        assert "github.com" in result.upstream_url

    @patch("skillmeat.sources.github.GitHubClient.resolve_version")
    @patch("skillmeat.sources.github.GitHubClient.clone_repo")
    @patch("skillmeat.sources.github.ArtifactValidator.validate")
    def test_fetch_invalid_artifact(
        self, mock_validate, mock_clone, mock_resolve, tmp_path
    ):
        """Test fetching invalid artifact."""
        mock_resolve.return_value = ("abc123", None)

        def clone_side_effect(spec, dest_dir, sha):
            skill_dir = dest_dir / spec.artifact_path
            skill_dir.mkdir(parents=True)
            # Don't create SKILL.md - invalid

        mock_clone.side_effect = clone_side_effect
        mock_validate.return_value = Mock(
            is_valid=False, error_message="Missing SKILL.md"
        )

        source = GitHubSource()
        with pytest.raises(ValueError, match="Invalid artifact"):
            source.fetch("anthropics/skills/test", ArtifactType.SKILL)

    @patch("skillmeat.sources.github.GitHubClient.resolve_version")
    @patch("skillmeat.sources.github.GitHubClient.clone_repo")
    def test_fetch_artifact_not_found(self, mock_clone, mock_resolve, tmp_path):
        """Test fetching artifact with nonexistent path."""
        mock_resolve.return_value = ("abc123", None)

        def clone_side_effect(spec, dest_dir, sha):
            # Don't create the artifact path
            pass

        mock_clone.side_effect = clone_side_effect

        source = GitHubSource()
        with pytest.raises(ValueError, match="not found in repository"):
            source.fetch("anthropics/skills/nonexistent", ArtifactType.SKILL)

    def test_fetch_invalid_spec(self):
        """Test fetching with invalid spec."""
        source = GitHubSource()
        with pytest.raises(ValueError, match="Invalid GitHub spec"):
            source.fetch("invalid", ArtifactType.SKILL)

    @patch("skillmeat.sources.github.GitHubClient.resolve_version")
    def test_check_updates_available(self, mock_resolve):
        """Test checking for available updates."""
        mock_resolve.return_value = ("newsha123", "v2.0.0")

        artifact = Artifact(
            name="test",
            type=ArtifactType.SKILL,
            path="skills/test",
            origin="github",
            metadata=ArtifactMetadata(),
            added="2024-01-01T00:00:00",
            upstream="https://github.com/anthropics/skills/tree/abc123/test",
            version_spec="latest",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
        )

        source = GitHubSource()
        update_info = source.check_updates(artifact)

        assert update_info is not None
        assert update_info.has_update is True
        assert update_info.current_sha == "abc123"
        assert update_info.latest_sha == "newsha123"

    @patch("skillmeat.sources.github.GitHubClient.resolve_version")
    def test_check_updates_none_available(self, mock_resolve):
        """Test checking for updates when none available."""
        mock_resolve.return_value = ("abc123", "v1.0.0")

        artifact = Artifact(
            name="test",
            type=ArtifactType.SKILL,
            path="skills/test",
            origin="github",
            metadata=ArtifactMetadata(),
            added="2024-01-01T00:00:00",
            upstream="https://github.com/anthropics/skills/tree/abc123/test",
            version_spec="latest",
            resolved_sha="abc123",
            resolved_version="v1.0.0",
        )

        source = GitHubSource()
        update_info = source.check_updates(artifact)

        assert update_info is None

    def test_check_updates_no_upstream(self):
        """Test checking updates for artifact without upstream."""
        artifact = Artifact(
            name="test",
            type=ArtifactType.SKILL,
            path="skills/test",
            origin="local",
            metadata=ArtifactMetadata(),
            added="2024-01-01T00:00:00",
        )

        source = GitHubSource()
        update_info = source.check_updates(artifact)

        assert update_info is None

    @patch("skillmeat.sources.github.ArtifactValidator.validate")
    def test_validate(self, mock_validator, tmp_path):
        """Test validation."""
        mock_validator.return_value = Mock(is_valid=True)

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        source = GitHubSource()
        result = source.validate(skill_dir, ArtifactType.SKILL)

        assert result is True
        mock_validator.assert_called_once_with(skill_dir, ArtifactType.SKILL)
