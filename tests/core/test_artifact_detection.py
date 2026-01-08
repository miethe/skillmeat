"""Tests for artifact_detection module.

Comprehensive test coverage for:
- ArtifactType enum values and methods
- DetectionResult dataclass
- ArtifactSignature dataclass
- Container normalization functions
- Artifact detection functions

Tests follow pytest conventions with fixtures for temporary directories
and filesystem structures.
"""

import pytest
from pathlib import Path

from skillmeat.core.artifact_detection import (
    ArtifactType,
    DetectionResult,
    ArtifactSignature,
    ContainerConfig,
    ARTIFACT_SIGNATURES,
    CONTAINER_ALIASES,
    CONTAINER_TO_TYPE,
    MANIFEST_FILES,
    CANONICAL_CONTAINERS,
    normalize_container_name,
    get_artifact_type_from_container,
    infer_artifact_type,
    detect_artifact,
    extract_manifest_file,
    InvalidContainerError,
    InvalidArtifactTypeError,
    DetectionError,
)


# =============================================================================
# ArtifactType Enum Tests
# =============================================================================


class TestArtifactType:
    """Tests for ArtifactType enum."""

    def test_primary_types_exist(self):
        """All primary artifact types should be defined."""
        assert ArtifactType.SKILL
        assert ArtifactType.COMMAND
        assert ArtifactType.AGENT
        assert ArtifactType.HOOK
        assert ArtifactType.MCP

    def test_context_types_exist(self):
        """All context entity types should be defined."""
        assert ArtifactType.PROJECT_CONFIG
        assert ArtifactType.SPEC_FILE
        assert ArtifactType.RULE_FILE
        assert ArtifactType.CONTEXT_FILE
        assert ArtifactType.PROGRESS_TEMPLATE

    def test_string_conversion(self):
        """ArtifactType.value should return lowercase string."""
        assert ArtifactType.SKILL.value == "skill"
        assert ArtifactType.COMMAND.value == "command"
        assert ArtifactType.AGENT.value == "agent"
        assert ArtifactType.HOOK.value == "hook"
        assert ArtifactType.MCP.value == "mcp"

    def test_enum_from_string(self):
        """Should be able to create enum from string value."""
        assert ArtifactType("skill") == ArtifactType.SKILL
        assert ArtifactType("command") == ArtifactType.COMMAND
        assert ArtifactType("agent") == ArtifactType.AGENT
        assert ArtifactType("hook") == ArtifactType.HOOK
        assert ArtifactType("mcp") == ArtifactType.MCP

    def test_primary_types_method(self):
        """primary_types() should return list of deployable types."""
        primary = ArtifactType.primary_types()
        assert len(primary) == 5
        assert ArtifactType.SKILL in primary
        assert ArtifactType.COMMAND in primary
        assert ArtifactType.AGENT in primary
        assert ArtifactType.HOOK in primary
        assert ArtifactType.MCP in primary
        # Should not contain context types
        assert ArtifactType.PROJECT_CONFIG not in primary

    def test_context_types_method(self):
        """context_types() should return list of non-deployable types."""
        context = ArtifactType.context_types()
        assert len(context) == 5
        assert ArtifactType.PROJECT_CONFIG in context
        assert ArtifactType.SPEC_FILE in context
        assert ArtifactType.RULE_FILE in context
        assert ArtifactType.CONTEXT_FILE in context
        assert ArtifactType.PROGRESS_TEMPLATE in context
        # Should not contain primary types
        assert ArtifactType.SKILL not in context

    def test_invalid_value_raises_valueerror(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError):
            ArtifactType("invalid_type")

    def test_str_enum_behavior(self):
        """ArtifactType extends str, so direct string comparison works."""
        assert ArtifactType.SKILL == "skill"
        # str() returns enum representation, use .value for string value
        assert ArtifactType.SKILL.value == "skill"
        # But comparison with string works due to str inheritance
        assert ArtifactType.SKILL == "skill"
        assert "skill" == ArtifactType.SKILL


# =============================================================================
# Container Normalization Tests
# =============================================================================


class TestContainerNormalization:
    """Tests for container name normalization."""

    def test_lowercase_normalization(self):
        """Uppercase container names should normalize to lowercase canonical form."""
        assert normalize_container_name("SKILLS") == "skills"
        assert normalize_container_name("Skills") == "skills"
        assert normalize_container_name("COMMANDS") == "commands"
        assert normalize_container_name("AGENTS") == "agents"

    def test_alias_normalization(self):
        """Container aliases should normalize to canonical name."""
        assert normalize_container_name("subagents") == "agents"
        assert normalize_container_name("mcp-servers") == "mcp"
        assert normalize_container_name("servers") == "mcp"
        assert normalize_container_name("mcp_servers") == "mcp"
        assert normalize_container_name("claude-skills") == "skills"

    def test_all_primary_types_have_aliases(self):
        """Every primary artifact type should have container aliases."""
        for artifact_type in ArtifactType.primary_types():
            assert artifact_type in CONTAINER_ALIASES
            aliases = CONTAINER_ALIASES[artifact_type]
            assert len(aliases) >= 2, f"{artifact_type} should have at least 2 aliases"

    def test_with_artifact_type_parameter(self):
        """normalize_container_name with artifact_type should validate against that type."""
        # Valid: subagents is alias for agents
        assert (
            normalize_container_name("subagents", ArtifactType.AGENT) == "agents"
        )
        # Valid: skills is canonical for SKILL type
        assert (
            normalize_container_name("skills", ArtifactType.SKILL) == "skills"
        )

    def test_case_insensitivity(self):
        """Normalization should be case-insensitive."""
        assert normalize_container_name("Skills") == "skills"
        assert normalize_container_name("SUBAGENTS") == "agents"
        assert normalize_container_name("MCP-Servers") == "mcp"

    def test_invalid_container_raises_error(self):
        """InvalidContainerError should be raised for unrecognized container names."""
        with pytest.raises(InvalidContainerError) as exc_info:
            normalize_container_name("invalid_container")
        assert "invalid_container" in str(exc_info.value)

    def test_invalid_container_for_specific_type(self):
        """InvalidContainerError when container doesn't match specified type."""
        with pytest.raises(InvalidContainerError) as exc_info:
            normalize_container_name("skills", ArtifactType.AGENT)
        assert "skills" in str(exc_info.value)
        assert "agent" in str(exc_info.value)

    def test_get_artifact_type_from_container(self):
        """get_artifact_type_from_container should return correct type."""
        assert get_artifact_type_from_container("skills") == ArtifactType.SKILL
        assert get_artifact_type_from_container("commands") == ArtifactType.COMMAND
        assert get_artifact_type_from_container("agents") == ArtifactType.AGENT
        assert get_artifact_type_from_container("subagents") == ArtifactType.AGENT
        assert get_artifact_type_from_container("hooks") == ArtifactType.HOOK
        assert get_artifact_type_from_container("mcp") == ArtifactType.MCP
        assert get_artifact_type_from_container("mcp-servers") == ArtifactType.MCP

    def test_unknown_container_returns_none(self):
        """Unknown container should return None from get_artifact_type_from_container."""
        assert get_artifact_type_from_container("unknown") is None
        assert get_artifact_type_from_container("random_dir") is None
        assert get_artifact_type_from_container("") is None


# =============================================================================
# Artifact Signatures Tests
# =============================================================================


class TestArtifactSignatures:
    """Tests for artifact signature registry."""

    def test_all_primary_types_have_signatures(self):
        """Every primary artifact type should have a signature defined."""
        for artifact_type in ArtifactType.primary_types():
            assert artifact_type in ARTIFACT_SIGNATURES, (
                f"Missing signature for {artifact_type}"
            )

    def test_skill_signature_is_directory_with_manifest(self):
        """SKILL signature should require directory with manifest."""
        sig = ARTIFACT_SIGNATURES[ArtifactType.SKILL]
        assert sig.is_directory is True
        assert sig.requires_manifest is True
        assert "SKILL.md" in sig.manifest_names
        assert sig.allowed_nesting is False

    def test_command_signature_is_file_without_required_manifest(self):
        """COMMAND signature should be file without required manifest."""
        sig = ARTIFACT_SIGNATURES[ArtifactType.COMMAND]
        assert sig.is_directory is False
        assert sig.requires_manifest is False
        assert sig.allowed_nesting is True  # Commands can be nested

    def test_agent_signature_allows_nesting(self):
        """AGENT signature should allow nesting in subdirectories."""
        sig = ARTIFACT_SIGNATURES[ArtifactType.AGENT]
        assert sig.is_directory is False
        assert sig.allowed_nesting is True

    def test_signature_matches_container_method(self):
        """ArtifactSignature.matches_container() should work case-insensitively."""
        sig = ARTIFACT_SIGNATURES[ArtifactType.SKILL]
        assert sig.matches_container("skills") is True
        assert sig.matches_container("SKILLS") is True
        assert sig.matches_container("skill") is True
        assert sig.matches_container("claude-skills") is True
        assert sig.matches_container("commands") is False

    def test_signature_matches_manifest_method(self):
        """ArtifactSignature.matches_manifest() should be case-insensitive."""
        sig = ARTIFACT_SIGNATURES[ArtifactType.SKILL]
        assert sig.matches_manifest("SKILL.md") is True
        assert sig.matches_manifest("skill.md") is True
        assert sig.matches_manifest("Skill.md") is True
        assert sig.matches_manifest("README.md") is False


# =============================================================================
# Detection Result Tests
# =============================================================================


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_basic_creation(self):
        """DetectionResult should be created with required fields."""
        result = DetectionResult(
            artifact_type=ArtifactType.SKILL,
            name="my-skill",
            path="/path/to/skills/my-skill",
            container_type="skills",
            detection_mode="strict",
            confidence=100,
        )
        assert result.artifact_type == ArtifactType.SKILL
        assert result.name == "my-skill"
        assert result.confidence == 100

    def test_is_confident_property_high_confidence(self):
        """is_confident should return True for confidence >= 80."""
        result = DetectionResult(
            artifact_type=ArtifactType.SKILL,
            name="test",
            path="/path",
            container_type="skills",
            detection_mode="strict",
            confidence=80,
        )
        assert result.is_confident is True

    def test_is_confident_property_low_confidence(self):
        """is_confident should return False for confidence < 80."""
        result = DetectionResult(
            artifact_type=ArtifactType.SKILL,
            name="test",
            path="/path",
            container_type="skills",
            detection_mode="heuristic",
            confidence=50,
        )
        assert result.is_confident is False

    def test_is_strict_property(self):
        """is_strict should return True for strict detection mode."""
        strict = DetectionResult(
            artifact_type=ArtifactType.SKILL,
            name="test",
            path="/path",
            container_type="skills",
            detection_mode="strict",
            confidence=100,
        )
        heuristic = DetectionResult(
            artifact_type=ArtifactType.SKILL,
            name="test",
            path="/path",
            container_type="skills",
            detection_mode="heuristic",
            confidence=50,
        )
        assert strict.is_strict is True
        assert heuristic.is_strict is False

    def test_confidence_validation(self):
        """Confidence must be in 0-100 range."""
        with pytest.raises(ValueError):
            DetectionResult(
                artifact_type=ArtifactType.SKILL,
                name="test",
                path="/path",
                container_type="skills",
                detection_mode="strict",
                confidence=150,  # Invalid
            )

        with pytest.raises(ValueError):
            DetectionResult(
                artifact_type=ArtifactType.SKILL,
                name="test",
                path="/path",
                container_type="skills",
                detection_mode="strict",
                confidence=-10,  # Invalid
            )


# =============================================================================
# Detection Functions Tests
# =============================================================================


class TestDetectionFunctions:
    """Tests for detection functions."""

    @pytest.fixture
    def temp_skill_dir(self, tmp_path):
        """Create a temporary skill directory with manifest."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill\n\nA test skill.")
        return skill_dir

    @pytest.fixture
    def temp_command_file(self, tmp_path):
        """Create a temporary command file."""
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        cmd_file = commands_dir / "my-command.md"
        cmd_file.write_text("# My Command\n\nA test command.")
        return cmd_file

    @pytest.fixture
    def temp_agent_file(self, tmp_path):
        """Create a temporary agent file in subagents directory."""
        agents_dir = tmp_path / "subagents"  # Using alias
        agents_dir.mkdir()
        agent_file = agents_dir / "my-agent.md"
        agent_file.write_text("# My Agent\n\nA test agent.")
        return agent_file

    @pytest.fixture
    def temp_nested_command(self, tmp_path):
        """Create a nested command structure."""
        commands_dir = tmp_path / "commands" / "nested"
        commands_dir.mkdir(parents=True)
        cmd_file = commands_dir / "nested-cmd.md"
        cmd_file.write_text("# Nested Command")
        return cmd_file

    # --- infer_artifact_type tests ---

    def test_infer_artifact_type_with_skill_directory(self, temp_skill_dir):
        """infer_artifact_type should detect skill from SKILL.md presence."""
        result = infer_artifact_type(temp_skill_dir)
        assert result == ArtifactType.SKILL

    def test_infer_artifact_type_with_command_file(self, temp_command_file):
        """infer_artifact_type should detect command from parent directory."""
        result = infer_artifact_type(temp_command_file)
        assert result == ArtifactType.COMMAND

    def test_infer_artifact_type_with_agent_alias(self, temp_agent_file):
        """infer_artifact_type should work with subagents alias."""
        result = infer_artifact_type(temp_agent_file)
        assert result == ArtifactType.AGENT

    def test_infer_artifact_type_returns_none_for_unknown(self, tmp_path):
        """infer_artifact_type should return None for unrecognized paths."""
        random_file = tmp_path / "random" / "file.txt"
        random_file.parent.mkdir(parents=True)
        random_file.write_text("random content")
        result = infer_artifact_type(random_file)
        assert result is None

    def test_infer_artifact_type_nested_command(self, temp_nested_command):
        """infer_artifact_type should detect nested commands."""
        result = infer_artifact_type(temp_nested_command)
        assert result == ArtifactType.COMMAND

    # --- detect_artifact tests ---

    def test_detect_artifact_strict_mode_success(self, temp_skill_dir):
        """detect_artifact in strict mode should return 100% confidence."""
        result = detect_artifact(temp_skill_dir, mode="strict")
        assert result.artifact_type == ArtifactType.SKILL
        assert result.confidence == 100
        assert result.detection_mode == "strict"
        assert result.name == "test-skill"

    def test_detect_artifact_strict_mode_failure(self, tmp_path):
        """detect_artifact in strict mode should raise DetectionError for unknown."""
        random_dir = tmp_path / "random"
        random_dir.mkdir()
        with pytest.raises(DetectionError):
            detect_artifact(random_dir, mode="strict")

    def test_detect_artifact_heuristic_mode_returns_confidence(self, tmp_path):
        """detect_artifact in heuristic mode should return low confidence for unknown."""
        random_dir = tmp_path / "random"
        random_dir.mkdir()
        result = detect_artifact(random_dir, mode="heuristic")
        assert result.confidence == 0
        assert result.detection_mode == "heuristic"
        # Should default to SKILL in heuristic mode when unknown
        assert result.artifact_type == ArtifactType.SKILL

    def test_detect_artifact_with_container_hint(self, tmp_path):
        """detect_artifact with container_type hint should use it for detection."""
        # Create a generic .md file
        some_dir = tmp_path / "some_dir"
        some_dir.mkdir()
        md_file = some_dir / "test.md"
        md_file.write_text("# Test")

        # With container hint, should detect as that type
        result = detect_artifact(md_file, container_type="commands", mode="heuristic")
        assert result.artifact_type == ArtifactType.COMMAND

    def test_detect_artifact_finds_manifest(self, temp_skill_dir):
        """detect_artifact should find and report manifest file."""
        result = detect_artifact(temp_skill_dir, mode="strict")
        assert result.manifest_file is not None
        assert "SKILL.md" in result.manifest_file

    def test_detect_artifact_missing_manifest_lowers_confidence(self, tmp_path):
        """Skill directory without manifest should fail strict detection."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "no-manifest-skill"
        skill_dir.mkdir()
        # No SKILL.md file

        with pytest.raises(DetectionError):
            detect_artifact(skill_dir, mode="strict")

    def test_detect_artifact_detection_reasons(self, temp_skill_dir):
        """detect_artifact should populate detection_reasons list."""
        result = detect_artifact(temp_skill_dir, mode="strict")
        assert len(result.detection_reasons) > 0
        # Should mention the manifest file
        reasons_text = " ".join(result.detection_reasons)
        assert "manifest" in reasons_text.lower() or "SKILL.md" in reasons_text

    # --- extract_manifest_file tests ---

    def test_extract_manifest_file_finds_skill_md(self, temp_skill_dir):
        """extract_manifest_file should find SKILL.md in skill directory."""
        manifest = extract_manifest_file(temp_skill_dir, ArtifactType.SKILL)
        assert manifest is not None
        assert manifest.name == "SKILL.md"

    def test_extract_manifest_file_returns_none_for_missing(self, tmp_path):
        """extract_manifest_file should return None when no manifest exists."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        manifest = extract_manifest_file(empty_dir, ArtifactType.SKILL)
        assert manifest is None

    def test_extract_manifest_file_case_insensitive(self, tmp_path):
        """extract_manifest_file should be case-insensitive."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        # Create lowercase manifest
        (skill_dir / "skill.md").write_text("# Lowercase manifest")
        manifest = extract_manifest_file(skill_dir, ArtifactType.SKILL)
        assert manifest is not None
        assert manifest.name == "skill.md"


# =============================================================================
# Exception Tests
# =============================================================================


class TestExceptions:
    """Tests for detection-related exceptions."""

    def test_invalid_container_error_attributes(self):
        """InvalidContainerError should have informative attributes."""
        exc = InvalidContainerError(
            container_name="bad_name",
            artifact_type=ArtifactType.SKILL,
            valid_aliases={"skills", "skill"},
        )
        assert exc.container_name == "bad_name"
        assert exc.artifact_type == ArtifactType.SKILL
        assert exc.valid_aliases == {"skills", "skill"}
        assert "bad_name" in str(exc)
        assert "skill" in str(exc)

    def test_invalid_artifact_type_error(self):
        """InvalidArtifactTypeError should have informative message."""
        exc = InvalidArtifactTypeError("not_a_type")
        assert exc.type_value == "not_a_type"
        assert "not_a_type" in str(exc)
        assert "Valid types" in str(exc)

    def test_detection_error_inheritance(self):
        """InvalidContainerError and InvalidArtifactTypeError should inherit DetectionError."""
        assert issubclass(InvalidContainerError, DetectionError)
        assert issubclass(InvalidArtifactTypeError, DetectionError)


# =============================================================================
# ContainerConfig Tests
# =============================================================================


class TestContainerConfig:
    """Tests for ContainerConfig dataclass."""

    def test_canonical_name_in_aliases(self):
        """Canonical name should always be in aliases (auto-added in __post_init__)."""
        config = ContainerConfig(
            canonical_name="skills",
            aliases=frozenset({"skill", "claude-skills"}),
        )
        assert "skills" in config.aliases

    def test_frozen_dataclass(self):
        """ContainerConfig should be frozen (immutable)."""
        config = ContainerConfig(
            canonical_name="skills",
            aliases=frozenset({"skills", "skill"}),
        )
        with pytest.raises(AttributeError):
            config.canonical_name = "commands"


# =============================================================================
# Registry Completeness Tests
# =============================================================================


class TestRegistryCompleteness:
    """Tests to verify registries are complete and consistent."""

    def test_container_to_type_has_all_aliases(self):
        """CONTAINER_TO_TYPE should have entries for all aliases."""
        for artifact_type, aliases in CONTAINER_ALIASES.items():
            for alias in aliases:
                assert alias.lower() in CONTAINER_TO_TYPE, (
                    f"Missing CONTAINER_TO_TYPE entry for '{alias}'"
                )
                assert CONTAINER_TO_TYPE[alias.lower()] == artifact_type

    def test_canonical_containers_match_aliases(self):
        """CANONICAL_CONTAINERS values should be in CONTAINER_ALIASES."""
        for artifact_type, canonical in CANONICAL_CONTAINERS.items():
            aliases = CONTAINER_ALIASES.get(artifact_type, set())
            assert canonical in aliases, (
                f"Canonical '{canonical}' not in aliases for {artifact_type}"
            )

    def test_manifest_files_match_signatures(self):
        """MANIFEST_FILES should be consistent with ARTIFACT_SIGNATURES."""
        for artifact_type, manifest_names in MANIFEST_FILES.items():
            if artifact_type in ARTIFACT_SIGNATURES:
                sig = ARTIFACT_SIGNATURES[artifact_type]
                assert manifest_names == sig.manifest_names, (
                    f"Manifest mismatch for {artifact_type}"
                )

    def test_all_signatures_have_valid_artifact_type(self):
        """Every signature should have a valid ArtifactType."""
        for artifact_type, sig in ARTIFACT_SIGNATURES.items():
            assert sig.artifact_type == artifact_type
            assert isinstance(sig.artifact_type, ArtifactType)
