---
type: progress
prd: "unified-sync-workflow"
phase: 4
phase_name: "Polish, Testing & Persistent Drift"
status: pending
progress: 0
created: 2026-02-04
updated: 2026-02-04

tasks:
  - id: "SYNC-018"
    name: "Implement persistent drift dismissal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "1 pt"
    model: "sonnet"

  - id: "SYNC-019"
    name: "E2E test: Deploy with conflicts"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-003"]
    estimate: "0.75 pts"
    model: "sonnet"

  - id: "SYNC-020"
    name: "E2E test: Push with conflicts"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-010"]
    estimate: "0.75 pts"
    model: "sonnet"

  - id: "SYNC-021"
    name: "E2E test: Full sync cycle"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["SYNC-019", "SYNC-020"]
    estimate: "1 pt"
    model: "sonnet"

  - id: "SYNC-022"
    name: "Accessibility audit"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-023"
    name: "Performance optimization"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-024"
    name: "Documentation and code comments"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimate: "0.5 pts"
    model: "sonnet"

  - id: "SYNC-025"
    name: "Code review and merge"
    status: "pending"
    assigned_to: ["code-reviewer"]
    dependencies: ["SYNC-018", "SYNC-019", "SYNC-020", "SYNC-021", "SYNC-022", "SYNC-023", "SYNC-024"]
    estimate: "0.5 pts"
    model: "opus"

parallelization:
  batch_1: ["SYNC-018", "SYNC-019", "SYNC-020", "SYNC-022", "SYNC-023", "SYNC-024"]
  batch_2: ["SYNC-021"]
  batch_3: ["SYNC-025"]

quality_gates:
  - "Drift dismissal persists across browser sessions"
  - "All E2E tests pass in CI"
  - "Zero axe-core accessibility violations"
  - "Dialogs render in <100ms"
  - "All code documented with JSDoc"
  - "Code review complete"
---

# Phase 4: Polish, Testing & Persistent Drift

**Goal**: Add persistent drift dismissal, comprehensive E2E tests, accessibility audit, and documentation.

**Duration**: 2-3 days | **Story Points**: 5.5

**Depends on**: Phase 3 complete

## Task Details

### SYNC-018: Implement persistent drift dismissal

**File**: `skillmeat/web/components/sync-status/sync-status-tab.tsx`

**Requirements**:
- Store dismissed drift alerts in localStorage
- Key format: `skillmeat:drift-dismissed:{artifactId}:{scope}`
- Expire after 24 hours
- Clear on update detection
- Handle SSR (check window exists)

### SYNC-019: E2E test - Deploy with conflicts

**File**: `skillmeat/web/tests/sync-workflow.e2e.ts`

**Requirements**:
- Test shows diff viewer when conflicts exist
- User confirms overwrite, deploy succeeds
- Toast notification appears
- Cache refreshes

### SYNC-020: E2E test - Push with conflicts

**File**: `skillmeat/web/tests/sync-workflow.e2e.ts`

**Requirements**:
- Test push flow with upstream changes
- User confirms push
- Collection updated

### SYNC-021: E2E test - Full sync cycle

**File**: `skillmeat/web/tests/sync-workflow.e2e.ts`

**Requirements**:
- Complete workflow: Pull → Modify → Push → Deploy
- All steps work end-to-end
- No stale data issues

### SYNC-022: Accessibility audit

**Requirements**:
- Run axe-core on all new dialogs
- Zero violations
- Proper focus management
- ARIA labels on buttons
- Keyboard navigation works

### SYNC-023: Performance optimization

**Requirements**:
- Profile dialog rendering
- Target <100ms render time
- Optimize DiffViewer for large diffs
- Consider virtualization if needed

### SYNC-024: Documentation and code comments

**Requirements**:
- JSDoc for all public APIs
- Usage examples in comments
- README updates if needed

### SYNC-025: Code review and merge

**Requirements**:
- Final code review
- Address all comments
- Merge to main branch

## Quick Reference

### Execute Phase

```text
# Batch 1: Parallel polish tasks
Task("ui-engineer-enhanced", "SYNC-018: Implement persistent drift dismissal
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
  - localStorage with key skillmeat:drift-dismissed:{id}:{scope}
  - 24 hour expiration
  - SSR-safe (check window)", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-019: Write E2E test for deploy with conflicts
  File: skillmeat/web/tests/sync-workflow.e2e.ts
  Test deploy flow shows diff, user confirms overwrite, deploy succeeds", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-020: Write E2E test for push with conflicts
  File: skillmeat/web/tests/sync-workflow.e2e.ts
  Test push flow with upstream changes", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-022: Accessibility audit with axe-core
  Run axe on all new dialogs, fix violations, verify focus management", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-023: Performance optimization
  Profile dialog rendering, target <100ms, optimize DiffViewer", model="sonnet")

Task("ui-engineer-enhanced", "SYNC-024: Add JSDoc documentation
  Document all public APIs with examples", model="sonnet")

# Batch 2: Full cycle E2E (after individual tests)
Task("ui-engineer-enhanced", "SYNC-021: Write E2E test for full sync cycle
  Test Pull -> Modify -> Push -> Deploy end-to-end", model="sonnet")

# Batch 3: Final review
Task("code-reviewer", "SYNC-025: Final code review and merge
  Review all changes from unified-sync-workflow feature
  Ensure quality gates met, approve and merge")
```

### Update Status (CLI)

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/unified-sync-workflow/phase-4-progress.md \
  --updates "SYNC-018:completed,SYNC-019:completed,SYNC-020:completed"
```
