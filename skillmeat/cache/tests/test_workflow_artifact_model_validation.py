"""
# WAW-P1.2 Artifact model validation — workflow type support
#
# VALIDATION RESULT: NO SCHEMA CHANGES REQUIRED
#
# Summary of findings (verified against skillmeat/cache/models.py):
#
# 1. CHECK CONSTRAINT already includes 'workflow'
#    Artifact.__table_args__ contains:
#      CheckConstraint(
#          "type IN ('skill', 'command', 'agent', 'mcp', 'mcp_server', 'hook', "
#          "'workflow', 'composite', ...)",
#          name="check_artifact_type",
#      )
#    'workflow' is explicitly listed at models.py line 410.
#
# 2. REQUIRED COLUMNS are all present on Artifact:
#    - name:        Mapped[str]  (String, nullable=False)
#    - description: Mapped[Optional[str]]  (Text, nullable=True)
#    - type:        Mapped[str]  (String, nullable=False)
#    - created_at:  Mapped[datetime]  (DateTime, nullable=False, auto-set)
#    - updated_at:  Mapped[datetime]  (DateTime, nullable=False, auto-set)
#
# 3. WORKFLOW-SPECIFIC METADATA STORAGE STRATEGY
#    There is no separate JSONB column on Artifact for extended fields.
#    Workflow-specific fields (definition_hash, stage_count, etc.) are stored
#    via the one-to-one ArtifactMetadata relationship:
#
#      artifact_metadata.metadata_json  — Text column storing a JSON blob
#
#    Helper methods on ArtifactMetadata handle serialization:
#      - set_metadata_dict({"definition_hash": "abc123", "stage_count": 3})
#      - get_metadata_dict()  -> dict or None
#
#    The artifact_metadata row is optional (nullable one-to-one via selectin
#    loading). It should be created alongside the Artifact row when a workflow
#    record is first cached. The full YAML frontmatter blob from SWDL files
#    can be stored verbatim in metadata_json; description and tags columns
#    provide fast-access denormalised copies.
#
# 4. DEDICATED Workflow / WorkflowStage / WorkflowExecution MODELS EXIST
#    The standalone workflow execution engine (WAW-P1.1) already has its own
#    ORM models (workflows, workflow_stages, workflow_executions, etc.).
#    The Artifact row with type='workflow' serves as the *collection-level
#    identity record* — discoverable, versioned, deployable — while the
#    Workflow model is the *parsed definition* used at runtime. They are
#    linked by convention (matching name/source), not a FK.
#
# TESTING APPROACH NOTE
# ---------------------
# Base.metadata.create_all() cannot be used against SQLite for this codebase
# because several unrelated tables use the PostgreSQL-only TSVECTOR column type
# (e.g. marketplace_catalog_entries.search_vector). SQLite's DDL compiler
# raises UnsupportedCompilationError when it encounters those tables.
#
# Instead, tests that require database persistence use selective Table.create()
# to create only the tables in the FK dependency chain for Artifact
# (projects -> artifacts -> artifact_metadata). This avoids touching any
# TSVECTOR-using table while still providing real SQLite-backed persistence
# tests for the relevant models.
"""

from __future__ import annotations

import json
from typing import Generator

import pytest
from sqlalchemy import CheckConstraint, inspect as sa_inspect
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import Artifact, ArtifactMetadata, Base, Project


# ---------------------------------------------------------------------------
# Fixtures — selective table creation to avoid TSVECTOR DDL failure on SQLite
# ---------------------------------------------------------------------------

# Tables in FK dependency order, excluding any that use TSVECTOR or other
# PostgreSQL-only DDL types.
_TABLES_NEEDED = [
    "projects",
    "artifacts",
    "artifact_metadata",
]


@pytest.fixture(scope="module")
def engine():
    """In-memory SQLite engine with only the tables required for Artifact tests."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create only the tables this test module needs, in dependency order.
    # Avoids the UnsupportedCompilationError from TSVECTOR columns in other tables.
    meta = Base.metadata
    with eng.begin() as conn:
        for table_name in _TABLES_NEEDED:
            meta.tables[table_name].create(conn, checkfirst=True)

    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    """Fresh session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    sess = Session_()
    yield sess
    sess.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def project(session: Session) -> Project:
    """Minimal Project row required for Artifact FK."""
    proj = Project(
        id="proj-waw-p12-test",
        name="WAW-P1.2 validation project",
        path="/tmp/waw-p12",
        status="active",
    )
    session.add(proj)
    session.flush()
    return proj


# ---------------------------------------------------------------------------
# Tests — model-level validation (no DB required)
# ---------------------------------------------------------------------------


class TestArtifactModelDefinition:
    """Static assertions about the Artifact model definition itself."""

    def test_workflow_in_check_constraint(self) -> None:
        """'workflow' appears in the check_artifact_type CHECK constraint."""
        table = Artifact.__table__
        check_constraints = [
            c for c in table.constraints if isinstance(c, CheckConstraint)
        ]
        assert check_constraints, "Expected at least one CheckConstraint on artifacts"

        type_constraint = next(
            (c for c in check_constraints if "check_artifact_type" in (c.name or "")),
            None,
        )
        assert type_constraint is not None, "check_artifact_type constraint not found"

        # The constraint text must contain 'workflow'
        constraint_text = str(type_constraint.sqltext)
        assert "'workflow'" in constraint_text, (
            f"'workflow' not found in check_artifact_type: {constraint_text!r}"
        )

    def test_required_columns_exist(self) -> None:
        """All columns required for workflow records exist on the Artifact table."""
        table = Artifact.__table__
        col_names = {c.name for c in table.columns}
        for required in ("name", "description", "type", "created_at", "updated_at"):
            assert required in col_names, f"Column '{required}' missing from Artifact"

    def test_type_column_is_not_nullable(self) -> None:
        """Artifact.type is non-nullable (workflows must always have a type)."""
        col = Artifact.__table__.c["type"]
        assert not col.nullable, "Artifact.type must be non-nullable"

    def test_name_column_is_not_nullable(self) -> None:
        """Artifact.name is non-nullable."""
        col = Artifact.__table__.c["name"]
        assert not col.nullable, "Artifact.name must be non-nullable"

    def test_description_column_is_nullable(self) -> None:
        """Artifact.description is nullable (optional for workflows)."""
        col = Artifact.__table__.c["description"]
        assert col.nullable, "Artifact.description should be nullable"

    def test_artifact_metadata_relationship_exists(self) -> None:
        """Artifact has an 'artifact_metadata' relationship for extended fields."""
        mapper = sa_inspect(Artifact)
        rel_names = {r.key for r in mapper.relationships}
        assert "artifact_metadata" in rel_names, (
            "Artifact.artifact_metadata relationship not found"
        )

    def test_artifact_metadata_is_one_to_one(self) -> None:
        """artifact_metadata relationship is uselist=False (one-to-one)."""
        mapper = sa_inspect(Artifact)
        rel = mapper.relationships["artifact_metadata"]
        assert not rel.uselist, (
            "Artifact.artifact_metadata must be uselist=False (one-to-one)"
        )


# ---------------------------------------------------------------------------
# Tests — database-backed persistence
# ---------------------------------------------------------------------------


class TestArtifactWorkflowPersistence:
    """Verify Artifact with type='workflow' can be persisted and retrieved."""

    def test_workflow_type_persisted_and_retrieved(
        self, session: Session, project: Project
    ) -> None:
        """Artifact with type='workflow' round-trips through SQLite correctly."""
        artifact = Artifact(
            id="wf:my-pipeline",
            project_id=project.id,
            name="my-pipeline",
            type="workflow",
            source="github:org/repo/.claude/workflows/my-pipeline.yml",
            description="Example pipeline workflow",
        )
        session.add(artifact)
        session.flush()

        retrieved = session.get(Artifact, "wf:my-pipeline")
        assert retrieved is not None
        assert retrieved.type == "workflow"
        assert retrieved.name == "my-pipeline"
        assert retrieved.description == "Example pipeline workflow"

    def test_timestamps_auto_populated(
        self, session: Session, project: Project
    ) -> None:
        """created_at and updated_at are set automatically for workflow rows."""
        artifact = Artifact(
            id="wf:ts-check",
            project_id=project.id,
            name="ts-check-workflow",
            type="workflow",
        )
        session.add(artifact)
        session.flush()

        row = session.get(Artifact, "wf:ts-check")
        assert row is not None
        assert row.created_at is not None
        assert row.updated_at is not None

    def test_optional_columns_default_to_none(
        self, session: Session, project: Project
    ) -> None:
        """Optional workflow columns (source, versions, etc.) default to None."""
        artifact = Artifact(
            id="wf:null-check",
            project_id=project.id,
            name="null-check-workflow",
            type="workflow",
        )
        session.add(artifact)
        session.flush()

        row = session.get(Artifact, "wf:null-check")
        assert row is not None
        assert row.description is None
        assert row.source is None
        assert row.deployed_version is None
        assert row.upstream_version is None


class TestArtifactMetadataWorkflowStorage:
    """Verify workflow-specific metadata is stored via ArtifactMetadata.metadata_json."""

    def test_workflow_metadata_round_trips(
        self, session: Session, project: Project
    ) -> None:
        """definition_hash and stage_count survive a set/get round-trip."""
        artifact = Artifact(
            id="wf:meta-rt",
            project_id=project.id,
            name="meta-rt-workflow",
            type="workflow",
            description="Workflow with extended metadata",
        )
        session.add(artifact)
        session.flush()

        workflow_meta = {
            "definition_hash": "sha256:abcdef1234567890",
            "stage_count": 4,
            "stages": ["fetch", "lint", "test", "deploy"],
            "swdl_version": "1.0",
        }
        meta_row = ArtifactMetadata(artifact_id=artifact.id)
        meta_row.set_metadata_dict(workflow_meta)
        meta_row.description = artifact.description
        meta_row.set_tags_list(["ci", "pipeline"])
        session.add(meta_row)
        session.flush()

        retrieved = session.get(ArtifactMetadata, artifact.id)
        assert retrieved is not None

        parsed = retrieved.get_metadata_dict()
        assert parsed is not None
        assert parsed["definition_hash"] == "sha256:abcdef1234567890"
        assert parsed["stage_count"] == 4
        assert parsed["stages"] == ["fetch", "lint", "test", "deploy"]
        assert parsed["swdl_version"] == "1.0"
        assert retrieved.get_tags_list() == ["ci", "pipeline"]

    def test_metadata_json_column_stores_string(
        self, session: Session, project: Project
    ) -> None:
        """metadata_json is stored as a Text (JSON string), not a dict object."""
        artifact = Artifact(
            id="wf:json-raw",
            project_id=project.id,
            name="json-raw-workflow",
            type="workflow",
        )
        session.add(artifact)
        session.flush()

        meta_row = ArtifactMetadata(artifact_id=artifact.id)
        meta_row.set_metadata_dict({"definition_hash": "abc", "stage_count": 2})
        session.add(meta_row)
        session.flush()

        retrieved = session.get(ArtifactMetadata, artifact.id)
        assert retrieved is not None

        # The underlying column is Text — a raw JSON string, not a Python dict.
        raw = retrieved.metadata_json
        assert isinstance(raw, str), (
            f"metadata_json must be a str, got {type(raw).__name__}"
        )
        decoded = json.loads(raw)
        assert decoded["stage_count"] == 2

    def test_to_dict_surfaces_metadata(
        self, session: Session, project: Project
    ) -> None:
        """ArtifactMetadata.to_dict() surfaces workflow fields correctly.

        Note: Artifact.to_dict() triggers selectin loads for composite_memberships
        and other relationships whose tables are not created in this SQLite-only
        fixture. We therefore test ArtifactMetadata.to_dict() directly, which is
        the actual call path that surfaces workflow metadata to callers.
        """
        artifact = Artifact(
            id="wf:to-dict",
            project_id=project.id,
            name="to-dict-workflow",
            type="workflow",
            description="to_dict smoke-test",
        )
        session.add(artifact)
        session.flush()

        meta_row = ArtifactMetadata(artifact_id=artifact.id)
        meta_row.set_metadata_dict({"definition_hash": "deadbeef", "stage_count": 1})
        meta_row.description = "to_dict smoke-test"
        meta_row.set_tags_list(["workflow"])
        session.add(meta_row)
        session.flush()

        # Test ArtifactMetadata.to_dict() — the path used by Artifact.to_dict()
        # when artifact_metadata is loaded (lazy="selectin" in production).
        d = meta_row.to_dict()
        assert d["artifact_id"] == "wf:to-dict"
        assert d["metadata"] is not None
        assert d["metadata"]["definition_hash"] == "deadbeef"
        assert d["metadata"]["stage_count"] == 1
        assert "workflow" in d["tags"]
