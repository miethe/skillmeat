"""Custom web marketplace broker.

Implements marketplace integration with user-supplied custom endpoints.
Supports JSON schema validation for endpoint compatibility.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from jsonschema import ValidationError as JSONValidationError
from jsonschema import validate

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


# Default JSON schema for custom broker endpoints
DEFAULT_LISTING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["listings"],
    "properties": {
        "listings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "listing_id",
                    "name",
                    "publisher",
                    "source_url",
                    "bundle_url",
                ],
                "properties": {
                    "listing_id": {"type": "string"},
                    "name": {"type": "string"},
                    "publisher": {"type": "string"},
                    "license": {"type": "string"},
                    "artifact_count": {"type": "integer"},
                    "price": {"type": "integer"},
                    "signature": {"type": "string"},
                    "source_url": {"type": "string"},
                    "bundle_url": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "version": {"type": "string"},
                    "homepage": {"type": "string"},
                    "repository": {"type": "string"},
                    "downloads": {"type": "integer"},
                    "rating": {"type": "number"},
                    "created_at": {"type": "string"},
                },
            },
        },
        "total_count": {"type": "integer"},
        "page": {"type": "integer"},
        "page_size": {"type": "integer"},
        "total_pages": {"type": "integer"},
    },
}


class CustomWebBroker(MarketplaceBroker):
    """Custom web endpoint marketplace broker.

    Provides marketplace integration with custom web endpoints:
    - Configurable endpoint URL
    - JSON schema validation for compatibility
    - Flexible listing/download/publish support
    - Schema URL for endpoint validation
    """

    def __init__(
        self,
        name: str = "custom",
        endpoint: str = "",
        schema_url: Optional[str] = None,
        rate_limit: Optional[RateLimitConfig] = None,
        cache_ttl: int = 300,
        key_manager: Optional[KeyManager] = None,
    ):
        """Initialize custom web broker.

        Args:
            name: Broker name
            endpoint: Custom marketplace API endpoint
            schema_url: Optional URL to JSON schema for validation
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

        self.schema_url = schema_url
        self._listing_schema = None

        # Load schema if URL provided
        if schema_url:
            self._load_schema()

    def _load_schema(self) -> None:
        """Load JSON schema from URL.

        Raises:
            MarketplaceBrokerError: If schema loading fails
        """
        if not self.schema_url:
            logger.debug("No schema URL provided, using default schema")
            self._listing_schema = DEFAULT_LISTING_SCHEMA
            return

        try:
            logger.info(f"Loading schema from {self.schema_url}")
            response = self._make_request("GET", self.schema_url)
            self._listing_schema = response.json()

            # Validate that it's a valid schema
            # (basic check - just ensure it's a dict with required fields)
            if not isinstance(self._listing_schema, dict):
                raise ValueError("Schema must be a JSON object")

            logger.info("Schema loaded successfully")

        except Exception as e:
            logger.warning(f"Failed to load schema, using default: {e}")
            self._listing_schema = DEFAULT_LISTING_SCHEMA

    def _validate_response(self, data: Dict, schema: Optional[Dict] = None) -> None:
        """Validate response data against JSON schema.

        Args:
            data: Response data to validate
            schema: Optional schema (uses listing schema if None)

        Raises:
            MarketplaceBrokerError: If validation fails
        """
        if schema is None:
            schema = self._listing_schema or DEFAULT_LISTING_SCHEMA

        try:
            validate(instance=data, schema=schema)
        except JSONValidationError as e:
            raise MarketplaceBrokerError(
                f"Response validation failed: {e.message}"
            ) from e

    def listings(
        self,
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[MarketplaceListing]:
        """Fetch paginated marketplace listings.

        Args:
            filters: Optional filters (endpoint-specific)
            page: Page number (1-indexed)
            page_size: Number of results per page

        Returns:
            List of MarketplaceListing objects

        Raises:
            MarketplaceBrokerError: If listing fetch fails
        """
        filters = filters or {}

        # Validate pagination
        if page < 1:
            raise MarketplaceBrokerError(f"Invalid page number: {page}")

        if page_size < 1:
            raise MarketplaceBrokerError(f"Invalid page_size: {page_size}")

        # Build query parameters
        params = {
            "page": page,
            "page_size": page_size,
        }

        # Add all filters as query params
        params.update(filters)

        # Make request
        url = f"{self.endpoint}/listings"
        cache_key = f"listings:{page}:{page_size}:{str(filters)}"

        try:
            response = self._make_request(
                "GET", url, cache_key=cache_key, params=params
            )
            data = response.json()

            # Validate response against schema
            self._validate_response(data)

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
                f"Fetched {len(listings)} listings from custom broker "
                f"(page {page}/{data.get('total_pages', '?')})"
            )

            return listings

        except Exception as e:
            raise MarketplaceBrokerError(f"Failed to fetch listings: {e}") from e

    def download(self, listing_id: str, output_dir: Optional[Path] = None) -> Path:
        """Download bundle from custom marketplace.

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
            output_dir = Path(tempfile.mkdtemp(prefix="skillmeat-custom-"))
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

        # Verify bundle if signature present
        if listing.is_signed:
            try:
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
        """Publish bundle to custom marketplace.

        Args:
            bundle: Bundle to publish (must have bundle_path set)
            metadata: Optional additional metadata (endpoint-specific)

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
            "description": bundle.metadata.description,
            "author": bundle.metadata.author,
            "license": bundle.metadata.license,
            "version": bundle.metadata.version,
            "tags": bundle.metadata.tags,
            "artifact_count": bundle.artifact_count,
        }

        # Add custom metadata
        upload_data.update(metadata)

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
                f"Bundle published successfully to custom broker: "
                f"{publish_result.submission_id} (status: {publish_result.status})"
            )

            return publish_result

        except Exception as e:
            raise PublishError(f"Failed to publish bundle: {e}") from e
