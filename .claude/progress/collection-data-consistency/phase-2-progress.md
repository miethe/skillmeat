---
type: progress
prd: collection-data-consistency
phase: 2
title: Frontend Mapping Consolidation
status: completed
started: null
completed: null
progress: 100
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
owners:
- ui-engineer
contributors: []
tasks:
- id: TASK-2.1
  title: Create Centralized Entity Mapper
  status: completed
  assigned_to:
  - ui-engineer
  dependencies: []
  model: opus
  effort: 1.5h
  priority: critical
  files:
  - skillmeat/web/lib/api/entity-mapper.ts
- id: TASK-2.2
  title: Migrate useEntityLifecycle
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.1
  model: sonnet
  effort: 0.5h
  priority: high
  files:
  - skillmeat/web/hooks/useEntityLifecycle.tsx
- id: TASK-2.3
  title: Migrate collection/page.tsx
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.1
  model: sonnet
  effort: 0.5h
  priority: high
  files:
  - skillmeat/web/app/collection/page.tsx
- id: TASK-2.4
  title: Migrate projects/[id]/manage/page.tsx
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.1
  model: sonnet
  effort: 0.5h
  priority: high
  files:
  - skillmeat/web/app/projects/[id]/manage/page.tsx
- id: TASK-2.5
  title: Add Unit Tests for Entity Mapper
  status: completed
  assigned_to:
  - ui-engineer
  dependencies:
  - TASK-2.1
  model: sonnet
  effort: 0.5h
  priority: medium
  files:
  - skillmeat/web/__tests__/lib/api/entity-mapper.test.ts
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  - TASK-2.3
  - TASK-2.4
  - TASK-2.5
blockers: []
success_criteria:
- id: SC-2.1
  description: Single mapper file exports mapArtifactToEntity and mapArtifactsToEntities
  status: pending
- id: SC-2.2
  description: All 24 Entity fields mapped correctly
  status: pending
- id: SC-2.3
  description: Collection badges visible on /collection page
  status: pending
- id: SC-2.4
  description: Collection badges visible on /projects/[id]/manage page
  status: pending
- id: SC-2.5
  description: No TypeScript errors
  status: pending
- id: SC-2.6
  description: Entity mapper unit tests pass with >90% coverage
  status: pending
- id: SC-2.7
  description: Zero instances of enrichArtifactSummary or inline mapping remain
  status: pending
updated: '2026-01-31'
---

# Phase 2: Frontend Mapping Consolidation

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-data-consistency/phase-2-progress.md \
  -t TASK-2.1 -s completed

# Batch update after parallel execution
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-data-consistency/phase-2-progress.md \
  --updates "TASK-2.2:completed,TASK-2.3:completed,TASK-2.4:completed,TASK-2.5:completed"
```

## Overview

Phase 2 consolidates the 3 duplicate mapping locations into a single centralized Entity mapper. This ensures all 24 Entity fields are consistently mapped regardless of context, fixing the collection badges that are missing on various pages.

**Estimated Duration**: 3-4 hours
**Risk**: Medium (touches multiple components)
**Dependencies**: None (can run parallel with Phase 1)

## Tasks

### TASK-2.1: Create Centralized Entity Mapper

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 1.5h
**Priority**: critical
**Model**: opus

**Description**: Create `lib/api/entity-mapper.ts` with `mapArtifactToEntity()` function covering all 24 Entity fields

**Requirements**:
- All 24 Entity fields mapped
- TypeScript compiles without errors
- Export EntityContext type ('collection' | 'project' | 'marketplace')
- Export mapArtifactsToEntities batch utility
- Collections field ALWAYS mapped (critical fix)

**Files**:
- `skillmeat/web/lib/api/entity-mapper.ts` (NEW)

**Key Implementation Notes**:
- Context-aware status mapping
- Null-safe collection array handling
- Type-safe with full Entity interface compliance

---

### TASK-2.2: Migrate useEntityLifecycle

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-2.1

**Description**: Replace `mapApiArtifactToEntity()` in `hooks/useEntityLifecycle.tsx` with centralized mapper import

**Requirements**:
- Hook uses centralized mapper
- All existing hook tests pass
- No breaking changes to hook interface

**Files**:
- `skillmeat/web/hooks/useEntityLifecycle.tsx`: Import and use centralized mapper

---

### TASK-2.3: Migrate collection/page.tsx

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-2.1

**Description**: Remove `enrichArtifactSummary()` function and use centralized mapper

**Requirements**:
- Collection page shows collection badges
- No inline mapping code remains
- Remove dead code completely

**Files**:
- `skillmeat/web/app/collection/page.tsx`: Remove enrichArtifactSummary, use mapper

---

### TASK-2.4: Migrate projects/[id]/manage/page.tsx

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.5h
**Priority**: high
**Model**: sonnet
**Dependencies**: TASK-2.1

**Description**: Remove both inline enrichment blocks (lines 80-95, 117-132) and use centralized mapper

**Requirements**:
- Project manage page uses centralized mapper
- No inline mapping code remains
- Collection badges visible for project-deployed artifacts

**Files**:
- `skillmeat/web/app/projects/[id]/manage/page.tsx`: Remove inline mapping blocks

---

### TASK-2.5: Add Unit Tests for Entity Mapper

**Status**: `pending`
**Assigned**: ui-engineer
**Effort**: 0.5h
**Priority**: medium
**Model**: sonnet
**Dependencies**: TASK-2.1

**Description**: Create tests for `mapArtifactToEntity()` covering all contexts and edge cases

**Requirements**:
- >90% coverage on entity-mapper.ts
- Tests for null/undefined handling
- Tests for all three contexts (collection, project, marketplace)
- Tests for batch mapping utility

**Files**:
- `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts` (NEW)

---

## Quality Gates

- [ ] Single mapper file exports `mapArtifactToEntity` and `mapArtifactsToEntities`
- [ ] All 24 Entity fields mapped correctly
- [ ] Collection badges visible on /collection page
- [ ] Collection badges visible on /projects/[id]/manage page
- [ ] No TypeScript errors
- [ ] Entity mapper unit tests pass with >90% coverage
- [ ] Zero instances of `enrichArtifactSummary` or inline mapping remain

## Key Files Modified

- `skillmeat/web/lib/api/entity-mapper.ts` (NEW)
- `skillmeat/web/hooks/useEntityLifecycle.tsx`
- `skillmeat/web/app/collection/page.tsx`
- `skillmeat/web/app/projects/[id]/manage/page.tsx`
- `skillmeat/web/__tests__/lib/api/entity-mapper.test.ts` (NEW)
