---
type: progress
prd: collection-refresh
phase: 1
title: Core CollectionRefresher Class & Data Models
status: pending
progress: 0
created: 2025-01-21
updated: 2025-01-21
tasks:
- id: BE-101
  name: Create RefreshEntryResult dataclass
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.5 pts
- id: BE-102
  name: Create RefreshResult dataclass
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.5 pts
- id: BE-103
  name: Create RefreshMode enum
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.25 pts
- id: BE-104
  name: Define field mapping config
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.25 pts
- id: BE-105
  name: Create CollectionRefresher class skeleton
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.5 pts
- id: BE-106
  name: Implement _parse_source_spec()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.75 pts
- id: BE-107
  name: Implement _fetch_upstream_metadata()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 1 pt
- id: BE-108
  name: Implement _detect_changes()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.75 pts
- id: BE-109
  name: Implement _apply_updates()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimate: 0.75 pts
- id: BE-110
  name: Implement refresh_metadata()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-106
  - BE-107
  - BE-108
  - BE-109
  estimate: 1.5 pts
- id: BE-111
  name: Implement refresh_collection()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-110
  estimate: 1 pt
- id: BE-112
  name: Add error handling and logging
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-110
  - BE-111
  estimate: 0.75 pts
- id: BE-113
  name: Unit tests for _parse_source_spec()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-106
  estimate: 1 pt
- id: BE-114
  name: Unit tests for _detect_changes()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-108
  estimate: 1 pt
- id: BE-115
  name: Unit tests for _apply_updates()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-109
  estimate: 1 pt
- id: BE-116
  name: Unit tests for refresh_metadata()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-110
  estimate: 1.5 pts
- id: BE-117
  name: Unit tests for refresh_collection()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-111
  estimate: 1.5 pts
- id: BE-118
  name: Mock GitHub API tests
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-107
  - BE-110
  estimate: 1 pt
parallelization:
  batch_1:
  - BE-101
  - BE-102
  - BE-103
  - BE-104
  - BE-105
  batch_2:
  - BE-106
  - BE-107
  - BE-108
  - BE-109
  batch_3:
  - BE-110
  batch_4:
  - BE-111
  - BE-112
  batch_5:
  - BE-113
  - BE-114
  - BE-115
  - BE-116
  - BE-117
  - BE-118
quality_gates:
- All dataclasses defined with correct type hints
- RefreshResult accurately tracks counts and durations
- _parse_source_spec() correctly parses all supported source formats
- _detect_changes() identifies all changed fields with old/new values
- refresh_metadata() returns RefreshEntryResult with correct status
- refresh_collection() aggregates results and maintains error summary
- Unit tests pass with >90% code coverage for refresher module
- No TypeScript/Pylint errors
- Error handling prevents crashes; all errors captured in RefreshResult
- Integration with existing managers works correctly
schema_version: 2
doc_type: progress
feature_slug: collection-refresh
---

# Phase 1: Core CollectionRefresher Class & Data Models

**Duration**: 5-7 days | **Total Effort**: 15.5 story points | **Status**: Pending

## Overview

Build the core `CollectionRefresher` class that enables refreshing artifact metadata from upstream GitHub sources. This phase establishes the foundation for CLI and API integration in subsequent phases.

## Key Files

| File | Action | Purpose |
|------|--------|---------|
| `skillmeat/core/refresher.py` | CREATE | CollectionRefresher class and data models |
| `tests/unit/test_refresher.py` | CREATE | Unit test suite |

## Dependencies (Existing Infrastructure)

- `skillmeat/core/github_metadata.py` - GitHubMetadataExtractor
- `skillmeat/core/github_client.py` - GitHubClient
- `skillmeat/core/collection.py` - CollectionManager
- `skillmeat/core/artifact.py` - Artifact model

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-refresh/phase-1-progress.md \
  -t BE-101 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-refresh/phase-1-progress.md \
  --updates "BE-101:completed,BE-102:completed"
```

## Delegation Commands

```python
# Data models (batch_1)
Task("python-backend-engineer", """
Implement Phase 1 batch_1 for collection-refresh:
- BE-101: Create RefreshEntryResult dataclass in skillmeat/core/refresher.py
- BE-102: Create RefreshResult dataclass
- BE-103: Create RefreshMode enum
- BE-104: Define field mapping config
- BE-105: Create CollectionRefresher class skeleton

Reference: docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md
""")

# Core methods (batch_2)
Task("python-backend-engineer", """
Implement Phase 1 batch_2 for collection-refresh:
- BE-106: Implement _parse_source_spec()
- BE-107: Implement _fetch_upstream_metadata()
- BE-108: Implement _detect_changes()
- BE-109: Implement _apply_updates()

Use existing GitHubMetadataExtractor and GitHubClient patterns.
Reference: docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md
""")
```

## Notes

- Critical path: All other phases depend on Phase 1 completion
- No database changes needed - uses existing artifact storage
- Leverage existing GitHubMetadataExtractor for upstream fetching
