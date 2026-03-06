"""Enterprise artifact download endpoint.

Exposes ``GET /api/v1/artifacts/{artifact_id}/download`` for enterprise
clients that need to fetch complete artifact bundles.  Authentication and
tenant isolation will be added in ENT-3.4; for now the tenant is hardcoded
to ``"default"``.

Routes
------
GET /api/v1/artifacts/{artifact_id}/download
    Download a full artifact payload (JSON or gzip-compressed).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from skillmeat.api.dependencies import DbSessionDep, verify_api_key
from skillmeat.api.schemas.enterprise import ArtifactDownloadResponse
from skillmeat.cache.enterprise_repositories import EnterpriseArtifactRepository
from skillmeat.core.services.enterprise_content import (
    ArtifactFilesystemError,
    ArtifactNotFoundError,
    EnterpriseContentService,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/artifacts",
    tags=["enterprise"],
    dependencies=[Depends(verify_api_key)],
)

# ---------------------------------------------------------------------------
# Dependency: per-request EnterpriseContentService
# ---------------------------------------------------------------------------


def _get_content_service(session: DbSessionDep) -> EnterpriseContentService:
    """Build an ``EnterpriseContentService`` for the current request.

    Tenant isolation is controlled via ``TenantContext`` (a ContextVar in
    ``skillmeat.cache.enterprise_repositories``).  When ``TenantContext`` is
    not set, the repository falls back to ``DEFAULT_TENANT_ID`` automatically.
    ENT-3.4 will set ``TenantContext`` via an authentication middleware before
    this dependency runs, replacing the implicit default.

    Parameters
    ----------
    session:
        Per-request SQLAlchemy session injected by ``DbSessionDep``.

    Returns
    -------
    EnterpriseContentService
        Service instance ready for use within the current request.
    """
    repo = EnterpriseArtifactRepository(session)
    return EnterpriseContentService(session=session, artifact_repo=repo)


ContentServiceDep = Annotated[EnterpriseContentService, Depends(_get_content_service)]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{artifact_id}/download",
    summary="Download enterprise artifact payload",
    description=(
        "Return the complete file bundle for an enterprise artifact identified by "
        "UUID or name.  Use ``compress=true`` to receive a gzip-compressed payload "
        "instead of JSON."
    ),
    response_model=ArtifactDownloadResponse,
    responses={
        200: {
            "description": (
                "Artifact payload as JSON (default) or ``application/gzip`` bytes "
                "when ``compress=true``."
            ),
        },
        404: {"description": "Artifact not found for the current tenant."},
        500: {"description": "Filesystem error prevented bundle assembly."},
    },
)
def download_artifact(
    artifact_id: str,
    svc: ContentServiceDep,
    compress: bool = Query(
        default=False,
        description=(
            "When true, return gzip-compressed JSON bytes "
            "(Content-Type: application/gzip) instead of a JSON response."
        ),
    ),
) -> ArtifactDownloadResponse | Response:
    """Download an enterprise artifact bundle.

    Parameters
    ----------
    artifact_id:
        UUID string or human-readable artifact name.  UUID lookup is
        attempted first; name lookup is used as a fallback.
    svc:
        ``EnterpriseContentService`` injected per-request.
    compress:
        When ``True``, return gzip-compressed bytes with
        ``Content-Type: application/gzip``.  When ``False`` (default),
        return a JSON response matching ``ArtifactDownloadResponse``.

    Returns
    -------
    ArtifactDownloadResponse | Response
        JSON payload or raw gzip bytes depending on the ``compress`` flag.

    Raises
    ------
    HTTPException(404)
        If the artifact does not exist for the current tenant.
    HTTPException(500)
        If the artifact's files cannot be read from the filesystem.
    """
    try:
        result = svc.build_payload(artifact_id, compress=compress)
    except ArtifactNotFoundError as exc:
        logger.info("Enterprise download: artifact not found — %s", exc.artifact_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact not found: {exc.artifact_id!r}",
        ) from exc
    except ArtifactFilesystemError as exc:
        logger.exception(
            "Enterprise download: filesystem error for artifact %r — %s",
            artifact_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Artifact files could not be read from the filesystem.",
        ) from exc
    except Exception as exc:
        logger.exception(
            "Enterprise download: unexpected error for artifact %r", artifact_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while assembling artifact bundle.",
        ) from exc

    if compress:
        # build_payload returns bytes when compress=True.
        return Response(
            content=result,  # type: ignore[arg-type]
            media_type="application/gzip",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{artifact_id}.json.gz"'
                ),
            },
        )

    # Uncompressed path: result is a plain dict; validate through the schema.
    return ArtifactDownloadResponse(**result)  # type: ignore[arg-type]
