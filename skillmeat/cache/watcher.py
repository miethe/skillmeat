"""File system watcher for cache invalidation.

This module provides the FileWatcher class which monitors file system changes
and triggers cache invalidation for affected projects and artifacts. It uses
the watchdog library for cross-platform file monitoring.

The watcher monitors:
- ~/.skillmeat/manifest.toml - Global manifest changes
- ./.claude/ directories - Project-specific artifact changes
- Deployment directories - Artifact file modifications

Features:
- Cross-platform support (Windows, macOS, Linux)
- Debouncing to avoid cascading invalidations
- Targeted invalidation based on file path
- Graceful error handling and resource cleanup
- Thread-safe operation

Architecture:
    FileWatcher
    ├── CacheFileEventHandler (watchdog event handler)
    ├── Observer threads (one per watch path)
    ├── Debounce queue (collects rapid changes)
    └── CacheRepository (for invalidation operations)

Example:
    >>> from skillmeat.cache.repository import CacheRepository
    >>> from skillmeat.cache.watcher import FileWatcher
    >>>
    >>> repo = CacheRepository()
    >>> watcher = FileWatcher(cache_repository=repo)
    >>>
    >>> # Start watching
    >>> watcher.start()
    >>>
    >>> # File changes automatically trigger cache invalidation
    >>> # ...
    >>>
    >>> # Stop watching when done
    >>> watcher.stop()

Usage in API:
    The FileWatcher is typically started when the API server starts and
    stopped during shutdown. It runs in background threads and requires
    no manual intervention after initialization.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from watchdog.events import (
    FileSystemEvent,
    FileSystemEventHandler,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)
from watchdog.observers import Observer

from skillmeat.cache.repository import CacheRepository

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Event Handler
# =============================================================================


class CacheFileEventHandler(FileSystemEventHandler):
    """Handles file system events for cache invalidation.

    This handler receives file system events from watchdog and filters them
    to identify relevant changes (manifest files, skill directories, etc.).
    Relevant changes are passed to the FileWatcher for processing.

    Attributes:
        watcher: Parent FileWatcher instance
    """

    def __init__(self, watcher: FileWatcher):
        """Initialize event handler.

        Args:
            watcher: Parent FileWatcher instance for event routing
        """
        super().__init__()
        self.watcher = watcher

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events.

        Args:
            event: FileSystemEvent containing file path and type
        """
        if not event.is_directory and self._is_relevant_file(event.src_path):
            logger.debug(f"File modified: {event.src_path}")
            self.watcher._handle_file_change(event.src_path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events.

        Args:
            event: FileSystemEvent containing file path and type
        """
        if not event.is_directory and self._is_relevant_file(event.src_path):
            logger.debug(f"File created: {event.src_path}")
            self.watcher._handle_file_change(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events.

        Args:
            event: FileSystemEvent containing file path and type
        """
        if not event.is_directory and self._is_relevant_file(event.src_path):
            logger.debug(f"File deleted: {event.src_path}")
            self.watcher._handle_file_change(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename events.

        Args:
            event: FileMovedEvent containing source and destination paths
        """
        if isinstance(event, FileMovedEvent):
            if not event.is_directory:
                # Check both source and destination
                if self._is_relevant_file(event.src_path):
                    logger.debug(f"File moved from: {event.src_path}")
                    self.watcher._handle_file_change(event.src_path)
                if self._is_relevant_file(event.dest_path):
                    logger.debug(f"File moved to: {event.dest_path}")
                    self.watcher._handle_file_change(event.dest_path)

    def _is_relevant_file(self, path: str) -> bool:
        """Check if file is relevant for cache invalidation.

        Relevant files include:
        - manifest.toml (global or project)
        - *.md files in artifact directories
        - SKILL.md, COMMAND.md, AGENT.md, etc.

        Ignores:
        - Temporary files (~, .tmp, .swp)
        - Hidden files (unless .claude/)
        - __pycache__, .git, node_modules
        - Build artifacts

        Args:
            path: File path to check

        Returns:
            True if file is relevant for cache invalidation
        """
        path_lower = path.lower()
        filename = os.path.basename(path)

        # Ignore temporary and system files
        if any(
            [
                filename.startswith(".") and ".claude" not in path,
                filename.endswith("~"),
                filename.endswith(".tmp"),
                filename.endswith(".swp"),
                "__pycache__" in path,
                ".git" in path.split(os.sep),
                "node_modules" in path.split(os.sep),
                ".next" in path.split(os.sep),
                "dist" in path.split(os.sep),
                "build" in path.split(os.sep),
            ]
        ):
            return False

        # Check for manifest files
        if filename == "manifest.toml":
            return True

        # Check for artifact definition files (case-insensitive)
        filename_upper = filename.upper()
        if filename_upper in [
            "SKILL.MD",
            "COMMAND.MD",
            "AGENT.MD",
            "MCP.MD",
            "HOOK.MD",
        ]:
            return True

        # Check for markdown files in .claude directories
        if ".claude" in path and filename.endswith(".md"):
            return True

        return False


# =============================================================================
# File Watcher
# =============================================================================


class FileWatcher:
    """Watches filesystem for changes and triggers cache invalidation.

    Monitors manifest files and deployment directories for changes, then
    triggers targeted cache invalidation through the CacheRepository.
    Uses debouncing to avoid cascading invalidations from rapid changes.

    The watcher runs observer threads in the background and requires no
    manual intervention after starting. It supports dynamic addition and
    removal of watch paths while running.

    Attributes:
        cache_repository: CacheRepository for cache operations
        watch_paths: List of paths currently being watched
        debounce_ms: Debounce window in milliseconds
        observers: Dict mapping paths to Observer instances
        running: Flag indicating if watcher is active
        invalidation_queue: Set of paths pending invalidation
        debounce_timer: Timer for debounce processing
        queue_lock: Lock for thread-safe queue operations

    Example:
        >>> repo = CacheRepository()
        >>> watcher = FileWatcher(
        ...     cache_repository=repo,
        ...     watch_paths=[
        ...         str(Path.home() / ".skillmeat"),
        ...         "./.claude"
        ...     ],
        ...     debounce_ms=100
        ... )
        >>> watcher.start()
        >>> # ... application runs ...
        >>> watcher.stop()
    """

    def __init__(
        self,
        cache_repository: CacheRepository,
        watch_paths: Optional[List[str]] = None,
        debounce_ms: int = 100,
    ):
        """Initialize file watcher.

        Args:
            cache_repository: CacheRepository instance for invalidation
            watch_paths: Paths to watch. If None, uses defaults:
                - ~/.skillmeat/
                - ./.claude/
            debounce_ms: Debounce window in milliseconds (default: 100)

        Example:
            >>> repo = CacheRepository()
            >>> watcher = FileWatcher(cache_repository=repo)
            >>>
            >>> # With custom paths
            >>> watcher = FileWatcher(
            ...     cache_repository=repo,
            ...     watch_paths=["/path/to/project"],
            ...     debounce_ms=200
            ... )
        """
        self.cache_repository = cache_repository
        self.debounce_ms = debounce_ms

        # Initialize watch paths
        if watch_paths is None:
            self.watch_paths: List[str] = self._get_default_watch_paths()
        else:
            self.watch_paths = [os.path.normpath(p) for p in watch_paths]

        # Observer management
        self.observers: Dict[str, Observer] = {}
        self.running = False

        # Debounce queue
        self.invalidation_queue: Set[str] = set()
        self.debounce_timer: Optional[threading.Timer] = None
        self.queue_lock = threading.Lock()

        logger.info(
            f"Initialized FileWatcher with {len(self.watch_paths)} paths, "
            f"debounce={debounce_ms}ms"
        )

    def _get_default_watch_paths(self) -> List[str]:
        """Get default watch paths.

        Returns:
            List of default paths to watch:
            - ~/.skillmeat/ (if exists)
            - ./.claude/ (if exists)
        """
        paths = []

        # Global skillmeat directory
        global_path = Path.home() / ".skillmeat"
        if global_path.exists():
            paths.append(str(global_path))

        # Local project directory
        local_path = Path.cwd() / ".claude"
        if local_path.exists():
            paths.append(str(local_path))

        return [os.path.normpath(p) for p in paths]

    def start(self) -> None:
        """Start watching for file changes.

        Creates observer threads for each watch path. Non-blocking - returns
        immediately after starting observers.

        Raises:
            RuntimeError: If watcher is already running

        Example:
            >>> watcher = FileWatcher(cache_repository=repo)
            >>> watcher.start()
            >>> print("Watching for changes...")
        """
        if self.running:
            raise RuntimeError("FileWatcher is already running")

        logger.info("Starting FileWatcher...")

        # Create observers for each path
        for path in self.watch_paths:
            if not os.path.exists(path):
                logger.warning(f"Watch path does not exist, skipping: {path}")
                continue

            try:
                observer = Observer()
                handler = CacheFileEventHandler(self)
                observer.schedule(handler, path, recursive=True)
                observer.start()
                self.observers[path] = observer
                logger.info(f"Started watching: {path}")
            except Exception as e:
                logger.error(f"Failed to watch path {path}: {e}")

        self.running = True
        logger.info(f"FileWatcher started with {len(self.observers)} active observers")

    def stop(self) -> None:
        """Stop watching for file changes.

        Stops all observer threads and cleans up resources. Waits for
        threads to terminate gracefully.

        Example:
            >>> watcher.stop()
            >>> print("Stopped watching")
        """
        if not self.running:
            logger.warning("FileWatcher is not running")
            return

        logger.info("Stopping FileWatcher...")

        # Cancel pending debounce timer
        with self.queue_lock:
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()
                self.debounce_timer = None

        # Stop all observers
        for path, observer in self.observers.items():
            try:
                observer.stop()
                observer.join(timeout=5.0)
                logger.info(f"Stopped watching: {path}")
            except Exception as e:
                logger.error(f"Error stopping observer for {path}: {e}")

        self.observers.clear()
        self.running = False
        logger.info("FileWatcher stopped")

    def is_running(self) -> bool:
        """Check if watcher is currently running.

        Returns:
            True if watcher is active

        Example:
            >>> if watcher.is_running():
            ...     print("Watcher is active")
        """
        return self.running

    def add_watch_path(self, path: str) -> bool:
        """Add a new path to watch.

        Can be called while watcher is running. Creates a new observer
        for the path if watcher is active.

        Args:
            path: Directory path to watch

        Returns:
            True if path was added successfully

        Example:
            >>> watcher.add_watch_path("/path/to/project")
            True
        """
        path = os.path.normpath(path)

        if path in self.watch_paths:
            logger.debug(f"Path already being watched: {path}")
            return False

        if not os.path.exists(path):
            logger.warning(f"Cannot watch non-existent path: {path}")
            return False

        self.watch_paths.append(path)

        # If watcher is running, start observer for this path
        if self.running:
            try:
                observer = Observer()
                handler = CacheFileEventHandler(self)
                observer.schedule(handler, path, recursive=True)
                observer.start()
                self.observers[path] = observer
                logger.info(f"Added watch path: {path}")
                return True
            except Exception as e:
                logger.error(f"Failed to watch path {path}: {e}")
                self.watch_paths.remove(path)
                return False
        else:
            logger.info(f"Added watch path (will start when watcher starts): {path}")
            return True

    def remove_watch_path(self, path: str) -> bool:
        """Remove a path from watching.

        Stops the observer for the path if watcher is running.

        Args:
            path: Directory path to stop watching

        Returns:
            True if path was removed

        Example:
            >>> watcher.remove_watch_path("/path/to/project")
            True
        """
        path = os.path.normpath(path)

        if path not in self.watch_paths:
            logger.debug(f"Path not being watched: {path}")
            return False

        self.watch_paths.remove(path)

        # If watcher is running, stop observer for this path
        if self.running and path in self.observers:
            try:
                observer = self.observers.pop(path)
                observer.stop()
                observer.join(timeout=5.0)
                logger.info(f"Removed watch path: {path}")
            except Exception as e:
                logger.error(f"Error removing watch path {path}: {e}")
                return False

        return True

    def get_watch_paths(self) -> List[str]:
        """Get list of currently watched paths.

        Returns:
            List of absolute paths being watched

        Example:
            >>> paths = watcher.get_watch_paths()
            >>> for path in paths:
            ...     print(f"Watching: {path}")
        """
        return self.watch_paths.copy()

    # =========================================================================
    # Internal Event Handling
    # =========================================================================

    def _handle_file_change(self, path: str) -> None:
        """Handle file change event.

        Routes the file change to appropriate handler based on file type.

        Args:
            path: Path to changed file
        """
        path = os.path.normpath(path)
        filename = os.path.basename(path)

        if filename == "manifest.toml":
            self.on_manifest_modified(path)
        elif filename.upper() in ["SKILL.md", "COMMAND.md", "AGENT.md", "MCP.md", "HOOK.md"]:
            self.on_deployment_modified(path)
        elif ".claude" in path and filename.endswith(".md"):
            self.on_deployment_modified(path)

    def on_manifest_modified(self, path: str) -> None:
        """Handle manifest file modification.

        Triggers cache invalidation for affected project.

        Args:
            path: Path to modified manifest.toml

        Example:
            >>> watcher.on_manifest_modified("~/.skillmeat/manifest.toml")
        """
        project_id = self._path_to_project_id(path)
        if project_id:
            logger.info(f"Manifest modified, invalidating project: {project_id}")
            self._queue_invalidation(project_id)
        else:
            # Global manifest - invalidate all
            logger.info("Global manifest modified, invalidating all projects")
            self._queue_invalidation(None)

    def on_deployment_modified(self, path: str) -> None:
        """Handle deployment directory modification.

        Identifies affected artifact and invalidates its cache.

        Args:
            path: Path to modified file in deployment directory

        Example:
            >>> watcher.on_deployment_modified("./.claude/skills/my-skill/SKILL.md")
        """
        project_id = self._path_to_project_id(path)
        if project_id:
            logger.info(f"Deployment modified, invalidating project: {project_id}")
            self._queue_invalidation(project_id)

    def _queue_invalidation(self, project_id: Optional[str] = None) -> None:
        """Queue an invalidation request with debouncing.

        Collects invalidation requests within the debounce window and
        processes them together to avoid cascading updates.

        Args:
            project_id: Project ID to invalidate, or None for global

        Example:
            >>> watcher._queue_invalidation("proj-123")
        """
        with self.queue_lock:
            # Add to queue (use special key for global invalidation)
            key = project_id if project_id else "__GLOBAL__"
            self.invalidation_queue.add(key)

            # Cancel existing timer
            if self.debounce_timer is not None:
                self.debounce_timer.cancel()

            # Start new timer
            self.debounce_timer = threading.Timer(
                self.debounce_ms / 1000.0, self._process_invalidation_queue
            )
            self.debounce_timer.start()

    def _process_invalidation_queue(self) -> None:
        """Process queued invalidations after debounce period.

        Executes all queued invalidation requests through the repository.
        """
        with self.queue_lock:
            if not self.invalidation_queue:
                return

            queue = self.invalidation_queue.copy()
            self.invalidation_queue.clear()
            self.debounce_timer = None

        logger.info(f"Processing {len(queue)} invalidation requests")

        for key in queue:
            try:
                if key == "__GLOBAL__":
                    # Global invalidation - mark all projects as stale
                    self._invalidate_all_projects()
                else:
                    # Project-specific invalidation
                    self._invalidate_project(key)
            except Exception as e:
                logger.error(f"Error invalidating {key}: {e}")

    def _invalidate_project(self, project_id: str) -> None:
        """Invalidate cache for a specific project.

        Args:
            project_id: Project ID to invalidate
        """
        try:
            project = self.cache_repository.get_project(project_id)
            if project:
                self.cache_repository.update_project(
                    project_id, status="stale", error_message=None
                )
                logger.info(f"Invalidated project cache: {project_id}")
            else:
                logger.debug(f"Project not in cache, skipping invalidation: {project_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate project {project_id}: {e}")

    def _invalidate_all_projects(self) -> None:
        """Invalidate cache for all projects."""
        try:
            projects = self.cache_repository.list_projects()
            count = 0
            for project in projects:
                self.cache_repository.update_project(
                    project.id, status="stale", error_message=None
                )
                count += 1
            logger.info(f"Invalidated all project caches ({count} projects)")
        except Exception as e:
            logger.error(f"Failed to invalidate all projects: {e}")

    def _path_to_project_id(self, path: str) -> Optional[str]:
        """Map a file path to a project ID for targeted invalidation.

        Uses heuristics to identify the project based on path structure:
        - ~/.skillmeat/ -> global (None)
        - /path/to/project/.claude/ -> project at /path/to/project

        Args:
            path: File path to map

        Returns:
            Project ID or None for global scope

        Example:
            >>> watcher._path_to_project_id("/home/user/project/.claude/skills/my-skill/SKILL.md")
            'proj-abc123'
        """
        path = os.path.normpath(path)

        # Check if path is in global skillmeat directory
        global_dir = os.path.normpath(str(Path.home() / ".skillmeat"))
        if path.startswith(global_dir):
            return None

        # Try to find .claude directory in path
        parts = path.split(os.sep)
        try:
            claude_index = parts.index(".claude")
            # Project path is everything before .claude
            project_path = os.sep.join(parts[:claude_index])

            # Look up project in cache by path
            project = self.cache_repository.get_project_by_path(project_path)
            if project:
                return project.id

            logger.debug(f"No cached project found for path: {project_path}")
            return None
        except (ValueError, IndexError):
            # .claude not in path or path structure invalid
            logger.debug(f"Could not extract project path from: {path}")
            return None
