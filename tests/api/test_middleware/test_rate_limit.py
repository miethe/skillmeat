"""Tests for rate limiting middleware.

Tests token bucket algorithm, rate limiting, and middleware integration.
"""

import time

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from skillmeat.api.middleware.rate_limit import (
    RateLimiter,
    RateLimitMiddleware,
    TokenBucket,
)


class TestTokenBucket:
    """Tests for TokenBucket implementation."""

    def test_token_bucket_init(self):
        """Test token bucket initialization."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        assert bucket.max_tokens == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10.0

    def test_consume_success(self):
        """Test successful token consumption."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        result = bucket.consume(5)
        assert result is True
        assert bucket.tokens == 5.0

    def test_consume_failure(self):
        """Test token consumption when insufficient tokens."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        # Consume all tokens
        bucket.consume(10)

        # Should fail
        result = bucket.consume(1)
        assert result is False

    def test_refill(self):
        """Test token refilling over time."""
        bucket = TokenBucket(max_tokens=10, refill_rate=10.0)  # 10 tokens/second

        # Consume tokens
        bucket.consume(10)
        assert bucket.tokens == 0

        # Wait and refill
        time.sleep(0.5)
        bucket.refill()

        # Should have ~5 tokens (0.5s * 10 tokens/s)
        assert bucket.tokens >= 4.0
        assert bucket.tokens <= 6.0

    def test_refill_max_cap(self):
        """Test that refill doesn't exceed max tokens."""
        bucket = TokenBucket(max_tokens=10, refill_rate=10.0)

        # Wait and refill
        time.sleep(2.0)
        bucket.refill()

        # Should be capped at max_tokens
        assert bucket.tokens == 10.0

    def test_time_until_refill(self):
        """Test calculating time until tokens available."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        # Consume all tokens
        bucket.consume(10)

        # Should take ~5 seconds to get 5 tokens
        time_needed = bucket.time_until_refill(5)
        assert time_needed >= 4.9
        assert time_needed <= 5.1

    def test_time_until_refill_sufficient(self):
        """Test time until refill when tokens already sufficient."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        time_needed = bucket.time_until_refill(5)
        assert time_needed == 0.0


class TestRateLimiter:
    """Tests for RateLimiter."""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(default_max_requests=100, default_window_seconds=60)

        assert limiter.default_config.max_requests == 100
        assert limiter.default_config.window_seconds == 60

    def test_add_endpoint_limit(self):
        """Test adding endpoint-specific limit."""
        limiter = RateLimiter()

        limiter.add_endpoint_limit("/api/test", max_requests=10, window_seconds=60)

        assert "/api/test" in limiter.endpoint_configs
        config = limiter.endpoint_configs["/api/test"]
        assert config.max_requests == 10
        assert config.window_seconds == 60

    def test_check_rate_limit_allowed(self):
        """Test rate limit check when allowed."""
        limiter = RateLimiter(default_max_requests=10, default_window_seconds=60)

        allowed, retry_after = limiter.check_rate_limit("192.168.1.1", "/api/test")

        assert allowed is True
        assert retry_after is None

    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when exceeded."""
        limiter = RateLimiter(default_max_requests=3, default_window_seconds=60)

        # Make requests up to limit
        for i in range(3):
            allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
            assert allowed is True

        # Fourth request should be rate limited
        allowed, retry_after = limiter.check_rate_limit("192.168.1.1", "/api/test")

        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0

    def test_endpoint_specific_limits(self):
        """Test that endpoint-specific limits work."""
        limiter = RateLimiter(default_max_requests=10, default_window_seconds=60)

        # Add stricter limit for specific endpoint
        limiter.add_endpoint_limit("/api/restricted", max_requests=2, window_seconds=60)

        # Make requests to default endpoint
        for i in range(5):
            allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
            assert allowed is True

        # Make requests to restricted endpoint
        for i in range(2):
            allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/restricted")
            assert allowed is True

        # Third request to restricted should fail
        allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/restricted")
        assert allowed is False

    def test_per_ip_tracking(self):
        """Test that rate limits are tracked per IP."""
        limiter = RateLimiter(default_max_requests=2, default_window_seconds=60)

        # Make requests from IP1
        for i in range(2):
            allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
            assert allowed is True

        # IP1 should be rate limited
        allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
        assert allowed is False

        # IP2 should still be allowed
        allowed, _ = limiter.check_rate_limit("192.168.1.2", "/api/test")
        assert allowed is True

    def test_reset_specific_ip(self):
        """Test resetting rate limits for specific IP."""
        limiter = RateLimiter(default_max_requests=2, default_window_seconds=60)

        # Exhaust rate limit
        for i in range(2):
            limiter.check_rate_limit("192.168.1.1", "/api/test")

        # Should be rate limited
        allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
        assert allowed is False

        # Reset
        limiter.reset(ip="192.168.1.1")

        # Should be allowed again
        allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
        assert allowed is True

    def test_reset_all(self):
        """Test resetting all rate limits."""
        limiter = RateLimiter(default_max_requests=2, default_window_seconds=60)

        # Exhaust rate limits for multiple IPs
        for i in range(2):
            limiter.check_rate_limit("192.168.1.1", "/api/test")
            limiter.check_rate_limit("192.168.1.2", "/api/test")

        # Reset all
        limiter.reset()

        # Both should be allowed again
        allowed, _ = limiter.check_rate_limit("192.168.1.1", "/api/test")
        assert allowed is True

        allowed, _ = limiter.check_rate_limit("192.168.1.2", "/api/test")
        assert allowed is True


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware integration."""

    def test_middleware_allows_requests(self):
        """Test that middleware allows requests under limit."""
        app = FastAPI()

        limiter = RateLimiter(default_max_requests=10, default_window_seconds=60)
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Make requests under limit
        for i in range(5):
            response = client.get("/test")
            assert response.status_code == 200

    def test_middleware_rate_limits(self):
        """Test that middleware enforces rate limits."""
        app = FastAPI()

        limiter = RateLimiter(default_max_requests=3, default_window_seconds=60)
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Make requests up to limit
        for i in range(3):
            response = client.get("/test")
            assert response.status_code == 200

        # Fourth request should be rate limited
        response = client.get("/test")
        assert response.status_code == 429
        assert "error" in response.json()
        assert response.json()["error"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in response.headers

    def test_middleware_excludes_paths(self):
        """Test that excluded paths bypass rate limiting."""
        app = FastAPI()

        limiter = RateLimiter(default_max_requests=2, default_window_seconds=60)
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=limiter,
            excluded_paths=["/health"],
        )

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        client = TestClient(app)

        # Exhaust rate limit on /test
        for i in range(2):
            response = client.get("/test")
            assert response.status_code == 200

        # /test should be rate limited
        response = client.get("/test")
        assert response.status_code == 429

        # /health should still work (excluded)
        for i in range(5):
            response = client.get("/health")
            assert response.status_code == 200

    def test_middleware_adds_headers(self):
        """Test that middleware adds rate limit headers."""
        app = FastAPI()

        limiter = RateLimiter(default_max_requests=10, default_window_seconds=60)
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200

        # Check headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_middleware_429_response(self):
        """Test 429 response format."""
        app = FastAPI()

        limiter = RateLimiter(default_max_requests=1, default_window_seconds=60)
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        # Exhaust limit
        client.get("/test")

        # Get 429 response
        response = client.get("/test")
        assert response.status_code == 429

        data = response.json()
        assert data["error"] == "RATE_LIMIT_EXCEEDED"
        assert "message" in data
        assert "retry_after" in data
        assert isinstance(data["retry_after"], int)

        # Check headers
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"
