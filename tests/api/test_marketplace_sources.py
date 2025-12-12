"""Integration tests for Marketplace Sources API endpoints.

This module tests the /api/v1/marketplace/sources endpoints:
- POST /marketplace/sources - Create new GitHub source
- GET /marketplace/sources - List sources with pagination
- GET /marketplace/sources/{id} - Get specific source
- PATCH /marketplace/sources/{id} - Update source configuration
- POST /marketplace/sources/{id}/rescan - Trigger repository rescan
- GET /marketplace/sources/{id}/artifacts - List artifacts with filters
- POST /marketplace/sources/{id}/import - Import artifacts to collection
"""

import uuid
from datetime import datetime
from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource
from skillmeat.core.marketplace.github_scanner import ScanResult


@pytest.fixture
def test_settings():
    """Create test settings with API key disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app):
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_source():
    """Create a mock MarketplaceSource."""
    return MarketplaceSource(
        id="src_test_123",
        repo_url="https://github.com/anthropics/anthropic-quickstarts",
        owner="anthropics",
        repo_name="anthropic-quickstarts",
        ref="main",
        root_hint="skills",
        trust_level="verified",
        visibility="public",
        scan_status="success",
        artifact_count=5,
        last_sync_at=datetime(2025, 12, 6, 10, 30, 0),
        created_at=datetime(2025, 12, 5, 9, 0, 0),
        updated_at=datetime(2025, 12, 6, 10, 30, 0),
    )


@pytest.fixture
def mock_catalog_entry():
    """Create a mock MarketplaceCatalogEntry."""
    return MarketplaceCatalogEntry(
        id="cat_test_456",
        source_id="src_test_123",
        artifact_type="skill",
        name="canvas-design",
        path="skills/canvas-design",
        upstream_url="https://github.com/anthropics/anthropic-quickstarts/tree/main/skills/canvas-design",
        detected_version="1.2.0",
        detected_sha="abc123def456",
        detected_at=datetime(2025, 12, 6, 10, 30, 0),
        confidence_score=95,
        status="new",
    )


@pytest.fixture
def mock_source_repo(mock_source):
    """Create mock MarketplaceSourceRepository."""
    mock = MagicMock()
    mock.get_by_id.return_value = mock_source
    mock.get_by_repo_url.return_value = None  # No existing source by default
    mock.create.return_value = mock_source
    mock.update.return_value = mock_source
    mock.delete.return_value = True
    mock.list_paginated.return_value = MagicMock(
        items=[mock_source], has_more=False
    )
    return mock


@pytest.fixture
def mock_catalog_repo(mock_catalog_entry):
    """Create mock MarketplaceCatalogRepository."""
    mock = MagicMock()
    mock.get_by_id.return_value = mock_catalog_entry
    mock.get_source_catalog.return_value = [mock_catalog_entry]
    mock.list_paginated.return_value = MagicMock(
        items=[mock_catalog_entry], has_more=False
    )
    mock.count_by_status.return_value = {"new": 5, "imported": 0}
    mock.count_by_type.return_value = {"skill": 4, "command": 1}
    return mock


@pytest.fixture
def mock_transaction_handler():
    """Create mock MarketplaceTransactionHandler."""
    mock = MagicMock()
    mock_ctx = MagicMock()
    mock.scan_update_transaction.return_value.__enter__.return_value = mock_ctx
    mock.import_transaction.return_value.__enter__.return_value = mock_ctx
    return mock


@pytest.fixture
def mock_scanner():
    """Create mock GitHubScanner."""
    mock = MagicMock()
    scan_result = ScanResult(
        status="success",
        artifacts_found=5,
        new_count=3,
        updated_count=1,
        removed_count=1,
        unchanged_count=0,
        scan_duration_ms=1234.56,
        errors=[],
        scanned_at=datetime(2025, 12, 6, 10, 35, 0),
    )
    mock.scan_repository.return_value = scan_result
    return mock


@pytest.fixture
def mock_import_coordinator():
    """Create mock ImportCoordinator."""
    from skillmeat.core.marketplace.import_coordinator import (
        ImportResult,
        ImportedEntry,
        ImportStatus,
    )

    mock = MagicMock()
    import_result = ImportResult(
        import_id="imp_test_789",
        success_count=2,
        skipped_count=1,
        error_count=0,
        entries=[
            ImportedEntry(
                catalog_entry_id="cat_test_456",
                artifact_name="canvas-design",
                artifact_type="skill",
                status=ImportStatus.SUCCESS,
            ),
            ImportedEntry(
                catalog_entry_id="cat_test_457",
                artifact_name="another-skill",
                artifact_type="skill",
                status=ImportStatus.SUCCESS,
            ),
            ImportedEntry(
                catalog_entry_id="cat_test_458",
                artifact_name="existing-skill",
                artifact_type="skill",
                status=ImportStatus.SKIPPED,
                error_message="Already exists in collection",
            ),
        ],
    )
    mock.import_entries.return_value = import_result
    return mock


# =============================================================================
# Test Create Source (POST /marketplace/sources)
# =============================================================================


class TestCreateSource:
    """Test POST /marketplace/sources endpoint."""

    def test_create_source_success(self, client, mock_source_repo):
        """Test creating a new GitHub source with valid URL."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
                    "ref": "main",
                    "root_hint": "skills",
                    "trust_level": "verified",
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify response structure
        assert data["id"] == "src_test_123"
        assert data["repo_url"] == "https://github.com/anthropics/anthropic-quickstarts"
        assert data["owner"] == "anthropics"
        assert data["repo_name"] == "anthropic-quickstarts"
        assert data["ref"] == "main"
        assert data["root_hint"] == "skills"
        assert data["trust_level"] == "verified"
        assert data["scan_status"] == "success"

    def test_create_source_with_manual_map(self, client, mock_source_repo):
        """Test creating source with manual artifact mapping."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/user/repo",
                    "ref": "main",
                    "manual_map": {
                        "skill": ["skills/my-skill", "custom/another-skill"],
                        "command": ["commands/my-command"],
                    },
                },
            )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_source_invalid_url_format(self, client, mock_source_repo):
        """Test creating source with invalid GitHub URL format."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "not-a-valid-url",
                    "ref": "main",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid GitHub repository URL format" in response.json()["detail"]

    def test_create_source_non_github_url(self, client, mock_source_repo):
        """Test creating source with non-GitHub URL."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://gitlab.com/user/repo",
                    "ref": "main",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_source_missing_required_fields(self, client):
        """Test creating source with missing required fields."""
        response = client.post(
            "/api/v1/marketplace/sources",
            json={
                "ref": "main",
                # Missing repo_url
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_source_duplicate_url(self, client, mock_source_repo, mock_source):
        """Test creating source with URL that already exists."""
        # Mock existing source
        mock_source_repo.get_by_repo_url.return_value = mock_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/anthropics/anthropic-quickstarts",
                    "ref": "main",
                },
            )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]

    def test_create_source_default_values(self, client, mock_source_repo):
        """Test creating source uses default values for optional fields."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/user/repo",
                    # ref defaults to "main"
                    # trust_level defaults to "basic"
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["ref"] == "main"  # Default value


# =============================================================================
# Test List Sources (GET /marketplace/sources)
# =============================================================================


class TestListSources:
    """Test GET /marketplace/sources endpoint."""

    def test_list_sources_success(self, client, mock_source_repo):
        """Test listing sources returns paginated results."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get("/api/v1/marketplace/sources")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "page_info" in data
        assert len(data["items"]) == 1

        # Verify source structure
        source = data["items"][0]
        assert source["id"] == "src_test_123"
        assert source["owner"] == "anthropics"
        assert source["repo_name"] == "anthropic-quickstarts"

    def test_list_sources_pagination(self, client, mock_source_repo):
        """Test listing sources with pagination parameters."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources?limit=10&cursor=src_test_123"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify page info
        assert data["page_info"]["has_previous_page"] is True

    def test_list_sources_empty(self, client, mock_source_repo):
        """Test listing sources when no sources exist."""
        mock_source_repo.list_paginated.return_value = MagicMock(
            items=[], has_more=False
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get("/api/v1/marketplace/sources")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 0
        assert data["page_info"]["has_next_page"] is False

    def test_list_sources_limit_validation(self, client, mock_source_repo):
        """Test limit parameter validation (1-100)."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            # Test valid limit
            response = client.get("/api/v1/marketplace/sources?limit=50")
            assert response.status_code == status.HTTP_200_OK

            # Test limit too high (>100)
            response = client.get("/api/v1/marketplace/sources?limit=150")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test limit too low (<1)
            response = client.get("/api/v1/marketplace/sources?limit=0")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Test Get Source (GET /marketplace/sources/{source_id})
# =============================================================================


class TestGetSource:
    """Test GET /marketplace/sources/{source_id} endpoint."""

    def test_get_source_success(self, client, mock_source_repo):
        """Test getting a specific source by ID."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/src_test_123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == "src_test_123"
        assert data["owner"] == "anthropics"
        assert data["repo_name"] == "anthropic-quickstarts"
        assert data["scan_status"] == "success"
        assert data["artifact_count"] == 5

    def test_get_source_not_found(self, client, mock_source_repo):
        """Test getting a non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get("/api/v1/marketplace/sources/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


# =============================================================================
# Test Update Source (PATCH /marketplace/sources/{source_id})
# =============================================================================


class TestUpdateSource:
    """Test PATCH /marketplace/sources/{source_id} endpoint."""

    def test_update_source_ref(self, client, mock_source_repo, mock_source):
        """Test updating source ref (branch/tag/SHA)."""
        updated_source = MarketplaceSource(**mock_source.__dict__)
        updated_source.ref = "v1.0.0"
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123?ref=v1.0.0"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ref"] == "v1.0.0"

    def test_update_source_root_hint(self, client, mock_source_repo, mock_source):
        """Test updating source root_hint."""
        updated_source = MarketplaceSource(**mock_source.__dict__)
        updated_source.root_hint = "artifacts"
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123?root_hint=artifacts"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["root_hint"] == "artifacts"

    def test_update_source_trust_level(self, client, mock_source_repo, mock_source):
        """Test updating source trust level."""
        updated_source = MarketplaceSource(**mock_source.__dict__)
        updated_source.trust_level = "official"
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123?trust_level=official"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["trust_level"] == "official"

    def test_update_source_multiple_fields(self, client, mock_source_repo, mock_source):
        """Test updating multiple source fields at once."""
        updated_source = MarketplaceSource(**mock_source.__dict__)
        updated_source.ref = "develop"
        updated_source.trust_level = "verified"
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123?ref=develop&trust_level=verified"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ref"] == "develop"
        assert data["trust_level"] == "verified"

    def test_update_source_no_params(self, client, mock_source_repo):
        """Test updating source with no parameters fails."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch("/api/v1/marketplace/sources/src_test_123")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "At least one update parameter" in response.json()["detail"]

    def test_update_source_not_found(self, client, mock_source_repo):
        """Test updating a non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/nonexistent?ref=main"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test Rescan Source (POST /marketplace/sources/{source_id}/rescan)
# =============================================================================


class TestRescanSource:
    """Test POST /marketplace/sources/{source_id}/rescan endpoint."""

    def test_rescan_source_success(
        self, client, mock_source_repo, mock_scanner, mock_transaction_handler
    ):
        """Test triggering a successful repository rescan."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ):
            response = client.post("/api/v1/marketplace/sources/src_test_123/rescan")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify scan result structure
        assert data["source_id"] == "src_test_123"
        assert data["status"] == "success"
        assert data["artifacts_found"] == 5
        assert data["new_count"] == 3
        assert data["updated_count"] == 1
        assert data["removed_count"] == 1
        assert data["scan_duration_ms"] == 1234.56
        assert data["errors"] == []

    def test_rescan_source_with_force(
        self, client, mock_source_repo, mock_scanner, mock_transaction_handler
    ):
        """Test forcing a rescan even if recently scanned."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/rescan",
                json={"force": True},
            )

        assert response.status_code == status.HTTP_200_OK

    def test_rescan_source_not_found(self, client, mock_source_repo):
        """Test rescanning a non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post("/api/v1/marketplace/sources/nonexistent/rescan")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rescan_source_scan_error(
        self, client, mock_source_repo, mock_scanner, mock_transaction_handler
    ):
        """Test rescan when scanner encounters an error."""
        # Mock scanner to raise exception
        mock_scanner.scan_repository.side_effect = Exception("GitHub API rate limit")

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ):
            response = client.post("/api/v1/marketplace/sources/src_test_123/rescan")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return error result
        assert data["status"] == "error"
        assert data["artifacts_found"] == 0
        assert len(data["errors"]) > 0


# =============================================================================
# Test List Artifacts (GET /marketplace/sources/{source_id}/artifacts)
# =============================================================================


class TestListArtifacts:
    """Test GET /marketplace/sources/{source_id}/artifacts endpoint."""

    def test_list_artifacts_success(self, client, mock_source_repo, mock_catalog_repo):
        """Test listing artifacts from a source."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "page_info" in data
        assert "counts_by_status" in data
        assert "counts_by_type" in data

        # Verify artifact entry
        assert len(data["items"]) == 1
        entry = data["items"][0]
        assert entry["id"] == "cat_test_456"
        assert entry["source_id"] == "src_test_123"
        assert entry["artifact_type"] == "skill"
        assert entry["name"] == "canvas-design"
        assert entry["confidence_score"] == 95
        assert entry["status"] == "new"

        # Verify counts
        assert data["counts_by_status"] == {"new": 5, "imported": 0}
        assert data["counts_by_type"] == {"skill": 4, "command": 1}

    def test_list_artifacts_filter_by_type(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test filtering artifacts by type."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?artifact_type=skill"
            )

        assert response.status_code == status.HTTP_200_OK

    def test_list_artifacts_filter_by_status(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test filtering artifacts by status."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?status=new"
            )

        assert response.status_code == status.HTTP_200_OK

    def test_list_artifacts_filter_by_min_confidence(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test filtering artifacts by minimum confidence score."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=80"
            )

        assert response.status_code == status.HTTP_200_OK

    def test_list_artifacts_combined_filters(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test applying multiple filters together."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?artifact_type=skill&status=new&min_confidence=90"
            )

        assert response.status_code == status.HTTP_200_OK

    def test_list_artifacts_pagination(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test pagination with cursor."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?limit=10&cursor=cat_test_456"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page_info"]["has_previous_page"] is True

    def test_list_artifacts_min_confidence_validation(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test min_confidence parameter validation (0-100)."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            # Valid range
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=50"
            )
            assert response.status_code == status.HTTP_200_OK

            # Too low
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=-1"
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Too high
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=101"
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_artifacts_source_not_found(self, client, mock_source_repo):
        """Test listing artifacts for non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/nonexistent/artifacts"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test Import Artifacts (POST /marketplace/sources/{source_id}/import)
# =============================================================================


class TestImportArtifacts:
    """Test POST /marketplace/sources/{source_id}/import endpoint."""

    def test_import_single_artifact(
        self,
        client,
        mock_source_repo,
        mock_catalog_repo,
        mock_transaction_handler,
        mock_import_coordinator,
    ):
        """Test importing a single artifact."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.ImportCoordinator",
            return_value=mock_import_coordinator,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/import",
                json={
                    "entry_ids": ["cat_test_456"],
                    "conflict_strategy": "skip",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify import result
        assert data["imported_count"] == 2
        assert data["skipped_count"] == 1
        assert data["error_count"] == 0
        assert "cat_test_456" in data["imported_ids"]

    def test_import_bulk_artifacts(
        self,
        client,
        mock_source_repo,
        mock_catalog_repo,
        mock_transaction_handler,
        mock_import_coordinator,
        mock_catalog_entry,
    ):
        """Test importing multiple artifacts at once."""
        # Mock multiple catalog entries
        entry2 = MarketplaceCatalogEntry(**mock_catalog_entry.__dict__)
        entry2.id = "cat_test_457"
        entry2.name = "another-skill"

        mock_catalog_repo.get_by_id.side_effect = lambda id: {
            "cat_test_456": mock_catalog_entry,
            "cat_test_457": entry2,
        }.get(id)

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.ImportCoordinator",
            return_value=mock_import_coordinator,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/import",
                json={
                    "entry_ids": ["cat_test_456", "cat_test_457"],
                    "conflict_strategy": "overwrite",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["imported_count"] == 2

    def test_import_empty_entry_ids(self, client, mock_source_repo):
        """Test importing with empty entry_ids list fails."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/import",
                json={
                    "entry_ids": [],
                    "conflict_strategy": "skip",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "entry_ids cannot be empty" in response.json()["detail"]

    def test_import_entry_not_found(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test importing with non-existent entry ID."""
        mock_catalog_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/import",
                json={
                    "entry_ids": ["nonexistent"],
                    "conflict_strategy": "skip",
                },
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_import_entry_wrong_source(
        self, client, mock_source_repo, mock_catalog_repo, mock_catalog_entry
    ):
        """Test importing entry that belongs to different source."""
        # Entry belongs to different source
        wrong_entry = MarketplaceCatalogEntry(**mock_catalog_entry.__dict__)
        wrong_entry.source_id = "different_source"
        mock_catalog_repo.get_by_id.return_value = wrong_entry

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/import",
                json={
                    "entry_ids": ["cat_test_456"],
                    "conflict_strategy": "skip",
                },
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not belong to source" in response.json()["detail"]

    def test_import_conflict_strategies(
        self,
        client,
        mock_source_repo,
        mock_catalog_repo,
        mock_transaction_handler,
        mock_import_coordinator,
    ):
        """Test different conflict resolution strategies."""
        strategies = ["skip", "overwrite", "rename"]

        for strategy in strategies:
            with patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
                return_value=mock_catalog_repo,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
                return_value=mock_transaction_handler,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.ImportCoordinator",
                return_value=mock_import_coordinator,
            ):
                response = client.post(
                    "/api/v1/marketplace/sources/src_test_123/import",
                    json={
                        "entry_ids": ["cat_test_456"],
                        "conflict_strategy": strategy,
                    },
                )

            assert response.status_code == status.HTTP_200_OK

    def test_import_source_not_found(self, client, mock_source_repo):
        """Test importing from non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/nonexistent/import",
                json={
                    "entry_ids": ["cat_test_456"],
                    "conflict_strategy": "skip",
                },
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_import_default_conflict_strategy(
        self,
        client,
        mock_source_repo,
        mock_catalog_repo,
        mock_transaction_handler,
        mock_import_coordinator,
    ):
        """Test import uses default conflict strategy if not specified."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.ImportCoordinator",
            return_value=mock_import_coordinator,
        ):
            response = client.post(
                "/api/v1/marketplace/sources/src_test_123/import",
                json={
                    "entry_ids": ["cat_test_456"],
                    # conflict_strategy defaults to "skip"
                },
            )

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# Test Error Scenarios
# =============================================================================


class TestErrorHandling:
    """Test error handling across all endpoints."""

    def test_database_connection_error(self, client):
        """Test handling of database connection errors."""
        mock_repo = MagicMock()
        mock_repo.list_paginated.side_effect = Exception("Database connection failed")

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_repo,
        ):
            response = client.get("/api/v1/marketplace/sources")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_github_api_rate_limit(
        self, client, mock_source_repo, mock_transaction_handler
    ):
        """Test handling of GitHub API rate limit during rescan."""
        mock_scanner = MagicMock()
        mock_scanner.scan_repository.side_effect = Exception("API rate limit exceeded")

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceTransactionHandler",
            return_value=mock_transaction_handler,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ):
            response = client.post("/api/v1/marketplace/sources/src_test_123/rescan")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert len(data["errors"]) > 0
