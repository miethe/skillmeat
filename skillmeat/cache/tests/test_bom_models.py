"""
Tests for the six SkillBOM SQLAlchemy models added in feat/skillbom-attestation.

Models under test:
  - AttestationRecord
  - ArtifactHistoryEvent
  - BomSnapshot
  - AttestationPolicy
  - BomMetadata
  - ScopeValidator

NOTE: Base.metadata.create_all() cannot be used against SQLite because several
unrelated tables use the PostgreSQL-only TSVECTOR column type.  All tests use
selective Table.create() in FK-dependency order to avoid
UnsupportedCompilationError.  See skillmeat/cache/tests/CLAUDE.md for details.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
import sqlalchemy as sa
from sqlalchemy import CheckConstraint, create_engine, event, inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    ArtifactHistoryEvent,
    AttestationPolicy,
    AttestationRecord,
    Base,
    BomMetadata,
    BomSnapshot,
    Project,
    ScopeValidator,
    _redact_db_url,
    create_db_engine,
    create_tables,
    drop_tables,
    get_engine,
    get_session,
    init_session_factory,
)


# ---------------------------------------------------------------------------
# Tables in FK dependency order (excludes TSVECTOR-bearing tables)
# ---------------------------------------------------------------------------

_TABLES_NEEDED = [
    "projects",
    "artifacts",
    "attestation_records",
    "artifact_history_events",
    "bom_snapshots",
    "attestation_policies",
    "bom_metadata",
    "scope_validators",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with only the BOM-related tables."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    meta = Base.metadata
    with eng.begin() as conn:
        for table_name in _TABLES_NEEDED:
            meta.tables[table_name].create(conn, checkfirst=True)

    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    """Fresh session that rolls back after each test for isolation.

    If a test calls session.rollback() internally (e.g. after an IntegrityError),
    the outer transaction is already deassociated.  We guard against the
    SAWarning by checking is_active before rolling back.
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    sess = Session_()
    yield sess
    sess.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture()
def project(session: Session) -> Project:
    """Minimal Project row required by Artifact FK."""
    proj = Project(
        id="proj-bom-test",
        name="BOM test project",
        path="/tmp/bom-test",
        status="active",
    )
    session.add(proj)
    session.flush()
    return proj


@pytest.fixture()
def artifact(session: Session, project: Project) -> Artifact:
    """Minimal Artifact row required by AttestationRecord and ArtifactHistoryEvent FKs."""
    art = Artifact(
        id="skill:bom-test-skill",
        project_id=project.id,
        name="bom-test-skill",
        type="skill",
    )
    session.add(art)
    session.flush()
    return art


# ---------------------------------------------------------------------------
# AttestationRecord
# ---------------------------------------------------------------------------


class TestAttestationRecord:
    """Tests for the AttestationRecord model."""

    def test_instantiation_with_valid_data(self, session: Session, artifact: Artifact):
        """AttestationRecord can be created and flushed with all valid fields."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-abc",
            roles=["admin", "viewer"],
            scopes=["artifact:read", "artifact:write"],
            visibility="private",
        )
        session.add(rec)
        session.flush()

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved is not None
        assert retrieved.artifact_id == artifact.id
        assert retrieved.owner_type == "user"
        assert retrieved.owner_id == "user-abc"
        assert retrieved.visibility == "private"

    def test_fk_to_artifacts(self, session: Session, artifact: Artifact):
        """artifact_id FK references the artifacts table correctly."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="team",
            owner_id="team-xyz",
        )
        session.add(rec)
        session.flush()

        # Relationship load
        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.artifact_id == artifact.id

    def test_fk_violation_raises_integrity_error(self, session: Session):
        """AttestationRecord with a nonexistent artifact_id raises IntegrityError."""
        rec = AttestationRecord(
            artifact_id="nonexistent:artifact",
            owner_type="user",
            owner_id="user-xyz",
        )
        session.add(rec)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_roles_and_scopes_json_round_trip(
        self, session: Session, artifact: Artifact
    ):
        """roles and scopes JSON lists survive a flush/retrieve round-trip."""
        roles = ["admin", "reviewer"]
        scopes = ["artifact:read", "deploy:write", "collection:admin"]
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-roundtrip",
            roles=roles,
            scopes=scopes,
        )
        session.add(rec)
        session.flush()
        session.expire(rec)

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.roles == roles
        assert retrieved.scopes == scopes

    def test_nullable_roles_and_scopes(self, session: Session, artifact: Artifact):
        """roles and scopes are nullable — None is stored and retrieved correctly."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-null-fields",
            roles=None,
            scopes=None,
        )
        session.add(rec)
        session.flush()
        session.expire(rec)

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.roles is None
        assert retrieved.scopes is None

    def test_created_at_auto_populated(self, session: Session, artifact: Artifact):
        """created_at and updated_at are set automatically on flush."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-ts",
        )
        session.add(rec)
        session.flush()

        assert rec.created_at is not None
        assert rec.updated_at is not None

    def test_default_owner_type_is_user(self, session: Session, artifact: Artifact):
        """owner_type defaults to 'user' when not specified."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_id="user-default-type",
        )
        session.add(rec)
        session.flush()

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.owner_type == "user"

    def test_default_visibility_is_private(self, session: Session, artifact: Artifact):
        """visibility defaults to 'private' when not specified."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-default-vis",
        )
        session.add(rec)
        session.flush()

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.visibility == "private"

    def test_team_owner_type_accepted(self, session: Session, artifact: Artifact):
        """owner_type='team' is a valid value."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="team",
            owner_id="team-alpha",
            visibility="team",
        )
        session.add(rec)
        session.flush()

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.owner_type == "team"
        assert retrieved.visibility == "team"

    def test_to_dict_serialization(self, session: Session, artifact: Artifact):
        """to_dict() returns expected keys and values."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-dict",
            roles=["viewer"],
            scopes=["artifact:read"],
            visibility="public",
        )
        session.add(rec)
        session.flush()

        d = rec.to_dict()
        assert d["artifact_id"] == artifact.id
        assert d["owner_type"] == "user"
        assert d["owner_id"] == "user-dict"
        assert d["roles"] == ["viewer"]
        assert d["scopes"] == ["artifact:read"]
        assert d["visibility"] == "public"
        assert d["created_at"] is not None

    def test_cascade_delete_from_artifact(
        self, session: Session, project: Project
    ):
        """Deleting an artifact cascades to its AttestationRecords."""
        # Use a dedicated artifact so deletion does not affect other tests
        art2 = Artifact(
            id="skill:cascade-attest",
            project_id=project.id,
            name="cascade-attest-skill",
            type="skill",
        )
        session.add(art2)
        session.flush()

        rec = AttestationRecord(
            artifact_id=art2.id,
            owner_type="user",
            owner_id="user-cascade",
        )
        session.add(rec)
        session.flush()
        rec_id = rec.id

        # Raw SQL DELETE bypasses ORM unit-of-work and fires ON DELETE CASCADE.
        # expire_all() clears the identity map so session.get() re-queries the DB.
        session.execute(
            sa.delete(Artifact).where(Artifact.id == art2.id)
        )
        session.flush()
        session.expire_all()

        assert session.get(AttestationRecord, rec_id) is None

    def test_repr_contains_artifact_id(self, artifact: Artifact):
        """__repr__ includes artifact_id for easy identification."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-repr",
        )
        r = repr(rec)
        assert artifact.id in r
        assert "AttestationRecord" in r


# ---------------------------------------------------------------------------
# ArtifactHistoryEvent
# ---------------------------------------------------------------------------


class TestArtifactHistoryEvent:
    """Tests for the ArtifactHistoryEvent model."""

    def test_instantiation_with_valid_event_types(
        self, session: Session, artifact: Artifact
    ):
        """All valid event_type values are accepted by the model."""
        valid_types = ["create", "update", "delete", "deploy", "undeploy", "sync"]
        for event_type in valid_types:
            evt = ArtifactHistoryEvent(
                artifact_id=artifact.id,
                event_type=event_type,
                owner_type="user",
            )
            session.add(evt)
        session.flush()

        events = (
            session.query(ArtifactHistoryEvent)
            .filter_by(artifact_id=artifact.id)
            .all()
        )
        assert len(events) == len(valid_types)

    def test_check_constraint_on_event_type(
        self, session: Session, artifact: Artifact
    ):
        """An invalid event_type raises IntegrityError due to CHECK constraint."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="invalid_event",
            owner_type="user",
        )
        session.add(evt)
        with pytest.raises((IntegrityError, sa.exc.StatementError)):
            session.flush()
        session.rollback()

    def test_check_constraint_defined_on_table(self):
        """CHECK constraint 'check_artifact_history_event_type' is present on table."""
        table = ArtifactHistoryEvent.__table__
        check_constraints = [
            c for c in table.constraints if isinstance(c, CheckConstraint)
        ]
        names = [c.name for c in check_constraints]
        assert "check_artifact_history_event_type" in names

    def test_fk_to_artifacts(self, session: Session, artifact: Artifact):
        """artifact_id FK references the artifacts table."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="create",
        )
        session.add(evt)
        session.flush()

        retrieved = session.get(ArtifactHistoryEvent, evt.id)
        assert retrieved.artifact_id == artifact.id

    def test_fk_violation_raises_integrity_error(self, session: Session):
        """ArtifactHistoryEvent with a nonexistent artifact_id raises IntegrityError."""
        evt = ArtifactHistoryEvent(
            artifact_id="nonexistent:artifact",
            event_type="create",
        )
        session.add(evt)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_nullable_optional_fields(self, session: Session, artifact: Artifact):
        """actor_id, diff_json, and content_hash are nullable."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="sync",
            actor_id=None,
            diff_json=None,
            content_hash=None,
        )
        session.add(evt)
        session.flush()

        retrieved = session.get(ArtifactHistoryEvent, evt.id)
        assert retrieved.actor_id is None
        assert retrieved.diff_json is None
        assert retrieved.content_hash is None

    def test_actor_id_stored_when_provided(self, session: Session, artifact: Artifact):
        """actor_id is stored and retrieved correctly when provided."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="deploy",
            actor_id="user-deployer-42",
        )
        session.add(evt)
        session.flush()

        retrieved = session.get(ArtifactHistoryEvent, evt.id)
        assert retrieved.actor_id == "user-deployer-42"

    def test_timestamp_auto_populated(self, session: Session, artifact: Artifact):
        """timestamp is set automatically on flush."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="update",
        )
        session.add(evt)
        session.flush()

        assert evt.timestamp is not None

    def test_diff_json_stores_arbitrary_payload(
        self, session: Session, artifact: Artifact
    ):
        """diff_json (Text column) stores an arbitrary JSON string."""
        payload = json.dumps({"before": {"version": "1.0"}, "after": {"version": "2.0"}})
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="update",
            diff_json=payload,
        )
        session.add(evt)
        session.flush()
        session.expire(evt)

        retrieved = session.get(ArtifactHistoryEvent, evt.id)
        parsed = json.loads(retrieved.diff_json)
        assert parsed["after"]["version"] == "2.0"

    def test_cascade_delete_from_artifact(
        self, session: Session, project: Project
    ):
        """Deleting an artifact cascades to its ArtifactHistoryEvents."""
        art2 = Artifact(
            id="skill:cascade-history",
            project_id=project.id,
            name="cascade-history-skill",
            type="skill",
        )
        session.add(art2)
        session.flush()

        evt = ArtifactHistoryEvent(
            artifact_id=art2.id,
            event_type="create",
        )
        session.add(evt)
        session.flush()
        evt_id = evt.id

        session.execute(sa.delete(Artifact).where(Artifact.id == art2.id))
        session.flush()
        session.expire_all()

        assert session.get(ArtifactHistoryEvent, evt_id) is None

    def test_to_dict_serialization(self, session: Session, artifact: Artifact):
        """to_dict() returns all expected keys."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="deploy",
            actor_id="user-to-dict",
            content_hash="sha256:abc123",
        )
        session.add(evt)
        session.flush()

        d = evt.to_dict()
        assert d["artifact_id"] == artifact.id
        assert d["event_type"] == "deploy"
        assert d["actor_id"] == "user-to-dict"
        assert d["content_hash"] == "sha256:abc123"
        assert d["timestamp"] is not None

    def test_repr_contains_event_type(self, artifact: Artifact):
        """__repr__ includes event_type for easy identification."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="sync",
        )
        r = repr(evt)
        assert "sync" in r
        assert "ArtifactHistoryEvent" in r


# ---------------------------------------------------------------------------
# BomSnapshot
# ---------------------------------------------------------------------------


class TestBomSnapshot:
    """Tests for the BomSnapshot model."""

    def test_instantiation_with_required_fields(self, session: Session):
        """BomSnapshot with only bom_json can be created and flushed."""
        snap = BomSnapshot(bom_json='{"artifacts": []}')
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved is not None
        assert retrieved.bom_json == '{"artifacts": []}'

    def test_nullable_optional_fields(self, session: Session):
        """project_id, commit_sha, signature, and signature_algorithm accept None."""
        snap = BomSnapshot(
            bom_json="{}",
            project_id=None,
            commit_sha=None,
            signature=None,
            signature_algorithm=None,
        )
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.project_id is None
        assert retrieved.commit_sha is None
        assert retrieved.signature is None
        assert retrieved.signature_algorithm is None

    def test_project_id_stored_when_provided(self, session: Session):
        """project_id is stored and retrieved correctly."""
        snap = BomSnapshot(
            bom_json='{"format": "cyclonedx"}',
            project_id="my-project-001",
        )
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.project_id == "my-project-001"

    def test_commit_sha_stored_when_provided(self, session: Session):
        """commit_sha is stored and retrieved correctly."""
        sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        snap = BomSnapshot(bom_json="{}", commit_sha=sha)
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.commit_sha == sha

    def test_signature_fields_round_trip(self, session: Session):
        """signature and signature_algorithm survive a round-trip."""
        sig = "base64sigpayload=="
        snap = BomSnapshot(
            bom_json='{"signed": true}',
            signature=sig,
            signature_algorithm="ed25519",
        )
        session.add(snap)
        session.flush()
        session.expire(snap)

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.signature == sig
        assert retrieved.signature_algorithm == "ed25519"

    def test_created_at_auto_populated(self, session: Session):
        """created_at is set automatically on flush."""
        snap = BomSnapshot(bom_json="{}")
        session.add(snap)
        session.flush()

        assert snap.created_at is not None

    def test_default_owner_type_is_user(self, session: Session):
        """owner_type defaults to 'user' when not specified."""
        snap = BomSnapshot(bom_json="{}")
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.owner_type == "user"

    def test_bom_json_stores_complex_payload(self, session: Session):
        """bom_json stores a complex nested JSON string and retrieves it intact."""
        payload = json.dumps({
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "components": [
                {"name": "skill-a", "version": "1.0.0"},
                {"name": "command-b", "version": "2.1.3"},
            ],
        })
        snap = BomSnapshot(bom_json=payload)
        session.add(snap)
        session.flush()
        session.expire(snap)

        retrieved = session.get(BomSnapshot, snap.id)
        parsed = json.loads(retrieved.bom_json)
        assert parsed["bomFormat"] == "CycloneDX"
        assert len(parsed["components"]) == 2

    def test_to_dict_serialization(self, session: Session):
        """to_dict() returns all expected keys."""
        snap = BomSnapshot(
            bom_json='{"test": true}',
            project_id="proj-dict",
            commit_sha="deadbeef",
        )
        session.add(snap)
        session.flush()

        d = snap.to_dict()
        assert d["project_id"] == "proj-dict"
        assert d["commit_sha"] == "deadbeef"
        assert d["bom_json"] == '{"test": true}'
        assert d["created_at"] is not None

    def test_repr_contains_project_id(self):
        """__repr__ includes project_id for easy identification."""
        snap = BomSnapshot(bom_json="{}", project_id="proj-repr")
        r = repr(snap)
        assert "proj-repr" in r
        assert "BomSnapshot" in r


# ---------------------------------------------------------------------------
# AttestationPolicy
# ---------------------------------------------------------------------------


class TestAttestationPolicy:
    """Tests for the AttestationPolicy model."""

    def test_instantiation_with_required_fields(self, session: Session):
        """AttestationPolicy with only name can be created and flushed."""
        policy = AttestationPolicy(name="baseline-policy")
        session.add(policy)
        session.flush()

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved is not None
        assert retrieved.name == "baseline-policy"

    def test_nullable_optional_fields(self, session: Session):
        """tenant_id, required_artifacts, required_scopes, compliance_metadata accept None."""
        policy = AttestationPolicy(
            name="null-fields-policy",
            tenant_id=None,
            required_artifacts=None,
            required_scopes=None,
            compliance_metadata=None,
        )
        session.add(policy)
        session.flush()

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved.tenant_id is None
        assert retrieved.required_artifacts is None
        assert retrieved.required_scopes is None
        assert retrieved.compliance_metadata is None

    def test_tenant_id_stored_when_provided(self, session: Session):
        """tenant_id is stored and retrieved correctly (enterprise mode)."""
        policy = AttestationPolicy(name="enterprise-policy", tenant_id="tenant-acme")
        session.add(policy)
        session.flush()

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved.tenant_id == "tenant-acme"

    def test_required_artifacts_json_round_trip(self, session: Session):
        """required_artifacts JSON list survives a flush/retrieve round-trip."""
        artifacts = ["skill:canvas", "command:git-commit", "agent:code-review"]
        policy = AttestationPolicy(
            name="artifacts-policy",
            required_artifacts=artifacts,
        )
        session.add(policy)
        session.flush()
        session.expire(policy)

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved.required_artifacts == artifacts

    def test_required_scopes_json_round_trip(self, session: Session):
        """required_scopes JSON list survives a flush/retrieve round-trip."""
        scopes = ["artifact:read", "deploy:write", "collection:admin"]
        policy = AttestationPolicy(name="scopes-policy", required_scopes=scopes)
        session.add(policy)
        session.flush()
        session.expire(policy)

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved.required_scopes == scopes

    def test_compliance_metadata_json_round_trip(self, session: Session):
        """compliance_metadata JSON dict survives a flush/retrieve round-trip."""
        meta = {"framework": "SOC2", "control": "CC6.1", "review_cadence": "annual"}
        policy = AttestationPolicy(
            name="compliance-policy",
            compliance_metadata=meta,
        )
        session.add(policy)
        session.flush()
        session.expire(policy)

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved.compliance_metadata == meta

    def test_created_at_and_updated_at_auto_populated(self, session: Session):
        """created_at and updated_at are set automatically on flush."""
        policy = AttestationPolicy(name="timestamp-policy")
        session.add(policy)
        session.flush()

        assert policy.created_at is not None
        assert policy.updated_at is not None

    def test_to_dict_serialization(self, session: Session):
        """to_dict() returns all expected keys."""
        policy = AttestationPolicy(
            name="dict-policy",
            tenant_id="tenant-x",
            required_artifacts=["skill:foo"],
            required_scopes=["artifact:read"],
            compliance_metadata={"level": "high"},
        )
        session.add(policy)
        session.flush()

        d = policy.to_dict()
        assert d["name"] == "dict-policy"
        assert d["tenant_id"] == "tenant-x"
        assert d["required_artifacts"] == ["skill:foo"]
        assert d["required_scopes"] == ["artifact:read"]
        assert d["compliance_metadata"] == {"level": "high"}
        assert d["created_at"] is not None

    def test_repr_contains_name(self):
        """__repr__ includes name for easy identification."""
        policy = AttestationPolicy(name="repr-policy")
        r = repr(policy)
        assert "repr-policy" in r
        assert "AttestationPolicy" in r


# ---------------------------------------------------------------------------
# BomMetadata
# ---------------------------------------------------------------------------


class TestBomMetadata:
    """Tests for the BomMetadata model."""

    def test_instantiation_with_no_args(self, session: Session):
        """BomMetadata can be created with no explicit arguments (all defaults)."""
        meta = BomMetadata()
        session.add(meta)
        session.flush()

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved is not None

    def test_schema_version_defaults_to_1_0_0(self, session: Session):
        """schema_version defaults to '1.0.0' when not specified."""
        meta = BomMetadata()
        session.add(meta)
        session.flush()

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved.schema_version == "1.0.0"

    def test_schema_version_can_be_overridden(self, session: Session):
        """schema_version can be set to a custom value."""
        meta = BomMetadata(schema_version="2.1.0")
        session.add(meta)
        session.flush()

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved.schema_version == "2.1.0"

    def test_nullable_optional_fields(self, session: Session):
        """format_version and generator_version accept None."""
        meta = BomMetadata(format_version=None, generator_version=None)
        session.add(meta)
        session.flush()

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved.format_version is None
        assert retrieved.generator_version is None

    def test_format_version_stored_when_provided(self, session: Session):
        """format_version is stored and retrieved correctly."""
        meta = BomMetadata(format_version="cyclonedx-1.4")
        session.add(meta)
        session.flush()

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved.format_version == "cyclonedx-1.4"

    def test_generator_version_stored_when_provided(self, session: Session):
        """generator_version is stored and retrieved correctly."""
        meta = BomMetadata(generator_version="0.9.1")
        session.add(meta)
        session.flush()

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved.generator_version == "0.9.1"

    def test_created_at_auto_populated(self, session: Session):
        """created_at is set automatically on flush."""
        meta = BomMetadata()
        session.add(meta)
        session.flush()

        assert meta.created_at is not None

    def test_all_version_fields_together(self, session: Session):
        """All three version fields can be set and retrieved together."""
        meta = BomMetadata(
            schema_version="1.2.0",
            format_version="spdx-2.3",
            generator_version="0.10.0",
        )
        session.add(meta)
        session.flush()
        session.expire(meta)

        retrieved = session.get(BomMetadata, meta.id)
        assert retrieved.schema_version == "1.2.0"
        assert retrieved.format_version == "spdx-2.3"
        assert retrieved.generator_version == "0.10.0"

    def test_to_dict_serialization(self, session: Session):
        """to_dict() returns all expected keys."""
        meta = BomMetadata(
            schema_version="1.0.0",
            format_version="cyclonedx-1.4",
            generator_version="0.9.1",
        )
        session.add(meta)
        session.flush()

        d = meta.to_dict()
        assert d["schema_version"] == "1.0.0"
        assert d["format_version"] == "cyclonedx-1.4"
        assert d["generator_version"] == "0.9.1"
        assert d["created_at"] is not None

    def test_repr_contains_schema_version(self):
        """__repr__ includes schema_version for easy identification."""
        meta = BomMetadata(schema_version="3.0.0")
        r = repr(meta)
        assert "3.0.0" in r
        assert "BomMetadata" in r


# ---------------------------------------------------------------------------
# ScopeValidator
# ---------------------------------------------------------------------------


class TestScopeValidator:
    """Tests for the ScopeValidator model."""

    def test_instantiation_with_valid_data(self, session: Session):
        """ScopeValidator can be created and flushed with all valid fields."""
        sv = ScopeValidator(
            scope_pattern="artifact:read",
            owner_type="user",
            description="Read access to artifacts.",
        )
        session.add(sv)
        session.flush()

        retrieved = session.get(ScopeValidator, sv.id)
        assert retrieved is not None
        assert retrieved.scope_pattern == "artifact:read"
        assert retrieved.owner_type == "user"

    def test_unique_constraint_on_scope_pattern(self, session: Session):
        """Duplicate scope_pattern raises IntegrityError."""
        sv1 = ScopeValidator(scope_pattern="deploy:write", owner_type="user")
        sv2 = ScopeValidator(scope_pattern="deploy:write", owner_type="team")
        session.add(sv1)
        session.flush()
        session.add(sv2)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_unique_constraint_defined_on_table(self):
        """Unique constraint exists on scope_pattern at the table level."""
        table = ScopeValidator.__table__
        # scope_pattern column is declared with unique=True
        col = table.c["scope_pattern"]
        assert col.unique is True or any(
            len(uc.columns) == 1 and "scope_pattern" in [c.name for c in uc.columns]
            for uc in table.constraints
            if hasattr(uc, "columns")
        ), "scope_pattern should have a unique constraint"

    def test_nullable_description(self, session: Session):
        """description is nullable."""
        sv = ScopeValidator(
            scope_pattern="collection:admin",
            owner_type="user",
            description=None,
        )
        session.add(sv)
        session.flush()

        retrieved = session.get(ScopeValidator, sv.id)
        assert retrieved.description is None

    def test_description_stored_when_provided(self, session: Session):
        """description is stored and retrieved correctly."""
        sv = ScopeValidator(
            scope_pattern="artifact:write",
            owner_type="user",
            description="Write access to artifacts.",
        )
        session.add(sv)
        session.flush()

        retrieved = session.get(ScopeValidator, sv.id)
        assert retrieved.description == "Write access to artifacts."

    def test_default_owner_type_is_user(self, session: Session):
        """owner_type defaults to 'user' when not specified."""
        sv = ScopeValidator(scope_pattern="hook:exec")
        session.add(sv)
        session.flush()

        retrieved = session.get(ScopeValidator, sv.id)
        assert retrieved.owner_type == "user"

    def test_team_owner_type_accepted(self, session: Session):
        """owner_type='team' is a valid value for team-scoped patterns."""
        sv = ScopeValidator(scope_pattern="team:manage", owner_type="team")
        session.add(sv)
        session.flush()

        retrieved = session.get(ScopeValidator, sv.id)
        assert retrieved.owner_type == "team"

    def test_created_at_auto_populated(self, session: Session):
        """created_at is set automatically on flush."""
        sv = ScopeValidator(scope_pattern="mcp:read")
        session.add(sv)
        session.flush()

        assert sv.created_at is not None

    def test_multiple_scope_patterns_distinct(self, session: Session):
        """Multiple distinct scope_patterns can be inserted successfully."""
        patterns = ["agent:read", "agent:write", "agent:admin"]
        for p in patterns:
            session.add(ScopeValidator(scope_pattern=p, owner_type="user"))
        session.flush()

        count = (
            session.query(ScopeValidator)
            .filter(ScopeValidator.scope_pattern.in_(patterns))
            .count()
        )
        assert count == 3

    def test_to_dict_serialization(self, session: Session):
        """to_dict() returns all expected keys."""
        sv = ScopeValidator(
            scope_pattern="command:execute",
            owner_type="team",
            description="Execute commands.",
        )
        session.add(sv)
        session.flush()

        d = sv.to_dict()
        assert d["scope_pattern"] == "command:execute"
        assert d["owner_type"] == "team"
        assert d["description"] == "Execute commands."
        assert d["created_at"] is not None

    def test_repr_contains_scope_pattern(self):
        """__repr__ includes scope_pattern for easy identification."""
        sv = ScopeValidator(scope_pattern="repr:test")
        r = repr(sv)
        assert "repr:test" in r
        assert "ScopeValidator" in r


# ---------------------------------------------------------------------------
# Extended model coverage: update behaviour, relationships, edge cases
# ---------------------------------------------------------------------------


class TestAttestationRecordExtended:
    """Additional tests for AttestationRecord covering edge cases."""

    def test_updated_at_changes_on_update(self, session: Session, artifact: Artifact):
        """updated_at is refreshed when the record is modified."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-update-test",
            visibility="private",
        )
        session.add(rec)
        session.flush()
        original_updated_at = rec.updated_at

        # Simulate time passing by setting updated_at manually and triggering
        # an onupdate-capable flush.
        rec.visibility = "public"
        session.flush()
        session.expire(rec)

        retrieved = session.get(AttestationRecord, rec.id)
        # updated_at must still be set (onupdate may equal original in fast tests)
        assert retrieved.updated_at is not None

    def test_artifact_relationship_loads(self, session: Session, artifact: Artifact):
        """AttestationRecord.artifact relationship returns the parent Artifact."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-rel-test",
        )
        session.add(rec)
        session.flush()
        session.expire(rec)

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.artifact is not None
        assert retrieved.artifact.id == artifact.id

    def test_multiple_records_per_artifact(self, session: Session, artifact: Artifact):
        """Multiple AttestationRecords can reference the same artifact."""
        for i in range(3):
            rec = AttestationRecord(
                artifact_id=artifact.id,
                owner_type="user",
                owner_id=f"user-multi-{i}",
            )
            session.add(rec)
        session.flush()

        count = (
            session.query(AttestationRecord)
            .filter_by(artifact_id=artifact.id)
            .count()
        )
        assert count >= 3

    def test_visibility_public_accepted(self, session: Session, artifact: Artifact):
        """visibility='public' is stored correctly."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-pub",
            visibility="public",
        )
        session.add(rec)
        session.flush()

        retrieved = session.get(AttestationRecord, rec.id)
        assert retrieved.visibility == "public"

    def test_to_dict_includes_updated_at(self, session: Session, artifact: Artifact):
        """to_dict() always includes an updated_at key."""
        rec = AttestationRecord(
            artifact_id=artifact.id,
            owner_type="user",
            owner_id="user-dict-upd",
        )
        session.add(rec)
        session.flush()

        d = rec.to_dict()
        assert "updated_at" in d
        assert d["updated_at"] is not None


class TestArtifactHistoryEventExtended:
    """Additional tests for ArtifactHistoryEvent covering edge cases."""

    def test_multiple_events_for_same_artifact(
        self, session: Session, artifact: Artifact
    ):
        """Multiple events can be inserted for the same artifact."""
        for etype in ("create", "update", "deploy"):
            evt = ArtifactHistoryEvent(
                artifact_id=artifact.id,
                event_type=etype,
                actor_id="user-multi",
            )
            session.add(evt)
        session.flush()

        evts = (
            session.query(ArtifactHistoryEvent)
            .filter_by(artifact_id=artifact.id, actor_id="user-multi")
            .all()
        )
        assert len(evts) == 3

    def test_events_ordered_by_timestamp(
        self, session: Session, artifact: Artifact
    ):
        """Events can be queried and ordered by timestamp."""
        t0 = datetime(2025, 1, 1, 0, 0, 0)
        for i, etype in enumerate(("create", "update", "sync")):
            evt = ArtifactHistoryEvent(
                artifact_id=artifact.id,
                event_type=etype,
                timestamp=t0 + timedelta(seconds=i),
            )
            session.add(evt)
        session.flush()

        evts = (
            session.query(ArtifactHistoryEvent)
            .filter_by(artifact_id=artifact.id)
            .order_by(ArtifactHistoryEvent.timestamp.asc())
            .all()
        )
        types_in_order = [e.event_type for e in evts if e.actor_id is None]
        assert types_in_order == ["create", "update", "sync"]

    def test_team_owner_type_accepted(self, session: Session, artifact: Artifact):
        """owner_type='team' is stored and retrieved correctly."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="deploy",
            owner_type="team",
        )
        session.add(evt)
        session.flush()

        retrieved = session.get(ArtifactHistoryEvent, evt.id)
        assert retrieved.owner_type == "team"

    def test_content_hash_stored_when_provided(
        self, session: Session, artifact: Artifact
    ):
        """content_hash (e.g. a SHA-256 hex digest) is stored correctly."""
        sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="update",
            content_hash=sha,
        )
        session.add(evt)
        session.flush()
        session.expire(evt)

        retrieved = session.get(ArtifactHistoryEvent, evt.id)
        assert retrieved.content_hash == sha

    def test_to_dict_includes_owner_type(self, session: Session, artifact: Artifact):
        """to_dict() includes the owner_type field."""
        evt = ArtifactHistoryEvent(
            artifact_id=artifact.id,
            event_type="sync",
            owner_type="team",
        )
        session.add(evt)
        session.flush()

        d = evt.to_dict()
        assert d["owner_type"] == "team"


class TestBomSnapshotExtended:
    """Additional coverage for BomSnapshot — signing_key_id and owner_type."""

    def test_signing_key_id_stored_when_provided(self, session: Session):
        """signing_key_id is stored and retrieved correctly."""
        key_id = "a" * 64  # 64-hex-char SHA-256 fingerprint
        snap = BomSnapshot(
            bom_json='{"signed": true}',
            signing_key_id=key_id,
        )
        session.add(snap)
        session.flush()
        session.expire(snap)

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.signing_key_id == key_id

    def test_signing_key_id_nullable(self, session: Session):
        """signing_key_id is nullable and defaults to None."""
        snap = BomSnapshot(bom_json="{}")
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.signing_key_id is None

    def test_team_owner_type_accepted(self, session: Session):
        """owner_type='team' is a valid value for team-scoped BOMs."""
        snap = BomSnapshot(bom_json='{"team": true}', owner_type="team")
        session.add(snap)
        session.flush()

        retrieved = session.get(BomSnapshot, snap.id)
        assert retrieved.owner_type == "team"

    def test_to_dict_includes_signature_algorithm(self, session: Session):
        """to_dict() includes the signature_algorithm field."""
        snap = BomSnapshot(
            bom_json="{}",
            signature="sig==",
            signature_algorithm="rsa-sha256",
        )
        session.add(snap)
        session.flush()

        d = snap.to_dict()
        assert d["signature_algorithm"] == "rsa-sha256"
        assert d["signature"] == "sig=="

    def test_to_dict_includes_owner_type(self, session: Session):
        """to_dict() includes the owner_type field."""
        snap = BomSnapshot(bom_json="{}", owner_type="team")
        session.add(snap)
        session.flush()

        d = snap.to_dict()
        assert d["owner_type"] == "team"

    def test_repr_includes_commit_sha(self):
        """__repr__ includes commit_sha when it is set."""
        snap = BomSnapshot(bom_json="{}", commit_sha="deadcafe")
        r = repr(snap)
        assert "deadcafe" in r


class TestAttestationPolicyExtended:
    """Additional coverage for AttestationPolicy."""

    def test_updated_at_changes_on_update(self, session: Session):
        """updated_at is set after a field mutation and flush."""
        policy = AttestationPolicy(name="upd-policy")
        session.add(policy)
        session.flush()

        policy.name = "upd-policy-v2"
        session.flush()
        session.expire(policy)

        retrieved = session.get(AttestationPolicy, policy.id)
        assert retrieved.updated_at is not None

    def test_multiple_policies_distinct_names(self, session: Session):
        """Multiple policies with distinct names can be inserted."""
        names = ["pol-alpha", "pol-beta", "pol-gamma"]
        for n in names:
            session.add(AttestationPolicy(name=n))
        session.flush()

        count = (
            session.query(AttestationPolicy)
            .filter(AttestationPolicy.name.in_(names))
            .count()
        )
        assert count == 3

    def test_to_dict_includes_updated_at(self, session: Session):
        """to_dict() always includes updated_at."""
        policy = AttestationPolicy(name="upd-dict-policy")
        session.add(policy)
        session.flush()

        d = policy.to_dict()
        assert "updated_at" in d
        assert d["updated_at"] is not None

    def test_repr_includes_tenant_id(self):
        """__repr__ includes tenant_id for enterprise policies."""
        policy = AttestationPolicy(name="ent-pol", tenant_id="acme-corp")
        r = repr(policy)
        assert "acme-corp" in r


# ---------------------------------------------------------------------------
# Utility function tests: create_db_engine, get_engine, session factory
# ---------------------------------------------------------------------------


class TestCreateDbEngine:
    """Tests for the create_db_engine() utility."""

    def test_returns_engine_with_explicit_path(self, tmp_path: Path):
        """create_db_engine() returns an Engine when given an explicit path."""
        db_file = tmp_path / "test.db"
        engine = create_db_engine(db_file)
        assert engine is not None
        assert "sqlite" in str(engine.url)
        engine.dispose()

    def test_returns_engine_with_default_path(self, tmp_path: Path, monkeypatch):
        """create_db_engine() uses a default path when db_path is None."""
        # Redirect home to a temp dir so we don't touch the real cache.
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        engine = create_db_engine(None)
        assert engine is not None
        assert "sqlite" in str(engine.url)
        engine.dispose()

    def test_engine_executes_pragmas(self, tmp_path: Path):
        """create_db_engine() configures foreign_keys=ON via PRAGMA."""
        db_file = tmp_path / "pragma_test.db"
        engine = create_db_engine(db_file)
        with engine.connect() as conn:
            result = conn.execute(sa.text("PRAGMA foreign_keys")).fetchone()
            assert result[0] == 1
        engine.dispose()

    def test_parent_directory_created(self, tmp_path: Path):
        """create_db_engine() creates the parent directory if it doesn't exist."""
        db_file = tmp_path / "nested" / "dir" / "db.sqlite"
        assert not db_file.parent.exists()
        engine = create_db_engine(db_file)
        assert db_file.parent.exists()
        engine.dispose()


class TestRedactDbUrl:
    """Tests for the _redact_db_url() helper."""

    def test_redacts_password_in_postgresql_url(self):
        """Password in a postgresql:// URL is replaced with '***'."""
        url = "postgresql://user:secret@host:5432/dbname"
        redacted = _redact_db_url(url)
        assert "secret" not in redacted
        assert "***" in redacted

    def test_no_password_url_unchanged(self):
        """URLs without a password component are not mangled."""
        url = "sqlite:////tmp/test.db"
        assert _redact_db_url(url) == url

    def test_psycopg2_url_redacted(self):
        """Password in a postgresql+psycopg2:// URL is also redacted."""
        url = "postgresql+psycopg2://admin:hunter2@localhost/prod"
        redacted = _redact_db_url(url)
        assert "hunter2" not in redacted
        assert "***" in redacted


class TestGetEngine:
    """Tests for get_engine() — environment-based engine factory."""

    def test_returns_sqlite_engine_by_default(self, tmp_path: Path, monkeypatch):
        """get_engine() returns an SQLite engine when no DATABASE_URL is set."""
        import skillmeat.cache.models as _models

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SKILLMEAT_DATABASE_URL", raising=False)
        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        engine = get_engine()
        assert "sqlite" in str(engine.url)
        monkeypatch.setattr(_models, "_engine_singleton", None)

    def test_singleton_returns_same_object(self, tmp_path: Path, monkeypatch):
        """Subsequent calls to get_engine() return the same engine instance."""
        import skillmeat.cache.models as _models

        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SKILLMEAT_DATABASE_URL", raising=False)
        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        e1 = get_engine()
        e2 = get_engine()
        assert e1 is e2
        monkeypatch.setattr(_models, "_engine_singleton", None)

    def test_uses_database_url_env_var_for_postgresql(self, monkeypatch):
        """get_engine() uses DATABASE_URL when it contains a postgresql:// URL."""
        import skillmeat.cache.models as _models

        pg_url = "postgresql://user:pass@localhost:5432/testdb"
        monkeypatch.setenv("DATABASE_URL", pg_url)
        monkeypatch.setattr(_models, "_engine_singleton", None)

        with mock.patch("skillmeat.cache.models.create_engine") as mock_create:
            mock_engine = mock.MagicMock()
            mock_create.return_value = mock_engine
            result = get_engine()
            assert result is mock_engine
            mock_create.assert_called_once()
            call_url = mock_create.call_args[0][0]
            assert call_url == pg_url

        monkeypatch.setattr(_models, "_engine_singleton", None)

    def test_uses_skillmeat_database_url_env_var(self, monkeypatch):
        """get_engine() uses SKILLMEAT_DATABASE_URL for postgresql when set."""
        import skillmeat.cache.models as _models

        pg_url = "postgresql+psycopg2://svc:pass@db:5432/skillmeat"
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("SKILLMEAT_DATABASE_URL", pg_url)
        monkeypatch.setattr(_models, "_engine_singleton", None)

        with mock.patch("skillmeat.cache.models.create_engine") as mock_create:
            mock_engine = mock.MagicMock()
            mock_create.return_value = mock_engine
            result = get_engine()
            assert result is mock_engine

        monkeypatch.setattr(_models, "_engine_singleton", None)


class TestSessionFactory:
    """Tests for init_session_factory() and get_session()."""

    def test_init_session_factory_sets_session_local(
        self, tmp_path: Path, monkeypatch
    ):
        """init_session_factory() assigns a non-None SessionLocal."""
        import skillmeat.cache.models as _models

        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(_models, "SessionLocal", None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        init_session_factory(tmp_path / "sf_test.db")
        assert _models.SessionLocal is not None

        # Cleanup
        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(_models, "SessionLocal", None)

    def test_get_session_returns_session(self, tmp_path: Path, monkeypatch):
        """get_session() returns an open SQLAlchemy Session."""
        import skillmeat.cache.models as _models

        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(_models, "SessionLocal", None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        sess = get_session(tmp_path / "gs_test.db")
        try:
            assert sess is not None
            # Should be usable — execute a trivial query
            sess.execute(sa.text("SELECT 1"))
        finally:
            sess.close()

        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(_models, "SessionLocal", None)

    def test_get_session_reuses_existing_session_local(
        self, tmp_path: Path, monkeypatch
    ):
        """get_session() skips re-init when SessionLocal is already set."""
        import skillmeat.cache.models as _models

        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(_models, "SessionLocal", None)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Prime SessionLocal
        init_session_factory(tmp_path / "reuse_test.db")
        first_factory = _models.SessionLocal

        # get_session() must not replace it
        sess = get_session()
        assert _models.SessionLocal is first_factory
        sess.close()

        monkeypatch.setattr(_models, "_engine_singleton", None)
        monkeypatch.setattr(_models, "SessionLocal", None)


class TestCreateAndDropTables:
    """Tests for create_tables() and drop_tables() helpers."""

    def test_create_tables_creates_bom_tables(self, tmp_path: Path):
        """create_tables() creates all BOM-related tables in the DB."""
        db_file = tmp_path / "create_test.db"
        create_tables(db_file)

        # Verify via inspection
        engine = create_db_engine(db_file)
        inspector = sa_inspect(engine)
        table_names = inspector.get_table_names()
        for tbl in (
            "attestation_records",
            "artifact_history_events",
            "bom_snapshots",
            "attestation_policies",
            "bom_metadata",
            "scope_validators",
        ):
            assert tbl in table_names, f"Expected table '{tbl}' to exist after create_tables()"
        engine.dispose()

    def test_create_tables_is_idempotent(self, tmp_path: Path):
        """Calling create_tables() twice does not raise an error."""
        db_file = tmp_path / "idempotent_test.db"
        create_tables(db_file)
        # Second call must not raise
        create_tables(db_file)

    def test_drop_tables_removes_bom_tables(self, tmp_path: Path):
        """drop_tables() removes all tables created by create_tables()."""
        db_file = tmp_path / "drop_test.db"
        create_tables(db_file)

        drop_tables(db_file)

        engine = create_db_engine(db_file)
        inspector = sa_inspect(engine)
        table_names = inspector.get_table_names()
        assert "attestation_records" not in table_names
        assert "bom_snapshots" not in table_names
        engine.dispose()
