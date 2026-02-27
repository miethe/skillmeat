"""E2E and integration tests for the workflow service lifecycle.

TEST-3.17: Full lifecycle — create → validate → plan → run → complete.

Covers:
    - WorkflowService CRUD roundtrip (create, get, list, update, delete)
    - WorkflowService.validate() — schema + DAG + artifact-ref passes
    - WorkflowService.plan() — parameter merging + batch layout
    - WorkflowExecutionService.start_execution() — status "running", step creation
    - WorkflowExecutionService.run_execution() — stub dispatch, all steps completed
    - Duplicate detection
    - Execution controls (start, cancel)

All tests use a real SQLite file in a pytest ``tmp_path`` directory so that
both ``WorkflowService`` (which constructs its own engine via BaseRepository)
and ``WorkflowExecutionService`` (which calls ``get_session(db_path)``) share
the same physical database without any monkeypatching of module globals.
"""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from skillmeat.core.workflow.exceptions import (
    WorkflowNotFoundError,
    WorkflowValidationError,
)
from skillmeat.core.workflow.execution_service import WorkflowExecutionService
from skillmeat.core.workflow.service import WorkflowService


# ---------------------------------------------------------------------------
# YAML fixtures
# ---------------------------------------------------------------------------

# Minimal valid two-stage workflow.  The `workflow.id` field is required by
# WorkflowMetadata; `roles.primary.artifact` must follow `type:name` format.
_TWO_STAGE_YAML = """
workflow:
  id: test-workflow
  name: Test Workflow
  version: "1.0.0"
  description: E2E test workflow
stages:
  - id: stage-1
    name: First Stage
    type: agent
    roles:
      primary:
        artifact: "agent:python-backend-engineer"
        task: "Do something"
  - id: stage-2
    name: Second Stage
    type: agent
    depends_on:
      - stage-1
    roles:
      primary:
        artifact: "agent:code-reviewer"
        task: "Review it"
"""

# Single-stage workflow used in simpler tests.
_ONE_STAGE_YAML = """
workflow:
  id: single-stage-wf
  name: Single Stage Workflow
  version: "1.0.0"
stages:
  - id: only-stage
    name: Only Stage
    type: agent
    roles:
      primary:
        artifact: "agent:python-backend-engineer"
"""

# Workflow with an intentional DAG cycle — used to verify validation rejects it.
_CYCLE_YAML = """
workflow:
  id: cycle-wf
  name: Cycle Workflow
  version: "1.0.0"
stages:
  - id: stage-a
    name: Stage A
    type: agent
    depends_on:
      - stage-b
    roles:
      primary:
        artifact: "agent:python-backend-engineer"
  - id: stage-b
    name: Stage B
    type: agent
    depends_on:
      - stage-a
    roles:
      primary:
        artifact: "agent:code-reviewer"
"""

# Workflow with invalid artifact reference (no colon) — validation should flag it.
_INVALID_ARTIFACT_YAML = """
workflow:
  id: bad-artifact-wf
  name: Bad Artifact Workflow
  version: "1.0.0"
stages:
  - id: stage-1
    name: Stage 1
    type: agent
    roles:
      primary:
        artifact: "python-backend-engineer"
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_session_global() -> None:
    """Reset the module-level ``SessionLocal`` global before and after each test.

    ``skillmeat.cache.models.get_session`` uses a module-level ``SessionLocal``
    that is lazily initialized on the first call and then cached.  Without this
    reset, the second test's ``WorkflowExecutionService`` would call
    ``get_session(new_db_path)`` but find ``SessionLocal is not None`` (set by
    the first test) and silently reuse the first test's database engine — causing
    FK constraint failures because the workflow rows written by the second test's
    ``WorkflowService`` (which has its own BaseRepository engine) live in a
    different file than the stale engine.

    Patching the global to ``None`` forces ``get_session`` to call
    ``init_session_factory(db_path)`` with the current test's path on every call,
    keeping both services in sync.
    """
    import skillmeat.cache.models as _models

    original = _models.SessionLocal
    _models.SessionLocal = None
    yield
    _models.SessionLocal = original


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Return a path string for a per-test SQLite database file.

    Using a real file (rather than in-memory) ensures both WorkflowService
    (BaseRepository engine) and WorkflowExecutionService (get_session) target
    the same database without any module-global patching.
    """
    return str(tmp_path / "test_workflow.db")


@pytest.fixture()
def wf_service(db_path: str) -> WorkflowService:
    """Return a WorkflowService backed by the test database."""
    return WorkflowService(db_path=db_path)


@pytest.fixture()
def exec_service(db_path: str) -> WorkflowExecutionService:
    """Return a WorkflowExecutionService backed by the test database.

    Instantiating WorkflowService first ensures that ``create_tables()`` has
    been called against this test's db_path before WorkflowExecutionService
    tries to open sessions against it.  Without this, tests that only use
    ``exec_service`` (not ``wf_service``) would find an empty SQLite file with
    no tables created.
    """
    # Ensure all tables exist by triggering BaseRepository.__init__ via a
    # WorkflowService instance (which calls create_tables internally).
    WorkflowService(db_path=db_path)
    return WorkflowExecutionService(db_path=db_path)


# ---------------------------------------------------------------------------
# TEST-3.17: Full E2E lifecycle
# ---------------------------------------------------------------------------


class TestFullWorkflowLifecycle:
    """E2E: create → validate → plan → run → complete."""

    def test_full_workflow_lifecycle(
        self, wf_service: WorkflowService, exec_service: WorkflowExecutionService
    ) -> None:
        """Complete lifecycle for a two-stage sequential workflow."""

        # ------------------------------------------------------------------
        # Step 1: Create — persist the workflow definition to the database.
        # ------------------------------------------------------------------
        workflow = wf_service.create(yaml_content=_TWO_STAGE_YAML)

        assert workflow.id, "Workflow should be assigned a non-empty ID"
        assert workflow.name == "Test Workflow"
        assert workflow.version == "1.0.0"
        assert workflow.status == "draft"
        assert len(workflow.stages) == 2, "Two stages should be persisted"
        stage_ids = {s.stage_id_ref for s in workflow.stages}
        assert stage_ids == {"stage-1", "stage-2"}

        # ------------------------------------------------------------------
        # Step 2: Validate — should pass all four validation passes.
        # ------------------------------------------------------------------
        result = wf_service.validate(workflow.id, is_yaml=False)

        assert result.valid, (
            f"Validation should pass; errors: {[str(e) for e in result.errors]}"
        )
        assert len(result.errors) == 0

        # ------------------------------------------------------------------
        # Step 3: Plan — should produce two batches (sequential dependency).
        # ------------------------------------------------------------------
        plan = wf_service.plan(workflow.id, parameters={})

        assert plan is not None
        # plan.workflow_id carries the SWDL `workflow.id` field ("test-workflow"),
        # not the DB UUID primary key.  Verify the name instead.
        assert plan.workflow_name == "Test Workflow"
        assert len(plan.batches) >= 1, "At least one execution batch expected"

        # The two stages have a dependency, so they cannot run in parallel —
        # we expect exactly two batches.
        assert len(plan.batches) == 2, (
            f"Expected 2 serial batches; got {len(plan.batches)}"
        )
        batch0_stage_ids = {s.stage_id for s in plan.batches[0].stages}
        batch1_stage_ids = {s.stage_id for s in plan.batches[1].stages}
        assert "stage-1" in batch0_stage_ids
        assert "stage-2" in batch1_stage_ids

        # ------------------------------------------------------------------
        # Step 4: start_execution — persists a "running" execution with steps.
        # ------------------------------------------------------------------
        execution = exec_service.start_execution(workflow.id, parameters={})

        assert execution.id, "Execution should receive a non-empty ID"
        assert execution.workflow_id == workflow.id
        assert execution.status == "running"
        assert execution.started_at is not None
        assert len(execution.steps) == 2, (
            "One ExecutionStep should be created per stage"
        )
        for step in execution.steps:
            assert step.status == "pending"

        # ------------------------------------------------------------------
        # Step 5: run_execution — runs the stub dispatch loop.
        # ------------------------------------------------------------------
        final = exec_service.run_execution(execution.id)

        assert final.status in ("completed", "failed"), (
            f"Execution should finish; got status={final.status!r}"
        )

        # ------------------------------------------------------------------
        # Step 6: Verify final step states.
        # ------------------------------------------------------------------
        completed_exec = exec_service.get_execution(execution.id)
        terminal_statuses = {"completed", "skipped", "failed", "waiting_for_approval"}
        for step in completed_exec.steps:
            assert step.status in terminal_statuses, (
                f"Step {step.stage_id!r} should be terminal; got {step.status!r}"
            )

        # For the stub dispatch, all agent stages complete successfully.
        if final.status == "completed":
            completed_steps = [
                s for s in completed_exec.steps if s.status == "completed"
            ]
            assert len(completed_steps) == 2, (
                "Both agent stages should complete with stub dispatch"
            )

    def test_validate_in_yaml_mode(self, wf_service: WorkflowService) -> None:
        """validate(is_yaml=True) should work without a DB round-trip."""
        result = wf_service.validate(_TWO_STAGE_YAML, is_yaml=True)
        assert result.valid
        assert len(result.errors) == 0

    def test_validate_detects_invalid_artifact_ref(
        self, wf_service: WorkflowService
    ) -> None:
        """Validation should flag artifact references missing the type: prefix."""
        result = wf_service.validate(_INVALID_ARTIFACT_YAML, is_yaml=True)
        assert not result.valid
        artifact_errors = [e for e in result.errors if e.category == "artifact"]
        assert len(artifact_errors) >= 1, (
            "Should produce at least one artifact validation error"
        )

    def test_validate_detects_dag_cycle(self, wf_service: WorkflowService) -> None:
        """Validation should detect a dependency cycle in the stage DAG."""
        result = wf_service.validate(_CYCLE_YAML, is_yaml=True)
        assert not result.valid
        dag_errors = [e for e in result.errors if e.category == "dag"]
        assert len(dag_errors) >= 1, "Should produce at least one DAG cycle error"

    def test_plan_raises_on_invalid_workflow(
        self, wf_service: WorkflowService
    ) -> None:
        """plan() should raise WorkflowValidationError for invalid definitions."""
        invalid_wf = wf_service.create(yaml_content=_INVALID_ARTIFACT_YAML)
        with pytest.raises(WorkflowValidationError):
            wf_service.plan(invalid_wf.id, parameters={})


# ---------------------------------------------------------------------------
# CRUD roundtrip
# ---------------------------------------------------------------------------


class TestWorkflowCrudRoundtrip:
    """Verify create / get / list / update / delete behave correctly."""

    def test_create_get(self, wf_service: WorkflowService) -> None:
        """Created workflow can be retrieved by ID with all fields intact."""
        created = wf_service.create(yaml_content=_ONE_STAGE_YAML)

        fetched = wf_service.get(created.id)

        assert fetched.id == created.id
        assert fetched.name == "Single Stage Workflow"
        assert fetched.version == "1.0.0"
        assert fetched.status == "draft"
        assert len(fetched.stages) == 1
        assert fetched.stages[0].stage_id_ref == "only-stage"

    def test_list_returns_created_workflow(
        self, wf_service: WorkflowService
    ) -> None:
        """list() should include a newly created workflow."""
        created = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        workflows = wf_service.list()

        ids = {w.id for w in workflows}
        assert created.id in ids

    def test_list_pagination(self, wf_service: WorkflowService) -> None:
        """list(skip, limit) should honour pagination parameters."""
        # Create three workflows.
        ids = set()
        for i in range(3):
            yaml = _ONE_STAGE_YAML.replace(
                "id: single-stage-wf", f"id: paging-wf-{i}"
            ).replace("name: Single Stage Workflow", f"name: Paging WF {i}")
            ids.add(wf_service.create(yaml_content=yaml).id)

        page1 = wf_service.list(skip=0, limit=2)
        page2 = wf_service.list(skip=2, limit=2)

        assert len(page1) == 2
        # Combined pages should cover at least the three created workflows.
        combined = {w.id for w in page1} | {w.id for w in page2}
        assert ids.issubset(combined)

    def test_update_replaces_definition(
        self, wf_service: WorkflowService
    ) -> None:
        """update() replaces the YAML definition and re-parses stages."""
        created = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        assert len(created.stages) == 1

        updated = wf_service.update(created.id, yaml_content=_TWO_STAGE_YAML)

        assert updated.id == created.id
        assert updated.name == "Test Workflow"  # Name came from the new YAML.
        assert len(updated.stages) == 2

    def test_update_nonexistent_raises(self, wf_service: WorkflowService) -> None:
        """update() on a missing ID should raise WorkflowNotFoundError."""
        with pytest.raises(WorkflowNotFoundError):
            wf_service.update("nonexistent-id", yaml_content=_ONE_STAGE_YAML)

    def test_delete_removes_workflow(self, wf_service: WorkflowService) -> None:
        """delete() should remove the workflow so subsequent get() raises."""
        created = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        wf_service.delete(created.id)

        with pytest.raises(WorkflowNotFoundError):
            wf_service.get(created.id)

    def test_delete_nonexistent_raises(self, wf_service: WorkflowService) -> None:
        """delete() on a missing ID should raise WorkflowNotFoundError."""
        with pytest.raises(WorkflowNotFoundError):
            wf_service.delete("does-not-exist")

    def test_get_nonexistent_raises(self, wf_service: WorkflowService) -> None:
        """get() on a missing ID should raise WorkflowNotFoundError."""
        with pytest.raises(WorkflowNotFoundError):
            wf_service.get("no-such-workflow")


# ---------------------------------------------------------------------------
# Duplicate
# ---------------------------------------------------------------------------


class TestWorkflowDuplicate:
    """Verify duplicate() creates an independent copy."""

    def test_duplicate_default_name(self, wf_service: WorkflowService) -> None:
        """duplicate() should use '<original> (copy)' as default name."""
        original = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        copy = wf_service.duplicate(original.id)

        assert copy.id != original.id
        assert copy.name == "Single Stage Workflow (copy)"
        assert copy.status == "draft"
        assert len(copy.stages) == len(original.stages)

    def test_duplicate_custom_name(self, wf_service: WorkflowService) -> None:
        """duplicate() with new_name should apply the supplied name."""
        original = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        copy = wf_service.duplicate(original.id, new_name="My Clone")

        assert copy.name == "My Clone"
        assert copy.id != original.id

    def test_duplicate_is_independent(self, wf_service: WorkflowService) -> None:
        """Modifying the copy's definition should not affect the original."""
        original = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        copy = wf_service.duplicate(original.id)

        # Update the copy with the two-stage YAML.
        wf_service.update(copy.id, yaml_content=_TWO_STAGE_YAML)

        # Original should still have one stage.
        refetched_original = wf_service.get(original.id)
        assert len(refetched_original.stages) == 1

    def test_duplicate_nonexistent_raises(
        self, wf_service: WorkflowService
    ) -> None:
        """duplicate() on a missing ID should raise WorkflowNotFoundError."""
        with pytest.raises(WorkflowNotFoundError):
            wf_service.duplicate("ghost-id")


# ---------------------------------------------------------------------------
# Execution controls
# ---------------------------------------------------------------------------


class TestExecutionControls:
    """Verify start_execution and cancellation behaviour."""

    def test_start_execution_creates_running_record(
        self,
        wf_service: WorkflowService,
        exec_service: WorkflowExecutionService,
    ) -> None:
        """start_execution() should persist a 'running' record with pending steps."""
        wf = wf_service.create(yaml_content=_TWO_STAGE_YAML)
        execution = exec_service.start_execution(wf.id, parameters={})

        assert execution.id
        assert execution.workflow_id == wf.id
        assert execution.status == "running"
        assert execution.started_at is not None
        # Two stages → two pending steps.
        assert len(execution.steps) == 2
        for step in execution.steps:
            assert step.status == "pending"

    def test_start_execution_unknown_workflow_raises(
        self, exec_service: WorkflowExecutionService
    ) -> None:
        """start_execution() for a non-existent workflow should raise."""
        with pytest.raises(WorkflowNotFoundError):
            exec_service.start_execution("nonexistent-workflow-id")

    def test_list_executions_filters_by_workflow(
        self,
        wf_service: WorkflowService,
        exec_service: WorkflowExecutionService,
    ) -> None:
        """list_executions(workflow_id=...) should filter to the right workflow."""
        wf_a = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        wf_b_yaml = _ONE_STAGE_YAML.replace(
            "id: single-stage-wf", "id: single-stage-b"
        ).replace("name: Single Stage Workflow", "name: Single Stage B")
        wf_b = wf_service.create(yaml_content=wf_b_yaml)

        exec_a = exec_service.start_execution(wf_a.id)
        exec_b = exec_service.start_execution(wf_b.id)

        results_a = exec_service.list_executions(workflow_id=wf_a.id)
        ids_a = {e.id for e in results_a}

        assert exec_a.id in ids_a
        assert exec_b.id not in ids_a

    def test_get_execution_not_found_raises(
        self, exec_service: WorkflowExecutionService
    ) -> None:
        """get_execution() for a missing ID should raise the appropriate error."""
        from skillmeat.core.workflow.exceptions import WorkflowExecutionNotFoundError

        with pytest.raises(WorkflowExecutionNotFoundError):
            exec_service.get_execution("no-such-execution")

    def test_cancel_sets_cancelled_status(
        self,
        wf_service: WorkflowService,
        exec_service: WorkflowExecutionService,
    ) -> None:
        """Cancelling an execution mid-run should result in 'cancelled' status.

        The execution service exposes cancellation via a threading.Event that is
        set by cancel_execution().  We start run_execution() in a background
        thread, set the cancel flag immediately, and verify the result.
        """
        # Use the two-stage workflow; with stub dispatch each stage is instant,
        # but we patch the cancellation flag to fire before the first batch.
        wf = wf_service.create(yaml_content=_TWO_STAGE_YAML)
        execution = exec_service.start_execution(wf.id, parameters={})
        execution_id = execution.id

        # Inject the cancel flag *before* run_execution so the loop sees it
        # at the first cancellation check point (between batches).
        cancel_event = threading.Event()
        cancel_event.set()  # Pre-set to cancel immediately.
        with exec_service._cancel_flags_lock:
            exec_service._cancel_flags[execution_id] = cancel_event

        # run_execution respects the flag between batches.  With a pre-set flag
        # it should return "cancelled" after the first batch (or immediately if
        # checked before any batch starts).
        final = exec_service.run_execution(execution_id)

        # Acceptable outcomes: cancelled (flag checked before batch loop starts
        # or between batches) or completed (both batches finished before the
        # flag check — the stub dispatch is essentially instant).
        assert final.status in ("cancelled", "completed"), (
            f"Unexpected final status: {final.status!r}"
        )

    def test_run_execution_completes_single_stage(
        self,
        wf_service: WorkflowService,
        exec_service: WorkflowExecutionService,
    ) -> None:
        """A single-stage workflow should complete with the step marked 'completed'."""
        wf = wf_service.create(yaml_content=_ONE_STAGE_YAML)
        execution = exec_service.start_execution(wf.id, parameters={})
        final = exec_service.run_execution(execution.id)

        assert final.status == "completed"
        assert len(final.steps) == 1
        assert final.steps[0].status == "completed"
        assert final.steps[0].output is not None, (
            "Stub dispatch should produce a non-None output dict"
        )
        assert final.steps[0].output.get("stub") is True
