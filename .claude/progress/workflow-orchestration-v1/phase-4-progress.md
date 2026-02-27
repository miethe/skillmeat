---
type: progress
prd: workflow-orchestration-v1
phase: 4
title: CLI Commands
status: pending
started: null
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 11
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors: []
tasks:
- id: CLI-4.1
  description: Create 'skillmeat workflow' Click command group
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - API-3.9
  estimated_effort: 1 pt
  priority: critical
- id: CLI-4.2
  description: 'workflow create <path>: read YAML, validate, store in collection +
    DB'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  - SVC-3.1
  estimated_effort: 2 pts
  priority: critical
- id: CLI-4.3
  description: workflow list [--status] [--tag] [--format table|json]
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  estimated_effort: 1 pt
  priority: high
- id: CLI-4.4
  description: 'workflow show <name>: display definition, stages, last execution'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  estimated_effort: 1 pt
  priority: high
- id: CLI-4.5
  description: 'workflow validate <path>: validate YAML without importing'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  - SVC-3.2
  estimated_effort: 1 pt
  priority: high
- id: CLI-4.6
  description: 'workflow plan <name> [--param key=val]: generate and display execution
    plan'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  - SVC-3.3
  estimated_effort: 2 pts
  priority: high
- id: CLI-4.7
  description: 'workflow run <name> [--param key=val] [--dry-run]: execute with Rich
    live display'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  - SVC-3.4
  estimated_effort: 3 pts
  priority: critical
- id: CLI-4.8
  description: 'workflow runs [<run_id>] [--logs] [--status]: list/show run details'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  estimated_effort: 1 pt
  priority: medium
- id: CLI-4.9
  description: 'workflow approve/cancel: gate approval and execution cancellation'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.1
  - SVC-3.6
  estimated_effort: 1 pt
  priority: medium
- id: CLI-4.10
  description: 'Collection manifest integration: type=workflow in TOML, skillmeat
    list includes workflows'
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.2
  - PREP-0.5
  estimated_effort: 1 pt
  priority: high
- id: TEST-4.11
  description: CLI unit tests for all commands with mocked services
  status: pending
  assigned_to:
  - python-backend-engineer
  dependencies:
  - CLI-4.10
  estimated_effort: 2 pts
  priority: high
parallelization:
  batch_1:
  - CLI-4.1
  batch_2:
  - CLI-4.2
  - CLI-4.3
  - CLI-4.4
  - CLI-4.5
  batch_3:
  - CLI-4.6
  - CLI-4.7
  - CLI-4.8
  - CLI-4.9
  batch_4:
  - CLI-4.10
  batch_5:
  - TEST-4.11
  critical_path:
  - CLI-4.1
  - CLI-4.7
  - CLI-4.10
  - TEST-4.11
  estimated_total_time: 5-7 days
blockers: []
success_criteria:
- id: SC-4.1
  description: All 9 CLI subcommands functional
  status: pending
- id: SC-4.2
  description: workflow run shows live progress with Rich
  status: pending
- id: SC-4.3
  description: Collection manifest supports workflow entries
  status: pending
- id: SC-4.4
  description: CLI tests passing
  status: pending
files_modified:
- skillmeat/cli.py
- skillmeat/cli/workflow.py
- tests/test_workflow_cli.py
schema_version: 2
doc_type: progress
feature_slug: workflow-orchestration-v1
progress: 45
updated: '2026-02-27'
---

# workflow-orchestration-v1 - Phase 4: CLI Commands

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

---

## Objective

Implement the full `skillmeat workflow` CLI command group with 9 subcommands for creating, validating, planning, running, and managing workflows from the terminal.

---

## Implementation Notes

### Parallel with Phase 5
This phase can run entirely in parallel with Phase 5 (Frontend). Both depend on Phase 3 API being complete but are independent of each other.

### Rich Output
Use Rich library for formatted terminal output (ASCII-compatible, no Unicode box-drawing per CLAUDE.md).
