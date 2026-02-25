"""Integration tests for Deployment Sets API endpoints.

Tests cover:
1. Circular reference detection (FR-09)
2. 3-level nested resolve deduplication + batch deploy adapter mapping
3. FR-10 delete semantics — deleting set B removes inbound member refs from set A
4. Clone isolation — cloning and renaming does not affect the original
5. Observability — missing-member UUID warning includes set_id and traversal path
"""

import logging
import uuid
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CollectionArtifact,
    DeploymentSet,
    DeploymentSetMember,
    Project,
)


# =============================================================================
# Shared fixtures
# =============================================================================


@pytest.fixture(scope="module")
def test_settings() -> APISettings:
    """Return API settings configured for testing (no auth, in-memory)."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        api_key_enabled=False,
    )


@pytest.fixture()
def test_engine(tmp_path):
    """Create an isolated SQLite engine with schema pre-created via ORM.

    Uses ``Base.metadata.create_all()`` (same approach as other API tests such
    as ``test_groups.py``) to bypass Alembic migrations entirely.  This avoids
    migration ordering issues (e.g. ALTER on tables that haven't been created
    yet in a fresh in-memory DB).
    """
    db_path = tmp_path / "deployment_sets_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def session_factory(test_engine):
    """Session factory bound to the per-test engine."""
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db(session_factory) -> Generator[Session, None, None]:
    """DB session for direct fixture setup."""
    session = session_factory()
    yield session
    session.close()


@pytest.fixture()
def app(test_settings, test_engine, session_factory):
    """FastAPI app wired to the per-test in-memory DB.

    Patching strategy mirrors ``test_groups.py``:

    1. Patch ``DeploymentSetRepository._get_session`` so the repo uses the
       per-test engine rather than building its own from disk.  This avoids
       running migrations on a fresh file and the resulting
       ``table already exists`` / ``no such table`` errors.
    2. Patch ``get_session`` in the router's namespace so
       ``DeploymentSetService`` (created inline in route handlers) also uses
       the per-test engine.
    """
    from skillmeat.api.config import get_settings
    from skillmeat.cache.repositories import DeploymentSetRepository

    _sf = session_factory

    def patched_get_session(self_inner):
        return _sf()

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings

    with patch.object(DeploymentSetRepository, "_get_session", patched_get_session):
        with patch("skillmeat.api.routers.deployment_sets.get_session", _sf):
            yield application

    application.dependency_overrides.clear()


@pytest.fixture()
def client(app) -> Generator[TestClient, None, None]:
    """FastAPI test client."""
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc


BASE = "/api/v1/deployment-sets"


# ---------------------------------------------------------------------------
# Helper: create a deployment set via the API
# ---------------------------------------------------------------------------


def _create_set(client: TestClient, name: str, description: str = "") -> dict:
    resp = client.post(BASE, json={"name": name, "description": description or None})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _add_nested_member(client: TestClient, parent_id: str, child_id: str) -> dict:
    resp = client.post(
        f"{BASE}/{parent_id}/members",
        json={"nested_set_id": child_id},
    )
    return resp


def _add_artifact_member(client: TestClient, set_id: str, artifact_uuid: str) -> dict:
    resp = client.post(
        f"{BASE}/{set_id}/members",
        json={"artifact_uuid": artifact_uuid},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# =============================================================================
# 1. Circular-reference detection
# =============================================================================


class TestCircularRefDetection:
    """FR-09: Adding a nested set that creates a cycle must return HTTP 422."""

    def test_circular_ref_a_contains_b_then_b_contains_a(self, client):
        """Create A, add B as member of A, then attempt A as member of B → 422."""
        set_a = _create_set(client, "Set A")
        set_b = _create_set(client, "Set B")

        # A contains B — should succeed
        add_resp = _add_nested_member(client, set_a["id"], set_b["id"])
        assert add_resp.status_code == 201, add_resp.text

        # Now try to add A as member of B — must fail with 422
        cycle_resp = _add_nested_member(client, set_b["id"], set_a["id"])
        assert cycle_resp.status_code == 422, cycle_resp.text

        detail = cycle_resp.json().get("detail", "")
        assert "circular" in detail.lower(), (
            f"Expected 'circular' in error detail, got: {detail!r}"
        )

    def test_self_reference_rejected(self, client):
        """A set cannot reference itself as a nested member."""
        set_a = _create_set(client, "Self-Ref Set")

        cycle_resp = _add_nested_member(client, set_a["id"], set_a["id"])
        assert cycle_resp.status_code == 422, cycle_resp.text

    def test_indirect_cycle_three_nodes(self, client):
        """A→B→C and then C→A must be rejected as a cycle."""
        set_a = _create_set(client, "Cycle A")
        set_b = _create_set(client, "Cycle B")
        set_c = _create_set(client, "Cycle C")

        r1 = _add_nested_member(client, set_a["id"], set_b["id"])
        assert r1.status_code == 201

        r2 = _add_nested_member(client, set_b["id"], set_c["id"])
        assert r2.status_code == 201

        # C→A would create a cycle A→B→C→A
        r3 = _add_nested_member(client, set_c["id"], set_a["id"])
        assert r3.status_code == 422, r3.text


# =============================================================================
# 2. Batch-deploy adapter — resolve deduplication + UUID mapping
# =============================================================================


class TestBatchDeployAdapter:
    """Resolve returns each artifact UUID exactly once; batch deploy maps UUIDs."""

    @pytest.fixture()
    def three_level_hierarchy(self, client, db) -> dict:
        """Create A→B→C hierarchy with artifacts at each level.

        Returns a dict with set IDs and artifact UUIDs.
        """
        # Create a collection + project so Artifact FK constraints are satisfied
        collection = Collection(id=uuid.uuid4().hex, name="Test Collection")
        db.add(collection)
        project = Project(
            id=uuid.uuid4().hex,
            name="Test Project",
            path="/tmp/test-proj",
            status="active",
        )
        db.add(project)
        db.flush()

        def make_artifact(name: str) -> str:
            art_uuid = uuid.uuid4().hex
            artifact = Artifact(
                id=f"skill:{name}",
                uuid=art_uuid,
                project_id=project.id,
                name=name,
                type="skill",
            )
            db.add(artifact)
            db.flush()
            ca = CollectionArtifact(
                collection_id=collection.id,
                artifact_uuid=art_uuid,
                added_at=datetime.utcnow(),
                synced_at=datetime.utcnow(),
            )
            db.add(ca)
            db.flush()
            return art_uuid

        uuid_c1 = make_artifact("artifact-c1")
        uuid_c2 = make_artifact("artifact-c2")
        uuid_b1 = make_artifact("artifact-b1")
        uuid_a1 = make_artifact("artifact-a1")
        db.commit()

        set_c = _create_set(client, "Set C — leaf")
        set_b = _create_set(client, "Set B — mid")
        set_a = _create_set(client, "Set A — root")

        # C gets two artifacts
        _add_artifact_member(client, set_c["id"], uuid_c1)
        _add_artifact_member(client, set_c["id"], uuid_c2)

        # B gets one artifact + C as nested set
        _add_artifact_member(client, set_b["id"], uuid_b1)
        r = _add_nested_member(client, set_b["id"], set_c["id"])
        assert r.status_code == 201

        # A gets one artifact + B as nested set
        _add_artifact_member(client, set_a["id"], uuid_a1)
        r = _add_nested_member(client, set_a["id"], set_b["id"])
        assert r.status_code == 201

        return {
            "set_a_id": set_a["id"],
            "set_b_id": set_b["id"],
            "set_c_id": set_c["id"],
            "uuids": {uuid_a1, uuid_b1, uuid_c1, uuid_c2},
        }

    def test_resolve_returns_all_uuids_exactly_once(self, client, three_level_hierarchy):
        """GET /{set_a_id}/resolve returns all 4 UUIDs with no duplicates."""
        set_a_id = three_level_hierarchy["set_a_id"]
        expected_uuids = three_level_hierarchy["uuids"]

        resp = client.get(f"{BASE}/{set_a_id}/resolve")
        assert resp.status_code == 200, resp.text

        data = resp.json()
        resolved = data["resolved_artifacts"]
        returned_uuids = [item["artifact_uuid"] for item in resolved]

        # No duplicates
        assert len(returned_uuids) == len(set(returned_uuids)), (
            f"Duplicates found in resolved artifacts: {returned_uuids}"
        )

        # All expected UUIDs present
        assert set(returned_uuids) == expected_uuids, (
            f"Expected {expected_uuids}, got {set(returned_uuids)}"
        )

        assert data["total_count"] == 4

    def test_batch_deploy_dry_run_maps_uuids(self, client, three_level_hierarchy, tmp_path):
        """POST /{set_a_id}/deploy dry_run returns skipped results for all UUIDs."""
        set_a_id = three_level_hierarchy["set_a_id"]
        expected_uuids = three_level_hierarchy["uuids"]

        project_dir = tmp_path / "mock-project"
        project_dir.mkdir()

        resp = client.post(
            f"{BASE}/{set_a_id}/deploy",
            json={"project_path": str(project_dir), "dry_run": True},
        )
        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["dry_run"] is True
        assert data["total"] == 4
        assert data["skipped"] == 4
        assert data["succeeded"] == 0
        assert data["failed"] == 0

        result_uuids = {r["artifact_uuid"] for r in data["results"]}
        assert result_uuids == expected_uuids, (
            f"Deploy result UUIDs {result_uuids} != expected {expected_uuids}"
        )

        for item in data["results"]:
            assert item["status"] == "skipped"


# =============================================================================
# 3. FR-10 delete semantics — inbound parent references removed
# =============================================================================


class TestDeleteSemantics:
    """Deleting a set must remove its membership rows in other (parent) sets."""

    def test_delete_child_removes_member_ref_from_parent(self, client):
        """Create A containing B; delete B; A's member list must be empty."""
        set_a = _create_set(client, "Parent Set")
        set_b = _create_set(client, "Child Set to Delete")

        # Add B as nested member of A
        add_resp = _add_nested_member(client, set_a["id"], set_b["id"])
        assert add_resp.status_code == 201

        # Verify A has 1 member
        members_resp = client.get(f"{BASE}/{set_a['id']}/members")
        assert members_resp.status_code == 200
        assert len(members_resp.json()) == 1

        # Delete B
        del_resp = client.delete(f"{BASE}/{set_b['id']}")
        assert del_resp.status_code == 204

        # Verify B is gone
        get_resp = client.get(f"{BASE}/{set_b['id']}")
        assert get_resp.status_code == 404

        # Verify A's member list no longer references B
        members_after = client.get(f"{BASE}/{set_a['id']}/members")
        assert members_after.status_code == 200
        members = members_after.json()
        nested_set_ids = [m.get("nested_set_id") for m in members]
        assert set_b["id"] not in nested_set_ids, (
            f"Deleted set B still referenced in A's members: {members}"
        )

    def test_delete_set_cascades_own_member_rows(self, client):
        """Deleting a set also removes its own member rows (cascade)."""
        set_a = _create_set(client, "Set With Members")
        artifact_uuid = uuid.uuid4().hex
        _add_artifact_member(client, set_a["id"], artifact_uuid)

        # Confirm member exists
        members_resp = client.get(f"{BASE}/{set_a['id']}/members")
        assert len(members_resp.json()) == 1

        # Delete the set
        del_resp = client.delete(f"{BASE}/{set_a['id']}")
        assert del_resp.status_code == 204

        # Set is gone
        assert client.get(f"{BASE}/{set_a['id']}").status_code == 404

    def test_delete_nonexistent_set_returns_404(self, client):
        """Deleting a set that does not exist must return 404."""
        fake_id = uuid.uuid4().hex
        resp = client.delete(f"{BASE}/{fake_id}")
        assert resp.status_code == 404


# =============================================================================
# 4. Clone isolation
# =============================================================================


class TestCloneIsolation:
    """Cloning a set creates a new independent copy."""

    def test_clone_has_copy_suffix(self, client):
        """Cloned set name is '<original> (copy)'."""
        original = _create_set(client, "My Original Set", "Original description")

        clone_resp = client.post(f"{BASE}/{original['id']}/clone")
        assert clone_resp.status_code == 201, clone_resp.text

        clone = clone_resp.json()
        assert clone["name"] == "My Original Set (copy)"
        assert clone["id"] != original["id"]

    def test_rename_clone_does_not_affect_original(self, client):
        """Modifying the clone name must not change the original set name."""
        original = _create_set(client, "Stable Name Set")

        clone_resp = client.post(f"{BASE}/{original['id']}/clone")
        assert clone_resp.status_code == 201
        clone = clone_resp.json()

        # Rename the clone
        rename_resp = client.put(
            f"{BASE}/{clone['id']}",
            json={"name": "Completely Different Name"},
        )
        assert rename_resp.status_code == 200
        assert rename_resp.json()["name"] == "Completely Different Name"

        # Verify original is untouched
        get_original = client.get(f"{BASE}/{original['id']}")
        assert get_original.status_code == 200
        assert get_original.json()["name"] == "Stable Name Set"

    def test_clone_inherits_members_independently(self, client):
        """Clone reproduces member list; removing a clone member does not affect original."""
        original = _create_set(client, "Set With Members")
        art_uuid = uuid.uuid4().hex
        _add_artifact_member(client, original["id"], art_uuid)

        clone_resp = client.post(f"{BASE}/{original['id']}/clone")
        assert clone_resp.status_code == 201
        clone = clone_resp.json()

        # Both original and clone should have 1 member
        orig_members = client.get(f"{BASE}/{original['id']}/members").json()
        clone_members = client.get(f"{BASE}/{clone['id']}/members").json()
        assert len(orig_members) == 1
        assert len(clone_members) == 1

        # Remove the member from the clone
        clone_member_id = clone_members[0]["id"]
        del_resp = client.delete(f"{BASE}/{clone['id']}/members/{clone_member_id}")
        assert del_resp.status_code == 204

        # Original must still have its member
        orig_after = client.get(f"{BASE}/{original['id']}/members").json()
        assert len(orig_after) == 1, (
            "Removing clone member affected original set members"
        )

    def test_clone_nonexistent_set_returns_404(self, client):
        """Cloning a set that does not exist must return 404."""
        fake_id = uuid.uuid4().hex
        resp = client.post(f"{BASE}/{fake_id}/clone")
        assert resp.status_code == 404


# =============================================================================
# 5. Observability — missing-member UUID warning log
# =============================================================================


class TestObservabilityWarnings:
    """Batch deploy with a missing-member UUID logs a warning with set_id and path."""

    def test_missing_uuid_logs_warning_with_set_id(self, client, tmp_path, caplog):
        """An artifact UUID not in the cache should produce a WARNING log entry
        and a completion INFO log; together they contain the set_id and the
        missing UUID (traversal path context)."""
        ds = _create_set(client, "Observability Test Set")
        missing_uuid = uuid.uuid4().hex

        # Add the missing UUID as a member (it's stored but has no Artifact row)
        _add_artifact_member(client, ds["id"], missing_uuid)

        project_dir = tmp_path / "obs-project"
        project_dir.mkdir()

        with caplog.at_level(logging.DEBUG, logger="skillmeat.api.routers.deployment_sets"):
            resp = client.post(
                f"{BASE}/{ds['id']}/deploy",
                json={"project_path": str(project_dir), "dry_run": False},
            )

        assert resp.status_code == 200, resp.text

        data = resp.json()
        assert data["failed"] == 1
        assert data["total"] == 1

        # The result should carry the missing UUID and an error message
        result = data["results"][0]
        assert result["artifact_uuid"] == missing_uuid
        assert result["status"] == "failed"
        assert result["error"] is not None

        all_messages = [r.message for r in caplog.records]

        # A WARNING must be emitted for the missing UUID (with the UUID as context)
        warning_messages = [
            r.message for r in caplog.records if r.levelno >= logging.WARNING
        ]
        assert any(missing_uuid in msg for msg in warning_messages), (
            f"No WARNING log containing missing_uuid={missing_uuid!r}. "
            f"Warning messages found: {warning_messages}"
        )

        # The batch_deploy completion log (INFO) must include the set_id so
        # operators can correlate failures to a specific deployment set.
        assert any(ds["id"] in msg for msg in all_messages), (
            f"No log containing set_id={ds['id']!r}. "
            f"All messages: {all_messages}"
        )

    def test_missing_uuid_error_message_contains_uuid(self, client, tmp_path):
        """The per-artifact error in the response references the missing UUID."""
        ds = _create_set(client, "Error Message Test")
        missing_uuid = uuid.uuid4().hex
        _add_artifact_member(client, ds["id"], missing_uuid)

        project_dir = tmp_path / "err-project"
        project_dir.mkdir()

        resp = client.post(
            f"{BASE}/{ds['id']}/deploy",
            json={"project_path": str(project_dir), "dry_run": False},
        )
        assert resp.status_code == 200

        result = resp.json()["results"][0]
        assert missing_uuid in (result.get("error") or ""), (
            f"Expected missing UUID in error message, got: {result.get('error')!r}"
        )
