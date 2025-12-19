---
type: progress
prd: "versioning-merge-system"
phase: 9
title: "Frontend - Merge UI & Conflict Resolution"
status: "completed"
started: "2025-12-17"
completed: "2025-12-17"
overall_progress: 100
completion_estimate: "complete"
total_tasks: 10
completed_tasks: 10
in_progress_tasks: 0
blocked_tasks: 0
owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: []

# STATUS NOTE: Not started - blocked by Phase 7 (merge API endpoints)
# No merge UI or conflict resolution components exist yet
# Requires: /api/v1/artifacts/{id}/merge/* endpoints

tasks:
  - id: "MERGE-UI-001"
    description: "Build ColoredDiffViewer - three-way colors (Green=upstream, Blue=local, Red=conflict, Yellow=removed)"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["APIVM-007"]
    estimated_effort: "8h"
    priority: "high"
    files: ["skillmeat/web/components/merge/colored-diff-viewer.tsx"]

  - id: "MERGE-UI-002"
    description: "Add change type labels (local change, upstream update, conflict)"
    status: "completed"
    assigned_to: ["frontend-developer"]
    dependencies: ["MERGE-UI-001"]
    estimated_effort: "2h"
    priority: "high"
    notes: "Integrated into ColoredDiffViewer and ConflictList components"

  - id: "MERGE-UI-003"
    description: "Build MergePreview component"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["APIVM-006"]
    estimated_effort: "5h"
    priority: "high"
    files: ["skillmeat/web/components/merge/merge-preview-view.tsx"]

  - id: "MERGE-UI-004"
    description: "Add merge statistics display (auto-merged count, conflicts, unchanged files)"
    status: "completed"
    assigned_to: ["frontend-developer"]
    dependencies: ["MERGE-UI-001"]
    estimated_effort: "2h"
    priority: "medium"
    notes: "Integrated into MergeAnalysisDialog and MergePreviewView"

  - id: "MERGE-UI-005"
    description: "Integrate existing conflict-resolver component"
    status: "completed"
    assigned_to: ["frontend-developer"]
    dependencies: ["APIVM-008"]
    estimated_effort: "3h"
    priority: "high"
    files: ["skillmeat/web/components/merge/conflict-resolver.tsx"]

  - id: "MERGE-UI-006"
    description: "Add conflict strategy selection (ours/theirs/manual per file)"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["MERGE-UI-005"]
    estimated_effort: "3h"
    priority: "high"
    files: ["skillmeat/web/components/merge/merge-strategy-selector.tsx"]

  - id: "MERGE-UI-007"
    description: "Build MergeWorkflow component (Preview → Conflicts → Confirm → Apply)"
    status: "completed"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["MERGE-UI-003"]
    estimated_effort: "5h"
    priority: "high"
    files: ["skillmeat/web/components/merge/merge-workflow-dialog.tsx"]

  - id: "MERGE-UI-008"
    description: "Wire merge apply endpoint to button"
    status: "completed"
    assigned_to: ["frontend-developer"]
    dependencies: ["MERGE-UI-007"]
    estimated_effort: "2h"
    priority: "high"
    notes: "Wired via useExecuteMerge hook in MergeWorkflowDialog"

  - id: "MERGE-UI-009"
    description: "Add merge result notification/toast"
    status: "completed"
    assigned_to: ["frontend-developer"]
    dependencies: ["MERGE-UI-008"]
    estimated_effort: "2h"
    priority: "medium"
    files: ["skillmeat/web/components/merge/merge-result-toast.tsx"]

  - id: "MERGE-UI-010"
    description: "Track merge operations in version history"
    status: "completed"
    assigned_to: ["frontend-developer"]
    dependencies: ["MERGE-UI-008"]
    estimated_effort: "2h"
    priority: "medium"
    notes: "useExecuteMerge invalidates snapshot queries on success"

parallelization:
  batch_1: ["MERGE-UI-001", "MERGE-UI-003"]
  batch_2: ["MERGE-UI-002", "MERGE-UI-004", "MERGE-UI-005", "MERGE-UI-006"]
  batch_3: ["MERGE-UI-007", "MERGE-UI-008", "MERGE-UI-009", "MERGE-UI-010"]
  critical_path: ["MERGE-UI-001", "MERGE-UI-007", "MERGE-UI-008"]
  estimated_total_time: "4-5d"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "Diff viewer displays three-way diffs correctly with proper color coding"
    status: "pending"
  - id: "SC-2"
    description: "Color coding clearly distinguishes change types (upstream, local, conflict, removed)"
    status: "pending"
  - id: "SC-3"
    description: "Merge preview accurately shows what will merge"
    status: "pending"
  - id: "SC-4"
    description: "Conflict resolver works for all conflict types (content, structural, semantic)"
    status: "pending"
  - id: "SC-5"
    description: "Workflow guides users through merge steps clearly"
    status: "pending"
  - id: "SC-6"
    description: "Apply merge works end-to-end from preview to result"
    status: "pending"
  - id: "SC-7"
    description: "Component tests achieve >80% coverage"
    status: "pending"
  - id: "SC-8"
    description: "All interactive elements keyboard accessible"
    status: "pending"
  - id: "SC-9"
    description: "Color not sole indicator of change type - text labels present"
    status: "pending"
---

# versioning-merge-system - Phase 9: Frontend - Merge UI & Conflict Resolution

**Phase**: 9 of 10
**Status**: ⏳ Planning (0% complete)
**Duration**: Estimated 4-5 days
**Owners**: ui-engineer-enhanced, frontend-developer
**Contributors**: None yet

**Dependencies**: Phase 7 (Merge API) complete, Phase 8 (Diff Viewer) complete

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Use this section to delegate tasks without reading the full file.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- MERGE-UI-001 → `ui-engineer-enhanced` (8h) - Build ColoredDiffViewer with three-way colors - **Depends on**: APIVM-007
- MERGE-UI-003 → `ui-engineer-enhanced` (5h) - Build MergePreview component - **Depends on**: APIVM-006

**Batch 2** (Sequential - Depends on Batch 1):
- MERGE-UI-002 → `frontend-developer` (2h) - Add change type labels - **Depends on**: MERGE-UI-001
- MERGE-UI-004 → `frontend-developer` (2h) - Add merge statistics display - **Depends on**: MERGE-UI-001
- MERGE-UI-005 → `frontend-developer` (3h) - Integrate conflict-resolver component - **Depends on**: APIVM-008
- MERGE-UI-006 → `ui-engineer-enhanced` (3h) - Add conflict strategy selection - **Depends on**: MERGE-UI-005

**Batch 3** (Sequential - Depends on Batch 2):
- MERGE-UI-007 → `ui-engineer-enhanced` (5h) - Build MergeWorkflow component - **Depends on**: MERGE-UI-003
- MERGE-UI-008 → `frontend-developer` (2h) - Wire merge apply endpoint - **Depends on**: MERGE-UI-007
- MERGE-UI-009 → `frontend-developer` (2h) - Add merge result notification - **Depends on**: MERGE-UI-008
- MERGE-UI-010 → `frontend-developer` (2h) - Track merge in version history - **Depends on**: MERGE-UI-008

**Critical Path**: MERGE-UI-001 → MERGE-UI-007 → MERGE-UI-008 (15h total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel)
Task("ui-engineer-enhanced", "MERGE-UI-001: Build ColoredDiffViewer component. Display three-way diffs with colors: Green=upstream changes, Blue=local changes, Red=conflicts, Yellow=removed lines. Support syntax highlighting. Component should accept {local, upstream, merge_result, conflicts} and render diff chunks with color coding and line numbers.")

Task("ui-engineer-enhanced", "MERGE-UI-003: Build MergePreview component. Show artifact name, merge source, preview of changes. Display file-level merge status summary. Component should accept {artifact, merge_proposal, stats} and render clear preview of what will be merged.")

# Batch 2 (After Batch 1 completes)
Task("frontend-developer", "MERGE-UI-002: Add change type labels to ColoredDiffViewer. Render text labels ('local change', 'upstream update', 'conflict', 'removed') alongside color coding. Ensure labels are always visible and not reliant on color alone.")

Task("frontend-developer", "MERGE-UI-004: Add merge statistics display. Show counts: auto-merged files, conflicts, unchanged files. Render in MergePreview. Format: '3 auto-merged, 1 conflict, 12 unchanged'.")

Task("frontend-developer", "MERGE-UI-005: Integrate existing conflict-resolver component into merge workflow. Update imports and props to match conflict structure from APIVM-008. Ensure it works with ColoredDiffViewer.")

Task("ui-engineer-enhanced", "MERGE-UI-006: Add conflict strategy selection UI. Per-file buttons for 'ours', 'theirs', 'manual'. State management to track selections. Preview result of each strategy choice before apply.")

# Batch 3 (After Batch 2 completes)
Task("ui-engineer-enhanced", "MERGE-UI-007: Build MergeWorkflow component - orchestrates merge steps: Preview → Conflicts → Confirm → Apply. Render MergePreview, ColoredDiffViewer, conflict-resolver, confirm dialog, status messages. Component state tracks current step.")

Task("frontend-developer", "MERGE-UI-008: Wire MergeWorkflow apply button to merge API endpoint. Call POST /api/v1/projects/{project_id}/merge with strategy selections. Handle loading state, errors. Transition to success state.")

Task("frontend-developer", "MERGE-UI-009: Add merge result notification. Toast/dialog showing merge outcome: success, file count, conflicts resolved, time taken. Show link to version history. Dismiss automatically or manual close.")

Task("frontend-developer", "MERGE-UI-010: Track merge operations in version history. Record merge as 'merge' operation in artifact version history. Show merge source, date, strategy used. Include in version timeline.")
```

---

## Overview

Phase 9 implements the complete merge user interface and conflict resolution workflow. Building on Phase 8's diff viewer foundation and Phase 7's API, this phase creates an intuitive guided experience for users to preview, understand, and execute merges with clear visual feedback for all change types and conflicts.

**Why This Phase**: Users need visual clarity when merging artifact versions. Three-way diffs with color coding, conflict highlighting, and strategic resolution options ensure users understand what's happening and can resolve conflicts confidently.

**Scope**:
- ✅ **IN SCOPE**: ColoredDiffViewer with three-way coloring, change type labels, MergePreview, merge statistics, conflict strategy selection, MergeWorkflow orchestration, apply button integration, result notifications, version history tracking
- ❌ **OUT OF SCOPE**: API endpoints (Phase 7), merge algorithm (Phase 5), diff algorithm (Phase 6), accessibility testing framework, automated conflict detection refinement

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | Diff viewer displays three-way diffs correctly with proper color coding | ⏳ Pending |
| SC-2 | Color coding clearly distinguishes change types (upstream, local, conflict, removed) | ⏳ Pending |
| SC-3 | Merge preview accurately shows what will merge | ⏳ Pending |
| SC-4 | Conflict resolver works for all conflict types (content, structural, semantic) | ⏳ Pending |
| SC-5 | Workflow guides users through merge steps clearly | ⏳ Pending |
| SC-6 | Apply merge works end-to-end from preview to result | ⏳ Pending |
| SC-7 | Component tests achieve >80% coverage | ⏳ Pending |
| SC-8 | All interactive elements keyboard accessible | ⏳ Pending |
| SC-9 | Color not sole indicator of change type - text labels present | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| MERGE-UI-001 | Build ColoredDiffViewer - three-way colors | ⏳ | ui-engineer-enhanced | APIVM-007 | 8h | Green=upstream, Blue=local, Red=conflict, Yellow=removed |
| MERGE-UI-002 | Add change type labels | ⏳ | frontend-developer | MERGE-UI-001 | 2h | local change, upstream update, conflict |
| MERGE-UI-003 | Build MergePreview component | ⏳ | ui-engineer-enhanced | APIVM-006 | 5h | Shows artifact, source, change preview |
| MERGE-UI-004 | Add merge statistics display | ⏳ | frontend-developer | MERGE-UI-001 | 2h | 3 auto-merged, 1 conflict, 12 unchanged |
| MERGE-UI-005 | Integrate conflict-resolver component | ⏳ | frontend-developer | APIVM-008 | 3h | Reuse existing component |
| MERGE-UI-006 | Add conflict strategy selection | ⏳ | ui-engineer-enhanced | MERGE-UI-005 | 3h | ours/theirs/manual per file |
| MERGE-UI-007 | Build MergeWorkflow component | ⏳ | ui-engineer-enhanced | MERGE-UI-003 | 5h | Preview → Conflicts → Confirm → Apply |
| MERGE-UI-008 | Wire merge apply endpoint to button | ⏳ | frontend-developer | MERGE-UI-007 | 2h | POST /api/v1/projects/{id}/merge |
| MERGE-UI-009 | Add merge result notification/toast | ⏳ | frontend-developer | MERGE-UI-008 | 2h | Show success, counts, version link |
| MERGE-UI-010 | Track merge operations in version history | ⏳ | frontend-developer | MERGE-UI-008 | 2h | Record merge operation in history |

**Status Legend**:
- `⏳` Not Started (Pending)
- `🔄` In Progress
- `✓` Complete
- `🚫` Blocked
- `⚠️` At Risk

---

## Architecture Context

### Current State

Phase 8 completed the DiffViewer component with basic syntax highlighting and two-way diffs. Phase 7 implemented merge API endpoints with three-way merge algorithm and conflict detection. Phase 9 bridges these by building the visual interface for merge operations.

### Design Requirements

**ColoredDiffViewer Specifications**:
- Input: `{local: string[], upstream: string[], merge_result: string[], conflicts: ConflictInfo[]}`
- Colors: Green (upstream change), Blue (local change), Red (conflict), Yellow (removed)
- Output: Rendered diff with color-coded chunks, line numbers, change type labels
- Features: Syntax highlighting, copy buttons per chunk, expand/collapse sections

**MergePreview Specifications**:
- Input: `{artifact: Artifact, merge_proposal: MergeProposal, stats: MergeStats}`
- Shows: Artifact name, merge source (branch/upstream), file count, change summary
- Stats: Auto-merged count, conflict count, unchanged count
- Features: Expandable file list, per-file status indicators

**Conflict Strategy Selection Specifications**:
- Per-conflict options: `ours`, `theirs`, `manual` (launch editor)
- State: Track user selections across all conflicts
- Preview: Show result of applying each strategy before final merge
- Feedback: Visual indication of resolved vs. pending conflicts

**MergeWorkflow Specifications**:
- Steps: Preview (view what's changing) → Conflicts (resolve conflicts) → Confirm (review selections) → Apply (execute merge)
- Progress: Clear step indicator showing current step and completion
- Navigation: Next/Previous buttons, skip optional steps
- Validation: Require conflict resolution before moving to Confirm

### Dependencies on Previous Phases

- **Phase 5 (Merge Algorithm)**: Three-way merge, conflict detection
- **Phase 6 (Diff Algorithm)**: Diff computation, chunk generation
- **Phase 7 (Merge API)**: POST /api/v1/projects/{id}/merge, conflict response
- **Phase 8 (Diff Viewer)**: DiffViewer component, syntax highlighting foundation

### Component Hierarchy

```
MergeWorkflow (orchestrator)
├── MergePreview (step 1)
│   └── Statistics display
├── ColoredDiffViewer (steps 2-3)
│   ├── Diff chunks with colors
│   ├── Change type labels
│   └── Syntax highlighting
├── ConflictResolver (step 2, if conflicts)
│   ├── Per-conflict UI
│   └── Strategy buttons (ours/theirs/manual)
└── ConfirmDialog (step 3)
    └── Summary of selections
```

---

## Implementation Notes

### Token Efficiency

This phase requires substantial component creation. Prioritize token efficiency:
- Reuse existing DiffViewer from Phase 8
- Reuse conflict-resolver component (already exists)
- Extract color mapping to constants, not inline
- Use composition over monolithic components

### Accessibility

Three-way merge UI requires specific accessibility considerations:
- Color alone insufficient to distinguish change types (SC-9) - always add text labels
- All strategy buttons must be keyboard accessible (Tab, Enter, Arrow keys)
- Workflow step navigation should be keyboard operable
- Screen reader support for diff chunks and conflict indicators
- High contrast for color-coded regions (WCAG AA minimum)

### Testing Strategy

Target >80% coverage (SC-7):
- Unit tests for color mapping logic
- Component tests for ColoredDiffViewer rendering
- Integration tests for MergeWorkflow step navigation
- E2E tests for complete merge flow: preview → resolve conflicts → apply
- Accessibility tests using axe-core or similar

### Key Integration Points

1. **With Phase 7 API**: MergeWorkflow calls POST /api/v1/projects/{id}/merge with user's strategy selections
2. **With Phase 8 DiffViewer**: ColoredDiffViewer extends existing DiffViewer, adds color layer
3. **With Version History**: MergeWorkflow result triggers version history update
4. **With Existing Conflict Resolver**: Reuse existing component, integrate into workflow

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Color scheme confusing for colorblind users | Medium | High | Always include text labels (SC-9); test with colorblind simulator |
| Three-way diff rendering complex | Medium | Medium | Break into smaller components; test incrementally |
| Conflict resolution state management complex | Medium | Medium | Use React Context or state management library; document flow |
| Accessibility not met | Low | High | Test with screen reader from start; follow WCAG AA |

---

## Git Workflow

- Create feature branch: `feature/phase-9-merge-ui`
- Commit strategy: One commit per component/feature
- PR to main with test coverage summary
- Final commit message should reference all MERGE-UI-* task IDs

---

## Related Phases

- **Phase 1**: Storage infrastructure (foundations)
- **Phase 5**: Merge algorithm (logic for this UI)
- **Phase 7**: Merge API endpoints (backend for apply)
- **Phase 8**: Diff Viewer (visual foundation)
- **Phase 10**: Documentation and release prep
