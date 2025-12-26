"""Tests for import coordinator.

Tests cover:
- Import workflow from catalog to collection
- Conflict detection and resolution strategies
- Import tracking and status reporting
- Edge cases (empty catalogs, missing paths, etc.)
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from skillmeat.core.marketplace.import_coordinator import (
    ConflictStrategy,
    DownloadResult,
    ImportCoordinator,
    ImportEntry,
    ImportResult,
    ImportStatus,
    import_from_catalog,
)


class TestImportStatus:
    """Test suite for ImportStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert ImportStatus.PENDING == "pending"
        assert ImportStatus.SUCCESS == "success"
        assert ImportStatus.SKIPPED == "skipped"
        assert ImportStatus.CONFLICT == "conflict"
        assert ImportStatus.ERROR == "error"


class TestConflictStrategy:
    """Test suite for ConflictStrategy enum."""

    def test_strategy_values(self):
        """Test that all expected strategy values exist."""
        assert ConflictStrategy.SKIP == "skip"
        assert ConflictStrategy.OVERWRITE == "overwrite"
        assert ConflictStrategy.RENAME == "rename"


class TestImportEntry:
    """Test suite for ImportEntry."""

    def test_create_entry(self):
        """Test creating an import entry."""
        entry = ImportEntry(
            catalog_entry_id="cat_123",
            artifact_type="skill",
            name="test-skill",
            upstream_url="https://github.com/user/repo/skills/test-skill",
        )

        assert entry.catalog_entry_id == "cat_123"
        assert entry.artifact_type == "skill"
        assert entry.name == "test-skill"
        assert entry.status == ImportStatus.PENDING
        assert entry.error_message is None
        assert entry.local_path is None

    def test_entry_with_error(self):
        """Test entry with error status."""
        entry = ImportEntry(
            catalog_entry_id="cat_123",
            artifact_type="skill",
            name="broken-skill",
            upstream_url="https://github.com/user/repo/skills/broken-skill",
            status=ImportStatus.ERROR,
            error_message="Failed to download",
        )

        assert entry.status == ImportStatus.ERROR
        assert entry.error_message == "Failed to download"

    def test_entry_with_conflict(self):
        """Test entry with conflict information."""
        entry = ImportEntry(
            catalog_entry_id="cat_123",
            artifact_type="skill",
            name="existing-skill",
            upstream_url="https://github.com/user/repo/skills/existing-skill",
            status=ImportStatus.CONFLICT,
            conflict_with="/path/to/existing",
        )

        assert entry.status == ImportStatus.CONFLICT
        assert entry.conflict_with == "/path/to/existing"


class TestImportResult:
    """Test suite for ImportResult."""

    def test_empty_result(self):
        """Test empty import result."""
        result = ImportResult(
            import_id="import_123",
            source_id="src_456",
            started_at=datetime.utcnow(),
        )

        assert result.import_id == "import_123"
        assert result.source_id == "src_456"
        assert result.success_count == 0
        assert result.skipped_count == 0
        assert result.conflict_count == 0
        assert result.error_count == 0
        assert result.summary["total"] == 0

    def test_result_counts(self):
        """Test count properties."""
        result = ImportResult(
            import_id="import_123",
            source_id="src_456",
            started_at=datetime.utcnow(),
        )

        # Add entries with different statuses
        result.entries.append(
            ImportEntry("e1", "skill", "s1", "url1", status=ImportStatus.SUCCESS)
        )
        result.entries.append(
            ImportEntry("e2", "skill", "s2", "url2", status=ImportStatus.SUCCESS)
        )
        result.entries.append(
            ImportEntry("e3", "skill", "s3", "url3", status=ImportStatus.SKIPPED)
        )
        result.entries.append(
            ImportEntry("e4", "skill", "s4", "url4", status=ImportStatus.CONFLICT)
        )
        result.entries.append(
            ImportEntry("e5", "skill", "s5", "url5", status=ImportStatus.ERROR)
        )

        assert result.success_count == 2
        assert result.skipped_count == 1
        assert result.conflict_count == 1
        assert result.error_count == 1

    def test_summary(self):
        """Test summary property."""
        result = ImportResult(
            import_id="import_123",
            source_id="src_456",
            started_at=datetime.utcnow(),
        )

        result.entries.extend(
            [
                ImportEntry("e1", "skill", "s1", "url1", status=ImportStatus.SUCCESS),
                ImportEntry("e2", "skill", "s2", "url2", status=ImportStatus.SKIPPED),
                ImportEntry("e3", "skill", "s3", "url3", status=ImportStatus.ERROR),
            ]
        )

        summary = result.summary
        assert summary["total"] == 3
        assert summary["success"] == 1
        assert summary["skipped"] == 1
        assert summary["conflict"] == 0
        assert summary["error"] == 1


class TestImportCoordinator:
    """Test suite for ImportCoordinator."""

    @pytest.fixture
    def temp_collection(self, tmp_path):
        """Create a temporary collection directory."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        return collection_path

    @pytest.fixture
    def coordinator(self, temp_collection):
        """Create an import coordinator with temp collection."""
        return ImportCoordinator(collection_path=temp_collection)

    @pytest.fixture
    def mock_download(self):
        """Mock _download_artifact to return success without HTTP calls."""
        with patch.object(
            ImportCoordinator,
            '_download_artifact',
            return_value=DownloadResult(success=True, files_downloaded=3)
        ) as mock:
            yield mock

    @pytest.fixture
    def mock_manifest(self):
        """Mock _update_manifest to avoid file operations."""
        with patch.object(ImportCoordinator, '_update_manifest') as mock:
            yield mock

    def test_init_default_path(self, monkeypatch, tmp_path):
        """Test initialization with default collection path."""
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        coordinator = ImportCoordinator()
        expected_path = home_dir / ".skillmeat" / "collection"
        assert coordinator.collection_path == expected_path

    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom path."""
        custom_path = tmp_path / "custom"
        coordinator = ImportCoordinator(collection_path=custom_path)
        assert coordinator.collection_path == custom_path

    def test_import_entries_empty_list(self, coordinator):
        """Test importing empty entry list."""
        result = coordinator.import_entries([], "source_123")

        assert result.source_id == "source_123"
        assert len(result.entries) == 0
        assert result.success_count == 0

    def test_import_entries_no_conflicts(self, coordinator, mock_download, mock_manifest):
        """Test importing entries with no conflicts."""
        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "skill1",
                "upstream_url": "https://github.com/user/repo/skills/skill1",
            },
            {
                "id": "e2",
                "artifact_type": "command",
                "name": "command1",
                "upstream_url": "https://github.com/user/repo/commands/command1",
            },
        ]

        result = coordinator.import_entries(entries, "source_123")

        assert result.success_count == 2
        assert result.skipped_count == 0
        assert result.error_count == 0
        assert len(result.entries) == 2

    def test_import_entries_with_conflicts_skip(self, coordinator, temp_collection, mock_download, mock_manifest):
        """Test importing with conflicts using skip strategy."""
        # Create existing artifact (old structure)
        existing_skill = temp_collection / "skills" / "existing-skill"
        existing_skill.mkdir(parents=True)
        (existing_skill / "SKILL.md").write_text("# Existing")

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "new-skill",
                "upstream_url": "https://github.com/user/repo/skills/new-skill",
            },
            {
                "id": "e2",
                "artifact_type": "skill",
                "name": "existing-skill",  # Conflict!
                "upstream_url": "https://github.com/user/repo/skills/existing-skill",
            },
        ]

        result = coordinator.import_entries(
            entries, "source_123", strategy=ConflictStrategy.SKIP
        )

        assert result.success_count == 1  # Only new-skill
        assert result.skipped_count == 1  # existing-skill skipped
        assert result.conflict_count == 0  # Counted as skipped

        # Check which entry was skipped
        skipped_entry = next(e for e in result.entries if e.status == ImportStatus.SKIPPED)
        assert skipped_entry.name == "existing-skill"
        assert skipped_entry.conflict_with is not None

    def test_import_entries_with_conflicts_rename(self, coordinator, temp_collection, mock_download, mock_manifest):
        """Test importing with conflicts using rename strategy."""
        # Create existing artifact
        existing_skill = temp_collection / "skills" / "existing-skill"
        existing_skill.mkdir(parents=True)
        (existing_skill / "SKILL.md").write_text("# Existing")

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "existing-skill",  # Will be renamed
                "upstream_url": "https://github.com/user/repo/skills/existing-skill",
            },
        ]

        result = coordinator.import_entries(
            entries, "source_123", strategy=ConflictStrategy.RENAME
        )

        assert result.success_count == 1
        assert result.skipped_count == 0

        # Check that name was changed
        renamed_entry = result.entries[0]
        assert renamed_entry.status == ImportStatus.SUCCESS
        assert renamed_entry.name != "existing-skill"
        assert "existing-skill" in renamed_entry.name  # Should be based on original

    def test_import_entries_with_conflicts_overwrite(self, coordinator, temp_collection, mock_download, mock_manifest):
        """Test importing with conflicts using overwrite strategy."""
        # Create existing artifact
        existing_skill = temp_collection / "skills" / "existing-skill"
        existing_skill.mkdir(parents=True)
        (existing_skill / "SKILL.md").write_text("# Existing")

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "existing-skill",  # Will overwrite
                "upstream_url": "https://github.com/user/repo/skills/existing-skill",
            },
        ]

        result = coordinator.import_entries(
            entries, "source_123", strategy=ConflictStrategy.OVERWRITE
        )

        assert result.success_count == 1
        assert result.skipped_count == 0

        # Entry should have original name (not renamed)
        overwritten_entry = result.entries[0]
        assert overwritten_entry.name == "existing-skill"
        assert overwritten_entry.status == ImportStatus.SUCCESS

    def test_import_entries_with_errors(self, coordinator, monkeypatch):
        """Test handling of import errors."""
        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "good-skill",
                "upstream_url": "https://github.com/user/repo/skills/good-skill",
            },
        ]

        # Mock _process_entry to raise an error
        def mock_process_error(entry, existing, strategy):
            if entry.name == "good-skill":
                raise ValueError("Simulated error")

        monkeypatch.setattr(coordinator, "_process_entry", mock_process_error)

        result = coordinator.import_entries(entries, "source_123")

        assert result.success_count == 0
        assert result.error_count == 1
        assert result.entries[0].status == ImportStatus.ERROR
        assert "Simulated error" in result.entries[0].error_message

    def test_compute_local_path_old_structure(self, coordinator, temp_collection):
        """Test local path computation with old structure."""
        # Old structure: skills/ directly in collection
        (temp_collection / "skills").mkdir()

        path = coordinator._compute_local_path("skill", "my-skill")
        expected = str(temp_collection / "skills" / "my-skill")
        assert path == expected

    def test_compute_local_path_new_structure(self, coordinator, temp_collection):
        """Test local path computation with new structure."""
        # New structure: artifacts/skills/
        (temp_collection / "artifacts").mkdir()

        path = coordinator._compute_local_path("skill", "my-skill")
        expected = str(temp_collection / "artifacts" / "skills" / "my-skill")
        assert path == expected

    def test_compute_local_path_plural_handling(self, coordinator, temp_collection):
        """Test that artifact types are properly pluralized."""
        (temp_collection / "artifacts").mkdir()

        # Test various artifact types
        assert "skills" in coordinator._compute_local_path("skill", "test")
        assert "commands" in coordinator._compute_local_path("command", "test")
        assert "agents" in coordinator._compute_local_path("agent", "test")

    def test_get_existing_artifacts_old_structure(self, coordinator, temp_collection):
        """Test getting existing artifacts with old structure."""
        # Create old structure
        (temp_collection / "skills" / "skill1").mkdir(parents=True)
        (temp_collection / "commands" / "cmd1").mkdir(parents=True)

        existing = coordinator._get_existing_artifacts()

        assert "skill:skill1" in existing
        assert "command:cmd1" in existing
        assert len(existing) == 2

    def test_get_existing_artifacts_new_structure(self, coordinator, temp_collection):
        """Test getting existing artifacts with new structure."""
        # Create new structure
        artifacts_dir = temp_collection / "artifacts"
        (artifacts_dir / "skills" / "skill1").mkdir(parents=True)
        (artifacts_dir / "commands" / "cmd1").mkdir(parents=True)
        (artifacts_dir / "agents" / "agent1").mkdir(parents=True)

        existing = coordinator._get_existing_artifacts()

        assert "skill:skill1" in existing
        assert "command:cmd1" in existing
        assert "agent:agent1" in existing
        assert len(existing) == 3

    def test_get_existing_artifacts_empty_collection(self, coordinator, temp_collection):
        """Test getting existing artifacts from empty collection."""
        existing = coordinator._get_existing_artifacts()
        assert len(existing) == 0

    def test_check_conflicts(self, coordinator, temp_collection):
        """Test conflict checking without importing."""
        # Create existing artifact
        (temp_collection / "skills" / "existing-skill").mkdir(parents=True)

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "new-skill",
                "upstream_url": "url1",
            },
            {
                "id": "e2",
                "artifact_type": "skill",
                "name": "existing-skill",  # Conflict!
                "upstream_url": "url2",
            },
        ]

        conflicts = coordinator.check_conflicts(entries)

        assert len(conflicts) == 1
        entry_id, name, path = conflicts[0]
        assert entry_id == "e2"
        assert name == "existing-skill"
        assert "existing-skill" in path

    def test_rename_multiple_conflicts(self, coordinator, temp_collection):
        """Test that rename handles multiple conflicts with incrementing suffix."""
        # Create existing artifacts
        (temp_collection / "skills" / "skill").mkdir(parents=True)
        (temp_collection / "skills" / "skill-1").mkdir(parents=True)

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "skill",  # Will conflict
                "upstream_url": "url1",
            },
        ]

        result = coordinator.import_entries(
            entries, "source_123", strategy=ConflictStrategy.RENAME
        )

        # Should be renamed to skill-2
        assert result.entries[0].name == "skill-2"

    def test_process_entry_sets_local_path(self, coordinator):
        """Test that process_entry sets local_path."""
        entry = ImportEntry(
            catalog_entry_id="e1",
            artifact_type="skill",
            name="test-skill",
            upstream_url="https://github.com/user/repo/skills/test-skill",
        )

        coordinator._process_entry(entry, {}, ConflictStrategy.SKIP)

        assert entry.local_path is not None
        assert "test-skill" in entry.local_path

    def test_import_result_completed_at(self, coordinator):
        """Test that completed_at is set after import."""
        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "skill1",
                "upstream_url": "url1",
            },
        ]

        result = coordinator.import_entries(entries, "source_123")

        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_import_result_has_uuid(self, coordinator):
        """Test that import result has UUID."""
        entries = []
        result = coordinator.import_entries(entries, "source_123")

        # Should be a valid UUID format
        import uuid

        try:
            uuid.UUID(result.import_id)
            is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        assert is_valid_uuid


class TestImportFromCatalog:
    """Test suite for import_from_catalog convenience function."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Auto-apply mocks to all tests in this class."""
        with patch.object(
            ImportCoordinator,
            '_download_artifact',
            return_value=DownloadResult(success=True, files_downloaded=3)
        ), patch.object(ImportCoordinator, '_update_manifest'):
            yield

    def test_basic_import(self, tmp_path):
        """Test basic import using convenience function."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "skill1",
                "upstream_url": "url1",
            },
        ]

        result = import_from_catalog(entries, "source_123", collection_path=collection_path)

        assert result.success_count == 1
        assert result.source_id == "source_123"

    def test_with_skip_strategy(self, tmp_path):
        """Test import with skip strategy string."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        (collection_path / "skills" / "existing").mkdir(parents=True)

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "existing",
                "upstream_url": "url1",
            },
        ]

        result = import_from_catalog(
            entries, "source_123", strategy="skip", collection_path=collection_path
        )

        assert result.skipped_count == 1

    def test_with_rename_strategy(self, tmp_path):
        """Test import with rename strategy string."""
        collection_path = tmp_path / "collection"
        collection_path.mkdir()
        (collection_path / "skills" / "existing").mkdir(parents=True)

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "existing",
                "upstream_url": "url1",
            },
        ]

        result = import_from_catalog(
            entries, "source_123", strategy="rename", collection_path=collection_path
        )

        assert result.success_count == 1
        assert result.entries[0].name != "existing"


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Auto-apply mocks to all tests in this class."""
        with patch.object(
            ImportCoordinator,
            '_download_artifact',
            return_value=DownloadResult(success=True, files_downloaded=3)
        ), patch.object(ImportCoordinator, '_update_manifest'):
            yield

    def test_empty_entry_id(self, tmp_path):
        """Test handling of entry with empty ID."""
        coordinator = ImportCoordinator(collection_path=tmp_path / "collection")

        entries = [
            {
                "id": "",  # Empty ID
                "artifact_type": "skill",
                "name": "test",
                "upstream_url": "url",
            },
        ]

        result = coordinator.import_entries(entries, "source_123")
        assert len(result.entries) == 1

    def test_missing_entry_fields(self, tmp_path):
        """Test handling of entries with missing fields."""
        coordinator = ImportCoordinator(collection_path=tmp_path / "collection")

        entries = [
            {
                "id": "e1",
                # Missing artifact_type, name, upstream_url
            },
        ]

        result = coordinator.import_entries(entries, "source_123")
        assert len(result.entries) == 1
        # Should handle gracefully (empty strings from .get())

    def test_special_characters_in_name(self, tmp_path):
        """Test handling of special characters in artifact name."""
        coordinator = ImportCoordinator(collection_path=tmp_path / "collection")

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "my-skill (v2)",  # Parentheses
                "upstream_url": "url1",
            },
        ]

        result = coordinator.import_entries(entries, "source_123")
        assert result.success_count == 1

    def test_unicode_in_name(self, tmp_path):
        """Test handling of unicode in artifact name."""
        coordinator = ImportCoordinator(collection_path=tmp_path / "collection")

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "日本語スキル",
                "upstream_url": "url1",
            },
        ]

        result = coordinator.import_entries(entries, "source_123")
        assert result.success_count == 1

    def test_very_long_name(self, tmp_path):
        """Test handling of very long artifact name."""
        coordinator = ImportCoordinator(collection_path=tmp_path / "collection")

        long_name = "a" * 500  # Very long name
        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": long_name,
                "upstream_url": "url1",
            },
        ]

        result = coordinator.import_entries(entries, "source_123")
        assert result.success_count == 1

    def test_rename_with_many_existing(self, tmp_path):
        """Test rename strategy with many existing conflicts."""
        collection_path = tmp_path / "collection"
        skills_dir = collection_path / "skills"
        skills_dir.mkdir(parents=True)

        # Create existing skills
        for i in range(10):
            (skills_dir / f"skill-{i}").mkdir()

        coordinator = ImportCoordinator(collection_path=collection_path)

        entries = [
            {
                "id": "e1",
                "artifact_type": "skill",
                "name": "skill",
                "upstream_url": "url1",
            },
        ]

        result = coordinator.import_entries(
            entries, "source_123", strategy=ConflictStrategy.RENAME
        )

        # Should find an available name
        assert result.success_count == 1
        assert result.entries[0].name not in [f"skill-{i}" for i in range(10)]
