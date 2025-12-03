---
title: "Implementation Plan: MeatyCapture"
description: "Phased plan to build a portable capture app for request-log entries with project-aware defaults and admin field management"
status: "draft"
created: 2025-12-03
updated: 2025-12-03
owners: ["engineering-lead"]
audience: [engineering, product, ai-agents]
category: "implementation-plan"
---

# Implementation Plan: MeatyCapture

## Guiding Principles
- Headless core: separate domain logic (projects, fields, doc writer) from UI.
- File-first: local markdown output in request-log format; no server dependency.
- Extensible catalogs: global + project field options, inline Add+ in UI.
- Portability: architecture suitable for web/desktop now, mobile (iOS/Swift) later.

## Architecture Snapshot (target)
- `core/` (TS/JS or Rust/Swift-ready model): data models, validation, doc writer, storage provider interface.
- `adapters/`:
  - `fs-local`: read/write docs, list existing request-log files, backups.
  - `config-local`: projects + field catalogs (JSON/TOML).
- `ui/` (web/desktop): Wizard, Admin screens, shared components (dropdown with Add+, tag multi-select, table).
- `platform/`:
  - `electron-tauri` (optional) for desktop shell.
  - `api-bridge` (future) to expose core over a minimal API for mobile.

## Phase Plan

### Phase 0: Scaffolding (0.5d)
- Create project structure under `/meatycapture`.
- Choose stack: TypeScript + Vite/React for UI; headless core in TS (keeps mobile webport easy; later Swift port via thin bindings or shared schema).
- Add lint/format/test minimal configs.

### Phase 1: Core Models & Storage Ports (1-1.5d)
- Define domain models: Project, FieldOption (global/project), ItemDraft, RequestLogDoc.
- Define storage ports: `ProjectStore`, `FieldCatalogStore`, `DocStore` (list/read/write/append with merge), `Clock`.
- Implement local FS adapters:
  - Projects/config at `~/.meatycapture/projects.json` (override via env/CLI).
  - Field catalogs at `~/.meatycapture/fields.{json|toml}` with project overrides.
- Implement request-log serializer/deserializer:
  - Build front matter + items_index + tags merge.
  - Generate IDs `REQ-<doc-date>-<project-slug>-XX`.
  - Append flow preserves existing content and updates counts/tags/index.
- Unit tests for serialization/merge.

### Phase 2: Wizard UI (1.5-2d)
- Step 1: Project select with inline Add New modal (name, default_path, repo_url?).
- Step 2: Doc selection (default new doc; list existing request-log files found under default path; allow path override).
- Step 3: Item details form (typed dropdowns with Add+, tag multi-select with Add+, notes).
- Step 4: Review/confirm + “Add another to same doc?” flow.
- State machine to avoid re-entering Project/Doc when batching.
- Motion/animations between steps; keyboard shortcuts for Next/Back.
- Error surfaces for path/write issues.

### Phase 3: Admin UI (1-1.5d)
- Admin page toggle: Global vs Project <name>.
- CRUD for field options per field group (type, domain, context, priority, status, tags).
- In project view, show global options greyed; “Enable for this project” to add project-level copies (no deletion of global).
- Persist via FieldCatalogStore.

### Phase 4: Polish & UX (1d)
- iOS-friendly styling (glass/x-morphism), focus/hover states, micro-interactions on step change.
- Accessibility pass (labels, roles, keyboard nav).
- Empty/loading states for dropdowns and doc listing.

### Phase 5: Packaging & Ops (optional, 1d)
- Wrap in Tauri/Electron-lite for desktop.
- Add simple `meatycapture` CLI to launch UI and run headless doc creation (batch from JSON).
- Basic logging + backup copy before writes.

## Milestones & Acceptance
- M1 (end Phase 1): Core models + FS adapters + serializer with tests passing.
- M2 (end Phase 2): Wizard can create new doc and append to existing; batching works; tags merged.
- M3 (end Phase 3): Admin can manage global/project field options with enable toggle behavior.
- M4 (end Phase 4): UX polish, accessibility, animations.
- M5 (optional): Desktop packaging + CLI entry point.

## Testing Strategy
- Unit: models, serializer/merger, ID generation, tag aggregation, catalog merging.
- Integration: Wizard happy path (new doc, append doc), project add inline, Add+ option creation, batch add multiple items.
- File I/O tests in temp dirs to ensure no corruption and backups on append.
- Snapshot tests for generated markdown.
- Accessibility smoke (aria labels, keyboard navigation).

## Risks / Mitigations
- **Path issues/permissions:** surface friendly errors; create backup copy before overwrite.  
- **Concurrent edits:** note in UI; later add file lock/version check.  
- **Catalog drift:** source of truth in config; show effective set in UI.  
- **Portability:** keep core free of DOM; expose core functions via simple interface for future mobile.

## Deliverables
- Core library (TS) with FS adapters.
- Wizard UI + Admin UI.
- CLI launcher (optional).
- Docs: PRD, Implementation Plan (this file), Design Spec.
