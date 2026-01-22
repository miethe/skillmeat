"""Tests for Collection Refresh API endpoint.

This module tests the POST /api/v1/user-collections/{collection_id}/refresh endpoint,
including request validation, response schemas, mode handling, and error scenarios.

Test IDs: BE-311 through BE-316
"""

import pytest
from datetime import datetime
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, PropertyMock

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.api.schemas.collections import (
    RefreshModeEnum,
    RefreshRequest,
    RefreshResponse,
    RefreshSummary,
    RefreshEntryResponse,
)
from skillmeat.core.refresher import (
    RefreshResult,
    RefreshEntryResult,
    RefreshMode,
    CollectionRefresher,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def test_settings():
    """Create test settings with API key disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,  # Disable API key for testing
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def mock_collection_manager():
    """Create mock CollectionManager with test collections."""
    mock_mgr = MagicMock()
    mock_mgr.list_collections.return_value = ["default", "work", "personal"]
    return mock_mgr


@pytest.fixture
def mock_refresh_result_success():
    """Create a successful RefreshResult with mixed statuses."""
    return RefreshResult(
        refreshed_count=3,
        unchanged_count=2,
        skipped_count=1,
        error_count=0,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:canvas-design",
                status="refreshed",
                changes=["description", "tags"],
                old_values={"description": "Old description", "tags": []},
                new_values={"description": "New description", "tags": ["design", "ui"]},
                duration_ms=150.5,
            ),
            RefreshEntryResult(
                artifact_id="skill:pdf-skill",
                status="refreshed",
                changes=["description"],
                old_values={"description": "PDF tool"},
                new_values={"description": "PDF processing tool"},
                duration_ms=120.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:excel-skill",
                status="refreshed",
                changes=["tags"],
                old_values={"tags": []},
                new_values={"tags": ["excel", "spreadsheet"]},
                duration_ms=100.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:word-skill",
                status="unchanged",
                changes=[],
                duration_ms=80.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:doc-skill",
                status="unchanged",
                changes=[],
                duration_ms=75.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:local-skill",
                status="skipped",
                changes=[],
                reason="No GitHub source",
                duration_ms=5.0,
            ),
        ],
        duration_ms=530.5,
    )


@pytest.fixture
def mock_refresh_result_partial():
    """Create a RefreshResult with some errors."""
    return RefreshResult(
        refreshed_count=2,
        unchanged_count=1,
        skipped_count=0,
        error_count=2,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:canvas-design",
                status="refreshed",
                changes=["description"],
                old_values={"description": "Old"},
                new_values={"description": "New"},
                duration_ms=150.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:pdf-skill",
                status="refreshed",
                changes=["tags"],
                old_values={"tags": []},
                new_values={"tags": ["pdf"]},
                duration_ms=100.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:word-skill",
                status="unchanged",
                changes=[],
                duration_ms=50.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:error-skill-1",
                status="error",
                changes=[],
                error="Rate limit exceeded",
                reason="GitHub API rate limit",
                duration_ms=10.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:error-skill-2",
                status="error",
                changes=[],
                error="Repository not found",
                reason="GitHub API error",
                duration_ms=15.0,
            ),
        ],
        duration_ms=325.0,
    )


@pytest.fixture
def mock_refresh_result_all_errors():
    """Create a RefreshResult where all artifacts failed."""
    return RefreshResult(
        refreshed_count=0,
        unchanged_count=0,
        skipped_count=0,
        error_count=3,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:fail-1",
                status="error",
                changes=[],
                error="Connection timeout",
                reason="Network error",
                duration_ms=5000.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:fail-2",
                status="error",
                changes=[],
                error="Authentication failed",
                reason="Invalid token",
                duration_ms=100.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:fail-3",
                status="error",
                changes=[],
                error="Rate limit exceeded",
                reason="GitHub API rate limit",
                duration_ms=50.0,
            ),
        ],
        duration_ms=5150.0,
    )


@pytest.fixture
def mock_refresh_result_dry_run():
    """Create a RefreshResult for dry-run mode."""
    return RefreshResult(
        refreshed_count=2,
        unchanged_count=1,
        skipped_count=0,
        error_count=0,
        entries=[
            RefreshEntryResult(
                artifact_id="skill:canvas-design",
                status="refreshed",
                changes=["description", "tags"],
                old_values={"description": "Old", "tags": []},
                new_values={"description": "New", "tags": ["design"]},
                reason="Dry run - changes not applied",
                duration_ms=150.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:pdf-skill",
                status="refreshed",
                changes=["description"],
                old_values={"description": "Old PDF"},
                new_values={"description": "New PDF"},
                reason="Dry run - changes not applied",
                duration_ms=100.0,
            ),
            RefreshEntryResult(
                artifact_id="skill:word-skill",
                status="unchanged",
                changes=[],
                duration_ms=50.0,
            ),
        ],
        duration_ms=300.0,
    )


@pytest.fixture
def client(app, mock_collection_manager):
    """Create test client with dependency overrides."""
    from skillmeat.api.dependencies import get_collection_manager
    from skillmeat.api.middleware.auth import verify_token

    # Override dependencies
    app.dependency_overrides[get_collection_manager] = lambda: mock_collection_manager
    app.dependency_overrides[verify_token] = lambda: "mock-token"

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


# =============================================================================
# Unit Tests for Endpoint Signature (BE-311)
# =============================================================================


class TestRefreshEndpointSignature:
    """Test endpoint responds correctly to HTTP requests."""

    def test_refresh_endpoint_signature(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Verify endpoint responds to POST with correct path."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK

    def test_refresh_endpoint_get_not_allowed(self, client):
        """Verify GET method is not allowed."""
        response = client.get("/api/v1/user-collections/default/refresh")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_refresh_endpoint_put_not_allowed(self, client):
        """Verify PUT method is not allowed."""
        response = client.put(
            "/api/v1/user-collections/default/refresh",
            json={"mode": "metadata_only"},
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_refresh_endpoint_delete_not_allowed(self, client):
        """Verify DELETE method is not allowed."""
        response = client.delete("/api/v1/user-collections/default/refresh")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# =============================================================================
# Unit Tests for Collection Not Found (BE-312)
# =============================================================================


class TestRefreshCollectionNotFound:
    """Test 404 responses for non-existent collections."""

    def test_refresh_collection_not_found(self, client, mock_collection_manager):
        """Returns 404 for non-existent collection."""
        # Mock returns list that doesn't include 'nonexistent'
        mock_collection_manager.list_collections.return_value = ["default", "work"]

        response = client.post(
            "/api/v1/user-collections/nonexistent/refresh",
            json={"mode": "metadata_only"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "nonexistent" in data["detail"]

    def test_refresh_collection_empty_id(self, client):
        """Returns 404 for empty collection ID (handled by routing)."""
        response = client.post(
            "/api/v1/user-collections//refresh",
            json={"mode": "metadata_only"},
        )
        # FastAPI returns 404 for invalid path
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_refresh_collection_special_chars(self, client, mock_collection_manager):
        """Returns 404 for collection with invalid special characters."""
        mock_collection_manager.list_collections.return_value = ["default"]

        response = client.post(
            "/api/v1/user-collections/invalid%2Fcollection/refresh",
            json={"mode": "metadata_only"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Unit Tests for Request Body Validation (BE-313)
# =============================================================================


class TestRefreshRequestBodyValidation:
    """Test request body validation."""

    def test_refresh_request_body_valid_metadata_only(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Valid RefreshRequest with metadata_only mode deserializes correctly."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "metadata_only"
        assert data["dry_run"] is False

    def test_refresh_request_body_valid_check_only(
        self, client, mock_collection_manager, mock_refresh_result_dry_run
    ):
        """Valid RefreshRequest with check_only mode deserializes correctly."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_dry_run,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "check_only", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "check_only"

    def test_refresh_request_body_valid_sync(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Valid RefreshRequest with sync mode deserializes correctly."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "sync", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "sync"

    def test_refresh_request_body_with_filter(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Valid RefreshRequest with artifact_filter deserializes correctly."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={
                    "mode": "metadata_only",
                    "artifact_filter": {"type": "skill"},
                    "dry_run": False,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        # Verify filter was passed to refresher
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("artifact_filter") == {"type": "skill"}

    def test_refresh_request_body_default_values(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """RefreshRequest uses defaults when minimal body provided."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            # Only mode is technically required based on schema defaults
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={},  # All defaults
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "metadata_only"  # Default mode
        assert data["dry_run"] is False  # Default dry_run


class TestRefreshRequestBodyInvalid:
    """Test invalid request body handling (BE-314)."""

    def test_refresh_request_body_invalid_mode(self, client, mock_collection_manager):
        """Invalid mode returns 422."""
        response = client.post(
            "/api/v1/user-collections/default/refresh",
            json={"mode": "invalid_mode"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_refresh_request_body_invalid_dry_run_type(
        self, client, mock_collection_manager
    ):
        """Invalid dry_run type returns 422."""
        response = client.post(
            "/api/v1/user-collections/default/refresh",
            json={
                "mode": "metadata_only",
                "dry_run": ["not", "a", "boolean"],
            },  # Should be boolean
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_refresh_request_body_invalid_filter_type(
        self, client, mock_collection_manager
    ):
        """Invalid artifact_filter type returns 422."""
        response = client.post(
            "/api/v1/user-collections/default/refresh",
            json={"mode": "metadata_only", "artifact_filter": "not-a-dict"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_refresh_request_body_not_json(self, client, mock_collection_manager):
        """Non-JSON body returns 422."""
        response = client.post(
            "/api/v1/user-collections/default/refresh",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Unit Tests for Query Parameter Mode Override (BE-315)
# =============================================================================


class TestRefreshQueryParamModeOverride:
    """Test query parameter overrides request body mode."""

    def test_refresh_query_param_mode_override(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Query param ?mode= overrides request body mode."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh?mode=sync",
                json={"mode": "metadata_only", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Response should reflect the query param mode
        assert data["mode"] == "sync"

        # Verify core refresher was called with sync mode
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("mode") == RefreshMode.SYNC

    def test_refresh_query_param_check_only_override(
        self, client, mock_collection_manager, mock_refresh_result_dry_run
    ):
        """Query param ?mode=check_only overrides body."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_dry_run,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh?mode=check_only",
                json={"mode": "sync"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["mode"] == "check_only"

        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("mode") == RefreshMode.CHECK_ONLY

    @pytest.mark.parametrize(
        "query_mode,expected_core_mode",
        [
            ("metadata_only", RefreshMode.METADATA_ONLY),
            ("check_only", RefreshMode.CHECK_ONLY),
            ("sync", RefreshMode.SYNC),
        ],
    )
    def test_refresh_query_param_all_modes(
        self,
        client,
        mock_collection_manager,
        mock_refresh_result_success,
        query_mode,
        expected_core_mode,
    ):
        """Query param works for all valid mode values."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ) as mock_refresh:
            response = client.post(
                f"/api/v1/user-collections/default/refresh?mode={query_mode}",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_200_OK
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("mode") == expected_core_mode

    def test_refresh_query_param_invalid_mode(self, client, mock_collection_manager):
        """Invalid query param mode returns 422."""
        response = client.post(
            "/api/v1/user-collections/default/refresh?mode=invalid",
            json={"mode": "metadata_only"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Unit Tests for Dry Run Mode (BE-316)
# =============================================================================


class TestRefreshDryRunMode:
    """Test dry_run=true doesn't persist changes."""

    def test_refresh_dry_run_mode(
        self, client, mock_collection_manager, mock_refresh_result_dry_run
    ):
        """dry_run=true in request body triggers dry run."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_dry_run,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only", "dry_run": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dry_run"] is True

        # Verify dry_run was passed to refresher
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("dry_run") is True

    def test_refresh_dry_run_shows_would_change(
        self, client, mock_collection_manager, mock_refresh_result_dry_run
    ):
        """Dry run response shows what would change without applying."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_dry_run,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only", "dry_run": True},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response includes details about changes
        assert "details" in data
        refreshed_entries = [e for e in data["details"] if e["status"] == "refreshed"]
        assert len(refreshed_entries) > 0

        # Verify each refreshed entry has old/new values
        for entry in refreshed_entries:
            assert "changes" in entry
            assert len(entry["changes"]) > 0
            assert "old_values" in entry
            assert "new_values" in entry

    def test_refresh_dry_run_false_persists(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """dry_run=false allows persistence."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["dry_run"] is False

        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("dry_run") is False


# =============================================================================
# Integration Tests - Full Flow (BE-317)
# =============================================================================


class TestRefreshEndpointFullFlow:
    """End-to-end tests with mocked GitHub."""

    def test_refresh_endpoint_full_flow(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """End-to-end test with mocked GitHub."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only", "dry_run": False},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert data["collection_id"] == "default"
        assert data["status"] == "completed"
        assert "timestamp" in data
        assert data["mode"] == "metadata_only"
        assert data["dry_run"] is False

        # Verify summary
        summary = data["summary"]
        assert summary["total_processed"] == 6
        assert summary["refreshed_count"] == 3
        assert summary["unchanged_count"] == 2
        assert summary["skipped_count"] == 1
        assert summary["error_count"] == 0
        assert summary["success_rate"] == 83.33  # (3+2)/6 * 100

        # Verify details
        assert len(data["details"]) == 6
        assert data["duration_ms"] > 0

    def test_refresh_endpoint_response_structure(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Verify complete response structure matches schema."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required fields are present
        required_fields = [
            "collection_id",
            "status",
            "timestamp",
            "mode",
            "dry_run",
            "summary",
            "details",
            "duration_ms",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Verify summary structure
        summary_fields = [
            "total_processed",
            "refreshed_count",
            "unchanged_count",
            "skipped_count",
            "error_count",
            "success_rate",
        ]
        for field in summary_fields:
            assert field in data["summary"], f"Missing summary field: {field}"

        # Verify detail entry structure
        for entry in data["details"]:
            assert "artifact_id" in entry
            assert "status" in entry
            assert "changes" in entry
            assert "duration_ms" in entry


class TestRefreshEndpointErrorHandling:
    """Test error handling for various failure scenarios (BE-318)."""

    def test_refresh_endpoint_error_handling(self, client, mock_collection_manager):
        """GitHub errors return 500 with proper message."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            side_effect=Exception("GitHub API connection failed"),
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "Failed to refresh collection" in data["detail"]

    def test_refresh_endpoint_partial_success(
        self, client, mock_collection_manager, mock_refresh_result_partial
    ):
        """Some artifacts fail, others succeed - returns 200 with partial status."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_partial,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Partial success should return "partial" status
        assert data["status"] == "partial"
        assert data["summary"]["refreshed_count"] == 2
        assert data["summary"]["error_count"] == 2

        # Verify error details are included
        error_entries = [e for e in data["details"] if e["status"] == "error"]
        assert len(error_entries) == 2
        for entry in error_entries:
            assert "error" in entry
            assert entry["error"] is not None

    def test_refresh_endpoint_all_errors(
        self, client, mock_collection_manager, mock_refresh_result_all_errors
    ):
        """All artifacts fail - returns 200 with failed status."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_all_errors,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All failures should return "failed" status
        assert data["status"] == "failed"
        assert data["summary"]["error_count"] == 3
        assert data["summary"]["refreshed_count"] == 0
        assert data["summary"]["success_rate"] == 0.0


# =============================================================================
# Schema Tests
# =============================================================================


class TestRefreshResponseFromRefreshResult:
    """Test RefreshResponse.from_refresh_result factory method."""

    def test_refresh_response_from_refresh_result(self, mock_refresh_result_success):
        """Factory method works correctly for success result."""
        response = RefreshResponse.from_refresh_result(
            collection_id="test-collection",
            result=mock_refresh_result_success,
            mode=RefreshModeEnum.METADATA_ONLY,
            dry_run=False,
        )

        assert response.collection_id == "test-collection"
        assert response.status == "completed"
        assert response.mode == RefreshModeEnum.METADATA_ONLY
        assert response.dry_run is False
        assert response.summary.total_processed == 6
        assert response.summary.refreshed_count == 3
        assert len(response.details) == 6

    def test_refresh_response_from_partial_result(self, mock_refresh_result_partial):
        """Factory method correctly sets partial status."""
        response = RefreshResponse.from_refresh_result(
            collection_id="test-collection",
            result=mock_refresh_result_partial,
            mode=RefreshModeEnum.SYNC,
            dry_run=True,
        )

        assert response.status == "partial"
        assert response.mode == RefreshModeEnum.SYNC
        assert response.dry_run is True
        assert response.summary.error_count == 2

    def test_refresh_response_from_failed_result(self, mock_refresh_result_all_errors):
        """Factory method correctly sets failed status."""
        response = RefreshResponse.from_refresh_result(
            collection_id="test-collection",
            result=mock_refresh_result_all_errors,
            mode=RefreshModeEnum.CHECK_ONLY,
            dry_run=False,
        )

        assert response.status == "failed"
        assert response.summary.error_count == 3
        assert response.summary.refreshed_count == 0


class TestRefreshSummaryCalculation:
    """Test RefreshSummary field calculations."""

    def test_refresh_summary_calculation(self, mock_refresh_result_success):
        """Counts and success_rate calculated correctly."""
        summary = RefreshSummary(
            total_processed=mock_refresh_result_success.total_processed,
            refreshed_count=mock_refresh_result_success.refreshed_count,
            unchanged_count=mock_refresh_result_success.unchanged_count,
            skipped_count=mock_refresh_result_success.skipped_count,
            error_count=mock_refresh_result_success.error_count,
            success_rate=mock_refresh_result_success.success_rate,
        )

        assert summary.total_processed == 6
        assert summary.refreshed_count == 3
        assert summary.unchanged_count == 2
        assert summary.skipped_count == 1
        assert summary.error_count == 0
        # Success rate = (refreshed + unchanged) / total * 100
        # = (3 + 2) / 6 * 100 = 83.33%
        assert summary.success_rate == 83.33

    def test_refresh_summary_zero_total(self):
        """Handle zero total processed correctly."""
        result = RefreshResult(
            refreshed_count=0,
            unchanged_count=0,
            skipped_count=0,
            error_count=0,
            entries=[],
            duration_ms=0.0,
        )

        assert result.total_processed == 0
        assert result.success_rate == 0.0

    def test_refresh_summary_all_unchanged(self):
        """100% success when all unchanged."""
        result = RefreshResult(
            refreshed_count=0,
            unchanged_count=5,
            skipped_count=0,
            error_count=0,
            entries=[],
            duration_ms=100.0,
        )

        assert result.total_processed == 5
        assert result.success_rate == 100.0

    def test_refresh_summary_all_skipped(self):
        """0% success when all skipped."""
        result = RefreshResult(
            refreshed_count=0,
            unchanged_count=0,
            skipped_count=5,
            error_count=0,
            entries=[],
            duration_ms=100.0,
        )

        assert result.total_processed == 5
        assert result.success_rate == 0.0


# =============================================================================
# Edge Cases and Additional Tests
# =============================================================================


class TestRefreshEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_refresh_empty_collection(self, client, mock_collection_manager):
        """Refresh empty collection returns appropriate response."""
        empty_result = RefreshResult(
            refreshed_count=0,
            unchanged_count=0,
            skipped_count=0,
            error_count=0,
            entries=[],
            duration_ms=10.0,
        )

        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=empty_result,
        ):
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "completed"
        assert data["summary"]["total_processed"] == 0
        assert len(data["details"]) == 0

    def test_refresh_with_name_pattern_filter(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Filter by name pattern is passed correctly."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={
                    "mode": "metadata_only",
                    "artifact_filter": {"name": "canvas-*"},
                },
            )

        assert response.status_code == status.HTTP_200_OK
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("artifact_filter") == {"name": "canvas-*"}

    def test_refresh_with_combined_filters(
        self, client, mock_collection_manager, mock_refresh_result_success
    ):
        """Multiple filters are passed correctly."""
        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ) as mock_refresh:
            response = client.post(
                "/api/v1/user-collections/default/refresh",
                json={
                    "mode": "sync",
                    "artifact_filter": {"type": "skill", "name": "pdf-*"},
                    "dry_run": True,
                },
            )

        assert response.status_code == status.HTTP_200_OK
        mock_refresh.assert_called_once()
        call_kwargs = mock_refresh.call_args.kwargs
        assert call_kwargs.get("artifact_filter") == {"type": "skill", "name": "pdf-*"}
        assert call_kwargs.get("dry_run") is True

    @pytest.mark.parametrize(
        "collection_id",
        [
            "default",
            "work",
            "personal",
            "my-collection-123",
        ],
    )
    def test_refresh_various_collection_ids(
        self,
        client,
        mock_collection_manager,
        mock_refresh_result_success,
        collection_id,
    ):
        """Refresh works for various valid collection IDs."""
        mock_collection_manager.list_collections.return_value = [
            "default",
            "work",
            "personal",
            "my-collection-123",
        ]

        with patch.object(
            CollectionRefresher,
            "refresh_collection",
            return_value=mock_refresh_result_success,
        ):
            response = client.post(
                f"/api/v1/user-collections/{collection_id}/refresh",
                json={"mode": "metadata_only"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["collection_id"] == collection_id

    def test_refresh_entry_response_all_fields(self):
        """RefreshEntryResponse includes all optional fields when present."""
        entry = RefreshEntryResponse(
            artifact_id="skill:test",
            status="refreshed",
            changes=["description", "tags"],
            old_values={"description": "old", "tags": []},
            new_values={"description": "new", "tags": ["tag1"]},
            error=None,
            reason="Update successful",
            duration_ms=100.0,
        )

        data = entry.model_dump()
        assert data["artifact_id"] == "skill:test"
        assert data["status"] == "refreshed"
        assert len(data["changes"]) == 2
        assert data["old_values"] is not None
        assert data["new_values"] is not None
        assert data["error"] is None
        assert data["reason"] == "Update successful"
        assert data["duration_ms"] == 100.0

    def test_refresh_entry_response_error_fields(self):
        """RefreshEntryResponse correctly handles error case."""
        entry = RefreshEntryResponse(
            artifact_id="skill:failed",
            status="error",
            changes=[],
            old_values=None,
            new_values=None,
            error="Connection timeout",
            reason="Network error",
            duration_ms=5000.0,
        )

        data = entry.model_dump()
        assert data["status"] == "error"
        assert data["error"] == "Connection timeout"
        assert data["reason"] == "Network error"
        assert len(data["changes"]) == 0
