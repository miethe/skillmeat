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
from skillmeat.api.schemas.marketplace import ScanResultDTO
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceCatalogEntry, MarketplaceSource


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
        enable_frontmatter_detection=False,
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
    scan_result = ScanResultDTO(
        source_id="src_test_123",
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

    def test_create_source_success(self, client, mock_source_repo, mock_source):
        """Test creating a new GitHub source with valid URL and auto-scan."""
        # Mock the scan function to avoid complex dependencies
        async def mock_perform_scan(*args, **kwargs):
            # Update mock source to success status
            mock_source.scan_status = "success"
            mock_source.artifact_count = 5
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=5,
                new_count=5,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=1234.56,
                errors=[],
                scanned_at=datetime(2025, 12, 6, 10, 35, 0),
            )

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
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
        assert data["artifact_count"] == 5

    def test_create_source_with_manual_map(self, client, mock_source_repo, mock_source):
        """Test creating source with manual artifact mapping."""
        # Mock the scan function
        async def mock_perform_scan(*args, **kwargs):
            mock_source.scan_status = "success"
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=2,
                new_count=2,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=1000.0,
                errors=[],
                scanned_at=datetime(2025, 12, 6, 10, 35, 0),
            )

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
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

    def test_create_source_default_values(self, client, mock_source_repo, mock_source):
        """Test creating source uses default values for optional fields."""
        # Mock the scan function to avoid complex dependencies
        async def mock_perform_scan(*args, **kwargs):
            # Update mock source to success status
            mock_source.scan_status = "success"
            mock_source.artifact_count = 0
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=0,
                new_count=0,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=100.0,
                errors=[],
                scanned_at=datetime(2025, 12, 6, 10, 35, 0),
            )

        with (
            patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ),
            patch(
                "skillmeat.api.routers.marketplace_sources._perform_scan",
                side_effect=mock_perform_scan,
            ),
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
        # Create a copy by extracting only the data attributes (not SQLAlchemy state)
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref="v1.0.0",  # Updated value
            root_hint=mock_source.root_hint,
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=mock_source.updated_at,
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"ref": "v1.0.0"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ref"] == "v1.0.0"

    def test_update_source_root_hint(self, client, mock_source_repo, mock_source):
        """Test updating source root_hint."""
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref=mock_source.ref,
            root_hint="artifacts",  # Updated value
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=mock_source.updated_at,
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"root_hint": "artifacts"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["root_hint"] == "artifacts"

    def test_update_source_trust_level(self, client, mock_source_repo, mock_source):
        """Test updating source trust level."""
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref=mock_source.ref,
            root_hint=mock_source.root_hint,
            trust_level="official",  # Updated value
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=mock_source.updated_at,
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"trust_level": "official"}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["trust_level"] == "official"

    def test_update_source_multiple_fields(self, client, mock_source_repo, mock_source):
        """Test updating multiple source fields at once."""
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref="develop",  # Updated value
            root_hint=mock_source.root_hint,
            trust_level="verified",  # Updated value
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=mock_source.updated_at,
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"ref": "develop", "trust_level": "verified"}
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
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={}  # Empty body - no update parameters
            )

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
                "/api/v1/marketplace/sources/nonexistent",
                json={"ref": "main"}
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
# Test Confidence Filtering (GET /marketplace/sources/{source_id}/artifacts)
# =============================================================================


class TestConfidenceFiltering:
    """Test confidence score filtering functionality."""

    @pytest.fixture
    def mock_catalog_entries_with_scores(self, mock_source):
        """Create mock catalog entries with various confidence scores."""
        entries = []
        scores = [
            (95, 62, "high-confidence-skill"),
            (75, 50, "medium-high-skill"),
            (50, 35, "medium-skill"),
            (40, 28, "low-medium-skill"),
            (25, 18, "low-confidence-skill"),
            (15, 10, "very-low-skill"),
        ]

        for idx, (confidence, raw_score, name) in enumerate(scores):
            entry = MarketplaceCatalogEntry(
                id=f"cat_test_{idx}",
                source_id=mock_source.id,
                artifact_type="skill",
                name=name,
                path=f"skills/{name}",
                upstream_url=f"https://github.com/test/repo/tree/main/skills/{name}",
                detected_version="1.0.0",
                detected_sha=f"sha{idx}",
                detected_at=datetime(2025, 12, 6, 10, 30, 0),
                confidence_score=confidence,
                raw_score=raw_score,
                score_breakdown={
                    "dir_name_score": 10,
                    "manifest_score": 20 if confidence > 50 else 10,
                    "extensions_score": 5,
                    "parent_hint_score": 15 if confidence > 40 else 5,
                    "frontmatter_score": 15 if confidence > 60 else 0,
                    "depth_penalty": -5,
                    "raw_total": raw_score,
                    "normalized_score": confidence,
                },
                status="new",
            )
            entries.append(entry)

        return entries

    def test_filter_by_min_confidence(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test min_confidence parameter filters correctly."""
        mock_catalog_repo = MagicMock()

        # Filter entries >= 50
        filtered_entries = [e for e in mock_catalog_entries_with_scores if e.confidence_score >= 50]
        mock_catalog_repo.get_source_catalog.return_value = filtered_entries
        mock_catalog_repo.count_by_status.return_value = {"new": len(filtered_entries)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(filtered_entries)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=50"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the repository was called with correct min_confidence parameter
        mock_catalog_repo.get_source_catalog.assert_called_once()
        call_kwargs = mock_catalog_repo.get_source_catalog.call_args[1]
        assert call_kwargs.get("min_confidence") == 50

        # Should only return filtered entries
        assert len(data["items"]) == 3  # 95, 75, 50
        for item in data["items"]:
            assert item["confidence_score"] >= 50

    def test_filter_by_max_confidence(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test max_confidence parameter filters correctly."""
        mock_catalog_repo = MagicMock()

        # Filter entries <= 70
        filtered_entries = [e for e in mock_catalog_entries_with_scores if e.confidence_score <= 70]
        mock_catalog_repo.get_source_catalog.return_value = filtered_entries
        mock_catalog_repo.count_by_status.return_value = {"new": len(filtered_entries)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(filtered_entries)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?max_confidence=70"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the repository was called with correct max_confidence parameter
        mock_catalog_repo.get_source_catalog.assert_called_once()
        call_kwargs = mock_catalog_repo.get_source_catalog.call_args[1]
        assert call_kwargs.get("max_confidence") == 70

        # Should only return filtered entries
        assert len(data["items"]) == 4  # 50, 40, 25, 15 <= 70
        for item in data["items"]:
            assert item["confidence_score"] <= 70

    def test_filter_by_confidence_range(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test min and max confidence together."""
        mock_catalog_repo = MagicMock()

        # Filter entries 40 <= confidence <= 80
        filtered_entries = [
            e for e in mock_catalog_entries_with_scores
            if 40 <= e.confidence_score <= 80
        ]
        mock_catalog_repo.get_source_catalog.return_value = filtered_entries
        mock_catalog_repo.count_by_status.return_value = {"new": len(filtered_entries)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(filtered_entries)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?min_confidence=40&max_confidence=80"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the repository was called with both parameters
        mock_catalog_repo.get_source_catalog.assert_called_once()
        call_kwargs = mock_catalog_repo.get_source_catalog.call_args[1]
        assert call_kwargs.get("max_confidence") == 80
        # Router applies max(min_confidence, threshold) since include_below_threshold defaults to False
        assert call_kwargs.get("min_confidence") == 40

        # Should only return filtered entries
        assert len(data["items"]) == 3  # 75, 50, 40
        for item in data["items"]:
            assert 40 <= item["confidence_score"] <= 80

    def test_include_below_threshold_false(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test default behavior hides entries < 30%."""
        mock_catalog_repo = MagicMock()

        # Default threshold = 30, filter entries >= 30
        filtered_entries = [e for e in mock_catalog_entries_with_scores if e.confidence_score >= 30]
        # When only threshold is applied (no other filters), router uses list_paginated
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=[], has_more=False  # Not used because get_source_catalog is called
        )
        mock_catalog_repo.get_source_catalog.return_value = filtered_entries
        mock_catalog_repo.count_by_status.return_value = {"new": len(filtered_entries)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(filtered_entries)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            # No parameters - should apply default threshold via get_source_catalog
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify threshold is applied via get_source_catalog (min_confidence should be 30)
        mock_catalog_repo.get_source_catalog.assert_called_once()
        call_kwargs = mock_catalog_repo.get_source_catalog.call_args[1]
        assert call_kwargs.get("min_confidence") == 30

        # Should only return filtered entries
        assert len(data["items"]) == 4  # 95, 75, 50, 40
        for item in data["items"]:
            assert item["confidence_score"] >= 30

    def test_include_below_threshold_true(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test toggle shows hidden entries."""
        mock_catalog_repo = MagicMock()

        # include_below_threshold=True - show ALL entries
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=mock_catalog_entries_with_scores, has_more=False
        )
        mock_catalog_repo.count_by_status.return_value = {"new": len(mock_catalog_entries_with_scores)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(mock_catalog_entries_with_scores)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?include_below_threshold=true"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should include ALL entries, even those < 30
        assert len(data["items"]) == 6  # All entries
        confidence_scores = [item["confidence_score"] for item in data["items"]]
        assert min(confidence_scores) < 30  # Verify we have low-confidence entries

    def test_response_includes_raw_score(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test API response includes raw_score field."""
        mock_catalog_repo = MagicMock()
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=[mock_catalog_entries_with_scores[0]], has_more=False
        )
        mock_catalog_repo.count_by_status.return_value = {"new": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 1}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?include_below_threshold=true"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify raw_score field exists
        assert "raw_score" in data["items"][0]
        assert data["items"][0]["raw_score"] is not None
        assert isinstance(data["items"][0]["raw_score"], int)

    def test_response_includes_breakdown(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test API response includes score_breakdown field."""
        mock_catalog_repo = MagicMock()
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=[mock_catalog_entries_with_scores[0]], has_more=False
        )
        mock_catalog_repo.count_by_status.return_value = {"new": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 1}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?include_below_threshold=true"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify score_breakdown field exists and has expected structure
        assert "score_breakdown" in data["items"][0]
        breakdown = data["items"][0]["score_breakdown"]
        assert breakdown is not None
        assert isinstance(breakdown, dict)

        # Verify expected keys in breakdown
        expected_keys = [
            "dir_name_score",
            "manifest_score",
            "extensions_score",
            "parent_hint_score",
            "frontmatter_score",
            "depth_penalty",
            "raw_total",
            "normalized_score",
        ]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"

    def test_threshold_interaction_with_min_confidence(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test min_confidence=20 with include_below_threshold=False still applies 30 threshold."""
        mock_catalog_repo = MagicMock()

        # threshold=False means default threshold (30) applies
        # Even though min_confidence=20, the effective min should be max(20, 30) = 30
        filtered_entries = [e for e in mock_catalog_entries_with_scores if e.confidence_score >= 30]
        mock_catalog_repo.get_source_catalog.return_value = filtered_entries
        mock_catalog_repo.count_by_status.return_value = {"new": len(filtered_entries)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(filtered_entries)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?min_confidence=20&include_below_threshold=false"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify effective min_confidence is 30 (threshold wins)
        mock_catalog_repo.get_source_catalog.assert_called_once()
        call_kwargs = mock_catalog_repo.get_source_catalog.call_args[1]
        assert call_kwargs.get("min_confidence") == 30  # max(20, 30) = 30

        # Should apply threshold (30), not user's min_confidence (20)
        assert len(data["items"]) == 4  # >= 30
        for item in data["items"]:
            assert item["confidence_score"] >= 30

    def test_min_confidence_overrides_threshold(
        self, client, mock_source_repo, mock_catalog_entries_with_scores
    ):
        """Test min_confidence=40 is stricter than 30 threshold."""
        mock_catalog_repo = MagicMock()

        # min_confidence=40 is stricter than threshold=30
        # Effective min should be max(40, 30) = 40
        filtered_entries = [e for e in mock_catalog_entries_with_scores if e.confidence_score >= 40]
        mock_catalog_repo.get_source_catalog.return_value = filtered_entries
        mock_catalog_repo.count_by_status.return_value = {"new": len(filtered_entries)}
        mock_catalog_repo.count_by_type.return_value = {"skill": len(filtered_entries)}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?min_confidence=40&include_below_threshold=false"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify effective min_confidence is 40 (user's value wins)
        mock_catalog_repo.get_source_catalog.assert_called_once()
        call_kwargs = mock_catalog_repo.get_source_catalog.call_args[1]
        assert call_kwargs.get("min_confidence") == 40  # max(40, 30) = 40

        # Should apply stricter min_confidence (40)
        assert len(data["items"]) == 4  # >= 40
        for item in data["items"]:
            assert item["confidence_score"] >= 40

    def test_confidence_validation_min_too_low(
        self, client, mock_source_repo
    ):
        """Test min_confidence validation rejects values < 0."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=-1"
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_confidence_validation_min_too_high(
        self, client, mock_source_repo
    ):
        """Test min_confidence validation rejects values > 100."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?min_confidence=101"
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_confidence_validation_max_too_low(
        self, client, mock_source_repo
    ):
        """Test max_confidence validation rejects values < 0."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?max_confidence=-1"
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_confidence_validation_max_too_high(
        self, client, mock_source_repo
    ):
        """Test max_confidence validation rejects values > 100."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?max_confidence=101"
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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


# =============================================================================
# Test Get File Tree (GET /marketplace/sources/{source_id}/artifacts/{path}/files)
# =============================================================================


class TestGetFileTree:
    """Test GET /marketplace/sources/{source_id}/artifacts/{artifact_path}/files endpoint."""

    @pytest.fixture
    def mock_file_tree(self):
        """Create mock file tree entries from GitHubScanner."""
        return [
            {"path": "SKILL.md", "type": "blob", "size": 2048, "sha": "abc123def456"},
            {"path": "src", "type": "tree", "size": None, "sha": "def789abc123"},
            {"path": "src/index.ts", "type": "blob", "size": 1024, "sha": "ghi456jkl789"},
            {"path": "README.md", "type": "blob", "size": 512, "sha": "mno012pqr345"},
        ]

    @pytest.fixture
    def mock_github_file_cache(self):
        """Create a fresh mock cache for each test."""
        from skillmeat.api.utils.github_cache import GitHubFileCache

        cache = GitHubFileCache(max_entries=100)
        return cache

    def test_get_file_tree_success(
        self, client, mock_source_repo, mock_file_tree, mock_github_file_cache
    ):
        """Test successful file tree retrieval."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.return_value = mock_file_tree

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "entries" in data
        assert "artifact_path" in data
        assert "source_id" in data

        # Verify artifact metadata
        assert data["artifact_path"] == "skills/canvas"
        assert data["source_id"] == "src_test_123"

        # Verify file tree entries
        assert len(data["entries"]) == 4

        # Check entry structure
        skill_md = next(e for e in data["entries"] if e["path"] == "SKILL.md")
        assert skill_md["type"] == "blob"
        assert skill_md["size"] == 2048
        assert skill_md["sha"] == "abc123def456"

        # Check directory entry
        src_dir = next(e for e in data["entries"] if e["path"] == "src")
        assert src_dir["type"] == "tree"
        assert src_dir["size"] is None

    def test_get_file_tree_source_not_found(self, client, mock_source_repo):
        """Test 404 for non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/nonexistent/artifacts/skills/canvas/files"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_file_tree_artifact_not_found(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test 404 for non-existent artifact path."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.return_value = []  # Empty means not found

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/nonexistent/path/files"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_file_tree_cache_hit(
        self, client, mock_source_repo, mock_file_tree, mock_github_file_cache
    ):
        """Test cache is used on second request."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.return_value = mock_file_tree

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            # First request - cache miss
            response1 = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )
            assert response1.status_code == status.HTTP_200_OK

            # GitHubScanner should be called once
            assert mock_scanner.get_file_tree.call_count == 1

            # Second request - cache hit (scanner should not be called again)
            response2 = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )
            assert response2.status_code == status.HTTP_200_OK

            # Scanner should still have been called only once (cache hit)
            assert mock_scanner.get_file_tree.call_count == 1

            # Verify responses are identical
            assert response1.json() == response2.json()

    def test_get_file_tree_github_api_error(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test handling of GitHub API errors."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.side_effect = Exception("GitHub API rate limited")

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve file tree" in response.json()["detail"]

    def test_get_file_tree_nested_artifact_path(
        self, client, mock_source_repo, mock_file_tree, mock_github_file_cache
    ):
        """Test file tree retrieval for deeply nested artifact paths."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.return_value = mock_file_tree

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/deep/nested/path/artifact/files"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["artifact_path"] == "deep/nested/path/artifact"


# =============================================================================
# Test Get File Content (GET /marketplace/sources/{source_id}/artifacts/{path}/files/{file})
# =============================================================================


class TestGetFileContent:
    """Test GET /marketplace/sources/{source_id}/artifacts/{artifact_path}/files/{file_path} endpoint."""

    @pytest.fixture
    def mock_text_file_content(self):
        """Create mock text file content from GitHubScanner."""
        return {
            "content": "# Canvas Design Skill\n\nThis is a sample skill...",
            "encoding": "none",
            "size": 2048,
            "sha": "abc123def456789abcdef0123456789abcdef01",
            "name": "SKILL.md",
            "path": "skills/canvas/SKILL.md",
            "is_binary": False,
        }

    @pytest.fixture
    def mock_binary_file_content(self):
        """Create mock binary file content (base64 encoded)."""
        import base64

        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        return {
            "content": base64.b64encode(binary_data).decode("utf-8"),
            "encoding": "base64",
            "size": len(binary_data),
            "sha": "binary123sha456",
            "name": "logo.png",
            "path": "skills/canvas/assets/logo.png",
            "is_binary": True,
        }

    @pytest.fixture
    def mock_github_file_cache(self):
        """Create a fresh mock cache for each test."""
        from skillmeat.api.utils.github_cache import GitHubFileCache

        cache = GitHubFileCache(max_entries=100)
        return cache

    def test_get_file_content_success(
        self, client, mock_source_repo, mock_text_file_content, mock_github_file_cache
    ):
        """Test successful file content retrieval."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_content.return_value = mock_text_file_content

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/SKILL.md"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "content" in data
        assert "encoding" in data
        assert "size" in data
        assert "sha" in data
        assert "name" in data
        assert "path" in data
        assert "is_binary" in data
        assert "artifact_path" in data
        assert "source_id" in data

        # Verify content
        assert data["content"] == "# Canvas Design Skill\n\nThis is a sample skill..."
        assert data["encoding"] == "none"
        assert data["size"] == 2048
        assert data["name"] == "SKILL.md"
        assert data["is_binary"] is False
        assert data["artifact_path"] == "skills/canvas"
        assert data["source_id"] == "src_test_123"

    def test_get_file_content_binary_file(
        self, client, mock_source_repo, mock_binary_file_content, mock_github_file_cache
    ):
        """Test binary file handling with base64 encoding."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_content.return_value = mock_binary_file_content

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/assets/logo.png"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify binary file handling
        assert data["is_binary"] is True
        assert data["encoding"] == "base64"
        assert data["name"] == "logo.png"
        # Content should be base64 encoded
        assert len(data["content"]) > 0

    def test_get_file_content_source_not_found(self, client, mock_source_repo):
        """Test 404 for non-existent source."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/nonexistent/artifacts/skills/canvas/files/SKILL.md"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_file_content_file_not_found(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test 404 for non-existent file."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_content.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/nonexistent.md"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_file_content_cache_hit(
        self, client, mock_source_repo, mock_text_file_content, mock_github_file_cache
    ):
        """Test cache is used on second request."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_content.return_value = mock_text_file_content

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            # First request - cache miss
            response1 = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/SKILL.md"
            )
            assert response1.status_code == status.HTTP_200_OK

            # GitHubScanner should be called once
            assert mock_scanner.get_file_content.call_count == 1

            # Second request - cache hit
            response2 = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/SKILL.md"
            )
            assert response2.status_code == status.HTTP_200_OK

            # Scanner should still have been called only once (cache hit)
            assert mock_scanner.get_file_content.call_count == 1

            # Verify responses are identical
            assert response1.json() == response2.json()

    def test_get_file_content_github_api_error(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test handling of GitHub API errors."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_content.side_effect = Exception("GitHub API error")

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/SKILL.md"
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve file content" in response.json()["detail"]

    def test_get_file_content_nested_path(
        self, client, mock_source_repo, mock_text_file_content, mock_github_file_cache
    ):
        """Test file content retrieval for deeply nested file paths."""
        mock_scanner = MagicMock()
        mock_scanner.get_file_content.return_value = mock_text_file_content

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/src/components/deep/nested/file.tsx"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["artifact_path"] == "skills/canvas"

    def test_get_file_content_different_file_types(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test content retrieval for various file types."""
        file_types = [
            ("main.py", "python"),
            ("index.ts", "typescript"),
            ("styles.css", "css"),
            ("config.json", "json"),
            ("schema.yaml", "yaml"),
        ]

        mock_scanner = MagicMock()

        for filename, _ in file_types:
            mock_content = {
                "content": f"# Content of {filename}",
                "encoding": "none",
                "size": 100,
                "sha": f"sha_{filename}",
                "name": filename,
                "path": f"skills/canvas/{filename}",
                "is_binary": False,
            }
            mock_scanner.get_file_content.return_value = mock_content

            with patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner",
                return_value=mock_scanner,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
                return_value=mock_github_file_cache,
            ):
                response = client.get(
                    f"/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/{filename}"
                )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == filename


# =============================================================================
# Test GitHub Cache Integration
# =============================================================================


class TestGitHubCacheIntegration:
    """Test GitHubFileCache integration with file endpoints."""

    @pytest.fixture
    def mock_github_file_cache(self):
        """Create a fresh mock cache for each test."""
        from skillmeat.api.utils.github_cache import GitHubFileCache

        cache = GitHubFileCache(max_entries=100)
        return cache

    def test_cache_key_format_tree(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test cache key format for tree requests."""
        from skillmeat.api.utils.github_cache import build_tree_key

        source_id = "src_test_123"
        artifact_path = "skills/canvas"
        sha = "main"

        expected_key = f"tree:{source_id}:{artifact_path}:{sha}"
        actual_key = build_tree_key(source_id, artifact_path, sha)

        assert actual_key == expected_key

    def test_cache_key_format_content(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test cache key format for content requests."""
        from skillmeat.api.utils.github_cache import build_content_key

        source_id = "src_test_123"
        artifact_path = "skills/canvas"
        file_path = "SKILL.md"
        sha = "main"

        expected_key = f"content:{source_id}:{artifact_path}:{file_path}:{sha}"
        actual_key = build_content_key(source_id, artifact_path, file_path, sha)

        assert actual_key == expected_key

    def test_cache_expiration(self, mock_github_file_cache):
        """Test cache entry expiration."""
        import time

        # Set a very short TTL (1 second)
        mock_github_file_cache.set("test_key", {"data": "value"}, ttl_seconds=1)

        # Should be available immediately
        assert mock_github_file_cache.get("test_key") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert mock_github_file_cache.get("test_key") is None

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        from skillmeat.api.utils.github_cache import GitHubFileCache

        # Create small cache
        cache = GitHubFileCache(max_entries=3)

        # Add entries
        cache.set("key1", "value1", ttl_seconds=3600)
        cache.set("key2", "value2", ttl_seconds=3600)
        cache.set("key3", "value3", ttl_seconds=3600)

        # Access key1 to make it recently used
        cache.get("key1")

        # Add new entry - should evict key2 (least recently used)
        cache.set("key4", "value4", ttl_seconds=3600)

        # key2 should be evicted
        assert cache.get("key1") is not None  # Recently used
        assert cache.get("key2") is None  # Evicted (LRU)
        assert cache.get("key3") is not None  # Still present
        assert cache.get("key4") is not None  # New entry

    def test_cache_stats(self, mock_github_file_cache):
        """Test cache statistics tracking."""
        # Add entry
        mock_github_file_cache.set("key1", "value1", ttl_seconds=3600)

        # Hit
        mock_github_file_cache.get("key1")

        # Miss
        mock_github_file_cache.get("nonexistent")

        stats = mock_github_file_cache.stats()

        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_cache_clear(self, mock_github_file_cache):
        """Test clearing cache."""
        mock_github_file_cache.set("key1", "value1", ttl_seconds=3600)
        mock_github_file_cache.set("key2", "value2", ttl_seconds=3600)

        assert len(mock_github_file_cache) == 2

        mock_github_file_cache.clear()

        assert len(mock_github_file_cache) == 0
        assert mock_github_file_cache.get("key1") is None


# =============================================================================
# Test Delete Source (DELETE /marketplace/sources/{source_id})
# =============================================================================


class TestDeleteSource:
    """Test DELETE /marketplace/sources/{source_id} endpoint."""

    def test_delete_source_success(self, client, mock_source_repo):
        """Test successful source deletion."""
        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.delete("/api/v1/marketplace/sources/src_test_123")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_source_not_found(self, client, mock_source_repo):
        """Test deleting a non-existent source."""
        mock_source_repo.delete.return_value = False

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.delete("/api/v1/marketplace/sources/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test Rate Limit Handling for File Endpoints
# =============================================================================


class TestFileEndpointsRateLimiting:
    """Test rate limit handling for file tree and content endpoints."""

    @pytest.fixture
    def mock_github_file_cache(self):
        """Create a fresh mock cache for each test."""
        from skillmeat.api.utils.github_cache import GitHubFileCache

        cache = GitHubFileCache(max_entries=100)
        return cache

    def test_file_tree_rate_limit(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test 429 response with Retry-After header for file tree endpoint."""
        from skillmeat.core.marketplace.github_scanner import RateLimitError

        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.side_effect = RateLimitError(
            "GitHub API rate limit exceeded (0 requests remaining). "
            "Wait 3600 seconds before retrying."
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )

        # Verify 429 status code
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify Retry-After header is present
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0  # Should have a positive retry value

        # Verify error detail
        data = response.json()
        assert "rate limit" in data["detail"].lower()

    def test_file_content_rate_limit(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test 429 response with Retry-After header for file content endpoint."""
        from skillmeat.core.marketplace.github_scanner import RateLimitError

        mock_scanner = MagicMock()
        mock_scanner.get_file_content.side_effect = RateLimitError(
            "GitHub API rate limit exceeded (0 requests remaining). "
            "Wait 1800 seconds before retrying."
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/SKILL.md"
            )

        # Verify 429 status code
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Verify Retry-After header is present
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0

        # Verify error detail
        data = response.json()
        assert "rate limit" in data["detail"].lower()

    def test_file_tree_rate_limit_retry_after_parsing(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test that Retry-After value is correctly parsed from error message."""
        from skillmeat.core.marketplace.github_scanner import RateLimitError

        # Test with specific wait time - parser looks for pattern like "45s" or "60s"
        wait_time = 7200
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.side_effect = RateLimitError(
            f"GitHub API rate limit exceeded. Rate limited for {wait_time}s."
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.headers["Retry-After"] == str(wait_time)

    def test_file_tree_rate_limit_default_retry_after(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test that default Retry-After is used when parsing fails."""
        from skillmeat.core.marketplace.github_scanner import RateLimitError

        # Error message without parseable wait time
        mock_scanner = MagicMock()
        mock_scanner.get_file_tree.side_effect = RateLimitError(
            "GitHub API rate limit exceeded with no time info"
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files"
            )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # Should use default value (typically 60 seconds)
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0  # Default should be positive

    def test_file_content_rate_limit_retry_after_parsing(
        self, client, mock_source_repo, mock_github_file_cache
    ):
        """Test Retry-After parsing for file content endpoint."""
        from skillmeat.core.marketplace.github_scanner import RateLimitError

        wait_time = 300  # 5 minutes
        mock_scanner = MagicMock()
        # Parser looks for pattern like "45s" or "60s"
        mock_scanner.get_file_content.side_effect = RateLimitError(
            f"Rate limit exceeded, reset in {wait_time}s"
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=mock_github_file_cache,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts/skills/canvas/files/SKILL.md"
            )

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert response.headers["Retry-After"] == str(wait_time)


# =============================================================================
# Test Exclude Artifact (PATCH /marketplace/sources/{source_id}/artifacts/{entry_id}/exclude)
# =============================================================================


class TestExcludeArtifact:
    """Test PATCH /marketplace/sources/{source_id}/artifacts/{entry_id}/exclude endpoint."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        mock = MagicMock()
        mock.query.return_value.filter_by.return_value.first.return_value = None
        mock.commit.return_value = None
        mock.rollback.return_value = None
        mock.refresh.return_value = None
        return mock

    @pytest.fixture
    def mock_catalog_entry_for_exclusion(self):
        """Create a mock catalog entry for exclusion tests."""
        entry = MarketplaceCatalogEntry(
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
            excluded_at=None,
            excluded_reason=None,
        )
        return entry

    @pytest.fixture
    def mock_excluded_catalog_entry(self):
        """Create a mock catalog entry that is already excluded."""
        entry = MarketplaceCatalogEntry(
            id="cat_test_789",
            source_id="src_test_123",
            artifact_type="skill",
            name="excluded-skill",
            path="skills/excluded-skill",
            upstream_url="https://github.com/anthropics/repo/tree/main/skills/excluded-skill",
            detected_version="1.0.0",
            detected_sha="def456abc123",
            detected_at=datetime(2025, 12, 6, 10, 30, 0),
            confidence_score=50,
            status="excluded",
            excluded_at=datetime(2025, 12, 7, 12, 0, 0),
            excluded_reason="False positive - documentation only",
        )
        return entry

    def test_exclude_artifact_success(
        self, client, mock_source_repo, mock_catalog_repo, mock_catalog_entry_for_exclusion
    ):
        """Test excluding an artifact successfully."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_catalog_entry_for_exclusion
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_456/exclude",
                json={
                    "excluded": True,
                    "reason": "False positive - documentation file",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the entry was marked as excluded
        assert data["id"] == "cat_test_456"
        assert data["status"] == "excluded"
        # The excluded_at should be set (we verify it's not None in the response)
        assert data["excluded_at"] is not None
        assert data["excluded_reason"] == "False positive - documentation file"

    def test_exclude_artifact_without_reason(
        self, client, mock_source_repo, mock_catalog_repo, mock_catalog_entry_for_exclusion
    ):
        """Test excluding an artifact without providing a reason."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_catalog_entry_for_exclusion
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_456/exclude",
                json={"excluded": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "excluded"
        # Reason should be None when not provided
        assert data["excluded_reason"] is None

    def test_exclude_artifact_idempotent(
        self, client, mock_source_repo, mock_catalog_repo, mock_excluded_catalog_entry
    ):
        """Test excluding an already excluded artifact returns success (idempotent)."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_excluded_catalog_entry
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_789/exclude",
                json={
                    "excluded": True,
                    "reason": "New reason",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "excluded"
        # The reason should be updated even on idempotent call
        assert data["excluded_reason"] == "New reason"

    def test_exclude_artifact_not_found(self, client, mock_source_repo, mock_catalog_repo):
        """Test excluding a non-existent artifact returns 404."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/artifacts/nonexistent/exclude",
                json={"excluded": True},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_exclude_artifact_wrong_source(
        self, client, mock_source_repo, mock_catalog_repo, mock_catalog_entry_for_exclusion
    ):
        """Test excluding artifact that belongs to different source returns 400."""
        # Create an entry that belongs to a different source
        wrong_source_entry = MarketplaceCatalogEntry(
            id="cat_test_999",
            source_id="src_other_456",  # Different source
            artifact_type="skill",
            name="other-skill",
            path="skills/other-skill",
            upstream_url="https://github.com/other/repo/tree/main/skills/other-skill",
            detected_version="1.0.0",
            detected_sha="xyz789",
            detected_at=datetime(2025, 12, 6, 10, 30, 0),
            confidence_score=80,
            status="new",
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            wrong_source_entry
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_999/exclude",
                json={"excluded": True},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not belong to source" in response.json()["detail"]

    def test_exclude_artifact_source_not_found(self, client, mock_source_repo, mock_catalog_repo):
        """Test excluding artifact when source doesn't exist returns 404."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/nonexistent/artifacts/cat_test_456/exclude",
                json={"excluded": True},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "source" in response.json()["detail"].lower()


# =============================================================================
# Test Restore Excluded Artifact (DELETE /marketplace/sources/{source_id}/artifacts/{entry_id}/exclude)
# =============================================================================


class TestRestoreExcludedArtifact:
    """Test DELETE /marketplace/sources/{source_id}/artifacts/{entry_id}/exclude endpoint."""

    @pytest.fixture
    def mock_excluded_entry(self):
        """Create a mock excluded catalog entry."""
        return MarketplaceCatalogEntry(
            id="cat_test_789",
            source_id="src_test_123",
            artifact_type="skill",
            name="excluded-skill",
            path="skills/excluded-skill",
            upstream_url="https://github.com/anthropics/repo/tree/main/skills/excluded-skill",
            detected_version="1.0.0",
            detected_sha="def456abc123",
            detected_at=datetime(2025, 12, 6, 10, 30, 0),
            confidence_score=50,
            status="excluded",
            excluded_at=datetime(2025, 12, 7, 12, 0, 0),
            excluded_reason="False positive - documentation only",
            import_date=None,
        )

    @pytest.fixture
    def mock_excluded_imported_entry(self):
        """Create a mock excluded catalog entry that was previously imported."""
        return MarketplaceCatalogEntry(
            id="cat_test_800",
            source_id="src_test_123",
            artifact_type="skill",
            name="imported-then-excluded-skill",
            path="skills/imported-then-excluded-skill",
            upstream_url="https://github.com/anthropics/repo/tree/main/skills/imported-skill",
            detected_version="1.0.0",
            detected_sha="ghi789",
            detected_at=datetime(2025, 12, 6, 10, 30, 0),
            confidence_score=75,
            status="excluded",
            excluded_at=datetime(2025, 12, 7, 12, 0, 0),
            excluded_reason="Accidentally excluded",
            import_date=datetime(2025, 12, 6, 11, 0, 0),  # Was imported before exclusion
        )

    def test_restore_excluded_artifact_success(
        self, client, mock_source_repo, mock_catalog_repo, mock_excluded_entry
    ):
        """Test restoring an excluded artifact successfully."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_excluded_entry
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.delete(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_789/exclude"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify the entry was restored
        assert data["id"] == "cat_test_789"
        # Status should be "new" since it was never imported
        assert data["status"] == "new"
        # Exclusion fields should be cleared
        assert data["excluded_at"] is None
        assert data["excluded_reason"] is None

    def test_restore_excluded_artifact_restores_to_imported(
        self, client, mock_source_repo, mock_catalog_repo, mock_excluded_imported_entry
    ):
        """Test restoring an artifact that was previously imported restores to 'imported' status."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_excluded_imported_entry
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.delete(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_800/exclude"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Status should be "imported" since it has an import_date
        assert data["status"] == "imported"
        assert data["excluded_at"] is None
        assert data["excluded_reason"] is None

    def test_restore_artifact_idempotent(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test restoring a non-excluded artifact returns success (idempotent)."""
        # Create entry that is NOT excluded
        non_excluded_entry = MarketplaceCatalogEntry(
            id="cat_test_456",
            source_id="src_test_123",
            artifact_type="skill",
            name="active-skill",
            path="skills/active-skill",
            upstream_url="https://github.com/anthropics/repo/tree/main/skills/active-skill",
            detected_version="1.0.0",
            detected_sha="abc123",
            detected_at=datetime(2025, 12, 6, 10, 30, 0),
            confidence_score=90,
            status="new",
            excluded_at=None,  # Not excluded
            excluded_reason=None,
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            non_excluded_entry
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.delete(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_456/exclude"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should still be "new", no change
        assert data["status"] == "new"

    def test_restore_artifact_not_found(self, client, mock_source_repo, mock_catalog_repo):
        """Test restoring a non-existent artifact returns 404."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.delete(
                "/api/v1/marketplace/sources/src_test_123/artifacts/nonexistent/exclude"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_restore_artifact_wrong_source(
        self, client, mock_source_repo, mock_catalog_repo
    ):
        """Test restoring artifact that belongs to different source returns 400."""
        wrong_source_entry = MarketplaceCatalogEntry(
            id="cat_test_999",
            source_id="src_other_456",  # Different source
            artifact_type="skill",
            name="other-skill",
            path="skills/other-skill",
            upstream_url="https://github.com/other/repo/tree/main/skills/other-skill",
            detected_version="1.0.0",
            detected_sha="xyz789",
            detected_at=datetime(2025, 12, 6, 10, 30, 0),
            confidence_score=80,
            status="excluded",
            excluded_at=datetime(2025, 12, 7, 12, 0, 0),
            excluded_reason="Some reason",
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            wrong_source_entry
        )
        mock_catalog_repo._get_session.return_value = mock_session

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.delete(
                "/api/v1/marketplace/sources/src_test_123/artifacts/cat_test_999/exclude"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not belong to source" in response.json()["detail"]

    def test_restore_artifact_source_not_found(self, client, mock_source_repo, mock_catalog_repo):
        """Test restoring artifact when source doesn't exist returns 404."""
        mock_source_repo.get_by_id.return_value = None

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.delete(
                "/api/v1/marketplace/sources/nonexistent/artifacts/cat_test_456/exclude"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test List Artifacts Exclusion Filtering (GET /marketplace/sources/{source_id}/artifacts)
# =============================================================================


class TestListArtifactsExclusionFiltering:
    """Test include_excluded parameter for GET /marketplace/sources/{source_id}/artifacts endpoint."""

    @pytest.fixture
    def mock_entries_with_excluded(self, mock_source):
        """Create mock catalog entries including excluded ones."""
        entries = [
            MarketplaceCatalogEntry(
                id="cat_active_1",
                source_id=mock_source.id,
                artifact_type="skill",
                name="active-skill-1",
                path="skills/active-skill-1",
                upstream_url="https://github.com/test/repo/tree/main/skills/active-skill-1",
                detected_version="1.0.0",
                detected_sha="sha1",
                detected_at=datetime(2025, 12, 6, 10, 30, 0),
                confidence_score=90,
                status="new",
                excluded_at=None,
                excluded_reason=None,
            ),
            MarketplaceCatalogEntry(
                id="cat_active_2",
                source_id=mock_source.id,
                artifact_type="skill",
                name="active-skill-2",
                path="skills/active-skill-2",
                upstream_url="https://github.com/test/repo/tree/main/skills/active-skill-2",
                detected_version="1.0.0",
                detected_sha="sha2",
                detected_at=datetime(2025, 12, 6, 10, 30, 0),
                confidence_score=85,
                status="imported",
                excluded_at=None,
                excluded_reason=None,
            ),
            MarketplaceCatalogEntry(
                id="cat_excluded_1",
                source_id=mock_source.id,
                artifact_type="skill",
                name="excluded-skill",
                path="skills/excluded-skill",
                upstream_url="https://github.com/test/repo/tree/main/skills/excluded-skill",
                detected_version="1.0.0",
                detected_sha="sha3",
                detected_at=datetime(2025, 12, 6, 10, 30, 0),
                confidence_score=40,
                status="excluded",
                excluded_at=datetime(2025, 12, 7, 12, 0, 0),
                excluded_reason="False positive",
            ),
        ]
        return entries

    def test_list_artifacts_excludes_excluded_by_default(
        self, client, mock_source_repo, mock_catalog_repo, mock_entries_with_excluded
    ):
        """Test that excluded artifacts are NOT returned by default."""
        # Return all entries from the repo query
        mock_catalog_repo.get_source_catalog.return_value = mock_entries_with_excluded
        mock_catalog_repo.count_by_status.return_value = {"new": 1, "imported": 1, "excluded": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 3}

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

        # Should only return non-excluded entries (2 out of 3)
        assert len(data["items"]) == 2
        item_ids = [item["id"] for item in data["items"]]
        assert "cat_active_1" in item_ids
        assert "cat_active_2" in item_ids
        assert "cat_excluded_1" not in item_ids

    def test_list_artifacts_include_excluded_true(
        self, client, mock_source_repo, mock_entries_with_excluded
    ):
        """Test that excluded artifacts ARE returned when include_excluded=true.

        Note: include_below_threshold=true is also needed to avoid the 30% confidence
        threshold filter, which would otherwise cause the router to use get_source_catalog
        instead of list_paginated.
        """
        # Create a fresh mock catalog repo with correct data for this test
        mock_catalog_repo = MagicMock()
        # When include_excluded=true AND include_below_threshold=true AND no other filters,
        # the router uses list_paginated for efficient pagination
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=mock_entries_with_excluded, has_more=False
        )
        mock_catalog_repo.count_by_status.return_value = {"new": 1, "imported": 1, "excluded": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 3}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?include_excluded=true&include_below_threshold=true"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return all entries including excluded (3 total)
        assert len(data["items"]) == 3
        item_ids = [item["id"] for item in data["items"]]
        assert "cat_excluded_1" in item_ids

    def test_list_artifacts_status_excluded_filter(
        self, client, mock_source_repo, mock_catalog_repo, mock_entries_with_excluded
    ):
        """Test filtering by status=excluded returns only excluded entries."""
        # Filter to only excluded entries
        excluded_entries = [e for e in mock_entries_with_excluded if e.status == "excluded"]
        mock_catalog_repo.get_source_catalog.return_value = excluded_entries
        mock_catalog_repo.count_by_status.return_value = {"new": 1, "imported": 1, "excluded": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 3}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?status=excluded"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return only the excluded entry
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "cat_excluded_1"
        assert data["items"][0]["status"] == "excluded"

    def test_list_artifacts_include_excluded_false_explicit(
        self, client, mock_source_repo, mock_catalog_repo, mock_entries_with_excluded
    ):
        """Test that explicitly setting include_excluded=false excludes entries."""
        mock_catalog_repo.get_source_catalog.return_value = mock_entries_with_excluded
        mock_catalog_repo.count_by_status.return_value = {"new": 1, "imported": 1, "excluded": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 3}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts?include_excluded=false"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should exclude the excluded entry
        assert len(data["items"]) == 2
        item_ids = [item["id"] for item in data["items"]]
        assert "cat_excluded_1" not in item_ids

    def test_list_artifacts_excluded_entry_has_exclusion_fields(
        self, client, mock_source_repo, mock_entries_with_excluded
    ):
        """Test that excluded entries include excluded_at and excluded_reason in response.

        Note: include_below_threshold=true is also needed to avoid the 30% confidence
        threshold filter, which would otherwise cause the router to use get_source_catalog
        instead of list_paginated.
        """
        # Create a fresh mock catalog repo with correct data for this test
        mock_catalog_repo = MagicMock()
        # When include_excluded=true AND include_below_threshold=true AND no other filters,
        # the router uses list_paginated for efficient pagination
        mock_catalog_repo.list_paginated.return_value = MagicMock(
            items=mock_entries_with_excluded, has_more=False
        )
        mock_catalog_repo.count_by_status.return_value = {"new": 1, "imported": 1, "excluded": 1}
        mock_catalog_repo.count_by_type.return_value = {"skill": 3}

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceCatalogRepository",
            return_value=mock_catalog_repo,
        ):
            response = client.get(
                "/api/v1/marketplace/sources/src_test_123/artifacts"
                "?include_excluded=true&include_below_threshold=true"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Find the excluded entry
        excluded_entry = next(
            (item for item in data["items"] if item["id"] == "cat_excluded_1"), None
        )
        assert excluded_entry is not None
        assert excluded_entry["excluded_at"] is not None
        assert excluded_entry["excluded_reason"] == "False positive"

        # Non-excluded entries should have None for these fields
        active_entry = next(
            (item for item in data["items"] if item["id"] == "cat_active_1"), None
        )
        assert active_entry is not None
        assert active_entry["excluded_at"] is None
        assert active_entry["excluded_reason"] is None


# =============================================================================
# P2-T5: File serving endpoint — path resolution regression and defensive tests
# Tests the GET /api/v1/marketplace/sources/{id}/artifacts/{path}/files/{file}
# endpoint for both directory-based (existing) and file-path (embedded) cases.
# Depends on P2-T1 (defensive path resolution) being implemented.
# =============================================================================


class TestFileServingPathResolution:
    """Regression and defensive tests for file serving path resolution (P2-T5).

    Two scenarios are verified:

    1. **Directory-based artifact** (existing behaviour):
       ``artifact_path = "skills/my-skill"`` + ``file_path = "SKILL.md"``
       → scanner receives ``"skills/my-skill/SKILL.md"``

    2. **File-path artifact** (embedded-artifact defensive fallback, P2-T1):
       ``artifact_path = "skills/my-skill/commands/foo.md"`` + ``file_path = "foo.md"``
       → scanner must receive ``"skills/my-skill/commands/foo.md"`` (NOT
         ``"skills/my-skill/commands/foo.md/foo.md"``)
    """

    # ------------------------------------------------------------------
    # Shared fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def mock_source(self):
        """Minimal mock MarketplaceSource for path-resolution tests."""
        src = MagicMock()
        src.owner = "anthropics"
        src.repo_name = "quickstarts"
        src.ref = "main"
        return src

    @pytest.fixture
    def mock_source_repo(self, mock_source):
        """Mock repository returning the test source."""
        repo = MagicMock()
        repo.get_by_id.return_value = mock_source
        return repo

    @pytest.fixture
    def mock_text_file_response(self):
        """Minimal file content dict returned by GitHubScanner."""
        return {
            "content": "# My Skill\n\nContent here.",
            "encoding": "none",
            "size": 512,
            "sha": "deadbeef1234",
            "name": "SKILL.md",
            "path": "skills/my-skill/SKILL.md",
            "is_binary": False,
        }

    @pytest.fixture
    def fresh_file_cache(self):
        """Fresh (empty) GitHubFileCache instance for each test."""
        from skillmeat.api.utils.github_cache import GitHubFileCache

        return GitHubFileCache(max_entries=50)

    # ------------------------------------------------------------------
    # Test 1 — Directory-based artifact (regression)
    # ------------------------------------------------------------------

    def test_directory_artifact_path_correct_resolution(
        self, client, mock_source_repo, mock_text_file_response, fresh_file_cache
    ):
        """Directory-based artifact_path is correctly concatenated with file_path.

        ``artifact_path = "skills/my-skill"`` + ``file_path = "SKILL.md"``
        must produce ``scanner.get_file_content(path="skills/my-skill/SKILL.md")``.
        """
        mock_scanner = MagicMock()
        mock_text_file_response["path"] = "skills/my-skill/SKILL.md"
        mock_text_file_response["name"] = "SKILL.md"
        mock_scanner.get_file_content.return_value = mock_text_file_response

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=fresh_file_cache,
        ):
            # Use a source ID with no underscores — validate_source_id only allows
            # alphanumeric characters and hyphens (^[a-zA-Z0-9\-]+$).
            response = client.get(
                "/api/v1/marketplace/sources/src-test-abc"
                "/artifacts/skills/my-skill/files/SKILL.md"
            )

        assert response.status_code == status.HTTP_200_OK

        # Verify the scanner received the concatenated path, not artifact_path alone
        mock_scanner.get_file_content.assert_called_once()
        call_kwargs = mock_scanner.get_file_content.call_args
        resolved_path = call_kwargs.kwargs.get("path") or call_kwargs.args[2]
        assert resolved_path == "skills/my-skill/SKILL.md", (
            f"Expected 'skills/my-skill/SKILL.md', got '{resolved_path}'"
        )

        data = response.json()
        assert data["artifact_path"] == "skills/my-skill"

    # ------------------------------------------------------------------
    # Test 2 — File-path artifact (defensive fallback, P2-T1)
    # ------------------------------------------------------------------

    def test_embedded_artifact_path_defensive_fallback(
        self, client, mock_source_repo, mock_text_file_response, fresh_file_cache
    ):
        """Embedded artifact with file-extension path must NOT 404.

        When ``artifact_path = "skills/my-skill/commands/foo.md"`` (ends with
        a recognised file extension), the endpoint must use ``artifact_path``
        as the resolved file path and IGNORE ``file_path``.  This prevents the
        double-path bug where the scanner would receive the non-existent path
        ``"skills/my-skill/commands/foo.md/foo.md"``.
        """
        mock_scanner = MagicMock()
        embedded_content = {
            "content": "# Foo Command\n\nDoes foo things.",
            "encoding": "none",
            "size": 256,
            "sha": "cafe1234abcd",
            "name": "foo.md",
            "path": "skills/my-skill/commands/foo.md",
            "is_binary": False,
        }
        mock_scanner.get_file_content.return_value = embedded_content

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.GitHubScanner",
            return_value=mock_scanner,
        ), patch(
            "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
            return_value=fresh_file_cache,
        ):
            # artifact_path ends with ".md" → defensive fallback must fire.
            # Use a source ID without underscores (validate_source_id rejects them).
            response = client.get(
                "/api/v1/marketplace/sources/src-test-abc"
                "/artifacts/skills/my-skill/commands/foo.md"
                "/files/foo.md"
            )

        assert response.status_code == status.HTTP_200_OK, (
            f"Expected 200 for embedded artifact path; got {response.status_code}: "
            f"{response.json()}"
        )

        # Verify the scanner received the artifact_path unchanged (no duplication)
        mock_scanner.get_file_content.assert_called_once()
        call_kwargs = mock_scanner.get_file_content.call_args
        resolved_path = call_kwargs.kwargs.get("path") or call_kwargs.args[2]
        assert resolved_path == "skills/my-skill/commands/foo.md", (
            f"Expected 'skills/my-skill/commands/foo.md' (no duplication), "
            f"got '{resolved_path}'"
        )

        data = response.json()
        assert data["artifact_path"] == "skills/my-skill/commands/foo.md"

    def test_embedded_artifact_path_various_extensions(
        self, client, mock_source_repo, fresh_file_cache
    ):
        """All recognised file extensions trigger the defensive fallback."""
        # Each tuple: (artifact_path_suffix, file_path, expected_resolved_path)
        cases = [
            ("agents/helper.md", "helper.md", "skills/s/agents/helper.md"),
            ("config/settings.yaml", "settings.yaml", "skills/s/config/settings.yaml"),
            ("config/settings.yml", "settings.yml", "skills/s/config/settings.yml"),
            ("config/pyproject.toml", "pyproject.toml", "skills/s/config/pyproject.toml"),
            ("scripts/run.sh", "run.sh", "skills/s/scripts/run.sh"),
            ("src/component.ts", "component.ts", "skills/s/src/component.ts"),
        ]

        for suffix, file_path_param, expected_path in cases:
            artifact_path_param = f"skills/s/{suffix}"
            content = {
                "content": "data",
                "encoding": "none",
                "size": 4,
                "sha": "abc",
                "name": file_path_param,
                "path": expected_path,
                "is_binary": False,
            }
            mock_scanner = MagicMock()
            mock_scanner.get_file_content.return_value = content

            with patch(
                "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
                return_value=mock_source_repo,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.GitHubScanner",
                return_value=mock_scanner,
            ), patch(
                "skillmeat.api.routers.marketplace_sources.get_github_file_cache",
                return_value=fresh_file_cache,
            ):
                response = client.get(
                    f"/api/v1/marketplace/sources/src-test-abc"
                    f"/artifacts/{artifact_path_param}"
                    f"/files/{file_path_param}"
                )

            assert response.status_code == status.HTTP_200_OK, (
                f"Expected 200 for artifact_path='{artifact_path_param}'; "
                f"got {response.status_code}"
            )
            call_kwargs = mock_scanner.get_file_content.call_args
            resolved = call_kwargs.kwargs.get("path") or call_kwargs.args[2]
            assert resolved == expected_path, (
                f"artifact_path='{artifact_path_param}': expected '{expected_path}', "
                f"got '{resolved}'"
            )
