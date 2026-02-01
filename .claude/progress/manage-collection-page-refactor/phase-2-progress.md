---
type: progress
prd: "manage-collection-page-refactor"
phase: 2
title: "Card Components"
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
  - id: "CARD-2.1"
    description: "Create ArtifactBrowseCard component: discovery-focused with type icon, name, author, description (truncated), tags, tools, score badge, quick actions menu. No drift/sync indicators."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "2h"
    priority: "high"
    model: "opus"

  - id: "CARD-2.2"
    description: "Create ArtifactOperationsCard component: operations-focused with checkbox, type icon, name, version arrows, deployments, badges (drift/update), sync time, action buttons."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["CARD-2.3"]
    estimated_effort: "2h"
    priority: "high"
    model: "opus"

  - id: "CARD-2.3"
    description: "Create shared status utility components: StatusBadge, HealthIndicator, DeploymentBadgeStack with proper styling and tooltips."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1.5h"
    priority: "high"
    model: "opus"

  - id: "CARD-2.4"
    description: "Integrate ArtifactBrowseCard into collection page. Replace existing card rendering, update prop passing and event handlers."
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["CARD-2.1"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"

  - id: "CARD-2.5"
    description: "Integrate ArtifactOperationsCard into manage page. Replace existing card rendering, integrate bulk selection and action handlers."
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["CARD-2.2"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"

parallelization:
  batch_1: ["CARD-2.1", "CARD-2.3"]
  batch_2: ["CARD-2.2", "CARD-2.4"]
  batch_3: ["CARD-2.5"]
  critical_path: ["CARD-2.3", "CARD-2.2", "CARD-2.5"]
  estimated_total_time: "4-6h"

blockers: []

success_criteria:
  - { id: "SC-2.1", description: "ArtifactBrowseCard renders without drift indicators", status: "pending" }
  - { id: "SC-2.2", description: "ArtifactOperationsCard shows health and deployment status", status: "pending" }
  - { id: "SC-2.3", description: "Shared utilities (StatusBadge, HealthIndicator, DeploymentBadgeStack) exported and working", status: "pending" }
  - { id: "SC-2.4", description: "Both cards integrate into pages with no console errors", status: "pending" }
  - { id: "SC-2.5", description: "Quick actions on browse card and operation buttons on operations card functional", status: "pending" }

files_modified:
  - "skillmeat/web/components/collection/artifact-browse-card.tsx"
  - "skillmeat/web/components/manage/artifact-operations-card.tsx"
  - "skillmeat/web/components/shared/status-badge.tsx"
  - "skillmeat/web/components/shared/health-indicator.tsx"
  - "skillmeat/web/components/shared/deployment-badge-stack.tsx"
  - "skillmeat/web/app/collection/page.tsx"
  - "skillmeat/web/app/manage/page.tsx"
---

# manage-collection-page-refactor - Phase 2: Card Components

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/manage-collection-page-refactor/phase-2-progress.md -t CARD-2.1 -s completed
```

---

## Objective

Create distinct card components that reflect each page's purpose and reduce cognitive load. Browse cards emphasize discovery (description, tags, tools). Operations cards emphasize health (drift, sync, deployments).

---

## Orchestration Quick Reference

### Batch 1 (Launch in parallel - single message)

```
Task("ui-engineer-enhanced", "CARD-2.1: Create ArtifactBrowseCard component. Discovery-focused card with: type icon, name, author, description (truncated to 2-3 lines), tags, tools, score badge, quick actions menu. Must NOT show drift/sync indicators. Hover/focus states required. File: skillmeat/web/components/collection/artifact-browse-card.tsx. Reference: /docs/design/ui-component-specs-page-refactor.md")

Task("ui-engineer-enhanced", "CARD-2.3: Create shared status utility components. Create StatusBadge (all states), HealthIndicator (colored health display), DeploymentBadgeStack (with overflow handling). All need tooltips and accessible labels. Files: skillmeat/web/components/shared/status-badge.tsx, skillmeat/web/components/shared/health-indicator.tsx, skillmeat/web/components/shared/deployment-badge-stack.tsx")
```

### Batch 2 (After batch_1 completes)

```
Task("ui-engineer-enhanced", "CARD-2.2: Create ArtifactOperationsCard component. Operations-focused card with: checkbox selection, type icon, name, version arrows, deployments (using DeploymentBadgeStack), status badges (drift/update using StatusBadge), sync time, health indicator (using HealthIndicator), action buttons. File: skillmeat/web/components/manage/artifact-operations-card.tsx")

Task("frontend-developer", "CARD-2.4: Integrate ArtifactBrowseCard into collection page. Replace existing card rendering with new ArtifactBrowseCard. Update prop passing and event handlers. Ensure quick actions work and click opens modal. File: skillmeat/web/app/collection/page.tsx", model="sonnet")
```

### Batch 3 (After batch_2 completes)

```
Task("frontend-developer", "CARD-2.5: Integrate ArtifactOperationsCard into manage page. Replace existing card rendering with new ArtifactOperationsCard. Integrate bulk selection (checkboxes), wire up action handlers. File: skillmeat/web/app/manage/page.tsx", model="sonnet")
```

---

## Tasks Reference

| Task ID | Description | Assignee | Est. | Dependencies |
|---------|-------------|----------|------|--------------|
| CARD-2.1 | Create ArtifactBrowseCard | ui-engineer-enhanced | 2h | - |
| CARD-2.2 | Create ArtifactOperationsCard | ui-engineer-enhanced | 2h | CARD-2.3 |
| CARD-2.3 | Create shared status utilities | ui-engineer-enhanced | 1.5h | - |
| CARD-2.4 | Integrate browse card into collection | frontend-developer | 1h | CARD-2.1 |
| CARD-2.5 | Integrate operations card into manage | frontend-developer | 1h | CARD-2.2 |

---

## Quality Gate

- [ ] ArtifactBrowseCard renders without drift indicators
- [ ] ArtifactOperationsCard shows health and deployment status
- [ ] Shared utilities (StatusBadge, HealthIndicator, DeploymentBadgeStack) exported and working
- [ ] Both cards integrate into pages with no console errors
- [ ] Quick actions on browse card and operation buttons on operations card functional

---

## Implementation Notes

### Architectural Decisions

- Cards are purpose-specific, not generic (reduces cognitive load)
- Shared utilities extracted for consistency across cards
- Browse card intentionally hides operational details
- Operations card prioritizes actionable information

### Patterns and Best Practices

- Use `React.memo()` for card components (performance)
- Truncate description with CSS `line-clamp-2` or `line-clamp-3`
- DeploymentBadgeStack shows max 3 badges + "+N more" overflow
- Use `cn()` for conditional styling

### Known Gotchas

- Checkbox state for bulk selection managed at page level, not card level
- Quick actions menu needs portal to avoid z-index issues
- Status colors must have sufficient contrast (WCAG AA)

### Component Props Reference

```typescript
// ArtifactBrowseCard
interface ArtifactBrowseCardProps {
  artifact: Artifact;
  onSelect: () => void;
  onQuickAction: (action: string) => void;
}

// ArtifactOperationsCard
interface ArtifactOperationsCardProps {
  artifact: Artifact;
  selected: boolean;
  onSelectionChange: (selected: boolean) => void;
  onAction: (action: string) => void;
}
```

---

## Completion Notes

(Fill in when phase is complete)
