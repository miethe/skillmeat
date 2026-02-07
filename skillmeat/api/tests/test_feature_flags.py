"""Tests that memory context endpoints are always available."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.server import app


@pytest.fixture(scope="function")
def client():
    """Create a TestClient for the FastAPI app."""
    return TestClient(app)


class TestMemoryContextAvailability:
    """Memory routes are not gated by runtime feature flags."""

    def test_memory_items_not_gated(self, client: TestClient):
        """Memory items endpoint should not return 503."""
        with patch.dict(os.environ, {"SKILLMEAT_MEMORY_CONTEXT_ENABLED": "false"}):
            # Force reload settings to pick up the env var
            from skillmeat.api.config import reload_settings

            reload_settings()

            response = client.get("/api/v1/memory-items?project_id=test-project")
            assert response.status_code != 503

    def test_context_modules_not_gated(self, client: TestClient):
        """Context modules endpoint should not return 503."""
        with patch.dict(os.environ, {"SKILLMEAT_MEMORY_CONTEXT_ENABLED": "false"}):
            from skillmeat.api.config import reload_settings

            reload_settings()

            response = client.get("/api/v1/context-modules?project_id=test-project")
            assert response.status_code != 503

    def test_context_packs_not_gated(self, client: TestClient):
        """Context packs endpoint should not return 503."""
        with patch.dict(os.environ, {"SKILLMEAT_MEMORY_CONTEXT_ENABLED": "false"}):
            from skillmeat.api.config import reload_settings

            reload_settings()

            response = client.post(
                "/api/v1/context-packs/preview?project_id=test-project",
                json={},
            )
            assert response.status_code != 503

    def test_memory_items_enabled_by_default(self, client: TestClient):
        """Memory items endpoint should work with default settings."""
        with patch.dict(os.environ, {"SKILLMEAT_MEMORY_CONTEXT_ENABLED": "true"}):
            from skillmeat.api.config import reload_settings

            reload_settings()

            # We expect a normal response (not 503)
            # The endpoint might fail with other errors (missing project, etc.)
            # but it should not return 503
            response = client.get("/api/v1/memory-items?project_id=test-project")
            assert response.status_code != 503
