"""Regression tests for marketplace composite child linking."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm import sessionmaker

from skillmeat.api.routers.marketplace_sources import _import_composite_children
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
)
from skillmeat.core.marketplace.import_coordinator import (
    ConflictStrategy,
    ImportEntry,
    ImportResult,
    ImportStatus,
)

_SENTINEL_PROJECT_ID = "collection_artifacts_global"


class _DummyImportContext:
    def mark_imported(self, entry_ids, import_id):
        return len(entry_ids)


class _DummyTransactionHandler:
    @contextmanager
    def import_transaction(self, source_id):
        yield _DummyImportContext()


class _FakeImportCoordinator:
    """Returns deterministic child import entries for helper testing."""

    def __init__(self, collection_name=None, collection_mgr=None):
        self.collection_name = collection_name
        self.collection_mgr = collection_mgr

    def import_entries(self, entries, source_id, strategy, source_ref):
        source_entry = entries[0]
        imported_name = source_entry["name"]

        # Simulate rename conflict resolution for one child.
        if imported_name == "child-two" and strategy == ConflictStrategy.RENAME:
            imported_name = "child-two-renamed"

        result_entry = ImportEntry(
            catalog_entry_id=source_entry["id"],
            artifact_type=source_entry["artifact_type"],
            name=imported_name,
            upstream_url=source_entry["upstream_url"],
            status=ImportStatus.SUCCESS,
        )
        return ImportResult(
            import_id=f"imp-{source_entry['id']}",
            source_id=source_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            entries=[result_entry],
        )


def _populate_artifact_row(session, _artifact_mgr, _collection_id, entry):
    existing_project = (
        session.query(Project)
        .filter(Project.id == _SENTINEL_PROJECT_ID)
        .first()
    )
    if existing_project is None:
        session.add(
            Project(
                id=_SENTINEL_PROJECT_ID,
                name="Collection Artifacts",
                path="~/.skillmeat/collections",
                description="Sentinel project for collection artifacts",
                status="active",
            )
        )
        session.flush()

    artifact_id = f"{entry.artifact_type}:{entry.name}"
    existing = session.query(Artifact).filter(Artifact.id == artifact_id).first()
    if existing is None:
        session.add(
            Artifact(
                id=artifact_id,
                uuid=uuid.uuid4().hex,
                project_id=_SENTINEL_PROJECT_ID,
                name=entry.name,
                type=entry.artifact_type,
                source=entry.upstream_url,
            )
        )
        session.flush()


def test_child_import_links_and_commits_memberships_with_resolved_names(tmp_path):
    """Membership rows should persist and use post-conflict child IDs."""
    db_path = tmp_path / "cache.db"
    engine = create_db_engine(str(db_path))
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = SessionLocal()
    try:
        session.add(Collection(id="default", name="default"))
        session.add(
            CompositeArtifact(
                id="composite:plugin-x",
                collection_id="default",
                composite_type="plugin",
                display_name="plugin-x",
            )
        )
        session.commit()

        composite_catalog = SimpleNamespace(
            id="cat-composite",
            artifact_type="composite",
            name="plugin-x",
            path="plugins/plugin-x",
        )
        child_one = SimpleNamespace(
            id="cat-child-one",
            artifact_type="skill",
            name="child-one",
            upstream_url="https://github.com/example/repo/tree/main/skills/child-one",
            path="plugins/plugin-x/skills/child-one",
            description="Child one",
            path_segments=None,
        )
        child_two = SimpleNamespace(
            id="cat-child-two",
            artifact_type="command",
            name="child-two",
            upstream_url="https://github.com/example/repo/tree/main/commands/child-two",
            path="plugins/plugin-x/commands/child-two",
            description="Child two",
            path_segments=None,
        )

        catalog_repo = SimpleNamespace(
            get_by_id=lambda entry_id: (
                composite_catalog if entry_id == "cat-composite" else None
            ),
            list_by_source=lambda _source_id: [
                composite_catalog,
                child_one,
                child_two,
            ],
        )

        composite_entry = ImportEntry(
            catalog_entry_id="cat-composite",
            artifact_type="composite",
            name="plugin-x",
            upstream_url="https://github.com/example/repo/tree/main/plugins/plugin-x",
            status=ImportStatus.SUCCESS,
        )

        with patch(
            "skillmeat.api.routers.marketplace_sources.ImportCoordinator",
            _FakeImportCoordinator,
        ):
            children_added = _import_composite_children(
                session=session,
                artifact_mgr=SimpleNamespace(),
                collection_mgr=SimpleNamespace(),
                catalog_repo=catalog_repo,
                transaction_handler=_DummyTransactionHandler(),
                source_id="src-1",
                source_ref="main",
                composite_entry=composite_entry,
                strategy=ConflictStrategy.RENAME,
                populate_fn=_populate_artifact_row,
            )

        assert children_added == 2
    finally:
        session.close()

    verify_session = SessionLocal()
    try:
        memberships = (
            verify_session.query(CompositeMembership, Artifact)
            .join(Artifact, Artifact.uuid == CompositeMembership.child_artifact_uuid)
            .filter(CompositeMembership.composite_id == "composite:plugin-x")
            .order_by(CompositeMembership.position.asc())
            .all()
        )
        assert len(memberships) == 2

        linked_child_ids = [artifact.id for _, artifact in memberships]
        assert linked_child_ids == [
            "skill:child-one",
            "command:child-two-renamed",
        ]
    finally:
        verify_session.close()
