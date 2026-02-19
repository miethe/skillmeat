---
type: progress
schema_version: 2
doc_type: progress
prd: composite-artifact-ux-v2
feature_slug: composite-artifact-ux-v2
phase: 5
title: "CLI Integration + Polish"
status: pending
created: "2026-02-19"
updated: "2026-02-19"
prd_ref: "docs/project_plans/PRDs/features/composite-artifact-ux-v2.md"
plan_ref: "docs/project_plans/implementation_plans/features/composite-artifact-ux-v2.md"
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
  - python-backend-engineer
contributors: []
tasks:
  - id: CUX-P5-01
    description: "Update skillmeat list command to include composite artifacts; correctly labeled; filtering by type works"
    status: pending
    assigned_to:
      - python-backend-engineer
    dependencies:
      - CUX-P1-05
    estimated_effort: 1pt
    priority: high

  - id: CUX-P5-02
    description: "Implement skillmeat composite create Click command to create plugin from specified artifact sources"
    status: pending
    assigned_to:
      - python-backend-engineer
    dependencies:
      - CUX-P1-05
    estimated_effort: 1pt
    priority: high

  - id: CUX-P5-03
    description: "Write CLI integration tests for list and composite create commands (happy path + error cases)"
    status: pending
    assigned_to:
      - python-backend-engineer
    dependencies:
      - CUX-P5-02
    estimated_effort: 1pt
    priority: high

  - id: CUX-P5-04
    description: "Update skillmeat --help to document composite command group and create subcommand"
    status: pending
    assigned_to:
      - python-backend-engineer
    dependencies:
      - CUX-P5-02
    estimated_effort: 1pt
    priority: medium

  - id: CUX-P5-05
    description: "Update CHANGELOG.md with v2 feature additions across all 5 phases"
    status: pending
    assigned_to:
      - python-backend-engineer
    dependencies: []
    estimated_effort: 1pt
    priority: medium

parallelization:
  batch_1:
    - CUX-P5-01
    - CUX-P5-02
    - CUX-P5-05
  batch_2:
    - CUX-P5-03
    - CUX-P5-04
  critical_path:
    - CUX-P5-02
    - CUX-P5-03
  estimated_total_time: "1-2 days"

blockers: []

success_criteria:
  - id: SC-P5-1
    description: "skillmeat list output includes composite artifacts"
    status: pending
  - id: SC-P5-2
    description: "skillmeat list can filter by type (supports composite)"
    status: pending
  - id: SC-P5-3
    description: "skillmeat composite create my-plugin skill:a command:b creates composite"
    status: pending
  - id: SC-P5-4
    description: "Created composite appears in skillmeat list immediately"
    status: pending
  - id: SC-P5-5
    description: "CLI integration tests pass"
    status: pending
  - id: SC-P5-6
    description: "skillmeat --help shows new commands"
    status: pending
  - id: SC-P5-7
    description: "CHANGELOG updated and accurate"
    status: pending

files_modified: []
progress: 0
---

# Phase 5: CLI Integration + Polish

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-5-progress.md -t CUX-P5-01 -s completed

python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/composite-artifact-ux-v2/phase-5-progress.md \
  --updates "CUX-P5-01:completed,CUX-P5-02:completed,CUX-P5-05:completed"
```

---

## Objective

Complete the first-class artifact experience at the command line by extending existing commands and adding composite-specific operations. All work builds on the DB cache and existing CLI patterns.

---

## Orchestration Quick Reference

### Batch 1 (No internal dependencies — launch immediately)

```
Task("python-backend-engineer", "CUX-P5-01: Update skillmeat list to include composites.
  File: skillmeat/cli.py
  Composites labeled as 'plugin'. Filtering by type works (e.g., skillmeat list composite).")

Task("python-backend-engineer", "CUX-P5-02: Implement skillmeat composite create command.
  File: skillmeat/cli.py
  Click command: skillmeat composite create my-plugin skill:canvas command:git-commit
  Validate sources exist, call CompositeService.create_composite(), exit 0 on success.")

Task("python-backend-engineer", "CUX-P5-05: Update CHANGELOG.md with v2 feature additions.
  File: CHANGELOG.md
  Cover all 5 phases, new commands, breaking changes, migration notes.")
```

### Batch 2 (After Batch 1)

```
Task("python-backend-engineer", "CUX-P5-03: Write CLI integration tests for composite commands.
  File: tests/test_cli_composites.py
  Test: list includes composites, list filters, create valid, create invalid, create duplicate, create no members.")

Task("python-backend-engineer", "CUX-P5-04: Update skillmeat --help for composite commands.
  File: skillmeat/cli.py
  Document composite command group and create subcommand with usage examples.")
```

---

## Known Gotchas

- Phase 1 must be complete (CRUD API and CompositeService verified).
- Phase 4 can run in parallel with Phase 5 -- no dependency between them.
- Follow existing Click command patterns in `cli.py`.
- Use DB cache repositories (CompositeMembershipRepository) rather than filesystem reads.
- Validate artifact sources before calling service (check they exist in collection).
- Match existing list/show output formatting for consistency.
