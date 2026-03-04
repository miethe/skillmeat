"""Tests for Deployments API endpoints.

This module tests the /api/v1/deploy endpoints, including:
- POST /api/v1/deploy           — deploy an artifact to a project
- POST /api/v1/deploy/undeploy  — remove a deployed artifact
- GET  /api/v1/deploy           — list all deployments in a project
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.deployment import Deployment
from skillmeat.api.routers.deployments import get_deployment_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings():
    """Create test API settings with auth disabled."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def mock_deployment():
    """Create a single mock Deployment dataclass instance."""
    return Deployment(
        artifact_name="pdf-skill",
        artifact_type="skill",
        from_collection="default",
        deployed_at=datetime(2025, 1, 15, 10, 0, 0),
        artifact_path=Path("skills/pdf-skill"),
        content_hash="abc123def456",
        local_modifications=False,
        collection_sha="abc123def456",
        deployment_profile_id="claude_code",
        platform=None,
        profile_root_dir=".claude",
    )


@pytest.fixture
def mock_deployment_manager(mock_deployment):
    """Return a mock DeploymentManager with sensible defaults."""
    mgr = MagicMock()
    mgr.list_deployments.return_value = [mock_deployment]
    mgr.deploy_artifacts.return_value = [mock_deployment]
    mgr.undeploy.return_value = None
    mgr.compute_deployment_statuses_batch.return_value = {
        "pdf-skill::skill::claude_code": "synced"
    }
    return mgr


def _make_app(test_settings, deployment_manager_override):
    """Build a FastAPI app with the deployment manager dependency overridden."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings
    # Override the dependency function used by the router
    app.dependency_overrides[get_deployment_manager] = lambda: deployment_manager_override
    return app


def _mock_session():
    """Return a no-op mock SQLAlchemy session."""
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


_GET_SESSION_PATCH = "skillmeat.api.routers.deployments.get_session"
_ADD_CACHE_PATCH = "skillmeat.api.routers.deployments.add_deployment_to_cache"
_REMOVE_CACHE_PATCH = "skillmeat.api.routers.deployments.remove_deployment_from_cache"
_STATS_CACHE_PATCH = "skillmeat.api.routers.deployments.get_deployment_stats_cache"


# ---------------------------------------------------------------------------
# POST /api/v1/deploy  — deploy_artifact
# ---------------------------------------------------------------------------


class TestDeployArtifact:
    """Tests for POST /api/v1/deploy."""

    def _deploy_payload(self, **overrides):
        payload = {
            "artifact_id": "skill:pdf-skill",
            "artifact_name": "pdf-skill",
            "artifact_type": "skill",
            "project_path": "/tmp/test-project",
            "collection_name": "default",
            "overwrite": False,
        }
        payload.update(overrides)
        return payload

    def test_deploy_artifact_success(self, test_settings, mock_deployment_manager):
        """Deploying a valid artifact returns 200 with deployment details."""
        mock_deployment_manager.list_deployments.return_value = []  # no existing

        stats_cache = MagicMock()
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            with (
                patch(_GET_SESSION_PATCH, return_value=_mock_session()),
                patch(_ADD_CACHE_PATCH),
                patch(_STATS_CACHE_PATCH, return_value=stats_cache),
            ):
                response = client.post("/api/v1/deploy", json=self._deploy_payload())

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["artifact_name"] == "pdf-skill"
        assert data["artifact_type"] == "skill"
        assert "deployed_path" in data
        assert "project_path" in data

    def test_deploy_artifact_invalid_type_returns_400(
        self, test_settings, mock_deployment_manager
    ):
        """An unrecognised artifact_type returns 400."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy",
                json=self._deploy_payload(artifact_type="foobar"),
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid artifact type" in response.json()["detail"]

    def test_deploy_artifact_conflict_without_overwrite_returns_409(
        self, test_settings, mock_deployment_manager
    ):
        """Deploying an already-deployed artifact without overwrite=True returns 409."""
        mock_deployment_manager.list_deployments.return_value = [
            MagicMock(
                artifact_name="pdf-skill",
                artifact_type="skill",
                deployment_profile_id="claude_code",
            )
        ]

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy",
                json=self._deploy_payload(overwrite=False),
            )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already deployed" in response.json()["detail"]

    def test_deploy_artifact_overwrite_replaces_existing(
        self, test_settings, mock_deployment_manager
    ):
        """Deploying with overwrite=True removes the old deployment and re-deploys."""
        mock_deployment_manager.list_deployments.return_value = [
            MagicMock(
                artifact_name="pdf-skill",
                artifact_type="skill",
                deployment_profile_id="claude_code",
            )
        ]

        stats_cache = MagicMock()
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            with (
                patch(_GET_SESSION_PATCH, return_value=_mock_session()),
                patch(_ADD_CACHE_PATCH),
                patch(_STATS_CACHE_PATCH, return_value=stats_cache),
            ):
                response = client.post(
                    "/api/v1/deploy",
                    json=self._deploy_payload(overwrite=True),
                )

        assert response.status_code == status.HTTP_200_OK
        # undeploy should have been called for the pre-existing entry
        mock_deployment_manager.undeploy.assert_called_once()

    def test_deploy_artifact_not_found_raises_value_error_returns_404(
        self, test_settings, mock_deployment_manager
    ):
        """When the manager raises ValueError the endpoint returns 404."""
        mock_deployment_manager.list_deployments.return_value = []
        mock_deployment_manager.deploy_artifacts.side_effect = ValueError(
            "Artifact 'missing-skill' not found"
        )

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy",
                json=self._deploy_payload(
                    artifact_name="missing-skill",
                    artifact_id="skill:missing-skill",
                ),
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deploy_artifact_empty_result_returns_404(
        self, test_settings, mock_deployment_manager
    ):
        """deploy_artifacts returning an empty list yields 404."""
        mock_deployment_manager.list_deployments.return_value = []
        mock_deployment_manager.deploy_artifacts.return_value = []

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post("/api/v1/deploy", json=self._deploy_payload())

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deploy_artifact_all_profiles_with_profile_id_returns_400(
        self, test_settings, mock_deployment_manager
    ):
        """Setting both all_profiles=True and deployment_profile_id is invalid."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy",
                json=self._deploy_payload(
                    all_profiles=True,
                    deployment_profile_id="claude_code",
                ),
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deploy_artifact_dest_path_traversal_returns_400(
        self, test_settings, mock_deployment_manager
    ):
        """A dest_path containing '..' is rejected with 400."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy",
                json=self._deploy_payload(dest_path="../etc"),
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "traversal" in response.json()["detail"].lower()

    def test_deploy_artifact_dest_path_absolute_returns_400(
        self, test_settings, mock_deployment_manager
    ):
        """An absolute dest_path is rejected with 400."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy",
                json=self._deploy_payload(dest_path="/absolute/path"),
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deploy_artifact_internal_error_returns_500(
        self, test_settings, mock_deployment_manager
    ):
        """Unexpected exceptions from the manager surface as 500."""
        mock_deployment_manager.list_deployments.return_value = []
        mock_deployment_manager.deploy_artifacts.side_effect = RuntimeError("disk full")

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post("/api/v1/deploy", json=self._deploy_payload())

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_deploy_artifact_missing_required_fields_returns_422(self, test_settings, mock_deployment_manager):
        """Sending an incomplete payload triggers Pydantic validation (422)."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post("/api/v1/deploy", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_deploy_artifact_without_project_path_uses_cwd(
        self, test_settings, mock_deployment_manager
    ):
        """Omitting project_path is valid; the endpoint resolves CWD internally."""
        mock_deployment_manager.list_deployments.return_value = []
        stats_cache = MagicMock()

        app = _make_app(test_settings, mock_deployment_manager)

        payload = {
            "artifact_id": "skill:pdf-skill",
            "artifact_name": "pdf-skill",
            "artifact_type": "skill",
        }

        with TestClient(app) as client:
            with (
                patch(_GET_SESSION_PATCH, return_value=_mock_session()),
                patch(_ADD_CACHE_PATCH),
                patch(_STATS_CACHE_PATCH, return_value=stats_cache),
            ):
                response = client.post("/api/v1/deploy", json=payload)

        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# POST /api/v1/deploy/undeploy — undeploy_artifact
# ---------------------------------------------------------------------------


class TestUndeployArtifact:
    """Tests for POST /api/v1/deploy/undeploy."""

    def _undeploy_payload(self, **overrides):
        payload = {
            "artifact_name": "pdf-skill",
            "artifact_type": "skill",
            "project_path": "/tmp/test-project",
        }
        payload.update(overrides)
        return payload

    def test_undeploy_artifact_success(self, test_settings, mock_deployment_manager):
        """Undeploying a valid artifact returns 200 with confirmation."""
        stats_cache = MagicMock()
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            with (
                patch(_GET_SESSION_PATCH, return_value=_mock_session()),
                patch(_REMOVE_CACHE_PATCH),
                patch(_STATS_CACHE_PATCH, return_value=stats_cache),
            ):
                response = client.post(
                    "/api/v1/deploy/undeploy", json=self._undeploy_payload()
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["artifact_name"] == "pdf-skill"
        assert data["artifact_type"] == "skill"
        assert "project_path" in data

    def test_undeploy_artifact_invalid_type_returns_400(
        self, test_settings, mock_deployment_manager
    ):
        """An unrecognised artifact_type returns 400."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy/undeploy",
                json=self._undeploy_payload(artifact_type="garbage"),
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid artifact type" in response.json()["detail"]

    def test_undeploy_artifact_not_deployed_returns_404(
        self, test_settings, mock_deployment_manager
    ):
        """Undeploying an artifact that is not deployed returns 404."""
        mock_deployment_manager.undeploy.side_effect = ValueError(
            "Artifact not found in deployments"
        )

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy/undeploy", json=self._undeploy_payload()
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_undeploy_artifact_internal_error_returns_500(
        self, test_settings, mock_deployment_manager
    ):
        """Unexpected exceptions from the manager surface as 500."""
        mock_deployment_manager.undeploy.side_effect = RuntimeError("permission denied")

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/deploy/undeploy", json=self._undeploy_payload()
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_undeploy_artifact_missing_required_fields_returns_422(
        self, test_settings, mock_deployment_manager
    ):
        """Sending an incomplete payload triggers Pydantic validation (422)."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.post("/api/v1/deploy/undeploy", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_undeploy_artifact_without_project_path_uses_cwd(
        self, test_settings, mock_deployment_manager
    ):
        """Omitting project_path is valid; the endpoint resolves CWD internally."""
        stats_cache = MagicMock()
        app = _make_app(test_settings, mock_deployment_manager)

        payload = {
            "artifact_name": "pdf-skill",
            "artifact_type": "skill",
        }

        with TestClient(app) as client:
            with (
                patch(_GET_SESSION_PATCH, return_value=_mock_session()),
                patch(_REMOVE_CACHE_PATCH),
                patch(_STATS_CACHE_PATCH, return_value=stats_cache),
            ):
                response = client.post("/api/v1/deploy/undeploy", json=payload)

        assert response.status_code == status.HTTP_200_OK

    def test_undeploy_artifact_with_profile_id_forwarded_to_manager(
        self, test_settings, mock_deployment_manager
    ):
        """Specifying a profile_id is forwarded correctly to the manager."""
        stats_cache = MagicMock()
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            with (
                patch(_GET_SESSION_PATCH, return_value=_mock_session()),
                patch(_REMOVE_CACHE_PATCH),
                patch(_STATS_CACHE_PATCH, return_value=stats_cache),
            ):
                response = client.post(
                    "/api/v1/deploy/undeploy",
                    json=self._undeploy_payload(profile_id="codex-default"),
                )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_deployment_manager.undeploy.call_args.kwargs
        assert call_kwargs.get("profile_id") == "codex-default"


# ---------------------------------------------------------------------------
# GET /api/v1/deploy — list_deployments
# ---------------------------------------------------------------------------


class TestListDeployments:
    """Tests for GET /api/v1/deploy."""

    def test_list_deployments_success(self, test_settings, mock_deployment_manager):
        """Listing deployments returns 200 with the expected structure."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get("/api/v1/deploy")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "project_path" in data
        assert "deployments" in data
        assert "deployments_by_profile" in data
        assert "total" in data
        assert data["total"] == 1

    def test_list_deployments_returns_deployment_fields(
        self, test_settings, mock_deployment_manager
    ):
        """Each deployment entry contains the expected fields."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get("/api/v1/deploy")

        assert response.status_code == status.HTTP_200_OK
        deployments = response.json()["deployments"]
        assert len(deployments) == 1

        dep = deployments[0]
        assert dep["artifact_name"] == "pdf-skill"
        assert dep["artifact_type"] == "skill"
        assert dep["from_collection"] == "default"
        assert "deployed_at" in dep
        assert "artifact_path" in dep
        assert "project_path" in dep

    def test_list_deployments_empty(self, test_settings, mock_deployment_manager):
        """When no deployments exist the response lists an empty array."""
        mock_deployment_manager.list_deployments.return_value = []
        mock_deployment_manager.compute_deployment_statuses_batch.return_value = {}

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get("/api/v1/deploy")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deployments"] == []
        assert data["total"] == 0

    def test_list_deployments_with_project_path(
        self, test_settings, mock_deployment_manager
    ):
        """Passing project_path query param is forwarded to the manager."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/deploy", params={"project_path": "/tmp/my-project"}
            )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_deployment_manager.list_deployments.call_args.kwargs
        resolved = call_kwargs.get("project_path")
        assert "my-project" in str(resolved)

    def test_list_deployments_with_profile_id_filter(
        self, test_settings, mock_deployment_manager
    ):
        """Passing profile_id filters results at the manager level."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/deploy", params={"profile_id": "codex-default"}
            )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_deployment_manager.list_deployments.call_args.kwargs
        assert call_kwargs.get("profile_id") == "codex-default"

    def test_list_deployments_groups_by_profile(
        self, test_settings, mock_deployment_manager
    ):
        """Response includes deployments_by_profile grouping keyed by profile name."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get("/api/v1/deploy")

        data = response.json()
        assert "deployments_by_profile" in data
        # The mock deployment uses deployment_profile_id="claude_code"
        assert "claude_code" in data["deployments_by_profile"]

    def test_list_deployments_includes_sync_status(
        self, test_settings, mock_deployment_manager
    ):
        """Each deployment entry includes a sync_status from the status map."""
        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get("/api/v1/deploy")

        dep = response.json()["deployments"][0]
        assert "sync_status" in dep
        assert dep["sync_status"] == "synced"

    def test_list_deployments_internal_error_returns_500(
        self, test_settings, mock_deployment_manager
    ):
        """Unexpected exceptions from the manager surface as 500."""
        mock_deployment_manager.list_deployments.side_effect = RuntimeError(
            "database unavailable"
        )

        app = _make_app(test_settings, mock_deployment_manager)

        with TestClient(app) as client:
            response = client.get("/api/v1/deploy")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
