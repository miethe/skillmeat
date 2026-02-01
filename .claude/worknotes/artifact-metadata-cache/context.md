# Artifact Metadata Cache v1: Context & Architecture

**PRD**: artifact-metadata-cache-v1  
**Related Plan**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`  
**Status**: Pending (not started)  
**Date**: 2026-02-01

---

## Enhancement Goal

Populate and maintain a complete **artifact metadata cache in the database**, enabling the `/collection` page to operate entirely from the database with **sub-100ms response times**. 

This is a **follow-on enhancement to collection-data-consistency-v1 (Phase 5)**, NOT a replacement. It solves the critical gap where metadata is still read from the file system despite having a database-backed collection system.

### Current Problem

After Phase 5 (collection-data-consistency-v1), the database has:
- ✓ `CollectionArtifact` associations (which artifacts belong to which collections)
- ✗ **Empty `Artifact` cache table** (missing metadata)

**Result**: `/collection` page falls back to file-based `ArtifactManager` on every request:
- 800-1500ms response times (includes file I/O)
- No true database-backed system
- Misses benefits of collection architecture

### Solution Approach

**One-way sync from file → database**:
1. **Startup**: `migrate_artifacts_to_default_collection()` populates `Artifact` cache with metadata
2. **CLI add**: After artifact added to manifest, trigger API sync endpoint
3. **CLI sync**: After collection updated, trigger batch refresh endpoint
4. **Background**: TTL-based staleness detection and invalidation

**Key Design Decision**: Keep both systems synchronized—file-based system remains source of truth for CLI, database cache serves web interface.

---

## What Gets Cached

From `ArtifactManager.show()` and file-based `Artifact` class:

```python
# Identity & source
id: str                    # 'skill:my-skill'
name: str                  # Display name
type: str                  # 'skill', 'command', 'agent', 'mcp', 'hook'
source: str                # GitHub path
origin: str                # 'github', 'local', 'marketplace'
origin_source: str         # Full URI

# Versioning
version_spec: str          # Specifier from manifest
resolved_sha: str          # Pinned SHA from lock file
resolved_version: str      # Resolved tag

# Metadata (from YAML frontmatter in artifact files)
description: str           # Short description
author: str                # Author name
license: str               # License type
tags: List[str]            # Classification tags
tools: List[str]           # Claude tools used

# Timestamps
synced_at: datetime         # When cached from file
updated_at: datetime        # When metadata last changed
```

---

## Architecture Overview

### Current State (Post-Phase 5)

```
File System                         Database
─────────────────                  ────────────────────
~/.skillmeat/                      skillmeat/
├── collection.toml                ├── Collections
├── artifacts/                      ├── CollectionArtifact (associations)
│   ├── SKILL.md (frontmatter)      └── Artifact (EMPTY - needs to populate)
│   ├── ...
│   └── ...
```

### After Implementation

```
File System                         Database
─────────────────                  ────────────────────
~/.skillmeat/                      skillmeat/
├── collection.toml                ├── Collections
├── artifacts/ ──Sync──>          ├── CollectionArtifact
│   │                              └── Artifact (populated with metadata)
│   └── SKILL.md (source)           
```

### Sync Mechanisms

| Trigger | Mechanism | Endpoint | Scope |
|---------|-----------|----------|-------|
| Server startup | `populate_artifact_metadata()` | N/A (internal) | All artifacts |
| CLI: `skillmeat add` | POST sync-artifact | `/api/v1/user-collections/sync-artifact` | Single artifact |
| CLI: `skillmeat sync` | POST refresh-metadata | `/api/v1/user-collections/refresh-metadata` | Batch (filtered) |
| Web: Deploy artifact | Hook in `deploy_artifact()` | Internal (auto-refresh) | Single artifact |
| Web: Sync artifact | Hook in `sync_artifact()` | Internal (auto-refresh) | Single artifact |
| Background (optional) | APScheduler/Celery task | Internal | Stale artifacts (TTL-based) |

---

## Data Flow Architecture

### Architectural Principle

**File system is source of truth for artifact content and metadata.**

All metadata changes must flow through the file system first, then sync to database cache.

### Data Flow by Operation Type

| Operation | Flow | DB Cache Action |
|-----------|------|-----------------|
| Add artifact (CLI) | File → DB | Sync new artifact |
| Sync artifact (CLI/Web) | File → DB | Refresh after file op |
| Deploy artifact (Web) | File → DB | Refresh after deploy |
| Edit metadata (Web, FUTURE) | **Web → File → DB** | Write to file, then refresh |
| Collection membership (Web) | DB only | N/A (web-only feature) |

### Future: Web-Based Editing

When web editing is implemented, it MUST follow:
```
Web UI Edit → API → File System → DB Cache Refresh → Response
```

NEVER: Write to DB only (causes file/DB divergence with CLI)

---

## Phase Breakdown

### Phase 1: Startup Sync & Schema (3-4 hours)

**Goal**: Establish database schema and initial population

- **TASK-1.1**: Add 7 new metadata fields to `Artifact` model
- **TASK-1.2**: Create Alembic migration (handles existing data)
- **TASK-1.3**: Implement `populate_artifact_metadata()` function
- **TASK-1.4**: Integrate into `migrate_artifacts_to_default_collection()`
- **TASK-1.5**: Add structured startup logging

**Assigned to**: python-backend-engineer  
**Output**: Artifact cache populated at startup with 100% of artifacts

### Phase 2: Incremental Sync Endpoints (3-4 hours)

**Goal**: Enable CLI-triggered cache updates

- **TASK-2.1**: `POST /sync-artifact` endpoint (single artifact)
- **TASK-2.2**: `POST /refresh-metadata` endpoint (batch with filters)
- **TASK-2.3**: Request validation and rate limiting
- **TASK-2.4**: Comprehensive error handling
- **TASK-2.5**: Unit tests (happy path + error cases)

**Assigned to**: python-backend-engineer  
**Dependencies**: Phase 1 complete  
**Output**: Incremental sync endpoints with 95%+ reliability

### Phase 3: Cache Invalidation & TTL (2-3 hours)

**Goal**: Automatic staleness detection and refresh

- **TASK-3.1**: `ArtifactCacheService.is_stale()` for staleness detection
- **TASK-3.2**: Cache invalidation hooks (triggered by collection changes)
- **TASK-3.3**: Background refresh task (optional, APScheduler/Celery)
- **TASK-3.4**: Observability metrics (cache hits, refresh latency, stale count)

**Assigned to**: python-backend-engineer  
**Dependencies**: Phase 2 complete  
**Output**: Automatic staleness management with metrics

### Phase 4: CLI Integration (1-2 hours, OPTIONAL)

**Goal**: Coordinate CLI commands with cache operations

- **TASK-4.1**: Add sync hook to `skillmeat add` command
- **TASK-4.2**: Add refresh hook to `skillmeat sync` command
- **TASK-4.3**: E2E test CLI→API→DB flow

**Assigned to**: python-backend-engineer  
**Dependencies**: Phase 2 complete  
**Output**: Integrated CLI commands  
**Priority**: Optional; prioritize phases 1-3 for immediate performance gain

---

## Key Implementation Decisions

### 1. One-Way Sync: File → Database

**Decision**: File-based system remains source of truth; database is cache layer.

**Why**: Preserves CLI-first, offline-capable model while enabling web performance.

### 2. TTL-Based Invalidation (Default 30 minutes)

**Decision**: Cache entries marked stale after 30-minute TTL; refresh on-demand or background.

**Why**: Balances freshness with API call overhead. Configurable per deployment.

### 3. Startup Population (Not Lazy Loading)

**Decision**: `migrate_artifacts_to_default_collection()` populates all artifacts at startup.

**Why**: Ensures `/collection` page always has data. No cold-start latency.

### 4. Background Refresh (Phase 3.3 Optional)

**Decision**: Background task is optional; implement only if Phase 3 metrics warrant.

**Why**: Immediate priority is synchronous endpoints. Background task is optimization.

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|-----------|
| Database coverage | 100% of file artifacts cached | Query count: `SELECT COUNT(*) FROM artifact WHERE synced_at IS NOT NULL` |
| Response time | <100ms for `/collection` page | API benchmark: metadata-heavy queries (50+ artifacts) |
| Cache reliability | 95%+ sync success rate | Track via metrics: `sync_success_count / sync_total_count` |
| Staleness bound | ≤30 min (default TTL) | Max age of cached metadata vs file-based source |
| Zero fallback | 0 file-system reads for web UI | Remove file-based fallback from `/collection` page |

---

## Files to Modify (Summary)

| File | Phase | Changes |
|------|-------|---------|
| `skillmeat/cache/models.py` | 1 | Add 7 fields to Artifact model |
| `skillmeat/api/alembic/versions/` | 1 | Migration script |
| `skillmeat/api/routers/user_collections.py` | 1, 2 | Sync functions + endpoints |
| `skillmeat/api/schemas.py` | 2 | Request/response schemas |
| `skillmeat/api/services/artifact_cache.py` | 3 | NEW: Cache service |
| `skillmeat/api/middleware/rate_limit.py` | 2 | Batch operation rate limits |
| `skillmeat/observability/metrics.py` | 3 | Metrics emission |
| `skillmeat/cli.py` | 4 | CLI hooks |
| `skillmeat/core/collection_manager.py` | 4 | Event hooks |

---

## Related Documentation

**Implementation Plan**: `/docs/project_plans/implementation_plans/refactors/artifact-metadata-cache-v1.md`

**Predecessor** (Phase 5 completed):
- `/docs/project_plans/implementation_plans/refactors/collection-data-consistency-v1.md`

**Architecture & Design**:
- `/docs/project_plans/reports/dual-collection-system-architecture-analysis.md`
- `/docs/project_plans/reports/manage-collection-page-architecture-analysis.md`

---

## Agent Notes

**Model Preference**: Opus (complex reasoning required for schema design, error handling)

**Parallelization Strategy**:
- Phase 1: TASK-1.1, 1.2, 1.3 can run in parallel (then 1.4, 1.5 sequentially)
- Phase 2: TASK-2.1, 2.2 can run in parallel (then 2.3, 2.4, 2.5 sequentially)
- Phase 3: TASK-3.1, 3.2 sequential; 3.3, 3.4 can run in parallel
- Phase 4: Optional; TASK-4.1, 4.2 can run in parallel

**Complexity**: Medium (schema extension, sync logic, error handling)

**Token Efficiency**: Use symbol queries for API schema lookups; delegate implementation to python-backend-engineer with file paths.
