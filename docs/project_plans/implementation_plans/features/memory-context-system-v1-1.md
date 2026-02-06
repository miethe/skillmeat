---
title: "Implementation Plan: Memory & Context Intelligence System v1.1"
description: "Follow-up implementation plan for deferred Phase 5 auto-extraction, full memory CLI, global memories navigation, and skillmeat-cli skill updates."
audience: [ai-agents, developers, architects]
tags: [implementation, planning, memory, context, auto-extraction, cli, navigation]
created: 2026-02-06
updated: 2026-02-06
category: "product-planning"
status: draft
related:
  - /docs/project_plans/PRDs/features/memory-context-system-v1-1.md
  - /docs/project_plans/design-specs/memory-context-system-v1-1-ui-spec.md
  - /docs/project_plans/implementation_plans/features/memory-context-system-v1.md
  - /.claude/skills/skillmeat-cli/SKILL.md
---

# Implementation Plan: Memory & Context Intelligence System v1.1

**Plan ID**: `IMPL-2026-02-06-memory-context-system-v1-1`  
**Date**: 2026-02-06  
**Author**: Implementation Planner Agent  
**Complexity**: XL  
**Estimated Effort**: 44 story points  
**Target Timeline**: 5-6 weeks

---

## Executive Summary

This follow-up plan extends Memory & Context v1 with four major deliverables:

1. **Phase 5 Auto-Extraction** (deferred from v1)
2. **Complete memory CLI command set**
3. **Global Memories visibility and Projects IA refinement**
4. **Comprehensive `.claude/skills/skillmeat-cli/` updates for automation-first usage**

The plan preserves existing route contracts while introducing a global memories route and terminal-native workflows for capture/consumption.

---

## Architecture Additions

### Existing v1 Layers Reused

- Memory repositories, services, routers
- Context modules and pack generation
- Web memory components

### New/Extended Layers in v1.1

- Extraction pipeline service + run input adapters
- CLI command tree under `skillmeat memory ...`
- Global memories page/controller (project selector)
- Skill docs and workflow contracts in `.claude/skills/skillmeat-cli/`

---

## Phase 0: Design Lock & Contract Alignment

**Duration**: 0.5 week  
**Dependencies**: PRD + Design Spec draft

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P0.1 | API Contract Freeze | Finalize request/response shape for extraction + global memory search | API schema diff approved | 1 pt |
| V11-P0.2 | CLI Taxonomy Review | Lock command group and flag naming conventions | CLI contract doc approved | 1 pt |
| V11-P0.3 | Navigation IA Review | Confirm sidebar grouping and `/memories` behavior | UX sign-off captured | 1 pt |

---

## Phase 1: Auto-Extraction Service (Deferred v1 Phase 5)

**Duration**: 1.5 weeks  
**Dependencies**: Phase 0

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P1.1 | Extraction Input Model | Define run artifact payload schema (text blobs, metadata) | Pydantic schema + validation tests | 2 pts |
| V11-P1.2 | Extraction Pipeline | Implement parse -> candidate detect -> dedupe -> score -> persist candidate | End-to-end extraction test passes | 3 pts |
| V11-P1.3 | Similarity Guardrails | Add content hash + semantic threshold dedupe strategy | Duplicate false-positive rate under target | 2 pts |
| V11-P1.4 | Extraction API | Add preview/apply endpoints for extraction | OpenAPI docs + contract tests | 2 pts |
| V11-P1.5 | Feature Flag Gate | Respect `MEMORY_AUTO_EXTRACT` with clear disabled responses | Flag tests pass | 1 pt |

### Quality Gates

- Extraction never auto-promotes beyond `candidate`.
- Provenance contains run/session/commit linkage.
- Deterministic output for identical input.

---

## Phase 2: Full Memory CLI Surface

**Duration**: 1.5 weeks  
**Dependencies**: Phase 1 API finalized

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P2.1 | CLI Group Scaffolding | Add `memory` group to `skillmeat/cli.py` | `skillmeat memory --help` available | 1 pt |
| V11-P2.2 | Item Commands | Implement create/list/show/update/delete/lifecycle/merge/bulk commands | Command tests + JSON parity pass | 4 pts |
| V11-P2.3 | Module Commands | Implement module CRUD + add/remove/list items + duplicate | Integration tests pass | 3 pts |
| V11-P2.4 | Pack Commands | Implement preview/generate with output control | Output/file tests pass | 2 pts |
| V11-P2.5 | Extract Commands | Implement extract preview/apply commands | Extraction CLI tests pass | 2 pts |
| V11-P2.6 | Search Commands | Implement project/global memory search | Query tests + pagination pass | 1 pt |

### CLI Command Groups (target)

- `skillmeat memory item ...`
- `skillmeat memory module ...`
- `skillmeat memory pack ...`
- `skillmeat memory extract ...`
- `skillmeat memory search ...`

---

## Phase 3: Global Visibility + Navigation

**Duration**: 1 week  
**Dependencies**: Phase 0

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P3.1 | Sidebar IA Refactor | Move Projects into dedicated top-level group and add `Memories` entry | Navigation tests updated and passing | 2 pts |
| V11-P3.2 | Global Memories Route | Create `/memories` page with project selector + memory list reuse | Functional page with selector and deep-linking | 3 pts |
| V11-P3.3 | Project Detail CTA | Add "Open Memory" action in `/projects/[id]` | CTA visible and navigates correctly | 1 pt |
| V11-P3.4 | URL Stability Guard | Confirm no regressions on existing project routes | Route regression tests pass | 1 pt |

### Quality Gates

- Existing URLs remain unchanged.
- Keyboard triage parity with `/projects/[id]/memory`.

---

## Phase 4: Skill Documentation & Automation Flows

**Duration**: 0.75 week  
**Dependencies**: Phase 2

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P4.1 | SKILL Contract Update | Update `.claude/skills/skillmeat-cli/SKILL.md` for memory operations and fallback behavior | Skill instructions are accurate and actionable | 1 pt |
| V11-P4.2 | Skill README Refresh | Add memory command usage and workflows; remove stale duplication | README consistent and concise | 1 pt |
| V11-P4.3 | Command Reference Update | Add memory command matrix to quick reference | Agent docs include full memory CLI set | 1 pt |
| V11-P4.4 | Memory Workflow Doc | Add dedicated automation workflow (pre-run consume, post-run capture) | Workflow examples validated | 1 pt |

---

## Phase 5: Cross-Project Foundations (v1.1 scope)

**Duration**: 0.75 week  
**Dependencies**: Phase 2/3

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P5.1 | Global Query Contract | Extend list/search service with project metadata and all-project mode | API + UI query tests pass | 2 pts |
| V11-P5.2 | Share Scope Field | Add optional share scope enum for future cross-project flows | Migration + schema + defaults pass | 2 pts |
| V11-P5.3 | Safety Policy | Restrict default scope to project-private and explicit opt-in for broader scope | Policy tests + docs complete | 1 pt |

---

## Phase 6: Testing, Docs, and Rollout

**Duration**: 1 week  
**Dependencies**: Phases 1-5

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| V11-P6.1 | Test Matrix Expansion | Unit + integration + CLI + web navigation tests | Coverage >=85% for new modules | 2 pts |
| V11-P6.2 | Performance Validation | Validate p95 targets for extraction/list/pack | Benchmarks documented | 1 pt |
| V11-P6.3 | User Docs | Add/refresh user docs for new global memories and CLI workflows | Docs linked from user index | 1 pt |
| V11-P6.4 | Release Controls | Feature flag rollout + monitoring dashboards | Rollout checklist approved | 1 pt |

---

## Suggested Technical Work Breakdown

### Backend

- `skillmeat/core/services/auto_extraction_service.py` (new)
- `skillmeat/api/routers/memory_extraction.py` (new or extend memory router)
- `skillmeat/api/schemas/memory.py` and/or extraction schema module updates
- migration for optional share scope metadata

### CLI

- `skillmeat/cli.py` memory command tree and handlers
- tests under `tests/cli/` for new `memory` command group

### Web

- `skillmeat/web/components/navigation.tsx`
- `skillmeat/web/app/memories/page.tsx` (new)
- `skillmeat/web/app/projects/[id]/page.tsx` (memory CTA)

### Skill Docs

- `.claude/skills/skillmeat-cli/SKILL.md`
- `.claude/skills/skillmeat-cli/README.md`
- `.claude/skills/skillmeat-cli/references/command-quick-reference.md`
- `.claude/skills/skillmeat-cli/workflows/memory-context-workflow.md` (new)

---

## Risks & Mitigations

- **Extraction noise volume**: start with strict defaults, enforce candidate-only writes.
- **CLI complexity**: enforce consistent option naming and `--json` support.
- **IA confusion**: preserve existing URLs and add clear breadcrumbs/CTAs.
- **Cross-project safety**: explicit scope metadata and conservative defaults.

---

## Exit Criteria

- Auto-extraction preview/apply is available and guarded by feature flag.
- Full CLI command set for memory operations is available and tested.
- Global memories route and navigation updates are shipped without URL regressions.
- Skill docs support full memory automation loop for AI agents.
