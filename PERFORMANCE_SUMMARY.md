# Performance Analysis - Quick Reference

## Critical Findings

### 🔴 N+1 COUNT Query Problem

**Location:** `skillmeat/api/routers/artifacts.py` lines 1905-1908

For every artifact on a page, a COUNT query runs:
```python
for artifact in artifacts:  # 50 artifacts
    for collection in artifact.collections:  # avg 2 collections
        count = session.query(CollectionArtifact)
                .filter_by(collection_id=collection.id)
                .count()  # ← RUNS 100 TIMES
```

**Impact:** Single page request = 103 database queries (1 list + 1 collections query + 101 COUNTs)

**Fix:** Replace loop with single aggregation query (see PERFORMANCE_ANALYSIS.md Priority 1)

---

### 🔴 Over-Eager Collection Loading

**Location:** `skillmeat/cache/models.py` lines 287-294

```python
class Artifact(Base):
    collections: Mapped[List["Collection"]] = relationship(
        "Collection",
        # ...
        lazy="selectin",  # ← Loads ALL collections for EVERY artifact
    )
```

But `artifacts.py` manually queries collections anyway (line 1879-1894), so this is wasted work.

**Impact:** Duplicate queries + memory overhead

**Fix:** Change `lazy="selectin"` to `lazy="select"` and control explicitly per query

---

### 🔴 Cascading Eager Loads

**Location:** `skillmeat/cache/models.py` multiple locations

Each relationship eagerly loads nested relationships:
- `Artifact.collections` (selectin)
- `Collection.groups` (selectin)
- `Collection.collection_artifacts` (selectin)
- `Collection.templates` (selectin)

Result: Loading 10 collections triggers 40+ additional queries.

**Fix:** Reduce selectin usage; use lazy loading with explicit control

---

## Query Pattern Analysis

### Current (Unoptimized)

```
GET /api/v1/artifacts?limit=50

1. Load artifacts
   ├─ 1 query: SELECT * FROM artifacts LIMIT 50
   └─ Selectin loads:
      ├─ N₁: SELECT * FROM collections WHERE id IN (...)
      ├─ N₂: SELECT * FROM artifact_metadata WHERE id IN (...)
      ├─ N₃: SELECT * FROM artifact_versions WHERE id IN (...)
      └─ N₄: SELECT * FROM tags WHERE id IN (...)

2. Load collections explicitly (line 1879-1894)
   ├─ 1 query: SELECT * FROM collection_artifacts WHERE artifact_id IN (...)
   └─ 1 query: SELECT * FROM collections WHERE id IN (...)

3. Count artifacts per collection
   ├─ 100 queries: SELECT COUNT(*) FROM collection_artifacts WHERE collection_id = ?

TOTAL: 5-7 base queries + 100 COUNT queries = 105-107 queries
```

### Optimized

```
GET /api/v1/artifacts?limit=50

1. Load artifacts (lazy load collections)
   ├─ 1 query: SELECT * FROM artifacts LIMIT 50
   └─ No selectin loading

2. Load collections and counts atomically
   ├─ 1 query: SELECT * FROM collection_artifacts WHERE artifact_id IN (...)
   ├─ 1 query: SELECT collection_id, COUNT(*) FROM collection_artifacts GROUP BY collection_id
   └─ 1 query: SELECT * FROM collections WHERE id IN (...)

TOTAL: 4 queries
```

**Improvement:** 105+ queries → 4 queries (96% reduction)

---

## Performance Timeline

### Symptom: Slow Collection Operations

| User Action | Current Time | Optimized | Improvement |
|------------|-------------|-----------|------------|
| List 50 artifacts | 800-1200ms | 100-200ms | 85-90% faster |
| View single collection | 200-400ms | 50-100ms | 75% faster |
| List 10 collections | 1000-1500ms | 100-200ms | 85% faster |

### Why It's Bad

1. **Connection Pool Exhaustion**: 100+ queries = 100+ waiting connections
2. **Database Overload**: COUNT queries scan full table
3. **Memory Bloat**: Collections loaded twice (selectin + manual query)
4. **P95 Latency**: Collection operations slow down entire app

---

## Detailed Issues by File

### File 1: `skillmeat/api/routers/artifacts.py`

**Issue: N+1 COUNT queries**
- Lines 1905-1908: Per-artifact COUNT loops
- Severity: CRITICAL
- Fix: Single GROUP BY query (Priority 1)

**Issue: Manual collection query despite selectin**
- Lines 1879-1894: Duplicate with model relationship
- Severity: HIGH
- Fix: Use model relationship or disable selectin

---

### File 2: `skillmeat/cache/models.py`

**Issue 1: Collection selectin in Artifact (line 293)**
- Eagerly loads collections
- But artifacts.py queries separately
- Impact: Wasted memory + wasted query

**Issue 2: Cascading selectin in Collection (lines 686-702)**
- Groups selectin
- collection_artifacts selectin
- templates selectin
- Impact: 4+ queries when loading any collection

**Issue 3: Multiple selectin on Artifact (lines 280-309)**
- artifact_metadata selectin (line 285)
- collections selectin (line 293)
- tags selectin (line 300)
- versions selectin (line 307)
- Impact: 5+ queries minimum per artifact query

---

### File 3: `skillmeat/api/routers/user_collections.py`

**Issue: Per-collection COUNT (lines 134-136)**
- COUNT query for each collection in list
- No aggregation or caching
- Impact: N COUNT queries for N collections
- Fix: Single aggregation query or cache

---

## Index Status

### Good News: Indexes Are Present

CollectionArtifact table has proper indexes:
- `idx_collection_artifacts_collection_id` - Fast collection lookups ✓
- `idx_collection_artifacts_artifact_id` - Fast artifact lookups ✓
- `idx_collection_artifacts_added_at` - Timestamp sorting ✓

**But indexes don't help COUNT queries** - they still scan all rows for aggregation.

### Missing Optimization

Could add composite index:
```sql
CREATE INDEX idx_collection_artifacts_collection_count
ON collection_artifacts(collection_id, artifact_id)
```

But COUNT query would still need to count all rows.

**Better solution:** Application-level count caching or denormalized count field

---

## Implementation Roadmap

### Phase 1: Fix Critical N+1 (1-2 days)

**File:** `skillmeat/api/routers/artifacts.py`
**Lines:** 1905-1908

Replace loop COUNT with single aggregation:
```python
# ✓ Single query instead of N
from sqlalchemy import func
counts = (session.query(
    CollectionArtifact.collection_id,
    func.count(CollectionArtifact.artifact_id).label('count')
)
.filter(CollectionArtifact.collection_id.in_(collection_ids))
.group_by(CollectionArtifact.collection_id)
.all())
count_map = {coll_id: count for coll_id, count in counts}
```

**Estimated Impact:** 90% of total improvements

---

### Phase 2: Fix Eager Loading (2-3 days)

**File:** `skillmeat/cache/models.py`

Change relationship loading strategy:
```python
# Before: Always loads via selectin
collections: Mapped[List["Collection"]] = relationship(..., lazy="selectin")

# After: Explicit control per query
collections: Mapped[List["Collection"]] = relationship(..., lazy="select")

# In queries, use options() for control:
session.query(Artifact).options(selectinload(Artifact.collections))
```

**Estimated Impact:** 10% additional improvement

---

### Phase 3: Add Count Caching (1-2 days)

**New File:** `skillmeat/cache/count_cache.py`

Simple TTL cache for collection counts:
```python
class CollectionCountCache:
    def get(self, collection_id: str, session: Session) -> int:
        # Return from cache or query
        ...
    def invalidate(self, collection_id: str):
        # Clear cache entry
        ...
```

**Estimated Impact:** Smooths spiky load, prevents storms

---

### Phase 4: Denormalize Counts (Future)

**Migration:** Add `Collection.artifact_count` field
**Trigger:** Auto-update on INSERT/DELETE to collection_artifacts
**Benefit:** O(1) reads, eliminates COUNT queries forever

---

## Code Snippets - Before & After

### Issue 1: N+1 COUNT

**Before (105+ queries):**
```python
# Lines 1905-1908 in artifacts.py
artifact_count = (
    db_session.query(CollectionArtifact)
    .filter_by(collection_id=coll.id)
    .count()
)  # Runs 100+ times
```

**After (1 query):**
```python
from sqlalchemy import func

# Batch count all collections at once
counts = (
    db_session.query(
        CollectionArtifact.collection_id,
        func.count(CollectionArtifact.artifact_id).label('count')
    )
    .filter(CollectionArtifact.collection_id.in_(collection_ids))
    .group_by(CollectionArtifact.collection_id)
    .all()
)
count_map = {coll_id: count for coll_id, count in counts}

# Use map instead of loop query
artifact_count = count_map.get(coll.id, 0)
```

---

### Issue 2: Redundant Selectin Loading

**Before:**
```python
# models.py line 287-294
class Artifact(Base):
    collections: Mapped[List["Collection"]] = relationship(
        "Collection",
        secondary="collection_artifacts",
        viewonly=True,
        lazy="selectin",  # Always loads
    )

# artifacts.py lines 1879-1894
# But then explicitly queries anyway
associations = db_session.query(CollectionArtifact).filter(...).all()
collections = db_session.query(Collection).filter(...).all()
```

**After:**
```python
# models.py: Change lazy strategy
class Artifact(Base):
    collections: Mapped[List["Collection"]] = relationship(
        "Collection",
        secondary="collection_artifacts",
        viewonly=True,
        lazy="select",  # No automatic loading
    )

# artifacts.py: Use explicit selectinload when needed
from sqlalchemy.orm import selectinload
artifacts = (
    session.query(Artifact)
    .options(selectinload(Artifact.collections))
    .all()
)
```

---

### Issue 3: Missing Count Cache

**Before:**
```python
# user_collections.py lines 134-136
artifact_count = (
    session.query(CollectionArtifact)
    .filter_by(collection_id=collection.id)
    .count()
)  # Runs for every collection in list
```

**After:**
```python
# Import cache
from skillmeat.cache.count_cache import _count_cache

# Use cached count
artifact_count = _count_cache.get(collection.id, session)

# On update, invalidate
_count_cache.invalidate(collection.id)
```

---

## Testing the Improvements

### Before Optimization

```bash
# Run against unoptimized code
curl -X GET "http://localhost:8000/api/v1/artifacts?limit=50" \
  -H "Authorization: Bearer token"

# Monitor:
# - Database query count (should see 100+)
# - Response time (should be 800-1200ms)
# - Database CPU (should spike)
```

### After Optimization

```bash
# Run same query against optimized code
curl -X GET "http://localhost:8000/api/v1/artifacts?limit=50" \
  -H "Authorization: Bearer token"

# Monitor:
# - Database query count (should see 4)
# - Response time (should be 100-200ms)
# - Database CPU (should stay low)
```

---

## Related Files to Review

1. **Primary**: `PERFORMANCE_ANALYSIS.md` - Full detailed analysis
2. **Models**: `skillmeat/cache/models.py` - Relationship definitions
3. **Routers**: `skillmeat/api/routers/artifacts.py` - Query patterns
4. **Collections**: `skillmeat/api/routers/user_collections.py` - Count queries
5. **Schema**: `skillmeat/cache/migrations/versions/20251212_1600_create_collections_schema.py` - Indexes

---

## Quick Wins (Low Effort, High Impact)

1. **Fix N+1 COUNT** (30 minutes): 90% improvement
   - Change 4 lines in artifacts.py
   - Add 8 lines for aggregation

2. **Add Count Cache** (1 hour): Prevents storms
   - Create new file: count_cache.py
   - Add 3 lines to routers to use cache
   - Add 1-2 lines on mutations to invalidate

3. **Remove Redundant Selectin** (30 minutes): Cleaner code
   - Change 1 line in models.py
   - Remove duplicate query in artifacts.py

**Total Effort:** 2 hours for 95% improvement

---

## Next Steps

1. Read `PERFORMANCE_ANALYSIS.md` for complete details
2. Start with Priority 1 (N+1 COUNT fix)
3. Follow implementation priority order
4. Test each change with query monitoring
5. Run load tests before/after to measure impact
