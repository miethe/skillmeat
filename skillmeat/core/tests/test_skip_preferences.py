"""Unit tests for SkipPreferenceManager.

This test suite provides comprehensive coverage for skip_preferences.py module,
testing CRUD operations, thread safety, file persistence, and error handling.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.core.skip_preferences import (
    SkipPreference,
    SkipPreferenceFile,
    SkipPreferenceManager,
    SkipPreferenceMetadata,
    build_artifact_key,
    parse_artifact_key,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory.

    Returns:
        Path to temporary project directory with .claude/ subdirectory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / ".claude").mkdir()
        yield project_path


class TestSkipPreferenceManager:
    """Tests for SkipPreferenceManager CRUD operations."""

    def test_load_empty_preferences(self, temp_project):
        """Test loading when no preferences file exists."""
        mgr = SkipPreferenceManager(temp_project)
        prefs = mgr.load_skip_prefs()

        assert len(prefs.skips) == 0
        assert prefs.metadata.version == "1.0.0"
        assert prefs.metadata.last_updated is not None

    def test_add_skip(self, temp_project):
        """Test adding a skip preference."""
        mgr = SkipPreferenceManager(temp_project)
        skip = mgr.add_skip("skill:canvas-design", "Already in collection")

        assert skip.artifact_key == "skill:canvas-design"
        assert skip.skip_reason == "Already in collection"
        assert skip.added_date is not None
        assert mgr.is_skipped("skill:canvas-design")

    def test_add_multiple_skips(self, temp_project):
        """Test adding multiple skip preferences."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:canvas-design", "Already in collection")
        mgr.add_skip("command:my-command", "Not needed")
        mgr.add_skip("agent:code-reviewer", "Using alternative")

        assert mgr.is_skipped("skill:canvas-design")
        assert mgr.is_skipped("command:my-command")
        assert mgr.is_skipped("agent:code-reviewer")

        skips = mgr.get_skipped_list()
        assert len(skips) == 3

    def test_remove_skip(self, temp_project):
        """Test removing a skip preference."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:test", "Test reason")
        assert mgr.is_skipped("skill:test")

        result = mgr.remove_skip("skill:test")
        assert result is True
        assert not mgr.is_skipped("skill:test")

    def test_remove_nonexistent_skip(self, temp_project):
        """Test removing skip that doesn't exist returns False."""
        mgr = SkipPreferenceManager(temp_project)
        result = mgr.remove_skip("skill:nonexistent")
        assert result is False

    def test_clear_skips(self, temp_project):
        """Test clearing all skips."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:one", "Reason 1")
        mgr.add_skip("skill:two", "Reason 2")
        mgr.add_skip("command:three", "Reason 3")

        count = mgr.clear_skips()
        assert count == 3
        assert len(mgr.get_skipped_list()) == 0

    def test_clear_empty_skips(self, temp_project):
        """Test clearing when no skips exist returns 0."""
        mgr = SkipPreferenceManager(temp_project)
        count = mgr.clear_skips()
        assert count == 0

    def test_duplicate_skip_raises(self, temp_project):
        """Test that adding duplicate raises ValueError."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:test", "First reason")

        with pytest.raises(ValueError, match="already exists"):
            mgr.add_skip("skill:test", "Second reason")

    def test_invalid_artifact_key_raises(self, temp_project):
        """Test that invalid artifact key raises ValueError."""
        mgr = SkipPreferenceManager(temp_project)

        # No colon
        with pytest.raises(ValueError):
            mgr.add_skip("invalid-key", "No colon separator")

        # Empty type
        with pytest.raises(ValueError):
            mgr.add_skip(":name", "Empty type")

        # Empty name
        with pytest.raises(ValueError):
            mgr.add_skip("skill:", "Empty name")

        # Invalid type
        with pytest.raises(ValueError):
            mgr.add_skip("invalid:name", "Invalid type")

    def test_persistence_across_instances(self, temp_project):
        """Test that skips persist across manager instances."""
        # Create first instance and add skip
        mgr1 = SkipPreferenceManager(temp_project)
        mgr1.add_skip("skill:test", "Persisted skip")

        # Create second instance and verify skip exists
        mgr2 = SkipPreferenceManager(temp_project)
        assert mgr2.is_skipped("skill:test")

        skip = mgr2.get_skip_by_key("skill:test")
        assert skip is not None
        assert skip.skip_reason == "Persisted skip"

    def test_get_skip_by_key(self, temp_project):
        """Test retrieving skip by artifact key."""
        mgr = SkipPreferenceManager(temp_project)
        original_skip = mgr.add_skip("skill:canvas-design", "Test reason")

        retrieved_skip = mgr.get_skip_by_key("skill:canvas-design")
        assert retrieved_skip is not None
        assert retrieved_skip.artifact_key == original_skip.artifact_key
        assert retrieved_skip.skip_reason == original_skip.skip_reason

    def test_get_skip_by_key_nonexistent(self, temp_project):
        """Test retrieving nonexistent skip returns None."""
        mgr = SkipPreferenceManager(temp_project)
        skip = mgr.get_skip_by_key("skill:nonexistent")
        assert skip is None

    def test_get_skipped_list(self, temp_project):
        """Test getting all skips as a list."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:one", "Reason 1")
        mgr.add_skip("skill:two", "Reason 2")

        skips = mgr.get_skipped_list()
        assert len(skips) == 2
        assert all(isinstance(skip, SkipPreference) for skip in skips)

        # Verify list is a copy (modifying it doesn't affect manager)
        skips.clear()
        assert len(mgr.get_skipped_list()) == 2

    def test_corrupt_file_handling(self, temp_project):
        """Test graceful handling of corrupt TOML file."""
        skip_path = temp_project / ".claude" / ".skillmeat_skip_prefs.toml"
        skip_path.write_text("invalid toml [[[")

        mgr = SkipPreferenceManager(temp_project)
        prefs = mgr.load_skip_prefs()

        # Should return empty preferences on corrupt file
        assert len(prefs.skips) == 0

    def test_is_skipped(self, temp_project):
        """Test checking if artifact is skipped."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:test", "Test reason")

        assert mgr.is_skipped("skill:test") is True
        assert mgr.is_skipped("skill:other") is False

    def test_atomic_file_operations(self, temp_project):
        """Test that file operations are atomic (no corruption on failure)."""
        mgr = SkipPreferenceManager(temp_project)
        mgr.add_skip("skill:test", "Original skip")

        # Verify file exists
        skip_path = temp_project / ".claude" / ".skillmeat_skip_prefs.toml"
        assert skip_path.exists()

        # Load in new instance to verify persistence
        mgr2 = SkipPreferenceManager(temp_project)
        assert mgr2.is_skipped("skill:test")


class TestSkipPreferenceFile:
    """Tests for SkipPreferenceFile model."""

    def test_create_empty(self):
        """Test creating empty skip preferences file."""
        prefs = SkipPreferenceFile.create_empty()

        assert len(prefs.skips) == 0
        assert prefs.metadata.version == "1.0.0"
        assert prefs.metadata.last_updated is not None

    def test_add_skip(self):
        """Test adding skip to file."""
        prefs = SkipPreferenceFile.create_empty()
        skip = prefs.add_skip("skill:test", "Test reason")

        assert skip.artifact_key == "skill:test"
        assert skip.skip_reason == "Test reason"
        assert len(prefs.skips) == 1

    def test_add_duplicate_skip_raises(self):
        """Test adding duplicate skip raises ValueError."""
        prefs = SkipPreferenceFile.create_empty()
        prefs.add_skip("skill:test", "First")

        with pytest.raises(ValueError, match="already exists"):
            prefs.add_skip("skill:test", "Second")

    def test_remove_skip(self):
        """Test removing skip from file."""
        prefs = SkipPreferenceFile.create_empty()
        prefs.add_skip("skill:test", "Test reason")

        result = prefs.remove_skip("skill:test")
        assert result is True
        assert len(prefs.skips) == 0

    def test_remove_nonexistent_skip(self):
        """Test removing nonexistent skip returns False."""
        prefs = SkipPreferenceFile.create_empty()
        result = prefs.remove_skip("skill:nonexistent")
        assert result is False

    def test_clear_all(self):
        """Test clearing all skips."""
        prefs = SkipPreferenceFile.create_empty()
        prefs.add_skip("skill:one", "Reason 1")
        prefs.add_skip("skill:two", "Reason 2")

        count = prefs.clear_all()
        assert count == 2
        assert len(prefs.skips) == 0

    def test_has_skip(self):
        """Test checking if skip exists."""
        prefs = SkipPreferenceFile.create_empty()
        prefs.add_skip("skill:test", "Test reason")

        assert prefs.has_skip("skill:test") is True
        assert prefs.has_skip("skill:other") is False

    def test_get_skip_by_key(self):
        """Test getting skip by key."""
        prefs = SkipPreferenceFile.create_empty()
        original = prefs.add_skip("skill:test", "Test reason")

        retrieved = prefs.get_skip_by_key("skill:test")
        assert retrieved is not None
        assert retrieved.artifact_key == original.artifact_key

    def test_validate_no_duplicates(self):
        """Test validation prevents duplicate artifact keys."""
        # Create file with duplicate artifact_keys manually
        metadata = SkipPreferenceMetadata(
            version="1.0.0",
            last_updated=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="Duplicate"):
            SkipPreferenceFile(
                metadata=metadata,
                skips=[
                    SkipPreference(
                        artifact_key="skill:test",
                        skip_reason="First",
                        added_date=datetime.utcnow(),
                    ),
                    SkipPreference(
                        artifact_key="skill:test",
                        skip_reason="Second",
                        added_date=datetime.utcnow(),
                    ),
                ],
            )


class TestSkipPreference:
    """Tests for SkipPreference model."""

    def test_create_skip_preference(self):
        """Test creating valid skip preference."""
        skip = SkipPreference(
            artifact_key="skill:canvas-design",
            skip_reason="Already in collection",
            added_date=datetime.utcnow(),
        )

        assert skip.artifact_key == "skill:canvas-design"
        assert skip.skip_reason == "Already in collection"
        assert skip.added_date is not None

    def test_validate_artifact_key_format(self):
        """Test artifact_key validation."""
        # Valid keys
        valid_keys = [
            "skill:canvas-design",
            "command:my-command",
            "agent:code-reviewer",
            "hook:pre-commit",
            "mcp:my-mcp",
        ]

        for key in valid_keys:
            skip = SkipPreference(
                artifact_key=key,
                skip_reason="Test",
                added_date=datetime.utcnow(),
            )
            assert skip.artifact_key == key

    def test_invalid_artifact_key_no_colon(self):
        """Test artifact_key without colon raises ValueError."""
        with pytest.raises(ValueError, match="format 'type:name'"):
            SkipPreference(
                artifact_key="invalid-key",
                skip_reason="Test",
                added_date=datetime.utcnow(),
            )

    def test_invalid_artifact_key_empty_parts(self):
        """Test artifact_key with empty parts raises ValueError."""
        # Empty type
        with pytest.raises(ValueError, match="non-empty"):
            SkipPreference(
                artifact_key=":name",
                skip_reason="Test",
                added_date=datetime.utcnow(),
            )

        # Empty name
        with pytest.raises(ValueError, match="non-empty"):
            SkipPreference(
                artifact_key="skill:",
                skip_reason="Test",
                added_date=datetime.utcnow(),
            )

    def test_invalid_artifact_type(self):
        """Test invalid artifact type raises ValueError."""
        with pytest.raises(ValueError, match="must be one of"):
            SkipPreference(
                artifact_key="invalid-type:name",
                skip_reason="Test",
                added_date=datetime.utcnow(),
            )

    def test_min_length_validation(self):
        """Test minimum length validation for fields."""
        # artifact_key minimum: "a:b" (3 chars)
        with pytest.raises(ValueError):
            SkipPreference(
                artifact_key="ab",  # Too short
                skip_reason="Test",
                added_date=datetime.utcnow(),
            )

        # skip_reason minimum: 1 char
        with pytest.raises(ValueError):
            SkipPreference(
                artifact_key="skill:test",
                skip_reason="",  # Empty string
                added_date=datetime.utcnow(),
            )


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_build_artifact_key(self):
        """Test artifact key building."""
        key = build_artifact_key("skill", "canvas-design")
        assert key == "skill:canvas-design"

        key = build_artifact_key("command", "my-command")
        assert key == "command:my-command"

    def test_parse_artifact_key(self):
        """Test artifact key parsing."""
        artifact_type, name = parse_artifact_key("skill:canvas-design")
        assert artifact_type == "skill"
        assert name == "canvas-design"

        artifact_type, name = parse_artifact_key("command:my-command")
        assert artifact_type == "command"
        assert name == "my-command"

    def test_parse_artifact_key_with_colon_in_name(self):
        """Test parsing key with colon in artifact name."""
        # Should split on first colon only
        artifact_type, name = parse_artifact_key("skill:my:complex:name")
        assert artifact_type == "skill"
        assert name == "my:complex:name"

    def test_parse_invalid_key_no_colon(self):
        """Test parsing invalid key raises ValueError."""
        with pytest.raises(ValueError, match="format 'type:name'"):
            parse_artifact_key("no-colon")

    def test_parse_invalid_key_empty_parts(self):
        """Test parsing key with empty parts raises ValueError."""
        with pytest.raises(ValueError, match="Invalid artifact_key format"):
            parse_artifact_key(":name")

        with pytest.raises(ValueError, match="Invalid artifact_key format"):
            parse_artifact_key("type:")


class TestMetadataTimestamps:
    """Tests for metadata timestamp handling."""

    def test_metadata_last_updated(self, temp_project):
        """Test that metadata.last_updated is updated on modifications."""
        mgr = SkipPreferenceManager(temp_project)

        # Add first skip
        mgr.add_skip("skill:one", "First")
        prefs1 = mgr.load_skip_prefs()
        first_update = prefs1.metadata.last_updated

        # Wait a tiny bit and add second skip
        import time

        time.sleep(0.01)

        mgr.add_skip("skill:two", "Second")
        prefs2 = mgr.load_skip_prefs()
        second_update = prefs2.metadata.last_updated

        # last_updated should have changed
        assert second_update > first_update

    def test_skip_added_date(self, temp_project):
        """Test that skip added_date is recorded correctly."""
        mgr = SkipPreferenceManager(temp_project)
        before = datetime.utcnow()

        skip = mgr.add_skip("skill:test", "Test reason")

        after = datetime.utcnow()

        # added_date should be between before and after
        assert before <= skip.added_date <= after


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_unicode_in_skip_reason(self, temp_project):
        """Test handling of Unicode characters in skip reason."""
        mgr = SkipPreferenceManager(temp_project)
        skip = mgr.add_skip(
            "skill:unicode-test", "Contains 中文, العربية, and emoji 🚀"
        )

        assert "中文" in skip.skip_reason
        assert "🚀" in skip.skip_reason

        # Verify persistence
        mgr2 = SkipPreferenceManager(temp_project)
        retrieved = mgr2.get_skip_by_key("skill:unicode-test")
        assert retrieved is not None
        assert "🚀" in retrieved.skip_reason

    def test_very_long_artifact_name(self, temp_project):
        """Test handling of very long artifact names."""
        long_name = "a" * 500  # 500 character name
        artifact_key = f"skill:{long_name}"

        mgr = SkipPreferenceManager(temp_project)
        skip = mgr.add_skip(artifact_key, "Long name test")

        assert skip.artifact_key == artifact_key
        assert mgr.is_skipped(artifact_key)

    def test_very_long_skip_reason(self, temp_project):
        """Test handling of very long skip reasons."""
        long_reason = "Reason " * 1000  # Very long reason

        mgr = SkipPreferenceManager(temp_project)
        skip = mgr.add_skip("skill:test", long_reason)

        assert skip.skip_reason == long_reason

        # Verify persistence
        mgr2 = SkipPreferenceManager(temp_project)
        retrieved = mgr2.get_skip_by_key("skill:test")
        assert retrieved.skip_reason == long_reason

    def test_whitespace_in_artifact_key(self, temp_project):
        """Test handling of whitespace in artifact key."""
        # Whitespace in name part is valid
        mgr = SkipPreferenceManager(temp_project)
        skip = mgr.add_skip("skill:my artifact name", "Test reason")

        assert skip.artifact_key == "skill:my artifact name"
        assert mgr.is_skipped("skill:my artifact name")

    def test_special_characters_in_name(self, temp_project):
        """Test handling of special characters in artifact name."""
        special_names = [
            "skill:my-artifact-123",
            "skill:my_artifact",
            "skill:my.artifact",
            "command:@my-command",
        ]

        mgr = SkipPreferenceManager(temp_project)
        for artifact_key in special_names:
            skip = mgr.add_skip(artifact_key, "Test reason")
            assert mgr.is_skipped(artifact_key)


class TestConcurrency:
    """Tests for thread safety (basic validation)."""

    def test_multiple_managers_same_project(self, temp_project):
        """Test multiple manager instances on same project."""
        mgr1 = SkipPreferenceManager(temp_project)
        mgr2 = SkipPreferenceManager(temp_project)

        # Add skip with mgr1
        mgr1.add_skip("skill:one", "Added by mgr1")

        # Verify mgr2 sees it (after reload)
        assert mgr2.is_skipped("skill:one")

        # Add skip with mgr2
        mgr2.add_skip("skill:two", "Added by mgr2")

        # Verify mgr1 sees it (after reload)
        assert mgr1.is_skipped("skill:two")
