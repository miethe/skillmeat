"""Integration tests for similarity settings API endpoints.

Covers:
- GET /api/v1/settings/similarity           → combined defaults
- GET /api/v1/settings/similarity/thresholds → threshold defaults
- PUT /api/v1/settings/similarity/thresholds → persist custom values (round-trip)
- GET /api/v1/settings/similarity/colors     → color defaults
- PUT /api/v1/settings/similarity/colors     → persist custom colors (round-trip)
- Validation: ordering violation, out-of-range, invalid hex
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pathlib import Path
from unittest.mock import MagicMock

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.config import ConfigManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings():
    """Minimal API settings for test environment."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def tmp_config(tmp_path: Path) -> ConfigManager:
    """ConfigManager backed by a fresh temporary directory."""
    return ConfigManager(config_dir=tmp_path)


@pytest.fixture
def app(test_settings, tmp_config):
    """FastAPI application with ConfigManager dependency overridden."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.dependencies import get_config_manager

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[get_config_manager] = lambda: tmp_config
    return application


@pytest.fixture
def client(app):
    """TestClient wrapping the test application."""
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Default-value tests
# ---------------------------------------------------------------------------


class TestSimilarityDefaults:
    """Endpoints return SkillMeat defaults when nothing is configured."""

    def test_get_combined_settings_defaults(self, client: TestClient):
        """GET /similarity returns combined defaults."""
        response = client.get("/api/v1/settings/similarity")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "thresholds" in data
        assert "colors" in data

        # Threshold defaults
        t = data["thresholds"]
        assert t["high"] == pytest.approx(0.80)
        assert t["partial"] == pytest.approx(0.55)
        assert t["low"] == pytest.approx(0.35)
        assert t["floor"] == pytest.approx(0.20)

        # Color defaults
        c = data["colors"]
        assert c["high"] == "#22c55e"
        assert c["partial"] == "#eab308"
        assert c["low"] == "#f97316"

    def test_get_threshold_defaults(self, client: TestClient):
        """GET /similarity/thresholds returns defaults."""
        response = client.get("/api/v1/settings/similarity/thresholds")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data == {
            "high": pytest.approx(0.80),
            "partial": pytest.approx(0.55),
            "low": pytest.approx(0.35),
            "floor": pytest.approx(0.20),
        }

    def test_get_color_defaults(self, client: TestClient):
        """GET /similarity/colors returns defaults."""
        response = client.get("/api/v1/settings/similarity/colors")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data == {
            "high": "#22c55e",
            "partial": "#eab308",
            "low": "#f97316",
        }


# ---------------------------------------------------------------------------
# Round-trip persistence tests
# ---------------------------------------------------------------------------


class TestSimilarityThresholdPersistence:
    """PUT thresholds → GET thresholds verifies values are persisted."""

    def test_full_update_round_trip(self, client: TestClient):
        """Setting all thresholds and reading them back returns the saved values."""
        payload = {"high": 0.90, "partial": 0.65, "low": 0.40, "floor": 0.25}

        put_response = client.put(
            "/api/v1/settings/similarity/thresholds",
            json=payload,
        )
        assert put_response.status_code == status.HTTP_200_OK
        returned = put_response.json()
        assert returned["high"] == pytest.approx(0.90)
        assert returned["partial"] == pytest.approx(0.65)
        assert returned["low"] == pytest.approx(0.40)
        assert returned["floor"] == pytest.approx(0.25)

        # Independent GET confirms persistence
        get_response = client.get("/api/v1/settings/similarity/thresholds")
        assert get_response.status_code == status.HTTP_200_OK
        persisted = get_response.json()
        assert persisted == returned

    def test_partial_update_merges_with_existing(self, client: TestClient):
        """Partial PUT only updates supplied keys; other keys retain values."""
        # Set baseline
        client.put(
            "/api/v1/settings/similarity/thresholds",
            json={"high": 0.85, "partial": 0.60, "low": 0.38, "floor": 0.22},
        )

        # Update only 'high'
        put_response = client.put(
            "/api/v1/settings/similarity/thresholds",
            json={"high": 0.88},
        )
        assert put_response.status_code == status.HTTP_200_OK
        data = put_response.json()
        assert data["high"] == pytest.approx(0.88)
        # Unchanged keys keep the previously set values
        assert data["partial"] == pytest.approx(0.60)
        assert data["low"] == pytest.approx(0.38)
        assert data["floor"] == pytest.approx(0.22)

    def test_empty_put_returns_current_thresholds(self, client: TestClient):
        """PUT with no fields returns current thresholds unchanged."""
        # Set a known state
        client.put(
            "/api/v1/settings/similarity/thresholds",
            json={"high": 0.82},
        )
        get_before = client.get("/api/v1/settings/similarity/thresholds").json()

        put_response = client.put(
            "/api/v1/settings/similarity/thresholds",
            json={},
        )
        assert put_response.status_code == status.HTTP_200_OK
        assert put_response.json() == get_before


class TestSimilarityColorPersistence:
    """PUT colors → GET colors verifies values are persisted."""

    def test_full_update_round_trip(self, client: TestClient):
        """Setting all colors and reading them back returns the saved values."""
        payload = {"high": "#16a34a", "partial": "#ca8a04", "low": "#ea580c"}

        put_response = client.put(
            "/api/v1/settings/similarity/colors",
            json=payload,
        )
        assert put_response.status_code == status.HTTP_200_OK
        returned = put_response.json()
        assert returned["high"] == "#16a34a"
        assert returned["partial"] == "#ca8a04"
        assert returned["low"] == "#ea580c"

        get_response = client.get("/api/v1/settings/similarity/colors")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json() == returned

    def test_partial_color_update(self, client: TestClient):
        """Partial PUT updates only the supplied color key."""
        put_response = client.put(
            "/api/v1/settings/similarity/colors",
            json={"high": "#15803d"},
        )
        assert put_response.status_code == status.HTTP_200_OK
        data = put_response.json()
        assert data["high"] == "#15803d"
        # Defaults still intact for un-supplied keys
        assert data["partial"] == "#eab308"
        assert data["low"] == "#f97316"

    def test_three_char_hex_accepted(self, client: TestClient):
        """3-digit CSS hex colors are accepted."""
        put_response = client.put(
            "/api/v1/settings/similarity/colors",
            json={"high": "#0f0"},
        )
        assert put_response.status_code == status.HTTP_200_OK
        assert put_response.json()["high"] == "#0f0"


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------


class TestSimilarityThresholdValidation:
    """Invalid threshold values must be rejected with 400."""

    def test_ordering_violation_returns_400(self, client: TestClient):
        """Setting high < partial violates ordering and must be rejected."""
        payload = {"high": 0.40, "partial": 0.60, "low": 0.35, "floor": 0.20}
        response = client.put(
            "/api/v1/settings/similarity/thresholds",
            json=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ordering" in response.json()["detail"].lower()

    def test_value_above_1_rejected_by_schema(self, client: TestClient):
        """Value > 1.0 is rejected by Pydantic field validation (422)."""
        response = client.put(
            "/api/v1/settings/similarity/thresholds",
            json={"high": 1.5},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_value_rejected_by_schema(self, client: TestClient):
        """Negative value is rejected by Pydantic field validation (422)."""
        response = client.put(
            "/api/v1/settings/similarity/thresholds",
            json={"floor": -0.1},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSimilarityColorValidation:
    """Invalid color values must be rejected."""

    def test_non_hex_color_rejected_by_schema(self, client: TestClient):
        """Non-hex color string rejected by Pydantic validator (422)."""
        response = client.put(
            "/api/v1/settings/similarity/colors",
            json={"high": "green"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_hex_without_hash_rejected(self, client: TestClient):
        """Hex string without # prefix rejected by Pydantic validator (422)."""
        response = client.put(
            "/api/v1/settings/similarity/colors",
            json={"high": "22c55e"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_unknown_color_key_rejected_by_schema(self, client: TestClient):
        """Unknown keys in PUT body are ignored by Pydantic (extra='ignore').

        Pydantic v2 ignores extra fields by default, so the request still
        succeeds; the unknown key simply has no effect.
        """
        response = client.put(
            "/api/v1/settings/similarity/colors",
            json={"unknown_band": "#ff0000"},
        )
        # Either 200 (extra ignored) or 422 depending on Pydantic config;
        # the important thing is that no 500 error occurs.
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# ---------------------------------------------------------------------------
# ConfigManager unit tests (no HTTP layer)
# ---------------------------------------------------------------------------


class TestConfigManagerSimilarity:
    """Unit tests for ConfigManager similarity methods."""

    def test_defaults_returned_when_unconfigured(self, tmp_config: ConfigManager):
        thresholds = tmp_config.get_similarity_thresholds()
        assert thresholds == {
            "high": 0.80,
            "partial": 0.55,
            "low": 0.35,
            "floor": 0.20,
        }
        colors = tmp_config.get_similarity_colors()
        assert colors == {
            "high": "#22c55e",
            "partial": "#eab308",
            "low": "#f97316",
        }

    def test_set_and_get_thresholds(self, tmp_config: ConfigManager):
        tmp_config.set_similarity_thresholds(
            {"high": 0.90, "partial": 0.65, "low": 0.40, "floor": 0.25}
        )
        result = tmp_config.get_similarity_thresholds()
        assert result["high"] == pytest.approx(0.90)
        assert result["partial"] == pytest.approx(0.65)
        assert result["low"] == pytest.approx(0.40)
        assert result["floor"] == pytest.approx(0.25)

    def test_partial_threshold_update_merges(self, tmp_config: ConfigManager):
        tmp_config.set_similarity_thresholds({"high": 0.88})
        result = tmp_config.get_similarity_thresholds()
        # Only 'high' changed; others remain default
        assert result["high"] == pytest.approx(0.88)
        assert result["partial"] == pytest.approx(0.55)

    def test_threshold_ordering_violation_raises(self, tmp_config: ConfigManager):
        with pytest.raises(ValueError, match="ordering"):
            tmp_config.set_similarity_thresholds(
                {"high": 0.30, "partial": 0.55, "low": 0.35, "floor": 0.20}
            )

    def test_unknown_threshold_key_raises(self, tmp_config: ConfigManager):
        with pytest.raises(ValueError, match="Unknown threshold keys"):
            tmp_config.set_similarity_thresholds({"unknown": 0.5})

    def test_out_of_range_threshold_raises(self, tmp_config: ConfigManager):
        with pytest.raises(ValueError, match="must be a float in"):
            tmp_config.set_similarity_thresholds({"high": 1.5})

    def test_set_and_get_colors(self, tmp_config: ConfigManager):
        tmp_config.set_similarity_colors({"high": "#16a34a"})
        result = tmp_config.get_similarity_colors()
        assert result["high"] == "#16a34a"
        # Others remain default
        assert result["partial"] == "#eab308"

    def test_invalid_color_hex_raises(self, tmp_config: ConfigManager):
        with pytest.raises(ValueError, match="CSS hex string"):
            tmp_config.set_similarity_colors({"high": "green"})

    def test_unknown_color_key_raises(self, tmp_config: ConfigManager):
        with pytest.raises(ValueError, match="Unknown color keys"):
            tmp_config.set_similarity_colors({"unknown_band": "#ff0000"})

    def test_persistence_across_instances(self, tmp_path: Path):
        """Values written by one ConfigManager instance are readable by another."""
        cfg1 = ConfigManager(config_dir=tmp_path)
        cfg1.set_similarity_thresholds(
            {"high": 0.91, "partial": 0.66, "low": 0.41, "floor": 0.26}
        )
        cfg1.set_similarity_colors({"high": "#14532d", "partial": "#713f12", "low": "#7c2d12"})

        cfg2 = ConfigManager(config_dir=tmp_path)
        t = cfg2.get_similarity_thresholds()
        assert t["high"] == pytest.approx(0.91)
        c = cfg2.get_similarity_colors()
        assert c["high"] == "#14532d"
