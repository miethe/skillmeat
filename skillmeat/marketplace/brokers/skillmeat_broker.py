"""SkillMeat Official Marketplace broker.

Implements marketplace integration with the official SkillMeat marketplace.
Supports listing, downloading, and publishing bundles with full signature validation.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.sharing.bundle import Bundle
from skillmeat.core.sharing.builder import inspect_bundle
from skillmeat.core.signing import BundleSigner, KeyManager

from ..broker import (
    DownloadError,
    MarketplaceBroker,
    MarketplaceBrokerError,
    PublishError,
    RateLimitConfig,
    ValidationError,
)
from ..models import MarketplaceListing, PublishResult

logger = logging.getLogger(__name__)


class SkillMeatMarketplaceBroker(MarketplaceBroker):
    """Official SkillMeat marketplace broker.

    Provides full read/write access to the official SkillMeat marketplace:
    - Browse paginated listings with filters
    - Download bundles with signature verification
    - Publish bundles with submission tracking
    - Automatic signature generation for uploads
    """

    def __init__(
        self,
        name: str = "skillmeat",
        endpoint: str = "https://marketplace.skillmeat.dev/api",
        rate_limit: Optional[RateLimitConfig] = None,
        cache_ttl: int = 300,
        key_manager: Optional[KeyManager] = None,
    ):
        """Initialize SkillMeat marketplace broker.

        Args:
            name: Broker name
            endpoint: Marketplace API endpoint
            rate_limit: Rate limiting configuration
            cache_ttl: Cache time-to-live in seconds
            key_manager: Key manager for signing/verification
        """
        super().__init__(
            name=name,
            endpoint=endpoint,
            rate_limit=rate_limit,
            cache_ttl=cache_ttl,
            key_manager=key_manager,
        )

    def listings(
        self,
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[MarketplaceListing]:
        """Fetch paginated marketplace listings.

        Args:
            filters: Optional filters:
                - tags: List[str] - Filter by tags
                - license: str - Filter by license
                - price_max: int - Maximum price in cents
                - publisher: str - Filter by publisher
                - query: str - Search query
            page: Page number (1-indexed)
            page_size: Number of results per page (max 100)

        Returns:
            List of MarketplaceListing objects

        Raises:
            MarketplaceBrokerError: If listing fetch fails
        """
        filters = filters or {}

        # Validate pagination
        if page < 1:
            raise MarketplaceBrokerError(f"Invalid page number: {page}")

        if page_size < 1 or page_size > 100:
            raise MarketplaceBrokerError(
                f"Invalid page_size: {page_size} (must be 1-100)"
            )

        # Build query parameters
        params = {
            "page": page,
            "page_size": page_size,
        }

        # Add filters
        if "tags" in filters:
            params["tags"] = ",".join(filters["tags"])

        if "license" in filters:
            params["license"] = filters["license"]

        if "price_max" in filters:
            params["price_max"] = filters["price_max"]

        if "publisher" in filters:
            params["publisher"] = filters["publisher"]

        if "query" in filters:
            params["q"] = filters["query"]

        # Make request
        url = f"{self.endpoint}/listings"
        cache_key = f"listings:{page}:{page_size}:{str(filters)}"

        try:
            response = self._make_request(
                "GET", url, cache_key=cache_key, params=params
            )
            data = response.json()

            # Parse listings
            listings = []
            for item in data.get("listings", []):
                try:
                    listing = MarketplaceListing.from_dict(item)
                    listings.append(listing)
                except Exception as e:
                    logger.warning(f"Failed to parse listing: {e}")
                    continue

            logger.info(
                f"Fetched {len(listings)} listings from SkillMeat marketplace "
                f"(page {page}/{data.get('total_pages', '?')})"
            )

            return listings

        except Exception as e:
            raise MarketplaceBrokerError(f"Failed to fetch listings: {e}") from e

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
        if not listing_id:
            raise DownloadError("listing_id cannot be empty")

        # Get listing details
        url = f"{self.endpoint}/listings/{listing_id}"

        try:
            response = self._make_request("GET", url)
            listing_data = response.json()
            listing = MarketplaceListing.from_dict(listing_data)

        except Exception as e:
            raise DownloadError(f"Failed to fetch listing details: {e}") from e

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="skillmeat-marketplace-"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Download bundle
        bundle_path = output_dir / f"{listing_id}.skillmeat-pack"

        try:
            logger.info(f"Downloading bundle from {listing.bundle_url}")
            response = self._make_request("GET", listing.bundle_url, stream=True)

            # Stream download to file
            with open(bundle_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded bundle to {bundle_path}")

        except Exception as e:
            raise DownloadError(f"Failed to download bundle: {e}") from e

        # Verify bundle hash if signature present
        if listing.is_signed:
            try:
                # Inspect bundle to get hash
                bundle = inspect_bundle(bundle_path)

                if bundle.bundle_hash:
                    # Verify signature
                    self.validate_signature(bundle)
                    logger.info("Bundle signature verified successfully")
                else:
                    logger.warning("Bundle has no hash - signature not verified")

            except Exception as e:
                # Clean up downloaded file on validation failure
                bundle_path.unlink(missing_ok=True)
                raise ValidationError(f"Bundle validation failed: {e}") from e

        return bundle_path

    def publish(
        self,
        bundle: Bundle,
        metadata: Optional[Dict] = None,
    ) -> PublishResult:
        """Publish bundle to marketplace.

        Args:
            bundle: Bundle to publish (must have bundle_path set)
            metadata: Optional additional metadata:
                - description: str - Detailed description
                - tags: List[str] - Tags for categorization
                - homepage: str - Project homepage URL
                - repository: str - Source repository URL
                - price: int - Price in cents (0 for free)

        Returns:
            PublishResult with submission details

        Raises:
            PublishError: If publishing fails
            ValidationError: If bundle validation fails
        """
        metadata = metadata or {}

        # Validate bundle
        if not bundle.bundle_path:
            raise PublishError("Bundle must have bundle_path set")

        if not bundle.bundle_path.exists():
            raise PublishError(f"Bundle file not found: {bundle.bundle_path}")

        # Sign bundle if not already signed
        if not hasattr(bundle, "signature") or not bundle.signature:
            logger.info("Bundle not signed - signing with default key")
            try:
                signer = BundleSigner(self.key_manager)
                manifest_dict = bundle.to_dict()
                signature_data = signer.sign_bundle(bundle.bundle_hash, manifest_dict)
                bundle.signature = signature_data
                logger.info("Bundle signed successfully")
            except Exception as e:
                raise PublishError(f"Failed to sign bundle: {e}") from e

        # Prepare upload data
        upload_data = {
            "name": bundle.metadata.name,
            "description": metadata.get("description", bundle.metadata.description),
            "author": bundle.metadata.author,
            "license": bundle.metadata.license,
            "version": bundle.metadata.version,
            "tags": metadata.get("tags", bundle.metadata.tags),
            "artifact_count": bundle.artifact_count,
            "homepage": metadata.get("homepage", bundle.metadata.homepage),
            "repository": metadata.get("repository", bundle.metadata.repository),
            "price": metadata.get("price", 0),
        }

        # Upload bundle file
        url = f"{self.endpoint}/publish"

        try:
            with open(bundle.bundle_path, "rb") as f:
                files = {"bundle": (bundle.bundle_path.name, f, "application/zip")}

                response = self._make_request(
                    "POST",
                    url,
                    data=upload_data,
                    files=files,
                )

            result_data = response.json()

            # Parse publish result
            publish_result = PublishResult.from_dict(result_data)

            logger.info(
                f"Bundle published successfully: {publish_result.submission_id} "
                f"(status: {publish_result.status})"
            )

            return publish_result

        except Exception as e:
            raise PublishError(f"Failed to publish bundle: {e}") from e
