---
type: progress
prd: smart-import-discovery
status: not_started
progress: 0
total_tasks: 35
phases: 5
created: 2025-11-30
updated: 2025-11-30
---

# Smart Import & Discovery - Progress Tracking

**PRD**: `/docs/project_plans/PRDs/enhancements/smart-import-discovery-v1.md`
**Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/smart-import-discovery-v1.md`

**Overall Status**: Not Started | Progress: 0/35 tasks | Effort: 95-110 story points

---

## Task Manifest

### Phase 1: Data Layer & Service Foundation (6 tasks, 34 story points)

| Task ID | Title | Status | Assigned To | Story Points | Dependencies | Notes |
|---------|-------|--------|-------------|--------------|--------------|-------|
| SID-001 | Create GitHub Metadata Extraction Service | pending | python-backend-engineer | 8 | - | githabMetadataExtractor class with URL parsing, API fetch, caching |
| SID-002 | Create Artifact Discovery Service | pending | python-backend-engineer | 8 | - | ArtifactDiscoveryService with .claude/ scanning, type detection |
| SID-003 | Implement Metadata Cache | pending | python-backend-engineer | 3 | - | MetadataCache with 1-hour TTL, thread-safe operations |
| SID-004 | Create Discovery & Import Schemas | pending | backend-architect | 5 | SID-001, SID-002 | Pydantic schemas for discovery, import, metadata responses |
| SID-005 | Unit Tests: GitHub Metadata Service | pending | python-backend-engineer | 5 | SID-001 | >80% coverage of URL parsing, API calls, caching, errors |
| SID-006 | Unit Tests: Artifact Discovery Service | pending | python-backend-engineer | 5 | SID-002 | >80% coverage of directory scanning, detection, validation |

**Phase 1 Quality Gates**:
- [ ] All services have >80% unit test coverage
- [ ] Error handling for invalid artifacts, GitHub API errors
- [ ] Metadata cache correctly implements TTL
- [ ] All schemas validated against existing artifact structures
- [ ] Performance: discovery scan <2 seconds for 50+ artifacts

---

### Phase 2: API Endpoints & Integration (5 tasks, 33 story points)

| Task ID | Title | Status | Assigned To | Story Points | Dependencies | Notes |
|---------|-------|--------|-------------|--------------|--------------|-------|
| SID-007 | Implement Discovery Endpoint | pending | python-backend-engineer | 5 | SID-002, SID-004 | POST /api/v1/artifacts/discover endpoint |
| SID-008 | Implement Bulk Import Endpoint | pending | python-backend-engineer | 8 | SID-002, SID-003, SID-004 | POST /api/v1/artifacts/discover/import with atomic transaction |
| SID-009 | Implement GitHub Metadata Endpoint | pending | python-backend-engineer | 5 | SID-001, SID-004 | GET /api/v1/artifacts/metadata/github endpoint |
| SID-010 | Implement Parameter Edit Endpoint | pending | backend-architect | 5 | SID-004 | PUT /api/v1/artifacts/{id}/parameters endpoint |
| SID-011 | Integration Tests: API Endpoints | pending | python-backend-engineer | 5 | SID-007 through SID-010 | >70% endpoint coverage for all scenarios |
| SID-012 | Error Handling & Validation | pending | backend-architect | 5 | SID-007 through SID-010 | Consistent error codes and user-friendly messages |

**Phase 2 Quality Gates**:
- [ ] All 4 endpoints implemented and tested
- [ ] Atomic operations verified for bulk import
- [ ] Error responses follow consistent format
- [ ] GitHub rate limiting handled gracefully
- [ ] Integration tests >70% coverage
- [ ] Performance: bulk import <3 seconds for 20 artifacts

---

### Phase 3: Frontend Components & Hooks (6 tasks, 39 story points)

| Task ID | Title | Status | Assigned To | Story Points | Dependencies | Notes |
|---------|-------|--------|-------------|--------------|--------------|-------|
| SID-013 | Create Discovery Banner Component | pending | ui-engineer-enhanced | 3 | SID-007 | DiscoveryBanner with count display and review CTA |
| SID-014 | Create Bulk Import Modal/Table | pending | ui-engineer-enhanced | 8 | SID-007, SID-008 | BulkImportModal with selectable rows, edit buttons, import action |
| SID-015 | Create Auto-Population Form Component | pending | ui-engineer-enhanced | 8 | SID-009 | AutoPopulationForm with GitHub URL input, metadata fetch, auto-fill |
| SID-016 | Create Parameter Editor Modal | pending | ui-engineer-enhanced | 5 | SID-010 | ParameterEditorModal for editing source, version, scope, tags |
| SID-017 | Create React Query Hooks | pending | frontend-developer | 5 | SID-007 through SID-010 | useDiscovery, useBulkImport, useGitHubMetadata, useEditParameters |
| SID-018 | Form Validation & Error States | pending | frontend-developer | 5 | SID-015, SID-016, SID-017 | Client-side validation, error messages, loading states |
| SID-019 | Component Integration Tests | pending | frontend-developer | 5 | SID-013 through SID-018 | >70% component coverage, user interactions, error scenarios |

**Phase 3 Quality Gates**:
- [ ] All 4 components render correctly in isolation and integrated
- [ ] React Query hooks properly handle async operations
- [ ] Form validation matches backend validation
- [ ] Loading states properly displayed
- [ ] Error messages clear and actionable
- [ ] Component tests >70% coverage

---

### Phase 4: Page Integration & UX Polish (7 tasks, 39 story points)

| Task ID | Title | Status | Assigned To | Story Points | Dependencies | Notes |
|---------|-------|--------|-------------|--------------|--------------|-------|
| SID-020 | Integrate Discovery into /manage Page | pending | frontend-developer | 5 | SID-007, SID-013, SID-014 | Scan on load, show banner, modal flow, import success |
| SID-021 | Integrate Auto-Population into Add Form | pending | frontend-developer | 5 | SID-009, SID-015 | URL field with debounced fetch, auto-fill, error recovery |
| SID-022 | Integrate Parameter Editor into Entity Detail | pending | ui-engineer-enhanced | 3 | SID-010, SID-016 | Edit button placement, modal open/close, success feedback |
| SID-023 | Polish Loading States & Error Messages | pending | frontend-developer | 5 | SID-014, SID-015, SID-016 | Skeleton states, clear error toasts, rollback feedback |
| SID-024 | Analytics Instrumentation | pending | frontend-developer | 5 | SID-007 through SID-023 | Track discovery, auto-population, bulk import, parameter edits |
| SID-025 | E2E Tests: Discovery Flow | pending | frontend-developer | 8 | All Phase 3 & 4 tasks | Full user journey: discover -> review -> import -> success |
| SID-026 | E2E Tests: Auto-Population Flow | pending | frontend-developer | 8 | All Phase 3 & 4 tasks | Full user journey: paste URL -> fetch -> fill -> import |

**Phase 4 Quality Gates**:
- [ ] All 3 pages/modals properly integrated
- [ ] E2E tests cover main user journeys
- [ ] Analytics events firing correctly
- [ ] Error scenarios tested and handled
- [ ] Loading states appropriate for each operation
- [ ] Accessibility checks passed

---

### Phase 5: Testing, Documentation & Deployment (5 tasks, 37 story points)

| Task ID | Title | Status | Assigned To | Story Points | Dependencies | Notes |
|---------|-------|--------|-------------|--------------|--------------|-------|
| SID-027 | Performance Testing & Optimization | pending | python-backend-engineer | 5 | Phase 2, Phase 4 | Discovery <2s, fetch <1s (cached), bulk import <3s |
| SID-028 | Error Scenario Testing | pending | python-backend-engineer | 5 | Phase 2, Phase 3 | GitHub down, invalid artifacts, network failures, partial failures |
| SID-029 | Accessibility Audit | pending | ui-engineer-enhanced | 3 | Phase 3, Phase 4 | Modal keyboard nav, table selection, screen reader announcements |
| SID-030 | User Guide: Discovery | pending | documentation-writer | 3 | SID-007 | How to use discovery, what's discovered, troubleshooting |
| SID-031 | User Guide: Auto-Population | pending | documentation-writer | 3 | SID-009 | How to use auto-population, supported sources, manual override |
| SID-032 | API Documentation | pending | documentation-writer | 3 | SID-007 through SID-010 | OpenAPI spec, endpoint examples, schema docs, error codes |
| SID-033 | Feature Flag Implementation | pending | backend-architect | 5 | Phase 2 | ENABLE_AUTO_DISCOVERY, ENABLE_AUTO_POPULATION flags |
| SID-034 | Monitoring & Error Tracking | pending | backend-architect | 5 | Phase 2, Phase 4 | Error tracking, performance metrics, analytics, alerts |
| SID-035 | Final Integration & Smoke Tests | pending | python-backend-engineer | 5 | All phases | Full system smoke tests, data consistency checks |

**Phase 5 Quality Gates**:
- [ ] Overall test coverage >85% (backend + frontend combined)
- [ ] All performance benchmarks met
- [ ] All documentation complete and reviewed
- [ ] Feature flags implemented and tested
- [ ] Monitoring and error tracking configured
- [ ] Final smoke tests passed
- [ ] No regressions in existing features

---

## Parallelization Strategy

### Batch 1: Phase 1 Services (Execute in Parallel)
```
SID-001, SID-002, SID-003 [python-backend-engineer] - 3 parallel streams
SID-004 [backend-architect] - Can start once SID-001/002 ready
SID-005, SID-006 [python-backend-engineer] - After services ready
```
**Duration**: 1-1.5 weeks | **Blockers**: None | **Entry Point**: SID-001/002/003

### Batch 2: Phase 2 API Endpoints (Mostly Sequential with Parallel Prep)
```
SID-007, SID-008, SID-009 [python-backend-engineer] - Sequential dependency
SID-010, SID-012 [backend-architect] - Can run in parallel with above
SID-011 [python-backend-engineer] - After all endpoints ready
```
**Duration**: 1 week | **Blockers**: Phase 1 completion | **Entry Point**: SID-007

### Batch 3: Phase 3 Frontend Components (Execute in Parallel)
```
SID-013, SID-014, SID-015, SID-016 [ui-engineer-enhanced] - 4 parallel streams
SID-017, SID-018, SID-019 [frontend-developer] - After components ready
```
**Duration**: 1.5 weeks | **Blockers**: Phase 2 completion (API endpoints) | **Entry Point**: SID-013

### Batch 4: Phase 4 Integration & UX (Mix of Sequential and Parallel)
```
SID-020, SID-021, SID-022 [frontend-developer, ui-engineer] - 3 parallel
SID-023, SID-024 [frontend-developer] - After integration ready
SID-025, SID-026 [frontend-developer] - 2 parallel E2E tests
```
**Duration**: 1-1.5 weeks | **Blockers**: Phase 3 completion | **Entry Point**: SID-020

### Batch 5: Phase 5 Testing & Deployment (Mostly Parallel)
```
SID-027, SID-028 [python-backend-engineer] - Performance & error testing (parallel)
SID-029 [ui-engineer-enhanced] - Accessibility audit (parallel)
SID-030, SID-031, SID-032 [documentation-writer] - 3 parallel documentation tasks
SID-033, SID-034 [backend-architect] - Feature flags & monitoring (parallel)
SID-035 [python-backend-engineer] - Final smoke tests (sequential, last)
```
**Duration**: 1-1.5 weeks | **Blockers**: All phases complete | **Entry Point**: SID-027 (most tasks parallel)

---

## Orchestration Quick Reference

### Batch 1: Phase 1 (Weeks 1-1.5)

**Parallel Stream 1 - Core Services**:
```
Task("python-backend-engineer", "SID-001: Create GitHub Metadata Extraction Service
  - skillmeat/core/github_metadata.py
  - Parse GitHub URLs (user/repo/path@version)
  - Fetch metadata from GitHub API and SKILL.md files
  - Implement caching with TTL
  - Handle rate limits gracefully
  Estimate: 8 pts")

Task("python-backend-engineer", "SID-002: Create Artifact Discovery Service
  - skillmeat/core/discovery.py
  - Scan .claude/artifacts/ recursively
  - Detect artifact types (skill, command, agent, hook, mcp)
  - Extract metadata from frontmatter
  - Handle invalid artifacts gracefully
  Estimate: 8 pts")

Task("python-backend-engineer", "SID-003: Implement Metadata Cache
  - skillmeat/core/cache.py
  - In-memory cache with 1-hour TTL
  - Thread-safe operations
  - Cache hit/miss tracking
  Estimate: 3 pts")
```

**After Core Services Ready**:
```
Task("backend-architect", "SID-004: Create Discovery & Import Schemas
  - skillmeat/api/schemas/artifacts.py
  - DiscoveredArtifact, DiscoveryRequest, DiscoveryResult
  - BulkImportRequest, BulkImportResult, ImportResult
  - GitHubMetadata, MetadataFetchResponse
  - ArtifactParameters, ParameterUpdateRequest/Response
  Estimate: 5 pts")

Task("python-backend-engineer", "SID-005: Unit Tests: GitHub Metadata Service
  - skillmeat/core/tests/test_github_metadata.py
  - >80% coverage: URL parsing, API calls, caching, errors
  Estimate: 5 pts")

Task("python-backend-engineer", "SID-006: Unit Tests: Artifact Discovery Service
  - skillmeat/core/tests/test_discovery_service.py
  - >80% coverage: directory scan, detection, validation
  - Performance: <2 seconds for 50+ artifacts
  Estimate: 5 pts")
```

### Batch 2: Phase 2 (Weeks 1.5-2.5)

```
Task("python-backend-engineer", "SID-007: Implement Discovery Endpoint
  - skillmeat/api/routers/artifacts.py
  - POST /api/v1/artifacts/discover
  - Returns DiscoveryResult with artifacts list and errors
  Estimate: 5 pts")

Task("python-backend-engineer", "SID-008: Implement Bulk Import Endpoint
  - skillmeat/api/routers/artifacts.py
  - POST /api/v1/artifacts/discover/import
  - Atomic transaction with validation
  - Per-artifact success/failure status
  Estimate: 8 pts")

Task("python-backend-engineer", "SID-009: Implement GitHub Metadata Endpoint
  - skillmeat/api/routers/artifacts.py
  - GET /api/v1/artifacts/metadata/github?source=...
  - Uses cache, handles GitHub errors
  Estimate: 5 pts")

Task("backend-architect", "SID-010: Implement Parameter Edit Endpoint
  - skillmeat/api/routers/artifacts.py
  - PUT /api/v1/artifacts/{artifact_id}/parameters
  - Validate and atomically update artifact
  Estimate: 5 pts")

Task("python-backend-engineer", "SID-011: Integration Tests: API Endpoints
  - skillmeat/api/tests/test_discovery_endpoints.py
  - >70% endpoint coverage
  Estimate: 5 pts")

Task("backend-architect", "SID-012: Error Handling & Validation
  - Consistent error format across endpoints
  - User-friendly error messages
  - Server-side validation
  Estimate: 5 pts")
```

### Batch 3: Phase 3 (Weeks 2-3)

```
Task("ui-engineer-enhanced", "SID-013: Create Discovery Banner Component
  - skillmeat/web/components/discovery/DiscoveryBanner.tsx
  - Display count, Review & Import button, dismissible
  Estimate: 3 pts")

Task("ui-engineer-enhanced", "SID-014: Create Bulk Import Modal/Table
  - skillmeat/web/components/discovery/BulkImportModal.tsx
  - Selectable table, edit per row, import action
  Estimate: 8 pts")

Task("ui-engineer-enhanced", "SID-015: Create Auto-Population Form Component
  - skillmeat/web/components/discovery/AutoPopulationForm.tsx
  - GitHub URL input, metadata fetch, auto-fill form fields
  Estimate: 8 pts")

Task("ui-engineer-enhanced", "SID-016: Create Parameter Editor Modal
  - skillmeat/web/components/discovery/ParameterEditorModal.tsx
  - Edit source, version, scope, tags
  Estimate: 5 pts")

Task("frontend-developer", "SID-017: Create React Query Hooks
  - skillmeat/web/hooks/useDiscovery.ts
  - useDiscovery, useBulkImport, useGitHubMetadata, useEditParameters
  Estimate: 5 pts")

Task("frontend-developer", "SID-018: Form Validation & Error States
  - Client-side validation with react-hook-form + Zod
  - Error messages, loading states, success toasts
  Estimate: 5 pts")

Task("frontend-developer", "SID-019: Component Integration Tests
  - skillmeat/web/tests/discovery.test.tsx
  - >70% component coverage
  Estimate: 5 pts")
```

### Batch 4: Phase 4 (Weeks 3-4)

```
Task("frontend-developer", "SID-020: Integrate Discovery into /manage Page
  - skillmeat/web/app/manage/page.tsx
  - Scan on load, show banner, modal flow, success feedback
  Estimate: 5 pts")

Task("frontend-developer", "SID-021: Integrate Auto-Population into Add Form
  - Add auto-population to artifact add form
  - Debounced fetch, auto-fill, error recovery
  Estimate: 5 pts")

Task("ui-engineer-enhanced", "SID-022: Integrate Parameter Editor into Entity Detail
  - skillmeat/web/app/manage/[type]/[name]/page.tsx
  - Add Edit Parameters button, open modal, success feedback
  Estimate: 3 pts")

Task("frontend-developer", "SID-023: Polish Loading States & Error Messages
  - Skeleton screens, spinners, clear error toasts
  - Rollback feedback, screen reader announcements
  Estimate: 5 pts")

Task("frontend-developer", "SID-024: Analytics Instrumentation
  - Track discovery scans, auto-population, bulk import, parameter edits
  - Use existing analytics SDK
  Estimate: 5 pts")

Task("frontend-developer", "SID-025: E2E Tests: Discovery Flow
  - skillmeat/web/e2e/discovery.spec.ts
  - Full user journey: discover -> review -> import -> success
  Estimate: 8 pts")

Task("frontend-developer", "SID-026: E2E Tests: Auto-Population Flow
  - skillmeat/web/e2e/auto-population.spec.ts
  - Full user journey: paste URL -> fetch -> fill -> import
  Estimate: 8 pts")
```

### Batch 5: Phase 5 (Weeks 4.5-5.5)

```
Task("python-backend-engineer", "SID-027: Performance Testing & Optimization
  - Create performance benchmarks
  - Verify: discovery <2s, fetch <1s (cached), bulk import <3s
  Estimate: 5 pts")

Task("python-backend-engineer", "SID-028: Error Scenario Testing
  - Test GitHub API down, invalid artifacts, network failures
  - Verify graceful error handling and recovery
  Estimate: 5 pts")

Task("ui-engineer-enhanced", "SID-029: Accessibility Audit
  - Test keyboard navigation, screen reader, WCAG 2.1 AA
  Estimate: 3 pts")

Task("documentation-writer", "SID-030: User Guide: Discovery
  - docs/guides/discovery-guide.md
  - What, how, when, troubleshooting, best practices
  Estimate: 3 pts")

Task("documentation-writer", "SID-031: User Guide: Auto-Population
  - docs/guides/auto-population-guide.md
  - Supported sources, manual override, troubleshooting
  Estimate: 3 pts")

Task("documentation-writer", "SID-032: API Documentation
  - docs/api/discovery-endpoints.md
  - Endpoint specs, schemas, examples, error codes
  Estimate: 3 pts")

Task("backend-architect", "SID-033: Feature Flag Implementation
  - skillmeat/api/config.py
  - ENABLE_AUTO_DISCOVERY, ENABLE_AUTO_POPULATION, GITHUB_TOKEN, CACHE_TTL
  Estimate: 5 pts")

Task("backend-architect", "SID-034: Monitoring & Error Tracking
  - Set up error tracking (Sentry), performance metrics
  - Analytics dashboard, alert thresholds
  Estimate: 5 pts")

Task("python-backend-engineer", "SID-035: Final Integration & Smoke Tests
  - Full system smoke tests, data consistency checks
  - Verify no regressions in existing features
  Estimate: 5 pts")
```

---

## Status Overview

| Phase | Tasks | Status | Story Points | Duration | Owner Team |
|-------|-------|--------|--------------|----------|-----------|
| 1: Data Layer & Services | 6 | Not Started | 34 | 1-1.5 weeks | Backend (2) |
| 2: API Endpoints | 6 | Not Started | 33 | 1 week | Backend (3) |
| 3: Frontend Components | 7 | Not Started | 39 | 1.5 weeks | Frontend (2) |
| 4: Integration & UX | 7 | Not Started | 39 | 1-1.5 weeks | Frontend (2) |
| 5: Testing & Deployment | 9 | Not Started | 37 | 1-1.5 weeks | Cross-team (5) |
| **TOTAL** | **35** | **Not Started** | **182** | **4-6 weeks** | **5-6 developers** |

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|-----------|-----------|-------|
| GitHub API rate limiting blocks metadata fetch | MEDIUM | MEDIUM | Cache metadata (1h TTL), optional token, graceful fallback | Backend |
| Bulk import fails partway, partial corruption | HIGH | LOW | Atomic transaction, validate all before import, rollback on error | Backend |
| Invalid artifacts in .claude/ crash discovery scan | MEDIUM | MEDIUM | Graceful error handling per artifact, skip invalid entries, log | Backend |
| User mistakenly selects wrong artifacts in bulk import | MEDIUM | MEDIUM | Show clear preview table, require confirmation, atomic rollback | Frontend |
| Metadata from GitHub incorrect or incomplete | LOW | MEDIUM | Show "auto-fetched" badge, allow user edits, manual override | Frontend |
| Discovery scan slow for projects with 100+ artifacts | MEDIUM | LOW | Incremental scanning, background job, cache results | Backend |
| Duplicate artifacts if user imports same source twice | MEDIUM | MEDIUM | Check for duplicates in batch, merge with existing, show conflicts | Backend |
| Non-standard GitHub formats break parser | MEDIUM | LOW | Validate format strictly, show clear error, allow manual source entry | Backend |

---

## Blockers & Dependencies

**Phase 1 Blockers**: None - can start immediately
**Phase 2 Blockers**: Phase 1 completion (services and schemas)
**Phase 3 Blockers**: Phase 2 completion (API endpoints ready)
**Phase 4 Blockers**: Phase 3 completion (components and hooks ready)
**Phase 5 Blockers**: All previous phases (full system ready for testing)

**Critical Path**:
```
SID-001/002/003 → SID-004 → SID-007/008/009/010 → SID-013/014/015/016 → SID-020/021/022 → SID-035
```

---

## Notes for Session Handoff

- **Entry Point**: Begin with Phase 1, Batch 1 (SID-001/002/003) in parallel
- **Key Decisions**: Feature flags enable gradual rollout; atomic transactions prevent data corruption
- **Testing Priority**: Performance benchmarks must be met before deployment
- **Documentation**: Three user guides + API docs required for feature launch
- **Accessibility**: Mandatory audit in Phase 5 before production release
- **Monitoring**: Error tracking and analytics critical for post-launch metrics

---

**Created**: 2025-11-30
**Status**: Ready for execution
**Next Step**: Delegate Phase 1 tasks to python-backend-engineer for parallel execution
