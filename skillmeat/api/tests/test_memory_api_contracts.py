"""API contract tests for memory items, context modules, and context packing endpoints.

Verifies that all memory/context API endpoints correctly validate requests,
return expected status codes, and produce response shapes matching their
declared schemas (MemoryItemResponse, ContextModuleResponse, pagination
envelopes, etc.).

Coverage per endpoint:
    1. Happy path (valid request -> expected status + response shape)
    2. Validation errors (invalid body -> 400/422)
    3. Not found (non-existent ID -> 404)
    4. Response schema (all required fields present)
    5. Pagination (cursor envelope: items, next_cursor, has_more, total)

Endpoint Groups:
    - Memory Items:  CRUD, lifecycle (promote/deprecate), merge
    - Context Modules: CRUD, memory associations
    - Context Packing: preview, generate (covered in test_context_packing_api.py
      for happy-path; additional contract tests here for completeness)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.server import app


# =============================================================================
# Fixtures and Helpers
# =============================================================================


@pytest.fixture(scope="function")
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


def _make_memory_item(
    id: str = "mem-001",
    project_id: str = "proj-1",
    type: str = "decision",
    content: str = "Use pytest for testing",
    confidence: float = 0.85,
    status: str = "candidate",
    provenance: Optional[Dict[str, Any]] = None,
    anchors: Optional[List[str]] = None,
    ttl_policy: Optional[Dict[str, Any]] = None,
    content_hash: str = "abc123",
    access_count: int = 0,
    created_at: str = "2025-06-15T12:00:00+00:00",
    updated_at: str = "2025-06-15T12:00:00+00:00",
    deprecated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a dict matching MemoryService return shape."""
    return {
        "id": id,
        "project_id": project_id,
        "type": type,
        "content": content,
        "confidence": confidence,
        "status": status,
        "provenance": provenance,
        "anchors": anchors,
        "ttl_policy": ttl_policy,
        "content_hash": content_hash,
        "access_count": access_count,
        "created_at": created_at,
        "updated_at": updated_at,
        "deprecated_at": deprecated_at,
    }


def _make_list_result(
    items: List[Dict[str, Any]] | None = None,
    next_cursor: Optional[str] = None,
    has_more: bool = False,
    total: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a dict matching MemoryService.list_items return shape."""
    return {
        "items": items or [],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total": total,
    }


def _make_context_module(
    id: str = "mod-001",
    project_id: str = "proj-1",
    name: str = "Test Module",
    description: Optional[str] = "A module for testing",
    selectors: Optional[Dict[str, Any]] = None,
    priority: int = 5,
    content_hash: Optional[str] = "hash123",
    created_at: str = "2025-06-15T12:00:00+00:00",
    updated_at: str = "2025-06-15T12:00:00+00:00",
    memory_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build a dict matching ContextModuleService return shape."""
    return {
        "id": id,
        "project_id": project_id,
        "name": name,
        "description": description,
        "selectors": selectors,
        "priority": priority,
        "content_hash": content_hash,
        "created_at": created_at,
        "updated_at": updated_at,
        "memory_items": memory_items,
    }


def _make_module_list_result(
    items: List[Dict[str, Any]] | None = None,
    next_cursor: Optional[str] = None,
    has_more: bool = False,
    total: Optional[int] = None,
) -> Dict[str, Any]:
    """Build a dict matching ContextModuleService.list_by_project return shape."""
    return {
        "items": items or [],
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total": total,
    }


def _assert_memory_item_shape(data: Dict[str, Any]) -> None:
    """Assert that a response dict has all required MemoryItemResponse fields."""
    required_fields = {"id", "project_id", "type", "content", "confidence", "status"}
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    assert isinstance(data["confidence"], (int, float))
    assert isinstance(data["access_count"], int)


def _assert_context_module_shape(data: Dict[str, Any]) -> None:
    """Assert that a response dict has all required ContextModuleResponse fields."""
    required_fields = {"id", "project_id", "name", "priority"}
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"
    assert isinstance(data["priority"], int)


def _assert_pagination_envelope(data: Dict[str, Any]) -> None:
    """Assert that a response dict has the standard pagination envelope fields."""
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "has_more" in data
    assert isinstance(data["has_more"], bool)
    # next_cursor and total may be None but must be present
    assert "next_cursor" in data


# =============================================================================
# Memory Items CRUD Tests
# =============================================================================


class TestMemoryItemList:
    """Tests for GET /api/v1/memory-items."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_list_returns_200_with_pagination_envelope(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: list returns 200 with proper pagination envelope."""
        items = [_make_memory_item(id=f"mem-{i}") for i in range(3)]
        mock_service = MagicMock()
        mock_service.list_items.return_value = _make_list_result(
            items=items, has_more=False, total=3
        )
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items?project_id=proj-1")

        assert response.status_code == 200
        data = response.json()
        _assert_pagination_envelope(data)
        assert len(data["items"]) == 3
        assert data["has_more"] is False
        assert data["total"] == 3
        for item in data["items"]:
            _assert_memory_item_shape(item)

    def test_list_missing_project_id_returns_422(self, client: TestClient):
        """Missing required project_id query param should return 422."""
        response = client.get("/api/v1/memory-items")
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_list_with_status_filter(self, mock_get_service, client: TestClient):
        """Filtering by status should pass through to service."""
        mock_service = MagicMock()
        mock_service.list_items.return_value = _make_list_result(items=[], total=0)
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&status=active"
        )

        assert response.status_code == 200
        call_kwargs = mock_service.list_items.call_args.kwargs
        assert call_kwargs["status"] == "active"

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_list_with_type_filter(self, mock_get_service, client: TestClient):
        """Filtering by type should pass through to service."""
        mock_service = MagicMock()
        mock_service.list_items.return_value = _make_list_result(items=[], total=0)
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&type=decision"
        )

        assert response.status_code == 200
        call_kwargs = mock_service.list_items.call_args.kwargs
        assert call_kwargs["type"] == "decision"

    def test_list_invalid_status_returns_422(self, client: TestClient):
        """Invalid status enum value should return 422."""
        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&status=invalid_status"
        )
        assert response.status_code == 422

    def test_list_invalid_type_returns_422(self, client: TestClient):
        """Invalid type enum value should return 422."""
        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&type=invalid_type"
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_list_with_min_confidence_filter(
        self, mock_get_service, client: TestClient
    ):
        """min_confidence filter should be forwarded to service."""
        mock_service = MagicMock()
        mock_service.list_items.return_value = _make_list_result(items=[], total=0)
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&min_confidence=0.8"
        )

        assert response.status_code == 200
        call_kwargs = mock_service.list_items.call_args.kwargs
        assert call_kwargs["min_confidence"] == 0.8

    def test_list_min_confidence_below_zero_returns_422(self, client: TestClient):
        """min_confidence below 0.0 should be rejected."""
        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&min_confidence=-0.1"
        )
        assert response.status_code == 422

    def test_list_min_confidence_above_one_returns_422(self, client: TestClient):
        """min_confidence above 1.0 should be rejected."""
        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&min_confidence=1.5"
        )
        assert response.status_code == 422

    def test_list_limit_above_max_returns_422(self, client: TestClient):
        """limit above 100 should be rejected."""
        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&limit=200"
        )
        assert response.status_code == 422

    def test_list_limit_below_min_returns_422(self, client: TestClient):
        """limit below 1 should be rejected."""
        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&limit=0"
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_list_with_cursor_pagination(self, mock_get_service, client: TestClient):
        """Cursor-based pagination should forward cursor to service."""
        mock_service = MagicMock()
        mock_service.list_items.return_value = _make_list_result(
            items=[_make_memory_item()],
            next_cursor="eyJpZCI6Im1lbS0wMDEifQ==",
            has_more=True,
            total=10,
        )
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/memory-items?project_id=proj-1&cursor=eyJpZCI6Im1lbS0wMDAifQ=="
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_list_service_error_returns_500(self, mock_get_service, client: TestClient):
        """Unexpected service errors should map to 500."""
        mock_service = MagicMock()
        mock_service.list_items.side_effect = RuntimeError("DB failure")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items?project_id=proj-1")
        assert response.status_code == 500


class TestMemoryItemCreate:
    """Tests for POST /api/v1/memory-items."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_create_returns_201_with_valid_body(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: valid create request returns 201 with full response shape."""
        mock_service = MagicMock()
        mock_service.create.return_value = _make_memory_item()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={
                "type": "decision",
                "content": "Use pytest for testing",
                "confidence": 0.85,
            },
        )

        assert response.status_code == 201
        data = response.json()
        _assert_memory_item_shape(data)

    def test_create_missing_project_id_returns_422(self, client: TestClient):
        """Missing project_id query param should return 422."""
        response = client.post(
            "/api/v1/memory-items",
            json={"type": "decision", "content": "Some content"},
        )
        assert response.status_code == 422

    def test_create_missing_type_returns_422(self, client: TestClient):
        """Missing required 'type' field should return 422."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={"content": "Some content"},
        )
        assert response.status_code == 422

    def test_create_missing_content_returns_422(self, client: TestClient):
        """Missing required 'content' field should return 422."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={"type": "decision"},
        )
        assert response.status_code == 422

    def test_create_empty_content_returns_422(self, client: TestClient):
        """Empty string content should be rejected by min_length=1."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={"type": "decision", "content": ""},
        )
        assert response.status_code == 422

    def test_create_invalid_type_returns_422(self, client: TestClient):
        """Invalid type enum value should return 422."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={"type": "invalid_type", "content": "Some content"},
        )
        assert response.status_code == 422

    def test_create_confidence_below_zero_returns_422(self, client: TestClient):
        """Confidence below 0.0 should be rejected."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={
                "type": "decision",
                "content": "Some content",
                "confidence": -0.1,
            },
        )
        assert response.status_code == 422

    def test_create_confidence_above_one_returns_422(self, client: TestClient):
        """Confidence above 1.0 should be rejected."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={
                "type": "decision",
                "content": "Some content",
                "confidence": 1.5,
            },
        )
        assert response.status_code == 422

    def test_create_invalid_status_returns_422(self, client: TestClient):
        """Invalid status enum value should return 422."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={
                "type": "decision",
                "content": "Some content",
                "status": "invalid",
            },
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_create_with_all_optional_fields(
        self, mock_get_service, client: TestClient
    ):
        """Create with all optional fields should succeed."""
        item = _make_memory_item(
            provenance={"source": "agent"},
            anchors=["file.py:10"],
            ttl_policy={"ttl_days": 30},
        )
        mock_service = MagicMock()
        mock_service.create.return_value = item
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={
                "type": "decision",
                "content": "Use pytest for testing",
                "confidence": 0.85,
                "status": "active",
                "provenance": {"source": "agent"},
                "anchors": ["file.py:10"],
                "ttl_policy": {"ttl_days": 30},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["provenance"] == {"source": "agent"}
        assert data["anchors"] == ["file.py:10"]
        assert data["ttl_policy"] == {"ttl_days": 30}

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_create_duplicate_returns_409(self, mock_get_service, client: TestClient):
        """Duplicate content should return 409 with existing item."""
        existing = _make_memory_item()
        mock_service = MagicMock()
        mock_service.create.return_value = {
            "duplicate": True,
            "item": existing,
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={"type": "decision", "content": "Use pytest for testing"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    def test_create_empty_body_returns_422(self, client: TestClient):
        """Completely empty body should return 422."""
        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_create_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected service errors should map to 500."""
        mock_service = MagicMock()
        mock_service.create.side_effect = RuntimeError("DB crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items?project_id=proj-1",
            json={"type": "decision", "content": "Test content"},
        )
        assert response.status_code == 500


class TestMemoryItemGet:
    """Tests for GET /api/v1/memory-items/{item_id}."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_get_returns_200_with_full_shape(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: existing item returns 200 with complete response shape."""
        mock_service = MagicMock()
        mock_service.get.return_value = _make_memory_item(id="mem-001")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items/mem-001")

        assert response.status_code == 200
        data = response.json()
        _assert_memory_item_shape(data)
        assert data["id"] == "mem-001"

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_get_not_found_returns_404(self, mock_get_service, client: TestClient):
        """Non-existent item ID should return 404."""
        mock_service = MagicMock()
        mock_service.get.side_effect = ValueError("Memory item not found: nonexistent")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items/nonexistent")

        assert response.status_code == 404

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_get_service_error_returns_500(self, mock_get_service, client: TestClient):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.get.side_effect = RuntimeError("Unexpected")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items/mem-001")
        assert response.status_code == 500


class TestMemoryItemUpdate:
    """Tests for PUT /api/v1/memory-items/{item_id}."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_update_returns_200_with_valid_body(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: valid update returns 200 with updated item."""
        updated = _make_memory_item(content="Updated content", confidence=0.95)
        mock_service = MagicMock()
        mock_service.update.return_value = updated
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"content": "Updated content", "confidence": 0.95},
        )

        assert response.status_code == 200
        data = response.json()
        _assert_memory_item_shape(data)

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_update_not_found_returns_404(self, mock_get_service, client: TestClient):
        """Updating a non-existent item should return 404."""
        mock_service = MagicMock()
        mock_service.update.side_effect = ValueError(
            "Memory item not found: nonexistent"
        )
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/memory-items/nonexistent",
            json={"content": "New content"},
        )

        assert response.status_code == 404

    def test_update_empty_body_returns_400(self, client: TestClient):
        """Empty update body (no updatable fields) should return 400."""
        # The router raises ValueError("No updatable fields provided") -> 400
        # But first, it needs to reach the router, so we need to mock the service
        # Actually, empty body {} with all Optional fields -> all None -> ValueError
        with patch("skillmeat.api.routers.memory_items._get_service") as mock_gs:
            mock_service = MagicMock()
            mock_gs.return_value = mock_service

            response = client.put(
                "/api/v1/memory-items/mem-001",
                json={},
            )

            assert response.status_code == 400

    def test_update_confidence_above_one_returns_422(self, client: TestClient):
        """Confidence above 1.0 should be rejected by schema validation."""
        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"confidence": 2.0},
        )
        assert response.status_code == 422

    def test_update_confidence_below_zero_returns_422(self, client: TestClient):
        """Confidence below 0.0 should be rejected by schema validation."""
        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"confidence": -0.5},
        )
        assert response.status_code == 422

    def test_update_empty_content_returns_422(self, client: TestClient):
        """Empty string content should be rejected by min_length=1."""
        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"content": ""},
        )
        assert response.status_code == 422

    def test_update_invalid_type_returns_422(self, client: TestClient):
        """Invalid type enum value should return 422."""
        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"type": "nonexistent_type"},
        )
        assert response.status_code == 422

    def test_update_invalid_status_returns_422(self, client: TestClient):
        """Invalid status enum value should return 422."""
        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"status": "nonexistent_status"},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_update_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.update.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/memory-items/mem-001",
            json={"content": "New content"},
        )
        assert response.status_code == 500


class TestMemoryItemDelete:
    """Tests for DELETE /api/v1/memory-items/{item_id}."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_delete_returns_204(self, mock_get_service, client: TestClient):
        """Happy path: successful delete returns 204 with no body."""
        mock_service = MagicMock()
        mock_service.delete.return_value = True
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/memory-items/mem-001")

        assert response.status_code == 204
        assert response.content == b""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_delete_not_found_returns_404(self, mock_get_service, client: TestClient):
        """Deleting a non-existent item should return 404."""
        mock_service = MagicMock()
        mock_service.delete.return_value = False
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/memory-items/nonexistent")

        assert response.status_code == 404

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_delete_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.delete.side_effect = RuntimeError("DB failure")
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/memory-items/mem-001")
        assert response.status_code == 500


class TestMemoryItemCount:
    """Tests for GET /api/v1/memory-items/count."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_count_returns_200_with_count_field(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: count returns 200 with a 'count' integer."""
        mock_service = MagicMock()
        mock_service.count.return_value = 42
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items/count?project_id=proj-1")

        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == 42

    def test_count_missing_project_id_returns_422(self, client: TestClient):
        """Missing required project_id should return 422."""
        response = client.get("/api/v1/memory-items/count")
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_count_with_filters(self, mock_get_service, client: TestClient):
        """Count with status and type filters should forward to service."""
        mock_service = MagicMock()
        mock_service.count.return_value = 5
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/memory-items/count?project_id=proj-1&status=active&type=decision"
        )

        assert response.status_code == 200
        call_kwargs = mock_service.count.call_args.kwargs
        assert call_kwargs["status"] == "active"
        assert call_kwargs["type"] == "decision"

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_count_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.count.side_effect = RuntimeError("DB crash")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/memory-items/count?project_id=proj-1")
        assert response.status_code == 500


# =============================================================================
# Memory Items Lifecycle Tests
# =============================================================================


class TestMemoryItemPromote:
    """Tests for POST /api/v1/memory-items/{item_id}/promote."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_promote_returns_200_with_updated_item(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: promote from candidate to active returns 200."""
        promoted = _make_memory_item(status="active")
        mock_service = MagicMock()
        mock_service.promote.return_value = promoted
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/promote",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        _assert_memory_item_shape(data)
        assert data["status"] == "active"

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_promote_with_reason(self, mock_get_service, client: TestClient):
        """Promote with a reason should forward reason to service."""
        promoted = _make_memory_item(status="active")
        mock_service = MagicMock()
        mock_service.promote.return_value = promoted
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/promote",
            json={"reason": "Verified by user"},
        )

        assert response.status_code == 200
        mock_service.promote.assert_called_once_with(
            "mem-001", reason="Verified by user"
        )

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_promote_not_found_returns_404(
        self, mock_get_service, client: TestClient
    ):
        """Promoting a non-existent item should return 404."""
        mock_service = MagicMock()
        mock_service.promote.side_effect = ValueError(
            "Memory item not found: nonexistent"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/nonexistent/promote",
            json={},
        )
        assert response.status_code == 404

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_promote_invalid_state_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Promoting from an invalid state (e.g., deprecated) should return 400."""
        mock_service = MagicMock()
        mock_service.promote.side_effect = ValueError(
            "Cannot promote item in status: deprecated"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/promote",
            json={},
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_promote_already_stable_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Promoting from stable (terminal state) should return 400."""
        mock_service = MagicMock()
        mock_service.promote.side_effect = ValueError(
            "Cannot promote item in status: stable"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/promote",
            json={},
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_promote_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.promote.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/promote",
            json={},
        )
        assert response.status_code == 500


class TestMemoryItemDeprecate:
    """Tests for POST /api/v1/memory-items/{item_id}/deprecate."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_deprecate_returns_200_with_deprecated_item(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: deprecate returns 200 with deprecated status."""
        deprecated = _make_memory_item(
            status="deprecated",
            deprecated_at="2025-06-15T14:00:00+00:00",
        )
        mock_service = MagicMock()
        mock_service.deprecate.return_value = deprecated
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/deprecate",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        _assert_memory_item_shape(data)
        assert data["status"] == "deprecated"
        assert data["deprecated_at"] is not None

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_deprecate_with_reason(self, mock_get_service, client: TestClient):
        """Deprecate with a reason should forward reason to service."""
        deprecated = _make_memory_item(status="deprecated")
        mock_service = MagicMock()
        mock_service.deprecate.return_value = deprecated
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/deprecate",
            json={"reason": "No longer valid"},
        )

        assert response.status_code == 200
        mock_service.deprecate.assert_called_once_with(
            "mem-001", reason="No longer valid"
        )

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_deprecate_not_found_returns_404(
        self, mock_get_service, client: TestClient
    ):
        """Deprecating a non-existent item should return 404."""
        mock_service = MagicMock()
        mock_service.deprecate.side_effect = ValueError(
            "Memory item not found: nonexistent"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/nonexistent/deprecate",
            json={},
        )
        assert response.status_code == 404

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_deprecate_already_deprecated_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Deprecating an already-deprecated item should return 400."""
        mock_service = MagicMock()
        mock_service.deprecate.side_effect = ValueError(
            "Item is already deprecated"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/deprecate",
            json={},
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_deprecate_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.deprecate.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/mem-001/deprecate",
            json={},
        )
        assert response.status_code == 500


class TestMemoryItemBulkPromote:
    """Tests for POST /api/v1/memory-items/bulk-promote."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_bulk_promote_returns_200_with_response_shape(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: bulk promote returns succeeded and failed lists."""
        mock_service = MagicMock()
        mock_service.bulk_promote.return_value = {
            "promoted": [{"id": "mem-001"}, {"id": "mem-002"}],
            "failed": [{"id": "mem-003", "error": "Already stable"}],
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/bulk-promote",
            json={"item_ids": ["mem-001", "mem-002", "mem-003"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "succeeded" in data
        assert "failed" in data
        assert len(data["succeeded"]) == 2
        assert len(data["failed"]) == 1

    def test_bulk_promote_missing_item_ids_returns_422(self, client: TestClient):
        """Missing required item_ids field should return 422."""
        response = client.post(
            "/api/v1/memory-items/bulk-promote",
            json={},
        )
        assert response.status_code == 422

    def test_bulk_promote_empty_body_returns_422(self, client: TestClient):
        """Completely empty body should return 422."""
        response = client.post(
            "/api/v1/memory-items/bulk-promote",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_bulk_promote_with_reason(self, mock_get_service, client: TestClient):
        """Bulk promote with reason should forward to service."""
        mock_service = MagicMock()
        mock_service.bulk_promote.return_value = {
            "promoted": [{"id": "mem-001"}],
            "failed": [],
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/bulk-promote",
            json={"item_ids": ["mem-001"], "reason": "Batch promotion"},
        )

        assert response.status_code == 200
        mock_service.bulk_promote.assert_called_once_with(
            item_ids=["mem-001"], reason="Batch promotion"
        )

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_bulk_promote_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.bulk_promote.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/bulk-promote",
            json={"item_ids": ["mem-001"]},
        )
        assert response.status_code == 500


class TestMemoryItemBulkDeprecate:
    """Tests for POST /api/v1/memory-items/bulk-deprecate."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_bulk_deprecate_returns_200_with_response_shape(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: bulk deprecate returns succeeded and failed lists."""
        mock_service = MagicMock()
        mock_service.bulk_deprecate.return_value = {
            "deprecated": [{"id": "mem-001"}],
            "failed": [{"id": "mem-002", "error": "Already deprecated"}],
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/bulk-deprecate",
            json={"item_ids": ["mem-001", "mem-002"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "succeeded" in data
        assert "failed" in data
        assert len(data["succeeded"]) == 1
        assert len(data["failed"]) == 1

    def test_bulk_deprecate_missing_item_ids_returns_422(self, client: TestClient):
        """Missing required item_ids field should return 422."""
        response = client.post(
            "/api/v1/memory-items/bulk-deprecate",
            json={},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_bulk_deprecate_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.bulk_deprecate.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/bulk-deprecate",
            json={"item_ids": ["mem-001"]},
        )
        assert response.status_code == 500


# =============================================================================
# Memory Items Merge Tests
# =============================================================================


class TestMemoryItemMerge:
    """Tests for POST /api/v1/memory-items/merge."""

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_returns_200_with_response_shape(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: merge returns MergeResponse with item and merged_source_id."""
        merged_item = _make_memory_item(id="mem-target", content="Merged content")
        result = dict(merged_item)
        result["merged_source_id"] = "mem-source"
        mock_service = MagicMock()
        mock_service.merge.return_value = result
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "mem-source",
                "target_id": "mem-target",
                "strategy": "keep_target",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "item" in data
        assert "merged_source_id" in data
        assert data["merged_source_id"] == "mem-source"
        _assert_memory_item_shape(data["item"])

    def test_merge_missing_required_fields_returns_422(self, client: TestClient):
        """Missing source_id or target_id should return 422."""
        response = client.post(
            "/api/v1/memory-items/merge",
            json={"source_id": "mem-001"},
        )
        assert response.status_code == 422

    def test_merge_invalid_strategy_returns_422(self, client: TestClient):
        """Invalid merge strategy should be rejected by pattern validation."""
        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "mem-001",
                "target_id": "mem-002",
                "strategy": "invalid_strategy",
            },
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_combine_without_content_allowed(
        self, mock_get_service, client: TestClient
    ):
        """Combine strategy without merged_content should be accepted at schema level."""
        merged_item = _make_memory_item(id="mem-target")
        result = dict(merged_item)
        result["merged_source_id"] = "mem-source"
        mock_service = MagicMock()
        mock_service.merge.return_value = result
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "mem-source",
                "target_id": "mem-target",
                "strategy": "combine",
            },
        )

        # Schema allows it; business logic may reject -- but it should not be 422
        assert response.status_code in (200, 400)

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_source_not_found_returns_404(
        self, mock_get_service, client: TestClient
    ):
        """Non-existent source item should return 404."""
        mock_service = MagicMock()
        mock_service.merge.side_effect = ValueError(
            "Source item not found: nonexistent"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "nonexistent",
                "target_id": "mem-002",
                "strategy": "keep_target",
            },
        )
        assert response.status_code == 404

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_target_not_found_returns_404(
        self, mock_get_service, client: TestClient
    ):
        """Non-existent target item should return 404."""
        mock_service = MagicMock()
        mock_service.merge.side_effect = ValueError(
            "Target item not found: nonexistent"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "mem-001",
                "target_id": "nonexistent",
                "strategy": "keep_target",
            },
        )
        assert response.status_code == 404

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_business_logic_error_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Business rule violations (not 'not found') should return 400."""
        mock_service = MagicMock()
        mock_service.merge.side_effect = ValueError(
            "Cannot merge: source is already deprecated"
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "mem-001",
                "target_id": "mem-002",
                "strategy": "keep_target",
            },
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.merge.side_effect = RuntimeError("DB crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/memory-items/merge",
            json={
                "source_id": "mem-001",
                "target_id": "mem-002",
                "strategy": "keep_target",
            },
        )
        assert response.status_code == 500

    def test_merge_empty_body_returns_422(self, client: TestClient):
        """Empty body should return 422 due to missing required fields."""
        response = client.post(
            "/api/v1/memory-items/merge",
            json={},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.memory_items._get_service")
    def test_merge_all_strategies_accepted(
        self, mock_get_service, client: TestClient
    ):
        """All valid strategies (keep_target, keep_source, combine) should be accepted."""
        for strategy in ("keep_target", "keep_source", "combine"):
            merged_item = _make_memory_item(id="mem-target")
            result = dict(merged_item)
            result["merged_source_id"] = "mem-source"
            mock_service = MagicMock()
            mock_service.merge.return_value = result
            mock_get_service.return_value = mock_service

            response = client.post(
                "/api/v1/memory-items/merge",
                json={
                    "source_id": "mem-source",
                    "target_id": "mem-target",
                    "strategy": strategy,
                },
            )
            assert response.status_code == 200, (
                f"Strategy '{strategy}' should be accepted but got {response.status_code}"
            )


# =============================================================================
# Context Module CRUD Tests
# =============================================================================


class TestContextModuleList:
    """Tests for GET /api/v1/context-modules."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_list_returns_200_with_pagination_envelope(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: list returns 200 with pagination envelope."""
        modules = [_make_context_module(id=f"mod-{i}") for i in range(2)]
        mock_service = MagicMock()
        mock_service.list_by_project.return_value = _make_module_list_result(
            items=modules, total=2
        )
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules?project_id=proj-1")

        assert response.status_code == 200
        data = response.json()
        _assert_pagination_envelope(data)
        assert len(data["items"]) == 2
        for item in data["items"]:
            _assert_context_module_shape(item)

    def test_list_missing_project_id_returns_422(self, client: TestClient):
        """Missing required project_id should return 422."""
        response = client.get("/api/v1/context-modules")
        assert response.status_code == 422

    def test_list_limit_above_max_returns_422(self, client: TestClient):
        """Limit above 100 should return 422."""
        response = client.get(
            "/api/v1/context-modules?project_id=proj-1&limit=200"
        )
        assert response.status_code == 422

    def test_list_limit_below_min_returns_422(self, client: TestClient):
        """Limit below 1 should return 422."""
        response = client.get(
            "/api/v1/context-modules?project_id=proj-1&limit=0"
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_list_with_cursor(self, mock_get_service, client: TestClient):
        """Cursor pagination should be forwarded to service."""
        mock_service = MagicMock()
        mock_service.list_by_project.return_value = _make_module_list_result(
            items=[_make_context_module()],
            next_cursor="eyJpZCI6Im1vZC0wMDEifQ==",
            has_more=True,
            total=10,
        )
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/context-modules?project_id=proj-1"
            "&cursor=eyJpZCI6Im1vZC0wMDAifQ=="
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_list_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.list_by_project.side_effect = RuntimeError("DB crash")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules?project_id=proj-1")
        assert response.status_code == 500


class TestContextModuleCreate:
    """Tests for POST /api/v1/context-modules."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_create_returns_201(self, mock_get_service, client: TestClient):
        """Happy path: valid create returns 201 with full shape."""
        mock_service = MagicMock()
        mock_service.create.return_value = _make_context_module()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={"name": "Test Module"},
        )

        assert response.status_code == 201
        data = response.json()
        _assert_context_module_shape(data)

    def test_create_missing_project_id_returns_422(self, client: TestClient):
        """Missing project_id should return 422."""
        response = client.post(
            "/api/v1/context-modules",
            json={"name": "Test"},
        )
        assert response.status_code == 422

    def test_create_missing_name_returns_422(self, client: TestClient):
        """Missing required name field should return 422."""
        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={},
        )
        assert response.status_code == 422

    def test_create_empty_name_returns_422(self, client: TestClient):
        """Empty string name should be rejected by min_length=1."""
        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={"name": ""},
        )
        assert response.status_code == 422

    def test_create_priority_above_max_returns_422(self, client: TestClient):
        """Priority above 100 should be rejected."""
        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={"name": "Test", "priority": 200},
        )
        assert response.status_code == 422

    def test_create_priority_below_min_returns_422(self, client: TestClient):
        """Priority below 0 should be rejected."""
        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={"name": "Test", "priority": -1},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_create_with_all_optional_fields(
        self, mock_get_service, client: TestClient
    ):
        """Create with all optional fields should succeed."""
        module = _make_context_module(
            description="Full module",
            selectors={"memory_types": ["decision"], "min_confidence": 0.8},
            priority=10,
        )
        mock_service = MagicMock()
        mock_service.create.return_value = module
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={
                "name": "Test Module",
                "description": "Full module",
                "selectors": {"memory_types": ["decision"], "min_confidence": 0.8},
                "priority": 10,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Full module"
        assert data["selectors"] is not None
        assert data["priority"] == 10

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_create_service_validation_error_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Service-level validation errors should map to 400."""
        mock_service = MagicMock()
        mock_service.create.side_effect = ValueError("Invalid selector key: foo")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={"name": "Bad Module", "selectors": {"foo": "bar"}},
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_create_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.create.side_effect = RuntimeError("DB crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules?project_id=proj-1",
            json={"name": "Test"},
        )
        assert response.status_code == 500


class TestContextModuleGet:
    """Tests for GET /api/v1/context-modules/{module_id}."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_get_returns_200_with_full_shape(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: existing module returns 200 with full shape."""
        mock_service = MagicMock()
        mock_service.get.return_value = _make_context_module(id="mod-001")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules/mod-001")

        assert response.status_code == 200
        data = response.json()
        _assert_context_module_shape(data)
        assert data["id"] == "mod-001"

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_get_not_found_returns_404(self, mock_get_service, client: TestClient):
        """Non-existent module ID should return 404."""
        mock_service = MagicMock()
        mock_service.get.side_effect = ValueError("Module not found: nonexistent")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules/nonexistent")
        assert response.status_code == 404

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_get_with_include_items(self, mock_get_service, client: TestClient):
        """include_items=true should forward to service."""
        module = _make_context_module(
            memory_items=[{"id": "mem-001", "content": "Test"}]
        )
        mock_service = MagicMock()
        mock_service.get.return_value = module
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/context-modules/mod-001?include_items=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["memory_items"] is not None
        assert len(data["memory_items"]) == 1

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_get_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.get.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules/mod-001")
        assert response.status_code == 500


class TestContextModuleUpdate:
    """Tests for PUT /api/v1/context-modules/{module_id}."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_update_returns_200(self, mock_get_service, client: TestClient):
        """Happy path: valid update returns 200."""
        updated = _make_context_module(name="Updated Name")
        mock_service = MagicMock()
        mock_service.update.return_value = updated
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/context-modules/mod-001",
            json={"name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        _assert_context_module_shape(data)

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_update_not_found_returns_404(self, mock_get_service, client: TestClient):
        """Updating a non-existent module should return 404."""
        mock_service = MagicMock()
        mock_service.update.side_effect = ValueError(
            "Module not found: nonexistent"
        )
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/context-modules/nonexistent",
            json={"name": "New Name"},
        )
        assert response.status_code == 404

    def test_update_empty_name_returns_422(self, client: TestClient):
        """Empty string name should be rejected by min_length=1."""
        response = client.put(
            "/api/v1/context-modules/mod-001",
            json={"name": ""},
        )
        assert response.status_code == 422

    def test_update_priority_above_max_returns_422(self, client: TestClient):
        """Priority above 100 should be rejected."""
        response = client.put(
            "/api/v1/context-modules/mod-001",
            json={"priority": 200},
        )
        assert response.status_code == 422

    def test_update_priority_below_min_returns_422(self, client: TestClient):
        """Priority below 0 should be rejected."""
        response = client.put(
            "/api/v1/context-modules/mod-001",
            json={"priority": -5},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_update_validation_error_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Service-level validation errors should map to 400."""
        mock_service = MagicMock()
        mock_service.update.side_effect = ValueError("Invalid selector key")
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/context-modules/mod-001",
            json={"selectors": {"invalid_key": "value"}},
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_update_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.update.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.put(
            "/api/v1/context-modules/mod-001",
            json={"name": "Updated"},
        )
        assert response.status_code == 500


class TestContextModuleDelete:
    """Tests for DELETE /api/v1/context-modules/{module_id}."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_delete_returns_204(self, mock_get_service, client: TestClient):
        """Happy path: successful delete returns 204 with no body."""
        mock_service = MagicMock()
        mock_service.delete.return_value = True
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/context-modules/mod-001")

        assert response.status_code == 204
        assert response.content == b""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_delete_not_found_returns_404(self, mock_get_service, client: TestClient):
        """Deleting a non-existent module should return 404."""
        mock_service = MagicMock()
        mock_service.delete.return_value = False
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/context-modules/nonexistent")
        assert response.status_code == 404

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_delete_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.delete.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.delete("/api/v1/context-modules/mod-001")
        assert response.status_code == 500


# =============================================================================
# Context Module Memory Association Tests
# =============================================================================


class TestContextModuleAddMemory:
    """Tests for POST /api/v1/context-modules/{module_id}/memories."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_add_memory_returns_200(self, mock_get_service, client: TestClient):
        """Happy path: adding a memory returns 200 with updated module."""
        module = _make_context_module(
            memory_items=[{"id": "mem-001", "content": "Test"}]
        )
        mock_service = MagicMock()
        mock_service.add_memory.return_value = module
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules/mod-001/memories",
            json={"memory_id": "mem-001"},
        )

        assert response.status_code == 200
        data = response.json()
        _assert_context_module_shape(data)

    def test_add_memory_missing_memory_id_returns_422(self, client: TestClient):
        """Missing required memory_id should return 422."""
        response = client.post(
            "/api/v1/context-modules/mod-001/memories",
            json={},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_add_memory_with_ordering(self, mock_get_service, client: TestClient):
        """Adding with ordering should forward to service."""
        module = _make_context_module()
        mock_service = MagicMock()
        mock_service.add_memory.return_value = module
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules/mod-001/memories",
            json={"memory_id": "mem-001", "ordering": 5},
        )

        assert response.status_code == 200
        mock_service.add_memory.assert_called_once_with(
            module_id="mod-001",
            memory_id="mem-001",
            ordering=5,
        )

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_add_memory_validation_error_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """Service-level validation errors should map to 400."""
        mock_service = MagicMock()
        mock_service.add_memory.side_effect = ValueError("Module not found")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules/nonexistent/memories",
            json={"memory_id": "mem-001"},
        )
        assert response.status_code == 400

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_add_memory_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.add_memory.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-modules/mod-001/memories",
            json={"memory_id": "mem-001"},
        )
        assert response.status_code == 500


class TestContextModuleRemoveMemory:
    """Tests for DELETE /api/v1/context-modules/{module_id}/memories/{memory_id}."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_remove_memory_returns_204(self, mock_get_service, client: TestClient):
        """Happy path: removing an association returns 204."""
        mock_service = MagicMock()
        mock_service.remove_memory.return_value = True
        mock_get_service.return_value = mock_service

        response = client.delete(
            "/api/v1/context-modules/mod-001/memories/mem-001"
        )

        assert response.status_code == 204
        assert response.content == b""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_remove_memory_not_found_returns_404(
        self, mock_get_service, client: TestClient
    ):
        """Removing a non-existent association should return 404."""
        mock_service = MagicMock()
        mock_service.remove_memory.return_value = False
        mock_get_service.return_value = mock_service

        response = client.delete(
            "/api/v1/context-modules/mod-001/memories/nonexistent"
        )
        assert response.status_code == 404

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_remove_memory_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.remove_memory.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.delete(
            "/api/v1/context-modules/mod-001/memories/mem-001"
        )
        assert response.status_code == 500


class TestContextModuleListMemories:
    """Tests for GET /api/v1/context-modules/{module_id}/memories."""

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_list_memories_returns_200_with_list(
        self, mock_get_service, client: TestClient
    ):
        """Happy path: listing module memories returns 200 with array."""
        mock_service = MagicMock()
        mock_service.get_memories.return_value = [
            {"id": "mem-001", "content": "First"},
            {"id": "mem-002", "content": "Second"},
        ]
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules/mod-001/memories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_list_memories_with_limit(self, mock_get_service, client: TestClient):
        """Limit parameter should be forwarded to service."""
        mock_service = MagicMock()
        mock_service.get_memories.return_value = []
        mock_get_service.return_value = mock_service

        response = client.get(
            "/api/v1/context-modules/mod-001/memories?limit=10"
        )

        assert response.status_code == 200
        call_kwargs = mock_service.get_memories.call_args
        assert call_kwargs.kwargs.get("limit") == 10 or call_kwargs[1].get("limit") == 10

    def test_list_memories_limit_above_max_returns_422(self, client: TestClient):
        """Limit above 1000 should return 422."""
        response = client.get(
            "/api/v1/context-modules/mod-001/memories?limit=2000"
        )
        assert response.status_code == 422

    def test_list_memories_limit_below_min_returns_422(self, client: TestClient):
        """Limit below 1 should return 422."""
        response = client.get(
            "/api/v1/context-modules/mod-001/memories?limit=0"
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_modules._get_service")
    def test_list_memories_service_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """Unexpected errors should map to 500."""
        mock_service = MagicMock()
        mock_service.get_memories.side_effect = RuntimeError("Crash")
        mock_get_service.return_value = mock_service

        response = client.get("/api/v1/context-modules/mod-001/memories")
        assert response.status_code == 500


# =============================================================================
# Context Packing Contract Tests (supplementary to test_context_packing_api.py)
# =============================================================================


class TestContextPackPreviewContract:
    """Supplementary contract tests for POST /api/v1/context-packs/preview.

    The main happy-path and error-mapping tests are in
    test_context_packing_api.py. These tests focus on additional validation
    edge cases and response shape assertions.
    """

    def test_preview_non_json_body_returns_422(self, client: TestClient):
        """Non-JSON content type should return 422."""
        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_preview_negative_budget_returns_422(self, client: TestClient):
        """Negative budget_tokens should be rejected."""
        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={"budget_tokens": -100},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_response_has_all_required_fields(
        self, mock_get_service, client: TestClient
    ):
        """Verify every field in ContextPackPreviewResponse is present."""
        mock_service = MagicMock()
        mock_service.preview_pack.return_value = {
            "items": [],
            "total_tokens": 0,
            "budget_tokens": 4000,
            "utilization": 0.0,
            "items_included": 0,
            "items_available": 0,
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        expected_fields = {
            "items", "total_tokens", "budget_tokens",
            "utilization", "items_included", "items_available",
        }
        assert expected_fields.issubset(set(data.keys()))


class TestContextPackGenerateContract:
    """Supplementary contract tests for POST /api/v1/context-packs/generate.

    The main happy-path and error-mapping tests are in
    test_context_packing_api.py. These tests focus on additional validation
    edge cases and response shape assertions.
    """

    def test_generate_non_json_body_returns_422(self, client: TestClient):
        """Non-JSON content type should return 422."""
        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_generate_negative_budget_returns_422(self, client: TestClient):
        """Negative budget_tokens should be rejected."""
        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={"budget_tokens": -100},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_response_has_all_required_fields(
        self, mock_get_service, client: TestClient
    ):
        """Verify every field in ContextPackGenerateResponse is present."""
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = {
            "items": [],
            "total_tokens": 0,
            "budget_tokens": 4000,
            "utilization": 0.0,
            "items_included": 0,
            "items_available": 0,
            "markdown": "# Pack\n",
            "generated_at": "2025-06-15T12:00:00+00:00",
        }
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        expected_fields = {
            "items", "total_tokens", "budget_tokens",
            "utilization", "items_included", "items_available",
            "markdown", "generated_at",
        }
        assert expected_fields.issubset(set(data.keys()))
