"""FastAPI server application for SkillMeat.

This module provides the main FastAPI application with lifespan management,
middleware configuration, and route registration. It serves as the entry point
for the web service layer.
"""

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
from .routers import analytics, artifacts, bundles, collections, health

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

    # Configure logging
    settings.configure_logging()
    logger.info("Logging configured")

    # Initialize application state
    app_state.initialize(settings)
    logger.info("Application state initialized")

    # Set service start time for health checks
    from .routers.health import set_service_start_time

    set_service_start_time()

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
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body if hasattr(exc, "body") else None,
            },
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

    # Include routers
    # Health check router (no API prefix, for load balancers)
    app.include_router(health.router)

    # API routers under API prefix
    app.include_router(collections.router, prefix=settings.api_prefix, tags=["collections"])
    app.include_router(artifacts.router, prefix=settings.api_prefix, tags=["artifacts"])
    app.include_router(analytics.router, prefix=settings.api_prefix, tags=["analytics"])
    app.include_router(bundles.router, prefix=settings.api_prefix, tags=["bundles"])

    # Future routers will be added here:
    # app.include_router(deployments.router, prefix=settings.api_prefix)
    # app.include_router(marketplace.router, prefix=settings.api_prefix)

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
    port: int = 8000,
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
