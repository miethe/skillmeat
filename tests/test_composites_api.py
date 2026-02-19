"""Integration tests for composite artifact CRUD API endpoints.

Covers all 8 endpoints under ``/api/v1/composites``:

    GET  /composites                           - list_composites
    POST /composites                           - create_composite
    GET  /composites/{composite_id}            - get_composite
    PUT  /composites/{composite_id}            - update_composite
    DELETE /composites/{composite_id}          - delete_composite
    POST /composites/{composite_id}/members    - add_composite_member
    DELETE /composites/{composite_id}/members/{member_uuid} - remove_composite_member
    PATCH /composites/{composite_id}/members   - reorder_composite_members

Test strategy
-------------
Each test spins up a real in-memory (temp-file) SQLite DB with all ORM tables
created via ``Base.metadata.create_all``.  The ``CompositeService`` and
``CompositeMembershipRepository`` are constructed with that temp DB path, then
monkey-patched into the router so no Alembic migrations are required.

Fixtures mirror the pattern established in ``test_associations_api.py`` and
``test_api_deployment_profiles.py``.
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
from sqlalchemy.orm import sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.composite_repository import CompositeMembershipRepository
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
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
    """Temporary SQLite database file for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture()
def db_engine(temp_db: str):
    """Engine with all ORM tables created (bypasses Alembic)."""
    engine = create_db_engine(temp_db)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine):
    """Return a live SQLAlchemy session bound to the temp database."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def seeded_db(db_session, temp_db: str) -> Dict[str, Any]:
    """Seed a collection, two child artifacts, and one composite with memberships.

    Graph::

        composite:test-plugin  (CompositeArtifact, collection_id=col_id)
            |-- skill:canvas     (child, relationship_type="contains", position=0)
            |-- command:build    (child, relationship_type="requires",  position=1)

    Returns a dict of identifiers and UUIDs for use in assertions.
    """
    col_id = "col-test-001"
    proj_id = "proj-composite-test"
    composite_id = "composite:test-plugin"

    canvas_uuid = _make_uuid()
    build_uuid = _make_uuid()

    # Project row (required FK for Artifact)
    db_session.add(
        Project(
            id=proj_id,
            name="Composite Test Project",
            path="/tmp/composite-test-project",
            status="active",
        )
    )

    # Collection row (referenced by CompositeMembership.collection_id)
    db_session.add(
        Collection(
            id=col_id,
            name="default",
        )
    )

    # Child artifacts
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
            display_name="Test Plugin",
            description="A test composite plugin.",
        )
    )

    # Membership edges
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=canvas_uuid,
            relationship_type="contains",
            position=0,
            created_at=_utcnow(),
        )
    )
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=build_uuid,
            relationship_type="requires",
            position=1,
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


@pytest.fixture()
def composite_repo(temp_db: str) -> CompositeMembershipRepository:
    """CompositeMembershipRepository wired to the temp database.

    Patches ``run_migrations`` to a no-op — tables already exist from
    ``db_engine`` / ``seeded_db`` fixtures.
    """
    with patch("skillmeat.cache.migrations.run_migrations"):
        repo = CompositeMembershipRepository(db_path=temp_db)
    return repo


@pytest.fixture()
def app(temp_db: str, db_engine, seeded_db: Dict[str, Any]):
    """FastAPI test app with composites router wired to the seeded temp DB.

    The ``CompositeService`` constructed in each router endpoint is monkey-
    patched at the module level so it uses the same temp DB as the seeded
    fixtures.
    """
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token
    from skillmeat.core.services.composite_service import CompositeService

    settings = APISettings(
        env=Environment.TESTING,
        api_key_enabled=False,
    )
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[verify_token] = lambda: "test-token"

    # Store references for use inside test helpers
    application.state._test_temp_db = temp_db
    application.state._test_seeded = seeded_db

    return application


# ---------------------------------------------------------------------------
# Context manager: patch CompositeService and CompositeMembershipRepository
# ---------------------------------------------------------------------------


def _patched_client(application) -> TestClient:
    """Return a TestClient with service/repo patches applied.

    Patches ``CompositeService`` at the composites router module level and
    ``CompositeMembershipRepository`` at the cache module level (the
    remove-member endpoint imports it locally from there).  Both are
    constructed pointing at the temp database stored on ``application.state``.
    """
    temp_db = application.state._test_temp_db

    with patch("skillmeat.cache.migrations.run_migrations"):
        from skillmeat.core.services.composite_service import CompositeService
        from skillmeat.cache.composite_repository import CompositeMembershipRepository

        real_svc = CompositeService(db_path=temp_db)
        real_repo = CompositeMembershipRepository(db_path=temp_db)

    svc_patch = patch(
        "skillmeat.api.routers.composites.CompositeService",
        return_value=real_svc,
    )
    # remove_composite_member does a local import; patch at the source module
    repo_patch = patch(
        "skillmeat.cache.composite_repository.CompositeMembershipRepository",
        return_value=real_repo,
    )

    # Apply both patches and enter TestClient context
    p1 = svc_patch.start()
    p2 = repo_patch.start()
    client = TestClient(application)
    client.__enter__()

    # Attach cleanup so teardown works correctly
    client._cleanup_patches = (svc_patch, repo_patch)
    return client


def _stop_client(client: TestClient) -> None:
    client.__exit__(None, None, None)
    for p in client._cleanup_patches:
        p.stop()


# ---------------------------------------------------------------------------
# List composites  GET /api/v1/composites
# ---------------------------------------------------------------------------


class TestListComposites:
    """Tests for GET /api/v1/composites."""

    def test_list_returns_seeded_composite(self, app, seeded_db):
        """Returns the composite inserted by seeded_db."""
        client = _patched_client(app)
        try:
            resp = client.get(
                "/api/v1/composites",
                params={"collection_id": seeded_db["col_id"]},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "items" in body
        assert body["total"] == 1
        assert body["items"][0]["id"] == seeded_db["composite_id"]

    def test_list_empty_for_unknown_collection(self, app, seeded_db):
        """Returns empty list for a collection_id with no composites."""
        client = _patched_client(app)
        try:
            resp = client.get(
                "/api/v1/composites",
                params={"collection_id": "col-does-not-exist"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_missing_collection_id_returns_422(self, app, seeded_db):
        """collection_id is required; omitting it returns 422."""
        client = _patched_client(app)
        try:
            resp = client.get("/api/v1/composites")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_response_includes_member_count(self, app, seeded_db):
        """Listed composite has correct member_count."""
        client = _patched_client(app)
        try:
            resp = client.get(
                "/api/v1/composites",
                params={"collection_id": seeded_db["col_id"]},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        item = resp.json()["items"][0]
        assert item["member_count"] == 2


# ---------------------------------------------------------------------------
# Create composite  POST /api/v1/composites
# ---------------------------------------------------------------------------


class TestCreateComposite:
    """Tests for POST /api/v1/composites."""

    def test_create_happy_path_returns_201(self, app, seeded_db):
        """Creating a valid composite returns 201 with the new record."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": "composite:new-plugin",
                    "collection_id": seeded_db["col_id"],
                    "composite_type": "plugin",
                    "display_name": "New Plugin",
                    "description": "Brand new composite.",
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["id"] == "composite:new-plugin"
        assert body["collection_id"] == seeded_db["col_id"]
        assert body["composite_type"] == "plugin"
        assert body["display_name"] == "New Plugin"
        assert body["member_count"] == 0

    def test_create_with_initial_members_resolves_and_links(self, app, seeded_db):
        """Creating a composite with initial_members links child artifacts."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": "composite:with-members",
                    "collection_id": seeded_db["col_id"],
                    "initial_members": ["skill:canvas", "command:build"],
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["member_count"] == 2
        child_uuids = {m["child_artifact_uuid"] for m in body["memberships"]}
        assert seeded_db["canvas_uuid"] in child_uuids
        assert seeded_db["build_uuid"] in child_uuids

    def test_create_missing_composite_id_returns_422(self, app, seeded_db):
        """Omitting composite_id returns 422 Unprocessable Entity."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={"collection_id": seeded_db["col_id"]},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_invalid_composite_id_format_returns_422(self, app, seeded_db):
        """composite_id must start with 'composite:'; other prefixes return 422."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": "skill:not-a-composite",
                    "collection_id": seeded_db["col_id"],
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_duplicate_id_returns_409(self, app, seeded_db):
        """Creating a composite with an already-existing id returns 409 Conflict."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": seeded_db["composite_id"],
                    "collection_id": seeded_db["col_id"],
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in resp.json()["detail"]

    def test_create_with_invalid_member_artifact_returns_400(self, app, seeded_db):
        """Referencing an artifact not in cache returns 400 Bad Request."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": "composite:bad-members",
                    "collection_id": seeded_db["col_id"],
                    "initial_members": ["skill:does-not-exist"],
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "skill:does-not-exist" in resp.json()["detail"]

    def test_create_stack_type(self, app, seeded_db):
        """composite_type='stack' is accepted and stored."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": "composite:my-stack",
                    "collection_id": seeded_db["col_id"],
                    "composite_type": "stack",
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["composite_type"] == "stack"

    def test_create_suite_type(self, app, seeded_db):
        """composite_type='suite' is accepted and stored."""
        client = _patched_client(app)
        try:
            resp = client.post(
                "/api/v1/composites",
                json={
                    "composite_id": "composite:my-suite",
                    "collection_id": seeded_db["col_id"],
                    "composite_type": "suite",
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["composite_type"] == "suite"


# ---------------------------------------------------------------------------
# Get composite  GET /api/v1/composites/{composite_id}
# ---------------------------------------------------------------------------


class TestGetComposite:
    """Tests for GET /api/v1/composites/{composite_id}."""

    def test_get_happy_path_returns_composite_with_memberships(self, app, seeded_db):
        """Returns the seeded composite with all membership details."""
        client = _patched_client(app)
        try:
            resp = client.get(f"/api/v1/composites/{seeded_db['composite_id']}")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["id"] == seeded_db["composite_id"]
        assert body["collection_id"] == seeded_db["col_id"]
        assert body["composite_type"] == "plugin"
        assert body["display_name"] == "Test Plugin"
        assert body["member_count"] == 2

    def test_get_includes_membership_details(self, app, seeded_db):
        """Response includes full membership edge fields."""
        client = _patched_client(app)
        try:
            resp = client.get(f"/api/v1/composites/{seeded_db['composite_id']}")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        memberships = resp.json()["memberships"]
        assert len(memberships) == 2

        child_uuids = {m["child_artifact_uuid"] for m in memberships}
        assert seeded_db["canvas_uuid"] in child_uuids
        assert seeded_db["build_uuid"] in child_uuids

        for m in memberships:
            assert "collection_id" in m
            assert "composite_id" in m
            assert "relationship_type" in m
            assert "created_at" in m

    def test_get_unknown_composite_returns_404(self, app, seeded_db):
        """Requesting a non-existent composite returns 404."""
        client = _patched_client(app)
        try:
            resp = client.get("/api/v1/composites/composite:does-not-exist")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_get_response_schema_shape(self, app, seeded_db):
        """Response body contains all required top-level keys."""
        client = _patched_client(app)
        try:
            resp = client.get(f"/api/v1/composites/{seeded_db['composite_id']}")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        required_keys = {
            "id", "collection_id", "composite_type", "display_name",
            "description", "created_at", "updated_at", "memberships",
            "member_count",
        }
        assert required_keys.issubset(body.keys())


# ---------------------------------------------------------------------------
# Update composite  PUT /api/v1/composites/{composite_id}
# ---------------------------------------------------------------------------


class TestUpdateComposite:
    """Tests for PUT /api/v1/composites/{composite_id}."""

    def test_update_display_name_returns_200(self, app, seeded_db):
        """Updating display_name returns 200 with the new value."""
        client = _patched_client(app)
        try:
            resp = client.put(
                f"/api/v1/composites/{seeded_db['composite_id']}",
                json={"display_name": "Updated Plugin Name"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["display_name"] == "Updated Plugin Name"

    def test_update_description_returns_200(self, app, seeded_db):
        """Updating description returns 200 with the new value."""
        client = _patched_client(app)
        try:
            resp = client.put(
                f"/api/v1/composites/{seeded_db['composite_id']}",
                json={"description": "New description text."},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["description"] == "New description text."

    def test_update_composite_type_returns_200(self, app, seeded_db):
        """Updating composite_type to 'stack' returns 200 with updated type."""
        client = _patched_client(app)
        try:
            resp = client.put(
                f"/api/v1/composites/{seeded_db['composite_id']}",
                json={"composite_type": "stack"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["composite_type"] == "stack"

    def test_update_unknown_composite_returns_404(self, app, seeded_db):
        """Updating a non-existent composite returns 404."""
        client = _patched_client(app)
        try:
            resp = client.put(
                "/api/v1/composites/composite:does-not-exist",
                json={"display_name": "Irrelevant"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_update_empty_body_is_accepted(self, app, seeded_db):
        """PUT with no changed fields (all nulls) returns 200 — no-op update."""
        client = _patched_client(app)
        try:
            resp = client.put(
                f"/api/v1/composites/{seeded_db['composite_id']}",
                json={},
            )
        finally:
            _stop_client(client)

        # Router delegates to service.update_composite() with all-None args;
        # should succeed (no-op) and return the unchanged record.
        assert resp.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Delete composite  DELETE /api/v1/composites/{composite_id}
# ---------------------------------------------------------------------------


class TestDeleteComposite:
    """Tests for DELETE /api/v1/composites/{composite_id}."""

    def test_delete_happy_path_returns_204(self, app, seeded_db):
        """Deleting an existing composite returns 204 No Content."""
        client = _patched_client(app)
        try:
            resp = client.delete(f"/api/v1/composites/{seeded_db['composite_id']}")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_removes_composite_from_list(self, app, seeded_db):
        """After deletion, the composite no longer appears in the list."""
        client = _patched_client(app)
        try:
            client.delete(f"/api/v1/composites/{seeded_db['composite_id']}")
            resp = client.get(
                "/api/v1/composites",
                params={"collection_id": seeded_db["col_id"]},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] == 0

    def test_delete_unknown_composite_returns_404(self, app, seeded_db):
        """Deleting a non-existent composite returns 404."""
        client = _patched_client(app)
        try:
            resp = client.delete("/api/v1/composites/composite:does-not-exist")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_delete_cascade_false_preserves_child_artifacts(self, app, seeded_db, db_session):
        """cascade_delete_children=false (default) does not delete child Artifact rows."""
        client = _patched_client(app)
        try:
            resp = client.delete(
                f"/api/v1/composites/{seeded_db['composite_id']}",
                params={"cascade_delete_children": "false"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Child Artifact rows must still exist
        remaining = (
            db_session.query(Artifact)
            .filter(Artifact.id.in_(["skill:canvas", "command:build"]))
            .all()
        )
        assert len(remaining) == 2

    @pytest.mark.xfail(
        reason=(
            "cascade_delete_children=True triggers ORM unit-of-work mismatch: "
            "session.delete(composite) cascades membership deletes via ORM, "
            "then ON DELETE CASCADE fires in SQLite — the ORM expects to delete "
            "N membership rows but finds 0 already removed, raising StaleDataError. "
            "Fix requires raw SQL delete or session.expunge on membership rows first."
        ),
        strict=True,
    )
    def test_delete_cascade_true_removes_child_artifacts(self, app, seeded_db, db_session):
        """cascade_delete_children=true also removes the child Artifact rows.

        Currently xfail due to ORM unit-of-work / ON DELETE CASCADE mismatch
        in CompositeMembershipRepository.delete_composite().
        """
        client = _patched_client(app)
        try:
            resp = client.delete(
                f"/api/v1/composites/{seeded_db['composite_id']}",
                params={"cascade_delete_children": "true"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Child Artifact rows must be gone
        remaining = (
            db_session.query(Artifact)
            .filter(Artifact.id.in_(["skill:canvas", "command:build"]))
            .all()
        )
        assert remaining == []


# ---------------------------------------------------------------------------
# Add member  POST /api/v1/composites/{composite_id}/members
# ---------------------------------------------------------------------------


class TestAddCompositeMember:
    """Tests for POST /api/v1/composites/{composite_id}/members."""

    def _add_member(self, client, composite_id, artifact_id, col_id, **extra):
        return client.post(
            f"/api/v1/composites/{composite_id}/members",
            params={"collection_id": col_id},
            json={"artifact_id": artifact_id, **extra},
        )

    def test_add_member_happy_path_returns_201(self, app, seeded_db, db_session):
        """Adding a new artifact member to a new composite returns 201."""
        # Create a fresh composite so we can add a member to it
        fresh_composite_id = "composite:for-add-member"
        db_session.add(
            CompositeArtifact(
                id=fresh_composite_id,
                collection_id=seeded_db["col_id"],
                composite_type="plugin",
            )
        )
        db_session.commit()

        client = _patched_client(app)
        try:
            resp = self._add_member(
                client,
                fresh_composite_id,
                "skill:canvas",
                seeded_db["col_id"],
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        body = resp.json()
        assert body["child_artifact_uuid"] == seeded_db["canvas_uuid"]
        assert body["composite_id"] == fresh_composite_id
        assert body["relationship_type"] == "contains"

    def test_add_member_unknown_composite_returns_404(self, app, seeded_db):
        """Adding a member to a non-existent composite returns 404."""
        client = _patched_client(app)
        try:
            resp = self._add_member(
                client,
                "composite:does-not-exist",
                "skill:canvas",
                seeded_db["col_id"],
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_add_member_unknown_artifact_returns_400(self, app, seeded_db):
        """Adding an artifact not in the cache returns 400."""
        client = _patched_client(app)
        try:
            resp = self._add_member(
                client,
                seeded_db["composite_id"],
                "skill:not-in-cache",
                seeded_db["col_id"],
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "skill:not-in-cache" in resp.json()["detail"]

    def test_add_duplicate_member_returns_409(self, app, seeded_db):
        """Adding an already-present member returns 409 Conflict."""
        # skill:canvas is already a member of composite:test-plugin via seeded_db
        client = _patched_client(app)
        try:
            resp = self._add_member(
                client,
                seeded_db["composite_id"],
                "skill:canvas",
                seeded_db["col_id"],
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_add_member_with_custom_relationship_type(self, app, seeded_db, db_session):
        """Relationship type is stored correctly when specified."""
        fresh_composite_id = "composite:for-reltype-test"
        db_session.add(
            CompositeArtifact(
                id=fresh_composite_id,
                collection_id=seeded_db["col_id"],
                composite_type="plugin",
            )
        )
        db_session.commit()

        client = _patched_client(app)
        try:
            resp = self._add_member(
                client,
                fresh_composite_id,
                "skill:canvas",
                seeded_db["col_id"],
                relationship_type="extends",
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["relationship_type"] == "extends"

    def test_add_member_with_position(self, app, seeded_db, db_session):
        """Position field is accepted and included in the response."""
        fresh_composite_id = "composite:for-position-test"
        db_session.add(
            CompositeArtifact(
                id=fresh_composite_id,
                collection_id=seeded_db["col_id"],
                composite_type="plugin",
            )
        )
        db_session.commit()

        client = _patched_client(app)
        try:
            resp = self._add_member(
                client,
                fresh_composite_id,
                "skill:canvas",
                seeded_db["col_id"],
                position=5,
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["position"] == 5

    def test_add_member_missing_collection_id_returns_422(self, app, seeded_db):
        """collection_id query param is required; omitting it returns 422."""
        client = _patched_client(app)
        try:
            resp = client.post(
                f"/api/v1/composites/{seeded_db['composite_id']}/members",
                json={"artifact_id": "skill:canvas"},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ---------------------------------------------------------------------------
# Remove member  DELETE /api/v1/composites/{composite_id}/members/{member_uuid}
# ---------------------------------------------------------------------------


class TestRemoveCompositeMember:
    """Tests for DELETE /api/v1/composites/{composite_id}/members/{member_uuid}.

    NOTE — Router ordering caveat
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    The composites router registers ``DELETE /{composite_id:path}`` before
    ``DELETE /{composite_id}/members/{member_uuid}``.  FastAPI matches routes
    in registration order, so the greedy ``:path`` pattern intercepts any
    ``DELETE .../members/{uuid}`` request before the dedicated endpoint can
    handle it.

    HTTP-path tests are marked ``xfail`` to document this production routing
    defect.  The service-level tests below validate the underlying delete logic
    works correctly and will pass once the router ordering is corrected.
    """

    @pytest.mark.xfail(
        reason=(
            "Router ordering bug: DELETE /{composite_id:path} intercepts "
            "DELETE /{composite_id}/members/{member_uuid} requests. "
            "Fix by registering /members routes before the :path catch-all."
        ),
        strict=True,
    )
    def test_remove_member_happy_path_returns_204(self, app, seeded_db):
        """Removing an existing member by UUID returns 204 No Content.

        Expected to fail until router ordering is corrected.
        """
        client = _patched_client(app)
        try:
            resp = client.delete(
                f"/api/v1/composites/{seeded_db['composite_id']}"
                f"/members/{seeded_db['canvas_uuid']}"
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.xfail(
        reason=(
            "Router ordering bug: DELETE /{composite_id:path} intercepts "
            "DELETE /{composite_id}/members/{member_uuid} requests."
        ),
        strict=True,
    )
    def test_remove_member_decrements_member_count(self, app, seeded_db):
        """After removal via HTTP, the composite's member_count is decremented.

        Expected to fail until router ordering is corrected.
        """
        client = _patched_client(app)
        try:
            client.delete(
                f"/api/v1/composites/{seeded_db['composite_id']}"
                f"/members/{seeded_db['canvas_uuid']}"
            )
            resp = client.get(f"/api/v1/composites/{seeded_db['composite_id']}")
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["member_count"] == 1

    def test_remove_member_unknown_uuid_returns_404_via_service(
        self, composite_repo, seeded_db, temp_db
    ):
        """Removing a UUID not present in any membership returns False from repo.

        Uses the repository directly to bypass the HTTP routing issue.
        """
        non_member_uuid = _make_uuid()
        result = composite_repo.delete_membership(
            composite_id=seeded_db["composite_id"],
            child_artifact_uuid=non_member_uuid,
        )
        assert result is False

    def test_remove_member_service_returns_true_when_found(
        self, composite_repo, seeded_db
    ):
        """Removing an existing membership via repo returns True."""
        result = composite_repo.delete_membership(
            composite_id=seeded_db["composite_id"],
            child_artifact_uuid=seeded_db["canvas_uuid"],
        )
        assert result is True

    def test_remove_member_child_artifact_row_preserved(
        self, composite_repo, seeded_db, db_session
    ):
        """Removing a membership edge via repo does NOT delete the child Artifact row."""
        composite_repo.delete_membership(
            composite_id=seeded_db["composite_id"],
            child_artifact_uuid=seeded_db["canvas_uuid"],
        )

        # skill:canvas Artifact row must still exist in the same DB
        db_session.expire_all()  # force re-read from DB
        artifact = db_session.query(Artifact).filter(
            Artifact.id == "skill:canvas"
        ).first()
        assert artifact is not None


# ---------------------------------------------------------------------------
# Reorder members  PATCH /api/v1/composites/{composite_id}/members
# ---------------------------------------------------------------------------


class TestReorderCompositeMembers:
    """Tests for PATCH /api/v1/composites/{composite_id}/members."""

    def test_reorder_happy_path_returns_200(self, app, seeded_db):
        """Reordering members returns 200 with updated membership list."""
        client = _patched_client(app)
        try:
            resp = client.patch(
                f"/api/v1/composites/{seeded_db['composite_id']}/members",
                json={
                    "members": [
                        {"artifact_id": "skill:canvas", "position": 1},
                        {"artifact_id": "command:build", "position": 0},
                    ]
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2

    def test_reorder_updates_positions(self, app, seeded_db):
        """After reorder, positions reflect the new order."""
        client = _patched_client(app)
        try:
            resp = client.patch(
                f"/api/v1/composites/{seeded_db['composite_id']}/members",
                json={
                    "members": [
                        {"artifact_id": "skill:canvas", "position": 9},
                        {"artifact_id": "command:build", "position": 3},
                    ]
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        positions = {m["child_artifact_uuid"]: m.get("position") for m in resp.json()}
        assert positions.get(seeded_db["canvas_uuid"]) == 9
        assert positions.get(seeded_db["build_uuid"]) == 3

    def test_reorder_unknown_composite_returns_404(self, app, seeded_db):
        """Reordering members of a non-existent composite returns 404."""
        client = _patched_client(app)
        try:
            resp = client.patch(
                "/api/v1/composites/composite:does-not-exist/members",
                json={
                    "members": [
                        {"artifact_id": "skill:canvas", "position": 0}
                    ]
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_reorder_unknown_artifact_returns_400(self, app, seeded_db):
        """Referencing an artifact not in cache during reorder returns 400."""
        client = _patched_client(app)
        try:
            resp = client.patch(
                f"/api/v1/composites/{seeded_db['composite_id']}/members",
                json={
                    "members": [
                        {"artifact_id": "skill:not-in-cache", "position": 0}
                    ]
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_reorder_empty_members_list_returns_422(self, app, seeded_db):
        """An empty members list fails validation (min_length=1 on the schema)."""
        client = _patched_client(app)
        try:
            resp = client.patch(
                f"/api/v1/composites/{seeded_db['composite_id']}/members",
                json={"members": []},
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reorder_response_is_list_of_memberships(self, app, seeded_db):
        """Response is a list of MembershipResponse objects with required fields."""
        client = _patched_client(app)
        try:
            resp = client.patch(
                f"/api/v1/composites/{seeded_db['composite_id']}/members",
                json={
                    "members": [
                        {"artifact_id": "skill:canvas", "position": 0},
                    ]
                },
            )
        finally:
            _stop_client(client)

        assert resp.status_code == status.HTTP_200_OK
        for item in resp.json():
            assert "child_artifact_uuid" in item
            assert "composite_id" in item
            assert "collection_id" in item
            assert "relationship_type" in item
            assert "created_at" in item


# ---------------------------------------------------------------------------
# Remove member endpoint: direct HTTP handler coverage
# ---------------------------------------------------------------------------


class TestRemoveCompositeMemberHTTPHandler:
    """Direct tests for remove_composite_member endpoint function.

    These tests patch ``CompositeMembershipRepository`` at the module that
    the endpoint imports it from (local import inside function body) so the
    handler code at lines 532-557 is executed and covered.
    """

    def _delete_member(self, application, composite_id, member_uuid):
        """Send DELETE to the remove-member URL (expects `:path` route to match)."""
        # The /{composite_id:path} DELETE route will intercept this URL.
        # We patch the service so it treats the full path as a delete-composite
        # call and returns False (not found), which gives us 404.  This is by
        # design; the tests document the routing limitation.
        with TestClient(application) as client:
            return client.delete(
                f"/api/v1/composites/{composite_id}/members/{member_uuid}"
            )

    def test_remove_member_endpoint_body_covered_via_mock(
        self, app, seeded_db, temp_db
    ):
        """Cover remove_composite_member handler body by invoking it directly.

        We patch the router's local import of CompositeMembershipRepository so
        delete_membership() returns True, then call the endpoint via its actual
        registered path.  Because /{composite_id:path} intercepts the request,
        the endpoint body is never reached via HTTP — this test covers the body
        by unit-testing the handler function directly.
        """
        from skillmeat.api.routers.composites import remove_composite_member
        import asyncio

        # Provide a mock repo that returns True (successful delete)
        mock_repo = MagicMock()
        mock_repo.delete_membership.return_value = True

        with patch(
            "skillmeat.cache.composite_repository.CompositeMembershipRepository",
            return_value=mock_repo,
        ):
            # Call the async handler directly
            result = asyncio.get_event_loop().run_until_complete(
                remove_composite_member(
                    composite_id=seeded_db["composite_id"],
                    member_uuid=seeded_db["canvas_uuid"],
                )
            )
            # Handler returns None on success (HTTP 204)
            assert result is None
            mock_repo.delete_membership.assert_called_once_with(
                composite_id=seeded_db["composite_id"],
                child_artifact_uuid=seeded_db["canvas_uuid"],
            )

    def test_remove_member_endpoint_body_not_found_via_mock(self, app, seeded_db):
        """Cover remove_composite_member handler's not-found branch."""
        from skillmeat.api.routers.composites import remove_composite_member
        from fastapi import HTTPException
        import asyncio

        mock_repo = MagicMock()
        mock_repo.delete_membership.return_value = False  # not found

        with patch(
            "skillmeat.cache.composite_repository.CompositeMembershipRepository",
            return_value=mock_repo,
        ):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    remove_composite_member(
                        composite_id=seeded_db["composite_id"],
                        member_uuid="nonexistent-uuid",
                    )
                )
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# 500 internal-error branch coverage
# ---------------------------------------------------------------------------


class TestInternalErrorBranches:
    """Cover the generic ``except Exception`` 500 branches in each endpoint."""

    def _build_broken_svc_patch(self, error_method: str):
        """Return a patch that raises RuntimeError when ``error_method`` is called."""
        mock_svc = MagicMock()
        getattr(mock_svc, error_method).side_effect = RuntimeError("boom")
        return patch(
            "skillmeat.api.routers.composites.CompositeService",
            return_value=mock_svc,
        )

    def test_create_500_on_unexpected_error(self, app, seeded_db):
        """Generic exception in create_composite returns 500."""
        with self._build_broken_svc_patch("create_composite"):
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/composites",
                    json={
                        "composite_id": "composite:boom",
                        "collection_id": seeded_db["col_id"],
                    },
                )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_get_500_on_unexpected_error(self, app, seeded_db):
        """Generic exception in get_composite returns 500."""
        with self._build_broken_svc_patch("get_composite"):
            with TestClient(app) as client:
                resp = client.get(
                    f"/api/v1/composites/{seeded_db['composite_id']}"
                )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_update_500_on_unexpected_error(self, app, seeded_db):
        """Generic exception in update_composite returns 500."""
        with self._build_broken_svc_patch("update_composite"):
            with TestClient(app) as client:
                resp = client.put(
                    f"/api/v1/composites/{seeded_db['composite_id']}",
                    json={"display_name": "X"},
                )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_reorder_500_on_unexpected_error(self, app, seeded_db):
        """Generic exception in reorder_composite_members returns 500."""
        mock_svc = MagicMock()
        mock_svc.get_composite.return_value = {"id": seeded_db["composite_id"]}
        mock_svc.reorder_composite_members.side_effect = RuntimeError("boom")

        with patch(
            "skillmeat.api.routers.composites.CompositeService",
            return_value=mock_svc,
        ):
            with TestClient(app) as client:
                resp = client.patch(
                    f"/api/v1/composites/{seeded_db['composite_id']}/members",
                    json={"members": [{"artifact_id": "skill:canvas", "position": 0}]},
                )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
