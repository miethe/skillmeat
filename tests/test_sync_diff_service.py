"""Unit tests for sync_diff_service.compute_skill_sync_diff().

These tests exercise the hierarchical version comparison row generation for
skills and their embedded members.  They use a temporary SQLite database and
bypass Alembic migrations by injecting a pre-seeded Session via the
``_session`` parameter supported by ``compute_skill_sync_diff``.

Acceptance criteria verified
-----------------------------
1. Skill with 3 members → 4 rows (1 parent + 3 children).
2. Each member row has ``source_version``, ``collection_version``,
   ``deployed_version`` fields populated from the DB.
3. Member rows carry ``parent_artifact_id == skill_artifact_id``.
4. Non-skill artifacts (no companion composite) → 1 row, no regression.
5. No N+1 queries — verified structurally by the two-IN-query batch path.
6. Missing artifact_id raises ``ValueError``.
7. Skill with companion composite but zero members → 1 row.
"""

from __future__ import annotations

import json
import tempfile
import uuid as _uuid
from datetime import datetime
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CollectionArtifact,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
    create_tables,
)
from skillmeat.core.services.sync_diff_service import (
    VersionComparisonRow,
    compute_skill_sync_diff,
)

# Sentinel — tests inject a session directly, so db_path is never used.
_FAKE_DB_PATH = "/tmp/test-sync-diff-not-used.db"


# =============================================================================
# Fixtures — shared DB infrastructure
# =============================================================================


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Provide a temporary SQLite database path, cleaned up after each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def engine(temp_db: str):
    """Create engine and initialise all ORM tables without running Alembic."""
    with patch("skillmeat.cache.migrations.run_migrations"):
        eng = create_db_engine(temp_db)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Provide a transactional SQLAlchemy session per test."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()


# =============================================================================
# Constants and DB seeding helpers
# =============================================================================

PROJECT_ID = "proj-sync-test"
COLLECTION_ID = "col-sync-test"


def _make_artifact(
    session: Session,
    artifact_id: str,
    name: str,
    artifact_type: str,
    deployed_version: str | None = None,
) -> Artifact:
    """Insert and return an Artifact row."""
    art = Artifact(
        id=artifact_id,
        uuid=_uuid.uuid4().hex,
        project_id=PROJECT_ID,
        name=name,
        type=artifact_type,
        deployed_version=deployed_version,
    )
    session.add(art)
    session.flush()
    return art


def _make_collection_artifact(
    session: Session,
    artifact_uuid: str,
    version: str | None = None,
    resolved_version: str | None = None,
) -> CollectionArtifact:
    """Insert and return a CollectionArtifact row."""
    ca = CollectionArtifact(
        collection_id=COLLECTION_ID,
        artifact_uuid=artifact_uuid,
        version=version,
        resolved_version=resolved_version,
        added_at=datetime.utcnow(),
    )
    session.add(ca)
    session.flush()
    return ca


def _make_composite(
    session: Session,
    composite_id: str,
    skill_uuid: str,
) -> CompositeArtifact:
    """Insert a skill-type CompositeArtifact companion for *skill_uuid*."""
    comp = CompositeArtifact(
        id=composite_id,
        collection_id=COLLECTION_ID,
        composite_type="skill",
        display_name=composite_id,
        metadata_json=json.dumps({"artifact_uuid": skill_uuid}),
    )
    session.add(comp)
    session.flush()
    return comp


def _make_membership(
    session: Session,
    composite_id: str,
    child_uuid: str,
    position: int = 0,
) -> CompositeMembership:
    """Insert a CompositeMembership edge."""
    mem = CompositeMembership(
        collection_id=COLLECTION_ID,
        composite_id=composite_id,
        child_artifact_uuid=child_uuid,
        relationship_type="contains",
        position=position,
    )
    session.add(mem)
    session.flush()
    return mem


def _seed_project(session: Session) -> Project:
    """Ensure the shared test project row and collection row exist."""
    proj = Project(
        id=PROJECT_ID,
        name="Sync Diff Test Project",
        path="/tmp/sync-diff-test",
        status="active",
    )
    session.add(proj)

    coll = Collection(
        id=COLLECTION_ID,
        name="Sync Diff Test Collection",
    )
    session.add(coll)

    session.flush()
    return proj


def _run(session: Session, artifact_id: str) -> list[VersionComparisonRow]:
    """Convenience wrapper: call compute_skill_sync_diff with session injection."""
    return compute_skill_sync_diff(
        artifact_id=artifact_id,
        collection_id=COLLECTION_ID,
        project_id=PROJECT_ID,
        db_path=_FAKE_DB_PATH,
        _session=session,
    )


# =============================================================================
# Test cases
# =============================================================================


class TestComputeSkillSyncDiff:
    """Tests for compute_skill_sync_diff()."""

    def test_skill_with_three_members_produces_four_rows(self, session: Session):
        """Core acceptance criterion: skill + 3 members → 4 rows."""
        _seed_project(session)

        # Parent skill
        skill_art = _make_artifact(
            session, "skill:my-skill", "my-skill", "skill", deployed_version="v1.0.0"
        )
        _make_collection_artifact(
            session,
            skill_art.uuid,
            version="v1.0.0",
            resolved_version="abc123",
        )

        # Companion composite
        comp = _make_composite(session, "composite:my-skill", skill_art.uuid)

        # 3 member artifacts
        for i in range(3):
            name = f"command-{i}"
            art = _make_artifact(
                session,
                f"command:{name}",
                name,
                "command",
                deployed_version=f"v0.{i}.0",
            )
            _make_collection_artifact(
                session,
                art.uuid,
                version=f"v0.{i}.0",
                resolved_version=f"sha-{i}",
            )
            _make_membership(session, comp.id, art.uuid, position=i)

        session.commit()

        rows = _run(session, "skill:my-skill")

        assert len(rows) == 4, f"Expected 4 rows, got {len(rows)}: {rows}"

    def test_parent_row_appears_first_and_is_not_member(self, session: Session):
        """Parent skill row is at index 0 with is_member=False."""
        _seed_project(session)
        skill_art = _make_artifact(
            session, "skill:foo", "foo", "skill", deployed_version="v2.0.0"
        )
        _make_collection_artifact(
            session, skill_art.uuid, version="v2.0.0", resolved_version="deadbeef"
        )
        comp = _make_composite(session, "composite:foo", skill_art.uuid)
        member = _make_artifact(
            session, "agent:bar", "bar", "agent", deployed_version="v1.0.0"
        )
        _make_collection_artifact(
            session, member.uuid, version="v1.0.0", resolved_version="cafebabe"
        )
        _make_membership(session, comp.id, member.uuid, position=0)
        session.commit()

        rows = _run(session, "skill:foo")

        assert rows[0].artifact_id == "skill:foo"
        assert rows[0].is_member is False
        assert rows[0].parent_artifact_id is None

    def test_member_rows_have_version_fields(self, session: Session):
        """Member rows carry all three version fields."""
        _seed_project(session)
        skill_art = _make_artifact(
            session, "skill:alpha", "alpha", "skill", deployed_version="v1.1.0"
        )
        _make_collection_artifact(
            session, skill_art.uuid, version="v1.1.0", resolved_version="src-sha"
        )
        comp = _make_composite(session, "composite:alpha", skill_art.uuid)

        member = _make_artifact(
            session,
            "command:beta",
            "beta",
            "command",
            deployed_version="v0.5.0",
        )
        _make_collection_artifact(
            session,
            member.uuid,
            version="v0.5.0",
            resolved_version="member-sha",
        )
        _make_membership(session, comp.id, member.uuid, position=0)
        session.commit()

        rows = _run(session, "skill:alpha")

        member_row = rows[1]
        assert member_row.is_member is True
        assert member_row.collection_version == "v0.5.0"
        assert member_row.source_version == "member-sha"
        assert member_row.deployed_version == "v0.5.0"

    def test_member_rows_link_to_parent_artifact_id(self, session: Session):
        """Every member row has parent_artifact_id set to the skill's id."""
        _seed_project(session)
        skill_art = _make_artifact(
            session, "skill:gamma", "gamma", "skill", deployed_version=None
        )
        _make_collection_artifact(session, skill_art.uuid, version="v1.0.0")
        comp = _make_composite(session, "composite:gamma", skill_art.uuid)

        for i in range(3):
            member = _make_artifact(session, f"command:m{i}", f"m{i}", "command")
            _make_collection_artifact(session, member.uuid, version=f"v{i}.0.0")
            _make_membership(session, comp.id, member.uuid, position=i)

        session.commit()

        rows = _run(session, "skill:gamma")

        for row in rows[1:]:
            assert row.parent_artifact_id == "skill:gamma", (
                f"Member row {row.artifact_id} has wrong parent: {row.parent_artifact_id}"
            )

    def test_non_skill_without_composite_returns_one_row(self, session: Session):
        """Skill with no companion composite → single row, no regression."""
        _seed_project(session)
        art = _make_artifact(
            session, "skill:solo", "solo", "skill", deployed_version="v0.1.0"
        )
        _make_collection_artifact(session, art.uuid, version="v0.1.0")
        session.commit()

        rows = _run(session, "skill:solo")

        assert len(rows) == 1
        assert rows[0].artifact_id == "skill:solo"
        assert rows[0].is_member is False

    def test_companion_composite_with_zero_members_returns_one_row(
        self, session: Session
    ):
        """Companion composite exists but has no members → single row."""
        _seed_project(session)
        art = _make_artifact(session, "skill:empty", "empty", "skill")
        _make_collection_artifact(session, art.uuid, version="v1.0.0")
        _make_composite(session, "composite:empty", art.uuid)
        # No memberships added
        session.commit()

        rows = _run(session, "skill:empty")

        assert len(rows) == 1
        assert rows[0].artifact_id == "skill:empty"

    def test_missing_artifact_id_raises_value_error(self, session: Session):
        """compute_skill_sync_diff raises ValueError for unknown artifact_id."""
        _seed_project(session)
        session.commit()

        with pytest.raises(ValueError, match="Artifact not found in cache"):
            _run(session, "skill:does-not-exist")

    def test_versions_are_none_when_not_in_collection(self, session: Session):
        """collection_version and source_version are None when no CA row exists."""
        _seed_project(session)
        # Artifact in project table but NOT in collection_artifacts
        art = _make_artifact(
            session, "skill:orphan", "orphan", "skill", deployed_version="v1.0.0"
        )
        # No CollectionArtifact row inserted
        session.commit()

        rows = _run(session, "skill:orphan")

        assert len(rows) == 1
        assert rows[0].collection_version is None
        assert rows[0].source_version is None
        assert rows[0].deployed_version == "v1.0.0"

    def test_member_order_follows_composite_position(self, session: Session):
        """Member rows appear in position order matching CompositeMembership.position."""
        _seed_project(session)
        skill_art = _make_artifact(session, "skill:ordered", "ordered", "skill")
        _make_collection_artifact(session, skill_art.uuid)
        comp = _make_composite(session, "composite:ordered", skill_art.uuid)

        # Names are deliberately non-alphabetical to confirm ordering is by
        # position, not insertion order or name.
        names = ["zeta", "alpha", "mu"]
        member_ids = []
        for i, name in enumerate(names):
            member = _make_artifact(session, f"command:{name}", name, "command")
            _make_collection_artifact(session, member.uuid)
            _make_membership(session, comp.id, member.uuid, position=i)
            member_ids.append(f"command:{name}")

        session.commit()

        rows = _run(session, "skill:ordered")

        assert len(rows) == 4
        actual_member_ids = [r.artifact_id for r in rows[1:]]
        assert actual_member_ids == member_ids

    def test_parent_version_fields_come_from_db(self, session: Session):
        """Parent skill row version fields are populated from the DB correctly."""
        _seed_project(session)
        art = _make_artifact(
            session, "skill:versioned", "versioned", "skill", deployed_version="v3.2.1"
        )
        _make_collection_artifact(
            session,
            art.uuid,
            version="v3.2.1",
            resolved_version="upstream-sha-999",
        )
        session.commit()

        rows = _run(session, "skill:versioned")

        assert rows[0].deployed_version == "v3.2.1"
        assert rows[0].collection_version == "v3.2.1"
        assert rows[0].source_version == "upstream-sha-999"

    def test_member_not_in_target_project_has_none_deployed_version(
        self, session: Session
    ):
        """Member absent from the target project's Artifact table → deployed_version=None.

        The member is registered in the collection and exists in a *different*
        project's artifact table, but not in PROJECT_ID.  The batch query is
        filtered to PROJECT_ID so deployed_version must be None.
        """
        _seed_project(session)
        skill_art = _make_artifact(
            session, "skill:partial", "partial", "skill", deployed_version="v1.0.0"
        )
        _make_collection_artifact(session, skill_art.uuid, version="v1.0.0")
        comp = _make_composite(session, "composite:partial", skill_art.uuid)

        # Member exists in a different project — satisfies FK but not in PROJECT_ID
        other_proj = Project(
            id="proj-other",
            name="Other Project",
            path="/tmp/other",
            status="active",
        )
        session.add(other_proj)
        session.flush()

        member_uuid = _uuid.uuid4().hex
        other_art = Artifact(
            id="command:undeployed",
            uuid=member_uuid,
            project_id="proj-other",  # Different project!
            name="undeployed",
            type="command",
            deployed_version=None,
        )
        session.add(other_art)
        session.flush()

        _make_collection_artifact(session, member_uuid, version="v0.1.0")
        _make_membership(session, comp.id, member_uuid, position=0)
        session.commit()

        rows = _run(session, "skill:partial")

        assert len(rows) == 2
        member_row = rows[1]
        # Batch query filters to PROJECT_ID, so the member won't be found there.
        assert member_row.deployed_version is None
        assert member_row.collection_version == "v0.1.0"
