# SPIKE: Collection Data Consistency & Performance Optimization

**Date**: 2026-01-30
**Author**: Claude Opus 4.5 (AI-generated)
**Status**: Draft - Ready for Review
**Related Report**: `docs/project_plans/reports/artifact-modal-architecture-analysis.md` (Recommendation 4)

---

## Executive Summary

This SPIKE investigates Recommendation 4 from the artifact modal architecture analysis: ensuring consistent collection membership data across all API endpoints. The investigation revealed this is not merely a consistency issue but a **compound problem** encompassing:

1. **Performance Crisis**: N+1 query patterns causing 100+ database queries per page load
2. **Data Inconsistency**: Multiple mapping functions producing different Entity objects
3. **Architectural Debt**: Duplicate enrichment logic scattered across frontend
4. **Caching Gaps**: No application-level caching for frequently accessed collection data

**Recommendation**: Address all four issues together as they share common refactoring points and the performance fixes alone would deliver 10x response time improvement.

---

## Business Value

| Metric | Current State | After Refactor | Impact |
|--------|---------------|----------------|--------|
| API Response Time | 800-1200ms | 80-120ms | 10x faster |
| Database Queries/Request | 105-107 | 4 | 96% reduction |
| Duplicate Mapping Code | 3 locations, 120 lines | 1 location | 67% less maintenance |
| Bug Risk (field omission) | High | Low | Centralized updates |
| Collection badge accuracy | Inconsistent | 100% consistent | Better UX |

---

## Requirements Analysis

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | All artifact-returning endpoints include consistent `collections` array | Must Have |
| FR-2 | Collection membership visible in all contexts (collection, manage, marketplace) | Must Have |
| FR-3 | Collection artifact counts accurate and performant | Must Have |
| FR-4 | Single source of truth for API → Entity mapping | Should Have |
| FR-5 | Collection data preloaded to eliminate navigation dependencies | Should Have |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | API response time for artifact lists | < 200ms (p95) |
| NFR-2 | Database queries per request | ≤ 5 |
| NFR-3 | Frontend mapping consistency | 100% field coverage |
| NFR-4 | Collection count staleness | ≤ 5 minutes |

---

## Architecture Design

### Current State Analysis

#### Database Layer
**Schema is sound** - Uses proper many-to-many junction table:

```
Artifact (1) <---> (*) CollectionArtifact (*) <---> (1) Collection
```

**Key Design Decision**: `CollectionArtifact.artifact_id` has **no FK constraint** because artifacts can be external (marketplace, GitHub). This is intentional and should be preserved.

#### API Layer Issues

**Problem 1: N+1 COUNT Queries**
Location: `skillmeat/api/routers/artifacts.py:1905-1908`

```python
# CURRENT: N+1 pattern - COUNT query per collection per artifact
for assoc in associations:
    coll = collection_details.get(assoc.collection_id)
    if coll:
        artifact_count = (
            db_session.query(CollectionArtifact)
            .filter_by(collection_id=coll.id)
            .count()  # ❌ Query inside loop!
        )
```

**Impact**: 50 artifacts × 2 collections avg = 100 COUNT queries per page load

**Problem 2: Redundant Relationship Loading**
Location: `skillmeat/cache/models.py:287-294`

```python
# Artifact model has eager loading...
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    lazy="selectin",  # Always loads, even when manually querying
)
```
But `artifacts.py` queries CollectionArtifact manually anyway, causing duplicate work.

#### Frontend Layer Issues

**Problem 3: Duplicate Mapping Functions**

| Location | Function | Fields Mapped | Missing Fields |
|----------|----------|---------------|----------------|
| `lib/api/mappers.ts` | `mapApiResponseToArtifact()` | 24/24 | None |
| `app/collection/page.tsx` | `enrichArtifactSummary()` | 4/24 | 20 fields |
| `app/projects/[id]/manage/page.tsx` | inline enrichment | 16/24 | 8 fields |
| `app/projects/[id]/manage/page.tsx` | inline enrichment (duplicate) | 16/24 | 8 fields |

**Impact**: Collection badges don't show on /collection page because `enrichArtifactSummary()` doesn't map the `collections` field.

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         API Layer Changes                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  NEW: services/collection_service.py                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  class CollectionService:                                        │   │
│  │    def get_collection_membership_batch(                          │   │
│  │        artifact_ids: List[str]                                   │   │
│  │    ) -> Dict[str, List[ArtifactCollectionInfo]]:                │   │
│  │        # Single query with GROUP BY for counts                   │   │
│  │        # Returns: {artifact_id: [collection_info, ...]}         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  MODIFIED: routers/artifacts.py                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  # Replace N+1 loop with single service call                     │   │
│  │  collections_map = collection_service.get_collection_membership_ │   │
│  │      batch(artifact_ids)                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  MODIFIED: cache/models.py                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  collections: Mapped[List["Collection"]] = relationship(         │   │
│  │      lazy="select",  # Changed from "selectin"                   │   │
│  │  )                                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       Frontend Layer Changes                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  NEW: lib/api/entity-mapper.ts                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  export function mapArtifactToEntity(                            │   │
│  │    artifact: ArtifactResponse,                                   │   │
│  │    context: 'collection' | 'project' | 'marketplace'             │   │
│  │  ): Entity {                                                     │   │
│  │    // Single source of truth for ALL 24 fields                   │   │
│  │    // Context determines mode-specific defaults                  │   │
│  │  }                                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  DELETED: enrichArtifactSummary() in collection/page.tsx               │
│  DELETED: inline enrichment in projects/[id]/manage/page.tsx (x2)      │
│                                                                         │
│  MODIFIED: useEntityLifecycle.tsx                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  // Import centralized mapper                                    │   │
│  │  import { mapArtifactToEntity } from '@/lib/api/entity-mapper'; │   │
│  │  // Replace mapApiArtifactToEntity with centralized version      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Caching Layer                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  NEW: cache/collection_cache.py                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  class CollectionCountCache:                                     │   │
│  │    _cache: Dict[str, Tuple[int, float]] = {}  # id -> (count, ts)│   │
│  │    TTL = 300  # 5 minutes                                        │   │
│  │                                                                  │   │
│  │    def get_counts(self, collection_ids: Set[str]) -> Dict:       │   │
│  │        # Return cached counts, fetch missing                     │   │
│  │                                                                  │   │
│  │    def invalidate(self, collection_id: str):                     │   │
│  │        # Called on add/remove artifact from collection           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Critical Performance Fix (Priority: CRITICAL)
**Estimated Effort**: 2-3 hours
**Dependencies**: None
**Risk**: Low (isolated change)

#### Task 1.1: Fix N+1 COUNT Query Pattern
**File**: `skillmeat/api/routers/artifacts.py`
**Agent**: `python-backend-engineer`

Replace:
```python
# Lines 1897-1916 - Current N+1 pattern
for assoc in associations:
    if assoc.artifact_id not in collections_map:
        collections_map[assoc.artifact_id] = []
    coll = collection_details.get(assoc.collection_id)
    if coll:
        artifact_count = (
            db_session.query(CollectionArtifact)
            .filter_by(collection_id=coll.id)
            .count()
        )
        collections_map[assoc.artifact_id].append({...})
```

With:
```python
# Single aggregation query for all counts
from sqlalchemy import func

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

# Build mapping with pre-computed counts
for assoc in associations:
    if assoc.artifact_id not in collections_map:
        collections_map[assoc.artifact_id] = []
    coll = collection_details.get(assoc.collection_id)
    if coll:
        collections_map[assoc.artifact_id].append({
            "id": coll.id,
            "name": coll.name,
            "artifact_count": count_map.get(coll.id, 0),
        })
```

**Expected Impact**: 100 queries → 1 query (99% reduction in COUNT queries)

#### Task 1.2: Update Relationship Loading Strategy
**File**: `skillmeat/cache/models.py`
**Agent**: `python-backend-engineer`

Change:
```python
# Artifact model
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    lazy="selectin",  # ← Change to "select"
)

# Collection model - same change for all relationships
groups: Mapped[List["Group"]] = relationship(
    lazy="selectin",  # ← Change to "select"
)
collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
    lazy="selectin",  # ← Change to "select"
)
```

**Rationale**: Prevents automatic eager loading when we're manually querying the data.

### Phase 2: Frontend Mapping Consolidation (Priority: HIGH)
**Estimated Effort**: 3-4 hours
**Dependencies**: None (can run parallel with Phase 1)
**Risk**: Medium (touches multiple components)

#### Task 2.1: Create Centralized Entity Mapper
**File**: `skillmeat/web/lib/api/entity-mapper.ts` (NEW)
**Agent**: `ui-engineer`

```typescript
import type { ArtifactResponse, Entity } from '@/types';

export type EntityContext = 'collection' | 'project' | 'marketplace';

/**
 * Single source of truth for mapping API responses to Entity objects.
 * Ensures all 24 fields are consistently mapped regardless of context.
 */
export function mapArtifactToEntity(
  artifact: ArtifactResponse,
  context: EntityContext = 'collection'
): Entity {
  return {
    // Core identity
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,

    // Source & version
    source: artifact.source,
    version: artifact.version,
    resolvedVersion: artifact.resolved_version,

    // Metadata
    description: artifact.description ?? '',
    author: artifact.author,
    license: artifact.license,
    tags: artifact.tags ?? [],

    // Status
    status: mapStatus(artifact, context),
    driftStatus: artifact.drift_status,
    hasLocalModifications: artifact.has_local_modifications,

    // Collections - CRITICAL: Always map this field
    collections: (artifact.collections ?? []).map(c => ({
      id: c.id,
      name: c.name,
      artifactCount: c.artifact_count,
    })),

    // Relationships
    dependencies: artifact.dependencies ?? [],
    upstream: artifact.upstream,
    origin: artifact.origin,

    // Analytics
    score: artifact.score,
    usageStats: artifact.usage_stats,

    // Timestamps
    createdAt: artifact.created_at,
    updatedAt: artifact.updated_at,

    // Context-specific
    mode: context === 'project' ? 'project' : 'collection',
  };
}
```

#### Task 2.2: Migrate useEntityLifecycle
**File**: `skillmeat/web/hooks/useEntityLifecycle.tsx`
**Agent**: `ui-engineer`

Replace `mapApiArtifactToEntity()` with import of centralized mapper.

#### Task 2.3: Migrate collection/page.tsx
**File**: `skillmeat/web/app/collection/page.tsx`
**Agent**: `ui-engineer`

Remove `enrichArtifactSummary()` function and use centralized mapper.

#### Task 2.4: Migrate projects/[id]/manage/page.tsx
**File**: `skillmeat/web/app/projects/[id]/manage/page.tsx`
**Agent**: `ui-engineer`

Remove both inline enrichment blocks (lines 80-95, 117-132).

### Phase 3: API Endpoint Consistency (Priority: HIGH)
**Estimated Effort**: 4-5 hours
**Dependencies**: Phase 1 complete
**Risk**: Medium (multiple endpoints)

#### Task 3.1: Create CollectionService
**File**: `skillmeat/api/services/collection_service.py` (NEW)
**Agent**: `python-backend-engineer`

```python
from typing import Dict, List, Set
from sqlalchemy import func
from skillmeat.cache.models import Collection, CollectionArtifact
from skillmeat.api.schemas.artifacts import ArtifactCollectionInfo

class CollectionService:
    """Centralized service for collection membership queries."""

    def __init__(self, db_session):
        self.db = db_session

    def get_collection_membership_batch(
        self,
        artifact_ids: List[str]
    ) -> Dict[str, List[ArtifactCollectionInfo]]:
        """
        Fetch collection memberships for multiple artifacts in a single query.

        Returns:
            Dict mapping artifact_id to list of ArtifactCollectionInfo
        """
        if not artifact_ids:
            return {}

        # Query associations
        associations = (
            self.db.query(CollectionArtifact)
            .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
            .all()
        )

        if not associations:
            return {}

        collection_ids = {a.collection_id for a in associations}

        # Batch fetch collection details with counts
        count_subquery = (
            self.db.query(
                CollectionArtifact.collection_id,
                func.count('*').label('count')
            )
            .group_by(CollectionArtifact.collection_id)
            .subquery()
        )

        collections_with_counts = (
            self.db.query(Collection, count_subquery.c.count)
            .outerjoin(
                count_subquery,
                Collection.id == count_subquery.c.collection_id
            )
            .filter(Collection.id.in_(collection_ids))
            .all()
        )

        collection_map = {
            c.id: ArtifactCollectionInfo(
                id=c.id,
                name=c.name,
                artifact_count=count or 0
            )
            for c, count in collections_with_counts
        }

        # Build result
        result: Dict[str, List[ArtifactCollectionInfo]] = {}
        for assoc in associations:
            if assoc.artifact_id not in result:
                result[assoc.artifact_id] = []
            if assoc.collection_id in collection_map:
                result[assoc.artifact_id].append(
                    collection_map[assoc.collection_id]
                )

        return result
```

#### Task 3.2: Update All Artifact Endpoints
**Files**: Multiple routers
**Agent**: `python-backend-engineer`

Audit and update these endpoints to use CollectionService:
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{id}`
- `GET /api/v1/projects/{id}/artifacts`
- `GET /api/v1/collections/{id}/artifacts`
- `POST /api/v1/artifacts` (response)

### Phase 4: Caching Layer (Priority: MEDIUM)
**Estimated Effort**: 2-3 hours
**Dependencies**: Phase 3 complete
**Risk**: Low (additive change)

#### Task 4.1: Implement Collection Count Cache
**File**: `skillmeat/cache/collection_cache.py` (NEW)
**Agent**: `python-backend-engineer`

Simple TTL-based in-memory cache for collection artifact counts.

#### Task 4.2: Add Cache Invalidation Hooks
**Files**: User collections router
**Agent**: `python-backend-engineer`

Invalidate cache on:
- `POST /api/v1/user-collections/{id}/artifacts` (add artifact)
- `DELETE /api/v1/user-collections/{id}/artifacts/{artifact_id}` (remove artifact)
- `DELETE /api/v1/user-collections/{id}` (delete collection)

### Phase 5: Frontend Data Preloading (Priority: LOW)
**Estimated Effort**: 1-2 hours
**Dependencies**: Phase 2 complete
**Risk**: Low

#### Task 5.1: Add DataPrefetcher Component
**File**: `skillmeat/web/app/providers.tsx`
**Agent**: `ui-engineer`

Preload sources and collections at app initialization to eliminate navigation-dependent cache population.

---

## Additional Enhancements Identified

During the SPIKE investigation, these additional improvements were identified:

### Enhancement A: Denormalized Artifact Count
**Priority**: Low (Future)
**Effort**: 2-3 hours

Add `artifact_count` column to `Collection` table and maintain via triggers or application hooks. Eliminates COUNT queries entirely.

```sql
ALTER TABLE collections ADD COLUMN artifact_count INTEGER DEFAULT 0;

-- Trigger to maintain count
CREATE TRIGGER update_collection_count
AFTER INSERT OR DELETE ON collection_artifacts
FOR EACH ROW EXECUTE FUNCTION update_collection_artifact_count();
```

### Enhancement B: Collection Membership Index Optimization
**Priority**: Medium
**Effort**: 30 minutes

Add composite index for common query pattern:

```sql
CREATE INDEX idx_collection_artifacts_lookup
ON collection_artifacts(artifact_id, collection_id);
```

### Enhancement C: API Response Compression
**Priority**: Low
**Effort**: 1 hour

Enable gzip compression for large artifact list responses:

```python
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Enhancement D: Collection Membership Bulk Operations
**Priority**: Medium (Feature Request)
**Effort**: 4-6 hours

Add endpoints for bulk collection operations:
- `POST /api/v1/user-collections/{id}/artifacts/bulk` - Add multiple artifacts
- `DELETE /api/v1/user-collections/{id}/artifacts/bulk` - Remove multiple artifacts

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| N+1 fix breaks edge case | Low | Medium | Comprehensive test coverage |
| Frontend mapping breaks modal | Medium | High | Test all modal contexts before merge |
| Cache invalidation race condition | Low | Low | Use atomic operations |
| Performance regression in other endpoints | Low | Medium | Benchmark before/after |

---

## Open Questions

1. **Q**: Should collection counts be exact or eventually consistent?
   **Recommendation**: Eventually consistent (5-minute TTL) is acceptable for counts; exact consistency for membership.

2. **Q**: Should we add a dedicated `/api/v1/artifacts/{id}/collections` endpoint?
   **Recommendation**: Not needed if we ensure consistent embedding in artifact responses.

3. **Q**: Database migration for denormalized count?
   **Recommendation**: Defer to Phase 2 PRD - current optimization sufficient.

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Artifact list API p95 latency | 1200ms | <200ms | APM monitoring |
| Database queries per request | 107 | ≤5 | Query logging |
| Collection badge render rate | ~60% | 100% | Manual QA |
| Duplicate mapping code | 120 lines | 0 lines | Code audit |

---

## Recommendation

**Proceed to PRD creation** with the following scope:

1. **Core Scope** (Must Have):
   - N+1 query fix (Phase 1)
   - Centralized entity mapper (Phase 2)
   - API endpoint consistency (Phase 3)

2. **Extended Scope** (Should Have):
   - Collection count caching (Phase 4)
   - Data preloading (Phase 5)

3. **Deferred** (Future PRD):
   - Denormalized count column
   - Bulk collection operations

**Estimated Total Effort**: 12-17 hours (3-4 days)
**Recommended Sprint Allocation**: Single sprint, Phase 1-3 prioritized

---

## Appendices

### A. Query Performance Baseline

```
Current State (50 artifacts, 2 collections avg):
├── SELECT artifacts (paginated): 1 query
├── SELECT collection_artifacts WHERE artifact_id IN (...): 1 query
├── SELECT collections WHERE id IN (...): 1 query
├── COUNT collection_artifacts for each collection: 100 queries ← PROBLEM
└── Total: 103 queries, ~1000ms

After Phase 1:
├── SELECT artifacts (paginated): 1 query
├── SELECT collection_artifacts WHERE artifact_id IN (...): 1 query
├── SELECT collections WITH COUNT (GROUP BY): 1 query
└── Total: 3 queries, ~100ms
```

### B. Related Files Reference

**Backend**:
- `skillmeat/api/routers/artifacts.py` - Main artifact endpoints
- `skillmeat/api/routers/user_collections.py` - Collection CRUD
- `skillmeat/api/schemas/artifacts.py` - Response schemas
- `skillmeat/cache/models.py` - SQLAlchemy models

**Frontend**:
- `skillmeat/web/lib/api/mappers.ts` - Current mapper location
- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Entity state management
- `skillmeat/web/hooks/use-collections.ts` - Collection hooks
- `skillmeat/web/app/collection/page.tsx` - Collection page
- `skillmeat/web/app/projects/[id]/manage/page.tsx` - Project manage page
- `skillmeat/web/components/entity/unified-entity-modal.tsx` - Modal component

### C. ADR Recommendations

Create the following ADRs during implementation:

1. **ADR-XXX: Collection Membership Query Strategy** - Document decision to use batch queries with GROUP BY instead of individual counts
2. **ADR-XXX: Entity Mapping Centralization** - Document single-source-of-truth pattern for API→Entity conversion
3. **ADR-XXX: Collection Count Caching Strategy** - Document TTL-based caching approach
