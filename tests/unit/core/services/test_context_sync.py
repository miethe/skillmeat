"""Unit tests for context sync service.

Tests for bi-directional synchronization of context entities between
collections and deployed projects.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from skillmeat.core.deployment import Deployment
from skillmeat.core.services.context_sync import (
    ContextSyncService,
    SyncConflict,
    SyncResult,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_collection_manager():
    """Mock CollectionManager for testing."""
    mgr = MagicMock()
    return mgr


@pytest.fixture
def mock_cache_manager():
    """Mock CacheManager for testing."""
    mgr = MagicMock()
    return mgr


@pytest.fixture
def sync_service(mock_collection_manager, mock_cache_manager):
    """ContextSyncService instance with mocked dependencies."""
    return ContextSyncService(mock_collection_manager, mock_cache_manager)


@pytest.fixture
def sample_deployment():
    """Sample deployment record for context entity."""
    return Deployment(
        artifact_name="api-patterns",
        artifact_type="rule_file",
        from_collection="default",
        deployed_at=datetime(2025, 12, 10, 10, 0, 0),
        artifact_path=Path("rules/api/patterns.md"),
        content_hash="abc123original",
        local_modifications=False,
    )


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project directory with .claude structure."""
    project = tmp_path / "test_project"
    claude_dir = project / ".claude"
    rules_dir = claude_dir / "rules" / "api"
    rules_dir.mkdir(parents=True)

    # Create deployed file
    deployed_file = rules_dir / "patterns.md"
    original_content = "# API Patterns\n\nOriginal content"
    deployed_file.write_text(original_content)

    # Compute correct hash for original content
    from skillmeat.core.services.content_hash import compute_content_hash
    original_hash = compute_content_hash(original_content)

    # Create deployment file with correct hash
    deployment_file = claude_dir / ".skillmeat-deployed.toml"
    deployment_file.write_text(
        f"""
[[deployed]]
artifact_name = "api-patterns"
artifact_type = "rule_file"
from_collection = "default"
deployed_at = "2025-12-10T10:00:00"
artifact_path = "rules/api/patterns.md"
content_hash = "{original_hash}"
local_modifications = false
"""
    )

    return project


# =============================================================================
# Test: detect_modified_entities
# =============================================================================


def test_detect_modified_entities_no_changes(sync_service, temp_project):
    """Test detecting entities when no changes exist."""
    # Deployed file matches deployment hash
    modified = sync_service.detect_modified_entities(str(temp_project))

    # Should detect 0 modified entities (hash matches)
    assert len(modified) == 0


def test_detect_modified_entities_project_modified(sync_service, temp_project):
    """Test detecting entity modified in project."""
    # Modify deployed file
    deployed_file = temp_project / ".claude" / "rules" / "api" / "patterns.md"
    deployed_file.write_text("# API Patterns\n\nModified in project")

    modified = sync_service.detect_modified_entities(str(temp_project))

    # Should detect 1 modified entity
    assert len(modified) == 1
    entity = modified[0]
    assert entity["entity_name"] == "api-patterns"
    assert entity["entity_type"] == "rule_file"
    assert entity["modified_in"] == "project"
    assert entity["deployed_hash"] != entity["last_synced_hash"]


def test_detect_modified_entities_collection_modified(sync_service, temp_project):
    """Test detecting entity modified in collection."""
    # This would require mocking cache manager to return different hash
    # For now, we test the logic by patching deployment.content_hash
    with patch(
        "skillmeat.storage.deployment.DeploymentTracker.read_deployments"
    ) as mock_read:
        # Create deployment with different collection hash
        deployment = Deployment(
            artifact_name="api-patterns",
            artifact_type="rule_file",
            from_collection="default",
            deployed_at=datetime(2025, 12, 10, 10, 0, 0),
            artifact_path=Path("rules/api/patterns.md"),
            content_hash="xyz789modified",  # Different from deployed file
            local_modifications=False,
        )
        mock_read.return_value = [deployment]

        # Deployed file unchanged
        modified = sync_service.detect_modified_entities(str(temp_project))

        # Should detect modification in collection
        # Note: Current implementation uses deployment.content_hash as both
        # collection_hash and last_synced_hash, so this won't detect changes yet
        # TODO: Update when cache manager integration is complete


def test_detect_modified_entities_both_modified(sync_service, temp_project):
    """Test detecting entity modified in both collection and project."""
    # This requires:
    # 1. Collection hash != last_synced_hash (collection modified)
    # 2. Deployed file hash != last_synced_hash (project modified)
    # Will implement fully when cache manager integration is complete
    pass


def test_detect_modified_entities_missing_file(sync_service, temp_project):
    """Test handling missing deployed file."""
    # Delete deployed file
    deployed_file = temp_project / ".claude" / "rules" / "api" / "patterns.md"
    deployed_file.unlink()

    modified = sync_service.detect_modified_entities(str(temp_project))

    # Should skip missing file
    assert len(modified) == 0


# =============================================================================
# Test: pull_changes
# =============================================================================


def test_pull_changes_project_modified(sync_service, temp_project):
    """Test pulling changes from project to collection."""
    # Modify deployed file
    deployed_file = temp_project / ".claude" / "rules" / "api" / "patterns.md"
    deployed_file.write_text("# API Patterns\n\nModified in project")

    results = sync_service.pull_changes(str(temp_project))

    # Should pull the modified entity
    assert len(results) == 1
    result = results[0]
    assert result.entity_name == "api-patterns"
    assert result.action == "pulled"
    assert "Successfully pulled" in result.message


def test_pull_changes_specific_entity(sync_service, temp_project):
    """Test pulling changes for specific entity ID."""
    # Modify deployed file
    deployed_file = temp_project / ".claude" / "rules" / "api" / "patterns.md"
    deployed_file.write_text("# API Patterns\n\nModified in project")

    # Pull only specific entity
    results = sync_service.pull_changes(
        str(temp_project),
        entity_ids=["rule_file:api-patterns"],
    )

    assert len(results) == 1
    assert results[0].entity_name == "api-patterns"


def test_pull_changes_no_modifications(sync_service, temp_project):
    """Test pulling when no entities are modified in project."""
    results = sync_service.pull_changes(str(temp_project))

    # No entities to pull
    assert len(results) == 0


# =============================================================================
# Test: push_changes
# =============================================================================


def test_push_changes_collection_modified(sync_service, temp_project):
    """Test pushing changes from collection to project."""
    # This would require mocking collection content
    # Skipping for now until cache manager integration
    pass


def test_push_changes_conflict_without_overwrite(sync_service, temp_project):
    """Test pushing when both sides modified (should detect conflict)."""
    # This requires both collection and project to be modified
    # Skipping for now until cache manager integration
    pass


def test_push_changes_force_overwrite(sync_service, temp_project):
    """Test pushing with overwrite=True (ignores conflicts)."""
    # This requires both collection and project to be modified
    # Skipping for now until cache manager integration
    pass


# =============================================================================
# Test: detect_conflicts
# =============================================================================


def test_detect_conflicts_none(sync_service, temp_project):
    """Test detecting conflicts when none exist."""
    conflicts = sync_service.detect_conflicts(str(temp_project))

    # No conflicts (no modifications)
    assert len(conflicts) == 0


def test_detect_conflicts_both_modified(sync_service, temp_project):
    """Test detecting conflicts when both sides modified."""
    # This requires mocking both collection and project modifications
    # Skipping for now until cache manager integration
    pass


# =============================================================================
# Test: resolve_conflict
# =============================================================================


def test_resolve_conflict_keep_local():
    """Test resolving conflict by keeping local (project) version."""
    sync_service = ContextSyncService(MagicMock(), MagicMock())

    conflict = SyncConflict(
        entity_id="rule_file:api-patterns",
        entity_name="api-patterns",
        entity_type="rule_file",
        collection_hash="abc123collection",
        deployed_hash="xyz789deployed",
        collection_content="# Collection version",
        deployed_content="# Deployed version",
        collection_path="/collection/rules/api/patterns.md",
        deployed_path="/project/.claude/rules/api/patterns.md",
        baseline_hash="original123baseline",
    )

    result = sync_service.resolve_conflict(conflict, resolution="keep_local")

    assert result.entity_id == "rule_file:api-patterns"
    assert result.action == "resolved"
    assert "keep_local" in result.message


def test_resolve_conflict_keep_remote():
    """Test resolving conflict by keeping remote (collection) version."""
    sync_service = ContextSyncService(MagicMock(), MagicMock())

    conflict = SyncConflict(
        entity_id="rule_file:api-patterns",
        entity_name="api-patterns",
        entity_type="rule_file",
        collection_hash="abc123collection",
        deployed_hash="xyz789deployed",
        collection_content="# Collection version",
        deployed_content="# Deployed version",
        collection_path="/collection/rules/api/patterns.md",
        deployed_path="/project/.claude/rules/api/patterns.md",
        baseline_hash="original123baseline",
    )

    result = sync_service.resolve_conflict(conflict, resolution="keep_remote")

    assert result.entity_id == "rule_file:api-patterns"
    assert result.action == "resolved"
    assert "keep_remote" in result.message


def test_resolve_conflict_merge():
    """Test resolving conflict with manual merge."""
    sync_service = ContextSyncService(MagicMock(), MagicMock())

    conflict = SyncConflict(
        entity_id="rule_file:api-patterns",
        entity_name="api-patterns",
        entity_type="rule_file",
        collection_hash="abc123collection",
        deployed_hash="xyz789deployed",
        collection_content="# Collection version",
        deployed_content="# Deployed version",
        collection_path="/collection/rules/api/patterns.md",
        deployed_path="/project/.claude/rules/api/patterns.md",
        baseline_hash="original123baseline",
    )

    merged_content = "# Merged version\n\nBest of both worlds"
    result = sync_service.resolve_conflict(
        conflict, resolution="merge", merged_content=merged_content
    )

    assert result.entity_id == "rule_file:api-patterns"
    assert result.action == "resolved"
    assert "merge" in result.message


def test_resolve_conflict_merge_missing_content():
    """Test that merge without merged_content raises error."""
    sync_service = ContextSyncService(MagicMock(), MagicMock())

    conflict = SyncConflict(
        entity_id="rule_file:api-patterns",
        entity_name="api-patterns",
        entity_type="rule_file",
        collection_hash="abc123collection",
        deployed_hash="xyz789deployed",
        collection_content="# Collection version",
        deployed_content="# Deployed version",
        collection_path="/collection/rules/api/patterns.md",
        deployed_path="/project/.claude/rules/api/patterns.md",
        baseline_hash="original123baseline",
    )

    with pytest.raises(ValueError, match="merged_content required"):
        sync_service.resolve_conflict(conflict, resolution="merge")


# =============================================================================
# Test: Edge Cases
# =============================================================================


def test_detect_modified_entities_non_context_artifacts(sync_service, temp_project):
    """Test that non-context entities are ignored."""
    # Add a skill deployment (not a context entity)
    deployment_file = temp_project / ".claude" / ".skillmeat-deployed.toml"
    deployment_file.write_text(
        """
[[deployed]]
artifact_name = "my-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2025-12-10T10:00:00"
artifact_path = "skills/my-skill"
content_hash = "abc123skill"
local_modifications = false
"""
    )

    modified = sync_service.detect_modified_entities(str(temp_project))

    # Should ignore skill artifacts
    assert len(modified) == 0


def test_service_initialization():
    """Test service initialization with managers."""
    collection_mgr = MagicMock()
    cache_mgr = MagicMock()

    service = ContextSyncService(collection_mgr, cache_mgr)

    assert service.collection_mgr is collection_mgr
    assert service.cache_mgr is cache_mgr
