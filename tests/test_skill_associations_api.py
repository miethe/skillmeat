"""Integration tests for skill-specific behavior of GET /api/v1/artifacts/{artifact_id}/associations.

Tests cover:
- Skill with members: companion CompositeArtifact (composite_type='skill') with
  membership rows → children are returned correctly.
- Skill with no members: skill artifact exists but no companion CompositeArtifact →
  empty children list (no error).
- Non-skill artifact (plugin): existing plugin behavior is unchanged.
- Missing artifact (404): non-existent artifact returns 404.
"""

from __future__ import annotations

import json
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
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database for skill association tests."""
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


# ---------------------------------------------------------------------------
# Scenario-specific seed helpers
# ---------------------------------------------------------------------------


def _seed_skill_with_members(db_session) -> Dict[str, Any]:
    """Seed DB with a skill artifact + companion CompositeArtifact + two child members.

    Graph::

        skill:my-skill  (Artifact, type='skill')
            └── CompositeArtifact(composite_type='skill',
                                  metadata_json='{"artifact_uuid": "<skill-uuid>"}')
                    |-- command:sub-cmd   (child, relationship_type='contains')
                    |-- agent:sub-agent   (child, relationship_type='contains')

    Returns a dict with identifiers for assertions.
    """
    col_id = _make_uuid()
    proj_id = "proj-skill-assoc-test"
    skill_uuid = _make_uuid()
    skill_id = "skill:my-skill"
    composite_id = "composite:my-skill-composite"

    cmd_uuid = _make_uuid()
    agent_uuid = _make_uuid()

    db_session.add(
        Project(
            id=proj_id,
            name="Skill Assoc Test Project",
            path="/tmp/skill-assoc-test",
            status="active",
        )
    )
    db_session.add(Collection(id=col_id, name="default"))

    # The skill artifact itself
    db_session.add(
        Artifact(
            id=skill_id,
            uuid=skill_uuid,
            name="my-skill",
            type="skill",
            project_id=proj_id,
        )
    )

    # Child artifacts embedded in the skill directory
    db_session.add(
        Artifact(
            id="command:sub-cmd",
            uuid=cmd_uuid,
            name="sub-cmd",
            type="command",
            project_id=proj_id,
        )
    )
    db_session.add(
        Artifact(
            id="agent:sub-agent",
            uuid=agent_uuid,
            name="sub-agent",
            type="agent",
            project_id=proj_id,
        )
    )

    # Companion CompositeArtifact whose metadata_json encodes the skill's UUID
    db_session.add(
        CompositeArtifact(
            id=composite_id,
            collection_id=col_id,
            composite_type="skill",
            display_name="My Skill Composite",
            metadata_json=json.dumps({"artifact_uuid": skill_uuid}),
        )
    )

    # Membership edges
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=cmd_uuid,
            relationship_type="contains",
            created_at=_utcnow(),
        )
    )
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=agent_uuid,
            relationship_type="contains",
            created_at=_utcnow(),
        )
    )

    db_session.commit()

    return {
        "col_id": col_id,
        "proj_id": proj_id,
        "skill_id": skill_id,
        "skill_uuid": skill_uuid,
        "composite_id": composite_id,
        "cmd_uuid": cmd_uuid,
        "agent_uuid": agent_uuid,
    }


def _seed_skill_no_members(db_session) -> Dict[str, Any]:
    """Seed DB with a skill artifact but no companion CompositeArtifact."""
    col_id = _make_uuid()
    proj_id = "proj-skill-no-members"
    skill_uuid = _make_uuid()
    skill_id = "skill:lonely-skill"

    db_session.add(
        Project(
            id=proj_id,
            name="Skill No Members Project",
            path="/tmp/skill-no-members",
            status="active",
        )
    )
    db_session.add(Collection(id=col_id, name="default"))

    db_session.add(
        Artifact(
            id=skill_id,
            uuid=skill_uuid,
            name="lonely-skill",
            type="skill",
            project_id=proj_id,
        )
    )

    db_session.commit()

    return {
        "col_id": col_id,
        "proj_id": proj_id,
        "skill_id": skill_id,
        "skill_uuid": skill_uuid,
    }


def _seed_plugin_with_members(db_session) -> Dict[str, Any]:
    """Seed DB with a plugin-type composite and two child artifacts (non-skill scenario)."""
    col_id = _make_uuid()
    proj_id = "proj-plugin-assoc-test"
    composite_id = "composite:my-plugin"
    skill_uuid = _make_uuid()
    cmd_uuid = _make_uuid()

    db_session.add(
        Project(
            id=proj_id,
            name="Plugin Assoc Test Project",
            path="/tmp/plugin-assoc-test",
            status="active",
        )
    )
    db_session.add(Collection(id=col_id, name="default"))

    db_session.add(
        Artifact(
            id="skill:plugin-skill",
            uuid=skill_uuid,
            name="plugin-skill",
            type="skill",
            project_id=proj_id,
        )
    )
    db_session.add(
        Artifact(
            id="command:plugin-cmd",
            uuid=cmd_uuid,
            name="plugin-cmd",
            type="command",
            project_id=proj_id,
        )
    )
    db_session.add(
        CompositeArtifact(
            id=composite_id,
            collection_id=col_id,
            composite_type="plugin",
            display_name="My Plugin",
        )
    )
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=skill_uuid,
            relationship_type="contains",
            created_at=_utcnow(),
        )
    )
    db_session.add(
        CompositeMembership(
            collection_id=col_id,
            composite_id=composite_id,
            child_artifact_uuid=cmd_uuid,
            relationship_type="requires",
            created_at=_utcnow(),
        )
    )

    db_session.commit()

    return {
        "col_id": col_id,
        "proj_id": proj_id,
        "composite_id": composite_id,
        "skill_uuid": skill_uuid,
        "cmd_uuid": cmd_uuid,
    }


# ---------------------------------------------------------------------------
# App fixture factory
# ---------------------------------------------------------------------------


def _build_app(temp_db: str, col_id: str):
    """Build a FastAPI TestClient app with auth bypassed."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token

    settings = APISettings(env=Environment.TESTING, api_key_enabled=False)
    application = create_app(settings)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[verify_token] = lambda: "test-token"

    # Store test metadata on app state for helpers
    application.state._test_temp_db = temp_db
    application.state._test_col_id = col_id
    return application


def _override_collection_mgr(
    application, collection_name: str, artifact_id: str, exists: bool = True
):
    """Override the CollectionManager dependency for a single test request."""
    from skillmeat.api.dependencies import get_collection_manager

    artifact_type_str, artifact_name = artifact_id.split(":", 1)

    mock_artifact = MagicMock()
    mock_artifact.name = artifact_name
    mock_artifact.type = artifact_type_str

    mock_collection = MagicMock()
    mock_collection.find_artifact.return_value = mock_artifact if exists else None

    mock_mgr = MagicMock()
    mock_mgr.get_active_collection_name.return_value = collection_name
    mock_mgr.list_collections.return_value = [collection_name]
    mock_mgr.load_collection.return_value = mock_collection

    application.dependency_overrides[get_collection_manager] = lambda: mock_mgr


def _make_patches(application):
    """Return patch context managers for CompositeMembershipRepository and get_session.

    Mirrors the approach used in test_associations_api.py so both the
    composite-membership repo and the Collection DB lookup resolve against
    the seeded temp database.
    """
    temp_db = application.state._test_temp_db

    from skillmeat.cache.composite_repository import CompositeMembershipRepository
    from sqlalchemy.orm import sessionmaker

    with patch("skillmeat.cache.migrations.run_migrations"):
        real_repo = CompositeMembershipRepository(db_path=temp_db)

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


def _run_request(app, artifact_id: str, params=None):
    """Apply patches and send GET request to the associations endpoint."""
    p1, p2 = _make_patches(app)
    with p1, p2:
        with TestClient(app) as client:
            return client.get(
                f"/api/v1/artifacts/{artifact_id}/associations",
                params=params or {},
            )


# ---------------------------------------------------------------------------
# Test: skill artifact WITH companion composite members
# ---------------------------------------------------------------------------


class TestSkillAssociationsWithMembers:
    """Skill artifact that has a companion CompositeArtifact returns children."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db, db_session):
        self.seeded = _seed_skill_with_members(db_session)
        self.app = _build_app(temp_db, self.seeded["col_id"])
        _override_collection_mgr(self.app, "default", self.seeded["skill_id"])

    def test_associations_skill_with_members_returns_children(self):
        """Skill with companion composite returns its embedded member artifacts."""
        resp = _run_request(self.app, self.seeded["skill_id"])

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["artifact_id"] == self.seeded["skill_id"]
        # A plain skill that belongs to no composite has no parents
        assert body["parents"] == []
        # Two children seeded through the skill-type composite
        assert len(body["children"]) == 2
        child_ids = {c["artifact_id"] for c in body["children"]}
        assert "command:sub-cmd" in child_ids
        assert "agent:sub-agent" in child_ids

    def test_associations_skill_children_have_correct_schema(self):
        """Each child item must have the required AssociationItemDTO fields."""
        resp = _run_request(self.app, self.seeded["skill_id"])

        assert resp.status_code == status.HTTP_200_OK
        for child in resp.json()["children"]:
            assert "artifact_id" in child
            assert "artifact_name" in child
            assert "artifact_type" in child
            assert "relationship_type" in child
            assert "created_at" in child

    def test_associations_skill_children_relationship_type(self):
        """Children returned via skill composite have the seeded relationship_type."""
        resp = _run_request(self.app, self.seeded["skill_id"])

        assert resp.status_code == status.HTTP_200_OK
        for child in resp.json()["children"]:
            assert child["relationship_type"] == "contains"

    def test_associations_skill_include_children_false_returns_empty(self):
        """include_children=false suppresses skill composite children."""
        resp = _run_request(
            self.app,
            self.seeded["skill_id"],
            params={"include_children": "false"},
        )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["children"] == []


# ---------------------------------------------------------------------------
# Test: skill artifact WITHOUT companion composite (no members)
# ---------------------------------------------------------------------------


class TestSkillAssociationsNoMembers:
    """Skill artifact with no companion CompositeArtifact returns empty children."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db, db_session):
        self.seeded = _seed_skill_no_members(db_session)
        self.app = _build_app(temp_db, self.seeded["col_id"])
        _override_collection_mgr(self.app, "default", self.seeded["skill_id"])

    def test_associations_skill_no_members_returns_empty_children(self):
        """Skill with no companion composite returns empty children list, not 404."""
        resp = _run_request(self.app, self.seeded["skill_id"])

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["artifact_id"] == self.seeded["skill_id"]
        assert body["parents"] == []
        assert body["children"] == []

    def test_associations_skill_no_members_response_has_correct_schema(self):
        """Empty associations response still contains required top-level keys."""
        resp = _run_request(self.app, self.seeded["skill_id"])

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert "artifact_id" in body
        assert "parents" in body
        assert "children" in body


# ---------------------------------------------------------------------------
# Test: non-skill (plugin) artifact — existing behavior unchanged
# ---------------------------------------------------------------------------


class TestPluginAssociationsUnchanged:
    """Plugin-type composite associations continue to work (regression guard)."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db, db_session):
        self.seeded = _seed_plugin_with_members(db_session)
        self.app = _build_app(temp_db, self.seeded["col_id"])
        _override_collection_mgr(self.app, "default", self.seeded["composite_id"])

    def test_associations_plugin_returns_children(self):
        """Plugin composite returns its child skill and command artifacts."""
        resp = _run_request(self.app, self.seeded["composite_id"])

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["artifact_id"] == self.seeded["composite_id"]
        assert body["parents"] == []
        assert len(body["children"]) == 2
        child_ids = {c["artifact_id"] for c in body["children"]}
        assert "skill:plugin-skill" in child_ids
        assert "command:plugin-cmd" in child_ids

    def test_associations_plugin_child_sees_parent(self):
        """A child artifact of a plugin composite has that composite as a parent."""
        _override_collection_mgr(self.app, "default", "skill:plugin-skill")

        resp = _run_request(self.app, "skill:plugin-skill")

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert len(body["parents"]) == 1
        assert body["parents"][0]["artifact_id"] == self.seeded["composite_id"]
        # A plain skill child has no children of its own through the plugin path
        assert body["children"] == []


# ---------------------------------------------------------------------------
# Test: 404 for non-existent artifact
# ---------------------------------------------------------------------------


class TestAssociationsMissingArtifact:
    """Requesting associations for a non-existent artifact returns 404."""

    @pytest.fixture(autouse=True)
    def setup(self, temp_db, db_session):
        # Seed a minimal collection so get_session has a valid DB
        col_id = _make_uuid()
        proj_id = "proj-missing"
        db_session.add(
            Project(
                id=proj_id,
                name="Missing Test Project",
                path="/tmp/missing-test",
                status="active",
            )
        )
        db_session.add(Collection(id=col_id, name="default"))
        db_session.commit()
        self.col_id = col_id
        self.app = _build_app(temp_db, col_id)

    def test_associations_missing_skill_returns_404(self):
        """GET associations for a skill that does not exist returns 404."""
        _override_collection_mgr(
            self.app, "default", "skill:nonexistent-skill", exists=False
        )

        resp = _run_request(self.app, "skill:nonexistent-skill")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()

    def test_associations_missing_plugin_returns_404(self):
        """GET associations for a composite that does not exist returns 404."""
        _override_collection_mgr(
            self.app, "default", "composite:ghost-plugin", exists=False
        )

        resp = _run_request(self.app, "composite:ghost-plugin")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"].lower()
