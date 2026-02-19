"""Composite artifact CRUD API endpoints.

Provides REST API for creating, reading, updating, and deleting composite
artifacts, as well as managing their child-artifact memberships.

API Endpoints:
    GET  /composites                           - List composites in a collection
    POST /composites                           - Create a new composite (201)
    GET  /composites/{composite_id}            - Get composite with memberships
    PUT  /composites/{composite_id}            - Update name/description (200)
    DELETE /composites/{composite_id}          - Delete composite (204)
    POST /composites/{composite_id}/members    - Add member artifact (201)
    DELETE /composites/{composite_id}/members/{member_uuid} - Remove member (204)
    PATCH /composites/{composite_id}/members   - Reorder members (200)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.schemas.composites import (
    CompositeCreateRequest,
    CompositeListResponse,
    CompositeResponse,
    CompositeUpdateRequest,
    MembershipCreateRequest,
    MembershipReorderRequest,
    MembershipResponse,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError
from skillmeat.core.services.composite_service import (
    ArtifactNotFoundError,
    CompositeService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/composites",
    tags=["composites"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _membership_dict_to_response(m: Dict[str, Any]) -> MembershipResponse:
    """Convert a ``MembershipRecord`` dict to a ``MembershipResponse`` schema.

    Args:
        m: Plain dict from the composite repository / service layer.

    Returns:
        Validated ``MembershipResponse`` instance.
    """
    created_at = m.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    return MembershipResponse(
        collection_id=m["collection_id"],
        composite_id=m["composite_id"],
        child_artifact_uuid=m["child_artifact_uuid"],
        relationship_type=m.get("relationship_type", "contains"),
        pinned_version_hash=m.get("pinned_version_hash"),
        position=m.get("position"),
        created_at=created_at,
        child_artifact=m.get("child_artifact"),
    )


def _composite_dict_to_response(c: Dict[str, Any]) -> CompositeResponse:
    """Convert a ``CompositeRecord`` dict to a ``CompositeResponse`` schema.

    Args:
        c: Plain dict from the composite repository / service layer.

    Returns:
        Validated ``CompositeResponse`` instance.
    """
    created_at = c.get("created_at")
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)

    updated_at = c.get("updated_at")
    if isinstance(updated_at, str):
        updated_at = datetime.fromisoformat(updated_at)

    memberships_raw: List[Dict[str, Any]] = c.get("memberships", [])
    memberships = [_membership_dict_to_response(m) for m in memberships_raw]

    return CompositeResponse(
        id=c["id"],
        collection_id=c["collection_id"],
        composite_type=c.get("composite_type", "plugin"),
        display_name=c.get("display_name"),
        description=c.get("description"),
        created_at=created_at,
        updated_at=updated_at,
        memberships=memberships,
        member_count=len(memberships),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=CompositeListResponse,
    summary="List composite artifacts",
    description="Return all composite artifacts in a collection.",
    responses={
        200: {"description": "Composite list retrieved successfully"},
        500: {"description": "Internal server error"},
    },
)
async def list_composites(
    collection_id: str = Query(
        ...,
        description="ID of the collection to list composites for.",
        examples=["default"],
    ),
) -> CompositeListResponse:
    """List all composite artifacts in the given collection.

    Args:
        collection_id: Owning collection identifier.

    Returns:
        ``CompositeListResponse`` with all composites and their member counts.

    Raises:
        HTTPException 500: On unexpected service error.
    """
    logger.info("list_composites: collection_id=%s", collection_id)
    try:
        svc = CompositeService()
        records = svc.list_composites(collection_id=collection_id)
        items = [_composite_dict_to_response(r) for r in records]
        return CompositeListResponse(items=items, total=len(items))
    except Exception as exc:
        logger.exception("list_composites failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list composite artifacts.",
        )


@router.post(
    "",
    response_model=CompositeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create composite artifact",
    description=(
        "Create a new composite artifact, optionally with initial child members."
    ),
    responses={
        201: {"description": "Composite created successfully"},
        400: {"description": "Invalid request or child artifact not found"},
        409: {"description": "Composite with that ID already exists"},
        500: {"description": "Internal server error"},
    },
)
async def create_composite(
    request: CompositeCreateRequest,
) -> CompositeResponse:
    """Create a new composite artifact.

    Resolves each ``initial_members`` entry (``type:name``) to a stable UUID
    before inserting membership edges.

    Args:
        request: ``CompositeCreateRequest`` body.

    Returns:
        Newly created ``CompositeResponse`` (HTTP 201).

    Raises:
        HTTPException 400: When a child artifact cannot be resolved.
        HTTPException 409: When the composite_id already exists.
        HTTPException 500: On unexpected service error.
    """
    logger.info(
        "create_composite: id=%s collection=%s",
        request.composite_id,
        request.collection_id,
    )
    try:
        svc = CompositeService()
        record = svc.create_composite(
            collection_id=request.collection_id,
            composite_id=request.composite_id,
            composite_type=request.composite_type,
            display_name=request.display_name,
            description=request.description,
            initial_members=request.initial_members or [],
            pinned_version_hash=request.pinned_version_hash,
        )
        return _composite_dict_to_response(record)
    except ArtifactNotFoundError as exc:
        logger.warning("create_composite: child not found — %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except ConstraintError as exc:
        logger.warning("create_composite: constraint violation — %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A composite with id '{request.composite_id}' already exists.",
        )
    except Exception as exc:
        logger.exception("create_composite failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create composite artifact.",
        )


@router.get(
    "/{composite_id:path}",
    response_model=CompositeResponse,
    summary="Get composite artifact",
    description="Retrieve a single composite artifact with its member list.",
    responses={
        200: {"description": "Composite retrieved successfully"},
        404: {"description": "Composite not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_composite(
    composite_id: str,
) -> CompositeResponse:
    """Retrieve a single composite artifact by its ``type:name`` id.

    Args:
        composite_id: ``type:name`` primary key (URL-encoded if it contains
            special characters).

    Returns:
        ``CompositeResponse`` with full membership list.

    Raises:
        HTTPException 404: When no composite with that id exists.
        HTTPException 500: On unexpected service error.
    """
    logger.info("get_composite: id=%s", composite_id)
    try:
        svc = CompositeService()
        record = svc.get_composite(composite_id=composite_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Composite '{composite_id}' not found.",
            )
        return _composite_dict_to_response(record)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("get_composite failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve composite artifact.",
        )


@router.put(
    "/{composite_id:path}",
    response_model=CompositeResponse,
    summary="Update composite artifact",
    description="Update mutable fields (display_name, description, composite_type).",
    responses={
        200: {"description": "Composite updated successfully"},
        404: {"description": "Composite not found"},
        500: {"description": "Internal server error"},
    },
)
async def update_composite(
    composite_id: str,
    request: CompositeUpdateRequest,
) -> CompositeResponse:
    """Update a composite artifact's mutable fields.

    Only fields provided in the request body (non-null) are updated.

    Args:
        composite_id: ``type:name`` primary key from URL path.
        request: ``CompositeUpdateRequest`` body.

    Returns:
        Updated ``CompositeResponse``.

    Raises:
        HTTPException 404: When no composite with that id exists.
        HTTPException 500: On unexpected service error.
    """
    logger.info("update_composite: id=%s", composite_id)
    try:
        svc = CompositeService()
        record = svc.update_composite(
            composite_id=composite_id,
            display_name=request.display_name,
            description=request.description,
            composite_type=request.composite_type,
        )
        return _composite_dict_to_response(record)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Composite '{composite_id}' not found.",
        )
    except Exception as exc:
        logger.exception("update_composite failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update composite artifact.",
        )


@router.delete(
    "/{composite_id:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete composite artifact",
    description=(
        "Delete a composite artifact and all its membership edges.  "
        "Set cascade_delete_children=true to also delete the child Artifact rows."
    ),
    responses={
        204: {"description": "Composite deleted"},
        404: {"description": "Composite not found"},
        500: {"description": "Internal server error"},
    },
)
async def delete_composite(
    composite_id: str,
    cascade_delete_children: bool = Query(
        default=False,
        description=(
            "When true, also delete the child Artifact rows referenced by "
            "this composite.  Defaults to false (only membership edges are removed)."
        ),
    ),
) -> None:
    """Delete a composite artifact.

    Membership rows are always removed via ON DELETE CASCADE.  Setting
    ``cascade_delete_children=true`` additionally hard-deletes the child
    Artifact rows.

    Args:
        composite_id: ``type:name`` primary key from URL path.
        cascade_delete_children: Whether to also delete child artifacts.

    Returns:
        HTTP 204 No Content.

    Raises:
        HTTPException 404: When no composite with that id exists.
        HTTPException 500: On unexpected service error.
    """
    logger.info(
        "delete_composite: id=%s cascade=%s", composite_id, cascade_delete_children
    )
    try:
        svc = CompositeService()
        deleted = svc.delete_composite(
            composite_id=composite_id,
            cascade_delete_children=cascade_delete_children,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Composite '{composite_id}' not found.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("delete_composite failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete composite artifact.",
        )


@router.post(
    "/{composite_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add member to composite",
    description="Add a child artifact (by type:name) as a member of the composite.",
    responses={
        201: {"description": "Member added successfully"},
        400: {"description": "Child artifact not found in cache"},
        404: {"description": "Composite not found"},
        409: {"description": "Membership already exists"},
        500: {"description": "Internal server error"},
    },
)
async def add_composite_member(
    composite_id: str,
    request: MembershipCreateRequest,
    collection_id: str = Query(
        ...,
        description="Owning collection ID.  Must match the composite's collection.",
        examples=["default"],
    ),
) -> MembershipResponse:
    """Add a child artifact to a composite.

    Resolves ``artifact_id`` (``type:name``) to a stable UUID.  The artifact
    must already be present in the collection cache.

    Args:
        composite_id: ``type:name`` primary key from URL path.
        request: ``MembershipCreateRequest`` body.
        collection_id: Owning collection identifier (required query param).

    Returns:
        Newly created ``MembershipResponse`` (HTTP 201).

    Raises:
        HTTPException 400: When ``artifact_id`` cannot be resolved.
        HTTPException 409: When the membership already exists.
        HTTPException 500: On unexpected service error.
    """
    logger.info(
        "add_composite_member: composite=%s child=%s",
        composite_id,
        request.artifact_id,
    )
    try:
        svc = CompositeService()

        # Verify composite exists before adding
        if svc.get_composite(composite_id=composite_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Composite '{composite_id}' not found.",
            )

        record = svc.add_composite_member(
            collection_id=collection_id,
            composite_id=composite_id,
            child_artifact_id=request.artifact_id,
            pinned_version_hash=request.pinned_version_hash,
            relationship_type=request.relationship_type,
        )

        # If a position was specified, apply it
        if request.position is not None:
            svc.reorder_composite_members(
                composite_id=composite_id,
                reorder=[
                    {
                        "artifact_id": request.artifact_id,
                        "position": request.position,
                    }
                ],
            )
            record["position"] = request.position

        return _membership_dict_to_response(record)
    except HTTPException:
        raise
    except ArtifactNotFoundError as exc:
        logger.warning("add_composite_member: child not found — %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except ConstraintError as exc:
        logger.warning("add_composite_member: duplicate membership — %s", exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Artifact '{request.artifact_id}' is already a member of "
                f"composite '{composite_id}'."
            ),
        )
    except Exception as exc:
        logger.exception("add_composite_member failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member to composite.",
        )


@router.delete(
    "/{composite_id}/members/{member_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from composite",
    description=(
        "Remove a child artifact membership by child artifact UUID.  "
        "The child Artifact row is NOT deleted — only the membership edge is removed."
    ),
    responses={
        204: {"description": "Member removed successfully"},
        404: {"description": "Composite or membership not found"},
        500: {"description": "Internal server error"},
    },
)
async def remove_composite_member(
    composite_id: str,
    member_uuid: str,
) -> None:
    """Remove a child artifact from a composite by UUID.

    Only the membership edge is removed; the child Artifact row is preserved.
    Use ``DELETE /composites/{id}?cascade_delete_children=true`` to remove
    the composite AND its children.

    Args:
        composite_id: ``type:name`` primary key from URL path.
        member_uuid: Stable UUID (ADR-007) of the child artifact to remove.

    Returns:
        HTTP 204 No Content.

    Raises:
        HTTPException 404: When the composite or membership is not found.
        HTTPException 500: On unexpected service error.
    """
    logger.info(
        "remove_composite_member: composite=%s member_uuid=%s",
        composite_id,
        member_uuid,
    )
    try:
        from skillmeat.cache.composite_repository import CompositeMembershipRepository

        repo = CompositeMembershipRepository()
        deleted = repo.delete_membership(
            composite_id=composite_id,
            child_artifact_uuid=member_uuid,
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Membership for artifact UUID '{member_uuid}' in composite "
                    f"'{composite_id}' not found."
                ),
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("remove_composite_member failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member from composite.",
        )


@router.patch(
    "/{composite_id}/members",
    response_model=List[MembershipResponse],
    summary="Reorder composite members",
    description=(
        "Bulk-update the position of child artifacts within a composite.  "
        "Positions are 0-based integers.  Artifacts not listed keep their "
        "current positions."
    ),
    responses={
        200: {"description": "Members reordered successfully"},
        400: {"description": "Child artifact not found in cache"},
        404: {"description": "Composite not found"},
        500: {"description": "Internal server error"},
    },
)
async def reorder_composite_members(
    composite_id: str,
    request: MembershipReorderRequest,
) -> List[MembershipResponse]:
    """Reorder child members within a composite.

    Each entry in the request body specifies a child ``artifact_id``
    (``type:name``) and its new ``position`` (0-based int).  The service
    resolves each ``artifact_id`` to a UUID before updating.

    Args:
        composite_id: ``type:name`` primary key from URL path.
        request: ``MembershipReorderRequest`` body.

    Returns:
        Full updated membership list ordered by new positions (nulls last).

    Raises:
        HTTPException 400: When any ``artifact_id`` cannot be resolved.
        HTTPException 404: When the composite does not exist.
        HTTPException 500: On unexpected service error.
    """
    logger.info(
        "reorder_composite_members: composite=%s count=%d",
        composite_id,
        len(request.members),
    )
    try:
        svc = CompositeService()

        if svc.get_composite(composite_id=composite_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Composite '{composite_id}' not found.",
            )

        reorder = [
            {"artifact_id": m.artifact_id, "position": m.position}
            for m in request.members
        ]
        updated = svc.reorder_composite_members(
            composite_id=composite_id,
            reorder=reorder,
        )
        return [_membership_dict_to_response(m) for m in updated]
    except HTTPException:
        raise
    except ArtifactNotFoundError as exc:
        logger.warning("reorder_composite_members: child not found — %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("reorder_composite_members failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder composite members.",
        )
