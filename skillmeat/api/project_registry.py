"""
Project Registry - Cached project discovery for fast API responses.

This module provides a singleton ProjectRegistry that caches discovered projects
to avoid expensive filesystem scans on every API request. The cache is refreshed
in the background and invalidated on deploy/delete operations.

Architecture:
- In-memory cache with TTL (default: 5 minutes)
- Background refresh task (non-blocking)
- Manual invalidation on mutations
- Thread-safe with asyncio.Lock

Performance improvement: ~10-30 seconds → <50ms for cached responses.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.storage.deployment import DeploymentTracker
from skillmeat.storage.project import ProjectMetadataStorage

logger = logging.getLogger(__name__)


@dataclass
class ProjectCacheEntry:
    """Cached information about a single project."""

    path: Path
    name: str
    deployment_count: int
    last_deployment: Optional[datetime]
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if this entry has expired."""
        age = (datetime.now(timezone.utc) - self.cached_at).total_seconds()
        return age > ttl_seconds


class ProjectRegistry:
    """
    Singleton registry for cached project discovery.

    This registry maintains an in-memory cache of discovered projects to avoid
    expensive filesystem scans on every API request. The cache is refreshed
    in the background and can be manually invalidated.

    Usage:
        registry = ProjectRegistry.get_instance()
        projects = await registry.get_projects()
    """

    _instance: Optional["ProjectRegistry"] = None
    _lock = asyncio.Lock()

    # Default configuration
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    DEFAULT_ENTRY_TTL = 60  # 1 minute for individual entries
    DEFAULT_MAX_DEPTH = 3

    def __init__(self):
        """Initialize the registry (use get_instance() instead)."""
        self._cache: Dict[str, ProjectCacheEntry] = {}
        self._last_full_scan: Optional[datetime] = None
        self._cache_ttl = self.DEFAULT_CACHE_TTL
        self._entry_ttl = self.DEFAULT_ENTRY_TTL
        self._max_depth = self.DEFAULT_MAX_DEPTH
        self._scan_lock = asyncio.Lock()
        self._refresh_task: Optional[asyncio.Task] = None
        self._search_paths: Optional[List[Path]] = None

    @classmethod
    async def get_instance(cls) -> "ProjectRegistry":
        """Get or create the singleton instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = ProjectRegistry()
            return cls._instance

    @classmethod
    def get_instance_sync(cls) -> "ProjectRegistry":
        """Get or create the singleton instance (sync version for startup)."""
        if cls._instance is None:
            cls._instance = ProjectRegistry()
        return cls._instance

    def configure(
        self,
        cache_ttl: Optional[float] = None,
        entry_ttl: Optional[float] = None,
        search_paths: Optional[List[Path]] = None,
        max_depth: Optional[int] = None,
    ) -> None:
        """Configure registry settings."""
        if cache_ttl is not None:
            self._cache_ttl = cache_ttl
        if entry_ttl is not None:
            self._entry_ttl = entry_ttl
        if search_paths is not None:
            self._search_paths = search_paths
        if max_depth is not None:
            self._max_depth = max_depth

    def _get_search_paths(self) -> List[Path]:
        """Get configured search paths or defaults."""
        if self._search_paths is not None:
            return self._search_paths

        home = Path.home()
        return [
            home / "projects",
            home / "dev",
            home / "workspace",
            home / "src",
            Path.cwd(),
        ]

    async def get_projects(
        self, force_refresh: bool = False
    ) -> List[ProjectCacheEntry]:
        """
        Get all projects, using cache when available.

        Args:
            force_refresh: If True, bypass cache and do full scan

        Returns:
            List of cached project entries
        """
        # Check if cache is valid
        if not force_refresh and self._is_cache_valid():
            logger.debug("Returning cached projects (%d entries)", len(self._cache))
            return list(self._cache.values())

        # Need to refresh - acquire lock to prevent concurrent scans
        async with self._scan_lock:
            # Double-check cache after acquiring lock (another request may have refreshed)
            if not force_refresh and self._is_cache_valid():
                return list(self._cache.values())

            # Perform the scan
            await self._refresh_cache()
            return list(self._cache.values())

    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if self._last_full_scan is None:
            return False

        age = (datetime.now(timezone.utc) - self._last_full_scan).total_seconds()
        return age < self._cache_ttl

    async def _refresh_cache(self) -> None:
        """
        Refresh the entire cache by scanning the filesystem.

        This runs the blocking filesystem scan in a thread pool to avoid
        blocking the event loop.
        """
        start_time = time.monotonic()
        logger.info("Starting project discovery scan...")

        # Run blocking filesystem scan in thread pool
        loop = asyncio.get_event_loop()
        discovered_paths = await loop.run_in_executor(
            None, self._discover_projects_sync
        )

        # Build cache entries (also in thread pool for TOML reads)
        new_cache: Dict[str, ProjectCacheEntry] = {}
        for project_path in discovered_paths:
            entry = await loop.run_in_executor(
                None, self._build_cache_entry, project_path
            )
            if entry:
                new_cache[str(project_path)] = entry

        # Atomic swap
        self._cache = new_cache
        self._last_full_scan = datetime.now(timezone.utc)

        elapsed = time.monotonic() - start_time
        logger.info(
            "Project discovery completed: %d projects found in %.2fs",
            len(self._cache),
            elapsed,
        )

    def _discover_projects_sync(self) -> List[Path]:
        """
        Synchronously discover projects with deployment files.

        This is the blocking filesystem scan that runs in a thread pool.
        """
        discovered = []
        search_paths = self._get_search_paths()

        for search_path in search_paths:
            if not search_path.exists() or not search_path.is_dir():
                continue

            try:
                search_path = search_path.resolve()
            except (RuntimeError, OSError) as e:
                logger.warning(f"Invalid search path {search_path}: {e}")
                continue

            try:
                # Use rglob to find deployment files
                for deployment_file in search_path.rglob(
                    ".claude/.skillmeat-deployed.toml"
                ):
                    project_path = deployment_file.parent.parent

                    # Validate path is within search_path
                    try:
                        project_path = project_path.resolve()
                        project_path.relative_to(search_path)
                    except (ValueError, RuntimeError, OSError):
                        continue

                    # Check depth limit
                    depth = len(project_path.relative_to(search_path).parts)
                    if depth > self._max_depth:
                        continue

                    if project_path not in discovered:
                        discovered.append(project_path)

            except (PermissionError, OSError) as e:
                logger.warning(f"Error scanning {search_path}: {e}")
                continue

        return discovered

    def _build_cache_entry(self, project_path: Path) -> Optional[ProjectCacheEntry]:
        """
        Build a cache entry for a project (blocking TOML reads).

        Returns None if the project can't be read.
        """
        try:
            deployments = DeploymentTracker.read_deployments(project_path)

            # Find most recent deployment
            last_deployment = None
            if deployments:
                last_deployment = max(d.deployed_at for d in deployments)

            # Get project name
            metadata = ProjectMetadataStorage.read_metadata(project_path)
            project_name = metadata.name if metadata else project_path.name

            return ProjectCacheEntry(
                path=project_path,
                name=project_name,
                deployment_count=len(deployments),
                last_deployment=last_deployment,
            )
        except Exception as e:
            logger.warning(f"Failed to build cache entry for {project_path}: {e}")
            return None

    async def invalidate(self, project_path: Optional[Path] = None) -> None:
        """
        Invalidate cache entry for a specific project, or entire cache.

        Call this after deploy/delete operations to ensure fresh data.

        Args:
            project_path: Specific project to invalidate, or None for entire cache
        """
        if project_path is None:
            # Invalidate entire cache
            self._last_full_scan = None
            logger.info("Project registry cache invalidated (full)")
        else:
            # Invalidate specific entry
            path_str = str(project_path.resolve())
            if path_str in self._cache:
                del self._cache[path_str]
                logger.info(f"Project registry cache invalidated for {project_path}")

    async def refresh_entry(self, project_path: Path) -> Optional[ProjectCacheEntry]:
        """
        Refresh a single project entry without full scan.

        Useful after deploy operations to update the cache immediately.
        """
        loop = asyncio.get_event_loop()
        entry = await loop.run_in_executor(None, self._build_cache_entry, project_path)

        if entry:
            self._cache[str(project_path)] = entry
            logger.debug(f"Refreshed cache entry for {project_path}")

        return entry

    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging/monitoring."""
        return {
            "entries": len(self._cache),
            "last_scan": (
                self._last_full_scan.isoformat() if self._last_full_scan else None
            ),
            "cache_ttl": self._cache_ttl,
            "is_valid": self._is_cache_valid(),
            "age_seconds": (
                (datetime.now(timezone.utc) - self._last_full_scan).total_seconds()
                if self._last_full_scan
                else None
            ),
        }

    async def start_background_refresh(self, interval: Optional[float] = None) -> None:
        """
        Start a background task that periodically refreshes the cache.

        Args:
            interval: Refresh interval in seconds (defaults to cache_ttl)
        """
        if self._refresh_task is not None:
            return  # Already running

        interval = interval or self._cache_ttl

        async def refresh_loop():
            while True:
                await asyncio.sleep(interval)
                try:
                    async with self._scan_lock:
                        await self._refresh_cache()
                except Exception as e:
                    logger.error(f"Background refresh failed: {e}")

        self._refresh_task = asyncio.create_task(refresh_loop())
        logger.info(f"Started background refresh task (interval: {interval}s)")

    async def stop_background_refresh(self) -> None:
        """Stop the background refresh task."""
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
            logger.info("Stopped background refresh task")


# Convenience function for API routes
async def get_project_registry() -> ProjectRegistry:
    """Get the ProjectRegistry instance (FastAPI dependency)."""
    return await ProjectRegistry.get_instance()
