---
type: progress
schema_version: 2
doc_type: progress
prd: "context-entity-creation-overhaul"
feature_slug: "context-entity-creation-overhaul"
prd_ref: "docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md"
phase: 6
title: "Integration and Polish"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 2
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 2
at_risk_tasks: 0

owners: ["python-backend-engineer", "ui-engineer-enhanced"]
contributors: ["api-documenter", "documentation-writer", "task-completion-validator"]

tasks:
  - id: "CECO-6.1"
    description: "Remove entity_type_config_enabled feature flag (promote DB validator to default); add deprecation entry for Artifact.category scalar column to deprecation registry; regenerate openapi.json for all new endpoints; update skillmeat/api/CLAUDE.md router table; update skillmeat/web/CLAUDE.md with new hook and component patterns; update validator module docstring"
    status: "pending"
    assigned_to: ["python-backend-engineer", "documentation-writer"]
    dependencies: ["CECO-1.1", "CECO-1.2", "CECO-1.3", "CECO-1.4", "CECO-2.1", "CECO-2.2", "CECO-2.3", "CECO-3.1", "CECO-3.2", "CECO-3.3", "CECO-3.4", "CECO-4.1", "CECO-5.1", "CECO-5.2"]
    estimated_effort: "3 pts"
    priority: "high"

  - id: "CECO-6.2"
    description: "Write Playwright/pytest E2E tests for 3 critical paths: (1) spec_file first-attempt success with template pre-populated, (2) custom type lifecycle (Settings → creation form → save), (3) multi-platform deploy with correct path derivation; accessibility audit on creation form; performance test POST /context-entities latency with DB validator (target ≤20ms added at p95)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced", "python-backend-engineer"]
    dependencies: ["CECO-6.1"]
    estimated_effort: "4 pts"
    priority: "high"

parallelization:
  batch_1: ["CECO-6.1"]
  batch_2: ["CECO-6.2"]
  critical_path: ["CECO-6.1", "CECO-6.2"]
  estimated_total_time: "4-5 days"

blockers: []

success_criteria:
  - { id: "SC-6.1", description: "entity_type_config_enabled flag removed; other flags documented for future cleanup", status: "pending" }
  - { id: "SC-6.2", description: "Deprecation entry for Artifact.category in deprecation registry", status: "pending" }
  - { id: "SC-6.3", description: "openapi.json regenerated; all new endpoints documented", status: "pending" }
  - { id: "SC-6.4", description: "E2E tests for 3 critical paths pass in CI", status: "pending" }
  - { id: "SC-6.5", description: "Accessibility: keyboard navigation, ARIA attributes, focus management verified", status: "pending" }
  - { id: "SC-6.6", description: "Performance: DB-backed validator adds ≤20ms at p95 vs baseline", status: "pending" }

files_modified:
  - "skillmeat/core/validators/context_entity.py"
  - "skillmeat/api/openapi.json"
  - "skillmeat/api/CLAUDE.md"
  - "skillmeat/web/CLAUDE.md"
  - ".claude/context/key-context/deprecation-and-sunset-registry.md"
  - "tests/e2e/"
---

# Context Entity Creation Overhaul - Phase 6: Integration and Polish

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/context-entity-creation-overhaul/phase-6-progress.md \
  -t CECO-6.1 -s completed
```

---

## Objective

Remove development feature flags, add deprecation notice for scalar `category` column, complete API docs, run accessibility audit, performance test, and add full E2E coverage. This phase closes the feature.

---

## Orchestration Quick Reference

```python
# Batch 1 — after all prior phases complete
Task("python-backend-engineer",
     "Implement CECO-6.1: Flag cleanup and docs.\n"
     "File: skillmeat/core/validators/context_entity.py (remove entity_type_config_enabled flag)\n"
     "File: skillmeat/api/openapi.json (regenerate for all new endpoints)\n"
     "File: skillmeat/api/CLAUDE.md (update router table)\n"
     "File: skillmeat/web/CLAUDE.md (update hook and component patterns)\n"
     "File: .claude/context/key-context/deprecation-and-sunset-registry.md (add Artifact.category entry)\n"
     "documentation-writer handles CLAUDE.md updates and deprecation registry entry.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 2 — after CECO-6.1
Task("ui-engineer-enhanced",
     "Implement CECO-6.2: E2E test suite and accessibility audit.\n"
     "File: tests/e2e/ (new E2E test files)\n"
     "3 E2E scenarios: spec_file first-attempt, custom type lifecycle, multi-platform deploy.\n"
     "Accessibility audit: keyboard navigation, aria-describedby, aria-combobox, platform checkbox labels.\n"
     "python-backend-engineer handles performance test (POST /context-entities p95 latency).\n"
     "Target: ≤20ms added latency vs baseline.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")
```

---

## Implementation Notes

### Architectural Decisions

- `entity_type_config_enabled` is the only flag promoted to permanent (removed) — other flags (`entity_types_settings_tab`, `creation_form_v2`, `modular_content_architecture`) remain but are documented for future cleanup.
- `Artifact.category` column drop deferred to a post-Phase-6 cleanup migration (not in this phase).

### Known Gotchas

- `openapi.json` regeneration requires running the FastAPI server and exporting the schema — confirm the command in `skillmeat/api/CLAUDE.md`.
- Performance test baseline must be captured before enabling the DB validator to have a valid comparison point.

---

## Completion Notes

*(Fill in when phase is complete)*
