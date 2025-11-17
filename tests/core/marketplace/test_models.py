"""Tests for marketplace models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from skillmeat.core.marketplace.models import (
    ArtifactCategory,
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    ListingSortOrder,
    PublishRequest,
    PublishResult,
    PublisherInfo,
)


class TestPublisherInfo:
    """Tests for PublisherInfo model."""

    def test_minimal_publisher(self):
        """Test creating publisher with minimal fields."""
        publisher = PublisherInfo(name="Test Publisher")

        assert publisher.name == "Test Publisher"
        assert publisher.email is None
        assert publisher.website is None
        assert publisher.verified is False
        assert publisher.key_fingerprint is None

    def test_full_publisher(self):
        """Test creating publisher with all fields."""
        publisher = PublisherInfo(
            name="Test Publisher",
            email="test@example.com",
            website="https://example.com",
            verified=True,
            key_fingerprint="abc123def456",
        )

        assert publisher.name == "Test Publisher"
        assert publisher.email == "test@example.com"
        assert str(publisher.website) == "https://example.com/"
        assert publisher.verified is True
        assert publisher.key_fingerprint == "abc123def456"


class TestListing:
    """Tests for Listing model."""

    def test_minimal_listing(self):
        """Test creating listing with required fields only."""
        publisher = PublisherInfo(name="Test Publisher")

        listing = Listing(
            listing_id="test-123",
            name="Test Artifact",
            description="A test artifact",
            category=ArtifactCategory.SKILL,
            version="1.0.0",
            publisher=publisher,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            source_url="https://example.com/listing",
            bundle_url="https://example.com/bundle.zip",
        )

        assert listing.listing_id == "test-123"
        assert listing.name == "Test Artifact"
        assert listing.category == ArtifactCategory.SKILL
        assert listing.license == "MIT"  # Default
        assert listing.price == 0.0  # Default
        assert listing.artifact_count == 1  # Default

    def test_full_listing(self):
        """Test creating listing with all fields."""
        publisher = PublisherInfo(name="Test Publisher", verified=True)

        listing = Listing(
            listing_id="test-123",
            name="Test Artifact",
            description="A test artifact",
            category=ArtifactCategory.COMMAND,
            version="2.1.0",
            publisher=publisher,
            license="Apache-2.0",
            tags=["automation", "productivity"],
            artifact_count=3,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            downloads=1000,
            price=9.99,
            signature="base64signature",
            source_url="https://example.com/listing",
            bundle_url="https://example.com/bundle.zip",
            homepage="https://example.com",
            repository="https://github.com/test/repo",
            metadata={"custom": "value"},
        )

        assert listing.listing_id == "test-123"
        assert listing.category == ArtifactCategory.COMMAND
        assert listing.license == "Apache-2.0"
        assert listing.tags == ["automation", "productivity"]
        assert listing.artifact_count == 3
        assert listing.downloads == 1000
        assert listing.price == 9.99
        assert listing.signature == "base64signature"
        assert listing.metadata == {"custom": "value"}

    def test_invalid_category(self):
        """Test that invalid category raises error."""
        publisher = PublisherInfo(name="Test Publisher")

        with pytest.raises(ValidationError):
            Listing(
                listing_id="test-123",
                name="Test",
                description="Test",
                category="invalid-category",
                version="1.0.0",
                publisher=publisher,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                source_url="https://example.com",
                bundle_url="https://example.com/bundle",
            )

    def test_category_enum(self):
        """Test all valid artifact categories."""
        publisher = PublisherInfo(name="Test")

        categories = [
            ArtifactCategory.SKILL,
            ArtifactCategory.COMMAND,
            ArtifactCategory.AGENT,
            ArtifactCategory.HOOK,
            ArtifactCategory.MCP_SERVER,
            ArtifactCategory.BUNDLE,
        ]

        for category in categories:
            listing = Listing(
                listing_id="test",
                name="Test",
                description="Test",
                category=category,
                version="1.0.0",
                publisher=publisher,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                source_url="https://example.com",
                bundle_url="https://example.com/bundle",
            )
            assert listing.category == category


class TestListingQuery:
    """Tests for ListingQuery model."""

    def test_default_query(self):
        """Test query with default values."""
        query = ListingQuery()

        assert query.search is None
        assert query.category is None
        assert query.tags == []
        assert query.publisher is None
        assert query.free_only is False
        assert query.verified_only is False
        assert query.sort == ListingSortOrder.NEWEST
        assert query.page == 1
        assert query.page_size == 20

    def test_custom_query(self):
        """Test query with custom values."""
        query = ListingQuery(
            search="automation",
            category=ArtifactCategory.SKILL,
            tags=["productivity", "tools"],
            publisher="Test Publisher",
            free_only=True,
            verified_only=True,
            sort=ListingSortOrder.POPULAR,
            page=2,
            page_size=50,
        )

        assert query.search == "automation"
        assert query.category == ArtifactCategory.SKILL
        assert query.tags == ["productivity", "tools"]
        assert query.publisher == "Test Publisher"
        assert query.free_only is True
        assert query.verified_only is True
        assert query.sort == ListingSortOrder.POPULAR
        assert query.page == 2
        assert query.page_size == 50

    def test_page_validation(self):
        """Test that page must be >= 1."""
        with pytest.raises(ValidationError):
            ListingQuery(page=0)

        with pytest.raises(ValidationError):
            ListingQuery(page=-1)

    def test_page_size_validation(self):
        """Test that page_size must be between 1 and 100."""
        with pytest.raises(ValidationError):
            ListingQuery(page_size=0)

        with pytest.raises(ValidationError):
            ListingQuery(page_size=101)

        # Valid values
        query1 = ListingQuery(page_size=1)
        assert query1.page_size == 1

        query2 = ListingQuery(page_size=100)
        assert query2.page_size == 100


class TestListingPage:
    """Tests for ListingPage model."""

    def test_empty_page(self):
        """Test empty listing page."""
        page = ListingPage(
            listings=[],
            total_count=0,
            page=1,
            page_size=20,
            total_pages=0,
            has_next=False,
            has_prev=False,
        )

        assert page.listings == []
        assert page.total_count == 0
        assert page.total_pages == 0
        assert page.has_next is False
        assert page.has_prev is False

    def test_page_with_listings(self):
        """Test page with listings."""
        publisher = PublisherInfo(name="Test")
        listings = [
            Listing(
                listing_id=f"test-{i}",
                name=f"Test {i}",
                description="Test",
                category=ArtifactCategory.SKILL,
                version="1.0.0",
                publisher=publisher,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                source_url="https://example.com",
                bundle_url="https://example.com/bundle",
            )
            for i in range(20)
        ]

        page = ListingPage(
            listings=listings,
            total_count=100,
            page=2,
            page_size=20,
            total_pages=5,
            has_next=True,
            has_prev=True,
        )

        assert len(page.listings) == 20
        assert page.total_count == 100
        assert page.page == 2
        assert page.total_pages == 5
        assert page.has_next is True
        assert page.has_prev is True


class TestPublishRequest:
    """Tests for PublishRequest model."""

    def test_minimal_request(self):
        """Test publish request with minimal fields."""
        request = PublishRequest(
            bundle_path="/path/to/bundle.pack",
            name="Test Bundle",
            description="A test bundle",
            category=ArtifactCategory.SKILL,
            version="1.0.0",
        )

        assert request.bundle_path == "/path/to/bundle.pack"
        assert request.name == "Test Bundle"
        assert request.license == "MIT"  # Default
        assert request.price == 0.0  # Default
        assert request.sign_bundle is True  # Default

    def test_full_request(self):
        """Test publish request with all fields."""
        request = PublishRequest(
            bundle_path="/path/to/bundle.pack",
            name="Test Bundle",
            description="A test bundle",
            category=ArtifactCategory.BUNDLE,
            version="2.0.0",
            license="Apache-2.0",
            tags=["tools", "productivity"],
            homepage="https://example.com",
            repository="https://github.com/test/repo",
            price=19.99,
            sign_bundle=False,
            publisher_key_id="key-123",
        )

        assert request.license == "Apache-2.0"
        assert request.tags == ["tools", "productivity"]
        assert str(request.homepage) == "https://example.com/"
        assert request.price == 19.99
        assert request.sign_bundle is False
        assert request.publisher_key_id == "key-123"

    def test_price_validation(self):
        """Test that price must be >= 0."""
        with pytest.raises(ValidationError):
            PublishRequest(
                bundle_path="/path/to/bundle.pack",
                name="Test",
                description="Test",
                category=ArtifactCategory.SKILL,
                version="1.0.0",
                price=-1.0,
            )


class TestPublishResult:
    """Tests for PublishResult model."""

    def test_success_result(self):
        """Test successful publish result."""
        result = PublishResult(
            success=True,
            listing_id="test-123",
            listing_url="https://example.com/listing/test-123",
            message="Successfully published",
            errors=[],
            warnings=["Warning: Large bundle size"],
        )

        assert result.success is True
        assert result.listing_id == "test-123"
        assert result.errors == []
        assert len(result.warnings) == 1

    def test_failure_result(self):
        """Test failed publish result."""
        result = PublishResult(
            success=False,
            listing_id=None,
            listing_url=None,
            message="Publish failed",
            errors=["Invalid bundle", "Missing signature"],
            warnings=[],
        )

        assert result.success is False
        assert result.listing_id is None
        assert len(result.errors) == 2


class TestDownloadResult:
    """Tests for DownloadResult model."""

    def test_success_download(self):
        """Test successful download result."""
        publisher = PublisherInfo(name="Test")
        listing = Listing(
            listing_id="test-123",
            name="Test",
            description="Test",
            category=ArtifactCategory.SKILL,
            version="1.0.0",
            publisher=publisher,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            source_url="https://example.com",
            bundle_url="https://example.com/bundle",
        )

        result = DownloadResult(
            success=True,
            bundle_path="/tmp/test-bundle.pack",
            listing=listing,
            verified=True,
            message="Download successful",
            errors=[],
        )

        assert result.success is True
        assert result.bundle_path == "/tmp/test-bundle.pack"
        assert result.verified is True
        assert result.errors == []

    def test_failed_download(self):
        """Test failed download result."""
        result = DownloadResult(
            success=False,
            bundle_path=None,
            listing=None,
            verified=False,
            message="Download failed",
            errors=["Network timeout", "Connection refused"],
        )

        assert result.success is False
        assert result.bundle_path is None
        assert result.listing is None
        assert len(result.errors) == 2
