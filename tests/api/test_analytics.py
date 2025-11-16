"""Tests for Analytics API endpoints.

This module tests the /api/v1/analytics endpoints, including:
- Get analytics summary
- Get top artifacts by usage
- Get usage trends over time
"""

import pytest
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


@pytest.fixture
def test_settings():
    """Create test settings."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app):
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_config_manager():
    """Create mock ConfigManager."""
    mock_mgr = MagicMock()
    mock_mgr.is_analytics_enabled.return_value = True
    mock_mgr.get_analytics_db_path.return_value = "/tmp/test_analytics.db"

    return mock_mgr


@pytest.fixture
def mock_analytics_db():
    """Create mock AnalyticsDB."""
    mock_db = MagicMock()

    # Mock get_stats
    mock_db.get_stats.return_value = {
        "total_events": 150,
        "total_artifacts": 5,
        "event_type_counts": {
            "deploy": 50,
            "update": 30,
            "sync": 20,
        },
        "artifact_type_counts": {
            "skill": 3,
            "command": 2,
        },
        "oldest_event": "2024-10-01T00:00:00",
        "newest_event": "2024-11-16T15:30:00",
        "db_size_bytes": 102400,
    }

    # Mock get_usage_summary
    mock_db.get_usage_summary.return_value = [
        {
            "artifact_name": "pdf-skill",
            "artifact_type": "skill",
            "first_used": "2024-10-01T12:00:00",
            "last_used": "2024-11-16T15:30:00",
            "deploy_count": 25,
            "update_count": 5,
            "sync_count": 3,
            "total_events": 50,
        },
        {
            "artifact_name": "excel-skill",
            "artifact_type": "skill",
            "first_used": "2024-10-05T12:00:00",
            "last_used": "2024-11-15T10:00:00",
            "deploy_count": 15,
            "update_count": 2,
            "sync_count": 1,
            "total_events": 30,
        },
    ]

    # Mock get_top_artifacts
    mock_db.get_top_artifacts.return_value = [
        {
            "artifact_name": "pdf-skill",
            "artifact_type": "skill",
            "total_events": 50,
            "deploy_count": 25,
            "last_used": "2024-11-16T15:30:00",
        },
    ]

    # Mock get_events
    now = datetime.now()
    mock_db.get_events.return_value = [
        {
            "id": i,
            "event_type": "deploy" if i % 2 == 0 else "update",
            "artifact_name": f"skill-{i % 3}",
            "artifact_type": "skill",
            "collection_name": "default",
            "timestamp": (now - timedelta(days=i)).isoformat(),
            "metadata": "{}",
        }
        for i in range(30)
    ]

    return mock_db


class TestAnalyticsSummary:
    """Test GET /api/v1/analytics/summary endpoint."""

    def test_get_summary_success(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test getting analytics summary."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ), patch(
            "skillmeat.api.routers.analytics.CollectionManager"
        ) as mock_coll_mgr_class, patch(
            "skillmeat.api.routers.analytics.ArtifactManager"
        ) as mock_art_mgr_class:
            # Mock collection and artifact managers
            mock_coll_mgr = MagicMock()
            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr_class.return_value = mock_coll_mgr

            mock_art_mgr = MagicMock()
            mock_art_mgr.list_artifacts.return_value = [
                MagicMock(),
                MagicMock(),
                MagicMock(),
            ]
            mock_art_mgr_class.return_value = mock_art_mgr

            response = client.get("/api/v1/analytics/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "total_collections" in data
        assert "total_artifacts" in data
        assert "total_deployments" in data
        assert "total_events" in data
        assert "artifacts_by_type" in data
        assert "recent_activity_count" in data
        assert "most_deployed_artifact" in data
        assert "last_activity" in data

        # Check values
        assert data["total_events"] == 150
        assert data["total_deployments"] == 50
        assert isinstance(data["artifacts_by_type"], dict)

    def test_get_summary_analytics_disabled(self, client):
        """Test getting summary when analytics is disabled."""
        mock_mgr = MagicMock()
        mock_mgr.is_analytics_enabled.return_value = False

        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_mgr,
        ):
            response = client.get("/api/v1/analytics/summary")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


class TestTopArtifacts:
    """Test GET /api/v1/analytics/top-artifacts endpoint."""

    def test_get_top_artifacts_success(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test getting top artifacts."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ), patch(
            "skillmeat.api.routers.analytics.CollectionManager"
        ) as mock_coll_mgr_class, patch(
            "skillmeat.api.routers.analytics.ArtifactManager"
        ) as mock_art_mgr_class:
            # Mock managers
            mock_coll_mgr = MagicMock()
            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr_class.return_value = mock_coll_mgr

            mock_art_mgr = MagicMock()
            mock_art_mgr.show.return_value = MagicMock()
            mock_art_mgr_class.return_value = mock_art_mgr

            response = client.get("/api/v1/analytics/top-artifacts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "items" in data
        assert "page_info" in data

        # Check items
        items = data["items"]
        assert len(items) > 0

        # Check item structure
        item = items[0]
        assert "artifact_name" in item
        assert "artifact_type" in item
        assert "deployment_count" in item
        assert "usage_count" in item
        assert "last_used" in item
        assert "collections" in item

    def test_get_top_artifacts_with_pagination(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test pagination for top artifacts."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ), patch(
            "skillmeat.api.routers.analytics.CollectionManager"
        ) as mock_coll_mgr_class, patch(
            "skillmeat.api.routers.analytics.ArtifactManager"
        ) as mock_art_mgr_class:
            mock_coll_mgr = MagicMock()
            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr_class.return_value = mock_coll_mgr

            mock_art_mgr = MagicMock()
            mock_art_mgr.show.return_value = MagicMock()
            mock_art_mgr_class.return_value = mock_art_mgr

            response = client.get("/api/v1/analytics/top-artifacts?limit=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have pagination info
        assert data["page_info"]["has_next_page"] in [True, False]
        assert "start_cursor" in data["page_info"]

    def test_get_top_artifacts_with_type_filter(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test filtering top artifacts by type."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ), patch(
            "skillmeat.api.routers.analytics.CollectionManager"
        ) as mock_coll_mgr_class, patch(
            "skillmeat.api.routers.analytics.ArtifactManager"
        ) as mock_art_mgr_class:
            mock_coll_mgr = MagicMock()
            mock_coll_mgr.list_collections.return_value = ["default"]
            mock_coll_mgr_class.return_value = mock_coll_mgr

            mock_art_mgr = MagicMock()
            mock_art_mgr.show.return_value = MagicMock()
            mock_art_mgr_class.return_value = mock_art_mgr

            response = client.get("/api/v1/analytics/top-artifacts?artifact_type=skill")

        assert response.status_code == status.HTTP_200_OK


class TestUsageTrends:
    """Test GET /api/v1/analytics/trends endpoint."""

    def test_get_trends_success(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test getting usage trends."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ):
            response = client.get("/api/v1/analytics/trends")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "period_type" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "data_points" in data
        assert "total_periods" in data

        # Check data points
        data_points = data["data_points"]
        assert isinstance(data_points, list)

        if len(data_points) > 0:
            point = data_points[0]
            assert "timestamp" in point
            assert "period" in point
            assert "deployment_count" in point
            assert "usage_count" in point
            assert "unique_artifacts" in point
            assert "top_artifact" in point

    def test_get_trends_with_period_hour(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test trends with hourly aggregation."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ):
            response = client.get("/api/v1/analytics/trends?period=hour&days=1")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["period_type"] == "hour"

    def test_get_trends_with_period_week(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test trends with weekly aggregation."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ):
            response = client.get("/api/v1/analytics/trends?period=week&days=90")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["period_type"] == "week"

    def test_get_trends_with_period_month(
        self, client, mock_config_manager, mock_analytics_db
    ):
        """Test trends with monthly aggregation."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ), patch(
            "skillmeat.storage.analytics.AnalyticsDB",
            return_value=mock_analytics_db,
        ):
            response = client.get("/api/v1/analytics/trends?period=month&days=365")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["period_type"] == "month"

    def test_get_trends_invalid_period(self, client, mock_config_manager):
        """Test trends with invalid period."""
        with patch(
            "skillmeat.api.routers.analytics.ConfigManagerDep",
            return_value=mock_config_manager,
        ):
            response = client.get("/api/v1/analytics/trends?period=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAnalyticsAuth:
    """Test authentication for analytics endpoints."""

    def test_analytics_with_api_key_enabled(self):
        """Test that API key is required when enabled."""
        test_settings = APISettings(
            env=Environment.TESTING,
            api_key_enabled=True,
            api_key="test-api-key",
        )

        from skillmeat.api.config import get_settings

        app = create_app(test_settings)
        app.dependency_overrides[get_settings] = lambda: test_settings

        with TestClient(app) as client:
            # Request without API key should fail
            response = client.get("/api/v1/analytics/summary")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

            # Request with valid API key should succeed
            response = client.get(
                "/api/v1/analytics/summary", headers={"X-API-Key": "test-api-key"}
            )
            # May fail for other reasons, but not auth
            assert response.status_code != status.HTTP_401_UNAUTHORIZED
