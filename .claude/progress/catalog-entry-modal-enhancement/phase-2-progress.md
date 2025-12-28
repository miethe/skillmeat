---
type: progress
prd: "catalog-entry-modal-enhancement"
phase: 2
title: "Frontend Modal Enhancement"
status: pending
progress: 0
total_tasks: 10
completed_tasks: 0
blocked_tasks: 0
created: 2025-12-28
updated: 2025-12-28

tasks:
  - id: "TASK-2.1"
    title: "Add read-only mode to FileTree"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    acceptance: "Add readOnly: boolean prop. When true, hide create/delete file buttons. Disable drag-and-drop."
    files: ["skillmeat/web/components/entity/file-tree.tsx"]

  - id: "TASK-2.2"
    title: "Add read-only mode to ContentPane"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    acceptance: "Add readOnly: boolean prop. When true, hide edit/save buttons, set Monaco editor readOnly: true."
    files: ["skillmeat/web/components/entity/content-pane.tsx"]

  - id: "TASK-2.3"
    title: "Refactor CatalogEntryModal for tabs"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: []
    acceptance: "Add Radix UI Tabs component with Overview and Contents tabs. Maintain existing layout."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-2.4"
    title: "Implement Overview tab"
    status: "pending"
    priority: "high"
    estimate: "1 pt"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.3"]
    acceptance: "Migrate existing metadata display (badges, confidence scores, metadata grid, action buttons) to Overview tab."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-2.6"
    title: "Create TanStack Query hooks"
    status: "pending"
    priority: "high"
    estimate: "2 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-1.3", "TASK-1.4"]
    acceptance: "useCatalogFileTree(sourceId, artifactPath) and useCatalogFileContent(sourceId, artifactPath, filePath) hooks."
    files: ["skillmeat/web/hooks/use-catalog-files.ts", "skillmeat/web/lib/api/catalog.ts"]
    note: "Depends on Phase 1 backend endpoints"

  - id: "TASK-2.5"
    title: "Implement Contents tab"
    status: "pending"
    priority: "high"
    estimate: "3 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["TASK-2.1", "TASK-2.2", "TASK-2.3", "TASK-2.6"]
    acceptance: "Add FileTree (left) + ContentPane (right) layout. Wire file selection to update content pane."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-2.7"
    title: "Add loading skeletons"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2.5"]
    acceptance: "Skeleton for file tree (3 rows) and content pane (code editor placeholder) during fetch."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-2.8"
    title: "Add error states"
    status: "pending"
    priority: "medium"
    estimate: "2 pts"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2.5"]
    acceptance: "Rate limit error: 'GitHub rate limit reached. Try again in X minutes.' Fetch error: 'Failed to load file. Try again or View on GitHub.'"
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

  - id: "TASK-2.9"
    title: "Configure TanStack Query caching"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2.6"]
    acceptance: "Set staleTime: 5 * 60 * 1000 (5min) for file trees, 30 * 60 * 1000 (30min) for file contents. cacheTime: 30min/2hr."
    files: ["skillmeat/web/hooks/use-catalog-files.ts"]

  - id: "TASK-2.10"
    title: "Style tab layout"
    status: "pending"
    priority: "medium"
    estimate: "1 pt"
    assigned_to: ["ui-engineer"]
    dependencies: ["TASK-2.3", "TASK-2.4", "TASK-2.5"]
    acceptance: "Match unified-entity-modal design: tab triggers in DialogHeader, content area max-w-6xl, proper spacing."
    files: ["skillmeat/web/components/CatalogEntryModal.tsx"]

parallelization:
  batch_1: ["TASK-2.1", "TASK-2.2", "TASK-2.3"]
  batch_2: ["TASK-2.4", "TASK-2.6"]
  batch_3: ["TASK-2.5"]
  batch_4: ["TASK-2.7", "TASK-2.8", "TASK-2.9", "TASK-2.10"]

quality_gate:
  owner: "ui-engineer-enhanced"
  criteria:
    - "Modal renders correctly on all screen sizes (mobile, tablet, desktop)"
    - "TanStack Query hooks configured with correct staleTime/cacheTime"
    - "Loading skeletons appear during data fetch (no blank screens)"
    - "Error states display user-friendly messages (no raw error objects)"
    - "Design matches unified-entity-modal patterns (Radix UI, Tailwind)"

blockers: []

notes:
  - "Phase 2 depends on Phase 1 completion (TASK-2.6 needs backend endpoints)"
---

# Phase 2: Frontend Modal Enhancement

**Goal**: Create tabbed catalog modal with file browser and content viewer.

**Duration**: 4 days | **Effort**: 14 story points

**Dependency**: Phase 1 must be complete (requires backend file endpoints)

## Orchestration Quick Reference

### Batch 1 (Parallel - No Internal Dependencies)

```
Task("ui-engineer-enhanced", "TASK-2.1: Add readOnly prop to FileTree component in skillmeat/web/components/entity/file-tree.tsx. When true: hide create/delete file buttons, disable drag-and-drop if present, remove any mutation handlers. Keep tree expansion/collapse behavior.")

Task("ui-engineer-enhanced", "TASK-2.2: Add readOnly prop to ContentPane component in skillmeat/web/components/entity/content-pane.tsx. When true: hide edit/save buttons, set Monaco editor readOnly: true, hide any file operation controls. Keep syntax highlighting and scrolling.")

Task("ui-engineer-enhanced", "TASK-2.3: Refactor CatalogEntryModal in skillmeat/web/components/CatalogEntryModal.tsx to use Radix UI Tabs. Add Overview and Contents tabs. Import from @radix-ui/react-tabs. Match unified-entity-modal tab styling.")
```

### Batch 2 (After Batch 1 + Phase 1)

```
Task("ui-engineer-enhanced", "TASK-2.4: Implement Overview tab content in CatalogEntryModal. Move existing metadata display (type/status badges, confidence score breakdown, metadata grid with path/URL/version/SHA, action buttons) into TabsContent for 'overview'. Keep layout unchanged.")

Task("ui-engineer-enhanced", "TASK-2.6: Create TanStack Query hooks in skillmeat/web/hooks/use-catalog-files.ts. Create useCatalogFileTree(sourceId: string, entryId: string) and useCatalogFileContent(sourceId: string, entryId: string, filePath: string). Add API functions in skillmeat/web/lib/api/catalog.ts calling GET /marketplace/sources/{id}/artifacts/{path}/files endpoints.")
```

### Batch 3 (After Batch 1 + Batch 2)

```
Task("ui-engineer-enhanced", "TASK-2.5: Implement Contents tab in CatalogEntryModal. Add two-column layout: FileTree (left, 250px) + ContentPane (right, flex-1). Use useCatalogFileTree for tree data, useCatalogFileContent for selected file. Pass readOnly={true} to both components. Wire file selection: onClick in FileTree calls setSelectedPath, which triggers content fetch.")
```

### Batch 4 (After Batch 3 - Polish)

```
Task("ui-engineer", "TASK-2.7: Add loading skeletons to Contents tab in CatalogEntryModal. File tree: 3 Skeleton rows (h-4 w-full). Content pane: Skeleton rectangle (h-[400px] w-full) with subtle animation. Show while isLoading from hooks.")

Task("ui-engineer", "TASK-2.8: Add error states to Contents tab. Check isError from hooks. Rate limit (status 429): Show Alert with 'GitHub rate limit reached. Try again in X minutes.' with countdown. Other errors: 'Failed to load file. [Retry] or [View on GitHub]' with action buttons.")

Task("ui-engineer", "TASK-2.9: Configure TanStack Query caching in use-catalog-files.ts. File tree hook: staleTime: 5 * 60 * 1000, gcTime: 30 * 60 * 1000. Content hook: staleTime: 30 * 60 * 1000, gcTime: 2 * 60 * 60 * 1000. Add retry: 2 with exponential backoff.")

Task("ui-engineer", "TASK-2.10: Style tab layout in CatalogEntryModal. Match unified-entity-modal: TabsList in DialogHeader below title, TabsContent with max-w-6xl mx-auto, proper padding (p-4 for tabs content). Use consistent Tailwind classes.")
```

## Key Files

| File | Purpose |
|------|---------|
| `skillmeat/web/components/CatalogEntryModal.tsx` | Main modal refactoring |
| `skillmeat/web/components/entity/file-tree.tsx` | Add readOnly prop |
| `skillmeat/web/components/entity/content-pane.tsx` | Add readOnly prop |
| `skillmeat/web/hooks/use-catalog-files.ts` | New TanStack Query hooks |
| `skillmeat/web/lib/api/catalog.ts` | API client for file endpoints |

## Acceptance Criteria

- [ ] Modal has Overview and Contents tabs with proper navigation
- [ ] FileTree displays artifact file structure in read-only mode
- [ ] ContentPane shows syntax-highlighted file contents (no edit controls)
- [ ] TanStack Query caches file trees (5min) and contents (30min)
- [ ] Loading skeletons appear during data fetch
- [ ] Rate limit errors show user-friendly retry UI
- [ ] Design matches unified-entity-modal patterns (Radix UI, Tailwind)
