"""FastAPI dependency injection providers.

This module provides dependency injection functions for FastAPI routes,
managing the lifecycle of shared resources like collection managers,
database connections, and configuration.
"""

import logging
from collections.abc import Callable, Coroutine
from typing import Annotated, Any, Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from skillmeat.api.auth.provider import AuthProvider
from skillmeat.api.schemas.auth import AuthContext
from skillmeat.config import ConfigManager
from skillmeat.core.artifact import ArtifactManager
from skillmeat.core.auth import TokenManager
from skillmeat.core.collection import CollectionManager
from skillmeat.core.interfaces.repositories import (
    IArtifactRepository,
    ICollectionRepository,
    IContextEntityRepository,
    IDbArtifactHistoryRepository,
    IDbCollectionArtifactRepository,
    IDbUserCollectionRepository,
    IDeploymentRepository,
    IGroupRepository,
    IMarketplaceSourceRepository,
    IProjectRepository,
    IProjectTemplateRepository,
    ISettingsRepository,
    ITagRepository,
)
from skillmeat.cache.repositories import (
    DbArtifactHistoryRepository,
    DbCollectionArtifactRepository,
    DbUserCollectionRepository,
    DeploymentProfileRepository,
    DeploymentSetRepository,
    DuplicatePairRepository,
    MarketplaceCatalogRepository,
    MarketplaceSourceRepository,
    MarketplaceTransactionHandler,
)
from skillmeat.cache.session import get_db_session
from skillmeat.core.path_resolver import ProjectPathResolver
from skillmeat.core.services.context_sync import ContextSyncService
from skillmeat.core.sync import SyncManager

from .config import APISettings, get_settings

logger = logging.getLogger(__name__)

# API Key security scheme (optional authentication)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# Application state container
class AppState:
    """Application state container for shared resources.

    This class holds singleton instances of managers and configuration
    that are shared across all requests.
    """

    def __init__(self):
        """Initialize application state."""
        self.config_manager: Optional[ConfigManager] = None
        self.collection_manager: Optional[CollectionManager] = None
        self.artifact_manager: Optional[ArtifactManager] = None
        self.token_manager: Optional[TokenManager] = None
        self.sync_manager: Optional[SyncManager] = None
        self.context_sync_service: Optional[ContextSyncService] = None
        self.settings: Optional[APISettings] = None
        self.metadata_cache: Optional[Any] = None  # MetadataCache, lazily initialized
        self.cache_manager: Optional[Any] = None  # CacheManager, lazily initialized
        self.refresh_job: Optional[Any] = None  # RefreshJob, lazily initialized
        self.path_resolver: Optional[ProjectPathResolver] = None

    def initialize(self, settings: APISettings) -> None:
        """Initialize all managers with settings.

        Args:
            settings: API settings instance
        """
        logger.info("Initializing application state...")
        self.settings = settings

        # Initialize SkillMeat core managers
        self.config_manager = ConfigManager()
        self.collection_manager = CollectionManager(config=self.config_manager)
        self.artifact_manager = ArtifactManager(collection_mgr=self.collection_manager)
        self.token_manager = TokenManager() if settings.auth_enabled else None
        self.sync_manager = SyncManager(
            collection_manager=self.collection_manager,
            artifact_manager=self.artifact_manager,
        )
        self.path_resolver = ProjectPathResolver()

        # Initialize cache manager if not already initialized (lazy init pattern)
        if self.cache_manager is None:
            try:
                from skillmeat.cache.manager import CacheManager as CacheManagerImpl

                self.cache_manager = CacheManagerImpl()
                logger.info("CacheManager initialized")
            except Exception as e:
                logger.warning(f"CacheManager initialization failed: {e}")
                self.cache_manager = None

        # Initialize context sync service
        if self.cache_manager is not None:
            self.context_sync_service = ContextSyncService(
                collection_mgr=self.collection_manager,
                cache_mgr=self.cache_manager,
            )
            logger.info("ContextSyncService initialized")
        else:
            logger.warning(
                "ContextSyncService not initialized (CacheManager unavailable)"
            )
            self.context_sync_service = None

        logger.info("Application state initialized successfully")

    def shutdown(self) -> None:
        """Clean up resources on shutdown."""
        logger.info("Shutting down application state...")
        # Add cleanup logic here if needed (close DB connections, etc.)

        # Stop refresh job scheduler if running
        if self.refresh_job is not None:
            try:
                self.refresh_job.stop_scheduler(wait=True)
            except Exception as e:
                logger.warning(f"Error stopping refresh job: {e}")

        self.config_manager = None
        self.collection_manager = None
        self.artifact_manager = None
        self.token_manager = None
        self.sync_manager = None
        self.context_sync_service = None
        self.metadata_cache = None
        self.cache_manager = None
        self.refresh_job = None
        self.path_resolver = None
        logger.info("Application state shutdown complete")


# Global application state (initialized in lifespan)
app_state = AppState()

# ---------------------------------------------------------------------------
# Auth provider singleton
# ---------------------------------------------------------------------------

#: Module-level auth provider instance.  Set during app startup via
#: ``set_auth_provider()``.  ``None`` until explicitly configured.
_auth_provider: Optional[AuthProvider] = None


def set_auth_provider(provider: AuthProvider) -> None:
    """Register the application-wide authentication provider.

    Call this once during startup (e.g. inside the lifespan function) before
    any requests are handled.

    Args:
        provider: A concrete ``AuthProvider`` implementation.
    """
    global _auth_provider
    _auth_provider = provider


def get_auth_provider() -> AuthProvider:
    """Return the configured authentication provider.

    Returns:
        The registered ``AuthProvider`` instance.

    Raises:
        HTTPException: 503 if no provider has been registered yet.
    """
    if _auth_provider is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider not configured",
        )
    return _auth_provider


# ---------------------------------------------------------------------------
# require_auth dependency
# ---------------------------------------------------------------------------


def require_auth(
    scopes: list[str] | None = None,
) -> Callable[..., Coroutine[Any, Any, AuthContext]]:
    """FastAPI dependency factory that validates authentication and optional scopes.

    # Auth Bypass Contract (CP-001)
    # -----------------------------------------------------------------------
    # auth_enabled=false → server.py lifespan registers LocalAuthProvider.
    #                      LocalAuthProvider.validate() always returns
    #                      LOCAL_ADMIN_CONTEXT (user_id="local", role=system_admin,
    #                      all scopes).  No credentials are inspected; auth
    #                      always succeeds.
    # auth_enabled=true  → lifespan registers the configured provider (e.g.
    #                      ClerkAuthProvider).  Every request is validated
    #                      against real credentials.
    # This function has NO awareness of auth_enabled.  The provider selection
    # at startup is the single enforcement decision point.
    # -----------------------------------------------------------------------

    Supports two usage patterns::

        # No scope check — just authenticate
        @router.get("/items")
        async def list_items(auth: AuthContext = Depends(require_auth)):
            ...

        # With scope check — 403 if any required scope is missing
        @router.post("/items")
        async def create_item(auth: AuthContext = Depends(require_auth(scopes=["artifact:write"]))):
            ...

    When used directly as ``Depends(require_auth)`` FastAPI calls ``require_auth``
    with no arguments (its default signature), which returns an inner coroutine
    that FastAPI then calls with the ``Request``.  When used as
    ``Depends(require_auth(scopes=[...]))`` the outer call returns the same inner
    coroutine type, so both forms are structurally identical to FastAPI.

    Args:
        scopes: Optional list of scope strings (e.g. ``["artifact:read"]``) that
            the authenticated context must carry.  Uses ``AuthContext.has_scope``
            which honours the ``admin:*`` wildcard automatically.

    Returns:
        An async dependency coroutine that resolves to the authenticated
        ``AuthContext``.

    Raises:
        HTTPException 401: Propagated from the provider when credentials are
            absent or invalid.
        HTTPException 403: When one or more required scopes are missing.
        HTTPException 503: When no auth provider has been registered.
    """

    async def _dependency(request: Request) -> AuthContext:
        provider = get_auth_provider()
        auth_context = await provider.validate(request)

        # Expose auth context on request state so middleware and downstream
        # handlers can access it without repeating the provider lookup.
        request.state.auth_context = auth_context

        if scopes:
            missing = [s for s in scopes if not auth_context.has_scope(s)]
            if missing:
                logger.warning(
                    "Auth scope check failed: user=%s missing=%s",
                    auth_context.user_id,
                    missing,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scopes: {missing}",
                )

        return auth_context

    return _dependency


#: Pre-built ``Annotated`` alias for routes that only need authentication
#: without explicit scope enforcement.
AuthContextDep = Annotated[AuthContext, Depends(require_auth())]


async def get_auth_context(request: Request) -> AuthContext:
    """Read AuthContext from request.state (set by router-level require_auth).

    This lightweight dependency avoids a second provider round-trip for
    handlers that are already protected by a router-level ``require_auth``
    dependency (registered via ``dependencies=_auth_deps`` in server.py).
    It simply reads the ``auth_context`` attribute that ``require_auth``
    stores on ``request.state`` and returns it.

    Args:
        request: The current FastAPI request.

    Returns:
        The ``AuthContext`` stored by the router-level auth dependency.

    Raises:
        HTTPException 401: If ``request.state`` has no ``auth_context``
            (should not happen when router-level auth is wired correctly).
    """
    auth_ctx = getattr(request.state, "auth_context", None)
    if auth_ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return auth_ctx


def get_app_state() -> AppState:
    """Get application state dependency.

    Returns:
        AppState instance

    Raises:
        HTTPException: If application state not initialized
    """
    if app_state.settings is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not initialized",
        )
    return app_state


def get_config_manager(
    state: Annotated[AppState, Depends(get_app_state)],
) -> ConfigManager:
    """Get ConfigManager dependency.

    Args:
        state: Application state

    Returns:
        ConfigManager instance

    Raises:
        HTTPException: If ConfigManager not available
    """
    if state.config_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration manager not available",
        )
    return state.config_manager


def get_collection_manager(
    state: Annotated[AppState, Depends(get_app_state)],
) -> CollectionManager:
    """Get CollectionManager dependency.

    Args:
        state: Application state

    Returns:
        CollectionManager instance

    Raises:
        HTTPException: If CollectionManager not available
    """
    if state.collection_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Collection manager not available",
        )
    return state.collection_manager


def get_artifact_manager(
    state: Annotated[AppState, Depends(get_app_state)],
) -> ArtifactManager:
    """Get ArtifactManager dependency.

    Args:
        state: Application state

    Returns:
        ArtifactManager instance

    Raises:
        HTTPException: If ArtifactManager not available
    """
    if state.artifact_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Artifact manager not available",
        )
    return state.artifact_manager


def get_token_manager(
    state: Annotated[AppState, Depends(get_app_state)],
) -> TokenManager:
    """Get TokenManager dependency.

    Args:
        state: Application state

    Returns:
        TokenManager instance

    Raises:
        HTTPException: If TokenManager not available
    """
    if state.token_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token manager not available",
        )
    return state.token_manager


def get_sync_manager(
    state: Annotated[AppState, Depends(get_app_state)],
) -> SyncManager:
    """Get SyncManager dependency.

    Args:
        state: Application state

    Returns:
        SyncManager instance

    Raises:
        HTTPException: If SyncManager not available
    """
    if state.sync_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sync manager not available",
        )
    return state.sync_manager


def get_context_sync_service(
    state: Annotated[AppState, Depends(get_app_state)],
) -> ContextSyncService:
    """Get ContextSyncService dependency.

    Args:
        state: Application state

    Returns:
        ContextSyncService instance

    Raises:
        HTTPException: If ContextSyncService not available
    """
    if state.context_sync_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Context sync service not available",
        )
    return state.context_sync_service


def verify_api_key(
    api_key: Annotated[Optional[str], Security(api_key_header)],
    settings: Annotated[APISettings, Depends(get_settings)],
) -> None:
    """Verify API key if authentication is enabled.

    Args:
        api_key: API key from request header
        settings: API settings

    Raises:
        HTTPException: If API key is invalid or missing when required
    """
    # Skip authentication if disabled
    if not settings.api_key_enabled:
        return

    # Check if API key is provided
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )


def require_memory_context_enabled(
    settings: Annotated[APISettings, Depends(get_settings)],
) -> None:
    """Legacy no-op dependency retained for backward compatibility."""
    _ = settings
    return


# ---------------------------------------------------------------------------
# Repository factory providers (hexagonal architecture)
#
# Enterprise Edition Provider Support (ENT2-002/003)
# Supported:   artifact, collection
# Unsupported: project, deployment, tag, settings, group, context_entity,
#              marketplace_source, project_template
# ---------------------------------------------------------------------------


def get_artifact_repository(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[Session, Depends(get_db_session)],
) -> IArtifactRepository:
    """Get IArtifactRepository dependency.

    Args:
        state: Application state
        session: Per-request SQLAlchemy session (used by enterprise edition)

    Returns:
        IArtifactRepository implementation for the configured edition.
        Local edition returns ``LocalArtifactRepository``; enterprise edition
        returns ``EnterpriseArtifactRepository`` (wired directly — no adapter).

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalArtifactRepository

        return LocalArtifactRepository(  # type: ignore[return-value]
            artifact_manager=state.artifact_manager,
            path_resolver=state.path_resolver,
        )
    if edition == "enterprise":
        from skillmeat.cache.enterprise_repositories import (
            EnterpriseArtifactRepository,
        )

        return EnterpriseArtifactRepository(session=session)  # type: ignore[return-value]
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Unsupported edition: {edition}",
    )


def get_project_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IProjectRepository:
    """Get IProjectRepository dependency.

    Args:
        state: Application state

    Returns:
        IProjectRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalProjectRepository

        return LocalProjectRepository(
            path_resolver=state.path_resolver,
            cache_manager=state.cache_manager,
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support project. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_collection_repository(
    state: Annotated[AppState, Depends(get_app_state)],
    session: Annotated[Session, Depends(get_db_session)],
) -> ICollectionRepository:
    """Get ICollectionRepository dependency.

    Args:
        state: Application state
        session: Per-request SQLAlchemy session (used by enterprise edition)

    Returns:
        ICollectionRepository implementation for the configured edition.
        Local edition returns ``LocalCollectionRepository``; enterprise edition
        returns ``EnterpriseCollectionRepository`` (wired directly — no adapter).

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalCollectionRepository

        return LocalCollectionRepository(  # type: ignore[return-value]
            collection_manager=state.collection_manager,
            path_resolver=state.path_resolver,
        )
    if edition == "enterprise":
        from skillmeat.cache.enterprise_repositories import (
            EnterpriseCollectionRepository,
        )

        return EnterpriseCollectionRepository(session=session)  # type: ignore[return-value]
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Unsupported edition: {edition}",
    )


def get_deployment_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IDeploymentRepository:
    """Get IDeploymentRepository dependency.

    Args:
        state: Application state

    Returns:
        IDeploymentRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.deployment import DeploymentManager
        from skillmeat.core.repositories import LocalDeploymentRepository

        deployment_manager = DeploymentManager(collection_mgr=state.collection_manager)
        return LocalDeploymentRepository(
            deployment_manager=deployment_manager,
            path_resolver=state.path_resolver,
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support deployment. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_tag_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> ITagRepository:
    """Get ITagRepository dependency.

    Args:
        state: Application state

    Returns:
        ITagRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalTagRepository

        return LocalTagRepository()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support tag. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_settings_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> ISettingsRepository:
    """Get ISettingsRepository dependency.

    Args:
        state: Application state

    Returns:
        ISettingsRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalSettingsRepository

        return LocalSettingsRepository(
            path_resolver=state.path_resolver,
            config_manager=state.config_manager,
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support settings. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_group_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IGroupRepository:
    """Get IGroupRepository dependency.

    Args:
        state: Application state

    Returns:
        IGroupRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalGroupRepository

        return LocalGroupRepository()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support group. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_context_entity_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IContextEntityRepository:
    """Get IContextEntityRepository dependency.

    Args:
        state: Application state

    Returns:
        IContextEntityRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalContextEntityRepository

        return LocalContextEntityRepository()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support context_entity. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_marketplace_source_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IMarketplaceSourceRepository:
    """Get IMarketplaceSourceRepository dependency.

    Args:
        state: Application state

    Returns:
        IMarketplaceSourceRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalMarketplaceSourceRepository

        return LocalMarketplaceSourceRepository()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support marketplace_source. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_project_template_repository(
    state: Annotated[AppState, Depends(get_app_state)],
) -> IProjectTemplateRepository:
    """Get IProjectTemplateRepository dependency.

    Args:
        state: Application state

    Returns:
        IProjectTemplateRepository implementation for the configured edition

    Raises:
        HTTPException: If the configured edition is not supported
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "local":
        from skillmeat.core.repositories import LocalProjectTemplateRepository

        return LocalProjectTemplateRepository()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Enterprise edition does not yet support project_template. "
            f"Supported providers: artifact, collection."
        ),
    )


def get_deployment_set_repository() -> DeploymentSetRepository:
    """Get DeploymentSetRepository dependency.

    Returns a new ``DeploymentSetRepository`` instance.  The repository
    manages its own session lifecycle internally, so no state injection is
    required.

    Returns:
        DeploymentSetRepository instance.
    """
    return DeploymentSetRepository()


def get_deployment_profile_repository() -> DeploymentProfileRepository:
    """Get DeploymentProfileRepository dependency.

    Returns a new ``DeploymentProfileRepository`` instance.  The repository
    manages its own session lifecycle internally, so no state injection is
    required.

    Returns:
        DeploymentProfileRepository instance.
    """
    return DeploymentProfileRepository()


def get_marketplace_source_repository_concrete() -> MarketplaceSourceRepository:
    """Get concrete MarketplaceSourceRepository dependency.

    Returns the concrete ``MarketplaceSourceRepository`` instance when the full
    set of repository methods (beyond the ``IMarketplaceSourceRepository``
    interface) is required — e.g. in the marketplace-sources router which uses
    ORM-level helpers not exposed by the interface.

    Returns:
        MarketplaceSourceRepository instance.
    """
    return MarketplaceSourceRepository()


def get_marketplace_catalog_repository() -> MarketplaceCatalogRepository:
    """Get MarketplaceCatalogRepository dependency.

    Returns a new ``MarketplaceCatalogRepository`` instance.  The repository
    manages its own session lifecycle internally.

    Returns:
        MarketplaceCatalogRepository instance.
    """
    return MarketplaceCatalogRepository()


def get_marketplace_transaction_handler() -> MarketplaceTransactionHandler:
    """Get MarketplaceTransactionHandler dependency.

    Returns a new ``MarketplaceTransactionHandler`` instance for coordinating
    atomic cross-table marketplace operations.

    Returns:
        MarketplaceTransactionHandler instance.
    """
    return MarketplaceTransactionHandler()


def get_db_user_collection_repository(
    state: Annotated["AppState", Depends(get_app_state)],
    session: Annotated[Session, Depends(get_db_session)],
) -> IDbUserCollectionRepository:
    """Get an edition-aware IDbUserCollectionRepository dependency.

    In local mode returns a ``DbUserCollectionRepository`` backed by the
    SQLite cache (manages its own session).  In enterprise mode returns an
    ``EnterpriseUserCollectionAdapter`` that wraps the PostgreSQL-backed
    ``EnterpriseCollectionRepository`` and receives the per-request
    ``Session`` from the FastAPI DI layer.

    Args:
        state: Application state (used to read the configured edition).
        session: Per-request SQLAlchemy session (used by the enterprise path).

    Returns:
        IDbUserCollectionRepository implementation appropriate for the
        configured edition.
    """
    edition = state.settings.edition if state.settings else "local"
    if edition == "enterprise":
        from skillmeat.cache.enterprise_repositories import (
            EnterpriseUserCollectionAdapter,
        )

        return EnterpriseUserCollectionAdapter(session=session)
    return DbUserCollectionRepository()


def get_db_collection_artifact_repository() -> IDbCollectionArtifactRepository:
    """Get DbCollectionArtifactRepository dependency.

    Returns a new ``DbCollectionArtifactRepository`` instance.  The repository
    manages its own session lifecycle internally, so no state injection is
    required.

    Returns:
        IDbCollectionArtifactRepository implementation backed by the SQLite cache.
    """
    return DbCollectionArtifactRepository()


def get_duplicate_pair_repository() -> DuplicatePairRepository:
    """Get DuplicatePairRepository dependency.

    Returns a new ``DuplicatePairRepository`` instance.  The repository
    manages its own session lifecycle internally.

    Returns:
        DuplicatePairRepository instance.
    """
    return DuplicatePairRepository()


# Type aliases for cleaner dependency injection
ConfigManagerDep = Annotated[ConfigManager, Depends(get_config_manager)]
CollectionManagerDep = Annotated[CollectionManager, Depends(get_collection_manager)]
ArtifactManagerDep = Annotated[ArtifactManager, Depends(get_artifact_manager)]
TokenManagerDep = Annotated[TokenManager, Depends(get_token_manager)]
SyncManagerDep = Annotated[SyncManager, Depends(get_sync_manager)]
ContextSyncServiceDep = Annotated[ContextSyncService, Depends(get_context_sync_service)]
SettingsDep = Annotated[APISettings, Depends(get_settings)]
APIKeyDep = Annotated[None, Depends(verify_api_key)]
MemoryContextEnabledDep = Annotated[None, Depends(require_memory_context_enabled)]

# Repository DI aliases (hexagonal architecture)
ArtifactRepoDep = Annotated[IArtifactRepository, Depends(get_artifact_repository)]
ProjectRepoDep = Annotated[IProjectRepository, Depends(get_project_repository)]
CollectionRepoDep = Annotated[ICollectionRepository, Depends(get_collection_repository)]
DeploymentRepoDep = Annotated[IDeploymentRepository, Depends(get_deployment_repository)]
TagRepoDep = Annotated[ITagRepository, Depends(get_tag_repository)]
SettingsRepoDep = Annotated[ISettingsRepository, Depends(get_settings_repository)]
GroupRepoDep = Annotated[IGroupRepository, Depends(get_group_repository)]
ContextEntityRepoDep = Annotated[
    IContextEntityRepository, Depends(get_context_entity_repository)
]
MarketplaceSourceRepoDep = Annotated[
    IMarketplaceSourceRepository, Depends(get_marketplace_source_repository)
]
ProjectTemplateRepoDep = Annotated[
    IProjectTemplateRepository, Depends(get_project_template_repository)
]
DeploymentSetRepoDep = Annotated[
    DeploymentSetRepository, Depends(get_deployment_set_repository)
]
DeploymentProfileRepoDep = Annotated[
    DeploymentProfileRepository, Depends(get_deployment_profile_repository)
]
MarketplaceCatalogRepoDep = Annotated[
    MarketplaceCatalogRepository, Depends(get_marketplace_catalog_repository)
]
DuplicatePairRepoDep = Annotated[
    DuplicatePairRepository, Depends(get_duplicate_pair_repository)
]
# Concrete MarketplaceSourceRepository (vs IMarketplaceSourceRepository interface).
# Use this in marketplace_sources router which requires methods beyond the interface.
MarketplaceSourceConcreteRepoDep = Annotated[
    MarketplaceSourceRepository, Depends(get_marketplace_source_repository_concrete)
]
MarketplaceTransactionHandlerDep = Annotated[
    MarketplaceTransactionHandler, Depends(get_marketplace_transaction_handler)
]
DbUserCollectionRepoDep = Annotated[
    IDbUserCollectionRepository, Depends(get_db_user_collection_repository)
]
DbCollectionArtifactRepoDep = Annotated[
    IDbCollectionArtifactRepository, Depends(get_db_collection_artifact_repository)
]


def get_db_artifact_history_repository() -> IDbArtifactHistoryRepository:
    """Get DbArtifactHistoryRepository dependency.

    Returns a new ``DbArtifactHistoryRepository`` instance.  The repository
    manages its own session lifecycle per operation.

    Returns:
        IDbArtifactHistoryRepository implementation backed by the SQLite cache.
    """
    return DbArtifactHistoryRepository()


DbArtifactHistoryRepoDep = Annotated[
    IDbArtifactHistoryRepository, Depends(get_db_artifact_history_repository)
]

# Per-request SQLAlchemy session (hexagonal architecture)
DbSessionDep = Annotated[Session, Depends(get_db_session)]
