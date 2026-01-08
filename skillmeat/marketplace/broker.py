"""Base marketplace broker class and utilities.

Defines the abstract base class for marketplace brokers with methods for
listing, downloading, publishing, and validating bundles.
"""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import requests

from skillmeat.core.sharing.bundle import Bundle
from skillmeat.core.signing import BundleVerifier, KeyManager, VerificationStatus

from .models import MarketplaceListing, PublishResult

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration.

    Attributes:
        max_requests: Maximum requests allowed in time window
        time_window: Time window in seconds
        retry_after: Seconds to wait after rate limit hit
    """

    max_requests: int = 100
    time_window: int = 60  # seconds
    retry_after: int = 60  # seconds


@dataclass
class CacheEntry:
    """Cache entry for HTTP responses.

    Attributes:
        data: Cached data
        etag: ETag header value for cache validation
        timestamp: Timestamp when cached
        ttl: Time-to-live in seconds
    """

    data: any
    etag: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300  # 5 minutes default

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if cache entry is expired
        """
        return time.time() - self.timestamp > self.ttl


class MarketplaceBrokerError(Exception):
    """Base exception for marketplace broker errors."""

    pass


class RateLimitError(MarketplaceBrokerError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message)
        self.retry_after = retry_after


class ValidationError(MarketplaceBrokerError):
    """Raised when bundle validation fails."""

    pass


class DownloadError(MarketplaceBrokerError):
    """Raised when bundle download fails."""

    pass


class PublishError(MarketplaceBrokerError):
    """Raised when bundle publishing fails."""

    pass


class MarketplaceBroker(ABC):
    """Abstract base class for marketplace brokers.

    Provides the interface for interacting with marketplace platforms,
    including listing artifacts, downloading bundles, publishing bundles,
    and validating signatures.

    Subclasses must implement:
    - listings(): Fetch paginated listings
    - download(): Download bundle to temp location
    - publish(): Publish bundle to marketplace
    - _fetch_listings(): Platform-specific listing fetch logic
    """

    def __init__(
        self,
        name: str,
        endpoint: str,
        rate_limit: Optional[RateLimitConfig] = None,
        cache_ttl: int = 300,
        key_manager: Optional[KeyManager] = None,
    ):
        """Initialize marketplace broker.

        Args:
            name: Broker name (e.g., "skillmeat", "claudehub")
            endpoint: Base endpoint URL for the marketplace API
            rate_limit: Rate limiting configuration
            cache_ttl: Cache time-to-live in seconds (default: 5 minutes)
            key_manager: Key manager for signature verification
        """
        self.name = name
        self.endpoint = endpoint.rstrip("/")
        self.rate_limit = rate_limit or RateLimitConfig()
        self.cache_ttl = cache_ttl
        self.key_manager = key_manager or KeyManager()

        # Rate limiting state
        self._request_times: List[float] = []

        # Response cache with ETag support
        self._cache: Dict[str, CacheEntry] = {}

        # HTTP session with retry logic
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "SkillMeat/1.0",
                "Accept": "application/json",
            }
        )

    def _check_rate_limit(self) -> None:
        """Check if rate limit would be exceeded.

        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        now = time.time()

        # Remove requests outside time window
        cutoff = now - self.rate_limit.time_window
        self._request_times = [t for t in self._request_times if t > cutoff]

        # Check if limit exceeded
        if len(self._request_times) >= self.rate_limit.max_requests:
            raise RateLimitError(
                f"Rate limit exceeded: {self.rate_limit.max_requests} requests per {self.rate_limit.time_window}s",
                retry_after=self.rate_limit.retry_after,
            )

        # Record this request
        self._request_times.append(now)

    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached data if not expired.

        Args:
            key: Cache key

        Returns:
            Cached data or None if expired/not found
        """
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                logger.debug(f"Cache hit for {key}")
                return entry.data
            else:
                logger.debug(f"Cache expired for {key}")
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: any, etag: Optional[str] = None) -> None:
        """Set cache entry.

        Args:
            key: Cache key
            data: Data to cache
            etag: Optional ETag header value
        """
        self._cache[key] = CacheEntry(
            data=data, etag=etag, timestamp=time.time(), ttl=self.cache_ttl
        )
        logger.debug(f"Cached data for {key} (ttl={self.cache_ttl}s)")

    def _make_request(
        self,
        method: str,
        url: str,
        cache_key: Optional[str] = None,
        **kwargs,
    ) -> requests.Response:
        """Make HTTP request with rate limiting and caching.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            cache_key: Optional cache key for GET requests
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            RateLimitError: If rate limit exceeded
            requests.RequestException: If request fails
        """
        # Check rate limit
        self._check_rate_limit()

        # Check cache for GET requests
        if method.upper() == "GET" and cache_key:
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                # Create mock response from cached data
                response = requests.Response()
                response.status_code = 200
                response._content = (
                    cached_data.encode()
                    if isinstance(cached_data, str)
                    else cached_data
                )
                return response

            # Add If-None-Match header if we have an ETag
            if cache_key in self._cache and self._cache[cache_key].etag:
                kwargs.setdefault("headers", {})
                kwargs["headers"]["If-None-Match"] = self._cache[cache_key].etag

        # Make request
        logger.debug(f"{method} {url}")
        response = self._session.request(method, url, **kwargs)

        # Handle 304 Not Modified
        if response.status_code == 304 and cache_key:
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                response._content = (
                    cached_data.encode()
                    if isinstance(cached_data, str)
                    else cached_data
                )
                response.status_code = 200
                return response

        # Raise for error status codes
        response.raise_for_status()

        # Cache successful GET requests
        if method.upper() == "GET" and cache_key and response.status_code == 200:
            etag = response.headers.get("ETag")
            self._set_cache(cache_key, response.content, etag)

        return response

    @abstractmethod
    def listings(
        self,
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[MarketplaceListing]:
        """Fetch paginated marketplace listings.

        Args:
            filters: Optional filters (tags, license, price_max, etc.)
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of MarketplaceListing objects

        Raises:
            MarketplaceBrokerError: If listing fetch fails
        """
        pass

    @abstractmethod
    def download(self, listing_id: str, output_dir: Optional[Path] = None) -> Path:
        """Download bundle from marketplace to temp location.

        Args:
            listing_id: Listing ID to download
            output_dir: Optional output directory (uses temp dir if None)

        Returns:
            Path to downloaded bundle file

        Raises:
            DownloadError: If download fails
            ValidationError: If bundle validation fails
        """
        pass

    @abstractmethod
    def publish(
        self,
        bundle: Bundle,
        metadata: Optional[Dict] = None,
    ) -> PublishResult:
        """Publish bundle to marketplace.

        Args:
            bundle: Bundle to publish
            metadata: Optional additional metadata (description, tags, etc.)

        Returns:
            PublishResult with submission details

        Raises:
            PublishError: If publishing fails
            ValidationError: If bundle validation fails
        """
        pass

    def validate_signature(self, bundle: Bundle) -> bool:
        """Verify bundle signature using Ed25519.

        Args:
            bundle: Bundle to validate

        Returns:
            True if signature is valid and key is trusted

        Raises:
            ValidationError: If signature validation fails
        """
        if not bundle.bundle_hash:
            raise ValidationError("Bundle has no hash - cannot validate signature")

        # Create verifier
        verifier = BundleVerifier(self.key_manager)

        # Verify signature
        manifest_dict = bundle.to_dict()
        result = verifier.verify_bundle(
            bundle.bundle_hash, manifest_dict, require_signature=True
        )

        # Check verification result
        if result.status == VerificationStatus.UNSIGNED:
            raise ValidationError("Bundle is not signed")

        if result.status == VerificationStatus.INVALID:
            raise ValidationError("Bundle signature is invalid - may be tampered")

        if result.status == VerificationStatus.KEY_NOT_FOUND:
            raise ValidationError(
                f"Signing key not found in trust store: {result.message}"
            )

        if result.status == VerificationStatus.KEY_UNTRUSTED:
            raise ValidationError(f"Signing key is not trusted: {result.message}")

        if result.status == VerificationStatus.TAMPERED:
            raise ValidationError("Bundle has been tampered with")

        if result.status == VerificationStatus.ERROR:
            raise ValidationError(f"Signature verification error: {result.message}")

        if result.status != VerificationStatus.VALID:
            raise ValidationError(f"Signature verification failed: {result.message}")

        logger.info(f"Bundle signature verified: {result.message}")
        return True

    def verify_bundle_hash(self, bundle_path: Path, expected_hash: str) -> bool:
        """Verify bundle file hash matches expected value.

        Args:
            bundle_path: Path to bundle file
            expected_hash: Expected SHA-256 hash (with or without "sha256:" prefix)

        Returns:
            True if hash matches

        Raises:
            ValidationError: If hash doesn't match
        """
        # Remove sha256: prefix if present
        if expected_hash.startswith("sha256:"):
            expected_hash = expected_hash[7:]

        # Compute actual hash
        sha256 = hashlib.sha256()
        with open(bundle_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        actual_hash = sha256.hexdigest()

        # Compare hashes
        if actual_hash != expected_hash:
            raise ValidationError(
                f"Bundle hash mismatch: expected {expected_hash[:8]}..., "
                f"got {actual_hash[:8]}..."
            )

        logger.debug(f"Bundle hash verified: {actual_hash[:8]}...")
        return True

    def close(self) -> None:
        """Close HTTP session and cleanup resources."""
        self._session.close()
        logger.debug(f"Broker {self.name} session closed")
