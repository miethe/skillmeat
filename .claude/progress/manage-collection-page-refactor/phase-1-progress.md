---
type: progress
prd: "manage-collection-page-refactor"
phase: 1
title: "Page Structure & Navigation"
status: "pending"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: []

tasks:
  - id: "NAV-1.1"
    description: "Update sidebar navigation labels to 'Health & Sync' (/manage) and 'Collections' (/collection) with icon changes"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"
    model: "opus"

  - id: "NAV-1.2"
    description: "Add page headers with descriptions: Collection='Browse & Discover', Manage='Health & Sync'"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["NAV-1.5"]
    estimated_effort: "1h"
    priority: "high"
    model: "sonnet"

  - id: "NAV-1.3"
    description: "Implement deep link support for artifacts (?artifact={id}) on both pages"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"
    model: "opus"

  - id: "NAV-1.4"
    description: "Add cross-navigation buttons to UnifiedEntityModal ('Open in Manage' and 'View Full Details')"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["NAV-1.3"]
    estimated_effort: "1.5h"
    priority: "medium"
    model: "sonnet"

  - id: "NAV-1.5"
    description: "Create reusable PageHeader component with title, description, icon, and action button slots"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"
    model: "opus"

parallelization:
  batch_1: ["NAV-1.1", "NAV-1.3", "NAV-1.5"]
  batch_2: ["NAV-1.2", "NAV-1.4"]
  critical_path: ["NAV-1.5", "NAV-1.2"]
  estimated_total_time: "4-6h"

blockers: []

success_criteria:
  - { id: "SC-1.1", description: "Sidebar reflects new navigation labels", status: "pending" }
  - { id: "SC-1.2", description: "Page headers display with correct descriptions", status: "pending" }
  - { id: "SC-1.3", description: "Deep links (?artifact={id}) work on both pages", status: "pending" }
  - { id: "SC-1.4", description: "Modal cross-navigation buttons appear and function", status: "pending" }
  - { id: "SC-1.5", description: "No accessibility violations in navigation elements", status: "pending" }

files_modified:
  - "skillmeat/web/components/navigation.tsx"
  - "skillmeat/web/app/manage/page.tsx"
  - "skillmeat/web/app/collection/page.tsx"
  - "skillmeat/web/components/entity/unified-entity-modal.tsx"
  - "skillmeat/web/components/shared/page-header.tsx"
---

# manage-collection-page-refactor - Phase 1: Page Structure & Navigation

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/manage-collection-page-refactor/phase-1-progress.md -t NAV-1.1 -s completed
```

---

## Objective

Establish clear page identities through navigation, headers, and deep linking infrastructure. Users should immediately understand each page's purpose and be able to navigate between contexts.

---

## Orchestration Quick Reference

### Batch 1 (Launch in parallel - single message)

```
Task("ui-engineer-enhanced", "NAV-1.1: Update sidebar navigation labels. Change /manage label to 'Health & Sync' and /collection to 'Collections'. Update icons appropriately. Ensure hover states work and mobile nav updated. File: skillmeat/web/components/navigation.tsx")

Task("frontend-developer", "NAV-1.3: Implement deep link support for artifacts. Support ?artifact={id} query param on both /manage and /collection pages to open modal with specific artifact. URL should update on modal open, browser back button must work, links must be bookmarkable. Files: skillmeat/web/app/manage/page.tsx, skillmeat/web/app/collection/page.tsx")

Task("ui-engineer-enhanced", "NAV-1.5: Create PageHeader component. Reusable component with title, description, icon, and optional action button slots. Must be responsive and use semantic HTML. File: skillmeat/web/components/shared/page-header.tsx")
```

### Batch 2 (After batch_1 completes)

```
Task("frontend-developer", "NAV-1.2: Add page headers with descriptions using PageHeader component (NAV-1.5). Collection page: 'Browse & Discover', Manage page: 'Health & Sync'. Icons should display correctly, responsive on mobile. Files: skillmeat/web/app/manage/page.tsx, skillmeat/web/app/collection/page.tsx", model="sonnet")

Task("frontend-developer", "NAV-1.4: Add cross-navigation buttons to UnifiedEntityModal. 'Open in Manage' button shows in collection context, 'View Full Details' button shows in manage context. Navigation must preserve artifact state, modal closes on navigation. File: skillmeat/web/components/entity/unified-entity-modal.tsx", model="sonnet")
```

---

## Tasks Reference

| Task ID | Description | Assignee | Est. | Dependencies |
|---------|-------------|----------|------|--------------|
| NAV-1.1 | Update sidebar navigation labels | ui-engineer-enhanced | 1h | - |
| NAV-1.2 | Add page headers with descriptions | frontend-developer | 1h | NAV-1.5 |
| NAV-1.3 | Implement deep link support | frontend-developer | 2h | - |
| NAV-1.4 | Add cross-navigation buttons | frontend-developer | 1.5h | NAV-1.3 |
| NAV-1.5 | Create PageHeader component | ui-engineer-enhanced | 1h | - |

---

## Quality Gate

- [ ] Sidebar reflects new navigation labels
- [ ] Page headers display with correct descriptions
- [ ] Deep links (`?artifact={id}`) work on both pages
- [ ] Modal cross-navigation buttons appear and function
- [ ] No accessibility violations in navigation elements

---

## Implementation Notes

### Architectural Decisions

- PageHeader is a shared component to ensure consistency across pages
- Deep linking uses URL query params for bookmarkability
- Cross-navigation buttons placed in modal header area

### Patterns and Best Practices

- Use `useSearchParams()` from `next/navigation` for URL state
- Await params in Next.js 15 dynamic routes
- Modal state synced with URL for browser history support

### Known Gotchas

- Next.js 15 requires awaiting `params` and `searchParams`
- URL updates should use `router.replace()` to avoid history pollution
- Mobile nav requires separate update from desktop sidebar

---

## Completion Notes

(Fill in when phase is complete)
