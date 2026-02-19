---
type: progress
prd: clone-based-artifact-indexing
phase: 3
title: Optimization & Observability
status: completed
started: null
updated: '2026-01-25'
completion: 0
total_tasks: 8
completed_tasks: 8
tasks:
- id: OPT-101
  title: Add OpenTelemetry spans for clone operations
  description: Instrument clone, extraction, storage operations with OpenTelemetry
    tracing spans
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Span for clone operation with duration
  - Span for extraction operation with artifact count
  - Span for database storage operation
  - Strategy attribute on clone span
  - Traces visible in observability tooling
- id: OPT-102
  title: Implement API call counter metric
  description: Track GitHub API calls per scan operation; emit metrics/logs showing
    reduction
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - Counter increments on each GitHub API call
  - Logs show 'X API calls for Y artifacts'
  - Validates hybrid approach is working
  - Metric exposed via existing observability
- id: OPT-103
  title: Add strategy selection logging
  description: Log detailed information about strategy selection decisions
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 30m
  story_points: 1
  acceptance_criteria:
  - Log includes artifact count, computed root, selected strategy
  - Log level is INFO for success, WARNING for fallback
  - Logs are structured (JSON-compatible)
- id: OPT-104
  title: Add performance timing metrics
  description: Add timing metrics for clone, extraction, and total scan duration
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - OPT-101
  model: sonnet
  estimated_time: 1h
  story_points: 2
  acceptance_criteria:
  - clone_duration_ms metric
  - extraction_duration_ms metric
  - total_scan_duration_ms metric
  - Histogram or summary for percentile analysis
- id: OPT-105
  title: Implement clone timeout with fallback
  description: Add configurable timeout for clone operations; graceful fallback to
    API if clone fails/times out
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: opus
  estimated_time: 1.5h
  story_points: 2
  acceptance_criteria:
  - Clone timeout configurable (default 5 minutes)
  - Timeout triggers graceful fallback to API
  - Clone failure (any reason) triggers fallback
  - Warning logged on fallback
  - Application does not crash on timeout
- id: OPT-106
  title: Add git binary availability check
  description: Detect missing git at startup; warn user; allow API-only mode
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 1
  acceptance_criteria:
  - Check runs at application startup
  - Clear warning if git not found
  - Application starts without git (API-only mode)
  - Clone operations gracefully fail with helpful message
- id: OPT-107
  title: Add disk space validation before clone
  description: Check available space before cloning; abort with clear error if insufficient
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 1
  acceptance_criteria:
  - Disk check runs before clone operation
  - Minimum space requirement configurable (default 500MB)
  - Clear error message if space insufficient
  - Falls back to API mode if space check fails
- id: OPT-108
  title: Expose clone_target in MarketplaceSourceResponse
  description: Add clone_target summary fields to API response schema
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  model: sonnet
  estimated_time: 1h
  story_points: 1
  acceptance_criteria:
  - Response includes artifacts_root, artifact_count, indexing_strategy
  - Fields are computed from stored clone_target_json
  - Fields are optional (null if never indexed)
  - Schema updated in skillmeat/api/schemas/marketplace.py
parallelization:
  batch_1:
  - OPT-101
  - OPT-102
  - OPT-103
  - OPT-105
  - OPT-106
  - OPT-107
  - OPT-108
  batch_2:
  - OPT-104
  critical_path:
  - OPT-101
  - OPT-104
  estimated_total_time: 8h
blockers: []
quality_gates:
- Performance benchmark meets <60 second target for 100-artifact repos
- API call count <10 for all scenarios
- All error paths logged with actionable messages
- Graceful fallback to API when clone fails
- Metrics clearly show strategy selection for each scan
- OpenTelemetry instrumentation complete
in_progress_tasks: 0
blocked_tasks: 0
progress: 100
schema_version: 2
doc_type: progress
feature_slug: clone-based-artifact-indexing
---

# Phase 3: Optimization & Observability

**Plan:** `docs/project_plans/implementation_plans/features/clone-based-artifact-indexing-v1.md`
**SPIKE:** `docs/project_plans/SPIKEs/clone-based-artifact-indexing-spike.md`
**Status:** Pending
**Story Points:** 12 total
**Duration:** 2-3 days
**Dependencies:** Phase 2 complete

## Orchestration Quick Reference

**Batch 1** (Parallel - 7h estimated):
- OPT-101 -> `python-backend-engineer` (sonnet) - OpenTelemetry spans
- OPT-102 -> `python-backend-engineer` (sonnet) - API call counter
- OPT-103 -> `python-backend-engineer` (sonnet) - Strategy selection logging
- OPT-105 -> `python-backend-engineer` (opus) - Clone timeout with fallback
- OPT-106 -> `python-backend-engineer` (sonnet) - Git binary check
- OPT-107 -> `python-backend-engineer` (sonnet) - Disk space validation
- OPT-108 -> `python-backend-engineer` (sonnet) - API response schema update

**Batch 2** (After Batch 1 - 1h estimated):
- OPT-104 -> `python-backend-engineer` (sonnet) - Performance timing metrics

### Task Delegation Commands

**Batch 1:**
```
Task("python-backend-engineer", "OPT-101: Add OpenTelemetry spans for clone operations

Add tracing spans to clone, extraction, and storage operations.

Locations:
- _clone_repo_sparse(): span with strategy, pattern_count, duration
- _extract_all_manifests_batch(): span with artifact_count, success_count
- Database commit in _perform_scan(): span with rows_affected

Use existing OpenTelemetry setup from skillmeat.observability module.
Add attributes: strategy, artifact_count, patterns_count, success.

Example:
with tracer.start_as_current_span('clone_repository') as span:
    span.set_attribute('strategy', strategy)
    span.set_attribute('patterns_count', len(patterns))
    # ... clone logic
    span.set_attribute('duration_ms', duration)", model="sonnet")

Task("python-backend-engineer", "OPT-102: Implement API call counter metric

Track GitHub API calls during scan operations.

Add counter that increments on each GitHub API call in:
- get_file_content() calls
- get_repo_tree() calls
- Any other GitHub API operations

At end of scan, log: 'Scan complete: {api_calls} API calls for {artifact_count} artifacts'

This validates the hybrid approach is reducing API usage.", model="sonnet")

Task("python-backend-engineer", "OPT-103: Add strategy selection logging

Add structured logging for strategy selection in _perform_scan().

Log content:
- artifact_count: int
- artifacts_root: Optional[str]
- selected_strategy: str
- patterns_count: int
- reason: str (e.g., 'count < 3', 'count > 20 with common root')

Use INFO level for normal selection, WARNING for fallback to API.
Format as structured log (JSON-compatible dict in message).", model="sonnet")

Task("python-backend-engineer", "OPT-105: Implement clone timeout with fallback

Add timeout handling to _clone_repo_sparse().

Requirements:
1. Configurable timeout via CLONE_TIMEOUT_SECONDS env var (default 300)
2. Use asyncio.wait_for() or subprocess timeout
3. On timeout: log warning, clean up temp dir, raise specific exception
4. In _perform_scan(): catch timeout exception, fall back to API mode
5. On any clone failure: same fallback behavior

Log: 'Clone timed out after {timeout}s, falling back to API mode'")

Task("python-backend-engineer", "OPT-106: Add git binary availability check

Add git availability check at application startup.

Location: skillmeat/api/server.py startup event or similar

Logic:
1. Run 'git --version' via subprocess
2. If succeeds: log git version at INFO
3. If fails: log warning 'Git not found, clone-based indexing disabled'
4. Store result in app state or module-level flag

In _perform_scan(): check flag, skip clone strategies if git unavailable.", model="sonnet")

Task("python-backend-engineer", "OPT-107: Add disk space validation before clone

Add disk space check before clone operations.

Location: _clone_repo_sparse(), before creating temp directory

Logic:
1. Use shutil.disk_usage() on temp directory path
2. Check free space >= MIN_CLONE_DISK_SPACE (env var, default 500MB)
3. If insufficient: raise InsufficientDiskSpaceError
4. In _perform_scan(): catch error, fall back to API mode

Log: 'Insufficient disk space ({available}MB < {required}MB), falling back to API'", model="sonnet")

Task("python-backend-engineer", "OPT-108: Expose clone_target in MarketplaceSourceResponse

Update API response schema to include clone_target summary.

File: skillmeat/api/schemas/marketplace.py

Add to MarketplaceSourceResponse:
- artifacts_root: Optional[str] = None
- artifact_count: Optional[int] = None
- indexing_strategy: Optional[str] = None
- last_indexed_tree_sha: Optional[str] = None

These are computed from clone_target_json in the router when building response.", model="sonnet")
```

**Batch 2:**
```
Task("python-backend-engineer", "OPT-104: Add performance timing metrics

Add timing histograms for scan operations.

Metrics to add:
- skillmeat_clone_duration_seconds (histogram)
- skillmeat_extraction_duration_seconds (histogram)
- skillmeat_scan_total_duration_seconds (histogram)

Labels: strategy, artifact_count_bucket (0-5, 5-20, 20-50, 50+)

Use existing metrics setup from skillmeat.observability.
Expose via /metrics endpoint for Prometheus scraping.

Also log timings at INFO level for easy debugging.", model="sonnet")
```

---

## Success Criteria

- [ ] Performance benchmark meets <60 second target for 100-artifact repos
- [ ] API call count <10 for all scenarios
- [ ] All error paths logged with actionable messages
- [ ] Graceful fallback to API when clone fails
- [ ] Metrics clearly show strategy selection for each scan
- [ ] OpenTelemetry instrumentation complete

---

## Work Log

[Session entries will be added as tasks complete]

---

## Decisions Log

[Architectural decisions will be logged here]

---

## Files Changed

[Will be tracked as implementation progresses]
