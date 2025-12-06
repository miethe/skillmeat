"""Unit tests for ImportStatus enum and determination logic.

Tests comprehensive coverage of:
- ImportStatus enum values and serialization
- ImportResult schema with status field
- Status determination logic in ArtifactImporter
- Integration with BulkImportResult
"""

import json
from unittest.mock import Mock

import pytest

from skillmeat.api.schemas.discovery import (
    BulkImportResult,
    ImportResult,
    ImportStatus,
)
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.importer import ArtifactImporter, BulkImportArtifactData


class TestImportStatusEnum:
    """Tests for ImportStatus enum values and serialization."""

    def test_enum_values(self):
        """Enum has SUCCESS, SKIPPED, FAILED values."""
        assert ImportStatus.SUCCESS.value == "success"
        assert ImportStatus.SKIPPED.value == "skipped"
        assert ImportStatus.FAILED.value == "failed"

    def test_json_serialization(self):
        """Status serializes as string value, not enum name."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SUCCESS,
            message="Test"
        )
        json_str = result.model_dump_json()
        assert '"status":"success"' in json_str or '"status": "success"' in json_str

    def test_string_instantiation(self):
        """Can instantiate with string value."""
        result = ImportResult(
            artifact_id="skill:test",
            status="success",  # String, not enum
            message="Test"
        )
        assert result.status == ImportStatus.SUCCESS

    def test_enum_comparison(self):
        """Enum values can be compared with strings."""
        assert ImportStatus.SUCCESS == "success"
        assert ImportStatus.SKIPPED == "skipped"
        assert ImportStatus.FAILED == "failed"


class TestImportResultSchema:
    """Tests for ImportResult schema with new status field."""

    def test_success_status_no_skip_reason(self):
        """SUCCESS status should not have skip_reason."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SUCCESS,
            message="Imported successfully"
        )
        assert result.skip_reason is None
        assert result.error is None

    def test_skipped_status_with_skip_reason(self):
        """SKIPPED status should have skip_reason."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SKIPPED,
            message="Skipped",
            skip_reason="Already exists in Collection"
        )
        assert result.skip_reason == "Already exists in Collection"
        assert result.error is None

    def test_failed_status_with_error(self):
        """FAILED status should have error field."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Permission denied"
        )
        assert result.error == "Permission denied"
        assert result.skip_reason is None

    def test_backward_compat_success_property(self):
        """success property returns True for SUCCESS status."""
        result_success = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SUCCESS,
            message="OK"
        )
        result_skipped = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SKIPPED,
            message="Skip"
        )
        result_failed = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.FAILED,
            message="Fail"
        )
        assert result_success.success is True
        assert result_skipped.success is False
        assert result_failed.success is False

    def test_all_statuses_serialize_correctly(self):
        """All status values serialize to correct JSON."""
        results = [
            ImportResult(artifact_id="skill:1", status=ImportStatus.SUCCESS, message="OK"),
            ImportResult(artifact_id="skill:2", status=ImportStatus.SKIPPED, message="Skip", skip_reason="Exists"),
            ImportResult(artifact_id="skill:3", status=ImportStatus.FAILED, message="Fail", error="Error"),
        ]

        for result in results:
            json_data = json.loads(result.model_dump_json())
            assert json_data["status"] in ["success", "skipped", "failed"]

    def test_skip_reason_optional_for_failed(self):
        """FAILED status can have None skip_reason."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Something went wrong"
        )
        assert result.skip_reason is None
        assert result.error == "Something went wrong"

    def test_error_optional_for_skipped(self):
        """SKIPPED status can have None error."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SKIPPED,
            message="Skipped",
            skip_reason="Already exists"
        )
        assert result.error is None
        assert result.skip_reason == "Already exists"


class TestDetermineImportStatus:
    """Tests for determine_import_status() method."""

    @pytest.fixture
    def importer(self, tmp_path):
        """Create importer instance for testing."""
        # Create mock managers
        collection_mgr = Mock(spec=CollectionManager)
        artifact_mgr = Mock()

        return ArtifactImporter(
            artifact_manager=artifact_mgr,
            collection_manager=collection_mgr,
        )

    def test_success_when_import_succeeds(self, importer):
        """Returns SUCCESS when artifact imported successfully."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=True,
            already_exists=False
        )
        assert status == ImportStatus.SUCCESS
        assert skip_reason is None

    def test_skipped_when_in_collection(self, importer):
        """Returns SKIPPED with reason when in Collection."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=False,
            already_exists=True,
            exists_location="collection"
        )
        assert status == ImportStatus.SKIPPED
        assert "Collection" in skip_reason
        assert skip_reason == "Already exists in Collection"

    def test_skipped_when_in_project(self, importer):
        """Returns SKIPPED with reason when in Project."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=False,
            already_exists=True,
            exists_location="project"
        )
        assert status == ImportStatus.SKIPPED
        assert "Project" in skip_reason
        assert skip_reason == "Already exists in Project"

    def test_skipped_when_in_both(self, importer):
        """Returns SKIPPED with reason when in both locations."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=False,
            already_exists=True,
            exists_location="both"
        )
        assert status == ImportStatus.SKIPPED
        assert "both" in skip_reason.lower()
        assert "Collection" in skip_reason
        assert "Project" in skip_reason

    def test_failed_when_import_fails(self, importer):
        """Returns FAILED when import fails with error."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=False,
            already_exists=False
        )
        assert status == ImportStatus.FAILED
        assert skip_reason is None

    def test_skipped_when_exists_no_location(self, importer):
        """Returns SKIPPED with generic reason when location not specified."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=False,
            already_exists=True,
            exists_location=None
        )
        assert status == ImportStatus.SKIPPED
        assert skip_reason == "Already exists"

    def test_success_overrides_error(self, importer):
        """SUCCESS status when import_success=True, even if error provided."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=True,
            error="Some error",
            already_exists=False
        )
        assert status == ImportStatus.SUCCESS
        assert skip_reason is None

    def test_already_exists_overrides_success(self, importer):
        """SKIPPED status when already_exists=True, even if import_success=True."""
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=True,
            already_exists=True,
            exists_location="collection"
        )
        assert status == ImportStatus.SKIPPED
        assert skip_reason == "Already exists in Collection"


class TestBulkImportResultStatusCounts:
    """Tests for status counts in BulkImportResult."""

    def test_total_skipped_calculated(self):
        """total_skipped reflects SKIPPED status count."""
        results = [
            ImportResult(artifact_id="skill:1", status=ImportStatus.SUCCESS, message="OK"),
            ImportResult(artifact_id="skill:2", status=ImportStatus.SKIPPED, message="Skip", skip_reason="Exists"),
            ImportResult(artifact_id="skill:3", status=ImportStatus.SKIPPED, message="Skip", skip_reason="Exists"),
            ImportResult(artifact_id="skill:4", status=ImportStatus.FAILED, message="Fail", error="Error"),
        ]
        bulk = BulkImportResult(
            total_requested=4,
            total_imported=1,
            total_skipped=2,
            total_failed=1,
            results=results,
            duration_ms=100.0
        )
        assert bulk.total_skipped == 2

    def test_summary_computed(self):
        """summary property generates readable string."""
        bulk = BulkImportResult(
            total_requested=10,
            total_imported=7,
            total_skipped=2,
            total_failed=1,
            results=[],
            duration_ms=100.0
        )
        assert "7 imported" in bulk.summary
        assert "2 skipped" in bulk.summary
        assert "1 failed" in bulk.summary

    def test_summary_no_skipped(self):
        """summary excludes skipped when count is 0."""
        bulk = BulkImportResult(
            total_requested=10,
            total_imported=9,
            total_skipped=0,
            total_failed=1,
            results=[],
            duration_ms=100.0
        )
        assert "9 imported" in bulk.summary
        assert "skipped" not in bulk.summary
        assert "1 failed" in bulk.summary

    def test_summary_all_success(self):
        """summary shows only imported when all succeed."""
        bulk = BulkImportResult(
            total_requested=10,
            total_imported=10,
            total_skipped=0,
            total_failed=0,
            results=[],
            duration_ms=100.0
        )
        assert bulk.summary == "10 imported"

    def test_summary_all_failed(self):
        """summary shows only failed when all fail."""
        bulk = BulkImportResult(
            total_requested=10,
            total_imported=0,
            total_skipped=0,
            total_failed=10,
            results=[],
            duration_ms=100.0
        )
        assert bulk.summary == "10 failed"

    def test_summary_all_skipped(self):
        """summary shows only skipped when all skipped."""
        bulk = BulkImportResult(
            total_requested=10,
            total_imported=0,
            total_skipped=10,
            total_failed=0,
            results=[],
            duration_ms=100.0
        )
        assert bulk.summary == "10 skipped"

    def test_summary_empty_results(self):
        """summary handles empty results list."""
        bulk = BulkImportResult(
            total_requested=0,
            total_imported=0,
            total_skipped=0,
            total_failed=0,
            results=[],
            duration_ms=100.0
        )
        assert bulk.summary == "No artifacts processed"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_import_result_with_empty_strings(self):
        """ImportResult handles empty strings correctly."""
        result = ImportResult(
            artifact_id="",
            status=ImportStatus.SUCCESS,
            message=""
        )
        assert result.artifact_id == ""
        assert result.message == ""

    def test_import_result_with_none_optional_fields(self):
        """ImportResult handles None optional fields correctly."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SUCCESS,
            message="OK",
            error=None,
            skip_reason=None
        )
        assert result.error is None
        assert result.skip_reason is None

    def test_bulk_import_result_with_mismatched_counts(self):
        """BulkImportResult allows counts that don't match results length."""
        # This is intentional - counts can be aggregated from multiple sources
        bulk = BulkImportResult(
            total_requested=10,
            total_imported=7,
            total_skipped=2,
            total_failed=1,
            results=[],  # Empty results list
            duration_ms=100.0
        )
        assert bulk.total_requested == 10
        assert len(bulk.results) == 0

    def test_determine_import_status_with_conflicting_flags(self):
        """determine_import_status handles conflicting flags correctly."""
        importer = ArtifactImporter(
            artifact_manager=Mock(),
            collection_manager=Mock(spec=CollectionManager),
        )

        # already_exists takes precedence
        status, skip_reason = importer.determine_import_status(
            artifact_key="skill:test",
            import_success=True,
            already_exists=True,
            exists_location="collection"
        )
        assert status == ImportStatus.SKIPPED

    def test_import_result_json_roundtrip(self):
        """ImportResult can be serialized and deserialized."""
        original = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SKIPPED,
            message="Already exists",
            skip_reason="Already exists in Collection"
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize from JSON
        deserialized = ImportResult.model_validate_json(json_str)

        assert deserialized.artifact_id == original.artifact_id
        assert deserialized.status == original.status
        assert deserialized.message == original.message
        assert deserialized.skip_reason == original.skip_reason

    def test_bulk_import_result_json_roundtrip(self):
        """BulkImportResult can be serialized and deserialized."""
        original = BulkImportResult(
            total_requested=3,
            total_imported=1,
            total_skipped=1,
            total_failed=1,
            results=[
                ImportResult(artifact_id="skill:1", status=ImportStatus.SUCCESS, message="OK"),
                ImportResult(artifact_id="skill:2", status=ImportStatus.SKIPPED, message="Skip", skip_reason="Exists"),
                ImportResult(artifact_id="skill:3", status=ImportStatus.FAILED, message="Fail", error="Error"),
            ],
            duration_ms=250.5
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize from JSON
        deserialized = BulkImportResult.model_validate_json(json_str)

        assert deserialized.total_requested == original.total_requested
        assert deserialized.total_imported == original.total_imported
        assert deserialized.total_skipped == original.total_skipped
        assert deserialized.total_failed == original.total_failed
        assert len(deserialized.results) == len(original.results)
        assert deserialized.duration_ms == original.duration_ms
