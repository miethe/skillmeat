---
title: "PRD: Persistent Project Cache"
description: "Maintain a stable, lightweight cache of project metadata for web app and CLI to eliminate slow reload times and enable efficient background updates"
audience: [ai-agents, developers]
tags: [prd, planning, enhancement, caching, performance, cli, web-ui]
created: 2025-11-30
updated: 2025-11-30
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
  - /docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md
---

# PRD: Persistent Project Cache

**Feature Name:** Persistent Project Cache

**Filepath Name:** `persistent-project-cache-v1`

**Date:** 2025-11-30

**Author:** Claude Code (AI Agent)

**Version:** 1.0

**Status:** Draft

**Related Documents:**
- Entity Lifecycle Management PRD
- Web UI Consolidation & Enhancements PRD

---

## 1. Executive Summary

The Persistent Project Cache feature eliminates slow reload times and improves responsiveness by maintaining a stable, locally-cached database of project metadata. Currently, the web app fetches project data on every reload, wiping the cache and causing 1+ minute load times for large projects. This feature introduces a lightweight SQLite-backed cache that persists across sessions, updates intelligently in the background based on triggers, and is shared between the web app and CLI.

**Priority:** HIGH

**Key Outcomes:**
- Web app loads cached project data in <100ms vs. 1+ minutes for fresh fetch
- Background cache updates keep data fresh without blocking UI
- CLI and web app share single cache source of truth
- Cache intelligently triggers refresh on time-basis, manual request, or change detection
- Lightweight implementation using SQLite with ~1-5MB footprint
- Cache can accelerate searches, update checks, and marketplace browsing

---

## 2. Context & Background

### Current State

**Performance Problem:**
- Web app fetches all project metadata on startup
- Fetching large projects (many artifacts) takes 1+ minute
- Cache is wiped on reload, requiring full re-fetch
- No background update mechanism
- Users blocked by loading spinner during fetch

**Current Architecture:**
- Projects loaded via `/api/v1/projects` endpoint
- No caching layer between API and UI
- CLI reads directly from filesystem (manifest.toml, deployment files)
- Web app and CLI have no shared cache

**Existing Infrastructure:**
- SQLAlchemy ORM available in backend
- Fast API infrastructure for cache endpoints
- React Query for client-side caching (limited TTL)
- Alembic for database migrations

### Problem Space

**Pain Points:**

1. **Slow Web App Load Times**
   - 1+ minute wait on fresh browser load
   - Users abandon or switch to CLI
   - Large projects unusable from web

2. **No Background Updates**
   - Stale data until next reload
   - Cannot refresh while user works
   - No indication of data freshness

3. **Cache Fragmentation**
   - CLI reads from files, web reads from API
   - No single source of truth for project state
   - Sync inconsistencies between tools

4. **Poor Search/Discovery Performance**
   - Searching for artifacts requires loading all data
   - No indexed search across all projects
   - Marketplace browsing slow

5. **Missing Update Indicators**
   - No way to know if artifact versions are outdated
   - Must manually check for updates
   - No background update detection

### Current Alternatives

**CLI Usage:**
- Users switch to CLI for faster operations
- `skillmeat list` reads from filesystem (faster)
- But no visual feedback or web UI

**Manual Caching:**
- Users open UI, wait, don't close browser
- Session cache survives while tab open
- Fragile and dependent on browser behavior

**No Workaround Available:**
- Cannot do background updates
- Cannot detect stale data automatically
- Cannot share cache between CLI and web

---

## 3. Goals & Success Metrics

### Primary Goals

**Goal 1: Eliminate Reload Delays**
- Web app loads from cache in <100ms on subsequent opens
- First load can take longer while populating cache
- Measurable: Page load time benchmark tests

**Goal 2: Background Cache Refresh**
- Cache updates in background without blocking UI
- User continues working while cache refreshes
- Measurable: Cache refresh completes without showing progress spinner

**Goal 3: Share Cache Between CLI and Web**
- CLI reads/writes to same cache as web app
- Single source of truth for project state
- Measurable: Consistency test comparing CLI vs web outputs

**Goal 4: Intelligent Trigger System**
- Time-based refresh (configurable TTL, default 6 hours)
- Manual refresh triggered by user
- Change detection (file modification triggers refresh)
- Measurable: Triggers activate correctly in acceptance tests

**Goal 5: Lightweight & Portable Implementation**
- Cache database < 5MB for typical projects
- No external dependencies beyond SQLite (stdlib in Python)
- Portable across OS/platforms (Windows, Mac, Linux)
- Measurable: File size and performance benchmarks

### Success Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Web app initial load time | 60-90s | <100ms cached | Performance test |
| Background refresh overhead | N/A | <5% CPU during refresh | System monitoring |
| Cache hit rate on reload | 0% | >95% | Session tracking |
| Cache size for 10 projects | N/A | <1MB | Disk usage |
| Update detection latency | N/A | <1s after change | Integration test |
| Search operation time | 30-60s | <500ms | Benchmark test |
| Update check latency | N/A | <1s | Integration test |
| CLI/web data consistency | N/A | 100% | Consistency validation |

---

## 4. User Personas & Journeys

### Personas

**Developer Dan**
- Role: Full-stack developer managing 10+ projects
- Needs: Fast access to project data, background updates, search across projects
- Current pain: Waits 1+ min for web app to load each session

**Team Lead Terry**
- Role: Team managing shared artifact library
- Needs: Marketplace caching, update indicators, quick browsing
- Current pain: Cannot efficiently discover updates across many artifacts

**Solo Samantha**
- Role: Freelancer with 2-3 projects
- Needs: Simple, responsive interface
- Current pain: Initial load delays, no indication of data freshness

### High-level Flows

**Scenario A: First Load After Server Start**
```
1. User opens web app
2. UI checks for cached project data
3. Cache empty, fetch from API starts
4. Background job populates cache
5. UI displays data as it streams in (progressive)
6. After ~10s, basic project structure available
7. Complete fetch happens in background
```

**Scenario B: Reload Within 6 Hours**
```
1. User refreshes browser
2. Web app loads from cache
3. UI renders in <100ms
4. Background refresh checks if update needed
5. If data stale, refreshes silently
6. UI updates if changes detected
```

**Scenario C: Manual Refresh**
```
1. User clicks "Refresh Projects" button
2. Cache immediately marked for refresh
3. Background job starts fetch
4. Toast shows "Syncing..." with progress
5. Cache updated as data arrives
6. UI updates projects in real-time (SSE)
```

**Scenario D: CLI and Web Consistency**
```
1. User adds artifact via CLI: skillmeat add ...
2. CLI writes to manifest.toml
3. Watchdog detects file change
4. Cache invalidated and queued for refresh
5. Web app automatically refreshes project data
6. User sees changes without manual refresh
```

---

## 5. Requirements

### 5.1 Functional Requirements

| ID | Requirement | Priority | Category | Notes |
|:--:|-----------|:--------:|----------|-------|
| FR-1 | Create SQLite cache database with project/artifact tables | MUST | Cache Storage | Schema includes metadata, timestamps, status |
| FR-2 | Web app loads projects from cache on startup | MUST | Cache Retrieval | Fallback to API if cache empty |
| FR-3 | Cache automatically populated on first run or invalidation | MUST | Cache Population | Progressive loading of data |
| FR-4 | Background refresh job runs periodically based on TTL | MUST | Background Refresh | Default 6h, configurable in CLI |
| FR-5 | Manual refresh trigger available in web UI | MUST | Manual Refresh | "Sync Projects" or "Refresh" button |
| FR-6 | File system watcher detects manifest/deployment changes | MUST | Change Detection | Triggers cache invalidation |
| FR-7 | Cache tracks last modified timestamp for each artifact | MUST | Update Tracking | Enables stale data detection |
| FR-8 | Cache tracks upstream version info for update checks | SHOULD | Update Detection | Compare deployed vs latest versions |
| FR-9 | CLI reads from same cache as web app | MUST | CLI Integration | Unified data source |
| FR-10 | Cache invalidation endpoint in API | SHOULD | Cache Mgmt | Allows selective refresh |
| FR-11 | Cache size monitoring and cleanup of old entries | SHOULD | Maintenance | Remove outdated snapshots after 30 days |
| FR-12 | Marketplace metadata caching | SHOULD | Marketplace | Cache remote collections/artifacts |
| FR-13 | Cache query language for searches | SHOULD | Search | Enable fast searches across projects |
| FR-14 | Data freshness indicator in UI | SHOULD | UX | Show "Updated X minutes ago" |
| FR-15 | Progress indicator during cache refresh | SHOULD | UX | Toast or progress bar during fetch |
| FR-16 | API endpoint to get cache status | SHOULD | Observability | Returns cache age, size, hit rate |
| FR-17 | Configuration option for cache TTL | SHOULD | Configuration | Via CLI or config file |
| FR-18 | Graceful degradation if cache corrupted | MUST | Reliability | Fallback to API fetch, rebuild cache |

### 5.2 Non-Functional Requirements

**Performance:**
- Cache read latency: <10ms
- Cache write latency: <50ms
- Background refresh CPU: <5%
- Web app startup time with warm cache: <500ms
- Cache query execution: <100ms for typical filters

**Scalability:**
- Support up to 100 projects with 10k+ artifacts
- Cache database size: <10MB for 100 projects
- Concurrent read/write from CLI and web: supported
- Background refresh doesn't block user operations

**Reliability:**
- Automatic recovery from corrupted cache
- Locking mechanism for concurrent access
- Atomic writes to prevent partial updates
- Backup of cache before major updates

**Portability:**
- No external database required (SQLite only)
- Works on Windows, macOS, Linux
- No special permissions needed
- Cache location: `~/.skillmeat/cache.db`

**Observability:**
- Log all cache operations (debug level)
- Metrics for cache hit/miss rates
- Errors logged with context
- Slow query warnings

---

## 6. Scope

### In Scope

**Core Caching:**
- SQLite database schema for projects, artifacts, metadata
- Cache population from API on first run
- Cache retrieval and fallback logic
- Background refresh job with TTL management

**Update Triggers:**
- Time-based refresh (configurable TTL, default 6 hours)
- File system watcher for manifest/deployment changes
- Manual refresh button in web UI
- API endpoint for triggering refresh

**CLI Integration:**
- CLI reads from cache (with API fallback)
- CLI writes cause cache invalidation
- Cache database accessible from both tools
- Unified project list across CLI and web

**Web UI Integration:**
- Load projects from cache on startup
- Fallback to API if cache unavailable
- Manual refresh button with progress feedback
- Data freshness indicator ("Updated X min ago")
- Toast notifications during refresh

**Observability:**
- Cache status endpoint (age, size, hit rate)
- Debug logging for cache operations
- Configuration option for TTL
- Error recovery with automatic rebuild

### Out of Scope

**Not in MVP:**
- Real-time sync between CLI and web (file watcher is enough)
- Distributed caching (multi-device sync)
- Advanced cache invalidation strategies
- Cache compression or encryption
- Mobile app cache support
- Automatic cache cleanup (manual purge command only)

**Future Enhancements:**
- Per-project cache refresh (vs global)
- Selective artifact caching (vs all)
- Cache statistics dashboard
- Predictive prefetching
- Cache versioning/rollback

---

## 7. Technical Design

### Cache Database Schema

```sql
-- Projects table
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  last_fetched TIMESTAMP,
  status TEXT DEFAULT 'healthy',
  error_message TEXT
);

-- Artifacts table (flattened from deployments)
CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  name TEXT NOT NULL,
  type TEXT NOT NULL,  -- skill, agent, command, hook, mcp
  source TEXT,
  deployed_version TEXT,
  upstream_version TEXT,
  is_outdated BOOLEAN,
  local_modified BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Metadata table (full artifact details)
CREATE TABLE artifact_metadata (
  artifact_id TEXT PRIMARY KEY,
  metadata JSON,  -- Full artifact metadata as JSON
  description TEXT,
  tags TEXT,  -- Comma-separated
  aliases TEXT,  -- Comma-separated
  FOREIGN KEY (artifact_id) REFERENCES artifacts(id)
);

-- Marketplace cache (optional)
CREATE TABLE marketplace (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT,  -- collection, artifact_source
  url TEXT,
  description TEXT,
  cached_at TIMESTAMP,
  data JSON  -- Full marketplace metadata
);

-- Cache metadata
CREATE TABLE cache_metadata (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_projects_updated ON projects(updated_at);
CREATE INDEX idx_artifacts_project ON artifacts(project_id);
CREATE INDEX idx_artifacts_type ON artifacts(type);
CREATE INDEX idx_artifacts_outdated ON artifacts(is_outdated);
```

### Architecture

```
~/.skillmeat/
├── cache.db              # SQLite database (persistent)
├── collection/
│   └── manifest.toml
└── projects/
    └── [project]/
        └── manifest.toml

skillmeat/
├── cache/
│   ├── manager.py        # CacheManager - read/write operations
│   ├── refresh.py        # RefreshJob - background worker
│   ├── watcher.py        # FileWatcher - filesystem monitoring
│   └── schema.py         # Database schema and migrations
├── api/
│   ├── routers/
│   │   ├── cache.py      # New: cache endpoints
│   │   └── projects.py   # Enhanced: fallback to cache
│   └── dependencies.py   # Inject CacheManager
└── cli/
    ├── commands/
    │   ├── list.py       # Enhanced: use cache
    │   └── cache.py      # New: cache management commands
    └── ...
```

### Background Refresh Job

**Design Patterns:**
- Scheduled job (APScheduler or similar)
- Runs every 6 hours by default (configurable)
- Non-blocking, low CPU priority
- Graceful shutdown
- Automatic retry on failure

**Flow:**
```
1. Check TTL for each project
2. If expired, queue fetch
3. Fetch data from API (or files for local projects)
4. Compare with cached version
5. Update cache if changed
6. Emit event if changes detected
7. Update "last_fetched" timestamp
```

**Events/Notifications:**
- Cache refresh started
- Cache refresh completed
- Changes detected (for UI real-time update)
- Errors during refresh

### Concurrent Access

**Locking Strategy:**
- SQLite built-in locking (WAL mode)
- Read-write locks at CacheManager level
- CLI and web app can read simultaneously
- Writes serialized (one at a time)
- Timeout handling for deadlocks

### File System Watching

**Mechanism:**
- Watchdog library monitors manifest.toml files
- Detects changes to `.claude/` directories
- Queues cache refresh on detection
- Debounced (wait 100ms for multiple changes)

**Trigger Points:**
- Manifest changes (artifact add/remove)
- Deployment changes (artifact deployed/undeployed)
- Project settings changes

---

## 8. Dependencies & Assumptions

### External Dependencies

**Libraries (Backend):**
- `sqlalchemy`: ORM (already used)
- `watchdog`: File system monitoring
- `apscheduler`: Background job scheduling
- `pydantic`: Data validation

**Libraries (Frontend):**
- Existing React Query setup (leveraged for cache revalidation)
- Existing shadcn/ui components for UI

### Internal Dependencies

**Feature Dependencies:**
- Entity Lifecycle Management: Provides API endpoints for fetch
- Existing manifest/deployment infrastructure

### Assumptions

- Projects have stable paths that don't change frequently
- Network failures are transient and retry-able
- File system changes are observable on target OS (Windows, Mac, Linux)
- SQLite available (part of Python stdlib)
- Users have write access to `~/.skillmeat/` directory
- Cache size remains under 10MB for typical use

### Configuration

**CLI Configuration Options:**
```bash
skillmeat config set cache-ttl 360      # 6 hours (minutes)
skillmeat config set cache-enabled true
skillmeat config set cache-path ~/.skillmeat/cache.db
```

**Environment Variables:**
```bash
SKILLMEAT_CACHE_TTL=360
SKILLMEAT_CACHE_ENABLED=true
SKILLMEAT_CACHE_PATH=~/.skillmeat/cache.db
```

---

## 9. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Cache corruption on power loss | HIGH | LOW | SQLite WAL mode, atomic writes |
| Stale data visible in UI | MEDIUM | MEDIUM | Freshness indicator, background refresh |
| Cache locks blocking CLI/web | HIGH | MEDIUM | Timeout handling, queue-based writes |
| Rapid file changes overwhelm watcher | MEDIUM | LOW | Debounced events, batch updates |
| Cache size grows unbounded | MEDIUM | LOW | Periodic cleanup, configurable retention |
| API outage prevents initial cache | HIGH | LOW | Graceful offline mode, use stale data |
| Concurrent updates during refresh | MEDIUM | LOW | Transaction isolation, version checks |
| Performance regression from cache queries | MEDIUM | LOW | Index optimization, query profiling |

---

## 10. Success Criteria (Definition of Done)

### Functional Acceptance

- [ ] SQLite cache database created and populated on first run
- [ ] Web app loads projects from cache in <100ms on reload
- [ ] Background refresh job runs periodically without blocking UI
- [ ] Manual refresh button works and shows progress
- [ ] File system watcher detects changes and invalidates cache
- [ ] CLI reads from cache (with API fallback)
- [ ] Cache data matches source data (consistency validation)
- [ ] Marketplace metadata can be cached and retrieved
- [ ] Cache recovers gracefully from corruption

### Technical Acceptance

- [ ] SQLAlchemy models for all cache tables
- [ ] Alembic migrations for schema creation
- [ ] CacheManager class with CRUD operations
- [ ] RefreshJob class for background updates
- [ ] FileWatcher class for change detection
- [ ] Cache endpoints in API router
- [ ] CLI commands for cache management
- [ ] Proper error handling and logging
- [ ] Type annotations throughout

### Quality Acceptance

- [ ] Unit tests for CacheManager (>80% coverage)
- [ ] Integration tests for refresh job
- [ ] E2E tests for web app cache loading
- [ ] Performance benchmarks met (load time, query speed)
- [ ] Concurrent access tests (CLI + web simultaneously)
- [ ] File watcher trigger tests
- [ ] Cache recovery tests
- [ ] No regressions in existing functionality

### Documentation Acceptance

- [ ] CacheManager API documentation
- [ ] Configuration guide for TTL and paths
- [ ] CLI cache management commands documented
- [ ] Architecture decision record
- [ ] Troubleshooting guide

---

## 11. Phased Implementation

### Phase 1: Cache Infrastructure (Week 1)

**Database & ORM:**
- [ ] Design SQLite schema
- [ ] Create Alembic migration
- [ ] SQLAlchemy models for all tables
- [ ] Index creation for performance

**Backend Integration:**
- [ ] CacheManager class (read/write/delete)
- [ ] Fallback logic in projects router
- [ ] Error handling and recovery
- [ ] Basic observability/logging

**Testing:**
- [ ] Unit tests for CacheManager
- [ ] Database integration tests
- [ ] Schema validation tests

### Phase 2: Background Refresh (Week 2)

**Refresh Job:**
- [ ] RefreshJob class with scheduling
- [ ] TTL-based refresh logic
- [ ] Incremental update strategy
- [ ] Event emission for UI updates

**File System Watching:**
- [ ] FileWatcher class with debouncing
- [ ] Integration with project directories
- [ ] Cache invalidation on changes
- [ ] Cross-platform compatibility

**API Integration:**
- [ ] Cache refresh endpoint
- [ ] Cache status endpoint
- [ ] Progress tracking (optional SSE)

**Testing:**
- [ ] Background job execution tests
- [ ] File watcher trigger tests
- [ ] TTL validation tests
- [ ] Event emission tests

### Phase 3: Web UI Integration (Week 2)

**Load Optimization:**
- [ ] Web app loads from cache
- [ ] API fallback if cache empty
- [ ] Progressive rendering of data

**User Interactions:**
- [ ] Manual refresh button
- [ ] Freshness indicator (UI badge)
- [ ] Progress feedback during refresh
- [ ] Toast notifications

**Testing:**
- [ ] Web app startup time benchmarks
- [ ] Cache load integration tests
- [ ] UI component tests

### Phase 4: CLI Integration (Week 1)

**Cache Usage:**
- [ ] CLI reads from cache with API fallback
- [ ] Cache invalidation on write operations
- [ ] Integration with list/search commands

**Cache Management:**
- [ ] `skillmeat cache status` command
- [ ] `skillmeat cache clear` command
- [ ] `skillmeat cache refresh` command
- [ ] `skillmeat config set cache-ttl` command

**Testing:**
- [ ] CLI/web consistency tests
- [ ] Cache command functionality tests

### Phase 5: Advanced Features (Week 2)

**Marketplace Caching:**
- [ ] Marketplace schema and models
- [ ] Cache remote artifact collections
- [ ] Marketplace status endpoint

**Update Detection:**
- [ ] Upstream version tracking
- [ ] Version comparison logic
- [ ] UI indicators for outdated artifacts

**Search Optimization:**
- [ ] Query builder for common searches
- [ ] Full-text search (if needed)
- [ ] Performance benchmarking

**Testing:**
- [ ] Marketplace cache tests
- [ ] Version comparison tests
- [ ] Search performance tests

### Phase 6: Testing & Polish (Week 1)

**Quality Assurance:**
- [ ] Performance benchmarking
- [ ] Stress testing (many projects)
- [ ] Concurrent access testing
- [ ] Cache recovery testing

**Documentation:**
- [ ] Configuration guide
- [ ] Troubleshooting guide
- [ ] Architecture decision record
- [ ] API documentation

**Deployment:**
- [ ] Feature flag configuration
- [ ] Gradual rollout plan
- [ ] Monitoring setup

---

## 12. User Stories & Acceptance Criteria

### Epic: Cache Infrastructure

| Story ID | Title | AC | Estimate |
|----------|-------|---|----------|
| PPC-001 | Create SQLite cache database | Schema created, migrations working, tables queryable | 5 pts |
| PPC-002 | Implement CacheManager class | CRUD ops work, errors handled, logs present | 8 pts |
| PPC-003 | Add cache fallback to projects API | API returns cached data, falls back to fetch if empty | 5 pts |
| PPC-004 | Create Alembic migrations | Schema migrations apply/rollback cleanly | 3 pts |

### Epic: Background Refresh

| Story ID | Title | AC | Estimate |
|----------|-------|---|----------|
| PPC-005 | Implement RefreshJob class | Job runs on schedule, updates cache, handles failures | 8 pts |
| PPC-006 | Add TTL-based refresh logic | Stale entries identified, refresh queued correctly | 5 pts |
| PPC-007 | Implement FileWatcher for changes | Changes detected, cache invalidated, cross-platform | 8 pts |
| PPC-008 | Add cache refresh endpoint | POST endpoint works, accepts project IDs, returns status | 3 pts |

### Epic: Web UI

| Story ID | Title | AC | Estimate |
|----------|-------|---|----------|
| PPC-009 | Load projects from cache on startup | Web app renders from cache <100ms, API fallback works | 5 pts |
| PPC-010 | Add manual refresh button | Button visible, triggers refresh, shows progress | 5 pts |
| PPC-011 | Add freshness indicator | "Updated X min ago" badge visible, updates on refresh | 3 pts |
| PPC-012 | Add refresh progress feedback | Toast/spinner shows during background refresh | 3 pts |

### Epic: CLI Integration

| Story ID | Title | AC | Estimate |
|----------|-------|---|----------|
| PPC-013 | CLI reads from cache | `skillmeat list` uses cache, API fallback works | 5 pts |
| PPC-014 | Cache invalidation on CLI write | Adding artifact invalidates cache, triggers refresh | 5 pts |
| PPC-015 | Add cache status command | `skillmeat cache status` returns age, size, hit rate | 3 pts |
| PPC-016 | Add cache management commands | clear, refresh commands work, show feedback | 3 pts |

### Epic: Advanced Features

| Story ID | Title | AC | Estimate |
|----------|-------|---|----------|
| PPC-017 | Cache marketplace metadata | Marketplace data fetched, cached, retrieved | 5 pts |
| PPC-018 | Track upstream versions | Upstream version stored, comparison works | 5 pts |
| PPC-019 | Add update indicators in UI | Outdated badge shows, version comparison available | 5 pts |
| PPC-020 | Optimize search with cache | Search queries <100ms, filtering works | 5 pts |

### Epic: Quality & Testing

| Story ID | Title | AC | Estimate |
|----------|-------|---|----------|
| PPC-021 | Unit tests for CacheManager | >80% coverage, all ops tested, edge cases | 8 pts |
| PPC-022 | Integration tests for refresh | Background job, file watcher, event emission | 8 pts |
| PPC-023 | E2E tests for web UI cache | Load time benchmark, fallback, manual refresh | 5 pts |
| PPC-024 | Performance benchmarking | Load time <100ms, queries <50ms, all targets met | 5 pts |
| PPC-025 | Documentation & guides | Config, troubleshooting, API docs, ADR | 5 pts |

---

## 13. Configuration & Deployment

### Feature Flags

```python
FEATURE_CACHE_ENABLED = True          # Master switch
FEATURE_CACHE_BACKGROUND = True       # Background refresh job
FEATURE_CACHE_WATCHER = True          # File system watcher
FEATURE_CACHE_MARKETPLACE = False     # Marketplace caching (future)
```

### Configuration Schema

```toml
[tool.skillmeat]
cache_enabled = true
cache_ttl = 360                        # Minutes (6 hours)
cache_path = "~/.skillmeat/cache.db"
cache_max_size = 10485760             # 10 MB
cache_cleanup_days = 30               # Retention for old entries
```

### Deployment Checklist

- [ ] Database migrations applied
- [ ] Background job scheduler running
- [ ] File watcher enabled
- [ ] API endpoints tested
- [ ] CLI commands working
- [ ] Web app integration verified
- [ ] Monitoring/logging configured
- [ ] Performance benchmarks validated
- [ ] Documentation published
- [ ] Release notes prepared

---

## 14. Success Measurement

### Performance Metrics

**Web App Load Time:**
- Baseline: 60-90 seconds (fresh fetch)
- Target: <100ms (cached) + ~10s background refresh
- Measurement: Browser DevTools, performance tests

**Cache Query Performance:**
- Target: <10ms read latency, <50ms write latency
- Measurement: Database query profiling

**Background Refresh:**
- Target: <5% CPU usage during refresh
- Measurement: System monitoring tools

### Adoption Metrics

**Cache Hit Rate:**
- Target: >95% after first 24 hours
- Measurement: Cache manager instrumentation

**User Task Completion:**
- Target: 100% of web app startup from cache
- Measurement: Session tracking

**CLI/Web Consistency:**
- Target: 100% data consistency
- Measurement: Automated consistency validation

### Observability Metrics

**Cache Health:**
- Hit/miss rates
- Query execution times
- Error rates during refresh
- Database file size

---

## 15. Assumptions & Open Questions

### Assumptions

- SQLite is acceptable for single-user cache (not multi-user)
- File system watching available on all target platforms
- Network outages are transient and retryable
- Cache size remains under 10MB for typical use
- Users have write access to ~/.skillmeat/

### Open Questions

- [ ] **Q1: Cache Invalidation Strategy**
  - Full rebuild vs incremental updates?
  - **A:** Start with incremental (compare timestamps), full rebuild on corruption

- [ ] **Q2: Marketplace Caching Priority**
  - Include in MVP or defer to Phase 2?
  - **A:** Defer to Phase 2 (advanced features)

- [ ] **Q3: Distributed Cache**
  - Support multi-device sync in future?
  - **A:** Out of scope for v1, plan for future

- [ ] **Q4: Cache Encryption**
  - Encrypt sensitive data in cache?
  - **A:** Not required for MVP (paths, metadata only)

- [ ] **Q5: Database Selection**
  - SQLite vs PostgreSQL for future scalability?
  - **A:** SQLite sufficient, extensible if needed

---

## 16. Appendices

### Reference: Database Recovery Procedure

If cache becomes corrupted:

```bash
# Manual recovery (user action)
skillmeat cache clear
skillmeat cache refresh

# Automatic recovery (background job)
# On next startup, detects corruption and rebuilds
```

### Reference: TTL Configuration Examples

```bash
# 12-hour refresh (default for large projects)
skillmeat config set cache-ttl 720

# 1-hour refresh (for rapidly changing projects)
skillmeat config set cache-ttl 60

# Disable cache (always fetch fresh)
skillmeat config set cache-enabled false
```

### Reference: Monitoring Queries

```sql
-- Cache size
SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();

-- Most recent refresh
SELECT name, last_fetched FROM projects ORDER BY last_fetched DESC LIMIT 5;

-- Stale entries (>6 hours old)
SELECT name FROM projects
WHERE last_fetched < datetime('now', '-6 hours');

-- Entry count by type
SELECT type, COUNT(*) FROM artifacts GROUP BY type;
```

---

## 17. Sign-off

**PRD Status:** Draft

**Approval Required:**
- [ ] Product Owner
- [ ] Backend Lead
- [ ] Performance Lead

**Created:** 2025-11-30

**Last Updated:** 2025-11-30

---

*This PRD is designed for AI agent execution. It provides sufficient detail for parallel implementation across cache infrastructure, background jobs, and UI integration phases.*
