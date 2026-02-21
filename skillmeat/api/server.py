"""FastAPI server application for SkillMeat.

This module provides the main FastAPI application with lifespan management,
middleware configuration, and route registration. It serves as the entry point
for the web service layer.
"""

# Load .env file into os.environ BEFORE any other imports
# This ensures environment variables are available to all modules
# including GitHubClientWrapper which checks os.environ for tokens
from dotenv import load_dotenv

load_dotenv()  # Loads .env from current directory or parents

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from skillmeat import __version__ as skillmeat_version

from .config import APISettings, get_settings
from .dependencies import app_state
from .routers import (
    analytics,
    artifacts,
    bundles,
    cache,
    collections,
    composites,
    config,
    context_entities,
    context_modules,
    context_packing,
    context_sync,
    deployment_profiles,
    deployments,
    groups,
    health,
    marketplace,
    marketplace_catalog,
    marketplace_sources,
    match,
    mcp,
    memory_items,
    merge,
    project_templates,
    projects,
    ratings,
    settings as settings_router,
    tags,
    user_collections,
    versions,
)
from .middleware import ObservabilityMiddleware, RateLimitMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown.

    This context manager handles:
    - Loading configuration
    - Initializing managers and dependencies
    - Configuring logging
    - Cleanup on shutdown

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("Starting SkillMeat API service...")

    # Load settings
    settings = get_settings()
    logger.info(f"Environment: {settings.env.value}")
    logger.info(f"API Version: {settings.api_version}")
    logger.info(f"Host: {settings.host}:{settings.port}")
    logger.info(
        "Authentication: %s",
        "enabled (Bearer tokens required)" if settings.auth_enabled else "disabled",
    )

    # Configure logging
    settings.configure_logging()
    logger.info("Logging configured")

    # Initialize application state
    app_state.initialize(settings)
    logger.info("Application state initialized")

    # Log GitHub API status
    try:
        from skillmeat.core.github_client import get_github_client

        github_client = get_github_client()
        rate_limit = github_client.get_rate_limit()
        if github_client.is_authenticated():
            logger.info(
                f"GitHub API: Token configured ({rate_limit['remaining']}/{rate_limit['limit']} requests remaining)"
            )
        else:
            logger.info(
                f"GitHub API: No token configured ({rate_limit['limit']} requests/hour limit)"
            )
    except Exception as e:
        logger.warning(f"GitHub API: Could not check status - {e}")

    # Check git availability for clone-based artifact indexing
    try:
        from skillmeat.api.routers.marketplace_sources import check_git_available

        await check_git_available()
    except Exception as e:
        logger.warning(f"Git availability check failed - {e}")

    # Set service start time for health checks
    from .routers.health import set_service_start_time

    set_service_start_time()

    # Ensure default collection exists and migrate existing artifacts
    try:
        from skillmeat.api.routers.user_collections import (
            ensure_default_collection,
            migrate_artifacts_to_default_collection,
        )
        from skillmeat.api.utils.fts5 import check_fts5_available
        from skillmeat.cache.models import get_session

        session = get_session()
        try:
            ensure_default_collection(session)
            logger.info("Default collection verified/created")

            # Check FTS5 availability at startup
            check_fts5_available(session)

            # Migrate existing artifacts to default collection
            if app_state.artifact_manager and app_state.collection_manager:
                result = migrate_artifacts_to_default_collection(
                    session=session,
                    artifact_mgr=app_state.artifact_manager,
                    collection_mgr=app_state.collection_manager,
                )
                logger.info(
                    f"Artifact migration: {result['migrated_count']} migrated, "
                    f"{result['already_present_count']} already present, "
                    f"{result['total_artifacts']} total"
                )
                # Log metadata cache stats if available
                if "metadata_cache" in result:
                    cache_stats = result["metadata_cache"]
                    if cache_stats.get("errors"):
                        logger.warning(
                            f"Metadata cache errors: {len(cache_stats['errors'])} artifacts failed"
                        )
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Could not ensure default collection or migrate artifacts: {e}")

    logger.info(f"SkillMeat API v{skillmeat_version} started successfully")

    yield

    # Shutdown
    logger.info("Shutting down SkillMeat API service...")
    app_state.shutdown()
    logger.info("SkillMeat API service stopped")


def create_app(settings: APISettings = None) -> FastAPI:
    """Create and configure FastAPI application.

    Args:
        settings: Optional settings override (useful for testing)

    Returns:
        Configured FastAPI application instance
    """
    # Use provided settings or load from environment
    if settings is None:
        settings = get_settings()

    # Create FastAPI app with OpenAPI documentation
    app = FastAPI(
        title=settings.api_title,
        description=settings.api_description,
        version=skillmeat_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    # Add observability middleware (should be added early to track all requests)
    app.add_middleware(ObservabilityMiddleware)
    logger.info("Observability middleware enabled")

    app.add_middleware(
        RateLimitMiddleware,
        window_seconds=10,
        burst_threshold=20,
        block_duration=10,
    )
    logger.info("RateLimit middleware enabled")

    # Configure CORS middleware
    if settings.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=settings.cors_allow_methods,
            allow_headers=settings.cors_allow_headers,
        )
        logger.info(f"CORS enabled with origins: {settings.cors_origins}")

    # Add exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors with detailed error messages.

        Args:
            request: The request that caused the error
            exc: The validation exception

        Returns:
            JSON response with error details
        """
        logger.warning(f"Validation error for {request.url}: {exc.errors()}")

        # Serialize error details, removing non-JSON-serializable objects
        def serialize_errors(errors):
            """Convert validation errors to JSON-serializable format."""
            serialized = []
            for error in errors:
                error_dict = {
                    "type": error.get("type"),
                    "loc": error.get("loc"),
                    "msg": error.get("msg"),
                }
                # Include input if available and serializable
                if "input" in error:
                    try:
                        import json

                        json.dumps(error["input"])
                        error_dict["input"] = error["input"]
                    except (TypeError, ValueError):
                        error_dict["input"] = str(error["input"])

                # Skip ctx as it often contains non-serializable exceptions
                serialized.append(error_dict)
            return serialized

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": serialize_errors(exc.errors())},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected errors.

        Args:
            request: The request that caused the error
            exc: The exception

        Returns:
            JSON response with error message
        """
        logger.error(f"Unexpected error for {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": (
                    "Internal server error" if settings.is_production else str(exc)
                ),
            },
        )

    # Add request logging middleware (development only)
    if settings.is_development:

        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            """Log all requests in development mode.

            Args:
                request: The incoming request
                call_next: Next middleware in chain

            Returns:
                Response from the next middleware
            """
            logger.debug(f"{request.method} {request.url.path}")
            response = await call_next(request)
            logger.debug(f"Response status: {response.status_code}")
            return response

    # Mount Prometheus metrics endpoint
    try:
        from prometheus_client import make_asgi_app

        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
        logger.info("Prometheus metrics endpoint enabled at /metrics")
    except ImportError:
        logger.warning("prometheus_client not installed, metrics endpoint disabled")

    # Include routers
    # Health check router (no API prefix, for load balancers)
    app.include_router(health.router)

    # API routers under API prefix
    app.include_router(
        collections.router, prefix=settings.api_prefix, tags=["collections"]
    )
    app.include_router(
        user_collections.router, prefix=settings.api_prefix, tags=["user-collections"]
    )
    app.include_router(artifacts.router, prefix=settings.api_prefix, tags=["artifacts"])
    app.include_router(analytics.router, prefix=settings.api_prefix, tags=["analytics"])
    app.include_router(bundles.router, prefix=settings.api_prefix, tags=["bundles"])
    app.include_router(cache.router, prefix=settings.api_prefix, tags=["cache"])
    app.include_router(config.router, prefix=settings.api_prefix, tags=["config"])
    app.include_router(
        context_entities.router, prefix=settings.api_prefix, tags=["context-entities"]
    )
    app.include_router(
        context_modules.router, prefix=settings.api_prefix, tags=["context-modules"]
    )
    app.include_router(
        context_packing.router, prefix=settings.api_prefix, tags=["context-packs"]
    )
    app.include_router(
        context_sync.router, prefix=settings.api_prefix, tags=["context-sync"]
    )
    app.include_router(
        deployment_profiles.router,
        prefix=settings.api_prefix,
        tags=["deployment-profiles"],
    )
    app.include_router(
        deployments.router, prefix=settings.api_prefix, tags=["deployments"]
    )
    app.include_router(groups.router, prefix=settings.api_prefix, tags=["groups"])
    app.include_router(
        composites.router, prefix=settings.api_prefix, tags=["composites"]
    )
    app.include_router(mcp.router, prefix=settings.api_prefix, tags=["mcp"])
    app.include_router(
        marketplace.router, prefix=settings.api_prefix, tags=["marketplace"]
    )
    app.include_router(
        marketplace_catalog.router,
        prefix=settings.api_prefix,
        tags=["marketplace-catalog"],
    )
    app.include_router(
        marketplace_sources.router,
        prefix=settings.api_prefix,
        tags=["marketplace-sources"],
    )
    app.include_router(match.router, prefix=settings.api_prefix, tags=["match"])
    app.include_router(
        memory_items.router, prefix=settings.api_prefix, tags=["memory-items"]
    )
    app.include_router(merge.router, prefix=settings.api_prefix, tags=["merge"])
    app.include_router(
        project_templates.router, prefix=settings.api_prefix, tags=["project-templates"]
    )
    app.include_router(projects.router, prefix=settings.api_prefix, tags=["projects"])
    app.include_router(ratings.router, prefix=settings.api_prefix, tags=["ratings"])
    app.include_router(
        settings_router.router, prefix=settings.api_prefix, tags=["settings"]
    )
    app.include_router(tags.router, prefix=settings.api_prefix, tags=["tags"])
    app.include_router(versions.router, prefix=settings.api_prefix, tags=["versions"])

    # Root endpoint
    @app.get(
        "/",
        tags=["root"],
        summary="API root",
        description="Returns basic API information and available endpoints",
    )
    async def root() -> dict:
        """Root endpoint with API information.

        Returns:
            Dictionary with API metadata
        """
        return {
            "name": settings.api_title,
            "version": skillmeat_version,
            "environment": settings.env.value,
            "api_prefix": settings.api_prefix,
            "docs_url": "/docs" if settings.is_development else None,
            "health_check": "/health",
        }

    # API version info endpoint
    @app.get(
        f"{settings.api_prefix}/version",
        tags=["root"],
        summary="API version",
        description="Returns detailed version information",
    )
    async def version_info() -> dict:
        """Version information endpoint.

        Returns:
            Dictionary with version details
        """
        return {
            "version": skillmeat_version,
            "api_version": settings.api_version,
            "environment": settings.env.value,
        }

    logger.info(
        f"FastAPI application created: {settings.api_title} v{skillmeat_version}"
    )
    return app


# Create default app instance
app = create_app()


def main(
    host: str = "127.0.0.1",
    port: int = 8080,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Run the FastAPI server using Uvicorn.

    This is the main entry point for running the server directly.
    For production, use a process manager like systemd or supervisord.

    Args:
        host: Host address to bind
        port: Port number to bind
        reload: Enable auto-reload on code changes
        log_level: Logging level for Uvicorn
    """
    import uvicorn

    settings = get_settings()

    # Override with function parameters
    host = host or settings.host
    port = port or settings.port
    reload = reload or settings.reload
    log_level = log_level or settings.log_level.lower()

    logger.info(f"Starting Uvicorn server on {host}:{port}")

    uvicorn.run(
        "skillmeat.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=settings.is_development,
    )


if __name__ == "__main__":
    # Allow running directly with: python -m skillmeat.api.server
    main()
