"""Unit tests for profile-aware path resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import (
    DeploymentPathProfile,
    resolve_artifact_path,
    resolve_config_path,
    resolve_context_path,
    resolve_deployment_path,
    resolve_profile_root,
)


def test_resolve_artifact_path_uses_default_claude_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    resolved = resolve_artifact_path(
        artifact_name="review",
        artifact_type="command",
        project_path=project,
    )

    assert resolved == (project / ".claude" / "commands" / "review.md").resolve()


def test_resolve_artifact_path_uses_profile_mapping(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    profile = DeploymentPathProfile(
        profile_id="codex-default",
        platform=Platform.CODEX,
        root_dir=".codex",
        artifact_path_map={"skill": "agents"},
    )

    resolved = resolve_artifact_path(
        artifact_name="planner",
        artifact_type="skill",
        project_path=project,
        profile=profile,
    )

    assert resolved == (project / ".codex" / "agents" / "planner").resolve()


def test_profile_root_rejects_traversal(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    profile = DeploymentPathProfile(root_dir="../outside")

    with pytest.raises(ValueError, match="must be relative|escapes allowed root"):
        resolve_profile_root(project, profile=profile)


def test_resolve_deployment_path_rejects_escape(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="escapes allowed root"):
        resolve_deployment_path("../outside.md", project_path=project)


def test_resolve_config_path_in_profile_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    profile = DeploymentPathProfile(root_dir=".gemini", platform=Platform.GEMINI)

    resolved = resolve_config_path(project, profile=profile)
    assert resolved == (project / ".gemini" / ".skillmeat-project.toml").resolve()


def test_resolve_context_path_honors_prefixes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    profile = DeploymentPathProfile(
        root_dir=".codex",
        platform=Platform.CODEX,
        context_prefixes=(".codex/context/",),
    )

    valid = resolve_context_path(
        ".codex/context/specs/architecture.md", project_path=project, profile=profile
    )
    assert valid == (
        project / ".codex" / "context" / "specs" / "architecture.md"
    ).resolve()

    with pytest.raises(ValueError, match="outside allowed profile prefixes"):
        resolve_context_path(
            ".claude/context/specs/architecture.md",
            project_path=project,
            profile=profile,
        )
