---
title: "Implementation Plan: Web UI Consolidation & Enhancements"
description: "Phased implementation for unified entity display, content viewing, sync, and performance"
audience: [ai-agents, developers]
tags: [implementation, web-ui, frontend, codemirror]
created: 2025-11-25
updated: 2025-11-25
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md
---

# Implementation Plan: Web UI Consolidation & Enhancements

**PRD:** `docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md`

**Total Effort:** ~35 story points

**Phases:** 4

---

## Phase Overview

| Phase | Title | Effort | Key Deliverables |
|-------|-------|--------|------------------|
| 1 | Unified Modal & Sync Fix | 10 pts | Single modal, working sync button |
| 2 | Contents Tab & File Browser | 10 pts | File tree, content viewer |
| 3 | Content Editing & CodeMirror | 8 pts | File editing, markdown split-view |
| 4 | Performance & Merge Integration | 7 pts | Caching, Sync Status tab fixes |

---

## Phase 1: Unified Modal & Sync Fix

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced, frontend-developer

### Objective
Consolidate the two different modal implementations into one unified design and fix the non-functional sync button.

### Tasks

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|-------------------|-----|
| WUI-001 | Audit existing modals | Compare `entity-detail-panel.tsx` and `artifact-detail.tsx` | Document differences and decide target design | 1 |
| WUI-002 | Create UnifiedEntityModal | Build new modal component based on collection Dialog design | Modal renders with Overview tab | 3 |
| WUI-003 | Add Sync Status tab | Migrate sync status from entity-detail-panel | Tab shows status and buttons | 2 |
| WUI-004 | Add History tab | Migrate history/version timeline | Tab shows version history | 1 |
| WUI-005 | Implement handleSync | Replace console.log with actual sync logic | Sync triggers API call, shows progress | 2 |
| WUI-006 | Update /manage page | Use UnifiedEntityModal | Modal opens from entity cards | 1 |

### Key Files

**Create:**
- `skillmeat/web/components/entity/unified-entity-modal.tsx`

**Modify:**
- `skillmeat/web/app/manage/page.tsx` (handleSync implementation)
- `skillmeat/web/app/manage/components/entity-detail-panel.tsx` (deprecate or refactor)
- `skillmeat/web/components/collection/artifact-detail.tsx` (deprecate or refactor)

### Success Criteria
- [ ] Single modal component used across all entity views
- [ ] Sync button triggers actual sync operation
- [ ] Toast notification shows sync success/failure

---

## Phase 2: Contents Tab & File Browser

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced, frontend-developer

### Objective
Add a Contents tab to the unified modal with file tree navigation and content viewing.

### Tasks

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|-------------------|-----|
| WUI-007 | Create FileTree component | Expandable tree showing entity files/folders | Tree renders entity structure | 3 |
| WUI-008 | Create ContentPane component | Scrollable pane for file content display | Content displays with scrolling | 2 |
| WUI-009 | Add Contents tab to modal | Integrate FileTree + ContentPane | Tab shows file browser layout | 2 |
| WUI-010 | Backend: file content endpoint | Add API endpoint to fetch individual file contents | GET /api/v1/artifacts/{id}/files/{path} returns content | 2 |
| WUI-011 | Wire up file selection | Clicking file in tree loads content in pane | File content loads on click | 1 |

### Component Structure

```typescript
// FileTree props
interface FileTreeProps {
  entityId: string;
  files: FileNode[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onAddFile?: () => void;
  onDeleteFile?: (path: string) => void;
}

// ContentPane props
interface ContentPaneProps {
  path: string;
  content: string;
  isLoading: boolean;
  onEdit?: () => void;
}
```

### Key Files

**Create:**
- `skillmeat/web/components/entity/file-tree.tsx`
- `skillmeat/web/components/entity/content-pane.tsx`
- `skillmeat/web/components/entity/contents-tab.tsx`
- `skillmeat/api/routers/files.py` (or extend artifacts.py)

### Success Criteria
- [ ] Contents tab visible in unified modal
- [ ] File tree shows entity directory structure
- [ ] Clicking file displays content in pane
- [ ] Content pane scrolls for large files

---

## Phase 3: Content Editing & CodeMirror

**Duration:** 2-3 days
**Assigned Subagent(s):** frontend-developer, ui-engineer-enhanced

### Objective
Enable file editing with CodeMirror 6 integration and markdown split-view preview.

### Tasks

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|-------------------|-----|
| WUI-012 | Install CodeMirror 6 | Add @codemirror/* packages | Packages installed, no build errors | 1 |
| WUI-013 | Create MarkdownEditor | CodeMirror 6 editor with markdown syntax | Editor renders with highlighting | 3 |
| WUI-014 | Add split-view preview | Side-by-side editor + rendered markdown | Preview updates as you type | 2 |
| WUI-015 | Wire Edit button | Toggle between view and edit mode | Button switches modes | 1 |
| WUI-016 | Backend: file update endpoint | PUT endpoint to save file content | PUT /api/v1/artifacts/{id}/files/{path} saves | 1 |

### CodeMirror Setup

```typescript
// Required packages
"@codemirror/state": "^6.x",
"@codemirror/view": "^6.x",
"@codemirror/lang-markdown": "^6.x",
"@codemirror/language": "^6.x",
"@codemirror/commands": "^6.x",
"react-markdown": "^9.x",
"remark-gfm": "^4.x"
```

### Key Files

**Create:**
- `skillmeat/web/components/editor/markdown-editor.tsx`
- `skillmeat/web/components/editor/code-viewer.tsx`
- `skillmeat/web/components/editor/split-preview.tsx`

**Modify:**
- `skillmeat/web/components/entity/content-pane.tsx` (integrate editor)

### Success Criteria
- [ ] Edit button visible for text files
- [ ] CodeMirror 6 editor loads for markdown
- [ ] Split-view shows editor + preview side-by-side
- [ ] Changes can be saved to backend

---

## Phase 4: Performance & Merge Integration

**Duration:** 2 days
**Assigned Subagent(s):** frontend-developer, react-performance-optimizer

### Objective
Optimize entity loading performance and integrate merge/diff into Sync Status tab.

### Tasks

| ID | Task | Description | Acceptance Criteria | Est |
|----|------|-------------|-------------------|-----|
| WUI-017 | Add prefetching on hover | Prefetch entity data when hovering cards | Data ready when modal opens | 2 |
| WUI-018 | Implement skeleton loading | Show skeleton while entities load | Skeletons display during load | 1 |
| WUI-019 | Add refresh button | Manual refresh in entity/project views | Button triggers data refetch | 1 |
| WUI-020 | Integrate DiffViewer in Sync Status | Show diff when changes available | Diff viewer renders in tab | 1 |
| WUI-021 | Add merge workflow trigger | Button to start MergeWorkflow component | Merge dialog opens from tab | 1 |
| WUI-022 | Wire Sync Status buttons | Connect Deploy/Sync/Rollback to actions | Buttons trigger operations | 1 |

### Performance Strategy

```typescript
// Prefetch on hover
const prefetchEntity = usePrefetchQuery();

<EntityCard
  onMouseEnter={() => prefetchEntity(entity.id)}
  onClick={() => openModal(entity)}
/>

// Stale-while-revalidate
useQuery({
  queryKey: ['entities', projectId],
  staleTime: 5 * 60 * 1000, // 5 min
  gcTime: 30 * 60 * 1000,   // 30 min
});
```

### Key Files

**Modify:**
- `skillmeat/web/components/entity/entity-card.tsx` (add prefetch)
- `skillmeat/web/hooks/useEntityLifecycle.tsx` (prefetch logic)
- `skillmeat/web/components/entity/unified-entity-modal.tsx` (Sync Status integration)
- `skillmeat/web/app/manage/page.tsx` (refresh button)
- `skillmeat/web/app/projects/[id]/manage/page.tsx` (refresh button)

### Success Criteria
- [ ] Entity data prefetched on card hover
- [ ] Skeleton loading during data fetch
- [ ] Refresh button triggers reload
- [ ] Sync Status tab shows diff when changes exist
- [ ] Merge workflow accessible from Sync Status tab
- [ ] All Sync Status buttons are functional

---

## File CRUD Operations (Cross-Phase)

File add/update/delete spans Phases 2-3:

| Operation | Phase | Implementation |
|-----------|-------|----------------|
| View file | Phase 2 | FileTree selection + ContentPane |
| Create file | Phase 2 | Add file button in FileTree header |
| Edit file | Phase 3 | CodeMirror editor with save |
| Delete file | Phase 2 | Context menu or delete icon |

### Backend Endpoints Needed

```
GET    /api/v1/artifacts/{id}/files             # List files in entity
GET    /api/v1/artifacts/{id}/files/{path}      # Get file content
PUT    /api/v1/artifacts/{id}/files/{path}      # Update file content
POST   /api/v1/artifacts/{id}/files             # Create new file
DELETE /api/v1/artifacts/{id}/files/{path}      # Delete file
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| CodeMirror bundle size | Medium | Dynamic import, tree-shaking |
| Large file performance | Medium | Virtualized rendering, line limits |
| Breaking existing flows | High | Feature flag for new modal, gradual rollout |
| Backend file API complexity | Medium | Start with read-only, add mutations incrementally |

---

## Testing Strategy

### Unit Tests
- FileTree component (expansion, selection, CRUD callbacks)
- ContentPane (scroll, loading states)
- MarkdownEditor (content changes, preview sync)

### Integration Tests
- Modal opens from all pages consistently
- File tree loads entity structure
- Content displays correctly for different file types
- Sync operation completes successfully

### E2E Tests
- User browses entity contents
- User edits and saves markdown file
- User syncs entity from upstream
- User triggers merge workflow

---

## Definition of Done

- [ ] UnifiedEntityModal used on /collection, /manage, /projects/[id]/manage
- [ ] Contents tab shows file browser with tree + content pane
- [ ] Markdown files editable with CodeMirror split-view
- [ ] File CRUD operations work from modal
- [ ] Sync button functional with progress feedback
- [ ] Entity loading < 1s with prefetching/caching
- [ ] Refresh button available in views
- [ ] Sync Status tab has working buttons and merge integration
- [ ] DiffViewer accessible from Sync Status tab
- [ ] All unit/integration tests pass
