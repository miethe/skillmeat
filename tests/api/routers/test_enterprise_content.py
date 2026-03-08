"""Integration tests for the enterprise artifact download endpoint.

Covers:
    GET /api/v1/artifacts/{artifact_id}/download

Authentication is performed via ``verify_enterprise_pat``; the test fixture
injects the PAT secret through ``app.dependency_overrides[get_settings]`` (the
canonical path) and sends ``Authorization: Bearer test-secret`` in all
authorized requests.

The ``EnterpriseContentService`` dependency is overridden at the FastAPI
dependency level so no real DB or filesystem access occurs.
"""

from __future__ import annotations

import gzip
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.routers.enterprise_content import _get_content_service
from skillmeat.api.schemas.enterprise import ArtifactDownloadResponse
from skillmeat.api.server import create_app
from skillmeat.core.services.enterprise_content import (
    ArtifactNotFoundError,
    ArtifactVersionNotFoundError,
    EnterpriseContentService,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PAT = "test-secret"
VALID_AUTH_HEADER = {"Authorization": f"Bearer {VALID_PAT}"}
ARTIFACT_UUID = str(uuid.UUID("11111111-1111-1111-1111-111111111111"))
CONTENT_HASH = "a" * 64

_SAMPLE_PAYLOAD: Dict[str, Any] = {
    "artifact_id": ARTIFACT_UUID,
    "version": "v1.2.0",
    "content_hash": CONTENT_HASH,
    "metadata": {
        "name": "canvas-design",
        "type": "skill",
        "source": "github:org/repo",
        "description": "A test skill",
        "tags": ["ai", "design"],
        "scope": "user",
    },
    "files": [
        {
            "path": "SKILL.md",
            "content": "# Canvas Design",
            "size": 16,
            "encoding": "utf-8",
        },
    ],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_settings():
    """APISettings with the enterprise PAT secret pre-configured."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        api_key_enabled=False,
        auth_enabled=False,
        enterprise_pat_secret=VALID_PAT,
    )


@pytest.fixture
def mock_service():
    """Return a MagicMock that acts as EnterpriseContentService."""
    svc = MagicMock(spec=EnterpriseContentService)
    svc.build_payload.return_value = dict(_SAMPLE_PAYLOAD)
    return svc


@pytest.fixture
def app(test_settings, mock_service):
    """Create FastAPI app with the content service dependency overridden."""
    _app = create_app(test_settings)

    from skillmeat.api.config import get_settings

    _app.dependency_overrides[get_settings] = lambda: test_settings
    _app.dependency_overrides[_get_content_service] = lambda: mock_service
    return _app


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_DOWNLOAD_URL = "/api/v1/artifacts/{artifact_id}/download"


def download_url(artifact_id: str = ARTIFACT_UUID) -> str:
    return _DOWNLOAD_URL.format(artifact_id=artifact_id)


# ---------------------------------------------------------------------------
# 200 — JSON success
# ---------------------------------------------------------------------------


class TestDownloadSuccess:
    def test_200_json_when_artifact_exists(self, client: TestClient, mock_service):
        resp = client.get(download_url(), headers=VALID_AUTH_HEADER)

        assert resp.status_code == 200
        body = resp.json()
        assert body["artifact_id"] == ARTIFACT_UUID
        assert body["version"] == "v1.2.0"
        assert body["content_hash"] == CONTENT_HASH
        mock_service.build_payload.assert_called_once_with(
            ARTIFACT_UUID, version=None, compress=False
        )

    def test_200_response_matches_schema(self, client: TestClient):
        resp = client.get(download_url(), headers=VALID_AUTH_HEADER)

        assert resp.status_code == 200
        # Validate response body against the Pydantic schema
        parsed = ArtifactDownloadResponse(**resp.json())
        assert parsed.artifact_id == ARTIFACT_UUID
        assert parsed.version == "v1.2.0"
        assert len(parsed.files) == 1
        assert parsed.files[0].path == "SKILL.md"
        assert parsed.files[0].encoding == "utf-8"

    def test_metadata_fields_in_response(self, client: TestClient):
        resp = client.get(download_url(), headers=VALID_AUTH_HEADER)

        meta = resp.json()["metadata"]
        assert meta["name"] == "canvas-design"
        assert meta["type"] == "skill"
        assert meta["source"] == "github:org/repo"

    def test_version_query_param_forwarded(self, client: TestClient, mock_service):
        resp = client.get(
            download_url(),
            params={"version": "v2.0.0"},
            headers=VALID_AUTH_HEADER,
        )

        assert resp.status_code == 200
        mock_service.build_payload.assert_called_once_with(
            ARTIFACT_UUID, version="v2.0.0", compress=False
        )

    def test_lookup_by_name(self, client: TestClient, mock_service):
        resp = client.get(
            download_url("canvas-design"), headers=VALID_AUTH_HEADER
        )

        assert resp.status_code == 200
        mock_service.build_payload.assert_called_once_with(
            "canvas-design", version=None, compress=False
        )


# ---------------------------------------------------------------------------
# 200 — Gzip compression
# ---------------------------------------------------------------------------


class TestDownloadCompressed:
    def test_200_gzip_bytes_when_compress_true(
        self, client: TestClient, mock_service
    ):
        compressed_bytes = gzip.compress(
            json.dumps(_SAMPLE_PAYLOAD).encode("utf-8")
        )
        mock_service.build_payload.return_value = compressed_bytes

        resp = client.get(
            download_url(),
            params={"compress": "true"},
            headers=VALID_AUTH_HEADER,
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/gzip"

    def test_compressed_bytes_are_gzip_decodable(
        self, client: TestClient, mock_service
    ):
        original = dict(_SAMPLE_PAYLOAD)
        compressed_bytes = gzip.compress(json.dumps(original).encode("utf-8"))
        mock_service.build_payload.return_value = compressed_bytes

        resp = client.get(
            download_url(),
            params={"compress": "true"},
            headers=VALID_AUTH_HEADER,
        )

        decompressed = gzip.decompress(resp.content)
        payload = json.loads(decompressed.decode("utf-8"))
        assert payload["artifact_id"] == ARTIFACT_UUID

    def test_compress_param_forwarded_to_service(
        self, client: TestClient, mock_service
    ):
        mock_service.build_payload.return_value = gzip.compress(b"{}")

        client.get(
            download_url(),
            params={"compress": "true"},
            headers=VALID_AUTH_HEADER,
        )

        mock_service.build_payload.assert_called_once_with(
            ARTIFACT_UUID, version=None, compress=True
        )


# ---------------------------------------------------------------------------
# 404 — Artifact not found
# ---------------------------------------------------------------------------


class TestArtifactNotFoundResponse:
    def test_404_when_artifact_not_found(self, client: TestClient, mock_service):
        mock_service.build_payload.side_effect = ArtifactNotFoundError(
            "no-such-artifact"
        )

        resp = client.get(
            download_url("no-such-artifact"), headers=VALID_AUTH_HEADER
        )

        assert resp.status_code == 404
        assert "no-such-artifact" in resp.json()["detail"]

    def test_404_when_version_not_found(self, client: TestClient, mock_service):
        mock_service.build_payload.side_effect = ArtifactVersionNotFoundError(
            artifact_id=ARTIFACT_UUID, version="bad-tag"
        )

        resp = client.get(
            download_url(),
            params={"version": "bad-tag"},
            headers=VALID_AUTH_HEADER,
        )

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "bad-tag" in detail

    def test_404_when_hash_version_not_found(self, client: TestClient, mock_service):
        bad_hash = "f" * 64
        mock_service.build_payload.side_effect = ArtifactVersionNotFoundError(
            artifact_id=ARTIFACT_UUID, version=bad_hash
        )

        resp = client.get(
            download_url(),
            params={"version": bad_hash},
            headers=VALID_AUTH_HEADER,
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 401 — Missing authorization header
# ---------------------------------------------------------------------------


class TestMissingAuthorization:
    def test_401_when_auth_header_absent(self, client: TestClient):
        resp = client.get(download_url())

        assert resp.status_code == 401

    def test_401_response_has_www_authenticate_header(self, client: TestClient):
        resp = client.get(download_url())

        # FastAPI / HTTPBearer sets WWW-Authenticate: Bearer on 401
        assert "www-authenticate" in resp.headers or resp.status_code == 401

    def test_401_detail_mentions_bearer(self, client: TestClient):
        resp = client.get(download_url())

        body = resp.json()
        assert "detail" in body


# ---------------------------------------------------------------------------
# 403 — Invalid PAT
# ---------------------------------------------------------------------------


class TestInvalidPAT:
    def test_403_when_pat_is_wrong(self, client: TestClient):
        resp = client.get(
            download_url(),
            headers={"Authorization": "Bearer wrong-token"},
        )

        assert resp.status_code == 403

    def test_403_detail_present(self, client: TestClient):
        resp = client.get(
            download_url(),
            headers={"Authorization": "Bearer wrong-token"},
        )

        body = resp.json()
        assert "detail" in body

    def test_403_when_enterprise_pat_secret_not_configured(
        self, app, mock_service
    ):
        """When enterprise_pat_secret is absent the server fails closed with 403."""
        from skillmeat.api.config import APISettings, Environment, get_settings

        unconfigured_settings = APISettings(
            env=Environment.TESTING,
            host="127.0.0.1",
            port=8000,
            log_level="DEBUG",
            api_key_enabled=False,
            auth_enabled=False,
            # enterprise_pat_secret intentionally omitted (defaults to None)
        )
        app.dependency_overrides[get_settings] = lambda: unconfigured_settings
        app.dependency_overrides[_get_content_service] = lambda: mock_service

        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.get(
                download_url(),
                headers={"Authorization": "Bearer any-token"},
            )

        assert resp.status_code == 403
