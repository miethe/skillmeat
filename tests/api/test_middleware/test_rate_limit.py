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

    def test_middleware_per_ip_tracking(self):
        """Test that rate limits are tracked per IP."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=5,
            block_duration=10,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Make requests up to threshold - 1 (4 requests OK)
        for _ in range(4):
            response = client.get("/test")
            assert response.status_code == 200

        # 5th request should trigger burst (threshold reached)
        response = client.get("/test")
        assert response.status_code == 429

        # Note: TestClient uses same IP for all requests
        # Per-IP isolation is tested in unit tests

    def test_middleware_blocked_ip_stays_blocked(self):
        """Test that blocked IP continues to receive 429."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=3,
            block_duration=10,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Trigger burst
        for _ in range(3):
            client.get("/test")

        # Should be blocked
        response = client.get("/test")
        assert response.status_code == 429

        # Should remain blocked on subsequent requests
        response = client.get("/test")
        assert response.status_code == 429

        response = client.get("/test")
        assert response.status_code == 429

    def test_middleware_block_expires(self):
        """Test that block expires after duration (QuickReset - RL-004)."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=2,  # Short window for testing
            burst_threshold=3,
            block_duration=1,  # Short block for testing
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Trigger burst on /test (2 OK, 3rd triggers)
        for _ in range(2):
            client.get("/test")

        # 3rd request triggers burst
        response = client.get("/test")
        assert response.status_code == 429

        # Wait for both block AND window to expire
        time.sleep(2.5)

        # After block and window expire, same endpoint should work again
        response = client.get("/test")
        assert response.status_code == 200

    def test_middleware_different_endpoints_no_burst(self):
        """Test that 20 different endpoints don't trigger burst."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=20,
            block_duration=10,
        )

        # Create multiple endpoints
        endpoints = []
        for i in range(25):

            @app.get(f"/test/{i}")
            async def test_endpoint():
                return {"status": "ok"}

            endpoints.append(f"/test/{i}")

        client = TestClient(app)

        # Make requests to different endpoints
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not trigger burst (all different fingerprints)
            assert response.status_code == 200

    def test_middleware_same_endpoint_different_params_no_burst(self):
        """Test that same endpoint with different params creates different fingerprints."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=20,
            block_duration=10,
        )

        @app.get("/test")
        async def test_endpoint(page: int = 1):
            return {"status": "ok", "page": page}

        client = TestClient(app)

        # Make requests with different query params
        for i in range(25):
            response = client.get(f"/test?page={i}")
            # Should not trigger burst (different fingerprints due to params)
            assert response.status_code == 200

    def test_middleware_same_endpoint_same_params_triggers_burst(self):
        """Test that identical requests (endpoint + params) trigger burst."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=10,
            block_duration=10,
        )

        @app.get("/test")
        async def test_endpoint(page: int = 1):
            return {"status": "ok", "page": page}

        client = TestClient(app)

        # Make identical requests (same endpoint and params) - 9 OK
        for i in range(9):
            response = client.get("/test?page=1")
            assert response.status_code == 200

        # 10th identical request should trigger burst (threshold reached)
        response = client.get("/test?page=1")
        assert response.status_code == 429

    def test_middleware_excluded_path_prefix(self):
        """Test that excluded path works as prefix match."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=5,
            block_duration=10,
            excluded_paths=["/api/public", "/health", "/docs", "/redoc", "/openapi.json", "/"],
        )

        @app.get("/api/public/test")
        async def public_endpoint():
            return {"status": "ok"}

        @app.get("/api/private/test")
        async def private_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Public endpoints should never be rate limited (prefix match)
        for _ in range(20):
            response = client.get("/api/public/test")
            assert response.status_code == 200

        # Private endpoint should be rate limited (4 OK, 5th triggers)
        for _ in range(4):
            response = client.get("/api/private/test")
            assert response.status_code == 200

        response = client.get("/api/private/test")
        assert response.status_code == 429

    def test_middleware_default_excluded_paths(self):
        """Test that default excluded paths are respected."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=5,
            block_duration=10,
            # Uses default excluded_paths: ["/health", "/docs", "/redoc", "/openapi.json", "/"]
        )

        @app.get("/")
        async def root():
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        @app.get("/docs")
        async def docs():
            return {"status": "docs"}

        @app.get("/api/test")
        async def api_test():
            return {"status": "ok"}

        client = TestClient(app)

        # All default excluded paths should allow unlimited requests
        for _ in range(10):
            assert client.get("/").status_code == 200
            assert client.get("/health").status_code == 200
            assert client.get("/docs").status_code == 200

        # Regular API endpoint should be rate limited (4 OK, 5th triggers)
        for _ in range(4):
            response = client.get("/api/test")
            assert response.status_code == 200

        response = client.get("/api/test")
        assert response.status_code == 429

    def test_middleware_headers_show_current_count(self):
        """Test that headers correctly show current request count."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            window_seconds=10,
            burst_threshold=10,
            block_duration=10,
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # First request
        response = client.get("/test")
        assert response.headers["X-RateLimit-Current"] == "1"

        # Second request
        response = client.get("/test")
        assert response.headers["X-RateLimit-Current"] == "2"

        # Third request
        response = client.get("/test")
        assert response.headers["X-RateLimit-Current"] == "3"
