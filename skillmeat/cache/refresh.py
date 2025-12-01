"""Background refresh job for SkillMeat cache.

This module provides the RefreshJob class which implements periodic cache
refresh operations using APScheduler. It runs as a background job to keep
cache data fresh based on TTL configuration.

Key Features:
- Periodic cache refresh based on configurable interval
- Manual refresh triggers (all projects or specific project)
- Concurrent project refreshes with configurable limits
- Retry logic with exponential backoff
- Event emission for UI real-time updates
- Change detection (version updates, new/removed artifacts)
- Thread-safe operations with proper synchronization

Architecture:
    RefreshJob -> CacheManager -> CacheRepository
    RefreshJob emits events -> Event listeners (UI, logging, etc.)

Usage:
    >>> from skillmeat.cache.manager import CacheManager
    >>> from skillmeat.cache.refresh import RefreshJob
    >>>
    >>> # Initialize manager and job
    >>> manager = CacheManager(ttl_minutes=360)
    >>> job = RefreshJob(
    ...     cache_manager=manager,
    ...     interval_hours=6.0,
    ...     max_concurrent=3
    ... )
    >>>
    >>> # Add event listener
    >>> def on_refresh_event(event: RefreshEvent):
    ...     print(f"Event: {event.type.value} at {event.timestamp}")
    >>> job.add_event_listener(on_refresh_event)
    >>>
    >>> # Start background scheduler
    >>> job.start_scheduler()
    >>>
    >>> # Manual refresh
    >>> result = job.refresh_all()
    >>> print(f"Refreshed {result.projects_refreshed} projects")
    >>>
    >>> # Stop scheduler when done
    >>> job.stop_scheduler()

Thread Safety:
    All public methods are thread-safe. Uses Lock for event listener
    management and relies on CacheManager's thread safety for cache operations.

Performance:
    - Runs with low priority to avoid blocking user operations
    - Limits concurrent refreshes to avoid overwhelming system
    - Only refreshes stale projects (TTL-based)
    - Emits events for incremental UI updates
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from skillmeat.cache.manager import CacheManager

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Event Types and Data Classes
# =============================================================================


class RefreshEventType(Enum):
    """Types of events emitted during refresh operations."""

    REFRESH_STARTED = "refresh_started"
    REFRESH_COMPLETED = "refresh_completed"
    REFRESH_ERROR = "refresh_error"
    CHANGES_DETECTED = "changes_detected"


@dataclass
class RefreshEvent:
    """Event emitted during refresh operations.

    Attributes:
        type: Type of event
        timestamp: When the event occurred
        project_id: Project ID (if event is project-specific)
        changes_detected: Whether changes were detected
        error: Error message (if event is error type)
        details: Additional event-specific details
    """

    type: RefreshEventType
    timestamp: datetime
    project_id: Optional[str] = None
    changes_detected: bool = False
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class RefreshResult:
    """Result of a refresh operation.

    Attributes:
        success: Overall success status
        projects_refreshed: Number of projects successfully refreshed
        errors: List of error messages encountered
        changes_detected: Whether any changes were detected
        duration_seconds: Total operation duration
    """

    success: bool
    projects_refreshed: int
    errors: List[str] = field(default_factory=list)
    changes_detected: bool = False
    duration_seconds: float = 0.0


# =============================================================================
# RefreshJob - Background Cache Refresh
# =============================================================================


class RefreshJob:
    """Background job for periodic cache refresh.

    Schedules periodic refreshes based on TTL configuration.
    Fetches fresh data and updates cache, emitting events
    for UI updates.

    Attributes:
        cache_manager: CacheManager for cache operations
        data_fetcher: Callable that fetches fresh data for a project
        interval_hours: How often to run periodic refresh
        max_concurrent: Max concurrent project refreshes
        retry_attempts: Number of retry attempts on failure
        retry_delay_seconds: Delay between retries

    Example:
        >>> manager = CacheManager()
        >>> job = RefreshJob(
        ...     cache_manager=manager,
        ...     interval_hours=6.0,
        ...     max_concurrent=3
        ... )
        >>> job.start_scheduler()
        >>> # ... later ...
        >>> job.stop_scheduler()
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        data_fetcher: Optional[Callable[[str], Optional[Dict]]] = None,
        interval_hours: float = 6.0,
        max_concurrent: int = 3,
        retry_attempts: int = 3,
        retry_delay_seconds: float = 5.0,
    ):
        """Initialize refresh job.

        Args:
            cache_manager: CacheManager for cache operations
            data_fetcher: Callable that fetches fresh data for a project.
                         Signature: (project_id) -> dict | None
                         If None, uses default filesystem fetcher.
            interval_hours: How often to run periodic refresh (default 6h)
            max_concurrent: Max concurrent project refreshes (default 3)
            retry_attempts: Number of retry attempts on failure
            retry_delay_seconds: Delay between retries with exponential backoff
        """
        self.cache_manager = cache_manager
        self.data_fetcher = data_fetcher or self._default_data_fetcher
        self.interval_hours = interval_hours
        self.max_concurrent = max_concurrent
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

        # Scheduler state
        self._scheduler: Optional[BackgroundScheduler] = None
        self._scheduler_lock = Lock()

        # Event system
        self._event_listeners: List[Callable[[RefreshEvent], None]] = []
        self._listener_lock = Lock()

        # Job state
        self._last_run_time: Optional[datetime] = None
        self._last_result: Optional[RefreshResult] = None

        logger.debug(
            f"Initialized RefreshJob (interval={interval_hours}h, "
            f"max_concurrent={max_concurrent}, retry_attempts={retry_attempts})"
        )

    # =========================================================================
    # Scheduler Management
    # =========================================================================

    def start_scheduler(self) -> None:
        """Start the background scheduler.

        Creates scheduler if not exists, adds periodic job,
        starts scheduler in background thread.

        Example:
            >>> job = RefreshJob(cache_manager)
            >>> job.start_scheduler()
            >>> print("Scheduler started")
        """
        with self._scheduler_lock:
            if self._scheduler is not None and self._scheduler.running:
                logger.warning("Scheduler already running")
                return

            # Create scheduler
            self._scheduler = BackgroundScheduler(
                daemon=True,  # Daemon thread for graceful shutdown
                job_defaults={
                    "coalesce": True,  # Combine missed runs
                    "max_instances": 1,  # Only one instance at a time
                    "misfire_grace_time": 300,  # 5 minute grace period
                },
            )

            # Add periodic job
            self._scheduler.add_job(
                func=self._periodic_refresh,
                trigger="interval",
                hours=self.interval_hours,
                id="cache_refresh",
                name="Cache Refresh Job",
                replace_existing=True,
            )

            # Start scheduler
            self._scheduler.start()

            logger.info(
                f"Cache refresh scheduler started (interval={self.interval_hours}h)"
            )

    def stop_scheduler(self, wait: bool = True) -> None:
        """Stop the background scheduler.

        Args:
            wait: If True, wait for running jobs to complete

        Example:
            >>> job.stop_scheduler(wait=True)
            >>> print("Scheduler stopped")
        """
        with self._scheduler_lock:
            if self._scheduler is None or not self._scheduler.running:
                logger.warning("Scheduler not running")
                return

            self._scheduler.shutdown(wait=wait)
            self._scheduler = None

            logger.info("Cache refresh scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is currently running.

        Returns:
            True if scheduler is running, False otherwise

        Example:
            >>> if job.is_running():
            ...     print("Scheduler is active")
        """
        with self._scheduler_lock:
            return self._scheduler is not None and self._scheduler.running

    # =========================================================================
    # Manual Refresh Operations
    # =========================================================================

    def refresh_all(self, force: bool = False) -> RefreshResult:
        """Manually refresh all projects.

        Args:
            force: If True, refresh even if not stale

        Returns:
            RefreshResult with summary of operation

        Example:
            >>> result = job.refresh_all(force=True)
            >>> print(f"Refreshed: {result.projects_refreshed} projects")
            >>> print(f"Changes detected: {result.changes_detected}")
        """
        start_time = time.time()

        # Emit start event
        self._emit_event(
            RefreshEvent(
                type=RefreshEventType.REFRESH_STARTED,
                timestamp=datetime.now(timezone.utc),
                details={"scope": "all", "force": force},
            )
        )

        logger.info(f"Starting refresh of all projects (force={force})")

        # Get all projects
        projects = self.cache_manager.get_projects()

        # Filter to stale projects only (unless force=True)
        if not force:
            projects_to_refresh = [
                p for p in projects if self.cache_manager.is_cache_stale(p.id)
            ]
            logger.debug(
                f"Found {len(projects_to_refresh)}/{len(projects)} stale projects"
            )
        else:
            projects_to_refresh = projects
            logger.debug(f"Force refresh: processing all {len(projects)} projects")

        # Refresh projects concurrently
        projects_refreshed = 0
        errors = []
        changes_detected = False

        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all refresh tasks
            future_to_project = {
                executor.submit(self._refresh_single_project, p.id): p.id
                for p in projects_to_refresh
            }

            # Process results as they complete
            for future in as_completed(future_to_project):
                project_id = future_to_project[future]
                try:
                    result = future.result()
                    if result.success:
                        projects_refreshed += 1
                        if result.changes_detected:
                            changes_detected = True
                    else:
                        errors.extend(result.errors)
                except Exception as e:
                    error_msg = f"Project {project_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Failed to refresh project {project_id}: {e}")

        duration = time.time() - start_time
        success = len(errors) == 0

        # Create result
        result = RefreshResult(
            success=success,
            projects_refreshed=projects_refreshed,
            errors=errors,
            changes_detected=changes_detected,
            duration_seconds=duration,
        )

        # Emit completion event
        self._emit_event(
            RefreshEvent(
                type=RefreshEventType.REFRESH_COMPLETED,
                timestamp=datetime.now(timezone.utc),
                changes_detected=changes_detected,
                details={
                    "projects_refreshed": projects_refreshed,
                    "total_projects": len(projects),
                    "duration_seconds": duration,
                },
            )
        )

        logger.info(
            f"Refresh completed: {projects_refreshed}/{len(projects_to_refresh)} "
            f"projects, changes={changes_detected}, duration={duration:.2f}s"
        )

        self._last_run_time = datetime.now(timezone.utc)
        self._last_result = result

        return result

    def refresh_project(self, project_id: str, force: bool = False) -> RefreshResult:
        """Refresh a specific project.

        Args:
            project_id: Project to refresh
            force: If True, refresh even if not stale

        Returns:
            RefreshResult with operation details

        Example:
            >>> result = job.refresh_project("proj-123")
            >>> if result.success:
            ...     print("Project refreshed successfully")
        """
        start_time = time.time()

        # Emit start event
        self._emit_event(
            RefreshEvent(
                type=RefreshEventType.REFRESH_STARTED,
                timestamp=datetime.now(timezone.utc),
                project_id=project_id,
                details={"scope": "project", "force": force},
            )
        )

        logger.info(f"Starting refresh of project {project_id} (force={force})")

        # Check if refresh needed
        if not force and not self.cache_manager.is_cache_stale(project_id):
            logger.debug(f"Project {project_id} is fresh, skipping refresh")
            return RefreshResult(
                success=True,
                projects_refreshed=0,
                duration_seconds=time.time() - start_time,
            )

        # Refresh project
        result = self._refresh_single_project(project_id)
        result.duration_seconds = time.time() - start_time

        # Emit completion event
        if result.success:
            self._emit_event(
                RefreshEvent(
                    type=RefreshEventType.REFRESH_COMPLETED,
                    timestamp=datetime.now(timezone.utc),
                    project_id=project_id,
                    changes_detected=result.changes_detected,
                    details={
                        "duration_seconds": result.duration_seconds,
                    },
                )
            )
        else:
            self._emit_event(
                RefreshEvent(
                    type=RefreshEventType.REFRESH_ERROR,
                    timestamp=datetime.now(timezone.utc),
                    project_id=project_id,
                    error="; ".join(result.errors),
                )
            )

        logger.info(
            f"Refresh completed for {project_id}: success={result.success}, "
            f"changes={result.changes_detected}, duration={result.duration_seconds:.2f}s"
        )

        return result

    # =========================================================================
    # Status and Queries
    # =========================================================================

    def get_next_run_time(self) -> Optional[datetime]:
        """Get when the next scheduled refresh will run.

        Returns:
            Datetime of next run, or None if scheduler not running

        Example:
            >>> next_run = job.get_next_run_time()
            >>> if next_run:
            ...     print(f"Next refresh at: {next_run}")
        """
        with self._scheduler_lock:
            if self._scheduler is None or not self._scheduler.running:
                return None

            job = self._scheduler.get_job("cache_refresh")
            if job is None:
                return None

            return job.next_run_time

    def get_last_run_time(self) -> Optional[datetime]:
        """Get when the last refresh completed.

        Returns:
            Datetime of last run, or None if never run

        Example:
            >>> last_run = job.get_last_run_time()
            >>> if last_run:
            ...     print(f"Last refresh: {last_run}")
        """
        return self._last_run_time

    def get_refresh_status(self) -> Dict[str, Any]:
        """Get current refresh job status.

        Returns dict with:
            - is_running: bool
            - last_run_time: datetime | None
            - next_run_time: datetime | None
            - last_result: RefreshResult | None
            - pending_refreshes: int

        Example:
            >>> status = job.get_refresh_status()
            >>> print(f"Running: {status['is_running']}")
            >>> print(f"Pending: {status['pending_refreshes']}")
        """
        # Count stale projects (pending refreshes)
        stale_count = len(
            [
                p
                for p in self.cache_manager.get_projects()
                if self.cache_manager.is_cache_stale(p.id)
            ]
        )

        return {
            "is_running": self.is_running(),
            "last_run_time": self._last_run_time,
            "next_run_time": self.get_next_run_time(),
            "last_result": self._last_result,
            "pending_refreshes": stale_count,
        }

    # =========================================================================
    # Event System
    # =========================================================================

    def add_event_listener(self, listener: Callable[[RefreshEvent], None]) -> None:
        """Add a listener for refresh events.

        Args:
            listener: Callable that accepts RefreshEvent

        Example:
            >>> def on_event(event: RefreshEvent):
            ...     print(f"Event: {event.type.value}")
            >>> job.add_event_listener(on_event)
        """
        with self._listener_lock:
            if listener not in self._event_listeners:
                self._event_listeners.append(listener)
                logger.debug(f"Added event listener: {listener.__name__}")

    def remove_event_listener(self, listener: Callable[[RefreshEvent], None]) -> None:
        """Remove an event listener.

        Args:
            listener: Callable to remove

        Example:
            >>> job.remove_event_listener(on_event)
        """
        with self._listener_lock:
            if listener in self._event_listeners:
                self._event_listeners.remove(listener)
                logger.debug(f"Removed event listener: {listener.__name__}")

    def _emit_event(self, event: RefreshEvent) -> None:
        """Emit an event to all listeners.

        Args:
            event: Event to emit

        Thread-safe: Yes
        """
        with self._listener_lock:
            listeners = self._event_listeners.copy()

        # Call listeners outside lock to avoid deadlock
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(
                    f"Event listener error ({listener.__name__}): {e}", exc_info=True
                )

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _periodic_refresh(self) -> None:
        """Scheduled job that runs periodically.

        Called by APScheduler on schedule.
        Refreshes all stale projects.
        """
        logger.info("Periodic refresh triggered")
        try:
            self.refresh_all(force=False)
        except Exception as e:
            logger.error(f"Periodic refresh failed: {e}", exc_info=True)
            # Emit error event
            self._emit_event(
                RefreshEvent(
                    type=RefreshEventType.REFRESH_ERROR,
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                )
            )

    def _refresh_single_project(self, project_id: str) -> RefreshResult:
        """Refresh a single project (with retry logic).

        Args:
            project_id: Project to refresh

        Returns:
            RefreshResult for this project

        Thread-safe: Yes (via CacheManager)
        """
        logger.debug(f"Refreshing project: {project_id}")

        # Get old data for change detection
        old_project = self.cache_manager.get_project(project_id)
        old_data = None
        if old_project:
            old_artifacts = self.cache_manager.get_artifacts(project_id)
            old_data = {
                "project": {
                    "name": old_project.name,
                    "path": old_project.path,
                    "status": old_project.status,
                },
                "artifacts": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "type": a.type,
                        "deployed_version": a.deployed_version,
                        "upstream_version": a.upstream_version,
                    }
                    for a in old_artifacts
                ],
            }

        # Fetch fresh data with retry
        new_data = self._fetch_project_data(project_id)

        if new_data is None:
            error_msg = f"Failed to fetch data for project {project_id}"
            self.cache_manager.mark_project_error(project_id, error_msg)
            return RefreshResult(
                success=False,
                projects_refreshed=0,
                errors=[error_msg],
            )

        # Update cache
        try:
            # Update project
            self.cache_manager.populate_projects([new_data])
            self.cache_manager.mark_project_refreshed(project_id)

            # Detect changes
            changes_detected = self._detect_changes(old_data, new_data)

            if changes_detected:
                logger.info(f"Changes detected in project {project_id}")
                self._emit_event(
                    RefreshEvent(
                        type=RefreshEventType.CHANGES_DETECTED,
                        timestamp=datetime.now(timezone.utc),
                        project_id=project_id,
                        changes_detected=True,
                        details={"old_data": old_data, "new_data": new_data},
                    )
                )

            return RefreshResult(
                success=True,
                projects_refreshed=1,
                changes_detected=changes_detected,
            )

        except Exception as e:
            error_msg = f"Failed to update cache for project {project_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.cache_manager.mark_project_error(project_id, str(e))
            return RefreshResult(
                success=False,
                projects_refreshed=0,
                errors=[error_msg],
            )

    def _fetch_project_data(self, project_id: str) -> Optional[Dict]:
        """Fetch fresh data for a project (with retry logic).

        Args:
            project_id: Project to fetch data for

        Returns:
            Project data dict or None on failure

        Implements exponential backoff retry.
        """
        for attempt in range(self.retry_attempts):
            try:
                data = self.data_fetcher(project_id)
                if data is not None:
                    return data

                # None result - treat as failure but don't log as error yet
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay_seconds * (2**attempt)
                    logger.warning(
                        f"Fetch attempt {attempt + 1}/{self.retry_attempts} "
                        f"returned None for {project_id}, retrying in {delay}s"
                    )
                    time.sleep(delay)

            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    delay = self.retry_delay_seconds * (2**attempt)
                    logger.warning(
                        f"Fetch attempt {attempt + 1}/{self.retry_attempts} "
                        f"failed for {project_id}: {e}, retrying in {delay}s"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All fetch attempts failed for {project_id}: {e}",
                        exc_info=True,
                    )

        return None

    def _detect_changes(self, old_data: Optional[Dict], new_data: Dict) -> bool:
        """Compare old and new data to detect changes.

        Args:
            old_data: Previous project data (None if new project)
            new_data: Fresh project data

        Returns:
            True if changes detected, False otherwise

        Detects:
            - Version changes in artifacts
            - New artifacts
            - Removed artifacts
            - Project status changes
        """
        if old_data is None:
            # New project - always consider as change
            return True

        # Compare artifact counts
        old_artifacts = old_data.get("artifacts", [])
        new_artifacts = new_data.get("artifacts", [])

        if len(old_artifacts) != len(new_artifacts):
            logger.debug("Change detected: artifact count changed")
            return True

        # Compare artifact versions
        old_artifact_map = {a["id"]: a for a in old_artifacts}
        new_artifact_map = {a["id"]: a for a in new_artifacts}

        # Check for new/removed artifacts
        old_ids = set(old_artifact_map.keys())
        new_ids = set(new_artifact_map.keys())

        if old_ids != new_ids:
            logger.debug("Change detected: artifact IDs changed")
            return True

        # Check for version changes
        for artifact_id in new_ids:
            old_artifact = old_artifact_map[artifact_id]
            new_artifact = new_artifact_map[artifact_id]

            # Check deployed version
            if old_artifact.get("deployed_version") != new_artifact.get(
                "deployed_version"
            ):
                logger.debug(
                    f"Change detected: deployed version changed for {artifact_id}"
                )
                return True

            # Check upstream version
            if old_artifact.get("upstream_version") != new_artifact.get(
                "upstream_version"
            ):
                logger.debug(
                    f"Change detected: upstream version changed for {artifact_id}"
                )
                return True

        # Check project status
        old_status = old_data.get("project", {}).get("status")
        new_status = new_data.get("status")

        if old_status != new_status:
            logger.debug("Change detected: project status changed")
            return True

        # No changes detected
        return False

    def _default_data_fetcher(self, project_id: str) -> Optional[Dict]:
        """Default data fetcher that reads from filesystem.

        Args:
            project_id: Project to fetch data for

        Returns:
            Project data dict or None on failure

        This is a placeholder implementation. In production,
        this should read from .claude/ directory, manifest files,
        and build the project data structure.
        """
        try:
            # Get project from cache
            project = self.cache_manager.get_project(project_id)
            if not project:
                logger.warning(f"Project not found in cache: {project_id}")
                return None

            # Read from filesystem (placeholder - implement actual logic)
            project_path = Path(project.path)
            claude_dir = project_path / ".claude"

            if not claude_dir.exists():
                logger.warning(f".claude directory not found: {claude_dir}")
                return None

            # Build project data (simplified - implement full logic)
            artifacts = self.cache_manager.get_artifacts(project_id)

            return {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "description": project.description,
                "status": "active",
                "artifacts": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "type": a.type,
                        "source": a.source,
                        "deployed_version": a.deployed_version,
                        "upstream_version": a.upstream_version,
                    }
                    for a in artifacts
                ],
            }

        except Exception as e:
            logger.error(f"Default data fetcher failed for {project_id}: {e}")
            return None
