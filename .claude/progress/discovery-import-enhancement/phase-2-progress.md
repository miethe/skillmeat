---
type: progress
prd: "discovery-import-enhancement"
phase: 2
title: "Backend - Skip Persistence & Endpoints"
status: "planning"
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 9
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer", "backend-architect"]
contributors: ["testing-specialist", "data-layer-expert"]

tasks:
  - id: "DIS-2.1"
    description: "Design skip preference schema for TOML/JSON storage in .claude/.skillmeat_skip_prefs.toml"
    status: "pending"
    assigned_to: ["backend-architect"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "high"

  - id: "DIS-2.2"
    description: "Implement SkipPreferenceManager class with CRUD operations and thread-safe file handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DIS-2.1"]
    estimated_effort: "1.5d"
    priority: "critical"

  - id: "DIS-2.3"
    description: "Integrate skip preference check into ArtifactDiscoveryService.discover() to filter skipped artifacts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DIS-2.2"]
    estimated_effort: "1d"
    priority: "critical"

  - id: "DIS-2.4"
    description: "Add API endpoints: POST/DELETE skip preferences, GET list skips for project"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["DIS-2.2"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-2.5"
    description: "Update BulkImportRequest schema to include optional skip_list parameter"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-2.6"
    description: "Update BulkImportResult to include skipped_artifacts with reasons"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["DIS-2.5"]
    estimated_effort: "0.5d"
    priority: "medium"

  - id: "DIS-2.7"
    description: "Unit tests for SkipPreferenceManager - CRUD, file handling, edge cases"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-2.2"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-2.8"
    description: "Unit tests for skip integration in discovery - filtering, performance <100ms overhead"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-2.3"]
    estimated_effort: "1d"
    priority: "high"

  - id: "DIS-2.9"
    description: "Integration tests for full skip workflow - discovery → mark skip → import → future discovery excludes skipped"
    status: "pending"
    assigned_to: ["testing-specialist"]
    dependencies: ["DIS-2.4", "DIS-2.6"]
    estimated_effort: "1d"
    priority: "high"

parallelization:
  batch_1: ["DIS-2.1", "DIS-2.5"]
  batch_2: ["DIS-2.2", "DIS-2.3", "DIS-2.4", "DIS-2.6"]
  batch_3: ["DIS-2.7", "DIS-2.8"]
  batch_4: ["DIS-2.9"]
  critical_path: ["DIS-2.1", "DIS-2.2", "DIS-2.3", "DIS-2.9"]
  estimated_total_time: "5-6 days"

blockers: []

success_criteria:
  - id: "SC-1"
    description: "Skip preference schema designed and approved"
    status: "pending"
  - id: "SC-2"
    description: "SkipPreferenceManager CRUD operations functional"
    status: "pending"
  - id: "SC-3"
    description: "Skip check integrated into discovery with <100ms overhead"
    status: "pending"
  - id: "SC-4"
    description: "API endpoints working and authenticated"
    status: "pending"
  - id: "SC-5"
    description: "Skip preferences persisted correctly to filesystem"
    status: "pending"
  - id: "SC-6"
    description: "Performance validation: discovery <2.1s with skip checks"
    status: "pending"
  - id: "SC-7"
    description: "Unit test coverage >80%"
    status: "pending"
  - id: "SC-8"
    description: "Integration tests pass: skip workflow end-to-end"
    status: "pending"

files_modified:
  - "skillmeat/core/skip_preferences.py"
  - "skillmeat/api/schemas/discovery.py"
  - "skillmeat/api/routers/artifacts.py"
  - "skillmeat/core/discovery.py"
  - "tests/core/test_skip_preferences.py"
  - "tests/core/test_skip_integration.py"
---

# Discovery & Import Enhancement - Phase 2: Backend - Skip Persistence & Endpoints

**Phase**: 2 of 6
**Status**: 📋 Planning (0% complete)
**Duration**: Estimated 2-3 days (Parallel with Phase 3)
**Owner**: python-backend-engineer, backend-architect
**Contributors**: testing-specialist, data-layer-expert
**Dependency**: Phase 1 ✓ Complete

---

## Orchestration Quick Reference

> **For Orchestration Agents**: Launch Phase 2 in parallel with Phase 3 after Phase 1 completes.

### Parallelization Strategy

**Batch 1** (Parallel - No Dependencies):
- DIS-2.1 → `backend-architect` (0.5d) - Design skip preference schema
- DIS-2.5 → `data-layer-expert` (0.5d) - Update BulkImportRequest schema

**Batch 2** (Parallel - Depends on Batch 1):
- DIS-2.2 → `python-backend-engineer` (1.5d) - Implement SkipPreferenceManager
- DIS-2.3 → `python-backend-engineer` (1d) - Integrate skip check into discovery (depends on DIS-2.2)
- DIS-2.4 → `python-backend-engineer` (1d) - Add API endpoints (depends on DIS-2.2)
- DIS-2.6 → `data-layer-expert` (0.5d) - Update BulkImportResult schema (depends on DIS-2.5)

**Batch 3** (Parallel - Depends on Batch 2):
- DIS-2.7 → `testing-specialist` (1d) - SkipPreferenceManager unit tests
- DIS-2.8 → `testing-specialist` (1d) - Skip integration unit tests (depends on DIS-2.3)

**Batch 4** (Sequential - Depends on Batch 3):
- DIS-2.9 → `testing-specialist` (1d) - Full skip workflow integration tests

**Critical Path**: DIS-2.1 → DIS-2.2 → DIS-2.3 → DIS-2.9 (5-6 days total)

### Task Delegation Commands

```
# Batch 1 (Launch in parallel after Phase 1 completes)
Task("backend-architect", "DIS-2.1: Design skip preference schema for TOML storage. File: .claude/.skillmeat_skip_prefs.toml structure. Include: project_id, artifact_key (type:name format), skip_reason, added_date. Acceptance: (1) Schema designed; (2) Handles collisions; (3) Supports per-project clearing; (4) Design reviewed")

Task("data-layer-expert", "DIS-2.5: Update BulkImportRequest schema to add optional skip_list parameter. File: skillmeat/api/schemas/discovery.py. Add: skip_list: Optional[List[str]]. Acceptance: (1) Schema updated; (2) Backward compat; (3) OpenAPI reflects change")

# Batch 2 (After Batch 1 completes)
Task("python-backend-engineer", "DIS-2.2: Implement SkipPreferenceManager class with thread-safe CRUD. File: skillmeat/core/skip_preferences.py (new). Methods: load_skip_prefs(project_id), add_skip(project_id, artifact_key, reason), is_skipped(project_id, artifact_key), clear_skips(project_id). Acceptance: (1) Thread-safe; (2) CRUD working; (3) Handles missing file; (4) Validates artifact_key; (5) Unit tests 80%+")

Task("python-backend-engineer", "DIS-2.3: Integrate skip check into ArtifactDiscoveryService.discover(). File: skillmeat/core/discovery.py. Load skip prefs and filter out skipped artifacts before returning. Acceptance: (1) Skip prefs loaded; (2) Skipped artifacts filtered; (3) Performance impact <100ms; (4) Skipped artifacts optional in separate list; (5) Tests pass")

Task("python-backend-engineer", "DIS-2.4: Add skip preference API endpoints. File: skillmeat/api/routers/artifacts.py. Endpoints: POST /projects/{project_id}/skip-preferences, DELETE /projects/{project_id}/skip-preferences/{artifact_key}, DELETE /projects/{project_id}/skip-preferences, GET /projects/{project_id}/skip-preferences. Acceptance: (1) All endpoints working; (2) Auth required; (3) Responses consistent; (4) Error handling robust")

Task("data-layer-expert", "DIS-2.6: Update BulkImportResult to include skipped_artifacts list. File: skillmeat/api/schemas/discovery.py. Add: skipped_artifacts: List[SkippedArtifactInfo] with artifact_key, skip_reason. Acceptance: (1) Schema updated; (2) Toast utils can parse; (3) Notification System integration ready")

# Batch 3 (After Batch 2 completes)
Task("testing-specialist", "DIS-2.7: Unit tests for SkipPreferenceManager. File: tests/core/test_skip_preferences.py (new). Test: CRUD operations, file handling, edge cases (corrupt file, missing project, duplicate keys). Acceptance: (1) All operations tested; (2) Handles errors gracefully; (3) File integrity maintained; (4) Coverage >80%")

Task("testing-specialist", "DIS-2.8: Unit tests for skip integration in discovery. File: tests/core/test_skip_integration.py (new). Test: skip filtering works, performance <100ms overhead, non-skipped artifacts included. Acceptance: (1) Skip filtering works; (2) Performance baseline + skip <100ms; (3) Coverage >80%")

# Batch 4 (After Batch 3 completes)
Task("testing-specialist", "DIS-2.9: Integration tests for full skip workflow. File: tests/integration/test_skip_workflow.py (new). Test: discovery → mark skip → import with skip list → future discovery excludes skipped. Acceptance: (1) Artifacts skipped during import; (2) Skip prefs saved; (3) Future discovery filters skipped; (4) All state consistent")
```

---

## Overview

**Phase 2** implements server-side skip preference storage and retrieval, allowing users to persistently exclude artifacts from future discovery results. This phase runs in parallel with Phase 3 (Frontend), with frontend using mocked API endpoints until Phase 2 completes.

**Why This Phase**: Phase 1 implemented intelligent pre-scan logic, but users have no way to mark "noisy" artifacts they don't want to see. Phase 2 adds skip preferences with file-based persistence, coordinated with frontend LocalStorage for optimal UX (client-side display, server-side state).

**Scope**:
- **IN**: Skip preference schema, SkipPreferenceManager class, API endpoints, discovery integration, backend tests
- **OUT**: Frontend LocalStorage persistence (Phase 3), Discovery Tab UI (Phase 4), Notification System integration (Phase 5)

---

## Success Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| SC-1 | Skip preference schema designed and approved | ⏳ Pending |
| SC-2 | SkipPreferenceManager CRUD operations functional | ⏳ Pending |
| SC-3 | Skip check integrated into discovery with <100ms overhead | ⏳ Pending |
| SC-4 | API endpoints working and authenticated | ⏳ Pending |
| SC-5 | Skip preferences persisted correctly to filesystem | ⏳ Pending |
| SC-6 | Performance validation: discovery <2.1s with skip checks | ⏳ Pending |
| SC-7 | Unit test coverage >80% | ⏳ Pending |
| SC-8 | Integration tests pass: skip workflow end-to-end | ⏳ Pending |

---

## Tasks

| ID | Task | Status | Agent | Dependencies | Est | Notes |
|----|------|--------|-------|--------------|-----|-------|
| DIS-2.1 | Design skip preference schema | ⏳ | backend-architect | None | 0.5d | TOML structure |
| DIS-2.2 | Implement SkipPreferenceManager | ⏳ | python-backend-engineer | DIS-2.1 | 1.5d | Thread-safe CRUD |
| DIS-2.3 | Integrate skip check in discovery | ⏳ | python-backend-engineer | DIS-2.2 | 1d | Filter skipped |
| DIS-2.4 | Add API endpoints | ⏳ | python-backend-engineer | DIS-2.2 | 1d | POST/DELETE/GET |
| DIS-2.5 | Update BulkImportRequest schema | ⏳ | data-layer-expert | None | 0.5d | Add skip_list |
| DIS-2.6 | Update BulkImportResult schema | ⏳ | data-layer-expert | DIS-2.5 | 0.5d | Add skipped_artifacts |
| DIS-2.7 | SkipPreferenceManager unit tests | ⏳ | testing-specialist | DIS-2.2 | 1d | CRUD, file handling |
| DIS-2.8 | Skip integration unit tests | ⏳ | testing-specialist | DIS-2.3 | 1d | Filtering, perf |
| DIS-2.9 | Skip workflow integration tests | ⏳ | testing-specialist | DIS-2.4, DIS-2.6 | 1d | End-to-end |

---

## Architecture Context

### Current State

No skip preference system exists. All discovered artifacts are shown every time discovery runs. Users cannot suppress noisy artifacts.

**Key Files**:
- `skillmeat/core/discovery.py` - ArtifactDiscoveryService (will be enhanced)
- `skillmeat/api/routers/artifacts.py` - Discovery endpoints (will be enhanced)
- `skillmeat/api/schemas/discovery.py` - Request/response schemas (will be updated)

### Reference Patterns

File-based storage pattern:
- Manifest files (manifest.toml) already used for Collection/Project artifact storage
- Lock files (.skillmeat.lock) already used for versioning
- Both follow TOML format with atomic write patterns

---

## Implementation Details

### Technical Approach

1. **Skip Preference Schema (DIS-2.1)**:
   - Design TOML structure: `.claude/.skillmeat_skip_prefs.toml`
   ```
   [projects]
   [projects."<project_id>"]
   skipped = [
     { artifact_key = "skill:canvas-design", skip_reason = "Too noisy", added_date = "2025-12-04" }
   ]
   ```
   - Alternative JSON structure in case TOML has issues
   - Handle collisions (same artifact key, different type prefixes)

2. **SkipPreferenceManager (DIS-2.2)**:
   - Class methods:
     - `load_skip_prefs(project_id: str) -> List[SkipPreference]`
     - `add_skip(project_id: str, artifact_key: str, reason: str) -> bool`
     - `is_skipped(project_id: str, artifact_key: str) -> bool`
     - `clear_skips(project_id: str, artifact_key: Optional[str]) -> bool`
   - Thread-safe file operations (atomic writes, locks)
   - Graceful error handling (missing file → empty list)

3. **Discovery Integration (DIS-2.3)**:
   - Load skip prefs for current project
   - Filter discovered artifacts by `is_skipped()`
   - Keep baseline performance <100ms overhead on pre-scan
   - Optional: return skipped artifacts in separate list for UI feedback

4. **API Endpoints (DIS-2.4)**:
   - `POST /projects/{project_id}/skip-preferences` - Add skip
   - `DELETE /projects/{project_id}/skip-preferences/{artifact_key}` - Remove single skip
   - `DELETE /projects/{project_id}/skip-preferences` - Clear all skips
   - `GET /projects/{project_id}/skip-preferences` - List skips
   - All require authentication/authorization

5. **Schema Updates (DIS-2.5, DIS-2.6)**:
   - BulkImportRequest: add `skip_list: Optional[List[str]]`
   - BulkImportResult: add `skipped_artifacts: List[SkippedArtifactInfo]`

### Known Gotchas

- **File Corruption**: If skip preferences file is corrupted → catch exception, log warning, proceed with empty skip list
- **Race Conditions**: Multiple processes adding skips simultaneously → use file locking or atomic operations
- **Permission Denied**: If can't write to .claude directory → log error, skip persistence continues
- **Backward Compatibility**: Existing projects without skip prefs file → gracefully handle missing file

### Development Setup

- Temporary project directory for testing skip operations
- Mocked file operations for error scenarios
- Test fixtures for corrupted/malformed skip preference files

---

## Blockers

### Active Blockers

- **Phase 1 Dependency**: Awaiting completion of Phase 1 before beginning Phase 2

---

## Dependencies

### External Dependencies

- **Phase 1 Complete**: Pre-scan logic and status enum from Phase 1 (no hard dependency, but needed context)
- **Phase 3 Parallel**: Frontend uses mocked Phase 2 endpoints; code merges after both complete

### Internal Integration Points

- **ArtifactDiscoveryService** - Calls `SkipPreferenceManager.is_skipped()` during discovery
- **API Routers** - New endpoints for skip management
- **Schemas** - BulkImportRequest/Result updated

---

## Testing Strategy

| Test Type | Scope | Coverage | Status |
|-----------|-------|----------|--------|
| Unit - SkipPreferenceManager | CRUD, file I/O, error handling, edge cases | 80%+ | ⏳ |
| Unit - Discovery Integration | Skip filtering, performance overhead | 80%+ | ⏳ |
| Unit - API Endpoints | Request validation, response format | 80%+ | ⏳ |
| Integration | Full skip workflow: mark → import → future discovery | Core flow | ⏳ |
| Performance | Skip check <100ms overhead on discovery | <2.1s total | ⏳ |

---

## Next Session Agenda

### Immediate Actions (Next Session - After Phase 1 Complete)
1. [ ] Launch Batch 1: Start DIS-2.1 and DIS-2.5 (can run in parallel)
2. [ ] Setup test fixtures for skip preference file operations
3. [ ] Coordinate with Phase 3 on API mock endpoints for frontend

### Upcoming Critical Items

- **Day 1-2**: Batch 2 completion (SkipPreferenceManager + endpoints)
- **Day 2-3**: Batch 3 starts (unit tests)
- **Day 4**: Quality gate check - all tests passing, integration flow verified

### Context for Continuing Agent

Phase 2 runs in parallel with Phase 3. Key coordination:
1. Phase 3 can mock Phase 2 API endpoints while Phase 2 is being implemented
2. Skip preference schema (DIS-2.1) must be finalized early for frontend mocking
3. Performance validation (<100ms overhead) is critical - benchmark early in DIS-2.3
4. File persistence must be robust - use atomic operations and comprehensive error handling

---

## Session Notes

*None yet - Phase 2 not started*

---

## Additional Resources

- **Skip Preference Design Spec**: To be created by backend-architect in DIS-2.1
- **Phase 1 Results**: ImportResult enum, pre-scan logic from Phase 1
- **Phase 3 Integration**: Frontend LocalStorage coordination
- **File Storage Reference**: Manifest.toml structure (skillmeat/storage/)
