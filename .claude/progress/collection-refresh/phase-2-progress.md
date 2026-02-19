---
type: progress
prd: collection-refresh
phase: 2
title: CLI Command Implementation
status: pending
progress: 0
created: 2025-01-21
updated: 2025-01-21
tasks:
- id: BE-201
  name: Create collection refresh command
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 1 pt
- id: BE-202
  name: Implement --metadata-only flag
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.5 pts
- id: BE-203
  name: Implement --dry-run flag
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.75 pts
- id: BE-204
  name: Implement --check flag
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - Phase 1
  estimate: 1 pt
- id: BE-205
  name: Implement --collection option
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.5 pts
- id: BE-206
  name: Add artifact filtering (--type, --name)
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.5 pts
- id: BE-207
  name: Implement progress tracking
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.75 pts
- id: BE-208
  name: Implement results summary table
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 1 pt
- id: BE-209
  name: Implement change details output
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.75 pts
- id: BE-210
  name: Implement error reporting
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.5 pts
- id: BE-211
  name: Implement dry-run indicator
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-203
  estimate: 0.25 pts
- id: BE-212
  name: Color-code status badges
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.5 pts
- id: BE-213
  name: 'Integration test: basic refresh'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 1.5 pts
- id: BE-214
  name: 'Integration test: --dry-run mode'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-203
  estimate: 1 pt
- id: BE-215
  name: 'Integration test: --metadata-only flag'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-202
  estimate: 1 pt
- id: BE-216
  name: 'Integration test: --check mode'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-204
  estimate: 1 pt
- id: BE-217
  name: 'Integration test: error handling'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - BE-201
  estimate: 0.75 pts
parallelization:
  batch_1:
  - BE-201
  batch_2:
  - BE-202
  - BE-203
  - BE-204
  - BE-205
  - BE-206
  batch_3:
  - BE-207
  - BE-208
  - BE-209
  - BE-210
  - BE-211
  - BE-212
  batch_4:
  - BE-213
  - BE-214
  - BE-215
  - BE-216
  - BE-217
quality_gates:
- '`skillmeat collection refresh` command executes without errors'
- All flags (--dry-run, --metadata-only, --check, --collection) work correctly
- Progress output shows current artifact and progress count
- Results table displays all refreshed artifacts with changes
- Change details show old/new values in readable format
- Errors captured and displayed without crashing CLI
- Dry-run mode prevents manifest writes
- Integration tests pass with real collection data
- Exit codes correct (0 for success, 1 for errors)
schema_version: 2
doc_type: progress
feature_slug: collection-refresh
---

# Phase 2: CLI Command Implementation

**Duration**: 3-4 days | **Total Effort**: 13.25 story points | **Status**: Pending

## Overview

Implement the `skillmeat collection refresh` CLI command with rich console output, progress tracking, and comprehensive flag support for different refresh modes.

## Key Files

| File | Action | Purpose |
|------|--------|---------|
| `skillmeat/cli.py` | MODIFY | Add collection refresh command group |
| `tests/integration/test_refresh_cli.py` | CREATE | CLI integration tests |

## Dependencies

- Phase 1 must be complete (CollectionRefresher tested and ready)
- Uses Click library (existing)
- Uses Rich library for console output (existing)

## CLI Usage Preview

```bash
# Basic refresh
skillmeat collection refresh

# Preview changes without saving
skillmeat collection refresh --dry-run

# Refresh only metadata fields
skillmeat collection refresh --metadata-only

# Check for available updates
skillmeat collection refresh --check

# Target specific collection
skillmeat collection refresh --collection work

# Filter by artifact type
skillmeat collection refresh --type skill
```

## Quick Reference

```bash
# Update task status
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/collection-refresh/phase-2-progress.md \
  -t BE-201 -s completed

# Batch update
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/collection-refresh/phase-2-progress.md \
  --updates "BE-201:completed,BE-202:completed"
```

## Delegation Commands

```python
# CLI command (batch_1 + batch_2)
Task("python-backend-engineer", """
Implement Phase 2 for collection-refresh CLI:
- BE-201: Create `skillmeat collection refresh` command
- BE-202: --metadata-only flag
- BE-203: --dry-run flag
- BE-204: --check flag
- BE-205: --collection option
- BE-206: --type, --name filter flags

Wire to CollectionRefresher from Phase 1.
Use Click patterns from existing CLI commands.
Reference: docs/project_plans/implementation_plans/features/collection-artifact-refresh-v1.md
""")

# Rich output (batch_3)
Task("python-backend-engineer", """
Implement CLI rich output for collection refresh:
- BE-207: Progress tracking with spinner/bar
- BE-208: Results summary table
- BE-209: Change details (old/new values)
- BE-210: Error reporting section
- BE-211: Dry-run indicator header
- BE-212: Color-coded status badges

Use Rich library patterns from existing CLI.
""")
```

## Notes

- Can run in parallel with Phase 3 (API endpoint)
- Rich output should match existing CLI aesthetics
- Progress bar using Rich Progress or spinner
