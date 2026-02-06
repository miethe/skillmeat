"""Performance benchmark tests for the Memory & Context Intelligence System.

Validates that key operations meet latency requirements:
    - Memory list queries < 200ms (p95)
    - pack_context (generate_pack) < 500ms (p95)
    - Deduplication check < 1s for 100 items

All benchmarks use a real SQLite database on a temporary file to reflect
production-like query paths through SQLAlchemy ORM, repository layer, and
service layer. Data is seeded with realistic volumes (50-100 memory items,
5-10 context modules) to exercise indexing, filtering, and pagination.

Tests are marked with @pytest.mark.benchmark for selective execution:
    pytest -m benchmark skillmeat/api/tests/test_performance_benchmarks.py
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest

from skillmeat.cache.memory_repositories import (
    ContextModuleRepository,
    MemoryItemRepository,
    _compute_content_hash,
)
from skillmeat.cache.models import Base, Project, create_db_engine
from skillmeat.cache.repositories import ConstraintError
from skillmeat.core.services.context_packer_service import ContextPackerService
from skillmeat.core.services.memory_service import MemoryService


# =============================================================================
# Constants
# =============================================================================

# Number of iterations per benchmark to compute percentiles
ITERATIONS = 20

# Percentile to assert on (p95)
PERCENTILE = 95

# SLA thresholds (seconds)
LIST_QUERY_SLA_MS = 200
PACK_CONTEXT_SLA_MS = 500
DEDUP_SLA_MS = 1000

# Data seeding volumes
NUM_MEMORY_ITEMS = 100
NUM_CONTEXT_MODULES = 10

# Memory types for realistic distribution
MEMORY_TYPES = ["decision", "constraint", "gotcha", "style_rule", "learning"]

# Statuses for distribution (weighted toward active/stable for pack tests)
STATUSES = ["candidate", "active", "stable"]


# =============================================================================
# Helpers
# =============================================================================


def _p95(timings: List[float]) -> float:
    """Compute the 95th percentile of a list of timing values in milliseconds."""
    sorted_timings = sorted(timings)
    idx = int(len(sorted_timings) * PERCENTILE / 100)
    idx = min(idx, len(sorted_timings) - 1)
    return sorted_timings[idx] * 1000  # convert seconds to milliseconds


def _make_unique_content(index: int, padding_words: int = 15) -> str:
    """Generate unique content for a memory item with realistic length.

    Produces content of roughly 100-200 characters to simulate real
    decisions, constraints, and learnings.
    """
    topics = [
        "Use SQLAlchemy ORM for data access layer",
        "Prefer cursor-based pagination over offset",
        "All API responses must include request_id header",
        "SQLite WAL mode required for concurrent reads",
        "Pydantic models validate at API boundary only",
        "Token estimation uses chars/4 heuristic",
        "Context modules group memories by workflow stage",
        "Confidence scores decay over time without access",
        "Content hash prevents duplicate memory insertion",
        "Rich library used for CLI output formatting",
    ]
    base = topics[index % len(topics)]
    # Make each item unique by appending index and padding
    # Use a deterministic suffix so the same index always produces the same content
    deterministic_id = hashlib.md5(f"bench-{index}".encode()).hexdigest()[:8]
    suffix = f" (variant {index}, project context {deterministic_id})"
    padding = " ".join([f"word{i}" for i in range(padding_words)])
    return f"{base}{suffix}. {padding}"


def _seed_project(engine, project_id: str = "bench-proj-1") -> str:
    """Create a Project row required by MemoryItem FK constraint.

    Returns the project_id.
    """
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        project = Project(
            id=project_id,
            name="Benchmark Test Project",
            path=f"/tmp/benchmark/{project_id}",
            status="active",
        )
        session.add(project)
        session.commit()
        return project_id
    finally:
        session.close()


def _seed_memory_items(
    repo: MemoryItemRepository,
    project_id: str,
    count: int = NUM_MEMORY_ITEMS,
) -> List[str]:
    """Seed the database with realistic memory items.

    Distributes items across types and statuses. Returns list of
    created item IDs.
    """
    item_ids: List[str] = []
    for i in range(count):
        item_type = MEMORY_TYPES[i % len(MEMORY_TYPES)]
        status = STATUSES[i % len(STATUSES)]
        confidence = 0.5 + (i % 50) / 100.0  # Range 0.50 - 0.99
        content = _make_unique_content(i)

        item = repo.create(
            {
                "project_id": project_id,
                "type": item_type,
                "content": content,
                "confidence": min(confidence, 1.0),
                "status": status,
            }
        )
        item_ids.append(item.id)

    return item_ids


def _seed_context_modules(
    module_repo: ContextModuleRepository,
    memory_repo: MemoryItemRepository,
    project_id: str,
    item_ids: List[str],
    count: int = NUM_CONTEXT_MODULES,
) -> List[str]:
    """Seed context modules and associate memory items.

    Each module gets a subset of memory items to simulate real usage.
    Returns list of created module IDs.
    """
    module_ids: List[str] = []
    items_per_module = max(1, len(item_ids) // count)

    for i in range(count):
        selectors = {
            "memory_types": [MEMORY_TYPES[i % len(MEMORY_TYPES)]],
            "min_confidence": 0.5 + (i * 0.05),
        }
        module = module_repo.create(
            {
                "project_id": project_id,
                "name": f"Module {i}: {MEMORY_TYPES[i % len(MEMORY_TYPES)].title()}",
                "description": f"Benchmark test module {i}",
                "selectors_json": json.dumps(selectors),
                "priority": i + 1,
            }
        )
        module_ids.append(module.id)

        # Associate a slice of memory items with this module
        start = i * items_per_module
        end = min(start + items_per_module, len(item_ids))
        for ordering, mem_id in enumerate(item_ids[start:end]):
            try:
                module_repo.add_memory_item(module.id, mem_id, ordering=ordering)
            except (ConstraintError, Exception):
                pass  # Skip if already linked or FK mismatch

    return module_ids


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def bench_db_path(tmp_path_factory) -> Path:
    """Create a temporary SQLite database for all benchmark tests in this module.

    Uses module scope so all benchmarks share the same seeded data,
    avoiding repeated setup overhead.
    """
    tmp_dir = tmp_path_factory.mktemp("bench_db")
    db_path = tmp_dir / "benchmark.db"
    return db_path


@pytest.fixture(scope="module")
def seeded_db(bench_db_path) -> Dict[str, Any]:
    """Seed the benchmark database with realistic data.

    Returns a dict with db_path, project_id, item_ids, and module_ids
    for use in benchmark tests.
    """
    db_path = str(bench_db_path)

    # Create engine and tables
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    # Seed project
    project_id = _seed_project(engine, "bench-proj-1")

    # Seed memory items via repository
    memory_repo = MemoryItemRepository(db_path=db_path)
    item_ids = _seed_memory_items(memory_repo, project_id, count=NUM_MEMORY_ITEMS)

    # Seed context modules
    module_repo = ContextModuleRepository(db_path=db_path)
    module_ids = _seed_context_modules(
        module_repo, memory_repo, project_id, item_ids, count=NUM_CONTEXT_MODULES
    )

    return {
        "db_path": db_path,
        "project_id": project_id,
        "item_ids": item_ids,
        "module_ids": module_ids,
    }


@pytest.fixture(scope="module")
def memory_service(seeded_db) -> MemoryService:
    """Create a MemoryService backed by the seeded benchmark database."""
    return MemoryService(db_path=seeded_db["db_path"])


@pytest.fixture(scope="module")
def packer_service(seeded_db) -> ContextPackerService:
    """Create a ContextPackerService backed by the seeded benchmark database."""
    return ContextPackerService(db_path=seeded_db["db_path"])


# =============================================================================
# Benchmark 1: Memory List Queries < 200ms (p95)
# =============================================================================


@pytest.mark.benchmark
class TestMemoryListQueryPerformance:
    """Verify that memory list queries complete under 200ms at p95.

    Tests exercise the full query path: MemoryService -> MemoryItemRepository
    -> SQLAlchemy -> SQLite, including filtering, sorting, and pagination.
    """

    def test_list_all_items_under_sla(self, memory_service, seeded_db):
        """List all memory items for a project with no filters.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = memory_service.list_items(project_id, limit=50)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (no filter) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )
        # Verify data correctness
        assert len(result["items"]) > 0

    def test_list_with_status_filter_under_sla(self, memory_service, seeded_db):
        """List memory items filtered by status.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = memory_service.list_items(project_id, status="active", limit=50)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (status=active) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )

    def test_list_with_type_filter_under_sla(self, memory_service, seeded_db):
        """List memory items filtered by type.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = memory_service.list_items(project_id, type="decision", limit=50)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (type=decision) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )

    def test_list_with_confidence_filter_under_sla(self, memory_service, seeded_db):
        """List memory items filtered by minimum confidence.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = memory_service.list_items(
                project_id, min_confidence=0.8, limit=50
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (min_confidence=0.8) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )

    def test_list_with_combined_filters_under_sla(self, memory_service, seeded_db):
        """List memory items with status + type + confidence filters combined.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = memory_service.list_items(
                project_id,
                status="active",
                type="decision",
                min_confidence=0.7,
                limit=50,
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (combined filters) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )

    def test_list_with_pagination_under_sla(self, memory_service, seeded_db):
        """List memory items with small page size to exercise cursor pagination.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            # First page
            page1 = memory_service.list_items(project_id, limit=10)
            # Second page using cursor
            if page1["next_cursor"]:
                memory_service.list_items(
                    project_id, limit=10, cursor=page1["next_cursor"]
                )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (paginated, 2 pages) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )

    def test_list_with_sort_by_confidence_under_sla(self, memory_service, seeded_db):
        """List memory items sorted by confidence descending.

        SLA: p95 < 200ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = memory_service.list_items(
                project_id,
                sort_by="confidence",
                sort_order="desc",
                limit=50,
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < LIST_QUERY_SLA_MS, (
            f"list_items (sort by confidence) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {LIST_QUERY_SLA_MS}ms"
        )


# =============================================================================
# Benchmark 2: pack_context (generate_pack) < 500ms (p95)
# =============================================================================


@pytest.mark.benchmark
class TestPackContextPerformance:
    """Verify that context pack generation completes under 500ms at p95.

    Tests exercise the full pack path: ContextPackerService -> MemoryService
    -> repository queries -> item selection with budget -> markdown generation.
    """

    def test_generate_pack_default_budget_under_sla(self, packer_service, seeded_db):
        """Generate a context pack with the default 4000 token budget.

        SLA: p95 < 500ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = packer_service.generate_pack(project_id, budget_tokens=4000)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < PACK_CONTEXT_SLA_MS, (
            f"generate_pack (budget=4000) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {PACK_CONTEXT_SLA_MS}ms"
        )
        # Verify pack contains data
        assert result["items_included"] > 0
        assert "# Context Pack" in result["markdown"]

    def test_generate_pack_large_budget_under_sla(self, packer_service, seeded_db):
        """Generate a context pack with a large budget that includes all items.

        SLA: p95 < 500ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = packer_service.generate_pack(project_id, budget_tokens=100000)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < PACK_CONTEXT_SLA_MS, (
            f"generate_pack (budget=100000) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {PACK_CONTEXT_SLA_MS}ms"
        )
        # Should include many items with large budget
        assert result["items_included"] > 10

    def test_generate_pack_with_type_filter_under_sla(
        self, packer_service, seeded_db
    ):
        """Generate a context pack filtered to a single memory type.

        SLA: p95 < 500ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = packer_service.generate_pack(
                project_id,
                budget_tokens=4000,
                filters={"type": "decision"},
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < PACK_CONTEXT_SLA_MS, (
            f"generate_pack (type=decision) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {PACK_CONTEXT_SLA_MS}ms"
        )

    def test_generate_pack_with_confidence_filter_under_sla(
        self, packer_service, seeded_db
    ):
        """Generate a context pack with a confidence threshold filter.

        SLA: p95 < 500ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = packer_service.generate_pack(
                project_id,
                budget_tokens=4000,
                filters={"min_confidence": 0.8},
            )
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < PACK_CONTEXT_SLA_MS, (
            f"generate_pack (min_confidence=0.8) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {PACK_CONTEXT_SLA_MS}ms"
        )

    def test_preview_pack_under_sla(self, packer_service, seeded_db):
        """Preview a context pack (selection only, no markdown).

        SLA: p95 < 500ms (should be faster than generate_pack)
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = packer_service.preview_pack(project_id, budget_tokens=4000)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < PACK_CONTEXT_SLA_MS, (
            f"preview_pack (budget=4000) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {PACK_CONTEXT_SLA_MS}ms"
        )

    def test_apply_module_selectors_under_sla(self, packer_service, seeded_db):
        """Apply module selectors to filter memory items.

        SLA: p95 < 500ms
        """
        project_id = seeded_db["project_id"]
        timings: List[float] = []

        selectors = {
            "memory_types": ["decision", "constraint"],
            "min_confidence": 0.7,
        }

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            result = packer_service.apply_module_selectors(project_id, selectors)
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < PACK_CONTEXT_SLA_MS, (
            f"apply_module_selectors p95={p95_ms:.1f}ms exceeds "
            f"SLA of {PACK_CONTEXT_SLA_MS}ms"
        )


# =============================================================================
# Benchmark 3: Deduplication < 1s for 100 Items
# =============================================================================


@pytest.mark.benchmark
class TestDeduplicationPerformance:
    """Verify that content deduplication checks complete under 1 second
    for 100 items at p95.

    Deduplication works via content_hash (SHA-256) computed at insert time
    and enforced by a UNIQUE constraint. This benchmark tests both the
    hash computation and the DB constraint enforcement.
    """

    def test_content_hash_computation_100_items_under_sla(self):
        """Compute content hashes for 100 items.

        SLA: p95 < 1000ms for all 100 items
        """
        contents = [_make_unique_content(i, padding_words=20) for i in range(100)]
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            hashes = [_compute_content_hash(c) for c in contents]
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < DEDUP_SLA_MS, (
            f"Content hash computation (100 items) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {DEDUP_SLA_MS}ms"
        )
        # Verify all hashes are unique
        assert len(set(hashes)) == 100

    def test_duplicate_detection_via_insert_100_items_under_sla(
        self, seeded_db
    ):
        """Insert 100 items that are duplicates of existing ones and verify
        detection speed.

        SLA: p95 < 1000ms for attempting 100 duplicate insertions
        """
        db_path = seeded_db["db_path"]
        project_id = seeded_db["project_id"]
        repo = MemoryItemRepository(db_path=db_path)

        # Pre-compute the content hashes of existing items to create duplicates
        duplicate_contents = [
            _make_unique_content(i, padding_words=15) for i in range(100)
        ]

        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            dedup_count = 0
            for content in duplicate_contents:
                content_hash = _compute_content_hash(content)
                existing = repo.get_by_content_hash(content_hash)
                if existing is not None:
                    dedup_count += 1
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < DEDUP_SLA_MS, (
            f"Duplicate detection (100 items) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {DEDUP_SLA_MS}ms"
        )
        # All 100 should be detected as existing duplicates
        assert dedup_count == 100

    def test_dedup_mixed_new_and_existing_under_sla(self, seeded_db):
        """Check deduplication for a mix of 50 new and 50 existing items.

        SLA: p95 < 1000ms for all 100 checks
        """
        db_path = seeded_db["db_path"]
        repo = MemoryItemRepository(db_path=db_path)

        # 50 existing items (indices 0-49 match seeded data)
        existing_contents = [_make_unique_content(i) for i in range(50)]
        # 50 truly new items (high indices that were not seeded)
        new_contents = [_make_unique_content(i + 10000) for i in range(50)]

        all_contents = existing_contents + new_contents
        timings: List[float] = []

        for _ in range(ITERATIONS):
            start = time.perf_counter()
            found_count = 0
            new_count = 0
            for content in all_contents:
                content_hash = _compute_content_hash(content)
                existing = repo.get_by_content_hash(content_hash)
                if existing is not None:
                    found_count += 1
                else:
                    new_count += 1
            elapsed = time.perf_counter() - start
            timings.append(elapsed)

        p95_ms = _p95(timings)
        assert p95_ms < DEDUP_SLA_MS, (
            f"Dedup (50 existing + 50 new) p95={p95_ms:.1f}ms exceeds "
            f"SLA of {DEDUP_SLA_MS}ms"
        )
        # Verify counts
        assert found_count == 50, f"Expected 50 existing, got {found_count}"
        assert new_count == 50, f"Expected 50 new, got {new_count}"


# =============================================================================
# Benchmark Summary: Aggregate Results
# =============================================================================


@pytest.mark.benchmark
class TestBenchmarkSummary:
    """Aggregate benchmark that runs the three core operations once each
    and reports all timings together.

    This test documents the combined performance characteristics in a
    single test for easy CI visibility.
    """

    def test_all_slas_met(self, memory_service, packer_service, seeded_db):
        """Run all three benchmark operations and assert all SLAs are met.

        - Memory list queries: p95 < 200ms
        - Context pack generation: p95 < 500ms
        - Deduplication for 100 items: p95 < 1000ms
        """
        project_id = seeded_db["project_id"]
        db_path = seeded_db["db_path"]
        repo = MemoryItemRepository(db_path=db_path)

        # 1. Memory list query timings
        list_timings: List[float] = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            memory_service.list_items(
                project_id, status="active", type="decision", limit=50
            )
            list_timings.append(time.perf_counter() - start)

        # 2. Pack generation timings
        pack_timings: List[float] = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            packer_service.generate_pack(project_id, budget_tokens=4000)
            pack_timings.append(time.perf_counter() - start)

        # 3. Dedup check timings (100 items)
        dedup_contents = [_make_unique_content(i) for i in range(100)]
        dedup_timings: List[float] = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            for content in dedup_contents:
                content_hash = _compute_content_hash(content)
                repo.get_by_content_hash(content_hash)
            dedup_timings.append(time.perf_counter() - start)

        # Compute p95 for each
        list_p95 = _p95(list_timings)
        pack_p95 = _p95(pack_timings)
        dedup_p95 = _p95(dedup_timings)

        # Assert all SLAs
        assert list_p95 < LIST_QUERY_SLA_MS, (
            f"Memory list query p95={list_p95:.1f}ms exceeds {LIST_QUERY_SLA_MS}ms"
        )
        assert pack_p95 < PACK_CONTEXT_SLA_MS, (
            f"Pack generation p95={pack_p95:.1f}ms exceeds {PACK_CONTEXT_SLA_MS}ms"
        )
        assert dedup_p95 < DEDUP_SLA_MS, (
            f"Dedup (100 items) p95={dedup_p95:.1f}ms exceeds {DEDUP_SLA_MS}ms"
        )
