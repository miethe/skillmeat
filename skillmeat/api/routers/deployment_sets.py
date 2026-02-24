"""Deployment Sets API router for managing named, ordered sets of artifacts.

This router provides endpoints for creating and managing deployment sets —
named, ordered collections of artifacts, groups, and/or nested sets that
can be batch-deployed to a project in a single operation.

API Endpoints:
    POST   /deployment-sets                              - Create new set (201)
    GET    /deployment-sets                              - List sets with pagination (200)
    GET    /deployment-sets/{set_id}                     - Get set with members (200)
    PUT    /deployment-sets/{set_id}                     - Update set metadata (200)
    DELETE /deployment-sets/{set_id}                     - Delete set, cascade members (204)
    POST   /deployment-sets/{set_id}/clone               - Clone set + members (201)
    GET    /deployment-sets/{set_id}/members             - List members (200)
    POST   /deployment-sets/{set_id}/members             - Add member (201)
    DELETE /deployment-sets/{set_id}/members/{member_id} - Remove member (204)
    PUT    /deployment-sets/{set_id}/members/{member_id} - Update member position (200)
    GET    /deployment-sets/{set_id}/resolve             - Resolve set recursively (200)
    POST   /deployment-sets/{set_id}/deploy              - Batch deploy (200)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from skillmeat.api.schemas.deployment_sets import (
    BatchDeployRequest,
    BatchDeployResponse,
    DeploymentSetCreate,
    DeploymentSetListResponse,
    DeploymentSetResponse,
    DeploymentSetUpdate,
    DeployResultItem,
    MemberCreate,
    MemberResponse,
    MemberUpdatePosition,
    ResolvedArtifactItem,
    ResolveResponse,
)
from skillmeat.cache.models import DeploymentSet, DeploymentSetMember, get_session
from skillmeat.cache.repositories import DeploymentSetRepository, RepositoryError
from skillmeat.core.deployment_sets import DeploymentSetService
from skillmeat.core.exceptions import DeploymentSetCycleError, DeploymentSetResolutionError

from ..config import get_settings
from ..dependencies import ArtifactManagerDep, SettingsDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployment-sets", tags=["deployment-sets"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_owner_id(settings) -> str:
    """Resolve owner_id from settings.

    When auth is disabled the owner is always the fixed local-user sentinel.
    Auth-enabled paths would derive the owner from the bearer token; that is
    not yet implemented.
    """
    if settings.auth_enabled:
        # Future: extract from verified token claim
        return "local-user"
    return "local-user"


def _ds_to_response(ds: DeploymentSet) -> DeploymentSetResponse:
    """Convert a DeploymentSet ORM instance to a response DTO."""
    return DeploymentSetResponse(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        icon=None,   # not persisted in current model
        color=None,  # not persisted in current model
        tags=ds.get_tags(),
        owner_id=ds.owner_id,
        member_count=len(ds.members) if ds.members is not None else 0,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


def _member_type(member: DeploymentSetMember) -> str:
    """Derive the member_type string from the ORM member row."""
    if member.artifact_uuid is not None:
        return "artifact"
    if member.group_id is not None:
        return "group"
    return "set"


def _member_to_response(member: DeploymentSetMember) -> MemberResponse:
    """Convert a DeploymentSetMember ORM instance to a response DTO."""
    return MemberResponse(
        id=member.id,
        deployment_set_id=member.set_id,
        artifact_uuid=member.artifact_uuid,
        group_id=member.group_id,
        nested_set_id=member.member_set_id,
        member_type=_member_type(member),
        position=member.position,
        added_at=member.created_at,
    )


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=DeploymentSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new deployment set",
)
def create_deployment_set(
    request: DeploymentSetCreate,
    settings: SettingsDep,
) -> DeploymentSetResponse:
    """Create a new named deployment set owned by the current user.

    Args:
        request: Deployment set creation payload.
        settings: API settings (owner derived from auth state).

    Returns:
        The newly created deployment set.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    try:
        ds = repo.create(
            name=request.name,
            owner_id=owner_id,
            description=request.description,
            tags=request.tags,
        )
    except RepositoryError as exc:
        logger.exception("Failed to create deployment set: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _ds_to_response(ds)


@router.get(
    "",
    response_model=DeploymentSetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List deployment sets",
)
def list_deployment_sets(
    settings: SettingsDep,
    name: Optional[str] = Query(default=None, description="Filter by name substring"),
    tag: Optional[str] = Query(default=None, description="Filter by tag"),
    limit: int = Query(default=50, ge=1, le=200, description="Page size"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> DeploymentSetListResponse:
    """List deployment sets owned by the current user, with optional filtering.

    Args:
        settings: API settings.
        name: Optional substring filter on set name.
        tag: Optional tag filter.
        limit: Maximum number of results to return.
        offset: Number of results to skip.

    Returns:
        Paginated list of deployment sets with total count.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    sets = repo.list(owner_id=owner_id, name=name, tag=tag, limit=limit, offset=offset)
    total = repo.count(owner_id=owner_id, name=name, tag=tag)

    return DeploymentSetListResponse(
        items=[_ds_to_response(ds) for ds in sets],
        total=total,
    )


@router.get(
    "/{set_id}",
    response_model=DeploymentSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a deployment set by ID",
)
def get_deployment_set(
    set_id: str,
    settings: SettingsDep,
) -> DeploymentSetResponse:
    """Fetch a single deployment set by its ID including its members.

    Args:
        set_id: Primary key of the deployment set.
        settings: API settings (owner scoping).

    Returns:
        The requested deployment set.

    Raises:
        HTTPException 404: If the set does not exist or belongs to another owner.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    ds = repo.get(set_id, owner_id)
    if ds is None:
        logger.warning("Deployment set not found: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    return _ds_to_response(ds)


@router.put(
    "/{set_id}",
    response_model=DeploymentSetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a deployment set",
)
def update_deployment_set(
    set_id: str,
    request: DeploymentSetUpdate,
    settings: SettingsDep,
) -> DeploymentSetResponse:
    """Update mutable metadata fields on a deployment set.

    Args:
        set_id: Primary key of the deployment set.
        request: Partial update payload (only provided fields are applied).
        settings: API settings.

    Returns:
        The updated deployment set.

    Raises:
        HTTPException 404: If the set does not exist or belongs to another owner.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    kwargs = {}
    if request.name is not None:
        kwargs["name"] = request.name
    if request.description is not None:
        kwargs["description"] = request.description
    if request.tags is not None:
        kwargs["tags"] = request.tags

    try:
        ds = repo.update(set_id, owner_id, **kwargs)
    except RepositoryError as exc:
        logger.exception("Failed to update deployment set %s: %s", set_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if ds is None:
        logger.warning("Deployment set not found for update: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    return _ds_to_response(ds)


@router.delete(
    "/{set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deployment set",
)
def delete_deployment_set(
    set_id: str,
    settings: SettingsDep,
) -> None:
    """Delete a deployment set and cascade-delete its member rows.

    Per FR-10: any member rows in *other* sets that reference this set as a
    nested member are also removed before the set itself is deleted.

    Args:
        set_id: Primary key of the deployment set.
        settings: API settings.

    Raises:
        HTTPException 404: If the set does not exist or belongs to another owner.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    try:
        deleted = repo.delete(set_id, owner_id)
    except RepositoryError as exc:
        logger.exception("Failed to delete deployment set %s: %s", set_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not deleted:
        logger.warning("Deployment set not found for deletion: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )


# ---------------------------------------------------------------------------
# Clone Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{set_id}/clone",
    response_model=DeploymentSetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone a deployment set",
)
def clone_deployment_set(
    set_id: str,
    settings: SettingsDep,
) -> DeploymentSetResponse:
    """Clone a deployment set and all its members.

    The clone receives a name of ``"<original name> (copy)"`` and a new UUID.
    Member rows are recreated preserving type, reference, and position.

    Args:
        set_id: Primary key of the source deployment set.
        settings: API settings.

    Returns:
        The newly created clone deployment set.

    Raises:
        HTTPException 404: If the source set does not exist.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    source = repo.get(set_id, owner_id)
    if source is None:
        logger.warning("Clone source not found: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    clone_name = f"{source.name} (copy)"

    try:
        clone = repo.create(
            name=clone_name,
            owner_id=owner_id,
            description=source.description,
            tags=source.get_tags(),
        )

        # Replicate members in position order
        for member in sorted(source.members or [], key=lambda m: m.position):
            repo.add_member(
                clone.id,
                owner_id,
                artifact_uuid=member.artifact_uuid,
                group_id=member.group_id,
                member_set_id=member.member_set_id,
                position=member.position,
            )
    except RepositoryError as exc:
        logger.exception("Failed to clone deployment set %s: %s", set_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Re-fetch to get the fully populated clone with members
    clone_full = repo.get(clone.id, owner_id)
    if clone_full is None:
        clone_full = clone

    return _ds_to_response(clone_full)


# ---------------------------------------------------------------------------
# Member Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{set_id}/members",
    response_model=List[MemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List members of a deployment set",
)
def list_members(
    set_id: str,
    settings: SettingsDep,
) -> List[MemberResponse]:
    """Return all members of a deployment set ordered by position.

    Args:
        set_id: Primary key of the parent deployment set.
        settings: API settings.

    Returns:
        Ordered list of member rows.

    Raises:
        HTTPException 404: If the set does not exist or belongs to another owner.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    ds = repo.get(set_id, owner_id)
    if ds is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    members = repo.get_members(set_id, owner_id)
    return [_member_to_response(m) for m in members]


@router.post(
    "/{set_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to a deployment set",
)
def add_member(
    set_id: str,
    request: MemberCreate,
    settings: SettingsDep,
) -> MemberResponse:
    """Add an artifact, group, or nested deployment set as a member.

    For nested set members (``nested_set_id`` provided), circular-reference
    detection is performed before insertion.  If the proposed nesting would
    create a cycle, HTTP 422 is returned.

    Args:
        set_id: Primary key of the parent deployment set.
        request: Member creation payload (exactly one ref must be set).
        settings: API settings.

    Returns:
        The newly created member row.

    Raises:
        HTTPException 404: If the parent set does not exist.
        HTTPException 422: If adding the member would create a circular reference.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    # Verify parent exists
    ds = repo.get(set_id, owner_id)
    if ds is None:
        logger.warning("Parent set not found for add_member: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    session = get_session()
    try:
        svc = DeploymentSetService(session=session)

        if request.nested_set_id is not None:
            # Cycle detection for set-type members
            try:
                member = svc.add_member_with_cycle_check(
                    set_id,
                    owner_id,
                    member_set_id=request.nested_set_id,
                    position=request.position,
                )
            except DeploymentSetCycleError as exc:
                logger.warning(
                    "Circular reference detected: set_id=%s nested_set_id=%s path=%s",
                    set_id,
                    request.nested_set_id,
                    exc.path,
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="This would create a circular reference",
                ) from exc
        else:
            # Artifact or group members — no cycle risk
            member = repo.add_member(
                set_id,
                owner_id,
                artifact_uuid=request.artifact_uuid,
                group_id=request.group_id,
                position=request.position,
            )
    except (RepositoryError, ValueError) as exc:
        logger.exception("Failed to add member to set %s: %s", set_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    finally:
        session.close()

    return _member_to_response(member)


@router.delete(
    "/{set_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from a deployment set",
)
def remove_member(
    set_id: str,
    member_id: str,
    settings: SettingsDep,
) -> None:
    """Remove a member row from a deployment set.

    Args:
        set_id: Primary key of the parent deployment set (used for owner check).
        member_id: Primary key of the member row to remove.
        settings: API settings.

    Raises:
        HTTPException 404: If the set or member does not exist.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    # Verify parent exists and is owned by this user
    ds = repo.get(set_id, owner_id)
    if ds is None:
        logger.warning("Set not found for remove_member: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    try:
        removed = repo.remove_member(member_id, owner_id)
    except RepositoryError as exc:
        logger.exception("Failed to remove member %s from set %s: %s", member_id, set_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not removed:
        logger.warning("Member not found for removal: member_id=%s set_id=%s", member_id, set_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member '{member_id}' not found in deployment set '{set_id}'.",
        )


@router.put(
    "/{set_id}/members/{member_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a member's position",
)
def update_member_position(
    set_id: str,
    member_id: str,
    request: MemberUpdatePosition,
    settings: SettingsDep,
) -> MemberResponse:
    """Update the ordering position of a member within a deployment set.

    Args:
        set_id: Primary key of the parent deployment set.
        member_id: Primary key of the member to update.
        request: Position update payload.
        settings: API settings.

    Returns:
        The updated member row.

    Raises:
        HTTPException 404: If the set or member does not exist.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    # Verify parent exists
    ds = repo.get(set_id, owner_id)
    if ds is None:
        logger.warning("Set not found for update_member_position: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    try:
        member = repo.update_member_position(member_id, owner_id, request.position)
    except RepositoryError as exc:
        logger.exception("Failed to update member position %s: %s", member_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if member is None:
        logger.warning("Member not found for position update: member_id=%s set_id=%s", member_id, set_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member '{member_id}' not found in deployment set '{set_id}'.",
        )

    return _member_to_response(member)


# ---------------------------------------------------------------------------
# Resolve Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/{set_id}/resolve",
    response_model=ResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve a deployment set to its flat artifact list",
)
def resolve_deployment_set(
    set_id: str,
    settings: SettingsDep,
) -> ResolveResponse:
    """Recursively resolve a deployment set into an ordered, deduplicated list
    of artifact UUIDs.

    Traversal is depth-first: artifact members are emitted directly, group
    members are expanded in position order, and nested set members are
    recursed into.  The first occurrence of each UUID is kept; duplicates are
    silently dropped.

    Args:
        set_id: Primary key of the root deployment set to resolve.
        settings: API settings.

    Returns:
        Resolution result including the flat artifact list and traversal metadata.

    Raises:
        HTTPException 404: If the set does not exist.
        HTTPException 422: If the resolution depth limit is exceeded.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    ds = repo.get(set_id, owner_id)
    if ds is None:
        logger.warning("Set not found for resolve: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    session = get_session()
    try:
        svc = DeploymentSetService(session=session)
        try:
            uuids = svc.resolve(set_id)
        except DeploymentSetResolutionError as exc:
            logger.warning("Resolution depth limit exceeded for set %s: %s", set_id, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        # Build resolved artifact items — enrich with name/type where possible
        from skillmeat.cache.models import Artifact

        if uuids:
            art_rows = (
                session.query(Artifact.uuid, Artifact.name, Artifact.type)
                .filter(Artifact.uuid.in_(uuids))
                .all()
            )
            uuid_info = {row.uuid: (row.name, row.type) for row in art_rows}
        else:
            uuid_info = {}

        resolved_artifacts = []
        for uuid in uuids:
            name, art_type = uuid_info.get(uuid, (None, None))
            resolved_artifacts.append(
                ResolvedArtifactItem(
                    artifact_uuid=uuid,
                    artifact_name=name,
                    artifact_type=art_type,
                    source_path=[ds.name],
                )
            )
    finally:
        session.close()

    return ResolveResponse(
        set_id=set_id,
        set_name=ds.name,
        resolved_artifacts=resolved_artifacts,
        total_count=len(resolved_artifacts),
    )


# ---------------------------------------------------------------------------
# Deploy Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{set_id}/deploy",
    response_model=BatchDeployResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch-deploy all artifacts in a deployment set",
)
def batch_deploy(
    set_id: str,
    request: BatchDeployRequest,
    settings: SettingsDep,
    artifact_mgr: ArtifactManagerDep,
) -> BatchDeployResponse:
    """Resolve the deployment set and deploy every artifact to the target project.

    Each artifact is deployed independently; per-artifact errors are captured
    and returned in the results list so a single failure does not abort the
    entire batch.

    Args:
        set_id: Primary key of the deployment set to deploy.
        request: Batch deploy payload (project_path, dry_run).
        settings: API settings.
        artifact_mgr: ArtifactManager dependency.

    Returns:
        Batch deployment result with per-artifact outcomes.

    Raises:
        HTTPException 404: If the set does not exist.
        HTTPException 422: If the project path is invalid or resolution fails.
    """
    owner_id = _get_owner_id(settings)
    repo = DeploymentSetRepository()

    ds = repo.get(set_id, owner_id)
    if ds is None:
        logger.warning("Set not found for batch_deploy: set_id=%s owner_id=%s", set_id, owner_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment set '{set_id}' not found.",
        )

    from pathlib import Path

    project_path = Path(request.project_path)
    if not project_path.exists():
        logger.warning("Project path does not exist: %s", project_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Project path '{request.project_path}' does not exist.",
        )

    session = get_session()
    try:
        svc = DeploymentSetService(session=session)

        try:
            uuids = svc.resolve(set_id)
        except DeploymentSetResolutionError as exc:
            logger.warning("Resolution failed for set %s during deploy: %s", set_id, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        # Resolve artifact metadata for result enrichment
        from skillmeat.cache.models import Artifact, CollectionArtifact

        if uuids:
            art_rows = (
                session.query(Artifact.uuid, Artifact.name, Artifact.type)
                .join(CollectionArtifact, CollectionArtifact.artifact_uuid == Artifact.uuid)
                .filter(Artifact.uuid.in_(uuids))
                .all()
            )
            uuid_info = {row.uuid: (row.name, row.type) for row in art_rows}
        else:
            uuid_info = {}

        results: List[DeployResultItem] = []
        succeeded = 0
        failed = 0
        skipped = 0

        for artifact_uuid in uuids:
            # Dry-run: skip all artifacts regardless of cache state
            if request.dry_run:
                artifact_name = uuid_info.get(artifact_uuid, (None, None))[0]
                results.append(
                    DeployResultItem(
                        artifact_uuid=artifact_uuid,
                        artifact_name=artifact_name,
                        status="skipped",
                        error=None,
                    )
                )
                skipped += 1
                continue

            if artifact_uuid not in uuid_info:
                logger.warning(
                    "batch_deploy: artifact UUID not in collection cache — skipping: %s",
                    artifact_uuid,
                )
                results.append(
                    DeployResultItem(
                        artifact_uuid=artifact_uuid,
                        artifact_name=None,
                        status="failed",
                        error=f"Artifact UUID '{artifact_uuid}' not found in collection cache.",
                    )
                )
                failed += 1
                continue

            artifact_name, artifact_type = uuid_info[artifact_uuid]

            try:
                artifact_mgr.deploy_artifacts(
                    artifact_names=[artifact_name],
                    project_path=project_path,
                )
                results.append(
                    DeployResultItem(
                        artifact_uuid=artifact_uuid,
                        artifact_name=artifact_name,
                        status="success",
                        error=None,
                    )
                )
                succeeded += 1
                logger.info("batch_deploy: deployed %s:%s", artifact_type, artifact_name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "batch_deploy: deploy failed for %s:%s — %s",
                    artifact_type,
                    artifact_name,
                    exc,
                )
                results.append(
                    DeployResultItem(
                        artifact_uuid=artifact_uuid,
                        artifact_name=artifact_name,
                        status="failed",
                        error=str(exc),
                    )
                )
                failed += 1
    finally:
        session.close()

    logger.info(
        "batch_deploy complete: set_id=%s total=%d succeeded=%d failed=%d skipped=%d",
        set_id,
        len(results),
        succeeded,
        failed,
        skipped,
    )

    return BatchDeployResponse(
        set_id=set_id,
        set_name=ds.name,
        project_path=request.project_path,
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        results=results,
        dry_run=request.dry_run,
    )
