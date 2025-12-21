# Implementation Plan: Discovery & Import Enhancement

**Complexity**: L (Large) | **Track**: Full | **Created**: 2025-12-04

**Estimated Effort**: 55-65 story points | **Timeline**: 12-16 days | **Parallelization**: 3 batches

**Status**: Ready for execution | **Last Updated**: 2025-12-04

---

## Executive Summary

This implementation plan transforms the Discovery & Import system to support intelligent pre-scan checks, granular import status tracking, persistent skip preferences, and a permanent Discovery Tab interface. The enhancement bridges critical UX gaps where artifacts marked as "Failed" are actually already in the Collection, and users cannot skip repeated noisy discoveries.

**Key Deliverables**:
1. Import status enum (success/skipped/failed) replacing boolean `success` field
2. Pre-scan logic checking Collection AND Project before filtering results
3. Skip preference persistence via browser LocalStorage with project-scoped namespacing
4. Permanent Discovery Tab on Project Detail page showing all discovered artifacts
5. Notification System integration with detailed status breakdowns
6. End-to-end workflow tested with performance validation (<2 seconds for discovery)

**Critical Path**: Phase 1 (Backend Schema) → Phase 2-3 (Parallel) → Phase 4 (Discovery Tab) → Phase 5-6 (Testing & Polish)

---

## Phase 1: Backend - Import Status Logic & Pre-scan Foundation

**Duration**: 2-3 days | **Status**: Not started | **Complexity**: High (architectural changes)

**Objective**: Update import status model to use enum instead of boolean, implement pre-scan logic to filter artifacts by Collection/Project existence, and establish foundation for remaining phases.

**Dependencies**: None (Phase 1 blocks all others)

### Phase 1 Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Status |
|---------|------|-------------|-------------------|----------|------------|--------|
| DIS-1.1 | Update ImportResult Schema | Change `success: bool` to `status: Enum["success", "skipped", "failed"]` + add `skip_reason: Optional[str]` field | (1) Pydantic enum created with all three values; (2) Backward compat analysis complete; (3) All usages updated; (4) Schema tests pass; (5) OpenAPI docs reflect new enum | 2d | data-layer-expert | pending |
| DIS-1.2 | Implement Pre-scan Check Logic | Create `check_artifact_exists()` method to verify if artifact exists in Collection or Project | (1) Method checks Collection manifest; (2) Method checks Project directory; (3) Returns accurate location info; (4) Handles missing/corrupt files gracefully; (5) Unit tests for all scenarios (exists nowhere, in Collection only, Project only, both) | 1.5d | python-backend-engineer | pending |
| DIS-1.3 | Update ArtifactDiscoveryService | Integrate pre-scan check into `discover()` method to filter results before returning to frontend; implement early return when 0 importable artifacts | (1) Discovery filters by pre-scan results; (2) `importable_count` reflects only new artifacts; (3) `discovered_count` unchanged (all found); (4) Performance benchmark <2s for typical project; (5) Integration tests pass | 1.5d | python-backend-engineer | pending |
| DIS-1.4 | Update Import Status Mapping | Implement logic to determine status for each artifact (success/skipped/failed) based on location (Collection, Project, or unknown error) | (1) Success: artifact added to target location; (2) Skipped: artifact already exists in Collection/Project; (3) Failed: permission error or network issue; (4) Skip reason populated with human-readable message; (5) Unit tests for all paths | 1.5d | python-backend-engineer | pending |
| DIS-1.5 | Update BulkImportResult Schema | Add `skipped_count` to result breakdown; update to distinguish Collection vs Project additions | (1) Schema includes skipped_count; (2) Results include per-location counts ("imported_to_collection": N, "added_to_project": N); (3) Backward compat analysis; (4) API response examples updated | 1d | data-layer-expert | pending |
| DIS-1.6 | Update API Response Models | Update all discovery/import endpoints to use new schemas; verify OpenAPI documentation | (1) GET /artifacts/discover returns DiscoveryResult with filtered artifacts; (2) POST /artifacts/discover/import returns BulkImportResult with new status enum; (3) OpenAPI schema generated correctly; (4) All responses validated | 1d | backend-architect | pending |
| DIS-1.7 | Unit Tests - Pre-scan Logic | Test pre-scan check with all combinations (artifact in Collection only, Project only, both, neither) and error cases | (1) Collection exists + Project exists → filtered correctly; (2) Collection exists + Project missing → filtered by Collection; (3) Both missing → includes artifact; (4) File corruption → graceful error; (5) Coverage >80% | 1d | testing-specialist | pending |
| DIS-1.8 | Unit Tests - Status Enum | Test import status determination for all scenarios (success adds to Collection, skipped already in Collection, failed permission denied) | (1) All enum values tested; (2) Skip reason populated correctly; (3) Error messages appropriate; (4) Coverage >80% | 1d | testing-specialist | pending |
| DIS-1.9 | Integration Tests - Discovery Flow | Test full discovery flow: scan → pre-check → filter → return with new status enum | (1) Discovery endpoint returns filtered results; (2) Import status accurate; (3) All fields populated; (4) Performance acceptable | 1d | testing-specialist | pending |

### Phase 1 Key Files to Modify

```
skillmeat/api/schemas/discovery.py
  - ImportResult: change success: bool → status: Enum + skip_reason: Optional[str]
  - BulkImportResult: add skipped_count, per_location counts

skillmeat/core/discovery.py
  - ArtifactDiscoveryService.discover(): integrate pre-scan check, filter by location
  - add check_artifact_exists(artifact_key) → {"location": "collection|project|both|none", ...}

skillmeat/core/importer.py
  - ArtifactImporter.bulk_import(): use new status enum
  - add determine_import_status() method for status mapping

skillmeat/api/routers/artifacts.py
  - POST /artifacts/discover: use new DiscoveryResult schema
  - POST /artifacts/discover/import: use new BulkImportResult schema
  - GET /artifacts/discover/project/{project_id}: integrate pre-scan

tests/core/test_discovery_prescan.py (new)
  - Test pre-scan check logic with all scenarios

tests/core/test_import_status_enum.py (new)
  - Test import status determination
```

### Phase 1 Quality Gates

- [ ] All ImportResult usages updated to use status enum (0 remaining `success: bool`)
- [ ] Pre-scan check performance <2 seconds on typical project (500 artifacts in Collection, 200 in Project)
- [ ] Import status determination tests pass (all scenarios covered)
- [ ] Discovery endpoint returns filtered results with new schema
- [ ] Backward compatibility analysis complete (document breaking changes for API consumers)
- [ ] OpenAPI documentation reflects new schemas
- [ ] Unit test coverage >80% for pre-scan and status mapping logic
- [ ] Integration tests pass: discovery → import → result

### Phase 1 Deliverable

Backend endpoints return accurate import status enums with skip reasons. Pre-scan logic filters artifacts by Collection/Project existence. Foundation ready for frontend type updates and skip preference implementation.

---

## Phase 2: Backend - Skip Persistence & Endpoint

**Duration**: 2-3 days | **Status**: Not started | **Depends On**: Phase 1 ✓

**Objective**: Implement server-side skip preference storage and retrieval endpoints for coordination with client-side LocalStorage. Create SkipPreferenceManager for CRUD operations on skip preferences.

**Runs In Parallel With**: Phase 3 (Frontend updates) - can proceed independently after Phase 1

### Phase 2 Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Status |
|---------|------|-------------|-------------------|----------|------------|--------|
| DIS-2.1 | Design Skip Preference Schema | Create TOML/JSON schema for skip list storage in `.claude/.skillmeat_skip_prefs.toml` or manifest extension | (1) Schema designed with project_id, artifact_key ("type:name"), skip_reason, added_date; (2) Handles collisions (same artifact key different types); (3) Supports clearing per-project; (4) Design reviewed and approved | 0.5d | backend-architect | pending |
| DIS-2.2 | Implement SkipPreferenceManager | Create Python class: `load_skip_prefs(project_id)`, `add_skip(project_id, artifact_key, reason)`, `is_skipped(project_id, artifact_key)`, `clear_skips(project_id)` | (1) Thread-safe file operations; (2) CRUD operations working; (3) Handles missing file gracefully; (4) Validates artifact_key format; (5) Unit tests 80%+ | 1.5d | python-backend-engineer | pending |
| DIS-2.3 | Integrate Skip Check in Discovery | Update `ArtifactDiscoveryService.discover()` to load skip prefs and filter out skipped artifacts before returning results | (1) Skip prefs loaded for project; (2) Skipped artifacts filtered from results; (3) Performance impact <100ms; (4) Skipped artifacts still visible with skip reason in optional separate list; (5) Tests pass | 1d | python-backend-engineer | pending |
| DIS-2.4 | Add Skip Preference API Endpoints | Create POST endpoint to add skip, DELETE endpoint to clear skips, GET endpoint to list skips for project | (1) POST /projects/{project_id}/skip-preferences: add skip with artifact_key and reason; (2) DELETE /projects/{project_id}/skip-preferences/{artifact_key}: remove single skip; (3) DELETE /projects/{project_id}/skip-preferences: clear all; (4) GET /projects/{project_id}/skip-preferences: list all; (5) Auth required | 1d | python-backend-engineer | pending |
| DIS-2.5 | Update BulkImportRequest Schema | Add optional `skip_list: List[str]` to request payload for frontend to send skipped artifacts at import time | (1) Schema updated; (2) Backend processes skip list (stores as skip preferences); (3) Skipped artifacts not imported; (4) Skip reason recorded for future discovery | 0.5d | data-layer-expert | pending |
| DIS-2.6 | Add Skip Reason to BulkImportResult | Include which artifacts were marked to skip in import result for frontend feedback | (1) Result includes skipped_artifacts with reason; (2) Toast utils can parse this; (3) Notification System integration ready | 0.5d | data-layer-expert | pending |
| DIS-2.7 | Unit Tests - SkipPreferenceManager | Test CRUD operations, file handling, edge cases (corrupt file, missing project, duplicate keys) | (1) All operations tested; (2) Handles errors gracefully; (3) File integrity maintained; (4) Coverage >80% | 1d | testing-specialist | pending |
| DIS-2.8 | Unit Tests - Skip Integration | Test skip preferences integrated into discovery (skipped artifacts filtered, performance acceptable) | (1) Skip filtering works; (2) Performance <2.1s (baseline <2s + skip overhead <0.1s); (3) Non-skipped artifacts included; (4) Coverage >80% | 1d | testing-specialist | pending |
| DIS-2.9 | Integration Tests - Skip Workflow | Test full skip workflow: discovery → user marks skip → import with skip list → future discovery excludes skipped | (1) Artifacts skipped during import; (2) Skip prefs saved; (3) Future discovery filters skipped; (4) All state consistent | 1d | testing-specialist | pending |

### Phase 2 Key Files to Modify/Create

```
skillmeat/core/skip_preferences.py (new)
  - SkipPreferenceManager class: load, save, check, clear operations
  - Skip preference file handling (.claude/.skillmeat_skip_prefs.toml)

skillmeat/api/schemas/discovery.py
  - BulkImportRequest: add skip_list: Optional[List[str]]
  - BulkImportResult: add skipped_artifacts: List[SkippedArtifactInfo]

skillmeat/api/routers/artifacts.py
  - POST /projects/{project_id}/skip-preferences: add skip
  - DELETE /projects/{project_id}/skip-preferences/{artifact_key}: remove skip
  - DELETE /projects/{project_id}/skip-preferences: clear all
  - GET /projects/{project_id}/skip-preferences: list skips

skillmeat/core/discovery.py
  - Integrate SkipPreferenceManager into ArtifactDiscoveryService.discover()

tests/core/test_skip_preferences.py (new)
  - Test SkipPreferenceManager CRUD, file handling, edge cases

tests/core/test_skip_integration.py (new)
  - Test skip integration with discovery
```

### Phase 2 Quality Gates

- [ ] Skip preference schema designed and approved
- [ ] SkipPreferenceManager CRUD operations functional
- [ ] Skip check integrated into discovery with <100ms overhead
- [ ] API endpoints working and authenticated
- [ ] Skip preferences persisted correctly to filesystem
- [ ] Performance validation: discovery <2.1s with skip checks
- [ ] Unit test coverage >80%
- [ ] Integration tests pass: skip workflow end-to-end
- [ ] Backward compatibility: existing projects work without skip preferences

### Phase 2 Deliverable

Skip preferences persisted on server via file-based storage. API endpoints available for managing skips. Discovery filters skipped artifacts automatically.

---

## Phase 3: Frontend - Type Updates & Form Integration

**Duration**: 2-3 days | **Status**: Not started | **Depends On**: Phase 1 ✓

**Objective**: Update frontend TypeScript types to match backend import status enum, implement skip checkbox UI in BulkImportModal, and integrate LocalStorage skip preference persistence.

**Runs In Parallel With**: Phase 2 (Backend skip) - can use mocked API while Phase 2 completes

### Phase 3 Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Status |
|---------|------|-------------|-------------------|----------|------------|--------|
| DIS-3.1 | Update discovery.ts Types | Change `ImportResult.success: boolean` to `status: "success" \| "skipped" \| "failed"`; add `skip_reason?: string` | (1) TypeScript compiles without errors; (2) All ImportResult usages updated; (3) Backward compat analysis (breaking change documented); (4) Types match backend schema | 0.5d | frontend-developer | pending |
| DIS-3.2 | Add Skip Preference Type | Create TypeScript interface for skip preferences: `{ project_id: string, artifact_key: string, skip_reason: string, added_date: string }[]` | (1) Type exported from discovery.ts; (2) Used in hooks; (3) Serializable to/from JSON | 0.5d | frontend-developer | pending |
| DIS-3.3 | Update BulkImportModal - Status Display | Display pre-scan status labels for each artifact: "Will add to Collection & Project", "Already in Collection, will add to Project", "Skipped (marked to skip)" | (1) Status labels render with appropriate styling; (2) Tooltips explain each status; (3) Color-coded badges; (4) Responsive layout | 1d | ui-engineer-enhanced | pending |
| DIS-3.4 | Add Skip Checkbox UI | Add per-artifact checkbox: "Don't show this in future discoveries"; checkbox disabled if already "skipped" | (1) Checkboxes render; (2) Checked state managed in component state; (3) UX clear (label, tooltip); (4) Accessibility: proper labels, screen reader support | 1d | ui-engineer-enhanced | pending |
| DIS-3.5 | Implement LocalStorage Skip Persistence | Create utility functions: `saveSkipPrefs(projectId, skipList)`, `loadSkipPrefs(projectId)`, `clearSkipPrefs(projectId, artifact_key?)` with key namespacing | (1) Functions serialize/deserialize JSON; (2) Keys namespaced: `skillmeat_skip_prefs_{project_id}`; (3) Handle localStorage unavailable gracefully; (4) Type-safe (TypeScript); (5) Unit tests | 1d | frontend-developer | pending |
| DIS-3.6 | Update useProjectDiscovery Hook | Integrate skip preference loading/saving: read skips on mount, apply to form, save on import | (1) Hook reads skip prefs from LocalStorage on mount; (2) Hook provides skip list state to components; (3) Hook saves skips after successful import; (4) Hook provides clear/update functions | 1d | frontend-developer | pending |
| DIS-3.7 | Update Import Form Submission | Collect skip list from checkboxes and send in request body as `skip_list: string[]` | (1) Form collects artifact keys marked to skip; (2) Skip list sent in POST /artifacts/discover/import request; (3) Error handling for network failures | 1d | frontend-developer | pending |
| DIS-3.8 | Unit Tests - Type Updates | Verify TypeScript types compile and match backend (status enum values, skip_reason, etc.) | (1) No TypeScript errors; (2) Type guards working; (3) Type narrowing correct | 0.5d | testing-specialist | pending |
| DIS-3.9 | Unit Tests - LocalStorage Skip Persistence | Test save/load/clear skip preferences with LocalStorage, including unavailability handling | (1) Save function writes JSON to LocalStorage; (2) Load function reads and deserializes; (3) Clear function removes keys; (4) Unavailability doesn't crash; (5) Coverage >80% | 1d | testing-specialist | pending |
| DIS-3.10 | Unit Tests - BulkImportModal | Test skip checkbox state management, form submission with skip list, status display | (1) Checkboxes toggle correctly; (2) Form submission includes skip list; (3) Status labels display; (4) Accessibility tests pass; (5) Coverage >80% | 1d | ui-engineer-enhanced | pending |
| DIS-3.11 | E2E Test - Skip Preference Persistence | Test skip checkbox checked → page reload → skip preferences remain (LocalStorage verified) | (1) Check skip checkbox; (2) Reload page; (3) Verify skip list in component state; (4) Verify localStorage key contains data | 1d | testing-specialist | pending |

### Phase 3 Key Files to Modify/Create

```
skillmeat/web/types/discovery.ts
  - ImportResult: status: "success" | "skipped" | "failed", skip_reason?: string
  - SkipPreference interface: project_id, artifact_key, skip_reason, added_date
  - Add type guards and union types for status

skillmeat/web/components/discovery/BulkImportModal.tsx
  - Add status labels for each artifact (display pre-scan status)
  - Add skip checkboxes per-artifact
  - Update form submission to collect skip list

skillmeat/web/lib/skip-preferences.ts (new)
  - saveSkipPrefs(projectId, skipList)
  - loadSkipPrefs(projectId)
  - clearSkipPrefs(projectId, artifactKey?)
  - Constants for LocalStorage key prefix

skillmeat/web/hooks/useProjectDiscovery.ts
  - Integrate skip preference loading on mount
  - Update import mutation to send skip list

skillmeat/web/__tests__/discovery-types.test.ts (new)
  - Type compilation tests
  - Type guard tests

skillmeat/web/__tests__/skip-preferences.test.ts (new)
  - LocalStorage persistence tests

skillmeat/web/__tests__/BulkImportModal.test.tsx (update)
  - Add tests for skip checkboxes, status display
```

### Phase 3 Quality Gates

- [ ] All ImportResult TypeScript usages compile without errors
- [ ] Status enum values match backend (success, skipped, failed)
- [ ] Skip preference types defined and exported
- [ ] BulkImportModal renders status labels correctly
- [ ] Skip checkboxes render and manage state
- [ ] LocalStorage skip persistence working (save/load/clear)
- [ ] Form submission includes skip_list in request
- [ ] Unit test coverage >80%
- [ ] E2E test passes: skip checkbox → page reload → skips persist
- [ ] Accessibility: skip checkboxes labeled, screen reader compatible

### Phase 3 Deliverable

Frontend types updated to match backend. Skip checkboxes integrated into BulkImportModal. LocalStorage persistence working for skip preferences across sessions.

---

## Phase 4: Frontend - Discovery Tab & UI Polish

**Duration**: 2-3 days | **Status**: Not started | **Depends On**: Phase 3 ✓

**Objective**: Create permanent Discovery Tab component on Project Detail page, update banner visibility logic for new statuses, polish toast notifications with detailed breakdowns, and integrate skip preference management UI.

### Phase 4 Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Status |
|---------|------|-------------|-------------------|----------|------------|--------|
| DIS-4.1 | Create DiscoveryTab Component | New React component showing all discovered artifacts in table/list format with columns: name, type, status, size, source, actions | (1) Component renders artifact list; (2) Shows artifact metadata (type, size, source); (3) Shows status badge with color coding; (4) Responsive layout; (5) Pagination/virtualization for large lists | 1.5d | ui-engineer-enhanced | pending |
| DIS-4.2 | Add Artifact Filtering & Sorting | Implement filters (by status: "success"/"skipped"/"failed", by type: "skill"/"command"/etc., by date range) and sort options | (1) Filter buttons/dropdowns visible; (2) Filters apply to table; (3) Sort by name, type, discovered_at; (4) Filtered state persists during session | 1d | ui-engineer-enhanced | pending |
| DIS-4.3 | Integrate DiscoveryTab into Project Detail | Add tab switcher on Project Detail page: "Deployed" | "Discovery"; route to tab via URL param (e.g., ?tab=discovery) | (1) Tabs visible and stylistically consistent; (2) Tab switching works; (3) URL param updates on tab click; (4) Tab state persists during session; (5) No layout shift | 1d | ui-engineer-enhanced | pending |
| DIS-4.4 | Update DiscoveryBanner Visibility Logic | Banner only shows if `importable_count > 0` (i.e., new artifacts available); banner hidden if all discovered artifacts already in Collection/Project | (1) Banner hidden when 0 new artifacts; (2) Banner shows only when truly new artifacts exist; (3) Tests validate banner visibility | 0.5d | ui-engineer-enhanced | pending |
| DIS-4.5 | Update Toast Utilities | Enhance `toast-utils.ts` to show detailed breakdown: "Imported to Collection: 3 | Added to Project: 5 | Skipped: 2" instead of just summary counts | (1) Toast accepts detailed breakdown from import result; (2) Toast displays multi-line summary; (3) Toast clickable link to open Notification Center; (4) Responsive layout | 1d | frontend-developer | pending |
| DIS-4.6 | Add Skip Management UI in Discovery Tab | Section in Discovery Tab to manage skip preferences: list of skipped artifacts with "Un-skip" buttons, "Clear all" button | (1) Skipped artifacts listed; (2) "Un-skip" button removes individual skip; (3) "Clear all" button removes all skips with confirmation; (4) Updates reflected immediately in artifact list | 1d | ui-engineer-enhanced | pending |
| DIS-4.7 | Add Artifact Actions Menu | Context menu for each artifact: "Import", "Skip for future", "View details", "Copy source" | (1) Actions visible on hover or click; (2) "Import" opens import confirmation; (3) "Skip for future" toggles skip checkbox; (4) Actions keyboard accessible | 0.5d | ui-engineer-enhanced | pending |
| DIS-4.8 | Unit Tests - DiscoveryTab Rendering | Test component renders with various artifact lists (empty, single, many), with filters and sorting | (1) Empty state displays; (2) Artifacts render; (3) Filters apply; (4) Sorts apply; (5) Coverage >80% | 1d | ui-engineer-enhanced | pending |
| DIS-4.9 | Unit Tests - Banner Visibility | Test banner shown only when importable_count > 0 | (1) Banner hidden when 0; (2) Banner visible when >0; (3) All combinations tested | 0.5d | testing-specialist | pending |
| DIS-4.10 | Unit Tests - Toast Utilities | Test toast utilities display detailed breakdown correctly | (1) Breakdown parsed and displayed; (2) Multi-line format correct; (3) Responsive | 0.5d | testing-specialist | pending |
| DIS-4.11 | E2E Test - Discovery Tab Navigation | Test Discovery Tab visible, clickable, shows artifacts, tab state persists via URL | (1) Tab visible on Project Detail; (2) Click tab navigates to tab; (3) URL updates; (4) Artifacts display; (5) Reload page, tab still selected | 1d | testing-specialist | pending |
| DIS-4.12 | E2E Test - Skip Management in Tab | Test skip artifact from tab → skip added → future discovery excludes it | (1) Click "Un-skip" on skipped artifact; (2) Artifact removed from skip list; (3) Future discovery includes artifact | 1d | testing-specialist | pending |

### Phase 4 Key Files to Modify/Create

```
skillmeat/web/components/discovery/DiscoveryTab.tsx (new)
  - Artifact table/list display with metadata, status badges
  - Filters (by status, type, date range)
  - Sort options
  - Pagination/virtualization

skillmeat/web/components/discovery/ArtifactActions.tsx (new)
  - Context menu with Import, Skip, View details, Copy source actions

skillmeat/web/components/discovery/SkipPreferencesList.tsx (new)
  - List of skipped artifacts
  - Un-skip buttons
  - Clear all button with confirmation

skillmeat/web/app/projects/[id]/page.tsx
  - Add tab switcher for Deployed | Discovery tabs
  - Integrate DiscoveryTab

skillmeat/web/components/discovery/DiscoveryBanner.tsx
  - Update visibility logic: only show if importable_count > 0

skillmeat/web/lib/toast-utils.ts
  - Update toast functions to accept and display detailed breakdown

skillmeat/web/__tests__/DiscoveryTab.test.tsx (new)
  - Tests for rendering, filtering, sorting

skillmeat/web/__tests__/toast-utils.test.ts (update)
  - Tests for detailed breakdown display
```

### Phase 4 Quality Gates

- [ ] DiscoveryTab component renders correctly with various data sets
- [ ] Artifact filters and sorting functional
- [ ] Tab switcher integrated into Project Detail, tab state persists
- [ ] Banner only shows when importable_count > 0 (no false positives)
- [ ] Toast utilities display detailed breakdown with counts
- [ ] Skip management UI in tab functional (Un-skip, Clear all)
- [ ] Artifact actions menu keyboard accessible
- [ ] Unit test coverage >80%
- [ ] E2E tests pass: tab navigation, skip management
- [ ] Visual design consistent with existing UI (colors, spacing, typography)

### Phase 4 Deliverable

Discovery Tab component fully functional on Project Detail page. Banner visibility logic updated. Toast notifications show detailed import breakdown. Skip preference management accessible from tab.

---

## Phase 5: Integration & End-to-End Testing

**Duration**: 2-3 days | **Status**: Not started | **Depends On**: Phase 2 ✓, Phase 3 ✓, Phase 4 ✓

**Objective**: Test complete discovery → pre-scan → import → notification flow; verify Notification System integration; performance validation; accessibility audit; and documentation updates.

### Phase 5 Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Status |
|---------|------|-------------|-------------------|----------|------------|--------|
| DIS-5.1 | Integration Test - Full Discovery Flow | Test end-to-end: project discovery → pre-scan checks → filtered results → user imports → notification shows breakdown | (1) Discovery endpoint called; (2) Pre-scan filters correctly; (3) Import mutations execute; (4) Notification created with detailed breakdown; (5) All state consistent | 1.5d | testing-specialist | pending |
| DIS-5.2 | Notification System Integration | Verify Notification System consumes new ImportResult.status enum; test notification displays skip reasons and per-location counts | (1) Notification created for import; (2) Notification shows "Imported": N, "Skipped": N, "Failed": N; (3) Skip reasons visible; (4) Notification persists in center | 1d | testing-specialist | pending |
| DIS-5.3 | Performance Validation - Discovery <2s | Benchmark discovery scan with pre-scan checks; verify <2 seconds on typical project (500 Collection, 200 Project artifacts) | (1) Benchmark run on test project; (2) Time measured and logged; (3) <2 seconds achieved; (4) Optimizations applied if needed (caching, indexing) | 1d | testing-specialist | pending |
| DIS-5.4 | E2E Test - Full Skip Workflow | Test: discovery → mark skip checkboxes → import with skips → verify skip prefs saved → future discovery excludes skipped | (1) Skip checkboxes marked; (2) Skip list sent in import request; (3) Skip prefs persisted to LocalStorage; (4) Future discovery filters skipped; (5) All state consistent | 1d | testing-specialist | pending |
| DIS-5.5 | E2E Test - Discovery Tab Interactions | Test: navigate to Discovery Tab → view artifacts → filter/sort → manage skips → re-scan → tab updated | (1) Tab displays correctly; (2) Filters/sorts work; (3) Skips managed; (4) Re-scan updates tab; (5) Tab state consistent | 1d | testing-specialist | pending |
| DIS-5.6 | Accessibility Audit - Discovery Tab | Audit Discovery Tab and related components: keyboard navigation (Tab, Enter, Arrow keys), screen reader compatibility, ARIA labels | (1) All interactive elements keyboard accessible; (2) Tab order logical; (3) Screen reader announces all text and states; (4) ARIA labels present for icons/badges; (5) Color not only indicator of state | 1d | web-accessibility-checker | pending |
| DIS-5.7 | Accessibility Audit - Skip Checkboxes | Verify skip checkboxes properly labeled, associated with artifact info, keyboard accessible | (1) `<label for>` associations correct; (2) Keyboard navigation works; (3) Screen reader announces checkbox state; (4) Focus visible | 0.5d | web-accessibility-checker | pending |
| DIS-5.8 | Load Test - Large Project Discovery | Test discovery on large project (500+ artifacts in Collection, 300+ in Project) with skip preferences | (1) Discovery completes successfully; (2) <2 seconds (or optimized); (3) All artifacts processed; (4) No memory leaks; (5) UI remains responsive | 1d | testing-specialist | pending |
| DIS-5.9 | Cross-browser Testing | Test LocalStorage persistence and UI rendering on Chrome, Firefox, Safari (focus on skip persistence) | (1) LocalStorage working on all browsers; (2) UI renders consistently; (3) Toast notifications display; (4) Tabs functional | 0.5d | testing-specialist | pending |
| DIS-5.10 | Error Handling & Edge Cases | Test error scenarios: network failure during import, corrupted skip prefs file, project directory missing, permission denied | (1) Network error: graceful fallback, user notified; (2) Corrupted file: skipped gracefully, user warned; (3) Missing project: error message clear; (4) Permission denied: retry or abort with message | 1d | testing-specialist | pending |
| DIS-5.11 | Notification System Detail Breakdown | Update Notification to show: "Imported to Collection: 3 | Added to Project: 5 | Skipped: 2" with click-through to see per-artifact details | (1) Notification shows summary; (2) Click shows detail list; (3) Skip reasons visible in detail; (4) Styling consistent with Notification System design | 1d | frontend-developer | pending |
| DIS-5.12 | API Documentation - OpenAPI Update | Update OpenAPI schema documentation for new ImportResult status enum, skip preferences endpoints, and DiscoveryResult filtering | (1) OpenAPI schema accurate; (2) Examples include new status enum values; (3) Skip reason field documented; (4) Endpoint descriptions updated | 0.5d | documentation-writer | pending |

### Phase 5 Key Files to Modify/Create

```
tests/e2e/discovery-full-workflow.spec.ts (new)
  - End-to-end: discovery → import → notification

tests/e2e/skip-workflow.spec.ts (new)
  - End-to-end: mark skip → import → future discovery

tests/integration/test_discovery_import_notification.py (new)
  - Integration: backend discovery → import → notification integration

skillmeat/web/components/notifications/NotificationItem.tsx (update)
  - Display detailed breakdown for import notifications

skillmeat/web/lib/toast-utils.ts (update)
  - Toast shows detailed breakdown with click-through

docs/dev/api/openapi-updated.json (generated)
  - Updated OpenAPI schema with new types
```

### Phase 5 Quality Gates

- [ ] End-to-end discovery → import → notification flow completes without errors
- [ ] Notification System displays new status enum values correctly
- [ ] Skip preferences persist across all browsers (LocalStorage validated)
- [ ] Performance: discovery <2 seconds on typical project
- [ ] Load test passes: 500+ artifacts handled smoothly
- [ ] Accessibility: Discovery Tab keyboard navigable, screen reader compatible
- [ ] Skip checkboxes labeled and accessible
- [ ] Error handling: network failures, corrupted files, missing directories handled gracefully
- [ ] All E2E tests pass: skip workflow, tab interactions, discovery filtering
- [ ] OpenAPI documentation updated and accurate

### Phase 5 Deliverable

Full end-to-end workflow tested and validated. Notification System integration complete. Performance and accessibility meet requirements. All documentation updated.

---

## Phase 6: Monitoring, Optimization & Release

**Duration**: 1-2 days | **Status**: Not started | **Depends On**: Phase 5 ✓

**Objective**: Add analytics tracking, observability, performance optimization if needed, final bug fixes, and release preparation.

### Phase 6 Task Breakdown

| Task ID | Name | Description | Acceptance Criteria | Estimate | Assigned To | Status |
|---------|------|-------------|-------------------|----------|------------|--------|
| DIS-6.1 | Analytics Tracking - UI Interactions | Add event tracking: skip checkbox clicks, Discovery Tab views, filter/sort actions, "Un-skip" clicks | (1) Analytics client called for each event; (2) Event names consistent; (3) Project ID and artifact key included; (4) No PII collected | 1d | frontend-developer | pending |
| DIS-6.2 | Analytics Tracking - Backend | Add metrics: discovery pre-scan hit rate, skip adoption rate, import status distribution (success/skipped/failed) | (1) Metrics logged on each discovery/import; (2) Aggregate metrics available; (3) Dashboard can display trends | 1d | python-backend-engineer | pending |
| DIS-6.3 | Logging & Observability | Add structured logging: import status determination, skip preference operations, pre-scan check results with trace_id for debugging | (1) Log statements include trace_id; (2) Logs include project_id, artifact_key, status; (3) Appropriate log levels (info, warn, error) | 0.5d | python-backend-engineer | pending |
| DIS-6.4 | Performance Optimization - If Needed | If Phase 5 benchmark shows >2 seconds, implement optimizations: artifact list caching, index on Collection manifest, parallel pre-scan checks | (1) Profiling identifies bottleneck; (2) Optimization applied; (3) Benchmark <2 seconds; (4) Regression tests pass | 1d | python-backend-engineer | pending |
| DIS-6.5 | Bug Fixes & Edge Cases | Fix any reported issues from testing phases; polish UI (spacing, colors, hover states, error messages) | (1) All critical bugs fixed; (2) UI polish applied; (3) Error messages clear and actionable; (4) Regression tests pass | 1d | ui-engineer-enhanced | pending |
| DIS-6.6 | User Guide - "Understanding Import Status" | Create user-facing documentation explaining new status enum: what "Skipped" means, when artifacts are skipped, how to un-skip | (1) Guide written in plain language; (2) Examples provided; (3) Includes screenshots; (4) Linked from UI tooltips; (5) Integrated into help system | 1d | documentation-writer | pending |
| DIS-6.7 | User Guide - Skip Preferences | Document skip preference feature: how to skip artifacts, how to un-skip, LocalStorage limitation (client-side only) | (1) Feature explanation clear; (2) Step-by-step instructions; (3) Limitation clearly stated; (4) Workaround for multi-device (export/sync future feature noted) | 0.5d | documentation-writer | pending |
| DIS-6.8 | API Documentation - Status Enum Values | Document each ImportResult.status value (success, skipped, failed) with examples and skip_reason meanings | (1) Enum values explained; (2) skip_reason examples for each scenario; (3) Integration examples (Notification System); (4) Breaking changes documented | 0.5d | documentation-writer | pending |
| DIS-6.9 | Release Notes & Migration Guide | Prepare release notes: new features, breaking changes (status enum replaces boolean success), deprecations (none) | (1) Release notes written; (2) Breaking changes clearly marked; (3) Migration guide for API consumers; (4) Upgrade instructions | 0.5d | documentation-writer | pending |
| DIS-6.10 | Feature Flag - Discovery Tab | Add feature flag `ENABLE_DISCOVERY_TAB` (default: true after Phase completion) to allow gradual rollout | (1) Flag added to frontend config; (2) Tab hidden if flag false; (3) Flag can be toggled via settings/admin | 0.5d | frontend-developer | pending |
| DIS-6.11 | Feature Flag - Skip Preferences | Add feature flag `ENABLE_SKIP_PREFERENCES` (default: true after Phase completion) to allow gradual rollout | (1) Flag added to frontend config; (2) Skip checkboxes hidden if flag false; (3) Skip endpoints available but skip filtering disabled if flag false | 0.5d | python-backend-engineer | pending |
| DIS-6.12 | Final QA & Smoke Tests | Run final comprehensive smoke tests: discovery works, import works, skip works, notifications show, no regressions | (1) Smoke test suite passes; (2) No new bugs introduced; (3) Performance acceptable; (4) Documentation complete | 1d | testing-specialist | pending |

### Phase 6 Key Files to Modify/Create

```
skillmeat/web/lib/analytics.ts
  - trackSkipCheckboxClick(projectId, artifactKey)
  - trackDiscoveryTabView(projectId)
  - trackFilterApplied(projectId, filterType)

skillmeat/core/discovery.py
  - Add metrics logging: pre-scan hit rate, skip adoption

skillmeat/api/config.py
  - Add feature flags: ENABLE_DISCOVERY_TAB, ENABLE_SKIP_PREFERENCES

docs/user/guides/understanding-import-status.md (new)
  - User guide for import status enum

docs/user/guides/skip-preferences-guide.md (new)
  - User guide for skip preferences

docs/dev/api/status-enum-reference.md (new)
  - API reference for status enum values

docs/RELEASE-NOTES-v1.1.0.md (new)
  - Release notes with new features, breaking changes

tests/smoke/discovery-smoke-tests.py (new)
  - Smoke test suite for full workflow
```

### Phase 6 Quality Gates

- [ ] Analytics events tracked for all UI interactions
- [ ] Backend metrics logged for discovery and import operations
- [ ] Performance optimization complete (if needed): <2 seconds
- [ ] All bugs fixed and UI polished
- [ ] User guides written and integrated
- [ ] API documentation complete
- [ ] Release notes and migration guide prepared
- [ ] Feature flags implemented and tested
- [ ] Final smoke tests pass: no regressions
- [ ] Release ready for production deployment

### Phase 6 Deliverable

Feature ready for production release. Analytics and monitoring in place. Documentation complete. Feature flags enable gradual rollout.

---

## Orchestration & Parallelization Strategy

### Critical Path Analysis

```
Phase 1 (Backend Schema & Pre-scan)
  └─ 2-3 days (CRITICAL PATH - blocks all others)

    Phase 2 (Backend Skip)    Phase 3 (Frontend Types)
    └─ 2-3 days              └─ 2-3 days
       (parallel)               (parallel)
       ↓                        ↓
       Phase 4 (Discovery Tab)
       └─ 2-3 days

         ↓

         Phase 5 (Integration & Testing)
         └─ 2-3 days

           ↓

           Phase 6 (Monitoring & Release)
           └─ 1-2 days
```

### Batch Execution Schedule

**Batch 1: Phase 1 - Backend Foundation**
- **Duration**: 2-3 days
- **Lead Agents**: `data-layer-expert`, `python-backend-engineer`
- **Tasks**: DIS-1.1 through DIS-1.9
- **Deliverable**: Import status enum, pre-scan logic, unit & integration tests
- **Success Criteria**: All Phase 1 quality gates pass; ready for Phase 2 & 3

**Batch 2: Phase 2 + Phase 3 (Parallel)**
- **Duration**: 2-3 days
- **Backend Track** (Phase 2):
  - Lead Agents: `python-backend-engineer`, `testing-specialist`
  - Tasks: DIS-2.1 through DIS-2.9
  - Deliverable: Skip preference persistence, API endpoints
- **Frontend Track** (Phase 3):
  - Lead Agents: `ui-engineer-enhanced`, `frontend-developer`, `testing-specialist`
  - Tasks: DIS-3.1 through DIS-3.11
  - Deliverable: Type updates, skip checkboxes, LocalStorage persistence
- **Coordination**: Frontend can mock Phase 2 endpoints; both tracks merge code after Phase 1 completion
- **Success Criteria**: Both Phase 2 and Phase 3 quality gates pass; ready for Phase 4

**Batch 3: Phase 4 + Phase 5 Start**
- **Duration**: 2-3 days
- **Phase 4** (Discovery Tab):
  - Lead Agents: `ui-engineer-enhanced`
  - Tasks: DIS-4.1 through DIS-4.12
  - Deliverable: Discovery Tab component, banner updates, toast utilities, skip management UI
- **Phase 5 Start** (Parallel in last 1 day):
  - Lead Agents: `testing-specialist`, `web-accessibility-checker`
  - Tasks: DIS-5.1 through DIS-5.12 (start early integration tests)
  - Deliverable: Integration tests, accessibility audit baseline
- **Success Criteria**: Phase 4 quality gates pass; Phase 5 integration tests in progress

**Batch 4: Phase 5 Completion + Phase 6**
- **Duration**: 2-3 days
- **Phase 5** (Complete):
  - Lead Agents: `testing-specialist`, `web-accessibility-checker`, `documentation-writer`
  - Tasks: Finish DIS-5.1 through DIS-5.12
  - Deliverable: Full E2E tests, accessibility audit, documentation
- **Phase 6**:
  - Lead Agents: `python-backend-engineer`, `frontend-developer`, `documentation-writer`
  - Tasks: DIS-6.1 through DIS-6.12
  - Deliverable: Analytics, logging, performance optimization, release notes
- **Success Criteria**: All Phase 6 quality gates pass; ready for production release

### Total Timeline

- **Best Case**: 8-10 days (Phases 2-3 perfectly parallelized, Phase 4-5 overlap minimal delay)
- **Realistic Case**: 12-14 days (with integration and testing delays, some sequential work)
- **Conservative Case**: 16-18 days (with performance optimization, extensive testing, documentation review)

### Key Coordination Points

| Checkpoint | Date | Stakeholders | Decision |
|------------|------|--------------|----------|
| Phase 1 Complete | Day 2-3 | Opus, Phase 1 agents | Approve schema changes; begin Phase 2 & 3 |
| Phase 2 & 3 Parallel Start | Day 3-4 | Opus, Phase 2 & 3 agents | Phase 3 can mock Phase 2 endpoints |
| Phase 2 & 3 Complete | Day 5-6 | Opus, all agents | Merge code; begin Phase 4 |
| Phase 4 Complete | Day 7-9 | Opus, Phase 4 agents | Begin Phase 5 integration tests |
| Phase 5 & 6 Complete | Day 9-14 | Opus, all agents | Release readiness review |
| Release | Day 14-16 | Opus, DevOps | Deploy to production |

---

## Subagent Assignment Reference

### Phase 1: Backend Schema & Pre-scan

- **data-layer-expert**: DIS-1.1 (ImportResult schema), DIS-1.5 (BulkImportResult), DIS-1.6 (response models)
- **python-backend-engineer**: DIS-1.2 (pre-scan check), DIS-1.3 (discovery service), DIS-1.4 (status mapping)
- **backend-architect**: DIS-1.6 (API response models)
- **testing-specialist**: DIS-1.7, DIS-1.8, DIS-1.9 (unit & integration tests)

### Phase 2: Backend Skip Persistence

- **backend-architect**: DIS-2.1 (schema design)
- **python-backend-engineer**: DIS-2.2 (SkipPreferenceManager), DIS-2.3 (discovery integration), DIS-2.4 (API endpoints)
- **data-layer-expert**: DIS-2.5 (BulkImportRequest), DIS-2.6 (BulkImportResult)
- **testing-specialist**: DIS-2.7, DIS-2.8, DIS-2.9 (unit & integration tests)

### Phase 3: Frontend Type Updates & Form Integration

- **frontend-developer**: DIS-3.1, DIS-3.2 (types), DIS-3.5, DIS-3.6 (skip persistence), DIS-3.7 (form submission)
- **ui-engineer-enhanced**: DIS-3.3 (status display), DIS-3.4 (skip checkbox UI), DIS-3.10 (unit tests)
- **testing-specialist**: DIS-3.8, DIS-3.9, DIS-3.11 (unit & E2E tests)

### Phase 4: Frontend Discovery Tab & UI Polish

- **ui-engineer-enhanced**: DIS-4.1 (DiscoveryTab), DIS-4.2 (filters/sort), DIS-4.3 (tab integration), DIS-4.4 (banner visibility), DIS-4.6 (skip management UI), DIS-4.7 (artifact actions), DIS-4.8, DIS-4.12 (unit & E2E tests)
- **frontend-developer**: DIS-4.5 (toast utilities), DIS-4.11 (E2E navigation)
- **testing-specialist**: DIS-4.9, DIS-4.10 (unit tests)

### Phase 5: Integration & End-to-End Testing

- **testing-specialist**: DIS-5.1, DIS-5.2, DIS-5.3, DIS-5.4, DIS-5.5, DIS-5.8, DIS-5.9, DIS-5.10, DIS-5.12 (integration & E2E tests, performance, load, cross-browser, error handling, QA)
- **web-accessibility-checker**: DIS-5.6, DIS-5.7 (accessibility audit)
- **frontend-developer**: DIS-5.11 (notification detail breakdown)
- **documentation-writer**: DIS-5.12 (OpenAPI documentation)

### Phase 6: Monitoring, Optimization & Release

- **frontend-developer**: DIS-6.1 (UI analytics), DIS-6.10 (feature flag frontend)
- **python-backend-engineer**: DIS-6.2 (backend analytics), DIS-6.3 (logging), DIS-6.4 (optimization), DIS-6.11 (feature flag backend)
- **ui-engineer-enhanced**: DIS-6.5 (bug fixes & polish)
- **documentation-writer**: DIS-6.6, DIS-6.7, DIS-6.8, DIS-6.9 (user guides, API docs, release notes)
- **testing-specialist**: DIS-6.12 (smoke tests)

---

## Risk Assessment & Mitigation

| Risk | Impact | Likelihood | Mitigation | Owner |
|------|--------|-----------|-----------|-------|
| Pre-scan performance >2 seconds | High | Medium | Benchmark early in Phase 1; implement caching if needed; use lazy-loading for large lists | python-backend-engineer |
| Skip preferences lost across devices | Medium | Low | Document LocalStorage limitation in UX; add tooltip "Skips saved locally on this device"; plan server-sync in future release | frontend-developer |
| Partial import failure corrupts state | High | Low | Transaction-like semantics: all-or-nothing import; rollback on any artifact failure; test with corrupted artifacts | python-backend-engineer |
| Discovery Tab UI clutters Project Detail | Medium | Medium | Integrate as tab, not permanent component; hide if no discovered artifacts; keep adjacent to existing tabs | ui-engineer-enhanced |
| User confusion with new statuses | High | Medium | UX: clear labels "Skipped: already in Collection" + tooltips; user guide in help docs; in-app guidance | documentation-writer, ui-engineer-enhanced |
| Backward compatibility broken for API consumers | High | Low | Document breaking changes clearly; provide migration guide; deprecation window (if applicable) | backend-architect |
| Skip preference file corruption | Medium | Low | Validation on load; atomic writes; fallback to empty skip list on error | python-backend-engineer |
| Notification System doesn't receive new enum values | High | Low | Test integration early in Phase 5; coordinate with Notification System owner; verify schema compatibility | testing-specialist |
| E2E test flakiness | Medium | Medium | Use explicit waits; mock datetime for deterministic tests; cross-browser testing on different environments | testing-specialist |
| TypeScript type mismatches between frontend & backend | Medium | Low | Use generated SDK from OpenAPI; validate types match; run type checks in CI/CD | frontend-developer |
| Accessibility failures | High | Medium | Audit early (Phase 4); use accessibility checker tool; cross-test with screen readers; keyboard navigation | web-accessibility-checker |

---

## Quality Gates Checklist

### Per-Phase Quality Gates

- [ ] **Phase 1**: Schema changes verified, pre-scan tests pass, integration tests pass
- [ ] **Phase 2**: Skip preferences persisted, API endpoints working, backend tests pass
- [ ] **Phase 3**: Types updated, LocalStorage persists, frontend tests pass
- [ ] **Phase 4**: Discovery Tab renders, banner visibility correct, UI polish complete
- [ ] **Phase 5**: Full workflow tested, accessibility audit passed, documentation complete
- [ ] **Phase 6**: Analytics logged, performance meets <2s, release notes ready, no regressions

### Overall Quality Checklist

- [ ] All tests pass (unit, integration, E2E, accessibility)
- [ ] Code coverage >80% for critical paths
- [ ] Performance validation: discovery <2 seconds
- [ ] No TypeScript errors
- [ ] API documentation up-to-date
- [ ] User documentation complete
- [ ] Feature flags implemented and tested
- [ ] Breaking changes documented
- [ ] Notification System integration verified
- [ ] Cross-browser testing passed
- [ ] Accessibility audit passed
- [ ] No data loss or corruption scenarios
- [ ] Error handling comprehensive
- [ ] Analytics logging in place
- [ ] Observability metrics available

---

## Key Decisions & Dependencies

### Architectural Decisions

1. **Skip Preferences Storage (Phase 2)**
   - Decision: File-based storage (`.claude/.skillmeat_skip_prefs.toml`), not database
   - Rationale: Aligns with current artifact storage model; no schema migration needed
   - Alternative: Server-side skip list stored in manifest (future enhancement)

2. **Import Status Enum (Phase 1)**
   - Decision: Three values (success, skipped, failed) with optional skip_reason
   - Rationale: Covers all import scenarios; extensible for future status types
   - Alternative: Richer enum (success_collection, success_project, skipped_collection_exists, skipped_project_exists) → too granular for MVP

3. **LocalStorage for Skip Preferences (Phase 3)**
   - Decision: Client-side only for MVP; no server sync
   - Rationale: Simpler implementation; skips are user preference, not critical data
   - Limitation: Skips lost across devices; documented in UX
   - Future: Server-side sync with device-specific overrides

4. **Discovery Tab as Permanent Component (Phase 4)**
   - Decision: Tab switcher on Project Detail (Deployed | Discovery)
   - Rationale: Permanent access to discovered artifacts; tab state persists via URL param
   - Alternative: Modal → less discoverable; no persistent access

5. **Toast Notification Breakdown (Phase 4-5)**
   - Decision: Multi-line toast with summary counts; click-through to Notification Center for details
   - Rationale: Balances UX (quick summary) with clarity (detailed view available)
   - Alternative: Inline expanded notification → clutters UI

### External Dependencies

- **Notification System**: Phase 5-6 complete; integration for detail breakdown
- **TanStack Query**: Already integrated; used for discovery state management
- **Radix UI + shadcn**: Existing component library; used for tab switcher, modal components
- **Toast Utils**: Existing implementation; enhanced in Phase 4

### Internal Dependencies

- **ArtifactDiscoveryService** (skillmeat/core/discovery.py): Enhanced with pre-scan logic
- **ArtifactImporter** (skillmeat/core/importer.py): Enhanced with status enum logic
- **Project Detail Page** (skillmeat/web/app/projects/[id]/page.tsx): Extended with Discovery Tab

---

## Success Metrics & Observability

### Success Criteria

1. **Discovery Accuracy**: 95%+ of shown artifacts are truly new (pre-scan filtering working)
2. **Skip Adoption**: 40%+ of users utilize skip checkbox within first month
3. **Banner False Positives**: 0% (no banner shown when all artifacts already exist)
4. **Import Status Clarity**: Users report understanding import outcomes (survey/feedback)
5. **Discovery Tab Usage**: 50%+ of users navigate to tab at least once
6. **Skip Persistence**: 95%+ of skips survive browser restart (LocalStorage verified)
7. **Performance**: Discovery scan <2 seconds on typical project
8. **Accessibility**: No critical accessibility violations (WCAG AA)

### Key Metrics to Track

| Metric | How to Track | Target |
|--------|-------------|--------|
| Discovery pre-scan hit rate | Backend logs: artifacts_filtered / artifacts_discovered | >95% accuracy |
| Skip adoption rate | Analytics: users_with_skip_prefs / total_users | >40% within month 1 |
| Import status distribution | Metrics: success_count, skipped_count, failed_count | skipped_count > 0 (validates new enum) |
| Discovery Tab usage | Analytics: discovery_tab_views / project_detail_views | >50% |
| Performance: discovery time | Benchmark: duration_ms in discovery endpoint log | <2000ms |
| Skip persistence | E2E test: LocalStorage survives page reload | 95%+ pass rate |
| Toast engagement | Analytics: toast_clicks_to_detail / toasts_shown | >30% |

---

## Documentation Deliverables

### User-Facing Documentation

1. **User Guide: "Understanding Import Status"** (Phase 6)
   - Explanation of success, skipped, and failed statuses
   - When artifacts are skipped (already in Collection vs Project)
   - How to re-import skipped artifacts

2. **User Guide: Skip Preferences** (Phase 6)
   - How to mark artifacts to skip in future discoveries
   - How to un-skip artifacts
   - LocalStorage limitation (client-side only)
   - Workaround: clear skips or export/sync (future feature)

### Developer-Facing Documentation

1. **API Reference: Import Status Enum** (Phase 6)
   - Enum values: success, skipped, failed
   - skip_reason field: when populated and possible values
   - Per-location import counts in BulkImportResult

2. **Architecture Guide: Pre-scan Intelligence** (Phase 1)
   - How pre-scan checks Collection and Project
   - Performance implications and optimizations

3. **Integration Guide: Notification System** (Phase 5)
   - How Notification System consumes new status enum
   - Detail breakdown format and display

### Release Documentation

1. **Release Notes** (Phase 6)
   - New features: status enum, skip preferences, Discovery Tab
   - Breaking changes: ImportResult.success → ImportResult.status
   - Migration guide for API consumers

2. **Deployment Guide** (Phase 6)
   - Feature flags: ENABLE_DISCOVERY_TAB, ENABLE_SKIP_PREFERENCES
   - Database migrations (if any)
   - Configuration changes

---

## Files to be Created/Modified Summary

### Backend Files (Python)

**New Files**:
- `skillmeat/core/skip_preferences.py` - SkipPreferenceManager class
- `tests/core/test_skip_preferences.py` - Skip manager unit tests
- `tests/core/test_skip_integration.py` - Skip integration tests
- `tests/core/test_discovery_prescan.py` - Pre-scan unit tests
- `tests/core/test_import_status_enum.py` - Status enum unit tests
- `tests/integration/test_discovery_import_notification.py` - Full workflow integration
- `tests/e2e/discovery_full_workflow.spec.ts` - E2E tests (or .py)

**Modified Files**:
- `skillmeat/api/schemas/discovery.py` - ImportResult (status enum + skip_reason), BulkImportResult (skipped_count)
- `skillmeat/core/discovery.py` - Pre-scan logic, skip preference check
- `skillmeat/core/importer.py` - Status mapping logic
- `skillmeat/api/routers/artifacts.py` - Updated endpoints, new skip endpoints
- `skillmeat/api/config.py` - Feature flags for Discovery Tab and Skip Preferences

### Frontend Files (TypeScript/React)

**New Files**:
- `skillmeat/web/components/discovery/DiscoveryTab.tsx` - Discovery Tab component
- `skillmeat/web/components/discovery/ArtifactActions.tsx` - Artifact context menu
- `skillmeat/web/components/discovery/SkipPreferencesList.tsx` - Skip management UI
- `skillmeat/web/lib/skip-preferences.ts` - LocalStorage persistence utilities
- `skillmeat/web/__tests__/discovery-types.test.ts` - Type validation tests
- `skillmeat/web/__tests__/skip-preferences.test.ts` - LocalStorage tests
- `skillmeat/web/__tests__/DiscoveryTab.test.tsx` - Component tests
- `skillmeat/web/__tests__/toast-utils.test.ts` - Toast utility tests
- `skillmeat/web/tests/discovery-full-workflow.spec.ts` - E2E workflow
- `skillmeat/web/tests/skip-workflow.spec.ts` - E2E skip workflow

**Modified Files**:
- `skillmeat/web/types/discovery.ts` - ImportResult (status enum), SkipPreference interface
- `skillmeat/web/components/discovery/BulkImportModal.tsx` - Status display, skip checkboxes
- `skillmeat/web/hooks/useProjectDiscovery.ts` - Skip preference integration
- `skillmeat/web/components/discovery/DiscoveryBanner.tsx` - Banner visibility logic
- `skillmeat/web/lib/toast-utils.ts` - Detailed breakdown format
- `skillmeat/web/app/projects/[id]/page.tsx` - Tab switcher integration
- `skillmeat/web/components/notifications/NotificationItem.tsx` - Detail breakdown display

### Documentation Files

**New Files**:
- `docs/user/guides/understanding-import-status.md` - User guide for status enum
- `docs/user/guides/skip-preferences-guide.md` - User guide for skip feature
- `docs/dev/api/status-enum-reference.md` - API reference for status enum
- `docs/RELEASE-NOTES-v1.1.0.md` - Release notes

---

## Next Steps for Orchestrator

1. **Approve Implementation Plan**: Review and sign off on task breakdown, timelines, and quality gates
2. **Begin Phase 1**: Delegate to `data-layer-expert` and `python-backend-engineer` for schema changes and pre-scan logic
3. **Monitor Progress**: Track Phase 1 completion; begin Phase 2 & 3 in parallel upon completion
4. **Coordinate Phases**: Manage Phase 2-3 parallelization; ensure code merges smoothly
5. **Final QA**: Run comprehensive smoke tests before Phase 6 release

---

**Document Status**: Ready for implementation | **Last Reviewed**: 2025-12-04 | **Next Review**: After Phase 1 completion
