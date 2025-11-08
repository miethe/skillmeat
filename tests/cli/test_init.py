"""Tests for 'skillmeat init' command."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from skillmeat.cli import main
from skillmeat.core.collection import CollectionManager


class TestInitCommand:
    """Test suite for the init command."""

    def test_init_default_collection(self, isolated_cli_runner):
        """Test creating default collection."""
        runner = isolated_cli_runner
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0
        assert "Collection 'default' initialized" in result.output
        assert "Location:" in result.output
        assert "Artifacts: 0" in result.output

    def test_init_custom_collection(self, isolated_cli_runner):
        """Test creating custom named collection."""
        runner = isolated_cli_runner
        result = runner.invoke(main, ["init", "--name", "work"])

        assert result.exit_code == 0
        assert "Collection 'work' initialized" in result.output
        assert "Location:" in result.output

    def test_init_short_flag(self, isolated_cli_runner):
        """Test creating collection with short -n flag."""
        runner = isolated_cli_runner
        result = runner.invoke(main, ["init", "-n", "personal"])

        assert result.exit_code == 0
        assert "Collection 'personal' initialized" in result.output

    def test_init_already_exists(self, isolated_cli_runner):
        """Test initializing collection that already exists."""
        runner = isolated_cli_runner

        # Create collection first time
        result1 = runner.invoke(main, ["init"])
        assert result1.exit_code == 0

        # Try to create again
        result2 = runner.invoke(main, ["init"])
        assert result2.exit_code == 0
        assert "already exists" in result2.output

    def test_init_multiple_collections(self, isolated_cli_runner):
        """Test creating multiple collections."""
        runner = isolated_cli_runner

        # Create first collection
        result1 = runner.invoke(main, ["init", "--name", "work"])
        assert result1.exit_code == 0
        assert "Collection 'work' initialized" in result1.output

        # Create second collection
        result2 = runner.invoke(main, ["init", "--name", "personal"])
        assert result2.exit_code == 0
        assert "Collection 'personal' initialized" in result2.output

    def test_init_creates_directory_structure(self, isolated_cli_runner, temp_home):
        """Test that init creates proper directory structure."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Check directory structure
        collection_dir = temp_home / ".skillmeat" / "collections" / "default"
        assert collection_dir.exists()
        assert (collection_dir / "collection.toml").exists()
        assert (collection_dir / "skills").exists()
        assert (collection_dir / "commands").exists()
        assert (collection_dir / "agents").exists()

    def test_init_creates_manifest(self, isolated_cli_runner, temp_home):
        """Test that init creates collection manifest."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["init", "--name", "test"])
        assert result.exit_code == 0

        manifest_file = (
            temp_home / ".skillmeat" / "collections" / "test" / "collection.toml"
        )
        assert manifest_file.exists()

        # Verify manifest content
        content = manifest_file.read_text()
        assert "[collection]" in content
        assert 'name = "test"' in content

    def test_init_sets_active_collection(self, isolated_cli_runner, temp_home):
        """Test that first init sets active collection."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Check config file for active collection
        config_file = temp_home / ".skillmeat" / "config.toml"
        if config_file.exists():
            content = config_file.read_text()
            # Active collection should be set
            assert "default" in content or "active-collection" in content
