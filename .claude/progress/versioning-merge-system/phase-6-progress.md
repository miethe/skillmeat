---
type: progress
prd: "versioning-merge-system"
phase: 6
title: "Service Layer - Rollback & Integration"
status: "planning"
started: null
completed: null
overall_progress: 0
completion_estimate: "on-track"
total_tasks: 7
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "ROLL-001"
    description: "Implement intelligent rollback with subsequent change preservation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVCV-006", "MERGE-001"]
    estimated_effort: "5h"
    priority: "critical"

  - id: "ROLL-002"
    description: "Implement rollback conflict detection to prevent bad rollbacks"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ROLL-001"]
    estimated_effort: "3h"
    priority: "high"

  - id: "ROLL-003"
    description: "Implement rollback audit trail metadata with detailed change tracking"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVCV-006"]
    estimated_effort: "2h"
    priority: "high"

  - id: "ROLL-004"
    description: "Ensure atomic rollback operations with transaction safety"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["ROLL-001"]
    estimated_effort: "2h"
    priority: "high"

  - id: "INTEG-001"
    description: "Create VersionMergeService coordinating all merge operations"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["SVCV-001", "MERGE-001"]
    estimated_effort: "3h"
    priority: "critical"

  - id: "INTEG-002"
    description: "Implement sync direction routing for upstream/project/collection merges"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["INTEG-001"]
    estimated_effort: "3h"
    priority: "high"

  - id: "INTEG-003"
    description: "Implement comprehensive error handling for version and merge operations"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["INTEG-001"]
    estimated_effort: "2h"
    priority: "high"

parallelization:
  batch_1: ["ROLL-001", "INTEG-001"]
  batch_2: ["ROLL-002", "ROLL-003", "ROLL-004", "INTEG-002", "INTEG-003"]
  critical_path: ["ROLL-001", "ROLL-002", "ROLL-004"]
  estimated_total_time: "2-3d"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "Rollback preserves subsequent changes while reverting target version"
    status: "pending"
  - id: "SC-2"
    description: "Conflict detection identifies incompatible rollback scenarios"
    status: "pending"
  - id: "SC-3"
    description: "Audit trail records all rollback operations with metadata"
    status: "pending"
  - id: "SC-4"
    description: "All rollback operations are atomic - no partial updates"
    status: "pending"
  - id: "SC-5"
    description: "Error messages are user-friendly and actionable"
    status: "pending"
  - id: "SC-6"
    description: "Integration tests achieve >80% coverage for merge operations"
    status: "pending"
  - id: "SC-7"
    description: "No data loss in any rollback or merge scenario"
    status: "pending"
---

# versioning-merge-system - Phase 6: Service Layer - Rollback & Integration

**Phase**: 6 of 11
**Status**: ⏳ Planning (0% complete)
**Duration**: 2-3 days
**Dependencies**: Phase 4 (Merge Strategy), Phase 5 (Conflict Resolution) must be complete

---

## Phase Overview

Phase 6 implements the service layer that coordinates version and merge operations, with particular focus on intelligent rollback capabilities and comprehensive error handling. This phase bridges the lower-level merge logic (Phase 5) with user-facing operations.

### Core Responsibilities

1. **Intelligent Rollback Service**: Revert to previous versions while preserving subsequent changes
2. **Conflict Detection**: Prevent unsafe rollbacks that would lose data
3. **Audit Trail**: Record all rollback operations for compliance and debugging
4. **Atomic Operations**: Ensure rollback operations never leave data in inconsistent state
5. **VersionMergeService**: Orchestrate all merge/sync operations across scopes (upstream, project, collection)
6. **Sync Direction Routing**: Route merge operations to correct handlers based on sync direction
7. **Error Handling**: User-friendly error messages with remediation guidance

---

## Task Breakdown

### Batch 1 (Parallel): Core Rollback & Integration Service

#### ROLL-001: Intelligent Rollback with Subsequent Change Preservation (5 pts)

**Objective**: Implement rollback logic that reverts a version while preserving changes made after that version.

**Key Responsibilities**:
- Identify target version to rollback to
- Collect all versions created after target version (subsequent changes)
- Generate reverse changeset for target version
- Replay subsequent changes on top of rollback state
- Handle file additions, modifications, and deletions during replay

**Implementation Details**:
- Create `VersionRollbackService` in `core/services/version_rollback.py`
- Implement `rollback(artifact_id, target_version_id)` method
- Track change provenance through version chain
- Use VersionMergeStrategy (from Phase 5) to replay subsequent changes
- Handle edge cases: binary file changes, moved files, deleted files

**Success Metrics**:
- Rollback successfully reverts target version content
- Subsequent changes preserved and applied correctly
- No data loss during rollback
- Performance: rollback <2s for typical artifacts

**Related Files**:
- `core/services/version_rollback.py` (NEW)
- `core/models/version.py` (reference)
- `core/services/merge_strategy.py` (use for replaying changes)

---

#### INTEG-001: VersionMergeService - Orchestration Service (3 pts)

**Objective**: Create service that orchestrates all merge, sync, and version operations with unified API.

**Key Responsibilities**:
- Coordinate merge operations across storage scopes
- Route requests to appropriate merge/sync handlers
- Manage transaction boundaries for atomic operations
- Provide unified error handling and user messaging
- Track merge operation metadata (timestamp, user, source/dest scopes)

**Implementation Details**:
- Create `VersionMergeService` in `core/services/version_merge_service.py`
- Implement factory pattern for merge direction handlers
- Methods: `merge_upstream()`, `merge_project()`, `merge_collection()`
- Support dry-run mode for preview before commit
- Validate merge preconditions (no conflicts, scopes exist, permissions)

**Success Metrics**:
- All merge operations routed through single unified service
- Atomic transaction handling across all operation types
- Dry-run mode accurately predicts actual merge results
- Error handling consistent across all merge types

**Related Files**:
- `core/services/version_merge_service.py` (NEW)
- `core/services/merge_strategy.py` (Phase 5, use for actual merge logic)
- `core/models/merge_operation.py` (NEW, track merge metadata)

---

### Batch 2 (After Batch 1): Extensions & Integration

#### ROLL-002: Rollback Conflict Detection (3 pts)

**Objective**: Detect scenarios where rollback would cause data loss or conflicts.

**Key Responsibilities**:
- Identify conflicts between rollback changeset and subsequent changes
- Detect file moves/renames that would break after rollback
- Identify circular dependencies or cascading changes
- Provide detailed conflict report with resolution options

**Implementation Details**:
- Implement `detect_rollback_conflicts()` in VersionRollbackService
- Use change tracking from Phase 4 (Change Detection)
- Leverage conflict detection from Phase 5 (Conflict Resolution)
- Return conflict report with:
  - Conflicted files/changes
  - Severity level (critical, warning, info)
  - Suggested resolutions
- Prevent rollback if critical conflicts exist

**Success Metrics**:
- All incompatible rollback scenarios detected
- False positives <5% (validated against test set)
- Conflict reports actionable and clear
- Prevents data loss in all test scenarios

**Related Files**:
- `core/services/version_rollback.py` (extend ROLL-001)
- `core/services/conflict_resolver.py` (Phase 5, reference)
- `tests/test_rollback_conflicts.py` (NEW)

---

#### ROLL-003: Rollback Audit Trail & Metadata (2 pts)

**Objective**: Record detailed metadata about every rollback operation for compliance and debugging.

**Key Responsibilities**:
- Create audit entry for each rollback operation
- Record: operator, timestamp, reason, affected versions, outcome
- Link audit entries to the rollback changeset
- Provide audit query interface (list rollbacks, view details)
- Support retention policies for audit data

**Implementation Details**:
- Create `AuditEntry` model in `core/models/audit.py` (if not exists)
- Add fields: `operation_type`, `operator_id`, `reason`, `affected_versions`, `outcome`
- Implement `AuditTrailManager` in `core/services/audit_trail.py`
- Methods: `record_rollback()`, `list_rollbacks()`, `get_rollback_details()`
- Hook audit recording into VersionRollbackService

**Success Metrics**:
- Every rollback operation recorded with complete metadata
- Audit trail queryable and searchable
- Audit data links to actual version files for verification
- Retention policies configurable per artifact

**Related Files**:
- `core/models/audit.py` (NEW or extend existing)
- `core/services/audit_trail.py` (NEW)
- `core/services/version_rollback.py` (integrate audit calls)
- `tests/test_audit_trail.py` (NEW)

---

#### ROLL-004: Atomic Rollback Operations (2 pts)

**Objective**: Ensure rollback operations are atomic - either fully succeed or fully fail, never partially applied.

**Key Responsibilities**:
- Implement transaction wrapper for rollback operations
- Use database transactions for metadata updates
- Use atomic file operations for version storage updates
- Provide rollback recovery if operation fails mid-execution
- Validate consistency before commit

**Implementation Details**:
- Use SQLAlchemy session transaction management
- Implement atomic file operations wrapper (temp → atomic move pattern)
- Create `RollbackTransaction` context manager for safe execution
- Pre-flight validation: check all files exist, no permissions issues
- Post-rollback validation: verify all changes applied correctly

**Success Metrics**:
- All rollback operations atomic (no partial updates observed)
- System recovers cleanly from interrupted rollbacks
- Consistency validation prevents corrupted states
- No data loss in any failure scenario

**Related Files**:
- `core/services/version_rollback.py` (integrate transaction management)
- `core/storage/atomic_operations.py` (reference existing atomic patterns)
- `tests/test_rollback_atomicity.py` (NEW)

---

#### INTEG-002: Sync Direction Routing (3 pts)

**Objective**: Route merge operations to correct handlers based on sync direction.

**Key Responsibilities**:
- Determine merge direction (upstream, project, collection)
- Route to appropriate merge strategy handler
- Handle scope-specific merge logic
- Support bi-directional syncs (upload/download)
- Validate sync preconditions per direction

**Implementation Details**:
- Extend `VersionMergeService` with routing logic
- Implement direction handlers:
  - `UpstreamMergeHandler`: Sync with upstream source
  - `ProjectMergeHandler`: Sync within project scope
  - `CollectionMergeHandler`: Sync within collection scope
- Each handler encapsulates direction-specific logic
- Use strategy pattern for pluggable handlers

**Success Metrics**:
- All sync directions routed to correct handlers
- Direction-specific logic isolated and testable
- Supports future handler additions without service changes
- Error messages indicate why direction is unsupported

**Related Files**:
- `core/services/version_merge_service.py` (extend INTEG-001)
- `core/services/merge_strategy.py` (Phase 5, handlers call this)
- `tests/test_merge_routing.py` (NEW)

---

#### INTEG-003: Comprehensive Error Handling (2 pts)

**Objective**: Implement unified error handling across all version and merge operations.

**Key Responsibilities**:
- Create domain-specific exception hierarchy
- Provide user-friendly error messages with remediation
- Log technical details for debugging without exposing to users
- Support error recovery and retry logic where applicable
- Document all error conditions

**Implementation Details**:
- Create exception hierarchy in `core/exceptions.py`:
  - `VersionOperationError` (base)
  - `RollbackError`, `MergeError`, `ConflictError`, etc.
- Implement error context with: what, why, how-to-fix
- Add structured logging for each error type
- Use exception translation in API layer (map to HTTP status codes)
- Document error scenarios in docstrings

**Success Metrics**:
- All operations have clear error paths
- Error messages helpful for end users (not technical jargon)
- Technical details available in logs for debugging
- Error recovery options provided where applicable

**Related Files**:
- `core/exceptions.py` (extend existing if present, create if needed)
- `core/services/version_rollback.py` (use custom exceptions)
- `core/services/version_merge_service.py` (use custom exceptions)
- `skillmeat/api/routers/artifacts.py` (map to HTTP errors)

---

## Orchestration Quick Reference

### Batch 1 Delegation Commands

**Critical Path**: ROLL-001 and INTEG-001 can run in parallel, then feed into Batch 2.

```
Task("python-backend-engineer", "ROLL-001: Implement intelligent rollback with subsequent change preservation
  File: core/services/version_rollback.py
  Methods: rollback(artifact_id, target_version_id), replay_subsequent_changes()
  Dependencies: core/models/version.py, core/services/merge_strategy.py
  Success: Rollback reverts version, preserves subsequent changes, <2s performance
  Tests: >80% coverage for rollback logic")

Task("python-backend-engineer", "INTEG-001: Create VersionMergeService orchestrating merge operations
  File: core/services/version_merge_service.py
  Methods: merge_upstream(), merge_project(), merge_collection(), with dry-run support
  Dependencies: core/models/version.py, core/services/merge_strategy.py
  Success: Single unified API for all merge operations, atomic transactions, clear error handling
  Tests: Integration tests for merge coordination")
```

### Batch 2 Delegation Commands

Run after Batch 1 completes successfully.

```
Task("python-backend-engineer", "ROLL-002: Implement rollback conflict detection
  File: core/services/version_rollback.py (extend)
  Method: detect_rollback_conflicts() returning conflict report
  Dependencies: ROLL-001, core/services/conflict_resolver.py
  Success: All incompatible rollbacks detected, <5% false positives, clear conflict reports
  Tests: Test conflict detection against known scenarios")

Task("python-backend-engineer", "ROLL-003: Implement rollback audit trail
  Files: core/models/audit.py, core/services/audit_trail.py
  Methods: record_rollback(), list_rollbacks(), get_rollback_details()
  Dependencies: ROLL-001, SVCV-006
  Success: Complete audit trail for all rollback operations, queryable and linked to versions
  Tests: Audit recording and query tests")

Task("python-backend-engineer", "ROLL-004: Ensure atomic rollback operations
  File: core/services/version_rollback.py (integrate)
  Pattern: RollbackTransaction context manager, pre/post-validation
  Dependencies: ROLL-001, core/storage/atomic_operations.py
  Success: All rollbacks atomic, no partial updates, clean recovery from failures
  Tests: Atomicity tests, failure scenario tests")

Task("python-backend-engineer", "INTEG-002: Implement sync direction routing
  File: core/services/version_merge_service.py (extend)
  Handlers: UpstreamMergeHandler, ProjectMergeHandler, CollectionMergeHandler
  Dependencies: INTEG-001, core/services/merge_strategy.py
  Success: All sync directions routed correctly, direction-specific logic isolated
  Tests: Routing tests for each direction")

Task("python-backend-engineer", "INTEG-003: Implement comprehensive error handling
  Files: core/exceptions.py, core/services/version_rollback.py, core/services/version_merge_service.py
  Pattern: Domain-specific exceptions with user-friendly messages and logging
  Dependencies: INTEG-001, ROLL-001
  Success: Clear error paths, user-friendly messages, technical logging, error recovery
  Tests: Error handling tests for all operations")
```

---

## Success Criteria Tracking

| Criterion | Status | Notes |
|-----------|--------|-------|
| Rollback preserves subsequent changes | ⏳ Pending | ROLL-001 |
| Conflict detection prevents bad rollbacks | ⏳ Pending | ROLL-002 |
| Audit trail records all rollbacks | ⏳ Pending | ROLL-003 |
| All operations atomic | ⏳ Pending | ROLL-004 |
| Error messages user-friendly | ⏳ Pending | INTEG-003 |
| Integration tests >80% coverage | ⏳ Pending | All tasks |
| No data loss in any scenario | ⏳ Pending | All tasks |

---

## Active Blockers

_No active blockers at this time. Phase 6 can begin immediately after Phase 4 and Phase 5 are complete._

### Dependencies Status

- **Phase 4 (Merge Strategy)**: Required for ROLL-001, INTEG-002
- **Phase 5 (Conflict Resolution)**: Required for ROLL-002, INTEG-002
- **SVCV-006 (Service Validation)**: Required for ROLL-001, ROLL-003

### Potential Risks

1. **Complex change replay**: Replaying subsequent changes during rollback could introduce subtle bugs
   - Mitigation: Comprehensive test suite with realistic multi-version scenarios

2. **Atomic file operations**: Cross-platform atomic operations can be tricky
   - Mitigation: Leverage existing atomic patterns from Phase 1, thorough testing

3. **Audit trail performance**: Audit recording could slow down operations
   - Mitigation: Async audit logging, batch operations if needed, performance testing

4. **Merge direction complexity**: Multiple sync directions could interact unexpectedly
   - Mitigation: Clear documentation of routing rules, integration tests for each direction

---

## Dependencies

### External Dependencies

- **Phase 4**: Change Detection and Merge Strategy (provides merge logic)
- **Phase 5**: Conflict Resolution (provides conflict detection patterns)
- **SQLAlchemy**: Transaction management for atomic operations
- **Existing Storage Layer**: File operations for versioning

### Internal Integration Points

- **core/models/version.py**: Version entity definitions
- **core/services/merge_strategy.py**: Merge logic for replaying changes
- **core/services/conflict_resolver.py**: Conflict detection patterns
- **core/storage/atomic_operations.py**: Atomic file operation utilities
- **skillmeat/api/routers/artifacts.py**: API endpoint mapping (Phase 10)
- **Phase 10 (API Integration)**: Will expose rollback/merge endpoints

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit | Rollback logic, change replay, conflict detection | 85%+ | ⏳ |
| Unit | Audit trail recording and queries | 90%+ | ⏳ |
| Unit | Error handling and exception hierarchy | 85%+ | ⏳ |
| Integration | Full rollback workflow with multiple versions | Core flows | ⏳ |
| Integration | Merge operation routing and coordination | All directions | ⏳ |
| Atomicity | Rollback operation atomicity and recovery | Failure scenarios | ⏳ |
| E2E | Complete rollback/merge workflows through API | Core scenarios | ⏳ |

**Test Data Sets**:
- Simple rollback: 2-3 versions, single file changes
- Complex rollback: 5+ versions, multiple files, deletes/renames
- Conflict scenarios: Incompatible rollback attempts
- Merge scenarios: Upstream/project/collection syncs with conflicts
- Failure scenarios: Interrupted operations, permission errors

**Performance Targets**:
- Rollback: <2s for typical artifacts (10-50 files)
- Merge routing: <100ms decision time
- Audit logging: <10ms per operation
- Conflict detection: <1s for standard artifacts

---

## Next Phase Dependencies

**Phase 7** (API Integration - Version Operations) depends on Phase 6:
- Will expose `VersionRollbackService` methods via API endpoints
- Will create endpoints for merge operations through `VersionMergeService`
- Will handle API error translation using exception hierarchy

**Phase 8+** (Advanced Features) build on Phase 6:
- Scheduled cleanup/retention uses audit trail
- Analytics and reporting uses merge metadata
- Advanced UI features depend on rollback capabilities

---

## Next Session Agenda

### Immediate Actions (Next Session)

1. [ ] ROLL-001: Implement VersionRollbackService with replay logic
2. [ ] INTEG-001: Create VersionMergeService with basic coordination
3. [ ] Set up test infrastructure for rollback and merge operations

### Critical Milestones

- **Day 1**: ROLL-001 and INTEG-001 complete and tested
- **Day 2**: ROLL-002, ROLL-003, ROLL-004 complete
- **Day 3**: INTEG-002, INTEG-003 complete, full integration testing

### Preparation for Phase 7

- Document rollback API contract for Phase 7 implementation
- Prepare error code/message standards for API layer
- Define merge operation parameters and response formats

### Context for Continuing Agent

**Key Implementation Patterns**:
- Use existing atomic operations patterns from Phase 1
- Leverage merge strategy from Phase 5 for change replay
- Follow transaction management patterns from SQLAlchemy
- Use Rich library for user-friendly error messages

**Critical Design Decisions**:
- Rollback reverses changes incrementally or atomically? → Atomic (no partial states)
- How many versions back can user rollback? → All versions (no limit)
- Can user rollback with active conflicts? → No (ROLL-002 prevents this)
- Should rollback be reversible (i.e., can user undo a rollback)? → Yes (rollback is itself a version)

**Files to Reference**:
- `core/storage/atomic_operations.py` - Atomic file operation patterns
- `core/services/merge_strategy.py` - Merge logic reference
- `core/models/version.py` - Version entity structure
- `core/services/conflict_resolver.py` - Conflict detection patterns

---

## Additional Resources

- **Implementation Plan**: `/docs/project_plans/implementation_plans/enhancements/versioning-merge-system-v1.md`
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Phase 4 Progress**: `.claude/progress/versioning-merge-system/phase-4-progress.md`
- **Phase 5 Progress**: `.claude/progress/versioning-merge-system/phase-5-progress.md`
- **SQLAlchemy Transactions**: Reference in existing API code
- **Rich Error Formatting**: `skillmeat/cli.py` for examples
