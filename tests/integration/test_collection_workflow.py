"""Integration tests for full collection workflow."""

import pytest
from pathlib import Path
from unittest.mock import patch

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import ArtifactManager, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.sources.base import FetchResult


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    return tmp_path / "config"


@pytest.fixture
def config_manager(temp_config_dir):
    """Create ConfigManager with temp directory."""
    return ConfigManager(config_dir=temp_config_dir)


@pytest.fixture
def collection_manager(config_manager):
    """Create CollectionManager with temp config."""
    return CollectionManager(config=config_manager)


@pytest.fixture
def artifact_manager(collection_manager):
    """Create ArtifactManager with temp config."""
    return ArtifactManager(collection_mgr=collection_manager)


@pytest.fixture
def test_skill_dir(tmp_path):
    """Create test skill directory."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill\n\nThis is a test skill.")
    (skill_dir / "helper.py").write_text("def helper(): pass")
    return skill_dir


@pytest.fixture
def test_command_file(tmp_path):
    """Create test command file."""
    command_file = tmp_path / "test-command.md"
    command_file.write_text("# Test Command\n\nCommand instructions here.")
    return command_file


def test_full_workflow_github_and_local(
    config_manager,
    collection_manager,
    artifact_manager,
    test_skill_dir,
    test_command_file,
    tmp_path,
):
    """Test complete workflow: init -> add GitHub -> add local -> list -> show -> remove."""

    # Step 1: Initialize collection
    collection = collection_manager.init("my-collection")
    assert collection.name == "my-collection"
    assert len(collection.artifacts) == 0

    # Verify collection directory structure
    collection_path = config_manager.get_collection_path("my-collection")
    assert collection_path.exists()
    assert (collection_path / "skills").exists()
    assert (collection_path / "commands").exists()
    assert (collection_path / "collection.toml").exists()

    # Step 2: Add artifact from GitHub (mocked)
    github_fetch_result = FetchResult(
        artifact_path=test_skill_dir,
        metadata=ArtifactMetadata(
            title="GitHub Skill",
            description="A skill from GitHub",
            author="testuser",
            tags=["python", "testing"],
        ),
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/testuser/test-repo/tree/abc123/skills/python-skill",
    )

    with patch.object(
        artifact_manager.github_source, "fetch", return_value=github_fetch_result
    ):
        github_artifact = artifact_manager.add_from_github(
            spec="testuser/test-repo/skills/python-skill@v1.0.0",
            artifact_type=ArtifactType.SKILL,
            collection_name="my-collection",
            tags=["github", "python"],
        )

        assert github_artifact.name == "python-skill"
        assert github_artifact.origin == "github"
        assert github_artifact.resolved_sha == "abc123def456"
        assert "github" in github_artifact.tags

    # Verify artifact files were copied
    skill_path = collection_path / "skills" / "python-skill"
    assert skill_path.exists()
    assert (skill_path / "SKILL.md").exists()

    # Step 3: Add artifact from local filesystem
    local_fetch_result = FetchResult(
        artifact_path=test_command_file,
        metadata=ArtifactMetadata(title="Local Command", description="A local command"),
        resolved_sha=None,
        resolved_version=None,
        upstream_url=None,
    )

    with patch.object(
        artifact_manager.local_source, "fetch", return_value=local_fetch_result
    ):
        local_artifact = artifact_manager.add_from_local(
            path=str(test_command_file),
            artifact_type=ArtifactType.COMMAND,
            collection_name="my-collection",
            tags=["local", "utility"],
        )

        assert local_artifact.name == "test-command"
        assert local_artifact.origin == "local"
        assert local_artifact.upstream is None

    # Verify command file was copied
    command_path = collection_path / "commands" / "test-command.md"
    assert command_path.exists()

    # Step 4: List all artifacts
    all_artifacts = artifact_manager.list_artifacts(collection_name="my-collection")
    assert len(all_artifacts) == 2
    assert {a.name for a in all_artifacts} == {"python-skill", "test-command"}

    # Step 5: List artifacts filtered by type
    skills = artifact_manager.list_artifacts(
        collection_name="my-collection", artifact_type=ArtifactType.SKILL
    )
    assert len(skills) == 1
    assert skills[0].name == "python-skill"

    commands = artifact_manager.list_artifacts(
        collection_name="my-collection", artifact_type=ArtifactType.COMMAND
    )
    assert len(commands) == 1
    assert commands[0].name == "test-command"

    # Step 6: List artifacts filtered by tags
    github_artifacts = artifact_manager.list_artifacts(
        collection_name="my-collection", tags=["github"]
    )
    assert len(github_artifacts) == 1
    assert github_artifacts[0].name == "python-skill"

    local_artifacts = artifact_manager.list_artifacts(
        collection_name="my-collection", tags=["local"]
    )
    assert len(local_artifacts) == 1
    assert local_artifacts[0].name == "test-command"

    # Step 7: Show artifact details
    skill_details = artifact_manager.show(
        artifact_name="python-skill",
        artifact_type=ArtifactType.SKILL,
        collection_name="my-collection",
    )
    assert skill_details.name == "python-skill"
    assert skill_details.metadata.title == "GitHub Skill"
    assert skill_details.upstream is not None

    # Step 8: Remove artifact
    artifact_manager.remove(
        artifact_name="python-skill",
        artifact_type=ArtifactType.SKILL,
        collection_name="my-collection",
    )

    # Verify removal
    remaining_artifacts = artifact_manager.list_artifacts(
        collection_name="my-collection"
    )
    assert len(remaining_artifacts) == 1
    assert remaining_artifacts[0].name == "test-command"

    # Verify files were deleted
    assert not skill_path.exists()

    # Step 9: Remove remaining artifact
    artifact_manager.remove(
        artifact_name="test-command",
        artifact_type=ArtifactType.COMMAND,
        collection_name="my-collection",
    )

    # Verify collection is empty
    final_artifacts = artifact_manager.list_artifacts(collection_name="my-collection")
    assert len(final_artifacts) == 0


def test_multi_collection_workflow(
    config_manager, collection_manager, artifact_manager, test_skill_dir
):
    """Test working with multiple collections."""

    # Create multiple collections
    collection1 = collection_manager.init("collection1")
    collection2 = collection_manager.init("collection2")

    # Verify both exist
    collections = collection_manager.list_collections()
    assert set(collections) == {"collection1", "collection2"}

    # Add artifact to collection1
    fetch_result = FetchResult(
        artifact_path=test_skill_dir,
        metadata=ArtifactMetadata(title="Skill 1"),
        resolved_sha="abc123",
        resolved_version=None,
        upstream_url="https://github.com/user/repo/tree/abc123/skill1",
    )

    with patch.object(
        artifact_manager.github_source, "fetch", return_value=fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/skill1@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="collection1",
        )

    # Add different artifact to collection2
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/skill1@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="collection2",
            custom_name="skill2",
        )

    # Verify artifacts are in correct collections
    artifacts1 = artifact_manager.list_artifacts(collection_name="collection1")
    assert len(artifacts1) == 1
    assert artifacts1[0].name == "skill1"

    artifacts2 = artifact_manager.list_artifacts(collection_name="collection2")
    assert len(artifacts2) == 1
    assert artifacts2[0].name == "skill2"

    # Switch active collection
    config_manager.set_active_collection("collection2")
    assert config_manager.get_active_collection() == "collection2"

    # Load without specifying name should use active collection
    loaded = collection_manager.load_collection()
    assert loaded.name == "collection2"


def test_persistence_across_manager_instances(
    temp_config_dir, test_skill_dir, tmp_path
):
    """Test that data persists across different manager instances."""

    # First manager instance - create collection and add artifact
    config1 = ConfigManager(config_dir=temp_config_dir)
    collection_mgr1 = CollectionManager(config=config1)
    artifact_mgr1 = ArtifactManager(collection_mgr=collection_mgr1)

    collection_mgr1.init("persistent-collection")

    fetch_result = FetchResult(
        artifact_path=test_skill_dir,
        metadata=ArtifactMetadata(title="Persistent Skill"),
        resolved_sha="abc123",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/user/repo/tree/abc123/skill",
    )

    with patch.object(artifact_mgr1.github_source, "fetch", return_value=fetch_result):
        artifact_mgr1.add_from_github(
            spec="user/repo/skill@v1.0.0",
            artifact_type=ArtifactType.SKILL,
            collection_name="persistent-collection",
        )

    # Second manager instance - load and verify
    config2 = ConfigManager(config_dir=temp_config_dir)
    collection_mgr2 = CollectionManager(config=config2)
    artifact_mgr2 = ArtifactManager(collection_mgr=collection_mgr2)

    # Verify collection exists
    collections = collection_mgr2.list_collections()
    assert "persistent-collection" in collections

    # Load and verify artifact
    artifacts = artifact_mgr2.list_artifacts(collection_name="persistent-collection")
    assert len(artifacts) == 1
    assert artifacts[0].name == "skill"
    assert artifacts[0].resolved_version == "v1.0.0"

    # Verify files exist
    collection_path = config2.get_collection_path("persistent-collection")
    skill_path = collection_path / "skills" / "skill"
    assert skill_path.exists()
    assert (skill_path / "SKILL.md").exists()


def test_error_handling_workflow(config_manager, collection_manager, artifact_manager):
    """Test error handling in workflow."""

    # Try to load nonexistent collection
    with pytest.raises(ValueError, match="not found"):
        collection_manager.load_collection("nonexistent")

    # Create collection
    collection_manager.init("test-collection")

    # Try to create duplicate collection
    with pytest.raises(ValueError, match="already exists"):
        collection_manager.init("test-collection")

    # Try to remove nonexistent artifact
    with pytest.raises(ValueError, match="not found"):
        artifact_manager.remove(
            artifact_name="nonexistent",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    # Try to show nonexistent artifact
    with pytest.raises(ValueError, match="not found"):
        artifact_manager.show(
            artifact_name="nonexistent",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )
