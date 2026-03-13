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

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from skillmeat import __version__ as skillmeat_version

from .config import APISettings, get_settings
from .dependencies import app_state, require_auth, set_auth_provider
from .openapi import generate_openapi_spec
from .middleware.tenant_context import set_tenant_context_dep
from .routers import (
    analytics,
    artifact_activity,
    artifact_history,
    artifacts,
    bom as bom_router,
    bundles,
    enterprise_content,
    cache,
    colors,
    composites,
    config,
    context_entities,
    context_modules,
    context_packing,
    context_sync,
    deployment_profiles,
    deployment_sets,
    deployments,
    groups,
    health,
    icon_packs,
    idp_integration,
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
    workflow_executions,
    workflows,
)
from .middleware import ObservabilityMiddleware, RateLimitMiddleware
from .middleware.filesystem_error_handler import FilesystemErrorMiddleware

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

    # Load settings early for validation
    settings = get_settings()

    # Validate edition/database configuration compatibility BEFORE
    # initializing the session factory, which would fail cryptically
    # if enterprise mode is set without a PostgreSQL database URL.
    import os

    database_url = os.environ.get("DATABASE_URL") or os.environ.get(
        "SKILLMEAT_DATABASE_URL"
    )
    if settings.edition == "enterprise":
        if not database_url or not (
            database_url.startswith("postgresql://")
            or database_url.startswith("postgresql+psycopg2://")
        ):
            raise RuntimeError(
                "Edition mismatch: SKILLMEAT_EDITION='enterprise' requires a PostgreSQL database. "
                "Set DATABASE_URL or SKILLMEAT_DATABASE_URL to a postgresql:// URL, "
                "or set SKILLMEAT_EDITION='local' for SQLite mode."
            )
        logger.info("Edition: enterprise (PostgreSQL)")
    else:
        logger.info("Edition: local (SQLite)")

    # Initialize session factory singleton before AppState to prevent
    # concurrent imports from each creating their own sessionmaker instance
    from skillmeat.cache.models import init_session_factory

    init_session_factory()
    logger.info("Database session factory initialized")

    logger.info(f"Environment: {settings.env.value}")
    logger.info(f"API Version: {settings.api_version}")
    logger.info(f"Host: {settings.host}:{settings.port}")
    logger.info(
        "Authentication: %s",
        (
            f"enabled (provider={settings.auth_provider})"
            if settings.auth_enabled
            else "local auth mode (auth_enabled=false — LocalAuthProvider selected)"
        ),
    )

    # Instantiate and register the authentication provider.
    #
    # Auth Bypass Contract (CP-001):
    #   auth_enabled=false  → LocalAuthProvider is always used, regardless of
    #                         the auth_provider setting.  LocalAuthProvider
    #                         never raises; it returns LOCAL_ADMIN_CONTEXT on
    #                         every request.  This is the single decision point
    #                         for bypass semantics — require_auth() itself has
    #                         no auth_enabled awareness.
    #   auth_enabled=true   → The configured auth_provider is used (e.g. clerk).
    #                         require_auth() validates every request via that
    #                         provider.
    if not settings.auth_enabled:
        from skillmeat.api.auth.local_provider import LocalAuthProvider

        _auth_provider = LocalAuthProvider()
        logger.info(
            "Auth provider: local (auth_enabled=false — all requests granted local-admin context)"
        )
    else:
        _provider_name = settings.auth_provider.lower()
        if _provider_name == "local":
            from skillmeat.api.auth.local_provider import LocalAuthProvider

            _auth_provider = LocalAuthProvider()
        elif _provider_name == "clerk":
            from skillmeat.api.auth.clerk_provider import ClerkAuthProvider

            if not settings.clerk_jwks_url:
                raise RuntimeError(
                    "CLERK_JWKS_URL (or SKILLMEAT_CLERK_JWKS_URL) must be set "
                    "when auth_provider='clerk'."
                )
            _auth_provider = ClerkAuthProvider(
                jwks_url=settings.clerk_jwks_url,
                audience=settings.clerk_audience,
                issuer=settings.clerk_issuer,
            )
        else:
            raise RuntimeError(
                f"Unknown auth_provider '{settings.auth_provider}'. "
                "Valid values are 'local' and 'clerk'."
            )
        logger.info(
            "Auth provider: %s (auth_enabled=true — requests require valid credentials)",
            settings.auth_provider,
        )
    set_auth_provider(_auth_provider)

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
        from skillmeat.api.utils.fts5 import detect_and_cache_backend
        from skillmeat.cache.models import get_session

        edition = settings.edition if settings else "local"

        if edition == "enterprise":
            # Enterprise: bootstrap default collection in PostgreSQL via the
            # same engine/session factory used by request-time DI.
            from skillmeat.cache.models import get_engine
            from skillmeat.cache.enterprise_repositories import (
                EnterpriseCollectionRepository,
            )
            from sqlalchemy.orm import Session as SASession

            ent_engine = get_engine()
            with SASession(ent_engine) as ent_session:
                ent_repo = EnterpriseCollectionRepository(session=ent_session)
                existing = ent_repo.get_by_name("Default Collection")
                if existing is None:
                    ent_repo.create(
                        name="Default Collection",
                        description="Default artifact collection",
                    )
                    ent_session.commit()
                    logger.info(
                        "Default collection created (enterprise)"
                    )
                else:
                    logger.info(
                        "Default collection verified (enterprise)"
                    )
        else:
            from skillmeat.cache.repositories import DbUserCollectionRepository

            session = get_session()
            try:
                ensure_default_collection(DbUserCollectionRepository())
                logger.info("Default collection verified/created")

                # Detect search backend (FTS5 / tsvector / LIKE) at startup
                detected = detect_and_cache_backend(session)
                logger.info("Search backend: %s", detected.value)

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

    # Seed built-in entity type configurations (idempotent)
    try:
        from skillmeat.cache.models import get_session
        from skillmeat.cache.seed_entity_types import seed_builtin_entity_types

        seed_session = get_session()
        try:
            inserted = seed_builtin_entity_types(seed_session)
            seed_session.commit()
            if inserted:
                logger.info(
                    f"Entity type seeding: {inserted} built-in type(s) inserted"
                )
            else:
                logger.debug("Entity type seeding: all built-in types already present")
        except Exception:
            seed_session.rollback()
            raise
        finally:
            seed_session.close()
    except Exception as e:
        logger.warning(f"Could not seed built-in entity type configs: {e}")

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

    app.add_middleware(FilesystemErrorMiddleware)
    logger.info("FilesystemError middleware enabled")

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

    # Blanket auth dependency applied to every protected router.
    # Excluded: health (load-balancer probes), cache (internal ops),
    # settings (read-only app config) — these remain publicly accessible.
    #
    # ENT2-004: Validated — tenant context lifecycle is correct:
    # 1. ORDERING: set_tenant_context_dep declares `Depends(require_auth())` in
    #    its own signature, so FastAPI resolves require_auth() first and passes the
    #    AuthContext into set_tenant_context_dep.  The outer Depends(require_auth())
    #    in this list is deduplicated by FastAPI's dependency cache, so both
    #    references share the same AuthContext for the request.
    # 2. SESSION: get_db_session() (session.py) calls SessionLocal() each request,
    #    yields a fresh Session, and closes it in a finally block — strictly
    #    request-scoped.  Enterprise repos receive this injected Session and never
    #    create their own.
    # 3. CONTEXVAR LEAKAGE: set_tenant_context_dep is an async generator dependency.
    #    It calls TenantContext.set() before yield and TenantContext.reset(token) in
    #    a finally block, guaranteeing the ContextVar is cleared even on exceptions
    #    and preventing tenant identity from leaking across reused async tasks.
    # 4. AUTH → TENANT PROPAGATION: set_tenant_context_dep reads AuthContext.tenant_id
    #    and is a no-op when tenant_id is None (local/single-tenant mode), falling
    #    back to DEFAULT_TENANT_ID inside the enterprise repository base class.
    _auth_deps = [Depends(require_auth()), Depends(set_tenant_context_dep)]

    # Include routers
    # Health check router (no API prefix, for load balancers) — public
    app.include_router(health.router)

    # API routers under API prefix
    app.include_router(
        user_collections.router,
        prefix=settings.api_prefix,
        tags=["user-collections"],
        dependencies=_auth_deps,
    )
    app.include_router(
        artifacts.router,
        prefix=settings.api_prefix,
        tags=["artifacts"],
        dependencies=_auth_deps,
    )
    app.include_router(
        artifact_history.router,
        prefix=settings.api_prefix,
        tags=["artifacts"],
        dependencies=_auth_deps,
    )
    app.include_router(
        artifact_activity.router,
        prefix=settings.api_prefix,
        tags=["artifact-activity"],
        dependencies=_auth_deps,
    )
    app.include_router(
        bom_router.router,
        prefix=settings.api_prefix,
        tags=["bom"],
        dependencies=_auth_deps,
    )
    app.include_router(
        enterprise_content.router,
        prefix=settings.api_prefix,
        tags=["enterprise"],
        dependencies=_auth_deps,
    )
    app.include_router(
        analytics.router,
        prefix=settings.api_prefix,
        tags=["analytics"],
        dependencies=_auth_deps,
    )
    app.include_router(
        bundles.router,
        prefix=settings.api_prefix,
        tags=["bundles"],
        dependencies=_auth_deps,
    )
    # cache router — public (internal cache management operations)
    app.include_router(cache.router, prefix=settings.api_prefix, tags=["cache"])
    app.include_router(
        config.router,
        prefix=settings.api_prefix,
        tags=["config"],
        dependencies=_auth_deps,
    )
    app.include_router(
        context_entities.router,
        prefix=settings.api_prefix,
        tags=["context-entities"],
        dependencies=_auth_deps,
    )
    app.include_router(
        context_modules.router,
        prefix=settings.api_prefix,
        tags=["context-modules"],
        dependencies=_auth_deps,
    )
    app.include_router(
        context_packing.router,
        prefix=settings.api_prefix,
        tags=["context-packs"],
        dependencies=_auth_deps,
    )
    app.include_router(
        context_sync.router,
        prefix=settings.api_prefix,
        tags=["context-sync"],
        dependencies=_auth_deps,
    )
    app.include_router(
        deployment_profiles.router,
        prefix=settings.api_prefix,
        tags=["deployment-profiles"],
        dependencies=_auth_deps,
    )
    app.include_router(
        deployment_sets.router,
        prefix=settings.api_prefix,
        tags=["deployment-sets"],
        dependencies=_auth_deps,
    )
    app.include_router(
        deployments.router,
        prefix=settings.api_prefix,
        tags=["deployments"],
        dependencies=_auth_deps,
    )
    app.include_router(
        groups.router,
        prefix=settings.api_prefix,
        tags=["groups"],
        dependencies=_auth_deps,
    )
    app.include_router(
        composites.router,
        prefix=settings.api_prefix,
        tags=["composites"],
        dependencies=_auth_deps,
    )
    app.include_router(
        mcp.router,
        prefix=settings.api_prefix,
        tags=["mcp"],
        dependencies=_auth_deps,
    )
    app.include_router(
        marketplace.router,
        prefix=settings.api_prefix,
        tags=["marketplace"],
        dependencies=_auth_deps,
    )
    app.include_router(
        marketplace_catalog.router,
        prefix=settings.api_prefix,
        tags=["marketplace-catalog"],
        dependencies=_auth_deps,
    )
    app.include_router(
        marketplace_sources.router,
        prefix=settings.api_prefix,
        tags=["marketplace-sources"],
        dependencies=_auth_deps,
    )
    app.include_router(
        match.router,
        prefix=settings.api_prefix,
        tags=["match"],
        dependencies=_auth_deps,
    )
    app.include_router(
        memory_items.router,
        prefix=settings.api_prefix,
        tags=["memory-items"],
        dependencies=_auth_deps,
    )
    app.include_router(
        merge.router,
        prefix=settings.api_prefix,
        tags=["merge"],
        dependencies=_auth_deps,
    )
    app.include_router(
        project_templates.router,
        prefix=settings.api_prefix,
        tags=["project-templates"],
        dependencies=_auth_deps,
    )
    app.include_router(
        idp_integration.router,
        prefix=settings.api_prefix,
        tags=["integrations-idp"],
        dependencies=_auth_deps,
    )
    app.include_router(
        projects.router,
        prefix=settings.api_prefix,
        tags=["projects"],
        dependencies=_auth_deps,
    )
    app.include_router(
        ratings.router,
        prefix=settings.api_prefix,
        tags=["ratings"],
        dependencies=_auth_deps,
    )
    # settings router — public (read-only app configuration info)
    app.include_router(
        settings_router.router, prefix=settings.api_prefix, tags=["settings"]
    )
    app.include_router(
        colors.router,
        prefix=settings.api_prefix,
        tags=["colors"],
        dependencies=_auth_deps,
    )
    app.include_router(
        icon_packs.router,
        prefix=settings.api_prefix,
        tags=["settings"],
        dependencies=_auth_deps,
    )
    app.include_router(
        tags.router,
        prefix=settings.api_prefix,
        tags=["tags"],
        dependencies=_auth_deps,
    )
    app.include_router(
        versions.router,
        prefix=settings.api_prefix,
        tags=["versions"],
        dependencies=_auth_deps,
    )
    app.include_router(
        workflows.router,
        prefix=settings.api_prefix,
        tags=["workflows"],
        dependencies=_auth_deps,
    )
    app.include_router(
        workflow_executions.router,
        prefix=settings.api_prefix,
        tags=["workflow-executions"],
        dependencies=_auth_deps,
    )

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

    # Wire the custom OpenAPI generator so /docs and app.openapi() include
    # BearerAuth scheme, scope/role documentation, and per-operation security.
    def _custom_openapi():
        return generate_openapi_spec(app, api_version=settings.api_version)

    app.openapi = _custom_openapi

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
