---
title: 'Implementation Plan: Memory & Context Gap Closure (v1.2)'
description: Execution plan to close functional, UX, API, CLI, extraction, and navigation
  gaps identified after Memory & Context v1 delivery.
audience:
- ai-agents
- developers
- architects
- product
tags:
- implementation
- planning
- memory
- context
- gap-closure
- v1.2
created: 2026-02-06
updated: 2026-02-07
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/implementation_plans/features/memory-context-system-v1.md
- /docs/project_plans/implementation_plans/features/memory-context-system-v1-1.md
- /docs/project_plans/PRDs/features/memory-context-system-v1.md
- /docs/project_plans/PRDs/features/memory-context-system-v1-1.md
- /docs/project_plans/design-specs/memory-context-system-v1-1-ui-spec.md
---
# Implementation Plan: Memory & Context Gap Closure (v1.2)

**Plan ID**: `IMPL-2026-02-06-memory-context-gap-closure-v1-2`
**Date**: 2026-02-06
**Target Timeline**: 6-8 weeks (phased, shippable increments)
**Goal**: Close all known post-v1 gaps and align shipped behavior with PRD expectations (v1 + deferred v1.1 scope).

## 1. Executive Summary

This plan closes all identified gaps across six areas:

1. Memory Inbox correctness and UX regressions.
2. Context Modules + Context Pack UI integration and missing actions.
3. Selector and packing parity with documented behavior.
4. CLI parity for memory operations.
5. Auto-extraction pipeline delivery.
6. Global memory visibility and navigation IA.

Delivery is split into 3 tracks:

- **Track A (P0 Stabilization)**: Fix correctness issues in currently exposed `/projects/[id]/memory` experience.
- **Track B (P1 Feature Completion)**: Complete context modules/packing UX and selector semantics.
- **Track C (P2 Deferred Scope Completion)**: Ship CLI, extraction, and global memory workflows from v1.1.

---

## 2. Gap Inventory and Closure Mapping

| Gap ID | Gap | Severity | Closure Phase |
|---|---|---|---|
| G1 | Memory type tab values mismatched with backend enum (`fix`, `pattern`) | Critical | Phase 1 |
| G2 | Search query not applied to backend or effective filtering | Critical | Phase 1 |
| G3 | Type/status count badges not aligned with API shape/intent | High | Phase 1 |
| G4 | Memory settings CTA is non-functional | Medium | Phase 1 |
| G5 | Context Modules UI components not mounted in live project memory route | High | Phase 2 |
| G6 | ContextModulesTab hook contract/mutation contract mismatches | Critical | Phase 2 |
| G7 | Context module edit/preview actions are placeholders | High | Phase 2 |
| G8 | Manual memory add-to-module flow is disabled/TODO | High | Phase 2 |
| G9 | `file_patterns` and `workflow_stages` selectors accepted but not applied in pack selection | High | Phase 3 |
| G10 | Context packer currently excludes context entities despite PRD intent | High | Phase 3 |
| G11 | Memory CLI command tree (`skillmeat memory ...`) absent | High | Phase 4 |
| G12 | Auto-extraction service/endpoints absent | High | Phase 5 |
| G13 | Global `/memories` route + sidebar IA updates absent | Medium | Phase 6 |
| G14 | Docs overstate shipped UI flow (tabs/features not fully exposed) | High | Phase 7 |
| G15 | Feature-flag defaults/behavior drift vs rollout expectations | Medium | Phase 7 |

---

## 3. Phase Plan

## Phase 0: Contract Freeze and Scope Lock (0.5 week)

### Objectives
- Lock API/UI contracts for memory list search, count responses, and module hooks.
- Confirm whether v1.2 includes all v1.1 deferred scope in this cycle.

### Tasks
- `GC-0.1` Publish ADR for memory list query contract (search semantics, server-side vs client-side fallback).
- `GC-0.2` Publish ADR for counts contract (single aggregate vs per-type/status aggregate endpoint).
- `GC-0.3` Lock module hooks interface and mutation payloads to prevent shape drift.

### Exit Criteria
- Signed API contract notes in docs.
- All downstream phases reference frozen request/response shapes.

---

## Phase 1: P0 Stabilization of Memory Inbox (1 week)

### Objectives
- Make current `/projects/[id]/memory` path reliable and semantically correct.

### Tasks
- `GC-1.1` Replace invalid memory type values with valid enum set.
- `GC-1.2` Implement search filtering end-to-end:
  - Add optional `search` query support in memory list API/service/repository OR
  - Apply explicit client-side filtering with pagination caveat documented.
- `GC-1.3` Fix counts integration:
  - Add aggregate counts endpoint (all + per-type + per-status) or
  - Adjust UI to consume available count model correctly.
- `GC-1.4` Wire Memory Settings CTA:
  - Route to settings page if available, or
  - Hide/disable with explicit “coming soon” affordance.
- `GC-1.5` Add regression tests for type filtering, search behavior, and badge counts.

### Acceptance Criteria
- Type tabs map to backend-supported values only.
- Search input changes visible list deterministically.
- Badge counts are non-zero and correct for seeded fixture data.
- No dead primary CTA in page header.

---

## Phase 2: Context Modules + Packs UX Completion (1.5 weeks)

### Objectives
- Expose and complete module/pack flows already partially implemented.

### Tasks
- `GC-2.1` Mount context modules and pack generation UI into project memory route.
- `GC-2.2` Fix hook signature and mutation payload mismatches (`useContextModules`, delete payload).
- `GC-2.3` Implement module edit flow (open editor, persist updates, optimistic refresh).
- `GC-2.4` Implement module preview action (open pack preview flow scoped to module).
- `GC-2.5` Implement manual memory picker for add-to-module (search + select + ordering).
- `GC-2.6` Add integration tests for create/edit/delete module and add/remove memory flows.

### Acceptance Criteria
- User can create, edit, preview, and delete modules from live UI.
- User can manually add and remove memory items from modules.
- Context pack preview can be launched from module card action.

---

## Phase 3: Selector and Packer Parity (1.5 weeks)

### Objectives
- Ensure selectors behave as documented and pack composition matches product intent.

### Tasks
- `GC-3.1` Implement `file_patterns` selector filtering in pack candidate selection.
- `GC-3.2` Implement `workflow_stages` selector filtering (using provenance/metadata stage field contract).
- `GC-3.3` Extend context pack service to include context entities as pack candidates.
- `GC-3.4` Define deterministic merge order: module selectors, manual inclusions, entities, then token budget ranking.
- `GC-3.5` Add service + API tests for selector correctness and mixed memory/entity packs.

### Acceptance Criteria
- All four selector dimensions are applied, not just validated.
- Generated packs can include both memories and context entities.
- Preview and generate endpoints return consistent item sets under same inputs.

---

## Phase 4: Memory CLI Parity (1.25 weeks)

### Objectives
- Deliver full terminal-first memory workflow.

### Tasks
- `GC-4.1` Add `skillmeat memory item` commands:
  - create/list/show/update/delete/promote/deprecate/merge/bulk-promote/bulk-deprecate
- `GC-4.2` Add `skillmeat memory module` commands:
  - create/list/show/update/delete/add-item/remove-item/list-items/duplicate
- `GC-4.3` Add `skillmeat memory pack` commands:
  - preview/generate with stdout/file output.
- `GC-4.4` Add `skillmeat memory search` scoped/global query.
- `GC-4.5` CLI test coverage and docs update in `.claude/skills/skillmeat-cli/`.

### Acceptance Criteria
- CLI supports parity operations for items/modules/packs/search.
- `--json` and non-interactive automation-friendly output supported.

---

## Phase 5: Auto-Extraction Delivery (1.5 weeks)

### Objectives
- Ship deferred extraction path with direct deployment semantics.

### Tasks
- `GC-5.1` Implement `MemoryExtractorService` (parse -> candidate detect -> dedupe -> score).
- `GC-5.2` Add extraction endpoints (`preview` + `apply`) and payload schema.
- `GC-5.3` Enforce candidate-only writes (no auto-promotion).
- `GC-5.4` Validate extraction endpoint availability and candidate-only safety behavior.
- `GC-5.5` Add extraction quality and deterministic replay tests.

### Acceptance Criteria
- Same input corpus yields stable extraction output.
- Extraction endpoints are available without runtime feature gating.
- Applied extraction writes candidate memories with complete provenance.

---

## Phase 6: Global Memories + Navigation IA (1 week)

### Objectives
- Improve discoverability and enable cross-project review workflows.

### Tasks
- `GC-6.1` Add `/memories` route with project selector and deep-link to project memory page.
- `GC-6.2` Update sidebar IA with Projects + Memories grouping.
- `GC-6.3` Add project detail CTA (“Open Memory”) for direct access.
- `GC-6.4` Add global query support in memory list/search API if required by route.

### Acceptance Criteria
- Users can navigate to global memories from primary sidebar.
- Existing project URLs remain stable and unaffected.

---

## Phase 7: Docs, Observability, and Release Hardening (0.75 week)

### Objectives
- Align documentation with actual shipped behavior and harden release controls.

### Tasks
- `GC-7.1` Update user docs to match final UI structure and feature availability.
- `GC-7.2` Document direct deployment posture (no runtime memory/extraction gating).
- `GC-7.3` Add missing observability counters/spans for new flows (search, module actions, extraction).
- `GC-7.4` Finalize rollout checklist and smoke tests.

### Acceptance Criteria
- No doc path instructs unavailable UI behavior.
- Direct deployment behavior is explicit and validated in tests.
- Operational runbook reflects new routes/endpoints.

---

## 4. Testing Matrix

| Layer | Coverage Focus |
|---|---|
| Unit | service selector semantics, search filtering, extraction scoring/dedupe |
| API Integration | memory list/count/search, module CRUD + associations, pack preview/generate, extract endpoints |
| Web Component | memory filters/count badges, module editor actions, preview dialogs |
| Web E2E | project memory triage flow, context module flow, global memories navigation |
| CLI | command parsing, JSON output, parity with API operations |
| Performance | list p95, pack p95, extraction p95 targets |

---

## 5. Rollout Strategy

1. Ship **Phase 1** independently as hotfix release (stabilization).
2. Ship **Phases 2-3** as feature completion release.
3. Ship **Phases 4-5** directly with test-gated release checks.
4. Ship **Phase 6** IA update with route regression tests.
5. Ship **Phase 7** docs + operations update as release gate.

---

## 6. Definition of Done

- All G1-G15 gaps are either:
  - implemented and validated, or
  - explicitly deferred with approved follow-up plan and tracked issue.
- Memory UI, API, and CLI behaviors are contract-consistent.
- Context modules and pack generation are fully operable in production UI.
- Extraction is available with review-first candidate-only writes.
- Documentation and navigation accurately reflect shipped product.

## 7. Execution Notes (Current Pass)

- G11 (Memory CLI): Implemented `skillmeat memory` command tree for items/modules/packs/extract/search.
- G12 (Auto-extraction): Implemented preview/apply extraction endpoints and extraction service with candidate-only writes.
- G13 (Global memories IA): Backend global list/search support implemented; `/memories` page + sidebar IA deferred as UI-heavy follow-up.
- G14 (Docs): Updated user/developer docs to reflect current memory/context behavior and APIs.
- G15 (Flags): Memory/context endpoint gating removed; memory features deploy directly without runtime feature toggles.

## 8. Remaining Gap Assessment vs PRD v1.1 (2026-02-07)

This section compares current v1.2 execution status to PRD v1.1 (`/docs/project_plans/PRDs/features/memory-context-system-v1-1.md`) and tracks only remaining or not-yet-evidenced items.

| Remaining Gap ID | PRD Reference | Gap | Evidence in Current Plan/Notes | Closure Needed |
|---|---|---|---|---|
| RG1 | FR-5.11, FR-5.13, FR-5.14 | Global memories discoverability UI still incomplete (`/memories`, sidebar group, project detail CTA). | Explicitly deferred in G13 execution note. | Implement UI routes/navigation and validate route stability. |
| RG2 | FR-5.16 | Share-scope foundation (`private`, `project`, `global_candidate`) is not explicitly planned as a schema/API deliverable. | No explicit task in Phases 1-7. | Add schema + API + CLI/UI read/write path for `share_scope`. |
| RG3 | FR-5.3 | Extraction profiles (`strict`, `balanced`, `aggressive`) are not explicitly contract-tested in plan acceptance. | Phase 5 covers extraction generally, but profile behavior is not acceptance-gated. | Add profile contract tests and documented defaults. |
| RG4 | FR-5.15 | Global list/search ownership metadata is not explicitly acceptance-gated. | Phase 6 references global query support, but not metadata completeness checks. | Add response contract tests for ownership metadata in global endpoints. |
| RG5 | FR-5.9 | CLI extraction parity requires `run`, `preview`, `apply`; `run` parity not explicitly acceptance-gated. | Execution notes mention extract tree; explicit subcommand parity not called out. | Add explicit CLI parity test + docs for all extraction subcommands. |
| RG6 | Goals A-D, NFRs | Success metrics/instrumentation not fully operationalized (acceptance %, adoption, latency dashboards). | Testing matrix names perf category but lacks measurable release gate thresholds. | Add observability + release gate checklist tied to PRD metrics. |

## 9. Updated Remaining-Gap Closure Plan (v1.2.1)

**Target Timeline**: 2.5-3.5 weeks  
**Goal**: Close RG1-RG6 and declare PRD v1.1 full closure with test-backed evidence.

### Phase R1: Global Memories UI + IA Completion (1 week)

#### Tasks
- `R1.1` Implement `/memories` route with project picker and deep-link to `/projects/[id]/memory`.
- `R1.2` Implement sidebar top-level `Projects` group with `Projects` and `Memories` entries.
- `R1.3` Add project detail page CTA: `Open Memory`.
- `R1.4` Add E2E tests for all three navigation entry points and legacy URL stability.

#### Acceptance Criteria
- FR-5.11/5.13/5.14 behaviors are visible in production UI.
- Existing project memory URLs remain unchanged and functional.

### Phase R2: Cross-Project Foundations Contract Completion (0.75 week)

#### Tasks
- `R2.1` Add/confirm `share_scope` on memory model with allowed values: `private`, `project`, `global_candidate`.
- `R2.2` Add API contract coverage for global list/search ownership metadata (`project_id`, `project_name`, scope).
- `R2.3` Add migration/backfill rules for existing memories (default `project` or explicit decided default).
- `R2.4` Add CLI exposure for setting/filtering `share_scope` where applicable.

#### Acceptance Criteria
- FR-5.15 and FR-5.16 are validated by API integration tests and documented contracts.
- No cross-project leakage occurs without explicit scope.

### Phase R3: Extraction and CLI Parity Hardening (0.5 week)

#### Tasks
- `R3.1` Enforce extraction profile contract (`strict`, `balanced`, `aggressive`) with deterministic tests.
- `R3.2` Ensure CLI extraction includes `run`, `preview`, and `apply` with automation-friendly output.
- `R3.3` Document extraction profile semantics and recommended defaults.

#### Acceptance Criteria
- FR-5.3 and FR-5.9 are explicitly test-passing and documented.
- Replay corpus confirms stable outputs per profile.

### Phase R4: Metrics, Observability, and Closure Gate (0.5-0.75 week)

#### Tasks
- `R4.1` Add dashboard/report queries for PRD metrics:
  - extraction acceptance/edit rate
  - extraction latency p95
  - global query latency p95
  - global memories adoption and navigation time-to-target
- `R4.2` Add release gate checklist mapping each PRD goal/FR to evidence artifact (test, dashboard, doc).
- `R4.3` Run pilot measurement window and publish closure report.

#### Acceptance Criteria
- PRD Goal A-D metrics have measurable sources and threshold checks.
- v1.1 PRD closure can be signed with objective evidence.

## 10. Updated Definition of Done for v1.2 Closeout

- RG1-RG6 are closed or explicitly deferred with approved issue IDs and owner/date.
- PRD FR-5.1 through FR-5.16 each map to passing tests and docs references.
- Global memories UX (`/memories` + sidebar + project CTA) is live.
- Cross-project foundations include explicit `share_scope` + ownership metadata contracts.
- Extraction profile behavior and CLI extract parity are validated in CI.
