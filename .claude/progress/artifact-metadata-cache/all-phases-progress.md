---
type: progress
prd: "artifact-metadata-cache-v1"
status: pending
progress: 0
total_phases: 4
total_tasks: 18
estimated_effort: "10-14 hours"
start_date: 2026-02-01

parallelization:
  batch_1:
    phase: 1
    tasks: [TASK-1.1, TASK-1.2, TASK-1.3, TASK-1.4, TASK-1.5]
    max_parallel: 3
    blocked_by: []
  batch_2:
    phase: 2
    tasks: [TASK-2.1, TASK-2.2, TASK-2.3, TASK-2.4, TASK-2.5]
    max_parallel: 3
    blocked_by: [TASK-1.4]
  batch_3:
    phase: 3
    tasks: [TASK-3.1, TASK-3.2, TASK-3.3, TASK-3.4]
    max_parallel: 2
    blocked_by: [TASK-2.2]
  batch_4:
    phase: 4
    tasks: [TASK-4.1, TASK-4.2, TASK-4.3]
    max_parallel: 2
    blocked_by: [TASK-2.1, TASK-2.2]
    optional: true

tasks:
  TASK-1.1:
    id: TASK-1.1
    title: "Add metadata fields to Artifact model"
    description: "Extend skillmeat/cache/models.py Artifact model with description, author, license, tags, resolved_sha, resolved_version, synced_at fields"
    phase: 1
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "30-40 min"
    dependencies: []
    files:
      - skillmeat/cache/models.py
    notes: "Use SQLAlchemy Column types: String, DateTime, JSON for tags array"

  TASK-1.2:
    id: TASK-1.2
    title: "Create Alembic migration for new metadata fields"
    description: "Generate and verify Alembic migration to add 7 new columns to artifact table without breaking existing data"
    phase: 1
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "20-30 min"
    dependencies: [TASK-1.1]
    files:
      - skillmeat/api/alembic/versions/
    notes: "Use nullable=True for all new columns initially; test with existing artifact data"

  TASK-1.3:
    id: TASK-1.3
    title: "Create populate_artifact_metadata() function"
    description: "Implement populate_artifact_metadata(session, artifact_mgr, collection_id) in skillmeat/api/routers/user_collections.py that reads file-based artifacts and creates/updates Artifact cache records"
    phase: 1
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "45-60 min"
    dependencies: [TASK-1.1]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/core/artifact.py
    notes: "Loop through collection.artifacts, extract metadata from YAML frontmatter, create Artifact records with synced_at=now()"

  TASK-1.4:
    id: TASK-1.4
    title: "Integrate with migrate_artifacts_to_default_collection()"
    description: "Modify migrate_artifacts_to_default_collection() to call populate_artifact_metadata() after creating CollectionArtifact associations"
    phase: 1
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "15-20 min"
    dependencies: [TASK-1.3]
    files:
      - skillmeat/api/routers/user_collections.py
    notes: "Call populate_artifact_metadata() at end of migration function; ensure transactional consistency"

  TASK-1.5:
    id: TASK-1.5
    title: "Add startup sync logging"
    description: "Log startup artifact cache population: count of artifacts synced, fields populated, any errors encountered"
    phase: 1
    status: pending
    assigned_to: python-backend-engineer
    priority: medium
    effort: "10-15 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/server.py
      - skillmeat/api/routers/user_collections.py
    notes: "Use structured logging; log before and after populate_artifact_metadata() call"

  TASK-2.1:
    id: TASK-2.1
    title: "Create sync single artifact endpoint"
    description: "Implement POST /api/v1/user-collections/sync-artifact with artifact_id param that fetches file-based artifact and updates Artifact cache record"
    phase: 2
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "40-50 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/api/schemas.py
    notes: "Response: {artifact_id, synced_at, fields_updated, status}; Handle missing artifacts gracefully"

  TASK-2.2:
    id: TASK-2.2
    title: "Create batch refresh endpoint"
    description: "Implement POST /api/v1/user-collections/refresh-metadata with optional filters (older_than_minutes, tags) to refresh multiple artifacts"
    phase: 2
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "50-60 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/api/schemas.py
    notes: "Query Artifact records by TTL age; support filtering; return {artifacts_refreshed, skipped, errors}"

  TASK-2.3:
    id: TASK-2.3
    title: "Add endpoint parameters validation"
    description: "Validate request parameters: artifact_id required for sync, filters valid for refresh; enforce rate limiting for batch operations"
    phase: 2
    status: pending
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-30 min"
    dependencies: [TASK-2.1, TASK-2.2]
    files:
      - skillmeat/api/schemas.py
      - skillmeat/api/middleware/rate_limit.py
    notes: "Use Pydantic validators; implement exponential backoff for GitHub file fetches"

  TASK-2.4:
    id: TASK-2.4
    title: "Add error handling and logging"
    description: "Implement comprehensive error handling for sync/refresh endpoints: GitHub API failures, malformed metadata, missing fields"
    phase: 2
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "30-40 min"
    dependencies: [TASK-2.1, TASK-2.2]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/api/schemas.py
    notes: "Log all errors with context; return detailed error messages in 400/500 responses; track error metrics"

  TASK-2.5:
    id: TASK-2.5
    title: "Add unit tests for endpoints"
    description: "Test sync and refresh endpoints: successful sync, missing artifacts, partial failures, batch operations with filters"
    phase: 2
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "45-60 min"
    dependencies: [TASK-2.1, TASK-2.2, TASK-2.4]
    files:
      - skillmeat/api/routers/__tests__/test_user_collections.py
    notes: "Mock ArtifactManager, test happy path and error cases; verify database state after sync"

  TASK-3.1:
    id: TASK-3.1
    title: "Create staleness detection service"
    description: "Implement ArtifactCacheService.is_stale(artifact_id, ttl_minutes=30) that checks synced_at timestamp and identifies artifacts needing refresh"
    phase: 3
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "25-35 min"
    dependencies: [TASK-2.2]
    files:
      - skillmeat/api/services/artifact_cache.py
    notes: "Compare synced_at against current time; configurable TTL; return stale count for monitoring"

  TASK-3.2:
    id: TASK-3.2
    title: "Create cache invalidation hook"
    description: "Implement invalidation mechanism triggered by: collection updates, artifact additions, version changes; automatically refresh affected metadata"
    phase: 3
    status: pending
    assigned_to: python-backend-engineer
    priority: high
    effort: "35-45 min"
    dependencies: [TASK-3.1]
    files:
      - skillmeat/api/services/artifact_cache.py
      - skillmeat/api/routers/user_collections.py
    notes: "Hook into CollectionManager events; mark artifacts stale on version/manifest changes; trigger async refresh"

  TASK-3.3:
    id: TASK-3.3
    title: "Create background refresh task (optional)"
    description: "Implement optional Celery/APScheduler task to periodically refresh stale metadata in background without blocking API requests"
    phase: 3
    status: pending
    assigned_to: python-backend-engineer
    priority: low
    effort: "40-50 min"
    dependencies: [TASK-3.1, TASK-3.2]
    files:
      - skillmeat/api/tasks/artifact_refresh.py
      - skillmeat/api/server.py
    notes: "Optional: start with manual refresh via endpoint, add background task if performance metrics warrant"

  TASK-3.4:
    id: TASK-3.4
    title: "Add monitoring metrics"
    description: "Track cache hit rate, refresh latency, stale artifact count; emit to observability system for dashboard"
    phase: 3
    status: pending
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-30 min"
    dependencies: [TASK-3.1, TASK-3.2]
    files:
      - skillmeat/api/services/artifact_cache.py
      - skillmeat/observability/metrics.py
    notes: "Use Prometheus-style metrics; track: hits, misses, refresh_duration, stale_count"

  TASK-4.1:
    id: TASK-4.1
    title: "Add sync hook to CLI add command"
    description: "Integrate sync-artifact endpoint call into CLI add command; after artifact added to collection.toml, trigger API to populate cache"
    phase: 4
    status: pending
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-25 min"
    dependencies: [TASK-2.1]
    files:
      - skillmeat/cli.py
      - skillmeat/core/collection_manager.py
    notes: "Optional Phase: Call POST /sync-artifact after manifest updated; log sync status to CLI user"

  TASK-4.2:
    id: TASK-4.2
    title: "Add refresh hook to CLI sync command"
    description: "Integrate refresh-metadata endpoint call into CLI sync command; after collection.toml synced, trigger batch refresh"
    phase: 4
    status: pending
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-25 min"
    dependencies: [TASK-2.2]
    files:
      - skillmeat/cli.py
      - skillmeat/core/collection_manager.py
    notes: "Optional Phase: Call POST /refresh-metadata; show user progress of refresh operation"

  TASK-4.3:
    id: TASK-4.3
    title: "Test end-to-end CLI→API→DB flow"
    description: "E2E test: CLI add artifact → API syncs metadata → database updated → API query returns full data"
    phase: 4
    status: pending
    assigned_to: python-backend-engineer
    priority: medium
    effort: "25-30 min"
    dependencies: [TASK-4.1, TASK-4.2]
    files:
      - skillmeat/tests/test_cli_artifact_sync.py
    notes: "Optional Phase: Full integration test from CLI through to web API; verify /collection page performance"

completion_criteria:
  Phase 1: "Artifact model extended, migration applied, startup sync populates cache with 100% of artifacts"
  Phase 2: "Incremental sync endpoints tested with 95%+ success rate; batch refresh handles filters and errors"
  Phase 3: "Staleness detection working, invalidation triggers on collection changes, metrics emitted"
  Phase 4: "CLI commands integrated and E2E tested (optional); all sync mechanisms coordinated"

success_metrics:
  - "Database Artifact table contains metadata for 100% of file-based artifacts"
  - "/collection page response time <100ms (database-backed)"
  - "Cache invalidation automatic and reliable"
  - "Metadata staleness bounded by TTL (default 30 min)"
---

# Artifact Metadata Cache v1 Progress

**Plan Reference**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`

## Overview

This 4-phase implementation plan populates and maintains a complete artifact metadata cache in the database, enabling the `/collection` page to operate entirely from the database with sub-100ms response times. Follow-on enhancement to collection-data-consistency-v1 (Phase 5).

**Current Status**: Pending (not started)  
**Total Effort**: 10-14 hours across 2-3 days  
**Team**: python-backend-engineer (all phases)

---

## Phase 1: Enhanced Sync Function & Schema (3-4 hours)

**Objective**: Establish database schema and populate metadata cache at startup

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-1.1: Add metadata fields to Artifact model | pending | 30-40 min | python-backend-engineer |
| TASK-1.2: Create Alembic migration | pending | 20-30 min | python-backend-engineer |
| TASK-1.3: Create populate_artifact_metadata() function | pending | 45-60 min | python-backend-engineer |
| TASK-1.4: Integrate with migrate_artifacts_to_default_collection() | pending | 15-20 min | python-backend-engineer |
| TASK-1.5: Add startup sync logging | pending | 10-15 min | python-backend-engineer |

**Completion Criteria**: Artifact model extended, migration applied, startup sync populates 100% of artifacts

---

## Phase 2: Incremental Sync & API Endpoints (3-4 hours)

**Objective**: Enable CLI triggers to keep cache updated after collection changes

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-2.1: Create sync single artifact endpoint | pending | 40-50 min | python-backend-engineer |
| TASK-2.2: Create batch refresh endpoint | pending | 50-60 min | python-backend-engineer |
| TASK-2.3: Add endpoint parameters validation | pending | 20-30 min | python-backend-engineer |
| TASK-2.4: Add error handling and logging | pending | 30-40 min | python-backend-engineer |
| TASK-2.5: Add unit tests for endpoints | pending | 45-60 min | python-backend-engineer |

**Completion Criteria**: Incremental sync endpoints tested with 95%+ success rate; batch refresh handles filters and errors

**Dependencies**: Phase 1 complete (TASK-1.4)

---

## Phase 3: Cache Invalidation & TTL-Based Refresh (2-3 hours)

**Objective**: Automatic staleness detection and cache invalidation

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-3.1: Create staleness detection service | pending | 25-35 min | python-backend-engineer |
| TASK-3.2: Create cache invalidation hook | pending | 35-45 min | python-backend-engineer |
| TASK-3.3: Create background refresh task (optional) | pending | 40-50 min | python-backend-engineer |
| TASK-3.4: Add monitoring metrics | pending | 20-30 min | python-backend-engineer |

**Completion Criteria**: Staleness detection working, invalidation triggers on collection changes, metrics emitted

**Dependencies**: Phase 2 complete (TASK-2.2)

---

## Phase 4: CLI Integration Hooks (1-2 hours, OPTIONAL)

**Objective**: Coordinate CLI commands with API cache operations

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-4.1: Add sync hook to CLI add command | pending | 20-25 min | python-backend-engineer |
| TASK-4.2: Add refresh hook to CLI sync command | pending | 20-25 min | python-backend-engineer |
| TASK-4.3: Test end-to-end CLI→API→DB flow | pending | 25-30 min | python-backend-engineer |

**Completion Criteria**: CLI commands integrated and E2E tested; all sync mechanisms coordinated

**Dependencies**: Phase 2 complete (TASK-2.1, TASK-2.2)

**Note**: This phase is optional; prioritize phases 1-3 for immediate performance gain.

---

## Quick Reference: Task Delegation Commands

### Phase 1: Startup Sync & Schema

```bash
# Execute Phase 1 batch (tasks can run in parallel)
Task("python-backend-engineer", "Implement TASK-1.1, TASK-1.2, TASK-1.3 in parallel:\n\nTASK-1.1: Add metadata fields (description, author, license, tags, resolved_sha, resolved_version, synced_at) to Artifact model in skillmeat/cache/models.py\n\nTASK-1.2: Create Alembic migration to add new columns to artifact table\n\nTASK-1.3: Implement populate_artifact_metadata(session, artifact_mgr, collection_id) in skillmeat/api/routers/user_collections.py\n\nReference: /docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md", model="opus")

Task("python-backend-engineer", "Implement TASK-1.4 and TASK-1.5 after Phase 1.1-1.3 complete:\n\nTASK-1.4: Integrate populate_artifact_metadata() call into migrate_artifacts_to_default_collection()\n\nTASK-1.5: Add structured logging for artifact cache population at startup\n\nFile: skillmeat/api/routers/user_collections.py", model="opus")
```

### Phase 2: Incremental Sync Endpoints

```bash
# Execute Phase 2 batch (block on Phase 1, tasks can run in parallel)
Task("python-backend-engineer", "Implement TASK-2.1 and TASK-2.2 in parallel:\n\nTASK-2.1: Create POST /api/v1/user-collections/sync-artifact endpoint for single artifact sync\n\nTASK-2.2: Create POST /api/v1/user-collections/refresh-metadata endpoint for batch refresh with filtering\n\nFiles: skillmeat/api/routers/user_collections.py, skillmeat/api/schemas.py", model="opus")

Task("python-backend-engineer", "Implement TASK-2.3, TASK-2.4, TASK-2.5:\n\nTASK-2.3: Validate endpoint parameters and enforce rate limiting\n\nTASK-2.4: Comprehensive error handling for GitHub API failures and metadata issues\n\nTASK-2.5: Unit tests for endpoints covering happy path and error cases\n\nFiles: skillmeat/api/routers/user_collections.py, skillmeat/api/schemas.py, tests/", model="opus")
```

### Phase 3: Cache Invalidation

```bash
# Execute Phase 3 batch (block on Phase 2 complete)
Task("python-backend-engineer", "Implement TASK-3.1, TASK-3.2, TASK-3.3, TASK-3.4:\n\nTASK-3.1: Create ArtifactCacheService.is_stale() for staleness detection\n\nTASK-3.2: Implement cache invalidation hook triggered by collection changes\n\nTASK-3.3: Create optional background refresh task (APScheduler/Celery)\n\nTASK-3.4: Add observability metrics (cache hit rate, refresh latency, stale count)\n\nFiles: skillmeat/api/services/artifact_cache.py, skillmeat/observability/metrics.py", model="opus")
```

### Phase 4: CLI Integration (Optional)

```bash
# Execute Phase 4 batch (optional, block on Phase 2 complete)
Task("python-backend-engineer", "Implement TASK-4.1, TASK-4.2, TASK-4.3:\n\nTASK-4.1: Add sync-artifact endpoint hook to CLI add command\n\nTASK-4.2: Add refresh-metadata endpoint hook to CLI sync command\n\nTASK-4.3: E2E test CLI→API→DB flow\n\nFiles: skillmeat/cli.py, skillmeat/core/collection_manager.py, tests/", model="opus")
```

---

## Key Files to Modify

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/cache/models.py` | Add metadata fields to Artifact model | 1 |
| `skillmeat/api/alembic/versions/` | Migration scripts | 1 |
| `skillmeat/api/routers/user_collections.py` | Sync functions and endpoints | 1-2 |
| `skillmeat/api/schemas.py` | Request/response schemas | 2 |
| `skillmeat/api/services/artifact_cache.py` | NEW: Cache service logic | 3 |
| `skillmeat/api/middleware/rate_limit.py` | Rate limiting for batch ops | 2 |
| `skillmeat/observability/metrics.py` | Metrics emission | 3 |
| `skillmeat/cli.py` | CLI command hooks | 4 |
| `skillmeat/core/collection_manager.py` | Collection event hooks | 4 |

---

## Related Documentation

- **Plan Reference**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`
- **Predecessor**: `/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md`
- **Architecture**: `/docs/project_plans/reports/dual-collection-system-architecture-analysis.md`
- **Design**: `/docs/project_plans/reports/manage-collection-page-architecture-analysis.md`
