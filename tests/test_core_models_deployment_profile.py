"""Phase 1 tests for platform and deployment profile core models."""

from datetime import datetime

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.deployment import Deployment
from skillmeat.core.deployment_profile import DeploymentProfile
from skillmeat.core.enums import Platform


def test_platform_enum_includes_codex_and_gemini():
    """Platform enum should include new multi-platform values."""
    assert Platform.CLAUDE_CODE.value == "claude_code"
    assert Platform.CODEX.value == "codex"
    assert Platform.GEMINI.value == "gemini"


def test_artifact_target_platforms_round_trip():
    """Artifact target_platforms should serialize/deserialize via TOML dict."""
    artifact = Artifact(
        name="phase1-skill",
        type=ArtifactType.SKILL,
        path="skills/phase1-skill",
        origin="local",
        metadata=ArtifactMetadata(title="Phase 1"),
        added=datetime.utcnow(),
        target_platforms=[Platform.CLAUDE_CODE, Platform.CODEX],
    )

    payload = artifact.to_dict()
    assert payload["target_platforms"] == ["claude_code", "codex"]

    restored = Artifact.from_dict(payload)
    assert restored.target_platforms == [Platform.CLAUDE_CODE, Platform.CODEX]


def test_deployment_profile_model_validation():
    """DeploymentProfile model should validate required fields and enum types."""
    model = DeploymentProfile(
        profile_id="codex-default",
        platform=Platform.CODEX,
        root_dir=".codex",
        artifact_path_map={"skill": "skills"},
        project_config_filenames=["CODEX.md"],
        context_path_prefixes=[".codex/context/"],
        supported_artifact_types=["skill", "command"],
    )

    assert model.profile_id == "codex-default"
    assert model.platform == Platform.CODEX
    assert model.root_dir == ".codex"


def test_deployment_record_profile_fields_round_trip():
    """Deployment records should preserve profile-related optional fields."""
    deployment = Deployment(
        artifact_name="phase1-skill",
        artifact_type="skill",
        from_collection="default",
        deployed_at=datetime.utcnow(),
        artifact_path="skills/phase1-skill",
        content_hash="abc123",
        deployment_profile_id="codex-default",
        platform=Platform.CODEX,
        profile_root_dir=".codex",
    )

    payload = deployment.to_dict()
    assert payload["deployment_profile_id"] == "codex-default"
    assert payload["platform"] == "codex"
    assert payload["profile_root_dir"] == ".codex"

    restored = Deployment.from_dict(payload)
    assert restored.deployment_profile_id == "codex-default"
    assert restored.platform == Platform.CODEX
    assert restored.profile_root_dir == ".codex"
