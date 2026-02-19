"""Integration tests for GET /api/v1/artifacts/{artifact_id}/associations.

Tests cover:
- 200 with correct parents/children for a valid artifact
- 404 for an unknown artifact
- Query param filtering: include_parents=false, include_children=false
- Empty associations return empty lists (not 404)
- relationship_type filter narrows results
- Response schema shape is correct
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
    create_tables,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database for association tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture()
def db_engine(temp_db):
    """Engine with all ORM tables created (bypasses Alembic)."""
    engine = create_db_engine(temp_db)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    """Return a live SQLAlchemy session bound to the temp database."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded_db(db_session, temp_db) -> Dict[str, Any]:
    """Seed the DB with one collection, one composite artifact and two child artifacts.

    Graph::

        composite:my-plugin  (CompositeArtifact)
            |-- skill:canvas      (child, relationship_type="contains")
            |-- command:build     (child, relationship_type="requires")

    Returns a dict with ids and UUIDs for assertions.
    """
    col_id = _make_uuid()
    proj_id = "proj-assoc-test"
    composite_id = "composite:my-plugin"

    canvas_uuid = _make_uuid()
    build_uuid = _make_uuid()

    # Project row (required by Artifact FK)
    db_session.add(
        Project(
            id=proj_id,
            name="Test Project",
            path="/tmp/assoc-test-project",
            status="active",
        )
    )

    # Collection row (used by CompositeMembership.collection_id)
    db_session.add(
        Collection(
            id=col_id,
            name="default",
        )
    )

    # Child artifact rows
    db_session.add(
        Artifact(
            id="skill:canvas",
            uuid=canvas_uuid,
            name="canvas",
            type="skill",
            project_id=proj_id,
        )
    )
    db_session.add(
        Artifact(
            id="command:build",
            uuid=build_uuid,
            name="build",
            type="command",
            project_id=proj_id,
        )
    )

    # Composite artifact row
    db_session.add(
        CompositeArtifact(
            id=composite_id,
            collection_id=col_id,
            composite_type="plugin",
            display_name="My Plugin",
        )
    )

    # Membership edges
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=canvas_uuid,
            relationship_type="contains",
            created_at=_utcnow(),
        )
    )
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=build_uuid,
            relationship_type="requires",
            created_at=_utcnow(),
        )
    )

    db_session.commit()

    return {
        "col_id": col_id,
        "proj_id": proj_id,
        "composite_id": composite_id,
        "canvas_uuid": canvas_uuid,
        "build_uuid": build_uuid,
    }


def _make_mock_collection_mgr(
    collection_name: str,
    artifact_id: str,
    artifact_exists: bool = True,
):
    """Build a minimal CollectionManager mock that satisfies the endpoint's calls."""
    artifact_type_str, artifact_name = artifact_id.split(":", 1)

    mock_artifact = MagicMock()
    mock_artifact.name = artifact_name
    mock_artifact.type = artifact_type_str

    mock_collection = MagicMock()
    if artifact_exists:
        mock_collection.find_artifact.return_value = mock_artifact
    else:
        mock_collection.find_artifact.return_value = None

    mock_mgr = MagicMock()
    mock_mgr.get_active_collection_name.return_value = collection_name
    mock_mgr.list_collections.return_value = [collection_name]
    mock_mgr.load_collection.return_value = mock_collection

    return mock_mgr


@pytest.fixture()
def app(temp_db, seeded_db):
    """FastAPI test app with dependency overrides pointing at the seeded DB."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token

    settings = APISettings(
        env=Environment.TESTING,
        api_key_enabled=False,
    )
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[verify_token] = lambda: "test-token"

    # Store temp_db path on app state for test helpers
    application.state._test_temp_db = temp_db
    application.state._test_col_id = seeded_db["col_id"]

    return application


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestGetArtifactAssociations:
    """Tests for GET /api/v1/artifacts/{artifact_id}/associations."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _override_collection_mgr(
        application, collection_name, artifact_id, exists=True
    ):
        from skillmeat.api.dependencies import get_collection_manager

        mock_mgr = _make_mock_collection_mgr(collection_name, artifact_id, exists)
        application.dependency_overrides[get_collection_manager] = lambda: mock_mgr
        return mock_mgr

    @staticmethod
    def _make_patches(application):
        """Return two patch context managers for the repo and get_session.

        Patches:
        1. ``skillmeat.api.routers.artifacts.CompositeMembershipRepository``
           (the module-level import used by the endpoint) — replaced with a
           factory that returns a real repo pointing at the temp DB.
        2. ``skillmeat.api.routers.artifacts.get_session`` — replaced so the
           Collection lookup resolves against the seeded temp DB.
        """
        temp_db = application.state._test_temp_db

        from skillmeat.cache.composite_repository import CompositeMembershipRepository
        from sqlalchemy.orm import sessionmaker

        # Real repo bound to the temp DB (no Alembic migration needed — tables
        # already exist from the db_engine fixture).
        with patch("skillmeat.cache.migrations.run_migrations"):
            real_repo = CompositeMembershipRepository(db_path=temp_db)

        # Session that can resolve Collection rows from the temp DB
        engine = create_db_engine(temp_db)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        def _get_session_factory():
            return SessionLocal()

        from unittest.mock import patch as _patch

        p1 = _patch(
            "skillmeat.api.routers.artifacts.CompositeMembershipRepository",
            return_value=real_repo,
        )
        p2 = _patch(
            "skillmeat.api.routers.artifacts.get_session",
            side_effect=_get_session_factory,
        )
        return p1, p2

    def _run_request(self, app, artifact_id, params=None):
        """Helper: apply patches and send GET request."""
        p1, p2 = self._make_patches(app)
        with p1, p2:
            with TestClient(app) as client:
                return client.get(
                    f"/api/v1/artifacts/{artifact_id}/associations",
                    params=params or {},
                )

    # ------------------------------------------------------------------
    # 200 — composite artifact (has children)
    # ------------------------------------------------------------------

    def test_composite_returns_children(self, app, seeded_db):
        """Composite artifact endpoint returns its child associations."""
        self._override_collection_mgr(app, "default", "composite:my-plugin")

        resp = self._run_request(app, "composite:my-plugin")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["artifact_id"] == "composite:my-plugin"
        # The composite has no parents in seeded data
        assert body["parents"] == []
        # Two children were seeded
        assert len(body["children"]) == 2
        child_ids = {c["artifact_id"] for c in body["children"]}
        assert "skill:canvas" in child_ids
        assert "command:build" in child_ids

    # ------------------------------------------------------------------
    # 200 — child artifact (has parents)
    # ------------------------------------------------------------------

    def test_child_artifact_returns_parents(self, app, seeded_db):
        """Child artifact endpoint returns composite parents."""
        self._override_collection_mgr(app, "default", "skill:canvas")

        resp = self._run_request(app, "skill:canvas")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["artifact_id"] == "skill:canvas"
        assert len(body["parents"]) == 1
        assert body["parents"][0]["artifact_id"] == "composite:my-plugin"
        assert body["parents"][0]["artifact_type"] == "composite"
        assert body["parents"][0]["artifact_name"] == "my-plugin"
        # skill:canvas has no children of its own
        assert body["children"] == []

    # ------------------------------------------------------------------
    # 200 — empty associations (not 404)
    # ------------------------------------------------------------------

    def test_artifact_with_no_associations_returns_empty_lists(self, app, seeded_db):
        """An artifact that exists but has no memberships returns empty lists, not 404."""
        # skill:orphan has neither parents nor children
        self._override_collection_mgr(app, "default", "skill:orphan")

        # Add the orphan artifact to the DB so the repo doesn't find it
        # (the endpoint only checks the FS via mock; the repo returns empty lists)
        resp = self._run_request(app, "skill:orphan")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["parents"] == []
        assert body["children"] == []

    # ------------------------------------------------------------------
    # 404 — artifact not found
    # ------------------------------------------------------------------

    def test_unknown_artifact_returns_404(self, app, seeded_db):
        """A request for a non-existent artifact returns 404."""
        self._override_collection_mgr(
            app, "default", "skill:does-not-exist", exists=False
        )

        resp = self._run_request(app, "skill:does-not-exist")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    # ------------------------------------------------------------------
    # Query param: include_parents=false
    # ------------------------------------------------------------------

    def test_include_parents_false_omits_parents(self, app, seeded_db):
        """include_parents=false returns empty parents list."""
        self._override_collection_mgr(app, "default", "skill:canvas")

        resp = self._run_request(
            app, "skill:canvas", params={"include_parents": "false"}
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["parents"] == []

    # ------------------------------------------------------------------
    # Query param: include_children=false
    # ------------------------------------------------------------------

    def test_include_children_false_omits_children(self, app, seeded_db):
        """include_children=false returns empty children list."""
        self._override_collection_mgr(app, "default", "composite:my-plugin")

        resp = self._run_request(
            app, "composite:my-plugin", params={"include_children": "false"}
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["children"] == []

    # ------------------------------------------------------------------
    # Query param: relationship_type filter
    # ------------------------------------------------------------------

    def test_relationship_type_filter_narrows_children(self, app, seeded_db):
        """relationship_type=contains only returns 'contains' edges."""
        self._override_collection_mgr(app, "default", "composite:my-plugin")

        resp = self._run_request(
            app,
            "composite:my-plugin",
            params={"relationship_type": "contains"},
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        # Only "skill:canvas" has relationship_type="contains"
        assert len(body["children"]) == 1
        assert body["children"][0]["artifact_id"] == "skill:canvas"
        assert body["children"][0]["relationship_type"] == "contains"

    def test_relationship_type_filter_no_match_returns_empty(self, app, seeded_db):
        """relationship_type with no matching edges returns empty lists."""
        self._override_collection_mgr(app, "default", "composite:my-plugin")

        resp = self._run_request(
            app,
            "composite:my-plugin",
            params={"relationship_type": "nonexistent-type"},
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["parents"] == []
        assert body["children"] == []

    # ------------------------------------------------------------------
    # 400 — invalid artifact ID format
    # ------------------------------------------------------------------

    def test_invalid_artifact_id_format_returns_400(self, app, seeded_db):
        """An artifact_id without ':' separator returns 400."""
        from skillmeat.api.dependencies import get_collection_manager

        mock_mgr = MagicMock()
        mock_mgr.get_active_collection_name.return_value = "default"
        app.dependency_overrides[get_collection_manager] = lambda: mock_mgr

        resp = self._run_request(app, "badformat")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # ------------------------------------------------------------------
    # Response schema shape
    # ------------------------------------------------------------------

    def test_response_schema_shape(self, app, seeded_db):
        """Response body must contain artifact_id, parents, and children keys."""
        self._override_collection_mgr(app, "default", "composite:my-plugin")

        resp = self._run_request(app, "composite:my-plugin")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "artifact_id" in body
        assert "parents" in body
        assert "children" in body

        # Each association item must have required fields
        for item in body["children"]:
            assert "artifact_id" in item
            assert "artifact_name" in item
            assert "artifact_type" in item
            assert "relationship_type" in item
            assert "created_at" in item
