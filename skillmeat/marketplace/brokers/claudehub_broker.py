"""Claude Hub marketplace broker.

Implements read-only integration with Claude Hub public catalogs.
Supports browsing and downloading artifacts, but not publishing.
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.sharing.bundle import Bundle
from skillmeat.core.sharing.builder import inspect_bundle
from skillmeat.core.signing import KeyManager

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


class ClaudeHubBroker(MarketplaceBroker):
    """Claude Hub public catalog broker.

    Provides read-only access to Claude Hub public catalogs:
    - Browse public artifact listings
    - Download artifacts in SkillMeat-compatible format
    - Transform Claude format to SkillMeat format
    - No publishing support (read-only)
    """

    def __init__(
        self,
        name: str = "claudehub",
        endpoint: str = "https://claude.ai/marketplace/api",
        rate_limit: Optional[RateLimitConfig] = None,
        cache_ttl: int = 300,
        key_manager: Optional[KeyManager] = None,
    ):
        """Initialize Claude Hub broker.

        Args:
            name: Broker name
            endpoint: Claude Hub API endpoint
            rate_limit: Rate limiting configuration
            cache_ttl: Cache time-to-live in seconds
            key_manager: Key manager for verification
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
                - category: str - Filter by category
                - query: str - Search query
            page: Page number (1-indexed)
            page_size: Number of results per page (max 50)

        Returns:
            List of MarketplaceListing objects transformed from Claude format

        Raises:
            MarketplaceBrokerError: If listing fetch fails
        """
        filters = filters or {}

        # Validate pagination
        if page < 1:
            raise MarketplaceBrokerError(f"Invalid page number: {page}")

        if page_size < 1 or page_size > 50:
            raise MarketplaceBrokerError(
                f"Invalid page_size: {page_size} (must be 1-50)"
            )

        # Build query parameters (Claude Hub API format)
        params = {
            "page": page,
            "limit": page_size,
        }

        # Add filters
        if "tags" in filters:
            params["tags"] = ",".join(filters["tags"])

        if "category" in filters:
            params["category"] = filters["category"]

        if "query" in filters:
            params["search"] = filters["query"]

        # Make request
        url = f"{self.endpoint}/artifacts"
        cache_key = f"listings:{page}:{page_size}:{str(filters)}"

        try:
            response = self._make_request(
                "GET", url, cache_key=cache_key, params=params
            )
            data = response.json()

            # Transform Claude Hub format to SkillMeat format
            listings = []
            for item in data.get("artifacts", []):
                try:
                    listing = self._transform_claude_to_skillmeat(item)
                    listings.append(listing)
                except Exception as e:
                    logger.warning(f"Failed to transform Claude listing: {e}")
                    continue

            logger.info(
                f"Fetched {len(listings)} listings from Claude Hub "
                f"(page {page}/{data.get('total_pages', '?')})"
            )

            return listings

        except Exception as e:
            raise MarketplaceBrokerError(
                f"Failed to fetch Claude Hub listings: {e}"
            ) from e

    def _transform_claude_to_skillmeat(self, claude_item: Dict) -> MarketplaceListing:
        """Transform Claude Hub artifact format to SkillMeat listing format.

        Args:
            claude_item: Claude Hub artifact data

        Returns:
            MarketplaceListing object

        Raises:
            ValueError: If required fields are missing
        """
        # Claude Hub format typically has:
        # - id, name, description, author, category, tags, download_url
        # Transform to SkillMeat format

        # Parse created_at timestamp
        created_at = None
        if "created_at" in claude_item:
            try:
                created_at = datetime.fromisoformat(claude_item["created_at"])
            except Exception:
                pass

        return MarketplaceListing(
            listing_id=f"claudehub-{claude_item['id']}",
            name=claude_item.get("name", "Unknown"),
            publisher=claude_item.get("author", "Unknown"),
            license=claude_item.get("license", "Unknown"),
            artifact_count=1,  # Claude Hub typically has single artifacts
            price=0,  # Claude Hub is free
            signature="",  # Claude Hub doesn't provide signatures
            source_url=claude_item.get("url", ""),
            bundle_url=claude_item.get("download_url", ""),
            tags=claude_item.get("tags", []),
            created_at=created_at,
            description=claude_item.get("description"),
            version=claude_item.get("version"),
            homepage=claude_item.get("homepage"),
            repository=claude_item.get("repository"),
            downloads=claude_item.get("download_count"),
            rating=claude_item.get("rating"),
        )

    def download(self, listing_id: str, output_dir: Optional[Path] = None) -> Path:
        """Download artifact from Claude Hub.

        Args:
            listing_id: Listing ID to download (format: "claudehub-{id}")
            output_dir: Optional output directory (uses temp dir if None)

        Returns:
            Path to downloaded artifact (converted to SkillMeat format if needed)

        Raises:
            DownloadError: If download fails
            ValidationError: If artifact validation fails
        """
        if not listing_id:
            raise DownloadError("listing_id cannot be empty")

        # Extract Claude artifact ID
        if not listing_id.startswith("claudehub-"):
            raise DownloadError(
                f"Invalid Claude Hub listing_id: {listing_id} "
                "(must start with 'claudehub-')"
            )

        claude_id = listing_id[len("claudehub-") :]

        # Get artifact details
        url = f"{self.endpoint}/artifacts/{claude_id}"

        try:
            response = self._make_request("GET", url)
            artifact_data = response.json()

        except Exception as e:
            raise DownloadError(f"Failed to fetch artifact details: {e}") from e

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="skillmeat-claudehub-"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Download artifact
        download_url = artifact_data.get("download_url")
        if not download_url:
            raise DownloadError("Artifact has no download URL")

        artifact_path = output_dir / f"{claude_id}.zip"

        try:
            logger.info(f"Downloading artifact from {download_url}")
            response = self._make_request("GET", download_url, stream=True)

            # Stream download to file
            with open(artifact_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded artifact to {artifact_path}")

        except Exception as e:
            raise DownloadError(f"Failed to download artifact: {e}") from e

        # Note: Claude Hub artifacts may need format conversion
        # For now, we assume they're compatible or handle conversion elsewhere

        return artifact_path

    def publish(
        self,
        bundle: Bundle,
        metadata: Optional[Dict] = None,
    ) -> PublishResult:
        """Publishing is not supported for Claude Hub (read-only).

        Args:
            bundle: Bundle to publish
            metadata: Optional metadata

        Raises:
            PublishError: Always raises (not supported)
        """
        raise PublishError(
            "Publishing to Claude Hub is not supported. "
            "Claude Hub is a read-only marketplace. "
            "To publish artifacts, use the SkillMeat marketplace or a custom broker."
        )
