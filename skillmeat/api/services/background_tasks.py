"""Background tasks for cache maintenance.

This module provides an optional background task for periodically refreshing
stale artifact metadata in the CollectionArtifact cache. The task runs in
the background without blocking API requests.

Usage:
    The CacheRefreshTask is optional and can be started during app lifespan:

    >>> from skillmeat.api.services.background_tasks import CacheRefreshTask
    >>>
    >>> # In lifespan context manager
    >>> cache_task = CacheRefreshTask(
    ...     db_session_factory=get_session,
    ...     artifact_mgr=app.state.artifact_manager,
    ...     refresh_interval_seconds=300,  # 5 minutes
    ...     ttl_seconds=1800,  # 30 minutes
    ... )
    >>> await cache_task.start()
    >>> yield
    >>> await cache_task.stop()

Note:
    This is optional. The implementation plan suggests starting with manual
    refresh via endpoint, and only adding background task if performance
    metrics warrant it.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CacheRefreshTask:
    """Background task to periodically refresh stale artifact metadata.

    This task runs in an asyncio loop and periodically checks for artifacts
    with stale metadata (based on synced_at timestamp and TTL). When stale
    artifacts are found, it refreshes their cache from the filesystem.

    Attributes:
        db_session_factory: Callable that returns a new SQLAlchemy session
        artifact_mgr: ArtifactManager instance with show() method
        refresh_interval: Seconds between refresh cycles (default: 5 minutes)
        ttl: Seconds before an artifact is considered stale (default: 30 minutes)

    Example:
        >>> task = CacheRefreshTask(
        ...     db_session_factory=get_session,
        ...     artifact_mgr=artifact_manager,
        ...     refresh_interval_seconds=300,
        ...     ttl_seconds=1800,
        ... )
        >>> await task.start()
        >>> # ... app runs ...
        >>> await task.stop()
    """

    def __init__(
        self,
        db_session_factory: Callable,
        artifact_mgr,
        refresh_interval_seconds: int = 300,  # 5 minutes
        ttl_seconds: int = 1800,  # 30 minutes
    ):
        """Initialize the background refresh task.

        Args:
            db_session_factory: Factory function that returns a new DB session
            artifact_mgr: ArtifactManager instance for reading file metadata
            refresh_interval_seconds: How often to check for stale artifacts
            ttl_seconds: How old synced_at must be before considered stale
        """
        self.db_session_factory = db_session_factory
        self.artifact_mgr = artifact_mgr
        self.refresh_interval = refresh_interval_seconds
        self.ttl = ttl_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_refresh_time: Optional[datetime] = None
        self._refresh_count = 0
        self._error_count = 0

    @property
    def is_running(self) -> bool:
        """Check if the background task is currently running."""
        return self._running

    @property
    def stats(self) -> dict:
        """Get statistics about the background task."""
        return {
            "is_running": self._running,
            "refresh_interval_seconds": self.refresh_interval,
            "ttl_seconds": self.ttl,
            "last_refresh_time": (
                self._last_refresh_time.isoformat() if self._last_refresh_time else None
            ),
            "total_refresh_count": self._refresh_count,
            "total_error_count": self._error_count,
        }

    async def start(self) -> None:
        """Start the background refresh task.

        If already running, this is a no-op.
        """
        if self._running:
            logger.warning("Cache refresh task already running, ignoring start")
            return

        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info(
            f"Cache refresh background task started "
            f"(interval={self.refresh_interval}s, ttl={self.ttl}s)"
        )

    async def stop(self) -> None:
        """Stop the background refresh task gracefully.

        Cancels the running task and waits for it to complete.
        """
        if not self._running:
            logger.debug("Cache refresh task not running, ignoring stop")
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass  # Expected when task is cancelled
            self._task = None

        logger.info("Cache refresh background task stopped")

    async def _refresh_loop(self) -> None:
        """Main refresh loop - runs until stopped.

        This method runs in a loop, sleeping for refresh_interval seconds
        between each refresh cycle. It catches and logs exceptions to
        prevent the loop from dying on transient errors.
        """
        while self._running:
            try:
                await self._refresh_stale_artifacts()
                self._last_refresh_time = datetime.utcnow()
                self._refresh_count += 1
            except asyncio.CancelledError:
                # Task was cancelled, exit gracefully
                raise
            except Exception as e:
                self._error_count += 1
                logger.exception(f"Background refresh error: {e}")

            # Sleep until next refresh cycle
            try:
                await asyncio.sleep(self.refresh_interval)
            except asyncio.CancelledError:
                # Task was cancelled during sleep
                raise

    async def _refresh_stale_artifacts(self) -> None:
        """Find and refresh stale artifacts.

        This method:
        1. Creates a new DB session
        2. Queries for stale artifacts (synced_at is NULL or older than TTL)
        3. Refreshes each stale artifact from the filesystem
        4. Logs the results

        Note: Errors for individual artifacts are logged but don't stop
        the refresh of other artifacts.
        """
        from skillmeat.api.services.artifact_cache_service import (
            find_stale_artifacts,
            refresh_single_artifact_cache,
        )

        session = self.db_session_factory()
        try:
            stale = find_stale_artifacts(session, self.ttl)

            if not stale:
                logger.debug("No stale artifacts found")
                return

            logger.info(f"Background refresh: found {len(stale)} stale artifacts")
            refreshed = 0
            errors = 0

            for assoc in stale:
                try:
                    # Refresh this artifact's cache from filesystem
                    if refresh_single_artifact_cache(
                        session,
                        self.artifact_mgr,
                        assoc.artifact_id,
                        assoc.collection_id,
                    ):
                        refreshed += 1
                    else:
                        errors += 1
                        logger.debug(f"Failed to refresh artifact: {assoc.artifact_id}")
                except Exception as e:
                    errors += 1
                    logger.warning(f"Error refreshing {assoc.artifact_id}: {e}")

            logger.info(
                f"Background refresh completed: "
                f"refreshed={refreshed}, errors={errors}, total={len(stale)}"
            )

        finally:
            session.close()

    async def refresh_now(self) -> dict:
        """Trigger an immediate refresh (outside normal schedule).

        Returns:
            Dictionary with refresh results:
            - stale_count: Number of stale artifacts found
            - refreshed_count: Number successfully refreshed
            - error_count: Number that failed to refresh
        """
        from skillmeat.api.services.artifact_cache_service import (
            find_stale_artifacts,
            refresh_single_artifact_cache,
        )

        session = self.db_session_factory()
        try:
            stale = find_stale_artifacts(session, self.ttl)
            refreshed = 0
            errors = 0

            for assoc in stale:
                try:
                    if refresh_single_artifact_cache(
                        session,
                        self.artifact_mgr,
                        assoc.artifact_id,
                        assoc.collection_id,
                    ):
                        refreshed += 1
                    else:
                        errors += 1
                except Exception:
                    errors += 1

            self._last_refresh_time = datetime.utcnow()
            self._refresh_count += 1

            return {
                "stale_count": len(stale),
                "refreshed_count": refreshed,
                "error_count": errors,
            }

        finally:
            session.close()
