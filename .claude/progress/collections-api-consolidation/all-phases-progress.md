---
type: progress
prd: collections-api-consolidation
status: not_started
progress: 0
total_tasks: 21
completed_tasks: 0
tasks:
- id: TASK-1.1
  title: Add GET /user-collections/{id}/artifacts endpoint
  status: pending
  estimate: 3 SP
  assigned_to:
  - python-backend-engineer
  dependencies: []
  phase: 1
- id: TASK-1.2
  title: Update user_collections schema
  status: pending
  estimate: 1 SP
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.1
  phase: 1
- id: TASK-1.3
  title: Add copy artifact endpoint (optional)
  status: pending
  estimate: 2 SP
  assigned_to:
  - python-backend-engineer
  dependencies: []
  phase: 1
- id: TASK-1.4
  title: Add move artifact endpoint (optional)
  status: pending
  estimate: 2 SP
  assigned_to:
  - python-backend-engineer
  dependencies:
  - TASK-1.3
  phase: 1
- id: TASK-2.1
  title: Refactor fetchCollections()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.2
  title: Refactor fetchCollection(id)
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.3
  title: Fix updateCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.4
  title: Fix deleteCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.5
  title: Fix addArtifactToCollection()
  status: pending
  estimate: 2 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.6
  title: Fix removeArtifactFromCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.7
  title: Update copy/move or remove stubs
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-2.8
  title: Update TypeScript types
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies: []
  phase: 2
- id: TASK-3.1
  title: Update useCollections() hook
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies:
  - TASK-2.1
  phase: 3
- id: TASK-3.2
  title: Update useCollection(id) hook
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies:
  - TASK-2.2
  phase: 3
- id: TASK-3.3
  title: Implement useUpdateCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies:
  - TASK-2.3
  phase: 3
- id: TASK-3.4
  title: Implement useDeleteCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies:
  - TASK-2.4
  phase: 3
- id: TASK-3.5
  title: Implement useAddArtifactToCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies:
  - TASK-2.5
  phase: 3
- id: TASK-3.6
  title: Implement useRemoveArtifactFromCollection()
  status: pending
  estimate: 1 SP
  assigned_to:
  - ui-engineer-enhanced
  - frontend-developer
  dependencies:
  - TASK-2.6
  phase: 3
- id: TASK-5.1
  title: Add deprecation warnings to old endpoints
  status: pending
  estimate: 1 SP
  assigned_to:
  - python-backend-engineer
  dependencies: []
  phase: 5
- id: TASK-5.2
  title: Update API documentation
  status: pending
  estimate: 1 SP
  assigned_to:
  - documentation-writer
  dependencies: []
  phase: 5
- id: TASK-5.3
  title: Add removal timeline and migration guide
  status: pending
  estimate: 0.5 SP
  assigned_to:
  - documentation-writer
  dependencies: []
  phase: 5
parallelization:
  batch_1:
  - TASK-1.1
  - TASK-1.2
  - TASK-1.3
  - TASK-1.4
  batch_2:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.3
  - TASK-2.4
  - TASK-2.5
  - TASK-2.6
  - TASK-2.7
  - TASK-2.8
  batch_3:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.3
  - TASK-3.4
  - TASK-3.5
  - TASK-3.6
  batch_4:
  - TASK-5.1
  - TASK-5.2
  - TASK-5.3
schema_version: 2
doc_type: progress
feature_slug: collections-api-consolidation
---

# Collections API Consolidation Progress

**Status**: Not Started
**Progress**: 0/21 tasks completed (0%)
**Total Estimate**: 30 SP

## Overview

This refactoring consolidates the fragmented collections API across the backend and frontend into a cohesive, single-source-of-truth implementation. The work is organized into sequential phases with parallelized task batches.

### Phase Summary

| Phase | Name | Tasks | Estimate | Status |
|-------|------|-------|----------|--------|
| 1 | Backend API Gap Filling | 4 | 8 SP | pending |
| 2 | Frontend API Client | 8 | 9 SP | pending |
| 3 | Frontend Hooks | 6 | 6 SP | pending |
| 5 | Deprecation & Cleanup | 3 | 3 SP | pending |

## Orchestration Quick Reference

### Batch 1: Backend API (Phase 1) - Sequential
- TASK-1.1: Add GET /user-collections/{id}/artifacts endpoint (3 SP)
- TASK-1.2: Update user_collections schema (1 SP) - depends on TASK-1.1
- TASK-1.3: Add copy artifact endpoint (2 SP)
- TASK-1.4: Add move artifact endpoint (2 SP) - depends on TASK-1.3

### Batch 2: Frontend API Client (Phase 2) - Parallel
- TASK-2.1: Refactor fetchCollections() (1 SP)
- TASK-2.2: Refactor fetchCollection(id) (1 SP)
- TASK-2.3: Fix updateCollection() (1 SP)
- TASK-2.4: Fix deleteCollection() (1 SP)
- TASK-2.5: Fix addArtifactToCollection() (2 SP)
- TASK-2.6: Fix removeArtifactFromCollection() (1 SP)
- TASK-2.7: Update copy/move or remove stubs (1 SP)
- TASK-2.8: Update TypeScript types (1 SP)

### Batch 3: Frontend Hooks (Phase 3) - Parallel
- TASK-3.1: Update useCollections() hook (1 SP) - depends on TASK-2.1
- TASK-3.2: Update useCollection(id) hook (1 SP) - depends on TASK-2.2
- TASK-3.3: Implement useUpdateCollection() (1 SP) - depends on TASK-2.3
- TASK-3.4: Implement useDeleteCollection() (1 SP) - depends on TASK-2.4
- TASK-3.5: Implement useAddArtifactToCollection() (1 SP) - depends on TASK-2.5
- TASK-3.6: Implement useRemoveArtifactFromCollection() (1 SP) - depends on TASK-2.6

### Batch 4: Deprecation & Cleanup (Phase 5) - Parallel
- TASK-5.1: Add deprecation warnings to old endpoints (1 SP)
- TASK-5.2: Update API documentation (1 SP)
- TASK-5.3: Add removal timeline and migration guide (0.5 SP)

## Task Delegation Commands

### Execute Batch 1
```
Task("python-backend-engineer", "TASK-1.1: Add GET /user-collections/{id}/artifacts endpoint (3 SP)
File: skillmeat/api/app/routers/user_collections.py
Add endpoint that returns artifacts within a specific collection.
Ensure proper pagination and filtering support.")

Task("python-backend-engineer", "TASK-1.2: Update user_collections schema (1 SP)
File: skillmeat/api/app/schemas/user_collections.py
Update schema to support the new artifacts endpoint response format.
Depends on: TASK-1.1")

Task("python-backend-engineer", "TASK-1.3: Add copy artifact endpoint (optional) (2 SP)
File: skillmeat/api/app/routers/user_collections.py
Add POST endpoint for copying artifacts between collections.
Include validation for collection ownership.")

Task("python-backend-engineer", "TASK-1.4: Add move artifact endpoint (optional) (2 SP)
File: skillmeat/api/app/routers/user_collections.py
Add POST endpoint for moving artifacts between collections.
Depends on: TASK-1.3")
```

### Execute Batch 2
```
Task("ui-engineer-enhanced", "TASK-2.1-2.8: Refactor Frontend API Client Functions
Phase 2 encompasses 8 parallel frontend API client tasks:

1. TASK-2.1: Refactor fetchCollections() (1 SP)
2. TASK-2.2: Refactor fetchCollection(id) (1 SP)
3. TASK-2.3: Fix updateCollection() (1 SP)
4. TASK-2.4: Fix deleteCollection() (1 SP)
5. TASK-2.5: Fix addArtifactToCollection() (2 SP)
6. TASK-2.6: Fix removeArtifactFromCollection() (1 SP)
7. TASK-2.7: Update copy/move or remove stubs (1 SP)
8. TASK-2.8: Update TypeScript types (1 SP)

File: skillmeat/web/src/lib/api/collections.ts
Ensure all functions use unified error handling, proper type safety, and consistent parameter validation.
Run tests after each fix to ensure compatibility.")
```

### Execute Batch 3
```
Task("ui-engineer-enhanced", "TASK-3.1-3.6: Implement Frontend Hooks
Phase 3 encompasses 6 parallel frontend hook implementations:

1. TASK-3.1: Update useCollections() hook (1 SP) - depends on TASK-2.1
2. TASK-3.2: Update useCollection(id) hook (1 SP) - depends on TASK-2.2
3. TASK-3.3: Implement useUpdateCollection() (1 SP) - depends on TASK-2.3
4. TASK-3.4: Implement useDeleteCollection() (1 SP) - depends on TASK-2.4
5. TASK-3.5: Implement useAddArtifactToCollection() (1 SP) - depends on TASK-2.5
6. TASK-3.6: Implement useRemoveArtifactFromCollection() (1 SP) - depends on TASK-2.6

File: skillmeat/web/src/hooks/useCollections.ts
Create hooks that integrate with refactored API client functions.
Include loading/error states, caching, and refetch capabilities.")
```

### Execute Batch 4
```
Task("python-backend-engineer", "TASK-5.1: Add deprecation warnings (1 SP)
File: skillmeat/api/app/routers/user_collections.py
Add deprecation headers and warnings to old collection endpoints.
Include migration path in warnings.")

Task("documentation-writer", "TASK-5.2-5.3: Update API Documentation (1.5 SP)
Files: docs/api/collections.md
1. Update API documentation with new endpoints
2. Add removal timeline (v1.0.0)
3. Create migration guide for consumers")
```

## Progress Tracking

- **Last Updated**: 2025-12-13
- **Phase Duration**: ~4-6 weeks (estimated)
- **Next Milestone**: Complete Phase 1 (Backend API)

---

*Progress file created for orchestration-driven development with artifact-tracking integration.*
