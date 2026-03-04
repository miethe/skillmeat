"""Tests for icon pack configuration API endpoints.

Covers all routes in skillmeat/api/routers/icon_packs.py:
- GET   /api/v1/settings/icon-packs
- PATCH /api/v1/settings/icon-packs
- POST  /api/v1/settings/icon-packs/install
- DELETE /api/v1/settings/icon-packs/{pack_id}
"""

import io
import json
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app


@pytest.fixture
def test_settings():
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
    )


@pytest.fixture
def app(test_settings):
    from skillmeat.api.config import get_settings

    _app = create_app(test_settings)
    _app.dependency_overrides[get_settings] = lambda: test_settings
    return _app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


_DEFAULT_CONFIG = {
    "packs": [
        {"id": "lucide-default", "name": "Lucide Default", "enabled": True}
    ]
}

_MULTI_PACK_CONFIG = {
    "packs": [
        {"id": "lucide-default", "name": "Lucide Default", "enabled": True},
        {"id": "custom-pack", "name": "Custom Pack", "enabled": False},
    ]
}


# ---------------------------------------------------------------------------
# GET /api/v1/settings/icon-packs
# ---------------------------------------------------------------------------


class TestListIconPacks:
    def test_list_icon_packs_success(self, client):
        """Returns 200 with a list of icon pack objects."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=_DEFAULT_CONFIG,
        ):
            response = client.get("/api/v1/settings/icon-packs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "lucide-default"
        assert data[0]["enabled"] is True

    def test_list_icon_packs_multiple_packs(self, client):
        """Returns all packs when config has multiple entries."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=_MULTI_PACK_CONFIG,
        ):
            response = client.get("/api/v1/settings/icon-packs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    def test_list_icon_packs_empty_config(self, client):
        """Config with no packs returns empty list."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value={"packs": []},
        ):
            response = client.get("/api/v1/settings/icon-packs")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_icon_packs_config_read_error_returns_500(self, client):
        """RuntimeError from config read → 500."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            side_effect=RuntimeError("Failed to read icon-packs config: disk error"),
        ):
            response = client.get("/api/v1/settings/icon-packs")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# PATCH /api/v1/settings/icon-packs
# ---------------------------------------------------------------------------


class TestUpdateIconPacks:
    def test_update_icon_packs_toggle_enabled(self, client):
        """Toggling a known pack updates and persists its enabled state."""
        written_config = {}

        def fake_write(config):
            written_config.update(config)

        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=json.loads(json.dumps(_DEFAULT_CONFIG)),
        ), patch(
            "skillmeat.api.routers.icon_packs._write_config",
            side_effect=fake_write,
        ):
            response = client.patch(
                "/api/v1/settings/icon-packs",
                json=[{"pack_id": "lucide-default", "enabled": False}],
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        toggled = next((p for p in data if p["id"] == "lucide-default"), None)
        assert toggled is not None
        assert toggled["enabled"] is False

    def test_update_icon_packs_unknown_id_ignored(self, client):
        """Unknown pack_id in update list is silently ignored."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=json.loads(json.dumps(_DEFAULT_CONFIG)),
        ), patch("skillmeat.api.routers.icon_packs._write_config"):
            response = client.patch(
                "/api/v1/settings/icon-packs",
                json=[{"pack_id": "non-existent-pack", "enabled": True}],
            )

        assert response.status_code == status.HTTP_200_OK
        # Only lucide-default in response, untouched
        data = response.json()
        assert data[0]["id"] == "lucide-default"
        assert data[0]["enabled"] is True

    def test_update_icon_packs_empty_updates(self, client):
        """Empty update list returns existing config unchanged."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=json.loads(json.dumps(_DEFAULT_CONFIG)),
        ), patch("skillmeat.api.routers.icon_packs._write_config"):
            response = client.patch("/api/v1/settings/icon-packs", json=[])

        assert response.status_code == status.HTTP_200_OK

    def test_update_icon_packs_config_read_error_returns_500(self, client):
        """RuntimeError reading config → 500."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            side_effect=RuntimeError("Failed to read icon-packs config: io error"),
        ):
            response = client.patch(
                "/api/v1/settings/icon-packs",
                json=[{"pack_id": "lucide-default", "enabled": False}],
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# POST /api/v1/settings/icon-packs/install
# ---------------------------------------------------------------------------


class TestInstallIconPack:
    _VALID_PACK = json.dumps(
        {"id": "my-pack", "name": "My Pack", "icons": [{"name": "circle"}]}
    ).encode()

    def test_install_icon_pack_from_file_success(self, client):
        """Valid file upload creates a new pack entry and returns 201."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=json.loads(json.dumps(_DEFAULT_CONFIG)),
        ), patch("skillmeat.api.routers.icon_packs._write_config"):
            response = client.post(
                "/api/v1/settings/icon-packs/install",
                files={"file": ("my-pack.json", io.BytesIO(self._VALID_PACK), "application/json")},
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == "my-pack"
        assert data["enabled"] is True

    def test_install_icon_pack_no_source_returns_400(self, client):
        """Neither url nor file provided → 400."""
        response = client.post("/api/v1/settings/icon-packs/install", data={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_install_icon_pack_both_sources_returns_400(self, client):
        """Both url and file provided → 400."""
        response = client.post(
            "/api/v1/settings/icon-packs/install",
            data={"url": "http://example.com/pack.json"},
            files={"file": ("pack.json", io.BytesIO(self._VALID_PACK), "application/json")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_install_icon_pack_invalid_json_returns_400(self, client):
        """Malformed JSON file → 400."""
        response = client.post(
            "/api/v1/settings/icon-packs/install",
            files={"file": ("bad.json", io.BytesIO(b"not-json"), "application/json")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_install_icon_pack_missing_required_field_returns_400(self, client):
        """JSON missing 'icons' field → 400."""
        bad_pack = json.dumps({"id": "partial-pack", "name": "Partial"}).encode()
        response = client.post(
            "/api/v1/settings/icon-packs/install",
            files={"file": ("partial.json", io.BytesIO(bad_pack), "application/json")},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_install_icon_pack_duplicate_id_returns_409(self, client):
        """Pack id already registered → 409 Conflict."""
        existing_pack = json.dumps(
            {"id": "lucide-default", "name": "Lucide Default", "icons": []}
        ).encode()
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=json.loads(json.dumps(_DEFAULT_CONFIG)),
        ):
            response = client.post(
                "/api/v1/settings/icon-packs/install",
                files={"file": ("dup.json", io.BytesIO(existing_pack), "application/json")},
            )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_install_icon_pack_from_url_fetch_error_returns_400(self, client):
        """URL fetch failure → 400."""
        import urllib.error

        with patch(
            "skillmeat.api.routers.icon_packs.urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            response = client.post(
                "/api/v1/settings/icon-packs/install",
                data={"url": "http://bad-host.example.com/pack.json"},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# DELETE /api/v1/settings/icon-packs/{pack_id}
# ---------------------------------------------------------------------------


class TestDeleteIconPack:
    def test_delete_icon_pack_success(self, client):
        """Custom pack is deleted and 204 is returned."""
        config = json.loads(json.dumps(_MULTI_PACK_CONFIG))

        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=config,
        ), patch("skillmeat.api.routers.icon_packs._write_config"):
            response = client.delete("/api/v1/settings/icon-packs/custom-pack")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_lucide_default_returns_400(self, client):
        """Built-in lucide-default cannot be deleted → 400."""
        response = client.delete("/api/v1/settings/icon-packs/lucide-default")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_nonexistent_pack_returns_404(self, client):
        """Deleting a pack that is not registered → 404."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=json.loads(json.dumps(_DEFAULT_CONFIG)),
        ):
            response = client.delete("/api/v1/settings/icon-packs/ghost-pack")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_icon_pack_config_read_error_returns_500(self, client):
        """RuntimeError reading config → 500."""
        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            side_effect=RuntimeError("Failed to read icon-packs config: disk error"),
        ):
            response = client.delete("/api/v1/settings/icon-packs/some-pack")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_delete_icon_pack_config_write_error_returns_500(self, client):
        """RuntimeError writing config after deletion → 500."""
        config = json.loads(json.dumps(_MULTI_PACK_CONFIG))

        with patch(
            "skillmeat.api.routers.icon_packs._read_config",
            return_value=config,
        ), patch(
            "skillmeat.api.routers.icon_packs._write_config",
            side_effect=RuntimeError("Failed to write icon-packs config: permission denied"),
        ):
            response = client.delete("/api/v1/settings/icon-packs/custom-pack")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
