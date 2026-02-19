---
type: context
prd: persistent-project-cache
title: Persistent Project Cache - Development Context
status: active
created: '2025-11-30'
updated: '2025-11-30'
critical_notes_count: 0
implementation_decisions_count: 5
active_gotchas_count: 0
agent_contributors: []
agents: []
phase_status: []
blockers: []
decisions: []
integrations: []
gotchas: []
modified_files: []
schema_version: 2
doc_type: context
feature_slug: persistent-project-cache
---

# Persistent Project Cache - Implementation Context

## Feature Overview

**Problem**: Web app currently takes 60-90 seconds to load projects from scratch, wiping cache on every reload. Users experience slow startup times and must wait for full API fetch every session.

**Solution**: Implement a lightweight SQLite-backed cache that persists project metadata across sessions, with intelligent background refresh and file system watching.

**Key Outcomes**:
- Web app loads cached data in <100ms (vs 60-90s fresh)
- Background refresh keeps data fresh without blocking UI
- CLI and web app share single cache source of truth
- Cross-platform file watching triggers cache invalidation

---

## Architecture & Technical Decisions

### Why SQLite?

**Decision**: Use SQLite for persistent cache instead of PostgreSQL, Redis, or in-memory solutions.

**Rationale**:
- **No external dependencies**: SQLite included in Python stdlib
- **Single-file database**: Portable, easy to backup (~/.skillmeat/cache.db)
- **Sufficient for single-user**: Perfect for SkillMeat (per-user caches)
- **Transactional support**: ACID guarantees prevent corruption
- **Built-in concurrency**: WAL mode supports read/write simultaneously
- **Indexing**: Query performance sufficient for <100 projects
- **Future-proof**: Can migrate to PostgreSQL later if needed

**Trade-offs Accepted**:
- Not suitable for multi-user access (not a requirement)
- No distributed caching across devices (future enhancement)
- Some query performance limitations (index carefully)

### Cache Data Model

**Tables**:
1. **projects**: Project metadata (id, name, path, created_at, updated_at, last_fetched, status)
2. **artifacts**: Artifact data (id, project_id, name, type, source, deployed_version, upstream_version, is_outdated)
3. **artifact_metadata**: Full artifact details as JSON (description, tags, aliases)
4. **marketplace**: Optional marketplace entry cache (for future)
5. **cache_metadata**: TTL tracking and refresh status (key-value store)

**Key Indexes**:
- projects(updated_at) - for TTL-based refresh queries
- artifacts(project_id) - for artifact listing by project
- artifacts(type) - for type-based filtering
- artifacts(is_outdated) - for update detection
- Composite: (project_id, type) - for common queries

### Background Refresh Strategy

**Approach**: Time-based + event-based invalidation

**Time-Based (TTL)**:
- Default 6-hour TTL (configurable)
- Periodic job checks each project's last_fetched timestamp
- Queues stale projects for refresh
- Non-blocking background operation

**Event-Based (File Watching)**:
- Watchdog monitors ~/.skillmeat and ./.claude directories
- Detects manifest.toml changes (artifact add/remove)
- Detects deployment directory changes
- Debounced (100ms) to avoid cascading refreshes
- Triggers immediate cache invalidation + queue refresh

**Manual Refresh**:
- User-triggered via web UI "Refresh Projects" button
- CLI command: `skillmeat cache refresh`
- Immediate refresh, non-blocking with progress feedback

### Concurrency & Locking

**SQLite Concurrency Control**:
- Enable WAL mode (Write-Ahead Logging)
- Allows concurrent reads while writes serialize
- Read/write locks at CacheManager level
- Transaction isolation prevents partial updates
- Timeout handling for deadlock recovery

**CLI + Web Conflict Prevention**:
- CLI writes cause cache invalidation → background refresh
- Web reads use cache with API fallback
- No direct conflicts (reads cache, writes invalidate)
- File watcher detects CLI changes → web automatically updates

### Search Optimization

**Approach**: Direct SQLAlchemy queries against cache with proper indexing

**Query Patterns**:
- Search by name: Case-insensitive LIKE queries
- Filter by type: Direct equality (indexed)
- Filter by status: Indexed queries
- Full-text search: If needed, implement later

**Performance Target**: <100ms for typical searches (1000s of artifacts)

---

## Implementation Approach

### Layered Architecture (MeatyPrompts Pattern)

```
┌─────────────────────────────────────┐
│   CLI / Web UI Layer                │ Phase 4-5
├─────────────────────────────────────┤
│   API Router / Endpoints            │ Phase 2
├─────────────────────────────────────┤
│   Service Layer (CacheManager)      │ Phase 2
├─────────────────────────────────────┤
│   Repository Layer (CacheRepository)│ Phase 1
├─────────────────────────────────────┤
│   Database Layer (SQLAlchemy ORM)   │ Phase 1
├─────────────────────────────────────┤
│   SQLite Database (cache.db)        │ Phase 1
└─────────────────────────────────────┘
```

### File Structure

```
skillmeat/
├── cache/
│   ├── __init__.py
│   ├── manager.py              # CacheManager (service)
│   ├── repository.py           # CacheRepository (data access)
│   ├── models.py               # SQLAlchemy models
│   ├── schema.py               # Database schema definition
│   ├── refresh.py              # RefreshJob (background)
│   ├── watcher.py              # FileWatcher (change detection)
│   └── migrations/
│       └── versions/001_initial_schema.py
├── api/
│   └── routers/
│       ├── cache.py            # New cache endpoints
│       └── projects.py         # Modified for cache fallback
├── cli/
│   └── commands/
│       ├── cache.py            # New cache commands
│       └── list.py             # Enhanced for cache
└── tests/
    ├── test_cache_repository.py
    ├── test_cache_manager.py
    ├── test_refresh_job.py
    ├── test_file_watcher.py
    └── integration/test_cache_integration.py
```

---

## Phase Execution Strategy

### Phase 1: Foundation (Database Layer)
- **Critical Path**: Schema → Models → Repository
- **Duration**: 1 week
- **Key Blocker**: Schema design (CACHE-1.1) blocks all other work
- **Parallelization**: Migrations & Models can run in parallel after schema

### Phase 2: Service & Background (Business Logic)
- **Critical Path**: CacheManager → RefreshJob → API
- **Duration**: 1.5 weeks
- **Key Decision**: FileWatcher runs in parallel with CacheManager
- **Parallelization**: CacheManager & FileWatcher in parallel, then RefreshJob, then API, then tests

### Phase 3: Web UI (Frontend Integration)
- **Sequential**: Endpoint → Hooks → Component → Refresh button
- **Duration**: 1 week
- **Dependency**: Requires Phase 2 API endpoints
- **Design Pattern**: React Query for client-side caching

### Phase 4: CLI Integration (Command-Line Interface)
- **Sequential**: List command → Cache commands → Invalidation → Tests
- **Duration**: 1 week
- **Dependency**: Requires Phase 2 CacheManager
- **Goal**: CLI/web consistency and fast CLI operations

### Phase 5: Advanced Features (Enhancement)
- **Parallel**: Marketplace & Versions can run independently
- **Duration**: 1.5 weeks
- **Optional for MVP**: Could defer marketplace caching to Phase 2
- **Dependent**: UI indicators depend on version tracking

### Phase 6: Quality & Release (Testing & Documentation)
- **Parallel**: Performance, concurrent access, recovery testing in parallel
- **Duration**: 1 week
- **Critical**: Must pass all acceptance criteria before production
- **Documentation**: Configuration guide, API reference, troubleshooting

---

## Key Technical Decisions

### Decision 1: SQLite Schema Normalization

**Question**: Should we normalize tables or flatten artifacts into single table?

**Decision**: Normalize projects & artifacts, but flatten artifact_metadata as JSON.

**Rationale**:
- Normalized for queries (project_id foreign key)
- JSON metadata for flexibility (schema evolution without migrations)
- Balance between structure (queries) and flexibility (metadata)

### Decision 2: Background Job Scheduling

**Question**: Use APScheduler, FastAPI BackgroundTasks, or manual threading?

**Decision**: APScheduler with configurable interval.

**Rationale**:
- Production-grade job scheduling
- Configurable intervals (TTL-based)
- Graceful shutdown
- Resilient retry logic
- Can scale to multiple job types later

### Decision 3: File Watcher Implementation

**Question**: Use watchdog, Python pathlib, or manual polling?

**Decision**: Use watchdog library with debouncing.

**Rationale**:
- Cross-platform (Windows, Mac, Linux)
- Event-driven (not polling)
- Debouncing prevents cascading refreshes
- Well-maintained open-source library

### Decision 4: Cache Invalidation Strategy

**Question**: Full rebuild or incremental updates?

**Decision**: Incremental updates with full rebuild on corruption.

**Rationale**:
- Performance: Only update changed artifacts
- Efficiency: Compare timestamps before updating
- Reliability: Automatic full rebuild on corruption detection
- Recovery: Graceful fallback if incremental fails

### Decision 5: API Response Format

**Question**: Should we add cache metadata to existing /api/v1/projects response?

**Decision**: Include optional X-Cache-Hit header and last_fetched timestamp.

**Rationale**:
- Backward compatible (existing clients unaffected)
- Minimal changes to response schema
- Clients can detect cache hits for observability
- Can add freshness indicator in UI

---

## Dependencies & Prerequisites

### External Libraries (To Install)
- `watchdog>=3.0.0` - File system monitoring
- `apscheduler>=3.10.0` - Background job scheduling

### External Libraries (Already Available)
- `sqlalchemy>=2.0` - ORM
- `alembic>=1.13` - Database migrations
- `fastapi>=0.100` - API framework
- `react-query` - Client-side caching

### Internal Dependencies
- Existing Entity Lifecycle Management PRD (provides API endpoints)
- Existing CLI command structure
- Existing React component library (shadcn/ui, Radix UI)
- Existing test infrastructure (pytest, testing-library)

---

## Quality & Acceptance Criteria

### Functional Requirements
- [ ] SQLite cache database created and working
- [ ] Web app loads cached projects in <100ms
- [ ] Background refresh runs without blocking UI
- [ ] Manual refresh button works with progress feedback
- [ ] File watcher detects changes and invalidates cache
- [ ] CLI reads from cache with API fallback
- [ ] Cache recovers gracefully from corruption
- [ ] Marketplace metadata can be cached (Phase 5)

### Performance Targets
- Cache read latency: <10ms
- Cache write latency: <50ms
- Web app startup (warm cache): <500ms total
- Search query latency: <100ms
- Background refresh CPU: <5%
- Cache database size: <10MB for 100 projects

### Test Coverage
- >80% coverage for critical paths
- Unit tests for CacheManager, CacheRepository, RefreshJob, FileWatcher
- Integration tests for end-to-end workflows
- E2E tests for user workflows
- Concurrent access tests
- Recovery & error scenario tests

### Code Quality
- All tests passing
- Linting passes (black, flake8, mypy)
- Type hints throughout
- Comprehensive docstrings
- No regressions in existing functionality
- Security validation (no hardcoded secrets)

---

## Known Risks & Mitigations

### Risk 1: SQLite Concurrency Under Load
**Probability**: Medium | **Impact**: Medium

**Mitigation**:
- Enable WAL mode for concurrent reads
- Comprehensive locking tests in Phase 6
- Load testing with 100 projects/10k artifacts
- Timeout handling for deadlock recovery

### Risk 2: File Watcher Missing Rapid Changes
**Probability**: Low | **Impact**: Medium

**Mitigation**:
- Debounce events (100ms window)
- Periodic consistency checks
- Fallback to TTL refresh
- Clear logging of watcher events

### Risk 3: Cache Invalidation Edge Cases
**Probability**: Medium | **Impact**: Low

**Mitigation**:
- Thorough testing of all invalidation paths
- Clear logging for debugging
- Corruption detection + auto-rebuild
- Manual clear command as fallback

### Risk 4: Migration Issues on Existing Installs
**Probability**: Low | **Impact**: High

**Mitigation**:
- Comprehensive migration testing
- Rollback procedures documented
- Version control for migrations
- User communication about cache rebuild

### Risk 5: Performance Regression from Cache Queries
**Probability**: Low | **Impact**: Medium

**Mitigation**:
- Benchmark all queries before/after
- Profile database indexes
- Optimize hot paths
- Performance tests in Phase 6

### Risk 6: Marketplace Caching Staleness
**Probability**: Low | **Impact**: Medium

**Mitigation**:
- Appropriate TTL configuration
- Manual refresh option for users
- Clear freshness indicators
- Error handling for stale data

---

## Session Handoff Notes

### For Next Agent/Session

**Context**:
- All 25 tasks defined across 6 phases
- PRD and implementation plan complete and comprehensive
- Progress tracking setup with parallelization strategy
- Clear agent assignments for each task

**What's Ready**:
- Phase 1 can start immediately (no blockers)
- Architecture patterns established
- File structure defined
- Acceptance criteria documented

**What Needs Attention**:
- Install external dependencies (watchdog, APScheduler)
- Validate existing test infrastructure
- Review existing API endpoint patterns for cache integration
- Plan feature flag rollout

**Execution Strategy**:
1. Start with Phase 1 (CACHE-1.1) - schema design
2. Execute batches in parallel as defined
3. Update progress file after each task completion
4. Run validation checks between phases
5. Document architectural decisions via ADR

**Important Files**:
- Progress tracking: `.claude/progress/persistent-project-cache/phase-1-progress.md`
- Context notes: `.claude/worknotes/persistent-project-cache/context.md`
- PRD: `docs/project_plans/PRDs/enhancements/persistent-project-cache-v1.md`
- Implementation plan: `docs/project_plans/implementation_plans/enhancements/persistent-project-cache-v1.md`

---

## Quick Reference

### Phase Durations & Effort
- **Phase 1**: 1 week, 21 pts (schema, models, repository)
- **Phase 2**: 1.5 weeks, 28 pts (service, refresh, API)
- **Phase 3**: 1 week, 20 pts (web UI integration)
- **Phase 4**: 1 week, 16 pts (CLI integration)
- **Phase 5**: 1.5 weeks, 18 pts (advanced features)
- **Phase 6**: 1 week, 17 pts (testing, docs, polish)

### Critical Path
1. CACHE-1.1 (schema) → blocks all Phase 1
2. CACHE-1.4 (repository) → blocks Phase 2
3. CACHE-2.1 (CacheManager) → blocks Phase 2 API & Phase 3/4
4. CACHE-2.4 (API endpoints) → blocks Phase 3 web UI

### Success Metrics
- Web app loads in <100ms from cache
- Background refresh CPU <5%
- All tests passing with >80% coverage
- No regressions in existing functionality
- Concurrent CLI + web operations work without conflicts

---

*Context document for Persistent Project Cache feature implementation. Updated: 2025-11-30*
