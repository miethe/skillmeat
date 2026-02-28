"""Tests for the WORKFLOW_ENGINE_ENABLED feature flag.

Covers:
  - Flag appears in GET /api/v1/config/feature-flags response
  - Workflow API endpoints return 404 when flag is False
  - Workflow API endpoints work normally when flag is True
  - CLI workflow commands show "coming soon" when flag is False
  - CLI workflow commands execute normally when flag is True
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cli import main


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_FLAGS_URL = "/api/v1/config/feature-flags"
WORKFLOWS_URL = "/api/v1/workflows"
EXECUTIONS_URL = "/api/v1/workflow-executions"

RUNNER = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> APISettings:
    """Return an APISettings instance suitable for testing."""
    defaults = dict(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=False,
        api_key_enabled=False,
        auth_enabled=False,
        rate_limit_enabled=False,
    )
    defaults.update(overrides)
    return APISettings(**defaults)


def _make_app(settings: APISettings) -> TestClient:
    """Create a FastAPI TestClient with dependency overrides applied."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token

    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[verify_token] = lambda: "test-token"
    return TestClient(application)


# ---------------------------------------------------------------------------
# Feature-flags endpoint
# ---------------------------------------------------------------------------


class TestFeatureFlagsEndpoint:
    """workflow_engine_enabled is included in the feature-flags response."""

    def test_flag_present_when_enabled(self) -> None:
        settings = _make_settings(workflow_engine_enabled=True)
        client = _make_app(settings)

        resp = client.get(FEATURE_FLAGS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert "workflow_engine_enabled" in data
        assert data["workflow_engine_enabled"] is True

    def test_flag_present_when_disabled(self) -> None:
        settings = _make_settings(workflow_engine_enabled=False)
        client = _make_app(settings)

        resp = client.get(FEATURE_FLAGS_URL)

        assert resp.status_code == 200
        data = resp.json()
        assert "workflow_engine_enabled" in data
        assert data["workflow_engine_enabled"] is False

    def test_existing_flags_still_present(self) -> None:
        """Ensure the new flag did not break existing flag fields."""
        settings = _make_settings()
        client = _make_app(settings)

        resp = client.get(FEATURE_FLAGS_URL)

        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "composite_artifacts_enabled",
            "deployment_sets_enabled",
            "memory_context_enabled",
            "workflow_engine_enabled",
        ):
            assert key in data, f"Missing flag: {key}"


# ---------------------------------------------------------------------------
# Workflow API routes — disabled
# ---------------------------------------------------------------------------


class TestWorkflowRoutesDisabled:
    """All workflow and workflow-execution routes return 404 when the flag is off."""

    @pytest.fixture(scope="class")
    def disabled_client(self) -> TestClient:
        settings = _make_settings(workflow_engine_enabled=False)
        return _make_app(settings)

    def test_list_workflows_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.get(WORKFLOWS_URL)
        assert resp.status_code == 404
        assert "not enabled" in resp.json()["detail"].lower()

    def test_create_workflow_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.post(
            WORKFLOWS_URL, json={"yaml_content": "name: test\nversion: '1.0.0'\nstages: []\n"}
        )
        assert resp.status_code == 404

    def test_get_workflow_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.get(f"{WORKFLOWS_URL}/some-id")
        assert resp.status_code == 404

    def test_delete_workflow_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.delete(f"{WORKFLOWS_URL}/some-id")
        assert resp.status_code == 404

    def test_list_executions_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.get(EXECUTIONS_URL)
        assert resp.status_code == 404
        assert "not enabled" in resp.json()["detail"].lower()

    def test_start_execution_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.post(
            EXECUTIONS_URL, json={"workflow_id": "some-id"}
        )
        assert resp.status_code == 404

    def test_get_execution_returns_404(self, disabled_client: TestClient) -> None:
        resp = disabled_client.get(f"{EXECUTIONS_URL}/some-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Workflow API routes — enabled
# ---------------------------------------------------------------------------


class TestWorkflowRoutesEnabled:
    """Workflow routes pass through normally when the flag is True."""

    @pytest.fixture(scope="class")
    def enabled_client(self) -> TestClient:
        settings = _make_settings(workflow_engine_enabled=True)
        return _make_app(settings)

    def test_list_workflows_not_404(self, enabled_client: TestClient) -> None:
        """When enabled, list endpoint must not return 404 (any other code is fine)."""
        with patch(
            "skillmeat.api.routers.workflows._get_service",
            return_value=MagicMock(list=MagicMock(return_value=[])),
        ):
            resp = enabled_client.get(WORKFLOWS_URL)
        assert resp.status_code != 404

    def test_list_executions_not_404(self, enabled_client: TestClient) -> None:
        with patch(
            "skillmeat.api.routers.workflow_executions._get_service",
            return_value=MagicMock(list=MagicMock(return_value=[])),
        ):
            resp = enabled_client.get(EXECUTIONS_URL)
        assert resp.status_code != 404


# ---------------------------------------------------------------------------
# CLI — feature flag disabled
# ---------------------------------------------------------------------------


class TestWorkflowCLIDisabled:
    """CLI workflow subcommands print a coming-soon message and exit 0 when disabled."""

    def _run_disabled(self, *args: str) -> object:
        """Invoke the CLI with workflow engine disabled via env var."""
        env = {**os.environ, "SKILLMEAT_WORKFLOW_ENGINE_ENABLED": "false"}
        return RUNNER.invoke(main, ["workflow"] + list(args), env=env, catch_exceptions=False)

    def test_list_shows_coming_soon(self) -> None:
        result = self._run_disabled("list")
        assert result.exit_code == 0
        assert "coming soon" in result.output.lower()

    def test_create_shows_coming_soon(self) -> None:
        result = self._run_disabled("create", "nonexistent.yaml")
        # The flag guard fires before Click validates the path argument.
        assert result.exit_code == 0
        assert "coming soon" in result.output.lower()

    def test_show_shows_coming_soon(self) -> None:
        result = self._run_disabled("show", "my-workflow")
        assert result.exit_code == 0
        assert "coming soon" in result.output.lower()

    def test_run_shows_coming_soon(self) -> None:
        result = self._run_disabled("run", "my-workflow")
        assert result.exit_code == 0
        assert "coming soon" in result.output.lower()

    def test_validate_shows_coming_soon(self) -> None:
        result = self._run_disabled("validate", "nonexistent.yaml")
        assert result.exit_code == 0
        assert "coming soon" in result.output.lower()


# ---------------------------------------------------------------------------
# CLI — feature flag enabled
# ---------------------------------------------------------------------------


class TestWorkflowCLIEnabled:
    """With the flag enabled, subcommands do not show the coming-soon message."""

    def _run_enabled(self, *args: str) -> object:
        env = {**os.environ, "SKILLMEAT_WORKFLOW_ENGINE_ENABLED": "true"}
        return RUNNER.invoke(main, ["workflow"] + list(args), env=env, catch_exceptions=False)

    def test_list_does_not_show_coming_soon(self) -> None:
        mock_svc = MagicMock()
        mock_svc.list.return_value = []
        with patch("skillmeat.core.workflow.service.WorkflowService", return_value=mock_svc):
            result = self._run_enabled("list")
        assert "coming soon" not in result.output.lower()

    def test_help_works_regardless_of_flag(self) -> None:
        """--help should never be blocked by the feature flag."""
        env = {**os.environ, "SKILLMEAT_WORKFLOW_ENGINE_ENABLED": "false"}
        result = RUNNER.invoke(main, ["workflow", "--help"], env=env, catch_exceptions=False)
        assert result.exit_code == 0
        assert "coming soon" not in result.output.lower()


# ---------------------------------------------------------------------------
# APISettings — env-var wiring
# ---------------------------------------------------------------------------


class TestAPISettingsFlag:
    """Ensure APISettings picks up SKILLMEAT_WORKFLOW_ENGINE_ENABLED."""

    def test_default_is_true(self) -> None:
        settings = APISettings(env=Environment.TESTING, _env_file=None)
        assert settings.workflow_engine_enabled is True

    def test_env_var_false_disables_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKILLMEAT_WORKFLOW_ENGINE_ENABLED", "false")
        settings = APISettings(env=Environment.TESTING)
        assert settings.workflow_engine_enabled is False

    def test_env_var_true_enables_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SKILLMEAT_WORKFLOW_ENGINE_ENABLED", "true")
        settings = APISettings(env=Environment.TESTING)
        assert settings.workflow_engine_enabled is True
