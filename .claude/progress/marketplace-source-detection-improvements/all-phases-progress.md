---
type: progress
prd: "marketplace-source-detection-improvements"
phase: "all"
status: not_started
progress: 0
total_tasks: 58
completed_tasks: 0
created: 2026-01-05
updated: 2026-01-05

phases:
  - id: 1
    name: "Database & Schema"
    status: "not_started"
    progress: 0
    effort: "5-8 pts"
    assigned_to: ["data-layer-expert"]

  - id: 2
    name: "Backend Detection Engine"
    status: "not_started"
    progress: 0
    effort: "20-30 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: [1]

  - id: 3
    name: "API Layer"
    status: "not_started"
    progress: 0
    effort: "12-18 pts"
    assigned_to: ["python-backend-engineer"]
    dependencies: [2]

  - id: 4
    name: "Frontend UI"
    status: "not_started"
    progress: 0
    effort: "20-28 pts"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: [3]

  - id: 5
    name: "Testing & Documentation"
    status: "not_started"
    progress: 0
    effort: "8-12 pts"
    assigned_to: ["python-backend-engineer", "documentation-writer"]
    dependencies: [4]

tasks:
  # Phase 1: Database & Schema (4 tasks)
  - id: "P1.1"
    phase: 1
    name: "Validate manual_map column"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    effort: "2 pts"

  - id: "P1.2"
    phase: 1
    name: "Validate metadata_json column"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    effort: "2 pts"

  - id: "P1.3"
    phase: 1
    name: "Document manual_map schema"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: []
    effort: "2 pts"

  - id: "P1.4"
    phase: 1
    name: "Create Pydantic validation schemas"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["P1.1", "P1.2", "P1.3"]
    effort: "3 pts"

  # Phase 2: Backend Detection Engine - Manual Mapping (5 tasks)
  - id: "P2.1a"
    phase: 2
    name: "Update detector signature"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1.4"]
    effort: "2 pts"

  - id: "P2.1b"
    phase: 2
    name: "Implement directory matching"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1a"]
    effort: "5 pts"

  - id: "P2.1c"
    phase: 2
    name: "Apply hierarchical inheritance"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1b"]
    effort: "3 pts"

  - id: "P2.1d"
    phase: 2
    name: "Set confidence scoring"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1c"]
    effort: "2 pts"

  - id: "P2.1e"
    phase: 2
    name: "Unit tests for mapping"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1d"]
    effort: "3 pts"

  # Phase 2: Backend Detection Engine - Content Hashing (4 tasks)
  - id: "P2.2a"
    phase: 2
    name: "Implement SHA256 hashing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1.4"]
    effort: "3 pts"

  - id: "P2.2b"
    phase: 2
    name: "Add hash caching"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2a"]
    effort: "2 pts"

  - id: "P2.2c"
    phase: 2
    name: "Add file size limit"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2a"]
    effort: "2 pts"

  - id: "P2.2d"
    phase: 2
    name: "Unit tests for hashing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2b", "P2.2c"]
    effort: "3 pts"

  # Phase 2: Backend Detection Engine - Deduplication (5 tasks)
  - id: "P2.3a"
    phase: 2
    name: "Create DeduplicationEngine class"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2a"]
    effort: "4 pts"

  - id: "P2.3b"
    phase: 2
    name: "Implement within-source dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3a"]
    effort: "4 pts"

  - id: "P2.3c"
    phase: 2
    name: "Implement cross-source dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3b"]
    effort: "4 pts"

  - id: "P2.3d"
    phase: 2
    name: "Implement exclusion marking"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3c"]
    effort: "2 pts"

  - id: "P2.3e"
    phase: 2
    name: "Unit tests for dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3d"]
    effort: "4 pts"

  # Phase 2: Backend Detection Engine - Integration (4 tasks)
  - id: "P2.4a"
    phase: 2
    name: "Wire into scan workflow"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1e", "P2.3e"]
    effort: "3 pts"

  - id: "P2.4b"
    phase: 2
    name: "Return dedup counts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4a"]
    effort: "2 pts"

  - id: "P2.4c"
    phase: 2
    name: "Integration tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4b"]
    effort: "3 pts"

  - id: "P2.4d"
    phase: 2
    name: "Performance validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4c"]
    effort: "2 pts"

  # Phase 3: API Layer - PATCH Endpoint (5 tasks)
  - id: "P3.1a"
    phase: 3
    name: "Add manual_map to request schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4d"]
    effort: "2 pts"

  - id: "P3.1b"
    phase: 3
    name: "Validate directory paths"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1a"]
    effort: "3 pts"

  - id: "P3.1c"
    phase: 3
    name: "Validate artifact types"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1a"]
    effort: "1 pt"

  - id: "P3.1d"
    phase: 3
    name: "Persist mappings"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1b", "P3.1c"]
    effort: "2 pts"

  - id: "P3.1e"
    phase: 3
    name: "Update PATCH route handler"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1d"]
    effort: "2 pts"

  # Phase 3: API Layer - GET Endpoint (2 tasks)
  - id: "P3.2a"
    phase: 3
    name: "Include manual_map in response"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.1e"]
    effort: "1 pt"

  - id: "P3.2b"
    phase: 3
    name: "Test GET response"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.2a"]
    effort: "1 pt"

  # Phase 3: API Layer - Rescan Endpoint (4 tasks)
  - id: "P3.3a"
    phase: 3
    name: "Pass manual_map to detector"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.2b"]
    effort: "2 pts"

  - id: "P3.3b"
    phase: 3
    name: "Return dedup counts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3a"]
    effort: "2 pts"

  - id: "P3.3c"
    phase: 3
    name: "Update response schema"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3b"]
    effort: "2 pts"

  - id: "P3.3d"
    phase: 3
    name: "Integration test"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3c"]
    effort: "2 pts"

  # Phase 3: API Layer - Error Handling & Docs (2 tasks)
  - id: "P3.4a"
    phase: 3
    name: "Add error responses"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.3d"]
    effort: "2 pts"

  - id: "P3.4b"
    phase: 3
    name: "Update OpenAPI docs"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P3.4a"]
    effort: "2 pts"

  # Phase 4: Frontend UI - Modal Component (6 tasks)
  - id: "P4.1a"
    phase: 4
    name: "Create DirectoryMapModal component"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P3.4b"]
    effort: "4 pts"

  - id: "P4.1b"
    phase: 4
    name: "Implement file tree rendering"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.1a"]
    effort: "3 pts"

  - id: "P4.1c"
    phase: 4
    name: "Implement type dropdown"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.1a"]
    effort: "3 pts"

  - id: "P4.1d"
    phase: 4
    name: "Implement hierarchical logic"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.1b", "P4.1c"]
    effort: "3 pts"

  - id: "P4.1e"
    phase: 4
    name: "Add save/cancel/rescan buttons"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.1d"]
    effort: "2 pts"

  - id: "P4.1f"
    phase: 4
    name: "Unit tests for modal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.1e"]
    effort: "3 pts"

  # Phase 4: Frontend UI - Toolbar Integration (3 tasks)
  - id: "P4.2a"
    phase: 4
    name: "Add Map Directories button"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.1f"]
    effort: "2 pts"

  - id: "P4.2b"
    phase: 4
    name: "Wire button to modal"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.2a"]
    effort: "1 pt"

  - id: "P4.2c"
    phase: 4
    name: "Test toolbar integration"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.2b"]
    effort: "1 pt"

  # Phase 4: Frontend UI - Source Detail Updates (5 tasks)
  - id: "P4.3a"
    phase: 4
    name: "Display current mappings"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.2c"]
    effort: "2 pts"

  - id: "P4.3b"
    phase: 4
    name: "Show dedup counts in scan results"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.3a"]
    effort: "2 pts"

  - id: "P4.3c"
    phase: 4
    name: "Add duplicate badge to entries"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.3b"]
    effort: "2 pts"

  - id: "P4.3d"
    phase: 4
    name: "Update marketplace.ts types"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.3c"]
    effort: "2 pts"

  - id: "P4.3e"
    phase: 4
    name: "Test source detail updates"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.3d"]
    effort: "2 pts"

  # Phase 4: Frontend UI - Notifications (3 tasks)
  - id: "P4.4a"
    phase: 4
    name: "Add dedup count to scan toast"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.3e"]
    effort: "2 pts"

  - id: "P4.4b"
    phase: 4
    name: "Add filter for duplicates in excluded list"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.4a"]
    effort: "2 pts"

  - id: "P4.4c"
    phase: 4
    name: "Test notifications"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4.4b"]
    effort: "1 pt"

  # Phase 5: Testing & Documentation - Integration Tests (4 tasks)
  - id: "P5.1a"
    phase: 5
    name: "E2E test: mapping → scan → dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P4.4c"]
    effort: "3 pts"

  - id: "P5.1b"
    phase: 5
    name: "E2E test: cross-source dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P5.1a"]
    effort: "2 pts"

  - id: "P5.1c"
    phase: 5
    name: "Edge case tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P5.1b"]
    effort: "2 pts"

  - id: "P5.1d"
    phase: 5
    name: "Performance benchmark"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P5.1c"]
    effort: "2 pts"

  # Phase 5: Testing & Documentation - Documentation (3 tasks)
  - id: "P5.2a"
    phase: 5
    name: "User guide for mapping"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P4.4c"]
    effort: "2 pts"

  - id: "P5.2b"
    phase: 5
    name: "API documentation update"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5.2a"]
    effort: "1 pt"

  - id: "P5.2c"
    phase: 5
    name: "Developer guide for dedup"
    status: "pending"
    assigned_to: ["documentation-writer"]
    dependencies: ["P5.2b"]
    effort: "2 pts"

  # Phase 5: Testing & Documentation - Deployment (3 tasks)
  - id: "P5.3a"
    phase: 5
    name: "Deployment checklist"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P5.1d", "P5.2c"]
    effort: "1 pt"

  - id: "P5.3b"
    phase: 5
    name: "Rollback procedure"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P5.3a"]
    effort: "1 pt"

  - id: "P5.3c"
    phase: 5
    name: "Feature flag setup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P5.3b"]
    effort: "1 pt"

parallelization:
  # Phase 1 - all validation tasks can run in parallel
  batch_1_1: ["P1.1", "P1.2", "P1.3"]
  batch_1_2: ["P1.4"]  # depends on batch_1_1

  # Phase 2 - parallel tracks: mapping vs hashing
  batch_2_1: ["P2.1a", "P2.2a"]  # start mapping + hashing in parallel
  batch_2_2: ["P2.1b", "P2.2b", "P2.2c"]  # parallel after respective batch_2_1
  batch_2_3: ["P2.1c", "P2.2d", "P2.3a"]  # hashing tests + start dedup
  batch_2_4: ["P2.1d", "P2.3b"]
  batch_2_5: ["P2.1e", "P2.3c"]
  batch_2_6: ["P2.3d"]
  batch_2_7: ["P2.3e"]
  batch_2_8: ["P2.4a"]  # integration after unit tests
  batch_2_9: ["P2.4b"]
  batch_2_10: ["P2.4c"]
  batch_2_11: ["P2.4d"]

  # Phase 3 - sequential API updates with some parallelization
  batch_3_1: ["P3.1a"]
  batch_3_2: ["P3.1b", "P3.1c"]  # validate paths and types in parallel
  batch_3_3: ["P3.1d"]
  batch_3_4: ["P3.1e"]
  batch_3_5: ["P3.2a"]
  batch_3_6: ["P3.2b"]
  batch_3_7: ["P3.3a"]
  batch_3_8: ["P3.3b"]
  batch_3_9: ["P3.3c"]
  batch_3_10: ["P3.3d"]
  batch_3_11: ["P3.4a", "P3.4b"]  # error handling and docs in parallel

  # Phase 4 - parallel UI work
  batch_4_1: ["P4.1a"]
  batch_4_2: ["P4.1b", "P4.1c"]  # tree rendering and dropdown in parallel
  batch_4_3: ["P4.1d"]
  batch_4_4: ["P4.1e"]
  batch_4_5: ["P4.1f"]
  batch_4_6: ["P4.2a"]
  batch_4_7: ["P4.2b"]
  batch_4_8: ["P4.2c"]
  batch_4_9: ["P4.3a"]
  batch_4_10: ["P4.3b"]
  batch_4_11: ["P4.3c"]
  batch_4_12: ["P4.3d"]
  batch_4_13: ["P4.3e"]
  batch_4_14: ["P4.4a"]
  batch_4_15: ["P4.4b"]
  batch_4_16: ["P4.4c"]

  # Phase 5 - tests + docs in parallel tracks
  batch_5_1: ["P5.1a", "P5.2a"]  # E2E tests + user guide in parallel
  batch_5_2: ["P5.1b", "P5.2b"]
  batch_5_3: ["P5.1c", "P5.2c"]
  batch_5_4: ["P5.1d"]
  batch_5_5: ["P5.3a"]
  batch_5_6: ["P5.3b"]
  batch_5_7: ["P5.3c"]
---

# Progress: Marketplace Source Detection Improvements

## Orchestration Quick Reference

### Phase 1: Database & Schema

**Batch 1.1** (Parallel - 3 tasks):
```
Task("data-layer-expert", "P1.1: Validate MarketplaceSource.manual_map column exists and supports JSON storage. P1.2: Validate MarketplaceCatalogEntry.metadata_json can store content_hash field. P1.3: Document manual_map JSON schema structure with directory paths as keys and artifact types as values", model="haiku")
```

**Batch 1.2** (Sequential - 1 task):
```
Task("data-layer-expert", "P1.4: Create Pydantic validation schemas for manual_map structure and deduplication response in skillmeat/api/schemas/marketplace.py", model="haiku")
```

### Phase 2: Backend Detection Engine

**Batch 2.1** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P2.1a: Update heuristic_detector.detect_artifacts() signature to accept optional manual_mappings parameter (backward compatible)")
Task("python-backend-engineer", "P2.2a: Implement SHA256 content hashing for single files and directory contents in skillmeat/core/marketplace/")
```

**Batch 2.2** (Parallel - 3 tasks):
```
Task("python-backend-engineer", "P2.1b: Implement directory matching logic in heuristic detector to apply manual mappings with exact and prefix matching")
Task("python-backend-engineer", "P2.2b: Add hash caching mechanism to avoid recomputing hashes for unchanged files", model="sonnet")
Task("python-backend-engineer", "P2.2c: Add file size limit (10MB) for hashing to prevent timeouts on large files", model="sonnet")
```

**Batch 2.3** (Parallel - 3 tasks):
```
Task("python-backend-engineer", "P2.1c: Apply hierarchical inheritance for manual mappings (parent directory mapping applies to children)")
Task("python-backend-engineer", "P2.2d: Unit tests for content hashing including edge cases (empty files, large files, directories)", model="sonnet")
Task("python-backend-engineer", "P2.3a: Create DeduplicationEngine class in skillmeat/core/marketplace/deduplication_engine.py with hash-based duplicate detection")
```

**Batch 2.4** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P2.1d: Set confidence scores for manual mappings (manual=95, parent_match=90)")
Task("python-backend-engineer", "P2.3b: Implement within-source deduplication logic - keep highest confidence artifact on hash collision")
```

**Batch 2.5** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P2.1e: Unit tests for manual mapping logic with various directory structures and edge cases")
Task("python-backend-engineer", "P2.3c: Implement cross-source deduplication - check existing artifacts in other sources by hash")
```

**Batch 2.6** (Sequential - 1 task):
```
Task("python-backend-engineer", "P2.3d: Implement exclusion marking for duplicates - mark as excluded instead of deleting")
```

**Batch 2.7** (Sequential - 1 task):
```
Task("python-backend-engineer", "P2.3e: Unit tests for deduplication engine with within-source and cross-source scenarios")
```

**Batch 2.8** (Sequential - 1 task):
```
Task("python-backend-engineer", "P2.4a: Wire deduplication into scan workflow in github_scanner.py - run after all detection")
```

**Batch 2.9** (Sequential - 1 task):
```
Task("python-backend-engineer", "P2.4b: Return dedup counts in scan results (duplicates_removed, cross_source_duplicates)", model="sonnet")
```

**Batch 2.10** (Sequential - 1 task):
```
Task("python-backend-engineer", "P2.4c: Integration tests for full scan workflow with manual mappings and deduplication", model="sonnet")
```

**Batch 2.11** (Sequential - 1 task):
```
Task("python-backend-engineer", "P2.4d: Performance validation - ensure scan completes in <120s for 1000 artifacts", model="sonnet")
```

### Phase 3: API Layer

**Batch 3.1** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.1a: Add manual_map field to MarketplaceSourceUpdate request schema in skillmeat/api/schemas/marketplace.py")
```

**Batch 3.2** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P3.1b: Validate directory paths in manual_map exist in source repository using GitHub API", model="sonnet")
Task("python-backend-engineer", "P3.1c: Validate artifact types in manual_map against allowed types (skill, command, agent, mcp_server, hook)", model="sonnet")
```

**Batch 3.3** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.1d: Persist manual_map to MarketplaceSource.manual_map column as JSON")
```

**Batch 3.4** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.1e: Update PATCH /api/v1/marketplace-sources/{id} route handler to accept and validate manual_map")
```

**Batch 3.5** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.2a: Include manual_map in GET /api/v1/marketplace-sources/{id} response schema", model="sonnet")
```

**Batch 3.6** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.2b: Test GET endpoint returns manual_map correctly", model="sonnet")
```

**Batch 3.7** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3a: Pass manual_map from database to detector in rescan endpoint")
```

**Batch 3.8** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3b: Return dedup counts in rescan response (duplicates_removed, cross_source_duplicates)", model="sonnet")
```

**Batch 3.9** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3c: Update MarketplaceRescanResponse schema to include dedup counts", model="sonnet")
```

**Batch 3.10** (Sequential - 1 task):
```
Task("python-backend-engineer", "P3.3d: Integration test for rescan endpoint with manual mappings and deduplication", model="sonnet")
```

**Batch 3.11** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P3.4a: Add error responses for invalid directory paths and artifact types (400, 422)", model="sonnet")
Task("python-backend-engineer", "P3.4b: Update OpenAPI docs for PATCH, GET, and rescan endpoints with manual_map examples", model="sonnet")
```

### Phase 4: Frontend UI

**Batch 4.1** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1a: Create DirectoryMapModal component in skillmeat/web/components/marketplace/DirectoryMapModal.tsx with Radix Dialog")
```

**Batch 4.2** (Parallel - 2 tasks):
```
Task("ui-engineer-enhanced", "P4.1b: Implement file tree rendering in modal using source.tree_data from GitHub API")
Task("ui-engineer-enhanced", "P4.1c: Implement artifact type dropdown for each directory (skill, command, agent, mcp_server, hook)")
```

**Batch 4.3** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1d: Implement hierarchical logic - selecting parent directory auto-selects children")
```

**Batch 4.4** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1e: Add Save, Cancel, and Rescan buttons to modal with proper state management")
```

**Batch 4.5** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.1f: Unit tests for DirectoryMapModal component using Jest and React Testing Library")
```

**Batch 4.6** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.2a: Add Map Directories button to source-toolbar.tsx in marketplace source detail page", model="sonnet")
```

**Batch 4.7** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.2b: Wire Map Directories button to open DirectoryMapModal", model="sonnet")
```

**Batch 4.8** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.2c: Test toolbar integration - button opens modal correctly", model="sonnet")
```

**Batch 4.9** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3a: Display current manual_map mappings in source detail page", model="sonnet")
```

**Batch 4.10** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3b: Show dedup counts in scan results notification (X duplicates removed, Y cross-source)", model="sonnet")
```

**Batch 4.11** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3c: Add duplicate badge to catalog entries that were marked as duplicates", model="sonnet")
```

**Batch 4.12** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3d: Update skillmeat/web/types/marketplace.ts to include manual_map and dedup fields", model="sonnet")
```

**Batch 4.13** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.3e: Test source detail page displays manual_map and dedup counts correctly", model="sonnet")
```

**Batch 4.14** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.4a: Add dedup count to scan toast notification message", model="sonnet")
```

**Batch 4.15** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.4b: Add filter option to show only duplicates in excluded entries list", model="sonnet")
```

**Batch 4.16** (Sequential - 1 task):
```
Task("ui-engineer-enhanced", "P4.4c: Test notifications display dedup counts and filter works correctly", model="sonnet")
```

### Phase 5: Testing & Documentation

**Batch 5.1** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P5.1a: E2E test for full workflow - create source, set manual mappings, scan, verify deduplication")
Task("documentation-writer", "P5.2a: Create user guide for directory mapping feature in docs/user-guide/", model="haiku")
```

**Batch 5.2** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P5.1b: E2E test for cross-source deduplication - two sources with overlapping artifacts", model="sonnet")
Task("documentation-writer", "P5.2b: Update API documentation with manual_map examples and dedup response fields", model="haiku")
```

**Batch 5.3** (Parallel - 2 tasks):
```
Task("python-backend-engineer", "P5.1c: Edge case tests - empty mappings, invalid paths, large repos, timeout scenarios", model="sonnet")
Task("documentation-writer", "P5.2c: Create developer guide for deduplication engine architecture and extension points", model="haiku")
```

**Batch 5.4** (Sequential - 1 task):
```
Task("python-backend-engineer", "P5.1d: Performance benchmark for 1000+ artifacts with deduplication enabled", model="sonnet")
```

**Batch 5.5** (Sequential - 1 task):
```
Task("python-backend-engineer", "P5.3a: Create deployment checklist - database validation, feature flag, rollback plan", model="sonnet")
```

**Batch 5.6** (Sequential - 1 task):
```
Task("python-backend-engineer", "P5.3b: Document rollback procedure - revert manual_map changes, re-scan without dedup", model="sonnet")
```

**Batch 5.7** (Sequential - 1 task):
```
Task("python-backend-engineer", "P5.3c: Set up feature flag for manual mapping and deduplication features", model="sonnet")
```

## Current Status

**Phase**: Not Started
**Next Action**: Begin Phase 1 - Database & Schema validation
**Blocked**: None

## Quality Gates

### Phase 1 Gates
- [ ] manual_map column validated in MarketplaceSource model
- [ ] metadata_json column validated in MarketplaceCatalogEntry model
- [ ] Schema documentation created with examples
- [ ] Pydantic schemas compile and validate test data

### Phase 2 Gates
- [ ] All unit tests pass (>70% coverage for new code)
- [ ] Integration tests pass for scan workflow
- [ ] Performance benchmark <120s for 1000 artifacts
- [ ] Manual mappings apply correctly with hierarchical inheritance
- [ ] Deduplication removes expected duplicates

### Phase 3 Gates
- [ ] PATCH endpoint accepts and persists manual_map
- [ ] GET endpoint returns manual_map correctly
- [ ] Rescan endpoint uses manual_map and returns dedup counts
- [ ] OpenAPI docs updated and validated
- [ ] Error handling tested for all edge cases

### Phase 4 Gates
- [ ] DirectoryMapModal renders file tree correctly
- [ ] Hierarchical selection works (parent → children)
- [ ] Save persists mappings via PATCH endpoint
- [ ] Rescan triggers scan with new mappings
- [ ] Dedup counts displayed in UI correctly
- [ ] All UI components tested with unit tests

### Phase 5 Gates
- [ ] E2E tests pass for full workflow
- [ ] Cross-source dedup tested and verified
- [ ] Edge cases handled gracefully
- [ ] Performance meets <120s requirement
- [ ] Documentation complete and reviewed
- [ ] Deployment checklist validated

## Risk Log

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Dedup timeout on large repos | High | Lazy hashing, caching, 10MB file limit, 120s timeout | Mitigated |
| Hash collisions | Low | SHA256 (2^256 space), logging on collision | Acceptable |
| GitHub rate limits on tree fetch | Medium | Cache tree data in metadata_json, batch validation | Mitigated |
| Invalid directory paths in mappings | Medium | Validate paths against GitHub tree before saving | Mitigated |
| UI complexity for large repos | Medium | Virtualized tree rendering, search/filter | Planned |

## Notes

- **PRD**: `/docs/project_plans/PRDs/features/marketplace-source-detection-improvements-v1.md`
- **Implementation Plan**: `/docs/project_plans/implementation_plans/features/marketplace-source-detection-improvements-v1.md`
- **Request**: REQ-20260104-skillmeat
- **Total Estimated Effort**: 65-96 story points
- **Estimated Duration**: 16-21 days
- **No database migrations needed** - reusing existing columns (manual_map, metadata_json)
