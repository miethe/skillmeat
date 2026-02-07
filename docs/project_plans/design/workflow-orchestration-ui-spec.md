---
title: Workflow Orchestration Engine - UI/UX Design Specification
description: Comprehensive design specification for the Workflow Builder, Library, Execution Dashboard, and Detail pages
audience: developers, designers
tags: [ui, ux, design, workflow, orchestration, frontend]
created: 2026-02-06
updated: 2026-02-06
category: design
status: draft
references:
  - skillmeat/web/app/**/*.tsx
  - skillmeat/web/components/**/*.tsx
  - skillmeat/web/hooks/index.ts
  - skillmeat/web/types/artifact.ts
---

# Workflow Orchestration Engine -- UI/UX Design Specification

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Information Architecture](#2-information-architecture)
3. [Page Layouts](#3-page-layouts)
   - 3.1 Workflow Library Page
   - 3.2 Workflow Builder Page
   - 3.3 Workflow Detail Page
   - 3.4 Execution Dashboard Page
4. [Component Inventory](#4-component-inventory)
5. [Interaction Patterns](#5-interaction-patterns)
6. [State Management](#6-state-management)
7. [Accessibility](#7-accessibility)
8. [Mobile / Responsive](#8-mobile--responsive)
9. [Design System Integration](#9-design-system-integration)
10. [Implementation Roadmap](#10-implementation-roadmap)

---

## 1. Design Philosophy

### Guiding Principles

The workflow orchestration UI follows the existing SkillMeat design language: **Linear/Notion-inspired**, clean, minimal, and precise. The interface must feel like a natural extension of the collection management experience rather than a bolted-on feature.

**Core tenets:**

- **Progressive disclosure** -- Show the simple case first; reveal complexity on demand. A workflow with three sequential stages should look trivially simple.
- **Artifact-native** -- Workflows are first-class citizens alongside Skills, Commands, and Agents. They share the same card patterns, badge language, and navigation primitives.
- **Builder, not diagrammer** -- The workflow builder is a structured form with drag-and-drop reordering, not a freeform node-graph canvas. This keeps implementation lean and the UX predictable.
- **Status at a glance** -- Every running execution is visible as a vertical timeline with clear status indicators. No hunting through logs to find what failed.

### Visual Language

| Token | Value | Usage |
|-------|-------|-------|
| Workflow accent color | `text-indigo-500` / `bg-indigo-500` | Workflow type badge, active stage indicator |
| Stage card radius | `rounded-lg` (8px) | Consistent with artifact cards |
| Stage connector | 2px solid `border-muted` | Vertical line connecting sequential stages |
| Parallel branch indicator | Dashed `border-muted` with fork icon | Visual cue for parallel execution |
| Spacing between stages | `gap-3` (12px) | Tighter than page sections, denser than card grids |
| Builder canvas padding | `p-6` | Matches main content area |

---

## 2. Information Architecture

### Navigation Integration

Add a new navigation section to the existing sidebar configuration in `components/navigation.tsx`:

```
Agent Context (existing section)
  Context Entities
  Templates

Workflows (NEW section)          <-- storageKey: 'workflows'
  Library         /workflows                icon: Workflow (or GitBranch)
  Executions      /workflows/executions     icon: Play
```

The section uses `Workflow` from lucide-react (or `GitBranch` as fallback) for the section icon, and individual nav items use `Library` and `Play`.

### URL Structure

| Route | Page | Notes |
|-------|------|-------|
| `/workflows` | Workflow Library | List/grid of all workflows |
| `/workflows/new` | Workflow Builder (create) | Empty builder canvas |
| `/workflows/[id]` | Workflow Detail | Read-only view of a workflow definition |
| `/workflows/[id]/edit` | Workflow Builder (edit) | Builder pre-populated with workflow data |
| `/workflows/executions` | Execution List | All executions across workflows |
| `/workflows/[id]/executions` | Filtered Execution List | Executions for a specific workflow |
| `/workflows/[id]/executions/[runId]` | Execution Dashboard | Single execution timeline view |

Query parameters follow existing conventions:

- `?search=` -- Free-text search
- `?tags=` -- Comma-separated tag filter
- `?status=` -- Execution status filter (pending, running, completed, failed, cancelled)
- `?tab=` -- Active tab within a detail/execution view
- `?view=` -- `grid` or `list` (library page)

---

## 3. Page Layouts

### 3.1 Workflow Library Page

**Route:** `/workflows`
**Component:** `app/workflows/page.tsx` (client component)
**Pattern:** Mirrors `/collection` page structure -- PageHeader + toolbar + content grid

#### Layout Wireframe

```
+---------------------------------------------------------------+
| [PageHeader]                                                   |
|   icon: Workflow    title: "Workflows"                         |
|   desc: "Build and manage orchestration workflows"             |
|   actions: [+ New Workflow]                                    |
+---------------------------------------------------------------+
| [Toolbar]                                                      |
|   [Search input]  [Tag filter]  [Sort dropdown]  [View toggle] |
+---------------------------------------------------------------+
| [Content Area]                                                 |
|                                                                |
|   [WorkflowCard]  [WorkflowCard]  [WorkflowCard]              |
|   [WorkflowCard]  [WorkflowCard]  [WorkflowCard]              |
|                                                                |
|   -- or in list mode --                                        |
|                                                                |
|   [WorkflowListItem]                                           |
|   [WorkflowListItem]                                           |
|   [WorkflowListItem]                                           |
+---------------------------------------------------------------+
```

#### WorkflowCard Design

Each card in the grid displays a workflow at a glance:

```
+-------------------------------------------+
| [Workflow icon]  My Deployment Pipeline    |
|                  3 stages  |  Last run 2h  |
|                                           |
| [tag: ci/cd] [tag: deploy] [tag: review]  |
|                                           |
| Created by user  |  Updated Jan 15        |
|                                           |
| [Run]  [Edit]  [...]                      |
+-------------------------------------------+
```

**Card specifications:**

- **Container:** `rounded-lg border bg-card p-4 hover:shadow-md transition-shadow cursor-pointer`
- **Title:** `text-sm font-semibold` -- single line, truncated with `truncate`
- **Metadata row:** `text-xs text-muted-foreground` -- stage count, last run relative time
- **Tags:** Up to 3 visible, `+N more` overflow. Use existing `Badge variant="outline"` with `text-xs`
- **Actions row:** `flex items-center gap-1 mt-3 pt-3 border-t`
  - "Run" -- `Button variant="default" size="sm"` with `Play` icon
  - "Edit" -- `Button variant="ghost" size="sm"` with `Pencil` icon
  - "..." -- `DropdownMenu` with Duplicate, Delete, Export options

**Grid layout:** `grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3`

#### WorkflowListItem Design

For list view, each row shows:

```
[Icon] My Deployment Pipeline   3 stages   Last run: 2h ago   [tags]   [Run] [Edit] [...]
```

- **Container:** `flex items-center gap-4 rounded-md border p-3 hover:bg-accent/50 transition-colors cursor-pointer`
- **Name column:** `flex-1 min-w-0` with `truncate`
- **Metadata columns:** Fixed widths, `text-xs text-muted-foreground`
- **Actions:** Same as card but inline

#### Empty State

```
+-------------------------------------------+
|                                           |
|          [Workflow illustration]           |
|                                           |
|    No workflows yet                       |
|    Create your first workflow to          |
|    orchestrate multi-stage operations.    |
|                                           |
|    [+ Create Workflow]                    |
|                                           |
+-------------------------------------------+
```

Uses existing empty state pattern: centered content with muted icon, title, description, and CTA button.

---

### 3.2 Workflow Builder Page

**Route:** `/workflows/new` (create) or `/workflows/[id]/edit` (edit)
**Component:** `app/workflows/[id]/edit/page.tsx` and `app/workflows/new/page.tsx` (both client)
**Pattern:** Full-width builder canvas with a fixed top bar and scrollable stage list

This is the most complex new page. The builder avoids a freeform canvas in favor of a **structured vertical stage list** that is faster to implement, more accessible, and sufficient for sequential/parallel workflow definition.

#### Layout Wireframe

```
+---------------------------------------------------------------+
| [Builder Top Bar]                                              |
|   [< Back]  "Untitled Workflow"  [Save Draft] [Save & Close]  |
+---------------------------------------------------------------+
| [Sidebar: Workflow Meta]     | [Canvas: Stage List]            |
|                              |                                 |
| Name: _______________        | +-----------------------------+ |
| Description: ________        | | Stage 1: Code Review        | |
| Tags: [ci] [deploy] [+]     | | Primary: code-reviewer agent| |
| Version: 1.0.0               | | Context: [code-style-guide] | |
|                              | | [drag handle] [edit] [x]   | |
|                              | +-----------------------------+ |
|                              |        |                        |
|                              |        v (connector)            |
|                              |        |                        |
|                              | +-----------------------------+ |
|                              | | Stage 2: Build & Test       | |
|                              | | Primary: builder agent      | |
|                              | | Context: [test-patterns]    | |
|                              | | [drag handle] [edit] [x]   | |
|                              | +-----------------------------+ |
|                              |        |                        |
|                              |        v                        |
|                              |        |                        |
|                              | +----[+ Add Stage]-------------+|
|                              |                                 |
+---------------------------------------------------------------+
```

#### Builder Top Bar

A sticky header specific to the builder context:

- **Container:** `sticky top-14 z-40 flex items-center justify-between border-b bg-background/95 backdrop-blur px-6 py-3`
  - Note: `top-14` accounts for the global header height (h-14)
- **Left side:** Back button (`ArrowLeft` icon button) + editable workflow name (inline text input, click to edit)
- **Right side:** "Save Draft" (`Button variant="outline" size="sm"`), "Save & Close" (`Button variant="default" size="sm"`)
- **Unsaved changes indicator:** A small `dot` indicator (6px circle, `bg-amber-500`) next to the name when there are unsaved changes

#### Sidebar: Workflow Metadata Panel

A fixed-width panel on the left for workflow-level settings:

- **Width:** `w-80` (320px), collapses on mobile
- **Container:** `border-r bg-muted/30 p-6 space-y-6 overflow-y-auto`
- **Sections:**
  1. **Name & Description** -- `Input` for name, `Textarea` for description
  2. **Tags** -- Existing tag input pattern with `Badge` chips and autocomplete
  3. **Version** -- Read-only display for saved workflows, editable `Input` for new
  4. **Global Context Policy** -- Default context modules applied to all stages unless overridden. Uses `ContextModulePicker` (see Component Inventory)
  5. **Execution Settings** -- Toggles for "Stop on first failure" (default: true), "Allow manual overrides at runtime" (default: false)

#### Canvas: Stage List

The main content area where stages are defined and ordered:

- **Container:** `flex-1 p-6 overflow-y-auto`
- **Stage list:** `space-y-0` (connectors provide visual spacing)

Each **Stage Card** in the canvas:

```
+-------------------------------------------------------+
| [drag-handle]  [#1]  Code Review           [edit] [x] |
|-------------------------------------------------------|
| Primary Agent: [code-reviewer] [Bot icon]              |
| Tools: [Read] [WebSearch]                              |
| Context: [code-style-guide] [review-checklist]         |
| Description: Reviews code changes for style and...     |
+-------------------------------------------------------+
```

**Stage Card specifications:**

- **Container:** `rounded-lg border bg-card p-4 relative group`
- **Drag handle:** `GripVertical` icon, `cursor-grab`, visible on hover (`opacity-0 group-hover:opacity-100 transition-opacity`)
- **Stage number badge:** `inline-flex items-center justify-center h-6 w-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold dark:bg-indigo-900 dark:text-indigo-300`
- **Title:** `text-sm font-semibold flex-1` -- inline editable
- **Action buttons:** `edit` (Pencil icon) opens stage editor panel, `x` (X icon) removes stage with confirmation
- **Content rows:** Each row is `flex items-center gap-2 text-xs text-muted-foreground mt-2`
- **Artifact references:** Shown as `Badge variant="secondary"` with the artifact type icon

**Stage Connector** (between cards):

```tsx
<div className="flex items-center justify-center py-1">
  <div className="h-6 w-px bg-border" />
</div>
```

For **parallel branches**, the connector splits:

```
        |
    +---+---+
    |       |
 [Stage]  [Stage]
    |       |
    +---+---+
        |
```

Parallel branch visual:

- The connector line splits via a horizontal bar with dashed borders
- Parallel stages sit side by side in a `flex gap-4` container
- Each parallel lane has its own vertical connector
- A "merge" connector brings them back together

**Add Stage Button:**

- Appears at the bottom of the stage list
- `Button variant="dashed" className="w-full border-dashed"` with `Plus` icon
- Label: "Add Stage"
- Also appears between stages on hover as a small `+` circle button (`absolute left-1/2 -translate-x-1/2`) centered on the connector line

#### Stage Editor (Slide-Over Panel)

When clicking "edit" on a stage card, a slide-over panel opens from the right:

- **Container:** `fixed inset-y-0 right-0 w-[480px] border-l bg-background shadow-xl z-50` with `transition-transform` animation
- **Backdrop:** Semi-transparent overlay `fixed inset-0 bg-black/20` (click to close)
- **Header:** Stage name + close button
- **Content:** Scrollable form with sections:

**Stage Editor Form Sections:**

1. **Basic Info**
   - Name: `Input`
   - Description: `Textarea`
   - Execution mode: `RadioGroup` -- "Sequential" (default) or "Parallel with previous"

2. **Roles (Agent Assignment)**
   - Primary Agent: `ArtifactPicker` component filtered to `type: 'agent'`
   - Supporting Tools: Multi-select `ArtifactPicker` filtered to `type: 'skill' | 'command'`
   - Each selected artifact shows as a removable `Badge`

3. **Context Policy**
   - Inherits global: `Checkbox` (default: true)
   - Additional context modules: `ContextModulePicker` (multi-select)
   - Override global: `Checkbox` (when checked, only stage-specific modules apply)
   - Each module shown as a card with name, description, memory count

4. **Advanced**
   - Timeout: `Input type="number"` with unit selector (seconds/minutes)
   - Retry count: `Input type="number"` (0-3, default: 0)
   - Failure action: `Select` -- "Stop workflow" | "Skip and continue" | "Retry then stop"

---

### 3.3 Workflow Detail Page

**Route:** `/workflows/[id]`
**Component:** `app/workflows/[id]/page.tsx` (server component wrapper, client content)
**Pattern:** Similar to artifact detail modal but as a full page with tabs

#### Layout Wireframe

```
+---------------------------------------------------------------+
| [PageHeader]                                                   |
|   [< Back to Library]                                          |
|   icon: Workflow  title: "My Deployment Pipeline"              |
|   desc: "Automated deployment with code review"                |
|   actions: [Run] [Edit] [...]                                  |
+---------------------------------------------------------------+
| [Tab Bar]                                                      |
|   [Stages]  [Executions]  [Settings]  [History]                |
+---------------------------------------------------------------+
| [Tab Content]                                                  |
|                                                                |
|   --- Stages Tab (default) ---                                 |
|   Read-only stage cards in vertical timeline                   |
|   Same visual as builder but without drag/edit controls        |
|                                                                |
|   --- Executions Tab ---                                       |
|   Filtered list of past/current executions for this workflow   |
|   Each row: run ID, status, started, duration, trigger         |
|                                                                |
|   --- Settings Tab ---                                         |
|   Read-only display of workflow metadata, tags, version        |
|   Global context policy display                                |
|                                                                |
|   --- History Tab ---                                          |
|   Version history with diff viewer (reuses existing pattern)   |
|                                                                |
+---------------------------------------------------------------+
```

#### Stages Tab (Read-Only Timeline)

Stage cards in this view are non-interactive read-only versions:

```
+-------------------------------------------------------+
| [#1]  Code Review                          [indigo]   |
|-------------------------------------------------------|
| Agent: code-reviewer                                   |
| Tools: Read, WebSearch                                 |
| Context: code-style-guide, review-checklist            |
| Timeout: 5 minutes  |  Retries: 1                     |
+-------------------------------------------------------+
        |
        v
+-------------------------------------------------------+
| [#2]  Build & Test                         [indigo]   |
| ...                                                    |
+-------------------------------------------------------+
```

- No drag handles, no edit/delete buttons
- Stage cards use `bg-muted/30` instead of `bg-card` to differentiate from the editable builder
- Click on an artifact reference badge navigates to that artifact's detail page

#### Run Action

The "Run" button in the header opens a **Run Configuration Dialog**:

```
+-------------------------------------------+
| Run Workflow                               |
|-------------------------------------------|
| Workflow: My Deployment Pipeline           |
|                                           |
| Override Context (optional):               |
| [Context module picker -- multi-select]    |
|                                           |
| Override Agents (optional):                |
| Stage 1: [agent picker -- pre-filled]     |
| Stage 2: [agent picker -- pre-filled]     |
|                                           |
| [Cancel]                   [Run Workflow]  |
+-------------------------------------------+
```

- Uses `Dialog` / `DialogContent` from shadcn
- Pre-populates all fields from the workflow definition
- Only shows override sections if workflow has "Allow manual overrides" enabled
- "Run Workflow" button: `Button variant="default"` with `Play` icon, triggers mutation

---

### 3.4 Execution Dashboard Page

**Route:** `/workflows/[id]/executions/[runId]`
**Component:** `app/workflows/[id]/executions/[runId]/page.tsx` (client component)
**Pattern:** Unique layout -- vertical timeline with expandable step details

This is the most visually distinctive page. It shows a running (or completed) workflow execution as a timeline.

#### Layout Wireframe

```
+---------------------------------------------------------------+
| [Execution Header]                                             |
|   Workflow: My Deployment Pipeline                             |
|   Run #47  |  Started: 2 min ago  |  Status: [Running...]     |
|   actions: [Pause] [Cancel]                                    |
+---------------------------------------------------------------+
| [Progress Bar]                                                 |
|   [=====>                                    ] 2/5 stages      |
+---------------------------------------------------------------+
| [Timeline + Detail Split]                                      |
|                                                                |
| [Timeline Column]          | [Detail Panel]                   |
|                            |                                   |
| [*] Stage 1: Code Review  | Stage 2: Build & Test             |
|     completed (45s)        | --------------------------------- |
|     |                      | Status: Running                   |
| [>] Stage 2: Build & Test | Agent: builder                    |
|     running (1:23)         | Started: 1 min ago                |
|     |                      | Duration: 1:23                    |
| [ ] Stage 3: Deploy       | --------------------------------- |
|     pending                | Context Consumed:                  |
|     |                      |   - test-patterns (2.1 KB)        |
| [ ] Stage 4: Verify       |   - build-config (0.8 KB)         |
|     pending                | --------------------------------- |
|     |                      | [Log Viewer]                      |
| [ ] Stage 5: Notify       |  > Building project...             |
|     pending                |  > Running test suite...           |
|                            |  > 47/52 tests passing...          |
|                            |                                   |
+---------------------------------------------------------------+
```

#### Execution Header

- **Container:** `border-b bg-background px-6 py-4`
- **Left side:** Workflow name (link back to workflow detail), run identifier, started timestamp
- **Right side:** Status badge + action buttons
- **Status badge mapping:**
  - `pending` -- `Badge variant="outline"` with `Clock` icon, `text-muted-foreground`
  - `running` -- `Badge` with `Loader2 animate-spin` icon, `bg-blue-100 text-blue-700`
  - `completed` -- `Badge` with `CheckCircle` icon, `bg-green-100 text-green-700`
  - `failed` -- `Badge` with `XCircle` icon, `bg-red-100 text-red-700`
  - `cancelled` -- `Badge` with `Ban` icon, `bg-amber-100 text-amber-700`
  - `paused` -- `Badge` with `Pause` icon, `bg-yellow-100 text-yellow-700`
- **Action buttons:**
  - Running: [Pause] (`Button variant="outline" size="sm"`) [Cancel] (`Button variant="destructive" size="sm"`)
  - Paused: [Resume] (`Button variant="default" size="sm"`) [Cancel] (`Button variant="destructive" size="sm"`)
  - Completed/Failed/Cancelled: [Re-run] (`Button variant="outline" size="sm"`)

#### Progress Bar

- **Container:** `border-b bg-muted/20 px-6 py-3`
- Uses shadcn `Progress` component
- Shows `N of M stages complete` text alongside the bar
- Animated fill when stages complete

#### Timeline Column

The left column is a vertical timeline showing all stages:

- **Width:** `w-72` (288px)
- **Container:** `border-r bg-muted/10 p-4 overflow-y-auto`

Each timeline node:

```tsx
<div className="flex items-start gap-3">
  {/* Status indicator */}
  <div className="relative flex flex-col items-center">
    <div className={cn(
      "flex h-8 w-8 items-center justify-center rounded-full border-2",
      status === 'completed' && "border-green-500 bg-green-50 text-green-600",
      status === 'running' && "border-blue-500 bg-blue-50 text-blue-600",
      status === 'failed' && "border-red-500 bg-red-50 text-red-600",
      status === 'pending' && "border-muted bg-muted/50 text-muted-foreground",
    )}>
      {/* Icon based on status */}
    </div>
    {/* Connector line to next node */}
    {!isLast && <div className="h-8 w-px bg-border" />}
  </div>

  {/* Stage info */}
  <button className={cn(
    "flex-1 rounded-md px-3 py-2 text-left text-sm transition-colors",
    isSelected && "bg-accent",
    "hover:bg-accent/50",
  )}>
    <div className="font-medium">{stage.name}</div>
    <div className="text-xs text-muted-foreground">
      {status === 'completed' && `completed (${duration})`}
      {status === 'running' && `running (${elapsed})`}
      {status === 'pending' && 'pending'}
      {status === 'failed' && `failed (${duration})`}
    </div>
  </button>
</div>
```

Clicking a timeline node selects it and shows its details in the right panel.

#### Detail Panel

The right panel shows details for the selected stage:

- **Container:** `flex-1 p-6 overflow-y-auto`
- **Header:** Stage name + status badge
- **Sections:**

1. **Agent & Tools** -- Shows assigned agent and tools with artifact badges
2. **Timing** -- Started, duration (live counter for running), ended
3. **Context Consumed** -- List of context modules injected, with byte sizes
4. **Log Viewer** -- Scrollable log output area

**Log Viewer specifications:**

- **Container:** `rounded-lg border bg-muted/30 p-4 font-mono text-xs overflow-y-auto max-h-[400px]`
- Uses `font-mono` (JetBrains Mono) for log content
- New lines auto-scroll to bottom when running (with a "scroll to bottom" button if user scrolls up)
- Supports ANSI color parsing for colored log output
- Empty state: "Waiting for logs..." with muted text
- Failed state: Error message highlighted with `bg-destructive/10 text-destructive` at the end of the log

#### Real-Time Updates

The execution dashboard uses **Server-Sent Events (SSE)** for real-time progress:

- Reuses existing `useSSE` hook from the hooks registry
- SSE endpoint: `GET /api/v1/workflows/{id}/executions/{runId}/stream`
- Events: `stage_started`, `stage_completed`, `stage_failed`, `log_line`, `execution_completed`
- The timeline and detail panel update reactively as events arrive
- Falls back to polling (30s interval) if SSE connection drops

---

## 4. Component Inventory

### New Components

#### Feature Components (`components/workflow/`)

| Component | File | Props | Description |
|-----------|------|-------|-------------|
| `WorkflowCard` | `workflow-card.tsx` | `workflow, onClick, onRun, onEdit, onDuplicate, onDelete` | Card for library grid view |
| `WorkflowListItem` | `workflow-list-item.tsx` | `workflow, onClick, onRun, onEdit, onDuplicate, onDelete` | Row for library list view |
| `WorkflowToolbar` | `workflow-toolbar.tsx` | `search, tags, sort, view, onChange*` | Filter/sort toolbar for library |
| `StageCard` | `stage-card.tsx` | `stage, index, mode ('edit'\|'readonly'), onEdit, onDelete, onDragStart, onDragEnd` | Stage card for builder/detail |
| `StageConnector` | `stage-connector.tsx` | `type ('sequential'\|'parallel-start'\|'parallel-end'), onAddStage?` | Visual connector between stages |
| `StageEditor` | `stage-editor.tsx` | `stage, open, onClose, onSave, artifacts, contextModules` | Slide-over panel for editing a stage |
| `StageTimeline` | `stage-timeline.tsx` | `stages, selectedStageId, onSelectStage` | Vertical timeline for execution view |
| `ExecutionHeader` | `execution-header.tsx` | `execution, onPause, onResume, onCancel, onRerun` | Header bar for execution dashboard |
| `ExecutionProgress` | `execution-progress.tsx` | `completedStages, totalStages, status` | Progress bar with stage count |
| `ExecutionDetail` | `execution-detail.tsx` | `stage, execution` | Right panel detail for selected stage |
| `LogViewer` | `log-viewer.tsx` | `logs, isLive, maxHeight?` | Monospace log viewer with auto-scroll |
| `RunWorkflowDialog` | `run-workflow-dialog.tsx` | `workflow, open, onClose, onRun` | Run configuration dialog |

#### Shared/Reusable Components (`components/shared/`)

| Component | File | Props | Description |
|-----------|------|-------|-------------|
| `ArtifactPicker` | `artifact-picker.tsx` | `value, onChange, filter: { types }, multi?, placeholder` | Searchable dropdown to select artifacts |
| `ContextModulePicker` | `context-module-picker.tsx` | `value, onChange, multi?, placeholder` | Searchable dropdown for context modules |
| `DragHandle` | `drag-handle.tsx` | `className?` | Reusable grip icon for drag-and-drop |
| `StatusDot` | `status-dot.tsx` | `status: ExecutionStatus, size?, pulse?` | Colored dot indicator with optional pulse animation |
| `InlineEdit` | `inline-edit.tsx` | `value, onChange, placeholder?, className?` | Click-to-edit text field |
| `SlideOverPanel` | `slide-over-panel.tsx` | `open, onClose, title, children, width?` | Reusable right-side slide-over |
| `VerticalTimeline` | `vertical-timeline.tsx` | `children` | Layout wrapper for vertical timeline nodes |
| `TimelineNode` | `timeline-node.tsx` | `status, icon, isLast, isSelected, onClick, children` | Individual node in a vertical timeline |

### Existing Components Reused

| Component | Location | Usage |
|-----------|----------|-------|
| `PageHeader` | `components/shared/page-header.tsx` | Library, Detail, Execution pages |
| `Badge` | `components/ui/badge` | Tags, status, artifact types |
| `Button` | `components/ui/button` | All action buttons |
| `Dialog` / `DialogContent` | `components/ui/dialog` | Run dialog, confirmations |
| `DropdownMenu` | `components/ui/dropdown-menu` | Card actions, sort options |
| `Input` / `Textarea` | `components/ui/input`, `components/ui/textarea` | Builder forms |
| `Tabs` / `TabsList` / `TabsTrigger` / `TabsContent` | `components/ui/tabs` | Detail page tabs |
| `TabNavigation` | `components/shared/tab-navigation.tsx` | Detail page tab bar |
| `Select` | `components/ui/select` | Dropdowns in stage editor |
| `Checkbox` | `components/ui/checkbox` | Settings toggles |
| `Skeleton` | `components/ui/skeleton` | Loading states |
| `Progress` | `components/ui/progress` | Execution progress bar |
| `Tooltip` | `components/ui/tooltip` | Icon button labels |
| `ScrollArea` | `components/ui/scroll-area` | Log viewer scroll |

---

## 5. Interaction Patterns

### 5.1 Drag and Drop (Stage Reordering)

**Library:** `@dnd-kit/core` + `@dnd-kit/sortable` (recommended for React, accessible, lightweight)

**Behavior:**

1. User grabs the drag handle (`GripVertical` icon) on a stage card
2. Card lifts with a subtle shadow (`shadow-lg`) and reduces opacity of the original position (`opacity-30`)
3. Drop indicators appear between stages as the card is dragged
4. On drop, stages reorder with a smooth `transition-all duration-200` animation
5. Stage numbers auto-recalculate after reorder

**Keyboard alternative:**

- Focus the drag handle
- Press `Space` or `Enter` to pick up
- `Arrow Up` / `Arrow Down` to move
- `Space` or `Enter` to drop
- `Escape` to cancel

**Constraints:**

- Parallel stages within a branch can only reorder within their branch
- Cannot drag a stage out of a parallel branch directly (must change execution mode first)

### 5.2 Artifact Picker Interaction

The `ArtifactPicker` is a `Popover`-based searchable selector:

1. Click the picker trigger (shows current selection or placeholder)
2. Popover opens with a search input at the top
3. Results are grouped by artifact type (Skills, Agents, Commands)
4. Each result row shows: artifact icon, name, description (truncated)
5. Click to select (single mode) or toggle (multi mode)
6. Selected items appear as removable `Badge` components below the trigger
7. Search debounced at 300ms using `useDebounce`

**Data source:** Reuses `useArtifacts` hook with type filter parameter.

### 5.3 Context Module Picker Interaction

Similar to ArtifactPicker but sourced from `useContextModules` hook:

1. Click trigger
2. Popover with search
3. Each module shows: name, description, memory item count
4. Multi-select with badges for selected modules
5. "Global modules" section at top shows inherited modules (if in stage context with global inheritance enabled)

### 5.4 Add Stage Between Existing Stages

On hover over a stage connector, a small circular `+` button fades in:

- **Position:** Absolutely centered on the connector line
- **Size:** `h-6 w-6 rounded-full`
- **Style:** `bg-primary text-primary-foreground shadow-sm opacity-0 hover:opacity-100 transition-opacity`
- **Behavior:** Click opens the stage editor panel pre-configured for a new stage at that position
- **Keyboard:** `Tab` focuses the add button between stages; `Enter` to activate

### 5.5 Keyboard Shortcuts

| Shortcut | Scope | Action |
|----------|-------|--------|
| `Cmd+S` / `Ctrl+S` | Builder | Save workflow |
| `Cmd+Enter` / `Ctrl+Enter` | Builder | Save and close |
| `Escape` | Builder (editor open) | Close stage editor panel |
| `Escape` | Builder (editor closed) | Prompt to save if unsaved changes |
| `Cmd+N` / `Ctrl+N` | Builder | Add new stage at end |
| `Delete` / `Backspace` | Builder (stage focused) | Delete focused stage (with confirmation) |
| `Cmd+D` / `Ctrl+D` | Builder (stage focused) | Duplicate focused stage |
| `J` / `K` | Execution Dashboard | Navigate up/down in timeline |
| `Cmd+R` / `Ctrl+R` | Detail Page | Run workflow |

Shortcuts are registered via the existing `useKeyboardShortcuts` hook pattern.

### 5.6 Animations

| Element | Trigger | Animation | Implementation |
|---------|---------|-----------|----------------|
| Stage card | Add | `animate-in fade-in-0 slide-in-from-top-2` | Tailwind animation utility |
| Stage card | Remove | `animate-out fade-out-0 slide-out-to-top-2` | Tailwind animation utility |
| Stage card | Reorder | `transition-all duration-200` | dnd-kit default |
| Slide-over panel | Open | `translate-x-0` from `translate-x-full` | CSS transition (300ms ease-out) |
| Slide-over panel | Close | `translate-x-full` from `translate-x-0` | CSS transition (200ms ease-in) |
| Timeline node | Status change | `transition-colors duration-300` | Tailwind transition |
| Progress bar | Update | Smooth width transition | shadcn Progress component default |
| Log line | Append | None (instant) | Performance: no animation on frequent updates |
| Connector add button | Hover | `opacity-0 to opacity-100` | `transition-opacity duration-150` |
| Unsaved dot | Appear | `animate-pulse` | Tailwind pulse animation |

---

## 6. State Management

### 6.1 Data Types

```typescript
// types/workflow.ts

export type WorkflowStatus = 'draft' | 'published' | 'archived';
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
export type StageExecutionMode = 'sequential' | 'parallel';
export type StageFailureAction = 'stop' | 'skip' | 'retry_then_stop';

export interface WorkflowStageRole {
  /** Primary agent artifact ID */
  primaryAgent?: string;
  /** Supporting tool/skill artifact IDs */
  tools?: string[];
}

export interface WorkflowStageContextPolicy {
  /** Whether this stage inherits global context modules */
  inheritGlobal: boolean;
  /** Additional context module IDs specific to this stage */
  moduleIds: string[];
}

export interface WorkflowStage {
  /** Unique stage ID (UUID) */
  id: string;
  /** Human-readable stage name */
  name: string;
  /** Optional description */
  description?: string;
  /** Execution mode relative to the previous stage */
  executionMode: StageExecutionMode;
  /** Parallel group ID -- stages in the same group run concurrently */
  parallelGroupId?: string;
  /** Role assignments */
  roles: WorkflowStageRole;
  /** Context policy */
  contextPolicy: WorkflowStageContextPolicy;
  /** Timeout in seconds (0 = no timeout) */
  timeoutSeconds: number;
  /** Number of retries on failure */
  retryCount: number;
  /** What to do when stage fails */
  failureAction: StageFailureAction;
  /** Display order within the workflow */
  order: number;
}

export interface Workflow {
  /** Unique workflow ID */
  id: string;
  /** Human-readable name */
  name: string;
  /** Optional description */
  description?: string;
  /** Tags for categorization */
  tags?: string[];
  /** Semantic version */
  version: string;
  /** Workflow status */
  status: WorkflowStatus;
  /** Ordered list of stages */
  stages: WorkflowStage[];
  /** Global context module IDs applied to all stages by default */
  globalContextModuleIds: string[];
  /** Whether to stop execution on first stage failure */
  stopOnFailure: boolean;
  /** Whether runtime overrides are allowed */
  allowRuntimeOverrides: boolean;
  /** Creator identifier */
  createdBy?: string;
  /** ISO 8601 timestamps */
  createdAt: string;
  updatedAt: string;
  /** Last execution info */
  lastExecution?: {
    runId: string;
    status: ExecutionStatus;
    startedAt: string;
    completedAt?: string;
  };
}

export interface WorkflowExecution {
  /** Unique run ID */
  runId: string;
  /** Workflow ID */
  workflowId: string;
  /** Workflow name (denormalized for display) */
  workflowName: string;
  /** Overall execution status */
  status: ExecutionStatus;
  /** Per-stage execution state */
  stages: WorkflowStageExecution[];
  /** Runtime overrides applied */
  overrides?: {
    contextModuleIds?: string[];
    agentOverrides?: Record<string, string>; // stageId -> agentId
  };
  /** Timestamps */
  startedAt: string;
  completedAt?: string;
  /** Who/what triggered this execution */
  trigger: 'manual' | 'scheduled' | 'api';
}

export interface WorkflowStageExecution {
  /** Stage definition ID */
  stageId: string;
  /** Stage name (denormalized) */
  stageName: string;
  /** Stage execution status */
  status: ExecutionStatus;
  /** Assigned agent artifact ID */
  agentId?: string;
  /** Context modules consumed */
  contextConsumed?: Array<{ moduleId: string; moduleName: string; sizeBytes: number }>;
  /** Timestamps */
  startedAt?: string;
  completedAt?: string;
  /** Duration in seconds */
  durationSeconds?: number;
  /** Log output lines */
  logs?: string[];
  /** Error message if failed */
  error?: string;
}
```

### 6.2 TanStack Query Hooks

New hooks to create in `hooks/use-workflows.ts`:

```typescript
// hooks/use-workflows.ts

export const workflowKeys = {
  all: ['workflows'] as const,
  lists: () => [...workflowKeys.all, 'list'] as const,
  list: (filters: WorkflowFilters) => [...workflowKeys.lists(), filters] as const,
  details: () => [...workflowKeys.all, 'detail'] as const,
  detail: (id: string) => [...workflowKeys.details(), id] as const,
};

// List workflows (stale time: 5min -- standard browsing)
export function useWorkflows(filters?: WorkflowFilters);

// Get single workflow (stale time: 5min)
export function useWorkflow(id: string);

// CRUD mutations
export function useCreateWorkflow();   // POST /api/v1/workflows
export function useUpdateWorkflow();   // PUT /api/v1/workflows/{id}
export function useDeleteWorkflow();   // DELETE /api/v1/workflows/{id}
export function useDuplicateWorkflow(); // POST /api/v1/workflows/{id}/duplicate
```

New hooks in `hooks/use-workflow-executions.ts`:

```typescript
export const executionKeys = {
  all: ['workflow-executions'] as const,
  lists: () => [...executionKeys.all, 'list'] as const,
  list: (workflowId?: string, filters?: ExecutionFilters) =>
    [...executionKeys.lists(), workflowId, filters] as const,
  details: () => [...executionKeys.all, 'detail'] as const,
  detail: (runId: string) => [...executionKeys.details(), runId] as const,
};

// List executions (stale time: 30sec -- monitoring)
export function useWorkflowExecutions(workflowId?: string, filters?: ExecutionFilters);

// Get single execution (stale time: 30sec -- monitoring)
export function useWorkflowExecution(runId: string);

// Run workflow
export function useRunWorkflow();       // POST /api/v1/workflows/{id}/run

// Execution control
export function usePauseExecution();    // POST /api/v1/workflows/{id}/executions/{runId}/pause
export function useResumeExecution();   // POST /api/v1/workflows/{id}/executions/{runId}/resume
export function useCancelExecution();   // POST /api/v1/workflows/{id}/executions/{runId}/cancel

// SSE stream for real-time updates
export function useExecutionStream(workflowId: string, runId: string);
```

### 6.3 Query Invalidation Graph

```
useCreateWorkflow    -> invalidate: workflowKeys.lists()
useUpdateWorkflow    -> invalidate: workflowKeys.lists(), workflowKeys.detail(id)
useDeleteWorkflow    -> invalidate: workflowKeys.lists()
useDuplicateWorkflow -> invalidate: workflowKeys.lists()
useRunWorkflow       -> invalidate: executionKeys.lists(), workflowKeys.detail(id)
usePauseExecution    -> invalidate: executionKeys.detail(runId)
useResumeExecution   -> invalidate: executionKeys.detail(runId)
useCancelExecution   -> invalidate: executionKeys.detail(runId), executionKeys.lists()
```

### 6.4 Builder Local State

The Workflow Builder maintains **local state** (not server state) until explicitly saved:

```typescript
// Builder state managed with useReducer for complex state transitions
interface BuilderState {
  workflow: Workflow;          // Working copy
  isDirty: boolean;           // Unsaved changes flag
  selectedStageId: string | null;
  editorOpen: boolean;
  dragState: DragState | null;
}

type BuilderAction =
  | { type: 'SET_NAME'; name: string }
  | { type: 'SET_DESCRIPTION'; description: string }
  | { type: 'ADD_STAGE'; stage: WorkflowStage; afterIndex?: number }
  | { type: 'UPDATE_STAGE'; stageId: string; updates: Partial<WorkflowStage> }
  | { type: 'REMOVE_STAGE'; stageId: string }
  | { type: 'REORDER_STAGES'; fromIndex: number; toIndex: number }
  | { type: 'SELECT_STAGE'; stageId: string | null }
  | { type: 'TOGGLE_EDITOR'; open: boolean }
  | { type: 'MARK_SAVED' }
  | { type: 'LOAD_WORKFLOW'; workflow: Workflow };
```

**Unsaved changes guard:** A `beforeunload` event listener warns before navigating away with unsaved changes. Additionally, the `useRouter` navigation is intercepted to show a confirmation dialog.

### 6.5 Optimistic Updates

| Mutation | Optimistic Behavior |
|----------|---------------------|
| Delete workflow | Remove from list immediately, roll back on error |
| Duplicate workflow | Add optimistic copy to list with "Copying..." indicator |
| Run workflow | Navigate to execution dashboard immediately, show "Initializing..." status |
| Pause/Resume | Update status badge immediately |
| Cancel execution | Update status badge immediately |

### 6.6 URL State Mapping

Following existing SkillMeat patterns, filter state lives in URL search params:

```typescript
// Library page URL state
const urlSearch = searchParams.get('search') || '';
const urlTags = searchParams.get('tags')?.split(',').filter(Boolean) || [];
const urlSort = searchParams.get('sort') || 'updatedAt';
const urlOrder = (searchParams.get('order') as 'asc' | 'desc') || 'desc';
const urlView = (searchParams.get('view') as 'grid' | 'list') || 'grid';

// Execution list URL state
const urlStatus = searchParams.get('status') as ExecutionStatus | null;
```

---

## 7. Accessibility

### 7.1 ARIA Roles and Labels

| Element | Role/Attribute | Value |
|---------|---------------|-------|
| Stage list (builder) | `role="list"` | -- |
| Stage card (builder) | `role="listitem"` | -- |
| Drag handle | `aria-label` | `"Reorder stage: {name}"` |
| Drag handle | `aria-roledescription` | `"sortable"` |
| Stage editor panel | `role="dialog"` | `aria-label="Edit stage: {name}"` |
| Timeline (execution) | `role="list"` | `aria-label="Execution timeline"` |
| Timeline node | `role="listitem"` + `role="button"` | `aria-label="{name} - {status}"` |
| Timeline node | `aria-current="step"` | On the currently running stage |
| Log viewer | `role="log"` | `aria-label="Stage execution logs"` |
| Log viewer | `aria-live="polite"` | For real-time log updates |
| Progress bar | `role="progressbar"` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| Run button | `aria-label` | `"Run workflow: {name}"` |
| Status badges | `aria-label` | `"Status: {status}"` |
| Workflow card | `role="article"` | `aria-label="{workflow name}"` |

### 7.2 Focus Management

- **Builder:** When adding a new stage, focus moves to the new stage's name field in the editor
- **Builder:** When deleting a stage, focus moves to the next stage (or previous if last)
- **Builder:** When opening/closing the stage editor panel, focus is trapped within the panel and returns to the edit button on close
- **Execution:** When selecting a timeline node, focus moves to the detail panel header
- **Dialogs:** All dialogs use Radix Dialog which provides built-in focus trapping and return
- **Tab navigation:** All tab bars support arrow key navigation per Radix Tabs

### 7.3 Screen Reader Announcements

Use `aria-live` regions for dynamic content:

```typescript
// Announce stage reorder
<div role="status" aria-live="polite" className="sr-only">
  {announceMessage} {/* e.g., "Stage 'Build & Test' moved to position 2" */}
</div>

// Announce execution status changes
<div role="status" aria-live="polite" className="sr-only">
  {`Stage ${stageName} ${status}`} {/* e.g., "Stage 'Deploy' completed" */}
</div>
```

### 7.4 Color Independence

All status indicators use both color AND icon/shape:

- Completed: green + checkmark
- Running: blue + spinner
- Failed: red + X
- Pending: gray + clock
- Paused: yellow + pause bars

This ensures information is conveyed through multiple channels, not color alone.

---

## 8. Mobile / Responsive

### 8.1 Breakpoint Strategy

| Breakpoint | Layout Changes |
|------------|---------------|
| `< 640px` (mobile) | Single column, stacked cards, no sidebar in builder |
| `640-1024px` (tablet) | 2-column grid, collapsible sidebar in builder |
| `> 1024px` (desktop) | 3-column grid, full sidebar in builder, split view in execution |

### 8.2 Workflow Library (Mobile)

- Cards stack in single column: `grid-cols-1`
- Toolbar collapses: search input full-width, filters behind a "Filter" button that opens a sheet
- Card actions moved to swipe gesture or long-press context menu

### 8.3 Workflow Builder (Mobile)

- Sidebar metadata panel collapses into a top sheet (accessible via a "Settings" button in the builder top bar)
- Stage cards are full-width
- Drag-and-drop still functional (touch events supported by @dnd-kit)
- Stage editor opens as a full-screen sheet instead of a slide-over
- "Add Stage" button is always visible (no hover-reveal on connectors)

### 8.4 Execution Dashboard (Mobile)

- Split layout becomes stacked: timeline on top, detail below
- Timeline is horizontal scrollable (or condensed to current + adjacent stages)
- Detail panel is full-width below the timeline
- Log viewer has a "View Full Logs" button that opens in a full-screen sheet

### 8.5 Touch Considerations

- All touch targets minimum 44x44px
- Drag handles have generous touch targets (48px)
- Swipe gestures for card actions on mobile
- Pull-to-refresh on library and execution list pages

---

## 9. Design System Integration

### 9.1 Artifact Type Extension

Add `workflow` to the artifact type system:

```typescript
// Addition to types/artifact.ts (or types/workflow.ts)
// Note: Workflows are a separate entity type, not a standard artifact.
// However, they participate in the same visual system.

export const WORKFLOW_TYPE_CONFIG = {
  type: 'workflow' as const,
  label: 'Workflow',
  pluralLabel: 'Workflows',
  icon: 'Workflow',     // lucide-react Workflow icon (or GitBranch)
  color: 'text-indigo-500',
};
```

### 9.2 Color Tokens

New semantic colors for workflow states:

| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--workflow-accent` | `indigo-500` | `indigo-400` | Workflow badges, stage numbers |
| `--stage-completed` | `green-500` | `green-400` | Completed stage indicator |
| `--stage-running` | `blue-500` | `blue-400` | Running stage indicator |
| `--stage-failed` | `red-500` | `red-400` | Failed stage indicator |
| `--stage-pending` | `muted` | `muted` | Pending stage indicator |
| `--stage-paused` | `yellow-500` | `yellow-400` | Paused stage indicator |

These map to existing Tailwind color utilities -- no custom CSS variables needed. The table is for reference.

### 9.3 Navigation Config Update

```typescript
// Addition to navigationConfig.sections in components/navigation.tsx
{
  title: 'Workflows',
  icon: Workflow,           // from lucide-react (or GitBranch)
  storageKey: 'workflows',
  items: [
    { name: 'Library', href: '/workflows', icon: Library },
    { name: 'Executions', href: '/workflows/executions', icon: Play },
  ],
},
```

### 9.4 Shared Pattern Reuse

| Pattern | Existing Implementation | Reuse In |
|---------|------------------------|----------|
| URL-driven filters | `collection/page.tsx` `updateUrlParams` | Library page, Execution list |
| Infinite scroll | `useIntersectionObserver` + `useInfiniteArtifacts` | Library page (if large collection) |
| Card grid/list toggle | `collection/page.tsx` viewMode | Library page |
| PageHeader + toolbar layout | `collection/page.tsx`, `manage/page.tsx` | All workflow pages |
| Tab navigation | `TabNavigation` component | Detail page |
| Modal detail view | `BaseArtifactModal` | (Not reused -- workflows have their own detail page) |
| Empty state pattern | `collection/page.tsx` EmptyState | Library page |
| Deletion confirmation | `ArtifactDeletionDialog` | Workflow/stage deletion |
| SSE streaming | `useSSE` hook | Execution dashboard |
| Keyboard shortcuts | `useKeyboardShortcuts` hook | Builder, Execution dashboard |
| Toast notifications | `useToast` hook | All mutation feedback |
| Debounced search | `useDebounce` hook | Library search, artifact picker |

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Estimated: 3-4 days)

**Goal:** Core data types, API hooks, navigation, and empty pages.

| Task | Component/File | Complexity |
|------|---------------|------------|
| Define TypeScript types | `types/workflow.ts` | Low |
| Create workflow hooks | `hooks/use-workflows.ts`, `hooks/use-workflow-executions.ts` | Medium |
| Register hooks in barrel | `hooks/index.ts` | Low |
| Add navigation section | `components/navigation.tsx` | Low |
| Create route structure | `app/workflows/**` (empty pages) | Low |
| Build WorkflowCard | `components/workflow/workflow-card.tsx` | Low |
| Build WorkflowListItem | `components/workflow/workflow-list-item.tsx` | Low |
| Build Library page | `app/workflows/page.tsx` | Medium |

### Phase 2: Builder Core (Estimated: 4-5 days)

**Goal:** Functional workflow builder with stage management.

| Task | Component/File | Complexity |
|------|---------------|------------|
| Build StageCard | `components/workflow/stage-card.tsx` | Medium |
| Build StageConnector | `components/workflow/stage-connector.tsx` | Low |
| Build SlideOverPanel (shared) | `components/shared/slide-over-panel.tsx` | Medium |
| Build StageEditor | `components/workflow/stage-editor.tsx` | High |
| Build ArtifactPicker (shared) | `components/shared/artifact-picker.tsx` | Medium |
| Build ContextModulePicker (shared) | `components/shared/context-module-picker.tsx` | Medium |
| Build InlineEdit (shared) | `components/shared/inline-edit.tsx` | Low |
| Build Builder page with useReducer | `app/workflows/new/page.tsx`, `app/workflows/[id]/edit/page.tsx` | High |
| Implement drag-and-drop | Integration with @dnd-kit | Medium |
| Implement save/load | Mutations + local state management | Medium |

### Phase 3: Detail and Execution (Estimated: 3-4 days)

**Goal:** Workflow detail view and execution dashboard.

| Task | Component/File | Complexity |
|------|---------------|------------|
| Build Detail page | `app/workflows/[id]/page.tsx` | Medium |
| Build RunWorkflowDialog | `components/workflow/run-workflow-dialog.tsx` | Medium |
| Build StageTimeline | `components/workflow/stage-timeline.tsx` | Medium |
| Build ExecutionHeader | `components/workflow/execution-header.tsx` | Low |
| Build ExecutionProgress | `components/workflow/execution-progress.tsx` | Low |
| Build ExecutionDetail | `components/workflow/execution-detail.tsx` | Medium |
| Build LogViewer | `components/workflow/log-viewer.tsx` | Medium |
| Build Execution Dashboard page | `app/workflows/[id]/executions/[runId]/page.tsx` | High |
| Integrate SSE streaming | `useExecutionStream` hook | Medium |

### Phase 4: Polish and Responsive (Estimated: 2-3 days)

**Goal:** Mobile responsiveness, animations, keyboard shortcuts, and edge cases.

| Task | Component/File | Complexity |
|------|---------------|------------|
| Responsive builder layout | Mobile sheet patterns | Medium |
| Responsive execution layout | Stacked mobile layout | Medium |
| Keyboard shortcuts | Integration with `useKeyboardShortcuts` | Medium |
| Animations (stage add/remove, panel slide) | CSS transitions + Tailwind | Low |
| Unsaved changes guard | `beforeunload` + router intercept | Medium |
| Loading skeletons for all pages | Skeleton components | Low |
| Error states and empty states | All pages | Low |
| Parallel branch UI | Builder parallel stage support | High |

### Dependency Install

```bash
# Required new dependency for drag-and-drop
pnpm add @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

### Backend API Requirements (Not in Scope for This Spec)

This UI spec assumes the following API endpoints will be available:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/v1/workflows` | List workflows |
| `POST` | `/api/v1/workflows` | Create workflow |
| `GET` | `/api/v1/workflows/{id}` | Get workflow |
| `PUT` | `/api/v1/workflows/{id}` | Update workflow |
| `DELETE` | `/api/v1/workflows/{id}` | Delete workflow |
| `POST` | `/api/v1/workflows/{id}/duplicate` | Duplicate workflow |
| `POST` | `/api/v1/workflows/{id}/run` | Start execution |
| `GET` | `/api/v1/workflows/{id}/executions` | List executions for workflow |
| `GET` | `/api/v1/workflows/executions` | List all executions |
| `GET` | `/api/v1/workflows/{id}/executions/{runId}` | Get execution detail |
| `POST` | `/api/v1/workflows/{id}/executions/{runId}/pause` | Pause execution |
| `POST` | `/api/v1/workflows/{id}/executions/{runId}/resume` | Resume execution |
| `POST` | `/api/v1/workflows/{id}/executions/{runId}/cancel` | Cancel execution |
| `GET` | `/api/v1/workflows/{id}/executions/{runId}/stream` | SSE stream for execution |

---

## Appendix A: Component State Checklist

Every component should handle these states:

| Component | Default | Hover/Focus | Active | Disabled | Loading | Error | Empty | Dark Mode |
|-----------|---------|-------------|--------|----------|---------|-------|-------|-----------|
| WorkflowCard | Y | Y (shadow lift) | Y (ring) | N/A | N/A | N/A | N/A | Y |
| StageCard (edit) | Y | Y (border highlight) | Y (drag lift) | N/A | N/A | N/A | N/A | Y |
| StageCard (readonly) | Y | N/A | N/A | N/A | N/A | N/A | N/A | Y |
| ArtifactPicker | Y | Y | Y (popover) | Y (grayed) | Y (spinner) | Y (red border) | Y (no results) | Y |
| LogViewer | Y | N/A | N/A | N/A | Y (waiting) | Y (error highlight) | Y (no logs) | Y |
| Timeline Node | Y | Y (bg highlight) | Y (selected bg) | N/A | N/A | Y (red) | N/A | Y |
| ExecutionProgress | Y | N/A | N/A | N/A | Y (indeterminate) | Y (red fill) | N/A | Y |
| RunWorkflowDialog | Y | N/A | N/A | Y (form invalid) | Y (submitting) | Y (error msg) | N/A | Y |

## Appendix B: File Structure Summary

```
skillmeat/web/
  app/
    workflows/
      page.tsx                           # Library page
      new/
        page.tsx                         # Builder (create)
      [id]/
        page.tsx                         # Detail page
        edit/
          page.tsx                       # Builder (edit)
        executions/
          page.tsx                       # Execution list for this workflow
          [runId]/
            page.tsx                     # Execution dashboard
      executions/
        page.tsx                         # All executions list
  components/
    workflow/
      workflow-card.tsx                  # Grid card
      workflow-list-item.tsx             # List row
      workflow-toolbar.tsx               # Filter/sort bar
      stage-card.tsx                     # Stage card (edit + readonly modes)
      stage-connector.tsx                # Connector line between stages
      stage-editor.tsx                   # Slide-over editor panel
      stage-timeline.tsx                 # Execution timeline
      execution-header.tsx               # Execution page header
      execution-progress.tsx             # Progress bar
      execution-detail.tsx               # Stage detail panel
      log-viewer.tsx                     # Log output viewer
      run-workflow-dialog.tsx            # Run configuration dialog
    shared/
      artifact-picker.tsx                # Searchable artifact selector
      context-module-picker.tsx          # Searchable context module selector
      slide-over-panel.tsx               # Reusable slide-over
      inline-edit.tsx                    # Click-to-edit text
      status-dot.tsx                     # Status indicator dot
      vertical-timeline.tsx              # Timeline layout wrapper
      timeline-node.tsx                  # Timeline node
      drag-handle.tsx                    # Drag handle icon
  hooks/
    use-workflows.ts                     # Workflow CRUD hooks
    use-workflow-executions.ts           # Execution hooks
  types/
    workflow.ts                          # Workflow type definitions
```
