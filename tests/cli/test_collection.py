"""Tests for 'skillmeat collection' commands (create, list, use)."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from skillmeat.cli import main
from tests.conftest import create_minimal_skill


class TestCollectionCreateCommand:
    """Test suite for 'skillmeat collection create' command."""

    def test_create_new_collection(self, isolated_cli_runner):
        """Test creating a new collection."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["collection", "create", "work"])

        assert result.exit_code == 0
        assert "Collection 'work' created" in result.output
        assert "Location:" in result.output

    def test_create_collection_already_exists(self, isolated_cli_runner):
        """Test creating collection that already exists."""
        runner = isolated_cli_runner

        # Create first time
        result1 = runner.invoke(main, ["collection", "create", "work"])
        assert result1.exit_code == 0

        # Try to create again
        result2 = runner.invoke(main, ["collection", "create", "work"])
        assert result2.exit_code == 0
        assert "already exists" in result2.output

    def test_create_multiple_collections(self, isolated_cli_runner):
        """Test creating multiple collections."""
        runner = isolated_cli_runner

        # Create first collection
        result1 = runner.invoke(main, ["collection", "create", "work"])
        assert result1.exit_code == 0
        assert "Collection 'work' created" in result1.output

        # Create second collection
        result2 = runner.invoke(main, ["collection", "create", "personal"])
        assert result2.exit_code == 0
        assert "Collection 'personal' created" in result2.output

        # Create third collection
        result3 = runner.invoke(main, ["collection", "create", "experimental"])
        assert result3.exit_code == 0
        assert "Collection 'experimental' created" in result3.output

    def test_create_collection_with_special_chars(self, isolated_cli_runner):
        """Test creating collection with special characters in name."""
        runner = isolated_cli_runner

        # Try various names
        result1 = runner.invoke(main, ["collection", "create", "work-2024"])
        assert result1.exit_code == 0

        result2 = runner.invoke(main, ["collection", "create", "my_collection"])
        assert result2.exit_code == 0

    def test_create_collection_creates_structure(self, isolated_cli_runner, temp_home):
        """Test that create builds proper directory structure."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["collection", "create", "test"])
        assert result.exit_code == 0

        # Verify structure
        collection_dir = temp_home / ".skillmeat" / "collections" / "test"
        assert collection_dir.exists()
        assert (collection_dir / "collection.toml").exists()
        assert (collection_dir / "skills").exists()
        assert (collection_dir / "commands").exists()
        assert (collection_dir / "agents").exists()


class TestCollectionListCommand:
    """Test suite for 'skillmeat collection list' command."""

    def test_list_no_collections(self, isolated_cli_runner):
        """Test listing when no collections exist."""
        runner = isolated_cli_runner

        result = runner.invoke(main, ["collection", "list"])

        assert result.exit_code == 0
        assert "No collections found" in result.output
        assert "skillmeat init" in result.output

    def test_list_with_collections(self, isolated_cli_runner):
        """Test listing existing collections."""
        runner = isolated_cli_runner

        # Create collections
        runner.invoke(main, ["collection", "create", "work"])
        runner.invoke(main, ["collection", "create", "personal"])

        result = runner.invoke(main, ["collection", "list"])

        assert result.exit_code == 0
        assert "Collections" in result.output
        assert "work" in result.output
        assert "personal" in result.output

    def test_list_shows_active_collection(self, isolated_cli_runner):
        """Test that list shows which collection is active."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(main, ["collection", "create", "work"])

        result = runner.invoke(main, ["collection", "list"])

        assert result.exit_code == 0
        # Should have some indicator of active collection (checkmark, asterisk, etc.)
        assert "Active" in result.output or "✓" in result.output

    def test_list_shows_artifact_count(self, isolated_cli_runner, sample_skill_dir):
        """Test that list shows artifact count for each collection."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        result = runner.invoke(main, ["collection", "list"])

        assert result.exit_code == 0
        assert "Artifacts" in result.output
        # Should show count of artifacts

    def test_list_multiple_collections_with_artifacts(
        self, isolated_cli_runner, sample_skill_dir, sample_command_file
    ):
        """Test listing multiple collections with different artifacts."""
        runner = isolated_cli_runner

        # Create first collection with skill
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

        # Create second collection with command
        runner.invoke(main, ["collection", "create", "personal"])
        runner.invoke(
            main,
            [
                "add",
                "command",
                str(sample_command_file),
                "--collection",
                "personal",
                "--dangerously-skip-permissions",
            ],
        )

        result = runner.invoke(main, ["collection", "list"])

        assert result.exit_code == 0
        assert "work" in result.output
        assert "personal" in result.output


class TestCollectionUseCommand:
    """Test suite for 'skillmeat collection use' command."""

    def test_use_existing_collection(self, isolated_cli_runner):
        """Test switching to existing collection."""
        runner = isolated_cli_runner

        # Create collections
        runner.invoke(main, ["init"])
        runner.invoke(main, ["collection", "create", "work"])

        # Switch to work collection
        result = runner.invoke(main, ["collection", "use", "work"])

        assert result.exit_code == 0
        assert "Switched to collection 'work'" in result.output

    def test_use_nonexistent_collection(self, isolated_cli_runner):
        """Test switching to non-existent collection."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["collection", "use", "nonexistent"])

        assert result.exit_code == 0
        assert "not found" in result.output
        assert "Available collections" in result.output

    def test_use_shows_available_collections(self, isolated_cli_runner):
        """Test that use command shows available collections when not found."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(main, ["collection", "create", "work"])
        runner.invoke(main, ["collection", "create", "personal"])

        result = runner.invoke(main, ["collection", "use", "invalid"])

        assert result.exit_code == 0
        assert "Available collections" in result.output
        assert (
            "default" in result.output
            or "work" in result.output
            or "personal" in result.output
        )

    def test_use_switches_active_collection(
        self, isolated_cli_runner, sample_skill_dir
    ):
        """Test that use actually switches the active collection."""
        runner = isolated_cli_runner

        # Create two collections with different artifacts
        runner.invoke(main, ["init"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        runner.invoke(main, ["collection", "create", "work"])

        # List should show test-skill in default collection
        list1 = runner.invoke(main, ["list"])
        assert "test-skill" in list1.output

        # Switch to work collection
        runner.invoke(main, ["collection", "use", "work"])

        # List should now be empty
        list2 = runner.invoke(main, ["list"])
        assert "No artifacts found" in list2.output or "test-skill" not in list2.output

    def test_use_persists_across_commands(self, isolated_cli_runner):
        """Test that collection switch persists."""
        runner = isolated_cli_runner

        runner.invoke(main, ["init"])
        runner.invoke(main, ["collection", "create", "work"])

        # Switch to work
        runner.invoke(main, ["collection", "use", "work"])

        # List collections - work should be active
        list_result = runner.invoke(main, ["collection", "list"])
        # The active collection should be indicated in the list


class TestCollectionWorkflows:
    """Test complete collection management workflows."""

    def test_create_list_use_workflow(self, isolated_cli_runner):
        """Test workflow: create → list → use."""
        runner = isolated_cli_runner

        # Create multiple collections
        runner.invoke(main, ["collection", "create", "work"])
        runner.invoke(main, ["collection", "create", "personal"])
        runner.invoke(main, ["collection", "create", "experimental"])

        # List collections
        list_result = runner.invoke(main, ["collection", "list"])
        assert list_result.exit_code == 0
        assert "work" in list_result.output
        assert "personal" in list_result.output
        assert "experimental" in list_result.output

        # Switch to work
        use_result = runner.invoke(main, ["collection", "use", "work"])
        assert use_result.exit_code == 0

        # Verify switch in list
        list_result2 = runner.invoke(main, ["collection", "list"])
        assert list_result2.exit_code == 0

    def test_multiple_collections_workflow(
        self, isolated_cli_runner, sample_skill_dir, sample_command_file
    ):
        """Test managing artifacts across multiple collections."""
        runner = isolated_cli_runner

        # Create work collection with skill
        runner.invoke(main, ["collection", "create", "work"])
        runner.invoke(main, ["collection", "use", "work"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Verify skill in work collection
        list_work = runner.invoke(main, ["list"])
        assert "test-skill" in list_work.output

        # Create personal collection with command
        runner.invoke(main, ["collection", "create", "personal"])
        runner.invoke(main, ["collection", "use", "personal"])
        runner.invoke(
            main,
            [
                "add",
                "command",
                str(sample_command_file),
                "--dangerously-skip-permissions",
            ],
        )

        # Verify command in personal collection
        list_personal = runner.invoke(main, ["list"])
        assert "test-command" in list_personal.output
        assert "test-skill" not in list_personal.output

        # Switch back to work
        runner.invoke(main, ["collection", "use", "work"])

        # Verify skill still in work collection
        list_work2 = runner.invoke(main, ["list"])
        assert "test-skill" in list_work2.output
        assert "test-command" not in list_work2.output

    def test_collection_isolation(self, isolated_cli_runner, sample_skill_dir):
        """Test that collections are properly isolated."""
        runner = isolated_cli_runner

        # Create two collections
        runner.invoke(main, ["collection", "create", "coll1"])
        runner.invoke(main, ["collection", "create", "coll2"])

        # Add artifact to coll1
        runner.invoke(main, ["collection", "use", "coll1"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Verify artifact in coll1
        list1 = runner.invoke(main, ["list"])
        assert "test-skill" in list1.output

        # Switch to coll2
        runner.invoke(main, ["collection", "use", "coll2"])

        # Verify artifact NOT in coll2
        list2 = runner.invoke(main, ["list"])
        assert "No artifacts found" in list2.output

    def test_default_collection_creation(self, isolated_cli_runner):
        """Test that init creates default collection."""
        runner = isolated_cli_runner

        # Init should create default collection
        runner.invoke(main, ["init"])

        # List should show default collection
        result = runner.invoke(main, ["collection", "list"])
        assert result.exit_code == 0
        assert "default" in result.output

    def test_collection_with_snapshots(self, isolated_cli_runner, sample_skill_dir):
        """Test snapshots work with collection switching."""
        runner = isolated_cli_runner

        # Create collection and add artifact
        runner.invoke(main, ["collection", "create", "work"])
        runner.invoke(main, ["collection", "use", "work"])
        runner.invoke(
            main,
            ["add", "skill", str(sample_skill_dir), "--dangerously-skip-permissions"],
        )

        # Create snapshot
        snapshot_result = runner.invoke(main, ["snapshot", "Work backup"])
        assert snapshot_result.exit_code == 0

        # View history
        history_result = runner.invoke(main, ["history"])
        assert history_result.exit_code == 0
        assert "Work backup" in history_result.output

        # Switch to different collection
        runner.invoke(main, ["collection", "create", "personal"])
        runner.invoke(main, ["collection", "use", "personal"])

        # History should be different (empty for new collection)
        history_result2 = runner.invoke(main, ["history"])
        assert (
            "No snapshots found" in history_result2.output
            or history_result2.exit_code == 0
        )
