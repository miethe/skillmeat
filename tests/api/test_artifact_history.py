"""Tests for artifact history/provenance API endpoints.

Covers all routes in skillmeat/api/routers/artifact_history.py:
- GET /api/v1/artifacts/{artifact_id}/history
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.schemas.artifacts import ArtifactHistoryEventResponse
from skillmeat.api.server import create_app


@pytest.fixture
def test_settings():
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    from skillmeat.api.config import get_settings

    _app = create_app(test_settings)
    _app.dependency_overrides[get_settings] = lambda: test_settings
    return _app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def _make_cache_artifact(name="pdf-skill", art_type="skill"):
    """Return a minimal CacheArtifact mock."""
    art = MagicMock()
    art.id = f"{art_type}:{name}"
    art.name = name
    art.type = art_type
    art.uuid = "aaaabbbbccccdddd1234567890123456"
    art.project = None
    return art


def _make_history_event(
    event_id: str = "version:1",
    category: str = "version",
    project_path: str = None,
    collection_name: str = None,
) -> ArtifactHistoryEventResponse:
    """Return a real ArtifactHistoryEventResponse instance."""
    return ArtifactHistoryEventResponse(
        id=event_id,
        timestamp=datetime.now(timezone.utc),
        event_category=category,
        event_type="updated",
        source="artifact_versions",
        artifact_name="pdf-skill",
        artifact_type="skill",
        collection_name=collection_name,
        project_path=project_path,
        content_sha="abc123",
        parent_sha=None,
        version_lineage=None,
        metadata={},
    )


def _setup_session_mock(artifact=None):
    """Build a SQLAlchemy session mock that returns artifact from name+type query."""
    session = MagicMock()
    if artifact is None:
        # Return empty list — artifact not found
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = []
    else:
        session.query.return_value.filter.return_value.filter.return_value.all.return_value = [
            artifact
        ]
    return session


# ---------------------------------------------------------------------------
# GET /api/v1/artifacts/{artifact_id}/history  (type:name format)
# ---------------------------------------------------------------------------


class TestGetArtifactHistoryByTypeName:
    def test_get_history_success_type_name(self, client):
        """type:name artifact_id returns 200 with history timeline."""
        artifact = _make_cache_artifact()
        event = _make_history_event()
        session = _setup_session_mock(artifact)
        cfg_mgr = MagicMock()
        cfg_mgr.is_analytics_enabled.return_value = False

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[event],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ), patch(
            "skillmeat.api.dependencies.app_state"
        ) as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get("/api/v1/artifacts/skill:pdf-skill/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["artifact_name"] == "pdf-skill"
        assert data["artifact_type"] == "skill"
        assert "timeline" in data
        assert "statistics" in data
        assert len(data["timeline"]) == 1

    def test_get_history_artifact_not_found_returns_404(self, client):
        """No matching artifact rows → 404."""
        session = _setup_session_mock(artifact=None)
        cfg_mgr = MagicMock()

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get("/api/v1/artifacts/skill:no-such-skill/history")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_history_empty_timeline(self, client):
        """Artifact found but no events → empty timeline."""
        artifact = _make_cache_artifact()
        session = _setup_session_mock(artifact)
        cfg_mgr = MagicMock()
        cfg_mgr.is_analytics_enabled.return_value = False

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ), patch(
            "skillmeat.api.dependencies.app_state"
        ) as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get("/api/v1/artifacts/skill:pdf-skill/history")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["timeline"] == []

    def test_get_history_multiple_event_types(self, client):
        """Timeline merges version, analytics, and deployment events."""
        artifact = _make_cache_artifact()
        version_evt = _make_history_event("version:1", "version")
        analytics_evt = _make_history_event(
            "analytics:1",
            "analytics",
            # analytics source must be "analytics_events"
        )
        # Rebuild with correct source
        analytics_evt = ArtifactHistoryEventResponse(
            id="analytics:1",
            timestamp=datetime.now(timezone.utc),
            event_category="analytics",
            event_type="deploy",
            source="analytics_events",
            artifact_name="pdf-skill",
            artifact_type="skill",
            collection_name=None,
            project_path=None,
            content_sha=None,
            parent_sha=None,
            version_lineage=None,
            metadata={},
        )
        deploy_evt = ArtifactHistoryEventResponse(
            id="deployment:1",
            timestamp=datetime.now(timezone.utc),
            event_category="deployment",
            event_type="deploy_record",
            source="deployment_tracker",
            artifact_name="pdf-skill",
            artifact_type="skill",
            collection_name=None,
            project_path=None,
            content_sha=None,
            parent_sha=None,
            version_lineage=None,
            metadata={},
        )

        session = _setup_session_mock(artifact)
        cfg_mgr = MagicMock()
        cfg_mgr.is_analytics_enabled.return_value = True

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[version_evt],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[analytics_evt],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[deploy_evt],
        ), patch(
            "skillmeat.api.dependencies.app_state"
        ) as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get("/api/v1/artifacts/skill:pdf-skill/history")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["timeline"]) == 3

    def test_get_history_statistics_populated(self, client):
        """Response statistics reflect event counts."""
        artifact = _make_cache_artifact()
        event = _make_history_event()
        session = _setup_session_mock(artifact)
        cfg_mgr = MagicMock()
        cfg_mgr.is_analytics_enabled.return_value = False

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[event],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ), patch(
            "skillmeat.api.dependencies.app_state"
        ) as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get("/api/v1/artifacts/skill:pdf-skill/history")

        stats = response.json()["statistics"]
        assert stats["total_events"] == 1
        assert stats["version_events"] == 1


# ---------------------------------------------------------------------------
# GET /api/v1/artifacts/{artifact_id}/history  (UUID format)
# ---------------------------------------------------------------------------


class TestGetArtifactHistoryByUUID:
    def test_get_history_uuid_not_found_returns_404(self, client):
        """UUID with no matching artifact → 404."""
        # UUID path: filter(uuid == ...).first() returns None
        session = MagicMock()
        uuid_mock = MagicMock()
        uuid_mock.first.return_value = None
        session.query.return_value.filter.return_value = uuid_mock

        cfg_mgr = MagicMock()

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get(
                "/api/v1/artifacts/deadbeefdeadbeef1234567890123456/history"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# Query parameter controls
# ---------------------------------------------------------------------------


class TestGetArtifactHistoryQueryParams:
    def _call_with_params(self, client, params: str, artifact=None):
        if artifact is None:
            artifact = _make_cache_artifact()
        session = _setup_session_mock(artifact)
        cfg_mgr = MagicMock()
        cfg_mgr.is_analytics_enabled.return_value = False

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[],
        ), patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ), patch(
            "skillmeat.api.dependencies.app_state"
        ) as mock_state:
            mock_state.config_manager = cfg_mgr
            return client.get(
                f"/api/v1/artifacts/skill:pdf-skill/history?{params}"
            )

    def test_include_versions_false(self, client):
        """include_versions=false is accepted and returns 200."""
        response = self._call_with_params(client, "include_versions=false")
        assert response.status_code == status.HTTP_200_OK

    def test_include_analytics_false(self, client):
        """include_analytics=false is accepted and returns 200."""
        response = self._call_with_params(client, "include_analytics=false")
        assert response.status_code == status.HTTP_200_OK

    def test_include_deployments_false(self, client):
        """include_deployments=false is accepted and returns 200."""
        response = self._call_with_params(client, "include_deployments=false")
        assert response.status_code == status.HTTP_200_OK

    def test_limit_parameter_accepted(self, client):
        """limit=50 query param is accepted and returns 200."""
        response = self._call_with_params(client, "limit=50")
        assert response.status_code == status.HTTP_200_OK

    def test_limit_too_large_returns_422(self, client):
        """limit exceeding max (2000) → 422 Unprocessable Entity."""
        response = self._call_with_params(client, "limit=9999")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_zero_returns_422(self, client):
        """limit=0 is below minimum (1) → 422."""
        response = self._call_with_params(client, "limit=0")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestGetArtifactHistoryErrors:
    def test_get_history_session_exception_returns_500(self, client):
        """Unexpected exception during DB session → 500."""
        session = MagicMock()
        session.query.side_effect = RuntimeError("database connection lost")
        cfg_mgr = MagicMock()

        with patch(
            "skillmeat.api.routers.artifact_history.get_session",
            return_value=session,
        ), patch("skillmeat.api.dependencies.app_state") as mock_state:
            mock_state.config_manager = cfg_mgr
            response = client.get("/api/v1/artifacts/skill:pdf-skill/history")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Statistics helper (unit tests, no HTTP)
# ---------------------------------------------------------------------------


class TestComputeStatistics:
    """Unit tests for the _compute_statistics helper function."""

    def test_compute_statistics_empty(self):
        from skillmeat.api.routers.artifact_history import _compute_statistics

        stats = _compute_statistics([])
        assert stats["total_events"] == 0
        assert stats["version_events"] == 0
        assert stats["analytics_events"] == 0
        assert stats["deployment_events"] == 0
        assert stats["snapshot_events"] == 0
        assert stats["lineage_depth_max"] == 0
        assert stats["unique_projects"] == 0
        assert stats["unique_collections"] == 0

    def test_compute_statistics_counts_categories(self):
        from skillmeat.api.routers.artifact_history import _compute_statistics

        source_map = {
            "version": "artifact_versions",
            "analytics": "analytics_events",
            "deployment": "deployment_tracker",
            "snapshot": "deployment_tracker",
        }
        events = []
        for category in ["version", "analytics", "deployment", "snapshot"]:
            evt = ArtifactHistoryEventResponse(
                id=f"{category}:1",
                timestamp=datetime.now(timezone.utc),
                event_category=category,
                event_type="test",
                source=source_map[category],
                artifact_name="test",
                artifact_type="skill",
                collection_name=f"coll-{category}",
                project_path=f"/project/{category}",
                content_sha=None,
                parent_sha=None,
                version_lineage=None,
                metadata={},
            )
            events.append(evt)

        stats = _compute_statistics(events)
        assert stats["total_events"] == 4
        assert stats["version_events"] == 1
        assert stats["analytics_events"] == 1
        assert stats["deployment_events"] == 1
        assert stats["snapshot_events"] == 1
        assert stats["unique_projects"] == 4
        assert stats["unique_collections"] == 4

    def test_compute_statistics_lineage_depth(self):
        from skillmeat.api.routers.artifact_history import _compute_statistics

        evt = ArtifactHistoryEventResponse(
            id="version:1",
            timestamp=datetime.now(timezone.utc),
            event_category="version",
            event_type="test",
            source="artifact_versions",
            artifact_name="test",
            artifact_type="skill",
            collection_name=None,
            project_path=None,
            content_sha=None,
            parent_sha=None,
            version_lineage=["sha1", "sha2", "sha3"],
            metadata={},
        )

        stats = _compute_statistics([evt])
        assert stats["lineage_depth_max"] == 3

    def test_compute_statistics_no_lineage(self):
        from skillmeat.api.routers.artifact_history import _compute_statistics

        evt = ArtifactHistoryEventResponse(
            id="version:1",
            timestamp=datetime.now(timezone.utc),
            event_category="version",
            event_type="test",
            source="artifact_versions",
            artifact_name="test",
            artifact_type="skill",
            collection_name=None,
            project_path=None,
            content_sha=None,
            parent_sha=None,
            version_lineage=None,
            metadata={},
        )

        stats = _compute_statistics([evt])
        assert stats["lineage_depth_max"] == 0
