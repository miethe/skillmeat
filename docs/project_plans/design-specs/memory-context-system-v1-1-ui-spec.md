---
title: "Design Spec: Memory & Context v1.1 UI (Global Memories + Projects IA)"
description: "UI/UX specification for global memory visibility, project-centric navigation restructuring, and memory workflow discoverability improvements."
audience: [developers, designers, ai-agents]
tags: [design-spec, memory, context, navigation, sidebar, projects, search]
created: 2026-02-06
updated: 2026-02-06
category: design
status: draft
references:
  - /docs/project_plans/PRDs/features/memory-context-system-v1-1.md
  - /docs/project_plans/design-specs/memory-context-system-ui-spec.md
  - /skillmeat/web/components/navigation.tsx
  - /skillmeat/web/app/projects/[id]/memory/page.tsx
---

# Design Spec: Memory & Context v1.1 UI

**PRD Reference:** `memory-context-system-v1-1`  
**Version:** 1.0  
**Date:** 2026-02-06

---

## 1. Objectives

1. Make memory capabilities obvious and accessible from primary navigation.
2. Preserve existing project URLs while introducing a global memories entry point.
3. Support cross-project workflows (future) without forcing immediate backend coupling.
4. Keep keyboard-first triage model from v1 intact.

---

## 2. Information Architecture

## 2.1 Sidebar Structure (Target)

Current sidebar mixes projects under Collections section. v1.1 introduces a dedicated top-level **Projects** section.

### Proposed Navigation Groups

- `Dashboard`
- `Collections`
  - `Collections` (`/collection`)
  - `Groups` (`/groups`)
  - `Health & Sync` (`/manage`)
- `Projects` (new dedicated group)
  - `Projects` (`/projects`) [existing route]
  - `Memories` (`/memories`) [new route]
  - `MCP Servers` (`/mcp`) (optional placement decision; see Open Questions)
- `Marketplace`
- `Agent Context`
- `Resources`
- `Settings`

### URL Preservation

- No route changes for existing project pages:
  - `/projects`
  - `/projects/[id]`
  - `/projects/[id]/manage`
  - `/projects/[id]/memory`

---

## 3. New View: Global Memories (`/memories`)

## 3.1 Purpose

Provide a global memory inbox entry point that makes memory features discoverable without requiring users to first navigate through a project detail page.

## 3.2 Core UX

- Project selector (required context) at top of page
- Optional "All Projects" mode for future cross-project queries
- Reuse existing Memory Inbox components where possible
- Fast deep-link to project-scoped memory route

## 3.3 Layout

```
+-------------------------------------------------------------------+
| Memories                                                           |
| [Project: v dropdown] [Open Project Page] [Open Project Memory]   |
+-------------------------------------------------------------------+
| [Type Tabs] [Status] [Sort] [Search]                              |
+-------------------------------------------------------------------+
| Memory list + detail panel (same triage model as project memory)  |
+-------------------------------------------------------------------+
```

## 3.4 States

- `No project selected`: empty state with selector prompt
- `Project selected`: full memory inbox content for selected project
- `No memories`: onboarding callout with "Create Memory" and "Run Extraction" CTAs

---

## 4. Project Detail Enhancements

Add explicit path from project detail to memory workspace:

- Primary/secondary CTA: **Open Memory**
- Contextual stats card: candidate count, active count, stable count
- Keep existing tab behavior unchanged

---

## 5. Reuse Strategy

- Reuse `MemoryPageContent` internals for `/memories` via container wrapper
- Abstract project-id dependency into a selector-aware controller
- Avoid duplicate list/detail/filter components

---

## 6. Keyboard & Accessibility

- Preserve all v1 shortcuts in global memories view.
- Project selector must be fully keyboard operable.
- Focus management:
  - Switching project returns focus to list container.
  - Shortcut `?` still opens keyboard help.

---

## 7. Future-Ready UX Hooks

## 7.1 Cross-Project Search Mode (future)

- Toggle in `/memories`: `Current Project | All Projects`
- Result cards include project pill
- "Promote to module" action should require project context

## 7.2 Memory Sharing (future)

- Filter chips for scope: `project`, `global_candidate`
- Warnings when importing external memories across projects

---

## 8. API/Data Requirements for UI

- Global memories route needs:
  - project list for selector
  - memory counts per project (optional for selector badges)
  - list/search endpoint supporting project scope parameter
- Extraction status badges (future): pending, completed, failed

---

## 9. Responsive Behavior

- Desktop: split list/detail layout as in v1
- Tablet/mobile:
  - project selector pinned at top
  - detail panel becomes full-screen sheet

---

## 10. Open Questions

1. Should `MCP Servers` live under `Projects` or remain under `Collections`?
2. Should `/memories` default to the last active project from local storage?
3. In all-project mode, should promote/deprecate actions be enabled directly or require project pinning first?

---

## 11. Implementation Notes

- Recommended files for UI changes:
  - `skillmeat/web/components/navigation.tsx`
  - `skillmeat/web/app/memories/page.tsx` (new)
  - `skillmeat/web/app/projects/[id]/page.tsx` (add memory CTA)
  - `skillmeat/web/components/memory/*` (selector/controller extraction)

- QA checklist:
  - URL stability for existing project pages
  - keyboard regressions
  - mobile selector usability
  - breadcrumb and deep-link correctness
