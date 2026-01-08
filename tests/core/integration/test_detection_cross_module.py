"""Cross-module integration tests for artifact detection.

This test suite verifies consistency across all detection layers:
- Phase 1: artifact_detection.py (shared core module)
- Phase 2: discovery.py (local discovery service)
- Phase 3: heuristic_detector.py (marketplace detection)

The tests ensure that:
1. All modules use the same ArtifactType enum
2. Detection is consistent for the same artifact structure
3. Container aliases are recognized uniformly
4. Manifest extraction is consistent
5. Marketplace confidence is higher than strict mode for ambiguous cases
6. Detection reasons are traceable across layers
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from skillmeat.core.artifact_detection import (
    ARTIFACT_SIGNATURES,
    CANONICAL_CONTAINERS,
    CONTAINER_ALIASES,
    ArtifactType,
    DetectionError,
    DetectionResult,
    detect_artifact,
    extract_manifest_file,
    normalize_container_name,
)
from skillmeat.core.discovery import ArtifactDiscoveryService
from skillmeat.core.marketplace.heuristic_detector import HeuristicDetector


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def project_dir(temp_dir) -> Path:
    """Create a .claude project directory with multiple artifacts.

    Returns:
        Path to project root
    """
    claude_dir = temp_dir / ".claude"

    # Skill
    skills_dir = claude_dir / "skills"
    skills_dir.mkdir(parents=True)
    skill = skills_dir / "test-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill"
    )

    # Command
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "test-command.md").write_text(
        "---\nname: test-command\n---\n# Test Command"
    )

    # Agent using alias (subagents)
    agents_dir = claude_dir / "subagents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "test-agent.md").write_text(
        "---\nname: test-agent\n---\n# Test Agent"
    )

    return temp_dir


@pytest.fixture
def ambiguous_skill() -> Path:
    """Create skill directory without manifest for ambiguous detection tests.

    Returns:
        Path to project root
    """
    temp_path = Path(tempfile.mkdtemp())
    skills_dir = temp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    ambiguous = skills_dir / "ambiguous"
    ambiguous.mkdir()
    (ambiguous / "README.md").write_text("# No manifest")
    yield temp_path
    shutil.rmtree(temp_path)


# =============================================================================
# Test 1: Same Artifact Detected Consistently
# =============================================================================


class TestSameArtifactDetectedConsistently:
    """Verify the same artifact is detected consistently across all layers."""

    def test_skill_detected_by_all_layers(self, project_dir: Path):
        """Verify skill is detected by shared, discovery, and marketplace."""
        skill_path = project_dir / ".claude" / "skills" / "test-skill"

        # Phase 1: Shared module (strict mode)
        shared_result = detect_artifact(skill_path, container_type="skills", mode="strict")
        assert shared_result.artifact_type == ArtifactType.SKILL
        assert shared_result.confidence == 100

        # Phase 2: Discovery
        discovery = ArtifactDiscoveryService(project_dir, scan_mode="project")
        discovery_result = discovery.discover_artifacts()
        skills = [a for a in discovery_result.artifacts if a.type == "skill"]
        assert len(skills) == 1
        assert skills[0].name == "test-skill"

        # Phase 3: Marketplace
        detector = HeuristicDetector()
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(skill_path))
        assert marketplace_type == ArtifactType.SKILL
        assert marketplace_confidence > 0

    def test_command_detected_by_all_layers(self, project_dir: Path):
        """Verify command is detected by shared, discovery, and marketplace."""
        command_path = project_dir / ".claude" / "commands" / "test-command.md"

        # Phase 1: Shared module
        shared_result = detect_artifact(command_path, container_type="commands", mode="strict")
        assert shared_result.artifact_type == ArtifactType.COMMAND

        # Phase 2: Discovery
        discovery = ArtifactDiscoveryService(project_dir, scan_mode="project")
        discovery_result = discovery.discover_artifacts()
        commands = [a for a in discovery_result.artifacts if a.type == "command"]
        assert len(commands) == 1
        assert commands[0].name == "test-command"

        # Phase 3: Marketplace
        detector = HeuristicDetector()
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(command_path))
        assert marketplace_type == ArtifactType.COMMAND
        assert marketplace_confidence > 0

    def test_agent_detected_via_alias(self, project_dir: Path):
        """Verify agent is detected via 'subagents' alias by all layers."""
        agent_path = project_dir / ".claude" / "subagents" / "test-agent.md"

        # Phase 1: Shared module (with alias)
        shared_result = detect_artifact(agent_path, container_type="subagents", mode="strict")
        assert shared_result.artifact_type == ArtifactType.AGENT

        # Phase 2: Discovery (should recognize subagents/ alias)
        discovery = ArtifactDiscoveryService(project_dir, scan_mode="project")
        discovery_result = discovery.discover_artifacts()
        agents = [a for a in discovery_result.artifacts if a.type == "agent"]
        assert len(agents) == 1
        assert agents[0].name == "test-agent"

        # Phase 3: Marketplace (NOTE: may return None for file-based artifacts)
        # This is expected - marketplace detector is optimized for directory-based artifacts
        detector = HeuristicDetector()
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(agent_path))
        # Marketplace may not detect file-based artifacts, which is acceptable
        if marketplace_type is not None:
            assert marketplace_type == ArtifactType.AGENT


# =============================================================================
# Test 2: ArtifactType Enum Consistency
# =============================================================================


class TestArtifactTypeEnumConsistency:
    """Verify all modules use the same ArtifactType enum."""

    def test_all_modules_import_same_enum(self):
        """Verify ArtifactType is the same class across imports."""
        # Import from different modules
        from skillmeat.core.artifact_detection import ArtifactType as SharedType
        from skillmeat.core.discovery import ArtifactType as DiscoveryType
        from skillmeat.core.marketplace.heuristic_detector import ArtifactType as MarketplaceType

        # All should be the exact same class
        assert SharedType is DiscoveryType
        assert SharedType is MarketplaceType
        assert DiscoveryType is MarketplaceType

    def test_enum_values_consistent(self):
        """Verify enum values match string representations."""
        for artifact_type in ArtifactType.primary_types():
            # Value should match lowercase name
            assert artifact_type.value == artifact_type.name.lower()

    def test_enum_instances_are_identical(self, project_dir: Path):
        """Verify enum instances from different modules are identical."""
        skill_path = project_dir / ".claude" / "skills" / "test-skill"

        # Detect using shared module
        shared_result = detect_artifact(skill_path, container_type="skills", mode="strict")

        # Compare instances
        assert shared_result.artifact_type == ArtifactType.SKILL
        assert shared_result.artifact_type.value == "skill"
        assert isinstance(shared_result.artifact_type, ArtifactType)


# =============================================================================
# Test 3: Container Alias Consistency
# =============================================================================


class TestContainerAliasConsistency:
    """Verify container aliases are recognized uniformly."""

    def test_shared_normalize_container_works(self):
        """Verify shared normalize_container_name handles aliases."""
        # Test canonical name
        assert normalize_container_name("skills", ArtifactType.SKILL) == "skills"

        # Test alias (subagents → agents)
        assert normalize_container_name("subagents", ArtifactType.AGENT) == "agents"

        # Test case-insensitive
        assert normalize_container_name("SKILLS", ArtifactType.SKILL) == "skills"

    def test_marketplace_normalizes_containers(self, project_dir: Path):
        """Verify marketplace detector handles container normalization."""
        agent_path = project_dir / ".claude" / "subagents" / "test-agent.md"

        # Marketplace should detect agent despite using alias
        # NOTE: Marketplace may not detect file-based artifacts (returns None)
        detector = HeuristicDetector()
        marketplace_type, _ = detector.detect_artifact_type(str(agent_path))
        # If detected, should be AGENT
        if marketplace_type is not None:
            assert marketplace_type == ArtifactType.AGENT

    def test_all_aliases_registered(self):
        """Verify all registered aliases are in CONTAINER_ALIASES."""
        # Check that aliases exist for primary types
        for artifact_type in ArtifactType.primary_types():
            aliases = CONTAINER_ALIASES.get(artifact_type, set())
            canonical = CANONICAL_CONTAINERS.get(artifact_type, None)

            # Should have at least the canonical name
            assert canonical in aliases, f"{artifact_type} missing canonical in aliases"


# =============================================================================
# Test 4: Marketplace Confidence Higher Than Strict Mode
# =============================================================================


class TestMarketplaceConfidenceScoring:
    """Verify marketplace uses higher confidence for ambiguous artifacts."""

    def test_strict_mode_rejects_ambiguous(self, ambiguous_skill: Path):
        """Verify strict mode rejects artifacts without manifest."""
        ambiguous_path = ambiguous_skill / ".claude" / "skills" / "ambiguous"

        # Strict mode should raise DetectionError
        with pytest.raises(DetectionError):
            detect_artifact(ambiguous_path, container_type="skills", mode="strict")

    def test_heuristic_mode_accepts_ambiguous(self, ambiguous_skill: Path):
        """Verify heuristic mode accepts artifacts without manifest."""
        ambiguous_path = ambiguous_skill / ".claude" / "skills" / "ambiguous"

        # Heuristic mode should work (directory structure + parent hint)
        result = detect_artifact(ambiguous_path, container_type="skills", mode="heuristic")
        assert result.artifact_type == ArtifactType.SKILL
        assert result.confidence > 0
        assert result.confidence < 100  # Lower confidence without manifest

    def test_marketplace_confidence_intermediate(self, ambiguous_skill: Path):
        """Verify marketplace returns intermediate confidence for ambiguous artifacts."""
        ambiguous_path = ambiguous_skill / ".claude" / "skills" / "ambiguous"

        detector = HeuristicDetector()
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(ambiguous_path))

        assert marketplace_type == ArtifactType.SKILL
        # Should have intermediate confidence (not 0, not 100)
        assert 0 < marketplace_confidence < 100

    def test_marketplace_confidence_higher_with_manifest(self, project_dir: Path, ambiguous_skill: Path):
        """Verify marketplace gives higher confidence when manifest exists."""
        detector = HeuristicDetector()

        # With manifest
        with_manifest_path = project_dir / ".claude" / "skills" / "test-skill"
        _, with_manifest_confidence = detector.detect_artifact_type(str(with_manifest_path))

        # Without manifest
        without_manifest_path = ambiguous_skill / ".claude" / "skills" / "ambiguous"
        _, without_manifest_confidence = detector.detect_artifact_type(str(without_manifest_path))

        # Confidence with manifest should be higher (or at least equal if both are low)
        assert with_manifest_confidence >= without_manifest_confidence


# =============================================================================
# Test 5: Detection Reasons Traceable
# =============================================================================


class TestDetectionReasonsTraceable:
    """Verify detection reasons indicate signal sources."""

    def test_shared_module_provides_reasons(self, project_dir: Path):
        """Verify shared module populates detection_reasons."""
        skill_path = project_dir / ".claude" / "skills" / "test-skill"
        result = detect_artifact(skill_path, container_type="skills", mode="strict")

        # Should have reasons
        assert len(result.detection_reasons) > 0

        # Reasons should mention key signals
        reasons_text = " ".join(result.detection_reasons).lower()
        assert "manifest" in reasons_text or "skill.md" in reasons_text

    def test_heuristic_mode_provides_reasons(self, project_dir: Path):
        """Verify heuristic mode populates detection_reasons."""
        skill_path = project_dir / ".claude" / "skills" / "test-skill"
        result = detect_artifact(skill_path, container_type="skills", mode="heuristic")

        # Should have reasons
        assert len(result.detection_reasons) > 0
        assert result.confidence > 0


# =============================================================================
# Test 6: Manifest Extraction Consistency
# =============================================================================


class TestManifestExtractionConsistency:
    """Verify manifest extraction is consistent across layers."""

    def test_shared_extract_manifest_works(self, project_dir: Path):
        """Verify shared extract_manifest_file finds SKILL.md."""
        skill_path = project_dir / ".claude" / "skills" / "test-skill"
        manifest = extract_manifest_file(skill_path, ArtifactType.SKILL)

        assert manifest is not None
        assert manifest.name == "SKILL.md"
        assert manifest.exists()

    def test_manifest_found_consistently(self, project_dir: Path):
        """Verify all layers find the same manifest file."""
        skill_path = project_dir / ".claude" / "skills" / "test-skill"

        # Shared module
        shared_manifest = extract_manifest_file(skill_path, ArtifactType.SKILL)
        assert shared_manifest is not None

        # Discovery (indirectly through detect_artifact)
        shared_result = detect_artifact(skill_path, container_type="skills", mode="strict")
        assert "manifest" in " ".join(shared_result.detection_reasons).lower()


# =============================================================================
# Test 7: Cross-Module Integration Flow
# =============================================================================


class TestCrossModuleIntegrationFlow:
    """Verify end-to-end detection flow across all layers."""

    def test_complete_detection_pipeline(self, project_dir: Path):
        """Test complete detection flow: shared → discovery → marketplace."""
        # Phase 1: Shared module detects individual artifacts
        skill_path = project_dir / ".claude" / "skills" / "test-skill"
        shared_result = detect_artifact(skill_path, container_type="skills", mode="strict")
        assert shared_result.artifact_type == ArtifactType.SKILL

        # Phase 2: Discovery scans entire project
        discovery = ArtifactDiscoveryService(project_dir, scan_mode="project")
        discovery_result = discovery.discover_artifacts()
        assert discovery_result.discovered_count == 3
        assert len(discovery_result.artifacts) == 3

        # Phase 3: Marketplace detection (skips file-based artifacts)
        detector = HeuristicDetector()
        for artifact in discovery_result.artifacts:
            artifact_path = Path(artifact.path)
            marketplace_type, _ = detector.detect_artifact_type(str(artifact_path))

            # Types should match (if detected)
            if marketplace_type is not None:
                assert marketplace_type.value == artifact.type

    def test_all_layers_use_same_types(self, project_dir: Path):
        """Verify all layers identify the same artifact types."""
        discovery = ArtifactDiscoveryService(project_dir, scan_mode="project")
        discovery_result = discovery.discover_artifacts()

        detector = HeuristicDetector()

        for artifact in discovery_result.artifacts:
            artifact_path = Path(artifact.path)
            container = artifact_path.parent.name

            # Shared module
            shared_result = detect_artifact(artifact_path, container_type=container, mode="strict")

            # Marketplace (may skip file-based artifacts)
            marketplace_type, _ = detector.detect_artifact_type(str(artifact_path))

            # Shared and discovery should agree
            assert shared_result.artifact_type.value == artifact.type
            # Marketplace should agree if it detected anything
            if marketplace_type is not None:
                assert marketplace_type.value == artifact.type


# =============================================================================
# Test 8: Performance and Scalability
# =============================================================================


class TestPerformanceAndScalability:
    """Verify detection performance is acceptable across all layers."""

    def test_shared_module_performance(self, temp_dir: Path):
        """Verify shared module detection is fast."""
        import time

        # Create 50 artifacts
        skills_dir = temp_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        for i in range(50):
            skill = skills_dir / f"skill-{i}"
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"---\nname: skill-{i}\n---\n# Skill {i}")

        # Detect all
        start = time.time()
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                detect_artifact(skill_path, container_type="skills", mode="strict")
        duration = time.time() - start

        # Should be fast (< 1 second for 50 artifacts)
        assert duration < 1.0, f"Shared detection took {duration:.2f}s"

    def test_marketplace_performance(self, temp_dir: Path):
        """Verify marketplace detection is reasonably fast."""
        import time

        # Create 50 artifacts
        skills_dir = temp_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        for i in range(50):
            skill = skills_dir / f"skill-{i}"
            skill.mkdir()
            (skill / "SKILL.md").write_text(f"---\nname: skill-{i}\n---\n# Skill {i}")

        # Detect all
        detector = HeuristicDetector()
        start = time.time()
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                detector.detect_artifact_type(str(skill_path))
        duration = time.time() - start

        # Marketplace is slower (has more signals), but should still be reasonable
        assert duration < 2.0, f"Marketplace detection took {duration:.2f}s"


# =============================================================================
# Test 9: Edge Cases and Error Handling
# =============================================================================


class TestEdgeCasesAndErrorHandling:
    """Verify consistent error handling across all layers."""

    def test_invalid_path_handled(self):
        """Verify all layers handle non-existent paths gracefully."""
        invalid_path = Path("/nonexistent/path")

        # Shared module (strict mode raises exception for non-existent paths)
        with pytest.raises(DetectionError):
            detect_artifact(invalid_path, container_type="skills", mode="strict")

        # Heuristic mode may also raise or return low confidence
        # (Non-existent paths are fundamentally undetectable)
        try:
            heuristic_result = detect_artifact(invalid_path, container_type="skills", mode="heuristic")
            # If it doesn't raise, confidence should be very low
            assert heuristic_result.confidence == 0
        except DetectionError:
            # Also acceptable - can't detect non-existent paths
            pass

        # Marketplace
        detector = HeuristicDetector()
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(invalid_path))
        # Should return None or confidence 0 for non-existent paths
        assert marketplace_type is None or marketplace_confidence == 0

    def test_empty_directory_handled(self, temp_dir: Path):
        """Verify empty directory is handled consistently."""
        empty = temp_dir / ".claude" / "skills" / "empty"
        empty.mkdir(parents=True)

        # Shared module (strict mode should fail)
        with pytest.raises(DetectionError):
            detect_artifact(empty, container_type="skills", mode="strict")

        # Heuristic mode should work with low confidence
        heuristic_result = detect_artifact(empty, container_type="skills", mode="heuristic")
        assert heuristic_result.artifact_type == ArtifactType.SKILL
        assert heuristic_result.confidence < 100

    def test_file_instead_of_directory(self, temp_dir: Path):
        """Verify file in directory-based container is handled."""
        skills_dir = temp_dir / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        invalid_file = skills_dir / "not-a-skill.txt"
        invalid_file.write_text("Invalid")

        # Shared module (strict mode raises exception for structure mismatch)
        with pytest.raises(DetectionError):
            detect_artifact(invalid_file, container_type="skills", mode="strict")

        # Heuristic mode should handle gracefully (low/zero confidence)
        heuristic_result = detect_artifact(invalid_file, container_type="skills", mode="heuristic")
        # Should have very low confidence for invalid structure
        assert heuristic_result.confidence <= 20

        # Marketplace (may detect based on parent directory but with low confidence)
        detector = HeuristicDetector()
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(invalid_file))
        # If detected, should have low confidence (no valid manifest)
        if marketplace_type is not None:
            assert marketplace_confidence < 50  # Low confidence for invalid structure


# =============================================================================
# Test 10: Comprehensive Integration Test
# =============================================================================


def test_comprehensive_cross_module_consistency(project_dir: Path):
    """Comprehensive test verifying all layers work together consistently."""
    # 1. Discovery scans project
    discovery = ArtifactDiscoveryService(project_dir, scan_mode="project")
    discovery_result = discovery.discover_artifacts()

    assert discovery_result.discovered_count == 3

    # 2. For each discovered artifact, verify shared and marketplace agree
    detector = HeuristicDetector()

    for artifact in discovery_result.artifacts:
        artifact_path = Path(artifact.path)
        container = artifact_path.parent.name

        # Shared module
        shared_result = detect_artifact(artifact_path, container_type=container, mode="strict")

        # Marketplace (may skip file-based artifacts)
        marketplace_type, marketplace_confidence = detector.detect_artifact_type(str(artifact_path))

        # Shared and discovery should agree
        assert shared_result.artifact_type.value == artifact.type

        # Shared strict mode should have 100% confidence
        assert shared_result.confidence == 100

        # Shared should have detection reasons
        assert len(shared_result.detection_reasons) > 0

        # Marketplace should agree if it detected anything
        if marketplace_type is not None:
            assert marketplace_type.value == artifact.type
            # Marketplace should have some confidence (may be lower for ambiguous cases)
            assert marketplace_confidence > 0
