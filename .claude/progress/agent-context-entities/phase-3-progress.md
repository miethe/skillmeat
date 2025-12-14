---
type: progress
prd: "agent-context-entities"
phase: 3
phase_title: "Web UI"
status: pending
progress: 0
total_tasks: 9
completed_tasks: 0
created: "2025-12-14"
updated: "2025-12-14"

tasks:
  - id: "TASK-3.1"
    name: "Create Context Entities List Page"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.2", "TASK-3.5", "TASK-3.7", "TASK-3.8", "TASK-3.9"]
    estimate: 3

  - id: "TASK-3.2"
    name: "Create ContextEntityCard Component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.7"]
    estimate: 2

  - id: "TASK-3.3"
    name: "Create ContextEntityDetail Modal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.7", "TASK-3.8"]
    estimate: 3

  - id: "TASK-3.4"
    name: "Create ContextEntityEditor Component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.7", "TASK-3.9"]
    estimate: 3

  - id: "TASK-3.5"
    name: "Create Context Entity Filters Sidebar"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.7"]
    estimate: 2

  - id: "TASK-3.6"
    name: "Create DeployToProjectDialog Component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-3.7", "TASK-3.8", "TASK-3.9"]
    estimate: 2

  - id: "TASK-3.7"
    name: "Create TypeScript Types for Context Entities"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: []
    estimate: 1

  - id: "TASK-3.8"
    name: "Create API Client Functions"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.7"]
    estimate: 2

  - id: "TASK-3.9"
    name: "Create React Hooks for Context Entities"
    status: "pending"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-3.7", "TASK-3.8"]
    estimate: 2

parallelization:
  batch_1: ["TASK-3.7", "TASK-3.8"]
  batch_2: ["TASK-3.9"]
  batch_3: ["TASK-3.2", "TASK-3.3", "TASK-3.4", "TASK-3.5", "TASK-3.6"]
  batch_4: ["TASK-3.1"]
---

# Phase 3: Web UI

## Orchestration Quick Reference

**Batch 1** (Parallel - Foundation):
- TASK-3.7 → `ui-engineer` (1h)
- TASK-3.8 → `ui-engineer` (2h)

**Batch 2** (Sequential):
- TASK-3.9 → `ui-engineer` (2h)

**Batch 3** (Parallel - Components):
- TASK-3.2 → `ui-engineer-enhanced` (2h)
- TASK-3.3 → `ui-engineer-enhanced` (3h)
- TASK-3.4 → `ui-engineer-enhanced` (3h)
- TASK-3.5 → `ui-engineer` (2h)
- TASK-3.6 → `ui-engineer-enhanced` (2h)

**Batch 4** (Sequential - Integration):
- TASK-3.1 → `ui-engineer-enhanced` (3h)

### Task Delegation Commands

**Batch 1**:
```python
Task("ui-engineer", "TASK-3.7: Create TypeScript types for context entities. File: skillmeat/web/types/context-entity.ts. Types: ContextEntityType enum, ContextEntity interface, CreateContextEntityRequest, UpdateContextEntityRequest, ContextEntityListResponse, ContextEntityContentResponse, ContextEntityFilters. Match backend API schemas.")

Task("ui-engineer", "TASK-3.8: Create API client functions. File: skillmeat/web/lib/api/context-entities.ts. Implement fetchContextEntities, fetchContextEntity, createContextEntity, updateContextEntity, deleteContextEntity, fetchContextEntityContent, deployContextEntity. Follow patterns from lib/api/collections.ts.")
```

**Batch 2**:
```python
Task("ui-engineer", "TASK-3.9: Create React hooks with TanStack Query. File: skillmeat/web/hooks/use-context-entities.ts. Implement useContextEntities, useContextEntity, useCreateContextEntity, useUpdateContextEntity, useDeleteContextEntity. Query key factory pattern. Cache invalidation on mutations.")
```

**Batch 3**:
```python
Task("ui-engineer-enhanced", "TASK-3.2: Create ContextEntityCard component. File: skillmeat/web/components/context/context-entity-card.tsx. Display name, type badge, category, auto-load indicator, path pattern. Preview and Deploy buttons. Type-specific color coding.")

Task("ui-engineer-enhanced", "TASK-3.3: Create ContextEntityDetail modal with lazy loading. File: skillmeat/web/components/context/context-entity-detail.tsx. Tabs: Preview (rendered markdown with syntax highlighting), Metadata, Raw Content. Use react-markdown and react-syntax-highlighter. Deploy action button.")

Task("ui-engineer-enhanced", "TASK-3.4: Create ContextEntityEditor component with validation. File: skillmeat/web/components/context/context-entity-editor.tsx. Form with react-hook-form and Zod. Fields: name, type, path_pattern, category, auto_load, content, version. Path pattern validation (no .., must start with .claude/). Monospace textarea for content.")

Task("ui-engineer", "TASK-3.5: Create ContextEntityFilters sidebar. File: skillmeat/web/components/context/context-entity-filters.tsx. Filters: search input, type checkboxes, category select, auto-load toggle. Clear filters button. Update parent state on change.")

Task("ui-engineer-enhanced", "TASK-3.6: Create DeployToProjectDialog component. File: skillmeat/web/components/context/deploy-to-project-dialog.tsx. Project selector, target path display, overwrite warning. Call deployContextEntity API function. Success/error toasts.")
```

**Batch 4**:
```python
Task("ui-engineer-enhanced", "TASK-3.1: Create context entities list page. File: skillmeat/web/app/context-entities/page.tsx. Grid layout (responsive 1/2/3 columns). Filter sidebar integration. Loading/error/empty states. Pagination footer. Add Entity button. Use ContextEntityCard, ContextEntityFilters, and hooks.")
```

## Quality Gates

- [ ] All components render without errors
- [ ] TypeScript types match backend schemas
- [ ] API client handles all CRUD operations
- [ ] Query hooks fetch and cache data correctly
- [ ] Filters update entity list
- [ ] Markdown preview renders correctly
- [ ] Syntax highlighting works for code blocks
- [ ] Form validation prevents invalid submissions
- [ ] Loading and error states handled
- [ ] Responsive design works on mobile

## Notes

_Session notes go here_
