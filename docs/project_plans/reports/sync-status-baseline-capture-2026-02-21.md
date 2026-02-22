---
schema_name: ccdash_document
schema_version: 2
doc_type: report
doc_subtype: performance_baseline_capture
root_kind: project_plans
id: DOC-sync-status-baseline-capture-2026-02-21
title: "Sync Status Baseline Capture - 2026-02-21"
status: draft
category: reports
feature_slug: sync-status-performance-refactor-v1
feature_version: v1
feature_family: sync-status-performance-refactor
priority: high
confidence: 0.90
created: "2026-02-21T00:00:00Z"
updated: "2026-02-21T00:00:00Z"
target_release: 2026-Q2
milestone: Sync Status Performance Refactor
tags:
  - report
  - performance
  - baseline
  - instrumentation
  - sync-status
labels:
  - backend-hotpath
  - frontend-query-orchestration
related_documents:
  - docs/project_plans/reports/sync-status-baseline-scenarios.md
  - docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md
  - docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md
context_files:
  - skillmeat/observability/timing.py
  - skillmeat/web/lib/perf-marks.ts
  - .claude/specs/artifact-structures/ccdash-doc-structure.md
owners:
  - engineering
contributors:
  - backend
  - frontend
  - platform
summary: "Practical measurement template for capturing Sync Status baseline performance metrics before optimization work begins. Records backend endpoint timings, frontend performance marks, and scenario-specific metrics for tracking improvements."
---

# Sync Status Baseline Capture - 2026-02-21

## Purpose

This document is a **measurement capture template** for recording actual baseline performance data during manual testing of Sync Status tab scenarios. Use this to collect concrete timing measurements that establish a baseline before optimization work begins.

Data captured here will inform the optimization targets in the Performance Refactor implementation plan.

## How to Capture

### Setup

1. **Start the development servers**:
   ```bash
   skillmeat web dev
   ```

2. **Filter backend perf logs** (in a separate terminal):
   ```bash
   skillmeat web dev 2>&1 | grep 'perf\.'
   ```
   Or monitor the API logs for `skillmeat.perf` logger entries in your logs dashboard.

3. **Open browser DevTools** → Performance panel:
   - Click "Record" before starting each scenario
   - Filter User Timings by `skillmeat.sync` prefix
   - Stop recording after scenario completes
   - Export trace as `.json` for archival if needed

4. **Clear caches before cold-path tests**:
   - Hard refresh: `Cmd+Shift+R` (macOS) or `Ctrl+Shift+R` (Linux/Windows)
   - Clear browser cache if testing cold-open scenario

### Per-Scenario Execution

For each scenario in `docs/project_plans/reports/sync-status-baseline-scenarios.md`:

1. Start browser DevTools Performance recording
2. Execute the scenario steps
3. Note the wall-clock time when UI becomes interactive
4. Copy backend perf logs from the terminal
5. Stop DevTools recording
6. Record observations in the tables below

---

## Backend Endpoint Timings

Record the `elapsed_ms` values from backend `perf.*` log records. Example log line:

```
[INFO] perf.storage.read_deployments {"elapsed_ms": 45.23, "count": 3, "project_path": "/home/user/proj"}
```

### BASELINE-001: Cold Open (First Time)

**Date/Time**: __________ | **Tester**: __________

| Operation | Scenario | Elapsed (ms) | Count/Note |
|-----------|----------|--------------|-----------|
| `perf.storage.read_deployments` | BASELINE-001 | | |
| `perf.storage.detect_modifications` | BASELINE-001 | | (per deployment) |
| `perf.deployment.list_deployments` | BASELINE-001 | | |
| `perf.deployment.check_deployment_status` | BASELINE-001 | | |
| `perf.router.deploy_artifact.execute` | BASELINE-001 | | |
| `perf.router.list_deployments.fetch` | BASELINE-001 | | |
| `perf.router.list_deployments.check_status` | BASELINE-001 | | |
| `perf.router.check_artifact_upstream.fetch` | BASELINE-001 | | |
| `perf.router.get_artifact_diff.enumerate_files` | BASELINE-001 | | |
| `perf.router.get_artifact_diff.compute` | BASELINE-001 | | |
| `perf.router.get_artifact_source_project_diff.fetch_upstream` | BASELINE-001 | | |
| `perf.router.get_artifact_source_project_diff.enumerate_files` | BASELINE-001 | | |
| `perf.router.get_artifact_source_project_diff.compute` | BASELINE-001 | | |

**Total API calls**: __________ | **Total backend compute time**: __________ ms

---

### BASELINE-002: Tab Switch

**Date/Time**: __________ | **Tester**: __________

| Operation | Scenario | Elapsed (ms) | Count/Note |
|-----------|----------|--------------|-----------|
| `perf.storage.read_deployments` | BASELINE-002 | | |
| `perf.storage.detect_modifications` | BASELINE-002 | | (per deployment) |
| `perf.deployment.list_deployments` | BASELINE-002 | | |
| `perf.deployment.check_deployment_status` | BASELINE-002 | | |
| `perf.router.deploy_artifact.execute` | BASELINE-002 | | |
| `perf.router.list_deployments.fetch` | BASELINE-002 | | |
| `perf.router.list_deployments.check_status` | BASELINE-002 | | |
| `perf.router.check_artifact_upstream.fetch` | BASELINE-002 | | |
| `perf.router.get_artifact_diff.enumerate_files` | BASELINE-002 | | |
| `perf.router.get_artifact_diff.compute` | BASELINE-002 | | |
| `perf.router.get_artifact_source_project_diff.fetch_upstream` | BASELINE-002 | | |
| `perf.router.get_artifact_source_project_diff.enumerate_files` | BASELINE-002 | | |
| `perf.router.get_artifact_source_project_diff.compute` | BASELINE-002 | | |

**Total API calls**: __________ | **Per-switch latency**: __________ ms

---

### BASELINE-003: Modal Reopen (Warm Cache)

**Date/Time**: __________ | **Tester**: __________

| Operation | Scenario | Elapsed (ms) | Count/Note |
|-----------|----------|--------------|-----------|
| `perf.storage.read_deployments` | BASELINE-003 | | |
| `perf.storage.detect_modifications` | BASELINE-003 | | (per deployment) |
| `perf.deployment.list_deployments` | BASELINE-003 | | |
| `perf.deployment.check_deployment_status` | BASELINE-003 | | |
| `perf.router.deploy_artifact.execute` | BASELINE-003 | | |
| `perf.router.list_deployments.fetch` | BASELINE-003 | | |
| `perf.router.list_deployments.check_status` | BASELINE-003 | | |
| `perf.router.check_artifact_upstream.fetch` | BASELINE-003 | | |
| `perf.router.get_artifact_diff.enumerate_files` | BASELINE-003 | | |
| `perf.router.get_artifact_diff.compute` | BASELINE-003 | | |
| `perf.router.get_artifact_source_project_diff.fetch_upstream` | BASELINE-003 | | |
| `perf.router.get_artifact_source_project_diff.enumerate_files` | BASELINE-003 | | |
| `perf.router.get_artifact_source_project_diff.compute` | BASELINE-003 | | |

**Total API calls**: __________ | **Cache hit rate**: __________ %

---

### BASELINE-004: Large Artifact (50+ Files)

**Date/Time**: __________ | **Tester**: __________

**Artifact tested**: ______________________ | **File count**: __________

| Operation | Scenario | Elapsed (ms) | Count/Note |
|-----------|----------|--------------|-----------|
| `perf.storage.read_deployments` | BASELINE-004 | | |
| `perf.storage.detect_modifications` | BASELINE-004 | | (per deployment) |
| `perf.deployment.list_deployments` | BASELINE-004 | | |
| `perf.deployment.check_deployment_status` | BASELINE-004 | | |
| `perf.router.deploy_artifact.execute` | BASELINE-004 | | |
| `perf.router.list_deployments.fetch` | BASELINE-004 | | |
| `perf.router.list_deployments.check_status` | BASELINE-004 | | |
| `perf.router.check_artifact_upstream.fetch` | BASELINE-004 | | |
| `perf.router.get_artifact_diff.enumerate_files` | BASELINE-004 | | |
| `perf.router.get_artifact_diff.compute` | BASELINE-004 | | |
| `perf.router.get_artifact_source_project_diff.fetch_upstream` | BASELINE-004 | | |
| `perf.router.get_artifact_source_project_diff.enumerate_files` | BASELINE-004 | | |
| `perf.router.get_artifact_source_project_diff.compute` | BASELINE-004 | | |

**Total API calls**: __________ | **Response payload size**: __________ KB | **Backend diff compute time**: __________ ms

---

### BASELINE-005: Small Artifact (1-5 Files)

**Date/Time**: __________ | **Tester**: __________

**Artifact tested**: ______________________ | **File count**: __________

| Operation | Scenario | Elapsed (ms) | Count/Note |
|-----------|----------|--------------|-----------|
| `perf.storage.read_deployments` | BASELINE-005 | | |
| `perf.storage.detect_modifications` | BASELINE-005 | | (per deployment) |
| `perf.deployment.list_deployments` | BASELINE-005 | | |
| `perf.deployment.check_deployment_status` | BASELINE-005 | | |
| `perf.router.deploy_artifact.execute` | BASELINE-005 | | |
| `perf.router.list_deployments.fetch` | BASELINE-005 | | |
| `perf.router.list_deployments.check_status` | BASELINE-005 | | |
| `perf.router.check_artifact_upstream.fetch` | BASELINE-005 | | |
| `perf.router.get_artifact_diff.enumerate_files` | BASELINE-005 | | |
| `perf.router.get_artifact_diff.compute` | BASELINE-005 | | |
| `perf.router.get_artifact_source_project_diff.fetch_upstream` | BASELINE-005 | | |
| `perf.router.get_artifact_source_project_diff.enumerate_files` | BASELINE-005 | | |
| `perf.router.get_artifact_source_project_diff.compute` | BASELINE-005 | | |

**Total API calls**: __________ | **Baseline overhead**: __________ ms

---

### BASELINE-006: Multi-Project Deploy (3+ Projects)

**Date/Time**: __________ | **Tester**: __________

**Artifact tested**: ______________________ | **Project count**: __________

| Operation | Scenario | Elapsed (ms) | Count/Note |
|-----------|----------|--------------|-----------|
| `perf.storage.read_deployments` | BASELINE-006 | | |
| `perf.storage.detect_modifications` | BASELINE-006 | | (per deployment) |
| `perf.deployment.list_deployments` | BASELINE-006 | | |
| `perf.deployment.check_deployment_status` | BASELINE-006 | | |
| `perf.router.deploy_artifact.execute` | BASELINE-006 | | |
| `perf.router.list_deployments.fetch` | BASELINE-006 | | |
| `perf.router.list_deployments.check_status` | BASELINE-006 | | |
| `perf.router.check_artifact_upstream.fetch` | BASELINE-006 | | |
| `perf.router.get_artifact_diff.enumerate_files` | BASELINE-006 | | |
| `perf.router.get_artifact_diff.compute` | BASELINE-006 | | |
| `perf.router.get_artifact_source_project_diff.fetch_upstream` | BASELINE-006 | | |
| `perf.router.get_artifact_source_project_diff.enumerate_files` | BASELINE-006 | | |
| `perf.router.get_artifact_source_project_diff.compute` | BASELINE-006 | | |

**Total API calls**: __________ | **Fanout latency (p95)**: __________ ms | **N+1 cost**: __________ ms

---

## Frontend Performance Marks

Record durations from browser DevTools Performance panel. Look for measures prefixed with `skillmeat.sync` in the User Timings lane. Example:

```
Measure: skillmeat.sync.modal.open
Duration: 1234.56 ms
```

### BASELINE-001: Cold Open

**Date/Time**: __________ | **Tester**: __________

| Measure | Duration (ms) | Notes |
|---------|---------------|-------|
| `skillmeat.sync.modal.open` | | |
| `skillmeat.sync.sync-tab.mount` | | |
| `skillmeat.sync.sync-tab.first-data` | | |
| `skillmeat.sync.sync-tab.activate` | | |
| `skillmeat.sync.project-selector.ready` | | |
| `skillmeat.sync.diff-viewer.summary-ready` | | |
| `skillmeat.sync.diff-viewer.render` | | |
| `skillmeat.sync.sync-tab.scope.*` (scope 1) | | |
| `skillmeat.sync.sync-tab.scope.*` (scope 2) | | |
| `skillmeat.sync.sync-tab.scope.*` (scope 3) | | |

**Time to First Content (TTFC)**: __________ ms | **Time to Interactive (TTI)**: __________ ms

---

### BASELINE-002: Tab Switch

**Date/Time**: __________ | **Tester**: __________

| Measure | Switch 1 (ms) | Switch 2 (ms) | Switch 3 (ms) | Average (ms) |
|---------|---------------|---------------|---------------|--------------|
| `skillmeat.sync.sync-tab.scope.*` | | | | |

**Per-switch latency (average)**: __________ ms

---

### BASELINE-003: Modal Reopen

**Date/Time**: __________ | **Tester**: __________

| Measure | Duration (ms) | Notes |
|---------|---------------|-------|
| `skillmeat.sync.modal.open` | | |
| `skillmeat.sync.sync-tab.mount` | | |
| `skillmeat.sync.sync-tab.first-data` | | |
| `skillmeat.sync.sync-tab.activate` | | |

**Time to First Content (TTFC)**: __________ ms | **Time to Interactive (TTI)**: __________ ms

---

### BASELINE-004: Large Artifact (50+ Files)

**Date/Time**: __________ | **Tester**: __________

**Artifact tested**: ______________________ | **File count**: __________

| Measure | Duration (ms) | Notes |
|---------|---------------|-------|
| `skillmeat.sync.modal.open` | | |
| `skillmeat.sync.sync-tab.mount` | | |
| `skillmeat.sync.sync-tab.first-data` | | |
| `skillmeat.sync.diff-viewer.summary-ready` | | |
| `skillmeat.sync.diff-viewer.render` | | |

**Client parse + render time**: __________ ms | **Browser memory increase**: __________ MB

---

### BASELINE-005: Small Artifact (1-5 Files)

**Date/Time**: __________ | **Tester**: __________

**Artifact tested**: ______________________ | **File count**: __________

| Measure | Duration (ms) | Notes |
|---------|---------------|-------|
| `skillmeat.sync.modal.open` | | |
| `skillmeat.sync.sync-tab.mount` | | |
| `skillmeat.sync.sync-tab.first-data` | | |
| `skillmeat.sync.sync-tab.activate` | | |

**Time to First Content (TTFC)**: __________ ms | **Baseline overhead**: __________ ms

---

### BASELINE-006: Multi-Project Deploy (3+ Projects)

**Date/Time**: __________ | **Tester**: __________

**Artifact tested**: ______________________ | **Project count**: __________

| Measure | Duration (ms) | Notes |
|---------|---------------|-------|
| `skillmeat.sync.modal.open` | | |
| `skillmeat.sync.sync-tab.mount` | | |
| `skillmeat.sync.sync-tab.first-data` | | |
| `skillmeat.sync.sync-tab.activate` | | |

**Fanout latency (p95)**: __________ ms

---

## Summary Metrics

### Per-Scenario Overview

| Scenario | TTFC (ms) | TTI (ms) | Total Load (ms) | API Calls | Backend Compute (ms) | Notes |
|----------|-----------|---------|-----------------|-----------|---------------------|-------|
| BASELINE-001 | | | | | | |
| BASELINE-002 | | | | | | |
| BASELINE-003 | | | | | | |
| BASELINE-004 | | | | | | |
| BASELINE-005 | | | | | | |
| BASELINE-006 | | | | | | |

### Key Observations

**Fastest scenario**: __________

**Slowest scenario**: __________

**Largest payload**: __________ KB (scenario: __________)

**Most API calls**: __________ calls (scenario: __________)

**Notable patterns**:
-
-
-

**Bottlenecks identified** (rank by severity):
1.
2.
3.

**Unexpected behavior**:
-

---

## Hardware & Environment

**Test Machine**: _________________________ | **OS**: __________ | **Browser**: __________

**Network conditions**:
- [ ] Uncapped (desktop testing)
- [ ] Fast 3G (mobile simulation)
- [ ] Other: __________

**Backend environment**:
- [ ] Local dev (localhost:8080)
- [ ] Remote: __________

**Collection size**: __________ artifacts | **Project count**: __________ projects

---

## Post-Test Checklist

- [ ] All 6 scenarios executed
- [ ] Backend perf logs captured for each scenario
- [ ] Frontend DevTools traces exported and archived
- [ ] Environment notes recorded (hardware, network, browser cache state)
- [ ] Key bottlenecks documented in observations
- [ ] Data shared with optimization team
- [ ] Link to this capture added to implementation plan tracking

---

## Related Documents

- **Baseline Scenarios**: `docs/project_plans/reports/sync-status-baseline-scenarios.md`
- **Performance Analysis**: `docs/project_plans/reports/sync-status-performance-analysis-2026-02-20.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/refactors/sync-status-performance-refactor-v1.md`
- **Backend Timing Code**: `skillmeat/observability/timing.py`
- **Frontend Performance Marks**: `skillmeat/web/lib/perf-marks.ts`
