---
type: progress
schema_version: 2
doc_type: progress
prd: backstage-integration-demo
feature_slug: backstage-integration-demo
prd_ref: docs/project_plans/PRDs/integrations/backstage-integration-demo.md
plan_ref: null
phase: 2
title: Backstage Plugin
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
- platform-engineer
contributors: []
tasks:
- id: TASK-2.1
  description: Scaffold @skillmeat/backstage-plugin-scaffolder-backend via @backstage/cli
    create-plugin --backend
  status: completed
  assigned_to:
  - platform-engineer
  dependencies: []
  estimated_effort: 1h
  priority: high
- id: TASK-2.2
  description: "Implement createSkillMeatInjectAction \u2014 calls POST /idp/scaffold,\
    \ writes returned files into Backstage scaffolder workspace using @backstage/integration\
    \ file APIs"
  status: completed
  assigned_to:
  - platform-engineer
  dependencies:
  - TASK-2.1
  - TASK-1.4
  estimated_effort: 4h
  priority: high
- id: TASK-2.3
  description: "Implement createSkillMeatRegisterAction \u2014 calls POST /idp/register-deployment\
    \ after publish:github completes, passing resolved repoUrl"
  status: completed
  assigned_to:
  - platform-engineer
  dependencies:
  - TASK-2.1
  - TASK-1.4
  estimated_effort: 2h
  priority: high
- id: TASK-2.4
  description: Export actions for Backstage host registration; write plugin README
    with installation, configuration, and action schema documentation
  status: completed
  assigned_to:
  - platform-engineer
  dependencies:
  - TASK-2.2
  - TASK-2.3
  estimated_effort: 2h
  priority: medium
parallelization:
  batch_1:
  - TASK-2.1
  batch_2:
  - TASK-2.2
  - TASK-2.3
  batch_3:
  - TASK-2.4
  critical_path:
  - TASK-2.1
  - TASK-2.2
  - TASK-2.4
  estimated_total_time: 7h
blockers:
- id: BLOCKER-P2-001
  title: Phase 1 API endpoints must be complete before plugin can call them
  severity: high
  blocking:
  - TASK-2.2
  - TASK-2.3
  resolution: Phase 1 completion (TASK-1.4)
  created: '2026-03-03'
success_criteria:
- id: SC-1
  description: skillmeat:context:inject action writes .claude/ files into Backstage
    workspace
  status: pending
- id: SC-2
  description: skillmeat:deployment:register action creates DeploymentSet via SAM
    API
  status: pending
- id: SC-3
  description: Plugin README includes input schemas and configuration examples
  status: pending
files_modified: []
updated: '2026-03-03'
progress: 100
---

# backstage-integration-demo - Phase 2: Backstage Plugin

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python scripts/update-status.py -f .claude/progress/backstage-integration-demo/phase-2-progress.md -t TASK-X -s completed
```

---

## Objective

Author `@skillmeat/backstage-plugin-scaffolder-backend` — a Node.js package containing two Backstage custom scaffolder actions that call the SAM IDP API endpoints from Phase 1. This is an external package, separate from the SAM Python codebase.

---

## Implementation Notes

### Architectural Decisions

- Plugin is a standalone Node.js package using Backstage plugin conventions.
- Actions use `@backstage/plugin-scaffolder-node` for workspace access.
- Bearer token for SAM API is read from Backstage backend config, never from frontend.

### Known Gotchas

- Backstage workspace file API may differ between RHDH versions — pin to tested version.
- Base64 decoding of scaffold response must preserve binary-safe content (use Buffer, not atob).
- Register action must wait for `publish:github` to complete to have the `repoUrl` output.

---

## Completion Notes

_Fill in when phase is complete._
