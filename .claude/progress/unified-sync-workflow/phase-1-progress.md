---
type: progress
prd: "unified-sync-workflow"
phase: 1
phase_name: "Backend Enablement + Unified Hook"
status: pending
progress: 0
created: 2026-02-04
updated: 2026-02-05

tasks:
  - id: "SYNC-B01"
    name: "Source-vs-project diff endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "1.5 pts"
    model: "opus"

  - id: "SYNC-B02"
    name: "Extend deploy with merge strategy"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: "2 pts"
    model: "opus"

  - id: "SYNC-H01"
    name: "Create unified useConflictCheck hook"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1.5 pts"
    model: "opus"

  - id: "SYNC-B03"
    name: "Backend unit tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SYNC-B01", "SYNC-B02"]
    estimate: "1 pt"
    model: "sonnet"

parallelization:
  batch_1: ["SYNC-B01", "SYNC-B02", "SYNC-H01"]
  batch_2: ["SYNC-B03"]

quality_gates:
  - "Source-project diff endpoint returns accurate file-level diffs"
  - "Deploy with strategy='merge' performs file merge, reports conflicts"
  - "useConflictCheck routes to correct API per direction"
  - "targetHasChanges flag correctly computed for merge gating"
  - "All backend tests pass"
  - "No regressions in existing sync/deploy flows"
---

# Phase 1: Backend Enablement + Unified Hook

**Goal**: Add missing backend endpoints and create the unified frontend hook for pre-operation conflict detection.

**Duration**: 2-3 days | **Story Points**: 6

## Task Details

### SYNC-B01: Source-vs-project diff endpoint

**File**: `skillmeat/api/routers/artifacts.py`

**Requirements**:
- Add `GET /artifacts/{id}/source-project-diff?project_path=...`
- Follow `/upstream-diff` endpoint pattern (~line 4055)
- Use existing DiffEngine to compare upstream source directly against project deployment
- Return `ArtifactDiffResponse` with file-level diffs
- ~50 LOC addition

### SYNC-B02: Extend deploy with merge strategy

**File**: `skillmeat/api/routers/artifacts.py` (~line 2898)

**Requirements**:
- Extend `POST /deploy` request model to accept `strategy: 'overwrite' | 'merge'`
- Default to `'overwrite'` (no breaking change)
- When `strategy='merge'`:
  - Use DiffEngine to compare collection vs project files
  - Files only in collection: copy to project
  - Files only in project: keep (don't delete)
  - Both sides modified same file: attempt merge, return conflict
  - Return conflicts array in response
- ~150 LOC addition

### SYNC-H01: Create unified useConflictCheck hook

**File**: `skillmeat/web/hooks/use-conflict-check.ts`

**Requirements**:
- Signature: `useConflictCheck(direction: 'deploy' | 'push' | 'pull', artifactId, opts)`
- Direction routing:
  - `'deploy'`: `GET /artifacts/{id}/diff?project_path=...` (collection vs project)
  - `'push'`: `GET /artifacts/{id}/diff?project_path=...` (collection vs project)
  - `'pull'`: `GET /artifacts/{id}/upstream-diff` (source vs collection)
- Returns: `{ diffData, hasChanges, hasConflicts, targetHasChanges, isLoading, error }`
- `targetHasChanges` computed from FileDiff statuses (any modified/added in target side)
- Stale time: 30 seconds
- Export from `hooks/index.ts`

### SYNC-B03: Backend unit tests

**Files**: `tests/test_artifacts_sync.py` (or appropriate test file)

**Requirements**:
- Source-project diff: with changes, no changes, error cases
- Deploy merge strategy: success, conflicts, error, no regression on overwrite
- Cover edge cases: missing project, missing source, empty diffs

## Quick Reference

### Execute Phase

```text
# Batch 1: Backend + Hook (parallel)
Task("python-backend-engineer", "SYNC-B01: Add source-vs-project diff endpoint
  File: skillmeat/api/routers/artifacts.py
  Pattern: Follow /upstream-diff endpoint structure (~line 4055)
  New: GET /artifacts/{id}/source-project-diff?project_path=...
  Use existing DiffEngine. Return ArtifactDiffResponse. ~50 LOC.")

Task("python-backend-engineer", "SYNC-B02: Extend deploy endpoint with merge strategy
  File: skillmeat/api/routers/artifacts.py (~line 2898)
  Extend POST /deploy to accept strategy: 'overwrite' | 'merge'
  When merge: DiffEngine comparison, file-level merge, return conflicts.
  Existing overwrite behavior MUST remain unchanged as default.")

Task("ui-engineer-enhanced", "SYNC-H01: Create unified useConflictCheck hook
  File: skillmeat/web/hooks/use-conflict-check.ts
  Export from hooks/index.ts
  Direction-based routing to appropriate diff API.
  Returns: { diffData, hasChanges, hasConflicts, targetHasChanges, isLoading }")

# Batch 2: Tests (after batch 1)
Task("python-backend-engineer", "SYNC-B03: Backend tests for new/extended endpoints", model="sonnet")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-1-progress.md \
  --updates "SYNC-B01:completed,SYNC-B02:completed,SYNC-H01:completed"
```
