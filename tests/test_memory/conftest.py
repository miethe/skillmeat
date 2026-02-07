"""Shared fixtures for Memory & Context Intelligence System tests.

Provides test fixtures for:
- In-memory SQLAlchemy database sessions
- Sample MemoryItem creation data (factory fixture)
- Sample ContextModule creation data (factory fixture)
- Temporary project directories with .claude structure
- Pre-seeded database states for integration testing

These fixtures follow the existing patterns from tests/e2e/conftest.py
and tests/integration/conftest.py.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from skillmeat.cache.models import Base


# =============================================================================
# Database Fixtures
# =============================================================================


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key enforcement for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture
def db_engine(tmp_path: Path):
    """Create a SQLAlchemy engine backed by a temporary SQLite database.

    Creates all tables defined in the ORM Base metadata, including any
    memory-related tables once they are added to the models.

    Returns:
        SQLAlchemy Engine instance

    Example:
        def test_something(db_engine):
            Session = sessionmaker(bind=db_engine)
            session = Session()
    """
    db_path = tmp_path / "test_memory.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
    )

    # Create all tables from ORM metadata
    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a scoped SQLAlchemy session with automatic rollback.

    Each test gets a fresh session that rolls back on teardown,
    ensuring test isolation without needing to recreate tables.

    Returns:
        SQLAlchemy Session instance

    Example:
        def test_create_item(db_session):
            item = MemoryItem(**data)
            db_session.add(item)
            db_session.commit()
            assert item.id is not None
    """
    SessionFactory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )
    session = SessionFactory()

    yield session

    session.rollback()
    session.close()


# =============================================================================
# Project Fixtures
# =============================================================================


@pytest.fixture
def sample_project_id() -> str:
    """Return a deterministic project ID for testing.

    Returns:
        String project ID

    Example:
        def test_something(sample_project_id):
            assert sample_project_id == "proj-test-memory-project"
    """
    return "proj-test-memory-project"


@pytest.fixture
def sample_project_path(tmp_path: Path) -> Path:
    """Create a temporary project directory with .claude structure.

    Returns:
        Path to temporary project directory

    Example:
        def test_something(sample_project_path):
            assert (sample_project_path / ".claude").exists()
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create .claude directory structure
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir()
    (claude_dir / "skills").mkdir()
    (claude_dir / "commands").mkdir()
    (claude_dir / "agents").mkdir()

    return project_dir


# =============================================================================
# Memory Item Data Fixtures (Factory Pattern)
# =============================================================================


def _generate_content_hash(content: str) -> str:
    """Generate SHA-256 content hash for deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@pytest.fixture
def memory_item_data() -> Callable[..., Dict[str, Any]]:
    """Factory fixture that returns sample MemoryItem creation data.

    Returns a callable that generates memory item dictionaries with
    sensible defaults. All fields can be overridden via keyword arguments.

    Returns:
        Callable that produces MemoryItem data dictionaries

    Example:
        def test_create_memory(memory_item_data):
            # Use defaults
            data = memory_item_data()
            assert data["type"] == "constraint"

            # Override specific fields
            data = memory_item_data(
                type="decision",
                content="Use PostgreSQL for production",
                confidence=0.95,
            )
            assert data["type"] == "decision"

            # Create multiple unique items
            items = [memory_item_data(content=f"Item {i}") for i in range(5)]
            assert len(set(d["content_hash"] for d in items)) == 5
    """
    _counter = [0]

    def _factory(
        project_id: str = "proj-test-memory-project",
        type: str = "constraint",
        content: Optional[str] = None,
        confidence: float = 0.75,
        status: str = "candidate",
        share_scope: str = "project",
        provenance: Optional[Dict[str, Any]] = None,
        anchors: Optional[List[str]] = None,
        ttl_policy: Optional[Dict[str, Any]] = None,
        **overrides: Any,
    ) -> Dict[str, Any]:
        _counter[0] += 1
        idx = _counter[0]

        if content is None:
            content = (
                f"Test memory item {idx}: API endpoint X always returns 422 "
                f"if field Y is omitted from the request body."
            )

        if provenance is None:
            provenance = {
                "source_type": "manual",
                "created_by": "test-user",
                "session_id": f"session-{idx:04d}",
                "commit_sha": None,
            }

        if anchors is None:
            anchors = [f"skillmeat/api/routers/test_router_{idx}.py"]

        if ttl_policy is None:
            ttl_policy = {
                "max_age_days": 30,
                "max_idle_days": 7,
            }

        content_hash = _generate_content_hash(content)

        data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "type": type,
            "content": content,
            "confidence": confidence,
            "status": status,
            "share_scope": share_scope,
            "provenance_json": provenance,
            "anchors_json": anchors,
            "ttl_policy_json": ttl_policy,
            "content_hash": content_hash,
        }
        data.update(overrides)
        return data

    return _factory


@pytest.fixture
def sample_memory_items(memory_item_data) -> List[Dict[str, Any]]:
    """Pre-built collection of memory items covering all types and statuses.

    Returns a list of 6 memory item dicts with varied types, statuses,
    and confidence scores for comprehensive test coverage.

    Returns:
        List of MemoryItem data dictionaries

    Example:
        def test_filter_by_type(sample_memory_items):
            constraints = [m for m in sample_memory_items if m["type"] == "constraint"]
            assert len(constraints) == 1
    """
    return [
        memory_item_data(
            type="constraint",
            content="API rate limit is 100 requests per minute per user.",
            confidence=0.90,
            status="stable",
        ),
        memory_item_data(
            type="decision",
            content="Use cursor-based pagination instead of offset for all list endpoints.",
            confidence=0.85,
            status="active",
        ),
        memory_item_data(
            type="gotcha",
            content="SQLAlchemy lazy loading triggers N+1 queries in list views. Use selectin.",
            confidence=0.80,
            status="active",
        ),
        memory_item_data(
            type="style_rule",
            content="All API responses must use DTO wrappers, never return ORM models directly.",
            confidence=0.95,
            status="stable",
        ),
        memory_item_data(
            type="learning",
            content="TF-IDF cosine similarity threshold of 0.85 works well for dedup.",
            confidence=0.60,
            status="candidate",
        ),
        memory_item_data(
            type="constraint",
            content="Deprecated endpoint /v1/old-sync still receives traffic. Do not remove yet.",
            confidence=0.40,
            status="deprecated",
            provenance={
                "source_type": "auto_extracted",
                "created_by": "memory-extractor",
                "session_id": "session-auto-001",
                "commit_sha": "abc123def456",
            },
        ),
    ]


# =============================================================================
# Context Module Data Fixtures (Factory Pattern)
# =============================================================================


@pytest.fixture
def context_module_data() -> Callable[..., Dict[str, Any]]:
    """Factory fixture that returns sample ContextModule creation data.

    Returns a callable that generates context module dictionaries with
    sensible defaults. All fields can be overridden via keyword arguments.

    Returns:
        Callable that produces ContextModule data dictionaries

    Example:
        def test_create_module(context_module_data):
            # Use defaults
            data = context_module_data()
            assert data["name"] == "Debug Mode"

            # Override specific fields
            data = context_module_data(
                name="Release Mode",
                description="Context for release preparation",
                priority=10,
            )
            assert data["priority"] == 10
    """
    _counter = [0]

    def _factory(
        project_id: str = "proj-test-memory-project",
        name: Optional[str] = None,
        description: Optional[str] = None,
        selectors: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        **overrides: Any,
    ) -> Dict[str, Any]:
        _counter[0] += 1
        idx = _counter[0]

        if name is None:
            names = [
                "Debug Mode",
                "Release Mode",
                "Research Mode",
                "Review Mode",
                "Onboarding Mode",
            ]
            name = names[(idx - 1) % len(names)]

        if description is None:
            description = f"Context module '{name}' for testing (#{idx})."

        if selectors is None:
            selectors = {
                "memory_types": ["constraint", "gotcha"],
                "min_confidence": 0.7,
                "file_patterns": ["skillmeat/api/**/*.py"],
                "workflow_stages": ["implementation"],
            }

        content_hash = _generate_content_hash(f"{name}:{project_id}:{idx}")

        data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "name": name,
            "description": description,
            "selectors_json": selectors,
            "priority": priority,
            "content_hash": content_hash,
        }
        data.update(overrides)
        return data

    return _factory


@pytest.fixture
def sample_context_modules(context_module_data) -> List[Dict[str, Any]]:
    """Pre-built collection of context modules for testing.

    Returns a list of 3 context module dicts with varied selectors
    and priorities.

    Returns:
        List of ContextModule data dictionaries

    Example:
        def test_list_modules(sample_context_modules):
            assert len(sample_context_modules) == 3
            assert sample_context_modules[0]["name"] == "Debug Mode"
    """
    return [
        context_module_data(
            name="Debug Mode",
            description="Constraints and gotchas relevant during debugging sessions.",
            selectors={
                "memory_types": ["constraint", "gotcha"],
                "min_confidence": 0.6,
                "file_patterns": ["**/*.py"],
                "workflow_stages": ["debugging"],
            },
            priority=10,
        ),
        context_module_data(
            name="Release Mode",
            description="Decisions and style rules for release preparation.",
            selectors={
                "memory_types": ["decision", "style_rule"],
                "min_confidence": 0.8,
                "file_patterns": [],
                "workflow_stages": ["release", "review"],
            },
            priority=8,
        ),
        context_module_data(
            name="Research Mode",
            description="All learnings and low-confidence candidates for exploration.",
            selectors={
                "memory_types": ["learning"],
                "min_confidence": 0.3,
                "file_patterns": [],
                "workflow_stages": ["research", "exploration"],
            },
            priority=3,
        ),
    ]


# =============================================================================
# Module-Memory Association Data Fixture
# =============================================================================


@pytest.fixture
def module_memory_link_data() -> Callable[..., Dict[str, Any]]:
    """Factory fixture for module-memory association (many-to-many) data.

    Returns a callable that generates module_memory_items join table data.

    Returns:
        Callable that produces association data dictionaries

    Example:
        def test_link(module_memory_link_data):
            link = module_memory_link_data(
                module_id="mod-1",
                memory_id="mem-1",
                ordering=0,
            )
    """

    def _factory(
        module_id: str = "module-placeholder",
        memory_id: str = "memory-placeholder",
        ordering: int = 0,
        **overrides: Any,
    ) -> Dict[str, Any]:
        data = {
            "module_id": module_id,
            "memory_id": memory_id,
            "ordering": ordering,
        }
        data.update(overrides)
        return data

    return _factory


# =============================================================================
# Helper Constants
# =============================================================================

# Valid memory item types (from PRD FR-1)
MEMORY_TYPES = ["decision", "constraint", "gotcha", "style_rule", "learning"]

# Valid memory statuses (lifecycle state machine)
MEMORY_STATUSES = ["candidate", "active", "stable", "deprecated"]

# Valid status transitions (from PRD FR-5, FR-6)
VALID_TRANSITIONS = {
    "candidate": ["active", "deprecated"],
    "active": ["stable", "deprecated"],
    "stable": ["deprecated"],
    "deprecated": [],  # terminal state
}

# Export constants for use in tests
pytest.MEMORY_TYPES = MEMORY_TYPES
pytest.MEMORY_STATUSES = MEMORY_STATUSES
pytest.VALID_TRANSITIONS = VALID_TRANSITIONS
