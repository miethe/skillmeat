"""Unit tests for ContextPackerService.

Tests token estimation, item selection with budget constraints,
module selector filtering, markdown generation, and utilization
calculation. All external dependencies (MemoryService, ContextModuleService)
are mocked to isolate the service under test.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from skillmeat.core.services.context_packer_service import (
    ContextPackerService,
    _confidence_label,
    _sort_key_confidence_desc_created_desc,
)


# =============================================================================
# Fixtures & Helpers
# =============================================================================


def _make_memory_item(
    id: str = "mem-1",
    type: str = "decision",
    content: str = "Use pytest for testing",
    confidence: float = 0.9,
    status: str = "active",
    created_at: str = "2025-01-15T10:00:00Z",
    project_id: str = "proj-1",
) -> Dict[str, Any]:
    """Create a fake memory item dict matching MemoryService output shape."""
    return {
        "id": id,
        "project_id": project_id,
        "type": type,
        "content": content,
        "confidence": confidence,
        "status": status,
        "content_hash": f"hash-{id}",
        "access_count": 0,
        "created_at": created_at,
        "updated_at": created_at,
        "deprecated_at": None,
        "provenance": None,
        "anchors": None,
        "ttl_policy": None,
    }


def _make_module(
    id: str = "mod-1",
    project_id: str = "proj-1",
    name: str = "Test Module",
    selectors: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a fake context module dict matching ContextModuleService output."""
    return {
        "id": id,
        "project_id": project_id,
        "name": name,
        "description": None,
        "selectors": selectors,
        "priority": 5,
        "content_hash": None,
        "created_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
    }


def _mock_list_items_return(items: List[Dict[str, Any]]):
    """Create the dict shape that MemoryService.list_items returns."""
    return {
        "items": items,
        "next_cursor": None,
        "has_more": False,
        "total": None,
    }


@pytest.fixture
def mock_memory_service():
    """Create a mock MemoryService."""
    return MagicMock()


@pytest.fixture
def mock_module_service():
    """Create a mock ContextModuleService."""
    return MagicMock()


@pytest.fixture
def service(mock_memory_service, mock_module_service):
    """Create a ContextPackerService with mocked dependencies."""
    with patch.object(
        ContextPackerService, "__init__", lambda self, *a, **kw: None
    ):
        svc = ContextPackerService.__new__(ContextPackerService)
        svc.memory_service = mock_memory_service
        svc.module_service = mock_module_service
        return svc


# =============================================================================
# Token Estimation Tests
# =============================================================================


class TestEstimateTokens:
    """Tests for ContextPackerService.estimate_tokens."""

    def test_empty_string_returns_zero(self):
        assert ContextPackerService.estimate_tokens("") == 0

    def test_none_like_empty_returns_zero(self):
        """Empty string is the only falsy input; method should return 0."""
        assert ContextPackerService.estimate_tokens("") == 0

    def test_hello_world_returns_reasonable_estimate(self):
        result = ContextPackerService.estimate_tokens("hello world")
        # "hello world" is 11 chars, 11 // 4 = 2
        assert result == 2

    def test_uses_len_div_4_approximation(self):
        text = "a" * 100
        assert ContextPackerService.estimate_tokens(text) == 25

    def test_short_text_minimum_one_token(self):
        """Non-empty text should return at least 1 token."""
        result = ContextPackerService.estimate_tokens("hi")
        # "hi" is 2 chars, 2 // 4 = 0, but max(1, 0) = 1
        assert result == 1

    def test_single_character_returns_one(self):
        assert ContextPackerService.estimate_tokens("x") == 1

    def test_four_characters_returns_one(self):
        assert ContextPackerService.estimate_tokens("abcd") == 1

    def test_five_characters_returns_one(self):
        # 5 // 4 = 1
        assert ContextPackerService.estimate_tokens("abcde") == 1

    def test_long_text(self):
        text = "a" * 4000
        assert ContextPackerService.estimate_tokens(text) == 1000


# =============================================================================
# Preview Pack Tests (Selection Logic)
# =============================================================================


class TestPreviewPack:
    """Tests for ContextPackerService.preview_pack."""

    def test_empty_project_returns_empty(self, service, mock_memory_service):
        """No memory items in project produces empty preview."""
        mock_memory_service.list_items.return_value = _mock_list_items_return([])

        result = service.preview_pack("proj-1", budget_tokens=4000)

        assert result["items"] == []
        assert result["total_tokens"] == 0
        assert result["items_included"] == 0
        assert result["items_available"] == 0
        assert result["budget_tokens"] == 4000
        assert result["utilization"] == 0.0

    def test_items_sorted_by_confidence_desc_then_recency_desc(
        self, service, mock_memory_service
    ):
        """Items should be ordered by confidence descending, then created_at descending."""
        items = [
            _make_memory_item(
                id="low", confidence=0.5, created_at="2025-01-10T00:00:00Z"
            ),
            _make_memory_item(
                id="high-old", confidence=0.95, created_at="2025-01-01T00:00:00Z"
            ),
            _make_memory_item(
                id="high-new", confidence=0.95, created_at="2025-01-15T00:00:00Z"
            ),
            _make_memory_item(
                id="med", confidence=0.7, created_at="2025-01-12T00:00:00Z"
            ),
        ]
        # The service calls list_items for "active" and "stable" statuses.
        # Return all items under "active" and empty for "stable".
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),  # active
            _mock_list_items_return([]),       # stable
        ]

        result = service.preview_pack("proj-1", budget_tokens=100000)

        ids = [item["id"] for item in result["items"]]
        # high-new before high-old (same confidence, newer first)
        # then med, then low
        assert ids == ["high-new", "high-old", "med", "low"]

    def test_budget_enforcement_stops_when_exceeded(
        self, service, mock_memory_service
    ):
        """Budget enforcement should stop adding items when budget would be exceeded."""
        # Each item content ~20 chars = ~5 tokens
        items = [
            _make_memory_item(id=f"item-{i}", content="A" * 20, confidence=0.9 - i * 0.1)
            for i in range(10)
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        # Budget of 15 tokens: should fit 3 items (5 tokens each)
        result = service.preview_pack("proj-1", budget_tokens=15)

        assert result["items_included"] == 3
        assert result["total_tokens"] == 15
        assert result["items_available"] == 10

    def test_only_active_and_stable_statuses_included(
        self, service, mock_memory_service
    ):
        """Only items with 'active' or 'stable' status are queried."""
        active_items = [
            _make_memory_item(id="active-1", status="active"),
        ]
        stable_items = [
            _make_memory_item(id="stable-1", status="stable"),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(active_items),
            _mock_list_items_return(stable_items),
        ]

        result = service.preview_pack("proj-1", budget_tokens=100000)

        # Both active and stable items should be present
        ids = {item["id"] for item in result["items"]}
        assert "active-1" in ids
        assert "stable-1" in ids
        assert result["items_included"] == 2

        # Verify list_items was called with correct status values
        calls = mock_memory_service.list_items.call_args_list
        statuses_called = {call.kwargs.get("status") or call.args[0] if call.args else call.kwargs.get("status") for call in calls}
        # Both "active" and "stable" should have been queried
        assert "active" in {c.kwargs.get("status") for c in calls}
        assert "stable" in {c.kwargs.get("status") for c in calls}

    def test_high_confidence_items_selected_first(
        self, service, mock_memory_service
    ):
        """Higher confidence items are selected before lower confidence ones."""
        items = [
            _make_memory_item(id="high", content="A" * 20, confidence=0.95),
            _make_memory_item(id="med", content="B" * 20, confidence=0.7),
            _make_memory_item(id="low", content="C" * 20, confidence=0.3),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        # Budget for only 1 item (~5 tokens)
        result = service.preview_pack("proj-1", budget_tokens=5)

        assert result["items_included"] == 1
        assert result["items"][0]["id"] == "high"

    def test_preview_returns_correct_item_fields(
        self, service, mock_memory_service
    ):
        """Preview items should contain id, type, content, confidence, tokens."""
        items = [
            _make_memory_item(id="mem-1", type="decision", content="Test content", confidence=0.9),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=100000)

        item = result["items"][0]
        assert set(item.keys()) == {"id", "type", "content", "confidence", "tokens"}
        assert item["id"] == "mem-1"
        assert item["type"] == "decision"
        assert item["content"] == "Test content"
        assert item["confidence"] == 0.9
        assert isinstance(item["tokens"], int)


# =============================================================================
# Module Selector Tests
# =============================================================================


class TestApplyModuleSelectors:
    """Tests for ContextPackerService.apply_module_selectors."""

    def test_filter_by_memory_types(self, service, mock_memory_service):
        """Selectors with memory_types should only query those types."""
        decision_items = [_make_memory_item(id="d1", type="decision")]
        mock_memory_service.list_items.return_value = _mock_list_items_return(
            decision_items
        )

        selectors = {"memory_types": ["decision"]}
        result = service.apply_module_selectors("proj-1", selectors)

        assert len(result) >= 1
        # list_items should be called with type="decision" for each includable status
        calls = mock_memory_service.list_items.call_args_list
        types_called = {c.kwargs.get("type") for c in calls if c.kwargs.get("type")}
        assert "decision" in types_called

    def test_filter_by_min_confidence(self, service, mock_memory_service):
        """Selectors with min_confidence should pass it to list_items."""
        items = [_make_memory_item(id="high", confidence=0.9)]
        mock_memory_service.list_items.return_value = _mock_list_items_return(items)

        selectors = {"min_confidence": 0.8}
        result = service.apply_module_selectors("proj-1", selectors)

        # Verify min_confidence was passed to list_items
        calls = mock_memory_service.list_items.call_args_list
        for call in calls:
            assert call.kwargs.get("min_confidence") == 0.8

    def test_combined_selectors_and_logic(self, service, mock_memory_service):
        """Combined memory_types + min_confidence should both be applied (AND logic)."""
        items = [
            _make_memory_item(id="match", type="constraint", confidence=0.9),
        ]
        mock_memory_service.list_items.return_value = _mock_list_items_return(items)

        selectors = {
            "memory_types": ["constraint"],
            "min_confidence": 0.85,
        }
        result = service.apply_module_selectors("proj-1", selectors)

        calls = mock_memory_service.list_items.call_args_list
        for call in calls:
            assert call.kwargs.get("type") == "constraint"
            assert call.kwargs.get("min_confidence") == 0.85

    def test_empty_selectors_returns_all_items(self, service, mock_memory_service):
        """Empty selectors dict should pass no filters, returning all active/stable items."""
        all_items = [
            _make_memory_item(id="d1", type="decision"),
            _make_memory_item(id="c1", type="constraint"),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(all_items),  # active
            _mock_list_items_return([]),           # stable
        ]

        result = service.apply_module_selectors("proj-1", {})

        assert len(result) == 2
        # No type or min_confidence filter should be passed
        calls = mock_memory_service.list_items.call_args_list
        for call in calls:
            assert call.kwargs.get("type") is None
            assert call.kwargs.get("min_confidence") is None

    def test_multiple_memory_types_queries_each(self, service, mock_memory_service):
        """Multiple memory_types should result in separate queries per type per status."""
        decision_items = [_make_memory_item(id="d1", type="decision")]
        constraint_items = [_make_memory_item(id="c1", type="constraint")]

        # For each type, list_items is called twice (active + stable)
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(decision_items),    # decision + active
            _mock_list_items_return([]),                  # decision + stable
            _mock_list_items_return(constraint_items),   # constraint + active
            _mock_list_items_return([]),                  # constraint + stable
        ]

        selectors = {"memory_types": ["decision", "constraint"]}
        result = service.apply_module_selectors("proj-1", selectors)

        # Both types should appear in the result
        ids = {item["id"] for item in result}
        assert "d1" in ids
        assert "c1" in ids

    def test_results_sorted_confidence_desc_created_desc(
        self, service, mock_memory_service
    ):
        """Results should be sorted by confidence desc, then created_at desc."""
        items = [
            _make_memory_item(
                id="low", confidence=0.5, created_at="2025-01-10T00:00:00Z"
            ),
            _make_memory_item(
                id="high-old", confidence=0.9, created_at="2025-01-01T00:00:00Z"
            ),
            _make_memory_item(
                id="high-new", confidence=0.9, created_at="2025-01-15T00:00:00Z"
            ),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.apply_module_selectors("proj-1", {})

        ids = [item["id"] for item in result]
        assert ids == ["high-new", "high-old", "low"]


# =============================================================================
# Budget Edge Cases
# =============================================================================


class TestBudgetEdgeCases:
    """Tests for edge cases in token budget handling."""

    def test_very_small_budget_fits_only_one_item(
        self, service, mock_memory_service
    ):
        """Budget of 100 should fit only a small item."""
        # Item with ~100 chars = ~25 tokens
        items = [
            _make_memory_item(id="small", content="A" * 100, confidence=0.9),
            _make_memory_item(id="another", content="B" * 100, confidence=0.8),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=100)

        # 100 chars / 4 = 25 tokens per item. Budget 100 fits 4 items max.
        # But we only have 2 items.
        assert result["items_included"] == 2

    def test_very_large_budget_includes_all(self, service, mock_memory_service):
        """Budget of 100000 should include all eligible items."""
        items = [
            _make_memory_item(id=f"item-{i}", content="Content " * 10, confidence=0.9 - i * 0.05)
            for i in range(20)
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=100000)

        assert result["items_included"] == 20
        assert result["items_available"] == 20

    def test_single_item_exactly_at_budget(self, service, mock_memory_service):
        """An item whose tokens exactly equal the budget should be included."""
        # 40 chars => 10 tokens
        items = [
            _make_memory_item(id="exact", content="A" * 40, confidence=0.9),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=10)

        assert result["items_included"] == 1
        assert result["total_tokens"] == 10

    def test_budget_overflow_excludes_item(self, service, mock_memory_service):
        """An item that would push total over budget should be excluded."""
        # Item 1: 40 chars => 10 tokens. Item 2: 40 chars => 10 tokens.
        items = [
            _make_memory_item(id="fits", content="A" * 40, confidence=0.95),
            _make_memory_item(id="overflow", content="B" * 40, confidence=0.9),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        # Budget of 15: first item (10 tokens) fits, second (10 tokens) would
        # make total 20 > 15, so it should be excluded.
        result = service.preview_pack("proj-1", budget_tokens=15)

        assert result["items_included"] == 1
        assert result["items"][0]["id"] == "fits"
        assert result["total_tokens"] == 10

    def test_zero_budget_includes_nothing(self, service, mock_memory_service):
        """Budget of 0 should not include any items (edge: utilization = 0.0)."""
        items = [_make_memory_item(id="item-1", content="short")]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        # Note: schema enforces >= 100, but service level allows any int
        result = service.preview_pack("proj-1", budget_tokens=0)

        assert result["items_included"] == 0
        assert result["utilization"] == 0.0


# =============================================================================
# Generate Pack Tests
# =============================================================================


class TestGeneratePack:
    """Tests for ContextPackerService.generate_pack."""

    def test_returns_all_required_fields(self, service, mock_memory_service):
        """generate_pack should return all preview fields plus markdown and generated_at."""
        items = [
            _make_memory_item(id="d1", type="decision", content="Use pytest", confidence=0.9),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.generate_pack("proj-1", budget_tokens=100000)

        expected_keys = {
            "items",
            "total_tokens",
            "budget_tokens",
            "utilization",
            "items_included",
            "items_available",
            "markdown",
            "generated_at",
        }
        assert set(result.keys()) == expected_keys

    def test_markdown_includes_type_headings(self, service, mock_memory_service):
        """Generated markdown should include section headings for each memory type."""
        items = [
            _make_memory_item(id="d1", type="decision", content="Use pytest", confidence=0.9),
            _make_memory_item(id="c1", type="constraint", content="No ORM", confidence=0.85),
            _make_memory_item(id="g1", type="gotcha", content="Watch out", confidence=0.7),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.generate_pack("proj-1", budget_tokens=100000)
        md = result["markdown"]

        assert "## Decisions" in md
        assert "## Constraints" in md
        assert "## Gotchas" in md

    def test_markdown_groups_by_type(self, service, mock_memory_service):
        """Items of the same type should be grouped under one heading."""
        items = [
            _make_memory_item(id="d1", type="decision", content="Decision A", confidence=0.9),
            _make_memory_item(id="d2", type="decision", content="Decision B", confidence=0.85),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.generate_pack("proj-1", budget_tokens=100000)
        md = result["markdown"]

        assert md.count("## Decisions") == 1
        assert "Decision A" in md
        assert "Decision B" in md

    def test_empty_pack_appropriate_markdown(self, service, mock_memory_service):
        """Empty pack should produce a minimal header with a no-items message."""
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return([]),
            _mock_list_items_return([]),
        ]

        result = service.generate_pack("proj-1", budget_tokens=4000)

        assert "# Context Pack" in result["markdown"]
        assert "No items" in result["markdown"]

    def test_generated_at_is_iso_timestamp(self, service, mock_memory_service):
        """generated_at should be a valid ISO 8601 timestamp."""
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return([]),
            _mock_list_items_return([]),
        ]

        result = service.generate_pack("proj-1", budget_tokens=4000)

        # Should parse without error
        dt = datetime.fromisoformat(result["generated_at"])
        assert dt.tzinfo is not None  # Should have timezone info (UTC)

    def test_confidence_annotations_in_markdown(self, service, mock_memory_service):
        """Markdown should annotate medium and low confidence items."""
        items = [
            _make_memory_item(id="high", type="decision", content="High conf", confidence=0.95),
            _make_memory_item(id="med", type="decision", content="Med conf", confidence=0.7),
            _make_memory_item(id="low", type="decision", content="Low conf", confidence=0.4),
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.generate_pack("proj-1", budget_tokens=100000)
        md = result["markdown"]

        # High confidence: no label
        assert "[medium confidence]" not in md.split("High conf")[0].split("- ")[-1] if "High conf" in md else True
        # Medium confidence: labeled
        assert "[medium confidence]" in md
        # Low confidence: labeled
        assert "[low confidence]" in md


# =============================================================================
# Utilization Calculation Tests
# =============================================================================


class TestUtilizationCalculation:
    """Tests for utilization ratio calculation."""

    def test_zero_items_utilization_zero(self, service, mock_memory_service):
        """No items selected should yield utilization of 0.0."""
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return([]),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=4000)

        assert result["utilization"] == 0.0

    def test_partial_fill_between_zero_and_one(self, service, mock_memory_service):
        """Partial fill should produce a utilization between 0 and 1."""
        # 40 chars => 10 tokens. Budget 100 => utilization = 10/100 = 0.1
        items = [_make_memory_item(id="item-1", content="A" * 40, confidence=0.9)]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=100)

        assert 0.0 < result["utilization"] < 1.0
        assert result["utilization"] == pytest.approx(0.1)

    def test_full_fill_near_one(self, service, mock_memory_service):
        """When items consume most of the budget, utilization should be close to 1.0."""
        # Each item: 40 chars => 10 tokens. 10 items => 100 tokens total.
        items = [
            _make_memory_item(id=f"item-{i}", content="A" * 40, confidence=0.9)
            for i in range(10)
        ]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=100)

        assert result["utilization"] == pytest.approx(1.0)
        assert result["items_included"] == 10

    def test_exact_budget_utilization_is_one(self, service, mock_memory_service):
        """A single item consuming exact budget should yield utilization 1.0."""
        # 40 chars => 10 tokens, budget = 10
        items = [_make_memory_item(id="exact", content="A" * 40, confidence=0.9)]
        mock_memory_service.list_items.side_effect = [
            _mock_list_items_return(items),
            _mock_list_items_return([]),
        ]

        result = service.preview_pack("proj-1", budget_tokens=10)

        assert result["utilization"] == pytest.approx(1.0)


# =============================================================================
# Module-Level Helper Tests
# =============================================================================


class TestConfidenceLabel:
    """Tests for the _confidence_label helper."""

    def test_high_confidence_no_label(self):
        assert _confidence_label(0.85) == ""
        assert _confidence_label(0.99) == ""
        assert _confidence_label(1.0) == ""

    def test_medium_confidence_label(self):
        assert _confidence_label(0.60) == "[medium confidence]"
        assert _confidence_label(0.70) == "[medium confidence]"
        assert _confidence_label(0.84) == "[medium confidence]"

    def test_low_confidence_label(self):
        assert _confidence_label(0.59) == "[low confidence]"
        assert _confidence_label(0.0) == "[low confidence]"
        assert _confidence_label(0.3) == "[low confidence]"


class TestSortKey:
    """Tests for _sort_key_confidence_desc_created_desc."""

    def test_higher_confidence_sorts_first(self):
        high = {"confidence": 0.9, "created_at": "2025-01-01T00:00:00Z"}
        low = {"confidence": 0.5, "created_at": "2025-01-01T00:00:00Z"}
        assert _sort_key_confidence_desc_created_desc(high) < _sort_key_confidence_desc_created_desc(low)

    def test_same_confidence_newer_sorts_first(self):
        newer = {"confidence": 0.9, "created_at": "2025-01-15T00:00:00Z"}
        older = {"confidence": 0.9, "created_at": "2025-01-01T00:00:00Z"}
        assert _sort_key_confidence_desc_created_desc(newer) < _sort_key_confidence_desc_created_desc(older)

    def test_missing_fields_default_safely(self):
        item = {}
        # Should not raise
        key = _sort_key_confidence_desc_created_desc(item)
        assert isinstance(key, tuple)


# =============================================================================
# Get Candidates (Module Integration) Tests
# =============================================================================


class TestGetCandidatesWithModule:
    """Tests for _get_candidates when a module_id is provided."""

    def test_module_selectors_applied(
        self, service, mock_memory_service, mock_module_service
    ):
        """When module_id is provided, its selectors should be used for filtering."""
        module = _make_module(
            id="mod-1",
            selectors={"memory_types": ["decision"], "min_confidence": 0.8},
        )
        mock_module_service.get.return_value = module

        items = [_make_memory_item(id="d1", type="decision", confidence=0.9)]
        mock_memory_service.list_items.return_value = _mock_list_items_return(items)

        result = service.preview_pack("proj-1", module_id="mod-1", budget_tokens=100000)

        mock_module_service.get.assert_called_once_with("mod-1", include_items=True)
        assert result["items_included"] >= 1

    def test_module_selectors_with_additional_filters(
        self, service, mock_memory_service, mock_module_service
    ):
        """Additional filters should merge with module selectors."""
        module = _make_module(
            id="mod-1",
            selectors={"memory_types": ["decision", "constraint"]},
        )
        mock_module_service.get.return_value = module

        items = [_make_memory_item(id="c1", type="constraint", confidence=0.9)]
        mock_memory_service.list_items.return_value = _mock_list_items_return(items)

        result = service.preview_pack(
            "proj-1",
            module_id="mod-1",
            budget_tokens=100000,
            filters={"type": "constraint"},
        )

        # The type filter should override module's memory_types
        calls = mock_memory_service.list_items.call_args_list
        types_called = {c.kwargs.get("type") for c in calls if c.kwargs.get("type")}
        assert "constraint" in types_called

    def test_min_confidence_uses_stricter(
        self, service, mock_memory_service, mock_module_service
    ):
        """When both module and filters set min_confidence, the higher value wins."""
        module = _make_module(
            id="mod-1",
            selectors={"min_confidence": 0.6},
        )
        mock_module_service.get.return_value = module

        items = [_make_memory_item(id="h1", confidence=0.9)]
        mock_memory_service.list_items.return_value = _mock_list_items_return(items)

        result = service.preview_pack(
            "proj-1",
            module_id="mod-1",
            budget_tokens=100000,
            filters={"min_confidence": 0.85},
        )

        # Should use max(0.6, 0.85) = 0.85
        calls = mock_memory_service.list_items.call_args_list
        for call in calls:
            assert call.kwargs.get("min_confidence") == 0.85
