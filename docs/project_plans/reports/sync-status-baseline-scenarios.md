---
schema_name: ccdash_document
schema_version: 2
doc_type: report
doc_subtype: performance_baseline
root_kind: project_plans
id: DOC-sync-status-baseline-scenarios
title: "Sync Status Performance Baseline Scenarios"
status: draft
category: reports
feature_slug: sync-status-performance-refactor-v1
feature_version: v1
feature_family: sync-status-performance-refactor
priority: high
confidence: 0.90
created: 2026-02-21T00:00:00Z
updated: 2026-02-21T00:00:00Z
target_release: 2026-Q2
milestone: Sync Status Performance Refactor
tags:
  - report
  - performance
  - baseline
  - testing
  - sync-status
labels:
  - backend-hotpath
  - frontend-query-orchestration
related_documents:
  - docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md
  - docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md
context_files:
  - .claude/specs/artifact-structures/ccdash-doc-structure.md
owners:
  - engineering
contributors:
  - backend
  - frontend
  - platform
summary: "Repeatable performance test scenarios for Sync Status tab baseline establishment before optimization work begins."
---

# Sync Status Performance Baseline Scenarios

## Purpose

This document defines repeatable test scenarios for measuring Sync Status tab performance before and after optimization work. These scenarios establish a baseline that allows tracking performance improvements through the refactor cycle.

## Scenario Matrix

| Scenario | Description | Input Size | API Calls | Expected Query Pattern | Measurement Points |
|----------|-------------|-----------|-----------|----------------------|-------------------|
| **BASELINE-001: Cold Open** | User navigates to artifact detail, opens Sync tab for first time. No prior cache. | 1 artifact, 10 files, 2 projects | 4-5 calls | `list_deployments`, `upstream-diff`, `project-diff` | TTFC, TTI, total load |
| **BASELINE-002: Tab Switch** | User switches between Source↔Collection, Collection↔Project, Source↔Project comparison tabs while modal remains open. | 1 artifact, 10 files, 2 projects | 2 calls per switch | `upstream-diff` or `project-diff` depending on scope | per-switch latency |
| **BASELINE-003: Modal Reopen** | User closes Sync tab modal and reopens it within the same session. Cache warm. | 1 artifact, 10 files, 2 projects | 2-3 calls | Depends on cache state | cache hit rate, TTFC |
| **BASELINE-004: Large Artifact** | Artifact with 50+ files in source, deployed to 2 projects. Simulates real-world skills. | 1 artifact, 50+ files, 2 projects | 4-6 calls | `list_deployments`, `upstream-diff` (large), `project-diff` (large) | backend diff compute, payload size, client parse time |
| **BASELINE-005: Small Artifact** | Minimal artifact with 1-5 files, single deployment. Measures baseline overhead. | 1 artifact, 1-5 files, 1 project | 2-3 calls | `list_deployments`, `upstream-diff`, `project-diff` | TTFC overhead, query amortization |
| **BASELINE-006: Multi-Project Deploy** | Single artifact deployed to 3+ projects. Tests deployment fanout behavior. | 1 artifact, 15 files, 3+ projects | 5-8 calls | `list_deployments` (N+1 for each), per-project `project-diff` | deployment enumeration cost, fanout latency |

## Scenario Details

### BASELINE-001: Cold Open

**Setup**:
1. Sign in; navigate to artifact detail page
2. Modal has not been opened before in this session
3. Click "Sync" tab (or equivalent control)

**Expected Flow**:
- `GET /artifacts/{id}` (if not cached from previous nav)
- `GET /deployments?artifact_id={id}` → triggers `check_deployment_status()` N+1 reads
- `GET /artifacts/{id}/upstream-diff` → executes `fetch_update()` path
- `GET /artifacts/{id}/project-diff?project_id={proj}` → per-project diff computation

**Key Metrics**:
- **Time to First Content (TTFC)**: When first comparison data appears (includes layout shift from spinner → results)
- **Time to Interactive (TTI)**: When UI is interactive (buttons clickable, able to switch tabs)
- **Total Load Time**: Complete query resolution + initial render
- **API Call Count**: Should be 4-5
- **Backend Compute Time**: Sum of deployment + diff operations

**Instrumentation Points**:
- Frontend perf mark: `sync-tab:open-start`, `sync-tab:data-received`, `sync-tab:render-complete`
- Backend logs: `deployments.list_deployments()`, `deployment.check_deployment_status()`, `artifacts.upstream_diff()`
- Browser DevTools: Network waterfall, Core Web Vitals

---

### BASELINE-002: Tab Switch

**Setup**:
1. From BASELINE-001, modal is open with "Source vs Collection" tab active
2. Click tab to switch to "Collection vs Project" or "Source vs Project"
3. Repeat for other combinations

**Expected Flow**:
- Depending on scope:
  - Source→Collection: may use cached upstream-diff, hits `project-diff`
  - Collection→Project: hits `project-diff`
  - Source→Project: may re-query `upstream-diff` (or cache), hits `source-project-diff`

**Key Metrics**:
- **Per-Switch Latency**: Time from click to new comparison rendered
- **Cache Hit Behavior**: Whether upstream/project diffs are cached across scope switches
- **Redundant Query Count**: How many queries are repeated vs reused
- **Network Request Overlap**: If queries run in parallel vs sequential

**Instrumentation Points**:
- Frontend perf mark: `sync-tab:scope-switch-{scope}`, `sync-tab:scope-switch-complete`
- Browser DevTools: Network tab to verify request dedupe

---

### BASELINE-003: Modal Reopen

**Setup**:
1. From BASELINE-001, close the modal
2. Wait 1 second (simulate user doing other work)
3. Reopen artifact detail and click Sync tab again

**Expected Flow**:
- May hit browser cache or query cache if TTL permits
- Behavioral depends on cache invalidation strategy (currently no caching)

**Key Metrics**:
- **TTFC on Reopen**: Faster than cold open if caching is enabled
- **API Call Count**: Should be fewer than cold open if cache is effective
- **Cache Invalidation Events**: Track any mutations that invalidate cached state

**Instrumentation Points**:
- Frontend perf mark: `sync-tab:reopen-cache-state` (log cache hit/miss)
- Backend cache hit/miss logs (if caching is introduced)

---

### BASELINE-004: Large Artifact

**Setup**:
1. Select artifact with 50+ files (e.g., a large skill or composite)
2. Artifact is deployed to 2 projects
3. Open modal, navigate to Sync tab

**Expected Flow**:
- Same as BASELINE-001 but with larger payload
- Backend diff computation scales with file count
- Client-side diff parsing overhead increases

**Key Metrics**:
- **Backend Diff Compute Time**: Should scale linearly or sub-linearly with file count
- **Response Payload Size**: Unified diff blobs for 50+ files can be large (100KB+)
- **Client Parse + Render Time**: Time to parse all diffs and render UI
- **Memory Usage**: Browser memory footprint during diff rendering

**Instrumentation Points**:
- Frontend perf mark: `sync-tab:diff-parse-start`, `sync-tab:diff-parse-complete`
- Backend timing: `artifacts.upstream_diff()` compute duration, response size
- Browser DevTools: Memory profiler, FCP/LCP metrics

---

### BASELINE-005: Small Artifact

**Setup**:
1. Select minimal artifact (1-5 files)
2. Single deployment to one project
3. Open modal, navigate to Sync tab

**Expected Flow**:
- Minimal computation overhead
- Should be fast even without optimization

**Key Metrics**:
- **Baseline Overhead**: Fixed cost of modal/tab interaction regardless of artifact size
- **Query Amortization**: Per-artifact vs per-call costs
- **UI Render Overhead**: Client CPU for simple diffs

**Instrumentation Points**:
- Same as BASELINE-001, but smaller numbers serve as control
- Useful for identifying fixed vs variable costs

---

### BASELINE-006: Multi-Project Deploy

**Setup**:
1. Select artifact deployed to 3 or more projects (e.g., public skill in multiple collections)
2. Open modal, navigate to Sync tab

**Expected Flow**:
- `list_deployments()` returns 3+ entries
- `check_deployment_status()` iterates all 3+, each calling `detect_modifications()` (N+1 reads)
- Project-diff queries run for each deployed project

**Key Metrics**:
- **Deployment Enumeration Cost**: Time to list and check status of all deployments
- **N+1 Impact**: How many extra reads occur for 3 vs 1 deployment
- **Fanout Latency**: Total time for parallel project-diff queries across all projects
- **Deployment Count Scaling**: Should measure 1, 2, 3, 5 deployments to understand scaling

**Instrumentation Points**:
- Backend logs: `check_deployment_status()` call count, per-deployment file I/O duration
- Frontend perf: `sync-tab:deployments-loaded`, parallelization metrics
- Network tab: Concurrent vs sequential queries

---

## Instrumentation Checklist

Use this checklist to verify that all key telemetry points are active during baseline testing.

### Backend Timing Hooks

- [ ] `skillmeat/api/routers/deployments.py::list_deployments()` — log entry/exit with count
- [ ] `skillmeat/core/deployment.py::check_deployment_status()` — log per-deployment iteration and file I/O time
- [ ] `skillmeat/core/artifact.py::detect_modifications()` — log file hash compute duration
- [ ] `skillmeat/api/routers/artifacts.py::upstream_diff()` — log `fetch_update()` path time and response size
- [ ] `skillmeat/api/routers/artifacts.py::project_diff()` — log diff compute and response size
- [ ] `skillmeat/core/artifact.py::fetch_update()` — log GitHub fetch/update check duration
- [ ] Database queries — log query count and duration if using SQLAlchemy ORM

### Frontend Performance Marks

- [ ] `sync-tab:open-start` — when user initiates Sync tab open
- [ ] `sync-tab:modal-mounted` — when modal DOM is ready
- [ ] `sync-tab:data-received` — when initial GraphQL/REST response arrives
- [ ] `sync-tab:render-complete` — when UI fully renders (all components mounted)
- [ ] `sync-tab:scope-switch-{scope}` — when user clicks to switch comparison scope
- [ ] `sync-tab:diff-parse-start` — when client begins parsing unified diffs
- [ ] `sync-tab:diff-parse-complete` — when diff parse completes (before render)
- [ ] `sync-tab:interaction-ready` — when buttons/dropdowns become clickable

### Browser Performance Metrics

- [ ] First Contentful Paint (FCP)
- [ ] Largest Contentful Paint (LCP)
- [ ] Cumulative Layout Shift (CLS)
- [ ] Time to Interactive (TTI)
- [ ] Total Blocking Time (TBT)

### Network Telemetry

- [ ] Request count by endpoint (group by `/deployments`, `/upstream-diff`, `/project-diff`)
- [ ] Request latency histogram (p50, p95, p99)
- [ ] Response payload size histogram
- [ ] Concurrent vs sequential request pattern
- [ ] Cache hit/miss for repeated queries (once caching is added)

### Logging Verification

Before running tests, verify these logs are enabled:

**Python (CLI/API)**:
```python
# In skillmeat/observability/logging.py or router entry:
logger.info(f"deployments.list_deployments() start", extra={"artifact_id": artifact_id})
logger.info(f"deployments.list_deployments() took {elapsed_ms}ms, count={len(deployments)}")

logger.info(f"check_deployment_status() iteration {i}/{count}", extra={"project_path": project_path})
logger.info(f"detect_modifications() hash compute took {elapsed_ms}ms")
```

**TypeScript (Frontend)**:
```typescript
// In React components:
performance.mark('sync-tab:open-start');
// ... async work ...
performance.mark('sync-tab:data-received');
performance.measure('sync-data-fetch', 'sync-tab:open-start', 'sync-tab:data-received');
```

---

## Testing Protocol

### Per-Scenario Checklist

1. **Environment Prep**
   - [ ] Fresh browser session or hard refresh (Cmd+Shift+R)
   - [ ] Clear all caches if testing cold-path
   - [ ] Network throttling set consistently (e.g., Fast 3G for realistic mobile, uncapped for desktop)
   - [ ] Dev tools open on Network tab for call inspection

2. **Test Execution**
   - [ ] Run scenario 3 times, capture all 3 runs
   - [ ] Record browser DevTools metrics (Performance tab)
   - [ ] Note any backend error logs
   - [ ] Verify instrumentation points fired in correct order

3. **Data Collection**
   - [ ] Screenshot network waterfall
   - [ ] Export Performance tab trace (`.json`)
   - [ ] Copy-paste backend logs to text file
   - [ ] Note any anomalies (slow API, high latency, unexpected queries)

4. **Verification**
   - [ ] Confirm expected API calls executed (count, order)
   - [ ] Verify no unexpected queries ran
   - [ ] Check response payload sizes match expectations
   - [ ] Validate UI rendered correctly (no errors, all sections visible)

---

## Baseline Results Template

Create a file `docs/project_plans/reports/sync-status-baseline-results-{date}.md` after running tests with this structure:

```markdown
# Sync Status Baseline Results - {DATE}

| Scenario | TTFC (ms) | TTI (ms) | Total (ms) | API Calls | Notes |
|----------|-----------|---------|-----------|-----------|-------|
| BASELINE-001 | X | X | X | 5 | [observations] |
| BASELINE-002 | X | X | X | 2 | [observations] |
| BASELINE-003 | X | X | X | 3 | [observations] |
| BASELINE-004 | X | X | X | 6 | [observations] |
| BASELINE-005 | X | X | X | 3 | [observations] |
| BASELINE-006 | X | X | X | 8 | [observations] |

## Key Observations

- [Notable patterns across scenarios]
- [Bottlenecks identified]
- [Unexpected behavior]

## Next Steps

[Notes for optimization work]
```

---

## References

- Performance Analysis: `docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md`
- Implementation Plan: `docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md`
- Architecture Context: `skillmeat/api/CLAUDE.md`, `skillmeat/web/CLAUDE.md`
