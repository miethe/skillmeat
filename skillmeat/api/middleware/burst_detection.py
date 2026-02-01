"""Burst detection middleware for rate limiting.

Detects and tracks request bursts to prevent overwhelming the server.
"""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

from fastapi import Request


@dataclass
class RequestFingerprint:
    """Unique identifier for request shape.

    A fingerprint combines the endpoint, HTTP method, and a hash of request
    parameters to uniquely identify requests with the same shape. This allows
    burst detection to track identical requests separately from similar but
    distinct requests.

    Attributes:
        endpoint: The URL path (e.g., "/api/v1/artifacts")
        method: HTTP method (e.g., "GET", "POST")
        param_hash: MD5 hash of sorted query/body parameters (first 8 chars)
    """

    endpoint: str
    method: str
    param_hash: str

    def __hash__(self) -> int:
        """Make fingerprint hashable for use as dict key."""
        return hash((self.endpoint, self.method, self.param_hash))

    def __eq__(self, other: Any) -> bool:
        """Compare fingerprints for equality."""
        if not isinstance(other, RequestFingerprint):
            return False
        return (
            self.endpoint == other.endpoint
            and self.method == other.method
            and self.param_hash == other.param_hash
        )


def create_fingerprint(request: Request) -> RequestFingerprint:
    """Create a request fingerprint from a FastAPI request.

    Args:
        request: The FastAPI request object

    Returns:
        RequestFingerprint uniquely identifying the request shape

    Example:
        >>> fingerprint = create_fingerprint(request)
        >>> # Same params always produce same fingerprint
        >>> fingerprint2 = create_fingerprint(request)
        >>> assert fingerprint == fingerprint2
    """
    # Extract endpoint and method
    endpoint = request.url.path
    method = request.method

    # Create sorted string of query parameters for hashing
    # This ensures same params in different order produce same hash
    query_params = sorted(request.query_params.items())
    param_str = "&".join(f"{k}={v}" for k, v in query_params)

    # Generate MD5 hash and take first 8 characters for brevity
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]

    return RequestFingerprint(
        endpoint=endpoint,
        method=method,
        param_hash=param_hash,
    )


@dataclass
class RequestRecord:
    """Single request in sliding window.

    Attributes:
        timestamp: Unix timestamp when the request was made
        fingerprint: The request fingerprint for pattern matching
        ip: Client IP address that made the request
    """

    timestamp: float
    fingerprint: RequestFingerprint
    ip: str


class SlidingWindowTracker:
    """Track requests in sliding time window per IP.

    Provides burst detection by tracking request patterns within a
    configurable time window. Supports temporary IP blocking with
    automatic expiration (QuickReset).

    Attributes:
        window_seconds: Size of the sliding window in seconds
        requests: Mapping of IP addresses to their request records
        blocks: Mapping of IP addresses to block expiration timestamps

    Example:
        >>> tracker = SlidingWindowTracker(window_seconds=10)
        >>> fingerprint = create_fingerprint(request)
        >>> tracker.add_request("192.168.1.1", fingerprint)
        >>> if tracker.detect_burst("192.168.1.1", threshold=20):
        ...     tracker.block_ip("192.168.1.1", duration=10)
    """

    def __init__(self, window_seconds: int = 10) -> None:
        """Initialize the sliding window tracker.

        Args:
            window_seconds: Size of the sliding window in seconds.
                Requests older than this are automatically cleaned.
        """
        self.window_seconds = window_seconds
        # IP -> list of RequestRecords
        self.requests: Dict[str, List[RequestRecord]] = defaultdict(list)
        # IP -> blocked_until timestamp
        self.blocks: Dict[str, float] = {}

    def add_request(self, ip: str, fingerprint: RequestFingerprint) -> None:
        """Add request to tracking window. Auto-cleans old requests.

        Args:
            ip: Client IP address
            fingerprint: The request fingerprint to track
        """
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old requests outside the window
        self.requests[ip] = [
            record for record in self.requests[ip] if record.timestamp > cutoff
        ]

        # Add new request
        self.requests[ip].append(
            RequestRecord(timestamp=now, fingerprint=fingerprint, ip=ip)
        )

    def detect_burst(self, ip: str, threshold: int = 20) -> bool:
        """Check if any fingerprint exceeds threshold count in window.

        Args:
            ip: Client IP address to check
            threshold: Maximum allowed identical requests in window

        Returns:
            True if any fingerprint appears >= threshold times, False otherwise
        """
        records = self.requests.get(ip, [])
        if not records:
            return False

        # Count requests by fingerprint
        fingerprint_counts: Dict[RequestFingerprint, int] = {}
        for record in records:
            fingerprint_counts[record.fingerprint] = (
                fingerprint_counts.get(record.fingerprint, 0) + 1
            )

        # Check if any fingerprint exceeds threshold
        return any(count >= threshold for count in fingerprint_counts.values())

    def is_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked. Auto-clears expired blocks.

        Implements QuickReset (RL-004): Blocks automatically expire and
        are cleaned up when checked, allowing legitimate traffic to
        resume immediately after the block duration.

        Args:
            ip: Client IP address to check

        Returns:
            True if IP is currently blocked, False otherwise
        """
        if ip not in self.blocks:
            return False

        # Check if block has expired (QuickReset - RL-004)
        if time.time() >= self.blocks[ip]:
            # Block expired, clean up and return False
            del self.blocks[ip]
            return False

        return True

    def block_ip(self, ip: str, duration: int = 10) -> None:
        """Block IP for duration seconds.

        Args:
            ip: Client IP address to block
            duration: Block duration in seconds
        """
        self.blocks[ip] = time.time() + duration
