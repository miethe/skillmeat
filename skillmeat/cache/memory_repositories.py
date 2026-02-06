"""Repository pattern implementation for Memory & Context Intelligence System.

This module provides repository classes for memory items and context modules,
following the same patterns established in repositories.py. These repositories
abstract SQLAlchemy session management and provide type-safe CRUD operations
for the memory system domain.

Repositories:
    - MemoryItemRepository: CRUD + query for memory items (decisions, constraints, etc.)
    - ContextModuleRepository: CRUD + relationship management for context modules

Usage:
    >>> from skillmeat.cache.memory_repositories import (
    ...     MemoryItemRepository,
    ...     ContextModuleRepository,
    ... )
    >>>
    >>> memory_repo = MemoryItemRepository()
    >>> module_repo = ContextModuleRepository()
    >>>
    >>> # Create a memory item
    >>> item = memory_repo.create({
    ...     "project_id": "proj-123",
    ...     "type": "decision",
    ...     "content": "Use SQLAlchemy for ORM",
    ...     "confidence": 0.9,
    ... })
    >>>
    >>> # List items with filtering
    >>> result = memory_repo.list_items("proj-123", type="decision", min_confidence=0.8)
    >>> for item in result.items:
    ...     print(item.content)
"""

from __future__ import annotations

import base64
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from skillmeat.cache.models import ContextModule, MemoryItem, ModuleMemoryItem
from skillmeat.cache.repositories import (
    BaseRepository,
    ConstraintError,
    NotFoundError,
    PaginatedResult,
    RepositoryError,
)

# Configure logging
logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# =============================================================================
# MemoryItemRepository
# =============================================================================


class MemoryItemRepository(BaseRepository[MemoryItem]):
    """Repository for MemoryItem CRUD operations and queries.

    Provides data access for project-scoped memory items including decisions,
    constraints, gotchas, style rules, and learnings. Supports cursor-based
    pagination with configurable sort fields and filtering.

    Example:
        >>> repo = MemoryItemRepository()
        >>> item = repo.create({
        ...     "project_id": "proj-123",
        ...     "type": "gotcha",
        ...     "content": "SQLite does not support ALTER COLUMN",
        ...     "confidence": 0.95,
        ... })
        >>> print(item.id, item.content_hash)
    """

    def __init__(self, db_path=None):
        """Initialize MemoryItemRepository.

        Args:
            db_path: Optional path to database file (uses default if None)
        """
        super().__init__(db_path, MemoryItem)

    def create(self, data: Dict[str, Any]) -> MemoryItem:
        """Create a new memory item from a dictionary.

        Generates ``id`` if not provided, sets timestamps, and computes
        ``content_hash`` from ``content`` when not explicitly given.

        Args:
            data: Dictionary of MemoryItem fields. Must include at minimum
                ``project_id``, ``type``, and ``content``.

        Returns:
            The created MemoryItem instance.

        Raises:
            ConstraintError: If a memory item with the same content_hash
                already exists (duplicate content).
        """
        now = _now_iso()

        # Set defaults
        data.setdefault("id", uuid.uuid4().hex)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        data.setdefault("confidence", 0.75)
        data.setdefault("status", "candidate")
        data.setdefault("access_count", 0)

        # Compute content hash if not provided
        if "content_hash" not in data:
            data["content_hash"] = _compute_content_hash(data["content"])

        item = MemoryItem(**data)

        session = self._get_session()
        try:
            session.add(item)
            session.commit()
            session.refresh(item)
            logger.info(
                f"Created memory item: {item.id} "
                f"(project={item.project_id}, type={item.type})"
            )
            return item
        except IntegrityError as e:
            session.rollback()
            raise ConstraintError(
                f"Memory item with duplicate content_hash already exists: {e}"
            ) from e
        finally:
            session.close()

    def get_by_id(self, item_id: str) -> Optional[MemoryItem]:
        """Get a memory item by primary key.

        Args:
            item_id: Unique memory item identifier.

        Returns:
            MemoryItem if found, None otherwise.
        """
        session = self._get_session()
        try:
            return session.query(MemoryItem).filter_by(id=item_id).first()
        finally:
            session.close()

    def get_by_content_hash(self, content_hash: str) -> Optional[MemoryItem]:
        """Find a memory item by its content hash (for deduplication).

        Args:
            content_hash: SHA-256 hash of the content text.

        Returns:
            MemoryItem if found, None otherwise.
        """
        session = self._get_session()
        try:
            return (
                session.query(MemoryItem)
                .filter_by(content_hash=content_hash)
                .first()
            )
        finally:
            session.close()

    def list_items(
        self,
        project_id: str,
        *,
        status: Optional[str] = None,
        type: Optional[str] = None,
        search: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaginatedResult[MemoryItem]:
        """List memory items with filtering and cursor-based pagination.

        Args:
            project_id: Required project scope filter.
            status: Optional status filter (candidate, active, stable, deprecated).
            type: Optional type filter (decision, constraint, gotcha, etc.).
            min_confidence: Optional minimum confidence threshold.
            limit: Maximum items per page (default 50).
            cursor: Cursor from previous page for pagination.
            sort_by: Field to sort by (default "created_at").
            sort_order: Sort direction, "asc" or "desc" (default "desc").

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag.
        """
        session = self._get_session()
        try:
            query = session.query(MemoryItem).filter(
                MemoryItem.project_id == project_id
            )

            # Apply optional filters
            if status is not None:
                query = query.filter(MemoryItem.status == status)
            if type is not None:
                query = query.filter(MemoryItem.type == type)
            if search:
                query = query.filter(MemoryItem.content.ilike(f"%{search}%"))
            if min_confidence is not None:
                query = query.filter(MemoryItem.confidence >= min_confidence)

            # Determine sort column and direction
            sort_col = getattr(MemoryItem, sort_by, MemoryItem.created_at)
            is_desc = sort_order == "desc"

            # Apply cursor filter if provided
            if cursor:
                cursor_id, cursor_value = self._decode_cursor(cursor)
                if is_desc:
                    query = query.filter(
                        or_(
                            sort_col < cursor_value,
                            and_(sort_col == cursor_value, MemoryItem.id < cursor_id),
                        )
                    )
                else:
                    query = query.filter(
                        or_(
                            sort_col > cursor_value,
                            and_(sort_col == cursor_value, MemoryItem.id > cursor_id),
                        )
                    )

            # Apply ordering
            if is_desc:
                query = query.order_by(sort_col.desc(), MemoryItem.id.desc())
            else:
                query = query.order_by(sort_col.asc(), MemoryItem.id.asc())

            # Fetch limit + 1 to check for more
            items = query.limit(limit + 1).all()

            has_more = len(items) > limit
            if has_more:
                items = items[:limit]

            next_cursor = (
                self._encode_cursor(items[-1], sort_by) if items and has_more else None
            )

            logger.debug(
                f"Listed {len(items)} memory items "
                f"(project={project_id}, status={status}, type={type}, "
                f"cursor={cursor}, has_more={has_more})"
            )

            return PaginatedResult(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
            )
        finally:
            session.close()

    def update(self, item_id: str, data: Dict[str, Any]) -> MemoryItem:
        """Update a memory item's fields.

        Sets ``updated_at`` to the current time. If ``status`` is changed to
        ``"deprecated"``, also sets ``deprecated_at``.

        Args:
            item_id: The memory item ID to update.
            data: Dictionary of fields to update.

        Returns:
            The updated MemoryItem instance.

        Raises:
            NotFoundError: If no memory item exists with the given ID.
        """
        session = self._get_session()
        try:
            item = session.query(MemoryItem).filter_by(id=item_id).first()
            if not item:
                raise NotFoundError(f"Memory item not found: {item_id}")

            # Track status change for deprecated_at
            old_status = item.status

            for key, value in data.items():
                if hasattr(item, key):
                    setattr(item, key, value)

            item.updated_at = _now_iso()

            # Set deprecated_at when status transitions to deprecated
            if data.get("status") == "deprecated" and old_status != "deprecated":
                item.deprecated_at = _now_iso()

            session.commit()
            session.refresh(item)
            logger.info(f"Updated memory item: {item_id}")
            return item
        except NotFoundError:
            raise
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to update memory item: {e}") from e
        finally:
            session.close()

    def delete(self, item_id: str) -> bool:
        """Delete a memory item by ID.

        Args:
            item_id: The memory item ID to delete.

        Returns:
            True if the item was deleted, False if not found.
        """
        session = self._get_session()
        try:
            item = session.query(MemoryItem).filter_by(id=item_id).first()
            if not item:
                return False

            session.delete(item)
            session.commit()
            logger.info(f"Deleted memory item: {item_id}")
            return True
        finally:
            session.close()

    def increment_access_count(self, item_id: str) -> None:
        """Increment the access_count by 1 using a SQL expression.

        Uses an atomic SQL UPDATE to avoid race conditions when multiple
        callers access the same item concurrently.

        Args:
            item_id: The memory item ID whose count to increment.
        """
        session = self._get_session()
        try:
            rows = (
                session.query(MemoryItem)
                .filter_by(id=item_id)
                .update(
                    {MemoryItem.access_count: MemoryItem.access_count + 1},
                    synchronize_session=False,
                )
            )
            session.commit()
            if rows:
                logger.debug(f"Incremented access_count for memory item: {item_id}")
        finally:
            session.close()

    def count_by_project(
        self, project_id: str, *, status: Optional[str] = None
    ) -> int:
        """Count memory items for a project with optional status filter.

        Args:
            project_id: Project scope to count within.
            status: Optional status filter.

        Returns:
            Count of matching memory items.
        """
        session = self._get_session()
        try:
            query = session.query(MemoryItem).filter(
                MemoryItem.project_id == project_id
            )
            if status is not None:
                query = query.filter(MemoryItem.status == status)
            return query.count()
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Cursor helpers
    # -------------------------------------------------------------------------

    def _encode_cursor(self, item: MemoryItem, sort_by: str) -> str:
        """Encode an item into a cursor string.

        Cursor format: Base64("{id}:{sort_field_value}")

        Args:
            item: The last item on the current page.
            sort_by: The sort field name.

        Returns:
            Base64-encoded cursor string.
        """
        value = getattr(item, sort_by, "")
        raw = f"{item.id}:{value}"
        return base64.b64encode(raw.encode()).decode()

    def _decode_cursor(self, cursor: str) -> tuple:
        """Decode a cursor string into (id, sort_value).

        Args:
            cursor: Base64-encoded cursor string.

        Returns:
            Tuple of (item_id, sort_field_value).
        """
        raw = base64.b64decode(cursor.encode()).decode()
        item_id, sort_value = raw.split(":", 1)
        return item_id, sort_value


# =============================================================================
# ContextModuleRepository
# =============================================================================


class ContextModuleRepository(BaseRepository[ContextModule]):
    """Repository for ContextModule CRUD and relationship management.

    Manages context modules and their many-to-many relationships with
    memory items via the ModuleMemoryItem join table.

    Example:
        >>> repo = ContextModuleRepository()
        >>> module = repo.create({
        ...     "project_id": "proj-123",
        ...     "name": "API Design Decisions",
        ...     "description": "Key decisions for the REST API layer",
        ...     "priority": 3,
        ... })
        >>> repo.add_memory_item(module.id, "memory-456", ordering=1)
    """

    def __init__(self, db_path=None):
        """Initialize ContextModuleRepository.

        Args:
            db_path: Optional path to database file (uses default if None)
        """
        super().__init__(db_path, ContextModule)

    def create(self, data: Dict[str, Any]) -> ContextModule:
        """Create a new context module from a dictionary.

        Generates ``id`` if not provided and sets timestamps.

        Args:
            data: Dictionary of ContextModule fields. Must include at minimum
                ``project_id`` and ``name``.

        Returns:
            The created ContextModule instance.
        """
        now = _now_iso()

        data.setdefault("id", uuid.uuid4().hex)
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        data.setdefault("priority", 5)

        module = ContextModule(**data)

        session = self._get_session()
        try:
            session.add(module)
            session.commit()
            session.refresh(module)
            logger.info(
                f"Created context module: {module.id} "
                f"(project={module.project_id}, name={module.name!r})"
            )
            return module
        except IntegrityError as e:
            session.rollback()
            raise ConstraintError(
                f"Failed to create context module (constraint violation): {e}"
            ) from e
        finally:
            session.close()

    def get_by_id(
        self, module_id: str, *, eager_load_items: bool = False
    ) -> Optional[ContextModule]:
        """Get a context module by primary key.

        Args:
            module_id: Unique context module identifier.
            eager_load_items: If True, eagerly load the memory_items
                relationship to avoid lazy-load N+1 queries.

        Returns:
            ContextModule if found, None otherwise.
        """
        session = self._get_session()
        try:
            query = session.query(ContextModule).filter_by(id=module_id)
            if eager_load_items:
                query = query.options(joinedload(ContextModule.memory_items))
            return query.first()
        finally:
            session.close()

    def list_by_project(
        self,
        project_id: str,
        *,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> PaginatedResult[ContextModule]:
        """List context modules for a project with cursor-based pagination.

        Modules are ordered by priority (ascending) then by ID for stable
        cursor pagination.

        Args:
            project_id: Required project scope filter.
            limit: Maximum items per page (default 50).
            cursor: Cursor from previous page for pagination.

        Returns:
            PaginatedResult with items, next_cursor, and has_more flag.
        """
        session = self._get_session()
        try:
            query = session.query(ContextModule).filter(
                ContextModule.project_id == project_id
            )

            # Apply cursor filter (priority asc, id asc)
            if cursor:
                cursor_id, cursor_priority = self._decode_cursor(cursor)
                query = query.filter(
                    or_(
                        ContextModule.priority > cursor_priority,
                        and_(
                            ContextModule.priority == cursor_priority,
                            ContextModule.id > cursor_id,
                        ),
                    )
                )

            query = query.order_by(
                ContextModule.priority.asc(), ContextModule.id.asc()
            )

            items = query.limit(limit + 1).all()

            has_more = len(items) > limit
            if has_more:
                items = items[:limit]

            next_cursor = (
                self._encode_cursor(items[-1], "priority")
                if items and has_more
                else None
            )

            logger.debug(
                f"Listed {len(items)} context modules "
                f"(project={project_id}, cursor={cursor}, has_more={has_more})"
            )

            return PaginatedResult(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
            )
        finally:
            session.close()

    def update(self, module_id: str, data: Dict[str, Any]) -> ContextModule:
        """Update a context module's fields.

        Sets ``updated_at`` to the current time.

        Args:
            module_id: The context module ID to update.
            data: Dictionary of fields to update.

        Returns:
            The updated ContextModule instance.

        Raises:
            NotFoundError: If no context module exists with the given ID.
        """
        session = self._get_session()
        try:
            module = session.query(ContextModule).filter_by(id=module_id).first()
            if not module:
                raise NotFoundError(f"Context module not found: {module_id}")

            for key, value in data.items():
                if hasattr(module, key):
                    setattr(module, key, value)

            module.updated_at = _now_iso()

            session.commit()
            session.refresh(module)
            logger.info(f"Updated context module: {module_id}")
            return module
        except NotFoundError:
            raise
        except Exception as e:
            session.rollback()
            raise RepositoryError(f"Failed to update context module: {e}") from e
        finally:
            session.close()

    def delete(self, module_id: str) -> bool:
        """Delete a context module by ID.

        Cascade deletes associated ModuleMemoryItem join table entries.

        Args:
            module_id: The context module ID to delete.

        Returns:
            True if the module was deleted, False if not found.
        """
        session = self._get_session()
        try:
            module = session.query(ContextModule).filter_by(id=module_id).first()
            if not module:
                return False

            session.delete(module)
            session.commit()
            logger.info(f"Deleted context module: {module_id}")
            return True
        finally:
            session.close()

    def add_memory_item(
        self, module_id: str, memory_id: str, ordering: int = 0
    ) -> None:
        """Add a memory item to a context module.

        Creates a ModuleMemoryItem association with the given ordering.
        Handles duplicate (module_id, memory_id) pairs gracefully by
        raising a ConstraintError.

        Args:
            module_id: The context module ID.
            memory_id: The memory item ID to add.
            ordering: Display/priority order within the module (default 0).

        Raises:
            NotFoundError: If the module does not exist.
            ConstraintError: If the memory item is already in the module.
        """
        with self.transaction() as session:
            module = session.query(ContextModule).filter_by(id=module_id).first()
            if not module:
                raise NotFoundError(f"Context module not found: {module_id}")

            # Check for existing link
            existing = (
                session.query(ModuleMemoryItem)
                .filter_by(module_id=module_id, memory_id=memory_id)
                .first()
            )
            if existing:
                raise ConstraintError(
                    f"Memory item {memory_id} already in module {module_id}"
                )

            link = ModuleMemoryItem(
                module_id=module_id,
                memory_id=memory_id,
                ordering=ordering,
            )
            session.add(link)
            logger.info(
                f"Added memory item {memory_id} to module {module_id} "
                f"(ordering={ordering})"
            )

    def remove_memory_item(self, module_id: str, memory_id: str) -> bool:
        """Remove a memory item from a context module.

        Args:
            module_id: The context module ID.
            memory_id: The memory item ID to remove.

        Returns:
            True if the association was removed, False if not found.
        """
        session = self._get_session()
        try:
            link = (
                session.query(ModuleMemoryItem)
                .filter_by(module_id=module_id, memory_id=memory_id)
                .first()
            )
            if not link:
                return False

            session.delete(link)
            session.commit()
            logger.info(f"Removed memory item {memory_id} from module {module_id}")
            return True
        finally:
            session.close()

    def get_memory_items(
        self, module_id: str, *, limit: int = 100
    ) -> List[MemoryItem]:
        """Get all memory items in a context module, ordered by ordering.

        Args:
            module_id: The context module ID.
            limit: Maximum number of items to return (default 100).

        Returns:
            List of MemoryItem instances ordered by their position
            within the module.
        """
        session = self._get_session()
        try:
            items = (
                session.query(MemoryItem)
                .join(
                    ModuleMemoryItem,
                    ModuleMemoryItem.memory_id == MemoryItem.id,
                )
                .filter(ModuleMemoryItem.module_id == module_id)
                .order_by(ModuleMemoryItem.ordering.asc())
                .limit(limit)
                .all()
            )
            logger.debug(
                f"Retrieved {len(items)} memory items from module {module_id}"
            )
            return items
        finally:
            session.close()

    # -------------------------------------------------------------------------
    # Cursor helpers
    # -------------------------------------------------------------------------

    def _encode_cursor(self, item: ContextModule, sort_by: str) -> str:
        """Encode an item into a cursor string.

        Args:
            item: The last item on the current page.
            sort_by: The sort field name.

        Returns:
            Base64-encoded cursor string.
        """
        value = getattr(item, sort_by, "")
        raw = f"{item.id}:{value}"
        return base64.b64encode(raw.encode()).decode()

    def _decode_cursor(self, cursor: str) -> tuple:
        """Decode a cursor string into (id, sort_value).

        Args:
            cursor: Base64-encoded cursor string.

        Returns:
            Tuple of (item_id, sort_field_value).
        """
        raw = base64.b64decode(cursor.encode()).decode()
        item_id, sort_value = raw.split(":", 1)
        return item_id, sort_value
