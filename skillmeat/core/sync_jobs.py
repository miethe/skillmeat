"""Async sync job queue and runner."""

import logging
import threading
import uuid
from datetime import datetime, timezone
from queue import Queue, Empty
from typing import Callable, Optional

from skillmeat.config import ConfigManager
from skillmeat.models import SyncJobRecord, SyncJobState
from skillmeat.storage import SyncJobStore

logger = logging.getLogger(__name__)


class SyncJobRunner:
    """In-process job runner that persists job state and executes sync tasks."""

    def __init__(
        self,
        sync_fn: Callable[[SyncJobRecord], SyncJobRecord],
        config_mgr: Optional[ConfigManager] = None,
        store: Optional[SyncJobStore] = None,
    ):
        self.config_mgr = config_mgr or ConfigManager()
        self.store = store or SyncJobStore(config_dir=self.config_mgr.config_dir)
        self.sync_fn = sync_fn
        self._queue: Queue[str] = Queue()
        self._threads_started = False
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start worker thread and enqueue any recovered jobs."""
        if self._threads_started:
            return
        self._threads_started = True
        recovered = self.store.recover_incomplete_jobs()
        for job in recovered:
            self._queue.put(job.id)
        worker = threading.Thread(
            target=self._run_loop,
            name="sync-job-runner",
            daemon=True,
        )
        worker.start()

    def enqueue(self, job: SyncJobRecord) -> None:
        """Add a job to the queue."""
        self.store.save_job(job)
        self._queue.put(job.id)

    def shutdown(self) -> None:
        """Signal shutdown (best-effort, in-process only)."""
        self._stop_event.set()

    def _run_loop(self) -> None:
        """Worker loop consuming the queue."""
        while not self._stop_event.is_set():
            try:
                job_id = self._queue.get(timeout=0.5)
            except Empty:
                continue

            job = self.store.get_job(job_id)
            if not job:
                continue

            if not self.config_mgr.is_sync_async_enabled():
                # kill-switch: mark canceled
                job.state = SyncJobState.CANCELED
                job.ended_at = datetime.now(timezone.utc)
                job.log_excerpt = "Kill-switch enabled; job canceled"
                self.store.save_job(job)
                self._queue.task_done()
                continue

            try:
                job.state = SyncJobState.RUNNING
                job.started_at = datetime.now(timezone.utc)
                job.attempts += 1
                job.pct_complete = 0.05
                self.store.save_job(job)

                # Execute sync
                job = self.sync_fn(job)

                if job.state not in {SyncJobState.SUCCESS, SyncJobState.CONFLICT}:
                    job.state = SyncJobState.SUCCESS
                job.pct_complete = 1.0
                job.ended_at = job.ended_at or datetime.now(timezone.utc)
                self.store.save_job(job)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Sync job failed", extra={"job_id": job.id})
                job.state = SyncJobState.ERROR
                job.log_excerpt = str(exc)
                job.ended_at = datetime.now(timezone.utc)
                self.store.save_job(job)
            finally:
                self._queue.task_done()


class InProcessJobService:
    """Facade for creating and tracking jobs through the runner."""

    def __init__(self, sync_fn: Callable[[SyncJobRecord], SyncJobRecord]):
        self.config_mgr = ConfigManager()
        self.store = SyncJobStore(config_dir=self.config_mgr.config_dir)
        self.runner = SyncJobRunner(sync_fn=sync_fn, config_mgr=self.config_mgr, store=self.store)
        self.runner.start()

    def create_job(
        self,
        direction: str,
        artifacts: Optional[list[str]] = None,
        project_path: Optional[str] = None,
        collection: Optional[str] = None,
        strategy: Optional[str] = None,
        dry_run: bool = False,
        trace_id: Optional[str] = None,
    ) -> SyncJobRecord:
        """Create and enqueue a job."""
        if not self.config_mgr.is_sync_async_enabled():
            raise ValueError("Async sync disabled by configuration")

        job = SyncJobRecord(
            id=uuid.uuid4().hex,
            direction=direction,
            artifacts=artifacts or [],
            project_path=project_path,
            collection=collection,
            strategy=strategy,
            dry_run=dry_run,
            trace_id=trace_id or uuid.uuid4().hex,
            created_at=datetime.now(timezone.utc),
        )
        self.store.save_job(job)
        self.runner.enqueue(job)
        return job

    def get_job(self, job_id: str) -> Optional[SyncJobRecord]:
        """Return a job by ID."""
        return self.store.get_job(job_id)

    def list_recent(self, limit: int = 50) -> list[SyncJobRecord]:
        """List recent jobs."""
        return self.store.list_jobs(limit=limit)
