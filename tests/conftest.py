"""Shared pytest fixtures and utilities for SkillMeat tests.

This module provides common fixtures used across all test suites:
- Temporary directories for collections and projects
- Sample artifact fixtures
- Mock GitHub client
- Isolated filesystem contexts
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# Temporary Directory Fixtures
# =============================================================================

@pytest.fixture
def temp_collection(tmp_path):
    """Create a temporary collection directory.

    Returns:
        Path: Path to temporary collection directory

    Example:
        def test_something(temp_collection):
            collection_path = temp_collection / "my-collection"
            collection_path.mkdir()
    """
    collection_dir = tmp_path / "test_collection"
    collection_dir.mkdir(parents=True, exist_ok=True)
    return collection_dir


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory and set HOME environment variable.

    Returns:
        Path: Path to temporary home directory

    Example:
        def test_something(temp_home):
            # HOME is set to temp_home
            config_dir = temp_home / ".skillmeat"
    """
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    return home_dir


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project directory with .claude/ structure.

    Returns:
        Path: Path to temporary project directory

    Example:
        def test_deploy(temp_project):
            claude_dir = temp_project / ".claude"
            assert claude_dir.exists()
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create .claude directory structure
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    (claude_dir / "skills").mkdir()
    (claude_dir / "commands").mkdir()
    (claude_dir / "agents").mkdir()

    return project_dir


@pytest.fixture
def isolated_fs(tmp_path, monkeypatch):
    """Create an isolated filesystem with temporary home and working directory.

    Returns:
        Dict[str, Path]: Dictionary with 'home', 'cwd', and 'tmp' paths

    Example:
        def test_something(isolated_fs):
            home = isolated_fs['home']
            cwd = isolated_fs['cwd']
    """
    home_dir = tmp_path / "home"
    work_dir = tmp_path / "work"

    home_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.chdir(work_dir)

    return {
        "home": home_dir,
        "cwd": work_dir,
        "tmp": tmp_path
    }


# =============================================================================
# Sample Artifact Fixtures
# =============================================================================

@pytest.fixture
def sample_artifacts():
    """Return paths to sample test fixtures.

    Returns:
        Dict[str, Path]: Dictionary with paths to sample artifacts

    Example:
        def test_something(sample_artifacts):
            skill_path = sample_artifacts['skill']
            command_path = sample_artifacts['command']
    """
    fixtures_dir = Path(__file__).parent / "fixtures"

    return {
        "skill": fixtures_dir / "sample_skills" / "test-skill",
        "skill_md": fixtures_dir / "sample_skills" / "test-skill" / "SKILL.md",
        "command": fixtures_dir / "sample_commands" / "test-command.md",
        "agent": fixtures_dir / "sample_agents" / "test-agent.md",
        "fixtures_dir": fixtures_dir,
    }


@pytest.fixture
def sample_skill_dir(sample_artifacts, tmp_path):
    """Create a copy of the sample skill in a temporary directory.

    Returns:
        Path: Path to copied skill directory

    Example:
        def test_something(sample_skill_dir):
            # sample_skill_dir is a temporary copy you can modify
            skill_md = sample_skill_dir / "SKILL.md"
    """
    skill_src = sample_artifacts["skill"]
    skill_dst = tmp_path / "test-skill"

    shutil.copytree(skill_src, skill_dst)
    return skill_dst


@pytest.fixture
def sample_command_file(sample_artifacts, tmp_path):
    """Create a copy of the sample command in a temporary directory.

    Returns:
        Path: Path to copied command file
    """
    command_src = sample_artifacts["command"]
    command_dst = tmp_path / "test-command.md"

    shutil.copy2(command_src, command_dst)
    return command_dst


@pytest.fixture
def sample_agent_file(sample_artifacts, tmp_path):
    """Create a copy of the sample agent in a temporary directory.

    Returns:
        Path: Path to copied agent file
    """
    agent_src = sample_artifacts["agent"]
    agent_dst = tmp_path / "test-agent.md"

    shutil.copy2(agent_src, agent_dst)
    return agent_dst


# =============================================================================
# Mock GitHub Client
# =============================================================================

@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client for testing.

    Returns:
        MagicMock: Mock GitHub client with common methods

    Example:
        def test_something(mock_github_client):
            mock_github_client.clone_repo.return_value = "/path/to/repo"
    """
    mock = MagicMock()

    # Configure common return values
    mock.clone_repo.return_value = "/tmp/mocked_repo"
    mock.resolve_version.return_value = ("v1.0.0", "abc123def456")
    mock.get_latest_tag.return_value = "v1.0.0"
    mock.get_commit_sha.return_value = "abc123def456"

    return mock


@pytest.fixture
def mock_github_source(sample_artifacts):
    """Create a mock GitHub source that returns local fixtures.

    Returns:
        MagicMock: Mock GitHub source

    Example:
        def test_something(mock_github_source):
            result = mock_github_source.fetch("user/repo/skill")
            assert result['artifact_path'] is not None
    """
    mock = MagicMock()

    def mock_fetch(spec_str, target_dir=None):
        """Mock fetch that copies fixture to target directory."""
        # Return sample skill by default
        skill_path = sample_artifacts["skill"]

        if target_dir:
            target_path = Path(target_dir) / "test-skill"
            shutil.copytree(skill_path, target_path)
            return {
                "artifact_path": target_path,
                "metadata": {
                    "title": "Test Skill",
                    "description": "A sample skill for testing",
                    "version": "1.0.0",
                },
                "resolved_version": "v1.0.0",
                "resolved_sha": "abc123",
            }

        return {
            "artifact_path": skill_path,
            "metadata": {
                "title": "Test Skill",
                "description": "A sample skill for testing",
                "version": "1.0.0",
            },
            "resolved_version": "v1.0.0",
            "resolved_sha": "abc123",
        }

    mock.fetch.side_effect = mock_fetch
    mock.validate.return_value = True

    return mock


# =============================================================================
# Configuration and Environment
# =============================================================================

@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for isolated testing.

    Removes common environment variables that might affect tests.

    Example:
        def test_something(clean_env):
            # Environment is clean
            assert "SKILLMEAT_HOME" not in os.environ
    """
    vars_to_remove = [
        "SKILLMEAT_HOME",
        "SKILLMEAT_CONFIG",
        "GITHUB_TOKEN",
    ]

    for var in vars_to_remove:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_config():
    """Create a mock ConfigManager.

    Returns:
        MagicMock: Mock config manager with default settings
    """
    mock = MagicMock()

    # Default config values
    mock.get.return_value = None
    mock.get_default_collection.return_value = "default"
    mock.get_github_token.return_value = None
    mock.get_update_strategy.return_value = "prompt"

    return mock


# =============================================================================
# CLI Testing Utilities
# =============================================================================

@pytest.fixture
def cli_runner():
    """Create a Click CLI test runner.

    Returns:
        CliRunner: Click test runner instance

    Example:
        def test_cli(cli_runner):
            from skillmeat.cli import main
            result = cli_runner.invoke(main, ['--help'])
            assert result.exit_code == 0
    """
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def isolated_cli_runner(tmp_path, monkeypatch):
    """Create a CLI runner with isolated filesystem.

    Returns:
        CliRunner: Click test runner with isolated filesystem
    """
    from click.testing import CliRunner

    # Set up isolated environment
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))

    return CliRunner()


# =============================================================================
# Helper Functions
# =============================================================================

def create_minimal_skill(path: Path, name: str = "test-skill") -> Path:
    """Create a minimal valid skill directory for testing.

    Args:
        path: Parent directory to create skill in
        name: Name of the skill directory

    Returns:
        Path: Path to created skill directory
    """
    skill_dir = path / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
title: Test Skill
description: A minimal test skill
version: 1.0.0
---

# Test Skill

Minimal skill for testing.
""")

    return skill_dir


def create_minimal_command(path: Path, name: str = "test-command.md") -> Path:
    """Create a minimal valid command file for testing.

    Args:
        path: Parent directory to create command in
        name: Filename for the command

    Returns:
        Path: Path to created command file
    """
    command_file = path / name
    command_file.write_text("""---
title: Test Command
description: A minimal test command
version: 1.0.0
---

# Test Command

Minimal command for testing.
""")

    return command_file


def create_minimal_agent(path: Path, name: str = "test-agent.md") -> Path:
    """Create a minimal valid agent file for testing.

    Args:
        path: Parent directory to create agent in
        name: Filename for the agent

    Returns:
        Path: Path to created agent file
    """
    agent_file = path / name
    agent_file.write_text("""---
title: Test Agent
description: A minimal test agent
version: 1.0.0
---

# Test Agent

Minimal agent for testing.
""")

    return agent_file


# Export helper functions for use in tests
pytest.create_minimal_skill = create_minimal_skill
pytest.create_minimal_command = create_minimal_command
pytest.create_minimal_agent = create_minimal_agent
