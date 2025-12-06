"""Repository pattern implementation for marketplace entities.

This module provides repository classes for marketplace data access following
the Repository pattern. These repositories abstract SQLAlchemy session management
and provide type-safe CRUD operations for marketplace-related entities.

Single-User Architecture Decision:
    SkillMeat is designed as a PERSONAL COLLECTION MANAGER - single user only.
    SQLite does not support PostgreSQL Row-Level Security (RLS) natively.

    Current Implementation:
        - No user_id scoping (single user assumed)
        - Repository methods operate on all data
        - Session management per-operation pattern

    Future Multi-Tenancy Extension Path:
        If multi-user support is needed in the future:
        1. Add user_id column to MarketplaceSource and MarketplaceCatalogEntry models
        2. Add user_id parameter to all repository methods
        3. Filter queries by user_id in BaseRepository._apply_user_scope()
        4. Migrate to PostgreSQL for proper RLS support

        Example extension pattern:
            class MarketplaceSourceRepository(BaseRepository[MarketplaceSource]):
                def list_all(self, user_id: Optional[str] = None) -> List[MarketplaceSource]:
                    session = self._get_session()
                    try:
                        query = session.query(MarketplaceSource)
                        if user_id:  # Apply scoping if multi-tenant
                            query = query.filter(MarketplaceSource.user_id == user_id)
                        return query.all()
                    finally:
                        session.close()

Repositories:
    - BaseRepository: Common CRUD patterns and session management
    - MarketplaceSourceRepository: GitHub repository source management
    - MarketplaceCatalogRepository: Discovered artifact management

Usage:
    >>> from skillmeat.cache.repositories import (
    ...     MarketplaceSourceRepository,
    ...     MarketplaceCatalogRepository
    ... )
    >>>
    >>> # Create repositories
    >>> source_repo = MarketplaceSourceRepository()
    >>> catalog_repo = MarketplaceCatalogRepository()
    >>>
    >>> # CRUD operations
    >>> source = source_repo.get_by_repo_url("https://github.com/user/repo")
    >>> entries = catalog_repo.list_by_source(source.id)
    >>>
    >>> # Bulk operations
    >>> new_entries = [entry1, entry2, entry3]
    >>> created = catalog_repo.bulk_create(new_entries)
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from skillmeat.cache.models import (
    Base,
    MarketplaceCatalogEntry,
    MarketplaceSource,
    create_db_engine,
    create_tables,
)

# Configure logging
logger = logging.getLogger(__name__)

# Generic type for ORM models
T = TypeVar("T", bound=Base)


# =============================================================================
# Custom Exceptions
# =============================================================================


class RepositoryError(Exception):
    """Base exception for repository errors."""

    pass


class NotFoundError(RepositoryError):
    """Raised when a requested entity is not found."""

    pass


class ConstraintError(RepositoryError):
    """Raised when a database constraint is violated."""

    pass


# =============================================================================
# Base Repository
# =============================================================================


class BaseRepository(Generic[T]):
    """Base repository with common CRUD patterns and session management.

    Provides reusable patterns for data access operations that can be
    inherited by specific repository implementations. Handles session
    lifecycle, transaction management, and error handling.

    Type Parameters:
        T: SQLAlchemy ORM model type

    Attributes:
        db_path: Path to SQLite database file
        engine: SQLAlchemy engine for database connections
        model_class: ORM model class for type-safe operations

    Example:
        >>> class UserRepository(BaseRepository[User]):
        ...     def __init__(self, db_path: Optional[str] = None):
        ...         super().__init__(db_path, User)
        ...
        ...     def get_by_email(self, email: str) -> Optional[User]:
        ...         session = self._get_session()
        ...         try:
        ...             return session.query(User).filter_by(email=email).first()
        ...         finally:
        ...             session.close()
    """

    # Retry configuration for transient SQLite errors
    MAX_RETRIES = 3
    RETRY_DELAY_MS = 100

    def __init__(
        self, db_path: Optional[str | Path] = None, model_class: Type[T] = None
    ):
        """Initialize repository with database path and model class.

        Args:
            db_path: Optional path to database file (uses default if None)
            model_class: SQLAlchemy ORM model class
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

        # Store model class for type-safe operations
        self.model_class = model_class

        logger.debug(
            f"Initialized {self.__class__.__name__} with database: {self.db_path}"
        )

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
        the session. Provides automatic cleanup and error handling.

        Yields:
            SQLAlchemy Session instance

        Raises:
            RepositoryError: If operation fails

        Example:
            >>> with repo.transaction() as session:
            ...     entity = MyModel(id="123", name="Test")
            ...     session.add(entity)
            ...     # Automatic commit on success
        """
        session = self._get_session()
        try:
            yield session
            session.commit()
            logger.debug(f"Transaction committed successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise RepositoryError(f"Transaction failed: {e}") from e
        finally:
            session.close()


# =============================================================================
# MarketplaceSource Repository
# =============================================================================


class MarketplaceSourceRepository(BaseRepository[MarketplaceSource]):
    """Repository for GitHub repository source management.

    Provides CRUD operations for MarketplaceSource entities, which represent
    GitHub repositories that can be scanned for Claude Code artifacts.

    Methods:
        - get_by_id: Retrieve source by ID
        - get_by_repo_url: Retrieve source by repository URL (unique)
        - list_all: List all sources
        - create: Create new source
        - update: Update existing source
        - delete: Delete source (cascade deletes catalog entries)

    Example:
        >>> repo = MarketplaceSourceRepository()
        >>>
        >>> # Create a new source
        >>> source = MarketplaceSource(
        ...     id=str(uuid.uuid4()),
        ...     repo_url="https://github.com/anthropics/anthropic-quickstarts",
        ...     owner="anthropics",
        ...     repo_name="anthropic-quickstarts",
        ...     ref="main",
        ...     trust_level="official",
        ... )
        >>> created = repo.create(source)
        >>>
        >>> # Find by URL
        >>> found = repo.get_by_repo_url("https://github.com/anthropics/anthropic-quickstarts")
        >>>
        >>> # Update scan status
        >>> found.scan_status = "success"
        >>> found.last_sync_at = datetime.utcnow()
        >>> updated = repo.update(found)
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialize MarketplaceSource repository.

        Args:
            db_path: Optional path to database file
        """
        super().__init__(db_path, MarketplaceSource)

    def get_by_id(self, source_id: str) -> Optional[MarketplaceSource]:
        """Retrieve marketplace source by ID.

        Args:
            source_id: Unique source identifier

        Returns:
            MarketplaceSource instance or None if not found
        """
        session = self._get_session()
        try:
            return session.query(MarketplaceSource).filter_by(id=source_id).first()
        finally:
            session.close()

    def get_by_repo_url(self, repo_url: str) -> Optional[MarketplaceSource]:
        """Retrieve marketplace source by repository URL.

        Repository URLs are unique per source. This is the primary lookup
        method for checking if a source already exists.

        Args:
            repo_url: Full GitHub repository URL

        Returns:
            MarketplaceSource instance or None if not found

        Example:
            >>> source = repo.get_by_repo_url("https://github.com/user/repo")
        """
        session = self._get_session()
        try:
            return session.query(MarketplaceSource).filter_by(repo_url=repo_url).first()
        finally:
            session.close()

    def list_all(self) -> List[MarketplaceSource]:
        """List all marketplace sources.

        Returns:
            List of all MarketplaceSource instances

        Note:
            Single-user architecture - no scoping applied.
            For multi-tenancy, add user_id parameter and filter.
        """
        session = self._get_session()
        try:
            return session.query(MarketplaceSource).all()
        finally:
            session.close()

    def create(self, source: MarketplaceSource) -> MarketplaceSource:
        """Create a new marketplace source.

        Args:
            source: MarketplaceSource instance to create

        Returns:
            Created MarketplaceSource instance

        Raises:
            ConstraintError: If repo_url already exists (unique constraint)

        Example:
            >>> source = MarketplaceSource(
            ...     id=str(uuid.uuid4()),
            ...     repo_url="https://github.com/user/repo",
            ...     owner="user",
            ...     repo_name="repo",
            ... )
            >>> created = repo.create(source)
        """
        session = self._get_session()
        try:
            session.add(source)
            session.commit()
            session.refresh(source)
            logger.info(f"Created marketplace source: {source.id} ({source.repo_url})")
            return source
        except IntegrityError as e:
            session.rollback()
            raise ConstraintError(f"Source with repo_url already exists: {e}") from e
        finally:
            session.close()

    def update(self, source: MarketplaceSource) -> MarketplaceSource:
        """Update an existing marketplace source.

        Args:
            source: MarketplaceSource instance with updated values

        Returns:
            Updated MarketplaceSource instance

        Raises:
            NotFoundError: If source does not exist

        Example:
            >>> source = repo.get_by_id("source-123")
            >>> source.scan_status = "success"
            >>> source.artifact_count = 5
            >>> updated = repo.update(source)
        """
        session = self._get_session()
        try:
            # Ensure entity exists
            existing = session.query(MarketplaceSource).filter_by(id=source.id).first()
            if not existing:
                raise NotFoundError(f"Source not found: {source.id}")

            # Merge changes and get the merged instance
            merged = session.merge(source)
            session.commit()
            session.refresh(merged)
            logger.info(f"Updated marketplace source: {source.id}")
            return merged
        finally:
            session.close()

    def delete(self, source_id: str) -> bool:
        """Delete a marketplace source.

        This performs a hard delete (actually removes from database).
        Cascade deletes all associated catalog entries.

        Args:
            source_id: Unique source identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = repo.delete("source-123")
        """
        session = self._get_session()
        try:
            source = session.query(MarketplaceSource).filter_by(id=source_id).first()
            if not source:
                return False

            session.delete(source)
            session.commit()
            logger.info(f"Deleted marketplace source: {source_id}")
            return True
        finally:
            session.close()


# =============================================================================
# MarketplaceCatalog Repository
# =============================================================================


class MarketplaceCatalogRepository(BaseRepository[MarketplaceCatalogEntry]):
    """Repository for discovered artifact management.

    Provides CRUD and query operations for MarketplaceCatalogEntry entities,
    which represent artifacts detected during GitHub repository scanning.

    Methods:
        - get_by_id: Retrieve entry by ID
        - list_by_source: List entries from a specific source
        - list_by_status: List entries with a specific status
        - find_by_upstream_url: Find entry by upstream URL (deduplication)
        - bulk_create: Efficiently create multiple entries
        - update_status: Update entry import status

    Example:
        >>> repo = MarketplaceCatalogRepository()
        >>>
        >>> # List all new artifacts from a source
        >>> new_artifacts = repo.list_by_source("source-123")
        >>>
        >>> # Bulk create entries
        >>> entries = [entry1, entry2, entry3]
        >>> created = repo.bulk_create(entries)
        >>>
        >>> # Mark as imported
        >>> repo.update_status(entry.id, "imported")
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialize MarketplaceCatalog repository.

        Args:
            db_path: Optional path to database file
        """
        super().__init__(db_path, MarketplaceCatalogEntry)

    def get_by_id(self, entry_id: str) -> Optional[MarketplaceCatalogEntry]:
        """Retrieve catalog entry by ID.

        Args:
            entry_id: Unique catalog entry identifier

        Returns:
            MarketplaceCatalogEntry instance or None if not found
        """
        session = self._get_session()
        try:
            return session.query(MarketplaceCatalogEntry).filter_by(id=entry_id).first()
        finally:
            session.close()

    def list_by_source(self, source_id: str) -> List[MarketplaceCatalogEntry]:
        """List all catalog entries from a specific source.

        Args:
            source_id: Marketplace source identifier

        Returns:
            List of MarketplaceCatalogEntry instances

        Example:
            >>> entries = repo.list_by_source("source-123")
            >>> for entry in entries:
            ...     print(f"{entry.name} ({entry.artifact_type}): {entry.status}")
        """
        session = self._get_session()
        try:
            return (
                session.query(MarketplaceCatalogEntry)
                .filter_by(source_id=source_id)
                .all()
            )
        finally:
            session.close()

    def list_by_status(self, status: str) -> List[MarketplaceCatalogEntry]:
        """List all catalog entries with a specific status.

        Args:
            status: Import status ("new", "updated", "removed", "imported")

        Returns:
            List of MarketplaceCatalogEntry instances

        Example:
            >>> # Find all new artifacts not yet imported
            >>> new_entries = repo.list_by_status("new")
        """
        session = self._get_session()
        try:
            return session.query(MarketplaceCatalogEntry).filter_by(status=status).all()
        finally:
            session.close()

    def find_by_upstream_url(self, url: str) -> Optional[MarketplaceCatalogEntry]:
        """Find catalog entry by upstream URL.

        Used for deduplication - check if an artifact URL has already been
        discovered before creating a new catalog entry.

        Args:
            url: Full URL to artifact in repository

        Returns:
            MarketplaceCatalogEntry instance or None if not found

        Example:
            >>> existing = repo.find_by_upstream_url(
            ...     "https://github.com/user/repo/blob/main/skills/my-skill"
            ... )
            >>> if existing:
            ...     print("Already cataloged!")
        """
        session = self._get_session()
        try:
            return (
                session.query(MarketplaceCatalogEntry)
                .filter_by(upstream_url=url)
                .first()
            )
        finally:
            session.close()

    def bulk_create(
        self, entries: List[MarketplaceCatalogEntry]
    ) -> List[MarketplaceCatalogEntry]:
        """Create multiple catalog entries efficiently.

        Uses bulk insert for performance when creating many entries at once
        (e.g., after scanning a large repository).

        Args:
            entries: List of MarketplaceCatalogEntry instances to create

        Returns:
            List of created MarketplaceCatalogEntry instances

        Raises:
            RepositoryError: If bulk insert fails

        Example:
            >>> entries = [
            ...     MarketplaceCatalogEntry(id=str(uuid.uuid4()), ...),
            ...     MarketplaceCatalogEntry(id=str(uuid.uuid4()), ...),
            ... ]
            >>> created = repo.bulk_create(entries)
        """
        if not entries:
            return []

        session = self._get_session()
        try:
            session.bulk_save_objects(entries)
            session.commit()
            logger.info(f"Bulk created {len(entries)} catalog entries")
            return entries
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Bulk create failed: {e}") from e
        finally:
            session.close()

    def update_status(self, entry_id: str, status: str) -> bool:
        """Update catalog entry import status.

        Args:
            entry_id: Unique catalog entry identifier
            status: New status ("new", "updated", "removed", "imported")

        Returns:
            True if updated, False if not found

        Example:
            >>> # Mark entry as imported
            >>> repo.update_status("entry-123", "imported")
        """
        session = self._get_session()
        try:
            entry = (
                session.query(MarketplaceCatalogEntry).filter_by(id=entry_id).first()
            )
            if not entry:
                return False

            entry.status = status
            if status == "imported":
                entry.import_date = datetime.utcnow()

            session.commit()
            logger.info(f"Updated catalog entry status: {entry_id} -> {status}")
            return True
        finally:
            session.close()
