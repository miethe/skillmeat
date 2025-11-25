# All-Phases Progress: Web UI Consolidation & Enhancements

**Status:** NOT STARTED
**Last Updated:** 2025-11-25
**Completion:** 0% (0 of 22 tasks)
**Total Effort:** ~35 story points

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md`
- Implementation Plan: `/docs/project_plans/implementation_plans/enhancements/web-ui-consolidation-v1.md`

---

## Phase Overview

| Phase | Title | Effort | Status | Completion |
|-------|-------|--------|--------|-----------|
| 1 | Unified Modal & Sync Fix | 10 pts | NOT STARTED | 0% |
| 2 | Contents Tab & File Browser | 10 pts | NOT STARTED | 0% |
| 3 | Content Editing & CodeMirror | 8 pts | NOT STARTED | 0% |
| 4 | Performance & Merge Integration | 7 pts | NOT STARTED | 0% |

---

## Phase 1: Unified Modal & Sync Fix

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced, frontend-developer
**Code Domains:** Web, Test

### Completion Checklist

- [ ] **WUI-001: Audit existing modals** (1 pt)
  - **Domain:** Web
  - **AC:** Document differences between entity-detail-panel.tsx and artifact-detail.tsx; decide target design
  - **Success Criteria:**
    - [ ] Differences documented (structure, props, tabs, styling)
    - [ ] Decision made on which pattern to extend
    - [ ] Comparison doc created
  - **Key Files:** `entity-detail-panel.tsx`, `artifact-detail.tsx`

- [ ] **WUI-002: Create UnifiedEntityModal** (3 pts)
  - **Domain:** Web
  - **AC:** Modal renders with Overview tab consistently
  - **Success Criteria:**
    - [ ] New component created at `components/entity/unified-entity-modal.tsx`
    - [ ] Accepts entity type/id props
    - [ ] Overview tab renders metadata (name, type, description, tags, source, version)
    - [ ] Modal header shows entity name + type badge + status
    - [ ] Modal footer has action buttons
    - [ ] Styled consistently with collection design system
  - **Key Files:** `skillmeat/web/components/entity/unified-entity-modal.tsx`

- [ ] **WUI-003: Add Sync Status tab** (2 pts)
  - **Domain:** Web
  - **AC:** Tab shows status and buttons
  - **Success Criteria:**
    - [ ] Sync Status tab added to UnifiedEntityModal
    - [ ] Status badge displays: synced/modified/outdated/conflict
    - [ ] Displays current vs upstream version info
    - [ ] Contains Deploy to Project button
    - [ ] Contains Sync with Upstream button
    - [ ] Status-specific alerts render correctly
  - **Key Files:** `unified-entity-modal.tsx`

- [ ] **WUI-004: Add History tab** (1 pt)
  - **Domain:** Web
  - **AC:** Tab shows version history
  - **Success Criteria:**
    - [ ] History tab added to UnifiedEntityModal
    - [ ] Version timeline renders with colored dots
    - [ ] Shows deployment/sync/rollback events
    - [ ] File change counts display
    - [ ] Relative time formatting applied
    - [ ] Empty state shown when no history
  - **Key Files:** `unified-entity-modal.tsx`

- [ ] **WUI-005: Implement handleSync** (2 pts)
  - **Domain:** Web, API
  - **AC:** Sync triggers API call, shows progress
  - **Success Criteria:**
    - [ ] `handleSync()` in `/app/manage/page.tsx` calls API endpoint
    - [ ] Sync operation shows progress indicator/toast
    - [ ] Success/failure notifications displayed
    - [ ] Entity data refreshes after sync completes
    - [ ] No more console.log only behavior
  - **Key Files:** `skillmeat/web/app/manage/page.tsx`

- [ ] **WUI-006: Update /manage page** (1 pt)
  - **Domain:** Web
  - **AC:** Modal opens from entity cards
  - **Success Criteria:**
    - [ ] UnifiedEntityModal imported and used in manage page
    - [ ] Clicking entity card opens modal
    - [ ] Modal closes on X button or Escape
    - [ ] Entity data loads correctly in modal
    - [ ] No regressions in existing card functionality
  - **Key Files:** `skillmeat/web/app/manage/page.tsx`, `entity-card.tsx`

---

## Phase 2: Contents Tab & File Browser

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced, frontend-developer
**Code Domains:** Web, API, Test

### Completion Checklist

- [ ] **WUI-007: Create FileTree component** (3 pts)
  - **Domain:** Web
  - **AC:** Tree renders entity structure
  - **Success Criteria:**
    - [ ] Component created at `components/entity/file-tree.tsx`
    - [ ] Displays folders as expandable/collapsible items
    - [ ] Shows files with appropriate icons
    - [ ] Clicking file triggers `onSelect` callback with path
    - [ ] Folder expansion state managed locally
    - [ ] Handles nested directory structures
    - [ ] Visual indicators for current selection
  - **Key Files:** `skillmeat/web/components/entity/file-tree.tsx`

- [ ] **WUI-008: Create ContentPane component** (2 pts)
  - **Domain:** Web
  - **AC:** Content displays with scrolling
  - **Success Criteria:**
    - [ ] Component created at `components/entity/content-pane.tsx`
    - [ ] Displays file path at top
    - [ ] Content area is scrollable for large files
    - [ ] Loading state shown during fetch
    - [ ] Edit button visible for text files
    - [ ] File content renders with monospace font
    - [ ] Line numbers optional (nice to have)
  - **Key Files:** `skillmeat/web/components/entity/content-pane.tsx`

- [ ] **WUI-009: Add Contents tab to modal** (2 pts)
  - **Domain:** Web
  - **AC:** Tab shows file browser layout
  - **Success Criteria:**
    - [ ] Contents tab added to UnifiedEntityModal
    - [ ] FileTree component renders on left side
    - [ ] ContentPane component renders on right side
    - [ ] Layout responsive (side-by-side on desktop, stacked on mobile)
    - [ ] Tab integrates with modal's tab navigation
    - [ ] File selection state persists while switching tabs
  - **Key Files:** `unified-entity-modal.tsx`, `file-tree.tsx`, `content-pane.tsx`

- [ ] **WUI-010: Backend: file content endpoint** (2 pts)
  - **Domain:** API
  - **AC:** GET /api/v1/artifacts/{id}/files/{path} returns content
  - **Success Criteria:**
    - [ ] Endpoint added to artifacts router or new files router
    - [ ] Returns file content as text
    - [ ] Returns 404 if file not found
    - [ ] Returns 400 for path traversal attempts
    - [ ] Handles both small and large files gracefully
    - [ ] Supports all text file types
  - **Key Files:** `skillmeat/api/routers/artifacts.py` or `skillmeat/api/routers/files.py`

- [ ] **WUI-011: Wire up file selection** (1 pt)
  - **Domain:** Web, Test
  - **AC:** File content loads on click
  - **Success Criteria:**
    - [ ] Clicking file in FileTree loads content via API
    - [ ] ContentPane displays loaded content
    - [ ] Loading state shown during fetch
    - [ ] Error state handled gracefully
    - [ ] File path passed correctly to backend
  - **Key Files:** `file-tree.tsx`, `content-pane.tsx`, `contents-tab.tsx`

---

## Phase 3: Content Editing & CodeMirror

**Duration:** 2-3 days
**Assigned Subagent(s):** frontend-developer, ui-engineer-enhanced
**Code Domains:** Web, API, Test

### Completion Checklist

- [ ] **WUI-012: Install CodeMirror 6** (1 pt)
  - **Domain:** Web
  - **AC:** Packages installed, no build errors
  - **Success Criteria:**
    - [ ] All CodeMirror 6 packages added to package.json
    - [ ] Build succeeds without errors
    - [ ] No version conflicts with existing dependencies
    - [ ] Packages: @codemirror/state, @codemirror/view, @codemirror/lang-markdown
  - **Key Files:** `package.json`

- [ ] **WUI-013: Create MarkdownEditor** (3 pts)
  - **Domain:** Web
  - **AC:** Editor renders with highlighting
  - **Success Criteria:**
    - [ ] Component created at `components/editor/markdown-editor.tsx`
    - [ ] CodeMirror instance initializes correctly
    - [ ] Markdown syntax highlighting applied
    - [ ] Content can be typed and edited
    - [ ] onChange callback fires on changes
    - [ ] Initial content loads from props
    - [ ] Editor is keyboard accessible
  - **Key Files:** `skillmeat/web/components/editor/markdown-editor.tsx`

- [ ] **WUI-014: Add split-view preview** (2 pts)
  - **Domain:** Web
  - **AC:** Preview updates as you type
  - **Success Criteria:**
    - [ ] Component created at `components/editor/split-preview.tsx`
    - [ ] Left side shows CodeMirror editor
    - [ ] Right side shows rendered markdown preview
    - [ ] Preview updates in real-time as user types
    - [ ] GFM features supported (tables, strikethrough, etc.)
    - [ ] Layout responsive with scrollable panes
    - [ ] Syntax highlighting in both editor and preview
  - **Key Files:** `skillmeat/web/components/editor/split-preview.tsx`

- [ ] **WUI-015: Wire Edit button** (1 pt)
  - **Domain:** Web
  - **AC:** Button switches modes
  - **Success Criteria:**
    - [ ] Edit button added to ContentPane header
    - [ ] Clicking toggles between view and edit mode
    - [ ] View mode shows read-only content
    - [ ] Edit mode shows CodeMirror + preview
    - [ ] Save button appears in edit mode
    - [ ] Cancel button reverts unsaved changes
  - **Key Files:** `content-pane.tsx`

- [ ] **WUI-016: Backend: file update endpoint** (1 pt)
  - **Domain:** API
  - **AC:** PUT /api/v1/artifacts/{id}/files/{path} saves
  - **Success Criteria:**
    - [ ] Endpoint added for file updates
    - [ ] Accepts file path and content in request body
    - [ ] Validates path for traversal attacks
    - [ ] Returns 201/200 on success
    - [ ] Returns 404 if file not found
    - [ ] Returns 400 for invalid inputs
    - [ ] Creates backup of original file (nice to have)
  - **Key Files:** `skillmeat/api/routers/files.py`

---

## Phase 4: Performance & Merge Integration

**Duration:** 2 days
**Assigned Subagent(s):** frontend-developer, react-performance-optimizer
**Code Domains:** Web, Test

### Completion Checklist

- [ ] **WUI-017: Add prefetching on hover** (2 pts)
  - **Domain:** Web
  - **AC:** Data ready when modal opens
  - **Success Criteria:**
    - [ ] Prefetch query implemented using React Query
    - [ ] onMouseEnter on EntityCard triggers prefetch
    - [ ] Data cached before modal opens
    - [ ] Modal opens instantly with cached data
    - [ ] No unnecessary network requests
    - [ ] Works on both collection and project pages
  - **Key Files:** `entity-card.tsx`, `useEntityLifecycle.tsx`

- [ ] **WUI-018: Implement skeleton loading** (1 pt)
  - **Domain:** Web
  - **AC:** Skeletons display during load
  - **Success Criteria:**
    - [ ] Skeleton component created or imported
    - [ ] Shows skeleton in entity list during initial load
    - [ ] Shows skeleton in modal tabs during load
    - [ ] Smooth transition from skeleton to content
    - [ ] Improves perceived performance
  - **Key Files:** `entity-card.tsx`, `unified-entity-modal.tsx`

- [ ] **WUI-019: Add refresh button** (1 pt)
  - **Domain:** Web
  - **AC:** Button triggers data refetch
  - **Success Criteria:**
    - [ ] Refresh button added to page header
    - [ ] Clicking triggers `refetch()` on entity query
    - [ ] Shows loading state during refetch
    - [ ] Success/error feedback shown
    - [ ] Manual refresh available in entity detail
    - [ ] Works on both /manage and /projects/[id]/manage
  - **Key Files:** `skillmeat/web/app/manage/page.tsx`, `skillmeat/web/app/projects/[id]/manage/page.tsx`

- [ ] **WUI-020: Integrate DiffViewer in Sync Status** (1 pt)
  - **Domain:** Web
  - **AC:** Diff viewer renders in tab
  - **Success Criteria:**
    - [ ] DiffViewer component imported into Sync Status tab
    - [ ] Shows diff when changes available
    - [ ] Left side shows local version
    - [ ] Right side shows upstream version
    - [ ] Color coding: green (additions), red (deletions)
    - [ ] File list sidebar shows all changed files
  - **Key Files:** `unified-entity-modal.tsx`, `diff-viewer.tsx`

- [ ] **WUI-021: Add merge workflow trigger** (1 pt)
  - **Domain:** Web
  - **AC:** Merge dialog opens from tab
  - **Success Criteria:**
    - [ ] Merge button added to Sync Status tab
    - [ ] Clicking opens MergeWorkflow component
    - [ ] Merge workflow shows in modal or overlay
    - [ ] Conflict detection works
    - [ ] Progress stages display correctly
    - [ ] Completion status shown
  - **Key Files:** `unified-entity-modal.tsx`, `merge-workflow.tsx`

- [ ] **WUI-022: Wire Sync Status buttons** (1 pt)
  - **Domain:** Web
  - **AC:** Buttons trigger operations
  - **Success Criteria:**
    - [ ] Deploy to Project button calls deploy API
    - [ ] Sync with Upstream button calls sync API
    - [ ] Rollback button calls rollback API (if present)
    - [ ] All buttons show loading state during operation
    - [ ] Success/error notifications displayed
    - [ ] Entity data refreshes after operation
    - [ ] No console.log only behavior
  - **Key Files:** `unified-entity-modal.tsx`

---

## Cross-Phase Requirements

### File CRUD Operations

File add/update/delete is cross-phase:

| Operation | Phase | Component | Status |
|-----------|-------|-----------|--------|
| View file | 2 | ContentPane | WUI-008 |
| Create file | 2 | FileTree context menu | WUI-007 |
| Edit file | 3 | MarkdownEditor | WUI-013 |
| Delete file | 2 | FileTree context menu | WUI-007 |
| Save changes | 3 | Backend endpoint | WUI-016 |

---

## Testing & Validation

### Unit Tests
- [ ] FileTree component expansion/selection logic
- [ ] ContentPane scroll behavior
- [ ] MarkdownEditor content changes
- [ ] Split-preview sync
- [ ] Modal tab navigation

### Integration Tests
- [ ] Modal opens from all pages consistently
- [ ] File tree loads and displays correctly
- [ ] Content displays for different file types
- [ ] Sync operation completes successfully
- [ ] Merge workflow functions end-to-end

### E2E Tests
- [ ] User browses entity contents
- [ ] User edits and saves markdown file
- [ ] User syncs entity from upstream
- [ ] User triggers merge workflow

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
- [ ] No regressions in existing functionality
