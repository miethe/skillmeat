---
feature: sync-tab-collapsible-sections
status: completed
created: 2026-02-05
scope: 2 components, ~2 files
tasks:
- id: COLL-1
  name: Auto-collapsing empty deployments message
  status: completed
  file: skillmeat/web/components/entity/project-selector-for-diff.tsx
  assigned_to: ui-engineer-enhanced
- id: COLL-2
  name: Collapsible ArtifactFlowBanner with smart collapsed state
  status: completed
  file: skillmeat/web/components/sync-status/artifact-flow-banner.tsx
  assigned_to: ui-engineer-enhanced
schema_version: 2
doc_type: quick_feature
feature_slug: sync-tab-collapsible-sections
---

# Sync Tab Collapsible Sections

## Goal
Reduce vertical space consumption in the Sync Status tab of ArtifactOperationsModal to maximize DiffViewer visibility.

## Tasks

### COLL-1: Auto-collapsing empty deployments message
- File: `project-selector-for-diff.tsx` (lines 222-236)
- Current: Large centered block with h-12 folder icon, h3 heading, paragraph
- Target: Show full message initially, auto-collapse after 3s to a slim horizontal bar showing "No deployments found" text only
- Not expandable (no additional info to show)
- Re-shows full message on rescan trigger

### COLL-2: Collapsible ArtifactFlowBanner
- File: `artifact-flow-banner.tsx`
- Current: Always-expanded 3-tier flow visualization (~200px tall)
- Target: Collapsible with chevron indicator
- Default: expanded
- Collapsed state: slim horizontal bar with inline status summary
  - Show truncated SHA (7 chars) for each tier where available
  - Show fallback labels ("Not configured", "Not deployed") greyed out where data missing
- Click anywhere on collapsed bar to expand
- Subtle visual indicator when expanded that it's collapsible
