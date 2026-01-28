---
type: progress
prd: entity-artifact-consolidation
phase: 4-5
status: pending
progress: 83
last_updated: '2026-01-28'
tasks:
- id: P4-T1
  name: Update UnifiedEntityModal props
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P3-T6
  model: opus
  effort: 2
  files:
  - skillmeat/web/components/entity/unified-entity-modal.tsx
- id: P4-T2
  name: Update modal tab components
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4-T1
  model: opus
  effort: 3
  files:
  - skillmeat/web/components/entity/modal-collections-tab.tsx
  - skillmeat/web/components/entity/modal-sources-tab.tsx
  - skillmeat/web/components/entity/modal-upstream-tab.tsx
  - skillmeat/web/components/entity/modal-basic-info-tab.tsx
- id: P4-T3
  name: Update entity form component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4-T1
  model: opus
  effort: 2
  files:
  - skillmeat/web/components/entity/entity-form.tsx
- id: P4-T4
  name: Refactor /collection page
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4-T2
  model: opus
  effort: 2
  files:
  - skillmeat/web/app/collection/page.tsx
- id: P4-T5
  name: Refactor /manage page
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4-T2
  - P4-T3
  model: opus
  effort: 2
  files:
  - skillmeat/web/app/manage/page.tsx
- id: P4-T6
  name: Update additional components
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4-T1
  model: opus
  effort: 3
  files:
  - skillmeat/web/components/entity/*.tsx
  - skillmeat/web/components/sync-status/*.tsx
- id: P4-T7
  name: Component integration testing
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - P4-T4
  - P4-T5
  - P4-T6
  model: opus
  effort: 3
  files: []
- id: P5-T1
  name: Add deprecation notices
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - P4-T7
  model: haiku
  effort: 1
  files:
  - skillmeat/web/types/entity.ts
- id: P5-T2
  name: Create migration guide
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - P5-T1
  model: sonnet
  effort: 2
  files:
  - .claude/guides/entity-to-artifact-migration.md
- id: P5-T3
  name: Update architecture documentation
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - P5-T1
  model: sonnet
  effort: 2
  files:
  - skillmeat/web/CLAUDE.md
  - .claude/context/key-context/component-patterns.md
- id: P5-T4
  name: Code audit and cleanup
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - P5-T2
  - P5-T3
  model: haiku
  effort: 1
  files: []
- id: P5-T5
  name: Final validation and sign-off
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - P5-T4
  model: opus
  effort: 2
  files: []
parallelization:
  batch_1:
  - P4-T1
  batch_2:
  - P4-T2
  - P4-T3
  batch_3:
  - P4-T4
  - P4-T5
  - P4-T6
  batch_4:
  - P4-T7
  batch_5:
  - P5-T1
  batch_6:
  - P5-T2
  - P5-T3
  batch_7:
  - P5-T4
  batch_8:
  - P5-T5
quality_gates:
- All components accept Artifact type
- Modal displays complete data from both pages
- Form CRUD operations work with new type
- Component tests >80% coverage
- No visual regressions
- Migration guide published
- Deprecation notices in place
- Code review approval
total_tasks: 12
completed_tasks: 10
in_progress_tasks: 0
blocked_tasks: 0
updated: '2026-01-28'
---

# Phase 4-5: Component Unification & Deprecation

## Quick Reference

### Task() Commands

```
# Phase 4: Component Type Unification
Task("ui-engineer-enhanced", "Execute P4-T1: Update UnifiedEntityModal props to accept Artifact type. Make navigation handlers required when artifact has source. Add runtime warning for missing handlers.", model="opus")

Task("ui-engineer-enhanced", "Execute P4-T2: Update modal tab components to accept Artifact type and access flattened metadata. Update modal-collections-tab, modal-sources-tab, modal-upstream-tab, modal-basic-info-tab.", model="opus")

Task("ui-engineer-enhanced", "Execute P4-T3: Update entity-form.tsx to accept Artifact type. Bind form fields to flattened properties (description, not metadata.description).", model="opus")

Task("ui-engineer-enhanced", "Execute P4-T4: Refactor /collection page to use Artifact type throughout. Ensure navigation handlers provided to modal.", model="opus")

Task("ui-engineer-enhanced", "Execute P4-T5: Refactor /manage page to use Artifact type consistently. Verify CRUD operations work.", model="opus")

Task("ui-engineer-enhanced", "Execute P4-T6: Update remaining Entity-typed components in components/entity/ and components/sync-status/. Use codebase-explorer to find all.", model="opus")

Task("ui-engineer-enhanced", "Execute P4-T7: Run component integration tests. Verify modal, form, collections tab, sources tab, navigation handlers.", model="opus")

# Phase 5: Deprecation & Cleanup
Task("documentation-writer", "Execute P5-T1: Add @deprecated JSDoc notices to all Entity exports in types/entity.ts. Reference Q3 2026 removal date.", model="haiku")

Task("documentation-writer", "Execute P5-T2: Create .claude/guides/entity-to-artifact-migration.md with step-by-step instructions, before/after examples, FAQ.", model="sonnet")

Task("documentation-writer", "Execute P5-T3: Update skillmeat/web/CLAUDE.md and component-patterns.md to reference Artifact type instead of Entity.", model="sonnet")

Task("documentation-writer", "Execute P5-T4: Audit codebase for remaining Entity usages. Create list of files (<10 expected). Verify deprecation notices in place.", model="haiku")

Task("documentation-writer", "Execute P5-T5: Final validation - all phases complete, all bug fixes verified, all tests pass, code review approval.", model="opus")
```

### CLI Updates

```bash
# Single task completion
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/entity-artifact-consolidation/phase-4-5-progress.md \
  -t P4-T1 -s completed

# Batch update after parallel tasks
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/entity-artifact-consolidation/phase-4-5-progress.md \
  --updates "P4-T2:completed,P4-T3:completed"

# Phase 5 batch
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/entity-artifact-consolidation/phase-4-5-progress.md \
  --updates "P5-T2:completed,P5-T3:completed"
```

## Phase Overview

**Phase 4**: Update all components accepting Entity type to use unified Artifact type. Update modal and form components. Enforce required modal handlers. Ensure type consistency.

**Phase 5**: Add deprecation notices. Document migration path. Audit remaining Entity usages. Update architecture documentation.

**Total Effort**: 19 story points
**Duration**: 7-10 days
**Dependencies**: Phase 1-3 complete

---

## Phase 4 Tasks

### P4-T1: Update UnifiedEntityModal props

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/components/entity/unified-entity-modal.tsx`

**Changes**:
- Props accept `Artifact` type (not `Entity`)
- Navigation handlers remain same signature
- Add runtime warning if handlers missing on artifacts with source
- Modal tabs access flattened properties

**Acceptance Criteria**:
- [ ] Props accept `Artifact` type
- [ ] Runtime warning for missing handlers
- [ ] Modal tabs access flattened properties
- [ ] TypeScript compilation succeeds
- [ ] Visual appearance unchanged

---

### P4-T2: Update modal tab components

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 3 points
- **Files**:
  - `modal-collections-tab.tsx`
  - `modal-sources-tab.tsx`
  - `modal-upstream-tab.tsx`
  - `modal-basic-info-tab.tsx`

**Key Change**: Access flattened metadata
- Before: `entity.metadata?.description`
- After: `artifact.description`

**Acceptance Criteria**:
- [ ] All tab components accept `Artifact` type
- [ ] No more `metadata?.` paths
- [ ] Collections tab displays correctly
- [ ] Sources tab shows source information
- [ ] TypeScript compilation succeeds

---

### P4-T3: Update entity form component

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/components/entity/entity-form.tsx`

**Changes**:
- Accept `Artifact` type
- Form fields bind to flattened properties
- Form submission returns complete Artifact

**Acceptance Criteria**:
- [ ] Form accepts `Artifact` type
- [ ] Form fields bind to flattened properties
- [ ] Form submission returns complete Artifact
- [ ] CRUD operations work
- [ ] All tests pass

---

### P4-T4: Refactor /collection page

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/app/collection/page.tsx`

**Changes**:
- Use `Artifact` type throughout
- No `artifactToEntity()` conversion (handled in P3-T5)
- Ensure navigation handlers provided to modal

**Acceptance Criteria**:
- [ ] Page uses `Artifact` type throughout
- [ ] Modal receives navigation handlers
- [ ] Click handlers work correctly
- [ ] Modal opens with complete data

---

### P4-T5: Refactor /manage page

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 2 points
- **File**: `skillmeat/web/app/manage/page.tsx`

**Changes**:
- Use `Artifact` type consistently
- Form and modal components handle unified type
- CRUD operations work

**Acceptance Criteria**:
- [ ] Page uses `Artifact` type
- [ ] Form and modal work correctly
- [ ] CRUD operations work
- [ ] Collections tab shows data
- [ ] Navigation handlers provided

---

### P4-T6: Update additional components

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 3 points
- **Files**: ~10-15 component files

**Components to Update**:
- `components/entity/entity-list.tsx`
- `components/entity/entity-crud-modal.tsx`
- `components/entity/artifact-card.tsx`
- `components/sync-status/sync-status-badge.tsx`
- `components/sync-status/sync-status-dialog.tsx`
- `components/sync-status/sync-status-tab.tsx`

**Process**:
```bash
grep -r "Entity" skillmeat/web/components --include="*.tsx" | grep -v "node_modules"
```

**Acceptance Criteria**:
- [ ] All Entity-typed components updated
- [ ] Type consistency across all components
- [ ] All component tests pass

---

### P4-T7: Component integration testing

- **Status**: pending
- **Agent**: ui-engineer-enhanced
- **Model**: opus
- **Effort**: 3 points

**Test Coverage**:
- UnifiedEntityModal with Artifact prop
- EntityForm with Artifact type
- /collection page with Artifact type
- /manage page with Artifact type
- Modal tabs display data correctly
- Navigation handlers called correctly

**Acceptance Criteria**:
- [ ] All component tests pass
- [ ] >80% test coverage
- [ ] Modal displays complete data
- [ ] Collections tab populated (bug fix)
- [ ] Form submission works
- [ ] Navigation handlers work
- [ ] No visual regression

---

## Phase 5 Tasks

### P5-T1: Add deprecation notices

- **Status**: pending
- **Agent**: documentation-writer
- **Model**: haiku
- **Effort**: 1 point
- **File**: `skillmeat/web/types/entity.ts`

**Changes**:
- Add `@deprecated` JSDoc to all Entity exports
- Include Q3 2026 removal date
- Reference migration guide

**Acceptance Criteria**:
- [ ] All Entity exports marked `@deprecated`
- [ ] Deprecation messages include removal timeline
- [ ] Migration guide referenced
- [ ] IDE shows deprecation warnings

---

### P5-T2: Create migration guide

- **Status**: pending
- **Agent**: documentation-writer
- **Model**: sonnet
- **Effort**: 2 points
- **File**: `.claude/guides/entity-to-artifact-migration.md` (NEW)

**Content**:
- Overview and rationale
- Timeline (Jan-Jun 2026)
- Step-by-step migration instructions
- Before/after examples
- Common patterns table
- FAQ
- Checklist

**Acceptance Criteria**:
- [ ] Comprehensive migration guide written
- [ ] Step-by-step instructions provided
- [ ] Before/after examples included
- [ ] FAQ addresses likely questions
- [ ] Checklist for developers

---

### P5-T3: Update architecture documentation

- **Status**: pending
- **Agent**: documentation-writer
- **Model**: sonnet
- **Effort**: 2 points
- **Files**:
  - `skillmeat/web/CLAUDE.md`
  - `.claude/context/key-context/component-patterns.md`

**Changes**:
- Update type system section to reference Artifact
- Update examples to use flattened metadata
- Add deprecation note for Entity
- Update status enum values

**Acceptance Criteria**:
- [ ] CLAUDE.md updated with Artifact references
- [ ] Examples use flattened metadata structure
- [ ] Migration guide referenced
- [ ] Architecture documentation consistent

---

### P5-T4: Code audit and cleanup

- **Status**: pending
- **Agent**: documentation-writer
- **Model**: haiku
- **Effort**: 1 point

**Process**:
```bash
# Find remaining Entity usages
grep -r "Entity" skillmeat/web --include="*.ts" --include="*.tsx" | grep -v "node_modules" | grep -v ".deprecated"

# Expected: <10 remaining files (mostly intentional)
```

**Acceptance Criteria**:
- [ ] Audit completed
- [ ] Remaining Entity usages documented (<10)
- [ ] All usages intentional or deprecated
- [ ] Audit report generated

---

### P5-T5: Final validation and sign-off

- **Status**: pending
- **Agent**: documentation-writer
- **Model**: opus
- **Effort**: 2 points

**Validation Checklist**:

**Type System**:
- [ ] Artifact type defined and exported
- [ ] SyncStatus enum with 5 values
- [ ] Backward compatibility aliases work
- [ ] TypeScript strict mode passes

**API Mapping**:
- [ ] Single mapApiResponseToArtifact() function
- [ ] All 4 old conversion functions removed
- [ ] Both pipelines use unified mapper

**Components**:
- [ ] All components accept Artifact type
- [ ] Modal displays complete data
- [ ] Navigation handlers consistent

**Bug Fixes**:
- [ ] Collections tab populated on /manage (FIXED)
- [ ] Source tab appears on /collection (FIXED)
- [ ] Source link navigation works (FIXED)

**Documentation**:
- [ ] Migration guide complete
- [ ] CLAUDE.md updated
- [ ] Deprecation notices in place

**Acceptance Criteria**:
- [ ] All Phase 1-5 tasks complete
- [ ] All tests passing
- [ ] All bug fixes verified
- [ ] Documentation complete
- [ ] Code review approval
- [ ] Ready for deployment

---

## Quality Gates (Before Release)

- [ ] All Phase 4-5 tasks completed
- [ ] All components accept Artifact type
- [ ] Modal works from both pages
- [ ] Form CRUD operations work
- [ ] All tests pass (>85% coverage)
- [ ] No visual regressions
- [ ] Migration guide published
- [ ] Deprecation notices in place
- [ ] Code review approval

---

## Bug Fixes Verified

- [ ] Collections tab populated on /manage page
- [ ] Source tab appears on /collection page
- [ ] Source link navigation functional
- [ ] No synthetic fallback artifacts

---

## Timeline Summary

| Phase | Duration | Critical Path |
|-------|----------|---------------|
| Phase 4: Components | 5-7 days | Yes |
| Phase 5: Deprecation | 2-3 days | No |

---

## Notes

- **Implementation Spec**: `docs/project_plans/implementation_plans/refactors/entity-artifact-consolidation-v1/phase-4-5-components.md`
- **PRD**: `docs/project_plans/PRDs/refactors/entity-artifact-consolidation-v1.md`
- **Removal Timeline**: Q3 2026 (6-month deprecation window)
