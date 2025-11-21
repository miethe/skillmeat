---
status: in-progress
date_created: 11-21-2025
author: Codex
primary_model: GPT-5.1-Codex-Max
---

# Implementation Plan: Artifact Version Sync & Visualization (PRD v2)
- Source PRD: `artifact-version-tracking-sync-prd-v2.md`
- Audience: AI agents (optimize for grep/edit; minimal prose)
- Default config (enabled; no feature gating): `SYNC_ASYNC_ENABLED=true`, `SYNC_JOB_STORE=sqlite-fallback-jsonl`, `SYNC_UI_TOASTS=true`, `SYNC_DIFF_PREVIEW_MAX=1MB`, `SYNC_PATCH_EXPORT=tar.gz`

## Backend Plan (keys anchor tracking)
- [BK-JOB-API] FR1/2/9: Add async job queue (in-proc runner, sqlite primary, jsonl fallback); job schema `id,direction,artifact_ids?,project_path,collection,strategy,dry_run,state,pct,started_at,ended_at,trace_id,log_excerpt,conflicts?`. Expose POST `/api/v1/sync/jobs` (create job; return id, trace_id) and GET `/api/v1/sync/jobs/{id}` (state, pct, duration, result summary, conflicts, log excerpt). Persist on enqueue; reload runnable jobs on startup; idempotent status queries; lock per artifact.
- [BK-JOB-RUN] FR1/2/9: Runner consumes queue, wraps existing sync functions (upstream→collection, collection→project, project→collection) with dry-run default. Emit state transitions (queued→running→success/conflict/error), progress ticks from phase hooks (fetch/merge/apply), and collect structured logs. Retry policy: 1 retry on transient IO; mark error on repeat.
- [BK-VERSIONS] FR3: Implement `/api/v1/artifacts/{id}/versions` returning upstream/collection/project metadata (hash, timestamp, source, branch/tag), lineage hints, sync status flag (synced/outdated/diverged/conflict).
- [BK-DIFF] FR4/5: Implement `/api/v1/artifacts/{id}/diff?lhs=collection&rhs=project` (also upstream vs collection, upstream vs project). Text diff inline with size guard; binary or >1MB returns download link. Include summary stats (added/removed lines, files).
- [BK-RESOLVE] FR6/7: POST `/api/v1/sync/resolve` accepts job_id/artifact_id + per-artifact strategy (auto/ours/theirs). For conflict files, overwrite via ours/theirs; validate markers removed; return unresolved list. Reuse job runner to apply resolve tasks.
- [BK-PATCH] FR8: POST `/api/v1/sync/patch` generates tar.gz (or zip) diff bundle project→upstream; returns download URL + hash/size; optional GitHub PR link field (string URL only).
- [BK-OBS] NFR: Inject trace_id into job start/status; metrics for queue depth, duration, success/conflict rate, diff render failures; structured logs keyed by job_id.
- [BK-SEC] NFR: Auth middleware on all endpoints; validate project_path/collection inputs; sandbox temp dirs; deny direct upstream writes; rate-limit patch export.

## UI Plan (keys anchor tracking)
- [UI-VIEW] FR5: Artifact detail panel shows upstream/collection/project cards with hash/timestamp/source; sync status badge; selectable diff pair (U↔C, C↔P, U↔P); diff viewer with truncation notice + download link for large/binary.
- [UI-JOBS] FR1/2/9: “Sync/Update” CTA opens directional chooser; submits job; non-blocking; toast on completion (success/conflict/error) via SSE or poll. Status badge updates from job status.
- [UI-RESOLVE] FR6/7: Conflict modal listing artifacts/files; per-artifact strategy selector (auto/ours/theirs); submit resolve job; show unresolved files if markers remain.
- [UI-PATCH] FR8: “Push upstream” action to request patch export; fetch download link; present copyable URL and optional “Open GitHub link” if provided.
- [UI-OBS] NFR: Show trace_id in debug drawer; loading/progress indicators for jobs/diff fetch; empty/error states.

## Data/Storage Notes
- Job store pref: sqlite db under app data dir; fallback jsonl append w/ compaction. Jobs survive restart; cleanup cron for >30d.
- Temp dirs per job with atomic move on apply; delete after completion.
- Diff payload cache (optional) keyed by job_id + lhs/rhs to reduce recompute for UI polling.

## Integration/Interop Notes
- Reuse existing sync service/merge engine; add async wrappers and event hooks for progress/conflict lists.
- SSE endpoint optional; if infra absent, UI polls `GET /sync/jobs/{id}` every 2s with backoff.
- No feature flags/slow-roll during active dev; single config kill-switch only.

## Testing Plan
- Unit: job enqueue/dequeue/state transitions; status serialization; diff size guards; resolve overwrite logic; patch bundle contents.
- Integration: each direction job (success/conflict/error); UI->API flows; SSE/poll fallback; binary diff fallback; restart recovery of running jobs.
- Perf: job creation <150ms; status poll <100ms; median job start-to-toast <3s for small artifacts.

## Rollout Plan
- Build/enable order: backend job APIs → UI version/diff → UI job flows → resolve → patch export. Enable immediately in dev; kill-switch only if rollback needed; SSE enabled once backend ready.
- Backward compatibility: keep existing CLI sync paths; new async API additive.
- Observability watch: queue depth, conflict/error rates; rollback only via kill-switch config.

## Risks/Mitigations
- Job loss/corruption: persisted store + recovery on boot + idempotent status; alert on failed reload.
- Large diff slowness: size guard + download link; optional streaming.
- Destructive overwrite: double-confirm ours/theirs in UI; dry-run default; audit log entries.
- Security: sanitize paths; limit patch export frequency/size.

## Tracking (update live; link keys above)

### Phase 0: Foundations

| Done | Task | FR | SP | Domain | Risk | Reasoning | Target Model+Tools | Success Criteria | Ref |
|------|------|----|----|--------|------|-----------|--------------------|------------------|-----|
| [ ] | T0-SCHEMA | FR2 | 1 | API/Infra | Low | Low | GPT-5.1-Codex-Max (default tools) | job table/jsonl schema defined/migrated; replay on boot works | BK-JOB-API |
| [ ] | T0-CONFIG | FR9 | 1 | Infra | Low | Low | GPT-4o or GH Copilot for config touch-up | defaults loaded with no gating; kill-switch config documented | Integration/Interop |

### Phase 1: Backend Job System

| Done | Task | FR | SP | Domain | Risk | Reasoning | Target Model+Tools | Success Criteria | Ref |
|------|------|----|----|--------|------|-----------|--------------------|------------------|-----|
| [ ] | T1-QUEUE | FR1/2 | 3 | API/Infra | Medium | Medium | GPT-5.1-Codex-Max, local tools | enqueue + persisted jobs; restart resumes; lock per artifact; retry policy applied | BK-JOB-API, BK-JOB-RUN |
| [ ] | T1-STATUS | FR2/9 | 2 | API | Medium | Medium | GPT-5.1-Codex-Max | GET status returns state/pct/duration/log excerpt/conflicts; latency <100ms | BK-JOB-API |
| [ ] | T1-OBS | NFR | 2 | Observability | Medium | Medium | GPT-5.1-Codex-Max | traces + metrics for queue depth/duration/outcomes; logs keyed by job_id | BK-OBS |

### Phase 2: Sync/Diff APIs

| Done | Task | FR | SP | Domain | Risk | Reasoning | Target Model+Tools | Success Criteria | Ref |
|------|------|----|----|--------|------|-----------|--------------------|------------------|-----|
| [ ] | T2-VERSIONS | FR3 | 2 | API | Medium | Medium | GPT-5.1-Codex-Max | versions endpoint returns metadata + sync status; validated against sample artifacts | BK-VERSIONS |
| [ ] | T2-DIFF | FR4/5 | 3 | API | Medium | Medium | GPT-5.1-Codex-Max | diff endpoint supports U↔C,C↔P,U↔P; size guard + download fallback; summary stats present | BK-DIFF |
| [ ] | T2-RESOLVE | FR6/7 | 3 | API | High | High | GPT-5.1-Codex-Max (optionally Claude Code for merge edge cases) | resolve request overwrites according to strategy; reports unresolved markers; reuses job runner | BK-RESOLVE |
| [ ] | T2-PATCH | FR8 | 2 | API | Medium | Medium | GPT-5.1-Codex-Max | patch export returns tar.gz + hash/size; validated contents vs upstream diff | BK-PATCH |

### Phase 3: UI Enablement

| Done | Task | FR | SP | Domain | Risk | Reasoning | Target Model+Tools | Success Criteria | Ref |
|------|------|----|----|--------|------|-----------|--------------------|------------------|-----|
| [ ] | T3-VIEW | FR5 | 3 | Web | Medium | Medium | GPT-5.1-Codex-Max + GH Copilot for JSX | versions panel + diff selector render hashes/timestamps; truncation notices for large/binary; selectable pairs work | UI-VIEW |
| [ ] | T3-JOBS | FR1/2/9 | 3 | Web | Medium | Medium | GPT-5.1-Codex-Max | async job kickoff non-blocking; toasts on completion via SSE/poll; status badge updates | UI-JOBS |
| [ ] | T3-RESOLVE | FR6/7 | 3 | Web | High | High | GPT-5.1-Codex-Max (consider Claude Code for UX polish) | conflict modal surfaces files; applies per-artifact strategy; shows unresolved list if markers remain | UI-RESOLVE |
| [ ] | T3-PATCH | FR8 | 2 | Web | Medium | Medium | GPT-5.1-Codex-Max | push-upstream action downloads patch; exposes copyable URL/GitHub link; handles errors | UI-PATCH |

### Phase 4: Quality/Perf

| Done | Task | FR | SP | Domain | Risk | Reasoning | Target Model+Tools | Success Criteria | Ref |
|------|------|----|----|--------|------|-----------|--------------------|------------------|-----|
| [ ] | T4-TESTS | FR1-9 | 3 | Test | Medium | Medium | GPT-5.1-Codex-Max (optionally Claude Code for test generation) | unit/integration coverage added for jobs/diff/resolve/patch; restart recovery tested | Testing Plan |
| [ ] | T4-PERF | NFR | 2 | Perf | Medium | Medium | GPT-5.1-Codex-Max | perf checks meet job creation/status targets; diff render fallback validated | Testing Plan |
| [ ] | T4-SEC | NFR | 2 | Security | Medium | Medium | GPT-5.1-Codex-Max | auth/validation on new endpoints; path sanitization; rate limits on patch export | BK-SEC |

### Phase 5: Go-Live (no slow-roll)

| Done | Task | FR | SP | Domain | Risk | Reasoning | Target Model+Tools | Success Criteria | Ref |
|------|------|----|----|--------|------|-----------|--------------------|------------------|-----|
| [ ] | T5-ENABLE | FR9 | 1 | Infra | Low | Low | GPT-5.1-Codex-Max | all features enabled in dev/prod parity; kill-switch documented and tested; monitoring dashboards live | Rollout Plan |
