---
prd: path-based-tag-extraction-v1
phase: 3
name: "Import Integration & Polish"
status: pending
created: 2026-01-04
updated: 2026-01-04
completion: 0

tasks:
  - id: "TASK-3.1"
    name: "Update Import Request Schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: []
    estimated_effort: "0.5h"

  - id: "TASK-3.2"
    name: "Backend Import Logic"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "opus"
    dependencies: ["TASK-3.1"]
    estimated_effort: "2h"

  - id: "TASK-3.3"
    name: "Import UI Checkbox"
    status: "pending"
    assigned_to: ["ui-engineer"]
    model: "sonnet"
    dependencies: []
    estimated_effort: "0.5h"

  - id: "TASK-3.4"
    name: "Frontend State Management"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    model: "sonnet"
    dependencies: ["TASK-3.3"]
    estimated_effort: "1h"

  - id: "TASK-3.5"
    name: "Integration Tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    model: "sonnet"
    dependencies: ["TASK-3.2"]
    estimated_effort: "1.5h"

  - id: "TASK-3.6"
    name: "E2E Tests"
    status: "pending"
    assigned_to: ["ui-engineer"]
    model: "sonnet"
    dependencies: ["TASK-3.4", "TASK-3.5"]
    estimated_effort: "2h"

  - id: "TASK-3.7"
    name: "QA Workflow Testing"
    status: "pending"
    assigned_to: ["karen"]
    model: "sonnet"
    dependencies: ["TASK-3.6"]
    estimated_effort: "1.5h"

  - id: "TASK-3.8"
    name: "Documentation Update"
    status: "pending"
    assigned_to: ["documentation-writer"]
    model: "haiku"
    dependencies: ["TASK-3.7"]
    estimated_effort: "1h"

parallelization:
  batch_1: ["TASK-3.1", "TASK-3.3"]
  batch_2: ["TASK-3.2", "TASK-3.4"]
  batch_3: ["TASK-3.5"]
  batch_4: ["TASK-3.6"]
  batch_5: ["TASK-3.7"]
  batch_6: ["TASK-3.8"]
---

# Phase 3: Import Integration & Polish

## Overview

Integrate path-based tags into bulk import workflow, add "Apply Tags" option, and polish the end-to-end experience.

## Progress Summary

- **Total Tasks**: 8
- **Completed**: 0
- **In Progress**: 0
- **Blocked**: 0
- **Not Started**: 8

## Task Details

### Batch 1 (Parallel - Independent)

#### TASK-3.1: Update Import Request Schema
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 0.5h

Add optional `apply_path_tags` field to bulk import schema.

**Deliverables**:
- Update `skillmeat/api/schemas/marketplace.py`:
  - Add `apply_path_tags: bool = True` to `BulkImportRequest`
  - Document field behavior in docstring
- Default to `True` (apply tags by default)

#### TASK-3.3: Import UI Checkbox
**Status**: Pending
**Owner**: ui-engineer (sonnet)
**Effort**: 0.5h

Add checkbox to import modal for applying tags.

**Deliverables**:
- Update `skillmeat/web/components/marketplace/import-modal.tsx`:
  - Add checkbox: "Apply path-based tags"
  - Default checked
  - Tooltip: "Automatically tag artifacts based on source path structure"
- Use Radix UI Checkbox component

---

### Batch 2 (Parallel - After Batch 1)

#### TASK-3.2: Backend Import Logic
**Status**: Pending
**Owner**: python-backend-engineer (opus)
**Effort**: 2h
**Dependencies**: TASK-3.1

Implement tag application during bulk import.

**Deliverables**:
- Update `skillmeat/core/marketplace/import_service.py`:
  - If `apply_path_tags=True`:
    - Fetch `path_tags` from marketplace source
    - Apply segments as tags to imported artifact
    - Preserve existing tags (additive, no overwrite)
  - If `apply_path_tags=False`: Skip tag application
  - Log tag application (debug level)
- Handle missing path_tags gracefully (no-op)

#### TASK-3.4: Frontend State Management
**Status**: Pending
**Owner**: ui-engineer-enhanced (sonnet)
**Effort**: 1h
**Dependencies**: TASK-3.3

Wire checkbox state to import mutation.

**Deliverables**:
- Update `skillmeat/web/components/marketplace/import-modal.tsx`:
  - Add `applyPathTags` state (default true)
  - Pass to `useBulkImport()` mutation
- Update `skillmeat/web/hooks/use-bulk-import.ts`:
  - Accept `apply_path_tags` in mutation data
  - Pass to API client
- Update `skillmeat/web/lib/api/marketplace.ts`:
  - Include `apply_path_tags` in request body

---

### Batch 3 (Sequential - After Batch 2)

#### TASK-3.5: Integration Tests
**Status**: Pending
**Owner**: python-backend-engineer (sonnet)
**Effort**: 1.5h
**Dependencies**: TASK-3.2

Test import with tag application.

**Deliverables**:
- `tests/integration/test_import_with_tags.py`:
  - Test: Import with `apply_path_tags=True` → verify tags applied
  - Test: Import with `apply_path_tags=False` → verify tags NOT applied
  - Test: Import with missing path_tags → no error
  - Test: Import preserves existing tags (additive)
- Use test database

---

### Batch 4 (Sequential - After Batch 3)

#### TASK-3.6: E2E Tests
**Status**: Pending
**Owner**: ui-engineer (sonnet)
**Effort**: 2h
**Dependencies**: TASK-3.4, TASK-3.5

End-to-end workflow tests.

**Deliverables**:
- `skillmeat/web/e2e/marketplace-import-tags.spec.ts`:
  - Test: Full workflow (scan → review tags → apply on import)
  - Test: Uncheck "Apply tags" → verify tags not applied
  - Test: Edit tags → import → verify edited tags applied
  - Test: Skip tag review → import → verify auto-extracted tags applied
- Use Playwright or Cypress
- Mock backend responses

---

### Batch 5 (Sequential - After Batch 4)

#### TASK-3.7: QA Workflow Testing
**Status**: Pending
**Owner**: karen (sonnet)
**Effort**: 1.5h
**Dependencies**: TASK-3.6

Manual QA testing of complete feature.

**Deliverables**:
- Test scenarios:
  - Happy path: Scan → review → edit tags → import → verify tags in collection
  - Skip review: Scan → import → verify auto-tags applied
  - Disable tags: Scan → uncheck "Apply tags" → import → verify no tags
  - Edge cases: Missing path_tags, malformed paths
- Document findings in `.claude/worknotes/path-based-tag-extraction/qa-results.md`
- Report bugs if found

---

### Batch 6 (Sequential - After Batch 5)

#### TASK-3.8: Documentation Update
**Status**: Pending
**Owner**: documentation-writer (haiku)
**Effort**: 1h
**Dependencies**: TASK-3.7

Update user-facing documentation.

**Deliverables**:
- Update `docs/features/marketplace-import.md`:
  - Document tag review step
  - Document "Apply tags" checkbox
  - Include screenshots
- Update `docs/api/marketplace.md`:
  - Document `apply_path_tags` field
- Update `CHANGELOG.md`:
  - Add entry for path-based tag extraction feature

---

## Orchestration Quick Reference

### Batch 1 (Parallel)
```
Task("python-backend-engineer", "TASK-3.1: Add apply_path_tags: bool = True field to BulkImportRequest schema in skillmeat/api/schemas/marketplace.py. Document behavior in docstring.", model="sonnet")
Task("ui-engineer", "TASK-3.3: Add 'Apply path-based tags' checkbox to import modal in skillmeat/web/components/marketplace/import-modal.tsx. Default checked. Use Radix UI Checkbox. Add tooltip.", model="sonnet")
```

### Batch 2 (Parallel - After Batch 1)
```
Task("python-backend-engineer", "TASK-3.2: Implement tag application logic in skillmeat/core/marketplace/import_service.py. If apply_path_tags=True: fetch path_tags from source, apply to artifact, preserve existing. If False: skip. Handle missing path_tags. Log at debug level.", model="opus")
Task("ui-engineer-enhanced", "TASK-3.4: Wire checkbox state to import mutation. Update import-modal.tsx: add applyPathTags state. Update use-bulk-import.ts: accept apply_path_tags. Update lib/api/marketplace.ts: include in request body.", model="sonnet")
```

### Batch 3 (Sequential - After Batch 2)
```
Task("python-backend-engineer", "TASK-3.5: Write integration tests in tests/integration/test_import_with_tags.py. Test: apply_path_tags=True/False, missing path_tags, preserves existing tags. Use test DB.", model="sonnet")
```

### Batch 4 (Sequential - After Batch 3)
```
Task("ui-engineer", "TASK-3.6: Write E2E tests in skillmeat/web/e2e/marketplace-import-tags.spec.ts. Test: full workflow (scan→review→import), uncheck apply, edit tags, skip review. Use Playwright/Cypress. Mock backend.", model="sonnet")
```

### Batch 5 (Sequential - After Batch 4)
```
Task("karen", "TASK-3.7: Manual QA testing. Test: happy path (scan→review→edit→import), skip review, disable tags, edge cases. Document findings in .claude/worknotes/path-based-tag-extraction/qa-results.md. Report bugs.", model="sonnet")
```

### Batch 6 (Sequential - After Batch 5)
```
Task("documentation-writer", "TASK-3.8: Update docs: docs/features/marketplace-import.md (tag review step, checkbox, screenshots), docs/api/marketplace.md (apply_path_tags field), CHANGELOG.md (new feature entry).", model="haiku")
```

---

## Critical Files

### Backend
- `skillmeat/api/schemas/marketplace.py`
- `skillmeat/core/marketplace/import_service.py`

### Frontend
- `skillmeat/web/components/marketplace/import-modal.tsx`
- `skillmeat/web/hooks/use-bulk-import.ts`
- `skillmeat/web/lib/api/marketplace.ts`

### Tests
- `tests/integration/test_import_with_tags.py`
- `skillmeat/web/e2e/marketplace-import-tags.spec.ts`

### Documentation
- `docs/features/marketplace-import.md`
- `docs/api/marketplace.md`
- `CHANGELOG.md`
- `.claude/worknotes/path-based-tag-extraction/qa-results.md`

---

## Success Criteria

- [ ] Import request schema accepts `apply_path_tags` field
- [ ] Backend applies tags from path_tags when enabled
- [ ] Backend skips tag application when disabled
- [ ] UI checkbox controls tag application
- [ ] Integration tests verify tag application logic
- [ ] E2E tests verify full workflow
- [ ] QA testing passes (no critical bugs)
- [ ] Documentation updated with screenshots

---

## Notes

- Use Opus for complex logic (import service)
- Use Sonnet for most tasks (integration, UI wiring, tests)
- Use Haiku for documentation
- Default `apply_path_tags=True` for convenience
- Tag application is additive (preserves existing tags)
- Handle missing path_tags gracefully (no-op, no error)
