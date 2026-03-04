---
type: progress
schema_version: 2
doc_type: progress
prd: backstage-integration-demo
feature_slug: backstage-integration-demo
prd_ref: docs/project_plans/PRDs/integrations/backstage-integration-demo.md
plan_ref: null
phase: 3
title: Demo Environment & Data
status: completed
started: null
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 4
completed_tasks: 4
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- python-backend-engineer
contributors:
- documentation-writer
- platform-engineer
tasks:
- id: TASK-3.1
  description: 'Create fin-serv-compliance composite seed data script — composite
    type ''stack'' with three member artifacts: CLAUDE.md (ProjectConfig), agent:db-architect,
    mcp:internal-db-explorer'
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 3h
  priority: high
- id: TASK-3.2
  description: Author docker-compose.demo.yml — SAM API/UI, local Backstage with plugin
    mounted, mock PostgreSQL for MCP target
  status: completed
  assigned_to:
  - python-backend-engineer
  - platform-engineer
  dependencies:
  - TASK-1.5
  - TASK-2.4
  estimated_effort: 4h
  priority: high
- id: TASK-3.3
  description: Author Backstage template.yaml example with fetch:template, skillmeat:context:inject,
    publish:github, and skillmeat:deployment:register steps
  status: completed
  assigned_to:
  - python-backend-engineer
  - platform-engineer
  dependencies:
  - TASK-2.4
  estimated_effort: 2h
  priority: high
- id: TASK-3.4
  description: Write DEMO_GUIDE.md with end-to-end walkthrough narrative for GTM demo
  status: completed
  assigned_to:
  - documentation-writer
  dependencies:
  - TASK-3.2
  - TASK-3.3
  estimated_effort: 2h
  priority: medium
parallelization:
  batch_1:
  - TASK-3.1
  batch_2:
  - TASK-3.2
  - TASK-3.3
  batch_3:
  - TASK-3.4
  critical_path:
  - TASK-3.1
  - TASK-3.2
  - TASK-3.4
  estimated_total_time: 9h
blockers:
- id: BLOCKER-P3-001
  title: Phase 1 and Phase 2 must be complete for full demo integration
  severity: high
  blocking:
  - TASK-3.2
  - TASK-3.3
  resolution: Phase 1 (TASK-1.5) and Phase 2 (TASK-2.4) completion
  created: '2026-03-03'
success_criteria:
- id: SC-1
  description: docker-compose demo-up starts all services healthy on macOS and Linux
  status: pending
- id: SC-2
  description: Backstage template creates GitHub repo with .claude/ directory
  status: pending
- id: SC-3
  description: Agent in cloned repo uses injected CLAUDE.md constraints without manual
    setup
  status: pending
- id: SC-4
  description: DEMO_GUIDE.md is reproducible by a new operator
  status: pending
files_modified: []
progress: 100
updated: '2026-03-03'
---

# backstage-integration-demo - Phase 3: Demo Environment & Data

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/backstage-integration-demo/phase-3-progress.md -t TASK-X -s completed
```

---

## Objective

Create the complete demo environment: seed composite data, docker-compose stack, Backstage template, and walkthrough guide. This phase produces the reproducible GTM demo for enterprise pilot engagements.

---

## Implementation Notes

### Architectural Decisions

- Demo composite uses `stack` type with ordered members via `CompositeMembership.position`.
- Docker Compose uses `postgres:15-alpine` for mock MCP target database.
- Backstage instance mounts the plugin from Phase 2 via volume or npm link.

### Known Gotchas

- Docker networking between SAM API and Backstage containers needs shared network.
- Backstage startup is slow (~30-60s) — demo guide should note expected wait time.
- Mock PostgreSQL must be pre-seeded with sample financial data for the MCP demo to be meaningful.

---

## Completion Notes

_Fill in when phase is complete._
