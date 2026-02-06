"""Context packer service for composing context packs from memory items.

This service assembles memory items into structured context packs suitable
for injection into agent prompts. It supports token-budget-aware selection,
module-based filtering via selectors, and markdown generation grouped by
memory type with confidence annotations.

Key Features:
    - Token estimation for budget-aware packing
    - Preview mode (read-only selection without markdown generation)
    - Full generation mode with grouped markdown output
    - Module selector application (type, confidence, file pattern filtering)
    - Confidence-tiered labeling in generated output

Usage:
    >>> from skillmeat.core.services.context_packer_service import ContextPackerService
    >>>
    >>> service = ContextPackerService(db_path="/path/to/db.sqlite")
    >>>
    >>> # Preview what a pack would contain
    >>> preview = service.preview_pack("proj-123", budget_tokens=4000)
    >>> print(f"Would include {preview['items_included']} items")
    >>>
    >>> # Generate a full context pack with markdown
    >>> pack = service.generate_pack("proj-123", module_id="mod-456")
    >>> print(pack["markdown"])
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from skillmeat.core.services.context_module_service import ContextModuleService
from skillmeat.core.services.memory_service import MemoryService

# Configure logging
logger = logging.getLogger(__name__)

# Statuses considered includable in context packs
_INCLUDABLE_STATUSES = frozenset({"active", "stable"})

# Display order for memory type sections in generated markdown
_TYPE_DISPLAY_ORDER = [
    "decision",
    "constraint",
    "gotcha",
    "style_rule",
    "learning",
]

# Human-readable section headings for each memory type
_TYPE_HEADINGS: Dict[str, str] = {
    "decision": "Decisions",
    "constraint": "Constraints",
    "gotcha": "Gotchas",
    "style_rule": "Style Rules",
    "learning": "Learnings",
}


# =============================================================================
# ContextPackerService
# =============================================================================


class ContextPackerService:
    """Service for composing context packs from memory items and modules.

    Combines MemoryService (item retrieval) and ContextModuleService (module
    selectors) to build token-budget-aware context packs. All public methods
    return plain dicts.

    Attributes:
        memory_service: MemoryService for memory item access
        module_service: ContextModuleService for module and selector access
    """

    def __init__(self, db_path: str):
        """Initialize ContextPackerService.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.memory_service = MemoryService(db_path=db_path)
        self.module_service = ContextModuleService(db_path=db_path)
        logger.info("ContextPackerService initialized (db_path=%s)", db_path)

    # =========================================================================
    # Token Estimation
    # =========================================================================

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate the token count for a text string.

        Uses a simple character-based heuristic (chars / 4) that provides
        a reasonable approximation for English text without requiring a
        tokenizer dependency.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count (integer, minimum 1 for non-empty text).
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    # =========================================================================
    # Pack Composition
    # =========================================================================

    def preview_pack(
        self,
        project_id: str,
        module_id: Optional[str] = None,
        budget_tokens: int = 4000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Preview what a context pack would contain without generating markdown.

        Performs read-only selection of memory items based on module selectors,
        additional filters, and token budget constraints. Items are selected
        by confidence (descending) then recency (descending).

        Args:
            project_id: Project to build the context pack for.
            module_id: Optional module whose selectors define the filter
                criteria. If None, all active/stable items for the project
                are considered.
            budget_tokens: Maximum token budget for the pack (default 4000).
            filters: Optional additional filters dict. Supported keys:
                - ``type`` (str): Filter to a single memory type.
                - ``min_confidence`` (float): Minimum confidence threshold.

        Returns:
            Dict with keys: items (list of item preview dicts), total_tokens,
            budget_tokens, utilization, items_included, items_available.
        """
        candidates = self._get_candidates(project_id, module_id, filters)
        items_available = len(candidates)

        # Select items within budget
        selected: List[Dict[str, Any]] = []
        total_tokens = 0

        for item in candidates:
            tokens = self.estimate_tokens(item["content"])
            if total_tokens + tokens > budget_tokens:
                break
            selected.append({
                "id": item["id"],
                "type": item["type"],
                "content": item["content"],
                "confidence": item["confidence"],
                "tokens": tokens,
            })
            total_tokens += tokens

        utilization = total_tokens / budget_tokens if budget_tokens > 0 else 0.0

        logger.info(
            "Preview pack: %d/%d items, %d/%d tokens (%.1f%% utilization) "
            "for project=%s",
            len(selected),
            items_available,
            total_tokens,
            budget_tokens,
            utilization * 100,
            project_id,
        )

        return {
            "items": selected,
            "total_tokens": total_tokens,
            "budget_tokens": budget_tokens,
            "utilization": utilization,
            "items_included": len(selected),
            "items_available": items_available,
        }

    def generate_pack(
        self,
        project_id: str,
        module_id: Optional[str] = None,
        budget_tokens: int = 4000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a full context pack with structured markdown output.

        Performs the same selection as preview_pack, then additionally
        generates markdown grouped by memory type with confidence annotations.

        Args:
            project_id: Project to build the context pack for.
            module_id: Optional module whose selectors define the filter
                criteria. If None, all active/stable items for the project
                are considered.
            budget_tokens: Maximum token budget for the pack (default 4000).
            filters: Optional additional filters dict. Supported keys:
                - ``type`` (str): Filter to a single memory type.
                - ``min_confidence`` (float): Minimum confidence threshold.

        Returns:
            Dict with all preview_pack keys plus:
                - ``markdown`` (str): Formatted markdown context pack.
                - ``generated_at`` (str): ISO 8601 timestamp of generation.
        """
        # Get the preview data (selection + stats)
        result = self.preview_pack(project_id, module_id, budget_tokens, filters)

        # Generate markdown from the selected items
        markdown = self._generate_markdown(result["items"])
        generated_at = datetime.now(timezone.utc).isoformat()

        result["markdown"] = markdown
        result["generated_at"] = generated_at

        logger.info(
            "Generated pack: %d items, %d tokens, markdown=%d chars "
            "for project=%s",
            result["items_included"],
            result["total_tokens"],
            len(markdown),
            project_id,
        )

        return result

    # =========================================================================
    # Module Selector Application
    # =========================================================================

    def apply_module_selectors(
        self,
        project_id: str,
        selectors: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Apply module selector rules to filter memory items.

        Queries memory items matching the selector criteria and returns
        only those with active or stable status.

        Args:
            project_id: Project to query memory items from.
            selectors: Selector criteria dict with optional keys:
                - ``memory_types`` (list[str]): Filter to specific types.
                - ``min_confidence`` (float): Minimum confidence threshold.
                - ``file_patterns`` (list[str]): File path patterns (for
                  future anchor-based filtering).
                - ``workflow_stages`` (list[str]): Workflow stage filters
                  (reserved for future use).

        Returns:
            List of matching memory item dicts with active/stable status,
            sorted by confidence DESC then created_at DESC.
        """
        memory_types = selectors.get("memory_types")
        min_confidence = selectors.get("min_confidence")

        items: List[Dict[str, Any]] = []

        if memory_types:
            # Query each type separately and merge results
            for mem_type in memory_types:
                for status in _INCLUDABLE_STATUSES:
                    result = self.memory_service.list_items(
                        project_id,
                        status=status,
                        type=mem_type,
                        min_confidence=min_confidence,
                        limit=10000,
                        sort_by="confidence",
                        sort_order="desc",
                    )
                    items.extend(result["items"])
        else:
            # No type filter -- get all active and stable items
            for status in _INCLUDABLE_STATUSES:
                result = self.memory_service.list_items(
                    project_id,
                    status=status,
                    min_confidence=min_confidence,
                    limit=10000,
                    sort_by="confidence",
                    sort_order="desc",
                )
                items.extend(result["items"])

        # Sort combined results: confidence DESC, then created_at DESC
        items = sorted(items, key=_sort_key_confidence_desc_created_desc)

        logger.debug(
            "Applied module selectors: %d items matched for project=%s "
            "(types=%s, min_confidence=%s)",
            len(items),
            project_id,
            memory_types,
            min_confidence,
        )

        return items

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _get_candidates(
        self,
        project_id: str,
        module_id: Optional[str],
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Get candidate memory items for pack composition.

        If a module_id is provided, uses its selectors to filter items.
        Otherwise, retrieves all active/stable items for the project.
        Additional filters are applied on top.

        Args:
            project_id: Project scope.
            module_id: Optional module for selector-based filtering.
            filters: Optional additional filters (type, min_confidence).

        Returns:
            List of candidate item dicts sorted by confidence DESC,
            created_at DESC.
        """
        if module_id:
            # Get module and extract selectors
            module = self.module_service.get(module_id)
            selectors = module.get("selectors") or {}

            # Merge additional filters into selectors
            if filters:
                if "type" in filters and filters["type"]:
                    # Override or narrow memory_types
                    selectors["memory_types"] = [filters["type"]]
                if "min_confidence" in filters and filters["min_confidence"] is not None:
                    # Use the stricter (higher) min_confidence
                    existing_min = selectors.get("min_confidence", 0.0)
                    selectors["min_confidence"] = max(
                        existing_min, filters["min_confidence"]
                    )

            candidates = self.apply_module_selectors(project_id, selectors)
        else:
            # No module -- build selectors from filters
            selectors: Dict[str, Any] = {}
            if filters:
                if "type" in filters and filters["type"]:
                    selectors["memory_types"] = [filters["type"]]
                if "min_confidence" in filters and filters["min_confidence"] is not None:
                    selectors["min_confidence"] = filters["min_confidence"]

            candidates = self.apply_module_selectors(project_id, selectors)

        return candidates

    @staticmethod
    def _generate_markdown(items: List[Dict[str, Any]]) -> str:
        """Generate formatted markdown from selected pack items.

        Groups items by type and orders sections according to the canonical
        type display order. Within each section, items are listed in their
        existing order (confidence descending). Confidence tiers determine
        annotation labels:
            - High (>= 0.85): no label (implied high quality)
            - Medium (0.60 - 0.84): ``[medium confidence]``
            - Low (< 0.60): ``[low confidence]``

        Args:
            items: List of item dicts with type, content, and confidence.

        Returns:
            Formatted markdown string. Returns a minimal header if no
            items are provided.
        """
        if not items:
            return "# Context Pack\n\n_No items match the current criteria._\n"

        # Group items by type
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            mem_type = item.get("type", "learning")
            if mem_type not in grouped:
                grouped[mem_type] = []
            grouped[mem_type].append(item)

        # Build markdown sections in canonical order
        sections: List[str] = ["# Context Pack"]

        for mem_type in _TYPE_DISPLAY_ORDER:
            if mem_type not in grouped:
                continue

            heading = _TYPE_HEADINGS.get(mem_type, mem_type.replace("_", " ").title())
            sections.append(f"\n## {heading}")

            for item in grouped[mem_type]:
                content = item.get("content", "").strip()
                confidence = item.get("confidence", 0.0)
                label = _confidence_label(confidence)

                if label:
                    sections.append(f"- {label} {content}")
                else:
                    sections.append(f"- {content}")

        return "\n".join(sections) + "\n"


# =============================================================================
# Module-Level Helpers
# =============================================================================


def _confidence_label(confidence: float) -> str:
    """Return the confidence tier label for markdown output.

    Args:
        confidence: Confidence score between 0.0 and 1.0.

    Returns:
        Label string, or empty string for high confidence items.
    """
    if confidence >= 0.85:
        return ""
    if confidence >= 0.60:
        return "[medium confidence]"
    return "[low confidence]"


def _sort_key_confidence_desc_created_desc(item: Dict[str, Any]) -> tuple:
    """Sort key for ordering items by confidence DESC, created_at DESC.

    Uses negated confidence for descending primary sort. For the secondary
    sort on created_at (ISO timestamp strings), inverts each character
    ordinal so that lexicographic ascending sort produces descending order.

    Args:
        item: Memory item dict with ``confidence`` and ``created_at`` keys.

    Returns:
        Tuple suitable for ascending sort that yields confidence DESC,
        created_at DESC ordering.
    """
    confidence = item.get("confidence") or 0.0
    created_at = item.get("created_at") or ""

    # Invert character ordinals so ascending sort yields descending order
    inverted_created = (
        "".join(chr(0xFFFF - ord(c)) for c in created_at)
        if created_at
        else ""
    )

    return (-confidence, inverted_created)
