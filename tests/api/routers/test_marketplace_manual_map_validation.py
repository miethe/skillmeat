"""Tests for manual_map directory path validation in marketplace sources.

Tests the validation logic added in Phase 3, P3.1b that ensures directory paths
in manual_map exist in the GitHub repository before allowing updates.
"""

import pytest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from skillmeat.api.routers.marketplace_sources import _validate_manual_map_paths


class TestManualMapValidation:
    """Test suite for manual_map directory path validation."""

    @pytest.fixture
    def mock_tree_valid_paths(self):
        """Mock GitHub tree with valid directory paths."""
        return [
            {"path": "skills", "type": "tree"},
            {"path": "skills/python", "type": "tree"},
            {"path": "skills/typescript", "type": "tree"},
            {"path": "commands", "type": "tree"},
            {"path": "commands/dev", "type": "tree"},
            {"path": "agents", "type": "tree"},
            {"path": "skills/python/skill.md", "type": "blob"},
            {"path": "commands/dev/run.sh", "type": "blob"},
        ]

    @pytest.mark.asyncio
    async def test_valid_paths_pass_validation(self, mock_tree_valid_paths):
        """Test that valid directory paths pass validation."""
        manual_map = {
            "skills/python": "skill",
            "commands/dev": "command",
        }

        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
            mock_scanner_class.return_value = mock_scanner

            # Should not raise exception
            await _validate_manual_map_paths(
                manual_map=manual_map,
                owner="test-owner",
                repo="test-repo",
                ref="main",
            )

            # Verify tree was fetched
            mock_scanner._fetch_tree.assert_called_once_with(
                "test-owner", "test-repo", "main"
            )

    @pytest.mark.asyncio
    async def test_invalid_paths_raise_422(self, mock_tree_valid_paths):
        """Test that invalid directory paths raise 422 error."""
        manual_map = {
            "skills/python": "skill",
            "nonexistent/path": "command",  # Invalid path
            "another/invalid": "agent",  # Another invalid path
        }

        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
            mock_scanner_class.return_value = mock_scanner

            with pytest.raises(HTTPException) as exc_info:
                await _validate_manual_map_paths(
                    manual_map=manual_map,
                    owner="test-owner",
                    repo="test-repo",
                    ref="main",
                )

            # Verify error details
            assert exc_info.value.status_code == 422
            assert "Invalid directory path(s) not found in repository" in exc_info.value.detail
            assert "'another/invalid'" in exc_info.value.detail
            assert "'nonexistent/path'" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_empty_manual_map_passes(self):
        """Test that empty manual_map passes without API calls."""
        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner_class.return_value = mock_scanner

            # Should return early without calling API
            await _validate_manual_map_paths(
                manual_map={},
                owner="test-owner",
                repo="test-repo",
                ref="main",
            )

            # Verify no API call was made
            mock_scanner._fetch_tree.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_manual_map_passes(self):
        """Test that None manual_map passes without API calls."""
        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner_class.return_value = mock_scanner

            # Should return early without calling API
            await _validate_manual_map_paths(
                manual_map=None,
                owner="test-owner",
                repo="test-repo",
                ref="main",
            )

            # Verify no API call was made
            mock_scanner._fetch_tree.assert_not_called()

    @pytest.mark.asyncio
    async def test_github_api_error_raises_500(self):
        """Test that GitHub API errors raise 500."""
        manual_map = {"skills/python": "skill"}

        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner._fetch_tree.side_effect = Exception("GitHub API error")
            mock_scanner_class.return_value = mock_scanner

            with pytest.raises(HTTPException) as exc_info:
                await _validate_manual_map_paths(
                    manual_map=manual_map,
                    owner="test-owner",
                    repo="test-repo",
                    ref="main",
                )

            # Verify error details
            assert exc_info.value.status_code == 500
            assert "Failed to validate directory paths" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_all_paths_valid(self, mock_tree_valid_paths):
        """Test that all paths must be valid."""
        manual_map = {
            "skills": "skill",
            "commands": "command",
            "agents": "agent",
        }

        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
            mock_scanner_class.return_value = mock_scanner

            # Should not raise exception
            await _validate_manual_map_paths(
                manual_map=manual_map,
                owner="test-owner",
                repo="test-repo",
                ref="main",
            )

    @pytest.mark.asyncio
    async def test_nested_paths_validated(self, mock_tree_valid_paths):
        """Test that nested directory paths are validated correctly."""
        manual_map = {
            "skills/python": "skill",
            "skills/typescript": "skill",
            "commands/dev": "command",
        }

        with patch("skillmeat.api.routers.marketplace_sources.GitHubScanner") as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
            mock_scanner_class.return_value = mock_scanner

            # Should not raise exception
            await _validate_manual_map_paths(
                manual_map=manual_map,
                owner="test-owner",
                repo="test-repo",
                ref="main",
            )
