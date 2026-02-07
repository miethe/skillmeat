"""Tests for profile-aware project discovery."""

from __future__ import annotations

from pathlib import Path

from skillmeat.api.project_registry import ProjectRegistry
from skillmeat.api.routers.projects import discover_projects
from skillmeat.storage.deployment import DeploymentTracker


def _write_deployment_file(project_path: Path, root_dir: str) -> None:
    profile_root = project_path / root_dir
    profile_root.mkdir(parents=True, exist_ok=True)
    (profile_root / DeploymentTracker.DEPLOYMENT_FILE).write_text("deployed = []\n")


def test_discover_projects_scans_multiple_profile_roots(tmp_path: Path) -> None:
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()

    _write_deployment_file(project_a, ".claude")
    _write_deployment_file(project_a, ".codex")
    _write_deployment_file(project_b, ".gemini")

    discovered = discover_projects(search_paths=[tmp_path])
    discovered_paths = {path.resolve() for path in discovered}

    assert project_a.resolve() in discovered_paths
    assert project_b.resolve() in discovered_paths
    assert len(discovered_paths) == 2


def test_discover_projects_supports_profile_filter(tmp_path: Path) -> None:
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()

    _write_deployment_file(project_a, ".claude")
    _write_deployment_file(project_b, ".codex")

    codex_only = discover_projects(search_paths=[tmp_path], profile_id="codex")
    codex_paths = {path.resolve() for path in codex_only}

    assert project_b.resolve() in codex_paths
    assert project_a.resolve() not in codex_paths


def test_project_registry_discovers_non_claude_profiles(tmp_path: Path) -> None:
    project = tmp_path / "project-a"
    project.mkdir()
    _write_deployment_file(project, ".codex")

    registry = ProjectRegistry()
    registry.configure(search_paths=[tmp_path], max_depth=4)

    discovered = registry._discover_projects_sync()
    discovered_paths = {path.resolve() for path in discovered}

    assert project.resolve() in discovered_paths
