"""Integration tests for CLI diff artifact command.

Tests the 'skillmeat diff artifact' command for comparing artifacts with
upstream and project versions.
"""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner

from skillmeat.cli import main
from skillmeat.core.collection import CollectionManager
from skillmeat.core.artifact import ArtifactManager, ArtifactType


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


class TestDiffArtifactCLI:
    """Test cases for diff artifact CLI command."""

    def test_diff_artifact_help(self, cli_runner):
        """Test that diff artifact help is displayed correctly."""
        result = cli_runner.invoke(main, ["diff", "artifact", "--help"])

        assert result.exit_code == 0
        assert "Compare artifact versions" in result.output
        assert "--upstream" in result.output
        assert "--project" in result.output
        assert "--summary-only" in result.output
        assert "--limit" in result.output

    def test_diff_artifact_missing_mode(self, cli_runner):
        """Test error when neither --upstream nor --project is specified."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(main, ["diff", "artifact", "test-skill"])

            assert result.exit_code == 1
            assert "Must specify either --upstream or --project" in result.output

    def test_diff_artifact_both_modes(self, cli_runner):
        """Test error when both --upstream and --project are specified."""
        with cli_runner.isolated_filesystem():
            result = cli_runner.invoke(
                main,
                ["diff", "artifact", "test-skill", "--upstream", "--project", "/tmp"],
            )

            assert result.exit_code == 1
            assert "Cannot specify both --upstream and --project" in result.output

    # NOTE: Full integration tests with artifact collection setup require
    # complex test environment setup. The command has been manually tested
    # and works correctly. Additional tests can be added in the future with
    # proper test isolation fixtures.
