---
prd: path-based-tag-extraction-v1
phase: 2
name: Frontend UI Components
status: pending
created: 2026-01-04
updated: 2026-01-04
completion: 0
tasks:
- id: TASK-2.1
  name: API Client Functions
  status: pending
  assigned_to:
  - ui-engineer
  model: sonnet
  dependencies: []
  estimated_effort: 1h
- id: TASK-2.2
  name: Type Definitions
  status: pending
  assigned_to:
  - ui-engineer
  model: haiku
  dependencies: []
  estimated_effort: 0.5h
- id: TASK-2.3
  name: React Query Hooks
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  model: opus
  dependencies:
  - TASK-2.1
  - TASK-2.2
  estimated_effort: 1.5h
- id: TASK-2.4
  name: PathTagReview Component
  status: pending
  assigned_to:
  - ui-engineer-enhanced
  model: opus
  dependencies:
  - TASK-2.3
  estimated_effort: 3h
- id: TASK-2.5
  name: Modal Integration
  status: pending
  assigned_to:
  - ui-engineer
  model: sonnet
  dependencies:
  - TASK-2.4
  estimated_effort: 1h
- id: TASK-2.6
  name: Accessibility Audit
  status: pending
  assigned_to:
  - a11y-sheriff
  model: sonnet
  dependencies:
  - TASK-2.4
  estimated_effort: 1h
- id: TASK-2.7
  name: E2E Tests
  status: pending
  assigned_to:
  - ui-engineer
  model: sonnet
  dependencies:
  - TASK-2.5
  estimated_effort: 2h
- id: TASK-2.8
  name: Unit Tests
  status: pending
  assigned_to:
  - ui-engineer
  model: sonnet
  dependencies:
  - TASK-2.4
  estimated_effort: 1.5h
parallelization:
  batch_1:
  - TASK-2.1
  - TASK-2.2
  batch_2:
  - TASK-2.3
  batch_3:
  - TASK-2.4
  batch_4:
  - TASK-2.5
  - TASK-2.6
  - TASK-2.8
  batch_5:
  - TASK-2.7
schema_version: 2
doc_type: progress
feature_slug: path-based-tag-extraction-v1
type: progress
---

# Phase 2: Frontend UI Components

## Overview

Build React components for reviewing and editing path-based tags during marketplace import workflow.

## Progress Summary

- **Total Tasks**: 8
- **Completed**: 0
- **In Progress**: 0
- **Blocked**: 0
- **Not Started**: 8

## Task Details

### Batch 1 (Parallel - Independent)

#### TASK-2.1: API Client Functions
**Status**: Pending
**Owner**: ui-engineer (sonnet)
**Effort**: 1h

Create API client functions for path tags endpoints.

**Deliverables**:
- `skillmeat/web/lib/api/marketplace.ts` updates:
  - `fetchPathTags(sourceId: string): Promise<PathTagsResponse>`
  - `updatePathTags(sourceId: string, data: PathTagsPatchRequest): Promise<PathTagsResponse>`
- Use `buildUrl()` helper
- Standard error handling (extract `detail` from backend)
- Follow `.claude/rules/web/api-client.md` patterns

#### TASK-2.2: Type Definitions
**Status**: Pending
**Owner**: ui-engineer (haiku)
**Effort**: 0.5h

Define TypeScript types for path tags.

**Deliverables**:
- `skillmeat/web/types/marketplace.ts` updates:
  - `PathTagSegment` type (value, segment_type, original_value)
  - `PathTagsResponse` type (source_id, path, segments)
  - `PathTagsPatchRequest` type (tag_overrides)
- Match backend Pydantic schemas exactly

---

### Batch 2 (Sequential - After Batch 1)

#### TASK-2.3: React Query Hooks
**Status**: Pending
**Owner**: ui-engineer-enhanced (opus)
**Effort**: 1.5h
**Dependencies**: TASK-2.1, TASK-2.2

Create TanStack Query hooks for path tags.

**Deliverables**:
- `skillmeat/web/hooks/use-path-tags.ts`:
  - `usePathTags(sourceId: string)` query hook
  - `useUpdatePathTags()` mutation hook
  - Query key factory: `pathTagKeys`
  - Cache invalidation on update
- Follow `.claude/rules/web/hooks.md` patterns
- Proper error handling (ApiError)

---

### Batch 3 (Sequential - After Batch 2)

#### TASK-2.4: PathTagReview Component
**Status**: Pending
**Owner**: ui-engineer-enhanced (opus)
**Effort**: 3h
**Dependencies**: TASK-2.3

Build main component for reviewing/editing path tags.

**Deliverables**:
- `skillmeat/web/components/marketplace/path-tag-review.tsx`:
  - Display segments grouped by type (org, repo, category, skill-name)
  - Inline editing (text input per segment)
  - Reset to auto-extracted values
  - Save button (calls mutation)
  - Loading/error states
  - Radix UI components (Table, Input, Button)
- Props: `sourceId: string`, `onSave?: () => void`
- Accessible (keyboard navigation, ARIA labels)

---

### Batch 4 (Parallel - After Batch 3)

#### TASK-2.5: Modal Integration
**Status**: Pending
**Owner**: ui-engineer (sonnet)
**Effort**: 1h
**Dependencies**: TASK-2.4

Integrate PathTagReview into import workflow modal.

**Deliverables**:
- Update `skillmeat/web/components/marketplace/import-modal.tsx`:
  - Add "Review Tags" step (after URL entry, before final import)
  - Render `PathTagReview` component
  - Pass `sourceId` from scan result
  - Handle save → proceed to import
  - Skip button (use auto-extracted tags)
- Update stepper UI (3 steps: URL, Tags, Confirm)

#### TASK-2.6: Accessibility Audit
**Status**: Pending
**Owner**: a11y-sheriff (sonnet)
**Effort**: 1h
**Dependencies**: TASK-2.4

Audit PathTagReview component for accessibility.

**Deliverables**:
- Check keyboard navigation (tab order, focus management)
- Verify ARIA labels (inputs, buttons, status messages)
- Test screen reader compatibility
- Ensure color contrast meets WCAG AA
- Document findings in `docs/accessibility/path-tag-review.md`
- Fix critical issues

#### TASK-2.8: Unit Tests
**Status**: Pending
**Owner**: ui-engineer (sonnet)
**Effort**: 1.5h
**Dependencies**: TASK-2.4

Write unit tests for PathTagReview component.

**Deliverables**:
- `skillmeat/web/components/marketplace/__tests__/path-tag-review.test.tsx`:
  - Test: Renders segments correctly
  - Test: Inline editing updates state
  - Test: Reset button restores original values
  - Test: Save button calls mutation
  - Test: Loading state displayed
  - Test: Error state displayed
- Use `@testing-library/react`
- Mock `usePathTags` and `useUpdatePathTags` hooks

---

### Batch 5 (Sequential - After Batch 4)

#### TASK-2.7: E2E Tests
**Status**: Pending
**Owner**: ui-engineer (sonnet)
**Effort**: 2h
**Dependencies**: TASK-2.5

Write end-to-end tests for tag review workflow.

**Deliverables**:
- `skillmeat/web/e2e/marketplace-tag-review.spec.ts`:
  - Test: Open import modal → scan URL → review tags step appears
  - Test: Edit segment → save → verify API call
  - Test: Reset segment → verify original value restored
  - Test: Skip review → proceed to import
- Use Playwright or Cypress
- Mock backend responses

---

## Orchestration Quick Reference

### Batch 1 (Parallel)
```
Task("ui-engineer", "TASK-2.1: Create API client functions in skillmeat/web/lib/api/marketplace.ts: fetchPathTags(sourceId) and updatePathTags(sourceId, data). Use buildUrl() helper, standard error handling. Follow .claude/rules/web/api-client.md patterns.", model="sonnet")
Task("ui-engineer", "TASK-2.2: Define TypeScript types in skillmeat/web/types/marketplace.ts: PathTagSegment, PathTagsResponse, PathTagsPatchRequest. Match backend Pydantic schemas.", model="haiku")
```

### Batch 2 (Sequential - After Batch 1)
```
Task("ui-engineer-enhanced", "TASK-2.3: Create React Query hooks in skillmeat/web/hooks/use-path-tags.ts: usePathTags(sourceId) query, useUpdatePathTags() mutation, pathTagKeys factory. Cache invalidation on update. Follow .claude/rules/web/hooks.md patterns.", model="opus")
```

### Batch 3 (Sequential - After Batch 2)
```
Task("ui-engineer-enhanced", "TASK-2.4: Build PathTagReview component in skillmeat/web/components/marketplace/path-tag-review.tsx. Display segments grouped by type, inline editing, reset button, save button. Use Radix UI. Props: sourceId, onSave. Accessible (keyboard, ARIA).", model="opus")
```

### Batch 4 (Parallel - After Batch 3)
```
Task("ui-engineer", "TASK-2.5: Integrate PathTagReview into skillmeat/web/components/marketplace/import-modal.tsx. Add 'Review Tags' step (after URL scan, before import). Pass sourceId, handle save→proceed. Add skip button. Update stepper (3 steps).", model="sonnet")
Task("a11y-sheriff", "TASK-2.6: Audit PathTagReview component for accessibility. Check keyboard nav, ARIA labels, screen reader compat, color contrast (WCAG AA). Document findings in docs/accessibility/path-tag-review.md. Fix critical issues.", model="sonnet")
Task("ui-engineer", "TASK-2.8: Write unit tests for PathTagReview in skillmeat/web/components/marketplace/__tests__/path-tag-review.test.tsx. Test: renders, editing, reset, save, loading, error. Use @testing-library/react. Mock hooks.", model="sonnet")
```

### Batch 5 (Sequential - After Batch 4)
```
Task("ui-engineer", "TASK-2.7: Write E2E tests in skillmeat/web/e2e/marketplace-tag-review.spec.ts. Test: modal→scan→review step, edit→save, reset, skip. Use Playwright or Cypress. Mock backend.", model="sonnet")
```

---

## Critical Files

### API Layer
- `skillmeat/web/lib/api/marketplace.ts`
- `skillmeat/web/types/marketplace.ts`

### Hooks
- `skillmeat/web/hooks/use-path-tags.ts`

### Components
- `skillmeat/web/components/marketplace/path-tag-review.tsx`
- `skillmeat/web/components/marketplace/import-modal.tsx`

### Tests
- `skillmeat/web/components/marketplace/__tests__/path-tag-review.test.tsx`
- `skillmeat/web/e2e/marketplace-tag-review.spec.ts`

### Documentation
- `docs/accessibility/path-tag-review.md`

---

## Success Criteria

- [ ] API client functions call correct endpoints
- [ ] TypeScript types match backend schemas
- [ ] React Query hooks manage cache correctly
- [ ] PathTagReview component renders and allows editing
- [ ] Modal integration adds review step to workflow
- [ ] Component passes accessibility audit
- [ ] Unit tests pass (>80% coverage)
- [ ] E2E tests pass (full workflow)

---

## Notes

- Use Opus for complex UI logic (hooks, main component)
- Use Sonnet for integration and tests
- Use Haiku for simple type definitions
- Follow existing patterns in `.claude/rules/web/` directory
- Radix UI for accessible primitives (Table, Input, Button)
- TanStack Query v5 for data fetching/mutations
