"""Data access layer for SkillMeat cache database.

This module provides the CacheRepository class which implements the Repository
pattern for low-level database operations. It abstracts SQLAlchemy session
management and provides CRUD operations for all cache entities.

The repository is used by the CacheManager (service layer) and provides:
- CRUD operations for Projects, Artifacts, Metadata, and Marketplace entries
- Batch operations for efficient bulk updates
- Transaction support with retry logic for SQLite
- Query optimization with eager loading
- Full error handling with custom exceptions

Usage:
    >>> from skillmeat.cache.repository import CacheRepository
    >>> repo = CacheRepository()
    >>>
    >>> # Get all active projects
    >>> projects = repo.get_projects_by_status('active')
    >>>
    >>> # Find outdated artifacts
    >>> outdated = repo.list_outdated_artifacts()
    >>>
    >>> # Transaction example
    >>> with repo.transaction() as session:
    ...     project = repo.create_project(project_obj)
    ...     artifact = repo.create_artifact(artifact_obj)

Architecture:
    - SQLAlchemy models defined in models.py
    - Session management per operation (create/close)
    - Context managers for transactions
    - Retry logic for SQLITE_BUSY errors
    - Comprehensive logging for debugging
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, cast

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, joinedload

from skillmeat.cache.models import (
    Artifact,
    ArtifactMetadata,
    CacheMetadata,
    MarketplaceEntry,
    Project,
    create_db_engine,
    create_tables,
)

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class CacheError(Exception):
    """Base exception for cache repository errors."""

    pass


class CacheNotFoundError(CacheError):
    """Raised when a requested entity is not found in the cache."""

    pass


class CacheConstraintError(CacheError):
    """Raised when a database constraint is violated (duplicate key, FK, etc.)."""

    pass


# =============================================================================
# Repository Implementation
# =============================================================================


class CacheRepository:
    """Repository for cache database operations.

    Provides low-level data access for Projects, Artifacts, Metadata, and
    Marketplace entries. Handles session management, transactions, and retry
    logic for SQLite operations.

    Attributes:
        db_path: Path to SQLite database file
        engine: SQLAlchemy engine for database connections

    Example:
        >>> repo = CacheRepository()
        >>>
        >>> # Create a project
        >>> project = Project(
        ...     id="proj-123",
        ...     name="My Project",
        ...     path="/path/to/project"
        ... )
        >>> created = repo.create_project(project)
        >>>
        >>> # Get project by path
        >>> found = repo.get_project_by_path("/path/to/project")
        >>>
        >>> # Update project status
        >>> updated = repo.update_project("proj-123", status="stale")
    """

    # Retry configuration for transient SQLite errors
    MAX_RETRIES = 3
    RETRY_DELAY_MS = 100

    def __init__(self, db_path: Optional[str] = None):
        """Initialize repository with database path.

        If db_path is None, uses default ~/.skillmeat/cache/cache.db.
        Creates database and tables if they don't exist.

        Args:
            db_path: Optional path to database file

        Example:
            >>> # Use default path
            >>> repo = CacheRepository()
            >>>
            >>> # Use custom path
            >>> repo = CacheRepository("/custom/path/cache.db")
        """
        # Resolve database path
        if db_path is None:
            self.db_path = Path.home() / ".skillmeat" / "cache" / "cache.db"
        else:
            self.db_path = Path(db_path)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        self.engine = create_db_engine(self.db_path)

        # Create tables if they don't exist
        create_tables(self.db_path)

        logger.debug(f"Initialized CacheRepository with database: {self.db_path}")

    # =========================================================================
    # Session Management
    # =========================================================================

    def _get_session(self) -> Session:
        """Create a new database session.

        Returns:
            SQLAlchemy Session instance

        Note:
            Sessions should be closed after use. Prefer using the
            transaction() context manager for automatic cleanup.
        """
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        return SessionLocal()

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for transactional operations.

        Automatically commits on success, rolls back on error, and closes
        the session. Includes retry logic for transient SQLite errors.

        Yields:
            SQLAlchemy Session instance

        Raises:
            CacheError: If operation fails after retries

        Example:
            >>> with repo.transaction() as session:
            ...     project = Project(id="p1", name="Test", path="/test")
            ...     session.add(project)
            ...     # Automatic commit on success
        """
        session = self._get_session()
        retries = 0

        while retries <= self.MAX_RETRIES:
            try:
                yield session
                session.commit()
                logger.debug("Transaction committed successfully")
                break
            except OperationalError as e:
                # Handle SQLITE_BUSY errors with retry
                if (
                    "database is locked" in str(e).lower()
                    and retries < self.MAX_RETRIES
                ):
                    retries += 1
                    delay = self.RETRY_DELAY_MS * retries
                    logger.warning(
                        f"Database locked, retrying in {delay}ms "
                        f"(attempt {retries}/{self.MAX_RETRIES})"
                    )
                    time.sleep(delay / 1000.0)
                    session.rollback()
                    continue
                else:
                    logger.error(f"Database operation failed: {e}")
                    session.rollback()
                    raise CacheError(f"Database operation failed: {e}") from e
            except Exception as e:
                logger.error(f"Transaction failed: {e}")
                session.rollback()
                raise
            finally:
                session.close()

    # =========================================================================
    # Project Operations
    # =========================================================================

    def create_project(self, project: Project) -> Project:
        """Create a new project in the cache.

        Args:
            project: Project object to create

        Returns:
            Created Project object with populated fields

        Raises:
            CacheConstraintError: If project with same ID or path already exists

        Example:
            >>> project = Project(
            ...     id="proj-123",
            ...     name="My Project",
            ...     path="/path/to/project",
            ...     status="active"
            ... )
            >>> created = repo.create_project(project)
        """
        session = self._get_session()
        try:
            session.add(project)
            session.commit()
            session.refresh(project)
            logger.debug(f"Created project: {project.id}")
            # Make object accessible after session close
            session.expunge(project)
            return project
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Project creation failed (duplicate key): {e}")
            raise CacheConstraintError(
                f"Project with ID {project.id} or path {project.path} already exists"
            ) from e
        finally:
            session.close()

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID.

        Args:
            project_id: Unique project identifier

        Returns:
            Project object or None if not found

        Example:
            >>> project = repo.get_project("proj-123")
            >>> if project:
            ...     print(f"Found: {project.name}")
        """
        session = self._get_session()
        try:
            project = (
                session.query(Project)
                .options(joinedload(Project.artifacts))
                .filter(Project.id == project_id)
                .first()
            )
            logger.debug(
                f"Retrieved project: {project_id} (found={project is not None})"
            )
            return project
        finally:
            session.close()

    def get_project_by_path(self, path: str) -> Optional[Project]:
        """Get project by filesystem path.

        Args:
            path: Absolute filesystem path to project

        Returns:
            Project object or None if not found

        Example:
            >>> project = repo.get_project_by_path("/home/user/my-project")
            >>> if project:
            ...     print(f"Project: {project.name}")
        """
        session = self._get_session()
        try:
            project = (
                session.query(Project)
                .options(joinedload(Project.artifacts))
                .filter(Project.path == path)
                .first()
            )
            logger.debug(
                f"Retrieved project by path: {path} (found={project is not None})"
            )
            return project
        finally:
            session.close()

    def list_projects(self, skip: int = 0, limit: int = 100) -> List[Project]:
        """List projects with pagination.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of Project objects

        Example:
            >>> # Get first 50 projects
            >>> projects = repo.list_projects(skip=0, limit=50)
            >>>
            >>> # Get next 50 projects
            >>> more = repo.list_projects(skip=50, limit=50)
        """
        session = self._get_session()
        try:
            projects = (
                session.query(Project)
                .options(joinedload(Project.artifacts))
                .offset(skip)
                .limit(limit)
                .all()
            )
            logger.debug(
                f"Listed {len(projects)} projects (skip={skip}, limit={limit})"
            )
            return projects
        finally:
            session.close()

    def update_project(self, project_id: str, **kwargs) -> Project:
        """Update project fields.

        Args:
            project_id: Unique project identifier
            **kwargs: Fields to update (name, path, status, etc.)

        Returns:
            Updated Project object

        Raises:
            CacheNotFoundError: If project not found

        Example:
            >>> project = repo.update_project(
            ...     "proj-123",
            ...     status="stale",
            ...     error_message="Failed to fetch artifacts"
            ... )
        """
        session = self._get_session()
        try:
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise CacheNotFoundError(f"Project not found: {project_id}")

            # Update fields
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)

            session.commit()
            session.refresh(project)
            logger.debug(f"Updated project: {project_id} with {kwargs}")
            return project
        except CacheNotFoundError:
            raise
        finally:
            session.close()

    def delete_project(self, project_id: str) -> bool:
        """Delete project and cascade to artifacts.

        Args:
            project_id: Unique project identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = repo.delete_project("proj-123")
            >>> if deleted:
            ...     print("Project deleted successfully")
        """
        session = self._get_session()
        try:
            project = session.query(Project).filter(Project.id == project_id).first()
            if not project:
                logger.debug(f"Delete failed - project not found: {project_id}")
                return False

            session.delete(project)
            session.commit()
            logger.debug(f"Deleted project: {project_id}")
            return True
        finally:
            session.close()

    def get_stale_projects(self, ttl_minutes: int = 360) -> List[Project]:
        """Get projects that haven't been refreshed within TTL.

        Args:
            ttl_minutes: Time-to-live in minutes (default 6 hours)

        Returns:
            List of stale Project objects

        Example:
            >>> # Get projects not refreshed in 6 hours
            >>> stale = repo.get_stale_projects(ttl_minutes=360)
            >>> for project in stale:
            ...     print(f"Stale: {project.name}")
        """
        session = self._get_session()
        try:
            threshold = datetime.utcnow() - timedelta(minutes=ttl_minutes)
            projects = (
                session.query(Project)
                .options(joinedload(Project.artifacts))
                .filter(
                    or_(
                        Project.last_fetched == None,
                        Project.last_fetched < threshold,
                    )
                )
                .all()
            )
            logger.debug(
                f"Found {len(projects)} stale projects (TTL={ttl_minutes}m, "
                f"threshold={threshold})"
            )
            return projects
        finally:
            session.close()

    def get_projects_by_status(self, status: str) -> List[Project]:
        """Get projects filtered by status.

        Args:
            status: Project status ('active', 'stale', or 'error')

        Returns:
            List of Project objects with matching status

        Example:
            >>> # Get all active projects
            >>> active = repo.get_projects_by_status('active')
            >>>
            >>> # Get all projects with errors
            >>> errors = repo.get_projects_by_status('error')
        """
        session = self._get_session()
        try:
            projects = (
                session.query(Project)
                .options(joinedload(Project.artifacts))
                .filter(Project.status == status)
                .all()
            )
            logger.debug(f"Found {len(projects)} projects with status={status}")
            return projects
        finally:
            session.close()

    # =========================================================================
    # Artifact Operations
    # =========================================================================

    def create_artifact(self, artifact: Artifact) -> Artifact:
        """Create a new artifact in the cache.

        Args:
            artifact: Artifact object to create

        Returns:
            Created Artifact object with populated fields

        Raises:
            CacheConstraintError: If artifact with same ID already exists
                                 or if project_id doesn't exist

        Example:
            >>> artifact = Artifact(
            ...     id="art-123",
            ...     project_id="proj-123",
            ...     name="my-skill",
            ...     type="skill",
            ...     deployed_version="1.0.0"
            ... )
            >>> created = repo.create_artifact(artifact)
        """
        session = self._get_session()
        try:
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            logger.debug(f"Created artifact: {artifact.id}")
            # Make object accessible after session close
            session.expunge(artifact)
            return artifact
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Artifact creation failed (constraint violation): {e}")
            raise CacheConstraintError(
                f"Artifact with ID {artifact.id} already exists or "
                f"project {artifact.project_id} not found"
            ) from e
        finally:
            session.close()

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID.

        Args:
            artifact_id: Unique artifact identifier

        Returns:
            Artifact object or None if not found

        Example:
            >>> artifact = repo.get_artifact("art-123")
            >>> if artifact:
            ...     print(f"Found: {artifact.name} ({artifact.type})")
        """
        session = self._get_session()
        try:
            artifact = (
                session.query(Artifact)
                .options(joinedload(Artifact.artifact_metadata))
                .filter(Artifact.id == artifact_id)
                .first()
            )
            logger.debug(
                f"Retrieved artifact: {artifact_id} (found={artifact is not None})"
            )
            return artifact
        finally:
            session.close()

    def list_artifacts_by_project(self, project_id: str) -> List[Artifact]:
        """Get all artifacts for a project.

        Args:
            project_id: Unique project identifier

        Returns:
            List of Artifact objects for the project

        Example:
            >>> artifacts = repo.list_artifacts_by_project("proj-123")
            >>> for artifact in artifacts:
            ...     print(f"{artifact.name}: {artifact.type}")
        """
        session = self._get_session()
        try:
            artifacts = (
                session.query(Artifact)
                .options(joinedload(Artifact.artifact_metadata))
                .filter(Artifact.project_id == project_id)
                .all()
            )
            logger.debug(f"Listed {len(artifacts)} artifacts for project: {project_id}")
            return artifacts
        finally:
            session.close()

    def get_artifacts_by_type(self, artifact_type: str) -> List[Artifact]:
        """Get all artifacts of a specific type.

        Args:
            artifact_type: Type of artifact ('skill', 'command', 'agent', etc.)

        Returns:
            List of Artifact objects with matching type

        Example:
            >>> skills = repo.get_artifacts_by_type('skill')
            >>> commands = repo.get_artifacts_by_type('command')
        """
        session = self._get_session()
        try:
            artifacts = (
                session.query(Artifact)
                .options(joinedload(Artifact.artifact_metadata))
                .filter(Artifact.type == artifact_type)
                .all()
            )
            logger.debug(f"Found {len(artifacts)} artifacts of type={artifact_type}")
            return artifacts
        finally:
            session.close()

    def list_outdated_artifacts(self) -> List[Artifact]:
        """Get all artifacts flagged as outdated.

        Returns:
            List of Artifact objects where is_outdated=True

        Example:
            >>> outdated = repo.list_outdated_artifacts()
            >>> for artifact in outdated:
            ...     print(f"{artifact.name}: {artifact.deployed_version} -> "
            ...           f"{artifact.upstream_version}")
        """
        session = self._get_session()
        try:
            artifacts = (
                session.query(Artifact)
                .options(joinedload(Artifact.artifact_metadata))
                .filter(Artifact.is_outdated == True)
                .all()
            )
            logger.debug(f"Found {len(artifacts)} outdated artifacts")
            return artifacts
        finally:
            session.close()

    def update_artifact(self, artifact_id: str, **kwargs) -> Artifact:
        """Update artifact fields.

        Args:
            artifact_id: Unique artifact identifier
            **kwargs: Fields to update (name, type, version, etc.)

        Returns:
            Updated Artifact object

        Raises:
            CacheNotFoundError: If artifact not found

        Example:
            >>> artifact = repo.update_artifact(
            ...     "art-123",
            ...     deployed_version="1.1.0",
            ...     is_outdated=False
            ... )
        """
        session = self._get_session()
        try:
            artifact = (
                session.query(Artifact).filter(Artifact.id == artifact_id).first()
            )
            if not artifact:
                raise CacheNotFoundError(f"Artifact not found: {artifact_id}")

            # Update fields
            for key, value in kwargs.items():
                if hasattr(artifact, key):
                    setattr(artifact, key, value)

            session.commit()
            session.refresh(artifact)
            logger.debug(f"Updated artifact: {artifact_id} with {kwargs}")
            return artifact
        except CacheNotFoundError:
            raise
        finally:
            session.close()

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete artifact and cascade to metadata.

        Args:
            artifact_id: Unique artifact identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = repo.delete_artifact("art-123")
            >>> if deleted:
            ...     print("Artifact deleted successfully")
        """
        session = self._get_session()
        try:
            artifact = (
                session.query(Artifact).filter(Artifact.id == artifact_id).first()
            )
            if not artifact:
                logger.debug(f"Delete failed - artifact not found: {artifact_id}")
                return False

            session.delete(artifact)
            session.commit()
            logger.debug(f"Deleted artifact: {artifact_id}")
            return True
        finally:
            session.close()

    def bulk_insert_artifacts(self, artifacts: List[Artifact]) -> List[Artifact]:
        """Bulk insert multiple artifacts efficiently.

        Args:
            artifacts: List of Artifact objects to insert

        Returns:
            List of created Artifact objects

        Raises:
            CacheConstraintError: If any artifact violates constraints

        Example:
            >>> artifacts = [
            ...     Artifact(id="a1", project_id="p1", name="skill1", type="skill"),
            ...     Artifact(id="a2", project_id="p1", name="skill2", type="skill"),
            ... ]
            >>> created = repo.bulk_insert_artifacts(artifacts)
        """
        try:
            with self.transaction() as session:
                session.bulk_save_objects(artifacts)
                session.flush()
                logger.debug(f"Bulk inserted {len(artifacts)} artifacts")
                return artifacts
        except IntegrityError as e:
            logger.error(f"Bulk insert failed (constraint violation): {e}")
            raise CacheConstraintError(
                f"One or more artifacts violate constraints"
            ) from e

    def bulk_update_artifacts(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update multiple artifacts efficiently.

        Args:
            updates: List of dicts with 'id' and fields to update

        Returns:
            Number of artifacts updated

        Example:
            >>> updates = [
            ...     {"id": "a1", "deployed_version": "1.1.0", "is_outdated": False},
            ...     {"id": "a2", "deployed_version": "2.0.0", "is_outdated": False},
            ... ]
            >>> count = repo.bulk_update_artifacts(updates)
            >>> print(f"Updated {count} artifacts")
        """
        session = self._get_session()
        try:
            count = 0
            for update_dict in updates:
                # Make a copy to avoid modifying input
                update = update_dict.copy()
                artifact_id = update.pop("id")
                result = (
                    session.query(Artifact)
                    .filter(Artifact.id == artifact_id)
                    .update(update, synchronize_session=False)
                )
                count += result

            session.commit()
            logger.debug(f"Bulk updated {count} artifacts")
            return count
        finally:
            session.close()

    def search_artifacts(
        self,
        query: str,
        project_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
    ) -> List[Artifact]:
        """Search artifacts by name or description.

        Args:
            query: Search query string (matched against name)
            project_id: Optional project ID filter
            artifact_type: Optional artifact type filter

        Returns:
            List of matching Artifact objects

        Example:
            >>> # Search all artifacts
            >>> results = repo.search_artifacts("docker")
            >>>
            >>> # Search within a project
            >>> results = repo.search_artifacts("api", project_id="proj-123")
            >>>
            >>> # Search for specific type
            >>> results = repo.search_artifacts("test", artifact_type="skill")
        """
        session = self._get_session()
        try:
            # Build base query
            q = session.query(Artifact).options(joinedload(Artifact.artifact_metadata))

            # Add name filter
            q = q.filter(Artifact.name.like(f"%{query}%"))

            # Add optional filters
            if project_id:
                q = q.filter(Artifact.project_id == project_id)
            if artifact_type:
                q = q.filter(Artifact.type == artifact_type)

            artifacts = q.all()
            logger.debug(
                f"Search found {len(artifacts)} artifacts "
                f"(query={query}, project={project_id}, type={artifact_type})"
            )
            return artifacts
        finally:
            session.close()

    # =========================================================================
    # Metadata Operations
    # =========================================================================

    def get_artifact_metadata(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """Get metadata for an artifact.

        Args:
            artifact_id: Unique artifact identifier

        Returns:
            ArtifactMetadata object or None if not found

        Example:
            >>> metadata = repo.get_artifact_metadata("art-123")
            >>> if metadata:
            ...     print(f"Description: {metadata.description}")
            ...     print(f"Tags: {metadata.get_tags_list()}")
        """
        session = self._get_session()
        try:
            metadata = (
                session.query(ArtifactMetadata)
                .filter(ArtifactMetadata.artifact_id == artifact_id)
                .first()
            )
            logger.debug(
                f"Retrieved metadata for artifact: {artifact_id} "
                f"(found={metadata is not None})"
            )
            return metadata
        finally:
            session.close()

    def set_artifact_metadata(
        self, artifact_id: str, metadata: Dict[str, Any]
    ) -> ArtifactMetadata:
        """Set or update metadata for an artifact.

        Args:
            artifact_id: Unique artifact identifier
            metadata: Dictionary with metadata fields

        Returns:
            Created or updated ArtifactMetadata object

        Example:
            >>> metadata = repo.set_artifact_metadata(
            ...     "art-123",
            ...     {
            ...         "description": "A useful skill",
            ...         "tags": ["automation", "testing"],
            ...         "aliases": ["test-skill", "tester"],
            ...     }
            ... )
        """
        session = self._get_session()
        try:
            # Check if metadata exists
            existing = (
                session.query(ArtifactMetadata)
                .filter(ArtifactMetadata.artifact_id == artifact_id)
                .first()
            )

            if existing:
                # Update existing
                for key, value in metadata.items():
                    if key == "tags" and isinstance(value, list):
                        existing.set_tags_list(value)
                    elif key == "aliases" and isinstance(value, list):
                        existing.set_aliases_list(value)
                    elif hasattr(existing, key):
                        setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                logger.debug(f"Updated metadata for artifact: {artifact_id}")
                return existing
            else:
                # Create new
                new_metadata = ArtifactMetadata(artifact_id=artifact_id)
                for key, value in metadata.items():
                    if key == "tags" and isinstance(value, list):
                        new_metadata.set_tags_list(value)
                    elif key == "aliases" and isinstance(value, list):
                        new_metadata.set_aliases_list(value)
                    elif hasattr(new_metadata, key):
                        setattr(new_metadata, key, value)

                session.add(new_metadata)
                session.commit()
                session.refresh(new_metadata)
                logger.debug(f"Created metadata for artifact: {artifact_id}")
                return new_metadata
        finally:
            session.close()

    def get_cache_metadata(self, key: str) -> Optional[str]:
        """Get cache system metadata by key.

        Args:
            key: Metadata key

        Returns:
            Metadata value string or None if not found

        Example:
            >>> version = repo.get_cache_metadata("schema_version")
            >>> last_vacuum = repo.get_cache_metadata("last_vacuum")
        """
        session = self._get_session()
        try:
            metadata = (
                session.query(CacheMetadata).filter(CacheMetadata.key == key).first()
            )
            value = metadata.value if metadata else None
            logger.debug(f"Retrieved cache metadata: {key}={value}")
            return value
        finally:
            session.close()

    def set_cache_metadata(self, key: str, value: str) -> None:
        """Set cache system metadata.

        Args:
            key: Metadata key
            value: Metadata value (stored as string)

        Example:
            >>> repo.set_cache_metadata("last_vacuum", "2024-11-29T10:00:00Z")
            >>> repo.set_cache_metadata("total_projects", "42")
        """
        session = self._get_session()
        try:
            # Check if exists
            existing = (
                session.query(CacheMetadata).filter(CacheMetadata.key == key).first()
            )

            if existing:
                existing.value = value
            else:
                new_metadata = CacheMetadata(key=key, value=value)
                session.add(new_metadata)

            session.commit()
            logger.debug(f"Set cache metadata: {key}={value}")
        finally:
            session.close()

    def delete_cache_metadata(self, key: str) -> bool:
        """Delete cache system metadata.

        Args:
            key: Metadata key

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = repo.delete_cache_metadata("temp_key")
        """
        session = self._get_session()
        try:
            metadata = (
                session.query(CacheMetadata).filter(CacheMetadata.key == key).first()
            )
            if not metadata:
                logger.debug(f"Delete failed - metadata not found: {key}")
                return False

            session.delete(metadata)
            session.commit()
            logger.debug(f"Deleted cache metadata: {key}")
            return True
        finally:
            session.close()

    # =========================================================================
    # Marketplace Operations
    # =========================================================================

    def get_marketplace_entry(self, entry_id: str) -> Optional[MarketplaceEntry]:
        """Get marketplace entry by ID.

        Args:
            entry_id: Unique marketplace entry identifier

        Returns:
            MarketplaceEntry object or None if not found

        Example:
            >>> entry = repo.get_marketplace_entry("mkt-123")
            >>> if entry:
            ...     print(f"Found: {entry.name} ({entry.type})")
        """
        session = self._get_session()
        try:
            entry = (
                session.query(MarketplaceEntry)
                .filter(MarketplaceEntry.id == entry_id)
                .first()
            )
            logger.debug(
                f"Retrieved marketplace entry: {entry_id} (found={entry is not None})"
            )
            return entry
        finally:
            session.close()

    def list_marketplace_entries(
        self, type_filter: Optional[str] = None
    ) -> List[MarketplaceEntry]:
        """List marketplace entries with optional type filter.

        Args:
            type_filter: Optional artifact type filter

        Returns:
            List of MarketplaceEntry objects

        Example:
            >>> # Get all marketplace entries
            >>> all_entries = repo.list_marketplace_entries()
            >>>
            >>> # Get only skills
            >>> skills = repo.list_marketplace_entries(type_filter="skill")
        """
        session = self._get_session()
        try:
            q = session.query(MarketplaceEntry)
            if type_filter:
                q = q.filter(MarketplaceEntry.type == type_filter)

            entries = q.all()
            logger.debug(
                f"Listed {len(entries)} marketplace entries (type={type_filter})"
            )
            return entries
        finally:
            session.close()

    def upsert_marketplace_entry(self, entry: MarketplaceEntry) -> MarketplaceEntry:
        """Insert or update marketplace entry.

        Args:
            entry: MarketplaceEntry object to upsert

        Returns:
            Created or updated MarketplaceEntry object

        Example:
            >>> entry = MarketplaceEntry(
            ...     id="mkt-123",
            ...     name="awesome-skill",
            ...     type="skill",
            ...     url="https://github.com/user/repo/skill"
            ... )
            >>> upserted = repo.upsert_marketplace_entry(entry)
        """
        session = self._get_session()
        try:
            # Check if exists
            existing = (
                session.query(MarketplaceEntry)
                .filter(MarketplaceEntry.id == entry.id)
                .first()
            )

            if existing:
                # Update existing
                existing.name = entry.name
                existing.type = entry.type
                existing.url = entry.url
                existing.description = entry.description
                existing.cached_at = datetime.utcnow()
                existing.data = entry.data
                session.commit()
                session.refresh(existing)
                logger.debug(f"Updated marketplace entry: {entry.id}")
                return existing
            else:
                # Insert new
                session.add(entry)
                session.commit()
                session.refresh(entry)
                logger.debug(f"Created marketplace entry: {entry.id}")
                return entry
        finally:
            session.close()

    def delete_stale_marketplace_entries(self, max_age_hours: int = 24) -> int:
        """Delete marketplace entries older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before entry is considered stale

        Returns:
            Number of entries deleted

        Example:
            >>> # Delete entries older than 24 hours
            >>> count = repo.delete_stale_marketplace_entries(max_age_hours=24)
            >>> print(f"Deleted {count} stale marketplace entries")
        """
        session = self._get_session()
        try:
            threshold = datetime.utcnow() - timedelta(hours=max_age_hours)
            result = (
                session.query(MarketplaceEntry)
                .filter(MarketplaceEntry.cached_at < threshold)
                .delete()
            )
            session.commit()
            logger.debug(
                f"Deleted {result} stale marketplace entries "
                f"(threshold={threshold}, max_age={max_age_hours}h)"
            )
            return result
        finally:
            session.close()
