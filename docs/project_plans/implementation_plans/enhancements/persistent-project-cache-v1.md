---
title: 'Implementation Plan: Persistent Project Cache'
description: Detailed task breakdown for implementing a persistent SQLite cache system
  for project metadata with background refresh and file watching
audience:
- ai-agents
- developers
tags:
- implementation-plan
- cache
- database
- background-jobs
- performance
- cli
- web-ui
created: 2025-11-30
updated: 2025-12-01
category: implementation
status: inferred_complete
prd_reference: /docs/project_plans/PRDs/enhancements/persistent-project-cache-v1.md
related:
- /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
- /docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md
schema_version: 2
doc_type: implementation_plan
feature_slug: persistent-project-cache
prd_ref: null
---
# Implementation Plan: Persistent Project Cache

**Feature Name:** Persistent Project Cache
**Complexity Level:** Large (L)
**Estimated Total Effort:** 88 Story Points
**Estimated Timeline:** 6 weeks (6 phases)
**Track:** Full Track (Architecture validation + Opus review)

---

## Executive Summary

This implementation plan breaks down the Persistent Project Cache feature into 6 sequential phases with 25 atomic tasks. The feature eliminates slow web app load times by maintaining a SQLite-backed cache of project metadata, updated intelligently through background jobs and file watching. Implementation follows the MeatyPrompts layered architecture: Database → Repository → Service → API → UI → Testing → Documentation → Deployment.

**Key Outcomes:**
- Web app loads cached data in <100ms (vs 60-90s fresh fetch)
- Background refresh keeps data fresh without UI blocking
- CLI and web app share single cache source of truth
- Cross-platform file watching triggers cache invalidation
- Complete test coverage with performance benchmarks

---

## Architecture Overview

### Layered Architecture (MeatyPrompts Pattern)

```
┌─────────────────────────────────────────┐
│         CLI / Web UI Layer              │ Phase 4-5
├─────────────────────────────────────────┤
│    API Router / HTTP Endpoints          │ Phase 2
├─────────────────────────────────────────┤
│  Service Layer (CacheManager, RefreshJob) │ Phase 1-2
├─────────────────────────────────────────┤
│ Repository Layer (CacheRepository)      │ Phase 1
├─────────────────────────────────────────┤
│    Database Layer (SQLAlchemy ORM)      │ Phase 1
├─────────────────────────────────────────┤
│   SQLite Database (cache.db)            │ Phase 1
└─────────────────────────────────────────┘
```

### File Structure

```
skillmeat/
├── cache/
│   ├── __init__.py
│   ├── manager.py              # CacheManager (service layer)
│   ├── repository.py           # CacheRepository (data access)
│   ├── models.py               # SQLAlchemy models
│   ├── schema.py               # Database schema definition
│   ├── refresh.py              # RefreshJob (background worker)
│   ├── watcher.py              # FileWatcher (change detection)
│   └── migrations/             # Alembic migrations
│       └── versions/
├── api/
│   └── routers/
│       ├── cache.py            # Cache endpoints (new)
│       └── projects.py         # Projects router (enhanced)
├── cli/
│   └── commands/
│       ├── cache.py            # Cache management commands (new)
│       └── list.py             # List command (enhanced)
└── tests/
    ├── test_cache_manager.py
    ├── test_cache_repository.py
    ├── test_refresh_job.py
    ├── test_file_watcher.py
    └── integration/
        └── test_cache_integration.py
```

---

## Detailed Task Breakdown

### Phase 1-2: Cache Infrastructure

**Duration:** 2.5 weeks | **Story Points:** 49 | **Assigned:** data-layer-expert, python-backend-engineer, backend-architect

**[Full Phase 1-2 Details](./persistent-project-cache-v1/phase-1-2-infrastructure.md)**

| Phase | Tasks | Focus |
|-------|-------|-------|
| 1 | CACHE-1.1 to CACHE-1.5 | Database schema, Alembic migrations, SQLAlchemy models, CacheRepository, Unit tests |
| 2 | CACHE-2.1 to CACHE-2.5 | CacheManager service, RefreshJob background worker, FileWatcher, API endpoints, Integration tests |

**Key Deliverables:**
- SQLite database with projects, artifacts, metadata tables
- Repository pattern data access layer
- Service layer with cache management, background refresh, file watching
- API endpoints for cache operations

---

### Phase 3-4: Integration Layers

**Duration:** 2 weeks | **Story Points:** 36 | **Assigned:** python-backend-engineer, ui-engineer-enhanced, frontend-developer

**[Full Phase 3-4 Details](./persistent-project-cache-v1/phase-3-4-integration.md)**

| Phase | Tasks | Focus |
|-------|-------|-------|
| 3 | CACHE-3.1 to CACHE-3.5 | Projects endpoint cache loading, React hooks, Projects page component, Refresh UI, Web tests |
| 4 | CACHE-4.1 to CACHE-4.4 | CLI list command enhancement, Cache management CLI commands, Write invalidation, CLI tests |

**Key Deliverables:**
- Web UI with cache-enabled project loading (<100ms)
- React hooks for cache status and refresh
- Cache freshness indicators and refresh buttons
- CLI cache commands (status, clear, refresh, config)

---

### Phase 5-6: Advanced Features & Polish

**Duration:** 2.5 weeks | **Story Points:** 35 | **Assigned:** python-backend-engineer, ui-engineer-enhanced, documentation-writer

**[Full Phase 5-6 Details](./persistent-project-cache-v1/phase-5-6-advanced-polish.md)**

| Phase | Tasks | Focus |
|-------|-------|-------|
| 5 | CACHE-5.1 to CACHE-5.4 | Marketplace caching, Upstream version tracking, Outdated artifact UI indicators, Search optimization |
| 6 | CACHE-6.1 to CACHE-6.6 | Performance benchmarks, Concurrent/load testing, Error recovery testing, Documentation, E2E tests, Release |

**Key Deliverables:**
- Marketplace metadata caching
- Update detection with "outdated" indicators in UI
- Optimized search queries (<100ms)
- Performance validated against targets
- Complete documentation suite
- Production-ready release

---

## Orchestration Quick Reference

See phase-specific files for detailed Task Delegation Commands.

**Phase Execution Order:**
1. **Phase 1-2** (Infrastructure): Start with CACHE-1.1, enables all subsequent work
2. **Phase 3-4** (Integration): Begin after CACHE-2.1 completes, Web and CLI in parallel
3. **Phase 5-6** (Advanced/Polish): Begin after core integration complete

---

## Task Summary Table

| Phase | Task ID | Task Title | Effort | Duration | Assigned To |
|-------|---------|-----------|--------|----------|------------|
| 1 | CACHE-1.1 | Design SQLite Schema | 5 pts | 2d | data-layer-expert |
| 1 | CACHE-1.2 | Create Alembic Migrations | 3 pts | 1d | python-backend-engineer |
| 1 | CACHE-1.3 | Implement SQLAlchemy Models | 5 pts | 2d | python-backend-engineer |
| 1 | CACHE-1.4 | Implement CacheRepository | 5 pts | 2d | python-backend-engineer |
| 1 | CACHE-1.5 | Unit Tests for DB Layer | 3 pts | 1.5d | python-backend-engineer |
| 2 | CACHE-2.1 | Implement CacheManager | 8 pts | 3d | python-backend-engineer |
| 2 | CACHE-2.2 | Implement RefreshJob | 8 pts | 3d | python-backend-engineer |
| 2 | CACHE-2.3 | Implement FileWatcher | 8 pts | 3d | python-backend-engineer |
| 2 | CACHE-2.4 | API Endpoints for Cache | 5 pts | 2d | python-backend-engineer |
| 2 | CACHE-2.5 | Integration Tests | 5 pts | 2d | python-backend-engineer |
| 3 | CACHE-3.1 | Modify Projects Endpoint | 3 pts | 1d | python-backend-engineer |
| 3 | CACHE-3.2 | React Hooks for Cache | 5 pts | 2d | frontend-developer |
| 3 | CACHE-3.3 | Projects Page Component | 5 pts | 2d | ui-engineer-enhanced |
| 3 | CACHE-3.4 | Refresh Button & Feedback | 3 pts | 1d | ui-engineer-enhanced |
| 3 | CACHE-3.5 | Web UI Component Tests | 4 pts | 1.5d | frontend-developer |
| 4 | CACHE-4.1 | Enhance CLI List Command | 3 pts | 1d | python-backend-engineer |
| 4 | CACHE-4.2 | Cache Management Commands | 5 pts | 2d | python-backend-engineer |
| 4 | CACHE-4.3 | CLI Write Invalidation | 3 pts | 1d | python-backend-engineer |
| 4 | CACHE-4.4 | CLI Tests & Documentation | 5 pts | 2d | python-backend-engineer |
| 5 | CACHE-5.1 | Marketplace Metadata Cache | 5 pts | 2d | python-backend-engineer |
| 5 | CACHE-5.2 | Track Upstream Versions | 5 pts | 2d | python-backend-engineer |
| 5 | CACHE-5.3 | Outdated Artifact Indicators | 5 pts | 2d | ui-engineer-enhanced |
| 5 | CACHE-5.4 | Optimize Search with Cache | 3 pts | 1d | python-backend-engineer |
| 6 | CACHE-6.1 | Performance Benchmarking | 5 pts | 2d | python-backend-engineer |
| 6 | CACHE-6.2 | Concurrent Access Testing | 4 pts | 1.5d | python-backend-engineer |
| 6 | CACHE-6.3 | Recovery & Error Testing | 3 pts | 1d | python-backend-engineer |
| 6 | CACHE-6.4 | Docs & Configuration | 3 pts | 1.5d | documentation-writer |
| 6 | CACHE-6.5 | E2E Integration Tests | 2 pts | 1d | python-backend-engineer |
| 6 | CACHE-6.6 | Final Review & Release | 2 pts | 1d | python-backend-engineer, backend-architect |

**Total: 88 Story Points, 6 Weeks**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| SQLite concurrency issues under load | Medium | Medium | Implement WAL mode, comprehensive locking tests, load testing |
| File watcher missing rapid changes | Low | Medium | Debounce events, periodic consistency checks, fallback TTL |
| Cache invalidation edge cases | Medium | Low | Thorough testing of all invalidation paths, clear logging |
| Migration issues on existing installations | Low | High | Comprehensive migration testing, rollback procedures, versioning |
| Performance regression from cache queries | Low | Medium | Benchmark all queries, profile indexes, optimize hot paths |
| Marketplace caching staleness | Low | Medium | Appropriate TTL, manual refresh option, clear freshness indicators |

---

## Dependencies & Prerequisites

**External Libraries (Already Available):**
- SQLAlchemy (ORM)
- FastAPI (API framework)
- React Query (client-side caching)
- watchdog (file system monitoring)

**To Install:**
- APScheduler (for background job scheduling)
- Alembic (for migrations, likely already available)

**Internal Dependencies:**
- Existing project API endpoints (Entity Lifecycle Management)
- Existing CLI command structure
- Existing React component library (shadcn/ui, Radix)

---

## Success Criteria

### Functional Completeness
- [ ] All 25 tasks completed and tested
- [ ] All acceptance criteria met
- [ ] PRD requirements fully implemented
- [ ] No critical regressions in existing functionality

### Quality Gates
- [ ] Test coverage >80% for critical paths
- [ ] All linting passes (black, flake8, mypy)
- [ ] Performance benchmarks met (load time, query speed, CPU)
- [ ] No security vulnerabilities (SCA passes)
- [ ] Concurrent access tested and verified

### User Experience
- [ ] Web app loads from cache in <100ms
- [ ] Background refresh non-blocking
- [ ] Clear UI indicators for cache status
- [ ] CLI commands intuitive and helpful
- [ ] Documentation complete and searchable

---

## Notes for Subagents

1. **Code Style**: Follow existing patterns in skillmeat codebase
2. **Error Handling**: All operations should fail gracefully with clear error messages
3. **Logging**: Use Python logging module, include context in all messages
4. **Type Safety**: Use type hints throughout (Python 3.9+ compatible)
5. **Testing**: Write tests alongside code, aim for >80% coverage
6. **Documentation**: Include docstrings, API docs, and user guides
7. **Performance**: Profile before optimizing, use pytest-benchmark for benchmarks
8. **Security**: Use parameterized queries, validate all inputs, no hardcoded secrets
9. **Backwards Compatibility**: Maintain API compatibility with existing clients
10. **Architecture**: Follow MeatyPrompts pattern strictly (DB → Repo → Service → API → UI)

---

## Additional Resources

- **Phase 1-2 Details**: [phase-1-2-infrastructure.md](./persistent-project-cache-v1/phase-1-2-infrastructure.md)
- **Phase 3-4 Details**: [phase-3-4-integration.md](./persistent-project-cache-v1/phase-3-4-integration.md)
- **Phase 5-6 Details**: [phase-5-6-advanced-polish.md](./persistent-project-cache-v1/phase-5-6-advanced-polish.md)

---

*Generated for AI agent execution. Implementation estimated at 88 story points over 6 weeks using Full Track (Opus architecture validation included). Phase-specific files contain detailed task breakdowns and delegation commands.*
