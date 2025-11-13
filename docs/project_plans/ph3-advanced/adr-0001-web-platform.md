---
title: "ADR-0001: Web Platform Stack for SkillMeat Phase 3"
status: accepted
date: 2025-11-10
deciders: ["lead-architect", "product-team"]
tags: [adr, web, architecture, phase3]
---

# ADR-0001 — Web Platform Stack for SkillMeat Phase 3

## Context

Phase 3 introduces a browser-based experience (F3.1) plus collaboration layers (F3.2) that must coexist with the existing Python CLI + local collection filesystem. The chosen stack needs to:

- Reuse current collection logic (ArtifactManager, manifests, sync subsystems).
- Serve both local-only deployments and hosted deployments without rewriting the core.
- Support modern UI patterns (React components, charts, drag-and-drop) and integrate with analytics added in Phase 2.
- Keep deployment lightweight so solo developers can run the UI locally (no heavy infra requirement).

Evaluated options:

1. **Extend CLI with TUI** (Textual-rich UI)
   - ✅ Minimal additional services.
   - ❌ Does not deliver browser-based experience, no sharing endpoints.
2. **Electron/desktop app**
   - ✅ Rich UI, offline storage.
   - ❌ Packaging burden across OSes, harder to automate, still needs backend for sharing.
3. **Web stack (Next.js + FastAPI)**
   - ✅ Modern React UI, SSR for fast load, API easy to host, leverages Python core via FastAPI.
   - ✅ Clear separation between presentation (Next.js) and orchestration (FastAPI service calling SkillMeat core as library).
   - ❌ Requires bundling Node + Python runtimes, adds deployment complexity.

## Decision

Adopt **Next.js 15 (App Router) for the web frontend** and **FastAPI for the backend API layer**, both running locally via `skillmeat web` and deployable to hosted environments. Key details:

- Backend service (`skillmeat/api/server.py`) exposes REST + SSE endpoints for collections, artifacts, analytics, sharing, and marketplace brokers. It loads the same configuration as CLI, invoking ArtifactManager/SearchManager/SyncManager modules directly.
- Frontend uses Next.js + Tailwind + shadcn/ui to provide dashboards, artifact browsers, MCP configuration editors, and marketplace workflows. The UI communicates with FastAPI via a thin TypeScript SDK generated from the OpenAPI schema.
- Authentication uses local API tokens in self-hosted mode and Clerk (or future provider) in hosted/team mode. Tokens stored in `~/.skillmeat/web/token`.
- Packaging: `skillmeat web dev` launches FastAPI via Uvicorn and Next.js via `pnpm dev`; `skillmeat web build` compiles production bundles; `skillmeat web start` launches both behind a supervisor (e.g., `uvicorn` + `node server.js`) for local use.

## Consequences

### Positive

- Re-uses Python code, minimizing divergence between CLI and web operations.
- OpenAPI contract makes AI-agent consumption easy (JSON schema).
- Next.js ecosystem unlocks rich data visualizations for analytics and marketplace browsing.
- FastAPI middle-tier is testable with existing pytest stack.

### Negative / Mitigations

- **Dual runtime management**: Provide helper CLI commands (`skillmeat web deps`, `skillmeat web doctor`) to verify Node availability.
- **State synchronization**: Add file watchers + SSE endpoints so the web UI stays in sync when CLI mutates the collection. Use `watchfiles` in FastAPI layer and send `collection.updated` events.
- **Security**: Provide HTTP middleware for token validation and same-origin policy. Document best practices for self-hosted TLS (ngrok, Caddy, etc.).

### Follow-Up Actions

- Generate OpenAPI schema + TS SDK as part of build (tracked in Phase 3 implementation plan).
- Define CI jobs for frontend lint/test separate from Python tests.
- Add monitoring for long-running FastAPI server when used in hosted mode.
