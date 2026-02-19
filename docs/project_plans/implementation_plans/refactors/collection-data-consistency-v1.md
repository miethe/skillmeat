---
title: 'Implementation Plan: Collection Data Consistency & Performance Optimization'
description: Phased implementation to fix N+1 query performance issues, consolidate
  frontend mapping, and ensure consistent collection data across all API endpoints
audience:
- ai-agents
- developers
tags:
- implementation
- refactor
- performance
- api
- frontend
- caching
created: 2026-01-30
updated: 2026-01-30
category: refactors
status: inferred_complete
complexity: Medium
total_effort: 12-17 hours
related:
- /docs/spikes/SPIKE-collection-data-consistency.md
- /docs/project_plans/reports/artifact-modal-architecture-analysis.md
schema_version: 2
doc_type: implementation_plan
feature_slug: collection-data-consistency
prd_ref: null
---
# Implementation Plan: Collection Data Consistency & Performance Optimization

**Plan ID**: `IMPL-2026-01-30-COLLECTION-DATA-CONSISTENCY`
**Date**: 2026-01-30
**Author**: Claude Opus 4.5 (AI-generated)
**Related Documents**:
- **SPIKE**: `/docs/spikes/SPIKE-collection-data-consistency.md`
- **Architecture Analysis**: `/docs/project_plans/reports/artifact-modal-architecture-analysis.md` (Recommendation 4)

**Complexity**: Medium
**Total Estimated Effort**: 12-17 hours (3-4 days)
**Target Timeline**: Single sprint

---

## Executive Summary

This implementation plan addresses a compound problem affecting collection data across the SkillMeat application: N+1 query patterns causing 100+ database queries per page load, inconsistent Entity mapping across frontend components, and missing caching infrastructure. The plan delivers 10x API response improvement (1200ms to 120ms), 96% database query reduction (107 to 4 queries), and consolidates 3 duplicate mapping locations into a single source of truth.

---

## Implementation Strategy

### Architecture Sequence

This refactor touches multiple layers but follows a specific optimization sequence:

1. **Performance Layer** - Fix N+1 queries in artifacts router (immediate impact)
2. **Frontend Mapping Layer** - Centralize Entity mappers (consistency)
3. **Service Layer** - Create CollectionService abstraction (maintainability)
4. **Caching Layer** - Add TTL-based count cache (sustained performance)
5. **Preloading Layer** - Frontend data prefetching (UX polish)

### Parallel Work Opportunities

| Parallel Track A | Parallel Track B |
|------------------|------------------|
| Phase 1: Backend N+1 fix | Phase 2: Frontend mapping consolidation |
| Phase 3: CollectionService | Phase 5: Data preloading (after Phase 2) |

**Note**: Phases 1 and 2 have NO dependencies and can execute in parallel.

### Critical Path

```
Phase 1 (N+1 fix) → Phase 3 (CollectionService) → Phase 4 (Caching)
```

Phase 2 is independent. Phase 5 depends only on Phase 2.

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Artifact list API p95 latency | 1200ms | <200ms | APM/logging |
| Database queries per request | 107 | ≤5 | Query logging |
| Collection badge render rate | ~60% | 100% | Manual QA |
| Duplicate mapping code | 3 locations, 120 lines | 1 location | Code audit |

---

## Phase Breakdown

### Phase 1: Critical Performance Fix

**Priority**: CRITICAL
**Duration**: 2-3 hours
**Dependencies**: None
**Risk**: Low (isolated change)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------|--------------|
| TASK-1.1 | Fix N+1 COUNT Query Pattern | Replace per-artifact COUNT queries with single aggregation query using GROUP BY in `artifacts.py:1897-1916` | Single COUNT query replaces 100+ individual queries; API response time <200ms for 50 artifacts | 1.5h | `python-backend-engineer` | None |
| TASK-1.2 | Update Relationship Loading Strategy | Change `lazy="selectin"` to `lazy="select"` on Artifact.collections, Collection.groups, Collection.collection_artifacts in `cache/models.py` | Relationships load on-demand only; no duplicate eager loading when manual queries used | 0.5h | `python-backend-engineer` | None |
| TASK-1.3 | Add Query Performance Logging | Add timing logs for artifact list endpoint to validate improvement | Query count and timing visible in logs for monitoring | 0.5h | `python-backend-engineer` | TASK-1.1 |

#### Implementation Details

**TASK-1.1: Fix N+1 COUNT Query Pattern**

File: `skillmeat/api/routers/artifacts.py`

Replace lines 1897-1916 (current N+1 pattern):
```python
# BEFORE: N+1 pattern - COUNT query per collection per artifact
for assoc in associations:
    if assoc.artifact_id not in collections_map:
        collections_map[assoc.artifact_id] = []
    coll = collection_details.get(assoc.collection_id)
    if coll:
        artifact_count = (
            db_session.query(CollectionArtifact)
            .filter_by(collection_id=coll.id)
            .count()  # Query inside loop!
        )
        collections_map[assoc.artifact_id].append({...})
```

With:
```python
# AFTER: Single aggregation query for all counts
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

**TASK-1.2: Update Relationship Loading Strategy**

File: `skillmeat/cache/models.py`

```python
# Artifact model - change lazy strategy
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    lazy="select",  # Changed from "selectin"
)

# Collection model - change lazy strategy
groups: Mapped[List["Group"]] = relationship(
    lazy="select",  # Changed from "selectin"
)
collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
    lazy="select",  # Changed from "selectin"
)
```

#### Phase 1 Quality Gates

- [ ] API response time for 50-artifact list <200ms (p95)
- [ ] Database queries per request ≤5 (verified via logging)
- [ ] Existing artifact list tests pass
- [ ] No regression in artifact detail endpoint
- [ ] Performance improvement documented in commit message

---

### Phase 2: Frontend Mapping Consolidation

**Priority**: HIGH
**Duration**: 3-4 hours
**Dependencies**: None (can run parallel with Phase 1)
**Risk**: Medium (touches multiple components)
**Assigned Subagent(s)**: `ui-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------|--------------|
| TASK-2.1 | Create Centralized Entity Mapper | Create `lib/api/entity-mapper.ts` with `mapArtifactToEntity()` function covering all 24 Entity fields | All 24 fields mapped; TypeScript compiles; exports EntityContext type | 1.5h | `ui-engineer` | None |
| TASK-2.2 | Migrate useEntityLifecycle | Replace `mapApiArtifactToEntity()` in `hooks/useEntityLifecycle.tsx` with centralized mapper import | Hook uses centralized mapper; all existing hook tests pass | 0.5h | `ui-engineer` | TASK-2.1 |
| TASK-2.3 | Migrate collection/page.tsx | Remove `enrichArtifactSummary()` function and use centralized mapper | Collection page shows collection badges; no inline mapping code | 0.5h | `ui-engineer` | TASK-2.1 |
| TASK-2.4 | Migrate projects/[id]/manage/page.tsx | Remove both inline enrichment blocks (lines 80-95, 117-132) | Project manage page uses centralized mapper; no inline mapping | 0.5h | `ui-engineer` | TASK-2.1 |
| TASK-2.5 | Add Unit Tests for Entity Mapper | Create tests for `mapArtifactToEntity()` covering all contexts and edge cases | >90% coverage on entity-mapper.ts; tests for null/undefined handling | 0.5h | `ui-engineer` | TASK-2.1 |

#### Implementation Details

**TASK-2.1: Create Centralized Entity Mapper**

File: `skillmeat/web/lib/api/entity-mapper.ts` (NEW)

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

function mapStatus(artifact: ArtifactResponse, context: EntityContext): string {
  // Context-aware status mapping logic
  if (context === 'project') {
    return artifact.deployment_status ?? artifact.status ?? 'unknown';
  }
  return artifact.status ?? 'available';
}

/**
 * Batch mapping utility for lists of artifacts.
 */
export function mapArtifactsToEntities(
  artifacts: ArtifactResponse[],
  context: EntityContext = 'collection'
): Entity[] {
  return artifacts.map(a => mapArtifactToEntity(a, context));
}
```

**TASK-2.3: Migrate collection/page.tsx**

File: `skillmeat/web/app/collection/page.tsx`

Remove:
```typescript
// DELETE this function entirely
function enrichArtifactSummary(artifact: ArtifactSummary): Entity {
  return {
    id: artifact.id,
    name: artifact.name,
    type: artifact.type,
    // ... only 4 fields mapped, missing 20 including collections!
  };
}
```

Replace with:
```typescript
import { mapArtifactToEntity } from '@/lib/api/entity-mapper';

// In component:
const entities = artifacts.map(a => mapArtifactToEntity(a, 'collection'));
```

#### Phase 2 Quality Gates

- [ ] Single mapper file exports `mapArtifactToEntity` and `mapArtifactsToEntities`
- [ ] All 24 Entity fields mapped correctly
- [ ] Collection badges visible on /collection page
- [ ] Collection badges visible on /projects/[id]/manage page
- [ ] No TypeScript errors
- [ ] Entity mapper unit tests pass with >90% coverage
- [ ] Zero instances of `enrichArtifactSummary` or inline mapping remain

---

### Phase 3: API Endpoint Consistency (CollectionService)

**Priority**: HIGH
**Duration**: 4-5 hours
**Dependencies**: Phase 1 complete
**Risk**: Medium (multiple endpoints)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------|--------------|
| TASK-3.1 | Create CollectionService Class | Create `api/services/collection_service.py` with `get_collection_membership_batch()` method | Service class exists; method accepts artifact_ids and returns Dict[str, List[ArtifactCollectionInfo]] | 2h | `python-backend-engineer` | TASK-1.1 |
| TASK-3.2 | Create Services __init__.py | Create `api/services/__init__.py` with proper exports | CollectionService importable from `skillmeat.api.services` | 0.25h | `python-backend-engineer` | TASK-3.1 |
| TASK-3.3 | Update GET /api/v1/artifacts | Refactor artifacts list endpoint to use CollectionService | Endpoint returns consistent collections array; uses batch query | 0.5h | `python-backend-engineer` | TASK-3.1 |
| TASK-3.4 | Update GET /api/v1/artifacts/{id} | Refactor artifact detail endpoint to use CollectionService | Single artifact includes collections array | 0.25h | `python-backend-engineer` | TASK-3.1 |
| TASK-3.5 | Update GET /api/v1/projects/{id}/artifacts | Refactor project artifacts endpoint to use CollectionService | Project artifact list includes collection membership | 0.5h | `python-backend-engineer` | TASK-3.1 |
| TASK-3.6 | Update GET /api/v1/collections/{id}/artifacts | Refactor collection artifacts endpoint to use CollectionService | Collection artifact list is self-consistent | 0.25h | `python-backend-engineer` | TASK-3.1 |
| TASK-3.7 | Add CollectionService Unit Tests | Create tests for CollectionService methods | >80% coverage; tests batch queries, empty inputs, edge cases | 1h | `python-backend-engineer` | TASK-3.1 |

#### Implementation Details

**TASK-3.1: Create CollectionService Class**

File: `skillmeat/api/services/collection_service.py` (NEW)

```python
"""Collection service for centralized collection membership queries."""

from typing import Dict, List, Set
from sqlalchemy import func
from sqlalchemy.orm import Session

from skillmeat.cache.models import Collection, CollectionArtifact
from skillmeat.api.schemas.artifacts import ArtifactCollectionInfo


class CollectionService:
    """Centralized service for collection membership queries."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_collection_membership_batch(
        self,
        artifact_ids: List[str]
    ) -> Dict[str, List[ArtifactCollectionInfo]]:
        """
        Fetch collection memberships for multiple artifacts in a single query.

        Args:
            artifact_ids: List of artifact IDs to query

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
            return {aid: [] for aid in artifact_ids}

        collection_ids = {a.collection_id for a in associations}

        # Batch fetch collection details with counts in single query
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

        # Build result - ensure all input artifact_ids have entries
        result: Dict[str, List[ArtifactCollectionInfo]] = {
            aid: [] for aid in artifact_ids
        }
        for assoc in associations:
            if assoc.collection_id in collection_map:
                result[assoc.artifact_id].append(
                    collection_map[assoc.collection_id]
                )

        return result

    def get_collection_membership_single(
        self,
        artifact_id: str
    ) -> List[ArtifactCollectionInfo]:
        """
        Convenience method for single artifact lookup.

        Args:
            artifact_id: Single artifact ID

        Returns:
            List of ArtifactCollectionInfo for the artifact
        """
        result = self.get_collection_membership_batch([artifact_id])
        return result.get(artifact_id, [])
```

**TASK-3.2: Create Services __init__.py**

File: `skillmeat/api/services/__init__.py` (NEW)

```python
"""API services layer."""

from .collection_service import CollectionService

__all__ = ["CollectionService"]
```

#### Phase 3 Quality Gates

- [ ] CollectionService class created with batch and single methods
- [ ] All artifact-returning endpoints use CollectionService
- [ ] No N+1 queries in any endpoint (verified via query logging)
- [ ] API responses include consistent `collections` array structure
- [ ] CollectionService unit tests achieve >80% coverage
- [ ] No regression in endpoint response schemas

---

### Phase 4: Caching Layer

**Priority**: MEDIUM
**Duration**: 2-3 hours
**Dependencies**: Phase 3 complete
**Risk**: Low (additive change)
**Assigned Subagent(s)**: `python-backend-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------|--------------|
| TASK-4.1 | Implement Collection Count Cache | Create `cache/collection_cache.py` with TTL-based in-memory cache for collection artifact counts | Cache class with get_counts(), invalidate(), and 5-minute TTL | 1h | `python-backend-engineer` | TASK-3.1 |
| TASK-4.2 | Integrate Cache with CollectionService | Update CollectionService to use cache for count lookups | Cache hit rate logged; fallback to DB on miss | 0.5h | `python-backend-engineer` | TASK-4.1 |
| TASK-4.3 | Add Cache Invalidation on Add Artifact | Invalidate cache on `POST /api/v1/user-collections/{id}/artifacts` | Cache invalidated when artifact added to collection | 0.25h | `python-backend-engineer` | TASK-4.1 |
| TASK-4.4 | Add Cache Invalidation on Remove Artifact | Invalidate cache on `DELETE /api/v1/user-collections/{id}/artifacts/{artifact_id}` | Cache invalidated when artifact removed from collection | 0.25h | `python-backend-engineer` | TASK-4.1 |
| TASK-4.5 | Add Cache Invalidation on Delete Collection | Invalidate cache on `DELETE /api/v1/user-collections/{id}` | Cache invalidated when collection deleted | 0.25h | `python-backend-engineer` | TASK-4.1 |
| TASK-4.6 | Add Cache Unit Tests | Create tests for cache behavior including TTL expiration | Tests cover get, invalidate, TTL expiry, concurrent access | 0.5h | `python-backend-engineer` | TASK-4.1 |

#### Implementation Details

**TASK-4.1: Implement Collection Count Cache**

File: `skillmeat/cache/collection_cache.py` (NEW)

```python
"""TTL-based cache for collection artifact counts."""

import time
from threading import Lock
from typing import Dict, Set, Tuple, Optional


class CollectionCountCache:
    """
    Thread-safe TTL-based cache for collection artifact counts.

    Counts are eventually consistent with 5-minute staleness window.
    """

    DEFAULT_TTL = 300  # 5 minutes

    def __init__(self, ttl: int = DEFAULT_TTL):
        self._cache: Dict[str, Tuple[int, float]] = {}  # id -> (count, timestamp)
        self._ttl = ttl
        self._lock = Lock()

    def get_counts(
        self,
        collection_ids: Set[str]
    ) -> Tuple[Dict[str, int], Set[str]]:
        """
        Get cached counts for collections.

        Args:
            collection_ids: Set of collection IDs to lookup

        Returns:
            Tuple of (cached_counts, missing_ids)
            - cached_counts: Dict of collection_id -> count for cache hits
            - missing_ids: Set of collection_ids not in cache or expired
        """
        now = time.time()
        cached: Dict[str, int] = {}
        missing: Set[str] = set()

        with self._lock:
            for cid in collection_ids:
                if cid in self._cache:
                    count, ts = self._cache[cid]
                    if now - ts < self._ttl:
                        cached[cid] = count
                    else:
                        # Expired
                        del self._cache[cid]
                        missing.add(cid)
                else:
                    missing.add(cid)

        return cached, missing

    def set_counts(self, counts: Dict[str, int]) -> None:
        """
        Set counts in cache.

        Args:
            counts: Dict of collection_id -> artifact_count
        """
        now = time.time()
        with self._lock:
            for cid, count in counts.items():
                self._cache[cid] = (count, now)

    def invalidate(self, collection_id: str) -> None:
        """
        Invalidate cache for a specific collection.

        Args:
            collection_id: Collection ID to invalidate
        """
        with self._lock:
            self._cache.pop(collection_id, None)

    def invalidate_all(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring."""
        with self._lock:
            return {
                "size": len(self._cache),
                "ttl": self._ttl,
            }


# Singleton instance
_cache_instance: Optional[CollectionCountCache] = None


def get_collection_count_cache() -> CollectionCountCache:
    """Get singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CollectionCountCache()
    return _cache_instance
```

#### Phase 4 Quality Gates

- [ ] Cache class created with thread-safe operations
- [ ] TTL expiration working (verified via tests)
- [ ] Cache invalidation triggered on add/remove/delete operations
- [ ] Cache hit rate visible in logs
- [ ] No stale data visible after invalidation events
- [ ] Cache unit tests achieve >80% coverage

---

### Phase 5: Frontend Data Preloading

**Priority**: LOW
**Duration**: 1-2 hours
**Dependencies**: Phase 2 complete
**Risk**: Low (additive UX improvement)
**Assigned Subagent(s)**: `ui-engineer`

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------|--------------|
| TASK-5.1 | Create DataPrefetcher Component | Create prefetcher component that loads sources and collections at app initialization | Component mounts in providers.tsx; prefetches on app load | 0.5h | `ui-engineer` | TASK-2.5 |
| TASK-5.2 | Integrate with QueryClient | Configure prefetch queries with staleTime to avoid redundant fetches | Prefetched data available immediately on navigation; no duplicate requests | 0.5h | `ui-engineer` | TASK-5.1 |
| TASK-5.3 | Add Loading State Indicator | Optional: Add subtle loading indicator during initial prefetch | Users see prefetch status (can be silent) | 0.25h | `ui-engineer` | TASK-5.1 |
| TASK-5.4 | Document Prefetch Strategy | Add comments explaining prefetch rationale and configuration | Future developers understand prefetch behavior | 0.25h | `ui-engineer` | TASK-5.1 |

#### Implementation Details

**TASK-5.1: Create DataPrefetcher Component**

File: `skillmeat/web/app/providers.tsx` (MODIFY)

```typescript
'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

/**
 * Prefetches commonly needed data at app initialization.
 * Eliminates navigation-dependent cache population for better UX.
 */
function DataPrefetcher() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Prefetch sources list - used across collection and project pages
    queryClient.prefetchQuery({
      queryKey: ['sources'],
      queryFn: async () => {
        const response = await fetch('/api/v1/sources');
        return response.json();
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
    });

    // Prefetch user collections - used for collection badges
    queryClient.prefetchQuery({
      queryKey: ['user-collections'],
      queryFn: async () => {
        const response = await fetch('/api/v1/user-collections');
        return response.json();
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
    });
  }, [queryClient]);

  return null; // No UI - background operation
}

// Add to Providers component:
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <DataPrefetcher />
      {children}
    </QueryClientProvider>
  );
}
```

#### Phase 5 Quality Gates

- [ ] DataPrefetcher component created and mounted in providers
- [ ] Sources and collections prefetched on app load
- [ ] No duplicate network requests on navigation
- [ ] Prefetch does not block initial render
- [ ] StaleTime configured appropriately (5 minutes)

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| N+1 fix breaks edge case | Low | Medium | Comprehensive test coverage; validate with existing tests before merge |
| Frontend mapping breaks modal | Medium | High | Test all modal contexts (collection, project, marketplace) before merge |
| Cache invalidation race condition | Low | Low | Use thread-safe operations with Lock; test concurrent access |
| Performance regression in other endpoints | Low | Medium | Benchmark all artifact endpoints before/after changes |

### Schedule Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Phase 1 and 2 parallel conflicts | Low | Low | Separate files; no merge conflicts expected |
| CollectionService integration complexity | Medium | Medium | Create service first, then integrate incrementally |
| Scope creep to additional enhancements | Medium | Medium | Defer Enhancement A-D to future PRD |

---

## Resource Requirements

### Subagent Assignments

| Agent | Primary Phases | Estimated Hours |
|-------|---------------|-----------------|
| `python-backend-engineer` | Phase 1, 3, 4 | 8-11 hours |
| `ui-engineer` | Phase 2, 5 | 4-6 hours |

### Key Files Reference

**Backend**:
- `skillmeat/api/routers/artifacts.py` - N+1 fix location
- `skillmeat/cache/models.py` - Relationship loading changes
- `skillmeat/api/services/collection_service.py` (NEW)
- `skillmeat/cache/collection_cache.py` (NEW)

**Frontend**:
- `skillmeat/web/lib/api/entity-mapper.ts` (NEW)
- `skillmeat/web/lib/api/mappers.ts` - Existing mapper (reference)
- `skillmeat/web/hooks/useEntityLifecycle.tsx` - Mapper migration
- `skillmeat/web/app/collection/page.tsx` - Remove enrichArtifactSummary
- `skillmeat/web/app/projects/[id]/manage/page.tsx` - Remove inline mapping
- `skillmeat/web/app/providers.tsx` - Add DataPrefetcher

---

## Deferred Enhancements

The following enhancements were identified in the SPIKE but deferred to a future PRD:

| Enhancement | Effort | Rationale for Deferral |
|-------------|--------|------------------------|
| A: Denormalized artifact_count column | 2-3h | Requires migration; current optimization sufficient |
| B: Collection membership index | 30min | Can add if performance still insufficient |
| C: API response compression (gzip) | 1h | Additive; not critical path |
| D: Bulk collection operations | 4-6h | Feature request; separate scope |

---

## Post-Implementation

### Monitoring

- Enable query timing logs for artifact endpoints
- Track cache hit rate for collection counts
- Monitor p95 latency for artifact list API

### Validation Checklist

- [ ] All acceptance criteria met per task
- [ ] All quality gates passed per phase
- [ ] No P0/P1 bugs in first week post-merge
- [ ] Success metrics achieved (10x response improvement)

### ADR Recommendations

Create the following ADRs during implementation:

1. **ADR: Collection Membership Query Strategy** - Document batch query with GROUP BY pattern
2. **ADR: Entity Mapping Centralization** - Document single-source-of-truth pattern
3. **ADR: Collection Count Caching Strategy** - Document TTL-based caching approach

---

## Progress Tracking

See `.claude/progress/collection-data-consistency/` for phase progress files.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-01-30
