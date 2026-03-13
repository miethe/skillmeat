"""Integration tests for BomGenerator and related classes.

Tests cover:
- BomGenerator end-to-end: generates valid BOM from mixed artifact types
- Determinism: two calls with the same state produce identical output
- Content hashes: 64-character hex strings or empty string
- Error handling: unknown type is skipped without crash
- CompositeAdapter: members resolved via mocked CompositeMembership
- MemoryItemAdapter: metadata extracted from mocked MemoryItem
- DeploymentSetAdapter: members list built from mocked DeploymentSet
- BomSerializer: to_json, to_dict, write_file (atomic write + permissions)
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from skillmeat.core.bom.generator import (
    BomGenerator,
    BomSerializer,
    CompositeAdapter,
    DeploymentSetAdapter,
    MemoryItemAdapter,
    _hash_string,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_artifact(
    name: str,
    artifact_type: str,
    source: Optional[str] = None,
    deployed_version: Optional[str] = None,
    upstream_version: Optional[str] = None,
    content: Optional[str] = None,
    content_hash: Optional[str] = None,
    project_id: Optional[str] = "proj-1",
) -> Any:
    """Return a MagicMock shaped like an ORM Artifact row."""
    art = MagicMock()
    art.id = f"{artifact_type}:{name}"
    art.name = name
    art.type = artifact_type
    art.source = source
    art.deployed_version = deployed_version
    art.upstream_version = upstream_version
    art.content = content
    art.content_hash = content_hash
    art.project_id = project_id
    art.created_at = None
    art.updated_at = None
    art.artifact_metadata = None
    art.uuid = f"uuid-{name}"
    return art


def _make_session(artifacts: List[Any]) -> MagicMock:
    """Return a MagicMock session whose query().all() returns *artifacts*."""
    session = MagicMock()

    # Support both filtered and unfiltered query chains.
    query_mock = MagicMock()
    query_mock.all.return_value = artifacts
    query_mock.filter.return_value = query_mock
    session.query.return_value = query_mock

    return session


# ---------------------------------------------------------------------------
# BomGenerator integration
# ---------------------------------------------------------------------------


class TestBomGeneratorEndToEnd:
    """End-to-end tests for BomGenerator.generate()."""

    def test_generates_valid_bom_structure(self):
        """generate() returns a dict with all required top-level keys."""
        artifacts = [
            _make_artifact("my-skill", "skill"),
            _make_artifact("my-command", "command"),
            _make_artifact("my-agent", "agent"),
        ]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        assert result["schema_version"] == "1.0.0"
        assert isinstance(result["generated_at"], str)
        assert result["artifact_count"] == 3
        assert isinstance(result["artifacts"], list)
        assert len(result["artifacts"]) == 3
        assert "metadata" in result
        assert "generator" in result["metadata"]
        assert "elapsed_ms" in result["metadata"]

    def test_artifact_count_matches_input(self):
        """artifact_count equals the number of adapted artifacts."""
        artifacts = [_make_artifact(f"a-{i}", "skill") for i in range(8)]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        assert result["artifact_count"] == 8

    def test_each_entry_has_required_keys(self):
        """Every BOM artifact entry contains name, type, source, version,
        content_hash, and metadata."""
        required_keys = {"name", "type", "source", "version", "content_hash", "metadata"}
        artifacts = [
            _make_artifact("skill-a", "skill"),
            _make_artifact("cmd-b", "command", source="user/repo/cmd-b"),
            _make_artifact("agent-c", "agent"),
        ]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        for entry in result["artifacts"]:
            assert required_keys.issubset(entry.keys()), (
                f"Entry {entry.get('name')} missing keys: "
                f"{required_keys - entry.keys()}"
            )

    def test_output_is_deterministic(self):
        """Calling generate() twice returns identical output (same BOM)."""
        artifacts = [
            _make_artifact("skill-x", "skill", content="some content"),
            _make_artifact("cmd-y", "command"),
            _make_artifact("hook-z", "hook"),
        ]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)

        first = gen.generate()
        second = gen.generate()

        # Compare JSON representations to normalise datetime differences
        # (generated_at will differ so compare only the artifact list).
        assert first["artifacts"] == second["artifacts"]
        assert first["artifact_count"] == second["artifact_count"]

    def test_entries_sorted_by_type_then_name(self):
        """Entries are sorted deterministically by (type, name)."""
        artifacts = [
            _make_artifact("z-skill", "skill"),
            _make_artifact("a-skill", "skill"),
            _make_artifact("m-command", "command"),
        ]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        keys = [(e["type"], e["name"]) for e in result["artifacts"]]
        assert keys == sorted(keys)

    def test_content_hashes_are_valid_hex_or_empty(self):
        """Each content_hash is a 64-character hex string or the empty string."""
        artifacts = [
            _make_artifact("skill-with-content", "skill", content="hello"),
            _make_artifact("skill-no-content", "skill"),  # no content → ""
        ]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        for entry in result["artifacts"]:
            ch = entry["content_hash"]
            assert isinstance(ch, str), f"content_hash must be str, got {type(ch)}"
            if ch:
                assert len(ch) == 64, f"non-empty hash must be 64 chars, got {len(ch)}"
                assert all(c in "0123456789abcdef" for c in ch), (
                    f"content_hash not valid hex: {ch}"
                )

    def test_source_preserved_in_entry(self):
        """The source field from the Artifact is preserved verbatim."""
        src = "anthropics/skills/canvas"
        artifacts = [_make_artifact("canvas", "skill", source=src)]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        assert result["artifacts"][0]["source"] == src

    def test_version_prefers_deployed_version(self):
        """version field prefers deployed_version over upstream_version."""
        art = _make_artifact(
            "versioned-skill",
            "skill",
            deployed_version="v1.2.3",
            upstream_version="v1.2.4",
        )
        session = _make_session([art])
        gen = BomGenerator(session=session)
        result = gen.generate()

        assert result["artifacts"][0]["version"] == "v1.2.3"

    def test_project_id_filter(self):
        """generate(project_id=...) filters via the session query."""
        artifacts = [_make_artifact("filtered-skill", "skill", project_id="proj-A")]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        gen.generate(project_id="proj-A")

        # Verify filter() was called on the query.
        session.query.return_value.filter.assert_called_once()

    def test_mixed_artifact_types(self):
        """BomGenerator handles all built-in types without error."""
        type_names = [
            ("skill", "s1"),
            ("command", "c1"),
            ("agent", "a1"),
            ("mcp_server", "m1"),
            ("hook", "h1"),
            ("workflow", "w1"),
            ("project_config", "cfg1"),
            ("spec_file", "spec1"),
            ("rule_file", "rule1"),
            ("context_file", "ctx1"),
        ]
        artifacts = [_make_artifact(name, t) for t, name in type_names]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        assert result["artifact_count"] == len(type_names)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestBomGeneratorErrorHandling:
    """Tests for error handling in BomGenerator."""

    def test_unknown_type_is_skipped_not_crashed(self):
        """Artifacts with unregistered types are skipped; no exception raised."""
        artifacts = [
            _make_artifact("known-skill", "skill"),
            _make_artifact("unknown-widget", "widget"),  # no adapter
        ]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)
        result = gen.generate()

        # Only the skill is included; widget is skipped.
        assert result["artifact_count"] == 1
        assert result["artifacts"][0]["name"] == "known-skill"

    def test_unknown_type_logged_as_warning(self, caplog):
        """A warning is logged for the first artifact of an unknown type."""
        import logging

        artifacts = [_make_artifact("mystery", "mystery_type")]
        session = _make_session(artifacts)
        gen = BomGenerator(session=session)

        with caplog.at_level(logging.WARNING, logger="skillmeat.core.bom.generator"):
            gen.generate()

        assert any("mystery_type" in r.message for r in caplog.records)

    def test_empty_artifact_list(self):
        """generate() with no artifacts returns valid BOM with 0 entries."""
        session = _make_session([])
        gen = BomGenerator(session=session)
        result = gen.generate()

        assert result["artifact_count"] == 0
        assert result["artifacts"] == []


# ---------------------------------------------------------------------------
# CompositeAdapter
# ---------------------------------------------------------------------------


class TestCompositeAdapter:
    """Tests for CompositeAdapter member resolution."""

    def test_members_populated_from_session(self):
        """CompositeAdapter includes members list from CompositeMembership rows."""
        child_art = _make_artifact("child-skill", "skill")
        child_art.uuid = "uuid-child-skill"

        membership = MagicMock()
        membership.child_artifact_uuid = "uuid-child-skill"
        membership.child_artifact = child_art
        membership.relationship_type = "bundled"
        membership.pinned_version_hash = None

        session = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [membership]
        session.query.return_value = query_mock

        parent_art = _make_artifact("my-composite", "composite")
        adapter = CompositeAdapter(session=session)
        entry = adapter.adapt(parent_art)

        assert "members" in entry
        assert len(entry["members"]) == 1
        member = entry["members"][0]
        assert member["name"] == "child-skill"
        assert member["type"] == "skill"
        assert member["relationship_type"] == "bundled"

    def test_no_session_returns_empty_members(self):
        """CompositeAdapter without session returns empty members list."""
        art = _make_artifact("lonely-composite", "composite")
        adapter = CompositeAdapter(session=None)
        entry = adapter.adapt(art)

        assert entry["members"] == []

    def test_content_hash_over_sorted_uuids(self):
        """Content hash is computed from sorted child UUIDs for determinism."""
        m1 = MagicMock()
        m1.child_artifact_uuid = "uuid-b"
        m2 = MagicMock()
        m2.child_artifact_uuid = "uuid-a"

        session = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [m1, m2]
        session.query.return_value = query_mock

        art = _make_artifact("my-composite", "composite")
        adapter = CompositeAdapter(session=session)
        hash_val = adapter.compute_content_hash(art)

        expected = _hash_string("composite:my-composite:uuid-a|uuid-b")
        # The hash is built as f"{artifact.id}:{'|'.join(child_uuids)}"
        expected = _hash_string(f"{art.id}:uuid-a|uuid-b")
        assert hash_val == expected
        assert len(hash_val) == 64


# ---------------------------------------------------------------------------
# MemoryItemAdapter
# ---------------------------------------------------------------------------


class TestMemoryItemAdapter:
    """Tests for MemoryItemAdapter metadata extraction."""

    def test_metadata_extracted_from_memory_item(self):
        """MemoryItemAdapter includes memory_type, confidence, status, anchors."""
        mem_item = MagicMock()
        mem_item.type = "gotcha"
        mem_item.confidence = 0.9
        mem_item.status = "active"
        mem_item.content = "Some memory content"
        mem_item.content_hash = _hash_string("Some memory content")
        mem_item.anchors_json = json.dumps([{"path": "foo.py", "type": "code"}])
        mem_item.id = "mem-id-1"

        session = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = mem_item
        session.query.return_value = query_mock

        art = _make_artifact("mem-id-1", "memory_item", content_hash=mem_item.content_hash)
        adapter = MemoryItemAdapter(session=session)
        entry = adapter.adapt(art)

        assert entry["type"] == "memory_item"
        assert entry["metadata"]["memory_type"] == "gotcha"
        assert entry["metadata"]["confidence"] == 0.9
        assert entry["metadata"]["status"] == "active"
        assert isinstance(entry["metadata"]["anchors"], list)

    def test_content_hash_uses_cached_hash(self):
        """MemoryItemAdapter prefers artifact.content_hash over recomputing."""
        cached = _hash_string("precomputed")
        art = _make_artifact("cached-mem", "memory_item", content_hash=cached)
        adapter = MemoryItemAdapter(session=None)
        ch = adapter.compute_content_hash(art)

        assert ch == cached

    def test_no_session_returns_empty_metadata(self):
        """MemoryItemAdapter without session returns None metadata fields."""
        art = _make_artifact("lonely-mem", "memory_item")
        adapter = MemoryItemAdapter(session=None)
        entry = adapter.adapt(art)

        assert entry["metadata"]["memory_type"] is None
        assert entry["metadata"]["confidence"] is None
        assert entry["metadata"]["anchors"] == []


# ---------------------------------------------------------------------------
# DeploymentSetAdapter
# ---------------------------------------------------------------------------


class TestDeploymentSetAdapter:
    """Tests for DeploymentSetAdapter member list construction."""

    def _make_ds_member(
        self,
        member_id: str,
        artifact_uuid: Optional[str] = None,
        group_id: Optional[str] = None,
        member_set_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        position: int = 0,
    ) -> MagicMock:
        m = MagicMock()
        m.id = member_id
        m.artifact_uuid = artifact_uuid
        m.group_id = group_id
        m.member_set_id = member_set_id
        m.workflow_id = workflow_id
        m.position = position
        return m

    def test_members_list_populated(self):
        """DeploymentSetAdapter builds members list from DeploymentSetMember rows."""
        ds = MagicMock()
        ds.name = "my-set"
        ds.description = "Test set"
        ds.members = [
            self._make_ds_member("m1", artifact_uuid="uuid-art-1", position=0),
            self._make_ds_member("m2", group_id="grp-1", position=1),
        ]
        ds.get_tags.return_value = ["backend"]

        session = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = ds
        session.query.return_value = query_mock

        art = _make_artifact("my-set", "deployment_set")
        adapter = DeploymentSetAdapter(session=session)
        entry = adapter.adapt(art)

        assert "members" in entry
        assert len(entry["members"]) == 2

        artifact_member = next(m for m in entry["members"] if m["ref_type"] == "artifact")
        assert artifact_member["ref_id"] == "uuid-art-1"
        assert artifact_member["position"] == 0

        group_member = next(m for m in entry["members"] if m["ref_type"] == "group")
        assert group_member["ref_id"] == "grp-1"
        assert group_member["position"] == 1

    def test_metadata_includes_description_and_tags(self):
        """DeploymentSetAdapter includes description and tags in metadata."""
        ds = MagicMock()
        ds.name = "tagged-set"
        ds.description = "A description"
        ds.members = []
        ds.get_tags.return_value = ["infra", "devops"]

        session = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = ds
        session.query.return_value = query_mock

        art = _make_artifact("tagged-set", "deployment_set")
        adapter = DeploymentSetAdapter(session=session)
        entry = adapter.adapt(art)

        assert entry["metadata"]["description"] == "A description"
        assert entry["metadata"]["tags"] == ["infra", "devops"]

    def test_no_session_returns_empty_members(self):
        """DeploymentSetAdapter without session returns empty members list."""
        art = _make_artifact("no-session-set", "deployment_set")
        adapter = DeploymentSetAdapter(session=None)
        entry = adapter.adapt(art)

        assert entry["members"] == []

    def test_content_hash_is_deterministic(self):
        """Content hash is the same for identical member sets."""
        ds = MagicMock()
        ds.name = "stable-set"
        ds.members = [
            self._make_ds_member("m1", artifact_uuid="uuid-X"),
            self._make_ds_member("m2", artifact_uuid="uuid-Y"),
        ]
        ds.get_tags.return_value = []

        session = MagicMock()
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = ds
        session.query.return_value = query_mock

        art = _make_artifact("stable-set", "deployment_set")
        adapter = DeploymentSetAdapter(session=session)

        h1 = adapter.compute_content_hash(art)
        h2 = adapter.compute_content_hash(art)

        assert h1 == h2
        assert len(h1) == 64


# ---------------------------------------------------------------------------
# BomSerializer
# ---------------------------------------------------------------------------


class TestBomSerializer:
    """Tests for BomSerializer."""

    def _sample_bom(self) -> Dict[str, Any]:
        """Return a minimal valid BOM dict."""
        return {
            "schema_version": "1.0.0",
            "generated_at": "2026-03-12T00:00:00+00:00",
            "project_path": None,
            "artifact_count": 1,
            "artifacts": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "source": None,
                    "version": None,
                    "content_hash": "a" * 64,
                    "metadata": {},
                }
            ],
            "metadata": {"generator": "skillmeat-bom", "elapsed_ms": 1.5},
        }

    def test_to_json_returns_valid_json_string(self):
        """to_json() returns a valid JSON string."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        result = serializer.to_json(bom)

        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["schema_version"] == "1.0.0"

    def test_to_json_sorts_keys(self):
        """to_json() produces deterministic output with sorted keys."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        result = serializer.to_json(bom)

        # Parse and re-serialize to check key order stability.
        parsed = json.loads(result)
        keys = list(parsed.keys())
        assert keys == sorted(keys), "Top-level keys are not sorted"

    def test_to_json_uses_2_space_indent(self):
        """to_json() uses 2-space indentation."""
        bom = {"schema_version": "1.0.0", "artifacts": []}
        serializer = BomSerializer()
        result = serializer.to_json(bom)

        # 2-space indent means "  " appears in the output.
        assert "  " in result

    def test_to_dict_returns_input_unchanged(self):
        """to_dict() returns the exact same dict object."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        result = serializer.to_dict(bom)

        assert result is bom

    def test_write_file_creates_file(self, tmp_path: Path):
        """write_file() creates the file at the given path."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        target = tmp_path / "context.lock"
        serializer.write_file(bom, target)

        assert target.exists()

    def test_write_file_content_is_valid_json(self, tmp_path: Path):
        """write_file() writes valid JSON that round-trips correctly."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        target = tmp_path / "context.lock"
        serializer.write_file(bom, target)

        content = target.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["schema_version"] == "1.0.0"
        assert parsed["artifact_count"] == 1

    def test_write_file_permissions_are_0o644(self, tmp_path: Path):
        """write_file() sets file permissions to 0o644."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        target = tmp_path / "context.lock"
        serializer.write_file(bom, target)

        file_mode = stat.S_IMODE(target.stat().st_mode)
        assert file_mode == 0o644, f"Expected 0o644, got 0o{file_mode:o}"

    def test_write_file_is_atomic_no_temp_files_left(self, tmp_path: Path):
        """write_file() leaves no temp files in the directory after success."""
        bom = self._sample_bom()
        serializer = BomSerializer()
        target = tmp_path / "context.lock"
        serializer.write_file(bom, target)

        remaining = list(tmp_path.glob(".bom_tmp_*"))
        assert remaining == [], f"Temp files found: {remaining}"

    def test_write_file_overwrites_existing(self, tmp_path: Path):
        """write_file() overwrites an existing file atomically."""
        bom1 = {**self._sample_bom(), "artifact_count": 1}
        bom2 = {**self._sample_bom(), "artifact_count": 99}
        serializer = BomSerializer()
        target = tmp_path / "context.lock"

        serializer.write_file(bom1, target)
        serializer.write_file(bom2, target)

        content = json.loads(target.read_text(encoding="utf-8"))
        assert content["artifact_count"] == 99
