# SQLite Locking Patterns - Quick Reference

## Files & Locations

### Core Database Configuration
- **Engine Creation**: `skillmeat/cache/models.py:4201-4251`
  - WAL mode enabled ✓
  - 30s timeout configured
  - Connection pool settings

- **Session Factory**: `skillmeat/cache/models.py:4254-4278`
  - Global `SessionLocal` variable (initialized at startup)
  - `init_session_factory()` - should be called in API lifespan

### Repository Session Management
- **BaseRepository._get_session()**: `skillmeat/cache/repositories.py:302-319`
  - **PROBLEM**: Recreates sessionmaker on every call
  - Should use global SessionLocal instead

- **MarketplaceTransactionHandler.import_transaction()**: `skillmeat/cache/repositories.py:997-1044`
  - Implements context manager for atomic operations
  - Calls `_get_session()` (inherits the recreation problem)

### Marketplace Import Flow
- **Main endpoint**: `skillmeat/api/routers/marketplace_sources.py:4119-4390`
  - Line 4147-4149: Create repositories (creates independent session factories)
  - Line 4153-4170: Verification queries (multiple sessions)
  - Line 4293-4357: **LONG TRANSACTION** Session F (100+ operations)
  - Line 4359-4380: **SECOND TRANSACTION** Session G (status updates)

### Workflow Transaction Pattern
- **File**: `skillmeat/cache/workflow_transaction.py`
- **Key method**: `atomic_execution_state_change()` lines 155-248
  - Uses `begin_transaction()` context manager
  - Updates execution + multiple step rows in single transaction
  - Shares same session instance pattern as marketplace

---

## Session Creation Pattern (Current)

```python
# PROBLEM: Recreates sessionmaker every time
class BaseRepository:
    def _get_session(self) -> Session:
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,  # Each repo has its own engine
        )
        return SessionLocal()
```

**Calls per import:**
- `source_repo.get_by_id()` → session 1
- Per entry: `catalog_repo.get_by_id()` → sessions 2, 3, 4, ...
- `catalog_repo.list_by_source()` → session N
- `import_transaction()` wrapper → session N+1
- **Total: N+2 sessionmaker creations for N artifacts**

---

## Session Creation Pattern (Recommended)

```python
# SOLUTION: Use global singleton
from skillmeat.cache.models import get_session

class BaseRepository:
    def _get_session(self) -> Session:
        return get_session(self.db_path)
```

**Also required in API lifespan:**
```python
# In skillmeat/api/server.py lifespan
from skillmeat.cache.models import init_session_factory

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_session_factory()  # Initialize once at startup
    # ... rest of initialization
    yield
    # ... cleanup
```

---

## Long Transaction Pattern (Current - Problematic)

```python
# Lines 4293-4357: Single transaction for all artifacts
with transaction_handler.import_transaction(source_id) as ctx:
    try:
        for entry in import_result.entries:
            # Each entry triggers:
            populate_collection_artifact_from_import(session, ...)
            # - INSERT into collection_artifacts
            # - FK constraint checks
            # - Potentially UPDATE if exists
        # Multiple optional nested operations
        if composite:
            _import_composite_children(session=session, ...)
        # All in ONE transaction, held for entire loop
        session.commit()  # Commits only after all entries processed
    except:
        session.rollback()
```

**Lock Impact:**
- Exclusive write lock held for N iterations
- Each iteration = 1-5 database operations
- 100 artifacts = 100-500 operations in single lock hold
- **Blocks concurrent writes for 2-3 seconds**

---

## Long Transaction Pattern (Recommended - Batched)

```python
# Solution: Batch into smaller transactions
BATCH_SIZE = 10

for batch_start in range(0, len(entries), BATCH_SIZE):
    batch_end = min(batch_start + BATCH_SIZE, len(entries))
    batch = entries[batch_start:batch_end]

    with transaction_handler.import_transaction(source_id) as ctx:
        for entry in batch:
            populate_collection_artifact_from_import(session, ...)
            # ... other operations
        # Commit after every 10 entries
        session.commit()
```

**Benefits:**
- Lock held for ~200-500ms per batch (vs 2-3s for all)
- Other requests can acquire lock between batches
- Better responsiveness for concurrent operations

---

## Engine Configuration Tuning

**Current** (`skillmeat/cache/models.py:4229-4236`):

```python
engine = create_engine(
    f"sqlite:///{db_path}",
    echo=False,
    connect_args={
        "check_same_thread": False,  # Allows async; increases lock contention
        "timeout": 30.0,             # Long wait for lock
    },
)
```

**Recommended for high-concurrency:**

```python
engine = create_engine(
    f"sqlite:///{db_path}",
    echo=False,
    connect_args={
        "check_same_thread": False,  # Keep (required for FastAPI async)
        "timeout": 10.0,  # Reduce timeout to detect lock issues faster
    },
    pool_size=5,           # Explicit pool size (SQLite doesn't use; FYI)
    max_overflow=10,       # Explicit overflow (SQLite doesn't use; FYI)
    pool_recycle=3600,     # Recycle connections hourly
)
```

**PRAGMA tuning** (lines 4239-4249):

```python
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")         # ✓ Good
    cursor.execute("PRAGMA synchronous=NORMAL")       # ✓ Good balance
    cursor.execute("PRAGMA foreign_keys=ON")          # ✓ Required
    cursor.execute("PRAGMA temp_store=MEMORY")        # ✓ Good
    cursor.execute("PRAGMA cache_size=-64000")        # ✓ Good
    cursor.execute("PRAGMA mmap_size=268435456")      # ✓ Good
    # Optional: For high-contention scenarios:
    # cursor.execute("PRAGMA wal_autocheckpoint=1000")  # Checkpoint more often
    cursor.close()
```

---

## Concurrent Operation Matrix

| Operation | Endpoint | Session Count | Lock Type | Duration |
|-----------|----------|---|---|---|
| Import 100 artifacts | `POST /import_artifacts` | 7+ | Exclusive | 2-3 sec |
| Reimport single | `POST /reimport_catalog_entry` | 2 | Exclusive | 200-500 ms |
| Update catalog entry | `PATCH /artifacts/{entry_id}` | 1 | Exclusive | 10-50 ms |
| List artifacts | `GET /artifacts` | 1 | Read | <50 ms |
| Update execution | Workflow API | 1 | Exclusive | 50-100 ms |

**Contention Hotspot:** Import endpoint with concurrent catalog updates or other imports.

---

## Debugging Lock Contention

### Enable SQLite Lock Logging

```python
# In create_db_engine():
engine = create_engine(
    f"sqlite:///{db_path}",
    echo=True,  # ← Enable to see SQL
    # ...
)
```

### Monitor Lock Waits

```python
# Add to import_artifacts endpoint:
import time
import logging

logger = logging.getLogger(__name__)

start = time.time()
# ... import logic ...
elapsed = time.time() - start

if elapsed > 2.0:
    logger.warning(
        f"Import took {elapsed:.2f}s (possible lock contention); "
        f"batch_size={BATCH_SIZE}, entry_count={len(entries)}"
    )
```

### Check Connection Pool Status

```python
# For debugging
from sqlalchemy import event
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def log_pool(dbapi_conn, connection_record):
    logger.debug(f"Pool size: {dbapi_conn.total_changes}")

@event.listens_for(Pool, "checkout")
def log_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug(f"Connection checked out from pool")
```

---

## Test Cases to Add

### Load Test: 5 Concurrent Imports

```python
# tests/test_concurrent_imports.py
import asyncio
import pytest

@pytest.mark.asyncio
async def test_concurrent_imports():
    """Verify no lock contention with 5 concurrent imports."""
    async def import_batch(source_id, entry_count):
        # Import entry_count artifacts
        # Measure elapsed time
        # Should be ~entry_count * 10ms, not 2s per import
        pass

    tasks = [
        import_batch(f"source-{i}", 100)
        for i in range(5)
    ]
    results = await asyncio.gather(*tasks)

    # Verify no task took > 1s longer than others
    times = [r["elapsed"] for r in results]
    assert max(times) - min(times) < 1.0  # Within 1 second of each other
```

### Lock Timeout Test

```python
# tests/test_lock_timeout.py
@pytest.mark.asyncio
async def test_import_respects_timeout():
    """Verify timeout doesn't cause silent failures."""
    # Start long import
    # During import, try rapid catalog updates
    # Verify updates fail with clear error, not hanging
    pass
```

---

## Files to Modify (Priority)

1. **High Priority (P0)**
   - `skillmeat/cache/repositories.py` - Fix `_get_session()`
   - `skillmeat/api/server.py` - Add `init_session_factory()` call

2. **High Priority (P1)**
   - `skillmeat/api/routers/marketplace_sources.py` - Batch import transactions

3. **Medium Priority (P2)**
   - `skillmeat/cache/models.py` - Tune PRAGMA/timeout settings
   - Add concurrent operation tests

4. **Low Priority (P3)**
   - Add lock contention metrics/logging
   - Monitor and optimize based on production data

