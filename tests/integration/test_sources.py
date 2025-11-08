"""Integration tests for artifact sources."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from skillmeat.core.artifact import ArtifactType
from skillmeat.sources.github import GitHubSource
from skillmeat.sources.local import LocalSource


class TestLocalSourceIntegration:
    """Integration tests for LocalSource."""

    def test_fetch_real_skill_directory(self, tmp_path):
        """Test fetching a real skill directory structure."""
        # Create a realistic skill structure
        skill_dir = tmp_path / "python-helper"
        skill_dir.mkdir()

        # Create SKILL.md with frontmatter
        (skill_dir / "SKILL.md").write_text(
            """---
title: Python Helper
description: Helps with Python development
author: Test Developer
license: MIT
version: 1.0.0
tags:
  - python
  - development
  - productivity
dependencies:
  - black
  - pytest
---

# Python Helper Skill

This skill provides Python development assistance including:

- Code formatting with black
- Running pytest tests
- Type checking with mypy

## Usage

Simply activate this skill and ask for Python help.
"""
        )

        # Create additional files
        (skill_dir / "README.md").write_text("# Python Helper\n\nDocumentation here.")
        (skill_dir / "config.json").write_text('{"enabled": true}')

        # Test fetch
        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        assert result.artifact_path == skill_dir
        assert result.metadata.title == "Python Helper"
        assert result.metadata.description == "Helps with Python development"
        assert result.metadata.author == "Test Developer"
        assert result.metadata.license == "MIT"
        assert result.metadata.version == "1.0.0"
        assert len(result.metadata.tags) == 3
        assert "python" in result.metadata.tags
        assert len(result.metadata.dependencies) == 2
        assert "black" in result.metadata.dependencies

    def test_fetch_real_command_file(self, tmp_path):
        """Test fetching a real command file."""
        command_file = tmp_path / "code-review.md"
        command_file.write_text(
            """---
title: Code Review
description: Performs code review on changes
author: Test Developer
version: 1.0.0
---

# Code Review Command

This command reviews code changes and provides feedback.

## Instructions

Review the code changes in the current branch and provide:
1. Code quality assessment
2. Potential bugs or issues
3. Suggestions for improvement
"""
        )

        source = LocalSource()
        result = source.fetch(str(command_file), ArtifactType.COMMAND)

        assert result.artifact_path == command_file
        assert result.metadata.title == "Code Review"
        assert result.metadata.description == "Performs code review on changes"

    def test_fetch_real_agent_directory(self, tmp_path):
        """Test fetching a real agent directory."""
        agent_dir = tmp_path / "senior-engineer"
        agent_dir.mkdir()

        (agent_dir / "AGENT.md").write_text(
            """---
title: Senior Engineer Agent
description: Acts as a senior software engineer
author: Test Developer
version: 2.0.0
tags:
  - agent
  - engineering
  - architecture
---

# Senior Engineer Agent

This agent acts as a senior software engineer, providing:

- Architectural guidance
- Code review feedback
- Best practices recommendations
- Performance optimization suggestions

## Behavior

The agent will:
1. Ask clarifying questions about requirements
2. Suggest appropriate design patterns
3. Consider scalability and maintainability
4. Provide detailed code examples
"""
        )

        (agent_dir / "context.md").write_text("Additional context for the agent.")

        source = LocalSource()
        result = source.fetch(str(agent_dir), ArtifactType.AGENT)

        assert result.artifact_path == agent_dir
        assert result.metadata.title == "Senior Engineer Agent"
        assert result.metadata.version == "2.0.0"
        assert "engineering" in result.metadata.tags

    def test_validate_multiple_artifact_types(self, tmp_path):
        """Test validating different artifact types."""
        source = LocalSource()

        # Create different artifact types
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        command_file = tmp_path / "command.md"
        command_file.write_text("# Command")

        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent")

        # Validate each
        assert source.validate(skill_dir, ArtifactType.SKILL) is True
        assert source.validate(command_file, ArtifactType.COMMAND) is True
        assert source.validate(agent_file, ArtifactType.AGENT) is True

        # Cross-validate (wrong types)
        # Skill directory is not a valid command (commands should be files or have .md)
        # But since skill_dir might have SKILL.md, it won't validate as command
        assert source.validate(command_file, ArtifactType.SKILL) is False

    def test_fetch_without_metadata(self, tmp_path):
        """Test fetching artifact without YAML frontmatter."""
        skill_dir = tmp_path / "simple-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            """# Simple Skill

This is a simple skill without YAML frontmatter.

It should still work and extract the description from the content.
"""
        )

        source = LocalSource()
        result = source.fetch(str(skill_dir), ArtifactType.SKILL)

        assert result.artifact_path == skill_dir
        # Should extract description from first paragraph
        assert result.metadata.description is not None
        assert "simple skill" in result.metadata.description.lower()


class TestGitHubSourceIntegration:
    """Integration tests for GitHubSource (with mocking)."""

    @patch("skillmeat.sources.github.subprocess.run")
    @patch("skillmeat.sources.github.requests.Session.get")
    def test_fetch_workflow(self, mock_get, mock_subprocess, tmp_path):
        """Test complete fetch workflow with mocked GitHub."""
        # Mock API responses
        repo_response = type(
            "MockResponse",
            (),
            {
                "json": lambda self: {"default_branch": "main"},
                "raise_for_status": lambda self: None,
            },
        )()

        commit_response = type(
            "MockResponse",
            (),
            {
                "json": lambda self: {"sha": "abc123def456"},
                "raise_for_status": lambda self: None,
            },
        )()

        mock_get.side_effect = [repo_response, commit_response]

        # Mock git commands
        def subprocess_side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "git" and cmd[1] == "clone":
                # Create fake repo with skill
                dest = Path(cmd[-1])
                dest.mkdir(parents=True, exist_ok=True)
                skill_dir = dest / "python-skill"
                skill_dir.mkdir()
                (skill_dir / "SKILL.md").write_text("# Python Skill")
                return type("Result", (), {"returncode": 0, "stderr": ""})()
            elif cmd[0] == "git" and "rev-parse" in cmd:
                return type(
                    "Result",
                    (),
                    {"returncode": 0, "stdout": "abc123def456\n", "stderr": ""},
                )()
            elif cmd[0] == "git" and "checkout" in cmd:
                return type("Result", (), {"returncode": 0, "stderr": ""})()
            elif cmd[0] == "git" and "fetch" in cmd:
                return type("Result", (), {"returncode": 0, "stderr": ""})()
            return type("Result", (), {"returncode": 0, "stderr": ""})()

        mock_subprocess.side_effect = subprocess_side_effect

        # Test fetch
        source = GitHubSource()
        result = source.fetch("anthropics/skills/python-skill", ArtifactType.SKILL)

        assert result.resolved_sha == "abc123def456"
        assert result.upstream_url is not None
        assert "github.com" in result.upstream_url

    def test_validate_calls_validator(self, tmp_path):
        """Test that validate delegates to ArtifactValidator."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill")

        source = GitHubSource()
        result = source.validate(skill_dir, ArtifactType.SKILL)

        assert result is True
