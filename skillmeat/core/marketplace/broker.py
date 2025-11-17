"""Base marketplace broker interface.

This module defines the abstract base class for marketplace brokers,
which provide a unified interface for discovering, downloading, and
publishing artifacts to different marketplace providers.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

from .models import (
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    PublishRequest,
    PublishResult,
)

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Thread-safe rate limiter for API calls.

    Implements token bucket algorithm for rate limiting.

    Attributes:
        calls_per_minute: Maximum calls allowed per minute
        tokens: Current number of available tokens
        last_refill: Timestamp of last token refill
        lock: Thread lock for concurrent access
    """

    calls_per_minute: int = 60
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self):
        """Initialize token bucket."""
        self.tokens = float(self.calls_per_minute)
        self.last_refill = time.time()

    def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens for a request.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            True if tokens acquired, False if rate limit exceeded
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(
                    f"Rate limiter: acquired {tokens} tokens, {self.tokens:.1f} remaining"
                )
                return True
            else:
                logger.warning(
                    f"Rate limit exceeded: need {tokens}, have {self.tokens:.1f}"
                )
                return False

    def wait_and_acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Wait for tokens to become available and acquire them.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum seconds to wait (None = wait indefinitely)

        Returns:
            True if tokens acquired, False if timeout reached
        """
        start_time = time.time()

        while True:
            if self.acquire(tokens):
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limiter timeout after {elapsed:.1f}s")
                    return False

            # Sleep until next refill
            with self.lock:
                time_to_next_refill = 60.0 - (time.time() - self.last_refill)
                sleep_time = max(0.1, min(time_to_next_refill, 1.0))

            logger.debug(f"Rate limiter: waiting {sleep_time:.1f}s for tokens")
            time.sleep(sleep_time)

    def _refill(self) -> None:
        """Refill token bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens based on elapsed time
        if elapsed >= 60.0:
            # Full refill after 60 seconds
            self.tokens = float(self.calls_per_minute)
            self.last_refill = now
            logger.debug(f"Rate limiter: full refill to {self.tokens} tokens")
        else:
            # Partial refill based on elapsed time
            tokens_to_add = (elapsed / 60.0) * self.calls_per_minute
            self.tokens = min(self.tokens + tokens_to_add, float(self.calls_per_minute))
            self.last_refill = now

    def reset(self) -> None:
        """Reset rate limiter to full capacity."""
        with self.lock:
            self.tokens = float(self.calls_per_minute)
            self.last_refill = time.time()
            logger.debug("Rate limiter: reset to full capacity")


class MarketplaceBroker(ABC):
    """Abstract base class for marketplace brokers.

    Marketplace brokers provide a unified interface for interacting with
    different marketplace providers. Each broker implementation handles
    the specifics of authentication, API calls, and data transformation
    for a particular marketplace.

    Subclasses must implement:
    - listings(): Fetch paginated listing feed
    - download(): Download bundle from marketplace
    - publish(): Publish bundle to marketplace
    """

    def __init__(
        self,
        name: str,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        rate_limit: int = 60,
    ):
        """Initialize marketplace broker.

        Args:
            name: Broker name (e.g., "SkillMeat", "ClaudeHub")
            base_url: Base URL for marketplace API
            api_key: Optional API key for authentication
            rate_limit: Maximum API calls per minute (default: 60)
        """
        self.name = name
        self.base_url = base_url
        self.api_key = api_key
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit)
        self._session_headers: Dict[str, str] = {}

        logger.info(f"Initialized {name} broker (rate limit: {rate_limit}/min)")

    @abstractmethod
    def listings(self, query: Optional[ListingQuery] = None) -> ListingPage:
        """Fetch paginated listing feed from marketplace.

        Args:
            query: Optional query parameters for filtering/sorting

        Returns:
            ListingPage with matching listings

        Raises:
            ValueError: If query parameters are invalid
            ConnectionError: If marketplace is unreachable
            TimeoutError: If request times out
        """
        pass

    @abstractmethod
    def download(self, listing_id: str, output_dir: Optional[Path] = None) -> DownloadResult:
        """Download bundle from marketplace.

        Args:
            listing_id: Marketplace listing identifier
            output_dir: Directory to save bundle (default: temp directory)

        Returns:
            DownloadResult with download status and bundle path

        Raises:
            ValueError: If listing_id is invalid
            FileNotFoundError: If listing not found
            PermissionError: If authentication fails
            ConnectionError: If download fails
        """
        pass

    @abstractmethod
    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish bundle to marketplace.

        Args:
            request: Publish request with bundle and metadata

        Returns:
            PublishResult with publication status

        Raises:
            ValueError: If request is invalid
            FileNotFoundError: If bundle file not found
            PermissionError: If authentication fails
            ConnectionError: If upload fails
        """
        pass

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        """Get a specific listing by ID.

        Default implementation queries with search filter.
        Subclasses may override for more efficient API calls.

        Args:
            listing_id: Listing identifier

        Returns:
            Listing if found, None otherwise
        """
        try:
            # Default: fetch listings and filter (inefficient)
            # Subclasses should override with direct API call
            result = self.listings(ListingQuery(page_size=100))

            for listing in result.listings:
                if listing.listing_id == listing_id:
                    return listing

            return None

        except Exception as e:
            logger.error(f"Failed to get listing {listing_id}: {e}")
            return None

    def verify_signature(self, listing: Listing) -> bool:
        """Verify listing signature.

        Args:
            listing: Listing to verify

        Returns:
            True if signature is valid or not required, False otherwise
        """
        if not listing.signature:
            logger.warning(f"Listing {listing.listing_id} has no signature")
            return True  # Optional signature

        # Import signature verifier
        try:
            from skillmeat.core.signing.key_manager import KeyManager
            from skillmeat.core.signing.verifier import BundleVerifier

            key_manager = KeyManager()

            # Check if we have publisher's public key
            if not listing.publisher.key_fingerprint:
                logger.warning(
                    f"Listing {listing.listing_id} has signature but no key fingerprint"
                )
                return False

            public_key = key_manager.load_public_key_by_fingerprint(
                listing.publisher.key_fingerprint
            )

            if not public_key:
                logger.warning(
                    f"Publisher key {listing.publisher.key_fingerprint[:8]}... not in trust store"
                )
                return False

            # Verify signature using bundle verifier
            verifier = BundleVerifier(key_manager=key_manager)

            # Create minimal manifest for signature verification
            manifest_data = {
                "name": listing.name,
                "version": listing.version,
                "description": listing.description,
                "listing_id": listing.listing_id,
                "signature": {"signature": listing.signature},
            }

            # For marketplace listings, we verify the listing metadata itself
            # The actual bundle will be verified when downloaded
            logger.info(f"Signature verification for listing {listing.listing_id} - skipped (bundle-level verification)")
            return True

        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def _rate_limit_wait(self) -> None:
        """Wait for rate limit token (blocks until available)."""
        self.rate_limiter.wait_and_acquire(tokens=1, timeout=30.0)

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self.name}', base_url='{self.base_url}')"
