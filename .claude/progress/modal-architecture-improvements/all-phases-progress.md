---
type: progress
prd: modal-architecture-improvements
phase: all
status: completed
progress: 100
created: '2026-01-28'
last_updated: '2026-01-28'
tasks:
- id: BUG-001
  name: Fix `/projects/[id]/page.tsx` handlers
  phase: 1
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies: []
  model: opus
  estimate_hours: 1.5
- id: BUG-002
  name: Fix `/projects/[id]/manage/page.tsx` handlers
  phase: 1
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies: []
  model: opus
  estimate_hours: 1.0
- id: BUG-003
  name: Manual verification of projects pages navigation
  phase: 1
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - BUG-001
  - BUG-002
  model: sonnet
  estimate_hours: 0.5
- id: COMP-001
  name: Create `CollectionArtifactModal` wrapper
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies: []
  model: opus
  estimate_hours: 1.5
- id: COMP-002
  name: Create `ProjectArtifactModal` wrapper
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies: []
  model: opus
  estimate_hours: 1.5
- id: COMP-003
  name: Update `/collection/page.tsx` to use wrapper
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - COMP-001
  model: sonnet
  estimate_hours: 0.5
- id: COMP-004
  name: Update `/manage/page.tsx` to use wrapper
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - COMP-001
  model: sonnet
  estimate_hours: 0.5
- id: COMP-005
  name: Update `/projects/[id]/page.tsx` to use wrapper
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - COMP-002
  - BUG-001
  model: sonnet
  estimate_hours: 0.5
- id: COMP-006
  name: Update `/projects/[id]/manage/page.tsx` to use wrapper
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - COMP-002
  - BUG-002
  model: sonnet
  estimate_hours: 0.5
- id: COMP-007
  name: "Complete `entity` \u2192 `artifact` prop migration"
  phase: 2
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies: []
  model: opus
  estimate_hours: 1.5
- id: PREF-001
  name: Add `DataPrefetcher` component to `providers.tsx`
  phase: 3
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies: []
  model: opus
  estimate_hours: 1.0
- id: PREF-002
  name: Integrate prefetcher in provider tree
  phase: 3
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - PREF-001
  model: sonnet
  estimate_hours: 0.5
- id: PREF-003
  name: Remove eager fetch from modal
  phase: 3
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - PREF-002
  model: sonnet
  estimate_hours: 0.5
- id: PREF-004
  name: Performance verification of Sources tab
  phase: 3
  status: completed
  assigned_to: ui-engineer-enhanced
  dependencies:
  - PREF-003
  model: sonnet
  estimate_hours: 1.0
parallelization:
  phase_1_batch_1:
  - BUG-001
  - BUG-002
  phase_1_batch_2:
  - BUG-003
  phase_2_batch_1:
  - COMP-001
  - COMP-002
  phase_2_batch_2:
  - COMP-003
  - COMP-004
  - COMP-005
  - COMP-006
  phase_2_batch_3:
  - COMP-007
  phase_3_batch_1:
  - PREF-001
  phase_3_batch_2:
  - PREF-002
  phase_3_batch_3:
  - PREF-003
  phase_3_batch_4:
  - PREF-004
phase_dependencies:
  phase_1: []
  phase_2:
  - phase_1
  phase_3:
  - phase_1
total_tasks: 14
completed_tasks: 14
in_progress_tasks: 0
blocked_tasks: 0
updated: '2026-01-28'
schema_version: 2
doc_type: progress
feature_slug: modal-architecture-improvements
---

# Modal Architecture Improvements - All Phases Progress

**Status**: Not Started
**Total Tasks**: 14
**Completion**: 0%
**Last Updated**: 2026-01-28

---

## Phase 1: Fix Critical Bugs (Projects Pages Navigation)

**Estimated Duration**: 2-3 hours
**Status**: Pending
**Completion**: 0/3 tasks

### Tasks

- [ ] **BUG-001**: Fix `/projects/[id]/page.tsx` handlers (1.5 hrs)
- [ ] **BUG-002**: Fix `/projects/[id]/manage/page.tsx` handlers (1.0 hrs)
- [ ] **BUG-003**: Manual verification of projects pages navigation (0.5 hrs)

### Phase 1 Quality Gates

- [ ] Both navigation handlers implemented in `/projects/[id]/page.tsx`
- [ ] Both navigation handlers verified in `/projects/[id]/manage/page.tsx`
- [ ] Clicking Source link navigates to correct source detail page
- [ ] Clicking Deployment link navigates to correct project page
- [ ] No console errors or warnings

---

## Phase 2: Component Props Contract Enforcement

**Estimated Duration**: 4-6 hours
**Status**: Pending
**Completion**: 0/7 tasks
**Dependencies**: Phase 1 (optional - can overlap)

### Tasks

- [ ] **COMP-001**: Create `CollectionArtifactModal` wrapper (1.5 hrs)
- [ ] **COMP-002**: Create `ProjectArtifactModal` wrapper (1.5 hrs)
- [ ] **COMP-003**: Update `/collection/page.tsx` (0.5 hrs)
- [ ] **COMP-004**: Update `/manage/page.tsx` (0.5 hrs)
- [ ] **COMP-005**: Update `/projects/[id]/page.tsx` (0.5 hrs)
- [ ] **COMP-006**: Update `/projects/[id]/manage/page.tsx` (0.5 hrs)
- [ ] **COMP-007**: Complete `entity` → `artifact` prop migration (1.5 hrs)

### Phase 2 Quality Gates

- [ ] Both wrapper components created and export properly
- [ ] All four pages updated to use appropriate wrapper
- [ ] Navigation handlers work identically before/after
- [ ] All components use `artifact` prop consistently
- [ ] No TypeScript errors or warnings

---

## Phase 3: App-Level Data Prefetching

**Estimated Duration**: 2-3 hours
**Status**: Pending
**Completion**: 0/4 tasks
**Dependencies**: Phase 1 (Phase 2 optional)

### Tasks

- [ ] **PREF-001**: Add `DataPrefetcher` component (1.0 hrs)
- [ ] **PREF-002**: Integrate prefetcher in provider tree (0.5 hrs)
- [ ] **PREF-003**: Remove eager fetch from modal (0.5 hrs)
- [ ] **PREF-004**: Performance verification (1.0 hrs)

### Phase 3 Quality Gates

- [ ] `DataPrefetcher` component functioning correctly
- [ ] Sources data prefetches on app initialization
- [ ] Sources tab opens instantly (<200ms)
- [ ] No duplicate data fetches or race conditions
- [ ] Performance improvement measurable and consistent

---

## Quick Reference: Orchestration Commands

### Sequential Phase Execution

```bash
# Execute Phase 1 (bug fixes)
/dev:execute-phase 1

# After Phase 1, execute Phase 2
/dev:execute-phase 2

# After Phase 1, execute Phase 3 (can run in parallel with Phase 2)
/dev:execute-phase 3
```

### Parallel Batch Execution (Manual)

**Phase 1 Parallel Work**:
```bash
Task("ui-engineer-enhanced", "BUG-001: Fix /projects/[id]/page.tsx - add onNavigateToSource and onNavigateToDeployment handlers", model="opus")
Task("ui-engineer-enhanced", "BUG-002: Fix /projects/[id]/manage/page.tsx - ensure navigation handlers wired", model="opus")
# Wait for both, then:
Task("ui-engineer-enhanced", "BUG-003: Manual verification of projects pages navigation", model="sonnet")
```

**Phase 2 Parallel Work**:
```bash
Task("ui-engineer-enhanced", "COMP-001: Create CollectionArtifactModal wrapper component", model="opus")
Task("ui-engineer-enhanced", "COMP-002: Create ProjectArtifactModal wrapper component", model="opus")
# Wait for both, then:
Task("ui-engineer-enhanced", "COMP-003/004/005/006: Update all four pages to use wrappers", model="sonnet")
Task("ui-engineer-enhanced", "COMP-007: Complete entity → artifact prop migration", model="opus")
```

**Phase 3 Sequential**:
```bash
Task("ui-engineer-enhanced", "PREF-001: Add DataPrefetcher component", model="opus")
Task("ui-engineer-enhanced", "PREF-002: Integrate prefetcher in provider tree", model="sonnet")
Task("ui-engineer-enhanced", "PREF-003: Remove eager fetch from modal", model="sonnet")
Task("ui-engineer-enhanced", "PREF-004: Performance verification", model="sonnet")
```

### Status Updates (CLI)

```bash
# Mark single task complete
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/modal-architecture-improvements/all-phases-progress.md \
  -t BUG-001 -s completed

# Batch update after phase completion
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/modal-architecture-improvements/all-phases-progress.md \
  --updates "BUG-001:completed,BUG-002:completed,BUG-003:completed"
```

### Key Files to Modify

| File | Phase | Task |
|------|-------|------|
| `skillmeat/web/app/projects/[id]/page.tsx` | 1 | BUG-001, COMP-005 |
| `skillmeat/web/app/projects/[id]/manage/page.tsx` | 1 | BUG-002, COMP-006 |
| `skillmeat/web/components/shared/CollectionArtifactModal.tsx` | 2 | COMP-001 |
| `skillmeat/web/components/shared/ProjectArtifactModal.tsx` | 2 | COMP-002 |
| `skillmeat/web/app/collection/page.tsx` | 2 | COMP-003 |
| `skillmeat/web/app/manage/page.tsx` | 2 | COMP-004 |
| `skillmeat/web/components/providers.tsx` | 3 | PREF-001, PREF-002 |
| `skillmeat/web/components/entity/unified-entity-modal.tsx` | 3 | PREF-003 |

---

**Total Estimated Effort**: 10-14 hours (1-2 days)
**Reference Plan**: `docs/project_plans/implementation_plans/refactors/modal-architecture-improvements-r2r3.md`
