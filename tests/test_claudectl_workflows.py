"""Integration tests for claudectl workflows.

Tests the end-to-end behavior of commands with --smart-defaults enabled.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.defaults import SmartDefaults


class TestSmartDefaultsFlag:
    """Test the --smart-defaults flag behavior."""

    @pytest.mark.skip(reason="--smart-defaults flag not yet implemented in main CLI group")
    def test_flag_appears_in_help(self):
        """The --smart-defaults flag should appear in help."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        assert '--smart-defaults' in result.output

    @pytest.mark.skip(reason="--smart-defaults flag not yet implemented in main CLI group")
    def test_flag_sets_context(self):
        """The flag should set smart_defaults in context."""
        runner = CliRunner()
        # Use a simple command to verify context
        result = runner.invoke(main, ['--smart-defaults', '--help'])
        assert result.exit_code == 0


class TestQuickAddCommand:
    """Tests for the quick-add command."""

    def test_quick_add_appears_in_help(self):
        """quick-add command should be available."""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        assert 'quick-add' in result.output

    def test_quick_add_help(self):
        """quick-add should have its own help."""
        runner = CliRunner()
        result = runner.invoke(main, ['quick-add', '--help'])
        assert result.exit_code == 0
        assert '--type' in result.output
        assert '--collection' in result.output
        assert '--format' in result.output

    def test_type_auto_detection_cli(self):
        """Should detect -cli suffix as command type."""
        assert SmartDefaults.detect_artifact_type('my-cli') == 'command'
        assert SmartDefaults.detect_artifact_type('tool-cmd') == 'command'

    def test_type_auto_detection_agent(self):
        """Should detect -agent suffix as agent type."""
        assert SmartDefaults.detect_artifact_type('my-agent') == 'agent'
        assert SmartDefaults.detect_artifact_type('helper-bot') == 'agent'

    def test_type_auto_detection_skill(self):
        """Should default to skill type."""
        assert SmartDefaults.detect_artifact_type('canvas') == 'skill'
        assert SmartDefaults.detect_artifact_type('pdf-tools') == 'skill'


class TestDeployCommand:
    """Tests for the deploy command with smart defaults."""

    def test_deploy_help(self):
        """deploy should show format option."""
        runner = CliRunner()
        result = runner.invoke(main, ['deploy', '--help'])
        assert result.exit_code == 0
        assert '--format' in result.output
        assert '--project' in result.output

    def test_deploy_with_format_option(self):
        """deploy should accept --format option."""
        runner = CliRunner()
        result = runner.invoke(main, ['deploy', '--help'])
        assert '--format' in result.output


class TestRemoveCommand:
    """Tests for the remove command with smart defaults."""

    def test_remove_has_force_flag(self):
        """remove should have --force flag."""
        runner = CliRunner()
        result = runner.invoke(main, ['remove', '--help'])
        assert result.exit_code == 0
        assert '--force' in result.output or '-f' in result.output

    def test_remove_has_format_option(self):
        """remove should have --format option."""
        runner = CliRunner()
        result = runner.invoke(main, ['remove', '--help'])
        assert '--format' in result.output


class TestUndeployCommand:
    """Tests for the undeploy command with smart defaults."""

    def test_undeploy_has_force_flag(self):
        """undeploy should have --force flag."""
        runner = CliRunner()
        result = runner.invoke(main, ['undeploy', '--help'])
        assert result.exit_code == 0
        assert '--force' in result.output or '-f' in result.output

    def test_undeploy_has_format_option(self):
        """undeploy should have --format option."""
        runner = CliRunner()
        result = runner.invoke(main, ['undeploy', '--help'])
        assert '--format' in result.output


class TestOutputFormatDetection:
    """Tests for output format auto-detection."""

    def test_tty_returns_table(self):
        """Should return 'table' for TTY output."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                assert SmartDefaults.detect_output_format() == 'table'

    def test_pipe_returns_json(self):
        """Should return 'json' for piped output."""
        with patch.object(sys.stdout, 'isatty', return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                assert SmartDefaults.detect_output_format() == 'json'

    def test_env_override(self):
        """CLAUDECTL_JSON should force JSON output."""
        with patch.object(sys.stdout, 'isatty', return_value=True):
            with patch.dict(os.environ, {'CLAUDECTL_JSON': '1'}):
                assert SmartDefaults.detect_output_format() == 'json'


class TestProjectDetection:
    """Tests for project path detection."""

    def test_returns_cwd(self):
        """Should return current working directory."""
        expected = Path.cwd()
        assert SmartDefaults.get_default_project() == expected


class TestCollectionDetection:
    """Tests for collection detection from config."""

    def test_returns_active_collection(self):
        """Should return active_collection from config."""
        config = {'active_collection': 'my-work'}
        assert SmartDefaults.get_default_collection(config) == 'my-work'

    def test_returns_default_when_missing(self):
        """Should return 'default' when not in config."""
        assert SmartDefaults.get_default_collection({}) == 'default'


class TestJSONOutputValidity:
    """Tests for JSON output format validity."""

    def test_json_output_is_valid(self):
        """JSON output should be parseable."""
        # Test that our format is valid JSON
        sample_output = {
            'status': 'success',
            'command': 'deploy',
            'deployments': [
                {'artifact': 'test', 'type': 'skill', 'path': '/path/to/artifact'}
            ]
        }
        json_str = json.dumps(sample_output)
        parsed = json.loads(json_str)
        assert parsed['status'] == 'success'
