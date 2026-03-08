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

import logging
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from skillmeat.api.dependencies import (
    ArtifactRepoDep,
    GroupRepoDep,
    get_auth_context,
    require_auth,
)
from skillmeat.api.schemas.auth import AuthContext

if TYPE_CHECKING:
    from skillmeat.core.interfaces.repositories import IArtifactRepository
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
from skillmeat.core.interfaces.dtos import GroupDTO

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/groups",
    tags=["groups"],
)


# =============================================================================
# Internal helpers
# =============================================================================


def _build_artifact_responses(
    group_artifacts: list,
    artifact_repo: "IArtifactRepository",
) -> list["GroupArtifactResponse"]:
    """Build GroupArtifactResponse objects from GroupArtifactDTO records.

    Resolves artifact UUIDs to their ``type:name`` IDs via a single batch
    lookup against the artifact repository.

    Args:
        group_artifacts: List of GroupArtifactDTO objects.
        artifact_repo: IArtifactRepository used for UUID → ID resolution.

    Returns:
        List of GroupArtifactResponse objects with ``artifact_id`` populated
        where resolvable.
    """
    uuids = [ga.artifact_uuid for ga in group_artifacts]
    uuid_to_id: dict[str, str] = artifact_repo.get_ids_by_uuids(uuids) if uuids else {}
    return [
        GroupArtifactResponse(
            artifact_uuid=ga.artifact_uuid,
            artifact_id=uuid_to_id.get(ga.artifact_uuid),
            position=ga.position,
            added_at=ga.added_at,
        )
        for ga in group_artifacts
    ]


def _dto_to_group_response(dto: GroupDTO) -> GroupResponse:
    """Convert a GroupDTO to a GroupResponse API schema.

    Args:
        dto: GroupDTO from the repository layer.

    Returns:
        GroupResponse suitable for API serialisation.
    """
    return GroupResponse(
        id=dto.id,
        collection_id=dto.collection_id,
        name=dto.name,
        description=dto.description,
        tags=list(dto.tags),
        color=dto.color,
        icon=dto.icon,
        position=dto.position,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        artifact_count=dto.artifact_count,
    )


def _build_group_with_artifacts_response(
    dto: GroupDTO,
    artifacts: list[GroupArtifactResponse],
) -> GroupWithArtifactsResponse:
    """Build a GroupWithArtifactsResponse from a DTO and resolved artifact list.

    Args:
        dto: GroupDTO from the repository.
        artifacts: Resolved list of GroupArtifactResponse objects.

    Returns:
        GroupWithArtifactsResponse for API serialisation.
    """
    return GroupWithArtifactsResponse(
        id=dto.id,
        collection_id=dto.collection_id,
        name=dto.name,
        description=dto.description,
        tags=list(dto.tags),
        color=dto.color,
        icon=dto.icon,
        position=dto.position,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        artifact_count=len(artifacts),
        artifacts=artifacts,
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
async def create_group(
    request: GroupCreateRequest,
    group_repo: GroupRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupResponse:
    """Create a new group in a collection.

    Args:
        request: Group creation request with collection_id, name, description, position
        group_repo: Injected IGroupRepository

    Returns:
        Created group with metadata

    Raises:
        HTTPException 400: If group name already exists in collection
        HTTPException 404: If collection not found
        HTTPException 500: If database operation fails
    """
    try:
        dto = group_repo.create(
            name=request.name,
            collection_id=request.collection_id,
            description=request.description,
            position=request.position,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(f"Failed to create group: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create group",
        ) from e

    logger.info(
        f"Created group: {dto.id} ('{dto.name}') in collection {dto.collection_id}"
    )

    # Apply tags/color/icon via update if provided (create only accepts name/description/position)
    needs_update = (
        (request.tags is not None and request.tags != [])
        or request.color is not None
        or request.icon is not None
    )
    if needs_update:
        updates: dict = {}
        if request.tags is not None:
            updates["tags"] = request.tags
        if request.color is not None:
            updates["color"] = request.color
        if request.icon is not None:
            updates["icon"] = request.icon
        try:
            dto = group_repo.update(dto.id, updates)
        except Exception as e:
            logger.warning(f"Failed to apply tags/color/icon on new group {dto.id}: {e}")

    return _dto_to_group_response(dto)


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
    group_repo: GroupRepoDep,
    collection_id: str = Query(..., description="Collection ID to list groups from"),
    search: Optional[str] = Query(
        None, description="Filter groups by name (case-insensitive)"
    ),
    artifact_id: Optional[str] = Query(
        None, description="Filter to groups containing this artifact"
    ),
    auth_context: AuthContext = Depends(get_auth_context),
) -> GroupListResponse:
    """List all groups in a collection.

    Args:
        group_repo: Injected IGroupRepository
        collection_id: Collection ID (required)
        search: Optional name filter
        artifact_id: Optional artifact ID filter - returns only groups containing this artifact

    Returns:
        List of groups ordered by position

    Raises:
        HTTPException 404: If collection not found
        HTTPException 500: If database operation fails
    """
    filters: dict = {}
    if search:
        filters["search"] = search
    if artifact_id:
        filters["artifact_id"] = artifact_id

    try:
        dtos = group_repo.list(collection_id, filters=filters or None)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(f"Failed to list groups: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list groups",
        ) from e

    group_responses = [_dto_to_group_response(dto) for dto in dtos]

    logger.info(
        f"Listed {len(group_responses)} groups from collection {collection_id}"
        + (f" (search: {search})" if search else "")
        + (f" (artifact_id: {artifact_id})" if artifact_id else "")
    )

    return GroupListResponse(
        groups=group_responses,
        total=len(group_responses),
    )


@router.get(
    "/{group_id}",
    response_model=GroupWithArtifactsResponse,
    summary="Get group details",
    description="""
    Get detailed information about a group including its artifacts.

    Artifacts are returned ordered by their position within the group.
    """,
)
async def get_group(
    group_id: str,
    group_repo: GroupRepoDep,
    artifact_repo: ArtifactRepoDep,
    auth_context: AuthContext = Depends(get_auth_context),
) -> GroupWithArtifactsResponse:
    """Get a single group with its artifacts.

    Args:
        group_id: Group ID
        group_repo: Injected IGroupRepository
        artifact_repo: Injected IArtifactRepository for UUID → ID resolution

    Returns:
        Group with artifacts list

    Raises:
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    try:
        dto = group_repo.get_with_artifacts(group_id)
    except RuntimeError as e:
        logger.error(f"Failed to get group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get group",
        ) from e

    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{group_id}' not found",
        )

    # Fetch ordered artifact memberships via repository
    group_artifact_dtos = group_repo.list_group_artifacts(group_id)
    artifacts = _build_artifact_responses(group_artifact_dtos, artifact_repo)

    logger.info(f"Retrieved group {group_id} with {len(artifacts)} artifacts")

    return _build_group_with_artifacts_response(dto, artifacts)


@router.put(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Update group",
    description="""
    Update group metadata (name, description, position).

    All fields are optional. Only provided fields will be updated.
    """,
)
async def update_group(
    group_id: str,
    request: GroupUpdateRequest,
    group_repo: GroupRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupResponse:
    """Update a group's metadata.

    Args:
        group_id: Group ID
        request: Update request with optional name, description, position
        group_repo: Injected IGroupRepository

    Returns:
        Updated group

    Raises:
        HTTPException 400: If new name conflicts with existing group
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    updates: dict = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.tags is not None:
        updates["tags"] = request.tags
    if request.color is not None:
        updates["color"] = request.color
    if request.icon is not None:
        updates["icon"] = request.icon
    if request.position is not None:
        updates["position"] = request.position

    try:
        dto = group_repo.update(group_id, updates)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(f"Failed to update group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update group",
        ) from e

    logger.info(f"Updated group {group_id}")
    return _dto_to_group_response(dto)


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
async def delete_group(
    group_id: str,
    group_repo: GroupRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> None:
    """Delete a group.

    Args:
        group_id: Group ID
        group_repo: Injected IGroupRepository

    Raises:
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    try:
        group_repo.delete(group_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(f"Failed to delete group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete group",
        ) from e

    logger.info(f"Deleted group {group_id}")


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
    group_repo: GroupRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupResponse:
    """Copy a group to another collection.

    Args:
        group_id: Source group ID to copy
        request: Copy request with target_collection_id
        group_repo: Injected IGroupRepository

    Returns:
        The newly created group in the target collection

    Raises:
        HTTPException 404: If source group or target collection not found
        HTTPException 400: If group name already exists in target collection
        HTTPException 500: If database operation fails
    """
    try:
        dto = group_repo.copy_to_collection(group_id, request.target_collection_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(f"Failed to copy group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy group",
        ) from e

    logger.info(
        f"Copied group ({group_id}) to collection "
        f"'{request.target_collection_id}' as group '{dto.id}'"
    )
    return _dto_to_group_response(dto)


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
async def reorder_groups(
    request: GroupReorderRequest,
    group_repo: GroupRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupListResponse:
    """Bulk reorder groups by updating their positions.

    Args:
        request: List of groups with new positions
        group_repo: Injected IGroupRepository

    Returns:
        Updated groups ordered by position

    Raises:
        HTTPException 404: If any group not found
        HTTPException 500: If database operation fails
    """
    if not request.groups:
        return GroupListResponse(groups=[], total=0)

    # Derive the collection_id from the first group's position update.
    # The original endpoint stored the collection_id from the loaded ORM object;
    # here we need to fetch the group first to get it, then call reorder_groups.
    # We fetch the first group to determine the collection, then build ordered_ids
    # from the request's position field (sorted ascending).
    first_group_id = request.groups[0].id
    try:
        first_dto = group_repo.get_with_artifacts(first_group_id)
    except RuntimeError as e:
        logger.error(f"Failed to reorder groups: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder groups",
        ) from e

    if not first_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{first_group_id}' not found",
        )

    collection_id = first_dto.collection_id

    # Build ordered_ids from the request position map (sort by position ascending)
    sorted_groups = sorted(request.groups, key=lambda g: g.position)
    ordered_ids = [g.id for g in sorted_groups]

    try:
        group_repo.reorder_groups(collection_id, ordered_ids)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(f"Failed to reorder groups: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder groups",
        ) from e

    logger.info(f"Reordered {len(ordered_ids)} groups")

    # Fetch updated group list for response
    try:
        dtos = group_repo.list(collection_id)
    except RuntimeError as e:
        logger.error(f"Failed to fetch groups after reorder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder groups",
        ) from e

    group_responses = [_dto_to_group_response(dto) for dto in dtos]

    return GroupListResponse(
        groups=group_responses,
        total=len(group_responses),
    )


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
    group_repo: GroupRepoDep,
    artifact_repo: ArtifactRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupWithArtifactsResponse:
    """Add artifacts to a group.

    Args:
        group_id: Group ID
        request: List of artifact IDs and optional position
        group_repo: Injected IGroupRepository
        artifact_repo: Injected IArtifactRepository for UUID resolution

    Returns:
        Updated group with artifacts

    Raises:
        HTTPException 404: If group not found
        HTTPException 500: If database operation fails
    """
    # Verify group exists
    try:
        dto = group_repo.get_with_artifacts(group_id)
    except RuntimeError as e:
        logger.error(f"Failed to add artifacts to group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add artifacts to group",
        ) from e

    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{group_id}' not found",
        )

    # Resolve artifact_ids (type:name strings) → UUIDs via artifact repo
    type_name_pairs = []
    for aid in request.artifact_ids:
        parts = aid.split(":", 1)
        if len(parts) == 2:
            type_name_pairs.append((parts[0], parts[1]))

    uuid_map: dict[str, str] = {}  # artifact_id → uuid
    if type_name_pairs:
        resolved = artifact_repo.batch_resolve_uuids(type_name_pairs)
        for (art_type, art_name), art_uuid in resolved.items():
            uuid_map[f"{art_type}:{art_name}"] = art_uuid

    # Determine UUIDs for artifacts not already in the group
    # The repo's add_artifacts handles deduplication silently
    new_uuids = [uuid_map[aid] for aid in request.artifact_ids if aid in uuid_map]

    if new_uuids:
        if request.position is not None:
            # Position-aware insert: shift existing, then insert at target position
            try:
                group_repo.add_artifacts_at_position(group_id, new_uuids, request.position)
                logger.info(
                    f"Added {len(new_uuids)} artifacts at position {request.position} "
                    f"in group {group_id}"
                )
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
            except RuntimeError as e:
                logger.error(
                    f"Failed to add artifacts at position in group {group_id}: {e}",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to add artifacts to group",
                ) from e
        else:
            # Append mode — repo handles deduplication and positioning
            try:
                group_repo.add_artifacts(group_id, new_uuids)
                logger.info(f"Added artifacts to group {group_id}")
            except KeyError as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=str(e),
                ) from e
            except RuntimeError as e:
                logger.error(
                    f"Failed to add artifacts to group {group_id}: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to add artifacts to group",
                ) from e
    else:
        logger.info(
            f"No new artifacts to add to group {group_id} (all duplicates or not found)"
        )

    # Refresh group DTO after mutation
    try:
        dto = group_repo.get_with_artifacts(group_id)
    except RuntimeError as e:
        logger.error(f"Failed to refresh group {group_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add artifacts to group",
        ) from e

    # Fetch current artifact memberships for response
    group_artifact_dtos = group_repo.list_group_artifacts(group_id)
    artifacts = _build_artifact_responses(group_artifact_dtos, artifact_repo)

    return _build_group_with_artifacts_response(dto, artifacts)


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
async def remove_artifact_from_group(
    group_id: str,
    artifact_id: str,
    group_repo: GroupRepoDep,
    artifact_repo: ArtifactRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> None:
    """Remove an artifact from a group.

    Args:
        group_id: Group ID
        artifact_id: Artifact ID (type:name format)
        group_repo: Injected IGroupRepository
        artifact_repo: Injected IArtifactRepository for UUID resolution

    Raises:
        HTTPException 404: If group or artifact association not found
        HTTPException 500: If database operation fails
    """
    # Resolve artifact_id (type:name string) → artifact_uuid
    parts = artifact_id.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )
    art_type, art_name = parts
    artifact_uuid = artifact_repo.resolve_uuid_by_type_name(art_type, art_name)
    if not artifact_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )

    try:
        group_repo.remove_artifact(group_id, artifact_uuid)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(
            f"Failed to remove artifact {artifact_id} from group {group_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove artifact from group",
        ) from e

    logger.info(f"Removed artifact {artifact_id} from group {group_id}")


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
    group_repo: GroupRepoDep,
    artifact_repo: ArtifactRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupArtifactResponse:
    """Update an artifact's position in a group.

    Args:
        group_id: Group ID
        artifact_id: Artifact ID (type:name format)
        position_update: New position
        group_repo: Injected IGroupRepository
        artifact_repo: Injected IArtifactRepository for UUID resolution

    Returns:
        Updated artifact association

    Raises:
        HTTPException 404: If group or artifact association not found
        HTTPException 500: If database operation fails
    """
    # Resolve artifact_id (type:name string) → artifact_uuid
    parts = artifact_id.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )
    art_type, art_name = parts
    artifact_uuid = artifact_repo.resolve_uuid_by_type_name(art_type, art_name)
    if not artifact_uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{artifact_id}' not found",
        )

    try:
        group_repo.update_artifact_position(
            group_id, artifact_uuid, position_update.position
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(
            f"Failed to update artifact {artifact_id} position in group {group_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update artifact position",
        ) from e

    logger.info(
        f"Updated artifact {artifact_id} position in group {group_id} "
        f"to {position_update.position}"
    )

    # Read back the updated membership record for the response via repository
    group_artifact_dtos = group_repo.list_group_artifacts(group_id)
    matching = next(
        (ga for ga in group_artifact_dtos if ga.artifact_uuid == artifact_uuid),
        None,
    )
    if matching:
        return GroupArtifactResponse(
            artifact_uuid=matching.artifact_uuid,
            artifact_id=artifact_id,
            position=matching.position,
            added_at=matching.added_at,
        )

    # Fallback: return the requested position directly
    return GroupArtifactResponse(
        artifact_uuid=artifact_uuid,
        artifact_id=artifact_id,
        position=position_update.position,
        added_at=None,
    )


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
    group_repo: GroupRepoDep,
    artifact_repo: ArtifactRepoDep,
    auth_context: AuthContext = Depends(require_auth(scopes=["collection:write"])),
) -> GroupWithArtifactsResponse:
    """Bulk reorder artifacts in a group.

    Args:
        group_id: Group ID
        request: List of artifacts with new positions (uses artifact_uuid values directly)
        group_repo: Injected IGroupRepository
        artifact_repo: Injected IArtifactRepository for UUID → ID resolution in response

    Returns:
        Updated group with artifacts

    Raises:
        HTTPException 404: If group or any artifact not found
        HTTPException 500: If database operation fails
    """
    # Verify group exists
    try:
        dto = group_repo.get_with_artifacts(group_id)
    except RuntimeError as e:
        logger.error(
            f"Failed to reorder artifacts in group {group_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder artifacts",
        ) from e

    if not dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group '{group_id}' not found",
        )

    # The request uses artifact_uuid values directly
    ordered_uuids = [a.artifact_uuid for a in request.artifacts]

    try:
        group_repo.reorder_artifacts(group_id, ordered_uuids)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        logger.error(
            f"Failed to reorder artifacts in group {group_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder artifacts",
        ) from e

    logger.info(f"Reordered {len(ordered_uuids)} artifacts in group {group_id}")

    # Fetch updated artifact memberships for response
    group_artifact_dtos = group_repo.list_group_artifacts(group_id)
    artifacts = _build_artifact_responses(group_artifact_dtos, artifact_repo)

    return _build_group_with_artifacts_response(dto, artifacts)
