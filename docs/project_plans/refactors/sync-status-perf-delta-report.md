---
title: "Sync Status Performance Refactor: Delta Report"
description: "Before/after analysis of performance improvements from phases 1-6 of the sync-status-performance-refactor"
audience: "developers, platform engineers"
tags:
  - sync-status
  - performance
  - delta-report
created: 2026-02-21
updated: 2026-02-21
category: refactors
status: complete
related_documents:
  - docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md
  - docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md
  - docs/project_plans/refactors/sync-status-performance-refactor-rollout.md
  - docs/project_plans/reports/sync-status-baseline-capture-2026-02-21.md
---

# Sync Status Performance Refactor: Delta Report

## Measurement Basis

**Important**: The baseline capture template at
`docs/project_plans/reports/sync-status-baseline-capture-2026-02-21.md` was
created as a manual testing artifact and was not filled in before refactor work
began. No wall-clock benchmark numbers were captured against the original code.

All estimates below are **derived from code analysis** of the before and after
states. Confidence ratings are noted. Runtime verification is the responsibility
of the instrumentation suite already wired in:

- **Backend**: `skillmeat/observability/timing.py` (`PerfTimer`) with 16 timing
  points across deployment and diff routers.
- **Frontend**: `skillmeat/web/lib/perf-marks.ts` with `skillmeat.sync.*`
  measures visible in DevTools User Timings.

---

## Summary Table

| Area | Finding addressed | Mechanism | Estimated reduction | Confidence |
|------|-------------------|-----------|---------------------|------------|
| Deployment status reads | F1: N+1 read/hash per deployment | Single-pass status computation (P1/P2) | N redundant TOML reads + N hash ops eliminated | High |
| Diff payload on first load | F3: eager full diff generation | Summary-first mode `?mode=summary` (P2/P3) | ~60–90% payload reduction for large diffs | High |
| Upstream GitHub API calls | F2: repeated fetch_update() per request | Short-lived upstream fetch cache (P4) | 60–80% duplicate upstream calls eliminated | Medium |
| Modal API fanout on open | F4: useQueries over all projects before sync tab | Fanout gated to deployments tab only (P5.1) | 0 deployment queries on modal open to non-deployments tab | High |
| Duplicate deployment fetch | F5: ProjectSelectorForDiff + modal both fetching | Single canonical deployment source (P5.2) | 1 fetch eliminated per sync tab open | High |
| Inactive scope diff queries | F6: all 3 scopes loaded in parallel on first mount | Scope-aware lazy loading (P5.3) | 2 of 3 diff queries deferred until scope selected | High |
| Repeated query re-fetches | Warm-path re-fetches on modal reopen | staleTime 30s on diff queries (P5.4) | Cache serves data for 30s; 0 API round-trips on reopen | High |
| DiffViewer parse at mount | F7: O(N files) ParsedDiffLine allocation at mount | On-demand parse via parseCacheRef (P6.1) | O(K) where K = files actually viewed, not N total files | High |
| Sidebar stats allocation | F7: per-line ParsedDiffLine objects for stats | Primitive counter scanner via statsCacheRef (P6.2) | Zero ParsedDiffLine[] allocations for non-viewed files | High |
| Large diff render blocking | Large diffs block main thread during parse | >50-file pagination + large file guardrail (P6.3) | Main thread unblocked for initial sidebar render | High |

---

## Per-Phase Detail

### Phase 1–2: Deployment Status Hot-Path

**Before**: `list_deployments()` called `check_deployment_status()`, which
looped over each deployment and invoked `detect_modifications()`. That function
called `get_deployment()` (TOML re-read) and re-hashed artifact content for
each item. For a project with N deployed artifacts: 1 + N file reads, N hash
operations.

**After**: Single-pass computation reads each deployment record once, reuses
loaded data for status checks, and hashes only when needed. The re-read inside
`detect_modifications()` inner loop is eliminated.

**Estimated impact**: Linear reduction in I/O with N. For N=5 deployments the
cost roughly halves; for N=20 the reduction is ~80% of I/O work on the hot
path. Status semantics are preserved (tests added in P2-T4).

---

### Phase 2–3: Summary-First Diff Contract

**Before**: All three diff endpoints (`/diff`, `/upstream-diff`,
`/source-project-diff`) computed unified diffs for every file on every request,
regardless of whether the client displayed them.

**After**: `?mode=summary` returns file-level status and counts without unified
diff content. `?mode=full` (or omitted for legacy compatibility) still returns
the original payload. Frontend uses summary mode on first load.

**Estimated impact**: For an artifact with 50 modified files, the summary
response omits all unified diff text. A conservative estimate: unified diff
content averages 2–5 KB per file, so a 50-file diff is ~100–250 KB under the
old path vs. ~5–10 KB in summary mode. **Payload reduction: ~95% on first
load** for large diffs. Small diffs (1–5 files) benefit less (~60%) because
file metadata still transfers.

---

### Phase 4: Upstream Fetch Cache

**Before**: Every call to the upstream-diff or source-project-diff endpoints
routed through `fetch_update()`, which could invoke GitHub API calls and
artifact workspace operations.

**After**: Short-lived in-process cache keyed by artifact + collection + ref
deduplicates upstream fetches within a configurable TTL. Cache invalidation
hooks fire on deploy and sync mutations to prevent stale data. Failure-safe
wrappers fall through to the uncached path if the cache layer errors.

**Estimated impact**: During typical sync modal usage (open → scope switch →
reopen), the same upstream ref is checked 3–5 times. With the cache, calls 2–N
serve from cache. **60–80% reduction in GitHub API calls** in active sessions.
The downstream effect on GitHub rate limit headroom is proportional. Confidence
is medium because cache TTL and usage frequency depend on session patterns.

---

### Phase 5: Frontend Query Orchestration

**Before**:
- `ArtifactOperationsModal` started `useQueries()` over all projects
  immediately on open, regardless of which tab was active.
- `ProjectSelectorForDiff` fetched with `include_deployments=true` while the
  modal also ran its deployment fanout — two parallel paths fetching the same
  data.
- All three diff scopes (`source-vs-collection`, `collection-vs-project`,
  `source-vs-project`) fired queries as soon as `projectPath` was available,
  independent of the selected scope.

**After**:
- Deployment fanout is gated: queries only execute when the `deployments` tab
  is active (P5.1). Opening to the sync tab — the common path — triggers zero
  deployment list calls.
- Single canonical deployment source for the sync flow eliminates one
  `include_deployments=true` fetch per session (P5.2).
- Only the active scope's diff query fires on mount; the other two are deferred
  until the user switches scope (P5.3).
- `staleTime: 30s`, `gcTime: 5min` on diff queries; `gcTime: 5min` on
  deployment hooks (P5.4). A modal closed and reopened within 30 seconds serves
  entirely from cache with zero API calls.

**Estimated impact**: On a typical sync-modal open to the sync tab with 3
projects in the collection, the old path issued ~3 deployment list queries + 2
diff queries = 5 API calls on mount. The new path issues 1 diff query (active
scope) + 0 deployment queries = 1 API call. **~80% reduction in API calls on
first modal open to sync tab.**

---

### Phase 6: DiffViewer Rendering

**Before**: `DiffViewer` called `parseDiff()` eagerly across all files when
computing sidebar stats. This allocated `ParsedDiffLine[]` for every line of
every file in the diff, even files the user never clicked on.

**After**:
- `parseCacheRef`: Diff is parsed only when a file is selected for viewing.
  Result is memoized in the ref; subsequent views of the same file are free.
- `statsCacheRef`: Sidebar addition/deletion counts use a lightweight line
  scanner that counts `+`/`-` prefix characters and stores only two primitive
  integers per file. No `ParsedDiffLine` objects are allocated until a file is
  opened.
- Large-diff guardrail: Diffs with >50 files paginate the sidebar list. Files
  above a size threshold show a "load" button rather than rendering
  automatically. This prevents a single large diff from blocking the main
  thread during initial render.

**Estimated impact**: For a 100-file diff where the user views 3 files: old
path allocates `ParsedDiffLine[]` for all 100 files; new path allocates for
3 files. **Memory allocation: O(K) viewed files vs O(N) total files.** For
typical usage (viewing 1–5 files from a 50-file diff), this is a ~90%
reduction in parse-related allocations. The sidebar stats path reduces from
per-line object allocation to per-file primitive increment — no heap pressure
for unviewed files at all.

---

## Target Criteria Assessment

The following targets were set in the implementation plan and rollout checklist.
Assessment is based on code analysis; runtime confirmation requires running
the instrumented servers against the baseline scenarios.

| Target | Set in | Assessment | Status |
|--------|--------|------------|--------|
| p95 latency on `/diff` <200ms | Rollout checklist | Summary-first mode removes unified diff generation from the hot path; realistic for cached/small artifacts. Large uncached diffs may still exceed this without streaming. | Likely met for summary mode; verify for full mode |
| Cache hit rate on repeated diffs >60% | Rollout checklist | `staleTime: 30s` guarantees 100% cache hit rate for reopens within 30s. Backend upstream cache targets 60-80% during active sessions. | Met for frontend cache; backend depends on session frequency |
| Sync modal load <500ms cold start | Rollout checklist | Cold-start issues 1 diff query (summary mode, fast) and 0 deployment queries. Bottleneck is now backend diff compute, not query fanout. | Likely met; requires measurement |
| No N+1 deployment status paths | Analysis M1 | Single-pass computation eliminates the inner `get_deployment()` call. | Met |
| Single deployment data source in sync flow | Analysis M3 | P5.1 + P5.2 gate the fanout and eliminate the duplicate fetch. | Met |
| Reduce eager heavy diff queries on initial open | Analysis M2 | 1 query (active scope) vs 2+ previously. | Met |

---

## Runtime Verification Path

No pre-refactor timing numbers were captured. To produce measured before/after
numbers against the new code:

1. Checkout the commit before `f37ab98d` (first P2 commit) for the "before"
   state if a baseline measurement run is needed.
2. Run the baseline scenarios from
   `docs/project_plans/reports/sync-status-baseline-scenarios.md` against both
   revisions.
3. Use `skillmeat web dev 2>&1 | grep 'perf\.'` to read backend PerfTimer logs.
4. Use DevTools Performance panel filtered on `skillmeat.sync` for frontend
   measures.
5. Fill in `docs/project_plans/reports/sync-status-baseline-capture-2026-02-21.md`
   for both states and compute delta.

The instrumentation infrastructure for this measurement is fully in place in
the current codebase.
