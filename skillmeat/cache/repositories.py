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

import json
import logging
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, func, or_, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, joinedload

from skillmeat.cache.models import (
    Artifact,
    ArtifactTag,
    Base,
    CollectionArtifact,
    DeploymentProfile,
    DeploymentSet,
    DeploymentSetMember,
    DeploymentSetTag,
    MarketplaceCatalogEntry,
    MarketplaceSource,
    Tag,
    create_db_engine,
    create_tables,
)
from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import (
    DEFAULT_ARTIFACT_PATH_MAP,
    default_project_config_filenames,
)

# Configure logging
logger = logging.getLogger(__name__)

# Generic type for ORM models
T = TypeVar("T", bound=Base)


# =============================================================================
# FTS5 Search Weights
# =============================================================================

# FTS5 bm25 column weights for search ranking
# Column indices in catalog_fts: 0=name(unindexed), 1=type(unindexed), 2=title,
#                                3=description, 4=search_text, 5=tags, 6=deep
# Higher weight = higher importance when ranking search results
SEARCH_WEIGHT_TITLE = 10.0
SEARCH_WEIGHT_DESCRIPTION = 5.0
SEARCH_WEIGHT_SEARCH_TEXT = 2.0
SEARCH_WEIGHT_TAGS = 3.0
SEARCH_WEIGHT_DEEP = 1.0


# =============================================================================
# Merge Result
# =============================================================================


@dataclass
class MergeResult:
    """Result of a catalog entry merge operation.

    Tracks counts for different merge outcomes and identifies entries
    that had SHA changes while preserving import status.

    Attributes:
        inserted_count: Number of new entries inserted
        updated_count: Number of existing entries updated (non-imported/excluded)
        preserved_count: Number of imported/excluded entries that were updated
        removed_count: Number of entries marked as removed (no longer detected)
        updated_imports: Entry IDs of imported artifacts that have SHA changes
    """

    inserted_count: int
    updated_count: int
    preserved_count: int
    removed_count: int
    updated_imports: List[str]


# =============================================================================
# Pagination Result
# =============================================================================


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result container.

    Provides cursor-based pagination for efficient querying of large datasets
    without the offset/limit performance penalty.

    Attributes:
        items: List of items for the current page
        next_cursor: Cursor value for fetching next page (None if no more)
        has_more: True if more items exist after this page
        total: Optional total count of items (expensive to compute)
        snippets: Optional dict mapping item ID to snippet data (FTS5 search only)

    Example:
        >>> # First page
        >>> result = repo.list_paginated(limit=50)
        >>> for item in result.items:
        ...     print(item.name)
        >>>
        >>> # Next page
        >>> if result.has_more:
        ...     next_result = repo.list_paginated(limit=50, cursor=result.next_cursor)
    """

    items: List[T]
    next_cursor: Optional[str]
    has_more: bool
    total: Optional[int] = None  # Optional total count
    snippets: Optional[Dict[str, Dict[str, Optional[str]]]] = None  # FTS5 snippets


@dataclass
class CatalogDiff:
    """Result of comparing old and new catalog entries.

    Used to identify changes when scanning a marketplace source and comparing
    against existing catalog entries. Enables efficient bulk updates.

    Attributes:
        new: Entries to create (in new_entries but not in DB)
        updated: Entries to update as (existing_id, new_data) pairs
        removed: Entry IDs to mark as removed (in DB but not in new_entries)
        unchanged: Entry IDs that haven't changed (matching URL and SHA)

    Example:
        >>> diff = repo.compare_catalogs("source-123", new_entries)
        >>> print(f"New: {len(diff.new)}, Updated: {len(diff.updated)}")
        >>> for entry_data in diff.new:
        ...     # Create new catalog entry
        ...     pass
    """

    new: List[Dict[str, Any]]  # Entries to create
    updated: List[tuple[str, Dict[str, Any]]]  # (existing_id, new_data) pairs
    removed: List[str]  # Entry IDs to mark as removed
    unchanged: List[str]  # Entry IDs that haven't changed


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

        # Create any missing base tables (backward compatibility)
        # Note: Alembic migrations run once at app startup via CacheManager
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
        except RepositoryError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise RepositoryError(f"Transaction failed: {e}") from e
        finally:
            session.close()


# =============================================================================
# Transaction Contexts
# =============================================================================


class ScanUpdateContext:
    """Context for scan update operations within a transaction.

    Provides helper methods for atomically updating both MarketplaceSource
    and MarketplaceCatalogEntry records during a scan completion.

    The session is managed by MarketplaceTransactionHandler - do not close it
    within this context.

    Attributes:
        session: Active SQLAlchemy session
        source_id: ID of the marketplace source being updated

    Example:
        >>> # Used within scan_update_transaction context manager
        >>> with handler.scan_update_transaction(source_id) as ctx:
        ...     ctx.update_source_status("success", artifact_count=5)
        ...     ctx.replace_catalog_entries(new_entries)
    """

    def __init__(self, session: Session, source_id: str):
        """Initialize scan update context.

        Args:
            session: Active SQLAlchemy session
            source_id: ID of the marketplace source being updated
        """
        self.session = session
        self.source_id = source_id

    def update_source_status(
        self,
        status: str,
        artifact_count: Optional[int] = None,
        error_message: Optional[str] = None,
        ref: Optional[str] = None,
    ) -> None:
        """Update source scan status and metadata.

        Updates scan_status, last_sync_at, artifact_count, and optionally
        last_error and ref for a marketplace source.

        Args:
            status: New scan status ("pending", "scanning", "success", "error")
            artifact_count: Number of artifacts discovered (None to leave unchanged)
            error_message: Error message if status is "error" (None clears error)
            ref: Actual git ref used during scan (None to leave unchanged). When
                the scanner falls back to a different default branch (e.g. the
                source stores "main" but the repo uses "master"), pass the
                resolved ref here so subsequent imports use the correct branch.

        Raises:
            NotFoundError: If source does not exist

        Example:
            >>> # Mark scan as successful
            >>> ctx.update_source_status("success", artifact_count=10)
            >>>
            >>> # Mark scan as failed
            >>> ctx.update_source_status("error", error_message="API rate limit")
            >>>
            >>> # Mark scan as successful and persist branch fallback
            >>> ctx.update_source_status("success", artifact_count=10, ref="master")
        """
        source = (
            self.session.query(MarketplaceSource).filter_by(id=self.source_id).first()
        )
        if not source:
            raise NotFoundError(f"Source not found: {self.source_id}")

        # Update scan status
        source.scan_status = status
        source.last_sync_at = datetime.utcnow()

        # Update artifact count if provided
        if artifact_count is not None:
            source.artifact_count = artifact_count

        # Update error message (None clears it)
        source.last_error = error_message

        # Update ref if provided (branch fallback detected during scan)
        if ref is not None:
            source.ref = ref
            logger.info(f"Updated source {self.source_id} ref to '{ref}'")

        logger.info(
            f"Updated source {self.source_id}: status={status}, "
            f"count={artifact_count}, error={error_message}"
        )

    def replace_catalog_entries(self, entries: List[MarketplaceCatalogEntry]) -> int:
        """Delete existing entries and insert new ones atomically.

        Removes all existing catalog entries for this source and replaces
        them with the provided list. This is the typical pattern after
        a full repository scan.

        Args:
            entries: List of new MarketplaceCatalogEntry instances

        Returns:
            Number of entries inserted

        Example:
            >>> new_entries = [entry1, entry2, entry3]
            >>> count = ctx.replace_catalog_entries(new_entries)
            >>> print(f"Replaced with {count} new entries")
        """
        # Delete existing entries for this source
        deleted_count = (
            self.session.query(MarketplaceCatalogEntry)
            .filter_by(source_id=self.source_id)
            .delete(synchronize_session=False)
        )
        logger.debug(
            f"Deleted {deleted_count} existing entries for source {self.source_id}"
        )

        # Insert new entries
        if entries:
            self.session.bulk_save_objects(entries)
            logger.info(
                f"Inserted {len(entries)} new entries for source {self.source_id}"
            )

        return len(entries)

    def merge_catalog_entries(
        self, entries: List[MarketplaceCatalogEntry]
    ) -> MergeResult:
        """Merge new catalog entries with existing ones, preserving import metadata.

        Unlike replace_catalog_entries(), this method preserves import-related
        metadata for entries that have been imported or excluded. It matches
        entries by upstream_url (primary) or path + source_id (fallback).

        Merge behavior by existing entry status:
            - "imported": Preserves status, import_date, import_id, excluded_at,
              excluded_reason. Updates detection metadata (SHA, scores, etc.)
            - "excluded": Preserves all exclusion data. Updates detection metadata.
            - "new"/"updated": Full update with new entry data.
            - Not in new entries: Marked as "removed" (not deleted).

        Args:
            entries: List of newly detected MarketplaceCatalogEntry instances

        Returns:
            MergeResult with counts and list of imported entry IDs with SHA changes

        Example:
            >>> result = ctx.merge_catalog_entries(detected_entries)
            >>> print(f"Inserted: {result.inserted_count}")
            >>> print(f"Updated: {result.updated_count}")
            >>> print(f"Preserved: {result.preserved_count}")
            >>> print(f"Removed: {result.removed_count}")
            >>> if result.updated_imports:
            ...     print(f"Imports with changes: {result.updated_imports}")
        """
        # Build lookup dicts of new entries for O(1) matching
        new_by_url: Dict[str, MarketplaceCatalogEntry] = {}
        new_by_path: Dict[str, MarketplaceCatalogEntry] = {}
        new_by_type_name: Dict[str, MarketplaceCatalogEntry] = {}
        for entry in entries:
            new_by_url[entry.upstream_url] = entry
            # Fallback key: path (unique within a source)
            new_by_path[entry.path] = entry
            # Secondary fallback: artifact_type:name (stable across URL changes)
            type_name_key = f"{entry.artifact_type}:{entry.name}"
            new_by_type_name[type_name_key] = entry

        # Get existing entries for this source
        existing_entries = (
            self.session.query(MarketplaceCatalogEntry)
            .filter_by(source_id=self.source_id)
            .all()
        )

        # Track which new entries have been matched
        matched_urls: set = set()
        matched_paths: set = set()
        matched_type_names: set = set()

        # Counters
        inserted_count = 0
        updated_count = 0
        preserved_count = 0
        removed_count = 0
        updated_imports: List[str] = []

        now = datetime.utcnow()

        # Process existing entries
        for existing in existing_entries:
            # Try to find matching new entry (priority: URL > path > type:name)
            new_entry = new_by_url.get(existing.upstream_url)
            if new_entry:
                matched_urls.add(existing.upstream_url)
            else:
                # Fallback 1: match by path
                new_entry = new_by_path.get(existing.path)
                if new_entry:
                    matched_paths.add(existing.path)
                else:
                    # Fallback 2: match by artifact_type:name (handles URL changes)
                    type_name_key = f"{existing.artifact_type}:{existing.name}"
                    new_entry = new_by_type_name.get(type_name_key)
                    if new_entry:
                        matched_type_names.add(type_name_key)
                        logger.debug(
                            f"Matched entry by type:name fallback: {existing.id} ({existing.name})"
                        )

            if new_entry is None:
                # Entry no longer detected - mark as removed
                if existing.status != "removed":
                    existing.status = "removed"
                    existing.updated_at = now
                    removed_count += 1
                    logger.debug(
                        f"Marked entry as removed: {existing.id} ({existing.name})"
                    )
                continue

            # Track SHA changes for imported entries
            sha_changed = (
                existing.detected_sha is not None
                and new_entry.detected_sha is not None
                and existing.detected_sha != new_entry.detected_sha
            )

            if existing.status in ("imported", "excluded"):
                # Preserve import/exclusion metadata, update detection data
                if sha_changed and existing.status == "imported":
                    updated_imports.append(existing.id)

                # Update detection metadata and URLs (URLs may change due to ref fixes)
                existing.detected_sha = new_entry.detected_sha
                existing.confidence_score = new_entry.confidence_score
                existing.raw_score = new_entry.raw_score
                existing.score_breakdown = new_entry.score_breakdown
                existing.detected_at = new_entry.detected_at
                existing.detected_version = new_entry.detected_version
                existing.path_segments = new_entry.path_segments
                existing.upstream_url = (
                    new_entry.upstream_url
                )  # Update URL (may have changed)
                existing.path = new_entry.path  # Update path for consistency
                existing.updated_at = now

                # Update search metadata even for preserved entries
                existing.title = new_entry.title
                existing.description = new_entry.description
                existing.search_tags = new_entry.search_tags
                existing.search_text = new_entry.search_text

                # Preserve: status, import_date, import_id, excluded_at, excluded_reason
                preserved_count += 1
                logger.debug(
                    f"Preserved {existing.status} entry: {existing.id} ({existing.name})"
                    + (f" [SHA changed]" if sha_changed else "")
                )
            else:
                # Full update for non-imported/excluded entries
                existing.artifact_type = new_entry.artifact_type
                existing.name = new_entry.name
                existing.path = new_entry.path
                existing.upstream_url = new_entry.upstream_url
                existing.detected_version = new_entry.detected_version
                existing.detected_sha = new_entry.detected_sha
                existing.detected_at = new_entry.detected_at
                existing.confidence_score = new_entry.confidence_score
                existing.raw_score = new_entry.raw_score
                existing.score_breakdown = new_entry.score_breakdown
                existing.path_segments = new_entry.path_segments
                existing.status = "updated" if existing.status != "new" else "new"
                existing.updated_at = now

                # Update search metadata (frontmatter extraction)
                existing.title = new_entry.title
                existing.description = new_entry.description
                existing.search_tags = new_entry.search_tags
                existing.search_text = new_entry.search_text

                updated_count += 1
                logger.debug(f"Updated entry: {existing.id} ({existing.name})")

        # Insert new entries that weren't matched
        for entry in entries:
            url_matched = entry.upstream_url in matched_urls
            path_matched = entry.path in matched_paths
            type_name_key = f"{entry.artifact_type}:{entry.name}"
            type_name_matched = type_name_key in matched_type_names

            if not url_matched and not path_matched and not type_name_matched:
                # New entry - insert it
                self.session.add(entry)
                inserted_count += 1
                logger.debug(f"Inserted new entry: {entry.id} ({entry.name})")

        logger.info(
            f"Merged catalog entries for source {self.source_id}: "
            f"inserted={inserted_count}, updated={updated_count}, "
            f"preserved={preserved_count}, removed={removed_count}"
        )

        if updated_imports:
            logger.info(
                f"Found {len(updated_imports)} imported entries with SHA changes: "
                f"{updated_imports[:5]}{'...' if len(updated_imports) > 5 else ''}"
            )

        return MergeResult(
            inserted_count=inserted_count,
            updated_count=updated_count,
            preserved_count=preserved_count,
            removed_count=removed_count,
            updated_imports=updated_imports,
        )

    def update_entry_statuses(self, status_updates: Dict[str, str]) -> int:
        """Bulk update entry statuses.

        Updates status for multiple catalog entries efficiently. Useful for
        marking specific entries as updated, removed, etc.

        Args:
            status_updates: Dictionary mapping entry_id -> new_status

        Returns:
            Number of entries updated

        Example:
            >>> status_updates = {
            ...     "entry-1": "updated",
            ...     "entry-2": "removed",
            ...     "entry-3": "updated"
            ... }
            >>> count = ctx.update_entry_statuses(status_updates)
        """
        if not status_updates:
            return 0

        updated_count = 0
        for entry_id, new_status in status_updates.items():
            result = (
                self.session.query(MarketplaceCatalogEntry)
                .filter_by(id=entry_id, source_id=self.source_id)
                .update(
                    {"status": new_status, "updated_at": datetime.utcnow()},
                    synchronize_session=False,
                )
            )
            updated_count += result

        logger.info(
            f"Updated {updated_count} entry statuses for source {self.source_id}"
        )
        return updated_count


class ImportContext:
    """Context for import operations within a transaction.

    Provides helper methods for tracking artifact imports from catalog
    to collection, including status updates and error tracking.

    The session is managed by MarketplaceTransactionHandler - do not close it
    within this context.

    Attributes:
        session: Active SQLAlchemy session
        source_id: ID of the marketplace source (for validation)

    Example:
        >>> # Used within import_transaction context manager
        >>> with handler.import_transaction(source_id) as ctx:
        ...     ctx.mark_imported(["entry-1", "entry-2"], import_id="imp-123")
        ...     ctx.mark_failed(["entry-3"], error="Validation failed")
    """

    def __init__(self, session: Session, source_id: str):
        """Initialize import context.

        Args:
            session: Active SQLAlchemy session
            source_id: ID of the marketplace source
        """
        self.session = session
        self.source_id = source_id

    def mark_imported(self, entry_ids: List[str], import_id: str) -> int:
        """Mark entries as imported with timestamp and import reference.

        Updates status to "imported", sets import_date, and stores the
        import_id in metadata for traceability.

        Args:
            entry_ids: List of catalog entry IDs to mark as imported
            import_id: Unique identifier for this import operation

        Returns:
            Number of entries updated

        Example:
            >>> import_id = str(uuid.uuid4())
            >>> count = ctx.mark_imported(["entry-1", "entry-2"], import_id)
        """
        if not entry_ids:
            return 0

        updated_count = 0
        now = datetime.utcnow()

        for entry_id in entry_ids:
            entry = (
                self.session.query(MarketplaceCatalogEntry)
                .filter_by(id=entry_id, source_id=self.source_id)
                .first()
            )
            if entry:
                entry.import_id = import_id  # Set the actual column
                entry.status = "imported"
                entry.import_date = now
                entry.updated_at = now

                # Store import_id in metadata using the model's helper method
                metadata = entry.get_metadata_dict() or {}
                metadata["import_id"] = import_id
                entry.set_metadata_dict(metadata)

                updated_count += 1

        logger.info(
            f"Marked {updated_count} entries as imported (import_id={import_id})"
        )
        return updated_count

    def mark_failed(self, entry_ids: List[str], error: str) -> int:
        """Mark entries as failed import with error message.

        Stores error information in metadata_json while leaving status
        unchanged. This allows retrying imports without losing the
        original detection status.

        Args:
            entry_ids: List of catalog entry IDs that failed to import
            error: Error message describing the failure

        Returns:
            Number of entries updated

        Example:
            >>> count = ctx.mark_failed(
            ...     ["entry-1"],
            ...     error="Schema validation failed: missing required field"
            ... )
        """
        if not entry_ids:
            return 0

        updated_count = 0
        now = datetime.utcnow()

        for entry_id in entry_ids:
            entry = (
                self.session.query(MarketplaceCatalogEntry)
                .filter_by(id=entry_id, source_id=self.source_id)
                .first()
            )
            if entry:
                # Store error in metadata without changing status using the model's helper method
                metadata = entry.get_metadata_dict() or {}
                metadata["import_error"] = error
                metadata["import_error_at"] = now.isoformat()
                entry.set_metadata_dict(metadata)

                entry.updated_at = now
                updated_count += 1

        logger.warning(f"Marked {updated_count} entries as failed import: {error}")
        return updated_count


# =============================================================================
# Transaction Handler
# =============================================================================


class MarketplaceTransactionHandler:
    """Coordinates transactional operations across marketplace repositories.

    Use this for operations that need to update both MarketplaceSource and
    MarketplaceCatalogEntry atomically (e.g., after a scan completes).

    This handler ensures that complex multi-table operations either fully
    succeed or fully rollback on error, maintaining database consistency.

    Attributes:
        db_path: Path to SQLite database file
        engine: SQLAlchemy engine for database connections

    Example:
        >>> handler = MarketplaceTransactionHandler()
        >>> with handler.scan_update_transaction(source_id) as ctx:
        ...     ctx.update_source_status("success", artifact_count=5)
        ...     ctx.replace_catalog_entries(new_entries)
        ...     # Automatic commit on success, rollback on error
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialize transaction handler with database path.

        Args:
            db_path: Optional path to database file (uses default if None)
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

        logger.debug(f"Initialized MarketplaceTransactionHandler: {self.db_path}")

    def _get_session(self) -> Session:
        """Create a new database session.

        Returns:
            SQLAlchemy Session instance
        """
        from sqlalchemy.orm import sessionmaker

        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        return SessionLocal()

    @contextmanager
    def scan_update_transaction(
        self, source_id: str
    ) -> Generator[ScanUpdateContext, None, None]:
        """Context manager for updating source and catalog after a scan.

        Provides atomic update of:
        - MarketplaceSource.scan_status, last_sync_at, artifact_count, last_error
        - MarketplaceCatalogEntry bulk delete and recreate

        On error, rolls back all changes. On success, commits all changes.

        Args:
            source_id: The marketplace source being updated

        Yields:
            ScanUpdateContext with helper methods

        Raises:
            RepositoryError: If transaction fails

        Example:
            >>> handler = MarketplaceTransactionHandler()
            >>> with handler.scan_update_transaction("source-123") as ctx:
            ...     # Update source metadata
            ...     ctx.update_source_status("success", artifact_count=10)
            ...
            ...     # Replace catalog entries atomically
            ...     new_entries = scan_repository(source)
            ...     ctx.replace_catalog_entries(new_entries)
            ...
            ...     # Transaction commits automatically on success
        """
        session = self._get_session()
        try:
            logger.debug(f"Starting scan update transaction for source {source_id}")

            # Yield context for operation
            context = ScanUpdateContext(session, source_id)
            yield context

            # Commit on success
            session.commit()
            logger.info(f"Scan update transaction committed for source {source_id}")

        except IntegrityError as e:
            session.rollback()
            logger.error(f"Scan update transaction failed (integrity): {e}")
            raise RepositoryError(
                f"Scan update failed due to integrity constraint: {e}"
            ) from e

        except OperationalError as e:
            session.rollback()
            logger.error(f"Scan update transaction failed (operational): {e}")
            raise RepositoryError(
                f"Scan update failed due to database error: {e}"
            ) from e

        except Exception as e:
            session.rollback()
            logger.error(f"Scan update transaction failed: {e}")
            raise RepositoryError(f"Scan update transaction failed: {e}") from e

        finally:
            session.close()

    @contextmanager
    def import_transaction(
        self, source_id: str
    ) -> Generator[ImportContext, None, None]:
        """Context manager for importing artifacts from catalog to collection.

        Tracks which entries are being imported and updates their status
        atomically. Use this when processing multiple catalog entries
        in a single import operation.

        Args:
            source_id: The marketplace source being imported from

        Yields:
            ImportContext with helper methods

        Raises:
            RepositoryError: If transaction fails

        Example:
            >>> handler = MarketplaceTransactionHandler()
            >>> with handler.import_transaction("source-123") as ctx:
            ...     import_id = str(uuid.uuid4())
            ...
            ...     # Try to import entries
            ...     for entry_id in entries_to_import:
            ...         try:
            ...             import_artifact(entry_id)
            ...             successful_ids.append(entry_id)
            ...         except Exception as e:
            ...             failed_ids.append(entry_id)
            ...
            ...     # Update statuses atomically
            ...     ctx.mark_imported(successful_ids, import_id)
            ...     ctx.mark_failed(failed_ids, str(e))
            ...
            ...     # Transaction commits automatically
        """
        session = self._get_session()
        try:
            logger.debug(f"Starting import transaction for source {source_id}")

            # Yield context for operation
            context = ImportContext(session, source_id)
            yield context

            # Commit on success
            session.commit()
            logger.info(f"Import transaction committed for source {source_id}")

        except IntegrityError as e:
            session.rollback()
            logger.error(f"Import transaction failed (integrity): {e}")
            raise RepositoryError(
                f"Import failed due to integrity constraint: {e}"
            ) from e

        except OperationalError as e:
            session.rollback()
            logger.error(f"Import transaction failed (operational): {e}")
            raise RepositoryError(f"Import failed due to database error: {e}") from e

        except Exception as e:
            session.rollback()
            logger.error(f"Import transaction failed: {e}")
            raise RepositoryError(f"Import transaction failed: {e}") from e

        finally:
            session.close()


# =============================================================================
# MarketplaceSource Repository
# =============================================================================


class MarketplaceSourceRepository(BaseRepository[MarketplaceSource]):
    """Repository for GitHub repository source management.

    Provides CRUD operations for MarketplaceSource entities, which represent
    GitHub repositories that can be scanned for Claude Code artifacts.

    Supported Fields:
        Core fields (required):
            - id, repo_url, owner, repo_name, ref

        User-provided metadata:
            - description: User-provided description (max 500 chars)
            - notes: Internal notes/documentation (max 2000 chars)

        GitHub-fetched metadata:
            - repo_description: Description from GitHub API (max 2000 chars)
            - repo_readme: README content from GitHub (up to 50KB)
            - tags: List of tags for categorization (JSON-serialized)

        Scan results:
            - scan_status: Current scan status
            - artifact_count: Total count of discovered artifacts
            - counts_by_type: Dict mapping artifact type to count (JSON-serialized)
            - last_sync_at, last_error

    Methods:
        - get_by_id: Retrieve source by ID
        - get_by_repo_url: Retrieve source by repository URL (unique)
        - list_all: List all sources
        - create: Create new source (with optional tags/counts_by_type kwargs)
        - update: Update existing source (with optional tags/counts_by_type kwargs)
        - update_fields: Partial update by source_id (convenience method)
        - delete: Delete source (cascade deletes catalog entries)

    Example:
        >>> repo = MarketplaceSourceRepository()
        >>>
        >>> # Create a new source with GitHub metadata
        >>> source = MarketplaceSource(
        ...     id=str(uuid.uuid4()),
        ...     repo_url="https://github.com/anthropics/anthropic-quickstarts",
        ...     owner="anthropics",
        ...     repo_name="anthropic-quickstarts",
        ...     ref="main",
        ...     trust_level="official",
        ...     repo_description="Official Anthropic quickstart examples",
        ...     repo_readme="# Anthropic Quickstarts\n\n...",
        ... )
        >>> created = repo.create(
        ...     source,
        ...     tags=["official", "anthropic"],
        ...     counts_by_type={"skill": 5},
        ... )
        >>>
        >>> # Find by URL
        >>> found = repo.get_by_repo_url("https://github.com/anthropics/anthropic-quickstarts")
        >>>
        >>> # Partial update with update_fields
        >>> updated = repo.update_fields(
        ...     found.id,
        ...     scan_status="success",
        ...     artifact_count=10,
        ...     counts_by_type={"skill": 7, "command": 3},
        ... )
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

    def create(
        self,
        source: MarketplaceSource,
        *,
        tags: Optional[List[str]] = None,
        counts_by_type: Optional[Dict[str, int]] = None,
    ) -> MarketplaceSource:
        """Create a new marketplace source.

        Args:
            source: MarketplaceSource instance to create. Can include:
                - repo_description: Description fetched from GitHub API
                - repo_readme: README content from GitHub
                - tags: Will be overridden if tags kwarg is provided
                - counts_by_type: Will be overridden if counts_by_type kwarg is provided
            tags: Optional list of tags (serialized via set_tags_list())
            counts_by_type: Optional dict mapping artifact type to count
                (serialized via set_counts_by_type_dict())

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
            ...     repo_description="A great repo for Claude artifacts",
            ...     repo_readme="# My Repo\n\nThis repo contains...",
            ... )
            >>> created = repo.create(
            ...     source,
            ...     tags=["productivity", "coding"],
            ...     counts_by_type={"skill": 5, "command": 2},
            ... )
        """
        # Apply serialized fields if provided as kwargs
        if tags is not None:
            source.set_tags_list(tags)
        if counts_by_type is not None:
            source.set_counts_by_type_dict(counts_by_type)

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

    def update(
        self,
        source: MarketplaceSource,
        *,
        tags: Optional[List[str]] = None,
        counts_by_type: Optional[Dict[str, int]] = None,
    ) -> MarketplaceSource:
        """Update an existing marketplace source.

        Args:
            source: MarketplaceSource instance with updated values. Can include:
                - repo_description: Description fetched from GitHub API
                - repo_readme: README content from GitHub
                - tags: Will be overridden if tags kwarg is provided
                - counts_by_type: Will be overridden if counts_by_type kwarg is provided
            tags: Optional list of tags to set (serialized via set_tags_list())
            counts_by_type: Optional dict mapping artifact type to count
                (serialized via set_counts_by_type_dict())

        Returns:
            Updated MarketplaceSource instance

        Raises:
            NotFoundError: If source does not exist

        Example:
            >>> source = repo.get_by_id("source-123")
            >>> source.scan_status = "success"
            >>> source.artifact_count = 5
            >>> source.repo_description = "Updated description from GitHub"
            >>> updated = repo.update(
            ...     source,
            ...     tags=["updated", "verified"],
            ...     counts_by_type={"skill": 10, "command": 3},
            ... )
        """
        # Apply serialized fields if provided as kwargs
        if tags is not None:
            source.set_tags_list(tags)
        if counts_by_type is not None:
            source.set_counts_by_type_dict(counts_by_type)

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

    def update_fields(
        self,
        source_id: str,
        *,
        repo_description: Optional[str] = None,
        repo_readme: Optional[str] = None,
        tags: Optional[List[str]] = None,
        counts_by_type: Optional[Dict[str, int]] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        scan_status: Optional[str] = None,
        artifact_count: Optional[int] = None,
        last_sync_at: Optional[datetime] = None,
        last_error: Optional[str] = None,
    ) -> MarketplaceSource:
        """Update specific fields on a marketplace source without full ORM object.

        This is a convenience method for partial updates. Only provided fields
        are updated; None values are ignored (not set to NULL).

        Args:
            source_id: Unique source identifier
            repo_description: Description fetched from GitHub API (max 2000 chars)
            repo_readme: README content from GitHub (up to 50KB)
            tags: List of tags for categorization (serialized to JSON)
            counts_by_type: Dict mapping artifact type to count (serialized to JSON)
            description: User-provided description (max 500 chars)
            notes: Internal notes/documentation (max 2000 chars)
            scan_status: Scan status ("pending", "scanning", "success", "error")
            artifact_count: Cached count of discovered artifacts
            last_sync_at: Timestamp of last successful scan
            last_error: Last error message if scan failed

        Returns:
            Updated MarketplaceSource instance

        Raises:
            NotFoundError: If source does not exist

        Example:
            >>> # Update GitHub metadata after fetching from API
            >>> updated = repo.update_fields(
            ...     "source-123",
            ...     repo_description="Official Claude Code skills repository",
            ...     repo_readme="# Anthropic Skills\n\nThis repo contains...",
            ...     tags=["official", "anthropic", "skills"],
            ... )
            >>>
            >>> # Update after successful scan
            >>> updated = repo.update_fields(
            ...     "source-123",
            ...     scan_status="success",
            ...     artifact_count=15,
            ...     counts_by_type={"skill": 10, "command": 3, "agent": 2},
            ...     last_sync_at=datetime.utcnow(),
            ... )
        """
        session = self._get_session()
        try:
            source = session.query(MarketplaceSource).filter_by(id=source_id).first()
            if not source:
                raise NotFoundError(f"Source not found: {source_id}")

            # Update simple fields if provided
            if repo_description is not None:
                source.repo_description = repo_description
            if repo_readme is not None:
                source.repo_readme = repo_readme
            if description is not None:
                source.description = description
            if notes is not None:
                source.notes = notes
            if scan_status is not None:
                source.scan_status = scan_status
            if artifact_count is not None:
                source.artifact_count = artifact_count
            if last_sync_at is not None:
                source.last_sync_at = last_sync_at
            if last_error is not None:
                source.last_error = last_error

            # Update JSON-serialized fields using helper methods
            if tags is not None:
                source.set_tags_list(tags)
            if counts_by_type is not None:
                source.set_counts_by_type_dict(counts_by_type)

            session.commit()
            session.refresh(source)
            logger.info(f"Updated fields on marketplace source: {source_id}")
            return source
        finally:
            session.close()

    # =========================================================================
    # REPO-001: Enhanced Query Methods
    # =========================================================================

    def list_paginated(
        self, limit: int = 50, cursor: Optional[str] = None
    ) -> PaginatedResult[MarketplaceSource]:
        """List marketplace sources with cursor-based pagination.

        Uses ID-based cursor pagination for stable, efficient paging through
        large result sets without the performance penalty of OFFSET.

        Args:
            limit: Maximum number of items per page (default: 50)
            cursor: Cursor from previous page (None for first page)

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag

        Example:
            >>> # First page
            >>> result = repo.list_paginated(limit=50)
            >>> for source in result.items:
            ...     print(source.repo_url)
            >>>
            >>> # Next page
            >>> if result.has_more:
            ...     next_result = repo.list_paginated(limit=50, cursor=result.next_cursor)
        """
        session = self._get_session()
        try:
            query = session.query(MarketplaceSource)

            # Apply cursor filter if provided
            if cursor:
                query = query.filter(MarketplaceSource.id > cursor)

            # Order by ID for stable pagination
            query = query.order_by(MarketplaceSource.id)

            # Fetch limit + 1 to check if more items exist
            items = query.limit(limit + 1).all()

            # Determine if more items exist
            has_more = len(items) > limit
            if has_more:
                items = items[:limit]

            # Generate next cursor from last item's ID
            next_cursor = items[-1].id if items and has_more else None

            logger.debug(
                f"Listed {len(items)} sources (cursor={cursor}, has_more={has_more})"
            )

            return PaginatedResult(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
            )
        finally:
            session.close()

    def list_by_scan_status(self, status: str) -> List[MarketplaceSource]:
        """List marketplace sources by scan status.

        Args:
            status: Scan status filter ("pending", "scanning", "success", "error")

        Returns:
            List of MarketplaceSource instances with matching status

        Example:
            >>> # Find all sources that failed to scan
            >>> failed = repo.list_by_scan_status("error")
            >>> for source in failed:
            ...     print(f"{source.repo_url}: {source.last_error}")
        """
        session = self._get_session()
        try:
            sources = (
                session.query(MarketplaceSource)
                .filter_by(scan_status=status)
                .order_by(MarketplaceSource.updated_at.desc())
                .all()
            )
            logger.debug(f"Found {len(sources)} sources with status '{status}'")
            return sources
        finally:
            session.close()

    def list_needs_rescan(self, hours: int = 24) -> List[MarketplaceSource]:
        """List marketplace sources that need rescanning.

        Identifies sources that haven't been successfully scanned in the
        specified time period, useful for periodic refresh jobs.

        Args:
            hours: Time threshold in hours (default: 24)

        Returns:
            List of MarketplaceSource instances needing rescan

        Example:
            >>> # Find sources not scanned in 48 hours
            >>> stale = repo.list_needs_rescan(hours=48)
            >>> for source in stale:
            ...     print(f"Rescan needed: {source.repo_url}")
        """
        session = self._get_session()
        try:
            threshold = datetime.utcnow() - timedelta(hours=hours)

            # Sources that need rescanning are those where:
            # 1. Never synced (last_sync_at is NULL), OR
            # 2. Last sync older than threshold, OR
            # 3. Last scan resulted in error
            sources = (
                session.query(MarketplaceSource)
                .filter(
                    or_(
                        MarketplaceSource.last_sync_at.is_(None),
                        MarketplaceSource.last_sync_at < threshold,
                        MarketplaceSource.scan_status == "error",
                    )
                )
                .order_by(
                    MarketplaceSource.last_sync_at.asc().nullsfirst()
                )  # Never-scanned first
                .all()
            )

            logger.debug(
                f"Found {len(sources)} sources needing rescan "
                f"(threshold: {hours} hours)"
            )
            return sources
        finally:
            session.close()

    def upsert(self, source: MarketplaceSource) -> MarketplaceSource:
        """Create or update a marketplace source by repo_url.

        Performs an upsert operation: creates if doesn't exist, updates if it does.
        Uses repo_url as the unique identifier for matching.

        Args:
            source: MarketplaceSource instance to create or update

        Returns:
            Created or updated MarketplaceSource instance

        Example:
            >>> source = MarketplaceSource(
            ...     id=str(uuid.uuid4()),
            ...     repo_url="https://github.com/user/repo",
            ...     owner="user",
            ...     repo_name="repo",
            ...     trust_level="basic",
            ... )
            >>> result = repo.upsert(source)
            >>> # If exists, updates; if new, creates
        """
        session = self._get_session()
        try:
            # Check if source exists by repo_url
            existing = (
                session.query(MarketplaceSource)
                .filter_by(repo_url=source.repo_url)
                .first()
            )

            if existing:
                # Update existing source (preserve ID)
                source.id = existing.id
                merged = session.merge(source)
                session.commit()
                session.refresh(merged)
                logger.info(
                    f"Updated marketplace source: {merged.id} ({merged.repo_url})"
                )
                return merged
            else:
                # Create new source
                session.add(source)
                session.commit()
                session.refresh(source)
                logger.info(
                    f"Created marketplace source: {source.id} ({source.repo_url})"
                )
                return source
        except IntegrityError as e:
            session.rollback()
            raise ConstraintError(f"Upsert failed due to constraint: {e}") from e
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

    def reset_import_status(
        self, entry_id: str, source_id: str
    ) -> Optional[MarketplaceCatalogEntry]:
        """Reset a catalog entry's import status to allow re-import.

        Sets status back to 'new', clears import_date, and removes import_id
        from metadata. This allows an artifact to be re-imported after deletion.

        Args:
            entry_id: Unique catalog entry identifier
            source_id: Source ID for validation

        Returns:
            Updated MarketplaceCatalogEntry if found and reset, None if not found

        Example:
            >>> # Reset entry to allow re-import
            >>> entry = repo.reset_import_status("entry-123", "source-456")
            >>> if entry:
            ...     print(f"Entry {entry.name} reset to status: {entry.status}")
        """
        session = self._get_session()
        try:
            entry = (
                session.query(MarketplaceCatalogEntry)
                .filter_by(id=entry_id, source_id=source_id)
                .first()
            )
            if not entry:
                logger.warning(
                    f"Catalog entry not found for reset: {entry_id} (source: {source_id})"
                )
                return None

            # Reset status to 'new'
            entry.status = "new"
            entry.import_date = None
            entry.updated_at = datetime.utcnow()

            # Remove import_id from metadata
            metadata = entry.get_metadata_dict() or {}
            if "import_id" in metadata:
                del metadata["import_id"]
            entry.set_metadata_dict(metadata)

            session.commit()
            session.refresh(entry)
            logger.info(f"Reset catalog entry import status: {entry_id} -> new")
            return entry
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to reset import status for {entry_id}: {e}")
            raise
        finally:
            session.close()

    def find_by_import_id(self, import_id: str) -> Optional[MarketplaceCatalogEntry]:
        """Find catalog entry by import_id in metadata.

        Useful for finding the catalog entry linked to an imported artifact.

        Args:
            import_id: Import ID stored in metadata

        Returns:
            MarketplaceCatalogEntry if found, None otherwise

        Example:
            >>> entry = repo.find_by_import_id("imp-abc-123")
        """
        session = self._get_session()
        try:
            # Search for entries where metadata contains the import_id
            # Since metadata is JSON, we use LIKE for SQLite compatibility
            entries = (
                session.query(MarketplaceCatalogEntry)
                .filter(
                    MarketplaceCatalogEntry.status == "imported",
                    MarketplaceCatalogEntry.metadata_json.like(
                        f'%"import_id": "{import_id}"%'
                    ),
                )
                .all()
            )

            # Verify the match by parsing metadata
            for entry in entries:
                metadata = entry.get_metadata_dict() or {}
                if metadata.get("import_id") == import_id:
                    return entry

            return None
        finally:
            session.close()

    def find_by_artifact_name_and_type(
        self, name: str, artifact_type: str, source_id: Optional[str] = None
    ) -> Optional[MarketplaceCatalogEntry]:
        """Find catalog entry by artifact name and type.

        Useful for finding the catalog entry that matches an artifact
        being deleted from the collection.

        Args:
            name: Artifact name
            artifact_type: Artifact type (skill, command, agent, etc.)
            source_id: Optional source ID to filter by

        Returns:
            MarketplaceCatalogEntry if found, None otherwise
        """
        session = self._get_session()
        try:
            query = session.query(MarketplaceCatalogEntry).filter(
                MarketplaceCatalogEntry.name == name,
                MarketplaceCatalogEntry.artifact_type == artifact_type,
                MarketplaceCatalogEntry.status == "imported",
            )
            if source_id:
                query = query.filter(MarketplaceCatalogEntry.source_id == source_id)

            return query.first()
        finally:
            session.close()

    # =========================================================================
    # REPO-002: Enhanced Query Methods
    # =========================================================================

    def list_paginated(
        self,
        source_id: Optional[str] = None,
        status: Optional[str] = None,
        artifact_type: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedResult[MarketplaceCatalogEntry]:
        """List catalog entries with cursor-based pagination and filtering.

        Uses ID-based cursor pagination for efficient querying. Supports
        optional filtering by source, status, and artifact type.

        Args:
            source_id: Optional source ID filter
            status: Optional status filter ("new", "updated", "removed", "imported")
            artifact_type: Optional artifact type filter
            limit: Maximum number of items per page (default: 50)
            cursor: Cursor from previous page (None for first page)

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag

        Example:
            >>> # List all new skills
            >>> result = repo.list_paginated(
            ...     status="new",
            ...     artifact_type="skill",
            ...     limit=50
            ... )
            >>>
            >>> # Next page
            >>> if result.has_more:
            ...     next_result = repo.list_paginated(
            ...         status="new",
            ...         artifact_type="skill",
            ...         limit=50,
            ...         cursor=result.next_cursor
            ...     )
        """
        session = self._get_session()
        try:
            query = session.query(MarketplaceCatalogEntry)

            # Apply filters
            if source_id:
                query = query.filter_by(source_id=source_id)
            if status:
                query = query.filter_by(status=status)
            if artifact_type:
                query = query.filter_by(artifact_type=artifact_type)

            # Apply cursor filter if provided
            if cursor:
                query = query.filter(MarketplaceCatalogEntry.id > cursor)

            # Order by ID for stable pagination
            query = query.order_by(MarketplaceCatalogEntry.id)

            # Fetch limit + 1 to check if more items exist
            items = query.limit(limit + 1).all()

            # Determine if more items exist
            has_more = len(items) > limit
            if has_more:
                items = items[:limit]

            # Generate next cursor from last item's ID
            next_cursor = items[-1].id if items and has_more else None

            logger.debug(
                f"Listed {len(items)} catalog entries "
                f"(source_id={source_id}, status={status}, "
                f"type={artifact_type}, cursor={cursor}, has_more={has_more})"
            )

            return PaginatedResult(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
            )
        finally:
            session.close()

    def list_by_source_and_status(
        self, source_id: str, status: str
    ) -> List[MarketplaceCatalogEntry]:
        """List catalog entries by source and status.

        Args:
            source_id: Marketplace source identifier
            status: Import status filter

        Returns:
            List of MarketplaceCatalogEntry instances

        Example:
            >>> # Find all new artifacts from a specific source
            >>> new_entries = repo.list_by_source_and_status("source-123", "new")
        """
        session = self._get_session()
        try:
            entries = (
                session.query(MarketplaceCatalogEntry)
                .filter_by(source_id=source_id, status=status)
                .order_by(MarketplaceCatalogEntry.detected_at.desc())
                .all()
            )
            logger.debug(
                f"Found {len(entries)} entries for source {source_id} "
                f"with status '{status}'"
            )
            return entries
        finally:
            session.close()

    def list_by_type(self, artifact_type: str) -> List[MarketplaceCatalogEntry]:
        """List catalog entries by artifact type.

        Args:
            artifact_type: Artifact type filter ("skill", "command", etc.)

        Returns:
            List of MarketplaceCatalogEntry instances

        Example:
            >>> # Find all detected skills
            >>> skills = repo.list_by_type("skill")
        """
        session = self._get_session()
        try:
            entries = (
                session.query(MarketplaceCatalogEntry)
                .filter_by(artifact_type=artifact_type)
                .order_by(MarketplaceCatalogEntry.detected_at.desc())
                .all()
            )
            logger.debug(f"Found {len(entries)} entries of type '{artifact_type}'")
            return entries
        finally:
            session.close()

    def filter_by_confidence_range(
        self, min_score: int, max_score: int = 100
    ) -> List[MarketplaceCatalogEntry]:
        """Filter catalog entries by confidence score range.

        Args:
            min_score: Minimum confidence score (inclusive, 0-100)
            max_score: Maximum confidence score (inclusive, 0-100, default: 100)

        Returns:
            List of MarketplaceCatalogEntry instances within score range

        Example:
            >>> # Find high-confidence detections only
            >>> high_confidence = repo.filter_by_confidence_range(min_score=80)
            >>>
            >>> # Find medium-confidence detections
            >>> medium = repo.filter_by_confidence_range(min_score=50, max_score=79)
        """
        session = self._get_session()
        try:
            entries = (
                session.query(MarketplaceCatalogEntry)
                .filter(
                    and_(
                        MarketplaceCatalogEntry.confidence_score >= min_score,
                        MarketplaceCatalogEntry.confidence_score <= max_score,
                    )
                )
                .order_by(
                    MarketplaceCatalogEntry.confidence_score.desc(),
                    MarketplaceCatalogEntry.detected_at.desc(),
                )
                .all()
            )
            logger.debug(
                f"Found {len(entries)} entries with confidence "
                f"between {min_score} and {max_score}"
            )
            return entries
        finally:
            session.close()

    def find_duplicates_by_type_and_name(
        self, artifact_type: str, name: str
    ) -> List[MarketplaceCatalogEntry]:
        """Find duplicate catalog entries by type and name.

        Useful for deduplication - identifies multiple detections of the
        same artifact across different sources or paths.

        Args:
            artifact_type: Artifact type to search
            name: Artifact name to search

        Returns:
            List of MarketplaceCatalogEntry instances with matching type and name

        Example:
            >>> # Check for duplicates before adding
            >>> duplicates = repo.find_duplicates_by_type_and_name("skill", "canvas")
            >>> if len(duplicates) > 1:
            ...     print(f"Found {len(duplicates)} versions of canvas skill")
        """
        session = self._get_session()
        try:
            entries = (
                session.query(MarketplaceCatalogEntry)
                .filter_by(artifact_type=artifact_type, name=name)
                .order_by(
                    MarketplaceCatalogEntry.confidence_score.desc(),
                    MarketplaceCatalogEntry.detected_at.desc(),
                )
                .all()
            )
            logger.debug(
                f"Found {len(entries)} entries matching "
                f"type='{artifact_type}', name='{name}'"
            )
            return entries
        finally:
            session.close()

    def bulk_update_status(self, entry_ids: List[str], status: str) -> int:
        """Bulk update status for multiple catalog entries.

        Uses efficient SQL UPDATE to modify multiple entries in one query.
        Sets import_date if status is "imported".

        Args:
            entry_ids: List of catalog entry IDs to update
            status: New status to set

        Returns:
            Number of entries updated

        Example:
            >>> # Mark multiple entries as imported
            >>> entry_ids = ["entry-1", "entry-2", "entry-3"]
            >>> count = repo.bulk_update_status(entry_ids, "imported")
            >>> print(f"Updated {count} entries")
        """
        if not entry_ids:
            return 0

        session = self._get_session()
        try:
            # Build update values
            update_values = {"status": status, "updated_at": datetime.utcnow()}
            if status == "imported":
                update_values["import_date"] = datetime.utcnow()

            # Execute bulk update
            result = (
                session.query(MarketplaceCatalogEntry)
                .filter(MarketplaceCatalogEntry.id.in_(entry_ids))
                .update(update_values, synchronize_session=False)
            )

            session.commit()
            logger.info(f"Bulk updated {result} catalog entries to status '{status}'")
            return result
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Bulk update failed: {e}") from e
        finally:
            session.close()

    def delete_by_source(self, source_id: str) -> int:
        """Delete all catalog entries for a specific source.

        Args:
            source_id: Marketplace source identifier

        Returns:
            Number of entries deleted

        Example:
            >>> # Clean up entries when removing a source
            >>> count = repo.delete_by_source("source-123")
            >>> print(f"Deleted {count} entries")
        """
        session = self._get_session()
        try:
            result = (
                session.query(MarketplaceCatalogEntry)
                .filter_by(source_id=source_id)
                .delete(synchronize_session=False)
            )

            session.commit()
            logger.info(f"Deleted {result} catalog entries for source {source_id}")
            return result
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Bulk delete failed: {e}") from e
        finally:
            session.close()

    # =========================================================================
    # REPO-003: Complex Filtering and Joins
    # =========================================================================

    def get_source_catalog(
        self,
        source_id: str,
        artifact_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        min_confidence: Optional[int] = None,
        max_confidence: Optional[int] = None,
    ) -> List[MarketplaceCatalogEntry]:
        """Get catalog entries for a source with optional filtering.

        Provides flexible filtering for querying a source's catalog with
        multiple criteria applied simultaneously.

        Args:
            source_id: Marketplace source ID
            artifact_types: Filter by types (e.g., ["skill", "command"])
            statuses: Filter by statuses (e.g., ["new", "updated"])
            min_confidence: Minimum confidence score (0-100)
            max_confidence: Maximum confidence score (0-100)

        Returns:
            List of matching catalog entries ordered by detection date

        Example:
            >>> # Get all high-confidence skills that are new or updated
            >>> entries = repo.get_source_catalog(
            ...     source_id="source-123",
            ...     artifact_types=["skill"],
            ...     statuses=["new", "updated"],
            ...     min_confidence=80
            ... )
            >>> for entry in entries:
            ...     print(f"{entry.name}: {entry.confidence_score}%")
        """
        session = self._get_session()
        try:
            query = session.query(MarketplaceCatalogEntry).filter_by(
                source_id=source_id
            )

            # Apply artifact type filter
            if artifact_types:
                query = query.filter(
                    MarketplaceCatalogEntry.artifact_type.in_(artifact_types)
                )

            # Apply status filter
            if statuses:
                query = query.filter(MarketplaceCatalogEntry.status.in_(statuses))

            # Apply confidence range filters
            if min_confidence is not None:
                query = query.filter(
                    MarketplaceCatalogEntry.confidence_score >= min_confidence
                )
            if max_confidence is not None:
                query = query.filter(
                    MarketplaceCatalogEntry.confidence_score <= max_confidence
                )

            # Order by detection date (most recent first)
            entries = query.order_by(MarketplaceCatalogEntry.detected_at.desc()).all()

            logger.debug(
                f"Found {len(entries)} catalog entries for source {source_id} "
                f"with filters (types={artifact_types}, statuses={statuses}, "
                f"confidence={min_confidence}-{max_confidence})"
            )
            return entries
        finally:
            session.close()

    def compare_catalogs(
        self,
        source_id: str,
        new_entries: List[Dict[str, Any]],
    ) -> CatalogDiff:
        """Compare existing catalog with new scan results.

        Identifies changes between current catalog and new scan results by
        comparing upstream URLs and detected SHAs. This enables efficient
        incremental updates when rescanning a source.

        Comparison logic:
        - new: entries in new_entries but not in DB (by upstream_url)
        - updated: entries with same upstream_url but different detected_sha
        - removed: entries in DB but not in new_entries
        - unchanged: entries with matching upstream_url and detected_sha

        Args:
            source_id: Marketplace source ID
            new_entries: List of dicts with keys:
                - upstream_url (str): Full URL to artifact
                - artifact_type (str): Type of artifact
                - name (str): Artifact name
                - detected_sha (str): Git SHA of detected artifact

        Returns:
            CatalogDiff with categorized changes

        Example:
            >>> # After scanning a repository
            >>> new_entries = [
            ...     {
            ...         "upstream_url": "https://github.com/user/repo/blob/main/skills/skill1",
            ...         "artifact_type": "skill",
            ...         "name": "skill1",
            ...         "detected_sha": "abc123"
            ...     },
            ... ]
            >>> diff = repo.compare_catalogs("source-123", new_entries)
            >>> print(f"New: {len(diff.new)}, Updated: {len(diff.updated)}, "
            ...       f"Removed: {len(diff.removed)}")
        """
        session = self._get_session()
        try:
            # Fetch all existing entries for this source
            existing_entries = (
                session.query(MarketplaceCatalogEntry)
                .filter_by(source_id=source_id)
                .all()
            )

            # Build lookup maps
            existing_by_url: Dict[str, MarketplaceCatalogEntry] = {
                entry.upstream_url: entry for entry in existing_entries
            }
            new_urls = {entry["upstream_url"] for entry in new_entries}

            # Categorize changes
            new: List[Dict[str, Any]] = []
            updated: List[tuple[str, Dict[str, Any]]] = []
            removed: List[str] = []
            unchanged: List[str] = []

            # Check each new entry
            for new_entry in new_entries:
                url = new_entry["upstream_url"]
                existing = existing_by_url.get(url)

                if not existing:
                    # Entry doesn't exist in DB - mark as new
                    new.append(new_entry)
                elif existing.detected_sha != new_entry.get("detected_sha"):
                    # Entry exists but SHA changed - mark as updated
                    updated.append((existing.id, new_entry))
                else:
                    # Entry exists with same SHA - mark as unchanged
                    unchanged.append(existing.id)

            # Find removed entries (in DB but not in new scan)
            for existing_entry in existing_entries:
                if existing_entry.upstream_url not in new_urls:
                    removed.append(existing_entry.id)

            logger.info(
                f"Catalog comparison for source {source_id}: "
                f"new={len(new)}, updated={len(updated)}, "
                f"removed={len(removed)}, unchanged={len(unchanged)}"
            )

            return CatalogDiff(
                new=new,
                updated=updated,
                removed=removed,
                unchanged=unchanged,
            )
        finally:
            session.close()

    def count_by_status(self, source_id: Optional[str] = None) -> Dict[str, int]:
        """Count catalog entries grouped by status.

        Uses efficient SQL aggregation to count entries by status. Useful for
        dashboard statistics and progress tracking.

        Args:
            source_id: Optional filter by source ID

        Returns:
            Dict mapping status -> count (e.g., {"new": 5, "imported": 3})

        Example:
            >>> # Count all entries by status
            >>> counts = repo.count_by_status()
            >>> print(f"New artifacts: {counts.get('new', 0)}")
            >>>
            >>> # Count entries for specific source
            >>> source_counts = repo.count_by_status(source_id="source-123")
        """
        session = self._get_session()
        try:
            query = session.query(
                MarketplaceCatalogEntry.status,
                func.count(MarketplaceCatalogEntry.id).label("count"),
            )

            # Apply source filter if provided
            if source_id:
                query = query.filter_by(source_id=source_id)

            # Group by status and execute
            results = query.group_by(MarketplaceCatalogEntry.status).all()

            # Convert to dict
            counts = {status: count for status, count in results}

            logger.debug(f"Status counts for source {source_id or 'all'}: {counts}")
            return counts
        finally:
            session.close()

    def count_by_type(self, source_id: Optional[str] = None) -> Dict[str, int]:
        """Count catalog entries grouped by artifact type.

        Uses efficient SQL aggregation to count entries by type. Useful for
        understanding the composition of discovered artifacts.

        Args:
            source_id: Optional filter by source ID

        Returns:
            Dict mapping artifact_type -> count (e.g., {"skill": 10, "command": 3})

        Example:
            >>> # Count all entries by type
            >>> counts = repo.count_by_type()
            >>> print(f"Total skills: {counts.get('skill', 0)}")
            >>>
            >>> # Count entries for specific source
            >>> source_counts = repo.count_by_type(source_id="source-123")
        """
        session = self._get_session()
        try:
            query = session.query(
                MarketplaceCatalogEntry.artifact_type,
                func.count(MarketplaceCatalogEntry.id).label("count"),
            )

            # Apply source filter if provided
            if source_id:
                query = query.filter_by(source_id=source_id)

            # Group by artifact type and execute
            results = query.group_by(MarketplaceCatalogEntry.artifact_type).all()

            # Convert to dict
            counts = {artifact_type: count for artifact_type, count in results}

            logger.debug(f"Type counts for source {source_id or 'all'}: {counts}")
            return counts
        finally:
            session.close()

    # =========================================================================
    # REPO-001: Cross-Source Artifact Search
    # =========================================================================

    def search(
        self,
        query: Optional[str] = None,
        artifact_type: Optional[str] = None,
        source_ids: Optional[List[str]] = None,
        min_confidence: int = 0,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedResult[MarketplaceCatalogEntry]:
        """Cross-source artifact search.

        Uses FTS5 full-text search when available for better performance and
        relevance ranking. Falls back to LIKE-based queries when FTS5 is not
        available or when no query is provided.

        Searches across marketplace catalog entries on name, title, description,
        and search_tags fields. Supports filtering by artifact type, source IDs,
        minimum confidence score, and tags.

        Results are ordered by confidence_score descending to surface the
        highest-quality matches first. Entries with status 'excluded' or
        'removed' are automatically excluded.

        Args:
            query: Optional search query. If None, returns all entries.
            artifact_type: Optional filter by artifact type ("skill", "command", etc.)
            source_ids: Optional list of source IDs to filter by. If provided,
                        only entries from these sources are returned.
            min_confidence: Minimum confidence score (0-100, default: 0).
                           Only entries with score >= min_confidence are returned.
            tags: Optional list of tags to filter by. Matches entries where
                  search_tags contains ANY of the specified tags (OR logic).
            limit: Maximum number of items per page (default: 50)
            cursor: Cursor from previous page (None for first page).
                   Cursor format: "score:id" for stable pagination.

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag

        Example:
            >>> # Search for "canvas" skills with high confidence
            >>> result = repo.search(
            ...     query="canvas",
            ...     artifact_type="skill",
            ...     min_confidence=80,
            ...     limit=20
            ... )
            >>> for entry in result.items:
            ...     print(f"{entry.name}: {entry.confidence_score}%")
            >>>
            >>> # Filter by source and tags
            >>> result = repo.search(
            ...     source_ids=["source-1", "source-2"],
            ...     tags=["automation", "testing"],
            ...     limit=50
            ... )
            >>>
            >>> # Pagination
            >>> if result.has_more:
            ...     next_page = repo.search(
            ...         query="canvas",
            ...         cursor=result.next_cursor
            ...     )
        """
        # Lazy import to avoid circular import
        from skillmeat.api.utils.fts5 import is_fts5_available

        # Use FTS5 when: query is provided AND FTS5 is available
        # Fall back to LIKE: no query, or FTS5 unavailable
        if query and is_fts5_available():
            logger.debug(f"Using FTS5 search for query: {query}")
            return self._search_fts5(
                query=query,
                artifact_type=artifact_type,
                source_ids=source_ids,
                min_confidence=min_confidence,
                tags=tags,
                limit=limit,
                cursor=cursor,
            )

        logger.debug(
            f"Using LIKE search (query={query}, fts5_available={is_fts5_available()})"
        )
        return self._search_like(
            query=query,
            artifact_type=artifact_type,
            source_ids=source_ids,
            min_confidence=min_confidence,
            tags=tags,
            limit=limit,
            cursor=cursor,
        )

    def _build_fts5_query(self, query: str) -> str:
        """Build FTS5 query string, escaping special characters.

        Supports simple phrase matching with prefix search for partial words.
        FTS5 special characters are escaped to prevent query syntax errors.

        Args:
            query: Raw search query from user

        Returns:
            FTS5-safe query string with prefix matching

        Example:
            >>> repo._build_fts5_query("canvas design")
            'canvas* design*'
            >>> repo._build_fts5_query("test-skill")
            'test skill*'
        """
        # FTS5 special characters and operators to escape/remove
        # These would otherwise be interpreted as FTS5 query syntax
        special_chars = ['"', "'", "*", "(", ")", "-", ":", "^", "+"]
        special_operators = ["OR", "AND", "NOT", "NEAR"]

        clean_query = query

        # Remove special characters
        for char in special_chars:
            clean_query = clean_query.replace(char, " ")

        # Split into terms
        terms = clean_query.split()

        # Remove FTS5 operators that might appear as search terms
        terms = [t for t in terms if t.upper() not in special_operators]

        if not terms:
            # If all terms were stripped, use wildcard
            return "*"

        # Use prefix matching for partial word search
        # e.g., "skill doc" -> "skill* doc*"
        return " ".join(f"{term}*" for term in terms if term)

    def _search_fts5(
        self,
        query: str,
        artifact_type: Optional[str] = None,
        source_ids: Optional[List[str]] = None,
        min_confidence: int = 0,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedResult[MarketplaceCatalogEntry]:
        """FTS5 full-text search with relevance ranking.

        Uses SQLite FTS5 virtual table for efficient full-text search with
        Porter stemming. Results are ranked by FTS5 relevance score, then
        by confidence_score for tie-breaking.

        Args:
            query: Search query (required for FTS5 path)
            artifact_type: Optional filter by artifact type
            source_ids: Optional list of source IDs to filter by
            min_confidence: Minimum confidence score (0-100)
            tags: Optional list of tags to filter by (OR logic)
            limit: Maximum number of items per page
            cursor: Cursor from previous page

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag
        """
        session = self._get_session()
        try:
            # Build FTS5 query with escaped special characters
            fts_query = self._build_fts5_query(query)

            # Build dynamic SQL with optional filters
            # Using raw SQL for FTS5 MATCH which SQLAlchemy doesn't support natively
            filters = ["ce.status NOT IN ('excluded', 'removed')"]
            params: Dict[str, Any] = {"query": fts_query, "limit": limit + 1}

            if artifact_type:
                filters.append("ce.artifact_type = :artifact_type")
                params["artifact_type"] = artifact_type

            if source_ids:
                # Build IN clause with positional parameters
                source_placeholders = ", ".join(
                    f":source_{i}" for i in range(len(source_ids))
                )
                filters.append(f"ce.source_id IN ({source_placeholders})")
                for i, source_id in enumerate(source_ids):
                    params[f"source_{i}"] = source_id

            if min_confidence > 0:
                filters.append("ce.confidence_score >= :min_confidence")
                params["min_confidence"] = min_confidence

            if tags:
                # Build OR conditions for tags (match any)
                tag_conditions = []
                for i, tag in enumerate(tags):
                    tag_conditions.append(f"ce.search_tags LIKE :tag_{i}")
                    params[f"tag_{i}"] = f'%"{tag}"%'
                filters.append(f"({' OR '.join(tag_conditions)})")

            # Apply cursor-based pagination
            # Cursor format: "{relevance}:{confidence_score}:{entry_id}"
            # Where relevance is the bm25 score (negative float, closer to 0 = better)
            # Note: We need to apply cursor filter AFTER the FTS5 join since relevance
            # comes from bm25(). We'll use a subquery or CTE approach instead.
            cursor_relevance: Optional[float] = None
            cursor_confidence: Optional[int] = None
            cursor_id: Optional[str] = None
            if cursor:
                try:
                    parts = cursor.split(":", 2)
                    if len(parts) == 3:
                        cursor_relevance = float(parts[0])
                        cursor_confidence = int(parts[1])
                        cursor_id = parts[2]
                    else:
                        # Legacy format: "{confidence_score}:{entry_id}"
                        # Fall back for backwards compatibility
                        cursor_confidence = int(parts[0])
                        cursor_id = parts[1]
                        logger.debug(f"Using legacy cursor format: {cursor}")
                except (ValueError, AttributeError, IndexError):
                    logger.warning(f"Invalid cursor format: {cursor}")

            where_clause = " AND ".join(filters)

            # FTS5 query using external content table
            # bm25() returns negative values (closer to 0 = better match)
            # We use bm25() with column weights to rank results by match location:
            #   - Title matches rank highest (weight 10.0)
            #   - Description matches next (weight 5.0)
            #   - Tag matches (weight 3.0)
            #   - Search text (weight 2.0)
            #   - Deep content matches lowest (weight 1.0)
            # snippet() generates highlighted text around matched terms
            # Column indices: 0=name(unindexed), 1=artifact_type(unindexed), 2=title,
            #                 3=description, 4=search_text, 5=tags, 6=deep_search_text
            # We extract snippets from title (2), description (3), and deep_search_text (6)
            # to determine match source and provide relevant highlighted content
            #
            # bm25 weights: columns 0,1 are unindexed (weight 0), then title, desc,
            #               search_text, tags, deep in order
            bm25_weights = (
                f"0, 0, {SEARCH_WEIGHT_TITLE}, {SEARCH_WEIGHT_DESCRIPTION}, "
                f"{SEARCH_WEIGHT_SEARCH_TEXT}, {SEARCH_WEIGHT_TAGS}, {SEARCH_WEIGHT_DEEP}"
            )

            # Build cursor filter for pagination
            # Since bm25() is computed at query time, we need to filter using the
            # same bm25() expression in the WHERE clause
            cursor_filter = ""
            if (
                cursor_relevance is not None
                and cursor_confidence is not None
                and cursor_id
            ):
                # Full 3-field cursor: relevance:confidence:id
                # ORDER BY relevance ASC, confidence_score DESC, id ASC
                # So "after cursor" means:
                #   - relevance > cursor_relevance (worse match), OR
                #   - relevance = cursor_relevance AND confidence_score < cursor_confidence, OR
                #   - relevance = cursor_relevance AND confidence_score = cursor_confidence AND id > cursor_id
                cursor_filter = f"""
                AND (
                    bm25(catalog_fts, {bm25_weights}) > :cursor_relevance
                    OR (bm25(catalog_fts, {bm25_weights}) = :cursor_relevance AND ce.confidence_score < :cursor_confidence)
                    OR (bm25(catalog_fts, {bm25_weights}) = :cursor_relevance AND ce.confidence_score = :cursor_confidence AND ce.id > :cursor_id)
                )
                """
                params["cursor_relevance"] = cursor_relevance
                params["cursor_confidence"] = cursor_confidence
                params["cursor_id"] = cursor_id
            elif cursor_confidence is not None and cursor_id:
                # Legacy 2-field cursor: confidence:id (no relevance)
                # For backwards compatibility, filter by confidence and id only
                cursor_filter = """
                AND (
                    ce.confidence_score < :cursor_confidence
                    OR (ce.confidence_score = :cursor_confidence AND ce.id > :cursor_id)
                )
                """
                params["cursor_confidence"] = cursor_confidence
                params["cursor_id"] = cursor_id

            sql = text(
                f"""
                SELECT ce.*,
                    bm25(catalog_fts, {bm25_weights}) AS relevance,
                    snippet(catalog_fts, 2, '<mark>', '</mark>', '...', 32) AS title_snippet,
                    snippet(catalog_fts, 3, '<mark>', '</mark>', '...', 64) AS description_snippet,
                    snippet(catalog_fts, 6, '<mark>', '</mark>', '...', 64) AS deep_snippet,
                    ce.deep_index_files AS deep_index_files
                FROM catalog_fts fts
                JOIN marketplace_catalog_entries ce ON ce.rowid = fts.rowid
                WHERE catalog_fts MATCH :query
                AND {where_clause}
                {cursor_filter}
                ORDER BY relevance ASC, ce.confidence_score DESC, ce.id ASC
                LIMIT :limit
                """
            )

            result = session.execute(sql, params)
            rows = result.fetchall()

            # Determine if more items exist
            has_more = len(rows) > limit
            if has_more:
                rows = rows[:limit]

            # Extract snippets and relevance from rows before re-querying for ORM objects
            # Determine if match came from deep_search_text vs title/description
            # A snippet contains '<mark>' if that column matched the search terms
            # Also store relevance scores for cursor generation
            snippets: Dict[str, Dict[str, Any]] = {}
            relevance_scores: Dict[str, float] = {}
            for row in rows:
                title_snippet = row.title_snippet
                description_snippet = row.description_snippet
                deep_snippet = getattr(row, "deep_snippet", None)
                # Store relevance score for cursor generation
                relevance_scores[row.id] = row.relevance

                # Determine if this is a deep match:
                # - Deep match if deep_snippet contains <mark> AND title/desc snippets don't
                # - Title/desc matches rank higher, so only mark as deep_match
                #   when the match clearly came from deep content
                title_has_match = title_snippet and "<mark>" in title_snippet
                desc_has_match = description_snippet and "<mark>" in description_snippet
                deep_has_match = deep_snippet and "<mark>" in deep_snippet

                # It's a deep match only if deep content matched but title/desc didn't
                # This ensures title/description matches rank higher
                # Use bool() to ensure we get False instead of None when deep_has_match is None
                deep_match = bool(
                    deep_has_match and not (title_has_match or desc_has_match)
                )

                # Extract first matched file from deep_index_files if available
                matched_file: Optional[str] = None
                if deep_match:
                    deep_files_json = getattr(row, "deep_index_files", None)
                    if deep_files_json:
                        try:
                            files_list = json.loads(deep_files_json)
                            if files_list and isinstance(files_list, list):
                                # Return first file as representative
                                # Future: could analyze deep_snippet to find exact file
                                matched_file = files_list[0]
                        except json.JSONDecodeError:
                            pass

                snippets[row.id] = {
                    "title_snippet": title_snippet,
                    "description_snippet": description_snippet,
                    "deep_match": deep_match,
                    "matched_file": matched_file,
                }

            # Convert rows to MarketplaceCatalogEntry objects
            # We need to load the entries properly to get the source relationship
            if rows:
                entry_ids = [row.id for row in rows]
                entries_query = (
                    session.query(MarketplaceCatalogEntry)
                    .options(joinedload(MarketplaceCatalogEntry.source))
                    .filter(MarketplaceCatalogEntry.id.in_(entry_ids))
                )
                entries_map = {e.id: e for e in entries_query.all()}
                # Preserve FTS result order
                items = [entries_map[row.id] for row in rows if row.id in entries_map]
            else:
                items = []

            # Generate next cursor from last item
            # Cursor format: "{relevance}:{confidence_score}:{entry_id}"
            # Where relevance is the bm25 score (negative float, closer to 0 = better)
            next_cursor = None
            if items and has_more:
                last_item = items[-1]
                last_relevance = relevance_scores.get(last_item.id, 0.0)
                next_cursor = (
                    f"{last_relevance}:{last_item.confidence_score}:{last_item.id}"
                )

            logger.debug(
                f"FTS5 search returned {len(items)} entries "
                f"(query={query}, fts_query={fts_query}, type={artifact_type}, "
                f"sources={source_ids}, min_conf={min_confidence}, tags={tags}, "
                f"cursor={cursor}, has_more={has_more})"
            )

            return PaginatedResult(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
                snippets=snippets,
            )
        except Exception as e:
            # If FTS5 query fails (e.g., syntax error), fall back to LIKE
            logger.warning(f"FTS5 search failed, falling back to LIKE: {e}")
            return self._search_like(
                query=query,
                artifact_type=artifact_type,
                source_ids=source_ids,
                min_confidence=min_confidence,
                tags=tags,
                limit=limit,
                cursor=cursor,
            )
        finally:
            session.close()

    def _search_like(
        self,
        query: Optional[str] = None,
        artifact_type: Optional[str] = None,
        source_ids: Optional[List[str]] = None,
        min_confidence: int = 0,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedResult[MarketplaceCatalogEntry]:
        """LIKE-based search fallback when FTS5 is unavailable.

        Uses ILIKE queries on name, title, description, and search_tags fields.
        This is the fallback path when FTS5 is not available or when no query
        is provided (listing mode).

        Args:
            query: Optional search query for ILIKE matching
            artifact_type: Optional filter by artifact type
            source_ids: Optional list of source IDs to filter by
            min_confidence: Minimum confidence score (0-100)
            tags: Optional list of tags to filter by (OR logic)
            limit: Maximum number of items per page
            cursor: Cursor from previous page

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag
        """
        session = self._get_session()
        try:
            # Build base query - exclude removed and excluded entries
            # Eagerly load source relationship for cross-source search results
            base_query = (
                session.query(MarketplaceCatalogEntry)
                .options(joinedload(MarketplaceCatalogEntry.source))
                .filter(MarketplaceCatalogEntry.status.notin_(["excluded", "removed"]))
            )

            # Apply text search filter using ILIKE for case-insensitive matching
            if query:
                pattern = f"%{query}%"
                base_query = base_query.filter(
                    or_(
                        MarketplaceCatalogEntry.name.ilike(pattern),
                        MarketplaceCatalogEntry.title.ilike(pattern),
                        MarketplaceCatalogEntry.description.ilike(pattern),
                        MarketplaceCatalogEntry.search_tags.ilike(pattern),
                    )
                )

            # Apply artifact type filter
            if artifact_type:
                base_query = base_query.filter(
                    MarketplaceCatalogEntry.artifact_type == artifact_type
                )

            # Apply source IDs filter
            if source_ids:
                base_query = base_query.filter(
                    MarketplaceCatalogEntry.source_id.in_(source_ids)
                )

            # Apply minimum confidence filter
            if min_confidence > 0:
                base_query = base_query.filter(
                    MarketplaceCatalogEntry.confidence_score >= min_confidence
                )

            # Apply tags filter (OR logic - matches if ANY tag is present)
            if tags:
                # For SQLite JSON, search_tags is stored as JSON array string
                # Use multiple LIKE conditions with OR for each tag
                tag_conditions = []
                for tag in tags:
                    # Match tag in JSON array: ["tag1", "tag2"] contains "tag"
                    tag_conditions.append(
                        MarketplaceCatalogEntry.search_tags.ilike(f'%"{tag}"%')
                    )
                base_query = base_query.filter(or_(*tag_conditions))

            # Apply cursor-based pagination
            # Cursor format: "confidence_score:id" for stable ordering
            if cursor:
                try:
                    cursor_score_str, cursor_id = cursor.split(":", 1)
                    cursor_score = int(cursor_score_str)
                    # Items after cursor: lower score, or same score with higher ID
                    base_query = base_query.filter(
                        or_(
                            MarketplaceCatalogEntry.confidence_score < cursor_score,
                            and_(
                                MarketplaceCatalogEntry.confidence_score
                                == cursor_score,
                                MarketplaceCatalogEntry.id > cursor_id,
                            ),
                        )
                    )
                except (ValueError, AttributeError):
                    # Invalid cursor format - ignore and return from start
                    logger.warning(f"Invalid cursor format: {cursor}")

            # Order by confidence_score descending, then by id for stability
            base_query = base_query.order_by(
                MarketplaceCatalogEntry.confidence_score.desc(),
                MarketplaceCatalogEntry.id.asc(),
            )

            # Fetch limit + 1 to check if more items exist
            items = base_query.limit(limit + 1).all()

            # Determine if more items exist
            has_more = len(items) > limit
            if has_more:
                items = items[:limit]

            # Generate next cursor from last item
            next_cursor = None
            if items and has_more:
                last_item = items[-1]
                next_cursor = f"{last_item.confidence_score}:{last_item.id}"

            logger.debug(
                f"LIKE search returned {len(items)} entries "
                f"(query={query}, type={artifact_type}, sources={source_ids}, "
                f"min_conf={min_confidence}, tags={tags}, cursor={cursor}, "
                f"has_more={has_more})"
            )

            return PaginatedResult(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
            )
        finally:
            session.close()


# =============================================================================
# Deployment Profile Repository
# =============================================================================


class DeploymentProfileRepository(BaseRepository[DeploymentProfile]):
    """Repository for deployment profile CRUD operations."""

    def __init__(self, db_path: Optional[str | Path] = None):
        super().__init__(db_path, DeploymentProfile)

    def create(
        self,
        *,
        project_id: str,
        profile_id: str,
        platform: str,
        root_dir: str,
        description: Optional[str] = None,
        artifact_path_map: Optional[Dict[str, str]] = None,
        config_filenames: Optional[List[str]] = None,
        context_prefixes: Optional[List[str]] = None,
        supported_types: Optional[List[str]] = None,
    ) -> DeploymentProfile:
        """Create a deployment profile."""
        session = self._get_session()
        try:
            platform_value = (
                platform.value if isinstance(platform, Platform) else str(platform)
            )
            platform_enum = (
                Platform(platform_value)
                if platform_value in {p.value for p in Platform}
                else Platform.OTHER
            )
            root_prefix = f"{root_dir.rstrip('/')}/context/"
            profile = DeploymentProfile(
                id=uuid.uuid4().hex,
                project_id=project_id,
                profile_id=profile_id,
                platform=platform_value,
                root_dir=root_dir,
                description=description,
                artifact_path_map=artifact_path_map or {},
                config_filenames=config_filenames
                or default_project_config_filenames(platform_enum),
                context_prefixes=context_prefixes or [root_prefix],
                supported_types=supported_types or [],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            return profile
        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Failed to create deployment profile: {e}") from e
        finally:
            session.close()

    def read_by_id(self, profile_db_id: str) -> Optional[DeploymentProfile]:
        """Read deployment profile by DB ID."""
        session = self._get_session()
        try:
            return (
                session.query(DeploymentProfile)
                .filter(DeploymentProfile.id == profile_db_id)
                .first()
            )
        finally:
            session.close()

    def read_by_project_and_profile_id(
        self, project_id: str, profile_id: str
    ) -> Optional[DeploymentProfile]:
        """Read deployment profile by project and profile ID."""
        session = self._get_session()
        try:
            return (
                session.query(DeploymentProfile)
                .filter(
                    DeploymentProfile.project_id == project_id,
                    DeploymentProfile.profile_id == profile_id,
                )
                .first()
            )
        finally:
            session.close()

    def list_by_project(self, project_id: str) -> List[DeploymentProfile]:
        """List deployment profiles for a project."""
        session = self._get_session()
        try:
            return (
                session.query(DeploymentProfile)
                .filter(DeploymentProfile.project_id == project_id)
                .order_by(DeploymentProfile.profile_id.asc())
                .all()
            )
        finally:
            session.close()

    def list_all_profiles(self, project_id: str) -> List[DeploymentProfile]:
        """Alias for listing all deployment profiles for a project."""
        return self.list_by_project(project_id)

    def get_profile_by_platform(
        self, project_id: str, platform: str | Platform
    ) -> Optional[DeploymentProfile]:
        """Get deployment profile by project and platform."""
        platform_value = (
            platform.value if isinstance(platform, Platform) else str(platform)
        )
        session = self._get_session()
        try:
            return (
                session.query(DeploymentProfile)
                .filter(
                    DeploymentProfile.project_id == project_id,
                    DeploymentProfile.platform == platform_value,
                )
                .order_by(DeploymentProfile.profile_id.asc())
                .first()
            )
        finally:
            session.close()

    def get_primary_profile(self, project_id: str) -> Optional[DeploymentProfile]:
        """Get primary deployment profile for a project.

        Preference order:
        1. Explicit Claude Code platform profile
        2. Profile id == "claude_code"
        3. First profile alphabetically
        """
        primary = self.get_profile_by_platform(project_id, Platform.CLAUDE_CODE)
        if primary:
            return primary

        profile = self.read_by_project_and_profile_id(project_id, "claude_code")
        if profile:
            return profile

        profiles = self.list_by_project(project_id)
        return profiles[0] if profiles else None

    def ensure_default_claude_profile(self, project_id: str) -> DeploymentProfile:
        """Ensure a backward-compatible default Claude profile exists."""
        primary = self.get_primary_profile(project_id)
        if primary:
            return primary

        return self.create(
            project_id=project_id,
            profile_id="claude_code",
            platform=Platform.CLAUDE_CODE.value,
            root_dir=".claude",
            artifact_path_map=DEFAULT_ARTIFACT_PATH_MAP.copy(),
            config_filenames=default_project_config_filenames(Platform.CLAUDE_CODE),
            context_prefixes=[".claude/context/", ".claude/"],
            supported_types=["skill", "command", "agent", "hook", "mcp"],
        )

    def update(
        self,
        project_id: str,
        profile_id: str,
        **updates: Any,
    ) -> Optional[DeploymentProfile]:
        """Update an existing deployment profile."""
        session = self._get_session()
        try:
            profile = (
                session.query(DeploymentProfile)
                .filter(
                    DeploymentProfile.project_id == project_id,
                    DeploymentProfile.profile_id == profile_id,
                )
                .first()
            )
            if not profile:
                return None

            for key, value in updates.items():
                if value is not None and hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(profile)
            return profile
        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Failed to update deployment profile: {e}") from e
        finally:
            session.close()

    def delete(self, project_id: str, profile_id: str) -> bool:
        """Delete deployment profile by project and profile ID."""
        session = self._get_session()
        try:
            profile = (
                session.query(DeploymentProfile)
                .filter(
                    DeploymentProfile.project_id == project_id,
                    DeploymentProfile.profile_id == profile_id,
                )
                .first()
            )
            if not profile:
                return False

            session.delete(profile)
            session.commit()
            return True
        finally:
            session.close()


# =============================================================================
# Tag Repository
# =============================================================================


class TagRepository(BaseRepository[Tag]):
    """Repository for tag management and artifact-tag associations.

    Provides CRUD operations for tags, search capabilities, and methods for
    managing many-to-many relationships between artifacts and tags.

    Usage:
        >>> repo = TagRepository()
        >>>
        >>> # Create tag
        >>> tag = repo.create("Python", "python", "#3776AB")
        >>>
        >>> # Search tags
        >>> tags = repo.search_by_name("py")
        >>>
        >>> # Associate tag with artifact
        >>> repo.add_tag_to_artifact(artifact_id="art-123", tag_id=tag.id)
        >>>
        >>> # Get artifacts by tag
        >>> artifacts, cursor, has_more = repo.get_artifacts_by_tag(tag.id)
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialize tag repository.

        Args:
            db_path: Optional path to database file (uses default if None)
        """
        super().__init__(db_path, Tag)

    # =========================================================================
    # REPO-001: CRUD Operations
    # =========================================================================

    def create(self, name: str, slug: str, color: Optional[str] = None) -> Tag:
        """Create a new tag.

        Args:
            name: Tag name (unique, max 100 characters)
            slug: URL-friendly identifier (unique, kebab-case)
            color: Optional hex color code (e.g., "#FF5733")

        Returns:
            Created Tag instance

        Raises:
            RepositoryError: If tag with same name/slug already exists

        Example:
            >>> tag = repo.create("Python", "python", "#3776AB")
            >>> print(f"Created tag: {tag.name}")
        """
        session = self._get_session()
        try:
            # Check for duplicates
            existing = (
                session.query(Tag)
                .filter(or_(Tag.name == name, Tag.slug == slug))
                .first()
            )

            if existing:
                if existing.name == name:
                    raise RepositoryError(f"Tag with name '{name}' already exists")
                else:
                    raise RepositoryError(f"Tag with slug '{slug}' already exists")

            # Create tag
            tag = Tag(
                id=uuid.uuid4().hex,
                name=name,
                slug=slug,
                color=color,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            session.add(tag)
            session.commit()
            session.refresh(tag)

            logger.info(f"Created tag: {tag.name} (id={tag.id})")
            return tag

        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Failed to create tag: {e}") from e
        finally:
            session.close()

    def get_by_id(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID.

        Args:
            tag_id: Tag identifier

        Returns:
            Tag instance or None if not found

        Example:
            >>> tag = repo.get_by_id("abc123")
            >>> if tag:
            ...     print(f"Found: {tag.name}")
        """
        session = self._get_session()
        try:
            tag = session.query(Tag).filter_by(id=tag_id).first()
            return tag
        finally:
            session.close()

    def get_by_slug(self, slug: str) -> Optional[Tag]:
        """Get tag by slug.

        Args:
            slug: URL-friendly identifier

        Returns:
            Tag instance or None if not found

        Example:
            >>> tag = repo.get_by_slug("python")
            >>> if tag:
            ...     print(f"Found: {tag.name}")
        """
        session = self._get_session()
        try:
            tag = session.query(Tag).filter_by(slug=slug).first()
            return tag
        finally:
            session.close()

    def update(
        self,
        tag_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Optional[Tag]:
        """Update tag attributes.

        Args:
            tag_id: Tag identifier
            name: New tag name (optional)
            slug: New slug (optional)
            color: New color code (optional)

        Returns:
            Updated Tag instance or None if not found

        Raises:
            RepositoryError: If update conflicts with existing tag

        Example:
            >>> tag = repo.update("abc123", color="#FF0000")
            >>> if tag:
            ...     print(f"Updated: {tag.name}")
        """
        session = self._get_session()
        try:
            tag = session.query(Tag).filter_by(id=tag_id).first()
            if not tag:
                return None

            # Check for conflicts if changing name or slug
            if name and name != tag.name:
                existing = session.query(Tag).filter_by(name=name).first()
                if existing:
                    raise RepositoryError(f"Tag with name '{name}' already exists")
                tag.name = name

            if slug and slug != tag.slug:
                existing = session.query(Tag).filter_by(slug=slug).first()
                if existing:
                    raise RepositoryError(f"Tag with slug '{slug}' already exists")
                tag.slug = slug

            if color is not None:
                tag.color = color

            tag.updated_at = datetime.utcnow()

            # Use merge to update
            tag = session.merge(tag)
            session.commit()
            session.refresh(tag)

            logger.info(f"Updated tag: {tag.name} (id={tag.id})")
            return tag

        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Failed to update tag: {e}") from e
        finally:
            session.close()

    def delete(self, tag_id: str) -> bool:
        """Delete tag by ID.

        Also removes all artifact-tag associations (CASCADE).

        Args:
            tag_id: Tag identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = repo.delete("abc123")
            >>> if deleted:
            ...     print("Tag deleted")
        """
        session = self._get_session()
        try:
            tag = session.query(Tag).filter_by(id=tag_id).first()
            if not tag:
                return False

            session.delete(tag)
            session.commit()

            logger.info(f"Deleted tag: {tag.name} (id={tag.id})")
            return True

        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to delete tag: {e}") from e
        finally:
            session.close()

    # =========================================================================
    # REPO-002: Search & List
    # =========================================================================

    def list_all(
        self, limit: int = 100, after_cursor: Optional[str] = None
    ) -> tuple[List[Tag], Optional[str], bool]:
        """List all tags with cursor-based pagination.

        Args:
            limit: Maximum number of tags to return (default: 100)
            after_cursor: Cursor for pagination (tag ID)

        Returns:
            Tuple of (tags, next_cursor, has_more):
                - tags: List of Tag instances
                - next_cursor: Cursor for next page (None if no more)
                - has_more: Whether more results exist

        Example:
            >>> tags, cursor, has_more = repo.list_all(limit=50)
            >>> while has_more:
            ...     tags, cursor, has_more = repo.list_all(limit=50, after_cursor=cursor)
        """
        session = self._get_session()
        try:
            query = session.query(Tag).order_by(Tag.created_at.desc(), Tag.id)

            # Apply cursor if provided
            if after_cursor:
                cursor_tag = session.query(Tag).filter_by(id=after_cursor).first()
                if cursor_tag:
                    query = query.filter(
                        or_(
                            Tag.created_at < cursor_tag.created_at,
                            and_(
                                Tag.created_at == cursor_tag.created_at,
                                Tag.id > cursor_tag.id,
                            ),
                        )
                    )

            # Fetch limit + 1 to check if more exist
            tags = query.limit(limit + 1).all()

            # Determine pagination state
            has_more = len(tags) > limit
            if has_more:
                tags = tags[:limit]
                next_cursor = tags[-1].id if tags else None
            else:
                next_cursor = None

            logger.debug(
                f"Listed {len(tags)} tags (cursor={after_cursor}, has_more={has_more})"
            )
            return tags, next_cursor, has_more

        finally:
            session.close()

    def search_by_name(self, pattern: str, limit: int = 50) -> List[Tag]:
        """Search tags by name pattern (case-insensitive).

        Args:
            pattern: Search pattern (matches anywhere in name)
            limit: Maximum results to return (default: 50)

        Returns:
            List of matching Tag instances

        Example:
            >>> tags = repo.search_by_name("py")
            >>> # Returns tags like "Python", "PyTorch", etc.
        """
        session = self._get_session()
        try:
            tags = (
                session.query(Tag)
                .filter(Tag.name.ilike(f"%{pattern}%"))
                .order_by(Tag.name)
                .limit(limit)
                .all()
            )

            logger.debug(f"Found {len(tags)} tags matching pattern '{pattern}'")
            return tags

        finally:
            session.close()

    # =========================================================================
    # REPO-003: Artifact-Tag Associations
    # =========================================================================

    def add_tag_to_artifact(self, artifact_uuid: str, tag_id: str) -> ArtifactTag:
        """Add tag to artifact (create association).

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity)
            tag_id: Tag identifier

        Returns:
            Created ArtifactTag association

        Raises:
            RepositoryError: If association already exists or IDs invalid

        Example:
            >>> assoc = repo.add_tag_to_artifact("abc123hex", "tag-456")
            >>> print(f"Tagged artifact at {assoc.created_at}")
        """
        session = self._get_session()
        try:
            # Check if association already exists
            existing = (
                session.query(ArtifactTag)
                .filter_by(artifact_uuid=artifact_uuid, tag_id=tag_id)
                .first()
            )

            if existing:
                raise RepositoryError(
                    f"Artifact {artifact_uuid} already has tag {tag_id}"
                )

            # Verify artifact and tag exist
            artifact = session.query(Artifact).filter_by(uuid=artifact_uuid).first()
            if not artifact:
                raise RepositoryError(
                    f"Artifact with uuid={artifact_uuid!r} not found in cache"
                )

            tag = session.query(Tag).filter_by(id=tag_id).first()
            if not tag:
                raise RepositoryError(f"Tag {tag_id} not found")

            # Create association
            assoc = ArtifactTag(
                artifact_uuid=artifact_uuid,
                tag_id=tag_id,
                created_at=datetime.utcnow(),
            )

            session.add(assoc)
            session.commit()
            session.refresh(assoc)

            logger.info(f"Added tag {tag_id} to artifact uuid={artifact_uuid}")
            return assoc

        except IntegrityError as e:
            session.rollback()
            raise RepositoryError(f"Failed to add tag to artifact: {e}") from e
        finally:
            session.close()

    def remove_tag_from_artifact(self, artifact_uuid: str, tag_id: str) -> bool:
        """Remove tag from artifact (delete association).

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity)
            tag_id: Tag identifier

        Returns:
            True if removed, False if association didn't exist

        Example:
            >>> removed = repo.remove_tag_from_artifact("abc123hex", "tag-456")
            >>> if removed:
            ...     print("Tag removed from artifact")
        """
        session = self._get_session()
        try:
            assoc = (
                session.query(ArtifactTag)
                .filter_by(artifact_uuid=artifact_uuid, tag_id=tag_id)
                .first()
            )

            if not assoc:
                return False

            session.delete(assoc)
            session.commit()

            logger.info(f"Removed tag {tag_id} from artifact uuid={artifact_uuid}")
            return True

        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to remove tag from artifact: {e}") from e
        finally:
            session.close()

    def get_artifact_tags(self, artifact_uuid: str) -> List[Tag]:
        """Get all tags for an artifact.

        Args:
            artifact_uuid: Artifact UUID (artifacts.uuid, ADR-007 stable identity)

        Returns:
            List of Tag instances (ordered by name)

        Example:
            >>> tags = repo.get_artifact_tags("abc123hex")
            >>> for tag in tags:
            ...     print(f"- {tag.name}")
        """
        session = self._get_session()
        try:
            tags = (
                session.query(Tag)
                .join(ArtifactTag, Tag.id == ArtifactTag.tag_id)
                .filter(ArtifactTag.artifact_uuid == artifact_uuid)
                .order_by(Tag.name)
                .all()
            )

            logger.debug(f"Found {len(tags)} tags for artifact uuid={artifact_uuid}")
            return tags

        finally:
            session.close()

    def get_artifacts_by_tag(
        self, tag_id: str, limit: int = 100, after_cursor: Optional[str] = None
    ) -> tuple[List[Artifact], Optional[str], bool]:
        """Get all artifacts with a specific tag (paginated).

        Args:
            tag_id: Tag identifier
            limit: Maximum number of artifacts to return (default: 100)
            after_cursor: Cursor for pagination (artifact ID)

        Returns:
            Tuple of (artifacts, next_cursor, has_more):
                - artifacts: List of Artifact instances
                - next_cursor: Cursor for next page (None if no more)
                - has_more: Whether more results exist

        Example:
            >>> artifacts, cursor, has_more = repo.get_artifacts_by_tag("tag-123")
            >>> for artifact in artifacts:
            ...     print(f"- {artifact.name}")
        """
        session = self._get_session()
        try:
            query = (
                session.query(Artifact)
                .join(ArtifactTag, Artifact.uuid == ArtifactTag.artifact_uuid)
                .filter(ArtifactTag.tag_id == tag_id)
                .order_by(ArtifactTag.created_at.desc(), Artifact.uuid)
            )

            # Apply cursor if provided (cursor is artifact_uuid)
            if after_cursor:
                cursor_assoc = (
                    session.query(ArtifactTag)
                    .filter_by(artifact_uuid=after_cursor, tag_id=tag_id)
                    .first()
                )
                if cursor_assoc:
                    query = query.filter(
                        or_(
                            ArtifactTag.created_at < cursor_assoc.created_at,
                            and_(
                                ArtifactTag.created_at == cursor_assoc.created_at,
                                Artifact.uuid > cursor_assoc.artifact_uuid,
                            ),
                        )
                    )

            # Fetch limit + 1 to check if more exist
            artifacts = query.limit(limit + 1).all()

            # Determine pagination state (cursor is artifact_uuid)
            has_more = len(artifacts) > limit
            if has_more:
                artifacts = artifacts[:limit]
                next_cursor = artifacts[-1].uuid if artifacts else None
            else:
                next_cursor = None

            logger.debug(
                f"Found {len(artifacts)} artifacts with tag {tag_id} "
                f"(cursor={after_cursor}, has_more={has_more})"
            )
            return artifacts, next_cursor, has_more

        finally:
            session.close()

    # =========================================================================
    # REPO-004: Statistics
    # =========================================================================

    def get_tag_artifact_count(self, tag_id: str) -> int:
        """Get number of artifacts with a specific tag.

        Args:
            tag_id: Tag identifier

        Returns:
            Count of artifacts with this tag

        Example:
            >>> count = repo.get_tag_artifact_count("tag-123")
            >>> print(f"Tag used on {count} artifacts")
        """
        session = self._get_session()
        try:
            count = (
                session.query(func.count(ArtifactTag.artifact_uuid))
                .filter_by(tag_id=tag_id)
                .scalar()
            )

            return count or 0

        finally:
            session.close()

    def get_all_tag_counts(self) -> List[tuple[Tag, int]]:
        """Get all tags with their artifact counts.

        Returns:
            List of (tag, count) tuples, ordered by count descending

        Example:
            >>> tag_counts = repo.get_all_tag_counts()
            >>> for tag, count in tag_counts:
            ...     print(f"{tag.name}: {count} artifacts")
        """
        session = self._get_session()
        try:
            results = (
                session.query(
                    Tag,
                    func.count(ArtifactTag.artifact_uuid).label("count"),
                )
                .outerjoin(ArtifactTag, Tag.id == ArtifactTag.tag_id)
                .group_by(Tag.id)
                .order_by(func.count(ArtifactTag.artifact_uuid).desc(), Tag.name)
                .all()
            )

            logger.debug(f"Retrieved counts for {len(results)} tags")
            return results

        finally:
            session.close()

    def get_tag_deployment_set_count(self, tag_id: str) -> int:
        """Get number of deployment sets with a specific tag.

        Args:
            tag_id: Tag identifier

        Returns:
            Count of deployment sets with this tag

        Example:
            >>> count = repo.get_tag_deployment_set_count("tag-123")
            >>> print(f"Tag used on {count} deployment sets")
        """
        session = self._get_session()
        try:
            result = (
                session.query(func.count(DeploymentSetTag.deployment_set_id))
                .filter(DeploymentSetTag.tag_id == tag_id)
                .scalar()
            )
            return result or 0
        finally:
            session.close()

    def get_all_deployment_set_tag_counts(self) -> List[tuple[Tag, int]]:
        """Get all tags with their deployment set counts.

        Returns:
            List of (tag, count) tuples where count is the number of
            deployment sets associated with each tag, ordered by count
            descending then by name.

        Example:
            >>> ds_counts = repo.get_all_deployment_set_tag_counts()
            >>> for tag, count in ds_counts:
            ...     print(f"{tag.name}: {count} deployment sets")
        """
        session = self._get_session()
        try:
            results = (
                session.query(
                    Tag,
                    func.count(DeploymentSetTag.deployment_set_id).label("count"),
                )
                .outerjoin(DeploymentSetTag, Tag.id == DeploymentSetTag.tag_id)
                .group_by(Tag.id)
                .order_by(
                    func.count(DeploymentSetTag.deployment_set_id).desc(), Tag.name
                )
                .all()
            )
            logger.debug(f"Retrieved deployment-set counts for {len(results)} tags")
            return results
        finally:
            session.close()


# =============================================================================
# Deployment Set Repository
# =============================================================================


class DeploymentSetRepository(BaseRepository[DeploymentSet]):
    """Repository for DeploymentSet CRUD with owner-scoped access.

    All reads and writes are scoped to ``owner_id`` — two different owners
    can never see each other's sets.  Tag filtering uses a JSON ``LIKE``
    match against the ``tags_json`` column (same approach used elsewhere in
    the codebase for JSON-text tag columns).

    FR-10 delete semantics: Before deleting a set, any
    ``DeploymentSetMember`` rows in *other* sets that reference the doomed
    set via ``member_set_id`` are deleted first, preventing orphan
    references.

    Usage:
        >>> repo = DeploymentSetRepository()
        >>> ds = repo.create(name="My Set", owner_id="user-1")
        >>> fetched = repo.get(ds.id, owner_id="user-1")
        >>> sets = repo.list(owner_id="user-1", tag="prod")
        >>> ok = repo.delete(ds.id, owner_id="user-1")
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        """Initialise repository.

        Args:
            db_path: Optional path to SQLite database file (uses default if None).
        """
        super().__init__(db_path, DeploymentSet)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _sync_tags(self, session: Session, set_id: str, tag_names: List[str]) -> None:
        """Sync deployment set tags via the deployment_set_tags junction table.

        Clears all existing tag associations for the given deployment set, then
        for each tag name finds or creates a ``Tag`` record and inserts a
        ``DeploymentSetTag`` junction row.

        Args:
            session: Active SQLAlchemy session (caller owns commit/rollback).
            set_id: Primary key of the deployment set to sync.
            tag_names: List of tag name strings to associate with the set.
        """
        # Clear existing tag associations for this set
        session.query(DeploymentSetTag).filter(
            DeploymentSetTag.deployment_set_id == set_id
        ).delete(synchronize_session=False)

        now = datetime.utcnow()

        for raw_name in tag_names:
            name = raw_name.strip()
            if not name:
                continue

            # Find existing tag by name (case-insensitive)
            tag = (
                session.query(Tag)
                .filter(func.lower(Tag.name) == func.lower(name))
                .first()
            )

            if not tag:
                # Build a unique slug
                slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                if not slug:
                    slug = uuid.uuid4().hex[:8]
                base_slug = slug
                counter = 1
                while session.query(Tag).filter(Tag.slug == slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                tag = Tag(
                    id=uuid.uuid4().hex,
                    name=name,
                    slug=slug,
                    created_at=now,
                    updated_at=now,
                )
                session.add(tag)
                session.flush()  # Assign id before referencing in junction row

            assoc = DeploymentSetTag(
                deployment_set_id=set_id,
                tag_id=tag.id,
                created_at=now,
            )
            session.add(assoc)

    # =========================================================================
    # Create
    # =========================================================================

    def create(
        self,
        *,
        name: str,
        owner_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> DeploymentSet:
        """Create and return a new DeploymentSet.

        Args:
            name: Human-readable set name (required).
            owner_id: Owning user / identity scope (required).
            description: Optional free-text description.
            tags: Optional list of tag strings.

        Returns:
            Newly created ``DeploymentSet`` instance.

        Raises:
            RepositoryError: If the insert fails (e.g. constraint violation).
        """
        session = self._get_session()
        try:
            now = datetime.utcnow()
            ds = DeploymentSet(
                id=uuid.uuid4().hex,
                name=name,
                owner_id=owner_id,
                description=description,
                created_at=now,
                updated_at=now,
            )
            session.add(ds)
            session.flush()  # Assign the id before syncing tags
            if tags:
                self._sync_tags(session, ds.id, tags)
            session.commit()
            session.refresh(ds)
            logger.debug("Created DeploymentSet id=%s owner=%s", ds.id, owner_id)
            return ds
        except IntegrityError as exc:
            session.rollback()
            raise RepositoryError(f"Failed to create DeploymentSet: {exc}") from exc
        finally:
            session.close()

    # =========================================================================
    # Read
    # =========================================================================

    def get(self, set_id: str, owner_id: str) -> Optional[DeploymentSet]:
        """Fetch a single DeploymentSet by ID, scoped to owner.

        Args:
            set_id: Primary key of the deployment set.
            owner_id: Owner scope — returns None if the set belongs to a
                different owner.

        Returns:
            ``DeploymentSet`` instance or ``None`` if not found.
        """
        session = self._get_session()
        try:
            return (
                session.query(DeploymentSet)
                .filter(
                    DeploymentSet.id == set_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
        finally:
            session.close()

    # =========================================================================
    # List
    # =========================================================================

    def list(
        self,
        owner_id: str,
        *,
        name: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DeploymentSet]:
        """Return a paginated, filterable list of DeploymentSets for an owner.

        Args:
            owner_id: Owning user / identity scope (always applied).
            name: Optional substring filter on ``DeploymentSet.name``
                (case-insensitive ``LIKE``).
            tag: Optional tag to filter by.  Matches if the tag string appears
                anywhere inside the JSON array stored in ``tags_json``.
            limit: Maximum number of rows to return (default 50).
            offset: Number of rows to skip for pagination (default 0).

        Returns:
            List of ``DeploymentSet`` instances ordered by ``created_at`` desc.
        """
        session = self._get_session()
        try:
            q = session.query(DeploymentSet).filter(DeploymentSet.owner_id == owner_id)
            if name is not None:
                q = q.filter(DeploymentSet.name.ilike(f"%{name}%"))
            if tag is not None:
                q = (
                    q.join(
                        DeploymentSetTag,
                        DeploymentSetTag.deployment_set_id == DeploymentSet.id,
                    )
                    .join(Tag, Tag.id == DeploymentSetTag.tag_id)
                    .filter(func.lower(Tag.name) == func.lower(tag))
                )
            return (
                q.order_by(DeploymentSet.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
        finally:
            session.close()

    # =========================================================================
    # Count
    # =========================================================================

    def count(
        self,
        owner_id: str,
        *,
        name: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> int:
        """Count DeploymentSets matching the given filters for an owner.

        Args:
            owner_id: Owning user / identity scope (always applied).
            name: Optional substring filter on ``DeploymentSet.name``.
            tag: Optional tag filter (JSON LIKE match).

        Returns:
            Integer count of matching sets.
        """
        session = self._get_session()
        try:
            q = session.query(func.count(DeploymentSet.id)).filter(
                DeploymentSet.owner_id == owner_id
            )
            if name is not None:
                q = q.filter(DeploymentSet.name.ilike(f"%{name}%"))
            if tag is not None:
                q = (
                    q.join(
                        DeploymentSetTag,
                        DeploymentSetTag.deployment_set_id == DeploymentSet.id,
                    )
                    .join(Tag, Tag.id == DeploymentSetTag.tag_id)
                    .filter(func.lower(Tag.name) == func.lower(tag))
                )
            return q.scalar() or 0
        finally:
            session.close()

    # =========================================================================
    # Update
    # =========================================================================

    def update(
        self,
        set_id: str,
        owner_id: str,
        **kwargs: Any,
    ) -> Optional[DeploymentSet]:
        """Update mutable fields on a DeploymentSet.

        Only ``name``, ``description``, and ``tags`` are writable.
        ``updated_at`` is refreshed automatically on every successful update.

        Args:
            set_id: Primary key of the deployment set.
            owner_id: Owner scope — returns None if the set belongs to a
                different owner or does not exist.
            **kwargs: Keyword arguments for fields to update.  Supported
                keys: ``name`` (str), ``description`` (str | None),
                ``tags`` (list[str]).

        Returns:
            Updated ``DeploymentSet`` instance, or ``None`` if not found.

        Raises:
            RepositoryError: If the update fails due to a constraint violation.
        """
        session = self._get_session()
        try:
            ds = (
                session.query(DeploymentSet)
                .filter(
                    DeploymentSet.id == set_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
            if ds is None:
                return None

            if "name" in kwargs:
                ds.name = kwargs["name"]
            if "description" in kwargs:
                ds.description = kwargs["description"]
            if "tags" in kwargs:
                self._sync_tags(session, ds.id, kwargs["tags"])

            ds.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(ds)
            logger.debug("Updated DeploymentSet id=%s owner=%s", set_id, owner_id)
            return ds
        except IntegrityError as exc:
            session.rollback()
            raise RepositoryError(f"Failed to update DeploymentSet: {exc}") from exc
        finally:
            session.close()

    # =========================================================================
    # Delete  (FR-10)
    # =========================================================================

    def delete(self, set_id: str, owner_id: str) -> bool:
        """Delete a DeploymentSet, cleaning up cross-set member references first.

        FR-10 semantics: Before deleting the target set, any
        ``DeploymentSetMember`` rows in *other* sets that reference the
        target via ``member_set_id`` are deleted to prevent orphan
        references.  The target set's own members are removed by the
        ``CASCADE DELETE`` on ``deployment_set_members.set_id``.

        Args:
            set_id: Primary key of the deployment set to delete.
            owner_id: Owner scope — returns False if the set belongs to a
                different owner or does not exist.

        Returns:
            ``True`` if the set was found and deleted, ``False`` otherwise.

        Raises:
            RepositoryError: If the deletion fails unexpectedly.
        """
        session = self._get_session()
        try:
            ds = (
                session.query(DeploymentSet)
                .filter(
                    DeploymentSet.id == set_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
            if ds is None:
                return False

            # FR-10: remove member rows in OTHER sets that reference this set
            # as a nested member before deleting the set itself.
            orphan_members = (
                session.query(DeploymentSetMember)
                .filter(
                    DeploymentSetMember.member_set_id == set_id,
                    DeploymentSetMember.set_id != set_id,
                )
                .all()
            )
            for member in orphan_members:
                session.delete(member)

            session.delete(ds)
            session.commit()
            logger.debug(
                "Deleted DeploymentSet id=%s owner=%s (removed %d orphan member refs)",
                set_id,
                owner_id,
                len(orphan_members),
            )
            return True
        except IntegrityError as exc:
            session.rollback()
            raise RepositoryError(f"Failed to delete DeploymentSet: {exc}") from exc
        finally:
            session.close()

    # =========================================================================
    # Member management
    # =========================================================================

    def add_member(
        self,
        set_id: str,
        owner_id: str,
        *,
        artifact_uuid: Optional[str] = None,
        group_id: Optional[str] = None,
        member_set_id: Optional[str] = None,
        position: Optional[int] = None,
    ) -> DeploymentSetMember:
        """Add a member to a DeploymentSet.

        Exactly one of ``artifact_uuid``, ``group_id``, or ``member_set_id``
        must be provided — this mirrors the DB CHECK constraint and produces
        a clear error before the row is even attempted.

        If ``position`` is omitted, the member is appended after the current
        maximum position (``max_position + 1``).  If the set has no existing
        members, position defaults to ``0``.

        Args:
            set_id: Primary key of the parent deployment set.
            owner_id: Owner scope — set must belong to this owner.
            artifact_uuid: Collection artifact UUID (ADR-007 stable identity).
            group_id: Artifact group id.
            member_set_id: Nested deployment set id.
            position: Explicit 0-based ordering position.  Auto-assigned
                when omitted.

        Returns:
            Newly created ``DeploymentSetMember`` instance.

        Raises:
            ValueError: If the exactly-one-ref constraint is violated, or if
                the parent set does not exist / belongs to a different owner.
            RepositoryError: If the insert fails due to a DB constraint.
        """
        # Repo-level guard: exactly one reference must be supplied.
        refs_provided = sum(
            [
                artifact_uuid is not None,
                group_id is not None,
                member_set_id is not None,
            ]
        )
        if refs_provided != 1:
            raise ValueError(
                "Exactly one of artifact_uuid, group_id, or member_set_id must be "
                f"provided (got {refs_provided} non-null values)."
            )

        session = self._get_session()
        try:
            # Verify parent set exists and is owned by owner_id.
            ds = (
                session.query(DeploymentSet)
                .filter(
                    DeploymentSet.id == set_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
            if ds is None:
                raise ValueError(
                    f"DeploymentSet id={set_id!r} not found for owner {owner_id!r}."
                )

            # Auto-assign position when not supplied.
            if position is None:
                max_pos = (
                    session.query(func.max(DeploymentSetMember.position))
                    .filter(DeploymentSetMember.set_id == set_id)
                    .scalar()
                )
                position = 0 if max_pos is None else max_pos + 1

            member = DeploymentSetMember(
                set_id=set_id,
                artifact_uuid=artifact_uuid,
                group_id=group_id,
                member_set_id=member_set_id,
                position=position,
                created_at=datetime.utcnow(),
            )
            session.add(member)
            session.commit()
            session.refresh(member)
            logger.debug(
                "Added DeploymentSetMember id=%s to set=%s owner=%s position=%d",
                member.id,
                set_id,
                owner_id,
                position,
            )
            return member
        except IntegrityError as exc:
            session.rollback()
            raise RepositoryError(
                f"Failed to add member to DeploymentSet {set_id!r}: {exc}"
            ) from exc
        finally:
            session.close()

    def remove_member(self, member_id: str, owner_id: str) -> bool:
        """Remove a member from a DeploymentSet.

        The parent set must belong to ``owner_id``; if it does not, or if
        the member does not exist, ``False`` is returned without raising.

        Args:
            member_id: Primary key of the ``DeploymentSetMember`` to delete.
            owner_id: Owner scope — parent set must belong to this owner.

        Returns:
            ``True`` if the member was found and deleted, ``False`` otherwise.

        Raises:
            RepositoryError: If the deletion fails unexpectedly.
        """
        session = self._get_session()
        try:
            member = (
                session.query(DeploymentSetMember)
                .join(
                    DeploymentSet,
                    DeploymentSet.id == DeploymentSetMember.set_id,
                )
                .filter(
                    DeploymentSetMember.id == member_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
            if member is None:
                return False

            session.delete(member)
            session.commit()
            logger.debug(
                "Removed DeploymentSetMember id=%s owner=%s", member_id, owner_id
            )
            return True
        except IntegrityError as exc:
            session.rollback()
            raise RepositoryError(
                f"Failed to remove DeploymentSetMember {member_id!r}: {exc}"
            ) from exc
        finally:
            session.close()

    def update_member_position(
        self, member_id: str, owner_id: str, position: int
    ) -> Optional[DeploymentSetMember]:
        """Update the ordering position of a DeploymentSetMember.

        The parent set must belong to ``owner_id``; if it does not, or if
        the member does not exist, ``None`` is returned.

        Args:
            member_id: Primary key of the ``DeploymentSetMember`` to update.
            owner_id: Owner scope — parent set must belong to this owner.
            position: New 0-based position value (must be >= 0).

        Returns:
            Updated ``DeploymentSetMember`` instance, or ``None`` if not found.

        Raises:
            RepositoryError: If the update fails due to a constraint violation.
        """
        session = self._get_session()
        try:
            member = (
                session.query(DeploymentSetMember)
                .join(
                    DeploymentSet,
                    DeploymentSet.id == DeploymentSetMember.set_id,
                )
                .filter(
                    DeploymentSetMember.id == member_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
            if member is None:
                return None

            member.position = position
            session.commit()
            session.refresh(member)
            logger.debug(
                "Updated DeploymentSetMember id=%s position=%d owner=%s",
                member_id,
                position,
                owner_id,
            )
            return member
        except IntegrityError as exc:
            session.rollback()
            raise RepositoryError(
                f"Failed to update position for DeploymentSetMember {member_id!r}: {exc}"
            ) from exc
        finally:
            session.close()

    def get_members(self, set_id: str, owner_id: str) -> List[DeploymentSetMember]:
        """Return all members of a DeploymentSet, ordered by position.

        The set must belong to ``owner_id``; an empty list is returned if
        the set does not exist or belongs to a different owner.

        Args:
            set_id: Primary key of the parent deployment set.
            owner_id: Owner scope — set must belong to this owner.

        Returns:
            List of ``DeploymentSetMember`` instances ordered by
            ``position`` ascending.  Empty list when not found.
        """
        session = self._get_session()
        try:
            ds = (
                session.query(DeploymentSet)
                .filter(
                    DeploymentSet.id == set_id,
                    DeploymentSet.owner_id == owner_id,
                )
                .first()
            )
            if ds is None:
                return []

            return (
                session.query(DeploymentSetMember)
                .filter(DeploymentSetMember.set_id == set_id)
                .order_by(DeploymentSetMember.position)
                .all()
            )
        finally:
            session.close()
