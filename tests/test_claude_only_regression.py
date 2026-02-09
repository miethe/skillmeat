"""Regression tests to verify Claude-only workflows remain backward compatible."""

from __future__ import annotations

from pathlib import Path

from unittest.mock import Mock

from skillmeat.core.deployment import DeploymentManager
from skillmeat.storage.deployment import DeploymentTracker


def _write_deployment_file(profile_root: Path, content: str) -> None:
    profile_root.mkdir(parents=True, exist_ok=True)
    (profile_root / DeploymentTracker.DEPLOYMENT_FILE).write_text(content, encoding="utf-8")


def test_default_profile_resolution_uses_claude_for_legacy_projects(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    collection_mgr = Mock()
    collection_mgr.config = Mock()

    manager = DeploymentManager(collection_mgr=collection_mgr)
    profiles = manager._resolve_target_profiles(project_path=project_dir)

    assert len(profiles) == 1
    assert profiles[0].profile_id == "claude_code"
    assert profiles[0].root_dir == ".claude"


def test_legacy_records_resolve_to_default_claude_profile(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()

    _write_deployment_file(
        project_path / ".claude",
        """
[[deployed]]
artifact_name = "legacy-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-02-09T10:00:00"
artifact_path = "skills/legacy-skill"
content_hash = "abc123"
local_modifications = false
collection_sha = "abc123"
""".strip()
        + "\n",
    )

    deployment = DeploymentTracker.get_deployment(
        project_path,
        artifact_name="legacy-skill",
        artifact_type="skill",
        profile_id="claude_code",
    )

    assert deployment is not None
    assert deployment.deployment_profile_id is None


def test_read_deployments_without_profile_includes_all_profiles(tmp_path: Path) -> None:
    project_path = tmp_path / "project"
    project_path.mkdir()

    _write_deployment_file(
        project_path / ".claude",
        """
[[deployed]]
artifact_name = "claude-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-02-09T10:00:00"
artifact_path = "skills/claude-skill"
content_hash = "hash-1"
local_modifications = false
collection_sha = "hash-1"
deployment_profile_id = "claude_code"
platform = "claude_code"
profile_root_dir = ".claude"
""".strip()
        + "\n",
    )

    _write_deployment_file(
        project_path / ".codex",
        """
[[deployed]]
artifact_name = "codex-skill"
artifact_type = "skill"
from_collection = "default"
deployed_at = "2026-02-09T10:00:00"
artifact_path = "skills/codex-skill"
content_hash = "hash-2"
local_modifications = false
collection_sha = "hash-2"
deployment_profile_id = "codex"
platform = "codex"
profile_root_dir = ".codex"
""".strip()
        + "\n",
    )

    deployments = DeploymentTracker.read_deployments(project_path, profile_root_dir=None)

    assert len(deployments) == 2
    assert sorted(d.deployment_profile_id for d in deployments) == ["claude_code", "codex"]
