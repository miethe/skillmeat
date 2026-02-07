---
title: 'Implementation Plan: Entity Lifecycle Management'
description: Detailed phased implementation for full entity lifecycle management in
  SkillMeat web app
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- web-ui
- lifecycle
created: 2025-11-24
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
---

# Implementation Plan: Entity Lifecycle Management

**Plan ID**: `IMPL-2025-11-24-ENTITY-LIFECYCLE`
**Date**: 2025-11-24
**Author**: Claude Code (lead-architect)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md`
- **Version Tracking PRD**: `/docs/project_plans/artifact-version-tracking-sync-prd.md`

**Complexity**: Large
**Total Estimated Effort**: 158 story points
**Target Timeline**: 7 phases

## Executive Summary

This implementation plan delivers full entity lifecycle management for the SkillMeat web application. The approach follows a bottom-up architecture: first extending backend APIs, then building shared components, and finally assembling pages that reuse these components across collection and project contexts. Key milestones include project CRUD APIs, shared EntityLifecycleManager components, a dedicated `/manage` page, and bidirectional sync workflows.

## Implementation Strategy

### Architecture Sequence

Following the layered approach appropriate for this feature:

1. **Backend API Layer** - CRUD endpoints for projects and artifacts
2. **Frontend Shared Components** - Reusable EntityLifecycleManager, DiffViewer, EntityForm
3. **Entity Management Pages** - Collection-level `/manage` route with tabs
4. **Project Management** - Project CRUD from web UI
5. **Project-Level Entities** - `/projects/[id]/manage` with shared components
6. **Merge Workflow** - Visual diff and merge UI integration
7. **Testing & Quality** - Unit, integration, E2E tests + accessibility

### Parallel Work Opportunities

- **Backend API (Phase 1)** and **Component Design** (start of Phase 2) can begin in parallel
- **Entity tabs** (Skills, Agents, Commands, Hooks, MCP) can be implemented in parallel during Phase 3
- **Testing** can begin incrementally as each phase completes

### Critical Path

1. Backend API → 2. Shared Components → 3. Entity Management Page → 6. Merge Workflow

Project management (Phase 4) and project-level entities (Phase 5) can proceed in parallel with Phase 6.

---

## Phase Breakdown

### Phase 1: Backend API Extensions

**Duration**: 3-5 days
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| API-001 | Project CRUD Endpoints | Add POST/PUT/DELETE for /api/v1/projects | All CRUD operations work, OpenAPI updated | 5 pts | python-backend-engineer | None |
| API-002 | Project Validation | Add validation for project name, path | Invalid data returns 400 with details | 2 pts | python-backend-engineer | API-001 |
| API-003 | Artifact Creation Endpoint | Add POST /api/v1/artifacts for new artifacts | Can add from GitHub URL or local path | 5 pts | python-backend-engineer | None |
| API-004 | Artifact Update Endpoint | Add PUT /api/v1/artifacts/{id} for metadata | Metadata updates persist correctly | 3 pts | python-backend-engineer | API-003 |
| API-005 | Diff Endpoint | Add GET /api/v1/artifacts/{id}/diff | Returns file-level diff between versions | 5 pts | backend-architect | None |
| API-006 | Pull Endpoint | Add POST /api/v1/artifacts/{id}/pull | Project changes sync to collection | 5 pts | backend-architect | API-005 |
| API-007 | SDK Regeneration | Regenerate TypeScript SDK from OpenAPI | SDK reflects all new endpoints | 2 pts | python-backend-engineer | API-001 thru API-006 |

**Phase 1 Quality Gates:**
- [ ] All CRUD endpoints return correct responses
- [ ] OpenAPI documentation complete for new endpoints
- [ ] Validation errors return proper ErrorResponse envelope
- [ ] SDK regenerated and compiles without errors
- [ ] Unit tests for all new endpoints (>80% coverage)

---

### Phase 2: Shared Components Foundation

**Duration**: 5-7 days
**Dependencies**: Phase 1 complete (SDK available)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| COMP-001 | EntityLifecycleManager Context | Create React context for entity state | Context provides entity data and actions | 5 pts | frontend-developer | API-007 |
| COMP-002 | Entity Types Registry | Create type registry with schemas per entity | Each type has form schema, validation | 3 pts | frontend-developer | COMP-001 |
| COMP-003 | DiffViewer Component | Build side-by-side diff visualization | Shows additions, deletions with syntax highlighting | 8 pts | ui-engineer-enhanced | API-005 |
| COMP-004 | EntityForm Component | Build add/edit form with type-specific fields | Form validates and submits for all types | 8 pts | ui-engineer-enhanced | COMP-002 |
| COMP-005 | EntityList Component | Build grid/list view with selection | Supports filter, sort, multi-select | 5 pts | frontend-developer | COMP-001 |
| COMP-006 | EntityCard Component | Build entity card for grid view | Shows type, status, version, actions | 3 pts | ui-engineer-enhanced | COMP-001 |
| COMP-007 | EntityRow Component | Build entity row for list view | Same info as card in table format | 3 pts | ui-engineer-enhanced | COMP-005 |
| COMP-008 | EntityActions Component | Build action menu (edit, delete, sync, deploy) | Actions work, confirmation for destructive | 3 pts | frontend-developer | COMP-001 |

**Phase 2 Quality Gates:**
- [ ] Components render in Storybook
- [ ] TypeScript strict mode passes
- [ ] Components handle loading, error, empty states
- [ ] Keyboard navigation works
- [ ] Component tests achieve >80% coverage

---

### Phase 3: Entity Management Page

**Duration**: 5-7 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PAGE-001 | Create /manage Route | Set up Next.js app router page | Route accessible, basic layout | 3 pts | frontend-developer | COMP-008 |
| PAGE-002 | Entity Tabs Component | Build tabs for entity types | Tabs switch content, URL updates | 3 pts | ui-engineer-enhanced | PAGE-001 |
| PAGE-003 | Skills Tab Implementation | Full CRUD for skills | Add, edit, delete, view skills | 8 pts | ui-engineer-enhanced | PAGE-002 |
| PAGE-004 | Agents Tab Implementation | Full CRUD for agents | Add, edit, delete, view agents | 5 pts | frontend-developer | PAGE-002 |
| PAGE-005 | Commands Tab Implementation | Full CRUD for commands | Add, edit, delete, view commands | 5 pts | frontend-developer | PAGE-002 |
| PAGE-006 | Hooks Tab Implementation | Full CRUD for hooks | Add, edit, delete, view hooks | 3 pts | ui-engineer-enhanced | PAGE-002 |
| PAGE-007 | MCP Tab Integration | Integrate existing MCP components | MCP management in tab interface | 3 pts | frontend-developer | PAGE-002 |
| PAGE-008 | Entity Detail Panel | Side panel with tabs (Overview, Sync, History) | Panel shows entity details and actions | 8 pts | ui-engineer-enhanced | PAGE-003 |
| PAGE-009 | Filter and Search | Add filter bar to entity management | Type, status, tag filters work | 5 pts | frontend-developer | PAGE-003 |

**Phase 3 Quality Gates:**
- [ ] All 5 entity tabs accessible and functional
- [ ] CRUD operations work end-to-end
- [ ] Filters correctly narrow results
- [ ] Entity detail panel shows all info
- [ ] Responsive layout works on tablet+
- [ ] Page load time < 1s

---

### Phase 4: Project Management

**Duration**: 3-5 days
**Dependencies**: Phase 1 complete (can run parallel with Phase 3)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PROJ-001 | Project Creation Modal | Build modal form for new project | Form validates, creates project | 5 pts | ui-engineer-enhanced | API-001 |
| PROJ-002 | Projects Page Enhancement | Add "New Project" button to /projects | Button opens modal, list updates | 2 pts | frontend-developer | PROJ-001 |
| PROJ-003 | Project Edit Functionality | Add edit button with inline/modal edit | Metadata updates save correctly | 3 pts | frontend-developer | API-001 |
| PROJ-004 | Project Delete Workflow | Add delete with multi-step confirmation | Delete completes with cleanup options | 3 pts | ui-engineer-enhanced | API-001 |
| PROJ-005 | Project Settings Page | Create /projects/[id]/settings route | Settings page shows project config | 5 pts | frontend-developer | PROJ-003 |
| PROJ-006 | Project Card Enhancement | Update project cards with action menu | Edit, delete, settings accessible | 2 pts | ui-engineer-enhanced | PROJ-003, PROJ-004 |

**Phase 4 Quality Gates:**
- [ ] Can create project from web UI
- [ ] Can edit project metadata
- [ ] Can delete project with confirmation
- [ ] Project settings page accessible
- [ ] All actions have proper error handling

---

### Phase 5: Project-Level Entity Management

**Duration**: 4-6 days
**Dependencies**: Phase 3 and Phase 4 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| PLEVEL-001 | Create /projects/[id]/manage Route | Set up project-level entity page | Route accessible with project context | 3 pts | frontend-developer | PAGE-008 |
| PLEVEL-002 | EntityLifecycleManager Project Mode | Add project context to manager | Components know collection vs project | 3 pts | frontend-developer | PLEVEL-001 |
| PLEVEL-003 | Project Entity Tabs | Reuse tabs for project-scoped entities | Shows only deployed entities | 3 pts | ui-engineer-enhanced | PLEVEL-002 |
| PLEVEL-004 | Deploy from Collection Workflow | Add "Add from Collection" button | Can deploy collection entity to project | 5 pts | ui-engineer-enhanced | PLEVEL-003 |
| PLEVEL-005 | Pull to Collection Workflow | Add "Pull to Collection" button | Modified entities sync back | 5 pts | frontend-developer | PLEVEL-003, API-006 |
| PLEVEL-006 | Entity Status in Project | Show sync status badges | Modified, synced, outdated visible | 3 pts | ui-engineer-enhanced | PLEVEL-003 |
| PLEVEL-007 | Project Entity Navigation | Add manage link to project detail | Easy navigation to entity management | 2 pts | frontend-developer | PLEVEL-001 |

**Phase 5 Quality Gates:**
- [ ] Project entity management matches collection level
- [ ] Deploy from collection works
- [ ] Pull to collection works
- [ ] Status badges accurate
- [ ] Components reused (>80% code sharing)

---

### Phase 6: Visual Merge Workflow

**Duration**: 5-7 days
**Dependencies**: Phase 2 (DiffViewer) and Phase 5 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer, backend-architect

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| MERGE-001 | Sync Tab Enhancement | Add visual diff to sync tab | DiffViewer shows before/after | 5 pts | ui-engineer-enhanced | PLEVEL-006 |
| MERGE-002 | MergeWorkflow Component | Build step-by-step merge UI | Steps: Preview → Resolve → Apply | 8 pts | frontend-developer | MERGE-001, COMP-003 |
| MERGE-003 | Conflict Detection UI | Integrate conflict detection | Conflicts highlighted in diff | 5 pts | ui-engineer-enhanced | MERGE-002 |
| MERGE-004 | ConflictResolver Integration | Reuse existing conflict resolver | Per-file resolution works | 3 pts | frontend-developer | MERGE-003 |
| MERGE-005 | Merge Progress Indicator | Show progress during merge | SSE-based progress updates | 3 pts | frontend-developer | MERGE-002 |
| MERGE-006 | Version Rollback UI | Add rollback button with confirmation | Can revert to previous version | 5 pts | ui-engineer-enhanced | PAGE-008 |
| MERGE-007 | Merge History in Detail Panel | Show recent merges in history tab | Merge commits visible | 3 pts | frontend-developer | MERGE-006 |

**Phase 6 Quality Gates:**
- [ ] Visual diff shows accurate changes
- [ ] Merge workflow completes end-to-end
- [ ] Conflicts detected and resolved
- [ ] Rollback restores previous version
- [ ] Progress indicator works with SSE

---

### Phase 7: Testing & Polish

**Duration**: 5-7 days
**Dependencies**: All previous phases complete
**Assigned Subagent(s)**: all developers, senior-code-reviewer

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Shared Component Unit Tests | Unit tests for all shared components | >80% coverage | 8 pts | frontend-developer | MERGE-007 |
| TEST-002 | API Integration Tests | Tests for all new API endpoints | All endpoints tested | 5 pts | python-backend-engineer | MERGE-007 |
| TEST-003 | CRUD Flow Tests | Integration tests for CRUD operations | All CRUD flows pass | 5 pts | frontend-developer | TEST-001 |
| TEST-004 | E2E Critical Paths | Playwright tests for key journeys | Create project, add entity, merge | 8 pts | frontend-developer | TEST-003 |
| TEST-005 | Accessibility Audit | axe-core + manual testing | WCAG 2.1 AA compliance | 5 pts | ui-engineer-enhanced | TEST-001 |
| TEST-006 | Performance Optimization | Audit and optimize render performance | Page load < 1s, smooth interactions | 5 pts | react-performance-optimizer | TEST-004 |
| TEST-007 | Code Review | Senior review of all new code | Code quality approved | 5 pts | senior-code-reviewer | TEST-006 |
| TEST-008 | Bug Fixes | Fix issues found during testing | All P0/P1 bugs resolved | 8 pts | all developers | TEST-007 |
| TEST-009 | Documentation | Component docs, user guide | Docs complete and accurate | 5 pts | documentation-writer | TEST-008 |

**Phase 7 Quality Gates:**
- [ ] Unit test coverage >80%
- [ ] All integration tests pass
- [ ] E2E tests pass in CI
- [ ] Accessibility audit passes
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Code review approved

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Component prop drilling complexity | High | Medium | Use React Context, composition patterns |
| Diff computation slow for large files | Medium | Low | Virtualized rendering, web worker |
| SDK regeneration breaks existing code | Medium | Low | Backward compatible changes, versioning |
| Merge workflow complexity | High | Medium | Step-by-step UI, clear visual feedback |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|-------------------|
| Phase dependencies create bottlenecks | Medium | Medium | Parallel work where possible |
| Feature scope creep | Medium | High | Strict MVP scope, defer enhancements |
| Testing uncovers major issues | High | Low | Test incrementally, fix as we go |

---

## Resource Requirements

### Team Composition (AI Agents)

- **python-backend-engineer**: Phases 1, 7 (API, integration tests)
- **backend-architect**: Phases 1, 6 (complex API logic, merge workflow)
- **ui-engineer-enhanced**: Phases 2, 3, 4, 5, 6, 7 (UI components, pages)
- **frontend-developer**: Phases 2, 3, 4, 5, 6, 7 (hooks, integration)
- **senior-code-reviewer**: Phase 7 (code quality)
- **documentation-writer**: Phase 7 (docs)
- **react-performance-optimizer**: Phase 7 (performance)

### Skill Requirements

- TypeScript/React 19, Next.js 15 App Router
- FastAPI, Pydantic, OpenAPI
- TanStack React Query, Radix UI
- Testing: Jest, Playwright, axe-core

---

## Success Metrics

### Delivery Metrics

- All 7 phases completed
- Code coverage >80%
- Performance benchmarks met (page load < 1s)
- Zero P0/P1 bugs in first week

### Feature Metrics

- Project CRUD: 4/4 operations available
- Entity CRUD: 5/5 entity types with full lifecycle
- Component reuse: >80% between collection/project views
- User actions for merge: 2-3 (down from 5+)

### Quality Metrics

- WCAG 2.1 AA compliance: 100%
- API documentation: 100%
- Test pass rate: 100%

---

## Communication Plan

- **Phase kickoff**: Agent delegation with task assignments
- **Phase completion**: Quality gate review
- **Blockers**: Immediate escalation with context
- **Progress**: Task completion tracked in progress file

---

## Post-Implementation

- Monitor page performance via analytics
- Track CRUD operation success rates
- Collect user feedback on merge workflow
- Plan Phase 2 enhancements (bulk ops, templates)
- Address technical debt from rapid implementation

---

## Summary Table: Phases and Effort

| Phase | Name | Effort (pts) | Assigned Agents |
|-------|------|-------------|-----------------|
| 1 | Backend API Extensions | 27 pts | python-backend-engineer, backend-architect |
| 2 | Shared Components Foundation | 38 pts | ui-engineer-enhanced, frontend-developer |
| 3 | Entity Management Page | 43 pts | ui-engineer-enhanced, frontend-developer |
| 4 | Project Management | 20 pts | ui-engineer-enhanced, frontend-developer |
| 5 | Project-Level Entity Management | 24 pts | ui-engineer-enhanced, frontend-developer |
| 6 | Visual Merge Workflow | 32 pts | ui-engineer-enhanced, frontend-developer, backend-architect |
| 7 | Testing & Polish | 54 pts | all developers |
| **Total** | | **238 pts** | |

---

**Progress Tracking:**

See `.claude/progress/entity-lifecycle-management-v1/all-phases-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2025-11-24
