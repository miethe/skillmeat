---
title: 'Implementation Plan: Memory & Context Intelligence System'
description: Comprehensive phased implementation plan with task breakdown, subagent
  assignments, and acceptance criteria for the Memory & Context Intelligence System
  feature.
audience:
- ai-agents
- developers
- architects
tags:
- implementation
- planning
- phases
- tasks
- memory
- context
created: 2026-02-05
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/memory-context-system-v1.md
- /docs/project_plans/design-specs/memory-context-system-ui-spec.md
---

# Implementation Plan: Memory & Context Intelligence System

**Plan ID**: `IMPL-2026-02-05-memory-context-system-v1`
**Date**: 2026-02-05
**Author**: Implementation Planner Agent
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/memory-context-system-v1.md`
- **UI Spec**: `/docs/project_plans/design-specs/memory-context-system-ui-spec.md`
- **API Reference**: `/skillmeat/api/CLAUDE.md`
- **Template Reference**: `.claude/context/key-context/router-patterns.md`

**Complexity**: Large (L)
**Total Estimated Effort**: 57 story points
**Target Timeline**: 6-7 weeks (Phase 0-6), optional Phase 5 in v1.1

---

## Executive Summary

This implementation plan guides the development of a project-scoped memory system that eliminates agent amnesia by capturing learnings, composing dynamic context packs, and providing institutional memory across sessions. The plan follows MeatyPrompts layered architecture (Database → Repository → Service → API → UI) with phased delivery starting from foundational database work through optional auto-extraction in Phase 5.

**Key Milestones**:
1. Phase 0: Verify prerequisites and feature branch setup (0.5 weeks)
2. Phase 1: Database schema and repositories (1 week)
3. Phase 2: Services and API routers (1.5 weeks)
4. Phase 3: Frontend Memory Inbox UI (1.5 weeks, can overlap Phase 2)
5. Phase 4: Context packing and preview (1 week)
6. Phase 6: Testing, documentation, and deployment (1 week)
7. Phase 5 (v1.1): Auto-extraction service (2 weeks, optional)

**Success Criteria**: All functional requirements (FR-1 through FR-13) implemented with 80%+ test coverage, <200ms list query p95, <500ms pack_context p95, WCAG 2.1 AA accessibility compliance.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture, build bottom-up:

1. **Database Layer** - Create `memory_items`, `context_modules`, `module_memory_items` tables with Alembic migration
2. **Repository Layer** - CRUD operations with cursor pagination, content hash deduplication
3. **Service Layer** - Business logic (promotion, deprecation, merge, context packing)
4. **API Layer** - FastAPI routers following `context_entities.py` pattern
5. **UI Layer** - React components, hooks, forms, keyboard navigation
6. **Testing Layer** - Unit, integration, component, E2E tests (85%+ coverage)
7. **Documentation Layer** - API docs, user guides, component documentation
8. **Deployment Layer** - Feature flags, monitoring, observability

### Parallel Work Opportunities

- **Phase 1 & 2 can overlap**: While database migration is being written, repository implementation can start
- **Phase 2 design & Phase 3**: UI designers can create wireframes and component specs during Phase 2 service development
- **Phase 3 & 4 backend coordination**: Frontend can implement Memory Inbox while backend implements context packing
- **Testing throughout**: Unit tests can be written during each phase; integration tests after Phase 2 completes
- **Documentation concurrent**: API docs updated as routers are completed; user guides written after UI milestone

### Critical Path

1. Phase 1 (Database) → 2 (Services/API) → 3 (UI) → 6 (Tests/Docs) → Deployment
2. Phase 4 (Context Packing) can start after Phase 2 API is complete
3. Phase 5 (Auto-Extraction) is optional, depends on agent run log storage infrastructure

---

## Phase 0: Prerequisites & Foundation

**Duration**: 0.5 weeks
**Dependencies**: None (blocking)
**Assigned Subagent(s)**: lead-architect, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PREP-0.1 | Verify Alembic Setup | Confirm migration chain is initialized and working | Alembic env configured, test migration runs successfully | 1 pt | data-layer-expert | None |
| PREP-0.2 | Create Feature Branch | Create `feat/memory-context-system-v1` branch from main | Branch exists, initial commit with plan reference | 0.5 pt | lead-pm | None |
| PREP-0.3 | API Pattern Review | Review `context_entities.py` router and schema patterns | Design notes capturing pagination, DTO patterns, error handling | 1 pt | backend-architect | None |
| PREP-0.4 | Test Infrastructure Setup | Initialize pytest fixtures for memory services | Fixtures for projects, sessions, database; test database seeded | 1 pt | python-backend-engineer | None |

**Phase 0 Quality Gates**:
- [ ] Alembic working in local environment
- [ ] Feature branch created and pushed
- [ ] Router pattern documentation reviewed
- [ ] Test fixtures ready for use

---

## Phase 1: Database + Repository Layer

**Duration**: 1 week
**Dependencies**: Phase 0 complete
**Assigned Subagent(s)**: data-layer-expert, python-backend-engineer

### 1.1 Database Schema Design

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DB-1.1 | Schema Design | Create Alembic migration for 3 tables with relationships | Migration file created, FK relationships defined, all columns specified | 2 pts | data-layer-expert | PREP-0.1 |
| DB-1.2 | ORM Models | Implement SQLAlchemy models in `cache/models.py` | MemoryItem, ContextModule, ModuleMemoryItem models with all fields and relationships | 2 pts | python-backend-engineer | DB-1.1 |
| DB-1.3 | Indexes & Constraints | Add indexes for query optimization and UNIQUE constraints | Indexes on (project_id, status), (project_id, type), (content_hash); FK cascade deletes | 1 pt | data-layer-expert | DB-1.2 |

**Tables Created**:

1. **memory_items**
   - Columns: id (UUID PK), project_id (FK), type, content, confidence (0.0-1.0), status (candidate/active/stable/deprecated), provenance_json, anchors_json, ttl_policy_json, content_hash (UNIQUE), access_count, created_at, updated_at, deprecated_at
   - Constraints: FK project_id, UNIQUE content_hash, CHECK confidence BETWEEN 0 AND 1

2. **context_modules**
   - Columns: id (UUID PK), project_id (FK), name, description, selectors_json, priority (int), content_hash, created_at, updated_at
   - Constraints: FK project_id

3. **module_memory_items**
   - Columns: module_id (FK), memory_id (FK), ordering (int)
   - Constraints: PK (module_id, memory_id), FK cascades

### 1.2 Repository Layer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| REPO-1.4 | MemoryItemRepository | Implement CRUD + find_by_content_hash, list with filters/pagination | All methods working, cursor pagination implemented, 85%+ test coverage | 3 pts | python-backend-engineer | DB-1.3 |
| REPO-1.5 | ContextModuleRepository | Implement CRUD + find_by_project_id | CRUD operations complete, list returns modules with memory counts | 2 pts | python-backend-engineer | DB-1.3 |
| REPO-1.6 | Transaction Handling | Add rollback/error handling for all mutations | Errors trigger automatic rollback, no partial writes | 1 pt | data-layer-expert | REPO-1.4 |
| TEST-1.7 | Repository Tests | Unit tests for all repository methods | 85%+ coverage, all CRUD ops tested, pagination edge cases | 2 pts | python-backend-engineer | REPO-1.6 |

**Pagination Pattern** (following `context_entities.py`):
- Use cursor-based pagination with base64-encoded cursors
- Cursor value: `{id}:{sort_field_value}`
- Response envelope: `items`, `next_cursor`, `prev_cursor`, `has_more`, `total_count`

**Phase 1 Quality Gates**:
- [ ] Alembic migration passes forward/backward tests
- [ ] All 3 ORM models correctly mapped
- [ ] Indexes created and verified
- [ ] Repository CRUD operations working
- [ ] Cursor pagination implemented
- [ ] Test coverage >85%

---

## Phase 2: Service + API Layer

**Duration**: 1.5 weeks
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: backend-architect, python-backend-engineer

### 2.1 Service Layer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SVC-2.1 | MemoryService - Core | Create service with CRUD methods (create, get, list, update, delete) | All methods return DTOs, validation applied, errors logged | 3 pts | backend-architect | REPO-1.6 |
| SVC-2.2 | MemoryService - Lifecycle | Implement promote (candidate→active→stable), deprecate, state machine logic | State transitions validated, audit trail recorded, dates tracked | 3 pts | backend-architect | SVC-2.1 |
| SVC-2.3 | MemoryService - Merge | Implement merge two memories, consolidate content or select one | User confirms before merge, audit trail logged, status resolved | 2 pts | python-backend-engineer | SVC-2.1 |
| SVC-2.4 | ContextModuleService | Implement compose (group memories + entities), list, update, delete | Selectors validated, modules persist, many-to-many relationships working | 2 pts | python-backend-engineer | REPO-1.5 |
| SVC-2.5 | ContextPackerService | Implement pack_context(budget_tokens) selecting memories + entities | Budget respected, high confidence first, returns DTO with metadata | 3 pts | backend-architect | SVC-2.1, SVC-2.4 |

**Service DTOs Created**:
- `MemoryItemCreateRequest`: type, content, confidence, ttl_policy
- `MemoryItemResponse`: Full representation with all fields
- `MemoryItemListResponse`: Paginated response with cursor
- `ContextModuleCreateRequest`: name, description, selectors
- `ContextModuleResponse`: Full module with nested memories
- `ContextPackRequest`: module_id, budget_tokens
- `ContextPackResponse`: Selected items, total_tokens, efficiency_score

### 2.2 API Layer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-2.6 | Memory Items Router - CRUD | Implement GET/POST/PUT/DELETE for `/api/v1/memory-items` | All endpoints return DTOs, pagination working, error handling | 2 pts | python-backend-engineer | SVC-2.1 |
| API-2.7 | Memory Items Router - Lifecycle | Implement PATCH `/promote/{id}` and `/deprecate/{id}` endpoints | State transitions validated, only valid transitions allowed, reason captured | 2 pts | python-backend-engineer | SVC-2.2 |
| API-2.8 | Memory Items Router - Merge | Implement POST `/memory-items/{id}/merge` endpoint | Two-way response, confirmation required, both items resolved | 1 pt | python-backend-engineer | SVC-2.3 |
| API-2.9 | Context Modules Router | Implement GET/POST/PUT/DELETE for `/api/v1/context-modules` | All endpoints return DTOs, relationships preserved, selectors validated | 2 pts | python-backend-engineer | SVC-2.4 |
| API-2.10 | Context Packing API | Implement POST `/context-packs/preview` and `/generate` endpoints | Preview is read-only, generate creates deployable pack, token count accurate | 2 pts | python-backend-engineer | SVC-2.5 |
| API-2.11 | OpenAPI Documentation | Update `openapi.json` with all new endpoints and schemas | All endpoints documented, request/response schemas accurate, examples provided | 1 pt | api-documenter | API-2.10 |
| TEST-2.12 | API Integration Tests | Integration tests for all endpoints (CRUD, promote, deprecate, merge, pack) | All endpoints tested, happy path and error cases, 85%+ coverage | 3 pts | python-backend-engineer | API-2.10 |
| TEST-2.13 | End-to-End Service Test | E2E test: create → approve → compose → pack | Complete workflow works, data persists correctly, all state transitions valid | 1 pt | python-backend-engineer | TEST-2.12 |

**Error Handling Pattern**:
- Use `ErrorResponse` envelope (consistent with existing API)
- Return appropriate HTTP status codes: 400 (validation), 401 (auth), 404 (not found), 409 (conflict), 422 (unprocessable)
- Log all errors with trace ID and context

**Phase 2 Quality Gates**:
- [ ] All services passing unit tests (80%+ coverage)
- [ ] All API endpoints returning correct responses
- [ ] Cursor pagination working
- [ ] DTOs never expose ORM models
- [ ] ErrorResponse envelope consistent
- [ ] OpenAPI documentation complete
- [ ] Integration tests passing

---

## Phase 3: Frontend - Memory Inbox UI

**Duration**: 1.5 weeks
**Dependencies**: Phase 2 API complete (can start design during Phase 2)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

### 3.1 Page & Components

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-3.1 | Memory Inbox Page Layout | Create `/projects/[id]/memory/page.tsx` with header, filter bar, list, detail panel | Page renders, layout responsive, all sections present | 2 pts | frontend-developer | API-2.6 |
| UI-3.2 | MemoryCard Component | Display memory with type badge, content, confidence bar, metadata, status dot | All fields rendered, accessible, hover states | 2 pts | ui-engineer-enhanced | UI-3.1 |
| UI-3.3 | Filter Bar Components | Type tabs, status dropdown, sort control, search input | All filters functional, counts accurate, selection persisted | 2 pts | frontend-developer | UI-3.1 |
| UI-3.4 | Detail Panel Component | Right sidebar showing full memory, provenance, access count, related items | Panel populates on card selection, shows full content, links work | 2 pts | frontend-developer | UI-3.2 |
| UI-3.5 | Triage Action Buttons | Implement Approve, Edit, Reject, Merge buttons/modals | Buttons call correct APIs, modals appear, confirmations work | 3 pts | ui-engineer-enhanced | UI-3.2 |
| UI-3.6 | Memory Form Modal | Create/edit modal with type, content, confidence, ttl_policy inputs | Form validation, before/after diff shown, submission to API | 2 pts | frontend-developer | UI-3.5 |
| UI-3.7 | Merge Modal | Three-pane comparison, select target, preview result | Comparison shows differences, user can adjust, merge submits | 2 pts | ui-engineer-enhanced | UI-3.5 |
| UI-3.8 | Batch Selection & Actions | Checkbox selection, bulk action toolbar, select/clear all | Selection persists, toolbar shows count, batch actions work | 2 pts | frontend-developer | UI-3.2 |

### 3.2 Hooks & State Management

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| HOOKS-3.9 | useMemoryItems Hook | Query hook for list with filters/pagination/search | Hook handles loading, error, success states; pagination works | 1 pt | frontend-developer | API-2.6 |
| HOOKS-3.10 | useMutateMemory Hook | Mutation hook for create, update, promote, deprecate, merge | All mutations implemented, optimistic updates, error handling | 2 pts | frontend-developer | API-2.7 |
| HOOKS-3.11 | useMemorySelection Hook | Manage selected item(s), focus state, keyboard navigation | Selection state managed, keyboard shortcuts work, focus tracked | 1 pt | frontend-developer | UI-3.8 |

### 3.3 Keyboard & Accessibility

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| A11Y-3.12 | Keyboard Navigation | Implement J/K for up/down, A/E/R/M for actions, Enter for detail | All shortcuts work, no conflicts, modals focus-trap | 2 pts | frontend-developer | HOOKS-3.11 |
| A11Y-3.13 | WCAG Compliance | Ensure WCAG 2.1 AA: labels, roles, focus indicators, contrast | Accessibility audit passes, screen reader tested | 2 pts | web-accessibility-checker | UI-3.8 |
| TEST-3.14 | Component Tests | React Testing Library tests for all components | 85%+ coverage, focus on user interactions, accessibility | 2 pts | frontend-developer | UI-3.8 |
| TEST-3.15 | Keyboard Tests | Tests for keyboard navigation and shortcuts | All shortcuts tested, focus management verified | 1 pt | web-accessibility-checker | A11Y-3.12 |

**Keyboard Shortcuts**:
- `J` / `K` — Navigate up/down in list (Vim-style)
- `A` — Approve selected memory
- `E` — Edit selected memory
- `R` — Reject/deprecate selected memory
- `M` — Merge selected memory with another
- `Space` — Toggle selection of focused item
- `?` — Show keyboard help modal

**Confidence Color Tiers**:
- High (≥85%): Emerald (#10b981)
- Medium (60-84%): Amber (#f59e0b)
- Low (<60%): Red (#ef4444)

**Phase 3 Quality Gates**:
- [ ] Memory Inbox page renders without errors
- [ ] All filters and search working
- [ ] Triage actions update memory status correctly
- [ ] Keyboard navigation works smoothly
- [ ] Component test coverage >85%
- [ ] WCAG 2.1 AA compliance verified
- [ ] No console errors or warnings

---

## Phase 4: Context Packing + Preview

**Duration**: 1 week
**Dependencies**: Phase 2 API complete, Phase 3 UI (can overlap)
**Assigned Subagent(s)**: backend-architect, ui-engineer-enhanced

### 4.1 Backend Context Packing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PACK-4.1 | ContextPackerService - Selection Logic | Implement memory selection by confidence, recency, selectors | Selects high-confidence items first, respects filters, reaches budget | 2 pts | backend-architect | SVC-2.5 |
| PACK-4.2 | ContextPackerService - Token Estimation | Implement token counting (len(text)/4 approximation or GPT tokenizer) | Token count accurate to within 5%, budget enforcement | 1 pt | python-backend-engineer | PACK-4.1 |
| PACK-4.3 | EffectiveContext Composition | Build effective context markdown (memories + entities in order) | Markdown formatted, all selected items included, metadata preserved | 2 pts | python-backend-engineer | PACK-4.1 |

### 4.2 Frontend Context Packing UI

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-4.4 | ContextModulesTab | Tab in project manage page: create/edit/delete modules | Modules persist, selectors shown, memories displayed | 2 pts | frontend-developer | API-2.9 |
| UI-4.5 | ModuleEditor Component | UI for configuring memory selectors and adding memories | Selector dropdowns, memory list, preview updates in real-time | 2 pts | ui-engineer-enhanced | API-2.9 |
| UI-4.6 | EffectiveContextPreview Modal | Read-only markdown rendering, token count, budget indicator | Markdown rendered correctly, token count accurate, budget vs actual shown | 2 pts | ui-engineer-enhanced | API-2.10 |
| UI-4.7 | Context Pack Generation | Save module, export/deploy context pack option | Module saved, pack generated, can be copied/used in workflows | 1 pt | frontend-developer | UI-4.6 |

### 4.3 Testing

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-4.8 | Packer Service Tests | Edge cases: budget overflow, empty module, all candidates, mixed confidence | All edge cases handled, no crashes, graceful degradation | 1 pt | python-backend-engineer | PACK-4.3 |
| TEST-4.9 | Packer API Integration Tests | Test preview and generate endpoints with various inputs | Both endpoints working, responses accurate, error handling | 1 pt | python-backend-engineer | TEST-4.8 |
| TEST-4.10 | Context Module UI Tests | Component tests for module editor and preview modal | All interactions tested, data flows correctly, responsive | 1 pt | frontend-developer | UI-4.7 |

**Phase 4 Quality Gates**:
- [ ] pack_context() respects token budget
- [ ] Context modules persist across sessions
- [ ] Preview modal shows accurate token count
- [ ] High-confidence items prioritized in packs
- [ ] All packer tests passing (80%+ coverage)
- [ ] UI components tested and functional

---

## Phase 5: Auto-Extraction Service (Optional v1.1)

**Duration**: 2 weeks
**Dependencies**: Phase 2 API complete, Agent run log storage infrastructure (blocking prerequisite)
**Assigned Subagent(s)**: python-backend-engineer, ai-engineer
**Status**: Optional (defer to v1.1 if run log storage not ready)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| EXT-5.1 | MemoryExtractorService | Parse run logs, heuristic extraction of constraints/decisions/fixes | Heuristics identify key learnings, >70% accuracy on manual samples | 3 pts | ai-engineer | PREP-0.4 |
| EXT-5.2 | TF-IDF Deduplication | Offline cosine similarity matching to group similar candidates | Dedup groups near-duplicates, <1s for 100 items, <5% false positive rate | 3 pts | python-backend-engineer | EXT-5.1 |
| EXT-5.3 | Confidence Scoring | Score = frequency × recency × source_quality (0.0-1.0) | Scores calculated correctly, higher frequent items score higher, validation rules | 2 pts | ai-engineer | EXT-5.1 |
| API-5.4 | Extract API Endpoint | POST `/memory-items/extract` to trigger extraction for run | Endpoint queues extraction, returns candidates, stores to inbox | 1 pt | python-backend-engineer | EXT-5.3 |
| TEST-5.5 | Extractor Heuristics Tests | Unit tests for extraction heuristics on sample run logs | >70% accuracy on test set, edge cases handled | 2 pts | python-backend-engineer | EXT-5.1 |
| TEST-5.6 | Extract Integration Test | Full flow: run log → extraction → dedup → inbox population | Candidates appear in inbox, confidence scores reasonable | 1 pt | python-backend-engineer | API-5.4 |

**Blocking Prerequisite**: Agent run log storage must be implemented (separate PRD, PREREQ-0.1 in Phase 0).

---

## Phase 6: Testing, Documentation & Deployment

**Duration**: 1 week (concurrent with earlier phases)
**Dependencies**: All earlier phases
**Assigned Subagent(s)**: python-backend-engineer, frontend-developer, documentation-writer, DevOps

### 6.1 Test Coverage

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-6.1 | Service Unit Tests | Comprehensive unit tests for MemoryService, ContextModuleService, ContextPackerService | 85%+ coverage, all business logic paths tested, edge cases | 2 pts | python-backend-engineer | SVC-2.5 |
| TEST-6.2 | Repository Unit Tests | Comprehensive tests for all repository CRUD and query methods | 85%+ coverage, pagination, filtering, transactions tested | 1 pt | python-backend-engineer | REPO-1.6 |
| TEST-6.3 | API Contract Tests | Verify all endpoints match OpenAPI spec, request/response validation | All endpoints conform to spec, invalid requests rejected | 1 pt | api-librarian | API-2.11 |
| TEST-6.4 | Performance Benchmarks | Measure list query (<200ms), pack_context (<500ms), dedup (<1s for 100) | All benchmarks met, results documented | 1 pt | python-backend-engineer | TEST-2.12 |
| TEST-6.5 | Complete E2E Test | Create → approve → compose → pack → inject workflow | Entire user journey works, data consistent, no state errors | 1 pt | testing specialist | TEST-2.13 |

### 6.2 Documentation

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DOC-6.6 | API Documentation | Update `openapi.json`, document all endpoints with examples | All 11 endpoints documented, request/response examples shown | 1 pt | api-documenter | API-2.11 |
| DOC-6.7 | Service Documentation | Document service method signatures, examples, error handling | All public methods documented with docstrings and examples | 1 pt | documentation-writer | SVC-2.5 |
| DOC-6.8 | Database Schema Docs | Document tables, columns, relationships, indexes | Schema design decisions documented, ERD included | 1 pt | documentation-writer | DB-1.3 |
| DOC-6.9 | User Guide - Memory Inbox | How-to guide for triage workflow, keyboard shortcuts, bulk actions | Covers all workflows, screenshots, accessibility notes | 1 pt | documentation-writer | UI-3.8 |
| DOC-6.10 | User Guide - Context Modules | How to compose modules, configure selectors, generate packs | Covers composition workflow, examples with different selectors | 1 pt | documentation-writer | UI-4.7 |
| DOC-6.11 | Developer Guide | Architecture overview, extending memory system, testing patterns | Developers can add new memory types and selectors | 1 pt | documentation-writer | TEST-6.5 |

### 6.3 Deployment & Observability

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DEPLOY-6.12 | Feature Flags | Implement `MEMORY_CONTEXT_ENABLED`, `MEMORY_AUTO_EXTRACT` flags | Flags controllable via config, feature can be toggled safely | 1 pt | DevOps | API-2.6 |
| DEPLOY-6.13 | Observability Setup | OpenTelemetry spans for memory operations, structured JSON logging | All state changes logged with trace ID, performance metrics captured | 1 pt | backend-architect | SVC-2.5 |
| DEPLOY-6.14 | Monitoring Configuration | Dashboards for list latency, pack_context latency, inbox size | Alerts on latency >500ms, inbox >200 items | 1 pt | DevOps | DEPLOY-6.13 |
| DEPLOY-6.15 | Staging Deployment | Deploy to staging environment, run smoke tests | Feature works in staging, no breaking changes | 1 pt | DevOps | DEPLOY-6.12 |
| DEPLOY-6.16 | Production Rollout | Graduated rollout to production (feature flag initially off) | Rollout successful, monitoring healthy, no P0 issues | 1 pt | DevOps | DEPLOY-6.15 |

**Phase 6 Quality Gates**:
- [ ] Service/Repository test coverage >85%
- [ ] All API endpoints conforming to OpenAPI spec
- [ ] Performance benchmarks met (list <200ms, pack <500ms)
- [ ] E2E test passing
- [ ] All user guides complete
- [ ] Monitoring and alerting configured
- [ ] Feature flags working
- [ ] Staging deployment successful

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Alembic migration errors | High | Low | Early testing in Phase 0, rollback procedures documented, test forward/backward migrations |
| Dedup false positives in Phase 5 | High | Medium | Require user confirmation for merges, never auto-merge, validate before save, manual creation first in v1 |
| User inbox fatigue (>100 unreviewed) | High | High | Auto-deprecate low-confidence (<0.5) candidates after 30 days, batch actions toolbar, email notifications for important |
| Memory injection degrades context quality | Medium | Medium | Allow manual override of packer selections, preview before injection, track hit rate metric, iterative tuning |
| Sensitive data in memories (API keys) | High | Low | Regex scan for common patterns before save, warn user, allow override with confirmation |
| Auto-extraction produces low signal:noise | Medium | High | Keep high confidence threshold (0.7+), manual creation first in v1, refine heuristics in Phase 5 based on feedback |
| Memory items drift from reality | Medium | Medium | TTL policy: revalidate after N days, auto-deprecate items with low hit rate (<2 uses/month), user reviews deprecated items |
| Run log storage not ready (Phase 5 blocker) | High | High | Defer Phase 5 to v1.1, complete manual memory creation in v1, document extraction plan for v1.1 |
| Database write contention during extraction | Medium | Medium | Use WAL mode (standard SQLite 3.31+), queue writes via service layer, use transactions |
| UI keyboard shortcut conflicts | Medium | Low | Early testing with existing shortcut map, document all shortcuts, allow customization in settings (v1.1) |

---

## Resource Requirements

### Team Composition

- **Backend Engineer (Opus)**: 2 FTE (Phases 0-4), 1 FTE (Phase 6)
- **Frontend Engineer (Opus)**: 1 FTE (Phase 3), 0.5 FTE (Phase 4), part-time (Phase 6)
- **Data/Database Engineer (Opus)**: 0.5 FTE (Phase 1), 0.25 FTE (Phase 2)
- **QA/Testing Specialist**: 0.5 FTE (Phase 6)
- **Documentation Writer**: 0.25 FTE (Phase 6)
- **DevOps Engineer**: 0.25 FTE (Phase 6)

### Skill Requirements

- TypeScript/React, Python/FastAPI, SQLAlchemy, Next.js 15, TanStack Query
- SQLite, Git, pytest, Jest/React Testing Library, Playwright
- Accessibility (WCAG 2.1 AA), Performance optimization, OpenTelemetry
- API design (REST patterns, OpenAPI), Docker, CI/CD

---

## Critical Success Metrics

### Delivery Metrics
- On-time delivery (±10% of 6-7 weeks)
- Code coverage >85% (backend services, API)
- Component test coverage >80% (frontend)
- Zero P0/P1 bugs in first week post-launch

### Business Metrics
- Memory Inbox "Zero" maintained ≥80% of time (<20 unreviewed items)
- Average Time to Stable ≤14 days
- Context Token Reduction ≥30% vs full-file injection
- Memory Hit Rate ≥50% (% of injected items referenced in agent output)

### Technical Metrics
- API list query <200ms p95
- pack_context <500ms p95
- 100% API documentation
- 100% WCAG 2.1 AA compliance
- Zero SQL injection vulnerabilities
- Alembic migrations tested forward/backward

---

## Communication Plan

- **Daily Standups**: Report progress, blockers, dependencies
- **Weekly Status Reports**: Milestone completion, velocity, risks
- **Phase Reviews**: Gate reviews before moving to next phase
- **Bi-weekly Stakeholder Updates**: Feature progress, metrics, business impact

---

## Parallel Work Tracks

### Track A: Backend (Phases 0-2)
```
PREP-0.1,0.2,0.3,0.4 → DB-1.1,1.2,1.3 ↘
                                        → REPO-1.4,1.5,1.6 → SVC-2.1,2.2,2.3,2.4,2.5 → API-2.6...2.11 → TEST-2.12,2.13
```

### Track B: Frontend (Phase 3, can start design during Phase 2)
```
UI spec review → UI-3.1,3.2,3.3,3.4,3.5,3.6,3.7,3.8 (parallel) → HOOKS-3.9,3.10,3.11 (parallel)
→ A11Y-3.12,3.13,3.14,3.15 (parallel) → TEST-3.14,3.15
```

### Track C: Context Packing (Phase 4, overlaps Phase 3)
```
PACK-4.1,4.2,4.3 (backend) || UI-4.4,4.5,4.6,4.7 (frontend) → TEST-4.8,4.9,4.10
```

### Track D: Testing & Docs (Throughout, finalized Phase 6)
```
TEST-* and DOC-* concurrent with implementation, finalized in Phase 6
```

---

## Definition of Done (Phase-by-Phase)

### Phase 0 Done
- Alembic environment verified and working
- Feature branch created
- API patterns reviewed and documented
- Test infrastructure ready

### Phase 1 Done
- Migration file created and tested (forward/backward)
- ORM models mapped correctly
- All 3 repositories implemented with CRUD + pagination
- Repository tests >85% coverage

### Phase 2 Done
- All 3 services implemented and tested
- All 11 API endpoints working
- DTOs never expose ORM models
- OpenAPI documentation complete
- Integration tests passing
- E2E workflow test passing

### Phase 3 Done
- Memory Inbox page renders without errors
- All filters, search, sorting working
- Triage actions (approve, reject, edit, merge) functional
- Keyboard shortcuts working
- Component tests >85% coverage
- WCAG 2.1 AA compliance verified

### Phase 4 Done
- pack_context() respects token budget
- Context modules persist
- Preview modal shows accurate counts
- Packing tests passing
- UI for module composition complete

### Phase 6 Done
- Service/Repository/API test coverage >85%
- Performance benchmarks met
- E2E test passing
- All user guides published
- Feature flags working
- Monitoring configured
- Staging deployment successful

---

## Post-Implementation

### Phase 7 (Optional Future Work)
- Performance tuning based on production usage
- Auto-deprecation policy refinement based on hit rate data
- v1.1 Auto-extraction service (Phase 5) once run log storage ready
- Memory search/RAG (future roadmap)
- Cross-project memory sharing (future roadmap)

### Monitoring & Maintenance
- Daily: Monitor API latency, inbox size, error rates
- Weekly: Review hit rate metrics, user feedback
- Monthly: Refine confidence scoring heuristics, analyze deprecated items
- Quarterly: Long-term trend analysis, v1.1 feature planning

---

## Implementation Notes

### Database-Native vs Filesystem-Backed
Memory items are **DB-native** (not filesystem-backed) like Tags and Collections. No write-through to `.claude/` directories needed. Memory system lives purely in SQLite with backups handled at infrastructure level.

### Alembic Migration Naming
Use naming convention: `2026_02_05_001_create_memory_items.py`

### ORM Model Naming
- Singularized names: `MemoryItem` (not `MemoryItems`)
- UUID primary keys: `id = Column(String(32), primary_key=True, default=lambda: uuid4().hex)`
- Timestamps: `created_at`, `updated_at`, `deprecated_at` with timezone awareness

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Memory confidence must be between 0.0 and 1.0",
    "detail": {
      "field": "confidence",
      "value": 1.5
    }
  }
}
```

### Pagination Cursor Format
Base64-encoded: `{id}:{sort_field}` e.g., `YWJjMTIzOjEwMC4w` → `abc123:100.0`

---

**Progress Tracking:**

See `.claude/progress/memory-context-system-v1/all-phases-progress.md` for real-time task status.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-05
**Total Story Points**: 57 pts (excluding Phase 5 optional: 38 pts for Phases 0-4, 6)
**Target Velocity**: ~10 pts/week → 6-7 weeks (Phases 0-6), +2 weeks optional Phase 5
