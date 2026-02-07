"""Integration-style tests for profile-aware deployment flows."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.core.deployment import DeploymentManager
from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import DeploymentPathProfile
from skillmeat.storage.deployment import DeploymentTracker


@pytest.fixture
def mock_collection_mgr():
    mgr = Mock()
    mgr.config = Mock()
    return mgr


@pytest.fixture
def sample_collection():
    return Collection(
        name="default",
        version="1.0.0",
        artifacts=[
            Artifact(
                name="test-skill",
                type=ArtifactType.SKILL,
                path="skills/test-skill",
                origin="github",
                metadata=ArtifactMetadata(),
                added=datetime.now(),
            )
        ],
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_deploy_same_artifact_to_multiple_profiles(
    tmp_path: Path, mock_collection_mgr, sample_collection, monkeypatch
) -> None:
    collection_path = tmp_path / "collection"
    project_path = tmp_path / "project"
    collection_path.mkdir(parents=True)
    project_path.mkdir(parents=True)
    (collection_path / "skills" / "test-skill").mkdir(parents=True)
    (collection_path / "skills" / "test-skill" / "SKILL.md").write_text("# Skill")

    mock_collection_mgr.load_collection.return_value = sample_collection
    mock_collection_mgr.config.get_collection_path.return_value = collection_path
    monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda _: True)

    manager = DeploymentManager(collection_mgr=mock_collection_mgr)
    monkeypatch.setattr(
        manager,
        "_resolve_target_profiles",
        lambda **_: [
            DeploymentPathProfile(
                profile_id="claude_code",
                platform=Platform.CLAUDE_CODE,
                root_dir=".claude",
            ),
            DeploymentPathProfile(
                profile_id="codex",
                platform=Platform.CODEX,
                root_dir=".codex",
            ),
        ],
    )

    deployments = manager.deploy_artifacts(
        artifact_names=["test-skill"],
        project_path=project_path,
        all_profiles=True,
    )

    assert len(deployments) == 2
    assert (project_path / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()
    assert (project_path / ".codex" / "skills" / "test-skill" / "SKILL.md").exists()

    records = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)
    assert len(records) == 2
    assert sorted([record.deployment_profile_id for record in records]) == [
        "claude_code",
        "codex",
    ]


def test_undeploy_single_profile_keeps_other_profile(
    tmp_path: Path, mock_collection_mgr, sample_collection, monkeypatch
) -> None:
    collection_path = tmp_path / "collection"
    project_path = tmp_path / "project"
    collection_path.mkdir(parents=True)
    project_path.mkdir(parents=True)
    (collection_path / "skills" / "test-skill").mkdir(parents=True)
    (collection_path / "skills" / "test-skill" / "SKILL.md").write_text("# Skill")

    mock_collection_mgr.load_collection.return_value = sample_collection
    mock_collection_mgr.config.get_collection_path.return_value = collection_path
    monkeypatch.setattr("skillmeat.core.deployment.Confirm.ask", lambda _: True)

    manager = DeploymentManager(collection_mgr=mock_collection_mgr)
    monkeypatch.setattr(
        manager,
        "_resolve_target_profiles",
        lambda **_: [
            DeploymentPathProfile(
                profile_id="claude_code",
                platform=Platform.CLAUDE_CODE,
                root_dir=".claude",
            ),
            DeploymentPathProfile(
                profile_id="codex",
                platform=Platform.CODEX,
                root_dir=".codex",
            ),
        ],
    )

    manager.deploy_artifacts(
        artifact_names=["test-skill"],
        project_path=project_path,
        all_profiles=True,
    )

    manager.undeploy(
        artifact_name="test-skill",
        artifact_type=ArtifactType.SKILL,
        project_path=project_path,
        profile_id="codex",
    )

    assert not (project_path / ".codex" / "skills" / "test-skill").exists()
    assert (project_path / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()

    remaining = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)
    assert len(remaining) == 1
    assert remaining[0].deployment_profile_id == "claude_code"


def test_default_profile_resolution_for_legacy_project(
    tmp_path: Path, mock_collection_mgr
) -> None:
    project_path = tmp_path / "legacy-project"
    project_path.mkdir()

    manager = DeploymentManager(collection_mgr=mock_collection_mgr)
    profiles = manager._resolve_target_profiles(project_path=project_path)

    assert len(profiles) == 1
    assert profiles[0].profile_id == "claude_code"
    assert profiles[0].root_dir == ".claude"
