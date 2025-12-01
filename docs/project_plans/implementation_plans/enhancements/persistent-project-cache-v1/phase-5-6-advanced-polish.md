---
title: "Persistent Project Cache - Phases 5-6: Advanced Features & Polish"
description: "Advanced cache features and testing, documentation, release preparation"
audience: [ai-agents, developers]
tags: [implementation-plan, cache, marketplace, versioning, testing, documentation, performance]
created: 2025-11-30
updated: 2025-12-01
category: "implementation"
status: active
parent_plan: /docs/project_plans/implementation_plans/enhancements/persistent-project-cache-v1.md
prd_reference: /docs/project_plans/PRDs/enhancements/persistent-project-cache-v1.md
---

# Phases 5-6: Advanced Features & Polish

**Parent Plan:** [Persistent Project Cache Implementation Plan](../persistent-project-cache-v1.md)

---

## Phase 5: Advanced Features

**Duration:** 1.5 weeks | **Story Points:** 18 | **Assigned:** python-backend-engineer, ui-engineer-enhanced

### Task 5.1: Implement Marketplace Metadata Caching

**Task ID:** CACHE-5.1
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1
**Duration:** 2 days

**Description:**
Add caching for marketplace metadata (remote artifact collections, update sources). Allows browsing marketplace without network latency.

**Acceptance Criteria:**
- [ ] Marketplace entries cached in marketplace table
- [ ] TTL-based refresh for marketplace cache (configurable)
- [ ] CacheManager.get_marketplace_entries() method
- [ ] CacheManager.update_marketplace_cache() method
- [ ] API endpoint: GET /api/v1/cache/marketplace
- [ ] Fallback to network if cache stale
- [ ] Version comparison with upstream
- [ ] No breaking changes to marketplace browsing

**Implementation Notes:**
- Reuse existing marketplace data fetch logic
- Store raw JSON response for flexibility
- Implement marketplace refresh job alongside project refresh
- Support selective marketplace updates

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py` (add marketplace methods)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/refresh.py` (add marketplace refresh)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (add marketplace endpoint)

---

### Task 5.2: Track Upstream Versions for Update Detection

**Task ID:** CACHE-5.2
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** CACHE-2.1, CACHE-2.2
**Duration:** 2 days

**Description:**
Track upstream artifact versions during refresh and flag outdated artifacts. Enable update indicators in UI.

**Acceptance Criteria:**
- [ ] Upstream version fetched during refresh for each artifact
- [ ] Version comparison logic: deployed vs upstream
- [ ] is_outdated flag set correctly for each artifact
- [ ] CacheManager.get_outdated_artifacts() returns stale artifacts
- [ ] API endpoint: GET /api/v1/cache/stale-artifacts with sorting/filtering
- [ ] Version comparison handles pre-release versions
- [ ] Proper error handling for version fetch failures
- [ ] Performance benchmarked (no N+1 queries)

**Implementation Notes:**
- Reuse existing version comparison logic if available
- Handle cases where upstream version unavailable
- Log version mismatches for observability
- Cache version info along with metadata

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py` (add update detection)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/refresh.py` (fetch upstream versions)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (add stale-artifacts endpoint)

---

### Task 5.3: Add UI Indicators for Outdated Artifacts

**Task ID:** CACHE-5.3
**Assigned To:** ui-engineer-enhanced
**Story Points:** 5
**Dependencies:** CACHE-5.2
**Duration:** 2 days

**Description:**
Add visual indicators in web UI for outdated artifacts. Show version comparison and update suggestions.

**Acceptance Criteria:**
- [ ] Badge component shows "Update available" on artifact cards
- [ ] Badge clickable, shows version comparison modal
- [ ] Modal shows deployed vs upstream versions
- [ ] Modal suggests update action
- [ ] Outdated artifacts filterable in projects list
- [ ] Sorting by update status available
- [ ] Proper visual styling (warning colors)
- [ ] Accessible tooltips and aria labels
- [ ] Responsive design

**Implementation Notes:**
- Use shadcn/ui Badge with warning variant
- Create UpdateAvailableModal component
- Integrate with useProjectCache hook for data
- Show count of outdated artifacts in toolbar

**Files to Create/Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/OutdatedBadge.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/components/UpdateAvailableModal.tsx` (new)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/app/projects/page.tsx` (modify)

---

### Task 5.4: Optimize Search with Cache Queries

**Task ID:** CACHE-5.4
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Implement efficient search queries against cache. Add full-text search support if needed. Benchmark search performance.

**Acceptance Criteria:**
- [ ] CacheManager.search_artifacts(query, filters) method
- [ ] Search by name, type, tags, source
- [ ] Filtering by project, type, status
- [ ] Full-text search on metadata (if needed)
- [ ] Search latency <100ms for typical queries
- [ ] Pagination support (offset/limit)
- [ ] Sorted results (relevance, name, date)
- [ ] Performance benchmarked against old search

**Implementation Notes:**
- Use SQLAlchemy query builder for flexibility
- Add proper indexes for search performance
- Support fuzzy matching for forgiving search
- Cache common searches in memory

**Files to Modify:**
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/cache/manager.py` (add search methods)
- `/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/routers/cache.py` (add search endpoint)

---

## Phase 6: Testing, Documentation & Polish

**Duration:** 1 week | **Story Points:** 17 | **Assigned:** python-backend-engineer, documentation-writer

### Task 6.1: Performance Benchmarking & Optimization

**Task ID:** CACHE-6.1
**Assigned To:** python-backend-engineer
**Story Points:** 5
**Dependencies:** All phases
**Duration:** 2 days

**Description:**
Benchmark cache performance against success criteria. Optimize queries and indexes based on results.

**Acceptance Criteria:**
- [ ] Cache read latency: <10ms (measure with perf tests)
- [ ] Cache write latency: <50ms
- [ ] Web app startup with warm cache: <500ms total (including network)
- [ ] Search query latency: <100ms for typical queries
- [ ] Background refresh CPU: <5% (measure with system profiler)
- [ ] Cache database file: <10MB for 100 projects
- [ ] All benchmarks documented in report
- [ ] Optimization recommendations if targets not met

**Implementation Notes:**
- Create benchmark script that tests all operations
- Use Python timeit for micro-benchmarks
- Use pytest-benchmark for automated benchmarking
- Profile database queries with EXPLAIN
- Add query indexes if needed

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/benchmarks/test_cache_performance.py`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/performance_report.md` (generated)

---

### Task 6.2: Concurrent Access & Load Testing

**Task ID:** CACHE-6.2
**Assigned To:** python-backend-engineer
**Story Points:** 4
**Dependencies:** All phases
**Duration:** 1.5 days

**Description:**
Test concurrent access scenarios (CLI + web simultaneously). Verify no deadlocks or data corruption. Load test with many projects.

**Acceptance Criteria:**
- [ ] Concurrent read/write tests pass (no deadlocks)
- [ ] Load test with 100 projects, 10k artifacts
- [ ] Simultaneous CLI list + web refresh don't conflict
- [ ] Transaction isolation verified
- [ ] Database integrity maintained
- [ ] No data corruption under concurrent load
- [ ] Clear test report with recommendations
- [ ] All edge cases documented

**Implementation Notes:**
- Use pytest-xdist for parallel test execution
- Use threading for concurrent access simulation
- Use locust or similar for load testing
- Monitor database locks during tests

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_concurrent_access.py`
- `/Users/miethe/dev/homelab/development/skillmeat/tests/load/locustfile.py`

---

### Task 6.3: Cache Recovery & Error Scenarios

**Task ID:** CACHE-6.3
**Assigned To:** python-backend-engineer
**Story Points:** 3
**Dependencies:** CACHE-2.1
**Duration:** 1 day

**Description:**
Test cache corruption recovery, disk full scenarios, permission errors. Ensure graceful degradation.

**Acceptance Criteria:**
- [ ] Corrupted database detected and rebuilt on startup
- [ ] Permission errors handled gracefully (fallback to memory cache)
- [ ] Disk full handled gracefully (pause refresh, warn user)
- [ ] Stale data used if refresh fails (better than blank)
- [ ] Clear error messages for troubleshooting
- [ ] Recovery tested end-to-end
- [ ] All scenarios documented

**Implementation Notes:**
- Use temporary files to simulate corruption
- Mock file system errors
- Test fallback paths thoroughly
- Add recovery logging

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/test_cache_recovery.py`

---

### Task 6.4: Configuration Guide & API Documentation

**Task ID:** CACHE-6.4
**Assigned To:** documentation-writer
**Story Points:** 3
**Dependencies:** All phases
**Duration:** 1.5 days

**Description:**
Write comprehensive documentation for cache feature: configuration guide, API reference, troubleshooting, architecture decisions.

**Acceptance Criteria:**
- [ ] Configuration guide: TTL, cache path, cleanup retention
- [ ] CLI commands reference: cache status, refresh, clear, config
- [ ] API endpoints reference: all cache endpoints with examples
- [ ] Architecture Decision Record (ADR) explaining design choices
- [ ] Troubleshooting guide: common issues and solutions
- [ ] Examples: using cache from Python code, API calls
- [ ] Performance tuning guide
- [ ] All docs searchable and properly indexed

**Implementation Notes:**
- Use frontmatter for proper documentation
- Include code examples
- Include diagrams for architecture
- Link to related docs

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/configuration-guide.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/api-reference.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/troubleshooting-guide.md`
- `/Users/miethe/dev/homelab/development/skillmeat/docs/cache/architecture-decision-record.md`

---

### Task 6.5: End-to-End Integration Tests

**Task ID:** CACHE-6.5
**Assigned To:** python-backend-engineer
**Story Points:** 2
**Dependencies:** All phases
**Duration:** 1 day

**Description:**
Write E2E tests simulating real user workflows: app startup, manual refresh, CLI operations, file changes.

**Acceptance Criteria:**
- [ ] E2E test: fresh app startup → cache populated → fast reload
- [ ] E2E test: manual refresh → cache updated → UI refreshed
- [ ] E2E test: CLI add artifact → cache invalidated → web reflects change
- [ ] E2E test: file change → file watcher triggers → cache updated
- [ ] All tests pass consistently
- [ ] No flaky tests
- [ ] Clear test documentation

**Implementation Notes:**
- Use real FastAPI test client
- Use temp databases for isolation
- Simulate file system changes
- Mock external APIs appropriately

**Files to Create:**
- `/Users/miethe/dev/homelab/development/skillmeat/tests/e2e/test_cache_workflow.py`

---

### Task 6.6: Final Review & Release Preparation

**Task ID:** CACHE-6.6
**Assigned To:** python-backend-engineer, backend-architect
**Story Points:** 2
**Dependencies:** All tasks
**Duration:** 1 day

**Description:**
Final code review, quality checks, feature flag configuration, release notes preparation.

**Acceptance Criteria:**
- [ ] All tests passing (>95% overall coverage target)
- [ ] Code reviewed by 2+ engineers
- [ ] Linting passes (black, flake8, mypy)
- [ ] No critical security issues
- [ ] Feature flags configured correctly
- [ ] Release notes written
- [ ] Known limitations documented
- [ ] Ready for production deployment

**Implementation Notes:**
- Configure FEATURE_CACHE_ENABLED flag
- Set up monitoring/alerting for cache health
- Document rollback procedure
- Prepare migration guide if needed

**Files to Create/Modify:**
- Release notes (part of commit/tag)
- Feature flags configuration

---

## Phase 5-6 Orchestration Quick Reference

### Phase 5 Parallelization
- CACHE-5.1 (Marketplace) and CACHE-5.2 (Versions) in parallel
- CACHE-5.3 (UI) depends on CACHE-5.2
- CACHE-5.4 (Search) independent

### Phase 6 Sequential
- CACHE-6.1, CACHE-6.2, CACHE-6.3 in parallel
- CACHE-6.4 (Docs) independent
- CACHE-6.5 (E2E Tests) depends on all phases
- CACHE-6.6 (Review) depends on all tasks

### Task Delegation Commands

**Phase 5 Parallel:**

```
Task("python-backend-engineer", "CACHE-5.1: Implement marketplace metadata caching.
  Location: skillmeat/cache/manager.py (add methods), refresh.py (marketplace refresh)
  Endpoints: GET /api/v1/cache/marketplace
  Features: TTL-based refresh, version comparison, fallback to network
  Reason: Accelerate marketplace browsing without network latency")

Task("python-backend-engineer", "CACHE-5.2: Track upstream versions for update detection.
  Files: cache/manager.py, cache/refresh.py, api/routers/cache.py
  Features: Fetch upstream versions, compare deployed vs upstream, flag is_outdated
  Endpoint: GET /api/v1/cache/stale-artifacts
  Reason: Enable automated update detection and indicators")

Task("python-backend-engineer", "CACHE-5.4: Optimize search with cache queries.
  File: skillmeat/cache/manager.py (add search methods)
  Features: search_artifacts(query, filters), pagination, sorting, FTS
  Performance: Target <100ms for typical queries
  Reason: Accelerate artifact discovery")
```

**Phase 5 Sequential (after parallel):**

```
Task("ui-engineer-enhanced", "CACHE-5.3: Add UI indicators for outdated artifacts.
  New components: OutdatedBadge.tsx, UpdateAvailableModal.tsx
  Features: Badge on artifact cards, version comparison modal, sortable/filterable
  Design: Warning colors, accessible, responsive
  Reason: Notify users about available updates")
```

**Phase 6 Parallel:**

```
Task("python-backend-engineer", "CACHE-6.1: Performance benchmarking and optimization.
  Location: tests/benchmarks/test_cache_performance.py
  Targets: Read <10ms, write <50ms, startup <500ms, search <100ms, CPU <5%
  Tools: pytest-benchmark, timeit, EXPLAIN queries
  Reason: Validate performance targets met")

Task("python-backend-engineer", "CACHE-6.2: Concurrent access and load testing.
  Location: tests/test_concurrent_access.py, tests/load/locustfile.py
  Scenarios: CLI + web simultaneously, 100 projects/10k artifacts
  Verification: No deadlocks, data integrity, transaction isolation
  Reason: Ensure robustness under concurrent and heavy load")

Task("python-backend-engineer", "CACHE-6.3: Cache recovery and error scenario testing.
  Location: tests/test_cache_recovery.py
  Scenarios: Corruption, permission errors, disk full, stale data fallback
  Verification: Graceful degradation, clear error messages, recovery works
  Reason: Ensure production reliability")

Task("documentation-writer", "CACHE-6.4: Write configuration guide and API documentation.
  Location: docs/cache/*.md (configuration-guide, api-reference, troubleshooting, ADR)
  Content: CLI config, API endpoints, examples, architecture decisions, troubleshooting
  Reason: Enable users and developers to understand and use cache feature")
```

**Phase 6 Sequential (after parallel):**

```
Task("python-backend-engineer", "CACHE-6.5: Write E2E integration tests.
  Location: tests/e2e/test_cache_workflow.py
  Scenarios: Fresh startup, manual refresh, CLI operations, file changes
  Verification: All workflows work end-to-end consistently
  Reason: Validate complete user workflows")

Task("python-backend-engineer, backend-architect", "CACHE-6.6: Final review and release preparation.
  Activities: Code review, linting, test coverage verification, feature flag setup, release notes
  Criteria: >95% test coverage, no security issues, all PRD acceptance met
  Reason: Gate feature for production release")
```

---

## Task Summary - Phases 5-6

| Phase | Task ID | Task Title | Effort | Duration | Assigned To |
|-------|---------|-----------|--------|----------|------------|
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

**Phases 5-6 Total: 35 Story Points**

---

*[Back to Parent Plan](../persistent-project-cache-v1.md)*
