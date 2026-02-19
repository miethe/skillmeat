---
type: progress
prd: sync-collections-regression
phase: 1-3
status: completed
progress: 100
tasks:
- id: P0-1.1
  title: Add migration call to cache initialization
  status: completed
  assigned_to:
  - python-backend-engineer
  model: sonnet
  files:
  - skillmeat/cache/manager.py
  dependencies: []
- id: P0-1.2
  title: Add integration test for cache migrations
  status: completed
  assigned_to:
  - python-backend-engineer
  model: sonnet
  files:
  - tests/cache/test_manager.py
  dependencies:
  - P0-1.1
- id: P1-2.1
  title: Fix artifact-to-deployment matching (add type)
  status: completed
  assigned_to:
  - ui-engineer
  model: sonnet
  files:
  - skillmeat/web/app/projects/[id]/page.tsx
  - skillmeat/web/app/collection/page.tsx
  dependencies: []
- id: P1-2.2
  title: Wire collection IDs through useEntityLifecycle
  status: completed
  assigned_to:
  - ui-engineer
  model: sonnet
  files:
  - skillmeat/web/hooks/useEntityLifecycle.tsx
  dependencies: []
- id: P1-2.3
  title: Update deploy dialog to pass collection context
  status: completed
  assigned_to:
  - ui-engineer
  model: sonnet
  files:
  - skillmeat/web/app/projects/[id]/manage/components/deploy-from-collection-dialog.tsx
  dependencies:
  - P1-2.2
- id: P1-2.4
  title: Add integration test for multi-collection deploy
  status: completed
  assigned_to:
  - ui-engineer
  model: sonnet
  files:
  - tests/web/integration/
  dependencies:
  - P1-2.1
  - P1-2.2
  - P1-2.3
- id: P2-3.1
  title: Add preview badge to context sync UI
  status: completed
  assigned_to:
  - ui-engineer
  model: sonnet
  files:
  - skillmeat/web/components/entity/context-sync-status.tsx
  dependencies: []
- id: P2-3.2
  title: Migrate sync.py to unified Deployment class
  status: completed
  assigned_to:
  - python-backend-engineer
  model: sonnet
  files:
  - skillmeat/core/sync.py
  dependencies: []
parallelization:
  batch_1:
  - P0-1.1
  batch_2:
  - P0-1.2
  batch_3:
  - P1-2.1
  - P1-2.2
  - P2-3.1
  - P2-3.2
  batch_4:
  - P1-2.3
  batch_5:
  - P1-2.4
success_criteria:
- Cache migrations run at initialization
- Artifact matching includes type check
- Collection IDs passed through frontend
- Preview badge visible on context sync
- sync.py uses DeploymentTracker
- All tests pass
total_tasks: 8
completed_tasks: 8
in_progress_tasks: 0
blocked_tasks: 0
updated: '2026-01-11'
schema_version: 2
doc_type: progress
feature_slug: sync-collections-regression
---

# Sync + Collections Regression Remediation - Progress Tracking

## Current Status: In Progress

### Phase 1: Critical Cache Migration Fix (P0)
| Task | Status | Assigned | Notes |
|------|--------|----------|-------|
| P0-1.1 | pending | python-backend-engineer | Add migration call |
| P0-1.2 | pending | python-backend-engineer | Integration test |

### Phase 2: Frontend Collection Identity (P1)
| Task | Status | Assigned | Notes |
|------|--------|----------|-------|
| P1-2.1 | pending | ui-engineer | Fix artifact matching |
| P1-2.2 | pending | ui-engineer | Wire collection IDs |
| P1-2.3 | pending | ui-engineer | Deploy dialog context |
| P1-2.4 | pending | ui-engineer | Integration test |

### Phase 3: Technical Debt (P2)
| Task | Status | Assigned | Notes |
|------|--------|----------|-------|
| P2-3.1 | pending | ui-engineer | Preview badge |
| P2-3.2 | pending | python-backend-engineer | Schema unification |
