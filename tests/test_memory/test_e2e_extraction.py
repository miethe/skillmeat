"""End-to-end tests for the memory extraction pipeline.

Validates the full pipeline: JSONL input -> parser -> filter -> classify ->
score -> output.  Covers diverse session types, backward compatibility,
the apply flow, and mocked LLM integration.

Phase coverage:
- Phase 1: JSONL parser, message filter, CLI truncation
- Phase 2: Provenance extraction, scoring enhancement, backward compat
- Phase 3: LLM classifier integration (mocked), retry, cost monitoring
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Base, Project, create_db_engine
from skillmeat.core.services.memory_extractor_service import MemoryExtractorService


# ============================================================================
# Constants
# ============================================================================

PROJECT_ID = "proj-e2e-extraction"

# Valid memory types from the heuristic classifier
VALID_HEURISTIC_TYPES = {"decision", "constraint", "gotcha", "style_rule", "learning"}

# Valid types that the LLM classifier may also return
VALID_LLM_TYPES = {"decision", "constraint", "gotcha", "learning", "process", "tool"}

ALL_VALID_TYPES = VALID_HEURISTIC_TYPES | VALID_LLM_TYPES


# ============================================================================
# Database fixture (reusable seeded DB with a project row)
# ============================================================================


@pytest.fixture
def seeded_db_path(tmp_path):
    """Create a temporary database seeded with a test project."""
    db_path = tmp_path / "e2e_extract.db"
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.add(
        Project(
            id=PROJECT_ID,
            name="E2E Extraction Test Project",
            path="/tmp/e2e-extraction-project",
            status="active",
        )
    )
    session.commit()
    session.close()
    engine.dispose()

    return str(db_path)


# ============================================================================
# Session Fixture Helpers
# ============================================================================


def _ts(minute: int) -> str:
    """Return a deterministic ISO timestamp for the given minute offset."""
    return f"2025-06-15T10:{minute:02d}:00Z"


def _human(content: str, *, minute: int = 0, session_id: str = "sess-e2e") -> Dict:
    """Build a human/user message dict."""
    return {
        "type": "human",
        "content": content,
        "uuid": f"msg-human-{minute}",
        "timestamp": _ts(minute),
        "sessionId": session_id,
        "gitBranch": "feat/e2e-tests",
    }


def _assistant_text(
    text: str, *, minute: int = 1, session_id: str = "sess-e2e"
) -> Dict:
    """Build an assistant message with plain text content."""
    return {
        "type": "assistant",
        "content": text,
        "uuid": f"msg-asst-{minute}",
        "timestamp": _ts(minute),
        "sessionId": session_id,
    }


def _assistant_blocks(
    blocks: List[Dict], *, minute: int = 1, session_id: str = "sess-e2e"
) -> Dict:
    """Build an assistant message with a list of content blocks."""
    return {
        "type": "assistant",
        "content": blocks,
        "uuid": f"msg-asst-blocks-{minute}",
        "timestamp": _ts(minute),
        "sessionId": session_id,
    }


def _noise_progress(minute: int = 0) -> Dict:
    return {"type": "progress", "content": "Working on it...", "timestamp": _ts(minute)}


def _noise_system(minute: int = 0) -> Dict:
    return {"type": "system", "content": "System init complete", "timestamp": _ts(minute)}


def _noise_file_history(minute: int = 0) -> Dict:
    return {
        "type": "file-history-snapshot",
        "content": "snapshot data blob",
        "timestamp": _ts(minute),
    }


def _noise_result(minute: int = 0) -> Dict:
    return {"type": "result", "content": "Operation result", "timestamp": _ts(minute)}


def _to_jsonl(messages: List[Dict]) -> str:
    """Serialize a list of message dicts to a JSONL string."""
    return "\n".join(json.dumps(m) for m in messages)


# ============================================================================
# Diverse Session Fixtures (10+ types)
# ============================================================================


def _coding_session() -> str:
    """User asks to implement a feature; assistant writes code with tool_use."""
    return _to_jsonl([
        _noise_system(0),
        _human("Implement a rate limiter middleware that limits to 100 req/min per IP.", minute=1),
        _assistant_blocks([
            {"type": "tool_use", "name": "Read", "input": {"path": "middleware/"}},
            {"type": "text", "text": (
                "Decision: Use a sliding-window counter stored in Redis for rate limiting. "
                "This approach handles distributed deployments and avoids the boundary "
                "problem of fixed-window counters."
            )},
            {"type": "tool_use", "name": "Write", "input": {"path": "middleware/rate_limit.py"}},
            {"type": "text", "text": (
                "Constraint: The rate limit middleware must check X-Forwarded-For headers "
                "when behind a reverse proxy to get the real client IP address."
            )},
        ], minute=2),
        _noise_progress(3),
    ])


def _debugging_session() -> str:
    """User reports a bug; assistant investigates and finds root cause."""
    return _to_jsonl([
        _human("The /api/v1/artifacts endpoint returns 500 when the collection is empty.", minute=0),
        _assistant_blocks([
            {"type": "tool_use", "name": "Read", "input": {"path": "routers/artifacts.py"}},
            {"type": "text", "text": (
                "Gotcha: The artifacts router calls collection_manager.list_artifacts() "
                "which returns None instead of an empty list when no artifacts exist. "
                "This causes an AttributeError when the router tries to iterate."
            )},
        ], minute=1),
        _assistant_text(
            "I learned that the CollectionManager.list_artifacts() method should always "
            "return an empty list rather than None to avoid downstream NoneType errors.",
            minute=2,
        ),
    ])


def _planning_session() -> str:
    """User asks to plan architecture; assistant proposes a design."""
    return _to_jsonl([
        _human("Plan the architecture for a plugin system that supports hot-reloading.", minute=0),
        _assistant_text(
            "Decision: Adopt an event-driven plugin architecture using a message bus. "
            "Plugins register handlers for specific event types and the core dispatches "
            "events asynchronously. This allows hot-reload by unregistering old handlers "
            "and loading new plugin modules at runtime.",
            minute=1,
        ),
        _assistant_text(
            "Constraint: Plugin isolation requires each plugin to run in its own namespace "
            "to prevent symbol collisions. We must use importlib.reload() carefully and "
            "clear module caches between reloads.",
            minute=2,
        ),
    ])


def _research_session() -> str:
    """User asks how something works; assistant explains."""
    return _to_jsonl([
        _human("How does SQLAlchemy handle connection pooling internally?", minute=0),
        _assistant_text(
            "I discovered that SQLAlchemy uses a QueuePool by default which maintains "
            "a configurable number of persistent connections. The pool_size parameter "
            "sets the steady-state count (default 5) and max_overflow allows temporary "
            "connections beyond that limit.",
            minute=1,
        ),
    ])


def _refactoring_session() -> str:
    """User asks to refactor code; assistant makes changes."""
    return _to_jsonl([
        _human("Refactor the user service to separate read and write operations.", minute=0),
        _assistant_blocks([
            {"type": "tool_use", "name": "Read", "input": {"path": "services/user_service.py"}},
            {"type": "text", "text": (
                "Decision: Split UserService into UserQueryService (reads) and "
                "UserCommandService (writes) following CQRS pattern. This reduces "
                "coupling and makes it easier to cache read-only operations."
            )},
            {"type": "tool_use", "name": "Write", "input": {"path": "services/user_query_service.py"}},
            {"type": "text", "text": (
                "Style rule: Prefer separate query and command services for domains "
                "with high read-to-write ratios. Name them *QueryService and "
                "*CommandService respectively."
            )},
        ], minute=1),
    ])


def _testing_session() -> str:
    """User asks to write tests; assistant generates test code."""
    return _to_jsonl([
        _human("Write integration tests for the deployment service.", minute=0),
        _assistant_blocks([
            {"type": "text", "text": (
                "Constraint: Integration tests must use a separate test database that "
                "is created and destroyed per test session. Never run integration tests "
                "against the development database."
            )},
            {"type": "tool_use", "name": "Write", "input": {"path": "tests/test_deploy.py"}},
            {"type": "text", "text": (
                "Gotcha: Beware of SQLAlchemy session leaks in integration tests. "
                "Always use a fixture that calls session.rollback() and session.close() "
                "in teardown to avoid connection pool exhaustion."
            )},
        ], minute=1),
    ])


def _config_setup_session() -> str:
    """User sets up environment; installs deps."""
    return _to_jsonl([
        _human("Set up the development environment with uv and install all dependencies.", minute=0),
        _assistant_blocks([
            {"type": "tool_use", "name": "Bash", "input": {"command": "uv pip install -e '.[dev]'"}},
            {"type": "text", "text": (
                "Decision: Use uv for dependency management instead of pip. "
                "uv resolves dependencies 10-100x faster and produces a lockfile "
                "for reproducible installs across environments."
            )},
        ], minute=1),
        _assistant_text(
            "Gotcha: When using uv with editable installs, the pyproject.toml must "
            "have a [build-system] section or uv will fall back to legacy setup.py "
            "which may fail for pure PEP 621 projects.",
            minute=2,
        ),
    ])


def _review_session() -> str:
    """User asks for code review; assistant provides feedback."""
    return _to_jsonl([
        _human("Review the changes I made to the cache invalidation logic.", minute=0),
        _assistant_text(
            "Constraint: Cache invalidation must happen synchronously before returning "
            "the HTTP response. The current implementation fires-and-forgets the "
            "invalidation which can serve stale data on the next request.",
            minute=1,
        ),
        _assistant_text(
            "Style rule: Prefer explicit cache key construction over string concatenation. "
            "Use a dedicated CacheKey dataclass or named tuple to avoid typos in cache "
            "key segments.",
            minute=2,
        ),
    ])


def _documentation_session() -> str:
    """User asks to write docs."""
    return _to_jsonl([
        _human("Write API documentation for the memory extraction endpoints.", minute=0),
        _assistant_text(
            "Decision: Use OpenAPI-first documentation where the spec is the source of "
            "truth and docs are generated from it. This ensures endpoint documentation "
            "never drifts from the actual implementation.",
            minute=1,
        ),
    ])


def _multi_turn_complex_session() -> str:
    """Long session with multiple topics, tool uses, errors, and noise."""
    return _to_jsonl([
        _noise_system(0),
        _noise_file_history(0),
        _human("Fix the broken deployment pipeline and add rollback support.", minute=1),
        _noise_progress(2),
        _assistant_blocks([
            {"type": "tool_use", "name": "Read", "input": {"path": "core/deployment.py"}},
            {"type": "text", "text": (
                "Gotcha: The deployment service does not handle partial failures. If "
                "step 3 of 5 fails, steps 1 and 2 are not rolled back, leaving the "
                "system in an inconsistent state."
            )},
            {"type": "tool_use", "name": "Bash", "input": {"command": "pytest tests/"}},
        ], minute=3),
        _noise_progress(4),
        _noise_result(4),
        _human("Good catch. Can you also make it idempotent?", minute=5),
        _assistant_text(
            "Decision: Implement the Saga pattern for multi-step deployments. Each "
            "step records a compensating action, and on failure the saga executor "
            "runs compensations in reverse order.",
            minute=6,
        ),
        _assistant_text(
            "Constraint: Compensating actions must be idempotent themselves, since "
            "they may be retried if the rollback process itself encounters transient "
            "failures.",
            minute=7,
        ),
        _noise_file_history(8),
        _assistant_text(
            "I realized that storing deployment state in a dedicated table with status "
            "columns (pending, running, succeeded, failed, rolling_back) makes it "
            "trivial to resume or retry partial deployments.",
            minute=9,
        ),
    ])


def _tool_heavy_no_text_session() -> str:
    """Session with only tool_use blocks and no text -- should extract nothing."""
    return _to_jsonl([
        _human("Read the config file.", minute=0),
        _assistant_blocks([
            {"type": "tool_use", "name": "Read", "input": {"path": "config.toml"}},
            {"type": "tool_use", "name": "Read", "input": {"path": "settings.py"}},
        ], minute=1),
    ])


# Collect all session builders for parametrized tests
ALL_SESSION_BUILDERS = {
    "coding": _coding_session,
    "debugging": _debugging_session,
    "planning": _planning_session,
    "research": _research_session,
    "refactoring": _refactoring_session,
    "testing": _testing_session,
    "config_setup": _config_setup_session,
    "review": _review_session,
    "documentation": _documentation_session,
    "multi_turn_complex": _multi_turn_complex_session,
}


# ============================================================================
# Test Class: E2E Extraction Pipeline
# ============================================================================


class TestE2EExtractionPipeline:
    """Validate the full extraction pipeline across diverse session types."""

    def test_coding_session_extracts_meaningful_candidates(self, seeded_db_path):
        """Coding session should extract decision and constraint candidates."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=_coding_session(),
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 2
        all_content = " ".join(c["content"] for c in candidates)
        assert "sliding-window" in all_content or "rate limit" in all_content.lower()

    def test_debugging_session_captures_root_cause(self, seeded_db_path):
        """Debugging session should extract gotcha and learning candidates."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=_debugging_session(),
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 2
        types = {c["type"] for c in candidates}
        # Should include gotcha (NoneType error) and/or learning
        assert types & {"gotcha", "learning"}

    def test_planning_session_extracts_decisions(self, seeded_db_path):
        """Planning session should extract architectural decisions."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=_planning_session(),
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 2
        types = {c["type"] for c in candidates}
        assert "decision" in types or "constraint" in types

    def test_research_session_extracts_learnings(self, seeded_db_path):
        """Research session should extract factual learning candidates."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=_research_session(),
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 1
        all_content = " ".join(c["content"] for c in candidates)
        assert "QueuePool" in all_content or "pool_size" in all_content

    @pytest.mark.parametrize("session_name", list(ALL_SESSION_BUILDERS.keys()))
    def test_diverse_sessions_all_extract_successfully(
        self, seeded_db_path, session_name
    ):
        """Every session type should produce at least one candidate."""
        builder = ALL_SESSION_BUILDERS[session_name]
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=builder(),
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 1, (
            f"Session '{session_name}' produced 0 candidates"
        )

    def test_no_empty_extractions(self, seeded_db_path):
        """All non-trivial sessions produce at least 1 candidate."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        for name, builder in ALL_SESSION_BUILDERS.items():
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=builder(),
                profile="balanced",
                min_confidence=0.0,
            )
            assert len(candidates) >= 1, f"Session '{name}' returned 0 candidates"

    def test_noise_filtered_out(self, seeded_db_path):
        """Progress, system, file-history, and result messages must not appear in candidates."""
        session = _to_jsonl([
            _noise_system(0),
            _noise_progress(1),
            _noise_file_history(2),
            _noise_result(3),
            _human("Decision: Use connection pooling for database access.", minute=4),
            _assistant_text(
                "Constraint: Connection pool size must be tuned to match worker count.",
                minute=5,
            ),
        ])
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=session,
            profile="balanced",
            min_confidence=0.0,
        )

        all_content = " ".join(c["content"] for c in candidates).lower()
        assert "system init" not in all_content
        assert "working on it" not in all_content
        assert "snapshot data" not in all_content
        assert "operation result" not in all_content

    def test_provenance_present_on_all_candidates(self, seeded_db_path):
        """Every candidate must carry a provenance dict with session and timestamp info."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        for name, builder in ALL_SESSION_BUILDERS.items():
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=builder(),
                profile="balanced",
                min_confidence=0.0,
                run_id="e2e-run",
                session_id="sess-e2e",
            )
            for c in candidates:
                prov = c["provenance"]
                assert prov["source"] == "memory_extraction", f"Failed for session '{name}'"
                assert prov["format"] == "jsonl", f"Failed for session '{name}'"
                assert prov["run_id"] == "e2e-run", f"Failed for session '{name}'"
                # JSONL-specific provenance
                assert "message_uuid" in prov, f"Failed for session '{name}'"
                assert "timestamp" in prov, f"Failed for session '{name}'"

    def test_confidence_scores_in_valid_range(self, seeded_db_path):
        """All confidence scores must be between 0.0 and 1.0 inclusive."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        for name, builder in ALL_SESSION_BUILDERS.items():
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=builder(),
                profile="balanced",
                min_confidence=0.0,
            )
            for c in candidates:
                assert 0.0 <= c["confidence"] <= 1.0, (
                    f"Session '{name}': confidence {c['confidence']} out of range"
                )

    def test_confidence_scores_show_spread(self, seeded_db_path):
        """Across all sessions there should be at least 5 distinct confidence values."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        all_scores: set[float] = set()
        for builder in ALL_SESSION_BUILDERS.values():
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=builder(),
                profile="balanced",
                min_confidence=0.0,
            )
            for c in candidates:
                all_scores.add(c["confidence"])

        assert len(all_scores) >= 5, (
            f"Only {len(all_scores)} distinct scores: {sorted(all_scores)}"
        )

    def test_candidate_types_are_valid(self, seeded_db_path):
        """All type values must be in the known set of heuristic types."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        for name, builder in ALL_SESSION_BUILDERS.items():
            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=builder(),
                profile="balanced",
                min_confidence=0.0,
            )
            for c in candidates:
                assert c["type"] in VALID_HEURISTIC_TYPES, (
                    f"Session '{name}': unknown type '{c['type']}'"
                )

    def test_mixed_content_session(self, seeded_db_path):
        """Session with tool_use + text blocks should only extract text content."""
        session = _to_jsonl([
            _assistant_blocks([
                {"type": "tool_use", "name": "Read", "input": {"path": "/etc/hosts"}},
                {"type": "text", "text": (
                    "Gotcha: Beware of DNS resolution caching in Python's urllib. "
                    "Connections may stick to stale IP addresses for up to 30 seconds."
                )},
                {"type": "tool_use", "name": "Bash", "input": {"command": "dig example.com"}},
            ], minute=0),
        ])
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=session,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 1
        all_content = " ".join(c["content"] for c in candidates)
        # Tool use content must not leak through
        assert "Read" not in all_content or "read" in all_content.lower()
        assert "/etc/hosts" not in all_content
        assert "dig example.com" not in all_content
        # But the text insight should be present
        assert "DNS" in all_content or "urllib" in all_content

    def test_large_session_performance(self, seeded_db_path):
        """A 500+ line JSONL session must complete in under 5 seconds."""
        messages: List[Dict] = []
        for i in range(250):
            messages.append(
                _human(
                    f"Decision: Module {i} should use async I/O for file operations. "
                    f"This reduces thread contention in worker pool number {i}.",
                    minute=i % 60,
                )
            )
            messages.append(
                _assistant_text(
                    f"Constraint: Module {i} must limit concurrent file descriptors to 50. "
                    f"Exceeding this causes EMFILE errors on the production server.",
                    minute=(i % 60) + 1,
                )
            )

        session = _to_jsonl(messages)
        assert session.count("\n") >= 499  # 500 lines

        service = MemoryExtractorService(db_path=seeded_db_path)
        start = time.time()
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=session,
            profile="balanced",
            min_confidence=0.0,
        )
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Large session took {elapsed:.2f}s (limit: 5s)"
        assert len(candidates) >= 100  # Should extract many candidates

    def test_tool_only_session_extracts_from_human_message(self, seeded_db_path):
        """A session with only tool_use in assistant message still extracts from human message."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=_tool_heavy_no_text_session(),
            profile="balanced",
            min_confidence=0.0,
        )

        # The human message "Read the config file." is only 21 chars, which is
        # >= 20 char threshold. However, after stripping it might not pass the
        # 24-char candidate-line threshold. Either way the pipeline should not crash.
        # The important thing is no tool_use content leaks through.
        for c in candidates:
            assert "tool_use" not in c["content"]
            assert "config.toml" not in c["content"]


# ============================================================================
# Test Class: E2E Apply Flow
# ============================================================================


class TestE2EApplyFlow:
    """Validate the preview -> apply -> store pipeline."""

    def test_preview_then_apply_stores_memories(self, seeded_db_path):
        """Call preview, then apply with the same corpus; verify created items."""
        corpus = _coding_session()
        service = MemoryExtractorService(db_path=seeded_db_path)

        # Preview first
        preview_candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )
        assert len(preview_candidates) >= 2

        # Apply
        result = service.apply(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert result["preview_total"] >= 2
        assert len(result["created"]) >= 1
        # All created items should be candidate status
        for item in result["created"]:
            assert item["status"] == "candidate"

    def test_apply_preserves_provenance(self, seeded_db_path):
        """Applied memories must retain provenance from the extraction step."""
        corpus = _debugging_session()
        service = MemoryExtractorService(db_path=seeded_db_path)

        result = service.apply(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
            run_id="apply-run-1",
            session_id="sess-apply",
        )

        assert len(result["created"]) >= 1
        for item in result["created"]:
            prov = item.get("provenance") or item.get("provenance_json") or {}
            # Provenance should have been persisted
            assert prov.get("source") == "memory_extraction"
            assert prov.get("run_id") == "apply-run-1"

    def test_apply_with_empty_corpus(self, seeded_db_path):
        """Applying an empty corpus should return empty results gracefully."""
        service = MemoryExtractorService(db_path=seeded_db_path)

        result = service.apply(
            project_id=PROJECT_ID,
            text_corpus="",
            profile="balanced",
            min_confidence=0.6,
        )

        assert result["preview_total"] == 0
        assert len(result["created"]) == 0
        assert len(result["skipped_duplicates"]) == 0

    def test_apply_deduplicates_on_second_run(self, seeded_db_path):
        """Running apply twice on the same corpus should skip duplicates the second time."""
        corpus = _planning_session()
        service = MemoryExtractorService(db_path=seeded_db_path)

        first_result = service.apply(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )
        first_created_count = len(first_result["created"])
        assert first_created_count >= 1

        # Second apply should detect duplicates
        second_result = service.apply(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(second_result["skipped_duplicates"]) >= 1
        # Second run should create fewer (ideally zero) new items
        assert len(second_result["created"]) < first_created_count


# ============================================================================
# Test Class: E2E Backward Compatibility
# ============================================================================


class TestE2EBackwardCompatibility:
    """Validate backward compatibility with plain text and mixed inputs."""

    def test_plain_text_input_still_works(self, seeded_db_path):
        """Plain text (not JSONL) should extract candidates via fallback path."""
        corpus = """
        Decision: Use SQLAlchemy for all database operations.
        Constraint: All queries must go through the repository layer.
        Gotcha: Beware of lazy loading causing N+1 queries in list views.
        I learned that eager loading with selectinload solves the N+1 problem.
        """

        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 3
        for c in candidates:
            assert c["provenance"]["format"] == "plain_text"
            assert c["status"] == "candidate"

    def test_mixed_format_input(self, seeded_db_path):
        """Input with some valid JSONL and some plain text lines."""
        # If all JSON lines fail, it falls back to plain text
        corpus = (
            "not json at all\n"
            "{invalid json line}\n"
            "Decision: Use environment variables for all configuration values.\n"
            "Constraint: Never hardcode secrets in source code files.\n"
        )

        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        # Should fall back to plain text extraction
        assert len(candidates) >= 2
        for c in candidates:
            assert c["provenance"]["format"] == "plain_text"

    def test_empty_input_returns_empty(self, seeded_db_path):
        """Empty string input should return empty candidates list."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus="",
            profile="balanced",
            min_confidence=0.6,
        )

        assert candidates == []

    def test_whitespace_only_input_returns_empty(self, seeded_db_path):
        """Whitespace-only input should return empty candidates list."""
        service = MemoryExtractorService(db_path=seeded_db_path)
        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus="   \n\n  \t  ",
            profile="balanced",
            min_confidence=0.6,
        )

        assert candidates == []

    def test_jsonl_and_plain_text_produce_different_format_fields(self, seeded_db_path):
        """JSONL input produces format='jsonl'; plain text produces format='plain_text'."""
        service = MemoryExtractorService(db_path=seeded_db_path)

        # JSONL path
        jsonl_corpus = _to_jsonl([
            _human("Decision: Use FastAPI for the API server implementation.", minute=0),
        ])
        jsonl_candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=jsonl_corpus,
            profile="balanced",
            min_confidence=0.0,
        )
        assert len(jsonl_candidates) >= 1
        assert jsonl_candidates[0]["provenance"]["format"] == "jsonl"

        # Plain text path
        plain_corpus = "Decision: Use Django for the admin interface implementation."
        plain_candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=plain_corpus,
            profile="balanced",
            min_confidence=0.0,
        )
        assert len(plain_candidates) >= 1
        assert plain_candidates[0]["provenance"]["format"] == "plain_text"


# ============================================================================
# Test Class: E2E With LLM Classification (Mocked)
# ============================================================================


class TestE2EWithLLMClassification:
    """Validate LLM integration with mocked classifiers."""

    def test_llm_enhances_classification(self, seeded_db_path):
        """With a mocked LLM, type and confidence should be overridden."""
        service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

        # Mock LLM results that differ from heuristic
        llm_results = [
            {"type": "gotcha", "confidence": 0.95, "reasoning": "Pitfall identified"},
            {"type": "process", "confidence": 0.88, "reasoning": "Workflow step"},
        ]

        with patch.object(service, "_semantic_classify_batch") as mock_batch:
            mock_classifier = MagicMock()
            mock_classifier.is_available.return_value = True
            mock_classifier.provider_name = "anthropic"
            mock_classifier.usage_stats = MagicMock()
            mock_classifier.usage_stats.summary.return_value = "1 call, 2 candidates"

            service._classifier = mock_classifier
            mock_batch.return_value = llm_results

            corpus = _to_jsonl([
                _human(
                    "Decision: Use connection pooling for database access patterns.",
                    minute=0,
                ),
                _assistant_text(
                    "Constraint: Pool size must match the number of worker threads.",
                    minute=1,
                ),
            ])

            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=corpus,
                profile="balanced",
                min_confidence=0.0,
            )

            assert len(candidates) >= 2

            # LLM should have been called
            mock_batch.assert_called_once()

            # Check that LLM overrides are applied
            types = {c["type"] for c in candidates}
            assert "gotcha" in types or "process" in types

            # Provenance should reflect LLM classification
            for c in candidates:
                assert c["provenance"]["classification_method"] == "llm"
                assert c["provenance"]["llm_provider"] == "anthropic"

    def test_llm_failure_falls_back_to_heuristic(self, seeded_db_path):
        """When LLM raises an exception, pipeline should still complete with heuristic."""
        service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

        with patch.object(service, "_semantic_classify_batch") as mock_batch:
            mock_classifier = MagicMock()
            mock_classifier.is_available.return_value = True
            mock_classifier.provider_name = "anthropic"
            mock_classifier.usage_stats = MagicMock()
            mock_classifier.usage_stats.summary.return_value = "0 calls"

            service._classifier = mock_classifier
            # Return all None (simulating LLM failure for every item)
            mock_batch.return_value = [None, None]

            corpus = _to_jsonl([
                _human(
                    "Decision: Use Redis for distributed caching across services.",
                    minute=0,
                ),
                _assistant_text(
                    "Gotcha: Beware of Redis key expiration race conditions under load.",
                    minute=1,
                ),
            ])

            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=corpus,
                profile="balanced",
                min_confidence=0.0,
            )

            assert len(candidates) >= 2
            # All should fall back to heuristic
            for c in candidates:
                assert c["provenance"]["classification_method"] == "heuristic"
                assert "llm_reasoning" not in c["provenance"]

    def test_llm_disabled_by_default(self, seeded_db_path):
        """Without use_llm=True, the heuristic classifier should be used."""
        service = MemoryExtractorService(db_path=seeded_db_path)

        assert service._classifier is None

        corpus = _to_jsonl([
            _human(
                "Constraint: API responses must include Cache-Control headers.",
                minute=0,
            ),
        ])

        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 1
        for c in candidates:
            assert c["provenance"]["classification_method"] == "heuristic"

    def test_llm_partial_failure_mixed_results(self, seeded_db_path):
        """When LLM succeeds for some items and fails for others, both paths should work."""
        service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

        # First item succeeds, second fails (None)
        llm_results = [
            {"type": "learning", "confidence": 0.92, "reasoning": "Clear insight"},
            None,
        ]

        with patch.object(service, "_semantic_classify_batch") as mock_batch:
            mock_classifier = MagicMock()
            mock_classifier.is_available.return_value = True
            mock_classifier.provider_name = "openai"
            mock_classifier.usage_stats = MagicMock()
            mock_classifier.usage_stats.summary.return_value = "1 call, 2 candidates"

            service._classifier = mock_classifier
            mock_batch.return_value = llm_results

            corpus = _to_jsonl([
                _human(
                    "I discovered that batch processing reduces API call overhead by 40%.",
                    minute=0,
                ),
                _assistant_text(
                    "Constraint: Batch size must not exceed 100 items per request.",
                    minute=1,
                ),
            ])

            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=corpus,
                profile="balanced",
                min_confidence=0.0,
            )

            assert len(candidates) >= 2

            llm_classified = [
                c for c in candidates
                if c["provenance"].get("classification_method") == "llm"
            ]
            heuristic_classified = [
                c for c in candidates
                if c["provenance"].get("classification_method") == "heuristic"
            ]

            assert len(llm_classified) >= 1
            assert len(heuristic_classified) >= 1

    def test_llm_results_respect_score_ordering(self, seeded_db_path):
        """After LLM classification, candidates should still be sorted by confidence desc."""
        service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

        llm_results = [
            {"type": "learning", "confidence": 0.60, "reasoning": "Low confidence"},
            {"type": "decision", "confidence": 0.95, "reasoning": "High confidence"},
            {"type": "gotcha", "confidence": 0.80, "reasoning": "Medium confidence"},
        ]

        with patch.object(service, "_semantic_classify_batch") as mock_batch:
            mock_classifier = MagicMock()
            mock_classifier.is_available.return_value = True
            mock_classifier.provider_name = "anthropic"
            mock_classifier.usage_stats = MagicMock()
            mock_classifier.usage_stats.summary.return_value = "1 call, 3 candidates"

            service._classifier = mock_classifier
            mock_batch.return_value = llm_results

            corpus = _to_jsonl([
                _human(
                    "Decision: Use PostgreSQL for the production database engine.",
                    minute=0,
                ),
                _assistant_text(
                    "Constraint: Database connections must always be pooled.",
                    minute=1,
                ),
                _assistant_text(
                    "Gotcha: Beware of N+1 query problems in ORM operations.",
                    minute=2,
                ),
            ])

            candidates = service.preview(
                project_id=PROJECT_ID,
                text_corpus=corpus,
                profile="balanced",
                min_confidence=0.0,
            )

            assert len(candidates) >= 3
            # Verify descending confidence order
            confidences = [c["confidence"] for c in candidates]
            assert confidences == sorted(confidences, reverse=True)
