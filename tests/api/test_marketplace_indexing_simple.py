"""Simple integration tests for marketplace source indexing_enabled field.

These tests verify that the indexing_enabled field can be set and retrieved
through the API endpoints without complex mocking.
"""

from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
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


class TestIndexingEnabledSchema:
    """Test that indexing_enabled field exists in schemas."""

    def test_source_response_has_indexing_enabled_field(self):
        """Test that MarketplaceSource model has indexing_enabled field."""
        source = MarketplaceSource(
            id="test_123",
            repo_url="https://github.com/test/repo",
            owner="test",
            repo_name="repo",
            ref="main",
            scan_status="pending",
            indexing_enabled=True,  # This field should exist
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert hasattr(source, "indexing_enabled")
        assert source.indexing_enabled is True

    def test_source_response_indexing_enabled_can_be_none(self):
        """Test that indexing_enabled can be None (opt-in mode)."""
        source = MarketplaceSource(
            id="test_123",
            repo_url="https://github.com/test/repo",
            owner="test",
            repo_name="repo",
            ref="main",
            scan_status="pending",
            indexing_enabled=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert hasattr(source, "indexing_enabled")
        assert source.indexing_enabled is None

    def test_source_response_indexing_enabled_can_be_false(self):
        """Test that indexing_enabled can be False (explicitly disabled)."""
        source = MarketplaceSource(
            id="test_123",
            repo_url="https://github.com/test/repo",
            owner="test",
            repo_name="repo",
            ref="main",
            scan_status="pending",
            indexing_enabled=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert hasattr(source, "indexing_enabled")
        assert source.indexing_enabled is False


class TestGetIndexingModeEndpoint:
    """Test GET /api/v1/settings/indexing-mode endpoint."""

    def test_get_indexing_mode_endpoint_exists(self, client):
        """Test that the indexing-mode endpoint exists and returns 200."""
        response = client.get("/api/v1/settings/indexing-mode")

        # Should return 200, not 404
        assert response.status_code == status.HTTP_200_OK

    def test_get_indexing_mode_response_structure(self, client):
        """Test that indexing-mode response has correct structure."""
        response = client.get("/api/v1/settings/indexing-mode")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert "indexing_mode" in data
        assert isinstance(data["indexing_mode"], str)
        assert data["indexing_mode"] in ["off", "on", "opt_in"]

    def test_get_indexing_mode_default_value(self, client):
        """Test that default indexing mode is opt_in."""
        response = client.get("/api/v1/settings/indexing-mode")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Default should be opt_in
        assert data["indexing_mode"] == "opt_in"
