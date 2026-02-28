---
type: progress
schema_version: 2
doc_type: progress
prd: "context-entity-creation-overhaul"
feature_slug: "context-entity-creation-overhaul"
prd_ref: "docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md"
phase: 4
title: "Modular Content Architecture"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 1
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 1
at_risk_tasks: 0

owners: ["python-backend-engineer", "data-layer-expert"]
contributors: []

tasks:
  - id: "CECO-4.1"
    description: "Add core_content nullable Text column to Artifact via additive Alembic migration; write skillmeat/core/content_assembly.py with assemble_content(core_content, entity_type_config, platform); modify deploy endpoint to call assembly engine when core_content present (flag-gated); modify POST/PUT /context-entities to store core_content separately when flag enabled"
    status: "pending"
    assigned_to: ["python-backend-engineer", "data-layer-expert"]
    dependencies: ["CECO-3.3"]
    estimated_effort: "5 pts"
    priority: "high"

parallelization:
  batch_1: ["CECO-4.1"]
  critical_path: ["CECO-4.1"]
  estimated_total_time: "5-7 days"

blockers: []

success_criteria:
  - { id: "SC-4.1", description: "core_content column added; existing Artifact rows unaffected", status: "pending" }
  - { id: "SC-4.2", description: "assemble_content() produces platform-correct output for all 5 built-in types", status: "pending" }
  - { id: "SC-4.3", description: "Deploy endpoint uses assembled content when flag enabled; raw content when disabled", status: "pending" }
  - { id: "SC-4.4", description: "Stored core_content is platform-agnostic (no platform-specific wrappers in DB)", status: "pending" }
  - { id: "SC-4.5", description: "Unit tests: assembly for all built-in types × all 5 platforms", status: "pending" }

files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/migrations/versions/"
  - "skillmeat/core/content_assembly.py"
  - "skillmeat/api/routers/context_entities.py"
---

# Context Entity Creation Overhaul - Phase 4: Modular Content Architecture

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/context-entity-creation-overhaul/phase-4-progress.md \
  -t CECO-4.1 -s completed
```

---

## Objective

Introduce a `core_content` column on context entity `Artifact` rows. A new `content_assembly.py` module composes `core_content` + entity type config + platform at deploy time, keeping stored content platform-agnostic. Gated behind `modular_content_architecture` feature flag.

---

## Orchestration Quick Reference

```python
# Batch 1 — after Phase 3 complete (CECO-3.3)
Task("python-backend-engineer",
     "Implement CECO-4.1: Content assembly engine.\n"
     "File: skillmeat/core/content_assembly.py (new module)\n"
     "File: skillmeat/cache/models.py (add core_content nullable Text column to Artifact)\n"
     "File: skillmeat/cache/migrations/versions/ (additive Alembic migration)\n"
     "File: skillmeat/api/routers/context_entities.py (update deploy + create/update endpoints)\n"
     "Write assemble_content(core_content, entity_type_config, platform) applying platform-specific\n"
     "frontmatter fields at assembly time. Keep existing content column as assembled/cached output.\n"
     "Feature flag: modular_content_architecture. Existing deploy behavior unchanged when flag off.\n"
     "data-layer-expert handles DB column + migration; python-backend-engineer handles assembly logic.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")
```

---

## Implementation Notes

### Architectural Decisions

- `core_content` is nullable — existing rows have NULL, meaning deploy falls back to `content` column.
- `content` column is retained as assembled/cached output for backward compatibility.
- `modular_content_architecture` flag gates the entire new code path — existing deploy tests must still pass when flag is off.

### Known Gotchas

- CECO-4.1 is jointly owned by `python-backend-engineer` (assembly logic + endpoint changes) and `data-layer-expert` (DB column + migration). Coordinate file-level boundaries to avoid merge conflicts.
- Assembly must not mutate stored `core_content` — it produces a derived `content` value at deploy time.

---

## Completion Notes

*(Fill in when phase is complete)*
