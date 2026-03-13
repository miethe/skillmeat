"""End-to-end integration test for the SkillBOM workflow.

Exercises the full BOM lifecycle without a running server:

1. Generate a BOM snapshot via BomGenerator (mocked session)
2. Verify BOM contents (structure, hashes, determinism)
3. Persist the BOM via BomAttestationService (in-memory SQLite)
4. Create ArtifactHistoryEvent rows and query them back
5. Create an AttestationRecord and verify its fields
6. Sign the BOM and verify the signature (Ed25519)
7. Store a signed BomSnapshot and confirm round-trip integrity
8. Query historical snapshots (time-travel concept)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    ArtifactHistoryEvent,
    AttestationRecord,
    Base,
    BomSnapshot,
)
from skillmeat.core.bom.generator import BomGenerator, BomSerializer
from skillmeat.core.bom.signing import (
    SignatureResult,
    VerificationResult,
    generate_signing_keypair,
    sign_bom,
    verify_signature,
)
from skillmeat.core.services.bom_service import BomAttestationService


# ---------------------------------------------------------------------------
# DB Fixtures
# ---------------------------------------------------------------------------

_NEEDED_TABLES = {
    "artifacts",
    "bom_snapshots",
    "attestation_records",
    "artifact_history_events",
}


def _make_test_engine():
    """Create an in-memory SQLite engine with a minimal schema for BOM tests."""
    engine = sa.create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    # projects table is required by Artifact FK
    with engine.begin() as conn:
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

    tables_to_create = [
        Base.metadata.tables[t]
        for t in _NEEDED_TABLES
        if t in Base.metadata.tables
    ]
    Base.metadata.create_all(engine, tables=tables_to_create)
    return engine


@pytest.fixture()
def db_session():
    """Yield a transactional SQLAlchemy session backed by in-memory SQLite."""
    engine = _make_test_engine()
    Session_ = sessionmaker(bind=engine)
    sess = Session_()
    yield sess
    sess.close()
    engine.dispose()


@pytest.fixture()
def bom_service(db_session: Session) -> BomAttestationService:
    """Return a BomAttestationService wired to the test DB session."""
    return BomAttestationService(db_session)


# ---------------------------------------------------------------------------
# Helpers: artifact mocks and DB row insertion
# ---------------------------------------------------------------------------


def _make_mock_artifact(
    name: str,
    artifact_type: str,
    source: Optional[str] = None,
    deployed_version: Optional[str] = None,
    content: Optional[str] = None,
    content_hash: Optional[str] = None,
    project_id: str = "proj-test",
) -> Any:
    """Return a MagicMock shaped like an ORM Artifact row."""
    art = MagicMock()
    art.id = f"{artifact_type}:{name}"
    art.name = name
    art.type = artifact_type
    art.source = source
    art.deployed_version = deployed_version
    art.upstream_version = None
    art.content = content
    art.content_hash = content_hash
    art.project_id = project_id
    art.created_at = None
    art.updated_at = None
    art.artifact_metadata = None
    art.uuid = f"uuid-{name}"
    return art


def _make_mock_session(artifacts: List[Any]) -> MagicMock:
    """Return a MagicMock session whose query().all() returns *artifacts*."""
    session = MagicMock()
    query_mock = MagicMock()
    query_mock.all.return_value = artifacts
    query_mock.filter.return_value = query_mock
    session.query.return_value = query_mock
    return session


def _insert_artifact_row(session: Session, artifact_id: str) -> None:
    """Insert minimal project + artifact rows for FK constraint satisfaction."""
    session.execute(
        sa.text(
            "INSERT INTO projects (id, name) VALUES (:id, 'test-project') "
            "ON CONFLICT(id) DO NOTHING"
        ),
        {"id": "proj-test"},
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
                    (:id, :art_uuid, 'proj-test', :name, :type,
                     0, 0,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "id": artifact_id,
                "art_uuid": uuid.uuid4().hex,
                "name": artifact_id.split(":", 1)[-1],
                "type": artifact_id.split(":", 1)[0],
            },
        )
    session.flush()


# ---------------------------------------------------------------------------
# Test: Full BOM workflow
# ---------------------------------------------------------------------------


class TestBomWorkflowEndToEnd:
    """Integration tests exercising the full BOM generation → storage → query cycle."""

    # ------------------------------------------------------------------
    # Step 1-3: Generate and verify BOM from mock artifacts
    # ------------------------------------------------------------------

    def test_bom_generation_produces_valid_structure(self):
        """BomGenerator creates a valid BOM over a mixed set of artifacts."""
        artifacts = [
            _make_mock_artifact("canvas", "skill", source="anthropics/skills/canvas", deployed_version="v1.0.0", content="skill content"),
            _make_mock_artifact("deploy-cmd", "command", source="user/repo/deploy", deployed_version="v2.3.0"),
            _make_mock_artifact("analyst", "agent", deployed_version="v0.5.0", content="agent spec"),
        ]
        session = _make_mock_session(artifacts)
        gen = BomGenerator(session=session)
        bom = gen.generate(project_id="proj-test")

        assert bom["schema_version"] == "1.0.0"
        assert bom["artifact_count"] == 3
        assert len(bom["artifacts"]) == 3
        assert "generated_at" in bom
        assert "metadata" in bom

    def test_bom_artifact_entries_have_required_fields(self):
        """Every BOM artifact entry carries name, type, source, version, content_hash, metadata."""
        required_keys = {"name", "type", "source", "version", "content_hash", "metadata"}
        artifacts = [
            _make_mock_artifact("my-skill", "skill", source="user/repo/my-skill", deployed_version="v1.0.0", content="hello"),
            _make_mock_artifact("my-cmd", "command"),
        ]
        session = _make_mock_session(artifacts)
        bom = BomGenerator(session=session).generate()

        for entry in bom["artifacts"]:
            missing = required_keys - entry.keys()
            assert not missing, f"Entry '{entry.get('name')}' missing keys: {missing}"

    def test_bom_content_hashes_are_valid_hex_or_empty(self):
        """Content hashes are either 64-char hex strings or the empty string."""
        artifacts = [
            _make_mock_artifact("skill-with-content", "skill", content="rich content here"),
            _make_mock_artifact("skill-no-content", "skill"),
        ]
        session = _make_mock_session(artifacts)
        bom = BomGenerator(session=session).generate()

        for entry in bom["artifacts"]:
            ch = entry["content_hash"]
            assert isinstance(ch, str)
            if ch:
                assert len(ch) == 64, f"Non-empty hash must be 64 chars, got {len(ch)}"
                assert all(c in "0123456789abcdef" for c in ch)

    def test_bom_generation_is_deterministic(self):
        """Generating BOM twice with the same state yields identical artifact lists."""
        artifacts = [
            _make_mock_artifact("stable-skill", "skill", source="user/repo/stable", content="fixed content"),
            _make_mock_artifact("stable-cmd", "command"),
        ]
        session = _make_mock_session(artifacts)
        gen = BomGenerator(session=session)

        bom_first = gen.generate()
        bom_second = gen.generate()

        assert bom_first["artifacts"] == bom_second["artifacts"]
        assert bom_first["artifact_count"] == bom_second["artifact_count"]

    def test_bom_entries_sorted_by_type_then_name(self):
        """BOM entries are sorted deterministically by (type, name)."""
        artifacts = [
            _make_mock_artifact("z-skill", "skill"),
            _make_mock_artifact("a-skill", "skill"),
            _make_mock_artifact("b-command", "command"),
        ]
        session = _make_mock_session(artifacts)
        bom = BomGenerator(session=session).generate()

        keys = [(e["type"], e["name"]) for e in bom["artifacts"]]
        assert keys == sorted(keys)

    # ------------------------------------------------------------------
    # Step 4-5: Persist BOM and create AttestationRecord via service
    # ------------------------------------------------------------------

    def test_bom_service_persists_snapshot(self, bom_service, db_session):
        """BomAttestationService stores BomSnapshot in the DB."""
        bom_dict = {
            "schema_version": "1.0.0",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "artifact_count": 1,
            "artifacts": [
                {
                    "name": "canvas",
                    "type": "skill",
                    "source": "anthropics/skills/canvas",
                    "version": "v1.0.0",
                    "content_hash": "a" * 64,
                    "metadata": {},
                }
            ],
            "metadata": {"generator": "skillmeat-bom", "elapsed_ms": 1.0},
        }
        bom_json = json.dumps(bom_dict)

        snapshot, attestation = bom_service.create_bom_with_attestation(
            bom_json=bom_json,
            project_id="proj-test",
        )
        db_session.commit()

        assert snapshot.id is not None
        assert attestation is None

        row = db_session.query(BomSnapshot).get(snapshot.id)
        assert row is not None
        assert row.project_id == "proj-test"
        parsed = json.loads(row.bom_json)
        assert parsed["artifact_count"] == 1
        assert parsed["artifacts"][0]["name"] == "canvas"

    def test_bom_service_creates_attestation_record(self, bom_service, db_session):
        """BomAttestationService creates AttestationRecord when artifact_id is given."""
        _insert_artifact_row(db_session, "skill:canvas")
        bom_json = json.dumps({"schema_version": "1.0.0"})

        snapshot, attestation = bom_service.create_bom_with_attestation(
            bom_json=bom_json,
            artifact_id="skill:canvas",
            owner_type="user",
            owner_id="alice",
            roles=["team_member"],
            scopes=["read", "write"],
            visibility="private",
        )
        db_session.commit()

        assert snapshot.id is not None
        assert attestation is not None
        assert attestation.artifact_id == "skill:canvas"
        assert attestation.owner_type == "user"
        assert attestation.owner_id == "alice"
        assert attestation.roles == ["team_member"]
        assert attestation.scopes == ["read", "write"]
        assert attestation.visibility == "private"

        # Verify persistence via fresh query
        row = db_session.query(AttestationRecord).get(attestation.id)
        assert row is not None
        assert row.artifact_id == "skill:canvas"

    def test_bom_round_trip_through_json_serialize(self, tmp_path):
        """BOM dict round-trips cleanly through BomSerializer write_file → JSON parse."""
        artifacts = [
            _make_mock_artifact("round-trip-skill", "skill", content="content here", deployed_version="v1.2.3"),
        ]
        session = _make_mock_session(artifacts)
        bom = BomGenerator(session=session).generate()

        serializer = BomSerializer()
        target = tmp_path / "context.lock"
        serializer.write_file(bom, target)

        assert target.exists()
        parsed = json.loads(target.read_text(encoding="utf-8"))

        assert parsed["schema_version"] == bom["schema_version"]
        assert parsed["artifact_count"] == bom["artifact_count"]
        assert len(parsed["artifacts"]) == len(bom["artifacts"])
        assert parsed["artifacts"][0]["name"] == "round-trip-skill"
        assert parsed["artifacts"][0]["version"] == "v1.2.3"

    # ------------------------------------------------------------------
    # Step 4 alt: Create and query ArtifactHistoryEvent rows
    # ------------------------------------------------------------------

    def test_history_event_created_and_queried(self, db_session):
        """ArtifactHistoryEvent rows are created and queryable via session."""
        _insert_artifact_row(db_session, "skill:canvas")

        event_obj = ArtifactHistoryEvent(
            artifact_id="skill:canvas",
            event_type="deploy",
            actor_id="alice",
            owner_type="user",
            timestamp=datetime.now(tz=timezone.utc),
            content_hash="b" * 64,
        )
        db_session.add(event_obj)
        db_session.commit()

        rows = (
            db_session.query(ArtifactHistoryEvent)
            .filter(ArtifactHistoryEvent.artifact_id == "skill:canvas")
            .all()
        )
        assert len(rows) == 1
        assert rows[0].event_type == "deploy"
        assert rows[0].actor_id == "alice"
        assert rows[0].content_hash == "b" * 64

    def test_multiple_history_events_ordered_by_timestamp(self, db_session):
        """Multiple history events can be queried and ordered by timestamp."""
        _insert_artifact_row(db_session, "command:deploy-cmd")

        event_types = ["create", "update", "deploy"]
        for etype in event_types:
            db_session.add(
                ArtifactHistoryEvent(
                    artifact_id="command:deploy-cmd",
                    event_type=etype,
                    actor_id="system",
                    owner_type="user",
                    timestamp=datetime.now(tz=timezone.utc),
                )
            )
        db_session.commit()

        rows = (
            db_session.query(ArtifactHistoryEvent)
            .filter(ArtifactHistoryEvent.artifact_id == "command:deploy-cmd")
            .order_by(ArtifactHistoryEvent.timestamp)
            .all()
        )
        assert len(rows) == 3
        assert [r.event_type for r in rows] == event_types

    def test_history_event_diff_json_round_trip(self, db_session):
        """diff_json payload is stored and retrieved intact."""
        _insert_artifact_row(db_session, "agent:planner")

        diff_payload = {
            "field": "deployed_version",
            "old": "v0.9.0",
            "new": "v1.0.0",
        }
        event_obj = ArtifactHistoryEvent(
            artifact_id="agent:planner",
            event_type="update",
            actor_id="bob",
            owner_type="user",
            timestamp=datetime.now(tz=timezone.utc),
            diff_json=json.dumps(diff_payload),
        )
        db_session.add(event_obj)
        db_session.commit()

        row = (
            db_session.query(ArtifactHistoryEvent)
            .filter(ArtifactHistoryEvent.artifact_id == "agent:planner")
            .one()
        )
        assert row.diff_json is not None
        recovered = json.loads(row.diff_json)
        assert recovered["old"] == "v0.9.0"
        assert recovered["new"] == "v1.0.0"

    # ------------------------------------------------------------------
    # Step 6-7: Sign BOM and verify the signature
    # ------------------------------------------------------------------

    def test_bom_signing_and_verification(self, tmp_path):
        """sign_bom + verify_signature round-trip succeeds with a temp keypair."""
        key_dir = tmp_path / "keys"
        public_pem, private_pem = generate_signing_keypair(key_dir=key_dir)

        bom_content = b'{"schema_version": "1.0.0", "artifact_count": 2}'
        sig_result = sign_bom(bom_content=bom_content, private_key=private_pem)

        assert isinstance(sig_result, SignatureResult)
        assert sig_result.algorithm == "ed25519"
        assert len(sig_result.signature_hex) == 128  # 64 bytes hex-encoded
        assert len(sig_result.key_id) == 64  # SHA-256 fingerprint

        verify_result = verify_signature(
            bom_content=bom_content,
            signature=sig_result.signature,
            public_key=public_pem,
        )

        assert isinstance(verify_result, VerificationResult)
        assert verify_result.valid is True
        assert verify_result.error is None
        assert verify_result.algorithm == "ed25519"
        assert verify_result.key_id == sig_result.key_id

    def test_tampered_bom_fails_signature_verification(self, tmp_path):
        """Verifying a valid signature against modified BOM content returns valid=False."""
        key_dir = tmp_path / "keys"
        public_pem, private_pem = generate_signing_keypair(key_dir=key_dir)

        original_content = b'{"schema_version": "1.0.0", "artifact_count": 1}'
        tampered_content = b'{"schema_version": "1.0.0", "artifact_count": 999}'

        sig_result = sign_bom(bom_content=original_content, private_key=private_pem)

        verify_result = verify_signature(
            bom_content=tampered_content,
            signature=sig_result.signature,
            public_key=public_pem,
        )

        assert verify_result.valid is False
        assert verify_result.error is not None

    def test_signed_bom_stored_as_snapshot(self, bom_service, db_session, tmp_path):
        """A signed BOM snapshot is stored with signature fields in the DB."""
        key_dir = tmp_path / "keys"
        public_pem, private_pem = generate_signing_keypair(key_dir=key_dir)

        artifacts = [
            _make_mock_artifact("signed-skill", "skill", content="some content", deployed_version="v2.0.0"),
        ]
        mock_session = _make_mock_session(artifacts)
        gen = BomGenerator(session=mock_session)
        bom_dict = gen.generate(project_id="proj-signed")
        bom_json_str = json.dumps(bom_dict, sort_keys=True)
        bom_bytes = bom_json_str.encode("utf-8")

        sig_result = sign_bom(bom_content=bom_bytes, private_key=private_pem)

        snapshot = BomSnapshot(
            project_id="proj-signed",
            commit_sha="deadbeef1234",
            bom_json=bom_json_str,
            signature=sig_result.signature_hex,
            signature_algorithm=sig_result.algorithm,
            signing_key_id=sig_result.key_id,
            owner_type="user",
        )
        db_session.add(snapshot)
        db_session.commit()

        row = db_session.query(BomSnapshot).get(snapshot.id)
        assert row is not None
        assert row.signature == sig_result.signature_hex
        assert row.signature_algorithm == "ed25519"
        assert row.signing_key_id == sig_result.key_id
        assert row.commit_sha == "deadbeef1234"

        # Verify the stored signature is still valid
        recovered_sig = bytes.fromhex(row.signature)
        verify_result = verify_signature(
            bom_content=row.bom_json.encode("utf-8"),
            signature=recovered_sig,
            public_key=public_pem,
        )
        assert verify_result.valid is True

    # ------------------------------------------------------------------
    # Step 8: Time-travel / restore concept
    # ------------------------------------------------------------------

    def test_query_bom_at_specific_commit(self, db_session):
        """Multiple BomSnapshot rows can be queried by commit_sha for time-travel."""
        sha_v1 = "aaa111"
        sha_v2 = "bbb222"
        sha_v3 = "ccc333"

        bom_v1 = json.dumps({"schema_version": "1.0.0", "artifact_count": 1, "artifacts": [{"name": "skill-a"}]})
        bom_v2 = json.dumps({"schema_version": "1.0.0", "artifact_count": 2, "artifacts": [{"name": "skill-a"}, {"name": "skill-b"}]})
        bom_v3 = json.dumps({"schema_version": "1.0.0", "artifact_count": 3, "artifacts": [{"name": "skill-a"}, {"name": "skill-b"}, {"name": "skill-c"}]})

        for sha, bom_json in [(sha_v1, bom_v1), (sha_v2, bom_v2), (sha_v3, bom_v3)]:
            db_session.add(
                BomSnapshot(
                    project_id="proj-time-travel",
                    commit_sha=sha,
                    bom_json=bom_json,
                    owner_type="user",
                )
            )
        db_session.commit()

        # Query by specific commit sha
        row_v2 = (
            db_session.query(BomSnapshot)
            .filter(
                BomSnapshot.project_id == "proj-time-travel",
                BomSnapshot.commit_sha == sha_v2,
            )
            .one()
        )
        parsed = json.loads(row_v2.bom_json)
        assert parsed["artifact_count"] == 2

        # Query all snapshots for project, ordered by creation time
        all_rows = (
            db_session.query(BomSnapshot)
            .filter(BomSnapshot.project_id == "proj-time-travel")
            .order_by(BomSnapshot.created_at)
            .all()
        )
        assert len(all_rows) == 3
        counts = [json.loads(r.bom_json)["artifact_count"] for r in all_rows]
        assert counts == [1, 2, 3]

    def test_latest_bom_snapshot_retrieval(self, db_session):
        """Retrieving the most recent BomSnapshot for a project works correctly."""
        for i in range(3):
            db_session.add(
                BomSnapshot(
                    project_id="proj-latest",
                    commit_sha=f"sha{i:03d}",
                    bom_json=json.dumps({"version": i}),
                    owner_type="user",
                )
            )
        db_session.commit()

        latest = (
            db_session.query(BomSnapshot)
            .filter(BomSnapshot.project_id == "proj-latest")
            .order_by(BomSnapshot.created_at.desc())
            .first()
        )
        assert latest is not None
        parsed = json.loads(latest.bom_json)
        # The last-inserted snapshot has version=2 (SQLite insertion order matches created_at)
        assert parsed["version"] == 2

    # ------------------------------------------------------------------
    # Cascade: Artifact deletion removes associated records
    # ------------------------------------------------------------------

    def test_cascade_delete_removes_attestation_records(self, db_session):
        """Deleting an artifact cascades to its AttestationRecord rows."""
        _insert_artifact_row(db_session, "skill:deletable")
        attest = AttestationRecord(
            artifact_id="skill:deletable",
            owner_type="user",
            owner_id="carol",
            visibility="private",
        )
        db_session.add(attest)
        db_session.commit()
        attest_id = attest.id

        # Delete via raw SQL to trigger ON DELETE CASCADE (bypass ORM unit-of-work)
        db_session.execute(
            sa.text("DELETE FROM artifacts WHERE id = 'skill:deletable'")
        )
        db_session.commit()

        gone = db_session.query(AttestationRecord).get(attest_id)
        assert gone is None

    def test_cascade_delete_removes_history_events(self, db_session):
        """Deleting an artifact cascades to its ArtifactHistoryEvent rows."""
        _insert_artifact_row(db_session, "command:ephemeral")
        db_session.add(
            ArtifactHistoryEvent(
                artifact_id="command:ephemeral",
                event_type="create",
                actor_id="system",
                owner_type="user",
                timestamp=datetime.now(tz=timezone.utc),
            )
        )
        db_session.commit()

        count_before = (
            db_session.query(ArtifactHistoryEvent)
            .filter(ArtifactHistoryEvent.artifact_id == "command:ephemeral")
            .count()
        )
        assert count_before == 1

        db_session.execute(
            sa.text("DELETE FROM artifacts WHERE id = 'command:ephemeral'")
        )
        db_session.commit()

        count_after = (
            db_session.query(ArtifactHistoryEvent)
            .filter(ArtifactHistoryEvent.artifact_id == "command:ephemeral")
            .count()
        )
        assert count_after == 0
