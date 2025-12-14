---
type: progress
prd: "agent-context-entities"
phase: 5
phase_title: "Progressive Disclosure & Sync"
status: pending
progress: 0
total_tasks: 8
completed_tasks: 0
created: "2025-12-14"
updated: "2025-12-14"

tasks:
  - id: "TASK-5.1"
    name: "Implement Content Hashing for Change Detection"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: 2

  - id: "TASK-5.2"
    name: "Create Context Sync Service"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.1"]
    estimate: 3

  - id: "TASK-5.3"
    name: "Create Context Discovery Endpoint"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimate: 2

  - id: "TASK-5.4"
    name: "Create Sync Operations Endpoints"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.2"]
    estimate: 2

  - id: "TASK-5.5"
    name: "Create Context Diff Viewer Component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: 3

  - id: "TASK-5.6"
    name: "Create Context Discovery Panel"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.3"]
    estimate: 2

  - id: "TASK-5.7"
    name: "Integrate Sync UI into Project Page"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.5", "TASK-5.6"]
    estimate: 2

  - id: "TASK-5.8"
    name: "Implement CLI Sync Commands"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["TASK-5.2", "TASK-5.4"]
    estimate: 1

parallelization:
  batch_1: ["TASK-5.1", "TASK-5.3"]
  batch_2: ["TASK-5.2"]
  batch_3: ["TASK-5.4", "TASK-5.8"]
  batch_4: ["TASK-5.5", "TASK-5.6"]
  batch_5: ["TASK-5.7"]
---

# Phase 5: Progressive Disclosure & Sync

## Orchestration Quick Reference

**Batch 1** (Parallel - Core Logic):
- TASK-5.1 → `python-backend-engineer` (2h)
- TASK-5.3 → `python-backend-engineer` (2h)

**Batch 2** (Sequential - Sync Service):
- TASK-5.2 → `python-backend-engineer` (3h)

**Batch 3** (Parallel - API + CLI):
- TASK-5.4 → `python-backend-engineer` (2h)
- TASK-5.8 → `python-backend-engineer` (1h)

**Batch 4** (Parallel - UI Components):
- TASK-5.5 → `ui-engineer-enhanced` (3h)
- TASK-5.6 → `ui-engineer-enhanced` (2h)

**Batch 5** (Sequential - UI Integration):
- TASK-5.7 → `ui-engineer-enhanced` (2h)

### Task Delegation Commands

**Batch 1**:
```python
Task("python-backend-engineer", "TASK-5.1: Implement content hashing for change detection. File: skillmeat/core/services/content_hash.py. Function: compute_content_hash (SHA256), detect_changes (compare collection hash vs deployed file hash). Hash computed on entity create/update.")

Task("python-backend-engineer", "TASK-5.3: Create context discovery endpoint. GET /projects/{id}/context-map. Scan project .claude/ directory. Return auto-loaded entities and on-demand entities with token estimates. Total token count for auto-load entities.")
```

**Batch 2**:
```python
Task("python-backend-engineer", "TASK-5.2: Create context sync service. File: skillmeat/core/services/context_sync.py. Methods: detect_modified_entities, pull_changes (project → collection), push_changes (collection → project), detect_conflicts (both modified), resolve_conflict (keep_local/keep_remote/merge). Use content hashing.")
```

**Batch 3**:
```python
Task("python-backend-engineer", "TASK-5.4: Create sync operations API endpoints. File: skillmeat/api/routers/context_sync.py. Endpoints: POST /context-sync/pull, POST /context-sync/push, GET /context-sync/status. Request bodies: SyncPullRequest, SyncPushRequest. Response: SyncStatusResponse with modified entities and conflicts.")

Task("python-backend-engineer", "TASK-5.8: Implement CLI sync commands. Commands: 'skillmeat project sync-context <path> --pull', '--push', '--status'. Show colored diff in terminal. Confirmation prompt. Summary of changes. Support --entities filter.")
```

**Batch 4**:
```python
Task("ui-engineer-enhanced", "TASK-5.5: Create context diff viewer component. File: skillmeat/web/components/context/context-diff-viewer.tsx. Side-by-side diff view. Highlight additions (green) and deletions (red). Resolution actions: Keep Local, Keep Remote, Merge (future). Use react-diff-viewer or diff2html. Preview result before applying.")

Task("ui-engineer-enhanced", "TASK-5.6: Create context discovery panel. File: skillmeat/web/components/projects/context-discovery-panel.tsx. Display auto-loaded entities with token counts. Display on-demand entities. Total token usage indicator. Load order visualization (specs → rules → context). Toggle auto-load flag. Warning if token count > 2000.")
```

**Batch 5**:
```python
Task("ui-engineer-enhanced", "TASK-5.7: Integrate sync UI into project page. File: skillmeat/web/app/projects/[id]/page.tsx. Add 'Sync Context' button in toolbar. Badge showing pending changes count. Modal with diff viewer for each modified entity. Batch apply changes (sync all).")
```

## Quality Gates

- [ ] Change detection identifies modified files
- [ ] Pull updates collection correctly
- [ ] Push updates project files correctly
- [ ] Conflicts detected and shown
- [ ] Diff view highlights changes accurately
- [ ] Context map returns correct auto-load status
- [ ] Token estimates are reasonable
- [ ] CLI sync commands work

## Notes

_Session notes go here_
