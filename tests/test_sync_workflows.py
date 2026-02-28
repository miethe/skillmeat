"""Tests for workflow synchronization support in SyncManager.

Covers:
- _get_artifact_type_plural maps "workflow" to "workflows"
- _get_project_artifact_path resolves workflow YAML file path (not directory)
- _compute_content_hash works on single files (needed for workflows)
- update_deployment_metadata creates correct path entries for workflows
- _get_collection_artifacts discovers workflow YAML files
- sync_workflows_with_db: create / update / delete / unchanged / error cases
"""

import hashlib
import textwrap
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from skillmeat.core.sync import SyncManager


# ---------------------------------------------------------------------------
# Minimal valid SWDL workflow YAML
# ---------------------------------------------------------------------------

_MINIMAL_WORKFLOW = textwrap.dedent(
    """\
    workflow:
      id: test-workflow
      name: Test Workflow
      version: "1.0.0"
    stages:
      - id: stage-1
        name: Stage One
        type: agent
        roles:
          primary:
            artifact: "agent:my-agent"
    """
)

_UPDATED_WORKFLOW = textwrap.dedent(
    """\
    workflow:
      id: test-workflow
      name: Test Workflow Updated
      version: "1.1.0"
    stages:
      - id: stage-1
        name: Stage One Updated
        type: agent
        roles:
          primary:
            artifact: "agent:my-agent"
    """
)

_SECOND_WORKFLOW = textwrap.dedent(
    """\
    workflow:
      id: second-workflow
      name: Second Workflow
      version: "1.0.0"
    stages:
      - id: step-1
        name: Step One
        type: agent
        roles:
          primary:
            artifact: "agent:other-agent"
    """
)

_INVALID_YAML = "this: is: not: valid: yaml: :\n  bad indent"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sync_mgr():
    """SyncManager without any collection/artifact managers."""
    return SyncManager()


@pytest.fixture
def collection_path(tmp_path) -> Path:
    """A minimal collection directory with a workflows/ sub-directory."""
    coll = tmp_path / "collection"
    (coll / "workflows").mkdir(parents=True)
    return coll


@pytest.fixture
def mock_collection_mgr(collection_path):
    """Mock collection manager that returns collection_path."""
    config = MagicMock()
    config.get_collection_path.return_value = collection_path

    mgr = MagicMock()
    mgr.config = config
    mgr.get_active_collection.return_value = MagicMock(name="default")
    return mgr


@pytest.fixture
def sync_mgr_with_collection(mock_collection_mgr):
    """SyncManager wired with a mock collection manager."""
    return SyncManager(collection_manager=mock_collection_mgr)


# ---------------------------------------------------------------------------
# _get_artifact_type_plural
# ---------------------------------------------------------------------------


class TestGetArtifactTypePlural:
    """'workflow' maps to 'workflows'; existing types are unchanged."""

    def test_workflow_maps_to_workflows(self, sync_mgr):
        assert sync_mgr._get_artifact_type_plural("workflow") == "workflows"

    def test_existing_types_unchanged(self, sync_mgr):
        assert sync_mgr._get_artifact_type_plural("skill") == "skills"
        assert sync_mgr._get_artifact_type_plural("command") == "commands"
        assert sync_mgr._get_artifact_type_plural("agent") == "agents"
        assert sync_mgr._get_artifact_type_plural("hook") == "hooks"
        assert sync_mgr._get_artifact_type_plural("mcp") == "mcps"
        assert sync_mgr._get_artifact_type_plural("plugin") == "plugins"
        assert sync_mgr._get_artifact_type_plural("composite") == "plugins"


# ---------------------------------------------------------------------------
# _get_project_artifact_path
# ---------------------------------------------------------------------------


class TestGetProjectArtifactPath:
    """Workflow paths resolve to YAML files, not directories."""

    def test_workflow_returns_yaml_path(self, tmp_path, sync_mgr):
        project_path = tmp_path / "project"
        wf_dir = project_path / ".claude" / "workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "my-workflow.yaml"
        wf_file.write_text(_MINIMAL_WORKFLOW)

        result = sync_mgr._get_project_artifact_path(project_path, "my-workflow", "workflow")
        assert result == wf_file

    def test_workflow_returns_none_when_missing(self, tmp_path, sync_mgr):
        project_path = tmp_path / "project"
        (project_path / ".claude" / "workflows").mkdir(parents=True)

        result = sync_mgr._get_project_artifact_path(project_path, "missing-wf", "workflow")
        assert result is None

    def test_non_workflow_returns_directory(self, tmp_path, sync_mgr):
        project_path = tmp_path / "project"
        skill_dir = project_path / ".claude" / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)

        result = sync_mgr._get_project_artifact_path(project_path, "my-skill", "skill")
        assert result == skill_dir
        assert result.is_dir()


# ---------------------------------------------------------------------------
# _compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    """_compute_content_hash works for both files and directories."""

    def test_hashes_single_file(self, tmp_path, sync_mgr):
        f = tmp_path / "test.yaml"
        f.write_text("hello: world\n")
        expected = hashlib.sha256(b"hello: world\n").hexdigest()
        assert sync_mgr._compute_content_hash(f) == expected

    def test_hashes_directory(self, tmp_path, sync_mgr):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "SKILL.md").write_text("# Skill\n")
        # Should not raise; result is a hex string
        result = sync_mgr._compute_content_hash(d)
        assert isinstance(result, str) and len(result) == 64

    def test_raises_for_nonexistent_path(self, tmp_path, sync_mgr):
        with pytest.raises(ValueError, match="does not exist"):
            sync_mgr._compute_content_hash(tmp_path / "nonexistent.yaml")

    def test_same_content_same_hash(self, tmp_path, sync_mgr):
        f1 = tmp_path / "a.yaml"
        f2 = tmp_path / "b.yaml"
        content = b"workflow:\n  id: wf\n"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert sync_mgr._compute_content_hash(f1) == sync_mgr._compute_content_hash(f2)

    def test_different_content_different_hash(self, tmp_path, sync_mgr):
        f1 = tmp_path / "a.yaml"
        f2 = tmp_path / "b.yaml"
        f1.write_text("version: 1\n")
        f2.write_text("version: 2\n")
        assert sync_mgr._compute_content_hash(f1) != sync_mgr._compute_content_hash(f2)


# ---------------------------------------------------------------------------
# update_deployment_metadata — workflow type
# ---------------------------------------------------------------------------


class TestWorkflowDeploymentMetadata:
    """Workflow deployment creates the correct TOML entry."""

    def test_update_deployment_metadata_workflow(self, tmp_path, sync_mgr):
        project_path = tmp_path / "project"
        (project_path / ".claude").mkdir(parents=True)

        collection_path = tmp_path / "collection"
        wf_dir = collection_path / "workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "my-workflow.yaml"
        wf_file.write_text(_MINIMAL_WORKFLOW)

        sync_mgr.update_deployment_metadata(
            project_path=project_path,
            artifact_name="my-workflow",
            artifact_type="workflow",
            collection_path=collection_path,
            collection_name="default",
        )

        deployed_file = project_path / ".claude" / ".skillmeat-deployed.toml"
        assert deployed_file.exists(), "Deployment metadata file should be created"

        content = deployed_file.read_text()
        assert "my-workflow" in content
        assert "workflow" in content
        # artifact_path inside .claude/ should reference the YAML file
        assert "workflows/my-workflow.yaml" in content

    def test_update_deployment_metadata_workflow_raises_when_missing(
        self, tmp_path, sync_mgr
    ):
        project_path = tmp_path / "project"
        (project_path / ".claude").mkdir(parents=True)

        collection_path = tmp_path / "collection"
        (collection_path / "workflows").mkdir(parents=True)
        # Do NOT create the YAML file

        with pytest.raises(ValueError, match="does not exist"):
            sync_mgr.update_deployment_metadata(
                project_path=project_path,
                artifact_name="missing-workflow",
                artifact_type="workflow",
                collection_path=collection_path,
                collection_name="default",
            )


# ---------------------------------------------------------------------------
# _get_collection_artifacts — workflow discovery
# ---------------------------------------------------------------------------


class TestGetCollectionArtifactsWorkflows:
    """_get_collection_artifacts discovers workflow YAML files from the collection."""

    def _make_sync_mgr_with_collection(self, collection_path: Path) -> SyncManager:
        config = MagicMock()
        config.get_collection_path.return_value = collection_path

        mgr = MagicMock()
        mgr.config = config
        mgr.load_collection.return_value = MagicMock()

        return SyncManager(collection_manager=mgr)

    def test_discovers_yaml_workflow(self, tmp_path):
        coll_path = tmp_path / "collection"
        wf_dir = coll_path / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "my-workflow.yaml").write_text(_MINIMAL_WORKFLOW)

        sync_mgr = self._make_sync_mgr_with_collection(coll_path)
        artifacts = sync_mgr._get_collection_artifacts("default")

        wf_artifacts = [a for a in artifacts if a["type"] == "workflow"]
        assert len(wf_artifacts) == 1
        assert wf_artifacts[0]["name"] == "my-workflow"
        assert wf_artifacts[0]["path"].name == "my-workflow.yaml"

    def test_discovers_yml_extension(self, tmp_path):
        coll_path = tmp_path / "collection"
        wf_dir = coll_path / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "other.yml").write_text(_MINIMAL_WORKFLOW)

        sync_mgr = self._make_sync_mgr_with_collection(coll_path)
        artifacts = sync_mgr._get_collection_artifacts("default")

        wf_artifacts = [a for a in artifacts if a["type"] == "workflow"]
        assert len(wf_artifacts) == 1
        assert wf_artifacts[0]["name"] == "other"

    def test_ignores_non_yaml_files(self, tmp_path):
        coll_path = tmp_path / "collection"
        wf_dir = coll_path / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "readme.md").write_text("# Workflows\n")
        (wf_dir / "valid.yaml").write_text(_MINIMAL_WORKFLOW)

        sync_mgr = self._make_sync_mgr_with_collection(coll_path)
        artifacts = sync_mgr._get_collection_artifacts("default")

        wf_names = [a["name"] for a in artifacts if a["type"] == "workflow"]
        assert "readme" not in wf_names
        assert "valid" in wf_names

    def test_no_workflows_dir_returns_empty_for_workflows(self, tmp_path):
        coll_path = tmp_path / "collection"
        coll_path.mkdir()
        # No workflows/ directory

        sync_mgr = self._make_sync_mgr_with_collection(coll_path)
        artifacts = sync_mgr._get_collection_artifacts("default")

        wf_artifacts = [a for a in artifacts if a["type"] == "workflow"]
        assert wf_artifacts == []

    def test_discovers_multiple_workflows(self, tmp_path):
        coll_path = tmp_path / "collection"
        wf_dir = coll_path / "workflows"
        wf_dir.mkdir(parents=True)
        (wf_dir / "alpha.yaml").write_text(_MINIMAL_WORKFLOW)
        (wf_dir / "beta.yaml").write_text(_SECOND_WORKFLOW)

        sync_mgr = self._make_sync_mgr_with_collection(coll_path)
        artifacts = sync_mgr._get_collection_artifacts("default")

        wf_names = sorted(a["name"] for a in artifacts if a["type"] == "workflow")
        assert wf_names == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# sync_workflows_with_db
# ---------------------------------------------------------------------------


class TestSyncWorkflowsWithDb:
    """sync_workflows_with_db reconciles filesystem workflows with the DB cache."""

    def _write_wf(self, workflows_dir: Path, name: str, content: str) -> Path:
        f = workflows_dir / f"{name}.yaml"
        f.write_text(content)
        return f

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_new_workflow(self, tmp_path, sync_mgr_with_collection, collection_path):
        """A YAML file not in the DB results in WorkflowService.create()."""
        workflows_dir = collection_path / "workflows"
        self._write_wf(workflows_dir, "test-workflow", _MINIMAL_WORKFLOW)

        created_dto = MagicMock()
        created_dto.id = "abc123"
        created_dto.name = "Test Workflow"

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = []
            instance.create.return_value = created_dto

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        instance.create.assert_called_once()
        assert "test-workflow" in result["created"]
        assert result["errors"] == {}
        assert result["updated"] == []
        assert result["deleted"] == []

    # ------------------------------------------------------------------
    # unchanged
    # ------------------------------------------------------------------

    def test_unchanged_workflow_not_updated(
        self, tmp_path, sync_mgr_with_collection, collection_path
    ):
        """A YAML file whose hash matches the DB row is not re-uploaded."""
        workflows_dir = collection_path / "workflows"
        self._write_wf(workflows_dir, "my-wf", _MINIMAL_WORKFLOW)

        existing_dto = MagicMock()
        existing_dto.id = "existing-id"
        existing_dto.name = "my-wf"
        # definition must match the on-disk content exactly for hash equality
        existing_dto.definition = _MINIMAL_WORKFLOW

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = [existing_dto]

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        instance.update.assert_not_called()
        assert "my-wf" in result["unchanged"]
        assert result["errors"] == {}

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_changed_workflow(
        self, tmp_path, sync_mgr_with_collection, collection_path
    ):
        """A YAML file whose hash differs from the DB row triggers an update."""
        workflows_dir = collection_path / "workflows"
        self._write_wf(workflows_dir, "my-wf", _UPDATED_WORKFLOW)

        existing_dto = MagicMock()
        existing_dto.id = "existing-id"
        existing_dto.name = "my-wf"
        # DB has the OLD definition — hashes will differ
        existing_dto.definition = _MINIMAL_WORKFLOW

        updated_dto = MagicMock()
        updated_dto.id = "existing-id"
        updated_dto.name = "my-wf"

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = [existing_dto]
            instance.update.return_value = updated_dto

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        instance.update.assert_called_once_with("existing-id", _UPDATED_WORKFLOW)
        assert "my-wf" in result["updated"]
        assert result["errors"] == {}

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    def test_delete_removed_workflow(
        self, tmp_path, sync_mgr_with_collection, collection_path
    ):
        """A DB row whose name has no on-disk YAML is deleted."""
        # No YAML files on disk

        stale_dto = MagicMock()
        stale_dto.id = "stale-id"
        stale_dto.name = "stale-workflow"
        stale_dto.definition = _MINIMAL_WORKFLOW

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = [stale_dto]

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        instance.delete.assert_called_once_with("stale-id")
        assert "stale-workflow" in result["deleted"]
        assert result["errors"] == {}

    # ------------------------------------------------------------------
    # error handling — invalid YAML
    # ------------------------------------------------------------------

    def test_invalid_yaml_recorded_as_error(
        self, tmp_path, sync_mgr_with_collection, collection_path
    ):
        """A workflow file that fails parse/validation is recorded in errors."""
        from skillmeat.core.workflow.exceptions import WorkflowParseError

        workflows_dir = collection_path / "workflows"
        self._write_wf(workflows_dir, "bad-wf", _INVALID_YAML)

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = []
            instance.create.side_effect = WorkflowParseError("bad YAML")

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        assert "bad-wf" in result["errors"]
        assert result["created"] == []

    # ------------------------------------------------------------------
    # mixed scenario
    # ------------------------------------------------------------------

    def test_mixed_create_update_delete_unchanged(
        self, tmp_path, sync_mgr_with_collection, collection_path
    ):
        """Full reconciliation: one of each outcome."""
        workflows_dir = collection_path / "workflows"

        # On disk: "new-wf" (new), "keep-wf" (unchanged), "changed-wf" (updated)
        self._write_wf(workflows_dir, "new-wf", _MINIMAL_WORKFLOW)
        self._write_wf(workflows_dir, "keep-wf", _MINIMAL_WORKFLOW)
        self._write_wf(workflows_dir, "changed-wf", _UPDATED_WORKFLOW)
        # "stale-wf" exists in DB but NOT on disk → delete

        keep_dto = MagicMock()
        keep_dto.id = "keep-id"
        keep_dto.name = "keep-wf"
        keep_dto.definition = _MINIMAL_WORKFLOW  # same as disk

        changed_dto = MagicMock()
        changed_dto.id = "changed-id"
        changed_dto.name = "changed-wf"
        changed_dto.definition = _MINIMAL_WORKFLOW  # different from disk (_UPDATED_WORKFLOW)

        stale_dto = MagicMock()
        stale_dto.id = "stale-id"
        stale_dto.name = "stale-wf"
        stale_dto.definition = _MINIMAL_WORKFLOW

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = [keep_dto, changed_dto, stale_dto]
            instance.create.return_value = MagicMock(id="new-id", name="new-wf")
            instance.update.return_value = MagicMock(id="changed-id", name="changed-wf")

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        assert result["created"] == ["new-wf"]
        assert result["updated"] == ["changed-wf"]
        assert result["deleted"] == ["stale-wf"]
        assert result["unchanged"] == ["keep-wf"]
        assert result["errors"] == {}

    # ------------------------------------------------------------------
    # no collection manager
    # ------------------------------------------------------------------

    def test_raises_without_collection_manager(self, sync_mgr):
        with pytest.raises(ValueError, match="collection manager"):
            sync_mgr.sync_workflows_with_db(collection_name="default")

    # ------------------------------------------------------------------
    # empty workflows directory
    # ------------------------------------------------------------------

    def test_no_workflows_directory_deletes_db_rows(
        self, tmp_path, sync_mgr_with_collection, collection_path
    ):
        """If there's no workflows/ dir, all DB rows are deleted."""
        # Remove the workflows dir created by the fixture
        import shutil
        shutil.rmtree(collection_path / "workflows")

        stale_dto = MagicMock()
        stale_dto.id = "stale-id"
        stale_dto.name = "stale-wf"
        stale_dto.definition = _MINIMAL_WORKFLOW

        with patch(
            "skillmeat.core.workflow.service.WorkflowService", autospec=True
        ) as MockSvc:
            instance = MockSvc.return_value
            instance.list.return_value = [stale_dto]

            result = sync_mgr_with_collection.sync_workflows_with_db(
                collection_name="default"
            )

        assert "stale-wf" in result["deleted"]
        assert result["created"] == []
        assert result["errors"] == {}
