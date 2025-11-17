"""Marketplace service layer.

Business logic for marketplace operations including multi-broker aggregation,
caching, filtering, and sorting of marketplace listings.
"""

import logging
from pathlib import Path
from typing import List, Optional

from skillmeat.core.collection import CollectionManager

from .broker import MarketplaceBroker
from .cache import MarketplaceCache
from .models import (
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    PublishRequest,
    PublishResult,
)

logger = logging.getLogger(__name__)


class MarketplaceService:
    """Service layer for marketplace operations.

    Coordinates between marketplace brokers, caching layer, and business logic
    for discovering, downloading, and publishing artifacts.

    Features:
    - Multi-broker support (aggregate listings from multiple sources)
    - Intelligent caching with ETag support
    - Client-side filtering and sorting
    - Signature verification
    - Collection integration

    Attributes:
        brokers: List of registered marketplace brokers
        cache: Marketplace cache instance
        collection_manager: Optional collection manager for installs
    """

    def __init__(
        self,
        brokers: Optional[List[MarketplaceBroker]] = None,
        cache_ttl: int = 300,
        collection_manager: Optional[CollectionManager] = None,
    ):
        """Initialize marketplace service.

        Args:
            brokers: List of marketplace brokers (default: SkillMeat official)
            cache_ttl: Cache TTL in seconds (default: 300)
            collection_manager: Optional collection manager for installs
        """
        self.brokers = brokers or []
        self.cache = MarketplaceCache(ttl=cache_ttl)
        self.collection_manager = collection_manager

        logger.info(
            f"Initialized marketplace service with {len(self.brokers)} broker(s)"
        )

        # Initialize default broker if none provided
        if not self.brokers:
            self._initialize_default_brokers()

    def _initialize_default_brokers(self) -> None:
        """Initialize default marketplace brokers."""
        try:
            from .brokers.skillmeat import SkillMeatMarketplaceBroker

            broker = SkillMeatMarketplaceBroker()
            self.brokers.append(broker)
            logger.info("Initialized default SkillMeat marketplace broker")

        except Exception as e:
            logger.warning(f"Failed to initialize default broker: {e}")

    def add_broker(self, broker: MarketplaceBroker) -> None:
        """Add a marketplace broker.

        Args:
            broker: Marketplace broker to add
        """
        self.brokers.append(broker)
        logger.info(f"Added marketplace broker: {broker.name}")

    def remove_broker(self, broker_name: str) -> bool:
        """Remove a marketplace broker by name.

        Args:
            broker_name: Name of broker to remove

        Returns:
            True if broker was removed, False if not found
        """
        for i, broker in enumerate(self.brokers):
            if broker.name == broker_name:
                del self.brokers[i]
                logger.info(f"Removed marketplace broker: {broker_name}")
                return True

        logger.warning(f"Broker not found: {broker_name}")
        return False

    def get_listings(
        self,
        query: Optional[ListingQuery] = None,
        if_none_match: Optional[str] = None,
    ) -> tuple[Optional[ListingPage], Optional[str], bool]:
        """Get marketplace listings with caching.

        Args:
            query: Optional query parameters for filtering/sorting
            if_none_match: ETag from client's If-None-Match header

        Returns:
            Tuple of (listings, etag, not_modified):
            - listings: ListingPage if data available, None if not modified
            - etag: Current ETag
            - not_modified: True if client's ETag matches (304 response)

        Raises:
            ValueError: If query parameters are invalid
            ConnectionError: If all brokers are unreachable
        """
        # Generate cache key from query
        cache_params = {}
        if query:
            if query.search:
                cache_params["search"] = query.search
            if query.category:
                cache_params["category"] = query.category
            if query.tags:
                cache_params["tags"] = ",".join(sorted(query.tags))
            if query.publisher:
                cache_params["publisher"] = query.publisher
            if query.free_only:
                cache_params["free_only"] = True
            if query.verified_only:
                cache_params["verified_only"] = True
            cache_params["sort"] = query.sort
            cache_params["page"] = query.page
            cache_params["page_size"] = query.page_size
        else:
            cache_params["page"] = 1
            cache_params["page_size"] = 20

        cache_key = MarketplaceCache.generate_cache_key(**cache_params)

        # Check cache
        cached_data, etag, not_modified = self.cache.get(cache_key, if_none_match)

        if not_modified:
            # Client has current version (304 Not Modified)
            logger.debug(f"Client has current version (ETag: {etag[:8]}...)")
            return None, etag, True

        if cached_data:
            # Cache hit
            logger.debug(f"Returning cached listings (ETag: {etag[:8]}...)")
            return cached_data, etag, False

        # Cache miss - fetch from brokers
        logger.debug("Cache miss - fetching from brokers")

        try:
            listings_page = self._aggregate_listings(query)

            # Cache the result
            etag = self.cache.set(cache_key, listings_page)

            logger.info(
                f"Fetched {len(listings_page.listings)} listings "
                f"from {len(self.brokers)} broker(s)"
            )

            return listings_page, etag, False

        except Exception as e:
            logger.error(f"Failed to fetch listings: {e}")
            raise

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        """Get a specific listing by ID.

        Args:
            listing_id: Listing identifier

        Returns:
            Listing if found, None otherwise
        """
        # Try each broker until listing is found
        for broker in self.brokers:
            try:
                listing = broker.get_listing(listing_id)
                if listing:
                    logger.info(f"Found listing {listing_id} in broker: {broker.name}")
                    return listing
            except Exception as e:
                logger.warning(
                    f"Failed to get listing from broker {broker.name}: {e}"
                )
                continue

        logger.warning(f"Listing {listing_id} not found in any broker")
        return None

    def download_listing(
        self, listing_id: str, output_dir: Optional[Path] = None
    ) -> DownloadResult:
        """Download a listing from marketplace.

        Args:
            listing_id: Marketplace listing identifier
            output_dir: Directory to save bundle

        Returns:
            DownloadResult with download status

        Raises:
            FileNotFoundError: If listing not found
            ConnectionError: If download fails
        """
        # Get listing metadata
        listing = self.get_listing(listing_id)
        if not listing:
            raise FileNotFoundError(f"Listing {listing_id} not found")

        # Find broker that has this listing
        for broker in self.brokers:
            try:
                # Try to download from this broker
                result = broker.download(listing_id, output_dir)
                if result.success:
                    logger.info(
                        f"Downloaded listing {listing_id} from broker: {broker.name}"
                    )
                    return result
            except Exception as e:
                logger.warning(
                    f"Failed to download from broker {broker.name}: {e}"
                )
                continue

        # All brokers failed
        raise ConnectionError(f"Failed to download listing {listing_id} from any broker")

    def publish_listing(
        self, request: PublishRequest, broker_name: Optional[str] = None
    ) -> PublishResult:
        """Publish a bundle to marketplace.

        Args:
            request: Publish request with bundle and metadata
            broker_name: Target broker (default: first broker)

        Returns:
            PublishResult with publication status

        Raises:
            ValueError: If broker not found or request invalid
            FileNotFoundError: If bundle file not found
            PermissionError: If authentication fails
        """
        # Select target broker
        if broker_name:
            broker = self._get_broker_by_name(broker_name)
            if not broker:
                raise ValueError(f"Broker not found: {broker_name}")
        else:
            if not self.brokers:
                raise ValueError("No marketplace brokers available")
            broker = self.brokers[0]

        logger.info(f"Publishing to broker: {broker.name}")

        try:
            result = broker.publish(request)

            if result.success:
                # Invalidate cache on successful publish
                self.cache.invalidate()
                logger.info(f"Published listing {result.listing_id} successfully")

            return result

        except Exception as e:
            logger.error(f"Failed to publish: {e}")
            raise

    def invalidate_cache(self) -> None:
        """Invalidate all cached listings.

        Useful after publishing new listings or when marketplace is updated.
        """
        self.cache.invalidate()
        logger.info("Invalidated marketplace cache")

    def _aggregate_listings(
        self, query: Optional[ListingQuery] = None
    ) -> ListingPage:
        """Aggregate listings from multiple brokers.

        Args:
            query: Query parameters for filtering/sorting

        Returns:
            Aggregated ListingPage

        Raises:
            ConnectionError: If all brokers fail
        """
        all_listings: List[Listing] = []
        errors = []

        # Fetch from all brokers
        for broker in self.brokers:
            try:
                logger.debug(f"Fetching listings from broker: {broker.name}")
                page = broker.listings(query)
                all_listings.extend(page.listings)

            except Exception as e:
                logger.warning(f"Failed to fetch from broker {broker.name}: {e}")
                errors.append(str(e))
                continue

        # Check if any broker succeeded
        if not all_listings and errors:
            raise ConnectionError(f"All brokers failed: {', '.join(errors)}")

        # Apply client-side filtering if needed
        filtered_listings = self._apply_filters(all_listings, query)

        # Apply sorting
        sorted_listings = self._apply_sorting(filtered_listings, query)

        # Apply pagination
        page, page_size = 1, 20
        if query:
            page = query.page
            page_size = query.page_size

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_listings = sorted_listings[start_idx:end_idx]

        # Build paginated response
        total_count = len(sorted_listings)
        total_pages = (total_count + page_size - 1) // page_size

        return ListingPage(
            listings=page_listings,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

    def _apply_filters(
        self, listings: List[Listing], query: Optional[ListingQuery]
    ) -> List[Listing]:
        """Apply client-side filtering to listings.

        Args:
            listings: List of listings to filter
            query: Query parameters

        Returns:
            Filtered listings
        """
        if not query:
            return listings

        filtered = listings

        # Filter by search term
        if query.search:
            search_lower = query.search.lower()
            filtered = [
                listing
                for listing in filtered
                if search_lower in listing.name.lower()
                or search_lower in listing.description.lower()
            ]

        # Filter by category
        if query.category:
            filtered = [
                listing for listing in filtered if listing.category == query.category
            ]

        # Filter by tags (listing must have all specified tags)
        if query.tags:
            filtered = [
                listing
                for listing in filtered
                if all(tag in listing.tags for tag in query.tags)
            ]

        # Filter by publisher
        if query.publisher:
            filtered = [
                listing
                for listing in filtered
                if listing.publisher.name.lower() == query.publisher.lower()
            ]

        # Filter free only
        if query.free_only:
            filtered = [listing for listing in filtered if listing.price == 0.0]

        # Filter verified only
        if query.verified_only:
            filtered = [listing for listing in filtered if listing.publisher.verified]

        return filtered

    def _apply_sorting(
        self, listings: List[Listing], query: Optional[ListingQuery]
    ) -> List[Listing]:
        """Apply sorting to listings.

        Args:
            listings: List of listings to sort
            query: Query parameters

        Returns:
            Sorted listings
        """
        if not query:
            # Default: newest first
            return sorted(listings, key=lambda x: x.created_at, reverse=True)

        sort_order = query.sort

        if sort_order == "newest":
            return sorted(listings, key=lambda x: x.created_at, reverse=True)
        elif sort_order == "popular":
            return sorted(listings, key=lambda x: x.downloads, reverse=True)
        elif sort_order == "updated":
            return sorted(listings, key=lambda x: x.updated_at, reverse=True)
        elif sort_order == "name":
            return sorted(listings, key=lambda x: x.name.lower())
        elif sort_order == "downloads":
            return sorted(listings, key=lambda x: x.downloads, reverse=True)
        else:
            # Default: newest
            return sorted(listings, key=lambda x: x.created_at, reverse=True)

    def _get_broker_by_name(self, name: str) -> Optional[MarketplaceBroker]:
        """Get broker by name.

        Args:
            name: Broker name

        Returns:
            MarketplaceBroker if found, None otherwise
        """
        for broker in self.brokers:
            if broker.name.lower() == name.lower():
                return broker
        return None
