"""Marketplace API endpoints.

REST API for browsing, filtering, and managing marketplace listings.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from skillmeat.api.dependencies import CollectionManagerDep, verify_api_key
from skillmeat.api.middleware.auth import OptionalTokenDep, TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.marketplace import (
    InstallRequest,
    InstallResponse,
    ListingDetailResponse,
    ListingFeedResponse,
    ListingResponse,
    PublishBundleRequest,
    PublishBundleResponse,
    PublisherResponse,
)
from skillmeat.core.marketplace.models import (
    ArtifactCategory,
    ListingQuery,
    ListingSortOrder,
    PublishRequest,
)
from skillmeat.core.marketplace.service import MarketplaceService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/marketplace",
    tags=["marketplace"],
)

# Global marketplace service (initialized on first use)
_marketplace_service: Optional[MarketplaceService] = None


def get_marketplace_service() -> MarketplaceService:
    """Get or create marketplace service instance.

    Returns:
        MarketplaceService instance
    """
    global _marketplace_service
    if _marketplace_service is None:
        _marketplace_service = MarketplaceService()
    return _marketplace_service


@router.get(
    "/listings",
    response_model=ListingFeedResponse,
    summary="List marketplace listings",
    description="Get a paginated feed of marketplace listings with optional filtering and sorting",
    responses={
        200: {"description": "Successfully retrieved listings"},
        304: {"description": "Not Modified - client has current version"},
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_listings(
    response: Response,
    marketplace_service: MarketplaceService = Depends(get_marketplace_service),
    token: OptionalTokenDep = None,
    if_none_match: Optional[str] = Header(None, description="ETag for conditional request"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    license: Optional[str] = Query(None, description="Filter by license type"),
    publisher: Optional[str] = Query(None, description="Filter by publisher name"),
    artifact_type: Optional[str] = Query(
        None,
        description="Filter by artifact type (skill, command, agent, hook, mcp-server, bundle)",
    ),
    search: Optional[str] = Query(None, description="Full-text search in name/description"),
    sort: str = Query("newest", description="Sort field (newest, popular, updated, name, downloads)"),
    free_only: bool = Query(False, description="Only show free listings"),
    verified_only: bool = Query(False, description="Only show verified publishers"),
) -> ListingFeedResponse:
    """List marketplace listings with pagination and filtering.

    This endpoint supports ETag-based caching. Send the ETag from a previous
    response in the If-None-Match header to receive a 304 Not Modified if
    the data hasn't changed.

    Rate limits:
    - Public (no token): 60 requests/minute
    - Authenticated (with token): 300 requests/minute

    Args:
        response: FastAPI response object (for setting headers)
        marketplace_service: Marketplace service dependency
        token: Optional authentication token
        if_none_match: ETag from previous response
        page: Page number
        per_page: Items per page
        tags: Filter by tags
        license: Filter by license
        publisher: Filter by publisher
        artifact_type: Filter by artifact type
        search: Search query
        sort: Sort order
        free_only: Only free listings
        verified_only: Only verified publishers

    Returns:
        Paginated listing feed

    Raises:
        HTTPException: On error
    """
    try:
        # Validate artifact type
        category = None
        if artifact_type:
            try:
                category = ArtifactCategory(artifact_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact type: {artifact_type}. "
                    f"Must be one of: skill, command, agent, hook, mcp-server, bundle",
                )

        # Validate sort order
        try:
            sort_order = ListingSortOrder(sort)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort order: {sort}. "
                f"Must be one of: newest, popular, updated, name, downloads",
            )

        # Build query
        query = ListingQuery(
            search=search,
            category=category,
            tags=tags or [],
            publisher=publisher,
            free_only=free_only,
            verified_only=verified_only,
            sort=sort_order,
            page=page,
            page_size=per_page,
        )

        logger.debug(
            f"Fetching listings (page={page}, per_page={per_page}, "
            f"type={artifact_type}, tags={tags})"
        )

        # Get listings with caching
        listings_page, etag, not_modified = marketplace_service.get_listings(
            query, if_none_match
        )

        # Handle 304 Not Modified
        if not_modified:
            response.status_code = status.HTTP_304_NOT_MODIFIED
            response.headers["ETag"] = etag or ""
            response.headers["Cache-Control"] = "max-age=300"
            return None  # FastAPI handles 304 with no body

        # Set cache headers
        if etag:
            response.headers["ETag"] = etag
            response.headers["Cache-Control"] = "max-age=300"

        # Convert to API response format
        items = [
            ListingResponse(
                listing_id=listing.listing_id,
                name=listing.name,
                description=listing.description,
                category=listing.category,
                version=listing.version,
                publisher=PublisherResponse(
                    name=listing.publisher.name,
                    email=listing.publisher.email,
                    website=listing.publisher.website,
                    verified=listing.publisher.verified,
                ),
                license=listing.license,
                tags=listing.tags,
                artifact_count=listing.artifact_count,
                downloads=listing.downloads,
                created_at=listing.created_at,
                updated_at=listing.updated_at,
                homepage=listing.homepage,
                repository=listing.repository,
            )
            for listing in listings_page.listings
        ]

        # Build pagination info
        from skillmeat.api.schemas.common import PageInfo

        page_info = PageInfo(
            has_next_page=listings_page.has_next,
            has_previous_page=listings_page.has_prev,
            start_cursor=None,  # Not using cursor-based pagination here
            end_cursor=None,
            total_count=listings_page.total_count,
        )

        logger.info(
            f"Retrieved {len(items)} listings (page {page}/{listings_page.total_pages})"
        )

        return ListingFeedResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing marketplace: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list marketplace: {str(e)}",
        )


@router.get(
    "/listings/{listing_id}",
    response_model=ListingDetailResponse,
    summary="Get listing details",
    description="Retrieve detailed information about a specific marketplace listing",
    responses={
        200: {"description": "Successfully retrieved listing"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_listing(
    listing_id: str,
    marketplace_service: MarketplaceService = Depends(get_marketplace_service),
    token: OptionalTokenDep = None,
) -> ListingDetailResponse:
    """Get detailed information for a specific listing.

    Args:
        listing_id: Listing identifier
        marketplace_service: Marketplace service dependency
        token: Optional authentication token

    Returns:
        Detailed listing information

    Raises:
        HTTPException: If listing not found or on error
    """
    try:
        logger.info(f"Getting listing: {listing_id}")

        # Get listing from marketplace
        listing = marketplace_service.get_listing(listing_id)

        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing '{listing_id}' not found",
            )

        # Convert to API response format
        return ListingDetailResponse(
            listing_id=listing.listing_id,
            name=listing.name,
            description=listing.description,
            category=listing.category,
            version=listing.version,
            publisher=PublisherResponse(
                name=listing.publisher.name,
                email=listing.publisher.email,
                website=listing.publisher.website,
                verified=listing.publisher.verified,
            ),
            license=listing.license,
            tags=listing.tags,
            artifact_count=listing.artifact_count,
            downloads=listing.downloads,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
            homepage=listing.homepage,
            repository=listing.repository,
            source_url=listing.source_url,
            bundle_url=listing.bundle_url,
            price=listing.price,
            signature=listing.signature,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting listing '{listing_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get listing: {str(e)}",
        )


@router.post(
    "/install",
    response_model=InstallResponse,
    summary="Install marketplace listing",
    description="Download and install a marketplace listing into your collection",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Successfully installed listing"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def install_listing(
    request: InstallRequest,
    marketplace_service: MarketplaceService = Depends(get_marketplace_service),
    collection_mgr: CollectionManagerDep = None,
    token: TokenDep = None,
) -> InstallResponse:
    """Install a marketplace listing into collection.

    Requires authentication (bearer token).

    Args:
        request: Install request
        marketplace_service: Marketplace service dependency
        collection_mgr: Collection manager dependency
        token: Authentication token

    Returns:
        Install result

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(f"Installing listing: {request.listing_id}")

        # Download listing
        from pathlib import Path
        import tempfile

        output_dir = Path(tempfile.gettempdir()) / "skillmeat-installs"
        download_result = marketplace_service.download_listing(
            request.listing_id, output_dir
        )

        if not download_result.success:
            return InstallResponse(
                success=False,
                listing_id=request.listing_id,
                artifacts_installed=0,
                collection_name="",
                message="Download failed",
                errors=download_result.errors,
            )

        # Verify signature if requested
        if request.verify_signature and not download_result.verified:
            logger.warning(
                f"Signature verification failed for listing {request.listing_id}"
            )
            return InstallResponse(
                success=False,
                listing_id=request.listing_id,
                artifacts_installed=0,
                collection_name="",
                message="Signature verification failed",
                warnings=["Bundle signature could not be verified"],
            )

        # TODO: Install bundle into collection
        # This requires bundle unpacking and artifact installation logic
        # For now, return success with download
        logger.info(f"Downloaded listing {request.listing_id} to {download_result.bundle_path}")

        return InstallResponse(
            success=True,
            listing_id=request.listing_id,
            artifacts_installed=1,  # Placeholder
            collection_name=request.collection_name or "default",
            message=f"Successfully downloaded {download_result.listing.name}",
            warnings=["Installation into collection not yet implemented"],
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error installing listing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to install listing: {str(e)}",
        )


@router.post(
    "/publish",
    response_model=PublishBundleResponse,
    summary="Publish bundle to marketplace",
    description="Publish a local bundle to the marketplace (requires publisher credentials)",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Successfully published bundle"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Publisher key required"},
        404: {"model": ErrorResponse, "description": "Bundle file not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def publish_bundle(
    request: PublishBundleRequest,
    marketplace_service: MarketplaceService = Depends(get_marketplace_service),
    token: TokenDep = None,
) -> PublishBundleResponse:
    """Publish a bundle to marketplace.

    Requires authentication (bearer token) and publisher credentials.

    Args:
        request: Publish request
        marketplace_service: Marketplace service dependency
        token: Authentication token

    Returns:
        Publish result

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(f"Publishing bundle: {request.name}")

        # Validate artifact type
        try:
            category = ArtifactCategory(request.category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid artifact category: {request.category}",
            )

        # Build publish request
        publish_req = PublishRequest(
            bundle_path=request.bundle_path,
            name=request.name,
            description=request.description,
            category=category,
            version=request.version,
            license=request.license,
            tags=request.tags,
            homepage=request.homepage,
            repository=request.repository,
            price=request.price,
            sign_bundle=request.sign_bundle,
            publisher_key_id=request.publisher_key_id,
        )

        # Publish to marketplace
        result = marketplace_service.publish_listing(publish_req)

        # Convert to API response
        return PublishBundleResponse(
            success=result.success,
            listing_id=result.listing_id,
            listing_url=result.listing_url,
            message=result.message,
            errors=result.errors,
            warnings=result.warnings,
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error publishing bundle: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish bundle: {str(e)}",
        )
