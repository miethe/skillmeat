---
title: "PRD: MeatyCapture"
description: "Lightweight, portable capture app to log enhancements/issues/ideas to request-log docs with project-aware defaults and tag aggregation"
audience: [ai-agents, product, eng, design]
status: "draft"
created: 2025-12-03
updated: 2025-12-03
owners: ["product-owner"]
domains: ["web", "desktop", "mobile-future"]
category: "prd"
---

# PRD: MeatyCapture

## Overview
MeatyCapture is a small, standalone capture tool for logging enhancements, bugs, and ideas into request-log markdown files. It supports multiple Projects (each with a filepath and optional repo), project-level field catalogs, inline creation of new options, and batch capture within a session. The UX is a wizard with a modern iOS-friendly aesthetic (x-morphism inspired), smooth transitions, and enterprise-grade clarity.

## Goals
- Fast capture: add multiple typed items in a single session with minimal friction.
- Project-aware defaults: choose a Project (or add inline), auto-apply its default path, allow edits.
- File-first storage: create new request-log docs by default; optionally append to an existing doc.
- Structured data: enforce typed fields (type, domain, context, priority, status, tags) with inline Add+.
- Tag hygiene: keep a unique tag set in front matter; auto-update when appending items.
- Extensibility: modular core for reuse (desktop/web) and future iOS/Swift UI port.
- Admin UX: manage global and project-level field options; project view shows global options (greyed) with enable-as-project-level capability (no deletions of global).

## Non-Goals
- No server back end for MVP (local file storage only).
- No authentication/authorization for MVP.
- No GitHub write integration in MVP (only local path).
- No mobile client in MVP (design for future port).

## Users / Personas
- Product/Founder capturing ideas and specs.
- Engineers logging bugs/enhancements with consistent IDs.
- AI Agents needing structured, queryable entries across docs.

## User Stories (MVP)
1) As a user, I can pick a Project (or Add New inline), auto-setting default filepath, and still edit the path.  
2) As a user, I can select “new doc” (default) or choose an existing doc for the Project.  
3) As a user, I can enter an item with required typed fields (type, domain, context, priority, status, tags) and optional notes, then add another item to the same doc without re-selecting Project/doc.  
4) As a user, I can add new field options inline in any dropdown (Add +).  
5) As a user, I can multi-select tags (existing or newly added).  
6) As a user, I can see aggregated tags automatically maintained in front matter when items are added/appended.  
7) As an admin, I can manage field options globally or per Project; project view shows global options greyed, with an enable-for-project toggle (no removing global options).  
8) As a user, I get smooth wizard transitions and a clean, modern UI.

## Functional Requirements
- **Projects**
  - Fields: name, default_path (required), repo_url (optional), enabled flag.
  - Dropdown to select Project; final option is “Add New Project…”.
  - Selecting Project sets default path; user can override path text field.
- **Doc selection**
  - Default: create new doc per session with generated doc_id/title (request-log format).
  - Option: pick existing request-log doc discovered under project path.
- **Items**
  - Fields (dropdown unless noted): type (enhancement|bug|idea|task|research + add), domain (api|web|cli|data|infra|ml|ops + add), context (free text + saved options per project), priority (p0-p3 + add), status (triage|todo|in-progress|blocked|done + add), tags (multi-select + add), title, notes/acceptance (multiline).
  - IDs: `REQ-<doc-date>-<project-slug>-XX` with incremental counter within doc.
  - After submission, prompt to “Add another item to this doc?”; keep Project/doc fixed.
- **Doc writing**
  - Write markdown in request-log format with YAML front matter: type, doc_id, title, created/updated, status, owners, domains, item_count, items_index, tags (unique set).
  - When appending to existing doc, merge items_index and tags; update item_count and updated date.
- **Admin**
  - Page-level selector: Global vs Project <name>.
  - Manage options for each field (add/edit/delete where allowed). Global shown in project view (greyed), with “Enable for this project” toggle; cannot delete global from project view.
- **UI/UX**
  - Wizard steps: 1) Project; 2) Doc selection; 3) Item details; 4) Review & add next.
  - Modern iOS-ready style (glass/x-morphism), subtle motion for step transitions, focus/hover states.
  - Keyboard-friendly; accessible labels.

## Data & File Formats
- Request-log matches `docs/project_plans/ideas/requests-template.md`:
  - Front matter with `items_index` summary and quick index table.
  - Items as headings with metadata line and bullet notes.
- Project registry stored locally (JSON or TOML) under app config (e.g., `~/.meatycapture/projects.json`) with fields above.
- Field catalogs: global + per-project catalogs stored alongside config; union used at runtime, with enablement flags.

## Success Metrics
- Time-to-first-item < 60 seconds from launch.  
- 100% items include typed fields and tags.  
- No malformed doc output in smoke tests across sample paths.  
- Append operations preserve existing content and add merged tags/index correctly.

## Constraints / Risks
- File write conflicts if docs edited concurrently outside app (mitigation: last-write wins with backup copy for MVP).
- Path access permissions vary by OS; surface errors clearly.
- Future mobile port needs headless core: keep core logic UI-agnostic.

## Release Plan (MVP)
- Release 0.1: Local Projects, wizard capture, new doc creation, append existing, tag aggregation.
- Release 0.2: Admin field manager (global/project), enable toggles.
- Release 0.3: Packaging for desktop (Electron-lite or Tauri) with shared core for mobile porting.
