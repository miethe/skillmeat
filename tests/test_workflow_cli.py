"""Unit tests for the ``skillmeat workflow`` CLI command group.

Covers all 9 subcommands — create, list, show, validate, plan, run, runs,
approve, cancel — using Click's CliRunner and unittest.mock for complete
service isolation.  No filesystem I/O or database connections are made.

Because workflow.py uses *lazy imports* inside each command function body,
we patch at the canonical module path rather than in the cli.workflow
namespace (the attribute does not exist at import time):

  skillmeat.core.workflow.service.WorkflowService
  skillmeat.core.workflow.execution_service.WorkflowExecutionService
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skillmeat.cli import main

# ---------------------------------------------------------------------------
# Module-level patch targets (lazy-import guard)
# ---------------------------------------------------------------------------

_SVC = "skillmeat.core.workflow.service.WorkflowService"
_EXEC_SVC = "skillmeat.core.workflow.execution_service.WorkflowExecutionService"
_COLLECTION_MGR = "skillmeat.core.collection.CollectionManager"
_FORMAT_SECONDS = "skillmeat.core.workflow.planner._format_seconds"

RUNNER = CliRunner()


# ---------------------------------------------------------------------------
# Shared factory helpers
# ---------------------------------------------------------------------------

def _make_workflow_dto(
    name: str = "my-workflow",
    workflow_id: str = "wf-uuid-1234",
    version: str = "1.0.0",
    status: str = "active",
    tags: list | None = None,
    stages: list | None = None,
    description: str | None = None,
    project_id: str | None = "default",
) -> MagicMock:
    dto = MagicMock()
    dto.id = workflow_id
    dto.name = name
    dto.version = version
    dto.status = status
    dto.tags = tags or []
    dto.stages = stages or []
    dto.description = description
    dto.project_id = project_id
    dto.created_at = datetime(2025, 1, 1, 12, 0)
    dto.updated_at = datetime(2025, 6, 1, 12, 0)
    return dto


def _make_stage_dto(
    name: str = "stage-1",
    stage_type: str = "agent",
    order_index: int = 0,
    depends_on: list | None = None,
    roles: dict | None = None,
) -> MagicMock:
    stage = MagicMock()
    stage.name = name
    stage.stage_type = stage_type
    stage.order_index = order_index
    stage.depends_on = depends_on or []
    stage.roles = roles or {}
    return stage


def _make_execution_dto(
    execution_id: str = "exec-uuid-abcd",
    workflow_id: str = "wf-uuid-1234",
    status: str = "completed",
    steps: list | None = None,
    parameters: dict | None = None,
    error_message: str | None = None,
) -> MagicMock:
    dto = MagicMock()
    dto.id = execution_id
    dto.workflow_id = workflow_id
    dto.status = status
    dto.steps = steps or []
    dto.parameters = parameters or {}
    dto.error_message = error_message
    dto.started_at = datetime(2025, 6, 1, 10, 0)
    dto.completed_at = datetime(2025, 6, 1, 10, 5)
    return dto


def _make_step_dto(
    stage_id: str = "stage-1",
    stage_name: str = "Stage One",
    stage_type: str = "agent",
    status: str = "completed",
    batch_index: int = 0,
    error_message: str | None = None,
    output: dict | None = None,
) -> MagicMock:
    step = MagicMock()
    step.stage_id = stage_id
    step.stage_name = stage_name
    step.stage_type = stage_type
    step.status = status
    step.batch_index = batch_index
    step.error_message = error_message
    step.output = output or {}
    step.started_at = datetime(2025, 6, 1, 10, 0)
    step.completed_at = datetime(2025, 6, 1, 10, 1)
    return step


def _make_validation_result(
    valid: bool = True,
    errors: list | None = None,
    warnings: list | None = None,
) -> MagicMock:
    result = MagicMock()
    result.valid = valid
    result.errors = errors or []
    result.warnings = warnings or []
    return result


def _make_plan(
    workflow_name: str = "my-workflow",
    workflow_version: str = "1.0.0",
    batches: list | None = None,
    parameters: dict | None = None,
    estimated_timeout_seconds: int = 60,
) -> MagicMock:
    plan = MagicMock()
    plan.workflow_name = workflow_name
    plan.workflow_version = workflow_version
    plan.batches = batches or []
    plan.parameters = parameters or {}
    plan.estimated_timeout_seconds = estimated_timeout_seconds
    plan.validation = _make_validation_result()
    return plan


def _make_plan_batch(index: int = 0, stages: list | None = None) -> MagicMock:
    batch = MagicMock()
    batch.index = index
    batch.stages = stages or []
    return batch


def _make_plan_stage(
    name: str = "stage-1",
    stage_id: str = "stage-1",
    stage_type: str = "agent",
    depends_on: list | None = None,
    primary_artifact: str | None = "my-agent",
    model: str | None = None,
    tools: list | None = None,
    inputs: dict | None = None,
    outputs: list | None = None,
    context_modules: list | None = None,
    condition: str | None = None,
    timeout: str | None = None,
    gate_approvers: list | None = None,
    gate_timeout: str | None = None,
) -> MagicMock:
    ps = MagicMock()
    ps.name = name
    ps.stage_id = stage_id
    ps.stage_type = stage_type
    ps.depends_on = depends_on or []
    ps.primary_artifact = primary_artifact
    ps.model = model
    ps.tools = tools or []
    ps.inputs = inputs or {}
    ps.outputs = outputs or []
    ps.context_modules = context_modules or []
    ps.condition = condition
    ps.timeout = timeout
    ps.gate_approvers = gate_approvers or []
    ps.gate_timeout = gate_timeout
    return ps


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestWorkflowCreate:
    """Tests for ``skillmeat workflow create``."""

    def test_create_success(self, tmp_path):
        """Happy-path: valid YAML, no existing workflow → success message."""
        yaml_content = (
            "workflow:\n"
            "  id: test-wf\n"
            "  name: My Workflow\n"
            "  version: 1.0.0\n"
            "stages: []\n"
        )
        yaml_file = tmp_path / "workflow.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        MockSvc = MagicMock()
        svc_instance = MockSvc.return_value
        svc_instance.validate.return_value = _make_validation_result(valid=True)
        svc_instance.list.return_value = []
        svc_instance.create.return_value = _make_workflow_dto(name="my-workflow")

        collection = MagicMock()
        collection.name = "default"
        collection.find_artifact.return_value = None
        MockCM = MagicMock()
        MockCM.return_value.load_collection.return_value = collection
        MockCM.return_value.config.get_collection_path.return_value = tmp_path

        with patch(_SVC, MockSvc), patch(_COLLECTION_MGR, MockCM):
            result = RUNNER.invoke(main, ["workflow", "create", str(yaml_file)])

        assert result.exit_code == 0, result.output
        assert "imported successfully" in result.output.lower()

    def test_create_file_not_found(self):
        """Non-existent file path → non-zero exit (Click rejects before our code)."""
        result = RUNNER.invoke(main, ["workflow", "create", "/nonexistent/path.yaml"])
        assert result.exit_code != 0

    def test_create_validation_error(self, tmp_path):
        """Validation fails → exit 1, error message printed."""
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("workflow:\n  id: bad\n", encoding="utf-8")

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(
            valid=False, errors=["Missing required field: stages"]
        )

        collection = MagicMock()
        collection.name = "default"
        MockCM = MagicMock()
        MockCM.return_value.load_collection.return_value = collection
        MockCM.return_value.config.get_collection_path.return_value = tmp_path

        with patch(_SVC, MockSvc), patch(_COLLECTION_MGR, MockCM):
            result = RUNNER.invoke(main, ["workflow", "create", str(yaml_file)])

        assert result.exit_code == 1
        assert "validation failed" in result.output.lower()

    def test_create_duplicate_no_force(self, tmp_path):
        """DB duplicate detected (no --force) → exit 1 with already-exists message.

        We use the DB-level duplicate path: svc.list() returns a workflow with
        the same name so the CLI prints the duplicate error before touching FS.
        """
        yaml_file = tmp_path / "workflow.yaml"
        # Use workflow name "my-workflow" so fs_name == "my-workflow" matches dto.name
        yaml_file.write_text(
            "workflow:\n  id: my-wf\n  name: my-workflow\n  version: 1.0.0\nstages: []\n",
            encoding="utf-8",
        )

        existing_dto = _make_workflow_dto(name="my-workflow")

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(valid=True)
        # Returning existing_dto causes the 'existing_dto is not None' branch without --force
        MockSvc.return_value.list.return_value = [existing_dto]

        collection = MagicMock()
        collection.name = "default"
        collection.find_artifact.return_value = None
        MockCM = MagicMock()
        MockCM.return_value.load_collection.return_value = collection
        MockCM.return_value.config.get_collection_path.return_value = tmp_path

        with patch(_SVC, MockSvc), patch(_COLLECTION_MGR, MockCM):
            result = RUNNER.invoke(main, ["workflow", "create", str(yaml_file)])

        assert result.exit_code == 1
        assert "--force" in result.output or "already exists" in result.output.lower()

    def test_create_duplicate_with_force(self, tmp_path):
        """Existing workflow + --force → success, svc.update() called."""
        yaml_file = tmp_path / "workflow.yaml"
        # workflow name "my-workflow" so fs_name matches dto.name
        yaml_file.write_text(
            "workflow:\n  id: my-wf\n  name: my-workflow\n  version: 1.0.0\nstages: []\n",
            encoding="utf-8",
        )
        existing_dto = _make_workflow_dto(name="my-workflow")
        updated_dto = _make_workflow_dto(name="my-workflow", workflow_id="wf-updated")

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(valid=True)
        MockSvc.return_value.list.return_value = [existing_dto]
        MockSvc.return_value.update.return_value = updated_dto

        collection = MagicMock()
        collection.name = "default"
        collection.find_artifact.return_value = None
        MockCM = MagicMock()
        MockCM.return_value.load_collection.return_value = collection
        MockCM.return_value.config.get_collection_path.return_value = tmp_path

        with patch(_SVC, MockSvc), patch(_COLLECTION_MGR, MockCM):
            result = RUNNER.invoke(
                main, ["workflow", "create", str(yaml_file), "--force"]
            )

        assert result.exit_code == 0, result.output
        MockSvc.return_value.update.assert_called_once()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestWorkflowList:
    """Tests for ``skillmeat workflow list``."""

    def test_list_empty(self):
        """No workflows → prints empty-state message, exit 0."""
        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = []

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "list"])

        assert result.exit_code == 0
        assert "No workflows" in result.output

    def test_list_with_items(self):
        """Workflows present → table contains workflow names."""
        wf1 = _make_workflow_dto(name="workflow-alpha", status="active")
        wf2 = _make_workflow_dto(
            name="workflow-beta", status="draft", workflow_id="wf-2"
        )

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf1, wf2]

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "list"])

        assert result.exit_code == 0
        assert "workflow-alpha" in result.output
        assert "workflow-beta" in result.output

    def test_list_format_json(self):
        """--format json → output contains workflow name as JSON."""
        wf = _make_workflow_dto(name="json-wf")
        wf.stages = [_make_stage_dto()]

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "list", "--format", "json"])

        assert result.exit_code == 0
        assert "json-wf" in result.output
        assert '"name"' in result.output

    def test_list_status_filter(self):
        """--status active shows active workflows, hides others."""
        active_wf = _make_workflow_dto(name="active-wf", status="active")
        draft_wf = _make_workflow_dto(
            name="draft-wf", status="draft", workflow_id="wf-2"
        )

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [active_wf, draft_wf]

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "list", "--status", "active"])

        assert result.exit_code == 0
        assert "active-wf" in result.output
        assert "draft-wf" not in result.output

    def test_list_tag_filter(self):
        """--tag ci shows only workflows tagged 'ci'."""
        ci_wf = _make_workflow_dto(name="ci-wf", tags=["ci", "test"])
        other_wf = _make_workflow_dto(
            name="other-wf", tags=["deploy"], workflow_id="wf-2"
        )

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [ci_wf, other_wf]

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "list", "--tag", "ci"])

        assert result.exit_code == 0
        assert "ci-wf" in result.output
        assert "other-wf" not in result.output

    def test_list_filter_no_match_shows_message(self):
        """Filter returning zero results → descriptive empty-state message."""
        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = []

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(
                main, ["workflow", "list", "--status", "archived"]
            )

        assert result.exit_code == 0
        assert "No workflows" in result.output


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


class TestWorkflowShow:
    """Tests for ``skillmeat workflow show``."""

    def test_show_found(self):
        """Workflow found → metadata panel and stage table printed."""
        stage = _make_stage_dto(name="build", stage_type="agent")
        wf = _make_workflow_dto(name="my-workflow", stages=[stage])

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.list_executions.return_value = []

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "show", "my-workflow"])

        assert result.exit_code == 0
        assert "my-workflow" in result.output
        assert "build" in result.output

    def test_show_not_found(self):
        """Workflow not found → exit 1 with error message."""
        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = []

        MockExecSvc = MagicMock()

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "show", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_show_with_execution_history(self):
        """Workflow with a recent execution → 'Last Execution' panel shown."""
        wf = _make_workflow_dto(name="my-workflow", workflow_id="wf-1")
        exec_dto = _make_execution_dto(status="completed")

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.list_executions.return_value = [exec_dto]

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "show", "my-workflow"])

        assert result.exit_code == 0
        assert "Last Execution" in result.output

    def test_show_no_stages(self):
        """Workflow with empty stages → 'No stages defined' message."""
        wf = _make_workflow_dto(name="empty-wf", stages=[])

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.list_executions.return_value = []

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "show", "empty-wf"])

        assert result.exit_code == 0
        assert "No stages" in result.output


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestWorkflowValidate:
    """Tests for ``skillmeat workflow validate``."""

    def test_validate_valid_yaml(self, tmp_path):
        """Valid YAML → exit 0 and 'Valid workflow' message."""
        yaml_file = tmp_path / "good.yaml"
        yaml_file.write_text(
            "workflow:\n  id: good-wf\n  name: Good\nstages: []\n",
            encoding="utf-8",
        )

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(valid=True)

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "validate", str(yaml_file)])

        assert result.exit_code == 0
        assert "Valid workflow" in result.output

    def test_validate_invalid_yaml(self, tmp_path):
        """Validation errors → exit 1 and failure message."""
        yaml_file = tmp_path / "bad.yaml"
        yaml_file.write_text("workflow:\n  id: bad\n", encoding="utf-8")

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(
            valid=False, errors=["stages field is required"]
        )

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "validate", str(yaml_file)])

        assert result.exit_code == 1
        assert "validation failed" in result.output.lower()

    def test_validate_strict_with_warnings(self, tmp_path):
        """--strict promotes warnings to errors → exit 1."""
        yaml_file = tmp_path / "warn.yaml"
        yaml_file.write_text(
            "workflow:\n  id: warn-wf\n  name: Warn\nstages: []\n",
            encoding="utf-8",
        )

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(
            valid=True, warnings=["No stages defined — workflow will do nothing"]
        )

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(
                main, ["workflow", "validate", str(yaml_file), "--strict"]
            )

        assert result.exit_code == 1
        assert "treated as errors" in result.output

    def test_validate_warnings_without_strict_passes(self, tmp_path):
        """Warnings without --strict → exit 0."""
        yaml_file = tmp_path / "warn.yaml"
        yaml_file.write_text(
            "workflow:\n  id: warn-wf\n  name: Warn\nstages: []\n",
            encoding="utf-8",
        )

        MockSvc = MagicMock()
        MockSvc.return_value.validate.return_value = _make_validation_result(
            valid=True, warnings=["No stages defined"]
        )

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "validate", str(yaml_file)])

        assert result.exit_code == 0
        assert "Valid workflow" in result.output


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


class TestWorkflowPlan:
    """Tests for ``skillmeat workflow plan``."""

    def test_plan_success(self):
        """Workflow found + plan generated → 'Execution Plan' output, exit 0."""
        wf = _make_workflow_dto(name="my-workflow")
        ps = _make_plan_stage(name="build")
        batch = _make_plan_batch(index=0, stages=[ps])
        plan = _make_plan(workflow_name="my-workflow", batches=[batch])

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]
        MockSvc.return_value.plan.return_value = plan

        with patch(_SVC, MockSvc), patch(_FORMAT_SECONDS, return_value="1m"):
            result = RUNNER.invoke(main, ["workflow", "plan", "my-workflow"])

        assert result.exit_code == 0
        assert "Execution Plan" in result.output
        assert "build" in result.output

    def test_plan_workflow_not_found(self):
        """Workflow not in DB → exit 1."""
        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = []

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(main, ["workflow", "plan", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_plan_invalid_param_format(self):
        """--param without = → exit 1 before svc.plan() is called."""
        wf = _make_workflow_dto(name="my-workflow")

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(
                main,
                ["workflow", "plan", "my-workflow", "--param", "invalid-no-equals"],
            )

        assert result.exit_code == 1
        assert "Invalid --param format" in result.output
        MockSvc.return_value.plan.assert_not_called()

    def test_plan_with_params(self):
        """--param key=value pairs are parsed and passed to svc.plan()."""
        wf = _make_workflow_dto(name="my-workflow")
        ps = _make_plan_stage()
        batch = _make_plan_batch(stages=[ps])
        plan = _make_plan(batches=[batch], parameters={"env": "prod", "feature": "auth"})

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]
        MockSvc.return_value.plan.return_value = plan

        with patch(_SVC, MockSvc), patch(_FORMAT_SECONDS, return_value="30s"):
            result = RUNNER.invoke(
                main,
                [
                    "workflow",
                    "plan",
                    "my-workflow",
                    "--param",
                    "env=prod",
                    "--param",
                    "feature=auth",
                ],
            )

        assert result.exit_code == 0
        call_args = MockSvc.return_value.plan.call_args
        # parameters dict is passed as keyword arg
        params_passed = call_args.kwargs.get("parameters", {})
        assert params_passed.get("env") == "prod"
        assert params_passed.get("feature") == "auth"


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


class TestWorkflowRun:
    """Tests for ``skillmeat workflow run``."""

    def test_run_dry_run(self):
        """--dry-run shows plan and exits 0 without calling start_execution."""
        wf = _make_workflow_dto(name="my-workflow")
        ps = _make_plan_stage()
        batch = _make_plan_batch(stages=[ps])
        plan = _make_plan(batches=[batch])

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]
        MockSvc.return_value.plan.return_value = plan

        MockExecSvc = MagicMock()

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc), \
             patch(_FORMAT_SECONDS, return_value="30s"):
            result = RUNNER.invoke(
                main, ["workflow", "run", "my-workflow", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "dry-run" in result.output.lower()
        MockExecSvc.return_value.start_execution.assert_not_called()

    def test_run_workflow_not_found(self):
        """Workflow not in DB → exit 1, start_execution never called."""
        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = []

        MockExecSvc = MagicMock()

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "run", "nonexistent"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
        MockExecSvc.return_value.start_execution.assert_not_called()

    def test_run_successful_execution(self):
        """Successful execution ends with exit 0 and run summary."""
        wf = _make_workflow_dto(name="my-workflow", workflow_id="wf-1")
        step = _make_step_dto(status="completed")
        exec_dto = _make_execution_dto(status="completed", steps=[step])

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        MockExecSvc = MagicMock()
        exec_instance = MockExecSvc.return_value
        exec_instance.start_execution.return_value = exec_dto
        exec_instance.run_execution.return_value = exec_dto
        exec_instance.get_events.return_value = [
            {"seq": 0, "type": "execution_completed", "data": {}}
        ]
        exec_instance.get_execution.return_value = exec_dto

        # Live and threading are lazy-imported inside the run() function body.
        # Patch at the source module level.
        def _fake_thread(target=None, daemon=False):
            t = MagicMock()
            t.start = lambda: target()
            t.is_alive.return_value = False
            t.join = lambda timeout=None: None
            return t

        MockLive = MagicMock()
        MockLive.return_value.__enter__ = MagicMock(return_value=MagicMock())
        MockLive.return_value.__exit__ = MagicMock(return_value=False)

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc), \
             patch("rich.live.Live", MockLive), \
             patch("threading.Thread", _fake_thread):
            result = RUNNER.invoke(main, ["workflow", "run", "my-workflow"])

        assert result.exit_code == 0
        assert "my-workflow" in result.output

    def test_run_failed_execution(self):
        """Failed execution → exit 1."""
        wf = _make_workflow_dto(name="my-workflow", workflow_id="wf-1")
        step = _make_step_dto(status="failed", error_message="command not found")
        exec_dto = _make_execution_dto(
            status="failed", steps=[step], error_message="stage failed"
        )

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        MockExecSvc = MagicMock()
        exec_instance = MockExecSvc.return_value
        exec_instance.start_execution.return_value = exec_dto
        exec_instance.run_execution.return_value = exec_dto
        exec_instance.get_events.return_value = [
            {"seq": 0, "type": "execution_failed", "data": {}}
        ]
        exec_instance.get_execution.return_value = exec_dto

        def _fake_thread(target=None, daemon=False):
            t = MagicMock()
            t.start = lambda: target()
            t.is_alive.return_value = False
            t.join = lambda timeout=None: None
            return t

        MockLive = MagicMock()
        MockLive.return_value.__enter__ = MagicMock(return_value=MagicMock())
        MockLive.return_value.__exit__ = MagicMock(return_value=False)

        with patch(_SVC, MockSvc), patch(_EXEC_SVC, MockExecSvc), \
             patch("rich.live.Live", MockLive), \
             patch("threading.Thread", _fake_thread):
            result = RUNNER.invoke(main, ["workflow", "run", "my-workflow"])

        assert result.exit_code == 1

    def test_run_invalid_param_format(self):
        """--param without = → exit 1 before execution starts."""
        wf = _make_workflow_dto(name="my-workflow")

        MockSvc = MagicMock()
        MockSvc.return_value.list.return_value = [wf]

        with patch(_SVC, MockSvc):
            result = RUNNER.invoke(
                main,
                ["workflow", "run", "my-workflow", "--param", "noequalssign"],
            )

        assert result.exit_code == 1
        assert "Invalid --param format" in result.output


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------


class TestWorkflowRuns:
    """Tests for ``skillmeat workflow runs``."""

    def test_runs_list_mode_empty(self):
        """No executions → 'No executions found', exit 0."""
        MockExecSvc = MagicMock()
        MockExecSvc.return_value.list_executions.return_value = []

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "runs"])

        assert result.exit_code == 0
        assert "No executions" in result.output

    def test_runs_list_mode_with_results(self):
        """Executions present → table with truncated run IDs."""
        exec1 = _make_execution_dto(execution_id="exec-abc-1234", status="completed")
        exec2 = _make_execution_dto(
            execution_id="exec-def-5678", status="failed", workflow_id="wf-2"
        )

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.list_executions.return_value = [exec1, exec2]

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "runs"])

        assert result.exit_code == 0
        # The CLI shows first 12 chars of run ID
        assert "exec-abc-123" in result.output
        assert "exec-def-567" in result.output

    def test_runs_detail_mode_with_run_id(self):
        """RUN_ID provided → 'Execution Detail' panel and stage table shown."""
        step = _make_step_dto(stage_name="Stage One", status="completed")
        exec_dto = _make_execution_dto(
            execution_id="exec-full-id-123", status="completed", steps=[step]
        )

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.return_value = exec_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "runs", "exec-full-id-123"])

        assert result.exit_code == 0
        assert "Execution Detail" in result.output
        assert "Stage One" in result.output

    def test_runs_detail_mode_not_found(self):
        """RUN_ID not found → exit 1."""
        from skillmeat.core.workflow.exceptions import WorkflowExecutionNotFoundError

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.side_effect = (
            WorkflowExecutionNotFoundError("not found")
        )

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "runs", "bad-run-id"])

        assert result.exit_code == 1
        assert "No execution found" in result.output

    def test_runs_status_filter(self):
        """--status filter is forwarded to list_executions()."""
        MockExecSvc = MagicMock()
        MockExecSvc.return_value.list_executions.return_value = []

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "runs", "--status", "failed"])

        assert result.exit_code == 0
        call_kwargs = MockExecSvc.return_value.list_executions.call_args.kwargs
        assert call_kwargs.get("status") == "failed"

    def test_runs_failed_detail_exits_1(self):
        """Detail view of a failed execution → exit 1."""
        exec_dto = _make_execution_dto(execution_id="fail-run-id", status="failed")

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.return_value = exec_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(main, ["workflow", "runs", "fail-run-id"])

        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------


class TestWorkflowApprove:
    """Tests for ``skillmeat workflow approve``."""

    def _make_waiting_step(self) -> MagicMock:
        return _make_step_dto(
            stage_id="gate-1",
            stage_name="Quality Gate",
            stage_type="gate",
            status="waiting_for_approval",
        )

    def test_approve_success_with_yes(self):
        """--yes skips prompt, gate approved → success message."""
        gate_step = self._make_waiting_step()
        exec_dto = _make_execution_dto(
            execution_id="run-abc", status="paused", steps=[gate_step]
        )
        approved_step = _make_step_dto(
            stage_id="gate-1",
            stage_name="Quality Gate",
            stage_type="gate",
            status="completed",
        )

        MockExecSvc = MagicMock()
        exec_instance = MockExecSvc.return_value
        exec_instance.get_execution.return_value = exec_dto
        exec_instance.approve_gate.return_value = approved_step

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "approve", "run-abc", "--yes"]
            )

        assert result.exit_code == 0
        assert "Gate approved" in result.output
        exec_instance.approve_gate.assert_called_once_with("run-abc", "gate-1")

    def test_approve_no_waiting_gate(self):
        """No waiting gate → exit 1 with informative message."""
        completed_step = _make_step_dto(status="completed")
        exec_dto = _make_execution_dto(
            execution_id="run-abc", status="completed", steps=[completed_step]
        )

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.return_value = exec_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "approve", "run-abc", "--yes"]
            )

        assert result.exit_code == 1
        assert (
            "No gate stage" in result.output
            or "waiting for approval" in result.output
        )

    def test_approve_execution_not_found(self):
        """Execution not found → exit 1."""
        from skillmeat.core.workflow.exceptions import WorkflowExecutionNotFoundError

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.side_effect = (
            WorkflowExecutionNotFoundError("not found")
        )

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "approve", "bad-run-id", "--yes"]
            )

        assert result.exit_code == 1
        assert "No execution found" in result.output

    def test_approve_prompts_without_yes(self):
        """Without --yes, confirmation prompt shown; 'y' confirms."""
        gate_step = self._make_waiting_step()
        exec_dto = _make_execution_dto(
            execution_id="run-abc", status="paused", steps=[gate_step]
        )
        approved_step = _make_step_dto(
            stage_id="gate-1",
            stage_name="Quality Gate",
            stage_type="gate",
            status="completed",
        )

        MockExecSvc = MagicMock()
        exec_instance = MockExecSvc.return_value
        exec_instance.get_execution.return_value = exec_dto
        exec_instance.approve_gate.return_value = approved_step

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "approve", "run-abc"], input="y\n"
            )

        assert result.exit_code == 0
        exec_instance.approve_gate.assert_called_once()


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


class TestWorkflowCancel:
    """Tests for ``skillmeat workflow cancel``."""

    def test_cancel_success_with_yes(self):
        """--yes skips confirmation → execution cancelled, exit 0."""
        step = _make_step_dto(status="running")
        exec_dto = _make_execution_dto(
            execution_id="run-xyz", status="running", steps=[step]
        )
        cancelled_dto = _make_execution_dto(
            execution_id="run-xyz", status="cancelled", steps=[step]
        )

        MockExecSvc = MagicMock()
        exec_instance = MockExecSvc.return_value
        exec_instance.get_execution.return_value = exec_dto
        exec_instance.cancel_execution.return_value = cancelled_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "cancel", "run-xyz", "--yes"]
            )

        assert result.exit_code == 0
        assert "Cancelled" in result.output
        exec_instance.cancel_execution.assert_called_once_with("run-xyz")

    def test_cancel_already_terminal(self):
        """Execution already in terminal state → informative message, exit 0."""
        exec_dto = _make_execution_dto(execution_id="run-done", status="completed")

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.return_value = exec_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "cancel", "run-done", "--yes"]
            )

        assert result.exit_code == 0
        assert "terminal" in result.output.lower() or "already" in result.output.lower()
        MockExecSvc.return_value.cancel_execution.assert_not_called()

    def test_cancel_execution_not_found(self):
        """Execution not found → exit 1."""
        from skillmeat.core.workflow.exceptions import WorkflowExecutionNotFoundError

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.side_effect = (
            WorkflowExecutionNotFoundError("not found")
        )

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "cancel", "bad-id", "--yes"]
            )

        assert result.exit_code == 1
        assert "No execution found" in result.output

    def test_cancel_prompts_without_yes(self):
        """Without --yes, confirmation prompt shown; 'y' proceeds with cancel."""
        step = _make_step_dto(status="running")
        exec_dto = _make_execution_dto(
            execution_id="run-xyz", status="running", steps=[step]
        )
        cancelled_dto = _make_execution_dto(
            execution_id="run-xyz", status="cancelled", steps=[]
        )

        MockExecSvc = MagicMock()
        exec_instance = MockExecSvc.return_value
        exec_instance.get_execution.return_value = exec_dto
        exec_instance.cancel_execution.return_value = cancelled_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "cancel", "run-xyz"], input="y\n"
            )

        assert result.exit_code == 0
        exec_instance.cancel_execution.assert_called_once()

    def test_cancel_user_aborts_prompt(self):
        """User types 'n' → aborted message, exit 0, cancel_execution not called."""
        step = _make_step_dto(status="running")
        exec_dto = _make_execution_dto(
            execution_id="run-xyz", status="running", steps=[step]
        )

        MockExecSvc = MagicMock()
        MockExecSvc.return_value.get_execution.return_value = exec_dto

        with patch(_EXEC_SVC, MockExecSvc):
            result = RUNNER.invoke(
                main, ["workflow", "cancel", "run-xyz"], input="n\n"
            )

        assert result.exit_code == 0
        assert (
            "aborted" in result.output.lower()
            or "Cancellation" in result.output
        )
        MockExecSvc.return_value.cancel_execution.assert_not_called()


# ---------------------------------------------------------------------------
# Smoke tests — command group wiring
# ---------------------------------------------------------------------------


class TestWorkflowGroupHelp:
    """Smoke tests that the command group is correctly registered."""

    def test_workflow_help(self):
        """``skillmeat workflow --help`` exits 0 and lists all subcommands."""
        result = RUNNER.invoke(main, ["workflow", "--help"])
        assert result.exit_code == 0
        for cmd in (
            "create", "list", "show", "validate",
            "plan", "run", "runs", "approve", "cancel",
        ):
            assert cmd in result.output, f"Expected {cmd!r} in help output"

    def test_workflow_list_help(self):
        """``skillmeat workflow list --help`` exits 0."""
        result = RUNNER.invoke(main, ["workflow", "list", "--help"])
        assert result.exit_code == 0

    def test_workflow_run_help(self):
        """``skillmeat workflow run --help`` mentions --dry-run."""
        result = RUNNER.invoke(main, ["workflow", "run", "--help"])
        assert result.exit_code == 0
        assert "dry-run" in result.output

    def test_workflow_validate_help(self):
        """``skillmeat workflow validate --help`` mentions --strict."""
        result = RUNNER.invoke(main, ["workflow", "validate", "--help"])
        assert result.exit_code == 0
        assert "strict" in result.output
