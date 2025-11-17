"""Tests for base marketplace broker and rate limiter."""

import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from skillmeat.core.marketplace.broker import MarketplaceBroker, RateLimiter
from skillmeat.core.marketplace.models import (
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    PublishRequest,
    PublishResult,
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


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(calls_per_minute=60)

        assert limiter.calls_per_minute == 60
        assert limiter.tokens == 60.0
        assert isinstance(limiter.last_refill, float)

    def test_acquire_single_token(self):
        """Test acquiring a single token."""
        limiter = RateLimiter(calls_per_minute=10)

        result = limiter.acquire(1)
        assert result is True
        assert limiter.tokens == 9.0

    def test_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens."""
        limiter = RateLimiter(calls_per_minute=10)

        result = limiter.acquire(5)
        assert result is True
        assert limiter.tokens == 5.0

    def test_acquire_exceeds_available(self):
        """Test acquiring more tokens than available."""
        limiter = RateLimiter(calls_per_minute=10)
        limiter.tokens = 3.0
        limiter.last_refill = time.time()  # Prevent refill

        result = limiter.acquire(5)
        assert result is False
        # Tokens may change slightly due to refill, just check it failed
        assert limiter.tokens < 5.0

    def test_acquire_all_tokens(self):
        """Test acquiring all available tokens."""
        limiter = RateLimiter(calls_per_minute=10)

        result = limiter.acquire(10)
        assert result is True
        assert limiter.tokens == 0.0

        # Next acquire should fail
        result = limiter.acquire(1)
        assert result is False

    def test_refill_after_time(self):
        """Test token refill after time passes."""
        limiter = RateLimiter(calls_per_minute=60)
        limiter.tokens = 0.0
        limiter.last_refill = time.time() - 60.0  # 60 seconds ago

        # Should refill on next acquire
        result = limiter.acquire(1)
        assert result is True
        assert limiter.tokens > 0.0

    def test_partial_refill(self):
        """Test partial refill based on elapsed time."""
        limiter = RateLimiter(calls_per_minute=60)
        limiter.tokens = 0.0
        limiter.last_refill = time.time() - 30.0  # 30 seconds ago (half refill)

        limiter._refill()
        # Should have ~30 tokens (half of 60)
        assert 25.0 < limiter.tokens < 35.0

    def test_reset(self):
        """Test resetting rate limiter."""
        limiter = RateLimiter(calls_per_minute=60)
        limiter.tokens = 10.0

        limiter.reset()
        assert limiter.tokens == 60.0

    def test_wait_and_acquire_immediate(self):
        """Test wait_and_acquire when tokens are available."""
        limiter = RateLimiter(calls_per_minute=10)

        start = time.time()
        result = limiter.wait_and_acquire(5, timeout=5.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 0.1  # Should be immediate

    def test_wait_and_acquire_timeout(self):
        """Test wait_and_acquire with timeout."""
        limiter = RateLimiter(calls_per_minute=10)
        limiter.tokens = 0.0
        limiter.last_refill = time.time()  # Start fresh

        start = time.time()
        result = limiter.wait_and_acquire(5, timeout=0.5)
        elapsed = time.time() - start

        assert result is False
        # Timeout may vary slightly, just ensure it didn't complete immediately
        assert elapsed >= 0.4

    def test_thread_safety(self):
        """Test thread safety of rate limiter."""
        import threading

        limiter = RateLimiter(calls_per_minute=100)
        acquired_counts = []

        def worker():
            count = 0
            for _ in range(10):
                if limiter.acquire(1):
                    count += 1
            acquired_counts.append(count)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Total acquired should not exceed available tokens
        total_acquired = sum(acquired_counts)
        assert total_acquired <= 100


class ConcreteMarketplaceBroker(MarketplaceBroker):
    """Concrete implementation of MarketplaceBroker for testing."""

    def listings(self, query=None):
        return ListingPage(
            listings=[],
            total_count=0,
            page=1,
            page_size=20,
            total_pages=0,
            has_next=False,
            has_prev=False,
        )

    def download(self, listing_id, output_dir=None):
        return DownloadResult(
            success=True,
            bundle_path="/tmp/test.pack",
            listing=None,
            verified=False,
            message="Test download",
            errors=[],
        )

    def publish(self, request):
        return PublishResult(
            success=True,
            listing_id="test-123",
            listing_url=None,
            message="Test publish",
            errors=[],
        )


class TestMarketplaceBroker:
    """Tests for MarketplaceBroker base class."""

    def test_initialization(self):
        """Test broker initialization."""
        broker = ConcreteMarketplaceBroker(
            name="TestBroker",
            base_url="https://test.example.com",
            api_key="test-key",
            rate_limit=30,
        )

        assert broker.name == "TestBroker"
        assert broker.base_url == "https://test.example.com"
        assert broker.api_key == "test-key"
        assert broker.rate_limiter.calls_per_minute == 30

    def test_initialization_defaults(self):
        """Test broker initialization with defaults."""
        broker = ConcreteMarketplaceBroker(name="TestBroker")

        assert broker.name == "TestBroker"
        assert broker.base_url is None
        assert broker.api_key is None
        assert broker.rate_limiter.calls_per_minute == 60

    def test_rate_limit_wait(self):
        """Test rate limiting in broker."""
        broker = ConcreteMarketplaceBroker(name="TestBroker", rate_limit=10)
        broker.rate_limiter.tokens = 0.0

        # Mock wait_and_acquire to avoid actual waiting
        with patch.object(broker.rate_limiter, "wait_and_acquire", return_value=True):
            broker._rate_limit_wait()
            broker.rate_limiter.wait_and_acquire.assert_called_once_with(
                tokens=1, timeout=30.0
            )

    def test_get_listing_default_implementation(self):
        """Test default get_listing implementation."""
        broker = ConcreteMarketplaceBroker(name="TestBroker")

        # Default implementation returns None (needs override)
        result = broker.get_listing("test-123")
        assert result is None

    def test_verify_signature_no_signature(self):
        """Test signature verification when listing has no signature."""
        broker = ConcreteMarketplaceBroker(name="TestBroker")

        listing = Listing(
            listing_id="test-123",
            name="Test Listing",
            description="Test",
            category="skill",
            version="1.0.0",
            publisher=PublisherInfo(name="Test Publisher"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            source_url="https://example.com/listing",
            bundle_url="https://example.com/bundle.zip",
            signature=None,  # No signature
        )

        # Should return True (signature is optional)
        result = broker.verify_signature(listing)
        assert result is True

    @pytest.mark.skipif(
        not CRYPTOGRAPHY_AVAILABLE, reason="Cryptography dependencies not available"
    )
    def test_verify_signature_with_signature_no_fingerprint(self):
        """Test signature verification with signature but no fingerprint."""
        broker = ConcreteMarketplaceBroker(name="TestBroker")

        listing = Listing(
            listing_id="test-123",
            name="Test Listing",
            description="Test",
            category="skill",
            version="1.0.0",
            publisher=PublisherInfo(
                name="Test Publisher",
                key_fingerprint=None,  # No fingerprint
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            source_url="https://example.com/listing",
            bundle_url="https://example.com/bundle.zip",
            signature="base64signature",
        )

        # Should return False (signature present but no fingerprint)
        result = broker.verify_signature(listing)
        assert result is False

    def test_repr(self):
        """Test string representation."""
        broker = ConcreteMarketplaceBroker(
            name="TestBroker", base_url="https://test.example.com"
        )

        repr_str = repr(broker)
        assert "ConcreteMarketplaceBroker" in repr_str
        assert "TestBroker" in repr_str
        assert "https://test.example.com" in repr_str


class TestAbstractMethods:
    """Tests for abstract method enforcement."""

    def test_cannot_instantiate_abstract_broker(self):
        """Test that MarketplaceBroker cannot be instantiated directly."""

        class IncompletebrokerBroker(MarketplaceBroker):
            """Broker missing implementations."""

            pass

        with pytest.raises(TypeError):
            IncompletebrokerBroker(name="Incomplete")

    def test_must_implement_listings(self):
        """Test that listings() must be implemented."""

        class NoListingsBroker(MarketplaceBroker):
            def download(self, listing_id, output_dir=None):
                pass

            def publish(self, request):
                pass

        with pytest.raises(TypeError):
            NoListingsBroker(name="NoListings")

    def test_must_implement_download(self):
        """Test that download() must be implemented."""

        class NoDownloadBroker(MarketplaceBroker):
            def listings(self, query=None):
                pass

            def publish(self, request):
                pass

        with pytest.raises(TypeError):
            NoDownloadBroker(name="NoDownload")

    def test_must_implement_publish(self):
        """Test that publish() must be implemented."""

        class NoPublishBroker(MarketplaceBroker):
            def listings(self, query=None):
                pass

            def download(self, listing_id, output_dir=None):
                pass

        with pytest.raises(TypeError):
            NoPublishBroker(name="NoPublish")
