"""Integration tests for BOM and attestation API endpoints (TASK-8.6).

Covers:
    GET  /api/v1/bom/snapshot      -- 200, 404, owner-scope filtering
    POST /api/v1/bom/generate      -- 201, auto-sign behaviour
    POST /api/v1/bom/verify        -- valid, invalid, missing signature
    GET  /api/v1/attestations      -- pagination, owner-scope, artifact_id filter
    POST /api/v1/attestations      -- creation, artifact validation, visibility
    GET  /api/v1/attestations/{id} -- 200, 404, cross-owner guard

All tests use FastAPI TestClient + MagicMock.  The DB session and auth context
are injected via ``app.dependency_overrides`` so no real database is required.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.auth import AuthContext, LOCAL_ADMIN_CONTEXT, Role, Scope


# =============================================================================
# Helpers
# =============================================================================

_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_TENANT_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")

_USER_AUTH = AuthContext(
    user_id=_USER_ID,
    tenant_id=None,
    roles=[Role.system_admin.value],
    scopes=[s.value for s in Scope],
)

_ENTERPRISE_AUTH = AuthContext(
    user_id=_USER_ID,
    tenant_id=_TENANT_ID,
    roles=[Role.system_admin.value],
    scopes=[s.value for s in Scope],
)


def _make_bom_json(artifact_count: int = 1) -> str:
    """Return a minimal serialised BOM dict."""
    return json.dumps(
        {
            "schema_version": "1.0.0",
            "generated_at": "2026-03-13T00:00:00Z",
            "artifact_count": artifact_count,
            "artifacts": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "source": "user/repo",
                    "version": "v1.0.0",
                    "content_hash": "abc123",
                    "metadata": {},
                }
            ][:artifact_count],
        }
    )


def _make_snapshot(
    snap_id: int = 1,
    owner_type: str = "user",
    project_id: Optional[str] = None,
    signature: Optional[str] = None,
    signature_algorithm: Optional[str] = None,
    signing_key_id: Optional[str] = None,
    bom_json: Optional[str] = None,
) -> MagicMock:
    """Build a MagicMock BomSnapshot ORM row."""
    snap = MagicMock()
    snap.id = snap_id
    snap.owner_type = owner_type
    snap.project_id = project_id
    snap.commit_sha = None
    snap.created_at = datetime(2026, 3, 13, 12, 0, 0, tzinfo=timezone.utc)
    snap.signature = signature
    snap.signature_algorithm = signature_algorithm
    snap.signing_key_id = signing_key_id
    snap.bom_json = bom_json or _make_bom_json()
    return snap


def _make_attestation(
    attest_id: int = 1,
    artifact_id: str = "skill:test-skill",
    owner_type: str = "user",
    owner_id: Optional[str] = None,
    roles: Optional[List[str]] = None,
    scopes: Optional[List[str]] = None,
    visibility: str = "private",
) -> MagicMock:
    """Build a MagicMock AttestationRecord ORM row."""
    rec = MagicMock()
    rec.id = attest_id
    rec.artifact_id = artifact_id
    rec.owner_type = owner_type
    rec.owner_id = owner_id or str(_USER_ID)
    rec.roles = roles or []
    rec.scopes = scopes or []
    rec.visibility = visibility
    rec.created_at = datetime(2026, 3, 13, 12, 0, 0, tzinfo=timezone.utc)
    return rec


class _MockQuery:
    """Minimal SQLAlchemy-like query chain for use in MagicMock DB sessions."""

    def __init__(self, rows: List[Any]) -> None:
        self._rows = rows

    def filter(self, *_args: Any, **_kwargs: Any) -> "_MockQuery":
        return self

    def order_by(self, *_args: Any) -> "_MockQuery":
        return self

    def first(self) -> Optional[Any]:
        return self._rows[0] if self._rows else None

    def limit(self, n: int) -> "_MockQuery":
        self._rows = self._rows[:n]
        return self

    def all(self) -> List[Any]:
        return list(self._rows)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _register_local_auth_provider():
    """Register LocalAuthProvider before each test and reset after.

    The BOM/attestation router has ``dependencies=_auth_deps`` applied at the
    server level, which calls ``require_auth()`` → ``get_auth_provider()``.
    Without a registered provider this raises 503.  LocalAuthProvider returns
    LOCAL_ADMIN_CONTEXT for every request (zero-config mode).
    """
    from skillmeat.api.auth.local_provider import LocalAuthProvider
    from skillmeat.api.dependencies import set_auth_provider
    import skillmeat.api.dependencies as _deps_module

    set_auth_provider(LocalAuthProvider())
    yield
    _deps_module._auth_provider = None


@pytest.fixture
def api_settings() -> APISettings:
    return APISettings(
        env="testing",
        api_key_enabled=False,
        cors_enabled=True,
    )


@pytest.fixture
def app(api_settings: APISettings):
    """Create a FastAPI test app with AppState initialised."""
    from skillmeat.api.dependencies import app_state
    from skillmeat.api.server import create_app

    application = create_app(api_settings)
    app_state.initialize(api_settings)
    yield application
    app_state.shutdown()


def _make_client(app, auth_ctx: AuthContext) -> TestClient:
    """Wire a TestClient with a mocked DB session and fixed AuthContext."""
    from skillmeat.api.dependencies import get_auth_context
    from skillmeat.cache.session import get_db_session

    mock_db = MagicMock()
    mock_db.close = MagicMock()

    # Override auth context — bypasses require_auth scope checks.
    app.dependency_overrides[get_auth_context] = lambda: auth_ctx
    # Override the DB session from the cache layer.
    app.dependency_overrides[get_db_session] = lambda: mock_db

    client = TestClient(app, raise_server_exceptions=False)
    client._mock_db = mock_db
    return client


@pytest.fixture
def user_client(app):
    """TestClient with user (non-tenant) AuthContext injected."""
    client = _make_client(app, _USER_AUTH)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def enterprise_client(app):
    """TestClient with enterprise (tenant) AuthContext injected."""
    client = _make_client(app, _ENTERPRISE_AUTH)
    yield client
    app.dependency_overrides.clear()


# =============================================================================
# GET /api/v1/bom/snapshot
# =============================================================================


class TestGetBomSnapshot:
    """Tests for GET /api/v1/bom/snapshot."""

    def test_200_returns_most_recent_snapshot(self, user_client: TestClient) -> None:
        """Returns 200 with the most recent BOM snapshot for the caller's scope."""
        snapshot = _make_snapshot(snap_id=42)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.get("/api/v1/bom/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 42
        assert data["owner_type"] == "user"
        assert "bom" in data
        assert data["bom"]["schema_version"] == "1.0.0"
        assert data["bom"]["artifact_count"] == 1

    def test_404_when_no_snapshot_exists(self, user_client: TestClient) -> None:
        """Returns 404 when no BOM snapshot exists for the caller's scope."""
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.get("/api/v1/bom/snapshot")

        assert response.status_code == 404
        assert "No BOM snapshot found" in response.json()["detail"]

    def test_enterprise_owner_scope_filter(self, enterprise_client: TestClient) -> None:
        """Enterprise auth context results in owner_type='enterprise' filter."""
        snapshot = _make_snapshot(snap_id=7, owner_type="enterprise")
        enterprise_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = enterprise_client.get("/api/v1/bom/snapshot")

        assert response.status_code == 200
        assert response.json()["owner_type"] == "enterprise"

    def test_memory_items_filtered_by_default(self, user_client: TestClient) -> None:
        """Memory-item artifact entries are excluded unless include_memory_items=true."""
        bom_with_memory = json.dumps(
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-03-13T00:00:00Z",
                "artifact_count": 2,
                "artifacts": [
                    {"name": "skill-a", "type": "skill", "content_hash": "aaa", "metadata": {}},
                    {"name": "mem-1", "type": "memory_item", "content_hash": "bbb", "metadata": {}},
                ],
            }
        )
        snapshot = _make_snapshot(bom_json=bom_with_memory)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.get("/api/v1/bom/snapshot")

        assert response.status_code == 200
        artifacts = response.json()["bom"]["artifacts"]
        types = [a["type"] for a in artifacts]
        assert "memory_item" not in types
        assert "skill" in types

    def test_memory_items_included_when_requested(self, user_client: TestClient) -> None:
        """Memory-item entries are present when include_memory_items=true."""
        bom_with_memory = json.dumps(
            {
                "schema_version": "1.0.0",
                "generated_at": "2026-03-13T00:00:00Z",
                "artifact_count": 2,
                "artifacts": [
                    {"name": "skill-a", "type": "skill", "content_hash": "aaa", "metadata": {}},
                    {"name": "mem-1", "type": "memory_item", "content_hash": "bbb", "metadata": {}},
                ],
            }
        )
        snapshot = _make_snapshot(bom_json=bom_with_memory)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.get("/api/v1/bom/snapshot?include_memory_items=true")

        assert response.status_code == 200
        types = [a["type"] for a in response.json()["bom"]["artifacts"]]
        assert "memory_item" in types

    def test_signatures_excluded_by_default(self, user_client: TestClient) -> None:
        """Signature fields are null unless include_signatures=true."""
        snapshot = _make_snapshot(
            signature="deadbeef",
            signature_algorithm="Ed25519",
            signing_key_id="fingerprint-abc",
        )
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.get("/api/v1/bom/snapshot")

        assert response.status_code == 200
        data = response.json()
        assert data["signature"] is None
        assert data["signature_algorithm"] is None
        assert data["signing_key_id"] is None

    def test_signatures_included_when_requested(self, user_client: TestClient) -> None:
        """Signature fields are populated when include_signatures=true."""
        snapshot = _make_snapshot(
            signature="deadbeef",
            signature_algorithm="Ed25519",
            signing_key_id="fingerprint-abc",
        )
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.get("/api/v1/bom/snapshot?include_signatures=true")

        assert response.status_code == 200
        data = response.json()
        assert data["signature"] == "deadbeef"
        assert data["signature_algorithm"] == "Ed25519"
        assert data["signing_key_id"] == "fingerprint-abc"

    def test_500_on_corrupted_bom_json(self, user_client: TestClient) -> None:
        """Returns 500 when the stored bom_json cannot be deserialised."""
        snapshot = _make_snapshot(bom_json="NOT_VALID_JSON{{{")
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.get("/api/v1/bom/snapshot")

        assert response.status_code == 500
        assert "corrupted" in response.json()["detail"].lower()


# =============================================================================
# POST /api/v1/bom/generate
# =============================================================================


class TestGenerateBom:
    """Tests for POST /api/v1/bom/generate."""

    def _make_persisted_snapshot(
        self,
        snap_id: int = 99,
        owner_type: str = "user",
        project_id: Optional[str] = None,
        signature: Optional[str] = None,
        signing_key_id: Optional[str] = None,
    ) -> MagicMock:
        snap = MagicMock()
        snap.id = snap_id
        snap.owner_type = owner_type
        snap.project_id = project_id
        snap.created_at = datetime(2026, 3, 13, 0, 0, 0, tzinfo=timezone.utc)
        snap.signature = signature
        snap.signing_key_id = signing_key_id
        return snap

    def test_201_generates_and_persists_bom(self, user_client: TestClient) -> None:
        """Returns 201 with generated BOM; auto_sign=false means no signature."""
        bom_dict: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "generated_at": "2026-03-13T00:00:00Z",
            "artifact_count": 1,
            "artifacts": [
                {"name": "skill-a", "type": "skill", "content_hash": "ccc", "metadata": {}}
            ],
        }
        persisted = self._make_persisted_snapshot()

        # BomGenerator and BomSerializer are imported inside the function body
        # via ``from skillmeat.core.bom.generator import BomGenerator, BomSerializer``.
        # BomSnapshot is imported at the top of bom.py, so patch it there.
        with (
            patch("skillmeat.core.bom.generator.BomGenerator") as MockGenerator,
            patch("skillmeat.core.bom.generator.BomSerializer") as MockSerializer,
            patch("skillmeat.api.routers.bom.BomSnapshot", return_value=persisted),
        ):
            MockGenerator.return_value.generate.return_value = bom_dict
            MockSerializer.return_value.to_json.return_value = json.dumps(bom_dict)
            user_client._mock_db.add = MagicMock()
            user_client._mock_db.commit = MagicMock()
            # db.refresh(snapshot) is called with our persisted mock — it's a no-op.
            user_client._mock_db.refresh = MagicMock()

            response = user_client.post(
                "/api/v1/bom/generate",
                json={"project_id": None, "auto_sign": False},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 99
        assert data["signed"] is False
        assert data["signature"] is None
        assert data["bom"]["artifact_count"] == 1

    def test_201_auto_sign_calls_sign_bom(self, user_client: TestClient) -> None:
        """When auto_sign=true and signing succeeds, snapshot is marked signed."""
        bom_dict: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "generated_at": "2026-03-13T00:00:00Z",
            "artifact_count": 0,
            "artifacts": [],
        }
        persisted = self._make_persisted_snapshot(
            signature="cafebabe", signing_key_id="key-fp"
        )

        sig_result = SimpleNamespace(
            signature_hex="cafebabe",
            key_id="key-fp",
            algorithm="Ed25519",
        )

        with (
            patch("skillmeat.core.bom.generator.BomGenerator") as MockGenerator,
            patch("skillmeat.core.bom.generator.BomSerializer") as MockSerializer,
            patch("skillmeat.api.routers.bom.BomSnapshot", return_value=persisted),
            patch("skillmeat.core.bom.signing.sign_bom", return_value=sig_result),
        ):
            MockGenerator.return_value.generate.return_value = bom_dict
            MockSerializer.return_value.to_json.return_value = json.dumps(bom_dict)
            user_client._mock_db.add = MagicMock()
            user_client._mock_db.commit = MagicMock()
            user_client._mock_db.refresh = MagicMock()

            response = user_client.post(
                "/api/v1/bom/generate",
                json={"auto_sign": True},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["signed"] is True
        assert data["signature"] == "cafebabe"
        assert data["signing_key_id"] == "key-fp"

    def test_auto_sign_failure_non_fatal(self, user_client: TestClient) -> None:
        """When signing fails the BOM is still persisted without a signature."""
        bom_dict: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "generated_at": "2026-03-13T00:00:00Z",
            "artifact_count": 0,
            "artifacts": [],
        }
        persisted = self._make_persisted_snapshot()

        with (
            patch("skillmeat.core.bom.generator.BomGenerator") as MockGenerator,
            patch("skillmeat.core.bom.generator.BomSerializer") as MockSerializer,
            patch("skillmeat.api.routers.bom.BomSnapshot", return_value=persisted),
            patch(
                "skillmeat.core.bom.signing.sign_bom",
                side_effect=RuntimeError("no key"),
            ),
        ):
            MockGenerator.return_value.generate.return_value = bom_dict
            MockSerializer.return_value.to_json.return_value = json.dumps(bom_dict)
            user_client._mock_db.add = MagicMock()
            user_client._mock_db.commit = MagicMock()
            user_client._mock_db.refresh = MagicMock()

            response = user_client.post(
                "/api/v1/bom/generate",
                json={"auto_sign": True},
            )

        # Should still succeed — signing failure is non-fatal.
        assert response.status_code == 201
        assert response.json()["signed"] is False

    def test_500_when_generator_raises(self, user_client: TestClient) -> None:
        """Returns 500 when BomGenerator.generate() raises an exception."""
        with patch("skillmeat.core.bom.generator.BomGenerator") as MockGenerator:
            MockGenerator.return_value.generate.side_effect = RuntimeError("db unavailable")

            response = user_client.post(
                "/api/v1/bom/generate",
                json={"auto_sign": False},
            )

        assert response.status_code == 500
        assert "BOM generation failed" in response.json()["detail"]


# =============================================================================
# POST /api/v1/bom/verify
# =============================================================================


class TestVerifyBom:
    """Tests for POST /api/v1/bom/verify."""

    _SIG_HEX = "a1b2c3d4" * 16  # 64-byte hex = valid Ed25519 sig length

    def test_200_valid_signature(self, user_client: TestClient) -> None:
        """Returns 200 with valid=true when signature verifies correctly."""
        snapshot = _make_snapshot(snap_id=5, signature=self._SIG_HEX)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        verify_result = SimpleNamespace(valid=True, error=None, key_id="key-fp")

        # verify_signature is imported inside the endpoint function body via
        # ``from skillmeat.core.bom.signing import verify_signature`` — patch
        # the function on the originating module.
        with patch("skillmeat.core.bom.signing.verify_signature", return_value=verify_result):
            response = user_client.post("/api/v1/bom/verify", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "valid" in data["details"].lower()
        assert data["snapshot_id"] == 5

    def test_200_invalid_signature(self, user_client: TestClient) -> None:
        """Returns 200 with valid=false when the signature does not verify."""
        snapshot = _make_snapshot(snap_id=5, signature=self._SIG_HEX)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        verify_result = SimpleNamespace(valid=False, error="bad signature", key_id=None)

        with patch("skillmeat.core.bom.signing.verify_signature", return_value=verify_result):
            response = user_client.post("/api/v1/bom/verify", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "bad signature" in data["details"]

    def test_404_when_no_snapshot(self, user_client: TestClient) -> None:
        """Returns 404 when no snapshot exists and no snapshot_id is provided."""
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.post("/api/v1/bom/verify", json={})

        assert response.status_code == 404

    def test_422_snapshot_has_no_signature(self, user_client: TestClient) -> None:
        """Returns 422 when the snapshot has no signature and none is supplied."""
        snapshot = _make_snapshot(snap_id=3, signature=None)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.post("/api/v1/bom/verify", json={})

        assert response.status_code == 422
        assert "No signature available" in response.json()["detail"]

    def test_422_invalid_hex_signature_in_request(self, user_client: TestClient) -> None:
        """Returns 422 when the supplied signature is not valid hex."""
        snapshot = _make_snapshot(snap_id=3, signature=None)
        user_client._mock_db.query.return_value = _MockQuery([snapshot])

        response = user_client.post(
            "/api/v1/bom/verify",
            json={"signature": "not-hex-data!"},
        )

        assert response.status_code == 422
        assert "not valid hex" in response.json()["detail"]

    def test_verify_with_explicit_snapshot_id(self, user_client: TestClient) -> None:
        """When snapshot_id is supplied, that specific snapshot is verified."""
        snapshot = _make_snapshot(snap_id=77, signature=self._SIG_HEX)

        # Simulate a query that returns the snapshot by id.
        mock_query = _MockQuery([snapshot])
        user_client._mock_db.query.return_value = mock_query

        verify_result = SimpleNamespace(valid=True, error=None, key_id=None)

        with patch("skillmeat.core.bom.signing.verify_signature", return_value=verify_result):
            response = user_client.post(
                "/api/v1/bom/verify",
                json={"snapshot_id": 77},
            )

        assert response.status_code == 200
        assert response.json()["snapshot_id"] == 77


# =============================================================================
# GET /api/v1/attestations
# =============================================================================


class TestListAttestations:
    """Tests for GET /api/v1/attestations."""

    def test_200_returns_empty_list_when_no_records(
        self, user_client: TestClient
    ) -> None:
        """Returns 200 with empty items list when no attestation records exist."""
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.get("/api/v1/attestations")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["page_info"]["has_next_page"] is False
        assert data["page_info"]["end_cursor"] is None

    def test_200_returns_records_for_caller(self, user_client: TestClient) -> None:
        """Returns attestation records scoped to the authenticated caller."""
        records = [_make_attestation(attest_id=i) for i in range(1, 4)]
        user_client._mock_db.query.return_value = _MockQuery(records)

        response = user_client.get("/api/v1/attestations")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_owner_scope_filter_user(self, user_client: TestClient) -> None:
        """owner_scope=user returns records scoped to user context."""
        records = [_make_attestation()]
        user_client._mock_db.query.return_value = _MockQuery(records)

        response = user_client.get("/api/v1/attestations?owner_scope=user")

        assert response.status_code == 200

    def test_owner_scope_invalid_returns_400(self, user_client: TestClient) -> None:
        """Returns 400 when an invalid owner_scope value is supplied."""
        response = user_client.get("/api/v1/attestations?owner_scope=invalid_scope")

        assert response.status_code == 400
        assert "Invalid owner_scope" in response.json()["detail"]

    def test_artifact_id_filter(self, user_client: TestClient) -> None:
        """artifact_id query parameter narrows results to that artifact."""
        records = [_make_attestation(artifact_id="command:my-cmd")]
        user_client._mock_db.query.return_value = _MockQuery(records)

        response = user_client.get("/api/v1/attestations?artifact_id=command:my-cmd")

        assert response.status_code == 200
        items = response.json()["items"]
        assert all(item["artifact_id"] == "command:my-cmd" for item in items)

    def test_pagination_cursor_encodes_last_id(self, user_client: TestClient) -> None:
        """end_cursor is the string ID of the last record when has_next_page is true."""
        # Create limit+1 records so has_next_page becomes True.
        records = [_make_attestation(attest_id=i) for i in range(1, 52)]
        # Default limit is 50; feed 51 records so the +1 probe triggers.
        user_client._mock_db.query.return_value = _MockQuery(records)

        response = user_client.get("/api/v1/attestations?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["page_info"]["has_next_page"] is True
        assert data["page_info"]["end_cursor"] is not None
        # The end_cursor is the id of the last record on the page (record 50).
        assert data["page_info"]["end_cursor"] == "50"

    def test_cursor_based_navigation(self, user_client: TestClient) -> None:
        """Passing cursor= returns records with id < cursor value (page 2)."""
        records = [_make_attestation(attest_id=i) for i in range(1, 4)]
        user_client._mock_db.query.return_value = _MockQuery(records)

        response = user_client.get("/api/v1/attestations?cursor=10")

        assert response.status_code == 200

    def test_invalid_cursor_returns_400(self, user_client: TestClient) -> None:
        """Returns 400 when the cursor value is not a valid integer."""
        response = user_client.get("/api/v1/attestations?cursor=notanint")

        assert response.status_code == 400
        assert "Invalid cursor" in response.json()["detail"]

    def test_cross_owner_records_not_visible(self, user_client: TestClient) -> None:
        """Records owned by a different user are not returned."""
        # DB query is filtered by owner — simulate an empty result for the caller.
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.get("/api/v1/attestations")

        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_enterprise_caller_uses_enterprise_owner_type(
        self, enterprise_client: TestClient
    ) -> None:
        """Enterprise auth context results in enterprise-scoped query."""
        records = [_make_attestation(owner_type="enterprise")]
        enterprise_client._mock_db.query.return_value = _MockQuery(records)

        response = enterprise_client.get("/api/v1/attestations")

        assert response.status_code == 200


# =============================================================================
# POST /api/v1/attestations
# =============================================================================


class TestCreateAttestation:
    """Tests for POST /api/v1/attestations."""

    def _payload(self, **overrides: Any) -> Dict[str, Any]:
        defaults: Dict[str, Any] = {
            "artifact_id": "skill:test-skill",
            "visibility": "private",
        }
        defaults.update(overrides)
        return defaults

    def test_201_creates_attestation(self, user_client: TestClient) -> None:
        """Returns 201 with the created attestation record."""
        artifact_row = MagicMock()
        artifact_row.id = "skill:test-skill"

        persisted = _make_attestation()

        user_client._mock_db.query.return_value = _MockQuery([artifact_row])
        user_client._mock_db.add = MagicMock()
        user_client._mock_db.commit = MagicMock()
        user_client._mock_db.refresh = MagicMock()

        with patch("skillmeat.api.routers.bom.AttestationRecord", return_value=persisted):
            response = user_client.post(
                "/api/v1/attestations",
                json=self._payload(),
            )

        assert response.status_code == 201
        data = response.json()
        assert data["artifact_id"] == "skill:test-skill"
        assert data["visibility"] == "private"

    def test_404_when_artifact_not_found(self, user_client: TestClient) -> None:
        """Returns 404 when the artifact_id does not exist in the database."""
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.post(
            "/api/v1/attestations",
            json=self._payload(artifact_id="skill:nonexistent"),
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_400_invalid_owner_scope(self, user_client: TestClient) -> None:
        """Returns 400 when owner_scope is not a valid value."""
        artifact_row = MagicMock()
        user_client._mock_db.query.return_value = _MockQuery([artifact_row])

        response = user_client.post(
            "/api/v1/attestations",
            json=self._payload(owner_scope="invalid"),
        )

        assert response.status_code == 400
        assert "Invalid owner_scope" in response.json()["detail"]

    def test_400_invalid_visibility(self, user_client: TestClient) -> None:
        """Returns 400 when visibility is not a valid value."""
        artifact_row = MagicMock()
        user_client._mock_db.query.return_value = _MockQuery([artifact_row])

        response = user_client.post(
            "/api/v1/attestations",
            json=self._payload(visibility="secret"),
        )

        assert response.status_code == 400
        assert "Invalid visibility" in response.json()["detail"]

    def test_roles_and_scopes_stored(self, user_client: TestClient) -> None:
        """Supplied roles and scopes are stored on the attestation record."""
        artifact_row = MagicMock()
        persisted = _make_attestation(
            roles=["team_admin"],
            scopes=["artifact:read"],
            visibility="team",
        )

        user_client._mock_db.query.return_value = _MockQuery([artifact_row])
        user_client._mock_db.add = MagicMock()
        user_client._mock_db.commit = MagicMock()
        user_client._mock_db.refresh = MagicMock()

        with patch("skillmeat.api.routers.bom.AttestationRecord", return_value=persisted):
            response = user_client.post(
                "/api/v1/attestations",
                json=self._payload(
                    roles=["team_admin"],
                    scopes=["artifact:read"],
                    visibility="team",
                ),
            )

        assert response.status_code == 201
        data = response.json()
        assert "team_admin" in data["roles"]
        assert "artifact:read" in data["scopes"]
        assert data["visibility"] == "team"

    def test_owner_scope_override_applies(self, user_client: TestClient) -> None:
        """owner_scope in request body overrides the caller's inferred owner_type."""
        artifact_row = MagicMock()
        persisted = _make_attestation(owner_type="team")

        user_client._mock_db.query.return_value = _MockQuery([artifact_row])
        user_client._mock_db.add = MagicMock()
        user_client._mock_db.commit = MagicMock()
        user_client._mock_db.refresh = MagicMock()

        with patch("skillmeat.api.routers.bom.AttestationRecord", return_value=persisted):
            response = user_client.post(
                "/api/v1/attestations",
                json=self._payload(owner_scope="team"),
            )

        assert response.status_code == 201
        assert response.json()["owner_type"] == "team"

    def test_enterprise_caller_infers_enterprise_owner_type(
        self, enterprise_client: TestClient
    ) -> None:
        """When tenant_id is set, owner_type defaults to 'enterprise'."""
        artifact_row = MagicMock()
        persisted = _make_attestation(owner_type="enterprise")

        enterprise_client._mock_db.query.return_value = _MockQuery([artifact_row])
        enterprise_client._mock_db.add = MagicMock()
        enterprise_client._mock_db.commit = MagicMock()
        enterprise_client._mock_db.refresh = MagicMock()

        with patch("skillmeat.api.routers.bom.AttestationRecord", return_value=persisted):
            response = enterprise_client.post(
                "/api/v1/attestations",
                json=self._payload(),
            )

        assert response.status_code == 201
        assert response.json()["owner_type"] == "enterprise"


# =============================================================================
# GET /api/v1/attestations/{id}
# =============================================================================


class TestGetAttestation:
    """Tests for GET /api/v1/attestations/{attestation_id}."""

    def test_200_returns_owned_record(self, user_client: TestClient) -> None:
        """Returns 200 with the attestation record when it belongs to the caller."""
        record = _make_attestation(attest_id=10)
        user_client._mock_db.query.return_value = _MockQuery([record])

        response = user_client.get("/api/v1/attestations/10")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "10"
        assert data["artifact_id"] == "skill:test-skill"

    def test_404_when_record_not_found(self, user_client: TestClient) -> None:
        """Returns 404 when the attestation record does not exist."""
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.get("/api/v1/attestations/9999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_404_cross_owner_returns_404_not_403(
        self, user_client: TestClient
    ) -> None:
        """Cross-owner records surface as 404 to prevent enumeration attacks."""
        # Simulate no record found for this caller's owner context.
        user_client._mock_db.query.return_value = _MockQuery([])

        response = user_client.get("/api/v1/attestations/42")

        # Must be 404 — never 403 — to prevent information leakage.
        assert response.status_code == 404

    def test_enterprise_caller_scoped_to_tenant(
        self, enterprise_client: TestClient
    ) -> None:
        """Enterprise caller can retrieve attestation records in their tenant scope."""
        record = _make_attestation(attest_id=20, owner_type="enterprise")
        enterprise_client._mock_db.query.return_value = _MockQuery([record])

        response = enterprise_client.get("/api/v1/attestations/20")

        assert response.status_code == 200
        assert response.json()["owner_type"] == "enterprise"

    def test_attestation_schema_fields_present(self, user_client: TestClient) -> None:
        """Response includes all expected AttestationSchema fields."""
        record = _make_attestation(
            attest_id=5,
            roles=["viewer"],
            scopes=["artifact:read"],
            visibility="public",
        )
        user_client._mock_db.query.return_value = _MockQuery([record])

        response = user_client.get("/api/v1/attestations/5")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "artifact_id" in data
        assert "owner_type" in data
        assert "owner_id" in data
        assert "roles" in data
        assert "scopes" in data
        assert "visibility" in data
        assert "created_at" in data
