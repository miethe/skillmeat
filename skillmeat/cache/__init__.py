"""Persistent cache module for SkillMeat project and artifact metadata.

This module provides a SQLite-based cache for storing project and artifact
metadata to avoid expensive filesystem scans on every operation. The cache
enables <100ms load times for the web UI and faster CLI operations.

Cache Architecture:
    - SQLite database at ~/.skillmeat/cache.db
    - WAL mode for concurrent access
    - TTL-based refresh strategy
    - Support for local and marketplace artifacts
    - FileWatcher for automatic cache invalidation
    - RefreshJob for background cache refresh

Main Components:
    - schema: Database schema definition and initialization
    - models: SQLAlchemy ORM models
    - repository: Data access layer
    - manager: Service layer for cache operations
    - watcher: File system monitoring for cache invalidation
    - refresh: Background refresh job with scheduling

Example:
    >>> from skillmeat.cache.schema import init_database
    >>> init_database()  # Creates database with schema
    >>>
    >>> # Start file watcher for automatic invalidation
    >>> from skillmeat.cache.repository import CacheRepository
    >>> from skillmeat.cache.watcher import FileWatcher
    >>> repo = CacheRepository()
    >>> watcher = FileWatcher(cache_repository=repo)
    >>> watcher.start()
    >>>
    >>> # Start background refresh job
    >>> from skillmeat.cache.manager import CacheManager
    >>> from skillmeat.cache.refresh import RefreshJob
    >>> manager = CacheManager()
    >>> job = RefreshJob(cache_manager=manager, interval_hours=6.0)
    >>> job.start_scheduler()
"""

__version__ = "0.1.0"

from skillmeat.cache.collection_cache import (
    CollectionCountCache,
    get_collection_count_cache,
)
from skillmeat.cache.manager import CacheManager
from skillmeat.cache.marketplace import MarketplaceCache
from skillmeat.cache.refresh import (
    RefreshEvent,
    RefreshEventType,
    RefreshJob,
    RefreshResult,
)
from skillmeat.cache.repositories import (
    ImportContext,
    MarketplaceCatalogRepository,
    MarketplaceSourceRepository,
    MarketplaceTransactionHandler,
    ScanUpdateContext,
)
from skillmeat.cache.repository import CacheRepository
from skillmeat.cache.watcher import FileWatcher

__all__ = [
    "CacheManager",
    "CacheRepository",
    "CollectionCountCache",
    "FileWatcher",
    "MarketplaceCache",
    "RefreshJob",
    "RefreshEvent",
    "RefreshEventType",
    "RefreshResult",
    "MarketplaceSourceRepository",
    "MarketplaceCatalogRepository",
    "MarketplaceTransactionHandler",
    "ScanUpdateContext",
    "ImportContext",
    "get_collection_count_cache",
]
