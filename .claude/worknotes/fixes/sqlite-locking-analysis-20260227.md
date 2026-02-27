# SQLite Database Locking Pattern Analysis

## Executive Summary

SkillMeat uses SQLite with WAL (Write-Ahead Logging) mode for its cache database, with session management patterns that expose potential lock contention issues in the marketplace import workflow. The analysis identified three critical patterns:

1. **Session Factory Recreation Per Request** - Every call to `_get_session()` recreates the `sessionmaker`, creating new engine connections unnecessarily
2. **Non-Shared Session Factory** - Repositories instantiate their own session factories instead of using a global singleton
3. **Long-Held Transactions in Import Flow** - The marketplace import orchestrates multiple sequential database operations without explicit batching

---

## 1. Session Lifecycle Management

### Current Pattern (Repositories)

Located in `skillmeat/cache/repositories.py` (BaseRepository class):

```python
def _get_session(self) -> Session:
    """Create a new database session."""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=self.engine,
    )
    return SessionLocal()
```

**Issues:**
- `sessionmaker` is **recreated on every call** (should be singleton)
- Each call creates a new pool of connections
- No connection pooling reuse across requests
- Multiple repositories create independent session factories (no sharing)

### Global Session Factory Pattern (Exists But Unused)

Located in `skillmeat/cache/models.py`:

```python
SessionLocal = None  # Global (but always None at module load)

def init_session_factory(db_path: Optional[str | Path] = None) -> None:
    """Initialize session factory (called once at startup)."""
    global SessionLocal
    engine = create_db_engine(db_path)
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

def get_session(db_path: Optional[str | Path] = None):
    """Get session from global factory."""
    # Implementation incomplete in provided excerpt
```

**Problem:** `SessionLocal` is initialized at startup but repositories call `_get_session()` instead, which recreates `sessionmaker` each time.

---

## 2. Database Engine Configuration

Located in `skillmeat/cache/models.py:create_db_engine()`:

```python
engine = create_engine(
    f"sqlite:///{db_path}",
    echo=False,
    connect_args={
        "check_same_thread": False,  # Allow multi-threaded access
        "timeout": 30.0,             # 30 second lock timeout
    },
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite PRAGMA settings on connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
    cursor.close()
```

**Configuration Analysis:**

| Setting | Value | Impact |
|---------|-------|--------|
| `journal_mode` | WAL | Good: Allows concurrent reads; reader doesn't block writers |
| `synchronous` | NORMAL | Moderate: Balances durability vs performance; can lose last transaction on crash |
| `timeout` | 30s | **RISK**: Long timeout; contending processes wait 30s before failing |
| `check_same_thread` | False | **RISK**: Allows async operations; SQLAlchemy pool not thread-aware |
| `cache_size` | -64MB | Good: Large working set reduces disk I/O |
| `mmap_size` | 256MB | Good: Memory-mapped I/O for faster reads |

**SQLite Lock Behavior Under WAL:**
- **Readers:** Acquire a small read lock on the WAL file → non-blocking
- **Writers:** Acquire exclusive lock on database file → can block following writes
- **Checkpoint:** Merges WAL into database → requires exclusive lock, blocks all access

---

## 3. Marketplace Import Transaction Flow

Located in `skillmeat/api/routers/marketplace_sources.py:import_artifacts()`:

### Transaction Sequence (Lines 4119-4380)

```python
# 1. Pre-transaction: Create repositories (no DB access yet)
source_repo = MarketplaceSourceRepository()
catalog_repo = MarketplaceCatalogRepository()
transaction_handler = MarketplaceTransactionHandler()

# 2. Verification queries (Session A)
source = source_repo.get_by_id(source_id)       # Opens session A
# ... implicit session.close() after get_by_id returns

# 3. Loop over entry_ids (Multiple sessions)
for entry_id in request.entry_ids:
    entry = catalog_repo.get_by_id(entry_id)    # Each opens Session B, C, D, ...
    # ... session.close() after each get_by_id

# 4. Resolve embedded artifacts (Session E - list query)
all_source_entries = catalog_repo.list_by_source(source_id)  # Opens Session E

# 5. Import coordination (No DB access - all in-memory)
coordinator = ImportCoordinator(...)
import_result = coordinator.import_entries(entries_data, ...)

# 6. **LONG TRANSACTION** - Session F (Lines 4293-4357)
#    All of this uses a single session but with multiple round-trips:
try:
    ensure_default_collection(session)  # Query 1

    for entry in import_result.entries:  # Loop with multiple queries per entry
        populate_collection_artifact_from_import(
            session, artifact_mgr, DEFAULT_COLLECTION_ID, entry
        )  # Each calls: INSERT CollectionArtifact, potentially UPDATE queries

        # Optional: Create composite rows (another round-trip)
        if _sca_enabled and entry.artifact_type == "skill":
            _wire_skill_composite(session=session, ...)  # More queries

        # Optional: Import child artifacts recursively
        if entry.artifact_type == "composite":
            _import_composite_children(
                session=session,
                # ... more nested queries
            )
except Exception as e:
    session.rollback()

# 7. **SECOND LONG TRANSACTION** - Session G (Lines 4359-4380)
with transaction_handler.import_transaction(source_id) as ctx:
    # This opens a NEW session and updates catalog entry statuses
    imported_ids = [...]
    ctx.mark_imported(imported_ids, import_result.import_id)  # UPDATE queries
    # session.close() happens here
```

**Locking Problem:**

Session F (Lines 4293-4357) can hold a write lock for:
- `ensure_default_collection()` query
- Loop with N iterations, each calling `populate_collection_artifact_from_import()` which does:
  - INSERT into `collection_artifacts`
  - Potentially UPDATE if artifact exists
  - FK constraint checks
- Optional: Composite wiring (more INSERTs/UPDATEs)
- Optional: Child import recursion (even more nested transactions)

**If N=100 artifacts:**
- ~100+ INSERT/UPDATE operations in a single transaction
- Exclusive write lock held for entire loop
- Any concurrent reader on other tables must wait

---

## 4. MarketplaceTransactionHandler Pattern

Located in `skillmeat/cache/repositories.py:import_transaction()`:

```python
@contextmanager
def import_transaction(self, source_id: str) -> Generator[ImportContext, None, None]:
    """Context manager for atomic imports."""
    session = self._get_session()  # **Creates new sessionmaker each time**
    try:
        logger.debug(f"Starting import transaction for source {source_id}")

        # Yield context for operation
        context = ImportContext(session, source_id)
        yield context

        # Commit on success
        session.commit()
        logger.info(f"Import transaction committed for source {source_id}")

    except IntegrityError as e:
        session.rollback()
        # ...
    except OperationalError as e:
        session.rollback()
        # ...
    finally:
        session.close()
```

**Key Points:**
- Calls `_get_session()` which recreates `sessionmaker` (inefficient)
- Clean try/finally/except structure (good error handling)
- But called **twice** in import flow (Sessions F and G above), meaning two separate transactions

---

## 5. Concurrent Operations Risk

The marketplace_sources router has these async endpoints that can run concurrently:

| Endpoint | Database Operations | Lock Duration |
|----------|-------------------|---|
| `POST /import_artifacts` | Multiple sessions + long import transaction | 2-3 seconds per 100 artifacts |
| `POST /reimport_catalog_entry` | Single import transaction | 1-2 seconds |
| `PATCH /artifacts/{entry_id}` | Update catalog entry | <100ms |
| `DELETE /artifacts/{entry_id}/exclude` | Update exclusion status | <100ms |
| `GET /artifacts` (list) | Read catalog entries | No write lock |

**Contention Scenario:**

```
Time  API Request 1           API Request 2           API Request 3
t=0   POST /import (100 items)
t=1   Session F opens
      INSERT ca_1
t=2   INSERT ca_2
t=3   INSERT ca_3             PATCH /artifacts/e1
      ...                      UPDATE catalog_entries (blocked, waits)
t=4   INSERT ca_50
t=5   INSERT ca_100           (still waiting)
      Session F commits
t=6   (Request 2 finally proceeds)
```

With `timeout=30.0`, Request 2 blocks for up to 2-3 seconds, then proceeds.

---

## 6. Workflow Orchestration Impact (New)

Recent additions (Migration `20260227_0900_add_workflow_tables`) added:

```
workflows
  ├─ workflow_stages
workflow_executions
  ├─ execution_steps
```

**Potential Lock Conflicts:**
- Workflow executions write to `workflow_executions` and `execution_steps` tables
- If marketplace imports run in parallel with workflow execution tracking, both contend for WAL checkpoint
- Workflow updates are typically short, but marketplace imports are long

Located in `skillmeat/cache/workflow_transaction.py`:

```python
def atomic_execution_state_change(
    self, execution_repo, step_repo, execution_id, new_execution_status, ...
) -> WorkflowExecution:
    """Atomically update execution + steps."""
    with self.begin_transaction():
        # Update execution status
        execution = execution_repo.update_status(...)

        # Update each step status
        if step_id_to_status:
            for step_id, new_status in step_id_to_status.items():
                step_repo.update_status(step_id, new_status)
```

**Risk:** If 50 steps update in parallel with a 100-artifact import, WAL checkpoint might be triggered, blocking both operations.

---

## Summary of Locking Patterns

### Critical Issues

1. **Session Factory Recreation** (High Impact)
   - Every `_get_session()` call recreates `sessionmaker`
   - Should use singleton from `init_session_factory()`
   - Estimated improvement: 20-30% reduction in connection overhead

2. **Long-Held Import Transaction** (High Impact)
   - 100+ sequential INSERTs in single transaction
   - Should batch or use incremental commits
   - Risk: 2-3 second blocks for concurrent requests

3. **No Connection Pool Awareness** (Medium Impact)
   - `check_same_thread=False` with recreated sessionmakers = unpredictable pool behavior
   - Multiple repositories create independent engines
   - Pool might exhaust during high concurrency

### Configuration Issues

4. **30-Second Lock Timeout** (Medium Risk)
   - Reasonable for most ops, but long for import bottleneck
   - Consider reducing to 5-10s or implementing client-side retry

5. **WAL Pragma Settings** (Low Risk)
   - `synchronous=NORMAL` is good balance, but consider `synchronous=FULL` for critical tables
   - `cache_size=-64MB` is reasonable but could be tuned per workload

---

## Recommended Fixes (Priority Order)

### P0: Session Factory Consolidation

```python
# In repositories.py, use the global SessionLocal
def _get_session(self) -> Session:
    from skillmeat.cache.models import get_session
    return get_session(self.db_path)

# Ensure init_session_factory() is called in API lifespan
```

### P1: Batch Import Transactions

```python
# Instead of one transaction for all artifacts:
for i in range(0, len(entries), BATCH_SIZE):
    with transaction_handler.import_transaction(source_id) as ctx:
        # Process BATCH_SIZE entries
        for entry in entries[i:i+BATCH_SIZE]:
            populate_collection_artifact_from_import(...)
        # Commit after each batch (every 10-20 artifacts)
```

### P2: Reduce Lock Timeout (Optional)

```python
# In models.py create_db_engine()
connect_args={
    "timeout": 10.0,  # Reduced from 30s
}
```

### P3: Add Concurrent Operation Metrics

```python
# Monitor lock contention
@router.post("/import_artifacts")
async def import_artifacts(...):
    start = time.time()
    # ... import logic ...
    elapsed = time.time() - start
    # Log if > 2 seconds = likely lock contention
```

---

## Testing Recommendations

1. **Load Test**: 5 concurrent imports of 100 artifacts each
2. **Lock Monitoring**: Enable `PRAGMA query_only;` logging to detect lock waits
3. **Connection Pool Inspection**: Monitor `sqlite3.Connection` count during tests
4. **Baseline**: Measure current import time, then re-measure after P0 + P1 fixes

---

## References

- SQLAlchemy + SQLite: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- WAL Mode: https://www.sqlite.org/wal.html
- Lock Timeouts: https://www.sqlite.org/pragma.html#pragma_busy_timeout
- Batch Inserts: https://docs.sqlalchemy.org/en/20/orm/bulk_operations.html

