"""Fresh-project profile verification tests (Phase 5)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.storage.deployment import DeploymentTracker


def test_init_profile_codex_creates_codex_root(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--profile",
            "codex",
            "--project-path",
            str(project_dir),
        ],
    )

    assert result.exit_code == 0
    assert (project_dir / ".codex" / "skills").is_dir()
    assert (project_dir / ".codex" / ".skillmeat-project.toml").exists()


def test_init_all_profiles_creates_all_profile_roots(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "init",
            "--all-profiles",
            "--project-path",
            str(project_dir),
        ],
    )

    assert result.exit_code == 0
    for root_dir in [".claude", ".codex", ".gemini", ".cursor"]:
        assert (project_dir / root_dir / "skills").is_dir()


def test_record_deployment_tracks_profile_metadata_per_profile_root(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()

    artifact = Artifact(
        name="sample-skill",
        type=ArtifactType.SKILL,
        path="skills/sample-skill",
        origin="local",
        metadata=ArtifactMetadata(),
        added=datetime.now(),
    )

    DeploymentTracker.record_deployment(
        project_path=project_path,
        artifact=artifact,
        collection_name="default",
        collection_sha="hash-claude",
        deployment_profile_id="claude_code",
        platform="claude_code",
        profile_root_dir=".claude",
    )

    DeploymentTracker.record_deployment(
        project_path=project_path,
        artifact=artifact,
        collection_name="default",
        collection_sha="hash-codex",
        deployment_profile_id="codex",
        platform="codex",
        profile_root_dir=".codex",
    )

    deployments = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)

    assert len(deployments) == 2
    by_profile = {d.deployment_profile_id: d for d in deployments}
    assert by_profile["claude_code"].profile_root_dir == ".claude"
    assert by_profile["codex"].profile_root_dir == ".codex"
