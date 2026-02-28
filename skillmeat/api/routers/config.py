"""Configuration endpoint router.

This module provides endpoints for exposing backend configuration to frontend
applications, enabling consistent behavior across the stack.
"""

import logging

from fastapi import APIRouter, status

from skillmeat.api.dependencies import SettingsDep
from skillmeat.api.schemas.config import DetectionPatternsResponse, FeatureFlagsResponse
from skillmeat.core.artifact_detection import (
    CANONICAL_CONTAINERS,
    CONTAINER_ALIASES,
    ArtifactType,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/config",
    tags=["config"],
)


@router.get(
    "/detection-patterns",
    response_model=DetectionPatternsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get artifact detection patterns",
    description="""
    Returns the detection patterns used by the backend for identifying artifact types
    from directory structures. This includes:

    - **container_aliases**: Maps each artifact type to all valid container directory names
    - **leaf_containers**: Flattened list of all valid container names for quick lookups
    - **canonical_containers**: Maps each artifact type to its preferred container name

    Frontend applications can use this data to replicate the same detection logic
    for consistent artifact type inference across the stack.
    """,
)
async def get_detection_patterns() -> DetectionPatternsResponse:
    """Get artifact detection patterns for frontend consumption.

    Returns the centralized detection patterns used by the Python backend,
    allowing frontend applications to perform consistent artifact detection.

    Returns:
        DetectionPatternsResponse with container aliases, leaf containers,
        and canonical container mappings.
    """
    # Convert CONTAINER_ALIASES from Dict[ArtifactType, Set[str]] to Dict[str, List[str]]
    container_aliases: dict[str, list[str]] = {
        artifact_type.value: sorted(aliases)
        for artifact_type, aliases in CONTAINER_ALIASES.items()
    }

    # Flatten all aliases to create leaf_containers list (unique, sorted)
    all_containers: set[str] = set()
    for aliases in CONTAINER_ALIASES.values():
        all_containers.update(aliases)
    leaf_containers = sorted(all_containers)

    # Convert CANONICAL_CONTAINERS from Dict[ArtifactType, str] to Dict[str, str]
    canonical_containers: dict[str, str] = {
        artifact_type.value: canonical_name
        for artifact_type, canonical_name in CANONICAL_CONTAINERS.items()
    }

    logger.debug(
        f"Returning detection patterns: {len(container_aliases)} types, "
        f"{len(leaf_containers)} containers"
    )

    return DetectionPatternsResponse(
        container_aliases=container_aliases,
        leaf_containers=leaf_containers,
        canonical_containers=canonical_containers,
    )


@router.get(
    "/feature-flags",
    response_model=FeatureFlagsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get backend feature flags",
    description="""
    Returns the current state of backend feature flags so the frontend can
    conditionally render features that depend on backend capabilities.

    Features gated by these flags:
    - **deployment_sets_enabled**: Controls visibility of Deployment Sets UI and nav item.
      When False, the `/api/v1/deployment-sets` endpoints return 404.
    - **composite_artifacts_enabled**: Controls composite artifact detection UI.
    - **memory_context_enabled**: Controls Memory & Context Intelligence System UI.
    - **workflow_engine_enabled**: Controls Workflow Orchestration Engine UI.
      When False, the `/api/v1/workflows` and `/api/v1/workflow-executions` endpoints
      return 404 and CLI workflow commands display a coming-soon message.
    """,
)
async def get_feature_flags(settings: SettingsDep) -> FeatureFlagsResponse:
    """Get backend feature flags for frontend consumption.

    Reads current feature flag state from APISettings and returns it to the
    frontend. The frontend uses these flags to conditionally show/hide nav items,
    pages, and UI elements that depend on backend feature availability.

    Returns:
        FeatureFlagsResponse with boolean flag values for each feature.
    """
    logger.debug("Returning feature flags to frontend")

    return FeatureFlagsResponse(
        composite_artifacts_enabled=settings.composite_artifacts_enabled,
        deployment_sets_enabled=settings.deployment_sets_enabled,
        memory_context_enabled=settings.memory_context_enabled,
        workflow_engine_enabled=settings.workflow_engine_enabled,
    )
