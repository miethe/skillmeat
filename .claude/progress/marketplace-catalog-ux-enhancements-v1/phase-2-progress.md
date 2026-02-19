---
prd: marketplace-catalog-ux-enhancements-v1
phase: 2
title: Bulk Tag Application
status: completed
started_at: '2026-01-08T12:00:00Z'
completed_at: '2026-01-08T13:15:00Z'
total_story_points: 13.5
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  batch_3:
  - TASK-2.3
  batch_4:
  - TASK-2.4
  batch_5:
  - TASK-2.5
  - TASK-2.6
tasks:
- id: TASK-2.1
  title: Extract directories from catalog
  status: completed
  story_points: 1
  assigned_to: ui-engineer
  dependencies: []
  started_at: '2026-01-08T12:00:00Z'
  completed_at: '2026-01-08T12:10:00Z'
- id: TASK-2.2
  title: Create BulkTagDialog component
  status: completed
  story_points: 4
  assigned_to: ui-engineer-enhanced
  dependencies:
  - TASK-2.1
  started_at: '2026-01-08T12:10:00Z'
  completed_at: '2026-01-08T12:25:00Z'
- id: TASK-2.3
  title: Implement directory tag options
  status: completed
  story_points: 3
  assigned_to: ui-engineer-enhanced
  dependencies:
  - TASK-2.2
  started_at: '2026-01-08T12:25:00Z'
  completed_at: '2026-01-08T12:40:00Z'
- id: TASK-2.4
  title: Implement tag application logic
  status: completed
  story_points: 2
  assigned_to: ui-engineer
  dependencies:
  - TASK-2.3
  started_at: '2026-01-08T12:40:00Z'
  completed_at: '2026-01-08T12:55:00Z'
- id: TASK-2.5
  title: Wire dialog to catalog toolbar
  status: completed
  story_points: 1.5
  assigned_to: ui-engineer
  dependencies:
  - TASK-2.2
  - TASK-2.4
  started_at: '2026-01-08T12:55:00Z'
  completed_at: '2026-01-08T13:10:00Z'
- id: TASK-2.6
  title: Unit and integration tests
  status: completed
  story_points: 2
  assigned_to: ui-engineer
  dependencies:
  - TASK-2.4
  started_at: '2026-01-08T12:55:00Z'
  completed_at: '2026-01-08T13:10:00Z'
success_criteria:
- Dialog shows detected directories from artifact paths
- Each directory has manual Tags and Path-based Suggested Tags options
- Tags apply to all artifacts matching directory prefix
- Dialog handles 50+ directories without lag
- Toast feedback shows updated artifact count
- '>80% unit test coverage'
schema_version: 2
doc_type: progress
feature_slug: marketplace-catalog-ux-enhancements-v1
type: progress
---

# Phase 2: Bulk Tag Application

## Overview

Implement bulk tag application UI for applying tags to all artifacts in a directory. This phase enables users to efficiently tag large collections of artifacts by directory, with both manual and path-based tag suggestions.

## Phase Objectives

1. **Directory Detection**: Extract unique directories from marketplace catalog artifact paths
2. **Bulk Tag Dialog**: Create modal component with directory-based tag application UI
3. **Tag Options**: Implement manual tag input and path-based suggested tags per directory
4. **Application Logic**: Apply tags to all artifacts matching directory prefix
5. **Toolbar Integration**: Wire dialog to catalog page toolbar button
6. **Testing**: Comprehensive unit and integration test coverage

## Tasks

### TASK-2.1: Extract directories from catalog
**Status**: Pending | **Points**: 1 | **Owner**: ui-engineer

**Description**: Create utility function to extract unique directory paths from marketplace catalog artifacts.

**Implementation Details**:
- Parse `full_path` field from each artifact in catalog
- Extract directory portion (everything before final `/`)
- Deduplicate and sort directories
- Handle edge cases (root artifacts, nested paths)

**Files**:
- `skillmeat/web/lib/utils/directory-utils.ts` (new)
- `skillmeat/web/lib/utils/directory-utils.test.ts` (new)

**Acceptance Criteria**:
- Extracts directories from artifact paths
- Handles nested paths (e.g., `skills/dev/`, `skills/dev/testing/`)
- Returns sorted unique list
- Unit tests cover edge cases

---

### TASK-2.2: Create BulkTagDialog component
**Status**: Pending | **Points**: 4 | **Owner**: ui-engineer-enhanced

**Description**: Create dialog component with directory list, tag input fields, and apply button.

**Dependencies**: TASK-2.1

**Implementation Details**:
- Use Radix UI Dialog component
- Display directories in scrollable list
- Each directory row has:
  - Directory path display
  - Manual tag input field
  - Path-based suggested tags section
- Apply button at bottom
- Cancel button
- Loading states during tag application

**Files**:
- `skillmeat/web/components/marketplace/bulk-tag-dialog.tsx` (new)
- `skillmeat/web/components/marketplace/bulk-tag-dialog.test.tsx` (new)

**Acceptance Criteria**:
- Dialog renders with directory list
- Handles 50+ directories without lag
- Keyboard navigation works (tab between inputs)
- Accessible (ARIA labels, focus management)
- Loading state shown during apply

---

### TASK-2.3: Implement directory tag options
**Status**: Pending | **Points**: 3 | **Owner**: ui-engineer-enhanced

**Description**: Add manual tag input and path-based suggested tag options per directory.

**Dependencies**: TASK-2.2

**Implementation Details**:
- Manual tag input:
  - Autocomplete from existing tags
  - Multi-select tag chips
  - Create new tags inline
- Path-based suggestions:
  - Parse directory path segments as tag candidates
  - Show as clickable chips
  - One-click to add to manual tags
- Tag validation (no duplicates, max length)

**Files**:
- Update `skillmeat/web/components/marketplace/bulk-tag-dialog.tsx`
- `skillmeat/web/components/marketplace/directory-tag-input.tsx` (new)
- `skillmeat/web/lib/utils/tag-suggestions.ts` (new)

**Acceptance Criteria**:
- Manual tag input supports multi-select
- Autocomplete shows existing tags
- Path-based suggestions generated from directory segments
- Clicking suggestion adds to manual tags
- No duplicate tags allowed
- Tag validation feedback

---

### TASK-2.4: Implement tag application logic
**Status**: Pending | **Points**: 2 | **Owner**: ui-engineer

**Description**: Implement logic to apply tags to all artifacts matching each directory prefix.

**Dependencies**: TASK-2.3

**Implementation Details**:
- For each directory with tags:
  - Find all artifacts where `full_path` starts with directory
  - Merge new tags with existing tags (deduplicate)
  - Batch update artifacts in bulk
- Show progress indicator during application
- Return count of updated artifacts
- Handle errors gracefully (partial success)

**Files**:
- `skillmeat/web/lib/utils/bulk-tag-apply.ts` (new)
- `skillmeat/web/lib/utils/bulk-tag-apply.test.ts` (new)

**Acceptance Criteria**:
- Tags applied to all matching artifacts
- Existing tags preserved (merge, not replace)
- Batch updates for performance
- Progress indicator during long operations
- Error handling with rollback on failure
- Returns updated artifact count

---

### TASK-2.5: Wire dialog to catalog toolbar
**Status**: Pending | **Points**: 1.5 | **Owner**: ui-engineer

**Description**: Add "Bulk Tag" button to catalog toolbar and wire to BulkTagDialog.

**Dependencies**: TASK-2.2, TASK-2.4

**Implementation Details**:
- Add button to catalog page toolbar
- Open dialog on click
- Pass catalog artifacts to dialog
- Show success toast with updated count
- Refresh catalog after apply
- Disable button when no artifacts in catalog

**Files**:
- Update `skillmeat/web/app/marketplace/catalog/page.tsx`

**Acceptance Criteria**:
- Button visible in catalog toolbar
- Dialog opens on click
- Success toast shows updated artifact count
- Catalog refreshes to show new tags
- Button disabled when catalog empty

---

### TASK-2.6: Unit and integration tests
**Status**: Pending | **Points**: 2 | **Owner**: ui-engineer

**Description**: Write comprehensive tests for bulk tag application feature.

**Dependencies**: TASK-2.4

**Implementation Details**:
- Unit tests for:
  - Directory extraction utility
  - Tag suggestion generation
  - Bulk tag application logic
  - Dialog component rendering
- Integration tests for:
  - End-to-end bulk tag workflow
  - Error handling scenarios
  - Performance with large catalogs (50+ directories)

**Files**:
- Update all `*.test.tsx` and `*.test.ts` files created in previous tasks

**Acceptance Criteria**:
- >80% unit test coverage
- All components have test files
- Integration tests cover happy path and error cases
- Performance tests validate 50+ directory handling

---

## Phase Execution Strategy

### Batch 1: Foundation (TASK-2.1)
**Parallelization**: Single task (foundation work)

**Task**: Extract directories from catalog
- Utility function for directory parsing
- Edge case handling
- Unit tests

**Token Estimate**: ~5K tokens

---

### Batch 2: Dialog Shell (TASK-2.2)
**Parallelization**: Single task (depends on Batch 1)

**Task**: Create BulkTagDialog component
- Dialog component structure
- Directory list rendering
- Basic UI layout
- Loading states

**Token Estimate**: ~12K tokens

---

### Batch 3: Tag Options (TASK-2.3)
**Parallelization**: Single task (depends on Batch 2)

**Task**: Implement directory tag options
- Manual tag input with autocomplete
- Path-based suggested tags
- Tag validation
- UI refinements

**Token Estimate**: ~10K tokens

---

### Batch 4: Application Logic (TASK-2.4)
**Parallelization**: Single task (depends on Batch 3)

**Task**: Implement tag application logic
- Bulk update logic
- Progress tracking
- Error handling
- Performance optimization

**Token Estimate**: ~8K tokens

---

### Batch 5: Integration & Testing (TASK-2.5, TASK-2.6)
**Parallelization**: 2 tasks in parallel (both ready after Batch 4)

**Tasks**:
1. Wire dialog to catalog toolbar
   - Toolbar button
   - Dialog integration
   - Success feedback
   - Catalog refresh

2. Unit and integration tests
   - Component tests
   - Utility tests
   - Integration scenarios
   - Performance tests

**Token Estimate**: ~6K tokens (combined)

---

## Success Metrics

- [ ] Dialog shows detected directories from artifact paths
- [ ] Each directory has manual Tags and Path-based Suggested Tags options
- [ ] Tags apply to all artifacts matching directory prefix
- [ ] Dialog handles 50+ directories without lag (<2s render time)
- [ ] Toast feedback shows updated artifact count
- [ ] >80% unit test coverage across all new code
- [ ] Integration tests pass for happy path and error scenarios
- [ ] No regressions in existing marketplace functionality

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance issues with large catalogs | Medium | High | Implement pagination, virtualization, or lazy loading in directory list |
| Path-based tag suggestions too generic | Low | Medium | Allow users to customize suggestion algorithm or hide suggestions |
| Tag merge conflicts (duplicate tags) | Low | Low | Deduplicate tags during merge, show conflict resolution UI |
| Bulk update fails mid-operation | Low | High | Implement transaction-like behavior with rollback on error |

---

## Notes

**Design Decisions**:
- Directory-based tagging chosen over individual artifact selection for efficiency
- Path-based suggestions optional (users can ignore and use manual tags only)
- Tags merged with existing tags (not replaced) to preserve user work

**Technical Constraints**:
- Dialog must handle 50+ directories (marketplace repo has ~60 directories)
- Tag application must complete in <5s for typical use cases
- UI must remain responsive during bulk updates

**Future Enhancements** (post-Phase 2):
- Save tag templates for common directory patterns
- Undo bulk tag application
- Export/import directory-tag mappings

---

## Context for AI Agents

**Architecture Context**:
- Frontend-only feature (no backend changes required)
- Uses existing marketplace catalog data structure
- Integrates with existing tag filtering (Phase 1)

**Key Files**:
- Catalog page: `skillmeat/web/app/marketplace/catalog/page.tsx`
- Catalog state: Local state in page component
- Tag rendering: Existing tag badge components

**Testing Requirements**:
- Jest + React Testing Library for component tests
- Mock marketplace catalog data for tests
- Performance benchmarks for 50+ directory scenario

**Related Work**:
- Phase 1 implemented tag filtering UI (dependency for this feature)
- Phase 3 will add multi-select for more granular control
