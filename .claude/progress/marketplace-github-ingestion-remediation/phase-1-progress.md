---
type: progress
prd: "marketplace-github-ingestion-remediation"
phase: 1
title: "Wire Existing Components"
status: "completed"
started: "2025-12-26T15:00:00Z"
completed: "2025-12-26T15:30:00Z"

overall_progress: 100
completion_estimate: "on-track"

total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0

owners: ["python-backend-engineer"]
contributors: []

tasks:
  - id: "REM-1.1"
    description: "Wire Heuristic Import - uncomment import in github_scanner.py:30-34"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: []
    estimated_effort: "5min"
    priority: "critical"
    file: "skillmeat/core/marketplace/github_scanner.py"
    lines: "30-34"

  - id: "REM-1.2"
    description: "Wire Detector Init - uncomment self.detector = HeuristicDetector() in line 101"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REM-1.1"]
    estimated_effort: "5min"
    priority: "critical"
    file: "skillmeat/core/marketplace/github_scanner.py"
    lines: "101"

  - id: "REM-1.3"
    description: "Wire scan_repository - uncomment detect_artifacts_in_tree call, remove placeholder"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REM-1.2"]
    estimated_effort: "10min"
    priority: "critical"
    file: "skillmeat/core/marketplace/github_scanner.py"
    lines: "159-174"

  - id: "REM-1.4"
    description: "Wire scan_github_source - uncomment detect_artifacts_in_tree call, remove placeholder"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REM-1.2"]
    estimated_effort: "10min"
    priority: "critical"
    file: "skillmeat/core/marketplace/github_scanner.py"
    lines: "464-478"

  - id: "REM-1.5"
    description: "Wire Diff Engine - replace hardcoded new_entries=[] with CatalogDiffEngine call"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["REM-1.3"]
    estimated_effort: "15min"
    priority: "high"
    file: "skillmeat/api/routers/marketplace_sources.py"
    lines: "545-548"

parallelization:
  batch_1: ["REM-1.1"]
  batch_2: ["REM-1.2"]
  batch_3: ["REM-1.3", "REM-1.4"]
  batch_4: ["REM-1.5"]
  critical_path: ["REM-1.1", "REM-1.2", "REM-1.3", "REM-1.5"]
  estimated_total_time: "45min"

blockers: []

success_criteria:
  - All imports resolve without circular dependency errors
  - python -m skillmeat.core.marketplace.heuristic_detector shows detection output
  - pytest tests/core/marketplace/test_heuristic_detector.py passes
  - Scanner returns non-empty artifacts for test repo

files_modified:
  - "skillmeat/core/marketplace/github_scanner.py"
  - "skillmeat/api/routers/marketplace_sources.py"
---

# Phase 1: Wire Existing Components

**Status:** Pending | **Owner:** python-backend-engineer | **Est. Effort:** 45 min

## Overview

Wire the fully-implemented heuristic detector and diff engine into the GitHub scanner. All code exists but is commented out or stubbed. This phase requires only uncommenting code and removing placeholder stubs.

## Root Cause

PR #26 (commit 1fc65c6) was merged with detection code commented out. The warning "Heuristic detector not yet implemented (SVC-002)" appears despite the detector being fully implemented.

## Orchestration Quick Reference

**Batch Execution:**
- Batch 1: REM-1.1 (sequential - import must come first)
- Batch 2: REM-1.2 (sequential - init requires import)
- Batch 3: REM-1.3, REM-1.4 (parallel - both require init)
- Batch 4: REM-1.5 (sequential - requires scanner working)

### Task Delegation Commands

```python
Task("python-backend-engineer", """REM-1.1 through REM-1.4: Wire heuristic detector in github_scanner.py.

File: skillmeat/core/marketplace/github_scanner.py

Changes needed:

1. Lines 30-34 - UNCOMMENT the import block:
   from skillmeat.core.marketplace.heuristic_detector import (
       HeuristicDetector,
       detect_artifacts_in_tree,
   )

2. Line 101 - UNCOMMENT the detector initialization:
   self.detector = HeuristicDetector()

3. Lines 159-174 - In scan_repository():
   - UNCOMMENT lines 161-166 (base_url and detect_artifacts_in_tree call)
   - DELETE lines 169-174 (placeholder returning empty list with warning)

4. Lines 464-478 - In scan_github_source():
   - UNCOMMENT lines 464-470 (detect_artifacts_in_tree call)
   - DELETE lines 473-478 (placeholder returning empty list with warning)

Verification: python -m skillmeat.core.marketplace.heuristic_detector
Expected output: "Detected N artifacts:" with confidence scores""")
```

```python
Task("python-backend-engineer", """REM-1.5: Wire diff engine in marketplace_sources.py.

File: skillmeat/api/routers/marketplace_sources.py
Location: rescan_source() endpoint, around line 545

Current code to REPLACE:
```python
# TODO: Use diff engine for incremental updates
# Currently heuristic detector returns empty list, so this is a placeholder
new_entries: List[MarketplaceCatalogEntry] = []
ctx.replace_catalog_entries(new_entries)
```

Replace with:
```python
from skillmeat.core.marketplace.diff_engine import CatalogDiffEngine

# Compute diff between existing and new catalog
diff_engine = CatalogDiffEngine()
existing_entries = catalog_repo.get_source_catalog(source_id=source_id)

# Build diff input from scan result
new_catalog_data = [
    {
        "artifact_type": a.artifact_type,
        "name": a.name,
        "path": a.path,
        "upstream_url": a.upstream_url,
        "confidence_score": a.confidence_score,
        "detected_sha": a.detected_sha,
    }
    for a in scan_result.artifacts
]

diff_result = diff_engine.compute_diff(
    [e.to_dict() for e in existing_entries],
    new_catalog_data,
    source_id,
)

# Apply diff
for entry in diff_result.new_entries:
    new_entry = MarketplaceCatalogEntry(
        id=str(uuid.uuid4()),
        source_id=source_id,
        **entry.new_data,
    )
    session.add(new_entry)

for entry in diff_result.updated_entries:
    if entry.existing_entry_id:
        catalog_repo.update(entry.existing_entry_id, entry.new_data)

for entry in diff_result.removed_entries:
    if entry.existing_entry_id:
        catalog_repo.update(entry.existing_entry_id, {"status": "removed"})

session.commit()
```

Note: Adjust based on actual diff_engine interface. Check diff_engine.py for exact method signatures.""")
```

## Tasks

| Task ID | Description | Status | Dependencies | Est. |
|---------|-------------|--------|--------------|------|
| REM-1.1 | Uncomment heuristic import | Pending | None | 5min |
| REM-1.2 | Uncomment detector init | Pending | REM-1.1 | 5min |
| REM-1.3 | Wire scan_repository | Pending | REM-1.2 | 10min |
| REM-1.4 | Wire scan_github_source | Pending | REM-1.2 | 10min |
| REM-1.5 | Wire diff engine | Pending | REM-1.3 | 15min |

## Verification Steps

After completing all tasks:

```bash
# 1. Verify import works
python -c "from skillmeat.core.marketplace.github_scanner import GitHubScanner; print('Import OK')"

# 2. Verify detector works standalone
python -m skillmeat.core.marketplace.heuristic_detector

# 3. Run unit tests
pytest tests/core/marketplace/test_heuristic_detector.py -v
pytest tests/core/marketplace/test_github_scanner.py -v

# 4. Integration test - scan a real repo
curl -X POST http://localhost:8000/api/v1/marketplace/sources \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/anthropics/anthropic-quickstarts", "ref": "main"}'
# Should return artifacts_found > 0
```

## Blockers

None identified.

## Next Phase

After Phase 1 completes, proceed to Phase 2 (Frontmatter Detection Toggle) or directly to Phase 4 (Validation) for quick verification.
