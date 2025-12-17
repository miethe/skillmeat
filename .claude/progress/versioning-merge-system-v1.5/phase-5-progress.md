---
type: progress
prd: versioning-merge-system-v1.5
phase: 5
title: "Web UI Integration"
status: pending
created: 2025-12-17
updated: 2025-12-17
duration_estimate: "2 days"
effort_estimate: "12-16h"
priority: MEDIUM

tasks:
  - id: "TASK-5.1"
    description: "Update frontend types to include change_origin field"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1-2h"
    priority: "MEDIUM"
    files:
      - "skillmeat/web/types/sync.ts"
      - "skillmeat/web/types/drift.ts"

  - id: "TASK-5.2"
    description: "Add ChangeBadge component for change origin display"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "3-4h"
    priority: "MEDIUM"
    files:
      - "skillmeat/web/components/sync/ChangeBadge.tsx"

  - id: "TASK-5.3"
    description: "Update diff viewer to show badges"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.2"]
    estimated_effort: "3-4h"
    priority: "MEDIUM"
    files:
      - "skillmeat/web/components/sync/DiffViewer.tsx"

  - id: "TASK-5.4"
    description: "Update version timeline to show change origin labels"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.2"]
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "skillmeat/web/components/sync/VersionTimeline.tsx"

  - id: "TASK-5.5"
    description: "Add tooltips explaining badge meanings"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.2"]
    estimated_effort: "1-2h"
    priority: "LOW"
    files:
      - "skillmeat/web/components/sync/ChangeBadge.tsx"

  - id: "TASK-5.6"
    description: "Write frontend tests for badge rendering"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-5.2"]
    estimated_effort: "2-3h"
    priority: "MEDIUM"
    files:
      - "skillmeat/web/__tests__/components/sync/ChangeBadge.test.tsx"

parallelization:
  batch_1: ["TASK-5.1", "TASK-5.2"]
  batch_2: ["TASK-5.3", "TASK-5.4", "TASK-5.5", "TASK-5.6"]

completion: 0%
---

# Phase 5: Web UI Integration

## Overview

Integrate change attribution into the web UI by adding visual badges and labels to show the origin of each change (upstream, local, both/conflict).

**Goal**: Make change attribution visible and understandable in the UI.

**Duration**: 2 days | **Effort**: 12-16h | **Priority**: MEDIUM

---

## Tasks

### TASK-5.1: Update frontend types to include change_origin field
**Status**: Pending | **Effort**: 1-2h | **Priority**: MEDIUM

**Description**:
Update TypeScript types to include `change_origin` field in drift detection and diff API responses.

**Files**:
- `skillmeat/web/types/sync.ts`
- `skillmeat/web/types/drift.ts`

**Type Updates**:
```typescript
// types/drift.ts
export interface DriftFile {
  path: string;
  status: 'added' | 'modified' | 'deleted';
  change_origin?: 'upstream' | 'local' | 'both' | 'none';
}

export interface DriftDetection {
  has_drift: boolean;
  files: DriftFile[];
  summary?: DriftSummary;
  baseline_hash?: string;
  current_hash?: string;
  modification_detected_at?: string;
}

export interface DriftSummary {
  total_files: number;
  upstream_changes: number;
  local_changes: number;
  conflicts: number;
  no_changes: number;
}

// types/sync.ts
export interface FileDiff {
  path: string;
  diff: string;
  change_origin?: 'upstream' | 'local' | 'both' | 'none';
  baseline_hash?: string;
  deployed_hash?: string;
  upstream_hash?: string;
}
```

**Acceptance Criteria**:
- [ ] Types updated with new fields
- [ ] All fields optional (backwards compatibility)
- [ ] TypeScript compilation succeeds
- [ ] No type errors in consuming components

---

### TASK-5.2: Add ChangeBadge component for change origin display
**Status**: Pending | **Effort**: 3-4h | **Priority**: MEDIUM

**Description**:
Create a reusable `ChangeBadge` component that displays a color-coded badge for change origin with optional tooltip.

**Files**:
- `skillmeat/web/components/sync/ChangeBadge.tsx`

**Component Spec**:
```typescript
interface ChangeBadgeProps {
  origin: 'upstream' | 'local' | 'both' | 'none';
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ChangeBadge({ origin, showTooltip = true, size = 'md' }: ChangeBadgeProps) {
  // Implementation
}
```

**Color Scheme**:
- **Upstream**: Blue badge (informational)
- **Local**: Amber badge (warning - modified locally)
- **Both**: Red badge (error - conflict)
- **None**: Gray badge (neutral - no changes)

**Badge Text**:
- Upstream: "Upstream"
- Local: "Local"
- Both: "Conflict"
- None: "No Change"

**Acceptance Criteria**:
- [ ] Component renders all 4 badge types
- [ ] Colors match design system (Radix UI)
- [ ] Size variants work (sm, md, lg)
- [ ] Tooltip optional
- [ ] Accessible (ARIA labels)

---

### TASK-5.3: Update diff viewer to show badges
**Status**: Pending | **Effort**: 3-4h | **Priority**: MEDIUM

**Description**:
Integrate `ChangeBadge` into the diff viewer to show change origin for each file.

**Files**:
- `skillmeat/web/components/sync/DiffViewer.tsx`

**UI Layout**:
```
┌─────────────────────────────────────────┐
│ [📄 SKILL.md]          [Local Badge]    │
│ ────────────────────────────────────── │
│ @@ -1,3 +1,4 @@                          │
│ - old content                           │
│ + new content                           │
└─────────────────────────────────────────┘
```

**Implementation**:
- Add badge next to file name in file header
- Badge aligned right
- Badge color indicates change origin
- Tooltip shows explanation on hover

**Acceptance Criteria**:
- [ ] Badge displayed for each file
- [ ] Badge positioned correctly (right-aligned)
- [ ] Badge updates when API data changes
- [ ] No layout shift
- [ ] Responsive (mobile friendly)

**Dependencies**: TASK-5.2 (ChangeBadge component)

---

### TASK-5.4: Update version timeline to show change origin labels
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Add change origin labels to the version timeline to show how each version was created (deployment, sync, local modification).

**Files**:
- `skillmeat/web/components/sync/VersionTimeline.tsx`

**UI Layout**:
```
Timeline:
  ● v1.2.0 (Deployment)     - Blue dot
  │
  ● v1.2.1 (Sync)           - Green dot
  │
  ● (Local changes)         - Amber dot
  │
  ● v1.3.0 (Sync)           - Green dot
```

**Implementation**:
- Add change origin label below timestamp
- Use color-coded dots matching badge colors
- Show "Deployment", "Sync", or "Local changes"
- Style consistently with timeline design

**Acceptance Criteria**:
- [ ] Labels shown for all versions
- [ ] Colors match badge scheme
- [ ] Timeline layout preserved
- [ ] Responsive

**Dependencies**: TASK-5.2 (ChangeBadge component for color scheme)

---

### TASK-5.5: Add tooltips explaining badge meanings
**Status**: Pending | **Effort**: 1-2h | **Priority**: LOW

**Description**:
Add informative tooltips to change badges explaining what each origin means.

**Files**:
- `skillmeat/web/components/sync/ChangeBadge.tsx`

**Tooltip Content**:
- **Upstream**: "Changed in upstream repository only"
- **Local**: "Modified locally (not in upstream)"
- **Conflict**: "Changed both locally and upstream - requires merge"
- **None**: "No changes detected"

**Implementation**:
- Use Radix UI Tooltip component
- Show on hover (desktop) and tap (mobile)
- Delay: 300ms
- Position: top (auto-adjust if near edge)

**Acceptance Criteria**:
- [ ] Tooltips show on hover
- [ ] Content is clear and concise
- [ ] Accessible (keyboard navigation)
- [ ] Mobile friendly (tap to show)

**Dependencies**: TASK-5.2 (ChangeBadge component)

---

### TASK-5.6: Write frontend tests for badge rendering
**Status**: Pending | **Effort**: 2-3h | **Priority**: MEDIUM

**Description**:
Write component tests for `ChangeBadge` and integration tests for diff viewer and timeline with badges.

**Files**:
- `skillmeat/web/__tests__/components/sync/ChangeBadge.test.tsx`

**Test Cases**:

**Unit Tests (ChangeBadge)**:
1. Renders all 4 badge variants (upstream, local, both, none)
2. Correct colors applied
3. Size variants work (sm, md, lg)
4. Tooltip shows on hover
5. Tooltip disabled when showTooltip=false
6. Accessible (ARIA labels)

**Integration Tests (DiffViewer)**:
1. Badge displayed for each file
2. Badge updates when change_origin changes
3. Tooltip shows correct explanation

**Integration Tests (VersionTimeline)**:
1. Labels shown for all versions
2. Colors match change origin
3. Timeline layout preserved

**Acceptance Criteria**:
- [ ] All test cases pass
- [ ] >80% coverage for new components
- [ ] Tests run in CI

**Dependencies**: TASK-5.2 (ChangeBadge component)

---

## Orchestration Quick Reference

**Batch 1** (Parallel - Foundation):
- TASK-5.1 → `ui-engineer-enhanced` (1-2h)
- TASK-5.2 → `ui-engineer-enhanced` (3-4h)

**Batch 2** (Parallel - Integration):
- TASK-5.3 → `ui-engineer-enhanced` (3-4h)
- TASK-5.4 → `ui-engineer-enhanced` (2-3h)
- TASK-5.5 → `ui-engineer-enhanced` (1-2h)
- TASK-5.6 → `ui-engineer-enhanced` (2-3h)

### Task Delegation Commands

```typescript
// Batch 1: Foundation (parallel)
Task("ui-engineer-enhanced", `TASK-5.1: Update frontend types to include change_origin field

Files:
- skillmeat/web/types/sync.ts
- skillmeat/web/types/drift.ts

Type Updates:
- Add change_origin?: 'upstream' | 'local' | 'both' | 'none' to DriftFile
- Add summary?: DriftSummary to DriftDetection
- Add change_origin, baseline_hash, deployed_hash to FileDiff

Requirements:
- Fields are optional (backwards compatibility)
- TypeScript compiles without errors
- No type errors in consuming components

Acceptance:
- Types updated
- Compilation succeeds
- No type errors
`)

Task("ui-engineer-enhanced", `TASK-5.2: Add ChangeBadge component for change origin display

Files:
- skillmeat/web/components/sync/ChangeBadge.tsx

Component Spec:
interface ChangeBadgeProps {
  origin: 'upstream' | 'local' | 'both' | 'none';
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

Color Scheme:
- Upstream: Blue (informational)
- Local: Amber (warning)
- Both: Red (error/conflict)
- None: Gray (neutral)

Badge Text:
- Upstream: "Upstream"
- Local: "Local"
- Both: "Conflict"
- None: "No Change"

Requirements:
- Use Radix UI Badge component
- Size variants (sm, md, lg)
- Optional tooltip (see TASK-5.5)
- Accessible (ARIA labels)

Acceptance:
- All 4 badge types render
- Colors correct
- Size variants work
- Accessible
`)

// Batch 2: Integration (parallel after batch 1)
Task("ui-engineer-enhanced", `TASK-5.3: Update diff viewer to show badges

Files:
- skillmeat/web/components/sync/DiffViewer.tsx

Requirements:
- Add ChangeBadge next to file name in file header
- Badge aligned right
- Badge updates when change_origin changes
- No layout shift
- Responsive

Layout:
┌─────────────────────────────────────────┐
│ [📄 SKILL.md]          [Local Badge]    │
│ ────────────────────────────────────── │
│ diff content...                         │
└─────────────────────────────────────────┘

Depends on: TASK-5.2 (ChangeBadge)

Acceptance:
- Badge displayed correctly
- Positioned right
- Updates dynamically
- Responsive
`)

Task("ui-engineer-enhanced", `TASK-5.4: Update version timeline to show change origin labels

Files:
- skillmeat/web/components/sync/VersionTimeline.tsx

Requirements:
- Add change origin label below timestamp
- Use color-coded dots matching badge colors
- Show "Deployment", "Sync", or "Local changes"
- Preserve timeline layout

UI:
● v1.2.0 (Deployment)   - Blue
│
● v1.2.1 (Sync)         - Green
│
● (Local changes)       - Amber

Depends on: TASK-5.2 (for color scheme)

Acceptance:
- Labels shown
- Colors match
- Layout preserved
- Responsive
`)

Task("ui-engineer-enhanced", `TASK-5.5: Add tooltips explaining badge meanings

Files:
- skillmeat/web/components/sync/ChangeBadge.tsx

Tooltip Content:
- Upstream: "Changed in upstream repository only"
- Local: "Modified locally (not in upstream)"
- Conflict: "Changed both locally and upstream - requires merge"
- None: "No changes detected"

Requirements:
- Use Radix UI Tooltip
- Show on hover (300ms delay)
- Position: top (auto-adjust)
- Accessible (keyboard navigation)
- Mobile friendly (tap to show)

Depends on: TASK-5.2 (ChangeBadge)

Acceptance:
- Tooltips show on hover
- Content clear
- Accessible
- Mobile works
`)

Task("ui-engineer-enhanced", `TASK-5.6: Write frontend tests for badge rendering

Files:
- skillmeat/web/__tests__/components/sync/ChangeBadge.test.tsx

Test Cases:
1. ChangeBadge renders all 4 variants
2. Correct colors applied
3. Size variants work
4. Tooltip shows on hover
5. Tooltip disabled when showTooltip=false
6. DiffViewer shows badges
7. VersionTimeline shows labels
8. Accessible

Depends on: TASK-5.2 (ChangeBadge)

Coverage: >80%
`)
```

---

## Success Criteria

- [ ] All tasks completed
- [ ] Change badges displayed in diff viewer
- [ ] Change origin labels shown in timeline
- [ ] Tooltips explain badge meanings
- [ ] Frontend tests pass (>80% coverage)
- [ ] Responsive design
- [ ] Accessible (ARIA, keyboard navigation)

---

## Dependencies

**Blocks**:
- Phase 6 (Testing & Validation) - needs UI for manual testing

**Blocked By**:
- Phase 4 (Change Attribution Logic) - API must return change_origin

---

## Notes

**Design System**: Use Radix UI components for consistency (Badge, Tooltip).

**Color Scheme**:
- Blue (Upstream): Informational, no action needed
- Amber (Local): Warning, local changes may be lost on sync
- Red (Conflict): Error, requires manual merge
- Gray (None): Neutral, no changes

**Accessibility**: All badges and tooltips must be keyboard-accessible and screen-reader friendly.

**Mobile**: Tooltips should show on tap (not just hover) for mobile users.
