"""API integration tests for workflow and workflow-execution endpoints.

Tests all endpoints in:
  - skillmeat/api/routers/workflows.py       (prefix /api/v1/workflows)
  - skillmeat/api/routers/workflow_executions.py (prefix /api/v1/workflow-executions)

Strategy
--------
Both routers call module-level ``_get_service()`` factories that instantiate
service objects directly (no DI container).  We patch those factories so every
test receives a fresh ``MagicMock`` instead of a real DB-backed service.

All mocked service return values use the DTO dataclasses so that the
``_dto_to_dict()`` helpers inside the routers serialise them correctly.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from skillmeat.api.config import APISettings, Environment
from skillmeat.api.server import create_app
from skillmeat.core.workflow.exceptions import (
    WorkflowExecutionInvalidStateError,
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
    WorkflowParseError,
    WorkflowValidationError,
)
from skillmeat.core.workflow.service import StageDTO, WorkflowDTO
from skillmeat.core.workflow.execution_service import ExecutionStepDTO, WorkflowExecutionDTO


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKFLOWS_URL = "/api/v1/workflows"
EXECUTIONS_URL = "/api/v1/workflow-executions"

_NOW = datetime(2026, 1, 15, 10, 0, 0)
_WORKFLOW_ID = "aabbccdd-1234-5678-abcd-000000000001"
_EXECUTION_ID = "eeff0011-1234-5678-abcd-000000000002"
_STAGE_ID = "review-gate"


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_stage_dto(**overrides: Any) -> StageDTO:
    """Return a minimal valid StageDTO."""
    defaults: Dict[str, Any] = dict(
        id="sstage-uuid-0001",
        stage_id_ref="fetch-data",
        name="Fetch Data",
        description=None,
        order_index=0,
        stage_type="agent",
        condition=None,
        depends_on=[],
        roles=None,
        inputs=None,
        outputs=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    defaults.update(overrides)
    return StageDTO(**defaults)


def _make_workflow_dto(**overrides: Any) -> WorkflowDTO:
    """Return a minimal valid WorkflowDTO."""
    defaults: Dict[str, Any] = dict(
        id=_WORKFLOW_ID,
        name="My Workflow",
        description="A test workflow",
        version="1.0.0",
        status="draft",
        definition="name: My Workflow\nversion: '1.0.0'\nstages: []\n",
        tags=["test"],
        stages=[_make_stage_dto()],
        project_id=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    defaults.update(overrides)
    return WorkflowDTO(**defaults)


def _make_execution_step_dto(**overrides: Any) -> ExecutionStepDTO:
    """Return a minimal valid ExecutionStepDTO."""
    defaults: Dict[str, Any] = dict(
        id="step-uuid-0001",
        execution_id=_EXECUTION_ID,
        stage_id="fetch-data",
        stage_name="Fetch Data",
        stage_type="agent",
        batch_index=0,
        status="pending",
        started_at=None,
        completed_at=None,
        output=None,
        error_message=None,
    )
    defaults.update(overrides)
    return ExecutionStepDTO(**defaults)


def _make_execution_dto(**overrides: Any) -> WorkflowExecutionDTO:
    """Return a minimal valid WorkflowExecutionDTO."""
    defaults: Dict[str, Any] = dict(
        id=_EXECUTION_ID,
        workflow_id=_WORKFLOW_ID,
        status="running",
        parameters={},
        workflow_snapshot=None,
        started_at=_NOW,
        completed_at=None,
        error_message=None,
        steps=[_make_execution_step_dto()],
    )
    defaults.update(overrides)
    return WorkflowExecutionDTO(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_settings() -> APISettings:
    """Minimal APISettings that disable auth and rate-limiting for tests."""
    return APISettings(
        env=Environment.TESTING,
        host="127.0.0.1",
        port=8000,
        log_level="DEBUG",
        cors_enabled=False,
        api_key_enabled=False,
    )


@pytest.fixture(scope="module")
def app(test_settings: APISettings):
    """Create a module-scoped FastAPI test application."""
    from skillmeat.api.config import get_settings
    from skillmeat.api.middleware.auth import verify_token

    application = create_app(test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[verify_token] = lambda: "test-token"
    return application


@pytest.fixture()
def mock_workflow_service() -> MagicMock:
    """Fresh mock of WorkflowService for each test."""
    return MagicMock()


@pytest.fixture()
def mock_execution_service() -> MagicMock:
    """Fresh mock of WorkflowExecutionService for each test."""
    return MagicMock()


@pytest.fixture()
def workflow_client(app, mock_workflow_service: MagicMock) -> TestClient:
    """TestClient with WorkflowService patched."""
    with patch(
        "skillmeat.api.routers.workflows._get_service",
        return_value=mock_workflow_service,
    ):
        with TestClient(app) as client:
            yield client, mock_workflow_service


@pytest.fixture()
def execution_client(app, mock_execution_service: MagicMock) -> TestClient:
    """TestClient with WorkflowExecutionService patched."""
    with patch(
        "skillmeat.api.routers.workflow_executions._get_service",
        return_value=mock_execution_service,
    ):
        with TestClient(app) as client:
            yield client, mock_execution_service


# ---------------------------------------------------------------------------
# Workflow CRUD tests
# ---------------------------------------------------------------------------


class TestListWorkflows:
    def test_list_workflows_empty(self, workflow_client):
        client, svc = workflow_client
        svc.list.return_value = []

        response = client.get(WORKFLOWS_URL)

        assert response.status_code == 200
        assert response.json() == []
        svc.list.assert_called_once_with(project_id=None, skip=0, limit=50)

    def test_list_workflows_with_results(self, workflow_client):
        client, svc = workflow_client
        dto = _make_workflow_dto()
        svc.list.return_value = [dto]

        response = client.get(WORKFLOWS_URL)

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == _WORKFLOW_ID
        assert body[0]["name"] == "My Workflow"

    def test_list_workflows_project_filter(self, workflow_client):
        client, svc = workflow_client
        svc.list.return_value = []

        response = client.get(WORKFLOWS_URL, params={"project_id": "proj-123"})

        assert response.status_code == 200
        svc.list.assert_called_once_with(project_id="proj-123", skip=0, limit=50)

    def test_list_workflows_pagination(self, workflow_client):
        client, svc = workflow_client
        svc.list.return_value = []

        response = client.get(WORKFLOWS_URL, params={"skip": 10, "limit": 5})

        assert response.status_code == 200
        svc.list.assert_called_once_with(project_id=None, skip=10, limit=5)


class TestCreateWorkflow:
    VALID_YAML = "name: My Workflow\nversion: '1.0.0'\nstages: []\n"

    def test_create_workflow_success(self, workflow_client):
        client, svc = workflow_client
        dto = _make_workflow_dto()
        svc.create.return_value = dto

        response = client.post(
            WORKFLOWS_URL,
            json={"yaml_content": self.VALID_YAML},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == _WORKFLOW_ID
        assert body["name"] == "My Workflow"
        svc.create.assert_called_once_with(
            yaml_content=self.VALID_YAML,
            project_id=None,
        )

    def test_create_workflow_with_project_id(self, workflow_client):
        client, svc = workflow_client
        dto = _make_workflow_dto(project_id="proj-abc")
        svc.create.return_value = dto

        response = client.post(
            WORKFLOWS_URL,
            json={"yaml_content": self.VALID_YAML, "project_id": "proj-abc"},
        )

        assert response.status_code == 201
        svc.create.assert_called_once_with(
            yaml_content=self.VALID_YAML,
            project_id="proj-abc",
        )

    def test_create_workflow_invalid_yaml(self, workflow_client):
        client, svc = workflow_client
        svc.create.side_effect = WorkflowParseError("Invalid YAML syntax")

        response = client.post(
            WORKFLOWS_URL,
            json={"yaml_content": ": bad: yaml: ["},
        )

        assert response.status_code == 422

    def test_create_workflow_validation_error(self, workflow_client):
        client, svc = workflow_client
        svc.create.side_effect = WorkflowValidationError("Schema validation failed")

        response = client.post(
            WORKFLOWS_URL,
            json={"yaml_content": self.VALID_YAML},
        )

        assert response.status_code == 422

    def test_create_workflow_missing_body(self, workflow_client):
        client, svc = workflow_client

        response = client.post(WORKFLOWS_URL, json={})

        assert response.status_code == 422  # Pydantic validation error


class TestGetWorkflow:
    def test_get_workflow_success(self, workflow_client):
        client, svc = workflow_client
        dto = _make_workflow_dto()
        svc.get.return_value = dto

        response = client.get(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == _WORKFLOW_ID
        assert body["version"] == "1.0.0"
        # Datetime fields should be ISO strings
        assert "T" in body["created_at"]
        svc.get.assert_called_once_with(_WORKFLOW_ID)

    def test_get_workflow_not_found(self, workflow_client):
        client, svc = workflow_client
        svc.get.side_effect = WorkflowNotFoundError(
            "Workflow not found", workflow_id="missing-id"
        )

        response = client.get(f"{WORKFLOWS_URL}/missing-id")

        assert response.status_code == 404


class TestUpdateWorkflow:
    NEW_YAML = "name: Updated Workflow\nversion: '2.0.0'\nstages: []\n"

    def test_update_workflow_success(self, workflow_client):
        client, svc = workflow_client
        dto = _make_workflow_dto(name="Updated Workflow", version="2.0.0")
        svc.update.return_value = dto

        response = client.put(
            f"{WORKFLOWS_URL}/{_WORKFLOW_ID}",
            json={"yaml_content": self.NEW_YAML},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Updated Workflow"
        assert body["version"] == "2.0.0"
        svc.update.assert_called_once_with(_WORKFLOW_ID, self.NEW_YAML)

    def test_update_workflow_not_found(self, workflow_client):
        client, svc = workflow_client
        svc.update.side_effect = WorkflowNotFoundError("Not found", workflow_id="missing")

        response = client.put(
            f"{WORKFLOWS_URL}/missing",
            json={"yaml_content": self.NEW_YAML},
        )

        assert response.status_code == 404

    def test_update_workflow_invalid_yaml(self, workflow_client):
        client, svc = workflow_client
        svc.update.side_effect = WorkflowParseError("Parse failed")

        response = client.put(
            f"{WORKFLOWS_URL}/{_WORKFLOW_ID}",
            json={"yaml_content": "bad yaml ["},
        )

        assert response.status_code == 422


class TestDeleteWorkflow:
    def test_delete_workflow_success(self, workflow_client):
        client, svc = workflow_client
        svc.delete.return_value = None

        response = client.delete(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}")

        assert response.status_code == 204
        assert response.content == b""
        svc.delete.assert_called_once_with(_WORKFLOW_ID)

    def test_delete_workflow_not_found(self, workflow_client):
        client, svc = workflow_client
        svc.delete.side_effect = WorkflowNotFoundError("Not found", workflow_id="missing")

        response = client.delete(f"{WORKFLOWS_URL}/missing")

        assert response.status_code == 404


class TestDuplicateWorkflow:
    def test_duplicate_workflow_success(self, workflow_client):
        client, svc = workflow_client
        copy_dto = _make_workflow_dto(
            id="copy-uuid-0001",
            name="My Workflow (copy)",
            status="draft",
        )
        svc.duplicate.return_value = copy_dto

        response = client.post(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/duplicate")

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == "copy-uuid-0001"
        assert body["name"] == "My Workflow (copy)"
        svc.duplicate.assert_called_once_with(_WORKFLOW_ID, new_name=None)

    def test_duplicate_workflow_with_new_name(self, workflow_client):
        client, svc = workflow_client
        copy_dto = _make_workflow_dto(
            id="copy-uuid-0002",
            name="Renamed Copy",
            status="draft",
        )
        svc.duplicate.return_value = copy_dto

        response = client.post(
            f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/duplicate",
            json={"new_name": "Renamed Copy"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Renamed Copy"
        svc.duplicate.assert_called_once_with(_WORKFLOW_ID, new_name="Renamed Copy")

    def test_duplicate_workflow_not_found(self, workflow_client):
        client, svc = workflow_client
        svc.duplicate.side_effect = WorkflowNotFoundError(
            "Not found", workflow_id="missing"
        )

        response = client.post(f"{WORKFLOWS_URL}/missing/duplicate")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Workflow operation tests
# ---------------------------------------------------------------------------


class TestValidateWorkflow:
    def test_validate_workflow_valid(self, workflow_client):
        client, svc = workflow_client

        from skillmeat.core.workflow.validator import ValidationResult

        valid_result = ValidationResult(valid=True, errors=[], warnings=[])
        svc.validate.return_value = valid_result

        response = client.post(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/validate")

        assert response.status_code == 200
        body = response.json()
        assert body["is_valid"] is True
        assert body["errors"] == []
        svc.validate.assert_called_once_with(_WORKFLOW_ID, is_yaml=False)

    def test_validate_workflow_invalid(self, workflow_client):
        """Validation failure returns HTTP 200 with is_valid=False (not an error response)."""
        client, svc = workflow_client

        from skillmeat.core.workflow.validator import ValidationIssue, ValidationResult

        invalid_result = ValidationResult(
            valid=False,
            errors=[
                ValidationIssue(
                    category="schema",
                    message="Stage 'fetch' has no role defined",
                    stage_id="fetch",
                )
            ],
            warnings=[],
        )
        svc.validate.return_value = invalid_result

        response = client.post(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/validate")

        assert response.status_code == 200
        body = response.json()
        assert body["is_valid"] is False
        assert len(body["errors"]) == 1

    def test_validate_workflow_not_found(self, workflow_client):
        client, svc = workflow_client
        svc.validate.side_effect = WorkflowNotFoundError(
            "Not found", workflow_id="missing"
        )

        response = client.post(f"{WORKFLOWS_URL}/missing/validate")

        assert response.status_code == 404


class TestPlanWorkflow:
    def _make_plan(self, **overrides):
        from skillmeat.core.workflow.planner import ExecutionPlan
        from skillmeat.core.workflow.validator import ValidationResult

        defaults = dict(
            workflow_id=_WORKFLOW_ID,
            workflow_name="My Workflow",
            workflow_version="1.0.0",
            parameters={},
            batches=[],
            estimated_timeout_seconds=60,
            validation=ValidationResult(valid=True),
        )
        defaults.update(overrides)
        return ExecutionPlan(**defaults)

    def test_plan_workflow_success(self, workflow_client):
        client, svc = workflow_client
        plan = self._make_plan()
        svc.plan.return_value = plan

        response = client.post(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/plan")

        assert response.status_code == 200
        body = response.json()
        assert body["workflow_id"] == _WORKFLOW_ID
        assert body["workflow_name"] == "My Workflow"
        svc.plan.assert_called_once_with(_WORKFLOW_ID, parameters=None)

    def test_plan_workflow_with_parameters(self, workflow_client):
        client, svc = workflow_client
        plan = self._make_plan(parameters={"env": "staging"})
        svc.plan.return_value = plan

        response = client.post(
            f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/plan",
            json={"parameters": {"env": "staging"}},
        )

        assert response.status_code == 200
        svc.plan.assert_called_once_with(
            _WORKFLOW_ID, parameters={"env": "staging"}
        )

    def test_plan_workflow_validation_error(self, workflow_client):
        """Validation failures during planning produce HTTP 422."""
        client, svc = workflow_client
        svc.plan.side_effect = WorkflowValidationError("Cycle detected in DAG")

        response = client.post(f"{WORKFLOWS_URL}/{_WORKFLOW_ID}/plan")

        assert response.status_code == 422

    def test_plan_workflow_not_found(self, workflow_client):
        client, svc = workflow_client
        svc.plan.side_effect = WorkflowNotFoundError(
            "Not found", workflow_id="missing"
        )

        response = client.post(f"{WORKFLOWS_URL}/missing/plan")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Workflow execution tests
# ---------------------------------------------------------------------------


class TestStartExecution:
    def test_start_execution_success(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto()
        svc.start_execution.return_value = dto

        response = client.post(
            EXECUTIONS_URL,
            json={"workflow_id": _WORKFLOW_ID},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == _EXECUTION_ID
        assert body["workflow_id"] == _WORKFLOW_ID
        assert body["status"] == "running"
        assert "T" in body["started_at"]  # ISO-formatted datetime
        svc.start_execution.assert_called_once_with(
            workflow_id=_WORKFLOW_ID,
            parameters=None,
            overrides=None,
        )

    def test_start_execution_with_parameters(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto(parameters={"env": "prod"})
        svc.start_execution.return_value = dto

        response = client.post(
            EXECUTIONS_URL,
            json={"workflow_id": _WORKFLOW_ID, "parameters": {"env": "prod"}},
        )

        assert response.status_code == 201
        svc.start_execution.assert_called_once_with(
            workflow_id=_WORKFLOW_ID,
            parameters={"env": "prod"},
            overrides=None,
        )

    def test_start_execution_workflow_not_found(self, execution_client):
        client, svc = execution_client
        svc.start_execution.side_effect = WorkflowNotFoundError(
            "Workflow not found", workflow_id="missing"
        )

        response = client.post(
            EXECUTIONS_URL,
            json={"workflow_id": "missing"},
        )

        assert response.status_code == 404

    def test_start_execution_validation_error(self, execution_client):
        client, svc = execution_client
        svc.start_execution.side_effect = WorkflowValidationError(
            "Workflow has cycle"
        )

        response = client.post(
            EXECUTIONS_URL,
            json={"workflow_id": _WORKFLOW_ID},
        )

        assert response.status_code == 422


class TestListExecutions:
    def test_list_executions_empty(self, execution_client):
        client, svc = execution_client
        svc.list_executions.return_value = []

        response = client.get(EXECUTIONS_URL)

        assert response.status_code == 200
        assert response.json() == []
        svc.list_executions.assert_called_once_with(
            workflow_id=None,
            status=None,
            skip=0,
            limit=50,
        )

    def test_list_executions_by_workflow(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto()
        svc.list_executions.return_value = [dto]

        response = client.get(
            EXECUTIONS_URL, params={"workflow_id": _WORKFLOW_ID}
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["workflow_id"] == _WORKFLOW_ID
        svc.list_executions.assert_called_once_with(
            workflow_id=_WORKFLOW_ID,
            status=None,
            skip=0,
            limit=50,
        )

    def test_list_executions_status_filter(self, execution_client):
        client, svc = execution_client
        svc.list_executions.return_value = []

        response = client.get(EXECUTIONS_URL, params={"status": "running"})

        assert response.status_code == 200
        svc.list_executions.assert_called_once_with(
            workflow_id=None,
            status="running",
            skip=0,
            limit=50,
        )

    def test_list_executions_by_workflow_path(self, execution_client):
        """Test the dedicated /by-workflow/{id} sub-path endpoint."""
        client, svc = execution_client
        dto = _make_execution_dto()
        svc.list_executions.return_value = [dto]

        response = client.get(
            f"{EXECUTIONS_URL}/by-workflow/{_WORKFLOW_ID}"
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["workflow_id"] == _WORKFLOW_ID


class TestGetExecution:
    def test_get_execution_success(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto()
        svc.get_execution.return_value = dto

        response = client.get(f"{EXECUTIONS_URL}/{_EXECUTION_ID}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == _EXECUTION_ID
        assert body["status"] == "running"
        assert len(body["steps"]) == 1
        svc.get_execution.assert_called_once_with(_EXECUTION_ID)

    def test_get_execution_not_found(self, execution_client):
        client, svc = execution_client
        svc.get_execution.side_effect = WorkflowExecutionNotFoundError(
            "Execution not found", execution_id="missing"
        )

        response = client.get(f"{EXECUTIONS_URL}/missing")

        assert response.status_code == 404

    def test_get_execution_includes_steps(self, execution_client):
        """Verify steps are serialised with ISO datetime fields."""
        client, svc = execution_client
        step = _make_execution_step_dto(
            started_at=_NOW,
            completed_at=_NOW,
            status="completed",
        )
        dto = _make_execution_dto(steps=[step], status="completed")
        svc.get_execution.return_value = dto

        response = client.get(f"{EXECUTIONS_URL}/{_EXECUTION_ID}")

        assert response.status_code == 200
        body = response.json()
        step_body = body["steps"][0]
        assert step_body["status"] == "completed"
        assert "T" in step_body["started_at"]
        assert "T" in step_body["completed_at"]


# ---------------------------------------------------------------------------
# Execution control tests
# ---------------------------------------------------------------------------


class TestPauseExecution:
    def test_pause_execution_success(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto(status="paused")
        svc.pause_execution.return_value = dto

        response = client.post(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/pause")

        assert response.status_code == 200
        assert response.json()["status"] == "paused"
        svc.pause_execution.assert_called_once_with(_EXECUTION_ID)

    def test_pause_execution_not_found(self, execution_client):
        client, svc = execution_client
        svc.pause_execution.side_effect = WorkflowExecutionNotFoundError(
            "Not found", execution_id="missing"
        )

        response = client.post(f"{EXECUTIONS_URL}/missing/pause")

        assert response.status_code == 404

    def test_pause_execution_invalid_state(self, execution_client):
        """Cannot pause an already-completed execution — expect 409 Conflict."""
        client, svc = execution_client
        svc.pause_execution.side_effect = WorkflowExecutionInvalidStateError(
            "Cannot pause: execution is completed",
            execution_id=_EXECUTION_ID,
            current_status="completed",
            expected_status="running",
        )

        response = client.post(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/pause")

        assert response.status_code == 409


class TestResumeExecution:
    def test_resume_execution_success(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto(status="running")
        svc.resume_execution.return_value = dto

        response = client.post(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/resume")

        assert response.status_code == 200
        assert response.json()["status"] == "running"
        svc.resume_execution.assert_called_once_with(_EXECUTION_ID)

    def test_resume_execution_invalid_state(self, execution_client):
        """Cannot resume a running execution — expect 409 Conflict."""
        client, svc = execution_client
        svc.resume_execution.side_effect = WorkflowExecutionInvalidStateError(
            "Cannot resume: execution is not paused",
            execution_id=_EXECUTION_ID,
            current_status="running",
            expected_status="paused",
        )

        response = client.post(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/resume")

        assert response.status_code == 409


class TestCancelExecution:
    def test_cancel_execution_success(self, execution_client):
        client, svc = execution_client
        dto = _make_execution_dto(status="cancelled")
        svc.cancel_execution.return_value = dto

        response = client.post(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        svc.cancel_execution.assert_called_once_with(_EXECUTION_ID)

    def test_cancel_execution_not_found(self, execution_client):
        client, svc = execution_client
        svc.cancel_execution.side_effect = WorkflowExecutionNotFoundError(
            "Not found", execution_id="missing"
        )

        response = client.post(f"{EXECUTIONS_URL}/missing/cancel")

        assert response.status_code == 404

    def test_cancel_execution_already_terminal(self, execution_client):
        """Cannot cancel a completed execution — expect 409 Conflict."""
        client, svc = execution_client
        svc.cancel_execution.side_effect = WorkflowExecutionInvalidStateError(
            "Execution is already in a terminal state",
            execution_id=_EXECUTION_ID,
            current_status="completed",
        )

        response = client.post(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/cancel")

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Gate approval / rejection tests
# ---------------------------------------------------------------------------


class TestApproveGate:
    def _gate_step_dto(self, status: str = "completed") -> ExecutionStepDTO:
        return _make_execution_step_dto(
            stage_id=_STAGE_ID,
            stage_type="gate",
            status=status,
            started_at=_NOW,
            completed_at=_NOW if status == "completed" else None,
        )

    def test_approve_gate_success(self, execution_client):
        client, svc = execution_client
        step = self._gate_step_dto(status="completed")
        svc.approve_gate.return_value = step

        response = client.post(
            f"{EXECUTIONS_URL}/{_EXECUTION_ID}/gates/{_STAGE_ID}/approve"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["stage_id"] == _STAGE_ID
        assert body["stage_type"] == "gate"
        svc.approve_gate.assert_called_once_with(_EXECUTION_ID, _STAGE_ID)

    def test_approve_gate_not_found(self, execution_client):
        client, svc = execution_client
        svc.approve_gate.side_effect = WorkflowExecutionNotFoundError(
            "Execution not found", execution_id="missing"
        )

        response = client.post(
            f"{EXECUTIONS_URL}/missing/gates/{_STAGE_ID}/approve"
        )

        assert response.status_code == 404

    def test_approve_gate_invalid_state(self, execution_client):
        """Cannot approve a gate that has already been resolved."""
        client, svc = execution_client
        svc.approve_gate.side_effect = WorkflowExecutionInvalidStateError(
            "Gate already resolved",
            execution_id=_EXECUTION_ID,
        )

        response = client.post(
            f"{EXECUTIONS_URL}/{_EXECUTION_ID}/gates/{_STAGE_ID}/approve"
        )

        assert response.status_code == 409


class TestRejectGate:
    def _gate_step_dto(self) -> ExecutionStepDTO:
        return _make_execution_step_dto(
            stage_id=_STAGE_ID,
            stage_type="gate",
            status="failed",
            error_message="Gate rejected by reviewer",
            started_at=_NOW,
            completed_at=_NOW,
        )

    def test_reject_gate_success(self, execution_client):
        client, svc = execution_client
        step = self._gate_step_dto()
        svc.reject_gate.return_value = step

        response = client.post(
            f"{EXECUTIONS_URL}/{_EXECUTION_ID}/gates/{_STAGE_ID}/reject",
            json={"reason": "Not ready for production"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["stage_id"] == _STAGE_ID
        assert body["status"] == "failed"
        svc.reject_gate.assert_called_once_with(
            _EXECUTION_ID, _STAGE_ID, "Not ready for production"
        )

    def test_reject_gate_no_reason(self, execution_client):
        """Rejection without a reason body should still work (reason is optional)."""
        client, svc = execution_client
        step = self._gate_step_dto()
        svc.reject_gate.return_value = step

        response = client.post(
            f"{EXECUTIONS_URL}/{_EXECUTION_ID}/gates/{_STAGE_ID}/reject"
        )

        assert response.status_code == 200
        svc.reject_gate.assert_called_once_with(_EXECUTION_ID, _STAGE_ID, None)

    def test_reject_gate_not_found(self, execution_client):
        client, svc = execution_client
        svc.reject_gate.side_effect = WorkflowExecutionNotFoundError(
            "Execution not found", execution_id="missing"
        )

        response = client.post(
            f"{EXECUTIONS_URL}/missing/gates/{_STAGE_ID}/reject"
        )

        assert response.status_code == 404

    def test_reject_gate_invalid_state(self, execution_client):
        client, svc = execution_client
        svc.reject_gate.side_effect = WorkflowExecutionInvalidStateError(
            "Gate already resolved",
            execution_id=_EXECUTION_ID,
        )

        response = client.post(
            f"{EXECUTIONS_URL}/{_EXECUTION_ID}/gates/{_STAGE_ID}/reject"
        )

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# SSE stream smoke test
# ---------------------------------------------------------------------------


class TestStreamExecution:
    def test_stream_execution_not_found(self, execution_client):
        """Requesting a stream for a non-existent execution yields 404 immediately."""
        client, svc = execution_client
        svc.get_execution.side_effect = WorkflowExecutionNotFoundError(
            "Not found", execution_id="missing"
        )

        response = client.get(f"{EXECUTIONS_URL}/missing/stream")

        assert response.status_code == 404

    def test_stream_execution_exists_opens_stream(self, execution_client):
        """A valid execution_id should return a streaming response with SSE content type."""
        client, svc = execution_client
        dto = _make_execution_dto(status="completed")

        # get_execution is called twice: once for validation, once during streaming
        svc.get_execution.return_value = dto
        # get_events returns empty list so the loop terminates quickly
        svc.get_events.return_value = []

        response = client.get(f"{EXECUTIONS_URL}/{_EXECUTION_ID}/stream")

        # TestClient reads the full streaming response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
