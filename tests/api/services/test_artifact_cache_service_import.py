"""Regression tests for import-time cache population helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.orm import sessionmaker

from skillmeat.api.services.artifact_cache_service import (
    populate_collection_artifact_from_import,
)
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    DEFAULT_COLLECTION_ID,
    Project,
    create_db_engine,
)


def test_non_composite_import_creates_artifact_row_and_sentinel(tmp_path):
    """Import cache population should self-heal when Artifact rows are missing."""
    db_path = tmp_path / "cache.db"
    engine = create_db_engine(str(db_path))
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = SessionLocal()
    try:
        session.add(Collection(id=DEFAULT_COLLECTION_ID, name="Default Collection"))
        session.commit()

        artifact_mgr = MagicMock()
        artifact_mgr.show.return_value = SimpleNamespace(
            metadata=SimpleNamespace(
                description="Demo skill",
                author="Tester",
                license="MIT",
                tools=["bash"],
                version="1.0.0",
            ),
            tags=["demo"],
            resolved_sha="a" * 40,
            resolved_version="1.0.0",
        )

        entry = SimpleNamespace(
            artifact_type="skill",
            name="demo-skill",
            description="Demo skill",
            upstream_url="https://github.com/example/repo/tree/main/skills/demo-skill",
            tags=["demo"],
        )

        association = populate_collection_artifact_from_import(
            session=session,
            artifact_mgr=artifact_mgr,
            collection_id=DEFAULT_COLLECTION_ID,
            entry=entry,
        )

        assert association.collection_id == DEFAULT_COLLECTION_ID

        artifact_row = (
            session.query(Artifact).filter(Artifact.id == "skill:demo-skill").first()
        )
        assert artifact_row is not None
        assert artifact_row.project_id == "collection_artifacts_global"

        sentinel = (
            session.query(Project)
            .filter(Project.id == "collection_artifacts_global")
            .first()
        )
        assert sentinel is not None
    finally:
        session.close()
