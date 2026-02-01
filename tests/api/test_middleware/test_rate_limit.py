"""Tests for rate limiting middleware.

Tests burst detection, rate limiting middleware, and deprecation warnings.
"""

import time
import warnings

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillmeat.api.middleware.rate_limit import (
    RateLimitConfig,
    RateLimiter,
    RateLimitMiddleware,
    TokenBucket,
)


class TestDeprecatedClasses:
    """Tests for deprecated classes and their deprecation warnings."""

    def test_rate_limit_config_deprecation_warning(self):
        """Test that RateLimitConfig raises DeprecationWarning on instantiation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = RateLimitConfig(requests_per_hour=100)

            # Should have one warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "RateLimitConfig is deprecated" in str(w[0].message)
            assert "will be removed in v1.0" in str(w[0].message)
            assert "SlidingWindowTracker" in str(w[0].message)

    def test_rate_limit_config_has_value(self):
        """Test that RateLimitConfig still holds the value despite deprecation."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            config = RateLimitConfig(requests_per_hour=50)
            assert config.requests_per_hour == 50

    def test_token_bucket_deprecation_warning(self):
        """Test that TokenBucket raises DeprecationWarning on instantiation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            bucket = TokenBucket()

            # Should have one warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "TokenBucket is deprecated" in str(w[0].message)
            assert "will be removed in v1.0" in str(w[0].message)
            assert "SlidingWindowTracker" in str(w[0].message)

    def test_token_bucket_methods_not_implemented(self):
        """Test that TokenBucket methods raise NotImplementedError."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            bucket = TokenBucket()

        # Test add_tokens
        with pytest.raises(NotImplementedError, match="TokenBucket is deprecated"):
            bucket.add_tokens(5)

        # Test consume_token
        with pytest.raises(NotImplementedError, match="TokenBucket is deprecated"):
            bucket.consume_token()

        # Test get_available_tokens
        with pytest.raises(NotImplementedError, match="TokenBucket is deprecated"):
            bucket.get_available_tokens()

    def test_rate_limiter_deprecation_warning(self):
        """Test that RateLimiter raises DeprecationWarning on instantiation."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            limiter = RateLimiter()

            # Should have one warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "RateLimiter is deprecated" in str(w[0].message)
            assert "will be removed in v1.0" in str(w[0].message)
            assert "SlidingWindowTracker" in str(w[0].message)

    def test_rate_limiter_methods_not_implemented(self):
        """Test that RateLimiter methods raise NotImplementedError."""
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            limiter = RateLimiter()

        # Test is_allowed
        with pytest.raises(NotImplementedError, match="RateLimiter is deprecated"):
            limiter.is_allowed()

        # Test reset
        with pytest.raises(NotImplementedError, match="RateLimiter is deprecated"):
            limiter.reset()


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware with burst detection."""

    def test_middleware_allows_normal_requests(self):
        """Test that middleware allows normal requests under burst threshold."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=20,
            block_duration=10,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Make requests under burst threshold
        for i in range(10):
            response = client.get("/test")
            assert response.status_code == 200

    def test_middleware_detects_burst(self):
        """Test that middleware detects burst and returns 429."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=5,  # Low threshold for testing
            block_duration=1,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Make requests up to burst threshold (4 requests are OK)
        for i in range(4):
            response = client.get("/test")
            assert response.status_code == 200

        # 5th identical request triggers burst detection (threshold reached)
        response = client.get("/test")
        assert response.status_code == 429
        assert "error" in response.json()
        assert response.json()["error"] == "RATE_LIMIT_EXCEEDED"

    def test_middleware_excludes_paths(self):
        """Test that excluded paths bypass rate limiting."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=2,
            excluded_paths=["/health"],
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        client = TestClient(app)

        # Trigger burst on /test
        for i in range(3):
            response = client.get("/test")

        # /test should be rate limited
        response = client.get("/test")
        assert response.status_code == 429

        # /health should still work (excluded)
        for i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_middleware_adds_rate_limit_headers(self):
        """Test that middleware adds rate limit headers to successful responses."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=20,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Check for new-style headers
        assert "X-RateLimit-Window" in response.headers
        assert "X-RateLimit-Threshold" in response.headers
        assert "X-RateLimit-Current" in response.headers
        assert "X-RateLimit-Blocked" in response.headers

    def test_middleware_429_response_format(self):
        """Test 429 response format and headers."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=1,
            block_duration=2,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Trigger burst
        client.get("/test")
        response = client.get("/test")

        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "RATE_LIMIT_EXCEEDED"
        assert "message" in data
        assert "retry_after" in data

        # Check headers
        assert "Retry-After" in response.headers
        assert int(response.headers["Retry-After"]) == 2
