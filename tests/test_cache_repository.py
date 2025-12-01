"""Unit tests for CacheRepository.

This module provides comprehensive unit tests for the CacheRepository class,
testing all CRUD operations, edge cases, error handling, and transaction management.

Test coverage includes:
- Project CRUD operations
- Artifact CRUD operations
- Metadata operations
- Marketplace entry operations
- Transaction management
- Error handling
- Concurrent access patterns
"""

from __future__ import annotations

import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

import pytest

from skillmeat.cache.models import (
    Artifact,
    ArtifactMetadata,
    CacheMetadata,
    MarketplaceEntry,
    Project,
)
from skillmeat.cache.repository import (
    CacheRepository,
    CacheError,
    CacheNotFoundError,
    CacheConstraintError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_db():
    """Create temporary in-memory database.

    Returns:
        Path to temporary database file

    Note:
        Using a temp file instead of :memory: to better simulate production
        and test file-based SQLite behavior.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def repo(temp_db):
    """Create CacheRepository instance for testing.

    Args:
        temp_db: Temporary database path from temp_db fixture

    Returns:
        CacheRepository instance with clean database
    """
    return CacheRepository(db_path=temp_db)


@pytest.fixture
def sample_project():
    """Create sample project data.

    Returns:
        Project instance with test data
    """
    return Project(
        id="proj-test-123",
        name="Test Project",
        path="/test/path/to/project",
        description="A test project",
        status="active",
    )


@pytest.fixture
def sample_artifact(sample_project):
    """Create sample artifact data linked to project.

    Args:
        sample_project: Project fixture to link artifact to

    Returns:
        Artifact instance with test data
    """
    return Artifact(
        id="art-test-123",
        project_id=sample_project.id,
        name="test-skill",
        type="skill",
        source="github:user/repo/skill",
        deployed_version="1.0.0",
        upstream_version="1.0.0",
        is_outdated=False,
        local_modified=False,
    )


# =============================================================================
# Project CRUD Tests
# =============================================================================


class TestProjectOperations:
    """Tests for project CRUD operations."""

    def test_create_project_success(self, repo, sample_project):
        """Test creating a project successfully."""
        project = repo.create_project(sample_project)

        assert project.id == sample_project.id
        assert project.name == sample_project.name
        assert project.path == sample_project.path
        assert project.description == sample_project.description
        assert project.status == "active"
        assert project.created_at is not None
        assert project.updated_at is not None

    def test_create_project_duplicate_id_raises_constraint_error(self, repo, sample_project):
        """Test that creating a project with duplicate ID raises CacheConstraintError."""
        repo.create_project(sample_project)

        # Try to create another project with same ID
        duplicate = Project(
            id=sample_project.id,
            name="Different Name",
            path="/different/path",
            status="active",
        )

        with pytest.raises(CacheConstraintError) as exc_info:
            repo.create_project(duplicate)

        assert sample_project.id in str(exc_info.value)

    def test_create_project_duplicate_path_raises_constraint_error(self, repo, sample_project):
        """Test that creating a project with duplicate path raises CacheConstraintError."""
        repo.create_project(sample_project)

        # Try to create another project with same path
        duplicate = Project(
            id="proj-different-456",
            name="Different Name",
            path=sample_project.path,
            status="active",
        )

        with pytest.raises(CacheConstraintError) as exc_info:
            repo.create_project(duplicate)

        assert sample_project.path in str(exc_info.value)

    def test_get_project_exists(self, repo, sample_project):
        """Test getting an existing project."""
        created = repo.create_project(sample_project)

        retrieved = repo.get_project(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name
        assert retrieved.path == created.path

    def test_get_project_not_found_returns_none(self, repo):
        """Test that getting a non-existent project returns None."""
        result = repo.get_project("nonexistent-id")

        assert result is None

    def test_get_project_by_path(self, repo, sample_project):
        """Test getting a project by filesystem path."""
        created = repo.create_project(sample_project)

        retrieved = repo.get_project_by_path(created.path)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.path == created.path

    def test_list_projects_empty(self, repo):
        """Test listing projects when database is empty."""
        projects = repo.list_projects()

        assert projects == []
        assert len(projects) == 0

    def test_list_projects_with_data(self, repo):
        """Test listing projects with data."""
        # Create multiple projects
        projects_to_create = [
            Project(id=f"proj-{i}", name=f"Project {i}", path=f"/path/{i}", status="active")
            for i in range(5)
        ]

        for project in projects_to_create:
            repo.create_project(project)

        retrieved = repo.list_projects()

        assert len(retrieved) == 5
        assert all(p.id in [f"proj-{i}" for i in range(5)] for p in retrieved)

    def test_list_projects_pagination(self, repo):
        """Test pagination when listing projects."""
        # Create 10 projects
        for i in range(10):
            project = Project(
                id=f"proj-{i}",
                name=f"Project {i}",
                path=f"/path/{i}",
                status="active"
            )
            repo.create_project(project)

        # Get first 5
        first_page = repo.list_projects(skip=0, limit=5)
        assert len(first_page) == 5

        # Get next 5
        second_page = repo.list_projects(skip=5, limit=5)
        assert len(second_page) == 5

        # Ensure no overlap
        first_ids = {p.id for p in first_page}
        second_ids = {p.id for p in second_page}
        assert len(first_ids & second_ids) == 0

    def test_update_project_success(self, repo, sample_project):
        """Test updating a project."""
        created = repo.create_project(sample_project)

        updated = repo.update_project(
            created.id,
            status="stale",
            error_message="Test error",
        )

        assert updated.id == created.id
        assert updated.status == "stale"
        assert updated.error_message == "Test error"
        assert updated.name == created.name  # Unchanged fields remain

    def test_update_project_not_found_raises_error(self, repo):
        """Test that updating a non-existent project raises CacheNotFoundError."""
        with pytest.raises(CacheNotFoundError) as exc_info:
            repo.update_project("nonexistent-id", status="stale")

        assert "nonexistent-id" in str(exc_info.value)

    def test_delete_project_success(self, repo, sample_project):
        """Test deleting a project."""
        created = repo.create_project(sample_project)

        result = repo.delete_project(created.id)

        assert result is True

        # Verify project is deleted
        retrieved = repo.get_project(created.id)
        assert retrieved is None

    def test_delete_project_not_found_returns_false(self, repo):
        """Test that deleting a non-existent project returns False."""
        result = repo.delete_project("nonexistent-id")

        assert result is False

    def test_delete_project_cascades_artifacts(self, repo, sample_project, sample_artifact):
        """Test that deleting a project cascades to its artifacts."""
        # Create project and artifact
        repo.create_project(sample_project)
        repo.create_artifact(sample_artifact)

        # Verify artifact exists
        retrieved_artifact = repo.get_artifact(sample_artifact.id)
        assert retrieved_artifact is not None

        # Delete project
        repo.delete_project(sample_project.id)

        # Verify artifact is also deleted
        retrieved_artifact = repo.get_artifact(sample_artifact.id)
        assert retrieved_artifact is None

    def test_get_stale_projects(self, repo):
        """Test getting stale projects."""
        # Create an old project
        old_project = Project(
            id="proj-old",
            name="Old Project",
            path="/old/path",
            status="active",
        )
        created_old = repo.create_project(old_project)

        # Manually set last_fetched to 7 hours ago
        old_threshold = datetime.utcnow() - timedelta(hours=7)
        repo.update_project(created_old.id, last_fetched=old_threshold)

        # Create a fresh project
        fresh_project = Project(
            id="proj-fresh",
            name="Fresh Project",
            path="/fresh/path",
            status="active",
        )
        created_fresh = repo.create_project(fresh_project)
        repo.update_project(created_fresh.id, last_fetched=datetime.utcnow())

        # Get stale projects (TTL = 360 minutes = 6 hours)
        stale = repo.get_stale_projects(ttl_minutes=360)

        assert len(stale) == 1
        assert stale[0].id == created_old.id

    def test_get_projects_by_status(self, repo):
        """Test getting projects filtered by status."""
        # Create projects with different statuses
        statuses = ["active", "stale", "error", "active"]
        for i, status in enumerate(statuses):
            project = Project(
                id=f"proj-{i}",
                name=f"Project {i}",
                path=f"/path/{i}",
                status=status,
            )
            repo.create_project(project)

        # Get active projects
        active = repo.get_projects_by_status("active")
        assert len(active) == 2
        assert all(p.status == "active" for p in active)

        # Get stale projects
        stale = repo.get_projects_by_status("stale")
        assert len(stale) == 1
        assert stale[0].status == "stale"

        # Get error projects
        error = repo.get_projects_by_status("error")
        assert len(error) == 1
        assert error[0].status == "error"


# =============================================================================
# Artifact CRUD Tests
# =============================================================================


class TestArtifactOperations:
    """Tests for artifact CRUD operations."""

    def test_create_artifact_success(self, repo, sample_project, sample_artifact):
        """Test creating an artifact successfully."""
        # Create project first
        repo.create_project(sample_project)

        # Create artifact
        artifact = repo.create_artifact(sample_artifact)

        assert artifact.id == sample_artifact.id
        assert artifact.project_id == sample_project.id
        assert artifact.name == sample_artifact.name
        assert artifact.type == sample_artifact.type
        assert artifact.created_at is not None

    def test_create_artifact_with_invalid_project_raises_error(self, repo):
        """Test that creating an artifact with non-existent project raises CacheConstraintError."""
        artifact = Artifact(
            id="art-orphan",
            project_id="nonexistent-project",
            name="orphan-skill",
            type="skill",
        )

        with pytest.raises(CacheConstraintError) as exc_info:
            repo.create_artifact(artifact)

        assert "nonexistent-project" in str(exc_info.value)

    def test_get_artifact_exists(self, repo, sample_project, sample_artifact):
        """Test getting an existing artifact."""
        repo.create_project(sample_project)
        created = repo.create_artifact(sample_artifact)

        retrieved = repo.get_artifact(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_artifact_not_found(self, repo):
        """Test that getting a non-existent artifact returns None."""
        result = repo.get_artifact("nonexistent-id")

        assert result is None

    def test_list_artifacts_by_project(self, repo, sample_project):
        """Test listing all artifacts for a project."""
        repo.create_project(sample_project)

        # Create multiple artifacts
        for i in range(3):
            artifact = Artifact(
                id=f"art-{i}",
                project_id=sample_project.id,
                name=f"skill-{i}",
                type="skill",
            )
            repo.create_artifact(artifact)

        artifacts = repo.list_artifacts_by_project(sample_project.id)

        assert len(artifacts) == 3
        assert all(a.project_id == sample_project.id for a in artifacts)

    def test_get_artifacts_by_type(self, repo, sample_project):
        """Test getting artifacts filtered by type."""
        repo.create_project(sample_project)

        # Create artifacts of different types
        types = ["skill", "command", "agent", "skill"]
        for i, artifact_type in enumerate(types):
            artifact = Artifact(
                id=f"art-{i}",
                project_id=sample_project.id,
                name=f"artifact-{i}",
                type=artifact_type,
            )
            repo.create_artifact(artifact)

        # Get skills
        skills = repo.get_artifacts_by_type("skill")
        assert len(skills) == 2
        assert all(a.type == "skill" for a in skills)

        # Get commands
        commands = repo.get_artifacts_by_type("command")
        assert len(commands) == 1
        assert commands[0].type == "command"

    def test_list_outdated_artifacts(self, repo, sample_project):
        """Test getting artifacts that are outdated."""
        repo.create_project(sample_project)

        # Create outdated artifact
        outdated = Artifact(
            id="art-outdated",
            project_id=sample_project.id,
            name="outdated-skill",
            type="skill",
            deployed_version="1.0.0",
            upstream_version="2.0.0",
            is_outdated=True,
        )
        repo.create_artifact(outdated)

        # Create up-to-date artifact
        current = Artifact(
            id="art-current",
            project_id=sample_project.id,
            name="current-skill",
            type="skill",
            deployed_version="1.0.0",
            upstream_version="1.0.0",
            is_outdated=False,
        )
        repo.create_artifact(current)

        # Get outdated artifacts
        outdated_list = repo.list_outdated_artifacts()

        assert len(outdated_list) == 1
        assert outdated_list[0].id == "art-outdated"
        assert outdated_list[0].is_outdated is True

    def test_update_artifact_success(self, repo, sample_project, sample_artifact):
        """Test updating an artifact."""
        repo.create_project(sample_project)
        created = repo.create_artifact(sample_artifact)

        updated = repo.update_artifact(
            created.id,
            deployed_version="2.0.0",
            is_outdated=True,
        )

        assert updated.id == created.id
        assert updated.deployed_version == "2.0.0"
        assert updated.is_outdated is True
        assert updated.name == created.name  # Unchanged fields remain

    def test_update_artifact_not_found_raises_error(self, repo):
        """Test that updating a non-existent artifact raises CacheNotFoundError."""
        with pytest.raises(CacheNotFoundError) as exc_info:
            repo.update_artifact("nonexistent-id", deployed_version="1.0.0")

        assert "nonexistent-id" in str(exc_info.value)

    def test_delete_artifact_success(self, repo, sample_project, sample_artifact):
        """Test deleting an artifact."""
        repo.create_project(sample_project)
        created = repo.create_artifact(sample_artifact)

        result = repo.delete_artifact(created.id)

        assert result is True

        # Verify artifact is deleted
        retrieved = repo.get_artifact(created.id)
        assert retrieved is None

    def test_delete_artifact_not_found_returns_false(self, repo):
        """Test that deleting a non-existent artifact returns False."""
        result = repo.delete_artifact("nonexistent-id")

        assert result is False

    def test_delete_artifact_cascades_metadata(self, repo, sample_project, sample_artifact):
        """Test that deleting an artifact cascades to its metadata."""
        repo.create_project(sample_project)
        repo.create_artifact(sample_artifact)

        # Add metadata
        metadata_dict = {
            "description": "Test description",
            "tags": ["test", "skill"],
        }
        repo.set_artifact_metadata(sample_artifact.id, metadata_dict)

        # Verify metadata exists
        metadata = repo.get_artifact_metadata(sample_artifact.id)
        assert metadata is not None

        # Delete artifact
        repo.delete_artifact(sample_artifact.id)

        # Verify metadata is also deleted
        metadata = repo.get_artifact_metadata(sample_artifact.id)
        assert metadata is None

    def test_bulk_insert_artifacts(self, repo, sample_project):
        """Test bulk inserting multiple artifacts."""
        repo.create_project(sample_project)

        # Create list of artifacts
        artifacts = [
            Artifact(
                id=f"art-{i}",
                project_id=sample_project.id,
                name=f"skill-{i}",
                type="skill",
            )
            for i in range(10)
        ]

        created = repo.bulk_insert_artifacts(artifacts)

        assert len(created) == 10

        # Verify all artifacts were created
        retrieved = repo.list_artifacts_by_project(sample_project.id)
        assert len(retrieved) == 10

    def test_bulk_insert_artifacts_with_constraint_violation(self, repo, sample_project):
        """Test that bulk insert with constraint violation raises CacheConstraintError."""
        repo.create_project(sample_project)

        # Create list with duplicate IDs
        artifacts = [
            Artifact(
                id="art-duplicate",
                project_id=sample_project.id,
                name="skill-1",
                type="skill",
            ),
            Artifact(
                id="art-duplicate",  # Duplicate ID
                project_id=sample_project.id,
                name="skill-2",
                type="skill",
            ),
        ]

        with pytest.raises(CacheConstraintError):
            repo.bulk_insert_artifacts(artifacts)

    def test_bulk_update_artifacts(self, repo, sample_project):
        """Test bulk updating multiple artifacts."""
        repo.create_project(sample_project)

        # Create artifacts
        for i in range(5):
            artifact = Artifact(
                id=f"art-{i}",
                project_id=sample_project.id,
                name=f"skill-{i}",
                type="skill",
                deployed_version="1.0.0",
            )
            repo.create_artifact(artifact)

        # Prepare updates
        updates = [
            {"id": f"art-{i}", "deployed_version": "2.0.0", "is_outdated": True}
            for i in range(5)
        ]

        count = repo.bulk_update_artifacts(updates)

        assert count == 5

        # Verify updates
        for i in range(5):
            artifact = repo.get_artifact(f"art-{i}")
            assert artifact.deployed_version == "2.0.0"
            assert artifact.is_outdated is True

    def test_search_artifacts_by_name(self, repo, sample_project):
        """Test searching artifacts by name."""
        repo.create_project(sample_project)

        # Create artifacts with different names
        names = ["docker-skill", "kubernetes-skill", "terraform-command", "docker-compose"]
        for i, name in enumerate(names):
            artifact = Artifact(
                id=f"art-{i}",
                project_id=sample_project.id,
                name=name,
                type="skill",
            )
            repo.create_artifact(artifact)

        # Search for "docker"
        results = repo.search_artifacts("docker")

        assert len(results) == 2
        assert all("docker" in a.name for a in results)

    def test_search_artifacts_with_filters(self, repo, sample_project):
        """Test searching artifacts with project and type filters."""
        # Create two projects
        repo.create_project(sample_project)

        other_project = Project(
            id="proj-other",
            name="Other Project",
            path="/other/path",
            status="active",
        )
        repo.create_project(other_project)

        # Create artifacts in both projects
        for project_id in [sample_project.id, other_project.id]:
            for i, artifact_type in enumerate(["skill", "command"]):
                artifact = Artifact(
                    id=f"art-{project_id}-{i}",
                    project_id=project_id,
                    name=f"test-{artifact_type}",
                    type=artifact_type,
                )
                repo.create_artifact(artifact)

        # Search with project filter
        results = repo.search_artifacts("test", project_id=sample_project.id)
        assert len(results) == 2
        assert all(a.project_id == sample_project.id for a in results)

        # Search with type filter
        results = repo.search_artifacts("test", artifact_type="skill")
        assert len(results) == 2
        assert all(a.type == "skill" for a in results)

        # Search with both filters
        results = repo.search_artifacts(
            "test",
            project_id=sample_project.id,
            artifact_type="command",
        )
        assert len(results) == 1
        assert results[0].project_id == sample_project.id
        assert results[0].type == "command"


# =============================================================================
# Metadata Tests
# =============================================================================


class TestMetadataOperations:
    """Tests for metadata operations."""

    def test_get_artifact_metadata_exists(self, repo, sample_project, sample_artifact):
        """Test getting metadata for an artifact that has metadata."""
        repo.create_project(sample_project)
        repo.create_artifact(sample_artifact)

        # Set metadata
        metadata_dict = {
            "description": "A test skill",
            "tags": ["test", "automation"],
        }
        repo.set_artifact_metadata(sample_artifact.id, metadata_dict)

        # Get metadata
        metadata = repo.get_artifact_metadata(sample_artifact.id)

        assert metadata is not None
        assert metadata.artifact_id == sample_artifact.id
        assert metadata.description == "A test skill"
        assert "test" in metadata.get_tags_list()
        assert "automation" in metadata.get_tags_list()

    def test_get_artifact_metadata_not_exists(self, repo):
        """Test getting metadata for an artifact that has no metadata."""
        result = repo.get_artifact_metadata("nonexistent-id")

        assert result is None

    def test_set_artifact_metadata_create(self, repo, sample_project, sample_artifact):
        """Test creating new metadata for an artifact."""
        repo.create_project(sample_project)
        repo.create_artifact(sample_artifact)

        metadata_dict = {
            "description": "Test description",
            "tags": ["tag1", "tag2"],
            "aliases": ["alias1", "alias2"],
        }

        metadata = repo.set_artifact_metadata(sample_artifact.id, metadata_dict)

        assert metadata.artifact_id == sample_artifact.id
        assert metadata.description == "Test description"
        assert metadata.get_tags_list() == ["tag1", "tag2"]
        assert metadata.get_aliases_list() == ["alias1", "alias2"]

    def test_set_artifact_metadata_update(self, repo, sample_project, sample_artifact):
        """Test updating existing metadata for an artifact."""
        repo.create_project(sample_project)
        repo.create_artifact(sample_artifact)

        # Create initial metadata
        initial_metadata = {
            "description": "Initial description",
            "tags": ["tag1"],
        }
        repo.set_artifact_metadata(sample_artifact.id, initial_metadata)

        # Update metadata
        updated_metadata = {
            "description": "Updated description",
            "tags": ["tag1", "tag2", "tag3"],
        }
        metadata = repo.set_artifact_metadata(sample_artifact.id, updated_metadata)

        assert metadata.description == "Updated description"
        assert len(metadata.get_tags_list()) == 3
        assert "tag3" in metadata.get_tags_list()

    def test_get_cache_metadata(self, repo):
        """Test getting cache system metadata."""
        # Set metadata
        repo.set_cache_metadata("schema_version", "1.0.0")

        # Get metadata
        value = repo.get_cache_metadata("schema_version")

        assert value == "1.0.0"

    def test_get_cache_metadata_not_found(self, repo):
        """Test getting non-existent cache metadata."""
        result = repo.get_cache_metadata("nonexistent-key")

        assert result is None

    def test_set_cache_metadata(self, repo):
        """Test setting cache system metadata."""
        repo.set_cache_metadata("last_vacuum", "2024-11-29T10:00:00Z")

        value = repo.get_cache_metadata("last_vacuum")

        assert value == "2024-11-29T10:00:00Z"

    def test_set_cache_metadata_update(self, repo):
        """Test updating existing cache metadata."""
        # Set initial value
        repo.set_cache_metadata("count", "100")

        # Update value
        repo.set_cache_metadata("count", "200")

        value = repo.get_cache_metadata("count")

        assert value == "200"

    def test_delete_cache_metadata(self, repo):
        """Test deleting cache system metadata."""
        # Set metadata
        repo.set_cache_metadata("temp_key", "temp_value")

        # Delete metadata
        result = repo.delete_cache_metadata("temp_key")

        assert result is True

        # Verify deletion
        value = repo.get_cache_metadata("temp_key")
        assert value is None

    def test_delete_cache_metadata_not_found(self, repo):
        """Test deleting non-existent cache metadata."""
        result = repo.delete_cache_metadata("nonexistent-key")

        assert result is False


# =============================================================================
# Marketplace Tests
# =============================================================================


class TestMarketplaceOperations:
    """Tests for marketplace entry operations."""

    def test_get_marketplace_entry(self, repo):
        """Test getting a marketplace entry."""
        # Create entry
        entry = MarketplaceEntry(
            id="mkt-test",
            name="test-skill",
            type="skill",
            url="https://github.com/user/repo/skill",
            description="A test skill",
        )
        repo.upsert_marketplace_entry(entry)

        # Get entry
        retrieved = repo.get_marketplace_entry("mkt-test")

        assert retrieved is not None
        assert retrieved.id == "mkt-test"
        assert retrieved.name == "test-skill"

    def test_get_marketplace_entry_not_found(self, repo):
        """Test getting a non-existent marketplace entry."""
        result = repo.get_marketplace_entry("nonexistent-id")

        assert result is None

    def test_list_marketplace_entries(self, repo):
        """Test listing all marketplace entries."""
        # Create multiple entries
        for i in range(5):
            entry = MarketplaceEntry(
                id=f"mkt-{i}",
                name=f"skill-{i}",
                type="skill",
                url=f"https://github.com/user/repo/skill-{i}",
            )
            repo.upsert_marketplace_entry(entry)

        entries = repo.list_marketplace_entries()

        assert len(entries) == 5

    def test_list_marketplace_entries_with_filter(self, repo):
        """Test listing marketplace entries with type filter."""
        # Create entries of different types
        types = ["skill", "command", "agent", "skill"]
        for i, entry_type in enumerate(types):
            entry = MarketplaceEntry(
                id=f"mkt-{i}",
                name=f"artifact-{i}",
                type=entry_type,
                url=f"https://github.com/user/repo/artifact-{i}",
            )
            repo.upsert_marketplace_entry(entry)

        # Filter by skill
        skills = repo.list_marketplace_entries(type_filter="skill")

        assert len(skills) == 2
        assert all(e.type == "skill" for e in skills)

    def test_upsert_marketplace_entry_insert(self, repo):
        """Test inserting a new marketplace entry."""
        entry = MarketplaceEntry(
            id="mkt-new",
            name="new-skill",
            type="skill",
            url="https://github.com/user/repo/skill",
        )

        result = repo.upsert_marketplace_entry(entry)

        assert result.id == "mkt-new"
        assert result.name == "new-skill"
        assert result.cached_at is not None

    def test_upsert_marketplace_entry_update(self, repo):
        """Test updating an existing marketplace entry."""
        # Create initial entry
        entry = MarketplaceEntry(
            id="mkt-update",
            name="old-name",
            type="skill",
            url="https://old-url.com",
        )
        repo.upsert_marketplace_entry(entry)

        # Wait a moment to ensure timestamp changes
        time.sleep(0.1)

        # Update entry
        updated_entry = MarketplaceEntry(
            id="mkt-update",
            name="new-name",
            type="command",
            url="https://new-url.com",
        )
        result = repo.upsert_marketplace_entry(updated_entry)

        assert result.id == "mkt-update"
        assert result.name == "new-name"
        assert result.type == "command"
        assert result.url == "https://new-url.com"

    def test_delete_stale_marketplace_entries(self, repo):
        """Test deleting stale marketplace entries."""
        # Create old entry
        old_entry = MarketplaceEntry(
            id="mkt-old",
            name="old-skill",
            type="skill",
            url="https://old.com",
        )
        old_entry.cached_at = datetime.utcnow() - timedelta(hours=25)
        repo.upsert_marketplace_entry(old_entry)

        # Manually update cached_at to old timestamp
        # (upsert resets it, so we need to update directly)
        with repo.transaction() as session:
            old_threshold = datetime.utcnow() - timedelta(hours=25)
            session.query(MarketplaceEntry).filter(
                MarketplaceEntry.id == "mkt-old"
            ).update({"cached_at": old_threshold})

        # Create fresh entry
        fresh_entry = MarketplaceEntry(
            id="mkt-fresh",
            name="fresh-skill",
            type="skill",
            url="https://fresh.com",
        )
        repo.upsert_marketplace_entry(fresh_entry)

        # Delete stale entries (max_age=24 hours)
        count = repo.delete_stale_marketplace_entries(max_age_hours=24)

        assert count == 1

        # Verify old entry is deleted
        assert repo.get_marketplace_entry("mkt-old") is None

        # Verify fresh entry still exists
        assert repo.get_marketplace_entry("mkt-fresh") is not None


# =============================================================================
# Transaction Tests
# =============================================================================


class TestTransactionManagement:
    """Tests for transaction management."""

    def test_transaction_commits_on_success(self, repo, sample_project):
        """Test that transaction commits when no errors occur."""
        project_id = sample_project.id

        with repo.transaction() as session:
            session.add(sample_project)

        # Verify project was committed
        retrieved = repo.get_project(project_id)
        assert retrieved is not None
        assert retrieved.id == project_id

    def test_transaction_rollback_on_error(self, repo, sample_project):
        """Test that transaction rolls back on error."""
        try:
            with repo.transaction() as session:
                session.add(sample_project)
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify project was not committed
        retrieved = repo.get_project(sample_project.id)
        assert retrieved is None


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_not_found_error_raised_correctly(self, repo):
        """Test that CacheNotFoundError is raised with correct message."""
        with pytest.raises(CacheNotFoundError) as exc_info:
            repo.update_project("missing-id", status="active")

        assert "missing-id" in str(exc_info.value)

    def test_constraint_error_raised_correctly(self, repo, sample_project):
        """Test that CacheConstraintError is raised for constraint violations."""
        repo.create_project(sample_project)

        # Create a new project with same ID (constraint violation)
        duplicate = Project(
            id=sample_project.id,
            name="Duplicate",
            path="/different/path",
            status="active",
        )

        with pytest.raises(CacheConstraintError) as exc_info:
            repo.create_project(duplicate)

        assert sample_project.id in str(exc_info.value)

    def test_fk_violation_raises_constraint_error(self, repo):
        """Test that foreign key violations raise CacheConstraintError."""
        artifact = Artifact(
            id="art-orphan",
            project_id="nonexistent-project",
            name="orphan",
            type="skill",
        )

        with pytest.raises(CacheConstraintError):
            repo.create_artifact(artifact)


# =============================================================================
# Concurrent Access Tests
# =============================================================================


class TestConcurrentAccess:
    """Tests for concurrent access patterns."""

    def test_concurrent_reads(self, repo, sample_project):
        """Test that concurrent reads work correctly."""
        import threading

        # Create a project
        repo.create_project(sample_project)

        errors = []
        results = []

        def read_project():
            try:
                project = repo.get_project(sample_project.id)
                results.append(project)
            except Exception as e:
                errors.append(str(e))

        # Run 10 concurrent reads
        threads = [threading.Thread(target=read_project) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors and all reads succeeded
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r.id == sample_project.id for r in results)

    def test_concurrent_writes(self, repo, sample_project):
        """Test that concurrent writes are handled correctly."""
        import threading

        repo.create_project(sample_project)

        errors = []

        def create_artifact(artifact_id: int):
            try:
                artifact = Artifact(
                    id=f"art-{artifact_id}",
                    project_id=sample_project.id,
                    name=f"skill-{artifact_id}",
                    type="skill",
                )
                repo.create_artifact(artifact)
            except Exception as e:
                errors.append(str(e))

        # Run 10 concurrent writes
        threads = [
            threading.Thread(target=create_artifact, args=(i,))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0

        # Verify all artifacts were created
        artifacts = repo.list_artifacts_by_project(sample_project.id)
        assert len(artifacts) == 10
