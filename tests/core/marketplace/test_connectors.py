"""Tests for marketplace broker connectors."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest
import requests
from requests.exceptions import RequestException

from skillmeat.core.marketplace.brokers.claudehub import ClaudeHubBroker
from skillmeat.core.marketplace.brokers.custom import CustomWebBroker
from skillmeat.core.marketplace.brokers.skillmeat import SkillMeatMarketplaceBroker
from skillmeat.core.marketplace.models import (
    ArtifactCategory,
    ListingQuery,
    PublishRequest,
    PublisherInfo,
)

# Check if cryptography dependencies are available
# NOTE: This will be False in environments without cffi/cryptography
# These tests will be skipped in such environments
CRYPTOGRAPHY_AVAILABLE = False
try:
    import sys
    # Check if we can import without crashing
    if '_cffi_backend' in sys.modules or 'cffi' in sys.modules:
        from skillmeat.core.signing.key_manager import KeyManager
        CRYPTOGRAPHY_AVAILABLE = True
except Exception:
    pass


class TestSkillMeatMarketplaceBroker:
    """Tests for SkillMeatMarketplaceBroker."""

    def test_initialization_default(self):
        """Test broker initialization with defaults."""
        broker = SkillMeatMarketplaceBroker()

        assert broker.name == "SkillMeat"
        assert broker.base_url == "https://marketplace.skillmeat.dev/api/v1"
        assert broker.api_key is None
        assert "User-Agent" in broker._session_headers

    def test_initialization_custom(self):
        """Test broker initialization with custom values."""
        broker = SkillMeatMarketplaceBroker(
            base_url="https://custom.example.com/api",
            api_key="test-key",
            rate_limit=30,
        )

        assert broker.base_url == "https://custom.example.com/api"
        assert broker.api_key == "test-key"
        assert broker.rate_limiter.calls_per_minute == 30
        assert broker._session_headers["Authorization"] == "Bearer test-key"

    @patch("requests.get")
    def test_listings_success(self, mock_get):
        """Test successful listings fetch."""
        broker = SkillMeatMarketplaceBroker()

        # Mock response data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listings": [
                {
                    "listing_id": "test-123",
                    "name": "Test Skill",
                    "description": "A test skill",
                    "category": "skill",
                    "version": "1.0.0",
                    "publisher": {"name": "Test Publisher"},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "source_url": "https://example.com/listing",
                    "bundle_url": "https://example.com/bundle.zip",
                }
            ],
            "total_count": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        }
        mock_get.return_value = mock_response

        # Test
        result = broker.listings()

        assert len(result.listings) == 1
        assert result.total_count == 1
        assert result.listings[0].name == "Test Skill"

    @patch("requests.get")
    def test_listings_with_query(self, mock_get):
        """Test listings fetch with query parameters."""
        broker = SkillMeatMarketplaceBroker()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listings": [],
            "total_count": 0,
            "page": 2,
            "page_size": 10,
            "total_pages": 0,
            "has_next": False,
            "has_prev": True,
        }
        mock_get.return_value = mock_response

        query = ListingQuery(
            search="automation",
            category=ArtifactCategory.SKILL,
            tags=["productivity"],
            page=2,
            page_size=10,
        )

        result = broker.listings(query)

        # Verify request was made with correct params
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["q"] == "automation"
        assert params["category"] == "skill"
        assert params["page"] == 2

    @patch("requests.get")
    def test_listings_connection_error(self, mock_get):
        """Test listings fetch with connection error."""
        broker = SkillMeatMarketplaceBroker()
        mock_get.side_effect = RequestException("Connection failed")

        with pytest.raises(ConnectionError):
            broker.listings()

    @patch("requests.get")
    def test_get_listing_success(self, mock_get):
        """Test successful get_listing."""
        broker = SkillMeatMarketplaceBroker()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listing_id": "test-123",
            "name": "Test Skill",
            "description": "A test skill",
            "category": "skill",
            "version": "1.0.0",
            "publisher": {"name": "Test Publisher"},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "source_url": "https://example.com/listing",
            "bundle_url": "https://example.com/bundle.zip",
        }
        mock_get.return_value = mock_response

        result = broker.get_listing("test-123")

        assert result is not None
        assert result.listing_id == "test-123"
        assert result.name == "Test Skill"

    @patch("requests.get")
    def test_get_listing_not_found(self, mock_get):
        """Test get_listing with 404 response."""
        broker = SkillMeatMarketplaceBroker()

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = broker.get_listing("nonexistent")

        assert result is None

    @pytest.mark.skipif(
        not CRYPTOGRAPHY_AVAILABLE, reason="Cryptography dependencies not available"
    )
    @patch("skillmeat.core.sharing.validator.BundleValidator")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_success(self, mock_file, mock_get, mock_validator_class):
        """Test successful bundle download."""
        broker = SkillMeatMarketplaceBroker()

        # Mock get_listing
        with patch.object(broker, "get_listing") as mock_get_listing:
            mock_listing = Mock()
            mock_listing.listing_id = "test-123"
            mock_listing.name = "test-skill"
            mock_listing.version = "1.0.0"
            mock_listing.bundle_url = "https://example.com/bundle.zip"
            mock_listing.signature = None  # No signature to avoid verification
            mock_get_listing.return_value = mock_listing

            # Mock download response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content = lambda chunk_size: [b"test data"]
            mock_get.return_value = mock_response

            # Mock validator
            mock_validator = Mock()
            mock_validation_result = Mock()
            mock_validation_result.is_valid = True
            mock_validator.validate.return_value = mock_validation_result
            mock_validator_class.return_value = mock_validator

            # Test
            result = broker.download("test-123")

            assert result.success is True
            assert result.bundle_path is not None
            assert "test-skill" in result.bundle_path

    @patch("requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"bundle data")
    def test_publish_success(self, mock_file, mock_post):
        """Test successful bundle publish."""
        broker = SkillMeatMarketplaceBroker(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listing_id": "new-123",
            "listing_url": "https://example.com/listing/new-123",
        }
        mock_post.return_value = mock_response

        # Create a temp file
        with patch("pathlib.Path.exists", return_value=True):
            request = PublishRequest(
                bundle_path="/tmp/test-bundle.pack",
                name="Test Bundle",
                description="A test bundle",
                category=ArtifactCategory.SKILL,
                version="1.0.0",
                sign_bundle=False,
            )

            result = broker.publish(request)

            assert result.success is True
            assert result.listing_id == "new-123"

    def test_publish_no_api_key(self):
        """Test publish without API key raises error."""
        broker = SkillMeatMarketplaceBroker()  # No API key

        # Mock file exists to bypass that check
        with patch("pathlib.Path.exists", return_value=True):
            request = PublishRequest(
                bundle_path="/tmp/test.pack",
                name="Test",
                description="Test",
                category=ArtifactCategory.SKILL,
                version="1.0.0",
            )

            with pytest.raises(PermissionError):
                broker.publish(request)


class TestClaudeHubBroker:
    """Tests for ClaudeHubBroker."""

    def test_initialization(self):
        """Test broker initialization."""
        broker = ClaudeHubBroker()

        assert broker.name == "ClaudeHub"
        assert broker.base_url == "https://claudehub.dev/api"
        assert broker.api_key is None
        assert broker.rate_limiter.calls_per_minute == 30

    @patch("requests.get")
    def test_listings_success(self, mock_get):
        """Test successful listings fetch."""
        broker = ClaudeHubBroker()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "test-123",
                    "name": "Test Skill",
                    "description": "Test",
                    "type": "skill",
                    "version": "1.0.0",
                    "author": {"name": "Test Author"},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "url": "https://claudehub.dev/catalog/test-123",
                    "download_url": "https://example.com/bundle.zip",
                }
            ],
            "total": 1,
        }
        mock_get.return_value = mock_response

        result = broker.listings()

        assert len(result.listings) == 1
        assert result.listings[0].name == "Test Skill"

    @patch("requests.get")
    def test_transform_claudehub_item(self, mock_get):
        """Test transformation of Claude Hub item to Listing."""
        broker = ClaudeHubBroker()

        item = {
            "id": "test-skill",
            "name": "Test Skill",
            "description": "A test skill",
            "type": "skill",
            "version": "2.0.0",
            "author": {
                "name": "Test Author",
                "email": "test@example.com",
                "website": "https://example.com",
            },
            "license": "Apache-2.0",
            "tags": ["automation", "tools"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "downloads": 500,
            "url": "https://claudehub.dev/catalog/test-skill",
            "download_url": "https://example.com/download",
            "repository": "https://github.com/test/repo",
        }

        listing = broker._transform_claudehub_item(item)

        assert listing.listing_id == "test-skill"
        assert listing.name == "Test Skill"
        assert listing.category == ArtifactCategory.SKILL
        assert listing.version == "2.0.0"
        assert listing.license == "Apache-2.0"
        assert listing.tags == ["automation", "tools"]
        assert listing.downloads == 500
        assert listing.price == 0.0  # Always free
        assert listing.signature is None  # No signatures

    def test_publish_not_supported(self):
        """Test that publishing is not supported."""
        broker = ClaudeHubBroker()

        request = PublishRequest(
            bundle_path="/tmp/test.pack",
            name="Test",
            description="Test",
            category=ArtifactCategory.SKILL,
            version="1.0.0",
        )

        result = broker.publish(request)

        assert result.success is False
        assert "not support" in result.message.lower()


class TestCustomWebBroker:
    """Tests for CustomWebBroker."""

    def test_initialization_default(self):
        """Test broker initialization with defaults."""
        broker = CustomWebBroker(base_url="https://custom.example.com/api")

        assert broker.name == "CustomWeb"
        assert broker.base_url == "https://custom.example.com/api"
        assert broker.api_key is None
        assert broker.verify_ssl is True

    def test_initialization_with_auth(self):
        """Test broker initialization with authentication."""
        broker = CustomWebBroker(
            base_url="https://custom.example.com/api",
            api_key="test-key",
            auth_header="X-API-Key",
            auth_prefix="",
        )

        assert broker.api_key == "test-key"
        assert broker._session_headers["X-API-Key"] == "test-key"

    def test_initialization_with_custom_headers(self):
        """Test broker initialization with custom headers."""
        custom_headers = {
            "X-Custom-Header": "value",
            "X-Another-Header": "another-value",
        }

        broker = CustomWebBroker(
            base_url="https://custom.example.com/api",
            custom_headers=custom_headers,
        )

        assert broker._session_headers["X-Custom-Header"] == "value"
        assert broker._session_headers["X-Another-Header"] == "another-value"

    @patch("requests.get")
    def test_listings_success(self, mock_get):
        """Test successful listings fetch."""
        broker = CustomWebBroker(base_url="https://custom.example.com/api")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listings": [
                {
                    "listing_id": "custom-123",
                    "name": "Custom Skill",
                    "description": "Test",
                    "category": "skill",
                    "version": "1.0.0",
                    "publisher": {"name": "Custom Publisher"},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "source_url": "https://example.com",
                    "bundle_url": "https://example.com/bundle",
                }
            ],
            "total_count": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        }
        mock_get.return_value = mock_response

        result = broker.listings()

        assert len(result.listings) == 1
        assert result.listings[0].name == "Custom Skill"

    @patch("requests.get")
    def test_listings_alternative_format(self, mock_get):
        """Test listings with alternative response format."""
        broker = CustomWebBroker(base_url="https://custom.example.com/api")

        # Some endpoints might return listings without full pagination wrapper
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "listings": [
                {
                    "listing_id": "custom-123",
                    "name": "Custom Skill",
                    "description": "Test",
                    "category": "skill",
                    "version": "1.0.0",
                    "publisher": {"name": "Custom Publisher"},
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "source_url": "https://example.com",
                    "bundle_url": "https://example.com/bundle",
                }
            ],
            "total_count": 1,
            # Missing some pagination fields
        }
        mock_get.return_value = mock_response

        result = broker.listings()

        assert len(result.listings) == 1

    def test_ssl_verification_disabled(self):
        """Test broker with SSL verification disabled."""
        broker = CustomWebBroker(
            base_url="https://custom.example.com/api", verify_ssl=False
        )

        assert broker.verify_ssl is False

    @pytest.mark.skipif(
        not CRYPTOGRAPHY_AVAILABLE, reason="Cryptography dependencies not available"
    )
    @patch("requests.get")
    def test_download_with_ssl_disabled(self, mock_get):
        """Test download respects verify_ssl setting."""
        broker = CustomWebBroker(
            base_url="https://custom.example.com/api", verify_ssl=False
        )

        with patch.object(broker, "get_listing") as mock_get_listing:
            mock_listing = Mock()
            mock_listing.listing_id = "test"
            mock_listing.name = "test"
            mock_listing.version = "1.0.0"
            mock_listing.bundle_url = "https://example.com/bundle"
            mock_listing.signature = None  # No signature to avoid verification
            mock_get_listing.return_value = mock_listing

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_content = lambda chunk_size: [b"data"]
            mock_get.return_value = mock_response

            with patch("skillmeat.core.sharing.validator.BundleValidator"):
                broker.download("test")

                # Verify SSL setting was passed to requests
                call_kwargs = mock_get.call_args[1]
                assert call_kwargs["verify"] is False
