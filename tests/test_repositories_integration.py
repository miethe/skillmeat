"""Integration tests for write-through invariant across all 6 local repositories.

These tests verify that after any mutation the relevant downstream state
(DB cache refresh, TOML config file, SQLite DB rows) is consistent with
the operation that was performed.  All external collaborators (managers,
sessions, cache services) are mocked so the tests remain fast and portable —
no real filesystem collection or live database is needed.

Test classes
------------
TestLocalArtifactRepositoryWriteThrough
    Verify that ``refresh_single_artifact_cache`` is called after every
    mutation and that the artifact manager receives the right arguments.

TestLocalProjectRepositoryWriteThrough
    Verify that the cache manager's ``upsert_project`` / ``delete_project``
    methods are called on create/update/delete, and that the repository
    falls back to filesystem discovery when no cache is available.

TestLocalCollectionRepositoryWriteThrough
    Verify that the collection manager is called on ``refresh()`` and that
    stats / artifact listing delegate correctly.

TestLocalDeploymentRepositoryWriteThrough
    Verify that ``deploy_artifacts`` and ``undeploy`` are delegated to the
    deployment manager and that the resulting DTOs carry the expected fields.

TestLocalTagRepositoryWriteThrough
    Verify that the underlying cache-layer ``TagRepository`` is called on
    every mutation and that DB rows are properly created/updated/deleted.

TestLocalSettingsRepositoryWriteThrough
    Verify that TOML config keys are written on ``update()`` and that
    ``get()`` reflects the latest values.

Run with::

    pytest tests/test_repositories_integration.py -v
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

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
    LocalDeploymentRepository,
    LocalProjectRepository,
    LocalSettingsRepository,
    LocalTagRepository,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_project_id(path: str) -> str:
    return base64.b64encode(path.encode()).decode()


def _make_mock_artifact(name: str = "my-skill", artifact_type: str = "skill") -> MagicMock:
    """Return a minimal mock that quacks like a core Artifact domain object."""
    mock = MagicMock()
    mock.name = name
    mock.type = MagicMock()
    mock.type.value = artifact_type
    mock.tags = []
    mock.metadata = MagicMock()
    mock.metadata.description = "A test skill"
    mock.metadata.tags = []
    mock.metadata.to_dict.return_value = {"description": "A test skill"}
    mock.upstream = None
    mock.path = f"{artifact_type}s/{name}"
    mock.uuid = "aaaa1111bbbb2222cccc3333dddd4444"
    mock.added = None
    mock.last_updated = None
    mock.resolved_version = "v1.0.0"
    mock.version_spec = "latest"
    return mock


def _make_mock_tag_orm(
    tag_id: str = "tag-1",
    name: str = "ai",
    slug: str = "ai",
    color: str | None = None,
) -> MagicMock:
    """Return a minimal mock that quacks like a cache-layer Tag ORM object."""
    mock = MagicMock()
    mock.id = tag_id
    mock.name = name
    mock.slug = slug
    mock.color = color
    mock.artifact_tags = []
    mock.deployment_set_tags = []
    mock.created_at = None
    mock.updated_at = None
    return mock


# =============================================================================
# LocalArtifactRepository — write-through tests
# =============================================================================


class TestLocalArtifactRepositoryWriteThrough:
    """Verify FS + DB cache consistency after create / update / delete."""

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    @pytest.fixture
    def mock_artifact_manager(self):
        """Return a mocked ArtifactManager."""
        mgr = MagicMock()
        # make show() raise ValueError by default (not found)
        mgr.show.side_effect = ValueError("not found")
        return mgr

    @pytest.fixture
    def mock_path_resolver(self, tmp_path):
        """Return a mocked ProjectPathResolver."""
        resolver = MagicMock()
        resolver.collection_root.return_value = tmp_path
        return resolver

    @pytest.fixture
    def mock_refresh_fn(self):
        """Return a mock for the refresh_single_artifact_cache callable."""
        return MagicMock(return_value=True)

    @pytest.fixture
    def mock_db_session(self):
        """Return a mock SQLAlchemy session."""
        return MagicMock()

    @pytest.fixture
    def repo(
        self,
        mock_artifact_manager,
        mock_path_resolver,
        mock_refresh_fn,
        mock_db_session,
    ):
        """Construct a LocalArtifactRepository with all deps mocked."""
        return LocalArtifactRepository(
            artifact_manager=mock_artifact_manager,
            path_resolver=mock_path_resolver,
            db_session=mock_db_session,
            refresh_fn=mock_refresh_fn,
        )

    # ------------------------------------------------------------------
    # create() — cache refresh called
    # ------------------------------------------------------------------

    def test_create_calls_cache_refresh(
        self,
        tmp_path,
        repo,
        mock_artifact_manager,
        mock_refresh_fn,
        mock_db_session,
    ):
        """After create(), refresh_single_artifact_cache must be called once."""
        # Arrange: a minimal source file on disk
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# My Skill", encoding="utf-8")

        mock_artifact = _make_mock_artifact("my-skill", "skill")
        mock_artifact_manager.add_from_local.return_value = mock_artifact

        dto = ArtifactDTO(
            id="skill:my-skill",
            name="my-skill",
            artifact_type="skill",
            content_path=str(skill_dir),
        )

        # Act
        result = repo.create(dto)

        # Assert: manager was called
        mock_artifact_manager.add_from_local.assert_called_once()

        # Assert: cache refresh was triggered with correct args
        mock_refresh_fn.assert_called_once_with(
            session=mock_db_session,
            artifact_mgr=mock_artifact_manager,
            artifact_id="skill:my-skill",
        )

        assert result.name == "my-skill"
        assert result.artifact_type == "skill"

    def test_create_without_content_path_raises(self, repo):
        """create() without content_path must raise ValueError immediately."""
        dto = ArtifactDTO(
            id="skill:no-path",
            name="no-path",
            artifact_type="skill",
        )
        with pytest.raises(ValueError, match="content_path is required"):
            repo.create(dto)

    def test_create_no_cache_refresh_when_no_session(
        self, mock_artifact_manager, mock_path_resolver, mock_refresh_fn, tmp_path
    ):
        """create() must not call the refresh function when db_session is None."""
        skill_dir = tmp_path / "no-session-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill", encoding="utf-8")

        mock_artifact = _make_mock_artifact("no-session-skill", "skill")
        mock_artifact_manager.add_from_local.return_value = mock_artifact

        repo_no_session = LocalArtifactRepository(
            artifact_manager=mock_artifact_manager,
            path_resolver=mock_path_resolver,
            db_session=None,
            refresh_fn=mock_refresh_fn,
        )

        dto = ArtifactDTO(
            id="skill:no-session-skill",
            name="no-session-skill",
            artifact_type="skill",
            content_path=str(skill_dir),
        )
        repo_no_session.create(dto)

        mock_refresh_fn.assert_not_called()

    # ------------------------------------------------------------------
    # update() — tag mutation triggers cache refresh
    # ------------------------------------------------------------------

    def test_update_tags_calls_cache_refresh(
        self, repo, mock_artifact_manager, mock_refresh_fn, mock_db_session
    ):
        """After update() with tag changes, cache refresh must be called."""
        mock_artifact = _make_mock_artifact("my-skill", "skill")
        mock_artifact_manager.show.side_effect = None
        mock_artifact_manager.show.return_value = mock_artifact

        # Arrange collection manager for the manifest save
        mock_collection = MagicMock()
        mock_artifact_manager.collection_mgr.load_collection.return_value = mock_collection

        # After refresh, get() should return the updated artifact
        mock_artifact_manager.show.return_value = mock_artifact

        result = repo.update("skill:my-skill", updates={"tags": ["ai", "testing"]})

        mock_refresh_fn.assert_called_once_with(
            session=mock_db_session,
            artifact_mgr=mock_artifact_manager,
            artifact_id="skill:my-skill",
        )

    def test_update_unknown_artifact_raises(self, repo, mock_artifact_manager):
        """update() on a non-existent artifact must raise KeyError."""
        mock_artifact_manager.show.side_effect = ValueError("not found")

        with pytest.raises(KeyError):
            repo.update("skill:ghost", updates={"tags": ["new"]})

    # ------------------------------------------------------------------
    # delete() — no cache refresh (artifact removed)
    # ------------------------------------------------------------------

    def test_delete_existing_artifact_returns_true(
        self, repo, mock_artifact_manager
    ):
        """delete() on an existing artifact should return True and call remove()."""
        from skillmeat.core.artifact import ArtifactType

        mock_artifact = _make_mock_artifact("my-skill", "skill")
        mock_artifact_manager.show.side_effect = None
        mock_artifact_manager.show.return_value = mock_artifact
        mock_artifact_manager.remove.return_value = None

        result = repo.delete("skill:my-skill")

        assert result is True
        # The implementation parses "skill:my-skill" and constructs an
        # ArtifactType enum from the "skill" prefix — verify with the real type.
        mock_artifact_manager.remove.assert_called_once_with(
            artifact_name="my-skill",
            artifact_type=ArtifactType("skill"),
            collection_name=None,
        )

    def test_delete_nonexistent_artifact_returns_false(
        self, repo, mock_artifact_manager
    ):
        """delete() on a missing artifact should return False without crashing."""
        mock_artifact_manager.show.side_effect = ValueError("not found")

        result = repo.delete("skill:ghost")

        assert result is False
        mock_artifact_manager.remove.assert_not_called()

    def test_delete_invalid_id_returns_false(self, repo):
        """delete() with a malformed id (no colon) should return False."""
        result = repo.delete("invalid-id-no-colon")
        assert result is False

    # ------------------------------------------------------------------
    # update_content() — file write + cache refresh
    # ------------------------------------------------------------------

    def test_update_content_writes_file_and_refreshes_cache(
        self,
        tmp_path,
        repo,
        mock_artifact_manager,
        mock_refresh_fn,
        mock_db_session,
    ):
        """After update_content(), the target file should be updated AND cache refreshed."""
        # Create an artifact file on disk
        skill_file = tmp_path / "my-skill.md"
        skill_file.write_text("# Old Content", encoding="utf-8")

        mock_artifact = _make_mock_artifact("my-skill", "skill")
        mock_artifact.path = "my-skill.md"
        mock_artifact_manager.show.side_effect = None
        mock_artifact_manager.show.return_value = mock_artifact

        # Make the path resolver return an absolute path
        mock_artifact_manager.collection_mgr.config.get_collection_path.return_value = tmp_path

        result = repo.update_content("skill:my-skill", "# New Content")

        assert result is True
        assert skill_file.read_text(encoding="utf-8") == "# New Content"

        mock_refresh_fn.assert_called_once_with(
            session=mock_db_session,
            artifact_mgr=mock_artifact_manager,
            artifact_id="skill:my-skill",
        )

    # ------------------------------------------------------------------
    # set_tags() — delegates to update(), which triggers refresh
    # ------------------------------------------------------------------

    def test_set_tags_calls_update_and_cache_refresh(
        self, repo, mock_artifact_manager, mock_refresh_fn, mock_db_session
    ):
        """set_tags() should delegate to update() which calls cache refresh."""
        mock_artifact = _make_mock_artifact("my-skill", "skill")
        mock_artifact_manager.show.side_effect = None
        mock_artifact_manager.show.return_value = mock_artifact
        mock_collection = MagicMock()
        mock_artifact_manager.collection_mgr.load_collection.return_value = mock_collection

        result = repo.set_tags("skill:my-skill", ["python", "testing"])

        assert result is True
        mock_refresh_fn.assert_called_once()

    def test_set_tags_on_unknown_artifact_returns_false(
        self, repo, mock_artifact_manager
    ):
        """set_tags() on a missing artifact should return False, not raise."""
        mock_artifact_manager.show.side_effect = ValueError("not found")

        result = repo.set_tags("skill:ghost", ["tag1"])

        assert result is False

    # ------------------------------------------------------------------
    # Cache refresh error handling — FS mutation still succeeds
    # ------------------------------------------------------------------

    def test_cache_refresh_failure_does_not_fail_create(
        self, tmp_path, mock_artifact_manager, mock_path_resolver, mock_db_session
    ):
        """A failing cache refresh must not prevent create() from succeeding."""
        failing_refresh = MagicMock(side_effect=RuntimeError("DB down"))
        skill_dir = tmp_path / "resilient-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Resilient", encoding="utf-8")

        mock_artifact = _make_mock_artifact("resilient-skill", "skill")
        mock_artifact_manager.add_from_local.return_value = mock_artifact

        repo = LocalArtifactRepository(
            artifact_manager=mock_artifact_manager,
            path_resolver=mock_path_resolver,
            db_session=mock_db_session,
            refresh_fn=failing_refresh,
        )

        dto = ArtifactDTO(
            id="skill:resilient-skill",
            name="resilient-skill",
            artifact_type="skill",
            content_path=str(skill_dir),
        )

        # Should not raise despite refresh failure
        result = repo.create(dto)
        assert result is not None
        assert result.name == "resilient-skill"


# =============================================================================
# LocalProjectRepository — write-through tests
# =============================================================================


class TestLocalProjectRepositoryWriteThrough:
    """Verify cache manager is called on create/update/delete."""

    @pytest.fixture
    def mock_path_resolver(self, tmp_path):
        resolver = MagicMock()
        resolver.collection_root.return_value = tmp_path
        return resolver

    @pytest.fixture
    def mock_cache_manager(self):
        cm = MagicMock()
        cm.repository = MagicMock()
        cm.repository.get_project.return_value = None
        cm.repository.list_projects.return_value = []
        return cm

    @pytest.fixture
    def repo_with_cache(self, mock_path_resolver, mock_cache_manager):
        return LocalProjectRepository(
            path_resolver=mock_path_resolver,
            cache_manager=mock_cache_manager,
        )

    @pytest.fixture
    def repo_no_cache(self, mock_path_resolver):
        return LocalProjectRepository(
            path_resolver=mock_path_resolver,
            cache_manager=None,
        )

    @pytest.fixture
    def project_dto(self, tmp_path):
        path_str = str(tmp_path / "my-project")
        project_id = _encode_project_id(path_str)
        return ProjectDTO(
            id=project_id,
            name="my-project",
            path=path_str,
        )

    # ------------------------------------------------------------------
    # create()
    # ------------------------------------------------------------------

    def test_create_calls_cache_upsert(
        self, repo_with_cache, mock_cache_manager, project_dto
    ):
        """create() must call upsert_project on the cache manager."""
        # Ensure get() returns None (project does not yet exist)
        mock_cache_manager.repository.get_project.return_value = None

        result = repo_with_cache.create(project_dto)

        mock_cache_manager.upsert_project.assert_called_once()
        call_kwargs = mock_cache_manager.upsert_project.call_args[0][0]
        assert call_kwargs["id"] == project_dto.id
        assert call_kwargs["name"] == project_dto.name

        assert result.id == project_dto.id
        assert result.name == project_dto.name

    def test_create_without_cache_still_returns_dto(
        self, repo_no_cache, project_dto, tmp_path
    ):
        """create() without a cache manager must still succeed and return a DTO."""
        # We need the path to exist for get() filesystem fallback (but project
        # does not have .skillmeat-deployed.toml so it won't be discovered —
        # that's fine because create() checks get() which returns None for
        # non-existent dirs).
        result = repo_no_cache.create(project_dto)

        assert result.id == project_dto.id
        assert result.created_at is not None

    def test_create_raises_for_duplicate(
        self, repo_with_cache, mock_cache_manager, project_dto, tmp_path
    ):
        """create() must raise ValueError when a project already exists."""
        mock_orm_project = MagicMock()
        mock_orm_project.id = project_dto.id
        mock_orm_project.name = project_dto.name
        mock_orm_project.path = project_dto.path
        mock_orm_project.artifacts = []
        mock_orm_project.description = None
        mock_orm_project.status = "active"
        mock_orm_project.created_at = None
        mock_orm_project.updated_at = None
        mock_orm_project.last_fetched = None
        mock_cache_manager.repository.get_project.return_value = mock_orm_project

        with pytest.raises(ValueError, match="already exists"):
            repo_with_cache.create(project_dto)

    # ------------------------------------------------------------------
    # update()
    # ------------------------------------------------------------------

    def test_update_calls_cache_update(
        self, repo_with_cache, mock_cache_manager, project_dto
    ):
        """update() must forward allowed fields to the cache repository."""
        # Pre-populate get() with a project
        mock_orm_project = MagicMock()
        mock_orm_project.id = project_dto.id
        mock_orm_project.name = project_dto.name
        mock_orm_project.path = project_dto.path
        mock_orm_project.artifacts = []
        mock_orm_project.description = None
        mock_orm_project.status = "active"
        mock_orm_project.created_at = None
        mock_orm_project.updated_at = None
        mock_orm_project.last_fetched = None
        mock_cache_manager.repository.get_project.return_value = mock_orm_project

        repo_with_cache.update(project_dto.id, {"name": "renamed-project"})

        mock_cache_manager.repository.update_project.assert_called_once_with(
            project_dto.id, name="renamed-project"
        )

    def test_update_nonexistent_raises(self, repo_with_cache, mock_cache_manager):
        """update() on a missing project must raise KeyError."""
        mock_cache_manager.repository.get_project.return_value = None

        with pytest.raises(KeyError):
            repo_with_cache.update("nonexistent-id", {"name": "whatever"})

    # ------------------------------------------------------------------
    # delete()
    # ------------------------------------------------------------------

    def test_delete_calls_cache_delete(
        self, repo_with_cache, mock_cache_manager, project_dto
    ):
        """delete() must delegate to cache_repository.delete_project."""
        mock_cache_manager.repository.delete_project.return_value = True

        result = repo_with_cache.delete(project_dto.id)

        mock_cache_manager.repository.delete_project.assert_called_once_with(
            project_dto.id
        )
        assert result is True

    def test_delete_without_cache_returns_false(
        self, repo_no_cache, project_dto
    ):
        """delete() without a cache manager must return False (nothing to delete)."""
        result = repo_no_cache.delete(project_dto.id)
        assert result is False

    # ------------------------------------------------------------------
    # refresh()
    # ------------------------------------------------------------------

    def test_refresh_syncs_to_cache(
        self, repo_with_cache, mock_cache_manager, tmp_path
    ):
        """refresh() must call upsert_project and return a current DTO."""
        project_dir = tmp_path / "refresh-project"
        project_dir.mkdir()
        project_id = _encode_project_id(str(project_dir))

        # No deployments on disk (empty project dir) — artifact_count == 0
        mock_cache_manager.repository.get_project.return_value = None

        result = repo_with_cache.refresh(project_id)

        mock_cache_manager.upsert_project.assert_called_once()
        assert result.id == project_id
        assert result.name == "refresh-project"

    def test_refresh_raises_for_nonexistent_path(
        self, repo_with_cache
    ):
        """refresh() for a path that does not exist on disk must raise KeyError."""
        bad_id = _encode_project_id("/this/path/does/not/exist")

        with pytest.raises(KeyError):
            repo_with_cache.refresh(bad_id)


# =============================================================================
# LocalCollectionRepository — write-through tests
# =============================================================================


class TestLocalCollectionRepositoryWriteThrough:
    """Verify collection manager is called correctly on read / refresh / stats."""

    @pytest.fixture
    def mock_collection_manager(self, tmp_path):
        cm = MagicMock()
        cm.get_active_collection_name.return_value = "default"

        mock_collection = MagicMock()
        mock_collection.name = "default"
        mock_collection.version = "1.0.0"
        mock_collection.artifacts = []
        mock_collection.created = None
        mock_collection.updated = None
        cm.load_collection.return_value = mock_collection
        cm.config.get_collection_path.return_value = tmp_path

        return cm

    @pytest.fixture
    def mock_path_resolver(self, tmp_path):
        resolver = MagicMock()
        resolver.collection_root.return_value = tmp_path
        resolver.artifacts_dir.return_value = tmp_path / "artifacts"
        return resolver

    @pytest.fixture
    def repo(self, mock_collection_manager, mock_path_resolver):
        return LocalCollectionRepository(
            collection_manager=mock_collection_manager,
            path_resolver=mock_path_resolver,
        )

    # ------------------------------------------------------------------
    # get()
    # ------------------------------------------------------------------

    def test_get_returns_active_collection_dto(self, repo, mock_collection_manager):
        """get() must return a CollectionDTO for the active collection."""
        result = repo.get()

        mock_collection_manager.get_active_collection_name.assert_called_once()
        assert result is not None
        assert result.id == "default"
        assert result.name == "default"

    def test_get_returns_none_when_no_active_collection(
        self, repo, mock_collection_manager
    ):
        """get() must return None when the collection manager raises."""
        mock_collection_manager.get_active_collection_name.side_effect = Exception(
            "no collection"
        )

        result = repo.get()

        assert result is None

    # ------------------------------------------------------------------
    # refresh() — invalidates cache and reloads
    # ------------------------------------------------------------------

    def test_refresh_invalidates_cache_and_reloads(
        self, repo, mock_collection_manager
    ):
        """refresh() must call invalidate_collection_cache then load_collection."""
        result = repo.refresh()

        mock_collection_manager.invalidate_collection_cache.assert_called_once_with(
            "default"
        )
        assert mock_collection_manager.load_collection.call_count >= 1
        assert result.id == "default"

    # ------------------------------------------------------------------
    # get_stats() — returns artifact count and size
    # ------------------------------------------------------------------

    def test_get_stats_returns_required_keys(self, repo, tmp_path):
        """get_stats() must return dict with artifact_count, total_size_bytes, etc."""
        stats = repo.get_stats()

        assert "artifact_count" in stats
        assert "total_size_bytes" in stats
        assert "last_synced" in stats
        assert "collection_root" in stats
        assert stats["artifact_count"] == 0

    # ------------------------------------------------------------------
    # list() — delegates to manager
    # ------------------------------------------------------------------

    def test_list_returns_collection_dtos(self, repo, mock_collection_manager):
        """list() must return a list of CollectionDTO values."""
        mock_collection_manager.list_collections.return_value = ["default"]

        result = repo.list()

        mock_collection_manager.list_collections.assert_called_once()
        assert isinstance(result, list)

    # ------------------------------------------------------------------
    # get_artifacts() — filters and paginates
    # ------------------------------------------------------------------

    def test_get_artifacts_returns_empty_for_empty_collection(
        self, repo, mock_collection_manager
    ):
        """get_artifacts() returns an empty list when no artifacts exist."""
        result = repo.get_artifacts("default")
        assert result == []

    def test_get_artifacts_returns_none_for_missing_collection(
        self, repo, mock_collection_manager
    ):
        """get_artifacts() returns [] when the collection does not exist."""
        mock_collection_manager.load_collection.side_effect = ValueError("not found")

        result = repo.get_artifacts("nonexistent")

        assert result == []


# =============================================================================
# LocalDeploymentRepository — write-through tests
# =============================================================================


class TestLocalDeploymentRepositoryWriteThrough:
    """Verify deploy / undeploy delegate to DeploymentManager correctly."""

    @pytest.fixture
    def mock_deployment_manager(self):
        return MagicMock()

    @pytest.fixture
    def mock_path_resolver(self, tmp_path):
        resolver = MagicMock()
        resolver.collection_root.return_value = tmp_path
        return resolver

    @pytest.fixture
    def repo(self, mock_deployment_manager, mock_path_resolver):
        return LocalDeploymentRepository(
            deployment_manager=mock_deployment_manager,
            path_resolver=mock_path_resolver,
        )

    @pytest.fixture
    def project_path(self, tmp_path):
        p = tmp_path / "target-project"
        p.mkdir()
        return p

    @pytest.fixture
    def project_id(self, project_path):
        return _encode_project_id(str(project_path))

    # ------------------------------------------------------------------
    # deploy()
    # ------------------------------------------------------------------

    def test_deploy_calls_deploy_artifacts(
        self,
        repo,
        mock_deployment_manager,
        project_id,
        project_path,
    ):
        """deploy() must delegate to DeploymentManager.deploy_artifacts."""
        mock_dep = MagicMock()
        mock_dep.artifact_name = "my-skill"
        mock_dep.artifact_type = "skill"
        mock_dep.from_collection = "default"
        mock_dep.local_modifications = False
        mock_dep.deployed_at = None
        mock_dep.artifact_path = "skills/my-skill"
        mock_dep.content_hash = "abc123"
        mock_dep.deployment_profile_id = None
        mock_dep.platform = None
        mock_deployment_manager.deploy_artifacts.return_value = [mock_dep]

        result = repo.deploy(
            artifact_id="skill:my-skill",
            project_id=project_id,
        )

        mock_deployment_manager.deploy_artifacts.assert_called_once()
        call_kwargs = mock_deployment_manager.deploy_artifacts.call_args[1]
        assert "artifact_names" in call_kwargs
        assert "my-skill" in call_kwargs["artifact_names"]

        assert result.artifact_id == "skill:my-skill"
        assert result.artifact_name == "my-skill"
        assert result.artifact_type == "skill"

    def test_deploy_invalid_artifact_id_raises(
        self, repo, project_id
    ):
        """deploy() with a malformed artifact_id must raise ValueError."""
        with pytest.raises(ValueError, match="type:name"):
            repo.deploy(artifact_id="no-colon-here", project_id=project_id)

    def test_deploy_invalid_project_id_raises(self, repo):
        """deploy() with an invalid (non-base64) project_id must raise ValueError."""
        with pytest.raises(ValueError):
            repo.deploy(
                artifact_id="skill:my-skill",
                project_id="!!!not-valid-base64!!!",
            )

    def test_deploy_records_exist_after_operation(
        self,
        repo,
        mock_deployment_manager,
        project_id,
        project_path,
    ):
        """After deploy(), list() filtered by project_id should include the new record."""
        mock_dep = MagicMock()
        mock_dep.artifact_name = "listed-skill"
        mock_dep.artifact_type = "skill"
        mock_dep.from_collection = "default"
        mock_dep.local_modifications = False
        mock_dep.deployed_at = None
        mock_dep.artifact_path = "skills/listed-skill"
        mock_dep.content_hash = "deadbeef"
        mock_dep.deployment_profile_id = None
        mock_dep.platform = None
        mock_deployment_manager.deploy_artifacts.return_value = [mock_dep]

        # list_deployments is called during list()
        mock_deployment_manager.list_deployments.return_value = [mock_dep]

        repo.deploy("skill:listed-skill", project_id)

        deployments = repo.list(filters={"project_id": project_id})
        assert len(deployments) == 1
        assert deployments[0].artifact_name == "listed-skill"

    # ------------------------------------------------------------------
    # undeploy()
    # ------------------------------------------------------------------

    def test_undeploy_calls_manager_undeploy(
        self, repo, mock_deployment_manager
    ):
        """undeploy() must delegate to DeploymentManager.undeploy."""
        mock_deployment_manager.undeploy.return_value = None

        result = repo.undeploy("skill:my-skill")

        mock_deployment_manager.undeploy.assert_called_once()
        assert result is True

    def test_undeploy_malformed_id_returns_false(self, repo):
        """undeploy() with a malformed id must return False without raising."""
        result = repo.undeploy("no-colon")
        assert result is False

    def test_undeploy_manager_exception_returns_false(
        self, repo, mock_deployment_manager
    ):
        """undeploy() must return False when the manager raises."""
        mock_deployment_manager.undeploy.side_effect = Exception("fs error")

        result = repo.undeploy("skill:my-skill")

        assert result is False

    # ------------------------------------------------------------------
    # get_status()
    # ------------------------------------------------------------------

    def test_get_status_returns_deployed_for_clean_deployment(
        self, repo, mock_deployment_manager
    ):
        """get_status() must return 'deployed' for a clean deployment."""
        mock_dep = MagicMock()
        mock_dep.artifact_name = "status-skill"
        mock_dep.artifact_type = "skill"
        mock_dep.from_collection = "default"
        mock_dep.local_modifications = False
        mock_dep.deployed_at = None
        mock_dep.artifact_path = "skills/status-skill"
        mock_dep.content_hash = None
        mock_dep.deployment_profile_id = None
        mock_dep.platform = None
        mock_deployment_manager.list_deployments.return_value = [mock_dep]

        status = repo.get_status("skill:status-skill")
        assert status == "deployed"

    def test_get_status_raises_for_unknown_deployment(
        self, repo, mock_deployment_manager
    ):
        """get_status() must raise KeyError for a non-existent deployment."""
        mock_deployment_manager.list_deployments.return_value = []

        with pytest.raises(KeyError):
            repo.get_status("skill:ghost")


# =============================================================================
# LocalTagRepository — write-through tests
# =============================================================================


class TestLocalTagRepositoryWriteThrough:
    """Verify that tag CRUD operations reach the underlying DB TagRepository."""

    @pytest.fixture
    def mock_tag_repo(self):
        """Mock the cache-layer TagRepository that LocalTagRepository delegates to."""
        repo = MagicMock()
        return repo

    @pytest.fixture
    def repo(self, mock_tag_repo):
        """Construct LocalTagRepository with an injected session factory."""
        with patch(
            "skillmeat.core.repositories.local_tag.LocalTagRepository._get_tag_repo",
            return_value=mock_tag_repo,
        ):
            yield LocalTagRepository()

    # ------------------------------------------------------------------
    # create()
    # ------------------------------------------------------------------

    def test_create_tag_persists_to_db(self, repo, mock_tag_repo):
        """create() must call TagRepository.create and return a TagDTO."""
        mock_orm_tag = _make_mock_tag_orm("tag-1", "ai", "ai", "#FF5733")
        mock_tag_repo.create.return_value = mock_orm_tag

        result = repo.create(name="ai", color="#FF5733")

        mock_tag_repo.create.assert_called_once_with(
            name="ai", slug="ai", color="#FF5733"
        )
        assert isinstance(result, TagDTO)
        assert result.name == "ai"
        assert result.slug == "ai"
        assert result.color == "#FF5733"

    def test_create_tag_slug_derived_from_name(self, repo, mock_tag_repo):
        """create() must derive the slug from the name via _slugify."""
        mock_orm_tag = _make_mock_tag_orm("tag-2", "My Tag", "my-tag")
        mock_tag_repo.create.return_value = mock_orm_tag

        repo.create(name="My Tag")

        _, call_kwargs = mock_tag_repo.create.call_args
        # slug should be kebab-cased
        assert call_kwargs["slug"] == "my-tag"

    def test_create_duplicate_raises_value_error(self, repo, mock_tag_repo):
        """create() must surface DB conflicts as ValueError."""
        mock_tag_repo.create.side_effect = Exception("unique constraint")

        with pytest.raises(ValueError, match="Failed to create tag"):
            repo.create(name="duplicate")

    # ------------------------------------------------------------------
    # update()
    # ------------------------------------------------------------------

    def test_update_tag_calls_db_update(self, repo, mock_tag_repo):
        """update() must call TagRepository.update with the supplied fields."""
        mock_orm_tag = _make_mock_tag_orm("tag-1", "ai", "ai", "#00FF00")
        mock_tag_repo.update.return_value = mock_orm_tag

        result = repo.update("tag-1", {"color": "#00FF00"})

        mock_tag_repo.update.assert_called_once_with(
            tag_id="tag-1",
            name=None,
            slug=None,
            color="#00FF00",
        )
        assert result.color == "#00FF00"

    def test_update_nonexistent_tag_raises_key_error(self, repo, mock_tag_repo):
        """update() must raise KeyError when TagRepository returns None."""
        mock_tag_repo.update.return_value = None

        with pytest.raises(KeyError):
            repo.update("ghost-id", {"color": "#FFFFFF"})

    # ------------------------------------------------------------------
    # delete()
    # ------------------------------------------------------------------

    def test_delete_tag_calls_db_delete(self, repo, mock_tag_repo):
        """delete() must call TagRepository.delete and return its result."""
        mock_tag_repo.delete.return_value = True

        result = repo.delete("tag-1")

        mock_tag_repo.delete.assert_called_once_with(tag_id="tag-1")
        assert result is True

    def test_delete_missing_tag_returns_false(self, repo, mock_tag_repo):
        """delete() must return False when the tag does not exist in the DB."""
        mock_tag_repo.delete.return_value = False

        result = repo.delete("ghost-tag")

        assert result is False

    # ------------------------------------------------------------------
    # list()
    # ------------------------------------------------------------------

    def test_list_tags_without_filter(self, repo, mock_tag_repo):
        """list() without filters must call list_all on the tag repo."""
        mock_tag_repo.list_all.return_value = ([], None, False)

        result = repo.list()

        mock_tag_repo.list_all.assert_called_once()
        assert result == []

    def test_list_tags_with_name_filter(self, repo, mock_tag_repo):
        """list() with a name filter must call search_by_name."""
        mock_tag_repo.search_by_name.return_value = [
            _make_mock_tag_orm("t1", "ai", "ai")
        ]

        result = repo.list(filters={"name": "ai"})

        mock_tag_repo.search_by_name.assert_called_once_with("ai", limit=1000)
        assert len(result) == 1
        assert result[0].name == "ai"

    # ------------------------------------------------------------------
    # get() / get_by_slug()
    # ------------------------------------------------------------------

    def test_get_existing_tag_by_id(self, repo, mock_tag_repo):
        """get() must return a TagDTO when the tag exists in the DB."""
        mock_tag_repo.get_by_id.return_value = _make_mock_tag_orm("tag-1", "ai", "ai")

        result = repo.get("tag-1")

        assert result is not None
        assert result.id == "tag-1"

    def test_get_missing_tag_returns_none(self, repo, mock_tag_repo):
        """get() must return None when the tag does not exist."""
        mock_tag_repo.get_by_id.return_value = None

        result = repo.get("missing-tag")

        assert result is None

    def test_get_by_slug(self, repo, mock_tag_repo):
        """get_by_slug() must delegate to TagRepository.get_by_slug."""
        mock_tag_repo.get_by_slug.return_value = _make_mock_tag_orm("t1", "ai", "ai")

        result = repo.get_by_slug("ai")

        mock_tag_repo.get_by_slug.assert_called_once_with("ai")
        assert result is not None
        assert result.slug == "ai"


# =============================================================================
# LocalSettingsRepository — write-through tests
# =============================================================================


class TestLocalSettingsRepositoryWriteThrough:
    """Verify TOML config is written on update() and readable via get()."""

    @pytest.fixture
    def mock_config_manager(self):
        """Return a mocked ConfigManager."""
        cm = MagicMock()
        # Default return values for config.get()
        cm.get.return_value = None
        cm.get_indexing_mode.return_value = "opt_in"
        cm.read.return_value = {}
        return cm

    @pytest.fixture
    def mock_path_resolver(self, tmp_path):
        resolver = MagicMock()
        resolver.collection_root.return_value = tmp_path
        return resolver

    @pytest.fixture
    def repo(self, mock_config_manager, mock_path_resolver):
        return LocalSettingsRepository(
            path_resolver=mock_path_resolver,
            config_manager=mock_config_manager,
        )

    # ------------------------------------------------------------------
    # get()
    # ------------------------------------------------------------------

    def test_get_returns_settings_dto(self, repo):
        """get() must return a SettingsDTO with the current configuration."""
        result = repo.get()

        assert isinstance(result, SettingsDTO)
        assert result.default_scope in ("user", "local")
        assert result.edition in ("community", "pro")

    def test_get_masks_github_token(self, repo, mock_config_manager):
        """get() must mask the GitHub token, exposing only the first 4 chars."""
        mock_config_manager.get.side_effect = lambda key, *_args, **_kw: (
            "ghp_secrettoken123" if "github-token" in key else None
        )

        result = repo.get()

        assert result.github_token is not None
        # The raw token should not appear; it should be masked
        assert "secret" not in (result.github_token or "")
        assert result.github_token.startswith("ghp_")
        assert "*" in result.github_token

    # ------------------------------------------------------------------
    # update()
    # ------------------------------------------------------------------

    def test_update_default_scope_writes_toml(
        self, repo, mock_config_manager
    ):
        """update() for default_scope must call config.set with the right TOML key."""
        repo.update({"default_scope": "local"})

        mock_config_manager.set.assert_called_with(
            "settings.default-scope", "local"
        )

    def test_update_github_token_writes_toml(
        self, repo, mock_config_manager
    ):
        """update() for github_token must call config.set with the right TOML key."""
        repo.update({"github_token": "ghp_newtoken123"})

        mock_config_manager.set.assert_called_with(
            "settings.github-token", "ghp_newtoken123"
        )

    def test_update_indexing_mode_calls_set_indexing_mode(
        self, repo, mock_config_manager
    ):
        """update() for indexing_mode must delegate to config.set_indexing_mode."""
        repo.update({"indexing_mode": "on"})

        mock_config_manager.set_indexing_mode.assert_called_once_with("on")

    def test_update_unknown_key_stored_under_settings_section(
        self, repo, mock_config_manager
    ):
        """update() for unrecognised keys must store them under 'settings.<key>'."""
        repo.update({"my_custom_key": "custom_value"})

        mock_config_manager.set.assert_called_with(
            "settings.my_custom_key", "custom_value"
        )

    def test_update_returns_updated_settings_dto(
        self, repo, mock_config_manager
    ):
        """update() must return a SettingsDTO reflecting the new values."""
        # After the set() call, config.get() should return the new value
        mock_config_manager.get.side_effect = lambda key, *args, **kw: (
            "local" if "default-scope" in key else None
        )

        result = repo.update({"default_scope": "local"})

        assert isinstance(result, SettingsDTO)

    def test_multiple_updates_all_written(self, repo, mock_config_manager):
        """update() with multiple keys must write each one to the config."""
        repo.update(
            {
                "default_scope": "user",
                "edition": "pro",
            }
        )

        calls = [str(c) for c in mock_config_manager.set.call_args_list]
        # Both keys must have been written
        assert any("default-scope" in c for c in calls)
        assert any("edition" in c for c in calls)

    # ------------------------------------------------------------------
    # validate_github_token()
    # ------------------------------------------------------------------

    def test_validate_github_token_empty_returns_false(self, repo):
        """validate_github_token() must return False immediately for an empty string."""
        result = repo.validate_github_token("")
        assert result is False

    def test_validate_github_token_whitespace_returns_false(self, repo):
        """validate_github_token() must return False for a whitespace-only token."""
        result = repo.validate_github_token("   ")
        assert result is False

    def test_validate_github_token_network_error_returns_false(
        self, repo, mock_config_manager
    ):
        """validate_github_token() must return False when GitHub is unreachable."""
        # The implementation imports GitHubClient inside the method body from
        # skillmeat.core.github_client — patch it at the source module.
        with patch(
            "skillmeat.core.github_client.GitHubClient",
            side_effect=Exception("network error"),
        ):
            result = repo.validate_github_token("ghp_somefaketoken")

        assert result is False
