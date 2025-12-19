---
title: "Implementation Plan: Tags Refactor V1"
description: "Comprehensive tagging system with database backend, frontend UI components, and filtering capabilities"
audience: [ai-agents, developers]
tags: [implementation, planning, phases, tags, database, ui]
created: 2025-12-18
updated: 2025-12-18
category: "product-planning"
status: draft
related:
  - /docs/project_plans/ideas/tags-refactor-v1.md
---

# Implementation Plan: Tags Refactor V1

**Plan ID**: `IMPL-2025-12-18-TAGS-REFACTOR-V1`
**Date**: 2025-12-18
**Author**: Implementation Planner
**Related Documents**:
- **Idea**: `/docs/project_plans/ideas/tags-refactor-v1.md`
- **Bug Report**: Artifact parameters scope validation (422 error)

**Complexity**: Medium
**Total Estimated Effort**: 52 story points
**Target Timeline**: 3-4 weeks (parallel work streams)

## Executive Summary

This implementation plan covers a complete tags system for SkillMeat artifacts. The effort includes three parallel work streams: (1) fixing the artifact scope validation bug in Phase 0, (2) building the database and API backend for tags in Phases 1-4, and (3) implementing the frontend UI components and filtering in Phases 5-6. The system uses a many-to-many junction table for artifact-tag associations, enabling global tag reuse across all artifacts. Key features include a shadcn.io-style tag input component, tag-based filtering with popover UI, and global tag management. Testing and documentation follow standard quality gates.

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Database Layer** - Tags table, artifact_tags junction, indexes
2. **Repository Layer** - Tag CRUD, artifact association queries
3. **Service Layer** - Tag management, business logic, DTOs
4. **API Layer** - FastAPI routers, endpoints, OpenAPI docs
5. **UI Layer** - Tag input, badge display, filter components
6. **Testing Layer** - Unit, integration, component, E2E tests
7. **Documentation Layer** - API docs, component docs
8. **Deployment Layer** - Feature flags, monitoring

### Parallel Work Opportunities

- **Phase 0 (Bug Fix)**: Frontend scope fix can proceed independently (1 day)
- **Phases 1-3 (Backend)**: Database, repository, service work sequentially
- **Phase 4 (API)**: Can start design in parallel with Phase 3
- **Phase 5 (UI Components)**: Tag input and badge can be built before full API integration
- **Phase 6 (Tag Filtering)**: Filter UI can use mock data initially
- **Testing**: Unit tests in parallel with implementation (test-driven approach)

### Critical Path

1. Phase 0 (Bug fix): 1 pt - blocks testing artifact edits
2. Phase 1 (DB schema): 3 pts - enables all backend work
3. Phase 2 (Repository): 4 pts - enables service layer
4. Phase 3 (Service): 6 pts - enables API endpoints
5. Phase 4 (API): 5 pts - enables frontend integration
6. Phase 5 (Tag Component): 7 pts - core UI feature
7. Phase 6 (Filter UI): 8 pts - enables full feature

---

## Phase 0: Bug Fix - Artifact Scope Validation

**Duration**: 1 day
**Dependencies**: None
**Assigned Subagent(s)**: frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| BUG-001 | Fix Scope Dropdown | Fix ParameterEditorModal scope field to use 'user'/'local' instead of 'default' | Form sends correct scope values, 422 error resolved | 1 pt | frontend-developer | None |

**Phase 0 Quality Gates:**
- [ ] ParameterEditorModal form submits without 422 error
- [ ] Scope dropdown shows only 'user' and 'local' options
- [ ] Manual testing confirms parameter save works

---

## Phase 1: Database Foundation - Tags Schema

**Duration**: 2 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DB-001 | Tags Table | Create tags table with id, name, slug, color, created_at | Table created, indexes on slug and created_at | 2 pts | data-layer-expert | None |
| DB-002 | Artifact-Tags Junction | Create artifact_tags junction table with FKs and unique constraint | Junction table with proper constraints, indexes on both FKs | 1 pt | data-layer-expert | DB-001 |
| DB-003 | Alembic Migration | Create migration for tags schema | Migration creates both tables, can be run and rolled back cleanly | 1 pt | data-layer-expert | DB-002 |

**Phase 1 Quality Gates:**
- [ ] Migration creates tags and artifact_tags tables
- [ ] Unique constraint on (artifact_id, tag_id) enforced
- [ ] Indexes created for query performance
- [ ] Rollback migration works cleanly

---

## Phase 2: Repository Layer - Tag Data Access

**Duration**: 2 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| REPO-001 | Tag CRUD Methods | Implement create, read, update, delete for tags | All CRUD operations work with proper error handling | 2 pts | python-backend-engineer | DB-003 |
| REPO-002 | Tag Search & List | Implement tag listing with cursor pagination and search by name | Tags can be filtered by substring, paginated results | 2 pts | python-backend-engineer | REPO-001 |
| REPO-003 | Artifact-Tag Association | Implement add/remove tags from artifacts, get tags for artifact | Associate/disassociate tags, retrieve artifact tag list | 2 pts | data-layer-expert | REPO-001 |
| REPO-004 | Tag Statistics | Implement tag count query (artifacts per tag) | Query returns accurate artifact count per tag | 1 pt | python-backend-engineer | REPO-003 |

**Phase 2 Quality Gates:**
- [ ] All CRUD operations working and tested
- [ ] Cursor pagination implemented for tag lists
- [ ] Search by tag name functional
- [ ] Tag statistics queries accurate
- [ ] Repository tests >80% coverage

---

## Phase 3: Service Layer - Tag Business Logic

**Duration**: 2 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: backend-architect, python-backend-engineer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SVC-001 | Tag DTOs | Create Pydantic schemas for tag request/response | TagResponse, TagCreateRequest, TagUpdateRequest defined | 1 pt | python-backend-engineer | REPO-004 |
| SVC-002 | Tag Service | Implement tag service with business logic | Service layer validates tags, handles duplicates, enforces consistency | 3 pts | backend-architect | SVC-001 |
| SVC-003 | Artifact-Tag Service | Implement artifact tag association service | Service validates artifact/tag existence, manages relationships | 2 pts | backend-architect | SVC-002 |
| SVC-004 | Error Handling | Implement error patterns for tag operations | Proper HTTPException statuses, consistent error responses | 1 pt | python-backend-engineer | SVC-003 |
| SVC-005 | Observability | Add OpenTelemetry spans for tag operations | Spans logged for create, delete, associate operations | 1 pt | backend-architect | SVC-004 |

**Phase 3 Quality Gates:**
- [ ] Business logic unit tests pass (>80% coverage)
- [ ] DTOs validate correctly
- [ ] ErrorResponse envelope used consistently
- [ ] OpenTelemetry instrumentation complete
- [ ] Service returns proper error codes

---

## Phase 4: API Layer - Tag Endpoints

**Duration**: 2 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-001 | Tag Router Setup | Create FastAPI router for tag endpoints | Router defined with proper tags and descriptions | 1 pt | python-backend-engineer | SVC-005 |
| API-002 | Tag CRUD Endpoints | Implement GET /tags, POST /tags, PUT /tags/{id}, DELETE /tags/{id} | All CRUD endpoints working with proper status codes | 2 pts | python-backend-engineer | API-001 |
| API-003 | Artifact-Tag Endpoints | Implement GET /artifacts/{id}/tags, POST /artifacts/{id}/tags/{tag_id}, DELETE /artifacts/{id}/tags/{tag_id} | All association endpoints working | 2 pts | python-backend-engineer | API-002 |
| API-004 | Response Formatting | Standardize tag response formats with pagination | Consistent envelope, cursor pagination for lists | 1 pt | python-backend-engineer | API-003 |
| API-005 | OpenAPI Documentation | Document all tag endpoints in Swagger | Complete endpoint documentation with examples | 1 pt | python-backend-engineer | API-004 |

**Phase 4 Quality Gates:**
- [ ] All endpoints return correct status codes
- [ ] OpenAPI documentation complete and accurate
- [ ] Request/response validation working
- [ ] Error responses consistent
- [ ] Integration tests pass (>80% coverage)

---

## Phase 5: Frontend UI - Tag Input Component & Integration

**Duration**: 3 days
**Dependencies**: Phase 4 complete (can start component design in Phase 3)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| UI-001 | Tag Input Design | Design tag input component spec (shadcn.io style, not shadcn/ui) | Design shows: search, enter to add, 'x' to remove, keyboard nav | 2 pts | ui-engineer-enhanced | API-005 |
| UI-002 | Tag Input Component | Implement TagInput component with all features | Component supports: typing, Enter, Backspace, arrow keys, copy-paste CSV | 3 pts | ui-engineer-enhanced | UI-001 |
| UI-003 | Tag Badge Component | Update Badge component for tag display with colors | Badge shows colored, rounded tag display with optional 'x' in edit mode | 1 pt | ui-engineer-enhanced | UI-002 |
| UI-004 | Parameter Editor Integration | Integrate TagInput into ParameterEditorModal | Tags field in modal uses TagInput component, saves to API | 2 pts | frontend-developer | UI-003 |
| UI-005 | Tag Display in Detail View | Show tags on artifact detail view (read-only) | Tags display as badges, clickable to filter | 1 pt | frontend-developer | UI-004 |
| UI-006 | Accessibility | Implement WCAG 2.1 AA features | Keyboard navigation, ARIA labels, focus management | 1 pt | ui-engineer-enhanced | UI-005 |

**Phase 5 Quality Gates:**
- [ ] TagInput component renders correctly
- [ ] Tag CRUD operations work (add, remove, search)
- [ ] Copy-paste CSV support working
- [ ] Keyboard navigation functional (arrows, Backspace, Enter)
- [ ] Component tests >80% coverage
- [ ] Accessibility requirements met (WCAG 2.1 AA)

---

## Phase 6: Frontend UI - Tag Filtering & Dashboard

**Duration**: 3 days
**Dependencies**: Phase 5 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| FILTER-001 | Tag Filter Popover | Create popover showing all tags with artifact counts | Popover shows tags, counts, search input, multi-select | 2 pts | ui-engineer-enhanced | UI-006 |
| FILTER-002 | Tag Filter Button | Add tag filter button to artifact views (collections, search) | Button displays selected tag count, opens popover | 2 pts | ui-engineer-enhanced | FILTER-001 |
| FILTER-003 | Filter Integration | Integrate tag filtering with artifact list queries | Selected tags filter artifact results, URL params updated | 2 pts | frontend-developer | FILTER-002 |
| FILTER-004 | Dashboard Tags Widget | Add tag metrics to analytics dashboard | Dashboard shows: tag distribution, top tags, artifact coverage | 2 pts | frontend-developer | FILTER-003 |

**Phase 6 Quality Gates:**
- [ ] Tag filter popover renders correctly
- [ ] Multi-select filtering works
- [ ] Artifact lists update based on selected tags
- [ ] Dashboard metrics display accurately
- [ ] Component tests >80% coverage
- [ ] All interactions tested

---

## Phase 7: Testing Layer

**Duration**: 2 days
**Dependencies**: Phases 5-6 complete
**Assigned Subagent(s)**: python-backend-engineer, frontend-developer, web-accessibility-checker

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Backend Unit Tests | Unit tests for tag service, repository, schemas | >80% coverage, all edge cases tested | 2 pts | python-backend-engineer | FILTER-004 |
| TEST-002 | API Integration Tests | Test all tag endpoints with various scenarios | All CRUD, association, and filtering tested | 2 pts | python-backend-engineer | TEST-001 |
| TEST-003 | Component Tests | Test TagInput, Badge, Filter components | User interactions, state changes, edge cases | 2 pts | frontend-developer | TEST-001 |
| TEST-004 | E2E Tests | End-to-end tag workflow testing | Create tag → add to artifact → filter by tag flow | 2 pts | frontend-developer | TEST-003 |
| TEST-005 | Accessibility Tests | WCAG 2.1 AA compliance automated testing | All accessibility requirements verified | 1 pt | web-accessibility-checker | TEST-004 |

**Phase 7 Quality Gates:**
- [ ] Code coverage >80% (backend and frontend)
- [ ] All tests passing in CI/CD
- [ ] E2E tests cover critical workflows
- [ ] Accessibility compliance validated
- [ ] Performance benchmarks met

---

## Phase 8: Documentation Layer

**Duration**: 1 day
**Dependencies**: Phase 7 complete
**Assigned Subagent(s)**: api-documenter, documentation-writer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| DOC-001 | API Documentation | Document all tag endpoints with examples | Complete endpoint docs, request/response examples | 1 pt | api-documenter | TEST-005 |
| DOC-002 | Component Documentation | Document TagInput, Badge, Filter components | Usage examples, props, accessibility features | 1 pt | documentation-writer | TEST-005 |
| DOC-003 | User Guide | Create tag usage guide for end users | How to: create, search, filter by tags | 1 pt | documentation-writer | TEST-005 |
| DOC-004 | Developer Guide | Create developer docs for tag system | Architecture, adding tags to new entities | 1 pt | documentation-writer | TEST-005 |

**Phase 8 Quality Gates:**
- [ ] API documentation complete and accurate
- [ ] Component documentation complete
- [ ] User guides clear and comprehensive
- [ ] Developer docs enable extension

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Tag name collision/duplicate | Medium | High | Enforce unique constraint on tag name in DB, use case-insensitive comparison |
| Performance on artifact lists with many tags | Medium | Medium | Index artifact_tags table, implement cursor pagination, cache tag counts |
| CSV copy-paste edge cases | Low | Medium | Extensive testing of edge cases (quotes, commas, newlines), clear error messages |
| Scope validation in API (existing bug) | High | High | Fix in Phase 0 before tag implementation, validate all scope values |
| Keyboard accessibility complexity | Low | Medium | Follow WAI-ARIA patterns, extensive keyboard testing, third-party validation |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Scope creep (tags on all entities) | High | High | Phase 1 focuses on artifacts only, document future phases separately |
| Frontend complexity (component interactions) | Medium | Medium | Early design review, component testing before integration |
| Database migration issues | High | Medium | Test migration rollback, staging environment deployment first |
| API design changes during implementation | Medium | Medium | Finalize API spec before Phase 4 starts, use OpenAPI-first approach |

---

## Resource Requirements

### Team Composition
- **Backend Developer**: 1.5 FTE (Phases 1-4), 0.5 FTE (Phase 7)
- **Frontend Developer**: 1.5 FTE (Phases 5-6), 0.5 FTE (Phase 7)
- **UI Engineer**: 1 FTE (Phases 5-6)
- **QA/Testing**: 0.5 FTE (Phase 7)
- **DevOps**: Part-time (Phase 8)

### Skill Requirements
- Python, FastAPI, SQLAlchemy, Alembic
- TypeScript, React, React Query, Tailwind CSS
- PostgreSQL, Git, CI/CD
- WCAG 2.1 AA accessibility standards
- Component design patterns (shadcn.io style)

---

## Success Metrics

### Delivery Metrics
- On-time delivery (±5%)
- Code coverage >80% (backend and frontend)
- Zero critical bugs in first week
- All tests passing in CI/CD

### Technical Metrics
- API endpoints fully documented
- Tag query performance <50ms (with indexes)
- Component tests >80% coverage
- 100% WCAG 2.1 AA compliance

### Business Metrics
- Tag system adoption rate (% of artifacts tagged)
- Filter usage metrics (% of searches using tag filters)
- User satisfaction with tag search/filtering

---

## Communication Plan

- **Daily**: 15-min standups for blockers
- **Phase gates**: Formal review at end of each phase
- **Weekly**: Status update on timeline
- **As-needed**: Architecture/design reviews

---

## Orchestration Quick Reference

### Batch 1: Bug Fix (Parallel - Day 1)
```
Task("frontend-developer", "BUG-001: Fix scope dropdown in ParameterEditorModal.
     File: skillmeat/web/components/ParameterEditorModal.tsx
     Change: Update scope field to use 'user' and 'local' options only (not 'default')
     Reason: API schema expects 'user' or 'local', currently sending 'default' causes 422 error")
```

### Batch 2: Database Schema (Phases 1 - Sequential, 2 days)
```
Task("data-layer-expert", "DB-001-DB-002: Design and create tags schema.
     Create tasks table (id, name, slug, color, created_at, updated_at)
     Create artifact_tags junction table (artifact_id, tag_id, created_at)
     Add unique constraint on (artifact_id, tag_id)
     Files to create: skillmeat/storage/models/tag.py
     Files to update: skillmeat/storage/migrations/")

Task("data-layer-expert", "DB-003: Create Alembic migration for tags schema.
     Files: skillmeat/storage/migrations/versions/
     Ensure migration can be rolled back cleanly")
```

### Batch 3: Repository Layer (Phase 2 - 2 days)
```
Task("python-backend-engineer", "REPO-001-REPO-004: Implement tag repository methods.
     Files: skillmeat/core/storage/repositories/tag_repository.py
     Methods needed:
       - create_tag(name, slug, color) -> Tag
       - get_tag(id) -> Tag
       - list_tags(search, limit, after_cursor) -> List[Tag]
       - update_tag(id, name, color) -> Tag
       - delete_tag(id) -> None
       - add_tag_to_artifact(artifact_id, tag_id) -> None
       - remove_tag_from_artifact(artifact_id, tag_id) -> None
       - get_artifact_tags(artifact_id) -> List[Tag]
       - get_tag_artifact_count(tag_id) -> int")
```

### Batch 4: Service Layer (Phase 3 - 2 days)
```
Task("backend-architect", "SVC-001-SVC-005: Implement tag service with business logic.
     Files: skillmeat/core/services/tag_service.py
     Implement:
       - validate_tag_uniqueness()
       - Tag lifecycle (create, read, update, delete)
       - Artifact association logic
       - Error handling with proper HTTP status codes
     Add OpenTelemetry spans for all operations")
```

### Batch 5: API Layer (Phase 4 - 2 days)
```
Task("python-backend-engineer", "API-001-API-005: Create tag API endpoints.
     Files: skillmeat/api/routers/tags.py
     Endpoints to implement:
       GET /api/v1/tags (list, search, paginate)
       POST /api/v1/tags (create)
       PUT /api/v1/tags/{id} (update)
       DELETE /api/v1/tags/{id} (delete)
       GET /api/v1/artifacts/{id}/tags (get artifact tags)
       POST /api/v1/artifacts/{id}/tags/{tag_id} (add tag)
       DELETE /api/v1/artifacts/{id}/tags/{tag_id} (remove tag)
     Add OpenAPI documentation for all endpoints")
```

### Batch 6: Frontend Components (Phase 5 - 3 days, Parallel Streams)
```
Task("ui-engineer-enhanced", "UI-001-UI-003: Design and implement TagInput and Badge components.
     Files:
       - skillmeat/web/components/ui/tag-input.tsx (new)
       - skillmeat/web/components/ui/badge.tsx (update existing)
     Features:
       - Type to search existing tags or add new
       - Press Enter to add, 'x' to remove
       - Keyboard navigation (arrow keys, Backspace/Delete)
       - Copy-paste CSV support (split by commas)
       - Color-coded badges with rounded corners
     Accessibility: Full keyboard support, ARIA labels")

Task("frontend-developer", "UI-004-UI-005: Integrate tags into artifact forms and views.
     Files:
       - skillmeat/web/components/ParameterEditorModal.tsx (update)
       - skillmeat/web/components/ArtifactDetail.tsx (update)
     Changes:
       - Add TagInput to ParameterEditorModal
       - Display tags in artifact detail view
       - Wire up API calls for tag CRUD operations")
```

### Batch 7: Tag Filtering UI (Phase 6 - 3 days)
```
Task("ui-engineer-enhanced", "FILTER-001-FILTER-002: Create tag filter UI components.
     Files: skillmeat/web/components/TagFilterPopover.tsx (new)
     Features:
       - Popover showing all tags with artifact counts
       - Search box to filter tags
       - Multi-select with visual indicator
       - Shows selected count in filter button")

Task("frontend-developer", "FILTER-003-FILTER-004: Integrate tag filtering and dashboard.
     Files:
       - skillmeat/web/components/ArtifactList.tsx (update)
       - skillmeat/web/pages/index.tsx (dashboard, update)
     Changes:
       - Filter artifact list by selected tags
       - Update URL params for tag filters
       - Add tag metrics widget to dashboard
       - Display tag distribution, top tags")
```

### Batch 8: Testing (Phase 7 - 2 days)
```
Task("python-backend-engineer", "TEST-001-TEST-002: Backend and API integration tests.
     Files:
       - tests/unit/services/test_tag_service.py
       - tests/integration/routers/test_tags_router.py
     Coverage requirements: >80%
     Test scenarios: CRUD operations, associations, error cases")

Task("frontend-developer", "TEST-003-TEST-004: Frontend component and E2E tests.
     Files:
       - tests/components/TagInput.test.tsx
       - tests/e2e/tags.spec.ts
     Test: Component rendering, user interactions, workflows")
```

### Batch 9: Documentation (Phase 8 - 1 day)
```
Task("api-documenter", "DOC-001: Generate API documentation.
     Files: docs/api/tags.md
     Include: All endpoints, request/response examples")

Task("documentation-writer", "DOC-002-DOC-004: Create user and developer guides.
     Files:
       - docs/components/TagInput.md
       - docs/guides/tags-user-guide.md
       - docs/guides/tags-architecture.md")
```

---

## Implementation Notes

### Phase 0 - Bug Fix Context
The scope validation error occurs because the ParameterEditorModal sends 'default' as the scope value, but the artifact schema expects 'user' or 'local'. This is independent of the tags feature and should be fixed first to unblock artifact editing tests.

### Tag Design Decisions
- **Slug field**: Tags use URL-friendly slugs for better API usability and future dashboard analytics
- **Color field**: Pre-assigned colors enable badge visual distinction (can be randomized or user-selected)
- **Global scope**: Tags are global across all artifacts, not per-collection or per-project
- **Many-to-many**: Junction table allows efficient queries (e.g., "all tags with X artifacts")

### Frontend Component Notes
- **NOT shadcn/ui**: The reference is to shadcn.io's registry (https://www.shadcn.io/registry/tags.json), not the shadcn/ui component library
- **Keyboard accessibility**: Must support full keyboard navigation for screen reader users
- **Badge reusability**: Update existing Badge component with color variants for tag display

### Future Phases (Not in Scope)
- Phase 9: Extend tags to all primary entities (commands, agents, MCP servers)
- Phase 10: Tag-based analytics and insights dashboard
- Phase 11: Tag templates and quick-assign workflows

---

**Progress Tracking:**

See `.claude/progress/tags-refactor-v1/` directory for phase-by-phase progress files

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2025-12-18
