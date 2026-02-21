---
schema_name: ccdash_document
schema_version: 2
doc_type: report
doc_subtype: implementation_report
root_kind: project_plans
id: DOC-sync-status-performance-analysis-2026-02-20
title: Sync Status Performance Analysis
status: completed
category: reports
feature_slug: sync-status-performance-refactor-v1
feature_version: v1
feature_family: sync-status-performance-refactor
prd_ref: ""
plan_ref: docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md
related_documents:
  - docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md
  - docs/project_plans/implementation_plans/bug-fixes/sync-status-tab-remediation-v1.md
  - docs/project_plans/reports/artifact-modal-architecture-analysis.md
related_features:
  - sync-status-tab-remediation
linked_sessions: []
linked_tasks: []
owner: codex
owners:
  - codex
contributors:
  - codex
reviewers: []
approvers: []
request_log_ids: []
commit_refs: []
pr_refs: []
priority: high
risk_level: medium
confidence: 0.88
created: 2026-02-20T00:00:00Z
updated: 2026-02-20T00:00:00Z
target_release: 2026-Q2
milestone: Sync Status Performance Refactor
tags:
  - report
  - performance
  - sync-status
  - artifact-modal
labels:
  - backend-hotpath
  - frontend-query-orchestration
files_affected:
  - skillmeat/web/components/manage/artifact-operations-modal.tsx
  - skillmeat/web/components/sync-status/sync-status-tab.tsx
  - skillmeat/web/components/entity/project-selector-for-diff.tsx
  - skillmeat/web/components/entity/diff-viewer.tsx
  - skillmeat/api/routers/artifacts.py
  - skillmeat/api/routers/deployments.py
  - skillmeat/core/deployment.py
  - skillmeat/storage/deployment.py
  - skillmeat/core/artifact.py
  - skillmeat/sources/github.py
context_files:
  - .claude/specs/artifact-structures/ccdash-doc-structure.md
report_period:
  start: 2026-02-20T00:00:00Z
  end: 2026-02-20T00:00:00Z
summary: Sync Status latency is dominated by repeated filesystem hashing, eager heavy diff computation, and broad query fanout across projects.
outcome: success
metrics:
  - id: M1
    name: n_plus_one_deployment_status_paths
    baseline: 0
    actual: 1
    target: 0
    unit: count
  - id: M2
    name: eager_heavy_diff_queries_on_initial_sync_open
    baseline: 0
    actual: 2
    target: 1
    unit: queries
  - id: M3
    name: duplicate_deployment_data_sources_in_sync_flow
    baseline: 0
    actual: 2
    target: 1
    unit: sources
findings:
  - id: F1
    severity: high
    title: Deployment status path performs repeated read+hash loops
    description: list_deployments() calls check_deployment_status(), which calls detect_modifications() per deployment; detect_modifications() re-loads deployment records and re-hashes deployed content repeatedly.
  - id: F2
    severity: high
    title: Upstream diff always executes expensive fetch/update check path
    description: upstream-diff and source-project-diff route through fetch_update(), causing frequent remote version checks and artifact fetch work.
  - id: F3
    severity: high
    title: Diff APIs eagerly compute full file hashes and unified diffs for all files
    description: backend generates full per-file detail for every diff request even when UI initially needs summary-level state.
  - id: F4
    severity: medium
    title: Modal fanout queries deployments for all projects before sync tab is needed
    description: ArtifactOperationsModal starts useQueries() over all projects immediately, creating avoidable API load.
  - id: F5
    severity: medium
    title: Sync flow duplicates deployment data retrieval paths
    description: ProjectSelectorForDiff fetches include_deployments=true while modal also fans out project deployment queries.
  - id: F6
    severity: medium
    title: SyncStatusTab runs multiple heavy queries in parallel on first load
    description: upstream-diff and project-diff are both enabled as soon as projectPath exists, independent of selected scope.
  - id: F7
    severity: low
    title: DiffViewer parses unified diffs for all files preemptively
    description: sidebar stats parse all unified diff blobs up front, increasing client CPU for large diff sets.
decisions:
  - id: D1
    title: Introduce summary-first diff contract
    rationale: Move heavy unified diff generation to on-demand operations and reduce first paint latency.
  - id: D2
    title: Consolidate deployment status computation into single-pass backend path
    rationale: Eliminate repeated deployment file reads and hashing loops.
  - id: D3
    title: Gate heavy modal queries by active tab and selected scope
    rationale: Reduce unnecessary API fanout and improve perceived responsiveness.
action_items:
  - id: A1
    title: Build optimized deployment status path with single deployment read per project
    owner: backend
    due_date: 2026-03-06
    status: pending
  - id: A2
    title: Add summary_only and include_unified_diff flags to diff endpoints
    owner: backend
    due_date: 2026-03-13
    status: pending
  - id: A3
    title: Add short TTL cache around upstream fetch/update check path
    owner: backend
    due_date: 2026-03-13
    status: pending
  - id: A4
    title: Refactor Sync Status frontend query orchestration and prewarm strategy
    owner: frontend
    due_date: 2026-03-20
    status: pending
  - id: A5
    title: Add instrumentation and regression performance tests for sync load path
    owner: platform
    due_date: 2026-03-20
    status: pending
---

# Sync Status Performance Analysis

## Executive Summary

The Sync Status tab is slow due to a combination of backend hot-path inefficiencies and frontend query orchestration patterns. The largest costs come from repeated deployment metadata reads and filesystem hashing, eager full-diff generation, and duplicate/fanout data fetching when opening modal flows.

This report documents concrete bottlenecks and maps them to a full refactor plan in `docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md`.

## Scope and Method

- Reviewed Sync Status path from modal open through query/mutation flow.
- Traced data fetches and compute work across frontend components and backend endpoints.
- Focused on latency contributors in:
  - deployment status retrieval
  - collection/project/upstream diff generation
  - upstream fetch/update checks
  - diff rendering on the client

## Key Findings

## F1 High: deployment status path has N+1 read/hash behavior

- `skillmeat/api/routers/deployments.py` calls both:
  - `list_deployments()` and
  - `check_deployment_status()`
- `check_deployment_status()` iterates deployments and calls `detect_modifications()` for each.
- `detect_modifications()` resolves deployment again via `get_deployment()`, which re-reads deployment TOML, then computes content hash on artifact path.

Impact:
- Repeated file I/O and hashing per deployment.
- Scales poorly with project artifact count.

## F2 High: upstream diff endpoints invoke expensive update/fetch flow

- `upstream-diff` and `source-project-diff` call `artifact_mgr.fetch_update()`.
- `fetch_update()` executes upstream update checks and may fetch artifact content into temp workspaces.
- GitHub path includes clone/fetch/checkout behavior.

Impact:
- High first-load latency and variable runtime depending on remote/network/repo state.

## F3 High: diff endpoints compute full detail eagerly

- `/diff`, `/upstream-diff`, and `/source-project-diff`:
  - enumerate file sets
  - hash files
  - generate unified diffs for modified text files
- No summary-first mode for initial render.

Impact:
- Backend CPU and response payload overhead on initial tab open.

## F4 Medium: modal-level deployment fanout occurs before needed

- `ArtifactOperationsModal` creates `useQueries()` for all registered projects immediately.
- This runs regardless of whether user opens Deployments/Sync tabs.

Impact:
- Avoidable request fanout and backend load at modal open.

## F5 Medium: duplicate deployment data paths in sync view

- `ProjectSelectorForDiff` fetches `/artifacts/{id}?include_deployments=true`.
- Modal already gathers deployment data via per-project `/deploy` fanout.

Impact:
- Redundant API calls and duplicated transformation logic.

## F6 Medium: SyncStatusTab launches multiple heavy queries simultaneously

- `upstream-diff` and `project-diff` queries can run together as soon as project selection is present.
- `source-project-diff` adds additional heavy path when switching scope.

Impact:
- Elevated first-load pressure and slower time-to-interactive.

## F7 Low: DiffViewer parses all unified diffs up front for sidebar stats

- `DiffViewer` pre-parses unified diff blobs for all files in `parsedDiffs`.

Impact:
- Extra client CPU and memory for large diff sets.

## Recommended Refactor Direction

1. Replace N+1 deployment status checks with single-pass computation.
2. Add diff API modes:
   - `summary_only=true`
   - `include_unified_diff=false` by default for initial load
3. Add short-lived cache for upstream fetch/update checks.
4. Gate heavy frontend queries by active tab/scope, and prefetch intentionally.
5. Unify deployment data source in sync flow.
6. Make diff detail parsing on-demand in UI.

## Expected Outcomes

- Faster Sync tab first paint and interaction.
- Lower backend CPU and I/O pressure.
- Reduced API fanout and payload sizes.
- Better scalability with project count and artifact size.

