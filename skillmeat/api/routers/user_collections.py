"""User Collections API endpoints.

Provides REST API for managing database-backed user collections (organizational).
Distinct from file-based collections in collections.py router.
"""

import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from skillmeat.api.dependencies import ArtifactManagerDep, CollectionManagerDep
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.collections import (
    RefreshModeEnum,
    RefreshRequest,
    RefreshResponse,
    UpdateCheckResponse,
)
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.user_collections import (
    AddArtifactsRequest,
    ArtifactGroupMembership,
    ArtifactSummary,
    CollectionArtifactsResponse,
    GroupSummary,
    UserCollectionCreateRequest,
    UserCollectionListResponse,
    UserCollectionResponse,
    UserCollectionUpdateRequest,
    UserCollectionWithGroupsResponse,
)
from skillmeat.api.services import get_artifact_metadata
from skillmeat.api.services.artifact_cache_service import (
    invalidate_collection_artifacts,
)
from skillmeat.api.services.artifact_metadata_service import _get_artifact_collections
from skillmeat.cache import get_collection_count_cache
from skillmeat.core.artifact import ArtifactType as CoreArtifactType
from skillmeat.core.refresher import CollectionRefresher, RefreshMode, validate_fields
from skillmeat.cache.models import (
    DEFAULT_COLLECTION_ID,
    DEFAULT_COLLECTION_NAME,
    Artifact,
    Collection,
    CollectionArtifact,
    Group,
    GroupArtifact,
    get_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/user-collections",
    tags=["user-collections"],
)


# =============================================================================
# Database Session Dependency
# =============================================================================


def get_db_session():
    """Get database session with proper cleanup.

    Yields:
        SQLAlchemy session instance

    Note:
        Session is automatically closed after request completes
    """
    session = get_session()
    try:
        yield session
    finally:
        session.close()


DbSessionDep = Annotated[Session, Depends(get_db_session)]


# =============================================================================
# Helper Functions
# =============================================================================


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


def collection_to_response(
    collection: Collection, session: Session
) -> UserCollectionResponse:
    """Convert Collection ORM model to API response.

    Args:
        collection: Collection ORM instance
        session: Database session for computing counts

    Returns:
        UserCollectionResponse DTO
    """
    # Compute counts
    group_count = len(collection.groups)
    artifact_count = (
        session.query(CollectionArtifact).filter_by(collection_id=collection.id).count()
    )

    return UserCollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        created_by=collection.created_by,
        collection_type=collection.collection_type,
        context_category=collection.context_category,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        group_count=group_count,
        artifact_count=artifact_count,
    )


def collection_to_response_with_groups(
    collection: Collection, session: Session
) -> UserCollectionWithGroupsResponse:
    """Convert Collection ORM model to API response with groups.

    Args:
        collection: Collection ORM instance
        session: Database session for computing counts

    Returns:
        UserCollectionWithGroupsResponse DTO with nested groups
    """
    # Get base response
    base_response = collection_to_response(collection, session)

    # Build group summaries
    groups = []
    for group in sorted(collection.groups, key=lambda g: g.position):
        artifact_count = len(group.group_artifacts)
        groups.append(
            GroupSummary(
                id=group.id,
                name=group.name,
                description=group.description,
                position=group.position,
                artifact_count=artifact_count,
            )
        )

    return UserCollectionWithGroupsResponse(
        **base_response.model_dump(),
        groups=groups,
    )


def ensure_default_collection(session: Session) -> Collection:
    """Ensure the default collection exists, creating it if necessary.

    This function should be called during server startup to guarantee
    the default collection exists for artifact assignments.

    Args:
        session: Database session

    Returns:
        The default Collection instance (existing or newly created)
    """
    existing = session.query(Collection).filter_by(id=DEFAULT_COLLECTION_ID).first()
    if existing:
        logger.debug(f"Default collection '{DEFAULT_COLLECTION_ID}' already exists")
        return existing

    default_collection = Collection(
        id=DEFAULT_COLLECTION_ID,
        name=DEFAULT_COLLECTION_NAME,
        description="Default collection for all artifacts. Artifacts are automatically added here when no specific collection is specified.",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(default_collection)
    session.commit()
    logger.info(f"Created default collection '{DEFAULT_COLLECTION_ID}'")
    return default_collection


def migrate_artifacts_to_default_collection(
    session: Session,
    artifact_mgr,
    collection_mgr,
) -> dict:
    """Migrate all existing artifacts to the default collection.

    This function ensures all artifacts from file-system collections
    are also registered in the default database collection, enabling
    them to use Groups and other collection features. Also populates
    the metadata cache for efficient artifact card rendering.

    Args:
        session: Database session
        artifact_mgr: Artifact manager for listing artifacts
        collection_mgr: Collection manager for listing collections

    Returns:
        dict with migration stats: migrated_count, already_present_count,
        total_artifacts, and metadata_cache stats
    """
    # 1. Ensure default collection exists first
    ensure_default_collection(session)

    # 2. Populate metadata cache from file-based artifacts
    # This creates/updates CollectionArtifact rows with full metadata
    # enabling the /collection page to render without N file reads
    metadata_stats = populate_collection_artifact_metadata(
        session, artifact_mgr, collection_mgr
    )

    # 3. Get all artifacts from all file-system collections
    all_artifact_ids = set()
    for coll_name in collection_mgr.list_collections():
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            for artifact in artifacts:
                artifact_id = f"{artifact.type.value}:{artifact.name}"
                all_artifact_ids.add(artifact_id)
        except Exception as e:
            logger.warning(
                f"Failed to load artifacts from collection '{coll_name}': {e}"
            )
            continue

    logger.info(
        f"Found {len(all_artifact_ids)} unique artifacts across all collections"
    )

    # 4. Get existing associations for the default collection
    existing_associations = (
        session.query(CollectionArtifact.artifact_id)
        .filter_by(collection_id=DEFAULT_COLLECTION_ID)
        .all()
    )
    existing_artifact_ids = {row[0] for row in existing_associations}

    # 5. Find artifacts not yet in default collection
    missing_artifact_ids = all_artifact_ids - existing_artifact_ids

    # 6. Add missing artifacts to default collection
    migrated_count = 0
    for artifact_id in missing_artifact_ids:
        try:
            new_association = CollectionArtifact(
                collection_id=DEFAULT_COLLECTION_ID,
                artifact_id=artifact_id,
                added_at=datetime.utcnow(),
            )
            session.add(new_association)
            migrated_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to add artifact '{artifact_id}' to default collection: {e}"
            )
            continue

    if migrated_count > 0:
        session.commit()
        logger.info(f"Migrated {migrated_count} artifacts to default collection")

    # 7. Return combined stats including metadata cache results
    return {
        "migrated_count": migrated_count,
        "already_present_count": len(existing_artifact_ids),
        "total_artifacts": len(all_artifact_ids),
        "metadata_cache": metadata_stats,
    }


def populate_collection_artifact_metadata(
    session: Session,
    artifact_mgr,
    collection_mgr,
) -> dict:
    """Populate CollectionArtifact metadata cache from file-based artifacts.

    For each file-based artifact, create or update CollectionArtifact rows with
    full metadata from YAML frontmatter and manifest entries. This enables the
    /collection page to render artifact cards without N file reads.

    Args:
        session: Database session
        artifact_mgr: ArtifactManager for listing and reading artifacts
        collection_mgr: CollectionManager for collection access

    Returns:
        dict with stats: created_count, updated_count, skipped_count, errors
    """
    import json
    import time

    logger.info("Starting CollectionArtifact metadata cache population...")
    start_time = time.time()

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []

    # Ensure default collection exists
    ensure_default_collection(session)

    # Iterate all file-based collections
    for coll_name in collection_mgr.list_collections():
        try:
            artifacts = artifact_mgr.list_artifacts(collection_name=coll_name)
            logger.debug(
                f"Processing collection '{coll_name}': {len(artifacts)} artifacts"
            )
        except Exception as e:
            error_msg = f"Failed to load artifacts from collection '{coll_name}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue

        for artifact in artifacts:
            try:
                # Build artifact_id: "{type}:{name}"
                artifact_id = f"{artifact.type.value}:{artifact.name}"

                # Extract metadata fields from artifact
                metadata = artifact.metadata
                description = metadata.description if metadata else None
                author = metadata.author if metadata else None
                license_val = metadata.license if metadata else None
                version = metadata.version if metadata else None

                # Convert tags list to JSON string
                tags_json = None
                if metadata and metadata.tags:
                    tags_json = json.dumps(metadata.tags)

                # Source and origin fields
                source = artifact.upstream
                origin = artifact.origin
                origin_source = artifact.origin_source
                resolved_sha = getattr(artifact, "resolved_sha", None)
                resolved_version = getattr(artifact, "resolved_version", None)

                # Check if CollectionArtifact exists for default collection
                existing = (
                    session.query(CollectionArtifact)
                    .filter_by(
                        collection_id=DEFAULT_COLLECTION_ID,
                        artifact_id=artifact_id,
                    )
                    .first()
                )

                if existing:
                    # Update existing row
                    existing.description = description
                    existing.author = author
                    existing.license = license_val
                    existing.tags_json = tags_json
                    existing.version = version
                    existing.source = source
                    existing.origin = origin
                    existing.origin_source = origin_source
                    existing.resolved_sha = resolved_sha
                    existing.resolved_version = resolved_version
                    existing.synced_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new row
                    new_association = CollectionArtifact(
                        collection_id=DEFAULT_COLLECTION_ID,
                        artifact_id=artifact_id,
                        added_at=datetime.utcnow(),
                        description=description,
                        author=author,
                        license=license_val,
                        tags_json=tags_json,
                        version=version,
                        source=source,
                        origin=origin,
                        origin_source=origin_source,
                        resolved_sha=resolved_sha,
                        resolved_version=resolved_version,
                        synced_at=datetime.utcnow(),
                    )
                    session.add(new_association)
                    created_count += 1

            except Exception as e:
                error_msg = (
                    f"Failed to populate metadata for artifact "
                    f"'{artifact.name}' ({artifact.type.value}): {e}"
                )
                logger.warning(error_msg)
                errors.append(error_msg)
                skipped_count += 1
                continue

    # Batch commit after all artifacts processed
    try:
        session.commit()
        duration = time.time() - start_time
        logger.info(
            f"CollectionArtifact metadata cache: created={created_count}, "
            f"updated={updated_count}, skipped={skipped_count}, errors={len(errors)}"
        )
        logger.info(f"Metadata cache population completed in {duration:.2f}s")
    except Exception as e:
        session.rollback()
        error_msg = f"Failed to commit metadata updates: {e}"
        logger.error(error_msg)
        errors.append(error_msg)

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


# =============================================================================
# Migration Endpoint
# =============================================================================


@router.post(
    "/migrate-to-default",
    summary="Migrate all artifacts to default collection",
    description=(
        "Ensures all existing artifacts from file-system collections are registered "
        "in the default database collection. This enables Groups and other collection "
        "features for all artifacts. Safe to run multiple times - only adds missing entries."
    ),
    responses={
        200: {"description": "Migration completed successfully"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def migrate_to_default_collection(
    session: DbSessionDep,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
) -> dict:
    """Migrate all artifacts to the default collection.

    This endpoint ensures all artifacts from file-system collections are
    registered in the default database collection, enabling them to use
    Groups and other collection features.

    Args:
        session: Database session
        artifact_mgr: Artifact manager for listing artifacts
        collection_mgr: Collection manager for listing collections
        token: Authentication token

    Returns:
        Migration statistics with counts

    Note:
        This operation is idempotent - running it multiple times will not
        create duplicate entries.
    """
    try:
        result = migrate_artifacts_to_default_collection(
            session=session,
            artifact_mgr=artifact_mgr,
            collection_mgr=collection_mgr,
        )

        logger.info(
            f"Migration completed: {result['migrated_count']} migrated, "
            f"{result['already_present_count']} already present"
        )

        return {
            "success": True,
            "message": f"Migrated {result['migrated_count']} artifacts to default collection",
            **result,
        }
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}",
        )


# =============================================================================
# Batch Cache Refresh Endpoint (MUST be before /{collection_id} routes)
# =============================================================================


def _refresh_single_collection_cache(
    session: Session,
    collection: Collection,
    artifact_mgr,
) -> dict:
    """Refresh CollectionArtifact metadata cache for a single DB collection.

    This helper extracts the core refresh logic to be reused by both scoped
    and batch refresh endpoints.

    Args:
        session: Database session
        collection: Collection ORM instance to refresh
        artifact_mgr: ArtifactManager for reading file-based artifacts

    Returns:
        dict with stats:
            - collection_id: str
            - updated: int (artifacts updated)
            - skipped: int (artifacts skipped/unchanged)
            - errors: list of error strings
    """
    updated = 0
    skipped = 0
    errors = []

    logger.debug(f"Refreshing cache for collection '{collection.id}'")

    # Get all CollectionArtifact rows for this collection
    collection_artifacts = (
        session.query(CollectionArtifact).filter_by(collection_id=collection.id).all()
    )

    if not collection_artifacts:
        logger.debug(f"Collection '{collection.id}' has no artifacts to refresh")
        return {
            "collection_id": collection.id,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

    # Process each CollectionArtifact
    for ca in collection_artifacts:
        try:
            # Parse artifact_id (format: "type:name")
            if ":" in ca.artifact_id:
                type_str, artifact_name = ca.artifact_id.split(":", 1)
            else:
                type_str, artifact_name = "unknown", ca.artifact_id

            # Try to get artifact type enum
            artifact_type_enum = None
            try:
                artifact_type_enum = CoreArtifactType(type_str)
            except ValueError:
                # Unknown type - skip
                logger.debug(f"Unknown artifact type '{type_str}' for {ca.artifact_id}")
                skipped += 1
                continue

            # Look up artifact in file system
            file_artifact = None
            try:
                file_artifact = artifact_mgr.show(
                    artifact_name=artifact_name,
                    artifact_type=artifact_type_enum,
                )
            except Exception as e:
                logger.debug(f"File-based lookup failed for {ca.artifact_id}: {e}")
                skipped += 1
                continue

            if not file_artifact:
                skipped += 1
                continue

            # Extract metadata fields from file-based artifact
            metadata = file_artifact.metadata
            description = metadata.description if metadata else None
            author = metadata.author if metadata else None
            license_val = metadata.license if metadata else None
            version = metadata.version if metadata else None

            # Convert tags list to JSON string
            tags_json = None
            if metadata and metadata.tags:
                tags_json = json.dumps(metadata.tags)

            # Source and origin fields
            source = file_artifact.upstream
            origin = file_artifact.origin
            origin_source = file_artifact.origin_source
            resolved_sha = getattr(file_artifact, "resolved_sha", None)
            resolved_version = getattr(file_artifact, "resolved_version", None)

            # Update CollectionArtifact row
            ca.description = description
            ca.author = author
            ca.license = license_val
            ca.tags_json = tags_json
            ca.version = version
            ca.source = source
            ca.origin = origin
            ca.origin_source = origin_source
            ca.resolved_sha = resolved_sha
            ca.resolved_version = resolved_version
            ca.synced_at = datetime.utcnow()
            updated += 1

        except Exception as e:
            error_msg = f"Failed to refresh {ca.artifact_id}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            skipped += 1

    return {
        "collection_id": collection.id,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


@router.post(
    "/refresh-cache",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Refresh metadata cache for all collections",
    description=(
        "Refresh CollectionArtifact metadata cache across all DB collections. "
        "Iterates all collections in the database and refreshes cached metadata "
        "from file-based artifacts. This is a bulk operation and may take time "
        "for large collections."
    ),
    responses={
        200: {"description": "Cache refresh completed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    tags=["user-collections"],
)
async def refresh_all_collections_cache(
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    session: DbSessionDep,
    token: TokenDep,
) -> dict:
    """Refresh CollectionArtifact metadata cache across all DB collections.

    Iterates all collections in the database and refreshes cached metadata
    from file-based artifacts.

    Args:
        artifact_mgr: Artifact manager for listing artifacts
        collection_mgr: Collection manager for listing collections
        session: Database session
        token: Authentication token

    Returns:
        dict with stats:
            - collections_refreshed: int
            - total_updated: int
            - total_skipped: int
            - errors: list of error dicts with collection_id and error messages

    Raises:
        HTTPException: On failure
    """
    import time

    start_time = time.time()
    logger.info("Starting batch cache refresh for all collections")

    try:
        # Query all Collection rows from database
        all_collections = session.query(Collection).all()
        logger.info(f"Found {len(all_collections)} collections to refresh")

        # Handle empty database gracefully
        if not all_collections:
            logger.info("No collections found in database, cache refresh skipped")
            return {
                "success": True,
                "collections_refreshed": 0,
                "total_updated": 0,
                "total_skipped": 0,
                "errors": [],
                "duration_seconds": 0.0,
            }

        collections_refreshed = 0
        total_updated = 0
        total_skipped = 0
        errors = []

        # Process each collection
        for collection in all_collections:
            try:
                result = _refresh_single_collection_cache(
                    session=session,
                    collection=collection,
                    artifact_mgr=artifact_mgr,
                )

                collections_refreshed += 1
                total_updated += result["updated"]
                total_skipped += result["skipped"]

                if result["errors"]:
                    errors.append(
                        {
                            "collection_id": collection.id,
                            "errors": result["errors"],
                        }
                    )

                logger.debug(
                    f"Collection '{collection.id}': updated={result['updated']}, "
                    f"skipped={result['skipped']}"
                )

            except Exception as e:
                error_msg = f"Failed to refresh collection '{collection.id}': {e}"
                logger.warning(error_msg)
                errors.append(
                    {
                        "collection_id": collection.id,
                        "errors": [str(e)],
                    }
                )

        # Commit all changes
        session.commit()

        duration = time.time() - start_time
        logger.info(
            f"Batch cache refresh completed in {duration:.2f}s: "
            f"collections={collections_refreshed}, updated={total_updated}, "
            f"skipped={total_skipped}, errors={len(errors)}"
        )

        return {
            "success": True,
            "collections_refreshed": collections_refreshed,
            "total_updated": total_updated,
            "total_skipped": total_skipped,
            "errors": errors,
            "duration_seconds": round(duration, 2),
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Batch cache refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "batch_cache_refresh_failed",
                "message": f"Failed to refresh all collections cache: {str(e)}",
            },
        )


# =============================================================================
# CRUD Endpoints
# =============================================================================


@router.get(
    "",
    response_model=UserCollectionListResponse,
    summary="List all user collections",
    description="Retrieve a paginated list of all user-defined collections",
    responses={
        200: {"description": "Successfully retrieved collections"},
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_user_collections(
    session: DbSessionDep,
    token: TokenDep,
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (max 100)",
    ),
    after: Optional[str] = Query(
        default=None,
        description="Cursor for pagination (next page)",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Filter by collection name (case-insensitive)",
    ),
    collection_type: Optional[str] = Query(
        default=None,
        description="Filter by collection type (e.g., 'context')",
    ),
) -> UserCollectionListResponse:
    """List all user collections with cursor-based pagination.

    Args:
        session: Database session
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        search: Optional name filter
        collection_type: Optional type filter

    Returns:
        Paginated list of collections

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(
            f"Listing user collections (limit={limit}, after={after}, search={search}, "
            f"type={collection_type})"
        )

        # Build base query
        query = session.query(Collection).order_by(Collection.id)

        # Apply search filter if provided
        if search:
            query = query.filter(Collection.name.ilike(f"%{search}%"))

        # Apply collection_type filter if provided
        if collection_type:
            query = query.filter(Collection.collection_type == collection_type)

        # Get all matching collections (for pagination)
        all_collections = query.all()

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                collection_ids = [c.id for c in all_collections]
                start_idx = collection_ids.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: collection not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_collections = all_collections[start_idx:end_idx]

        # Convert to response format
        items: List[UserCollectionResponse] = [
            collection_to_response(collection, session)
            for collection in page_collections
        ]

        # Build pagination info
        has_next = end_idx < len(all_collections)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(page_collections[0].id) if page_collections else None
        )
        end_cursor = (
            encode_cursor(page_collections[-1].id) if page_collections else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_collections),
        )

        logger.info(f"Retrieved {len(items)} user collections")
        return UserCollectionListResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing user collections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list user collections: {str(e)}",
        )


@router.post(
    "",
    response_model=UserCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user collection",
    description="Create a new user-defined collection",
    responses={
        201: {"description": "Successfully created collection"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "Collection name already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_user_collection(
    request: UserCollectionCreateRequest,
    session: DbSessionDep,
    token: TokenDep,
) -> UserCollectionResponse:
    """Create a new user collection.

    Args:
        request: Collection creation request
        session: Database session
        token: Authentication token

    Returns:
        Created collection details

    Raises:
        HTTPException: If validation fails or name already exists
    """
    try:
        logger.info(f"Creating user collection: {request.name}")

        # Check if name already exists
        existing = session.query(Collection).filter_by(name=request.name).first()
        if existing:
            logger.warning(f"Collection name already exists: {request.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Collection with name '{request.name}' already exists",
            )

        # Create new collection
        collection_id = uuid.uuid4().hex
        collection = Collection(
            id=collection_id,
            name=request.name,
            description=request.description,
            collection_type=request.collection_type,
            context_category=request.context_category,
            created_by=None,  # TODO: Set from authentication context
        )

        session.add(collection)
        session.commit()
        session.refresh(collection)

        logger.info(f"Created user collection: {collection_id} ({request.name})")
        return collection_to_response(collection, session)

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating user collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user collection: {str(e)}",
        )


@router.get(
    "/{collection_id}",
    response_model=UserCollectionWithGroupsResponse,
    summary="Get user collection details",
    description="Retrieve detailed information about a specific collection including groups",
    responses={
        200: {"description": "Successfully retrieved collection"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_user_collection(
    collection_id: str,
    session: DbSessionDep,
    token: TokenDep,
) -> UserCollectionWithGroupsResponse:
    """Get details for a specific user collection.

    Args:
        collection_id: Collection identifier
        session: Database session
        token: Authentication token

    Returns:
        Collection details with nested groups

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(f"Getting user collection: {collection_id}")

        # Fetch collection
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        return collection_to_response_with_groups(collection, session)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting user collection '{collection_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user collection: {str(e)}",
        )


@router.put(
    "/{collection_id}",
    response_model=UserCollectionResponse,
    summary="Update user collection",
    description="Update collection metadata (partial update supported)",
    responses={
        200: {"description": "Successfully updated collection"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        409: {"model": ErrorResponse, "description": "Collection name already exists"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def update_user_collection(
    collection_id: str,
    request: UserCollectionUpdateRequest,
    session: DbSessionDep,
    token: TokenDep,
) -> UserCollectionResponse:
    """Update a user collection.

    Args:
        collection_id: Collection identifier
        request: Update request with fields to modify
        session: Database session
        token: Authentication token

    Returns:
        Updated collection details

    Raises:
        HTTPException: If collection not found, validation fails, or name conflict
    """
    try:
        logger.info(f"Updating user collection: {collection_id}")

        # Check if any update parameters provided
        if (
            request.name is None
            and request.description is None
            and request.collection_type is None
            and request.context_category is None
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one update parameter must be provided",
            )

        # Fetch collection
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Check name uniqueness if changing name
        if request.name is not None and request.name != collection.name:
            existing = session.query(Collection).filter_by(name=request.name).first()
            if existing:
                logger.warning(f"Collection name already exists: {request.name}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Collection with name '{request.name}' already exists",
                )
            collection.name = request.name

        # Update description if provided
        if request.description is not None:
            collection.description = request.description

        # Update collection_type if provided
        if request.collection_type is not None:
            collection.collection_type = request.collection_type

        # Update context_category if provided
        if request.context_category is not None:
            collection.context_category = request.context_category

        session.commit()
        session.refresh(collection)

        logger.info(f"Updated user collection: {collection_id}")
        return collection_to_response(collection, session)

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Error updating user collection '{collection_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user collection: {str(e)}",
        )


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user collection",
    description="Delete a collection and all its groups and artifact associations",
    responses={
        204: {"description": "Successfully deleted collection"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def delete_user_collection(
    collection_id: str,
    session: DbSessionDep,
    token: TokenDep,
) -> None:
    """Delete a user collection.

    Args:
        collection_id: Collection identifier
        session: Database session
        token: Authentication token

    Raises:
        HTTPException: If collection not found or on error

    Note:
        Cascade deletion is handled by the database (groups and associations)
    """
    try:
        logger.info(f"Deleting user collection: {collection_id}")

        # Fetch collection
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        session.delete(collection)
        session.commit()

        # Invalidate cache for deleted collection
        cache = get_collection_count_cache()
        cache.invalidate(collection_id)

        logger.info(f"Deleted user collection: {collection_id}")

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Error deleting user collection '{collection_id}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user collection: {str(e)}",
        )


@router.get(
    "/{collection_id}/artifacts",
    response_model=CollectionArtifactsResponse,
    summary="List artifacts in collection",
    description="Retrieve paginated list of artifacts in a collection with optional type and group filtering",
    responses={
        200: {"description": "Successfully retrieved artifacts"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_artifacts(
    collection_id: str,
    session: DbSessionDep,
    artifact_mgr: ArtifactManagerDep,
    token: TokenDep,
    limit: int = Query(default=20, ge=1, le=100),
    after: Optional[str] = Query(default=None),
    artifact_type: Optional[str] = Query(
        default=None, description="Filter by artifact type"
    ),
    group_id: Optional[str] = Query(
        default=None,
        description="Filter by group membership - only return artifacts belonging to this group",
    ),
    include_groups: bool = Query(
        default=False,
        description="Include group memberships for each artifact in the response",
    ),
) -> CollectionArtifactsResponse:
    """List artifacts in a collection with pagination.

    Args:
        collection_id: Collection identifier
        session: Database session
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional artifact type filter
        group_id: Optional group filter - when provided, only returns artifacts
            that belong to the specified group
        include_groups: When true, include group membership info for each artifact

    Returns:
        Paginated list of artifacts

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(
            f"Listing artifacts for collection '{collection_id}' "
            f"(limit={limit}, after={after}, type={artifact_type}, "
            f"group_id={group_id}, include_groups={include_groups})"
        )

        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Build query for collection artifacts
        query = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id)
            .order_by(CollectionArtifact.artifact_id)
        )

        # Get all matching artifact associations
        all_associations = query.all()

        # Filter by group membership if group_id is provided
        if group_id:
            # Get artifact IDs that belong to the specified group
            group_artifact_ids = {
                ga.artifact_id
                for ga in session.query(GroupArtifact)
                .filter_by(group_id=group_id)
                .all()
            }
            # Filter associations to only those in the group
            all_associations = [
                assoc
                for assoc in all_associations
                if assoc.artifact_id in group_artifact_ids
            ]

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                artifact_ids = [assoc.artifact_id for assoc in all_associations]
                start_idx = artifact_ids.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: artifact not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_associations = all_associations[start_idx:end_idx]

        # Batch fetch group memberships if requested (avoids N+1 queries)
        artifact_groups_map: dict[str, list[ArtifactGroupMembership]] = {}
        if include_groups and page_associations:
            page_artifact_ids = [assoc.artifact_id for assoc in page_associations]

            # Get all groups in this collection
            collection_group_ids = [g.id for g in collection.groups]

            if collection_group_ids:
                # Batch query: get all group-artifact associations for page artifacts
                # within collection's groups
                group_artifacts = (
                    session.query(GroupArtifact, Group)
                    .join(Group, GroupArtifact.group_id == Group.id)
                    .filter(
                        GroupArtifact.artifact_id.in_(page_artifact_ids),
                        GroupArtifact.group_id.in_(collection_group_ids),
                    )
                    .all()
                )

                # Build lookup map: artifact_id -> list of group memberships
                for ga, group in group_artifacts:
                    if ga.artifact_id not in artifact_groups_map:
                        artifact_groups_map[ga.artifact_id] = []
                    artifact_groups_map[ga.artifact_id].append(
                        ArtifactGroupMembership(
                            id=group.id,
                            name=group.name,
                            position=ga.position,
                        )
                    )

        # Fetch artifact metadata for each association
        # Priority: 1. DB cache (if synced_at is set), 2. File system, 3. Marketplace
        items: List[ArtifactSummary] = []
        for assoc in page_associations:
            # Parse artifact_id (format: "type:name")
            if ":" in assoc.artifact_id:
                type_str, artifact_name = assoc.artifact_id.split(":", 1)
            else:
                type_str, artifact_name = "unknown", assoc.artifact_id

            artifact_summary = None

            # 1. Primary: Try to build from DB cache (check synced_at)
            if assoc.synced_at is not None:
                # Cache hit - use cached fields from CollectionArtifact
                tags = None
                if assoc.tags_json:
                    try:
                        tags = json.loads(assoc.tags_json)
                    except (json.JSONDecodeError, TypeError):
                        tags = None

                artifact_summary = ArtifactSummary(
                    id=assoc.artifact_id,
                    name=artifact_name,
                    type=type_str,
                    version=assoc.version,
                    source=assoc.source or assoc.artifact_id,
                    description=assoc.description,
                    author=assoc.author,
                    tags=tags,
                    collections=_get_artifact_collections(session, assoc.artifact_id),
                )
                logger.debug(f"Cache hit for {assoc.artifact_id}")

            # 2. Fallback: Try file-based ArtifactManager on cache miss
            if artifact_summary is None:
                try:
                    # Convert type string to ArtifactType enum
                    artifact_type_enum = None
                    try:
                        artifact_type_enum = CoreArtifactType(type_str)
                    except ValueError:
                        pass

                    file_artifact = artifact_mgr.show(
                        artifact_name=artifact_name,
                        artifact_type=artifact_type_enum,
                    )

                    if file_artifact:
                        # Build ArtifactSummary from file-based artifact
                        artifact_summary = ArtifactSummary(
                            id=assoc.artifact_id,
                            name=file_artifact.name,
                            type=(
                                file_artifact.type.value
                                if hasattr(file_artifact.type, "value")
                                else str(file_artifact.type)
                            ),
                            version=(
                                file_artifact.metadata.version
                                if file_artifact.metadata
                                else None
                            ),
                            source=file_artifact.upstream or assoc.artifact_id,
                            description=(
                                file_artifact.metadata.description
                                if file_artifact.metadata
                                else None
                            ),
                            author=(
                                file_artifact.metadata.author
                                if file_artifact.metadata
                                else None
                            ),
                            tags=(
                                file_artifact.metadata.tags
                                if file_artifact.metadata
                                and file_artifact.metadata.tags
                                else None
                            ),
                            collections=_get_artifact_collections(
                                session, assoc.artifact_id
                            ),
                        )
                        logger.debug(f"File-based lookup for {assoc.artifact_id}")
                except (ValueError, Exception) as e:
                    # Artifact not found in file system, fall through to fallback
                    logger.debug(
                        f"File-based lookup failed for {assoc.artifact_id}: {e}"
                    )

            # 3. Last resort: Fallback to marketplace/database service
            if artifact_summary is None:
                artifact_summary = get_artifact_metadata(session, assoc.artifact_id)
                logger.debug(f"Marketplace fallback for {assoc.artifact_id}")

            # Apply type filter if specified
            if artifact_type is None or artifact_summary.type == artifact_type:
                if include_groups:
                    # Add groups field to artifact summary while preserving all metadata
                    groups = artifact_groups_map.get(assoc.artifact_id, [])
                    items.append(
                        ArtifactSummary(
                            id=assoc.artifact_id,
                            name=artifact_summary.name,
                            type=artifact_summary.type,
                            version=artifact_summary.version,
                            source=artifact_summary.source,
                            description=artifact_summary.description,
                            author=artifact_summary.author,
                            tags=artifact_summary.tags,
                            collections=artifact_summary.collections,
                            groups=groups,
                        )
                    )
                else:
                    items.append(artifact_summary)

        # Build pagination info
        has_next = end_idx < len(all_associations)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(page_associations[0].artifact_id)
            if page_associations
            else None
        )
        end_cursor = (
            encode_cursor(page_associations[-1].artifact_id)
            if page_associations
            else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_associations),
        )

        logger.info(
            f"Retrieved {len(items)} artifacts for collection '{collection_id}'"
        )
        return CollectionArtifactsResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error listing artifacts for collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collection artifacts: {str(e)}",
        )


# =============================================================================
# Artifact Management Endpoints
# =============================================================================


@router.post(
    "/{collection_id}/artifacts",
    status_code=status.HTTP_201_CREATED,
    summary="Add artifacts to collection",
    description="Add one or more artifacts to a collection (idempotent)",
    responses={
        201: {"description": "Successfully added artifacts"},
        200: {"description": "Artifacts already in collection (idempotent)"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def add_artifacts_to_collection(
    collection_id: str,
    request: AddArtifactsRequest,
    session: DbSessionDep,
    token: TokenDep,
) -> dict:
    """Add artifacts to a collection.

    Args:
        collection_id: Collection identifier
        request: Request with artifact IDs
        session: Database session
        token: Authentication token

    Returns:
        Result with count of added artifacts

    Raises:
        HTTPException: If collection not found or validation fails

    Note:
        This operation is idempotent - re-adding existing artifacts returns 200
    """
    try:
        logger.info(
            f"Adding {len(request.artifact_ids)} artifacts to collection: {collection_id}"
        )

        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Get existing associations
        existing_artifact_ids = {
            assoc.artifact_id
            for assoc in session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id)
            .all()
        }

        # Add new associations
        added_count = 0
        for artifact_id in request.artifact_ids:
            if artifact_id not in existing_artifact_ids:
                association = CollectionArtifact(
                    collection_id=collection_id,
                    artifact_id=artifact_id,
                )
                session.add(association)
                added_count += 1

        session.commit()

        # Invalidate collection count cache
        cache = get_collection_count_cache()
        cache.invalidate(collection_id)

        # Invalidate metadata cache for newly added artifacts
        # This ensures they will be refreshed with current metadata
        if added_count > 0:
            invalidate_collection_artifacts(session, collection_id)

        logger.info(
            f"Added {added_count} new artifacts to collection {collection_id} "
            f"({len(request.artifact_ids) - added_count} already present)"
        )

        # Return 200 if all were already present (idempotent), 201 if any added
        status_code = (
            status.HTTP_200_OK if added_count == 0 else status.HTTP_201_CREATED
        )

        return {
            "collection_id": collection_id,
            "added_count": added_count,
            "already_present_count": len(request.artifact_ids) - added_count,
            "total_artifacts": len(existing_artifact_ids) + added_count,
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Error adding artifacts to collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add artifacts to collection: {str(e)}",
        )


@router.delete(
    "/{collection_id}/artifacts/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove artifact from collection",
    description="Remove an artifact from a collection (idempotent)",
    responses={
        204: {"description": "Successfully removed artifact"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def remove_artifact_from_collection(
    collection_id: str,
    artifact_id: str,
    session: DbSessionDep,
    token: TokenDep,
) -> None:
    """Remove an artifact from a collection.

    Args:
        collection_id: Collection identifier
        artifact_id: Artifact identifier
        session: Database session
        token: Authentication token

    Raises:
        HTTPException: If collection not found or on error

    Note:
        This operation is idempotent - removing non-existent artifacts returns 204
    """
    try:
        logger.info(f"Removing artifact {artifact_id} from collection: {collection_id}")

        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Remove association if exists
        association = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=artifact_id)
            .first()
        )

        if association:
            session.delete(association)
            session.commit()

            # Invalidate cache for this collection
            cache = get_collection_count_cache()
            cache.invalidate(collection_id)

            logger.info(
                f"Removed artifact {artifact_id} from collection {collection_id}"
            )
        else:
            logger.info(
                f"Artifact {artifact_id} not in collection {collection_id} (idempotent)"
            )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Error removing artifact from collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove artifact from collection: {str(e)}",
        )


# =============================================================================
# Entity Management Endpoints (Context Entities)
# =============================================================================


@router.post(
    "/{collection_id}/entities/{entity_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Add entity to collection",
    description="Add a context entity to a collection (idempotent)",
    responses={
        201: {"description": "Successfully added entity"},
        200: {"description": "Entity already in collection (idempotent)"},
        404: {
            "model": ErrorResponse,
            "description": "Collection or entity not found",
        },
        409: {
            "model": ErrorResponse,
            "description": "Entity already exists in collection",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def add_entity_to_collection(
    collection_id: str,
    entity_id: str,
    session: DbSessionDep,
    token: TokenDep,
) -> dict:
    """Add a context entity to a collection.

    Args:
        collection_id: Collection identifier
        entity_id: Entity (artifact) identifier
        session: Database session
        token: Authentication token

    Returns:
        Result with status information

    Raises:
        HTTPException: If collection not found or entity doesn't exist

    Note:
        This operation is idempotent - re-adding existing entities returns 200
    """
    try:
        logger.info(f"Adding entity {entity_id} to collection: {collection_id}")

        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Check if entity exists in artifacts table
        entity = session.query(Artifact).filter_by(id=entity_id).first()
        if not entity:
            logger.warning(f"Entity not found: {entity_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found",
            )

        # Check if association already exists
        existing = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=entity_id)
            .first()
        )

        if existing:
            logger.info(
                f"Entity {entity_id} already in collection {collection_id} (idempotent)"
            )
            return {
                "collection_id": collection_id,
                "entity_id": entity_id,
                "status": "already_present",
            }

        # Create association
        association = CollectionArtifact(
            collection_id=collection_id,
            artifact_id=entity_id,
        )
        session.add(association)
        session.commit()

        logger.info(f"Added entity {entity_id} to collection {collection_id}")
        return {
            "collection_id": collection_id,
            "entity_id": entity_id,
            "status": "added",
        }

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Error adding entity to collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add entity to collection: {str(e)}",
        )


@router.delete(
    "/{collection_id}/entities/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove entity from collection",
    description="Remove a context entity from a collection (idempotent)",
    responses={
        204: {"description": "Successfully removed entity"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def remove_entity_from_collection(
    collection_id: str,
    entity_id: str,
    session: DbSessionDep,
    token: TokenDep,
) -> None:
    """Remove a context entity from a collection.

    Args:
        collection_id: Collection identifier
        entity_id: Entity (artifact) identifier
        session: Database session
        token: Authentication token

    Raises:
        HTTPException: If collection not found or on error

    Note:
        This operation is idempotent - removing non-existent entities returns 204
    """
    try:
        logger.info(f"Removing entity {entity_id} from collection: {collection_id}")

        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Remove association if exists
        association = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id, artifact_id=entity_id)
            .first()
        )

        if association:
            session.delete(association)
            session.commit()
            logger.info(f"Removed entity {entity_id} from collection {collection_id}")
        else:
            logger.info(
                f"Entity {entity_id} not in collection {collection_id} (idempotent)"
            )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Error removing entity from collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove entity from collection: {str(e)}",
        )


@router.get(
    "/{collection_id}/entities",
    response_model=CollectionArtifactsResponse,
    summary="List entities in collection",
    description="Retrieve paginated list of context entities in a collection",
    responses={
        200: {"description": "Successfully retrieved entities"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_entities(
    collection_id: str,
    session: DbSessionDep,
    token: TokenDep,
    limit: int = Query(default=20, ge=1, le=100),
    after: Optional[str] = Query(default=None),
) -> CollectionArtifactsResponse:
    """List context entities in a collection with pagination.

    Args:
        collection_id: Collection identifier
        session: Database session
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page

    Returns:
        Paginated list of entities (artifacts)

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(
            f"Listing entities for collection '{collection_id}' "
            f"(limit={limit}, after={after})"
        )

        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            logger.warning(f"User collection not found: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Build query for collection artifacts
        query = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id)
            .order_by(CollectionArtifact.artifact_id)
        )

        # Get all matching artifact associations
        all_associations = query.all()

        # Decode cursor if provided
        start_idx = 0
        if after:
            cursor_value = decode_cursor(after)
            try:
                artifact_ids = [assoc.artifact_id for assoc in all_associations]
                start_idx = artifact_ids.index(cursor_value) + 1
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid cursor: entity not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_associations = all_associations[start_idx:end_idx]

        # Fetch artifact metadata for each association using fallback service
        # This ensures consistent metadata including description, tags, and collections
        items: List[ArtifactSummary] = []
        for assoc in page_associations:
            artifact_summary = get_artifact_metadata(session, assoc.artifact_id)
            items.append(artifact_summary)

        # Build pagination info
        has_next = end_idx < len(all_associations)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(page_associations[0].artifact_id)
            if page_associations
            else None
        )
        end_cursor = (
            encode_cursor(page_associations[-1].artifact_id)
            if page_associations
            else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_associations),
        )

        logger.info(f"Retrieved {len(items)} entities for collection '{collection_id}'")
        return CollectionArtifactsResponse(items=items, page_info=page_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error listing entities for collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collection entities: {str(e)}",
        )


# =============================================================================
# Cache Refresh Endpoints
# =============================================================================


@router.post(
    "/{collection_id}/refresh-cache",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["user-collections"],
    summary="Refresh collection metadata cache (DB-backed)",
    description=(
        "Refresh CollectionArtifact metadata cache for a specific DB collection. "
        "This is separate from /{collection_id}/refresh, which refreshes file-based "
        "collections. This endpoint targets only the DB cache, reading current "
        "file-based artifact metadata and updating CollectionArtifact cache rows."
    ),
    responses={
        200: {"description": "Cache refresh completed successfully"},
        404: {
            "model": ErrorResponse,
            "description": "Collection not found in database",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def refresh_collection_cache(
    collection_id: str,
    artifact_mgr: ArtifactManagerDep,
    collection_mgr: CollectionManagerDep,
    db_session: DbSessionDep,
    token: TokenDep,
) -> dict:
    """Refresh CollectionArtifact metadata cache for a specific DB collection.

    IMPORTANT: This is separate from /{collection_id}/refresh, which refreshes
    file-based collections. This endpoint targets only the DB cache.

    Reads current file-based artifact metadata and updates CollectionArtifact
    cache rows for all artifacts in the specified collection.

    Args:
        collection_id: UUID or name of the collection
        artifact_mgr: Artifact manager for reading file-based metadata
        collection_mgr: Collection manager for file-based collection access
        db_session: Database session
        token: Authentication token

    Returns:
        dict with refresh stats: updated_count, skipped_count, errors

    Raises:
        HTTPException: If collection not found in database
    """
    import json
    import time

    logger.info(f"Starting DB cache refresh for collection '{collection_id}'")
    start_time = time.time()

    # 1. Validate collection exists in database (Collection table)
    collection = db_session.query(Collection).filter_by(id=collection_id).first()
    if not collection:
        logger.error(f"Collection not found in database: {collection_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "collection_not_found",
                "collection_id": collection_id,
                "message": f"Collection '{collection_id}' not found in database",
            },
        )

    # 2. Query all CollectionArtifact rows for this collection_id
    collection_artifacts = (
        db_session.query(CollectionArtifact)
        .filter_by(collection_id=collection_id)
        .all()
    )

    logger.debug(
        f"Found {len(collection_artifacts)} artifacts in collection '{collection_id}'"
    )

    updated_count = 0
    skipped_count = 0
    errors: list[str] = []

    # 3. For each artifact: Read file-based metadata via ArtifactManager, update cache
    for ca in collection_artifacts:
        try:
            # Parse artifact_id (format: "type:name")
            if ":" in ca.artifact_id:
                type_str, artifact_name = ca.artifact_id.split(":", 1)
            else:
                type_str, artifact_name = "unknown", ca.artifact_id

            # Try to get artifact from file-based manager
            artifact_type_enum = None
            try:
                artifact_type_enum = CoreArtifactType(type_str)
            except ValueError:
                pass

            file_artifact = artifact_mgr.show(
                artifact_name=artifact_name,
                artifact_type=artifact_type_enum,
            )

            if file_artifact is None:
                # Artifact no longer exists in file system
                logger.debug(
                    f"Artifact '{ca.artifact_id}' not found in file system, skipping"
                )
                skipped_count += 1
                continue

            # Extract metadata fields from artifact
            metadata = file_artifact.metadata
            description = metadata.description if metadata else None
            author = metadata.author if metadata else None
            license_val = metadata.license if metadata else None
            version = metadata.version if metadata else None

            # Convert tags list to JSON string
            tags_json = None
            if metadata and metadata.tags:
                tags_json = json.dumps(metadata.tags)

            # Source and origin fields
            source = file_artifact.upstream
            origin = file_artifact.origin
            origin_source = file_artifact.origin_source
            resolved_sha = getattr(file_artifact, "resolved_sha", None)
            resolved_version = getattr(file_artifact, "resolved_version", None)

            # Update cache fields
            ca.description = description
            ca.author = author
            ca.license = license_val
            ca.tags_json = tags_json
            ca.version = version
            ca.source = source
            ca.origin = origin
            ca.origin_source = origin_source
            ca.resolved_sha = resolved_sha
            ca.resolved_version = resolved_version
            ca.synced_at = datetime.utcnow()

            updated_count += 1
            logger.debug(f"Updated cache for artifact '{ca.artifact_id}'")

        except Exception as e:
            error_msg = f"Failed to refresh cache for artifact '{ca.artifact_id}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
            skipped_count += 1
            continue

    # 4. Commit all updates
    try:
        db_session.commit()
        duration = time.time() - start_time
        logger.info(
            f"DB cache refresh for collection '{collection_id}' completed: "
            f"updated={updated_count}, skipped={skipped_count}, errors={len(errors)}, "
            f"duration={duration:.2f}s"
        )
    except Exception as e:
        db_session.rollback()
        logger.error(
            f"Failed to commit cache updates for collection '{collection_id}': {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "cache_commit_failed",
                "collection_id": collection_id,
                "message": f"Failed to commit cache updates: {str(e)}",
            },
        )

    # 5. Return stats
    return {
        "collection_id": collection_id,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": errors,
    }


# =============================================================================
# File-Based Refresh Endpoint
# =============================================================================


@router.post(
    "/{collection_id}/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh collection artifact metadata",
    description="Refresh metadata for artifacts in a collection from their upstream GitHub sources. Use mode=check to detect updates without applying changes.",
    responses={
        200: {
            "description": "Refresh completed successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "metadata_refresh": {
                            "summary": "Metadata refresh (default)",
                            "value": {
                                "collection_id": "default",
                                "status": "completed",
                                "mode": "metadata_only",
                                "summary": {
                                    "refreshed_count": 5,
                                    "unchanged_count": 10,
                                },
                            },
                        },
                        "check_updates": {
                            "summary": "Check for updates (mode=check)",
                            "value": {
                                "collection_id": "default",
                                "updates_available": 3,
                                "up_to_date": 12,
                                "results": [],
                            },
                        },
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {
            "model": ErrorResponse,
            "description": "Internal server error during refresh",
        },
    },
)
async def refresh_collection(
    collection_id: str,
    collection_mgr: CollectionManagerDep,
    token: TokenDep,
    request: RefreshRequest = Body(...),
    mode: Optional[RefreshModeEnum] = Query(
        None, description="Override request body mode"
    ),
):
    """Refresh artifact metadata for a collection from upstream GitHub sources.

    Supports three modes:
    - metadata_only: Update metadata fields without version changes (default)
    - check_only: Detect available updates without applying changes
    - sync: Full synchronization including version updates (reserved)

    Args:
        collection_id: Collection identifier
        request: Refresh request with mode, filters, and dry_run options
        mode: Optional query param to override request body mode
        collection_mgr: Collection manager dependency
        token: Authentication token

    Returns:
        RefreshResponse (for metadata_only/sync) or UpdateCheckResponse (for check_only)

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(f"Starting refresh for collection {collection_id}")

        # Validate field names if provided
        if request.fields is not None:
            try:
                validated_fields, invalid_fields = validate_fields(
                    request.fields, strict=False
                )
                if invalid_fields:
                    # Return 422 with details about invalid fields
                    from skillmeat.core.refresher import REFRESHABLE_FIELDS

                    valid_list = ", ".join(sorted(REFRESHABLE_FIELDS))
                    logger.warning(
                        f"Invalid field names in refresh request: {invalid_fields}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Invalid field name(s): {', '.join(invalid_fields)}. "
                            f"Valid fields: {valid_list}"
                        ),
                    )
                # Use validated (case-normalized) fields
                request.fields = validated_fields
            except ValueError as e:
                # This shouldn't happen with strict=False, but handle it anyway
                logger.error(f"Unexpected validation error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(e),
                )

        # Check if collection exists in collection manager
        if collection_id not in collection_mgr.list_collections():
            logger.warning(f"Collection not found for refresh: {collection_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Determine refresh mode - query param overrides request body
        effective_mode = mode if mode is not None else request.mode

        # Map RefreshModeEnum to core RefreshMode
        mode_mapping = {
            RefreshModeEnum.METADATA_ONLY: RefreshMode.METADATA_ONLY,
            RefreshModeEnum.CHECK_ONLY: RefreshMode.CHECK_ONLY,
            RefreshModeEnum.SYNC: RefreshMode.SYNC,
        }
        core_mode = mode_mapping[effective_mode]

        # Create CollectionRefresher
        refresher = CollectionRefresher(collection_mgr)

        # Branch based on mode
        if effective_mode == RefreshModeEnum.CHECK_ONLY:
            # Check mode - detect updates without applying changes
            logger.info(f"Running update check for collection {collection_id}")
            update_results = refresher.check_updates(
                collection_name=collection_id,
                artifact_filter=request.artifact_filter,
            )

            logger.info(
                f"Update check completed: "
                f"{sum(1 for r in update_results if r.update_available)} updates available"
            )

            # Return UpdateCheckResponse
            return UpdateCheckResponse.from_update_results(
                collection_id=collection_id,
                results=update_results,
            )
        else:
            # Metadata or sync mode - execute refresh
            result = refresher.refresh_collection(
                collection_name=collection_id,
                mode=core_mode,
                dry_run=request.dry_run,
                fields=request.fields,
                artifact_filter=request.artifact_filter,
            )

            logger.info(
                f"Refresh completed: {result.refreshed_count} refreshed, "
                f"{result.unchanged_count} unchanged"
            )

            # Return RefreshResponse
            return RefreshResponse.from_refresh_result(
                collection_id=collection_id,
                result=result,
                mode=effective_mode,
                dry_run=request.dry_run,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error refreshing collection '{collection_id}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh collection: {str(e)}",
        )


# =============================================================================
# Cache Statistics Endpoint (TASK-3.4)
# =============================================================================


@router.get(
    "/cache-stats",
    response_model=dict,
    tags=["user-collections"],
    summary="Get artifact cache statistics",
    description="Get statistics about artifact metadata cache health including "
    "total artifacts, fresh/stale counts, and staleness percentage.",
)
async def get_cache_stats(
    db_session: DbSessionDep,
    ttl_seconds: int = Query(
        default=None,
        description="Custom TTL in seconds for staleness calculation. "
        "Default is 30 minutes (1800 seconds).",
        ge=60,
        le=86400,
    ),
    collection_id: Optional[str] = Query(
        default=None,
        description="Filter stats to a specific collection ID. "
        "If not provided, stats are for all collections.",
    ),
) -> dict:
    """Get statistics about artifact metadata cache health.

    This endpoint returns metrics about the CollectionArtifact cache,
    useful for monitoring cache freshness and identifying performance issues.

    Returns:
        Dictionary with cache statistics:
        - total_artifacts: Total number of cached artifacts
        - fresh_count: Artifacts with synced_at within TTL
        - stale_count: Artifacts needing refresh (synced_at older than TTL or NULL)
        - percentage_stale: Percentage of stale artifacts (0-100)
        - oldest_sync_age_seconds: Age of oldest cached metadata in seconds
        - ttl_seconds: The TTL used for calculation
        - collection_id: The collection filter if provided

    Example response:
        {
            "total_artifacts": 42,
            "fresh_count": 40,
            "stale_count": 2,
            "percentage_stale": 4.8,
            "oldest_sync_age_seconds": 1234,
            "ttl_seconds": 1800
        }
    """
    from skillmeat.api.services.artifact_cache_service import (
        DEFAULT_METADATA_TTL_SECONDS,
        get_staleness_stats,
    )

    # Use default TTL if not provided
    effective_ttl = (
        ttl_seconds if ttl_seconds is not None else DEFAULT_METADATA_TTL_SECONDS
    )

    try:
        stats = get_staleness_stats(db_session, effective_ttl)

        # Add collection_id filter if provided
        if collection_id:
            # Re-query with collection filter
            stats = _get_filtered_staleness_stats(
                db_session, effective_ttl, collection_id
            )

        logger.debug(
            f"Cache stats requested: total={stats['total_artifacts']}, "
            f"stale={stats['stale_count']} ({stats['percentage_stale']}%)"
        )

        return stats

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}",
        )


def _get_filtered_staleness_stats(
    session: Session,
    ttl_seconds: int,
    collection_id: str,
) -> dict:
    """Get staleness stats filtered to a specific collection.

    Args:
        session: Database session
        ttl_seconds: TTL for staleness calculation
        collection_id: Collection ID to filter by

    Returns:
        Dictionary with staleness statistics for the collection
    """
    from datetime import timedelta

    cutoff_time = datetime.utcnow() - timedelta(seconds=ttl_seconds)

    # Filter to specific collection
    total = (
        session.query(CollectionArtifact)
        .filter(CollectionArtifact.collection_id == collection_id)
        .count()
    )

    if total == 0:
        return {
            "total_artifacts": 0,
            "stale_count": 0,
            "fresh_count": 0,
            "oldest_sync_age_seconds": 0,
            "percentage_stale": 0.0,
            "ttl_seconds": ttl_seconds,
            "collection_id": collection_id,
        }

    # Count stale artifacts in this collection
    stale_count = (
        session.query(CollectionArtifact)
        .filter(CollectionArtifact.collection_id == collection_id)
        .filter(
            (CollectionArtifact.synced_at.is_(None))
            | (CollectionArtifact.synced_at < cutoff_time)
        )
        .count()
    )

    # Find oldest sync time in this collection
    oldest = (
        session.query(CollectionArtifact.synced_at)
        .filter(CollectionArtifact.collection_id == collection_id)
        .filter(CollectionArtifact.synced_at.isnot(None))
        .order_by(CollectionArtifact.synced_at.asc())
        .first()
    )

    oldest_age = 0
    if oldest and oldest[0]:
        oldest_age = (datetime.utcnow() - oldest[0]).total_seconds()

    return {
        "total_artifacts": total,
        "stale_count": stale_count,
        "fresh_count": total - stale_count,
        "oldest_sync_age_seconds": oldest_age,
        "percentage_stale": round((stale_count / total * 100), 1) if total > 0 else 0.0,
        "ttl_seconds": ttl_seconds,
        "collection_id": collection_id,
    }
