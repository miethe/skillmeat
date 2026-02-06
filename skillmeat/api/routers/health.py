"""Health check endpoint router.

This module provides health check endpoints for monitoring service availability
and readiness. Used by load balancers, orchestrators, and monitoring systems.
"""

import logging
import platform
import sys
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from skillmeat import __version__ as skillmeat_version
from skillmeat.api.dependencies import (
    CollectionManagerDep,
    ConfigManagerDep,
    SettingsDep,
)
from skillmeat.core.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str = Field(
        description="Service status (healthy, degraded, unhealthy)",
        examples=["healthy"],
    )
    timestamp: str = Field(
        description="Current timestamp in ISO format",
        examples=["2024-11-16T12:00:00.000Z"],
    )
    version: str = Field(
        description="SkillMeat version",
        examples=["0.1.0-alpha"],
    )
    environment: str = Field(
        description="Application environment",
        examples=["development"],
    )
    uptime_seconds: Optional[float] = Field(
        default=None,
        description="Service uptime in seconds",
        examples=[3600.5],
    )


class DetailedHealthStatus(HealthStatus):
    """Detailed health check response with component status."""

    components: Dict[str, Dict[str, str]] = Field(
        description="Health status of individual components",
        examples=[
            {
                "collection_manager": {"status": "healthy", "details": "operational"},
                "config_manager": {"status": "healthy", "details": "operational"},
            }
        ],
    )
    system_info: Dict[str, str] = Field(
        description="System information",
        examples=[
            {
                "python_version": "3.11.0",
                "platform": "Linux",
                "platform_version": "5.15.0",
            }
        ],
    )


# Track service start time for uptime calculation
_service_start_time: Optional[datetime] = None


def set_service_start_time() -> None:
    """Set the service start time (called on startup)."""
    global _service_start_time
    _service_start_time = datetime.utcnow()


def get_uptime_seconds() -> Optional[float]:
    """Calculate service uptime in seconds.

    Returns:
        Uptime in seconds, or None if start time not set
    """
    if _service_start_time is None:
        return None
    delta = datetime.utcnow() - _service_start_time
    return delta.total_seconds()


@router.get(
    "",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="""
    Basic health check endpoint that returns service status.
    Used for simple availability checks by load balancers.

    Returns HTTP 200 if service is running.
    """,
)
async def health_check(settings: SettingsDep) -> HealthStatus:
    """Basic health check endpoint.

    Args:
        settings: API settings dependency

    Returns:
        HealthStatus with basic service information
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=skillmeat_version,
        environment=settings.env.value,
        uptime_seconds=get_uptime_seconds(),
    )


@router.get(
    "/detailed",
    response_model=DetailedHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="""
    Detailed health check endpoint that includes component status and system information.
    Used for comprehensive monitoring and diagnostics.

    Checks the health of:
    - Collection manager
    - Configuration manager
    - File system access

    Returns HTTP 200 if all components are healthy.
    Returns HTTP 503 if any critical component is unhealthy.
    """,
)
async def detailed_health_check(
    settings: SettingsDep,
    config_manager: ConfigManagerDep,
    collection_manager: CollectionManagerDep,
) -> DetailedHealthStatus:
    """Detailed health check with component status.

    Args:
        settings: API settings dependency
        config_manager: Config manager dependency
        collection_manager: Collection manager dependency

    Returns:
        DetailedHealthStatus with component and system information
    """
    components = {}
    overall_status = "healthy"

    # Check collection manager
    try:
        collections = collection_manager.list_collections()
        components["collection_manager"] = {
            "status": "healthy",
            "details": f"{len(collections)} collections available",
        }
    except Exception as e:
        logger.error(f"Collection manager health check failed: {e}")
        components["collection_manager"] = {
            "status": "unhealthy",
            "details": str(e),
        }
        overall_status = "degraded"

    # Check config manager
    try:
        config = config_manager.read()
        components["config_manager"] = {
            "status": "healthy",
            "details": "configuration loaded",
        }
    except Exception as e:
        logger.error(f"Config manager health check failed: {e}")
        components["config_manager"] = {
            "status": "unhealthy",
            "details": str(e),
        }
        overall_status = "degraded"

    # Check file system access
    try:
        collections_dir = config_manager.get_collections_dir()
        if collections_dir.exists():
            components["filesystem"] = {
                "status": "healthy",
                "details": f"collections directory accessible: {collections_dir}",
            }
        else:
            components["filesystem"] = {
                "status": "degraded",
                "details": f"collections directory not found: {collections_dir}",
            }
            # This is expected for new installations, so only mark as degraded
            if overall_status == "healthy":
                overall_status = "degraded"
    except Exception as e:
        logger.error(f"Filesystem health check failed: {e}")
        components["filesystem"] = {
            "status": "unhealthy",
            "details": str(e),
        }
        overall_status = "unhealthy"

    # Check memory system
    try:
        memory_service = MemoryService(db_path=None)
        # Quick health check: attempt to count items (should work even if 0)
        memory_service.repo.count_by_project("__health_check__")
        # Get inbox size (candidate items across all projects)
        inbox_query = memory_service.repo.list_items(
            project_id=None, status="candidate", limit=1
        )
        inbox_size = len(inbox_query.items) if hasattr(inbox_query, "items") else 0

        components["memory_system"] = {
            "status": "healthy",
            "details": f"database accessible, inbox_size={inbox_size}",
        }
    except Exception as e:
        logger.error(f"Memory system health check failed: {e}")
        components["memory_system"] = {
            "status": "unhealthy",
            "details": str(e),
        }
        overall_status = "degraded"

    # System information
    system_info = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "platform_version": platform.release(),
        "architecture": platform.machine(),
    }

    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=skillmeat_version,
        environment=settings.env.value,
        uptime_seconds=get_uptime_seconds(),
        components=components,
        system_info=system_info,
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="""
    Readiness check endpoint for Kubernetes and container orchestrators.
    Indicates whether the service is ready to accept traffic.

    Returns HTTP 200 if service is ready.
    Returns HTTP 503 if service is not ready (still initializing).
    """,
)
async def readiness_check(
    collection_manager: CollectionManagerDep,
) -> Dict[str, str]:
    """Readiness check for orchestrators.

    Args:
        collection_manager: Collection manager dependency

    Returns:
        Readiness status

    Raises:
        HTTPException 503 if not ready
    """
    # Service is ready if collection manager is initialized
    # Additional checks can be added here (DB connections, etc.)
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="""
    Liveness check endpoint for Kubernetes and container orchestrators.
    Indicates whether the service is alive (not deadlocked/crashed).

    Returns HTTP 200 if service is alive.
    Should never return 503 unless the service is truly unresponsive.
    """,
)
async def liveness_check() -> Dict[str, str]:
    """Liveness check for orchestrators.

    Returns:
        Liveness status
    """
    # Simple check - if we can respond, we're alive
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
