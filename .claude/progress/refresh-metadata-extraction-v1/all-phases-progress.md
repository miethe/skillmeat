---
type: progress
prd: "refresh-metadata-extraction-v1"
phase: "all"
status: in_progress
progress: 0

tasks:
  # Phase 1: Reusable Extraction Utilities
  - id: "UTIL-001"
    name: "extract_metadata_from_content()"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    phase: 1
  - id: "UTIL-002"
    name: "fetch_and_extract_github_metadata()"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["UTIL-001"]
    phase: 1
  - id: "UTIL-003"
    name: "Unit tests for new utilities"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["UTIL-002"]
    phase: 1

  # Phase 2: Wire Refresher
  - id: "REF-001"
    name: "Update _fetch_upstream_metadata()"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["UTIL-002"]
    phase: 2
  - id: "REF-002"
    name: "Update refresh_metadata() caller"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REF-001"]
    phase: 2
  - id: "REF-003"
    name: "Integration test"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REF-002"]
    phase: 2

  # Phase 3: Cache Database Sync
  - id: "CACHE-001"
    name: "CLI cache invalidation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REF-003"]
    phase: 3

  # Phase 4: Defense-in-Depth (parallel with Phase 3)
  - id: "GHM-001"
    name: "Fix fetch_metadata() single-file handling"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    phase: 4

parallelization:
  batch_1: ["UTIL-001"]
  batch_2: ["UTIL-002"]
  batch_3: ["UTIL-003", "REF-001"]
  batch_4: ["REF-002"]
  batch_5: ["REF-003", "GHM-001"]
  batch_6: ["CACHE-001"]
---

# Refresh Metadata Extraction v1 - All Phases Progress

## Execution Log

### Phase 1: Reusable Extraction Utilities
- Status: pending

### Phase 2: Wire Refresher
- Status: pending

### Phase 3: Cache Database Sync
- Status: pending

### Phase 4: Defense-in-Depth
- Status: pending
