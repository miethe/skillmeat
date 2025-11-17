"""Tests for marketplace API routes."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.server import create_app
from skillmeat.core.marketplace.models import (
    ArtifactCategory,
    DownloadResult,
    Listing,
    ListingPage,
    PublisherInfo,
    PublishResult,
)


@pytest.fixture
def test_client():
    """Create test client with disabled authentication."""
    from skillmeat.api.config import APISettings

    # Create settings with auth disabled
    settings = APISettings(api_key_enabled=False)

    # Create app with test settings
    app = create_app(settings)

    return TestClient(app)


@pytest.fixture
def sample_listing():
    """Create a sample listing."""
    publisher = PublisherInfo(
        name="Test Publisher",
        email="test@example.com",
        verified=True,
    )

    return Listing(
        listing_id="test-123",
        name="Test Artifact",
        description="Test description",
        category=ArtifactCategory.SKILL,
        version="1.0.0",
        publisher=publisher,
        license="MIT",
        tags=["test", "example"],
        artifact_count=1,
        created_at=datetime(2025, 1, 1, 12, 0, 0),
        updated_at=datetime(2025, 1, 1, 12, 0, 0),
        downloads=100,
        price=0.0,
        source_url="https://marketplace.example.com/test-123",
        bundle_url="https://marketplace.example.com/bundles/test-123.zip",
    )


@pytest.fixture
def sample_listing_page(sample_listing):
    """Create a sample listing page."""
    return ListingPage(
        listings=[sample_listing],
        total_count=1,
        page=1,
        page_size=20,
        total_pages=1,
        has_next=False,
        has_prev=False,
    )


@pytest.fixture
def mock_marketplace_service(sample_listing, sample_listing_page):
    """Create a mock marketplace service."""
    service = Mock()

    # Mock get_listings
    service.get_listings.return_value = (
        sample_listing_page,
        "test-etag-123",
        False,
    )

    # Mock get_listing
    service.get_listing.return_value = sample_listing

    # Mock download_listing
    download_result = DownloadResult(
        success=True,
        bundle_path="/tmp/test-bundle.zip",
        listing=sample_listing,
        verified=True,
        message="Download successful",
        errors=[],
    )
    service.download_listing.return_value = download_result

    # Mock publish_listing
    publish_result = PublishResult(
        success=True,
        listing_id="new-123",
        listing_url="https://marketplace.example.com/new-123",
        message="Publish successful",
        errors=[],
        warnings=[],
    )
    service.publish_listing.return_value = publish_result

    return service


def test_list_listings_success(test_client, mock_marketplace_service):
    """Test listing marketplace listings successfully."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get("/api/v1/marketplace/listings")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "items" in data
        assert "page_info" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["listing_id"] == "test-123"

        # Check cache headers
        assert "ETag" in response.headers
        assert response.headers["ETag"] == "test-etag-123"
        assert "Cache-Control" in response.headers


def test_list_listings_with_pagination(test_client, mock_marketplace_service):
    """Test listing with pagination parameters."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get(
            "/api/v1/marketplace/listings?page=2&per_page=10"
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify service was called with correct params
        call_args = mock_marketplace_service.get_listings.call_args
        query = call_args[0][0]
        assert query.page == 2
        assert query.page_size == 10


def test_list_listings_with_filters(test_client, mock_marketplace_service):
    """Test listing with filter parameters."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get(
            "/api/v1/marketplace/listings?"
            "tags=python&tags=ml&"
            "artifact_type=skill&"
            "publisher=TestPublisher&"
            "free_only=true&"
            "verified_only=true&"
            "search=test&"
            "sort=popular"
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify service was called with correct params
        call_args = mock_marketplace_service.get_listings.call_args
        query = call_args[0][0]
        assert "python" in query.tags
        assert "ml" in query.tags
        assert query.category == ArtifactCategory.SKILL
        assert query.publisher == "TestPublisher"
        assert query.free_only is True
        assert query.verified_only is True
        assert query.search == "test"
        assert query.sort == "popular"


def test_list_listings_with_invalid_artifact_type(test_client, mock_marketplace_service):
    """Test listing with invalid artifact type."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get(
            "/api/v1/marketplace/listings?artifact_type=invalid"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid artifact type" in data["detail"]


def test_list_listings_with_invalid_sort(test_client, mock_marketplace_service):
    """Test listing with invalid sort parameter."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get("/api/v1/marketplace/listings?sort=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Invalid sort order" in data["detail"]


def test_list_listings_with_etag_match(test_client, mock_marketplace_service):
    """Test listing with ETag match (304 Not Modified)."""
    # Configure service to return not_modified=True
    mock_marketplace_service.get_listings.return_value = (
        None,
        "test-etag-123",
        True,
    )

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get(
            "/api/v1/marketplace/listings",
            headers={"If-None-Match": "test-etag-123"},
        )

        assert response.status_code == status.HTTP_304_NOT_MODIFIED
        assert "ETag" in response.headers


def test_get_listing_success(test_client, mock_marketplace_service):
    """Test getting a specific listing successfully."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get("/api/v1/marketplace/listings/test-123")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["listing_id"] == "test-123"
        assert data["name"] == "Test Artifact"
        assert "source_url" in data
        assert "bundle_url" in data


def test_get_listing_not_found(test_client, mock_marketplace_service):
    """Test getting a non-existent listing."""
    mock_marketplace_service.get_listing.return_value = None

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get("/api/v1/marketplace/listings/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()


def test_install_listing_success(test_client, mock_marketplace_service):
    """Test installing a marketplace listing successfully."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/install",
            json={
                "listing_id": "test-123",
                "verify_signature": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert data["listing_id"] == "test-123"


def test_install_listing_with_collection_name(test_client, mock_marketplace_service):
    """Test installing into a specific collection."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/install",
            json={
                "listing_id": "test-123",
                "collection_name": "my-collection",
                "verify_signature": False,
            },
        )

        assert response.status_code == status.HTTP_200_OK


def test_install_listing_download_failure(test_client, mock_marketplace_service):
    """Test install when download fails."""
    # Configure service to return failed download
    failed_result = DownloadResult(
        success=False,
        bundle_path=None,
        listing=None,
        verified=False,
        message="Download failed",
        errors=["Connection timeout"],
    )
    mock_marketplace_service.download_listing.return_value = failed_result

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/install",
            json={"listing_id": "test-123"},
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is False
        assert "Download failed" in data["message"]


def test_install_listing_not_found(test_client, mock_marketplace_service):
    """Test installing a non-existent listing."""
    mock_marketplace_service.download_listing.side_effect = FileNotFoundError(
        "Listing not found"
    )

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/install",
            json={"listing_id": "nonexistent"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_publish_bundle_success(test_client, mock_marketplace_service):
    """Test publishing a bundle successfully."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": "/tmp/test-bundle.zip",
                "name": "New Artifact",
                "description": "Test description",
                "category": "skill",
                "version": "1.0.0",
                "license": "MIT",
                "tags": ["test"],
                "sign_bundle": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["success"] is True
        assert data["listing_id"] == "new-123"


def test_publish_bundle_with_invalid_category(test_client, mock_marketplace_service):
    """Test publishing with invalid category."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": "/tmp/test.zip",
                "name": "New Artifact",
                "description": "Test",
                "category": "invalid",
                "version": "1.0.0",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_publish_bundle_not_found(test_client, mock_marketplace_service):
    """Test publishing a non-existent bundle."""
    mock_marketplace_service.publish_listing.side_effect = FileNotFoundError(
        "Bundle file not found"
    )

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": "/tmp/nonexistent.zip",
                "name": "New Artifact",
                "description": "Test",
                "category": "skill",
                "version": "1.0.0",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


def test_publish_bundle_permission_error(test_client, mock_marketplace_service):
    """Test publishing without proper credentials."""
    mock_marketplace_service.publish_listing.side_effect = PermissionError(
        "Publisher key required"
    )

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.post(
            "/api/v1/marketplace/publish",
            json={
                "bundle_path": "/tmp/test.zip",
                "name": "New Artifact",
                "description": "Test",
                "category": "skill",
                "version": "1.0.0",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_rate_limiting_headers(test_client, mock_marketplace_service):
    """Test that rate limiting headers are present."""
    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get("/api/v1/marketplace/listings")

        assert response.status_code == status.HTTP_200_OK

        # Rate limit headers should be present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


def test_error_handling_server_error(test_client, mock_marketplace_service):
    """Test error handling for server errors."""
    mock_marketplace_service.get_listings.side_effect = Exception("Internal error")

    with patch(
        "skillmeat.api.routers.marketplace.get_marketplace_service",
        return_value=mock_marketplace_service,
    ):
        response = test_client.get("/api/v1/marketplace/listings")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data


def test_openapi_schema_includes_marketplace(test_client):
    """Test that marketplace endpoints are included in OpenAPI schema."""
    response = test_client.get("/api/v1/openapi.json")

    assert response.status_code == status.HTTP_200_OK

    schema = response.json()
    assert "/api/v1/marketplace/listings" in schema["paths"]
    assert "/api/v1/marketplace/listings/{listing_id}" in schema["paths"]
    assert "/api/v1/marketplace/install" in schema["paths"]
    assert "/api/v1/marketplace/publish" in schema["paths"]
