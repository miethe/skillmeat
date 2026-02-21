---
schema_name: ccdash_document
schema_version: 2
doc_type: implementation_plan
doc_subtype: implementation_plan
root_kind: project_plans
id: DOC-sync-status-performance-refactor-v1
title: Sync Status Performance Refactor v1
status: in-progress
category: refactors
feature_slug: sync-status-performance-refactor-v1
feature_version: v1
feature_family: sync-status-performance-refactor
prd_ref: ''
plan_ref: sync-status-performance-refactor-v1
related_documents:
- docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md
- docs/project_plans/implementation_plans/bug-fixes/sync-status-tab-remediation-v1.md
related_features:
- sync-status-tab-remediation
linked_sessions: []
linked_tasks: []
owner: engineering
owners:
- engineering
contributors:
- backend
- frontend
- platform
reviewers: []
approvers: []
request_log_ids: []
commit_refs: []
pr_refs: []
priority: high
risk_level: medium
confidence: 0.84
created: 2026-02-20 00:00:00+00:00
updated: '2026-02-21'
target_release: 2026-Q2
milestone: Sync Status Performance Refactor
tags:
- plan
- implementation
- performance
- sync-status
labels:
- backend-hotpath
- frontend-query-orchestration
files_affected:
- skillmeat/api/routers/deployments.py
- skillmeat/core/deployment.py
- skillmeat/storage/deployment.py
- skillmeat/api/routers/artifacts.py
- skillmeat/core/artifact.py
- skillmeat/sources/github.py
- skillmeat/web/components/manage/artifact-operations-modal.tsx
- skillmeat/web/components/sync-status/sync-status-tab.tsx
- skillmeat/web/components/entity/project-selector-for-diff.tsx
- skillmeat/web/components/entity/diff-viewer.tsx
context_files:
- docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md
- .claude/specs/artifact-structures/ccdash-doc-structure.md
scope:
  in_scope:
  - deployment status hot-path optimization
  - diff endpoint contract optimization (summary-first, lazy details)
  - upstream update/fetch short-lived caching
  - frontend sync modal query orchestration and prewarm strategy
  - client diff rendering optimization for large payloads
  - instrumentation and performance regression test coverage
  out_of_scope:
  - new sync feature semantics (merge strategy behavior changes)
  - migration of unrelated modal tabs
  - changes to artifact business rules unrelated to performance
architecture_summary: Refactor follows layered architecture from API routers to service/storage
  hot paths, then frontend orchestration and UI rendering.
rollout_strategy: Implement behind additive API flags and preserve legacy defaults
  until frontend migration is complete.
rollback_strategy: Keep old endpoint behavior and query gating toggles available;
  disable summary-first/lazy-diff paths via config if regressions appear.
observability_plan: Add backend timing logs for diff/status endpoints and frontend
  marks for sync-tab load milestones.
security_considerations:
- Preserve existing project path validation and access controls in diff/deploy endpoints.
- Avoid broad cache keys that could leak cross-artifact data.
test_strategy:
- backend unit tests for single-pass status computation and diff mode flags
- backend integration tests for payload compatibility and cache invalidation
- frontend integration tests for query gating and lazy diff load behavior
- performance assertions in sync modal integration tests
dependencies:
  internal:
  - deployment tracker read/write and status flow
  - artifacts diff endpoint schemas
  - sync modal integration tests
  external: []
phases:
- id: P1
  phase: 1
  title: Baseline and Instrumentation
  status: pending
  entry_criteria:
  - Analysis report approved
  exit_criteria:
  - Baseline timings captured for sync tab load and endpoint latency
  deliverables:
  - benchmark notes and instrumentation patches
- id: P2
  phase: 2
  title: Deployment Status Hot-Path Refactor
  status: pending
  entry_criteria:
  - Baseline metrics available
  exit_criteria:
  - Single-pass status path merged and verified
  deliverables:
  - optimized deployment status computation path
- id: P3
  phase: 3
  title: Diff API Contract Refactor
  status: pending
  entry_criteria:
  - P2 complete
  exit_criteria:
  - summary-first diff mode available and tested
  deliverables:
  - API flags and compatibility coverage
- id: P4
  phase: 4
  title: Upstream Fetch/Check Caching
  status: pending
  entry_criteria:
  - P3 complete
  exit_criteria:
  - repeated upstream checks avoid redundant heavy work
  deliverables:
  - cache layer and invalidation strategy
- id: P5
  phase: 5
  title: Frontend Query Orchestration Refactor
  status: pending
  entry_criteria:
  - P3 contracts finalized
  exit_criteria:
  - sync path no longer fans out unnecessary requests
  deliverables:
  - modal and sync-tab query gating updates
- id: P6
  phase: 6
  title: Diff Viewer Rendering Optimization
  status: pending
  entry_criteria:
  - P5 complete
  exit_criteria:
  - large diff views render with reduced upfront parsing
  deliverables:
  - lazy parsing and selective stats computation
- id: P7
  phase: 7
  title: Validation and Rollout
  status: pending
  entry_criteria:
  - P2-P6 complete
  exit_criteria:
  - regression suite green and release guardrails defined
  deliverables:
  - test evidence and rollout checklist
effort_estimate:
  engineering_weeks: 4
  story_points: 34
---

# Sync Status Performance Refactor v1

## 1. Executive Summary

This plan addresses Sync Status tab latency by refactoring the most expensive backend and frontend paths identified in the analysis report:

- eliminate repeated deployment read/hash loops
- shift diff APIs to summary-first and lazy-detail delivery
- reduce upstream fetch/check repetition with targeted caching
- stop early fanout and duplicate data retrieval in modal flows
- reduce client-side diff parsing overhead on large payloads

The refactor preserves current sync semantics and focuses on performance, scalability, and reliability of current behavior.

## 2. Implementation Strategy

### 2.1 Sequence

1. Measure current baseline and add instrumentation.
2. Remove backend hot-path inefficiencies first (largest gains).
3. Introduce additive API contracts for summary-first diffs.
4. Update frontend orchestration to use optimized contracts.
5. Optimize rendering path and complete validation/rollout.

### 2.2 Critical Path

- P2 deployment status optimization
- P3 diff API contract changes
- P5 frontend migration onto new contracts

### 2.3 Parallel Opportunities

- P4 upstream caching can start after P3 API behavior is stable.
- P6 viewer optimization can run in parallel with late P5 integration.

## 3. Phase Breakdown

## Phase 1: Baseline and Instrumentation

Assigned Subagent(s): `react-performance-optimizer`, `python-backend-engineer`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P1-T1 | Define baseline scenarios | Capture repeatable scenarios for sync-tab first open, tab switch, and modal reopen across small/large artifacts. | Scenario matrix documented with input sizes and expected telemetry. | 1 pt |
| P1-T2 | Backend endpoint timing hooks | Add timing logs around `/deploy`, `/diff`, `/upstream-diff`, `/source-project-diff` and status computation internals. | Logs expose wall time and major sub-step durations. | 2 pts |
| P1-T3 | Frontend load markers | Add perf marks for modal open, project selector ready, diff summary ready, diff detail render. | Browser trace confirms markers for all sync flows. | 1 pt |
| P1-T4 | Baseline capture | Record baseline timings before any refactor and commit as artifact in report appendix. | Baseline table exists and is reproducible. | 1 pt |

## Phase 2: Deployment Status Hot-Path Refactor

Assigned Subagent(s): `python-backend-engineer`, `data-layer-expert`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P2-T1 | Single-pass status function | Replace per-deployment `detect_modifications()` calls with a single-pass status computation over already loaded deployments. | No per-item redeclaration/read path remains in status loop. | 3 pts |
| P2-T2 | Remove redundant deployment file reads | Ensure status path does not call `get_deployment()` in inner loops and avoids duplicate TOML reads. | Profile confirms one deployment read per project status request. | 2 pts |
| P2-T3 | Hashing strategy cleanup | Reuse known hashes where possible and hash only when needed for local modification checks. | Hash operations reduced in benchmark scenarios. | 2 pts |
| P2-T4 | Tests for status correctness | Add/adjust tests for synced/modified/outdated status behavior with multiple profiles. | Regression tests pass with unchanged status semantics. | 2 pts |

## Phase 3: Diff API Contract Refactor (Summary First)

Assigned Subagent(s): `backend-architect`, `python-backend-engineer`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P3-T1 | Add query flags | Introduce additive flags (for example `summary_only`, `include_unified_diff`) to diff endpoints. | Existing clients remain compatible with default behavior. | 2 pts |
| P3-T2 | Summary-first execution path | Return counts/status/file metadata without generating all unified diffs on initial load path. | Endpoint can return summary quickly without full unified diff generation. | 3 pts |
| P3-T3 | Lazy file-detail endpoint or mode | Provide path to request unified diff for selected file(s) only. | Frontend can fetch file detail on demand. | 3 pts |
| P3-T4 | Contract tests | Add tests validating both legacy and summary-first modes. | Test suite confirms payload shape and fallback behavior. | 2 pts |

## Phase 4: Upstream Fetch/Check Caching

Assigned Subagent(s): `python-backend-engineer`, `backend-architect`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P4-T1 | Cache key design | Define artifact/collection/version-aware cache keys and TTL for upstream check/fetch results. | Cache key design documented and reviewed. | 1 pt |
| P4-T2 | Implement cache layer | Add short-lived cache around expensive upstream update/fetch operations used by upstream diff routes. | Repeated calls hit cache within TTL and avoid redundant fetch work. | 3 pts |
| P4-T3 | Invalidation hooks | Invalidate cache on sync/deploy/update operations that change relevant state. | Cache invalidation tests cover mutation flows. | 2 pts |
| P4-T4 | Failure-safe behavior | Ensure cache failures degrade gracefully to current behavior. | No regression in correctness when cache unavailable. | 1 pt |

## Phase 5: Frontend Query Orchestration Refactor

Assigned Subagent(s): `frontend-developer`, `react-performance-optimizer`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P5-T1 | Gate fanout deployment queries | In `ArtifactOperationsModal`, defer all-project deployment fanout until `sync` or `deployments` tab is active. | Modal open no longer triggers deployment fanout from unrelated tabs. | 3 pts |
| P5-T2 | Remove duplicate deployment sources | Consolidate Sync tab project/deployment source so it does not fetch both include_deployments and all-project deployment list unnecessarily. | One canonical source drives project selector for sync flow. | 2 pts |
| P5-T3 | Scope-aware diff loading | Load selected comparison scope first; prefetch other scopes in background only after first content render. | Time-to-initial-diff improved and still supports quick scope switching. | 3 pts |
| P5-T4 | Stale/gc tuning for heavy sync queries | Set explicit stale/gc policies for heavy sync queries to reduce unnecessary refetch churn. | Reopen/switch flows reuse cached heavy data within desired TTL. | 1 pt |

## Phase 6: Diff Viewer Rendering Optimization

Assigned Subagent(s): `frontend-developer`, `ui-engineer-enhanced`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P6-T1 | On-demand parse strategy | Stop parsing all file unified diffs up front; parse selected/expanded files only. | CPU usage drops for large diff datasets. | 2 pts |
| P6-T2 | Sidebar stat optimization | Compute additions/deletions lazily or from backend-provided summary where available. | Sidebar remains correct without full pre-parse. | 1 pt |
| P6-T3 | Large-diff UX fallback | Add guardrails for very large diffs (collapsed by default, optional load action). | UI remains responsive under stress fixtures. | 1 pt |

## Phase 7: Validation, Documentation, and Rollout

Assigned Subagent(s): `task-completion-validator`, `documentation-writer`

| Task ID | Task | Description | Acceptance Criteria | Estimate |
|---|---|---|---|---|
| P7-T1 | End-to-end regression suite | Expand sync modal integration tests for optimized query behavior and endpoint modes. | Suite validates no behavior regressions. | 2 pts |
| P7-T2 | Performance verification | Compare P1 baseline vs post-refactor metrics and document deltas. | Reported improvements meet agreed targets. | 2 pts |
| P7-T3 | Rollout checklist | Create deploy/rollback checklist and operational watchpoints. | Release notes include risk controls and fallback instructions. | 1 pt |
| P7-T4 | Documentation updates | Update affected plan/report docs and any relevant developer references. | Documentation reflects new data flow and contracts. | 1 pt |

## 4. Quality Gates

- All existing sync behavior tests pass (no semantic regressions).
- New tests cover:
  - single-pass deployment status computation
  - summary-first diff contracts
  - frontend query gating and lazy detail loading
- Performance gate:
  - reduced sync first-load latency and reduced endpoint runtime in baseline scenarios.
- Compatibility gate:
  - legacy clients continue to work during migration period.

## 5. Risks and Mitigations

| Risk | Level | Mitigation |
|---|---|---|
| Contract drift between old and new diff modes | Medium | Keep additive flags and compatibility tests until full frontend cutover. |
| Cache serving stale upstream state | Medium | Use short TTL + explicit invalidation hooks + fallback to uncached path. |
| Hidden frontend dependency on eager data | Medium | Incremental migration with feature flags and integration tests across tabs. |
| Perf gains not material in real projects | Medium | Baseline instrumentation first, validate each phase against metrics. |

## 6. Success Metrics

- Sync tab first content render latency reduced vs baseline.
- Deployment status endpoint runtime reduced in multi-deployment projects.
- Number of API calls at modal open reduced when sync/deploy tabs are not active.
- No increase in sync correctness defects or user-visible regressions.

## 7. Deliverables

- Optimized backend status and diff pathways.
- Updated frontend query orchestration and viewer rendering flow.
- Regression/performance test coverage.
- Updated architecture report with before/after measurements.

