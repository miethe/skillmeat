"""Tests for 'skillmeat list', 'skillmeat show', and 'skillmeat remove' commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from skillmeat.cli import main
from skillmeat.core.artifact import ArtifactManager, ArtifactType
from tests.conftest import (
    create_minimal_skill,
    create_minimal_command,
    create_minimal_agent,
)


class TestListCommand:
    """Test suite for the list command."""

    def test_list_empty_collection(self, isolated_cli_runner):
        """Test listing an empty collection."""
        runner = isolated_cli_runner

        # Initialize empty collection
        runner.invoke(main, ["init"])

        # List artifacts
        result = runner.invoke(main, ["list"])

        assert result.exit_code == 0
        assert "No artifacts found" in result.output

    def test_list_with_artifacts(self, isolated_cli_runner, sample_skill_dir):
        """Test listing collection with artifacts."""
        runner = isolated_cli_runner

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # List artifacts
        result = runner.invoke(main, ["list"])

        assert result.exit_code == 0
        assert "Artifacts" in result.output
        assert "test-skill" in result.output
        assert "skill" in result.output

    def test_list_filter_by_type_skill(
        self, isolated_cli_runner, sample_skill_dir, sample_command_file
    ):
        """Test filtering list by skill type."""
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

        # List only skills
        result = runner.invoke(main, ["list", "--type", "skill"])

        assert result.exit_code == 0
        assert "test-skill" in result.output
        # Command should not appear
        assert "test-command" not in result.output

    def test_list_filter_by_type_command(
        self, isolated_cli_runner, sample_skill_dir, sample_command_file
    ):
        """Test filtering list by command type."""
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

        # List only commands
        result = runner.invoke(main, ["list", "--type", "command"])

        assert result.exit_code == 0
        assert "test-command" in result.output
        # Skill should not appear
        assert "test-skill" not in result.output

    def test_list_with_tags(self, isolated_cli_runner, sample_skill_dir):
        """Test listing with tags displayed."""
        runner = isolated_cli_runner

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # List with tags
        result = runner.invoke(main, ["list", "--tags"])

        assert result.exit_code == 0
        assert "Tags" in result.output

    def test_list_short_flags(self, isolated_cli_runner, sample_skill_dir):
        """Test list command with short flags."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Test -t flag
        result = runner.invoke(main, ["list", "-t", "skill"])
        assert result.exit_code == 0


class TestShowCommand:
    """Test suite for the show command."""

    def test_show_existing_artifact(self, isolated_cli_runner, sample_skill_dir):
        """Test showing details of existing artifact."""
        runner = isolated_cli_runner

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Show artifact
        result = runner.invoke(main, ["show", "test-skill"])

        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_show_nonexistent_artifact(self, isolated_cli_runner):
        """Test showing non-existent artifact."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])

        # Try to show non-existent artifact
        result = runner.invoke(main, ["show", "nonexistent"])

        assert result.exit_code == 1
        # Should show error message

    def test_show_with_type_specification(self, isolated_cli_runner, sample_skill_dir):
        """Test showing artifact with explicit type."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Show with type
        result = runner.invoke(main, ["show", "test-skill", "--type", "skill"])

        assert result.exit_code == 0
        assert "test-skill" in result.output

    def test_show_ambiguous_name(self, isolated_cli_runner, tmp_path):
        """Test showing artifact when name is ambiguous (same name, different types)."""
        runner = isolated_cli_runner

        # Create skill and command with same name
        skill_dir = create_minimal_skill(tmp_path, "shared-name")
        command_file = create_minimal_command(tmp_path, "shared-name.md")

        runner.invoke(main, ["init"])
        runner.invoke(
            main, ["add", "skill", str(skill_dir), "--dangerously-skip-permissions"]
        )
        runner.invoke(
            main,
            [
                "add",
                "command",
                str(command_file),
                "--name",
                "shared-name",
                "--dangerously-skip-permissions",
            ],
        )

        # Try to show without type (should fail or prompt)
        result = runner.invoke(main, ["show", "shared-name"])

        # Should require type specification
        assert result.exit_code == 1 or "ambiguous" in result.output.lower()


class TestRemoveCommand:
    """Test suite for the remove command."""

    def test_remove_existing_artifact(
        self, isolated_cli_runner, sample_skill_dir, temp_home
    ):
        """Test removing an existing artifact."""
        runner = isolated_cli_runner

        # Initialize and add artifact
        runner.invoke(main, ["init"])
        add_result = runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )
        assert add_result.exit_code == 0

        # Remove artifact
        result = runner.invoke(main, ["remove", "test-skill"])

        assert result.exit_code == 0

        # Verify artifact is removed from manifest
        list_result = runner.invoke(main, ["list"])
        assert (
            "test-skill" not in list_result.output
            or "No artifacts found" in list_result.output
        )

    def test_remove_nonexistent_artifact(self, isolated_cli_runner):
        """Test removing non-existent artifact."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])

        # Try to remove non-existent artifact
        result = runner.invoke(main, ["remove", "nonexistent"])

        assert result.exit_code == 1

    def test_remove_with_keep_files(
        self, isolated_cli_runner, sample_skill_dir, temp_home
    ):
        """Test removing artifact but keeping files."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Remove with --keep-files
        result = runner.invoke(main, ["remove", "test-skill", "--keep-files"])

        assert result.exit_code == 0

        # Artifact should be removed from manifest but files might still exist
        list_result = runner.invoke(main, ["list"])
        assert (
            "test-skill" not in list_result.output
            or "No artifacts found" in list_result.output
        )

    def test_remove_with_type_specification(
        self, isolated_cli_runner, sample_skill_dir
    ):
        """Test removing artifact with explicit type."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Remove with type
        result = runner.invoke(main, ["remove", "test-skill", "--type", "skill"])

        assert result.exit_code == 0

    def test_remove_ambiguous_name(self, isolated_cli_runner, tmp_path):
        """Test removing artifact when name is ambiguous."""
        runner = isolated_cli_runner

        # Create skill and command with same name
        skill_dir = create_minimal_skill(tmp_path, "shared-name")
        command_file = create_minimal_command(tmp_path, "shared-name.md")

        runner.invoke(main, ["init"])
        runner.invoke(
            main, ["add", "skill", str(skill_dir), "--dangerously-skip-permissions"]
        )
        runner.invoke(
            main,
            [
                "add",
                "command",
                str(command_file),
                "--name",
                "shared-name",
                "--dangerously-skip-permissions",
            ],
        )

        # Try to remove without type (should fail or prompt)
        result = runner.invoke(main, ["remove", "shared-name"])

        # Should require type specification or fail
        assert result.exit_code == 1 or "ambiguous" in result.output.lower()

        # Remove with type should work
        result2 = runner.invoke(main, ["remove", "shared-name", "--type", "skill"])
        assert result2.exit_code == 0

    def test_remove_and_verify_files_deleted(
        self, isolated_cli_runner, sample_skill_dir, temp_home
    ):
        """Test that remove deletes files by default."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Get artifact path before removal
        collection_dir = temp_home / ".skillmeat" / "collections" / "default"
        artifact_path = collection_dir / "skills" / "test-skill"

        # Artifact should exist
        assert artifact_path.exists()

        # Remove artifact
        result = runner.invoke(main, ["remove", "test-skill"])
        assert result.exit_code == 0

        # Files should be deleted
        assert not artifact_path.exists()
