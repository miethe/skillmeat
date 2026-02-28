---
type: progress
schema_version: 2
doc_type: progress
prd: "context-entity-creation-overhaul"
feature_slug: "context-entity-creation-overhaul"
prd_ref: "docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md"
phase: 2
title: "Entity Type Settings UI"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 3
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 3
at_risk_tasks: 0

owners: ["python-backend-engineer", "ui-engineer-enhanced"]
contributors: []

tasks:
  - id: "CECO-2.1"
    description: "Add POST/PUT/DELETE /api/v1/settings/entity-type-configs CRUD endpoints; EntityTypeConfigCreateRequest schema with slug validation; block deletion of 5 built-in slugs; invalidate in-memory validator cache on write"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CECO-1.1", "CECO-1.3"]
    estimated_effort: "4 pts"
    priority: "critical"

  - id: "CECO-2.2"
    description: "Add content_template text column to EntityTypeConfig model via additive Alembic migration; update EntityTypeConfigResponse and EntityTypeConfigCreateRequest; populate 5 built-in templates from existing validator logic"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CECO-1.1", "CECO-2.1"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "CECO-2.3"
    description: "Add Entity Types tab to settings/page.tsx behind entity_types_settings_tab flag; build EntityTypeConfigList and EntityTypeConfigForm components; connect to CRUD API via new hooks; inline template editor; built-in types read-only (template editable only)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["CECO-2.1", "CECO-2.2"]
    estimated_effort: "5 pts"
    priority: "high"

parallelization:
  batch_1: ["CECO-2.1", "CECO-2.2"]
  batch_2: ["CECO-2.3"]
  critical_path: ["CECO-2.1", "CECO-2.2", "CECO-2.3"]
  estimated_total_time: "4-5 days"

blockers: []

success_criteria:
  - { id: "SC-2.1", description: "POST/PUT/DELETE /settings/entity-type-configs return correct status codes", status: "pending" }
  - { id: "SC-2.2", description: "Built-in type deletion returns 409; custom type deletion returns 204", status: "pending" }
  - { id: "SC-2.3", description: "content_template present in all API responses; migration additive", status: "pending" }
  - { id: "SC-2.4", description: "Settings tab renders; list, create, edit, delete flows operational", status: "pending" }
  - { id: "SC-2.5", description: "Built-in type template is editable; built-in type non-template fields are read-only", status: "pending" }
  - { id: "SC-2.6", description: "Integration tests: CRUD round-trip for custom type; built-in type protection", status: "pending" }
  - { id: "SC-2.7", description: "TypeScript types for EntityTypeConfigResponse generated/aligned from API schema", status: "pending" }

files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/migrations/versions/"
  - "skillmeat/api/routers/settings.py"
  - "skillmeat/api/schemas/context_entity.py"
  - "skillmeat/web/app/settings/page.tsx"
  - "skillmeat/web/app/settings/components/"
  - "skillmeat/web/lib/api/context-entities.ts"
  - "skillmeat/web/types/context-entity.ts"
---

# Context Entity Creation Overhaul - Phase 2: Entity Type Settings UI

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/context-entity-creation-overhaul/phase-2-progress.md \
  -t CECO-2.1 -s completed
```

---

## Objective

Power users can view, create, edit, and delete entity type configurations in a new Settings tab. Built-in types are protected from deletion. Content templates are editable. Gated behind `entity_types_settings_tab` feature flag.

---

## Orchestration Quick Reference

```python
# Batch 1 — after Phase 1 complete (CECO-1.1, CECO-1.3)
Task("python-backend-engineer",
     "Implement CECO-2.1: Config CRUD endpoints.\n"
     "File: skillmeat/api/routers/settings.py\n"
     "File: skillmeat/api/schemas/context_entity.py (add EntityTypeConfigCreateRequest)\n"
     "Add POST/PUT/DELETE /api/v1/settings/entity-type-configs.\n"
     "Slug validation regex: ^[a-z][a-z0-9_]{0,63}$.\n"
     "Block DELETE for 5 built-in slugs (return 409).\n"
     "Invalidate in-memory validator cache on write.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

Task("data-layer-expert",
     "Implement CECO-2.2: content_template field.\n"
     "File: skillmeat/cache/models.py (add content_template Text column)\n"
     "File: skillmeat/cache/migrations/versions/ (additive migration)\n"
     "File: skillmeat/api/schemas/context_entity.py (update request/response schemas)\n"
     "Populate 5 built-in templates from existing validator logic comments.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 2 — after CECO-2.1 and CECO-2.2 complete
Task("ui-engineer-enhanced",
     "Implement CECO-2.3: Entity Types Settings tab.\n"
     "File: skillmeat/web/app/settings/page.tsx\n"
     "File: skillmeat/web/app/settings/components/entity-type-config-list.tsx (new)\n"
     "File: skillmeat/web/app/settings/components/entity-type-config-form.tsx (new)\n"
     "File: skillmeat/web/lib/api/context-entities.ts (add CRUD methods)\n"
     "File: skillmeat/web/types/context-entity.ts (add EntityTypeConfigResponse type)\n"
     "Feature flag: entity_types_settings_tab.\n"
     "useEntityTypeConfigs() hook with 5min stale time.\n"
     "Built-in types: template editable, other fields read-only.\n"
     "Follow component-patterns: .claude/context/key-context/component-patterns.md\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")
```

---

## Implementation Notes

### Architectural Decisions

- `entity_types_settings_tab` feature flag gates the entire Settings tab UI.
- CECO-2.2 can run in parallel with CECO-2.1 since both touch different layers (DB vs API).
- TypeScript types must be kept in sync with `EntityTypeConfigResponse` schema — see `.claude/context/key-context/fe-be-type-sync-playbook.md`.

### Known Gotchas

- Built-in type slugs to reserve: confirm exact list from `platform_defaults.py` seeding logic in CECO-1.1.
- Cache invalidation from CECO-1.2 must fire on all CRUD writes (POST/PUT/DELETE) in CECO-2.1.
- `content_template` migration in CECO-2.2 must be additive — no nullability constraint that breaks existing rows.

---

## Completion Notes

*(Fill in when phase is complete)*
