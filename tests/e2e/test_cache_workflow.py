"""End-to-end integration tests for cache system workflows.

This module tests complete user workflows simulating real-world usage:
- Fresh app startup and cache population
- Manual refresh operations
- CLI operations triggering cache invalidation
- File changes triggering cache updates
- Outdated artifact detection
- Cross-project search functionality

Each test is independent and uses isolated temporary databases for determinism.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from skillmeat.cache.manager import CacheManager
from skillmeat.cache.models import Project, Artifact
from skillmeat.cache.repository import CacheRepository
from skillmeat.cache.refresh import RefreshJob


class TestCacheWorkflows:
    """End-to-end tests simulating real user workflows."""

    def test_fresh_app_startup_cache_populated(
        self, client: TestClient, cache_repository: CacheRepository, temp_project: Path
    ):
        """E2E: Fresh startup -> cache populated -> fast reload.

        Workflow:
        1. Start fresh (no cache data)
        2. Trigger initial refresh
        3. Verify cache populated with projects
        4. Reload (should be fast from cache)
        5. Verify data matches
        """
        # Step 1: Verify cache is empty initially
        response = client.get("/api/v1/cache/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_projects"] == 0
        assert data["total_artifacts"] == 0

        # Step 2: Manually add project to cache (simulating discovery)
        project_id = f"proj-{temp_project.name}"
        project = Project(
            id=project_id,
            name=temp_project.name,
            path=str(temp_project),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )
        cache_repository.create_project(project)

        artifact = Artifact(
            id=f"art-test-skill-{project_id}",
            name="test-skill",
            type="skill",
            project_id=project_id,
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
        )
        cache_repository.create_artifact(artifact)

        # Step 3: Verify cache populated
        response = client.get("/api/v1/cache/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_projects"] == 1
        assert data["total_artifacts"] == 1

        # Step 4: Reload from cache (should be fast)
        start_time = time.time()
        response = client.get("/api/v1/cache/projects")
        duration = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == temp_project.name

        # Cache read should be very fast (< 100ms)
        assert duration < 0.1

        # Step 5: Verify artifact data matches
        response = client.get("/api/v1/cache/artifacts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "test-skill"
        assert data["items"][0]["deployed_version"] == "1.0.0"

    def test_manual_refresh_updates_cache(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        temp_project: Path,
    ):
        """E2E: Manual refresh -> cache updated -> UI reflects changes.

        Workflow:
        1. Start with cached data
        2. Trigger manual refresh via API
        3. Verify cache updated
        4. Verify new data visible in subsequent requests
        """
        # Step 1: Seed cache with initial data
        project_id = f"proj-{temp_project.name}"
        project = Project(
            id=project_id,
            name=temp_project.name,
            path=str(temp_project),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )
        cache_repository.create_project(project)

        # Verify initial state
        response = client.get("/api/v1/cache/projects")
        assert response.status_code == status.HTTP_200_OK
        initial_data = response.json()
        assert initial_data["total"] == 1

        # Step 2: Trigger manual refresh
        # Mock RefreshJob to avoid actual filesystem operations
        with patch("skillmeat.api.routers.cache.RefreshJob") as MockRefreshJob:
            mock_job = Mock()
            MockRefreshJob.return_value = mock_job

            # Configure mock result
            mock_result = Mock()
            mock_result.success = True
            mock_result.projects_refreshed = 1
            mock_result.changes_detected = 1
            mock_result.errors = []
            mock_result.duration_seconds = 0.5
            mock_job.refresh_all.return_value = mock_result

            # Mock get_refresh_status
            mock_status = {
                "is_running": False,
                "next_run_time": None,
                "last_run_time": None,
            }
            mock_job.get_refresh_status.return_value = mock_status

            # Trigger refresh
            response = client.post(
                "/api/v1/cache/refresh",
                json={"force": False},
            )

            # Step 3: Verify refresh succeeded
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["projects_refreshed"] == 1
            assert data["changes_detected"] == 1

        # Step 4: Verify data still accessible
        response = client.get("/api/v1/cache/projects")
        assert response.status_code == status.HTTP_200_OK
        updated_data = response.json()
        assert updated_data["total"] >= 1

    def test_cli_add_artifact_invalidates_cache(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        temp_project: Path,
    ):
        """E2E: CLI add artifact -> cache invalidated -> web reflects change.

        Workflow:
        1. Start with cached data
        2. Simulate CLI adding new artifact (or calling invalidate)
        3. Verify cache marked as stale
        4. Web request triggers refresh
        5. New artifact visible in cache
        """
        # Step 1: Seed cache with initial data
        project_id = f"proj-{temp_project.name}"
        project = Project(
            id=project_id,
            name=temp_project.name,
            path=str(temp_project),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )
        cache_repository.create_project(project)

        # Add initial artifact
        artifact1 = Artifact(
            id=f"art-skill-1-{project_id}",
            name="skill-1",
            type="skill",
            project_id=project_id,
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
        )
        cache_repository.create_artifact(artifact1)

        # Verify initial state
        response = client.get("/api/v1/cache/artifacts")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 1

        # Step 2: Simulate CLI adding new artifact (invalidate cache)
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"project_id": project_id},
        )
        assert response.status_code == status.HTTP_200_OK
        invalidate_data = response.json()
        assert invalidate_data["success"] is True
        assert invalidate_data["invalidated_count"] == 1

        # Step 3: Verify cache marked as stale
        # Get project and check status
        updated_project = cache_repository.get_project(project_id)
        assert updated_project is not None
        assert updated_project.status == "stale"

        # Step 4: Add new artifact to cache (simulating refresh)
        artifact2 = Artifact(
            id=f"art-skill-2-{project_id}",
            name="skill-2",
            type="skill",
            project_id=project_id,
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
        )
        cache_repository.create_artifact(artifact2)

        # Update project to mark as refreshed
        cache_repository.update_project(
            project_id,
            last_fetched=datetime.now(timezone.utc),
            status="active",
        )

        # Step 5: Verify new artifact visible
        response = client.get("/api/v1/cache/artifacts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2

        artifact_names = {item["name"] for item in data["items"]}
        assert "skill-1" in artifact_names
        assert "skill-2" in artifact_names

    def test_file_change_triggers_cache_update(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        temp_project: Path,
    ):
        """E2E: File change -> watcher triggers -> cache updated.

        Workflow:
        1. Start with cached project
        2. Modify project files (simulate file change)
        3. Trigger invalidation (simulating file watcher)
        4. Verify cache marked stale
        5. Refresh and verify update
        """
        # Step 1: Seed cache with project
        project_id = f"proj-{temp_project.name}"
        project = Project(
            id=project_id,
            name=temp_project.name,
            path=str(temp_project),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )
        cache_repository.create_project(project)

        artifact = Artifact(
            id=f"art-test-skill-{project_id}",
            name="test-skill",
            type="skill",
            project_id=project_id,
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
        )
        cache_repository.create_artifact(artifact)

        # Step 2: Modify project file
        skill_md = temp_project / ".claude" / "skills" / "test-skill" / "SKILL.md"
        assert skill_md.exists()

        # Update version in file
        content = skill_md.read_text()
        updated_content = content.replace("version: 1.0.0", "version: 1.1.0")
        skill_md.write_text(updated_content)

        # Step 3: Trigger invalidation (simulating file watcher event)
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"project_id": project_id},
        )
        assert response.status_code == status.HTTP_200_OK

        # Step 4: Verify cache marked stale
        updated_project = cache_repository.get_project(project_id)
        assert updated_project.status == "stale"

        # Step 5: Refresh cache (update artifact with new version)
        cache_repository.update_artifact(
            artifact.id,
            deployed_version="1.1.0",
        )

        cache_repository.update_project(
            project_id,
            last_fetched=datetime.now(timezone.utc),
            status="active",
        )

        # Verify updated version visible
        response = client.get(f"/api/v1/cache/artifacts?project_id={project_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"][0]["deployed_version"] == "1.1.0"

    def test_outdated_artifact_detection_workflow(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        temp_project: Path,
    ):
        """E2E: Deploy artifact -> upstream update -> detected as outdated.

        Workflow:
        1. Cache project with artifact version 1.0.0
        2. Update upstream version to 1.1.0
        3. Trigger refresh
        4. Verify artifact shows as outdated
        5. Verify /stale-artifacts includes it
        """
        # Step 1: Cache project with artifact v1.0.0
        project_id = f"proj-{temp_project.name}"
        project = Project(
            id=project_id,
            name=temp_project.name,
            path=str(temp_project),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )
        cache_repository.create_project(project)

        artifact = Artifact(
            id=f"art-test-skill-{project_id}",
            name="test-skill",
            type="skill",
            project_id=project_id,
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
        )
        cache_repository.create_artifact(artifact)

        # Verify initial state - no outdated artifacts
        response = client.get("/api/v1/cache/stale-artifacts")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0

        # Step 2: Simulate upstream update to v1.1.0
        cache_repository.update_artifact(
            artifact.id,
            upstream_version="1.1.0",
            is_outdated=True,
        )

        # Step 3: Trigger refresh (mock to avoid actual GitHub calls)
        with patch("skillmeat.api.routers.cache.RefreshJob") as MockRefreshJob:
            mock_job = Mock()
            MockRefreshJob.return_value = mock_job

            mock_result = Mock()
            mock_result.success = True
            mock_result.projects_refreshed = 1
            mock_result.changes_detected = 1
            mock_result.errors = []
            mock_result.duration_seconds = 0.3
            mock_job.refresh_all.return_value = mock_result

            mock_status = {
                "is_running": False,
                "next_run_time": None,
                "last_run_time": None,
            }
            mock_job.get_refresh_status.return_value = mock_status

            response = client.post(
                "/api/v1/cache/refresh",
                json={"force": True},
            )
            assert response.status_code == status.HTTP_200_OK

        # Step 4: Verify artifact shows as outdated
        response = client.get("/api/v1/cache/artifacts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        outdated_artifacts = [item for item in data["items"] if item["is_outdated"]]
        assert len(outdated_artifacts) == 1
        assert outdated_artifacts[0]["deployed_version"] == "1.0.0"
        assert outdated_artifacts[0]["upstream_version"] == "1.1.0"

        # Step 5: Verify /stale-artifacts includes it
        response = client.get("/api/v1/cache/stale-artifacts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 1
        assert data["items"][0]["name"] == "test-skill"
        assert data["items"][0]["deployed_version"] == "1.0.0"
        assert data["items"][0]["upstream_version"] == "1.1.0"

    def test_search_across_cached_projects(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        multiple_projects: list[Path],
    ):
        """E2E: Search workflow across multiple projects.

        Workflow:
        1. Cache multiple projects with various artifacts
        2. Search for specific artifact name
        3. Verify results include matches from multiple projects
        4. Verify pagination works
        """
        # Step 1: Cache multiple projects with artifacts
        project_ids = []
        for i, project_path in enumerate(multiple_projects):
            project_id = f"proj-{project_path.name}"
            project_ids.append(project_id)

            project = Project(
                id=project_id,
                name=project_path.name,
                path=str(project_path),
                status="active",
                last_fetched=datetime.now(timezone.utc),
            )
            cache_repository.create_project(project)

            # Add artifacts with searchable names
            if i == 0:
                artifact_name = "docker-skill"
            elif i == 1:
                artifact_name = "docker-compose"
            else:
                artifact_name = "python-skill"

            artifact = Artifact(
                id=f"art-{artifact_name}-{project_id}",
                name=artifact_name,
                type="skill",
                project_id=project_id,
                deployed_version=f"1.{i}.0",
                upstream_version=f"1.{i}.0",
                is_outdated=False,
            )
            cache_repository.create_artifact(artifact)

        # Step 2: Search for "docker" artifacts
        response = client.get("/api/v1/cache/search?query=docker")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Step 3: Verify results include matches from multiple projects
        assert data["total"] == 2  # docker-skill and docker-compose
        assert data["query"] == "docker"

        result_names = {item["name"] for item in data["items"]}
        assert "docker-skill" in result_names
        assert "docker-compose" in result_names
        assert "python-skill" not in result_names

        # Verify relevance scoring
        for item in data["items"]:
            assert "score" in item
            assert item["score"] > 0

        # Step 4: Verify pagination works
        response = client.get("/api/v1/cache/search?query=docker&limit=1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 2  # Total matches
        assert len(data["items"]) == 1  # Limited to 1
        assert data["limit"] == 1

        # Get second page
        response = client.get("/api/v1/cache/search?query=docker&skip=1&limit=1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["skip"] == 1


class TestCacheWorkflowErrorHandling:
    """Test error handling in E2E workflows."""

    def test_invalidate_nonexistent_project(
        self, client: TestClient, cache_repository: CacheRepository
    ):
        """E2E: Invalidating non-existent project returns 404."""
        response = client.post(
            "/api/v1/cache/invalidate",
            json={"project_id": "nonexistent-proj"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_search_with_empty_query(self, client: TestClient):
        """E2E: Search with empty query returns validation error."""
        response = client.get("/api/v1/cache/search?query=")

        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_sort_parameter(
        self, client: TestClient, cache_repository: CacheRepository, temp_project: Path
    ):
        """E2E: Invalid sort parameter returns 400 Bad Request."""
        # Seed cache with data
        project_id = f"proj-{temp_project.name}"
        project = Project(
            id=project_id,
            name=temp_project.name,
            path=str(temp_project),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )
        cache_repository.create_project(project)

        artifact = Artifact(
            id=f"art-test-skill-{project_id}",
            name="test-skill",
            type="skill",
            project_id=project_id,
            deployed_version="1.0.0",
            upstream_version="2.0.0",
            is_outdated=True,
        )
        cache_repository.create_artifact(artifact)

        # Try invalid sort_by parameter
        response = client.get("/api/v1/cache/stale-artifacts?sort_by=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid" in data["detail"].lower()


class TestCacheWorkflowPerformance:
    """Test performance characteristics of cache workflows."""

    def test_cache_read_performance(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        multiple_projects: list[Path],
    ):
        """E2E: Verify cache reads are fast even with multiple projects."""
        # Seed cache with multiple projects and artifacts
        for i, project_path in enumerate(multiple_projects):
            project_id = f"proj-{project_path.name}"

            project = Project(
                id=project_id,
                name=project_path.name,
                path=str(project_path),
                status="active",
                last_fetched=datetime.now(timezone.utc),
            )
            cache_repository.create_project(project)

            # Add 5 artifacts per project
            for j in range(5):
                artifact = Artifact(
                    id=f"art-skill-{i}-{j}-{project_id}",
                    name=f"skill-{i}-{j}",
                    type="skill",
                    project_id=project_id,
                    deployed_version=f"1.{j}.0",
                    upstream_version=f"1.{j}.0",
                    is_outdated=False,
                )
                cache_repository.create_artifact(artifact)

        # Measure read performance
        start_time = time.time()
        response = client.get("/api/v1/cache/artifacts")
        duration = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should have 15 artifacts (3 projects * 5 artifacts each)
        assert data["total"] == 15

        # Read should be fast (< 200ms for 15 artifacts)
        assert duration < 0.2

    def test_search_performance_with_many_artifacts(
        self,
        client: TestClient,
        cache_repository: CacheRepository,
        multiple_projects: list[Path],
    ):
        """E2E: Verify search is performant with many artifacts."""
        # Seed cache with many artifacts
        for i, project_path in enumerate(multiple_projects):
            project_id = f"proj-{project_path.name}"

            project = Project(
                id=project_id,
                name=project_path.name,
                path=str(project_path),
                status="active",
                last_fetched=datetime.now(timezone.utc),
            )
            cache_repository.create_project(project)

            # Add 10 artifacts per project with mix of names
            for j in range(10):
                name = f"docker-skill-{j}" if j % 3 == 0 else f"python-skill-{j}"
                artifact = Artifact(
                    id=f"art-{name}-{project_id}",
                    name=name,
                    type="skill",
                    project_id=project_id,
                    deployed_version=f"1.{j}.0",
                    upstream_version=f"1.{j}.0",
                    is_outdated=False,
                )
                cache_repository.create_artifact(artifact)

        # Measure search performance
        start_time = time.time()
        response = client.get("/api/v1/cache/search?query=docker")
        duration = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should find docker artifacts across all projects
        assert data["total"] > 0

        # Search should be fast (< 100ms)
        assert duration < 0.1
