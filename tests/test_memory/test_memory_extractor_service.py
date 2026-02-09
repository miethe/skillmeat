"""Tests for MemoryExtractorService."""

import json
import pytest
from sqlalchemy.orm import sessionmaker

from skillmeat.cache.models import Base, Project, create_db_engine
from skillmeat.core.services.memory_extractor_service import MemoryExtractorService


PROJECT_ID = "proj-extract-test"


@pytest.fixture
def seeded_db_path(tmp_path):
    db_path = tmp_path / "extract.db"
    engine = create_db_engine(db_path)
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()
    session.add(
        Project(
            id=PROJECT_ID,
            name="Extraction Test Project",
            path="/tmp/extraction-project",
            status="active",
        )
    )
    session.commit()
    session.close()
    engine.dispose()

    return str(db_path)


def test_preview_extracts_candidates(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)
    corpus = """
    Decision: Use SQLAlchemy for persistence.
    Constraint: We must keep p95 latency under 200ms.
    Gotcha: Beware sqlite lock timeout during parallel tests.
    """

    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.6,
    )

    assert len(candidates) >= 2
    assert all(c["status"] == "candidate" for c in candidates)
    assert all(c["confidence"] >= 0.6 for c in candidates)


def test_apply_persists_candidates_as_candidate_status(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)
    corpus = "Decision: Choose deterministic retries for flaky API calls."

    result = service.apply(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.6,
    )

    assert result["preview_total"] >= 1
    assert len(result["created"]) >= 1
    assert all(item["status"] == "candidate" for item in result["created"])


def test_profile_scoring_order_strict_vs_aggressive(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)
    corpus = "Decision: Use transactional retries for lock contention handling."

    strict = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="strict",
        min_confidence=0.0,
    )
    aggressive = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="aggressive",
        min_confidence=0.0,
    )

    assert len(strict) == 1
    assert len(aggressive) == 1
    assert aggressive[0]["confidence"] > strict[0]["confidence"]


def test_invalid_profile_raises_value_error(seeded_db_path):
    service = MemoryExtractorService(db_path=seeded_db_path)

    with pytest.raises(ValueError, match="Invalid extraction profile"):
        service.preview(
            project_id=PROJECT_ID,
            text_corpus="Decision: Use deterministic retries.",
            profile="experimental",
            min_confidence=0.0,
        )


# ============================================================================
# JSONL Parser Tests (_parse_jsonl_messages)
# ============================================================================


def test_parse_jsonl_valid():
    """Multiple valid JSON lines should all be parsed as dicts."""
    corpus = (
        '{"role": "user", "content": "hello"}\n{"role": "assistant", "content": "hi"}'
    )
    result = MemoryExtractorService._parse_jsonl_messages(corpus)

    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "hello"}
    assert result[1] == {"role": "assistant", "content": "hi"}


def test_parse_jsonl_malformed():
    """Mix of valid and invalid lines should return only valid ones."""
    corpus = '{"role": "user"}\ninvalid json\n{"role": "assistant"}'
    result = MemoryExtractorService._parse_jsonl_messages(corpus)

    assert len(result) == 2
    assert result[0] == {"role": "user"}
    assert result[1] == {"role": "assistant"}


def test_parse_jsonl_empty():
    """Empty string should return empty list."""
    result = MemoryExtractorService._parse_jsonl_messages("")
    assert result == []


def test_parse_jsonl_whitespace_only():
    """Whitespace-only input should return empty list."""
    result = MemoryExtractorService._parse_jsonl_messages("   \n\n  \t  ")
    assert result == []


def test_parse_jsonl_non_dict_lines():
    """Lines that parse as JSON but aren't dicts should be filtered out."""
    corpus = '["array", "of", "strings"]\n42\n"just a string"\n{"role": "user"}'
    result = MemoryExtractorService._parse_jsonl_messages(corpus)

    assert len(result) == 1
    assert result[0] == {"role": "user"}


def test_parse_jsonl_escaped_newlines():
    """JSON-string-wrapped JSONL should be correctly unwrapped and parsed."""
    # Simulate what Claude CLI might export: entire JSONL corpus as a JSON string
    inner_jsonl = '{"role": "user"}\n{"role": "assistant"}'  # Actual newline in string
    json_wrapped = json.dumps(
        inner_jsonl
    )  # Produces: '"{\\"role\\":\\"user\\"}\\n..."'

    result = MemoryExtractorService._parse_jsonl_messages(json_wrapped)

    assert len(result) == 2
    assert result[0] == {"role": "user"}
    assert result[1] == {"role": "assistant"}


# ============================================================================
# Message Filter Tests (_extract_content_blocks)
# ============================================================================


def test_filter_skips_progress():
    """Messages with type=progress should be filtered out."""
    messages = [{"type": "progress", "content": "Working on it..."}]
    result = MemoryExtractorService._extract_content_blocks(messages)
    assert len(result) == 0


def test_filter_skips_system():
    """Messages with type=system should be filtered out."""
    messages = [{"type": "system", "content": "System initialization complete"}]
    result = MemoryExtractorService._extract_content_blocks(messages)
    assert len(result) == 0


def test_filter_skips_file_history():
    """Messages with type=file-history-snapshot should be filtered out."""
    messages = [{"type": "file-history-snapshot", "content": "File snapshot data"}]
    result = MemoryExtractorService._extract_content_blocks(messages)
    assert len(result) == 0


def test_filter_skips_result():
    """Messages with type=result should be filtered out."""
    messages = [{"type": "result", "content": "Operation completed"}]
    result = MemoryExtractorService._extract_content_blocks(messages)
    assert len(result) == 0


def test_filter_extracts_human_text():
    """Human messages with string content should be extracted."""
    messages = [
        {
            "type": "human",
            "content": "Decision: Use SQLAlchemy for database operations.",
            "uuid": "msg-123",
            "timestamp": "2024-01-01T00:00:00Z",
        }
    ]
    result = MemoryExtractorService._extract_content_blocks(messages)

    assert len(result) == 1
    content_text, provenance = result[0]
    assert "Decision: Use SQLAlchemy" in content_text
    assert provenance["message_uuid"] == "msg-123"
    assert provenance["message_role"] == "human"
    assert provenance["timestamp"] == "2024-01-01T00:00:00Z"


def test_filter_extracts_assistant_text_blocks():
    """Assistant messages with list content should extract text blocks and skip tool_use."""
    messages = [
        {
            "type": "assistant",
            "content": [
                {"type": "text", "text": "Constraint: API rate limit is 100 req/min."},
                {"type": "tool_use", "name": "read_file", "input": {"path": "/test"}},
                {"type": "text", "text": "Gotcha: Beware of timezone handling."},
            ],
            "uuid": "msg-456",
            "timestamp": "2024-01-02T00:00:00Z",
        }
    ]
    result = MemoryExtractorService._extract_content_blocks(messages)

    assert len(result) == 1
    content_text, provenance = result[0]
    assert "Constraint: API rate limit" in content_text
    assert "Gotcha: Beware of timezone" in content_text
    assert "read_file" not in content_text  # tool_use should be filtered
    assert provenance["message_uuid"] == "msg-456"


def test_filter_skips_meta_messages():
    """Messages with isMeta=True should be skipped."""
    messages = [
        {
            "type": "human",
            "content": "This is metadata, not real content",
            "isMeta": True,
        }
    ]
    result = MemoryExtractorService._extract_content_blocks(messages)
    assert len(result) == 0


def test_filter_skips_tool_use_results():
    """Messages with toolUseResult=True should be skipped."""
    messages = [
        {
            "type": "assistant",
            "content": "Tool execution result data",
            "toolUseResult": True,
        }
    ]
    result = MemoryExtractorService._extract_content_blocks(messages)
    assert len(result) == 0


def test_filter_short_content():
    """Content less than 20 characters should be filtered out."""
    messages = [
        {"type": "human", "content": "Too short"},  # 9 chars
        {
            "type": "human",
            "content": "This content is long enough to be extracted properly.",
        },
    ]
    result = MemoryExtractorService._extract_content_blocks(messages)

    assert len(result) == 1
    assert "long enough" in result[0][0]


def test_filter_provenance_metadata():
    """Extracted blocks should include correct provenance metadata."""
    messages = [
        {
            "type": "assistant",
            "role": "assistant",
            "content": "Decision: Adopt FastAPI for API server implementation.",
            "uuid": "msg-789",
            "timestamp": "2024-01-03T12:00:00Z",
            "sessionId": "session-abc",
        }
    ]
    result = MemoryExtractorService._extract_content_blocks(messages)

    assert len(result) == 1
    content_text, provenance = result[0]
    assert provenance["message_uuid"] == "msg-789"
    assert provenance["message_role"] == "assistant"
    assert provenance["timestamp"] == "2024-01-03T12:00:00Z"
    assert provenance["session_id"] == "session-abc"


# ============================================================================
# Integration Tests (JSONL Pipeline)
# ============================================================================


def test_preview_jsonl_full_pipeline(seeded_db_path):
    """Realistic JSONL corpus should extract candidates with proper filtering and provenance."""
    messages = [
        {"type": "system", "content": "System initialized"},  # Should be filtered
        {
            "type": "human",
            "content": "Decision: Use PostgreSQL for production database.",
            "uuid": "msg-001",
            "timestamp": "2024-01-01T10:00:00Z",
            "sessionId": "sess-123",
        },
        {"type": "progress", "content": "Processing..."},  # Should be filtered
        {
            "type": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Constraint: Database connections must be pooled.",
                },
                {"type": "tool_use", "name": "grep", "input": {"pattern": "db"}},
            ],
            "uuid": "msg-002",
            "timestamp": "2024-01-01T10:05:00Z",
            "sessionId": "sess-123",
        },
        {
            "type": "human",
            "content": "Gotcha: Beware of N+1 query problems in ORM.",
            "uuid": "msg-003",
            "timestamp": "2024-01-01T10:10:00Z",
        },
    ]

    # Convert to JSONL format
    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.0,
        run_id="test-run",
        session_id="sess-123",
    )

    # Should extract 3 candidates (PostgreSQL decision, connection pooling constraint, N+1 gotcha)
    assert len(candidates) >= 3

    # All should have candidate status
    assert all(c["status"] == "candidate" for c in candidates)

    # Check provenance is populated
    for candidate in candidates:
        prov = candidate["provenance"]
        assert prov["source"] == "memory_extraction"
        assert prov["run_id"] == "test-run"
        assert "message_uuid" in prov  # JSONL-specific provenance
        assert "message_role" in prov
        assert "timestamp" in prov

    # Verify noise was filtered (no system, progress, or tool_use content)
    all_content = " ".join(c["content"] for c in candidates)
    assert "System initialized" not in all_content
    assert "Processing..." not in all_content
    assert "grep" not in all_content


def test_preview_plaintext_fallback(seeded_db_path):
    """Plain text (not JSONL) should use legacy extraction path."""
    corpus = """
    Decision: Use Redis for session storage.
    Constraint: Sessions must expire after 24 hours.
    Gotcha: Beware of Redis memory limits in development.
    """

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    # Should extract candidates using plain-text path
    assert len(candidates) >= 3
    assert all(c["status"] == "candidate" for c in candidates)

    # Provenance should NOT have JSONL-specific fields
    for candidate in candidates:
        prov = candidate["provenance"]
        assert "message_uuid" not in prov
        assert "message_role" not in prov


def test_preview_jsonl_with_tool_use(seeded_db_path):
    """JSONL with tool_use blocks should filter tool_use and preserve text."""
    messages = [
        {
            "type": "assistant",
            "content": [
                {"type": "tool_use", "name": "read_file", "input": {"path": "/config"}},
                {
                    "type": "text",
                    "text": "Decision: Configuration stored in environment variables.",
                },
                {"type": "tool_use", "name": "bash", "input": {"command": "ls"}},
                {
                    "type": "text",
                    "text": "Constraint: Environment variables must be validated at startup.",
                },
            ],
            "uuid": "msg-100",
            "timestamp": "2024-01-05T00:00:00Z",
        }
    ]

    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    # Should extract 2 candidates (decision and constraint)
    assert len(candidates) >= 2

    # Verify tool_use content is NOT present
    all_content = " ".join(c["content"] for c in candidates)
    assert "read_file" not in all_content
    assert "bash" not in all_content

    # Verify text content IS present
    assert "Configuration stored" in all_content or any(
        "Configuration stored" in c["content"] for c in candidates
    )
    assert "validated at startup" in all_content or any(
        "validated at startup" in c["content"] for c in candidates
    )


# ============================================================================
# Phase 2 Tests: Provenance (MEX-2.1)
# ============================================================================


def test_provenance_includes_git_branch(seeded_db_path):
    """Git branch from JSONL message should appear in candidate provenance."""
    messages = [
        {
            "type": "human",
            "content": "Decision: Use feature flags for gradual rollouts.",
            "uuid": "msg-branch-test",
            "timestamp": "2024-01-10T00:00:00Z",
            "gitBranch": "feat/rollout-system",
        }
    ]

    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    assert len(candidates) >= 1
    prov = candidates[0]["provenance"]
    assert prov["git_branch"] == "feat/rollout-system"


def test_provenance_git_branch_missing_graceful(seeded_db_path):
    """Missing gitBranch field should result in empty string, not error."""
    messages = [
        {
            "type": "human",
            "content": "Decision: Use connection pooling for database access.",
            "uuid": "msg-no-branch",
            "timestamp": "2024-01-10T00:00:00Z",
            # gitBranch field intentionally omitted
        }
    ]

    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    assert len(candidates) >= 1
    prov = candidates[0]["provenance"]
    assert "git_branch" in prov
    assert prov["git_branch"] == ""


def test_provenance_all_fields_present(seeded_db_path):
    """Verify complete provenance structure has all expected fields."""
    messages = [
        {
            "type": "assistant",
            "content": "Constraint: Rate limit is 100 requests per minute.",
            "uuid": "msg-complete",
            "timestamp": "2024-01-10T12:00:00Z",
            "sessionId": "sess-complete-test",
            "gitBranch": "main",
        }
    ]

    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.0,
        run_id="run-abc",
        session_id="sess-complete-test",
        commit_sha="abc123def",
    )

    assert len(candidates) >= 1
    prov = candidates[0]["provenance"]

    # Base fields
    assert prov["source"] == "memory_extraction"
    assert prov["run_id"] == "run-abc"
    assert prov["session_id"] == "sess-complete-test"
    assert prov["commit_sha"] == "abc123def"
    assert prov["workflow_stage"] == "extraction"

    # JSONL-specific fields
    assert prov["message_uuid"] == "msg-complete"
    assert prov["message_role"] == "assistant"
    assert prov["timestamp"] == "2024-01-10T12:00:00Z"
    assert prov["git_branch"] == "main"
    assert prov["format"] == "jsonl"


# ============================================================================
# Phase 2 Tests: Scoring (MEX-2.2)
# ============================================================================


def test_score_learning_signal_boost(seeded_db_path):
    """Lines with learning indicators should score higher than generic lines."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    learning_line = "I learned that async handlers improve throughput by 40%."
    generic_line = "Async handlers improve throughput by 40%."

    learning_score = service._score(learning_line, "learning", "balanced")
    generic_score = service._score(generic_line, "learning", "balanced")

    assert learning_score > generic_score
    # Learning boost is +0.05
    assert abs(learning_score - generic_score - 0.05) < 0.01


def test_score_specificity_signal_boost(seeded_db_path):
    """Lines with file paths/function names should score higher."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    specific_line = "Gotcha: config.py:42 validate_settings() throws on missing keys."
    generic_line = "Gotcha: validation throws on missing configuration keys."

    specific_score = service._score(specific_line, "gotcha", "balanced")
    generic_score = service._score(generic_line, "gotcha", "balanced")

    assert specific_score > generic_score
    # Specificity boost is +0.03
    assert abs(specific_score - generic_score - 0.03) < 0.01


def test_score_question_penalty(seeded_db_path):
    """Lines ending with '?' should score lower than assertions."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    question_line = "Should we use Redis for caching API responses?"
    assertion_line = "We should use Redis for caching API responses."

    question_score = service._score(question_line, "decision", "balanced")
    assertion_score = service._score(assertion_line, "decision", "balanced")

    assert question_score < assertion_score
    # Question penalty is -0.03
    assert abs(assertion_score - question_score - 0.03) < 0.01


def test_score_vague_language_penalty(seeded_db_path):
    """Lines with vague words should score lower than definitive versions."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    vague_line = "We might need to use connection pooling maybe for performance."
    definitive_line = "We need to use connection pooling for performance."

    vague_score = service._score(vague_line, "constraint", "balanced")
    definitive_score = service._score(definitive_line, "constraint", "balanced")

    assert vague_score < definitive_score
    # Vague penalty is -0.04
    assert abs(definitive_score - vague_score - 0.04) < 0.01


def test_score_combined_signals(seeded_db_path):
    """Lines with multiple signals should stack bonuses."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    # Has learning signal (+0.05) + specificity (+0.03 for path and function)
    combined_line = "I learned that cache.py:get_or_set() reduces DB queries by 60%."
    baseline_line = "Cache reduces database queries by sixty percent."

    combined_score = service._score(combined_line, "learning", "balanced")
    baseline_score = service._score(baseline_line, "learning", "balanced")

    assert combined_score > baseline_score
    # Combined boost should be at least +0.05 (learning) + 0.03 (specificity) = +0.08
    assert (combined_score - baseline_score) >= 0.07


def test_score_distinct_values(seeded_db_path):
    """Diverse lines should produce varied scores (>=8 distinct values)."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    test_lines = [
        # Learning + specificity + numbers (very high)
        "I learned that api.py:rate_limit() allows 100 req/min for authenticated users.",
        # Decision + specificity + numbers (high)
        "Decision: Use PostgreSQL 14+ for advanced indexing features with p95 < 50ms.",
        # Constraint + specificity (medium-high)
        "Constraint: config.toml must define timeout_ms setting properly.",
        # Generic decision with vague word (lower)
        "Decision: Maybe use Redis for session storage.",
        # Learning only (medium)
        "I discovered that connection pooling reduces database latency significantly.",
        # Gotcha without specificity (medium-low)
        "Gotcha: Beware of timezone issues in datetime parsing operations.",
        # Question without learning (low due to penalty)
        "Should we use async handlers for API endpoints?",
        # Vague language stacked penalties (very low)
        "Maybe we could probably use caching somehow for performance.",
        # Learning + question (mixed)
        "I learned that caching helps, but should we use Redis for this?",
        # Very short generic (lowest)
        "Use environment variables.",
        # Constraint without specificity
        "Constraint: All async functions must have timeouts configured.",
        # Style rule (unique category)
        "Style rule: prefer explicit type hints for public APIs.",
    ]

    scores = [
        service._score(line, service._classify_type(line), "balanced")
        for line in test_lines
    ]
    distinct_scores = len(set(scores))

    # Must have at least 8 distinct score values
    assert (
        distinct_scores >= 8
    ), f"Only {distinct_scores} distinct scores: {sorted(set(scores))}"


# ============================================================================
# Phase 2 Tests: Backward Compatibility (MEX-2.3)
# ============================================================================


def test_plaintext_fallback_format_field(seeded_db_path):
    """Plain text input should produce candidates with format='plain_text'."""
    corpus = """
    Decision: Use async/await for I/O-bound operations.
    Constraint: All async functions must have timeouts.
    """

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    assert len(candidates) >= 2
    for candidate in candidates:
        assert candidate["provenance"]["format"] == "plain_text"


def test_jsonl_format_field(seeded_db_path):
    """Valid JSONL input should produce candidates with format='jsonl'."""
    messages = [
        {
            "type": "human",
            "content": "Decision: Use structured logging for production.",
            "uuid": "msg-format-test",
            "timestamp": "2024-01-15T00:00:00Z",
        }
    ]

    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    assert len(candidates) >= 1
    for candidate in candidates:
        assert candidate["provenance"]["format"] == "jsonl"


def test_invalid_json_fallback(seeded_db_path):
    """Input with invalid JSON lines should fall back to plain-text mode."""
    corpus = """
    {invalid json}
    {"partial": json without closing brace
    Decision: Use message queues for async processing.
    Constraint: Queue depth must not exceed 10000 messages.
    """

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    # Should extract candidates using plain-text fallback
    assert len(candidates) >= 2

    # All should have plain_text format
    for candidate in candidates:
        assert candidate["provenance"]["format"] == "plain_text"

    # Verify actual content was extracted
    all_content = " ".join(c["content"] for c in candidates)
    assert "message queues" in all_content or any(
        "message queues" in c["content"] for c in candidates
    )


# ============================================================================
# Phase 3 Tests: LLM Integration (MEX-3.5)
# ============================================================================


def test_preview_without_llm(seeded_db_path):
    """Default preview (no LLM) sets classification_method=heuristic."""
    service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)
    corpus = "Decision: Use Redis for distributed caching across services."

    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    assert len(candidates) >= 1
    for candidate in candidates:
        assert candidate["provenance"]["classification_method"] == "heuristic"
        assert "llm_reasoning" not in candidate["provenance"]
        assert "llm_provider" not in candidate["provenance"]


def test_preview_with_mock_llm(seeded_db_path):
    """Preview with mocked LLM overrides type and confidence."""
    from unittest.mock import MagicMock, patch
    from skillmeat.core.services.llm_classifier import ClassificationResult

    # Don't enable LLM in constructor - we'll mock _semantic_classify_batch directly
    service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

    # Return a high-confidence "gotcha" classification from the batch method
    llm_result_dict = {
        "type": "gotcha",
        "confidence": 0.95,
        "reasoning": "Identifies a specific pitfall with clear context",
    }

    # Mock the _semantic_classify_batch method to return our result
    with patch.object(service, "_semantic_classify_batch") as mock_batch:
        # Mock a classifier that's available
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_classifier.provider_name = "anthropic"
        mock_classifier.usage_stats = MagicMock()
        mock_classifier.usage_stats.summary.return_value = "1 calls, 1 candidates"

        service._classifier = mock_classifier
        mock_batch.return_value = [llm_result_dict]

        corpus = "Decision: Use connection pooling for database access."

        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 1
        candidate = candidates[0]

        # LLM should override heuristic values
        assert candidate["type"] == "gotcha"
        assert candidate["confidence"] == 0.95

        # LLM provenance should be present
        prov = candidate["provenance"]
        assert prov["classification_method"] == "llm"
        assert (
            prov["llm_reasoning"] == "Identifies a specific pitfall with clear context"
        )
        assert prov["llm_provider"] == "anthropic"


def test_preview_llm_failure_falls_back(seeded_db_path):
    """When LLM fails, candidates keep heuristic values."""
    from unittest.mock import MagicMock

    service = MemoryExtractorService(db_path=seeded_db_path, use_llm=True)

    # Mock the classifier to return None (failure)
    mock_classifier = MagicMock()
    mock_classifier.is_available.return_value = True
    mock_classifier.provider_name = "anthropic"
    mock_classifier.usage_stats = MagicMock()
    mock_classifier.usage_stats.summary.return_value = "0 calls"
    mock_classifier.classify_batch.return_value = [None]  # LLM failure

    service._classifier = mock_classifier

    corpus = "Constraint: API timeout must be under 5 seconds."

    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.0,
    )

    assert len(candidates) >= 1
    candidate = candidates[0]

    # Should keep heuristic classification
    assert candidate["type"] == "constraint"  # Heuristic would classify this
    assert candidate["provenance"]["classification_method"] == "heuristic"
    assert "llm_reasoning" not in candidate["provenance"]


def test_provenance_includes_llm_metadata(seeded_db_path):
    """Provenance includes llm_provider and llm_reasoning when LLM succeeds."""
    from unittest.mock import MagicMock, patch

    service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

    llm_result_dict = {
        "type": "learning",
        "confidence": 0.88,
        "reasoning": "General development insight about testing patterns",
    }

    with patch.object(service, "_semantic_classify_batch") as mock_batch:
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_classifier.provider_name = "openai"
        mock_classifier.usage_stats = MagicMock()
        mock_classifier.usage_stats.summary.return_value = "1 calls, 1 candidates"

        service._classifier = mock_classifier
        mock_batch.return_value = [llm_result_dict]

        corpus = "I learned that integration tests catch more bugs than unit tests."

        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 1
        prov = candidates[0]["provenance"]

        assert prov["classification_method"] == "llm"
        assert prov["llm_provider"] == "openai"
        assert (
            prov["llm_reasoning"]
            == "General development insight about testing patterns"
        )


def test_env_var_enables_llm(seeded_db_path, monkeypatch):
    """SKILLMEAT_LLM_ENABLED=true enables LLM."""
    from unittest.mock import MagicMock, patch

    # Set environment variable
    monkeypatch.setenv("SKILLMEAT_LLM_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Mock get_classifier at the module level where it's imported
    with patch(
        "skillmeat.core.services.llm_classifier.get_classifier"
    ) as mock_get_classifier:
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_get_classifier.return_value = mock_classifier

        # Create service without use_llm parameter
        service = MemoryExtractorService(db_path=seeded_db_path)

        # Should have created a classifier
        assert service._classifier is not None
        mock_get_classifier.assert_called_once()


def test_cli_flag_overrides_env(seeded_db_path, monkeypatch):
    """use_llm=True overrides SKILLMEAT_LLM_ENABLED=false."""
    from unittest.mock import MagicMock, patch

    # Set env to false
    monkeypatch.setenv("SKILLMEAT_LLM_ENABLED", "false")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Mock get_classifier
    with patch(
        "skillmeat.core.services.llm_classifier.get_classifier"
    ) as mock_get_classifier:
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_get_classifier.return_value = mock_classifier

        # Create service with use_llm=True (should override env)
        service = MemoryExtractorService(db_path=seeded_db_path, use_llm=True)

        # Should have created a classifier despite env=false
        assert service._classifier is not None
        mock_get_classifier.assert_called_once()


def test_llm_batch_classification(seeded_db_path):
    """Multiple candidates are classified in a single batch."""
    from unittest.mock import MagicMock, patch

    service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

    # Return 3 classifications
    llm_results = [
        {"type": "decision", "confidence": 0.90, "reasoning": "test1"},
        {"type": "constraint", "confidence": 0.85, "reasoning": "test2"},
        {"type": "gotcha", "confidence": 0.92, "reasoning": "test3"},
    ]

    with patch.object(service, "_semantic_classify_batch") as mock_batch:
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_classifier.provider_name = "anthropic"
        mock_classifier.usage_stats = MagicMock()
        mock_classifier.usage_stats.summary.return_value = "1 calls, 3 candidates"

        service._classifier = mock_classifier
        mock_batch.return_value = llm_results

        corpus = """
        Decision: Use PostgreSQL for production database.
        Constraint: Database connections must be pooled.
        Gotcha: Beware of N+1 query problems in ORM.
        """

        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        # Should classify all candidates in single batch
        assert mock_batch.call_count == 1

        # Verify LLM classifications were applied
        assert len(candidates) >= 3
        types = {c["type"] for c in candidates}
        assert "decision" in types or "constraint" in types or "gotcha" in types


def test_llm_partial_failure(seeded_db_path):
    """When LLM fails for some items, those fall back to heuristic."""
    from unittest.mock import MagicMock, patch

    service = MemoryExtractorService(db_path=seeded_db_path, use_llm=False)

    # Mock classifier to return mixed results (some success, some None)
    llm_results = [
        {"type": "learning", "confidence": 0.88, "reasoning": "test"},
        None,  # Second item failed
    ]

    with patch.object(service, "_semantic_classify_batch") as mock_batch:
        mock_classifier = MagicMock()
        mock_classifier.is_available.return_value = True
        mock_classifier.provider_name = "anthropic"
        mock_classifier.usage_stats = MagicMock()
        mock_classifier.usage_stats.summary.return_value = "1 calls, 2 candidates"

        service._classifier = mock_classifier
        mock_batch.return_value = llm_results

        corpus = """
        I learned that connection pooling improves performance significantly.
        Decision: Use async handlers for API endpoints.
        """

        candidates = service.preview(
            project_id=PROJECT_ID,
            text_corpus=corpus,
            profile="balanced",
            min_confidence=0.0,
        )

        assert len(candidates) >= 2

        # First should use LLM classification
        llm_classified = [
            c
            for c in candidates
            if c["provenance"].get("classification_method") == "llm"
        ]
        heuristic_classified = [
            c
            for c in candidates
            if c["provenance"].get("classification_method") == "heuristic"
        ]

        # Should have at least one of each
        assert len(llm_classified) >= 1
        assert len(heuristic_classified) >= 1


# ============================================================================
# Phase 4 Tests: Noise Filtering (Quality Improvements)
# ============================================================================


def test_is_noise_xml_tags():
    """XML/HTML tags should be detected as noise."""
    assert MemoryExtractorService._is_noise("<command-name>/clear</command-name>")
    assert MemoryExtractorService._is_noise("<command-args></command-args>")
    assert MemoryExtractorService._is_noise("<system-reminder>")
    assert MemoryExtractorService._is_noise("</system-reminder>")
    assert MemoryExtractorService._is_noise("<local-command-result>")
    assert MemoryExtractorService._is_noise("<invoke>")


def test_is_noise_table_syntax():
    """Table syntax patterns should be detected as noise."""
    assert MemoryExtractorService._is_noise("|-------|-----------|-----|")
    assert MemoryExtractorService._is_noise("| **Header** | **Description** |")
    assert MemoryExtractorService._is_noise("| Issue | Root Cause | Fix |")


def test_is_noise_action_phrases():
    """Conversational action phrases should be detected as noise."""
    assert MemoryExtractorService._is_noise("Let me check the configuration files")
    assert MemoryExtractorService._is_noise("I'll start by reading the schema")
    assert MemoryExtractorService._is_noise("Now let me verify the test results")
    assert MemoryExtractorService._is_noise("Hmm, the diff is empty")
    assert MemoryExtractorService._is_noise("Good. Now I understand the pattern")


def test_is_noise_not_triggered_on_valid_content():
    """Valid learning content should NOT be detected as noise."""
    assert not MemoryExtractorService._is_noise(
        "Learned that uv resolves dependencies faster than pip"
    )
    assert not MemoryExtractorService._is_noise(
        "Decision: Use SQLAlchemy for database operations"
    )
    assert not MemoryExtractorService._is_noise(
        "Constraint: API timeout must be under 5 seconds"
    )
    assert not MemoryExtractorService._is_noise(
        "Gotcha: Beware of N+1 query problems in ORM"
    )


def test_score_noise_penalty(seeded_db_path):
    """Lines matching noise patterns should receive severe penalty."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    # Noise content should score very low
    noise_score = service._score(
        "Let me check the configuration files", "learning", "balanced"
    )
    valid_score = service._score(
        "Configuration files must use TOML format", "constraint", "balanced"
    )

    # Noise should be penalized significantly
    assert noise_score < valid_score
    assert noise_score < 0.6  # Should be below typical min_confidence


def test_score_filler_penalty(seeded_db_path):
    """Conversational filler should receive penalty."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    filler_score = service._score(
        "Here's what I found in the codebase today", "learning", "balanced"
    )
    direct_score = service._score(
        "The codebase uses dependency injection pattern", "learning", "balanced"
    )

    assert filler_score < direct_score


def test_score_structural_content_penalty(seeded_db_path):
    """Lines with high non-alphanumeric ratio should be penalized."""
    service = MemoryExtractorService(db_path=seeded_db_path)

    # Line with lots of punctuation
    structural_score = service._score(
        "------- ******* ======= -------", "learning", "balanced"
    )
    # Normal prose
    prose_score = service._score(
        "Use dependency injection for testability", "decision", "balanced"
    )

    assert structural_score < prose_score


def test_preview_filters_noise_early(seeded_db_path):
    """Preview should filter noise patterns before scoring."""
    messages = [
        {
            "type": "assistant",
            "content": """<command-name>/clear</command-name>
            | Issue | Root Cause | Fix |
            |-------|-----------|-----|
            Let me check the configuration files
            Decision: Use SQLAlchemy for database operations.
            Hmm, the diff seems empty
            Gotcha: Beware of connection pooling timeouts.
            """,
            "uuid": "msg-noise-test",
            "timestamp": "2024-01-01T00:00:00Z",
        }
    ]

    jsonl_corpus = "\n".join(json.dumps(msg) for msg in messages)

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=jsonl_corpus,
        profile="balanced",
        min_confidence=0.5,  # Lower threshold to see what passes
    )

    # Extract all content for verification
    all_content = " ".join(c["content"] for c in candidates)

    # Noise should be filtered out
    assert "<command-name>" not in all_content
    assert "|-------|" not in all_content
    assert "Let me check" not in all_content
    assert "Hmm, the diff" not in all_content

    # Valid content should remain
    assert any("SQLAlchemy" in c["content"] for c in candidates) or any(
        "connection pooling" in c["content"] for c in candidates
    )


def test_preview_plaintext_filters_noise(seeded_db_path):
    """Plain-text fallback path should also filter noise."""
    corpus = """
    <command-name>/clear</command-name>
    Let me check the configuration
    Decision: Use Redis for caching operations.
    | Column1 | Column2 | Column3 |
    Gotcha: Beware of cache invalidation bugs.
    """

    service = MemoryExtractorService(db_path=seeded_db_path)
    candidates = service.preview(
        project_id=PROJECT_ID,
        text_corpus=corpus,
        profile="balanced",
        min_confidence=0.5,
    )

    all_content = " ".join(c["content"] for c in candidates)

    # Noise should be filtered
    assert "<command-name>" not in all_content
    assert "Let me check" not in all_content
    assert "| Column1 |" not in all_content

    # Valid content should remain
    assert any("Redis" in c["content"] for c in candidates) or any(
        "cache invalidation" in c["content"] for c in candidates
    )
