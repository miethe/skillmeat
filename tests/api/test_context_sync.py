"""Integration tests for Context Sync API endpoints.

Tests /api/v1/context-sync endpoints:
- POST /context-sync/pull  - Pull changes from project to collection
- POST /context-sync/push  - Push collection changes to project
- GET  /context-sync/status - Get sync status for a project
- POST /context-sync/resolve - Resolve a sync conflict
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


# =============================================================================
# Helpers / shared data
# =============================================================================

_ENTITY_ID = "spec_file:api-patterns"
_ENTITY_NAME = "api-patterns"
_ENTITY_TYPE = "spec_file"


def _make_sync_result(action: str = "pulled", entity_id: str = _ENTITY_ID):
    """Return a minimal SyncResult-like object."""
    result = MagicMock()
    result.entity_id = entity_id
    result.entity_name = entity_id.split(":")[-1]
    result.action = action
    result.message = f"Successfully {action} changes for {entity_id}"
    return result


def _make_conflict(
    entity_id: str = _ENTITY_ID,
    entity_name: str = _ENTITY_NAME,
    entity_type: str = _ENTITY_TYPE,
):
    """Return a minimal SyncConflict-like object."""
    conflict = MagicMock()
    conflict.entity_id = entity_id
    conflict.entity_name = entity_name
    conflict.entity_type = entity_type
    conflict.collection_hash = "abc123"
    conflict.deployed_hash = "def456"
    conflict.collection_content = "# Collection content"
    conflict.deployed_content = "# Project content (modified)"
    conflict.collection_path = "/collection/path/api-patterns.md"
    conflict.deployed_path = "/project/.claude/specs/api-patterns.md"
    conflict.baseline_hash = "base000"
    return conflict


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_settings():
    """Test settings with API key auth disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def mock_sync_service():
    """A MagicMock that stands in for ContextSyncService."""
    return MagicMock()


@pytest.fixture
def app(test_settings, mock_sync_service):
    """FastAPI app with ContextSyncService dependency overridden."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.dependencies import get_context_sync_service

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[get_context_sync_service] = (
        lambda: mock_sync_service
    )
    return application


@pytest.fixture
def client(app):
    """TestClient wrapping the app lifespan."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def existing_project(tmp_path):
    """Return the string path to a temporary directory that actually exists."""
    return str(tmp_path)


# =============================================================================
# POST /api/v1/context-sync/pull
# =============================================================================


class TestPullChanges:
    """Tests for POST /api/v1/context-sync/pull."""

    def test_pull_success_returns_200(self, client, mock_sync_service, existing_project):
        """Pull with valid project path and available sync results returns 200."""
        mock_sync_service.pull_changes.return_value = [
            _make_sync_result("pulled")
        ]

        response = client.post(
            "/api/v1/context-sync/pull",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["action"] == "pulled"
        assert data[0]["entity_id"] == _ENTITY_ID

    def test_pull_with_entity_ids_filters_correctly(
        self, client, mock_sync_service, existing_project
    ):
        """Pull with explicit entity_ids forwards them to the service."""
        mock_sync_service.pull_changes.return_value = [
            _make_sync_result("pulled", _ENTITY_ID)
        ]

        response = client.post(
            "/api/v1/context-sync/pull",
            json={
                "project_path": existing_project,
                "entity_ids": [_ENTITY_ID],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        mock_sync_service.pull_changes.assert_called_once_with(
            project_path=existing_project,
            entity_ids=[_ENTITY_ID],
        )

    def test_pull_empty_result_returns_empty_list(
        self, client, mock_sync_service, existing_project
    ):
        """Pull when no entities are modified returns an empty list."""
        mock_sync_service.pull_changes.return_value = []

        response = client.post(
            "/api/v1/context-sync/pull",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_pull_nonexistent_project_returns_404(self, client, mock_sync_service):
        """Pull with a project path that does not exist returns 404."""
        response = client.post(
            "/api/v1/context-sync/pull",
            json={"project_path": "/this/path/does/not/exist"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Project path not found" in response.json()["detail"]

    def test_pull_service_raises_file_not_found_returns_404(
        self, client, mock_sync_service, existing_project
    ):
        """Pull where the service raises FileNotFoundError returns 404."""
        mock_sync_service.pull_changes.side_effect = FileNotFoundError(
            "spec file missing"
        )

        response = client.post(
            "/api/v1/context-sync/pull",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_pull_service_raises_unexpected_error_returns_500(
        self, client, mock_sync_service, existing_project
    ):
        """Pull where the service raises an unexpected error returns 500."""
        mock_sync_service.pull_changes.side_effect = RuntimeError("db gone")

        response = client.post(
            "/api/v1/context-sync/pull",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Sync failed" in response.json()["detail"]

    def test_pull_missing_project_path_returns_422(self, client, mock_sync_service):
        """Pull with missing required field returns 422 Unprocessable Entity."""
        response = client.post(
            "/api/v1/context-sync/pull",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# POST /api/v1/context-sync/push
# =============================================================================


class TestPushChanges:
    """Tests for POST /api/v1/context-sync/push."""

    def test_push_success_returns_200(self, client, mock_sync_service, existing_project):
        """Push with valid project path returns 200 and pushed results."""
        mock_sync_service.push_changes.return_value = [
            _make_sync_result("pushed")
        ]

        response = client.post(
            "/api/v1/context-sync/push",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["action"] == "pushed"

    def test_push_with_overwrite_flag(self, client, mock_sync_service, existing_project):
        """Push with overwrite=True forwards the flag to the service."""
        mock_sync_service.push_changes.return_value = [
            _make_sync_result("pushed")
        ]

        response = client.post(
            "/api/v1/context-sync/push",
            json={"project_path": existing_project, "overwrite": True},
        )

        assert response.status_code == status.HTTP_200_OK
        mock_sync_service.push_changes.assert_called_once_with(
            project_path=existing_project,
            entity_ids=None,
            overwrite=True,
        )

    def test_push_with_entity_ids(self, client, mock_sync_service, existing_project):
        """Push with entity_ids filters operation to those entities."""
        mock_sync_service.push_changes.return_value = [
            _make_sync_result("pushed", _ENTITY_ID)
        ]

        response = client.post(
            "/api/v1/context-sync/push",
            json={
                "project_path": existing_project,
                "entity_ids": [_ENTITY_ID],
                "overwrite": False,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        mock_sync_service.push_changes.assert_called_once_with(
            project_path=existing_project,
            entity_ids=[_ENTITY_ID],
            overwrite=False,
        )

    def test_push_conflict_returns_conflict_action(
        self, client, mock_sync_service, existing_project
    ):
        """Push with conflict result surfaces action='conflict' to the caller."""
        conflict_result = _make_sync_result("conflict")
        conflict_result.message = (
            "Both collection and project modified, use overwrite=True to force"
        )
        mock_sync_service.push_changes.return_value = [conflict_result]

        response = client.post(
            "/api/v1/context-sync/push",
            json={"project_path": existing_project, "overwrite": False},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data[0]["action"] == "conflict"

    def test_push_nonexistent_project_returns_404(self, client, mock_sync_service):
        """Push with a project path that does not exist returns 404."""
        response = client.post(
            "/api/v1/context-sync/push",
            json={"project_path": "/this/path/does/not/exist"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Project path not found" in response.json()["detail"]

    def test_push_service_raises_file_not_found_returns_404(
        self, client, mock_sync_service, existing_project
    ):
        """Push where the service raises FileNotFoundError returns 404."""
        mock_sync_service.push_changes.side_effect = FileNotFoundError("missing")

        response = client.post(
            "/api/v1/context-sync/push",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_push_service_raises_unexpected_error_returns_500(
        self, client, mock_sync_service, existing_project
    ):
        """Push where the service raises an unexpected error returns 500."""
        mock_sync_service.push_changes.side_effect = OSError("disk full")

        response = client.post(
            "/api/v1/context-sync/push",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Sync failed" in response.json()["detail"]

    def test_push_missing_project_path_returns_422(self, client, mock_sync_service):
        """Push with missing required field returns 422."""
        response = client.post(
            "/api/v1/context-sync/push",
            json={"overwrite": False},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# GET /api/v1/context-sync/status
# =============================================================================


class TestGetSyncStatus:
    """Tests for GET /api/v1/context-sync/status."""

    def test_status_success_returns_200(
        self, client, mock_sync_service, existing_project
    ):
        """Status for a valid project path returns 200 with correct shape."""
        mock_sync_service.detect_modified_entities.return_value = [
            {"entity_id": _ENTITY_ID, "modified_in": "project"},
        ]
        mock_sync_service.detect_conflicts.return_value = []

        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "modified_in_project" in data
        assert "modified_in_collection" in data
        assert "conflicts" in data
        assert _ENTITY_ID in data["modified_in_project"]
        assert data["modified_in_collection"] == []
        assert data["conflicts"] == []

    def test_status_modified_in_collection(
        self, client, mock_sync_service, existing_project
    ):
        """Status surfaces entities modified in collection separately."""
        mock_sync_service.detect_modified_entities.return_value = [
            {"entity_id": "rule_file:debugging", "modified_in": "collection"},
        ]
        mock_sync_service.detect_conflicts.return_value = []

        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "rule_file:debugging" in data["modified_in_collection"]
        assert data["modified_in_project"] == []

    def test_status_modified_in_both_appears_in_both_lists(
        self, client, mock_sync_service, existing_project
    ):
        """Entities modified in both sides appear in both lists."""
        mock_sync_service.detect_modified_entities.return_value = [
            {"entity_id": _ENTITY_ID, "modified_in": "both"},
        ]
        mock_sync_service.detect_conflicts.return_value = []

        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert _ENTITY_ID in data["modified_in_project"]
        assert _ENTITY_ID in data["modified_in_collection"]

    def test_status_with_conflicts(self, client, mock_sync_service, existing_project):
        """Status includes conflict details when conflicts exist."""
        mock_sync_service.detect_modified_entities.return_value = []
        mock_sync_service.detect_conflicts.return_value = [_make_conflict()]

        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conflicts"]) == 1
        conflict = data["conflicts"][0]
        assert conflict["entity_id"] == _ENTITY_ID
        assert conflict["entity_name"] == _ENTITY_NAME
        assert conflict["entity_type"] == _ENTITY_TYPE
        assert conflict["collection_hash"] == "abc123"
        assert conflict["deployed_hash"] == "def456"
        assert conflict["change_origin"] == "conflict"

    def test_status_clean_project_returns_empty_lists(
        self, client, mock_sync_service, existing_project
    ):
        """Status for a project with no changes returns empty lists."""
        mock_sync_service.detect_modified_entities.return_value = []
        mock_sync_service.detect_conflicts.return_value = []

        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["modified_in_project"] == []
        assert data["modified_in_collection"] == []
        assert data["conflicts"] == []

    def test_status_nonexistent_project_returns_404(
        self, client, mock_sync_service
    ):
        """Status with a path that does not exist returns 404."""
        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": "/no/such/directory"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Project path not found" in response.json()["detail"]

    def test_status_missing_query_param_returns_422(self, client, mock_sync_service):
        """Status without required project_path query parameter returns 422."""
        response = client.get("/api/v1/context-sync/status")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_status_service_raises_error_returns_500(
        self, client, mock_sync_service, existing_project
    ):
        """Status where the service raises an unexpected error returns 500."""
        mock_sync_service.detect_modified_entities.side_effect = RuntimeError(
            "cache unavailable"
        )

        response = client.get(
            "/api/v1/context-sync/status",
            params={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Status check failed" in response.json()["detail"]


# =============================================================================
# POST /api/v1/context-sync/resolve
# =============================================================================


class TestResolveConflict:
    """Tests for POST /api/v1/context-sync/resolve."""

    def test_resolve_keep_local_success_returns_200(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve with keep_local strategy returns 200 and resolved action."""
        mock_sync_service.detect_conflicts.return_value = [_make_conflict()]
        mock_sync_service.resolve_conflict.return_value = _make_sync_result("resolved")

        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "keep_local",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["action"] == "resolved"
        assert data["entity_id"] == _ENTITY_ID

    def test_resolve_keep_remote_success_returns_200(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve with keep_remote strategy returns 200."""
        mock_sync_service.detect_conflicts.return_value = [_make_conflict()]
        mock_sync_service.resolve_conflict.return_value = _make_sync_result("resolved")

        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "keep_remote",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["action"] == "resolved"

    def test_resolve_merge_with_content_returns_200(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve with merge strategy and merged_content returns 200."""
        mock_sync_service.detect_conflicts.return_value = [_make_conflict()]
        mock_sync_service.resolve_conflict.return_value = _make_sync_result("resolved")

        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "merge",
                "merged_content": "# Merged content\n\nBest of both worlds.",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["action"] == "resolved"

    def test_resolve_merge_without_content_returns_400(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve with merge strategy but no merged_content returns 400."""
        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "merge",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "merged_content required" in response.json()["detail"]

    def test_resolve_nonexistent_project_returns_404(
        self, client, mock_sync_service
    ):
        """Resolve with a path that does not exist returns 404."""
        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": "/no/such/project",
                "entity_id": _ENTITY_ID,
                "resolution": "keep_local",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Project path not found" in response.json()["detail"]

    def test_resolve_no_conflict_for_entity_returns_404(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve when no conflict exists for the given entity_id returns 404."""
        mock_sync_service.detect_conflicts.return_value = []

        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": "spec_file:nonexistent",
                "resolution": "keep_local",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No conflict found" in response.json()["detail"]

    def test_resolve_service_raises_value_error_returns_400(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve where the service raises ValueError returns 400."""
        mock_sync_service.detect_conflicts.return_value = [_make_conflict()]
        mock_sync_service.resolve_conflict.side_effect = ValueError(
            "invalid resolution state"
        )

        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "keep_local",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resolve_service_raises_unexpected_error_returns_500(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve where the service raises an unexpected error returns 500."""
        mock_sync_service.detect_conflicts.return_value = [_make_conflict()]
        mock_sync_service.resolve_conflict.side_effect = RuntimeError("I/O error")

        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "keep_remote",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Resolution failed" in response.json()["detail"]

    def test_resolve_invalid_resolution_strategy_returns_422(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve with an invalid resolution literal value returns 422."""
        response = client.post(
            "/api/v1/context-sync/resolve",
            json={
                "project_path": existing_project,
                "entity_id": _ENTITY_ID,
                "resolution": "do_nothing",  # not in Literal enum
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_resolve_missing_required_fields_returns_422(
        self, client, mock_sync_service, existing_project
    ):
        """Resolve with missing required fields returns 422."""
        response = client.post(
            "/api/v1/context-sync/resolve",
            json={"project_path": existing_project},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
