---
title: "Implementation Plan: Marketplace Source Detection Improvements"
description: "Detailed implementation plan for manual source mapping and auto-detection deduplication features"
author: "Claude Code (Implementation Planning Orchestrator)"
date: 2026-01-05
status: "active"
complexity: "Medium (M)"
estimated_effort: "55-70 story points"
estimated_timeline: "4-5 weeks"
---

# Implementation Plan: Marketplace Source Detection Improvements

**Feature:** Marketplace Source Detection Improvements (Manual Mapping + Auto-Deduplication)

**PRD:** `/docs/project_plans/PRDs/features/marketplace-source-detection-improvements-v1.md`

**Complexity:** Medium (M) - 55-70 story points, 4-5 weeks

**Team:** Backend (Python) + Frontend (React/TypeScript) + QA

---

## Executive Summary

This implementation plan provides detailed task breakdowns across 5 phases to deliver two critical marketplace source detection enhancements:

1. **Manual Source Mapping** - Enable users to explicitly map directories to artifact types via a modal UI, persisted in the database and applied during detection with 90+ confidence scoring.

2. **Auto-detection Deduplication** - Eliminate duplicate artifacts using SHA256 content hashing, with within-source dedup and cross-source matching against existing collection artifacts.

The plan follows MeatyPrompts layered architecture, with clear dependencies, quality gates, and rollback procedures. Estimated delivery: 4-5 weeks with parallel phase execution where possible.

---

## Architecture Overview

### Current State

**Detection System Files:**
- `skillmeat/core/marketplace/github_scanner.py` - GitHub API scanning and tree traversal
- `skillmeat/core/marketplace/heuristic_detector.py` - Confidence scoring (0-100)
- `skillmeat/core/marketplace/diff_engine.py` - Status tracking (new/updated/removed)
- `skillmeat/core/marketplace/import_coordinator.py` - Import orchestration

**Database Models:**
- `skillmeat/cache/models.py` (Line 1173) - `MarketplaceSource` with existing `manual_map` JSON column
- `skillmeat/cache/models.py` (Line 1368) - `MarketplaceCatalogEntry` with `confidence_score`, `excluded_at`, `excluded_reason`

**API Layer:**
- `skillmeat/api/routers/marketplace_sources.py` - 21 endpoints for source management
- `skillmeat/api/schemas/marketplace.py` - Request/response models
- Existing endpoint: `PATCH /marketplace/sources/{id}` for updates

**Frontend:**
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Source detail page
- `skillmeat/web/components/source-toolbar.tsx` - Toolbar (will add "Map Directories" button)
- `skillmeat/web/types/marketplace.ts` - TypeScript types
- Hooks: `useSource()`, `useSourceCatalog()`, `useRescanSource()`

### MeatyPrompts Layered Architecture Alignment

```
Phase 1: Database & Schema (Foundation)
    ↓
Phase 2: Backend Detection Engine (Service Layer)
    ├── Heuristic detector modifications
    └── Deduplication engine
    ↓
Phase 3: API Layer (Router/Schema updates)
    └── PATCH endpoint updates
    └── Rescan endpoint updates
    ↓
Phase 4: Frontend UI (Presentation Layer)
    ├── DirectoryMapModal component
    ├── Source detail updates
    └── Notification system
    ↓
Phase 5: Testing & Documentation (Quality & Deployment)
    ├── Integration tests
    ├── E2E tests
    └── User/developer docs
```

---

## Phase 1: Database & Schema (1 day, 5-8 points)

**Duration:** 1 day
**Story Points:** 5-8
**Assigned To:** `data-layer-expert`

### Overview

Validate existing database schema and confirm no migrations are needed. Add documentation for extended usage of existing columns (`manual_map`, `metadata_json`). Create validation schemas for API layer.

### Tasks

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P1.1 | Validate manual_map column | Confirm MarketplaceSource.manual_map (Text field) exists and is usable for JSON storage | `manual_map` column exists, nullable, can store JSON; type system verified | 2 |
| P1.2 | Validate metadata_json column | Confirm MarketplaceCatalogEntry has metadata_json for content_hash storage | `metadata_json` column exists/usable; can store JSON objects | 2 |
| P1.3 | Document manual_map schema | Document JSON structure: `{ "mappings": [{"directory": "...", "type": "..."}] }` | Schema document created; examples provided | 2 |
| P1.4 | Create validation schemas | Build Pydantic models for manual_map structure, dedup response DTO | Schemas compile; validation works; test coverage >80% | 3 |

### Deliverables

- Schema validation document in `.claude/context/marketplace-schema.md`
- Pydantic validation schemas in `skillmeat/api/schemas/marketplace.py`
- Migration checklist confirming no DB changes needed

### Quality Gates

- [ ] All existing catalog entries load without errors
- [ ] No schema validation errors on test data
- [ ] Backward compatibility confirmed (sources without manual_map work fine)

### Dependencies

- None (foundation phase)

### Risks & Mitigations

**Risk:** Existing `manual_map` field has incompatible data
**Mitigation:** Query production DB; migrate any existing data if needed

---

## Phase 2: Backend Detection Engine (5-7 days, 20-30 points)

**Duration:** 5-7 days
**Story Points:** 20-30
**Assigned To:** `python-backend-engineer`

### Overview

Implement manual mapping integration in heuristic detector and create new deduplication engine. Wire both into the marketplace scanning workflow. Focus on correct handling of hierarchical mappings, content hashing, and confidence scoring.

### Tasks

#### P2.1: Manual Mapping in Heuristic Detector

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P2.1a | Update detector signature | Add `manual_mappings` parameter to `detect_artifacts()` function | Function signature updated; backwards compatible (optional param) | 2 |
| P2.1b | Implement directory matching | Match artifact directories against manual mappings (direct + parent match) | Matching logic passes unit tests; handles hierarchical inheritance | 5 |
| P2.1c | Apply hierarchical inheritance | Child directories override parent mapping; non-mapped dirs use parent type | Inheritance logic tested with 5+ scenarios | 3 |
| P2.1d | Set confidence scoring | Manual mappings get 95 confidence; parent match gets 90 | Confidence scores correctly assigned and logged | 2 |
| P2.1e | Unit tests for mapping | Test detection with and without manual mappings | >70% code coverage; all scenarios pass | 3 |

#### P2.2: Content Hashing

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P2.2a | Implement SHA256 hashing | Hash single files and directory contents (sorted JSON of file hashes) | Hashing logic correct; produces consistent output; tested | 3 |
| P2.2b | Add hash caching | Cache computed hashes to avoid recomputation on rescan | Hashes stored in metadata_json; cache hits reduce time by >50% | 2 |
| P2.2c | Add file size limit | Skip hashing files > 10MB (configurable); log warning | Config: MARKETPLACE_DEDUP_MAX_FILE_SIZE_MB (default 10) | 2 |
| P2.2d | Unit tests for hashing | Test hash computation for various file types and sizes | >75% coverage; edge cases handled | 3 |

#### P2.3: Deduplication Logic

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P2.3a | Create DeduplicationEngine class | New file `skillmeat/core/marketplace/deduplication_engine.py` | DeduplicationEngine with async methods; dataclasses for results | 4 |
| P2.3b | Implement within-source dedup | Stage 1: Group by (source, type, hash); keep highest confidence | Dedup logic tested; tie-breaking by confidence then path works | 4 |
| P2.3c | Implement cross-source dedup | Stage 2: Compare against collection artifacts; mark matching as duplicates | Query collection; identify cross-source matches; test with 10+ scenarios | 4 |
| P2.3d | Implement exclusion marking | Set excluded_at, excluded_reason for duplicate entries | Entries correctly marked; excluded_reason contains useful info | 2 |
| P2.3e | Unit tests for dedup | Test all dedup scenarios: no dupes, within-source, cross-source | >80% coverage; all tie-breaking scenarios | 4 |

#### P2.4: Integration

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P2.4a | Wire into scan workflow | Add dedup step after heuristic detection in `scan_github_source()` | Dedup called correctly; survives -> excluded split applied | 3 |
| P2.4b | Return dedup counts | Update ScanResult to include dedup stats | ScanResult.duplicates_within, duplicates_across; tested | 2 |
| P2.4c | Integration tests | Full scan -> detect -> dedup workflow tests | >60% coverage; scan + dedup works end-to-end | 3 |
| P2.4d | Performance validation | Verify dedup doesn't add >2x scan time | Benchmark on 100+ artifact repo; target <120s total | 2 |

### Deliverables

- Modified `skillmeat/core/marketplace/heuristic_detector.py`
- New `skillmeat/core/marketplace/deduplication_engine.py`
- Updated `skillmeat/core/marketplace/import_coordinator.py` or `github_scanner.py` with integration
- Unit & integration test suite (400+ lines)
- Performance benchmark results

### Quality Gates

- [ ] All P2 unit tests pass (>70% heuristic, >80% dedup coverage)
- [ ] All P2 integration tests pass
- [ ] No performance regression on existing scans (< +10%)
- [ ] Manual mappings correctly applied with expected confidence scores
- [ ] Deduplication correctly identifies and excludes duplicates

### Dependencies

- Phase 1 (schema validation)

### Risks & Mitigations

**Risk:** Dedup timeout on large repos (>10k files)
**Mitigation:** Implement lazy hashing, caching, configurable timeout (120s default)

**Risk:** Hash collisions (very low probability)
**Mitigation:** Use SHA256 industry standard; log collisions for monitoring

---

## Phase 3: API Layer (3-4 days, 12-18 points)

**Duration:** 3-4 days
**Story Points:** 12-18
**Assigned To:** `python-backend-engineer`

### Overview

Update existing PATCH endpoint to accept and validate manual_map field. Update GET endpoint to return manual_map. Modify rescan endpoint to apply mappings and return dedup counts. Add comprehensive API documentation.

### Tasks

#### P3.1: Update PATCH Endpoint

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P3.1a | Add manual_map to request schema | UpdateSourceRequest includes optional manual_map field | UpdateSourceRequest schema updated; validation works | 2 |
| P3.1b | Validate directory paths | Check all mapped directories exist in repository via GitHub API | Validation logic handles 500+ dir repos; <2s per request | 3 |
| P3.1c | Validate artifact types | Ensure all types are valid ArtifactType enum values | Validation rejects invalid types; returns 400 with detail | 1 |
| P3.1d | Persist mappings | Save manual_map JSON to MarketplaceSource.manual_map | PATCH endpoint accepts and saves; survives retrieval | 2 |
| P3.1e | Update PATCH route handler | Wire validation and persistence into endpoint | Endpoint passes 8+ test cases; error handling correct | 2 |

#### P3.2: Update GET Endpoint

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P3.2a | Include manual_map in response | SourceResponse includes deserialized manual_map field | SourceResponse schema updated; manual_map included in responses | 1 |
| P3.2b | Test GET response | Verify manual_map returned correctly after PATCH | GET returns same mappings that were PATCHed | 1 |

#### P3.3: Update Rescan Endpoint

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P3.3a | Pass manual_map to detector | Load manual_map from source; pass to heuristic_detector.detect_artifacts() | Manual mappings loaded and passed correctly | 2 |
| P3.3b | Return dedup counts | ScanResultDTO includes duplicates_within_source, duplicates_across_sources | Response schema updated; counts accurate | 2 |
| P3.3c | Update response schema | Add dedup and count_by_type fields to ScanResultDTO | OpenAPI schema reflects new fields | 2 |
| P3.3d | Integration test | Test PATCH -> rescan flow with manual mappings | End-to-end test passes; mappings applied; dedup counts accurate | 2 |

#### P3.4: Error Handling & Documentation

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P3.4a | Add error responses | Handle invalid mappings with 400; document errors | 400 responses include helpful detail; error messages clear | 2 |
| P3.4b | Update OpenAPI docs | Document manual_map field, dedup fields, examples | OpenAPI docs complete; examples accurate; /docs renders correctly | 2 |

### Deliverables

- Modified `skillmeat/api/routers/marketplace_sources.py` (PATCH, GET, POST /rescan endpoints)
- Updated `skillmeat/api/schemas/marketplace.py` (UpdateSourceRequest, SourceResponse, ScanResultDTO)
- API integration test suite (200+ lines)
- OpenAPI documentation updates

### Quality Gates

- [ ] All P3 API tests pass (>75% coverage)
- [ ] PATCH endpoint accepts and validates manual_map correctly
- [ ] GET endpoint returns manual_map
- [ ] Rescan applies manual_map and returns dedup counts
- [ ] OpenAPI docs complete and accurate
- [ ] No breaking changes to existing API

### Dependencies

- Phase 2 (backend detection engine)

### Risks & Mitigations

**Risk:** GitHub API rate limits during directory validation
**Mitigation:** Reuse scanner's cached tree data; batch validate directories

---

## Phase 4: Frontend UI (5-7 days, 20-28 points)

**Duration:** 5-7 days
**Story Points:** 20-28
**Assigned To:** `ui-engineer-enhanced`

### Overview

Create DirectoryMapModal component with file tree and type selectors. Integrate into source detail page. Add toolbar button. Update source detail to show mappings and dedup counts. Add notification system for scan completion.

### Tasks

#### P4.1: Modal Component

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P4.1a | Create DirectoryMapModal component | New component with file tree, type selectors, save/cancel/rescan buttons | Component renders; accepts directory data; handles 100+ dirs | 4 |
| P4.1b | Implement file tree rendering | Display hierarchical directory structure with indentation | Tree shows all dirs; proper nesting; <100ms render time | 3 |
| P4.1c | Implement type dropdown | Per-directory artifact type selector with all ArtifactType options | Dropdown functional; selects/changes type; includes "(none)" option | 3 |
| P4.1d | Implement hierarchical logic | Child directories inherit parent mapping; can override | Inheritance works as designed; tested with 5+ scenarios | 3 |
| P4.1e | Add form validation | Max 100 mappings; valid directory paths; valid types | Validation rejects invalid input; shows helpful errors | 2 |
| P4.1f | Implement actions | Save, Cancel, Rescan buttons with loading states | All actions work; loading states show during API calls | 2 |
| P4.1g | Component tests | Unit tests for modal, tree, type selector | >60% coverage; all user interactions tested | 4 |

#### P4.2: Toolbar Integration

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P4.2a | Add button to toolbar | "Map Directories" button in source-toolbar.tsx | Button visible and clickable; opens modal | 2 |
| P4.2b | Wire to modal | Button click opens DirectoryMapModal | Modal appears; modal disappears on close | 1 |
| P4.2c | Handle save/rescan | Save calls PATCH endpoint; rescan calls POST /rescan | API calls succeed; state updates after responses | 2 |

#### P4.3: Source Detail Updates

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P4.3a | Show manual mappings | Display applied mappings in source metadata section | Mappings displayed as list; readable format | 2 |
| P4.3b | Show dedup stats | Display duplicate counts from last scan | Stats show: "X within source, Y from collection" | 2 |
| P4.3c | Add duplicate badge | Show "Duplicate" badge on excluded entries in catalog view | Badge visible; matches design; shows on excluded entries | 2 |
| P4.3d | Implement badge tooltip | Tooltip explains duplicate reason on hover | Tooltip appears; explains why artifact is duplicate | 1 |
| P4.3e | Link to excluded filter | Link to view only excluded/duplicate artifacts | Link filters catalog; shows only excluded entries | 1 |

#### P4.4: Notification System

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P4.4a | Scan completion notification | Toast shows scan results with dedup counts | Toast appears; shows artifact count and dedup counts | 2 |
| P4.4b | Async scan notification | Handle long-running scans (>30s) with async notification | Notification updates when scan completes; no UI freeze | 1 |
| P4.4c | Link to source detail | Notification includes link to view results | Link navigates to source detail | 1 |

#### P4.5: Types & Hooks

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P4.5a | Update marketplace types | Add DirectoryMapping type to skillmeat/web/types/marketplace.ts | Types defined; match API schemas | 2 |
| P4.5b | Create hook for mapping update | useUpdateSourceMapping() hook for PATCH endpoint | Hook created; handles loading/error states; tested | 2 |
| P4.5c | Update rescan hook | useRescanSource() includes dedup counts in response | Hook updated; returns dedup stats; tests pass | 2 |

#### P4.6: UI Tests

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P4.6a | E2E test for mapping | Create source, add mapping, rescan, verify results | Test passes; correct types detected; dedup shown | 4 |
| P4.6b | Snapshot tests | UI component snapshot tests | Snapshots created; no visual regressions | 2 |
| P4.6c | Accessibility audit | WCAG AA compliance check | Audit passes; no critical issues | 2 |

### Deliverables

- `DirectoryMapModal.tsx` component (~400 lines)
- Updated `source-toolbar.tsx` with "Map Directories" button
- Updated source detail page with mappings/dedup display
- Updated `skillmeat/web/types/marketplace.ts`
- Updated hooks: `useUpdateSourceMapping()`, `useRescanSource()`
- Frontend test suite (400+ lines, >60% coverage)
- Design/accessibility verification

### Quality Gates

- [ ] All P4 component tests pass (>60% coverage)
- [ ] Modal renders correctly with 100+ directories
- [ ] Type selectors work on all devices
- [ ] Save/rescan actions call correct API endpoints
- [ ] No console errors or TypeScript errors
- [ ] WCAG AA accessibility audit passes

### Dependencies

- Phase 3 (API layer)

### Risks & Mitigations

**Risk:** Modal performance with 1000+ directories
**Mitigation:** Implement virtual scrolling; lazy load subtrees

**Risk:** Complex hierarchical mapping UI confusion
**Mitigation:** Add inline help text; example mapping; visual feedback

---

## Phase 5: Integration Testing & Deployment (2-3 days, 8-12 points)

**Duration:** 2-3 days
**Story Points:** 8-12
**Assigned To:** `python-backend-engineer`, `documentation-writer`

### Overview

Execute end-to-end workflow tests, edge case testing, performance validation, and backward compatibility verification. Create user and developer documentation. Prepare deployment checklist.

### Tasks

#### P5.1: Full Workflow Tests

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P5.1a | Create & map source | Create source, add manual mappings via modal, verify persisted | E2E test passes; mappings saved correctly | 1 |
| P5.1b | Rescan with mapping | Trigger rescan after mapping; verify correct types detected | Rescan applies mappings; confidence >= 90 | 1 |
| P5.1c | Dedup detection | Create source with duplicates; verify dedup exclusions | Within-source dedup works; cross-source dedup works | 1 |
| P5.1d | Import after dedup | Import some artifacts; verify duplicates remain excluded | Imports succeed; excluded entries stay excluded | 1 |
| P5.1e | Restore excluded | Restore excluded duplicate; verify appears in catalog | Restore action works; entry visible again | 1 |

#### P5.2: Edge Cases

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P5.2a | Empty repository | Scan repo with no artifacts; verify no errors | No artifacts detected; no crashes; dedup counts = 0 | 1 |
| P5.2b | All duplicates | Scan repo where all artifacts are duplicates | Only 1 survives; all others excluded; correct reason | 1 |
| P5.2c | Large repository | Scan 1000+ artifact repo; verify performance | Scan completes in <120s; dedup counts accurate | 2 |
| P5.2d | Deeply nested dirs | Scan repo with 20+ level nesting; verify mapping works | Deeply nested dirs can be mapped; inheritance works | 1 |
| P5.2e | Invalid mappings | Try to map non-existent dirs; verify 400 response | API returns 400 with helpful detail | 1 |

#### P5.3: Performance Testing

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P5.3a | Scan time regression | Measure scan time with/without dedup on 500 artifacts | <10% increase (target 120-130s) | 1 |
| P5.3b | Hash computation time | Measure SHA256 time on 1000 files | <10s total | 1 |
| P5.3c | Cross-source lookup | Measure dedup lookup against 1000 collection artifacts | <2s per scan | 1 |
| P5.3d | Modal responsiveness | Measure modal render time with 500+ directories | <100ms; smooth scrolling | 1 |

#### P5.4: Backward Compatibility

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P5.4a | Sources without mapping | Scan sources created before this feature | No errors; heuristic detection still works | 1 |
| P5.4b | Existing catalog entries | Load entries from before this feature | All entries load; metadata_json properly handled | 1 |
| P5.4c | API compatibility | Old clients calling existing endpoints | No breaking changes; new fields optional | 1 |

#### P5.5: Documentation

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P5.5a | User guide | Document manual mapping UI and dedup feature for end users | Guide includes: steps, screenshots, examples, FAQ | 2 |
| P5.5b | API documentation | Update OpenAPI docs and examples for new fields | Docs complete; examples accurate; /docs works | 1 |
| P5.5c | Developer guide | Document detection engine, dedup algorithm, extension points | Guide includes: flow diagrams, code examples, tuning tips | 2 |
| P5.5d | Troubleshooting guide | Common issues and solutions (wrong types, hidden duplicates, etc.) | Guide covers 5+ common scenarios | 1 |

#### P5.6: Deployment

| ID | Task | Description | Acceptance Criteria | Story Points |
|-----|------|-------------|-------------------|-------|
| P5.6a | Deployment checklist | Verify all systems ready for production | Checklist signed off; no blockers | 1 |
| P5.6b | Environment setup | Configure environment variables for dedup settings | Variables tested; defaults documented | 1 |
| P5.6c | Rollback plan | Document rollback procedure in case of critical issues | Rollback steps clear; tested (if possible) | 1 |

### Deliverables

- Integration test suite (600+ lines, fully automated)
- Edge case test results and documentation
- Performance benchmark report
- User documentation (guide + FAQ)
- API documentation updates
- Developer guide (architecture, extension points)
- Troubleshooting guide
- Deployment checklist
- Rollback playbook

### Quality Gates

- [ ] All E2E tests pass
- [ ] Edge cases handled gracefully (no crashes)
- [ ] Performance targets met (<120s for 1000 artifacts with dedup)
- [ ] Backward compatibility verified
- [ ] Documentation complete and accurate
- [ ] Deployment checklist signed off

### Dependencies

- Phases 1-4 (all previous phases)

### Risks & Mitigations

**Risk:** Critical issue found after partial deployment
**Mitigation:** Canary rollout to 10% first; monitor error rates closely

---

## Orchestration Quick Reference

This section provides ready-to-copy Task delegation commands for parallel execution.

### Phase 1: Database & Schema (Parallel)

```
Task("data-layer-expert", "P1.1-P1.4: Validate database schema and create validation models.
     Files: skillmeat/cache/models.py, skillmeat/api/schemas/marketplace.py
     Tasks: Confirm manual_map/metadata_json columns; create Pydantic schemas
     Expected: Schema validation document; Pydantic models in marketplace.py")
```

### Phase 2: Backend Engine (Sequential Batches)

**Batch 2.1: Detection mapping (Parallel)**
```
Task("python-backend-engineer", "P2.1a-P2.1e: Add manual mapping to heuristic detector.
     File: skillmeat/core/marketplace/heuristic_detector.py
     Changes:
       - Add manual_mappings parameter to detect_artifacts()
       - Implement directory matching logic
       - Apply hierarchical inheritance
       - Set confidence_score = 95 for manual mappings
     Tests: >70% coverage; all inheritance scenarios pass")
```

**Batch 2.2: Content hashing (Parallel with 2.1)**
```
Task("python-backend-engineer", "P2.2a-P2.2d: Implement SHA256 content hashing.
     File: skillmeat/core/marketplace/deduplication_engine.py (new)
     Changes:
       - Single file hashing
       - Directory hashing (sorted JSON of file hashes)
       - Hash caching in metadata_json
       - File size limit check (10MB)
     Tests: >75% coverage; consistency verified; performance <10s for 1000 files")
```

**Batch 2.3: Dedup logic (Sequential after 2.1-2.2)**
```
Task("python-backend-engineer", "P2.3a-P2.3e: Implement deduplication logic.
     File: skillmeat/core/marketplace/deduplication_engine.py
     Changes:
       - DeduplicationEngine class with compute_content_hash()
       - Within-source dedup (Stage 1)
       - Cross-source dedup (Stage 2)
       - Exclusion marking with excluded_at/excluded_reason
     Tests: >80% coverage; all scenarios tested")
```

**Batch 2.4: Integration (Sequential after 2.3)**
```
Task("python-backend-engineer", "P2.4a-P2.4d: Wire dedup into scan workflow.
     Files: skillmeat/core/marketplace/import_coordinator.py or github_scanner.py
     Changes:
       - Call deduplication engine after detection
       - Return dedup stats in ScanResult
       - Performance validation (<2x scan time)
     Tests: >60% integration coverage; benchmarks passed")
```

### Phase 3: API Layer (Sequential)

**Batch 3.1: PATCH endpoint (Sequential after Phase 2)**
```
Task("python-backend-engineer", "P3.1a-P3.1e: Update PATCH endpoint for manual mappings.
     Files: skillmeat/api/routers/marketplace_sources.py, skillmeat/api/schemas/marketplace.py
     Changes:
       - Add manual_map to UpdateSourceRequest schema
       - Validate directory paths via GitHub API
       - Validate artifact types
       - Persist to MarketplaceSource.manual_map
     Tests: 8+ test cases; error handling correct")
```

**Batch 3.2: GET & Rescan (Parallel with 3.1)**
```
Task("python-backend-engineer", "P3.2a-P3.3d: Update GET and rescan endpoints.
     Files: skillmeat/api/routers/marketplace_sources.py, skillmeat/api/schemas/marketplace.py
     Changes:
       - Include manual_map in GET SourceResponse
       - Pass manual_map to detector in rescan
       - Return dedup counts in ScanResultDTO
       - Update OpenAPI schema
     Tests: GET returns mappings; rescan applies mappings; dedup counts accurate")
```

**Batch 3.3: Error handling & docs (Sequential after 3.2)**
```
Task("python-backend-engineer", "P3.4a-P3.4b: Add error handling and OpenAPI docs.
     Files: skillmeat/api/routers/marketplace_sources.py, skillmeat/api/CLAUDE.md
     Changes:
       - 400 responses for invalid mappings
       - Clear error messages
       - OpenAPI documentation examples
     Expected: Docs complete; /docs renders correctly")
```

### Phase 4: Frontend UI (Parallel Batches)

**Batch 4.1: Modal component (Parallel)**
```
Task("ui-engineer-enhanced", "P4.1a-P4.1g: Create DirectoryMapModal component.
     Files: skillmeat/web/components/DirectoryMapModal.tsx (new)
     Tasks:
       - File tree rendering with hierarchical display
       - Type dropdown per directory
       - Hierarchical mapping logic (inheritance + override)
       - Form validation (max 100 mappings)
       - Save/Cancel/Rescan actions with loading states
       - Component tests (>60% coverage)
     Expected: 400+ line component; all interactions tested")
```

**Batch 4.2: Toolbar & detail integration (Parallel with 4.1)**
```
Task("ui-engineer-enhanced", "P4.2a-P4.3e: Integrate modal and update source detail.
     Files: skillmeat/web/components/source-toolbar.tsx, skillmeat/web/app/marketplace/sources/[id]/page.tsx
     Tasks:
       - Add 'Map Directories' button to toolbar
       - Wire button to open modal
       - Show manual mappings in source metadata
       - Show dedup stats (within-source, cross-source)
       - Add duplicate badge to excluded entries
       - Badge tooltip with duplicate reason
     Expected: Button works; modal opens; mappings displayed; badges visible")
```

**Batch 4.3: Notifications & hooks (Parallel with 4.1-4.2)**
```
Task("ui-engineer-enhanced", "P4.4a-P4.5c: Add notification system and update hooks.
     Files: skillmeat/web/types/marketplace.ts, skillmeat/web/hooks/ (new/updated)
     Tasks:
       - Scan completion toast with dedup counts
       - Async scan notification handling
       - DirectoryMapping type definition
       - useUpdateSourceMapping() hook
       - useRescanSource() hook update with dedup counts
     Expected: Toast appears on scan; shows counts; links work; hooks tested")
```

**Batch 4.4: UI tests (Sequential after 4.1-4.3)**
```
Task("ui-engineer-enhanced", "P4.6a-P4.6c: E2E and accessibility tests.
     Files: skillmeat/web/tests/ (new)
     Tasks:
       - E2E test: create source -> map directories -> rescan -> verify
       - Snapshot tests for modal and detail page
       - WCAG AA accessibility audit
     Expected: E2E passes; snapshots created; audit passes")
```

### Phase 5: Integration & Deployment (Sequential)

**Batch 5.1-5.3: Integration testing (Sequential after Phase 4)**
```
Task("python-backend-engineer", "P5.1a-P5.3d: Run integration, edge case, and performance tests.
     Files: Test suite in skillmeat/api/tests/, skillmeat/core/tests/
     Tasks:
       - Full workflow: create -> map -> rescan -> import -> restore
       - Edge cases: empty repo, all duplicates, 1000+ artifacts, nested dirs
       - Performance: scan time, hash time, modal responsiveness
       - Backward compatibility: old sources, entries, API clients
     Expected: All tests pass; performance targets met; no regressions")
```

**Batch 5.4-5.6: Documentation & deployment (Parallel after tests)**
```
Task("documentation-writer", "P5.5a-P5.5d: Create user, API, and developer documentation.
     Files: docs/ (new/updated)
     Tasks:
       - User guide: steps, screenshots, FAQ
       - API docs: update OpenAPI examples
       - Developer guide: architecture, dedup algorithm, extension points
       - Troubleshooting: 5+ common scenarios
     Expected: All docs complete; examples accurate; renders correctly")

Task("python-backend-engineer", "P5.6a-P5.6c: Prepare deployment checklist and rollback plan.
     Files: DEPLOYMENT.md (new)
     Tasks:
       - Verify all systems ready
       - Configure environment variables
       - Document rollback procedure
     Expected: Checklist signed off; rollback steps clear")
```

---

## Task Dependencies & Critical Path

### Dependency Graph

```
Phase 1 (Database & Schema)
    ↓ (required for all later phases)
Phase 2 (Backend Engine)
    ├─ P2.1 (Manual mapping) → must complete before P3
    ├─ P2.2 (Hashing) → can be parallel
    ├─ P2.3 (Dedup logic) → depends on P2.2
    └─ P2.4 (Integration) → depends on P2.1, P2.3
        ↓ (required for P3 & P4)
Phase 3 (API Layer)
    ├─ P3.1 (PATCH) → can be parallel with P3.2
    ├─ P3.2 (GET & Rescan) → depends on P2.4
    └─ P3.3 (Error handling & docs) → depends on P3.1, P3.2
        ↓ (required for Phase 4)
Phase 4 (Frontend)
    ├─ P4.1 (Modal) → can be parallel with P4.2
    ├─ P4.2 (Toolbar) → depends on Phase 3
    ├─ P4.3 (Notifications) → can be parallel
    └─ P4.4 (Tests) → depends on P4.1-P4.3
        ↓ (required for Phase 5)
Phase 5 (Integration & Deployment)
    └─ All phases must pass before deployment
```

### Critical Path (Longest dependency chain)

```
Phase 1 (1 day)
  → Phase 2.1 (Manual mapping: 3-4 days)
    → Phase 2.4 (Integration: 2-3 days)
      → Phase 3 (API: 3-4 days)
        → Phase 4.2 (Toolbar: 1 day)
          → Phase 5.1 (E2E tests: 1 day)
            → Deployment (0.5 days)

Total Critical Path: ~12-15 days
(Parallel execution reduces actual timeline to ~10-12 days)
```

### Optimization Opportunities

**Run in Parallel:**
- Phase 2.1 (mapping) + Phase 2.2 (hashing) can run simultaneously after Phase 1
- Phase 3.1 (PATCH) + Phase 3.2 (GET/Rescan) can run simultaneously
- Phase 4.1 (Modal) + Phase 4.2 (Toolbar) can run simultaneously after Phase 3
- Phase 4.1-4.3 (UI tasks) can run in parallel
- Phase 5.4-5.6 (Docs & deployment) can start as soon as code is stable

**Expected Timeline:** 4-5 weeks with optimal parallelization

---

## Quality Assurance Gates

### Phase 1 Gate

**Entry Criteria:**
- PRD approved and finalized
- Codebase ready for changes

**Exit Criteria:**
- [ ] All schema validation tests pass
- [ ] No existing data corrupted
- [ ] Backward compatibility confirmed
- [ ] Code review approved

**Sign-off:** Data layer lead

---

### Phase 2 Gate

**Entry Criteria:**
- Phase 1 complete and signed off

**Exit Criteria:**
- [ ] All heuristic detector tests pass (>70% coverage)
- [ ] All deduplication engine tests pass (>80% coverage)
- [ ] All integration tests pass (>60% coverage)
- [ ] Performance regression < 10% on existing scans
- [ ] Confidence scoring validated
- [ ] Code review approved

**Sign-off:** Backend team lead

---

### Phase 3 Gate

**Entry Criteria:**
- Phase 2 complete and signed off

**Exit Criteria:**
- [ ] All API tests pass (>75% coverage)
- [ ] PATCH endpoint validates and persists manual_map correctly
- [ ] GET endpoint returns manual_map
- [ ] Rescan applies manual_map and returns dedup counts
- [ ] OpenAPI documentation complete and accurate
- [ ] No breaking changes to existing API
- [ ] Code review approved

**Sign-off:** API team lead

---

### Phase 4 Gate

**Entry Criteria:**
- Phase 3 complete and signed off

**Exit Criteria:**
- [ ] All component tests pass (>60% coverage)
- [ ] Modal renders correctly with 100+ directories
- [ ] Type selectors and hierarchical mapping work
- [ ] Save/rescan actions call correct endpoints
- [ ] No console errors or TypeScript errors
- [ ] WCAG AA accessibility audit passes
- [ ] Code review approved

**Sign-off:** Frontend team lead

---

### Phase 5 Gate

**Entry Criteria:**
- Phase 4 complete and signed off

**Exit Criteria:**
- [ ] All E2E tests pass
- [ ] Edge cases handled gracefully
- [ ] Performance targets met
- [ ] Backward compatibility verified
- [ ] User documentation complete
- [ ] API documentation updated
- [ ] Developer guide complete
- [ ] Deployment checklist signed off
- [ ] Security review completed
- [ ] Code review approved

**Sign-off:** QA lead + Release manager

---

## Risk Management

### High-Priority Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|-----------|-------|
| Dedup performance timeout on large repos | Medium | High | Implement lazy hashing, caching, configurable timeout (120s); test with 1000+ artifacts | Backend |
| Manual mapping UI confusion (hierarchical logic) | Low | Medium | Add inline help text, examples, visual feedback; user testing with 5+ testers | Frontend |
| Hash collisions (SHA256) | Very Low | High | Use industry-standard SHA256; log collisions for monitoring; document risk | Backend |
| Backward compatibility breaking | Low | High | No DB changes; optional API fields; thorough testing of existing sources | QA |
| Over-exclusion of valid duplicates | Medium | Medium | Store duplicate reason in excluded_reason; allow restore; test with known duplicates | Backend/QA |

### Mitigation Strategies

1. **Performance:** Implement incremental hashing with caching; lazy evaluation for non-obvious duplicates
2. **UX:** Provide auto-suggestions for common directory names; add help modal; test with 5+ users
3. **Compatibility:** Run full regression test suite before deployment; canary rollout to 10% users first
4. **Monitoring:** Add metrics for scan time, dedup stats, error rates; set up alerts
5. **Rollback:** Keep previous code version; have database backup; document rollback procedure

---

## Metrics & Success Criteria

### Implementation Metrics

| Metric | Target | Owner | Frequency |
|--------|--------|-------|-----------|
| Code coverage (Phase 2) | >75% heuristic, >80% dedup | Backend | Per commit |
| Code coverage (Phase 3) | >75% API routes | Backend | Per commit |
| Code coverage (Phase 4) | >60% components | Frontend | Per commit |
| Test pass rate | 100% | QA | Per commit |
| Code review sign-offs | 100% | Tech leads | Per phase |

### Production Metrics

| Metric | Target | Owner | Frequency |
|--------|--------|-------|-----------|
| Detection accuracy (non-skills) | >= 85% | Product | Monthly |
| Duplicate detection rate | >= 90% | Product | Monthly |
| Manual mapping adoption | > 30% of sources | Product | Monthly |
| Scan time regression | < 10% increase | Backend | Weekly |
| User satisfaction survey | >= 4/5 stars | Product | Monthly |
| Error rate | < 2% on marketplace endpoints | DevOps | Daily |

### Observability

**Logging added:**
```
[INFO] Scan started: source_id=src_123, repo=user/repo
[INFO] Detection completed: artifacts=42, time_ms=3200
[INFO] Deduplication started: total_artifacts=42
[INFO] Within-source dedup: duplicates_found=4, surviving=38
[INFO] Cross-source dedup: duplicates_found=3, surviving=35
[INFO] Scan completed: time_ms=4100, duplicates_within=4, duplicates_across=3
```

**Metrics to track:**
```
marketplace_scan_duration_seconds (histogram)
marketplace_artifacts_detected (counter, tagged by source_id)
marketplace_duplicates_within_source (counter)
marketplace_duplicates_across_sources (counter)
marketplace_manual_mappings_used (counter)
marketplace_scan_errors (counter, tagged by error_type)
```

---

## Environment Configuration

### Required Environment Variables

| Variable | Default | Type | Description |
|----------|---------|------|-------------|
| `MARKETPLACE_MAX_MAPPINGS_PER_SOURCE` | 100 | int | Max manual mappings per source |
| `MARKETPLACE_DEDUP_ENABLED` | true | bool | Enable/disable deduplication |
| `MARKETPLACE_DEDUP_MAX_FILE_SIZE_MB` | 10 | int | Skip hashing files > this size |
| `MARKETPLACE_DEDUP_TIMEOUT_SECONDS` | 120 | int | Timeout for dedup operations |
| `MARKETPLACE_HASH_ALGORITHM` | sha256 | str | Algorithm: sha256 (only option for now) |
| `MARKETPLACE_DEDUP_LAZY_HASHING_ENABLED` | true | bool | Use lazy hashing for performance |

### Configuration in Code

**Backend (`skillmeat/api/config.py`):**
```python
class MarketplaceSettings(BaseSettings):
    max_mappings_per_source: int = 100
    dedup_enabled: bool = True
    dedup_max_file_size_mb: int = 10
    dedup_timeout_seconds: int = 120
    hash_algorithm: str = "sha256"
    lazy_hashing_enabled: bool = True
```

---

## Deployment Procedure

### Pre-Deployment Checklist

- [ ] All tests passing (unit, integration, E2E)
- [ ] Code review sign-offs complete
- [ ] Database backup taken (if needed)
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented and tested
- [ ] User documentation finalized
- [ ] Performance testing validated

### Deployment Steps

1. **Stage 1: Backend Deployment (Maintenance Window)**
   - Deploy Python backend changes
   - Verify API endpoints responding
   - Run health check endpoint
   - Monitor error logs for 5 minutes

2. **Stage 2: Frontend Deployment**
   - Deploy Next.js frontend changes
   - Verify page loads correctly
   - Check component rendering
   - Monitor browser console for errors

3. **Stage 3: Canary Rollout (Optional)**
   - Deploy to 10% of users first
   - Monitor metrics for 2 hours
   - Watch for error rate increases
   - If stable, proceed to full rollout

4. **Stage 4: Full Rollout**
   - Deploy to 100% of users
   - Monitor metrics closely for 24 hours
   - Check user feedback channels
   - Prepare for quick rollback if needed

### Rollback Procedure

**If critical issues arise:**

1. Revert backend code to previous commit
2. Revert frontend code to previous commit
3. Clear browser cache / CDN caches
4. Restore database from pre-deployment snapshot (if needed)
5. Monitor system for 24 hours post-rollback
6. Document issue and root cause

---

## Team & Responsibilities

### Role Assignments

| Role | Responsible For | Phase(s) |
|------|----------------|----------|
| **Data Layer Expert** | Database schema validation | Phase 1 |
| **Python Backend Engineer** | Detection engine, dedup, API | Phases 2-3, 5 (testing) |
| **UI Engineer Enhanced** | Modal, toolbar, detail UI | Phase 4 |
| **Documentation Writer** | User & developer docs | Phase 5 |
| **QA Lead** | Integration tests, acceptance | Phase 5 |
| **Tech Lead** | Code reviews, architecture decisions | All phases |
| **Release Manager** | Deployment checklist, rollout | Phase 5 |

### Communication Plan

- **Daily standups** (15 min) during active phase
- **Weekly sync** across team leads
- **Phase gate reviews** before proceeding to next phase
- **Slack notifications** for test failures and deployments

---

## References & Related Documents

### Key Files

**Backend:**
- `skillmeat/core/marketplace/github_scanner.py` - GitHub API scanning
- `skillmeat/core/marketplace/heuristic_detector.py` - Detection engine (to be modified)
- `skillmeat/core/marketplace/deduplication_engine.py` - NEW file
- `skillmeat/cache/models.py` (Lines 1173-1366) - Database models
- `skillmeat/api/routers/marketplace_sources.py` - API endpoints
- `skillmeat/api/schemas/marketplace.py` - Request/response schemas

**Frontend:**
- `skillmeat/web/components/DirectoryMapModal.tsx` - NEW component
- `skillmeat/web/components/source-toolbar.tsx` - Toolbar (to be modified)
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Source detail
- `skillmeat/web/types/marketplace.ts` - TypeScript types
- `skillmeat/web/hooks/` - React hooks (to be created/modified)

**Documentation:**
- `skillmeat/core/artifact.py` - Artifact types (skill, command, agent, mcp_server, hook)
- `skillmeat/api/CLAUDE.md` - API architecture guide
- `skillmeat/web/CLAUDE.md` - Frontend architecture guide

### Related PRDs

- [Marketplace GitHub Ingestion PRD](/docs/project_plans/PRDs/features/marketplace-github-ingestion-v1.md)
- [Marketplace Sources Non-Skills Bug Report](/docs/project_plans/bugs/marketplace-sources-non_skills-v1.md)

### Standards & References

- SHA256 (FIPS 180-4)
- REST API design (RFC 7231)
- WCAG AA accessibility standards

---

## Appendix: Data Structures

### Manual Map JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "mappings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "directory": {
            "type": "string",
            "description": "Path relative to root (e.g., 'commands', 'agents/llm')"
          },
          "type": {
            "type": "string",
            "enum": ["skill", "command", "agent", "mcp_server", "hook"],
            "description": "Artifact type for this directory"
          }
        },
        "required": ["directory", "type"],
        "additionalProperties": false
      },
      "minItems": 0,
      "maxItems": 100
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "When mappings were last updated"
    }
  },
  "required": ["mappings"],
  "additionalProperties": false
}
```

### DeduplicationResult Data Structure

```python
@dataclass
class DeduplicationResult:
    total_detected: int
    duplicates_within_source: int
    duplicates_across_sources: int
    surviving_entries: list[ArtifactMetadata]
    excluded_entries: list[tuple[ArtifactMetadata, str]]  # (entry, reason)
    dedup_time_ms: int
```

### Content Hash Storage (in metadata_json)

```json
{
  "content_hash": "sha256:abcd1234...",
  "hash_algorithm": "sha256",
  "hash_computed_at": "2026-01-05T10:00:00Z",
  "hash_files_count": 3,
  "hash_total_size_bytes": 5240,
  "duplicate_reason": "Duplicate within source (highest confidence survives)",
  "duplicate_group_id": "dedup_grp_123"
}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-05 | Claude Code | Initial implementation plan created from PRD |

---

**End of Implementation Plan**
