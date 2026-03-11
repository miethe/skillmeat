"""Unit tests for WorkflowArtifactSyncService.

Tests use mock-based isolation (MagicMock) — no real DB or filesystem access.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, call, patch

import pytest

from skillmeat.core.services.workflow_artifact_sync_service import (
    WorkflowArtifactSyncService,
    _NoopSpan,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_repo():
    """Return a MagicMock standing in for WorkflowArtifactSyncRepository."""
    repo = MagicMock()
    repo.upsert_artifact_from_workflow.return_value = "deadbeef" * 4  # hex uuid
    repo.delete_artifact_for_workflow.return_value = True
    return repo


@pytest.fixture
def svc(mock_repo):
    """WorkflowArtifactSyncService with injected mock repository."""
    return WorkflowArtifactSyncService(repository=mock_repo)


# =============================================================================
# _NoopSpan
# =============================================================================


class TestNoopSpan:
    """Ensure the _NoopSpan context-manager behaves as a no-op."""

    def test_context_manager_enters_and_exits(self):
        span = _NoopSpan()
        with span as s:
            assert s is span

    def test_set_attribute_is_noop(self):
        span = _NoopSpan()
        span.set_attribute("key", "value")  # should not raise

    def test_record_exception_is_noop(self):
        span = _NoopSpan()
        span.record_exception(RuntimeError("boom"))  # should not raise

    def test_exit_returns_false(self):
        span = _NoopSpan()
        result = span.__exit__(None, None, None)
        assert result is False


# =============================================================================
# Sync — create / update / delete
# =============================================================================


class TestSyncFromWorkflowCreate:
    """Create operation delegates to upsert_artifact_from_workflow."""

    def test_create_calls_upsert(self, svc, mock_repo):
        svc.sync_from_workflow(
            workflow_id="wf-001",
            operation="create",
            name="deploy-pipeline",
            description="Runs deployment",
            version="1.0.0",
        )
        mock_repo.upsert_artifact_from_workflow.assert_called_once_with(
            workflow_id="wf-001",
            name="deploy-pipeline",
            description="Runs deployment",
            version="1.0.0",
            project_id=None,
            metadata=None,
        )
        mock_repo.delete_artifact_for_workflow.assert_not_called()

    def test_create_with_project_id(self, svc, mock_repo):
        svc.sync_from_workflow(
            workflow_id="wf-002",
            operation="create",
            name="ci-pipeline",
            project_id="my-project",
        )
        mock_repo.upsert_artifact_from_workflow.assert_called_once_with(
            workflow_id="wf-002",
            name="ci-pipeline",
            description=None,
            version=None,
            project_id="my-project",
            metadata=None,
        )

    def test_create_with_metadata(self, svc, mock_repo):
        extra = {"owner": "alice", "environment": "prod"}
        svc.sync_from_workflow(
            workflow_id="wf-003",
            operation="create",
            name="release-pipeline",
            metadata=extra,
        )
        mock_repo.upsert_artifact_from_workflow.assert_called_once_with(
            workflow_id="wf-003",
            name="release-pipeline",
            description=None,
            version=None,
            project_id=None,
            metadata=extra,
        )


class TestSyncFromWorkflowUpdate:
    """Update operation also delegates to upsert_artifact_from_workflow."""

    def test_update_calls_upsert(self, svc, mock_repo):
        svc.sync_from_workflow(
            workflow_id="wf-010",
            operation="update",
            name="deploy-pipeline",
            version="2.0.0",
        )
        mock_repo.upsert_artifact_from_workflow.assert_called_once_with(
            workflow_id="wf-010",
            name="deploy-pipeline",
            description=None,
            version="2.0.0",
            project_id=None,
            metadata=None,
        )
        mock_repo.delete_artifact_for_workflow.assert_not_called()


class TestSyncFromWorkflowDelete:
    """Delete operation delegates to delete_artifact_for_workflow."""

    def test_delete_calls_delete(self, svc, mock_repo):
        svc.sync_from_workflow(workflow_id="wf-020", operation="delete")
        mock_repo.delete_artifact_for_workflow.assert_called_once_with("wf-020")
        mock_repo.upsert_artifact_from_workflow.assert_not_called()

    def test_delete_returns_none(self, svc, mock_repo):
        result = svc.sync_from_workflow(workflow_id="wf-021", operation="delete")
        assert result is None


# =============================================================================
# Idempotency
# =============================================================================


class TestIdempotency:
    """Calling sync twice with the same data produces a single logical row."""

    def test_double_create_calls_upsert_twice(self, svc, mock_repo):
        """Each call issues an upsert; idempotency is enforced by the repository."""
        for _ in range(2):
            svc.sync_from_workflow(
                workflow_id="wf-030",
                operation="create",
                name="my-workflow",
            )

        assert mock_repo.upsert_artifact_from_workflow.call_count == 2
        # Both calls use the same arguments
        expected_call = call(
            workflow_id="wf-030",
            name="my-workflow",
            description=None,
            version=None,
            project_id=None,
            metadata=None,
        )
        mock_repo.upsert_artifact_from_workflow.assert_has_calls(
            [expected_call, expected_call]
        )


# =============================================================================
# Failure isolation
# =============================================================================


class TestFailureIsolation:
    """DB errors are caught and logged; they never propagate to the caller."""

    def test_upsert_exception_is_swallowed(self, svc, mock_repo, caplog):
        mock_repo.upsert_artifact_from_workflow.side_effect = RuntimeError(
            "DB connection lost"
        )
        with caplog.at_level(logging.ERROR):
            # Must NOT raise
            result = svc.sync_from_workflow(
                workflow_id="wf-040",
                operation="create",
                name="fragile-pipeline",
            )

        assert result is None
        assert any("sync_from_workflow failed" in r.message for r in caplog.records)
        assert any("wf-040" in r.message for r in caplog.records)

    def test_delete_exception_is_swallowed(self, svc, mock_repo, caplog):
        mock_repo.delete_artifact_for_workflow.side_effect = OSError("disk full")
        with caplog.at_level(logging.ERROR):
            result = svc.sync_from_workflow(
                workflow_id="wf-041",
                operation="delete",
            )

        assert result is None
        assert any("sync_from_workflow failed" in r.message for r in caplog.records)

    def test_error_log_includes_operation(self, svc, mock_repo, caplog):
        mock_repo.upsert_artifact_from_workflow.side_effect = ValueError("bad value")
        with caplog.at_level(logging.ERROR):
            svc.sync_from_workflow(
                workflow_id="wf-042",
                operation="update",
                name="pipeline",
            )

        assert any("operation=update" in r.message for r in caplog.records)

    def test_invalid_operation_is_swallowed(self, svc, mock_repo, caplog):
        """Unknown operations raise ValueError internally but are caught."""
        with caplog.at_level(logging.ERROR):
            result = svc.sync_from_workflow(
                workflow_id="wf-043",
                operation="teleport",
                name="pipeline",
            )
        assert result is None
        # The error should be logged
        assert len(caplog.records) > 0

    def test_missing_name_for_create_is_swallowed(self, svc, mock_repo, caplog):
        """Omitting 'name' for create triggers ValueError, which is caught."""
        with caplog.at_level(logging.ERROR):
            result = svc.sync_from_workflow(
                workflow_id="wf-044",
                operation="create",
                # name intentionally omitted
            )
        assert result is None


# =============================================================================
# Feature-flag guard (WorkflowService layer)
# =============================================================================


class TestFeatureFlagIntegration:
    """Ensure WorkflowService honours workflow_artifact_sync_enabled."""

    def _make_workflow_service(self, mock_sync_svc):
        """Construct a WorkflowService with injected mock sync service."""
        from skillmeat.core.workflow.service import WorkflowService

        # Provide a mock repository for WorkflowService base class
        mock_wf_repo = MagicMock()
        svc = WorkflowService.__new__(WorkflowService)
        svc._repository = mock_wf_repo
        svc._sync_service = mock_sync_svc
        return svc

    def test_sync_skipped_when_flag_false(self, mock_repo):
        """When workflow_artifact_sync_enabled=False, sync is not called."""
        mock_sync_svc = MagicMock()

        wf_svc = self._make_workflow_service(mock_sync_svc)

        # get_settings is imported lazily inside _sync_artifact; patch at source.
        with patch(
            "skillmeat.api.config.get_settings",
            return_value=MagicMock(workflow_artifact_sync_enabled=False),
        ):
            wf_svc._sync_artifact(
                workflow_id="wf-050",
                operation="create",
                name="guarded-pipeline",
            )

        mock_sync_svc.sync_from_workflow.assert_not_called()

    def test_sync_called_when_flag_true(self):
        """When workflow_artifact_sync_enabled=True, sync is called."""
        mock_sync_svc = MagicMock()

        wf_svc = self._make_workflow_service(mock_sync_svc)

        with patch(
            "skillmeat.api.config.get_settings",
            return_value=MagicMock(workflow_artifact_sync_enabled=True),
        ):
            wf_svc._sync_artifact(
                workflow_id="wf-051",
                operation="create",
                name="enabled-pipeline",
            )

        mock_sync_svc.sync_from_workflow.assert_called_once_with(
            workflow_id="wf-051",
            operation="create",
            name="enabled-pipeline",
            description=None,
            version=None,
        )

    def test_sync_skipped_when_no_service(self):
        """_sync_artifact is a no-op when _sync_service is None."""
        from skillmeat.core.workflow.service import WorkflowService

        wf_svc = WorkflowService.__new__(WorkflowService)
        wf_svc._repository = MagicMock()
        wf_svc._sync_service = None

        # Should return immediately without error
        wf_svc._sync_artifact(
            workflow_id="wf-052",
            operation="create",
            name="no-service-pipeline",
        )


# =============================================================================
# Structured logging
# =============================================================================


class TestStructuredLogging:
    """Verify INFO logs include workflow_id, operation, and duration_ms."""

    def test_success_log_contains_key_fields(self, svc, mock_repo, caplog):
        with caplog.at_level(logging.INFO):
            svc.sync_from_workflow(
                workflow_id="wf-060",
                operation="create",
                name="log-test-pipeline",
            )

        success_records = [
            r for r in caplog.records if "sync_from_workflow" in r.message
        ]
        assert success_records, "Expected at least one INFO log from sync_from_workflow"
        combined = " ".join(r.message for r in success_records)
        assert "wf-060" in combined
        assert "create" in combined
        assert "duration_ms" in combined

    def test_error_log_contains_duration_ms(self, svc, mock_repo, caplog):
        mock_repo.upsert_artifact_from_workflow.side_effect = RuntimeError("fail")
        with caplog.at_level(logging.ERROR):
            svc.sync_from_workflow(
                workflow_id="wf-061",
                operation="create",
                name="duration-log-test",
            )

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records
        combined = " ".join(r.message for r in error_records)
        assert "duration_ms" in combined


# =============================================================================
# sync_all_workflows
# =============================================================================


class TestSyncAllWorkflows:
    """sync_all_workflows pages through all workflows and calls _execute_sync."""

    def _make_workflow_stub(self, wf_id, name, description=None, version=None):
        wf = MagicMock()
        wf.id = wf_id
        wf.name = name
        wf.description = description
        wf.version = version
        return wf

    def test_sync_all_calls_upsert_for_each_workflow(self, svc, mock_repo):
        wf1 = self._make_workflow_stub("wf-100", "workflow-a")
        wf2 = self._make_workflow_stub("wf-101", "workflow-b", version="1.2.3")

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository"
        ) as MockWFRepo:
            mock_wf_repo = MockWFRepo.return_value
            # First page returns both workflows; second page returns empty + cursor=None
            mock_wf_repo.list.side_effect = [
                ([wf1, wf2], None),  # last page
            ]
            svc.sync_all_workflows()

        assert mock_repo.upsert_artifact_from_workflow.call_count == 2
        calls = mock_repo.upsert_artifact_from_workflow.call_args_list
        ids = [c.kwargs["workflow_id"] for c in calls]
        assert "wf-100" in ids
        assert "wf-101" in ids

    def test_sync_all_handles_multiple_pages(self, svc, mock_repo):
        wf1 = self._make_workflow_stub("wf-200", "workflow-page1")
        wf2 = self._make_workflow_stub("wf-201", "workflow-page2")

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository"
        ) as MockWFRepo:
            mock_wf_repo = MockWFRepo.return_value
            mock_wf_repo.list.side_effect = [
                ([wf1], "cursor-1"),  # page 1
                ([wf2], None),  # page 2 (last)
            ]
            svc.sync_all_workflows()

        assert mock_repo.upsert_artifact_from_workflow.call_count == 2

    def test_sync_all_isolates_per_workflow_failures(self, svc, mock_repo, caplog):
        """A failure on one workflow must not prevent the others from syncing."""
        wf1 = self._make_workflow_stub("wf-300", "good-workflow")
        wf2 = self._make_workflow_stub("wf-301", "bad-workflow")

        call_count = 0

        def flaky_upsert(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("workflow_id") == "wf-301":
                raise RuntimeError("simulated DB error")
            return "uuid-abc"

        mock_repo.upsert_artifact_from_workflow.side_effect = flaky_upsert

        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository"
        ) as MockWFRepo:
            mock_wf_repo = MockWFRepo.return_value
            mock_wf_repo.list.return_value = ([wf1, wf2], None)
            with caplog.at_level(logging.WARNING):
                svc.sync_all_workflows()

        # Both workflows were attempted
        assert call_count == 2
        # The failure was logged as a warning
        warning_msgs = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("wf-301" in m for m in warning_msgs)

    def test_sync_all_handles_repo_instantiation_failure(self, svc, caplog):
        """WorkflowRepository construction failure is caught and logged."""
        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository"
        ) as MockWFRepo:
            MockWFRepo.side_effect = RuntimeError("cannot open DB")
            with caplog.at_level(logging.ERROR):
                svc.sync_all_workflows()  # must not raise

        error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("failed to instantiate WorkflowRepository" in m for m in error_msgs)

    def test_sync_all_handles_list_failure(self, svc, caplog):
        """list() failure during pagination is caught and logged."""
        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository"
        ) as MockWFRepo:
            mock_wf_repo = MockWFRepo.return_value
            mock_wf_repo.list.side_effect = RuntimeError("query failed")
            with caplog.at_level(logging.ERROR):
                svc.sync_all_workflows()  # must not raise

        error_msgs = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("list() failed" in m for m in error_msgs)

    def test_sync_all_empty_workflow_table(self, svc, mock_repo):
        """No workflows in DB -> no upsert calls, no errors."""
        with patch(
            "skillmeat.cache.workflow_repository.WorkflowRepository"
        ) as MockWFRepo:
            mock_wf_repo = MockWFRepo.return_value
            mock_wf_repo.list.return_value = ([], None)
            svc.sync_all_workflows()

        mock_repo.upsert_artifact_from_workflow.assert_not_called()
