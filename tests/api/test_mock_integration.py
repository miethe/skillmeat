"""Example tests demonstrating mock repository fixtures.

These tests show how to use the ``mock_repos``, ``app_with_mocks``, and
``client_with_mocks`` fixtures defined in ``tests/conftest.py`` to write
fast, hermetic API tests that require no filesystem I/O and no live database.

How it works
------------
``app_with_mocks`` calls ``fastapi.testclient.TestClient`` against a
``create_app()`` instance whose six repository DI providers have been replaced
with lambdas returning in-memory mock objects.  Any endpoint that injects
``ArtifactRepoDep``, ``ProjectRepoDep``, ``CollectionRepoDep``,
``DeploymentRepoDep``, ``TagRepoDep``, or ``SettingsRepoDep`` will receive
the corresponding mock automatically.

Endpoints that still depend on the old-style manager deps
(``CollectionManagerDep``, ``ArtifactManagerDep``, etc.) need those providers
overridden separately, as shown in the mixed-dependency examples below.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from skillmeat.core.interfaces.dtos import (
    ArtifactDTO,
    CollectionDTO,
    DeploymentDTO,
    ProjectDTO,
    TagDTO,
)


# =============================================================================
# Fixture smoke tests — verify the fixtures themselves are functional
# =============================================================================


class TestMockReposFixture:
    """Verify that ``mock_repos`` is correctly instantiated and isolated."""

    def test_all_six_repos_present(self, mock_repos):
        """The fixture returns all six mock repositories."""
        expected_keys = {
            "artifacts",
            "projects",
            "collections",
            "deployments",
            "tags",
            "settings",
        }
        assert set(mock_repos.keys()) == expected_keys

    def test_repos_start_empty(self, mock_repos):
        """Each mock starts with an empty store."""
        assert mock_repos["artifacts"].list() == []
        assert mock_repos["projects"].list() == []
        assert mock_repos["collections"].list() == []
        assert mock_repos["deployments"].list() == []
        assert mock_repos["tags"].list() == []

    def test_isolation_between_tests_a(self, mock_repos):
        """State written in one test must not bleed into another.

        This is test A — it seeds an artifact.  Test B (below) checks the
        store is empty, proving that ``reset()`` ran between them.
        """
        dto = ArtifactDTO(id="skill:canvas", name="canvas", artifact_type="skill")
        mock_repos["artifacts"].seed(dto)
        assert mock_repos["artifacts"].get("skill:canvas") is not None

    def test_isolation_between_tests_b(self, mock_repos):
        """State seeded in test A must not be visible here."""
        assert mock_repos["artifacts"].list() == []

    def test_seed_and_get_artifact(self, mock_repos):
        """Pre-seeded artifacts are retrievable by ID."""
        dto = ArtifactDTO(
            id="skill:test-skill",
            name="test-skill",
            artifact_type="skill",
            description="A seeded test skill",
        )
        mock_repos["artifacts"].seed(dto)

        result = mock_repos["artifacts"].get("skill:test-skill")
        assert result is not None
        assert result.name == "test-skill"
        assert result.description == "A seeded test skill"

    def test_seed_and_list_artifacts(self, mock_repos):
        """Multiple pre-seeded artifacts appear in list()."""
        dtos = [
            ArtifactDTO(id=f"skill:skill-{i}", name=f"skill-{i}", artifact_type="skill")
            for i in range(3)
        ]
        for dto in dtos:
            mock_repos["artifacts"].seed(dto)

        listed = mock_repos["artifacts"].list()
        assert len(listed) == 3

    def test_seed_and_get_project(self, mock_repos):
        """Pre-seeded projects are retrievable."""
        dto = ProjectDTO(id="project-alpha", name="Project Alpha", path="/tmp/alpha")
        mock_repos["projects"].seed(dto)

        result = mock_repos["projects"].get("project-alpha")
        assert result is not None
        assert result.name == "Project Alpha"

    def test_seed_and_get_collection(self, mock_repos):
        """Pre-seeded collections appear in get()."""
        dto = CollectionDTO(
            id="col-default",
            name="default",
            path="/tmp/collection",
        )
        mock_repos["collections"].seed(dto)

        result = mock_repos["collections"].get()
        assert result is not None
        assert result.name == "default"

    def test_seed_and_list_deployments(self, mock_repos):
        """Pre-seeded deployments appear in list()."""
        dto = DeploymentDTO(
            id="skill:canvas@project-alpha",
            artifact_id="skill:canvas",
            artifact_name="canvas",
            artifact_type="skill",
            project_id="project-alpha",
            scope="local",
            status="deployed",
            deployed_at="2026-01-01T00:00:00+00:00",
        )
        mock_repos["deployments"].seed(dto)

        listed = mock_repos["deployments"].list()
        assert len(listed) == 1
        assert listed[0].artifact_id == "skill:canvas"

    def test_seed_and_list_tags(self, mock_repos):
        """Pre-seeded tags appear in list()."""
        dto = TagDTO(id="tag-python", name="Python", slug="python")
        mock_repos["tags"].seed(dto)

        listed = mock_repos["tags"].list()
        assert len(listed) == 1
        assert listed[0].slug == "python"

    def test_settings_defaults(self, mock_repos):
        """The settings mock returns a SettingsDTO with sensible defaults."""
        from skillmeat.core.interfaces.dtos import SettingsDTO

        settings = mock_repos["settings"].get()
        assert isinstance(settings, SettingsDTO)

    def test_settings_update(self, mock_repos):
        """Settings can be mutated via update()."""
        mock_repos["settings"].update({"github_token": "ghp_test123"})
        settings = mock_repos["settings"].get()
        assert settings.github_token == "ghp_test123"


# =============================================================================
# DI override wiring — verify the fixtures inject mocks into the app
# =============================================================================


class TestAppWithMocksFixture:
    """Verify that ``app_with_mocks`` correctly wires mock repos into FastAPI."""

    def test_app_has_dependency_overrides(self, app_with_mocks):
        """The six repository providers are all overridden."""
        from skillmeat.api.dependencies import (
            get_artifact_repository,
            get_collection_repository,
            get_deployment_repository,
            get_project_repository,
            get_settings_repository,
            get_tag_repository,
        )

        overrides = app_with_mocks.dependency_overrides
        assert get_artifact_repository in overrides
        assert get_project_repository in overrides
        assert get_collection_repository in overrides
        assert get_deployment_repository in overrides
        assert get_tag_repository in overrides
        assert get_settings_repository in overrides

    def test_override_returns_mock_instance(self, app_with_mocks, mock_repos):
        """The overridden factory returns the exact mock instance."""
        from skillmeat.api.dependencies import get_artifact_repository

        factory = app_with_mocks.dependency_overrides[get_artifact_repository]
        returned = factory()
        assert returned is mock_repos["artifacts"]

    def test_mock_data_visible_through_override(self, app_with_mocks, mock_repos):
        """Data seeded on the mock is accessible via the DI-resolved instance."""
        from skillmeat.api.dependencies import get_artifact_repository

        dto = ArtifactDTO(id="skill:canvas", name="canvas", artifact_type="skill")
        mock_repos["artifacts"].seed(dto)

        # Simulate what FastAPI does: resolve the override and call the repo
        repo = app_with_mocks.dependency_overrides[get_artifact_repository]()
        assert repo.get("skill:canvas") is not None


# =============================================================================
# End-to-end HTTP example using ``client_with_mocks``
# =============================================================================


class TestClientWithMocksEndpointExample:
    """Demonstrate HTTP-level testing with mock repositories.

    These tests use ``client_with_mocks`` to make real HTTP requests against
    the FastAPI router layer.  No filesystem or database is touched.

    Endpoints that depend on legacy manager deps (CollectionManagerDep, etc.)
    alongside the new repo deps need those providers overridden separately on
    ``app_with_mocks``.  The pattern is shown below.
    """

    def test_health_endpoint_works(self, client_with_mocks):
        """The /health endpoint works without any mock data."""
        resp = client_with_mocks.get("/health")
        # Health endpoint may return 200 or 503 depending on cache_manager
        # availability — either is fine; we're testing the fixture wiring.
        assert resp.status_code in (200, 503)

    def test_deployment_list_with_mocked_repo_and_manager(
        self, app_with_mocks, mock_repos
    ):
        """``GET /api/v1/deploy`` returns a well-formed response with mocked deps.

        The deployments router (prefix ``/deploy``) uses ``DeploymentRepoDep``
        (overridden by ``app_with_mocks``) alongside ``DeploymentManager``
        (provided by ``get_deployment_manager`` which depends on
        ``CollectionManagerDep``).  We override both legacy deps with
        MagicMocks so no filesystem access occurs.

        Note: the full endpoint URL is ``/api/v1/deploy`` (the router uses
        prefix="/deploy"), not ``/api/v1/deployments``.
        """
        from fastapi.testclient import TestClient

        from skillmeat.api.dependencies import get_collection_manager
        from skillmeat.api.routers.deployments import get_deployment_manager

        # Override the legacy manager deps with MagicMocks
        mock_mgr = MagicMock()
        mock_mgr.list_deployments.return_value = []
        mock_mgr.compute_deployment_statuses_batch.return_value = {}

        mock_coll_mgr = MagicMock()

        app_with_mocks.dependency_overrides[get_deployment_manager] = (
            lambda: mock_mgr
        )
        app_with_mocks.dependency_overrides[get_collection_manager] = (
            lambda: mock_coll_mgr
        )

        try:
            with TestClient(app_with_mocks) as client:
                resp = client.get(
                    "/api/v1/deploy",
                    params={"project_path": "/tmp/proj"},
                )
                # The endpoint returns 200 with the deployment list.
                # Exact shape depends on router implementation; we verify the
                # response is a well-formed JSON object.
                assert resp.status_code == 200
                body = resp.json()
                assert isinstance(body, dict)
        finally:
            app_with_mocks.dependency_overrides.pop(get_deployment_manager, None)
            app_with_mocks.dependency_overrides.pop(get_collection_manager, None)


# =============================================================================
# Pattern reference — how to write your own mock-based router test
# =============================================================================


class TestPatternDocumentation:
    """Illustrative pattern for teams writing new router tests.

    These tests are intentionally simple and focus on the cookbook pattern
    rather than exercising complex business logic.
    """

    def test_pattern_seed_search_assert(self, mock_repos):
        """Three-step pattern: seed → search → assert (no HTTP layer).

        This is the lightest-weight option: test the mock repo directly
        to verify your seed/query logic before writing full HTTP tests.
        """
        # 1. Seed
        dtos = [
            ArtifactDTO(
                id=f"skill:{name}",
                name=name,
                artifact_type="skill",
                description=f"Skill: {name}",
            )
            for name in ["canvas", "document-skill", "test-runner"]
        ]
        for dto in dtos:
            mock_repos["artifacts"].seed(dto)

        # 2. Search
        results = mock_repos["artifacts"].search("canvas")

        # 3. Assert
        assert len(results) == 1
        assert results[0].id == "skill:canvas"

    def test_pattern_create_via_repo(self, mock_repos):
        """Artifacts created via the repo interface are retrievable."""
        dto = ArtifactDTO(id="command:my-cmd", name="my-cmd", artifact_type="command")
        created = mock_repos["artifacts"].create(dto)

        assert created.id == "command:my-cmd"
        assert created.uuid is not None  # UUID assigned on create

        # Verify it can be retrieved
        fetched = mock_repos["artifacts"].get("command:my-cmd")
        assert fetched is not None
        assert fetched.uuid == created.uuid

    def test_pattern_update_via_repo(self, mock_repos):
        """Artifacts can be updated after creation."""
        dto = ArtifactDTO(id="skill:updatable", name="updatable", artifact_type="skill")
        mock_repos["artifacts"].seed(dto)

        mock_repos["artifacts"].update(
            "skill:updatable", {"description": "Updated description"}
        )

        updated = mock_repos["artifacts"].get("skill:updatable")
        assert updated is not None
        assert updated.description == "Updated description"

    def test_pattern_delete_via_repo(self, mock_repos):
        """Artifacts can be deleted; subsequent get returns None."""
        dto = ArtifactDTO(id="skill:temp", name="temp", artifact_type="skill")
        mock_repos["artifacts"].seed(dto)

        deleted = mock_repos["artifacts"].delete("skill:temp")
        assert deleted is True

        assert mock_repos["artifacts"].get("skill:temp") is None

    def test_pattern_tag_assignment(self, mock_repos):
        """Tags can be assigned to artifacts and queried."""
        tag = TagDTO(id="t-python", name="Python", slug="python")
        mock_repos["tags"].seed(tag)

        mock_repos["tags"].assign("t-python", "skill:canvas")

        updated_tag = mock_repos["tags"].get("t-python")
        assert updated_tag is not None
        assert updated_tag.artifact_count == 1

        artifact_ids = mock_repos["tags"].get_artifact_ids("t-python")
        assert "skill:canvas" in artifact_ids
