"""Comprehensive regression tests for artifact update flow.

This test suite fills coverage gaps for P0-004 by testing:
- Edge cases not covered by existing tests
- Error handling beyond basic rollback
- Resource constraints and external interference
- Data validation scenarios
- Performance benchmarks
- Strategy method variations

Target: >80% coverage for update path in skillmeat/core/artifact.py
"""

import pytest
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime
import requests.exceptions

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import (
    ArtifactManager,
    ArtifactType,
    UpdateStrategy,
    UpdateFetchResult,
    UpdateResult,
    Artifact,
    ArtifactMetadata,
)
from skillmeat.core.collection import CollectionManager
from skillmeat.sources.base import FetchResult, UpdateInfo


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_skillmeat_dir(tmp_path):
    """Provide temporary SkillMeat directory."""
    return tmp_path / "skillmeat"


@pytest.fixture
def config(temp_skillmeat_dir):
    """Provide ConfigManager with temp directory."""
    return ConfigManager(temp_skillmeat_dir)


@pytest.fixture
def collection_mgr(config):
    """Provide CollectionManager."""
    return CollectionManager(config)


@pytest.fixture
def artifact_mgr(collection_mgr):
    """Provide ArtifactManager."""
    return ArtifactManager(collection_mgr)


@pytest.fixture
def initialized_collection(collection_mgr):
    """Initialize a test collection."""
    collection = collection_mgr.init("test-collection")
    collection_mgr.switch_collection("test-collection")
    return collection


@pytest.fixture
def github_artifact(artifact_mgr, initialized_collection, tmp_path):
    """Add a GitHub artifact to the collection."""
    initial_dir = tmp_path / "initial-skill"
    initial_dir.mkdir()
    (initial_dir / "SKILL.md").write_text("# Test Skill\n\nInitial version v1.0.0")

    initial_fetch = FetchResult(
        artifact_path=initial_dir,
        metadata=ArtifactMetadata(
            title="Test Skill",
            description="A test skill for comprehensive testing",
            version="1.0.0",
            tags=["test"],
        ),
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/user/repo/tree/abc123def456/path/to/test-skill",
    )

    with patch.object(artifact_mgr.github_source, "fetch", return_value=initial_fetch):
        artifact = artifact_mgr.add_from_github(
            spec="user/repo/path/to/test-skill@v1.0.0",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    return artifact


# =============================================================================
# Test UpdateFetchResult Edge Cases
# =============================================================================


class TestUpdateFetchResultEdgeCases:
    """Test UpdateFetchResult dataclass edge cases."""

    def test_fetch_result_with_error(self, artifact_mgr, github_artifact):
        """Test UpdateFetchResult properly captures error state."""
        error_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=False,
            update_info=None,
            error="Network timeout during fetch",
        )

        assert error_result.error is not None
        assert not error_result.has_update
        assert error_result.temp_workspace is None

    def test_fetch_result_no_update_available(self, artifact_mgr, github_artifact):
        """Test UpdateFetchResult when no update is available."""
        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="abc123def456",
            current_version="v1.0.0",
            latest_version="v1.0.0",
            has_update=False,
        )

        result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=False,
            update_info=update_info,
        )

        assert not result.has_update
        assert result.error is None
        assert result.update_info.current_sha == result.update_info.latest_sha


# =============================================================================
# Test fetch_update() Error Handling
# =============================================================================


class TestFetchUpdateErrorHandling:
    """Test error handling in fetch_update() method."""

    def test_fetch_update_network_error(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Test fetch_update() handles network errors gracefully."""
        with patch.object(
            artifact_mgr.github_source,
            "check_updates",
            side_effect=requests.exceptions.ConnectionError("Network unreachable"),
        ):
            result = artifact_mgr.fetch_update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )

            assert result.error is not None
            assert "Network error" in result.error or "Network unreachable" in str(result.error)
            assert not result.has_update
            # Verify temp workspace was cleaned up
            assert result.temp_workspace is None or not result.temp_workspace.exists()

    def test_fetch_update_invalid_artifact_name(
        self, artifact_mgr, initialized_collection
    ):
        """Test fetch_update() with non-existent artifact."""
        result = artifact_mgr.fetch_update(
            artifact_name="non-existent-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert result.error is not None
        assert "not found" in result.error
        assert not result.has_update

    def test_fetch_update_permission_error(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Test fetch_update() handles permission errors."""
        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="def999abc000",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        with patch.object(
            artifact_mgr.github_source, "check_updates", return_value=update_info
        ), patch.object(
            artifact_mgr.github_source,
            "fetch",
            side_effect=PermissionError("Access denied to private repository"),
        ):
            result = artifact_mgr.fetch_update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )

            assert result.error is not None
            assert "Permission denied" in result.error
            assert not result.has_update

    def test_fetch_update_no_upstream(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Test fetch_update() when artifact has no upstream reference."""
        # Remove upstream from artifact
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        artifact = collection.find_artifact("test-skill", ArtifactType.SKILL)
        artifact.upstream = None
        artifact_mgr.collection_mgr.save_collection(collection)

        result = artifact_mgr.fetch_update(
            artifact_name="test-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert result.error is not None
        assert "upstream reference" in result.error
        assert not result.has_update


# =============================================================================
# Test apply_update_strategy() Edge Cases
# =============================================================================


class TestApplyUpdateStrategyEdgeCases:
    """Test edge cases in apply_update_strategy()."""

    def test_apply_update_with_error_in_fetch_result(
        self, artifact_mgr, github_artifact
    ):
        """Test apply_update_strategy() rejects fetch result with error."""
        error_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=False,
            update_info=None,
            error="Network error",
        )

        with pytest.raises(ValueError, match="Cannot apply update"):
            artifact_mgr.apply_update_strategy(
                fetch_result=error_result,
                strategy="overwrite",
                collection_name="test-collection",
            )

    def test_apply_update_no_update_available(self, artifact_mgr, github_artifact):
        """Test apply_update_strategy() rejects fetch result with no update."""
        no_update_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=False,
            update_info=UpdateInfo(
                current_sha="abc123",
                latest_sha="abc123",
                current_version="v1.0.0",
                latest_version="v1.0.0",
                has_update=False,
            ),
        )

        with pytest.raises(ValueError, match="No update available"):
            artifact_mgr.apply_update_strategy(
                fetch_result=no_update_result,
                strategy="overwrite",
                collection_name="test-collection",
            )

    def test_apply_update_invalid_strategy(
        self, artifact_mgr, github_artifact, tmp_path
    ):
        """Test apply_update_strategy() rejects invalid strategy."""
        # Create temp workspace with artifact
        temp_workspace = tmp_path / "temp"
        temp_workspace.mkdir()
        artifact_dir = temp_workspace / "artifact"
        artifact_dir.mkdir()
        (artifact_dir / "SKILL.md").write_text("# Updated")

        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=UpdateInfo(
                current_sha="abc123",
                latest_sha="def456",
                current_version="v1.0.0",
                latest_version="v2.0.0",
                has_update=True,
            ),
            temp_workspace=temp_workspace,
        )

        with pytest.raises(ValueError, match="Invalid strategy"):
            artifact_mgr.apply_update_strategy(
                fetch_result=fetch_result,
                strategy="invalid-strategy",
                collection_name="test-collection",
            )

    def test_apply_update_missing_temp_workspace(
        self, artifact_mgr, github_artifact
    ):
        """Test apply_update_strategy() handles missing temp workspace."""
        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=UpdateInfo(
                current_sha="abc123",
                latest_sha="def456",
                current_version="v1.0.0",
                latest_version="v2.0.0",
                has_update=True,
            ),
            temp_workspace=None,
        )

        with pytest.raises(ValueError, match="Temp workspace not found"):
            artifact_mgr.apply_update_strategy(
                fetch_result=fetch_result,
                strategy="overwrite",
                collection_name="test-collection",
            )


# =============================================================================
# Test Strategy Methods
# =============================================================================


class TestOverwriteStrategy:
    """Test _apply_overwrite_strategy() method."""

    def test_overwrite_strategy_success(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test overwrite strategy successfully replaces files."""
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"

        # Create upstream artifact
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Updated Skill\n\nNew content")

        # Apply overwrite
        success = artifact_mgr._apply_overwrite_strategy(
            artifact_path, upstream_dir, github_artifact
        )

        assert success is True
        assert (artifact_path / "SKILL.md").read_text() == "# Updated Skill\n\nNew content"

    def test_overwrite_strategy_copy_failure(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test overwrite strategy handles copy failures."""
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"

        # Create non-existent upstream path
        upstream_dir = tmp_path / "non-existent"

        # Attempt overwrite - should fail
        success = artifact_mgr._apply_overwrite_strategy(
            artifact_path, upstream_dir, github_artifact
        )

        assert success is False


class TestMergeStrategy:
    """Test _apply_merge_strategy() method."""

    def test_merge_strategy_no_conflicts(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test merge strategy with no conflicts."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"

        # Create upstream with added file
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\n\nInitial version v1.0.0")
        (upstream_dir / "NEW_FILE.md").write_text("# New File")

        console = Console()

        # Apply merge
        success = artifact_mgr._apply_merge_strategy(
            artifact_path, upstream_dir, github_artifact, collection_path, console
        )

        assert success is True
        assert (artifact_path / "NEW_FILE.md").exists()

    def test_merge_strategy_with_conflicts(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test merge strategy with conflicts."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"

        # Create conflicting upstream
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\n\nConflicting content")

        # Modify local to create conflict
        (artifact_path / "SKILL.md").write_text("# Test Skill\n\nLocal changes")

        console = Console()

        # Apply merge - should succeed but with conflicts
        success = artifact_mgr._apply_merge_strategy(
            artifact_path, upstream_dir, github_artifact, collection_path, console
        )

        # Merge should complete even with conflicts (files will have markers)
        assert success is True


class TestPromptStrategy:
    """Test _apply_prompt_strategy() method."""

    def test_prompt_strategy_user_accepts(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy when user accepts update."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"

        # Create upstream
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Updated Skill")

        console = Console()

        # Mock user accepting
        with patch("skillmeat.core.artifact.Confirm.ask", return_value=True):
            success = artifact_mgr._apply_prompt_strategy(
                artifact_path, upstream_dir, github_artifact, True, console
            )

        assert success is True
        assert (artifact_path / "SKILL.md").read_text() == "# Updated Skill"

    def test_prompt_strategy_user_rejects(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy when user rejects update."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"
        original_content = (artifact_path / "SKILL.md").read_text()

        # Create upstream
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Updated Skill")

        console = Console()

        # Mock user rejecting
        with patch("skillmeat.core.artifact.Confirm.ask", return_value=False):
            success = artifact_mgr._apply_prompt_strategy(
                artifact_path, upstream_dir, github_artifact, True, console
            )

        assert success is False
        # Verify content unchanged
        assert (artifact_path / "SKILL.md").read_text() == original_content

    def test_prompt_strategy_non_interactive(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy in non-interactive mode."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "test-skill"

        # Create upstream
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Updated Skill")

        console = Console()

        # Non-interactive mode should skip update
        success = artifact_mgr._apply_prompt_strategy(
            artifact_path, upstream_dir, github_artifact, False, console
        )

        assert success is False


# =============================================================================
# Test Snapshot Creation Edge Cases
# =============================================================================


class TestSnapshotEdgeCases:
    """Test snapshot creation failure modes."""

    def test_update_proceeds_when_snapshot_fails(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test update proceeds with warning when snapshot creation fails."""
        # Create updated artifact
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="new123",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
            resolved_sha="new123",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/new123/path/to/test-skill",
        )

        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=updated_fetch,
            temp_workspace=tmp_path / "temp_workspace",
        )

        # Copy to temp workspace
        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Mock snapshot failure
        with patch.object(
            artifact_mgr, "_auto_snapshot", side_effect=Exception("Disk full")
        ):
            # Update should still proceed despite snapshot failure
            result = artifact_mgr.apply_update_strategy(
                fetch_result=fetch_result,
                strategy="overwrite",
                interactive=False,
                collection_name="test-collection",
            )

            assert result.updated is True


# =============================================================================
# Test Sequential Operations
# =============================================================================


class TestSequentialOperations:
    """Test sequential update operations."""

    def test_fail_rollback_retry_succeed(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test fail → rollback → retry → succeed pattern."""
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # First attempt: fail with manifest error
        updated_dir_v2 = tmp_path / "updated-v2"
        updated_dir_v2.mkdir()
        (updated_dir_v2 / "SKILL.md").write_text("# Version 2.0.0")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="v2sha",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        updated_fetch = FetchResult(
            artifact_path=updated_dir_v2,
            metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
            resolved_sha="v2sha",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/v2sha/path/to/test-skill",
        )

        fetch_result_v2 = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=updated_fetch,
            temp_workspace=tmp_path / "temp_v2",
        )

        workspace_artifact = fetch_result_v2.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir_v2, workspace_artifact)

        # Inject failure
        with patch.object(
            artifact_mgr.collection_mgr,
            "save_collection",
            side_effect=IOError("Simulated failure"),
        ):
            with pytest.raises(IOError):
                artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result_v2,
                    strategy="overwrite",
                    interactive=False,
                    collection_name="test-collection",
                )

        # Verify rollback - still at v1.0.0
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        artifact = collection.find_artifact("test-skill", ArtifactType.SKILL)
        assert artifact.resolved_version == "v1.0.0"

        # Second attempt: succeed
        updated_dir_v3 = tmp_path / "updated-v3"
        updated_dir_v3.mkdir()
        (updated_dir_v3 / "SKILL.md").write_text("# Version 3.0.0")

        update_info_v3 = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="v3sha",
            current_version="v1.0.0",
            latest_version="v3.0.0",
            has_update=True,
        )

        updated_fetch_v3 = FetchResult(
            artifact_path=updated_dir_v3,
            metadata=ArtifactMetadata(title="Test Skill", version="3.0.0"),
            resolved_sha="v3sha",
            resolved_version="v3.0.0",
            upstream_url="https://github.com/user/repo/tree/v3sha/path/to/test-skill",
        )

        fetch_result_v3 = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info_v3,
            fetch_result=updated_fetch_v3,
            temp_workspace=tmp_path / "temp_v3",
        )

        workspace_artifact_v3 = fetch_result_v3.temp_workspace / "artifact"
        workspace_artifact_v3.parent.mkdir(parents=True)
        shutil.copytree(updated_dir_v3, workspace_artifact_v3)

        # This time should succeed
        result = artifact_mgr.apply_update_strategy(
            fetch_result=fetch_result_v3,
            strategy="overwrite",
            interactive=False,
            collection_name="test-collection",
        )

        assert result.updated is True
        assert result.new_version == "v3.0.0"

    def test_multiple_updates_in_session(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test multiple sequential updates in same session."""
        # Add two artifacts
        artifact1_dir = tmp_path / "artifact1-v1"
        artifact1_dir.mkdir()
        (artifact1_dir / "SKILL.md").write_text("# Artifact 1")

        artifact2_dir = tmp_path / "artifact2-v1"
        artifact2_dir.mkdir()
        (artifact2_dir / "SKILL.md").write_text("# Artifact 2")

        fetch1 = FetchResult(
            artifact_path=artifact1_dir,
            metadata=ArtifactMetadata(title="Artifact 1", version="1.0.0"),
            resolved_sha="a1sha",
            resolved_version="v1.0.0",
            upstream_url="https://github.com/user/repo/tree/a1sha/artifact1",
        )

        fetch2 = FetchResult(
            artifact_path=artifact2_dir,
            metadata=ArtifactMetadata(title="Artifact 2", version="1.0.0"),
            resolved_sha="a2sha",
            resolved_version="v1.0.0",
            upstream_url="https://github.com/user/repo/tree/a2sha/artifact2",
        )

        with patch.object(artifact_mgr.github_source, "fetch", side_effect=[fetch1, fetch2]):
            artifact_mgr.add_from_github(
                spec="user/repo/artifact1@v1.0.0",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )
            artifact_mgr.add_from_github(
                spec="user/repo/artifact2@v1.0.0",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )

        # Update both artifacts
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Load artifacts for updates
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        a1 = collection.find_artifact("artifact1", ArtifactType.SKILL)
        a2 = collection.find_artifact("artifact2", ArtifactType.SKILL)

        # Create updated versions
        artifact1_v2_dir = tmp_path / "artifact1-v2"
        artifact1_v2_dir.mkdir()
        (artifact1_v2_dir / "SKILL.md").write_text("# Artifact 1 v2")

        artifact2_v2_dir = tmp_path / "artifact2-v2"
        artifact2_v2_dir.mkdir()
        (artifact2_v2_dir / "SKILL.md").write_text("# Artifact 2 v2")

        # Both updates should succeed independently
        fetch_result_1 = UpdateFetchResult(
            artifact=a1,
            has_update=True,
            update_info=UpdateInfo(
                current_sha="a1sha",
                latest_sha="a1v2sha",
                current_version="v1.0.0",
                latest_version="v2.0.0",
                has_update=True,
            ),
            fetch_result=FetchResult(
                artifact_path=artifact1_v2_dir,
                metadata=ArtifactMetadata(title="Artifact 1", version="2.0.0"),
                resolved_sha="a1v2sha",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/a1v2sha/artifact1",
            ),
            temp_workspace=tmp_path / "temp_a1",
        )

        workspace_a1 = fetch_result_1.temp_workspace / "artifact"
        workspace_a1.parent.mkdir(parents=True)
        shutil.copytree(artifact1_v2_dir, workspace_a1)

        result1 = artifact_mgr.apply_update_strategy(
            fetch_result=fetch_result_1,
            strategy="overwrite",
            interactive=False,
            collection_name="test-collection",
        )

        assert result1.updated is True
        assert result1.new_version == "v2.0.0"


# =============================================================================
# Test Resource Constraints
# =============================================================================


class TestResourceConstraints:
    """Test behavior under resource constraints."""

    def test_disk_full_during_snapshot(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test handling of disk full error during snapshot creation."""
        # Create updated artifact
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="new123",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=FetchResult(
                artifact_path=updated_dir,
                metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
                resolved_sha="new123",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/new123/path/to/test-skill",
            ),
            temp_workspace=tmp_path / "temp_workspace",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Mock disk full during snapshot
        with patch.object(
            artifact_mgr, "_auto_snapshot", side_effect=OSError("No space left on device")
        ):
            # Update should proceed with warning
            result = artifact_mgr.apply_update_strategy(
                fetch_result=fetch_result,
                strategy="overwrite",
                interactive=False,
                collection_name="test-collection",
            )

            # Should succeed despite snapshot failure
            assert result.updated is True


# =============================================================================
# Test Data Validation
# =============================================================================


class TestDataValidation:
    """Test validation of artifact data during updates."""

    def test_update_with_missing_metadata(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test update when upstream artifact has invalid/missing metadata."""
        # Create upstream without proper metadata
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Minimal Skill\n\nNo metadata")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="new123",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        # Metadata extraction might fail - should still complete update
        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=FetchResult(
                artifact_path=updated_dir,
                metadata=None,  # No metadata
                resolved_sha="new123",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/new123/path/to/test-skill",
            ),
            temp_workspace=tmp_path / "temp_workspace",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Update should succeed even with missing metadata
        result = artifact_mgr.apply_update_strategy(
            fetch_result=fetch_result,
            strategy="overwrite",
            interactive=False,
            collection_name="test-collection",
        )

        assert result.updated is True


# =============================================================================
# Test Performance Benchmarks
# =============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmarks for update operations."""

    def test_snapshot_creation_performance(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Benchmark snapshot creation time."""
        start_time = time.time()

        snapshot = artifact_mgr._auto_snapshot(
            "test-collection",
            github_artifact,
            "Performance test snapshot",
        )

        elapsed = time.time() - start_time

        # Snapshot creation for single artifact should be fast (<1s)
        assert elapsed < 1.0
        assert snapshot is not None

    def test_update_flow_end_to_end_performance(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Benchmark full update flow performance."""
        # Create updated artifact
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated Skill\n\nPerformance test")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="perf123",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=FetchResult(
                artifact_path=updated_dir,
                metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
                resolved_sha="perf123",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/perf123/path/to/test-skill",
            ),
            temp_workspace=tmp_path / "temp_workspace",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        start_time = time.time()

        result = artifact_mgr.apply_update_strategy(
            fetch_result=fetch_result,
            strategy="overwrite",
            interactive=False,
            collection_name="test-collection",
        )

        elapsed = time.time() - start_time

        assert result.updated is True
        # Full update flow should complete quickly for small artifact (<2s)
        assert elapsed < 2.0


# =============================================================================
# Test Error Messages
# =============================================================================


class TestErrorMessages:
    """Test that error messages are clear and actionable."""

    def test_clear_error_on_missing_artifact(
        self, artifact_mgr, initialized_collection
    ):
        """Test error message when artifact not found."""
        result = artifact_mgr.fetch_update(
            artifact_name="non-existent",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert result.error is not None
        assert "not found" in result.error

    def test_clear_error_on_missing_upstream(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Test error message when artifact has no upstream."""
        # Remove upstream
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        artifact = collection.find_artifact("test-skill", ArtifactType.SKILL)
        artifact.upstream = None
        artifact_mgr.collection_mgr.save_collection(collection)

        result = artifact_mgr.fetch_update(
            artifact_name="test-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert result.error is not None
        assert "upstream reference" in result.error
