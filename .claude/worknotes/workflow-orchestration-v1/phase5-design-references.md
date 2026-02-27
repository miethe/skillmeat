# Phase 5 & 6 Design References

Pre-work artefacts for Phases 5 and 6 of the Workflow Orchestration Engine.
Generated: 2026-02-27 | Status: P0 approved, P1 generated (pending human review)

---

## How to Use This File

When delegating to `ui-engineer-enhanced` or `frontend-developer`, include the relevant
`Reference image` and `Scaffold` paths in the task prompt. The scaffold is a STARTING POINT
(Gemini-generated, un-reviewed), not a finished implementation. The image is the approved
visual target.

Pattern:
```
Reference image: assets/ai-gen/2026-02-27/nano-banana-2/<file>.png
Scaffold (starting point): assets/ai-gen/2026-02-27/gemini-3.1-pro/<file>.tsx
Follow project conventions in skillmeat/web/CLAUDE.md and .claude/context/key-context/component-patterns.md
```

---

## P0 Components — Approved

### FE-6.1 StageTimeline

| Asset | Path |
|-------|------|
| Reference image | `assets/ai-gen/2026-02-27/nano-banana-2/stage-timeline-all-statuses.png` |
| Scaffold | `assets/ai-gen/2026-02-27/gemini-3.1-pro/stage-timeline-scaffold.tsx` |
| Target file | `skillmeat/web/components/workflow/stage-timeline.tsx` |

Key spec: Section 3.4 of `docs/project_plans/design/workflow-orchestration-ui-spec.md`.
All 7 ExecutionStatus states shown in image (pending/running/completed/failed/cancelled/paused/waiting).
J/K keyboard nav, aria-current='step' on running, aria-selected on selected.

---

### FE-5.16 StageCard

| Asset | Path |
|-------|------|
| Reference image | `assets/ai-gen/2026-02-27/nano-banana-2/stage-card-both-modes.png` |
| Scaffold | `assets/ai-gen/2026-02-27/gemini-3.1-pro/stage-card-scaffold.tsx` |
| Target file | `skillmeat/web/components/workflow/stage-card.tsx` |

Key spec: Section 3.2 — Builder canvas StageCard specifications.
Image shows both modes side-by-side. Edit mode: drag handle (opacity-0 group-hover:opacity-100), indigo badge, pencil+X actions. Readonly: bg-muted/30, no controls, Timeout/Retries footer.
Uses @dnd-kit/sortable useSortable in edit mode.

---

### FE-6.6 Execution Dashboard Page

| Asset | Path |
|-------|------|
| Reference image | `assets/ai-gen/2026-02-27/nano-banana-2/execution-dashboard-layout.png` |
| Scaffold | `assets/ai-gen/2026-02-27/gemini-3.1-pro/execution-dashboard-scaffold.tsx` |
| Target file | `skillmeat/web/app/workflows/[id]/executions/[runId]/page.tsx` |

Key spec: Section 3.4 — Execution Dashboard full layout.
Image is LIGHT MODE. Layout: ExecutionHeader + ExecutionProgress + split(StageTimeline w-72 | ExecutionDetail flex-1).
Scaffold includes inline stubs for ExecutionHeader, ExecutionProgress, ExecutionDetail — split these into
separate files per task assignments (FE-6.2, FE-6.3, FE-6.4).

---

## P1 Components — Generated (Pending Human Review)

Review images before Phase 5 Batch 2 begins. Scaffolds are ready regardless.

### FE-5.12 WorkflowCard

| Asset | Path |
|-------|------|
| Reference image | `assets/ai-gen/2026-02-27/nano-banana-2/workflow-card-grid.png` |
| Scaffold | `assets/ai-gen/2026-02-27/gemini-3.1-pro/workflow-card-scaffold.tsx` |
| Target file | `skillmeat/web/components/workflow/workflow-card.tsx` |

Key spec: Section 3.1 — grid card with title, stage count, last-run, tags (max 3 + overflow), footer actions (Run/Edit/DropdownMenu).

---

### FE-5.18 StageEditor

| Asset | Path |
|-------|------|
| Reference image | `assets/ai-gen/2026-02-27/nano-banana-2/stage-editor-slide-over.png` |
| Scaffold | `assets/ai-gen/2026-02-27/gemini-3.1-pro/stage-editor-scaffold.tsx` |
| Target file | `skillmeat/web/components/workflow/stage-editor.tsx` |

Key spec: Section 3.2 — fixed right slide-over w-[480px], 4 sections (Basic Info / Roles / Context Policy / Advanced), local useState form state, Cancel + Save footer.

---

### FE-6.5 LogViewer

| Asset | Path |
|-------|------|
| Reference image | `assets/ai-gen/2026-02-27/nano-banana-2/log-viewer-panel.png` |
| Scaffold | `assets/ai-gen/2026-02-27/gemini-3.1-pro/log-viewer-scaffold.tsx` |
| Target file | `skillmeat/web/components/workflow/log-viewer.tsx` |

Key spec: Section 3.4 — font-mono text-xs log lines, error=bg-destructive/10, warn=text-yellow-600, auto-scroll when isLive + near bottom, scroll-to-bottom ChevronDown button, empty state "Waiting for logs..."

---

## Step 5 Assets — Generated (Pending Human Review)

Supplementary visual references for empty states and status legend.

| Asset | Path | Use |
|-------|------|-----|
| Empty state — Library | `assets/ai-gen/2026-02-27/nano-banana-2/empty-state-library.png` | FE-5.3 EmptyState for Workflow Library |
| Status icon reference | `assets/ai-gen/2026-02-27/nano-banana-2/status-icon-reference.png` | Reference for all 7 ExecutionStatus states |

---

## Tool Notes

- **Image generation**: `nano-banana -m nb2 -s 2K` (Gemini 3.1 Flash Image)
- **TSX scaffold**: `gemini "..." --yolo -o text > file.tsx 2>/dev/null` (text positional arg, no image @ref)
- **Gemini @file image refs**: Do NOT work in non-interactive/piped mode — images are human review only
- **Output cleanup**: Always run `sed -i '' '/^```/d' file.tsx` after Gemini scaffold capture
- **Asset pipeline**: `assets/ai-gen/{date}/{model}/{filename}`

---

## multi-model.toml Note

`nano-banana-pro` config entry still references old model. Add nb2 entry when ready:
```toml
[models.nano_banana_2]
model = "gemini-flash-3.1-image"   # verify exact model ID
default_size = "1K"
```
