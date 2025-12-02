"""Shared fixtures for E2E cache workflow tests.

Provides test fixtures for:
- Temporary cache databases
- Temporary project directories
- FastAPI test clients
- Seeded cache data
- Mock external APIs
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.cache.manager import CacheManager
from skillmeat.cache.models import Project, Artifact, create_tables
from skillmeat.cache.repository import CacheRepository


# =============================================================================
# Cache Fixtures
# =============================================================================


@pytest.fixture
def temp_cache(tmp_path: Path) -> Generator[Path, None, None]:
    """Create temporary cache database.

    Returns:
        Path to temporary cache database file

    Example:
        def test_something(temp_cache):
            cache_manager = CacheManager(db_path=temp_cache)
            cache_manager.initialize_cache()
    """
    cache_db = tmp_path / "test_cache.db"

    # Create tables in the temporary database
    create_tables(db_path=cache_db)

    yield cache_db

    # Cleanup: Close any open connections and delete file
    if cache_db.exists():
        # Force close any open SQLite connections
        try:
            conn = sqlite3.connect(str(cache_db))
            conn.close()
        except Exception:
            pass
        cache_db.unlink()


@pytest.fixture
def cache_repository(temp_cache: Path) -> Generator[CacheRepository, None, None]:
    """Create CacheRepository with temporary database.

    Returns:
        CacheRepository instance with temporary database

    Example:
        def test_something(cache_repository):
            projects = cache_repository.get_all_projects()
            assert len(projects) == 0
    """
    repo = CacheRepository(db_path=str(temp_cache))
    yield repo
    repo.close()


@pytest.fixture
def cache_manager(temp_cache: Path) -> Generator[CacheManager, None, None]:
    """Create initialized CacheManager with temporary database.

    Returns:
        CacheManager instance with temporary database

    Example:
        def test_something(cache_manager):
            status = cache_manager.get_cache_status()
            assert status["total_projects"] == 0
    """
    manager = CacheManager(db_path=str(temp_cache), ttl_minutes=360)
    manager.initialize_cache()
    yield manager
    manager.close()


# =============================================================================
# Project Fixtures
# =============================================================================


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create temporary project with .claude directory structure.

    Returns:
        Path to temporary project directory

    Example:
        def test_something(temp_project):
            claude_dir = temp_project / ".claude"
            assert claude_dir.exists()
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create .claude directory structure
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()

    # Create subdirectories for different artifact types
    (claude_dir / "skills").mkdir()
    (claude_dir / "commands").mkdir()
    (claude_dir / "agents").mkdir()

    # Create a sample skill
    skill_dir = claude_dir / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
title: Test Skill
description: A test skill for E2E testing
version: 1.0.0
---

# Test Skill

This is a test skill for end-to-end testing.
"""
    )

    return project_dir


@pytest.fixture
def multiple_projects(tmp_path: Path) -> list[Path]:
    """Create multiple temporary projects for testing.

    Returns:
        List of project directory paths

    Example:
        def test_something(multiple_projects):
            assert len(multiple_projects) == 3
            for project in multiple_projects:
                assert (project / ".claude").exists()
    """
    projects = []

    for i in range(3):
        project_dir = tmp_path / f"project_{i}"
        project_dir.mkdir(parents=True, exist_ok=True)

        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "skills").mkdir()

        # Create sample skill with different versions
        skill_dir = claude_dir / "skills" / f"skill-{i}"
        skill_dir.mkdir(parents=True)

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            f"""---
title: Skill {i}
description: Test skill number {i}
version: 1.{i}.0
---

# Skill {i}

Test skill for project {i}.
"""
        )

        projects.append(project_dir)

    return projects


# =============================================================================
# FastAPI Client Fixtures
# =============================================================================


@pytest.fixture
def test_settings(temp_cache: Path) -> APISettings:
    """Create test API settings.

    Returns:
        APISettings configured for testing

    Example:
        def test_something(test_settings):
            assert test_settings.env == Environment.TESTING
    """
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=True,
        cors_origins=["http://localhost:3000"],
        auth_enabled=False,  # Disable auth for E2E tests
    )


@pytest.fixture
def client(test_settings: APISettings, temp_cache: Path) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with temp cache.

    Returns:
        TestClient with lifespan context

    Example:
        def test_something(client):
            response = client.get("/api/v1/cache/status")
            assert response.status_code == 200
    """
    # Create app with test settings
    app = create_app(test_settings)

    # Override cache manager to use temp cache
    from skillmeat.api.dependencies import app_state

    with TestClient(app) as test_client:
        # Initialize cache manager with temp database
        cache_mgr = CacheManager(db_path=str(temp_cache), ttl_minutes=360)
        cache_mgr.initialize_cache()
        app_state.cache_manager = cache_mgr

        yield test_client

        # Cleanup
        cache_mgr.close()


# =============================================================================
# Seeded Cache Fixtures
# =============================================================================


@pytest.fixture
def seeded_cache(
    cache_repository: CacheRepository, temp_project: Path
) -> tuple[CacheRepository, str]:
    """Cache with pre-seeded project data.

    Returns:
        Tuple of (CacheRepository, project_id)

    Example:
        def test_something(seeded_cache):
            cache_repository, project_id = seeded_cache
            projects = cache_repository.get_all_projects()
            assert len(projects) == 1
    """
    # Add project to cache
    project_id = f"proj-{temp_project.name}"

    # Insert project into cache
    project = Project(
        id=project_id,
        name=temp_project.name,
        path=str(temp_project),
        status="active",
        last_fetched=datetime.now(timezone.utc),
    )

    cache_repository.upsert_project(project)

    # Add artifact to cache
    artifact = Artifact(
        id=f"art-test-skill-{project_id}",
        name="test-skill",
        type="skill",
        project_id=project_id,
        deployed_version="1.0.0",
        upstream_version="1.0.0",
        is_outdated=False,
    )

    cache_repository.upsert_artifact(artifact)

    return cache_repository, project_id


@pytest.fixture
def seeded_cache_with_multiple_projects(
    cache_repository: CacheRepository, multiple_projects: list[Path]
) -> tuple[CacheRepository, list[str]]:
    """Cache with multiple pre-seeded projects.

    Returns:
        Tuple of (CacheRepository, list of project_ids)

    Example:
        def test_something(seeded_cache_with_multiple_projects):
            cache_repository, project_ids = seeded_cache_with_multiple_projects
            assert len(project_ids) == 3
    """
    project_ids = []

    for i, project_path in enumerate(multiple_projects):
        project_id = f"proj-{project_path.name}"
        project_ids.append(project_id)

        # Add project
        project = Project(
            id=project_id,
            name=project_path.name,
            path=str(project_path),
            status="active",
            last_fetched=datetime.now(timezone.utc),
        )

        cache_repository.upsert_project(project)

        # Add artifact
        artifact = Artifact(
            id=f"art-skill-{i}-{project_id}",
            name=f"skill-{i}",
            type="skill",
            project_id=project_id,
            deployed_version=f"1.{i}.0",
            upstream_version=f"1.{i}.0",
            is_outdated=False,
        )

        cache_repository.upsert_artifact(artifact)

    return cache_repository, project_ids


# =============================================================================
# Mock External APIs
# =============================================================================


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses.

    Returns:
        MagicMock configured to simulate GitHub API

    Example:
        def test_something(mock_github_api):
            with patch("requests.get", mock_github_api):
                # Your test that makes GitHub API calls
                pass
    """
    mock = MagicMock()

    def mock_get(url, **kwargs):
        """Simulate GitHub API GET requests."""
        response = Mock()
        response.status_code = 200

        # Mock releases API
        if "/releases" in url:
            response.json.return_value = [
                {
                    "tag_name": "v1.1.0",
                    "name": "Release 1.1.0",
                    "published_at": "2025-12-01T00:00:00Z",
                }
            ]
        # Mock commits API
        elif "/commits" in url:
            response.json.return_value = {
                "sha": "abc123def456",
                "commit": {
                    "message": "Update skill",
                    "author": {"date": "2025-12-01T00:00:00Z"},
                },
            }
        else:
            response.json.return_value = {}

        return response

    mock.get = mock_get
    return mock


@pytest.fixture
def mock_file_watcher():
    """Mock file system watcher.

    Returns:
        MagicMock configured to simulate file watcher events

    Example:
        def test_something(mock_file_watcher):
            with patch("watchdog.observers.Observer", mock_file_watcher):
                # Your test that uses file watching
                pass
    """
    mock = MagicMock()

    # Configure observer mock
    observer_instance = Mock()
    observer_instance.start.return_value = None
    observer_instance.stop.return_value = None
    observer_instance.join.return_value = None

    mock.return_value = observer_instance
    return mock


# =============================================================================
# Helper Functions
# =============================================================================


def create_artifact_file(
    project_dir: Path, artifact_type: str, name: str, version: str = "1.0.0"
) -> Path:
    """Helper to create artifact files in project.

    Args:
        project_dir: Project directory path
        artifact_type: Type of artifact (skill, command, agent)
        name: Artifact name
        version: Artifact version

    Returns:
        Path to created artifact

    Example:
        artifact_path = create_artifact_file(
            temp_project, "skill", "my-skill", "1.2.0"
        )
    """
    claude_dir = project_dir / ".claude"

    if artifact_type == "skill":
        artifact_dir = claude_dir / "skills" / name
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_file = artifact_dir / "SKILL.md"
    else:
        # Commands and agents are single files
        artifact_dir = claude_dir / f"{artifact_type}s"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_file = artifact_dir / f"{name}.md"

    artifact_file.write_text(
        f"""---
title: {name.replace('-', ' ').title()}
description: Test {artifact_type}
version: {version}
---

# {name.replace('-', ' ').title()}

Test {artifact_type} for E2E testing.
"""
    )

    return artifact_file


def simulate_file_change(file_path: Path, new_version: str = "1.1.0") -> None:
    """Helper to simulate file changes.

    Args:
        file_path: Path to file to modify
        new_version: New version to set in frontmatter

    Example:
        simulate_file_change(skill_md, "2.0.0")
    """
    content = file_path.read_text()

    # Update version in frontmatter
    import re

    updated_content = re.sub(
        r"version:\s*[\d.]+", f"version: {new_version}", content
    )

    file_path.write_text(updated_content)


# Export helper functions for use in tests
pytest.create_artifact_file = create_artifact_file
pytest.simulate_file_change = simulate_file_change
