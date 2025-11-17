"""Tests for marketplace broker base class."""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from skillmeat.core.sharing.bundle import Bundle, BundleMetadata
from skillmeat.marketplace.broker import (
    CacheEntry,
    DownloadError,
    MarketplaceBroker,
    MarketplaceBrokerError,
    PublishError,
    RateLimitConfig,
    RateLimitError,
    ValidationError,
)
from skillmeat.marketplace.models import MarketplaceListing, PublishResult


class TestBroker(MarketplaceBroker):
    """Test implementation of MarketplaceBroker."""

    def listings(self, filters=None, page=1, page_size=20):
        """Test implementation."""
        return []

    def download(self, listing_id, output_dir=None):
        """Test implementation."""
        return Path("/tmp/test.zip")

    def publish(self, bundle, metadata=None):
        """Test implementation."""
        return PublishResult(
            submission_id="test-123",
            status="pending",
            message="Test submission",
        )


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_cache_entry_not_expired(self):
        """Test that fresh cache entry is not expired."""
        entry = CacheEntry(data="test", ttl=60)
        assert not entry.is_expired()

    def test_cache_entry_expired(self):
        """Test that old cache entry is expired."""
        entry = CacheEntry(data="test", ttl=0)
        time.sleep(0.1)
        assert entry.is_expired()


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        assert config.max_requests == 100
        assert config.time_window == 60
        assert config.retry_after == 60

    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(max_requests=50, time_window=30, retry_after=30)
        assert config.max_requests == 50
        assert config.time_window == 30
        assert config.retry_after == 30


class TestMarketplaceBroker:
    """Tests for MarketplaceBroker base class."""

    def test_broker_initialization(self):
        """Test broker initialization."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        assert broker.name == "test"
        assert broker.endpoint == "https://test.example.com/api"
        assert broker.cache_ttl == 300
        assert broker.rate_limit.max_requests == 100

    def test_broker_initialization_with_trailing_slash(self):
        """Test that trailing slash is removed from endpoint."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api/",
        )

        assert broker.endpoint == "https://test.example.com/api"

    def test_rate_limit_check_passes(self):
        """Test that rate limit check passes under limit."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
            rate_limit=RateLimitConfig(max_requests=5, time_window=60),
        )

        # Should not raise
        for _ in range(5):
            broker._check_rate_limit()

    def test_rate_limit_check_fails(self):
        """Test that rate limit check fails when exceeded."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
            rate_limit=RateLimitConfig(max_requests=2, time_window=60),
        )

        # First two should pass
        broker._check_rate_limit()
        broker._check_rate_limit()

        # Third should fail
        with pytest.raises(RateLimitError) as exc_info:
            broker._check_rate_limit()

        assert exc_info.value.retry_after == 60

    def test_cache_get_hit(self):
        """Test cache hit."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        broker._set_cache("test-key", "test-data")
        result = broker._get_cached("test-key")

        assert result == "test-data"

    def test_cache_get_miss(self):
        """Test cache miss."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        result = broker._get_cached("nonexistent")
        assert result is None

    def test_cache_get_expired(self):
        """Test expired cache entry."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
            cache_ttl=0,
        )

        broker._set_cache("test-key", "test-data")
        time.sleep(0.1)

        result = broker._get_cached("test-key")
        assert result is None

    @patch("skillmeat.marketplace.broker.requests.Session.request")
    def test_make_request_success(self, mock_request):
        """Test successful HTTP request."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_request.return_value = mock_response

        response = broker._make_request("GET", "https://test.example.com/api/test")

        assert response.status_code == 200
        mock_request.assert_called_once()

    @patch("skillmeat.marketplace.broker.requests.Session.request")
    def test_make_request_with_cache(self, mock_request):
        """Test HTTP request with caching."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        # First request - should hit the API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_request.return_value = mock_response

        response1 = broker._make_request(
            "GET",
            "https://test.example.com/api/test",
            cache_key="test-cache",
        )
        assert response1.status_code == 200

        # Second request - should use cache (no API call)
        mock_request.reset_mock()
        response2 = broker._make_request(
            "GET",
            "https://test.example.com/api/test",
            cache_key="test-cache",
        )

        # Should not have called the API again
        mock_request.assert_not_called()

    def test_verify_bundle_hash_success(self, tmp_path):
        """Test successful bundle hash verification."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        # Create test file
        test_file = tmp_path / "test.zip"
        test_file.write_bytes(b"test content")

        # Calculate expected hash
        import hashlib

        sha256 = hashlib.sha256()
        sha256.update(b"test content")
        expected_hash = sha256.hexdigest()

        # Should not raise
        assert broker.verify_bundle_hash(test_file, expected_hash)

    def test_verify_bundle_hash_with_prefix(self, tmp_path):
        """Test bundle hash verification with sha256: prefix."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        # Create test file
        test_file = tmp_path / "test.zip"
        test_file.write_bytes(b"test content")

        # Calculate expected hash
        import hashlib

        sha256 = hashlib.sha256()
        sha256.update(b"test content")
        expected_hash = f"sha256:{sha256.hexdigest()}"

        # Should not raise
        assert broker.verify_bundle_hash(test_file, expected_hash)

    def test_verify_bundle_hash_mismatch(self, tmp_path):
        """Test bundle hash verification with mismatch."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        # Create test file
        test_file = tmp_path / "test.zip"
        test_file.write_bytes(b"test content")

        # Wrong hash
        wrong_hash = "0" * 64

        with pytest.raises(ValidationError, match="Bundle hash mismatch"):
            broker.verify_bundle_hash(test_file, wrong_hash)

    def test_validate_signature_no_hash(self):
        """Test signature validation fails without bundle hash."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        bundle = Bundle(
            metadata=BundleMetadata(
                name="test",
                description="test",
                author="test",
                created_at="2025-01-15T12:00:00",
            ),
            bundle_hash=None,
        )

        with pytest.raises(ValidationError, match="Bundle has no hash"):
            broker.validate_signature(bundle)

    def test_close(self):
        """Test broker session close."""
        broker = TestBroker(
            name="test",
            endpoint="https://test.example.com/api",
        )

        # Should not raise
        broker.close()
