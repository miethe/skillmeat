---
type: request-log
doc_id: "REQ-20251203-web"
title: "Enhancements & Issues — 2025-12-03"
created: 2025-12-03
updated: 2025-12-03
status: "open"
owners: ["product-owner"]
domains: ["web"]
item_count: 6
items_index:
  - id: "REQ-20251203-web-01"
    type: enhancement
    domain: web
    context: "/collection (collections vs manage)"
    priority: medium
    status: triage
    title: "Custom artifact grouping at collection level"
    tags: ["ux", "organization"]
  - id: "REQ-20251203-web-02"
    type: enhancement
    domain: web
    context: "artifact modal /manage"
    priority: medium
    status: triage
    title: "Deployments tab shows projects using artifact"
    tags: ["visibility", "deployments"]
  - id: "REQ-20251203-web-03"
    type: bug
    domain: web
    context: "artifact add modal"
    priority: high
    status: triage
    title: "Artifact parameter auto-population not working"
    tags: ["bug", "import"]
  - id: "REQ-20251203-web-04"
    type: enhancement
    domain: web
    context: "artifact card /manage"
    priority: medium
    status: triage
    title: "Deployment counter on artifact card"
    tags: ["ui", "deployments"]
  - id: "REQ-20251203-web-05"
    type: enhancement
    domain: web
    context: "artifact card (all views)"
    priority: medium
    status: triage
    title: "Hover tooltips for artifact cards and icons"
    tags: ["ux", "tooltips"]
  - id: "REQ-20251203-web-06"
    type: enhancement
    domain: web
    context: "/manage"
    priority: medium
    status: blocked
    title: "Add /collection functionality to /manage"
    tags: ["tbd"]
---

# Enhancements & Issues — 2025-12-03

## Quick index (for agents)
| ID | Type | Domain | Context | Priority | Status | Title |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-20251203-web-01 | enhancement | web | /collection (collections vs manage) | medium | triage | Custom artifact grouping at collection level |
| REQ-20251203-web-02 | enhancement | web | artifact modal /manage | medium | triage | Deployments tab shows projects using artifact |
| REQ-20251203-web-03 | bug | web | artifact add modal | high | triage | Artifact parameter auto-population not working |
| REQ-20251203-web-04 | enhancement | web | artifact card /manage | medium | triage | Deployment counter on artifact card |
| REQ-20251203-web-05 | enhancement | web | artifact card (all views) | medium | triage | Hover tooltips for artifact cards and icons |
| REQ-20251203-web-06 | enhancement | web | /manage (unspecified) | medium | blocked | TBD: /manage should support … |

## Items

### REQ-20251203-web-01 — Custom artifact grouping at collection level
**Type:** enhancement | **Domain:** web | **Context:** /collection (collections vs manage) | **Priority:** medium | **Status:** triage
**Tags:** ux, organization

- Allow users to create custom groups of artifacts at the collection level for organization by criteria (functionality, project phase, team ownership, etc.).
- UI should support drag-and-drop grouping and regrouping within a collection.
- Could re-purpose the existing `/collection` page since `/manage` currently has similar functionality.
- Add a new visual indicator on artifact cards showing which custom group they belong to when viewing the full collection. This will require the UI/UX and frontend designer skill and subagents.

### REQ-20251203-web-02 — Deployments tab shows projects using artifact
**Type:** enhancement | **Domain:** web | **Context:** artifact modal /manage | **Priority:** medium | **Status:** triage
**Tags:** visibility, deployments

- Add a **Deployments** tab to the artifact modal on `/manage` that lists all projects where the artifact is deployed.
- Each project entry should display project name, deployment date, status (active/inactive), and deployed version.
- Project entry actions: button/icon to open that specific deployment modal; clicking project name navigates to `/projects/{id}`.
- Include a "Deploy to new project" action that opens a dialog to select the target project and configure deployment settings.

### REQ-20251203-web-03 — Artifact parameter auto-population not working
**Type:** bug | **Domain:** web | **Context:** artifact add modal | **Priority:** high | **Status:** triage
**Tags:** bug, import

- Reported issue: auto-population of artifact parameters during **Add Artifact** does not function.
- Needs reproduction steps and expected vs actual behavior; verify data source feeding parameter defaults.

### REQ-20251203-web-04 — Deployment counter on artifact card
**Type:** enhancement | **Domain:** web | **Context:** artifact card /manage | **Priority:** medium | **Status:** triage
**Tags:** ui, deployments

- On `/manage`, add a deployment counter on each artifact card to show how many projects the artifact is deployed to.
- Should integrate cleanly with existing card layout.

### REQ-20251203-web-05 — Hover tooltips for artifact cards and icons
**Type:** enhancement | **Domain:** web | **Context:** artifact card (all views) | **Priority:** medium | **Status:** triage
**Tags:** ux, tooltips

- Hovering over an artifact card should show full artifact name and description.
- On `/manage`, hovering the deployment counter should show a tooltip listing projects where the artifact is deployed.
- Hovering over the artifact type icon should show the full type name (e.g., "Claude Skill", "Claude Agent", etc.).

### REQ-20251203-web-06 — Add /collection functionality to /manage
**Type:** enhancement | **Domain:** web | **Context:** /manage (unspecified) | **Priority:** medium | **Status:** blocked
**Tags:** tbd

- PRD `marketplace-github-ingestion-v1` has suggested repurposing /collection for another use case; we should align /manage to include /collection functionality.
- /manage should add an 'All' tab to view all artifact types together, similar to `/collection`.
- /manage should support the full filtering/search/sorting/grouping capabilities currently in `/collection`, plus added in `REQ-20251203-web-01`.
