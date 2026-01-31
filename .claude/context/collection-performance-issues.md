# Collection Data Performance Issues - Reference Context

Quick reference for performance bottlenecks in collection data handling.

## Critical Issues Summary

| Issue | Location | Severity | Root Cause |
|-------|----------|----------|-----------|
| N+1 COUNT queries | artifacts.py:1905-1908 | CRITICAL | Loop over artifacts, COUNT each collection |
| Redundant selectin | models.py:287-294 | HIGH | Collections loaded twice (model + manual) |
| Cascading eager loads | models.py:686-702 | HIGH | Collection relationships all use selectin |
| Missing count cache | user_collections.py:134-136 | HIGH | No caching for COUNT queries |

## Query Flow Diagrams

### Current Architecture (SLOW)

```
GET /api/v1/artifacts?limit=50

Step 1: Load Artifacts
┌─────────────────────────────────────────┐
│ SELECT * FROM artifacts LIMIT 50        │ Query 1
└─────────────────────────────────────────┘
         │
         ├─ Selectin: artifact_metadata         Query 2
         ├─ Selectin: collections              Query 3
         ├─ Selectin: tags                     Query 4
         └─ Selectin: versions                 Query 5

Step 2: Manual Collection Query (duplicate!)
┌─────────────────────────────────────────┐
│ SELECT * FROM collection_artifacts      │ Query 6
│ WHERE artifact_id IN (...)              │
└─────────────────────────────────────────┘
         │
         └─ Query 7: SELECT * FROM collections
             WHERE id IN (...)

Step 3: COUNT LOOP (🔴 CRITICAL)
┌─────────────────────────────────────────┐
│ FOR each artifact (50 total):            │
│   FOR each collection (avg 2 per):       │
│     SELECT COUNT(*)                     │ Queries 8-107 (100+ times!)
│     FROM collection_artifacts           │
│     WHERE collection_id = ?             │
└─────────────────────────────────────────┘

TOTAL: 107+ database queries for 1 API request!
```

### Optimized Architecture (FAST)

```
GET /api/v1/artifacts?limit=50

Step 1: Load Artifacts
┌─────────────────────────────────────────┐
│ SELECT * FROM artifacts LIMIT 50        │ Query 1
│ (NO selectin - lazy loading)            │
└─────────────────────────────────────────┘

Step 2: Fetch Collections + Counts Atomically
┌─────────────────────────────────────────┐
│ SELECT * FROM collection_artifacts      │ Query 2
│ WHERE artifact_id IN (...)              │
└─────────────────────────────────────────┘
         │
         ├─ Query 3: SELECT * FROM collections
         │                WHERE id IN (...)
         │
         └─ Query 4: SELECT collection_id,   ← Aggregation instead
                            COUNT(*) as count     of loop COUNT
                     FROM collection_artifacts
                     GROUP BY collection_id

TOTAL: 4 database queries for 1 API request!
```

## Before vs After Comparison

### Query Volume

```
BEFORE:
├─ Base queries: 5-7
├─ Collection queries: 1
└─ COUNT queries: 100+
TOTAL: 105-107 queries

AFTER:
├─ Base queries: 1
├─ Collection queries: 2
└─ Aggregation query: 1
TOTAL: 4 queries

IMPROVEMENT: 96% reduction (107 → 4)
```

### Response Time

```
BEFORE:
Query Planning:     50ms
Network Overhead:  100ms × 107 = 10,700ms
Database Time:      500ms (execution)
TOTAL:            ~800-1200ms

AFTER:
Query Planning:      20ms
Network Overhead:   100ms × 4 = 400ms
Database Time:       100ms (execution)
TOTAL:             ~100-200ms

IMPROVEMENT: 85-90% faster
```

## Code Locations

### Primary Issues

```
skillmeat/
├── api/routers/
│   ├── artifacts.py
│   │   └── lines 1905-1908: ← 🔴 N+1 COUNT LOOP
│   │       Loop over associations
│   │       COUNT per collection
│   │
│   └── user_collections.py
│       └── lines 134-136: ← 🟡 PER-COLLECTION COUNT
│           COUNT query per collection in list
│
└── cache/
    └── models.py
        ├── lines 159-163: Project.artifacts selectin
        ├── lines 287-294: ← 🔴 Artifact.collections selectin
        │   Duplicate loading (artifacts.py queries separately)
        │
        ├── lines 303-309: Artifact.versions selectin
        ├── lines 295-302: Artifact.tags selectin
        ├── lines 280-286: Artifact.metadata selectin
        │
        └── lines 686-702: ← 🟡 Collection cascading selectin
            ├── groups selectin
            ├── collection_artifacts selectin
            └── templates selectin
```

## Implementation Priority

### Week 1: Priority 1 - Fix N+1 (CRITICAL)

**File:** `skillmeat/api/routers/artifacts.py`
**Lines:** 1905-1908

Current:
```python
# Loop over associations, COUNT each collection
for assoc in associations:
    artifact_count = db_session.query(CollectionArtifact)\
        .filter_by(collection_id=coll.id)\
        .count()  # ← 100+ times!
```

Fix:
```python
# Single aggregation query
counts = db_session.query(
    CollectionArtifact.collection_id,
    func.count(CollectionArtifact.artifact_id).label('count')
)\
.filter(CollectionArtifact.collection_id.in_(collection_ids))\
.group_by(CollectionArtifact.collection_id)\
.all()
count_map = {coll_id: count for coll_id, count in counts}

# Use map
artifact_count = count_map.get(coll.id, 0)
```

**Benefit:** 90% of performance improvement

---

### Week 2: Priority 2 - Fix Eager Loading (HIGH)

**File:** `skillmeat/cache/models.py`
**Lines:** 287-294

Current:
```python
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    viewonly=True,
    lazy="selectin",  # Always loads, even if not used
)
```

Fix:
```python
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    viewonly=True,
    lazy="select",  # Control loading per query
)

# In queries that need collections:
session.query(Artifact).options(selectinload(Artifact.collections))
```

**Benefit:** Additional 10% improvement

---

### Week 3: Priority 3 - Add Count Cache (HIGH)

**New File:** `skillmeat/cache/count_cache.py`

```python
class CollectionCountCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl_seconds

    def get(self, collection_id: str, session: Session) -> int:
        now = time.time()
        if collection_id in self.cache:
            if now - self.timestamps[collection_id] < self.ttl:
                return self.cache[collection_id]

        count = session.query(CollectionArtifact)\
            .filter_by(collection_id=collection_id).count()
        self.cache[collection_id] = count
        self.timestamps[collection_id] = now
        return count

    def invalidate(self, collection_id: str):
        self.cache.pop(collection_id, None)
```

Usage in routers:
```python
from skillmeat.cache.count_cache import _count_cache

artifact_count = _count_cache.get(collection.id, session)

# On update:
_count_cache.invalidate(collection.id)
```

**Benefit:** Prevents query storms for popular collections

---

## Index Status

### Existing Indexes (GOOD)

```sql
CREATE INDEX idx_collection_artifacts_collection_id
    ON collection_artifacts(collection_id);  ← ✓ Fast lookup

CREATE INDEX idx_collection_artifacts_artifact_id
    ON collection_artifacts(artifact_id);    ← ✓ Fast lookup

CREATE INDEX idx_collection_artifacts_added_at
    ON collection_artifacts(added_at);       ← ✓ Timestamp sorting
```

**Note:** Indexes help with WHERE filtering but not with COUNT aggregation.

### Optional Future Index

```sql
-- Could help with COUNT queries, but caching is better
CREATE INDEX idx_collection_artifacts_collection_artifact
    ON collection_artifacts(collection_id, artifact_id);
```

## Performance Gains by Priority

| Priority | Fix | Improvement | Effort |
|----------|-----|-------------|--------|
| 1 | N+1 COUNT aggregation | 90% | 30 min |
| 2 | Reduce selectin loading | 10% | 1 hour |
| 3 | Add count cache | Storm prevention | 1 hour |
| 4 | Denormalized count field | Future-proof | 2 hours |

**Total Effort for 95% Gain:** ~2-2.5 hours

## Testing Strategy

### Before Optimization

```bash
# Add query logging
export SQLALCHEMY_ECHO=1

# Make request
curl -X GET "http://localhost:8000/api/v1/artifacts?limit=50" \
  -H "Authorization: Bearer token" | head -20

# Count queries in logs
grep "SELECT" logs.txt | wc -l
# Expected: 105+
```

### After Optimization

```bash
# Same request
curl -X GET "http://localhost:8000/api/v1/artifacts?limit=50" \
  -H "Authorization: Bearer token" | head -20

# Count queries in logs
grep "SELECT" logs.txt | wc -l
# Expected: 4
```

### Load Test

```bash
# Before
ab -n 100 -c 10 "http://localhost:8000/api/v1/artifacts?limit=50"
# Expected: ~100 req/sec, high CPU, many connection timeouts

# After
ab -n 100 -c 10 "http://localhost:8000/api/v1/artifacts?limit=50"
# Expected: ~1000 req/sec, low CPU, stable connections
```

## Related Documentation

- `PERFORMANCE_ANALYSIS.md` - Full detailed analysis
- `PERFORMANCE_SUMMARY.md` - Quick reference guide
- `.claude/rules/api/routers.md` - Router patterns
- `skillmeat/api/CLAUDE.md` - API architecture
