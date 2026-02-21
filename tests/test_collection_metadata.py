"""Unit tests for TagDefinition, GroupDefinition, and Collection metadata (MP-4.1).

Tests cover:
- TagDefinition.to_dict() / from_dict() round-trip
- GroupDefinition.to_dict() / from_dict() round-trip
- Collection.to_dict() / from_dict() with tag_definitions and groups
- Backward compatibility: old TOML format without tag_definitions/groups parses fine
- Empty tag_definitions/groups are NOT serialized (clean TOML output)
- Integration: write/read round-trip via ManifestManager (MP-4.4)
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from skillmeat.core.collection import Collection, GroupDefinition, TagDefinition
from skillmeat.storage.manifest import ManifestManager


# ---------------------------------------------------------------------------
# Helpers / shared data
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, 0, 0, 0)

_BARE_TOML = """\
[collection]
name = "default"
version = "1.0.0"
created = "2026-01-01T00:00:00"
updated = "2026-01-01T00:00:00"
"""

_OLD_FORMAT_TOML = """\
[collection]
name = "legacy"
version = "1.0.0"
created = "2025-06-01T10:00:00"
updated = "2025-06-01T10:00:00"

[[artifacts]]
name = "my-skill"
type = "skill"
path = "skills/my-skill/"
origin = "github"
added = "2025-06-01T10:00:00"
"""


def _bare_collection() -> Collection:
    """Return a minimal Collection with no tags or groups."""
    return Collection(
        name="default",
        version="1.0.0",
        artifacts=[],
        created=_NOW,
        updated=_NOW,
    )


# ---------------------------------------------------------------------------
# TagDefinition unit tests
# ---------------------------------------------------------------------------


class TestTagDefinition:
    """Tests for TagDefinition dataclass serialization."""

    def test_to_dict_returns_all_fields(self):
        tag = TagDefinition(
            name="Featured",
            slug="featured",
            color="#FF5733",
            description="Highlighted artifact",
        )
        d = tag.to_dict()
        assert d == {
            "name": "Featured",
            "slug": "featured",
            "color": "#FF5733",
            "description": "Highlighted artifact",
        }

    def test_from_dict_round_trip(self):
        original = TagDefinition(
            name="Beta",
            slug="beta",
            color="#3399FF",
            description="Beta quality",
        )
        restored = TagDefinition.from_dict(original.to_dict())
        assert restored.name == original.name
        assert restored.slug == original.slug
        assert restored.color == original.color
        assert restored.description == original.description

    def test_from_dict_optional_fields_default_to_empty(self):
        """from_dict must tolerate missing optional fields."""
        minimal = {"name": "Cool", "slug": "cool"}
        tag = TagDefinition.from_dict(minimal)
        assert tag.color == ""
        assert tag.description == ""

    def test_to_dict_empty_strings_preserved(self):
        """Empty color/description should still be serialized."""
        tag = TagDefinition(name="Plain", slug="plain", color="", description="")
        d = tag.to_dict()
        assert d["color"] == ""
        assert d["description"] == ""

    def test_multiple_round_trips_stable(self):
        tag = TagDefinition(name="Stable", slug="stable", color="blue", description="x")
        for _ in range(3):
            tag = TagDefinition.from_dict(tag.to_dict())
        assert tag.name == "Stable"
        assert tag.slug == "stable"
        assert tag.color == "blue"


# ---------------------------------------------------------------------------
# GroupDefinition unit tests
# ---------------------------------------------------------------------------


class TestGroupDefinition:
    """Tests for GroupDefinition dataclass serialization."""

    def test_to_dict_returns_all_fields(self):
        group = GroupDefinition(
            name="My Group",
            description="Test group",
            color="#336699",
            icon="layers",
            position=2,
            members=["skill:alpha", "skill:beta"],
        )
        d = group.to_dict()
        assert d == {
            "name": "My Group",
            "description": "Test group",
            "color": "#336699",
            "icon": "layers",
            "position": 2,
            "members": ["skill:alpha", "skill:beta"],
        }

    def test_from_dict_round_trip(self):
        original = GroupDefinition(
            name="Round-Trip Group",
            description="desc",
            color="red",
            icon="box",
            position=1,
            members=["command:foo", "agent:bar"],
        )
        restored = GroupDefinition.from_dict(original.to_dict())
        assert restored.name == original.name
        assert restored.description == original.description
        assert restored.color == original.color
        assert restored.icon == original.icon
        assert restored.position == original.position
        assert restored.members == original.members

    def test_from_dict_optional_fields_default(self):
        """from_dict must tolerate missing optional fields."""
        minimal = {"name": "Minimal"}
        group = GroupDefinition.from_dict(minimal)
        assert group.description == ""
        assert group.color == ""
        assert group.icon == ""
        assert group.position == 0
        assert group.members == []

    def test_members_list_is_copy(self):
        """Mutations to the original list must not affect the dataclass."""
        members = ["skill:a", "skill:b"]
        group = GroupDefinition(name="G", members=members)
        d = group.to_dict()
        members.append("skill:c")
        assert "skill:c" not in d["members"]

    def test_from_dict_members_is_copy(self):
        data = {"name": "G", "members": ["skill:x"]}
        group = GroupDefinition.from_dict(data)
        data["members"].append("skill:y")
        assert "skill:y" not in group.members

    def test_empty_members_serialized(self):
        group = GroupDefinition(name="Empty", members=[])
        d = group.to_dict()
        assert d["members"] == []


# ---------------------------------------------------------------------------
# Collection with tag_definitions and groups
# ---------------------------------------------------------------------------


class TestCollectionMetadataSerialization:
    """Tests for Collection.to_dict() / from_dict() with metadata fields."""

    def test_to_dict_omits_tag_definitions_when_empty(self):
        col = _bare_collection()
        d = col.to_dict()
        assert "tag_definitions" not in d

    def test_to_dict_omits_groups_when_empty(self):
        col = _bare_collection()
        d = col.to_dict()
        assert "groups" not in d

    def test_to_dict_includes_tag_definitions_when_present(self):
        col = _bare_collection()
        col.tag_definitions = [
            TagDefinition(name="Featured", slug="featured", color="#FF0000"),
        ]
        d = col.to_dict()
        assert "tag_definitions" in d
        assert len(d["tag_definitions"]) == 1
        assert d["tag_definitions"][0]["slug"] == "featured"

    def test_to_dict_includes_groups_when_present(self):
        col = _bare_collection()
        col.groups = [
            GroupDefinition(name="My Group", members=["skill:foo"]),
        ]
        d = col.to_dict()
        assert "groups" in d
        assert d["groups"][0]["name"] == "My Group"

    def test_from_dict_defaults_to_empty_lists_when_absent(self):
        """Old manifests without tag_definitions/groups must parse cleanly."""
        data = {
            "collection": {
                "name": "legacy",
                "version": "1.0.0",
                "created": "2026-01-01T00:00:00",
                "updated": "2026-01-01T00:00:00",
            },
        }
        col = Collection.from_dict(data)
        assert col.tag_definitions == []
        assert col.groups == []

    def test_round_trip_tag_definitions(self):
        col = _bare_collection()
        col.tag_definitions = [
            TagDefinition(name="A", slug="a", color="red", description="desc-a"),
            TagDefinition(name="B", slug="b", color="blue"),
        ]
        restored = Collection.from_dict(col.to_dict())
        assert len(restored.tag_definitions) == 2
        assert restored.tag_definitions[0].slug == "a"
        assert restored.tag_definitions[1].color == "blue"

    def test_round_trip_groups(self):
        col = _bare_collection()
        col.groups = [
            GroupDefinition(
                name="G1",
                description="first",
                color="#111",
                icon="star",
                position=0,
                members=["skill:foo"],
            ),
            GroupDefinition(name="G2", position=1, members=[]),
        ]
        restored = Collection.from_dict(col.to_dict())
        assert len(restored.groups) == 2
        assert restored.groups[0].name == "G1"
        assert restored.groups[0].members == ["skill:foo"]
        assert restored.groups[1].name == "G2"
        assert restored.groups[1].members == []

    def test_round_trip_both_tag_definitions_and_groups(self):
        col = _bare_collection()
        col.tag_definitions = [TagDefinition(name="X", slug="x")]
        col.groups = [GroupDefinition(name="GX", members=["skill:x"])]
        d = col.to_dict()
        restored = Collection.from_dict(d)
        assert len(restored.tag_definitions) == 1
        assert len(restored.groups) == 1
        assert restored.tag_definitions[0].name == "X"
        assert restored.groups[0].members == ["skill:x"]


# ---------------------------------------------------------------------------
# MP-4.4: Backward compatibility via ManifestManager (integration)
# ---------------------------------------------------------------------------


@pytest.fixture
def manifest_manager():
    return ManifestManager()


class TestManifestManagerBackwardCompatibility:
    """Integration tests: ManifestManager reads old-format TOML without error."""

    def test_bare_toml_no_tags_no_groups(self, tmp_path, manifest_manager):
        """collection.toml without tag_definitions/groups parses cleanly."""
        coll_dir = tmp_path / "my-collection"
        coll_dir.mkdir()
        (coll_dir / "collection.toml").write_text(_BARE_TOML, encoding="utf-8")

        col = manifest_manager.read(coll_dir)
        assert col.name == "default"
        assert col.tag_definitions == []
        assert col.groups == []

    def test_old_format_with_artifacts_parses_cleanly(self, tmp_path, manifest_manager):
        """Legacy manifest with artifacts but no metadata fields parses cleanly."""
        coll_dir = tmp_path / "legacy-coll"
        coll_dir.mkdir()
        (coll_dir / "collection.toml").write_text(_OLD_FORMAT_TOML, encoding="utf-8")

        col = manifest_manager.read(coll_dir)
        assert col.name == "legacy"
        assert col.tag_definitions == []
        assert col.groups == []
        assert len(col.artifacts) == 1
        assert col.artifacts[0].name == "my-skill"

    def test_write_then_read_preserves_tag_definitions(self, tmp_path, manifest_manager):
        """Write a collection with tags → read back → verify round-trip."""
        coll_dir = tmp_path / "coll-with-tags"
        coll_dir.mkdir()

        col = _bare_collection()
        col.tag_definitions = [
            TagDefinition(name="Featured", slug="featured", color="#FF5733"),
            TagDefinition(name="Beta", slug="beta", color="#3399FF", description="Beta"),
        ]
        manifest_manager.write(coll_dir, col)

        loaded = manifest_manager.read(coll_dir)
        assert len(loaded.tag_definitions) == 2
        assert loaded.tag_definitions[0].name == "Featured"
        assert loaded.tag_definitions[0].slug == "featured"
        assert loaded.tag_definitions[0].color == "#FF5733"
        assert loaded.tag_definitions[1].description == "Beta"

    def test_write_then_read_preserves_groups(self, tmp_path, manifest_manager):
        """Write a collection with groups → read back → verify round-trip."""
        coll_dir = tmp_path / "coll-with-groups"
        coll_dir.mkdir()

        col = _bare_collection()
        col.groups = [
            GroupDefinition(
                name="My Group",
                description="A test group",
                color="#336699",
                icon="layers",
                position=0,
                members=["skill:alpha", "skill:beta"],
            )
        ]
        manifest_manager.write(coll_dir, col)

        loaded = manifest_manager.read(coll_dir)
        assert len(loaded.groups) == 1
        g = loaded.groups[0]
        assert g.name == "My Group"
        assert g.description == "A test group"
        assert g.color == "#336699"
        assert g.icon == "layers"
        assert g.position == 0
        assert g.members == ["skill:alpha", "skill:beta"]

    def test_empty_collections_do_not_emit_sections(self, tmp_path, manifest_manager):
        """Writing a collection with no tags/groups must not emit those TOML keys."""
        coll_dir = tmp_path / "clean-coll"
        coll_dir.mkdir()

        col = _bare_collection()
        manifest_manager.write(coll_dir, col)

        raw = (coll_dir / "collection.toml").read_text(encoding="utf-8")
        assert "tag_definitions" not in raw
        assert "groups" not in raw

    def test_write_then_read_multiple_groups_ordering(self, tmp_path, manifest_manager):
        """Groups must be preserved in insertion order after a round-trip."""
        coll_dir = tmp_path / "ordered-groups"
        coll_dir.mkdir()

        col = _bare_collection()
        col.groups = [
            GroupDefinition(name="First", position=0),
            GroupDefinition(name="Second", position=1),
            GroupDefinition(name="Third", position=2),
        ]
        manifest_manager.write(coll_dir, col)

        loaded = manifest_manager.read(coll_dir)
        names = [g.name for g in loaded.groups]
        assert names == ["First", "Second", "Third"]
