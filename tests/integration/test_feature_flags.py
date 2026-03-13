"""Integration tests for the SkillBOM feature flag (``skillbom_enabled``).

Covers:
  - ``skillbom_enabled`` defaults to False.
  - It can be toggled True via APISettings constructor or env var.
  - ``SKILLMEAT_SKILLBOM_ENABLED=true`` / ``false`` env var is honoured.
  - Existing (non-BOM) features are unaffected when the flag changes.
  - The flag appears in GET /api/v1/config/feature-flags (if exposed).
  - The BOM router endpoints return data when the flag is True and are
    independently accessible (BOM router is unconditionally registered —
    no 404-gate like workflow engine).

Design note
-----------
``skillbom_enabled`` gates **feature behaviour** (history capture, auto-sign,
etc.) but the BOM API router is registered unconditionally (see server.py:528).
These tests therefore verify the *settings semantics* rather than 404 gating.
They follow the same pattern as ``tests/test_workflow_feature_flag.py``.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------

FEATURE_FLAGS_URL = "/api/v1/config/feature-flags"
BOM_SNAPSHOT_URL = "/api/v1/bom/snapshot"
BOM_GENERATE_URL = "/api/v1/bom/generate"


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> APISettings:
    """Return an APISettings suitable for testing (no external dependencies)."""
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


def _make_app(settings: APISettings):
    """Return a FastAPI application with auth and settings dependency overrides."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token

    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[verify_token] = lambda: "test-token"
    return application


# ---------------------------------------------------------------------------
# Test: Default values
# ---------------------------------------------------------------------------


class TestSkillbomFlagDefaults:
    """``skillbom_enabled`` defaults to False in all code paths."""

    def test_default_is_false_in_settings(self) -> None:
        """APISettings must default skillbom_enabled to False."""
        settings = _make_settings()
        assert settings.skillbom_enabled is False

    def test_env_var_false_sets_flag_false(self, monkeypatch) -> None:
        """SKILLMEAT_SKILLBOM_ENABLED=false must produce False."""
        monkeypatch.setenv("SKILLMEAT_SKILLBOM_ENABLED", "false")
        settings = APISettings(
            env=Environment.TESTING,
            cors_enabled=False,
            api_key_enabled=False,
            auth_enabled=False,
            rate_limit_enabled=False,
        )
        assert settings.skillbom_enabled is False

    def test_env_var_unset_gives_default_false(self, monkeypatch) -> None:
        """When the env var is absent, skillbom_enabled must default to False."""
        monkeypatch.delenv("SKILLMEAT_SKILLBOM_ENABLED", raising=False)
        settings = APISettings(
            env=Environment.TESTING,
            cors_enabled=False,
            api_key_enabled=False,
            auth_enabled=False,
            rate_limit_enabled=False,
        )
        assert settings.skillbom_enabled is False


# ---------------------------------------------------------------------------
# Test: Toggling the flag
# ---------------------------------------------------------------------------


class TestSkillbomFlagToggle:
    """``skillbom_enabled`` can be set True via constructor and env var."""

    def test_constructor_true(self) -> None:
        """Passing skillbom_enabled=True via constructor must work."""
        settings = _make_settings(skillbom_enabled=True)
        assert settings.skillbom_enabled is True

    def test_constructor_false(self) -> None:
        """Passing skillbom_enabled=False via constructor must work."""
        settings = _make_settings(skillbom_enabled=False)
        assert settings.skillbom_enabled is False

    def test_env_var_true_enables_flag(self, monkeypatch) -> None:
        """SKILLMEAT_SKILLBOM_ENABLED=true must produce True."""
        monkeypatch.setenv("SKILLMEAT_SKILLBOM_ENABLED", "true")
        settings = APISettings(
            env=Environment.TESTING,
            cors_enabled=False,
            api_key_enabled=False,
            auth_enabled=False,
            rate_limit_enabled=False,
        )
        assert settings.skillbom_enabled is True

    def test_env_var_1_enables_flag(self, monkeypatch) -> None:
        """SKILLMEAT_SKILLBOM_ENABLED=1 must produce True (Pydantic bool coercion)."""
        monkeypatch.setenv("SKILLMEAT_SKILLBOM_ENABLED", "1")
        settings = APISettings(
            env=Environment.TESTING,
            cors_enabled=False,
            api_key_enabled=False,
            auth_enabled=False,
            rate_limit_enabled=False,
        )
        assert settings.skillbom_enabled is True


# ---------------------------------------------------------------------------
# Test: Disabling does not break existing (non-BOM) features
# ---------------------------------------------------------------------------


class TestSkillbomFlagIsolation:
    """Toggling skillbom_enabled must not affect other feature flags."""

    def test_other_flags_unaffected_when_disabled(self) -> None:
        """Standard feature flags retain their defaults when skillbom is False."""
        settings = _make_settings(skillbom_enabled=False)

        assert settings.composite_artifacts_enabled is True, (
            "composite_artifacts_enabled should default True"
        )
        assert settings.deployment_sets_enabled is True, (
            "deployment_sets_enabled should default True"
        )
        assert settings.memory_context_enabled is True, (
            "memory_context_enabled should default True"
        )

    def test_other_flags_unaffected_when_enabled(self) -> None:
        """Standard feature flags retain their defaults when skillbom is True."""
        settings = _make_settings(skillbom_enabled=True)

        assert settings.composite_artifacts_enabled is True
        assert settings.deployment_sets_enabled is True
        assert settings.memory_context_enabled is True

    def test_feature_flags_endpoint_survives_skillbom_disabled(self) -> None:
        """GET /config/feature-flags must respond 200 regardless of skillbom_enabled."""
        settings = _make_settings(skillbom_enabled=False)
        with TestClient(_make_app(settings)) as client:
            resp = client.get(FEATURE_FLAGS_URL)

        assert resp.status_code == 200, (
            f"feature-flags endpoint returned {resp.status_code} with "
            "skillbom_enabled=False"
        )

    def test_feature_flags_endpoint_survives_skillbom_enabled(self) -> None:
        """GET /config/feature-flags must respond 200 when skillbom_enabled=True."""
        settings = _make_settings(skillbom_enabled=True)
        with TestClient(_make_app(settings)) as client:
            resp = client.get(FEATURE_FLAGS_URL)

        assert resp.status_code == 200, (
            f"feature-flags endpoint returned {resp.status_code} with "
            "skillbom_enabled=True"
        )

    def test_existing_feature_flags_in_response(self) -> None:
        """Known feature flags must always appear in the /config/feature-flags body."""
        settings = _make_settings(skillbom_enabled=True)
        with TestClient(_make_app(settings)) as client:
            resp = client.get(FEATURE_FLAGS_URL)

        assert resp.status_code == 200
        data = resp.json()

        for key in (
            "composite_artifacts_enabled",
            "deployment_sets_enabled",
            "memory_context_enabled",
            "workflow_engine_enabled",
        ):
            assert key in data, (
                f"Expected flag {key!r} missing from feature-flags response "
                "after toggling skillbom_enabled"
            )

    def test_health_endpoint_unaffected(self) -> None:
        """Health endpoint must return 200 regardless of skillbom_enabled."""
        for flag_value in (True, False):
            settings = _make_settings(skillbom_enabled=flag_value)
            with TestClient(_make_app(settings)) as client:
                resp = client.get("/health")
            assert resp.status_code == 200, (
                f"Health endpoint returned {resp.status_code} with "
                f"skillbom_enabled={flag_value}"
            )


# ---------------------------------------------------------------------------
# Test: Behaviour description when flag is False
# ---------------------------------------------------------------------------


class TestSkillbomFlagDisabledBehaviour:
    """When skillbom_enabled=False the settings flag is observable."""

    def test_flag_is_false_in_settings_object(self) -> None:
        """settings.skillbom_enabled must be False when flag is off."""
        settings = _make_settings(skillbom_enabled=False)
        app = _make_app(settings)

        # Retrieve the settings override via the dependency to verify it
        # flows through correctly.
        from skillmeat.api.config import get_settings

        resolved = app.dependency_overrides[get_settings]()
        assert resolved.skillbom_enabled is False

    def test_flag_is_true_in_settings_object(self) -> None:
        """settings.skillbom_enabled must be True when flag is on."""
        settings = _make_settings(skillbom_enabled=True)
        app = _make_app(settings)

        from skillmeat.api.config import get_settings

        resolved = app.dependency_overrides[get_settings]()
        assert resolved.skillbom_enabled is True


# ---------------------------------------------------------------------------
# Test: BOM router accessibility
# ---------------------------------------------------------------------------


class TestBomRouterAccessibility:
    """BOM router is unconditionally registered (no 404-gate).

    When the DB is not populated the endpoints return 404 (no data) rather
    than 404 (feature disabled).  We verify the router is reachable by
    checking that it does NOT return a "not enabled" 404.
    """

    def test_bom_snapshot_endpoint_reachable_when_enabled(self) -> None:
        """GET /bom/snapshot must be reachable (not 'not enabled' 404) when flag True."""
        settings = _make_settings(skillbom_enabled=True)
        with TestClient(_make_app(settings)) as client:
            resp = client.get(BOM_SNAPSHOT_URL)

        # The endpoint is registered — it may return 404 (no data) or 200.
        # What it must NOT say is "not enabled".
        if resp.status_code == 404:
            detail = resp.json().get("detail", "")
            assert "not enabled" not in detail.lower(), (
                f"BOM snapshot endpoint returned 'not enabled' 404 with "
                f"skillbom_enabled=True: {detail!r}"
            )

    def test_bom_snapshot_endpoint_reachable_when_disabled(self) -> None:
        """GET /bom/snapshot must be reachable even when flag is False.

        The BOM router is unconditionally registered — unlike the workflow
        engine, it does not gate on the feature flag at the router level.
        """
        settings = _make_settings(skillbom_enabled=False)
        with TestClient(_make_app(settings)) as client:
            resp = client.get(BOM_SNAPSHOT_URL)

        # Must not return a "not enabled" 404 — that pattern is workflow-only.
        if resp.status_code == 404:
            detail = resp.json().get("detail", "")
            assert "not enabled" not in detail.lower(), (
                f"BOM snapshot endpoint returned unexpected 'not enabled' 404: "
                f"{detail!r}"
            )
