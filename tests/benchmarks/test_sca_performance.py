"""Performance benchmarks for Skill-Contained Artifacts (SCA Phase 8).

Targets:
- Import skill with 10 embedded artifacts: <5 seconds
- GET /associations P95 for skill with 20 members: <200ms

The tests use an in-memory SQLite database (temp-file pattern) consistent with
existing benchmark and integration tests.  ``pytest-benchmark`` is used when
available; a ``time.perf_counter`` fallback is provided otherwise.
"""

from __future__ import annotations

import statistics
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Generator, List
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.composite_repository import CompositeMembershipRepository
from skillmeat.cache.models import (
    Artifact,
    Base,
    Collection,
    CompositeArtifact,
    CompositeMembership,
    Project,
    create_db_engine,
)
from skillmeat.core.services.composite_service import CompositeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ARTIFACT_TYPES = ["command", "agent", "hook", "mcp", "command", "agent", "hook",
                   "command", "agent", "hook"]


def _make_uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_embedded_artifact(index: int) -> SimpleNamespace:
    """Build a DetectedArtifact-like stub for one embedded child.

    The composite_service reads ``artifact_type``, ``name``, ``upstream_url``,
    and optionally ``content_hash`` via ``getattr``, so a ``SimpleNamespace``
    is sufficient.
    """
    artifact_type = _ARTIFACT_TYPES[index % len(_ARTIFACT_TYPES)]
    return SimpleNamespace(
        artifact_type=artifact_type,
        name=f"child-{index:03d}-{artifact_type}",
        upstream_url=f"https://github.com/example/repo/path/{artifact_type}-{index}",
        content_hash=None,  # no dedup; forces a new Artifact row per child
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database file (deleted after each test)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
        db_path = fh.name
    yield db_path
    try:
        Path(db_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture()
def db_engine(temp_db: str):
    """Engine with all ORM tables created (bypasses Alembic)."""
    engine = create_db_engine(temp_db)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_session(db_engine) -> Generator[Session, None, None]:
    """Live SQLAlchemy session bound to the temp database."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    sess = SessionLocal()
    yield sess
    sess.close()


@pytest.fixture()
def composite_service(temp_db: str) -> CompositeService:
    """CompositeService wired to the temp database (migrations no-op'ed)."""
    with patch("skillmeat.cache.migrations.run_migrations"):
        svc = CompositeService(db_path=temp_db)
    return svc


@pytest.fixture()
def seeded_skill_artifact(db_session: Session) -> Artifact:
    """Insert the minimal Project + Collection + Skill Artifact rows.

    Returns the Artifact instance for the parent skill so that
    ``create_skill_composite`` can derive the composite id and uuid.
    """
    proj = Project(
        id="bench-proj-001",
        name="Bench Project",
        path="/tmp/bench-proj-001",
        status="active",
    )
    col = Collection(id="bench-col-001", name="default")
    skill = Artifact(
        id="skill:bench-skill",
        uuid=_make_uuid(),
        name="bench-skill",
        type="skill",
        project_id="bench-proj-001",
    )
    db_session.add_all([proj, col, skill])
    db_session.commit()
    db_session.refresh(skill)
    return skill


# ---------------------------------------------------------------------------
# Benchmark 1 — Import skill with 10 embedded artifacts
# ---------------------------------------------------------------------------


class TestImportPerformance:
    """Benchmark the create_skill_composite() path for 10 embedded children.

    Target: entire DB-write operation completes in <5 seconds.
    """

    def test_import_10_embedded_artifacts_within_5s(
        self,
        composite_service: CompositeService,
        db_session: Session,
        seeded_skill_artifact: Artifact,
    ) -> None:
        """Time the import flow and assert it finishes within 5 seconds.

        The test exercises the full code path through
        ``CompositeService.create_skill_composite()``:

        1. Creates one ``CompositeArtifact`` row.
        2. Creates 10 ``Artifact`` child rows (no dedup — unique names).
        3. Creates 10 ``CompositeMembership`` edge rows.

        A conservative 5-second budget covers I/O-bound SQLite on slow CI
        runners while still catching catastrophic regressions.
        """
        embedded = [_make_embedded_artifact(i) for i in range(10)]

        start = time.perf_counter()
        record = composite_service.create_skill_composite(
            skill_artifact=seeded_skill_artifact,
            embedded_list=embedded,
            collection_id="bench-col-001",
            display_name="Bench Skill Composite",
        )
        elapsed = time.perf_counter() - start

        # Correctness assertions
        assert record is not None, "create_skill_composite returned None"
        assert record["composite_type"] == "skill"
        membership_count = len(record.get("memberships", []))
        assert membership_count == 10, (
            f"Expected 10 memberships, got {membership_count}"
        )

        # Performance assertion
        assert elapsed < 5.0, (
            f"Import of 10 embedded artifacts took {elapsed:.3f}s, "
            f"target is <5s"
        )

        print(f"\n[SCA-BENCH] import 10 embedded: {elapsed * 1000:.1f}ms")

    def test_import_10_embedded_artifacts_benchmark(
        self,
        composite_service: CompositeService,
        db_session: Session,
        seeded_skill_artifact: Artifact,
        benchmark,
    ) -> None:
        """pytest-benchmark version of the import test (skipped without plugin).

        When pytest-benchmark is installed, this test reports granular timing
        statistics (min/max/mean/stddev/rounds).
        """
        pytest.importorskip("pytest_benchmark")
        embedded = [_make_embedded_artifact(i) for i in range(10)]

        def run() -> None:
            composite_service.create_skill_composite(
                skill_artifact=seeded_skill_artifact,
                embedded_list=embedded,
                collection_id="bench-col-001",
                display_name="Bench Skill Composite",
            )

        # benchmark.pedantic gives a single well-timed round; we run once
        # because create_skill_composite is not idempotent across rounds
        # (duplicate composite_id would raise ConstraintError).
        result = benchmark.pedantic(run, rounds=1, warmup_rounds=0)
        assert benchmark.stats["mean"] < 5.0, (
            f"Mean import time {benchmark.stats['mean']:.3f}s exceeds 5s target"
        )


# ---------------------------------------------------------------------------
# Benchmark 2 — GET /associations P95 for skill with 20 members
# ---------------------------------------------------------------------------


class TestAssociationsQueryPerformance:
    """Benchmark the get_associations() code path for a skill with 20 members.

    Target: P95 latency across 100 iterations must be <200ms.

    The test seeds the DB once, then calls
    ``CompositeMembershipRepository.get_associations()`` 100 times and
    computes the 95th-percentile of those timings.
    """

    @pytest.fixture()
    def seeded_composite_with_20_members(
        self,
        db_session: Session,
        temp_db: str,
    ) -> dict:
        """Seed DB with a composite skill that has 20 CompositeMembership rows.

        Returns a dict with keys ``composite_id``, ``collection_id``, and
        ``temp_db`` so the benchmark can instantiate a repository.
        """
        col_id = "bench-assoc-col"
        proj_id = "bench-assoc-proj"
        composite_id = "composite:assoc-bench-skill"

        db_session.add(Project(
            id=proj_id,
            name="Assoc Bench Project",
            path="/tmp/assoc-bench",
            status="active",
        ))
        db_session.add(Collection(id=col_id, name="default"))
        db_session.flush()

        # Composite artifact row
        db_session.add(CompositeArtifact(
            id=composite_id,
            collection_id=col_id,
            composite_type="skill",
            display_name="Assoc Bench Skill",
            metadata_json='{"artifact_uuid": "' + _make_uuid() + '"}',
        ))
        db_session.flush()

        # 20 child artifacts + 20 membership rows
        for i in range(20):
            art_type = _ARTIFACT_TYPES[i % len(_ARTIFACT_TYPES)]
            child_uuid = _make_uuid()
            db_session.add(Artifact(
                id=f"{art_type}:assoc-child-{i:03d}",
                uuid=child_uuid,
                name=f"assoc-child-{i:03d}",
                type=art_type,
                project_id=proj_id,
            ))
            db_session.flush()
            db_session.add(CompositeMembership(
                collection_id=col_id,
                composite_id=composite_id,
                child_artifact_uuid=child_uuid,
                relationship_type="contains",
                created_at=_utcnow(),
            ))

        db_session.commit()
        return {
            "composite_id": composite_id,
            "collection_id": col_id,
            "temp_db": temp_db,
        }

    def test_associations_p95_under_200ms(
        self,
        seeded_composite_with_20_members: dict,
    ) -> None:
        """Assert P95 of 100 get_associations() calls is under 200ms.

        A new ``CompositeMembershipRepository`` is instantiated pointing at the
        pre-seeded temp database.  100 sequential calls to
        ``get_associations(composite_id, collection_id)`` are timed, and the
        95th percentile must be below 200ms.

        Rationale: the 200ms target allows ~5x headroom over expected SQLite
        in-process latency (~5-30ms) while catching query-plan regressions.
        """
        ctx = seeded_composite_with_20_members
        composite_id = ctx["composite_id"]
        collection_id = ctx["collection_id"]
        temp_db = ctx["temp_db"]

        with patch("skillmeat.cache.migrations.run_migrations"):
            repo = CompositeMembershipRepository(db_path=temp_db)

        iterations = 100
        timings: List[float] = []

        for _ in range(iterations):
            t0 = time.perf_counter()
            result = repo.get_associations(composite_id, collection_id)
            timings.append(time.perf_counter() - t0)

        # Correctness: children list should have all 20 members
        assert len(result["children"]) == 20, (
            f"Expected 20 children, got {len(result['children'])}"
        )

        # P95 calculation
        sorted_timings = sorted(timings)
        p95_index = int(0.95 * iterations) - 1
        p95_ms = sorted_timings[p95_index] * 1000
        mean_ms = statistics.mean(timings) * 1000
        max_ms = max(timings) * 1000

        print(
            f"\n[SCA-BENCH] associations 20 members | "
            f"mean={mean_ms:.1f}ms  P95={p95_ms:.1f}ms  max={max_ms:.1f}ms  "
            f"(n={iterations})"
        )

        assert p95_ms < 200.0, (
            f"P95 associations latency {p95_ms:.1f}ms exceeds 200ms target "
            f"(mean={mean_ms:.1f}ms, max={max_ms:.1f}ms)"
        )

    def test_associations_p95_benchmark(
        self,
        seeded_composite_with_20_members: dict,
        benchmark,
    ) -> None:
        """pytest-benchmark version of the associations P95 test.

        When pytest-benchmark is installed, this provides richer reporting.
        Skipped automatically when the plugin is not present.
        """
        pytest.importorskip("pytest_benchmark")
        ctx = seeded_composite_with_20_members
        composite_id = ctx["composite_id"]
        collection_id = ctx["collection_id"]
        temp_db = ctx["temp_db"]

        with patch("skillmeat.cache.migrations.run_migrations"):
            repo = CompositeMembershipRepository(db_path=temp_db)

        def run():
            return repo.get_associations(composite_id, collection_id)

        benchmark(run)
        assert benchmark.stats["mean"] < 0.2, (
            f"Mean associations latency {benchmark.stats['mean'] * 1000:.1f}ms "
            f"exceeds 200ms target"
        )


# ---------------------------------------------------------------------------
# Index check (informational, not a performance assertion)
# ---------------------------------------------------------------------------


class TestIndexPresence:
    """Verify the expected indexes are present on composite_artifacts.

    The associations query filters on ``composite_id`` (PK) and
    ``collection_id`` — both already indexed.  ``metadata_json`` is not in
    any query filter so no JSON index is needed.  This test documents what
    indexes exist so future regressions are visible.
    """

    def test_composite_artifacts_has_collection_id_index(
        self, db_engine
    ) -> None:
        """Confirm idx_composite_artifacts_collection_id exists."""
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db_engine)
        indexes = {
            idx["name"]
            for idx in inspector.get_indexes("composite_artifacts")
        }
        assert "idx_composite_artifacts_collection_id" in indexes, (
            f"Expected idx_composite_artifacts_collection_id in {indexes}"
        )

    def test_composite_artifacts_has_composite_type_index(
        self, db_engine
    ) -> None:
        """Confirm idx_composite_artifacts_composite_type exists."""
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db_engine)
        indexes = {
            idx["name"]
            for idx in inspector.get_indexes("composite_artifacts")
        }
        assert "idx_composite_artifacts_composite_type" in indexes, (
            f"Expected idx_composite_artifacts_composite_type in {indexes}"
        )

    def test_metadata_json_not_indexed(self, db_engine) -> None:
        """Confirm no idx_composite_artifacts_metadata_json index exists.

        The associations query does not filter on metadata_json, so adding
        a full-text or hash index on a JSON Text column would be dead weight.
        This test codifies the intentional absence of such an index.  If a
        future query requires JSON lookups, an index can be added along with
        an updated assertion here.
        """
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db_engine)
        index_names = {
            idx["name"]
            for idx in inspector.get_indexes("composite_artifacts")
        }
        assert "idx_composite_artifacts_metadata_json" not in index_names, (
            "Unexpected metadata_json index found — update this test if "
            "the index was intentionally added"
        )
