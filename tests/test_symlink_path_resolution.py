"""Tests for symlink-aware path resolution behavior."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from skillmeat.core.enums import Platform
from skillmeat.core.path_resolver import DeploymentPathProfile, resolve_profile_root


@pytest.mark.skipif(os.name == "nt", reason="Symlink creation is not reliable on Windows CI")
def test_resolve_profile_root_logs_symlink_warning(tmp_path: Path, caplog) -> None:
    project = tmp_path / "project"
    project.mkdir()

    target_dir = project / ".profiles" / "linked-root"
    target_dir.mkdir(parents=True)
    (project / ".codex").symlink_to(target_dir, target_is_directory=True)

    profile = DeploymentPathProfile(
        profile_id="codex",
        platform=Platform.CODEX,
        root_dir=".codex",
    )

    with caplog.at_level("WARNING"):
        resolved = resolve_profile_root(project, profile=profile)

    assert resolved == target_dir.resolve()
    assert any(
        "Profile root resolves through symlink" in message
        for message in caplog.messages
    )
