"""Integration tests for rollback atomicity and manifest/lock consistency.

This test suite verifies P0-003 requirements:
- Rollback restores both manifest AND lock files
- Temp workspaces are cleaned up on failure
- Collection remains consistent even when updates fail mid-operation
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import (
    ArtifactManager,
    ArtifactType,
    UpdateFetchResult,
    Artifact,
    ArtifactMetadata,
)
from skillmeat.core.collection import CollectionManager
from skillmeat.sources.base import FetchResult, UpdateInfo


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
            description="A test skill for rollback testing",
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


class TestRollbackOnManifestFailure:
    """Test rollback when manifest save fails after artifact files copied."""

    def test_rollback_restores_both_manifest_and_lock(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify rollback restores both manifest and lock when manifest save fails.

        Scenario:
        1. Start with v1.0.0 artifact
        2. Fetch update to v2.0.0
        3. Apply update with apply_update_strategy()
        4. Inject failure during manifest save
        5. Verify rollback restores both manifest and lock to v1.0.0 state
        """
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Capture initial state
        initial_collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        initial_artifact = initial_collection.find_artifact("test-skill", ArtifactType.SKILL)
        initial_lock = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )

        assert initial_artifact.resolved_version == "v1.0.0"
        assert initial_artifact.resolved_sha == "abc123def456"
        assert initial_lock.resolved_version == "v1.0.0"
        assert initial_lock.resolved_sha == "abc123def456"

        # Create updated artifact
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Test Skill\n\nUpdated version v2.0.0")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="def999abc000",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(
                title="Test Skill",
                version="2.0.0",
            ),
            resolved_sha="def999abc000",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/def999abc000/path/to/test-skill",
        )

        # Prepare fetch result as if fetch_update() succeeded
        fetch_result = UpdateFetchResult(
            artifact=initial_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=updated_fetch,
            temp_workspace=tmp_path / "temp_workspace",
        )

        # Copy updated artifact to temp workspace
        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Track whether save_collection was called
        save_called = False
        original_save = artifact_mgr.collection_mgr.save_collection

        def failing_save(collection):
            nonlocal save_called
            save_called = True
            # This will be called after artifact files are already updated
            raise IOError("Simulated manifest write failure")

        # Don't mock _auto_snapshot - let it create a real snapshot for rollback
        with patch.object(
            artifact_mgr.collection_mgr, "save_collection", side_effect=failing_save
        ):
            # Attempt update - should fail and rollback
            with pytest.raises(IOError, match="Simulated manifest write failure"):
                artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result,
                    strategy="overwrite",
                    interactive=False,
                    collection_name="test-collection",
                )

        # Verify save_collection was actually called (so we know the failure point)
        assert save_called, "save_collection should have been called"

        # Verify rollback: manifest should be restored to v1.0.0
        rolled_back_collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        rolled_back_artifact = rolled_back_collection.find_artifact("test-skill", ArtifactType.SKILL)

        assert rolled_back_artifact.resolved_version == "v1.0.0"
        assert rolled_back_artifact.resolved_sha == "abc123def456"

        # Verify rollback: lock should also be restored to v1.0.0
        rolled_back_lock = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )

        assert rolled_back_lock.resolved_version == "v1.0.0"
        assert rolled_back_lock.resolved_sha == "abc123def456"

        # Verify artifact files also rolled back
        skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        assert skill_file.read_text() == "# Test Skill\n\nInitial version v1.0.0"

        # Verify temp workspace was cleaned up
        assert not fetch_result.temp_workspace.exists()


class TestRollbackOnLockFailure:
    """Test rollback when lock file update fails after manifest succeeds."""

    def test_rollback_when_lock_update_fails(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify rollback when lock file update fails after manifest save.

        Scenario:
        1. Start with v1.0.0
        2. Update artifact files and manifest successfully
        3. Inject failure during lock file update
        4. Verify rollback restores entire state
        """
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Capture initial state
        initial_lock = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )

        # Create updated artifact
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Test Skill\n\nUpdated v2.0.0")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="xyz789",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
            resolved_sha="xyz789",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/xyz789/path/to/test-skill",
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

        # Inject failure during lock update (after manifest saved)
        def failing_lock_update(*args, **kwargs):
            raise PermissionError("Simulated lock file permission error")

        with patch.object(
            artifact_mgr.collection_mgr.lock_mgr,
            "update_entry",
            side_effect=failing_lock_update,
        ):
            with pytest.raises(PermissionError, match="Simulated lock file permission error"):
                artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result,
                    strategy="overwrite",
                    interactive=False,
                    collection_name="test-collection",
                )

        # Verify rollback: both manifest and lock should be v1.0.0
        rolled_back_collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        rolled_back_artifact = rolled_back_collection.find_artifact("test-skill", ArtifactType.SKILL)

        assert rolled_back_artifact.resolved_version == "v1.0.0"

        rolled_back_lock = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )

        assert rolled_back_lock.resolved_version == "v1.0.0"


class TestTempWorkspaceCleanup:
    """Test temp workspace cleanup in all scenarios."""

    def test_temp_workspace_cleaned_on_success(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify temp workspace is cleaned up after successful update."""
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
            temp_workspace=tmp_path / "temp_workspace_success",
        )

        # Copy to temp workspace
        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Perform successful update
        result = artifact_mgr.apply_update_strategy(
            fetch_result=fetch_result,
            strategy="overwrite",
            interactive=False,
            collection_name="test-collection",
        )

        assert result.updated is True

        # Verify temp workspace cleaned up
        assert not fetch_result.temp_workspace.exists()

    def test_temp_workspace_cleaned_on_failure(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify temp workspace is cleaned up even when update fails."""
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="new456",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
            resolved_sha="new456",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/new456/path/to/test-skill",
        )

        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=updated_fetch,
            temp_workspace=tmp_path / "temp_workspace_failure",
        )

        # Copy to temp workspace
        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Inject failure
        def failing_save(collection):
            raise RuntimeError("Update failure for cleanup test")

        with patch.object(
            artifact_mgr.collection_mgr, "save_collection", side_effect=failing_save
        ):
            with pytest.raises(RuntimeError):
                artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result,
                    strategy="overwrite",
                    interactive=False,
                    collection_name="test-collection",
                )

        # Verify temp workspace cleaned up even on failure
        assert not fetch_result.temp_workspace.exists()


class TestConsistencyGuarantees:
    """Test that manifest and lock are always consistent."""

    def test_manifest_lock_never_diverge(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify manifest and lock never diverge, even with failures.

        Test multiple failure scenarios and ensure consistency.
        """
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Helper to check consistency
        def verify_consistency():
            collection = artifact_mgr.collection_mgr.load_collection("test-collection")
            artifact = collection.find_artifact("test-skill", ArtifactType.SKILL)
            lock_entry = artifact_mgr.collection_mgr.lock_mgr.get_entry(
                collection_path, "test-skill", ArtifactType.SKILL
            )

            # Both must exist
            assert artifact is not None
            assert lock_entry is not None

            # Versions must match
            assert artifact.resolved_version == lock_entry.resolved_version
            assert artifact.resolved_sha == lock_entry.resolved_sha

            return artifact.resolved_version

        # Check initial consistency
        initial_version = verify_consistency()
        assert initial_version == "v1.0.0"

        # Attempt update with failure
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="fail123",
            current_version="v1.0.0",
            latest_version="v2.0.0",
            has_update=True,
        )

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
            resolved_sha="fail123",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/fail123/path/to/test-skill",
        )

        fetch_result = UpdateFetchResult(
            artifact=github_artifact,
            has_update=True,
            update_info=update_info,
            fetch_result=updated_fetch,
            temp_workspace=tmp_path / "temp_workspace_consistency",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Inject failure
        with patch.object(
            artifact_mgr.collection_mgr.lock_mgr,
            "update_entry",
            side_effect=IOError("Lock write failed"),
        ):
            with pytest.raises(IOError):
                artifact_mgr.apply_update_strategy(
                    fetch_result=fetch_result,
                    strategy="overwrite",
                    interactive=False,
                    collection_name="test-collection",
                )

        # Verify consistency maintained after rollback
        rolled_back_version = verify_consistency()
        assert rolled_back_version == initial_version == "v1.0.0"
