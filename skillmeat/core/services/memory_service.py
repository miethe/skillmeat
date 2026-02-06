"""Memory item management service for business logic.

This service handles memory item CRUD operations, querying, and lifecycle
management. It acts as an intermediary between API routers and the
MemoryItemRepository, providing business logic validation, duplicate
detection, and response formatting.

Key Features:
    - Memory item CRUD with content-hash-based deduplication
    - Business rule validation (type, status, confidence bounds)
    - Paginated listing with multi-field filtering
    - Access count tracking on reads
    - JSON field serialization/deserialization at the DTO boundary

Usage:
    >>> from skillmeat.core.services.memory_service import MemoryService
    >>>
    >>> service = MemoryService(db_path="/path/to/db.sqlite")
    >>>
    >>> # Create a memory item
    >>> item = service.create(
    ...     project_id="proj-123",
    ...     type="decision",
    ...     content="Use SQLAlchemy for ORM layer",
    ...     confidence=0.9,
    ... )
    >>>
    >>> # List items with filtering
    >>> result = service.list_items("proj-123", type="decision", min_confidence=0.8)
    >>> for item in result["items"]:
    ...     print(item["content"])
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from skillmeat.cache.memory_repositories import MemoryItemRepository
from skillmeat.cache.repositories import ConstraintError, NotFoundError

# Configure logging
logger = logging.getLogger(__name__)

# Valid values for type and status fields, matching DB CHECK constraints
VALID_TYPES = {"decision", "constraint", "gotcha", "style_rule", "learning"}
VALID_STATUSES = {"candidate", "active", "stable", "deprecated"}

# Fields that may be updated through the update() method
UPDATABLE_FIELDS = {
    "content",
    "confidence",
    "type",
    "status",
    "provenance_json",
    "anchors_json",
    "ttl_policy_json",
}


# =============================================================================
# MemoryService
# =============================================================================


class MemoryService:
    """Service layer for memory item operations.

    Encapsulates business rules for creating, reading, updating, and deleting
    memory items. All public methods return plain dicts (the DTO boundary)
    rather than ORM model instances.

    Attributes:
        repo: MemoryItemRepository instance for data access
    """

    def __init__(self, db_path: str):
        """Initialize memory service.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.repo = MemoryItemRepository(db_path=db_path)
        logger.info("MemoryService initialized (db_path=%s)", db_path)

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create(
        self,
        project_id: str,
        type: str,
        content: str,
        confidence: float = 0.5,
        status: str = "candidate",
        provenance: Optional[Dict[str, Any]] = None,
        anchors: Optional[List[str]] = None,
        ttl_policy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new memory item with validation.

        Args:
            project_id: The project this memory belongs to.
            type: Memory type (decision, constraint, gotcha, style_rule, learning).
            content: The memory content text.
            confidence: Confidence score between 0.0 and 1.0 (default 0.5).
            status: Initial lifecycle status (default "candidate").
            provenance: Optional provenance metadata dict.
            anchors: Optional list of anchored file paths.
            ttl_policy: Optional TTL policy dict (max_age_days, max_idle_days).

        Returns:
            Dict representation of the created item. If a duplicate is
            detected (same content_hash), returns ``{"duplicate": True,
            "item": <existing item dict>}`` instead.

        Raises:
            ValueError: If any validation check fails (type, confidence,
                project_id, status).
        """
        # Validate inputs
        self._validate_project_id(project_id)
        self._validate_type(type)
        self._validate_confidence(confidence)
        self._validate_status(status)

        # Build the data dict for the repository
        data: Dict[str, Any] = {
            "project_id": project_id,
            "type": type,
            "content": content,
            "confidence": confidence,
            "status": status,
        }

        if provenance is not None:
            data["provenance_json"] = json.dumps(provenance)
        if anchors is not None:
            data["anchors_json"] = json.dumps(anchors)
        if ttl_policy is not None:
            data["ttl_policy_json"] = json.dumps(ttl_policy)

        try:
            item = self.repo.create(data)
            logger.info(
                "Created memory item %s (project=%s, type=%s)",
                item.id,
                project_id,
                type,
            )
            return self._item_to_dict(item)

        except ConstraintError:
            # Duplicate content_hash -- look up the existing item and return it
            from skillmeat.cache.memory_repositories import _compute_content_hash

            content_hash = _compute_content_hash(content)
            existing = self.repo.get_by_content_hash(content_hash)
            if existing:
                logger.info(
                    "Duplicate memory item detected (hash=%s), returning existing %s",
                    content_hash,
                    existing.id,
                )
                return {"duplicate": True, "item": self._item_to_dict(existing)}

            # Should not happen, but handle gracefully
            raise ValueError(
                "Duplicate content detected but existing item could not be found"
            )

    def get(self, item_id: str) -> Dict[str, Any]:
        """Get a memory item by ID and increment its access count.

        Args:
            item_id: Unique memory item identifier.

        Returns:
            Dict representation of the memory item.

        Raises:
            ValueError: If no memory item exists with the given ID.
        """
        item = self.repo.get_by_id(item_id)
        if not item:
            raise ValueError(f"Memory item not found: {item_id}")

        # Track access
        self.repo.increment_access_count(item_id)

        # Re-fetch to reflect the incremented count
        item = self.repo.get_by_id(item_id)
        logger.debug("Retrieved memory item %s (access_count=%s)", item_id, item.access_count)
        return self._item_to_dict(item)

    def list_items(
        self,
        project_id: str,
        status: Optional[str] = None,
        type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """List memory items with filtering and cursor-based pagination.

        Args:
            project_id: Required project scope filter.
            status: Optional status filter.
            type: Optional type filter.
            min_confidence: Optional minimum confidence threshold.
            limit: Maximum items per page (default 50).
            cursor: Cursor from a previous page.
            sort_by: Field to sort by (default "created_at").
            sort_order: Sort direction, "asc" or "desc" (default "desc").

        Returns:
            Dict with keys: items (list of dicts), next_cursor (str or None),
            has_more (bool), total (int or None).
        """
        result = self.repo.list_items(
            project_id,
            status=status,
            type=type,
            min_confidence=min_confidence,
            limit=limit,
            cursor=cursor,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "items": [self._item_to_dict(item) for item in result.items],
            "next_cursor": result.next_cursor,
            "has_more": result.has_more,
            "total": None,  # Not computed for cursor-based pagination
        }

    def update(self, item_id: str, **fields: Any) -> Dict[str, Any]:
        """Update allowed fields on a memory item.

        Only the following fields may be updated: content, confidence, type,
        status, provenance_json, anchors_json, ttl_policy_json.

        Args:
            item_id: The memory item ID to update.
            **fields: Keyword arguments for the fields to change.

        Returns:
            Dict representation of the updated memory item.

        Raises:
            ValueError: If a disallowed field is provided, or if type or
                confidence validation fails.
            NotFoundError: If no memory item exists with the given ID
                (propagated from repository).
        """
        # Filter to only allowed fields that were actually provided
        update_data: Dict[str, Any] = {}
        for key, value in fields.items():
            if key not in UPDATABLE_FIELDS:
                raise ValueError(
                    f"Field '{key}' is not updatable. "
                    f"Allowed: {sorted(UPDATABLE_FIELDS)}"
                )
            update_data[key] = value

        if not update_data:
            raise ValueError("No updatable fields provided")

        # Validate values if present
        if "confidence" in update_data:
            self._validate_confidence(update_data["confidence"])
        if "type" in update_data:
            self._validate_type(update_data["type"])
        if "status" in update_data:
            self._validate_status(update_data["status"])

        item = self.repo.update(item_id, update_data)
        logger.info("Updated memory item %s (fields=%s)", item_id, list(update_data.keys()))
        return self._item_to_dict(item)

    def delete(self, item_id: str) -> bool:
        """Delete a memory item by ID.

        Args:
            item_id: The memory item ID to delete.

        Returns:
            True if the item was deleted, False if it was not found.
        """
        deleted = self.repo.delete(item_id)
        if deleted:
            logger.info("Deleted memory item %s", item_id)
        else:
            logger.warning("Memory item not found for deletion: %s", item_id)
        return deleted

    def count(
        self,
        project_id: str,
        status: Optional[str] = None,
        type: Optional[str] = None,
    ) -> int:
        """Count memory items for a project with optional filters.

        Args:
            project_id: Project scope to count within.
            status: Optional status filter.
            type: Optional type filter.

        Returns:
            Count of matching memory items.
        """
        if type is None:
            # Repository supports status-only filtering natively
            return self.repo.count_by_project(project_id, status=status)

        # When type filter is needed, use list_items with a high limit
        # to count matches. This is acceptable for the expected dataset
        # sizes per project (typically < 1000 items).
        result = self.repo.list_items(
            project_id,
            status=status,
            type=type,
            limit=10000,
        )
        return len(result.items)

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _item_to_dict(item: Any) -> Dict[str, Any]:
        """Convert a MemoryItem ORM instance to a plain dict.

        Scalar fields are copied directly. JSON text columns are deserialized
        into their native Python types (provenance_json -> provenance, etc.).

        Args:
            item: MemoryItem ORM model instance.

        Returns:
            Dict with all item fields, JSON fields parsed into native types.
        """
        result: Dict[str, Any] = {
            "id": item.id,
            "project_id": item.project_id,
            "type": item.type,
            "content": item.content,
            "confidence": item.confidence,
            "status": item.status,
            "content_hash": item.content_hash,
            "access_count": item.access_count,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "deprecated_at": item.deprecated_at,
        }

        # Parse JSON fields using the model's property helpers
        result["provenance"] = item.provenance
        result["anchors"] = item.anchors
        result["ttl_policy"] = item.ttl_policy

        return result

    @staticmethod
    def _validate_type(type_value: str) -> None:
        """Validate that a memory type is one of the allowed values.

        Raises:
            ValueError: If the type is not in VALID_TYPES.
        """
        if type_value not in VALID_TYPES:
            raise ValueError(
                f"Invalid memory type '{type_value}'. "
                f"Must be one of: {sorted(VALID_TYPES)}"
            )

    @staticmethod
    def _validate_status(status_value: str) -> None:
        """Validate that a status is one of the allowed values.

        Raises:
            ValueError: If the status is not in VALID_STATUSES.
        """
        if status_value not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status_value}'. "
                f"Must be one of: {sorted(VALID_STATUSES)}"
            )

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        """Validate that confidence is within the allowed range [0.0, 1.0].

        Raises:
            ValueError: If confidence is outside the valid range.
        """
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {confidence}"
            )

    @staticmethod
    def _validate_project_id(project_id: str) -> None:
        """Validate that project_id is not empty.

        Raises:
            ValueError: If project_id is empty or whitespace-only.
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id must not be empty")
