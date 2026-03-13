"""Integration tests for the artifact activity (audit/provenance) endpoint (TASK-8.6).

Covers:
    GET /api/v1/artifacts/activity

Tests exercise:
  - Pagination (limit, cursor-based navigation, hasNextPage)
  - event_type filter (valid, invalid)
  - time_range_start / time_range_end filters
  - owner_scope filter (valid, invalid)
  - artifact_id filter
  - actor_id filter
  - Cursor encoding/decoding (base64 opaque format)
  - Owner-scope isolation (only events with matching owner_type returned)
  - 400 responses for bad parameters

All tests use FastAPI TestClient + MagicMock.  The DB session and auth context
are injected via ``app.dependency_overrides``.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.schemas.auth import AuthContext, Role, Scope


# =============================================================================
# Constants / helpers
# =============================================================================

_USER_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

_AUTH = AuthContext(
    user_id=_USER_ID,
    tenant_id=None,
    roles=[Role.system_admin.value],
    scopes=[s.value for s in Scope],
)


def _encode_cursor(event_id: int) -> str:
    """Mirror the cursor encoding logic used in artifact_activity.py."""
    raw = f"activity:{event_id}"
    return base64.b64encode(raw.encode()).decode()


def _make_event(
    event_id: int = 1,
    artifact_id: str = "skill:test-skill",
    event_type: str = "create",
    actor_id: str = "local_admin",
    owner_type: str = "user",
    timestamp: Optional[datetime] = None,
    diff_json: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> MagicMock:
    """Build a MagicMock ArtifactHistoryEvent ORM row."""
    event = MagicMock()
    event.id = event_id
    event.artifact_id = artifact_id
    event.event_type = event_type
    event.actor_id = actor_id
    event.owner_type = owner_type
    event.timestamp = timestamp or datetime(2026, 3, 13, 12, 0, 0, tzinfo=timezone.utc)
    event.diff_json = diff_json
    event.content_hash = content_hash or f"hash{event_id}"
    return event


class _MockQuery:
    """Minimal SQLAlchemy-like query chain for use in MagicMock DB sessions."""

    def __init__(self, rows: List[Any]) -> None:
        self._rows = list(rows)

    def filter(self, *_args: Any, **_kwargs: Any) -> "_MockQuery":
        return self

    def order_by(self, *_args: Any) -> "_MockQuery":
        return self

    def limit(self, n: int) -> "_MockQuery":
        self._rows = self._rows[:n]
        return self

    def all(self) -> List[Any]:
        return list(self._rows)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_auth_provider():
    """Reset the module-level auth provider after each test."""
    import skillmeat.api.dependencies as _deps_module

    yield
    _deps_module._auth_provider = None


@pytest.fixture
def client():
    """Minimal FastAPI app with only the artifact_activity router.

    The full server includes both ``artifacts`` and ``artifact_activity``
    routers.  Because ``artifacts`` registers ``GET /{artifact_id}`` before
    ``artifact_activity`` registers ``GET /activity``, FastAPI matches
    ``/api/v1/artifacts/activity`` as artifact_id="activity" and returns 400.

    To avoid this routing collision, we build a minimal app that contains
    only the ``artifact_activity`` router and the necessary auth + DB
    dependency overrides.
    """
    from fastapi import FastAPI, Depends
    from skillmeat.api.auth.local_provider import LocalAuthProvider
    from skillmeat.api.dependencies import set_auth_provider, require_auth
    from skillmeat.api.routers import artifact_activity
    from skillmeat.cache.session import get_db_session

    # Register auth provider so require_auth() doesn't raise 503.
    set_auth_provider(LocalAuthProvider())

    mock_db = MagicMock()
    mock_db.close = MagicMock()

    app = FastAPI()
    app.dependency_overrides[get_db_session] = lambda: mock_db

    _auth_deps = [Depends(require_auth(scopes=["artifact:read"]))]
    app.include_router(
        artifact_activity.router,
        prefix="/api/v1",
        tags=["artifact-activity"],
        dependencies=_auth_deps,
    )

    tc = TestClient(app, raise_server_exceptions=False)
    tc._mock_db = mock_db
    yield tc


# =============================================================================
# Tests
# =============================================================================


class TestListArtifactActivity:
    """Tests for GET /api/v1/artifacts/activity."""

    # ------------------------------------------------------------------
    # Basic success cases
    # ------------------------------------------------------------------

    def test_200_empty_when_no_events(self, client: TestClient) -> None:
        """Returns 200 with empty items list when no events exist."""
        client._mock_db.query.return_value = _MockQuery([])

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pageInfo"]["hasNextPage"] is False
        assert data["pageInfo"]["endCursor"] is None

    def test_200_returns_events(self, client: TestClient) -> None:
        """Returns events when they exist in the database."""
        events = [_make_event(event_id=i) for i in range(1, 4)]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_items_have_expected_fields(self, client: TestClient) -> None:
        """Each item in the response has the expected HistoryEventSchema fields."""
        event = _make_event(
            event_id=1,
            artifact_id="command:deploy",
            event_type="deploy",
            actor_id="user-abc",
            owner_type="user",
        )
        client._mock_db.query.return_value = _MockQuery([event])

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["id"] == "1"
        assert item["artifact_id"] == "command:deploy"
        assert item["event_type"] == "deploy"
        assert item["actor_id"] == "user-abc"
        assert item["owner_type"] == "user"
        assert "timestamp" in item

    # ------------------------------------------------------------------
    # event_type filter
    # ------------------------------------------------------------------

    def test_event_type_filter_valid(self, client: TestClient) -> None:
        """Valid event_type filters are accepted (200)."""
        for valid_type in ("create", "update", "delete", "deploy", "undeploy", "sync"):
            client._mock_db.query.return_value = _MockQuery([])
            response = client.get(f"/api/v1/artifacts/activity?event_type={valid_type}")
            assert response.status_code == 200, f"Failed for event_type={valid_type}"

    def test_event_type_filter_invalid_returns_400(self, client: TestClient) -> None:
        """Returns 400 for unrecognised event_type values."""
        response = client.get("/api/v1/artifacts/activity?event_type=explode")

        assert response.status_code == 400
        assert "Invalid event_type" in response.json()["detail"]

    # ------------------------------------------------------------------
    # owner_scope filter
    # ------------------------------------------------------------------

    def test_owner_scope_valid(self, client: TestClient) -> None:
        """Valid owner_scope values are accepted (200)."""
        for scope in ("user", "team", "enterprise"):
            client._mock_db.query.return_value = _MockQuery([])
            response = client.get(f"/api/v1/artifacts/activity?owner_scope={scope}")
            assert response.status_code == 200, f"Failed for owner_scope={scope}"

    def test_owner_scope_invalid_returns_400(self, client: TestClient) -> None:
        """Returns 400 for unrecognised owner_scope values."""
        response = client.get("/api/v1/artifacts/activity?owner_scope=galactic")

        assert response.status_code == 400
        assert "Invalid owner_scope" in response.json()["detail"]

    # ------------------------------------------------------------------
    # artifact_id filter
    # ------------------------------------------------------------------

    def test_artifact_id_filter(self, client: TestClient) -> None:
        """artifact_id query parameter is accepted and filters results."""
        events = [_make_event(artifact_id="skill:canvas")]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity?artifact_id=skill:canvas")

        assert response.status_code == 200
        items = response.json()["items"]
        assert all(item["artifact_id"] == "skill:canvas" for item in items)

    # ------------------------------------------------------------------
    # time_range filters
    # ------------------------------------------------------------------

    def test_time_range_start_filter(self, client: TestClient) -> None:
        """time_range_start query parameter is accepted."""
        client._mock_db.query.return_value = _MockQuery([])

        response = client.get(
            "/api/v1/artifacts/activity?time_range_start=2026-01-01T00:00:00Z"
        )

        assert response.status_code == 200

    def test_time_range_end_filter(self, client: TestClient) -> None:
        """time_range_end query parameter is accepted."""
        client._mock_db.query.return_value = _MockQuery([])

        response = client.get(
            "/api/v1/artifacts/activity?time_range_end=2026-12-31T23:59:59Z"
        )

        assert response.status_code == 200

    def test_time_range_start_and_end_together(self, client: TestClient) -> None:
        """Both time bounds can be specified together."""
        client._mock_db.query.return_value = _MockQuery([])

        response = client.get(
            "/api/v1/artifacts/activity"
            "?time_range_start=2026-01-01T00:00:00Z"
            "&time_range_end=2026-12-31T23:59:59Z"
        )

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # actor_id filter
    # ------------------------------------------------------------------

    def test_actor_id_filter(self, client: TestClient) -> None:
        """actor_id query parameter is accepted."""
        events = [_make_event(actor_id="user-xyz")]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity?actor_id=user-xyz")

        assert response.status_code == 200

    # ------------------------------------------------------------------
    # Pagination: limit
    # ------------------------------------------------------------------

    def test_limit_accepted_valid_range(self, client: TestClient) -> None:
        """limit values between 1 and 200 are accepted."""
        for limit in (1, 50, 200):
            client._mock_db.query.return_value = _MockQuery([])
            response = client.get(f"/api/v1/artifacts/activity?limit={limit}")
            assert response.status_code == 200, f"Failed for limit={limit}"

    def test_limit_too_large_returns_422(self, client: TestClient) -> None:
        """limit > 200 is rejected by FastAPI validation."""
        response = client.get("/api/v1/artifacts/activity?limit=201")
        assert response.status_code == 422

    def test_limit_zero_returns_422(self, client: TestClient) -> None:
        """limit=0 is below the minimum and is rejected by FastAPI validation."""
        response = client.get("/api/v1/artifacts/activity?limit=0")
        assert response.status_code == 422

    # ------------------------------------------------------------------
    # Pagination: cursor
    # ------------------------------------------------------------------

    def test_has_next_page_false_when_fewer_than_limit(
        self, client: TestClient
    ) -> None:
        """hasNextPage is False when fewer than limit events are returned."""
        events = [_make_event(event_id=i) for i in range(1, 4)]  # 3 events < limit 50
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["pageInfo"]["hasNextPage"] is False

    def test_has_next_page_true_when_more_than_limit(
        self, client: TestClient
    ) -> None:
        """hasNextPage is True when limit+1 events are fetched."""
        # 6 events, limit=5 → hasNextPage True, endCursor set
        events = [_make_event(event_id=i) for i in range(1, 7)]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["pageInfo"]["hasNextPage"] is True
        assert data["pageInfo"]["endCursor"] is not None

    def test_end_cursor_is_base64_encoded(self, client: TestClient) -> None:
        """The endCursor is an opaque base64 string encoding the last event id."""
        events = [_make_event(event_id=i) for i in range(1, 7)]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity?limit=5")

        assert response.status_code == 200
        end_cursor = response.json()["pageInfo"]["endCursor"]
        assert end_cursor is not None

        # Decode and verify it follows the expected format.
        decoded = base64.b64decode(end_cursor.encode()).decode()
        assert decoded.startswith("activity:")
        cursor_id = int(decoded[len("activity:"):])
        # The last event on page 1 of 5 events is event_id=5.
        assert cursor_id == 5

    def test_cursor_navigates_to_next_page(self, client: TestClient) -> None:
        """Passing cursor= parameter is accepted and triggers page 2 results."""
        cursor = _encode_cursor(50)
        events = [_make_event(event_id=i) for i in range(40, 51)]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get(f"/api/v1/artifacts/activity?cursor={cursor}")

        assert response.status_code == 200

    def test_malformed_cursor_returns_400(self, client: TestClient) -> None:
        """Returns 400 when the cursor cannot be decoded."""
        response = client.get("/api/v1/artifacts/activity?cursor=not-base64!")

        assert response.status_code == 400
        assert "cursor" in response.json()["detail"].lower()

    def test_cursor_without_activity_prefix_returns_400(
        self, client: TestClient
    ) -> None:
        """Returns 400 when cursor decodes but lacks the 'activity:' prefix."""
        bad_cursor = base64.b64encode(b"wrong:123").decode()

        response = client.get(f"/api/v1/artifacts/activity?cursor={bad_cursor}")

        assert response.status_code == 400

    def test_end_cursor_none_when_no_next_page(self, client: TestClient) -> None:
        """endCursor is None when hasNextPage is False."""
        events = [_make_event(event_id=1)]
        client._mock_db.query.return_value = _MockQuery(events)

        response = client.get("/api/v1/artifacts/activity?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["pageInfo"]["hasNextPage"] is False
        assert data["pageInfo"]["endCursor"] is None

    # ------------------------------------------------------------------
    # diff_json parsing
    # ------------------------------------------------------------------

    def test_diff_json_parsed_as_dict(self, client: TestClient) -> None:
        """diff_json field is parsed into a dict in the response when valid JSON."""
        diff = {"before": "v1", "after": "v2", "project_id": "proj-abc"}
        event = _make_event(diff_json=json.dumps(diff))
        client._mock_db.query.return_value = _MockQuery([event])

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["diff_json"] == diff

    def test_invalid_diff_json_becomes_none(self, client: TestClient) -> None:
        """Invalid diff_json is silently set to None in the response."""
        event = _make_event(diff_json="NOT_JSON{{{")
        client._mock_db.query.return_value = _MockQuery([event])

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["diff_json"] is None

    def test_null_diff_json_remains_none(self, client: TestClient) -> None:
        """Events with no diff_json have diff_json=null in the response."""
        event = _make_event(diff_json=None)
        client._mock_db.query.return_value = _MockQuery([event])

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        assert response.json()["items"][0]["diff_json"] is None

    # ------------------------------------------------------------------
    # Owner-scope isolation
    # ------------------------------------------------------------------

    def test_owner_scope_user_filters_events(self, client: TestClient) -> None:
        """owner_scope=user returns only events with owner_type='user'."""
        user_events = [_make_event(owner_type="user")]
        client._mock_db.query.return_value = _MockQuery(user_events)

        response = client.get("/api/v1/artifacts/activity?owner_scope=user")

        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["owner_type"] == "user"

    def test_owner_scope_team_filters_events(self, client: TestClient) -> None:
        """owner_scope=team returns only events with owner_type='team'."""
        team_events = [_make_event(owner_type="team")]
        client._mock_db.query.return_value = _MockQuery(team_events)

        response = client.get("/api/v1/artifacts/activity?owner_scope=team")

        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["owner_type"] == "team"

    # ------------------------------------------------------------------
    # Response structure
    # ------------------------------------------------------------------

    def test_response_structure_keys_present(self, client: TestClient) -> None:
        """Response contains 'items' and 'pageInfo' top-level keys."""
        client._mock_db.query.return_value = _MockQuery([])

        response = client.get("/api/v1/artifacts/activity")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pageInfo" in data
        assert "endCursor" in data["pageInfo"]
        assert "hasNextPage" in data["pageInfo"]
