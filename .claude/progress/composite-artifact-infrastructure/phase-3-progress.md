---
type: progress
prd: composite-artifact-infrastructure
phase: 3
title: Import Orchestration & Deduplication (Core)
status: completed
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 9
completed_tasks: 9
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
- backend-architect
contributors:
- code-reviewer
tasks:
- id: CAI-P3-01
  description: Implement SHA-256 content hash computation for skills (tree hash) and
    single-file artifacts
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P2-05
  estimated_effort: 1pt
  priority: high
- id: CAI-P3-02
  description: 'Implement dedup logic: hash lookup -> link existing / new version
    / create new'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CAI-P3-01
  estimated_effort: 2pt
  priority: high
- id: CAI-P3-03
  description: Wrap plugin import (children + parent + associations) in single DB
    transaction with rollback
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P3-02
  estimated_effort: 2pt
  priority: critical
- id: CAI-P3-04
  description: Record pinned_version_hash in ArtifactAssociation at import time
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P3-03
  estimated_effort: 1pt
  priority: high
- id: CAI-P3-05
  description: Extend _get_artifact_type_plural() in sync.py for PLUGIN type
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CAI-P3-04
  estimated_effort: 1pt
  priority: medium
- id: CAI-P3-06
  description: Implement plugins/ directory structure in collection storage
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P3-05
  estimated_effort: 1pt
  priority: medium
- id: CAI-P3-07
  description: Implement GET /artifacts/{id}/associations API endpoint with AssociationsDTO
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P3-06
  estimated_effort: 2pt
  priority: high
- id: CAI-P3-08
  description: 'Integration tests: happy path, dedup scenarios, rollback validation'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CAI-P3-07
  estimated_effort: 2pt
  priority: medium
- id: CAI-P3-09
  description: Add OpenTelemetry spans + structured logs for composite detection,
    hash check, import transaction
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - CAI-P3-08
  estimated_effort: 1pt
  priority: low
parallelization:
  batch_1:
  - CAI-P3-01
  - CAI-P3-02
  batch_2:
  - CAI-P3-03
  - CAI-P3-04
  batch_3:
  - CAI-P3-05
  - CAI-P3-06
  batch_4:
  - CAI-P3-07
  batch_5:
  - CAI-P3-08
  - CAI-P3-09
  critical_path:
  - CAI-P3-01
  - CAI-P3-02
  - CAI-P3-03
  - CAI-P3-07
  - CAI-P3-08
  estimated_total_time: 3-4 days
blockers: []
success_criteria:
- id: SC-P3-1
  description: 'Plugin import happy path: all children + parent + associations in
    single transaction'
  status: pending
- id: SC-P3-2
  description: 'Dedup: re-importing same plugin creates 0 new rows for exact matches'
  status: pending
- id: SC-P3-3
  description: 'Rollback: simulated mid-import failure leaves collection in pre-import
    state'
  status: pending
- id: SC-P3-4
  description: Pinned hash recorded and readable via association repo
  status: pending
- id: SC-P3-5
  description: Sync engine handles PLUGIN type correctly
  status: pending
- id: SC-P3-6
  description: API endpoint returns 200 with AssociationsDTO, 404 for unknown
  status: pending
files_modified:
- skillmeat/core/importer.py
- skillmeat/core/sync.py
- skillmeat/api/routers/artifacts.py
- skillmeat/api/schemas/
- tests/test_import_orchestration.py
progress: 100
updated: '2026-02-18'
---

# composite-artifact-infrastructure - Phase 3: Import Orchestration & Deduplication (Core)

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/composite-artifact-infrastructure/phase-3-progress.md -t CAI-P3-01 -s completed
python .claude/skills/artifact-tracking/scripts/update-batch.py -f .claude/progress/composite-artifact-infrastructure/phase-3-progress.md --updates "CAI-P3-01:completed,CAI-P3-02:completed"
```

---

## Objective

Implement transactional smart import orchestration with SHA-256 deduplication, version pinning, and atomic rollback. Expose associations via API endpoint.

---

## Orchestration Quick Reference

```text
# Batch 1: Hash + dedup (python-backend-engineer, backend-architect)
Task("python-backend-engineer", "Implement SHA-256 content hashing for artifacts.
  Files: skillmeat/core/importer.py
  Task: CAI-P3-01
  Acceptance: Same content -> same hash, different content -> different hash")
Task("backend-architect", "Implement dedup logic with 3 scenarios: link/new-version/create.
  Files: skillmeat/core/importer.py
  Task: CAI-P3-02
  Acceptance: All 3 dedup scenarios handled correctly")

# Batch 2: Transaction + pinning (python-backend-engineer)
Task("python-backend-engineer", "Wrap plugin import in DB transaction with version pinning.
  Files: skillmeat/core/importer.py
  Tasks: CAI-P3-03, CAI-P3-04
  Acceptance: All-or-nothing semantics, rollback on failure, hash stored in association")

# Batch 3: Sync + storage (backend-architect, python-backend-engineer)
Task("python-backend-engineer", "Extend sync engine for PLUGIN + implement plugins/ storage.
  Tasks: CAI-P3-05, CAI-P3-06
  Acceptance: Sync handles plugins, meta-files at ~/.skillmeat/collection/plugins/<name>/")

# Batch 4: API endpoint (python-backend-engineer)
Task("python-backend-engineer", "Implement GET /artifacts/{id}/associations with AssociationsDTO.
  Files: skillmeat/api/routers/artifacts.py, skillmeat/api/schemas/
  Task: CAI-P3-07
  Pattern: Follow existing router patterns in key-context/router-patterns.md
  Acceptance: Returns 200 with DTO for valid ID, 404 for unknown")

# Batch 5: Tests + observability (python-backend-engineer, backend-architect)
Task("python-backend-engineer", "Integration tests for import: happy path, dedup, rollback.
  Task: CAI-P3-08
  Acceptance: All scenarios pass")
Task("backend-architect", "Add OTel spans + structured logs for composite operations.
  Task: CAI-P3-09
  Acceptance: Spans visible in tracing, metrics recorded")
```

---

## Implementation Notes

### Key Files

- `skillmeat/core/importer.py` — Import orchestration, hash computation, dedup
- `skillmeat/core/sync.py` — Sync engine PLUGIN type support
- `skillmeat/api/routers/artifacts.py` — Associations API endpoint
- `skillmeat/api/schemas/` — AssociationsDTO schema
- Implementation plan details: `docs/project_plans/implementation_plans/features/composite-artifact-infrastructure-v1/phase-3-import-orchestration.md`

### Known Gotchas

- SHA-256 for directories: hash all file contents sorted by relative path for deterministic tree hash
- Transaction must wrap children + parent + associations atomically
- Use existing temp-dir + atomic move pattern for filesystem operations
- AssociationsDTO must match OpenAPI contract — regenerate openapi.json after adding endpoint

---

## Completion Notes

_Fill in when phase is complete._
