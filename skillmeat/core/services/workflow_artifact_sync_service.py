"""Service for synchronising workflow records to the artifacts table.

This service bridges the ``workflows`` table and the ``artifacts`` table so
that create/update/delete lifecycle events on workflows are reflected in the
unified artifact collection without coupling the primary workflow write path
to the sync logic.

Design principles:
    - **Failure isolation**: Sync errors are caught and logged; they NEVER
      propagate to the caller.  The primary workflow write must succeed even
      when sync fails.
    - **Idempotency**: Multiple calls with the same ``(workflow_id, operation)``
      produce the same final state — safe to retry.
    - **Observability**: Structured log lines at INFO level include
      ``workflow_id``, ``operation``, and ``duration_ms``.  An OpenTelemetry
      span is emitted when the ``opentelemetry`` package is available.
    - **Dependency injection**: The ``WorkflowArtifactSyncRepository`` can be
      supplied by the caller (e.g. for testing), or the service creates a
      default instance backed by the standard cache database path.

Usage::

    svc = WorkflowArtifactSyncService()

    # On workflow create / update:
    svc.sync_from_workflow(
        workflow_id="abc123",
        operation="create",
        name="deploy-pipeline",
        description="Runs the deployment pipeline",
        version="1.0.0",
    )

    # On workflow delete:
    svc.sync_from_workflow(workflow_id="abc123", operation="delete")

    # Bulk re-sync (e.g. after a migration):
    svc.sync_all_workflows()
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional OpenTelemetry import — silently skipped when not installed.
# ---------------------------------------------------------------------------

try:
    from opentelemetry import trace as _otel_trace

    _tracer = _otel_trace.get_tracer(__name__)
    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover — OTel is optional
    _OTEL_AVAILABLE = False
    _tracer = None  # type: ignore[assignment]


class WorkflowArtifactSyncService:
    """Synchronises workflow lifecycle events to the artifacts table.

    This service is intentionally thin: it wraps ``WorkflowArtifactSyncRepository``
    with failure isolation, structured logging, and optional OTel tracing.

    Attributes:
        _repository: The underlying repository instance used for DB operations.
    """

    def __init__(
        self,
        repository=None,
        db_path=None,
    ) -> None:
        """Initialise the service.

        Args:
            repository: Optional pre-constructed
                :class:`~skillmeat.core.services.workflow_artifact_sync_repository.WorkflowArtifactSyncRepository`
                instance.  When ``None``, a default repository is created
                automatically (backed by ``~/.skillmeat/cache/cache.db``).
            db_path: Optional path forwarded to the default repository
                constructor.  Ignored when ``repository`` is supplied
                explicitly.
        """
        if repository is not None:
            self._repository = repository
        else:
            # Lazy import avoids circular dependencies at module load time.
            from skillmeat.core.services.workflow_artifact_sync_repository import (
                WorkflowArtifactSyncRepository,
            )

            self._repository = WorkflowArtifactSyncRepository(db_path=db_path)

        logger.debug(
            "WorkflowArtifactSyncService initialised with repository=%r",
            self._repository,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_from_workflow(
        self,
        workflow_id: str,
        operation: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        version: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Sync a single workflow lifecycle event to the artifacts table.

        This method is the primary integration point.  It must be called by
        the workflow service layer after a successful workflow write (create,
        update, or delete) so the artifact mirror stays in sync.

        Exceptions raised during the sync are caught and logged — they will
        NEVER propagate to the caller.

        Args:
            workflow_id: Primary key of the ``workflows`` row being synced.
            operation: One of ``"create"``, ``"update"``, or ``"delete"``.
                ``"create"`` and ``"update"`` both call
                :meth:`~WorkflowArtifactSyncRepository.upsert_artifact_from_workflow`;
                ``"delete"`` calls
                :meth:`~WorkflowArtifactSyncRepository.delete_artifact_for_workflow`.
            name: Workflow name (required for ``"create"``/``"update"``).
            description: Optional workflow description.
            version: Optional version string.
            project_id: Optional real project ID to associate the artifact row
                with.
            metadata: Optional extra key-value pairs stored in
                ``ArtifactMetadata``.

        Returns:
            ``None`` — result is communicated via logs and OTel spans.

        Example::

            svc.sync_from_workflow(
                workflow_id="abc123",
                operation="update",
                name="deploy-pipeline",
                version="2.0.0",
            )
        """
        start_ms = time.monotonic() * 1000

        if _OTEL_AVAILABLE and _tracer is not None:
            span_ctx = _tracer.start_as_current_span("workflow_artifact_sync")
        else:
            span_ctx = _NoopSpan()

        with span_ctx as span:
            if _OTEL_AVAILABLE and hasattr(span, "set_attribute"):
                span.set_attribute("workflow.id", workflow_id)
                span.set_attribute("operation", operation)

            try:
                self._execute_sync(
                    workflow_id=workflow_id,
                    operation=operation,
                    name=name,
                    description=description,
                    version=version,
                    project_id=project_id,
                    metadata=metadata,
                )
            except Exception as exc:  # noqa: BLE001 — deliberate broad catch
                duration_ms = round(time.monotonic() * 1000 - start_ms, 1)
                logger.error(
                    "WorkflowArtifactSyncService.sync_from_workflow failed: "
                    "workflow_id=%s operation=%s duration_ms=%.1f error=%r",
                    workflow_id,
                    operation,
                    duration_ms,
                    exc,
                )
                if _OTEL_AVAILABLE and hasattr(span, "record_exception"):
                    span.record_exception(exc)
                # Intentionally swallowed — primary write must not be blocked.
                return

            duration_ms = round(time.monotonic() * 1000 - start_ms, 1)

            if _OTEL_AVAILABLE and hasattr(span, "set_attribute"):
                span.set_attribute("duration_ms", duration_ms)

            logger.info(
                "WorkflowArtifactSyncService.sync_from_workflow: "
                "workflow_id=%s operation=%s duration_ms=%.1f",
                workflow_id,
                operation,
                duration_ms,
            )

    def sync_all_workflows(self) -> None:
        """Bulk re-sync all workflows to the artifacts table.

        Iterates every ``Workflow`` row in the DB and calls
        :meth:`sync_from_workflow` with ``operation="create"`` (which maps to
        an idempotent upsert).  Safe to call multiple times — each call
        produces the same final state.

        Failures for individual workflows are isolated: a single bad row does
        not prevent the remaining rows from syncing.

        This method is intended for use after migrations or when the artifacts
        table has drifted out of sync with the workflows table.

        Returns:
            ``None`` — progress is reported via log lines.

        Example::

            svc = WorkflowArtifactSyncService()
            svc.sync_all_workflows()  # brings artifact mirrors up to date
        """
        from skillmeat.cache.workflow_repository import WorkflowRepository

        logger.info(
            "WorkflowArtifactSyncService.sync_all_workflows: starting bulk sync"
        )

        try:
            repo = WorkflowRepository()
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "WorkflowArtifactSyncService.sync_all_workflows: "
                "failed to instantiate WorkflowRepository: %r",
                exc,
            )
            return

        # Page through all workflows using cursor pagination.
        cursor: Optional[str] = None
        page_size = 100
        total_attempted = 0
        total_ok = 0

        while True:
            try:
                workflows, next_cursor = repo.list(cursor=cursor, limit=page_size)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "WorkflowArtifactSyncService.sync_all_workflows: "
                    "list() failed (cursor=%s): %r",
                    cursor,
                    exc,
                )
                break

            for wf in workflows:
                total_attempted += 1
                start_ms = time.monotonic() * 1000
                try:
                    self._execute_sync(
                        workflow_id=wf.id,
                        operation="create",
                        name=wf.name,
                        description=wf.description,
                        version=wf.version if hasattr(wf, "version") else None,
                        project_id=None,
                        metadata=None,
                    )
                    total_ok += 1
                except Exception as exc:  # noqa: BLE001
                    duration_ms = round(time.monotonic() * 1000 - start_ms, 1)
                    logger.warning(
                        "WorkflowArtifactSyncService.sync_all_workflows: "
                        "skipping workflow_id=%s name=%r "
                        "duration_ms=%.1f error=%r",
                        wf.id,
                        wf.name,
                        duration_ms,
                        exc,
                    )

            if next_cursor is None:
                break
            cursor = next_cursor

        logger.info(
            "WorkflowArtifactSyncService.sync_all_workflows: "
            "completed total_attempted=%d total_ok=%d",
            total_attempted,
            total_ok,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_sync(
        self,
        workflow_id: str,
        operation: str,
        name: Optional[str],
        description: Optional[str],
        version: Optional[str],
        project_id: Optional[str],
        metadata: Optional[dict],
    ) -> None:
        """Dispatch a sync operation to the repository.

        Args:
            workflow_id: Primary key from the ``workflows`` table.
            operation: ``"create"``, ``"update"``, or ``"delete"``.
            name: Workflow name (required for create/update).
            description: Optional description.
            version: Optional version string.
            project_id: Optional project to associate the artifact row with.
            metadata: Optional extra metadata payload.

        Raises:
            ValueError: If ``operation`` is not one of the accepted values or
                if ``name`` is missing for a create/update operation.
            RuntimeError: Propagated from the repository on hard DB failures.
        """
        if operation in ("create", "update"):
            if not name:
                raise ValueError(
                    f"WorkflowArtifactSyncService: 'name' is required for "
                    f"operation='{operation}' (workflow_id={workflow_id})"
                )
            self._repository.upsert_artifact_from_workflow(
                workflow_id=workflow_id,
                name=name,
                description=description,
                version=version,
                project_id=project_id,
                metadata=metadata,
            )
        elif operation == "delete":
            self._repository.delete_artifact_for_workflow(workflow_id)
        else:
            raise ValueError(
                f"WorkflowArtifactSyncService: unknown operation '{operation}' "
                f"(workflow_id={workflow_id}). Expected 'create', 'update', or 'delete'."
            )


# ---------------------------------------------------------------------------
# Internal context manager used when OTel is unavailable.
# ---------------------------------------------------------------------------


class _NoopSpan:
    """No-op context manager that stands in for an OTel span."""

    def __enter__(self):
        return self

    def __exit__(self, *args):  # noqa: ARG002
        return False

    def set_attribute(self, _key: str, _value: object) -> None:
        """No-op."""

    def record_exception(self, _exception: BaseException) -> None:
        """No-op."""
