"""Integration tests for custom color and icon-pack API endpoints.

Tests for:
    GET    /api/v1/colors              - List all custom colors
    POST   /api/v1/colors              - Create a color
    PUT    /api/v1/colors/{id}         - Update a color
    DELETE /api/v1/colors/{id}         - Delete a color
    GET    /api/v1/settings/icon-packs - List icon packs
    PATCH  /api/v1/settings/icon-packs - Toggle pack enabled state
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.migrations import get_alembic_config
from skillmeat.cache.models import create_tables
from skillmeat.core.services.custom_color_service import CustomColorService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database for color API tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture()
def temp_icon_config(tmp_path: Path) -> Generator[Path, None, None]:
    """Temporary icon-packs config file.

    The icon_packs router hard-codes the config path relative to the source
    file, so we patch ``_ICON_PACKS_CONFIG_PATH`` in the router module.
    """
    config_file = tmp_path / "icon-packs.config.json"
    config = {
        "packs": [
            {"id": "lucide-default", "name": "Lucide Default", "enabled": True},
            {"id": "heroicons", "name": "Heroicons", "enabled": False},
        ]
    }
    config_file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    yield config_file


@pytest.fixture()
def app(temp_db: str, temp_icon_config: Path):
    """Create a test FastAPI app with isolated DB and icon config."""
    from alembic import command as alembic_command
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token
    from skillmeat.api.routers import colors as colors_module
    from skillmeat.api.routers import icon_packs as icon_packs_module

    settings = APISettings(
        env=Environment.TESTING,
        api_key_enabled=False,
    )
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[verify_token] = lambda: "test-token"

    # Set up DB tables without running incremental Alembic migrations.
    create_tables(temp_db)
    alembic_command.stamp(get_alembic_config(temp_db), "head")

    # Patch CustomColorService to use the temp DB so each test has a clean slate.
    original_service_init = CustomColorService.__init__

    def _patched_service_init(self, db_path=None):
        original_service_init(self, db_path=temp_db)

    application.extra["_temp_db"] = temp_db
    application.extra["_temp_icon_config"] = temp_icon_config

    with (
        patch.object(CustomColorService, "__init__", _patched_service_init),
        patch.object(
            icon_packs_module,
            "_ICON_PACKS_CONFIG_PATH",
            temp_icon_config,
        ),
    ):
        yield application


@pytest.fixture()
def client(app) -> Generator[TestClient, None, None]:
    """TestClient bound to the test app."""
    with TestClient(app) as test_client:
        yield test_client


# Convenience shorthand for the color base URL
COLORS_URL = "/api/v1/colors"
ICON_PACKS_URL = "/api/v1/settings/icon-packs"


# =============================================================================
# Helper
# =============================================================================


def _create_color(client: TestClient, hex_val: str, name: str | None = None) -> dict:
    """POST a color and assert 201; return the JSON body."""
    payload: dict = {"hex": hex_val}
    if name is not None:
        payload["name"] = name
    resp = client.post(COLORS_URL, json=payload)
    assert resp.status_code == status.HTTP_201_CREATED, resp.text
    return resp.json()


# =============================================================================
# GET /api/v1/colors
# =============================================================================


class TestListColors:
    """Tests for GET /api/v1/colors."""

    def test_get_returns_empty_list_initially(self, client: TestClient) -> None:
        """Should return an empty list when no colors have been created."""
        resp = client.get(COLORS_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json() == []

    def test_get_returns_created_colors(self, client: TestClient) -> None:
        """Should include all colors that have been created."""
        _create_color(client, "#aabbcc", "Test Color")
        _create_color(client, "#112233")

        resp = client.get(COLORS_URL)
        assert resp.status_code == status.HTTP_200_OK
        colors = resp.json()
        assert len(colors) == 2
        hex_values = {c["hex"] for c in colors}
        assert "#aabbcc" in hex_values
        assert "#112233" in hex_values


# =============================================================================
# POST /api/v1/colors
# =============================================================================


class TestCreateColor:
    """Tests for POST /api/v1/colors."""

    def test_create_with_valid_hex_returns_201(self, client: TestClient) -> None:
        """Valid 6-digit hex with name should return 201 with all fields set."""
        resp = client.post(COLORS_URL, json={"hex": "#7c3aed", "name": "Brand Violet"})
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["hex"] == "#7c3aed"
        assert body["name"] == "Brand Violet"
        assert "id" in body
        assert body["id"]  # non-empty
        assert "created_at" in body

    def test_create_without_name_returns_201(self, client: TestClient) -> None:
        """Omitting the optional name field should still succeed."""
        resp = client.post(COLORS_URL, json={"hex": "#3b82f6"})
        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["hex"] == "#3b82f6"
        assert body["name"] is None

    def test_create_with_shorthand_hex_returns_201(self, client: TestClient) -> None:
        """3-digit shorthand hex (e.g. #fff) should be accepted."""
        resp = client.post(COLORS_URL, json={"hex": "#fff"})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["hex"] == "#fff"

    def test_create_with_invalid_hex_returns_422(self, client: TestClient) -> None:
        """Invalid hex string should return 422 Unprocessable Entity."""
        resp = client.post(COLORS_URL, json={"hex": "#xyz"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_with_missing_hash_returns_422(self, client: TestClient) -> None:
        """Hex value without leading '#' should be rejected with 422."""
        resp = client.post(COLORS_URL, json={"hex": "7c3aed"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_duplicate_hex_returns_422(self, client: TestClient) -> None:
        """Submitting the same hex twice should return 422 for the second request."""
        first = client.post(COLORS_URL, json={"hex": "#abcdef"})
        assert first.status_code == status.HTTP_201_CREATED

        second = client.post(COLORS_URL, json={"hex": "#abcdef"})
        assert second.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# PUT /api/v1/colors/{id}
# =============================================================================


class TestUpdateColor:
    """Tests for PUT /api/v1/colors/{id}."""

    def test_update_name_returns_200(self, client: TestClient) -> None:
        """Updating the name on an existing color should return 200."""
        created = _create_color(client, "#10b981", "Original Name")
        color_id = created["id"]

        resp = client.put(f"{COLORS_URL}/{color_id}", json={"name": "Updated Name"})
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["name"] == "Updated Name"
        assert body["hex"] == "#10b981"
        assert body["id"] == color_id

    def test_update_hex_returns_200(self, client: TestClient) -> None:
        """Updating the hex value to a different valid color should succeed."""
        created = _create_color(client, "#ef4444")
        color_id = created["id"]

        resp = client.put(f"{COLORS_URL}/{color_id}", json={"hex": "#f97316"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["hex"] == "#f97316"

    def test_update_with_invalid_hex_returns_422(self, client: TestClient) -> None:
        """Providing an invalid hex in an update should return 422."""
        created = _create_color(client, "#22c55e")
        color_id = created["id"]

        resp = client.put(f"{COLORS_URL}/{color_id}", json={"hex": "not-a-color"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_nonexistent_id_returns_404(self, client: TestClient) -> None:
        """Updating a color that does not exist should return 404."""
        resp = client.put(
            f"{COLORS_URL}/nonexistent-id-00000000",
            json={"name": "Ghost"},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# DELETE /api/v1/colors/{id}
# =============================================================================


class TestDeleteColor:
    """Tests for DELETE /api/v1/colors/{id}."""

    def test_delete_existing_color_returns_204(self, client: TestClient) -> None:
        """Deleting an existing color should return 204 No Content."""
        created = _create_color(client, "#6366f1")
        color_id = created["id"]

        resp = client.delete(f"{COLORS_URL}/{color_id}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_nonexistent_id_returns_404(self, client: TestClient) -> None:
        """Deleting a color that does not exist should return 404."""
        resp = client.delete(f"{COLORS_URL}/ghost-id-does-not-exist")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Full round-trip test
# =============================================================================


class TestColorRoundTrip:
    """End-to-end round-trip: POST → GET → DELETE → GET."""

    def test_full_round_trip(self, client: TestClient) -> None:
        """Color should appear in list after creation and disappear after deletion."""
        # POST: create
        created = _create_color(client, "#0ea5e9", "Sky Blue")
        color_id = created["id"]

        # GET: verify color is present
        list_resp = client.get(COLORS_URL)
        assert list_resp.status_code == status.HTTP_200_OK
        ids_in_list = [c["id"] for c in list_resp.json()]
        assert color_id in ids_in_list

        # DELETE: remove the color
        del_resp = client.delete(f"{COLORS_URL}/{color_id}")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

        # GET: verify color is no longer present
        list_resp_after = client.get(COLORS_URL)
        assert list_resp_after.status_code == status.HTTP_200_OK
        ids_after = [c["id"] for c in list_resp_after.json()]
        assert color_id not in ids_after


# =============================================================================
# GET /api/v1/settings/icon-packs
# =============================================================================


class TestListIconPacks:
    """Tests for GET /api/v1/settings/icon-packs."""

    def test_get_returns_pack_list(self, client: TestClient) -> None:
        """Should return the packs defined in the config file."""
        resp = client.get(ICON_PACKS_URL)
        assert resp.status_code == status.HTTP_200_OK
        packs = resp.json()
        assert len(packs) == 2

    def test_get_includes_expected_pack_ids(self, client: TestClient) -> None:
        """Pack IDs from the fixture config should be present."""
        resp = client.get(ICON_PACKS_URL)
        assert resp.status_code == status.HTTP_200_OK
        ids = {p["id"] for p in resp.json()}
        assert "lucide-default" in ids
        assert "heroicons" in ids

    def test_get_returns_correct_enabled_states(self, client: TestClient) -> None:
        """Enabled state should match the fixture config initial values."""
        resp = client.get(ICON_PACKS_URL)
        packs = {p["id"]: p for p in resp.json()}
        assert packs["lucide-default"]["enabled"] is True
        assert packs["heroicons"]["enabled"] is False


# =============================================================================
# PATCH /api/v1/settings/icon-packs
# =============================================================================


class TestToggleIconPacks:
    """Tests for PATCH /api/v1/settings/icon-packs."""

    def test_patch_toggles_enabled_state(self, client: TestClient) -> None:
        """PATCH should flip a pack's enabled state and return the full list."""
        # Disable lucide-default (currently True) and enable heroicons (currently False)
        payload = [
            {"pack_id": "lucide-default", "enabled": False},
            {"pack_id": "heroicons", "enabled": True},
        ]
        resp = client.patch(ICON_PACKS_URL, json=payload)
        assert resp.status_code == status.HTTP_200_OK
        packs = {p["id"]: p for p in resp.json()}
        assert packs["lucide-default"]["enabled"] is False
        assert packs["heroicons"]["enabled"] is True

    def test_patch_persists_across_get(self, client: TestClient) -> None:
        """After a PATCH, a subsequent GET should reflect the new state."""
        client.patch(
            ICON_PACKS_URL,
            json=[{"pack_id": "heroicons", "enabled": True}],
        )
        get_resp = client.get(ICON_PACKS_URL)
        assert get_resp.status_code == status.HTTP_200_OK
        packs = {p["id"]: p for p in get_resp.json()}
        assert packs["heroicons"]["enabled"] is True

    def test_patch_unknown_pack_id_ignored(self, client: TestClient) -> None:
        """Updates for unrecognised pack IDs should be silently ignored."""
        payload = [{"pack_id": "does-not-exist", "enabled": False}]
        resp = client.patch(ICON_PACKS_URL, json=payload)
        assert resp.status_code == status.HTTP_200_OK
        # Original packs unchanged
        packs = {p["id"]: p for p in resp.json()}
        assert packs["lucide-default"]["enabled"] is True

    def test_patch_returns_full_pack_list(self, client: TestClient) -> None:
        """The PATCH response should contain every registered pack, not just updated ones."""
        payload = [{"pack_id": "lucide-default", "enabled": False}]
        resp = client.patch(ICON_PACKS_URL, json=payload)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()) == 2
