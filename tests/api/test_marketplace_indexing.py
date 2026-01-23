"""Integration tests for marketplace source indexing functionality.

Tests for:
- POST /marketplace/sources with indexing_enabled field
- PATCH /marketplace/sources/{id} with indexing_enabled updates
- GET /api/v1/settings/indexing-mode endpoint
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.schemas.marketplace import ScanResultDTO
from skillmeat.api.server import create_app
from skillmeat.cache.models import MarketplaceSource


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
        repo_url="https://github.com/test/repo",
        owner="test",
        repo_name="repo",
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
        indexing_enabled=None,  # Default NULL
    )


@pytest.fixture
def mock_source_repo(mock_source):
    """Create mock MarketplaceSourceRepository."""
    mock = MagicMock()
    mock.get_by_id.return_value = mock_source
    mock.get_by_repo_url.return_value = None  # No existing source by default
    mock.create.return_value = mock_source
    mock.update.return_value = mock_source
    return mock


@pytest.fixture
def mock_config_manager():
    """Create mock ConfigManager for settings tests."""
    mock = MagicMock()
    mock.get_indexing_mode.return_value = "opt_in"  # Default
    return mock


# =============================================================================
# Test Create Source with indexing_enabled
# =============================================================================


class TestCreateSourceIndexing:
    """Test POST /marketplace/sources with indexing_enabled field."""

    def test_create_source_with_indexing_enabled_true(
        self, client, mock_source_repo, mock_source
    ):
        """Test creating source with indexing_enabled=true."""
        # Update mock source with indexing enabled
        mock_source.indexing_enabled = True
        mock_source_repo.create.return_value = mock_source

        # Mock the scan function
        async def mock_perform_scan(*args, **kwargs):
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=5,
                new_count=5,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=100.0,
                errors=[],
                scanned_at=datetime.now(),
            )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources._perform_scan",
            side_effect=mock_perform_scan,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "ref": "main",
                    "indexing_enabled": True,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["indexing_enabled"] is True

    def test_create_source_with_indexing_enabled_false(
        self, client, mock_source_repo, mock_source
    ):
        """Test creating source with indexing_enabled=false."""
        # Update mock source with indexing disabled
        mock_source.indexing_enabled = False
        mock_source_repo.create.return_value = mock_source

        # Mock the scan function
        async def mock_perform_scan(*args, **kwargs):
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=5,
                new_count=5,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=100.0,
                errors=[],
                scanned_at=datetime.now(),
            )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources._perform_scan",
            side_effect=mock_perform_scan,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "ref": "main",
                    "indexing_enabled": False,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["indexing_enabled"] is False

    def test_create_source_with_indexing_enabled_null(
        self, client, mock_source_repo, mock_source
    ):
        """Test creating source without specifying indexing_enabled (NULL)."""
        # Mock source has indexing_enabled=None by default
        assert mock_source.indexing_enabled is None

        # Mock the scan function
        async def mock_perform_scan(*args, **kwargs):
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=5,
                new_count=5,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=100.0,
                errors=[],
                scanned_at=datetime.now(),
            )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources._perform_scan",
            side_effect=mock_perform_scan,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "ref": "main",
                    # indexing_enabled not specified
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # When not specified, should be None/null in response
        assert data["indexing_enabled"] is None

    def test_create_source_with_indexing_enabled_explicit_null(
        self, client, mock_source_repo, mock_source
    ):
        """Test creating source with indexing_enabled explicitly set to null."""
        # Mock source has indexing_enabled=None
        mock_source.indexing_enabled = None

        # Mock the scan function
        async def mock_perform_scan(*args, **kwargs):
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=5,
                new_count=5,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=100.0,
                errors=[],
                scanned_at=datetime.now(),
            )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources._perform_scan",
            side_effect=mock_perform_scan,
        ):
            response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "ref": "main",
                    "indexing_enabled": None,
                },
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["indexing_enabled"] is None


# =============================================================================
# Test Update Source indexing_enabled
# =============================================================================


class TestUpdateSourceIndexing:
    """Test PATCH /marketplace/sources/{id} with indexing_enabled updates."""

    def test_update_source_indexing_enabled_to_true(
        self, client, mock_source_repo, mock_source
    ):
        """Test updating source indexing_enabled from None to True."""
        # Original source has indexing_enabled=None
        assert mock_source.indexing_enabled is None

        # Updated source has indexing_enabled=True
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref=mock_source.ref,
            root_hint=mock_source.root_hint,
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=datetime.now(),
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
            indexing_enabled=True,  # Updated value
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"indexing_enabled": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["indexing_enabled"] is True

    def test_update_source_indexing_enabled_to_false(
        self, client, mock_source_repo, mock_source
    ):
        """Test updating source indexing_enabled from True to False."""
        # Original source has indexing_enabled=True
        mock_source.indexing_enabled = True

        # Updated source has indexing_enabled=False
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref=mock_source.ref,
            root_hint=mock_source.root_hint,
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=datetime.now(),
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
            indexing_enabled=False,  # Updated value
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"indexing_enabled": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["indexing_enabled"] is False

    def test_update_source_indexing_enabled_to_null(
        self, client, mock_source_repo, mock_source
    ):
        """Test updating source indexing_enabled from True to None."""
        # Original source has indexing_enabled=True
        mock_source.indexing_enabled = True

        # Updated source has indexing_enabled=None (reverts to global setting)
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref=mock_source.ref,
            root_hint=mock_source.root_hint,
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=datetime.now(),
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
            indexing_enabled=None,  # Updated value
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"indexing_enabled": None},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["indexing_enabled"] is None


# =============================================================================
# Test GET /api/v1/settings/indexing-mode endpoint
# =============================================================================


class TestGetIndexingMode:
    """Test GET /api/v1/settings/indexing-mode endpoint."""

    def test_get_indexing_mode_default(self, app, client, mock_config_manager):
        """Test getting default indexing mode (opt_in)."""
        from skillmeat.api.dependencies import get_config_manager

        mock_config_manager.get_indexing_mode.return_value = "opt_in"
        app.dependency_overrides[get_config_manager] = lambda: mock_config_manager

        response = client.get("/api/v1/settings/indexing-mode")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["indexing_mode"] == "opt_in"

        # Clean up
        app.dependency_overrides.clear()

    def test_get_indexing_mode_off(self, app, client, mock_config_manager):
        """Test getting indexing mode when set to 'off'."""
        from skillmeat.api.dependencies import get_config_manager

        mock_config_manager.get_indexing_mode.return_value = "off"
        app.dependency_overrides[get_config_manager] = lambda: mock_config_manager

        response = client.get("/api/v1/settings/indexing-mode")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["indexing_mode"] == "off"

        # Clean up
        app.dependency_overrides.clear()

    def test_get_indexing_mode_on(self, app, client, mock_config_manager):
        """Test getting indexing mode when set to 'on'."""
        from skillmeat.api.dependencies import get_config_manager

        mock_config_manager.get_indexing_mode.return_value = "on"
        app.dependency_overrides[get_config_manager] = lambda: mock_config_manager

        response = client.get("/api/v1/settings/indexing-mode")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["indexing_mode"] == "on"

        # Clean up
        app.dependency_overrides.clear()

    def test_get_indexing_mode_response_structure(self, app, client, mock_config_manager):
        """Test that indexing mode response has correct structure."""
        from skillmeat.api.dependencies import get_config_manager

        mock_config_manager.get_indexing_mode.return_value = "opt_in"
        app.dependency_overrides[get_config_manager] = lambda: mock_config_manager

        response = client.get("/api/v1/settings/indexing-mode")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "indexing_mode" in data
        assert isinstance(data["indexing_mode"], str)
        assert data["indexing_mode"] in ["off", "on", "opt_in"]

        # Clean up
        app.dependency_overrides.clear()


# =============================================================================
# Integration Tests: Combined Scenarios
# =============================================================================


class TestIndexingIntegration:
    """Test combined indexing scenarios."""

    def test_create_then_update_indexing_enabled(
        self, client, mock_source_repo, mock_source
    ):
        """Test creating source with indexing, then updating it."""
        # Step 1: Create source with indexing_enabled=True
        mock_source.indexing_enabled = True
        mock_source_repo.create.return_value = mock_source

        # Mock the scan function
        async def mock_perform_scan(*args, **kwargs):
            return ScanResultDTO(
                source_id="src_test_123",
                status="success",
                artifacts_found=5,
                new_count=5,
                updated_count=0,
                removed_count=0,
                unchanged_count=0,
                scan_duration_ms=100.0,
                errors=[],
                scanned_at=datetime.now(),
            )

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ), patch(
            "skillmeat.api.routers.marketplace_sources._perform_scan",
            side_effect=mock_perform_scan,
        ):
            create_response = client.post(
                "/api/v1/marketplace/sources",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "ref": "main",
                    "indexing_enabled": True,
                },
            )

        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.json()["indexing_enabled"] is True

        # Step 2: Update indexing_enabled to False
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref=mock_source.ref,
            root_hint=mock_source.root_hint,
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=datetime.now(),
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
            indexing_enabled=False,
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            update_response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"indexing_enabled": False},
            )

        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["indexing_enabled"] is False

    def test_null_indexing_persists_across_updates(
        self, client, mock_source_repo, mock_source
    ):
        """Test that NULL indexing_enabled persists when updating other fields."""
        # Source has indexing_enabled=None
        assert mock_source.indexing_enabled is None

        # Update ref, but keep indexing_enabled=None
        updated_source = MarketplaceSource(
            id=mock_source.id,
            repo_url=mock_source.repo_url,
            owner=mock_source.owner,
            repo_name=mock_source.repo_name,
            ref="develop",  # Changed
            root_hint=mock_source.root_hint,
            trust_level=mock_source.trust_level,
            visibility=mock_source.visibility,
            scan_status=mock_source.scan_status,
            artifact_count=mock_source.artifact_count,
            last_sync_at=mock_source.last_sync_at,
            created_at=mock_source.created_at,
            updated_at=datetime.now(),
            enable_frontmatter_detection=mock_source.enable_frontmatter_detection,
            indexing_enabled=None,  # Should remain None
        )
        mock_source_repo.update.return_value = updated_source

        with patch(
            "skillmeat.api.routers.marketplace_sources.MarketplaceSourceRepository",
            return_value=mock_source_repo,
        ):
            response = client.patch(
                "/api/v1/marketplace/sources/src_test_123",
                json={"ref": "develop"},  # Only update ref
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ref"] == "develop"
        assert data["indexing_enabled"] is None  # Should still be None
