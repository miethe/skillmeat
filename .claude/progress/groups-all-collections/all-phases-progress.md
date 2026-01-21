---
prd: groups-all-collections-v1
title: Groups in All Collections View
status: completed
created: 2025-01-16
updated: '2026-01-16'
phases:
- id: phase-1
  name: Backend - Copy Group Endpoint
  status: completed
- id: phase-2
  name: Frontend - Collection Picker Enhancement
  status: completed
- id: phase-3
  name: Frontend - Copy Group Feature
  status: completed
- id: phase-4
  name: Testing & Polish
  status: completed
tasks:
- id: BE-001
  phase: phase-1
  name: Copy Endpoint
  description: Add POST /groups/{id}/copy endpoint
  status: completed
  assigned_to: python-backend-engineer
  estimate: 2
- id: BE-002
  phase: phase-1
  name: Service Logic
  description: Implement atomic copy in GroupsService
  status: completed
  assigned_to: python-backend-engineer
  estimate: 1
  depends_on:
  - BE-001
- id: BE-003
  phase: phase-1
  name: Unit Tests
  description: Tests for copy operation
  status: completed
  assigned_to: python-backend-engineer
  estimate: 1
  depends_on:
  - BE-002
- id: FE-001
  phase: phase-2
  name: Collection Picker Step
  description: Add collection selection to AddToGroupDialog
  status: completed
  assigned_to: ui-engineer-enhanced
  estimate: 2
- id: FE-002
  phase: phase-2
  name: Wire All Collections
  description: Pass undefined collectionId in All Collections view
  status: completed
  assigned_to: frontend-developer
  estimate: 1
  depends_on:
  - FE-001
- id: FE-003
  phase: phase-2
  name: Unit Tests
  description: Test collection picker behavior
  status: completed
  assigned_to: frontend-developer
  estimate: 1
  depends_on:
  - FE-002
- id: FE-004
  phase: phase-3
  name: API Client
  description: Add copyGroup() function
  status: completed
  assigned_to: frontend-developer
  estimate: 0.5
  depends_on:
  - BE-003
- id: FE-005
  phase: phase-3
  name: Hook
  description: Add useCopyGroup() mutation hook
  status: completed
  assigned_to: frontend-developer
  estimate: 0.5
  depends_on:
  - FE-004
- id: FE-006
  phase: phase-3
  name: Copy Dialog
  description: Create CopyGroupDialog component
  status: completed
  assigned_to: ui-engineer-enhanced
  estimate: 2
  depends_on:
  - FE-005
- id: FE-007
  phase: phase-3
  name: Integration
  description: Add copy action to group management UI
  status: completed
  assigned_to: frontend-developer
  estimate: 1
  depends_on:
  - FE-006
- id: QA-001
  phase: phase-4
  name: E2E Tests
  description: Full workflow tests
  status: completed
  assigned_to: frontend-developer
  estimate: 1
  depends_on:
  - FE-007
- id: QA-002
  phase: phase-4
  name: Accessibility
  description: Audit new dialogs
  status: completed
  assigned_to: ui-engineer-enhanced
  estimate: 0.5
  depends_on:
  - FE-007
- id: QA-003
  phase: phase-4
  name: API Docs
  description: Document copy endpoint
  status: completed
  assigned_to: documentation-writer
  estimate: 0.5
  depends_on:
  - BE-003
- id: QA-004
  phase: phase-4
  name: User Guide
  description: Update groups documentation
  status: completed
  assigned_to: documentation-writer
  estimate: 0.5
  depends_on:
  - QA-001
parallelization:
  batch_1:
    description: Backend copy endpoint (Phase 1) + Collection picker (Phase 2) in
      parallel
    tasks:
    - BE-001
    - BE-002
    - BE-003
    - FE-001
    - FE-002
    - FE-003
  batch_2:
    description: Copy Group frontend (Phase 3) - depends on BE-003
    tasks:
    - FE-004
    - FE-005
    - FE-006
    - FE-007
  batch_3:
    description: Testing and polish (Phase 4)
    tasks:
    - QA-001
    - QA-002
    - QA-003
    - QA-004
total_estimate: 13
total_tasks: 14
completed_tasks: 14
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
---

# Groups in All Collections View - Progress

## Overview

Enable adding artifacts to groups from All Collections view with two-step collection selection, plus ability to copy entire groups to other collections.

## Current Status

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Backend | ✅ Completed | 3/3 tasks |
| Phase 2: Frontend Enhancement | ✅ Completed | 3/3 tasks |
| Phase 3: Copy Group Feature | ✅ Completed | 4/4 tasks |
| Phase 4: Testing & Polish | ✅ Completed | 4/4 tasks |

## Execution Strategy

**Parallel Batch 1**: Phase 1 (Backend) and Phase 2 (Frontend Enhancement) can run simultaneously
- Backend has no frontend dependencies
- Collection picker enhancement has no backend dependencies

**Sequential Batch 2**: Phase 3 depends on Phase 1 backend completion
- Copy Group frontend needs the backend endpoint

**Final Batch 3**: Phase 4 depends on Phases 1-3 completion

## Key Files

### Backend
- `api/routers/groups.py` - Copy endpoint
- `api/services/groups.py` - Copy logic
- `api/schemas/groups.py` - Request schema

### Frontend
- `components/collection/add-to-group-dialog.tsx` - Collection picker
- `components/collection/copy-group-dialog.tsx` - New dialog
- `lib/api/groups.ts` - API client
- `hooks/use-groups.ts` - Hooks

## Related Documents

- PRD: `docs/project_plans/PRDs/enhancements/groups-all-collections-v1.md`
- Implementation Plan: `docs/project_plans/implementation_plans/enhancements/groups-all-collections-v1.md`
