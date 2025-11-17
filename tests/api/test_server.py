"""Tests for FastAPI server application.

This module tests the core FastAPI application setup, including:
- Health endpoints
- Server startup/shutdown
- CORS configuration
- Error handling
- API versioning
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat import __version__ as skillmeat_version
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
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    """Create FastAPI app for testing."""
    from skillmeat.api.config import get_settings

    app = create_app(test_settings)

    # Override the settings dependency to use test_settings
    app.dependency_overrides[get_settings] = lambda: test_settings

    return app


@pytest.fixture
def client(app):
    """Create test client with lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_basic_health_check(self, client):
        """Test basic health check endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == skillmeat_version
        assert data["environment"] == "testing"
        assert "timestamp" in data
        assert "uptime_seconds" in data

    def test_detailed_health_check(self, client):
        """Test detailed health check includes component status."""
        response = client.get("/health/detailed")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "components" in data
        assert "system_info" in data

        # Check components
        components = data["components"]
        assert "collection_manager" in components
        assert "config_manager" in components
        assert "filesystem" in components

        # Check system info
        system_info = data["system_info"]
        assert "python_version" in system_info
        assert "platform" in system_info

    def test_readiness_check(self, client):
        """Test readiness endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data

    def test_liveness_check(self, client):
        """Test liveness endpoint."""
        response = client.get("/health/live")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data


class TestRootEndpoints:
    """Test root and version endpoints."""

    def test_root_endpoint(self, client, test_settings):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["name"] == test_settings.api_title
        assert data["version"] == skillmeat_version
        assert data["environment"] == "testing"
        assert data["api_prefix"] == "/api/v1"
        assert data["health_check"] == "/health"

    def test_version_endpoint(self, client, test_settings):
        """Test version endpoint returns version info."""
        response = client.get(f"{test_settings.api_prefix}/version")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["version"] == skillmeat_version
        assert data["api_version"] == test_settings.api_version
        assert data["environment"] == "testing"


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] in [
            "http://localhost:3000",
            "*",
        ]

    def test_cors_disabled(self):
        """Test CORS can be disabled."""
        settings = APISettings(
            env=Environment.TESTING,
            cors_enabled=False,
        )
        app = create_app(settings)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_405_method_not_allowed(self, client):
        """Test 405 error for wrong HTTP method."""
        response = client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation."""

    def test_openapi_schema(self, client, test_settings):
        """Test OpenAPI schema is accessible."""
        response = client.get(f"{test_settings.api_prefix}/openapi.json")
        assert response.status_code == status.HTTP_200_OK

        schema = response.json()
        assert schema["info"]["title"] == test_settings.api_title
        assert schema["info"]["version"] == skillmeat_version

    def test_docs_endpoint_in_development(self):
        """Test /docs endpoint is accessible in development."""
        settings = APISettings(env=Environment.DEVELOPMENT)
        app = create_app(settings)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == status.HTTP_200_OK

    def test_docs_endpoint_disabled_in_production(self):
        """Test /docs endpoint is disabled in production."""
        settings = APISettings(env=Environment.PRODUCTION)
        app = create_app(settings)
        client = TestClient(app)

        response = client.get("/docs")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestServerLifecycle:
    """Test server startup and shutdown."""

    def test_server_starts_successfully(self, client):
        """Test server starts and responds to requests."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_lifespan_context_initialization(self, app):
        """Test lifespan context initializes app state."""
        # App state should be initialized after lifespan startup
        from skillmeat.api.dependencies import app_state

        # TestClient handles lifespan automatically
        with TestClient(app):
            assert app_state.settings is not None
            assert app_state.config_manager is not None
            assert app_state.collection_manager is not None
            assert app_state.artifact_manager is not None


class TestConfiguration:
    """Test configuration loading and overrides."""

    def test_custom_port_and_host(self):
        """Test custom host and port configuration."""
        settings = APISettings(
            env=Environment.TESTING,
            host="0.0.0.0",
            port=9000,
        )
        app = create_app(settings)

        assert settings.host == "0.0.0.0"
        assert settings.port == 9000

    def test_api_prefix_configuration(self):
        """Test API prefix configuration."""
        settings = APISettings(
            env=Environment.TESTING,
            api_version="v2",
        )

        assert settings.api_prefix == "/api/v2"

    def test_environment_types(self):
        """Test different environment configurations."""
        dev_settings = APISettings(env=Environment.DEVELOPMENT)
        prod_settings = APISettings(env=Environment.PRODUCTION)
        test_settings = APISettings(env=Environment.TESTING)

        assert dev_settings.is_development is True
        assert dev_settings.is_production is False

        assert prod_settings.is_production is True
        assert prod_settings.is_development is False

        assert test_settings.is_testing is True
        assert test_settings.is_development is False


class TestAPIKeyAuthentication:
    """Test API key authentication."""

    def test_api_key_disabled_by_default(self, client):
        """Test API key authentication is disabled by default."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_api_key_enabled_requires_header(self):
        """Test API key authentication when enabled."""
        settings = APISettings(
            env=Environment.TESTING,
            api_key_enabled=True,
            api_key="test-api-key-12345",
        )
        app = create_app(settings)
        client = TestClient(app)

        # Health endpoint doesn't require auth
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

        # Future protected endpoints will require the API key
        # Example (when implemented):
        # response = client.get("/api/v1/collections")
        # assert response.status_code == status.HTTP_401_UNAUTHORIZED
        #
        # response = client.get(
        #     "/api/v1/collections",
        #     headers={"X-API-Key": "test-api-key-12345"}
        # )
        # assert response.status_code == status.HTTP_200_OK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
