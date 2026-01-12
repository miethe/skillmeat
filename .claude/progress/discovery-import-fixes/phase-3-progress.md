---
type: progress
prd: discovery-import-fixes-v1
phase: 3
phase_name: Deployment UX Improvements
status: completed
progress: 100
created: 2026-01-09
updated: '2026-01-09'
request_log: REQ-20260109-skillmeat
implementation_plan: docs/project_plans/implementation_plans/harden-polish/discovery-import-fixes-v1.md
phase_detail: docs/project_plans/implementation_plans/harden-polish/discovery-import-fixes-v1/phase-3-deploy-button.md
depends_on:
- phase-1
tasks:
- id: P3-T1
  name: Entity Modal deploy button
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  dependencies: []
  estimate: 2pts
  files:
  - skillmeat/web/components/artifacts/UnifiedEntityModal.tsx
- id: P3-T2
  name: Collection view deploy option
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  dependencies: []
  estimate: 2pts
  files:
  - skillmeat/web/components/collections/
- id: P3-T3
  name: Unified dialog consistency verification
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  model: sonnet
  dependencies:
  - P3-T1
  - P3-T2
  estimate: 2pts
  files:
  - skillmeat/web/components/deployments/AddToProjectDialog.tsx
parallelization:
  batch_1:
  - P3-T1
  - P3-T2
  batch_2:
  - P3-T3
quality_gates:
- Deploy button visible in Entity Modal Deployments tab (top right)
- Collection view meatballs menu includes 'Deploy to Project' option
- All three entry points use same dialog component (no duplicates)
- Deploy from modal completes without navigation
- Dialog opens with artifact pre-selected
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
---

# Phase 3: Deployment UX Improvements

**Duration:** 1 week | **Effort:** 6-8 story points | **Priority:** MEDIUM

**Depends On:** Phase 1 completion (basic discovery workflow must be stable)

## Overview

Add "Deploy to Project" button to multiple entry points:
1. Unified Entity Modal → Deployments tab
2. Collection view → artifact meatballs menu
3. Update existing /manage view button for consistency

All entry points should use the same "Add to Project" dialog component.

## Quick Reference

### CLI Status Updates
```bash
# Mark task complete
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/discovery-import-fixes/phase-3-progress.md \
  -t P3-T1 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/discovery-import-fixes/phase-3-progress.md \
  --updates "P3-T1:completed,P3-T2:completed,P3-T3:completed"
```

### Task Delegation
```
# Batch 1 (parallel - all frontend)
Task("ui-engineer-enhanced", "P3-T1: Add Deploy to Project button in Entity Modal...", model="sonnet")
Task("ui-engineer-enhanced", "P3-T2: Add Deploy to Project option in Collection meatballs...", model="sonnet")

# Batch 2 (after batch 1)
Task("ui-engineer-enhanced", "P3-T3: Verify all entry points use same dialog...", model="sonnet")
```

## Task Details

### P3-T1: Entity Modal Deploy Button
**Goal:** Add "Deploy to Project" button in Unified Entity Modal Deployments tab

**Acceptance Criteria:**
- [ ] Button visible in Deployments tab header (top right)
- [ ] Button styled consistently with existing modal buttons
- [ ] Opens AddToProjectDialog with current artifact pre-selected
- [ ] Dialog closes on successful deployment
- [ ] Toast notification on success/failure
- [ ] No page navigation required

### P3-T2: Collection View Deploy Option
**Goal:** Add "Deploy to Project" option in Collection view artifact menu

**Acceptance Criteria:**
- [ ] Option visible in artifact meatballs (three-dot) menu
- [ ] Uses same AddToProjectDialog component
- [ ] Artifact pre-selected in dialog
- [ ] Works for all artifact types (skills, commands, agents, etc.)
- [ ] Consistent icon with Entity Modal button

### P3-T3: Unified Dialog Consistency
**Goal:** Ensure all entry points use the same dialog component

**Acceptance Criteria:**
- [ ] Entity Modal uses AddToProjectDialog
- [ ] Collection view uses AddToProjectDialog
- [ ] /manage view uses AddToProjectDialog
- [ ] No duplicate dialog implementations
- [ ] Dialog accepts artifact prop for pre-selection
- [ ] Dialog behavior identical across entry points

## Blockers

- Need to verify AddToProjectDialog supports artifact pre-selection prop

## Notes

- Phase 3 can start after Phase 1 (independent of Phase 2)
- All tasks are frontend-only (no backend changes)
- Use Sonnet model (well-scoped, following established patterns)
- Check existing meatballs menu implementation for pattern
