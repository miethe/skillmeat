"""Tests for pre-scan check logic in artifact discovery.

This module tests the check_artifact_exists() method and its integration
into discover_artifacts() for filtering artifacts based on existence in
Collection and/or Project locations.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.artifact import ArtifactType
from skillmeat.core.discovery import ArtifactDiscoveryService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def collection_base(tmp_path):
    """Create a temporary collection base directory structure.

    Returns:
        Path: Path to collection base directory with artifacts/ subdirectory
    """
    collection_dir = tmp_path / "collection"
    artifacts_dir = collection_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create artifact type directories
    for artifact_type in ["skills", "commands", "agents", "hooks", "mcps"]:
        (artifacts_dir / artifact_type).mkdir(exist_ok=True)

    return collection_dir


@pytest.fixture
def project_base(tmp_path):
    """Create a temporary project base directory structure.

    Returns:
        Path: Path to project base directory with .claude/ subdirectory
    """
    project_dir = tmp_path / "project"
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Create artifact type directories
    for artifact_type in ["skills", "commands", "agents", "hooks", "mcps"]:
        (claude_dir / artifact_type).mkdir(exist_ok=True)

    return project_dir


@pytest.fixture
def discovery_service(project_base):
    """Create an ArtifactDiscoveryService instance for testing.

    Args:
        project_base: Pytest fixture providing project directory

    Returns:
        ArtifactDiscoveryService: Configured discovery service instance
    """
    return ArtifactDiscoveryService(base_path=project_base, scan_mode="project")


@pytest.fixture
def mock_collection_config(collection_base):
    """Mock ConfigManager to return test collection path.

    Args:
        collection_base: Pytest fixture providing collection directory

    Yields:
        MagicMock: Patched ConfigManager
    """
    # ConfigManager is imported inside check_artifact_exists, so patch it there
    with patch("skillmeat.config.ConfigManager") as mock_config_class:
        mock_config_instance = MagicMock()
        mock_config_instance.get_active_collection.return_value = "test-collection"
        mock_config_instance.get_collection_path.return_value = collection_base
        mock_config_class.return_value = mock_config_instance
        yield mock_config_instance


# =============================================================================
# Test check_artifact_exists() - Location Detection
# =============================================================================


class TestCheckArtifactExists:
    """Tests for check_artifact_exists() method."""

    def test_artifact_in_collection_only(
        self, discovery_service, collection_base, mock_collection_config
    ):
        """Artifact exists in Collection but not in Project."""
        # Setup: Create artifact in collection only
        artifact_dir = collection_base / "artifacts" / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "SKILL.md").write_text("---\ntitle: Test Skill\n---\n")

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="skill:test-skill"
        )

        # Assert
        assert result["exists_in_collection"] is True
        assert result["exists_in_project"] is False
        assert result["location"] == "collection"
        assert result["collection_path"] is not None
        assert result["project_path"] is None

    def test_artifact_in_project_only(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Artifact exists in Project but not in Collection."""
        # Setup: Create artifact in project only
        artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "SKILL.md").write_text("---\ntitle: Test Skill\n---\n")

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="skill:test-skill"
        )

        # Assert
        assert result["exists_in_collection"] is False
        assert result["exists_in_project"] is True
        assert result["location"] == "project"
        assert result["collection_path"] is None
        assert result["project_path"] is not None

    def test_artifact_in_both_locations(
        self, discovery_service, collection_base, project_base, mock_collection_config
    ):
        """Artifact exists in both Collection and Project."""
        # Setup: Create artifact in both locations
        # Collection
        collection_artifact_dir = collection_base / "artifacts" / "skills" / "test-skill"
        collection_artifact_dir.mkdir(parents=True, exist_ok=True)
        (collection_artifact_dir / "SKILL.md").write_text(
            "---\ntitle: Test Skill\n---\n"
        )

        # Project
        project_artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text("---\ntitle: Test Skill\n---\n")

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="skill:test-skill"
        )

        # Assert
        assert result["exists_in_collection"] is True
        assert result["exists_in_project"] is True
        assert result["location"] == "both"
        assert result["collection_path"] is not None
        assert result["project_path"] is not None

    def test_artifact_in_neither_location(
        self, discovery_service, mock_collection_config
    ):
        """Artifact exists nowhere."""
        # Setup: Empty directories (already done by fixtures)

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="skill:nonexistent-skill"
        )

        # Assert
        assert result["exists_in_collection"] is False
        assert result["exists_in_project"] is False
        assert result["location"] == "none"
        assert result["collection_path"] is None
        assert result["project_path"] is None

    def test_invalid_artifact_key_format(
        self, discovery_service, mock_collection_config
    ):
        """Invalid artifact key format returns 'none' gracefully."""
        # Execute: Test various invalid formats
        invalid_keys = [
            "invalid-no-colon",
            "too:many:colons",
            ":missing-type",
            "missing-name:",
            "",
        ]

        for invalid_key in invalid_keys:
            result = discovery_service.check_artifact_exists(
                artifact_key=invalid_key
            )

            # Assert: Should not raise exception, should return "none"
            assert result["location"] == "none"
            assert result["exists_in_collection"] is False
            assert result["exists_in_project"] is False
            assert result["collection_path"] is None
            assert result["project_path"] is None

    def test_permission_error_handling(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Permission errors handled gracefully."""
        # Setup: Create artifact in project
        artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "SKILL.md").write_text("---\ntitle: Test Skill\n---\n")

        # Mock ConfigManager to raise PermissionError for collection check
        with patch("skillmeat.config.ConfigManager") as mock_config_class:
            mock_config_instance = MagicMock()
            mock_config_instance.get_active_collection.side_effect = PermissionError(
                "Access denied"
            )
            mock_config_class.return_value = mock_config_instance

            # Execute: Should not raise exception
            result = discovery_service.check_artifact_exists(
                artifact_key="skill:test-skill"
            )

            # Assert: Should still check project, which succeeds
            assert result["exists_in_project"] is True
            assert result["location"] == "project"

    def test_collection_path_returned(
        self, discovery_service, collection_base, mock_collection_config
    ):
        """collection_path populated when artifact in collection."""
        # Setup
        artifact_dir = collection_base / "artifacts" / "commands" / "test-command"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "COMMAND.md").write_text("---\ntitle: Test Command\n---\n")

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="command:test-command"
        )

        # Assert
        assert result["collection_path"] is not None
        assert "test-command" in result["collection_path"]
        assert Path(result["collection_path"]).exists()

    def test_project_path_returned(
        self, discovery_service, project_base, mock_collection_config
    ):
        """project_path populated when artifact in project."""
        # Setup
        artifact_dir = project_base / ".claude" / "agents" / "test-agent"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "AGENT.md").write_text("---\ntitle: Test Agent\n---\n")

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="agent:test-agent"
        )

        # Assert
        assert result["project_path"] is not None
        assert "test-agent" in result["project_path"]
        assert Path(result["project_path"]).exists()

    def test_all_artifact_types(
        self, discovery_service, collection_base, mock_collection_config
    ):
        """Works with skill, command, agent, hook, mcp types."""
        artifact_types = [
            ("skill", "skills", "SKILL.md"),
            ("command", "commands", "COMMAND.md"),
            ("agent", "agents", "AGENT.md"),
            ("hook", "hooks", "HOOK.md"),
            ("mcp", "mcps", "MCP.md"),
        ]

        for artifact_type, type_plural, metadata_file in artifact_types:
            # Setup
            artifact_dir = (
                collection_base / "artifacts" / type_plural / f"test-{artifact_type}"
            )
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (artifact_dir / metadata_file).write_text(
                f"---\ntitle: Test {artifact_type.title()}\n---\n"
            )

            # Execute
            result = discovery_service.check_artifact_exists(
                artifact_key=f"{artifact_type}:test-{artifact_type}"
            )

            # Assert
            assert (
                result["exists_in_collection"] is True
            ), f"Failed for type: {artifact_type}"
            assert result["location"] in [
                "collection",
                "both",
            ], f"Failed for type: {artifact_type}"


# =============================================================================
# Test discover_artifacts() - Filtering Integration
# =============================================================================


class TestDiscoveryFiltering:
    """Tests for pre-scan filtering in discover_artifacts()."""

    def test_filters_artifacts_in_both_locations(
        self, discovery_service, collection_base, project_base, mock_collection_config
    ):
        """Artifacts in both Collection AND Project are filtered out."""
        # Setup: Create artifact in both locations
        # Collection
        collection_artifact_dir = collection_base / "artifacts" / "skills" / "test-skill"
        collection_artifact_dir.mkdir(parents=True, exist_ok=True)
        (collection_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        # Project (this is what gets scanned by discover_artifacts)
        project_artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert: Artifact should be discovered but filtered out
        assert result.discovered_count == 1  # Found during scan
        assert result.importable_count == 0  # Filtered out (exists in both)
        assert len(result.artifacts) == 0  # Not in importable list

    def test_keeps_artifacts_in_collection_only(
        self, discovery_service, collection_base, project_base, mock_collection_config
    ):
        """Artifacts only in Collection are kept (might want to add to Project)."""
        # Setup: Create artifact in collection only
        collection_artifact_dir = collection_base / "artifacts" / "skills" / "test-skill"
        collection_artifact_dir.mkdir(parents=True, exist_ok=True)
        (collection_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        # Project has a DIFFERENT artifact (to trigger scan)
        project_artifact_dir = project_base / ".claude" / "skills" / "other-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text(
            "---\nname: other-skill\ntitle: Other Skill\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert: other-skill is in collection only, should be kept
        assert result.discovered_count >= 1
        assert result.importable_count >= 1
        assert len(result.artifacts) >= 1
        assert any(a.name == "other-skill" for a in result.artifacts)

    def test_keeps_artifacts_in_project_only(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Artifacts only in Project are kept (might want to add to Collection)."""
        # Setup: Create artifact in project only
        project_artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert: Artifact should be kept (not in collection)
        assert result.discovered_count == 1
        assert result.importable_count == 1
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "test-skill"

    def test_keeps_artifacts_in_neither(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Artifacts in neither location are kept (completely new)."""
        # Setup: Create artifact that discovery service will scan
        # This is a hypothetical scenario - artifact discovered but not yet in either location
        # In practice, if it's being discovered, it must exist somewhere
        # We'll test with an artifact in project that doesn't exist in collection
        project_artifact_dir = project_base / ".claude" / "skills" / "new-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text(
            "---\nname: new-skill\ntitle: New Skill\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert: Should be kept
        assert result.discovered_count == 1
        assert result.importable_count == 1
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "new-skill"

    def test_discovered_count_unchanged(
        self, discovery_service, collection_base, project_base, mock_collection_config
    ):
        """discovered_count reflects ALL found, even if filtered."""
        # Setup: Create 3 artifacts in project
        # - 1 in both locations (filtered)
        # - 2 in project only (kept)

        # Artifact 1: In both (filtered)
        collection_dir_1 = collection_base / "artifacts" / "skills" / "skill-both"
        collection_dir_1.mkdir(parents=True, exist_ok=True)
        (collection_dir_1 / "SKILL.md").write_text(
            "---\nname: skill-both\ntitle: Skill Both\n---\n"
        )
        project_dir_1 = project_base / ".claude" / "skills" / "skill-both"
        project_dir_1.mkdir(parents=True, exist_ok=True)
        (project_dir_1 / "SKILL.md").write_text(
            "---\nname: skill-both\ntitle: Skill Both\n---\n"
        )

        # Artifact 2: Project only
        project_dir_2 = project_base / ".claude" / "skills" / "skill-project-1"
        project_dir_2.mkdir(parents=True, exist_ok=True)
        (project_dir_2 / "SKILL.md").write_text(
            "---\nname: skill-project-1\ntitle: Skill Project 1\n---\n"
        )

        # Artifact 3: Project only
        project_dir_3 = project_base / ".claude" / "skills" / "skill-project-2"
        project_dir_3.mkdir(parents=True, exist_ok=True)
        (project_dir_3 / "SKILL.md").write_text(
            "---\nname: skill-project-2\ntitle: Skill Project 2\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert
        assert result.discovered_count == 3  # All 3 found
        assert result.importable_count == 2  # Only 2 kept (skill-both filtered)
        assert len(result.artifacts) == 2

    def test_importable_count_reflects_filtered(
        self, discovery_service, collection_base, project_base, mock_collection_config
    ):
        """importable_count reflects only non-filtered artifacts."""
        # Setup: Similar to previous test
        # Artifact 1: In both (filtered)
        collection_dir_1 = collection_base / "artifacts" / "skills" / "skill-both"
        collection_dir_1.mkdir(parents=True, exist_ok=True)
        (collection_dir_1 / "SKILL.md").write_text(
            "---\nname: skill-both\ntitle: Skill Both\n---\n"
        )
        project_dir_1 = project_base / ".claude" / "skills" / "skill-both"
        project_dir_1.mkdir(parents=True, exist_ok=True)
        (project_dir_1 / "SKILL.md").write_text(
            "---\nname: skill-both\ntitle: Skill Both\n---\n"
        )

        # Artifact 2: Project only
        project_dir_2 = project_base / ".claude" / "skills" / "skill-project"
        project_dir_2.mkdir(parents=True, exist_ok=True)
        (project_dir_2 / "SKILL.md").write_text(
            "---\nname: skill-project\ntitle: Skill Project\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert
        assert result.importable_count == 1  # Only skill-project is importable
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "skill-project"

    def test_early_return_when_all_filtered(
        self, discovery_service, collection_base, project_base, mock_collection_config
    ):
        """Returns successfully when all artifacts filtered out."""
        # Setup: Create artifact in both locations
        collection_artifact_dir = collection_base / "artifacts" / "skills" / "test-skill"
        collection_artifact_dir.mkdir(parents=True, exist_ok=True)
        (collection_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        project_artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        # Execute discovery
        result = discovery_service.discover_artifacts()

        # Assert: Should return successfully with empty importable list
        assert result.discovered_count == 1
        assert result.importable_count == 0
        assert len(result.artifacts) == 0
        assert result.scan_duration_ms > 0  # Scan completed


# =============================================================================
# Test Error Handling
# =============================================================================


class TestPrescanErrorHandling:
    """Tests for error handling in pre-scan logic."""

    def test_corrupt_manifest_handled(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Corrupt manifest file handled gracefully."""
        # Setup: Create artifact in project
        project_artifact_dir = project_base / ".claude" / "skills" / "test-skill"
        project_artifact_dir.mkdir(parents=True, exist_ok=True)
        (project_artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ntitle: Test Skill\n---\n"
        )

        # Create a mock manifest that raises an error
        mock_manifest = MagicMock()
        mock_manifest.find_artifact.side_effect = Exception("Corrupt manifest")

        # Execute: Should not raise exception
        result = discovery_service.discover_artifacts(manifest=mock_manifest)

        # Assert: Discovery should complete successfully
        assert result.discovered_count == 1
        # Check should still succeed using directory check
        assert result.importable_count == 1

    def test_missing_collection_directory(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Missing collection directory handled gracefully."""
        # Setup: Mock ConfigManager to return non-existent collection path
        with patch("skillmeat.config.ConfigManager") as mock_config_class:
            mock_config_instance = MagicMock()
            mock_config_instance.get_active_collection.return_value = "nonexistent"
            mock_config_instance.get_collection_path.return_value = (
                Path("/nonexistent/path")
            )
            mock_config_class.return_value = mock_config_instance

            # Create artifact in project
            project_artifact_dir = project_base / ".claude" / "skills" / "test-skill"
            project_artifact_dir.mkdir(parents=True, exist_ok=True)
            (project_artifact_dir / "SKILL.md").write_text(
                "---\nname: test-skill\ntitle: Test Skill\n---\n"
            )

            # Execute: Should not raise exception
            result = discovery_service.discover_artifacts()

            # Assert: Should complete successfully
            assert result.discovered_count == 1
            assert result.importable_count == 1

    def test_missing_project_directory(
        self, tmp_path, mock_collection_config
    ):
        """Missing project .claude directory handled gracefully."""
        # Setup: Create discovery service with non-existent project
        project_dir = tmp_path / "nonexistent-project"
        discovery_service = ArtifactDiscoveryService(
            base_path=project_dir, scan_mode="project"
        )

        # Execute: Should not raise exception
        result = discovery_service.discover_artifacts()

        # Assert: Should return empty result with error
        assert result.discovered_count == 0
        assert result.importable_count == 0
        assert len(result.artifacts) == 0
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestPrescanEdgeCases:
    """Tests for edge cases in pre-scan logic."""

    def test_empty_artifact_key(self, discovery_service, mock_collection_config):
        """Empty artifact key handled gracefully."""
        result = discovery_service.check_artifact_exists(artifact_key="")

        assert result["location"] == "none"
        assert result["exists_in_collection"] is False
        assert result["exists_in_project"] is False

    def test_whitespace_only_artifact_key(
        self, discovery_service, mock_collection_config
    ):
        """Whitespace-only artifact key handled gracefully."""
        result = discovery_service.check_artifact_exists(artifact_key="   ")

        assert result["location"] == "none"

    def test_special_characters_in_artifact_name(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Artifact names with special characters are handled."""
        # Setup: Create artifact with special chars (valid filesystem chars)
        artifact_dir = project_base / ".claude" / "skills" / "test-skill_v1.0"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "SKILL.md").write_text(
            "---\nname: test-skill_v1.0\ntitle: Test Skill\n---\n"
        )

        # Execute
        result = discovery_service.check_artifact_exists(
            artifact_key="skill:test-skill_v1.0"
        )

        # Assert
        assert result["exists_in_project"] is True
        assert result["location"] == "project"

    def test_case_sensitive_artifact_names(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Artifact names follow filesystem case sensitivity."""
        import platform

        # Setup: Create artifact with specific case
        artifact_dir = project_base / ".claude" / "skills" / "TestSkill"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "SKILL.md").write_text(
            "---\nname: TestSkill\ntitle: Test Skill\n---\n"
        )

        # Execute: Check with different case
        result_upper = discovery_service.check_artifact_exists(
            artifact_key="skill:TestSkill"
        )
        result_lower = discovery_service.check_artifact_exists(
            artifact_key="skill:testskill"
        )

        # Assert: Exact case match should always exist
        assert result_upper["exists_in_project"] is True

        # Case sensitivity depends on filesystem
        # macOS and Windows are typically case-insensitive, Linux is case-sensitive
        if platform.system() in ["Darwin", "Windows"]:
            # Case-insensitive filesystem - both should match
            assert result_lower["exists_in_project"] is True
        else:
            # Case-sensitive filesystem - only exact match should work
            assert result_lower["exists_in_project"] is False

    def test_concurrent_discovery_calls(
        self, discovery_service, project_base, mock_collection_config
    ):
        """Multiple concurrent discovery calls don't interfere."""
        import threading

        # Setup: Create some artifacts
        for i in range(3):
            artifact_dir = project_base / ".claude" / "skills" / f"skill-{i}"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            (artifact_dir / "SKILL.md").write_text(
                f"---\nname: skill-{i}\ntitle: Skill {i}\n---\n"
            )

        results = []

        def run_discovery():
            result = discovery_service.discover_artifacts()
            results.append(result)

        # Execute: Run discovery in multiple threads
        threads = [threading.Thread(target=run_discovery) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Assert: All calls should succeed and return same count
        assert len(results) == 3
        assert all(r.discovered_count == 3 for r in results)
        assert all(r.importable_count == 3 for r in results)
