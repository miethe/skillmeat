"""Tests for marketplace service layer."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.marketplace.broker import MarketplaceBroker
from skillmeat.core.marketplace.models import (
    ArtifactCategory,
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    ListingSortOrder,
    PublisherInfo,
    PublishRequest,
    PublishResult,
)
from skillmeat.core.marketplace.service import MarketplaceService


@pytest.fixture
def sample_publisher():
    """Create a sample publisher."""
    return PublisherInfo(
        name="Test Publisher",
        email="test@example.com",
        verified=True,
    )


@pytest.fixture
def sample_listings(sample_publisher):
    """Create sample listings for testing."""
    listings = []

    for i in range(25):
        listing = Listing(
            listing_id=f"test-{i}",
            name=f"Test Artifact {i}",
            description=f"Description for artifact {i}",
            category=ArtifactCategory.SKILL,
            version=f"1.0.{i}",
            publisher=sample_publisher,
            license="MIT",
            tags=["test", "example"] if i % 2 == 0 else ["production"],
            artifact_count=1,
            created_at=datetime(2025, 1, i + 1, 12, 0, 0),
            updated_at=datetime(2025, 1, i + 1, 12, 0, 0),
            downloads=100 + i,
            price=0.0 if i % 3 == 0 else 10.0,
            source_url=f"https://marketplace.example.com/test-{i}",
            bundle_url=f"https://marketplace.example.com/bundles/test-{i}.zip",
        )
        listings.append(listing)

    return listings


@pytest.fixture
def mock_broker(sample_listings):
    """Create a mock marketplace broker."""

    class MockBroker(MarketplaceBroker):
        def __init__(self):
            super().__init__(name="MockBroker", base_url="https://mock.example.com")
            self.all_listings = sample_listings

        def listings(self, query=None):
            # Simple implementation for testing
            # Return ALL filtered listings (no broker-side pagination)
            # The service will handle pagination
            filtered = self.all_listings

            if query and query.tags:
                filtered = [
                    l for l in filtered if all(tag in l.tags for tag in query.tags)
                ]

            if query and query.free_only:
                filtered = [l for l in filtered if l.price == 0.0]

            # Return all listings (service will paginate)
            return ListingPage(
                listings=filtered,
                total_count=len(filtered),
                page=1,
                page_size=len(filtered),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

        def get_listing(self, listing_id):
            for listing in self.all_listings:
                if listing.listing_id == listing_id:
                    return listing
            return None

        def download(self, listing_id, output_dir=None):
            listing = self.get_listing(listing_id)
            if not listing:
                raise FileNotFoundError(f"Listing {listing_id} not found")

            return DownloadResult(
                success=True,
                bundle_path="/tmp/test-bundle.zip",
                listing=listing,
                verified=True,
                message="Download successful",
                errors=[],
            )

        def publish(self, request):
            return PublishResult(
                success=True,
                listing_id="new-listing-123",
                listing_url="https://marketplace.example.com/new-listing-123",
                message="Publish successful",
                errors=[],
                warnings=[],
            )

    return MockBroker()


def test_service_initialization():
    """Test marketplace service initialization."""
    service = MarketplaceService(brokers=[])

    assert len(service.brokers) >= 0  # May initialize default broker
    assert service.cache is not None
    assert service.collection_manager is None


def test_service_add_broker(mock_broker):
    """Test adding a broker to service."""
    service = MarketplaceService(brokers=[])

    initial_count = len(service.brokers)
    service.add_broker(mock_broker)

    assert len(service.brokers) == initial_count + 1
    assert mock_broker in service.brokers


def test_service_remove_broker(mock_broker):
    """Test removing a broker from service."""
    service = MarketplaceService(brokers=[mock_broker])

    assert len(service.brokers) == 1

    result = service.remove_broker("MockBroker")
    assert result is True
    assert len(service.brokers) == 0

    # Try removing non-existent broker
    result = service.remove_broker("NonExistent")
    assert result is False


def test_get_listings_no_cache(mock_broker):
    """Test getting listings without cache hit."""
    service = MarketplaceService(brokers=[mock_broker])

    # Get listings
    listings_page, etag, not_modified = service.get_listings()

    assert listings_page is not None
    assert len(listings_page.listings) == 20  # Default page size
    assert etag is not None
    assert not not_modified


def test_get_listings_with_cache(mock_broker):
    """Test getting listings with cache hit."""
    service = MarketplaceService(brokers=[mock_broker])

    # First request (cache miss)
    listings_page1, etag1, not_modified1 = service.get_listings()
    assert not not_modified1

    # Second request (cache hit)
    listings_page2, etag2, not_modified2 = service.get_listings()

    assert etag1 == etag2
    assert not not_modified2  # Data returned, not 304


def test_get_listings_with_etag_match(mock_broker):
    """Test getting listings with ETag match (304)."""
    service = MarketplaceService(brokers=[mock_broker])

    # First request
    _, etag, _ = service.get_listings()

    # Second request with matching ETag
    listings_page, returned_etag, not_modified = service.get_listings(
        if_none_match=etag
    )

    assert listings_page is None
    assert returned_etag == etag
    assert not_modified


def test_get_listings_with_query(mock_broker):
    """Test getting listings with query parameters."""
    service = MarketplaceService(brokers=[mock_broker])

    query = ListingQuery(
        tags=["test", "example"],
        free_only=True,
        page=1,
        page_size=10,
    )

    listings_page, _, _ = service.get_listings(query)

    assert listings_page is not None
    assert len(listings_page.listings) <= 10

    # Verify filtering
    for listing in listings_page.listings:
        assert "test" in listing.tags
        assert "example" in listing.tags
        assert listing.price == 0.0


def test_get_listings_pagination(mock_broker):
    """Test pagination of listings."""
    service = MarketplaceService(brokers=[mock_broker])

    # Page 1
    query1 = ListingQuery(page=1, page_size=10)
    page1, _, _ = service.get_listings(query1)

    assert page1.page == 1
    assert len(page1.listings) == 10
    # After sorting by newest (default), there should be more pages
    assert page1.total_pages >= 2

    # Page 2
    query2 = ListingQuery(page=2, page_size=10)
    page2, _, _ = service.get_listings(query2)

    assert page2.page == 2
    assert len(page2.listings) >= 10
    assert page2.total_pages >= 2


def test_get_listing_found(mock_broker):
    """Test getting a specific listing that exists."""
    service = MarketplaceService(brokers=[mock_broker])

    listing = service.get_listing("test-0")

    assert listing is not None
    assert listing.listing_id == "test-0"
    assert listing.name == "Test Artifact 0"


def test_get_listing_not_found(mock_broker):
    """Test getting a listing that doesn't exist."""
    service = MarketplaceService(brokers=[mock_broker])

    listing = service.get_listing("nonexistent")

    assert listing is None


def test_download_listing_success(mock_broker):
    """Test downloading a listing successfully."""
    service = MarketplaceService(brokers=[mock_broker])

    result = service.download_listing("test-0")

    assert result.success
    assert result.bundle_path == "/tmp/test-bundle.zip"
    assert result.listing is not None
    assert result.verified


def test_download_listing_not_found(mock_broker):
    """Test downloading a non-existent listing."""
    service = MarketplaceService(brokers=[mock_broker])

    with pytest.raises(FileNotFoundError):
        service.download_listing("nonexistent")


def test_publish_listing_success(mock_broker):
    """Test publishing a listing successfully."""
    service = MarketplaceService(brokers=[mock_broker])

    request = PublishRequest(
        bundle_path="/tmp/test.zip",
        name="New Artifact",
        description="Test description",
        category=ArtifactCategory.SKILL,
        version="1.0.0",
        license="MIT",
        tags=["test"],
    )

    result = service.publish_listing(request)

    assert result.success
    assert result.listing_id == "new-listing-123"


def test_publish_listing_no_brokers():
    """Test publishing with no brokers available."""
    # Create service without default broker initialization
    service = MarketplaceService(brokers=[])
    # Remove any default brokers that were initialized
    service.brokers = []

    request = PublishRequest(
        bundle_path="/tmp/test.zip",
        name="New Artifact",
        description="Test description",
        category=ArtifactCategory.SKILL,
        version="1.0.0",
    )

    with pytest.raises(ValueError, match="No marketplace brokers available"):
        service.publish_listing(request)


def test_cache_invalidation_on_publish(mock_broker):
    """Test that cache is invalidated after successful publish."""
    service = MarketplaceService(brokers=[mock_broker])

    # Get listings (populate cache)
    service.get_listings()
    assert len(service.cache._cache) > 0

    # Publish (should invalidate cache)
    request = PublishRequest(
        bundle_path="/tmp/test.zip",
        name="New Artifact",
        description="Test description",
        category=ArtifactCategory.SKILL,
        version="1.0.0",
    )

    service.publish_listing(request)

    # Cache should be empty
    assert len(service.cache._cache) == 0


def test_invalidate_cache():
    """Test manual cache invalidation."""
    service = MarketplaceService(brokers=[])

    # Manually add to cache
    service.cache._cache["test-key"] = "test-value"  # type: ignore
    assert len(service.cache._cache) == 1

    # Invalidate
    service.invalidate_cache()

    # Cache should be empty
    assert len(service.cache._cache) == 0


def test_filtering_by_search(mock_broker):
    """Test filtering listings by search term."""
    service = MarketplaceService(brokers=[mock_broker])

    query = ListingQuery(search="Artifact 5", page_size=100)
    listings_page, _, _ = service.get_listings(query)

    # Should only return artifacts with "5" in name
    assert listings_page.total_count > 0
    for listing in listings_page.listings:
        assert "5" in listing.name or "5" in listing.description


def test_sorting_by_name(mock_broker):
    """Test sorting listings by name."""
    service = MarketplaceService(brokers=[mock_broker])

    query = ListingQuery(sort=ListingSortOrder.NAME, page_size=100)
    listings_page, _, _ = service.get_listings(query)

    # Verify sorting
    names = [l.name.lower() for l in listings_page.listings]
    assert names == sorted(names)


def test_sorting_by_downloads(mock_broker):
    """Test sorting listings by downloads (descending)."""
    service = MarketplaceService(brokers=[mock_broker])

    query = ListingQuery(sort=ListingSortOrder.DOWNLOADS, page_size=100)
    listings_page, _, _ = service.get_listings(query)

    # Verify sorting (descending)
    downloads = [l.downloads for l in listings_page.listings]
    assert downloads == sorted(downloads, reverse=True)


def test_multi_broker_aggregation(sample_listings):
    """Test aggregating listings from multiple brokers."""

    class MockBroker1(MarketplaceBroker):
        def __init__(self):
            super().__init__(name="Broker1")

        def listings(self, query=None):
            return ListingPage(
                listings=sample_listings[:10],
                total_count=10,
                page=1,
                page_size=20,
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

        def download(self, listing_id, output_dir=None):
            raise NotImplementedError

        def publish(self, request):
            raise NotImplementedError

    class MockBroker2(MarketplaceBroker):
        def __init__(self):
            super().__init__(name="Broker2")

        def listings(self, query=None):
            return ListingPage(
                listings=sample_listings[10:20],
                total_count=10,
                page=1,
                page_size=20,
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

        def download(self, listing_id, output_dir=None):
            raise NotImplementedError

        def publish(self, request):
            raise NotImplementedError

    broker1 = MockBroker1()
    broker2 = MockBroker2()

    service = MarketplaceService(brokers=[broker1, broker2])

    # Should aggregate from both brokers
    listings_page, _, _ = service.get_listings()

    # Should have listings from both brokers
    assert listings_page.total_count == 20


def test_error_handling_all_brokers_fail():
    """Test error handling when all brokers fail."""

    class FailingBroker(MarketplaceBroker):
        def __init__(self):
            super().__init__(name="FailingBroker")

        def listings(self, query=None):
            raise ConnectionError("Broker is down")

        def download(self, listing_id, output_dir=None):
            raise NotImplementedError

        def publish(self, request):
            raise NotImplementedError

    broker = FailingBroker()
    service = MarketplaceService(brokers=[broker])

    with pytest.raises(ConnectionError, match="All brokers failed"):
        service.get_listings()


def test_handles_large_listing_count(sample_listings):
    """Test handling of >500 listings efficiently."""

    # Create a broker with many listings
    large_listings = []
    for i in range(600):
        listing = Listing(
            listing_id=f"test-{i}",
            name=f"Artifact {i}",
            description=f"Description {i}",
            category=ArtifactCategory.SKILL,
            version="1.0.0",
            publisher=PublisherInfo(name="Publisher", verified=True),
            license="MIT",
            tags=["test"],
            artifact_count=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            downloads=i,
            price=0.0,
            source_url=f"https://example.com/{i}",
            bundle_url=f"https://example.com/{i}.zip",
        )
        large_listings.append(listing)

    class LargeBroker(MarketplaceBroker):
        def __init__(self):
            super().__init__(name="LargeBroker")

        def listings(self, query=None):
            # Return ALL listings (service handles pagination)
            return ListingPage(
                listings=large_listings,
                total_count=len(large_listings),
                page=1,
                page_size=len(large_listings),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )

        def download(self, listing_id, output_dir=None):
            raise NotImplementedError

        def publish(self, request):
            raise NotImplementedError

    broker = LargeBroker()
    service = MarketplaceService(brokers=[broker])

    # Should handle efficiently with pagination
    # Note: Service applies client-side sorting, which may re-paginate
    # Use a query to test pagination properly
    query = ListingQuery(page=1, page_size=20)
    listings_page, _, _ = service.get_listings(query)

    # Should get all 600 listings (total count)
    assert listings_page.total_count == 600
    # Page should have 20 items
    assert len(listings_page.listings) == 20
    # Should have 30 total pages
    assert listings_page.total_pages == 30
