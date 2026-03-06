"""Performance benchmarks for enterprise repository operations (ENT-2.14).

Measures median latency for the six core repository operations and asserts
against published SLA targets:

    Operation            Target
    -------              ------
    get (PK lookup)      < 1 ms
    list(1000)           < 10 ms
    search_by_tags       < 5 ms
    list_artifacts       < 5 ms
    create               < 5 ms
    list paginated×10    < 50 ms total

Prerequisites
-------------
Start PostgreSQL::

    docker compose -f docker-compose.test.yml up -d postgres

Or point DATABASE_URL at a running instance.

Run::

    pytest -m "enterprise and performance" \\
        tests/integration/test_enterprise_benchmarks.py -v

All benchmarks are automatically skipped when PostgreSQL is unreachable
(same ``pg_engine`` fixture skip-propagation as ENT-2.13).
"""

from __future__ import annotations

import statistics
import time
import uuid
from typing import Dict, Generator, List

import pytest
from sqlalchemy import insert
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.enterprise_repositories import (
    EnterpriseArtifactRepository,
    EnterpriseCollectionRepository,
    tenant_scope,
)
from skillmeat.cache.models_enterprise import (
    EnterpriseArtifact,
    EnterpriseCollection,
    EnterpriseCollectionArtifact,
    EnterpriseArtifactVersion,
)

# ---------------------------------------------------------------------------
# Threshold constants (seconds)
# ---------------------------------------------------------------------------

THRESHOLDS: Dict[str, float] = {
    "get": 0.001,          # 1 ms
    "list_1000": 0.010,    # 10 ms
    "search": 0.005,       # 5 ms
    "list_artifacts": 0.005,  # 5 ms
    "create": 0.005,       # 5 ms
}

# How many repeated calls to take the median over
_REPEATS = 15

# Stable benchmark tenant — unique enough to avoid collisions across re-runs
_BENCH_TENANT = uuid.UUID("be0cb000-beef-4000-b000-000000000014")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uname(prefix: str = "bench") -> str:
    """Return a short unique name."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _purge_bench_tenant(session: Session) -> None:
    """Remove all rows belonging to _BENCH_TENANT in correct FK order."""
    from sqlalchemy import select, delete

    artifact_ids = list(
        session.execute(
            select(EnterpriseArtifact.id).where(
                EnterpriseArtifact.tenant_id == _BENCH_TENANT
            )
        ).scalars()
    )
    if artifact_ids:
        session.execute(
            EnterpriseCollectionArtifact.__table__.delete().where(
                EnterpriseCollectionArtifact.artifact_id.in_(artifact_ids)
            )
        )
        session.execute(
            EnterpriseArtifactVersion.__table__.delete().where(
                EnterpriseArtifactVersion.tenant_id == _BENCH_TENANT
            )
        )
        session.execute(
            EnterpriseArtifact.__table__.delete().where(
                EnterpriseArtifact.tenant_id == _BENCH_TENANT
            )
        )
    session.execute(
        EnterpriseCollection.__table__.delete().where(
            EnterpriseCollection.tenant_id == _BENCH_TENANT
        )
    )
    session.commit()


def _bulk_insert_artifacts(
    session: Session,
    count: int,
    tags_cycle: List[List[str]] | None = None,
) -> List[uuid.UUID]:
    """Bulk-insert *count* EnterpriseArtifact rows, bypassing the repository
    layer so setup time does not pollute benchmark measurements.

    Returns the list of inserted UUIDs.
    """
    import json

    if tags_cycle is None:
        tags_cycle = [[f"tag-{i % 10}"] for i in range(10)]

    rows = []
    ids = []
    for i in range(count):
        art_id = uuid.uuid4()
        ids.append(art_id)
        rows.append(
            {
                "id": art_id,
                "tenant_id": _BENCH_TENANT,
                "name": f"bench-art-{i:05d}-{art_id.hex[:6]}",
                "artifact_type": "skill",
                "is_active": True,
                "tags": json.dumps(tags_cycle[i % len(tags_cycle)]),
                "custom_fields": "{}",
                "source_url": None,
                "description": None,
            }
        )

    # Use core INSERT for maximum speed
    session.execute(
        EnterpriseArtifact.__table__.insert(),
        rows,
    )
    session.commit()
    return ids


# ---------------------------------------------------------------------------
# Session fixture (same pattern as ENT-2.13 repo_session)
# ---------------------------------------------------------------------------


@pytest.fixture
def bench_session(pg_engine, enterprise_tables) -> Generator[Session, None, None]:
    """Fresh session per benchmark test; commits are allowed.

    Cleanup removes all rows in _BENCH_TENANT after each test so that
    successive benchmarks start from a clean slate.
    """
    SessionFactory = sessionmaker(bind=pg_engine)
    session = SessionFactory()
    try:
        yield session
    finally:
        # Best-effort cleanup; ignore errors so failures don't cascade
        try:
            _purge_bench_tenant(session)
        except Exception:
            session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------


@pytest.mark.enterprise
@pytest.mark.performance
class TestEnterpriseRepositoryBenchmarks:
    """Median-latency benchmarks for all core enterprise repository operations.

    Each benchmark:
      1. Seeds required data via direct bulk INSERT (setup not timed).
      2. Runs the target operation _REPEATS times, recording wall-clock ns.
      3. Asserts median <= threshold.

    All tests skip automatically when PostgreSQL is not available via the
    ``bench_session`` fixture depending on ``pg_engine``.
    """

    # Accumulated results for the summary test — shared across instances
    _results: Dict[str, float] = {}

    def _median_seconds(self, fn, repeats: int = _REPEATS) -> float:
        """Return the median wall-clock time of *repeats* calls to *fn()* in seconds."""
        samples = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            fn()
            samples.append(time.perf_counter() - t0)
        return statistics.median(samples)

    # ------------------------------------------------------------------
    # bench_artifact_get — target: < 1 ms median
    # ------------------------------------------------------------------

    def test_bench_artifact_get(self, bench_session: Session) -> None:
        """Benchmark ``get()`` by primary key after seeding one known artifact."""
        # Seed one artifact to fetch
        ids = _bulk_insert_artifacts(bench_session, 1)
        target_id = ids[0]

        with tenant_scope(_BENCH_TENANT):
            repo = EnterpriseArtifactRepository(bench_session)

            def _op() -> None:
                # Expire the session cache each iteration so every call hits
                # the connection rather than the SQLAlchemy identity map.
                bench_session.expire_all()
                repo.get(target_id)

            median = self._median_seconds(_op)

        TestEnterpriseRepositoryBenchmarks._results["get"] = median

        assert median <= THRESHOLDS["get"], (
            f"bench_artifact_get median={median * 1000:.3f} ms "
            f"exceeds threshold {THRESHOLDS['get'] * 1000:.0f} ms"
        )

    # ------------------------------------------------------------------
    # bench_artifact_list_1000 — target: < 10 ms median
    # ------------------------------------------------------------------

    def test_bench_artifact_list_1000(self, bench_session: Session) -> None:
        """Benchmark ``list(limit=1000)`` against 1 000 pre-seeded rows."""
        _bulk_insert_artifacts(bench_session, 1000)

        with tenant_scope(_BENCH_TENANT):
            repo = EnterpriseArtifactRepository(bench_session)

            def _op() -> None:
                bench_session.expire_all()
                repo.list(limit=1000)

            median = self._median_seconds(_op)

        TestEnterpriseRepositoryBenchmarks._results["list_1000"] = median

        assert median <= THRESHOLDS["list_1000"], (
            f"bench_artifact_list_1000 median={median * 1000:.3f} ms "
            f"exceeds threshold {THRESHOLDS['list_1000'] * 1000:.0f} ms"
        )

    # ------------------------------------------------------------------
    # bench_artifact_list_paginated — target: < 50 ms for 10 pages × 100
    # ------------------------------------------------------------------

    def test_bench_artifact_list_paginated(self, bench_session: Session) -> None:
        """Benchmark fetching 10 pages of 100 rows each (1 000 rows total)."""
        _bulk_insert_artifacts(bench_session, 1000)

        with tenant_scope(_BENCH_TENANT):
            repo = EnterpriseArtifactRepository(bench_session)

            # Run the full 10-page sequence _REPEATS times and take the median
            def _op() -> None:
                bench_session.expire_all()
                for page in range(10):
                    repo.list(offset=page * 100, limit=100)

            median = self._median_seconds(_op)

        TestEnterpriseRepositoryBenchmarks._results["list_paginated"] = median

        # 50 ms total for 10 pages
        threshold = 0.050
        assert median <= threshold, (
            f"bench_artifact_list_paginated median={median * 1000:.3f} ms "
            f"exceeds threshold {threshold * 1000:.0f} ms"
        )

    # ------------------------------------------------------------------
    # bench_search_by_tags — target: < 5 ms median
    # ------------------------------------------------------------------

    def test_bench_search_by_tags(self, bench_session: Session) -> None:
        """Benchmark ``search_by_tags(['python'], match_all=True)`` over 200 tagged rows."""
        # Tag every artifact with "python" so there are guaranteed matches
        tags_cycle = [["python", f"extra-{i % 5}"] for i in range(10)]
        _bulk_insert_artifacts(bench_session, 200, tags_cycle=tags_cycle)

        with tenant_scope(_BENCH_TENANT):
            repo = EnterpriseArtifactRepository(bench_session)

            def _op() -> None:
                bench_session.expire_all()
                repo.search_by_tags(["python"], match_all=True)

            median = self._median_seconds(_op)

        TestEnterpriseRepositoryBenchmarks._results["search"] = median

        assert median <= THRESHOLDS["search"], (
            f"bench_search_by_tags median={median * 1000:.3f} ms "
            f"exceeds threshold {THRESHOLDS['search'] * 1000:.0f} ms"
        )

    # ------------------------------------------------------------------
    # bench_collection_list_artifacts — target: < 5 ms median
    # ------------------------------------------------------------------

    def test_bench_collection_list_artifacts(self, bench_session: Session) -> None:
        """Benchmark ``list_artifacts()`` for a collection with 100 members."""
        # Seed 100 artifacts and a collection via bulk insert
        artifact_ids = _bulk_insert_artifacts(bench_session, 100)

        import json

        # Create the collection directly
        col_id = uuid.uuid4()
        bench_session.execute(
            EnterpriseCollection.__table__.insert(),
            [
                {
                    "id": col_id,
                    "tenant_id": _BENCH_TENANT,
                    "name": f"bench-col-{col_id.hex[:6]}",
                    "description": None,
                }
            ],
        )

        # Create membership rows in bulk
        membership_rows = [
            {
                "collection_id": col_id,
                "artifact_id": art_id,
                "order_index": idx,
            }
            for idx, art_id in enumerate(artifact_ids)
        ]
        bench_session.execute(
            EnterpriseCollectionArtifact.__table__.insert(),
            membership_rows,
        )
        bench_session.commit()

        with tenant_scope(_BENCH_TENANT):
            col_repo = EnterpriseCollectionRepository(bench_session)

            def _op() -> None:
                bench_session.expire_all()
                col_repo.list_artifacts(col_id)

            median = self._median_seconds(_op)

        TestEnterpriseRepositoryBenchmarks._results["list_artifacts"] = median

        assert median <= THRESHOLDS["list_artifacts"], (
            f"bench_collection_list_artifacts median={median * 1000:.3f} ms "
            f"exceeds threshold {THRESHOLDS['list_artifacts'] * 1000:.0f} ms"
        )

    # ------------------------------------------------------------------
    # bench_create_artifact — target: < 5 ms median
    # ------------------------------------------------------------------

    def test_bench_create_artifact(self, bench_session: Session) -> None:
        """Benchmark ``create()`` including initial version content."""
        content = "# Benchmark Artifact\n\nContent for version 1.0.0."

        with tenant_scope(_BENCH_TENANT):
            repo = EnterpriseArtifactRepository(bench_session)

            def _op() -> None:
                repo.create(
                    name=_uname("create-bench"),
                    artifact_type="skill",
                    content=content,
                )

            median = self._median_seconds(_op, repeats=10)

        TestEnterpriseRepositoryBenchmarks._results["create"] = median

        assert median <= THRESHOLDS["create"], (
            f"bench_create_artifact median={median * 1000:.3f} ms "
            f"exceeds threshold {THRESHOLDS['create'] * 1000:.0f} ms"
        )


# ---------------------------------------------------------------------------
# Summary report — not a performance assertion; prints a formatted table
# ---------------------------------------------------------------------------


@pytest.mark.enterprise
@pytest.mark.performance
def test_print_benchmark_summary() -> None:
    """Print a human-readable table of all benchmark results for CI/CD visibility.

    This test always passes; its sole purpose is to emit a formatted summary
    so engineers can spot regressions in CI logs without parsing individual
    test output.

    NOTE: This test depends on TestEnterpriseRepositoryBenchmarks._results
    being populated by the benchmark tests above.  Run the full class first::

        pytest -m "enterprise and performance" tests/integration/test_enterprise_benchmarks.py -v
    """
    results = TestEnterpriseRepositoryBenchmarks._results

    if not results:
        print(
            "\n[benchmark summary] No results recorded — "
            "run the full TestEnterpriseRepositoryBenchmarks class first."
        )
        return

    threshold_map = {
        "get": THRESHOLDS["get"],
        "list_1000": THRESHOLDS["list_1000"],
        "list_paginated": 0.050,
        "search": THRESHOLDS["search"],
        "list_artifacts": THRESHOLDS["list_artifacts"],
        "create": THRESHOLDS["create"],
    }

    col_w = 22
    header = (
        f"\n{'Operation':<{col_w}} {'Median (ms)':>12} {'Target (ms)':>12} {'Status':>8}"
    )
    sep = "-" * (col_w + 36)
    rows = [header, sep]

    for key, median_s in sorted(results.items()):
        target_s = threshold_map.get(key, float("inf"))
        status = "PASS" if median_s <= target_s else "FAIL"
        rows.append(
            f"{key:<{col_w}} {median_s * 1000:>12.3f} {target_s * 1000:>12.1f} {status:>8}"
        )

    rows.append(sep)
    print("\n".join(rows))
