"""Deployment profile API endpoints."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from skillmeat.api.dependencies import (
    DeploymentProfileRepoDep,
    ProjectRepoDep,
    verify_api_key,
)
from skillmeat.api.middleware.auth import TokenDep
from skillmeat.api.schemas.common import ErrorResponse
from skillmeat.api.schemas.deployment_profiles import (
    DeploymentProfileCreate,
    DeploymentProfileRead,
    DeploymentProfileUpdate,
)
from skillmeat.core.interfaces.repositories import IProjectRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects",
    tags=["deployment-profiles"],
    dependencies=[Depends(verify_api_key)],
)


def _to_read_model(profile) -> DeploymentProfileRead:
    return DeploymentProfileRead(
        id=profile.id,
        project_id=profile.project_id,
        profile_id=profile.profile_id,
        platform=profile.platform,
        root_dir=profile.root_dir,
        description=profile.description,
        artifact_path_map=profile.artifact_path_map or {},
        project_config_filenames=profile.config_filenames or [],
        context_path_prefixes=profile.context_prefixes or [],
        supported_artifact_types=profile.supported_types or [],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _resolve_project_db_id(project_id: str, project_repo: IProjectRepository) -> str:
    """Resolve API project id to cache project primary key.

    Supports both:
    - direct cache project IDs (looked up via ``project_repo.get()``)
    - base64-encoded project paths (resolved via ``project_repo.get_or_create_by_path()``)

    Args:
        project_id: Raw project id from the API path parameter.
        project_repo: IProjectRepository instance injected via ``ProjectRepoDep``.
    """
    # Try direct ID lookup first (handles raw cache project IDs)
    existing = project_repo.get(project_id)
    if existing is not None:
        return existing.id

    # Attempt to decode as a base64-encoded path
    decoded_path: str | None = None
    try:
        decoded_path = base64.b64decode(project_id.encode()).decode()
    except Exception:
        decoded_path = None

    if decoded_path:
        # get_or_create_by_path resolves the path and creates a DB record if absent
        dto = project_repo.get_or_create_by_path(
            str(Path(decoded_path).expanduser().resolve())
        )
        return dto.id

    # Fallback: treat project_id as a raw cache project id (legacy behaviour)
    return project_id


@router.post(
    "/{project_id}/profiles",
    response_model=DeploymentProfileRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Deployment profile created"},
        409: {"model": ErrorResponse, "description": "Profile already exists"},
    },
)
async def create_profile(
    project_id: str,
    request: DeploymentProfileCreate,
    token: TokenDep,
    repo: DeploymentProfileRepoDep,
    project_repo: ProjectRepoDep,
) -> DeploymentProfileRead:
    resolved_project_id = _resolve_project_db_id(project_id, project_repo)
    try:
        created = repo.create(
            project_id=resolved_project_id,
            profile_id=request.profile_id,
            platform=request.platform.value,
            root_dir=request.root_dir,
            description=request.description,
            artifact_path_map=request.artifact_path_map,
            config_filenames=request.project_config_filenames,
            context_prefixes=request.context_path_prefixes,
            supported_types=request.supported_artifact_types,
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Deployment profile '{request.profile_id}' already exists",
            )
        raise

    return _to_read_model(created)


@router.get(
    "/{project_id}/profiles",
    response_model=List[DeploymentProfileRead],
)
async def list_profiles(
    project_id: str,
    token: TokenDep,
    repo: DeploymentProfileRepoDep,
    project_repo: ProjectRepoDep,
) -> List[DeploymentProfileRead]:
    resolved_project_id = _resolve_project_db_id(project_id, project_repo)
    return [
        _to_read_model(profile) for profile in repo.list_by_project(resolved_project_id)
    ]


@router.get(
    "/{project_id}/profiles/{profile_id}",
    response_model=DeploymentProfileRead,
    responses={404: {"model": ErrorResponse, "description": "Profile not found"}},
)
async def get_profile(
    project_id: str,
    profile_id: str,
    token: TokenDep,
    repo: DeploymentProfileRepoDep,
    project_repo: ProjectRepoDep,
) -> DeploymentProfileRead:
    resolved_project_id = _resolve_project_db_id(project_id, project_repo)
    profile = repo.read_by_project_and_profile_id(resolved_project_id, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment profile '{profile_id}' not found",
        )
    return _to_read_model(profile)


@router.put(
    "/{project_id}/profiles/{profile_id}",
    response_model=DeploymentProfileRead,
    responses={404: {"model": ErrorResponse, "description": "Profile not found"}},
)
async def update_profile(
    project_id: str,
    profile_id: str,
    request: DeploymentProfileUpdate,
    token: TokenDep,
    repo: DeploymentProfileRepoDep,
    project_repo: ProjectRepoDep,
) -> DeploymentProfileRead:
    resolved_project_id = _resolve_project_db_id(project_id, project_repo)
    updated = repo.update(
        project_id=resolved_project_id,
        profile_id=profile_id,
        platform=request.platform.value if request.platform else None,
        root_dir=request.root_dir,
        description=request.description,
        artifact_path_map=request.artifact_path_map,
        config_filenames=request.project_config_filenames,
        context_prefixes=request.context_path_prefixes,
        supported_types=request.supported_artifact_types,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment profile '{profile_id}' not found",
        )
    return _to_read_model(updated)


@router.delete(
    "/{project_id}/profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={404: {"model": ErrorResponse, "description": "Profile not found"}},
)
async def delete_profile(
    project_id: str,
    profile_id: str,
    token: TokenDep,
    repo: DeploymentProfileRepoDep,
    project_repo: ProjectRepoDep,
) -> None:
    resolved_project_id = _resolve_project_db_id(project_id, project_repo)
    deleted = repo.delete(resolved_project_id, profile_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment profile '{profile_id}' not found",
        )
