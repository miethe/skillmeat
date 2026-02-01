---
type: progress
prd: "manage-collection-page-refactor"
phase: 3
title: "Modal Separation"
status: "pending"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 6
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["ui-engineer-enhanced", "frontend-developer"]
contributors: []

tasks:
  - id: "MODAL-3.1"
    description: "Create ArtifactDetailsModal (collection-focused): Overview (default), Documentation, Dependencies, Advanced tabs. Emphasizes description, tools, tags. Includes 'Open in Manage' button. No sync/drift indicators."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["MODAL-3.3"]
    estimated_effort: "2.5h"
    priority: "high"
    model: "opus"

  - id: "MODAL-3.2"
    description: "Create ArtifactOperationsModal (manage-focused): Status (default), Deployments, Version History, Diff tabs. Emphasizes health, sync, version tracking. Includes 'View Full Details' button."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["MODAL-3.3"]
    estimated_effort: "2.5h"
    priority: "high"
    model: "opus"

  - id: "MODAL-3.3"
    description: "Extract shared modal components: TabNavigation, ModalHeader, TabContent wrapper for reuse across both modals."
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: []
    estimated_effort: "1h"
    priority: "high"
    model: "opus"

  - id: "MODAL-3.4"
    description: "Update CollectionsTabNavigation component with dual-button navigation showing 'View in Collection' and 'Open in Manage' for each collection."
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"

  - id: "MODAL-3.5"
    description: "Implement cross-navigation state preservation: URL state includes origin, return navigation possible, modal reopens correctly."
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["MODAL-3.1", "MODAL-3.2"]
    estimated_effort: "1h"
    priority: "medium"
    model: "opus"

  - id: "MODAL-3.6"
    description: "Integrate modals into respective pages: ArtifactDetailsModal to collection page, ArtifactOperationsModal to manage page."
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["MODAL-3.1", "MODAL-3.2", "MODAL-3.5"]
    estimated_effort: "1h"
    priority: "medium"
    model: "sonnet"

parallelization:
  batch_1: ["MODAL-3.3", "MODAL-3.4"]
  batch_2: ["MODAL-3.1", "MODAL-3.2"]
  batch_3: ["MODAL-3.5"]
  batch_4: ["MODAL-3.6"]
  critical_path: ["MODAL-3.3", "MODAL-3.1", "MODAL-3.5", "MODAL-3.6"]
  estimated_total_time: "6-8h"

blockers: []

success_criteria:
  - { id: "SC-3.1", description: "ArtifactDetailsModal shows discovery-focused content (no drift/sync)", status: "pending" }
  - { id: "SC-3.2", description: "ArtifactOperationsModal shows operations-focused content (health/sync/deployments)", status: "pending" }
  - { id: "SC-3.3", description: "Cross-navigation buttons present in both modals", status: "pending" }
  - { id: "SC-3.4", description: "Modals integrate into pages without errors", status: "pending" }
  - { id: "SC-3.5", description: "All tabs in both modals render and function correctly", status: "pending" }

files_modified:
  - "skillmeat/web/components/collection/artifact-details-modal.tsx"
  - "skillmeat/web/components/manage/artifact-operations-modal.tsx"
  - "skillmeat/web/components/shared/modal-header.tsx"
  - "skillmeat/web/components/shared/cross-navigation-buttons.tsx"
  - "skillmeat/web/components/shared/collections-tab-navigation.tsx"
  - "skillmeat/web/app/collection/page.tsx"
  - "skillmeat/web/app/manage/page.tsx"
---

# manage-collection-page-refactor - Phase 3: Modal Separation

**YAML frontmatter is the source of truth for tasks, status, and assignments.**

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/manage-collection-page-refactor/phase-3-progress.md -t MODAL-3.1 -s completed
```

---

## Objective

Create purpose-specific modals that reduce feature confusion and improve task completion flows. Discovery modal for browsing, operations modal for health management.

---

## Orchestration Quick Reference

### Batch 1 (Launch in parallel - single message)

```
Task("frontend-developer", "MODAL-3.3: Extract shared modal components. Create reusable TabNavigation, ModalHeader, TabContent wrapper components. Must be composable for both detail and operations modals. Ensure accessibility preserved (focus management). Files: skillmeat/web/components/shared/modal-header.tsx, skillmeat/web/components/shared/tab-navigation.tsx, skillmeat/web/components/shared/tab-content.tsx")

Task("ui-engineer-enhanced", "MODAL-3.4: Update CollectionsTabNavigation component. Add dual-button navigation showing 'View in Collection' and 'Open in Manage' for each collection. Buttons must navigate correctly, collection list renders properly, focus management correct. File: skillmeat/web/components/shared/collections-tab-navigation.tsx", model="sonnet")
```

### Batch 2 (After batch_1 completes)

```
Task("ui-engineer-enhanced", "MODAL-3.1: Create ArtifactDetailsModal (collection-focused). Tabs: Overview (default), Documentation, Dependencies, Advanced. Emphasizes description, tools, tags. Includes 'Open in Manage' cross-nav button. NO sync/drift indicators. Deploy and 'Add to Group' actions available. Use shared components from MODAL-3.3. File: skillmeat/web/components/collection/artifact-details-modal.tsx. Reference: /docs/design/ui-component-specs-page-refactor.md")

Task("ui-engineer-enhanced", "MODAL-3.2: Create ArtifactOperationsModal (manage-focused). Tabs: Status (default), Deployments, Version History, Diff. Shows health indicators, sync actions, version tracking. Includes 'View Full Details' cross-nav button. Use shared components from MODAL-3.3. File: skillmeat/web/components/manage/artifact-operations-modal.tsx. Reference: /docs/design/ui-component-specs-page-refactor.md")
```

### Batch 3 (After batch_2 completes)

```
Task("frontend-developer", "MODAL-3.5: Implement cross-navigation state preservation. URL state must include origin page, enable return navigation, no data loss on navigation, modal reopens correctly after navigation. Files: skillmeat/web/app/collection/page.tsx, skillmeat/web/app/manage/page.tsx")
```

### Batch 4 (After batch_3 completes)

```
Task("frontend-developer", "MODAL-3.6: Integrate modals into respective pages. Wire ArtifactDetailsModal to collection page, ArtifactOperationsModal to manage page. Artifact data flows correctly, close handlers work, no console errors. Files: skillmeat/web/app/collection/page.tsx, skillmeat/web/app/manage/page.tsx", model="sonnet")
```

---

## Tasks Reference

| Task ID | Description | Assignee | Est. | Dependencies |
|---------|-------------|----------|------|--------------|
| MODAL-3.1 | Create ArtifactDetailsModal | ui-engineer-enhanced | 2.5h | MODAL-3.3 |
| MODAL-3.2 | Create ArtifactOperationsModal | ui-engineer-enhanced | 2.5h | MODAL-3.3 |
| MODAL-3.3 | Extract shared modal components | frontend-developer | 1h | - |
| MODAL-3.4 | Update CollectionsTabNavigation | ui-engineer-enhanced | 1h | - |
| MODAL-3.5 | Implement cross-navigation state | frontend-developer | 1h | MODAL-3.1, MODAL-3.2 |
| MODAL-3.6 | Integrate modals into pages | frontend-developer | 1h | MODAL-3.1, MODAL-3.2, MODAL-3.5 |

---

## Quality Gate

- [ ] ArtifactDetailsModal shows discovery-focused content (no drift/sync)
- [ ] ArtifactOperationsModal shows operations-focused content (health/sync/deployments)
- [ ] Cross-navigation buttons present in both modals
- [ ] Modals integrate into pages without errors
- [ ] All tabs in both modals render and function correctly

---

## Implementation Notes

### Architectural Decisions

- Shared components extracted early to avoid duplication
- Each modal optimized for its page's purpose
- Tab structure similar but content distinct
- Cross-navigation preserves user context

### Patterns and Best Practices

- Focus trapped inside modal (use Radix Dialog)
- ESC key closes modal
- URL state tracks open modal and active tab
- Lazy load tab content for performance

### Known Gotchas

- Existing `unified-entity-modal.tsx` is 650+ lines - extracting shared components will simplify
- Tab content may need suspense boundaries for lazy loading
- Cross-navigation must handle cases where artifact doesn't exist on target page

### Tab Structure Reference

```
ArtifactDetailsModal (Collection)
  - Overview (default): name, description, author, tools, tags, score
  - Documentation: readme, usage examples
  - Dependencies: required artifacts
  - Advanced: raw YAML, metadata

ArtifactOperationsModal (Manage)
  - Status (default): health, drift, sync status
  - Deployments: where deployed, versions
  - Version History: changelog, commits
  - Diff: compare versions
```

---

## Completion Notes

(Fill in when phase is complete)
