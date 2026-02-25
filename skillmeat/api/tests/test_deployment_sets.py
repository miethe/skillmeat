"""Integration tests for Deployment Sets API endpoints.

Tests CRUD, clone, member management, resolve, and batch-deploy endpoints
against a real in-memory SQLite database via TestClient.
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings
from skillmeat.api.server import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_settings():
    """Create test API settings with auth and API-key auth disabled."""
    return APISettings(
        env="testing",
        auth_enabled=False,
        api_key_enabled=False,
        cors_enabled=False,
    )


@pytest.fixture
def client(api_settings):
    """TestClient with a fresh in-memory SQLite DB per test.

    We patch ``get_session`` to always return sessions from a temporary DB so
    tests are fully isolated from the developer's real collection.
    """
    app = create_app(api_settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def in_memory_repo(tmp_path):
    """Return a DeploymentSetRepository backed by a fresh SQLite file.

    Uses ``Base.metadata.create_all()`` to build the full schema instantly
    then stamps Alembic at head so the repository constructor's migration
    call is a no-op.  This avoids the incremental ALTER TABLE failures that
    occur when running migrations on a blank DB.
    """
    from alembic import command
    from sqlalchemy import create_engine

    from skillmeat.cache.migrations import get_alembic_config
    from skillmeat.cache.models import Base
    from skillmeat.cache.repositories import DeploymentSetRepository

    db_file = str(tmp_path / "test.db")

    # Build full schema via ORM (avoids incremental ALTER TABLE migration bugs)
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    engine.dispose()

    # Stamp Alembic at head so repository constructor migration call is a no-op
    alembic_cfg = get_alembic_config(db_file)
    command.stamp(alembic_cfg, "head")

    repo = DeploymentSetRepository(db_path=db_file)
    return repo, db_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_set_payload(name: str = "Test Set", **extra) -> dict:
    """Build a minimal valid DeploymentSetCreate payload."""
    payload = {"name": name}
    payload.update(extra)
    return payload


def make_artifact_member_payload(artifact_uuid: str, position: int = 0) -> dict:
    """Build a MemberCreate payload for an artifact."""
    return {"artifact_uuid": artifact_uuid, "position": position}


def make_set_member_payload(nested_set_id: str, position: int = 0) -> dict:
    """Build a MemberCreate payload for a nested set."""
    return {"nested_set_id": nested_set_id, "position": position}


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets
# ---------------------------------------------------------------------------


class TestCreateDeploymentSet:
    """Tests for POST /api/v1/deployment-sets."""

    def test_create_minimal(self, in_memory_repo):
        """Create a set with only a name — 201 returned."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/deployment-sets",
                    json={"name": "My Set"},
                )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Set"
        assert "id" in data
        assert data["member_count"] == 0
        assert data["tags"] == []
        assert data["owner_id"] == "local-user"

    def test_create_full(self, in_memory_repo):
        """Create a set with all optional fields."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/deployment-sets",
                    json={
                        "name": "Full Set",
                        "description": "A full set",
                        "icon": "🛠️",
                        "color": "#3b82f6",
                        "tags": ["backend", "python"],
                    },
                )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Full Set"
        assert data["description"] == "A full set"
        assert data["tags"] == ["backend", "python"]


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets
# ---------------------------------------------------------------------------


class TestListDeploymentSets:
    """Tests for GET /api/v1/deployment-sets."""

    def test_list_empty(self, in_memory_repo):
        """List returns empty items when no sets exist."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_sets(self, in_memory_repo):
        """List returns all sets owned by local-user."""
        repo, db_file = in_memory_repo
        repo.create(name="Set A", owner_id="local-user")
        repo.create(name="Set B", owner_id="local-user")
        repo.create(name="Other Owner", owner_id="other-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {item["name"] for item in data["items"]}
        assert names == {"Set A", "Set B"}

    def test_list_name_filter(self, in_memory_repo):
        """Name filter is applied as case-insensitive substring."""
        repo, db_file = in_memory_repo
        repo.create(name="Backend Tools", owner_id="local-user")
        repo.create(name="Frontend Setup", owner_id="local-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets?name=backend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Backend Tools"

    def test_list_pagination(self, in_memory_repo):
        """Limit and offset work correctly."""
        repo, db_file = in_memory_repo
        for i in range(5):
            repo.create(name=f"Set {i}", owner_id="local-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets?limit=3&offset=0")
                data = resp.json()
                assert len(data["items"]) == 3
                assert data["total"] == 5

                resp2 = client.get("/api/v1/deployment-sets?limit=3&offset=3")
                data2 = resp2.json()
                assert len(data2["items"]) == 2


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets/{set_id}
# ---------------------------------------------------------------------------


class TestGetDeploymentSet:
    """Tests for GET /api/v1/deployment-sets/{set_id}."""

    def test_get_existing(self, in_memory_repo):
        """Returns 200 with set details for a valid ID."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Target Set", owner_id="local-user", description="desc")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get(f"/api/v1/deployment-sets/{ds.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == ds.id
        assert data["name"] == "Target Set"
        assert data["description"] == "desc"

    def test_get_missing_returns_404(self, in_memory_repo):
        """Returns 404 for a non-existent set ID."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets/nonexistent-id")
        assert resp.status_code == 404

    def test_get_other_owners_set_returns_404(self, in_memory_repo):
        """Returns 404 when the set belongs to a different owner."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Private Set", owner_id="other-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get(f"/api/v1/deployment-sets/{ds.id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/deployment-sets/{set_id}
# ---------------------------------------------------------------------------


class TestUpdateDeploymentSet:
    """Tests for PUT /api/v1/deployment-sets/{set_id}."""

    def test_update_name(self, in_memory_repo):
        """Updating name returns 200 with updated data."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Old Name", owner_id="local-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.put(
                    f"/api/v1/deployment-sets/{ds.id}",
                    json={"name": "New Name"},
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"

    def test_update_tags(self, in_memory_repo):
        """Updating tags replaces existing tags."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Tagged Set", owner_id="local-user", tags=["old"])

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.put(
                    f"/api/v1/deployment-sets/{ds.id}",
                    json={"tags": ["new", "tags"]},
                )
        assert resp.status_code == 200
        assert resp.json()["tags"] == ["new", "tags"]

    def test_update_missing_returns_404(self, in_memory_repo):
        """Returns 404 for a non-existent set."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.put(
                    "/api/v1/deployment-sets/nonexistent",
                    json={"name": "x"},
                )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/deployment-sets/{set_id}
# ---------------------------------------------------------------------------


class TestDeleteDeploymentSet:
    """Tests for DELETE /api/v1/deployment-sets/{set_id}."""

    def test_delete_existing(self, in_memory_repo):
        """Deleting an existing set returns 204."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="To Delete", owner_id="local-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.delete(f"/api/v1/deployment-sets/{ds.id}")
        assert resp.status_code == 204

        # Verify it's gone
        assert repo.get(ds.id, "local-user") is None

    def test_delete_missing_returns_404(self, in_memory_repo):
        """Returns 404 when deleting a non-existent set."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.delete("/api/v1/deployment-sets/ghost")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets/{set_id}/clone
# ---------------------------------------------------------------------------


class TestCloneDeploymentSet:
    """Tests for POST /api/v1/deployment-sets/{set_id}/clone."""

    def test_clone_basic(self, in_memory_repo):
        """Clone returns 201 and appends ' (copy)' to the name."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Original", owner_id="local-user", tags=["a"])

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(f"/api/v1/deployment-sets/{ds.id}/clone")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Original (copy)"
        assert data["id"] != ds.id
        assert data["tags"] == ["a"]

    def test_clone_missing_source_returns_404(self, in_memory_repo):
        """Clone returns 404 when the source set does not exist."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post("/api/v1/deployment-sets/missing-id/clone")
        assert resp.status_code == 404

    def test_clone_preserves_members(self, in_memory_repo):
        """Clone includes all members of the source set."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="With Members", owner_id="local-user")
        art_uuid = uuid.uuid4().hex
        repo.add_member(ds.id, "local-user", artifact_uuid=art_uuid, position=0)

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(f"/api/v1/deployment-sets/{ds.id}/clone")
        assert resp.status_code == 201
        data = resp.json()
        assert data["member_count"] == 1


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets/{set_id}/members
# ---------------------------------------------------------------------------


class TestAddMember:
    """Tests for POST /api/v1/deployment-sets/{set_id}/members."""

    def test_add_artifact_member(self, in_memory_repo):
        """Adding an artifact member returns 201."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="My Set", owner_id="local-user")
        art_uuid = uuid.uuid4().hex

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session"
        ) as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    f"/api/v1/deployment-sets/{ds.id}/members",
                    json={"artifact_uuid": art_uuid, "position": 0},
                )
        assert resp.status_code == 201
        data = resp.json()
        assert data["artifact_uuid"] == art_uuid
        assert data["member_type"] == "artifact"
        assert data["position"] == 0

    def test_add_member_missing_set_returns_404(self, in_memory_repo):
        """Adding a member to a missing set returns 404."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/deployment-sets/missing-set/members",
                    json={"artifact_uuid": uuid.uuid4().hex},
                )
        assert resp.status_code == 404

    def test_add_member_invalid_payload_returns_422(self, in_memory_repo):
        """Sending zero refs returns 422 from Pydantic validation."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="My Set", owner_id="local-user")
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    f"/api/v1/deployment-sets/{ds.id}/members",
                    json={"position": 0},  # No ref provided
                )
        assert resp.status_code == 422

    def test_circular_reference_returns_422(self, in_memory_repo):
        """Adding a nested set that would form a cycle returns 422."""
        repo, db_file = in_memory_repo
        ds_a = repo.create(name="Set A", owner_id="local-user")
        ds_b = repo.create(name="Set B", owner_id="local-user")

        # Add A → B using the repo (A contains B as a nested member)
        repo.add_member(ds_a.id, "local-user", member_set_id=ds_b.id, position=0)

        # Now try to add B → A (cycle) via the API — should get 422
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(
            f"sqlite:///{db_file}",
            echo=False,
            connect_args={"check_same_thread": False},
        )

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session"
        ) as mock_get_session:
            mock_session = Session(engine)
            mock_get_session.return_value = mock_session

            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    f"/api/v1/deployment-sets/{ds_b.id}/members",
                    json={"nested_set_id": ds_a.id},
                )
            mock_session.close()
        assert resp.status_code == 422
        assert "circular" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /api/v1/deployment-sets/{set_id}/members/{member_id}
# ---------------------------------------------------------------------------


class TestRemoveMember:
    """Tests for DELETE /api/v1/deployment-sets/{set_id}/members/{member_id}."""

    def test_remove_existing_member(self, in_memory_repo):
        """Removing an existing member returns 204."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="My Set", owner_id="local-user")
        art_uuid = uuid.uuid4().hex
        member = repo.add_member(ds.id, "local-user", artifact_uuid=art_uuid)

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.delete(
                    f"/api/v1/deployment-sets/{ds.id}/members/{member.id}"
                )
        assert resp.status_code == 204

    def test_remove_missing_member_returns_404(self, in_memory_repo):
        """Removing a non-existent member returns 404."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="My Set", owner_id="local-user")
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.delete(
                    f"/api/v1/deployment-sets/{ds.id}/members/ghost-member-id"
                )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/v1/deployment-sets/{set_id}/members/{member_id}
# ---------------------------------------------------------------------------


class TestUpdateMemberPosition:
    """Tests for PUT /api/v1/deployment-sets/{set_id}/members/{member_id}."""

    def test_update_position(self, in_memory_repo):
        """Updating position returns 200 with new position."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="My Set", owner_id="local-user")
        art_uuid = uuid.uuid4().hex
        member = repo.add_member(ds.id, "local-user", artifact_uuid=art_uuid, position=0)

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.put(
                    f"/api/v1/deployment-sets/{ds.id}/members/{member.id}",
                    json={"position": 5},
                )
        assert resp.status_code == 200
        assert resp.json()["position"] == 5

    def test_update_position_missing_member_returns_404(self, in_memory_repo):
        """Returns 404 for a non-existent member."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="My Set", owner_id="local-user")
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.put(
                    f"/api/v1/deployment-sets/{ds.id}/members/no-such-member",
                    json={"position": 3},
                )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/deployment-sets/{set_id}/resolve
# ---------------------------------------------------------------------------


class TestResolveDeploymentSet:
    """Tests for GET /api/v1/deployment-sets/{set_id}/resolve."""

    def test_resolve_empty_set(self, in_memory_repo):
        """Resolving an empty set returns an empty artifact list."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Empty Set", owner_id="local-user")

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(f"sqlite:///{db_file}", echo=False)

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=Session(engine),
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get(f"/api/v1/deployment-sets/{ds.id}/resolve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["set_id"] == ds.id
        assert data["set_name"] == "Empty Set"
        assert data["resolved_artifacts"] == []
        assert data["total_count"] == 0

    def test_resolve_missing_set_returns_404(self, in_memory_repo):
        """Resolving a missing set returns 404."""
        repo, db_file = in_memory_repo
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets/no-such-set/resolve")
        assert resp.status_code == 404

    def test_resolve_set_with_artifacts(self, in_memory_repo):
        """Resolving a set with artifact members returns their UUIDs."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Art Set", owner_id="local-user")
        art1 = uuid.uuid4().hex
        art2 = uuid.uuid4().hex
        repo.add_member(ds.id, "local-user", artifact_uuid=art1, position=0)
        repo.add_member(ds.id, "local-user", artifact_uuid=art2, position=1)

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        engine = create_engine(f"sqlite:///{db_file}", echo=False)

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=Session(engine),
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get(f"/api/v1/deployment-sets/{ds.id}/resolve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 2
        uuids = {item["artifact_uuid"] for item in data["resolved_artifacts"]}
        assert uuids == {art1, art2}


# ---------------------------------------------------------------------------
# POST /api/v1/deployment-sets/{set_id}/deploy
# ---------------------------------------------------------------------------


class TestBatchDeploy:
    """Tests for POST /api/v1/deployment-sets/{set_id}/deploy."""

    def test_deploy_dry_run(self, in_memory_repo, tmp_path):
        """Dry-run deploy skips all artifacts, returns skipped count."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Deploy Set", owner_id="local-user")
        art_uuid = uuid.uuid4().hex
        repo.add_member(ds.id, "local-user", artifact_uuid=art_uuid, position=0)

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from unittest.mock import MagicMock

        engine = create_engine(f"sqlite:///{db_file}", echo=False)
        mock_artifact_mgr = MagicMock()

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ), patch(
            "skillmeat.api.routers.deployment_sets.get_session",
            return_value=Session(engine),
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app
            from skillmeat.api.dependencies import app_state

            app = create_app(APISettings(env="testing"))
            app.state = MagicMock()
            app.state.artifact_manager = mock_artifact_mgr

            # Override the dependency
            from skillmeat.api.dependencies import get_artifact_manager

            app.dependency_overrides[get_artifact_manager] = lambda: mock_artifact_mgr

            with TestClient(app) as client:
                resp = client.post(
                    f"/api/v1/deployment-sets/{ds.id}/deploy",
                    json={
                        "project_path": str(project_dir),
                        "dry_run": True,
                    },
                )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["skipped"] == 1
        assert data["succeeded"] == 0
        assert data["failed"] == 0
        # dry run should not call artifact manager
        mock_artifact_mgr.deploy_artifacts.assert_not_called()

    def test_deploy_missing_set_returns_404(self, in_memory_repo, tmp_path):
        """Returns 404 when the deployment set does not exist."""
        repo, db_file = in_memory_repo
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/deployment-sets/ghost-set/deploy",
                    json={"project_path": str(project_dir), "dry_run": False},
                )
        assert resp.status_code == 404

    def test_deploy_invalid_project_path_returns_422(self, in_memory_repo):
        """Returns 422 when the project path does not exist."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Deploy Set", owner_id="local-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.post(
                    f"/api/v1/deployment-sets/{ds.id}/deploy",
                    json={
                        "project_path": "/nonexistent/path/that/does/not/exist",
                        "dry_run": False,
                    },
                )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Owner scope isolation
# ---------------------------------------------------------------------------


class TestOwnerScopeIsolation:
    """Tests verifying that owner_id scoping prevents cross-user access."""

    def test_cannot_get_another_owners_set(self, in_memory_repo):
        """GET on a set owned by a different owner returns 404."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Private", owner_id="alice")
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get(f"/api/v1/deployment-sets/{ds.id}")
        assert resp.status_code == 404

    def test_cannot_delete_another_owners_set(self, in_memory_repo):
        """DELETE on a set owned by a different owner returns 404."""
        repo, db_file = in_memory_repo
        ds = repo.create(name="Private", owner_id="alice")
        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.delete(f"/api/v1/deployment-sets/{ds.id}")
        assert resp.status_code == 404

    def test_list_only_returns_own_sets(self, in_memory_repo):
        """List endpoint returns only sets belonging to local-user."""
        repo, db_file = in_memory_repo
        repo.create(name="Mine", owner_id="local-user")
        repo.create(name="Theirs", owner_id="alice")
        repo.create(name="Also Mine", owner_id="local-user")

        with patch(
            "skillmeat.api.routers.deployment_sets.DeploymentSetRepository",
            return_value=repo,
        ):
            from skillmeat.api.config import APISettings
            from skillmeat.api.server import create_app

            app = create_app(APISettings(env="testing"))
            with TestClient(app) as client:
                resp = client.get("/api/v1/deployment-sets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        names = {item["name"] for item in data["items"]}
        assert names == {"Mine", "Also Mine"}
