---
type: progress
schema_version: 2
doc_type: progress
prd: "context-entity-creation-overhaul"
feature_slug: "context-entity-creation-overhaul"
prd_ref: "docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md"
phase: 5
title: "Custom Entity Types"
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
contributors: []

tasks:
  - id: "CECO-5.1"
    description: "Extend EntityTypeConfig with applicable_platforms (JSON list) and frontmatter_schema (JSON) columns via additive migration; update CreateRequest to validate custom slugs and reject reserved built-ins; extend validate_context_entity() DB path to use jsonschema for custom type frontmatter validation; update Settings tab EntityTypeConfigForm with applicable_platforms multi-select and frontmatter_schema JSON editor"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CECO-2.1", "CECO-2.2"]
    estimated_effort: "6 pts"
    priority: "critical"

  - id: "CECO-5.2"
    description: "Update useEntityTypeConfigs() hook to include custom types in type dropdown; verify template injection and inline hints work for custom types; update path derivation to use custom type's path_prefix with {PLATFORM} token support"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["CECO-5.1", "CECO-3.3"]
    estimated_effort: "3 pts"
    priority: "high"

parallelization:
  batch_1: ["CECO-5.1"]
  batch_2: ["CECO-5.2"]
  critical_path: ["CECO-5.1", "CECO-5.2"]
  estimated_total_time: "6-8 days"

blockers: []

success_criteria:
  - { id: "SC-5.1", description: "applicable_platforms and frontmatter_schema columns added; migration additive", status: "pending" }
  - { id: "SC-5.2", description: "Custom type slug validation enforces regex and reserved slug protection", status: "pending" }
  - { id: "SC-5.3", description: "validate_context_entity() uses jsonschema for custom type frontmatter validation", status: "pending" }
  - { id: "SC-5.4", description: "Custom types appear in creation form alongside built-in types", status: "pending" }
  - { id: "SC-5.5", description: "Template injection and inline hints work for custom types", status: "pending" }
  - { id: "SC-5.6", description: "Integration test: full lifecycle — create type in Settings → create entity → deploy", status: "pending" }
  - { id: "SC-5.7", description: "E2E test: Settings → create custom type → creation form → save succeeds", status: "pending" }

files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/migrations/versions/"
  - "skillmeat/core/validators/context_entity.py"
  - "skillmeat/api/routers/settings.py"
  - "skillmeat/api/schemas/context_entity.py"
  - "skillmeat/web/app/settings/components/"
  - "skillmeat/web/components/context/context-entity-editor.tsx"
  - "skillmeat/web/lib/api/context-entities.ts"
---

# Context Entity Creation Overhaul - Phase 5: Custom Entity Types

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/context-entity-creation-overhaul/phase-5-progress.md \
  -t CECO-5.1 -s completed
```

---

## Objective

Users can define new entity types in Settings with full field set. Custom types appear in the creation form and validate correctly using JSON Schema subset validation.

---

## Orchestration Quick Reference

```python
# Batch 1 — after CECO-2.1 and CECO-2.2 complete
Task("python-backend-engineer",
     "Implement CECO-5.1: Custom type CRUD (full field set).\n"
     "File: skillmeat/cache/models.py (add applicable_platforms JSON, frontmatter_schema JSON columns)\n"
     "File: skillmeat/cache/migrations/versions/ (additive migration)\n"
     "File: skillmeat/api/schemas/context_entity.py (update EntityTypeConfigCreateRequest)\n"
     "File: skillmeat/core/validators/context_entity.py (add jsonschema validation for custom types)\n"
     "File: skillmeat/web/app/settings/components/ (update EntityTypeConfigForm)\n"
     "Slug validation regex: ^[a-z][a-z0-9_]{0,63}$. Reject reserved built-in slugs.\n"
     "JSON Schema subset: required keys + type constraints only (not full JSON Schema).\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 2 — after CECO-5.1 and CECO-3.3 complete
Task("ui-engineer-enhanced",
     "Implement CECO-5.2: Custom types in creation form.\n"
     "File: skillmeat/web/components/context/context-entity-editor.tsx\n"
     "File: skillmeat/web/lib/api/context-entities.ts (update useEntityTypeConfigs hook)\n"
     "Custom types appear in type dropdown alongside built-ins.\n"
     "Template injection and inline hints work for custom types.\n"
     "Path derivation uses custom type's path_prefix with {PLATFORM} token.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")
```

---

## Implementation Notes

### Architectural Decisions

- JSON Schema subset for custom type validation: only `required` keys and basic `type` constraints — full JSON Schema validation deferred if complexity is high.
- 5 built-in slugs must be reserved and enforced on POST — document reserved list in `EntityTypeConfigCreateRequest` validator docstring.

### Known Gotchas

- `jsonschema` library may not be in current deps — add to `requirements.txt` / `pyproject.toml` if missing.
- Custom type `applicable_platforms` is a JSON list — must handle empty list (applies to all platforms) vs explicit list.
- CECO-5.2 dependency on CECO-3.3 means form hook changes from Phase 3 must be fully stable first.

---

## Completion Notes

*(Fill in when phase is complete)*
