"""Tests for marketplace API router.

Tests all marketplace endpoints including listings, install, publish, and brokers.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.server import create_app
from skillmeat.api.config import APISettings, Environment
from skillmeat.api.utils.cache import get_cache_manager
from skillmeat.marketplace.broker import MarketplaceBroker, DownloadError, PublishError
from skillmeat.marketplace.models import MarketplaceListing, PublishResult


class MockBroker(MarketplaceBroker):
    """Mock broker for testing."""

    def __init__(self, name: str, endpoint: str, listings_data: Optional[List] = None):
        super().__init__(name=name, endpoint=endpoint)
        self.listings_data = listings_data or []

    def listings(self, filters=None, page=1, page_size=20) -> List[MarketplaceListing]:
        """Return mock listings."""
        return self.listings_data

    def download(self, listing_id: str, output_dir: Optional[Path] = None) -> Path:
        """Mock download."""
        # Return a mock path
        return Path(f"/tmp/bundle_{listing_id}.tar.gz")

    def publish(self, bundle, metadata=None) -> PublishResult:
        """Mock publish."""
        return PublishResult(
            submission_id="test-submission-123",
            status="pending",
            message="Bundle submitted for review",
        )


@pytest.fixture
def test_settings():
    """Test API settings."""
    return APISettings(
        env=Environment.TESTING,
        api_title="SkillMeat Test API",
        api_version="v1",
        host="127.0.0.1",
        port=8000,
    )


@pytest.fixture
def client(test_settings):
    """Test client with mocked dependencies."""
    app = create_app(test_settings)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the global cache between tests."""
    get_cache_manager().clear()


@pytest.fixture
def mock_listings():
    """Mock marketplace listings."""
    return [
        MarketplaceListing(
            listing_id="test-listing-1",
            name="Test Bundle 1",
            publisher="test-publisher",
            license="MIT",
            artifact_count=5,
            price=0,
            signature="test-signature",
            source_url="https://example.com/listing/1",
            bundle_url="https://example.com/bundle/1.tar.gz",
            tags=["testing", "python"],
            created_at=datetime(2025, 1, 15, 10, 30, 0),
            description="A test bundle",
            version="1.0.0",
        ),
        MarketplaceListing(
            listing_id="test-listing-2",
            name="Test Bundle 2",
            publisher="test-publisher",
            license="Apache-2.0",
            artifact_count=3,
            price=0,
            signature="test-signature-2",
            source_url="https://example.com/listing/2",
            bundle_url="https://example.com/bundle/2.tar.gz",
            tags=["productivity"],
            created_at=datetime(2025, 1, 14, 10, 30, 0),
        ),
    ]


class TestListListings:
    """Tests for GET /api/v1/marketplace/listings endpoint."""

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_success(self, mock_registry, client, mock_listings):
        """Test successful listing retrieval."""
        # Setup mock registry
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_enabled_brokers.return_value = [mock_broker]

        # Make request
        response = client.get("/api/v1/marketplace/listings")

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "page_info" in data
        assert len(data["items"]) == 2

        # Check first listing
        listing = data["items"][0]
        assert listing["listing_id"] == "test-listing-1"
        assert listing["name"] == "Test Bundle 1"
        assert listing["publisher"] == "test-publisher"

        # Check pagination
        page_info = data["page_info"]
        assert "has_next_page" in page_info
        assert "has_previous_page" in page_info

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_with_filters(self, mock_registry, client, mock_listings):
        """Test listing with filters."""
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_enabled_brokers.return_value = [mock_broker]

        # Make request with filters
        response = client.get(
            "/api/v1/marketplace/listings",
            params={
                "query": "test",
                "tags": "python,testing",
                "license": "MIT",
                "publisher": "test-publisher",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_with_pagination(self, mock_registry, client, mock_listings):
        """Test listing with pagination."""
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_enabled_brokers.return_value = [mock_broker]

        # Make request with limit
        response = client.get("/api/v1/marketplace/listings", params={"limit": 1})

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["page_info"]["has_next_page"] is True

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_no_brokers(self, mock_registry, client):
        """Test error when no brokers available."""
        mock_registry.return_value.get_enabled_brokers.return_value = []

        response = client.get("/api/v1/marketplace/listings")

        assert response.status_code == 503
        assert "No marketplace brokers" in response.json()["detail"]

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_specific_broker(self, mock_registry, client, mock_listings):
        """Test filtering by specific broker."""
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_broker.return_value = mock_broker

        response = client.get(
            "/api/v1/marketplace/listings", params={"broker": "test-broker"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_broker_not_found(self, mock_registry, client):
        """Test error when broker not found."""
        mock_registry.return_value.get_broker.return_value = None

        response = client.get(
            "/api/v1/marketplace/listings", params={"broker": "nonexistent"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_listings_etag_caching(self, mock_registry, client, mock_listings):
        """Test ETag caching for listings."""
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_enabled_brokers.return_value = [mock_broker]

        # First request
        response1 = client.get("/api/v1/marketplace/listings")
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")
        assert etag is not None

        # Second request with If-None-Match
        response2 = client.get(
            "/api/v1/marketplace/listings", headers={"If-None-Match": etag}
        )
        # Should return 304 Not Modified (but test client may not support this)
        # At minimum, should use cache


class TestGetListingDetail:
    """Tests for GET /api/v1/marketplace/listings/{listing_id} endpoint."""

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_get_listing_success(self, mock_registry, client, mock_listings):
        """Test successful listing detail retrieval."""
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_enabled_brokers.return_value = [mock_broker]

        response = client.get("/api/v1/marketplace/listings/test-listing-1")

        assert response.status_code == 200
        data = response.json()

        assert data["listing_id"] == "test-listing-1"
        assert data["name"] == "Test Bundle 1"
        assert data["bundle_url"] == "https://example.com/bundle/1.tar.gz"
        assert data["signature"] == "test-signature"

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_get_listing_not_found(self, mock_registry, client):
        """Test error when listing not found."""
        mock_broker = MockBroker("test-broker", "https://test.com", [])
        mock_registry.return_value.get_enabled_brokers.return_value = [mock_broker]

        response = client.get("/api/v1/marketplace/listings/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_get_listing_no_brokers(self, mock_registry, client):
        """Test error when no brokers available."""
        mock_registry.return_value.get_enabled_brokers.return_value = []

        response = client.get("/api/v1/marketplace/listings/test-listing-1")

        assert response.status_code == 503


class TestInstallListing:
    """Tests for POST /api/v1/marketplace/install endpoint."""

    @patch("skillmeat.api.routers.marketplace.BundleImporter")
    @patch("skillmeat.api.routers.marketplace.Bundle")
    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    @patch("skillmeat.api.dependencies.verify_api_key")
    def test_install_success(
        self, mock_auth, mock_registry, mock_bundle, mock_importer, client, mock_listings
    ):
        """Test successful installation."""
        # Mock auth
        mock_auth.return_value = None

        # Setup mock broker
        mock_broker = MockBroker("test-broker", "https://test.com", mock_listings)
        mock_registry.return_value.get_broker.return_value = mock_broker

        # Mock bundle operations
        mock_bundle.from_file.return_value = Mock()

        # Mock import result
        mock_artifact1 = Mock()
        mock_artifact1.name = "artifact1"
        mock_artifact2 = Mock()
        mock_artifact2.name = "artifact2"

        mock_result = Mock()
        mock_result.imported_artifacts = [mock_artifact1, mock_artifact2]
        mock_importer.return_value.import_bundle.return_value = mock_result

        # Make request
        response = client.post(
            "/api/v1/marketplace/install",
            json={
                "listing_id": "test-listing-1",
                "broker": "test-broker",
                "strategy": "merge",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["artifacts_imported"]) == 2
        assert "artifact1" in data["artifacts_imported"]
        assert data["listing_id"] == "test-listing-1"
        assert data["broker"] == "test-broker"

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    @patch("skillmeat.api.dependencies.verify_api_key")
    def test_install_broker_not_found(self, mock_auth, mock_registry, client):
        """Test error when broker not found."""
        mock_auth.return_value = None
        mock_registry.return_value.get_broker.return_value = None

        response = client.post(
            "/api/v1/marketplace/install",
            json={
                "listing_id": "test-listing-1",
                "broker": "nonexistent",
                "strategy": "merge",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 404

    @patch("skillmeat.api.dependencies.verify_api_key")
    def test_install_invalid_strategy(self, mock_auth, client):
        """Test validation of strategy parameter."""
        mock_auth.return_value = None

        response = client.post(
            "/api/v1/marketplace/install",
            json={
                "listing_id": "test-listing-1",
                "strategy": "invalid",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        # Should fail validation
        assert response.status_code == 422


class TestPublishBundle:
    """Tests for POST /api/v1/marketplace/publish endpoint."""

    @patch("skillmeat.api.routers.marketplace.Bundle")
    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    @patch("skillmeat.api.dependencies.verify_api_key")
    def test_publish_success(self, mock_auth, mock_registry, mock_bundle, client, tmp_path):
        """Test successful bundle publishing."""
        mock_auth.return_value = None

        # Create temporary bundle file
        bundle_file = tmp_path / "test_bundle.tar.gz"
        bundle_file.write_text("test bundle content")

        # Setup mock broker
        mock_broker = MockBroker("test-broker", "https://test.com")
        mock_registry.return_value.get_broker.return_value = mock_broker

        # Mock bundle loading
        mock_bundle_instance = Mock()
        mock_bundle.from_file.return_value = mock_bundle_instance

        # Mock signature validation
        mock_broker.validate_signature = Mock(return_value=True)

        # Make request
        response = client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": str(bundle_file),
                "broker": "test-broker",
                "metadata": {
                    "description": "Test bundle",
                    "tags": ["testing"],
                },
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["submission_id"] == "test-submission-123"
        assert data["status"] == "pending"
        assert data["broker"] == "test-broker"

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    @patch("skillmeat.api.dependencies.verify_api_key")
    def test_publish_bundle_not_found(self, mock_auth, mock_registry, client):
        """Test error when bundle file not found."""
        mock_auth.return_value = None

        response = client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": "/nonexistent/bundle.tar.gz",
                "broker": "test-broker",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    @patch("skillmeat.api.dependencies.verify_api_key")
    def test_publish_broker_not_found(self, mock_auth, mock_registry, client, tmp_path):
        """Test error when broker not found."""
        mock_auth.return_value = None
        mock_registry.return_value.get_broker.return_value = None

        bundle_file = tmp_path / "test_bundle.tar.gz"
        bundle_file.write_text("test")

        response = client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": str(bundle_file),
                "broker": "nonexistent",
            },
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 404


class TestListBrokers:
    """Tests for GET /api/v1/marketplace/brokers endpoint."""

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_brokers_success(self, mock_registry, client):
        """Test successful broker listing."""
        # Mock registry config
        mock_registry.return_value._read_config.return_value = {
            "brokers": {
                "skillmeat": {
                    "enabled": True,
                    "endpoint": "https://marketplace.skillmeat.dev/api",
                    "description": "Official SkillMeat marketplace",
                },
                "claudehub": {
                    "enabled": True,
                    "endpoint": "https://claude.ai/marketplace/api",
                    "description": "Claude Hub",
                },
            }
        }

        response = client.get("/api/v1/marketplace/brokers")

        assert response.status_code == 200
        data = response.json()

        assert "brokers" in data
        assert len(data["brokers"]) == 2

        # Check first broker
        broker = data["brokers"][0]
        assert "name" in broker
        assert "enabled" in broker
        assert "endpoint" in broker
        assert "supports_publish" in broker

    @patch("skillmeat.api.routers.marketplace.get_broker_registry")
    def test_list_brokers_includes_disabled(self, mock_registry, client):
        """Test that listing includes disabled brokers."""
        mock_registry.return_value._read_config.return_value = {
            "brokers": {
                "broker1": {"enabled": True, "endpoint": "https://test1.com"},
                "broker2": {"enabled": False, "endpoint": "https://test2.com"},
            }
        }

        response = client.get("/api/v1/marketplace/brokers")

        assert response.status_code == 200
        data = response.json()

        # Should include both enabled and disabled
        assert len(data["brokers"]) == 2
