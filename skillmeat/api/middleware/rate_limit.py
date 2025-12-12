"""Rate limiting middleware for API endpoints.

Implements token bucket algorithm for rate limiting with per-IP tracking
and configurable limits for different endpoint patterns.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Implements the token bucket algorithm where tokens are added at a fixed rate
    and consumed on each request. When bucket is empty, requests are rejected.

    Attributes:
        max_tokens: Maximum tokens in bucket (burst capacity)
        refill_rate: Tokens added per second
        tokens: Current number of tokens
        last_refill: Timestamp of last refill
    """

    max_tokens: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(default_factory=time.time)

    def __post_init__(self):
        """Initialize tokens to max capacity."""
        self.tokens = float(self.max_tokens)

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_refill(self, tokens: int = 1) -> float:
        """Calculate time until enough tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds until tokens are available
        """
        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint pattern.

    Attributes:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        path_pattern: Endpoint path pattern (supports wildcards)
    """

    max_requests: int
    window_seconds: int
    path_pattern: str = "*"

    @property
    def refill_rate(self) -> float:
        """Calculate token refill rate.

        Returns:
            Tokens per second
        """
        return self.max_requests / self.window_seconds


class RateLimiter:
    """Rate limiter using token bucket algorithm.

    Tracks rate limits per IP address with configurable limits for
    different endpoint patterns.

    Attributes:
        default_config: Default rate limit configuration
        endpoint_configs: Per-endpoint rate limit configurations
        buckets: Token buckets per IP and endpoint
    """

    def __init__(
        self,
        default_max_requests: int = 100,
        default_window_seconds: int = 3600,
    ):
        """Initialize rate limiter.

        Args:
            default_max_requests: Default max requests per window
            default_window_seconds: Default window in seconds (default: 1 hour)
        """
        self.default_config = RateLimitConfig(
            max_requests=default_max_requests,
            window_seconds=default_window_seconds,
        )

        # Endpoint-specific configurations
        self.endpoint_configs: Dict[str, RateLimitConfig] = {}

        # Token buckets per (ip, endpoint_pattern)
        self.buckets: Dict[tuple, TokenBucket] = defaultdict(self._create_bucket)

        # Track last cleanup time
        self._last_cleanup = time.time()
        self._cleanup_interval = 3600  # Cleanup every hour

        logger.info(
            f"Rate limiter initialized (default: {default_max_requests} req/{default_window_seconds}s)"
        )

    def add_endpoint_limit(
        self,
        path_pattern: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Add rate limit for specific endpoint pattern.

        Args:
            path_pattern: Path pattern (e.g., "/api/marketplace/listings")
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
        """
        config = RateLimitConfig(
            max_requests=max_requests,
            window_seconds=window_seconds,
            path_pattern=path_pattern,
        )
        self.endpoint_configs[path_pattern] = config
        logger.info(
            f"Added rate limit: {path_pattern} = {max_requests} req/{window_seconds}s"
        )

    def _create_bucket(self) -> TokenBucket:
        """Create new token bucket with default config.

        Returns:
            Initialized TokenBucket
        """
        return TokenBucket(
            max_tokens=self.default_config.max_requests,
            refill_rate=self.default_config.refill_rate,
        )

    def _get_config_for_path(self, path: str) -> RateLimitConfig:
        """Get rate limit config for a path.

        Args:
            path: Request path

        Returns:
            Matching RateLimitConfig
        """
        import fnmatch

        # Check endpoint-specific configs
        for pattern, config in self.endpoint_configs.items():
            if fnmatch.fnmatch(path, pattern):
                return config

        # Return default config
        return self.default_config

    def _get_bucket(self, ip: str, path: str) -> TokenBucket:
        """Get or create token bucket for IP and path.

        Args:
            ip: Client IP address
            path: Request path

        Returns:
            TokenBucket instance
        """
        config = self._get_config_for_path(path)
        key = (ip, config.path_pattern)

        # Create bucket if doesn't exist
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(
                max_tokens=config.max_requests,
                refill_rate=config.refill_rate,
            )

        return self.buckets[key]

    def check_rate_limit(self, ip: str, path: str) -> tuple[bool, Optional[float]]:
        """Check if request should be rate limited.

        Args:
            ip: Client IP address
            path: Request path

        Returns:
            Tuple of (allowed, retry_after_seconds)
            - allowed: True if request is allowed
            - retry_after_seconds: Seconds to wait if not allowed, None if allowed
        """
        # Periodic cleanup of old buckets
        if time.time() - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_buckets()

        bucket = self._get_bucket(ip, path)

        if bucket.consume():
            return (True, None)
        else:
            retry_after = bucket.time_until_refill()
            logger.warning(
                f"Rate limit exceeded for {ip} on {path} (retry after {retry_after:.1f}s)"
            )
            return (False, retry_after)

    def _cleanup_old_buckets(self) -> None:
        """Remove inactive token buckets to free memory."""
        # Remove buckets that are full (haven't been used recently)
        keys_to_remove = []
        for key, bucket in self.buckets.items():
            bucket.refill()
            if bucket.tokens >= bucket.max_tokens * 0.99:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.buckets[key]

        if keys_to_remove:
            logger.debug(
                f"Cleaned up {len(keys_to_remove)} inactive rate limit buckets"
            )

        self._last_cleanup = time.time()

    def reset(self, ip: Optional[str] = None) -> None:
        """Reset rate limits.

        Args:
            ip: Optional IP to reset (resets all if None)
        """
        if ip:
            # Reset specific IP
            keys_to_remove = [key for key in self.buckets.keys() if key[0] == ip]
            for key in keys_to_remove:
                del self.buckets[key]
            logger.info(f"Reset rate limits for IP: {ip}")
        else:
            # Reset all
            self.buckets.clear()
            logger.info("Reset all rate limits")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for request rate limiting.

    Applies rate limiting to API endpoints with configurable limits per path.
    Returns 429 Too Many Requests with Retry-After header when limit exceeded.

    Attributes:
        rate_limiter: RateLimiter instance
        excluded_paths: Paths to exclude from rate limiting
    """

    def __init__(
        self,
        app,
        rate_limiter: Optional[RateLimiter] = None,
        excluded_paths: Optional[list] = None,
    ):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance (creates default if None)
            excluded_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)

        self.rate_limiter = rate_limiter or RateLimiter()

        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
        ]

        logger.info(
            f"Rate limit middleware initialized (excluded: {self.excluded_paths})"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response (429 if rate limited, otherwise from next middleware)
        """
        path = request.url.path

        # Check if path is excluded
        if self._is_excluded(path):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(client_ip, path)

        if not allowed:
            # Return 429 Too Many Requests
            return self._rate_limit_response(retry_after)

        # Add rate limit headers
        response = await call_next(request)
        self._add_rate_limit_headers(response, client_ip, path)

        return response

    def _is_excluded(self, path: str) -> bool:
        """Check if path is excluded from rate limiting.

        Args:
            path: Request path

        Returns:
            True if path should be excluded
        """
        for excluded in self.excluded_paths:
            if path == excluded or path.startswith(excluded + "/"):
                return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request.

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()

        # Fall back to direct client host
        if request.client:
            return request.client.host

        return "unknown"

    def _rate_limit_response(self, retry_after: Optional[float]) -> JSONResponse:
        """Create rate limit exceeded response.

        Args:
            retry_after: Seconds to wait before retrying

        Returns:
            429 JSON response
        """
        retry_after_int = int(retry_after) + 1 if retry_after else 60

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after_int,
            },
            headers={
                "Retry-After": str(retry_after_int),
                "X-RateLimit-Limit": str(self.rate_limiter.default_config.max_requests),
                "X-RateLimit-Remaining": "0",
            },
        )

    def _add_rate_limit_headers(self, response: Response, ip: str, path: str) -> None:
        """Add rate limit headers to response.

        Args:
            response: Response object
            ip: Client IP
            path: Request path
        """
        bucket = self.rate_limiter._get_bucket(ip, path)
        config = self.rate_limiter._get_config_for_path(path)

        response.headers["X-RateLimit-Limit"] = str(config.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        response.headers["X-RateLimit-Reset"] = str(
            int(bucket.last_refill + config.window_seconds)
        )


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()

        # Add marketplace-specific limits
        _global_rate_limiter.add_endpoint_limit(
            path_pattern="/api/v1/marketplace/listings*",
            max_requests=100,
            window_seconds=3600,  # 100 per hour
        )
        _global_rate_limiter.add_endpoint_limit(
            path_pattern="/api/v1/marketplace/install",
            max_requests=10,
            window_seconds=3600,  # 10 per hour
        )
        _global_rate_limiter.add_endpoint_limit(
            path_pattern="/api/v1/marketplace/publish",
            max_requests=10,
            window_seconds=3600,  # 10 per hour
        )

        # Analytics endpoints - higher limits (read-only, low cost)
        _global_rate_limiter.add_endpoint_limit(
            path_pattern="/api/v1/analytics*",
            max_requests=1000,
            window_seconds=3600,  # 1000 per hour
        )

    return _global_rate_limiter
