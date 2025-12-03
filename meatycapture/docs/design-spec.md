---
title: "Design Spec: MeatyCapture"
description: "Architecture, data model, UX flow, and component design for the MeatyCapture request-log app"
status: "draft"
created: 2025-12-03
updated: 2025-12-03
owners: ["engineering-lead", "design-lead"]
audience: [engineering, design, ai-agents]
category: "design-spec"
---

# Design Spec: MeatyCapture

## Architecture Overview
- **Layers**
  - **Core (headless)**: domain models, validation, ID generation, request-log serializer/merger, catalog resolution, backup handling.
  - **Ports/Adapters**:
    - `DocStore` (list/read/write/append) → `fs-local`.
    - `ProjectStore` → `config-local`.
    - `FieldCatalogStore` → `config-local`.
    - `Clock` → system clock.
  - **UI**:
    - Wizard (multi-step).
    - Admin (field manager).
    - Shared components (dropdown with Add+, multi-select tags, path picker, tables, modals, toasts).
  - **Platform**:
    - Web/desktop shell now (Vite + React + CSS).
    - Optional Tauri/Electron wrapper.
    - Future: expose Core via lightweight bridge for Swift/iOS or React Native reuse.

## Data Model
- `Project`: { id, name, default_path, repo_url?, enabled }
- `FieldOption`: { id, field: "type"|"domain"|"context"|"priority"|"status"|"tag", value, label, scope: "global"|"project", project_id?, enabled }
- `FieldCatalog`: { global: FieldOption[], project: Record<project_id, FieldOption[]> }
- `ItemDraft`: { title, type, domain, context, priority, status, tags[], notes }
- `RequestLogDoc`: {
    doc_id,
    title,
    created,
    updated,
    status,
    owners,
    domains,
    item_count,
    tags: string[],
    items_index: Array<{id,type,domain,context,priority,status,title,tags}>,
    body_items: Array<{id, metadata_line, notes[]}>
  }

## File Format (request-log)
- YAML front matter fields (aligned with template):
  - `type: request-log`
  - `doc_id`, `title`, `created`, `updated`, `status`, `owners`, `domains`, `item_count`
  - `items_index`: list of per-item summary objects
  - `tags`: deduped list of all tags present in items (auto-updated on append)
- Markdown body:
  - Quick index table (ID, Type, Domain, Context, Priority, Status, Title).
  - Item sections:
    ```
    ### REQ-20251203-web-01 — Title
    **Type:** enhancement | **Domain:** web | **Context:** /collection | **Priority:** medium | **Status:** triage  
    **Tags:** ux, grouping

    - Problem/goal: ...
    - Key behaviors/acceptance: ...
    - Notes: ...
    ```

## ID and Slug Rules
- `doc_id`: `REQ-YYYYMMDD-<project-slug>`
- `item_id`: `REQ-YYYYMMDD-<project-slug>-XX` (XX zero-padded counter per doc, starting 01)
- `project-slug`: kebab-case of project name.

## Core Behaviors
- **Doc creation**: generate doc_id/title, build front matter, add first item, set item_count=1, tags from item tags.
- **Doc append**: read existing doc, parse front matter/items_index, compute next item_id, merge tags (union), update item_count/updated date, append new items to body and index/table.
- **Tag aggregation**: maintain `tags` as unique sorted list; update on every write.
- **Catalog resolution**: effective options = global + project-level additions; global shown as disabled in project admin unless explicitly enabled copy is created.
- **Backups**: before write/append, write `filename.bak` (single-version) for recovery.

## UX Flows (Wizard)
1) **Project Step**
   - Dropdown listing Projects (name + path); last option “Add New Project…”.
   - If Add New: modal with name, default_path (required), repo_url (optional). Save to ProjectStore.
   - On select, default path field populated (editable).
2) **Doc Step**
   - Radio: Create new doc (default) vs Select existing.
   - If create: show generated doc_id/title preview; allow edit of doc title.
   - If select existing: list request-log files under chosen path (lazy loaded); text box for direct path override.
3) **Item Details Step**
   - Dropdowns for type, domain, context (with Add+ inline), priority, status.
   - Tag multi-select with Add+; shows suggestions as user types.
   - Title (text), Notes (multiline markdown-friendly).
4) **Review/Confirm**
   - Summary card with target filepath, doc mode (new/append), item preview.
   - On submit, write/append doc via DocStore.
   - Post-submit prompt: “Add another to this doc?” → returns to Item Details with Project/Doc fixed.
5) **Completion**
   - Show file path, item IDs written, copy-to-clipboard for IDs.

## Admin Flow
- Page selector: Global vs Project <dropdown>.
- For each field group, list options with edit/delete (delete disabled for global when viewed under project scope).
- Button “Enable global option for this project” clones into project scope.
- Add+ opens inline form row.
- Save writes catalogs via FieldCatalogStore.

## Components (UI)
- `ProjectSelect` (with Add New modal)
- `PathField` (text with browse button, validates exist/write)
- `DocSelector` (new vs existing list)
- `DropdownWithAdd` (single select)
- `MultiSelectWithAdd` (tags)
- `StepShell` (wizard container, progress indicator, animated transitions)
- `ReviewCard`
- `AdminFieldTable`
- `Toast/InlineAlert` for errors/success

## Styling & Motion
- Glass/x-morphism-inspired surfaces, soft shadows, blur backgrounds, rounded corners.
- Color system: neutral base with accent primary; avoid purple bias; accessible contrast.
- Motion: slide/fade transitions between steps; micro-interaction on Add+ confirmations.
- Responsive: mobile-friendly layout; stepper collapses to top progress bar on small screens.

## Accessibility
- Labels/aria on inputs, buttons.
- Keyboard: Tab/Shift+Tab, Enter to advance, Escape to close modals.
- Focus ring visible; dropdowns navigable via arrows.

## Persistence & Config
- Default config path: `~/.meatycapture/`.
- `projects.json`: array of projects.
- `fields.json`: global + project maps.
- Optional env overrides: `MEATYCAPTURE_CONFIG_DIR`, `MEATYCAPTURE_DEFAULT_PROJECT_PATH`.

## Error Handling
- Path not writable: block submission, show inline error.
- Existing doc parse failure: show warning with option to back up and overwrite; default is cancel.
- Backup failure: warn but allow user to proceed explicitly.

## Future Extensions
- GitHub repo sync (read/write via API).
- Search across request-log docs by tag/type.
- Mobile app consuming Core via lightweight API or shared schema.
- Collaboration: file locks or merge helpers.

## Open Questions
- Should we support YAML vs TOML for catalogs? (default JSON now).
- Do we need per-field default values per project? (not in MVP).
- Should we auto-open created file in editor? (optional command/setting).
