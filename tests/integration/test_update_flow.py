"""Integration tests for artifact update flow."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import (
    ArtifactManager,
    ArtifactType,
    UpdateStrategy,
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
    (initial_dir / "SKILL.md").write_text("# Test Skill\n\nInitial version.")

    initial_fetch = FetchResult(
        artifact_path=initial_dir,
        metadata=ArtifactMetadata(
            title="Test Skill",
            description="A test skill",
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


class TestUpdateFlowGithubSuccess:
    """Test successful update flow for GitHub artifacts."""

    def test_update_flow_github_success(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify successful GitHub artifact update with version progression.

        Steps:
        1. Add GitHub artifact to collection
        2. Mock upstream having new version
        3. Run update command
        4. Verify artifact updated successfully
        5. Verify lock file updated
        6. Verify manifest updated
        """
        # Create updated artifact directory
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Test Skill\n\nUpdated version with new content.")

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(
                title="Test Skill",
                description="A test skill",
                version="2.0.0",
                tags=["test"],
            ),
            resolved_sha="def999abc000",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/def999abc000/path/to/test-skill",
        )

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
            artifact_mgr.github_source, "fetch", return_value=updated_fetch
        ), patch.object(
            artifact_mgr, "_auto_snapshot"
        ) as mock_snapshot:
            result = artifact_mgr.update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                strategy=UpdateStrategy.TAKE_UPSTREAM,
            )

        # Verify update result
        assert result.updated is True
        assert result.status == "updated_github"
        assert result.previous_version == "v1.0.0"
        assert result.new_version == "v2.0.0"
        assert result.previous_sha == "abc123def456"
        assert result.new_sha == "def999abc000"
        mock_snapshot.assert_called_once()

        # Verify artifact content was updated
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        assert skill_file.read_text() == "# Test Skill\n\nUpdated version with new content."

        # Verify lock file updated
        lock_entry = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )
        assert lock_entry is not None
        assert lock_entry.resolved_sha == "def999abc000"
        assert lock_entry.resolved_version == "v2.0.0"

        # Verify manifest updated
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        artifact = collection.find_artifact("test-skill", ArtifactType.SKILL)
        assert artifact.resolved_version == "v2.0.0"
        assert artifact.resolved_sha == "def999abc000"
        assert artifact.upstream == "https://github.com/user/repo/tree/def999abc000/path/to/test-skill"


class TestUpdateFlowNetworkFailure:
    """Test update flow with network failures and rollback."""

    def test_update_flow_network_failure_rollback(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify rollback on network failure during fetch.

        Steps:
        1. Add GitHub artifact to collection
        2. Mock network failure during fetch
        3. Run update command
        4. CRITICAL: Verify rollback occurred
        5. Verify collection unchanged
        6. Verify lock unchanged
        """
        # Store original state
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        original_skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        original_content = original_skill_file.read_text()

        original_lock_entry = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )
        original_sha = original_lock_entry.resolved_sha if original_lock_entry else None

        # Mock network failure
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
            side_effect=RuntimeError("Network error: Connection refused"),
        ), patch.object(
            artifact_mgr, "_auto_snapshot"
        ):
            # Attempt update - should fail with exception
            with pytest.raises(RuntimeError):
                artifact_mgr.update(
                    artifact_name="test-skill",
                    artifact_type=ArtifactType.SKILL,
                    collection_name="test-collection",
                    strategy=UpdateStrategy.TAKE_UPSTREAM,
                )

        # Verify collection unchanged
        assert original_skill_file.read_text() == original_content

        # Verify lock unchanged
        rolled_back_lock_entry = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )
        if original_lock_entry:
            assert rolled_back_lock_entry.resolved_sha == original_sha


class TestUpdateFlowLocalModificationsPrompt:
    """Test update flow with local modifications and prompt strategy."""

    def test_update_flow_local_modifications_prompt(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify prompt strategy with local modifications.

        Steps:
        1. Add GitHub artifact
        2. Modify artifact locally
        3. Mock upstream has updates
        4. Run update with strategy=PROMPT
        5. Mock user declining update
        6. Verify artifact NOT updated (kept local changes)
        """
        # Modify artifact locally
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        local_modification = "# Test Skill\n\nLocally modified content."
        skill_file.write_text(local_modification)

        # Note: We do NOT update the lock entry here. The local modification
        # will be detected because the file hash won't match the lock entry's hash.

        # Mock upstream update
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Test Skill\n\nUpdated version.")

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
            artifact_mgr.github_source, "fetch", return_value=updated_fetch
        ), patch(
            "skillmeat.core.artifact.Confirm.ask", return_value=False
        ) as mock_confirm, patch.object(
            artifact_mgr, "_auto_snapshot"
        ):
            result = artifact_mgr.update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                strategy=UpdateStrategy.PROMPT,
            )

        # Verify user was prompted
        mock_confirm.assert_called_once()

        # Verify artifact NOT updated
        assert result.updated is False
        assert result.status == "cancelled"
        assert result.local_modifications is True

        # Verify local changes preserved
        assert skill_file.read_text() == local_modification


class TestUpdateFlowStrategyEnforcement:
    """Test update strategy enforcement."""

    def test_update_flow_strategy_enforcement_take_upstream(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify TAKE_UPSTREAM strategy overwrites local changes."""
        # Modify artifact locally
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        skill_file.write_text("# Test Skill\n\nLocally modified.")

        # Note: We do NOT update the lock entry here. The local modification
        # will be detected because the file hash won't match the lock entry's hash.

        # Mock upstream update
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Test Skill\n\nUpstream content.")

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(title="Test Skill", version="2.0.0"),
            resolved_sha="def999abc000",
            resolved_version="v2.0.0",
            upstream_url="https://github.com/user/repo/tree/def999abc000/path/to/test-skill",
        )

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
            artifact_mgr.github_source, "fetch", return_value=updated_fetch
        ), patch.object(
            artifact_mgr, "_auto_snapshot"
        ):
            result = artifact_mgr.update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                strategy=UpdateStrategy.TAKE_UPSTREAM,
            )

        # Verify update succeeded
        assert result.updated is True
        assert result.status == "updated_github"

        # Verify local changes were overwritten
        assert skill_file.read_text() == "# Test Skill\n\nUpstream content."

    def test_update_flow_strategy_enforcement_keep_local(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify KEEP_LOCAL strategy skips update."""
        # Modify artifact locally
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
        local_content = "# Test Skill\n\nLocally modified."
        skill_file.write_text(local_content)

        # Note: We do NOT update the lock entry here. The local modification
        # will be detected because the file hash won't match the lock entry's hash.

        # Mock upstream update
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
            artifact_mgr.github_source, "fetch"
        ) as mock_fetch, patch.object(
            artifact_mgr, "_auto_snapshot"
        ) as mock_snapshot:
            result = artifact_mgr.update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                strategy=UpdateStrategy.KEEP_LOCAL,
            )

        # Verify update skipped
        assert result.updated is False
        assert result.status == "local_changes_kept"
        assert result.local_modifications is True

        # Verify fetch not called
        mock_fetch.assert_not_called()
        mock_snapshot.assert_not_called()

        # Verify local changes preserved
        assert skill_file.read_text() == local_content


class TestUpdateFlowLockManifestConsistency:
    """Test lock file and manifest consistency during updates."""

    def test_update_flow_lock_manifest_consistency(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Verify manifest and lock stay consistent through update cycle.

        Steps:
        1. Start with consistent state
        2. Run update with new version
        3. Verify both lock and manifest updated together
        4. Verify no partial states
        """
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Get initial state
        initial_artifact = artifact_mgr.collection_mgr.load_collection(
            "test-collection"
        ).find_artifact("test-skill", ArtifactType.SKILL)
        initial_version = initial_artifact.resolved_version

        initial_lock = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )
        initial_lock_version = initial_lock.resolved_version

        # Verify initial consistency
        assert initial_version == initial_lock_version

        # Mock upstream update
        updated_dir = tmp_path / "updated-skill"
        updated_dir.mkdir()
        (updated_dir / "SKILL.md").write_text("# Test Skill\n\nUpdated.")

        updated_fetch = FetchResult(
            artifact_path=updated_dir,
            metadata=ArtifactMetadata(title="Test Skill", version="3.0.0"),
            resolved_sha="ghi555jkl666",
            resolved_version="v3.0.0",
            upstream_url="https://github.com/user/repo/tree/ghi555jkl666/path/to/test-skill",
        )

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="ghi555jkl666",
            current_version="v1.0.0",
            latest_version="v3.0.0",
            has_update=True,
        )

        with patch.object(
            artifact_mgr.github_source, "check_updates", return_value=update_info
        ), patch.object(
            artifact_mgr.github_source, "fetch", return_value=updated_fetch
        ), patch.object(
            artifact_mgr, "_auto_snapshot"
        ):
            artifact_mgr.update(
                artifact_name="test-skill",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                strategy=UpdateStrategy.TAKE_UPSTREAM,
            )

        # Verify final consistency
        final_artifact = artifact_mgr.collection_mgr.load_collection(
            "test-collection"
        ).find_artifact("test-skill", ArtifactType.SKILL)
        final_version = final_artifact.resolved_version

        final_lock = artifact_mgr.collection_mgr.lock_mgr.get_entry(
            collection_path, "test-skill", ArtifactType.SKILL
        )
        final_lock_version = final_lock.resolved_version

        # Verify they match
        assert final_version == final_lock_version == "v3.0.0"

        # Verify both updated from initial state
        assert final_version != initial_version
        assert final_lock_version != initial_lock_version
