---
type: progress
schema_version: 2
doc_type: progress
prd: "context-entity-creation-overhaul"
feature_slug: "context-entity-creation-overhaul"
prd_ref: "docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md"
phase: 3
title: "Enhanced Creation Form"
status: "planning"
started: null
completed: null
commit_refs: []
pr_refs: []

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 4
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 4
at_risk_tasks: 0

owners: ["data-layer-expert", "python-backend-engineer", "ui-engineer-enhanced"]
contributors: []

tasks:
  - id: "CECO-3.1"
    description: "Add ContextEntityCategory SQLAlchemy model and entity_category_associations join table; write additive Alembic migration (keep Artifact.category string column); define ORM relationships"
    status: "pending"
    assigned_to: ["data-layer-expert"]
    dependencies: ["CECO-1.1"]
    estimated_effort: "3 pts"
    priority: "critical"

  - id: "CECO-3.2"
    description: "Add GET /api/v1/settings/entity-categories (list with optional entity_type_slug + platform filters) and POST /api/v1/settings/entity-categories; block DELETE when associations exist; ContextEntityCategoryResponse and ContextEntityCategoryCreateRequest schemas"
    status: "pending"
    assigned_to: ["python-backend-engineer"]
    dependencies: ["CECO-3.1"]
    estimated_effort: "2 pts"
    priority: "high"

  - id: "CECO-3.3"
    description: "Redesign context-entity-editor.tsx behind creation_form_v2 flag: platform multi-select, path pattern derivation on type+platform change, template injection on type select, inline validation hints panel; useEntityTypeConfigs() hook; graceful fallback to 5 built-in types"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["CECO-2.2", "CECO-3.2"]
    estimated_effort: "8 pts"
    priority: "critical"

  - id: "CECO-3.4"
    description: "Replace category string input with shadcn Combobox multi-select backed by useEntityCategories() hook; inline create via Enter key; update create/update API calls to send category_ids; update ContextEntityCreateRequest/UpdateRequest schemas; write entity_category_associations join table rows"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["CECO-3.2", "CECO-3.3"]
    estimated_effort: "4 pts"
    priority: "high"

parallelization:
  batch_1: ["CECO-3.1"]
  batch_2: ["CECO-3.2"]
  batch_3: ["CECO-3.3"]
  batch_4: ["CECO-3.4"]
  critical_path: ["CECO-3.1", "CECO-3.2", "CECO-3.3", "CECO-3.4"]
  estimated_total_time: "7-10 days"

blockers: []

success_criteria:
  - { id: "SC-3.1", description: "ContextEntityCategory and entity_category_associations tables created; migration additive", status: "pending" }
  - { id: "SC-3.2", description: "GET/POST /settings/entity-categories functional; DELETE blocked on associations", status: "pending" }
  - { id: "SC-3.3", description: "Creation form: platform multi-select populates from configured platforms", status: "pending" }
  - { id: "SC-3.4", description: "Creation form: path pattern auto-derives on type + platform selection", status: "pending" }
  - { id: "SC-3.5", description: "Creation form: template injects on type select; user can edit", status: "pending" }
  - { id: "SC-3.6", description: "Creation form: validation hints appear inline before submit", status: "pending" }
  - { id: "SC-3.7", description: "E2E test: create spec_file succeeds on first attempt with template pre-populated", status: "pending" }
  - { id: "SC-3.8", description: "Category combobox: multi-select, inline create, keyboard navigation, ARIA attributes", status: "pending" }
  - { id: "SC-3.9", description: "creation_form_v2 flag toggles cleanly; legacy form still works when disabled", status: "pending" }

files_modified:
  - "skillmeat/cache/models.py"
  - "skillmeat/cache/migrations/versions/"
  - "skillmeat/api/routers/settings.py"
  - "skillmeat/api/routers/context_entities.py"
  - "skillmeat/api/schemas/context_entity.py"
  - "skillmeat/web/components/context/context-entity-editor.tsx"
  - "skillmeat/web/lib/api/context-entities.ts"
  - "skillmeat/web/types/context-entity.ts"
---

# Context Entity Creation Overhaul - Phase 3: Enhanced Creation Form

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/context-entity-creation-overhaul/phase-3-progress.md \
  -t CECO-3.1 -s completed
```

---

## Objective

Rebuild the creation form with platform multi-select, platform-driven path pattern derivation, content template injection, inline validation hints, and a multi-select category combobox with inline create. Gated behind `creation_form_v2` feature flag.

---

## Orchestration Quick Reference

```python
# Batch 1 — after Phase 1 complete (CECO-1.1)
Task("data-layer-expert",
     "Implement CECO-3.1: Category DB model + migration.\n"
     "File: skillmeat/cache/models.py\n"
     "File: skillmeat/cache/migrations/versions/ (additive migration)\n"
     "Add ContextEntityCategory model and entity_category_associations join table.\n"
     "Keep existing Artifact.category string column untouched.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 2 — after CECO-3.1
Task("python-backend-engineer",
     "Implement CECO-3.2: Category API endpoints.\n"
     "File: skillmeat/api/routers/settings.py\n"
     "File: skillmeat/api/schemas/context_entity.py (add category schemas)\n"
     "Add GET /api/v1/settings/entity-categories with optional entity_type_slug + platform filters.\n"
     "Add POST /api/v1/settings/entity-categories (inline create).\n"
     "Block DELETE when associations exist (return 409).\n"
     "p95 response time target: ≤200ms.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 3 — after CECO-2.2 and CECO-3.2 complete
Task("ui-engineer-enhanced",
     "Implement CECO-3.3: Creation form v2.\n"
     "File: skillmeat/web/components/context/context-entity-editor.tsx\n"
     "File: skillmeat/web/lib/api/context-entities.ts (add useEntityTypeConfigs hook)\n"
     "Feature flag: creation_form_v2.\n"
     "Add platform multi-select populated from existing platforms API.\n"
     "Path pattern derivation: type + platform → path_prefix + platform root_dir + {PLATFORM} token.\n"
     "Template injection: on type select, insert content_template into editor.\n"
     "Inline hints panel below type dropdown showing required_frontmatter_keys.\n"
     "Graceful fallback to 5 built-in types when config API unavailable.\n"
     "aria-describedby on hint text.\n"
     "Follow component-patterns: .claude/context/key-context/component-patterns.md\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")

# Batch 4 — after CECO-3.3 complete
Task("ui-engineer-enhanced",
     "Implement CECO-3.4: Multi-select category combobox.\n"
     "File: skillmeat/web/components/context/context-entity-editor.tsx\n"
     "File: skillmeat/web/lib/api/context-entities.ts (add useEntityCategories hook)\n"
     "File: skillmeat/api/schemas/context_entity.py (add category_ids to create/update request)\n"
     "Replace category string input with shadcn Combobox multi-select.\n"
     "Inline create: Enter on new value → POST /settings/entity-categories → select immediately.\n"
     "Update API calls to send category_ids: string[].\n"
     "aria-combobox ARIA pattern.\n"
     "See plan: docs/project_plans/implementation_plans/features/context-entity-creation-overhaul-v1.md")
```

---

## Implementation Notes

### Architectural Decisions

- CECO-3.3 is the largest task (8 pts) — strictly scoped to platform multi-select, path derivation, template injection, inline hints. Per-platform template views deferred to Phase 4.
- `creation_form_v2` flag must cleanly toggle — legacy form must remain functional when disabled.
- Path derivation uses `{PLATFORM}` token substitution from entity type's `path_prefix`.

### Known Gotchas

- `Artifact.category` string column must NOT be dropped in CECO-3.1 migration — join table backfill deferred, column drop deferred to post-Phase-6 cleanup.
- Category DELETE blocked when associations exist — important to check before allowing deletion via UI.
- CECO-3.3 depends on CECO-2.2 (content_template field) being complete before template injection can work.

---

## Completion Notes

*(Fill in when phase is complete)*
