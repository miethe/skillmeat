"""Performance benchmarks for the memory extraction pipeline.

Tests the extraction service across different session sizes to validate
performance characteristics and ensure acceptable processing times.
"""

from __future__ import annotations

import json
import time
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Base, Project, create_db_engine
from skillmeat.core.services.memory_extractor_service import MemoryExtractorService


# ============================================================================
# Constants
# ============================================================================

PROJECT_ID = "proj-perf-benchmark"

# Heuristic mode target: < 5 seconds
HEURISTIC_TIME_LIMIT = 5.0

# LLM mode (mocked) target: < 15 seconds
LLM_TIME_LIMIT = 15.0


# ============================================================================
# Database fixture (reusable seeded DB with a project row)
# ============================================================================


@pytest.fixture
def seeded_db_path(tmp_path):
    """Create a temporary database seeded with a test project."""
    db_path = tmp_path / "perf_benchmark.db"
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.add(
        Project(
            id=PROJECT_ID,
            name="Performance Benchmark Project",
            path="/tmp/perf-benchmark",
            status="active",
        )
    )
    session.commit()
    session.close()
    engine.dispose()

    return str(db_path)


# ============================================================================
# Session Generator
# ============================================================================


def _generate_session_jsonl(target_size_kb: int) -> str:
    """Generate realistic JSONL session data of approximately target_size_kb.

    Creates a mix of:
    - User questions (human messages)
    - Assistant text responses
    - Assistant tool_use blocks
    - Progress/system messages (noise)

    The generator alternates between message types to create realistic
    session structure.
    """
    lines: List[str] = []
    session_id = f"perf-test-{target_size_kb}kb"
    target_bytes = target_size_kb * 1024
    current_size = 0
    msg_idx = 0

    # Message templates for variety
    user_questions = [
        "How do I implement a rate limiter for the API endpoints?",
        "Fix the bug where the database connection pool gets exhausted.",
        "Refactor the user service to separate read and write operations.",
        "Add integration tests for the deployment pipeline.",
        "Explain how SQLAlchemy connection pooling works internally.",
        "Review the cache invalidation logic for potential race conditions.",
        "Write documentation for the memory extraction API.",
        "Set up the development environment with all dependencies.",
        "Design an architecture for a plugin system with hot-reloading.",
        "Optimize the query performance for the artifact listing endpoint.",
    ]

    decision_templates = [
        "Decision: Use Redis for distributed caching across services. This provides "
        "atomic operations and built-in TTL support which is critical for our session "
        "management requirements.",
        "Decision: Adopt an event-driven architecture using message queues. This allows "
        "microservices to communicate asynchronously and improves system resilience.",
        "Decision: Use SQLAlchemy ORM for all database operations. The type safety and "
        "migration support justify the performance overhead for our use case.",
        "Decision: Implement the Saga pattern for multi-step transactions. This provides "
        "rollback capabilities without requiring distributed transaction coordinators.",
        "Decision: Use uv for dependency management instead of pip. The 10-100x faster "
        "resolution speed significantly improves developer productivity.",
    ]

    constraint_templates = [
        "Constraint: All API endpoints must include rate limiting headers. The standard "
        "is X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset per RFC 6585.",
        "Constraint: Database migrations must be reversible. Every migration needs both "
        "upgrade() and downgrade() operations tested in the development environment.",
        "Constraint: Cache keys must include a version prefix to support zero-downtime "
        "deployments. Format: v{SCHEMA_VERSION}:{entity}:{id}",
        "Constraint: All background tasks must be idempotent. The task queue may deliver "
        "messages multiple times during network failures or worker restarts.",
        "Constraint: API responses must never include internal error details in production. "
        "Use error codes that map to documentation rather than exposing stack traces.",
    ]

    gotcha_templates = [
        "Gotcha: Beware of N+1 query problems when using ORM lazy loading. Always use "
        "selectinload() or joinedload() for relationships accessed in list views.",
        "Gotcha: SQLAlchemy session objects are not thread-safe. Each request must get its "
        "own session from the scoped_session registry to avoid race conditions.",
        "Gotcha: Redis SETEX is not atomic with GET operations. Use Lua scripts or the "
        "SET command with EX and NX options for atomic test-and-set behavior.",
        "Gotcha: FastAPI dependency injection creates new instances per request by default. "
        "Use lru_cache on the dependency function for singleton behavior.",
        "Gotcha: PostgreSQL JSONB index updates are not atomic. Concurrent updates to the "
        "same JSONB column can cause lost writes without MVCC conflict detection.",
    ]

    learning_templates = [
        "I learned that connection pool size should match the number of worker threads. "
        "Oversizing wastes resources while undersizing causes connection timeout errors.",
        "I discovered that FastAPI's BackgroundTasks run after the response is sent. This "
        "is perfect for fire-and-forget operations like logging and analytics.",
        "I realized that Redis pipelining reduces network round-trips by 10x for batch "
        "operations. Group related commands into a single pipeline for optimal performance.",
        "I found that SQLAlchemy's bulk_insert_mappings is 50x faster than individual "
        "session.add() calls for batch inserts exceeding 100 rows.",
        "I learned that pytest fixtures with session scope can leak test data. Use function "
        "scope for database fixtures to ensure proper isolation between tests.",
    ]

    def _ts(minute: int) -> str:
        """Return a deterministic ISO timestamp."""
        return f"2025-06-15T10:{minute % 60:02d}:{(minute // 60) % 60:02d}Z"

    def _human(content: str, minute: int) -> dict:
        """Build a human/user message dict."""
        return {
            "type": "human",
            "content": content,
            "uuid": f"msg-human-{msg_idx}",
            "timestamp": _ts(minute),
            "sessionId": session_id,
            "gitBranch": "feat/perf-benchmark",
        }

    def _assistant_text(text: str, minute: int) -> dict:
        """Build an assistant message with plain text content."""
        return {
            "type": "assistant",
            "content": text,
            "uuid": f"msg-asst-{msg_idx}",
            "timestamp": _ts(minute),
            "sessionId": session_id,
        }

    def _assistant_blocks(blocks: List[dict], minute: int) -> dict:
        """Build an assistant message with content blocks."""
        return {
            "type": "assistant",
            "content": blocks,
            "uuid": f"msg-asst-blocks-{msg_idx}",
            "timestamp": _ts(minute),
            "sessionId": session_id,
        }

    def _noise_progress(minute: int) -> dict:
        return {
            "type": "progress",
            "content": f"Processing step {msg_idx}...",
            "timestamp": _ts(minute),
        }

    def _noise_system(minute: int) -> dict:
        return {
            "type": "system",
            "content": f"System checkpoint {msg_idx}",
            "timestamp": _ts(minute),
        }

    # Generate messages until we hit target size
    while current_size < target_bytes:
        msg_idx += 1
        minute = msg_idx

        # Cycle through message types for variety
        msg_type = msg_idx % 8

        if msg_type == 0:
            # User question
            question = user_questions[msg_idx % len(user_questions)]
            msg = _human(question, minute)
        elif msg_type == 1:
            # Decision in assistant text
            decision = decision_templates[msg_idx % len(decision_templates)]
            msg = _assistant_text(decision, minute)
        elif msg_type == 2:
            # Constraint in assistant text
            constraint = constraint_templates[msg_idx % len(constraint_templates)]
            msg = _assistant_text(constraint, minute)
        elif msg_type == 3:
            # Gotcha in assistant blocks with tool_use
            gotcha = gotcha_templates[msg_idx % len(gotcha_templates)]
            msg = _assistant_blocks([
                {"type": "tool_use", "name": "Read", "input": {"path": f"module_{msg_idx}.py"}},
                {"type": "text", "text": gotcha},
            ], minute)
        elif msg_type == 4:
            # Learning in assistant text
            learning = learning_templates[msg_idx % len(learning_templates)]
            msg = _assistant_text(learning, minute)
        elif msg_type == 5:
            # Mixed assistant blocks
            decision = decision_templates[msg_idx % len(decision_templates)]
            constraint = constraint_templates[msg_idx % len(constraint_templates)]
            msg = _assistant_blocks([
                {"type": "text", "text": decision},
                {"type": "tool_use", "name": "Write", "input": {"path": f"service_{msg_idx}.py"}},
                {"type": "text", "text": constraint},
            ], minute)
        elif msg_type == 6:
            # Progress noise
            msg = _noise_progress(minute)
        else:
            # System noise
            msg = _noise_system(minute)

        line = json.dumps(msg) + "\n"
        lines.append(line)
        current_size += len(line.encode())

    return "".join(lines)


# ============================================================================
# Heuristic Mode Benchmarks
# ============================================================================


class TestExtractionPerformanceBenchmarks:
    """Benchmark the memory extraction pipeline across different session sizes."""

    @pytest.mark.parametrize("size_kb", [100, 250, 500, 1000, 2500])
    def test_heuristic_mode_performance(self, seeded_db_path, size_kb, capsys):
        """Heuristic mode should complete within 5 seconds for sessions up to 2.5MB."""
        # Generate session
        session = _generate_session_jsonl(size_kb)
        actual_size_kb = len(session.encode()) / 1024

        # Run extraction
        service = MemoryExtractorService(db_path=seeded_db_path)
        start = time.perf_counter()
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=session,
            profile="balanced",
            min_confidence=0.0,
        )
        elapsed = time.perf_counter() - start

        # Verify completion time
        assert elapsed < HEURISTIC_TIME_LIMIT, (
            f"Heuristic mode for {size_kb}KB session took {elapsed:.2f}s "
            f"(limit: {HEURISTIC_TIME_LIMIT}s)"
        )

        # Verify extraction worked
        assert len(candidates) > 0, f"No candidates extracted from {size_kb}KB session"

        # Calculate throughput
        candidates_per_sec = len(candidates) / elapsed if elapsed > 0 else 0

        # Print results
        print(
            f"\n[Heuristic {size_kb:4d}KB] "
            f"Actual: {actual_size_kb:6.1f}KB | "
            f"Time: {elapsed:5.2f}s | "
            f"Candidates: {len(candidates):4d} | "
            f"Rate: {candidates_per_sec:6.1f} cand/s"
        )

    def test_heuristic_scaling_characteristics(self, seeded_db_path, capsys):
        """Verify that processing time grows roughly linearly, not exponentially."""
        sizes = [100, 250, 500]
        timings: List[tuple[int, float]] = []

        for size_kb in sizes:
            session = _generate_session_jsonl(size_kb)
            service = MemoryExtractorService(db_path=seeded_db_path)

            start = time.perf_counter()
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=session,
                profile="balanced",
                min_confidence=0.0,
            )
            elapsed = time.perf_counter() - start

            timings.append((size_kb, elapsed))
            assert len(candidates) > 0

        # Check scaling: 500KB should take less than 10x the time of 100KB
        # (allows for some overhead but rules out exponential scaling)
        time_100kb = timings[0][1]
        time_500kb = timings[2][1]
        ratio = time_500kb / time_100kb if time_100kb > 0 else 0

        assert ratio < 10.0, (
            f"Scaling appears exponential: 500KB took {ratio:.1f}x longer than 100KB "
            f"(expected roughly linear, max 10x)"
        )

        # Print scaling analysis
        print("\n--- Scaling Analysis ---")
        for size_kb, elapsed in timings:
            print(f"{size_kb:4d}KB: {elapsed:5.2f}s")
        print(f"Ratio (500KB / 100KB): {ratio:.2f}x")


# ============================================================================
# LLM Mode Benchmarks (Mocked)
# ============================================================================


class TestLLMModePerformanceBenchmarks:
    """Benchmark LLM classification mode (with mocked LLM calls)."""

    @pytest.mark.parametrize("size_kb", [100, 250, 500])
    def test_llm_mode_performance_mocked(self, seeded_db_path, size_kb, capsys):
        """LLM mode (mocked) should complete within 15 seconds."""
        # Generate session
        session = _generate_session_jsonl(size_kb)
        actual_size_kb = len(session.encode()) / 1024

        # Setup service with mocked LLM
        service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

        # Mock the LLM classifier
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_classifier.provider_name = "anthropic"
        mock_classifier.usage_stats = MagicMock()
        mock_classifier.usage_stats.summary.return_value = "mocked"
        service._classifier = mock_classifier

        # Mock batch classification to return fixed results instantly
        def mock_batch_classify(contents, classifier):
            # Return LLM-style results for each content item
            return [
                {
                    "type": "decision",
                    "confidence": 0.85,
                    "reasoning": "Mock classification"
                }
                for _ in contents
            ]

        with patch.object(service, "_semantic_classify_batch", side_effect=mock_batch_classify):
            # Run extraction
            start = time.perf_counter()
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=session,
                profile="balanced",
                min_confidence=0.0,
            )
            elapsed = time.perf_counter() - start

        # Verify completion time
        assert elapsed < LLM_TIME_LIMIT, (
            f"LLM mode (mocked) for {size_kb}KB session took {elapsed:.2f}s "
            f"(limit: {LLM_TIME_LIMIT}s)"
        )

        # Verify extraction worked
        assert len(candidates) > 0, f"No candidates extracted from {size_kb}KB session"

        # Calculate throughput
        candidates_per_sec = len(candidates) / elapsed if elapsed > 0 else 0

        # Print results
        print(
            f"\n[LLM Mock {size_kb:4d}KB] "
            f"Actual: {actual_size_kb:6.1f}KB | "
            f"Time: {elapsed:5.2f}s | "
            f"Candidates: {len(candidates):4d} | "
            f"Rate: {candidates_per_sec:6.1f} cand/s"
        )


# ============================================================================
# Throughput Statistics
# ============================================================================


class TestThroughputStatistics:
    """Generate comprehensive throughput statistics."""

    def test_throughput_summary(self, seeded_db_path, capsys):
        """Run multiple sizes and generate a summary table."""
        test_sizes = [100, 250, 500, 1000, 2500]
        results: List[tuple[int, float, float, int, float]] = []

        print("\n" + "=" * 80)
        print("MEMORY EXTRACTION PIPELINE PERFORMANCE BENCHMARK")
        print("=" * 80)

        for size_kb in test_sizes:
            session = _generate_session_jsonl(size_kb)
            actual_size_kb = len(session.encode()) / 1024

            service = MemoryExtractorService(db_path=seeded_db_path)

            start = time.perf_counter()
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=session,
                profile="balanced",
                min_confidence=0.0,
            )
            elapsed = time.perf_counter() - start

            candidates_per_sec = len(candidates) / elapsed if elapsed > 0 else 0

            results.append((size_kb, actual_size_kb, elapsed, len(candidates), candidates_per_sec))

        # Print summary table
        print("\n--- Heuristic Mode Performance Summary ---")
        print(f"{'Target':<8} {'Actual':<10} {'Time':<8} {'Candidates':<12} {'Rate':<15}")
        print(f"{'Size':<8} {'Size':<10} {'(sec)':<8} {'Extracted':<12} {'(cand/sec)':<15}")
        print("-" * 80)

        for target_kb, actual_kb, elapsed, count, rate in results:
            print(
                f"{target_kb:4d}KB   {actual_kb:6.1f}KB   "
                f"{elapsed:5.2f}s   {count:6d}       {rate:8.1f}"
            )

        print("-" * 80)
        print(f"Performance Target: < {HEURISTIC_TIME_LIMIT}s per session (all sizes)")
        print("=" * 80 + "\n")

        # All should pass the time limit
        for target_kb, actual_kb, elapsed, count, rate in results:
            assert elapsed < HEURISTIC_TIME_LIMIT, (
                f"{target_kb}KB session exceeded time limit: {elapsed:.2f}s"
            )
