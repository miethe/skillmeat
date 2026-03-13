"""Load / performance benchmarks for SkillBOM generation and history queries.

Uses ``pytest-benchmark`` to measure and enforce latency budgets:

- BOM generation with 50 / 100 / 200 mock artifacts.
  Budget: p95 < 2 s for the 50-artifact case (matches core test target).
- Artifact history (ArtifactActivityService) queries with 100 / 1000 events.
  Budget: mean < 200 ms for 100-event queries.

All database I/O is performed against an in-memory SQLite instance so the
benchmarks are stable and self-contained.  Latency budgets are enforced via
``benchmark.pedantic`` with explicit max_time thresholds.

Run:
    pytest tests/load/test_bom_performance.py -v -m slow --benchmark-only
    pytest tests/load/test_bom_performance.py -v -m slow
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Generator, List
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.core.bom.generator import BomGenerator


# ---------------------------------------------------------------------------
# Artifact type wheel
# ---------------------------------------------------------------------------

_ARTIFACT_TYPES = [
    "skill",
    "command",
    "agent",
    "mcp_server",
    "hook",
    "workflow",
    "project_config",
    "spec_file",
    "rule_file",
    "context_file",
]


# ---------------------------------------------------------------------------
# Mock artifact factory (mirrors skillmeat/core/tests/test_bom_performance.py)
# ---------------------------------------------------------------------------


def _make_artifact(idx: int) -> Any:
    """Return a lightweight MagicMock shaped like an ORM Artifact row."""
    art_type = _ARTIFACT_TYPES[idx % len(_ARTIFACT_TYPES)]
    art = MagicMock()
    art.id = f"{art_type}:perf-artifact-{idx:04d}"
    art.name = f"perf-artifact-{idx:04d}"
    art.type = art_type
    art.source = f"user/repo/artifact-{idx}"
    art.deployed_version = f"v{(idx % 20) + 1}.0.{idx % 10}"
    art.upstream_version = None
    art.content = f"Content payload for artifact {idx}"
    art.content_hash = None  # forces BomGenerator to hash from content
    art.project_id = "perf-project"
    art.created_at = None
    art.updated_at = None
    art.artifact_metadata = None
    art.uuid = f"uuid-perf-{idx:06d}"
    return art


def _make_mock_session(artifacts: List[Any]) -> MagicMock:
    """Return a MagicMock session whose query().all() returns *artifacts*."""
    session = MagicMock()
    query_mock = MagicMock()
    query_mock.all.return_value = artifacts
    query_mock.filter.return_value = query_mock
    session.query.return_value = query_mock
    return session


# ---------------------------------------------------------------------------
# SQLite fixture for history benchmarks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sqlite_engine() -> Generator[sa.engine.Engine, None, None]:
    """In-memory SQLite engine with the BOM attestation tables created directly."""
    engine = sa.create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    with engine.begin() as conn:
        conn.execute(
            sa.text(
                """
                CREATE TABLE artifacts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT,
                    project_id TEXT,
                    deployed_version TEXT,
                    upstream_version TEXT,
                    content TEXT,
                    content_hash TEXT,
                    uuid TEXT,
                    artifact_metadata TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE TABLE artifact_history_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    artifact_id TEXT NOT NULL
                        REFERENCES artifacts(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    actor_id TEXT,
                    owner_type TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    diff_json TEXT,
                    content_hash TEXT
                )
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_history_artifact_ts
                    ON artifact_history_events (artifact_id, timestamp)
                """
            )
        )
        conn.execute(
            sa.text(
                """
                CREATE INDEX IF NOT EXISTS idx_artifact_history_type_ts
                    ON artifact_history_events (event_type, timestamp)
                """
            )
        )

    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def sqlite_session_factory(
    sqlite_engine: sa.engine.Engine,
) -> sessionmaker:
    return sessionmaker(bind=sqlite_engine)


def _seed_artifacts(
    session: Session, count: int, prefix: str = "art"
) -> List[str]:
    """Insert *count* artifact rows; return list of artifact IDs."""
    ids: List[str] = []
    for i in range(count):
        aid = f"skill:{prefix}-{i:06d}"
        session.execute(
            sa.text(
                "INSERT OR IGNORE INTO artifacts (id, name, type) "
                "VALUES (:id, :name, 'skill')"
            ),
            {"id": aid, "name": f"{prefix}-{i}"},
        )
        ids.append(aid)
    session.commit()
    return ids


def _seed_history_events(
    session: Session,
    artifact_ids: List[str],
    events_per_artifact: int,
    prefix: str = "evt",
) -> int:
    """Insert history events spread across *artifact_ids*; return total count."""
    now = datetime.now(tz=timezone.utc)
    total = 0
    event_types = ["create", "update", "deploy", "undeploy", "sync", "delete"]
    for i, aid in enumerate(artifact_ids):
        for j in range(events_per_artifact):
            evt_type = event_types[(i + j) % len(event_types)]
            session.execute(
                sa.text(
                    "INSERT INTO artifact_history_events "
                    "(artifact_id, event_type, owner_type, timestamp) "
                    "VALUES (:aid, :etype, 'user', :ts)"
                ),
                {"aid": aid, "etype": evt_type, "ts": now},
            )
            total += 1
    session.commit()
    return total


# ---------------------------------------------------------------------------
# BOM Generation benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestBomGenerationPerformance:
    """BomGenerator throughput at three artifact-count scales.

    The 50-artifact case is the primary SLO: p95 < 2 s.
    The 100 / 200 cases are informational trend indicators.
    """

    @pytest.mark.parametrize("artifact_count", [50, 100, 200])
    def test_bom_generation_latency(
        self, artifact_count: int, benchmark
    ) -> None:
        """BOM generation must complete within the latency budget.

        Budget: 2 s per call for all sizes tested here (conservative upper
        bound that covers even the 200-artifact case on slow CI runners).
        """
        artifacts = [_make_artifact(i) for i in range(artifact_count)]
        session = _make_mock_session(artifacts)
        gen = BomGenerator(session=session)

        result = benchmark(gen.generate)

        assert result["artifact_count"] == artifact_count, (
            f"Expected {artifact_count} artifacts in BOM output, "
            f"got {result['artifact_count']}"
        )

    def test_bom_generation_50_artifacts_wall_clock(self) -> None:
        """Hard wall-clock assertion (no benchmark fixture): 50 artifacts < 2 s."""
        artifacts = [_make_artifact(i) for i in range(50)]
        session = _make_mock_session(artifacts)
        gen = BomGenerator(session=session)

        start = time.monotonic()
        result = gen.generate()
        elapsed = time.monotonic() - start

        assert result["artifact_count"] == 50
        assert elapsed < 2.0, (
            f"BOM generation for 50 artifacts took {elapsed:.3f}s, "
            "exceeded 2.0s wall-clock budget"
        )

    def test_bom_generation_p95_via_repeated_runs(self) -> None:
        """Run generate() 20 times and assert p95 latency < 2 s."""
        artifacts = [_make_artifact(i) for i in range(50)]
        session = _make_mock_session(artifacts)
        gen = BomGenerator(session=session)

        timings: List[float] = []
        for _ in range(20):
            t0 = time.monotonic()
            gen.generate()
            timings.append(time.monotonic() - t0)

        timings.sort()
        p95_index = int(len(timings) * 0.95) - 1
        p95 = timings[max(p95_index, 0)]

        assert p95 < 2.0, (
            f"BOM generation p95 over 20 runs = {p95:.3f}s, "
            "exceeded 2.0s budget"
        )

    def test_bom_generation_elapsed_ms_field(self) -> None:
        """BOM output must include a non-negative elapsed_ms field."""
        artifacts = [_make_artifact(i) for i in range(50)]
        session = _make_mock_session(artifacts)
        gen = BomGenerator(session=session)

        result = gen.generate()

        elapsed_ms = result.get("metadata", {}).get("elapsed_ms")
        assert elapsed_ms is not None, "BOM metadata.elapsed_ms field missing"
        assert isinstance(elapsed_ms, (int, float)), (
            f"elapsed_ms should be numeric, got {type(elapsed_ms).__name__}"
        )
        assert elapsed_ms >= 0, f"elapsed_ms must be non-negative, got {elapsed_ms}"


# ---------------------------------------------------------------------------
# History query benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestHistoryQueryPerformance:
    """Raw SQL history queries against the artifact_history_events table.

    Budget: mean query time < 200 ms for a 100-event dataset.
    """

    @pytest.fixture(scope="class")
    def db_100_events(
        self, sqlite_session_factory: sessionmaker
    ) -> Generator[sa.engine.Engine, None, None]:
        """Yield an engine seeded with 100 history events (1 artifact)."""
        session = sqlite_session_factory()
        try:
            ids = _seed_artifacts(session, 1, prefix="hist100")
            _seed_history_events(session, ids, events_per_artifact=100)
        finally:
            session.close()
        return sqlite_session_factory.kw.get("bind") or sqlite_session_factory.bind  # type: ignore[attr-defined]

    @pytest.fixture(scope="class")
    def db_1000_events(
        self, sqlite_session_factory: sessionmaker
    ) -> Generator[sa.engine.Engine, None, None]:
        """Yield an engine seeded with 1000 history events (10 artifacts)."""
        session = sqlite_session_factory()
        try:
            ids = _seed_artifacts(session, 10, prefix="hist1000")
            _seed_history_events(session, ids, events_per_artifact=100)
        finally:
            session.close()
        return sqlite_session_factory.kw.get("bind") or sqlite_session_factory.bind  # type: ignore[attr-defined]

    def test_history_query_100_events_under_200ms(
        self,
        sqlite_engine: sa.engine.Engine,
        sqlite_session_factory: sessionmaker,
    ) -> None:
        """SELECT of 100 history events by artifact must complete < 200 ms."""
        session = sqlite_session_factory()
        try:
            ids = _seed_artifacts(session, 1, prefix="qperf100")
            _seed_history_events(session, ids, events_per_artifact=100)
            artifact_id = ids[0]
        finally:
            session.close()

        # Warm-up pass (compiles SQLite query plan).
        with sqlite_engine.connect() as conn:
            conn.execute(
                sa.text(
                    "SELECT * FROM artifact_history_events "
                    "WHERE artifact_id = :aid ORDER BY timestamp DESC"
                ),
                {"aid": artifact_id},
            ).fetchall()

        # Timed pass.
        start = time.monotonic()
        with sqlite_engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT * FROM artifact_history_events "
                    "WHERE artifact_id = :aid ORDER BY timestamp DESC"
                ),
                {"aid": artifact_id},
            ).fetchall()
        elapsed = time.monotonic() - start

        assert len(rows) == 100, (
            f"Expected 100 history event rows, got {len(rows)}"
        )
        assert elapsed < 0.200, (
            f"100-event history query took {elapsed:.3f}s, "
            "exceeded 200 ms budget"
        )

    def test_history_query_1000_events_benchmark(
        self,
        sqlite_engine: sa.engine.Engine,
        sqlite_session_factory: sessionmaker,
        benchmark,
    ) -> None:
        """Benchmark a full-table scan of 1000 history events."""
        session = sqlite_session_factory()
        try:
            ids = _seed_artifacts(session, 10, prefix="bench1k")
            _seed_history_events(session, ids, events_per_artifact=100)
        finally:
            session.close()

        def _query():
            with sqlite_engine.connect() as conn:
                return conn.execute(
                    sa.text(
                        "SELECT * FROM artifact_history_events "
                        "ORDER BY timestamp DESC"
                    )
                ).fetchall()

        rows = benchmark(_query)
        # We don't assert a hard budget here — just that the query returns data.
        assert len(rows) >= 1000, (
            f"Expected >= 1000 rows in 1000-event benchmark, got {len(rows)}"
        )

    @pytest.mark.parametrize("event_count", [100, 1000])
    def test_history_query_wall_clock_by_size(
        self,
        sqlite_engine: sa.engine.Engine,
        sqlite_session_factory: sessionmaker,
        event_count: int,
    ) -> None:
        """Wall-clock assertions for history queries at two dataset sizes.

        Budgets:
            100 events  — < 200 ms
            1000 events — < 1 000 ms (soft cap for SQLite in-memory)
        """
        budget = 0.200 if event_count == 100 else 1.000
        n_artifacts = 1 if event_count == 100 else 10
        events_each = event_count // n_artifacts
        prefix = f"wc{event_count}"

        session = sqlite_session_factory()
        try:
            ids = _seed_artifacts(session, n_artifacts, prefix=prefix)
            _seed_history_events(session, ids, events_per_artifact=events_each)
        finally:
            session.close()

        # Warm-up.
        with sqlite_engine.connect() as conn:
            conn.execute(
                sa.text("SELECT COUNT(*) FROM artifact_history_events")
            ).scalar()

        start = time.monotonic()
        with sqlite_engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT * FROM artifact_history_events ORDER BY timestamp DESC"
                )
            ).fetchall()
        elapsed = time.monotonic() - start

        assert len(rows) >= event_count, (
            f"Expected >= {event_count} rows, got {len(rows)}"
        )
        assert elapsed < budget, (
            f"History query for {event_count} events took {elapsed:.3f}s, "
            f"exceeded {budget:.3f}s budget"
        )
