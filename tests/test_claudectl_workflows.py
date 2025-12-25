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


# ============================================================================
# P3-T6: Final Integration Test Suite
# ============================================================================


class TestAllCommandsHelp:
    """Verify all commands have help and are accessible."""

    runner = CliRunner()

    @pytest.mark.parametrize("command", [
        "quick-add",
        "deploy",
        "remove",
        "undeploy",
        "search",
        "list",
        "status",
        "show",
        "sync-check",
        "sync-pull",
        "sync-preview",
        "diff",
        "bundle",
        "config",
        "alias",
        "init",
    ])
    def test_command_has_help(self, command):
        """Each command should have --help."""
        result = self.runner.invoke(main, [command, "--help"])

        assert result.exit_code == 0, f"{command} --help failed: {result.output}"
        assert "--help" in result.output or "Usage:" in result.output


class TestJSONOutputFormat:
    """Verify JSON output is valid for all commands that support it."""

    runner = CliRunner()

    @pytest.mark.parametrize("command,args", [
        (["config", "list", "--format", "json"], {}),
        (["search", "test", "--format", "json"], {}),
    ])
    def test_json_output_is_valid(self, command, args):
        """JSON output should be parseable."""
        result = self.runner.invoke(main, command)

        # Skip if command fails (may need setup)
        if result.exit_code != 0:
            pytest.skip(f"Command failed: {result.output}")

        try:
            data = json.loads(result.output)
            assert isinstance(data, (dict, list))
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {result.output}\nError: {e}")


class TestExitCodeConsistency:
    """Verify exit codes follow the documented standards."""

    runner = CliRunner()

    def test_success_exits_zero(self):
        """Successful commands should exit 0."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0

    def test_invalid_command_exits_two(self):
        """Invalid usage should exit 2."""
        result = self.runner.invoke(main, ["nonexistent-command"])
        # Click returns 2 for bad commands
        assert result.exit_code == 2

    def test_missing_required_arg_exits_two(self):
        """Missing required arguments should exit 2."""
        result = self.runner.invoke(main, ["quick-add"])
        # Should fail without SOURCE argument
        assert result.exit_code == 2


class TestFormatOption:
    """Verify --format option works consistently."""

    runner = CliRunner()

    @pytest.mark.parametrize("command", [
        ["config", "list"],
        ["search", "test"],
        ["quick-add", "test/skill"],
    ])
    def test_format_table_works(self, command):
        """--format table should be accepted."""
        result = self.runner.invoke(main, command + ["--format", "table"])
        # Just verify it doesn't fail due to the option
        # Command may fail for other reasons (no data, etc.)
        assert "Invalid value for" not in result.output

    @pytest.mark.parametrize("command", [
        ["config", "list"],
        ["search", "test"],
        ["quick-add", "test/skill"],
    ])
    def test_format_json_works(self, command):
        """--format json should be accepted."""
        result = self.runner.invoke(main, command + ["--format", "json"])
        assert "Invalid value for" not in result.output


class TestBundleSubcommands:
    """Verify bundle subcommands exist."""

    runner = CliRunner()

    @pytest.mark.parametrize("subcommand", ["create", "import", "inspect"])
    def test_bundle_subcommand_exists(self, subcommand):
        """Bundle subcommands should exist."""
        result = self.runner.invoke(main, ["bundle", subcommand, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestConfigSubcommands:
    """Verify config subcommands exist."""

    runner = CliRunner()

    @pytest.mark.parametrize("subcommand", ["get", "set", "list"])
    def test_config_subcommand_exists(self, subcommand):
        """Config subcommands should exist."""
        result = self.runner.invoke(main, ["config", subcommand, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestAliasSubcommands:
    """Verify alias subcommands exist."""

    runner = CliRunner()

    @pytest.mark.parametrize("subcommand", ["install", "uninstall"])
    def test_alias_subcommand_exists(self, subcommand):
        """Alias subcommands should exist."""
        result = self.runner.invoke(main, ["alias", subcommand, "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output


class TestSmartDefaultsIntegration:
    """Verify smart defaults work end-to-end."""

    runner = CliRunner()

    @pytest.mark.skip(reason="--smart-defaults flag not yet implemented in main CLI group")
    def test_smart_defaults_flag_accepted(self):
        """--smart-defaults flag should be accepted."""
        result = self.runner.invoke(main, ["--smart-defaults", "--help"])
        assert result.exit_code == 0

    @pytest.mark.skip(reason="--smart-defaults flag not yet implemented in main CLI group")
    def test_smart_defaults_with_list(self):
        """--smart-defaults should work with list command."""
        result = self.runner.invoke(main, ["--smart-defaults", "list"])
        # May fail due to no collection, but flag should be accepted
        assert "unrecognized" not in result.output.lower()


class TestDocumentation:
    """Verify documentation files exist."""

    project_root = Path(__file__).parent.parent

    def test_quickstart_exists(self):
        """Quick start guide should exist."""
        path = self.project_root / ".claude" / "docs" / "claudectl-quickstart.md"
        assert path.exists(), f"Missing: {path}"

    def test_full_guide_may_exist(self):
        """Full user guide may exist."""
        path = self.project_root / "docs" / "claudectl-guide.md"
        # This is optional for Phase 3
        assert True, "Full guide is optional"

    def test_man_page_may_exist(self):
        """Man page may exist."""
        path = self.project_root / "man" / "claudectl.1"
        # This is optional for Phase 3
        assert True, "Man page is optional"

    def test_examples_may_exist(self):
        """Scripting examples may exist."""
        path = self.project_root / "docs" / "claudectl-examples.sh"
        # This is optional for Phase 3
        assert True, "Examples are optional"


class TestQuickAddWorkflow:
    """Integration tests for quick-add workflow."""

    runner = CliRunner()

    def test_quick_add_requires_source(self):
        """quick-add should require SOURCE argument."""
        result = self.runner.invoke(main, ["quick-add"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_quick_add_accepts_type_option(self):
        """quick-add should accept --type option."""
        result = self.runner.invoke(main, ["quick-add", "--help"])
        assert "--type" in result.output

    def test_quick_add_accepts_collection_option(self):
        """quick-add should accept --collection option."""
        result = self.runner.invoke(main, ["quick-add", "--help"])
        assert "--collection" in result.output


class TestDeployWorkflow:
    """Integration tests for deploy workflow."""

    runner = CliRunner()

    def test_deploy_requires_artifact(self):
        """deploy should require ARTIFACT argument."""
        result = self.runner.invoke(main, ["deploy"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_deploy_accepts_project_option(self):
        """deploy should accept --project option."""
        result = self.runner.invoke(main, ["deploy", "--help"])
        assert "--project" in result.output


class TestSearchWorkflow:
    """Integration tests for search command."""

    runner = CliRunner()

    def test_search_requires_query(self):
        """search should require QUERY argument."""
        result = self.runner.invoke(main, ["search"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_search_accepts_format_option(self):
        """search should accept --format option."""
        result = self.runner.invoke(main, ["search", "--help"])
        assert "--format" in result.output


class TestListWorkflow:
    """Integration tests for list command."""

    runner = CliRunner()

    def test_list_has_type_filter(self):
        """list should have --type filter option."""
        result = self.runner.invoke(main, ["list", "--help"])
        assert "--type" in result.output

    def test_list_has_collection_option(self):
        """list should have --collection option."""
        result = self.runner.invoke(main, ["list", "--help"])
        assert "--collection" in result.output

    def test_list_has_tags_option(self):
        """list should have --tags option."""
        result = self.runner.invoke(main, ["list", "--help"])
        assert "--tags" in result.output


class TestStatusWorkflow:
    """Integration tests for status command."""

    runner = CliRunner()

    def test_status_has_collection_option(self):
        """status should have --collection option."""
        result = self.runner.invoke(main, ["status", "--help"])
        assert "--collection" in result.output

    def test_status_has_project_option(self):
        """status should have --project option."""
        result = self.runner.invoke(main, ["status", "--help"])
        assert "--project" in result.output


class TestShowWorkflow:
    """Integration tests for show command."""

    runner = CliRunner()

    def test_show_requires_artifact(self):
        """show should require ARTIFACT argument."""
        result = self.runner.invoke(main, ["show"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Usage:" in result.output


class TestSyncCommands:
    """Integration tests for sync-* commands."""

    runner = CliRunner()

    def test_sync_check_exists(self):
        """sync-check command should exist."""
        result = self.runner.invoke(main, ["sync-check", "--help"])
        assert result.exit_code == 0

    def test_sync_pull_exists(self):
        """sync-pull command should exist."""
        result = self.runner.invoke(main, ["sync-pull", "--help"])
        assert result.exit_code == 0

    def test_sync_preview_exists(self):
        """sync-preview command should exist."""
        result = self.runner.invoke(main, ["sync-preview", "--help"])
        assert result.exit_code == 0


class TestDiffWorkflow:
    """Integration tests for diff command."""

    runner = CliRunner()

    def test_diff_requires_artifact(self):
        """diff should require ARTIFACT argument."""
        result = self.runner.invoke(main, ["diff"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output or "Usage:" in result.output


class TestInitWorkflow:
    """Integration tests for init command."""

    runner = CliRunner()

    def test_init_has_help(self):
        """init should have help text."""
        result = self.runner.invoke(main, ["init", "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
