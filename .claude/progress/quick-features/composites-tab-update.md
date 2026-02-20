---
feature: Composites Tab Update
status: completed
created: 2026-02-20
scope: frontend-only
files:
- skillmeat/web/types/artifact.ts
- skillmeat/web/components/shared/artifact-type-tabs.tsx
- skillmeat/web/app/manage/components/entity-tabs.tsx
tasks:
- id: QF-1
  title: Rename Plugin tab to Composites + add sub-type config
  file: skillmeat/web/types/artifact.ts
  status: completed
  assigned_to: ui-engineer-enhanced
- id: QF-2
  title: Update artifact-type-tabs with compact sizing + sub-type filter
  file: skillmeat/web/components/shared/artifact-type-tabs.tsx
  status: completed
  assigned_to: ui-engineer-enhanced
- id: QF-3
  title: Update entity-tabs with compact sizing + sub-type filter
  file: skillmeat/web/app/manage/components/entity-tabs.tsx
  status: completed
  assigned_to: ui-engineer-enhanced
total_tasks: 3
completed_tasks: 3
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
updated: '2026-02-20'
---

# Quick Feature: Composites Tab Update

## Goal
Update the "Plugins" tab on /collection and /manage pages to:
1. Cover all Composite Artifacts (renamed from "Plugins" to "Composites")
2. Add sub-type filtering within the tab (plugin, stack, suite)
3. Compact tab text so all tabs fit on one line

## Implementation Notes
- `composite_type` discriminator already exists: "plugin" | "stack" | "suite"
- Only "plugin" is actively used currently
- Tab grids use `grid-cols-6` (collection) and `grid-cols-5` (manage)
- Labels come from `ARTIFACT_TYPES` config in `types/artifact.ts`
