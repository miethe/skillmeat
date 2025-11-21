"""Persistent job store for async sync operations.

Uses SQLite by default with JSONL fallback to survive restarts. Provides
idempotent reads and replay of runnable jobs (queued or previously running).
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from skillmeat.config import ConfigManager
from skillmeat.models import ConflictInfo, SyncJobRecord, SyncJobState


class SyncJobStore:
    """Manages persistence of sync jobs with SQLite primary and JSONL fallback."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        jsonl_path: Optional[Path] = None,
        config_dir: Optional[Path] = None,
    ):
        self.config_mgr = ConfigManager(config_dir=config_dir)
        self.jobs_dir = self.config_mgr.get_sync_jobs_dir()

        preferred_backend = self.config_mgr.get_sync_job_store_backend()
        self._sqlite_forced_off = preferred_backend.lower() == "jsonl"

        self.db_path = db_path or (self.jobs_dir / "sync_jobs.db")
        self.jsonl_path = jsonl_path or (self.jobs_dir / "sync_jobs.jsonl")
        self.connection: Optional[sqlite3.Connection] = None
        self._sqlite_ready = False

        self._init_store()

    def _init_store(self) -> None:
        """Initialize storage; prefer SQLite, fallback to JSONL."""
        if self._sqlite_forced_off:
            self._ensure_jsonl_file()
            return
        try:
            self.connection = sqlite3.connect(
                str(self.db_path), check_same_thread=False
            )
            self.connection.row_factory = sqlite3.Row
        except Exception:
            self.connection = None
            self._sqlite_ready = False
            self._ensure_jsonl_file()
            return

        try:
            self._apply_schema()
            self._sqlite_ready = True
        except Exception:
            # SQLite unavailable; fallback to JSONL
            self.connection = None
            self._sqlite_ready = False
            self._ensure_jsonl_file()

    def _apply_schema(self) -> None:
        """Apply initial schema for sync jobs."""
        assert self.connection is not None
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sync_jobs (
                id TEXT PRIMARY KEY,
                direction TEXT NOT NULL,
                artifacts TEXT,
                project_path TEXT,
                collection TEXT,
                strategy TEXT,
                dry_run INTEGER DEFAULT 0,
                state TEXT NOT NULL,
                pct_complete REAL DEFAULT 0,
                started_at TEXT,
                ended_at TEXT,
                created_at TEXT,
                trace_id TEXT,
                log_excerpt TEXT,
                conflicts TEXT,
                attempts INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_sync_jobs_state ON sync_jobs(state);
            CREATE INDEX IF NOT EXISTS idx_sync_jobs_trace ON sync_jobs(trace_id);
            """
        )
        self.connection.commit()

    def _ensure_jsonl_file(self) -> None:
        """Ensure JSONL fallback file exists."""
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.jsonl_path.exists():
            self.jsonl_path.touch()

    def _row_to_job(self, row) -> SyncJobRecord:
        """Convert SQLite row to job record."""
        artifacts = json.loads(row["artifacts"]) if row["artifacts"] else []
        conflicts_raw = json.loads(row["conflicts"]) if row["conflicts"] else []
        conflicts: List[ConflictInfo] = [
            ConflictInfo.from_dict(c) if isinstance(c, dict) else c
            for c in conflicts_raw
        ]
        return SyncJobRecord(
            id=row["id"],
            direction=row["direction"],
            artifacts=artifacts or None,
            project_path=row["project_path"],
            collection=row["collection"],
            strategy=row["strategy"],
            dry_run=bool(row["dry_run"]),
            state=SyncJobState(row["state"]),
            pct_complete=float(row["pct_complete"] or 0.0),
            started_at=datetime.fromisoformat(row["started_at"])
            if row["started_at"]
            else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            trace_id=row["trace_id"],
            log_excerpt=row["log_excerpt"],
            conflicts=conflicts,
            attempts=int(row["attempts"] or 0),
        )

    def create_job(
        self,
        direction: str,
        artifacts: Optional[List[str]] = None,
        project_path: Optional[str] = None,
        collection: Optional[str] = None,
        strategy: Optional[str] = None,
        dry_run: bool = False,
        trace_id: Optional[str] = None,
    ) -> SyncJobRecord:
        """Create and persist a new job record."""
        now = datetime.utcnow()
        job = SyncJobRecord(
            id=uuid.uuid4().hex,
            direction=direction,
            artifacts=artifacts or [],
            project_path=project_path,
            collection=collection,
            strategy=strategy,
            dry_run=dry_run,
            trace_id=trace_id,
            created_at=now,
        )
        return self.save_job(job)

    def save_job(self, job: SyncJobRecord) -> SyncJobRecord:
        """Insert or replace a job record."""
        if self._sqlite_ready and self.connection:
            payload = job.to_dict()
            self.connection.execute(
                """
                INSERT OR REPLACE INTO sync_jobs (
                    id, direction, artifacts, project_path, collection, strategy,
                    dry_run, state, pct_complete, started_at, ended_at, created_at,
                    trace_id, log_excerpt, conflicts, attempts
                )
                VALUES (
                    :id, :direction, :artifacts, :project_path, :collection, :strategy,
                    :dry_run, :state, :pct_complete, :started_at, :ended_at,
                    :created_at, :trace_id, :log_excerpt, :conflicts, :attempts
                )
                """,
                {
                    **payload,
                    "artifacts": json.dumps(payload["artifacts"]),
                    "conflicts": json.dumps(payload["conflicts"]),
                },
            )
            self.connection.commit()
            return job

        jobs = self._read_jsonl_jobs()
        jobs[job.id] = job.to_dict()
        self._write_jsonl_jobs(jobs.values())
        return job

    def get_job(self, job_id: str) -> Optional[SyncJobRecord]:
        """Fetch a job by ID."""
        if self._sqlite_ready and self.connection:
            cursor = self.connection.execute(
                "SELECT * FROM sync_jobs WHERE id = ?", (job_id,)
            )
            row = cursor.fetchone()
            return self._row_to_job(row) if row else None

        jobs = self._read_jsonl_jobs()
        data = jobs.get(job_id)
        return SyncJobRecord.from_dict(data) if data else None

    def list_jobs(
        self, states: Optional[Iterable[SyncJobState]] = None, limit: Optional[int] = None
    ) -> List[SyncJobRecord]:
        """List jobs filtered by state."""
        if self._sqlite_ready and self.connection:
            params: List[str] = []
            sql = "SELECT * FROM sync_jobs"
            state_list = list(states) if states else []
            if state_list:
                placeholders = ",".join(["?"] * len(state_list))
                sql += f" WHERE state IN ({placeholders})"
                params = [state.value for state in state_list]
            sql += " ORDER BY created_at DESC"
            if limit:
                sql += " LIMIT ?"
                params.append(limit)
            cursor = self.connection.execute(sql, params)
            return [self._row_to_job(r) for r in cursor.fetchall()]

        jobs = self._read_jsonl_jobs()
        filtered = []
        for data in jobs.values():
            state_values = {s.value for s in states} if states else None
            if state_values and data.get("state") not in state_values:
                continue
            filtered.append(SyncJobRecord.from_dict(data))
        filtered.sort(key=lambda j: j.created_at or datetime.utcnow(), reverse=True)
        return filtered[:limit] if limit else filtered

    def recover_incomplete_jobs(self) -> List[SyncJobRecord]:
        """Reset running jobs to queued for replay after restart."""
        runnable_states = {SyncJobState.QUEUED, SyncJobState.RUNNING}
        jobs = self.list_jobs(states=runnable_states)
        recovered: List[SyncJobRecord] = []
        for job in jobs:
            if job.state == SyncJobState.RUNNING:
                job.state = SyncJobState.QUEUED
                job.started_at = None
                job.ended_at = None
                job.attempts += 1
                self.save_job(job)
                recovered.append(job)
        return jobs

    def _read_jsonl_jobs(self) -> dict:
        """Read all jobs from JSONL fallback."""
        self._ensure_jsonl_file()
        jobs = {}
        with open(self.jsonl_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    jobs[data["id"]] = data
                except Exception:
                    continue
        return jobs

    def _write_jsonl_jobs(self, jobs: Iterable[dict]) -> None:
        """Rewrite JSONL file with provided jobs."""
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.jsonl_path, "w", encoding="utf-8") as handle:
            for job in jobs:
                handle.write(json.dumps(job))
                handle.write("\n")
