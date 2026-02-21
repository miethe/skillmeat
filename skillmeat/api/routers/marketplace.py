"""Marketplace API endpoints.

Provides REST API for browsing, installing, and publishing marketplace listings
through configured broker integrations.
"""

import base64
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from skillmeat.api.dependencies import verify_api_key
from skillmeat.api.middleware.auth import OptionalTokenDep, TokenDep
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.marketplace import (
    BrokerInfo,
    BrokerListResponse,
    InstallRequest,
    InstallResponse,
    ListingDetailResponse,
    ListingResponse,
    ListingsPageResponse,
    PublishRequest,
    PublishResponse,
)
from skillmeat.api.services.artifact_cache_service import (
    populate_collection_artifact_from_import,
)
from skillmeat.api.utils.cache import get_cache_manager
from skillmeat.cache.models import Artifact as ArtifactModel, CompositeMembership, get_session
from skillmeat.core.sharing.bundle import Bundle
from skillmeat.core.sharing.importer import BundleImporter
from skillmeat.marketplace.broker import (
    DownloadError,
    MarketplaceBrokerError,
    PublishError,
    RateLimitError,
    ValidationError,
)
from skillmeat.marketplace.models import MarketplaceListing
from skillmeat.marketplace.registry import get_broker_registry

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/marketplace",
    tags=["marketplace"],
)

# Get global cache manager
cache_manager = get_cache_manager(default_ttl=300)  # 5 minute default TTL


def encode_cursor(value: str) -> str:
    """Encode a cursor value to base64.

    Args:
        value: Value to encode

    Returns:
        Base64 encoded cursor string
    """
    return base64.b64encode(value.encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a base64 cursor value.

    Args:
        cursor: Base64 encoded cursor

    Returns:
        Decoded cursor value

    Raises:
        HTTPException: If cursor is invalid
    """
    try:
        return base64.b64decode(cursor.encode()).decode()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}",
        )


@router.get(
    "/listings",
    response_model=ListingsPageResponse,
    summary="Browse marketplace listings",
    description="Retrieve paginated marketplace listings with optional filtering",
    responses={
        200: {"description": "Successfully retrieved listings"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Broker unavailable"},
    },
)
async def list_listings(
    request: Request,
    response: Response,
    token: OptionalTokenDep = None,
    broker: Optional[str] = Query(
        default=None,
        description="Filter by broker name",
        examples=["skillmeat"],
    ),
    query: Optional[str] = Query(
        default=None,
        description="Search term",
        examples=["testing"],
    ),
    tags: Optional[str] = Query(
        default=None,
        description="Comma-separated tags",
        examples=["python,testing"],
    ),
    license: Optional[str] = Query(
        default=None,
        description="Filter by license",
        examples=["MIT"],
    ),
    publisher: Optional[str] = Query(
        default=None,
        description="Filter by publisher",
        examples=["anthropics"],
    ),
    cursor: Optional[str] = Query(
        default=None,
        description="Pagination cursor",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Items per page (max 100)",
    ),
) -> ListingsPageResponse:
    """Browse marketplace listings with filtering and pagination.

    This endpoint aggregates listings from enabled brokers and provides
    cursor-based pagination for efficient browsing.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        token: Optional authentication token
        broker: Optional broker filter
        query: Optional search query
        tags: Optional comma-separated tags
        license: Optional license filter
        publisher: Optional publisher filter
        cursor: Optional pagination cursor
        limit: Number of items per page

    Returns:
        Paginated listings response

    Raises:
        HTTPException: If broker not found, invalid parameters, or server error
    """
    logger.info(
        f"Listing marketplace items (broker={broker}, query={query}, limit={limit})"
    )

    try:
        # Build cache key from query parameters
        cache_key = f"listings:{broker or 'all'}:{query or ''}:{tags or ''}:{license or ''}:{publisher or ''}:{cursor or ''}:{limit}"

        # Check cache
        cached = cache_manager.get(cache_key)
        if cached:
            data, etag = cached
            # Check if client has cached version (If-None-Match)
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match == etag:
                response.status_code = status.HTTP_304_NOT_MODIFIED
                return Response(status_code=status.HTTP_304_NOT_MODIFIED)

            # Return cached data with ETag
            response.headers["ETag"] = etag
            return data

        # Get broker registry
        registry = get_broker_registry()

        # Determine which brokers to query
        if broker:
            broker_instance = registry.get_broker(broker)
            if not broker_instance:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Broker '{broker}' not found",
                )
            brokers_to_query = [broker_instance]
        else:
            # Query all enabled brokers
            brokers_to_query = registry.get_enabled_brokers()

        if not brokers_to_query:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No marketplace brokers are currently available",
            )

        # Parse cursor for page number
        page = 1
        if cursor:
            try:
                page = int(decode_cursor(cursor))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor format",
                )

        # Build filters
        filters = {}
        if query:
            filters["query"] = query
        if tags:
            filters["tags"] = [tag.strip() for tag in tags.split(",")]
        if license:
            filters["license"] = license
        if publisher:
            filters["publisher"] = publisher

        # Aggregate listings from brokers
        all_listings: List[MarketplaceListing] = []
        for broker_inst in brokers_to_query:
            try:
                broker_listings = broker_inst.listings(
                    filters=filters,
                    page=page,
                    page_size=limit,
                )
                all_listings.extend(broker_listings)
                logger.debug(
                    f"Retrieved {len(broker_listings)} listings from {broker_inst.name}"
                )
            except RateLimitError as e:
                logger.warning(
                    f"Rate limit exceeded for broker {broker_inst.name}: {e}"
                )
                # Continue with other brokers
                continue
            except MarketplaceBrokerError as e:
                logger.error(f"Error fetching from broker {broker_inst.name}: {e}")
                # Continue with other brokers
                continue

        # Sort by created_at (newest first)
        all_listings.sort(
            key=lambda x: x.created_at if x.created_at else "", reverse=True
        )

        # Apply pagination
        total_count = len(all_listings)
        start_idx = 0
        end_idx = min(limit, total_count)

        paginated_listings = all_listings[start_idx:end_idx]

        # Convert to response models
        listing_responses = [
            ListingResponse(
                listing_id=listing.listing_id,
                name=listing.name,
                publisher=listing.publisher,
                license=listing.license,
                artifact_count=listing.artifact_count,
                tags=listing.tags,
                created_at=listing.created_at,
                source_url=listing.source_url,
                description=listing.description,
                version=listing.version,
                downloads=listing.downloads,
                rating=listing.rating,
                price=listing.price,
            )
            for listing in paginated_listings
        ]

        # Build pagination info
        has_next = end_idx < total_count
        has_prev = page > 1

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_prev,
            start_cursor=encode_cursor(str(page)) if paginated_listings else None,
            end_cursor=encode_cursor(str(page + 1)) if has_next else None,
            total_count=total_count,
        )

        result = ListingsPageResponse(
            items=listing_responses,
            page_info=page_info,
        )

        # Cache result
        etag = cache_manager.set(cache_key, result.dict())
        response.headers["ETag"] = etag

        logger.info(
            f"Retrieved {len(listing_responses)} listings (total: {total_count})"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing marketplace items: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve listings: {str(e)}",
        )


@router.get(
    "/listings/{listing_id}",
    response_model=ListingDetailResponse,
    summary="Get listing details",
    description="Retrieve detailed information for a specific marketplace listing",
    responses={
        200: {"description": "Successfully retrieved listing"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Broker unavailable"},
    },
)
async def get_listing_detail(
    listing_id: str,
    request: Request,
    response: Response,
    token: OptionalTokenDep = None,
) -> ListingDetailResponse:
    """Get detailed information for a specific listing.

    Args:
        listing_id: The listing ID to retrieve
        request: FastAPI request object
        response: FastAPI response object
        token: Optional authentication token

    Returns:
        Detailed listing information

    Raises:
        HTTPException: If listing not found or error occurs
    """
    logger.info(f"Fetching listing details: {listing_id}")

    try:
        # Check cache
        cache_key = f"listing_detail:{listing_id}"
        cached = cache_manager.get(cache_key)
        if cached:
            data, etag = cached
            # Check if client has cached version
            if_none_match = request.headers.get("If-None-Match")
            if if_none_match == etag:
                return Response(status_code=status.HTTP_304_NOT_MODIFIED)

            response.headers["ETag"] = etag
            return data

        # Get broker registry
        registry = get_broker_registry()
        brokers = registry.get_enabled_brokers()

        if not brokers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No marketplace brokers are currently available",
            )

        # Search for listing across brokers
        found_listing: Optional[MarketplaceListing] = None
        for broker in brokers:
            try:
                # Fetch all listings and search for matching ID
                # In production, brokers should have a get_listing(id) method
                listings = broker.listings(page=1, page_size=100)
                for listing in listings:
                    if listing.listing_id == listing_id:
                        found_listing = listing
                        break
                if found_listing:
                    break
            except MarketplaceBrokerError as e:
                logger.warning(f"Error fetching from broker {broker.name}: {e}")
                continue

        if not found_listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Listing '{listing_id}' not found",
            )

        # Convert to response model
        result = ListingDetailResponse(
            listing_id=found_listing.listing_id,
            name=found_listing.name,
            publisher=found_listing.publisher,
            license=found_listing.license,
            artifact_count=found_listing.artifact_count,
            tags=found_listing.tags,
            created_at=found_listing.created_at,
            source_url=found_listing.source_url,
            bundle_url=found_listing.bundle_url,
            signature=found_listing.signature,
            description=found_listing.description,
            version=found_listing.version,
            homepage=found_listing.homepage,
            repository=found_listing.repository,
            downloads=found_listing.downloads,
            rating=found_listing.rating,
            price=found_listing.price,
        )

        # Cache result
        etag = cache_manager.set(cache_key, result.dict())
        response.headers["ETag"] = etag

        logger.info(f"Retrieved listing details: {listing_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listing details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve listing: {str(e)}",
        )


@router.post(
    "/install",
    response_model=InstallResponse,
    summary="Install marketplace listing",
    description="Download and install a bundle from the marketplace",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Successfully installed listing"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Listing not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def install_listing(
    install_req: InstallRequest,
    token: TokenDep,
) -> InstallResponse:
    """Install a marketplace listing.

    Downloads the bundle from the marketplace and imports artifacts
    into the local collection using the specified conflict resolution strategy.

    Args:
        install_req: Installation request with listing ID and strategy
        token: Authentication token

    Returns:
        Installation result with imported artifacts

    Raises:
        HTTPException: If installation fails
    """
    logger.info(
        f"Installing listing: {install_req.listing_id} (strategy={install_req.strategy})"
    )

    try:
        # Get broker registry
        registry = get_broker_registry()

        # Determine broker
        if install_req.broker:
            broker_inst = registry.get_broker(install_req.broker)
            if not broker_inst:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Broker '{install_req.broker}' not found",
                )
        else:
            # Auto-detect broker by searching for listing
            brokers = registry.get_enabled_brokers()
            broker_inst = None
            for broker in brokers:
                try:
                    listings = broker.listings(page=1, page_size=100)
                    if any(l.listing_id == install_req.listing_id for l in listings):
                        broker_inst = broker
                        break
                except MarketplaceBrokerError:
                    continue

            if not broker_inst:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Listing '{install_req.listing_id}' not found in any broker",
                )

        # Download bundle
        try:
            bundle_path = broker_inst.download(install_req.listing_id)
            logger.info(f"Downloaded bundle to: {bundle_path}")
        except DownloadError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download bundle: {str(e)}",
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bundle validation failed: {str(e)}",
            )

        # Load bundle
        try:
            bundle = Bundle.from_file(bundle_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load bundle: {str(e)}",
            )

        # Import bundle with specified strategy
        try:
            importer = BundleImporter()
            result = importer.import_bundle(
                bundle_path=bundle_path,
                strategy=install_req.strategy,
            )

            artifact_names = [artifact.name for artifact in result.artifacts]

            logger.info(
                f"Imported {len(artifact_names)} artifacts from bundle: {artifact_names}"
            )

            # Sync imported artifacts to DB cache with source from bundle metadata
            # (refresh_single_artifact_cache reads file_artifact.upstream which is empty
            # for marketplace imports; we must use bundle.metadata.repository instead)
            try:
                db_session = get_session()
                try:
                    synced_count = 0
                    # Get source URL from bundle metadata
                    source_url = bundle.metadata.repository if bundle.metadata else None

                    # Build a map of artifact name -> BundleArtifact for per-artifact metadata
                    bundle_artifact_map = {a.name: a for a in bundle.artifacts}

                    # Entry-like adapter for populate_collection_artifact_from_import
                    class MarketplaceImportEntry:
                        def __init__(
                            self, name, artifact_type, description, upstream_url, tags
                        ):
                            self.name = name
                            self.artifact_type = artifact_type
                            self.description = description
                            self.upstream_url = upstream_url
                            self.tags = tags

                    for artifact in result.artifacts:
                        # Only sync successfully imported artifacts (not skipped)
                        if artifact.resolution in ("imported", "forked", "merged"):
                            artifact_name = artifact.new_name or artifact.name
                            artifact_id = f"{artifact.type}:{artifact_name}"

                            # Get per-artifact metadata from bundle if available
                            bundle_artifact = bundle_artifact_map.get(artifact.name)
                            artifact_metadata = (
                                bundle_artifact.metadata if bundle_artifact else {}
                            )

                            entry = MarketplaceImportEntry(
                                name=artifact_name,
                                artifact_type=artifact.type,
                                description=artifact_metadata.get("description")
                                or (
                                    bundle.metadata.description
                                    if bundle.metadata
                                    else None
                                ),
                                upstream_url=source_url,
                                tags=(
                                    bundle.metadata.tags if bundle.metadata else None
                                ),
                            )

                            try:
                                populate_collection_artifact_from_import(
                                    db_session,
                                    importer.artifact_mgr,
                                    "default",
                                    entry,
                                )
                                synced_count += 1
                            except Exception as cache_err:
                                logger.warning(
                                    f"Cache sync failed for {artifact_id}: {cache_err}"
                                )
                    logger.info(
                        f"Synced {synced_count}/{len(artifact_names)} artifacts to DB cache"
                    )

                    # ------------------------------------------------------------------
                    # Create CompositeMembership rows for composite/plugin bundles.
                    # All Artifact rows must exist before this block runs (populated
                    # above via populate_collection_artifact_from_import).
                    # ------------------------------------------------------------------
                    collection_id = "default"

                    composite_artifacts = [
                        a
                        for a in result.artifacts
                        if a.type == "composite"
                        and a.resolution in ("imported", "forked", "merged")
                    ]

                    for composite_art in composite_artifacts:
                        composite_name = composite_art.new_name or composite_art.name
                        composite_id = f"composite:{composite_name}"

                        # Children = all other non-composite artifacts in the same import
                        children = [
                            a
                            for a in result.artifacts
                            if a.type != "composite"
                            and a.resolution in ("imported", "forked", "merged")
                        ]

                        membership_count = 0
                        for idx, child in enumerate(children):
                            child_name = child.new_name or child.name
                            child_artifact_id = f"{child.type}:{child_name}"

                            # Resolve stable UUID from the Artifact table
                            artifact_row = (
                                db_session.query(ArtifactModel)
                                .filter(ArtifactModel.id == child_artifact_id)
                                .first()
                            )

                            if artifact_row is None:
                                logger.warning(
                                    f"CompositeMembership: artifact row not found for "
                                    f"'{child_artifact_id}', skipping"
                                )
                                continue

                            # Upsert membership row
                            existing = (
                                db_session.query(CompositeMembership)
                                .filter(
                                    CompositeMembership.collection_id == collection_id,
                                    CompositeMembership.composite_id == composite_id,
                                    CompositeMembership.child_artifact_uuid
                                    == artifact_row.uuid,
                                )
                                .first()
                            )

                            if existing is None:
                                membership = CompositeMembership(
                                    collection_id=collection_id,
                                    composite_id=composite_id,
                                    child_artifact_uuid=artifact_row.uuid,
                                    relationship_type="contains",
                                    pinned_version_hash=None,
                                    position=idx,
                                )
                                db_session.add(membership)
                                membership_count += 1
                            else:
                                # Already linked; update position in case ordering changed
                                existing.position = idx

                        try:
                            db_session.flush()
                            logger.info(
                                f"Created {membership_count} CompositeMembership rows "
                                f"for composite '{composite_id}'"
                            )
                        except Exception as mem_err:
                            logger.warning(
                                f"CompositeMembership flush failed for '{composite_id}': "
                                f"{mem_err}"
                            )
                finally:
                    db_session.close()
            except Exception as e:
                # Don't fail the entire install if cache sync fails
                logger.warning(f"DB cache sync failed: {e}")

            # Invalidate listings cache after successful install
            cache_manager.invalidate_pattern("listings:*")

            return InstallResponse(
                success=True,
                artifacts_imported=artifact_names,
                message=f"Successfully installed {len(artifact_names)} artifacts from bundle",
                listing_id=install_req.listing_id,
                broker=broker_inst.name,
            )

        except Exception as e:
            logger.error(f"Failed to import bundle: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import bundle: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error installing listing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Installation failed: {str(e)}",
        )


@router.post(
    "/publish",
    response_model=PublishResponse,
    summary="Publish bundle to marketplace",
    description="Publish a signed bundle to the marketplace for distribution",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Successfully published bundle"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid request or validation failed",
        },
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Broker not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def publish_bundle(
    publish_req: PublishRequest,
    token: TokenDep,
) -> PublishResponse:
    """Publish a bundle to the marketplace.

    Validates the bundle signature and submits it to the specified broker
    for review and publication.

    Args:
        publish_req: Publish request with bundle path and metadata
        token: Authentication token (requires publisher key)

    Returns:
        Publish result with submission ID and status

    Raises:
        HTTPException: If publish fails
    """
    logger.info(f"Publishing bundle: {publish_req.bundle_path} to {publish_req.broker}")

    try:
        # Validate bundle path exists
        bundle_path = Path(publish_req.bundle_path)
        if not bundle_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bundle file not found: {publish_req.bundle_path}",
            )

        if not bundle_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bundle path is not a file: {publish_req.bundle_path}",
            )

        # Get broker
        registry = get_broker_registry()
        broker_inst = registry.get_broker(publish_req.broker)
        if not broker_inst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Broker '{publish_req.broker}' not found",
            )

        # Load bundle
        try:
            bundle = Bundle.from_file(bundle_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to load bundle: {str(e)}",
            )

        # Validate bundle signature
        try:
            broker_inst.validate_signature(bundle)
            logger.info("Bundle signature validated successfully")
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bundle signature validation failed: {str(e)}",
            )

        # Publish bundle
        try:
            result = broker_inst.publish(bundle, metadata=publish_req.metadata)

            logger.info(
                f"Bundle published: submission_id={result.submission_id}, status={result.status}"
            )

            # Invalidate listings cache after publish
            cache_manager.invalidate_pattern("listings:*")

            return PublishResponse(
                submission_id=result.submission_id,
                status=result.status,
                message=result.message,
                broker=publish_req.broker,
                listing_url=result.listing_url,
            )

        except PublishError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to publish bundle: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing bundle: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Publish failed: {str(e)}",
        )


@router.get(
    "/brokers",
    response_model=BrokerListResponse,
    summary="List available brokers",
    description="Retrieve list of all configured marketplace brokers",
    responses={
        200: {"description": "Successfully retrieved brokers"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_brokers() -> BrokerListResponse:
    """List all available marketplace brokers.

    This is a public endpoint that shows all configured brokers
    and their current status.

    Returns:
        List of broker information

    Raises:
        HTTPException: If error occurs
    """
    logger.info("Listing marketplace brokers")

    try:
        # Get broker registry
        registry = get_broker_registry()

        # Get all broker names (including disabled)
        config = registry._read_config()
        all_broker_configs = config.get("brokers", {})

        # Build broker info list
        broker_infos = []
        for broker_name, broker_config in all_broker_configs.items():
            enabled = broker_config.get("enabled", False)
            endpoint = broker_config.get("endpoint", "")
            description = broker_config.get("description", "")

            # Check if broker supports publishing (read-only brokers don't)
            supports_publish = broker_name not in [
                "claudehub"
            ]  # claudehub is read-only

            broker_infos.append(
                BrokerInfo(
                    name=broker_name,
                    enabled=enabled,
                    endpoint=endpoint,
                    supports_publish=supports_publish,
                    description=description,
                )
            )

        logger.info(f"Retrieved {len(broker_infos)} broker configurations")

        return BrokerListResponse(brokers=broker_infos)

    except Exception as e:
        logger.error(f"Error listing brokers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve brokers: {str(e)}",
        )


# ====================
# Compliance Endpoints
# ====================


@router.post(
    "/compliance/scan",
    summary="Scan bundle for license compliance",
    description="Scan all files in bundle for license headers and copyright notices",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Scan completed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid bundle path"},
        500: {"model": ErrorResponse, "description": "Scan failed"},
    },
)
async def compliance_scan(
    bundle_path: str,
    token: TokenDep,
):
    """Scan bundle for license compliance.

    Args:
        bundle_path: Path to bundle ZIP file
        token: Authentication token (required)

    Returns:
        License scan report

    Raises:
        HTTPException: If scan fails
    """
    logger.info(f"Scanning bundle for compliance: {bundle_path}")

    try:
        from skillmeat.marketplace.compliance import LicenseScanner

        bundle_path_obj = Path(bundle_path)
        if not bundle_path_obj.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bundle not found: {bundle_path}",
            )

        scanner = LicenseScanner()
        report = scanner.scan_bundle(bundle_path_obj)

        # Convert to dict for JSON response
        return {
            "declared_license": report.declared_license,
            "detected_licenses": [
                {
                    "file_path": d.file_path,
                    "detected_license": d.detected_license,
                    "confidence": d.confidence,
                    "copyright_notices": d.copyright_notices,
                }
                for d in report.detected_licenses
            ],
            "conflicts": report.conflicts,
            "missing_licenses": report.missing_licenses,
            "attribution_required": report.attribution_required,
            "recommendations": report.recommendations,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance scan failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}",
        )


@router.post(
    "/compliance/checklist",
    summary="Generate compliance checklist",
    description="Generate legal compliance checklist for bundle",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Checklist generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Generation failed"},
    },
)
async def compliance_checklist(
    bundle_id: str,
    license: str,
    token: TokenDep,
):
    """Generate compliance checklist for bundle.

    Args:
        bundle_id: Unique identifier for bundle
        license: SPDX license identifier
        token: Authentication token (required)

    Returns:
        Compliance checklist

    Raises:
        HTTPException: If generation fails
    """
    logger.info(f"Generating compliance checklist: {bundle_id} ({license})")

    try:
        from skillmeat.marketplace.compliance import ComplianceChecklistGenerator

        generator = ComplianceChecklistGenerator()
        checklist = generator.create_checklist(
            bundle_id=bundle_id,
            license=license,
        )

        return checklist.to_dict()

    except Exception as e:
        logger.error(f"Checklist generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}",
        )


@router.post(
    "/compliance/consent",
    summary="Record compliance consent",
    description="Record publisher consent to compliance checklist",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "Consent recorded successfully"},
        400: {"model": ErrorResponse, "description": "Invalid consent data"},
        500: {"model": ErrorResponse, "description": "Recording failed"},
    },
)
async def compliance_consent(
    checklist_id: str,
    bundle_id: str,
    publisher_email: str,
    consents: dict,
    token: TokenDep,
):
    """Record publisher consent to compliance checklist.

    Args:
        checklist_id: ID of compliance checklist
        bundle_id: ID of bundle
        publisher_email: Publisher email address
        consents: Dictionary of item_id -> consented (bool)
        token: Authentication token (required)

    Returns:
        Consent record

    Raises:
        HTTPException: If recording fails
    """
    logger.info(f"Recording compliance consent: {checklist_id}")

    try:
        from skillmeat.marketplace.compliance import ConsentLogger

        logger_obj = ConsentLogger()
        record = logger_obj.record_consent(
            checklist_id=checklist_id,
            bundle_id=bundle_id,
            publisher_email=publisher_email,
            consents=consents,
        )

        return record.to_dict()

    except Exception as e:
        logger.error(f"Consent recording failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recording failed: {str(e)}",
        )


@router.get(
    "/compliance/history",
    summary="Get consent history",
    description="Retrieve compliance consent history",
    dependencies=[Depends(verify_api_key)],
    responses={
        200: {"description": "History retrieved successfully"},
        403: {"model": ErrorResponse, "description": "Unauthorized access"},
        500: {"model": ErrorResponse, "description": "Retrieval failed"},
    },
)
async def compliance_history(
    publisher_email: Optional[str] = Query(
        None, description="Filter by publisher email"
    ),
    token: TokenDep = None,
):
    """Get compliance consent history.

    Args:
        publisher_email: Optional filter by publisher email (admin only for others)
        token: Authentication token (required)

    Returns:
        List of consent records

    Raises:
        HTTPException: If retrieval fails or unauthorized
    """
    logger.info(f"Retrieving compliance history: {publisher_email or 'all'}")

    try:
        from skillmeat.marketplace.compliance import ConsentLogger

        # TODO: Add admin check for viewing other publisher's history
        # For now, allow viewing own history only

        logger_obj = ConsentLogger()
        records = logger_obj.get_consent_history(publisher_email=publisher_email)

        return {
            "records": [record.to_dict() for record in records],
            "total": len(records),
        }

    except Exception as e:
        logger.error(f"History retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(e)}",
        )
