"""Tests for ArtifactManager."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from skillmeat.config import ConfigManager
from skillmeat.core.artifact import (
    Artifact,
    ArtifactManager,
    ArtifactMetadata,
    ArtifactType,
    UpdateStrategy,
)
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
def test_collection(collection_manager):
    """Create test collection."""
    return collection_manager.init("test-collection")


@pytest.fixture
def test_skill_dir(tmp_path):
    """Create test skill directory."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill\n\nThis is a test skill.")
    return skill_dir


@pytest.fixture
def mock_github_fetch_result(test_skill_dir):
    """Create mock GitHub fetch result."""
    return FetchResult(
        artifact_path=test_skill_dir,
        metadata=ArtifactMetadata(
            title="Test Skill", description="A test skill", tags=["test"]
        ),
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/user/repo/tree/abc123/path/to/skill",
    )


def test_add_from_github_success(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test successfully adding artifact from GitHub."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact = artifact_manager.add_from_github(
            spec="user/repo/path/to/test-skill@v1.0.0",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert artifact.name == "test-skill"
        assert artifact.type == ArtifactType.SKILL
        assert artifact.origin == "github"
        assert (
            artifact.upstream
            == "https://github.com/user/repo/tree/abc123/path/to/skill"
        )
        assert artifact.resolved_sha == "abc123def456"
        assert artifact.resolved_version == "v1.0.0"
        assert artifact.version_spec == "v1.0.0"

        # Verify artifact was added to collection
        collection = artifact_manager.collection_mgr.load_collection("test-collection")
        assert len(collection.artifacts) == 1
        assert collection.artifacts[0].name == "test-skill"


def test_add_from_github_with_custom_name(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test adding artifact with custom name."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact = artifact_manager.add_from_github(
            spec="user/repo/path/to/original-name@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            custom_name="custom-name",
        )

        assert artifact.name == "custom-name"


def test_add_from_github_with_tags(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test adding artifact with tags."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact = artifact_manager.add_from_github(
            spec="user/repo/path/to/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            tags=["python", "testing", "automation"],
        )

        assert artifact.tags == ["python", "testing", "automation"]


def test_add_from_github_duplicate_raises_error(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test adding duplicate artifact raises ValueError."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        # Add first time
        artifact_manager.add_from_github(
            spec="user/repo/path/to/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Try to add again
        with pytest.raises(ValueError, match="already exists"):
            artifact_manager.add_from_github(
                spec="user/repo/path/to/test-skill@latest",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )


def test_add_from_github_uses_repo_name_when_no_path(
    artifact_manager, test_collection, tmp_path
):
    """Test artifact name uses repo name when spec has no path."""
    skill_dir = tmp_path / "repo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Repo Skill")

    fetch_result = FetchResult(
        artifact_path=skill_dir,
        metadata=ArtifactMetadata(title="Repo Skill"),
        resolved_sha="abc123",
        resolved_version=None,
        upstream_url="https://github.com/user/repo/tree/abc123",
    )

    with patch.object(
        artifact_manager.github_source, "fetch", return_value=fetch_result
    ):
        artifact = artifact_manager.add_from_github(
            spec="user/repo@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert artifact.name == "repo"


def test_add_from_local_success(artifact_manager, test_collection, test_skill_dir):
    """Test successfully adding artifact from local filesystem."""
    fetch_result = FetchResult(
        artifact_path=test_skill_dir,
        metadata=ArtifactMetadata(title="Local Skill", description="Local test skill"),
        resolved_sha=None,
        resolved_version=None,
        upstream_url=None,
    )

    with patch.object(
        artifact_manager.local_source, "fetch", return_value=fetch_result
    ):
        artifact = artifact_manager.add_from_local(
            path=str(test_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert artifact.name == "test-skill"
        assert artifact.type == ArtifactType.SKILL
        assert artifact.origin == "local"
        assert artifact.upstream is None
        assert artifact.resolved_sha is None
        assert artifact.resolved_version is None


def test_add_from_local_with_custom_name(
    artifact_manager, test_collection, test_skill_dir
):
    """Test adding local artifact with custom name."""
    fetch_result = FetchResult(
        artifact_path=test_skill_dir,
        metadata=ArtifactMetadata(title="Local Skill"),
        resolved_sha=None,
        resolved_version=None,
        upstream_url=None,
    )

    with patch.object(
        artifact_manager.local_source, "fetch", return_value=fetch_result
    ):
        artifact = artifact_manager.add_from_local(
            path=str(test_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            custom_name="custom-local-name",
        )

        assert artifact.name == "custom-local-name"


def test_remove_artifact(artifact_manager, test_collection, mock_github_fetch_result):
    """Test removing artifact from collection."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        # Add artifact
        artifact_manager.add_from_github(
            spec="user/repo/path/to/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Verify it exists
        collection = artifact_manager.collection_mgr.load_collection("test-collection")
        assert len(collection.artifacts) == 1

        # Remove it
        artifact_manager.remove(
            artifact_name="test-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Verify it's gone
        collection = artifact_manager.collection_mgr.load_collection("test-collection")
        assert len(collection.artifacts) == 0


def test_remove_nonexistent_artifact_raises_error(artifact_manager, test_collection):
    """Test removing nonexistent artifact raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        artifact_manager.remove(
            artifact_name="nonexistent",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )


def test_list_artifacts_all(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test listing all artifacts."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        # Add multiple artifacts
        artifact_manager.add_from_github(
            spec="user/repo/skill1@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )
        artifact_manager.add_from_github(
            spec="user/repo/skill2@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            custom_name="skill2",
        )

        artifacts = artifact_manager.list_artifacts(collection_name="test-collection")
        assert len(artifacts) == 2
        assert {a.name for a in artifacts} == {"skill1", "skill2"}


def test_list_artifacts_filter_by_type(
    artifact_manager, test_collection, mock_github_fetch_result, tmp_path
):
    """Test filtering artifacts by type."""
    # Create command artifact
    command_file = tmp_path / "test-command.md"
    command_file.write_text("# Test Command")

    command_fetch_result = FetchResult(
        artifact_path=command_file,
        metadata=ArtifactMetadata(title="Test Command"),
        resolved_sha="def456",
        resolved_version=None,
        upstream_url="https://github.com/user/repo/tree/def456/command",
    )

    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/skill1@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    with patch.object(
        artifact_manager.github_source, "fetch", return_value=command_fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/command@latest",
            artifact_type=ArtifactType.COMMAND,
            collection_name="test-collection",
        )

    # Filter by SKILL
    skills = artifact_manager.list_artifacts(
        collection_name="test-collection", artifact_type=ArtifactType.SKILL
    )
    assert len(skills) == 1
    assert skills[0].type == ArtifactType.SKILL

    # Filter by COMMAND
    commands = artifact_manager.list_artifacts(
        collection_name="test-collection", artifact_type=ArtifactType.COMMAND
    )
    assert len(commands) == 1
    assert commands[0].type == ArtifactType.COMMAND


def test_list_artifacts_filter_by_tags(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test filtering artifacts by tags."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/skill1@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            tags=["python", "testing"],
        )
        artifact_manager.add_from_github(
            spec="user/repo/skill2@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            custom_name="skill2",
            tags=["javascript", "testing"],
        )
        artifact_manager.add_from_github(
            spec="user/repo/skill3@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            custom_name="skill3",
            tags=["python"],
        )

    # Filter by "python"
    python_artifacts = artifact_manager.list_artifacts(
        collection_name="test-collection", tags=["python"]
    )
    assert len(python_artifacts) == 2
    assert {a.name for a in python_artifacts} == {"skill1", "skill3"}

    # Filter by "testing"
    testing_artifacts = artifact_manager.list_artifacts(
        collection_name="test-collection", tags=["testing"]
    )
    assert len(testing_artifacts) == 2
    assert {a.name for a in testing_artifacts} == {"skill1", "skill2"}


def test_show_artifact(artifact_manager, test_collection, mock_github_fetch_result):
    """Test showing artifact details."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/test-skill@v1.0.0",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        artifact = artifact_manager.show(
            artifact_name="test-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert artifact.name == "test-skill"
        assert artifact.version_spec == "v1.0.0"
        assert artifact.metadata.title == "Test Skill"


def test_show_nonexistent_artifact_raises_error(artifact_manager, test_collection):
    """Test showing nonexistent artifact raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        artifact_manager.show(
            artifact_name="nonexistent",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )


def test_check_updates_no_updates(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test checking updates when no updates available."""
    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    # Mock check_updates to return None (no updates)
    with patch.object(
        artifact_manager.github_source, "check_updates", return_value=None
    ):
        updates = artifact_manager.check_updates(collection_name="test-collection")
        assert updates == {}


def test_check_updates_with_updates(
    artifact_manager, test_collection, mock_github_fetch_result
):
    """Test checking updates when updates available."""
    from skillmeat.sources.base import UpdateInfo

    with patch.object(
        artifact_manager.github_source, "fetch", return_value=mock_github_fetch_result
    ):
        artifact_manager.add_from_github(
            spec="user/repo/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    # Mock check_updates to return update info
    update_info = UpdateInfo(
        current_sha="abc123",
        latest_sha="def456",
        current_version="v1.0.0",
        latest_version="v1.1.0",
        has_update=True,
    )

    with patch.object(
        artifact_manager.github_source, "check_updates", return_value=update_info
    ):
        updates = artifact_manager.check_updates(collection_name="test-collection")
        assert "test-skill::skill" in updates
        assert updates["test-skill::skill"].latest_version == "v1.1.0"


def test_update_github_artifact_applies_new_version(
    artifact_manager, test_collection, tmp_path
):
    """Ensure GitHub artifacts pull latest upstream content."""
    initial_dir = tmp_path / "initial-skill"
    initial_dir.mkdir()
    (initial_dir / "SKILL.md").write_text("# Skill\n\nInitial content.")

    updated_dir = tmp_path / "updated-skill"
    updated_dir.mkdir()
    (updated_dir / "SKILL.md").write_text("# Skill\n\nUpdated content.")

    initial_fetch = FetchResult(
        artifact_path=initial_dir,
        metadata=ArtifactMetadata(title="Initial Skill"),
        resolved_sha="abc123def456",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/user/repo/tree/abc123def456/path/to/test-skill",
    )

    updated_fetch = FetchResult(
        artifact_path=updated_dir,
        metadata=ArtifactMetadata(title="Updated Skill"),
        resolved_sha="def999abc000",
        resolved_version="v1.1.0",
        upstream_url="https://github.com/user/repo/tree/def999abc000/path/to/test-skill",
    )

    with patch.object(
        artifact_manager.github_source, "fetch", side_effect=[initial_fetch, updated_fetch]
    ):
        artifact_manager.add_from_github(
            spec="user/repo/path/to/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        from skillmeat.sources.base import UpdateInfo

        update_info = UpdateInfo(
            current_sha="abc123def456",
            latest_sha="def999abc000",
            current_version="v1.0.0",
            latest_version="v1.1.0",
            has_update=True,
        )

        with patch.object(
            artifact_manager.github_source, "check_updates", return_value=update_info
        ):
            with patch.object(artifact_manager, "_auto_snapshot") as mock_snapshot:
                result = artifact_manager.update(
                    artifact_name="test-skill",
                    artifact_type=ArtifactType.SKILL,
                    collection_name="test-collection",
                    strategy=UpdateStrategy.TAKE_UPSTREAM,
                )

    assert result.updated is True
    assert result.status == "updated_github"
    assert result.previous_version == "v1.0.0"
    assert result.new_version == "v1.1.0"
    assert result.previous_sha == "abc123def456"
    assert result.new_sha == "def999abc000"
    mock_snapshot.assert_called_once()

    collection_path = artifact_manager.collection_mgr.config.get_collection_path(
        "test-collection"
    )
    skill_file = collection_path / "skills" / "test-skill" / "SKILL.md"
    assert skill_file.read_text() == "# Skill\n\nUpdated content."

    lock_entry = artifact_manager.collection_mgr.lock_mgr.get_entry(
        collection_path, "test-skill", ArtifactType.SKILL
    )
    assert lock_entry is not None
    assert lock_entry.resolved_sha == "def999abc000"


def test_update_respects_keep_local_strategy(
    artifact_manager, test_collection, tmp_path
):
    """Ensure local modifications are preserved when strategy=local."""
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("# Skill\n\nOriginal content.")

    fetch_result = FetchResult(
        artifact_path=skill_dir,
        metadata=ArtifactMetadata(title="Skill"),
        resolved_sha="abc111",
        resolved_version="v1.0.0",
        upstream_url="https://github.com/user/repo/tree/abc111/skills/test-skill",
    )

    with patch.object(artifact_manager.github_source, "fetch", return_value=fetch_result):
        artifact_manager.add_from_github(
            spec="user/repo/skills/test-skill@latest",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    collection_path = artifact_manager.collection_mgr.config.get_collection_path(
        "test-collection"
    )
    local_skill = collection_path / "skills" / "test-skill" / "SKILL.md"
    local_skill.write_text("# Skill\n\nLocally modified content.")

    from skillmeat.sources.base import UpdateInfo

    update_info = UpdateInfo(
        current_sha="abc111",
        latest_sha="def222",
        current_version="v1.0.0",
        latest_version="v1.1.0",
        has_update=True,
    )

    with patch.object(
        artifact_manager.github_source, "check_updates", return_value=update_info
    ), patch.object(
        artifact_manager.github_source, "fetch"
    ) as mock_fetch, patch.object(
        artifact_manager, "_auto_snapshot"
    ) as mock_snapshot:
        result = artifact_manager.update(
            artifact_name="test-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            strategy=UpdateStrategy.KEEP_LOCAL,
        )

    assert result.updated is False
    assert result.status == "local_changes_kept"
    assert result.local_modifications is True
    mock_fetch.assert_not_called()
    mock_snapshot.assert_not_called()
    assert "Locally modified" in local_skill.read_text()


def test_update_refreshes_local_artifacts(
    artifact_manager, test_collection, tmp_path
):
    """Local artifacts should refresh metadata and lock entries."""
    local_dir = tmp_path / "local-skill"
    local_dir.mkdir()
    local_file = local_dir / "SKILL.md"
    local_file.write_text(
        "---\n"
        "title: Local Skill\n"
        "version: 1.0.0\n"
        "---\n"
        "\n"
        "Initial body\n"
    )

    fetch_result = FetchResult(
        artifact_path=local_dir,
        metadata=ArtifactMetadata(title="Local Skill", version="1.0.0"),
        resolved_sha=None,
        resolved_version=None,
        upstream_url=None,
    )

    with patch.object(artifact_manager.local_source, "fetch", return_value=fetch_result):
        artifact_manager.add_from_local(
            path=str(local_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    collection_path = artifact_manager.collection_mgr.config.get_collection_path(
        "test-collection"
    )
    stored_skill = collection_path / "skills" / "local-skill"
    stored_file = stored_skill / "SKILL.md"
    stored_file.write_text(
        "---\n"
        "title: Updated Local Skill\n"
        "version: 1.1.0\n"
        "---\n"
        "\n"
        "Updated body\n"
    )

    with patch.object(artifact_manager, "_auto_snapshot"):
        result = artifact_manager.update(
            artifact_name="local-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

    assert result.updated is True
    assert result.status == "refreshed_local"
    collection = artifact_manager.collection_mgr.load_collection("test-collection")
    artifact = collection.find_artifact("local-skill", ArtifactType.SKILL)
    assert artifact.metadata.title == "Updated Local Skill"
    assert artifact.metadata.version == "1.1.0"

    lock_entry = artifact_manager.collection_mgr.lock_mgr.get_entry(
        collection_path, "local-skill", ArtifactType.SKILL
    )
    assert lock_entry is not None
