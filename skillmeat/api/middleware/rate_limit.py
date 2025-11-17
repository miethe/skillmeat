"""Rate limiting middleware for SkillMeat API.

Provides IP-based and token-based rate limiting with sliding window algorithm.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Dict, Optional, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class RateLimitWindow:
    """Sliding window rate limit tracker.

    Attributes:
        requests: List of request timestamps in current window
        window_start: Start time of current window
        limit: Maximum requests per window
        window_seconds: Window duration in seconds
    """

    requests: list = field(default_factory=list)
    window_start: float = field(default_factory=time.time)
    limit: int = 60
    window_seconds: int = 60

    def is_allowed(self) -> bool:
        """Check if request is allowed within rate limit.

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()

        # Remove requests outside the current window
        self.requests = [ts for ts in self.requests if now - ts < self.window_seconds]

        # Check if limit exceeded
        if len(self.requests) >= self.limit:
            return False

        # Add current request
        self.requests.append(now)
        return True

    def get_remaining(self) -> int:
        """Get remaining requests in current window.

        Returns:
            Number of remaining requests
        """
        now = time.time()
        self.requests = [ts for ts in self.requests if now - ts < self.window_seconds]
        return max(0, self.limit - len(self.requests))

    def get_reset_time(self) -> int:
        """Get Unix timestamp when rate limit resets.

        Returns:
            Reset timestamp
        """
        if not self.requests:
            return int(time.time() + self.window_seconds)

        # Reset time is when oldest request expires
        oldest_request = min(self.requests)
        return int(oldest_request + self.window_seconds)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with IP and token-based limits.

    Implements sliding window rate limiting with different limits for:
    - Public endpoints (IP-based): 60 requests/minute
    - Authenticated endpoints (token-based): 300 requests/minute

    Rate limit headers are added to all responses:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Requests remaining in window
    - X-RateLimit-Reset: Unix timestamp when limit resets

    Attributes:
        public_limit: Requests per minute for public endpoints
        authenticated_limit: Requests per minute for authenticated endpoints
        window_seconds: Rate limit window duration
        excluded_paths: Paths excluded from rate limiting
    """

    def __init__(
        self,
        app,
        public_limit: int = 60,
        authenticated_limit: int = 300,
        window_seconds: int = 60,
        excluded_paths: Optional[list] = None,
    ):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            public_limit: Max requests/window for public endpoints (default: 60)
            authenticated_limit: Max requests/window for authenticated (default: 300)
            window_seconds: Rate limit window in seconds (default: 60)
            excluded_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)

        self.public_limit = public_limit
        self.authenticated_limit = authenticated_limit
        self.window_seconds = window_seconds

        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
        ]

        # Rate limit tracking (IP -> RateLimitWindow)
        self._ip_limits: Dict[str, RateLimitWindow] = defaultdict(
            lambda: RateLimitWindow(
                limit=self.public_limit, window_seconds=self.window_seconds
            )
        )

        # Token-based limits (token -> RateLimitWindow)
        self._token_limits: Dict[str, RateLimitWindow] = defaultdict(
            lambda: RateLimitWindow(
                limit=self.authenticated_limit, window_seconds=self.window_seconds
            )
        )

        self._lock = Lock()

        logger.info(
            f"Rate limit middleware initialized "
            f"(public: {public_limit}/min, authenticated: {authenticated_limit}/min)"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for excluded paths
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # Determine rate limit key (token or IP)
        limit_key, is_authenticated = self._get_limit_key(request)

        # Check rate limit
        with self._lock:
            if is_authenticated:
                window = self._token_limits[limit_key]
            else:
                window = self._ip_limits[limit_key]

            allowed = window.is_allowed()
            remaining = window.get_remaining()
            reset_time = window.get_reset_time()
            limit = window.limit

        # Rate limit exceeded
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {limit_key} "
                f"({'token' if is_authenticated else 'IP'})"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": reset_time - int(time.time()),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time - int(time.time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_limit_key(self, request: Request) -> Tuple[str, bool]:
        """Get rate limit key from request.

        Args:
            request: Incoming request

        Returns:
            Tuple of (limit_key, is_authenticated)
        """
        # Check for bearer token (authenticated)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token[:16], True  # Use first 16 chars of token as key

        # Fall back to IP address (public)
        client_ip = self._get_client_ip(request)
        return client_ip, False

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Checks X-Forwarded-For header for proxy/load balancer support.

        Args:
            request: Incoming request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in chain (original client)
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct connection IP
        if request.client:
            return request.client.host

        return "unknown"

    def _is_excluded(self, path: str) -> bool:
        """Check if path is excluded from rate limiting.

        Args:
            path: Request path

        Returns:
            True if path is excluded
        """
        for excluded in self.excluded_paths:
            if path == excluded or path.startswith(excluded + "/"):
                return True
        return False

    def cleanup_expired(self) -> int:
        """Clean up expired rate limit windows.

        Should be called periodically to prevent memory growth.

        Returns:
            Number of windows cleaned up
        """
        with self._lock:
            now = time.time()
            count = 0

            # Clean up IP limits
            expired_ips = [
                ip
                for ip, window in self._ip_limits.items()
                if all(now - ts > window.window_seconds for ts in window.requests)
            ]
            for ip in expired_ips:
                del self._ip_limits[ip]
                count += 1

            # Clean up token limits
            expired_tokens = [
                token
                for token, window in self._token_limits.items()
                if all(now - ts > window.window_seconds for ts in window.requests)
            ]
            for token in expired_tokens:
                del self._token_limits[token]
                count += 1

            if count > 0:
                logger.debug(f"Cleaned up {count} expired rate limit windows")

            return count

    def get_stats(self) -> dict:
        """Get rate limiting statistics.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                "tracked_ips": len(self._ip_limits),
                "tracked_tokens": len(self._token_limits),
                "public_limit": self.public_limit,
                "authenticated_limit": self.authenticated_limit,
                "window_seconds": self.window_seconds,
            }
