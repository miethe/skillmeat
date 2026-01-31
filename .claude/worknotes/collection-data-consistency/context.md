---
type: context
prd: "collection-data-consistency"
title: "Collection Data Consistency & Performance Optimization Context"
status: "pending"
created: "2026-01-30"
updated: "2026-01-30"

phase_status:
  - phase: 1
    title: "Critical Performance Fix"
    status: "pending"
    reason: null
  - phase: 2
    title: "Frontend Mapping Consolidation"
    status: "pending"
    reason: null
  - phase: 3
    title: "API Endpoint Consistency"
    status: "pending"
    reason: "Depends on Phase 1"
  - phase: 4
    title: "Caching Layer"
    status: "pending"
    reason: "Depends on Phase 3"
  - phase: 5
    title: "Frontend Data Preloading"
    status: "pending"
    reason: "Depends on Phase 2"

blockers: []

decisions:
  - id: "DECISION-1"
    question: "How to fix N+1 query for collection artifact counts?"
    decision: "Single aggregation query with GROUP BY"
    rationale: "Replaces 100+ queries with 1 query, ~10x performance improvement"
    tradeoffs: "Slightly more complex query logic"
    location: "skillmeat/api/routers/artifacts.py"
  - id: "DECISION-2"
    question: "Where to centralize Entity mapping?"
    decision: "New file: lib/api/entity-mapper.ts"
    rationale: "Single source of truth, eliminates 3 duplicate mapping locations"
    tradeoffs: "Migration effort across multiple components"
    location: "skillmeat/web/lib/api/entity-mapper.ts"
  - id: "DECISION-3"
    question: "How to ensure endpoint consistency?"
    decision: "CollectionService abstraction"
    rationale: "Centralized service ensures all endpoints use same query pattern"
    tradeoffs: "New service layer to maintain"
    location: "skillmeat/api/services/collection_service.py"
  - id: "DECISION-4"
    question: "Caching strategy for collection counts?"
    decision: "TTL-based in-memory cache with 5-minute expiration"
    rationale: "Simple, effective, matches typical user session patterns"
    tradeoffs: "Eventually consistent (5-minute staleness window)"
    location: "skillmeat/cache/collection_cache.py"

integrations:
  - system: "frontend"
    component: "EntityModal"
    calls: ["GET /api/v1/artifacts", "GET /api/v1/artifacts/{id}"]
    status: "pending-optimization"
  - system: "frontend"
    component: "CollectionPage"
    calls: ["GET /api/v1/artifacts"]
    status: "pending-mapping-fix"
  - system: "frontend"
    component: "ProjectManagePage"
    calls: ["GET /api/v1/projects/{id}/artifacts"]
    status: "pending-mapping-fix"

gotchas: []

modified_files: []
---

# Collection Data Consistency & Performance Optimization Context

**Status**: Pending
**Last Updated**: 2026-01-30
**Purpose**: Token-efficient context for agents continuing this work

## Objective

Fix compound problem affecting collection data across SkillMeat:

1. **N+1 Query Pattern**: 100+ database queries per page load (1200ms p95 latency)
2. **Inconsistent Entity Mapping**: 3 duplicate mapping locations, 20 fields missing in some
3. **Missing Collection Data**: Collection badges not showing on various pages

**Target Metrics**:
- API response time: 1200ms -> <200ms (10x improvement)
- Database queries: 107 -> <=5 (96% reduction)
- Collection badge render rate: ~60% -> 100%
- Duplicate mapping code: 3 locations -> 1 location

## Critical Path

```
Phase 1 (N+1 fix) --> Phase 3 (CollectionService) --> Phase 4 (Caching)

Phase 2 (Mapping) --> Phase 5 (Preloading)
```

**Parallel Tracks**:
- Track A: Phases 1 -> 3 -> 4 (Backend)
- Track B: Phases 2 -> 5 (Frontend)

Phases 1 and 2 have NO dependencies and can execute simultaneously.

## Key Decisions

### DECISION-1: N+1 Fix Strategy

**Question**: How to fix N+1 query for collection artifact counts?

**Decision**: Single aggregation query with GROUP BY

**Implementation**:
```python
count_query = (
    db_session.query(
        CollectionArtifact.collection_id,
        func.count(CollectionArtifact.artifact_id).label('artifact_count')
    )
    .filter(CollectionArtifact.collection_id.in_(collection_ids))
    .group_by(CollectionArtifact.collection_id)
    .all()
)
count_map = {row.collection_id: row.artifact_count for row in count_query}
```

**Location**: `skillmeat/api/routers/artifacts.py:1897-1916`

### DECISION-2: Entity Mapping Centralization

**Question**: Where to centralize Entity mapping?

**Decision**: New file `lib/api/entity-mapper.ts`

**Key Points**:
- Maps all 24 Entity fields
- Context-aware (collection, project, marketplace)
- Collections field ALWAYS mapped (critical fix)
- Batch utility for lists

**Migration Required**:
- `hooks/useEntityLifecycle.tsx` - replace mapApiArtifactToEntity
- `app/collection/page.tsx` - remove enrichArtifactSummary
- `app/projects/[id]/manage/page.tsx` - remove inline mapping blocks

### DECISION-3: CollectionService Abstraction

**Question**: How to ensure all endpoints return consistent collection data?

**Decision**: Create `CollectionService` class in `api/services/`

**Methods**:
- `get_collection_membership_batch(artifact_ids)` - main batch method
- `get_collection_membership_single(artifact_id)` - convenience wrapper

**Endpoints to Update**:
- GET /api/v1/artifacts
- GET /api/v1/artifacts/{id}
- GET /api/v1/projects/{id}/artifacts
- GET /api/v1/collections/{id}/artifacts

### DECISION-4: Caching Strategy

**Question**: How to sustain performance for collection counts?

**Decision**: TTL-based in-memory cache with 5-minute expiration

**Characteristics**:
- Thread-safe with Lock
- Lazy expiration (check on read)
- Explicit invalidation on mutations
- Eventually consistent (acceptable for count data)

**Invalidation Triggers**:
- POST /api/v1/user-collections/{id}/artifacts (add)
- DELETE /api/v1/user-collections/{id}/artifacts/{artifact_id} (remove)
- DELETE /api/v1/user-collections/{id} (delete collection)

## Implementation Notes

### Backend (python-backend-engineer)

**Relationship Loading Change**:
```python
# In cache/models.py, change lazy strategy:
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    lazy="select",  # Changed from "selectin"
)
```

**Why**: Prevents duplicate eager loading when manual queries are used.

### Frontend (ui-engineer)

**Entity Mapper Critical Fields**:
```typescript
// These fields were missing in some mappers:
collections: (artifact.collections ?? []).map(c => ({
  id: c.id,
  name: c.name,
  artifactCount: c.artifact_count,
})),
```

**Prefetch Strategy**:
- Prefetch `/api/v1/sources` and `/api/v1/user-collections` on app load
- Use 5-minute staleTime to match backend cache TTL
- Non-blocking (useEffect, not Suspense)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| N+1 fix breaks edge case | Comprehensive test coverage before merge |
| Frontend mapping breaks modal | Test all modal contexts before merge |
| Cache race condition | Thread-safe Lock, test concurrent access |

## Deferred Enhancements

The following were identified but deferred to future PRD:
- A: Denormalized artifact_count column (2-3h)
- B: Collection membership index (30min)
- C: API response compression (1h)
- D: Bulk collection operations (4-6h)

## Files Reference

### New Files
- `skillmeat/api/services/collection_service.py`
- `skillmeat/api/services/__init__.py`
- `skillmeat/cache/collection_cache.py`
- `skillmeat/web/lib/api/entity-mapper.ts`
- `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts`
- `tests/api/services/test_collection_service.py`
- `tests/cache/test_collection_cache.py`

### Modified Files
- `skillmeat/api/routers/artifacts.py`
- `skillmeat/api/routers/projects.py`
- `skillmeat/api/routers/collections.py`
- `skillmeat/api/routers/user_collections.py`
- `skillmeat/cache/models.py`
- `skillmeat/web/hooks/useEntityLifecycle.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/web/app/projects/[id]/manage/page.tsx`
- `skillmeat/web/app/providers.tsx`

## Handoff Notes

**For Backend Engineer Starting Phase 1**:
1. Look at `artifacts.py:1897-1916` for the N+1 loop
2. The fix pattern is documented in DECISION-1 above
3. Run existing tests after changes to verify no regressions

**For Frontend Engineer Starting Phase 2**:
1. Start with entity-mapper.ts creation (TASK-2.1)
2. Reference existing mapper in `lib/api/mappers.ts` for patterns
3. Key fix: ensure `collections` field is always mapped

**For Continuation After Phase 1/2**:
- Phase 3 can start immediately after Phase 1 completes
- Phase 5 can start immediately after Phase 2 completes
- Phases 1 and 2 are independent - no coordination needed

## Related Documents

- **Implementation Plan**: `/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md`
- **SPIKE**: `/docs/spikes/SPIKE-collection-data-consistency.md`
- **Architecture Analysis**: `/docs/project_plans/reports/artifact-modal-architecture-analysis.md`
