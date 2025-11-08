"""Tests for 'skillmeat status' and 'skillmeat update' commands."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock

from skillmeat.cli import main
from tests.conftest import create_minimal_skill


class TestStatusCommand:
    """Test suite for the status command."""

    def test_status_empty_collection(self, isolated_cli_runner):
        """Test status with empty collection."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert "Checking for updates" in result.output

    def test_status_with_artifacts(self, isolated_cli_runner, sample_skill_dir):
        """Test status with artifacts in collection."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert "Checking for updates" in result.output

    @patch('skillmeat.core.artifact.ArtifactManager.check_updates')
    def test_status_shows_available_updates(self, mock_check_updates, isolated_cli_runner, sample_skill_dir):
        """Test status when updates are available."""
        runner = isolated_cli_runner

        # Mock updates available
        mock_check_updates.return_value = {
            "updates_available": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "current_version": "1.0.0",
                    "latest_version": "2.0.0",
                }
            ],
            "up_to_date": [],
        }

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert "Updates available" in result.output
        assert "test-skill" in result.output
        assert "1.0.0" in result.output
        assert "2.0.0" in result.output

    @patch('skillmeat.core.artifact.ArtifactManager.check_updates')
    def test_status_all_up_to_date(self, mock_check_updates, isolated_cli_runner, sample_skill_dir):
        """Test status when all artifacts are up to date."""
        runner = isolated_cli_runner

        # Mock all up to date
        mock_check_updates.return_value = {
            "updates_available": [],
            "up_to_date": [
                {
                    "name": "test-skill",
                    "type": "skill",
                }
            ],
        }

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert "Up to date" in result.output
        assert "test-skill" in result.output

    @patch('skillmeat.core.deployment.DeploymentManager.check_deployment_status')
    def test_status_deployment_check(self, mock_check_status, isolated_cli_runner, sample_skill_dir, temp_project):
        """Test status checks deployment status."""
        runner = isolated_cli_runner

        # Mock deployment status
        mock_check_status.return_value = {
            "modified": [],
            "synced": [
                {
                    "name": "test-skill",
                    "type": "skill",
                }
            ],
        }

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])
        runner.invoke(main, ['deploy', 'test-skill', '--project', str(temp_project)])

        result = runner.invoke(main, ['status', '--project', str(temp_project)])

        assert result.exit_code == 0
        assert "Checking deployment status" in result.output

    @patch('skillmeat.core.deployment.DeploymentManager.check_deployment_status')
    def test_status_shows_modified_deployments(self, mock_check_status, isolated_cli_runner, sample_skill_dir, temp_project):
        """Test status when deployments have local modifications."""
        runner = isolated_cli_runner

        # Mock modified deployments
        mock_check_status.return_value = {
            "modified": [
                {
                    "name": "test-skill",
                    "type": "skill",
                }
            ],
            "synced": [],
        }

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])
        runner.invoke(main, ['deploy', 'test-skill', '--project', str(temp_project)])

        result = runner.invoke(main, ['status', '--project', str(temp_project)])

        assert result.exit_code == 0
        assert "Locally modified" in result.output
        assert "test-skill" in result.output

    def test_status_specific_collection(self, isolated_cli_runner, sample_skill_dir):
        """Test status for specific collection."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init', '--name', 'work'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--collection', 'work', '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['status', '--collection', 'work'])

        assert result.exit_code == 0


class TestUpdateCommand:
    """Test suite for the update command."""

    def test_update_without_name(self, isolated_cli_runner):
        """Test update without specifying artifact name."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(main, ['update'])

        assert result.exit_code == 0
        assert "Please specify artifact name" in result.output

    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_update_single_artifact(self, mock_update, isolated_cli_runner, sample_skill_dir):
        """Test updating a single artifact."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['update', 'test-skill'])

        assert result.exit_code == 0
        assert "Updating test-skill" in result.output
        mock_update.assert_called_once()

    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_update_with_type(self, mock_update, isolated_cli_runner, sample_skill_dir):
        """Test updating with explicit type."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['update', 'test-skill', '--type', 'skill'])

        assert result.exit_code == 0
        mock_update.assert_called_once()

    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_update_with_strategy_upstream(self, mock_update, isolated_cli_runner, sample_skill_dir):
        """Test update with upstream strategy."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['update', 'test-skill', '--strategy', 'upstream'])

        assert result.exit_code == 0
        mock_update.assert_called_once()

    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_update_with_strategy_local(self, mock_update, isolated_cli_runner, sample_skill_dir):
        """Test update with local strategy."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['update', 'test-skill', '--strategy', 'local'])

        assert result.exit_code == 0
        mock_update.assert_called_once()

    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_update_with_strategy_prompt(self, mock_update, isolated_cli_runner, sample_skill_dir):
        """Test update with prompt strategy (default)."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['update', 'test-skill', '--strategy', 'prompt'])

        assert result.exit_code == 0
        mock_update.assert_called_once()

    def test_update_nonexistent_artifact(self, isolated_cli_runner):
        """Test updating non-existent artifact."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init'])

        result = runner.invoke(main, ['update', 'nonexistent'])

        assert result.exit_code == 1

    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_update_from_specific_collection(self, mock_update, isolated_cli_runner, sample_skill_dir):
        """Test updating artifact from specific collection."""
        runner = isolated_cli_runner

        runner.invoke(main, ['init', '--name', 'work'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--collection', 'work', '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['update', 'test-skill', '--collection', 'work'])

        assert result.exit_code == 0
        mock_update.assert_called_once()


class TestStatusUpdateWorkflow:
    """Test complete status/update workflows."""

    @patch('skillmeat.core.artifact.ArtifactManager.check_updates')
    @patch('skillmeat.core.artifact.ArtifactManager.update')
    def test_check_then_update_workflow(self, mock_update, mock_check_updates, isolated_cli_runner, sample_skill_dir):
        """Test workflow: status → update."""
        runner = isolated_cli_runner

        # Mock updates available
        mock_check_updates.return_value = {
            "updates_available": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "current_version": "1.0.0",
                    "latest_version": "2.0.0",
                }
            ],
            "up_to_date": [],
        }

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])

        # Check status
        status_result = runner.invoke(main, ['status'])
        assert status_result.exit_code == 0
        assert "Updates available" in status_result.output

        # Update artifact
        update_result = runner.invoke(main, ['update', 'test-skill'])
        assert update_result.exit_code == 0

    @patch('skillmeat.core.artifact.ArtifactManager.check_updates')
    def test_status_multiple_artifacts(self, mock_check_updates, isolated_cli_runner, sample_skill_dir, sample_command_file):
        """Test status with multiple artifacts."""
        runner = isolated_cli_runner

        # Mock mixed update status
        mock_check_updates.return_value = {
            "updates_available": [
                {
                    "name": "test-skill",
                    "type": "skill",
                    "current_version": "1.0.0",
                    "latest_version": "2.0.0",
                }
            ],
            "up_to_date": [
                {
                    "name": "test-command",
                    "type": "command",
                }
            ],
        }

        runner.invoke(main, ['init'])
        runner.invoke(main, ['add', 'skill', str(sample_skill_dir), '--dangerously-skip-permissions'])
        runner.invoke(main, ['add', 'command', str(sample_command_file), '--dangerously-skip-permissions'])

        result = runner.invoke(main, ['status'])

        assert result.exit_code == 0
        assert "Updates available" in result.output
        assert "Up to date" in result.output
        assert "test-skill" in result.output
        assert "test-command" in result.output
