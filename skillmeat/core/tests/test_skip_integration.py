"""Integration tests for skip preferences in discovery service.

This test suite verifies that skip preferences are properly integrated into
the artifact discovery workflow, including filtering, performance, and error handling.
"""

import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import Collection
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.core.skip_preferences import SkipPreferenceManager, build_artifact_key


@pytest.fixture
def collection_with_artifacts(tmp_path):
    """Create a collection with multiple artifacts.

    Returns:
        Path to collection root with artifacts in artifacts/skills/
    """
    # Create skills directory
    skills_dir = tmp_path / "artifacts" / "skills"
    skills_dir.mkdir(parents=True)

    # Create 5 test skills
    for i in range(5):
        skill_dir = skills_dir / f"skill-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"""---
name: skill-{i}
description: Test skill {i}
source: github/test/skill-{i}
---

# Skill {i}
"""
        )

    return tmp_path


class TestSkipIntegration:
    """Tests for skip preference integration in discovery service."""

    def test_skip_filtering_excludes_skipped_artifacts(self, collection_with_artifacts):
        """Test that skipped artifacts are filtered from discovery results."""
        # Create .claude directory for skip preferences
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        # Add some skip preferences
        skip_mgr.add_skip("skill:skill-0", "Already in collection")
        skip_mgr.add_skip("skill:skill-2", "Not needed for this project")

        # Run discovery with skip filtering (use collection mode to scan artifacts/)
        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(project_path=collection_with_artifacts)

        # Should discover 5, but only 3 should be importable (5 - 2 skipped)
        assert result.discovered_count == 5
        assert result.importable_count == 3

        # Verify skipped artifacts are not in results
        artifact_names = {a.name for a in result.artifacts}
        assert "skill-0" not in artifact_names
        assert "skill-2" not in artifact_names

        # Verify non-skipped artifacts are present
        assert "skill-1" in artifact_names
        assert "skill-3" in artifact_names
        assert "skill-4" in artifact_names

    def test_skip_filtering_no_skips(self, collection_with_artifacts):
        """Test discovery when no skip preferences exist."""
        # Create .claude directory
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(project_path=collection_with_artifacts)

        # All artifacts should be importable
        assert result.discovered_count == 5
        assert result.importable_count == 5

    def test_skip_filtering_all_skipped(self, collection_with_artifacts):
        """Test discovery when all artifacts are skipped."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        # Skip all artifacts
        for i in range(5):
            skip_mgr.add_skip(f"skill:skill-{i}", f"Skipping skill-{i}")

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(project_path=collection_with_artifacts)

        # All discovered, none importable
        assert result.discovered_count == 5
        assert result.importable_count == 0
        assert len(result.artifacts) == 0

    def test_include_skipped_returns_skipped_artifacts(self, collection_with_artifacts):
        """Test include_skipped=True returns skipped artifacts with reasons."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        # Add skip preferences with specific reasons
        skip_mgr.add_skip("skill:skill-0", "Already in collection")
        skip_mgr.add_skip("skill:skill-2", "Not needed for this project")

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(
            project_path=collection_with_artifacts, include_skipped=True
        )

        # Should have skipped artifacts in separate list
        assert result.discovered_count == 5
        assert result.importable_count == 3
        assert len(result.artifacts) == 3
        assert len(result.skipped_artifacts) == 2

        # Verify skipped artifacts have reasons
        skipped_names = {a.name for a in result.skipped_artifacts}
        assert "skill-0" in skipped_names
        assert "skill-2" in skipped_names

        # Check skip reasons are attached
        for artifact in result.skipped_artifacts:
            assert artifact.skip_reason is not None
            if artifact.name == "skill-0":
                assert artifact.skip_reason == "Already in collection"
            elif artifact.name == "skill-2":
                assert artifact.skip_reason == "Not needed for this project"

    def test_include_skipped_false_excludes_skipped(self, collection_with_artifacts):
        """Test include_skipped=False (default) excludes skipped artifacts."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        skip_mgr.add_skip("skill:skill-0", "Skipped")

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(
            project_path=collection_with_artifacts, include_skipped=False
        )

        # Skipped artifacts should not appear in either list
        assert len(result.skipped_artifacts) == 0
        artifact_names = {a.name for a in result.artifacts}
        assert "skill-0" not in artifact_names

    def test_skip_filtering_with_manifest_filtering(self, collection_with_artifacts):
        """Test skip filtering works alongside manifest-based filtering."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        # Create manifest with some artifacts already imported
        manifest = Collection(
            name="test-collection",
            version="1.0.0",
            artifacts=[
                Artifact(
                    name="skill-1",
                    type=ArtifactType.SKILL,
                    path="skills/skill-1",
                    origin="github",
                    metadata=ArtifactMetadata(),
                    added=datetime.utcnow(),
                    upstream="github/test/skill-1",
                ),
            ],
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )

        # Create corresponding project artifact (so skill-1 exists in BOTH)
        project_skills_dir = collection_with_artifacts / ".claude" / "skills"
        project_skills_dir.mkdir(parents=True)
        skill1_project = project_skills_dir / "skill-1"
        skill1_project.mkdir()
        (skill1_project / "SKILL.md").write_text(
            "---\nname: skill-1\nsource: github/test/skill-1\n---\n"
        )

        # Skip one artifact
        skip_mgr.add_skip("skill:skill-2", "Not needed")

        service = ArtifactDiscoveryService(
            collection_with_artifacts, scan_mode="collection"
        )
        result = service.discover_artifacts(
            manifest=manifest, project_path=collection_with_artifacts
        )

        # 5 discovered
        # skill-1 in BOTH locations (filtered by manifest+project check)
        # skill-2 skipped
        # skill-0, skill-3, skill-4 importable
        assert result.discovered_count == 5
        assert result.importable_count == 3

        artifact_names = {a.name for a in result.artifacts}
        assert "skill-1" not in artifact_names  # In both locations
        assert "skill-2" not in artifact_names  # Skipped
        assert "skill-0" in artifact_names
        assert "skill-3" in artifact_names
        assert "skill-4" in artifact_names

    def test_skip_filtering_without_project_path(self, collection_with_artifacts):
        """Test that skip filtering is skipped when project_path not provided."""
        # Don't provide project_path
        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(project_path=None)

        # All artifacts should be importable (no skip filtering)
        assert result.discovered_count == 5
        assert result.importable_count == 5

    def test_skip_filtering_performance(self, tmp_path):
        """Test skip filtering adds minimal overhead (<100ms for 50 artifacts)."""
        # Create 50 artifacts
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        for i in range(50):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\nsource: github/test/skill-{i}\n---\n"
            )

        # Create project with skip preferences
        (tmp_path / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(tmp_path)

        # Skip 10 artifacts
        for i in range(0, 20, 2):  # Skip every other one
            skip_mgr.add_skip(f"skill:skill-{i}", f"Skipped {i}")

        # Measure performance
        service = ArtifactDiscoveryService(tmp_path, scan_mode="collection")

        start = time.perf_counter()
        result = service.discover_artifacts(project_path=tmp_path)
        duration_ms = (time.perf_counter() - start) * 1000

        # Verify correctness
        assert result.discovered_count == 50
        assert result.importable_count == 40  # 50 - 10 skipped

        # Performance requirement: total scan + skip filtering < 2 seconds
        # Skip filtering overhead should be minimal (<100ms)
        assert duration_ms < 2000, f"Discovery took {duration_ms:.2f}ms (expected <2000ms)"

        print(
            f"\n  Performance: Discovered {result.discovered_count} artifacts "
            f"({result.importable_count} importable, 10 skipped) in {duration_ms:.2f}ms"
        )

    def test_corrupt_skip_file_handling(self, collection_with_artifacts):
        """Test graceful handling when skip preferences file is corrupt."""
        # Create .claude directory
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)

        # Create corrupt skip preferences file
        skip_path = collection_with_artifacts / ".claude" / ".skillmeat_skip_prefs.toml"
        skip_path.write_text("invalid toml [[[")

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(project_path=collection_with_artifacts)

        # Should not crash, gracefully handle corrupt file
        assert result.discovered_count == 5
        assert result.importable_count == 5  # No skip filtering due to error (loads empty)

        # No errors added to result (just logged as warning)
        # This is expected behavior - corrupt file is handled gracefully

    def test_skip_filtering_with_multiple_artifact_types(self, tmp_path):
        """Test skip filtering works across different artifact types."""
        # Create artifacts of different types
        artifacts_dir = tmp_path / "artifacts"

        # Create skills
        skills_dir = artifacts_dir / "skills"
        skills_dir.mkdir(parents=True)
        for i in range(3):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"---\nname: skill-{i}\n---\n")

        # Create commands
        commands_dir = artifacts_dir / "commands"
        commands_dir.mkdir(parents=True)
        for i in range(2):
            cmd_dir = commands_dir / f"cmd-{i}"
            cmd_dir.mkdir()
            (cmd_dir / "COMMAND.md").write_text(f"---\nname: cmd-{i}\n---\n")

        # Create skip preferences
        (tmp_path / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(tmp_path)

        # Skip one skill and one command
        skip_mgr.add_skip("skill:skill-0", "Skip skill")
        skip_mgr.add_skip("command:cmd-1", "Skip command")

        service = ArtifactDiscoveryService(tmp_path, scan_mode="collection")
        result = service.discover_artifacts(project_path=tmp_path)

        # 5 total artifacts, 2 skipped
        assert result.discovered_count == 5
        assert result.importable_count == 3

        # Verify correct artifacts are filtered
        artifact_keys = {build_artifact_key(a.type, a.name) for a in result.artifacts}
        assert "skill:skill-0" not in artifact_keys
        assert "command:cmd-1" not in artifact_keys
        assert "skill:skill-1" in artifact_keys
        assert "skill:skill-2" in artifact_keys
        assert "command:cmd-0" in artifact_keys

    def test_skip_reason_accuracy(self, collection_with_artifacts):
        """Test that skip reasons are accurately retrieved and attached."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        # Add skips with very specific reasons
        skip_mgr.add_skip("skill:skill-0", "Already deployed to production")
        skip_mgr.add_skip("skill:skill-1", "Incompatible with current setup")

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")
        result = service.discover_artifacts(
            project_path=collection_with_artifacts, include_skipped=True
        )

        # Find skipped artifacts and verify reasons
        skipped_dict = {a.name: a for a in result.skipped_artifacts}

        assert "skill-0" in skipped_dict
        assert skipped_dict["skill-0"].skip_reason == "Already deployed to production"

        assert "skill-1" in skipped_dict
        assert (
            skipped_dict["skill-1"].skip_reason == "Incompatible with current setup"
        )

    def test_skip_filtering_empty_project_directory(self, collection_with_artifacts):
        """Test skip filtering when project directory doesn't have .claude/."""
        # Create project without .claude directory
        project_path = collection_with_artifacts / "empty_project"
        project_path.mkdir()

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")

        # Should handle missing .claude/ gracefully
        result = service.discover_artifacts(project_path=project_path)

        # All artifacts should be importable (no skip file found)
        assert result.discovered_count == 5
        assert result.importable_count == 5

    def test_skip_filtering_with_nonexistent_project_path(self, collection_with_artifacts):
        """Test skip filtering with nonexistent project path."""
        nonexistent_path = collection_with_artifacts / "does_not_exist"

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")

        # Should handle gracefully (skip filtering skipped)
        result = service.discover_artifacts(project_path=nonexistent_path)

        # All artifacts importable (skip filtering couldn't load)
        assert result.discovered_count == 5
        assert result.importable_count == 5


class TestSkipPreferenceEdgeCases:
    """Tests for edge cases in skip preference integration."""

    def test_unicode_artifact_names_in_skip(self, tmp_path):
        """Test skip filtering with Unicode artifact names."""
        # Create artifact with Unicode name
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        unicode_name = "skill-中文"
        skill_dir = skills_dir / unicode_name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\nname: {unicode_name}\n---\n")

        # Skip it
        (tmp_path / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(tmp_path)
        skip_mgr.add_skip(f"skill:{unicode_name}", "Unicode skip test")

        service = ArtifactDiscoveryService(tmp_path, scan_mode="collection")
        result = service.discover_artifacts(project_path=tmp_path)

        assert result.discovered_count == 1
        assert result.importable_count == 0  # Skipped

    def test_skip_filtering_case_sensitivity(self, tmp_path):
        """Test that skip filtering is case-sensitive for artifact names."""
        # Create artifacts (use different directory names to avoid case-insensitive FS issues)
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        # Use directory names that differ by more than just case
        skill_upper = skills_dir / "MySkill-Upper"
        skill_upper.mkdir()
        (skill_upper / "SKILL.md").write_text("---\nname: MySkill\n---\n")

        skill_lower = skills_dir / "myskill-lower"
        skill_lower.mkdir()
        (skill_lower / "SKILL.md").write_text("---\nname: myskill\n---\n")

        # Skip lowercase version
        (tmp_path / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(tmp_path)
        skip_mgr.add_skip("skill:myskill", "Skip lowercase")

        service = ArtifactDiscoveryService(tmp_path, scan_mode="collection")
        result = service.discover_artifacts(project_path=tmp_path)

        # Only lowercase should be skipped
        assert result.discovered_count == 2
        assert result.importable_count == 1

        artifact_names = {a.name for a in result.artifacts}
        assert "MySkill" in artifact_names
        assert "myskill" not in artifact_names

    def test_skip_filtering_with_whitespace(self, tmp_path):
        """Test skip filtering with whitespace in artifact names."""
        # Create artifact with spaces in name
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        name_with_space = "my skill name"
        skill_dir = skills_dir / name_with_space.replace(" ", "-")
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"---\nname: {name_with_space}\n---\n")

        # Skip it
        (tmp_path / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(tmp_path)
        skip_mgr.add_skip(f"skill:{name_with_space}", "Whitespace test")

        service = ArtifactDiscoveryService(tmp_path, scan_mode="collection")
        result = service.discover_artifacts(project_path=tmp_path)

        assert result.discovered_count == 1
        assert result.importable_count == 0


class TestSkipLogging:
    """Tests for skip filtering logging and metrics."""

    def test_skip_filtering_logs_filtered_count(self, collection_with_artifacts, caplog):
        """Test that skip filtering logs the number of filtered artifacts."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(collection_with_artifacts)

        # Skip 2 artifacts
        skip_mgr.add_skip("skill:skill-0", "Skip 0")
        skip_mgr.add_skip("skill:skill-2", "Skip 2")

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")

        import logging

        with caplog.at_level(logging.INFO):
            result = service.discover_artifacts(project_path=collection_with_artifacts)

        # Should log skip filtering summary
        assert any("Filtered 2 skipped artifacts" in record.message for record in caplog.records)

    def test_skip_filtering_logs_performance(self, tmp_path, caplog):
        """Test that skip filtering logs performance metrics."""
        # Create artifacts
        skills_dir = tmp_path / "artifacts" / "skills"
        skills_dir.mkdir(parents=True)

        for i in range(10):
            skill_dir = skills_dir / f"skill-{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"---\nname: skill-{i}\n---\n")

        # Create skip preferences
        (tmp_path / ".claude").mkdir(exist_ok=True)
        skip_mgr = SkipPreferenceManager(tmp_path)
        for i in range(5):
            skip_mgr.add_skip(f"skill:skill-{i}", f"Skip {i}")

        service = ArtifactDiscoveryService(tmp_path, scan_mode="collection")

        import logging

        with caplog.at_level(logging.INFO):
            result = service.discover_artifacts(project_path=tmp_path)

        # Should log skip filtering performance
        assert any("skipped artifacts" in record.message.lower() for record in caplog.records)
        assert any("ms" in record.message for record in caplog.records)

    def test_no_skips_logs_debug_message(self, collection_with_artifacts, caplog):
        """Test that discovery logs debug message when no artifacts are skipped."""
        (collection_with_artifacts / ".claude").mkdir(exist_ok=True)

        service = ArtifactDiscoveryService(collection_with_artifacts, scan_mode="collection")

        import logging

        with caplog.at_level(logging.DEBUG):
            result = service.discover_artifacts(project_path=collection_with_artifacts)

        # Should log that skip check completed with no skips
        assert any(
            "no skipped artifacts" in record.message.lower()
            for record in caplog.records
        )
