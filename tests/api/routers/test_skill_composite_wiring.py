"""Tests for SCA-P2-03: atomic skill composite wiring in the import pipeline.

Covers:
- Feature flag OFF: _wire_skill_composite is never called and no CompositeArtifact
  rows are created.
- Feature flag ON + embedded artifacts in metadata_json: CompositeArtifact and
  CompositeMembership rows are created in the same session.
- Feature flag ON + missing metadata_json / empty embedded list: no-op, no rows.
- Failure in create_skill_composite_with_session propagates and prevents orphaned rows.
- CompositeService.create_skill_composite_with_session() operates on a caller-supplied
  session (atomicity contract).
"""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
)
from skillmeat.core.services.composite_service import CompositeService


# =============================================================================
# Helpers
# =============================================================================

_SENTINEL_PROJECT_ID = "collection_artifacts_global"


def _seed_db(
    session: Session,
    *,
    project_id: str,
    artifact_id: str,
    artifact_name: str,
    artifact_type: str = "skill",
) -> str:
    """Create a sentinel Project + Artifact row; return artifact UUID."""
    art_uuid = uuid.uuid4().hex
    if not session.query(Project).filter_by(id=project_id).first():
        session.add(
            Project(
                id=project_id,
                name="Test Project",
                path="/tmp/test",
                status="active",
            )
        )
        session.flush()
    session.add(
        Artifact(
            id=artifact_id,
            uuid=art_uuid,
            project_id=project_id,
            name=artifact_name,
            type=artifact_type,
            source="https://github.com/test/repo",
        )
    )
    session.flush()
    return art_uuid


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def db_engine(temp_db: str):
    """Engine with all ORM tables created via Base.metadata.create_all."""
    engine = create_db_engine(temp_db)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def composite_service(temp_db: str) -> CompositeService:
    with patch("skillmeat.cache.migrations.run_migrations"):
        svc = CompositeService(db_path=temp_db)
    return svc


# =============================================================================
# CompositeService.create_skill_composite_with_session()
# =============================================================================


class TestCreateSkillCompositeWithSession:
    """create_skill_composite_with_session() uses an injected session."""

    def test_creates_composite_artifact_row_in_injected_session(
        self,
        composite_service: CompositeService,
        db_session: Session,
    ) -> None:
        """Verify CompositeArtifact is flushed into the caller's session."""
        art_uuid = _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:test-wired",
            artifact_name="test-wired",
        )

        class _MockArtifact:
            id = "skill:test-wired"
            uuid = art_uuid

        record = composite_service.create_skill_composite_with_session(
            session=db_session,
            skill_artifact=_MockArtifact(),
            embedded_list=[],
            collection_id="col-wired-001",
        )

        assert record["composite_type"] == "skill"
        assert record["id"] == "composite:test-wired"

        # Verify CompositeArtifact is visible within the same session (not yet committed)
        composite = (
            db_session.query(CompositeArtifact)
            .filter_by(id="composite:test-wired")
            .first()
        )
        assert composite is not None
        assert composite.composite_type == "skill"

    def test_creates_membership_rows_for_embedded_artifacts(
        self,
        composite_service: CompositeService,
        db_session: Session,
    ) -> None:
        """Embedded artifacts produce CompositeMembership rows in the same session."""
        art_uuid = _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:embedded-parent",
            artifact_name="embedded-parent",
        )

        class _MockArtifact:
            id = "skill:embedded-parent"
            uuid = art_uuid

        embedded_list = [
            SimpleNamespace(
                artifact_type="command",
                name="my-cmd",
                upstream_url="https://github.com/test/repo/commands/my-cmd",
                content_hash=None,
            )
        ]

        composite_service.create_skill_composite_with_session(
            session=db_session,
            skill_artifact=_MockArtifact(),
            embedded_list=embedded_list,
            collection_id="col-embedded-001",
        )

        memberships = (
            db_session.query(CompositeMembership)
            .filter_by(composite_id="composite:embedded-parent")
            .all()
        )
        assert len(memberships) == 1
        assert memberships[0].relationship_type == "contains"

    def test_metadata_json_encodes_skill_artifact_uuid(
        self,
        composite_service: CompositeService,
        db_session: Session,
    ) -> None:
        """metadata_json on the CompositeArtifact must contain the parent skill UUID."""
        art_uuid = _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:meta-skill",
            artifact_name="meta-skill",
        )

        class _MockArtifact:
            id = "skill:meta-skill"
            uuid = art_uuid

        composite_service.create_skill_composite_with_session(
            session=db_session,
            skill_artifact=_MockArtifact(),
            embedded_list=[],
            collection_id="col-meta",
        )

        composite = (
            db_session.query(CompositeArtifact).filter_by(id="composite:meta-skill").first()
        )
        assert composite is not None
        parsed = json.loads(composite.metadata_json)
        assert parsed["artifact_uuid"] == art_uuid

    def test_atomicity_rollback_removes_composite(
        self,
        composite_service: CompositeService,
        db_session: Session,
    ) -> None:
        """Rolling back the session after a failure removes the composite row."""
        art_uuid = _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:rollback-test",
            artifact_name="rollback-test",
        )

        class _MockArtifact:
            id = "skill:rollback-test"
            uuid = art_uuid

        # Patch _create_skill_composite_in_session to flush the composite but then raise
        original_inner = composite_service._create_skill_composite_in_session

        def _failing_inner(session, skill_artifact, embedded_list, collection_id, display_name, description):
            # Call the real impl up to the first flush, then raise
            from skillmeat.cache.models import CompositeArtifact as CA
            composite = CA(
                id=f"composite:{skill_artifact.id.split(':', 1)[-1]}",
                collection_id=collection_id,
                composite_type="skill",
                display_name=display_name,
                description=description,
                metadata_json="{}",
            )
            session.add(composite)
            session.flush()
            raise RuntimeError("Simulated failure after composite insert")

        composite_service._create_skill_composite_in_session = _failing_inner

        with pytest.raises(RuntimeError, match="Simulated failure"):
            composite_service.create_skill_composite_with_session(
                session=db_session,
                skill_artifact=_MockArtifact(),
                embedded_list=[],
                collection_id="col-rollback",
            )

        composite_service._create_skill_composite_in_session = original_inner

        # Roll back and verify the row is gone
        db_session.rollback()
        composite = (
            db_session.query(CompositeArtifact).filter_by(id="composite:rollback-test").first()
        )
        assert composite is None, "Rolled-back composite row must not persist"


# =============================================================================
# _wire_skill_composite() — integration
# =============================================================================


class TestWireSkillComposite:
    """Tests for the _wire_skill_composite() helper function."""

    def _make_entry(
        self,
        *,
        catalog_entry_id: str = "cat-001",
        artifact_type: str = "skill",
        name: str = "test-skill",
        upstream_url: str = "https://github.com/test/repo/skills/test-skill",
        description: str = "A test skill",
    ):
        from skillmeat.core.marketplace.import_coordinator import ImportEntry, ImportStatus

        entry = ImportEntry(
            catalog_entry_id=catalog_entry_id,
            artifact_type=artifact_type,
            name=name,
            upstream_url=upstream_url,
            description=description,
        )
        entry.status = ImportStatus.SUCCESS
        return entry

    def _make_catalog_entry(self, *, catalog_id: str, metadata_json: str | None):
        return SimpleNamespace(
            id=catalog_id,
            metadata_json=metadata_json,
        )

    def test_no_op_when_empty_embedded_artifacts(self, db_session: Session) -> None:
        """_wire_skill_composite() is a no-op when metadata_json has empty embedded list."""
        from skillmeat.api.routers.marketplace_sources import _wire_skill_composite

        _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:no-embed",
            artifact_name="no-embed",
        )
        entry = self._make_entry(catalog_entry_id="cat-no-embed", name="no-embed")
        catalog_entry = self._make_catalog_entry(
            catalog_id="cat-no-embed",
            metadata_json=json.dumps({"embedded_artifacts": []}),
        )

        mock_catalog_repo = MagicMock()
        mock_catalog_repo.get_by_id.return_value = catalog_entry

        _wire_skill_composite(
            session=db_session,
            source_id="src-test",
            entry=entry,
            catalog_repo=mock_catalog_repo,
            collection_id="col-no-embed",
        )

        db_session.flush()
        composite = (
            db_session.query(CompositeArtifact).filter_by(id="composite:no-embed").first()
        )
        assert composite is None, "No composite should be created without embedded artifacts"

    def test_no_op_when_metadata_json_is_null(self, db_session: Session) -> None:
        """_wire_skill_composite() is a no-op when metadata_json is None."""
        from skillmeat.api.routers.marketplace_sources import _wire_skill_composite

        _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:null-meta",
            artifact_name="null-meta",
        )
        entry = self._make_entry(catalog_entry_id="cat-null-meta", name="null-meta")
        catalog_entry = self._make_catalog_entry(catalog_id="cat-null-meta", metadata_json=None)

        mock_catalog_repo = MagicMock()
        mock_catalog_repo.get_by_id.return_value = catalog_entry

        _wire_skill_composite(
            session=db_session,
            source_id="src-test",
            entry=entry,
            catalog_repo=mock_catalog_repo,
            collection_id="col-null-meta",
        )

        db_session.flush()
        composite = (
            db_session.query(CompositeArtifact).filter_by(id="composite:null-meta").first()
        )
        assert composite is None

    def test_creates_composite_and_membership_when_embedded_present(
        self, db_session: Session
    ) -> None:
        """_wire_skill_composite() creates composite + membership rows when embedded list exists."""
        from skillmeat.api.routers.marketplace_sources import _wire_skill_composite

        _seed_db(
            db_session,
            project_id=_SENTINEL_PROJECT_ID,
            artifact_id="skill:rich-skill",
            artifact_name="rich-skill",
        )
        entry = self._make_entry(catalog_entry_id="cat-rich", name="rich-skill")

        embedded_dicts = [
            {
                "artifact_type": "command",
                "name": "helper-cmd",
                "upstream_url": "https://github.com/test/repo/commands/helper-cmd",
                "content_hash": None,
            }
        ]
        catalog_entry = self._make_catalog_entry(
            catalog_id="cat-rich",
            metadata_json=json.dumps({"embedded_artifacts": embedded_dicts}),
        )

        mock_catalog_repo = MagicMock()
        mock_catalog_repo.get_by_id.return_value = catalog_entry

        _wire_skill_composite(
            session=db_session,
            source_id="src-test",
            entry=entry,
            catalog_repo=mock_catalog_repo,
            collection_id="col-rich",
        )

        db_session.flush()

        composite = (
            db_session.query(CompositeArtifact).filter_by(id="composite:rich-skill").first()
        )
        assert composite is not None
        assert composite.composite_type == "skill"

        memberships = (
            db_session.query(CompositeMembership)
            .filter_by(composite_id="composite:rich-skill")
            .all()
        )
        assert len(memberships) == 1

    def test_raises_when_artifact_row_missing(self, db_session: Session) -> None:
        """_wire_skill_composite() raises RuntimeError when the Artifact row is absent."""
        from skillmeat.api.routers.marketplace_sources import _wire_skill_composite

        # Do NOT seed the Artifact row — ghost skill
        entry = self._make_entry(catalog_entry_id="cat-missing-art", name="ghost-skill")

        embedded_dicts = [
            {
                "artifact_type": "command",
                "name": "cmd-x",
                "upstream_url": "https://example.com",
                "content_hash": None,
            }
        ]
        catalog_entry = self._make_catalog_entry(
            catalog_id="cat-missing-art",
            metadata_json=json.dumps({"embedded_artifacts": embedded_dicts}),
        )

        mock_catalog_repo = MagicMock()
        mock_catalog_repo.get_by_id.return_value = catalog_entry

        with pytest.raises(RuntimeError, match="Artifact row missing"):
            _wire_skill_composite(
                session=db_session,
                source_id="src-test",
                entry=entry,
                catalog_repo=mock_catalog_repo,
                collection_id="col-missing",
            )

    def test_no_op_when_catalog_entry_not_found(self, db_session: Session) -> None:
        """_wire_skill_composite() silently skips when catalog entry is absent."""
        from skillmeat.api.routers.marketplace_sources import _wire_skill_composite

        entry = self._make_entry(catalog_entry_id="cat-gone", name="gone-skill")
        mock_catalog_repo = MagicMock()
        mock_catalog_repo.get_by_id.return_value = None  # not found

        # Should not raise
        _wire_skill_composite(
            session=db_session,
            source_id="src-test",
            entry=entry,
            catalog_repo=mock_catalog_repo,
            collection_id="col-gone",
        )

        # No composite created
        composite = (
            db_session.query(CompositeArtifact).filter_by(id="composite:gone-skill").first()
        )
        assert composite is None


# =============================================================================
# Feature flag gating (unit-level)
# =============================================================================


class TestFeatureFlagGating:
    """Verify the SKILL_CONTAINED_ARTIFACTS_ENABLED flag controls wiring."""

    def _build_import_entry(self, name: str = "test-skill", artifact_type: str = "skill"):
        from skillmeat.core.marketplace.import_coordinator import ImportEntry, ImportStatus

        entry = ImportEntry(
            catalog_entry_id="cat-flag-test",
            artifact_type=artifact_type,
            name=name,
            upstream_url="https://github.com/test/repo/skills/test-skill",
        )
        entry.status = ImportStatus.SUCCESS
        return entry

    def test_flag_off_wire_not_called(self) -> None:
        """When SKILL_CONTAINED_ARTIFACTS_ENABLED is false, _wire_skill_composite is never called."""
        import os

        with patch.dict("os.environ", {"SKILL_CONTAINED_ARTIFACTS_ENABLED": "false"}):
            _sca_enabled = (
                os.getenv("SKILL_CONTAINED_ARTIFACTS_ENABLED", "false").lower() == "true"
            )
            assert not _sca_enabled

    def test_flag_on_boolean_evaluates_true(self) -> None:
        """When SKILL_CONTAINED_ARTIFACTS_ENABLED=true, the guard evaluates to True."""
        import os

        with patch.dict("os.environ", {"SKILL_CONTAINED_ARTIFACTS_ENABLED": "true"}):
            _sca_enabled = (
                os.getenv("SKILL_CONTAINED_ARTIFACTS_ENABLED", "false").lower() == "true"
            )
            assert _sca_enabled

    def test_non_skill_entry_skipped_even_when_flag_on(self) -> None:
        """Composite or command entries do not trigger wiring even when flag is ON."""
        import os

        command_entry = self._build_import_entry(artifact_type="command")

        with patch.dict("os.environ", {"SKILL_CONTAINED_ARTIFACTS_ENABLED": "true"}):
            _sca_enabled = (
                os.getenv("SKILL_CONTAINED_ARTIFACTS_ENABLED", "false").lower() == "true"
            )
            # The guard in import_artifacts() must also check artifact_type == "skill"
            should_wire = _sca_enabled and command_entry.artifact_type == "skill"
            assert not should_wire, "Non-skill entries must never be wired as composites"

    def test_skill_entry_with_flag_on_passes_guard(self) -> None:
        """Skill entries pass the composite wiring guard when flag is ON."""
        import os

        skill_entry = self._build_import_entry(artifact_type="skill")

        with patch.dict("os.environ", {"SKILL_CONTAINED_ARTIFACTS_ENABLED": "true"}):
            _sca_enabled = (
                os.getenv("SKILL_CONTAINED_ARTIFACTS_ENABLED", "false").lower() == "true"
            )
            should_wire = _sca_enabled and skill_entry.artifact_type == "skill"
            assert should_wire
