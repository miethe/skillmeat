"""Integration tests for context packing API endpoints.

Tests the POST /context-packs/preview and POST /context-packs/generate
endpoints including validation, mocked service responses, and error handling.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from skillmeat.api.server import app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


def _make_preview_result(
    items: List[Dict[str, Any]] | None = None,
    total_tokens: int = 0,
    budget_tokens: int = 4000,
    items_included: int = 0,
    items_available: int = 0,
) -> Dict[str, Any]:
    """Build a mock return value matching ContextPackerService.preview_pack output."""
    if items is None:
        items = []
    utilization = total_tokens / budget_tokens if budget_tokens > 0 else 0.0
    return {
        "items": items,
        "total_tokens": total_tokens,
        "budget_tokens": budget_tokens,
        "utilization": utilization,
        "items_included": items_included,
        "items_available": items_available,
    }


def _make_generate_result(
    items: List[Dict[str, Any]] | None = None,
    total_tokens: int = 0,
    budget_tokens: int = 4000,
    items_included: int = 0,
    items_available: int = 0,
    markdown: str = "# Context Pack\n\n_No items match the current criteria._\n",
    generated_at: str | None = None,
) -> Dict[str, Any]:
    """Build a mock return value matching ContextPackerService.generate_pack output."""
    result = _make_preview_result(
        items=items,
        total_tokens=total_tokens,
        budget_tokens=budget_tokens,
        items_included=items_included,
        items_available=items_available,
    )
    result["markdown"] = markdown
    result["generated_at"] = generated_at or datetime.now(timezone.utc).isoformat()
    return result


# =============================================================================
# POST /context-packs/preview Tests
# =============================================================================


class TestPreviewEndpoint:
    """Tests for POST /api/v1/context-packs/preview."""

    def test_missing_project_id_returns_422(self, client: TestClient):
        """Missing required project_id query param should return 422."""
        response = client.post(
            "/api/v1/context-packs/preview",
            json={},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_valid_request_with_defaults_returns_200(
        self, mock_get_service, client: TestClient
    ):
        """Valid request with default parameters should return 200."""
        mock_service = MagicMock()
        mock_service.preview_pack.return_value = _make_preview_result()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_tokens" in data
        assert "budget_tokens" in data
        assert "utilization" in data
        assert "items_included" in data
        assert "items_available" in data

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_with_module_filter(
        self, mock_get_service, client: TestClient
    ):
        """Request with module_id should pass it to the service."""
        mock_service = MagicMock()
        mock_service.preview_pack.return_value = _make_preview_result(
            items=[
                {"id": "m1", "type": "decision", "content": "Test", "confidence": 0.9, "tokens": 1},
            ],
            total_tokens=1,
            items_included=1,
            items_available=1,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={"module_id": "mod-1"},
        )

        assert response.status_code == 200
        mock_service.preview_pack.assert_called_once_with(
            project_id="proj-1",
            module_id="mod-1",
            budget_tokens=4000,
            filters=None,
        )

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_with_type_filter(
        self, mock_get_service, client: TestClient
    ):
        """Request with type filter should be passed through."""
        mock_service = MagicMock()
        mock_service.preview_pack.return_value = _make_preview_result()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={"filters": {"type": "decision"}},
        )

        assert response.status_code == 200
        call_args = mock_service.preview_pack.call_args
        assert call_args.kwargs["filters"] == {"type": "decision"}

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_budget_parameter_respected(
        self, mock_get_service, client: TestClient
    ):
        """Custom budget_tokens should be forwarded to the service."""
        mock_service = MagicMock()
        mock_service.preview_pack.return_value = _make_preview_result(
            budget_tokens=500
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={"budget_tokens": 500},
        )

        assert response.status_code == 200
        call_args = mock_service.preview_pack.call_args
        assert call_args.kwargs["budget_tokens"] == 500

    def test_preview_budget_below_minimum_returns_422(self, client: TestClient):
        """budget_tokens below minimum (100) should be rejected by schema validation."""
        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={"budget_tokens": 50},
        )
        assert response.status_code == 422

    def test_preview_budget_above_maximum_returns_422(self, client: TestClient):
        """budget_tokens above maximum (100000) should be rejected by schema validation."""
        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={"budget_tokens": 200000},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_returns_correct_response_shape(
        self, mock_get_service, client: TestClient
    ):
        """Response should match the ContextPackPreviewResponse schema."""
        items = [
            {"id": "m1", "type": "decision", "content": "Use pytest", "confidence": 0.9, "tokens": 3},
            {"id": "m2", "type": "constraint", "content": "No ORM", "confidence": 0.85, "tokens": 2},
        ]
        mock_service = MagicMock()
        mock_service.preview_pack.return_value = _make_preview_result(
            items=items,
            total_tokens=5,
            budget_tokens=4000,
            items_included=2,
            items_available=5,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items_included"] == 2
        assert data["items_available"] == 5
        assert data["total_tokens"] == 5
        assert data["budget_tokens"] == 4000
        assert len(data["items"]) == 2
        assert isinstance(data["utilization"], float)

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_service_value_error_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """A ValueError from the service should map to 400."""
        mock_service = MagicMock()
        mock_service.preview_pack.side_effect = ValueError("Invalid project")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=bad-project",
            json={},
        )

        assert response.status_code == 400

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_preview_service_generic_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """An unexpected exception from the service should map to 500."""
        mock_service = MagicMock()
        mock_service.preview_pack.side_effect = RuntimeError("Unexpected failure")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/preview?project_id=proj-1",
            json={},
        )

        assert response.status_code == 500


# =============================================================================
# POST /context-packs/generate Tests
# =============================================================================


class TestGenerateEndpoint:
    """Tests for POST /api/v1/context-packs/generate."""

    def test_missing_project_id_returns_422(self, client: TestClient):
        """Missing required project_id query param should return 422."""
        response = client.post(
            "/api/v1/context-packs/generate",
            json={},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_valid_request_returns_200_with_markdown(
        self, mock_get_service, client: TestClient
    ):
        """Valid request should return 200 with markdown in response."""
        markdown = "# Context Pack\n\n## Decisions\n- Use pytest\n"
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = _make_generate_result(
            items=[
                {"id": "m1", "type": "decision", "content": "Use pytest", "confidence": 0.9, "tokens": 3},
            ],
            total_tokens=3,
            items_included=1,
            items_available=1,
            markdown=markdown,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert "markdown" in data
        assert data["markdown"] == markdown

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_response_includes_generated_at(
        self, mock_get_service, client: TestClient
    ):
        """Response should include a generated_at ISO timestamp."""
        timestamp = "2025-06-15T12:00:00+00:00"
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = _make_generate_result(
            generated_at=timestamp,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["generated_at"] == timestamp
        # Validate it parses as ISO 8601
        dt = datetime.fromisoformat(data["generated_at"])
        assert dt is not None

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_markdown_is_well_formed(
        self, mock_get_service, client: TestClient
    ):
        """The markdown output should start with a heading and be a non-empty string."""
        markdown = "# Context Pack\n\n## Decisions\n- Use pytest\n"
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = _make_generate_result(
            markdown=markdown,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["markdown"].startswith("# Context Pack")
        assert len(data["markdown"]) > 0

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_response_shape(
        self, mock_get_service, client: TestClient
    ):
        """Response should match ContextPackGenerateResponse schema (superset of preview)."""
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = _make_generate_result(
            items=[
                {"id": "m1", "type": "decision", "content": "Use pytest", "confidence": 0.9, "tokens": 3},
            ],
            total_tokens=3,
            budget_tokens=4000,
            items_included=1,
            items_available=5,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        # All preview fields
        assert "items" in data
        assert "total_tokens" in data
        assert "budget_tokens" in data
        assert "utilization" in data
        assert "items_included" in data
        assert "items_available" in data
        # Plus generate-specific fields
        assert "markdown" in data
        assert "generated_at" in data

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_with_custom_budget(
        self, mock_get_service, client: TestClient
    ):
        """Custom budget should be forwarded to the service."""
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = _make_generate_result(
            budget_tokens=8000,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={"budget_tokens": 8000},
        )

        assert response.status_code == 200
        call_args = mock_service.generate_pack.call_args
        assert call_args.kwargs["budget_tokens"] == 8000

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_service_value_error_returns_400(
        self, mock_get_service, client: TestClient
    ):
        """A ValueError from the service should map to 400."""
        mock_service = MagicMock()
        mock_service.generate_pack.side_effect = ValueError("Bad module id")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={"module_id": "bad-id"},
        )

        assert response.status_code == 400

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_service_generic_error_returns_500(
        self, mock_get_service, client: TestClient
    ):
        """An unexpected exception should map to 500."""
        mock_service = MagicMock()
        mock_service.generate_pack.side_effect = RuntimeError("DB crash")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={},
        )

        assert response.status_code == 500

    def test_generate_budget_below_minimum_returns_422(self, client: TestClient):
        """budget_tokens below schema minimum should be rejected."""
        response = client.post(
            "/api/v1/context-packs/generate?project_id=proj-1",
            json={"budget_tokens": 10},
        )
        assert response.status_code == 422

    @patch("skillmeat.api.routers.context_packing._get_service")
    def test_generate_empty_project_returns_empty_markdown(
        self, mock_get_service, client: TestClient
    ):
        """An empty project should return markdown with a no-items message."""
        mock_service = MagicMock()
        mock_service.generate_pack.return_value = _make_generate_result()
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/context-packs/generate?project_id=empty-proj",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items_included"] == 0
        assert "No items" in data["markdown"]
