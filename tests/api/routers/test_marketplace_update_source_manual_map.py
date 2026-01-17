"""Integration tests for update_source with manual_map validation.

Tests the complete flow of updating a marketplace source with manual_map
validation, ensuring directory paths are validated against the GitHub repository.
"""

import pytest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from skillmeat.api.routers.marketplace_sources import update_source
from skillmeat.api.schemas.marketplace import UpdateSourceRequest
from skillmeat.cache.models import MarketplaceSource


class TestUpdateSourceManualMapValidation:
    """Test suite for update_source endpoint with manual_map validation."""

    @pytest.fixture
    def mock_source(self):
        """Mock marketplace source."""
        from datetime import datetime
        import json

        source = Mock(spec=MarketplaceSource)
        source.id = "test-source-123"
        source.owner = "test-owner"
        source.repo_name = "test-repo"
        source.repo_url = "https://github.com/test-owner/test-repo"
        source.ref = "main"
        source.root_hint = None
        source.trust_level = "basic"
        source.description = "Test repository"
        source.notes = None
        source.enable_frontmatter_detection = False
        source.manual_map = None
        source.visibility = "public"
        source.scan_status = "success"
        source.artifact_count = 0
        source.last_sync_at = datetime(2025, 1, 6, 12, 0, 0)
        source.last_error = None
        source.created_at = datetime(2025, 1, 6, 12, 0, 0)
        source.updated_at = datetime(2025, 1, 6, 12, 0, 0)

        # Add set_manual_map_dict and get_manual_map_dict methods to mock
        def set_manual_map_dict(manual_map_dict):
            source.manual_map = json.dumps(manual_map_dict)

        def get_manual_map_dict():
            if not source.manual_map:
                return None
            try:
                return json.loads(source.manual_map)
            except json.JSONDecodeError:
                return None

        source.set_manual_map_dict = set_manual_map_dict
        source.get_manual_map_dict = get_manual_map_dict
        return source

    @pytest.fixture
    def mock_tree_with_paths(self):
        """Mock GitHub tree with directory paths."""
        return [
            {"path": "skills", "type": "tree"},
            {"path": "skills/python", "type": "tree"},
            {"path": "skills/typescript", "type": "tree"},
            {"path": "commands", "type": "tree"},
            {"path": "commands/dev", "type": "tree"},
            {"path": "skills/python/skill.md", "type": "blob"},
        ]

    @pytest.mark.asyncio
    async def test_update_source_with_valid_manual_map(
        self, mock_source, mock_tree_with_paths
    ):
        """Test updating source with valid manual_map paths."""
        request = UpdateSourceRequest(
            manual_map={
                "skills/python": "skill",
                "commands/dev": "command",
            }
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner"
        ) as mock_scanner_class:
            # Setup repository mock
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo.update.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            # Setup scanner mock
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = (mock_tree_with_paths, "main")
            mock_scanner_class.return_value = mock_scanner

            # Execute update
            result = await update_source(
                source_id="test-source-123",
                request=request,
            )

            # Verify validation was called
            mock_scanner._fetch_tree.assert_called_once_with(
                "test-owner", "test-repo", "main"
            )

            # Verify manual_map was stored
            assert mock_source.manual_map is not None

    @pytest.mark.asyncio
    async def test_update_source_with_invalid_manual_map(
        self, mock_source, mock_tree_with_paths
    ):
        """Test updating source with invalid manual_map paths raises 422."""
        request = UpdateSourceRequest(
            manual_map={
                "skills/python": "skill",
                "nonexistent/path": "command",  # Invalid path
            }
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner"
        ) as mock_scanner_class:
            # Setup repository mock
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            # Setup scanner mock
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = (mock_tree_with_paths, "main")
            mock_scanner_class.return_value = mock_scanner

            # Execute update - should raise 422
            with pytest.raises(HTTPException) as exc_info:
                await update_source(
                    source_id="test-source-123",
                    request=request,
                )

            # Verify error
            assert exc_info.value.status_code == 422
            assert "Invalid directory path(s) not found in repository" in exc_info.value.detail
            assert "'nonexistent/path'" in exc_info.value.detail

            # Verify update was not called
            mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_source_with_new_ref_uses_new_ref(
        self, mock_source, mock_tree_with_paths
    ):
        """Test that validation uses the new ref when both ref and manual_map are updated."""
        request = UpdateSourceRequest(
            ref="develop",  # Changing ref
            manual_map={
                "skills/python": "skill",
            }
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner"
        ) as mock_scanner_class:
            # Setup repository mock
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo.update.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            # Setup scanner mock
            mock_scanner = Mock()
            mock_scanner._fetch_tree.return_value = (mock_tree_with_paths, "main")
            mock_scanner_class.return_value = mock_scanner

            # Execute update
            await update_source(
                source_id="test-source-123",
                request=request,
            )

            # Verify validation used new ref "develop", not old "main"
            mock_scanner._fetch_tree.assert_called_once_with(
                "test-owner", "test-repo", "develop"
            )

    @pytest.mark.asyncio
    async def test_update_source_without_manual_map_skips_validation(
        self, mock_source
    ):
        """Test that updating without manual_map skips path validation."""
        request = UpdateSourceRequest(
            description="Updated description",
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class, patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner"
        ) as mock_scanner_class:
            # Setup repository mock
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo.update.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            # Setup scanner mock
            mock_scanner = Mock()
            mock_scanner_class.return_value = mock_scanner

            # Execute update
            await update_source(
                source_id="test-source-123",
                request=request,
            )

            # Verify validation was NOT called
            mock_scanner._fetch_tree.assert_not_called()

            # Verify description was updated
            assert mock_source.description == "Updated description"
