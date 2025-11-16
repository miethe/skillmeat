"""Additional edge case tests to achieve >80% coverage for update path."""

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
    return tmp_path / "skillmeat"


@pytest.fixture
def config(temp_skillmeat_dir):
    return ConfigManager(temp_skillmeat_dir)


@pytest.fixture
def collection_mgr(config):
    return CollectionManager(config)


@pytest.fixture
def artifact_mgr(collection_mgr):
    return ArtifactManager(collection_mgr)


@pytest.fixture
def initialized_collection(collection_mgr):
    collection = collection_mgr.init("test-collection")
    collection_mgr.switch_collection("test-collection")
    return collection


@pytest.fixture
def github_artifact(artifact_mgr, initialized_collection, tmp_path):
    initial_dir = tmp_path / "initial-skill"
    initial_dir.mkdir()
    (initial_dir / "SKILL.md").write_text("# Test Skill\n\nInitial")

    initial_fetch = FetchResult(
        artifact_path=initial_dir,
        metadata=ArtifactMetadata(
            title="Test Skill",
            version="1.0.0",
        ),
        resolved_sha="abc123",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/user/repo/tree/abc123/path/to/skill",
    )

    with patch.object(artifact_mgr.github_source, "fetch", return_value=initial_fetch):
        artifact = artifact_mgr.add_from_github(
            spec="user/repo/path/to/skill@v1.0.0",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    return artifact


class TestMergeStrategyErrorHandling:
    """Test error handling in merge strategy."""

    def test_merge_strategy_merge_engine_exception(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test merge strategy when MergeEngine raises exception."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "skill"

        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Updated")

        console = Console()

        # Mock merge engine to raise exception (it's imported inside the method)
        with patch("skillmeat.core.merge_engine.MergeEngine") as mock_merge_engine_class:
            mock_engine = MagicMock()
            mock_engine.merge.side_effect = Exception("Merge engine internal error")
            mock_merge_engine_class.return_value = mock_engine

            success = artifact_mgr._apply_merge_strategy(
                artifact_path, upstream_dir, github_artifact, collection_path, console
            )

            assert success is False


class TestPromptStrategyErrorHandling:
    """Test error handling in prompt strategy."""

    def test_prompt_strategy_diff_engine_exception(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy when DiffEngine raises exception."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "skill"

        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Updated")

        console = Console()

        # Mock diff engine to raise exception (it's imported inside the method)
        with patch("skillmeat.core.diff_engine.DiffEngine") as mock_diff_class:
            mock_diff = MagicMock()
            mock_diff.diff_directories.side_effect = Exception("Diff engine error")
            mock_diff_class.return_value = mock_diff

            success = artifact_mgr._apply_prompt_strategy(
                artifact_path, upstream_dir, github_artifact, True, console
            )

            assert success is False


class TestMetadataExtractionFailure:
    """Test handling of metadata extraction failures."""

    def test_update_metadata_extraction_failure(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test update when metadata extraction fails."""
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123",
            latest_sha="def456",
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
                metadata=ArtifactMetadata(title="Test", version="2.0.0"),
                resolved_sha="def456",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/def456/path/to/skill",
            ),
            temp_workspace=tmp_path / "temp_workspace",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Mock metadata extraction to fail (imported inside the method from utils.metadata)
        with patch(
            "skillmeat.utils.metadata.extract_artifact_metadata",
            side_effect=Exception("Metadata extraction failed"),
        ):
            # Update should still succeed despite metadata extraction failure
            result = artifact_mgr.apply_update_strategy(
                fetch_result=fetch_result,
                strategy="overwrite",
                interactive=False,
                collection_name="test-collection",
            )

            assert result.updated is True


class TestRollbackFailureHandling:
    """Test critical rollback failure scenarios."""

    def test_rollback_itself_fails(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test when rollback restoration fails (critical error path)."""
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123",
            latest_sha="def456",
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
                metadata=ArtifactMetadata(title="Test", version="2.0.0"),
                resolved_sha="def456",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/def456/path/to/skill",
            ),
            temp_workspace=tmp_path / "temp_workspace",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Create a real snapshot first
        snapshot = artifact_mgr._auto_snapshot(
            "test-collection", github_artifact, "Before critical failure test"
        )

        # Inject failure in save_collection
        def failing_save(collection):
            raise IOError("Critical save failure")

        # Inject failure in rollback too
        original_restore = None

        def failing_restore(snapshot_obj, collection_path):
            raise RuntimeError("Rollback also failed")

        with patch.object(
            artifact_mgr.collection_mgr, "save_collection", side_effect=failing_save
        ):
            # Mock snapshot manager restore to fail
            with patch(
                "skillmeat.storage.snapshot.SnapshotManager.restore_snapshot",
                side_effect=failing_restore,
            ):
                # Both update and rollback should fail - expect RuntimeError
                with pytest.raises(RuntimeError, match="rollback also failed"):
                    artifact_mgr.apply_update_strategy(
                        fetch_result=fetch_result,
                        strategy="overwrite",
                        interactive=False,
                        collection_name="test-collection",
                    )


class TestNoSnapshotAvailableForRollback:
    """Test rollback when no snapshot was created."""

    def test_rollback_no_snapshot_available(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test error handling when no snapshot available for rollback."""
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Updated")

        update_info = UpdateInfo(
            current_sha="abc123",
            latest_sha="def456",
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
                metadata=ArtifactMetadata(title="Test", version="2.0.0"),
                resolved_sha="def456",
                resolved_version="v2.0.0",
                upstream_url="https://github.com/user/repo/tree/def456/path/to/skill",
            ),
            temp_workspace=tmp_path / "temp_workspace",
        )

        workspace_artifact = fetch_result.temp_workspace / "artifact"
        workspace_artifact.parent.mkdir(parents=True)
        shutil.copytree(updated_dir, workspace_artifact)

        # Mock snapshot creation to return None (no snapshot available)
        with patch.object(artifact_mgr, "_auto_snapshot", return_value=None):
            # Inject failure in save_collection
            with patch.object(
                artifact_mgr.collection_mgr,
                "save_collection",
                side_effect=IOError("Save failed"),
            ):
                # Should raise original error and log warning about no snapshot
                with pytest.raises(IOError, match="Save failed"):
                    artifact_mgr.apply_update_strategy(
                        fetch_result=fetch_result,
                        strategy="overwrite",
                        interactive=False,
                        collection_name="test-collection",
                    )


class TestCommandAndAgentArtifactTypes:
    """Test update paths for COMMAND and AGENT artifact types."""

    def test_add_command_from_local(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test adding COMMAND artifact type."""
        command_file = tmp_path / "test-command.md"
        command_file.write_text(
            """---
title: Test Command
version: 1.0.0
---

# Test Command

A test command.
"""
        )

        artifact = artifact_mgr.add_from_local(
            path=str(command_file),
            artifact_type=ArtifactType.COMMAND,
            collection_name="test-collection",
        )

        assert artifact.type == ArtifactType.COMMAND

    def test_add_agent_from_local(self, artifact_mgr, initialized_collection, tmp_path):
        """Test adding AGENT artifact type."""
        agent_file = tmp_path / "test-agent.md"
        agent_file.write_text(
            """---
title: Test Agent
version: 1.0.0
---

# Test Agent

A test agent.
"""
        )

        artifact = artifact_mgr.add_from_local(
            path=str(agent_file),
            artifact_type=ArtifactType.AGENT,
            collection_name="test-collection",
        )

        assert artifact.type == ArtifactType.AGENT


class TestUpdateNoUpdateAvailable:
    """Test update method when no update is available."""

    def test_update_no_update_available(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Test update when artifact is already up-to-date."""
        from skillmeat.core.artifact import UpdateStrategy

        # Mock check_updates to return no update
        update_info = UpdateInfo(
            current_sha="abc123",
            latest_sha="abc123",
            current_version="v1.0.0",
            latest_version="v1.0.0",
            has_update=False,
        )

        with patch.object(
            artifact_mgr.github_source, "check_updates", return_value=update_info
        ):
            result = artifact_mgr.update(
                artifact_name="skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                strategy=UpdateStrategy.TAKE_UPSTREAM,
            )

            assert result.updated is False
            assert result.status == "up_to_date"


class TestUpdateLocalArtifact:
    """Test update behavior for local artifacts."""

    def test_update_local_artifact_unsupported(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test that update() recognizes local artifacts and refreshes them."""
        from skillmeat.core.artifact import UpdateStrategy

        # Add local artifact (will have origin="local")
        local_skill_dir = tmp_path / "local-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text(
            """---
title: Local Skill
version: 1.0.0
---

# Local Skill
"""
        )

        artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Update local artifact should trigger refresh
        result = artifact_mgr.update(
            artifact_name="local-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            strategy=UpdateStrategy.PROMPT,
        )

        # Local artifacts get refreshed
        assert result.status == "refreshed_local"


class TestUpdateNoUpstream:
    """Test update when GitHub artifact has no upstream."""

    def test_update_github_artifact_no_upstream(
        self, artifact_mgr, initialized_collection, github_artifact
    ):
        """Test update when GitHub artifact has no upstream URL."""
        from skillmeat.core.artifact import UpdateStrategy

        # Remove upstream from artifact
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        artifact = collection.find_artifact("skill", ArtifactType.SKILL)
        artifact.upstream = None
        artifact_mgr.collection_mgr.save_collection(collection)

        # Update should return no_upstream status
        result = artifact_mgr.update(
            artifact_name="skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            strategy=UpdateStrategy.TAKE_UPSTREAM,
        )

        assert result.updated is False
        assert result.status == "no_upstream"
