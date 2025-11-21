# PRD v2: Artifact Version Sync & Visualization

**Date:** 2025-XX-XX  
**Status:** Draft (targets web UI parity)

## 1) Context
- Current implementation delivers backend/CLI sync (upstream↔collection↔project) but web UI does not surface sync status or operations.
- Users need non-blocking, observable sync with visual diffs to decide merge/update paths.

## 2) Objectives
- Enable web UI to initiate and observe upstream/collection/project sync jobs without blocking navigation.
- Visualize artifact versions across tiers (upstream, collection, project) with diffs.
- Provide guided update/merge actions for upstream→collection, collection↔project, and project→upstream (push-back) flows.

## 3) User Stories
- As a developer, I can see upstream, collection, and project versions side-by-side with diffs before choosing update/merge.
- As a developer, I can start a sync job from the UI, continue working, and get a toast on completion (success/conflict/error).
- As a developer, I can resolve simple conflicts by choosing ours/theirs per file from the UI.
- As a team lead, I can push a project’s changes back to collection (and optionally upstream) with reviewable diffs.

## 4) Scope (MVP)
- Async sync jobs (upstream→collection, collection→project, project→collection) exposed via web API, UI triggers jobs and polls/SSE for status.
- Version visualization: list upstream/collection/project hashes, timestamps, source; show diff for selected pair.
- Update/merge UI: choose strategy (auto/ours/theirs) per artifact; confirm apply.
- Conflict handling (coarse): ours/theirs overwrite from UI; surface conflict file list when merge markers exist.
- Project→Upstream push: allow staged patch creation (zip/tarball) to download or submit via GitHub link (no direct push).

## 5) Out of Scope (v2)
- Fine-grained merge editor in browser (future).
- Multi-user approvals/workflows.
- Direct authenticated upstream push (GitHub PR automation) beyond downloadable patch.

## 6) Requirements
### Functional
- FR1: Start sync job via API/UI for directions: upstream→collection, collection→project, project→collection, project→upstream (patch export).
- FR2: Job status API with progress (% if available), state (queued/running/success/conflict/error), duration.
- FR3: Version view API returning upstream/collection/project metadata and hashes for an artifact.
- FR4: Diff API for artifact across tiers (upstream vs collection, collection vs project, upstream vs project).
- FR5: UI: version panel with selectable pairs and rendered diff (text, fallback to download for binary).
- FR6: UI: update/merge action chooser (auto/ours/theirs) + confirm; send resolve request.
- FR7: Conflict resolution API/UI supporting ours/theirs overwrite; report unresolved files if markers remain.
- FR8: Project→Upstream: API to generate patch bundle from project artifact vs upstream; UI download link.
- FR9: Non-blocking UX: job creation returns job_id; toasts on completion via SSE/poll; page remains navigable.
### Non-Functional
- Latency: job creation <150ms; job status poll <100ms.
- Observability: trace_id on job start/status; metrics for duration, success/conflict rate.
- Reliability: jobs survive process restarts (persisted state or in-memory with graceful degradation); idempotent status queries.
- Security: require auth token; guard project_path inputs; no automatic upstream writes.

## 7) Architecture/Flows
- Job Queue: in-process queue backed by persistent file store (jsonl) or lightweight sqlite; job runner executes sync/service calls.
- APIs:
  - POST `/api/v1/sync/jobs` body: {direction, artifacts?, project_path?, collection?, strategy?, dry_run?}
  - GET `/api/v1/sync/jobs/{id}` -> state/result/conflicts/log excerpt
  - GET `/api/v1/artifacts/{id}/versions` -> upstream/collection/project metadata
  - GET `/api/v1/artifacts/{id}/diff?lhs=collection&rhs=project` -> diff payload/download link
  - POST `/api/v1/sync/resolve` -> overwrite ours/theirs
  - POST `/api/v1/sync/patch` -> generate project→upstream patch bundle
- UI:
  - Artifact detail page: versions panel (upstream/collection/project), diff selector, “Sync/Update” CTA.
  - Toast + notifications panel for job completions; status badge on artifacts.
  - Conflict modal: per-artifact overwrite choice (ours/theirs), list of conflict files.

## 8) Deliverables
- Async job runner + job APIs.
- Version/diff APIs integrated with UI.
- UI views for versions/diffs, job toasts, and update/resolve actions.
- Patch export for project→upstream.
- Tracing/metrics for sync jobs.

## 9) Risks/Mitigations
- Job loss on crash → persist minimal job state; retry on startup.
- Large diffs slow UI → stream or provide download link for >1MB; truncate preview.
- Conflict overwrite risk → double-confirm destructive choices; dry-run default where applicable.

## 10) Success Metrics
- Job start-to-toast median < 3s (excluding long merges).
- UI diff render success > 95% of text artifacts; fall back gracefully for binaries.
- Reduction in “UI hang” reports to near zero post-launch.
