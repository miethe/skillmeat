"""Tests for profile-aware CLI init behavior."""

from __future__ import annotations

from click.testing import CliRunner

from skillmeat.cli import main


def test_init_profile_codex_scaffolds_profile_root(tmp_path, monkeypatch):
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
    assert (project_dir / ".codex" / ".skillmeat-deployed.toml").exists()


def test_init_profile_default_claude(tmp_path, monkeypatch):
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
            "claude_code",
            "--project-path",
            str(project_dir),
        ],
    )

    assert result.exit_code == 0
    assert (project_dir / ".claude" / "skills").is_dir()
    assert (project_dir / ".claude" / ".skillmeat-project.toml").exists()


def test_init_all_profiles_scaffolds_each_root(tmp_path, monkeypatch):
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
        assert (project_dir / root_dir / ".skillmeat-project.toml").exists()
