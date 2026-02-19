---
type: progress
prd: collection-refresh
phase: 4
title: Update Detection & Advanced Features
status: pending
progress: 0
created: 2025-01-21
updated: 2025-01-21
tasks:
- id: BE-401
  name: Implement check_updates() method
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 1.5 pts
- id: BE-402
  name: Integrate with SyncManager.check_drift()
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  estimate: 1 pt
- id: BE-403
  name: Implement --check-only CLI flag
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  estimate: 0.75 pts
- id: BE-404
  name: Add API query parameter mode=check
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  estimate: 0.75 pts
- id: BE-405
  name: Add field whitelist configuration
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 0.75 pts
- id: BE-406
  name: Implement field-selective CLI flag
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-405
  estimate: 0.75 pts
- id: BE-407
  name: Add field validation
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-405
  estimate: 0.5 pts
- id: BE-408
  name: Implement refresh snapshot creation
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 0.75 pts
- id: BE-409
  name: Add --rollback flag to CLI
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-408
  estimate: 0.75 pts
- id: BE-410
  name: Document rollback procedure
  status: pending
  assigned_to:
  - documentation-writer
  dependencies:
  - BE-408
  estimate: 0.5 pts
  model: haiku
- id: BE-411
  name: 'Unit tests: update detection'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  estimate: 1 pt
- id: BE-412
  name: 'Unit tests: field selective refresh'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-405
  estimate: 0.75 pts
- id: BE-413
  name: 'Integration test: end-to-end update flow'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-401
  estimate: 1.5 pts
- id: BE-414
  name: 'Performance: large collection refresh'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 1 pt
- id: BE-415
  name: 'Stress test: concurrent refreshes'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 1 pt
parallelization:
  batch_1:
  - BE-401
  - BE-405
  - BE-408
  batch_2:
  - BE-402
  - BE-403
  - BE-404
  - BE-406
  - BE-407
  - BE-409
  - BE-410
  batch_3:
  - BE-411
  - BE-412
  - BE-413
  - BE-414
  - BE-415
quality_gates:
- check_updates() correctly compares SHAs and detects available updates
- SyncManager integration provides accurate drift detection
- --check-only CLI flag works and displays update summary
- API mode=check query parameter returns correct results
- Field whitelist configuration recognized and applied
- --fields CLI flag filters refresh to specified fields only
- Invalid field names rejected with helpful error message
- Pre-refresh snapshots created and tagged correctly
- Rollback restores collection to pre-refresh state
- All unit tests pass with >90% coverage
- Integration tests pass with real-world scenarios
- Performance acceptable for large collections
- Thread-safe and handles concurrent operations
schema_version: 2
doc_type: progress
feature_slug: collection-refresh
---

# Phase 4: Update Detection & Advanced Features

**Duration**: 4-5 days | **Total Effort**: 13.25 story points | **Status**: Pending

## Overview

Add advanced features including SHA-based update detection, selective field refresh, and rollback support. This phase enhances the refresh system with safety features and integration with existing sync infrastructure.

## Key Files

| File | Action | Purpose |
|------|--------|---------|
| `skillmeat/core/refresher.py` | MODIFY | Add check_updates(), field filtering |
| `skillmeat/cli.py` | MODIFY | Add --check-only, --fields, --rollback flags |
| `skillmeat/api/routers/collections.py` | MODIFY | Add mode=check support |
| `docs/guides/artifact-refresh-guide.md` | CREATE | User documentation |
| `tests/unit/test_refresher.py` | MODIFY | Add advanced feature tests |

## Dependencies

- Phase 1 must be complete
- Phases 2 and 3 are optional (features work independently)
- Uses existing SyncManager.check_drift() for drift detection

## Features Added

### Update Detection
```bash
# Check for updates without applying
skillmeat collection refresh --check-only

# API mode
POST /api/v1/collections/default/refresh?mode=check
```

### Selective Field Refresh
```bash
# Refresh only specific fields
skillmeat collection refresh --fields "description,tags"
```

### Rollback Support
```bash
# Rollback to pre-refresh state
skillmeat collection refresh --rollback
```

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-refresh/phase-4-progress.md \
  -t BE-401 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-refresh/phase-4-progress.md \
  --updates "BE-401:completed,BE-402:completed"
```

## Delegation Commands

```python
# Update detection (batch_1 partial)
Task("python-backend-engineer", """
Implement Phase 4 update detection for collection-refresh:
- BE-401: Implement check_updates() method comparing upstream SHAs
- BE-402: Integrate with SyncManager.check_drift()
- BE-403: Add --check-only CLI flag
- BE-404: Add API mode=check support

Leverage existing SyncManager in skillmeat/core/sync.py.
Reference: docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md
""")

# Selective refresh & rollback (batch_1 partial + batch_2)
Task("python-backend-engineer", """
Implement Phase 4 advanced features:
- BE-405: Field whitelist configuration
- BE-406: --fields CLI flag
- BE-407: Field validation
- BE-408: Pre-refresh snapshot creation
- BE-409: --rollback CLI flag

Reference: docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md
""")

# Documentation
Task("documentation-writer", """
Create user guide for artifact refresh feature:
- BE-410: docs/guides/artifact-refresh-guide.md
- Topics: when to use refresh vs re-import, understanding diff output,
  dry-run workflow, troubleshooting, performance considerations
""", model="haiku")
```

## Notes

- Can begin after Phase 1, independent of Phases 2 and 3
- SyncManager already provides three-way merge drift detection
- Snapshots use existing snapshot infrastructure
- Performance benchmarks critical for large collections
