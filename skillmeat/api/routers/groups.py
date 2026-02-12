"""Groups API router for managing artifact groups within collections.

This router provides endpoints for organizing artifacts into logical groups
within collections. Groups support custom ordering and can contain multiple
artifacts with their own position-based ordering.

API Endpoints:
    POST /groups - Create new group in a collection
    GET /groups?collection_id={id} - List groups in a collection
    GET /groups/{id} - Get group by ID with artifacts
    PUT /groups/{id} - Update group metadata
    DELETE /groups/{id} - Delete group
    POST /groups/{id}/copy - Copy group to another collection
    PUT /groups/reorder - Bulk reorder groups
    POST /groups/{id}/artifacts - Add artifacts to group
    DELETE /groups/{id}/artifacts/{artifact_id} - Remove artifact from group
    PUT /groups/{id}/artifacts/{artifact_id} - Update artifact position
    POST /groups/{id}/reorder-artifacts - Bulk reorder artifacts in group
"""

import json
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from skillmeat.api.schemas.groups import (
    AddGroupArtifactsRequest,
    ArtifactPositionUpdate,
    CopyGroupRequest,
    GroupArtifactResponse,
    GroupCreateRequest,
    GroupListResponse,
    GroupPositionUpdate,
    GroupReorderRequest,
    GroupResponse,
    GroupUpdateRequest,
    GroupWithArtifactsResponse,
    ReorderArtifactsRequest,
)
from skillmeat.cache.models import (
    Collection,
    CollectionArtifact,
    Group,
    GroupArtifact,
    get_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
)


def _parse_group_tags(tags_json: Optional[str]) -> list[str]:
    """Parse group tags JSON safely."""
    if not tags_json:
        return []
    try:
        parsed = json.loads(tags_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [tag for tag in parsed if isinstance(tag, str)]


def _build_group_response(
    session,
    group: Group,
    *,
    artifact_count: Optional[int] = None,
) -> GroupResponse:
    """Map ORM Group model to API response with metadata fields."""
    count = (
        artifact_count
        if artifact_count is not None
        else session.query(GroupArtifact).filter_by(group_id=group.id).count()
    )
    return GroupResponse(
        id=group.id,
        collection_id=group.collection_id,
        name=group.name,
        description=group.description,
        tags=_parse_group_tags(group.tags_json),
        color=group.color or "slate",
        icon=group.icon or "layers",
        position=group.position,
        created_at=group.created_at,
        updated_at=group.updated_at,
        artifact_count=count,
    )


# =============================================================================
# Group CRUD Operations
# =============================================================================


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new group",
    description="""
    Create a new group within a collection for organizing artifacts.

    Group names must be unique within their collection. Position determines
    the display order (0-based, default 0).
    """,
)
async def create_group(request: GroupCreateRequest) -> GroupResponse:
    """Create a new group in a collection.

    Args:
        request: Group creation request with collection_id, name, description, position

    Returns:
        Created group with metadata

    Raises:
        HTTPException 400: If group name already exists in collection
        HTTPException 404: If collection not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Verify collection exists
        collection = (
            session.query(Collection).filter_by(id=request.collection_id).first()
        )
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{request.collection_id}' not found",
            )

        # Check unique name constraint
        existing = (
            session.query(Group)
            .filter_by(collection_id=request.collection_id, name=request.name)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group '{request.name}' already exists in collection '{request.collection_id}'",
            )

        # Create group
        group = Group(
            id=uuid.uuid4().hex,
            collection_id=request.collection_id,
            name=request.name,
            description=request.description,
            tags_json=json.dumps(request.tags or []),
            color=request.color,
            icon=request.icon,
            position=request.position,
        )

        session.add(group)
        session.commit()
        session.refresh(group)

        logger.info(
            f"Created group: {group.id} ('{group.name}') in collection {group.collection_id}"
        )

        return _build_group_response(session, group, artifact_count=0)

    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error creating group: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name must be unique within collection",
        ) from e
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create group: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create group",
        ) from e
    finally:
        session.close()


@router.get(
    "",
    response_model=GroupListResponse,
    summary="List groups in collection",
    description="""
    List all groups in a collection, ordered by position.

    Optionally filter by name using the search parameter, or filter to only
    groups containing a specific artifact using the artifact_id parameter.
    """,
)
async def list_groups(
    collection_id: str = Query(..., description="Collection ID to list groups from"),
    search: Optional[str] = Query(
        None, description="Filter groups by name (case-insensitive)"
    ),
    artifact_id: Optional[str] = Query(
        None, description="Filter to groups containing this artifact"
    ),
) -> GroupListResponse:
    """List all groups in a collection.

    Args:
        collection_id: Collection ID (required)
        search: Optional name filter
        artifact_id: Optional artifact ID filter - returns only groups containing this artifact

    Returns:
        List of groups ordered by position

    Raises:
        HTTPException 404: If collection not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Verify collection exists
        collection = session.query(Collection).filter_by(id=collection_id).first()
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_id}' not found",
            )

        # Build query
        query = session.query(Group).filter_by(collection_id=collection_id)

        # Apply search filter if provided
        if search:
            query = query.filter(Group.name.ilike(f"%{search}%"))

        # Apply artifact_id filter if provided
        if artifact_id:
            query = query.join(GroupArtifact).filter(
                GroupArtifact.artifact_id == artifact_id
            )

        # Order by position
        query = query.order_by(Group.position)

        groups = query.all()

        # Build response with artifact counts
        group_responses = []
        for group in groups:
            artifact_count = (
                session.query(GroupArtifact).filter_by(group_id=group.id).count()
            )
            group_responses.append(
                _build_group_response(
                    session,
                    group,
                    artifact_count=artifact_count,
                )
            )

        logger.info(
            f"Listed {len(group_responses)} groups from collection {collection_id}"
            + (f" (search: {search})" if search else "")
            + (f" (artifact_id: {artifact_id})" if artifact_id else "")
        )

        return GroupListResponse(
            groups=group_responses,
            total=len(group_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list groups: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list groups",
        ) from e
    finally:
        session.close()


@router.get(
    "/{group_id}",
    response_model=GroupWithArtifactsResponse,
    summary="Get group details",
    description="""
    Get detailed information about a group including its artifacts.

    Artifacts are returned ordered by their position within the group.
    """,
)
async def get_group(group_id: str) -> GroupWithArtifactsResponse:
    """Get a single group with its artifacts.

    Args:
        group_id: Group ID

    Returns:
        Group with artifacts list

    Raises:
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        group = session.query(Group).filter_by(id=group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{group_id}' not found",
            )

        # Get artifacts ordered by position
        group_artifacts = (
            session.query(GroupArtifact)
            .filter_by(group_id=group_id)
            .order_by(GroupArtifact.position)
            .all()
        )

        artifacts = [
            GroupArtifactResponse(
                artifact_id=ga.artifact_id,
                position=ga.position,
                added_at=ga.added_at,
            )
            for ga in group_artifacts
        ]

        logger.info(f"Retrieved group {group_id} with {len(artifacts)} artifacts")

        return GroupWithArtifactsResponse(
            id=group.id,
            collection_id=group.collection_id,
            name=group.name,
            description=group.description,
            tags=_parse_group_tags(group.tags_json),
            color=group.color or "slate",
            icon=group.icon or "layers",
            position=group.position,
            created_at=group.created_at,
            updated_at=group.updated_at,
            artifact_count=len(artifacts),
            artifacts=artifacts,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get group",
        ) from e
    finally:
        session.close()


@router.put(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Update group",
    description="""
    Update group metadata (name, description, position).

    All fields are optional. Only provided fields will be updated.
    """,
)
async def update_group(group_id: str, request: GroupUpdateRequest) -> GroupResponse:
    """Update a group's metadata.

    Args:
        group_id: Group ID
        request: Update request with optional name, description, position

    Returns:
        Updated group

    Raises:
        HTTPException 400: If new name conflicts with existing group
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        group = session.query(Group).filter_by(id=group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{group_id}' not found",
            )

        # Check name uniqueness if changing name
        if request.name and request.name != group.name:
            existing = (
                session.query(Group)
                .filter_by(collection_id=group.collection_id, name=request.name)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Group '{request.name}' already exists in collection",
                )

        # Update fields
        if request.name is not None:
            group.name = request.name
        if request.description is not None:
            group.description = request.description
        if request.tags is not None:
            group.tags_json = json.dumps(request.tags)
        if request.color is not None:
            group.color = request.color
        if request.icon is not None:
            group.icon = request.icon
        if request.position is not None:
            group.position = request.position

        session.commit()
        session.refresh(group)

        logger.info(f"Updated group {group_id}")

        return _build_group_response(session, group)

    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error updating group: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name must be unique within collection",
        ) from e
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update group",
        ) from e
    finally:
        session.close()


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete group",
    description="""
    Delete a group from a collection.

    Artifacts are removed from the group but not deleted from the collection.
    The group-artifact associations are cascaded automatically.
    """,
)
async def delete_group(group_id: str) -> None:
    """Delete a group.

    Args:
        group_id: Group ID

    Raises:
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        group = session.query(Group).filter_by(id=group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{group_id}' not found",
            )

        # Delete group (cascade will remove group_artifacts)
        session.delete(group)
        session.commit()

        logger.info(f"Deleted group {group_id}")

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to delete group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete group",
        ) from e
    finally:
        session.close()


# =============================================================================
# Group Copy Operations
# =============================================================================


@router.post(
    "/{group_id}/copy",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Copy group to another collection",
    description="""
    Copy a group with all its artifacts to another collection.

    The new group will have the same name with " (Copy)" suffix.
    If an artifact is not already in the target collection, it will be added.
    Duplicate artifacts (already in target collection) are silently skipped.
    """,
)
async def copy_group(
    group_id: str,
    request: CopyGroupRequest,
) -> GroupResponse:
    """Copy a group to another collection.

    Args:
        group_id: Source group ID to copy
        request: Copy request with target_collection_id

    Returns:
        The newly created group in the target collection

    Raises:
        HTTPException 404: If source group or target collection not found
        HTTPException 400: If group name already exists in target collection
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Verify source group exists and load its artifacts
        source_group = session.query(Group).filter_by(id=group_id).first()
        if not source_group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{group_id}' not found",
            )

        # Verify target collection exists
        target_collection = (
            session.query(Collection).filter_by(id=request.target_collection_id).first()
        )
        if not target_collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target collection '{request.target_collection_id}' not found",
            )

        # Create new group name with " (Copy)" suffix
        new_group_name = f"{source_group.name} (Copy)"

        # Check if group name already exists in target collection
        existing_group = (
            session.query(Group)
            .filter_by(collection_id=request.target_collection_id, name=new_group_name)
            .first()
        )
        if existing_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group '{new_group_name}' already exists in target collection",
            )

        # Determine position for new group (append to end)
        max_position = (
            session.query(Group.position)
            .filter_by(collection_id=request.target_collection_id)
            .order_by(Group.position.desc())
            .first()
        )
        new_position = (max_position[0] + 1) if max_position else 0

        # Create new group in target collection
        new_group = Group(
            id=uuid.uuid4().hex,
            collection_id=request.target_collection_id,
            name=new_group_name,
            description=source_group.description,
            tags_json=source_group.tags_json or "[]",
            color=source_group.color or "slate",
            icon=source_group.icon or "layers",
            position=new_position,
        )
        session.add(new_group)
        session.flush()  # Get the new group ID

        # Get source group artifacts
        source_artifacts = (
            session.query(GroupArtifact)
            .filter_by(group_id=group_id)
            .order_by(GroupArtifact.position)
            .all()
        )

        # Get existing artifacts in target collection
        existing_collection_artifacts = {
            ca.artifact_id
            for ca in session.query(CollectionArtifact)
            .filter_by(collection_id=request.target_collection_id)
            .all()
        }

        # Copy artifacts to new group and add to collection if needed
        for source_ga in source_artifacts:
            # Add artifact to target collection if not already there
            if source_ga.artifact_id not in existing_collection_artifacts:
                collection_artifact = CollectionArtifact(
                    collection_id=request.target_collection_id,
                    artifact_id=source_ga.artifact_id,
                )
                session.add(collection_artifact)
                existing_collection_artifacts.add(source_ga.artifact_id)

            # Add artifact to new group with same position
            new_group_artifact = GroupArtifact(
                group_id=new_group.id,
                artifact_id=source_ga.artifact_id,
                position=source_ga.position,
            )
            session.add(new_group_artifact)

        session.commit()
        session.refresh(new_group)

        logger.info(
            f"Copied group '{source_group.name}' ({group_id}) to collection "
            f"'{request.target_collection_id}' as '{new_group_name}' ({new_group.id}) "
            f"with {len(source_artifacts)} artifacts"
        )

        return _build_group_response(session, new_group, artifact_count=len(source_artifacts))

    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error copying group: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name must be unique within collection",
        ) from e
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to copy group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy group",
        ) from e
    finally:
        session.close()


# =============================================================================
# Group Reordering
# =============================================================================


@router.put(
    "/reorder",
    response_model=GroupListResponse,
    summary="Bulk reorder groups",
    description="""
    Update positions of multiple groups in a single transaction.

    This is more efficient than updating groups individually and ensures
    atomic updates across all groups.
    """,
)
async def reorder_groups(request: GroupReorderRequest) -> GroupListResponse:
    """Bulk reorder groups by updating their positions.

    Args:
        request: List of groups with new positions

    Returns:
        Updated groups ordered by position

    Raises:
        HTTPException 404: If any group not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Load all groups
        group_ids = [g.id for g in request.groups]
        groups = session.query(Group).filter(Group.id.in_(group_ids)).all()

        # Verify all groups exist
        found_ids = {g.id for g in groups}
        missing_ids = set(group_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Groups not found: {', '.join(missing_ids)}",
            )

        # Build position map
        position_map = {g.id: g.position for g in request.groups}

        # Update positions
        for group in groups:
            new_position = position_map.get(group.id)
            if new_position is not None:
                group.position = new_position

        session.commit()

        logger.info(f"Reordered {len(groups)} groups")

        # Refresh and build response
        group_responses = []
        for group in sorted(groups, key=lambda g: g.position):
            session.refresh(group)
            artifact_count = (
                session.query(GroupArtifact).filter_by(group_id=group.id).count()
            )
            group_responses.append(
                _build_group_response(
                    session,
                    group,
                    artifact_count=artifact_count,
                )
            )

        return GroupListResponse(
            groups=group_responses,
            total=len(group_responses),
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to reorder groups: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder groups",
        ) from e
    finally:
        session.close()


# =============================================================================
# Group-Artifact Management
# =============================================================================


@router.post(
    "/{group_id}/artifacts",
    status_code=status.HTTP_201_CREATED,
    summary="Add artifacts to group",
    description="""
    Add one or more artifacts to a group.

    Artifacts can be added at a specific position (shifting existing artifacts)
    or appended to the end (default). Duplicate artifacts are silently ignored.
    """,
)
async def add_artifacts_to_group(
    group_id: str,
    request: AddGroupArtifactsRequest,
) -> GroupWithArtifactsResponse:
    """Add artifacts to a group.

    Args:
        group_id: Group ID
        request: List of artifact IDs and optional position

    Returns:
        Updated group with artifacts

    Raises:
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Verify group exists
        group = session.query(Group).filter_by(id=group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{group_id}' not found",
            )

        # Get existing artifacts
        existing_artifact_ids = {
            ga.artifact_id
            for ga in session.query(GroupArtifact).filter_by(group_id=group_id).all()
        }

        # Filter out duplicates
        new_artifact_ids = [
            aid for aid in request.artifact_ids if aid not in existing_artifact_ids
        ]

        if not new_artifact_ids:
            logger.info(f"No new artifacts to add to group {group_id} (all duplicates)")
        else:
            # Determine position
            if request.position is not None:
                # Shift existing artifacts at and after position
                session.query(GroupArtifact).filter(
                    GroupArtifact.group_id == group_id,
                    GroupArtifact.position >= request.position,
                ).update(
                    {
                        GroupArtifact.position: GroupArtifact.position
                        + len(new_artifact_ids)
                    }
                )
                start_position = request.position
            else:
                # Append to end
                max_position = (
                    session.query(GroupArtifact.position)
                    .filter_by(group_id=group_id)
                    .order_by(GroupArtifact.position.desc())
                    .first()
                )
                start_position = (max_position[0] + 1) if max_position else 0

            # Add new artifacts
            for i, artifact_id in enumerate(new_artifact_ids):
                group_artifact = GroupArtifact(
                    group_id=group_id,
                    artifact_id=artifact_id,
                    position=start_position + i,
                )
                session.add(group_artifact)

            session.commit()
            logger.info(f"Added {len(new_artifact_ids)} artifacts to group {group_id}")

        # Get updated artifacts
        group_artifacts = (
            session.query(GroupArtifact)
            .filter_by(group_id=group_id)
            .order_by(GroupArtifact.position)
            .all()
        )

        artifacts = [
            GroupArtifactResponse(
                artifact_id=ga.artifact_id,
                position=ga.position,
                added_at=ga.added_at,
            )
            for ga in group_artifacts
        ]

        return GroupWithArtifactsResponse(
            id=group.id,
            collection_id=group.collection_id,
            name=group.name,
            description=group.description,
            tags=_parse_group_tags(group.tags_json),
            color=group.color or "slate",
            icon=group.icon or "layers",
            position=group.position,
            created_at=group.created_at,
            updated_at=group.updated_at,
            artifact_count=len(artifacts),
            artifacts=artifacts,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to add artifacts to group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add artifacts to group",
        ) from e
    finally:
        session.close()


@router.delete(
    "/{group_id}/artifacts/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove artifact from group",
    description="""
    Remove an artifact from a group.

    Remaining artifacts are automatically reordered to fill the gap.
    The artifact itself is not deleted from the collection.
    """,
)
async def remove_artifact_from_group(group_id: str, artifact_id: str) -> None:
    """Remove an artifact from a group.

    Args:
        group_id: Group ID
        artifact_id: Artifact ID

    Raises:
        HTTPException 404: If group or artifact association not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Find association
        group_artifact = (
            session.query(GroupArtifact)
            .filter_by(group_id=group_id, artifact_id=artifact_id)
            .first()
        )

        if not group_artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in group '{group_id}'",
            )

        removed_position = group_artifact.position

        # Delete association
        session.delete(group_artifact)

        # Reorder remaining artifacts (shift down)
        session.query(GroupArtifact).filter(
            GroupArtifact.group_id == group_id,
            GroupArtifact.position > removed_position,
        ).update({GroupArtifact.position: GroupArtifact.position - 1})

        session.commit()

        logger.info(f"Removed artifact {artifact_id} from group {group_id}")

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to remove artifact {artifact_id} from group {group_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove artifact from group",
        ) from e
    finally:
        session.close()


@router.put(
    "/{group_id}/artifacts/{artifact_id}",
    response_model=GroupArtifactResponse,
    summary="Update artifact position",
    description="""
    Update an artifact's position within a group.

    Other artifacts are automatically shifted to accommodate the new position.
    """,
)
async def update_artifact_position(
    group_id: str,
    artifact_id: str,
    position_update: ArtifactPositionUpdate,
) -> GroupArtifactResponse:
    """Update an artifact's position in a group.

    Args:
        group_id: Group ID
        artifact_id: Artifact ID
        position_update: New position

    Returns:
        Updated artifact association

    Raises:
        HTTPException 404: If group or artifact association not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Find association
        group_artifact = (
            session.query(GroupArtifact)
            .filter_by(group_id=group_id, artifact_id=artifact_id)
            .first()
        )

        if not group_artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact '{artifact_id}' not found in group '{group_id}'",
            )

        old_position = group_artifact.position
        new_position = position_update.position

        if old_position != new_position:
            # Shift artifacts between old and new position
            if new_position > old_position:
                # Moving down: shift up artifacts in range (old+1, new]
                session.query(GroupArtifact).filter(
                    GroupArtifact.group_id == group_id,
                    GroupArtifact.position > old_position,
                    GroupArtifact.position <= new_position,
                ).update({GroupArtifact.position: GroupArtifact.position - 1})
            else:
                # Moving up: shift down artifacts in range [new, old-1]
                session.query(GroupArtifact).filter(
                    GroupArtifact.group_id == group_id,
                    GroupArtifact.position >= new_position,
                    GroupArtifact.position < old_position,
                ).update({GroupArtifact.position: GroupArtifact.position + 1})

            # Update artifact position
            group_artifact.position = new_position

            session.commit()
            session.refresh(group_artifact)

            logger.info(
                f"Updated artifact {artifact_id} position in group {group_id}: {old_position} -> {new_position}"
            )

        return GroupArtifactResponse(
            artifact_id=group_artifact.artifact_id,
            position=group_artifact.position,
            added_at=group_artifact.added_at,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to update artifact {artifact_id} position in group {group_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update artifact position",
        ) from e
    finally:
        session.close()


@router.post(
    "/{group_id}/reorder-artifacts",
    response_model=GroupWithArtifactsResponse,
    summary="Bulk reorder artifacts",
    description="""
    Update positions of multiple artifacts in a single transaction.

    This is more efficient than updating artifacts individually and ensures
    atomic updates across all artifacts.
    """,
)
async def reorder_artifacts_in_group(
    group_id: str,
    request: ReorderArtifactsRequest,
) -> GroupWithArtifactsResponse:
    """Bulk reorder artifacts in a group.

    Args:
        group_id: Group ID
        request: List of artifacts with new positions

    Returns:
        Updated group with artifacts

    Raises:
        HTTPException 404: If group or any artifact not found
        HTTPException 500: If database operation fails
    """
    session = get_session()
    try:
        # Verify group exists
        group = session.query(Group).filter_by(id=group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group '{group_id}' not found",
            )

        # Load all group artifacts
        artifact_ids = [a.artifact_id for a in request.artifacts]
        group_artifacts = (
            session.query(GroupArtifact)
            .filter(
                GroupArtifact.group_id == group_id,
                GroupArtifact.artifact_id.in_(artifact_ids),
            )
            .all()
        )

        # Verify all artifacts exist in group
        found_ids = {ga.artifact_id for ga in group_artifacts}
        missing_ids = set(artifact_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifacts not found in group: {', '.join(missing_ids)}",
            )

        # Build position map
        position_map = {a.artifact_id: a.position for a in request.artifacts}

        # Update positions
        for ga in group_artifacts:
            new_position = position_map.get(ga.artifact_id)
            if new_position is not None:
                ga.position = new_position

        session.commit()

        logger.info(f"Reordered {len(group_artifacts)} artifacts in group {group_id}")

        # Get all artifacts ordered by position
        all_group_artifacts = (
            session.query(GroupArtifact)
            .filter_by(group_id=group_id)
            .order_by(GroupArtifact.position)
            .all()
        )

        artifacts = [
            GroupArtifactResponse(
                artifact_id=ga.artifact_id,
                position=ga.position,
                added_at=ga.added_at,
            )
            for ga in all_group_artifacts
        ]

        return GroupWithArtifactsResponse(
            id=group.id,
            collection_id=group.collection_id,
            name=group.name,
            description=group.description,
            tags=_parse_group_tags(group.tags_json),
            color=group.color or "slate",
            icon=group.icon or "layers",
            position=group.position,
            created_at=group.created_at,
            updated_at=group.updated_at,
            artifact_count=len(artifacts),
            artifacts=artifacts,
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(
            f"Failed to reorder artifacts in group {group_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder artifacts",
        ) from e
    finally:
        session.close()
