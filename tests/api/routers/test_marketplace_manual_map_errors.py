"""Comprehensive error handling tests for manual_map in PATCH /marketplace/sources/{id}.

Tests all validation failure scenarios for the manual_map field including:
- Invalid directory paths (422)
- Invalid artifact types (422)
- Malformed manual_map structure (422 - handled by Pydantic)
- Multiple validation errors
- Edge cases (empty strings, None values, etc.)

Phase: 3, Task: P3.4a
"""

import pytest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from skillmeat.api.server import app
from skillmeat.cache.models import MarketplaceSource


@pytest.fixture
def client():
    """Test client for API endpoints."""
    return TestClient(app)


@pytest.fixture
def mock_source():
    """Mock MarketplaceSource for testing."""
    from datetime import datetime, timezone

    return MarketplaceSource(
        id="test-source-123",
        repo_url="https://github.com/test-org/test-repo",
        owner="test-org",
        repo_name="test-repo",
        ref="main",
        root_hint=None,
        trust_level="basic",
        visibility="public",
        scan_status="success",
        artifact_count=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        enable_frontmatter_detection=False,
    )


@pytest.fixture
def mock_tree_valid_paths():
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


class TestManualMapErrorResponses:
    """Test comprehensive error handling for manual_map validation."""

    def test_patch_invalid_directory_path_single(
        self, client, mock_source, mock_tree_valid_paths
    ):
        """PATCH with single invalid directory path should return 422 with clear message.

        Scenario: User provides a directory path that doesn't exist in the repository.
        Expected: 422 error with message listing the invalid path.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            with patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner"
            ) as mock_scanner_class:
                mock_scanner = Mock()
                mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
                mock_scanner_class.return_value = mock_scanner

                response = client.patch(
                    "/api/v1/marketplace/sources/test-source-123",
                    json={"manual_map": {"nonexistent/path": "skill"}},
                )

                assert response.status_code == 422
                error_detail = response.json()["detail"]
                assert "Invalid directory path(s) not found in repository" in error_detail
                assert "'nonexistent/path'" in error_detail

    def test_patch_invalid_directory_path_multiple(
        self, client, mock_source, mock_tree_valid_paths
    ):
        """PATCH with multiple invalid directory paths should return 422 listing all invalid paths.

        Scenario: User provides multiple paths that don't exist.
        Expected: 422 error with message listing ALL invalid paths (sorted).
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            with patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner"
            ) as mock_scanner_class:
                mock_scanner = Mock()
                mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
                mock_scanner_class.return_value = mock_scanner

                response = client.patch(
                    "/api/v1/marketplace/sources/test-source-123",
                    json={
                        "manual_map": {
                            "nonexistent/path": "skill",
                            "another/invalid": "command",
                            "third/missing": "agent",
                        }
                    },
                )

                assert response.status_code == 422
                error_detail = response.json()["detail"]
                assert "Invalid directory path(s) not found in repository" in error_detail
                # All three invalid paths should be mentioned (alphabetically sorted)
                assert "'another/invalid'" in error_detail
                assert "'nonexistent/path'" in error_detail
                assert "'third/missing'" in error_detail

    def test_patch_invalid_artifact_type_single(self, client, mock_source):
        """PATCH with invalid artifact type should return 422 with clear message.

        Scenario: User provides an artifact type that isn't in the allowed set.
        Expected: 422 error with message listing the invalid type and allowed types.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={"manual_map": {"skills/python": "invalid_type"}},
            )

            assert response.status_code == 422
            error_detail = response.json()["detail"]
            # Check that error mentions the invalid type and allowed types
            # Pydantic validation message format
            assert "manual_map" in str(error_detail).lower()
            assert (
                "invalid_type" in str(error_detail).lower()
                or "Invalid artifact type" in str(error_detail)
            )

    def test_patch_invalid_artifact_type_multiple(self, client, mock_source):
        """PATCH with multiple invalid artifact types should return 422.

        Scenario: User provides multiple invalid artifact types.
        Expected: 422 error mentioning validation failure.
        Note: Pydantic validates in order, so may report first error.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={
                    "manual_map": {
                        "skills/python": "bad_type",
                        "commands/dev": "another_bad_type",
                    }
                },
            )

            assert response.status_code == 422
            error_detail = response.json()["detail"]
            # At least one invalid type should be mentioned
            assert "manual_map" in str(error_detail).lower() or "artifact type" in str(
                error_detail
            ).lower()

    def test_patch_malformed_manual_map_not_dict(self, client, mock_source):
        """PATCH with manual_map as non-dict should return 422.

        Scenario: User sends manual_map as string instead of dict.
        Expected: 422 error from Pydantic type validation.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={"manual_map": "not-a-dict"},
            )

            assert response.status_code == 422
            error_detail = response.json()["detail"]
            # Pydantic should report type validation error
            assert "manual_map" in str(error_detail).lower()

    def test_patch_malformed_manual_map_list(self, client, mock_source):
        """PATCH with manual_map as list should return 422.

        Scenario: User sends manual_map as array instead of object.
        Expected: 422 error from Pydantic type validation.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={"manual_map": ["skills/python", "command"]},
            )

            assert response.status_code == 422
            error_detail = response.json()["detail"]
            assert "manual_map" in str(error_detail).lower()

    def test_patch_mixed_errors_invalid_path_and_type(
        self, client, mock_source, mock_tree_valid_paths
    ):
        """PATCH with both invalid path AND invalid type should return 422.

        Scenario: User provides a path that doesn't exist AND an invalid artifact type.
        Expected: 422 error - may report first encountered error (type validation happens first).
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            # Type validation happens in schema BEFORE path validation in endpoint
            # So we expect type validation to fail first
            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={"manual_map": {"nonexistent/path": "invalid_type"}},
            )

            assert response.status_code == 422
            error_detail = response.json()["detail"]
            # Should report the first error encountered (artifact type validation)
            assert "manual_map" in str(error_detail).lower() or "artifact type" in str(
                error_detail
            ).lower()

    def test_patch_valid_path_valid_type_succeeds(
        self, client, mock_source, mock_tree_valid_paths
    ):
        """PATCH with valid path and valid type should succeed.

        Scenario: User provides a path that exists and a valid artifact type.
        Expected: 200 OK with updated source.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo.update.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            with patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner"
            ) as mock_scanner_class:
                mock_scanner = Mock()
                mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
                mock_scanner_class.return_value = mock_scanner

                response = client.patch(
                    "/api/v1/marketplace/sources/test-source-123",
                    json={"manual_map": {"skills/python": "skill"}},
                )

                assert response.status_code == 200
                # Verify manual_map was set
                assert response.json()["manual_map"] == {"skills/python": "skill"}

    def test_patch_empty_manual_map_clears_mapping(self, client, mock_source):
        """PATCH with empty manual_map should clear existing mappings.

        Scenario: User sends empty dict to remove manual mappings.
        Expected: 200 OK with manual_map set to None.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo.update.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={"manual_map": {}},
            )

            assert response.status_code == 200
            # Empty manual_map should result in None
            assert response.json()["manual_map"] is None

    def test_patch_allowed_artifact_types_comprehensive(
        self, client, mock_source, mock_tree_valid_paths
    ):
        """Verify all allowed artifact types are accepted.

        Scenario: User provides each allowed artifact type.
        Expected: All allowed types should pass validation.
        """
        allowed_types = ["skill", "command", "agent", "mcp_server", "hook"]

        for artifact_type in allowed_types:
            with patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
            ) as mock_repo_class:
                mock_repo = Mock()
                mock_repo.get_by_id.return_value = mock_source
                mock_repo.update.return_value = mock_source
                mock_repo_class.return_value = mock_repo

                with patch(
                    "skillmeat.api.routers.marketplace_sources.GitHubScanner"
                ) as mock_scanner_class:
                    mock_scanner = Mock()
                    mock_scanner._fetch_tree.return_value = mock_tree_valid_paths
                    mock_scanner_class.return_value = mock_scanner

                    response = client.patch(
                        "/api/v1/marketplace/sources/test-source-123",
                        json={"manual_map": {"skills/python": artifact_type}},
                    )

                    assert (
                        response.status_code == 200
                    ), f"Expected 200 for {artifact_type}, got {response.status_code}: {response.json()}"

    def test_patch_source_not_found_returns_404(self, client):
        """PATCH with non-existent source ID should return 404.

        Scenario: User tries to update a source that doesn't exist.
        Expected: 404 error before any validation occurs.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = None  # Source not found
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/nonexistent-id",
                json={"manual_map": {"skills/python": "skill"}},
            )

            assert response.status_code == 404
            error_detail = response.json()["detail"]
            assert "not found" in error_detail.lower()

    def test_patch_github_api_failure_returns_500(
        self, client, mock_source, mock_tree_valid_paths
    ):
        """PATCH when GitHub API fails should return 500.

        Scenario: GitHub API call fails when validating directory paths.
        Expected: 500 error with appropriate message.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            with patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner"
            ) as mock_scanner_class:
                mock_scanner = Mock()
                mock_scanner._fetch_tree.side_effect = Exception("GitHub API error")
                mock_scanner_class.return_value = mock_scanner

                response = client.patch(
                    "/api/v1/marketplace/sources/test-source-123",
                    json={"manual_map": {"skills/python": "skill"}},
                )

                assert response.status_code == 500
                error_detail = response.json()["detail"]
                assert "Failed to validate directory paths" in error_detail

    def test_patch_no_params_returns_400(self, client, mock_source):
        """PATCH with no update parameters should return 400.

        Scenario: User sends PATCH with empty body.
        Expected: 400 error requiring at least one parameter.
        """
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_repo.get_by_id.return_value = mock_source
            mock_repo_class.return_value = mock_repo

            response = client.patch(
                "/api/v1/marketplace/sources/test-source-123",
                json={},
            )

            assert response.status_code == 400
            error_detail = response.json()["detail"]
            assert "at least one update parameter" in error_detail.lower()
