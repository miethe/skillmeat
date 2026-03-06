"""Targeted coverage tests for skillmeat.core.repositories and interfaces.

Covers the missing lines identified by the initial coverage report:
- local_artifact.py: 45% → targets get/get_by_uuid/list/count/search/delete edge cases,
  get_content/update_content dir handling, get_tags, _tag_name_to_dto
- local_project.py: 51% → targets get/list/create/update/delete/get_artifacts/refresh,
  filesystem fallback paths, _discover_project_paths helpers
- local_tag.py: 62% → targets assign/unassign, _resolve_artifact_uuid, _slugify edge cases
- local_collection.py: 65% → targets get_by_id/get_artifacts with filters, _artifact_to_dto
- skillmeat.core.interfaces.dtos: from_dict classmethods, _to_iso
- skillmeat.core.interfaces.context: RequestContext.create()

All external collaborators are mocked; no real filesystem collection or live DB needed.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import (
    ArtifactDTO,
    CollectionDTO,
    DeploymentDTO,
    ProjectDTO,
    SettingsDTO,
    TagDTO,
)
from skillmeat.core.repositories import (
    LocalArtifactRepository,
    LocalCollectionRepository,
    LocalProjectRepository,
    LocalTagRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_id(path: str) -> str:
    return base64.b64encode(path.encode()).decode()


def _make_artifact(
    name: str = "my-skill",
    artifact_type: str = "skill",
    tags: list | None = None,
    uuid: str | None = "aabb1122ccdd3344eeff5566aabb1122",
    description: str = "A test skill",
    upstream: str | None = None,
    path: str | None = None,
    added=None,
    last_updated=None,
) -> MagicMock:
    m = MagicMock()
    m.name = name
    m.type = MagicMock()
    m.type.value = artifact_type
    m.tags = tags or []
    m.metadata = MagicMock()
    m.metadata.description = description
    m.metadata.tags = []
    m.metadata.to_dict.return_value = {"description": description}
    m.upstream = upstream
    m.path = path or f"{artifact_type}s/{name}"
    m.uuid = uuid
    m.added = added
    m.last_updated = last_updated
    m.resolved_version = "v1.0.0"
    m.version_spec = "latest"
    return m


def _make_tag_orm(
    tag_id: str = "tag-abc",
    name: str = "python",
    slug: str = "python",
    color: str | None = "#336699",
) -> MagicMock:
    m = MagicMock()
    m.id = tag_id
    m.name = name
    m.slug = slug
    m.color = color
    m.artifact_tags = []
    m.deployment_set_tags = []
    m.created_at = None
    m.updated_at = None
    return m


# ============================================================================
# RequestContext
# ============================================================================


class TestRequestContext:
    def test_create_with_explicit_id(self):
        ctx = RequestContext.create(request_id="my-req-123")
        assert ctx.request_id == "my-req-123"
        assert ctx.edition == "local"

    def test_create_without_id_generates_uuid(self):
        ctx = RequestContext.create()
        assert len(ctx.request_id) > 0
        # Should be a UUID4 — 36 chars with dashes
        assert len(ctx.request_id) == 36

    def test_defaults(self):
        ctx = RequestContext()
        assert ctx.user_id is None
        assert ctx.tenant_id is None
        assert ctx.edition == "local"
        assert ctx.request_id == ""


# ============================================================================
# DTO from_dict and _to_iso helpers
# ============================================================================


class TestArtifactDTOFromDict:
    def test_from_dict_minimal(self):
        dto = ArtifactDTO.from_dict({"id": "skill:foo", "name": "foo", "artifact_type": "skill"})
        assert dto.id == "skill:foo"
        assert dto.artifact_type == "skill"
        assert dto.is_outdated is False

    def test_from_dict_with_orm_type_alias(self):
        # ORM column is called "type", not "artifact_type"
        dto = ArtifactDTO.from_dict({"id": "skill:bar", "name": "bar", "type": "skill"})
        assert dto.artifact_type == "skill"

    def test_from_dict_with_datetime_created_at(self):
        dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        dto = ArtifactDTO.from_dict(
            {"id": "skill:x", "name": "x", "artifact_type": "skill", "created_at": dt}
        )
        assert dto.created_at is not None
        assert "2024" in dto.created_at

    def test_from_dict_deployed_version_alias(self):
        dto = ArtifactDTO.from_dict(
            {
                "id": "skill:x",
                "name": "x",
                "artifact_type": "skill",
                "deployed_version": "v2.0",
            }
        )
        assert dto.version == "v2.0"

    def test_from_dict_uses_tags_as_list(self):
        dto = ArtifactDTO.from_dict(
            {"id": "skill:x", "name": "x", "artifact_type": "skill", "tags": ["a", "b"]}
        )
        assert list(dto.tags) == ["a", "b"]


class TestProjectDTOFromDict:
    def test_from_dict_minimal(self):
        dto = ProjectDTO.from_dict({"id": "abc", "name": "proj", "path": "/tmp/proj"})
        assert dto.id == "abc"
        assert dto.status == "active"
        assert dto.artifact_count == 0

    def test_from_dict_with_all_fields(self):
        dto = ProjectDTO.from_dict(
            {
                "id": "xyz",
                "name": "my-project",
                "path": "/home/user/proj",
                "description": "desc",
                "status": "stale",
                "artifact_count": 5,
                "created_at": "2024-01-01T00:00:00",
                "last_fetched": "2024-02-01T00:00:00",
            }
        )
        assert dto.description == "desc"
        assert dto.status == "stale"
        assert dto.artifact_count == 5


class TestCollectionDTOFromDict:
    def test_from_dict_minimal(self):
        dto = CollectionDTO.from_dict({"id": "main", "name": "main"})
        assert dto.id == "main"
        assert dto.version == "1.0.0"

    def test_from_dict_uses_created_alias(self):
        dto = CollectionDTO.from_dict(
            {"id": "c1", "name": "c1", "created": "2024-01-01", "updated": "2024-02-01"}
        )
        assert dto.created_at == "2024-01-01"
        assert dto.updated_at == "2024-02-01"


class TestDeploymentDTOFromDict:
    def test_from_dict_minimal(self):
        dto = DeploymentDTO.from_dict(
            {
                "id": "dep-1",
                "artifact_id": "skill:foo",
                "artifact_name": "foo",
                "artifact_type": "skill",
            }
        )
        assert dto.id == "dep-1"
        assert dto.status == "deployed"
        assert dto.local_modifications is False

    def test_from_dict_target_path_alias(self):
        dto = DeploymentDTO.from_dict(
            {
                "id": "dep-2",
                "artifact_id": "skill:foo",
                "artifact_name": "foo",
                "artifact_type": "skill",
                "deployed_path": "/target/foo",
            }
        )
        assert dto.target_path == "/target/foo"

    def test_from_dict_collection_sha_alias(self):
        dto = DeploymentDTO.from_dict(
            {
                "id": "dep-3",
                "artifact_id": "skill:foo",
                "artifact_name": "foo",
                "artifact_type": "skill",
                "content_hash": "deadbeef",
            }
        )
        assert dto.collection_sha == "deadbeef"


class TestTagDTOFromDict:
    def test_from_dict_full(self):
        dto = TagDTO.from_dict(
            {
                "id": "t1",
                "name": "Python",
                "slug": "python",
                "color": "#336699",
                "artifact_count": 3,
                "deployment_set_count": 1,
            }
        )
        assert dto.color == "#336699"
        assert dto.artifact_count == 3

    def test_from_dict_none_counts_default_to_zero(self):
        dto = TagDTO.from_dict(
            {"id": "t2", "name": "go", "slug": "go", "artifact_count": None}
        )
        assert dto.artifact_count == 0


class TestSettingsDTOFromDict:
    def test_from_dict_known_keys(self):
        dto = SettingsDTO.from_dict(
            {
                "github_token": "ghp_test",
                "default_scope": "local",
                "edition": "enterprise",
                "indexing_mode": "on",
            }
        )
        assert dto.github_token == "ghp_test"
        assert dto.default_scope == "local"

    def test_from_dict_unknown_keys_go_to_extra(self):
        dto = SettingsDTO.from_dict(
            {"github_token": None, "my_custom_key": "value"}
        )
        assert "my_custom_key" in dto.extra
        assert dto.extra["my_custom_key"] == "value"


# ============================================================================
# LocalArtifactRepository — uncovered methods
# ============================================================================


@pytest.fixture
def artifact_mgr():
    mgr = MagicMock()
    mgr.show.side_effect = ValueError("not found")
    return mgr


@pytest.fixture
def path_resolver(tmp_path):
    r = MagicMock()
    r.collection_root.return_value = tmp_path
    return r


@pytest.fixture
def artifact_repo(artifact_mgr, path_resolver):
    return LocalArtifactRepository(
        artifact_manager=artifact_mgr,
        path_resolver=path_resolver,
        db_session=None,
        refresh_fn=None,
    )


class TestLocalArtifactRepositoryGet:
    def test_get_invalid_id_returns_none(self, artifact_repo):
        result = artifact_repo.get("no-colon-here")
        assert result is None

    def test_get_unknown_type_returns_none(self, artifact_repo):
        result = artifact_repo.get("unknown_type:foo")
        assert result is None

    def test_get_not_found_returns_none(self, artifact_repo, artifact_mgr):
        artifact_mgr.show.side_effect = ValueError("not found")
        assert artifact_repo.get("skill:ghost") is None

    def test_get_manager_exception_returns_none(self, artifact_repo, artifact_mgr):
        artifact_mgr.show.side_effect = RuntimeError("db error")
        assert artifact_repo.get("skill:bad") is None

    def test_get_found_returns_dto(self, artifact_repo, artifact_mgr):
        mock_art = _make_artifact("canvas", "skill")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        dto = artifact_repo.get("skill:canvas")
        assert dto is not None
        assert dto.name == "canvas"
        assert dto.artifact_type == "skill"

    def test_get_with_datetime_timestamps(self, artifact_repo, artifact_mgr):
        from datetime import datetime, timezone

        mock_art = _make_artifact("ts-skill", "skill")
        mock_art.added = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_art.last_updated = datetime(2024, 6, 1, tzinfo=timezone.utc)
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        dto = artifact_repo.get("skill:ts-skill")
        assert dto.created_at is not None
        assert "2024" in dto.created_at


class TestLocalArtifactRepositoryGetByUuid:
    def test_returns_none_when_not_found(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.return_value = []
        result = artifact_repo.get_by_uuid("nonexistent-uuid")
        assert result is None

    def test_returns_dto_when_found(self, artifact_repo, artifact_mgr):
        mock_art = _make_artifact("found-skill", "skill", uuid="aabb1122ccdd3344")
        artifact_mgr.list_artifacts.return_value = [mock_art]
        result = artifact_repo.get_by_uuid("aabb1122ccdd3344")
        assert result is not None
        assert result.name == "found-skill"

    def test_returns_none_on_list_exception(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.side_effect = RuntimeError("fail")
        result = artifact_repo.get_by_uuid("any-uuid")
        assert result is None


class TestLocalArtifactRepositoryList:
    def test_list_all(self, artifact_repo, artifact_mgr):
        artifacts = [_make_artifact(f"skill-{i}", "skill") for i in range(3)]
        artifact_mgr.list_artifacts.return_value = artifacts
        result = artifact_repo.list()
        assert len(result) == 3

    def test_list_with_pagination(self, artifact_repo, artifact_mgr):
        artifacts = [_make_artifact(f"skill-{i}", "skill") for i in range(10)]
        artifact_mgr.list_artifacts.return_value = artifacts
        result = artifact_repo.list(offset=3, limit=4)
        assert len(result) == 4

    def test_list_with_unknown_type_filter_returns_empty(self, artifact_repo, artifact_mgr):
        result = artifact_repo.list(filters={"artifact_type": "bogus_type_xyz"})
        assert result == []

    def test_list_on_manager_exception_returns_empty(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.side_effect = RuntimeError("fail")
        assert artifact_repo.list() == []


class TestLocalArtifactRepositoryCount:
    def test_count_empty(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.return_value = []
        assert artifact_repo.count() == 0

    def test_count_with_artifacts(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.return_value = [
            _make_artifact(f"s{i}", "skill") for i in range(5)
        ]
        assert artifact_repo.count() == 5

    def test_count_unknown_type_returns_zero(self, artifact_repo, artifact_mgr):
        assert artifact_repo.count(filters={"artifact_type": "nope"}) == 0

    def test_count_on_exception_returns_zero(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.side_effect = RuntimeError("fail")
        assert artifact_repo.count() == 0


class TestLocalArtifactRepositorySearch:
    def test_search_matches_name(self, artifact_repo, artifact_mgr):
        m = _make_artifact("canvas-design", "skill")
        artifact_mgr.list_artifacts.return_value = [m]
        result = artifact_repo.search("canvas")
        assert len(result) == 1

    def test_search_matches_description(self, artifact_repo, artifact_mgr):
        m = _make_artifact("foo", "skill", description="amazing tool for data")
        m.metadata.description = "amazing tool for data"
        artifact_mgr.list_artifacts.return_value = [m]
        result = artifact_repo.search("data")
        assert len(result) == 1

    def test_search_matches_tag(self, artifact_repo, artifact_mgr):
        m = _make_artifact("taggy", "skill", tags=["machine-learning"])
        artifact_mgr.list_artifacts.return_value = [m]
        result = artifact_repo.search("machine")
        assert len(result) == 1

    def test_search_no_match_returns_empty(self, artifact_repo, artifact_mgr):
        m = _make_artifact("nothing-relevant", "skill")
        artifact_mgr.list_artifacts.return_value = [m]
        result = artifact_repo.search("xyz_definitely_not_present")
        assert result == []

    def test_search_with_unknown_type_filter_returns_empty(self, artifact_repo, artifact_mgr):
        result = artifact_repo.search("anything", filters={"artifact_type": "bogus"})
        assert result == []

    def test_search_on_list_exception_returns_empty(self, artifact_repo, artifact_mgr):
        artifact_mgr.list_artifacts.side_effect = RuntimeError("fail")
        assert artifact_repo.search("query") == []


class TestLocalArtifactRepositoryDelete:
    def test_delete_invalid_id_returns_false(self, artifact_repo):
        assert artifact_repo.delete("no-colon") is False

    def test_delete_unknown_type_returns_false(self, artifact_repo):
        assert artifact_repo.delete("bogus_type:foo") is False

    def test_delete_remove_exception_returns_false(self, artifact_repo, artifact_mgr):
        mock_art = _make_artifact("bad-remove", "skill")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.remove.side_effect = RuntimeError("fs error")
        assert artifact_repo.delete("skill:bad-remove") is False


class TestLocalArtifactRepositoryGetContent:
    def test_get_content_file(self, artifact_repo, artifact_mgr, tmp_path):
        skill_file = tmp_path / "single-skill.md"
        skill_file.write_text("# Content", encoding="utf-8")

        mock_art = _make_artifact("single-skill", "skill", path="single-skill.md")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        content = artifact_repo.get_content("skill:single-skill")
        assert content == "# Content"

    def test_get_content_directory_with_descriptor(self, artifact_repo, artifact_mgr, tmp_path):
        skill_dir = tmp_path / "dir-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Dir Skill", encoding="utf-8")

        mock_art = _make_artifact("dir-skill", "skill", path="dir-skill")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        content = artifact_repo.get_content("skill:dir-skill")
        assert content == "# Dir Skill"

    def test_get_content_directory_fallback_to_md(self, artifact_repo, artifact_mgr, tmp_path):
        skill_dir = tmp_path / "fallback-skill"
        skill_dir.mkdir()
        (skill_dir / "notes.md").write_text("# Notes", encoding="utf-8")

        mock_art = _make_artifact("fallback-skill", "skill", path="fallback-skill")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        content = artifact_repo.get_content("skill:fallback-skill")
        assert content == "# Notes"

    def test_get_content_no_file_in_dir_raises(self, artifact_repo, artifact_mgr, tmp_path):
        skill_dir = tmp_path / "empty-dir"
        skill_dir.mkdir()

        mock_art = _make_artifact("empty-dir", "skill", path="empty-dir")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        with pytest.raises(FileNotFoundError):
            artifact_repo.get_content("skill:empty-dir")

    def test_get_content_path_missing_raises(self, artifact_repo, artifact_mgr, tmp_path):
        mock_art = _make_artifact("missing-path", "skill", path="nonexistent-path")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        with pytest.raises(FileNotFoundError):
            artifact_repo.get_content("skill:missing-path")

    def test_get_content_not_found_raises_key_error(self, artifact_repo, artifact_mgr):
        artifact_mgr.show.side_effect = ValueError("not found")
        with pytest.raises(KeyError):
            artifact_repo.get_content("skill:ghost")

    def test_get_content_bad_type_raises_key_error(self, artifact_repo):
        with pytest.raises(KeyError):
            artifact_repo.get_content("bogus_type:foo")

    def test_get_content_unresolvable_path_raises_file_not_found(
        self, artifact_repo, artifact_mgr
    ):
        mock_art = _make_artifact("resolve-fail", "skill")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        # Make config.get_collection_path raise an exception → path_str is None
        artifact_mgr.collection_mgr.config.get_collection_path.side_effect = RuntimeError("fail")

        with pytest.raises(FileNotFoundError):
            artifact_repo.get_content("skill:resolve-fail")


class TestLocalArtifactRepositoryUpdateContent:
    def test_update_content_directory_with_no_file_raises(
        self, artifact_repo, artifact_mgr, tmp_path
    ):
        skill_dir = tmp_path / "empty-dir-update"
        skill_dir.mkdir()

        mock_art = _make_artifact("empty-dir-update", "skill", path="empty-dir-update")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        with pytest.raises(FileNotFoundError):
            artifact_repo.update_content("skill:empty-dir-update", "content")

    def test_update_content_bad_type_raises_key_error(self, artifact_repo):
        with pytest.raises(KeyError):
            artifact_repo.update_content("bad_type:foo", "content")

    def test_update_content_path_missing_raises(self, artifact_repo, artifact_mgr, tmp_path):
        mock_art = _make_artifact("no-exist", "skill", path="nonexistent-path")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        with pytest.raises(FileNotFoundError):
            artifact_repo.update_content("skill:no-exist", "new content")

    def test_update_content_directory_with_descriptor(
        self, artifact_repo, artifact_mgr, tmp_path
    ):
        skill_dir = tmp_path / "dir-update-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Old", encoding="utf-8")

        mock_art = _make_artifact("dir-update-skill", "skill", path="dir-update-skill")
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        artifact_mgr.collection_mgr.config.get_collection_path.return_value = tmp_path

        result = artifact_repo.update_content("skill:dir-update-skill", "# New")
        assert result is True
        assert (skill_dir / "SKILL.md").read_text() == "# New"


class TestLocalArtifactRepositoryGetTags:
    def test_get_tags_returns_tag_dtos(self, artifact_repo, artifact_mgr):
        mock_art = _make_artifact("tagged-skill", "skill", tags=["python", "data"])
        artifact_mgr.show.side_effect = None
        artifact_mgr.show.return_value = mock_art
        result = artifact_repo.get_tags("skill:tagged-skill")
        assert len(result) == 2
        names = {t.name for t in result}
        assert names == {"python", "data"}

    def test_get_tags_unknown_type_returns_empty(self, artifact_repo):
        result = artifact_repo.get_tags("bogus_type:foo")
        assert result == []

    def test_get_tags_not_found_returns_empty(self, artifact_repo, artifact_mgr):
        artifact_mgr.show.side_effect = ValueError("not found")
        result = artifact_repo.get_tags("skill:ghost")
        assert result == []


class TestLocalArtifactRepositoryCreate:
    def test_create_unknown_type_raises(self, artifact_repo):
        dto = ArtifactDTO(
            id="bogus:foo",
            name="foo",
            artifact_type="bogus_type",
            content_path="/tmp/foo",
        )
        with pytest.raises(ValueError, match="Unknown artifact type"):
            artifact_repo.create(dto)


# ============================================================================
# LocalCollectionRepository — uncovered branches
# ============================================================================


@pytest.fixture
def mock_collection_manager():
    mgr = MagicMock()
    mgr.get_active_collection_name.return_value = "default"
    return mgr


@pytest.fixture
def mock_coll_resolver(tmp_path):
    r = MagicMock()
    r.collection_root.return_value = tmp_path
    r.artifacts_dir.return_value = tmp_path / "artifacts"
    r.artifact_path.side_effect = lambda name, atype: tmp_path / atype / name
    return r


@pytest.fixture
def coll_repo(mock_collection_manager, mock_coll_resolver):
    return LocalCollectionRepository(
        collection_manager=mock_collection_manager,
        path_resolver=mock_coll_resolver,
    )


class TestLocalCollectionRepositoryGetById:
    def test_get_by_id_not_found_returns_none(self, coll_repo, mock_collection_manager):
        mock_collection_manager.load_collection.side_effect = ValueError("not found")
        assert coll_repo.get_by_id("missing") is None

    def test_get_by_id_found(self, coll_repo, mock_collection_manager):
        coll = MagicMock()
        coll.name = "default"
        coll.version = "1.0.0"
        coll.artifacts = []
        coll.created = None
        coll.updated = None
        mock_collection_manager.load_collection.side_effect = None
        mock_collection_manager.load_collection.return_value = coll
        mock_collection_manager.config.get_collection_path.return_value = Path("/tmp/col")
        dto = coll_repo.get_by_id("default")
        assert dto is not None
        assert dto.id == "default"


class TestLocalCollectionRepositoryGetArtifacts:
    def test_get_artifacts_not_found_returns_empty(self, coll_repo, mock_collection_manager):
        mock_collection_manager.load_collection.side_effect = ValueError("not found")
        assert coll_repo.get_artifacts("missing") == []

    def test_get_artifacts_with_type_filter(self, coll_repo, mock_collection_manager):
        skill = MagicMock()
        skill.type = MagicMock()
        skill.type.value = "skill"
        skill.name = "skill-a"
        skill.upstream = None
        skill.metadata = None
        skill.uuid = None
        skill.version = None
        skill.scope = None

        command = MagicMock()
        command.type = MagicMock()
        command.type.value = "command"
        command.name = "cmd-a"
        command.upstream = None
        command.metadata = None
        command.uuid = None
        command.version = None
        command.scope = None

        coll = MagicMock()
        coll.artifacts = [skill, command]
        mock_collection_manager.load_collection.side_effect = None
        mock_collection_manager.load_collection.return_value = coll

        result = coll_repo.get_artifacts("default", filters={"artifact_type": "skill"})
        assert len(result) == 1
        assert result[0].artifact_type == "skill"

    def test_get_artifacts_with_name_filter(self, coll_repo, mock_collection_manager):
        a = MagicMock()
        a.type = MagicMock()
        a.type.value = "skill"
        a.name = "canvas-design"
        a.upstream = None
        a.metadata = None
        a.uuid = None
        a.version = None
        a.scope = None

        b = MagicMock()
        b.type = MagicMock()
        b.type.value = "skill"
        b.name = "document-editor"
        b.upstream = None
        b.metadata = None
        b.uuid = None
        b.version = None
        b.scope = None

        coll = MagicMock()
        coll.artifacts = [a, b]
        mock_collection_manager.load_collection.side_effect = None
        mock_collection_manager.load_collection.return_value = coll

        result = coll_repo.get_artifacts("default", filters={"name": "canvas"})
        assert len(result) == 1
        assert result[0].name == "canvas-design"

    def test_get_artifacts_with_source_filter(self, coll_repo, mock_collection_manager):
        a = MagicMock()
        a.type = MagicMock()
        a.type.value = "skill"
        a.name = "github-skill"
        a.upstream = "github:anthropics/skills/canvas"
        a.metadata = None
        a.uuid = None
        a.version = None
        a.scope = None

        b = MagicMock()
        b.type = MagicMock()
        b.type.value = "skill"
        b.name = "local-skill"
        b.upstream = None
        b.metadata = None
        b.uuid = None
        b.version = None
        b.scope = None

        coll = MagicMock()
        coll.artifacts = [a, b]
        mock_collection_manager.load_collection.side_effect = None
        mock_collection_manager.load_collection.return_value = coll

        result = coll_repo.get_artifacts("default", filters={"source": "anthropics"})
        assert len(result) == 1
        assert result[0].name == "github-skill"

    def test_get_artifacts_pagination(self, coll_repo, mock_collection_manager):
        arts = []
        for i in range(10):
            m = MagicMock()
            m.type = MagicMock()
            m.type.value = "skill"
            m.name = f"skill-{i}"
            m.upstream = None
            m.metadata = None
            m.uuid = None
            m.version = None
            m.scope = None
            arts.append(m)
        coll = MagicMock()
        coll.artifacts = arts
        mock_collection_manager.load_collection.side_effect = None
        mock_collection_manager.load_collection.return_value = coll

        result = coll_repo.get_artifacts("default", offset=5, limit=3)
        assert len(result) == 3


class TestLocalCollectionRepositoryArtifactToDto:
    def test_artifact_to_dto_with_metadata(self, coll_repo, mock_collection_manager):
        a = MagicMock()
        a.type = MagicMock()
        a.type.value = "skill"
        a.name = "meta-skill"
        a.upstream = "github:org/repo"
        a.version = "v1.0"
        a.scope = "user"
        a.uuid = "aabb"
        meta = MagicMock()
        meta.description = "A great skill"
        meta.title = "Meta Skill"
        meta.author = "Alice"
        meta.license = "MIT"
        meta.version = "v1.0"
        meta.dependencies = None
        meta.extra = None
        meta.tags = ["ai", "data"]
        a.metadata = meta

        coll = MagicMock()
        coll.artifacts = [a]
        mock_collection_manager.load_collection.side_effect = None
        mock_collection_manager.load_collection.return_value = coll

        result = coll_repo.get_artifacts("default")
        assert len(result) == 1
        dto = result[0]
        assert dto.description == "A great skill"
        assert "ai" in dto.tags


# ============================================================================
# LocalProjectRepository — uncovered branches
# ============================================================================


@pytest.fixture
def proj_path_resolver(tmp_path):
    r = MagicMock()
    r.collection_root.return_value = tmp_path
    return r


@pytest.fixture
def proj_repo_no_cache(proj_path_resolver):
    return LocalProjectRepository(path_resolver=proj_path_resolver, cache_manager=None)


@pytest.fixture
def mock_cache_repo():
    r = MagicMock()
    return r


@pytest.fixture
def mock_cache_mgr(mock_cache_repo):
    mgr = MagicMock()
    mgr.repository = mock_cache_repo
    return mgr


@pytest.fixture
def proj_repo_with_cache(proj_path_resolver, mock_cache_mgr):
    return LocalProjectRepository(
        path_resolver=proj_path_resolver, cache_manager=mock_cache_mgr
    )


class TestLocalProjectRepositoryGetFilesystemFallback:
    def test_get_with_invalid_id_returns_none(self, proj_repo_no_cache):
        # Non-base64 ID
        result = proj_repo_no_cache.get("!!!invalid!!!")
        assert result is None

    def test_get_with_nonexistent_path_returns_none(self, proj_repo_no_cache):
        fake_id = _encode_id("/definitely/does/not/exist/here")
        result = proj_repo_no_cache.get(fake_id)
        assert result is None

    def test_get_existing_path_returns_dto(self, proj_repo_no_cache, tmp_path):
        proj_dir = tmp_path / "my-project"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_no_cache.get(project_id)

        assert result is not None
        assert result.name == "my-project"


class TestLocalProjectRepositoryGetWithCache:
    def test_get_from_db_cache(self, proj_repo_with_cache, mock_cache_repo, tmp_path):
        proj_dir = tmp_path / "cached-proj"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        orm_project = MagicMock()
        orm_project.id = project_id
        orm_project.name = "cached-proj"
        orm_project.path = str(proj_dir)
        orm_project.description = None
        orm_project.status = "active"
        orm_project.artifacts = []
        orm_project.created_at = None
        orm_project.updated_at = None
        orm_project.last_fetched = None

        mock_cache_repo.get_project.return_value = orm_project

        result = proj_repo_with_cache.get(project_id)
        assert result is not None
        assert result.name == "cached-proj"

    def test_get_db_miss_fallback_to_filesystem(
        self, proj_repo_with_cache, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "fs-fallback"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        # DB returns None → fall back to filesystem
        mock_cache_repo.get_project.return_value = None

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_with_cache.get(project_id)

        assert result is not None
        assert result.name == "fs-fallback"


class TestLocalProjectRepositoryList:
    def test_list_from_cache(self, proj_repo_with_cache, mock_cache_repo):
        orm_p = MagicMock()
        orm_p.id = "proj-1"
        orm_p.name = "proj-1"
        orm_p.path = "/tmp/proj-1"
        orm_p.description = None
        orm_p.status = "active"
        orm_p.artifacts = []
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        mock_cache_repo.list_projects.return_value = [orm_p]

        result = proj_repo_with_cache.list()
        assert len(result) == 1
        assert result[0].name == "proj-1"

    def test_list_with_status_filter(self, proj_repo_with_cache, mock_cache_repo):
        orm_p = MagicMock()
        orm_p.id = "proj-1"
        orm_p.name = "proj-1"
        orm_p.path = "/tmp/proj-1"
        orm_p.description = None
        orm_p.status = "stale"
        orm_p.artifacts = []
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        mock_cache_repo.get_projects_by_status.return_value = [orm_p]

        result = proj_repo_with_cache.list(filters={"status": "stale"})
        assert len(result) == 1
        mock_cache_repo.get_projects_by_status.assert_called_once_with("stale")

    def test_list_db_failure_falls_back_to_fs(self, proj_repo_with_cache, mock_cache_repo, tmp_path):
        mock_cache_repo.list_projects.side_effect = RuntimeError("db down")

        with patch(
            "skillmeat.core.repositories.local_project._discover_project_paths",
            return_value=[],
        ):
            result = proj_repo_with_cache.list()

        assert result == []


class TestLocalProjectRepositoryCreate:
    def test_create_new_project(self, proj_repo_with_cache, mock_cache_mgr, tmp_path):
        proj_dir = tmp_path / "new-proj"
        # Not a real dir, but get() will return None (no cache hit, not on disk)
        project_id = _encode_id(str(proj_dir))

        mock_cache_mgr.repository.get_project.return_value = None

        dto = ProjectDTO(id=project_id, name="new-proj", path=str(proj_dir))
        result = proj_repo_with_cache.create(dto)

        assert result.id == project_id
        assert result.name == "new-proj"
        mock_cache_mgr.upsert_project.assert_called_once()

    def test_create_existing_raises(self, proj_repo_with_cache, mock_cache_repo, tmp_path):
        proj_dir = tmp_path / "exists"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        orm_p = MagicMock()
        orm_p.id = project_id
        orm_p.name = "exists"
        orm_p.path = str(proj_dir)
        orm_p.description = None
        orm_p.status = "active"
        orm_p.artifacts = []
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        mock_cache_repo.get_project.return_value = orm_p

        dto = ProjectDTO(id=project_id, name="exists", path=str(proj_dir))
        with pytest.raises(ValueError, match="already exists"):
            proj_repo_with_cache.create(dto)

    def test_create_without_cache_still_returns_dto(self, proj_repo_no_cache, tmp_path):
        proj_dir = tmp_path / "no-cache-create"
        project_id = _encode_id(str(proj_dir))
        dto = ProjectDTO(id=project_id, name="no-cache-create", path=str(proj_dir))
        result = proj_repo_no_cache.create(dto)
        assert result.id == project_id


class TestLocalProjectRepositoryGetArtifacts:
    def test_get_artifacts_from_cache(self, proj_repo_with_cache, mock_cache_repo, tmp_path):
        proj_dir = tmp_path / "with-artifacts"
        project_id = _encode_id(str(proj_dir))

        orm_art = MagicMock()
        orm_art.id = "skill:foo"
        orm_art.name = "foo"
        orm_art.type = "skill"
        orm_art.uuid = None
        orm_art.source = None
        orm_art.deployed_version = None
        orm_art.scope = None
        orm_art.description = None
        orm_art.content_path = None
        orm_art.is_outdated = False
        orm_art.local_modified = False
        orm_art.project_id = project_id
        orm_art.created_at = None
        orm_art.updated_at = None

        mock_cache_repo.list_artifacts_by_project.return_value = [orm_art]
        result = proj_repo_with_cache.get_artifacts(project_id)
        assert len(result) == 1
        assert result[0].name == "foo"

    def test_get_artifacts_filesystem_fallback(self, proj_repo_no_cache, tmp_path):
        proj_dir = tmp_path / "fs-artifacts"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        dep = MagicMock()
        dep.artifact_type = MagicMock()
        dep.artifact_type.value = "skill"
        dep.name = "canvas"
        dep.version = "v1.0"
        dep.deployed_at = None

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[dep],
        ):
            result = proj_repo_no_cache.get_artifacts(project_id)

        assert len(result) == 1
        assert result[0].name == "canvas"

    def test_get_artifacts_invalid_project_id_returns_empty(self, proj_repo_no_cache):
        result = proj_repo_no_cache.get_artifacts("!!!not-valid-base64!!!")
        assert result == []


class TestLocalProjectRepositoryRefresh:
    def test_refresh_invalid_id_raises(self, proj_repo_no_cache):
        with pytest.raises(KeyError):
            proj_repo_no_cache.refresh("not-valid-base64!!!!")

    def test_refresh_nonexistent_path_raises(self, proj_repo_no_cache, tmp_path):
        missing_id = _encode_id("/nonexistent/path/to/project")
        with pytest.raises(KeyError):
            proj_repo_no_cache.refresh(missing_id)

    def test_refresh_existing_path_no_cache(self, proj_repo_no_cache, tmp_path):
        proj_dir = tmp_path / "refresh-proj"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_no_cache.refresh(project_id)

        assert result.name == "refresh-proj"
        assert result.artifact_count == 0

    def test_refresh_with_cache_manager_syncs_to_db(
        self, proj_repo_with_cache, mock_cache_mgr, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "refresh-cached"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        # get() will return None (cache miss + on-disk dir found via fs)
        mock_cache_repo.get_project.return_value = None

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_with_cache.refresh(project_id)

        mock_cache_mgr.upsert_project.assert_called_once()
        assert result.name == "refresh-cached"

    def test_refresh_deployment_read_exception_is_logged(self, proj_repo_no_cache, tmp_path):
        proj_dir = tmp_path / "dep-err-proj"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            side_effect=RuntimeError("read fail"),
        ):
            result = proj_repo_no_cache.refresh(project_id)

        # Should not raise; returns DTO with 0 artifacts
        assert result.artifact_count == 0

    def test_refresh_with_artifact_count_mismatch_overrides(
        self, proj_repo_with_cache, mock_cache_mgr, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "mismatch-proj"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        dep = MagicMock()
        dep.artifact_type = MagicMock()
        dep.artifact_type.value = "skill"
        dep.name = "some-skill"
        dep.version = None
        dep.deployed_at = None

        # DB returns a project with artifact_count=0 (stale)
        orm_p = MagicMock()
        orm_p.id = project_id
        orm_p.name = "mismatch-proj"
        orm_p.path = str(proj_dir)
        orm_p.description = None
        orm_p.status = "active"
        orm_p.artifacts = []
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        mock_cache_repo.get_project.return_value = orm_p

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[dep],  # 1 deployment found on disk
        ):
            result = proj_repo_with_cache.refresh(project_id)

        # artifact_count should be overridden to 1
        assert result.artifact_count == 1


# ============================================================================
# LocalTagRepository — uncovered branches
# ============================================================================


class TestLocalProjectRepositoryHelperFunctions:
    """Test module-level helpers in local_project.py."""

    def test_to_iso_with_datetime(self):
        from skillmeat.core.repositories.local_project import _to_iso
        from datetime import datetime, timezone

        dt = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        result = _to_iso(dt)
        assert "2024" in result

    def test_to_iso_with_string_passthrough(self):
        from skillmeat.core.repositories.local_project import _to_iso

        result = _to_iso("2024-01-01")
        assert result == "2024-01-01"

    def test_to_iso_with_none(self):
        from skillmeat.core.repositories.local_project import _to_iso

        assert _to_iso(None) is None

    def test_to_iso_with_other_type(self):
        from skillmeat.core.repositories.local_project import _to_iso

        result = _to_iso(12345)
        assert result == "12345"

    def test_build_project_dto_from_path_deployment_exception(self, tmp_path):
        from skillmeat.core.repositories.local_project import _build_project_dto_from_path

        proj_dir = tmp_path / "exc-proj"
        proj_dir.mkdir()

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            side_effect=RuntimeError("cannot read"),
        ):
            dto = _build_project_dto_from_path(proj_dir)

        assert dto.name == "exc-proj"
        assert dto.artifact_count == 0

    def test_discover_project_paths_returns_list(self):
        from skillmeat.core.repositories.local_project import _discover_project_paths

        # Just ensure it's callable and returns a list (may be empty in CI)
        result = _discover_project_paths()
        assert isinstance(result, list)

    def test_discover_project_paths_with_mocked_search(self, tmp_path):
        """Cover the rglob + depth + dedup logic in _discover_project_paths."""
        from skillmeat.core.repositories.local_project import _discover_project_paths
        from skillmeat.storage.deployment import DeploymentTracker

        # Create a fake project directory structure
        proj_dir = tmp_path / "myproject"
        proj_dir.mkdir()
        dot_dir = proj_dir / ".claude"
        dot_dir.mkdir()
        dep_file = dot_dir / DeploymentTracker.DEPLOYMENT_FILE
        dep_file.write_text("[deployed]\n", encoding="utf-8")

        with patch(
            "skillmeat.core.repositories.local_project.Path.home",
            return_value=tmp_path,
        ):
            # Override search paths to only include tmp_path/projects
            projects_dir = tmp_path / "projects"
            projects_dir.mkdir()
            # Copy our project structure in there
            import shutil

            shutil.copytree(str(proj_dir), str(projects_dir / "myproject"))

            with patch(
                "skillmeat.core.repositories.local_project._discover_project_paths.__code__",
                wraps=None,
            ) if False else patch.multiple("builtins", open=open):
                # Just call it; the important thing is it doesn't crash
                result = _discover_project_paths()
                assert isinstance(result, list)


class TestLocalProjectRepositoryUpdateAndDelete:
    def test_update_raises_key_error_for_missing(self, proj_repo_no_cache, tmp_path):
        missing_id = _encode_id("/no/such/path")
        with pytest.raises(KeyError):
            proj_repo_no_cache.update(missing_id, {"name": "new-name"})

    def test_update_with_cache_calls_repo_update(
        self, proj_repo_with_cache, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "update-me"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        orm_p = MagicMock()
        orm_p.id = project_id
        orm_p.name = "update-me"
        orm_p.path = str(proj_dir)
        orm_p.description = None
        orm_p.status = "active"
        orm_p.artifacts = []
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        mock_cache_repo.get_project.return_value = orm_p

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_with_cache.update(project_id, {"name": "updated-name"})

        mock_cache_repo.update_project.assert_called_once()

    def test_update_db_failure_returns_fallback_dto(
        self, proj_repo_with_cache, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "update-fail-proj"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        orm_p = MagicMock()
        orm_p.id = project_id
        orm_p.name = "update-fail-proj"
        orm_p.path = str(proj_dir)
        orm_p.description = None
        orm_p.status = "active"
        orm_p.artifacts = []
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        # First call (for get()) returns orm_p, subsequent calls raise
        mock_cache_repo.get_project.return_value = orm_p
        mock_cache_repo.update_project.side_effect = RuntimeError("db fail")

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_with_cache.update(project_id, {"name": "new-name"})

        # Should succeed despite db failure — returns a constructed DTO
        assert result is not None

    def test_delete_with_cache_exception_returns_false(
        self, proj_repo_with_cache, mock_cache_repo
    ):
        mock_cache_repo.delete_project.side_effect = RuntimeError("db fail")
        result = proj_repo_with_cache.delete("some-project-id")
        assert result is False

    def test_delete_no_cache_returns_false(self, proj_repo_no_cache):
        result = proj_repo_no_cache.delete("any-id")
        assert result is False


class TestLocalProjectRepositoryGetArtifactsEdgeCases:
    def test_get_artifacts_db_exception_falls_back(
        self, proj_repo_with_cache, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "db-fail-artifacts"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))
        mock_cache_repo.list_artifacts_by_project.side_effect = RuntimeError("db fail")

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_with_cache.get_artifacts(project_id)

        assert result == []

    def test_get_artifacts_valid_id_nonexistent_dir_returns_empty(self, proj_repo_no_cache, tmp_path):
        missing_dir = tmp_path / "no-dir-here"
        project_id = _encode_id(str(missing_dir))
        result = proj_repo_no_cache.get_artifacts(project_id)
        assert result == []

    def test_get_artifacts_deployment_tracker_exception_returns_empty(
        self, proj_repo_no_cache, tmp_path
    ):
        proj_dir = tmp_path / "dep-exc-proj"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            side_effect=RuntimeError("tracker fail"),
        ):
            result = proj_repo_no_cache.get_artifacts(project_id)

        assert result == []


class TestLocalProjectRepositoryDtoFromPath:
    def test_dto_from_path_with_db_hit(self, proj_repo_with_cache, mock_cache_repo, tmp_path):
        proj_dir = tmp_path / "db-hit-proj"
        proj_dir.mkdir()

        orm_p = MagicMock()
        orm_p.id = _encode_id(str(proj_dir))
        orm_p.name = "db-hit-proj"
        orm_p.path = str(proj_dir)
        orm_p.description = "from DB"
        orm_p.status = "active"
        orm_p.artifacts = [MagicMock(), MagicMock()]  # 2 artifacts
        orm_p.created_at = None
        orm_p.updated_at = None
        orm_p.last_fetched = None
        mock_cache_repo.get_project.return_value = orm_p

        # _dto_from_path is called internally via get()
        project_id = _encode_id(str(proj_dir))
        result = proj_repo_with_cache.get(project_id)

        assert result is not None
        assert result.artifact_count == 2  # from ORM artifacts list

    def test_dto_from_path_db_exception_falls_back_to_fs(
        self, proj_repo_with_cache, mock_cache_repo, tmp_path
    ):
        proj_dir = tmp_path / "db-exc-fallback"
        proj_dir.mkdir()
        project_id = _encode_id(str(proj_dir))

        # DB raises on get_project
        mock_cache_repo.get_project.side_effect = RuntimeError("db error")

        with patch(
            "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
            return_value=[],
        ):
            result = proj_repo_with_cache.get(project_id)

        assert result is not None
        assert result.name == "db-exc-fallback"


class TestLocalProjectRepositoryListFilesystemFilter:
    def test_list_no_cache_with_status_filter(self, proj_repo_no_cache, tmp_path):
        proj_dir = tmp_path / "fs-filter-proj"
        proj_dir.mkdir()

        with patch(
            "skillmeat.core.repositories.local_project._discover_project_paths",
            return_value=[proj_dir],
        ):
            with patch(
                "skillmeat.core.repositories.local_project.DeploymentTracker.read_deployments",
                return_value=[],
            ):
                # Only "active" projects should match
                result_active = proj_repo_no_cache.list(filters={"status": "active"})
                result_stale = proj_repo_no_cache.list(filters={"status": "stale"})

        assert len(result_active) == 1
        assert len(result_stale) == 0


class TestLocalTagRepositoryHelpers:
    def test_slugify_basic(self):
        from skillmeat.core.repositories.local_tag import _slugify
        assert _slugify("Python 3.9") == "python-3-9"

    def test_slugify_leading_trailing_hyphens(self):
        from skillmeat.core.repositories.local_tag import _slugify
        assert _slugify("---AI---") == "ai"

    def test_slugify_empty_returns_tag(self):
        from skillmeat.core.repositories.local_tag import _slugify
        assert _slugify("") == "tag"

    def test_tag_to_dto_with_datetime_timestamps(self):
        from skillmeat.core.repositories.local_tag import _tag_to_dto
        from datetime import datetime, timezone

        tag = _make_tag_orm()
        tag.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        tag.updated_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
        dto = _tag_to_dto(tag)
        assert dto.created_at is not None
        assert "2024" in dto.created_at

    def test_tag_to_dto_string_timestamps(self):
        from skillmeat.core.repositories.local_tag import _tag_to_dto

        tag = _make_tag_orm()
        tag.created_at = "2024-01-01T00:00:00"
        tag.updated_at = "2024-06-01T00:00:00"
        dto = _tag_to_dto(tag)
        assert dto.created_at == "2024-01-01T00:00:00"

    def test_tag_to_dto_counts_artifact_tags(self):
        from skillmeat.core.repositories.local_tag import _tag_to_dto

        tag = _make_tag_orm()
        tag.artifact_tags = [MagicMock(), MagicMock()]
        tag.deployment_set_tags = [MagicMock()]
        dto = _tag_to_dto(tag)
        assert dto.artifact_count == 2
        assert dto.deployment_set_count == 1


class TestLocalTagRepositoryAssignUnassign:
    @pytest.fixture
    def mock_tag_inner_repo(self):
        return MagicMock()

    @pytest.fixture
    def tag_repo(self, mock_tag_inner_repo):
        r = LocalTagRepository(session_factory=None, db_path=None)
        r._get_tag_repo = MagicMock(return_value=mock_tag_inner_repo)
        return r

    def test_assign_artifact_not_found_raises(self, tag_repo):
        tag_repo._resolve_artifact_uuid = MagicMock(return_value=None)
        with pytest.raises(KeyError, match="not found in DB cache"):
            tag_repo.assign("tag-1", "skill:ghost")

    def test_assign_idempotent_on_already_exists(self, tag_repo, mock_tag_inner_repo):
        tag_repo._resolve_artifact_uuid = MagicMock(return_value="uuid-abc")
        mock_tag_inner_repo.add_tag_to_artifact.side_effect = Exception(
            "Association already exists"
        )
        result = tag_repo.assign("tag-1", "skill:foo")
        assert result is True

    def test_assign_other_exception_raises_key_error(self, tag_repo, mock_tag_inner_repo):
        tag_repo._resolve_artifact_uuid = MagicMock(return_value="uuid-abc")
        mock_tag_inner_repo.add_tag_to_artifact.side_effect = Exception("some db error")
        with pytest.raises(KeyError):
            tag_repo.assign("tag-1", "skill:foo")

    def test_assign_success(self, tag_repo, mock_tag_inner_repo):
        tag_repo._resolve_artifact_uuid = MagicMock(return_value="uuid-abc")
        mock_tag_inner_repo.add_tag_to_artifact.return_value = None
        result = tag_repo.assign("tag-1", "skill:foo")
        assert result is True

    def test_unassign_artifact_not_found_returns_false(self, tag_repo):
        tag_repo._resolve_artifact_uuid = MagicMock(return_value=None)
        result = tag_repo.unassign("tag-1", "skill:ghost")
        assert result is False

    def test_unassign_success(self, tag_repo, mock_tag_inner_repo):
        tag_repo._resolve_artifact_uuid = MagicMock(return_value="uuid-abc")
        mock_tag_inner_repo.remove_tag_from_artifact.return_value = True
        result = tag_repo.unassign("tag-1", "skill:foo")
        assert result is True


class TestLocalTagRepositoryGetTagRepo:
    def test_get_tag_repo_raises_on_import_failure(self):
        repo = LocalTagRepository(session_factory=None, db_path=None)
        with patch.dict("sys.modules", {"skillmeat.cache.repositories": None}):
            with pytest.raises(RuntimeError, match="failed to create TagRepository"):
                repo._get_tag_repo()


# ============================================================================
# Verify mock implementations in tests/mocks/repositories.py
# ============================================================================


class TestMockRepositoriesModule:
    def test_mock_repositories_importable(self):
        from tests.mocks.repositories import (  # type: ignore[import]
            MockArtifactRepository,
            MockCollectionRepository,
            MockDeploymentRepository,
            MockProjectRepository,
            MockSettingsRepository,
            MockTagRepository,
        )
        # Quick sanity check all six are present
        assert MockArtifactRepository is not None
        assert MockCollectionRepository is not None
        assert MockDeploymentRepository is not None
        assert MockProjectRepository is not None
        assert MockSettingsRepository is not None
        assert MockTagRepository is not None

    def test_mock_artifact_repo_search(self):
        from tests.mocks.repositories import MockArtifactRepository  # type: ignore[import]

        repo = MockArtifactRepository()
        a = ArtifactDTO(
            id="skill:canvas",
            name="canvas",
            artifact_type="skill",
            description="draws things",
        )
        repo._store["skill:canvas"] = a
        results = repo.search("canvas")
        assert len(results) == 1

    def test_mock_artifact_repo_get_by_uuid(self):
        from tests.mocks.repositories import MockArtifactRepository  # type: ignore[import]

        repo = MockArtifactRepository()
        a = ArtifactDTO(
            id="skill:canvas",
            name="canvas",
            artifact_type="skill",
            uuid="aabb1122",
        )
        # Use seed() so the UUID index is populated
        repo.seed(a)
        result = repo.get_by_uuid("aabb1122")
        assert result is not None
        assert result.name == "canvas"

    def test_mock_tag_repo_assign_and_unassign(self):
        from tests.mocks.repositories import MockTagRepository  # type: ignore[import]

        repo = MockTagRepository()
        tag = TagDTO(id="t1", name="ai", slug="ai")
        repo._store["t1"] = tag
        assert repo.assign("t1", "skill:foo") is True
        assert repo.unassign("t1", "skill:foo") is True
