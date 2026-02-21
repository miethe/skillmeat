"""Unit tests for recover_collection_metadata (MP-3.1, MP-3.2, MP-3.3).

Tests cover:
- MP-3.1: Tag definitions recovered from TOML when DB has no colored tags
- MP-3.2: Groups recovered from TOML when DB has no groups for the collection
- MP-3.3: Partial recovery when some member names cannot be resolved
- Conflict-resolution guards (DB-authoritative when data already present)
- Missing collection.toml is handled gracefully
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.api.services.artifact_cache_service import recover_collection_metadata
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    DEFAULT_COLLECTION_ID,
    Group,
    GroupArtifact,
    Project,
    Tag,
    create_db_engine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SENTINEL_PROJECT_ID = "collection_artifacts_global"


def _make_engine_and_session(tmp_path: Path):
    """Create an in-memory SQLite DB and return (engine, SessionLocal)."""
    db_path = tmp_path / "cache.db"
    engine = create_db_engine(str(db_path))
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine, SessionLocal


def _seed_default_collection(session) -> Collection:
    """Insert a minimal default collection row and return it."""
    coll = Collection(id=DEFAULT_COLLECTION_ID, name="default")
    sentinel = Project(
        id=SENTINEL_PROJECT_ID,
        name="Collection Artifacts",
        path="~/.skillmeat/collections",
        status="active",
    )
    session.add_all([coll, sentinel])
    session.commit()
    return coll


def _add_artifact(session, name: str, artifact_type: str = "skill") -> Artifact:
    """Insert an Artifact row and return it."""
    artifact_id = f"{artifact_type}:{name}"
    row = Artifact(
        id=artifact_id,
        uuid=uuid.uuid4().hex,
        project_id=SENTINEL_PROJECT_ID,
        name=name,
        type=artifact_type,
    )
    session.add(row)
    session.commit()
    return row


def _write_collection_toml(collection_dir: Path, content: str) -> None:
    """Write collection.toml content to the given directory."""
    collection_dir.mkdir(parents=True, exist_ok=True)
    (collection_dir / "collection.toml").write_text(content, encoding="utf-8")


# Minimal valid collection.toml with no tags or groups
_BARE_TOML = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"
"""

# TOML with two tag definitions
_TOML_WITH_TAGS = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[tag_definitions]]
name = "Featured"
slug = "featured"
color = "#FF5733"
description = "Highlighted artifact"

[[tag_definitions]]
name = "Beta"
slug = "beta"
color = "#3399FF"
description = "Beta quality"
"""

# TOML with one group and two members
_TOML_WITH_GROUPS = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[groups]]
name = "My Group"
description = "Test group"
color = "#336699"
icon = "layers"
position = 0
members = ["skill:alpha", "skill:beta"]
"""

# TOML with group where one member is missing from the DB
_TOML_WITH_PARTIAL_MEMBERS = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[groups]]
name = "Partial Group"
description = ""
color = "slate"
icon = "layers"
position = 0
members = ["skill:present", "skill:missing"]
"""


# ---------------------------------------------------------------------------
# MP-3.1 — Tag definition recovery
# ---------------------------------------------------------------------------


class TestTagDefinitionRecovery:
    """MP-3.1: Recover tag definitions from collection.toml."""

    def test_tags_recovered_when_db_empty(self, tmp_path):
        """When DB has no colored tags, tag definitions should be imported from TOML."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_TAGS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["tags_recovered"] == 2
        assert stats["skipped_reason"] is None

        tags = session.query(Tag).order_by(Tag.name).all()
        assert len(tags) == 2
        slugs = {t.slug for t in tags}
        assert slugs == {"featured", "beta"}
        colors = {t.slug: t.color for t in tags}
        assert colors["featured"] == "#FF5733"
        assert colors["beta"] == "#3399FF"

    def test_tags_skipped_when_colored_tags_exist(self, tmp_path):
        """When DB already has colored tags, the tag section should be skipped."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Pre-populate a colored tag so DB is treated as authoritative
        existing_tag = Tag(
            name="Existing",
            slug="existing",
            color="#AABBCC",
        )
        session.add(existing_tag)
        session.commit()

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_TAGS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["tags_recovered"] == 0
        # Only the pre-existing tag should remain; TOML tags NOT imported
        all_tags = session.query(Tag).all()
        assert len(all_tags) == 1
        assert all_tags[0].slug == "existing"

    def test_colorless_tag_in_db_does_not_block_recovery(self, tmp_path):
        """Tags with color=NULL in DB do not count as 'colored'; recovery should run."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Tag with no color (auto-created by artifact tag sync)
        session.add(Tag(name="Auto", slug="auto", color=None))
        session.commit()

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_TAGS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        # 2 new tags created from TOML (the colorless "auto" tag stays untouched)
        assert stats["tags_recovered"] == 2
        all_tags = session.query(Tag).all()
        assert len(all_tags) == 3  # auto + featured + beta

    def test_tag_color_updated_on_existing_colorless_slug(self, tmp_path):
        """If slug already exists in DB with NULL color, TOML color should be applied."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Insert tag without color (DB colorless — recovery should run)
        session.add(Tag(name="Featured", slug="featured", color=None))
        session.commit()

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_TAGS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        # "featured" color updated + "beta" created = 2 updates
        assert stats["tags_recovered"] == 2
        featured = session.query(Tag).filter_by(slug="featured").first()
        assert featured is not None
        assert featured.color == "#FF5733"

    def test_no_tags_in_toml_is_noop(self, tmp_path):
        """If collection.toml has no tag_definitions, recovery stats should be zero."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _BARE_TOML)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["tags_recovered"] == 0
        assert session.query(Tag).count() == 0

    def test_invalid_color_stored_as_null(self, tmp_path):
        """Tags with non-hex color strings should be stored with color=NULL."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        toml_with_bad_color = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[tag_definitions]]
name = "BadColor"
slug = "bad-color"
color = "not-a-hex"
description = ""
"""
        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, toml_with_bad_color)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["tags_recovered"] == 1
        tag = session.query(Tag).filter_by(slug="bad-color").first()
        assert tag is not None
        assert tag.color is None


# ---------------------------------------------------------------------------
# MP-3.2 — Group recovery
# ---------------------------------------------------------------------------


class TestGroupRecovery:
    """MP-3.2: Recover groups from collection.toml."""

    def test_groups_recovered_when_db_empty(self, tmp_path):
        """When DB has no groups for the collection, they should be imported from TOML."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Add both member artifacts to the DB
        _add_artifact(session, "alpha")
        _add_artifact(session, "beta")

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_GROUPS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["groups_recovered"] == 1
        assert stats["members_recovered"] == 2
        assert stats["members_skipped"] == 0

        groups = session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).all()
        assert len(groups) == 1
        grp = groups[0]
        assert grp.name == "My Group"
        assert grp.position == 0

        # Verify GroupArtifact memberships
        gas = session.query(GroupArtifact).filter_by(group_id=grp.id).all()
        assert len(gas) == 2

    def test_groups_skipped_when_groups_exist(self, tmp_path):
        """When DB already has groups for the collection, TOML import should be skipped."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Pre-populate a group in DB
        existing_group = Group(
            id=uuid.uuid4().hex,
            collection_id=DEFAULT_COLLECTION_ID,
            name="Pre-existing Group",
            position=0,
        )
        session.add(existing_group)
        session.commit()

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_GROUPS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["groups_recovered"] == 0
        # Only the pre-existing group should exist
        assert session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).count() == 1

    def test_group_properties_set_correctly(self, tmp_path):
        """Group color, icon, description, and position should be set from TOML."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        toml_content = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[groups]]
name = "Styled Group"
description = "A styled group"
color = "slate"
icon = "star"
position = 3
members = []
"""
        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, toml_content)

        recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        grp = session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).first()
        assert grp is not None
        assert grp.name == "Styled Group"
        assert grp.description == "A styled group"
        assert grp.color == "slate"
        assert grp.icon == "star"
        assert grp.position == 3

    def test_no_groups_in_toml_is_noop(self, tmp_path):
        """If collection.toml has no groups, no Group rows should be created."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _BARE_TOML)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["groups_recovered"] == 0
        assert session.query(Group).count() == 0

    def test_member_positions_are_sequential(self, tmp_path):
        """Members should be assigned positions 0, 1, 2, ... in TOML order."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        _add_artifact(session, "first")
        _add_artifact(session, "second")
        _add_artifact(session, "third")

        toml_content = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[groups]]
name = "Ordered"
description = ""
color = "slate"
icon = "layers"
position = 0
members = ["skill:first", "skill:second", "skill:third"]
"""
        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, toml_content)

        recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        grp = session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).first()
        gas = (
            session.query(GroupArtifact)
            .filter_by(group_id=grp.id)
            .order_by(GroupArtifact.position)
            .all()
        )
        assert [ga.position for ga in gas] == [0, 1, 2]


# ---------------------------------------------------------------------------
# MP-3.3 — Partial recovery / member resolution failures
# ---------------------------------------------------------------------------


class TestPartialMemberRecovery:
    """MP-3.3: Member resolution failures should be skipped with a warning."""

    def test_partial_members_resolved(self, tmp_path):
        """If only some members exist in DB, the rest should be skipped (not fail)."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Only add one of the two members referenced in _TOML_WITH_PARTIAL_MEMBERS
        _add_artifact(session, "present")
        # "skill:missing" is NOT added

        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_PARTIAL_MEMBERS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["groups_recovered"] == 1
        assert stats["members_recovered"] == 1
        assert stats["members_skipped"] == 1

        grp = session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).first()
        assert grp is not None
        gas = session.query(GroupArtifact).filter_by(group_id=grp.id).all()
        assert len(gas) == 1  # only "present" was added

    def test_all_members_missing_creates_empty_group(self, tmp_path):
        """If ALL members fail resolution, the group should still be created (empty)."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # No artifacts added; all members will fail
        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, _TOML_WITH_GROUPS)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["groups_recovered"] == 1
        assert stats["members_recovered"] == 0
        assert stats["members_skipped"] == 2

        grp = session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).first()
        assert grp is not None
        assert session.query(GroupArtifact).filter_by(group_id=grp.id).count() == 0

    def test_multiple_groups_partial_failures_independent(self, tmp_path):
        """Member resolution failure in one group should not block another group."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        # Only "good-artifact" exists
        _add_artifact(session, "good-artifact")

        toml_content = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[groups]]
name = "Group A"
description = ""
color = "slate"
icon = "layers"
position = 0
members = ["skill:missing-artifact"]

[[groups]]
name = "Group B"
description = ""
color = "slate"
icon = "layers"
position = 1
members = ["skill:good-artifact"]
"""
        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, toml_content)

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["groups_recovered"] == 2
        assert stats["members_recovered"] == 1
        assert stats["members_skipped"] == 1

        groups = (
            session.query(Group)
            .filter_by(collection_id=DEFAULT_COLLECTION_ID)
            .order_by(Group.position)
            .all()
        )
        assert len(groups) == 2
        assert groups[0].name == "Group A"
        assert groups[1].name == "Group B"

        # Group A should have 0 members; Group B should have 1
        assert session.query(GroupArtifact).filter_by(group_id=groups[0].id).count() == 0
        assert session.query(GroupArtifact).filter_by(group_id=groups[1].id).count() == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for recover_collection_metadata."""

    def test_missing_collection_toml_returns_skipped_reason(self, tmp_path):
        """If collection.toml doesn't exist, return skipped_reason='no_collection_toml'."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        non_existent_path = tmp_path / "does" / "not" / "exist"

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=non_existent_path,
        )

        assert stats["skipped_reason"] == "no_collection_toml"
        assert stats["tags_recovered"] == 0
        assert stats["groups_recovered"] == 0

    def test_corrupted_toml_returns_skipped_reason(self, tmp_path):
        """Corrupted collection.toml should return skipped_reason='toml_read_error'."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)

        collection_dir = tmp_path / "collections" / "default"
        collection_dir.mkdir(parents=True)
        (collection_dir / "collection.toml").write_bytes(b"\xff\xfe invalid toml bytes!!!")

        stats = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )

        assert stats["skipped_reason"] == "toml_read_error"
        assert stats["tags_recovered"] == 0
        assert stats["groups_recovered"] == 0

    def test_recovery_idempotent_when_called_twice(self, tmp_path):
        """Calling recovery twice should not create duplicate rows."""
        engine, SessionLocal = _make_engine_and_session(tmp_path)
        session = SessionLocal()
        _seed_default_collection(session)
        _add_artifact(session, "alpha")

        toml_content = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"

[[tag_definitions]]
name = "Featured"
slug = "featured"
color = "#FF5733"
description = ""

[[groups]]
name = "Solo Group"
description = ""
color = "slate"
icon = "layers"
position = 0
members = ["skill:alpha"]
"""
        collection_dir = tmp_path / "collections" / "default"
        _write_collection_toml(collection_dir, toml_content)

        stats1 = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )
        assert stats1["tags_recovered"] == 1
        assert stats1["groups_recovered"] == 1

        # Second call: DB is now authoritative (colored tag + existing group)
        stats2 = recover_collection_metadata(
            session=session,
            collection_id=DEFAULT_COLLECTION_ID,
            collection_path=collection_dir,
        )
        assert stats2["tags_recovered"] == 0
        assert stats2["groups_recovered"] == 0

        # Still only 1 tag and 1 group in DB
        assert session.query(Tag).count() == 1
        assert session.query(Group).filter_by(collection_id=DEFAULT_COLLECTION_ID).count() == 1
