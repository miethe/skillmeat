"""Context module service for the Memory & Context Intelligence System.

This service manages context modules — named groupings of memory items with
selector criteria that define how memories are assembled into contextual
knowledge for different workflows.

Key Features:
    - CRUD operations for context modules
    - Selector validation (memory_types, min_confidence, file_patterns, workflow_stages)
    - Memory item association management (add/remove memories from modules)
    - Paginated module listings scoped by project

Usage:
    >>> from skillmeat.core.services.context_module_service import ContextModuleService
    >>>
    >>> service = ContextModuleService(db_path="/path/to/db.sqlite")
    >>>
    >>> # Create a module with selectors
    >>> module = service.create(
    ...     project_id="proj-123",
    ...     name="API Design Decisions",
    ...     selectors={"memory_types": ["decision", "constraint"], "min_confidence": 0.8},
    ... )
    >>>
    >>> # Add a memory item to the module
    >>> service.add_memory(module["id"], "memory-456", ordering=1)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from skillmeat.cache.memory_repositories import (
    ContextModuleRepository,
    MemoryItemRepository,
)
from skillmeat.cache.repositories import ConstraintError, NotFoundError
from skillmeat.observability.tracing import trace_operation

# Configure logging
logger = logging.getLogger(__name__)

# Valid keys for the selectors dict
_VALID_SELECTOR_KEYS = frozenset(
    {"memory_types", "min_confidence", "file_patterns", "workflow_stages"}
)

# Valid memory types (mirrors ck_memory_items_type constraint)
_VALID_MEMORY_TYPES = frozenset(
    {"decision", "constraint", "gotcha", "style_rule", "learning"}
)

# Updatable fields for context modules
_UPDATABLE_FIELDS = frozenset({"name", "description", "selectors", "priority"})


# =============================================================================
# ContextModuleService
# =============================================================================


class ContextModuleService:
    """Service layer for context module operations.

    Provides business logic validation, selector handling, and dict-based
    responses on top of the ContextModuleRepository and MemoryItemRepository
    data access layers.

    Attributes:
        module_repo: ContextModuleRepository for module data access
        memory_repo: MemoryItemRepository for memory item validation
    """

    def __init__(self, db_path: str):
        """Initialize ContextModuleService.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.module_repo = ContextModuleRepository(db_path=db_path)
        self.memory_repo = MemoryItemRepository(db_path=db_path)
        logger.info("ContextModuleService initialized")

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
        selectors: Optional[Dict[str, Any]] = None,
        priority: int = 5,
    ) -> Dict[str, Any]:
        """Create a new context module.

        Args:
            project_id: Project to scope the module to.
            name: Human-readable module name.
            description: Optional description of the module's purpose.
            selectors: Optional dict of selector criteria. Allowed keys:
                memory_types (list), min_confidence (float),
                file_patterns (list), workflow_stages (list).
            priority: Module priority for ordering (default 5).

        Returns:
            Dict representation of the created module.

        Raises:
            ValueError: If name or project_id is empty, or selectors are invalid.
        """
        with trace_operation(
            "context_module.create",
            project_id=project_id,
            module_name=name,
            priority=priority,
        ) as span:
            # Validate required fields
            if not project_id or not project_id.strip():
                raise ValueError("project_id must be a non-empty string")
            if not name or not name.strip():
                raise ValueError("name must be a non-empty string")

            # Validate and serialize selectors
            selectors_json = None
            if selectors is not None:
                self._validate_selectors(selectors)
                selectors_json = json.dumps(selectors)
                span.set_attribute("has_selectors", True)

            data = {
                "project_id": project_id.strip(),
                "name": name.strip(),
                "description": description,
                "selectors_json": selectors_json,
                "priority": priority,
            }

            module = self.module_repo.create(data)
            span.set_attribute("module_id", module.id)
            logger.info(
                f"Created context module: {module.id} (name={name!r})",
                extra={
                    "module_id": module.id,
                    "project_id": project_id,
                    "module_name": name,
                    "priority": priority,
                },
            )
            return self._module_to_dict(module)

    def get(self, module_id: str, include_items: bool = False) -> Dict[str, Any]:
        """Get a context module by ID.

        Args:
            module_id: Unique module identifier.
            include_items: If True, include associated memory items in response.

        Returns:
            Dict representation of the module.

        Raises:
            ValueError: If the module is not found.
        """
        module = self.module_repo.get_by_id(module_id, eager_load_items=include_items)
        if not module:
            raise ValueError(f"Context module not found: {module_id}")

        return self._module_to_dict(module, include_items=include_items)

    def list_by_project(
        self,
        project_id: str,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List context modules for a project with cursor-based pagination.

        Args:
            project_id: Project scope to list modules for.
            limit: Maximum number of modules per page (default 50).
            cursor: Cursor from previous page for pagination.

        Returns:
            Dict with keys: items (list of module dicts), next_cursor,
            has_more, total (None — not computed for performance).
        """
        result = self.module_repo.list_by_project(
            project_id, limit=limit, cursor=cursor
        )

        return {
            "items": [self._module_to_dict(m) for m in result.items],
            "next_cursor": result.next_cursor,
            "has_more": result.has_more,
            "total": getattr(result, "total", None),
        }

    def update(self, module_id: str, **fields: Any) -> Dict[str, Any]:
        """Update a context module's fields.

        Only the following fields may be updated: name, description,
        selectors, priority.

        Args:
            module_id: The module ID to update.
            **fields: Keyword arguments for fields to update.

        Returns:
            Dict representation of the updated module.

        Raises:
            ValueError: If an unsupported field is provided, or validation fails.
            NotFoundError: If the module does not exist (propagated from repo).
        """
        # Filter to only allowed fields that were actually provided
        unknown = set(fields.keys()) - _UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Cannot update fields: {', '.join(sorted(unknown))}")

        update_data: Dict[str, Any] = {}

        if "name" in fields:
            name = fields["name"]
            if not name or not str(name).strip():
                raise ValueError("name must be a non-empty string")
            update_data["name"] = str(name).strip()

        if "description" in fields:
            update_data["description"] = fields["description"]

        if "selectors" in fields:
            selectors = fields["selectors"]
            if selectors is not None:
                self._validate_selectors(selectors)
                update_data["selectors_json"] = json.dumps(selectors)
            else:
                update_data["selectors_json"] = None

        if "priority" in fields:
            update_data["priority"] = fields["priority"]

        if not update_data:
            # Nothing to update — just return the current state
            return self.get(module_id)

        module = self.module_repo.update(module_id, update_data)
        logger.info(f"Updated context module: {module_id}")
        return self._module_to_dict(module)

    def delete(self, module_id: str) -> bool:
        """Delete a context module by ID.

        Cascade deletes associated memory item links.

        Args:
            module_id: The module ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        deleted = self.module_repo.delete(module_id)
        if deleted:
            logger.info(f"Deleted context module: {module_id}")
        else:
            logger.warning(f"Context module not found for deletion: {module_id}")
        return deleted

    # =========================================================================
    # Memory Association Operations
    # =========================================================================

    def add_memory(
        self, module_id: str, memory_id: str, ordering: int = 0
    ) -> Dict[str, Any]:
        """Add a memory item to a context module.

        Verifies that both the module and the memory item exist before
        creating the association. If the memory is already linked,
        returns the module with an ``already_linked`` flag.

        Args:
            module_id: The context module ID.
            memory_id: The memory item ID to add.
            ordering: Display/priority order within the module (default 0).

        Returns:
            Dict representation of the module with items, plus an
            ``already_linked`` boolean flag.

        Raises:
            ValueError: If the module or memory item does not exist.
        """
        with trace_operation(
            "context_module.add_memory",
            module_id=module_id,
            memory_id=memory_id,
            ordering=ordering,
        ) as span:
            # Verify module exists
            module = self.module_repo.get_by_id(module_id)
            if not module:
                raise ValueError(f"Context module not found: {module_id}")

            # Verify memory item exists
            memory = self.memory_repo.get_by_id(memory_id)
            if not memory:
                raise ValueError(f"Memory item not found: {memory_id}")

            already_linked = False
            try:
                self.module_repo.add_memory_item(module_id, memory_id, ordering)
                logger.info(
                    f"Added memory {memory_id} to module {module_id} "
                    f"(ordering={ordering})",
                    extra={
                        "module_id": module_id,
                        "memory_id": memory_id,
                        "ordering": ordering,
                    },
                )
            except ConstraintError:
                already_linked = True
                span.set_attribute("already_linked", True)
                logger.info(
                    f"Memory {memory_id} already linked to module {module_id}",
                    extra={
                        "module_id": module_id,
                        "memory_id": memory_id,
                        "already_linked": True,
                    },
                )

            # Return updated module with items
            result = self.get(module_id, include_items=True)
            result["already_linked"] = already_linked
            return result

    def remove_memory(self, module_id: str, memory_id: str) -> bool:
        """Remove a memory item from a context module.

        Args:
            module_id: The context module ID.
            memory_id: The memory item ID to remove.

        Returns:
            True if the association was removed, False if not found.
        """
        removed = self.module_repo.remove_memory_item(module_id, memory_id)
        if removed:
            logger.info(f"Removed memory {memory_id} from module {module_id}")
        else:
            logger.warning(
                f"Memory link not found: module={module_id}, memory={memory_id}"
            )
        return removed

    def get_memories(self, module_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all memory items in a context module.

        Args:
            module_id: The context module ID.
            limit: Maximum number of items to return (default 100).

        Returns:
            List of memory item dicts ordered by their position in the module.
        """
        items = self.module_repo.get_memory_items(module_id, limit=limit)
        return [self._item_to_dict(item) for item in items]

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    @staticmethod
    def _validate_selectors(selectors: Dict[str, Any]) -> None:
        """Validate the structure and values of a selectors dict.

        Args:
            selectors: Dict to validate.

        Raises:
            ValueError: If the selectors dict contains invalid keys or values.
        """
        if not isinstance(selectors, dict):
            raise ValueError("selectors must be a dict")

        invalid_keys = set(selectors.keys()) - _VALID_SELECTOR_KEYS
        if invalid_keys:
            raise ValueError(
                f"Invalid selector keys: {', '.join(sorted(invalid_keys))}. "
                f"Allowed: {', '.join(sorted(_VALID_SELECTOR_KEYS))}"
            )

        # Validate memory_types
        if "memory_types" in selectors:
            types = selectors["memory_types"]
            if not isinstance(types, list):
                raise ValueError("selectors.memory_types must be a list")
            invalid_types = set(types) - _VALID_MEMORY_TYPES
            if invalid_types:
                raise ValueError(
                    f"Invalid memory types: {', '.join(sorted(invalid_types))}. "
                    f"Valid: {', '.join(sorted(_VALID_MEMORY_TYPES))}"
                )

        # Validate min_confidence
        if "min_confidence" in selectors:
            conf = selectors["min_confidence"]
            if not isinstance(conf, (int, float)):
                raise ValueError("selectors.min_confidence must be a number")
            if conf < 0.0 or conf > 1.0:
                raise ValueError("selectors.min_confidence must be between 0.0 and 1.0")

        # Validate file_patterns
        if "file_patterns" in selectors:
            patterns = selectors["file_patterns"]
            if not isinstance(patterns, list):
                raise ValueError("selectors.file_patterns must be a list")
            if not all(isinstance(p, str) for p in patterns):
                raise ValueError("selectors.file_patterns must contain only strings")

        # Validate workflow_stages
        if "workflow_stages" in selectors:
            stages = selectors["workflow_stages"]
            if not isinstance(stages, list):
                raise ValueError("selectors.workflow_stages must be a list")
            if not all(isinstance(s, str) for s in stages):
                raise ValueError("selectors.workflow_stages must contain only strings")

    # =========================================================================
    # Serialization Helpers
    # =========================================================================

    @staticmethod
    def _module_to_dict(module, include_items: bool = False) -> Dict[str, Any]:
        """Convert a ContextModule ORM instance to a dict.

        Args:
            module: ContextModule ORM model instance.
            include_items: If True, include the list of memory item dicts.

        Returns:
            Dict representation of the module.
        """
        selectors = None
        if module.selectors_json:
            selectors = json.loads(module.selectors_json)

        result: Dict[str, Any] = {
            "id": module.id,
            "project_id": module.project_id,
            "name": module.name,
            "description": module.description,
            "selectors": selectors,
            "priority": module.priority,
            "content_hash": module.content_hash,
            "created_at": module.created_at,
            "updated_at": module.updated_at,
        }

        if include_items:
            result["memory_items"] = [
                ContextModuleService._item_to_dict(item)
                for item in (module.memory_items or [])
            ]

        return result

    @staticmethod
    def _item_to_dict(item) -> Dict[str, Any]:
        """Convert a MemoryItem ORM instance to a dict.

        Args:
            item: MemoryItem ORM model instance.

        Returns:
            Dict representation of the memory item.
        """
        provenance = None
        if item.provenance_json:
            provenance = json.loads(item.provenance_json)

        anchors = None
        if item.anchors_json:
            anchors = json.loads(item.anchors_json)

        ttl_policy = None
        if item.ttl_policy_json:
            ttl_policy = json.loads(item.ttl_policy_json)

        return {
            "id": item.id,
            "project_id": item.project_id,
            "type": item.type,
            "content": item.content,
            "confidence": item.confidence,
            "status": item.status,
            "provenance": provenance,
            "anchors": anchors,
            "ttl_policy": ttl_policy,
            "content_hash": item.content_hash,
            "access_count": item.access_count,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "deprecated_at": item.deprecated_at,
        }
