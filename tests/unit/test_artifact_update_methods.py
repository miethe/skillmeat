"""Unit tests for artifact update methods to achieve >80% coverage.

This test suite focuses on specific code paths in update methods
that aren't covered by integration tests.
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
    (initial_dir / "SKILL.md").write_text("# Test Skill\n\nInitial version")

    initial_fetch = FetchResult(
        artifact_path=initial_dir,
        metadata=ArtifactMetadata(
            title="Test Skill",
            description="Unit test skill",
            version="1.0.0",
            tags=["test"],
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


# =============================================================================
# Test Missing Upstream Artifact in Temp Workspace
# =============================================================================


class TestMissingUpstreamInWorkspace:
    """Test handling of missing upstream artifact in temp workspace."""

    def test_apply_update_missing_upstream_artifact_in_workspace(
        self, artifact_mgr, github_artifact, tmp_path
    ):
        """Test error when upstream artifact missing from temp workspace."""
        # Create temp workspace but WITHOUT the artifact subdirectory
        temp_workspace = tmp_path / "temp"
        temp_workspace.mkdir()
        # Note: NOT creating temp_workspace / "artifact"

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

        # Should raise ValueError about missing artifact in workspace
        with pytest.raises(ValueError, match="Artifact not found in temp workspace"):
            artifact_mgr.apply_update_strategy(
                fetch_result=fetch_result,
                strategy="overwrite",
                interactive=False,
                collection_name="test-collection",
            )


# =============================================================================
# Test Diff Display Edge Cases
# =============================================================================


class TestPromptStrategyDiffDisplay:
    """Test prompt strategy diff display edge cases."""

    def test_prompt_strategy_many_added_files(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy with >5 added files (tests truncation)."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "skill"

        # Create upstream with many added files
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\n\nInitial version")

        # Add 10 new files to trigger truncation in display
        for i in range(10):
            (upstream_dir / f"file_{i}.txt").write_text(f"Content {i}")

        console = Console()

        # Mock user rejecting update
        with patch("skillmeat.core.artifact.Confirm.ask", return_value=False):
            success = artifact_mgr._apply_prompt_strategy(
                artifact_path, upstream_dir, github_artifact, True, console
            )

        assert success is False

    def test_prompt_strategy_many_removed_files(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy with >5 removed files (tests truncation)."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "skill"

        # Add many files to local
        for i in range(10):
            (artifact_path / f"file_{i}.txt").write_text(f"Content {i}")

        # Create upstream with just SKILL.md (removing all extra files)
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\n\nUpdated")

        console = Console()

        # Mock user rejecting update
        with patch("skillmeat.core.artifact.Confirm.ask", return_value=False):
            success = artifact_mgr._apply_prompt_strategy(
                artifact_path, upstream_dir, github_artifact, True, console
            )

        assert success is False

    def test_prompt_strategy_many_modified_files(
        self, artifact_mgr, initialized_collection, github_artifact, tmp_path
    ):
        """Test prompt strategy with >5 modified files (tests truncation)."""
        from rich.console import Console

        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        artifact_path = collection_path / "skills" / "skill"

        # Add many files to local
        for i in range(10):
            (artifact_path / f"file_{i}.txt").write_text(f"Original {i}")

        # Create upstream with modified files
        upstream_dir = tmp_path / "upstream"
        upstream_dir.mkdir()
        (upstream_dir / "SKILL.md").write_text("# Test Skill\n\nInitial version")
        for i in range(10):
            (upstream_dir / f"file_{i}.txt").write_text(f"Modified {i}")

        console = Console()

        # Mock user rejecting update
        with patch("skillmeat.core.artifact.Confirm.ask", return_value=False):
            success = artifact_mgr._apply_prompt_strategy(
                artifact_path, upstream_dir, github_artifact, True, console
            )

        assert success is False


# =============================================================================
# Test Local Artifact Methods
# =============================================================================


class TestLocalArtifactMethods:
    """Test methods for local (non-GitHub) artifacts."""

    def test_add_from_local(self, artifact_mgr, initialized_collection, tmp_path):
        """Test adding artifact from local filesystem."""
        # Create local skill
        local_skill_dir = tmp_path / "my-local-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text(
            """---
title: Local Skill
version: 1.0.0
---

# Local Skill

This is a local skill.
"""
        )

        # Add from local
        artifact = artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        assert artifact is not None
        assert artifact.name == "my-local-skill"
        assert artifact.origin == "local"
        assert artifact.metadata.title == "Local Skill"

    def test_add_from_local_with_custom_name(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test adding artifact from local with custom name."""
        local_skill_dir = tmp_path / "original-name"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text("# Custom Named Skill")

        artifact = artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            custom_name="custom-skill-name",
        )

        assert artifact.name == "custom-skill-name"

    def test_add_from_local_duplicate_without_force(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test adding duplicate local artifact without force flag."""
        local_skill_dir = tmp_path / "duplicate-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text("# Duplicate")

        # Add first time
        artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Try adding again without force - should fail
        with pytest.raises(ValueError, match="already exists"):
            artifact_mgr.add_from_local(
                path=str(local_skill_dir),
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
                force=False,
            )

    def test_add_from_local_duplicate_with_force(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test adding duplicate local artifact with force=True."""
        local_skill_dir = tmp_path / "duplicate-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text("# Duplicate v1")

        # Add first time
        artifact1 = artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Modify and add again with force
        (local_skill_dir / "SKILL.md").write_text("# Duplicate v2")

        artifact2 = artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            force=True,
        )

        assert artifact2.name == artifact1.name

        # Verify content was updated
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        skill_file = collection_path / "skills" / "duplicate-skill" / "SKILL.md"
        assert "v2" in skill_file.read_text()


# =============================================================================
# Test Remove Method
# =============================================================================


class TestRemoveMethod:
    """Test artifact removal."""

    def test_remove_artifact(self, artifact_mgr, initialized_collection, tmp_path):
        """Test removing an artifact from collection."""
        # Add an artifact
        local_skill_dir = tmp_path / "removable-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text("# Removable Skill")

        artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Verify it exists
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        assert collection.find_artifact("removable-skill", ArtifactType.SKILL) is not None

        # Remove it
        artifact_mgr.remove(
            artifact_name="removable-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Verify it's gone
        collection = artifact_mgr.collection_mgr.load_collection("test-collection")
        assert collection.find_artifact("removable-skill", ArtifactType.SKILL) is None

    def test_remove_nonexistent_artifact(
        self, artifact_mgr, initialized_collection
    ):
        """Test removing artifact that doesn't exist."""
        with pytest.raises(ValueError, match="not found"):
            artifact_mgr.remove(
                artifact_name="nonexistent",
                artifact_type=ArtifactType.SKILL,
                collection_name="test-collection",
            )


# =============================================================================
# Test Refresh Local Artifact
# =============================================================================


class TestRefreshLocalArtifact:
    """Test refreshing metadata for local artifacts."""

    def test_refresh_local_artifact(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test refreshing a local artifact updates metadata."""
        from skillmeat.core.artifact import UpdateStrategy

        # Add local artifact
        local_skill_dir = tmp_path / "refreshable-skill"
        local_skill_dir.mkdir()
        (local_skill_dir / "SKILL.md").write_text(
            """---
title: Refreshable Skill
version: 1.0.0
---

# Refreshable Skill

Version 1.0.0
"""
        )

        artifact_mgr.add_from_local(
            path=str(local_skill_dir),
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
        )

        # Modify the artifact file directly
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )
        skill_file = collection_path / "skills" / "refreshable-skill" / "SKILL.md"
        skill_file.write_text(
            """---
title: Refreshable Skill
version: 2.0.0
---

# Refreshable Skill

Version 2.0.0 - updated
"""
        )

        # Refresh the artifact
        result = artifact_mgr.update(
            artifact_name="refreshable-skill",
            artifact_type=ArtifactType.SKILL,
            collection_name="test-collection",
            strategy=UpdateStrategy.PROMPT,
        )

        assert result.updated is True
        assert result.status == "refreshed_local"
        assert result.new_version == "2.0.0"


# =============================================================================
# Test Build Spec from Artifact
# =============================================================================


class TestBuildSpecFromArtifact:
    """Test _build_spec_from_artifact method."""

    def test_build_spec_from_artifact_no_upstream(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test building spec when artifact has no upstream."""
        # Create artifact without upstream
        artifact = Artifact(
            name="no-upstream",
            type=ArtifactType.SKILL,
            path="skills/no-upstream",
            origin="local",
            metadata=ArtifactMetadata(title="No Upstream"),
            added=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="does not have an upstream reference"):
            artifact_mgr._build_spec_from_artifact(artifact)

    def test_build_spec_from_artifact_invalid_url_format(
        self, artifact_mgr, initialized_collection
    ):
        """Test building spec with invalid upstream URL format."""
        # Create artifact with invalid upstream URL
        artifact = Artifact(
            name="invalid-upstream",
            type=ArtifactType.SKILL,
            path="skills/invalid-upstream",
            origin="github",
            metadata=ArtifactMetadata(title="Invalid Upstream"),
            added=datetime.utcnow(),
            upstream="https://invalid.com/not/github/format",
        )

        with pytest.raises(ValueError, match="Unsupported upstream URL format"):
            artifact_mgr._build_spec_from_artifact(artifact)


# =============================================================================
# Test Detect Local Modifications
# =============================================================================


class TestDetectLocalModifications:
    """Test _detect_local_modifications method."""

    def test_detect_local_modifications_no_lock_entry(
        self, artifact_mgr, initialized_collection, tmp_path
    ):
        """Test detection when no lock entry exists."""
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Create artifact without lock entry
        artifact_path = collection_path / "skills" / "unlocked-skill"
        artifact_path.mkdir(parents=True)
        (artifact_path / "SKILL.md").write_text("# Unlocked")

        artifact = Artifact(
            name="unlocked-skill",
            type=ArtifactType.SKILL,
            path="skills/unlocked-skill",
            origin="local",
            metadata=ArtifactMetadata(title="Unlocked"),
            added=datetime.utcnow(),
        )

        # Should return False when no lock entry
        has_mods = artifact_mgr._detect_local_modifications(
            collection_path, artifact, artifact_path
        )

        assert has_mods is False

    def test_detect_local_modifications_missing_files(
        self, artifact_mgr, initialized_collection
    ):
        """Test detection when artifact files are missing."""
        collection_path = artifact_mgr.collection_mgr.config.get_collection_path(
            "test-collection"
        )

        # Create artifact pointing to non-existent path
        artifact = Artifact(
            name="missing-files",
            type=ArtifactType.SKILL,
            path="skills/missing",
            origin="local",
            metadata=ArtifactMetadata(title="Missing"),
            added=datetime.utcnow(),
        )

        non_existent_path = collection_path / "skills" / "missing"

        # Should return False when files don't exist
        has_mods = artifact_mgr._detect_local_modifications(
            collection_path, artifact, non_existent_path
        )

        assert has_mods is False
