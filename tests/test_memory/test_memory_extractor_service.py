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
    corpus = '{"role": "user", "content": "hello"}\n{"role": "assistant", "content": "hi"}'
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
    json_wrapped = json.dumps(inner_jsonl)  # Produces: '"{\\"role\\":\\"user\\"}\\n..."'

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
        {"type": "human", "content": "This content is long enough to be extracted properly."},
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
                {"type": "text", "text": "Constraint: Database connections must be pooled."},
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
                {"type": "text", "text": "Decision: Configuration stored in environment variables."},
                {"type": "tool_use", "name": "bash", "input": {"command": "ls"}},
                {"type": "text", "text": "Constraint: Environment variables must be validated at startup."},
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
