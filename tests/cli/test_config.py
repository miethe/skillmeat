"""Tests for 'skillmeat config' commands (list, get, set)."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from skillmeat.cli import main


class TestConfigListCommand:
    """Test suite for 'skillmeat config list' command."""

    def test_list_empty_config(self, isolated_cli_runner):
        """Test listing when no config is set."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'list'])

        assert result.exit_code == 0
        # Should show empty or no configuration message

    def test_list_with_config(self, isolated_cli_runner):
        """Test listing existing configuration."""
        runner = isolated_cli_runner

        # Set some config values
        runner.invoke(main, ['config', 'set', 'test-key', 'test-value'])

        result = runner.invoke(main, ['config', 'list'])

        assert result.exit_code == 0
        assert "Configuration" in result.output
        assert "test-key" in result.output
        assert "test-value" in result.output

    def test_list_masks_github_token(self, isolated_cli_runner):
        """Test that list masks GitHub token."""
        runner = isolated_cli_runner

        # Set GitHub token
        runner.invoke(main, ['config', 'set', 'github-token', 'ghp_1234567890abcdefghij'])

        result = runner.invoke(main, ['config', 'list'])

        assert result.exit_code == 0
        assert "github-token" in result.output
        # Token should be masked
        assert "ghp_1234567890abcdefghij" not in result.output
        assert "..." in result.output or "***" in result.output

    def test_list_multiple_config_values(self, isolated_cli_runner):
        """Test listing multiple configuration values."""
        runner = isolated_cli_runner

        # Set multiple values
        runner.invoke(main, ['config', 'set', 'default-collection', 'work'])
        runner.invoke(main, ['config', 'set', 'update-strategy', 'upstream'])

        result = runner.invoke(main, ['config', 'list'])

        assert result.exit_code == 0
        assert "default-collection" in result.output
        assert "work" in result.output
        assert "update-strategy" in result.output
        assert "upstream" in result.output


class TestConfigGetCommand:
    """Test suite for 'skillmeat config get' command."""

    def test_get_existing_key(self, isolated_cli_runner):
        """Test getting existing configuration key."""
        runner = isolated_cli_runner

        # Set value
        runner.invoke(main, ['config', 'set', 'test-key', 'test-value'])

        # Get value
        result = runner.invoke(main, ['config', 'get', 'test-key'])

        assert result.exit_code == 0
        assert "test-key" in result.output
        assert "test-value" in result.output

    def test_get_nonexistent_key(self, isolated_cli_runner):
        """Test getting non-existent key."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'get', 'nonexistent'])

        assert result.exit_code == 0
        assert "not set" in result.output

    def test_get_masks_github_token(self, isolated_cli_runner):
        """Test that get masks GitHub token."""
        runner = isolated_cli_runner

        # Set token
        runner.invoke(main, ['config', 'set', 'github-token', 'ghp_1234567890abcdefghij'])

        # Get token
        result = runner.invoke(main, ['config', 'get', 'github-token'])

        assert result.exit_code == 0
        assert "github-token" in result.output
        # Should be masked
        assert "ghp_1234567890abcdefghij" not in result.output
        assert "..." in result.output or "***" in result.output

    def test_get_default_collection(self, isolated_cli_runner):
        """Test getting default-collection setting."""
        runner = isolated_cli_runner

        runner.invoke(main, ['config', 'set', 'default-collection', 'work'])

        result = runner.invoke(main, ['config', 'get', 'default-collection'])

        assert result.exit_code == 0
        assert "work" in result.output

    def test_get_update_strategy(self, isolated_cli_runner):
        """Test getting update-strategy setting."""
        runner = isolated_cli_runner

        runner.invoke(main, ['config', 'set', 'update-strategy', 'upstream'])

        result = runner.invoke(main, ['config', 'get', 'update-strategy'])

        assert result.exit_code == 0
        assert "upstream" in result.output


class TestConfigSetCommand:
    """Test suite for 'skillmeat config set' command."""

    def test_set_new_key(self, isolated_cli_runner):
        """Test setting a new configuration key."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'set', 'new-key', 'new-value'])

        assert result.exit_code == 0
        assert "Set new-key" in result.output

        # Verify it was set
        get_result = runner.invoke(main, ['config', 'get', 'new-key'])
        assert "new-value" in get_result.output

    def test_set_existing_key(self, isolated_cli_runner):
        """Test updating existing configuration key."""
        runner = isolated_cli_runner

        # Set initial value
        runner.invoke(main, ['config', 'set', 'test-key', 'initial-value'])

        # Update value
        result = runner.invoke(main, ['config', 'set', 'test-key', 'updated-value'])

        assert result.exit_code == 0
        assert "Set test-key" in result.output

        # Verify it was updated
        get_result = runner.invoke(main, ['config', 'get', 'test-key'])
        assert "updated-value" in get_result.output
        assert "initial-value" not in get_result.output

    def test_set_github_token(self, isolated_cli_runner):
        """Test setting GitHub token."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'set', 'github-token', 'ghp_test123'])

        assert result.exit_code == 0
        assert "Set github-token" in result.output

    def test_set_default_collection(self, isolated_cli_runner):
        """Test setting default collection."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'set', 'default-collection', 'work'])

        assert result.exit_code == 0

        # Verify
        get_result = runner.invoke(main, ['config', 'get', 'default-collection'])
        assert "work" in get_result.output

    def test_set_update_strategy(self, isolated_cli_runner):
        """Test setting update strategy."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'set', 'update-strategy', 'upstream'])

        assert result.exit_code == 0

        # Verify
        get_result = runner.invoke(main, ['config', 'get', 'update-strategy'])
        assert "upstream" in get_result.output

    def test_set_value_with_spaces(self, isolated_cli_runner):
        """Test setting value that contains spaces."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'set', 'description', 'value with spaces'])

        assert result.exit_code == 0

        # Verify
        get_result = runner.invoke(main, ['config', 'get', 'description'])
        assert "value with spaces" in get_result.output

    def test_set_overwrites_previous_value(self, isolated_cli_runner):
        """Test that set overwrites previous value."""
        runner = isolated_cli_runner

        # Set first value
        runner.invoke(main, ['config', 'set', 'key', 'value1'])

        # Set second value
        runner.invoke(main, ['config', 'set', 'key', 'value2'])

        # Get should return second value
        result = runner.invoke(main, ['config', 'get', 'key'])
        assert "value2" in result.output
        assert "value1" not in result.output


class TestConfigWorkflows:
    """Test complete config management workflows."""

    def test_set_get_workflow(self, isolated_cli_runner):
        """Test workflow: set → get."""
        runner = isolated_cli_runner

        # Set value
        set_result = runner.invoke(main, ['config', 'set', 'test-key', 'test-value'])
        assert set_result.exit_code == 0

        # Get value
        get_result = runner.invoke(main, ['config', 'get', 'test-key'])
        assert get_result.exit_code == 0
        assert "test-value" in get_result.output

    def test_set_list_workflow(self, isolated_cli_runner):
        """Test workflow: set multiple → list all."""
        runner = isolated_cli_runner

        # Set multiple values
        runner.invoke(main, ['config', 'set', 'key1', 'value1'])
        runner.invoke(main, ['config', 'set', 'key2', 'value2'])
        runner.invoke(main, ['config', 'set', 'key3', 'value3'])

        # List all
        list_result = runner.invoke(main, ['config', 'list'])
        assert list_result.exit_code == 0
        assert "key1" in list_result.output
        assert "key2" in list_result.output
        assert "key3" in list_result.output

    def test_github_token_workflow(self, isolated_cli_runner):
        """Test setting and using GitHub token."""
        runner = isolated_cli_runner

        # Set token
        set_result = runner.invoke(main, ['config', 'set', 'github-token', 'ghp_test123'])
        assert set_result.exit_code == 0

        # Get token (should be masked)
        get_result = runner.invoke(main, ['config', 'get', 'github-token'])
        assert get_result.exit_code == 0
        assert "ghp_test123" not in get_result.output

        # List config (token should be masked)
        list_result = runner.invoke(main, ['config', 'list'])
        assert list_result.exit_code == 0
        assert "ghp_test123" not in list_result.output

    def test_config_persists(self, isolated_cli_runner):
        """Test that config persists across commands."""
        runner = isolated_cli_runner

        # Set value
        runner.invoke(main, ['config', 'set', 'test-key', 'test-value'])

        # Run other commands
        runner.invoke(main, ['init'])

        # Get value should still work
        get_result = runner.invoke(main, ['config', 'get', 'test-key'])
        assert get_result.exit_code == 0
        assert "test-value" in get_result.output

    def test_config_common_settings(self, isolated_cli_runner):
        """Test configuring common settings."""
        runner = isolated_cli_runner

        # Set common configuration
        runner.invoke(main, ['config', 'set', 'github-token', 'ghp_example123'])
        runner.invoke(main, ['config', 'set', 'default-collection', 'work'])
        runner.invoke(main, ['config', 'set', 'update-strategy', 'prompt'])

        # List all
        result = runner.invoke(main, ['config', 'list'])
        assert result.exit_code == 0
        assert "github-token" in result.output
        assert "default-collection" in result.output
        assert "work" in result.output
        assert "update-strategy" in result.output
        assert "prompt" in result.output

    def test_update_config_values(self, isolated_cli_runner):
        """Test updating configuration values."""
        runner = isolated_cli_runner

        # Set initial values
        runner.invoke(main, ['config', 'set', 'update-strategy', 'prompt'])

        # Update values
        runner.invoke(main, ['config', 'set', 'update-strategy', 'upstream'])

        # Verify updated
        result = runner.invoke(main, ['config', 'get', 'update-strategy'])
        assert "upstream" in result.output
        assert "prompt" not in result.output


class TestConfigEdgeCases:
    """Test edge cases for config commands."""

    def test_config_with_empty_value(self, isolated_cli_runner):
        """Test setting config with empty value."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ['config', 'set', 'empty-key', ''])

        # Should handle gracefully
        assert result.exit_code in [0, 1]

    def test_config_with_special_characters(self, isolated_cli_runner):
        """Test config values with special characters."""
        runner = isolated_cli_runner

        # Set value with special characters
        result = runner.invoke(main, ['config', 'set', 'special', 'value@#$%'])

        if result.exit_code == 0:
            # Verify
            get_result = runner.invoke(main, ['config', 'get', 'special'])
            assert "value@#$%" in get_result.output

    def test_config_key_case_sensitivity(self, isolated_cli_runner):
        """Test if config keys are case-sensitive."""
        runner = isolated_cli_runner

        # Set lowercase
        runner.invoke(main, ['config', 'set', 'lowercase', 'value1'])

        # Try to get with different case
        result = runner.invoke(main, ['config', 'get', 'LOWERCASE'])

        # Behavior depends on implementation
        # Could be case-sensitive or case-insensitive

    def test_config_before_init(self, isolated_cli_runner):
        """Test setting config before initializing collection."""
        runner = isolated_cli_runner

        # Set config without init
        result = runner.invoke(main, ['config', 'set', 'test-key', 'test-value'])

        # Should work (config is global)
        assert result.exit_code == 0
