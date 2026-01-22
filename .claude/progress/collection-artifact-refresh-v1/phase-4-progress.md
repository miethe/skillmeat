---
type: progress
prd: collection-artifact-refresh-v1
phase: 4
title: Advanced Features & Performance Testing
status: completed
progress: 100
total_tasks: 15
completed_tasks: 12
in_progress_tasks: 0
blocked_tasks: 0
deferred_tasks: 4
notes: "BE-412, BE-413, BE-414, BE-415 deferred per user request"
owners:
- python-backend-engineer
contributors: []
created: '2025-01-22'
updated: '2026-01-22'
tasks:
- id: BE-401
  title: Implement check_updates() method
  description: Compare upstream SHAs with artifact.resolved_sha for update detection
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PHASE-3
  model: opus
  estimated_effort: 1.5 pts
  priority: high
  files:
  - skillmeat/core/collection_refresher.py
- id: BE-402
  title: Integrate with SyncManager.check_drift()
  description: Leverage existing three-way merge logic for update detection
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  model: opus
  estimated_effort: 1 pt
  priority: high
  files:
  - skillmeat/core/collection_refresher.py
  - skillmeat/core/sync_manager.py
- id: BE-403
  title: Implement --check-only CLI flag
  description: Detect updates without applying changes
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  model: sonnet
  estimated_effort: 0.75 pts
  priority: medium
  files:
  - skillmeat/cli.py
- id: BE-404
  title: Add API query parameter mode=check
  description: API mode for update detection without applying changes
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  model: sonnet
  estimated_effort: 0.75 pts
  priority: medium
  files:
  - skillmeat/api/routers/collections.py
- id: BE-405
  title: Add field whitelist configuration
  description: Allow users to refresh only specific fields
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PHASE-3
  model: sonnet
  estimated_effort: 0.75 pts
  priority: medium
  files:
  - skillmeat/core/collection_refresher.py
- id: BE-406
  title: Implement field-selective CLI flag
  description: Add --fields flag to CLI for selective field refresh
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-405
  model: sonnet
  estimated_effort: 0.75 pts
  priority: medium
  files:
  - skillmeat/cli.py
- id: BE-407
  title: Add field validation
  description: Validate allowed field names before applying refresh
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-405
  model: sonnet
  estimated_effort: 0.5 pts
  priority: medium
  files:
  - skillmeat/core/collection_refresher.py
- id: BE-408
  title: Implement refresh snapshot creation
  description: Save pre-refresh collection state for rollback
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PHASE-3
  model: sonnet
  estimated_effort: 0.75 pts
  priority: high
  files:
  - skillmeat/core/collection_refresher.py
  - skillmeat/storage/snapshot_manager.py
- id: BE-409
  title: Add --rollback flag to CLI
  description: Restore collection to pre-refresh state
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-408
  model: sonnet
  estimated_effort: 0.75 pts
  priority: high
  files:
  - skillmeat/cli.py
- id: BE-410
  title: Document rollback procedure
  description: User-facing documentation for rollback functionality
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - BE-409
  model: haiku
  estimated_effort: 0.5 pts
  priority: medium
  files:
  - docs/user/collection-refresh.md
- id: BE-411
  title: 'Unit tests: update detection'
  description: Test SHA comparison and drift detection logic
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-402
  model: sonnet
  estimated_effort: 1 pt
  priority: high
  files:
  - tests/core/test_collection_refresher_updates.py
- id: BE-412
  title: 'Unit tests: field selective refresh'
  description: Test field whitelist filtering and validation
  status: deferred
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-407
  model: sonnet
  estimated_effort: 0.75 pts
  priority: high
  files:
  - tests/core/test_collection_refresher_fields.py
- id: BE-413
  title: 'Integration test: end-to-end update flow'
  description: Test detect→decide→refresh→verify flow
  status: deferred
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-402
  - BE-408
  model: opus
  estimated_effort: 1.5 pts
  priority: high
  files:
  - tests/integration/test_collection_refresh_e2e.py
- id: BE-414
  title: 'Performance: large collection refresh'
  description: Benchmark refresh_collection() on large datasets
  status: deferred
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PHASE-3
  model: sonnet
  estimated_effort: 1 pt
  priority: medium
  files:
  - tests/performance/test_refresh_benchmarks.py
- id: BE-415
  title: 'Stress test: concurrent refreshes'
  description: Test thread safety and rate limiting under load
  status: deferred
  assigned_to:
  - python-backend-engineer
  dependencies:
  - PHASE-3
  model: sonnet
  estimated_effort: 1 pt
  priority: medium
  files:
  - tests/stress/test_concurrent_refresh.py
parallelization:
  batch_1:
  - BE-401
  - BE-402
  batch_2:
  - BE-403
  - BE-404
  - BE-405
  - BE-406
  - BE-407
  batch_3:
  - BE-408
  - BE-409
  - BE-410
  batch_4:
  - BE-411
  - BE-412
  - BE-413
  - BE-414
  - BE-415
  critical_path:
  - BE-401
  - BE-402
  - BE-408
  - BE-413
---

# Phase 4: Advanced Features & Performance Testing

**Objective**: Implement update detection, selective field refresh, rollback support, and comprehensive performance/stress testing.

## Overview

Phase 4 completes the collection refresh implementation with advanced features that enable production-grade operation:

- **Update Detection**: Compare upstream SHAs with locally cached values to identify what has changed
- **Selective Refresh**: Allow users to refresh only specific fields rather than entire metadata
- **Rollback Support**: Save pre-refresh state and allow restoration if needed
- **Production Readiness**: Comprehensive testing including performance benchmarks and stress tests under concurrent load

This phase builds on Phases 1-3 core functionality and adds the sophisticated capabilities needed for real-world deployment.

## Orchestration Quick Reference

### Batch 1: Core Update Detection (PARALLEL - Both Opus, Blocking for batch 2-4)

**Effort**: ~2.5 pts | **Duration**: 1-2 days

- **BE-401**: Implement check_updates() method (~1.5 pts, 2h)
  - Compare upstream SHAs with artifact.resolved_sha
  - Return list of changed artifacts
  - Assigned to: python-backend-engineer (Opus)

- **BE-402**: Integrate with SyncManager.check_drift() (~1 pt, 1.5h)
  - Leverage existing three-way merge logic
  - Coordinate with SyncManager for consistency
  - Assigned to: python-backend-engineer (Opus)

### Batch 2: CLI/API Integration + Field Config (PARALLEL - All Sonnet, After batch_1)

**Effort**: ~3.25 pts | **Duration**: 1-2 days

- **BE-403**: Implement --check-only CLI flag (~0.75 pts, 1h)
- **BE-404**: Add API query parameter mode=check (~0.75 pts, 1h)
- **BE-405**: Add field whitelist configuration (~0.75 pts, 1h)
- **BE-406**: Implement field-selective CLI flag (~0.75 pts, 1h)
- **BE-407**: Add field validation (~0.5 pts, 1h)
  - All assigned to: python-backend-engineer (Sonnet)

### Batch 3: Rollback Support (SEQUENTIAL - After batch_1)

**Effort**: ~2 pts | **Duration**: 1 day

- **BE-408**: Implement refresh snapshot creation (~0.75 pts, 1h)
  - Assigned to: python-backend-engineer (Sonnet)

- **BE-409**: Add --rollback flag to CLI (~0.75 pts, 1h)
  - Assigned to: python-backend-engineer (Sonnet)
  - Depends on: BE-408

- **BE-410**: Document rollback procedure (~0.5 pts, 30 min)
  - Assigned to: documentation-writer (Haiku)
  - Depends on: BE-409

### Batch 4: All Tests (PARALLEL - After batch_3, Mixed models)

**Effort**: ~5 pts | **Duration**: 2-3 days

- **BE-411**: Unit tests: update detection (~1 pt, 2h) - Sonnet
- **BE-412**: Unit tests: field selective refresh (~0.75 pts, 1.5h) - Sonnet
- **BE-413**: Integration test: end-to-end flow (~1.5 pts, 3h) - Opus
- **BE-414**: Performance: large collection refresh (~1 pt, 2h) - Sonnet
- **BE-415**: Stress test: concurrent refreshes (~1 pt, 2h) - Sonnet

## Task Details

### Section 4.1: SHA-Based Update Detection

#### BE-401: Implement check_updates() Method

**Purpose**: Core update detection capability

**Responsibilities**:
- Fetch current upstream SHAs for all collection artifacts
- Compare with stored artifact.resolved_sha values
- Generate list of changed artifacts with before/after SHAs
- Handle rate limiting (GitHub API)

**Implementation**:
- Location: `skillmeat/core/collection_refresher.py`
- Method signature: `check_updates(collection: Collection) -> List[UpdatedArtifact]`
- Return type includes: artifact_id, old_sha, new_sha, change_type (updated|moved|deleted)

**Testing Prerequisites**:
- Mock GitHub client with known artifacts
- Test single artifact update detection
- Test multiple artifacts with mixed changes
- Test error handling (404, rate limit, auth errors)

---

#### BE-402: Integrate with SyncManager.check_drift()

**Purpose**: Reuse existing merge logic for update detection

**Responsibilities**:
- Leverage `SyncManager.check_drift()` three-way merge capabilities
- Coordinate local vs upstream vs manifest state
- Use existing conflict resolution patterns
- Maintain consistency with sync workflow

**Implementation**:
- Location: `skillmeat/core/collection_refresher.py` + `skillmeat/core/sync_manager.py`
- Integration pattern: Call `SyncManager.check_drift()` within `check_updates()`
- Coordinate with existing drift detection

**Dependencies**:
- BE-401 must complete first
- Requires understanding of SyncManager architecture

---

### Section 4.2: Selective Field Refresh

#### BE-405: Add Field Whitelist Configuration

**Purpose**: Allow users to refresh only specific metadata fields

**Responsibilities**:
- Define allowed field names (tags, description, category, license, deprecated)
- Implement field filtering in refresh logic
- Support partial updates without full metadata refresh
- Validate field selections

**Implementation**:
- Location: `skillmeat/core/collection_refresher.py`
- Configuration: Add `field_whitelist` parameter to RefreshConfig
- Default behavior: Refresh all fields (backward compatible)

---

#### BE-406 & BE-407: CLI Integration & Validation

**Purpose**: User-facing field selection

**BE-406 Responsibilities**:
- Add `--fields tag,category` CLI flag to `skillmeat collection refresh`
- Parse comma-separated field list
- Validate before passing to refresher
- Display selected fields in output

**BE-407 Responsibilities**:
- Validate field names against allowed set
- Raise clear errors for invalid fields
- Support `--fields help` to list available fields
- Document field meanings in help text

---

### Section 4.3: Rollback Support

#### BE-408: Implement Refresh Snapshot Creation

**Purpose**: Save pre-refresh collection state

**Responsibilities**:
- Create snapshot before refresh begins
- Snapshot location: `.skillmeat/collection/snapshots/refresh-<timestamp>.json`
- Include full artifact metadata and manifest state
- Enable atomic snapshot creation

**Implementation**:
- Location: `skillmeat/core/collection_refresher.py` + `skillmeat/storage/snapshot_manager.py`
- Use atomic operations (temp file + move)
- Compress snapshots for storage efficiency

---

#### BE-409: Add --rollback Flag to CLI

**Purpose**: Restore collection to pre-refresh state

**Responsibilities**:
- Implement `skillmeat collection rollback --snapshot <timestamp>`
- List available snapshots with `skillmeat collection snapshots`
- Restore from snapshot atomically
- Verify restoration success

**Implementation**:
- Location: `skillmeat/cli.py`
- Validation: Ensure snapshot exists before rollback
- Output: Confirm restored artifacts and timestamp

---

#### BE-410: Document Rollback Procedure

**Purpose**: User-facing documentation

**Responsibilities**:
- Document `--rollback` flag usage
- Explain when to use rollback vs. re-fetch
- Provide rollback examples
- Document snapshot retention policy

**Implementation**:
- Location: `docs/user/collection-refresh.md` (new section)
- Include: Screenshots of CLI output, troubleshooting guide

---

### Section 4.4: Advanced Tests & Performance

#### BE-411: Unit Tests - Update Detection

**Purpose**: Verify SHA comparison logic

**Test Coverage**:
- Single artifact update (SHA mismatch)
- Multiple artifacts with mixed changes
- New artifacts (not in local collection)
- Deleted artifacts (in local, removed upstream)
- Error scenarios (GitHub API failures, timeouts)
- Rate limit handling

**Implementation**:
- Location: `tests/core/test_collection_refresher_updates.py`
- Fixtures: Mock collections, mock GitHub responses
- Use pytest parametrization for multiple scenarios

---

#### BE-412: Unit Tests - Field Selective Refresh

**Purpose**: Verify field whitelist filtering

**Test Coverage**:
- Valid field selection (tags, category)
- Invalid field names (error handling)
- Empty field list (default to all)
- Field combination effects on refresh
- Validation error messages

**Implementation**:
- Location: `tests/core/test_collection_refresher_fields.py`
- Use pytest parametrization for field combinations

---

#### BE-413: Integration Test - End-to-End Update Flow

**Purpose**: Verify complete refresh workflow

**Scenario**:
1. Create collection with 3 artifacts
2. Modify upstream (update 1, delete 1, keep 1)
3. Run `check_updates()` → verify detection
4. Run refresh with selective fields → verify changes applied
5. Verify rollback restores original state

**Implementation**:
- Location: `tests/integration/test_collection_refresh_e2e.py`
- Use temporary directories for isolated test collections
- Mock GitHub API responses
- Verify manifest state, lock files, and artifacts

---

#### BE-414: Performance - Large Collection Refresh

**Purpose**: Benchmark refresh performance

**Scenarios**:
- 100 artifacts (small collection)
- 1000 artifacts (medium collection)
- 5000 artifacts (large collection)
- Measure: Time to check_updates(), time to refresh, memory usage

**Implementation**:
- Location: `tests/performance/test_refresh_benchmarks.py`
- Use pytest-benchmark plugin
- Generate synthetic collections with known sizes
- Report: Time/artifact, memory/artifact, throughput

---

#### BE-415: Stress Test - Concurrent Refreshes

**Purpose**: Verify thread safety and rate limiting

**Scenarios**:
- 10 concurrent refresh operations on same collection
- 50 concurrent refresh operations
- Mixed operations (refresh + delete + add)
- Verify: No data corruption, proper rate limiting, clean recovery

**Implementation**:
- Location: `tests/stress/test_concurrent_refresh.py`
- Use `concurrent.futures.ThreadPoolExecutor`
- Add thread-safe assertions for collection state
- Measure: Contention, lock wait times, final consistency

---

## Success Criteria

### Functional Requirements
- [ ] `check_updates()` correctly identifies changed, new, and deleted artifacts
- [ ] `--check-only` flag detects updates without applying changes
- [ ] `mode=check` API parameter works as expected
- [ ] Field selection with `--fields` works correctly
- [ ] `--rollback` restores collection to pre-refresh state
- [ ] All snapshots created before refresh

### Performance Requirements
- [ ] 1000-artifact collection refresh completes in <5 seconds
- [ ] Memory usage stays <100MB for large collections
- [ ] Concurrent refreshes complete without data corruption
- [ ] Rate limiting prevents GitHub API errors

### Test Coverage Requirements
- [ ] Unit test coverage >85% for new code
- [ ] Integration tests cover happy path and error scenarios
- [ ] Performance benchmarks document baseline metrics
- [ ] Stress tests pass with 50 concurrent operations

### Code Quality Requirements
- [ ] All code has type hints
- [ ] Docstrings explain key functions
- [ ] Error handling covers GitHub API failures
- [ ] Logging appropriate for debugging

## Implementation Notes

### Architecture Considerations

1. **Update Detection**: Leverage existing SyncManager rather than reimplementing merge logic
2. **Field Whitelist**: Keep list simple and extendable for future fields
3. **Snapshots**: Use atomic file operations to prevent partial snapshots
4. **Concurrency**: Use file-based locking to prevent simultaneous refreshes
5. **Rate Limiting**: Coordinate with existing GitHub client rate limiter

### Integration Points

- **SyncManager**: Reuse `check_drift()` for three-way merge
- **SnapshotManager**: Existing snapshot storage and retrieval
- **CLI**: Extend existing collection commands
- **API**: Extend collections router with refresh endpoints
- **GitHub Client**: Already wrapped in centralized client

### Error Handling

- GitHub API errors (404, 403, 500)
- Invalid field names (clear error messages)
- Snapshot creation failures (atomic rollback)
- Concurrent refresh conflicts (file locking)

## Files Modified Summary

**New Files**:
- `tests/core/test_collection_refresher_updates.py`
- `tests/core/test_collection_refresher_fields.py`
- `tests/integration/test_collection_refresh_e2e.py`
- `tests/performance/test_refresh_benchmarks.py`
- `tests/stress/test_concurrent_refresh.py`
- `docs/user/collection-refresh.md` (new section)

**Modified Files**:
- `skillmeat/core/collection_refresher.py` (add check_updates, field logic, snapshots)
- `skillmeat/core/sync_manager.py` (integrate with existing drift logic)
- `skillmeat/api/routers/collections.py` (add refresh endpoints with mode=check)
- `skillmeat/cli.py` (add --check-only, --fields, --rollback flags)
- `skillmeat/storage/snapshot_manager.py` (enhance snapshot support)

## Completion Tracking

**Phase Status**: Pending (not yet started)

When complete, this section will be updated with:
- Completion date
- Total time spent per task
- Any blockers or deviations from plan
- Final test coverage metrics
- Performance benchmark results
