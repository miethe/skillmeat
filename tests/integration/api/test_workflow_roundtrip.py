"""End-to-end round-trip integration test for workflow-artifact sync.

WAW-P5.3: Verifies the complete lifecycle of a workflow as it flows through
all layers of the workflow-artifact wiring feature:

    1. WorkflowService.create()  →  artifact row auto-created via sync hook
    2. Artifact record matches workflow data (name, description, type='workflow')
    3. Add workflow to a DeploymentSet  →  member has workflow_id set
    4. WorkflowService.update()  →  artifact record is updated in-place
    5. WorkflowService.delete()  →  artifact record is removed
    6. DeploymentSet members referencing the workflow are cleaned up

Design notes
------------
- Uses a real SQLite database in a temporary directory so that actual SQL
  constraints and ORM behaviour are exercised (not just mock stubs).
- Both ``WorkflowArtifactSyncRepository`` and ``WorkflowRepository`` /
  ``DeploymentSetRepository`` are pointed at the **same** temp DB so that
  FK relationships work correctly.
- ``WorkflowService`` is constructed with a real ``WorkflowArtifactSyncService``
  instance so the sync hooks actually fire on each CRUD operation.
- The test does **not** hit the HTTP layer; all assertions are made directly
  against the DB via repository queries so the coverage is tightly scoped to
  the sync service contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.orm import sessionmaker as _sessionmaker

from skillmeat.cache.models import (
    Artifact,
    ArtifactMetadata,
    Base,
    DeploymentSet,
    DeploymentSetMember,
    DeploymentSetTag,
    Project,
    Tag,
    Workflow,
    WorkflowStage,
    create_db_engine,
)
from skillmeat.cache.repositories import DeploymentSetRepository
from skillmeat.cache.workflow_repository import WorkflowRepository
from skillmeat.core.services.workflow_artifact_sync_repository import (
    WorkflowArtifactSyncRepository,
)
from skillmeat.core.services.workflow_artifact_sync_service import (
    WorkflowArtifactSyncService,
)
from skillmeat.core.workflow.service import WorkflowService


# ---------------------------------------------------------------------------
# Minimal valid SWDL YAML used across all test scenarios
# ---------------------------------------------------------------------------

_WORKFLOW_YAML_V1 = """\
workflow:
  id: roundtrip-wf
  name: Round-Trip Workflow
  description: Integration test workflow - version 1
  version: "1.0.0"

stages:
  - id: step-one
    name: Step One
    type: agent
    roles:
      primary:
        artifact: "skill:some-skill"
"""

_WORKFLOW_YAML_V2 = """\
workflow:
  id: roundtrip-wf
  name: Round-Trip Workflow
  description: Integration test workflow - version 2
  version: "2.0.0"

stages:
  - id: step-one
    name: Step One (updated)
    type: agent
    roles:
      primary:
        artifact: "skill:some-skill"
  - id: step-two
    name: Step Two
    type: agent
    roles:
      primary:
        artifact: "skill:other-skill"
    depends_on:
      - step-one
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _create_needed_tables(db_path: Path) -> None:
    """Create only the tables required by this test suite.

    ``Base.metadata.create_all()`` fails on SQLite because the
    ``marketplace_catalog_entries.search_vector`` column uses the
    PostgreSQL-only ``TSVECTOR`` type.  We work around this by temporarily
    patching that column's type to ``Text`` for the duration of the
    ``create_all`` call so SQLite can render it.

    BaseRepository.__init__ will call create_tables() again when repositories
    are instantiated, so we patch ``skillmeat.cache.models.create_tables`` to
    use our SQLite-safe variant throughout the fixture lifetime.  The patch is
    applied at module level so that all downstream imports see the replacement.
    """
    import skillmeat.cache.models as _models_mod

    # Temporarily replace the TSVECTOR column type with Text so SQLite's
    # DDL compiler can render the CREATE TABLE statement.
    catalog_table = Base.metadata.tables.get("marketplace_catalog_entries")
    if catalog_table is not None:
        sv_col = catalog_table.c.get("search_vector")
        if sv_col is not None:
            original_type = sv_col.type
            sv_col.type = Text()
            try:
                engine = create_db_engine(db_path)
                Base.metadata.create_all(engine, checkfirst=True)
            finally:
                sv_col.type = original_type
        else:
            engine = create_db_engine(db_path)
            Base.metadata.create_all(engine, checkfirst=True)
    else:
        engine = create_db_engine(db_path)
        Base.metadata.create_all(engine, checkfirst=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sqlite_safe_create_tables(db_path=None):
    """Replacement for ``create_tables`` that is safe on SQLite.

    This is injected via ``monkeypatch`` to prevent BaseRepository.__init__
    from hitting the TSVECTOR compilation error when setting up test databases.
    """
    from skillmeat.cache.models import Base, create_db_engine  # noqa: PLC0415
    from sqlalchemy import Text  # noqa: PLC0415

    catalog_table = Base.metadata.tables.get("marketplace_catalog_entries")
    if catalog_table is not None:
        sv_col = catalog_table.c.get("search_vector")
        if sv_col is not None:
            original_type = sv_col.type
            sv_col.type = Text()
            try:
                engine = create_db_engine(db_path)
                Base.metadata.create_all(engine, checkfirst=True)
            finally:
                sv_col.type = original_type
            return
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine, checkfirst=True)


@pytest.fixture(autouse=True)
def _patch_create_tables(monkeypatch):
    """Patch ``create_tables`` globally for the duration of each test.

    This prevents BaseRepository.__init__ from hitting the SQLite-incompatible
    TSVECTOR compilation error when creating tables for the test database.
    """
    monkeypatch.setattr(
        "skillmeat.cache.models.create_tables", _sqlite_safe_create_tables
    )
    monkeypatch.setattr(
        "skillmeat.cache.repositories.create_tables", _sqlite_safe_create_tables
    )


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a path to a freshly-initialised SQLite cache database."""
    db_file = tmp_path / "test_cache.db"
    _create_needed_tables(db_file)
    return db_file


@pytest.fixture()
def sync_repo(tmp_db: Path) -> WorkflowArtifactSyncRepository:
    """Sync repository pointed at the temp DB."""
    return WorkflowArtifactSyncRepository(db_path=tmp_db)


@pytest.fixture()
def sync_service(sync_repo: WorkflowArtifactSyncRepository) -> WorkflowArtifactSyncService:
    """Sync service wired to the temp-DB sync repository."""
    return WorkflowArtifactSyncService(repository=sync_repo)


@pytest.fixture()
def workflow_svc(
    tmp_db: Path, sync_service: WorkflowArtifactSyncService
) -> WorkflowService:
    """WorkflowService backed by temp DB with sync hooks active."""
    return WorkflowService(db_path=str(tmp_db), sync_service=sync_service)


@pytest.fixture()
def ds_repo(tmp_db: Path) -> DeploymentSetRepository:
    """DeploymentSetRepository backed by the same temp DB."""
    return DeploymentSetRepository(db_path=tmp_db)


def _get_artifact(db_path: Path, artifact_id: str) -> Optional[Artifact]:
    """Return the Artifact ORM row for ``artifact_id``, or None."""
    engine = create_db_engine(db_path)
    Session = _sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        return session.query(Artifact).filter_by(id=artifact_id).first()
    finally:
        session.close()


def _get_artifact_metadata_json(db_path: Path, workflow_id: str) -> Optional[str]:
    """Return the raw ``metadata_json`` for the artifact linked to ``workflow_id``.

    Executes inside its own session so the data is fully loaded before the
    session closes, avoiding ``DetachedInstanceError`` on lazy relationships.
    """
    engine = create_db_engine(db_path)
    Session = _sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        row = (
            session.query(ArtifactMetadata)
            .join(Artifact, ArtifactMetadata.artifact_id == Artifact.id)
            .filter(Artifact.type == "workflow")
            .first()
        )
        return row.metadata_json if row is not None else None
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Helper — SWDL artifact id convention
# ---------------------------------------------------------------------------


def _workflow_artifact_id(name: str) -> str:
    """Return the expected artifact primary key for a workflow named ``name``."""
    return f"workflow:{name}"


# ---------------------------------------------------------------------------
# Test class — full lifecycle
# ---------------------------------------------------------------------------


class TestWorkflowRoundTrip:
    """End-to-end sync round-trip for the workflow-artifact wiring feature."""

    # ------------------------------------------------------------------
    # Step 1 + 2: Create workflow → artifact record exists with correct fields
    # ------------------------------------------------------------------

    def test_create_workflow_creates_artifact_record(
        self, workflow_svc: WorkflowService, sync_repo: WorkflowArtifactSyncRepository, tmp_db: Path
    ) -> None:
        """Creating a workflow via WorkflowService produces an artifact row."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        artifact = _get_artifact(tmp_db, _workflow_artifact_id(dto.name))

        assert artifact is not None, "Artifact row should be created after workflow.create()"

    def test_artifact_record_has_correct_name(
        self, workflow_svc: WorkflowService, tmp_db: Path
    ) -> None:
        """Artifact name matches workflow name."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        artifact = _get_artifact(tmp_db, _workflow_artifact_id(dto.name))

        assert artifact is not None
        assert artifact.name == dto.name

    def test_artifact_record_has_correct_type(
        self, workflow_svc: WorkflowService, tmp_db: Path
    ) -> None:
        """Artifact type is 'workflow'."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        artifact = _get_artifact(tmp_db, _workflow_artifact_id(dto.name))

        assert artifact is not None
        assert artifact.type == "workflow"

    def test_artifact_record_has_correct_description(
        self, workflow_svc: WorkflowService, tmp_db: Path
    ) -> None:
        """Artifact description matches workflow description from YAML."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        artifact = _get_artifact(tmp_db, _workflow_artifact_id(dto.name))

        assert artifact is not None
        assert artifact.description == "Integration test workflow - version 1"

    def test_artifact_metadata_links_workflow_id(
        self,
        workflow_svc: WorkflowService,
        sync_repo: WorkflowArtifactSyncRepository,
        tmp_db: Path,
    ) -> None:
        """ArtifactMetadata.metadata_json contains the workflow_id."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        # Verify get_artifact_by_workflow_id returns a row
        artifact = sync_repo.get_artifact_by_workflow_id(dto.id)
        assert artifact is not None, "get_artifact_by_workflow_id should find the row"

        # Read the metadata JSON in a separate session to avoid DetachedInstanceError
        # on the lazy-loaded artifact_metadata relationship.
        raw_json = _get_artifact_metadata_json(tmp_db, dto.id)
        assert raw_json is not None, "ArtifactMetadata row should exist"
        meta = json.loads(raw_json)
        assert meta.get("workflow_id") == dto.id

    # ------------------------------------------------------------------
    # Step 3: Add workflow to deployment set → member has workflow_id
    # ------------------------------------------------------------------

    def test_add_workflow_to_deployment_set(
        self,
        workflow_svc: WorkflowService,
        ds_repo: DeploymentSetRepository,
    ) -> None:
        """After adding workflow as a deployment set member, workflow_id is populated."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        # Create a deployment set in the same temp DB
        ds = ds_repo.create(name="Test Set", owner_id="test-owner")
        member = ds_repo.add_member(
            ds.id, "test-owner", workflow_id=dto.id
        )

        assert member.workflow_id == dto.id
        assert member.artifact_uuid is None
        assert member.group_id is None

    def test_deployment_set_member_appears_in_list(
        self,
        workflow_svc: WorkflowService,
        ds_repo: DeploymentSetRepository,
    ) -> None:
        """The workflow member is returned by get_members."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        ds = ds_repo.create(name="Test Set", owner_id="test-owner")
        ds_repo.add_member(ds.id, "test-owner", workflow_id=dto.id)

        members = ds_repo.get_members(ds.id, "test-owner")

        assert len(members) == 1
        assert members[0].workflow_id == dto.id

    # ------------------------------------------------------------------
    # Step 4: Update workflow → artifact record is updated
    # ------------------------------------------------------------------

    def test_update_workflow_updates_artifact_record(
        self,
        workflow_svc: WorkflowService,
        tmp_db: Path,
    ) -> None:
        """Updating a workflow re-syncs the artifact row with new data."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)
        artifact_id = _workflow_artifact_id(dto.name)

        # Capture UUID before update so we can assert it is stable
        before = _get_artifact(tmp_db, artifact_id)
        assert before is not None
        original_uuid = before.uuid

        workflow_svc.update(dto.id, yaml_content=_WORKFLOW_YAML_V2)

        after = _get_artifact(tmp_db, artifact_id)
        assert after is not None
        # Description must reflect the v2 YAML
        assert after.description == "Integration test workflow - version 2"
        # UUID should be stable (idempotent upsert)
        assert after.uuid == original_uuid

    def test_update_workflow_preserves_artifact_uuid(
        self,
        workflow_svc: WorkflowService,
        sync_repo: WorkflowArtifactSyncRepository,
    ) -> None:
        """The artifact uuid is unchanged after an update (ADR-007 stability)."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        before = sync_repo.get_artifact_by_workflow_id(dto.id)
        assert before is not None
        uuid_before = before.uuid

        workflow_svc.update(dto.id, yaml_content=_WORKFLOW_YAML_V2)

        after = sync_repo.get_artifact_by_workflow_id(dto.id)
        assert after is not None
        assert after.uuid == uuid_before

    # ------------------------------------------------------------------
    # Step 5 + 6: Delete workflow → artifact removed; deployment set cleanup
    # ------------------------------------------------------------------

    def test_delete_workflow_removes_artifact_record(
        self,
        workflow_svc: WorkflowService,
        tmp_db: Path,
    ) -> None:
        """Deleting a workflow removes the corresponding artifact row."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)
        artifact_id = _workflow_artifact_id(dto.name)

        # Verify it exists before deletion
        assert _get_artifact(tmp_db, artifact_id) is not None

        workflow_svc.delete(dto.id)

        assert _get_artifact(tmp_db, artifact_id) is None

    def test_delete_workflow_sync_repo_returns_none(
        self,
        workflow_svc: WorkflowService,
        sync_repo: WorkflowArtifactSyncRepository,
    ) -> None:
        """After deletion get_artifact_by_workflow_id returns None."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)

        assert sync_repo.get_artifact_by_workflow_id(dto.id) is not None

        workflow_svc.delete(dto.id)

        assert sync_repo.get_artifact_by_workflow_id(dto.id) is None

    def test_deployment_set_member_cleanup_after_workflow_delete(
        self,
        workflow_svc: WorkflowService,
        ds_repo: DeploymentSetRepository,
    ) -> None:
        """Deployment set member referencing the deleted workflow is removed.

        The ``DeploymentSetMember.workflow_id`` column has ``ON DELETE SET NULL``
        (or the application removes the member explicitly).  This test verifies
        that after workflow deletion the member's ``workflow_id`` is either
        cleared (set to None) or the member row is removed — either outcome
        is acceptable as long as there is no dangling hard reference.
        """
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)
        ds = ds_repo.create(name="Cleanup Test Set", owner_id="test-owner")
        member = ds_repo.add_member(ds.id, "test-owner", workflow_id=dto.id)
        member_id = member.id

        workflow_svc.delete(dto.id)

        members = ds_repo.get_members(ds.id, "test-owner")

        # Either the member row was removed OR its workflow_id was nulled out
        surviving = [m for m in members if m.id == member_id]
        if surviving:
            # Member still exists — workflow_id must be None (SET NULL cascade)
            assert surviving[0].workflow_id is None, (
                "Surviving member must have workflow_id=None after workflow deletion"
            )
        # If surviving is empty, the member was deleted — also acceptable

    # ------------------------------------------------------------------
    # Full round-trip in one test (integration smoke test)
    # ------------------------------------------------------------------

    def test_full_lifecycle_no_errors(
        self,
        workflow_svc: WorkflowService,
        sync_repo: WorkflowArtifactSyncRepository,
        ds_repo: DeploymentSetRepository,
        tmp_db: Path,
    ) -> None:
        """Full create → add to set → update → delete lifecycle completes without errors."""
        # Step 1: Create
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)
        assert _get_artifact(tmp_db, _workflow_artifact_id(dto.name)) is not None

        # Step 2: Add to deployment set
        ds = ds_repo.create(name="Full Lifecycle Set", owner_id="test-owner")
        member = ds_repo.add_member(ds.id, "test-owner", workflow_id=dto.id)
        assert member.workflow_id == dto.id

        # Step 3: Update
        updated_dto = workflow_svc.update(dto.id, yaml_content=_WORKFLOW_YAML_V2)
        artifact = _get_artifact(tmp_db, _workflow_artifact_id(dto.name))
        assert artifact is not None
        assert "version 2" in (artifact.description or "")

        # Step 4: Delete
        workflow_svc.delete(dto.id)
        assert _get_artifact(tmp_db, _workflow_artifact_id(dto.name)) is None
        assert sync_repo.get_artifact_by_workflow_id(dto.id) is None

    # ------------------------------------------------------------------
    # Idempotency: sync_all_workflows
    # ------------------------------------------------------------------

    def test_sync_all_workflows_is_idempotent(
        self,
        workflow_svc: WorkflowService,
        sync_service: WorkflowArtifactSyncService,
        sync_repo: WorkflowArtifactSyncRepository,
        tmp_db: Path,
    ) -> None:
        """Calling sync_all_workflows multiple times produces the same artifact set."""
        dto = workflow_svc.create(yaml_content=_WORKFLOW_YAML_V1)
        artifact_id = _workflow_artifact_id(dto.name)

        before_uuid = _get_artifact(tmp_db, artifact_id)
        assert before_uuid is not None

        # Run bulk sync twice
        sync_service.sync_all_workflows()
        sync_service.sync_all_workflows()

        after = _get_artifact(tmp_db, artifact_id)
        assert after is not None
        # UUID must be stable across idempotent re-syncs
        assert after.uuid == before_uuid.uuid
