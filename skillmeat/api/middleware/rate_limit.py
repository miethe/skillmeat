"""Rate limiting middleware for API endpoints.

Implements sliding window burst detection for rate limiting with per-IP tracking.

DEPRECATED CLASSES: TokenBucket, RateLimiter, and RateLimitConfig are deprecated
and provided only for backward compatibility. Use SlidingWindowTracker directly.
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Callable, List, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .burst_detection import (
    RequestFingerprint,
    SlidingWindowTracker,
    create_fingerprint,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DEPRECATED CLASSES - For backward compatibility only
# ============================================================================


@dataclass
class RateLimitConfig:
    """DEPRECATED: Use BurstLimitConfig or direct initialization instead.

    This class is provided for backward compatibility only. New code should
    use SlidingWindowTracker directly with appropriate window and threshold
    parameters.

    Raises:
        DeprecationWarning: When instantiated
    """

    requests_per_hour: int = 100

    def __post_init__(self) -> None:
        """Emit deprecation warning on instantiation."""
        warnings.warn(
            "RateLimitConfig is deprecated and will be removed in v1.0. "
            "Use SlidingWindowTracker with appropriate window_seconds and "
            "threshold parameters instead.",
            DeprecationWarning,
            stacklevel=2,
        )


class TokenBucket:
    """DEPRECATED: Replaced by SlidingWindowTracker.

    This class is provided for backward compatibility only. New code should
    use SlidingWindowTracker instead, which implements sliding window burst
    detection with better accuracy.

    Raises:
        DeprecationWarning: When instantiated
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize deprecated TokenBucket.

        Args:
            *args: Ignored (for backward compatibility)
            **kwargs: Ignored (for backward compatibility)
        """
        warnings.warn(
            "TokenBucket is deprecated and will be removed in v1.0. "
            "Use SlidingWindowTracker for burst detection instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def add_tokens(self, *args, **kwargs) -> None:
        """Deprecated method.

        Raises:
            NotImplementedError: This method is no longer supported
        """
        raise NotImplementedError(
            "TokenBucket is deprecated. Use SlidingWindowTracker instead."
        )

    def consume_token(self, *args, **kwargs) -> bool:
        """Deprecated method.

        Raises:
            NotImplementedError: This method is no longer supported
        """
        raise NotImplementedError(
            "TokenBucket is deprecated. Use SlidingWindowTracker instead."
        )

    def get_available_tokens(self, *args, **kwargs) -> int:
        """Deprecated method.

        Raises:
            NotImplementedError: This method is no longer supported
        """
        raise NotImplementedError(
            "TokenBucket is deprecated. Use SlidingWindowTracker instead."
        )


class RateLimiter:
    """DEPRECATED: Use SlidingWindowTracker directly.

    This class is provided for backward compatibility only. New code should
    use SlidingWindowTracker, which implements sliding window burst detection.

    Raises:
        DeprecationWarning: When instantiated
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize deprecated RateLimiter.

        Args:
            *args: Ignored (for backward compatibility)
            **kwargs: Ignored (for backward compatibility)
        """
        warnings.warn(
            "RateLimiter is deprecated and will be removed in v1.0. "
            "Use SlidingWindowTracker for burst detection instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    def is_allowed(self, *args, **kwargs) -> bool:
        """Deprecated method.

        Raises:
            NotImplementedError: This method is no longer supported
        """
        raise NotImplementedError(
            "RateLimiter is deprecated. Use SlidingWindowTracker instead."
        )

    def reset(self, *args, **kwargs) -> None:
        """Deprecated method.

        Raises:
            NotImplementedError: This method is no longer supported
        """
        raise NotImplementedError(
            "RateLimiter is deprecated. Use SlidingWindowTracker instead."
        )


# ============================================================================
# END DEPRECATED CLASSES
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for request rate limiting using sliding window burst detection.

    Applies rate limiting to API endpoints by detecting request bursts within
    a sliding time window. Returns 429 Too Many Requests when burst detected.

    Attributes:
        tracker: SlidingWindowTracker for burst detection
        burst_threshold: Maximum identical requests allowed in window
        block_duration: Seconds to block IP after burst detected
        excluded_paths: Paths to exclude from rate limiting
    """

    def __init__(
        self,
        app,
        window_seconds: int = 10,
        burst_threshold: int = 20,
        block_duration: int = 10,
        excluded_paths: Optional[List[str]] = None,
    ):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            window_seconds: Sliding window size in seconds
            burst_threshold: Max identical requests before burst is triggered
            block_duration: Seconds to block IP after burst
            excluded_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)

        self.tracker = SlidingWindowTracker(window_seconds=window_seconds)
        self.burst_threshold = burst_threshold
        self.block_duration = block_duration

        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
        ]

        logger.info(
            f"Rate limit middleware initialized "
            f"(window={window_seconds}s, threshold={burst_threshold}, "
            f"block={block_duration}s, excluded={self.excluded_paths})"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with burst detection rate limiting.

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

        # Check if IP is currently blocked
        if self.tracker.is_blocked(client_ip):
            logger.warning(f"Blocked request from {client_ip} on {path}")
            return self._rate_limit_response(client_ip, blocked=True)

        # Create fingerprint and track request
        fingerprint = create_fingerprint(request)
        self.tracker.add_request(client_ip, fingerprint)

        # Check for burst
        if self.tracker.detect_burst(client_ip, threshold=self.burst_threshold):
            # Block IP and return 429
            self.tracker.block_ip(client_ip, duration=self.block_duration)
            logger.warning(
                f"Burst detected for {client_ip} on {path} - "
                f"blocking for {self.block_duration}s"
            )
            return self._rate_limit_response(client_ip, blocked=True)

        # Process request normally
        response = await call_next(request)

        # Add rate limit headers to successful responses
        self._add_rate_limit_headers(response, client_ip, fingerprint)

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

    def _get_current_count(self, client_ip: str, fingerprint: RequestFingerprint) -> int:
        """Get current request count for IP/fingerprint in sliding window.

        Args:
            client_ip: Client IP address
            fingerprint: Request fingerprint to count

        Returns:
            Number of requests with this fingerprint in current window
        """
        records = self.tracker.requests.get(client_ip, [])
        return sum(1 for record in records if record.fingerprint == fingerprint)

    def _add_rate_limit_headers(
        self,
        response: Response,
        client_ip: str,
        fingerprint: RequestFingerprint,
    ) -> None:
        """Add rate limit headers to response.

        Headers indicate rate limit status:
        - X-RateLimit-Window: Sliding window size in seconds
        - X-RateLimit-Threshold: Burst detection threshold
        - X-RateLimit-Current: Current request count in window for this IP
        - X-RateLimit-Blocked: Whether IP is currently blocked

        Args:
            response: FastAPI response object
            client_ip: Client IP address
            fingerprint: Current request fingerprint
        """
        current_count = self._get_current_count(client_ip, fingerprint)
        is_blocked = self.tracker.is_blocked(client_ip)

        response.headers["X-RateLimit-Window"] = str(self.tracker.window_seconds)
        response.headers["X-RateLimit-Threshold"] = str(self.burst_threshold)
        response.headers["X-RateLimit-Current"] = str(current_count)
        response.headers["X-RateLimit-Blocked"] = str(is_blocked).lower()

    def _rate_limit_response(self, client_ip: str, blocked: bool = False) -> JSONResponse:
        """Create rate limit exceeded response.

        Args:
            client_ip: Client IP address
            blocked: Whether the IP is blocked

        Returns:
            429 JSON response with rate limit headers
        """
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "retry_after": self.block_duration,
            },
        )

        # Add rate limit headers to 429 response
        response.headers["Retry-After"] = str(self.block_duration)
        response.headers["X-RateLimit-Window"] = str(self.tracker.window_seconds)
        response.headers["X-RateLimit-Threshold"] = str(self.burst_threshold)
        response.headers["X-RateLimit-Current"] = str(self.burst_threshold)
        response.headers["X-RateLimit-Blocked"] = str(blocked).lower()

        return response
