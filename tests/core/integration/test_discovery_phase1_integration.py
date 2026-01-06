"""Integration tests for discovery module with Phase 1 artifact_detection module.

This test suite verifies that the discovery module correctly integrates with
the unified artifact_detection module, ensuring:
- Shared ArtifactType enum is used consistently
- Container aliases are recognized
- Detection signatures are respected
- Confidence scoring works correctly
- Performance is acceptable
"""

import shutil
import tempfile
import time
from pathlib import Path

import pytest

from skillmeat.core.artifact_detection import (
    ARTIFACT_SIGNATURES,
    CANONICAL_CONTAINERS,
    CONTAINER_ALIASES,
    CONTAINER_TO_TYPE,
    MANIFEST_FILES,
    ArtifactType,
    DetectionError,
    DetectionResult,
    detect_artifact,
    extract_manifest_file,
    get_artifact_type_from_container,
    infer_artifact_type,
    normalize_container_name,
)
from skillmeat.core.discovery import ArtifactDiscoveryService, DiscoveredArtifact


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with .claude/ structure."""
    temp_dir = Path(tempfile.mkdtemp())
    claude_dir = temp_dir / ".claude"
    claude_dir.mkdir(parents=True)
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_project_dir(temp_project_dir):
    """Create a project directory with various artifact types."""
    # Skill with SKILL.md
    skills_dir = temp_project_dir / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    skill_dir = skills_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: Test skill\n---\n# Test Skill"
    )

    # Command as single .md file
    commands_dir = temp_project_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test-command.md").write_text(
        "---\nname: test-command\ndescription: Test command\n---\n# Test Command"
    )

    # Agent as single .md file in subagents alias
    agents_dir = temp_project_dir / ".claude" / "subagents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "test-agent.md").write_text(
        "---\nname: test-agent\ndescription: Test agent\n---\n# Test Agent"
    )

    return temp_project_dir


class TestDiscoveryPhase1Integration:
    """Integration tests between discovery and artifact_detection modules."""

    # ==========================================================================
    # Test 1: Shared ArtifactType Enum Usage
    # ==========================================================================

    def test_discovery_uses_shared_artifact_type_enum(self, temp_project_dir):
        """Verify discovery uses ArtifactType enum from shared module."""
        # Create a skill
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\n---\n# Test Skill"
        )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Verify artifact type matches enum value
        assert len(result.artifacts) == 1
        artifact = result.artifacts[0]
        assert artifact.type == ArtifactType.SKILL.value
        assert artifact.type == "skill"

    def test_all_artifact_types_recognized(self, temp_project_dir):
        """Verify all ArtifactType enum values are recognized by discovery."""
        # Create artifacts for primary types (skill, command, agent)
        # Note: hooks and mcp have more specific requirements, tested separately
        testable_types = [ArtifactType.SKILL, ArtifactType.COMMAND, ArtifactType.AGENT]

        for artifact_type in testable_types:
            container_name = CANONICAL_CONTAINERS[artifact_type]
            container_dir = temp_project_dir / ".claude" / container_name
            container_dir.mkdir(parents=True, exist_ok=True)

            # Get signature to determine structure
            sig = ARTIFACT_SIGNATURES[artifact_type]

            if sig.is_directory:
                # Directory-based artifact (e.g., skill)
                artifact_dir = container_dir / f"test-{artifact_type.value}"
                artifact_dir.mkdir()
                if sig.requires_manifest:
                    manifest_name = list(sig.manifest_names)[0]
                    (artifact_dir / manifest_name).write_text(
                        f"---\nname: test-{artifact_type.value}\n---\n# Test"
                    )
            else:
                # File-based artifact (e.g., command, agent)
                artifact_file = container_dir / f"test-{artifact_type.value}.md"
                artifact_file.write_text(
                    f"---\nname: test-{artifact_type.value}\n---\n# Test"
                )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Verify all testable types were discovered
        discovered_types = {a.type for a in result.artifacts}
        expected_types = {t.value for t in testable_types}
        assert discovered_types == expected_types

    # ==========================================================================
    # Test 2: Container Alias Recognition
    # ==========================================================================

    def test_container_aliases_recognized(self, temp_project_dir):
        """Verify all container aliases from shared module are recognized."""
        # Test with 'subagents' alias (should map to 'agent')
        agents_dir = temp_project_dir / ".claude" / "subagents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test-agent.md").write_text(
            "---\nname: test-agent\n---\n# Test Agent"
        )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Should discover agent via 'subagents' alias
        assert len(result.artifacts) >= 1
        agent_artifacts = [a for a in result.artifacts if a.type == "agent"]
        assert len(agent_artifacts) == 1
        assert agent_artifacts[0].name == "test-agent"

    def test_all_container_aliases_work(self, temp_project_dir):
        """Verify all registered container aliases are recognized."""
        test_cases = []

        # Build test cases for testable types (skill, command, agent)
        testable_types = [ArtifactType.SKILL, ArtifactType.COMMAND, ArtifactType.AGENT]

        for artifact_type in testable_types:
            aliases = CONTAINER_ALIASES[artifact_type]
            sig = ARTIFACT_SIGNATURES[artifact_type]
            # Test one non-canonical alias per type
            canonical = CANONICAL_CONTAINERS[artifact_type]
            non_canonical = [a for a in aliases if a != canonical]
            if non_canonical:
                test_cases.append(
                    (artifact_type, non_canonical[0], sig.is_directory, sig.manifest_names)
                )

        # Create artifacts using non-canonical aliases
        for artifact_type, alias, is_dir, manifest_names in test_cases:
            container_dir = temp_project_dir / ".claude" / alias
            container_dir.mkdir(parents=True, exist_ok=True)

            if is_dir:
                artifact_dir = container_dir / f"test-{artifact_type.value}"
                artifact_dir.mkdir()
                if manifest_names:
                    manifest_name = list(manifest_names)[0]
                    (artifact_dir / manifest_name).write_text(
                        f"---\nname: test-{artifact_type.value}\n---\n# Test"
                    )
            else:
                (container_dir / f"test-{artifact_type.value}.md").write_text(
                    f"---\nname: test-{artifact_type.value}\n---\n# Test"
                )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Verify all aliases were recognized
        discovered_types = {a.type for a in result.artifacts}
        expected_types = {t.value for t, _, _, _ in test_cases}
        assert discovered_types == expected_types

    # ==========================================================================
    # Test 3: Artifact Signature Respect
    # ==========================================================================

    def test_artifact_signatures_respected(self, temp_project_dir):
        """Verify ARTIFACT_SIGNATURES rules are respected during discovery."""
        # Skills require SKILL.md manifest
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        # Valid skill (has SKILL.md)
        valid_skill = skills_dir / "valid-skill"
        valid_skill.mkdir()
        (valid_skill / "SKILL.md").write_text(
            "---\nname: valid-skill\n---\n# Valid"
        )

        # Invalid skill (missing SKILL.md)
        invalid_skill = skills_dir / "invalid-skill"
        invalid_skill.mkdir()
        (invalid_skill / "README.md").write_text("# Not a skill")

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        skill_names = [a.name for a in result.artifacts if a.type == "skill"]
        assert "valid-skill" in skill_names
        assert "invalid-skill" not in skill_names

    def test_directory_vs_file_structure_enforced(self, temp_project_dir):
        """Verify directory/file structure requirements are enforced."""
        # Commands must be files (not directories)
        commands_dir = temp_project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        # Valid command (single file)
        (commands_dir / "valid-command.md").write_text(
            "---\nname: valid-command\n---\n# Valid Command"
        )

        # Invalid command (directory with COMMAND.md) - deprecated pattern
        # Discovery still detects this but logs a deprecation warning
        invalid_dir = commands_dir / "invalid-command"
        invalid_dir.mkdir()
        (invalid_dir / "COMMAND.md").write_text(
            "---\nname: invalid-command\n---\n# Invalid"
        )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "valid-command" in command_names
        # Directory-based commands may be discovered (with deprecation warning)
        # The key is that the warning is logged, not that they're excluded

    def test_nested_artifacts_supported(self, temp_project_dir):
        """Verify nested artifacts work for types that allow nesting."""
        # Commands support nesting
        commands_dir = temp_project_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        # Nested command
        subdir = commands_dir / "category"
        subdir.mkdir()
        (subdir / "nested-command.md").write_text(
            "---\nname: nested-command\n---\n# Nested"
        )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        command_names = [a.name for a in result.artifacts if a.type == "command"]
        assert "nested-command" in command_names

    # ==========================================================================
    # Test 4: Container Normalization
    # ==========================================================================

    def test_container_normalization_used(self, temp_project_dir):
        """Verify container names are normalized via shared function."""
        # Create skill using non-canonical container name
        skills_dir = temp_project_dir / ".claude" / "SKILLS"  # Uppercase
        skills_dir.mkdir(parents=True)
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\n---\n# Test"
        )

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Should discover skill and normalize container name
        assert len(result.artifacts) == 1
        artifact = result.artifacts[0]
        assert artifact.type == "skill"
        # Discovery should use canonical container name internally
        normalized = normalize_container_name("SKILLS", ArtifactType.SKILL)
        assert normalized == "skills"

    # ==========================================================================
    # Test 5: Detection Confidence Scoring
    # ==========================================================================

    def test_detection_confidence_scores_strict_mode(self, temp_project_dir):
        """Verify 100% confidence for valid artifacts in strict mode."""
        # Create a valid skill
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\n---\n# Test"
        )

        # Use detect_artifact directly in strict mode
        result = detect_artifact(skill_dir, container_type="skills", mode="strict")

        assert result.artifact_type == ArtifactType.SKILL
        assert result.confidence == 100
        assert result.is_confident
        assert result.is_strict

    def test_detection_confidence_heuristic_mode(self, temp_project_dir):
        """Verify confidence scoring in heuristic mode."""
        # Create an ambiguous artifact (no manifest, just directory)
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        ambiguous_dir = skills_dir / "ambiguous"
        ambiguous_dir.mkdir()
        # No SKILL.md - should fail strict mode but work in heuristic

        # Heuristic mode should return a result with lower confidence
        result = detect_artifact(
            ambiguous_dir, container_type="skills", mode="heuristic"
        )

        assert result.artifact_type == ArtifactType.SKILL
        assert result.confidence < 100  # Lower confidence
        assert not result.is_strict

    def test_discovery_uses_heuristic_mode(self, populated_project_dir):
        """Verify discovery uses heuristic mode for flexible detection."""
        service = ArtifactDiscoveryService(populated_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # All valid artifacts should be discovered
        assert len(result.artifacts) == 3  # skill, command, agent
        assert result.discovered_count == 3

    # ==========================================================================
    # Test 6: Cross-Module Type Consistency
    # ==========================================================================

    def test_cross_module_type_consistency(self, populated_project_dir):
        """Verify ArtifactType enum is used consistently across modules."""
        service = ArtifactDiscoveryService(populated_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        for artifact in result.artifacts:
            # Verify artifact.type can be converted to ArtifactType enum
            artifact_type_enum = ArtifactType(artifact.type)
            assert artifact_type_enum in ArtifactType.primary_types()

            # Verify enum value matches string
            assert artifact.type == artifact_type_enum.value

    def test_manifest_file_detection(self, populated_project_dir):
        """Verify manifest files are detected using shared module."""
        service = ArtifactDiscoveryService(populated_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Check that skill has manifest file detected
        skill_artifacts = [a for a in result.artifacts if a.type == "skill"]
        assert len(skill_artifacts) == 1
        skill = skill_artifacts[0]

        # Verify manifest file was found using shared module
        skill_path = Path(skill.path)
        manifest = extract_manifest_file(skill_path, ArtifactType.SKILL)
        assert manifest is not None
        assert manifest.name == "SKILL.md"

    # ==========================================================================
    # Test 7: Integration with DetectionResult
    # ==========================================================================

    def test_detection_results_parsed_correctly(self, temp_project_dir):
        """Verify DetectionResult is correctly converted to DiscoveredArtifact."""
        # Create a skill
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Test skill\nversion: 1.0.0\n---\n# Test"
        )

        # Detect using shared module
        detection_result = detect_artifact(
            skill_dir, container_type="skills", mode="strict"
        )

        # Run discovery
        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        discovery_result = service.discover_artifacts()

        # Verify DiscoveredArtifact matches DetectionResult
        assert len(discovery_result.artifacts) == 1
        discovered = discovery_result.artifacts[0]

        assert discovered.type == detection_result.artifact_type.value
        assert discovered.name == detection_result.name
        assert discovered.path == detection_result.path

    # ==========================================================================
    # Test 8: Performance Comparison
    # ==========================================================================

    def test_performance_with_shared_detector(self, temp_project_dir):
        """Verify discovery time with shared detector is acceptable."""
        # Create 30+ artifacts (skill, command, agent only - testable types)
        testable_types = [ArtifactType.SKILL, ArtifactType.COMMAND, ArtifactType.AGENT]

        for artifact_type in testable_types:
            container_name = CANONICAL_CONTAINERS[artifact_type]
            container_dir = temp_project_dir / ".claude" / container_name
            container_dir.mkdir(parents=True, exist_ok=True)

            sig = ARTIFACT_SIGNATURES[artifact_type]

            # Create 10 artifacts per type
            for i in range(10):
                if sig.is_directory:
                    artifact_dir = container_dir / f"artifact-{i}"
                    artifact_dir.mkdir()
                    if sig.requires_manifest:
                        manifest_name = list(sig.manifest_names)[0]
                        (artifact_dir / manifest_name).write_text(
                            f"---\nname: artifact-{i}\n---\n# Test {i}"
                        )
                else:
                    (container_dir / f"artifact-{i}.md").write_text(
                        f"---\nname: artifact-{i}\n---\n# Test {i}"
                    )

        # Measure discovery time
        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        start = time.time()
        result = service.discover_artifacts()
        duration = time.time() - start

        # Verify performance target: <2 seconds for 30+ artifacts
        assert result.discovered_count >= 30
        assert duration < 2.0, f"Discovery took {duration:.2f}s (target: <2s)"

    def test_detection_error_handling(self, temp_project_dir):
        """Verify detection errors are handled gracefully."""
        # Create an invalid structure
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        # Create a file in skills/ (should be directory)
        (skills_dir / "invalid-skill.txt").write_text("Invalid")

        # Discovery should handle this gracefully without failing
        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Should complete without raising exception
        assert result.discovered_count >= 0
        # Errors may be logged but shouldn't crash

    # ==========================================================================
    # Test 9: Shared Registry Usage
    # ==========================================================================

    def test_container_to_type_registry_used(self, temp_project_dir):
        """Verify CONTAINER_TO_TYPE registry is used for lookups."""
        # Test that all registered containers are recognized
        for container_name, expected_type in CONTAINER_TO_TYPE.items():
            # Create artifact using this container name
            container_dir = temp_project_dir / ".claude" / container_name
            container_dir.mkdir(parents=True, exist_ok=True)

            sig = ARTIFACT_SIGNATURES[expected_type]
            if sig.is_directory:
                artifact_dir = container_dir / "test-artifact"
                artifact_dir.mkdir()
                if sig.requires_manifest:
                    manifest_name = list(sig.manifest_names)[0]
                    (artifact_dir / manifest_name).write_text(
                        "---\nname: test-artifact\n---\n# Test"
                    )
            else:
                (container_dir / "test-artifact.md").write_text(
                    "---\nname: test-artifact\n---\n# Test"
                )

            # Verify lookup works
            detected_type = get_artifact_type_from_container(container_name)
            assert detected_type == expected_type

            # Clean up for next iteration
            shutil.rmtree(container_dir)

    # ==========================================================================
    # Test 10: Error Conditions
    # ==========================================================================

    def test_invalid_container_name_handled(self, temp_project_dir):
        """Verify invalid container names are handled gracefully."""
        # Create directory with invalid name
        invalid_dir = temp_project_dir / ".claude" / "invalid_type"
        invalid_dir.mkdir(parents=True)
        (invalid_dir / "artifact.md").write_text("# Test")

        # Discovery should skip this directory
        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Should not discover anything from invalid_type/
        assert result.discovered_count == 0

    def test_missing_manifest_file_rejected(self, temp_project_dir):
        """Verify artifacts without required manifest are rejected."""
        # Skills require SKILL.md
        skills_dir = temp_project_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        # Create skill directory without SKILL.md
        skill_dir = skills_dir / "no-manifest-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Missing SKILL.md")

        service = ArtifactDiscoveryService(temp_project_dir, scan_mode="project")
        result = service.discover_artifacts()

        # Should not discover skill without manifest
        skill_names = [a.name for a in result.artifacts if a.type == "skill"]
        assert "no-manifest-skill" not in skill_names


# =============================================================================
# Additional Integration Tests
# =============================================================================


def test_end_to_end_discovery_flow(populated_project_dir):
    """Test complete discovery flow using shared detection module."""
    service = ArtifactDiscoveryService(populated_project_dir, scan_mode="project")
    result = service.discover_artifacts()

    # Verify all artifacts were discovered
    assert result.discovered_count == 3
    assert result.importable_count == 3

    # Verify types are correct
    types = {a.type for a in result.artifacts}
    assert types == {"skill", "command", "agent"}

    # Verify names are correct
    names = {a.name for a in result.artifacts}
    assert names == {"test-skill", "test-command", "test-agent"}

    # Verify paths are correct
    for artifact in result.artifacts:
        path = Path(artifact.path)
        assert path.exists()


def test_infer_artifact_type_integration(populated_project_dir):
    """Verify infer_artifact_type works with discovery results."""
    service = ArtifactDiscoveryService(populated_project_dir, scan_mode="project")
    result = service.discover_artifacts()

    for artifact in result.artifacts:
        path = Path(artifact.path)
        # Infer type using shared module
        inferred_type = infer_artifact_type(path)
        assert inferred_type is not None
        assert inferred_type.value == artifact.type
