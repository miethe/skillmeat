"""Tests for marketplace broker implementations."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.sharing.bundle import Bundle, BundleArtifact, BundleMetadata
from skillmeat.marketplace.broker import (
    DownloadError,
    MarketplaceBrokerError,
    PublishError,
)
from skillmeat.marketplace.brokers import (
    ClaudeHubBroker,
    CustomWebBroker,
    SkillMeatMarketplaceBroker,
)
from skillmeat.marketplace.models import MarketplaceListing


class TestSkillMeatMarketplaceBroker:
    """Tests for SkillMeatMarketplaceBroker."""

    def test_initialization(self):
        """Test broker initialization."""
        broker = SkillMeatMarketplaceBroker()

        assert broker.name == "skillmeat"
        assert "marketplace.skillmeat.dev" in broker.endpoint

    @patch("skillmeat.marketplace.brokers.skillmeat_broker.MarketplaceBroker._make_request")
    def test_listings_success(self, mock_request):
        """Test successful listings fetch."""
        broker = SkillMeatMarketplaceBroker()

        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "listings": [
                {
                    "listing_id": "sm-123",
                    "name": "Test Bundle",
                    "publisher": "Test Publisher",
                    "license": "MIT",
                    "artifact_count": 3,
                    "price": 0,
                    "signature": "test-sig",
                    "source_url": "https://example.com/listing",
                    "bundle_url": "https://example.com/bundle.zip",
                    "tags": ["python"],
                }
            ],
            "total_pages": 1,
        }
        mock_request.return_value = mock_response

        listings = broker.listings(page=1, page_size=20)

        assert len(listings) == 1
        assert listings[0].listing_id == "sm-123"
        assert listings[0].name == "Test Bundle"

    @patch("skillmeat.marketplace.brokers.skillmeat_broker.MarketplaceBroker._make_request")
    def test_listings_with_filters(self, mock_request):
        """Test listings fetch with filters."""
        broker = SkillMeatMarketplaceBroker()

        mock_response = Mock()
        mock_response.json.return_value = {
            "listings": [],
            "total_pages": 0,
        }
        mock_request.return_value = mock_response

        filters = {
            "tags": ["python", "productivity"],
            "license": "MIT",
            "price_max": 1000,
        }

        listings = broker.listings(filters=filters, page=1, page_size=10)

        # Check that request was made with correct params
        call_args = mock_request.call_args
        assert call_args[1]["params"]["tags"] == "python,productivity"
        assert call_args[1]["params"]["license"] == "MIT"
        assert call_args[1]["params"]["price_max"] == 1000

    def test_listings_invalid_page(self):
        """Test that invalid page raises error."""
        broker = SkillMeatMarketplaceBroker()

        with pytest.raises(MarketplaceBrokerError, match="Invalid page number"):
            broker.listings(page=0)

    def test_listings_invalid_page_size(self):
        """Test that invalid page_size raises error."""
        broker = SkillMeatMarketplaceBroker()

        with pytest.raises(MarketplaceBrokerError, match="Invalid page_size"):
            broker.listings(page_size=101)

    def test_download_empty_listing_id(self):
        """Test that empty listing_id raises error."""
        broker = SkillMeatMarketplaceBroker()

        with pytest.raises(DownloadError, match="listing_id cannot be empty"):
            broker.download("")

    @patch("skillmeat.marketplace.brokers.skillmeat_broker.inspect_bundle")
    @patch("skillmeat.marketplace.brokers.skillmeat_broker.MarketplaceBroker._make_request")
    def test_download_success(self, mock_request, mock_inspect, tmp_path):
        """Test successful bundle download."""
        broker = SkillMeatMarketplaceBroker()

        # Mock listing fetch
        listing_response = Mock()
        listing_response.json.return_value = {
            "listing_id": "sm-123",
            "name": "Test Bundle",
            "publisher": "Test",
            "license": "MIT",
            "artifact_count": 1,
            "price": 0,
            "signature": "",  # No signature
            "source_url": "https://example.com/listing",
            "bundle_url": "https://example.com/bundle.zip",
        }

        # Mock bundle download
        bundle_response = Mock()
        bundle_response.iter_content = lambda chunk_size: [b"test content"]

        mock_request.side_effect = [listing_response, bundle_response]

        bundle_path = broker.download("sm-123", output_dir=tmp_path)

        assert bundle_path.exists()
        assert bundle_path.parent == tmp_path

    def test_publish_no_bundle_path(self):
        """Test that publishing without bundle_path raises error."""
        broker = SkillMeatMarketplaceBroker()

        bundle = Bundle(
            metadata=BundleMetadata(
                name="test",
                description="test",
                author="test",
                created_at="2025-01-15T12:00:00",
            ),
            bundle_hash="sha256:test",
        )

        with pytest.raises(PublishError, match="Bundle must have bundle_path set"):
            broker.publish(bundle)


class TestClaudeHubBroker:
    """Tests for ClaudeHubBroker."""

    def test_initialization(self):
        """Test broker initialization."""
        broker = ClaudeHubBroker()

        assert broker.name == "claudehub"
        assert "claude.ai" in broker.endpoint

    @patch("skillmeat.marketplace.brokers.claudehub_broker.MarketplaceBroker._make_request")
    def test_listings_success(self, mock_request):
        """Test successful listings fetch."""
        broker = ClaudeHubBroker()

        # Mock response in Claude Hub format
        mock_response = Mock()
        mock_response.json.return_value = {
            "artifacts": [
                {
                    "id": "ch-123",
                    "name": "Claude Artifact",
                    "author": "Claude",
                    "license": "Apache-2.0",
                    "url": "https://claude.ai/artifact/123",
                    "download_url": "https://claude.ai/download/123",
                    "tags": ["ai"],
                    "description": "A Claude artifact",
                }
            ],
            "total_pages": 1,
        }
        mock_request.return_value = mock_response

        listings = broker.listings()

        assert len(listings) == 1
        assert listings[0].listing_id == "claudehub-ch-123"
        assert listings[0].name == "Claude Artifact"
        assert listings[0].publisher == "Claude"

    def test_publish_not_supported(self):
        """Test that publishing raises error."""
        broker = ClaudeHubBroker()

        bundle = Bundle(
            metadata=BundleMetadata(
                name="test",
                description="test",
                author="test",
                created_at="2025-01-15T12:00:00",
            ),
        )

        with pytest.raises(PublishError, match="Publishing to Claude Hub is not supported"):
            broker.publish(bundle)

    def test_download_invalid_listing_id(self):
        """Test that invalid listing_id raises error."""
        broker = ClaudeHubBroker()

        with pytest.raises(DownloadError, match="Invalid Claude Hub listing_id"):
            broker.download("invalid-id")


class TestCustomWebBroker:
    """Tests for CustomWebBroker."""

    def test_initialization_without_schema(self):
        """Test broker initialization without schema URL."""
        broker = CustomWebBroker(
            name="custom",
            endpoint="https://custom.example.com/api",
        )

        assert broker.name == "custom"
        assert broker.endpoint == "https://custom.example.com/api"
        assert broker.schema_url is None

    def test_initialization_with_schema(self):
        """Test broker initialization with schema URL."""
        with patch.object(CustomWebBroker, "_load_schema"):
            broker = CustomWebBroker(
                name="custom",
                endpoint="https://custom.example.com/api",
                schema_url="https://custom.example.com/schema.json",
            )

            assert broker.schema_url == "https://custom.example.com/schema.json"

    @patch("skillmeat.marketplace.brokers.custom_broker.MarketplaceBroker._make_request")
    def test_load_schema_success(self, mock_request):
        """Test successful schema loading."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "listings": {"type": "array"},
            },
        }
        mock_request.return_value = mock_response

        broker = CustomWebBroker(
            name="custom",
            endpoint="https://custom.example.com/api",
            schema_url="https://custom.example.com/schema.json",
        )

        assert broker._listing_schema is not None
        assert "$schema" in broker._listing_schema

    @patch("skillmeat.marketplace.brokers.custom_broker.MarketplaceBroker._make_request")
    def test_listings_with_validation(self, mock_request):
        """Test listings fetch with schema validation."""
        broker = CustomWebBroker(
            name="custom",
            endpoint="https://custom.example.com/api",
        )

        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "listings": [
                {
                    "listing_id": "custom-123",
                    "name": "Custom Bundle",
                    "publisher": "Custom Publisher",
                    "license": "MIT",
                    "artifact_count": 2,
                    "price": 0,
                    "signature": "custom-sig",
                    "source_url": "https://custom.example.com/listing",
                    "bundle_url": "https://custom.example.com/bundle.zip",
                }
            ],
        }
        mock_request.return_value = mock_response

        listings = broker.listings()

        assert len(listings) == 1
        assert listings[0].listing_id == "custom-123"

    def test_publish_metadata_override(self, tmp_path):
        """Test that metadata can be overridden during publish."""
        broker = CustomWebBroker(
            name="custom",
            endpoint="https://custom.example.com/api",
        )

        # Create test bundle file
        bundle_file = tmp_path / "test.zip"
        bundle_file.write_bytes(b"test")

        bundle = Bundle(
            metadata=BundleMetadata(
                name="test",
                description="original description",
                author="test author",
                created_at="2025-01-15T12:00:00",
            ),
            bundle_hash="sha256:test",
            bundle_path=bundle_file,
        )

        # Mock the signing and request
        with patch("skillmeat.marketplace.brokers.custom_broker.BundleSigner"):
            with patch.object(broker, "_make_request") as mock_request:
                mock_response = Mock()
                mock_response.json.return_value = {
                    "submission_id": "custom-sub-123",
                    "status": "pending",
                    "message": "Submitted",
                }
                mock_request.return_value = mock_response

                metadata = {
                    "custom_field": "custom_value",
                }

                result = broker.publish(bundle, metadata=metadata)

                # Check that custom metadata was included
                call_args = mock_request.call_args
                upload_data = call_args[1]["data"]
                assert "custom_field" in upload_data
                assert upload_data["custom_field"] == "custom_value"
