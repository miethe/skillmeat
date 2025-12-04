---
type: progress
prd: "discovery-import-enhancement"
phase: 3
title: "Frontend - Type Updates & Form Integration"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 11
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["frontend-developer", "ui-engineer-enhanced"]
contributors: ["testing-specialist"]

tasks:
  - id: "DIS-3.1"
    description: "Update discovery.ts types - change ImportResult.success:boolean to status enum (success|skipped|failed)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "critical"

  - id: "DIS-3.2"
    description: "Add SkipPreference type interface with project_id, artifact_key, skip_reason, added_date"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "high"

  - id: "DIS-3.3"
    description: "Update BulkImportModal status display labels - show pre-scan status for each artifact"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-3.1"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.4"
    description: "Add skip checkbox UI to BulkImportModal with accessibility labels and tooltips"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-3.1"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.5"
    description: "Implement LocalStorage skip preference persistence utilities with project_id namespacing"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["DIS-3.2"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.6"
    description: "Update useProjectDiscovery hook to integrate skip preference loading and saving"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["DIS-3.5"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.7"
    description: "Update import form submission to collect skip list and send in request"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["DIS-3.6"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.8"
    description: "Unit tests for TypeScript type updates - verify types compile and match backend"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-3.1", "DIS-3.2"]
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-3.9"
    description: "Unit tests for LocalStorage skip persistence - save/load/clear operations"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-3.5"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.10"
    description: "Unit tests for BulkImportModal - skip checkboxes, status display, form submission"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["DIS-3.3", "DIS-3.4", "DIS-3.7"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-3.11"
    description: "E2E test for skip preference persistence - checkbox check → reload → skips remain"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-3.5", "DIS-3.9"]
    estimated_effort: "1d"
    priority: "medium"

parallelization:
  batch_1: ["DIS-3.1", "DIS-3.2"]
  batch_2: ["DIS-3.3", "DIS-3.4", "DIS-3.5"]
  batch_3: ["DIS-3.6", "DIS-3.7"]
  batch_4: ["DIS-3.8", "DIS-3.9", "DIS-3.10"]
  batch_5: ["DIS-3.11"]
  critical_path: ["DIS-3.1", "DIS-3.5", "DIS-3.6", "DIS-3.7", "DIS-3.10"]
  estimated_total_time: "6-7 days"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "All ImportResult TypeScript usages compile without errors"
    status: "pending"
  - id: "SC-2"
    description: "Status enum values match backend (success, skipped, failed)"
    status: "pending"
  - id: "SC-3"
    description: "Skip preference types defined and exported"
    status: "pending"
  - id: "SC-4"
    description: "BulkImportModal renders status labels correctly"
    status: "pending"
  - id: "SC-5"
    description: "Skip checkboxes render and manage state"
    status: "pending"
  - id: "SC-6"
    description: "LocalStorage skip persistence working (save/load/clear)"
    status: "pending"
  - id: "SC-7"
    description: "Form submission includes skip_list in request"
    status: "pending"
  - id: "SC-8"
    description: "Unit test coverage >80%"
    status: "pending"
  - id: "SC-9"
    description: "E2E test passes: skip checkbox → page reload → skips persist"
    status: "pending"
  - id: "SC-10"
    description: "Accessibility: skip checkboxes labeled, screen reader compatible"
    status: "pending"

files_modified:
  - "skillmeat/web/types/discovery.ts"
  - "skillmeat/web/components/discovery/BulkImportModal.tsx"
  - "skillmeat/web/lib/skip-preferences.ts"
  - "skillmeat/web/hooks/useProjectDiscovery.ts"
  - "skillmeat/web/__tests__/discovery-types.test.ts"
  - "skillmeat/web/__tests__/skip-preferences.test.ts"
  - "skillmeat/web/__tests__/BulkImportModal.test.tsx"
---

# Discovery & Import Enhancement - Phase 3: Frontend - Type Updates & Form Integration

**Phase**: 3 of 6
**Status**: 📋 Planning (0% complete)
**Duration**: Estimated 2-3 days (Parallel with Phase 2)
**Owner**: frontend-developer, ui-engineer-enhanced
**Contributors**: testing-specialist
**Dependency**: Phase 1 ✓ Complete

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Launch Phase 3 in parallel with Phase 2 after Phase 1 completes. Frontend can use mocked Phase 2 API endpoints.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- DIS-3.1 → `frontend-developer` (0.5d) - Update ImportResult types
- DIS-3.2 → `frontend-developer` (0.5d) - Add SkipPreference type

**Batch 2** (Parallel - Depends on Batch 1):
- DIS-3.3 → `ui-engineer-enhanced` (1d) - Status display labels (depends on DIS-3.1)
- DIS-3.4 → `ui-engineer-enhanced` (1d) - Skip checkbox UI (depends on DIS-3.1)
- DIS-3.5 → `frontend-developer` (1d) - LocalStorage persistence (depends on DIS-3.2)

**Batch 3** (Parallel - Depends on Batch 2):
- DIS-3.6 → `frontend-developer` (1d) - useProjectDiscovery hook (depends on DIS-3.5)
- DIS-3.7 → `frontend-developer` (1d) - Form submission (depends on DIS-3.6)

**Batch 4** (Parallel - Depends on Batch 3):
- DIS-3.8 → `testing-specialist` (0.5d) - Type tests (depends on DIS-3.1, DIS-3.2)
- DIS-3.9 → `testing-specialist` (1d) - LocalStorage tests (depends on DIS-3.5)
- DIS-3.10 → `ui-engineer-enhanced` (1d) - BulkImportModal tests (depends on DIS-3.3, DIS-3.4, DIS-3.7)

**Batch 5** (Sequential - Depends on Batch 4):
- DIS-3.11 → `testing-specialist` (1d) - E2E skip persistence test

**Critical Path**: DIS-3.1 → DIS-3.5 → DIS-3.6 → DIS-3.7 → DIS-3.10 (6-7 days total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel after Phase 1 completes)
Task("frontend-developer", "DIS-3.1: Update discovery.ts types - change ImportResult.success:boolean to status enum. File: skillmeat/web/types/discovery.ts. Change: status: 'success' | 'skipped' | 'failed'. Add: skip_reason?: string. Acceptance: (1) TypeScript compiles; (2) All ImportResult usages updated; (3) Backward compat documented; (4) Types match backend schema")

Task("frontend-developer", "DIS-3.2: Add SkipPreference type interface. File: skillmeat/web/types/discovery.ts. Export: SkipPreference interface with project_id, artifact_key, skip_reason, added_date. Acceptance: (1) Type exported; (2) Used in hooks; (3) JSON serializable")

# Batch 2 (After Batch 1 completes)
Task("ui-engineer-enhanced", "DIS-3.3: Update BulkImportModal status display. File: skillmeat/web/components/discovery/BulkImportModal.tsx. Display status labels: 'Will add to Collection', 'Already in Collection', 'Skipped'. Add color-coded badges and tooltips. Acceptance: (1) Labels render; (2) Tooltips explain; (3) Color-coded; (4) Responsive")

Task("ui-engineer-enhanced", "DIS-3.4: Add skip checkbox UI to BulkImportModal. File: skillmeat/web/components/discovery/BulkImportModal.tsx. Per-artifact checkbox: 'Don't show in future discoveries'. Acceptance: (1) Checkboxes render; (2) State managed; (3) Labels and tooltips; (4) Accessibility: proper labels, screen reader support")

Task("frontend-developer", "DIS-3.5: Implement LocalStorage skip persistence utilities. File: skillmeat/web/lib/skip-preferences.ts (new). Functions: saveSkipPrefs(projectId, skipList), loadSkipPrefs(projectId), clearSkipPrefs(projectId, artifact_key?). Acceptance: (1) JSON serialization; (2) Key namespacing: skillmeat_skip_prefs_{project_id}; (3) Handles unavailability; (4) Type-safe; (5) Unit tests")

# Batch 3 (After Batch 2 completes)
Task("frontend-developer", "DIS-3.6: Update useProjectDiscovery hook for skip preferences. File: skillmeat/web/hooks/useProjectDiscovery.ts. Integrate: load skips on mount, apply to form, save on import. Acceptance: (1) Hook reads LocalStorage on mount; (2) Provides skip state; (3) Provides save/clear functions; (4) Tests pass")

Task("frontend-developer", "DIS-3.7: Update import form submission to collect skip list. File: skillmeat/web/components/discovery/BulkImportModal.tsx. Collect artifact keys marked to skip; send as skip_list in POST request. Acceptance: (1) Form collects skip list; (2) Skip list in request body; (3) Error handling; (4) Tests pass")

# Batch 4 (After Batch 3 completes)
Task("testing-specialist", "DIS-3.8: Unit tests for TypeScript types. File: skillmeat/web/__tests__/discovery-types.test.ts (new). Test: types compile, type guards work, type narrowing correct. Acceptance: (1) No TypeScript errors; (2) Type guards working; (3) Type narrowing correct")

Task("testing-specialist", "DIS-3.9: Unit tests for LocalStorage skip persistence. File: skillmeat/web/__tests__/skip-preferences.test.ts (new). Test: save/load/clear operations, unavailability handling. Acceptance: (1) Save writes JSON; (2) Load deserializes; (3) Clear removes keys; (4) Unavailability doesn't crash; (5) Coverage >80%")

Task("ui-engineer-enhanced", "DIS-3.10: Unit tests for BulkImportModal. File: skillmeat/web/__tests__/BulkImportModal.test.tsx (update). Test: skip checkbox state, form submission with skip list, status display. Acceptance: (1) Checkboxes toggle; (2) Form includes skip_list; (3) Status labels display; (4) Accessibility tests pass; (5) Coverage >80%")

# Batch 5 (After Batch 4 completes)
Task("testing-specialist", "DIS-3.11: E2E test for skip preference persistence. File: skillmeat/web/__tests__/e2e/skip-persistence.spec.ts (new). Test: check skip checkbox → reload page → skip preferences remain. Acceptance: (1) Check checkbox; (2) Reload; (3) Verify skip in state; (4) Verify localStorage key exists")
```

---

## Overview

**Phase 3** updates the frontend TypeScript types to match the new import status enum from Phase 1, implements skip preference UI in the BulkImportModal with per-artifact checkboxes, and adds LocalStorage persistence for skip preferences across browser sessions.

**Why This Phase**: Phase 1 changes the backend data model; Phase 3 ensures the frontend reflects those changes and introduces the skip preference feature. This phase runs in parallel with Phase 2, with frontend mocking Phase 2's API endpoints until they're ready.

**Scope**:
- **IN**: Type updates, skip checkbox UI, LocalStorage persistence, form integration, frontend tests
- **OUT**: Discovery Tab component (Phase 4), API endpoint implementation (Phase 2), Notification System integration (Phase 5)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | All ImportResult TypeScript usages compile without errors | ⏳ Pending |
| SC-2 | Status enum values match backend (success, skipped, failed) | ⏳ Pending |
| SC-3 | Skip preference types defined and exported | ⏳ Pending |
| SC-4 | BulkImportModal renders status labels correctly | ⏳ Pending |
| SC-5 | Skip checkboxes render and manage state | ⏳ Pending |
| SC-6 | LocalStorage skip persistence working (save/load/clear) | ⏳ Pending |
| SC-7 | Form submission includes skip_list in request | ⏳ Pending |
| SC-8 | Unit test coverage >80% | ⏳ Pending |
| SC-9 | E2E test passes: skip checkbox → page reload → skips persist | ⏳ Pending |
| SC-10 | Accessibility: skip checkboxes labeled, screen reader compatible | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| DIS-3.1 | Update discovery.ts types | ⏳ | frontend-developer | None | 0.5d | status enum + skip_reason |
| DIS-3.2 | Add SkipPreference type | ⏳ | frontend-developer | None | 0.5d | Type interface |
| DIS-3.3 | Update BulkImportModal status display | ⏳ | ui-engineer-enhanced | DIS-3.1 | 1d | Labels + badges |
| DIS-3.4 | Add skip checkbox UI | ⏳ | ui-engineer-enhanced | DIS-3.1 | 1d | Per-artifact checkboxes |
| DIS-3.5 | Implement LocalStorage persistence | ⏳ | frontend-developer | DIS-3.2 | 1d | Save/load/clear utils |
| DIS-3.6 | Update useProjectDiscovery hook | ⏳ | frontend-developer | DIS-3.5 | 1d | Load/save on mount/import |
| DIS-3.7 | Update form submission | ⏳ | frontend-developer | DIS-3.6 | 1d | Collect & send skip list |
| DIS-3.8 | Unit tests - types | ⏳ | testing-specialist | DIS-3.1, DIS-3.2 | 0.5d | Type compilation |
| DIS-3.9 | Unit tests - LocalStorage | ⏳ | testing-specialist | DIS-3.5 | 1d | Persistence operations |
| DIS-3.10 | Unit tests - BulkImportModal | ⏳ | ui-engineer-enhanced | DIS-3.3, DIS-3.4, DIS-3.7 | 1d | Checkboxes, status, form |
| DIS-3.11 | E2E test - skip persistence | ⏳ | testing-specialist | DIS-3.5, DIS-3.9 | 1d | Checkbox → reload |

---

## Architecture Context

### Current State

Frontend discovery types use generic success/failure structure. No skip preference system exists on frontend. BulkImportModal displays basic artifact list without pre-scan status information.

**Key Files**:
- `skillmeat/web/types/discovery.ts` - Current ImportResult type
- `skillmeat/web/components/discovery/BulkImportModal.tsx` - Current import UI
- `skillmeat/web/hooks/useProjectDiscovery.ts` - Discovery hook

### Reference Patterns

LocalStorage patterns in codebase:
- Project preferences stored in LocalStorage (reference pattern for project scoping)
- JSON serialization/deserialization (use existing utility functions)

---

## Implementation Details

### Technical Approach

1. **Type Updates (DIS-3.1, DIS-3.2)**:
   - Create import status union type: `type ImportStatus = 'success' | 'skipped' | 'failed'`
   - Update ImportResult: `status: ImportStatus, skip_reason?: string`
   - Create SkipPreference interface with project_id, artifact_key, skip_reason, added_date

2. **Status Display (DIS-3.3)**:
   - Add status column to BulkImportModal artifact table
   - Color-code badges: green (success), yellow (skipped), red (failed)
   - Add tooltips explaining each status

3. **Skip Checkbox (DIS-3.4)**:
   - Add checkbox per artifact: "Don't show in future discoveries"
   - Disabled if artifact status is "skipped" (already marked)
   - Manage checked state in component state
   - Proper `<label>` association for accessibility

4. **LocalStorage Persistence (DIS-3.5)**:
   - Create `skip-preferences.ts` utility module
   - Functions:
     - `saveSkipPrefs(projectId: string, skipList: string[]): void`
     - `loadSkipPrefs(projectId: string): string[]`
     - `clearSkipPrefs(projectId: string, artifactKey?: string): void`
   - Key format: `skillmeat_skip_prefs_{projectId}`
   - Handle localStorage unavailable (wrap in try-catch)

5. **Hook Integration (DIS-3.6, DIS-3.7)**:
   - Update useProjectDiscovery to:
     - Load skip prefs on mount from LocalStorage
     - Apply skip list to form initial state
     - Save skip prefs after successful import
     - Provide skip state and update functions
   - Update form submission to collect checked skip boxes and include in request

### Known Gotchas

- **LocalStorage Unavailable**: Private browsing, quota exceeded → gracefully fallback (no skip persistence)
- **Type Breaking Change**: ImportResult.success no longer exists → update all type guards
- **Accessibility**: Skip checkboxes must have proper labels for screen readers
- **Private Browsing**: LocalStorage might throw errors in private mode → catch and suppress silently

### Development Setup

- Test fixtures with sample artifacts and skip preferences
- LocalStorage mocking for tests (jest.mock or similar)
- Browser testing for LocalStorage functionality (use E2E test)

---

## Blockers

### Active Blockers

- **Phase 1 Dependency**: Awaiting Phase 1 completion (type definitions)
- **Phase 2 API Endpoints**: Phase 3 can mock these until Phase 2 is ready

---

## Dependencies

### External Dependencies

- **Phase 1 Complete**: ImportResult schema and status enum definition
- **Phase 2 Running in Parallel**: Skip preference API endpoints (can be mocked)

### Internal Integration Points

- **BulkImportModal** - Renders status labels, skip checkboxes
- **useProjectDiscovery Hook** - Manages skip preference state
- **API Client** - Calls discovery and import endpoints with skip list

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit - Types | Type compilation, guards, narrowing | N/A | ⏳ |
| Unit - LocalStorage | Save/load/clear operations, unavailability | 80%+ | ⏳ |
| Unit - BulkImportModal | Skip checkboxes, status display, form submission | 80%+ | ⏳ |
| E2E - Skip Persistence | Checkbox → reload → skips remain | Happy path | ⏳ |
| Accessibility | Checkbox labels, screen reader support | Interactive elements | ⏳ |

---

## Next Session Agenda

### Immediate Actions (Next Session - After Phase 1 Complete)
1. [ ] Launch Batch 1: Start DIS-3.1 and DIS-3.2 (type definitions)
2. [ ] Setup LocalStorage test fixtures
3. [ ] Create mock API responses for Phase 2 endpoints
4. [ ] Coordinate with Phase 2 team on skip preference API design (DIS-2.1)

### Upcoming Critical Items

- **Day 1-2**: Batch 2 completion (status display + skip checkbox)
- **Day 2-3**: Batch 3 completes (LocalStorage + hook integration)
- **Day 4**: Batch 4 starts (unit tests)
- **Day 5**: Quality gate check - all tests passing, LocalStorage verified

### Context for Continuing Agent

Phase 3 runs in parallel with Phase 2. Key coordination:
1. DIS-3.1 (type updates) is on critical path and should start immediately
2. DIS-3.5 (LocalStorage) can proceed with mocked API while Phase 2 implements endpoints
3. Skip preference API can be temporarily mocked in DIS-3.5/DIS-3.6 tests
4. When Phase 2 endpoints are ready, integration tests will verify they match mocked behavior

---

## Session Notes

*None yet - Phase 3 not started*

---

## Additional Resources

- **Phase 1 Results**: ImportResult enum schema, pre-scan logic
- **Phase 2 API Design**: Skip preference schema from DIS-2.1 (needed for mocking)
- **BulkImportModal Component**: Current implementation to extend
- **LocalStorage Patterns**: Existing project preference storage in codebase
