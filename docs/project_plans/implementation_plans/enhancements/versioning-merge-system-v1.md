---
title: 'Implementation Plan: Versioning & Merge System'
description: Detailed phased implementation for artifact version history, rollback,
  and three-way merge system
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- phases
- tasks
- versioning
- merge
- sync
created: 2025-11-30
updated: 2025-11-30
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md
- /docs/project_plans/implementation_plans/features/entity-lifecycle-management-v1.md
---
# Implementation Plan: Versioning & Merge System

**Plan ID**: `IMPL-2025-11-30-VERSIONING-MERGE`
**Date**: 2025-11-30
**Author**: Claude Code (orchestration-lead)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md`
- **Entity Lifecycle PRD**: `/docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md`

**Complexity**: Extra Large (XL)
**Total Estimated Effort**: 78 story points
**Target Timeline**: 8 phases over 6-8 weeks

## Executive Summary

This implementation plan delivers a comprehensive version history and three-way merge system for SkillMeat artifacts. The phased approach builds from storage infrastructure upward through merge logic, UI components, and finally integration with existing sync workflows. Key outcomes include per-artifact version snapshots, intelligent three-way merge with automatic conflict detection, rollback capabilities, and clear visual diff indicators showing local vs. upstream changes.

The plan follows a strict bottom-up MeatyPrompts layered architecture sequence:
1. **Database/Storage Layer** - Version snapshot directory structure and metadata TOML schema
2. **Repository Layer** - Version CRUD operations, snapshot management, file operations
3. **Service Layer** - Version comparisons, three-way merge logic, conflict detection
4. **API Layer** - RESTful endpoints for version and merge operations
5. **Frontend UI Layer** - Components for history browsing, merge workflow, conflict resolution
6. **Integration Layer** - Wiring merge into existing sync workflows
7. **Testing & Quality** - Comprehensive test coverage and documentation

---

## Implementation Strategy

### Architecture Sequence

This implementation strictly adheres to the MeatyPrompts layered architecture:

```
Phase 1: Storage Infrastructure (DB/Repository base)
    ↓
Phase 2: Repository Layer (CRUD operations)
    ↓
Phase 3: Service Layer (Merge logic, comparisons)
    ↓
Phase 4: Merge Engine Core (Three-way algorithm, conflict detection)
    ↓
Phase 5: API Layer (RESTful endpoints)
    ↓
Phase 6: Frontend Components (History tab, merge UI)
    ↓
Phase 7: Sync Integration (Wire into existing workflows)
    ↓
Phase 8: Testing & Documentation (Comprehensive coverage)
```

### Parallel Work Opportunities

- **Phase 2 & 3** can begin as soon as Phase 1 design complete (storage structure finalized)
- **Phase 5 API endpoints** can proceed in parallel with Phase 4 once merge core is defined
- **Phase 6 components** can start partial implementation based on API contracts
- **Phase 7 & 8** can proceed in parallel with final backend work

### Critical Path

1. Phase 1 (Storage design) → Phase 2 (Repository layer) → Phase 3 (Service layer) → Phase 4 (Merge engine) → Phase 5 (API layer) → Phase 6 (Frontend) → Phase 7 (Integration)

Phase 8 (Testing) can run parallel with final phases but must complete before release.

---

## Phase Breakdown

### Phase 1: Version Storage Infrastructure

**Duration**: 2-3 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert

This phase establishes the foundational storage structure for version history at both collection and project levels.

#### Phase 1 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| STORE-001 | Version Directory Structure Design | Design and document `versions/` and `latest/` directory layout for artifacts | Directory structure documented in design doc, supports symlinks for latest | 3 pts | data-layer-expert | None |
| STORE-002 | Version Metadata Schema (TOML) | Define `.version.toml` schema with all required fields | Schema includes: id, timestamp, hash, source, files_changed, change_summary, parent_versions | 3 pts | data-layer-expert | STORE-001 |
| STORE-003 | Version ID Generation | Implement deterministic version ID generation (v{n}-{hash}) | IDs are sortable, unique, contain content hash | 2 pts | data-layer-expert | STORE-002 |
| STORE-004 | File Hash Computation | Implement deterministic hashing strategy for artifact files | Uses SHA256, handles different file types, fast computation | 2 pts | data-layer-expert | None |
| STORE-005 | Storage Directory Creation Helper | Build utility to create version snapshot directories | Creates versioned directory from source, handles symlinks | 2 pts | data-layer-expert | STORE-001 |
| STORE-006 | Compression Strategy (Optional) | Design gzip/bzip2 compression option for version storage | Optional compression reduces storage, configurable via feature flag | 2 pts | data-layer-expert | STORE-005 |

**Phase 1 Quality Gates:**
- [ ] Directory structure design reviewed and approved
- [ ] TOML schema is complete with all fields documented
- [ ] Version ID generation tested with multiple artifacts
- [ ] Hash computation deterministic (same artifact = same hash)
- [ ] Directory creation utility handles edge cases (missing files, symlinks)
- [ ] Unit tests for all utilities (>90% coverage)
- [ ] Documentation includes examples of version directory layout

**Phase 1 Deliverables:**
- Version storage architecture document
- `.version.toml` schema definition
- Storage directory structure established
- Version ID generation library
- File hashing utilities

---

### Phase 2: Repository Layer - Version CRUD

**Duration**: 3-5 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: python-backend-engineer, data-layer-expert

Implements the repository layer for version operations: creating, retrieving, listing, and deleting versions. This forms the base for all higher-level operations.

#### Phase 2 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| REPO-001 | VersionRepository Base Class | Create VersionRepository with CRUD interface | Defines contract: create_version, get_version, list_versions, delete_version | 3 pts | python-backend-engineer | STORE-002 |
| REPO-002 | Create Version Operation | Implement create_version: snapshot files, write metadata TOML | Version created with correct timestamp, hash, metadata | 5 pts | python-backend-engineer | REPO-001 |
| REPO-003 | Get Version by ID | Implement get_version to retrieve specific version | Returns version metadata and file listing | 2 pts | python-backend-engineer | REPO-002 |
| REPO-004 | List Versions Operation | Implement list_versions with chronological ordering | Returns all versions sorted by timestamp, supports filtering | 3 pts | python-backend-engineer | REPO-002 |
| REPO-005 | Delete Version Operation | Implement delete_version with safety checks | Can delete old versions, prevents deleting latest | 2 pts | python-backend-engineer | REPO-002 |
| REPO-006 | Get Version Content | Implement method to retrieve full file content of version | Reads files from version directory, handles binary gracefully | 3 pts | python-backend-engineer | REPO-003 |
| REPO-007 | Version Existence Check | Implement has_version helper | Quick check for version existence | 1 pt | python-backend-engineer | REPO-003 |
| REPO-008 | Latest Version Pointer | Implement get_latest_version helper | Returns most recent version | 1 pt | python-backend-engineer | REPO-004 |
| REPO-009 | CollectionVersionRepository Implementation | Implement for `~/.skillmeat/collection/artifacts/{name}/` | Works with collection-level artifact versions | 3 pts | python-backend-engineer | REPO-001 |
| REPO-010 | ProjectVersionRepository Implementation | Implement for `./.claude/artifacts/{name}/` | Works with project-level artifact versions | 3 pts | python-backend-engineer | REPO-001 |
| REPO-011 | Version Metadata Persistence | Test TOML read/write for version metadata | Metadata correctly persists and loads | 2 pts | data-layer-expert | REPO-002 |

**Phase 2 Quality Gates:**
- [ ] All CRUD operations work end-to-end
- [ ] Version metadata persists and loads correctly
- [ ] List operations return chronologically ordered results
- [ ] Delete operation safe (no accidental deletions)
- [ ] File content retrieval handles all file types
- [ ] Unit tests for all operations (>85% coverage)
- [ ] Integration tests for both collection and project repositories
- [ ] Performance: list 100 versions < 100ms

**Phase 2 Deliverables:**
- VersionRepository base class and interfaces
- CollectionVersionRepository implementation
- ProjectVersionRepository implementation
- Version CRUD operations
- Unit and integration tests

---

### Phase 3: Repository Layer - Version Comparisons & Metadata

**Duration**: 2-3 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: python-backend-engineer

Extends the repository layer with comparison and metadata operations needed by higher layers.

#### Phase 3 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| REPO-012 | Get Version Diff (Two-Way) | Implement get_version_diff(v1_id, v2_id) | Returns DiffResult with file-level changes | 3 pts | python-backend-engineer | REPO-006 |
| REPO-013 | Get Files Changed Between Versions | Implement get_files_changed(v1_id, v2_id) | Returns list of changed files | 2 pts | python-backend-engineer | REPO-012 |
| REPO-014 | Version Summary Calculation | Implement calculate_summary for version | Summary: "{N} added, {M} modified, {K} removed" | 2 pts | python-backend-engineer | REPO-012 |
| REPO-015 | Retention Policy Support | Implement version cleanup by count and age | Can keep last N versions or versions from last N days | 3 pts | python-backend-engineer | REPO-005 |
| REPO-016 | Version Rollback Preparation | Implement get_version_for_restore helper | Returns all files needed to restore version | 2 pts | python-backend-engineer | REPO-006 |
| REPO-017 | Version Audit Metadata | Extend .version.toml for audit info | Add: performed_by, merge_parent_versions for audit trail | 2 pts | python-backend-engineer | REPO-002 |

**Phase 3 Quality Gates:**
- [ ] Two-way diffs compute correctly
- [ ] Files changed lists are accurate
- [ ] Summaries human-readable and accurate
- [ ] Retention policies execute correctly
- [ ] Rollback preparation includes all needed files
- [ ] Audit metadata stores correctly
- [ ] Unit tests (>85% coverage)

**Phase 3 Deliverables:**
- Version comparison methods
- Two-way diff generation
- Retention policy implementation
- Audit metadata structures
- Additional unit tests

---

### Phase 4: Service Layer - Version Management Service

**Duration**: 3-4 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: python-backend-engineer

Builds high-level version management service that coordinates repositories and business logic.

#### Phase 4 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SVCV-001 | VersionManagementService Base | Create service orchestrating version operations | Provides clean interface to version operations | 3 pts | python-backend-engineer | REPO-011 |
| SVCV-002 | Capture Version on Sync | Implement capture_version_on_sync | Automatically captures version when artifact synced | 3 pts | python-backend-engineer | SVCV-001 |
| SVCV-003 | Capture Version on Deploy | Implement capture_version_on_deploy | Automatically captures version when deployed | 2 pts | python-backend-engineer | SVCV-001 |
| SVCV-004 | Get Version History | Implement get_version_history with pagination | Returns paginated list of versions | 2 pts | python-backend-engineer | SVCV-001 |
| SVCV-005 | Compare Versions Service | Implement compare_versions high-level method | Uses repository diff, formats results | 2 pts | python-backend-engineer | REPO-012 |
| SVCV-006 | Restore Version Service | Implement restore_version with validation | Restores artifact to prior version, captures rollback event | 3 pts | python-backend-engineer | SVCV-001 |
| SVCV-007 | Clean Old Versions Service | Implement cleanup based on policy | Applies retention policies, logs deletions | 2 pts | python-backend-engineer | SVCV-001 |
| SVCV-008 | Version Diffstat Calculation | Implement diffstat formatting | Returns human-readable stat like "5 added, 2 modified" | 2 pts | python-backend-engineer | REPO-014 |

**Phase 4 Quality Gates:**
- [ ] All service methods have proper error handling
- [ ] Version capture triggered correctly on sync/deploy
- [ ] Rollback preserves data integrity
- [ ] Pagination works with large version counts
- [ ] Cleanup policies execute without errors
- [ ] Service unit tests (>80% coverage)
- [ ] Integration tests with repositories

**Phase 4 Deliverables:**
- VersionManagementService class
- Integration with sync and deploy workflows
- Rollback mechanism
- Cleanup and retention policy implementation

---

### Phase 5: Service Layer - Three-Way Merge Engine

**Duration**: 4-5 days
**Dependencies**: Phase 3 complete (can run partial parallel with Phase 4)
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

Implements the core three-way merge algorithm that detects conflicts and automatically merges non-conflicting changes.

#### Phase 5 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| MERGE-001 | Three-Way Merge Algorithm | Implement three_way_merge(base, ours, theirs) | Returns merged_files, conflicts, non_conflicts | 8 pts | backend-architect | REPO-006 |
| MERGE-002 | File-Level Change Detection | Implement file_changed(base, new) helper | Detects: added, removed, modified, unchanged | 2 pts | backend-architect | MERGE-001 |
| MERGE-003 | Line-Level Merge Attempt | Implement attempt_line_merge for text files | Tries to merge changes, marks lines as conflicted | 5 pts | backend-architect | MERGE-001 |
| MERGE-004 | Conflict Marker Format | Implement conflict marker generation | Format: `<<<<<<< ours`, `=======`, `>>>>>>> theirs` | 2 pts | backend-architect | MERGE-003 |
| MERGE-005 | Three-Way Diff Generation | Implement three_way_diff(base, ours, theirs) | Returns colored diff for visualization | 5 pts | backend-architect | MERGE-001 |
| MERGE-006 | Change Classification | Implement classify_change(base, ours, theirs) | Returns: "upstream_only", "local_only", "conflict", "unchanged" | 3 pts | backend-architect | MERGE-002 |
| MERGE-007 | Merge Simulation | Implement preview_merge without applying | Returns what would merge without changing files | 3 pts | backend-architect | MERGE-001 |
| MERGE-008 | Apply Merge Result | Implement apply_merge to write merged files | Atomically writes all merged files | 3 pts | backend-architect | MERGE-001 |
| MERGE-009 | Merge Algorithm Testing Harness | Create test data sets for merge scenarios | 50+ test cases covering edge cases | 5 pts | backend-architect | MERGE-001 |
| MERGE-010 | Binary File Handling | Implement binary file merge handling | Binary files: accept ours or theirs, no merge | 2 pts | backend-architect | MERGE-001 |
| MERGE-011 | Merge Conflict Statistics | Implement merge_stats(merge_result) | Returns counts: auto_merged, conflicts, unchanged | 2 pts | backend-architect | MERGE-001 |

**Phase 5 Quality Gates:**
- [ ] Three-way merge algorithm handles all cases
- [ ] Line-level merge works for text files
- [ ] Conflict markers clearly formatted
- [ ] Three-way diff produces correct output
- [ ] Merge preview accurate
- [ ] Binary files handled gracefully
- [ ] Atomic merge application (no partial writes)
- [ ] Unit tests with 50+ scenarios (>90% coverage)
- [ ] Performance: 10MB artifact merge < 2s

**Phase 5 Deliverables:**
- MergeEngine class with three-way merge algorithm
- Conflict detection and classification
- Merge preview and application
- Comprehensive test cases

---

### Phase 6: Service Layer - Rollback & Integration

**Duration**: 2-3 days
**Dependencies**: Phase 4 complete, Phase 5 complete
**Assigned Subagent(s)**: python-backend-engineer

Implements rollback with preservation of subsequent changes and integrates version/merge operations.

#### Phase 6 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| ROLL-001 | Intelligent Rollback Logic | Implement rollback that preserves subsequent non-conflicting changes | Rolls back to version, preserves later changes | 5 pts | python-backend-engineer | SVCV-006, MERGE-001 |
| ROLL-002 | Rollback Conflict Detection | Detect if rollback conflicts with later changes | Warns if rollback would conflict | 3 pts | python-backend-engineer | ROLL-001 |
| ROLL-003 | Rollback Audit Trail | Implement rollback_metadata tracking | Records who rolled back, when, to which version | 2 pts | python-backend-engineer | SVCV-006 |
| ROLL-004 | Atomic Rollback Operation | Ensure rollback all-or-nothing | Transaction-like semantics | 2 pts | python-backend-engineer | ROLL-001 |
| INTEG-001 | Merge Service Orchestration | Create VersionMergeService coordinating merge operations | Coordinates version and merge logic | 3 pts | python-backend-engineer | SVCV-001, MERGE-001 |
| INTEG-002 | Sync Direction Routing | Implement routing for upstream/project/collection merges | Correctly identifies which versions to compare | 3 pts | python-backend-engineer | INTEG-001 |
| INTEG-003 | Error Handling & Recovery | Comprehensive error handling for version/merge ops | All operations have proper error handling | 2 pts | python-backend-engineer | INTEG-001 |

**Phase 6 Quality Gates:**
- [ ] Rollback works with subsequent changes
- [ ] Conflict detection prevents bad rollbacks
- [ ] Audit trail records all rollbacks
- [ ] All operations atomic
- [ ] Error messages user-friendly
- [ ] Integration tests (>80% coverage)
- [ ] No data loss in any scenario

**Phase 6 Deliverables:**
- Rollback service with preservation logic
- VersionMergeService orchestration
- Error handling framework
- Integration tests

---

### Phase 7: API Layer - Version & Merge Endpoints

**Duration**: 3-4 days
**Dependencies**: Phase 4, Phase 5, Phase 6 complete
**Assigned Subagent(s)**: python-backend-engineer, backend-architect

Exposes version and merge operations through REST API endpoints following OpenAPI standards.

#### Phase 7 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| APIVM-001 | GET /api/v1/artifacts/{id}/versions | List version history | Returns paginated list of versions with metadata | 3 pts | python-backend-engineer | SVCV-004 |
| APIVM-002 | GET /api/v1/artifacts/{id}/versions/{version_id} | Get version details | Returns version metadata and file listing | 2 pts | python-backend-engineer | REPO-003 |
| APIVM-003 | GET /api/v1/artifacts/{id}/versions/{version_id}/files | Get version files | Returns artifact content at that version | 2 pts | python-backend-engineer | REPO-006 |
| APIVM-004 | GET /api/v1/artifacts/{id}/versions/{v1}/diff/{v2} | Diff two versions | Returns DiffResult with file changes | 2 pts | python-backend-engineer | REPO-012 |
| APIVM-005 | POST /api/v1/artifacts/{id}/versions/{version_id}/restore | Restore to version | Confirms and restores to prior version | 3 pts | python-backend-engineer | SVCV-006 |
| APIVM-006 | POST /api/v1/artifacts/{id}/merge/preview | Preview merge | Returns what would merge without applying | 3 pts | python-backend-engineer | MERGE-007 |
| APIVM-007 | POST /api/v1/artifacts/{id}/merge/analyze | Analyze merge (three-way) | Returns auto_merged, conflicts, change classification | 3 pts | backend-architect | MERGE-001, MERGE-006 |
| APIVM-008 | POST /api/v1/artifacts/{id}/merge/apply | Apply merge | Applies merge with conflict resolutions | 3 pts | python-backend-engineer | MERGE-008 |
| APIVM-009 | Schema Definitions | Define request/response schemas | Schemas for all endpoints in OpenAPI | 3 pts | python-backend-engineer | APIVM-001 |
| APIVM-010 | Error Response Standardization | Ensure consistent error responses | All errors follow ErrorResponse format | 2 pts | python-backend-engineer | APIVM-001 |
| APIVM-011 | OpenAPI Documentation Generation | Generate OpenAPI spec and Swagger UI | OpenAPI spec complete and accurate | 2 pts | python-backend-engineer | APIVM-009 |
| APIVM-012 | TypeScript SDK Regeneration | Regenerate SDK from OpenAPI | SDK includes all new endpoints | 2 pts | python-backend-engineer | APIVM-011 |
| APIVM-013 | API Integration Tests | Test all endpoints end-to-end | All endpoints tested with real data | 5 pts | backend-architect | APIVM-012 |

**Phase 7 Quality Gates:**
- [ ] All endpoints return correct responses
- [ ] OpenAPI schema complete and valid
- [ ] Pagination works correctly
- [ ] Error handling returns proper codes and messages
- [ ] SDK generates without errors and compiles
- [ ] Integration tests >85% coverage
- [ ] Performance: version list endpoint < 100ms
- [ ] Performance: merge preview < 2s for 10MB artifact

**Phase 7 Deliverables:**
- REST API endpoints for version management
- REST API endpoints for merge operations
- OpenAPI schema and documentation
- TypeScript SDK with new endpoints
- Integration tests

---

### Phase 8: Frontend - History Tab & Version Browsing

**Duration**: 4-5 days
**Dependencies**: Phase 7 complete (SDK available)
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

Implements History tab with version timeline, content viewing, and comparison UI.

#### Phase 8 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| HIST-001 | VersionTimeline Component | Build chronological version list | Shows: version ID, timestamp, source, summary | 5 pts | ui-engineer-enhanced | APIVM-001 |
| HIST-002 | Version Metadata Display | Show metadata for each version | Displays: hash, files changed, change summary | 3 pts | ui-engineer-enhanced | HIST-001 |
| HIST-003 | Version Content Viewer | Build read-only file viewer for version | Shows files as they existed in that version | 5 pts | ui-engineer-enhanced | APIVM-003 |
| HIST-004 | Version Comparison View | Build side-by-side diff viewer | Shows two versions with highlighted changes | 5 pts | ui-engineer-enhanced | APIVM-004 |
| HIST-005 | Compare Button/UI | Add "Compare" button to version timeline | Allows selecting two versions to compare | 2 pts | frontend-developer | HIST-001 |
| HIST-006 | Restore Button & Confirmation | Add "Restore" button with confirmation dialog | Dialog warns about implications, allows restore | 3 pts | frontend-developer | HIST-001 |
| HIST-007 | History Tab Integration | Wire History tab into modal detail view | History tab shows in artifact detail modal | 3 pts | frontend-developer | HIST-002 |
| HIST-008 | Loading & Error States | Handle loading and error states gracefully | Shows spinners, error messages | 2 pts | frontend-developer | HIST-001 |
| HIST-009 | Pagination & Virtualization | Handle large version histories efficiently | Pagination or virtual scrolling for 100+ versions | 3 pts | frontend-developer | HIST-001 |
| HIST-010 | Keyboard Navigation | Full keyboard support in history UI | Tab, arrow keys, Enter work | 2 pts | ui-engineer-enhanced | HIST-001 |

**Phase 8 Quality Gates:**
- [ ] History tab displays correctly in modal
- [ ] Version timeline shows all versions
- [ ] Content viewer renders all file types
- [ ] Comparison shows correct diffs
- [ ] Restore dialog works with confirmation
- [ ] Handles 100+ versions efficiently
- [ ] Keyboard navigation functional
- [ ] Component tests >80% coverage
- [ ] Responsive on mobile/tablet

**Phase 8 Deliverables:**
- VersionTimeline component
- VersionContentViewer component
- VersionComparisonView component
- History tab integration
- Component tests and Storybook stories

---

### Phase 9: Frontend - Merge UI & Conflict Resolution

**Duration**: 4-5 days
**Dependencies**: Phase 7 complete, Phase 8 complete
**Assigned Subagent(s)**: ui-engineer-enhanced, frontend-developer

Implements merge workflow UI with three-way diff visualization and conflict resolution interface.

#### Phase 9 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| MERGE-UI-001 | ColoredDiffViewer Component | Build three-way diff with color coding | Green=upstream, Blue=local, Red=conflict, Yellow=removed | 8 pts | ui-engineer-enhanced | APIVM-007 |
| MERGE-UI-002 | Change Type Classification Display | Show labels for change types | Each change labeled: "local change", "upstream update", "conflict" | 2 pts | frontend-developer | MERGE-UI-001 |
| MERGE-UI-003 | MergePreview Component | Build merge preview before apply | Shows what would merge + stats | 5 pts | ui-engineer-enhanced | APIVM-006 |
| MERGE-UI-004 | Merge Statistics Display | Show merge stats clearly | "3 auto-merged, 1 conflict, 12 unchanged" | 2 pts | frontend-developer | MERGE-UI-001 |
| MERGE-UI-005 | ConflictResolver Integration | Reuse existing conflict-resolver component | Wire for merge conflicts | 3 pts | frontend-developer | APIVM-008 |
| MERGE-UI-006 | Conflict Strategy Selection | Allow ours/theirs/manual per file | Radio buttons or buttons for strategy | 3 pts | ui-engineer-enhanced | MERGE-UI-005 |
| MERGE-UI-007 | MergeWorkflow Component | Build step-by-step merge workflow | Steps: Preview → Conflicts → Confirm → Apply | 5 pts | ui-engineer-enhanced | MERGE-UI-003 |
| MERGE-UI-008 | Apply Merge Button | Wire merge apply endpoint | Confirms and applies merge | 2 pts | frontend-developer | MERGE-UI-007 |
| MERGE-UI-009 | Merge Result Notification | Show success/failure after merge | Toast with merge stats | 2 pts | frontend-developer | MERGE-UI-008 |
| MERGE-UI-010 | Merge History in Version Tab | Track merge operations in version history | Shows merge as version entry | 2 pts | frontend-developer | MERGE-UI-008 |

**Phase 9 Quality Gates:**
- [ ] Diff viewer displays three-way diffs correctly
- [ ] Color coding clearly distinguishes change types
- [ ] Merge preview accurately shows what will merge
- [ ] Conflict resolver works for all conflict types
- [ ] Workflow guides users through merge steps
- [ ] Apply merge works end-to-end
- [ ] Component tests >80% coverage
- [ ] Accessibility: all interactive elements keyboard accessible
- [ ] Accessibility: color not sole indicator of change type

**Phase 9 Deliverables:**
- ColoredDiffViewer component
- MergePreview component
- MergeWorkflow component
- Conflict resolver integration
- Component tests and Storybook stories

---

### Phase 10: Sync Workflow Integration

**Duration**: 3-4 days
**Dependencies**: Phase 7, Phase 9 complete
**Assigned Subagent(s)**: python-backend-engineer, ui-engineer-enhanced

Integrates version and merge operations into existing sync workflows for all sync directions.

#### Phase 10 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| SYNC-INT-001 | Upstream Sync (Source→Collection) | Wire three-way merge to sync from source | Sync detects changes, shows merge preview | 4 pts | python-backend-engineer | MERGE-UI-007 |
| SYNC-INT-002 | Deploy Sync (Collection→Project) | Wire three-way merge to deploy | Deploy shows merge preview if project diverged | 4 pts | python-backend-engineer | MERGE-UI-007 |
| SYNC-INT-003 | Pull Sync (Project→Collection) | Wire three-way merge to pull local changes | Pull shows merge preview if collection diverged | 4 pts | python-backend-engineer | MERGE-UI-007 |
| SYNC-INT-004 | Sync Status Tab Enhancement | Update SyncStatusTab with merge display | Shows merge stats, colored diff | 4 pts | ui-engineer-enhanced | MERGE-UI-001 |
| SYNC-INT-005 | Sync Dialog Flow Redesign | Update sync dialogs to show merge workflow | Single unified merge workflow for all directions | 3 pts | ui-engineer-enhanced | SYNC-INT-004 |
| SYNC-INT-006 | Auto-Capture Version on Sync | Automatic version capture during sync | Version created when sync completes | 2 pts | python-backend-engineer | SVCV-002 |
| SYNC-INT-007 | Merge Conflict Error Handling | Proper error handling if merge fails | User-friendly error messages | 2 pts | python-backend-engineer | MERGE-UI-009 |
| SYNC-INT-008 | Merge Undo/Rollback After Sync | Allow undo if merge not desired | Undo capability for merge results | 2 pts | frontend-developer | MERGE-UI-009 |

**Phase 10 Quality Gates:**
- [ ] All sync directions support three-way merge
- [ ] Sync Status tab shows merge information clearly
- [ ] Merge preview accurate for all sync types
- [ ] Versions automatically created on sync
- [ ] Error handling covers all failure cases
- [ ] No breaking changes to existing sync behavior
- [ ] Integration tests for all sync directions
- [ ] User testing confirms merge workflow clear

**Phase 10 Deliverables:**
- Sync workflow integration with merge engine
- Updated SyncStatusTab component
- Updated sync dialogs
- Version auto-capture on sync
- Integration tests

---

### Phase 11: Testing & Documentation

**Duration**: 4-5 days
**Dependencies**: All phases (can run parallel with final phases)
**Assigned Subagent(s)**: python-backend-engineer, ui-engineer-enhanced, documentation-writer

Comprehensive testing and documentation to ensure quality and usability.

#### Phase 11 Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|--------------|
| TEST-001 | Unit Tests - Version Storage | Test all storage layer operations | >90% coverage of storage utilities | 3 pts | python-backend-engineer | STORE-006 |
| TEST-002 | Unit Tests - Repository Layer | Test all repository CRUD operations | >85% coverage of repositories | 3 pts | python-backend-engineer | REPO-011 |
| TEST-003 | Unit Tests - Merge Engine | Test merge algorithm with 50+ scenarios | >90% coverage, all edge cases | 5 pts | python-backend-engineer | MERGE-001 |
| TEST-004 | Unit Tests - Services | Test version and merge services | >80% coverage of service layer | 3 pts | python-backend-engineer | SVCV-008, INTEG-003 |
| TEST-005 | Integration Tests - Version Workflows | Test end-to-end version capture, list, compare | Full workflow tests | 4 pts | python-backend-engineer | REPO-011 |
| TEST-006 | Integration Tests - Merge Workflows | Test end-to-end merge operations | Auto-merge, conflict resolution, apply | 4 pts | python-backend-engineer | MERGE-008 |
| TEST-007 | Integration Tests - API Endpoints | Test all API endpoints | >85% coverage of API layer | 4 pts | python-backend-engineer | APIVM-012 |
| TEST-008 | Component Tests - Frontend | Test all React components | >80% coverage of components | 4 pts | ui-engineer-enhanced | HIST-010, MERGE-UI-010 |
| TEST-009 | E2E Tests - History Workflow | Test version history and restore | User story: browse history and restore | 3 pts | ui-engineer-enhanced | HIST-007 |
| TEST-010 | E2E Tests - Merge Workflow | Test full merge workflow with conflicts | User story: detect, resolve, apply merge | 4 pts | ui-engineer-enhanced | MERGE-UI-008 |
| TEST-011 | E2E Tests - Sync Integration | Test sync with merge enabled | All three sync directions | 3 pts | ui-engineer-enhanced | SYNC-INT-005 |
| TEST-012 | Performance Tests | Measure version operations performance | Version list <100ms, merge <2s, rollback <1s | 3 pts | python-backend-engineer | APIVM-013 |
| DOC-001 | API Documentation | Document all new endpoints | OpenAPI spec complete, Swagger UI | 2 pts | documentation-writer | APIVM-011 |
| DOC-002 | User Guide - Version History | Document how to use version history | Screenshots, step-by-step guide | 2 pts | documentation-writer | HIST-007 |
| DOC-003 | User Guide - Merge Workflow | Document merge workflow and conflict resolution | Clear explanation of three-way merge | 2 pts | documentation-writer | MERGE-UI-008 |
| DOC-004 | Architecture Documentation | Document version storage and merge design | Design rationale, architecture decisions | 2 pts | documentation-writer | STORE-002 |
| DOC-005 | Developer Guide - Version APIs | Document version service APIs | Code examples, usage patterns | 2 pts | documentation-writer | SVCV-008 |
| DOC-006 | Developer Guide - Merge Engine | Document merge algorithm | How three-way merge works, conflict detection | 2 pts | documentation-writer | MERGE-001 |

**Phase 11 Quality Gates:**
- [ ] Unit test coverage >85% across all layers
- [ ] Integration tests cover all workflows
- [ ] E2E tests pass for critical user paths
- [ ] Performance benchmarks met
- [ ] User documentation clear and complete
- [ ] API documentation in OpenAPI format
- [ ] No regressions in existing functionality
- [ ] Accessibility audit passes WCAG 2.1 AA

**Phase 11 Deliverables:**
- Comprehensive test suite (unit, integration, E2E)
- User documentation and guides
- API documentation
- Architecture documentation
- Performance benchmarks

---

## Orchestration Quick Reference

### Phase Execution Order

Execute phases in strict sequence due to dependencies:

1. **Phase 1** (Storage) → 2-3 days
2. **Phase 2** (Repository CRUD) → 3-5 days
3. **Phase 3** (Repository Comparisons) → 2-3 days
4. **Phase 4 & 5** (Can run parallel once Phase 3 done) → 7-9 days
5. **Phase 6** (Rollback & Integration) → 2-3 days
6. **Phase 7** (API) → 3-4 days
7. **Phase 8 & 9** (Frontend - can start parallel with Phase 7) → 8-10 days
8. **Phase 10** (Sync Integration) → 3-4 days
9. **Phase 11** (Testing & Docs - parallel with final phases) → 4-5 days

**Total Duration**: 6-8 weeks

### Task Delegation Commands

#### Phase 1: Storage Infrastructure

```
Task("data-layer-expert", "STORE-001: Design version directory structure with versions/ and latest/ layout")
Task("data-layer-expert", "STORE-002: Define .version.toml metadata schema with all required fields")
Task("data-layer-expert", "STORE-003: Implement deterministic version ID generation (v{n}-{hash})")
Task("data-layer-expert", "STORE-004: Implement file hash computation using SHA256")
Task("data-layer-expert", "STORE-005: Build version snapshot directory creation utility")
Task("data-layer-expert", "STORE-006: Design gzip compression option for version storage")
```

#### Phase 2: Repository Layer - Version CRUD

```
Task("python-backend-engineer", "REPO-001: Create VersionRepository base class with CRUD interface")
Task("python-backend-engineer", "REPO-002: Implement create_version with file snapshot and TOML metadata")
Task("python-backend-engineer", "REPO-003: Implement get_version to retrieve specific version")
Task("python-backend-engineer", "REPO-004: Implement list_versions with chronological ordering")
Task("python-backend-engineer", "REPO-005: Implement delete_version with safety checks")
Task("python-backend-engineer", "REPO-006: Implement get_version_content for file retrieval")
Task("python-backend-engineer", "REPO-007: Implement version existence check helper")
Task("python-backend-engineer", "REPO-008: Implement get_latest_version helper")
Task("python-backend-engineer", "REPO-009: Implement CollectionVersionRepository for ~/.skillmeat/")
Task("python-backend-engineer", "REPO-010: Implement ProjectVersionRepository for ./.claude/")
Task("data-layer-expert", "REPO-011: Test TOML read/write for version metadata persistence")
```

#### Phase 3: Repository Layer - Comparisons & Metadata

```
Task("python-backend-engineer", "REPO-012: Implement get_version_diff for two-way diffs")
Task("python-backend-engineer", "REPO-013: Implement get_files_changed between versions")
Task("python-backend-engineer", "REPO-014: Implement version summary calculation")
Task("python-backend-engineer", "REPO-015: Implement retention policy support (keep last N or N days)")
Task("python-backend-engineer", "REPO-016: Implement version rollback preparation")
Task("python-backend-engineer", "REPO-017: Extend .version.toml with audit metadata")
```

#### Phase 4: Service Layer - Version Management

```
Task("python-backend-engineer", "SVCV-001: Create VersionManagementService base class")
Task("python-backend-engineer", "SVCV-002: Implement capture_version_on_sync")
Task("python-backend-engineer", "SVCV-003: Implement capture_version_on_deploy")
Task("python-backend-engineer", "SVCV-004: Implement get_version_history with pagination")
Task("python-backend-engineer", "SVCV-005: Implement compare_versions high-level method")
Task("python-backend-engineer", "SVCV-006: Implement restore_version with validation")
Task("python-backend-engineer", "SVCV-007: Implement cleanup based on retention policy")
Task("python-backend-engineer", "SVCV-008: Implement version diffstat formatting")
```

#### Phase 5: Service Layer - Three-Way Merge Engine

```
Task("backend-architect", "MERGE-001: Implement three_way_merge algorithm with conflict detection")
Task("backend-architect", "MERGE-002: Implement file-level change detection")
Task("backend-architect", "MERGE-003: Implement line-level merge for text files")
Task("backend-architect", "MERGE-004: Implement conflict marker generation")
Task("backend-architect", "MERGE-005: Implement three_way_diff for visualization")
Task("backend-architect", "MERGE-006: Implement change classification (upstream/local/conflict)")
Task("backend-architect", "MERGE-007: Implement merge_preview without applying")
Task("backend-architect", "MERGE-008: Implement apply_merge with atomic writes")
Task("backend-architect", "MERGE-009: Create test data sets with 50+ merge scenarios")
Task("backend-architect", "MERGE-010: Implement binary file merge handling")
Task("backend-architect", "MERGE-011: Implement merge_stats calculation")
```

#### Phase 6: Service Layer - Rollback & Integration

```
Task("python-backend-engineer", "ROLL-001: Implement rollback with subsequent change preservation")
Task("python-backend-engineer", "ROLL-002: Implement rollback conflict detection")
Task("python-backend-engineer", "ROLL-003: Implement rollback audit trail metadata")
Task("python-backend-engineer", "ROLL-004: Ensure atomic rollback operations")
Task("python-backend-engineer", "INTEG-001: Create VersionMergeService orchestration")
Task("python-backend-engineer", "INTEG-002: Implement merge direction routing logic")
Task("python-backend-engineer", "INTEG-003: Implement comprehensive error handling")
```

#### Phase 7: API Layer - Version & Merge Endpoints

```
Task("python-backend-engineer", "APIVM-001: Implement GET /api/v1/artifacts/{id}/versions")
Task("python-backend-engineer", "APIVM-002: Implement GET /api/v1/artifacts/{id}/versions/{version_id}")
Task("python-backend-engineer", "APIVM-003: Implement GET /api/v1/artifacts/{id}/versions/{version_id}/files")
Task("python-backend-engineer", "APIVM-004: Implement GET /api/v1/artifacts/{id}/versions/{v1}/diff/{v2}")
Task("python-backend-engineer", "APIVM-005: Implement POST /api/v1/artifacts/{id}/versions/{version_id}/restore")
Task("python-backend-engineer", "APIVM-006: Implement POST /api/v1/artifacts/{id}/merge/preview")
Task("backend-architect", "APIVM-007: Implement POST /api/v1/artifacts/{id}/merge/analyze")
Task("python-backend-engineer", "APIVM-008: Implement POST /api/v1/artifacts/{id}/merge/apply")
Task("python-backend-engineer", "APIVM-009: Define request/response schemas for all endpoints")
Task("python-backend-engineer", "APIVM-010: Standardize error responses across endpoints")
Task("python-backend-engineer", "APIVM-011: Generate OpenAPI spec and Swagger UI")
Task("python-backend-engineer", "APIVM-012: Regenerate TypeScript SDK from OpenAPI")
Task("backend-architect", "APIVM-013: Create API integration tests for all endpoints")
```

#### Phase 8: Frontend - History Tab

```
Task("ui-engineer-enhanced", "HIST-001: Build VersionTimeline component with list view")
Task("ui-engineer-enhanced", "HIST-002: Implement version metadata display")
Task("ui-engineer-enhanced", "HIST-003: Build VersionContentViewer for read-only file viewing")
Task("ui-engineer-enhanced", "HIST-004: Build VersionComparisonView for side-by-side diffs")
Task("frontend-developer", "HIST-005: Add Compare button to version timeline")
Task("frontend-developer", "HIST-006: Add Restore button with confirmation dialog")
Task("frontend-developer", "HIST-007: Wire History tab into artifact detail modal")
Task("frontend-developer", "HIST-008: Implement loading and error state handling")
Task("frontend-developer", "HIST-009: Implement pagination/virtualization for large histories")
Task("ui-engineer-enhanced", "HIST-010: Implement full keyboard navigation support")
```

#### Phase 9: Frontend - Merge UI

```
Task("ui-engineer-enhanced", "MERGE-UI-001: Build ColoredDiffViewer with three-way colors")
Task("frontend-developer", "MERGE-UI-002: Add change type labels to diff display")
Task("ui-engineer-enhanced", "MERGE-UI-003: Build MergePreview component")
Task("frontend-developer", "MERGE-UI-004: Add merge statistics display")
Task("frontend-developer", "MERGE-UI-005: Integrate existing conflict-resolver component")
Task("ui-engineer-enhanced", "MERGE-UI-006: Add conflict strategy selection UI")
Task("ui-engineer-enhanced", "MERGE-UI-007: Build MergeWorkflow step-by-step component")
Task("frontend-developer", "MERGE-UI-008: Wire merge apply endpoint to button")
Task("frontend-developer", "MERGE-UI-009: Add merge result notification/toast")
Task("frontend-developer", "MERGE-UI-010: Track merge operations in version history")
```

#### Phase 10: Sync Integration

```
Task("python-backend-engineer", "SYNC-INT-001: Wire three-way merge to upstream sync")
Task("python-backend-engineer", "SYNC-INT-002: Wire three-way merge to deploy sync")
Task("python-backend-engineer", "SYNC-INT-003: Wire three-way merge to pull sync")
Task("ui-engineer-enhanced", "SYNC-INT-004: Enhance SyncStatusTab with merge display")
Task("ui-engineer-enhanced", "SYNC-INT-005: Redesign sync dialogs for unified merge workflow")
Task("python-backend-engineer", "SYNC-INT-006: Auto-capture version on sync completion")
Task("python-backend-engineer", "SYNC-INT-007: Add merge-specific error handling")
Task("frontend-developer", "SYNC-INT-008: Add merge undo/rollback capability")
```

#### Phase 11: Testing & Documentation

```
Task("python-backend-engineer", "TEST-001: Write unit tests for storage layer (>90% coverage)")
Task("python-backend-engineer", "TEST-002: Write unit tests for repository layer (>85% coverage)")
Task("python-backend-engineer", "TEST-003: Write unit tests for merge engine with 50+ scenarios")
Task("python-backend-engineer", "TEST-004: Write unit tests for services (>80% coverage)")
Task("python-backend-engineer", "TEST-005: Write integration tests for version workflows")
Task("python-backend-engineer", "TEST-006: Write integration tests for merge workflows")
Task("python-backend-engineer", "TEST-007: Write integration tests for API endpoints (>85%)")
Task("ui-engineer-enhanced", "TEST-008: Write component tests for frontend (>80% coverage)")
Task("ui-engineer-enhanced", "TEST-009: Write E2E tests for history workflow")
Task("ui-engineer-enhanced", "TEST-010: Write E2E tests for merge workflow")
Task("ui-engineer-enhanced", "TEST-011: Write E2E tests for sync integration")
Task("python-backend-engineer", "TEST-012: Create performance tests and benchmarks")
Task("documentation-writer", "DOC-001: Write API documentation for all endpoints")
Task("documentation-writer", "DOC-002: Write user guide for version history feature")
Task("documentation-writer", "DOC-003: Write user guide for merge workflow")
Task("documentation-writer", "DOC-004: Write architecture documentation")
Task("documentation-writer", "DOC-005: Write developer guide for version APIs")
Task("documentation-writer", "DOC-006: Write developer guide for merge engine")
```

---

## Key Architectural Decisions

### 1. Directory-Based Snapshots

**Decision**: Use filesystem directories for version snapshots rather than delta storage or Git history

**Rationale**:
- Simple, debuggable (users can directly inspect versions on disk)
- No external dependency (Git optional)
- Fast for typical artifact sizes (< 10MB)
- Preserves file structure and permissions

**Trade-off**: Higher disk usage vs. simplicity

### 2. Content-Addressed Version IDs

**Decision**: Version IDs include content hash (v{n}-{hash}) for deterministic identification

**Rationale**:
- Same content produces same ID (idempotent)
- Enables deduplication in future
- Makes versions tamper-evident

### 3. Three-Way Merge Algorithm

**Decision**: Implement line-level merge for text files, file-level for binary

**Rationale**:
- Supports auto-merging non-conflicting changes
- Practical conflict detection (only true conflicts to user)
- Line-level granularity sufficient for most artifacts

### 4. Atomic Operations

**Decision**: All merge and rollback operations are all-or-nothing (transactional semantics)

**Rationale**:
- Prevents partial updates
- No corruption on failure
- Simple recovery (retry entire operation)

### 5. Version Capture on Sync/Deploy

**Decision**: Automatic version capture during all synchronization operations

**Rationale**:
- Complete audit trail
- No user action required
- Enables rollback from any state

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| Merge algorithm produces corrupt artifact | HIGH | LOW | Atomic operations, validation, 50+ test scenarios, code review |
| Version storage bloats disk space | MEDIUM | MEDIUM | Compression, retention policies, configurable cleanup |
| Three-way merge confuses users | MEDIUM | MEDIUM | Clear color coding + labels, guided workflow, user testing |
| Large version histories slow down UI | MEDIUM | LOW | Pagination, virtual scrolling, lazy loading |
| Rollback conflicts with later changes | HIGH | LOW | Rollback conflict detection, user confirmation |
| Network failure during merge loses changes | MEDIUM | LOW | Atomic writes, local fallback, retry capability |
| Users accidentally restore wrong version | MEDIUM | MEDIUM | Confirmation dialog, clear version info, undo support |

---

## Success Criteria

### Functional Acceptance

- [x] Per-artifact version snapshots created on sync/deploy/edit
- [x] Version metadata stored with timestamp, hash, source, change list
- [x] History tab displays chronological version list
- [x] Users can view content and compare any two versions
- [x] One-click restore to prior version with confirmation
- [x] Three-way merge detects changes in all three directions
- [x] Auto-merge applies non-conflicting changes automatically
- [x] Conflict resolver shows merge options for true conflicts
- [x] Color-coded diff displays changes with clear labels
- [x] All sync directions use three-way merge
- [x] Rollback operation is atomic and preserves data integrity

### Performance Acceptance

- [x] Version history retrieval for 100 versions: < 500ms
- [x] Three-way diff computation for 10MB artifact: < 2s
- [x] Rollback operation: < 1s (excluding I/O)
- [x] Merge operation (including storage): < 5s

### Quality Acceptance

- [x] Unit test coverage >85% across all layers
- [x] Integration tests cover all workflows
- [x] E2E tests pass for critical user paths
- [x] API documentation complete in OpenAPI
- [x] User documentation clear and comprehensive
- [x] No regressions in existing functionality
- [x] Accessibility audit passes WCAG 2.1 AA

---

## Timeline Estimate

```
Week 1:  Phase 1 (Storage) + Phase 2 (Repository CRUD)
Week 2:  Phase 3 (Repository Comparisons) + Phase 4 & 5 (Services)
Week 3:  Phase 4 & 5 continued + Phase 6 (Rollback & Integration)
Week 4:  Phase 7 (API) + Phase 8 (History Tab) - parallel
Week 5:  Phase 8 & 9 (Frontend) - parallel
Week 6:  Phase 9 continued + Phase 10 (Sync Integration)
Week 7:  Phase 10 continued + Phase 11 (Testing & Docs)
Week 8:  Phase 11 continued - Final testing and polish
```

**Critical Path**: Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8/9 (parallel) → 10

**Parallel Opportunities**:
- Phase 4 & 5 (once Phase 3 done)
- Phase 8 & 9 (once Phase 7 done)
- Phase 11 (with Phase 10)

---

## Deliverables Summary

### Backend Deliverables
- Version storage infrastructure (STORE-001 to STORE-006)
- VersionRepository implementations (REPO-001 to REPO-017)
- VersionManagementService (SVCV-001 to SVCV-008)
- MergeEngine with three-way merge (MERGE-001 to MERGE-011)
- Rollback service with preservation logic (ROLL-001 to ROLL-004)
- REST API endpoints for version and merge (APIVM-001 to APIVM-013)
- Comprehensive test suite (TEST-001 to TEST-012)

### Frontend Deliverables
- VersionTimeline component
- VersionContentViewer component
- VersionComparisonView component
- ColoredDiffViewer component
- MergePreview component
- MergeWorkflow component
- Enhanced SyncStatusTab
- Conflict resolver integration
- Component tests and Storybook stories

### Documentation Deliverables
- API documentation (OpenAPI)
- User guides (Version history, Merge workflow)
- Architecture documentation
- Developer guides (Version APIs, Merge engine)

---

## Dependencies & Assumptions

### External Dependencies
- Python standard library (difflib, pathlib)
- FastAPI (existing)
- React/TypeScript (existing)
- Radix UI & shadcn (existing)
- Existing conflict-resolver component

### Assumptions
- Artifact files are text-based or text-representable
- Users have stable network during sync/merge
- Version metadata < 100 versions per artifact typical
- Rollback always safe (content-addressed storage)
- Three-way merge sufficient (no semantic merge needed)

---

## Feature Flags

For safe rollout and testing:

```python
ENABLE_VERSION_HISTORY = True      # Enable per-artifact versioning
ENABLE_THREE_WAY_MERGE = True      # Enable smart merge algorithm
ENABLE_AUTO_MERGE = True           # Enable automatic merges
ENABLE_MERGE_UI = True             # Enable merge UI in frontend
VERSION_RETENTION_DAYS = 90        # Keep versions for 90 days
VERSION_RETENTION_COUNT = 50       # Or keep last 50 versions
VERSION_COMPRESSION = "gzip"       # gzip, bzip2, or none
```

---

## References & Related Documentation

### PRDs
- `/docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md` - Complete PRD
- `/docs/project_plans/PRDs/features/entity-lifecycle-management-v1.md` - Related entity management
- `/docs/project_plans/PRDs/enhancements/web-ui-consolidation-v1.md` - Related UI consolidation

### Codebase References
- `skillmeat/storage/snapshot.py` - Existing snapshot manager (extend)
- `skillmeat/core/sync.py` - Sync manager (integrate merge)
- `skillmeat/models.py` - DiffResult model (enhance)
- `skillmeat/web/components/collection/conflict-resolver.tsx` - Reuse component
- `skillmeat/api/routers/artifacts.py` - Artifact endpoints (extend)

### Prior Art
- Git three-way merge and conflict markers
- Mercurial merge strategies
- Google Docs revision history
- Figma version history and branching

---

**Plan Status**: Draft
**Last Updated**: 2025-11-30
**Created**: 2025-11-30

This implementation plan is designed for AI agent execution with clear task breakdown, dependencies, acceptance criteria, and story point estimates. Execute phases sequentially following the critical path while leveraging parallel opportunities for components with independent dependencies.
