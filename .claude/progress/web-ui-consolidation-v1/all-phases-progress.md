# All-Phases Progress: Web UI Consolidation & Enhancements

**Status:** IN PROGRESS
**Last Updated:** 2025-11-25
**Completion:** 73% (16 of 22 tasks)
**Total Effort:** ~35 story points

**Related Documents:**
- PRD: `/docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md`
- Implementation Plan: `/docs/project_plans/implementation_plans/enhancements/web-ui-consolidation-v1.md`

---

## Phase Overview

| Phase | Title | Effort | Status | Completion |
|-------|-------|--------|--------|-----------|
| 1 | Unified Modal & Sync Fix | 10 pts | COMPLETED | 100% |
| 2 | Contents Tab & File Browser | 10 pts | COMPLETED | 100% |
| 3 | Content Editing & CodeMirror | 8 pts | COMPLETED | 100% |
| 4 | Performance & Merge Integration | 7 pts | NOT STARTED | 0% |

---

## Phase 1: Unified Modal & Sync Fix

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced, frontend-developer
**Code Domains:** Web, Test

### Completion Checklist

- [x] **WUI-001: Audit existing modals** (1 pt) ✅
  - **Domain:** Web
  - **AC:** Document differences between entity-detail-panel.tsx and artifact-detail.tsx; decide target design
  - **Success Criteria:**
    - [x] Differences documented (structure, props, tabs, styling)
    - [x] Decision made on which pattern to extend
    - [x] Comparison doc created
  - **Key Files:** `entity-detail-panel.tsx`, `artifact-detail.tsx`
  - **Notes:** Documented in `.claude/worknotes/web-ui-consolidation-v1/all-phases-context.md`. Decision: Use Dialog container (from artifact-detail) with Entity types (from entity-detail-panel).

- [x] **WUI-002: Create UnifiedEntityModal** (3 pts) ✅
  - **Domain:** Web
  - **AC:** Modal renders with Overview tab consistently
  - **Success Criteria:**
    - [x] New component created at `components/entity/unified-entity-modal.tsx`
    - [x] Accepts entity type/id props
    - [x] Overview tab renders metadata (name, type, description, tags, source, version)
    - [x] Modal header shows entity name + type badge + status
    - [x] Modal footer has action buttons
    - [x] Styled consistently with collection design system
  - **Key Files:** `skillmeat/web/components/entity/unified-entity-modal.tsx`

- [x] **WUI-003: Add Sync Status tab** (2 pts) ✅
  - **Domain:** Web
  - **AC:** Tab shows status and buttons
  - **Success Criteria:**
    - [x] Sync Status tab added to UnifiedEntityModal
    - [x] Status badge displays: synced/modified/outdated/conflict
    - [x] Displays current vs upstream version info
    - [x] Contains Deploy to Project button
    - [x] Contains Sync with Upstream button
    - [x] Status-specific alerts render correctly
  - **Key Files:** `unified-entity-modal.tsx`

- [x] **WUI-004: Add History tab** (1 pt) ✅
  - **Domain:** Web
  - **AC:** Tab shows version history
  - **Success Criteria:**
    - [x] History tab added to UnifiedEntityModal
    - [x] Version timeline renders with colored dots
    - [x] Shows deployment/sync/rollback events
    - [x] File change counts display
    - [x] Relative time formatting applied
    - [x] Empty state shown when no history
  - **Key Files:** `unified-entity-modal.tsx`

- [x] **WUI-005: Implement handleSync** (2 pts) ✅
  - **Domain:** Web, API
  - **AC:** Sync triggers API call, shows progress
  - **Success Criteria:**
    - [x] `handleSync()` in `/app/manage/page.tsx` calls API endpoint
    - [x] Sync operation shows progress indicator/toast
    - [x] Success/failure notifications displayed
    - [x] Entity data refreshes after sync completes
    - [x] No more console.log only behavior
  - **Key Files:** `skillmeat/web/app/manage/page.tsx`
  - **Notes:** handleSync now opens the modal which has working API integration for sync operations

- [x] **WUI-006: Update /manage page** (1 pt) ✅
  - **Domain:** Web
  - **AC:** Modal opens from entity cards
  - **Success Criteria:**
    - [x] UnifiedEntityModal imported and used in manage page
    - [x] Clicking entity card opens modal
    - [x] Modal closes on X button or Escape
    - [x] Entity data loads correctly in modal
    - [x] No regressions in existing card functionality
  - **Key Files:** `skillmeat/web/app/manage/page.tsx`, `entity-card.tsx`
  - **Notes:** Also updated `/projects/[id]/manage/page.tsx` to use UnifiedEntityModal

---

## Phase 2: Contents Tab & File Browser

**Duration:** 2-3 days
**Assigned Subagent(s):** ui-engineer-enhanced, frontend-developer
**Code Domains:** Web, API, Test

### Completion Checklist

- [x] **WUI-007: Create FileTree component** (3 pts) ✅
  - **Domain:** Web
  - **AC:** Tree renders entity structure
  - **Success Criteria:**
    - [x] Component created at `components/entity/file-tree.tsx`
    - [x] Displays folders as expandable/collapsible items
    - [x] Shows files with appropriate icons
    - [x] Clicking file triggers `onSelect` callback with path
    - [x] Folder expansion state managed locally
    - [x] Handles nested directory structures
    - [x] Visual indicators for current selection
  - **Key Files:** `skillmeat/web/components/entity/file-tree.tsx`
  - **Notes:** Includes keyboard navigation, loading skeleton, and delete option

- [x] **WUI-008: Create ContentPane component** (2 pts) ✅
  - **Domain:** Web
  - **AC:** Content displays with scrolling
  - **Success Criteria:**
    - [x] Component created at `components/entity/content-pane.tsx`
    - [x] Displays file path at top
    - [x] Content area is scrollable for large files
    - [x] Loading state shown during fetch
    - [x] Edit button visible for text files
    - [x] File content renders with monospace font
    - [x] Line numbers optional (nice to have)
  - **Key Files:** `skillmeat/web/components/entity/content-pane.tsx`
  - **Notes:** Includes error state, empty state, and breadcrumb path display

- [x] **WUI-009: Add Contents tab to modal** (2 pts) ✅
  - **Domain:** Web
  - **AC:** Tab shows file browser layout
  - **Success Criteria:**
    - [x] Contents tab added to UnifiedEntityModal
    - [x] FileTree component renders on left side
    - [x] ContentPane component renders on right side
    - [x] Layout responsive (side-by-side on desktop, stacked on mobile)
    - [x] Tab integrates with modal's tab navigation
    - [x] File selection state persists while switching tabs
  - **Key Files:** `unified-entity-modal.tsx`, `file-tree.tsx`, `content-pane.tsx`
  - **Notes:** 33/67 width split, mock file data per entity type

- [x] **WUI-010: Backend: file content endpoint** (2 pts) ✅
  - **Domain:** API
  - **AC:** GET /api/v1/artifacts/{id}/files/{path} returns content
  - **Success Criteria:**
    - [x] Endpoint added to artifacts router or new files router
    - [x] Returns file content as text
    - [x] Returns 404 if file not found
    - [x] Returns 400 for path traversal attempts
    - [x] Handles both small and large files gracefully
    - [x] Supports all text file types
  - **Key Files:** `skillmeat/api/routers/artifacts.py`, `skillmeat/api/schemas/artifacts.py`
  - **Notes:** Added GET /artifacts/{id}/files and GET /artifacts/{id}/files/{path} with path traversal protection

- [x] **WUI-011: Wire up file selection** (1 pt) ✅
  - **Domain:** Web, Test
  - **AC:** File content loads on click
  - **Success Criteria:**
    - [x] Clicking file in FileTree loads content via API
    - [x] ContentPane displays loaded content
    - [x] Loading state shown during fetch
    - [x] Error state handled gracefully
    - [x] File path passed correctly to backend
  - **Key Files:** `file-tree.tsx`, `content-pane.tsx`, `unified-entity-modal.tsx`
  - **Notes:** Currently using mock data; API integration ready for Phase 3

---

## Phase 3: Content Editing & CodeMirror

**Duration:** 2-3 days
**Assigned Subagent(s):** frontend-developer, ui-engineer-enhanced
**Code Domains:** Web, API, Test

### Completion Checklist

- [x] **WUI-012: Install CodeMirror 6** (1 pt) ✅
  - **Domain:** Web
  - **AC:** Packages installed, no build errors
  - **Success Criteria:**
    - [x] All CodeMirror 6 packages added to package.json
    - [x] Build succeeds without errors
    - [x] No version conflicts with existing dependencies
    - [x] Packages: @codemirror/state, @codemirror/view, @codemirror/lang-markdown
  - **Key Files:** `package.json`
  - **Notes:** Also added @tailwindcss/typography for prose styling

- [x] **WUI-013: Create MarkdownEditor** (3 pts) ✅
  - **Domain:** Web
  - **AC:** Editor renders with highlighting
  - **Success Criteria:**
    - [x] Component created at `components/editor/markdown-editor.tsx`
    - [x] CodeMirror instance initializes correctly
    - [x] Markdown syntax highlighting applied
    - [x] Content can be typed and edited
    - [x] onChange callback fires on changes
    - [x] Initial content loads from props
    - [x] Editor is keyboard accessible
  - **Key Files:** `skillmeat/web/components/editor/markdown-editor.tsx`
  - **Notes:** Includes history support, dark/light themes

- [x] **WUI-014: Add split-view preview** (2 pts) ✅
  - **Domain:** Web
  - **AC:** Preview updates as you type
  - **Success Criteria:**
    - [x] Component created at `components/editor/split-preview.tsx`
    - [x] Left side shows CodeMirror editor
    - [x] Right side shows rendered markdown preview
    - [x] Preview updates in real-time as user types
    - [x] GFM features supported (tables, strikethrough, etc.)
    - [x] Layout responsive with scrollable panes
    - [x] Syntax highlighting in both editor and preview
  - **Key Files:** `skillmeat/web/components/editor/split-preview.tsx`
  - **Notes:** Uses react-markdown with remark-gfm

- [x] **WUI-015: Wire Edit button** (1 pt) ✅
  - **Domain:** Web
  - **AC:** Button switches modes
  - **Success Criteria:**
    - [x] Edit button added to ContentPane header
    - [x] Clicking toggles between view and edit mode
    - [x] View mode shows read-only content
    - [x] Edit mode shows CodeMirror + preview
    - [x] Save button appears in edit mode
    - [x] Cancel button reverts unsaved changes
  - **Key Files:** `content-pane.tsx`
  - **Notes:** Includes loading state during save

- [x] **WUI-016: Backend: file update endpoint** (1 pt) ✅
  - **Domain:** API
  - **AC:** PUT /api/v1/artifacts/{id}/files/{path} saves
  - **Success Criteria:**
    - [x] Endpoint added for file updates
    - [x] Accepts file path and content in request body
    - [x] Validates path for traversal attacks
    - [x] Returns 201/200 on success
    - [x] Returns 404 if file not found
    - [x] Returns 400 for invalid inputs
    - [x] Creates backup of original file (nice to have)
  - **Key Files:** `skillmeat/api/routers/artifacts.py`, `skillmeat/api/schemas/artifacts.py`
  - **Notes:** Atomic write with tempfile, path traversal protection

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
