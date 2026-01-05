---
type: progress
prd: "marketplace-source-detection-improvements"
phase: 2
phase_name: "Backend Detection Engine"
status: not_started
progress: 0
total_tasks: 18
completed_tasks: 0
effort: "20-30 pts"
created: 2026-01-05
updated: 2026-01-05

assigned_to: ["python-backend-engineer"]
dependencies: [1]

tasks:
  # Manual Mapping (5 tasks)
  - id: "P2.1a"
    name: "Update detector signature"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1.4"]
    effort: "2 pts"

  - id: "P2.1b"
    name: "Implement directory matching"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1a"]
    effort: "5 pts"

  - id: "P2.1c"
    name: "Apply hierarchical inheritance"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1b"]
    effort: "3 pts"

  - id: "P2.1d"
    name: "Set confidence scoring"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1c"]
    effort: "2 pts"

  - id: "P2.1e"
    name: "Unit tests for mapping"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1d"]
    effort: "3 pts"

  # Content Hashing (4 tasks)
  - id: "P2.2a"
    name: "Implement SHA256 hashing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P1.4"]
    effort: "3 pts"

  - id: "P2.2b"
    name: "Add hash caching"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2a"]
    effort: "2 pts"

  - id: "P2.2c"
    name: "Add file size limit"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2a"]
    effort: "2 pts"

  - id: "P2.2d"
    name: "Unit tests for hashing"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2b", "P2.2c"]
    effort: "3 pts"

  # Deduplication (5 tasks)
  - id: "P2.3a"
    name: "Create DeduplicationEngine class"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.2a"]
    effort: "4 pts"

  - id: "P2.3b"
    name: "Implement within-source dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3a"]
    effort: "4 pts"

  - id: "P2.3c"
    name: "Implement cross-source dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3b"]
    effort: "4 pts"

  - id: "P2.3d"
    name: "Implement exclusion marking"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3c"]
    effort: "2 pts"

  - id: "P2.3e"
    name: "Unit tests for dedup"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.3d"]
    effort: "4 pts"

  # Integration (4 tasks)
  - id: "P2.4a"
    name: "Wire into scan workflow"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.1e", "P2.3e"]
    effort: "3 pts"

  - id: "P2.4b"
    name: "Return dedup counts"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4a"]
    effort: "2 pts"

  - id: "P2.4c"
    name: "Integration tests"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4b"]
    effort: "3 pts"

  - id: "P2.4d"
    name: "Performance validation"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["P2.4c"]
    effort: "2 pts"

parallelization:
  batch_1: ["P2.1a", "P2.2a"]
  batch_2: ["P2.1b", "P2.2b", "P2.2c"]
  batch_3: ["P2.1c", "P2.2d", "P2.3a"]
  batch_4: ["P2.1d", "P2.3b"]
  batch_5: ["P2.1e", "P2.3c"]
  batch_6: ["P2.3d"]
  batch_7: ["P2.3e"]
  batch_8: ["P2.4a"]
  batch_9: ["P2.4b"]
  batch_10: ["P2.4c"]
  batch_11: ["P2.4d"]
---

# Phase 2: Backend Detection Engine

## Overview

Implement manual directory mapping, content hashing, and deduplication engine.

**Duration**: 5-7 days
**Effort**: 20-30 pts
**Assigned**: python-backend-engineer
**Dependencies**: Phase 1 complete

## Orchestration Quick Reference

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

## Quality Gates

- [ ] All unit tests pass (>70% coverage for new code)
- [ ] Integration tests pass for scan workflow
- [ ] Performance benchmark <120s for 1000 artifacts
- [ ] Manual mappings apply correctly with hierarchical inheritance
- [ ] Deduplication removes expected duplicates

## Key Files

- `skillmeat/core/marketplace/heuristic_detector.py` - Manual mapping logic
- `skillmeat/core/marketplace/deduplication_engine.py` - New file for dedup
- `skillmeat/core/marketplace/github_scanner.py` - Scan workflow integration
- `tests/test_marketplace_detection.py` - Unit and integration tests

## Notes

- **Confidence Scores**: manual=95, parent_match=90
- **File Size Limit**: 10MB for hashing
- **Performance Target**: <120s for 1000 artifacts
- **Dedup Strategy**: Keep highest confidence artifact, mark others as excluded
