---
schema_version: 2
doc_type: progress
type: progress
prd: "similarity-scoring-overhaul"
feature_slug: "similarity-scoring-overhaul"
prd_ref: "docs/project_plans/PRDs/features/similarity-scoring-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/similarity-scoring-overhaul-v1.md"
phase: 2
title: "Schema + Pre-computation Cache"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 9
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners: ["python-backend-engineer", "data-layer-expert", "ui-engineer-enhanced"]
contributors: []

# === TASKS (SOURCE OF TRUTH) ===
tasks:
  - id: "SSO-2.1"
    description: "Add fingerprint columns to CollectionArtifact: artifact_content_hash, artifact_structure_hash, artifact_file_count, artifact_total_size"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["SSO-1.3"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-2.2"
    description: "Create SimilarityCache ORM model with source/target UUIDs, composite_score, breakdown_json, computed_at"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["SSO-2.1"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-2.3"
    description: "Create SimilarityCacheManager with get_similar(), compute_and_store(), invalidate(), rebuild_all() methods"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-2.2"]
    estimated_effort: "3 pts"
    priority: "high"

  - id: "SSO-2.4"
    description: "Populate fingerprint columns at sync/import time in refresh_single_artifact_cache() path"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-2.2"]
    estimated_effort: "3 pts"
    priority: "high"

  - id: "SSO-2.5"
    description: "Wire cache invalidation into refresh flow: invalidate and rebuild cache after refresh_single_artifact_cache()"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-2.3", "SSO-2.4"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-2.6"
    description: "Update similar endpoint to read from cache first, fall back to live computation, return X-Cache headers"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-2.5"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-2.7"
    description: "Add FTS5 virtual table migration with artifact_uuid, name, title, description, tags columns"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["SSO-2.2"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "SSO-2.8"
    description: "Update frontend hook (use-similar-artifacts.ts) and tab to handle cache indicators and invalidation on edit"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SSO-2.6"]
    estimated_effort: "2 pts"
    priority: "medium"

  - id: "SSO-2.9"
    description: "Write Phase 2 tests: test_similarity_cache.py, migration test, content_score test"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SSO-2.6"]
    estimated_effort: "2 pts"
    priority: "high"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["SSO-2.1"]
  batch_2: ["SSO-2.2", "SSO-2.7"]
  batch_3: ["SSO-2.3", "SSO-2.4"]
  batch_4: ["SSO-2.5"]
  batch_5: ["SSO-2.6"]
  batch_6: ["SSO-2.8", "SSO-2.9"]
  critical_path: ["SSO-2.1", "SSO-2.2", "SSO-2.3", "SSO-2.5", "SSO-2.6", "SSO-2.8"]
  estimated_total_time: "~2.5 days (18 pts)"

# Critical Blockers
blockers: []

# Success Criteria
success_criteria:
  - id: "SC-1"
    description: "Tab loads in < 200ms from cache for warm cache"
    status: "pending"
  - id: "SC-2"
    description: "Cache rebuilds in < 60s for 1000 artifacts (full rebuild)"
    status: "pending"
  - id: "SC-3"
    description: "Incremental update for single artifact < 1s"
    status: "pending"
  - id: "SC-4"
    description: "_compute_content_score() returns > 0 for artifacts with shared content hashes"
    status: "pending"
  - id: "SC-5"
    description: "FTS5 pre-filter reduces full-score computation from O(n) to O(50) candidates"
    status: "pending"
  - id: "SC-6"
    description: "Alembic migration runs cleanly against existing DB with no data loss"
    status: "pending"
  - id: "SC-7"
    description: "X-Cache response headers present on all /similar responses"
    status: "pending"

# Files Modified
files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/similarity_cache.py"
  - "skillmeat/core/similarity.py"
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/web/hooks/use-similar-artifacts.ts"
  - "skillmeat/web/components/collection/similar-artifacts-tab.tsx"
  - "alembic/versions/XXXX_add_similarity_cache.py"
  - "tests/test_similarity_cache.py"
  - "tests/test_similarity_integration.py"
---

# Similarity Scoring Overhaul - Phase 2: Schema + Pre-computation Cache

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/similarity-scoring-overhaul/phase-2-progress.md \
  -t SSO-2.1 -s completed
```

---

## Objective

Pre-compute similarity at sync/import time so tab loads become cache lookups. Target: <200ms response from cache, <1s incremental update for single artifact. Adds SQLite FTS5 pre-filtering, a `similarity_cache` table, and fingerprint columns to `CollectionArtifact`.

---

## Implementation Notes

### Architectural Decisions

**Pre-computation Cache Architecture**
- `similarity_cache` table stores top-20 results per artifact (O(n) storage, not O(n²))
- Composite primary key: (source_artifact_uuid, target_artifact_uuid) with indexed lookup
- Cache invalidation: when `refresh_single_artifact_cache()` runs for artifact X, delete all rows where source or target equals X
- Rationale: Gradual cache invalidation prevents O(n²) full rebuilds on single artifact changes

**FTS5 Pre-filtering**
- SQLite FTS5 available in Python's standard `sqlite3` module (no new dependencies)
- Virtual table with columns: artifact_uuid UNINDEXED, name, title, description, tags
- Tokenizer: porter ascii (standard, handles plural/stemming)
- Pre-filter reduces full-score computation from O(n) to O(50) candidates before scoring
- Rationale: BM25-based FTS5 is database-native and requires zero additional packages

**Fingerprint Persistence**
- Add to `CollectionArtifact`: artifact_content_hash, artifact_structure_hash, artifact_file_count, artifact_total_size
- Populate during sync/import from filesystem metadata
- `_compute_content_score()` reads from these fields instead of empty `Artifact` fields
- Rationale: Content scoring was always returning 0.0 because hashes weren't persisted; fixing this restores the content dimension

**Cache Headers**
- Response includes `X-Cache: HIT|MISS` and `X-Cache-Age: <seconds>` headers
- Frontend uses headers to display "cached 2m ago" indicator
- React Query cache invalidated on artifact edit events
- Rationale: User visibility into cache freshness + event-driven invalidation prevents stale results

### Patterns and Best Practices

- **Alembic Migrations**: Use `batch_alter_table` mode for SQLite compatibility (ALTER TABLE limitations)
- **FTS5 Virtual Table**: Created via raw SQL (not ORM) in migration with `CREATE VIRTUAL TABLE` statement
- **Cache Manager Pattern**: Single entry point for all cache operations (get, compute, invalidate, rebuild)
- **Graceful FTS5 Fallback**: Check `SELECT fts5()` at startup; log warning and skip pre-filter if unavailable
- **Incremental Updates**: After single artifact sync, only recompute that artifact's cache (not full rebuild)

### Known Gotchas

- **SQLite ALTER TABLE Limitations**: Some operations not available. MUST use `batch_alter_table` mode in Alembic migrations.
- **FTS5 Token Order**: Token sequence in virtual table doesn't affect search, but UNINDEXED on artifact_uuid prevents it from being tokenized.
- **Cascade Deletes**: FK cascade on both UUID columns must be verified; deleting an artifact should remove its cache rows automatically.
- **Fingerprint Population Rate**: If diagnostic query shows 0% populated after migration, there's likely a pipeline bug. Check before Phase 2 work.
- **Cache Coherency**: If cache is stale immediately after sync, first request triggers recompute; second request hits cache. Document this in UI.
- **FTS5 Rebuild**: FTS5 virtual table does not auto-sync from parent tables. Rebuild FTS5 entries during `refresh_single_artifact_cache()`.

### Development Setup

**Database Setup**:
```bash
# Create test DB with new schema
alembic upgrade head
```

**FTS5 Availability Check**:
```python
import sqlite3
try:
    conn = sqlite3.connect(':memory:')
    conn.execute('SELECT fts5()')
    print("FTS5 available")
except sqlite3.OperationalError:
    print("FTS5 not available")
```

**Test Execution**:
```bash
pytest tests/test_similarity_cache.py -v
pytest tests/test_similarity_integration.py -v
```

**Manual Verification**:
After Phase 2 is complete:
1. Trigger a sync and verify fingerprint columns are populated: `SELECT COUNT(*), COUNT(artifact_content_hash) FROM collection_artifacts`
2. Access Similar Artifacts tab and verify response time < 200ms for warm cache
3. Check response headers: `curl -i http://localhost:8080/api/v1/artifacts/{id}/similar | grep -i X-Cache`

---

## Completion Notes

_To be filled in when phase is complete._

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase (Phase 3: embeddings)
