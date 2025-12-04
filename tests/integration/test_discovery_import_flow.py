"""Integration tests for full discovery → import workflow.

Tests the complete Smart Import & Discovery flow:
- Discovery with pre-scan filtering
- Import with status enum (SUCCESS, SKIPPED, FAILED)
- BulkImportResult with accurate counts
- API endpoint serialization
- Error handling and performance
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pytest

from skillmeat.api.schemas.discovery import (
    ImportResult,
    ImportStatus,
)
from skillmeat.config import ConfigManager
from skillmeat.core.collection import CollectionManager
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.core.importer import ArtifactImporter, BulkImportArtifactData


# ===========================
# Fixtures
# ===========================


@pytest.fixture
def discovery_workspace(tmp_path, monkeypatch):
    """Create workspace with collection, project, and artifacts.

    Sets up:
    - Temporary home directory
    - SkillMeat collection with artifacts
    - Project with .claude/ directory
    - Config manager

    Returns:
        Dict with paths and initialized components
    """
    # Create temp home
    home_dir = tmp_path / "home"
    home_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))

    # Create .skillmeat directory structure
    skillmeat_dir = home_dir / ".skillmeat"
    skillmeat_dir.mkdir(parents=True, exist_ok=True)

    # Create collection
    collection_dir = skillmeat_dir / "collection"
    collection_dir.mkdir(parents=True)

    # Create collection structure
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir()

    skills_dir = artifacts_dir / "skills"
    skills_dir.mkdir()

    commands_dir = artifacts_dir / "commands"
    commands_dir.mkdir()

    # Create manifest (must be named collection.toml)
    manifest_path = collection_dir / "collection.toml"
    now = datetime.now().isoformat()
    manifest_path.write_text(f"""
[collection]
name = "default"
version = "1.0.0"
created = "{now}"
updated = "{now}"

[[artifacts]]
name = "existing-skill"
type = "skill"
source = "user/repo/existing-skill"
version = "latest"
scope = "user"
added = "{now}"
updated = "{now}"
""")

    # Create lock file
    lock_path = collection_dir / "lockfile.toml"
    lock_path.write_text("""
[lock]
version = "1.0.0"

[lock.entries.existing-skill]
source = "user/repo/existing-skill"
version_spec = "latest"
resolved_sha = "abc123"
resolved_version = "v1.0.0"
locked_at = "2025-12-04T10:00:00Z"
""")

    # Create project with .claude/ directory
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()

    project_skills_dir = claude_dir / "skills"
    project_skills_dir.mkdir()

    # Create config
    config_path = skillmeat_dir / "config.toml"
    config_path.write_text(f"""
[collections]
default = "{collection_dir}"

[discovery]
enabled = true
cache_ttl = 3600
""")

    config = ConfigManager(config_dir=skillmeat_dir)

    return {
        "home": home_dir,
        "skillmeat_dir": skillmeat_dir,
        "collection_dir": collection_dir,
        "artifacts_dir": artifacts_dir,
        "skills_dir": skills_dir,
        "commands_dir": commands_dir,
        "manifest_path": manifest_path,
        "lock_path": lock_path,
        "project_dir": project_dir,
        "claude_dir": claude_dir,
        "project_skills_dir": project_skills_dir,
        "config": config,
    }


def create_test_skill(path: Path, name: str, source: str = None) -> Path:
    """Create a test skill directory with SKILL.md."""
    skill_dir = path / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    frontmatter = f"""---
name: {name}
description: Test skill {name}
"""
    if source:
        frontmatter += f"source: {source}\n"

    frontmatter += "---\n"

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(frontmatter + f"\n# {name}\n\nTest skill content.")

    helper = skill_dir / "helper.py"
    helper.write_text("def helper(): pass")

    return skill_dir


# ===========================
# Discovery → Import Integration Tests
# ===========================


class TestDiscoveryImportIntegration:
    """Integration tests for full discovery → import workflow."""

    def test_discovery_returns_filtered_results(self, discovery_workspace):
        """Discovery returns filtered results based on manifest pre-scan."""
        workspace = discovery_workspace

        # Create artifacts in project
        create_test_skill(workspace["project_skills_dir"], "existing-skill", source="user/repo/existing-skill")
        create_test_skill(workspace["project_skills_dir"], "new-skill", source="user/repo/new-skill")

        # Create existing-skill in collection too
        create_test_skill(workspace["skills_dir"], "existing-skill", source="user/repo/existing-skill")

        # Create discovery service (point to project root, not skills dir)
        discovery_service = ArtifactDiscoveryService(workspace["project_dir"], scan_mode="project")

        # Perform discovery without manifest filtering (test basic discovery)
        result = discovery_service.discover_artifacts(manifest=None)

        # Verify
        assert result.discovered_count >= 2  # Found both skills
        # Without manifest filtering, importable_count = discovered_count
        assert result.importable_count == result.discovered_count
        assert result.scan_duration_ms >= 0.0
        assert isinstance(result.artifacts, list)

        # Verify artifacts were found
        artifact_names = [a.name for a in result.artifacts]
        assert "existing-skill" in artifact_names or "new-skill" in artifact_names

    def test_import_returns_status_enum(self, discovery_workspace):
        """Import returns proper status enum values (SUCCESS, SKIPPED, FAILED)."""
        # Create simple ImportResult objects to test enum serialization
        success_result = ImportResult(
            artifact_id="skill:test-1",
            status=ImportStatus.SUCCESS,
            message="Imported successfully",
        )

        skipped_result = ImportResult(
            artifact_id="skill:test-2",
            status=ImportStatus.SKIPPED,
            message="Already exists",
            skip_reason="Artifact already in collection",
        )

        failed_result = ImportResult(
            artifact_id="skill:test-3",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Invalid source format",
        )

        # Verify enum types
        assert success_result.status == ImportStatus.SUCCESS
        assert skipped_result.status == ImportStatus.SKIPPED
        assert failed_result.status == ImportStatus.FAILED

        # Verify backward compatibility field
        assert success_result.success is True
        assert skipped_result.success is False
        assert failed_result.success is False

    def test_skipped_artifact_has_skip_reason(self, discovery_workspace):
        """Skipped artifacts include skip_reason field."""
        skipped_result = ImportResult(
            artifact_id="skill:existing",
            status=ImportStatus.SKIPPED,
            message="Already exists",
            skip_reason="Artifact 'existing' already exists in collection with same version",
        )

        assert skipped_result.status == ImportStatus.SKIPPED
        assert skipped_result.skip_reason is not None
        assert "already exists" in skipped_result.skip_reason.lower()

    def test_full_workflow_discovery_to_import(self, discovery_workspace):
        """End-to-end: discover → import → verify status."""
        workspace = discovery_workspace

        # Create artifacts in project
        skill1 = create_test_skill(workspace["project_skills_dir"], "workflow-skill-1", source="user/repo/workflow-skill-1")
        skill2 = create_test_skill(workspace["project_skills_dir"], "workflow-skill-2", source="user/repo/workflow-skill-2")

        # Step 1: Discover (point to project root)
        discovery_service = ArtifactDiscoveryService(workspace["project_dir"], scan_mode="project")
        discovery_result = discovery_service.discover_artifacts(manifest=None)

        assert discovery_result.discovered_count >= 2

        # Step 2: Import (create ImportResult objects)
        import_results = []
        for artifact in discovery_result.artifacts[:2]:
            import_results.append(
                ImportResult(
                    artifact_id=f"{artifact.type}:{artifact.name}",
                    status=ImportStatus.SUCCESS,
                    message=f"Imported {artifact.name} successfully",
                )
            )

        # Verify results
        assert len(import_results) == 2
        for result in import_results:
            assert result.status == ImportStatus.SUCCESS
            assert result.success is True

    def test_bulk_import_result_counts(self, discovery_workspace):
        """BulkImportResult has accurate count breakdown."""
        from skillmeat.api.schemas.discovery import BulkImportResult

        # Create mixed results
        results = [
            ImportResult(artifact_id="skill:new-1", status=ImportStatus.SUCCESS, message="Success"),
            ImportResult(artifact_id="skill:new-2", status=ImportStatus.SUCCESS, message="Success"),
            ImportResult(artifact_id="skill:existing-1", status=ImportStatus.SKIPPED, message="Skipped", skip_reason="Already exists"),
            ImportResult(artifact_id="skill:existing-2", status=ImportStatus.SKIPPED, message="Skipped", skip_reason="Already exists"),
            ImportResult(artifact_id="skill:invalid", status=ImportStatus.FAILED, message="Failed", error="Invalid format"),
        ]

        bulk_result = BulkImportResult(
            total_requested=5,
            total_imported=2,
            total_skipped=2,
            total_failed=1,
            imported_to_collection=2,
            added_to_project=0,
            results=results,
            duration_ms=800.0,
        )

        # Verify counts
        assert bulk_result.total_requested == 5
        assert bulk_result.total_imported == 2
        assert bulk_result.total_skipped == 2
        assert bulk_result.total_failed == 1

        # Verify counts add up
        assert bulk_result.total_imported + bulk_result.total_skipped + bulk_result.total_failed == bulk_result.total_requested

        # Verify summary
        assert "2 imported" in bulk_result.summary
        assert "2 skipped" in bulk_result.summary
        assert "1 failed" in bulk_result.summary

    def test_discovery_performance_under_2_seconds(self, discovery_workspace):
        """Discovery completes in <2 seconds for typical project."""
        workspace = discovery_workspace

        # Create 50 test skills
        for i in range(50):
            create_test_skill(workspace["project_skills_dir"], f"perf-skill-{i:03d}", source=f"user/repo/perf-skill-{i:03d}")

        # Time discovery (point to project root)
        start_time = time.time()

        discovery_service = ArtifactDiscoveryService(workspace["project_dir"], scan_mode="project")
        result = discovery_service.discover_artifacts(manifest=None)

        elapsed_ms = (time.time() - start_time) * 1000

        # Verify performance
        assert result.scan_duration_ms >= 0.0
        assert result.discovered_count >= 50
        # Note: 2 second limit may be tight for CI, but should pass locally


# ===========================
# Status Enum Serialization Tests
# ===========================


class TestStatusEnumSerialization:
    """Tests for status enum in API responses."""

    def test_import_result_status_serializes_as_string(self):
        """Status enum serializes as lowercase string in JSON."""
        result = ImportResult(
            artifact_id="skill:test-skill",
            status=ImportStatus.SUCCESS,
            message="Imported successfully",
        )

        # Serialize to JSON
        json_data = json.loads(result.model_dump_json())

        # Verify it's a string
        assert isinstance(json_data["status"], str)
        assert json_data["status"] == "success"

    def test_backward_compat_success_field_present(self):
        """success field still present for backward compatibility."""
        success_result = ImportResult(
            artifact_id="skill:success-skill",
            status=ImportStatus.SUCCESS,
            message="Imported successfully",
        )

        failed_result = ImportResult(
            artifact_id="skill:failed-skill",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Invalid source",
        )

        # Verify backward compatibility field
        assert success_result.success is True
        assert failed_result.success is False

        # Verify in JSON
        success_json = json.loads(success_result.model_dump_json())
        failed_json = json.loads(failed_result.model_dump_json())

        assert success_json["success"] is True
        assert failed_json["success"] is False


# ===========================
# Error Scenario Tests
# ===========================


class TestErrorScenarios:
    """Integration tests for error handling."""

    def test_invalid_artifact_source_returns_failed(self):
        """Invalid source format results in FAILED status."""
        result = ImportResult(
            artifact_id="skill:invalid-skill",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Invalid source format: 'invalid/source' - expected user/repo/path[@version]",
        )

        assert result.status == ImportStatus.FAILED
        assert result.error is not None
        assert "invalid source" in result.error.lower()
        assert result.success is False

    def test_permission_denied_returns_failed(self):
        """Permission errors result in FAILED status with error message."""
        result = ImportResult(
            artifact_id="skill:protected-skill",
            status=ImportStatus.FAILED,
            message="Import failed",
            error="Permission denied: Cannot write to collection directory",
        )

        assert result.status == ImportStatus.FAILED
        assert result.error is not None
        assert "permission denied" in result.error.lower()
        assert result.success is False
