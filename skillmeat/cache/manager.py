"""Service layer for SkillMeat cache operations.

This module provides the CacheManager class which implements high-level cache
management operations. It serves as the primary interface between the application
(CLI/API) and the cache repository, providing:

- Thread-safe cache operations with RLock
- Read/write operations for projects and artifacts
- Cache invalidation and refresh strategies
- TTL-based staleness detection
- Cache statistics and status reporting
- Automatic version comparison and outdated detection

Architecture:
    - Service layer coordinates cache operations
    - Delegates database operations to CacheRepository
    - Provides transaction boundaries and error handling
    - Implements business logic (TTL checks, version comparison)

Usage:
    >>> from skillmeat.cache.manager import CacheManager
    >>>
    >>> # Initialize manager
    >>> manager = CacheManager(ttl_minutes=360)
    >>>
    >>> # Populate cache with project data
    >>> projects = [
    ...     {
    ...         "id": "proj-1",
    ...         "name": "My Project",
    ...         "path": "/path/to/project",
    ...         "artifacts": [
    ...             {
    ...                 "id": "art-1",
    ...                 "name": "my-skill",
    ...                 "type": "skill",
    ...                 "deployed_version": "1.0.0",
    ...             }
    ...         ],
    ...     }
    ... ]
    >>> manager.populate_projects(projects)
    >>>
    >>> # Query cache
    >>> project = manager.get_project("proj-1")
    >>> artifacts = manager.get_artifacts("proj-1")
    >>> outdated = manager.get_outdated_artifacts()
    >>>
    >>> # Check staleness
    >>> if manager.is_cache_stale("proj-1"):
    ...     print("Project cache needs refresh")
    >>>
    >>> # Get cache statistics
    >>> status = manager.get_cache_status()
    >>> print(f"Total projects: {status['total_projects']}")
    >>> print(f"Outdated artifacts: {status['outdated_artifacts']}")

Thread Safety:
    All public methods are thread-safe via RLock. Multiple readers are allowed
    concurrently, but writes acquire exclusive lock.

Error Handling:
    - Repository errors are caught and logged
    - Methods return empty results ([], None, False) on errors
    - Critical errors are raised (initialization failures)
"""

from __future__ import annotations

import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from skillmeat.cache.models import Artifact, Project, create_tables
from skillmeat.cache.repository import CacheNotFoundError, CacheRepository

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# CacheManager Service Layer
# =============================================================================


class CacheManager:
    """Service layer for cache operations.

    Provides high-level methods for cache management, including
    read/write operations, invalidation, and refresh coordination.
    Thread-safe via RLock for concurrent access.

    Attributes:
        db_path: Path to cache database file
        ttl_minutes: Time-to-live for cached data (default 6 hours)
        repository: CacheRepository instance for database operations
        _lock: RLock for thread-safe operations

    Example:
        >>> manager = CacheManager(ttl_minutes=360)
        >>> manager.initialize_cache()
        >>>
        >>> # Populate cache
        >>> projects = [{"id": "p1", "name": "Test", "path": "/test"}]
        >>> manager.populate_projects(projects)
        >>>
        >>> # Query cache
        >>> all_projects = manager.get_projects()
        >>> stale_projects = manager.get_projects(include_stale=False)
    """

    def __init__(self, db_path: Optional[str] = None, ttl_minutes: int = 360):
        """Initialize cache manager.

        Args:
            db_path: Path to cache database. Uses ~/.skillmeat/cache/cache.db if None.
            ttl_minutes: Time-to-live for cached data (default 6 hours).

        Example:
            >>> # Use default path and TTL
            >>> manager = CacheManager()
            >>>
            >>> # Custom path and TTL
            >>> manager = CacheManager(
            ...     db_path="/custom/cache.db",
            ...     ttl_minutes=120
            ... )
        """
        # Resolve database path
        if db_path is None:
            self.db_path = str(Path.home() / ".skillmeat" / "cache" / "cache.db")
        else:
            self.db_path = db_path

        self.ttl_minutes = ttl_minutes

        # Initialize repository
        self.repository = CacheRepository(db_path=self.db_path)

        # Thread safety lock (RLock allows same thread to acquire multiple times)
        self._lock = threading.RLock()

        logger.debug(
            f"Initialized CacheManager (db={self.db_path}, ttl={ttl_minutes}m)"
        )

    # =========================================================================
    # Initialization
    # =========================================================================

    def initialize_cache(self) -> bool:
        """Initialize the cache database if needed.

        Creates database and runs migrations if not exists.
        Safe to call multiple times.

        Returns:
            True if initialization successful

        Example:
            >>> manager = CacheManager()
            >>> if manager.initialize_cache():
            ...     print("Cache initialized successfully")
        """
        try:
            with self._lock:
                # Ensure parent directory exists
                db_path = Path(self.db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)

                # Run Alembic migrations first (creates/updates schema)
                from skillmeat.cache.migrations import run_migrations
                run_migrations(self.db_path)

                # Then create any missing base tables (backward compatibility)
                create_tables(self.db_path)

                logger.info(f"Cache initialized at {self.db_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}", exc_info=True)
            return False

    # =========================================================================
    # Read Operations (Projects)
    # =========================================================================

    def get_projects(self, include_stale: bool = True) -> List[Project]:
        """Get all cached projects.

        Args:
            include_stale: If False, exclude stale projects based on TTL

        Returns:
            List of Project objects

        Example:
            >>> # Get all projects (including stale)
            >>> all_projects = manager.get_projects()
            >>>
            >>> # Get only fresh projects
            >>> fresh_projects = manager.get_projects(include_stale=False)
        """
        try:
            with self._lock:
                if include_stale:
                    projects = self.repository.list_projects()
                    logger.debug(f"Retrieved {len(projects)} projects (all)")
                else:
                    # Get all projects and filter out stale ones
                    all_projects = self.repository.list_projects()
                    stale_ids = {
                        p.id
                        for p in self.repository.get_stale_projects(self.ttl_minutes)
                    }
                    projects = [p for p in all_projects if p.id not in stale_ids]
                    logger.debug(
                        f"Retrieved {len(projects)} projects (fresh only, "
                        f"excluded {len(stale_ids)} stale)"
                    )
                return projects
        except Exception as e:
            logger.error(f"Failed to get projects: {e}", exc_info=True)
            return []

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a specific cached project by ID.

        Args:
            project_id: Unique project identifier

        Returns:
            Project object or None if not found

        Example:
            >>> project = manager.get_project("proj-123")
            >>> if project:
            ...     print(f"Found: {project.name}")
            ...     print(f"Artifacts: {len(project.artifacts)}")
        """
        try:
            with self._lock:
                project = self.repository.get_project(project_id)
                logger.debug(
                    f"Retrieved project: {project_id} (found={project is not None})"
                )
                return project
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}", exc_info=True)
            return None

    def get_project_by_path(self, path: str) -> Optional[Project]:
        """Get a project by its filesystem path.

        Args:
            path: Absolute filesystem path to project

        Returns:
            Project object or None if not found

        Example:
            >>> project = manager.get_project_by_path("/home/user/my-project")
            >>> if project:
            ...     print(f"Project ID: {project.id}")
        """
        try:
            with self._lock:
                project = self.repository.get_project_by_path(path)
                logger.debug(
                    f"Retrieved project by path: {path} (found={project is not None})"
                )
                return project
        except Exception as e:
            logger.error(f"Failed to get project by path {path}: {e}", exc_info=True)
            return None

    # =========================================================================
    # Read Operations (Artifacts)
    # =========================================================================

    def get_artifacts(self, project_id: str) -> List[Artifact]:
        """Get all artifacts for a project.

        Args:
            project_id: Unique project identifier

        Returns:
            List of Artifact objects for the project

        Example:
            >>> artifacts = manager.get_artifacts("proj-123")
            >>> for artifact in artifacts:
            ...     print(f"{artifact.name}: {artifact.type}")
            ...     if artifact.is_outdated:
            ...         print(f"  Update available: {artifact.upstream_version}")
        """
        try:
            with self._lock:
                artifacts = self.repository.list_artifacts_by_project(project_id)
                logger.debug(f"Retrieved {len(artifacts)} artifacts for {project_id}")
                return artifacts
        except Exception as e:
            logger.error(
                f"Failed to get artifacts for {project_id}: {e}", exc_info=True
            )
            return []

    def get_outdated_artifacts(self) -> List[Artifact]:
        """Get all artifacts that have newer upstream versions.

        Returns:
            List of Artifact objects where is_outdated=True

        Example:
            >>> outdated = manager.get_outdated_artifacts()
            >>> for artifact in outdated:
            ...     print(f"{artifact.name}:")
            ...     print(f"  Deployed: {artifact.deployed_version}")
            ...     print(f"  Available: {artifact.upstream_version}")
        """
        try:
            with self._lock:
                artifacts = self.repository.list_outdated_artifacts()
                logger.debug(f"Retrieved {len(artifacts)} outdated artifacts")
                return artifacts
        except Exception as e:
            logger.error(f"Failed to get outdated artifacts: {e}", exc_info=True)
            return []

    def search_artifacts(
        self,
        query: str,
        project_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "relevance",
    ) -> tuple[List[Artifact], int]:
        """Search artifacts by name with pagination and sorting.

        Args:
            query: Search query string (matched against artifact name)
            project_id: Optional project ID filter
            artifact_type: Optional artifact type filter
            skip: Number of results to skip (for pagination)
            limit: Maximum number of results to return
            sort_by: Sort order ('relevance', 'name', 'type', 'updated')

        Returns:
            Tuple of (artifacts, total_count) where:
                - artifacts: List of matching Artifact objects
                - total_count: Total number of matches (before pagination)

        Example:
            >>> # Search all artifacts with pagination
            >>> results, total = manager.search_artifacts("docker", skip=0, limit=20)
            >>> print(f"Showing {len(results)} of {total} results")
            >>>
            >>> # Search within a project, sorted by name
            >>> results, total = manager.search_artifacts(
            ...     "api",
            ...     project_id="proj-123",
            ...     sort_by="name"
            ... )
            >>>
            >>> # Search for specific type with pagination
            >>> results, total = manager.search_artifacts(
            ...     "test",
            ...     artifact_type="skill",
            ...     skip=10,
            ...     limit=10
            ... )
        """
        try:
            with self._lock:
                artifacts, total = self.repository.search_artifacts(
                    query=query,
                    project_id=project_id,
                    artifact_type=artifact_type,
                    skip=skip,
                    limit=limit,
                    sort_by=sort_by,
                )
                logger.debug(
                    f"Search returned {len(artifacts)} of {total} artifacts "
                    f"(query={query}, project={project_id}, type={artifact_type}, "
                    f"skip={skip}, limit={limit}, sort={sort_by})"
                )
                return artifacts, total
        except Exception as e:
            logger.error(
                f"Failed to search artifacts (query={query}): {e}", exc_info=True
            )
            return [], 0

    # =========================================================================
    # Write Operations (Populate)
    # =========================================================================

    def upsert_project(self, project_data: Dict[str, Any]) -> bool:
        """Add or update a single project in the cache.

        Unlike populate_projects(), this preserves existing entries and only
        adds/updates the specified project. Use this for incremental updates
        (e.g., after creating a new project).

        Args:
            project_data: Dict with keys:
                - id (str): Project ID
                - name (str): Project name
                - path (str): Filesystem path
                - description (str, optional): Project description
                - artifacts (list, optional): List of artifact dicts

        Returns:
            True if upsert successful, False otherwise

        Example:
            >>> project_data = {
            ...     "id": "proj-1",
            ...     "name": "My Project",
            ...     "path": "/path/to/project",
            ...     "description": "A test project",
            ...     "artifacts": [],
            ... }
            >>> success = manager.upsert_project(project_data)
            >>> if success:
            ...     print("Project added to cache")
        """
        try:
            with self._lock:
                # Extract artifacts if present (make a copy to avoid modifying input)
                data = project_data.copy()
                artifacts_data = data.pop("artifacts", [])

                # Check if project exists
                existing = self.repository.get_project(data["id"])

                if existing:
                    # Update existing project
                    self.repository.update_project(
                        data["id"],
                        **{k: v for k, v in data.items() if k not in ["id"]},
                    )
                    logger.debug(f"Updated project in cache: {data['id']}")
                else:
                    # Create new project
                    project_obj = Project(
                        id=data["id"],
                        name=data["name"],
                        path=data["path"],
                        description=data.get("description"),
                        status="active",
                        last_fetched=datetime.utcnow(),
                    )
                    self.repository.create_project(project_obj)
                    logger.debug(f"Created project in cache: {data['id']}")

                # Populate artifacts if provided
                if artifacts_data:
                    self.populate_artifacts(data["id"], artifacts_data)

                logger.info(f"Upserted project: {data['id']}")
                return True
        except Exception as e:
            logger.error(f"Failed to upsert project: {e}", exc_info=True)
            return False

    def populate_projects(self, projects: List[Dict[str, Any]]) -> int:
        """Populate cache with project data.

        Creates or updates projects and their artifacts in a single transaction.
        Existing projects are updated, new projects are created.

        Args:
            projects: List of project dicts with keys:
                - id (str): Project ID
                - name (str): Project name
                - path (str): Filesystem path
                - description (str, optional): Project description
                - artifacts (list, optional): List of artifact dicts

        Returns:
            Count of projects processed

        Example:
            >>> projects = [
            ...     {
            ...         "id": "proj-1",
            ...         "name": "My Project",
            ...         "path": "/path/to/project",
            ...         "description": "A test project",
            ...         "artifacts": [
            ...             {
            ...                 "id": "art-1",
            ...                 "name": "my-skill",
            ...                 "type": "skill",
            ...                 "deployed_version": "1.0.0",
            ...             }
            ...         ],
            ...     }
            ... ]
            >>> count = manager.populate_projects(projects)
            >>> print(f"Processed {count} projects")
        """
        try:
            with self._lock:
                count = 0
                for project_data in projects:
                    # Extract artifacts if present
                    artifacts_data = project_data.pop("artifacts", [])

                    # Check if project exists
                    existing = self.repository.get_project(project_data["id"])

                    if existing:
                        # Update existing project
                        self.repository.update_project(
                            project_data["id"],
                            **{
                                k: v for k, v in project_data.items() if k not in ["id"]
                            },
                        )
                        logger.debug(f"Updated project: {project_data['id']}")
                    else:
                        # Create new project
                        project_obj = Project(
                            id=project_data["id"],
                            name=project_data["name"],
                            path=project_data["path"],
                            description=project_data.get("description"),
                            status="active",
                            last_fetched=datetime.utcnow(),
                        )
                        self.repository.create_project(project_obj)
                        logger.debug(f"Created project: {project_data['id']}")

                    # Populate artifacts if provided
                    if artifacts_data:
                        self.populate_artifacts(project_data["id"], artifacts_data)

                    count += 1

                logger.info(f"Populated {count} projects")
                return count
        except Exception as e:
            logger.error(f"Failed to populate projects: {e}", exc_info=True)
            return 0

    def populate_artifacts(
        self, project_id: str, artifacts: List[Dict[str, Any]]
    ) -> int:
        """Populate artifacts for a specific project.

        Creates or updates artifacts in the cache. Automatically detects
        outdated artifacts by comparing deployed_version with upstream_version.

        Args:
            project_id: Project to add artifacts to
            artifacts: List of artifact dicts with keys:
                - id (str): Artifact ID
                - name (str): Artifact name
                - type (str): Artifact type (skill, command, etc.)
                - source (str, optional): Source identifier
                - deployed_version (str, optional): Version deployed to project
                - upstream_version (str, optional): Latest available version

        Returns:
            Count of artifacts processed

        Example:
            >>> artifacts = [
            ...     {
            ...         "id": "art-1",
            ...         "name": "my-skill",
            ...         "type": "skill",
            ...         "source": "github:user/repo/skill",
            ...         "deployed_version": "1.0.0",
            ...         "upstream_version": "1.1.0",
            ...     }
            ... ]
            >>> count = manager.populate_artifacts("proj-123", artifacts)
            >>> print(f"Processed {count} artifacts")
        """
        try:
            with self._lock:
                count = 0
                for artifact_data in artifacts:
                    # Check if artifact exists
                    existing = self.repository.get_artifact(artifact_data["id"])

                    # Determine if outdated
                    deployed = artifact_data.get("deployed_version")
                    upstream = artifact_data.get("upstream_version")
                    is_outdated = (
                        deployed is not None
                        and upstream is not None
                        and deployed != upstream
                    )

                    if existing:
                        # Update existing artifact
                        self.repository.update_artifact(
                            artifact_data["id"],
                            **{
                                k: v
                                for k, v in artifact_data.items()
                                if k not in ["id", "project_id"]
                            },
                            is_outdated=is_outdated,
                        )
                        logger.debug(f"Updated artifact: {artifact_data['id']}")
                    else:
                        # Create new artifact
                        artifact_obj = Artifact(
                            id=artifact_data["id"],
                            project_id=project_id,
                            name=artifact_data["name"],
                            type=artifact_data["type"],
                            source=artifact_data.get("source"),
                            deployed_version=deployed,
                            upstream_version=upstream,
                            is_outdated=is_outdated,
                            local_modified=artifact_data.get("local_modified", False),
                        )
                        self.repository.create_artifact(artifact_obj)
                        logger.debug(f"Created artifact: {artifact_data['id']}")

                    count += 1

                logger.info(f"Populated {count} artifacts for project: {project_id}")
                return count
        except Exception as e:
            logger.error(
                f"Failed to populate artifacts for {project_id}: {e}", exc_info=True
            )
            return 0

    # =========================================================================
    # Write Operations (Update)
    # =========================================================================

    def update_artifact_versions(
        self,
        artifact_id: str,
        deployed: Optional[str] = None,
        upstream: Optional[str] = None,
    ) -> bool:
        """Update version information for an artifact.

        Automatically sets is_outdated based on version comparison.
        Only updates fields that are provided (non-None).

        Args:
            artifact_id: Unique artifact identifier
            deployed: Deployed version string (optional)
            upstream: Upstream version string (optional)

        Returns:
            True if update successful, False otherwise

        Example:
            >>> # Update deployed version
            >>> manager.update_artifact_versions("art-123", deployed="1.1.0")
            >>>
            >>> # Update upstream version
            >>> manager.update_artifact_versions("art-123", upstream="1.2.0")
            >>>
            >>> # Update both (will mark as outdated if different)
            >>> manager.update_artifact_versions(
            ...     "art-123",
            ...     deployed="1.0.0",
            ...     upstream="1.2.0"
            ... )
        """
        try:
            with self._lock:
                # Get current artifact
                artifact = self.repository.get_artifact(artifact_id)
                if not artifact:
                    logger.warning(f"Artifact not found: {artifact_id}")
                    return False

                # Determine new versions
                new_deployed = (
                    deployed if deployed is not None else artifact.deployed_version
                )
                new_upstream = (
                    upstream if upstream is not None else artifact.upstream_version
                )

                # Calculate is_outdated
                is_outdated = (
                    new_deployed is not None
                    and new_upstream is not None
                    and new_deployed != new_upstream
                )

                # Update artifact
                update_dict = {"is_outdated": is_outdated}
                if deployed is not None:
                    update_dict["deployed_version"] = deployed
                if upstream is not None:
                    update_dict["upstream_version"] = upstream

                self.repository.update_artifact(artifact_id, **update_dict)
                logger.debug(
                    f"Updated versions for artifact {artifact_id}: "
                    f"deployed={new_deployed}, upstream={new_upstream}, "
                    f"outdated={is_outdated}"
                )
                return True
        except CacheNotFoundError:
            logger.warning(f"Artifact not found: {artifact_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to update artifact versions for {artifact_id}: {e}",
                exc_info=True,
            )
            return False

    def update_upstream_versions(self, version_map: Dict[str, str]) -> int:
        """Batch update upstream versions for multiple artifacts.

        Updates the upstream_version field for multiple artifacts in a single
        transaction. Automatically sets is_outdated flag based on version
        comparison.

        Args:
            version_map: Dict mapping artifact_id -> upstream_version

        Returns:
            Count of artifacts successfully updated

        Example:
            >>> version_map = {
            ...     "art-1": "1.2.0",
            ...     "art-2": "2.0.0",
            ...     "art-3": "abc1234",
            ... }
            >>> count = manager.update_upstream_versions(version_map)
            >>> print(f"Updated {count} artifacts")
        """
        if not version_map:
            logger.debug("Empty version map provided")
            return 0

        try:
            with self._lock:
                updated_count = 0

                for artifact_id, upstream_version in version_map.items():
                    try:
                        # Get current artifact
                        artifact = self.repository.get_artifact(artifact_id)
                        if not artifact:
                            logger.warning(f"Artifact not found: {artifact_id}")
                            continue

                        # Check if version actually changed
                        if artifact.upstream_version == upstream_version:
                            logger.debug(
                                f"Upstream version unchanged for {artifact_id}: {upstream_version}"
                            )
                            continue

                        # Calculate is_outdated
                        is_outdated = (
                            artifact.deployed_version is not None
                            and upstream_version is not None
                            and artifact.deployed_version != upstream_version
                        )

                        # Update artifact
                        self.repository.update_artifact(
                            artifact_id,
                            upstream_version=upstream_version,
                            is_outdated=is_outdated,
                        )

                        updated_count += 1

                        logger.debug(
                            f"Updated upstream version for {artifact_id}: "
                            f"{artifact.upstream_version} -> {upstream_version}, "
                            f"outdated={is_outdated}"
                        )

                    except CacheNotFoundError:
                        logger.warning(f"Artifact not found: {artifact_id}")
                        continue
                    except Exception as e:
                        logger.error(
                            f"Failed to update upstream version for {artifact_id}: {e}",
                            exc_info=True,
                        )
                        continue

                logger.info(
                    f"Batch updated upstream versions: {updated_count}/{len(version_map)} artifacts"
                )
                return updated_count

        except Exception as e:
            logger.error(
                f"Failed to batch update upstream versions: {e}", exc_info=True
            )
            return 0

    def mark_project_refreshed(self, project_id: str) -> bool:
        """Mark a project as freshly fetched (update last_fetched).

        Updates the project's last_fetched timestamp to current time
        and sets status to 'active'.

        Args:
            project_id: Unique project identifier

        Returns:
            True if update successful, False otherwise

        Example:
            >>> manager.mark_project_refreshed("proj-123")
        """
        try:
            with self._lock:
                self.repository.update_project(
                    project_id,
                    last_fetched=datetime.utcnow(),
                    status="active",
                    error_message=None,
                )
                logger.debug(f"Marked project refreshed: {project_id}")
                return True
        except CacheNotFoundError:
            logger.warning(f"Project not found: {project_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to mark project refreshed {project_id}: {e}", exc_info=True
            )
            return False

    def mark_project_error(self, project_id: str, error_message: str) -> bool:
        """Mark a project as having an error during fetch.

        Updates the project's status to 'error' and stores the error message.

        Args:
            project_id: Unique project identifier
            error_message: Error message to store

        Returns:
            True if update successful, False otherwise

        Example:
            >>> manager.mark_project_error(
            ...     "proj-123",
            ...     "Failed to read .claude directory"
            ... )
        """
        try:
            with self._lock:
                self.repository.update_project(
                    project_id,
                    status="error",
                    error_message=error_message,
                )
                logger.debug(f"Marked project error: {project_id} - {error_message}")
                return True
        except CacheNotFoundError:
            logger.warning(f"Project not found: {project_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to mark project error {project_id}: {e}", exc_info=True
            )
            return False

    # =========================================================================
    # Cache Management
    # =========================================================================

    def invalidate_cache(self, project_id: Optional[str] = None) -> int:
        """Invalidate cached data.

        Marks projects as stale by clearing their last_fetched timestamp.
        Does not delete data, just marks it as needing refresh.

        Args:
            project_id: If provided, only invalidate this project.
                       If None, invalidate entire cache.

        Returns:
            Count of entries invalidated

        Example:
            >>> # Invalidate entire cache
            >>> count = manager.invalidate_cache()
            >>> print(f"Invalidated {count} projects")
            >>>
            >>> # Invalidate specific project
            >>> count = manager.invalidate_cache("proj-123")
        """
        try:
            with self._lock:
                if project_id:
                    # Invalidate single project
                    self.repository.update_project(
                        project_id,
                        last_fetched=None,
                        status="stale",
                    )
                    logger.info(f"Invalidated project: {project_id}")
                    return 1
                else:
                    # Invalidate all projects
                    projects = self.repository.list_projects()
                    count = 0
                    for project in projects:
                        self.repository.update_project(
                            project.id,
                            last_fetched=None,
                            status="stale",
                        )
                        count += 1
                    logger.info(f"Invalidated {count} projects")
                    return count
        except CacheNotFoundError:
            logger.warning(f"Project not found: {project_id}")
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}", exc_info=True)
            return 0

    def refresh_if_stale(self, project_id: str, force: bool = False) -> bool:
        """Check if project needs refresh and trigger if so.

        Checks if project's last_fetched is older than TTL and marks
        it as needing refresh if so.

        Args:
            project_id: Unique project identifier
            force: If True, mark as stale regardless of TTL

        Returns:
            True if refresh was triggered/needed, False if still fresh

        Example:
            >>> # Check and refresh if stale
            >>> if manager.refresh_if_stale("proj-123"):
            ...     print("Project marked for refresh")
            >>>
            >>> # Force refresh regardless of TTL
            >>> manager.refresh_if_stale("proj-123", force=True)
        """
        try:
            with self._lock:
                if force:
                    # Force refresh
                    self.invalidate_cache(project_id)
                    logger.info(f"Forced refresh for project: {project_id}")
                    return True

                # Check if stale
                project = self.repository.get_project(project_id)
                if not project:
                    logger.warning(f"Project not found: {project_id}")
                    return False

                if project.last_fetched is None:
                    # Never fetched - mark for refresh
                    self.invalidate_cache(project_id)
                    logger.debug(f"Project never fetched: {project_id}")
                    return True

                threshold = datetime.utcnow() - timedelta(minutes=self.ttl_minutes)
                if project.last_fetched < threshold:
                    # Stale - mark for refresh
                    self.invalidate_cache(project_id)
                    logger.debug(f"Project stale: {project_id}")
                    return True

                # Still fresh
                logger.debug(f"Project fresh: {project_id}")
                return False
        except Exception as e:
            logger.error(
                f"Failed to check staleness for {project_id}: {e}", exc_info=True
            )
            return False

    def clear_cache(self) -> bool:
        """Clear all cached data.

        Deletes all projects and artifacts from the cache.
        This is destructive and cannot be undone.

        Returns:
            True on success, False on error

        Example:
            >>> # Clear entire cache
            >>> if manager.clear_cache():
            ...     print("Cache cleared successfully")
        """
        try:
            with self._lock:
                projects = self.repository.list_projects()
                count = 0
                for project in projects:
                    self.repository.delete_project(project.id)
                    count += 1
                logger.info(f"Cleared cache: deleted {count} projects")
                return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}", exc_info=True)
            return False

    # =========================================================================
    # Status and Statistics
    # =========================================================================

    def get_cache_status(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns comprehensive cache statistics including counts,
        staleness information, and cache size.

        Returns:
            Dictionary with cache statistics:
                - total_projects: Total number of cached projects
                - total_artifacts: Total number of cached artifacts
                - stale_projects: Number of stale projects (past TTL)
                - outdated_artifacts: Number of artifacts with updates available
                - cache_size_bytes: Database file size in bytes
                - oldest_entry: Datetime of oldest project (by created_at)
                - newest_entry: Datetime of newest project (by created_at)
                - last_refresh: Datetime of most recent project refresh

        Example:
            >>> status = manager.get_cache_status()
            >>> print(f"Total projects: {status['total_projects']}")
            >>> print(f"Stale projects: {status['stale_projects']}")
            >>> print(f"Outdated artifacts: {status['outdated_artifacts']}")
            >>> print(f"Cache size: {status['cache_size_bytes'] / 1024:.1f} KB")
        """
        try:
            with self._lock:
                # Get counts
                projects = self.repository.list_projects()
                stale_projects = self.repository.get_stale_projects(self.ttl_minutes)
                outdated_artifacts = self.repository.list_outdated_artifacts()

                # Calculate total artifacts
                total_artifacts = sum(len(p.artifacts) for p in projects)

                # Get oldest/newest entries
                oldest_entry = (
                    min((p.created_at for p in projects), default=None)
                    if projects
                    else None
                )
                newest_entry = (
                    max((p.created_at for p in projects), default=None)
                    if projects
                    else None
                )

                # Get last refresh
                last_refresh = (
                    max(
                        (p.last_fetched for p in projects if p.last_fetched),
                        default=None,
                    )
                    if projects
                    else None
                )

                # Get cache size
                cache_size = 0
                if os.path.exists(self.db_path):
                    cache_size = os.path.getsize(self.db_path)

                status = {
                    "total_projects": len(projects),
                    "total_artifacts": total_artifacts,
                    "stale_projects": len(stale_projects),
                    "outdated_artifacts": len(outdated_artifacts),
                    "cache_size_bytes": cache_size,
                    "oldest_entry": oldest_entry,
                    "newest_entry": newest_entry,
                    "last_refresh": last_refresh,
                }

                logger.debug(f"Cache status: {status}")
                return status
        except Exception as e:
            logger.error(f"Failed to get cache status: {e}", exc_info=True)
            return {
                "total_projects": 0,
                "total_artifacts": 0,
                "stale_projects": 0,
                "outdated_artifacts": 0,
                "cache_size_bytes": 0,
                "oldest_entry": None,
                "newest_entry": None,
                "last_refresh": None,
            }

    def get_last_refresh_time(
        self, project_id: Optional[str] = None
    ) -> Optional[datetime]:
        """Get when cache was last refreshed.

        Args:
            project_id: If provided, returns that project's last_fetched.
                       Otherwise returns the most recent refresh across all projects.

        Returns:
            Datetime of last refresh, or None if never refreshed

        Example:
            >>> # Get last refresh for specific project
            >>> last_refresh = manager.get_last_refresh_time("proj-123")
            >>> if last_refresh:
            ...     print(f"Last refreshed: {last_refresh}")
            >>>
            >>> # Get most recent refresh across all projects
            >>> last_refresh = manager.get_last_refresh_time()
        """
        try:
            with self._lock:
                if project_id:
                    # Get specific project's last refresh
                    project = self.repository.get_project(project_id)
                    if not project:
                        logger.warning(f"Project not found: {project_id}")
                        return None
                    return project.last_fetched
                else:
                    # Get most recent refresh across all projects
                    projects = self.repository.list_projects()
                    if not projects:
                        return None

                    last_refresh = max(
                        (p.last_fetched for p in projects if p.last_fetched),
                        default=None,
                    )
                    return last_refresh
        except Exception as e:
            logger.error(f"Failed to get last refresh time: {e}", exc_info=True)
            return None

    def is_cache_stale(self, project_id: Optional[str] = None) -> bool:
        """Check if cache (or specific project) is stale based on TTL.

        Args:
            project_id: If provided, checks if that project is stale.
                       Otherwise checks if any project is stale.

        Returns:
            True if cache/project is stale, False if fresh

        Example:
            >>> # Check if specific project is stale
            >>> if manager.is_cache_stale("proj-123"):
            ...     print("Project needs refresh")
            >>>
            >>> # Check if any project is stale
            >>> if manager.is_cache_stale():
            ...     print("Cache has stale data")
        """
        try:
            with self._lock:
                if project_id:
                    # Check specific project
                    project = self.repository.get_project(project_id)
                    if not project:
                        logger.warning(f"Project not found: {project_id}")
                        return True  # Treat missing as stale

                    if project.last_fetched is None:
                        return True

                    threshold = datetime.utcnow() - timedelta(minutes=self.ttl_minutes)
                    return project.last_fetched < threshold
                else:
                    # Check if any project is stale
                    stale_projects = self.repository.get_stale_projects(
                        self.ttl_minutes
                    )
                    return len(stale_projects) > 0
        except Exception as e:
            logger.error(f"Failed to check cache staleness: {e}", exc_info=True)
            return True  # Treat errors as stale to trigger refresh

    # =========================================================================
    # Marketplace Operations
    # =========================================================================

    def get_marketplace_entries(self, entry_type: Optional[str] = None) -> List[Any]:
        """Get cached marketplace entries with optional type filter.

        Args:
            entry_type: Optional artifact type filter (skill, command, etc.)

        Returns:
            List of MarketplaceEntry objects

        Example:
            >>> # Get all marketplace entries
            >>> all_entries = manager.get_marketplace_entries()
            >>>
            >>> # Get only skills
            >>> skills = manager.get_marketplace_entries(entry_type="skill")
        """
        try:
            with self._lock:
                entries = self.repository.list_marketplace_entries(
                    type_filter=entry_type
                )
                logger.debug(
                    f"Retrieved {len(entries)} marketplace entries (type={entry_type})"
                )
                return entries
        except Exception as e:
            logger.error(f"Failed to get marketplace entries: {e}", exc_info=True)
            return []

    def update_marketplace_cache(self, entries: List[Dict[str, Any]]) -> int:
        """Update marketplace cache with new entries.

        Upserts entries and removes stale ones (older than 24 hours).

        Args:
            entries: List of marketplace entry dicts with keys:
                - id (str): Unique entry identifier
                - name (str): Artifact name
                - type (str): Artifact type
                - url (str): URL to artifact
                - description (str, optional): Entry description
                - data (dict, optional): Additional data

        Returns:
            Count of entries updated

        Example:
            >>> entries = [
            ...     {
            ...         "id": "mkt-1",
            ...         "name": "awesome-skill",
            ...         "type": "skill",
            ...         "url": "https://github.com/user/skill",
            ...         "description": "An awesome skill",
            ...     }
            ... ]
            >>> count = manager.update_marketplace_cache(entries)
            >>> print(f"Updated {count} marketplace entries")
        """
        try:
            with self._lock:
                from skillmeat.cache.models import MarketplaceEntry
                import json

                count = 0
                for entry_data in entries:
                    # Create MarketplaceEntry object
                    entry = MarketplaceEntry(
                        id=entry_data["id"],
                        name=entry_data["name"],
                        type=entry_data["type"],
                        url=entry_data["url"],
                        description=entry_data.get("description"),
                        cached_at=datetime.utcnow(),
                    )

                    # Store additional data as JSON if provided
                    if "data" in entry_data and entry_data["data"] is not None:
                        entry.data = json.dumps(entry_data["data"])

                    # Upsert entry
                    self.repository.upsert_marketplace_entry(entry)
                    count += 1

                # Clean up stale entries (older than 24 hours)
                deleted = self.repository.delete_stale_marketplace_entries(
                    max_age_hours=24
                )
                logger.debug(f"Deleted {deleted} stale marketplace entries")

                logger.info(f"Updated {count} marketplace entries")
                return count
        except Exception as e:
            logger.error(f"Failed to update marketplace cache: {e}", exc_info=True)
            return 0

    def is_marketplace_cache_stale(self, ttl_hours: int = 24) -> bool:
        """Check if marketplace cache needs refresh (TTL-based).

        Args:
            ttl_hours: Time-to-live in hours (default 24 hours)

        Returns:
            True if marketplace cache is stale or empty, False if fresh

        Example:
            >>> if manager.is_marketplace_cache_stale():
            ...     print("Marketplace cache needs refresh")
        """
        try:
            with self._lock:
                # Get all marketplace entries
                entries = self.repository.list_marketplace_entries()

                # Empty cache is considered stale
                if not entries:
                    logger.debug("Marketplace cache is empty")
                    return True

                # Check if oldest entry is past TTL
                # If the oldest entry is stale, entire cache needs refresh
                threshold = datetime.utcnow() - timedelta(hours=ttl_hours)
                oldest_entry = min(entries, key=lambda e: e.cached_at)

                if oldest_entry.cached_at < threshold:
                    logger.debug(
                        f"Marketplace cache is stale (oldest entry: "
                        f"{oldest_entry.cached_at}, threshold: {threshold})"
                    )
                    return True

                logger.debug("Marketplace cache is fresh")
                return False
        except Exception as e:
            logger.error(
                f"Failed to check marketplace cache staleness: {e}", exc_info=True
            )
            return True  # Treat errors as stale to trigger refresh

    # =========================================================================
    # Thread Safety Helpers
    # =========================================================================

    @contextmanager
    def read_lock(self) -> Generator[None, None, None]:
        """Acquire read lock.

        With RLock, this is the same as write_lock (exclusive access).
        Included for API consistency and potential future optimization
        with ReadWriteLock.

        Yields:
            None

        Example:
            >>> with manager.read_lock():
            ...     projects = manager.get_projects()
        """
        with self._lock:
            yield

    @contextmanager
    def write_lock(self) -> Generator[None, None, None]:
        """Acquire exclusive write lock.

        Ensures thread-safe write operations.

        Yields:
            None

        Example:
            >>> with manager.write_lock():
            ...     manager.populate_projects(projects)
        """
        with self._lock:
            yield
