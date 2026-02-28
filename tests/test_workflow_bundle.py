"""Tests for workflow bundle export and import (INT-7.1).

Covers:
- BundleBuilder.add_workflow() — packages YAML content into a bundle artifact
- BundleArtifact validation accepts the "workflow" type
- BundleImporter._import_workflow_artifact() — creates workflow via WorkflowService
- BundleImporter._detect_conflicts() — detects name collisions in DB
- Conflict resolution: skip, merge (overwrite), fork (rename)
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from skillmeat.core.artifact import ArtifactMetadata, ArtifactType
from skillmeat.core.sharing.bundle import BundleArtifact, BundleMetadata, Bundle
from skillmeat.core.sharing.builder import BundleBuilder, BundleValidationError
from skillmeat.core.sharing.importer import BundleImporter, ImportResult
from skillmeat.core.sharing.strategies import ConflictResolution


# ---------------------------------------------------------------------------
# YAML fixtures
# ---------------------------------------------------------------------------

_MINIMAL_WORKFLOW_YAML = """\
workflow:
  id: test-bundle-wf
  name: Test Bundle Workflow
  version: "1.0.0"
  description: Workflow for bundle testing
stages:
  - id: only-stage
    name: Only Stage
    type: agent
    roles:
      primary:
        artifact: "agent:python-backend-engineer"
        task: "Do something"
"""

_SECOND_WORKFLOW_YAML = """\
workflow:
  id: second-bundle-wf
  name: Second Bundle Workflow
  version: "2.0.0"
stages:
  - id: stage-a
    name: Stage A
    type: agent
    roles:
      primary:
        artifact: "agent:code-reviewer"
        task: "Review"
"""


# ===========================================================================
# BundleArtifact — model validation
# ===========================================================================


class TestBundleArtifactWorkflowType:
    """BundleArtifact should accept 'workflow' as a valid type."""

    def test_workflow_type_accepted(self):
        """Creating a BundleArtifact with type='workflow' must not raise."""
        artifact = BundleArtifact(
            type="workflow",
            name="my-workflow",
            version="1.0.0",
            scope="user",
            path="artifacts/workflow/my-workflow/",
            files=["WORKFLOW.yaml"],
            hash="sha256:" + "a" * 64,
        )
        assert artifact.type == "workflow"
        assert artifact.name == "my-workflow"

    def test_workflow_roundtrip_dict(self):
        """to_dict / from_dict must preserve all workflow artifact fields."""
        original = BundleArtifact(
            type="workflow",
            name="roundtrip-wf",
            version="1.2.3",
            scope="user",
            path="artifacts/workflow/roundtrip-wf/",
            files=["WORKFLOW.yaml"],
            hash="sha256:" + "b" * 64,
            metadata={"description": "A workflow", "content": "workflow:\n  id: x"},
        )
        restored = BundleArtifact.from_dict(original.to_dict())
        assert restored.type == original.type
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.files == original.files
        assert restored.hash == original.hash
        assert restored.metadata["description"] == "A workflow"


# ===========================================================================
# BundleBuilder.add_workflow()
# ===========================================================================


@pytest.fixture()
def builder(tmp_path):
    """Return a BundleBuilder with a mocked CollectionManager."""
    from skillmeat.core.collection import Collection

    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[],
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )

    with patch("skillmeat.core.sharing.builder.CollectionManager") as mock_cm_cls:
        mock_cm = mock_cm_cls.return_value
        mock_cm.load_collection.return_value = collection
        mock_cm.config.get_collection_path.return_value = tmp_path / "collection"

        yield BundleBuilder(
            name="test-bundle",
            description="Test bundle",
            author="test@example.com",
        )


class TestBundleBuilderAddWorkflow:
    """Tests for BundleBuilder.add_workflow()."""

    def test_add_workflow_creates_artifact(self, builder):
        """add_workflow() should add one BundleArtifact of type 'workflow'."""
        builder.add_workflow(
            workflow_name="my-workflow",
            yaml_content=_MINIMAL_WORKFLOW_YAML,
            version="1.0.0",
            description="My test workflow",
        )

        assert len(builder._artifacts) == 1
        artifact = builder._artifacts[0]
        assert artifact.type == ArtifactType.WORKFLOW.value
        assert artifact.name == "my-workflow"
        assert artifact.version == "1.0.0"
        assert artifact.files == ["WORKFLOW.yaml"]
        assert artifact.hash.startswith("sha256:")
        assert artifact.metadata["content"] == _MINIMAL_WORKFLOW_YAML
        assert artifact.metadata["description"] == "My test workflow"

    def test_add_workflow_path_format(self, builder):
        """Bundle path must follow the artifacts/workflow/<name>/ convention."""
        builder.add_workflow("pipe-wf", _MINIMAL_WORKFLOW_YAML)
        assert builder._artifacts[0].path == "artifacts/workflow/pipe-wf/"

    def test_add_workflow_hash_deterministic(self, builder):
        """Same YAML content must produce the same hash."""
        import hashlib

        builder.add_workflow("wf-a", _MINIMAL_WORKFLOW_YAML)
        expected = "sha256:" + hashlib.sha256(
            _MINIMAL_WORKFLOW_YAML.encode("utf-8")
        ).hexdigest()
        assert builder._artifacts[0].hash == expected

    def test_add_workflow_duplicate_raises(self, builder):
        """Adding the same workflow name twice must raise ValueError."""
        builder.add_workflow("dup-wf", _MINIMAL_WORKFLOW_YAML)
        with pytest.raises(ValueError, match="already added"):
            builder.add_workflow("dup-wf", _MINIMAL_WORKFLOW_YAML)

    def test_add_workflow_default_scope(self, builder):
        """Default scope for workflow artifacts is 'user'."""
        builder.add_workflow("scoped-wf", _MINIMAL_WORKFLOW_YAML)
        assert builder._artifacts[0].scope == "user"

    def test_add_workflow_custom_scope(self, builder):
        """custom_scope parameter must be honoured."""
        builder.add_workflow("local-wf", _MINIMAL_WORKFLOW_YAML, custom_scope="local")
        assert builder._artifacts[0].scope == "local"

    def test_add_multiple_workflows(self, builder):
        """Multiple workflows can coexist in the same builder."""
        builder.add_workflow("wf-1", _MINIMAL_WORKFLOW_YAML)
        builder.add_workflow("wf-2", _SECOND_WORKFLOW_YAML)
        assert len(builder._artifacts) == 2
        names = {a.name for a in builder._artifacts}
        assert names == {"wf-1", "wf-2"}

    def test_validate_bundle_workflow_content_required(self, builder):
        """_validate_bundle should raise if a workflow artifact has no content."""
        # Manually inject a workflow artifact without 'content' in metadata
        artifact = BundleArtifact(
            type="workflow",
            name="broken-wf",
            version="1.0.0",
            scope="user",
            path="artifacts/workflow/broken-wf/",
            files=["WORKFLOW.yaml"],
            hash="sha256:" + "c" * 64,
            metadata={},  # missing 'content'
        )
        builder._artifacts.append(artifact)
        builder._artifact_paths["workflow::broken-wf"] = None  # type: ignore[assignment]

        with pytest.raises(BundleValidationError, match="missing YAML content"):
            builder._validate_bundle()


# ===========================================================================
# BundleBuilder.build() — workflow written to ZIP
# ===========================================================================


class TestBundleBuilderBuildWorkflow:
    """Integration tests: build() must write WORKFLOW.yaml into the archive."""

    def test_build_writes_workflow_yaml(self, builder, tmp_path):
        """build() should produce a ZIP containing WORKFLOW.yaml for each workflow."""
        builder.add_workflow(
            workflow_name="zip-test-wf",
            yaml_content=_MINIMAL_WORKFLOW_YAML,
            version="1.0.0",
        )

        output = tmp_path / "test.skillmeat-pack"
        with patch("skillmeat.core.sharing.builder.ManifestValidator") as mock_mv:
            mock_mv.validate_manifest.return_value = Mock(valid=True, errors=[])
            bundle = builder.build(output, validate=False)

        assert output.exists()

        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "artifacts/workflow/zip-test-wf/WORKFLOW.yaml" in names

            # Verify YAML content is faithfully preserved
            stored = zf.read("artifacts/workflow/zip-test-wf/WORKFLOW.yaml").decode(
                "utf-8"
            )
            assert stored == _MINIMAL_WORKFLOW_YAML

    def test_build_manifest_contains_workflow_artifact(self, builder, tmp_path):
        """The manifest.json must list the workflow artifact with correct fields."""
        builder.add_workflow(
            workflow_name="manifest-wf",
            yaml_content=_MINIMAL_WORKFLOW_YAML,
            version="2.0.0",
        )

        output = tmp_path / "manifest-test.skillmeat-pack"
        with patch("skillmeat.core.sharing.builder.ManifestValidator") as mock_mv:
            mock_mv.validate_manifest.return_value = Mock(valid=True, errors=[])
            builder.build(output, validate=False)

        with zipfile.ZipFile(output, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        artifacts = manifest["artifacts"]
        assert len(artifacts) == 1
        art = artifacts[0]
        assert art["type"] == "workflow"
        assert art["name"] == "manifest-wf"
        assert art["version"] == "2.0.0"
        assert art["files"] == ["WORKFLOW.yaml"]


# ===========================================================================
# BundleImporter._import_workflow_artifact()
# ===========================================================================


def _make_bundle_zip(tmp_path: Path, workflow_name: str, yaml_content: str) -> Path:
    """Create a minimal .skillmeat-pack ZIP containing one workflow artifact."""
    bundle_path = tmp_path / f"{workflow_name}.skillmeat-pack"

    artifact_rel = f"artifacts/workflow/{workflow_name}/"
    manifest = {
        "version": "1.0",
        "name": "test-bundle",
        "description": "Test",
        "author": "test",
        "created_at": datetime.utcnow().isoformat(),
        "license": "MIT",
        "tags": [],
        "artifacts": [
            {
                "type": "workflow",
                "name": workflow_name,
                "version": "1.0.0",
                "scope": "user",
                "path": artifact_rel,
                "files": ["WORKFLOW.yaml"],
                "hash": "sha256:" + "d" * 64,
                "metadata": {},
            }
        ],
        "dependencies": [],
        "bundle_hash": "sha256:" + "e" * 64,
    }

    fixed = (2020, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(bundle_path, "w") as zf:
        # manifest.json
        zf.writestr(
            zipfile.ZipInfo("manifest.json", date_time=fixed),
            json.dumps(manifest),
        )
        # WORKFLOW.yaml
        zf.writestr(
            zipfile.ZipInfo(artifact_rel + "WORKFLOW.yaml", date_time=fixed),
            yaml_content,
        )

    return bundle_path


def _make_importer(tmp_path: Path) -> BundleImporter:
    """Return a BundleImporter with all heavy dependencies mocked out."""
    from skillmeat.core.collection import Collection

    collection = Collection(
        name="test",
        version="1.0.0",
        artifacts=[],
        created=datetime.utcnow(),
        updated=datetime.utcnow(),
    )

    # Use MagicMock (not Mock(spec=...)) so attribute chains work freely
    mock_cm = MagicMock()
    mock_cm.load_collection.return_value = collection
    mock_cm.config.get_collection_path.return_value = tmp_path / "collection"
    mock_cm.save_collection.return_value = None

    from skillmeat.core.sharing.validator import BundleValidator
    from skillmeat.utils.filesystem import FilesystemManager

    mock_am = MagicMock()
    mock_validator = MagicMock(spec=BundleValidator)
    mock_validator.validate.return_value = MagicMock(
        is_valid=True,
        has_warnings=Mock(return_value=False),
        get_errors=Mock(return_value=[]),
        get_warnings=Mock(return_value=[]),
        summary=Mock(return_value="OK"),
        bundle_hash="sha256:" + "e" * 64,
    )
    mock_fs = MagicMock(spec=FilesystemManager)

    importer = BundleImporter(
        collection_mgr=mock_cm,
        artifact_mgr=mock_am,
        validator=mock_validator,
        filesystem_mgr=mock_fs,
    )
    return importer


class TestBundleImporterWorkflowImport:
    """Tests for _import_workflow_artifact() in BundleImporter."""

    def test_import_workflow_calls_workflow_service(self, tmp_path):
        """_import_workflow_artifact should call WorkflowService.create()."""
        from skillmeat.core.workflow.service import WorkflowDTO

        mock_dto = Mock(spec=WorkflowDTO)
        mock_dto.id = "abc123"

        extract_dir = tmp_path / "extracted"
        artifact_rel = "artifacts/workflow/my-wf/"
        wf_dir = extract_dir / artifact_rel
        wf_dir.mkdir(parents=True)
        (wf_dir / "WORKFLOW.yaml").write_text(_MINIMAL_WORKFLOW_YAML, encoding="utf-8")

        importer = _make_importer(tmp_path)

        from rich.console import Console

        console = Console(quiet=True)
        artifact_data = {
            "type": "workflow",
            "name": "my-wf",
            "version": "1.0.0",
            "scope": "user",
            "path": artifact_rel,
            "files": ["WORKFLOW.yaml"],
            "hash": "sha256:" + "d" * 64,
        }

        with patch(
            "skillmeat.core.workflow.service.WorkflowService"
        ) as mock_svc_cls:
            mock_svc = mock_svc_cls.return_value
            mock_svc.create.return_value = mock_dto

            importer._import_workflow_artifact(artifact_data, extract_dir, console)

            mock_svc.create.assert_called_once_with(yaml_content=_MINIMAL_WORKFLOW_YAML)

    def test_import_workflow_missing_yaml_raises(self, tmp_path):
        """ValueError should be raised when WORKFLOW.yaml is absent from bundle."""
        extract_dir = tmp_path / "extracted"
        artifact_rel = "artifacts/workflow/missing-wf/"
        # Do NOT create the WORKFLOW.yaml
        (extract_dir / artifact_rel).mkdir(parents=True)

        importer = _make_importer(tmp_path)

        from rich.console import Console

        console = Console(quiet=True)
        artifact_data = {
            "type": "workflow",
            "name": "missing-wf",
            "path": artifact_rel,
        }

        with pytest.raises(ValueError, match="missing WORKFLOW.yaml"):
            importer._import_workflow_artifact(artifact_data, extract_dir, console)

    def test_import_workflow_invalid_yaml_raises(self, tmp_path):
        """ValueError should be raised when WORKFLOW.yaml content is invalid."""
        extract_dir = tmp_path / "extracted"
        artifact_rel = "artifacts/workflow/bad-wf/"
        wf_dir = extract_dir / artifact_rel
        wf_dir.mkdir(parents=True)
        (wf_dir / "WORKFLOW.yaml").write_text("this: is: not: valid: swdl:", encoding="utf-8")

        importer = _make_importer(tmp_path)

        from rich.console import Console
        from skillmeat.core.workflow.exceptions import WorkflowValidationError

        console = Console(quiet=True)
        artifact_data = {
            "type": "workflow",
            "name": "bad-wf",
            "path": artifact_rel,
        }

        with patch(
            "skillmeat.core.workflow.service.WorkflowService"
        ) as mock_svc_cls:
            mock_svc = mock_svc_cls.return_value
            mock_svc.create.side_effect = WorkflowValidationError("bad schema")

            with pytest.raises(ValueError, match="definition is invalid"):
                importer._import_workflow_artifact(artifact_data, extract_dir, console)


# ===========================================================================
# BundleImporter._detect_conflicts() — workflow conflict detection
# ===========================================================================


class TestBundleImporterDetectConflicts:
    """Tests for workflow conflict detection in _detect_conflicts()."""

    def test_no_conflict_when_workflow_absent(self, tmp_path):
        """When no matching workflow exists in DB, artifact goes to non_conflicts."""
        importer = _make_importer(tmp_path)

        from skillmeat.core.collection import Collection

        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )

        manifest_data = {
            "artifacts": [
                {
                    "type": "workflow",
                    "name": "brand-new-wf",
                    "version": "1.0.0",
                    "path": "artifacts/workflow/brand-new-wf/",
                    "files": ["WORKFLOW.yaml"],
                    "hash": "sha256:" + "f" * 64,
                }
            ]
        }

        # _find_existing_workflow returns None → no conflict
        with patch.object(importer, "_find_existing_workflow", return_value=None):
            conflicts, non_conflicts = importer._detect_conflicts(
                manifest_data, collection
            )

        assert len(conflicts) == 0
        assert len(non_conflicts) == 1
        assert non_conflicts[0]["name"] == "brand-new-wf"

    def test_conflict_when_workflow_exists(self, tmp_path):
        """When a matching workflow exists in DB, artifact goes to conflicts."""
        from skillmeat.core.workflow.service import WorkflowDTO

        existing_dto = Mock(spec=WorkflowDTO)
        existing_dto.name = "existing-wf"
        existing_dto.id = "wf-001"
        existing_dto.created_at = datetime.utcnow()

        importer = _make_importer(tmp_path)

        from skillmeat.core.collection import Collection

        collection = Collection(
            name="test",
            version="1.0.0",
            artifacts=[],
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        )

        manifest_data = {
            "artifacts": [
                {
                    "type": "workflow",
                    "name": "existing-wf",
                    "version": "1.0.0",
                    "path": "artifacts/workflow/existing-wf/",
                    "files": ["WORKFLOW.yaml"],
                    "hash": "sha256:" + "f" * 64,
                }
            ]
        }

        with patch.object(
            importer, "_find_existing_workflow", return_value=existing_dto
        ):
            conflicts, non_conflicts = importer._detect_conflicts(
                manifest_data, collection
            )

        assert len(conflicts) == 1
        assert len(non_conflicts) == 0
        # Synthetic Artifact should have WORKFLOW type and matching name
        synthetic, artifact_data = conflicts[0]
        assert synthetic.type == ArtifactType.WORKFLOW
        assert synthetic.name == "existing-wf"


# ===========================================================================
# Conflict resolution — skip / merge / fork
# ===========================================================================


class TestWorkflowConflictResolution:
    """Conflict resolution paths for workflow artifacts in _apply_conflict_resolution."""

    def _make_decision(self, resolution, artifact_name="existing-wf", new_name=None):
        from skillmeat.core.sharing.strategies import ConflictDecision

        decision = Mock(spec=ConflictDecision)
        decision.artifact_name = artifact_name
        decision.artifact_type = ArtifactType.WORKFLOW
        decision.resolution = resolution
        decision.new_name = new_name
        decision.reason = "test"
        return decision

    def _make_manifest_data(self, artifact_name: str) -> dict:
        return {
            "artifacts": [
                {
                    "type": "workflow",
                    "name": artifact_name,
                    "version": "1.0.0",
                    "path": f"artifacts/workflow/{artifact_name}/",
                    "files": ["WORKFLOW.yaml"],
                    "hash": "sha256:" + "a" * 64,
                }
            ]
        }

    def test_skip_increments_skipped_count(self, tmp_path):
        """SKIP resolution must increment result.skipped_count."""
        from rich.console import Console
        from skillmeat.core.collection import Collection
        from skillmeat.core.sharing.importer import ImportResult

        importer = _make_importer(tmp_path)
        collection = Collection("t", "1", [], datetime.utcnow(), datetime.utcnow())
        result = ImportResult(success=True)
        console = Console(quiet=True)

        decision = self._make_decision(ConflictResolution.SKIP)

        importer._apply_conflict_resolution(
            decision,
            self._make_manifest_data("existing-wf"),
            tmp_path / "bundle",
            collection,
            result,
            console,
        )

        assert result.skipped_count == 1
        assert result.artifacts[0].resolution == "skipped"

    def test_merge_deletes_existing_then_imports(self, tmp_path):
        """MERGE resolution must delete existing workflow and call create."""
        from rich.console import Console
        from skillmeat.core.collection import Collection
        from skillmeat.core.sharing.importer import ImportResult
        from skillmeat.core.workflow.service import WorkflowDTO

        existing_dto = Mock(spec=WorkflowDTO)
        existing_dto.name = "existing-wf"
        existing_dto.id = "old-id"
        existing_dto.created_at = datetime.utcnow()

        new_dto = Mock(spec=WorkflowDTO)
        new_dto.id = "new-id"

        # Prepare extracted bundle dir with WORKFLOW.yaml
        bundle_dir = tmp_path / "bundle"
        wf_dir = bundle_dir / "artifacts/workflow/existing-wf/"
        wf_dir.mkdir(parents=True)
        (wf_dir / "WORKFLOW.yaml").write_text(_MINIMAL_WORKFLOW_YAML, encoding="utf-8")

        importer = _make_importer(tmp_path)
        collection = Collection("t", "1", [], datetime.utcnow(), datetime.utcnow())
        result = ImportResult(success=True)
        console = Console(quiet=True)

        decision = self._make_decision(ConflictResolution.MERGE)

        with patch.object(
            importer, "_find_existing_workflow", return_value=existing_dto
        ):
            with patch(
                "skillmeat.core.workflow.service.WorkflowService"
            ) as mock_svc_cls:
                mock_svc = mock_svc_cls.return_value
                mock_svc.delete.return_value = None
                mock_svc.create.return_value = new_dto

                importer._apply_conflict_resolution(
                    decision,
                    self._make_manifest_data("existing-wf"),
                    bundle_dir,
                    collection,
                    result,
                    console,
                )

                mock_svc.delete.assert_called_once_with("old-id")
                mock_svc.create.assert_called_once()

        assert result.merged_count == 1
        assert result.artifacts[0].resolution == "merged"

    def test_fork_imports_with_new_name(self, tmp_path):
        """FORK resolution must import the workflow under a different name."""
        from rich.console import Console
        from skillmeat.core.collection import Collection
        from skillmeat.core.sharing.importer import ImportResult
        from skillmeat.core.workflow.service import WorkflowDTO

        new_dto = Mock(spec=WorkflowDTO)
        new_dto.id = "fork-id"

        bundle_dir = tmp_path / "bundle"
        # The FORK path rewrites artifact_data["name"] temporarily; the path
        # in the bundle still uses the original name
        original_name = "existing-wf"
        wf_dir = bundle_dir / f"artifacts/workflow/{original_name}/"
        wf_dir.mkdir(parents=True)
        (wf_dir / "WORKFLOW.yaml").write_text(_MINIMAL_WORKFLOW_YAML, encoding="utf-8")

        importer = _make_importer(tmp_path)
        collection = Collection("t", "1", [], datetime.utcnow(), datetime.utcnow())
        result = ImportResult(success=True)
        console = Console(quiet=True)

        forked_name = "existing-wf-copy"
        decision = self._make_decision(
            ConflictResolution.FORK, artifact_name=original_name, new_name=forked_name
        )

        with patch(
            "skillmeat.core.workflow.service.WorkflowService"
        ) as mock_svc_cls:
            mock_svc = mock_svc_cls.return_value
            mock_svc.create.return_value = new_dto

            importer._apply_conflict_resolution(
                decision,
                self._make_manifest_data(original_name),
                bundle_dir,
                collection,
                result,
                console,
            )

            mock_svc.create.assert_called_once()

        assert result.forked_count == 1
        forked = result.artifacts[0]
        assert forked.resolution == "forked"
        assert forked.new_name == forked_name
        assert forked.name == original_name
