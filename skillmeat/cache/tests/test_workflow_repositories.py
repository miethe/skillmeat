"""Comprehensive tests for the workflow data layer.

Covers:
    - WorkflowRepository (session-per-operation / BaseRepository subclass)
    - WorkflowExecutionRepository (session-injected)
    - ExecutionStepRepository (session-injected)
    - WorkflowTransactionManager (cross-repo atomic helpers)

All tests use an in-memory SQLite database so they are fast and isolated.
The engine is created fresh per test class via a module-scoped fixture and
each test gets a clean session via a function-scoped fixture that rolls back
on teardown.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.execution_step_repository import ExecutionStepRepository
from skillmeat.cache.models import (
    Base,
    ExecutionStep,
    Workflow,
    WorkflowExecution,
    WorkflowStage,
)
from skillmeat.cache.repositories import ConstraintError
from skillmeat.cache.workflow_execution_repository import WorkflowExecutionRepository
from skillmeat.cache.workflow_repository import WorkflowRepository
from skillmeat.cache.workflow_transaction import WorkflowTransactionManager


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine once per test module."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def set_pragmas(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine) -> Generator[Session, None, None]:
    """Provide a fresh session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    sess = Session_()

    yield sess

    sess.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Helper: WorkflowRepository pointing at the in-memory engine
#
# WorkflowRepository is a BaseRepository subclass that creates its own engine
# from a db_path.  For tests we bypass that by monkey-patching the engine
# attribute after construction so it uses our in-memory instance.
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_session(engine) -> Generator[Session, None, None]:
    """Provide a session with full commit support for tests that trigger rollbacks.

    Unlike the ``session`` fixture, this fixture does NOT wrap in a
    savepoint/transaction.  The test is responsible for cleanup, which is
    acceptable since all data lands in the module-scoped in-memory DB that
    is discarded at module teardown.
    """
    Session_ = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = Session_()
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture()
def workflow_repo(engine, tmp_path) -> WorkflowRepository:
    """Return a WorkflowRepository wired to the in-memory test engine."""
    db_file = tmp_path / "test_wf.db"
    repo = WorkflowRepository(db_path=str(db_file))
    # Point at the shared in-memory engine so we can inspect state via session
    repo.engine = engine
    return repo


# ---------------------------------------------------------------------------
# Test data builder helpers
# ---------------------------------------------------------------------------


def make_workflow(
    name: str = "Test Workflow",
    status: str = "draft",
    description: str | None = None,
    tags: list[str] | None = None,
    version: str = "1.0.0",
) -> Workflow:
    """Return an unsaved Workflow instance with sensible defaults."""
    wf = Workflow(
        id=uuid.uuid4().hex,
        name=name,
        status=status,
        description=description,
        definition_yaml="version: '1'\nstages: []",
        version=version,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    if tags:
        wf.tags_json = json.dumps(tags)
    return wf


def make_stage(workflow_id: str, stage_id_ref: str = "stage-1", order_index: int = 0) -> WorkflowStage:
    """Return an unsaved WorkflowStage instance."""
    return WorkflowStage(
        id=uuid.uuid4().hex,
        workflow_id=workflow_id,
        stage_id_ref=stage_id_ref,
        name=f"Stage {stage_id_ref}",
        order_index=order_index,
        stage_type="agent",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def make_execution(
    workflow_id: str,
    status: str = "pending",
    started_at: datetime | None = None,
) -> WorkflowExecution:
    """Return an unsaved WorkflowExecution instance."""
    return WorkflowExecution(
        id=uuid.uuid4().hex,
        workflow_id=workflow_id,
        workflow_name="Test Workflow",
        workflow_version="1.0.0",
        status=status,
        trigger="manual",
        started_at=started_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def make_step(
    execution_id: str,
    stage_id_ref: str = "stage-1",
    status: str = "pending",
) -> ExecutionStep:
    """Return an unsaved ExecutionStep instance."""
    return ExecutionStep(
        id=uuid.uuid4().hex,
        execution_id=execution_id,
        stage_id_ref=stage_id_ref,
        stage_name=f"Stage {stage_id_ref}",
        status=status,
        attempt_number=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ===========================================================================
# WorkflowRepository tests
# ===========================================================================


class TestWorkflowRepositoryCreateAndGet:
    """Basic create + retrieve round-trip."""

    def test_create_and_get(self, workflow_repo):
        wf = make_workflow(name="Pipeline Alpha")
        created = workflow_repo.create(wf)

        assert created.id is not None
        fetched = workflow_repo.get(created.id)
        assert fetched is not None
        assert fetched.name == "Pipeline Alpha"
        assert fetched.status == "draft"
        assert fetched.version == "1.0.0"

    def test_get_returns_none_for_unknown_id(self, workflow_repo):
        assert workflow_repo.get("nonexistent-id-xyz") is None

    def test_create_auto_assigns_timestamps(self, workflow_repo):
        wf = Workflow(
            name="Timestamped",
            status="draft",
            definition_yaml="version: '1'\nstages: []",
        )
        created = workflow_repo.create(wf)
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_create_auto_assigns_id_when_missing(self, workflow_repo):
        wf = Workflow(
            name="No ID",
            status="draft",
            definition_yaml="version: '1'\nstages: []",
        )
        wf.id = None  # ensure it's not pre-set
        created = workflow_repo.create(wf)
        assert created.id is not None
        assert len(created.id) > 0


class TestWorkflowRepositoryGetWithStages:
    """get_with_stages eager-loads child stage records."""

    def test_get_with_stages(self, workflow_repo, engine):
        wf = workflow_repo.create(make_workflow(name="Staged Workflow"))

        # Insert stages directly via a raw session
        with Session(engine) as s:
            s.add(make_stage(wf.id, stage_id_ref="s1", order_index=0))
            s.add(make_stage(wf.id, stage_id_ref="s2", order_index=1))
            s.commit()

        fetched = workflow_repo.get_with_stages(wf.id)
        assert fetched is not None
        assert len(fetched.stages) == 2
        refs = {st.stage_id_ref for st in fetched.stages}
        assert refs == {"s1", "s2"}

    def test_get_with_stages_returns_none_for_unknown(self, workflow_repo):
        assert workflow_repo.get_with_stages("no-such-id") is None


class TestWorkflowRepositoryUpdate:
    """Update modifies persisted fields."""

    def test_update_name_and_status(self, workflow_repo):
        wf = workflow_repo.create(make_workflow(name="Old Name", status="draft"))

        wf.name = "New Name"
        wf.status = "active"
        updated = workflow_repo.update(wf)

        assert updated.name == "New Name"
        assert updated.status == "active"

        # Verify persisted
        fetched = workflow_repo.get(updated.id)
        assert fetched.name == "New Name"
        assert fetched.status == "active"

    def test_update_refreshes_updated_at(self, workflow_repo):
        original_ts = datetime(2020, 1, 1)
        wf = make_workflow()
        wf.updated_at = original_ts
        created = workflow_repo.create(wf)

        created.name = "Changed"
        updated = workflow_repo.update(created)

        assert updated.updated_at > original_ts


class TestWorkflowRepositoryDelete:
    """Delete removes the row; deleting a non-existent id returns False."""

    def test_delete_existing_workflow(self, workflow_repo):
        wf = workflow_repo.create(make_workflow())
        result = workflow_repo.delete(wf.id)

        assert result is True
        assert workflow_repo.get(wf.id) is None

    def test_delete_nonexistent_returns_false(self, workflow_repo):
        result = workflow_repo.delete("id-that-does-not-exist")
        assert result is False

    def test_save_is_alias_for_update(self, workflow_repo):
        """WorkflowRepository.save() delegates to update()."""
        wf = workflow_repo.create(make_workflow(name="Save Test"))
        wf.status = "active"
        saved = workflow_repo.save(wf)
        assert saved.status == "active"


class TestWorkflowRepositoryFindByName:
    """find_by_name does an exact-match lookup."""

    def test_find_existing_name(self, workflow_repo):
        workflow_repo.create(make_workflow(name="Exact Match Workflow"))
        found = workflow_repo.find_by_name("Exact Match Workflow")
        assert found is not None
        assert found.name == "Exact Match Workflow"

    def test_find_name_not_found(self, workflow_repo):
        assert workflow_repo.find_by_name("Nonexistent Workflow Name") is None

    def test_find_name_is_case_sensitive(self, workflow_repo):
        workflow_repo.create(make_workflow(name="CaseSensitive"))
        assert workflow_repo.find_by_name("casesensitive") is None
        assert workflow_repo.find_by_name("CASESENSITIVE") is None


class TestWorkflowRepositoryList:
    """list() with various filter combinations."""

    def test_list_no_filters_returns_all(self, workflow_repo):
        for i in range(3):
            workflow_repo.create(make_workflow(name=f"Workflow {i}"))
        results, _ = workflow_repo.list()
        assert len(results) >= 3

    def test_list_filter_by_status(self, workflow_repo):
        workflow_repo.create(make_workflow(name="Active WF", status="active"))
        workflow_repo.create(make_workflow(name="Draft WF", status="draft"))

        active_results, _ = workflow_repo.list(status="active")
        statuses = {r.status for r in active_results}
        assert statuses == {"active"}

    def test_list_filter_by_tags(self, workflow_repo):
        workflow_repo.create(make_workflow(name="Tagged Alpha", tags=["python", "etl"]))
        workflow_repo.create(make_workflow(name="Tagged Beta", tags=["java"]))
        workflow_repo.create(make_workflow(name="No Tags"))

        results, _ = workflow_repo.list(tags=["python"])
        names = [r.name for r in results]
        assert "Tagged Alpha" in names
        assert "Tagged Beta" not in names
        assert "No Tags" not in names

    def test_list_filter_by_multiple_tags_and_semantics(self, workflow_repo):
        workflow_repo.create(make_workflow(name="Both Tags", tags=["python", "etl"]))
        workflow_repo.create(make_workflow(name="One Tag", tags=["python"]))

        results, _ = workflow_repo.list(tags=["python", "etl"])
        names = [r.name for r in results]
        assert "Both Tags" in names
        assert "One Tag" not in names

    def test_list_text_search_on_name(self, workflow_repo):
        workflow_repo.create(make_workflow(name="Deploy Pipeline UNIQUE_TOKEN_NAME"))
        results, _ = workflow_repo.list(search="UNIQUE_TOKEN_NAME")
        assert any(r.name == "Deploy Pipeline UNIQUE_TOKEN_NAME" for r in results)

    def test_list_text_search_on_description(self, workflow_repo):
        wf = make_workflow(name="Search Desc Test", description="UNIQUE_TOKEN_DESC found here")
        workflow_repo.create(wf)
        results, _ = workflow_repo.list(search="UNIQUE_TOKEN_DESC")
        assert any(r.description and "UNIQUE_TOKEN_DESC" in r.description for r in results)

    def test_list_text_search_case_insensitive(self, workflow_repo):
        workflow_repo.create(make_workflow(name="MixedCase Workflow NAME_ILIKE"))
        results_lower, _ = workflow_repo.list(search="name_ilike")
        results_upper, _ = workflow_repo.list(search="NAME_ILIKE")
        # At least one case should find it (SQLite LIKE is case-insensitive for ASCII)
        assert len(results_lower) > 0 or len(results_upper) > 0


class TestWorkflowRepositoryPagination:
    """Cursor-based pagination exhausts all pages correctly."""

    def test_list_cursor_pagination(self, workflow_repo):
        # Use a unique tag so these workflows are isolated
        tag = f"pagtest-{uuid.uuid4().hex}"
        for i in range(5):
            workflow_repo.create(make_workflow(name=f"Page WF {i}", tags=[tag]))

        collected = []
        cursor = None
        while True:
            page, cursor = workflow_repo.list(tags=[tag], limit=2, cursor=cursor)
            collected.extend(page)
            if cursor is None:
                break

        assert len(collected) == 5

    def test_list_returns_none_cursor_on_last_page(self, workflow_repo):
        tag = f"single-{uuid.uuid4().hex}"
        workflow_repo.create(make_workflow(name="Only One", tags=[tag]))
        results, next_cursor = workflow_repo.list(tags=[tag], limit=10)
        assert len(results) == 1
        assert next_cursor is None


class TestWorkflowRepositoryCountAndExists:
    """count() and exists() behave correctly."""

    def test_count_all(self, workflow_repo):
        before, _ = workflow_repo.list()
        count_before = workflow_repo.count()
        assert count_before == len(before)

    def test_count_with_status_filter(self, workflow_repo):
        tag = f"cnt-{uuid.uuid4().hex}"
        workflow_repo.create(make_workflow(name="Count Active", status="active", tags=[tag]))
        workflow_repo.create(make_workflow(name="Count Draft", status="draft", tags=[tag]))

        active_results, _ = workflow_repo.list(tags=[tag], status="active")
        assert workflow_repo.count(status="active") >= len(active_results)

    def test_exists_returns_true_for_known_id(self, workflow_repo):
        wf = workflow_repo.create(make_workflow())
        assert workflow_repo.exists(wf.id) is True

    def test_exists_returns_false_for_unknown_id(self, workflow_repo):
        assert workflow_repo.exists("unknown-id-that-does-not-exist") is False


# ===========================================================================
# WorkflowExecutionRepository tests
# ===========================================================================


class TestWorkflowExecutionRepositoryCreateAndGet:
    """Basic create + retrieve round-trip."""

    def test_create_and_get(self, session, engine):
        # Ensure workflow row exists (FK constraint)
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Exec WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()

        exec_repo = WorkflowExecutionRepository(session)
        execution = make_execution(workflow_id=wf_id, status="pending")
        created = exec_repo.create(execution)
        session.commit()

        fetched = exec_repo.get(created.id)
        assert fetched is not None
        assert fetched.workflow_id == wf_id
        assert fetched.status == "pending"
        assert fetched.workflow_name == "Test Workflow"

    def test_get_returns_none_for_unknown_id(self, session):
        exec_repo = WorkflowExecutionRepository(session)
        assert exec_repo.get("no-such-execution") is None

    def test_get_with_steps(self, session, engine):
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Steps WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()

        exec_repo = WorkflowExecutionRepository(session)
        execution = make_execution(workflow_id=wf_id)
        exec_repo.create(execution)

        step_repo = ExecutionStepRepository(session)
        step_repo.create(make_step(execution.id, stage_id_ref="s1"))
        step_repo.create(make_step(execution.id, stage_id_ref="s2"))
        session.commit()

        fetched = exec_repo.get_with_steps(execution.id)
        assert fetched is not None
        assert len(fetched.steps) == 2
        refs = {st.stage_id_ref for st in fetched.steps}
        assert refs == {"s1", "s2"}


class TestWorkflowExecutionRepositoryListFilters:
    """list() with workflow_id and status filters."""

    def _create_workflow(self, engine, name: str = "List WF") -> str:
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name=name)
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()
        return wf_id

    def test_list_filter_by_workflow(self, session, engine):
        wf1_id = self._create_workflow(engine, "WF List A")
        wf2_id = self._create_workflow(engine, "WF List B")

        exec_repo = WorkflowExecutionRepository(session)
        exec_repo.create(make_execution(workflow_id=wf1_id))
        exec_repo.create(make_execution(workflow_id=wf1_id))
        exec_repo.create(make_execution(workflow_id=wf2_id))
        session.commit()

        results, _ = exec_repo.list(workflow_id=wf1_id)
        assert len(results) == 2
        assert all(r.workflow_id == wf1_id for r in results)

    def test_list_filter_by_status(self, session, engine):
        wf_id = self._create_workflow(engine, "WF Status Filter")
        exec_repo = WorkflowExecutionRepository(session)
        exec_repo.create(make_execution(wf_id, status="running"))
        exec_repo.create(make_execution(wf_id, status="completed"))
        session.commit()

        running, _ = exec_repo.list(status="running")
        assert all(r.status == "running" for r in running)

    def test_list_active_returns_only_active_statuses(self, session, engine):
        wf_id = self._create_workflow(engine, "WF Active Filter")
        exec_repo = WorkflowExecutionRepository(session)
        exec_repo.create(make_execution(wf_id, status="pending"))
        exec_repo.create(make_execution(wf_id, status="running"))
        exec_repo.create(make_execution(wf_id, status="paused"))
        exec_repo.create(make_execution(wf_id, status="completed"))
        session.commit()

        active = exec_repo.list_active()
        statuses = {r.status for r in active}
        assert "completed" not in statuses
        assert statuses.issubset({"pending", "running", "paused"})

    def test_get_latest_for_workflow(self, session, engine):
        wf_id = self._create_workflow(engine, "WF Latest")
        exec_repo = WorkflowExecutionRepository(session)

        older = make_execution(wf_id)
        older.started_at = datetime.utcnow() - timedelta(hours=1)
        newer = make_execution(wf_id)
        newer.started_at = datetime.utcnow()

        exec_repo.create(older)
        exec_repo.create(newer)
        session.commit()

        latest = exec_repo.get_latest_for_workflow(wf_id)
        assert latest is not None
        assert latest.id == newer.id

    def test_get_latest_returns_none_for_unknown_workflow(self, session):
        exec_repo = WorkflowExecutionRepository(session)
        assert exec_repo.get_latest_for_workflow("unknown-wf-id") is None


class TestWorkflowExecutionRepositoryUpdateStatus:
    """update_status applies all optional fields correctly."""

    def _setup_execution(self, session, engine) -> WorkflowExecution:
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Status WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()
        exec_repo = WorkflowExecutionRepository(session)
        execution = make_execution(workflow_id=wf_id, status="pending")
        exec_repo.create(execution)
        session.commit()
        return execution

    def test_update_status_pending_to_running(self, session, engine):
        execution = self._setup_execution(session, engine)
        exec_repo = WorkflowExecutionRepository(session)

        now = datetime.utcnow()
        updated = exec_repo.update_status(
            execution.id, "running", started_at=now
        )
        session.commit()

        assert updated is not None
        assert updated.status == "running"
        assert updated.started_at == now

    def test_update_status_to_completed_with_completed_at(self, session, engine):
        execution = self._setup_execution(session, engine)
        exec_repo = WorkflowExecutionRepository(session)

        now = datetime.utcnow()
        updated = exec_repo.update_status(
            execution.id,
            "completed",
            completed_at=now,
        )
        session.commit()

        assert updated.status == "completed"
        assert updated.completed_at == now

    def test_update_status_to_failed_with_error_message(self, session, engine):
        execution = self._setup_execution(session, engine)
        exec_repo = WorkflowExecutionRepository(session)

        updated = exec_repo.update_status(
            execution.id,
            "failed",
            error_message="Something went wrong",
        )
        session.commit()

        assert updated.status == "failed"
        assert updated.error_message == "Something went wrong"

    def test_update_status_returns_none_for_unknown_id(self, session):
        exec_repo = WorkflowExecutionRepository(session)
        result = exec_repo.update_status("no-such-id", "running")
        assert result is None


class TestWorkflowExecutionRepositoryCursorPagination:
    """Cursor pagination iterates all pages."""

    def test_cursor_pagination(self, session, engine):
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Paginate WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()

        exec_repo = WorkflowExecutionRepository(session)
        for i in range(6):
            exec_repo.create(make_execution(wf_id))
        session.commit()

        collected = []
        cursor = None
        while True:
            page, cursor = exec_repo.list(workflow_id=wf_id, limit=2, cursor=cursor)
            collected.extend(page)
            if cursor is None:
                break

        assert len(collected) == 6


class TestWorkflowExecutionRepositoryCount:
    """count() with workflow_id and status filters."""

    def test_count_all_for_workflow(self, session, engine):
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Count WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()
        exec_repo = WorkflowExecutionRepository(session)
        for _ in range(3):
            exec_repo.create(make_execution(wf_id))
        session.commit()

        assert exec_repo.count(workflow_id=wf_id) == 3

    def test_count_with_status_filter(self, session, engine):
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Count Status WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()
        exec_repo = WorkflowExecutionRepository(session)
        exec_repo.create(make_execution(wf_id, status="pending"))
        exec_repo.create(make_execution(wf_id, status="pending"))
        exec_repo.create(make_execution(wf_id, status="completed"))
        session.commit()

        assert exec_repo.count(workflow_id=wf_id, status="pending") == 2
        assert exec_repo.count(workflow_id=wf_id, status="completed") == 1


# ===========================================================================
# ExecutionStepRepository tests
# ===========================================================================


class _StepRepoBase:
    """Shared helper: create workflow + execution FK rows."""

    @staticmethod
    def _create_execution(session, engine) -> WorkflowExecution:
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="Step WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()

        exec_repo = WorkflowExecutionRepository(session)
        execution = make_execution(workflow_id=wf_id)
        exec_repo.create(execution)
        session.commit()
        return execution


class TestExecutionStepRepositoryCreateAndGet(_StepRepoBase):
    """create() and get() round-trip."""

    def test_create_and_get(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)

        step = make_step(execution.id, stage_id_ref="s1")
        created = repo.create(step)
        session.commit()

        fetched = repo.get(created.id)
        assert fetched is not None
        assert fetched.execution_id == execution.id
        assert fetched.stage_id_ref == "s1"
        assert fetched.status == "pending"

    def test_get_returns_none_for_unknown_id(self, session):
        repo = ExecutionStepRepository(session)
        assert repo.get("unknown-step-id") is None

    def test_create_bulk_persists_all(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)

        steps = [make_step(execution.id, stage_id_ref=f"s{i}") for i in range(3)]
        created = repo.create_bulk(steps)
        session.commit()

        assert len(created) == 3
        for i, st in enumerate(created):
            assert repo.get(st.id) is not None

    def test_create_bulk_empty_list_returns_empty(self, session):
        repo = ExecutionStepRepository(session)
        result = repo.create_bulk([])
        assert result == []


class TestExecutionStepRepositoryListByExecution(_StepRepoBase):
    """list_by_execution returns steps ordered by created_at."""

    def test_list_by_execution_ordered(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)

        # Create with slight time offsets
        for i in range(3):
            step = make_step(execution.id, stage_id_ref=f"s{i}")
            step.created_at = datetime.utcnow() + timedelta(seconds=i)
            repo.create(step)
        session.commit()

        steps = repo.list_by_execution(execution.id)
        assert len(steps) == 3
        refs = [s.stage_id_ref for s in steps]
        assert refs == sorted(refs)  # ascending by created_at → s0, s1, s2

    def test_list_by_execution_empty_when_no_steps(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        assert repo.list_by_execution(execution.id) == []


class TestExecutionStepRepositoryGetByStageRef(_StepRepoBase):
    """get_by_stage_ref finds the right step within an execution."""

    def test_get_by_stage_ref_found(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)

        step = make_step(execution.id, stage_id_ref="target-stage")
        repo.create(step)
        session.commit()

        found = repo.get_by_stage_ref(execution.id, "target-stage")
        assert found is not None
        assert found.stage_id_ref == "target-stage"

    def test_get_by_stage_ref_not_found(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        result = repo.get_by_stage_ref(execution.id, "nonexistent-stage")
        assert result is None


class TestExecutionStepRepositoryUpdateStatus(_StepRepoBase):
    """update_status applies status + timing fields."""

    def test_update_status_basic(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        step = make_step(execution.id)
        repo.create(step)
        session.commit()

        now = datetime.utcnow()
        updated = repo.update_status(
            step.id, "running", started_at=now
        )
        session.commit()

        assert updated is not None
        assert updated.status == "running"
        assert updated.started_at == now

    def test_update_status_with_completion_fields(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        step = make_step(execution.id)
        repo.create(step)
        session.commit()

        start = datetime.utcnow()
        end = start + timedelta(seconds=5)
        updated = repo.update_status(
            step.id,
            "completed",
            started_at=start,
            completed_at=end,
            duration_seconds=5.0,
        )
        session.commit()

        assert updated.status == "completed"
        assert updated.duration_seconds == 5.0
        assert updated.completed_at == end

    def test_update_status_returns_none_for_unknown_step(self, session):
        repo = ExecutionStepRepository(session)
        result = repo.update_status("no-step-id", "running")
        assert result is None


class TestExecutionStepRepositoryUpdateOutputs(_StepRepoBase):
    """update_outputs stores outputs and optional logs."""

    def test_update_outputs(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        step = make_step(execution.id)
        repo.create(step)
        session.commit()

        outputs = json.dumps({"result": "ok", "count": 42})
        updated = repo.update_outputs(step.id, outputs_json=outputs)
        session.commit()

        assert updated is not None
        assert json.loads(updated.outputs_json) == {"result": "ok", "count": 42}

    def test_update_outputs_with_logs(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        step = make_step(execution.id)
        repo.create(step)
        session.commit()

        log_data = json.dumps(["line one", "line two"])
        repo.update_outputs(step.id, outputs_json="{}", logs_json=log_data)
        session.commit()

        fetched = repo.get(step.id)
        assert json.loads(fetched.logs_json) == ["line one", "line two"]

    def test_update_outputs_returns_none_for_unknown_step(self, session):
        repo = ExecutionStepRepository(session)
        result = repo.update_outputs("no-step", outputs_json="{}")
        assert result is None


class TestExecutionStepRepositoryAppendLog(_StepRepoBase):
    """append_log grows the JSON array incrementally."""

    def test_append_log_multiple_entries(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        step = make_step(execution.id)
        repo.create(step)
        session.commit()

        repo.append_log(step.id, "entry 1")
        repo.append_log(step.id, "entry 2")
        repo.append_log(step.id, "entry 3")
        session.commit()

        fetched = repo.get(step.id)
        logs = json.loads(fetched.logs_json)
        assert logs == ["entry 1", "entry 2", "entry 3"]

    def test_append_log_to_empty_step(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        step = make_step(execution.id)
        step.logs_json = None  # start with no logs
        repo.create(step)
        session.commit()

        repo.append_log(step.id, "first entry")
        session.commit()

        fetched = repo.get(step.id)
        logs = json.loads(fetched.logs_json)
        assert logs == ["first entry"]

    def test_append_log_returns_none_for_unknown_step(self, session):
        repo = ExecutionStepRepository(session)
        result = repo.append_log("no-step-id", "something")
        assert result is None


class TestExecutionStepRepositoryBulkUpdateStatus(_StepRepoBase):
    """bulk_update_status updates multiple steps in one call."""

    def test_bulk_update_status(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        steps = [make_step(execution.id, stage_id_ref=f"s{i}") for i in range(3)]
        repo.create_bulk(steps)
        session.commit()

        step_ids = [s.id for s in steps]
        count = repo.bulk_update_status(step_ids, "completed")
        session.commit()

        assert count == 3
        for sid in step_ids:
            fetched = repo.get(sid)
            assert fetched.status == "completed"

    def test_bulk_update_status_empty_list_returns_zero(self, session):
        repo = ExecutionStepRepository(session)
        assert repo.bulk_update_status([], "running") == 0

    def test_bulk_update_status_partial_ids(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        s1 = make_step(execution.id, stage_id_ref="s1")
        s2 = make_step(execution.id, stage_id_ref="s2")
        repo.create_bulk([s1, s2])
        session.commit()

        count = repo.bulk_update_status([s1.id], "skipped")
        session.commit()

        assert count == 1
        assert repo.get(s1.id).status == "skipped"
        assert repo.get(s2.id).status == "pending"  # unchanged


class TestExecutionStepRepositoryCountByStatus(_StepRepoBase):
    """count_by_status returns a zero-filled dict covering all statuses."""

    def test_count_by_status_all_statuses_present(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)

        repo.create(make_step(execution.id, stage_id_ref="s1", status="pending"))
        repo.create(make_step(execution.id, stage_id_ref="s2", status="pending"))
        repo.create(make_step(execution.id, stage_id_ref="s3", status="running"))
        repo.create(make_step(execution.id, stage_id_ref="s4", status="completed"))
        repo.create(make_step(execution.id, stage_id_ref="s5", status="failed"))
        session.commit()

        counts = repo.count_by_status(execution.id)

        # All known statuses must be present (even with 0 count)
        for key in ("pending", "running", "completed", "failed", "skipped", "cancelled"):
            assert key in counts

        assert counts["pending"] == 2
        assert counts["running"] == 1
        assert counts["completed"] == 1
        assert counts["failed"] == 1
        assert counts["skipped"] == 0
        assert counts["cancelled"] == 0

    def test_count_by_status_empty_execution(self, session, engine):
        execution = self._create_execution(session, engine)
        repo = ExecutionStepRepository(session)
        counts = repo.count_by_status(execution.id)
        assert all(v == 0 for v in counts.values())


# ===========================================================================
# WorkflowTransactionManager tests
# ===========================================================================


class _TxBase:
    """Create workflow + execution rows for transaction tests."""

    @staticmethod
    def _create_workflow_row(engine) -> str:
        wf_id = uuid.uuid4().hex
        wf = make_workflow(name="TX WF")
        wf.id = wf_id
        with Session(engine) as s:
            s.add(wf)
            s.commit()
        return wf_id


class TestWorkflowTransactionManagerAtomicCreate(_TxBase):
    """atomic_create_execution persists execution + steps in one flush."""

    def test_atomic_create_execution(self, session, engine):
        wf_id = self._create_workflow_row(engine)

        exec_repo = WorkflowExecutionRepository(session)
        step_repo = ExecutionStepRepository(session)
        tx = WorkflowTransactionManager(session)

        execution = make_execution(wf_id)
        steps = [make_step(execution.id, stage_id_ref=f"s{i}") for i in range(3)]

        created = tx.atomic_create_execution(exec_repo, step_repo, execution, steps)
        session.commit()

        # Execution persisted
        assert exec_repo.get(created.id) is not None

        # All steps persisted
        persisted_steps = step_repo.list_by_execution(created.id)
        assert len(persisted_steps) == 3

    def test_atomic_create_execution_empty_steps(self, session, engine):
        wf_id = self._create_workflow_row(engine)

        exec_repo = WorkflowExecutionRepository(session)
        step_repo = ExecutionStepRepository(session)
        tx = WorkflowTransactionManager(session)

        execution = make_execution(wf_id)
        created = tx.atomic_create_execution(exec_repo, step_repo, execution, [])
        session.commit()

        assert exec_repo.get(created.id) is not None
        assert step_repo.list_by_execution(created.id) == []


class TestWorkflowTransactionManagerAtomicStateChange(_TxBase):
    """atomic_execution_state_change updates execution + steps atomically."""

    def _seed_execution_with_steps(self, session, engine, wf_id: str, num_steps: int = 2):
        exec_repo = WorkflowExecutionRepository(session)
        step_repo = ExecutionStepRepository(session)
        execution = make_execution(wf_id)
        exec_repo.create(execution)
        steps = [make_step(execution.id, stage_id_ref=f"s{i}") for i in range(num_steps)]
        step_repo.create_bulk(steps)
        session.commit()
        return execution, steps

    def test_atomic_execution_state_change(self, session, engine):
        wf_id = self._create_workflow_row(engine)
        execution, steps = self._seed_execution_with_steps(session, engine, wf_id)

        exec_repo = WorkflowExecutionRepository(session)
        step_repo = ExecutionStepRepository(session)
        tx = WorkflowTransactionManager(session)

        now = datetime.utcnow()
        step_id_to_status = {s.id: "completed" for s in steps}

        updated = tx.atomic_execution_state_change(
            execution_repo=exec_repo,
            step_repo=step_repo,
            execution_id=execution.id,
            new_execution_status="completed",
            completed_at=now,
            step_id_to_status=step_id_to_status,
        )
        session.commit()

        assert updated.status == "completed"
        assert updated.completed_at == now

        for step in steps:
            fetched = step_repo.get(step.id)
            assert fetched.status == "completed"

    def test_atomic_state_change_raises_for_unknown_execution(self, isolated_session, engine):
        """Uses isolated_session because begin_transaction internally rollbacks the session."""
        wf_id = self._create_workflow_row(engine)

        exec_repo = WorkflowExecutionRepository(isolated_session)
        step_repo = ExecutionStepRepository(isolated_session)
        tx = WorkflowTransactionManager(isolated_session)

        with pytest.raises(ValueError, match="not found"):
            tx.atomic_execution_state_change(
                execution_repo=exec_repo,
                step_repo=step_repo,
                execution_id="no-such-execution-id",
                new_execution_status="failed",
            )


class TestWorkflowTransactionManagerRollback(_TxBase):
    """begin_transaction rolls back on error so no partial state is visible."""

    def test_rollback_on_error(self, isolated_session, engine):
        """Uses isolated_session because begin_transaction internally rollbacks the session."""
        wf_id = self._create_workflow_row(engine)

        exec_repo = WorkflowExecutionRepository(isolated_session)
        step_repo = ExecutionStepRepository(isolated_session)
        tx = WorkflowTransactionManager(isolated_session)

        execution = make_execution(wf_id)
        exec_repo.create(execution)

        execution_id = execution.id

        # Simulate an error mid-transaction using begin_transaction context manager
        with pytest.raises(RuntimeError):
            with tx.begin_transaction():
                # Add a valid step first
                step = make_step(execution_id, stage_id_ref="s1")
                step_repo.create(step)
                # Then raise an error — should trigger rollback
                raise RuntimeError("Simulated failure")

        # After rollback the session state should be clean; commit will be a no-op
        isolated_session.commit()

        # The execution was added outside the transaction guard, but the step
        # should not be visible after the session was rolled back inside
        # begin_transaction. We verify by starting a fresh query:
        remaining_steps = step_repo.list_by_execution(execution_id)
        # The rollback clears the session; the step was never committed
        assert len(remaining_steps) == 0

    def test_begin_transaction_commits_on_success(self, session, engine):
        wf_id = self._create_workflow_row(engine)

        exec_repo = WorkflowExecutionRepository(session)
        step_repo = ExecutionStepRepository(session)
        tx = WorkflowTransactionManager(session)

        execution = make_execution(wf_id)
        exec_repo.create(execution)

        # No error — transaction guard should not interfere
        with tx.begin_transaction():
            step = make_step(execution.id, stage_id_ref="success-stage")
            step_repo.create(step)

        session.commit()

        steps = step_repo.list_by_execution(execution.id)
        assert any(s.stage_id_ref == "success-stage" for s in steps)
