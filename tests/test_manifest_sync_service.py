"""Unit tests for ManifestSyncService (MP-4.2).

Tests cover:
- sync_groups() with mock DB session — queries groups, builds GroupDefinitions,
  writes to manifest
- sync_tag_definitions() with mock DB session — queries tags, builds
  TagDefinitions, writes to manifest
- Error handling — sync failure is logged but does not raise
- Empty groups/tags (no-op case / clean write)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from skillmeat.core.collection import Collection, GroupDefinition, TagDefinition
from skillmeat.core.services.manifest_sync_service import ManifestSyncService
from skillmeat.storage.manifest import ManifestManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, 0, 0, 0)
_COLLECTION_ID = "test-collection-id"
_COLLECTION_NAME = "default"


def _make_collection_toml(tmp_path: Path, name: str = "default") -> Path:
    """Create a minimal collection.toml in *tmp_path* and return the dir."""
    coll_dir = tmp_path / name
    coll_dir.mkdir(parents=True, exist_ok=True)
    toml_content = (
        f"[collection]\n"
        f'name = "{name}"\n'
        f'version = "1.0.0"\n'
        f'created = "2026-01-01T00:00:00"\n'
        f'updated = "2026-01-01T00:00:00"\n'
    )
    (coll_dir / "collection.toml").write_text(toml_content, encoding="utf-8")
    return coll_dir


def _make_db_group(
    name: str,
    collection_id: str = _COLLECTION_ID,
    description: str = "",
    color: str = "slate",
    icon: str = "layers",
    position: int = 0,
) -> MagicMock:
    """Return a MagicMock that looks like a DB Group row."""
    g = MagicMock()
    g.id = uuid.uuid4().hex
    g.name = name
    g.collection_id = collection_id
    g.description = description
    g.color = color
    g.icon = icon
    g.position = position
    return g


def _make_db_tag(
    name: str,
    slug: str,
    color: str | None = None,
) -> MagicMock:
    """Return a MagicMock that looks like a DB Tag row."""
    t = MagicMock()
    t.id = uuid.uuid4().hex
    t.name = name
    t.slug = slug
    t.color = color
    return t


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def svc():
    return ManifestSyncService()


@pytest.fixture
def manifest_manager():
    return ManifestManager()


# ---------------------------------------------------------------------------
# sync_groups() tests
# ---------------------------------------------------------------------------


class TestSyncGroups:
    """Tests for ManifestSyncService.sync_groups()."""

    def _build_session(
        self,
        collection_path: Path,
        collection_name: str,
        groups,
        group_member_map=None,
    ) -> MagicMock:
        """Build a mock SQLAlchemy session suitable for sync_groups().

        group_member_map: dict[group_id -> list[str]] mapping group IDs to
        resolved artifact.id strings (type:name).  Defaults to empty per group.
        """
        if group_member_map is None:
            group_member_map = {}

        session = MagicMock()

        # Mock Collection lookup (used by _resolve_collection_path).
        db_collection = MagicMock()
        db_collection.name = collection_name

        def _query_side_effect(model):
            q = MagicMock()

            if model.__name__ == "Collection":
                q.filter_by.return_value.first.return_value = db_collection
                return q

            if model.__name__ == "Group":
                q.filter_by.return_value.order_by.return_value.all.return_value = groups
                return q

            if model.__name__ == "Artifact":
                # Return a query that supports .join().filter().order_by().all()
                def _artifact_query():
                    aq = MagicMock()

                    def _join(*args, **kwargs):
                        jq = MagicMock()

                        def _filter(cond):
                            fq = MagicMock()

                            def _order_by(*a):
                                obq = MagicMock()

                                # Determine which group's members to return
                                # by inspecting the filter expression repr.
                                # We use a simpler approach: capture via closure
                                # by patching __eq__ on group.id attributes.
                                # Instead, just cycle through groups.
                                members = []
                                for g in groups:
                                    if g.id in group_member_map:
                                        members = [
                                            (m,)
                                            for m in group_member_map[g.id]
                                        ]
                                obq.all.return_value = members
                                return obq

                            fq.order_by = _order_by
                            return fq

                        jq.filter = _filter
                        return jq

                    aq.join = _join
                    return aq

                return _artifact_query()

            return MagicMock()

        session.query.side_effect = _query_side_effect
        return session

    def _build_simple_session(
        self,
        collection_path: Path,
        collection_name: str,
        groups,
        members_per_group: list[list[str]],
    ) -> MagicMock:
        """Simpler session builder using sequential member resolution.

        The sync service calls session.query(Artifact).join(...).filter(...).
        order_by(...).all() once per group.  We set up the mock so each
        successive call returns the next member list.
        """
        session = MagicMock()

        db_collection = MagicMock()
        db_collection.name = collection_name

        # Track how many times the artifact query chain is called.
        call_counter = {"n": 0}

        def _query(model):
            q = MagicMock()

            # Inspect by checking if model has __tablename__ or __name__.
            model_name = getattr(model, "__name__", None) or getattr(
                model, "__tablename__", ""
            )

            if model_name == "Collection":
                q.filter_by.return_value.first.return_value = db_collection
                return q

            if model_name == "Group":
                q.filter_by.return_value.order_by.return_value.all.return_value = groups
                return q

            # Artifact — build a chain that returns from members_per_group[n]
            idx = call_counter["n"]
            call_counter["n"] += 1
            member_rows = [
                (m,) for m in (members_per_group[idx] if idx < len(members_per_group) else [])
            ]

            # Build a deep chain: .join().filter().order_by().all()
            terminal = MagicMock()
            terminal.all.return_value = member_rows

            order_by_mock = MagicMock()
            order_by_mock.all = terminal.all
            order_by_mock.return_value = terminal

            filter_mock = MagicMock()
            filter_mock.order_by.return_value = order_by_mock

            join_mock = MagicMock()
            join_mock.filter.return_value = filter_mock

            q.join.return_value = join_mock
            return q

        session.query.side_effect = _query
        return session

    def test_sync_groups_writes_group_definitions(self, svc, tmp_path, manifest_manager):
        """sync_groups() must write GroupDefinitions extracted from DB."""
        coll_dir = _make_collection_toml(tmp_path)
        groups = [
            _make_db_group("Alpha", position=0),
            _make_db_group("Beta", color="#336699", icon="star", position=1),
        ]
        members_per_group = [["skill:foo"], ["command:bar", "agent:baz"]]

        session = self._build_simple_session(
            coll_dir, _COLLECTION_NAME, groups, members_per_group
        )

        with patch("skillmeat.config.ConfigManager") as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_groups(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert len(loaded.groups) == 2
        assert loaded.groups[0].name == "Alpha"
        assert loaded.groups[0].members == ["skill:foo"]
        assert loaded.groups[1].name == "Beta"
        assert loaded.groups[1].members == ["command:bar", "agent:baz"]
        assert loaded.groups[1].color == "#336699"

    def test_sync_groups_empty_groups_writes_clean_toml(self, svc, tmp_path, manifest_manager):
        """sync_groups() with zero groups must write an empty groups list (no section)."""
        coll_dir = _make_collection_toml(tmp_path)
        session = self._build_simple_session(coll_dir, _COLLECTION_NAME, [], [])

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_groups(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert loaded.groups == []

        raw = (coll_dir / "collection.toml").read_text(encoding="utf-8")
        assert "groups" not in raw

    def test_sync_groups_missing_collection_toml_is_noop(self, svc, tmp_path):
        """sync_groups() must not raise when collection.toml is absent."""
        coll_dir = tmp_path / "no-toml"
        coll_dir.mkdir()  # directory exists, but no collection.toml

        session = MagicMock()
        db_coll = MagicMock()
        db_coll.name = _COLLECTION_NAME
        session.query.return_value.filter_by.return_value.first.return_value = db_coll

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            # Must not raise.
            svc.sync_groups(session, _COLLECTION_ID)

    def test_sync_groups_missing_collection_row_is_noop(self, svc, tmp_path):
        """sync_groups() must not raise when the collection row is missing in DB."""
        session = MagicMock()
        session.query.return_value.filter_by.return_value.first.return_value = None

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = tmp_path
            # Must not raise.
            svc.sync_groups(session, "nonexistent-id")

    def test_sync_groups_error_is_logged_not_raised(self, svc, tmp_path, caplog):
        """sync_groups() must log errors but not propagate them to the caller."""
        coll_dir = _make_collection_toml(tmp_path)

        # Simulate a crash inside _sync_groups_inner.
        with (
            patch.object(svc, "_sync_groups_inner", side_effect=RuntimeError("boom")),
            caplog.at_level(logging.ERROR, logger="skillmeat.core.services.manifest_sync_service"),
        ):
            svc.sync_groups(MagicMock(), _COLLECTION_ID)  # must not raise

        assert any("boom" in r.message or "boom" in str(r.exc_info) for r in caplog.records)

    def test_sync_groups_preserves_position_ordering(self, svc, tmp_path, manifest_manager):
        """GroupDefinition.position must be preserved after sync."""
        coll_dir = _make_collection_toml(tmp_path)
        groups = [
            _make_db_group("Z-Group", position=5),
        ]
        session = self._build_simple_session(coll_dir, _COLLECTION_NAME, groups, [[]])

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_groups(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert loaded.groups[0].position == 5


# ---------------------------------------------------------------------------
# sync_tag_definitions() tests
# ---------------------------------------------------------------------------


class TestSyncTagDefinitions:
    """Tests for ManifestSyncService.sync_tag_definitions()."""

    def _build_session(self, collection_name: str, tags) -> MagicMock:
        """Build a mock session for sync_tag_definitions()."""
        session = MagicMock()

        db_collection = MagicMock()
        db_collection.name = collection_name

        def _query(model):
            q = MagicMock()
            model_name = getattr(model, "__name__", None) or ""

            if model_name == "Collection":
                q.filter_by.return_value.first.return_value = db_collection
                return q

            if model_name == "Tag":
                q.order_by.return_value.all.return_value = tags
                return q

            return MagicMock()

        session.query.side_effect = _query
        return session

    def test_sync_tag_definitions_writes_definitions(self, svc, tmp_path, manifest_manager):
        """sync_tag_definitions() must write TagDefinitions extracted from DB."""
        coll_dir = _make_collection_toml(tmp_path)
        tags = [
            _make_db_tag("Beta", "beta", color="#3399FF"),
            _make_db_tag("Featured", "featured", color="#FF5733"),
        ]
        session = self._build_session(_COLLECTION_NAME, tags)

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_tag_definitions(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert len(loaded.tag_definitions) == 2
        slugs = {td.slug for td in loaded.tag_definitions}
        assert "beta" in slugs
        assert "featured" in slugs

    def test_sync_tag_definitions_null_color_becomes_empty_string(
        self, svc, tmp_path, manifest_manager
    ):
        """Tags with NULL color in DB should emit empty string in TOML."""
        coll_dir = _make_collection_toml(tmp_path)
        tags = [_make_db_tag("No Color", "no-color", color=None)]
        session = self._build_session(_COLLECTION_NAME, tags)

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_tag_definitions(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert loaded.tag_definitions[0].color == ""

    def test_sync_tag_definitions_empty_tags_writes_no_section(
        self, svc, tmp_path, manifest_manager
    ):
        """sync_tag_definitions() with zero tags should not emit tag_definitions key."""
        coll_dir = _make_collection_toml(tmp_path)
        session = self._build_session(_COLLECTION_NAME, [])

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_tag_definitions(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert loaded.tag_definitions == []

        raw = (coll_dir / "collection.toml").read_text(encoding="utf-8")
        assert "tag_definitions" not in raw

    def test_sync_tag_definitions_missing_toml_is_noop(self, svc, tmp_path):
        """sync_tag_definitions() must not raise when collection.toml is absent."""
        coll_dir = tmp_path / "no-toml"
        coll_dir.mkdir()
        session = self._build_session(_COLLECTION_NAME, [])

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_tag_definitions(session, _COLLECTION_ID)

    def test_sync_tag_definitions_error_is_logged_not_raised(self, svc, tmp_path, caplog):
        """sync_tag_definitions() must log errors but not propagate them."""
        with (
            patch.object(
                svc, "_sync_tag_definitions_inner", side_effect=ValueError("oops")
            ),
            caplog.at_level(
                logging.ERROR, logger="skillmeat.core.services.manifest_sync_service"
            ),
        ):
            svc.sync_tag_definitions(MagicMock(), _COLLECTION_ID)  # must not raise

        assert any(
            "oops" in r.message or "oops" in str(r.exc_info) for r in caplog.records
        )

    def test_sync_tag_definitions_description_defaults_to_empty(
        self, svc, tmp_path, manifest_manager
    ):
        """Tag model has no description column; TagDefinition.description must default to ''."""
        coll_dir = _make_collection_toml(tmp_path)
        tags = [_make_db_tag("HasDesc?", "has-desc", color="#123456")]
        session = self._build_session(_COLLECTION_NAME, tags)

        with patch(
            "skillmeat.config.ConfigManager"
        ) as MockConfig:
            MockConfig.return_value.get_collection_path.return_value = coll_dir
            svc.sync_tag_definitions(session, _COLLECTION_ID)

        loaded = manifest_manager.read(coll_dir)
        assert loaded.tag_definitions[0].description == ""
