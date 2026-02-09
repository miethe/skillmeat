"""Tests for platform detection during bulk artifact import."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from skillmeat.core.enums import Platform
from skillmeat.core.importer import ArtifactImporter, BulkImportArtifactData


def _build_importer() -> tuple[ArtifactImporter, MagicMock]:
    artifact_manager = MagicMock()
    artifact_manager.add_from_local.return_value = SimpleNamespace(name="test-skill")
    artifact_manager.add_from_github.return_value = SimpleNamespace(name="test-skill")
    collection_manager = MagicMock()
    importer = ArtifactImporter(artifact_manager, collection_manager)
    # Structure validation is covered elsewhere; disable to isolate platform inference.
    importer._validate_artifact_structure = MagicMock(return_value=None)
    return importer, artifact_manager


def test_import_infers_codex_target_platform_from_local_profile_path() -> None:
    importer, artifact_manager = _build_importer()
    artifact = BulkImportArtifactData(
        source="local/test-skill",
        artifact_type="skill",
        name="test-skill",
        path="/tmp/my-project/.codex/skills/test-skill",
    )

    result = importer._import_single(artifact, collection_name="default")

    assert result.success is True
    kwargs = artifact_manager.add_from_local.call_args.kwargs
    assert kwargs["target_platforms"] == [Platform.CODEX]


def test_import_respects_explicit_target_platform_override() -> None:
    importer, artifact_manager = _build_importer()
    artifact = BulkImportArtifactData(
        source="local/test-skill",
        artifact_type="skill",
        name="test-skill",
        path="/tmp/my-project/.codex/skills/test-skill",
        target_platforms=["gemini"],
    )

    result = importer._import_single(artifact, collection_name="default")

    assert result.success is True
    kwargs = artifact_manager.add_from_local.call_args.kwargs
    assert kwargs["target_platforms"] == [Platform.GEMINI]


def test_import_leaves_target_platforms_unset_when_source_has_no_profile_hint() -> None:
    importer, artifact_manager = _build_importer()
    artifact = BulkImportArtifactData(
        source="anthropics/skills/test-skill@latest",
        artifact_type="skill",
        name="test-skill",
    )

    result = importer._import_single(artifact, collection_name="default")

    assert result.success is True
    kwargs = artifact_manager.add_from_github.call_args.kwargs
    assert kwargs["target_platforms"] is None
