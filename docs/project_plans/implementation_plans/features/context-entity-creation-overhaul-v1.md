---
title: 'Implementation Plan: Context Entity Creation Overhaul'
schema_version: 2
doc_type: implementation_plan
status: in-progress
created: 2026-02-28
updated: '2026-02-28'
feature_slug: context-entity-creation-overhaul
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md
plan_ref: null
scope: Migrate entity type definitions from hardcoded Python to DB config, build Settings
  UI for type management, overhaul the creation form with platform awareness and content
  templates, add multi-select categories, and enable user-defined custom entity types.
effort_estimate: 58 pts
architecture_summary: DB-backed EntityTypeConfig + ContextEntityCategory tables feed
  a refactored backend validator and new Settings API endpoints; the creation form
  is rebuilt to consume entity type configs for template injection, inline hints,
  and platform-driven path derivation; content assembly at deploy time keeps stored
  content platform-agnostic.
related_documents:
- docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md
- docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md
- docs/project_plans/PRDs/features/agent-context-entities-v1.md
owner: null
contributors: []
priority: high
risk_level: medium-high
category: product-planning
tags:
- implementation
- planning
- context-entities
- platform-aware
- settings
- creation-flow
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- skillmeat/cache/models.py
- skillmeat/cache/migrations/versions/
- skillmeat/core/validators/context_entity.py
- skillmeat/core/platform_defaults.py
- skillmeat/api/routers/context_entities.py
- skillmeat/api/routers/settings.py
- skillmeat/api/schemas/context_entity.py
- skillmeat/api/schemas/platform_defaults.py
- skillmeat/web/app/settings/page.tsx
- skillmeat/web/app/settings/components/
- skillmeat/web/components/context/context-entity-editor.tsx
- skillmeat/web/types/context-entity.ts
- skillmeat/web/lib/api/context-entities.ts
- skillmeat/web/components/settings/platform-defaults-settings.tsx
phases:
- 'Phase 1: Entity Type Configuration Backend'
- 'Phase 2: Entity Type Settings UI'
- 'Phase 3: Enhanced Creation Form'
- 'Phase 4: Modular Content Architecture'
- 'Phase 5: Custom Entity Types'
- 'Phase 6: Integration and Polish'
test_strategy: Unit tests for DB seeding idempotency, validator cache TTL, and fallback
  paths; integration tests for all new settings API endpoints (CRUD round-trips);
  E2E tests for spec_file first-attempt success, custom type lifecycle, and multi-platform
  deploy flow.
---

# Implementation Plan: Context Entity Creation Overhaul

**Plan ID**: `IMPL-2026-02-28-CONTEXT-ENTITY-CREATION-OVERHAUL`
**Date**: 2026-02-28
**Author**: Claude (implementation-planner / Sonnet 4.6)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/context-entity-creation-overhaul-v1.md`
- **Enhanced Platform Profiles**: `docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md`
- **Agent Context Entities**: `docs/project_plans/PRDs/features/agent-context-entities-v1.md`

**Complexity**: XL
**Total Estimated Effort**: 58 pts
**Target Timeline**: 5–6 sprints (~25–31 dev days)

---

## Executive Summary

This plan migrates the 5 hardcoded context entity type definitions from Python source into a DB-backed `EntityTypeConfig` table, builds a new Settings tab for managing entity type configurations and custom types, and redesigns the creation form to surface platform selection, path pattern derivation, content template injection, and a multi-select category system. A content assembly engine is introduced in Phase 4 to keep stored content platform-agnostic. All work is gated behind feature flags for safe incremental delivery. Each phase is independently releasable.

---

## Implementation Strategy

### Architecture Sequence

Following SkillMeat's layered architecture:

1. **Database Layer** — `EntityTypeConfig` model, `ContextEntityCategory` model, `entity_category_associations` join table, Alembic migrations
2. **Service/Validator Layer** — DB-backed `validate_context_entity()`, in-memory cache with TTL, hardcoded fallback
3. **API Layer** — New settings sub-routes under `/api/v1/settings/entity-type-configs` and `/api/v1/settings/entity-categories`
4. **Frontend Hooks Layer** — `useEntityTypeConfigs()`, `useEntityCategories()` TanStack Query hooks
5. **UI Layer** — Entity Types settings tab, redesigned creation form with platform multi-select, path derivation, template injection, category combobox
6. **Content Assembly Layer** — `skillmeat/core/content_assembly.py`, `core_content` column, deploy-time assembly
7. **Testing Layer** — Unit, integration, and E2E coverage per phase
8. **Integration/Polish Layer** — Feature flag cleanup, accessibility audit, docs, performance validation

### Parallel Work Opportunities

| Batch | Parallel Tasks | Phase |
|-------|----------------|-------|
| P1-A | CECO-1.1 (DB model + migration) | Phase 1 |
| P1-B | CECO-1.2 (validator refactor) + CECO-1.4 (error hints) — after P1-A | Phase 1 |
| P1-C | CECO-1.3 (list endpoint) — alongside P1-B | Phase 1 |
| P2-A | CECO-2.1 (CRUD endpoints) + CECO-2.2 (content_template field) | Phase 2 |
| P2-B | CECO-2.3 (Settings tab UI) — after P2-A | Phase 2 |
| P3-A | CECO-3.1 (category DB + migration) + CECO-3.2 (category API) | Phase 3 |
| P3-B | CECO-3.3 (creation form v2) + CECO-3.4 (multi-select categories) — after P3-A | Phase 3 |
| P4-A | CECO-4.1 (content assembly engine) — standalone | Phase 4 |
| P5-A | CECO-5.1 (custom type CRUD) + CECO-5.2 (custom type in form) | Phase 5 |
| P6-A | CECO-6.1 (flag cleanup + docs) + CECO-6.2 (E2E tests) | Phase 6 |

### Critical Path

```
CECO-1.1 → CECO-1.2 → CECO-2.1 → CECO-2.2 → CECO-2.3
                   ↘ CECO-1.3 ↗
CECO-1.1 → CECO-3.1 → CECO-3.2 → CECO-3.3 → CECO-3.4
CECO-2.2 → CECO-3.3 (template injection)
CECO-3.3 → CECO-5.1 → CECO-5.2
CECO-5.2 → CECO-4.1 → CECO-6.1 → CECO-6.2
```

The critical path runs through the DB model → validator refactor → creation form → custom types → content assembly → polish. Settings tab UI and category system can proceed in parallel once their respective API tasks complete.

---

## Phase Breakdown

### Phase 1: Entity Type Configuration Backend

**Duration**: 5–7 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert (DB), python-backend-engineer (validator + API)
**Feature Flag**: `entity_type_config_enabled` (default `false`; gates DB validator switch)

Goal: All 5 built-in entity type definitions live in a DB table. The validator reads from DB with in-memory cache. A hardcoded fallback preserves existing behavior when the flag is off. One read-only API endpoint exposes configs to the frontend.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CECO-1.1 | EntityTypeConfig DB model + migration | Add `EntityTypeConfig` SQLAlchemy model to `skillmeat/cache/models.py`; write Alembic migration creating `entity_type_configs` table; write idempotent seeding logic populating 5 built-in rows from `platform_defaults.py` and `context_entity.py` validator rules | Table created; 5 rows seeded idempotently on repeated startup; existing `Artifact` rows unaffected; migration file follows naming convention `YYYYMMDD_HHMM_add_entity_type_configs.py` | 3 pts | data-layer-expert | None |
| CECO-1.2 | DB-backed validator | Refactor `validate_context_entity()` in `skillmeat/core/validators/context_entity.py` to load type config from DB with 60s in-memory TTL; preserve existing hardcoded dispatch map as fallback when `entity_type_config_enabled=false` or DB unavailable; update `POST /context-entities` and `PUT /context-entities/{id}` to use refactored validator | Validator uses DB config when flag enabled; falls back to hardcoded functions on DB error; cache invalidated within 1s of config write; unit tests pass for fallback path | 3 pts | python-backend-engineer | CECO-1.1 |
| CECO-1.3 | Config list endpoint | Add `GET /api/v1/settings/entity-type-configs` returning all `EntityTypeConfig` rows as DTOs; add `EntityTypeConfigResponse` Pydantic schema to `skillmeat/api/schemas/`; register sub-route in `skillmeat/api/routers/settings.py` | Endpoint returns 200 with list of all configs; response matches `EntityTypeConfigResponse` schema; built-in types always included; custom types included when present | 2 pts | python-backend-engineer | CECO-1.1 |
| CECO-1.4 | Enhanced error hints | Update `POST /context-entities` and `PUT /context-entities/{id}` validation error responses to include `field` and `hint` keys in the 400 detail payload (e.g., `{"field": "content", "hint": "Add frontmatter with 'title' key"}`) | 400 response body is a list of `{"field": str, "hint": str}` objects; `field` maps to `content`, `path_pattern`, or `frontmatter`; unit tests assert hint text for each built-in type | 2 pts | python-backend-engineer | CECO-1.2 |

**Phase 1 Quality Gates:**
- [ ] `entity_type_configs` table exists in DB after migration
- [ ] 5 built-in type rows seeded; seeding is idempotent (run twice → still 5 rows)
- [ ] Existing `Artifact` rows with context entity types survive migration unchanged
- [ ] `validate_context_entity()` uses DB config when flag enabled; hardcoded dispatch map when disabled
- [ ] `GET /settings/entity-type-configs` returns 200 with all 5 configs
- [ ] 400 errors from `POST /context-entities` include `field` + `hint` keys
- [ ] Unit tests: seeding idempotency, cache TTL, fallback path, error hint shapes

---

### Phase 2: Entity Type Settings UI

**Duration**: 4–5 days
**Dependencies**: Phase 1 complete (CECO-1.1, CECO-1.3)
**Assigned Subagent(s)**: python-backend-engineer (API), ui-engineer-enhanced (Settings UI)
**Feature Flag**: `entity_types_settings_tab`

Goal: Power users can view, create, edit, and delete entity type configurations in a new Settings tab. Built-in types are protected from deletion. Content templates are editable.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CECO-2.1 | Config CRUD endpoints | Add `POST /api/v1/settings/entity-type-configs`, `PUT /api/v1/settings/entity-type-configs/{slug}`, `DELETE /api/v1/settings/entity-type-configs/{slug}`; add `EntityTypeConfigCreateRequest` Pydantic schema with slug validation (`^[a-z][a-z0-9_]{0,63}$`); block deletion of 5 built-in type slugs; invalidate in-memory validator cache on write | Full CRUD round-trip for custom types; `DELETE` of built-in type returns 409; 201 on create; 200 on update; slug uniqueness enforced; cache invalidated on write | 4 pts | python-backend-engineer | CECO-1.1, CECO-1.3 |
| CECO-2.2 | Content template field | Add `content_template` text column to `EntityTypeConfig` model; write Alembic migration; update `EntityTypeConfigResponse` and `EntityTypeConfigCreateRequest` to include `content_template`; populate 5 built-in templates from existing validator logic comments | `content_template` returned in GET response; migration is additive; 5 built-in types have non-empty templates; template stored as raw Markdown string | 2 pts | data-layer-expert | CECO-1.1, CECO-2.1 |
| CECO-2.3 | Entity Types Settings tab | Add "Entity Types" tab to `skillmeat/web/app/settings/page.tsx` behind `entity_types_settings_tab` flag; build `EntityTypeConfigList` and `EntityTypeConfigForm` components in `skillmeat/web/app/settings/components/`; connect to `GET/POST/PUT/DELETE /settings/entity-type-configs` via new API client methods in `skillmeat/web/lib/api/context-entities.ts`; add `useEntityTypeConfigs()` TanStack Query hook with 5min stale time; show inline template editor; mark built-in types as read-only (template editable only) | Tab renders behind flag; list shows all types with type badges; create/edit modal with all fields; delete works for custom types; built-in types show edit-template-only UI; TypeScript types match API response schema | 5 pts | ui-engineer-enhanced | CECO-2.1, CECO-2.2 |

**Phase 2 Quality Gates:**
- [ ] `POST/PUT/DELETE /settings/entity-type-configs` return correct status codes
- [ ] Built-in type deletion returns 409; custom type deletion returns 204
- [ ] `content_template` present in all API responses; migration additive
- [ ] Settings tab renders; list, create, edit, delete flows operational
- [ ] Built-in type template is editable; built-in type non-template fields are read-only
- [ ] Integration tests: CRUD round-trip for custom type; built-in type protection
- [ ] TypeScript types for `EntityTypeConfigResponse` generated/aligned from API schema

---

### Phase 3: Enhanced Creation Form

**Duration**: 7–10 days
**Dependencies**: Phase 1 (CECO-1.1, CECO-1.3) and Phase 2 (CECO-2.2) complete
**Assigned Subagent(s)**: data-layer-expert (category DB), python-backend-engineer (category API), ui-engineer-enhanced (form redesign + category combobox)
**Feature Flag**: `creation_form_v2`

Goal: The creation form is rebuilt with platform multi-select, platform-driven path pattern derivation, content template injection, inline validation hints, and a multi-select category combobox with inline create.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CECO-3.1 | Category DB model + migration | Add `ContextEntityCategory` SQLAlchemy model and `entity_category_associations` join table to `skillmeat/cache/models.py`; write Alembic migration (additive — keep `Artifact.category` string column); add association between `Artifact` and `ContextEntityCategory` via join table | Tables created; migration additive; existing `Artifact.category` column unchanged; ORM relationships defined; unit test: create category, associate with artifact, verify join table row | 3 pts | data-layer-expert | CECO-1.1 |
| CECO-3.2 | Category API endpoints | Add `GET /api/v1/settings/entity-categories` (list with optional `entity_type_slug` + `platform` filters) and `POST /api/v1/settings/entity-categories` (create new category); block `DELETE` when associations exist; add `ContextEntityCategoryResponse` and `ContextEntityCategoryCreateRequest` Pydantic schemas; register sub-routes in `settings.py` | List endpoint returns 200 with all categories; POST creates and returns 201; DELETE of category with associations returns 409; p95 response time ≤200ms | 2 pts | python-backend-engineer | CECO-3.1 |
| CECO-3.3 | Creation form v2 | Redesign `skillmeat/web/components/context/context-entity-editor.tsx` behind `creation_form_v2` flag; add platform multi-select field populated from configured platforms via existing platforms API; add path pattern derivation: on type + platform change, compute suggested path using entity type's `path_prefix` + platform `root_dir`, resolving `{PLATFORM}` token; add template injection: on type select, insert `content_template` into editor (user can edit before save); add inline validation hints panel below type dropdown showing `required_frontmatter_keys` from entity type config; add `useEntityTypeConfigs()` hook call; ensure graceful fallback to 5 built-in types when config API unavailable | Platform multi-select renders with configured platforms; path pattern auto-populates on type+platform selection; template injects on type select; hint panel shows required fields; first-attempt `spec_file` creation succeeds without backend 422; fallback works when config API unavailable; `aria-describedby` on hint text; `creation_form_v2` flag toggles | 8 pts | ui-engineer-enhanced | CECO-2.2, CECO-3.2 |
| CECO-3.4 | Multi-select category combobox | Replace `category` string input in creation form with shadcn Combobox multi-select backed by `useEntityCategories()` hook (calls `GET /settings/entity-categories`); add inline create: typing a new value and pressing Enter creates the category via `POST /settings/entity-categories` and immediately selects it; update create/update API calls to send `category_ids: string[]`; update `ContextEntityCreateRequest` and `ContextEntityUpdateRequest` schemas to accept `category_ids`; update `POST/PUT /context-entities` to write `entity_category_associations` join table rows | Multi-select renders existing categories; new category creatable inline; multiple categories assignable; keyboard navigation works; `aria-combobox` ARIA pattern implemented; `category_ids` sent in API request; join table rows written on save | 4 pts | ui-engineer-enhanced | CECO-3.2, CECO-3.3 |

**Phase 3 Quality Gates:**
- [ ] `ContextEntityCategory` and `entity_category_associations` tables created; migration additive
- [ ] `GET/POST /settings/entity-categories` endpoints functional; DELETE blocked on associations
- [ ] Creation form: platform multi-select populates from configured platforms
- [ ] Creation form: path pattern auto-derives on type + platform selection
- [ ] Creation form: template injects on type select; user can edit
- [ ] Creation form: validation hints appear inline before submit
- [ ] E2E test: create `spec_file` succeeds on first attempt with template pre-populated
- [ ] Category combobox: multi-select, inline create, keyboard navigation, ARIA attributes
- [ ] `creation_form_v2` flag toggles cleanly; legacy form still works when disabled

---

### Phase 4: Modular Content Architecture

**Duration**: 5–7 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: data-layer-expert (column + migration), python-backend-engineer (assembly engine + deploy integration)
**Feature Flag**: `modular_content_architecture`

Goal: Introduce a `core_content` column on context entity `Artifact` rows. A new `content_assembly.py` module composes `core_content` + entity type config + platform at deploy time, keeping stored content platform-agnostic.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CECO-4.1 | Content assembly engine | Add `core_content` nullable Text column to `Artifact` via additive Alembic migration (existing `content` column kept as assembled/cached output); write `skillmeat/core/content_assembly.py` with `assemble_content(core_content, entity_type_config, platform)` function applying platform-specific frontmatter fields at assembly time; modify `POST /{entity_id}/deploy` in `context_entities.py` to call assembly engine when `core_content` is present (flag-gated); modify `POST /context-entities` and `PUT /context-entities/{id}` to store `core_content` separately when flag enabled | `core_content` column added; migration additive; `assemble_content()` returns different output per platform for same core content; `content` column retains assembled cache for deploy; unit tests: assembly for each of 5 built-in types × each platform; `modular_content_architecture` flag toggles | 5 pts | python-backend-engineer, data-layer-expert | CECO-3.3 |

**Phase 4 Quality Gates:**
- [ ] `core_content` column added; existing `Artifact` rows unaffected
- [ ] `assemble_content()` produces platform-correct output for all 5 built-in types
- [ ] Deploy endpoint uses assembled content when flag enabled; raw `content` when disabled
- [ ] Stored `core_content` is platform-agnostic (no platform-specific wrappers in DB)
- [ ] Unit tests: assembly for all built-in types × all 5 platforms

---

### Phase 5: Custom Entity Types

**Duration**: 6–8 days
**Dependencies**: Phase 2 (CECO-2.1, CECO-2.2) and Phase 3 (CECO-3.3) complete
**Assigned Subagent(s)**: python-backend-engineer (backend validation + schema), ui-engineer-enhanced (form integration)

Goal: Users can define new entity types in Settings with full field set. Custom types appear in the creation form and validate correctly.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CECO-5.1 | Custom type CRUD (full field set) | Extend `EntityTypeConfig` model with `applicable_platforms` (JSON list) and `frontmatter_schema` (JSON, storing JSON Schema subset) columns via additive Alembic migration; update `EntityTypeConfigCreateRequest` to validate custom type slugs (`^[a-z][a-z0-9_]{0,63}$`), reject reserved built-in slugs, and validate `frontmatter_schema` structure; extend `validate_context_entity()` DB path to use `jsonschema` library for custom type frontmatter validation; update Settings tab `EntityTypeConfigForm` to expose `applicable_platforms` multi-select and `frontmatter_schema` JSON editor | New columns added; migration additive; custom type with `frontmatter_schema` validates correctly on `POST /context-entities`; built-in slug reservation enforced; integration test: create custom type in Settings → create entity of custom type → backend validates correctly | 6 pts | python-backend-engineer | CECO-2.1, CECO-2.2 |
| CECO-5.2 | Custom types in creation form | Update `useEntityTypeConfigs()` hook to include custom types in the type dropdown; verify template injection and inline hints work for custom types using their `content_template` and `required_frontmatter_keys`; update path derivation to use custom type's `path_prefix` (supports `{PLATFORM}` token) | Custom types appear in creation form type dropdown; template injects; hints show required fields; path derives from custom `path_prefix`; E2E test: create custom type in Settings → use in creation form → save succeeds | 3 pts | ui-engineer-enhanced | CECO-5.1, CECO-3.3 |

**Phase 5 Quality Gates:**
- [ ] `applicable_platforms` and `frontmatter_schema` columns added; migration additive
- [ ] Custom type slug validation enforces regex and reserved slug protection
- [ ] `validate_context_entity()` uses `jsonschema` for custom type frontmatter validation
- [ ] Custom types appear in creation form alongside built-in types
- [ ] Template injection and inline hints work for custom types
- [ ] Integration test: full lifecycle — create type in Settings → create entity → deploy
- [ ] E2E test: Settings → create custom type → creation form → save succeeds

---

### Phase 6: Integration and Polish

**Duration**: 4–5 days
**Dependencies**: Phases 1–5 complete
**Assigned Subagent(s)**: python-backend-engineer (flag cleanup, performance), ui-engineer-enhanced (a11y), api-documenter (API docs), documentation-writer (user docs), task-completion-validator (validation)

Goal: Remove development feature flags, add deprecation notice for scalar `category` column, complete API docs, run accessibility audit, performance test, and add full E2E coverage.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| CECO-6.1 | Flag cleanup and docs | Remove `entity_type_config_enabled` feature flag (promote DB validator to default); add deprecation entry for `Artifact.category` scalar column to `.claude/context/key-context/deprecation-and-sunset-registry.md`; regenerate `skillmeat/api/openapi.json` for all new endpoints; update `skillmeat/api/CLAUDE.md` router table; update `skillmeat/web/CLAUDE.md` with new hook and component patterns; update module docstring in `skillmeat/core/validators/context_entity.py` to reflect DB-driven architecture | No `entity_type_config_enabled` flag remains in codebase; `Artifact.category` deprecation entry present; `openapi.json` includes all new `/settings/entity-type-configs` and `/settings/entity-categories` endpoints; CLAUDE.md files accurate | 3 pts | python-backend-engineer, documentation-writer | All prior phases |
| CECO-6.2 | E2E test suite and accessibility audit | Write Playwright/pytest E2E tests for: (1) create `spec_file` first attempt success with template pre-populated, (2) create custom entity type in Settings → use in creation form → save, (3) deploy multi-platform entity showing correct path derivation; run accessibility audit on creation form: keyboard navigation through platform multi-select, category combobox, and type dropdown; verify `aria-describedby` on hint text, `aria-combobox` pattern on category field, visible labels on platform checkboxes; performance test: compare `POST /context-entities` latency with DB-backed validator vs baseline (target: ≤20ms added latency at p95) | All 3 E2E test scenarios green in CI; no keyboard navigation regressions; `aria-describedby` associations verified; `POST /context-entities` p95 latency delta ≤20ms | 4 pts | ui-engineer-enhanced, python-backend-engineer | CECO-6.1 |

**Phase 6 Quality Gates:**
- [ ] `entity_type_config_enabled` flag removed; other flags documented for future cleanup
- [ ] Deprecation entry for `Artifact.category` in deprecation registry
- [ ] `openapi.json` regenerated; all new endpoints documented
- [ ] E2E tests for 3 critical paths pass in CI
- [ ] Accessibility: keyboard navigation, ARIA attributes, focus management verified
- [ ] Performance: DB-backed validator adds ≤20ms at p95 vs baseline

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| Alembic migration regresses existing `Artifact` rows with context entity `type` values | High | Medium | All migrations are additive (no column drops on `artifacts` table in Phases 1–5); pre-migration test asserts existing row count unchanged; `entity_type_config_enabled` flag defaults to `false` until Phase 1 fully validated |
| Frontend/backend type drift for custom entity type fields | Medium | Medium | `openapi.json` regenerated in Phase 6; TypeScript types for `EntityTypeConfigResponse` kept aligned via `fe-be-type-sync-playbook.md`; Phase 2 integration test validates response shape vs TypeScript interface |
| DB-backed validator adds perceptible latency to `POST /context-entities` | Low | Medium | Entity type configs cached in memory with 60s TTL at API startup; cache invalidated on config write; Phase 6 performance test gates promotion |
| `category` column data loss during multi-select migration | High | Low | `Artifact.category` column kept (not dropped) through all phases; join table backfill from existing string values at Phase 3 migration time; column drop deferred to post-Phase-6 cleanup migration |
| Custom entity type slugs collide with future built-in types | Low | Low | 5 built-in slugs reserved and enforced on `POST` in Phase 5; reserved list documented in `EntityTypeConfigCreateRequest` validator |
| Phase sequencing creates long tail of partially-delivered UX | Medium | Medium | Each phase independently releasable behind feature flags; user-facing improvement visible from Phase 3 (`creation_form_v2`) onward |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| Phase 3 creation form scope creep (8 pt task) | Medium | High | CECO-3.3 strictly scoped to: platform multi-select, path derivation, template injection, inline hints; per-platform template views deferred to Phase 4 per PRD Q3 resolution |
| Phase 5 `jsonschema` integration complexity | Medium | Medium | JSON Schema subset (required keys + type constraints only); full JSON Schema validation deferred if complex; unit tests define exact subset supported |
| Phase 4 content assembly touching deploy endpoint | Medium | Low | Flag-gated entirely; deploy endpoint behavior unchanged when `modular_content_architecture=false`; existing deploy E2E tests must still pass |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| 422 error rate on `POST /context-entities` | <5% of creation attempts | API error logs for 422s |
| Built-in type DB config coverage | 100% (5/5 types with DB rows, templates, required fields) | DB row count assertion in integration test |
| Custom entity type roundtrip | Functional (create in Settings → available in form) | E2E test passes |
| Multi-category assignment | Multiple categories assignable + new categories creatable inline | E2E test passes |
| `POST /context-entities` p95 latency delta with DB validator | ≤20ms added | Performance test in Phase 6 |
| Accessibility compliance | Keyboard navigation, ARIA combobox pattern, `aria-describedby` | Phase 6 audit |

---

**Progress Tracking:**

See `.claude/progress/context-entity-creation-overhaul/all-phases-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-28
