# SQLite Locking Patterns - Flow Diagrams

## 1. Current Import Flow (Problematic)

```
POST /marketplace/sources/{source_id}/import
│
├─ Create repositories [No DB]
│  ├─ MarketplaceSourceRepository()
│  ├─ MarketplaceCatalogRepository()
│  └─ MarketplaceTransactionHandler()
│
├─ Verify source exists [Session A: READ]
│  └─ source_repo.get_by_id(source_id)
│     └─ _get_session() → NEW sessionmaker created
│        └─ session.close()
│
├─ Fetch catalog entries [Sessions B, C, D... : READ]
│  ├─ For each entry_id in request.entry_ids:
│  │  └─ catalog_repo.get_by_id(entry_id)
│  │     └─ _get_session() → NEW sessionmaker created per entry
│  │        └─ session.close()
│
├─ Resolve embedded artifacts [Session E: READ]
│  └─ catalog_repo.list_by_source(source_id)
│     └─ _get_session() → NEW sessionmaker created
│        └─ session.close()
│
├─ Import coordination [No DB: ImportCoordinator in-memory]
│  └─ coordinator.import_entries(entries_data, ...)
│
├─ *** LONG TRANSACTION *** [Session F: WRITE - Lines 4293-4357]
│  │   ⚠️  Exclusive lock held entire loop duration
│  │
│  └─ with transaction_handler.import_transaction(source_id):
│     └─ _get_session() → NEW sessionmaker created
│        │
│        ├─ ensure_default_collection(session)  [1 query]
│        │
│        └─ For EACH entry in import_result.entries:  [N iterations]
│           │
│           ├─ populate_collection_artifact_from_import()
│           │  ├─ INSERT into collection_artifacts
│           │  ├─ Potential UPDATE if exists
│           │  └─ FK constraint checks
│           │
│           ├─ Optional: _wire_skill_composite()
│           │  ├─ INSERT into composite_artifacts
│           │  └─ More FK checks
│           │
│           └─ Optional: _import_composite_children()
│              ├─ Recursive import
│              └─ 1-N more INSERT/UPDATE operations
│
│        ⚠️  Lock still held here at end of loop
│        └─ session.commit()  [Releases lock]
│
├─ Handle cache population errors [No DB ops if already failed]
│
└─ *** SECOND TRANSACTION *** [Session G: WRITE - Lines 4359-4380]
   │   ⚠️  Another exclusive lock (shorter, but still a lock)
   │
   └─ with transaction_handler.import_transaction(source_id):
      └─ _get_session() → NEW sessionmaker created
         │
         ├─ ctx.mark_imported(imported_ids, import_id)
         │  └─ UPDATE marketplace_catalog_entries
         │
         └─ ctx.mark_failed(failed_ids, error_msg)
            └─ UPDATE marketplace_catalog_entries

         └─ session.commit()  [Releases lock]
```

### Lock Timeline for 100 Artifacts

```
Time    Event                                    Lock Status
────────────────────────────────────────────────────────────
0.0s    POST /import_artifacts
        Create repositories

0.1s    Session A: get_by_id(source_id)        [READ lock: 5ms]
        Session B-E: get_by_id() × N            [READ locks: 50ms total]

0.2s    ImportCoordinator (in-memory)           [No lock]

1.0s    Session F: enter transaction            [EXCLUSIVE lock acquired]
        ensure_default_collection()              [EXCLUSIVE, held]

1.0s    Loop iteration 1-10
        INSERT ca_1 ... ca_10                    [EXCLUSIVE, held]

1.5s    Loop iteration 11-50                    [EXCLUSIVE, held]
        INSERT ca_11 ... ca_50
        ⚠️ Other requests BLOCKED here

2.5s    Loop iteration 51-100                   [EXCLUSIVE, held]
        INSERT ca_51 ... ca_100
        _wire_skill_composite() × M              [EXCLUSIVE, held]
        _import_composite_children() × K         [EXCLUSIVE, held]

3.5s    Session F: commit()                     [EXCLUSIVE lock released]

3.6s    Session G: enter transaction            [EXCLUSIVE lock acquired]
        mark_imported(100 entries)                [EXCLUSIVE, held]

3.7s    Session G: commit()                     [EXCLUSIVE lock released]

3.7s    Return ImportResultDTO
```

**Result:** Any concurrent write blocked for 3+ seconds (if N=100 artifacts)

---

## 2. Recommended Batched Import Flow

```
POST /marketplace/sources/{source_id}/import
│
├─ [Unchanged: Create repos, verify source, fetch entries, resolve embedded]
│
├─ Import coordination [No DB: ImportCoordinator in-memory]
│
└─ *** BATCHED TRANSACTIONS *** [Multiple short transactions]
   │
   ├─ Batch 1 (entries 1-10) [Session F1: WRITE - ~400ms]
   │  └─ with transaction_handler.import_transaction(source_id):
   │     └─ For entry in batch_1:
   │        ├─ populate_collection_artifact_from_import()
   │        └─ Optional: _wire_skill_composite()
   │     └─ session.commit()  [Releases lock]
   │
   ├─ [Gap: 50ms - other requests can proceed]
   │
   ├─ Batch 2 (entries 11-20) [Session F2: WRITE - ~400ms]
   │  └─ with transaction_handler.import_transaction(source_id):
   │     └─ For entry in batch_2:
   │        ├─ populate_collection_artifact_from_import()
   │        └─ ...
   │     └─ session.commit()
   │
   ├─ [Gap: 50ms]
   │
   ├─ Batch 3 (entries 21-30) [Session F3: WRITE - ~400ms]
   │
   ├─ [Gap: 50ms]
   │
   ├─ ... (continue for all batches)
   │
   └─ Final batch (entries 91-100) [Session FN: WRITE - ~400ms]
      └─ Mark all imported & release lock
```

### Lock Timeline for 100 Artifacts (Batched)

```
Time    Event                                    Lock Status
────────────────────────────────────────────────────────────
0.0s    POST /import_artifacts
        Prepare (repos, verify, fetch)          [READ locks: 100ms total]

0.1s    ImportCoordinator (in-memory)           [No lock]

0.5s    Batch 1: Batch transaction (entries 1-10)
        INSERT ca_1 ... ca_10                    [EXCLUSIVE, held: 400ms]

0.9s    [Gap: Other requests CAN acquire lock here]

1.0s    Batch 2: Batch transaction (entries 11-20)
        INSERT ca_11 ... ca_20                   [EXCLUSIVE, held: 400ms]

1.4s    [Gap: Other requests CAN acquire lock here]

1.5s    Batch 3: Batch transaction (entries 21-30)
        INSERT ca_21 ... ca_30                   [EXCLUSIVE, held: 400ms]

...     [Repeat: 400ms lock + 50ms gap pattern]

4.5s    Batch 10: Final batch transaction
        INSERT ca_91 ... ca_100                  [EXCLUSIVE, held: 400ms]

4.9s    All batches complete, mark_imported()   [EXCLUSIVE, final: 100ms]

5.0s    Return ImportResultDTO
```

**Result:** Concurrent writes only blocked for 400ms at a time (vs 3500ms continuous)

**Concurrency Improvement:** 8.75x better responsiveness (3.5s ÷ 0.4s)

---

## 3. Session Factory Recreation Problem

```
Current Pattern (Inefficient)
─────────────────────────────

Operation                                   What Happens
──────────────────────────────────────────────────────────
source_repo.get_by_id(source_id)
  └─ source_repo._get_session()
     └─ sessionmaker(autocommit=False,     ← Recreates sessionmaker
                     autoflush=False,          (expensive)
                     bind=self.engine)
     └─ SessionLocal()
     └─ Query...
     └─ session.close()

catalog_repo.get_by_id(entry_id)
  └─ catalog_repo._get_session()
     └─ sessionmaker(autocommit=False,     ← Another sessionmaker created
                     autoflush=False,
                     bind=self.engine)
     └─ SessionLocal()
     └─ Query...
     └─ session.close()

transaction_handler.import_transaction()
  └─ self._get_session()
     └─ sessionmaker(autocommit=False,     ← Yet another sessionmaker
                     autoflush=False,
                     bind=self.engine)
     └─ SessionLocal()
     └─ ...operations...
     └─ session.commit()

Result: 3+ sessionmakers created for a single import request
        (should be 1 global SessionLocal)
```

### Recommended Pattern (Efficient)

```
Global Session Factory Pattern
──────────────────────────────

App Startup (lifespan)
  └─ init_session_factory()
     └─ global SessionLocal = sessionmaker(      ← Created ONCE
          autocommit=False,
          autoflush=False,
          bind=engine
        )

Request Processing
  │
  ├─ source_repo.get_by_id(source_id)
  │  └─ source_repo._get_session()
  │     └─ return get_session(self.db_path)
  │        └─ return SessionLocal()              ← Reuses singleton
  │        └─ Query...
  │        └─ session.close()
  │
  ├─ catalog_repo.get_by_id(entry_id)
  │  └─ catalog_repo._get_session()
  │     └─ return get_session(self.db_path)
  │        └─ return SessionLocal()              ← Reuses singleton
  │        └─ Query...
  │        └─ session.close()
  │
  └─ transaction_handler.import_transaction()
     └─ self._get_session()
        └─ return get_session(self.db_path)
           └─ return SessionLocal()              ← Reuses singleton
           └─ ...operations...
           └─ session.commit()

Result: 1 sessionmaker used for entire import request
        (efficient, predictable connection pool behavior)
```

---

## 4. Concurrent Import Contention Scenario

```
Timeline: Two imports of 100 artifacts each

Time    API Request 1                API Request 2
        (import_artifacts)           (import_artifacts)
──────────────────────────────────────────────────
0.0s    POST /sources/A/import
        → Create repos A
        → Verify source A
        → Fetch entries (READ: 50ms)

0.1s                                 POST /sources/B/import
                                     → Create repos B
                                     → Verify source B
                                     → Fetch entries (READ: 50ms)

0.2s    ImportCoordinator A          ImportCoordinator B
        (no DB access)               (no DB access)

0.5s    Session F-A: WRITE lock      (waiting for F-A to release)
        INSERT ca_1-10

0.7s    INSERT ca_11-20              ⚠️ BLOCKED - F-A holds lock

0.9s    INSERT ca_21-30              ⚠️ BLOCKED

...     [All of Request 2 stalled]

2.9s    Session F-A: commit()        Lock released
        Session G-A: WRITE lock      (wait ~100ms for G-A)
        mark_imported()

3.0s    Session G-A: commit()        Lock released

3.1s                                 ✓ NOW Request 2 can proceed
                                     Session F-B: WRITE lock
                                     INSERT ca_1-10 (from Request 2)

...     [Request 2 continues]

6.0s                                 ✓ Request 2 completes
```

**Total Time:** ~6 seconds (sequential)
**With Batching (proposed):** ~3.5 seconds (request 1) + 3.5 seconds (request 2 in parallel) = 3.5s total (interleaved batches)

---

## 5. Lock Behavior Under WAL Mode

```
SQLite WAL (Write-Ahead Logging) Lock Diagram
──────────────────────────────────────────────

Scenario: Import in progress, concurrent catalog update attempt

Time  Action                Lock Type          Block Status
──────────────────────────────────────────────────────────────
0.0s  Import Session F      EXCLUSIVE on DB    Acquired
      enters transaction

      ├─ Acquired via:
      │  └─ First INSERT
      │     triggers write
      │     to WAL file +
      │     exclusive lock
      │     on database
      │
      │
0.5s  Catalog Update        Attempts to get    BLOCKED
      (PATCH /artifacts/)   EXCLUSIVE lock
      calls:
      UPDATE catalog_entries

      ├─ Blocked because:
      │  └─ Already exclusive
      │     lock held by
      │     Import Session F
      │
      │  Waits up to
      │  30 seconds for
      │  Import to release
      │

2.5s  Import Session F      Releases lock      Unblocked
      calls                 (via commit())
      session.commit()

                            Catalog Update
                            now acquires lock
                            (immediate)

2.6s  Catalog Update        Lock acquired      ✓ Succeeds
      completes
      session.commit()

      Lock released
```

**Key Insight:** WAL mode allows readers to proceed while writer is active, but **does not allow two concurrent writers**. Import (writer) blocks catalog updates (writer).

---

## 6. Workflow Orchestration Integration

```
Parallel Workflow Execution & Marketplace Import
────────────────────────────────────────────────

Time  Marketplace Import          Workflow Execution         Lock Status
────────────────────────────────────────────────────────────────────────
0.0s  POST /import (100 items)
      Session F: WRITE lock
      acquired

0.5s  INSERT ca_1-50              POST /workflows/wf1/run
                                  atomic_execution_state_change()
                                  Tries to:
                                  - UPDATE workflow_executions
                                  ⚠️ BLOCKED (30s timeout)

1.5s  INSERT ca_51-100            Still waiting...

2.5s  mark_imported()             Still waiting...
      Session F: WRITE lock
      released

2.6s                              Lock acquired
                                  UPDATE workflow_executions
                                  INSERT execution_steps ×5

2.8s                              Workflow execution
                                  completes

Result: Workflow blocked for 2.6s waiting for import lock
```

**Risk with New Workflow Tables:** Marketplace imports now contend with workflow execution tracking for database locks.

---

## Summary: Impact Visualization

```
Current State (Single 3.5s lock)
────────────────────────────────

Request 1  [████████████████████████████] 3.5s write lock
Request 2  [................████████████████] 3.5s (3.5s blocked) Total: 7s
Request 3  [...................................████████████████] 7s (7s blocked) Total: 10.5s

Proposed (4 × 0.4s batched locks + gaps)
─────────────────────────────────────────

Request 1  [██..██..██..██..] 1.8s total (4 × 0.4s + gaps)
Request 2  [..██..██..██..██] 1.8s total (interleaved with R1)
Request 3  [....██..██..██..] 1.8s total (interleaved with R1/R2)

Max Total Time: 1.8s (vs 10.5s)
Throughput Improvement: 5.8x
```

This visualization shows why batching is critical for concurrent workloads.

