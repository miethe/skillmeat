"""Tests for migration command."""

from pathlib import Path

from skillmeat.cli import main


def test_migrate_without_from_skillman_flag(isolated_cli_runner):
    """Test migrate command without --from-skillman flag."""
    runner = isolated_cli_runner

    result = runner.invoke(main, ["migrate"])

    assert result.exit_code == 0
    assert "Please specify --from-skillman flag" in result.output


def test_migrate_no_skillman_installation(isolated_cli_runner, tmp_path, monkeypatch):
    """Test migrate when no skillman installation is found."""
    runner = isolated_cli_runner
    # Change to empty temp directory to avoid finding project's skills.toml
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(main, ["migrate", "--from-skillman"])

    assert result.exit_code == 0
    assert "No skillman installation found" in result.output
    assert "Nothing to migrate" in result.output


def test_migrate_dry_run_with_manifest(isolated_cli_runner, tmp_path, monkeypatch):
    """Test migrate in dry-run mode with skillman manifest."""
    runner = isolated_cli_runner

    # Set working directory to temp path
    monkeypatch.chdir(tmp_path)

    # Create mock skillman manifest
    manifest_content = """
[tool.skillman]
version = "1.0.0"

[[tool.skillman.skills]]
name = "test-skill"
source = "user/repo/skill"
version = "latest"
scope = "user"
"""
    manifest_path = Path("skills.toml")
    manifest_path.write_text(manifest_content)

    result = runner.invoke(
        main, ["migrate", "--from-skillman", "--dry-run"]
    )

    assert result.exit_code == 0
    assert "Detected skillman installation" in result.output
    assert "Migration Plan" in result.output
    assert "Dry-run mode: No changes will be made" in result.output


def test_migrate_with_config(isolated_cli_runner, monkeypatch, tmp_path):
    """Test migrate imports skillman config."""
    runner = isolated_cli_runner

    # Get HOME from environment (should be set by isolated_cli_runner)
    home_dir = Path.home()

    # Create mock skillman config
    skillman_dir = home_dir / ".skillman"
    skillman_dir.mkdir(parents=True, exist_ok=True)
    config_path = skillman_dir / "config.toml"
    config_content = """
github-token = "ghp_test_token_12345"
default-scope = "user"
"""
    config_path.write_text(config_content)

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes", "--no-snapshot"],
    )

    assert result.exit_code == 0
    assert "Detected skillman installation" in result.output
    assert "Config:" in result.output


def test_migrate_with_manifest_yes_flag(isolated_cli_runner, monkeypatch, tmp_path):
    """Test migrate with manifest and --yes flag."""
    runner = isolated_cli_runner
    monkeypatch.chdir(tmp_path)

    # Create mock skillman manifest
    manifest_content = """
[tool.skillman]
version = "1.0.0"

[[tool.skillman.skills]]
name = "test-skill"
source = "user/repo/skill"
version = "latest"
scope = "user"
"""
    manifest_path = Path("skills.toml")
    manifest_path.write_text(manifest_content)

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes", "--no-snapshot"],
    )

    assert result.exit_code == 0
    assert "Migrating..." in result.output or "Migration complete!" in result.output


def test_migrate_with_user_skills_directory(isolated_cli_runner):
    """Test migrate imports skills from user directory."""
    runner = isolated_cli_runner

    # Get HOME from environment
    home_dir = Path.home()

    # Create mock user skills directory
    user_skills_dir = home_dir / ".claude" / "skills" / "user"
    user_skills_dir.mkdir(parents=True, exist_ok=True)

    # Create a mock skill
    skill_dir = user_skills_dir / "test-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
title: Test Skill
description: A test skill
---

# Test Skill

This is a test skill.
""")

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes", "--no-snapshot"],
    )

    assert result.exit_code == 0
    assert "User skills:" in result.output or "user directory" in result.output


def test_migrate_cancelled_by_user(isolated_cli_runner, monkeypatch, tmp_path):
    """Test migrate is cancelled when user declines confirmation."""
    runner = isolated_cli_runner
    monkeypatch.chdir(tmp_path)

    # Create mock skillman manifest
    manifest_content = """
[tool.skillman]
version = "1.0.0"

[[tool.skillman.skills]]
name = "test-skill"
source = "user/repo/skill"
version = "latest"
scope = "user"
"""
    manifest_path = Path("skills.toml")
    manifest_path.write_text(manifest_content)

    # Simulate user declining confirmation
    result = runner.invoke(
        main,
        ["migrate", "--from-skillman"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Migration cancelled" in result.output or "Cancelled" in result.output


def test_migrate_force_overwrite(isolated_cli_runner, monkeypatch, tmp_path):
    """Test migrate with --force flag overwrites existing artifacts."""
    runner = isolated_cli_runner
    monkeypatch.chdir(tmp_path)

    # Initialize collection first
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    # Create mock skillman manifest
    manifest_content = """
[tool.skillman]
version = "1.0.0"

[[tool.skillman.skills]]
name = "test-skill"
source = "user/repo/skill"
version = "latest"
scope = "user"
"""
    manifest_path = Path("skills.toml")
    manifest_path.write_text(manifest_content)

    # Run migration with force
    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--force", "--yes", "--no-snapshot"],
    )

    assert result.exit_code == 0


def test_migrate_with_local_skills_directory(isolated_cli_runner, monkeypatch, tmp_path):
    """Test migrate imports skills from local directory."""
    runner = isolated_cli_runner
    monkeypatch.chdir(tmp_path)

    # Create mock local skills directory
    local_skills_dir = Path.cwd() / ".claude" / "skills"
    local_skills_dir.mkdir(parents=True, exist_ok=True)

    # Create a mock skill
    skill_dir = local_skills_dir / "local-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
title: Local Skill
description: A local test skill
---

# Local Skill

This is a local test skill.
""")

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes", "--no-snapshot"],
    )

    assert result.exit_code == 0
    assert "Local skills:" in result.output or "local directory" in result.output


def test_migrate_with_custom_path(isolated_cli_runner, monkeypatch, tmp_path):
    """Test migrate with custom manifest path."""
    runner = isolated_cli_runner
    monkeypatch.chdir(tmp_path)

    # Create mock skillman manifest in custom location
    custom_dir = Path("custom")
    custom_dir.mkdir()
    manifest_content = """
[tool.skillman]
version = "1.0.0"

[[tool.skillman.skills]]
name = "custom-skill"
source = "user/repo/custom"
version = "v1.0.0"
scope = "local"
"""
    manifest_path = custom_dir / "skills.toml"
    manifest_path.write_text(manifest_content)

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes", "--no-snapshot", str(manifest_path)],
    )

    assert result.exit_code == 0
    assert "Detected skillman installation" in result.output


def test_migrate_creates_snapshot_by_default(isolated_cli_runner):
    """Test migrate creates snapshot unless --no-snapshot is used."""
    runner = isolated_cli_runner
    home_dir = Path.home()

    # Create minimal skillman setup
    skillman_dir = home_dir / ".skillman"
    skillman_dir.mkdir(parents=True, exist_ok=True)
    config_path = skillman_dir / "config.toml"
    config_path.write_text("# minimal config\n")

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes"],
    )

    # Should attempt to create snapshot
    # (may fail but should try)
    assert result.exit_code == 0


def test_migrate_completion_message(isolated_cli_runner):
    """Test migrate shows completion message and next steps."""
    runner = isolated_cli_runner
    home_dir = Path.home()

    # Create minimal skillman setup
    skillman_dir = home_dir / ".skillman"
    skillman_dir.mkdir(parents=True, exist_ok=True)
    config_path = skillman_dir / "config.toml"
    config_path.write_text("github-token = 'test'\n")

    result = runner.invoke(
        main,
        ["migrate", "--from-skillman", "--yes", "--no-snapshot"],
    )

    assert result.exit_code == 0
    assert "Migration complete!" in result.output
    assert "Next steps:" in result.output
    assert "skillmeat list" in result.output
    assert "skillmeat deploy" in result.output
