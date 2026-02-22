"""Tests for analytics API routes."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.analytics import (
    ArtifactHistorySummary,
    EnterpriseAdoptionMetrics,
    EnterpriseAnalyticsSummaryResponse,
    EnterpriseDeliveryMetrics,
    EnterpriseMetricWindow,
    EnterpriseReliabilityMetrics,
    ProjectActivityItem,
    TopArtifactItem,
)
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


def _sample_enterprise_summary() -> EnterpriseAnalyticsSummaryResponse:
    now = datetime.now(timezone.utc)
    return EnterpriseAnalyticsSummaryResponse(
        generated_at=now,
        total_events=123,
        total_artifacts=14,
        total_projects=3,
        total_collections=2,
        event_type_counts={"deploy": 40, "sync": 50, "update": 20, "search": 13},
        windows=[
            EnterpriseMetricWindow(
                window_days=7,
                total_events=45,
                deploy_events=16,
                sync_events=18,
                update_events=8,
                remove_events=1,
                search_events=2,
                success_count=36,
                failure_count=4,
                success_rate=0.9,
                unique_artifacts=11,
                unique_projects=3,
                unique_collections=2,
                deploy_frequency_per_day=2.3,
            )
        ],
        delivery=EnterpriseDeliveryMetrics(
            deployment_frequency_7d=2.3,
            deployment_frequency_30d=1.7,
            median_deploy_interval_minutes_30d=85.0,
            unique_artifacts_deployed_30d=10,
        ),
        reliability=EnterpriseReliabilityMetrics(
            change_failure_rate_30d=0.1,
            sync_success_rate_7d=0.92,
            rollback_rate_30d=0.05,
            mean_time_to_recovery_hours_30d=2.1,
        ),
        adoption=EnterpriseAdoptionMetrics(
            active_projects_7d=3,
            active_projects_30d=4,
            active_collections_30d=2,
            search_to_deploy_conversion_30d=0.6,
        ),
        top_projects=[
            ProjectActivityItem(
                project_path="/workspace/project-a",
                event_count=20,
                deploy_count=8,
                sync_count=7,
                last_activity=now,
            )
        ],
        top_artifacts=[
            TopArtifactItem(
                artifact_name="test-skill",
                artifact_type="skill",
                deployment_count=12,
                usage_count=24,
                last_used=now,
                collections=["default"],
            )
        ],
        history_summary=ArtifactHistorySummary(
            version_events=30,
            merge_events=4,
            deployment_events=12,
        ),
    )


def test_get_enterprise_summary_success(client):
    mock_db = Mock()
    mock_db.close = Mock()
    summary = _sample_enterprise_summary()

    with (
        patch("skillmeat.api.routers.analytics.get_analytics_db", return_value=mock_db),
        patch("skillmeat.api.routers.analytics._build_enterprise_summary", return_value=summary),
    ):
        response = client.get("/api/v1/analytics/enterprise-summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_events"] == 123
    assert payload["delivery"]["deployment_frequency_7d"] == 2.3
    assert payload["history_summary"]["merge_events"] == 4
    mock_db.close.assert_called_once()


def test_list_analytics_events_normalizes_outcome(client):
    mock_db = Mock()
    mock_db.get_events.return_value = [
        {
            "id": 1,
            "event_type": "sync",
            "artifact_name": "test-skill",
            "artifact_type": "skill",
            "collection_name": "default",
            "project_path": "/workspace/project-a",
            "timestamp": "2026-02-20T12:00:00Z",
            "metadata": '{"result":"success","files_changed":3}',
        }
    ]
    mock_db.close = Mock()

    with patch("skillmeat.api.routers.analytics.get_analytics_db", return_value=mock_db):
        response = client.get("/api/v1/analytics/events?limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["event_type"] == "sync"
    assert payload["items"][0]["outcome"] == "success"
    assert payload["page_info"]["has_next_page"] is True
    mock_db.close.assert_called_once()


def test_export_analytics_prometheus(client):
    mock_db = Mock()
    mock_db.close = Mock()
    summary = _sample_enterprise_summary()

    with (
        patch("skillmeat.api.routers.analytics.get_analytics_db", return_value=mock_db),
        patch("skillmeat.api.routers.analytics._build_enterprise_summary", return_value=summary),
    ):
        response = client.get("/api/v1/analytics/export?format=prometheus")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "skillmeat_analytics_total_events" in response.text
    assert "skillmeat_analytics_deployment_frequency_7d" in response.text
    mock_db.close.assert_called_once()


def test_get_analytics_summary_success(client):
    mock_db = Mock()
    mock_db.close = Mock()

    with (
        patch("skillmeat.api.routers.analytics.get_analytics_db", return_value=mock_db),
        patch(
            "skillmeat.api.routers.analytics._build_legacy_summary",
            return_value={
                "total_collections": 2,
                "total_artifacts": 10,
                "total_deployments": 5,
                "total_events": 30,
                "artifacts_by_type": {"skill": 8, "command": 2},
                "recent_activity_count": 6,
                "most_deployed_artifact": "test-skill",
                "last_activity": datetime.now(timezone.utc),
            },
        ),
    ):
        response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_collections"] == 2
    assert payload["most_deployed_artifact"] == "test-skill"
    mock_db.close.assert_called_once()
