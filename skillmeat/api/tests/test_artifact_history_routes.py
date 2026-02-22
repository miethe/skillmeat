"""Tests for artifact history/provenance API route."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.artifacts import ArtifactHistoryEventResponse
from skillmeat.api.server import create_app


@pytest.fixture
def api_settings():
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def client(api_settings):
    from skillmeat.api.dependencies import app_state

    app = create_app(api_settings)
    app_state.initialize(api_settings)
    client = TestClient(app)

    yield client

    app_state.shutdown()


class _MockArtifactQuery:
    def __init__(self, artifacts):
        self._artifacts = artifacts

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._artifacts[0] if self._artifacts else None

    def all(self):
        return self._artifacts


def test_get_artifact_history_success(client):
    now = datetime.now(timezone.utc)
    artifacts = [
        SimpleNamespace(
            id=1,
            uuid="abc-123",
            name="test-skill",
            type="skill",
            project=SimpleNamespace(path="/workspace/project-a"),
        )
    ]

    session = Mock()
    session.query.return_value = _MockArtifactQuery(artifacts)
    session.close = Mock()

    version_event = ArtifactHistoryEventResponse(
        id="version:1",
        timestamp=now,
        event_category="version",
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

    with (
        patch("skillmeat.api.routers.artifact_history.get_session", return_value=session),
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
    ):
        response = client.get("/api/v1/artifacts/skill:test-skill/history?limit=50")

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_name"] == "test-skill"
    assert len(payload["timeline"]) == 2
    assert payload["statistics"]["total_events"] == 2
    assert payload["statistics"]["version_events"] == 1
    assert payload["statistics"]["analytics_events"] == 1
    session.close.assert_called_once()


def test_get_artifact_history_not_found(client):
    session = Mock()
    session.query.return_value = _MockArtifactQuery([])
    session.close = Mock()

    with patch("skillmeat.api.routers.artifact_history.get_session", return_value=session):
        response = client.get("/api/v1/artifacts/skill:missing/history")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    session.close.assert_called_once()
