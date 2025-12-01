"""Example: FileWatcher integration with FastAPI server.

This demonstrates how to integrate the FileWatcher with the SkillMeat API
server for automatic cache invalidation during development and production.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from skillmeat.cache import CacheRepository, FileWatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
cache_repo: CacheRepository | None = None
file_watcher: FileWatcher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: startup and shutdown.

    This is the recommended way to manage startup/shutdown in FastAPI 0.104+.
    Replaces @app.on_event("startup") and @app.on_event("shutdown").
    """
    global cache_repo, file_watcher

    # Startup
    logger.info("Starting SkillMeat API server...")

    try:
        # Initialize cache repository
        cache_repo = CacheRepository()
        logger.info("Cache repository initialized")

        # Initialize and start file watcher
        file_watcher = FileWatcher(
            cache_repository=cache_repo,
            debounce_ms=100,  # 100ms debounce for development
        )
        file_watcher.start()
        logger.info(
            f"FileWatcher started, monitoring {len(file_watcher.get_watch_paths())} paths"
        )

        # Log watched paths
        for path in file_watcher.get_watch_paths():
            logger.info(f"  - Watching: {path}")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield  # Server is running

    # Shutdown
    logger.info("Shutting down SkillMeat API server...")

    try:
        # Stop file watcher
        if file_watcher and file_watcher.is_running():
            file_watcher.stop()
            logger.info("FileWatcher stopped")

        logger.info("Shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application with lifespan
app = FastAPI(
    title="SkillMeat API",
    description="Personal collection manager for Claude Code artifacts",
    version="0.3.0-beta",
    lifespan=lifespan,
)


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Service health status including watcher state
    """
    watcher_status = "unknown"
    watched_paths = []

    if file_watcher:
        if file_watcher.is_running():
            watcher_status = "running"
            watched_paths = file_watcher.get_watch_paths()
        else:
            watcher_status = "stopped"

    return {
        "status": "healthy",
        "service": "skillmeat-api",
        "version": "0.3.0-beta",
        "cache": {
            "repository": "active" if cache_repo else "inactive",
            "watcher": watcher_status,
            "watched_paths": len(watched_paths),
        },
    }


@app.get("/health/watcher")
async def watcher_health() -> dict:
    """Detailed watcher health check.

    Returns:
        Detailed watcher status and configuration

    Raises:
        HTTPException: If watcher is not initialized
    """
    if not file_watcher:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FileWatcher not initialized",
        )

    return {
        "running": file_watcher.is_running(),
        "watched_paths": file_watcher.get_watch_paths(),
        "debounce_ms": file_watcher.debounce_ms,
        "active_observers": len(file_watcher.observers),
        "queued_invalidations": len(file_watcher.invalidation_queue),
    }


# =============================================================================
# Watcher Management Endpoints (Admin)
# =============================================================================


@app.post("/admin/watcher/add-path")
async def add_watch_path(path: str) -> dict:
    """Add a new path to watch (admin only).

    Args:
        path: Directory path to watch

    Returns:
        Operation result

    Raises:
        HTTPException: If watcher not initialized or path invalid
    """
    if not file_watcher:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FileWatcher not initialized",
        )

    success = file_watcher.add_watch_path(path)

    if success:
        return {"status": "success", "message": f"Added watch path: {path}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add watch path: {path}",
        )


@app.post("/admin/watcher/remove-path")
async def remove_watch_path(path: str) -> dict:
    """Remove a path from watching (admin only).

    Args:
        path: Directory path to stop watching

    Returns:
        Operation result

    Raises:
        HTTPException: If watcher not initialized or path not watched
    """
    if not file_watcher:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FileWatcher not initialized",
        )

    success = file_watcher.remove_watch_path(path)

    if success:
        return {"status": "success", "message": f"Removed watch path: {path}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path not being watched: {path}",
        )


@app.post("/admin/watcher/invalidate")
async def trigger_invalidation(project_id: str | None = None) -> dict:
    """Manually trigger cache invalidation (admin only).

    Args:
        project_id: Optional project ID to invalidate (None for global)

    Returns:
        Operation result

    Raises:
        HTTPException: If watcher not initialized
    """
    if not file_watcher:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FileWatcher not initialized",
        )

    file_watcher._queue_invalidation(project_id)

    scope = "global" if project_id is None else f"project {project_id}"
    return {
        "status": "success",
        "message": f"Queued invalidation for {scope}",
    }


# =============================================================================
# Cache Statistics Endpoints
# =============================================================================


@app.get("/admin/cache/stats")
async def cache_stats() -> dict:
    """Get cache statistics.

    Returns:
        Cache statistics including project counts

    Raises:
        HTTPException: If cache not initialized
    """
    if not cache_repo:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache repository not initialized",
        )

    try:
        projects = cache_repo.list_projects()
        active_projects = [p for p in projects if p.status == "active"]
        stale_projects = [p for p in projects if p.status == "stale"]
        error_projects = [p for p in projects if p.status == "error"]

        return {
            "total_projects": len(projects),
            "active_projects": len(active_projects),
            "stale_projects": len(stale_projects),
            "error_projects": len(error_projects),
        }

    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache statistics: {str(e)}",
        )


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """Global exception handler for uncaught errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
        },
    )


# =============================================================================
# Development Server
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    # Enable debug logging for development
    logging.getLogger("skillmeat.cache.watcher").setLevel(logging.DEBUG)

    logger.info("Starting development server with FileWatcher...")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload when using FileWatcher
        log_level="info",
    )
