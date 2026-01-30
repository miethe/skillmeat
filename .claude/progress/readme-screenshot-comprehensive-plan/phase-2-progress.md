---
type: progress
prd: "readme-screenshot-comprehensive-plan"
phase: 2
status: in_progress
progress: 25
started_at: "2026-01-30T13:00:00Z"

tasks:
  - id: "TASK-2.1"
    name: "Start web dev server"
    status: "completed"
    assigned_to: ["bash"]
    dependencies: []
    notes: "Servers running on ports 3011 (Next.js) and 8080 (API)"

  - id: "TASK-2.2"
    name: "Capture README screenshots (6 primary)"
    status: "in_progress"
    assigned_to: ["claude-in-chrome", "chrome-devtools"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "hero-dashboard - DONE"
      - "feature-collection - DONE"
      - "feature-marketplace - DONE"
      - "feature-deploy - DONE"
      - "feature-sync - DONE (shows entity management, sync modal needs recapture)"
      - "cli-quickstart - PENDING"

  - id: "TASK-2.3"
    name: "Capture dashboard feature screenshots (4)"
    status: "pending"
    assigned_to: ["claude-in-chrome"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "dashboard-full"
      - "dashboard-stats"
      - "dashboard-trends"
      - "dashboard-top-artifacts"

  - id: "TASK-2.4"
    name: "Capture collection feature screenshots (6)"
    status: "pending"
    assigned_to: ["claude-in-chrome"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "collection-grid"
      - "collection-list"
      - "collection-filters"
      - "collection-artifact-modal"

  - id: "TASK-2.5"
    name: "Capture marketplace feature screenshots (6)"
    status: "pending"
    assigned_to: ["claude-in-chrome"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "marketplace-sources"
      - "marketplace-source-detail"
      - "marketplace-folder-detail"
      - "marketplace-publish"

  - id: "TASK-2.6"
    name: "Capture project/deployment screenshots (6)"
    status: "pending"
    assigned_to: ["claude-in-chrome"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "projects-list"
      - "projects-manage"
      - "deployments-flat"
      - "deployments-grouped"

  - id: "TASK-2.7"
    name: "Capture remaining feature screenshots"
    status: "pending"
    assigned_to: ["claude-in-chrome"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "manage-skills"
      - "context-entities-list"
      - "templates-list"
      - "mcp-list"
      - "settings-general"

  - id: "TASK-2.8"
    name: "Capture modal screenshots"
    status: "pending"
    assigned_to: ["claude-in-chrome"]
    dependencies: ["TASK-2.1"]
    subtasks:
      - "modal-diff-viewer"
      - "modal-conflict-resolver"

  - id: "TASK-2.9"
    name: "Update screenshots.json with capture dates"
    status: "pending"
    assigned_to: ["backend-typescript-architect"]
    dependencies: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6", "TASK-2.7", "TASK-2.8"]

  - id: "TASK-2.10"
    name: "Validate all screenshots exist"
    status: "pending"
    assigned_to: ["bash"]
    dependencies: ["TASK-2.9"]

parallelization:
  batch_1: ["TASK-2.1"]
  batch_2: ["TASK-2.2", "TASK-2.3", "TASK-2.4", "TASK-2.5", "TASK-2.6", "TASK-2.7", "TASK-2.8"]
  batch_3: ["TASK-2.9", "TASK-2.10"]

success_criteria:
  - "All 6 README screenshots captured"
  - "All feature screenshots captured (35 total)"
  - "Screenshots meet quality requirements (1280x720, light mode)"
  - "screenshots.json updated with capture dates"
  - "Validation script passes"
---

# Phase 2: Screenshot Capture

## Summary

Capture all screenshots for README and documentation using browser automation.

## Screenshot Requirements

- **Viewport**: 1280x720 (standard), 1000x700 (modals)
- **Theme**: Light mode
- **State**: Populated with sample data, no errors/loading states

## Capture Sequence

### README Screenshots (Priority)
1. hero-dashboard - Dashboard with all widgets
2. feature-collection - Collection grid view
3. feature-marketplace - Marketplace sources
4. feature-deploy - Deployments page
5. feature-sync - Sync modal with diff
6. cli-quickstart - Terminal output (separate)

### Feature Screenshots (By Page)
Systematic capture of all feature pages per screenshots.json
