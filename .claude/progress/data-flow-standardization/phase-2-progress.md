---
# === PROGRESS TRACKING TEMPLATE ===
# Phase-level task tracking optimized for AI agent orchestration
# REQUIRED FIELDS: assigned_to, dependencies for EVERY task
# Copy this template and replace all [PLACEHOLDER] values

# Metadata: Identification and Classification
type: progress
prd: "data-flow-standardization"
phase: 2
title: "Backend Cache-First Reads"
status: "planning"
started: "2026-02-04"
completed: null

# Overall Progress: Status and Estimates
overall_progress: 0
completion_estimate: "on-track"

# Task Counts: Machine-readable task state
total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

# Ownership: Primary and secondary agents
owners: ["python-backend-engineer"]
contributors: ["ui-engineer-enhanced"]

# === TASKS (SOURCE OF TRUTH) ===
# Machine-readable task definitions with assignments and dependencies
# Update using: python scripts/update-status.py -f FILE -t TASK-X -s [pending|in_progress|complete|blocked|at-risk]
tasks:
  - id: "TASK-2.1"
    description: "Add cache-first read path for `GET /artifacts` list endpoint in `api/routers/artifacts.py:1680-1800`"
    status: "deferred"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"
    notes: "DEFERRED pending further architecture analysis. artifact-metadata-cache-v1.md already handles DB-first reads for `/user-collections/{id}/artifacts`. Adding cache-first to root `/artifacts` requires careful dual-stack architecture consideration."

  - id: "TASK-2.2"
    description: "Add cache-first read path for `GET /artifacts/{id}` detail endpoint in `api/routers/artifacts.py:1993-2112`"
    status: "deferred"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"
    notes: "DEFERRED pending further architecture analysis. artifact-metadata-cache-v1.md already handles DB-first reads for `/user-collections/{id}/artifacts`. Adding cache-first to root `/artifacts` requires careful dual-stack architecture consideration."

  - id: "TASK-2.3"
    description: "Add `refresh_single_artifact_cache()` after file create in `api/routers/artifacts.py:~5350`"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "30m"
    priority: "high"

  - id: "TASK-2.4"
    description: "Add `refresh_single_artifact_cache()` after file update in `api/routers/artifacts.py:~5100`"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "30m"
    priority: "high"

  - id: "TASK-2.5"
    description: "Add `refresh_single_artifact_cache()` after file delete in `api/routers/artifacts.py:~5610`"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "30m"
    priority: "high"

  - id: "TASK-2.6"
    description: "Migrate `useSync()` from raw `fetch()` to `apiRequest()` in `hooks/useSync.ts:59`"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "30m"
    priority: "low"

# Parallelization Strategy (computed from dependencies)
parallelization:
  batch_1: ["TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6"]
  deferred: ["TASK-2.1", "TASK-2.2"]
  critical_path: ["TASK-2.3"]
  estimated_total_time: "30m"  # If run optimally (parallel batch)

# Critical Blockers: For immediate visibility
blockers: []

# Success Criteria: Acceptance conditions for phase completion
success_criteria: [
  { id: "SC-1", description: "File mutations trigger cache refresh (metadata stays fresh)", status: "pending" },
  { id: "SC-2", description: "useSync uses unified apiRequest client", status: "pending" },
  { id: "SC-3", description: "(Deferred) All artifact endpoints use cache-first reads", status: "deferred" }
]

# Files Modified: What's being changed in this phase
files_modified: [
  "skillmeat/api/routers/artifacts.py",
  "skillmeat/web/hooks/useSync.ts"
]
---

# data-flow-standardization - Phase 2: Backend Cache-First Reads

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/data-flow-standardization/phase-2-progress.md -t TASK-X -s completed
```

---

## Objective

Ensure all artifact file mutations (create/update/delete) immediately refresh the DB cache to maintain data consistency, and migrate frontend hooks to use the unified API client. This phase focuses on write-through cache consistency rather than read optimization (which is already handled by artifact-metadata-cache-v1.md for the primary collection endpoint).

---

## Implementation Notes

### Architectural Decisions

**Cache-First Reads (DEFERRED)**:
- TASK-2.1 and TASK-2.2 are deferred because `artifact-metadata-cache-v1.md` already implements DB-first reads for `/user-collections/{id}/artifacts`, which is the primary artifact browsing endpoint used by the web UI.
- Root `/artifacts` endpoints are primarily used by CLI and legacy code paths.
- Further architectural analysis needed to determine if dual-stack caching at both levels provides meaningful value vs. complexity.

**Write-Through on File Mutations (ACTIVE)**:
- File create/update/delete operations must call `refresh_single_artifact_cache()` after filesystem writes.
- Ensures DB cache reflects filesystem state immediately after mutations.
- Follows Data Flow Principle #3: "Write-Through for Web Mutations".

**Frontend API Client Migration (LOW PRIORITY)**:
- `useSync()` currently uses raw `fetch()` instead of the unified `apiRequest()` wrapper.
- Migration provides consistent error handling and auth patterns but is non-critical.

### Patterns and Best Practices

**Cache Refresh Pattern**:
```python
# After filesystem write
await refresh_single_artifact_cache(
    artifact_id=artifact.id,
    collection_root=collection_root,
    db=db
)
```

**apiRequest() Migration Pattern**:
```typescript
// Before
const response = await fetch('/api/artifacts/sync', { method: 'POST', ... });

// After
const response = await apiRequest('/artifacts/sync', { method: 'POST', ... });
```

### Known Gotchas

**File Operation Locations**:
- File operations are spread across `artifacts.py` (~6000 lines).
- Line numbers (~5350, ~5100, ~5610) are approximate; use grep/symbols to locate exact endpoints.
- Ensure cache refresh happens AFTER successful filesystem write, not before.

**Error Handling**:
- If cache refresh fails, log error but don't fail the overall operation.
- Filesystem is source of truth; cache staleness is recoverable via manual refresh.

**Transaction Boundaries**:
- DB cache refresh should be part of the same logical transaction as the file write.
- Use try/finally to ensure cache cleanup even if later steps fail.

### Development Setup

No special setup required. Standard dev environment:
```bash
skillmeat web dev  # Start API + Next.js
```

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
