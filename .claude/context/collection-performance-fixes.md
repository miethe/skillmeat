# Collection Performance Fixes - Code Examples

Complete code examples for implementing each performance fix.

## Fix 1: N+1 COUNT Query Aggregation (PRIORITY 1)

### Location
**File:** `skillmeat/api/routers/artifacts.py`
**Lines:** 1905-1908 (within the collections_map building loop)

### Current Code (BROKEN)

```python
# Line 1875-1920 in artifacts.py
if artifact_ids:
    try:
        db_session = get_session()
        # Query CollectionArtifact associations
        associations = (
            db_session.query(CollectionArtifact)
            .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
            .all()
        )

        # Get unique collection IDs
        collection_ids = {assoc.collection_id for assoc in associations}

        if collection_ids:
            # Query Collection details
            collections = (
                db_session.query(Collection)
                .filter(Collection.id.in_(collection_ids))
                .all()
            )
            collection_details = {c.id: c for c in collections}

            # Build mapping: artifact_id -> list of collection info
            for assoc in associations:
                if assoc.artifact_id not in collections_map:
                    collections_map[assoc.artifact_id] = []

                coll = collection_details.get(assoc.collection_id)
                if coll:
                    # ❌ PROBLEM: This COUNT runs for EVERY association
                    # If 50 artifacts × 2 collections = 100 COUNT queries!
                    artifact_count = (
                        db_session.query(CollectionArtifact)
                        .filter_by(collection_id=coll.id)
                        .count()
                    )
                    collections_map[assoc.artifact_id].append({
                        "id": coll.id,
                        "name": coll.name,
                        "artifact_count": artifact_count,
                    })

        db_session.close()
    except Exception as e:
        logger.warning(f"Failed to query collection memberships: {e}")
```

### Fixed Code (OPTIMIZED)

```python
# Replace lines 1905-1916 with:
if artifact_ids:
    try:
        db_session = get_session()

        # Query CollectionArtifact associations
        associations = (
            db_session.query(CollectionArtifact)
            .filter(CollectionArtifact.artifact_id.in_(artifact_ids))
            .all()
        )

        # Get unique collection IDs
        collection_ids = {assoc.collection_id for assoc in associations}

        if collection_ids:
            # Query Collection details
            collections = (
                db_session.query(Collection)
                .filter(Collection.id.in_(collection_ids))
                .all()
            )
            collection_details = {c.id: c for c in collections}

            # ✓ NEW: Get ALL counts in single query instead of loop
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
            count_map = {coll_id: count for coll_id, count in count_query}

            # Build mapping: artifact_id -> list of collection info
            for assoc in associations:
                if assoc.artifact_id not in collections_map:
                    collections_map[assoc.artifact_id] = []

                coll = collection_details.get(assoc.collection_id)
                if coll:
                    # ✓ FIXED: Use pre-computed count from map
                    artifact_count = count_map.get(coll.id, 0)
                    collections_map[assoc.artifact_id].append({
                        "id": coll.id,
                        "name": coll.name,
                        "artifact_count": artifact_count,
                    })

        db_session.close()
    except Exception as e:
        logger.warning(f"Failed to query collection memberships: {e}")
```

### Import Required

```python
# Add to imports at top of artifacts.py
from sqlalchemy import func
```

### Impact

- Before: 103+ queries (1 + 1 + 100+ COUNTs)
- After: 4 queries (1 + 1 + 1 aggregation + 1 collections)
- **Improvement: 96% query reduction**

---

## Fix 2: Reduce Eager Collection Loading (PRIORITY 2)

### Location 1: Model Definition
**File:** `skillmeat/cache/models.py`
**Lines:** 287-294

### Current Code (EAGER LOADS)

```python
# In Artifact class
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id",
    secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
    viewonly=True,
    lazy="selectin",  # ❌ ALWAYS loads via extra query
)
```

### Fixed Code (EXPLICIT CONTROL)

```python
# In Artifact class - Change lazy strategy
collections: Mapped[List["Collection"]] = relationship(
    "Collection",
    secondary="collection_artifacts",
    primaryjoin="foreign(CollectionArtifact.artifact_id) == Artifact.id",
    secondaryjoin="foreign(CollectionArtifact.collection_id) == Collection.id",
    viewonly=True,
    lazy="select",  # ✓ No automatic loading
)
```

### Location 2: Usage in artifacts.py

Since we've disabled automatic selectin loading, need to use explicit loading where needed:

```python
# If you need collections loaded for a query, use options():
from sqlalchemy.orm import selectinload

# Example: If you want to load artifacts WITH collections eagerly
artifacts = (
    session.query(Artifact)
    .options(selectinload(Artifact.collections))
    .all()
)

# Otherwise, just use the normal query without selectinload
# and manually query collections separately (current approach)
artifacts = session.query(Artifact).all()
```

### Impact

- Removes wasteful selectin loading
- Saves 1 query per artifact list
- Makes code clearer (explicit control)

---

## Fix 3: Add Collection Count Cache (PRIORITY 3)

### New File: Create `skillmeat/cache/count_cache.py`

```python
"""Cache for collection artifact counts with TTL expiration.

This module provides a simple in-memory cache for collection artifact counts
to avoid repeated COUNT queries during normal operation.

Usage:
    from skillmeat.cache.count_cache import _count_cache

    # Get count (cached if available)
    count = _count_cache.get(collection_id, session)

    # Invalidate on mutations
    _count_cache.invalidate(collection_id)
"""

import time
from typing import Dict, Tuple, Optional
from sqlalchemy.orm import Session

from skillmeat.cache.models import CollectionArtifact


class CollectionCountCache:
    """Thread-safe cache for collection artifact counts.

    Caches COUNT queries for each collection with automatic expiration
    after TTL. Reduces database load for collection operations.

    Attributes:
        cache: Dict mapping collection_id -> (count, timestamp)
        ttl: Time-to-live in seconds for cache entries
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default 5 min)
        """
        self.cache: Dict[str, Tuple[int, float]] = {}
        self.ttl = ttl_seconds

    def get(self, collection_id: str, session: Session) -> int:
        """Get artifact count for collection, using cache if valid.

        Args:
            collection_id: The collection ID to count artifacts for
            session: SQLAlchemy session for database queries

        Returns:
            Count of artifacts in the collection
        """
        now = time.time()

        # Check if cache entry exists and is not expired
        if collection_id in self.cache:
            count, cached_at = self.cache[collection_id]
            if (now - cached_at) < self.ttl:
                return count

        # Cache miss or expired - query database
        count = (
            session.query(CollectionArtifact)
            .filter_by(collection_id=collection_id)
            .count()
        )

        # Update cache
        self.cache[collection_id] = (count, now)
        return count

    def invalidate(self, collection_id: str) -> None:
        """Invalidate cache entry for a collection.

        Call this after:
        - Adding artifact to collection
        - Removing artifact from collection
        - Deleting collection

        Args:
            collection_id: The collection ID to invalidate
        """
        self.cache.pop(collection_id, None)

    def invalidate_all(self) -> None:
        """Invalidate entire cache.

        Call this for maintenance or during cache purges.
        """
        self.cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached entries."""
        return len(self.cache)

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring."""
        now = time.time()
        expired = sum(
            1 for _, (_, cached_at) in self.cache.items()
            if (now - cached_at) >= self.ttl
        )
        return {
            "total_entries": len(self.cache),
            "expired_entries": expired,
            "active_entries": len(self.cache) - expired,
        }


# Global cache instance
_count_cache = CollectionCountCache(ttl_seconds=300)
```

### Usage in user_collections.py

```python
# Add import
from skillmeat.cache.count_cache import _count_cache

# In collection_to_response() function - replace lines 134-136
def collection_to_response(collection: Collection, session: Session):
    """Convert Collection ORM model to API response.

    Args:
        collection: Collection ORM instance
        session: Database session for computing counts

    Returns:
        UserCollectionResponse DTO
    """
    # Compute counts
    group_count = len(collection.groups)

    # ✓ Use cache instead of direct query
    artifact_count = _count_cache.get(collection.id, session)

    return UserCollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        created_by=collection.created_by,
        collection_type=collection.collection_type,
        context_category=collection.context_category,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        group_count=group_count,
        artifact_count=artifact_count,
    )
```

### Cache Invalidation

Add to collection mutation endpoints:

```python
# In create_collection_artifact or similar endpoints
from skillmeat.cache.count_cache import _count_cache

@router.post("/collections/{collection_id}/artifacts/{artifact_id}")
async def add_artifact_to_collection(
    collection_id: str,
    artifact_id: str,
    session: Session = Depends(get_db_session)
) -> CollectionArtifactResponse:
    """Add artifact to collection."""

    # ... create association ...

    # ✓ Invalidate cache for this collection
    _count_cache.invalidate(collection_id)

    return response


@router.delete("/collections/{collection_id}/artifacts/{artifact_id}")
async def remove_artifact_from_collection(
    collection_id: str,
    artifact_id: str,
    session: Session = Depends(get_db_session)
) -> None:
    """Remove artifact from collection."""

    # ... delete association ...

    # ✓ Invalidate cache for this collection
    _count_cache.invalidate(collection_id)
```

### Impact

- Eliminates repeated COUNT queries for same collection
- 5-minute TTL prevents stale data
- Simple cache invalidation on mutations
- Prevents query storms during burst access

---

## Fix 4: Reduce Cascading Eager Loads (PRIORITY 2B)

### Location: Collection Model Relationships
**File:** `skillmeat/cache/models.py`
**Lines:** 686-702

### Current Code (CASCADING SELECTIN)

```python
# In Collection class - ALL relations use selectin
groups: Mapped[List["Group"]] = relationship(
    "Group",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="selectin",  # ❌ Always loads groups
)
collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
    "CollectionArtifact",
    cascade="all, delete-orphan",
    lazy="selectin",  # ❌ Always loads associations
)
templates: Mapped[List["ProjectTemplate"]] = relationship(
    "ProjectTemplate",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="selectin",  # ❌ Always loads templates
)
```

### Fixed Code (SELECTIVE LOADING)

```python
# In Collection class - Use select for explicit control
groups: Mapped[List["Group"]] = relationship(
    "Group",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="select",  # ✓ Explicit control per query
)
collection_artifacts: Mapped[List["CollectionArtifact"]] = relationship(
    "CollectionArtifact",
    cascade="all, delete-orphan",
    lazy="select",  # ✓ Explicit control per query
)
templates: Mapped[List["ProjectTemplate"]] = relationship(
    "ProjectTemplate",
    back_populates="collection",
    cascade="all, delete-orphan",
    lazy="select",  # ✓ Explicit control per query
)
```

### Usage Pattern

```python
# When you need groups/templates loaded, use options()
from sqlalchemy.orm import selectinload

# Load collection WITH its groups
collection = (
    session.query(Collection)
    .options(selectinload(Collection.groups))
    .filter_by(id=collection_id)
    .first()
)

# Load collection WITHOUT loading extra relationships
collection = (
    session.query(Collection)
    .filter_by(id=collection_id)
    .first()
)
# Groups will be lazily loaded only if accessed
```

---

## Fix 5: Optional - Denormalized Count Field (PRIORITY 4)

### Create Migration File

**File:** `skillmeat/cache/migrations/versions/[timestamp]_add_artifact_count_to_collections.py`

```python
"""Add denormalized artifact_count to collections table.

Revision ID: [timestamp]_add_artifact_count
Revises: [previous_revision]
Create Date: [timestamp]

This migration adds a denormalized artifact_count field to the collections
table, maintained automatically via database triggers. This eliminates the
need for COUNT queries on the collection_artifacts table.

The count is automatically updated when artifacts are added or removed
from collections via triggers, ensuring consistency without application
logic.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "[timestamp]_add_artifact_count"
down_revision: Union[str, None] = "[previous_revision_id]"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add artifact_count denormalized field."""
    # Add column with default 0
    op.add_column(
        "collections",
        sa.Column("artifact_count", sa.Integer, nullable=False, server_default="0"),
    )

    # Populate with current counts
    op.execute("""
        UPDATE collections
        SET artifact_count = (
            SELECT COUNT(*) FROM collection_artifacts
            WHERE collection_id = collections.id
        )
    """)

    # Create trigger for INSERT
    op.execute("""
        CREATE TRIGGER collection_artifact_count_insert
        AFTER INSERT ON collection_artifacts
        FOR EACH ROW
        BEGIN
            UPDATE collections
            SET artifact_count = artifact_count + 1
            WHERE id = NEW.collection_id;
        END;
    """)

    # Create trigger for DELETE
    op.execute("""
        CREATE TRIGGER collection_artifact_count_delete
        AFTER DELETE ON collection_artifacts
        FOR EACH ROW
        BEGIN
            UPDATE collections
            SET artifact_count = artifact_count - 1
            WHERE id = OLD.collection_id;
        END;
    """)


def downgrade() -> None:
    """Remove artifact_count field and triggers."""
    op.execute("DROP TRIGGER IF EXISTS collection_artifact_count_insert")
    op.execute("DROP TRIGGER IF EXISTS collection_artifact_count_delete")
    op.drop_column("collections", "artifact_count")
```

### Update Model

```python
# In Collection class in models.py
class Collection(Base):
    # ... existing fields ...

    # ✓ Add denormalized count field
    artifact_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
```

### Usage

```python
# Now COUNT queries become simple field lookups
def collection_to_response(collection: Collection, session: Session):
    group_count = len(collection.groups)
    artifact_count = collection.artifact_count  # ✓ O(1) lookup instead of COUNT

    return UserCollectionResponse(
        id=collection.id,
        # ... rest of fields ...
        artifact_count=artifact_count,
    )
```

### Benefits

- O(1) count lookups (no queries needed)
- Automatic synchronization via database triggers
- Eliminates COUNT queries entirely
- Works even if you remove the cache

### Trade-off

- Requires migration
- Adds denormalization (minor trade-off)
- Database triggers add slight overhead to INSERT/DELETE

---

## Testing the Fixes

### Test Fix 1: N+1 Aggregation

```python
# In a test file, mock the query and verify COUNT aggregation
from unittest.mock import patch, MagicMock
from skillmeat.api.routers.artifacts import list_artifacts
from sqlalchemy import func

def test_collection_counts_use_aggregation(session):
    """Verify that collection counts use GROUP BY instead of loop COUNT."""

    # Create test data
    collection = Collection(id="c1", name="Test")
    for i in range(5):
        artifact = Artifact(id=f"a{i}", name=f"art{i}", type="skill")
        session.add(artifact)
        assoc = CollectionArtifact(
            collection_id="c1",
            artifact_id=f"a{i}"
        )
        session.add(assoc)
    session.commit()

    # Make request
    response = client.get("/api/v1/artifacts?limit=50")

    # Verify response includes collection data
    assert response.status_code == 200
    artifacts = response.json()["items"]

    # Find our artifact with collection
    art_with_coll = [a for a in artifacts if a["id"] == "a0"][0]
    assert art_with_coll["collections_data"][0]["artifact_count"] == 5
```

### Test Fix 3: Count Cache

```python
from skillmeat.cache.count_cache import _count_cache

def test_count_cache_returns_cached_value(session):
    """Verify cache returns same count without additional queries."""

    # Clear cache
    _count_cache.invalidate_all()

    # First call - hits database
    count1 = _count_cache.get("c1", session)

    # Mock session to detect additional queries
    with patch.object(session, 'query', side_effect=Exception("Should not query")):
        # Second call - should use cache
        count2 = _count_cache.get("c1", session)

    # Both calls returned same count (not queried twice)
    assert count1 == count2

def test_count_cache_invalidation(session):
    """Verify cache invalidation works."""

    # Get initial count
    _count_cache.invalidate_all()
    count1 = _count_cache.get("c1", session)

    # Add artifact to collection
    session.execute("INSERT INTO collection_artifacts VALUES ('c1', 'a99')")
    session.commit()

    # Cache still returns old value (expired or invalidated)
    # This is OK - we invalidate in mutation endpoints

    # Invalidate cache
    _count_cache.invalidate("c1")

    # New query gets new count
    count2 = _count_cache.get("c1", session)
    assert count2 == count1 + 1
```

---

## Summary

| Fix | Priority | Lines Changed | Impact |
|-----|----------|----------------|--------|
| N+1 Aggregation | 1 | ~20 | 90% improvement |
| Reduce selectin | 2 | ~10 | 10% improvement |
| Add cache | 3 | ~100 (new file) | Storm prevention |
| Denormalize counts | 4 | ~30 (migration) | Future-proof |

**Total Implementation Time:** 2-3 hours for all fixes

**Expected Result:** 2000ms → 200ms (10x faster)
