"""Tests for marketplace data models."""

import pytest
from datetime import datetime

from skillmeat.marketplace.models import MarketplaceListing, PublishResult


class TestMarketplaceListing:
    """Tests for MarketplaceListing model."""

    def test_create_minimal_listing(self):
        """Test creating listing with minimal required fields."""
        listing = MarketplaceListing(
            listing_id="test-123",
            name="Test Bundle",
            publisher="Test Publisher",
            license="MIT",
            artifact_count=3,
            price=0,
            signature="test-signature",
            source_url="https://example.com/listing/123",
            bundle_url="https://example.com/bundles/123.zip",
        )

        assert listing.listing_id == "test-123"
        assert listing.name == "Test Bundle"
        assert listing.publisher == "Test Publisher"
        assert listing.license == "MIT"
        assert listing.artifact_count == 3
        assert listing.price == 0
        assert listing.is_free is True
        assert listing.is_signed is True

    def test_create_full_listing(self):
        """Test creating listing with all fields."""
        created_at = datetime.now()

        listing = MarketplaceListing(
            listing_id="test-456",
            name="Full Bundle",
            publisher="Full Publisher",
            license="Apache-2.0",
            artifact_count=5,
            price=999,
            signature="full-signature",
            source_url="https://example.com/listing/456",
            bundle_url="https://example.com/bundles/456.zip",
            tags=["python", "productivity"],
            created_at=created_at,
            description="A full test bundle",
            version="1.0.0",
            homepage="https://example.com",
            repository="https://github.com/test/repo",
            downloads=1000,
            rating=4.5,
        )

        assert listing.listing_id == "test-456"
        assert listing.tags == ["python", "productivity"]
        assert listing.created_at == created_at
        assert listing.description == "A full test bundle"
        assert listing.version == "1.0.0"
        assert listing.homepage == "https://example.com"
        assert listing.repository == "https://github.com/test/repo"
        assert listing.downloads == 1000
        assert listing.rating == 4.5
        assert listing.is_free is False

    def test_empty_listing_id_raises_error(self):
        """Test that empty listing_id raises ValueError."""
        with pytest.raises(ValueError, match="listing_id cannot be empty"):
            MarketplaceListing(
                listing_id="",
                name="Test",
                publisher="Test",
                license="MIT",
                artifact_count=1,
                price=0,
                signature="sig",
                source_url="url",
                bundle_url="url",
            )

    def test_empty_name_raises_error(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            MarketplaceListing(
                listing_id="test",
                name="",
                publisher="Test",
                license="MIT",
                artifact_count=1,
                price=0,
                signature="sig",
                source_url="url",
                bundle_url="url",
            )

    def test_negative_price_raises_error(self):
        """Test that negative price raises ValueError."""
        with pytest.raises(ValueError, match="price cannot be negative"):
            MarketplaceListing(
                listing_id="test",
                name="Test",
                publisher="Test",
                license="MIT",
                artifact_count=1,
                price=-100,
                signature="sig",
                source_url="url",
                bundle_url="url",
            )

    def test_invalid_rating_raises_error(self):
        """Test that invalid rating raises ValueError."""
        with pytest.raises(ValueError, match="rating must be between 0.0 and 5.0"):
            MarketplaceListing(
                listing_id="test",
                name="Test",
                publisher="Test",
                license="MIT",
                artifact_count=1,
                price=0,
                signature="sig",
                source_url="url",
                bundle_url="url",
                rating=6.0,
            )

    def test_to_dict(self):
        """Test converting listing to dictionary."""
        created_at = datetime(2025, 1, 15, 12, 0, 0)

        listing = MarketplaceListing(
            listing_id="test-123",
            name="Test Bundle",
            publisher="Test Publisher",
            license="MIT",
            artifact_count=3,
            price=0,
            signature="test-signature",
            source_url="https://example.com/listing/123",
            bundle_url="https://example.com/bundles/123.zip",
            tags=["test"],
            created_at=created_at,
            description="Test description",
        )

        data = listing.to_dict()

        assert data["listing_id"] == "test-123"
        assert data["name"] == "Test Bundle"
        assert data["publisher"] == "Test Publisher"
        assert data["license"] == "MIT"
        assert data["artifact_count"] == 3
        assert data["price"] == 0
        assert data["signature"] == "test-signature"
        assert data["tags"] == ["test"]
        assert data["created_at"] == created_at.isoformat()
        assert data["description"] == "Test description"

    def test_from_dict(self):
        """Test creating listing from dictionary."""
        data = {
            "listing_id": "test-123",
            "name": "Test Bundle",
            "publisher": "Test Publisher",
            "license": "MIT",
            "artifact_count": 3,
            "price": 0,
            "signature": "test-signature",
            "source_url": "https://example.com/listing/123",
            "bundle_url": "https://example.com/bundles/123.zip",
            "tags": ["test"],
            "created_at": "2025-01-15T12:00:00",
            "description": "Test description",
        }

        listing = MarketplaceListing.from_dict(data)

        assert listing.listing_id == "test-123"
        assert listing.name == "Test Bundle"
        assert listing.publisher == "Test Publisher"
        assert listing.tags == ["test"]
        assert listing.description == "Test description"


class TestPublishResult:
    """Tests for PublishResult model."""

    def test_create_pending_result(self):
        """Test creating pending publish result."""
        result = PublishResult(
            submission_id="sub-123",
            status="pending",
            message="Submission is pending review",
        )

        assert result.submission_id == "sub-123"
        assert result.status == "pending"
        assert result.is_pending is True
        assert result.is_approved is False
        assert result.is_rejected is False
        assert result.has_errors is False

    def test_create_approved_result(self):
        """Test creating approved publish result."""
        result = PublishResult(
            submission_id="sub-456",
            status="approved",
            message="Bundle approved",
            listing_url="https://marketplace.example.com/listing-789",
        )

        assert result.submission_id == "sub-456"
        assert result.status == "approved"
        assert result.is_pending is False
        assert result.is_approved is True
        assert result.is_rejected is False
        assert result.listing_url == "https://marketplace.example.com/listing-789"

    def test_create_rejected_result(self):
        """Test creating rejected publish result."""
        result = PublishResult(
            submission_id="sub-789",
            status="rejected",
            message="Bundle rejected",
            errors=["Invalid metadata", "Missing files"],
            warnings=["Large file size"],
        )

        assert result.submission_id == "sub-789"
        assert result.status == "rejected"
        assert result.is_pending is False
        assert result.is_approved is False
        assert result.is_rejected is True
        assert result.has_errors is True
        assert result.has_warnings is True
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_invalid_status_raises_error(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            PublishResult(
                submission_id="sub-123",
                status="invalid",
                message="Test",
            )

    def test_empty_submission_id_raises_error(self):
        """Test that empty submission_id raises ValueError."""
        with pytest.raises(ValueError, match="submission_id cannot be empty"):
            PublishResult(
                submission_id="",
                status="pending",
                message="Test",
            )

    def test_to_dict(self):
        """Test converting publish result to dictionary."""
        submitted_at = datetime(2025, 1, 15, 12, 0, 0)
        reviewed_at = datetime(2025, 1, 15, 14, 0, 0)

        result = PublishResult(
            submission_id="sub-123",
            status="approved",
            message="Approved",
            listing_url="https://example.com/listing",
            errors=[],
            warnings=["Warning 1"],
            submitted_at=submitted_at,
            reviewed_at=reviewed_at,
            reviewer_notes="Looks good",
        )

        data = result.to_dict()

        assert data["submission_id"] == "sub-123"
        assert data["status"] == "approved"
        assert data["message"] == "Approved"
        assert data["listing_url"] == "https://example.com/listing"
        assert data["warnings"] == ["Warning 1"]
        assert data["submitted_at"] == submitted_at.isoformat()
        assert data["reviewed_at"] == reviewed_at.isoformat()
        assert data["reviewer_notes"] == "Looks good"

    def test_from_dict(self):
        """Test creating publish result from dictionary."""
        data = {
            "submission_id": "sub-123",
            "status": "approved",
            "message": "Approved",
            "listing_url": "https://example.com/listing",
            "errors": [],
            "warnings": ["Warning 1"],
            "submitted_at": "2025-01-15T12:00:00",
            "reviewed_at": "2025-01-15T14:00:00",
            "reviewer_notes": "Looks good",
        }

        result = PublishResult.from_dict(data)

        assert result.submission_id == "sub-123"
        assert result.status == "approved"
        assert result.message == "Approved"
        assert result.listing_url == "https://example.com/listing"
        assert result.warnings == ["Warning 1"]
        assert result.reviewer_notes == "Looks good"
