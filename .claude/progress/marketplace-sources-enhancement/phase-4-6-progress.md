---
# === PROGRESS TRACKING: Phases 4-6 Frontend ===
# Components, pages, and dialogs for marketplace sources enhancement

# Metadata: Identification and Classification
type: progress
prd: "marketplace-sources-enhancement"
phase: 4
title: "Phases 4-6: Frontend Implementation"
status: "planning"
started: "2025-01-18"
completed: null

# Overall Progress
overall_progress: 0
completion_estimate: "on-track"

# Task Counts
total_tasks: 10
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

# Ownership
owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: []

# === TASKS (SOURCE OF TRUTH) ===
tasks:
  # Phase 4: Components
  - id: "UI-001"
    description: "Create SourceFilterBar component with artifact type, tags, trust level filters"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"

  - id: "UI-002"
    description: "Create TagBadge component (reuse patterns from collection)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1.5h"
    priority: "medium"

  - id: "UI-003"
    description: "Redesign SourceCard with tags, count tooltip, description fallback"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced", "frontend-developer"]
    dependencies: ["UI-002"]
    estimated_effort: "3h"
    priority: "high"

  - id: "UI-004"
    description: "Create RepoDetailsModal with ContentPane for description/README"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "medium"

  - id: "UI-005"
    description: "Create artifact count tooltip component (CountBadge)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "1h"
    priority: "medium"

  # Phase 5: Pages Integration
  - id: "UI-006"
    description: "Integrate filters into Sources list page with URL state sync"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["UI-001", "API-002"]
    estimated_effort: "3h"
    priority: "high"

  - id: "UI-007"
    description: "Add status filtering to Source detail page catalog"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["API-002"]
    estimated_effort: "2h"
    priority: "medium"

  - id: "UI-008"
    description: "Add Repo Details button to detail page (opens RepoDetailsModal)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["UI-004", "API-003"]
    estimated_effort: "1h"
    priority: "medium"

  # Phase 6: Dialogs
  - id: "UI-009"
    description: "Update CreateSourceDialog with import toggles (description, README)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["API-001"]
    estimated_effort: "1.5h"
    priority: "high"

  - id: "UI-010"
    description: "Update EditSourceDialog with toggles and tags input"
    status: "pending"
    assigned_to: ["frontend-developer", "ui-engineer-enhanced"]
    dependencies: ["UI-009"]
    estimated_effort: "2h"
    priority: "high"

# Parallelization Strategy
parallelization:
  batch_1: ["UI-001", "UI-002", "UI-004", "UI-005"]
  batch_2: ["UI-003"]
  batch_3: ["UI-006", "UI-007", "UI-008", "UI-009"]
  batch_4: ["UI-010"]
  critical_path: ["UI-001", "UI-006", "UI-009", "UI-010"]
  estimated_total_time: "10h"

# Blockers
blockers: []

# Success Criteria
success_criteria:
  - { id: "SC-1", description: "SourceFilterBar renders correctly with all filter options", status: "pending" }
  - { id: "SC-2", description: "Tag badges display with proper overflow handling (+n more)", status: "pending" }
  - { id: "SC-3", description: "Count badge shows total and type breakdown on hover", status: "pending" }
  - { id: "SC-4", description: "Filter state synced with URL query parameters", status: "pending" }
  - { id: "SC-5", description: "RepoDetailsModal accessible and keyboard navigable", status: "pending" }
  - { id: "SC-6", description: "All components meet WCAG 2.1 AA standards", status: "pending" }
  - { id: "SC-7", description: "Components work on desktop, tablet, mobile", status: "pending" }

# Files Modified
files_modified:
  - "skillmeat/web/types/marketplace.ts"
  - "skillmeat/web/components/marketplace/source-card.tsx"
  - "skillmeat/web/components/marketplace/source-filter-bar.tsx"
  - "skillmeat/web/components/marketplace/repo-details-modal.tsx"
  - "skillmeat/web/components/marketplace/tag-badge.tsx"
  - "skillmeat/web/components/marketplace/count-badge.tsx"
  - "skillmeat/web/app/marketplace/sources/page.tsx"
  - "skillmeat/web/app/marketplace/sources/[id]/page.tsx"
  - "skillmeat/web/components/dialogs/create-source-dialog.tsx"
  - "skillmeat/web/components/dialogs/edit-source-dialog.tsx"
---

# marketplace-sources-enhancement - Phases 4-6: Frontend Implementation

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/marketplace-sources-enhancement/phase-4-6-progress.md -t UI-001 -s completed
```

---

## Objective

Implement frontend components, pages, and dialogs for marketplace sources enhancement: create filter UI, redesign source cards with tags and count badges, add repo details modal, integrate filtering into list/detail pages, and update import/edit dialogs with new fields.

---

## Implementation Notes

### Architectural Decisions

- **shadcn/ui primitives**: Use Button, Badge, Dialog, Tooltip from shadcn/ui for consistency
- **TanStack Query**: Manage filter state and API calls with TanStack Query hooks
- **URL state sync**: Use `useSearchParams` from `next/navigation` for filter state in URL
- **Named exports only**: Follow project convention, no default exports

### Patterns and Best Practices

- Follow existing component patterns in `skillmeat/web/components/marketplace/`
- Use `cn()` utility for conditional class merging
- ARIA labels on all interactive elements (icon buttons, filters)
- Keyboard navigation: Tab through filters, Escape closes modals
- Color contrast minimum 4.5:1 for WCAG AA

### Known Gotchas

- Next.js 15: params must be awaited in page components
- Keep `'use client'` boundary as low as possible
- Tag overflow: show "+n more" when tags exceed maxDisplay
- Filter changes should provide <100ms UI feedback

### Development Setup

```bash
# Run frontend dev server
cd skillmeat/web && pnpm dev

# Run frontend tests
cd skillmeat/web && pnpm test

# Run specific component tests
cd skillmeat/web && pnpm test source-filter-bar
```

---

## Component Interface Reference

```typescript
// SourceFilterBar.tsx
interface SourceFilterBarProps {
  currentFilters: FilterState;
  onFilterChange: (filters: FilterState) => void;
  availableTags?: string[];
  trustLevels?: string[];
}

interface FilterState {
  artifact_type?: string;
  tags?: string[];
  trust_level?: string;
}

// TagBadge.tsx
interface TagBadgeProps {
  tags: string[];
  maxDisplay?: number;  // Default: 3
  onTagClick?: (tag: string) => void;
}

// CountBadge.tsx
interface CountBadgeProps {
  countsByType: Record<string, number>;
}

// RepoDetailsModal.tsx
interface RepoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  source: GitHubSource;
}
```

---

## Orchestration Quick Reference

### Batch Execution Commands

**Batch 1 (parallel)** - Independent components:
```
Task("ui-engineer-enhanced", "Implement UI-001: Create SourceFilterBar component with dropdowns for artifact_type, tags (multi-select chips), trust_level. Emit onFilterChange callback. Keyboard accessible. Files: skillmeat/web/components/marketplace/source-filter-bar.tsx", model="opus")
Task("ui-engineer-enhanced", "Implement UI-002: Create TagBadge component with color coding, overflow handling (+n more), hover tooltip, WCAG AA color contrast. Files: skillmeat/web/components/marketplace/tag-badge.tsx", model="opus")
Task("ui-engineer-enhanced", "Implement UI-004: Create RepoDetailsModal using Dialog from shadcn/ui. Display description section at top, README in scrollable ContentPane. Focus management, Escape to close. Files: skillmeat/web/components/marketplace/repo-details-modal.tsx", model="opus")
Task("frontend-developer", "Implement UI-005: Create CountBadge component showing total count with hover tooltip revealing type breakdown (Skills: 5, Commands: 3). ARIA label for accessibility. Files: skillmeat/web/components/marketplace/count-badge.tsx", model="opus")
```

**Batch 2 (after Batch 1)** - Source card redesign:
```
Task("ui-engineer-enhanced", "Implement UI-003: Redesign SourceCard to display tags (using TagBadge), count badge (using CountBadge), description fallback (user description or repo_description). Match artifact card visual patterns. Files: skillmeat/web/components/marketplace/source-card.tsx", model="opus")
```

**Batch 3 (after Batch 2 + API-002, parallel)** - Page integration:
```
Task("frontend-developer", "Implement UI-006: Integrate SourceFilterBar into sources list page. Sync filter state with URL using useSearchParams. Trigger API calls via TanStack Query on filter change. Add Clear Filters button. Files: skillmeat/web/app/marketplace/sources/page.tsx", model="opus")
Task("frontend-developer", "Implement UI-007: Add artifact type and status filters to source detail page catalog. Filter artifacts using query params. Files: skillmeat/web/app/marketplace/sources/[id]/page.tsx", model="opus")
Task("frontend-developer", "Implement UI-008: Add Repo Details button to source detail page (conditional: only if repo_description or repo_readme populated). Opens RepoDetailsModal. Files: skillmeat/web/app/marketplace/sources/[id]/page.tsx", model="opus")
Task("frontend-developer", "Implement UI-009: Update CreateSourceDialog with import_repo_description and import_repo_readme toggles (default false). Add help text tooltips. Files: skillmeat/web/components/dialogs/create-source-dialog.tsx", model="opus")
```

**Batch 4 (after Batch 3)** - Edit dialog:
```
Task("frontend-developer", "Implement UI-010: Update EditSourceDialog with toggles (mirrors create dialog) and tags input (comma-separated or chip entry, max 20, validation). Files: skillmeat/web/components/dialogs/edit-source-dialog.tsx", model="opus")
```

---

## Completion Notes

Summary of phase completion (fill in when phase is complete):

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
