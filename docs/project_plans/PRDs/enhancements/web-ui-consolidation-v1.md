---
title: "PRD: Web UI Consolidation & Enhancements"
description: "Unified entity display, content viewing/editing, sync functionality, and performance improvements"
audience: [ai-agents, developers]
tags: [prd, web-ui, enhancement, consolidation, content-viewer, sync]
created: 2025-11-25
updated: 2025-11-25
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md
  - /docs/project_plans/artifact-version-tracking-sync-prd.md
---

# PRD: Web UI Consolidation & Enhancements

**Feature Name:** Web UI Consolidation & Enhancements

**Filepath Name:** `web-ui-consolidation-v1`

**Date:** 2025-11-25

**Version:** 1.0

**Status:** Draft

**Builds On:** Entity Lifecycle Management PRD (completed)

---

## 1. Executive Summary

This PRD addresses several gaps in the current web UI following the Entity Lifecycle Management implementation:

1. **Unified Entity Design** - Consolidate two modal designs into one consistent pattern
2. **Content Viewing/Editing** - Add file browser with content viewer and editor
3. **Sync Button Functionality** - Implement the non-functional sync button
4. **Performance Optimization** - Fix slow loading of deployed artifacts
5. **Sync Status Tab Enhancement** - Add functional merge/diff capabilities

**Priority:** HIGH

---

## 2. Problem Statement

### Current Issues

**1. Inconsistent Entity Display**
- `/collection` uses `artifact-detail.tsx` (Dialog modal)
- `/manage` pages use `entity-detail-panel.tsx` (Sheet/Side drawer)
- Different tab structures, different UX patterns
- User confusion when navigating between views

**2. No Content Viewing**
- Cannot view entity file contents from web UI
- No file tree visualization
- Cannot browse or edit individual files
- Must use external editor or CLI

**3. Non-Functional Sync Button**
- `handleSync()` in `/app/manage/page.tsx` only `console.log`s
- Toast indicates "not implemented"
- Core feature broken after lifecycle implementation

**4. Slow Deployed Artifacts Loading**
- `/projects/[id]/manage` page loads slowly
- No caching or pre-loading strategy
- Poor UX for projects with many entities

**5. Sync Status Tab Gaps**
- Buttons appear but don't function
- Merge/diff functionality exists but isn't integrated
- `merge-workflow.tsx`, `conflict-resolver.tsx`, `sync-dialog.tsx` components exist but aren't used in entity detail

---

## 3. Goals & Success Metrics

| Goal | Metric | Target |
|------|--------|--------|
| Unified entity display | Component variants | 1 (vs current 2) |
| Content viewing | Files viewable in UI | 100% of text files |
| File editing | Files editable | All text files |
| Sync button functional | Operations working | 100% |
| Page load time | Project entities load | < 1s (vs current 3-5s) |
| Merge accessibility | Merge from detail | Available in all contexts |

---

## 4. Requirements

### 4.1 Unified Entity Design (FR-1 to FR-3)

| ID | Requirement | Priority |
|:--:|-------------|:--------:|
| FR-1 | Single unified modal design based on collection's card/modal pattern | MUST |
| FR-2 | Modal used consistently on /collection, /manage, and /projects/[id]/manage | MUST |
| FR-3 | Card design consistent in catalog/grid views across all pages | MUST |

### 4.2 Content Viewing/Editing (FR-4 to FR-10)

| ID | Requirement | Priority |
|:--:|-------------|:--------:|
| FR-4 | "Contents" tab added to entity modal | MUST |
| FR-5 | File tree on left side showing entity structure | MUST |
| FR-6 | Content pane on right showing selected file | MUST |
| FR-7 | Scrollable content pane for large files | MUST |
| FR-8 | Add/update/delete files from within modal | MUST |
| FR-9 | "Edit" button for text files with inline editor | MUST |
| FR-10 | Markdown rendering with CodeMirror 6 split-view (editor + preview) | MUST |

### 4.3 Sync Button Implementation (FR-11 to FR-13)

| ID | Requirement | Priority |
|:--:|-------------|:--------:|
| FR-11 | Implement sync button on /manage page | MUST |
| FR-12 | Sync pulls from upstream (GitHub) to collection | MUST |
| FR-13 | Visual feedback during sync with SSE progress | SHOULD |

### 4.4 Performance Optimization (FR-14 to FR-17)

| ID | Requirement | Priority |
|:--:|-------------|:--------:|
| FR-14 | Pre-load or cache entity data for projects | MUST |
| FR-15 | Periodic background refresh (configurable interval) | SHOULD |
| FR-16 | Manual refresh button in project/entity view | MUST |
| FR-17 | Incremental loading with skeleton states | SHOULD |

### 4.5 Sync Status Tab Enhancement (FR-18 to FR-22)

| ID | Requirement | Priority |
|:--:|-------------|:--------:|
| FR-18 | Sync Status tab buttons functional (Deploy, Sync) | MUST |
| FR-19 | Integrate DiffViewer into Sync Status tab | MUST |
| FR-20 | Three-way merge support: collection, project, upstream | MUST |
| FR-21 | Conflict resolution workflow accessible from tab | MUST |
| FR-22 | Clear visual indicators for sync direction (pull/push) | SHOULD |

---

## 5. Scope

### In Scope
- Consolidate modal/card components
- Add Contents tab with file tree and viewer
- CodeMirror 6 integration for markdown editing
- File CRUD operations within modal
- Sync button implementation
- Performance optimization with caching
- Sync Status tab with merge/diff integration

### Out of Scope
- Real-time collaborative editing
- Binary file preview (images, PDFs)
- Syntax highlighting for all languages (markdown + common only)
- Version control within UI (beyond current diff/merge)

---

## 6. Technical Approach

### Unified Modal Component

```
<UnifiedEntityModal>
  ├── <ModalHeader> (name, type badge, status)
  ├── <Tabs>
  │   ├── Overview (metadata, tags, source)
  │   ├── Contents (NEW - file tree + viewer)
  │   ├── Sync Status (enhanced with merge)
  │   └── History (version timeline)
  ├── <ModalFooter> (action buttons)
  └── </Tabs>
</UnifiedEntityModal>
```

### Contents Tab Architecture

```
<ContentsTab>
  ├── <FileTree>
  │   ├── Folder expansion
  │   ├── File selection
  │   └── CRUD context menu
  ├── <ContentPane>
  │   ├── <FileHeader> (path, edit button)
  │   ├── <MarkdownEditor> (CodeMirror 6 + preview) OR
  │   └── <CodeViewer> (syntax highlighted read-only)
  └── </ContentPane>
</ContentsTab>
```

### Performance Strategy

1. **React Query Prefetching**: Prefetch entity data on hover
2. **Stale-While-Revalidate**: Serve cached data, refresh in background
3. **Optimistic Updates**: UI updates before API confirms
4. **Skeleton Loading**: Progressive rendering with placeholders

---

## 7. Dependencies

- **CodeMirror 6**: `@codemirror/state`, `@codemirror/view`, `@codemirror/lang-markdown`
- **Markdown Preview**: `react-markdown` + `remark-gfm`
- **Existing Components**: `DiffViewer`, `MergeWorkflow`, `ConflictResolver`
- **Backend APIs**: File content endpoints (may need extension)

---

## 8. Acceptance Criteria

- [ ] Single modal design used across /collection, /manage, /projects/[id]/manage
- [ ] Contents tab shows file tree with expandable folders
- [ ] Clicking file displays content with proper scrolling
- [ ] Markdown files render with split-view editor + preview
- [ ] Files can be added, updated, deleted from modal
- [ ] Sync button triggers actual sync operation
- [ ] Project entity page loads in < 1s
- [ ] Refresh button available in entity views
- [ ] Sync Status tab shows merge options with diff viewer
- [ ] Three-way merge workflow accessible from entity detail

---

## Implementation

See: `docs/project_plans/implementation_plans/enhancements/web-ui-consolidation-v1.md`
