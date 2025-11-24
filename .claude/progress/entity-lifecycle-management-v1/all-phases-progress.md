# All-Phases Progress: Entity Lifecycle Management

**Status**: NOT STARTED
**Last Updated**: 2025-11-24
**Completion**: 0% (0 of 238 story points)

**PRD**: `/docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md`
**Implementation Plan**: `/docs/project_plans/implementation_plans/features/entity-lifecycle-management-v1.md`

**Priority**: HIGH
**Total Effort**: 238 story points

---

## Phase Overview

| Phase | Title | Effort | Status | Completion |
|-------|-------|--------|--------|-----------|
| 1 | Backend API Extensions | 27 pts | NOT STARTED | 0% |
| 2 | Shared Components Foundation | 38 pts | NOT STARTED | 0% |
| 3 | Entity Management Page | 43 pts | NOT STARTED | 0% |
| 4 | Project Management | 20 pts | NOT STARTED | 0% |
| 5 | Project-Level Entity Management | 24 pts | NOT STARTED | 0% |
| 6 | Visual Merge Workflow | 32 pts | NOT STARTED | 0% |
| 7 | Testing & Polish | 54 pts | NOT STARTED | 0% |

---

## Phase 1: Backend API Extensions

**Status**: NOT STARTED
**Duration**: 3-5 days
**Effort**: 27 story points
**Completion**: 0% (0 of 7 tasks)
**Dependencies**: None

### Completion Checklist

- [ ] **API-001**: Project CRUD Endpoints (5 pts)
      **Description**: Add POST/PUT/DELETE for /api/v1/projects
      **Assigned Subagent(s)**: python-backend-engineer
      **Acceptance Criteria**:
      - [ ] POST /projects creates new project with validation
      - [ ] PUT /projects/{id} updates project metadata
      - [ ] DELETE /projects/{id} removes project
      - [ ] OpenAPI spec updated

- [ ] **API-002**: Project Validation (2 pts)
      **Description**: Add validation for project name, path
      **Assigned Subagent(s)**: python-backend-engineer
      **Acceptance Criteria**:
      - [ ] Invalid project name returns 400
      - [ ] Invalid path returns 400 with details
      - [ ] Duplicate detection works

- [ ] **API-003**: Artifact Creation Endpoint (5 pts)
      **Description**: Add POST /api/v1/artifacts for new artifacts
      **Assigned Subagent(s)**: python-backend-engineer
      **Acceptance Criteria**:
      - [ ] Can add artifact from GitHub URL
      - [ ] Can add artifact from local path
      - [ ] Validates artifact structure

- [ ] **API-004**: Artifact Update Endpoint (3 pts)
      **Description**: Add PUT /api/v1/artifacts/{id} for metadata
      **Assigned Subagent(s)**: python-backend-engineer
      **Acceptance Criteria**:
      - [ ] Can update artifact tags
      - [ ] Can update artifact description
      - [ ] Changes persist to manifest

- [ ] **API-005**: Diff Endpoint (5 pts)
      **Description**: Add GET /api/v1/artifacts/{id}/diff
      **Assigned Subagent(s)**: backend-architect
      **Acceptance Criteria**:
      - [ ] Returns file-level diff between versions
      - [ ] Supports collection vs project comparison
      - [ ] Returns in standard diff format

- [ ] **API-006**: Pull Endpoint (5 pts)
      **Description**: Add POST /api/v1/artifacts/{id}/pull
      **Assigned Subagent(s)**: backend-architect
      **Acceptance Criteria**:
      - [ ] Project changes sync to collection
      - [ ] Handles merge conflicts
      - [ ] Updates version tracking

- [ ] **API-007**: SDK Regeneration (2 pts)
      **Description**: Regenerate TypeScript SDK from OpenAPI
      **Assigned Subagent(s)**: python-backend-engineer
      **Acceptance Criteria**:
      - [ ] SDK reflects all new endpoints
      - [ ] SDK compiles without errors
      - [ ] Types are correct

### Success Criteria

- [ ] All CRUD endpoints return correct responses
- [ ] OpenAPI documentation complete for new endpoints
- [ ] Validation errors return proper ErrorResponse envelope
- [ ] SDK regenerated and compiles without errors
- [ ] Unit tests for all new endpoints (>80% coverage)

### Key Files

- `skillmeat/api/routers/projects.py` - Project CRUD endpoints
- `skillmeat/api/routers/artifacts.py` - Artifact endpoints
- `skillmeat/api/schemas/` - Pydantic schemas
- `skillmeat/web/sdk/` - Regenerated SDK

---

## Phase 2: Shared Components Foundation

**Status**: NOT STARTED
**Duration**: 5-7 days
**Effort**: 38 story points
**Completion**: 0% (0 of 8 tasks)
**Dependencies**: Phase 1 complete (SDK available)

### Completion Checklist

- [ ] **COMP-001**: EntityLifecycleManager Context (5 pts)
      **Description**: Create React context for entity state
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Context provides entity data
      - [ ] Context provides CRUD actions
      - [ ] Handles loading/error states

- [ ] **COMP-002**: Entity Types Registry (3 pts)
      **Description**: Create type registry with schemas per entity
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Each type has form schema
      - [ ] Validation rules per type
      - [ ] Easy to extend for new types

- [ ] **COMP-003**: DiffViewer Component (8 pts)
      **Description**: Build side-by-side diff visualization
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Shows additions (green)
      - [ ] Shows deletions (red)
      - [ ] Syntax highlighting for code
      - [ ] Scrolls in sync

- [ ] **COMP-004**: EntityForm Component (8 pts)
      **Description**: Build add/edit form with type-specific fields
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Works for all entity types
      - [ ] Validates input
      - [ ] Handles GitHub/local source

- [ ] **COMP-005**: EntityList Component (5 pts)
      **Description**: Build grid/list view with selection
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Grid and list view modes
      - [ ] Multi-select support
      - [ ] Sort and filter

- [ ] **COMP-006**: EntityCard Component (3 pts)
      **Description**: Build entity card for grid view
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Shows type, status, version
      - [ ] Shows tags
      - [ ] Click to select/open

- [ ] **COMP-007**: EntityRow Component (3 pts)
      **Description**: Build entity row for list view
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Same info as card
      - [ ] Table format
      - [ ] Sortable columns

- [ ] **COMP-008**: EntityActions Component (3 pts)
      **Description**: Build action menu (edit, delete, sync, deploy)
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] All actions work
      - [ ] Confirmation for destructive
      - [ ] Loading states

### Success Criteria

- [ ] Components render in Storybook
- [ ] TypeScript strict mode passes
- [ ] Components handle loading, error, empty states
- [ ] Keyboard navigation works
- [ ] Component tests achieve >80% coverage

### Key Files

- `skillmeat/web/components/entity/` - New entity components
- `skillmeat/web/hooks/useEntityLifecycle.ts` - Entity hooks
- `skillmeat/web/types/entity.ts` - Entity types

---

## Phase 3: Entity Management Page

**Status**: NOT STARTED
**Duration**: 5-7 days
**Effort**: 43 story points
**Completion**: 0% (0 of 9 tasks)
**Dependencies**: Phase 2 complete

### Completion Checklist

- [ ] **PAGE-001**: Create /manage Route (3 pts)
      **Description**: Set up Next.js app router page
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Route accessible
      - [ ] Basic layout renders
      - [ ] Navigation link added

- [ ] **PAGE-002**: Entity Tabs Component (3 pts)
      **Description**: Build tabs for entity types
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Tabs switch content
      - [ ] URL updates with tab
      - [ ] Keyboard accessible

- [ ] **PAGE-003**: Skills Tab Implementation (8 pts)
      **Description**: Full CRUD for skills
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] List skills
      - [ ] Add skill
      - [ ] Edit skill
      - [ ] Delete skill
      - [ ] View skill detail

- [ ] **PAGE-004**: Agents Tab Implementation (5 pts)
      **Description**: Full CRUD for agents
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] List, add, edit, delete agents
      - [ ] View agent detail

- [ ] **PAGE-005**: Commands Tab Implementation (5 pts)
      **Description**: Full CRUD for commands
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] List, add, edit, delete commands
      - [ ] View command detail

- [ ] **PAGE-006**: Hooks Tab Implementation (3 pts)
      **Description**: Full CRUD for hooks
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] List, add, edit, delete hooks
      - [ ] View hook detail

- [ ] **PAGE-007**: MCP Tab Integration (3 pts)
      **Description**: Integrate existing MCP components
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] MCP management in tab interface
      - [ ] Reuses existing MCP components
      - [ ] Consistent with other tabs

- [ ] **PAGE-008**: Entity Detail Panel (8 pts)
      **Description**: Side panel with tabs (Overview, Sync, History)
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Overview shows metadata
      - [ ] Sync shows upstream status
      - [ ] History shows versions
      - [ ] Actions work

- [ ] **PAGE-009**: Filter and Search (5 pts)
      **Description**: Add filter bar to entity management
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Type filter works
      - [ ] Status filter works
      - [ ] Tag filter works
      - [ ] Search by name

### Success Criteria

- [ ] All 5 entity tabs accessible and functional
- [ ] CRUD operations work end-to-end
- [ ] Filters correctly narrow results
- [ ] Entity detail panel shows all info
- [ ] Responsive layout works on tablet+
- [ ] Page load time < 1s

### Key Files

- `skillmeat/web/app/manage/page.tsx` - Management page
- `skillmeat/web/app/manage/[type]/page.tsx` - Type-filtered view
- `skillmeat/web/components/entity/` - Entity components

---

## Phase 4: Project Management

**Status**: NOT STARTED
**Duration**: 3-5 days
**Effort**: 20 story points
**Completion**: 0% (0 of 6 tasks)
**Dependencies**: Phase 1 complete (can run parallel with Phase 3)

### Completion Checklist

- [ ] **PROJ-001**: Project Creation Modal (5 pts)
      **Description**: Build modal form for new project
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Form validates input
      - [ ] Creates project on submit
      - [ ] Shows success/error

- [ ] **PROJ-002**: Projects Page Enhancement (2 pts)
      **Description**: Add "New Project" button to /projects
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Button opens modal
      - [ ] List updates after create

- [ ] **PROJ-003**: Project Edit Functionality (3 pts)
      **Description**: Add edit button with inline/modal edit
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Can edit name
      - [ ] Can edit description
      - [ ] Saves correctly

- [ ] **PROJ-004**: Project Delete Workflow (3 pts)
      **Description**: Add delete with multi-step confirmation
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Confirmation dialog
      - [ ] Type project name to confirm
      - [ ] Cleanup options

- [ ] **PROJ-005**: Project Settings Page (5 pts)
      **Description**: Create /projects/[id]/settings route
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Shows project config
      - [ ] Editable settings
      - [ ] Delete option

- [ ] **PROJ-006**: Project Card Enhancement (2 pts)
      **Description**: Update project cards with action menu
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Edit accessible
      - [ ] Delete accessible
      - [ ] Settings link

### Success Criteria

- [ ] Can create project from web UI
- [ ] Can edit project metadata
- [ ] Can delete project with confirmation
- [ ] Project settings page accessible
- [ ] All actions have proper error handling

### Key Files

- `skillmeat/web/app/projects/page.tsx` - Enhanced projects list
- `skillmeat/web/app/projects/[id]/settings/page.tsx` - Settings page
- `skillmeat/web/components/project/` - Project components

---

## Phase 5: Project-Level Entity Management

**Status**: NOT STARTED
**Duration**: 4-6 days
**Effort**: 24 story points
**Completion**: 0% (0 of 7 tasks)
**Dependencies**: Phase 3 and Phase 4 complete

### Completion Checklist

- [ ] **PLEVEL-001**: Create /projects/[id]/manage Route (3 pts)
      **Description**: Set up project-level entity page
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Route accessible
      - [ ] Has project context
      - [ ] Basic layout

- [ ] **PLEVEL-002**: EntityLifecycleManager Project Mode (3 pts)
      **Description**: Add project context to manager
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Components know context
      - [ ] Filters to project entities
      - [ ] Actions aware of context

- [ ] **PLEVEL-003**: Project Entity Tabs (3 pts)
      **Description**: Reuse tabs for project-scoped entities
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Shows deployed entities only
      - [ ] Same tabs as collection
      - [ ] Context-aware actions

- [ ] **PLEVEL-004**: Deploy from Collection Workflow (5 pts)
      **Description**: Add "Add from Collection" button
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Opens collection picker
      - [ ] Deploys to project
      - [ ] Shows result

- [ ] **PLEVEL-005**: Pull to Collection Workflow (5 pts)
      **Description**: Add "Pull to Collection" button
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Shows diff preview
      - [ ] Confirms pull
      - [ ] Updates collection

- [ ] **PLEVEL-006**: Entity Status in Project (3 pts)
      **Description**: Show sync status badges
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Modified badge
      - [ ] Synced badge
      - [ ] Outdated badge

- [ ] **PLEVEL-007**: Project Entity Navigation (2 pts)
      **Description**: Add manage link to project detail
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Link visible in project detail
      - [ ] Navigates to manage page

### Success Criteria

- [ ] Project entity management matches collection level
- [ ] Deploy from collection works
- [ ] Pull to collection works
- [ ] Status badges accurate
- [ ] Components reused (>80% code sharing)

### Key Files

- `skillmeat/web/app/projects/[id]/manage/page.tsx` - Project entity page
- `skillmeat/web/components/entity/` - Shared components

---

## Phase 6: Visual Merge Workflow

**Status**: NOT STARTED
**Duration**: 5-7 days
**Effort**: 32 story points
**Completion**: 0% (0 of 7 tasks)
**Dependencies**: Phase 2 (DiffViewer) and Phase 5 complete

### Completion Checklist

- [ ] **MERGE-001**: Sync Tab Enhancement (5 pts)
      **Description**: Add visual diff to sync tab
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] DiffViewer shows changes
      - [ ] Clear before/after
      - [ ] Scrolls together

- [ ] **MERGE-002**: MergeWorkflow Component (8 pts)
      **Description**: Build step-by-step merge UI
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Step 1: Preview changes
      - [ ] Step 2: Resolve conflicts
      - [ ] Step 3: Apply merge
      - [ ] Can cancel at any step

- [ ] **MERGE-003**: Conflict Detection UI (5 pts)
      **Description**: Integrate conflict detection
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Conflicts highlighted
      - [ ] Per-file indicators
      - [ ] Clear resolution needed

- [ ] **MERGE-004**: ConflictResolver Integration (3 pts)
      **Description**: Reuse existing conflict resolver
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Per-file resolution
      - [ ] Ours/theirs/manual
      - [ ] Saves choices

- [ ] **MERGE-005**: Merge Progress Indicator (3 pts)
      **Description**: Show progress during merge
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] SSE-based updates
      - [ ] Step completion
      - [ ] Error handling

- [ ] **MERGE-006**: Version Rollback UI (5 pts)
      **Description**: Add rollback button with confirmation
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] Shows version history
      - [ ] Confirms rollback
      - [ ] Reverts to previous

- [ ] **MERGE-007**: Merge History in Detail Panel (3 pts)
      **Description**: Show recent merges in history tab
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Merge commits visible
      - [ ] Shows what changed
      - [ ] Can expand details

### Success Criteria

- [ ] Visual diff shows accurate changes
- [ ] Merge workflow completes end-to-end
- [ ] Conflicts detected and resolved
- [ ] Rollback restores previous version
- [ ] Progress indicator works with SSE

### Key Files

- `skillmeat/web/components/entity/merge-workflow.tsx` - Merge workflow
- `skillmeat/web/components/entity/diff-viewer.tsx` - Diff visualization
- `skillmeat/web/hooks/useMerge.ts` - Merge hooks

---

## Phase 7: Testing & Polish

**Status**: NOT STARTED
**Duration**: 5-7 days
**Effort**: 54 story points
**Completion**: 0% (0 of 9 tasks)
**Dependencies**: All previous phases complete

### Completion Checklist

- [ ] **TEST-001**: Shared Component Unit Tests (8 pts)
      **Description**: Unit tests for all shared components
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] >80% coverage
      - [ ] All states tested
      - [ ] Interactions tested

- [ ] **TEST-002**: API Integration Tests (5 pts)
      **Description**: Tests for all new API endpoints
      **Assigned Subagent(s)**: python-backend-engineer
      **Acceptance Criteria**:
      - [ ] All endpoints tested
      - [ ] Error cases covered
      - [ ] Auth tested

- [ ] **TEST-003**: CRUD Flow Tests (5 pts)
      **Description**: Integration tests for CRUD operations
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Create flows pass
      - [ ] Update flows pass
      - [ ] Delete flows pass

- [ ] **TEST-004**: E2E Critical Paths (8 pts)
      **Description**: Playwright tests for key journeys
      **Assigned Subagent(s)**: frontend-developer
      **Acceptance Criteria**:
      - [ ] Create project E2E
      - [ ] Add entity E2E
      - [ ] Merge workflow E2E

- [ ] **TEST-005**: Accessibility Audit (5 pts)
      **Description**: axe-core + manual testing
      **Assigned Subagent(s)**: ui-engineer-enhanced
      **Acceptance Criteria**:
      - [ ] WCAG 2.1 AA compliance
      - [ ] Keyboard navigation
      - [ ] Screen reader tested

- [ ] **TEST-006**: Performance Optimization (5 pts)
      **Description**: Audit and optimize render performance
      **Assigned Subagent(s)**: react-performance-optimizer
      **Acceptance Criteria**:
      - [ ] Page load < 1s
      - [ ] Smooth interactions
      - [ ] No memory leaks

- [ ] **TEST-007**: Code Review (5 pts)
      **Description**: Senior review of all new code
      **Assigned Subagent(s)**: senior-code-reviewer
      **Acceptance Criteria**:
      - [ ] Code quality approved
      - [ ] Patterns consistent
      - [ ] Security reviewed

- [ ] **TEST-008**: Bug Fixes (8 pts)
      **Description**: Fix issues found during testing
      **Assigned Subagent(s)**: all developers
      **Acceptance Criteria**:
      - [ ] All P0/P1 bugs resolved
      - [ ] Regression tests added

- [ ] **TEST-009**: Documentation (5 pts)
      **Description**: Component docs, user guide
      **Assigned Subagent(s)**: documentation-writer
      **Acceptance Criteria**:
      - [ ] Component API docs
      - [ ] User guide complete
      - [ ] Examples provided

### Success Criteria

- [ ] Unit test coverage >80%
- [ ] All integration tests pass
- [ ] E2E tests pass in CI
- [ ] Accessibility audit passes
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Code review approved

### Key Files

- `skillmeat/web/__tests__/` - Frontend tests
- `tests/api/` - Backend API tests
- `e2e/` - Playwright E2E tests
- `docs/` - Documentation

---

## Blockers & Issues

### Active Blockers

None at this time.

### Resolved Blockers

None yet.

---

## Notes & Context

### Implementation Notes

- **Component Reuse**: Key goal is >80% component sharing between collection and project views
- **Progressive Enhancement**: Start with basic functionality, enhance with merge/diff
- **Shared State**: EntityLifecycleManager context handles both contexts

### Gotchas & Learnings

- TBD as implementation progresses

### Integration Points

- **SDK Dependency**: Frontend depends on regenerated SDK from Phase 1
- **Existing Components**: Reuse sync-dialog, conflict-resolver, version-tree
- **API Patterns**: Follow existing ErrorResponse, cursor pagination patterns

---

**Last Review**: 2025-11-24
**Next Review**: On phase completion
