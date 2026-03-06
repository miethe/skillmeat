"""Unit tests for EnterpriseContentService.

Tests build_payload() structure, version resolution strategies, compression,
and tenant-isolation exception paths.  No real DB or filesystem I/O —
everything is mocked.
"""

from __future__ import annotations

import gzip
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.services.enterprise_content import (
    ArtifactFilesystemError,
    ArtifactNotFoundError,
    ArtifactVersionNotFoundError,
    EnterpriseContentService,
    _resolve_artifact_fs_path,
    _is_excluded,
)


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
ARTIFACT_UUID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CONTENT_HASH = "a" * 64  # 64-char hex string (valid hash format)
VERSION_TAG = "v1.2.0"


def _make_artifact(
    artifact_id: uuid.UUID = ARTIFACT_UUID,
    name: str = "canvas-design",
    artifact_type: str = "skill",
    tenant_id: uuid.UUID = TENANT_A,
    source_url: Optional[str] = "github:org/repo/path",
    description: Optional[str] = "A test skill",
    tags: Optional[List[str]] = None,
    scope: str = "user",
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Mock:
    artifact = Mock()
    artifact.id = artifact_id
    artifact.name = name
    artifact.artifact_type = artifact_type
    artifact.tenant_id = tenant_id
    artifact.source_url = source_url
    artifact.description = description
    artifact.tags = tags or ["ai", "design"]
    artifact.scope = scope
    artifact.custom_fields = custom_fields or {}
    return artifact


def _make_version(
    artifact_id: uuid.UUID = ARTIFACT_UUID,
    version_tag: str = VERSION_TAG,
    content_hash: str = CONTENT_HASH,
    created_at: Optional[datetime] = None,
    commit_sha: Optional[str] = "deadbeef",
) -> Mock:
    version = Mock()
    version.artifact_id = artifact_id
    version.version_tag = version_tag
    version.content_hash = content_hash
    version.created_at = created_at or datetime(2024, 6, 1, tzinfo=timezone.utc)
    version.commit_sha = commit_sha
    return version


def _make_service(
    artifact: Optional[Mock] = None,
    version: Optional[Mock] = None,
    collection_root: Optional[Path] = None,
) -> tuple[EnterpriseContentService, Mock, Mock]:
    """Return (service, mock_repo, mock_session)."""
    mock_session = MagicMock()
    mock_repo = MagicMock()

    if artifact is not None:
        mock_repo.get.return_value = artifact
        mock_repo.get_by_name.return_value = artifact

    if version is not None:
        # Simulate session.execute(...).scalar_one_or_none() returning version
        mock_session.execute.return_value.scalar_one_or_none.return_value = version

    svc = EnterpriseContentService(
        session=mock_session,
        artifact_repo=mock_repo,
        collection_root=collection_root or Path("/fake/collection"),
    )
    return svc, mock_repo, mock_session


# ---------------------------------------------------------------------------
# _is_excluded helper
# ---------------------------------------------------------------------------


class TestIsExcluded:
    def test_excludes_ds_store(self):
        assert _is_excluded(".DS_Store") is True

    def test_excludes_git_dir(self):
        assert _is_excluded(".git") is True

    def test_excludes_node_modules(self):
        assert _is_excluded("node_modules") is True

    def test_excludes_tmp_suffix(self):
        assert _is_excluded("file.tmp") is True

    def test_excludes_swp_suffix(self):
        assert _is_excluded("file.swp") is True

    def test_excludes_tilde_prefix(self):
        assert _is_excluded("~$document.docx") is True

    def test_does_not_exclude_normal_file(self):
        assert _is_excluded("SKILL.md") is False

    def test_does_not_exclude_normal_dir(self):
        assert _is_excluded("commands") is False


# ---------------------------------------------------------------------------
# _resolve_artifact_fs_path helper
# ---------------------------------------------------------------------------


class TestResolveArtifactFsPath:
    def test_skill_uses_dir_layout(self, tmp_path: Path):
        p = _resolve_artifact_fs_path("canvas-design", "skill", tmp_path)
        assert p == tmp_path / "skills" / "canvas-design"

    def test_command_uses_file_layout(self, tmp_path: Path):
        p = _resolve_artifact_fs_path("run-tests", "command", tmp_path)
        assert p == tmp_path / "commands" / "run-tests.md"

    def test_agent_uses_file_layout(self, tmp_path: Path):
        p = _resolve_artifact_fs_path("my-agent", "agent", tmp_path)
        assert p == tmp_path / "agents" / "my-agent.md"

    def test_composite_uses_dir_layout(self, tmp_path: Path):
        p = _resolve_artifact_fs_path("my-plugin", "composite", tmp_path)
        assert p == tmp_path / "composites" / "my-plugin"

    def test_custom_fields_fs_path_absolute(self, tmp_path: Path):
        override = tmp_path / "custom" / "artifact"
        p = _resolve_artifact_fs_path(
            "canvas-design",
            "skill",
            tmp_path,
            custom_fields={"fs_path": str(override)},
        )
        assert p == override

    def test_custom_fields_fs_path_relative(self, tmp_path: Path):
        p = _resolve_artifact_fs_path(
            "canvas-design",
            "skill",
            tmp_path,
            custom_fields={"fs_path": "custom/canvas-design"},
        )
        assert p == tmp_path / "custom" / "canvas-design"

    def test_unknown_type_falls_back_gracefully(self, tmp_path: Path):
        p = _resolve_artifact_fs_path("widget", "widget", tmp_path)
        # Unknown type appends 's' as subdir and treats as directory
        assert p == tmp_path / "widgets" / "widget"


# ---------------------------------------------------------------------------
# build_payload — structure tests
# ---------------------------------------------------------------------------


class TestBuildPayloadStructure:
    """build_payload returns correct JSON-serialisable dict keys and values."""

    def test_payload_top_level_keys(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        # Create a minimal skill directory so _collect_files has something.
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Canvas Design")

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("canvas-design")

        assert isinstance(payload, dict)
        assert set(payload.keys()) == {
            "artifact_id",
            "version",
            "content_hash",
            "metadata",
            "files",
        }

    def test_payload_artifact_id_is_str(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("canvas-design")

        assert payload["artifact_id"] == str(ARTIFACT_UUID)

    def test_payload_version_and_hash(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version(version_tag="v2.0.0", content_hash="b" * 64)
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("canvas-design")

        assert payload["version"] == "v2.0.0"
        assert payload["content_hash"] == "b" * 64

    def test_payload_metadata_fields(self, tmp_path: Path):
        artifact = _make_artifact(
            name="test-skill",
            artifact_type="skill",
            source_url="github:org/repo",
            description="desc",
            tags=["tag1"],
            scope="user",
        )
        version = _make_version()
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("test-skill")

        meta = payload["metadata"]
        assert meta["name"] == "test-skill"
        assert meta["type"] == "skill"
        assert meta["source"] == "github:org/repo"
        assert meta["description"] == "desc"
        assert meta["tags"] == ["tag1"]
        assert meta["scope"] == "user"

    def test_payload_files_list(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Canvas")
        (skill_dir / "prompt.md").write_text("You are a canvas expert.")

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("canvas-design")

        files = payload["files"]
        assert isinstance(files, list)
        assert len(files) == 2
        paths = [f["path"] for f in files]
        assert "SKILL.md" in paths
        assert "prompt.md" in paths

    def test_payload_file_entry_keys(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content")

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("canvas-design")

        entry = payload["files"][0]
        assert set(entry.keys()) == {"path", "content", "size", "encoding"}
        assert entry["encoding"] in ("utf-8", "base64")
        assert isinstance(entry["size"], int)

    def test_no_version_rows_payload_has_unknown_version(self, tmp_path: Path):
        """When artifact has no version rows, version='unknown' and hash=''."""
        artifact = _make_artifact()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, mock_session = _make_service(
            artifact, version=None, collection_root=tmp_path
        )
        # session.execute().scalar_one_or_none() returns None (no version)
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        payload = svc.build_payload("canvas-design")

        assert payload["version"] == "unknown"
        assert payload["content_hash"] == ""


# ---------------------------------------------------------------------------
# build_payload — version resolution
# ---------------------------------------------------------------------------


class TestVersionResolution:
    """Version parameter resolution: hash, tag, and latest fallback."""

    def test_version_none_resolves_latest(self, tmp_path: Path):
        artifact = _make_artifact()
        latest = _make_version(version_tag="v3.0.0")
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, mock_session = _make_service(
            artifact, version=None, collection_root=tmp_path
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = latest

        payload = svc.build_payload("canvas-design", version=None)
        assert payload["version"] == "v3.0.0"

    def test_version_tag_resolves(self, tmp_path: Path):
        artifact = _make_artifact()
        tagged = _make_version(version_tag="v1.0.0", content_hash="c" * 64)
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, mock_session = _make_service(
            artifact, version=None, collection_root=tmp_path
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = tagged

        payload = svc.build_payload("canvas-design", version="v1.0.0")
        assert payload["version"] == "v1.0.0"
        assert payload["content_hash"] == "c" * 64

    def test_version_content_hash_resolves(self, tmp_path: Path):
        artifact = _make_artifact()
        hashed = _make_version(version_tag="v2.0.0", content_hash=CONTENT_HASH)
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, mock_session = _make_service(
            artifact, version=None, collection_root=tmp_path
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = hashed

        # Pass a 64-char hex string — should trigger hash lookup
        payload = svc.build_payload("canvas-design", version=CONTENT_HASH)
        assert payload["content_hash"] == CONTENT_HASH

    def test_unknown_version_raises(self, tmp_path: Path):
        artifact = _make_artifact()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, mock_session = _make_service(
            artifact, version=None, collection_root=tmp_path
        )
        # No matching version row
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ArtifactVersionNotFoundError) as exc_info:
            svc.build_payload("canvas-design", version="bad-tag")

        assert exc_info.value.artifact_id == str(ARTIFACT_UUID)
        assert exc_info.value.version == "bad-tag"

    def test_unknown_hash_raises(self, tmp_path: Path):
        artifact = _make_artifact()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, mock_session = _make_service(
            artifact, version=None, collection_root=tmp_path
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        bad_hash = "f" * 64
        with pytest.raises(ArtifactVersionNotFoundError):
            svc.build_payload("canvas-design", version=bad_hash)


# ---------------------------------------------------------------------------
# build_payload — compression
# ---------------------------------------------------------------------------


class TestBuildPayloadCompression:
    def test_compress_true_returns_bytes(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("hello")

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        result = svc.build_payload("canvas-design", compress=True)

        assert isinstance(result, bytes)

    def test_compress_true_is_gzip_decodable(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("hello world")

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        compressed = svc.build_payload("canvas-design", compress=True)

        decompressed = gzip.decompress(compressed)
        payload = json.loads(decompressed.decode("utf-8"))

        assert "artifact_id" in payload
        assert "files" in payload

    def test_compress_false_returns_dict(self, tmp_path: Path):
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        result = svc.build_payload("canvas-design", compress=False)

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# build_payload — ArtifactNotFoundError
# ---------------------------------------------------------------------------


class TestArtifactNotFound:
    def test_not_found_by_name_raises(self, tmp_path: Path):
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_repo.get_by_name.return_value = None

        svc = EnterpriseContentService(
            session=mock_session,
            artifact_repo=mock_repo,
            collection_root=tmp_path,
        )
        with pytest.raises(ArtifactNotFoundError) as exc_info:
            svc.build_payload("nonexistent-artifact")

        assert "nonexistent-artifact" in str(exc_info.value)
        assert exc_info.value.artifact_id == "nonexistent-artifact"

    def test_not_found_by_uuid_raises(self, tmp_path: Path):
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get.return_value = None
        mock_repo.get_by_name.return_value = None

        svc = EnterpriseContentService(
            session=mock_session,
            artifact_repo=mock_repo,
            collection_root=tmp_path,
        )
        missing_uuid = str(uuid.uuid4())
        with pytest.raises(ArtifactNotFoundError):
            svc.build_payload(missing_uuid)


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """Artifact from tenant A must not be accessible from tenant B context."""

    def test_artifact_not_found_for_wrong_tenant(self, tmp_path: Path):
        """When repo returns None (tenant filter applied), raise ArtifactNotFoundError."""
        mock_session = MagicMock()
        mock_repo = MagicMock()
        # Simulates: tenant B's repo returns nothing for tenant A's artifact
        mock_repo.get.return_value = None
        mock_repo.get_by_name.return_value = None

        svc = EnterpriseContentService(
            session=mock_session,
            artifact_repo=mock_repo,
            collection_root=tmp_path,
        )
        with pytest.raises(ArtifactNotFoundError):
            svc.build_payload("canvas-design")

    def test_service_uses_injected_repo_for_lookups(self, tmp_path: Path):
        """Service delegates all DB access to the injected repo, not raw session."""
        artifact = _make_artifact(tenant_id=TENANT_A)
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, mock_repo, _ = _make_service(artifact, version, collection_root=tmp_path)
        svc.build_payload("canvas-design")

        # get_by_name should have been called (name lookup path for non-UUID)
        mock_repo.get_by_name.assert_called_once_with("canvas-design")

    def test_uuid_lookup_path_uses_repo_get(self, tmp_path: Path):
        """UUID-format artifact_id triggers repo.get(), not get_by_name()."""
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)

        svc, mock_repo, _ = _make_service(artifact, version, collection_root=tmp_path)
        svc.build_payload(str(ARTIFACT_UUID))

        mock_repo.get.assert_called_once_with(ARTIFACT_UUID)


# ---------------------------------------------------------------------------
# Filesystem error path
# ---------------------------------------------------------------------------


class TestArtifactFilesystemError:
    def test_missing_fs_path_returns_empty_files(self, tmp_path: Path):
        """Non-existent FS path → payload with empty files list (warning logged)."""
        artifact = _make_artifact()
        version = _make_version()
        # Do NOT create the skill directory → fs_path won't exist.

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)
        payload = svc.build_payload("canvas-design")

        assert payload["files"] == []

    def test_unreadable_dir_raises_filesystem_error(self, tmp_path: Path):
        """If os.walk raises, ArtifactFilesystemError propagates."""
        artifact = _make_artifact()
        version = _make_version()
        skill_dir = tmp_path / "skills" / "canvas-design"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("content")

        svc, _, _ = _make_service(artifact, version, collection_root=tmp_path)

        with patch("skillmeat.core.services.enterprise_content.os.walk") as mock_walk:
            mock_walk.side_effect = OSError("permission denied")
            with pytest.raises(ArtifactFilesystemError):
                svc.build_payload("canvas-design")
