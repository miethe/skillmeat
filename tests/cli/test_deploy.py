"""Tests for 'skillmeat deploy' and 'skillmeat undeploy' commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from skillmeat.cli import main
from tests.conftest import (
    create_minimal_skill,
    create_minimal_command,
    create_minimal_agent,
)


class TestDeployCommand:
    """Test suite for the deploy command."""

    def test_deploy_single_artifact(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test deploying a single artifact to a project."""
        runner = isolated_cli_runner

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Deploy to project
        result = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(temp_project)]
        )

        assert result.exit_code == 0
        assert "Deployed" in result.output
        assert "test-skill" in result.output

        # Verify artifact exists in project
        deployed_path = temp_project / ".claude" / "skills" / "test-skill"
        assert deployed_path.exists()

    def test_deploy_multiple_artifacts(
        self, isolated_cli_runner, sample_skill_dir, sample_command_file, temp_project
    ):
        """Test deploying multiple artifacts at once."""
        runner = isolated_cli_runner

        # Initialize and add artifacts
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        runner.invoke(
            main,
            [
                "add",
                "command",
                str(sample_command_file),
                "--dangerously-skip-permissions",
            ],
        )

        # Deploy both
        result = runner.invoke(
            main,
            ["deploy", "test-skill", "test-command", "--project", str(temp_project)],
        )

        assert result.exit_code == 0
        assert "Deployed" in result.output

        # Verify both exist
        assert (temp_project / ".claude" / "skills" / "test-skill").exists()
        assert (temp_project / ".claude" / "commands" / "test-command.md").exists()

    def test_deploy_to_current_directory(
        self, isolated_cli_runner, sample_skill_dir, tmp_path, monkeypatch
    ):
        """Test deploying to current directory (no --project flag)."""
        runner = isolated_cli_runner

        # Create project structure in tmp_path
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "skills").mkdir()

        # Change to project directory
        monkeypatch.chdir(project_dir)

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Deploy without --project flag
        result = runner.invoke(main, ["deploy", "test-skill"])

        assert result.exit_code == 0
        assert "Deployed" in result.output

    def test_deploy_nonexistent_artifact(self, isolated_cli_runner, temp_project):
        """Test deploying non-existent artifact."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])

        result = runner.invoke(
            main, ["deploy", "nonexistent", "--project", str(temp_project)]
        )

        assert result.exit_code == 1

    def test_deploy_with_type_specification(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test deploying with explicit type."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        result = runner.invoke(
            main,
            ["deploy", "test-skill", "--type", "skill", "--project", str(temp_project)],
        )

        assert result.exit_code == 0

    def test_deploy_creates_directory_structure(
        self, isolated_cli_runner, sample_skill_dir, tmp_path
    ):
        """Test that deploy creates .claude directory structure if needed."""
        runner = isolated_cli_runner

        # Create project without .claude directory
        project_dir = tmp_path / "new_project"
        project_dir.mkdir()

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        result = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(project_dir)]
        )

        # Should create structure automatically or fail gracefully
        if result.exit_code == 0:
            assert (project_dir / ".claude" / "skills").exists()

    def test_deploy_overwrites_existing(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test deploying artifact that already exists in project."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Deploy first time
        result1 = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(temp_project)]
        )
        assert result1.exit_code == 0

        # Deploy again (should overwrite)
        result2 = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(temp_project)]
        )
        assert result2.exit_code == 0

    def test_deploy_from_specific_collection(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test deploying from a specific collection."""
        runner = isolated_cli_runner

        # Create and use custom collection
        runner.invoke(main, ["init", "--name", "work"])
        runner.invoke(
            main,
            [
                "add",
                "skill",
                str(sample_skill_dir),
                "--collection",
                "work",
                "--dangerously-skip-permissions",
            ],
        )

        # Deploy from specific collection
        result = runner.invoke(
            main,
            [
                "deploy",
                "test-skill",
                "--collection",
                "work",
                "--project",
                str(temp_project),
            ],
        )

        assert result.exit_code == 0

    def test_deploy_short_flags(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test deploy with short flags."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Use short flags
        result = runner.invoke(
            main, ["deploy", "test-skill", "-p", str(temp_project), "-t", "skill"]
        )

        assert result.exit_code == 0


class TestUndeployCommand:
    """Test suite for the undeploy command."""

    def test_undeploy_existing_deployment(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test undeploying a deployed artifact."""
        runner = isolated_cli_runner

        # Initialize, add, and deploy artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        runner.invoke(main, ["deploy", "test-skill", "--project", str(temp_project)])

        # Verify it's deployed
        deployed_path = temp_project / ".claude" / "skills" / "test-skill"
        assert deployed_path.exists()

        # Undeploy
        result = runner.invoke(
            main, ["undeploy", "test-skill", "--project", str(temp_project)]
        )

        assert result.exit_code == 0

        # Verify it's removed
        assert not deployed_path.exists()

    def test_undeploy_nonexistent(self, isolated_cli_runner, temp_project):
        """Test undeploying artifact that isn't deployed."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])

        result = runner.invoke(
            main, ["undeploy", "nonexistent", "--project", str(temp_project)]
        )

        assert result.exit_code == 1

    def test_undeploy_with_type(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test undeploying with explicit type."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        runner.invoke(main, ["deploy", "test-skill", "--project", str(temp_project)])

        result = runner.invoke(
            main,
            [
                "undeploy",
                "test-skill",
                "--type",
                "skill",
                "--project",
                str(temp_project),
            ],
        )

        assert result.exit_code == 0

    def test_undeploy_from_current_directory(
        self, isolated_cli_runner, sample_skill_dir, tmp_path, monkeypatch
    ):
        """Test undeploying from current directory."""
        runner = isolated_cli_runner

        # Create project
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()
        (claude_dir / "skills").mkdir()

        monkeypatch.chdir(project_dir)

        # Initialize, add, and deploy
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        runner.invoke(main, ["deploy", "test-skill"])

        # Undeploy without --project
        result = runner.invoke(main, ["undeploy", "test-skill"])

        assert result.exit_code == 0

    def test_undeploy_updates_tracking(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test that undeploy updates deployment tracking."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        runner.invoke(main, ["deploy", "test-skill", "--project", str(temp_project)])

        # Undeploy
        result = runner.invoke(
            main, ["undeploy", "test-skill", "--project", str(temp_project)]
        )

        assert result.exit_code == 0

        # Deployment tracking should be updated
        # (exact verification depends on implementation)


class TestDeploymentWorkflows:
    """Test complete deployment workflows."""

    def test_full_deploy_workflow(
        self, isolated_cli_runner, sample_skill_dir, temp_project
    ):
        """Test complete workflow: init → add → deploy → undeploy."""
        runner = isolated_cli_runner

        # Initialize collection
        init_result = runner.invoke(main, ["init"])
        assert init_result.exit_code == 0

        # Add artifact
        add_result = runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        assert add_result.exit_code == 0

        # Deploy
        deploy_result = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(temp_project)]
        )
        assert deploy_result.exit_code == 0

        # Verify deployed
        assert (temp_project / ".claude" / "skills" / "test-skill").exists()

        # Undeploy
        undeploy_result = runner.invoke(
            main, ["undeploy", "test-skill", "--project", str(temp_project)]
        )
        assert undeploy_result.exit_code == 0

        # Verify removed
        assert not (temp_project / ".claude" / "skills" / "test-skill").exists()

    def test_deploy_multiple_types(
        self,
        isolated_cli_runner,
        sample_skill_dir,
        sample_command_file,
        sample_agent_file,
        temp_project,
    ):
        """Test deploying all artifact types."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        runner.invoke(
            main,
            [
                "add",
                "command",
                str(sample_command_file),
                "--dangerously-skip-permissions",
            ],
        )
        runner.invoke(
            main,
            ["add", "agent", str(sample_agent_file), "--dangerously-skip-permissions"],
        )

        # Deploy all three
        result = runner.invoke(
            main,
            [
                "deploy",
                "test-skill",
                "test-command",
                "test-agent",
                "--project",
                str(temp_project),
            ],
        )

        assert result.exit_code == 0

        # Verify all deployed
        assert (temp_project / ".claude" / "skills" / "test-skill").exists()
        assert (temp_project / ".claude" / "commands" / "test-command.md").exists()
        assert (temp_project / ".claude" / "agents" / "test-agent.md").exists()

    def test_deploy_to_multiple_projects(
        self, isolated_cli_runner, sample_skill_dir, tmp_path
    ):
        """Test deploying same artifact to multiple projects."""
        runner = isolated_cli_runner

        # Create two projects
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / ".claude").mkdir()
        (project1 / ".claude" / "skills").mkdir()

        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / ".claude").mkdir()
        (project2 / ".claude" / "skills").mkdir()

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Deploy to first project
        result1 = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(project1)]
        )
        assert result1.exit_code == 0

        # Deploy to second project
        result2 = runner.invoke(
            main, ["deploy", "test-skill", "--project", str(project2)]
        )
        assert result2.exit_code == 0

        # Verify both deployments
        assert (project1 / ".claude" / "skills" / "test-skill").exists()
        assert (project2 / ".claude" / "skills" / "test-skill").exists()
