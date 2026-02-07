---
title: 'PRD: Memory & Context Intelligence System v1.1'
description: Follow-up PRD for deferred auto-extraction (Phase 5), full CLI memory
  workflows, improved navigation visibility, and cross-project memory foundations.
audience:
- ai-agents
- developers
- architects
- product
tags:
- prd
- planning
- memory
- context
- cli
- navigation
- auto-extraction
- cross-project
created: 2026-02-06
updated: '2026-02-07'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/memory-context-system-v1.md
- /docs/project_plans/implementation_plans/features/memory-context-system-v1.md
- /docs/project_plans/design-specs/memory-context-system-ui-spec.md
- /.claude/skills/skillmeat-cli/SKILL.md
---

# PRD: Memory & Context Intelligence System v1.1

**Feature Name:** Memory & Context Intelligence System v1.1  
**Filepath Name:** `memory-context-system-v1-1`  
**Date:** 2026-02-06  
**Author:** Claude Code (AI Agent)  
**Version:** 1.0 (follow-up)  
**Status:** Superseded by v1.2 execution

---

## 1. Executive Summary

Memory & Context v1 delivered project-scoped memory CRUD, lifecycle governance, context modules, and context pack generation via API/Web UI. This follow-up (v1.1) closes the highest-value gaps:

1. Deliver deferred **Phase 5 auto-extraction** from agent run artifacts.
2. Deliver a complete **memory CLI command group** for creation and consumption in terminal-first and automation workflows.
3. Increase discoverability with a **top-level Projects navigation group** and a new **global Memories page**.
4. Establish foundations for **cross-project memory sharing/search** without blocking v1.1 delivery.
5. Update `.claude/skills/skillmeat-cli/` so agents can reliably use memory features end-to-end.

**Priority:** HIGH

---

## 2. Context & Current Gaps

### 2.1 What Exists (v1)

- Project-scoped memory model and lifecycle (`candidate`, `active`, `stable`, `deprecated`)
- Context modules and token-budget pack APIs
- Project memory page at `/projects/[id]/memory`
- Runtime gating assumptions in this section are historical. Current shipped behavior deploys memory/context endpoints directly without runtime feature gating.

### 2.2 Gaps

1. **No first-class CLI for memory system**
- Current CLI docs/entrypoint do not expose a `skillmeat memory ...` surface.

2. **No automatic capture path**
- Phase 5 was deferred; learnings are still mostly manual unless users explicitly create memories.

3. **Low visibility/discoverability in UI**
- Memory features are buried under per-project detail routes.

4. **Automation friction for agentic workflows**
- No standard pre-run/post-run commands for "generate context pack" and "capture learnings" loops.

5. **Cross-project future is not scaffolded**
- No global memory view, no cross-project search contract, no opt-in sharing model.

---

## 3. Goals & Success Metrics

### Goal A: Automatic Memory Capture

Implement Phase 5 extraction pipeline that proposes candidate memories from run artifacts/logs.

- Metric: >=70% of extracted items are accepted or edited (not discarded) in pilot projects.
- Metric: Extraction latency <=2s p95 for typical run artifacts (<2 MB text corpus).

### Goal B: Full CLI Coverage for Memory Lifecycle + Consumption

Ship `skillmeat memory ...` commands for item, module, pack, and extraction workflows.

- Metric: 100% parity with core memory API capabilities.
- Metric: >=80% of memory operations in dogfooding can be completed without web UI.

### Goal C: Visibility & Navigation

Make Memories directly discoverable from primary sidebar IA.

- Metric: New global Memories page adoption by >=60% of active users in 30 days.
- Metric: Time-to-memory-page navigation reduced by >=50% vs v1 baseline.

### Goal D: Foundations for Cross-Project Memory

Support global query and explicit sharing policies as v1.1 foundations.

- Metric: Global read path supports project-filtered and all-project queries with <300ms p95.

---

## 4. Scope

### In Scope (v1.1)

- Deferred Phase 5 auto-extraction service (opt-in, review-first)
- New CLI namespace: `skillmeat memory` (full CRUD/lifecycle/module/pack/extract/search)
- Sidebar IA change: explicit Projects group with direct Memories entry
- New global memory route (proposed: `/memories`) with project selector
- Project detail CTA linking to project memory page (`/projects/[id]/memory`)
- Skill updates under `.claude/skills/skillmeat-cli/`
- API extensions for extraction jobs, run-source ingestion, and global memory list/search

### Out of Scope (v1.1)

- Fully autonomous, unreviewed memory promotion
- Cross-user/team cloud sync beyond local instance boundaries
- Embedding/vector infrastructure dependency as required path
- Automatic prompt injection at every runtime without user/agent control

---

## 5. Functional Requirements

### 5.1 Auto-Extraction (Phase 5)

- **FR-5.1** Ingest run artifact/log payload and produce candidate memory items.
- **FR-5.2** Deduplicate against existing project memory by content hash + semantic similarity threshold.
- **FR-5.3** Support configurable extraction profiles (`strict`, `balanced`, `aggressive`).
- **FR-5.4** Persist provenance linking extraction to run id/session id/commit.
- **FR-5.5** Never auto-promote extracted memories beyond `candidate` in v1.1.

### 5.2 CLI Memory Surface

- **FR-5.6** `skillmeat memory item` command group:
  - `create`, `list`, `show`, `update`, `delete`, `promote`, `deprecate`, `merge`, `bulk-promote`, `bulk-deprecate`
- **FR-5.7** `skillmeat memory module` command group:
  - `create`, `list`, `show`, `update`, `delete`, `add-item`, `remove-item`, `list-items`, `duplicate`
- **FR-5.8** `skillmeat memory pack` command group:
  - `preview`, `generate` with file/stdout output modes
- **FR-5.9** `skillmeat memory extract` command group:
  - `run`, `preview`, `apply` (review-first pipeline)
- **FR-5.10** `skillmeat memory search` command:
  - scoped (`--project`) and global (`--all-projects`) query

### 5.3 Navigation & Visibility

- **FR-5.11** Sidebar adds a top-level **Projects** group containing:
  - `Projects` (`/projects`)
  - `Memories` (`/memories`)
- **FR-5.12** Existing project detail flows remain on same URL paths.
- **FR-5.13** New `/memories` page supports project picker + deep-link into `/projects/[id]/memory`.
- **FR-5.14** Project detail page includes direct "Open Memory" action.

### 5.4 Cross-Project Foundations

- **FR-5.15** Global list/search API includes project ownership metadata.
- **FR-5.16** Optional share scope field for future cross-project reuse (`private`, `project`, `global_candidate`).

---

## 6. Proposed CLI Command Set (Target)

```bash
# Item lifecycle
skillmeat memory item create --project <project> --type decision --content "..." --confidence 0.82
skillmeat memory item list --project <project> --status candidate --type gotcha --limit 50
skillmeat memory item show <item-id>
skillmeat memory item update <item-id> --content "..." --confidence 0.9
skillmeat memory item promote <item-id> --reason "validated in prod"
skillmeat memory item deprecate <item-id> --reason "superseded"
skillmeat memory item merge --source <id> --target <id> --strategy combine --merged-content "..."
skillmeat memory item bulk-promote --ids <id1,id2> --reason "triage"

# Module management
skillmeat memory module create --project <project> --name "API Debug" --types decision,constraint,gotcha --min-confidence 0.7
skillmeat memory module add-item <module-id> --item <item-id> --ordering 10
skillmeat memory module list --project <project>

# Pack generation
skillmeat memory pack preview --project <project> --module <module-id> --budget 4000 --json
skillmeat memory pack generate --project <project> --module <module-id> --budget 4000 --output ./context-pack.md

# Auto-extraction
skillmeat memory extract preview --project <project> --run-log ./run.log --profile balanced
skillmeat memory extract apply --project <project> --run-log ./run.log --min-confidence 0.65

# Search/future foundation
skillmeat memory search "oauth timeout" --project <project>
skillmeat memory search "postgres migration lock" --all-projects
```

---

## 7. UX / IA Requirements

- Preserve existing routes and behavior for project pages.
- Add global discoverability via `/memories`.
- Ensure keyboard workflows remain first-class in both global and project memory views.
- Include project context chip and switcher in global memory list.

---

## 8. Non-Functional Requirements

- Memory list/search p95 <300ms (project and global)
- Pack preview/generate p95 <500ms
- Extraction dry-run p95 <2s for typical run artifacts
- WCAG 2.1 AA for new global memories UI and selector flows
- Structured observability for extraction pipeline (traceable by run_id)

---

## 9. Risks & Mitigations

- **Risk:** Low-signal extraction floods candidate queue.  
  **Mitigation:** conservative default profile + confidence threshold + batching + dedupe.

- **Risk:** CLI surface complexity increases support burden.  
  **Mitigation:** strong command taxonomy, consistent flags, JSON output parity.

- **Risk:** Navigation refactor causes orientation confusion.  
  **Mitigation:** keep old routes, add breadcrumbs, add project memory CTA.

- **Risk:** Cross-project leakage concerns.  
  **Mitigation:** explicit share scopes, default private/project-local behavior.

---

## 10. Rollout Strategy (Historical)

This PRD section reflects the original v1.1 proposal.
Current v1.2 execution uses direct deployment with CI/test gates, candidate-only extraction writes, and operational monitoring.

---

## 11. Dependencies

- Existing v1 memory tables/services/APIs
- Run artifact/log source contract (from agent workflows)
- CLI command architecture in `skillmeat/cli.py`
- `.claude/skills/skillmeat-cli/` docs updates for agent usage patterns

---

## 12. Acceptance Criteria

- New PRD-approved CLI command set documented and implemented (or explicitly flagged staged if partial).
- Auto-extraction paths create candidate items with provenance and deterministic dedupe.
- `/memories` page and new Projects sidebar group are usable without changing existing URLs.
- Skill docs accurately describe current vs planned memory command flows and automation recipes.
