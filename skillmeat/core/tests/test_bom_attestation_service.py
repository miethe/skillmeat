"""Tests for BomAttestationService.

Covers:
- create_bom_with_attestation: creates both BomSnapshot and AttestationRecord
- create_bom_with_attestation without artifact_id: creates only BomSnapshot
- owner_type / owner_id correctly populated on AttestationRecord
- roles and scopes stored correctly
- create_attestation_for_artifact: standalone creation
- visibility defaults to 'private'
- Uses in-memory SQLite with only the tables required by the service
"""

from __future__ import annotations

import json
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import AttestationRecord, Artifact, Base, BomSnapshot
from skillmeat.core.services.bom_service import BomAttestationService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_NEEDED_TABLES = {
    "artifacts",
    "bom_snapshots",
    "attestation_records",
}


def _make_engine():
    """Create an in-memory SQLite engine with only the required tables."""
    engine = sa.create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    # Create only the tables needed by the service to keep the fixture fast.
    # We must respect FK order: projects → artifacts → attestation_records.
    # BomSnapshot has no FK so it can be created independently.
    # AttestationRecord.artifact_id → artifacts.id, so artifacts must exist.
    # Artifact.project_id → projects.id, so projects must exist too.
    with engine.begin() as conn:
        # Minimal projects table (required by Artifact FK)
        conn.execute(
            sa.text(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT ''
                )
                """
            )
        )

    # Use SQLAlchemy metadata to create only the three service-level tables.
    tables_to_create = [
        Base.metadata.tables[t]
        for t in _NEEDED_TABLES
        if t in Base.metadata.tables
    ]
    Base.metadata.create_all(engine, tables=tables_to_create)
    return engine


@pytest.fixture()
def session():
    """Yield a transactional SQLAlchemy session backed by in-memory SQLite."""
    engine = _make_engine()
    Session_ = sessionmaker(bind=engine)
    sess = Session_()
    yield sess
    sess.close()
    engine.dispose()


@pytest.fixture()
def service(session):
    """Return a BomAttestationService wired to the test session."""
    return BomAttestationService(session)


def _insert_artifact(session: Session, artifact_id: str) -> None:
    """Insert a minimal Artifact row so FK constraints are satisfied."""
    session.execute(
        sa.text(
            "INSERT INTO projects (id, name) VALUES (:id, 'test-project') "
            "ON CONFLICT(id) DO NOTHING"
        ),
        {"id": "proj-1"},
    )
    exists = session.execute(
        sa.text("SELECT 1 FROM artifacts WHERE id = :id"),
        {"id": artifact_id},
    ).fetchone()
    if not exists:
        session.execute(
            sa.text(
                """
                INSERT INTO artifacts
                    (id, uuid, project_id, name, type,
                     is_outdated, local_modified,
                     created_at, updated_at)
                VALUES
                    (:id, :uuid, 'proj-1', 'test-art', 'skill',
                     0, 0,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {"id": artifact_id, "uuid": uuid.uuid4().hex},
        )
    session.flush()


# ---------------------------------------------------------------------------
# Tests: create_bom_with_attestation
# ---------------------------------------------------------------------------


class TestCreateBomWithAttestation:
    """create_bom_with_attestation() happy-path and branching behaviour."""

    def test_creates_bom_snapshot(self, service, session):
        """A BomSnapshot row is created and flushed when called."""
        bom_json = json.dumps({"schema_version": "1.0.0", "artifacts": []})
        snapshot, _ = service.create_bom_with_attestation(
            bom_json=bom_json,
            project_id="proj-abc",
        )

        assert snapshot.id is not None
        assert snapshot.bom_json == bom_json
        assert snapshot.project_id == "proj-abc"

        row = session.query(BomSnapshot).get(snapshot.id)
        assert row is not None
        assert row.bom_json == bom_json

    def test_creates_attestation_when_artifact_id_given(self, service, session):
        """Both BomSnapshot and AttestationRecord are created when artifact_id is set."""
        _insert_artifact(session, "skill:my-skill")
        bom_json = json.dumps({"schema_version": "1.0.0"})

        snapshot, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="skill:my-skill",
            owner_type="user",
            owner_id="alice",
        )

        assert snapshot.id is not None
        assert attestation is not None
        assert attestation.id is not None
        assert attestation.artifact_id == "skill:my-skill"

    def test_no_attestation_when_artifact_id_omitted(self, service, session):
        """No AttestationRecord is created when artifact_id is None."""
        bom_json = json.dumps({"schema_version": "1.0.0"})

        snapshot, attestation = service.create_bom_with_attestation(bom_json=bom_json)

        assert snapshot is not None
        assert attestation is None
        # Confirm no attestation rows exist in the DB.
        count = session.query(AttestationRecord).count()
        assert count == 0

    def test_owner_type_and_owner_id_on_snapshot(self, service, session):
        """owner_type is stored on BomSnapshot."""
        bom_json = json.dumps({})
        snapshot, _ = service.create_bom_with_attestation(
            bom_json=bom_json,
            owner_type="team",
        )
        assert snapshot.owner_type == "team"

    def test_owner_type_and_owner_id_on_attestation(self, service, session):
        """owner_type and owner_id are correctly stored on AttestationRecord."""
        _insert_artifact(session, "command:deploy")
        bom_json = json.dumps({})

        _, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="command:deploy",
            owner_type="team",
            owner_id="backend-team",
        )

        assert attestation.owner_type == "team"
        assert attestation.owner_id == "backend-team"

    def test_roles_stored_correctly(self, service, session):
        """roles list is persisted verbatim on the AttestationRecord."""
        _insert_artifact(session, "skill:canvas")
        bom_json = json.dumps({})
        roles = ["team_admin", "team_member"]

        _, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="skill:canvas",
            owner_id="carol",
            roles=roles,
        )
        session.commit()

        # Re-query to verify persistence
        row = session.query(AttestationRecord).get(attestation.id)
        assert row.roles == roles

    def test_scopes_stored_correctly(self, service, session):
        """scopes list is persisted verbatim on the AttestationRecord."""
        _insert_artifact(session, "agent:planner")
        bom_json = json.dumps({})
        scopes = ["read", "write", "deploy"]

        _, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="agent:planner",
            owner_id="dave",
            scopes=scopes,
        )
        session.commit()

        row = session.query(AttestationRecord).get(attestation.id)
        assert row.scopes == scopes

    def test_visibility_defaults_to_private(self, service, session):
        """Visibility defaults to 'private' when not explicitly supplied."""
        _insert_artifact(session, "skill:default-vis")
        bom_json = json.dumps({})

        _, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="skill:default-vis",
            owner_id="eve",
        )

        assert attestation.visibility == "private"

    def test_explicit_visibility_stored(self, service, session):
        """Explicit visibility value is stored as-is."""
        _insert_artifact(session, "skill:public-art")
        bom_json = json.dumps({})

        _, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="skill:public-art",
            owner_id="frank",
            visibility="public",
        )

        assert attestation.visibility == "public"

    def test_commit_sha_stored_on_snapshot(self, service, session):
        """commit_sha is preserved on the created BomSnapshot."""
        bom_json = json.dumps({})
        sha = "abc123def456"

        snapshot, _ = service.create_bom_with_attestation(
            bom_json=bom_json,
            commit_sha=sha,
        )

        assert snapshot.commit_sha == sha

    def test_roles_none_stored_as_none(self, service, session):
        """When roles is None the column stays NULL / None."""
        _insert_artifact(session, "skill:null-roles")
        bom_json = json.dumps({})

        _, attestation = service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="skill:null-roles",
            owner_id="grace",
            roles=None,
            scopes=None,
        )
        session.commit()

        row = session.query(AttestationRecord).get(attestation.id)
        assert row.roles is None
        assert row.scopes is None


# ---------------------------------------------------------------------------
# Tests: create_attestation_for_artifact (standalone)
# ---------------------------------------------------------------------------


class TestCreateAttestationForArtifact:
    """Standalone create_attestation_for_artifact() tests."""

    def test_returns_attestation_record_instance(self, service, session):
        """Returns an AttestationRecord ORM instance."""
        _insert_artifact(session, "skill:standalone")
        rec = service.create_attestation_for_artifact(
            artifact_id="skill:standalone",
            owner_type="user",
            owner_id="henry",
        )
        assert isinstance(rec, AttestationRecord)

    def test_added_to_session(self, service, session):
        """The record is added to the session so a subsequent flush persists it."""
        _insert_artifact(session, "skill:session-check")
        rec = service.create_attestation_for_artifact(
            artifact_id="skill:session-check",
            owner_type="user",
            owner_id="iris",
        )
        session.flush()
        assert rec.id is not None

    def test_persisted_after_commit(self, service, session):
        """Attestation row survives a commit and can be re-queried."""
        _insert_artifact(session, "skill:persist-test")
        rec = service.create_attestation_for_artifact(
            artifact_id="skill:persist-test",
            owner_type="enterprise",
            owner_id="acme-corp",
            roles=["system_admin"],
            scopes=["*"],
            visibility="team",
        )
        session.commit()

        row = session.query(AttestationRecord).get(rec.id)
        assert row.owner_type == "enterprise"
        assert row.owner_id == "acme-corp"
        assert row.roles == ["system_admin"]
        assert row.scopes == ["*"]
        assert row.visibility == "team"

    def test_visibility_defaults_to_private(self, service, session):
        """Standalone helper also defaults visibility to 'private'."""
        _insert_artifact(session, "skill:vis-default")
        rec = service.create_attestation_for_artifact(
            artifact_id="skill:vis-default",
            owner_type="user",
            owner_id="jack",
        )
        assert rec.visibility == "private"

    def test_multiple_attestations_for_same_artifact(self, service, session):
        """Multiple AttestationRecords can reference the same artifact."""
        _insert_artifact(session, "skill:multi-owner")

        rec1 = service.create_attestation_for_artifact(
            artifact_id="skill:multi-owner",
            owner_type="user",
            owner_id="user-a",
        )
        rec2 = service.create_attestation_for_artifact(
            artifact_id="skill:multi-owner",
            owner_type="team",
            owner_id="team-b",
        )
        session.flush()

        assert rec1.id != rec2.id
        count = (
            session.query(AttestationRecord)
            .filter_by(artifact_id="skill:multi-owner")
            .count()
        )
        assert count == 2
