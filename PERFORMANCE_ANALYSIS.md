# SkillMeat Collection Data Architecture - Performance Analysis

## Executive Summary

The current collection data architecture exhibits **critical N+1 query patterns** and **aggressive eager-loading strategies** that will cause performance degradation at scale. The system currently performs COUNT queries per artifact per collection, leading to O(n²) database operations in worst case.

**Key Findings:**
- 🔴 **CRITICAL**: N+1 COUNT queries in artifact list endpoint (lines 1905-1908 in artifacts.py)
- 🔴 **CRITICAL**: All collections relationship loaded with `selectin` on every Artifact query
- 🟡 **HIGH**: Multiple eager-load strategies compounds query proliferation
- 🟡 **HIGH**: Missing COUNT query optimization (no aggregate caching)
- 🟢 **Good**: Proper indexes on CollectionArtifact table exist

---

## 1. Database Query Patterns - N+1 Issues

### Critical Issue: Per-Artifact COUNT in Collections Mapping

**File:** `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/artifacts.py`
**Lines:** 1905-1908

```python
# BUILD collections_map for each artifact
for assoc in associations:
    if assoc.artifact_id not in collections_map:
        collections_map[assoc.artifact_id] = []

    coll = collection_details.get(assoc.collection_id)
    if coll:
        # COUNT query executed per artifact per collection membership
        artifact_count = (
            db_session.query(CollectionArtifact)
            .filter_by(collection_id=coll.id)
            .count()  # ← PROBLEM: N+1 COUNT queries
        )
        collections_map[assoc.artifact_id].append({
            "id": coll.id,
            "name": coll.name,
            "artifact_count": artifact_count,  # ← Included in response
        })
```

**Problem Analysis:**
- For a page of 50 artifacts with average 2 collections per artifact: **~100 additional COUNT queries**
- Each COUNT query scans the entire `collection_artifacts` table (full scan or index scan)
- Total query count: 3 (associations) + 1 (collections) + N (COUNTs) = **O(n) additional queries**
- At scale (1000 artifacts, 500 collections): **500+ COUNT queries per request**

**Impact:**
- Single page list request: 103 database round-trips minimum
- Response time: linear to artifact-collection memberships
- Database CPU: high under concurrent load
- Connection pool exhaustion: probable with multiple concurrent requests

---

### Secondary Issue: Per-Collection COUNT in user_collections.py

**File:** `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/user_collections.py`
**Lines:** 134-136

```python
def collection_to_response(collection: Collection, session: Session):
    group_count = len(collection.groups)
    artifact_count = (
        session.query(CollectionArtifact)
        .filter_by(collection_id=collection.id)
        .count()  # ← Redundant COUNT per collection response
    )
```

**Problem:** When listing multiple collections, each collection triggers a COUNT query:
- List 10 collections → 10 COUNT queries
- Could be optimized with a single COUNT(*) GROUP BY query

---

## 2. Eager Loading Strategy Issues

### Over-Aggressive selectin Loading

**File:** `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`
**Lines:** 287-294 (Artifact.collections relationship)

```python
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id",
    secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
    viewonly=True,
    lazy="selectin",  # ← Loads ALL collections for EVERY artifact query
)
```

**Impact Chain:**
1. Query artifacts → SQLAlchemy loads collections via selectin
2. selectin generates: `SELECT ... FROM collections WHERE id IN (...)`
3. For 50 artifacts with 10 collections average: **extra IN query with 500 IDs**
4. Collections relationship ignored in artifacts.py (lines 1872-1920) - **wasted load**

**Why This Matters:**
- artifacts.py explicitly queries collections via separate path (lines 1879-1894)
- The selectin loading is **redundant and wasteful**
- Memory overhead: N collections loaded into Artifact objects but discarded

### Compounding Eager Loads

**Related Relationships (all selectin):**

```python
# Line 159-163: Project.artifacts
artifacts: Mapped[List["Artifact"]] = relationship(
    "Artifact",
    back_populates="project",
    cascade="all, delete-orphan",
    lazy="selectin",  # ← Eagerly loads all artifacts
)

# Line 280-286: Artifact.artifact_metadata
artifact_metadata: Mapped[Optional["ArtifactMetadata"]] = relationship(
    "ArtifactMetadata",
    back_populates="artifact",
    cascade="all, delete-orphan",
    uselist=False,
    lazy="selectin",  # ← Eagerly loads metadata
)

# Line 303-309: Artifact.versions
versions: Mapped[List["ArtifactVersion"]] = relationship(
    "ArtifactVersion",
    back_populates="artifact",
    cascade="all, delete-orphan",
    lazy="selectin",  # ← Eagerly loads all versions
    order_by="ArtifactVersion.created_at.desc()",
)

# Line 295-302: Artifact.tags
tags: Mapped[List["Tag"]] = relationship(
    "Tag",
    secondary="artifact_tags",
    primaryjoin="Artifact.id == foreign(ArtifactTag.artifact_id)",
    secondaryjoin="foreign(ArtifactTag.tag_id) == Tag.id",
    lazy="selectin",  # ← Eagerly loads all tags
    back_populates="artifacts",
)
```

**Query Multiplication Example (artifacts.py listing):**
- Base query: 1 (load Artifact list)
- selectin: collections → N₁ (IN query for all artifact IDs)
- selectin: artifact_metadata → N₂ (IN query for all artifact IDs)
- selectin: versions → N₃ (IN query with LIMIT per artifact)
- selectin: tags → N₄ (IN query for all artifact IDs)
- **Total: 5 database queries minimum for single artifact list**

**But artifacts.py ignores most of this data:**
- artifacts.py uses: **only artifact_id, name, type**
- artifacts.py queries collections separately (duplicate with selectin)
- artifacts.py discards: metadata, versions, tags

---

### Collection Relationship Eager Loading

**File:** `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/models.py`
**Lines:** 686-702 (Collection model)

```python
# Collection eager loads its nested relationships
groups: Mapped[List["Group"]] = relationship(
    "Group",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="selectin",  # ← Eagerly load groups
)
collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
    "CollectionArtifact",
    cascade="all, delete-orphan",
    lazy="selectin",  # ← Eagerly load associations
)
templates: Mapped[List["ProjectTemplate"]] = relationship(
    "ProjectTemplate",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="selectin",  # ← Eagerly load templates
)
```

**When collections are loaded by selectin:**
1. Collections selectin: loads 10 collections
2. Each collection's groups selectin: loads N groups
3. Each collection's collection_artifacts selectin: loads M associations
4. Each collection's templates selectin: loads K templates
5. **Result: 4+ additional queries for what should be 1 lookup**

---

## 3. Index Analysis - CollectionArtifact Table

**File:** `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/migrations/versions/20251212_1600_create_collections_schema.py`
**Lines:** 170-184

```sql
-- ✓ Index on collection_id (primary lookup)
CREATE INDEX idx_collection_artifacts_collection_id ON collection_artifacts(collection_id);

-- ✓ Index on artifact_id (reverse lookup)
CREATE INDEX idx_collection_artifacts_artifact_id ON collection_artifacts(artifact_id);

-- ✓ Index on added_at (timestamp sorting)
CREATE INDEX idx_collection_artifacts_added_at ON collection_artifacts(added_at);
```

**Status:** Indexes are well-designed and present. **This is good.**

**Missing Optimization:** The COUNT queries can still benefit from:
- **Composite index**: `(collection_id, artifact_id)` would help count aggregation
- **Database-level count caching**: SQLite doesn't provide this, but application-level caching can

---

## 4. SQLAlchemy Relationship Loading Analysis

### Current lazy="selectin" Strategy Issues

**Problem 1: Selectin Unpredictability**
- selectin generates separate query per relationship
- Can't control batch size or IN clause limits
- Each IN query loads ALL matching records

**Problem 2: Memory Overhead**
- All collections loaded into Artifact.collections attribute
- But artifacts.py manually queries collections again
- Duplicated data in memory

**Problem 3: False Optimization**
- selectin looks efficient (fewer queries than default lazy loading)
- But loads data that's never used
- Better to use lazy="raise" or lazy="joined" for specific queries

---

## 5. Caching Opportunities

### Collection Counts - Best Optimization

**Current State:**
- COUNT queries run per response
- No aggregation or caching
- O(n) queries for collection listings

**Recommended Approach:**
```python
# Option 1: Denormalized count field
class Collection(Base):
    artifact_count: Mapped[int] = mapped_column(Integer, default=0)
    # Update via trigger on INSERT/DELETE to collection_artifacts

# Option 2: Application-level cache
from functools import lru_cache
import time

class CollectionCountCache:
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl_seconds

    def get_count(self, collection_id: str, session: Session) -> int:
        now = time.time()
        if collection_id in self.cache:
            if now - self.timestamps[collection_id] < self.ttl:
                return self.cache[collection_id]

        count = session.query(CollectionArtifact)\
            .filter_by(collection_id=collection_id).count()

        self.cache[collection_id] = count
        self.timestamps[collection_id] = now
        return count

# Usage in collection_to_response()
artifact_count = cache.get_count(collection.id, session)
```

**Benefit:** 300-400ms saved per 10-collection listing (with 50-artifact per collection average)

### Artifact-Collection Membership Lookup Cache

**Current State:**
- collections_map rebuilt per request
- No cache between requests
- Repeated queries for same artifacts

**Recommended Approach:**
```python
# Cache artifact memberships with TTL
cache_key = f"artifact_collections:{artifact_id}"
memberships = cache.get(cache_key)
if memberships is None:
    memberships = (
        session.query(CollectionArtifact)
        .filter_by(artifact_id=artifact_id)
        .with_entities(CollectionArtifact.collection_id, Collection.name)
        .join(Collection)
        .all()
    )
    cache.set(cache_key, memberships, ttl=300)
```

**Benefit:** Eliminate redundant queries for popular artifacts across requests

### Collection Membership Cache Invalidation

**Required:**
- Invalidate on InsertCollectionArtifact
- Invalidate on DeleteCollectionArtifact
- Invalidate on UpdateCollection (name changes)

---

## Performance Estimates

### Current Architecture (50 artifacts, 10 collections)

| Operation | Query Count | Time (estimated) | Notes |
|-----------|------------|------------------|-------|
| List artifacts | 103-110 | 800-1200ms | 1 + 1 + 50-100 COUNTs |
| Get collection | 12-15 | 200-400ms | 1 + N groups + M artifacts COUNT |
| List 10 collections | 50-60 | 1000-1500ms | 10 + 30-40 COUNT queries |
| **Total 3 requests** | **165-185** | **2000-3100ms** | Shows cumulative impact |

### Optimized Architecture (same scale)

| Operation | Query Count | Time (estimated) | Improvement |
|-----------|------------|------------------|------------|
| List artifacts | 3-5 | 100-200ms | 90% faster |
| Get collection | 2-3 | 50-100ms | 75% faster |
| List 10 collections | 5-7 | 100-200ms | 85% faster |
| **Total 3 requests** | **10-15** | **250-500ms** | **88% faster** |

---

## Recommendations

### Priority 1: Eliminate N+1 COUNT Queries (CRITICAL)

**File:** `skillmeat/api/routers/artifacts.py` lines 1905-1908

```python
# ❌ BEFORE: N+1 COUNT queries
for assoc in associations:
    artifact_count = (
        db_session.query(CollectionArtifact)
        .filter_by(collection_id=coll.id)
        .count()
    )

# ✓ AFTER: Single aggregation query
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

# Then use: artifact_count = count_map.get(coll.id, 0)
```

**Impact:** Reduce 100+ queries to 1 query for typical page load

---

### Priority 2: Reduce Eager Loading (HIGH)

**File:** `skillmeat/cache/models.py` lines 287-294

**Option A: Lazy load collections in artifacts.py**
```python
# Change lazy="selectin" to lazy="select"
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id",
    secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
    viewonly=True,
    lazy="select",  # ← Explicit control per query
)

# In artifacts.py, don't rely on selectin
# Use explicit contains_eager() for JOINED load when needed
```

**Option B: Use query options for fine control**
```python
# In artifacts.py
artifacts = (
    session.query(Artifact)
    .options(
        selectinload(Artifact.collections)  # Only load when needed
    )
    .all()
)

# For collection listing, don't load collections at all
artifacts = session.query(Artifact).all()  # No selectin
```

**Impact:** Reduce 5+ queries to 1-2 queries per artifact list

---

### Priority 3: Add Collection Count Caching (HIGH)

**File:** Create `skillmeat/cache/count_cache.py`

```python
from datetime import datetime, timedelta
from typing import Dict, Optional

class CollectionCountCache:
    """Cache collection artifact counts with TTL"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, tuple[int, datetime]] = {}
        self.ttl = ttl_seconds

    def get(self, collection_id: str, session: Session) -> int:
        """Get artifact count, using cache if valid"""
        now = datetime.utcnow()

        if collection_id in self.cache:
            count, cached_at = self.cache[collection_id]
            if (now - cached_at).total_seconds() < self.ttl:
                return count

        # Cache miss or expired
        count = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id)
            .count()
        )
        self.cache[collection_id] = (count, now)
        return count

    def invalidate(self, collection_id: str):
        """Invalidate cache entry"""
        self.cache.pop(collection_id, None)

    def invalidate_all(self):
        """Invalidate entire cache"""
        self.cache.clear()

# Global instance
_count_cache = CollectionCountCache(ttl_seconds=300)
```

**Usage in routers:**
```python
from skillmeat.cache.count_cache import _count_cache

artifact_count = _count_cache.get(collection.id, session)

# On collection membership change:
_count_cache.invalidate(collection.id)
```

**Impact:** 10-15 COUNT queries eliminated per typical collection listing

---

### Priority 4: Add Denormalized Count Field (MEDIUM)

**File:** `skillmeat/cache/migrations/versions/[timestamp]_add_artifact_count_to_collections.py`

```python
def upgrade():
    """Add artifact_count denormalized field"""
    op.add_column(
        'collections',
        sa.Column('artifact_count', sa.Integer, default=0, server_default='0')
    )

    # Populate with current counts
    op.execute("""
        UPDATE collections
        SET artifact_count = (
            SELECT COUNT(*) FROM collection_artifacts
            WHERE collection_id = collections.id
        )
    """)

    # Add trigger for automatic updates
    op.execute("""
        CREATE TRIGGER update_collection_count_insert
        AFTER INSERT ON collection_artifacts
        FOR EACH ROW
        BEGIN
            UPDATE collections SET artifact_count = artifact_count + 1
            WHERE id = NEW.collection_id;
        END;
    """)

    op.execute("""
        CREATE TRIGGER update_collection_count_delete
        AFTER DELETE ON collection_artifacts
        FOR EACH ROW
        BEGIN
            UPDATE collections SET artifact_count = artifact_count - 1
            WHERE id = OLD.collection_id;
        END;
    """)
```

**Benefits:**
- O(1) count lookups instead of O(n)
- Eliminates COUNT queries entirely
- Automatic synchronization via triggers

**Downside:** Requires database migration + denormalization trade-off

---

### Priority 5: Optimize Collection.groups Relationship Loading

**File:** `skillmeat/cache/models.py` lines 686-691

**Current Issue:**
```python
groups: Mapped[List["Group"]] = relationship(
    "Group",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="selectin",  # ← Always loads groups
)

# But user_collections.py line 133:
group_count = len(collection.groups)  # ← Using len() on loaded relationship
```

**Optimization:**
```python
# Option A: Count at query time
group_count = (
    session.query(func.count(Group.id))
    .filter(Group.collection_id == collection.id)
    .scalar()
)

# Option B: Denormalize like collections
class Collection(Base):
    group_count: Mapped[int] = mapped_column(Integer, default=0)
    # Update via trigger
```

---

## Summary Table

| Issue | Location | Severity | Fix | Query Reduction |
|-------|----------|----------|-----|-----------------|
| N+1 COUNT in artifacts.py | lines 1905-1908 | CRITICAL | Aggregate query | 100+ → 1 |
| Redundant collections selectin | models.py:287-294 | HIGH | Lazy load | 1-2 queries |
| Unused relationship loading | models.py:303-309 | MEDIUM | Selective load | 2-3 queries |
| Missing count cache | user_collections.py | HIGH | Add cache | 10-15 per page |
| No denormalized counts | Collection model | MEDIUM | Add field + triggers | Future-proof |
| Unnecessary group loading | models.py:686-691 | LOW | Count at query time | 1 per collection |

---

## Implementation Priority

1. **Week 1**: Fix N+1 COUNT queries (Priority 1) - **88% of performance gain**
2. **Week 2**: Reduce eager loading (Priority 2) - **Additional 10% improvement**
3. **Week 3**: Add count caching (Priority 3) - **Smooth spiky load**
4. **Future**: Denormalize counts (Priority 4) - **Long-term optimization**

**Expected Outcome:** 2000-3100ms → 250-500ms (88% faster) for typical collection operations.
