---
status: inferred_complete
schema_version: 2
doc_type: implementation_plan
feature_slug: agent-context-entities
prd_ref: null
---
# Implementation Plan: Agent Context Entities v2

**Feature:** Agent Context Entities - Completion Plan
**Original PRD:** `/docs/project_plans/PRDs/features/agent-context-entities-v1.md`
**Original Plan:** `/docs/project_plans/implementation_plans/features/agent-context-entities-v1.md`
**Status:** Ready for Implementation
**Priority:** HIGH (Feature non-functional without this)
**Complexity:** Medium (M)
**Estimated Duration:** 2-3 days

---

## Executive Summary

This v2 plan completes the Agent Context Entities feature that was incorrectly marked as completed in v1. The original implementation created database columns, schemas, validation, and UI components, but **all backend API endpoints return 501 (Not Implemented) errors**, making the entire feature non-functional.

### Critical Gap Identified

| Component | v1 Status | Actual State |
|-----------|-----------|--------------|
| Database columns | "Completed" | **Done** - `path_pattern`, `auto_load`, `category`, `content_hash` added to Artifact |
| API Schemas | "Completed" | **Done** - All Pydantic models created |
| Validation | "Completed" | **Done** - Path traversal, frontmatter validation |
| Router | "Completed" | **NOT DONE** - All endpoints throw `HTTPException(501)` |
| Content Storage | Not addressed | **MISSING** - Artifact model has no `content` column |
| Web UI | "Completed" | **Done** - But non-functional due to 501 errors |

### Root Cause

1. The Artifact model was extended with metadata columns but **no content column** was added
2. Router endpoints were written as stubs with commented-out implementation templates
3. Progress files were marked "completed" despite endpoints returning 501 errors
4. Phase 3 notes even document: "Backend API returns 501 (stub) - database model needs to be wired in Phase 1 completion"

---

## Technical Analysis

### Current State of `skillmeat/api/routers/context_entities.py`

All 6 endpoints currently throw:
```python
raise HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Context entities database model not yet implemented (TASK-1.2)",
)
```

The router has **commented-out implementation templates** for each endpoint that need to be:
1. Adapted to use the existing `Artifact` model (not a separate `ContextEntity` model)
2. Filter by context entity types (`project_config`, `spec_file`, `rule_file`, `context_file`, `progress_template`)
3. Handle content storage (new column needed)

### Database Model Gap

**Current Artifact model has:**
```python
path_pattern: Mapped[Optional[str]]
auto_load: Mapped[bool]
category: Mapped[Optional[str]]
content_hash: Mapped[Optional[str]]
```

**Missing for context entities:**
```python
content: Mapped[Optional[Text]]  # Markdown content storage
description: Mapped[Optional[str]]  # Entity description
```

### Decision Required: Content Storage Strategy

**Option A: Add `content` column to Artifact model (Recommended)**
- Simpler implementation
- Content stored in database with other metadata
- Works well for context files (typically < 50KB)
- Requires Alembic migration

**Option B: File-based content storage**
- Store content in `~/.skillmeat/context-entities/{id}.md`
- Database stores metadata only
- Better for very large files
- More complex implementation

**Recommendation:** Option A - Add `content` column. Context files are typically small markdown documents (< 50KB), and database storage simplifies queries and backups.

---

## Implementation Tasks

### Phase 1: Database Completion (Day 1 - Morning)

#### TASK-V2.1: Add Missing Columns to Artifact Model
**Agent:** `python-backend-engineer`
**Files:** `skillmeat/cache/models.py`
**Changes:**
1. Add `content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to Artifact model
2. Add `description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to Artifact model
3. Update `to_dict()` method to include new fields
4. Run tests to verify model changes

#### TASK-V2.2: Create Alembic Migration
**Agent:** `data-layer-expert`
**Files:** New migration file in `alembic/versions/`
**Changes:**
```sql
ALTER TABLE artifacts ADD COLUMN content TEXT;
ALTER TABLE artifacts ADD COLUMN description TEXT;
```
**Note:** Must be reversible migration.

### Phase 2: Router Implementation (Day 1 - Afternoon)

#### TASK-V2.3: Implement Context Entities Router
**Agent:** `python-backend-engineer`
**File:** `skillmeat/api/routers/context_entities.py`
**Changes:**
1. Import `Artifact`, `get_session` from `skillmeat.cache.models`
2. Define CONTEXT_ENTITY_TYPES constant:
   ```python
   CONTEXT_ENTITY_TYPES = {
       "project_config", "spec_file", "rule_file",
       "context_file", "progress_template"
   }
   ```
3. Implement all 6 endpoints by adapting commented templates:
   - `GET /context-entities` - List with filters, cursor pagination
   - `POST /context-entities` - Create with validation
   - `GET /context-entities/{id}` - Get by ID
   - `PUT /context-entities/{id}` - Update with validation
   - `DELETE /context-entities/{id}` - Delete entity
   - `GET /context-entities/{id}/content` - Get raw content

**Key implementation notes:**
- Query `Artifact` model where `type IN CONTEXT_ENTITY_TYPES`
- Store content directly in `Artifact.content` column
- Compute and store `content_hash` on create/update
- Generate UUID for new entities with `ctx_` prefix

### Phase 3: Integration Testing (Day 2 - Morning)

#### TASK-V2.4: API Integration Tests
**Agent:** `python-backend-engineer`
**File:** `tests/integration/test_context_entities_api.py`
**Tests:**
1. Create context entity (all 5 types)
2. List with filters (type, category, auto_load, search)
3. Cursor-based pagination
4. Get entity by ID
5. Update entity (partial and full)
6. Delete entity
7. Get raw content
8. Validation error cases (path traversal, invalid type)
9. 404 for non-existent entities

#### TASK-V2.5: End-to-End Verification
**Agent:** `python-backend-engineer`
**Actions:**
1. Start API server
2. Verify each endpoint returns 200/201/204 (not 501)
3. Create test entities via API
4. Verify frontend loads data (manual check)
5. Clean up test data

### Phase 4: Frontend Fixes (Day 2 - Afternoon, if needed)

#### TASK-V2.6: Verify and Fix API Client (Conditional)
**Agent:** `ui-engineer`
**File:** `skillmeat/web/lib/api/context-entities.ts`
**Condition:** Only if API response structure differs from frontend expectations
**Changes:**
1. Verify response types match backend
2. Fix any type mismatches
3. Verify deploy endpoint integration

---

## Parallelization Strategy

```
Day 1 (Morning):
├── TASK-V2.1 → python-backend-engineer (Model changes)
└── TASK-V2.2 → data-layer-expert (Migration)

Day 1 (Afternoon):
└── TASK-V2.3 → python-backend-engineer (Router implementation)

Day 2 (Morning):
├── TASK-V2.4 → python-backend-engineer (Integration tests)
└── TASK-V2.5 → python-backend-engineer (E2E verification)

Day 2 (Afternoon) - If needed:
└── TASK-V2.6 → ui-engineer (Frontend fixes)
```

---

## Orchestration Quick Reference

### Day 1 - Batch 1 (Parallel - Foundation)

```python
Task("python-backend-engineer", """TASK-V2.1: Add missing columns to Artifact model.
File: skillmeat/cache/models.py

Changes needed:
1. Add content column after content_hash:
   content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

2. Add description column:
   description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

3. Update to_dict() to include:
   "content": self.content,
   "description": self.description,

Run tests after: pytest -v -k artifact""")

Task("data-layer-expert", """TASK-V2.2: Create Alembic migration for content columns.
Create new migration adding:
- content TEXT column (nullable) to artifacts table
- description TEXT column (nullable) to artifacts table

Ensure migration is reversible.
Test: alembic upgrade head && alembic downgrade -1 && alembic upgrade head""")
```

### Day 1 - Batch 2 (Sequential - Router)

```python
Task("python-backend-engineer", """TASK-V2.3: Implement context entities router endpoints.
File: skillmeat/api/routers/context_entities.py

This router currently has all endpoints throwing 501 errors with commented-out
implementation templates. Implement all endpoints by:

1. Add imports at top:
   from skillmeat.cache.models import Artifact, get_session

2. Define constant:
   CONTEXT_ENTITY_TYPES = {"project_config", "spec_file", "rule_file", "context_file", "progress_template"}

3. For each endpoint, uncomment and adapt the template code:
   - Replace ContextEntity with Artifact
   - Add filter: .filter(Artifact.type.in_(CONTEXT_ENTITY_TYPES))
   - Map schema response to use Artifact fields
   - Remove the raise HTTPException(501) calls

4. For create endpoint:
   - Generate ID: f"ctx_{uuid.uuid4().hex[:12]}"
   - Compute content_hash before save
   - Validate content with validators

5. For list endpoint:
   - Support cursor-based pagination
   - Support all query filters (type, category, auto_load, search)

Reference the commented-out templates in the file for implementation patterns.
Each endpoint has a detailed template showing the logic needed.""")
```

### Day 2 - Batch 3 (Parallel - Verification)

```python
Task("python-backend-engineer", """TASK-V2.4: Create integration tests for context entities API.
File: tests/integration/test_context_entities_api.py

Test cases needed:
1. test_list_context_entities - verify GET returns 200, not 501
2. test_create_context_entity_spec_file - create with valid data
3. test_create_context_entity_rule_file - create rule file type
4. test_filter_by_type - test entity_type filter
5. test_filter_by_category - test category filter
6. test_filter_by_auto_load - test auto_load filter
7. test_pagination - test cursor-based pagination
8. test_get_entity_by_id - test GET /{id}
9. test_update_entity - test PUT /{id}
10. test_delete_entity - test DELETE /{id}
11. test_get_content - test GET /{id}/content
12. test_path_traversal_rejected - ensure ../.. is rejected
13. test_invalid_type_rejected - ensure non-context types rejected
14. test_entity_not_found - 404 for missing ID

Use TestClient pattern from existing API tests.
Create test fixtures for each entity type.""")
```

---

## Quality Gates

- [ ] All endpoints return appropriate status codes (not 501)
- [ ] Create operation stores content and returns entity
- [ ] List operation supports filters and pagination
- [ ] Content validation prevents path traversal
- [ ] Frontend `/context-entities` page loads data
- [ ] Entity detail modal displays content
- [ ] Create/edit forms submit successfully
- [ ] 90%+ test coverage for new code
- [ ] No TypeScript errors in frontend

---

## Success Criteria

1. **API Functional:** All 6 endpoints return real data (not 501)
2. **E2E Works:** Can create entity in UI → see it in list → view content → delete
3. **Validation Works:** Invalid path patterns rejected with 400
4. **Pagination Works:** Cursor-based pagination functions correctly
5. **Content Stored:** Markdown content persisted and retrievable

---

## Risk Assessment

### Low Risk
- This is completion work, not new design
- All schemas and validation already exist
- Frontend is already built and tested

### Medium Risk
- Alembic migration on production database
  - **Mitigation:** Test migration on staging first
  - **Mitigation:** Migration only adds nullable columns (backward compatible)

### Potential Blockers
- None identified - all dependencies in place

---

## Related Documentation

- **Original PRD:** `/docs/project_plans/PRDs/features/agent-context-entities-v1.md`
- **Original Plan:** `/docs/project_plans/implementation_plans/features/agent-context-entities-v1.md`
- **Progress Files:** `.claude/progress/agent-context-entities/` (mark as incomplete)
- **Database Models:** `skillmeat/cache/models.py`
- **API Patterns:** `.claude/rules/api/routers.md`

---

## Post-Implementation

After v2 completion:
1. Update Phase 1 progress file to reflect actual completion
2. Mark Phase 3 as truly complete (frontend already done)
3. Proceed with Phase 4-6 per original plan (templates, sync, polish)
4. Close this gap in the implementation tracking

---

**Ready to begin implementation.**
