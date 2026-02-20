"""Integration tests for the metadata write-through round-trip (MP-4.3).

Tests cover:
- Create group in DB → verify collection.toml updated → simulate DB reset →
  call recovery → verify group restored
- Create tag in DB → verify collection.toml updated → simulate DB reset →
  call recovery → verify tag restored
- Write-through combined: groups + tags persisted and recovered together

These tests use real filesystem (tmp_path), real ManifestManager/Collection
instances, and a real SQLite in-memory DB (via create_db_engine).  The DB
session is injected manually (no FastAPI app required).
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.api.services.artifact_cache_service import recover_collection_metadata
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection as DBCollection,
    DEFAULT_COLLECTION_ID,
    Group,
    GroupArtifact,
    Project,
    Tag,
    create_db_engine,
)
from skillmeat.core.services.manifest_sync_service import ManifestSyncService
from skillmeat.storage.manifest import ManifestManager


# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_SENTINEL_PROJECT_ID = "collection_artifacts_global"


def _make_engine_and_session(tmp_path: Path):
    """Create a real SQLite DB on disk and return (engine, SessionLocal)."""
    db_path = tmp_path / "cache.db"
    engine = create_db_engine(str(db_path))
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, SessionLocal


def _seed_default_collection(session) -> DBCollection:
    """Insert the minimal default collection row (plus sentinel project)."""
    coll = DBCollection(id=DEFAULT_COLLECTION_ID, name="default")
    sentinel = Project(
        id=_SENTINEL_PROJECT_ID,
        name="Collection Artifacts",
        path="~/.skillmeat/collections",
        status="active",
    )
    session.add_all([coll, sentinel])
    session.commit()
    return coll


def _add_artifact(session, artifact_id: str, name: str, artifact_type: str) -> Artifact:
    """Insert an Artifact row and return it."""
    row = Artifact(
        id=artifact_id,
        uuid=uuid.uuid4().hex,
        project_id=_SENTINEL_PROJECT_ID,
        name=name,
        type=artifact_type,
    )
    session.add(row)
    session.commit()
    return row


def _make_collection_toml(collection_dir: Path, name: str = "default") -> None:
    """Write a bare collection.toml to *collection_dir*."""
    collection_dir.mkdir(parents=True, exist_ok=True)
    content = (
        f"[collection]\n"
        f'name = "{name}"\n'
        f'version = "1.0.0"\n'
        f'created = "2026-01-01T00:00:00"\n'
        f'updated = "2026-01-01T00:00:00"\n'
    )
    (collection_dir / "collection.toml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manifest_manager():
    return ManifestManager()


@pytest.fixture
def svc():
    return ManifestSyncService()


# ---------------------------------------------------------------------------
# MP-4.3 integration tests
# ---------------------------------------------------------------------------


class TestGroupWriteThroughRoundTrip:
    """Integration: create group in DB → sync to TOML → reset DB → recover."""

    def test_group_write_through_and_recovery(self, svc, tmp_path, manifest_manager):
        """Full round-trip: DB group → TOML → recovered back into fresh DB."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)

        # --- Step 1: Seed DB ---
        with SessionLocal() as session:
            _seed_default_collection(session)
            art = _add_artifact(session, "skill:alpha", "alpha", "skill")

            # Create a group
            group = Group(
                id=uuid.uuid4().hex,
                collection_id=DEFAULT_COLLECTION_ID,
                name="My Test Group",
                description="Integration test group",
                color="#336699",
                icon="layers",
                position=0,
            )
            session.add(group)
            session.flush()

            # Link artifact to group via GroupArtifact join row
            ga = GroupArtifact(
                group_id=group.id,
                artifact_uuid=art.uuid,
                position=0,
            )
            session.add(ga)
            session.commit()

            group_id = group.id

        # --- Step 2: Write collection.toml and sync groups via ManifestSyncService ---
        collection_dir = tmp_path / "collections" / "default"
        _make_collection_toml(collection_dir)

        with SessionLocal() as session:
            # Patch ConfigManager so the service resolves to our temp dir.
            from unittest.mock import patch

            with patch(
                "skillmeat.config.ConfigManager"
            ) as MockConfig:
                MockConfig.return_value.get_collection_path.return_value = collection_dir
                svc.sync_groups(session, DEFAULT_COLLECTION_ID)

        # --- Step 3: Verify TOML was updated ---
        col = manifest_manager.read(collection_dir)
        assert len(col.groups) == 1
        assert col.groups[0].name == "My Test Group"
        assert "skill:alpha" in col.groups[0].members

        # --- Step 4: Simulate DB reset (drop and recreate tables) ---
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        # --- Step 5: Re-seed minimal data (collection row + artifact) ---
        with SessionLocal() as session:
            _seed_default_collection(session)
            _add_artifact(session, "skill:alpha", "alpha", "skill")

        # --- Step 6: Run recovery from TOML ---
        with SessionLocal() as session:
            stats = recover_collection_metadata(
                session=session,
                collection_id=DEFAULT_COLLECTION_ID,
                collection_path=collection_dir,
            )

        assert stats["groups_recovered"] == 1
        assert stats["skipped_reason"] is None

        # --- Step 7: Verify group is back in DB ---
        with SessionLocal() as session:
            groups = (
                session.query(Group)
                .filter_by(collection_id=DEFAULT_COLLECTION_ID)
                .all()
            )
        assert len(groups) == 1
        assert groups[0].name == "My Test Group"

    def test_empty_groups_write_through_is_noop(self, svc, tmp_path, manifest_manager):
        """When there are no groups in DB, sync should not add a groups section to TOML."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)

        with SessionLocal() as session:
            _seed_default_collection(session)

        collection_dir = tmp_path / "collections" / "default"
        _make_collection_toml(collection_dir)

        with SessionLocal() as session:
            from unittest.mock import patch

            with patch(
                "skillmeat.config.ConfigManager"
            ) as MockConfig:
                MockConfig.return_value.get_collection_path.return_value = collection_dir
                svc.sync_groups(session, DEFAULT_COLLECTION_ID)

        col = manifest_manager.read(collection_dir)
        assert col.groups == []

        raw = (collection_dir / "collection.toml").read_text(encoding="utf-8")
        assert "groups" not in raw


class TestTagWriteThroughRoundTrip:
    """Integration: create tag in DB → sync to TOML → reset DB → recover."""

    def test_tag_write_through_and_recovery(self, svc, tmp_path, manifest_manager):
        """Full round-trip: DB tag → TOML → recovered back into fresh DB."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)

        # --- Step 1: Seed DB with tags ---
        with SessionLocal() as session:
            _seed_default_collection(session)
            session.add(Tag(name="Featured", slug="featured", color="#FF5733"))
            session.add(Tag(name="Beta", slug="beta", color="#3399FF"))
            session.commit()

        # --- Step 2: Sync tag definitions to TOML ---
        collection_dir = tmp_path / "collections" / "default"
        _make_collection_toml(collection_dir)

        with SessionLocal() as session:
            from unittest.mock import patch

            with patch(
                "skillmeat.config.ConfigManager"
            ) as MockConfig:
                MockConfig.return_value.get_collection_path.return_value = collection_dir
                svc.sync_tag_definitions(session, DEFAULT_COLLECTION_ID)

        # --- Step 3: Verify TOML was updated ---
        col = manifest_manager.read(collection_dir)
        assert len(col.tag_definitions) == 2
        slugs = {td.slug for td in col.tag_definitions}
        assert "featured" in slugs
        assert "beta" in slugs

        # --- Step 4: Simulate DB reset ---
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        with SessionLocal() as session:
            _seed_default_collection(session)

        # --- Step 5: Run recovery from TOML ---
        with SessionLocal() as session:
            stats = recover_collection_metadata(
                session=session,
                collection_id=DEFAULT_COLLECTION_ID,
                collection_path=collection_dir,
            )

        assert stats["tags_recovered"] == 2
        assert stats["skipped_reason"] is None

        # --- Step 6: Verify tags are back in DB ---
        with SessionLocal() as session:
            tags = session.query(Tag).order_by(Tag.name).all()
        assert len(tags) == 2
        assert tags[0].slug == "beta"
        assert tags[1].slug == "featured"
        assert tags[1].color == "#FF5733"

    def test_empty_tags_write_through_is_noop(self, svc, tmp_path, manifest_manager):
        """When there are no tags in DB, sync should not add tag_definitions section."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)

        with SessionLocal() as session:
            _seed_default_collection(session)

        collection_dir = tmp_path / "collections" / "default"
        _make_collection_toml(collection_dir)

        with SessionLocal() as session:
            from unittest.mock import patch

            with patch(
                "skillmeat.config.ConfigManager"
            ) as MockConfig:
                MockConfig.return_value.get_collection_path.return_value = collection_dir
                svc.sync_tag_definitions(session, DEFAULT_COLLECTION_ID)

        col = manifest_manager.read(collection_dir)
        assert col.tag_definitions == []

        raw = (collection_dir / "collection.toml").read_text(encoding="utf-8")
        assert "tag_definitions" not in raw


class TestCombinedWriteThroughRoundTrip:
    """Integration: groups + tags synced and recovered in a single pass."""

    def test_combined_write_through_and_recovery(self, svc, tmp_path, manifest_manager):
        """Groups and tags written together, both recovered after DB reset."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)

        collection_dir = tmp_path / "collections" / "default"
        _make_collection_toml(collection_dir)

        # --- Step 1: Seed DB ---
        with SessionLocal() as session:
            _seed_default_collection(session)
            art = _add_artifact(session, "skill:widget", "widget", "skill")

            session.add(Tag(name="Alpha Tag", slug="alpha-tag", color="#AABBCC"))

            group = Group(
                id=uuid.uuid4().hex,
                collection_id=DEFAULT_COLLECTION_ID,
                name="Combined Group",
                description="combined test",
                color="blue",
                icon="box",
                position=0,
            )
            session.add(group)
            session.flush()
            session.add(
                GroupArtifact(
                    group_id=group.id,
                    artifact_uuid=art.uuid,
                    position=0,
                )
            )
            session.commit()

        # --- Step 2: Sync both groups and tags ---
        with SessionLocal() as session:
            from unittest.mock import patch

            with patch(
                "skillmeat.config.ConfigManager"
            ) as MockConfig:
                MockConfig.return_value.get_collection_path.return_value = collection_dir
                svc.sync_groups(session, DEFAULT_COLLECTION_ID)
                svc.sync_tag_definitions(session, DEFAULT_COLLECTION_ID)

        # --- Step 3: Verify TOML has both ---
        col = manifest_manager.read(collection_dir)
        assert len(col.groups) == 1
        assert len(col.tag_definitions) == 1
        assert col.groups[0].name == "Combined Group"
        assert col.tag_definitions[0].slug == "alpha-tag"

        # --- Step 4: Simulate DB reset ---
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        with SessionLocal() as session:
            _seed_default_collection(session)
            _add_artifact(session, "skill:widget", "widget", "skill")

        # --- Step 5: Run recovery ---
        with SessionLocal() as session:
            stats = recover_collection_metadata(
                session=session,
                collection_id=DEFAULT_COLLECTION_ID,
                collection_path=collection_dir,
            )

        assert stats["groups_recovered"] == 1
        assert stats["tags_recovered"] == 1

        # --- Step 6: Verify both are restored ---
        with SessionLocal() as session:
            groups = session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).all()
            tags = session.query(Tag).all()

        assert len(groups) == 1
        assert groups[0].name == "Combined Group"
        assert len(tags) == 1
        assert tags[0].slug == "alpha-tag"
