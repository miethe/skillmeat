---
type: progress
prd: "artifact-metadata-cache-v1"
status: completed
progress: 100
total_phases: 5
total_tasks: 26
estimated_effort: "12-16 hours (Phases 1-4) + 6-8 hours (Phase 5 future)"
start_date: 2026-02-01

parallelization:
  batch_1:
    phase: 1
    tasks: [TASK-1.1, TASK-1.2, TASK-1.3, TASK-1.4, TASK-1.5]
    max_parallel: 3
    blocked_by: []
  batch_2:
    phase: 2
    tasks: [TASK-2.1, TASK-2.2, TASK-2.3, TASK-2.4, TASK-2.5, TASK-2.6, TASK-2.7, TASK-2.8, TASK-2.9]
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
  batch_5:
    phase: 5
    tasks: [TASK-5.1, TASK-5.2, TASK-5.3, TASK-5.4, TASK-5.5]
    max_parallel: 2
    blocked_by: [TASK-3.1]
    future: true
    notes: "Groundwork only - implementation deferred until web editing feature prioritized"

tasks:
  TASK-1.1:
    id: TASK-1.1
    title: "Add metadata fields to CollectionArtifact model"
    description: "Extend skillmeat/cache/models.py CollectionArtifact model with description, author, license, tags_json, version, source, origin, origin_source, resolved_sha, resolved_version, synced_at fields"
    phase: 1
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "30-40 min"
    dependencies: []
    files:
      - skillmeat/cache/models.py
    notes: "Use SQLAlchemy Column types: String, Text, DateTime; tags_json stores JSON array string"

  TASK-1.2:
    id: TASK-1.2
    title: "Create Alembic migration for CollectionArtifact cache fields"
    description: "Generate and verify migration to add new cache columns to collection_artifacts table without breaking existing data"
    phase: 1
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "20-30 min"
    dependencies: [TASK-1.1]
    files:
      - skillmeat/cache/migrations/versions/
    notes: "Use nullable=True for all new columns initially; test upgrade/downgrade"

  TASK-1.3:
    id: TASK-1.3
    title: "Create populate_collection_artifact_metadata() function"
    description: "Implement populate_collection_artifact_metadata(session, artifact_mgr, collection_mgr) in skillmeat/api/routers/user_collections.py that reads file-based artifacts and upserts CollectionArtifact cache records"
    phase: 1
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "45-60 min"
    dependencies: [TASK-1.1]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/core/artifact.py
    notes: "Extract metadata from ArtifactMetadata; store tags_json; set synced_at=now()"

  TASK-1.4:
    id: TASK-1.4
    title: "Integrate with migrate_artifacts_to_default_collection()"
    description: "Modify migrate_artifacts_to_default_collection() to call populate_collection_artifact_metadata() after creating CollectionArtifact associations"
    phase: 1
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "15-20 min"
    dependencies: [TASK-1.3]
    files:
      - skillmeat/api/routers/user_collections.py
    notes: "Call populate_collection_artifact_metadata() at end of migration function; ensure transactional consistency"

  TASK-1.5:
    id: TASK-1.5
    title: "Add startup sync logging"
    description: "Log startup CollectionArtifact cache population: count of artifacts synced, fields populated, any errors encountered"
    phase: 1
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "10-15 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/server.py
      - skillmeat/api/routers/user_collections.py
    notes: "Use structured logging; log before and after populate_collection_artifact_metadata() call"

  TASK-2.1:
    id: TASK-2.1
    title: "Create DB cache refresh endpoint (scoped)"
    description: "Implement POST /api/v1/user-collections/{collection_id}/refresh-cache to fetch file-based metadata and update CollectionArtifact cache rows for a DB collection"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "40-50 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/api/schemas/user_collections.py
    notes: "Keep separate from /{collection_id}/refresh (file-based) to avoid collisions"

  TASK-2.2:
    id: TASK-2.2
    title: "Create batch refresh endpoint (all collections)"
    description: "Implement POST /api/v1/user-collections/refresh-cache to refresh CollectionArtifact cache across all DB collections"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "50-60 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/api/schemas/user_collections.py
    notes: "Return {collections_refreshed, artifacts_refreshed, skipped, errors}"

  TASK-2.3:
    id: TASK-2.3
    title: "Add endpoint parameters validation"
    description: "Validate request parameters: collection_id ownership and request payload; enforce rate limiting for refresh-cache operations"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-30 min"
    dependencies: [TASK-2.1, TASK-2.2]
    files:
      - skillmeat/api/schemas/user_collections.py
      - skillmeat/api/middleware/rate_limit.py
    notes: "Use Pydantic validators; ensure DB collection exists before refresh"

  TASK-2.4:
    id: TASK-2.4
    title: "Add error handling and logging"
    description: "Implement comprehensive error handling for refresh-cache endpoints: malformed metadata, missing fields, collection not found"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "30-40 min"
    dependencies: [TASK-2.1, TASK-2.2]
    files:
      - skillmeat/api/routers/user_collections.py
      - skillmeat/api/schemas/user_collections.py
    notes: "Log all errors with context; return detailed error messages in 400/500 responses; track error metrics"

  TASK-2.5:
    id: TASK-2.5
    title: "Add unit tests for endpoints"
    description: "Test refresh-cache endpoints: successful refresh, missing collections, partial failures, batch operations"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "45-60 min"
    dependencies: [TASK-2.1, TASK-2.2, TASK-2.4]
    files:
      - skillmeat/api/tests/test_user_collections.py
    notes: "Mock ArtifactManager; verify CollectionArtifact cache fields updated"

  TASK-2.6:
    id: TASK-2.6
    title: "Hook deploy endpoint to refresh cache"
    description: "After artifacts.py deploy_artifact() completes file operation, trigger cache refresh for deployed artifact"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "30 min"
    dependencies: [TASK-2.1]
    files:
      - skillmeat/api/routers/artifacts.py
      - skillmeat/api/services/artifact_cache_service.py
    notes: "Deploy via web auto-refreshes DB cache; no manual refresh needed; graceful failure handling"

  TASK-2.7:
    id: TASK-2.7
    title: "Hook sync endpoint to refresh cache"
    description: "After artifacts.py sync_artifact() completes file operation, trigger cache refresh for synced artifact"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "30 min"
    dependencies: [TASK-2.1]
    files:
      - skillmeat/api/routers/artifacts.py
      - skillmeat/api/services/artifact_cache_service.py
    notes: "Sync via web auto-refreshes DB cache; version changes reflected immediately; graceful failure handling"

  TASK-2.8:
    id: TASK-2.8
    title: "Hook create/update/delete endpoints"
    description: "After create/update/delete operations, refresh or invalidate cache for affected artifacts"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "25-35 min"
    dependencies: [TASK-2.1]
    files:
      - skillmeat/api/routers/artifacts.py
      - skillmeat/api/services/artifact_cache_service.py
    notes: "Ensure cache stays fresh after file mutations; handle errors gracefully"

  TASK-2.9:
    id: TASK-2.9
    title: "Make /user-collections read path DB-first"
    description: "Use CollectionArtifact cache as primary source; fallback to filesystem only on cache miss"
    phase: 2
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "45-60 min"
    dependencies: [TASK-1.4]
    files:
      - skillmeat/api/routers/user_collections.py
    notes: "Build ArtifactSummary from cached fields; keep marketplace fallback last"

  TASK-3.1:
    id: TASK-3.1
    title: "Create staleness detection service"
    description: "Implement ArtifactCacheService.find_stale_artifacts() for CollectionArtifact cache rows based on synced_at and TTL"
    phase: 3
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "25-35 min"
    dependencies: [TASK-2.2]
    files:
      - skillmeat/api/services/artifact_cache_service.py
    notes: "Compare CollectionArtifact.synced_at against current time; configurable TTL; return stale count for monitoring"

  TASK-3.2:
    id: TASK-3.2
    title: "Create cache invalidation hook"
    description: "Implement invalidation mechanism triggered by collection add/remove operations; mark affected cache rows stale"
    phase: 3
    status: completed
    assigned_to: python-backend-engineer
    priority: high
    effort: "35-45 min"
    dependencies: [TASK-3.1]
    files:
      - skillmeat/api/services/artifact_cache_service.py
      - skillmeat/api/routers/user_collections.py
    notes: "Invalidate by collection_id + artifact_id; refresh via refresh-cache endpoint when needed"

  TASK-3.3:
    id: TASK-3.3
    title: "Create background refresh task (optional)"
    description: "Implement optional background task to periodically refresh stale CollectionArtifact metadata without blocking API requests"
    phase: 3
    status: completed
    assigned_to: python-backend-engineer
    priority: low
    effort: "40-50 min"
    dependencies: [TASK-3.1, TASK-3.2]
    files:
      - skillmeat/api/services/background_tasks.py
      - skillmeat/api/server.py
    notes: "Optional: start with manual refresh via endpoint, add background task if performance metrics warrant"

  TASK-3.4:
    id: TASK-3.4
    title: "Add monitoring metrics"
    description: "Track cache hit rate, refresh latency, stale cache row count; emit to observability system for dashboard"
    phase: 3
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-30 min"
    dependencies: [TASK-3.1, TASK-3.2]
    files:
      - skillmeat/api/services/artifact_cache_service.py
      - skillmeat/observability/metrics.py
    notes: "Use Prometheus-style metrics; track: hits, misses, refresh_duration, stale_count"

  TASK-4.1:
    id: TASK-4.1
    title: "Add refresh-cache hook to CLI add command"
    description: "Integrate refresh-cache endpoint call into CLI add command; after artifact added to collection.toml, trigger API to populate cache"
    phase: 4
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-25 min"
    dependencies: [TASK-2.1]
    files:
      - skillmeat/cli.py
    notes: "Implemented _refresh_api_cache() function and integrated into _add_artifact_from_spec(); gracefully handles API unavailability"

  TASK-4.2:
    id: TASK-4.2
    title: "Add refresh-cache hook to CLI sync command"
    description: "Integrate refresh-cache endpoint call into CLI sync command; after collection.toml synced, trigger batch refresh"
    phase: 4
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "20-25 min"
    dependencies: [TASK-2.2]
    files:
      - skillmeat/cli.py
    notes: "Added _refresh_api_cache_batch() function and integrated into sync_pull_cmd; shows refresh stats on success"

  TASK-4.3:
    id: TASK-4.3
    title: "Test end-to-end CLI→API→DB flow"
    description: "E2E test: CLI add artifact → API syncs metadata → database updated → API query returns full data"
    phase: 4
    status: completed
    assigned_to: python-backend-engineer
    priority: medium
    effort: "25-30 min"
    dependencies: [TASK-4.1, TASK-4.2]
    files:
      - tests/test_cli_artifact_sync.py
    notes: "Created 31 unit tests for _refresh_api_cache() and _refresh_api_cache_batch() functions covering: success, errors, timeouts, connection failures, graceful degradation, endpoint formats, timeouts, and response handling"

  # Phase 5: Web-Based Artifact Editing Groundwork (FUTURE)
  # Groundwork only - implementation deferred until web editing feature prioritized

  TASK-5.1:
    id: TASK-5.1
    title: "Create artifact metadata write service"
    description: "Service that writes metadata changes to file system (collection.toml and artifact frontmatter). File system is source of truth."
    phase: 5
    status: future
    assigned_to: python-backend-engineer
    priority: low
    effort: "2h"
    dependencies: [TASK-3.1]
    files:
      - skillmeat/api/services/artifact_write_service.py
    notes: "FUTURE: Ensures correct data flow Web → File → DB. Writes to correct file locations; preserves existing data; handles TOML/YAML correctly"

  TASK-5.2:
    id: TASK-5.2
    title: "Create PUT /api/v1/artifacts/{id}/metadata endpoint"
    description: "API endpoint for updating artifact metadata via web. Writes to file system first, then refreshes cache."
    phase: 5
    status: future
    assigned_to: python-backend-engineer
    priority: low
    effort: "1.5h"
    dependencies: [TASK-5.1]
    files:
      - skillmeat/api/routers/artifacts.py
      - skillmeat/api/schemas/artifacts.py
    notes: "FUTURE: Validates input; calls write service; refreshes cache; returns updated artifact"

  TASK-5.3:
    id: TASK-5.3
    title: "Create POST /api/v1/artifacts endpoint (web add)"
    description: "API endpoint for adding new artifacts via web UI. Creates file-based artifact first, then syncs to cache."
    phase: 5
    status: future
    assigned_to: python-backend-engineer
    priority: low
    effort: "2h"
    dependencies: [TASK-5.1]
    files:
      - skillmeat/api/routers/artifacts.py
      - skillmeat/api/services/artifact_write_service.py
    notes: "FUTURE: Creates artifact in file system; adds to collection.toml; syncs to DB cache"

  TASK-5.4:
    id: TASK-5.4
    title: "Add optimistic locking"
    description: "Prevent concurrent edits from CLI and web causing conflicts. Version/hash check before write."
    phase: 5
    status: future
    assigned_to: python-backend-engineer
    priority: low
    effort: "1h"
    dependencies: [TASK-5.2]
    files:
      - skillmeat/api/services/artifact_write_service.py
      - skillmeat/api/routers/artifacts.py
    notes: "FUTURE: Returns 409 Conflict on version mismatch; prevents lost updates"

  TASK-5.5:
    id: TASK-5.5
    title: "Create web UI for metadata editing"
    description: "Frontend form for editing artifact description, tags, author, license. Follows Design Principles."
    phase: 5
    status: future
    assigned_to: ui-engineer-enhanced
    priority: low
    effort: "2h"
    dependencies: [TASK-5.2]
    files:
      - skillmeat/web/components/artifacts/metadata-edit-form.tsx
      - skillmeat/web/app/artifacts/[id]/edit/page.tsx
    notes: "FUTURE: Form validates input; shows loading state; handles errors; uses existing shadcn components"

completion_criteria:
  Phase 1: "CollectionArtifact cache fields added, migration applied, startup sync populates cache with 100% of artifacts"
  Phase 2: "Refresh-cache endpoints tested with 95%+ success rate; cache hooks auto-refresh on deploy/sync/create/delete; /user-collections read path DB-first"
  Phase 3: "Staleness detection working, invalidation triggers on collection changes, metrics emitted"
  Phase 4: "CLI commands integrated and E2E tested (optional); all refresh-cache mechanisms coordinated"
  Phase 5: "FUTURE: Write service writes to file system; PUT endpoint refreshes cache after file write; optimistic locking prevents conflicts"

success_metrics:
  - "CollectionArtifact cache contains metadata for 100% of file-based artifacts"
  - "/collection page response time <100ms (database-backed)"
  - "Cache invalidation automatic and reliable"
  - "Metadata staleness bounded by TTL (default 30 min)"
  - "Web deploy/sync operations auto-refresh cache (no manual refresh needed)"
  - "FUTURE: Web editing writes to file first, then refreshes cache (correct data flow)"
---

# Artifact Metadata Cache v1 Progress

**Plan Reference**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`

## Overview

This 5-phase implementation plan populates and maintains a complete artifact metadata cache in the database, enabling the `/collection` page to operate entirely from the database with sub-100ms response times. Follow-on enhancement to collection-data-consistency-v1.

- **Phases 1-4**: Core caching implementation (12-16 hours)
- **Phase 5**: Web-based editing groundwork (6-8 hours, FUTURE)

**Current Status**: Pending (not started)
**Total Effort**: 12-16 hours (Phases 1-4) + 6-8 hours (Phase 5 future)
**Team**: python-backend-engineer (Phases 1-4), ui-engineer-enhanced (Phase 5)

---

## Phase 1: Enhanced Sync Function & Schema (3-4 hours)

**Objective**: Establish database schema and populate metadata cache at startup

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-1.1: Add metadata fields to CollectionArtifact model | pending | 30-40 min | python-backend-engineer |
| TASK-1.2: Create Alembic migration | pending | 20-30 min | python-backend-engineer |
| TASK-1.3: Create populate_collection_artifact_metadata() function | pending | 45-60 min | python-backend-engineer |
| TASK-1.4: Integrate with migrate_artifacts_to_default_collection() | pending | 15-20 min | python-backend-engineer |
| TASK-1.5: Add startup sync logging | pending | 10-15 min | python-backend-engineer |

**Completion Criteria**: CollectionArtifact cache fields added, migration applied, startup sync populates 100% of artifacts

---

## Phase 2: Incremental Sync & API Endpoints (3-4 hours)

**Objective**: Enable refresh-cache endpoints and hooks to keep cache updated after file-based changes

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-2.1: Create DB cache refresh endpoint (scoped) | pending | 40-50 min | python-backend-engineer |
| TASK-2.2: Create batch refresh endpoint (all collections) | pending | 50-60 min | python-backend-engineer |
| TASK-2.3: Add endpoint parameters validation | pending | 20-30 min | python-backend-engineer |
| TASK-2.4: Add error handling and logging | pending | 30-40 min | python-backend-engineer |
| TASK-2.5: Add unit tests for endpoints | pending | 45-60 min | python-backend-engineer |
| TASK-2.6: Hook deploy endpoint to refresh cache | pending | 30 min | python-backend-engineer |
| TASK-2.7: Hook sync endpoint to refresh cache | pending | 30 min | python-backend-engineer |
| TASK-2.8: Hook create/update/delete endpoints | pending | 25-35 min | python-backend-engineer |
| TASK-2.9: Make /user-collections read path DB-first | pending | 45-60 min | python-backend-engineer |

**Completion Criteria**: Refresh-cache endpoints tested with 95%+ success rate; DB-first read path avoids filesystem on cache hits

**Dependencies**: Phase 1 complete (TASK-1.4)

---

## Phase 3: Cache Invalidation & TTL-Based Refresh (2-3 hours)

**Objective**: Automatic staleness detection and cache invalidation

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-3.1: Create staleness detection service | completed | 25-35 min | python-backend-engineer |
| TASK-3.2: Create cache invalidation hook | completed | 35-45 min | python-backend-engineer |
| TASK-3.3: Create background refresh task (optional) | completed | 40-50 min | python-backend-engineer |
| TASK-3.4: Add monitoring metrics | completed | 20-30 min | python-backend-engineer |

**Completion Criteria**: Staleness detection working, invalidation triggers on collection changes, metrics emitted

**Dependencies**: Phase 2 complete (TASK-2.2)

---

## Phase 4: CLI Integration Hooks (1-2 hours, OPTIONAL)

**Objective**: Coordinate CLI commands with API cache operations

| Task | Status | Effort | Assigned To |
|------|--------|--------|-------------|
| TASK-4.1: Add refresh-cache hook to CLI add command | completed | 20-25 min | python-backend-engineer |
| TASK-4.2: Add refresh-cache hook to CLI sync command | completed | 20-25 min | python-backend-engineer |
| TASK-4.3: Test end-to-end CLI→API→DB flow | completed | 25-30 min | python-backend-engineer |

**Completion Criteria**: CLI commands integrated and E2E tested; refresh-cache mechanisms coordinated

**Dependencies**: Phase 2 complete (TASK-2.1, TASK-2.2)

**Note**: This phase is optional; prioritize phases 1-3 for immediate performance gain.

---

## Quick Reference: Task Delegation Commands

### Phase 1: Startup Sync & Schema

```bash
# Execute Phase 1 batch (tasks can run in parallel)
Task("python-backend-engineer", "Implement TASK-1.1, TASK-1.2, TASK-1.3 in parallel:\n\nTASK-1.1: Add metadata fields (description, author, license, tags_json, version, source, origin, origin_source, resolved_sha, resolved_version, synced_at) to CollectionArtifact model in skillmeat/cache/models.py\n\nTASK-1.2: Create Alembic migration to add new columns to collection_artifacts table\n\nTASK-1.3: Implement populate_collection_artifact_metadata(session, artifact_mgr, collection_mgr) in skillmeat/api/routers/user_collections.py\n\nReference: /docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md", model="opus")

Task("python-backend-engineer", "Implement TASK-1.4 and TASK-1.5 after Phase 1.1-1.3 complete:\n\nTASK-1.4: Integrate populate_collection_artifact_metadata() call into migrate_artifacts_to_default_collection()\n\nTASK-1.5: Add structured logging for CollectionArtifact cache population at startup\n\nFile: skillmeat/api/routers/user_collections.py", model="opus")
```

### Phase 2: Incremental Sync Endpoints

```bash
# Execute Phase 2 batch (block on Phase 1, tasks can run in parallel)
Task("python-backend-engineer", "Implement TASK-2.1 and TASK-2.2 in parallel:\n\nTASK-2.1: Create POST /api/v1/user-collections/{collection_id}/refresh-cache endpoint\n\nTASK-2.2: Create POST /api/v1/user-collections/refresh-cache endpoint for batch refresh\n\nFiles: skillmeat/api/routers/user_collections.py, skillmeat/api/schemas/user_collections.py", model="opus")

Task("python-backend-engineer", "Implement TASK-2.3, TASK-2.4, TASK-2.5:\n\nTASK-2.3: Validate endpoint parameters and enforce rate limiting\n\nTASK-2.4: Comprehensive error handling for refresh-cache endpoints\n\nTASK-2.5: Unit tests for endpoints covering happy path and error cases\n\nFiles: skillmeat/api/routers/user_collections.py, skillmeat/api/schemas/user_collections.py, tests/", model="opus")

Task("python-backend-engineer", "Implement TASK-2.6, TASK-2.7, TASK-2.8, TASK-2.9:\n\nTASK-2.6: Hook deploy endpoint to refresh cache\n\nTASK-2.7: Hook sync endpoint to refresh cache\n\nTASK-2.8: Hook create/update/delete endpoints for cache refresh/invalidation\n\nTASK-2.9: Make /user-collections read path DB-first (filesystem only on cache miss)\n\nFiles: skillmeat/api/routers/artifacts.py, skillmeat/api/routers/user_collections.py, skillmeat/api/services/artifact_cache_service.py", model="opus")
```

### Phase 3: Cache Invalidation

```bash
# Execute Phase 3 batch (block on Phase 2 complete)
Task("python-backend-engineer", "Implement TASK-3.1, TASK-3.2, TASK-3.3, TASK-3.4:\n\nTASK-3.1: Create ArtifactCacheService.find_stale_artifacts() for CollectionArtifact staleness detection\n\nTASK-3.2: Implement cache invalidation hook triggered by collection changes\n\nTASK-3.3: Create optional background refresh task (APScheduler)\n\nTASK-3.4: Add observability metrics (cache hit rate, refresh latency, stale count)\n\nFiles: skillmeat/api/services/artifact_cache_service.py, skillmeat/api/services/background_tasks.py, skillmeat/observability/metrics.py", model="opus")
```

### Phase 4: CLI Integration (Optional)

```bash
# Execute Phase 4 batch (optional, block on Phase 2 complete)
Task("python-backend-engineer", "Implement TASK-4.1, TASK-4.2, TASK-4.3:\n\nTASK-4.1: Add refresh-cache endpoint hook to CLI add command\n\nTASK-4.2: Add refresh-cache endpoint hook to CLI sync command\n\nTASK-4.3: E2E test CLI→API→DB flow\n\nFiles: skillmeat/cli.py, skillmeat/core/collection_manager.py, tests/", model="opus")
```

---

## Key Files to Modify

| File | Purpose | Phase |
|------|---------|-------|
| `skillmeat/cache/models.py` | Add metadata fields to CollectionArtifact model | 1 |
| `skillmeat/cache/migrations/versions/` | Migration scripts | 1 |
| `skillmeat/api/routers/user_collections.py` | Cache population and refresh-cache endpoints | 1-2 |
| `skillmeat/api/schemas/user_collections.py` | Request/response schemas | 2 |
| `skillmeat/api/services/artifact_cache_service.py` | NEW: Cache service logic | 3 |
| `skillmeat/api/services/background_tasks.py` | Optional background refresh | 3 |
| `skillmeat/api/middleware/rate_limit.py` | Rate limiting for refresh-cache ops | 2 |
| `skillmeat/observability/metrics.py` | Metrics emission | 3 |
| `skillmeat/cli.py` | CLI command hooks | 4 |
| `skillmeat/core/collection_manager.py` | Collection event hooks | 4 |

---

## Related Documentation

- **Plan Reference**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`
- **Predecessor**: `/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md`
- **Architecture**: `/docs/project_plans/reports/dual-collection-system-architecture-analysis.md`
- **Design**: `/docs/project_plans/reports/manage-collection-page-architecture-analysis.md`
