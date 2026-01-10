"""Unit tests for graceful error handling in bulk import.

Tests for P1-T1: Backend - Validate Artifact Structure & Handle Errors Gracefully

Covers:
- YAML parsing errors
- Invalid artifact structure
- Missing metadata files
- Error classification
- Per-artifact error reporting
- Mixed batch processing (valid + invalid artifacts)
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from skillmeat.api.schemas.discovery import (
    BulkImportResult,
    ErrorReasonCode,
    ImportResult,
    ImportStatus,
)
from skillmeat.core.collection import Collection, CollectionManager
from skillmeat.core.importer import (
    ArtifactImporter,
    BulkImportArtifactData,
    ImportResultData,
)


class TestErrorReasonCodeEnum:
    """Tests for ErrorReasonCode enum values."""

    def test_enum_values_validation_errors(self):
        """Validation error reason codes exist."""
        assert ErrorReasonCode.INVALID_STRUCTURE.value == "invalid_structure"
        assert ErrorReasonCode.YAML_PARSE_ERROR.value == "yaml_parse_error"
        assert ErrorReasonCode.MISSING_METADATA.value == "missing_metadata"
        assert ErrorReasonCode.INVALID_TYPE.value == "invalid_type"
        assert ErrorReasonCode.INVALID_SOURCE.value == "invalid_source"

    def test_enum_values_import_errors(self):
        """Import error reason codes exist."""
        assert ErrorReasonCode.IMPORT_ERROR.value == "import_error"
        assert ErrorReasonCode.NETWORK_ERROR.value == "network_error"
        assert ErrorReasonCode.PERMISSION_ERROR.value == "permission_error"
        assert ErrorReasonCode.IO_ERROR.value == "io_error"

    def test_enum_values_skip_reasons(self):
        """Skip reason codes exist."""
        assert ErrorReasonCode.ALREADY_EXISTS.value == "already_exists"
        assert ErrorReasonCode.IN_SKIP_LIST.value == "in_skip_list"
        assert ErrorReasonCode.DUPLICATE.value == "duplicate"


class TestImportResultWithReasonCode:
    """Tests for ImportResult schema with reason_code field."""

    def test_failed_with_reason_code(self):
        """FAILED status can have reason_code."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Invalid YAML frontmatter",
            reason_code=ErrorReasonCode.YAML_PARSE_ERROR,
            details="Line 5, Column 3: expected ':' but found '-'"
        )
        assert result.reason_code == ErrorReasonCode.YAML_PARSE_ERROR
        assert result.details is not None
        assert "Line 5" in result.details

    def test_failed_with_path(self):
        """FAILED status includes path when available."""
        result = ImportResult(
            artifact_id="skill:test",
            path="/path/to/artifact",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Missing SKILL.md"
        )
        assert result.path == "/path/to/artifact"

    def test_success_no_reason_code(self):
        """SUCCESS status has no reason_code."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.SUCCESS,
            message="Imported successfully"
        )
        assert result.reason_code is None
        assert result.details is None

    def test_reason_code_serialization(self):
        """reason_code serializes correctly to JSON."""
        result = ImportResult(
            artifact_id="skill:test",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="YAML error",
            reason_code=ErrorReasonCode.YAML_PARSE_ERROR
        )
        json_data = result.model_dump()
        assert json_data["reason_code"] == "yaml_parse_error"


class TestClassifyError:
    """Tests for error classification logic."""

    @pytest.fixture
    def importer(self):
        """Create importer instance for testing."""
        return ArtifactImporter(
            artifact_manager=Mock(),
            collection_manager=Mock(spec=CollectionManager),
        )

    def test_classify_yaml_error(self, importer):
        """YAML parsing errors classified correctly."""
        # Create a YAML error with problem_mark
        yaml_error = yaml.YAMLError("test error")
        yaml_error.problem_mark = Mock()
        yaml_error.problem_mark.line = 4
        yaml_error.problem_mark.column = 2
        yaml_error.problem = "expected ':'"

        reason_code, message, details = importer._classify_error(yaml_error)

        assert reason_code == "yaml_parse_error"
        assert "YAML" in message
        assert details is not None
        assert "Line 5" in details  # 1-indexed

    def test_classify_permission_error(self, importer):
        """Permission errors classified correctly."""
        error = PermissionError("Access denied to /path/to/file")

        reason_code, message, details = importer._classify_error(error, "/path/to/file")

        assert reason_code == "permission_error"
        assert "Permission denied" in message

    def test_classify_io_error(self, importer):
        """I/O errors classified correctly."""
        error = IOError("File not found")

        reason_code, message, details = importer._classify_error(error, "/path/to/file")

        assert reason_code == "io_error"
        assert "I/O error" in message

    def test_classify_network_error_from_message(self, importer):
        """Network errors detected from message content."""
        error = Exception("Connection timeout to server")

        reason_code, message, details = importer._classify_error(error)

        assert reason_code == "network_error"
        assert "timeout" in message.lower()

    def test_classify_404_error(self, importer):
        """404 errors classified as network errors."""
        error = Exception("404: Repository not found")

        reason_code, message, details = importer._classify_error(error)

        assert reason_code == "network_error"
        assert "not found" in message.lower()

    def test_classify_invalid_type_error(self, importer):
        """Invalid type ValueError classified correctly."""
        error = ValueError("Invalid artifact type: foo")

        reason_code, message, details = importer._classify_error(error)

        assert reason_code == "invalid_type"

    def test_classify_invalid_source_error(self, importer):
        """Invalid source ValueError classified correctly."""
        error = ValueError("Invalid source format")

        reason_code, message, details = importer._classify_error(error)

        assert reason_code == "invalid_source"

    def test_classify_missing_metadata_error(self, importer):
        """Missing metadata errors classified correctly."""
        error = KeyError("name")

        reason_code, message, details = importer._classify_error(error)

        assert reason_code == "missing_metadata"
        assert "Missing required field" in message

    def test_classify_generic_error(self, importer):
        """Unknown errors get generic import_error code."""
        error = Exception("Something went wrong")

        reason_code, message, details = importer._classify_error(error)

        assert reason_code == "import_error"


class TestValidateArtifactStructure:
    """Tests for artifact structure validation."""

    @pytest.fixture
    def importer(self):
        """Create importer instance for testing."""
        return ArtifactImporter(
            artifact_manager=Mock(),
            collection_manager=Mock(spec=CollectionManager),
        )

    @pytest.fixture
    def valid_skill_dir(self, tmp_path):
        """Create a valid skill directory."""
        skill_dir = tmp_path / "valid-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: valid-skill
description: A valid test skill
---

# Valid Skill

Content here.
""")
        return skill_dir

    @pytest.fixture
    def invalid_yaml_skill_dir(self, tmp_path):
        """Create a skill directory with invalid YAML frontmatter."""
        skill_dir = tmp_path / "invalid-yaml-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        # Invalid YAML: indentation error causes parse failure
        skill_md.write_text("""---
name: valid-skill
  indented: wrong
---

# Invalid Skill
""")
        return skill_dir

    @pytest.fixture
    def missing_metadata_skill_dir(self, tmp_path):
        """Create a skill directory without SKILL.md."""
        skill_dir = tmp_path / "missing-metadata-skill"
        skill_dir.mkdir()
        # Create some other file but not SKILL.md
        (skill_dir / "README.md").write_text("# README")
        return skill_dir

    def test_validate_valid_skill(self, importer, valid_skill_dir):
        """Valid skill passes validation."""
        artifact = BulkImportArtifactData(
            source="local/skill/valid-skill",
            artifact_type="skill",
            name="valid-skill",
            path=str(valid_skill_dir),
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is None  # None means validation passed

    def test_validate_missing_path(self, importer):
        """Local source without path fails validation."""
        artifact = BulkImportArtifactData(
            source="local/skill/test-skill",
            artifact_type="skill",
            name="test-skill",
            path=None,  # Missing path
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is not None
        assert result.success is False
        assert result.reason_code == "invalid_source"
        assert "requires 'path' field" in result.error

    def test_validate_nonexistent_path(self, importer, tmp_path):
        """Non-existent path fails validation."""
        artifact = BulkImportArtifactData(
            source="local/skill/nonexistent",
            artifact_type="skill",
            name="nonexistent",
            path=str(tmp_path / "nonexistent"),
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is not None
        assert result.success is False
        assert result.reason_code == "invalid_structure"
        assert "does not exist" in result.error

    def test_validate_path_is_file(self, importer, tmp_path):
        """Path pointing to a file fails validation."""
        file_path = tmp_path / "skill-file"
        file_path.write_text("This is a file, not a directory")

        artifact = BulkImportArtifactData(
            source="local/skill/skill-file",
            artifact_type="skill",
            name="skill-file",
            path=str(file_path),
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is not None
        assert result.success is False
        assert result.reason_code == "invalid_structure"
        assert "not a directory" in result.error

    def test_validate_missing_skill_md(self, importer, missing_metadata_skill_dir):
        """Missing SKILL.md fails validation."""
        artifact = BulkImportArtifactData(
            source="local/skill/missing-metadata-skill",
            artifact_type="skill",
            name="missing-metadata-skill",
            path=str(missing_metadata_skill_dir),
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is not None
        assert result.success is False
        assert result.reason_code == "missing_metadata"
        assert "SKILL.md" in result.error

    def test_validate_invalid_yaml_frontmatter(self, importer, invalid_yaml_skill_dir):
        """Invalid YAML frontmatter fails validation."""
        artifact = BulkImportArtifactData(
            source="local/skill/invalid-yaml-skill",
            artifact_type="skill",
            name="invalid-yaml-skill",
            path=str(invalid_yaml_skill_dir),
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is not None
        assert result.success is False
        assert result.reason_code == "yaml_parse_error"
        assert "Invalid YAML frontmatter" in result.error
        # Details should include line info
        assert result.details is not None

    def test_validate_github_source_skips_validation(self, importer):
        """GitHub sources skip local structure validation."""
        artifact = BulkImportArtifactData(
            source="anthropics/skills/canvas-design@latest",
            artifact_type="skill",
            name="canvas-design",
            path=None,  # No path for GitHub
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is None  # Validation skipped

    def test_validate_command_metadata_file(self, importer, tmp_path):
        """Command artifacts check for command.md."""
        command_dir = tmp_path / "test-command"
        command_dir.mkdir()
        # Missing command.md

        artifact = BulkImportArtifactData(
            source="local/command/test-command",
            artifact_type="command",
            name="test-command",
            path=str(command_dir),
        )

        result = importer._validate_artifact_structure(artifact)

        assert result is not None
        assert result.success is False
        assert result.reason_code == "missing_metadata"
        assert "command.md" in result.error


class TestBulkImportWithErrors:
    """Tests for bulk import with mixed valid/invalid artifacts."""

    @pytest.fixture
    def importer(self, tmp_path):
        """Create importer with mocked managers."""
        # Mock artifact manager
        artifact_mgr = Mock()
        mock_artifact = Mock()
        mock_artifact.name = "imported-skill"
        artifact_mgr.add_from_local.return_value = mock_artifact
        artifact_mgr.add_from_github.return_value = mock_artifact

        # Mock collection manager
        collection_mgr = Mock(spec=CollectionManager)
        mock_collection = Mock(spec=Collection)
        mock_collection.find_artifact.return_value = None
        collection_mgr.load_collection.return_value = mock_collection

        return ArtifactImporter(
            artifact_manager=artifact_mgr,
            collection_manager=collection_mgr,
        )

    @pytest.fixture
    def valid_skill_dir(self, tmp_path):
        """Create a valid skill directory."""
        skill_dir = tmp_path / "valid-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: valid-skill
description: A valid test skill
---

# Valid Skill
""")
        return skill_dir

    @pytest.fixture
    def invalid_yaml_dir(self, tmp_path):
        """Create skill with invalid YAML."""
        skill_dir = tmp_path / "invalid-yaml"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        # Invalid YAML: indentation error causes parse failure
        skill_md.write_text("""---
name: invalid-yaml
  indented: wrong
---
""")
        return skill_dir

    @pytest.fixture
    def missing_skill_md_dir(self, tmp_path):
        """Create skill without SKILL.md."""
        skill_dir = tmp_path / "missing-skill-md"
        skill_dir.mkdir()
        return skill_dir

    def test_bulk_import_all_valid(self, importer, valid_skill_dir):
        """Bulk import succeeds with all valid artifacts."""
        artifacts = [
            BulkImportArtifactData(
                source="local/skill/valid-skill",
                artifact_type="skill",
                name="valid-skill",
                path=str(valid_skill_dir),
            ),
        ]

        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)

        assert result.total_requested == 1
        assert result.total_imported == 1
        assert result.total_failed == 0

    def test_bulk_import_with_invalid_skipped(
        self, importer, valid_skill_dir, invalid_yaml_dir, missing_skill_md_dir
    ):
        """Invalid artifacts are skipped, valid ones imported."""
        artifacts = [
            BulkImportArtifactData(
                source="local/skill/valid-skill",
                artifact_type="skill",
                name="valid-skill",
                path=str(valid_skill_dir),
            ),
            BulkImportArtifactData(
                source="local/skill/invalid-yaml",
                artifact_type="skill",
                name="invalid-yaml",
                path=str(invalid_yaml_dir),
            ),
            BulkImportArtifactData(
                source="local/skill/missing-skill-md",
                artifact_type="skill",
                name="missing-skill-md",
                path=str(missing_skill_md_dir),
            ),
        ]

        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)

        # Should have 1 success, 2 failures
        assert result.total_requested == 3
        assert result.total_imported == 1
        assert result.total_failed == 2

        # Check that failures have reason codes
        failed_results = [r for r in result.results if not r.success]
        assert len(failed_results) == 2

        reason_codes = [r.reason_code for r in failed_results]
        assert "yaml_parse_error" in reason_codes
        assert "missing_metadata" in reason_codes

    def test_bulk_import_per_artifact_status(
        self, importer, valid_skill_dir, invalid_yaml_dir
    ):
        """Each artifact gets individual status."""
        artifacts = [
            BulkImportArtifactData(
                source="local/skill/valid-skill",
                artifact_type="skill",
                name="valid-skill",
                path=str(valid_skill_dir),
            ),
            BulkImportArtifactData(
                source="local/skill/invalid-yaml",
                artifact_type="skill",
                name="invalid-yaml",
                path=str(invalid_yaml_dir),
            ),
        ]

        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)

        assert len(result.results) == 2

        # Find results by path (more reliable than artifact_id since mock returns same name)
        valid_result = next(r for r in result.results if r.path and "valid-skill" in r.path)
        invalid_result = next(r for r in result.results if r.path and "invalid-yaml" in r.path)

        assert valid_result.success is True
        assert valid_result.status == ImportStatus.SUCCESS

        assert invalid_result.success is False
        assert invalid_result.status == ImportStatus.FAILED
        assert invalid_result.reason_code == "yaml_parse_error"

    def test_bulk_import_returns_200_with_partial_success(
        self, importer, valid_skill_dir, invalid_yaml_dir
    ):
        """Bulk import returns results (not raises) with mixed batch."""
        artifacts = [
            BulkImportArtifactData(
                source="local/skill/valid-skill",
                artifact_type="skill",
                name="valid-skill",
                path=str(valid_skill_dir),
            ),
            BulkImportArtifactData(
                source="local/skill/invalid-yaml",
                artifact_type="skill",
                name="invalid-yaml",
                path=str(invalid_yaml_dir),
            ),
        ]

        # Should not raise exception, should return result
        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)

        assert result is not None
        assert result.total_requested == 2
        assert result.total_imported == 1
        assert result.total_failed == 1

    def test_bulk_import_includes_path_in_results(
        self, importer, invalid_yaml_dir
    ):
        """Results include artifact path for debugging."""
        artifacts = [
            BulkImportArtifactData(
                source="local/skill/invalid-yaml",
                artifact_type="skill",
                name="invalid-yaml",
                path=str(invalid_yaml_dir),
            ),
        ]

        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)

        assert len(result.results) == 1
        assert result.results[0].path == str(invalid_yaml_dir)


class TestMixedBatchPerformance:
    """Tests for mixed batch processing (acceptance criteria)."""

    @pytest.fixture
    def importer(self, tmp_path):
        """Create importer with mocked managers."""
        artifact_mgr = Mock()
        mock_artifact = Mock()
        mock_artifact.name = "imported-skill"
        artifact_mgr.add_from_local.return_value = mock_artifact

        collection_mgr = Mock(spec=CollectionManager)
        mock_collection = Mock(spec=Collection)
        mock_collection.find_artifact.return_value = None
        collection_mgr.load_collection.return_value = mock_collection

        return ArtifactImporter(
            artifact_manager=artifact_mgr,
            collection_manager=collection_mgr,
        )

    @pytest.fixture
    def many_valid_skills(self, tmp_path):
        """Create 20 valid skill directories."""
        skills = []
        for i in range(20):
            skill_dir = tmp_path / f"valid-skill-{i}"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(f"""---
name: valid-skill-{i}
description: Valid test skill {i}
---

# Valid Skill {i}
""")
            skills.append(skill_dir)
        return skills

    @pytest.fixture
    def invalid_skills(self, tmp_path):
        """Create 3 invalid skill directories."""
        skills = []

        # Invalid YAML - indentation error causes parse error
        skill1 = tmp_path / "invalid-yaml-1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: value\n  indented: wrong\n---\n")
        skills.append(("invalid-yaml-1", skill1))

        # Missing SKILL.md
        skill2 = tmp_path / "missing-metadata"
        skill2.mkdir()
        skills.append(("missing-metadata", skill2))

        # Invalid YAML - mixing mapping and sequence
        skill3 = tmp_path / "invalid-yaml-2"
        skill3.mkdir()
        (skill3 / "SKILL.md").write_text("---\nkey: value\n- list item\n---\n")
        skills.append(("invalid-yaml-2", skill3))

        return skills

    def test_mixed_batch_20_valid_3_invalid(
        self, importer, many_valid_skills, invalid_skills
    ):
        """Integration test: 20 valid + 3 invalid -> 20 imported, 3 skipped."""
        artifacts = []

        # Add 20 valid skills
        for i, skill_dir in enumerate(many_valid_skills):
            artifacts.append(BulkImportArtifactData(
                source=f"local/skill/valid-skill-{i}",
                artifact_type="skill",
                name=f"valid-skill-{i}",
                path=str(skill_dir),
            ))

        # Add 3 invalid skills
        for name, skill_dir in invalid_skills:
            artifacts.append(BulkImportArtifactData(
                source=f"local/skill/{name}",
                artifact_type="skill",
                name=name,
                path=str(skill_dir),
            ))

        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)

        # Acceptance criteria
        assert result.total_requested == 23
        assert result.total_imported == 20
        assert result.total_failed == 3

        # Verify reason codes on failures
        failed_results = [r for r in result.results if not r.success]
        assert len(failed_results) == 3

        reason_codes = [r.reason_code for r in failed_results if r.reason_code]
        assert "yaml_parse_error" in reason_codes or "missing_metadata" in reason_codes

    def test_performance_20_artifacts_under_2_seconds(
        self, importer, many_valid_skills
    ):
        """Performance target: 20 artifacts processed in <2 seconds."""
        import time

        artifacts = [
            BulkImportArtifactData(
                source=f"local/skill/valid-skill-{i}",
                artifact_type="skill",
                name=f"valid-skill-{i}",
                path=str(skill_dir),
            )
            for i, skill_dir in enumerate(many_valid_skills)
        ]

        start = time.time()
        result = importer.bulk_import(artifacts, "default", auto_resolve_conflicts=True)
        elapsed = time.time() - start

        # Acceptance criteria: < 2 seconds
        assert elapsed < 2.0, f"Bulk import took {elapsed:.2f}s, expected < 2s"
        assert result.duration_ms < 2000
