---
title: "Execution Reference: Memory & Context Intelligence System"
description: "Quick reference for subagents executing tasks in the Memory & Context Intelligence System implementation."
audience: [ai-agents, developers]
tags: [reference, execution, memory-context-system, quick-lookup]
created: 2026-02-05
updated: 2026-02-05
---

# Execution Reference: Memory & Context Intelligence System

**Plan**: `IMPL-2026-02-05-memory-context-system-v1`
**Progress File**: `.claude/progress/memory-context-system-v1/all-phases-progress.md`
**Implementation Plan**: `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md`
**PRD**: `/docs/project_plans/PRDs/features/memory-context-system-v1.md`

---

## Task Lookup Table

Use this to quickly find task details by ID.

| Task ID | Name | Type | Phase | Estimate | Assigned To |
|---------|------|------|-------|----------|------------|
| PREP-0.1 | Verify Alembic Setup | Database Setup | 0 | 1 pt | data-layer-expert |
| PREP-0.2 | Create Feature Branch | Project Setup | 0 | 0.5 pt | lead-pm |
| PREP-0.3 | API Pattern Review | Review | 0 | 1 pt | backend-architect |
| PREP-0.4 | Test Infrastructure Setup | Testing Setup | 0 | 1 pt | python-backend-engineer |
| DB-1.1 | Schema Design | Database | 1 | 2 pts | data-layer-expert |
| DB-1.2 | ORM Models | Database | 1 | 2 pts | python-backend-engineer |
| DB-1.3 | Indexes & Constraints | Database | 1 | 1 pt | data-layer-expert |
| REPO-1.4 | MemoryItemRepository | Backend | 1 | 3 pts | python-backend-engineer |
| REPO-1.5 | ContextModuleRepository | Backend | 1 | 2 pts | python-backend-engineer |
| REPO-1.6 | Transaction Handling | Backend | 1 | 1 pt | data-layer-expert |
| TEST-1.7 | Repository Tests | Testing | 1 | 2 pts | python-backend-engineer |
| SVC-2.1 | MemoryService - Core | Backend | 2 | 3 pts | backend-architect |
| SVC-2.2 | MemoryService - Lifecycle | Backend | 2 | 3 pts | backend-architect |
| SVC-2.3 | MemoryService - Merge | Backend | 2 | 2 pts | python-backend-engineer |
| SVC-2.4 | ContextModuleService | Backend | 2 | 2 pts | python-backend-engineer |
| SVC-2.5 | ContextPackerService | Backend | 2 | 3 pts | backend-architect |
| API-2.6 | Memory Items Router - CRUD | API | 2 | 2 pts | python-backend-engineer |
| API-2.7 | Memory Items Router - Lifecycle | API | 2 | 2 pts | python-backend-engineer |
| API-2.8 | Memory Items Router - Merge | API | 2 | 1 pt | python-backend-engineer |
| API-2.9 | Context Modules Router | API | 2 | 2 pts | python-backend-engineer |
| API-2.10 | Context Packing API | API | 2 | 2 pts | python-backend-engineer |
| API-2.11 | OpenAPI Documentation | Documentation | 2 | 1 pt | api-documenter |
| TEST-2.12 | API Integration Tests | Testing | 2 | 3 pts | python-backend-engineer |
| TEST-2.13 | End-to-End Service Test | Testing | 2 | 1 pt | python-backend-engineer |
| UI-3.1 | Memory Inbox Page Layout | Frontend | 3 | 2 pts | frontend-developer |
| UI-3.2 | MemoryCard Component | Frontend | 3 | 2 pts | ui-engineer-enhanced |
| UI-3.3 | Filter Bar Components | Frontend | 3 | 2 pts | frontend-developer |
| UI-3.4 | Detail Panel Component | Frontend | 3 | 2 pts | frontend-developer |
| UI-3.5 | Triage Action Buttons | Frontend | 3 | 3 pts | ui-engineer-enhanced |
| UI-3.6 | Memory Form Modal | Frontend | 3 | 2 pts | frontend-developer |
| UI-3.7 | Merge Modal | Frontend | 3 | 2 pts | ui-engineer-enhanced |
| UI-3.8 | Batch Selection & Actions | Frontend | 3 | 2 pts | frontend-developer |
| HOOKS-3.9 | useMemoryItems Hook | Frontend | 3 | 1 pt | frontend-developer |
| HOOKS-3.10 | useMutateMemory Hook | Frontend | 3 | 2 pts | frontend-developer |
| HOOKS-3.11 | useMemorySelection Hook | Frontend | 3 | 1 pt | frontend-developer |
| A11Y-3.12 | Keyboard Navigation | Frontend | 3 | 2 pts | frontend-developer |
| A11Y-3.13 | WCAG Compliance | Frontend | 3 | 2 pts | web-accessibility-checker |
| TEST-3.14 | Component Tests | Testing | 3 | 2 pts | frontend-developer |
| TEST-3.15 | Keyboard Tests | Testing | 3 | 1 pt | web-accessibility-checker |
| PACK-4.1 | ContextPackerService - Selection Logic | Backend | 4 | 2 pts | backend-architect |
| PACK-4.2 | ContextPackerService - Token Estimation | Backend | 4 | 1 pt | python-backend-engineer |
| PACK-4.3 | EffectiveContext Composition | Backend | 4 | 2 pts | python-backend-engineer |
| UI-4.4 | ContextModulesTab | Frontend | 4 | 2 pts | frontend-developer |
| UI-4.5 | ModuleEditor Component | Frontend | 4 | 2 pts | ui-engineer-enhanced |
| UI-4.6 | EffectiveContextPreview Modal | Frontend | 4 | 2 pts | ui-engineer-enhanced |
| UI-4.7 | Context Pack Generation | Frontend | 4 | 1 pt | frontend-developer |
| TEST-4.8 | Packer Service Tests | Testing | 4 | 1 pt | python-backend-engineer |
| TEST-4.9 | Packer API Integration Tests | Testing | 4 | 1 pt | python-backend-engineer |
| TEST-4.10 | Context Module UI Tests | Testing | 4 | 1 pt | frontend-developer |
| EXT-5.1 | MemoryExtractorService | Backend | 5 | 3 pts | ai-engineer |
| EXT-5.2 | TF-IDF Deduplication | Backend | 5 | 3 pts | python-backend-engineer |
| EXT-5.3 | Confidence Scoring | Backend | 5 | 2 pts | ai-engineer |
| API-5.4 | Extract API Endpoint | API | 5 | 1 pt | python-backend-engineer |
| TEST-5.5 | Extractor Heuristics Tests | Testing | 5 | 2 pts | python-backend-engineer |
| TEST-5.6 | Extract Integration Test | Testing | 5 | 1 pt | python-backend-engineer |
| TEST-6.1 | Service Unit Tests | Testing | 6 | 2 pts | python-backend-engineer |
| TEST-6.2 | Repository Unit Tests | Testing | 6 | 1 pt | python-backend-engineer |
| TEST-6.3 | API Contract Tests | Testing | 6 | 1 pt | api-librarian |
| TEST-6.4 | Performance Benchmarks | Testing | 6 | 1 pt | python-backend-engineer |
| TEST-6.5 | Complete E2E Test | Testing | 6 | 1 pt | testing specialist |
| DOC-6.6 | API Documentation | Documentation | 6 | 1 pt | api-documenter |
| DOC-6.7 | Service Documentation | Documentation | 6 | 1 pt | documentation-writer |
| DOC-6.8 | Database Schema Docs | Documentation | 6 | 1 pt | documentation-writer |
| DOC-6.9 | User Guide - Memory Inbox | Documentation | 6 | 1 pt | documentation-writer |
| DOC-6.10 | User Guide - Context Modules | Documentation | 6 | 1 pt | documentation-writer |
| DOC-6.11 | Developer Guide | Documentation | 6 | 1 pt | documentation-writer |
| DEPLOY-6.12 | Feature Flags | DevOps | 6 | 1 pt | DevOps |
| DEPLOY-6.13 | Observability Setup | DevOps | 6 | 1 pt | backend-architect |
| DEPLOY-6.14 | Monitoring Configuration | DevOps | 6 | 1 pt | DevOps |
| DEPLOY-6.15 | Staging Deployment | DevOps | 6 | 1 pt | DevOps |
| DEPLOY-6.16 | Production Rollout | DevOps | 6 | 1 pt | DevOps |

---

## Key File Locations

### Core Implementation Files

| Path | Purpose |
|------|---------|
| `skillmeat/cache/models.py` | ORM models (MemoryItem, ContextModule, ModuleMemoryItem) |
| `skillmeat/cache/migrations/` | Alembic migration: `versions/[hash]_create_memory_tables.py` |
| `skillmeat/core/services/memory_service.py` | MemoryService business logic |
| `skillmeat/core/services/context_module_service.py` | ContextModuleService |
| `skillmeat/core/services/context_packing_service.py` | ContextPackerService |
| `skillmeat/core/services/memory_extractor.py` | MemoryExtractorService (Phase 5) |
| `skillmeat/cache/repositories.py` | Repository CRUD classes |
| `skillmeat/api/routers/memory_items.py` | Memory CRUD endpoints |
| `skillmeat/api/routers/context_modules.py` | Module endpoints |
| `skillmeat/api/routers/context_packs.py` | Packing endpoints |
| `skillmeat/api/schemas/memory.py` | Pydantic DTOs |
| `skillmeat/web/app/projects/[id]/memory/page.tsx` | Memory Inbox page |
| `skillmeat/web/components/memory/` | React components (cards, forms, modals) |

### Reference Files

| Path | Purpose |
|------|---------|
| `skillmeat/api/routers/context_entities.py` | Template for router pattern |
| `skillmeat/cache/models.py` | Template for ORM model patterns |
| `.claude/context/key-context/router-patterns.md` | Router conventions |
| `.claude/context/key-context/component-patterns.md` | React component conventions |
| `/skillmeat/api/CLAUDE.md` | API architecture guide |
| `/skillmeat/web/CLAUDE.md` | Frontend architecture guide |

### Documentation Files

| Path | Purpose |
|------|---------|
| `/docs/project_plans/PRDs/features/memory-context-system-v1.md` | Full PRD |
| `/docs/project_plans/design-specs/memory-context-system-ui-spec.md` | UI/UX spec |
| `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md` | This implementation plan |
| `.claude/progress/memory-context-system-v1/all-phases-progress.md` | Progress tracking |

---

## Database Schema Overview

### memory_items Table

```sql
CREATE TABLE memory_items (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL,
    type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
    status VARCHAR(20) NOT NULL,
    provenance_json TEXT,
    anchors_json TEXT,
    ttl_policy_json TEXT,
    content_hash VARCHAR(64) UNIQUE NOT NULL,
    access_count INT DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    deprecated_at DATETIME,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_memory_items_project_status ON memory_items(project_id, status);
CREATE INDEX idx_memory_items_project_type ON memory_items(project_id, type);
CREATE INDEX idx_memory_items_content_hash ON memory_items(content_hash);
```

### context_modules Table

```sql
CREATE TABLE context_modules (
    id VARCHAR(32) PRIMARY KEY,
    project_id VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    selectors_json TEXT,
    priority INT DEFAULT 0,
    content_hash VARCHAR(64),
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

### module_memory_items Table (Many-to-Many)

```sql
CREATE TABLE module_memory_items (
    module_id VARCHAR(32) NOT NULL,
    memory_id VARCHAR(32) NOT NULL,
    ordering INT NOT NULL,
    PRIMARY KEY (module_id, memory_id),
    FOREIGN KEY (module_id) REFERENCES context_modules(id) ON DELETE CASCADE,
    FOREIGN KEY (memory_id) REFERENCES memory_items(id) ON DELETE CASCADE
);
```

---

## API Endpoints Summary

### Memory Items Endpoints

```
GET    /api/v1/memory-items           List memories (paginated, filtered)
POST   /api/v1/memory-items           Create new memory
GET    /api/v1/memory-items/{id}      Get single memory
PUT    /api/v1/memory-items/{id}      Update memory
DELETE /api/v1/memory-items/{id}      Delete memory
PATCH  /api/v1/memory-items/{id}/promote    Promote (candidate→active→stable)
PATCH  /api/v1/memory-items/{id}/deprecate  Deprecate with reason
POST   /api/v1/memory-items/{id}/merge      Merge with target memory
```

### Context Modules Endpoints

```
GET    /api/v1/context-modules        List modules
POST   /api/v1/context-modules        Create module
GET    /api/v1/context-modules/{id}   Get module
PUT    /api/v1/context-modules/{id}   Update module
DELETE /api/v1/context-modules/{id}   Delete module
```

### Context Packing Endpoints

```
POST   /api/v1/context-packs/preview  Preview pack (dry-run)
POST   /api/v1/context-packs/generate Create deployable pack
```

---

## Response Envelope Format

### Success Response (List)

```json
{
  "items": [
    {
      "id": "uuid",
      "project_id": "uuid",
      "type": "constraint",
      "content": "Memory content here",
      "confidence": 0.87,
      "status": "active",
      "created_at": "2026-02-05T10:00:00Z",
      "updated_at": "2026-02-05T10:00:00Z",
      "access_count": 3
    }
  ],
  "next_cursor": "YWJjMTIzOjEwMC4w",
  "prev_cursor": null,
  "has_more": true,
  "total_count": 150
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Confidence must be between 0.0 and 1.0",
    "detail": {
      "field": "confidence",
      "value": 1.5
    }
  }
}
```

---

## Testing Patterns

### Repository Tests

```python
def test_memory_item_repository_create(session):
    repo = MemoryItemRepository(session)
    memory = repo.create(MemoryItemCreateRequest(...))
    assert memory.id is not None
    assert memory.content_hash is not None
```

### Service Tests

```python
def test_memory_service_promote(session):
    service = MemoryService(repo, session)
    memory = service.promote(memory_id, "active")
    assert memory.status == "active"
    assert memory.updated_at is not None
```

### API Tests

```python
def test_create_memory_item(client):
    response = client.post(
        "/api/v1/memory-items",
        json={"type": "constraint", "content": "...", "confidence": 0.85}
    )
    assert response.status_code == 201
    assert "id" in response.json()
```

### Component Tests

```typescript
test("MemoryCard displays confidence bar", () => {
  const { getByRole } = render(
    <MemoryCard memory={mockMemory} selected={false} />
  );
  const bar = getByRole("presentation", { hidden: true });
  expect(bar).toHaveClass("bg-emerald-500");
});
```

---

## Key Design Decisions

### Memory Types

| Type | Icon | Color | Use Case |
|------|------|-------|----------|
| constraint | ShieldAlert | Violet | API limitations, system rules |
| decision | GitBranch | Blue | Architecture choices, technology picks |
| fix | Wrench | Orange | Workarounds, bug fixes |
| pattern | Puzzle | Cyan | Coding patterns, best practices |
| learning | Lightbulb | Pink | Insights, lessons learned |
| style_rule | Palette | Teal | Code style, naming conventions |

### Confidence Tiers

| Range | Tier | Color | Meaning |
|-------|------|-------|---------|
| ≥85% | High | Emerald | Well-validated, frequently used |
| 60-84% | Medium | Amber | Moderately confident, situational |
| <60% | Low | Red | Uncertain, needs validation |

### Memory Lifecycle

```
candidate → active → stable → deprecated
     ↑                              ↓
     └──────────────────────────────┘
                (reject)
```

- **Candidate**: Newly extracted or created, unreviewed
- **Active**: Reviewed and approved, in current use
- **Stable**: Repeatedly validated, high-quality permanent record
- **Deprecated**: Outdated, low hit rate, user-marked obsolete

---

## Common Tasks Checklists

### Database Migration (Task DB-1.1)

- [ ] Create `versions/{timestamp}_create_memory_tables.py` in `skillmeat/cache/migrations/`
- [ ] Define `upgrade()` function with CREATE TABLE statements
- [ ] Define `downgrade()` function with DROP TABLE statements
- [ ] Test: `alembic upgrade head` succeeds
- [ ] Test: `alembic downgrade -1` succeeds
- [ ] Verify all 3 tables created with correct columns
- [ ] Verify indexes created
- [ ] Verify foreign key constraints

### ORM Model Implementation (Task DB-1.2)

- [ ] Add 3 class definitions to `skillmeat/cache/models.py`
- [ ] Use SQLAlchemy Mapped types with proper imports
- [ ] Add UUID primary keys: `id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)`
- [ ] Add relationships: MemoryItem ↔ ContextModule (many-to-many)
- [ ] Add __tablename__ and __table_args__
- [ ] Test: Models import without errors
- [ ] Test: Models can be instantiated
- [ ] Verify relationships work both directions

### Repository CRUD (Task REPO-1.4)

- [ ] Create `MemoryItemRepository` class
- [ ] Implement `create(request: MemoryItemCreateRequest) → MemoryItem`
- [ ] Implement `get(id: str) → Optional[MemoryItem]`
- [ ] Implement `list(project_id, filters) → List[MemoryItem]` with pagination
- [ ] Implement `update(id, request) → MemoryItem`
- [ ] Implement `delete(id) → bool`
- [ ] Implement `find_by_content_hash(content_hash) → Optional[MemoryItem]`
- [ ] Add cursor pagination helper methods
- [ ] Add transaction handling with try/except
- [ ] Test all methods, >85% coverage

### Service Implementation (Task SVC-2.1)

- [ ] Create `MemoryService` class
- [ ] Accept repository and session in __init__
- [ ] Implement CRUD methods delegating to repository
- [ ] All methods return DTOs (not ORM models)
- [ ] Add proper error handling with specific exceptions
- [ ] Add logging for all operations
- [ ] Write unit tests with fixtures, >80% coverage
- [ ] Document with docstrings

### API Router (Task API-2.6)

- [ ] Create `skillmeat/api/routers/memory_items.py`
- [ ] Define router with `/api/v1/memory-items` prefix
- [ ] Implement GET (list) with pagination + filters
- [ ] Implement POST (create) with validation
- [ ] Implement GET (get one)
- [ ] Implement PUT (update)
- [ ] Implement DELETE
- [ ] All endpoints use DTOs, never ORM models
- [ ] Use consistent error response envelopes
- [ ] Add proper status codes (201 for create, 204 for delete, etc.)
- [ ] Write integration tests

### Frontend Component (Task UI-3.2)

- [ ] Create `skillmeat/web/components/memory/MemoryCard.tsx`
- [ ] Props: memory, selected, focused, onToggleSelect, onApprove, onReject, onEdit, onClick
- [ ] Render: checkbox, confidence bar, type badge, content preview, metadata row
- [ ] Implement hover/focus states
- [ ] Implement keyboard support (Space to select, Enter for detail)
- [ ] Add accessibility labels and ARIA attributes
- [ ] Write component tests with React Testing Library
- [ ] Test focus management and keyboard navigation

---

## Common Pitfalls to Avoid

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Exposing ORM models in API | API returns `MemoryItem` instance | Return DTOs only: `MemoryItemResponse` |
| Forgetting cursor pagination | Large datasets load slowly | Implement base64 cursor logic |
| No transaction handling | Partial writes on error | Use try/except with rollback |
| Missing content_hash uniqueness | Duplicate memories created | Add UNIQUE constraint to migration |
| Inaccessible keyboard shortcuts | Screen reader can't see shortcuts | Use semantic HTML, ARIA labels |
| Breaking existing router pattern | New routers inconsistent | Copy pattern from `context_entities.py` |
| Missing error logging | Can't debug failures | Log every exception with context |
| Forgetting to update openapi.json | API docs out of sync | Run FastAPI doc generation |

---

## Quick Status Update Command

To update progress file from command line:

```bash
# Update single task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/memory-context-system-v1/all-phases-progress.md \
  -t DB-1.1 \
  -s in-progress

# Update multiple tasks
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/memory-context-system-v1/all-phases-progress.md \
  --updates "DB-1.1:completed,DB-1.2:in-progress,REPO-1.4:queued"
```

---

## Contact Points

| Aspect | Point of Contact | File |
|--------|------------------|------|
| Overall Orchestration | Implementation Planner | `/docs/project_plans/implementation_plans/features/memory-context-system-v1.md` |
| Database Design Questions | Data Layer Expert | `skillmeat/cache/models.py` |
| API Contract Questions | Backend Architect | `skillmeat/api/routers/memory_items.py` |
| Frontend Design Questions | UI Designer | `docs/project_plans/design-specs/memory-context-system-ui-spec.md` |
| Testing Strategy | Testing Specialist | `.claude/progress/memory-context-system-v1/all-phases-progress.md` |
| Performance Concerns | Backend Architect | Section: "Critical Success Metrics" |

---

**Last Updated**: 2026-02-05
**Version**: 1.0
