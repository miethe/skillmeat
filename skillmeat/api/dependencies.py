"""FastAPI dependency injection providers.

This module provides dependency injection functions for FastAPI routes,
managing the lifecycle of shared resources like collection managers,
database connections, and configuration.
"""

import logging
from typing import Annotated, Any, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import ArtifactManager
from skillmeat.core.auth import TokenManager
from skillmeat.core.collection import CollectionManager
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
        self.token_manager = TokenManager()
        self.sync_manager = SyncManager(
            collection_manager=self.collection_manager,
            artifact_manager=self.artifact_manager,
        )

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
        logger.info("Application state shutdown complete")


# Global application state (initialized in lifespan)
app_state = AppState()


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
