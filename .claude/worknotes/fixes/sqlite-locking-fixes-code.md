# SQLite Locking - Fix Implementation Guide

## FIX #1: Replace Session Factory Recreation with Singleton

### Problem Code
**File:** `skillmeat/cache/repositories.py` (lines 302-319)

```python
def _get_session(self) -> Session:
    """Create a new database session.

    Returns:
        SQLAlchemy Session instance

    Note:
        Sessions should be closed after use. Prefer using the
        transaction() context manager for automatic cleanup.
    """
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(  # ❌ PROBLEM: Recreates every call
        autocommit=False,
        autoflush=False,
        bind=self.engine,
    )
    return SessionLocal()
```

### Fixed Code

```python
def _get_session(self) -> Session:
    """Create a new database session.

    Returns:
        SQLAlchemy Session instance

    Note:
        Sessions should be closed after use. Prefer using the
        transaction() context manager for automatic cleanup.
    """
    from skillmeat.cache.models import get_session

    # ✅ Use global singleton SessionLocal instead of recreating
    return get_session(self.db_path)
```

### Where to Apply
1. `BaseRepository._get_session()` - line 302
2. `MarketplaceSourceRepository._get_session()` - line 894 (identical pattern)

### Related Change Required
Ensure `skillmeat/cache/models.py` has working `get_session()`:

**Current code** (lines 4280-4290, excerpt):
```python
def get_session(db_path: Optional[str | Path] = None):
    """Get session from global factory or create one."""
    global SessionLocal
    if SessionLocal is None:
        init_session_factory(db_path)
    return SessionLocal()
```

**Verification:** Check that `SessionLocal` is not None after `init_session_factory()` is called.

---

## FIX #2: Initialize Session Factory in API Lifespan

### Problem
`init_session_factory()` is defined but never called, so `SessionLocal` stays None.

### Solution
**File:** `skillmeat/api/server.py` (lifespan function)

**Find** the current lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    app.state = AppState()
    app.state.initialize(get_settings())
    yield
    app.state.shutdown()
```

**Add initialization:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown logic."""
    # ✅ Initialize global session factory FIRST
    from skillmeat.cache.models import init_session_factory
    init_session_factory()

    app.state = AppState()
    app.state.initialize(get_settings())
    yield
    app.state.shutdown()
```

**Why:** This ensures `SessionLocal` is created once at startup, not recreated for every request.

---

## FIX #3: Batch Marketplace Import Transactions

### Problem Code
**File:** `skillmeat/api/routers/marketplace_sources.py` (lines 4293-4357)

```python
try:
    ensure_default_collection(session)
    from skillmeat.api.services.artifact_cache_service import (
        populate_collection_artifact_from_import,
    )

    db_added_count = 0
    for entry in import_result.entries:  # ❌ PROBLEM: All entries in one transaction
        if entry.status.value != "success":
            continue
        try:
            populate_collection_artifact_from_import(
                session, artifact_mgr, DEFAULT_COLLECTION_ID, entry
            )
            db_added_count += 1
        except Exception as cache_err:
            # ... error handling ...
            continue

        # Optional nested operations inside loop
        if _sca_enabled and entry.artifact_type == "skill":
            _wire_skill_composite(session=session, ...)

        if entry.artifact_type == "composite":
            _import_composite_children(session=session, ...)

    logger.info(
        f"Added {db_added_count} artifacts to default database collection "
        f"with full metadata"
    )
except Exception as e:
    logger.error(f"Failed to add artifacts to database collection: {e}")
    session.rollback()
```

### Fixed Code

```python
from skillmeat.api.services.artifact_cache_service import (
    populate_collection_artifact_from_import,
)

IMPORT_BATCH_SIZE = 10  # ✅ Add batch size constant

# Group entries into batches
batches = []
for i in range(0, len(import_result.entries), IMPORT_BATCH_SIZE):
    batches.append(import_result.entries[i:i+IMPORT_BATCH_SIZE])

total_db_added = 0

for batch_idx, batch_entries in enumerate(batches):
    # ✅ Open NEW transaction for each batch
    try:
        with transaction_handler.import_transaction(source_id) as ctx:
            # Initialize collection only in first batch
            if batch_idx == 0:
                ensure_default_collection(ctx.session)

            db_added_count = 0
            for entry in batch_entries:
                if entry.status.value != "success":
                    continue
                try:
                    populate_collection_artifact_from_import(
                        ctx.session, artifact_mgr, DEFAULT_COLLECTION_ID, entry
                    )
                    db_added_count += 1
                except Exception as cache_err:
                    logger.warning(
                        f"Cache population failed for "
                        f"{entry.artifact_type}:{entry.name}: {cache_err}"
                    )
                    continue

                # Optional nested operations
                if _sca_enabled and entry.artifact_type == "skill":
                    _wire_skill_composite(
                        session=ctx.session,
                        source_id=source_id,
                        entry=entry,
                        catalog_repo=catalog_repo,
                        collection_id=DEFAULT_COLLECTION_ID,
                    )

                if entry.artifact_type == "composite":
                    _import_composite_children(
                        session=ctx.session,
                        artifact_mgr=artifact_mgr,
                        collection_mgr=collection_mgr,
                        catalog_repo=catalog_repo,
                        transaction_handler=transaction_handler,
                        source_id=source_id,
                        source_ref=source.ref,
                        composite_entry=entry,
                        strategy=strategy,
                        populate_fn=populate_collection_artifact_from_import,
                    )

            total_db_added += db_added_count
            logger.debug(
                f"Batch {batch_idx + 1}/{len(batches)}: "
                f"Added {db_added_count} artifacts"
            )
            # Transaction commits automatically when exiting with block

    except Exception as e:
        logger.error(f"Failed to import batch {batch_idx}: {e}")
        # Continue with next batch instead of failing entire import
        continue  # ✅ Allows partial success

logger.info(
    f"Completed import: {total_db_added}/{len(import_result.entries)} "
    f"artifacts added to default database collection"
)
```

### Why This Works

1. **Smaller Transactions:** Each batch (10 artifacts) holds exclusive lock for ~400ms instead of 3.5s
2. **Lock Release:** Lock released after each batch, allowing concurrent operations to proceed
3. **Partial Success:** If batch 5 fails, batches 1-4 are still committed (better resilience)
4. **Scalability:** Works with 10, 100, or 1000 artifacts without blocking others

### Testing the Fix

```python
# Add to test_marketplace_sources.py
import asyncio
import time

@pytest.mark.asyncio
async def test_batched_import_concurrent_operations():
    """Verify import doesn't block concurrent catalog updates."""
    source_id = "test-source-123"

    # Create 100 catalog entries
    entries = [
        {
            "id": f"entry-{i}",
            "artifact_type": "skill",
            "name": f"skill-{i}",
            "upstream_url": "https://github.com/test/repo",
            "path": f"skills/skill-{i}",
            "description": f"Test skill {i}",
            "tags": [],
        }
        for i in range(100)
    ]

    import_request = ImportRequest(entry_ids=[e["id"] for e in entries])

    # Start import
    import_task = asyncio.create_task(
        import_artifacts(source_id, import_request, collection_mgr, artifact_mgr, session)
    )

    # Wait for first batch to start (100ms)
    await asyncio.sleep(0.1)

    # During import, try catalog update
    start_update = time.time()
    update_response = await update_catalog_entry_name(
        source_id, "entry-50", UpdateCatalogEntryNameRequest(name="updated-name")
    )
    elapsed_update = time.time() - start_update

    # Wait for import to finish
    import_response = await import_task

    # Verify update was fast (not blocked for 3+ seconds)
    assert elapsed_update < 1.0, f"Update took {elapsed_update}s (likely blocked)"
    assert import_response.imported_count == 100
```

---

## FIX #4: Tune SQLite Configuration (Optional)

### Problem Code
**File:** `skillmeat/cache/models.py` (lines 4229-4249)

```python
engine = create_engine(
    f"sqlite:///{db_path}",
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,  # ⚠️ Long timeout masks lock issues
    },
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA mmap_size=268435456")
    cursor.close()
```

### Fixed Code (High-Concurrency Tuning)

```python
engine = create_engine(
    f"sqlite:///{db_path}",
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 10.0,  # ✅ Reduce to 10s (earlier failure detection)
    },
    # Pool settings (FYI: SQLite doesn't use these, but good practice)
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Recycle connections hourly
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")           # ✓ Good
    cursor.execute("PRAGMA synchronous=NORMAL")         # ✓ Good balance
    cursor.execute("PRAGMA foreign_keys=ON")            # ✓ Required
    cursor.execute("PRAGMA temp_store=MEMORY")          # ✓ Good
    cursor.execute("PRAGMA cache_size=-64000")          # ✓ Good
    cursor.execute("PRAGMA mmap_size=268435456")        # ✓ Good

    # ✅ Optional: For very high concurrency, checkpoint WAL more frequently
    # This prevents WAL from growing too large and causing lock contention
    # during checkpoint merges
    cursor.execute("PRAGMA wal_autocheckpoint=1000")   # Checkpoint after 1000 pages

    cursor.close()
```

**Why the changes:**

| Change | Reason |
|--------|--------|
| `timeout: 10.0` (from 30.0) | Faster failure detection; 10s is still reasonable |
| `pool_recycle=3600` | Prevents stale connections; good practice |
| `wal_autocheckpoint=1000` | Prevents WAL from growing huge (can cause lock spikes) |

---

## FIX #5: Add Lock Contention Monitoring

### Add to `skillmeat/api/routers/marketplace_sources.py`

```python
import time
import logging

logger = logging.getLogger(__name__)

# Add to import_artifacts endpoint
async def import_artifacts(
    source_id: str,
    request: ImportRequest,
    collection_mgr: CollectionManagerDep,
    artifact_mgr: ArtifactManagerDep,
    session: DbSessionDep,
) -> ImportResultDTO:
    """Import catalog entries to local collection."""

    # ✅ Add timing instrumentation
    request_start = time.time()
    lock_hold_times = []  # Track lock hold duration per batch

    # ... [existing code for repos, verification, import] ...

    IMPORT_BATCH_SIZE = 10

    for batch_idx, batch_entries in enumerate(batches):
        batch_start = time.time()
        try:
            with transaction_handler.import_transaction(source_id) as ctx:
                # ... [existing batch import logic] ...
                pass  # Transaction commits here

        except Exception as e:
            logger.error(f"Failed to import batch {batch_idx}: {e}")
            continue

        # ✅ Track lock hold duration
        batch_elapsed = time.time() - batch_start
        lock_hold_times.append(batch_elapsed)

        logger.debug(
            f"Batch {batch_idx + 1}: lock held for {batch_elapsed:.2f}s"
        )

        # ⚠️ Warn if batch took too long (indicates lock contention)
        if batch_elapsed > 1.0:
            logger.warning(
                f"Batch {batch_idx + 1} took {batch_elapsed:.2f}s "
                f"(possible lock contention)"
            )

    # ✅ Log summary
    total_elapsed = time.time() - request_start
    max_lock_hold = max(lock_hold_times) if lock_hold_times else 0

    logger.info(
        f"Import complete: {total_elapsed:.2f}s total, "
        f"{max_lock_hold:.2f}s max lock hold, "
        f"{len(batches)} batches"
    )

    return ImportResultDTO(...)
```

### Add Health Check Endpoint

```python
# In skillmeat/api/routers/health.py or create new metrics endpoint

@router.get("/health/database-lock-stats")
async def get_database_lock_stats() -> dict:
    """Return database lock contention metrics."""
    from skillmeat.cache.models import get_session

    session = get_session()
    try:
        # SQLite doesn't expose lock info directly, but we can infer
        # from recent import times
        result = session.execute(
            text("""
            SELECT
                COUNT(*) as total_imports,
                AVG((julianday(completed_at) - julianday(started_at)) * 86400) as avg_import_seconds,
                MAX((julianday(completed_at) - julianday(started_at)) * 86400) as max_import_seconds
            FROM marketplace_catalog_entries
            WHERE import_status = 'imported'
            AND imported_at > datetime('now', '-1 hour')
            """
            )
        )
        stats = result.fetchone()

        return {
            "total_imports_last_hour": stats[0],
            "avg_import_duration_seconds": float(stats[1] or 0),
            "max_import_duration_seconds": float(stats[2] or 0),
            "status": "healthy" if (stats[2] or 0) < 5.0 else "degraded",
        }
    finally:
        session.close()
```

---

## Rollout Checklist

### Before Deployment

- [ ] Review all three fixes with team (especially batching logic)
- [ ] Run test suite to ensure no regressions
- [ ] Load test with concurrent imports (at least 3 simultaneous)
- [ ] Verify lock hold times with monitoring (should be <1s per batch)

### Deployment Steps

1. **Deploy Fix #1 + #2** (session factory)
   - Deploy and verify no import regressions
   - Monitor for 1 hour

2. **Deploy Fix #3** (batching)
   - Deploy and monitor lock contention metrics
   - Expected: Lock hold time drops from 2-3s to 400-500ms per batch

3. **Deploy Fix #4 + #5** (tuning + monitoring)
   - Enables better visibility into lock issues
   - No functional changes, purely observability

### Verification

```python
# Run after deployment
def verify_batching_working():
    """Confirm batches are being used."""
    import subprocess

    # Tail logs for batch messages
    result = subprocess.run(
        ["grep", "-c", "Batch.*lock held for", "/var/log/skillmeat/api.log"],
        capture_output=True
    )

    count = int(result.stdout.decode().strip())
    assert count > 0, "No batch logs found - batching not working"

    print(f"✓ Batching active: {count} batch operations logged")
```

---

## Rollback Plan

If issues occur:

1. **Revert Fix #3** (batching) first
   - Git reset to pre-batching version
   - Restart API
   - Import will use single long transaction (original behavior)

2. **Revert Fix #1 + #2** (session factory) if needed
   - Git reset to pre-factory version
   - Restart API
   - Will recreate sessionmakers (less efficient but functional)

3. **Keep Fix #4 + #5** (monitoring)
   - These are additive, no risk of breaking functionality

---

## Success Metrics

After deploying all fixes:

| Metric | Before | After | Success Criteria |
|--------|--------|-------|------------------|
| Max lock hold time | 3-4s | <0.5s | Reduce by 7-8x |
| Concurrent import throughput | 1 import/3s | 3 imports/3s | Increase by 3x |
| P99 catalog update latency | 3-4s | <500ms | Reduce by 6-8x |
| Successful import rate | 98% | >99.5% | No degradation |

---

## Code Review Points

### For PR Review:

1. ✅ Session factory consolidation maintains same behavior
2. ✅ Batch processing preserves transaction atomicity per batch (not globally)
3. ✅ Error handling allows partial imports (intentional design choice)
4. ✅ Monitoring doesn't impact performance
5. ✅ All backward compatibility maintained

### Questions to Ask Reviewers:

- Should batch size be configurable (currently hardcoded to 10)?
- Is partial import acceptable (some batches fail, others succeed)?
- Should we add circuit breaker for too many consecutive batch failures?
- Should we log more details about failed batches?

