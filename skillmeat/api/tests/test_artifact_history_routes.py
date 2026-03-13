"""Tests for artifact history/provenance API route.

Updated to use dependency_overrides instead of patching get_session,
reflecting the refactor to DbArtifactHistoryRepoDep (IDbArtifactHistoryRepository).
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.artifacts import ArtifactHistoryEventResponse
from skillmeat.api.server import create_app
from skillmeat.core.interfaces.dtos import CacheArtifactSummaryDTO


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _register_local_auth_provider():
    """Register LocalAuthProvider so require_auth() resolves without 503."""
    from skillmeat.api.auth.local_provider import LocalAuthProvider
    from skillmeat.api.dependencies import set_auth_provider
    import skillmeat.api.dependencies as _deps_module

    set_auth_provider(LocalAuthProvider())
    yield
    _deps_module._auth_provider = None


@pytest.fixture
def api_settings():
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def app(api_settings):
    from skillmeat.api.dependencies import app_state

    application = create_app(api_settings)
    app_state.initialize(api_settings)
    yield application
    app_state.shutdown()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(name: str = "test-skill", art_type: str = "skill") -> CacheArtifactSummaryDTO:
    return CacheArtifactSummaryDTO(
        id=f"{art_type}:{name}",
        uuid="aaaabbbbccccdddd1234567890123456",
        name=name,
        type=art_type,
        project_path="/workspace/project-a",
    )


def _make_history_repo(summary=None):
    """Build a mock IDbArtifactHistoryRepository."""
    repo = MagicMock()
    if summary is None:
        repo.list_cache_artifacts_by_name_type.return_value = []
        repo.get_cache_artifact_by_uuid.return_value = None
    else:
        repo.list_cache_artifacts_by_name_type.return_value = [summary]
        repo.get_cache_artifact_by_uuid.return_value = summary
    repo.list_versions_for_artifacts.return_value = []
    return repo


def _make_event(now: datetime, event_category: str = "version") -> ArtifactHistoryEventResponse:
    return ArtifactHistoryEventResponse(
        id=f"{event_category}:1",
        timestamp=now,
        event_category=event_category,
        event_type="local_modification",
        source="artifact_versions",
        artifact_name="test-skill",
        artifact_type="skill",
        collection_name="default",
        project_path="/workspace/project-a",
        content_sha="abc123",
        parent_sha=None,
        version_lineage=["root", "abc123"],
        metadata={},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_artifact_history_success(app, client):
    """GET /{artifact_id}/history returns 200 with merged timeline."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    now = datetime.now(timezone.utc)
    summary = _make_summary()
    repo = _make_history_repo(summary)

    version_event = _make_event(now, "version")
    analytics_event = ArtifactHistoryEventResponse(
        id="analytics:2",
        timestamp=now,
        event_category="analytics",
        event_type="sync",
        source="analytics_events",
        artifact_name="test-skill",
        artifact_type="skill",
        collection_name="default",
        project_path="/workspace/project-a",
        content_sha="def456",
        parent_sha="abc123",
        version_lineage=None,
        metadata={"result": "success"},
    )

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    cfg_mgr = MagicMock()
    cfg_mgr.is_analytics_enabled.return_value = False

    with (
        patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[version_event],
        ),
        patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[analytics_event],
        ),
        patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ),
        patch("skillmeat.api.dependencies.app_state") as mock_state,
    ):
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:test-skill/history?limit=50")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_name"] == "test-skill"
    assert len(payload["timeline"]) == 2
    assert payload["statistics"]["total_events"] == 2
    assert payload["statistics"]["version_events"] == 1
    assert payload["statistics"]["analytics_events"] == 1


def test_get_artifact_history_not_found(app, client):
    """GET /{artifact_id}/history returns 404 when artifact is absent."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    repo = _make_history_repo(summary=None)
    cfg_mgr = MagicMock()

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with patch("skillmeat.api.dependencies.app_state") as mock_state:
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:missing/history")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Auth enforcement tests
# ---------------------------------------------------------------------------


def test_history_endpoint_requires_no_auth_when_api_key_disabled(app, client):
    """With api_key_enabled=False the endpoint is accessible without credentials."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    repo = _make_history_repo(summary=None)
    cfg_mgr = MagicMock()

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with patch("skillmeat.api.dependencies.app_state") as mock_state:
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:anything/history")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    # 404 (not 401/403) — accessible but artifact absent
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Request validation (422)
# ---------------------------------------------------------------------------


def test_history_limit_too_large_returns_422(app, client):
    """limit > 2000 should result in 422 Unprocessable Entity."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    summary = _make_summary()
    repo = _make_history_repo(summary)
    cfg_mgr = MagicMock()

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with patch("skillmeat.api.dependencies.app_state") as mock_state:
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:test-skill/history?limit=9999")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 422


def test_history_limit_zero_returns_422(app, client):
    """limit=0 is below the minimum (1) — 422 Unprocessable Entity."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    summary = _make_summary()
    repo = _make_history_repo(summary)
    cfg_mgr = MagicMock()

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with patch("skillmeat.api.dependencies.app_state") as mock_state:
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:test-skill/history?limit=0")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Response format
# ---------------------------------------------------------------------------


def test_history_response_has_required_fields(app, client):
    """Successful response includes artifact_name, artifact_type, timeline, statistics."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    summary = _make_summary()
    repo = _make_history_repo(summary)
    cfg_mgr = MagicMock()
    cfg_mgr.is_analytics_enabled.return_value = False

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with (
        patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[],
        ),
        patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[],
        ),
        patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ),
        patch("skillmeat.api.dependencies.app_state") as mock_state,
    ):
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:test-skill/history")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 200
    data = response.json()
    assert "artifact_name" in data
    assert "artifact_type" in data
    assert "timeline" in data
    assert "statistics" in data
    assert "last_updated" in data


def test_history_empty_timeline_statistics_are_zeros(app, client):
    """Statistics should all be 0 when timeline is empty."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    summary = _make_summary()
    repo = _make_history_repo(summary)
    cfg_mgr = MagicMock()
    cfg_mgr.is_analytics_enabled.return_value = False

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with (
        patch(
            "skillmeat.api.routers.artifact_history._build_version_events",
            return_value=[],
        ),
        patch(
            "skillmeat.api.routers.artifact_history._build_analytics_events",
            return_value=[],
        ),
        patch(
            "skillmeat.api.routers.artifact_history._build_deployment_events",
            return_value=[],
        ),
        patch("skillmeat.api.dependencies.app_state") as mock_state,
    ):
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:test-skill/history")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    stats = response.json()["statistics"]
    assert stats["total_events"] == 0
    assert stats["version_events"] == 0
    assert stats["analytics_events"] == 0
    assert stats["deployment_events"] == 0


# ---------------------------------------------------------------------------
# Error codes — 404 (artifact not found via UUID path)
# ---------------------------------------------------------------------------


def test_history_uuid_artifact_not_found_returns_404(app, client):
    """UUID-format artifact_id with no matching DB row → 404."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    repo = _make_history_repo(summary=None)
    cfg_mgr = MagicMock()

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with patch("skillmeat.api.dependencies.app_state") as mock_state:
        mock_state.config_manager = cfg_mgr
        response = client.get(
            "/api/v1/artifacts/deadbeefdeadbeef1234567890123456/history"
        )

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Error handling — 500 on unexpected repository failure
# ---------------------------------------------------------------------------


def test_history_repository_exception_returns_500(app, client):
    """Unexpected exception from the history repository → 500 Internal Server Error."""
    from skillmeat.api.dependencies import get_db_artifact_history_repository

    repo = MagicMock()
    repo.list_cache_artifacts_by_name_type.side_effect = RuntimeError(
        "database connection lost"
    )
    cfg_mgr = MagicMock()

    app.dependency_overrides[get_db_artifact_history_repository] = lambda: repo

    with patch("skillmeat.api.dependencies.app_state") as mock_state:
        mock_state.config_manager = cfg_mgr
        response = client.get("/api/v1/artifacts/skill:test-skill/history")

    app.dependency_overrides.pop(get_db_artifact_history_repository, None)

    assert response.status_code == 500
    assert "Failed to retrieve artifact history" in response.json()["detail"]
