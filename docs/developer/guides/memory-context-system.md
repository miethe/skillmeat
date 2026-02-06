---
title: Memory & Context Intelligence System Developer Guide
description: Architecture, implementation patterns, and extension guide for the Memory & Context Intelligence System
audience: [developers, architects]
tags: [memory, context, intelligence, architecture, development, sqlite, api, testing]
created: 2026-02-06
updated: 2026-02-06
category: developer-guide
status: active
related:
  - /docs/user/guides/memory-context-system.md
  - /docs/feature-flags.md
  - /skillmeat/core/services/memory_service.py
  - /skillmeat/cache/memory_repositories.py
---

# Memory & Context Intelligence System Developer Guide

## Overview

The Memory & Context Intelligence System is a project-scoped knowledge management platform that captures agent learnings, manages lifecycle governance, and dynamically composes context for AI workflows. This guide covers the architecture, implementation patterns, and extension points for developers who need to maintain or extend the system.

**Key Capabilities:**
- **Memory Governance**: Project-scoped CRUD for capturing decisions, constraints, gotchas, style rules, and learnings
- **Lifecycle Management**: State machine with promote/deprecate operations and provenance tracking
- **Context Packing**: Token-budget-aware composition of memory items into injectable context
- **Module System**: Reusable selector-based groupings for different workflows

**Status**: Active (Phase 6 complete)

---

## Architecture Overview

### Layered Architecture

The system follows a strict layered architecture pattern:

```
┌─────────────────────────────────────────────────────────┐
│  API Layer (FastAPI)                                    │
│  - Routers: memory_items.py, context_modules.py        │
│  - Schemas: memory.py (Pydantic models)                 │
│  - Dependencies: Feature flag enforcement               │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  Service Layer (Business Logic)                         │
│  - MemoryService: CRUD, lifecycle, merge                │
│  - ContextModuleService: Module management              │
│  - ContextPackerService: Token-aware composition        │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  Repository Layer (Data Access)                         │
│  - MemoryItemRepository: ORM abstraction                │
│  - ContextModuleRepository: Module data access          │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  ORM Layer (SQLAlchemy Models)                          │
│  - MemoryItem: Memory item entity                       │
│  - ContextModule: Module entity                         │
│  - ModuleMemoryItem: Join table for many-to-many        │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  Database Layer (SQLite)                                │
│  - Tables: memory_items, context_modules               │
│  - Migrations: Alembic version control                  │
└─────────────────────────────────────────────────────────┘
```

**Layer Responsibilities:**

| Layer | Responsibility | Files |
|-------|----------------|-------|
| **API** | HTTP surface, request validation, response formatting | `skillmeat/api/routers/memory_items.py` |
| **Service** | Business logic, validation, lifecycle rules, DTO conversion | `skillmeat/core/services/memory_service.py` |
| **Repository** | Data access, query building, cursor pagination | `skillmeat/cache/memory_repositories.py` |
| **ORM** | Schema definition, relationships, constraints | `skillmeat/cache/models.py` |
| **Database** | Persistence, indexes, CHECK constraints | SQLite with Alembic migrations |

**Key Principle**: Business logic lives in the service layer. Repositories are thin data access abstractions. Routers delegate to services and handle HTTP concerns only.

---

## Database Schema

### Memory Items Table

```sql
CREATE TABLE memory_items (
    id TEXT PRIMARY KEY,                    -- UUID hex string
    project_id TEXT NOT NULL,               -- FK to projects.id
    type TEXT NOT NULL                      -- CHECK: decision, constraint, gotcha, style_rule, learning
        CHECK (type IN ('decision', 'constraint', 'gotcha', 'style_rule', 'learning')),
    content TEXT NOT NULL,                  -- The memory content
    confidence REAL NOT NULL DEFAULT 0.75   -- 0.0 to 1.0
        CHECK (confidence BETWEEN 0.0 AND 1.0),
    status TEXT NOT NULL DEFAULT 'candidate' -- CHECK: candidate, active, stable, deprecated
        CHECK (status IN ('candidate', 'active', 'stable', 'deprecated')),
    provenance_json TEXT,                   -- JSON: {source, session_id, commit_sha, transitions[]}
    anchors_json TEXT,                      -- JSON array of file paths
    ttl_policy_json TEXT,                   -- JSON: {max_age_days, max_idle_days}
    content_hash TEXT NOT NULL UNIQUE,      -- SHA-256 for deduplication
    access_count INTEGER DEFAULT 0,         -- Usage tracking
    created_at TEXT NOT NULL,               -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,               -- ISO 8601 timestamp
    deprecated_at TEXT,                     -- ISO 8601 timestamp when deprecated

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX idx_memory_items_project_status ON memory_items(project_id, status);
CREATE INDEX idx_memory_items_project_type ON memory_items(project_id, type);
CREATE INDEX idx_memory_items_created_at ON memory_items(created_at DESC);
```

### Context Modules Table

```sql
CREATE TABLE context_modules (
    id TEXT PRIMARY KEY,                    -- UUID hex string
    project_id TEXT NOT NULL,               -- FK to projects.id
    name TEXT NOT NULL,                     -- Human-readable name
    description TEXT,                       -- Optional description
    selectors_json TEXT,                    -- JSON: {memory_types[], min_confidence, file_patterns[], workflow_stages[]}
    priority INTEGER DEFAULT 5,             -- Ordering priority
    content_hash TEXT,                      -- Hash of assembled content
    created_at TEXT NOT NULL,               -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,               -- ISO 8601 timestamp

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_context_modules_project ON context_modules(project_id);
```

### Module-Memory Join Table

```sql
CREATE TABLE module_memory_items (
    module_id TEXT NOT NULL,               -- FK to context_modules.id
    memory_id TEXT NOT NULL,               -- FK to memory_items.id
    ordering INTEGER DEFAULT 0,            -- Display order within module

    PRIMARY KEY (module_id, memory_id),
    FOREIGN KEY (module_id) REFERENCES context_modules(id) ON DELETE CASCADE,
    FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
);
```

**Schema Design Decisions:**

1. **TEXT primary keys**: UUID hex strings for stable, portable IDs across systems
2. **JSON columns**: Flexible structured data without rigid schema changes (provenance, selectors, TTL policies)
3. **content_hash UNIQUE**: SHA-256 deduplication prevents exact duplicate content
4. **CHECK constraints**: Enforce valid types and statuses at the database level
5. **Cascade deletes**: Module/memory associations are automatically cleaned up

---

## Service Layer

### MemoryService

**File**: `skillmeat/core/services/memory_service.py`

The MemoryService handles all memory item business logic. It validates inputs, enforces lifecycle rules, tracks provenance, and converts between ORM models and plain dicts.

**Core Methods:**

```python
from skillmeat.core.services.memory_service import MemoryService

service = MemoryService(db_path="/path/to/db.sqlite")

# CRUD Operations
item = service.create(
    project_id="proj-123",
    type="decision",
    content="Use SQLAlchemy for ORM layer",
    confidence=0.9,
    status="candidate",
    provenance={"source": "manual", "creator": "user-456"},
    anchors=["skillmeat/cache/models.py"],
    ttl_policy={"max_age_days": 365, "max_idle_days": 90}
)

item = service.get(item_id="mem-789")  # Increments access_count
result = service.list_items(
    project_id="proj-123",
    status="active",
    type="decision",
    min_confidence=0.8,
    limit=50,
    sort_by="confidence",
    sort_order="desc"
)
updated = service.update(item_id="mem-789", confidence=0.95, status="active")
deleted = service.delete(item_id="mem-789")  # Returns bool

# Lifecycle Management
promoted = service.promote(
    item_id="mem-789",
    reason="Validated in production for 30 days"
)  # candidate → active → stable

deprecated = service.deprecate(
    item_id="mem-789",
    reason="Superseded by mem-890"
)  # Any status → deprecated

bulk_result = service.bulk_promote(
    item_ids=["mem-1", "mem-2", "mem-3"],
    reason="Batch approval after review"
)  # {promoted: [...], failed: [{id, error}, ...]}

# Merge Operations
merged = service.merge(
    source_id="mem-old",
    target_id="mem-new",
    strategy="keep_target",  # or "keep_source" or "combine"
    merged_content="Combined content"  # Required for "combine" strategy
)
```

**Validation Rules:**

| Field | Validation |
|-------|------------|
| `project_id` | Non-empty string |
| `type` | One of: `decision`, `constraint`, `gotcha`, `style_rule`, `learning` |
| `confidence` | Float between 0.0 and 1.0 |
| `status` | One of: `candidate`, `active`, `stable`, `deprecated` |
| `content` | Non-empty (enforced at schema layer with max 10,000 chars) |

**Lifecycle State Machine:**

```
candidate ──promote──> active ──promote──> stable
    │                     │                   │
    └──────deprecate──────┴──────deprecate───┘
```

**Provenance Tracking:**

```python
# Provenance structure (stored as JSON)
{
    "source": "manual" | "auto_extract" | "import",
    "creator": "user-id",
    "session_id": "session-uuid",
    "commit_sha": "abc123",
    "transitions": [
        {
            "from": "candidate",
            "to": "active",
            "reason": "Validated in production",
            "timestamp": "2026-02-05T10:30:00Z"
        }
    ]
}
```

**Duplicate Detection:**

When creating a memory item, the service computes a SHA-256 hash of the content. If a duplicate hash exists, the service returns:

```python
{
    "duplicate": True,
    "item": {existing_item_dict}
}
```

This prevents identical content from being stored multiple times.

---

### ContextModuleService

**File**: `skillmeat/core/services/context_module_service.py`

Manages context modules — named groupings of memory items with selector criteria.

**Core Methods:**

```python
from skillmeat.core.services.context_module_service import ContextModuleService

service = ContextModuleService(db_path="/path/to/db.sqlite")

# CRUD Operations
module = service.create(
    project_id="proj-123",
    name="API Design Decisions",
    description="Key decisions for REST API layer",
    selectors={
        "memory_types": ["decision", "constraint"],
        "min_confidence": 0.8,
        "file_patterns": ["skillmeat/api/**"],
        "workflow_stages": ["design", "implementation"]
    },
    priority=3
)

module = service.get(module_id="mod-456", include_items=True)
result = service.list_by_project(project_id="proj-123", limit=50)
updated = service.update(module_id="mod-456", priority=1)
deleted = service.delete(module_id="mod-456")

# Memory Association
result = service.add_memory(
    module_id="mod-456",
    memory_id="mem-789",
    ordering=1
)  # Returns {already_linked: bool, ...}

removed = service.remove_memory(module_id="mod-456", memory_id="mem-789")
memories = service.get_memories(module_id="mod-456", limit=100)
```

**Selector Structure:**

Selectors define filtering criteria for memory items:

```python
{
    "memory_types": ["decision", "constraint"],  # Filter by type
    "min_confidence": 0.8,                       # Minimum confidence threshold
    "file_patterns": ["skillmeat/api/**"],       # Glob patterns for anchor filtering
    "workflow_stages": ["design", "review"]      # Workflow stage filtering (future)
}
```

**Selector Validation:**

- `memory_types`: List of valid memory types
- `min_confidence`: Float between 0.0 and 1.0
- `file_patterns`: List of strings (glob patterns)
- `workflow_stages`: List of strings

Invalid keys or values raise `ValueError` at creation/update time.

---

### ContextPackerService

**File**: `skillmeat/core/services/context_packer_service.py`

Composes memory items into token-budget-aware context packs for injection into agent prompts.

**Core Methods:**

```python
from skillmeat.core.services.context_packer_service import ContextPackerService

service = ContextPackerService(db_path="/path/to/db.sqlite")

# Preview (read-only, no markdown generation)
preview = service.preview_pack(
    project_id="proj-123",
    module_id="mod-456",  # Optional
    budget_tokens=4000,
    filters={"type": "decision", "min_confidence": 0.8}
)
# Returns: {items: [...], total_tokens, budget_tokens, utilization, items_included, items_available}

# Generate (full pack with markdown)
pack = service.generate_pack(
    project_id="proj-123",
    module_id="mod-456",
    budget_tokens=4000,
    filters={"type": "decision"}
)
# Returns: {items: [...], markdown: "...", generated_at: "2026-02-06T...", ...}
```

**Token Estimation:**

Uses a simple character-based heuristic: `tokens ≈ len(text) / 4`

This provides reasonable accuracy without requiring a tokenizer dependency.

**Selection Algorithm:**

1. Fetch candidates (active/stable only) filtered by module selectors + additional filters
2. Sort by confidence (DESC) then created_at (DESC)
3. Iteratively add items until budget exhausted
4. Return selected items + stats

**Markdown Generation:**

Grouped by type with confidence annotations:

```markdown
# Context Pack

## Decisions
- Use SQLAlchemy for ORM layer
- [medium confidence] Prefer cursor-based pagination over offset

## Constraints
- API endpoints must return 503 when feature flag disabled
- [low confidence] Rate limit: 100 req/min per user

## Gotchas
- SQLite does not support ALTER COLUMN
```

**Confidence Labels:**

| Confidence | Label |
|------------|-------|
| ≥ 0.85 | (no label) |
| 0.60 - 0.84 | `[medium confidence]` |
| < 0.60 | `[low confidence]` |

---

## API Endpoints

### Memory Items Router

**File**: `skillmeat/api/routers/memory_items.py`

**Base Path**: `/api/v1/memory-items`

**Feature Flag**: `SKILLMEAT_MEMORY_CONTEXT_ENABLED` (default: `true`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List memory items with filters and cursor pagination |
| `POST` | `/` | Create a new memory item (with duplicate detection) |
| `GET` | `/count` | Count memory items with filters |
| `GET` | `/{id}` | Get a memory item by ID |
| `PUT` | `/{id}` | Update a memory item |
| `DELETE` | `/{id}` | Delete a memory item |
| `POST` | `/{id}/promote` | Promote to next lifecycle stage |
| `POST` | `/{id}/deprecate` | Deprecate a memory item |
| `POST` | `/bulk-promote` | Promote multiple items |
| `POST` | `/bulk-deprecate` | Deprecate multiple items |
| `POST` | `/merge` | Merge two memory items |

**Example: Create Memory Item**

```bash
curl -X POST http://localhost:8080/api/v1/memory-items?project_id=proj-123 \
  -H "Content-Type: application/json" \
  -d '{
    "type": "decision",
    "content": "Use SQLAlchemy for ORM layer",
    "confidence": 0.9,
    "status": "candidate",
    "provenance": {"source": "manual", "creator": "user-456"},
    "anchors": ["skillmeat/cache/models.py"]
  }'
```

**Response:**

```json
{
  "id": "mem-789abc",
  "project_id": "proj-123",
  "type": "decision",
  "content": "Use SQLAlchemy for ORM layer",
  "confidence": 0.9,
  "status": "candidate",
  "provenance": {"source": "manual", "creator": "user-456"},
  "anchors": ["skillmeat/cache/models.py"],
  "content_hash": "a1b2c3...",
  "access_count": 0,
  "created_at": "2026-02-06T10:30:00Z",
  "updated_at": "2026-02-06T10:30:00Z",
  "deprecated_at": null
}
```

---

## Adding New Memory Types

To add a new memory type (e.g., `performance_note`), follow these steps:

### Step 1: Update Database Constraint

**File**: Create a new Alembic migration

```bash
cd skillmeat/cache
alembic revision -m "add_performance_note_memory_type"
```

**Migration file** (`skillmeat/cache/migrations/versions/YYYYMMDD_HHMM_add_performance_note_memory_type.py`):

```python
"""Add performance_note memory type

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2026-02-06 10:00:00.000000
"""

from alembic import op

revision = 'abc123def456'
down_revision = 'previous_revision_id'

def upgrade():
    # Recreate CHECK constraint with new type
    with op.batch_alter_table('memory_items') as batch_op:
        batch_op.drop_constraint('ck_memory_items_type', type_='check')
        batch_op.create_check_constraint(
            'ck_memory_items_type',
            "type IN ('decision', 'constraint', 'gotcha', 'style_rule', 'learning', 'performance_note')"
        )

def downgrade():
    # Revert to original constraint
    with op.batch_alter_table('memory_items') as batch_op:
        batch_op.drop_constraint('ck_memory_items_type', type_='check')
        batch_op.create_check_constraint(
            'ck_memory_items_type',
            "type IN ('decision', 'constraint', 'gotcha', 'style_rule', 'learning')"
        )
```

### Step 2: Update Service Layer Constants

**File**: `skillmeat/core/services/memory_service.py`

```python
# Valid values for type and status fields, matching DB CHECK constraints
VALID_TYPES = {"decision", "constraint", "gotcha", "style_rule", "learning", "performance_note"}
```

**File**: `skillmeat/core/services/context_module_service.py`

```python
# Valid memory types (mirrors ck_memory_items_type constraint)
_VALID_MEMORY_TYPES = frozenset(
    {"decision", "constraint", "gotcha", "style_rule", "learning", "performance_note"}
)
```

### Step 3: Update API Schema

**File**: `skillmeat/api/schemas/memory.py`

```python
class MemoryType(str, Enum):
    """Allowed memory item types matching DB CHECK constraint."""

    DECISION = "decision"
    CONSTRAINT = "constraint"
    GOTCHA = "gotcha"
    STYLE_RULE = "style_rule"
    LEARNING = "learning"
    PERFORMANCE_NOTE = "performance_note"  # NEW
```

### Step 4: Update Context Packer Display Order

**File**: `skillmeat/core/services/context_packer_service.py`

```python
# Display order for memory type sections in generated markdown
_TYPE_DISPLAY_ORDER = [
    "decision",
    "constraint",
    "gotcha",
    "style_rule",
    "learning",
    "performance_note",  # NEW
]

# Human-readable section headings for each memory type
_TYPE_HEADINGS: Dict[str, str] = {
    "decision": "Decisions",
    "constraint": "Constraints",
    "gotcha": "Gotchas",
    "style_rule": "Style Rules",
    "learning": "Learnings",
    "performance_note": "Performance Notes",  # NEW
}
```

### Step 5: Apply Migration

```bash
cd skillmeat/cache
alembic upgrade head
```

### Step 6: Test

```bash
pytest skillmeat/api/tests/test_memory_services.py -v
pytest skillmeat/api/tests/test_e2e_memory_workflow.py -v
```

---

## Adding New Selectors

To add a new selector type (e.g., `author_filter` to filter by creator), follow these steps:

### Step 1: Update Selector Constants

**File**: `skillmeat/core/services/context_module_service.py`

```python
# Valid keys for the selectors dict
_VALID_SELECTOR_KEYS = frozenset(
    {"memory_types", "min_confidence", "file_patterns", "workflow_stages", "author_filter"}  # NEW
)
```

### Step 2: Add Validation Logic

**File**: `skillmeat/core/services/context_module_service.py`

In the `_validate_selectors` method, add validation for the new selector:

```python
@staticmethod
def _validate_selectors(selectors: Dict[str, Any]) -> None:
    """Validate the structure and values of a selectors dict."""
    # ... existing validation ...

    # Validate author_filter (NEW)
    if "author_filter" in selectors:
        authors = selectors["author_filter"]
        if not isinstance(authors, list):
            raise ValueError("selectors.author_filter must be a list")
        if not all(isinstance(a, str) for a in authors):
            raise ValueError("selectors.author_filter must contain only strings")
```

### Step 3: Implement Selector Application Logic

**File**: `skillmeat/core/services/context_packer_service.py`

Update `apply_module_selectors` to handle the new selector:

```python
def apply_module_selectors(
    self,
    project_id: str,
    selectors: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Apply module selector rules to filter memory items."""
    memory_types = selectors.get("memory_types")
    min_confidence = selectors.get("min_confidence")
    author_filter = selectors.get("author_filter")  # NEW

    items: List[Dict[str, Any]] = []

    # ... existing query logic ...

    # Apply author filter (NEW)
    if author_filter:
        items = [
            item for item in items
            if item.get("provenance", {}).get("creator") in author_filter
        ]

    return items
```

### Step 4: Update Tests

**File**: `skillmeat/api/tests/test_context_module_service.py`

```python
def test_author_filter_selector(module_svc, memory_svc, project_id):
    """Test author_filter selector."""
    # Create memories from different authors
    mem1 = memory_svc.create(
        project_id=project_id,
        type="decision",
        content="Decision by Alice",
        provenance={"creator": "alice"}
    )
    mem2 = memory_svc.create(
        project_id=project_id,
        type="decision",
        content="Decision by Bob",
        provenance={"creator": "bob"}
    )

    # Create module with author filter
    module = module_svc.create(
        project_id=project_id,
        name="Alice's Decisions",
        selectors={"author_filter": ["alice"]}
    )

    # Apply selectors
    from skillmeat.core.services.context_packer_service import ContextPackerService
    packer_svc = ContextPackerService(db_path=None)
    items = packer_svc.apply_module_selectors(project_id, module["selectors"])

    assert len(items) == 1
    assert items[0]["id"] == mem1["id"]
```

---

## Testing Patterns

### Unit Tests

**File**: `skillmeat/api/tests/test_memory_services.py`

Test individual service methods in isolation:

```python
import pytest
from skillmeat.core.services.memory_service import MemoryService

@pytest.fixture
def memory_svc():
    """Provide a MemoryService with a test database."""
    return MemoryService(db_path=":memory:")

@pytest.fixture
def project_id():
    """Provide a test project ID."""
    return "test-proj-123"

def test_create_memory_item(memory_svc, project_id):
    """Test creating a memory item."""
    item = memory_svc.create(
        project_id=project_id,
        type="decision",
        content="Use SQLAlchemy for ORM",
        confidence=0.9
    )

    assert item["id"] is not None
    assert item["project_id"] == project_id
    assert item["type"] == "decision"
    assert item["confidence"] == 0.9
    assert item["status"] == "candidate"

def test_duplicate_detection(memory_svc, project_id):
    """Test duplicate content detection."""
    content = "Use SQLAlchemy for ORM"

    item1 = memory_svc.create(
        project_id=project_id,
        type="decision",
        content=content
    )

    result = memory_svc.create(
        project_id=project_id,
        type="decision",
        content=content
    )

    assert result.get("duplicate") is True
    assert result["item"]["id"] == item1["id"]
```

### Integration Tests

**File**: `skillmeat/api/tests/test_e2e_memory_workflow.py`

Test complete workflows across multiple services:

```python
def test_full_memory_triage_pipeline(memory_svc, module_svc, packer_svc, project_id):
    """Test complete workflow: create → promote → pack → inject."""
    # Create candidate memories
    mem1 = memory_svc.create(
        project_id=project_id,
        type="decision",
        content="Use cursor-based pagination",
        confidence=0.7
    )

    # Promote to active
    promoted = memory_svc.promote(mem1["id"], reason="Validated in dev")
    assert promoted["status"] == "active"

    # Create module
    module = module_svc.create(
        project_id=project_id,
        name="API Module",
        selectors={"memory_types": ["decision"], "min_confidence": 0.6}
    )

    # Generate pack
    pack = packer_svc.generate_pack(
        project_id=project_id,
        module_id=module["id"],
        budget_tokens=2000
    )

    assert pack["items_included"] >= 1
    assert "Use cursor-based pagination" in pack["markdown"]
```

### Performance Benchmarks

**File**: `skillmeat/api/tests/test_performance_benchmarks.py`

Validate system performance under load:

```python
def test_large_pack_generation_performance(memory_svc, packer_svc, project_id):
    """Benchmark pack generation with 1000 memories."""
    import time

    # Create 1000 test memories
    for i in range(1000):
        memory_svc.create(
            project_id=project_id,
            type="learning",
            content=f"Learning item {i}",
            confidence=0.5,
            status="active"
        )

    # Measure generation time
    start = time.time()
    pack = packer_svc.generate_pack(project_id=project_id, budget_tokens=10000)
    elapsed = time.time() - start

    # Should complete in < 2 seconds
    assert elapsed < 2.0
    assert pack["items_included"] > 0
```

### Test Database Setup

All tests use in-memory SQLite databases (`db_path=":memory:"`) for fast, isolated execution. Fixtures create fresh database instances per test:

```python
@pytest.fixture
def memory_svc():
    return MemoryService(db_path=":memory:")
```

---

## Feature Flags

**File**: `docs/feature-flags.md`

The system uses feature flags for gradual rollout and testing.

### `MEMORY_CONTEXT_ENABLED`

**Environment Variable**: `SKILLMEAT_MEMORY_CONTEXT_ENABLED`
**Default**: `true`
**Type**: boolean

Controls whether the entire Memory & Context Intelligence System is available. When disabled, all memory-related endpoints return 503 (Service Unavailable).

**Usage:**

```bash
# Disable the feature
export SKILLMEAT_MEMORY_CONTEXT_ENABLED=false
skillmeat web dev

# All memory endpoints return 503
curl http://localhost:8080/api/v1/memory-items?project_id=test
# {"detail": "Memory & Context Intelligence System is disabled"}
```

**Implementation:**

```python
# File: skillmeat/api/dependencies.py
def require_memory_context_enabled(settings: APISettings = Depends(get_settings)):
    """Dependency that raises 503 if memory system is disabled."""
    if not settings.memory_context_enabled:
        raise HTTPException(
            status_code=503,
            detail="Memory & Context Intelligence System is disabled"
        )

# File: skillmeat/api/routers/memory_items.py
router = APIRouter(
    prefix="/memory-items",
    tags=["memory-items"],
    dependencies=[Depends(require_memory_context_enabled)],  # Applied to all routes
)
```

### Testing with Feature Flags

```python
import os
from unittest.mock import patch

def test_memory_disabled():
    """Test behavior when memory system is disabled."""
    with patch.dict(os.environ, {"SKILLMEAT_MEMORY_CONTEXT_ENABLED": "false"}):
        response = client.get("/api/v1/memory-items?project_id=test")
        assert response.status_code == 503
        assert "disabled" in response.json()["detail"]
```

---

## Observability

### Metrics

The system emits structured logs and spans for all operations.

**Key Metrics:**

| Metric | Description | Usage |
|--------|-------------|-------|
| `memory.create` | Memory item creation | Track duplicate rate, type distribution |
| `memory.update` | Memory item updates | Monitor lifecycle transitions |
| `memory.promote` | Promotions | Track promotion success rate |
| `memory.deprecate` | Deprecations | Monitor memory turnover |
| `memory.merge` | Merge operations | Track deduplication patterns |
| `context_pack.preview` | Pack previews | Monitor token utilization |
| `context_pack.generate` | Pack generation | Track generation time, item count |

### Tracing

**File**: `skillmeat/observability/tracing.py`

All service methods are instrumented with `trace_operation` context managers:

```python
from skillmeat.observability.tracing import trace_operation

def create(self, project_id: str, type: str, content: str, **kwargs) -> Dict[str, Any]:
    """Create a new memory item with validation."""
    with trace_operation(
        "memory.create",
        project_id=project_id,
        memory_type=type,
        confidence=kwargs.get("confidence", 0.5),
    ) as span:
        # Validation
        self._validate_type(type)

        # Create item
        item = self.repo.create(data)
        span.set_attribute("memory_id", item.id)

        # Log success
        logger.info(
            "Created memory item %s (project=%s, type=%s)",
            item.id,
            project_id,
            type,
            extra={
                "memory_id": item.id,
                "project_id": project_id,
                "memory_type": type,
            }
        )

        return self._item_to_dict(item)
```

**Span Attributes:**

Spans capture key operation metadata:

```python
span.set_attribute("memory_id", "mem-123")
span.set_attribute("memory_type", "decision")
span.set_attribute("duplicate", False)
span.set_attribute("from_status", "candidate")
span.set_attribute("to_status", "active")
span.add_event("merge_complete")
```

### Logging

**Structured Logging Format:**

```json
{
  "timestamp": "2026-02-06T10:30:00.123Z",
  "level": "INFO",
  "logger": "skillmeat.core.services.memory_service",
  "message": "Created memory item mem-123 (project=proj-456, type=decision)",
  "extra": {
    "memory_id": "mem-123",
    "project_id": "proj-456",
    "memory_type": "decision",
    "status": "candidate",
    "confidence": 0.9
  }
}
```

**Log Levels:**

| Level | Usage |
|-------|-------|
| `DEBUG` | Detailed query operations, cursor pagination details |
| `INFO` | CRUD operations, lifecycle transitions, pack generation |
| `WARNING` | Duplicate detection, partial bulk failures |
| `ERROR` | Validation failures, constraint violations |

---

## Extension Points

### 1. Custom Memory Types

Add domain-specific memory types (e.g., `security_note`, `api_endpoint_doc`) by following the "Adding New Memory Types" workflow above.

**Use Case**: Track security constraints separately from general constraints.

### 2. Custom Selectors

Extend module selectors with project-specific filters (e.g., `team_filter`, `severity_level`, `compliance_tag`).

**Use Case**: Create modules for different teams or compliance requirements.

### 3. TTL Policy Enforcement

Implement automated lifecycle transitions based on TTL policies:

```python
# File: skillmeat/core/services/memory_service.py

def apply_ttl_policies(self, project_id: str) -> Dict[str, Any]:
    """Deprecate memories that exceed TTL thresholds."""
    items = self.list_items(project_id, limit=10000)["items"]
    now = datetime.now(timezone.utc)
    deprecated_count = 0

    for item in items:
        ttl = item.get("ttl_policy")
        if not ttl:
            continue

        created_at = datetime.fromisoformat(item["created_at"])
        max_age_days = ttl.get("max_age_days")

        if max_age_days and (now - created_at).days > max_age_days:
            self.deprecate(item["id"], reason="TTL policy: max_age_days exceeded")
            deprecated_count += 1

    return {"deprecated_count": deprecated_count}
```

**Use Case**: Automatically expire learnings after 180 days to prevent stale knowledge accumulation.

### 4. Export/Import

Implement memory export for sharing across projects or teams:

```python
def export_memories(self, project_id: str, output_path: str) -> None:
    """Export all memories to JSON file."""
    items = self.list_items(project_id, limit=10000)["items"]

    with open(output_path, "w") as f:
        json.dump({"memories": items, "exported_at": _now_iso()}, f, indent=2)

def import_memories(self, project_id: str, input_path: str) -> Dict[str, Any]:
    """Import memories from JSON file."""
    with open(input_path, "r") as f:
        data = json.load(f)

    imported = []
    failed = []

    for item_data in data["memories"]:
        try:
            # Remove fields that shouldn't be imported
            item_data.pop("id", None)
            item_data.pop("created_at", None)
            item_data.pop("updated_at", None)
            item_data["project_id"] = project_id  # Override project

            item = self.create(**item_data)
            imported.append(item["id"])
        except Exception as e:
            failed.append({"content": item_data.get("content"), "error": str(e)})

    return {"imported": imported, "failed": failed}
```

**Use Case**: Share "Deployment Checklist" memories across multiple projects.

### 5. Auto-Extraction (Phase 5)

Implement automated memory extraction from agent run logs:

```python
def extract_from_run_log(self, project_id: str, run_log: str) -> List[Dict[str, Any]]:
    """Extract memory candidates from agent run log using TF-IDF."""
    # 1. Parse run log into structured events
    events = self._parse_run_log(run_log)

    # 2. Extract candidate memories using TF-IDF
    candidates = self._extract_candidates(events)

    # 3. Compute confidence scores
    for candidate in candidates:
        candidate["confidence"] = self._compute_confidence(candidate)

    # 4. Create memory items (status=candidate)
    created = []
    for candidate in candidates:
        item = self.create(
            project_id=project_id,
            type=candidate["type"],
            content=candidate["content"],
            confidence=candidate["confidence"],
            status="candidate",
            provenance={"source": "auto_extract", "run_id": candidate["run_id"]}
        )
        created.append(item)

    return created
```

**Use Case**: Automatically capture constraint violations and gotchas from failed CI runs.

---

## Common Patterns

### Pattern 1: Triage Workflow

```python
# 1. Create candidate memories (manual or auto-extracted)
candidate = service.create(
    project_id="proj-123",
    type="constraint",
    content="API rate limit: 100 req/min per user",
    confidence=0.6,
    status="candidate"
)

# 2. Validate in development (increase confidence)
service.update(candidate["id"], confidence=0.8)

# 3. Promote to active
active = service.promote(candidate["id"], reason="Validated in dev environment")

# 4. Validate in production for 30 days
# (manual monitoring)

# 5. Promote to stable
stable = service.promote(active["id"], reason="Validated in production for 30 days")
```

### Pattern 2: Module-Based Workflow Selection

```python
# Create modules for different workflows
debug_module = module_svc.create(
    project_id="proj-123",
    name="Debug Mode",
    selectors={
        "memory_types": ["gotcha", "constraint"],
        "min_confidence": 0.7
    },
    priority=1
)

release_module = module_svc.create(
    project_id="proj-123",
    name="Release Checklist",
    selectors={
        "memory_types": ["decision", "constraint"],
        "min_confidence": 0.9
    },
    priority=1
)

# Generate context pack for debugging
debug_pack = packer_svc.generate_pack(
    project_id="proj-123",
    module_id=debug_module["id"],
    budget_tokens=3000
)

# Generate context pack for release
release_pack = packer_svc.generate_pack(
    project_id="proj-123",
    module_id=release_module["id"],
    budget_tokens=2000
)
```

### Pattern 3: Merge Duplicates

```python
# Detect duplicates (manual or automated similarity search)
duplicate_pairs = [
    ("mem-old-1", "mem-new-1"),
    ("mem-old-2", "mem-new-2"),
]

for source_id, target_id in duplicate_pairs:
    try:
        merged = service.merge(
            source_id=source_id,
            target_id=target_id,
            strategy="keep_target",  # Keep the newer item
        )
        logger.info(f"Merged {source_id} into {target_id}")
    except ValueError as e:
        logger.error(f"Merge failed: {e}")
```

---

## Troubleshooting

### Issue: Duplicate Detection Not Working

**Symptom**: Same content is being stored multiple times.

**Cause**: Content hash computation includes whitespace/formatting differences.

**Solution**: Normalize content before hashing:

```python
def _compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of normalized content."""
    normalized = " ".join(content.split())  # Collapse whitespace
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

### Issue: Pack Token Budget Exceeded

**Symptom**: Generated pack exceeds budget by 10-20%.

**Cause**: Token estimation heuristic (`len(text) / 4`) is approximate.

**Solution**: Add safety margin to budget:

```python
effective_budget = int(budget_tokens * 0.9)  # 10% safety margin
pack = service.generate_pack(project_id, budget_tokens=effective_budget)
```

### Issue: Selector Not Filtering Correctly

**Symptom**: Module includes items that don't match selectors.

**Cause**: Selector logic in `apply_module_selectors` has a bug.

**Debug Strategy**:

1. Add debug logging to selector application:

```python
def apply_module_selectors(self, project_id: str, selectors: Dict[str, Any]):
    logger.debug(f"Applying selectors: {selectors}")
    items = self._fetch_candidates(project_id, selectors)
    logger.debug(f"Found {len(items)} candidate items")

    # Log filtering steps
    if "min_confidence" in selectors:
        before = len(items)
        items = [item for item in items if item["confidence"] >= selectors["min_confidence"]]
        logger.debug(f"Confidence filter: {before} → {len(items)}")

    return items
```

2. Write a failing test case:

```python
def test_min_confidence_filter_edge_case(packer_svc, memory_svc, project_id):
    """Test that min_confidence filter works correctly at boundary."""
    mem1 = memory_svc.create(
        project_id=project_id,
        type="decision",
        content="Test",
        confidence=0.799999  # Just below 0.8
    )

    items = packer_svc.apply_module_selectors(
        project_id,
        selectors={"min_confidence": 0.8}
    )

    assert mem1["id"] not in [item["id"] for item in items]
```

---

## Migration Guide (Database Changes)

When modifying the schema, always create an Alembic migration:

```bash
cd skillmeat/cache
alembic revision -m "description_of_change"
```

**Example: Add `source_url` column to `memory_items`**

```python
"""Add source_url to memory_items

Revision ID: def789ghi012
Revises: abc123def456
Create Date: 2026-02-06 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'def789ghi012'
down_revision = 'abc123def456'

def upgrade():
    op.add_column('memory_items', sa.Column('source_url', sa.String(), nullable=True))

def downgrade():
    op.drop_column('memory_items', 'source_url')
```

**Apply migration:**

```bash
alembic upgrade head
```

---

## Performance Considerations

### Database Indexes

The schema includes indexes for common query patterns:

```sql
CREATE INDEX idx_memory_items_project_status ON memory_items(project_id, status);
CREATE INDEX idx_memory_items_project_type ON memory_items(project_id, type);
CREATE INDEX idx_memory_items_created_at ON memory_items(created_at DESC);
```

**Query Pattern**: List active memories for a project, sorted by recency

```python
result = service.list_items(
    project_id="proj-123",
    status="active",
    sort_by="created_at",
    sort_order="desc"
)
```

This query uses the `idx_memory_items_project_status` index.

### Cursor-Based Pagination

All list operations use cursor-based pagination to avoid offset-based query performance degradation:

```python
# First page
result = service.list_items(project_id="proj-123", limit=50)

# Next page
result = service.list_items(
    project_id="proj-123",
    limit=50,
    cursor=result["next_cursor"]
)
```

**Why cursor-based?**
- Consistent performance regardless of page depth
- No duplicate/skipped items when data changes between requests
- More efficient for large datasets

### Content Hash Indexing

The `content_hash` column has a UNIQUE index for O(1) duplicate detection:

```sql
CREATE UNIQUE INDEX uq_memory_items_content_hash ON memory_items(content_hash);
```

When creating a memory item, the database enforces uniqueness at insert time, avoiding expensive content comparison queries.

---

## References

**Source Files:**
- Service Layer: `skillmeat/core/services/memory_service.py`, `context_module_service.py`, `context_packer_service.py`
- Repository Layer: `skillmeat/cache/memory_repositories.py`
- ORM Models: `skillmeat/cache/models.py` (lines 2400-2600)
- API Routers: `skillmeat/api/routers/memory_items.py`, `context_modules.py`, `context_packs.py`
- Schemas: `skillmeat/api/schemas/memory.py`
- Migrations: `skillmeat/cache/migrations/versions/20260205_1200_add_memory_and_context_tables.py`
- Tests: `skillmeat/api/tests/test_memory_services.py`, `test_e2e_memory_workflow.py`, `test_performance_benchmarks.py`

**Documentation:**
- User Guide: `/docs/user/guides/memory-context-system.md`
- Feature Flags: `/docs/feature-flags.md`
- PRD: `/docs/project_plans/PRDs/features/memory-context-system-v1.md`

**Key Context:**
- Data Flow Patterns: `.claude/context/key-context/data-flow-patterns.md`
- API Contract Source of Truth: `.claude/context/key-context/api-contract-source-of-truth.md`
- Testing Patterns: `.claude/context/key-context/testing-patterns.md`

---

## Summary

The Memory & Context Intelligence System provides a complete infrastructure for capturing, managing, and composing project-scoped knowledge. Developers can extend the system by:

1. **Adding memory types** to capture domain-specific knowledge
2. **Implementing custom selectors** for advanced filtering
3. **Building TTL automation** for lifecycle management
4. **Creating export/import tools** for knowledge sharing
5. **Developing auto-extraction** from logs and conversations

The layered architecture ensures clean separation of concerns, making the system maintainable and extensible. All operations are traced, logged, and tested for production readiness.
