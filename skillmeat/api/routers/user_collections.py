"""User Collections API endpoints.

Provides REST API for managing database-backed user collections (organizational).
Distinct from file-based collections in collections.py router.
"""

import base64
import logging
import uuid
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse, PageInfo
from skillmeat.api.schemas.user_collections import (
    AddArtifactsRequest,
    ArtifactSummary,
    CollectionArtifactsResponse,
    GroupSummary,
    UserCollectionCreateRequest,
    UserCollectionListResponse,
    UserCollectionResponse,
    UserCollectionUpdateRequest,
    UserCollectionWithGroupsResponse,
)
from skillmeat.cache.models import (
    Artifact,
    Collection,
    CollectionArtifact,
    Group,
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
        session.query(CollectionArtifact)
        .filter_by(collection_id=collection.id)
        .count()
    )

    return UserCollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        created_by=collection.created_by,
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
) -> UserCollectionListResponse:
    """List all user collections with cursor-based pagination.

    Args:
        session: Database session
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        search: Optional name filter

    Returns:
        Paginated list of collections

    Raises:
        HTTPException: On error
    """
    try:
        logger.info(
            f"Listing user collections (limit={limit}, after={after}, search={search})"
        )

        # Build base query
        query = session.query(Collection).order_by(Collection.id)

        # Apply search filter if provided
        if search:
            query = query.filter(Collection.name.ilike(f"%{search}%"))

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

        start_cursor = encode_cursor(page_collections[0].id) if page_collections else None
        end_cursor = encode_cursor(page_collections[-1].id) if page_collections else None

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
        if request.name is None and request.description is None:
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
    description="Retrieve paginated list of artifacts in a collection with optional type filtering",
    responses={
        200: {"description": "Successfully retrieved artifacts"},
        404: {"model": ErrorResponse, "description": "Collection not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def list_collection_artifacts(
    collection_id: str,
    session: DbSessionDep,
    token: TokenDep,
    limit: int = Query(default=20, ge=1, le=100),
    after: Optional[str] = Query(default=None),
    artifact_type: Optional[str] = Query(default=None, description="Filter by artifact type"),
) -> CollectionArtifactsResponse:
    """List artifacts in a collection with pagination.

    Args:
        collection_id: Collection identifier
        session: Database session
        token: Authentication token
        limit: Number of items per page
        after: Cursor for next page
        artifact_type: Optional artifact type filter

    Returns:
        Paginated list of artifacts

    Raises:
        HTTPException: If collection not found or on error
    """
    try:
        logger.info(
            f"Listing artifacts for collection '{collection_id}' "
            f"(limit={limit}, after={after}, type={artifact_type})"
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
                    detail="Invalid cursor: artifact not found",
                )

        # Paginate
        end_idx = start_idx + limit
        page_associations = all_associations[start_idx:end_idx]

        # Fetch artifact metadata for each association
        items: List[ArtifactSummary] = []
        for assoc in page_associations:
            # Try to get artifact metadata from cache database
            artifact = session.query(Artifact).filter_by(id=assoc.artifact_id).first()

            if artifact:
                # If artifact metadata exists, use it
                artifact_summary = ArtifactSummary(
                    name=artifact.name,
                    type=artifact.type,
                    version=artifact.deployed_version or artifact.upstream_version,
                    source=artifact.source or assoc.artifact_id,
                )
            else:
                # TODO: Fetch artifact metadata from artifact storage system
                # For now, return artifact_id as both name and source
                artifact_summary = ArtifactSummary(
                    name=assoc.artifact_id,
                    type="unknown",
                    version=None,
                    source=assoc.artifact_id,
                )

            # Apply type filter if specified
            if artifact_type is None or artifact_summary.type == artifact_type:
                items.append(artifact_summary)

        # Build pagination info
        has_next = end_idx < len(all_associations)
        has_previous = start_idx > 0

        start_cursor = (
            encode_cursor(page_associations[0].artifact_id) if page_associations else None
        )
        end_cursor = (
            encode_cursor(page_associations[-1].artifact_id) if page_associations else None
        )

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            total_count=len(all_associations),
        )

        logger.info(f"Retrieved {len(items)} artifacts for collection '{collection_id}'")
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

        logger.info(
            f"Added {added_count} new artifacts to collection {collection_id} "
            f"({len(request.artifact_ids) - added_count} already present)"
        )

        # Return 200 if all were already present (idempotent), 201 if any added
        status_code = status.HTTP_200_OK if added_count == 0 else status.HTTP_201_CREATED

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
        logger.info(
            f"Removing artifact {artifact_id} from collection: {collection_id}"
        )

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
