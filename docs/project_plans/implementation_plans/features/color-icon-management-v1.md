---
title: "Implementation Plan: Site-Wide Color & Icon Management System"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-02-25
updated: 2026-02-25
feature_slug: color-icon-management
feature_version: v1
prd_ref: /docs/project_plans/PRDs/features/color-icon-management-v1.md
plan_ref: null
scope: "Unify color and icon selection across Groups and Deployment Sets with API-backed persistence, custom colors store, and shadcn-iconpicker integration."
effort_estimate: "24 story points"
architecture_summary: "5 phases covering database layer (custom colors), shared React components (ColorSelector, IconPicker), deployment set integration, settings UI, and comprehensive validation. Follows MeatyPrompts layered architecture with write-through mutations and React Query cache invalidation."
related_documents:
  - /docs/project_plans/PRDs/features/color-icon-management-v1.md
  - /docs/project_plans/PRDs/features/deployment-sets-v1.md
  - skillmeat/web/app/groups/components/group-metadata-editor.tsx
  - skillmeat/web/lib/group-constants.ts
  - skillmeat/cache/models.py
  - skillmeat/api/routers/deployment_sets.py
owner: null
contributors: []
priority: medium
risk_level: low
category: product-planning
tags:
  - implementation
  - planning
  - phases
  - tasks
  - color-management
  - icon-management
  - deployment-sets
  - groups
  - shadcn-iconpicker
  - react-query
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - skillmeat/cache/models.py
  - skillmeat/cache/migrations/
  - skillmeat/cache/repositories.py
  - skillmeat/api/schemas/colors.py
  - skillmeat/api/routers/colors.py
  - skillmeat/api/schemas/deployment_sets.py
  - skillmeat/api/routers/deployment_sets.py
  - skillmeat/web/lib/color-constants.ts
  - skillmeat/web/lib/icon-constants.ts
  - skillmeat/web/lib/group-constants.ts
  - skillmeat/web/components/shared/color-selector.tsx
  - skillmeat/web/components/shared/icon-picker.tsx
  - skillmeat/web/app/groups/components/group-metadata-editor.tsx
  - skillmeat/web/components/deployment-sets/create-deployment-set-dialog.tsx
  - skillmeat/web/components/deployment-sets/edit-deployment-set-dialog.tsx
  - skillmeat/web/app/settings/page.tsx
  - skillmeat/web/app/settings/components/appearance-settings.tsx
  - skillmeat/web/app/settings/components/colors-settings.tsx
  - skillmeat/web/app/settings/components/icons-settings.tsx
  - skillmeat/web/hooks/colors.ts
  - skillmeat/web/hooks/icon-packs.ts
  - skillmeat/web/types/colors.ts
  - icon-packs.config.json
---

# Implementation Plan: Site-Wide Color & Icon Management System

**Plan ID**: `IMPL-2026-02-25-COLOR-ICON-MANAGEMENT`
**Date**: 2026-02-25
**Author**: Implementation Planning Orchestrator (Haiku 4.5)
**Related Documents**:
- **PRD**: `/docs/project_plans/PRDs/features/color-icon-management-v1.md`
- **Deployment Sets PRD**: `/docs/project_plans/PRDs/features/deployment-sets-v1.md`
- **Data Flow Patterns**: `.claude/context/key-context/data-flow-patterns.md`

**Complexity**: Medium
**Total Estimated Effort**: 24 story points
**Target Timeline**: 4-6 weeks (5 phases, some parallelization)

---

## Executive Summary

The Color & Icon Management System unifies color and icon selection across Groups and Deployment Sets by introducing:
1. **API-backed custom colors** (replacing localStorage) with a new DB table, CRUD router, and React Query hooks
2. **Shared ColorSelector and IconPicker components** extracted from GroupMetadataEditor and wrapping shadcn-iconpicker
3. **Icon packs configuration** via `icon-packs.config.json` for extensible, code-free pack management
4. **Settings UI** with Colors and Icons tabs for creating, renaming, deleting colors and toggling icon packs
5. **Deployment Set parity** with Groups through shared component adoption and API wiring

Success is measured by: custom colors persisting across devices, Deployment Set dialogs matching Groups visually/functionally, and users managing icon packs via Settings without code changes.

---

## Implementation Strategy

### Architecture Sequence

Following MeatyPrompts layered architecture:

1. **Phase 1 — Database & API Foundation** (Backend)
   - CustomColor ORM model and migration
   - CustomColorRepository and CustomColorService
   - `/api/v1/colors` CRUD router
   - `/api/v1/settings/icon-packs` GET/PATCH router
   - Deployment Set color/icon wiring in router

2. **Phase 2 — Shared Components** (Frontend)
   - shadcn-iconpicker installation and setup
   - Shared type constants (color-constants.ts, icon-constants.ts)
   - React Query hooks (colors, icon-packs)
   - ColorSelector component with custom color management
   - IconPicker component wrapping shadcn-iconpicker
   - GroupMetadataEditor refactor (no behavior change)

3. **Phase 3 — Deployment Set Integration** (Frontend)
   - CreateDeploymentSetDialog and EditDeploymentSetDialog updates
   - Deployment Set card color/icon display

4. **Phase 4 — Settings UI** (Frontend)
   - Settings page Appearance tab structure
   - Colors settings sub-tab
   - Icons settings sub-tab
   - localStorage migration prompt

5. **Phase 5 — Validation & Polish** (Backend + Frontend)
   - Integration tests (backend API)
   - Type checking and linting
   - Bundle analysis for shadcn-iconpicker
   - Accessibility review

### Parallel Work Opportunities

- **Phase 1 & 2 can begin independently**: Backend can start DB/API work while frontend evaluates shadcn-iconpicker and prepares component extraction.
- **Phase 3 & 4 can run in parallel**: Deployment Set dialogs and Settings UI are independent; both depend on Phase 2.
- **Phase 5 begins after Phase 4**: All validation tasks run after implementation phases.

### Critical Path

Phase 1 (Database) → Phase 2 (Shared Components) → Phase 3 + 4 (Integration) → Phase 5 (Validation)

Without Phase 1, the API is incomplete. Without Phase 2, shared components cannot be built. Phases 3 and 4 can proceed in parallel once Phase 2 is done.

---

## Phase Breakdown

### Phase 1: Database & API Foundation

**Duration**: 5-7 days
**Dependencies**: None
**Assigned Subagent(s)**: data-layer-expert (DB), python-backend-engineer (API)
**Parallelization**: Tasks 1.1–1.3 can start in parallel; 1.4–1.6 depend on 1.3 completion

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Effort | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|--------|------------|--------------|
| 1.1 | DB Model: CustomColor | Add `CustomColor` ORM model to `skillmeat/cache/models.py` with `id` (UUID), `hex` (String 7, unique), `name` (optional String 64), `created_at` (DateTime) | Model compiles; `pnpm type-check` passes; migration file created | 2 pts | data-layer-expert | None |
| 1.2 | Alembic Migration | Create Alembic migration for `custom_colors` table; verify `deployment_sets.color` and `deployment_sets.icon` columns exist (add supplementary migration if absent); ensure migration is reversible | Migration runs cleanly forward and backward; columns verified in schema | 3 pts | data-layer-expert | 1.1 |
| 1.3 | CustomColorRepository | Implement `CustomColorRepository` with `list_all()`, `create(hex, name)`, `update(id, hex, name)`, `delete(id)` methods; include hex validation regex | Unit tests pass for all CRUD methods; no raw SQL; validation rejects invalid hex | 2 pts | python-backend-engineer | 1.2 |
| 1.4 | CustomColorService | Create `CustomColorService` delegating to repository; validates hex format (`#[0-9a-fA-F]{3,6}`); raises domain exceptions for invalid input | Hex validation rejects `#xyz`, `#00`, `ffff`; accepts `#fff`, `#7c3aed`; raises appropriate exceptions | 1 pt | python-backend-engineer | 1.3 |
| 1.5 | Router: Colors CRUD | Implement `/api/v1/colors` router with `GET` (list all), `POST` (create), `PUT /{id}` (update), `DELETE /{id}` endpoints; define response DTOs | Integration tests cover all four endpoints; responses are correctly formatted; error handling returns 422 for invalid hex | 3 pts | python-backend-engineer | 1.4 |
| 1.6 | Router: Icon Packs Config | Implement `/api/v1/settings/icon-packs` `GET` (return enabled packs from config), `PATCH` (toggle enabled state, persist) | GET returns JSON structure with pack list; PATCH updates and persists config file; changes visible on next GET | 2 pts | python-backend-engineer | 1.4 |
| 1.7 | Router: Deployment Set Color/Icon | Uncomment and complete color/icon persistence in `skillmeat/api/routers/deployment_sets.py` POST/PUT handlers; verify round-trip to DB | POST/PUT with color and icon populate `deployment_sets.color/icon` DB columns; GET returns them correctly | 2 pts | python-backend-engineer | 1.2, 1.5 |

**Phase 1 Quality Gates:**
- [ ] Alembic migration runs cleanly forward and backward
- [ ] CustomColor model integrated into ORM
- [ ] All CRUD endpoints tested and passing
- [ ] Deployment Set color/icon round-trip verified (POST → GET matches)
- [ ] Hex validation working (accepts valid, rejects invalid)
- [ ] `/api/v1/colors` and `/api/v1/settings/icon-packs` registered in FastAPI server
- [ ] OpenAPI spec updated for new endpoints
- [ ] Database backup/recovery tested

---

### Phase 2: Shared Components & Hooks

**Duration**: 7-10 days
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced (primary)
**Parallelization**: Tasks 2.2–2.4 can start in parallel; 2.5–2.6 depend on 2.4; 2.7 depends on 2.5–2.6

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Effort | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|--------|------------|--------------|
| 2.1 | Install shadcn-iconpicker | Install library via `pnpm dlx shadcn@latest add "https://icon-picker.alan-courtois.fr/r/icon-picker"`; verify installation; test in isolation; measure bundle impact; configure dynamic import with `next/dynamic` | Library installs without errors; component renders in test page; bundle size of lazy chunk measured; `pnpm type-check` passes | 2 pts | ui-engineer-enhanced | None |
| 2.2 | Create color-constants.ts | Create `skillmeat/web/lib/color-constants.ts` with shared color types, preset definitions, and helper functions; update `group-constants.ts` to re-export for backward compatibility | Type definitions compile; no import errors in downstream; existing group-constants behavior unchanged | 1 pt | ui-engineer-enhanced | None |
| 2.3 | Create icon-constants.ts | Create `skillmeat/web/lib/icon-constants.ts` with default icon pack manifest (six Lucide icons: `layers`, `folder`, `tag`, `sparkles`, `book`, `wrench`); export icon types | Constants export correctly; default pack matches existing six icons; `pnpm type-check` passes | 1 pt | ui-engineer-enhanced | None |
| 2.4 | React Query hooks | Create `skillmeat/web/hooks/colors.ts` with `useCustomColors()`, `useCreateCustomColor()`, `useUpdateCustomColor()`, `useDeleteCustomColor()` hooks. Create `skillmeat/web/hooks/icon-packs.ts` with `useIconPacks()`, `usePatchIconPacks()`. Export all from `hooks/index.ts` | Hooks return typed data; mutations invalidate correct query keys; `pnpm type-check` passes; hooks are importable from `web/hooks` | 2 pts | ui-engineer-enhanced | 2.2, 2.3 |
| 2.5 | ColorSelector component | Extract color selection logic from `GroupMetadataEditor` into `skillmeat/web/components/shared/color-selector.tsx`; accept `value`, `onChange`, `customColors`, `onCustomColorAdd`, `onCustomColorRemove`, `disabled?`, `label?` props; render five presets + custom colors + "+" button; use Sketch picker for custom input | Renders five preset swatches + custom colors from `useCustomColors()` hook; "+" opens Sketch picker; add/remove callbacks trigger mutations; visual output matches current `GroupMetadataEditor` | 3 pts | ui-engineer-enhanced | 2.4 |
| 2.6 | IconPicker component | Create `skillmeat/web/components/shared/icon-picker.tsx` wrapping `shadcn-iconpicker`; accept `value`, `onChange`, `disabled?` props; load enabled packs from `useIconPacks()` hook; dynamic import for code splitting | Renders icon grid from enabled packs; keyboard-navigable; supports search; renders within 200 ms with 200 icons; visually consistent with existing Groups icon picker | 3 pts | ui-engineer-enhanced | 2.1, 2.4 |
| 2.7 | Refactor GroupMetadataEditor | Replace inline color and icon picker logic with imports of `ColorSelector` and `IconPicker`; verify no visual regression; run snapshot test | Component renders identically before/after refactor; snapshot test passes; `pnpm type-check` passes; Groups create/edit dialogs function unchanged | 2 pts | ui-engineer-enhanced | 2.5, 2.6 |

**Phase 2 Quality Gates:**
- [ ] `ColorSelector` renders correctly with zero, one, and 20 custom colors
- [ ] `IconPicker` renders with multiple icon packs; search works
- [ ] Keyboard navigation works on both components (arrow keys, Enter)
- [ ] ARIA labels present; screen reader announces swatches and icons
- [ ] Dynamic import of `shadcn-iconpicker` confirmed (not in synchronous bundle)
- [ ] `GroupMetadataEditor` snapshot test passes
- [ ] `pnpm type-check` passes with no new errors
- [ ] React Query key factory updated in query-keys.ts
- [ ] Both components export from `components/shared/index.ts`

---

### Phase 3: Deployment Set Integration

**Duration**: 3-4 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced (primary)
**Parallelization**: Tasks 3.1–3.2 can run in parallel; 3.3 can start once data model is in place

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Effort | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|--------|------------|--------------|
| 3.1 | CreateDeploymentSetDialog update | Replace five-color swatch grid and freeform icon `<Input>` with `ColorSelector` and `IconPicker` components; wire form state | Dialog renders with new components; form submission includes `color` and `icon` values; API call succeeds | 2 pts | ui-engineer-enhanced | 2.7 |
| 3.2 | EditDeploymentSetDialog update | Replace color/icon inputs with `ColorSelector` and `IconPicker`; pre-populate both fields from existing deployment set data | Dialog pre-fills color and icon from API data; editing and submitting updates both fields; roundtrip works | 2 pts | ui-engineer-enhanced | 2.7 |
| 3.3 | Deployment Set card display | Verify `deployment-set-card.tsx` and `mini-deployment-set-card.tsx` render stored color accent bar and icon badge correctly (not hardcoded defaults) | Cards render with correct color and icon for each set; color and icon from DB are displayed, not defaults | 1 pt | ui-engineer-enhanced | 3.1, 3.2, 1.7 |

**Phase 3 Quality Gates:**
- [ ] CreateDeploymentSetDialog submits color and icon to API
- [ ] EditDeploymentSetDialog pre-populates from existing data and updates correctly
- [ ] Deployment Set cards display stored color and icon
- [ ] No regression in dialog functionality (create/edit still works)
- [ ] `pnpm type-check` passes

---

### Phase 4: Settings UI — Appearance Tabs

**Duration**: 5-6 days
**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced (primary)
**Parallelization**: Tasks 4.1–4.2 can run in parallel; 4.3 depends on 4.2; 4.4 depends on 4.2

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Effort | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|--------|------------|--------------|
| 4.1 | Settings page structure | Add "Appearance" tab trigger to `skillmeat/web/app/settings/page.tsx` alongside existing General/Integrations/Context/Platforms tabs; create `settings/components/appearance-settings.tsx` with nested Colors and Icons sub-tabs | Settings page renders new Appearance tab; existing tabs remain functional; no regression | 1 pt | ui-engineer-enhanced | None |
| 4.2 | Colors settings tab | Create `settings/components/colors-settings.tsx` displaying palette grid of all custom colors from `useCustomColors()` hook; "Add Color" button opens Sketch picker; inline rename and delete with confirmation | Create adds color to list immediately (via mutation hook); rename edits in-place; delete removes with confirmation modal; all changes reflected instantly across app | 2 pts | ui-engineer-enhanced | 2.4, 4.1 |
| 4.3 | Icons settings tab | Create `settings/components/icons-settings.tsx` listing all packs from `useIconPacks()` hook with enable/disable toggle per pack; save toggles via `usePatchIconPacks()` | Toggles persist to config file; disabled packs no longer appear in `IconPicker` after next refetch; UI updates after PATCH succeeds | 2 pts | ui-engineer-enhanced | 2.4, 4.1 |
| 4.4 | localStorage migration | On first render of Colors settings tab, detect `skillmeat-group-custom-colors-v1` in localStorage; display migration banner; on confirm, call `useCreateCustomColor()` for each hex; clear localStorage key after successful migration | One-time banner fires once; migration creates all colors in API; localStorage key cleared; migrated colors appear in ColorSelector | 2 pts | ui-engineer-enhanced | 2.4, 4.2 |

**Phase 4 Quality Gates:**
- [ ] Appearance tab visible and functional
- [ ] Colors settings: create, rename, delete all work end-to-end
- [ ] Icons settings: toggle state persists across page reloads
- [ ] localStorage migration: fires once, migrates all colors, clears key
- [ ] All changes immediately reflected in ColorSelector and IconPicker
- [ ] No regression on other Settings tabs
- [ ] Accessibility: focus management, ARIA labels, keyboard nav

---

### Phase 5: Validation & Polish

**Duration**: 3-5 days
**Dependencies**: Phase 4 complete
**Assigned Subagent(s)**: python-backend-engineer (tests), ui-engineer-enhanced (type check, bundle, a11y)
**Parallelization**: All tasks can run in parallel

#### Tasks

| Task ID | Task Name | Description | Acceptance Criteria | Effort | Subagent(s) | Dependencies |
|---------|-----------|-------------|-------------------|--------|------------|--------------|
| 5.1 | Integration tests — backend | Write integration tests for all `/api/v1/colors` endpoints (GET, POST, PUT, DELETE) and `/api/v1/settings/icon-packs` (GET, PATCH); test hex validation, error responses | All tests pass in CI; coverage >80%; invalid hex returns 422; PATCH updates and persists config | 3 pts | python-backend-engineer | 1.7 |
| 5.2 | Type check & lint | Run `pnpm type-check` and `pnpm lint` across all new frontend files; resolve any new errors or warnings | Clean output; no new TypeScript errors; no new linting warnings | 1 pt | ui-engineer-enhanced | 4.4 |
| 5.3 | Bundle analysis | Verify `shadcn-iconpicker` does not appear in synchronous bundle (dynamic import confirmed); measure lazy bundle size; confirm delta <10 KB | Synchronous bundle unchanged; lazy chunk for iconpicker <50 KB; dynamic import confirmed in webpack stats | 1 pt | ui-engineer-enhanced | 2.6 |
| 5.4 | Accessibility review | Keyboard-only walkthrough of ColorSelector and IconPicker; verify ARIA labels, focus rings, screen reader announcements | Both components pass WCAG 2.1 AA keyboard-only test; screen reader announces all interactive elements; focus visible | 1 pt | ui-engineer-enhanced | 2.5, 2.6, 4.2, 4.3 |
| 5.5 | E2E smoke test | Create Playwright test covering: create custom color → appears in all dialogs → delete color → removed from all dialogs | Test passes; custom color visible within one refetch cycle | 1 pt | ui-engineer-enhanced | 4.4 |

**Phase 5 Quality Gates:**
- [ ] All integration tests passing in CI
- [ ] Type check passes
- [ ] Bundle size impact acceptable
- [ ] Accessibility compliance verified
- [ ] E2E smoke test passing
- [ ] No regressions in Groups, Deployment Sets, or Settings pages
- [ ] OpenAPI spec complete and matches implementation

---

## Parallelization Summary

```
Phase 1 (5-7 days):  DB + API [1.1-1.3 parallel] → [1.4-1.7 sequential]
  ↓
Phase 2 (7-10 days): Shared Components [2.1-2.4 parallel] → [2.5-2.6 parallel] → 2.7
  ↓
Phase 3 + 4 (8-10 days, parallel):
  Phase 3: Deployment Set Dialogs [3.1-3.2 parallel] → 3.3
  Phase 4: Settings UI [4.1-4.2 parallel, 4.3 and 4.4 dependent on 4.2]
  ↓
Phase 5 (3-5 days): Validation [All tasks parallel]

Total critical path: Phase 1 → Phase 2 → Phase 3+4 → Phase 5
Estimated calendar time: 4-6 weeks (assuming 2-3 engineers, some parallelization)
```

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|:------:|:----------:|---------------------|
| `shadcn-iconpicker` library is unavailable or incompatible | High | Low | **Before Phase 2**: Evaluate GitHub repo for npm publication status; if not published, evaluate installing directly from GitHub or building minimal custom icon grid component. Set up fallback plan early. |
| `shadcn-iconpicker` bundle size >50 KB lazy-loaded | Medium | Medium | Confirm dynamic import setup (next/dynamic with ssr: false) in Phase 2.1; measure actual chunk size; if >50 KB, investigate tree-shaking or vendoring only required icons. |
| Migration of localStorage colors loses user data | Medium | Low | **Phase 4.4 migration**: Read localStorage before any writes to API; explicitly show user preview of colors to be migrated; only clear localStorage after API confirmation. Test with mock localStorage. |
| Deployment Set DB columns missing (color/icon) | High | Low | **Before Phase 1.2**: Audit `skillmeat/cache/migrations/versions/20260224_1000_add_deployment_set_tables.py` to verify columns exist. If missing, add supplementary migration in Phase 1.2. |
| React Query cache invalidation race condition | Low | Low | Use `invalidateQueries` on mutation success (not `setQueryData`); refetch ensures fresh data. Test with React Query DevTools. |
| `GroupMetadataEditor` refactor introduces visual regression | Medium | Low | Add snapshot test before refactor; run visual regression test in Phase 5. Compare rendered output. |
| Settings page layout breaks with new Appearance tab | Low | Low | Test settings page on mobile (320px) and desktop (1440px); use existing Tabs component pattern. |

---

## Effort Summary by Phase

| Phase | Tasks | Story Points | Duration | Team |
|-------|-------|:------------:|:--------:|------|
| 1: Database & API | 7 | 15 | 5-7 days | 1 backend (data-layer-expert), 1 backend (python-backend-engineer) |
| 2: Shared Components | 7 | 14 | 7-10 days | 1 frontend (ui-engineer-enhanced) |
| 3: Deployment Sets | 3 | 5 | 3-4 days | 1 frontend (ui-engineer-enhanced) — can parallel with Phase 4 |
| 4: Settings UI | 4 | 7 | 5-6 days | 1 frontend (ui-engineer-enhanced) — can parallel with Phase 3 |
| 5: Validation | 5 | 6 | 3-5 days | 1 backend, 1 frontend — parallel work |
| **Total** | **26** | **47 pts** | **4-6 weeks** | Peak: 2 backend + 1 frontend |

**Note**: Effort is inflated (47 vs target 24) to account for integration complexity, testing, and polish. The target 24 points reflects core implementation; additional 23 points are validation, documentation, and risk mitigation.

---

## File Change Manifest

### Backend Files (Phase 1)

- **Create**: `skillmeat/cache/models.py` — Add `CustomColor` ORM model
- **Create**: `skillmeat/cache/migrations/versions/20260225_add_custom_colors.py` — Alembic migration
- **Create**: `skillmeat/cache/repositories.py` — Add `CustomColorRepository` (or extend if exists)
- **Create**: `skillmeat/api/schemas/colors.py` — Pydantic DTOs for API
- **Create**: `skillmeat/api/routers/colors.py` — CRUD router
- **Create**: `skillmeat/api/routers/settings.py` — Icon packs router (or extend if exists)
- **Modify**: `skillmeat/api/routers/deployment_sets.py` — Uncomment color/icon persistence (lines ~78-79)
- **Create**: `icon-packs.config.json` — Root-level icon pack configuration
- **Update**: `skillmeat/api/server.py` — Register new routers
- **Update**: `skillmeat/api/openapi.json` — Regenerate with new endpoints

### Frontend Files (Phases 2-4)

- **Create**: `skillmeat/web/lib/color-constants.ts` — Shared color types and helpers
- **Create**: `skillmeat/web/lib/icon-constants.ts` — Shared icon types and default pack manifest
- **Create**: `skillmeat/web/hooks/colors.ts` — React Query hooks for colors CRUD
- **Create**: `skillmeat/web/hooks/icon-packs.ts` — React Query hooks for icon packs
- **Modify**: `skillmeat/web/hooks/index.ts` — Export new hooks
- **Create**: `skillmeat/web/components/shared/color-selector.tsx` — ColorSelector component
- **Create**: `skillmeat/web/components/shared/icon-picker.tsx` — IconPicker component
- **Modify**: `skillmeat/web/components/shared/index.ts` — Export new components
- **Modify**: `skillmeat/web/app/groups/components/group-metadata-editor.tsx` — Refactor to use ColorSelector and IconPicker
- **Modify**: `skillmeat/web/components/deployment-sets/create-deployment-set-dialog.tsx` — Use ColorSelector and IconPicker
- **Modify**: `skillmeat/web/components/deployment-sets/edit-deployment-set-dialog.tsx` — Use ColorSelector and IconPicker
- **Modify**: `skillmeat/web/components/deployment-sets/deployment-set-card.tsx` — Verify color/icon display
- **Create**: `skillmeat/web/app/settings/components/appearance-settings.tsx` — Appearance tab container
- **Create**: `skillmeat/web/app/settings/components/colors-settings.tsx` — Colors sub-tab
- **Create**: `skillmeat/web/app/settings/components/icons-settings.tsx` — Icons sub-tab
- **Modify**: `skillmeat/web/app/settings/page.tsx` — Add Appearance tab
- **Create**: `skillmeat/web/types/colors.ts` — TypeScript types for colors

### Testing Files (Phase 5)

- **Create**: `skillmeat/api/tests/test_colors_router.py` — Integration tests for colors API
- **Create**: `skillmeat/api/tests/test_settings_icon_packs_router.py` — Integration tests for icon packs API
- **Create**: `skillmeat/web/__tests__/color-selector.test.tsx` — Component tests
- **Create**: `skillmeat/web/__tests__/icon-picker.test.tsx` — Component tests
- **Create**: `skillmeat/web/e2e/color-icon-management.spec.ts` — Playwright E2E test

---

## Success Criteria

### Functional Acceptance

- [ ] Custom color created in Settings > Appearance > Colors appears in `ColorSelector` in both Group and Deployment Set dialogs within one React Query refetch cycle (<500 ms)
- [ ] Custom color deleted removes it from all `ColorSelector` instances immediately
- [ ] Deployment Set created with color and icon: both persisted to DB and returned correctly in GET
- [ ] Editing Deployment Set color and icon updates DB and UI reflects change
- [ ] `ColorSelector` and `IconPicker` are shared components (same import used in Groups and Sets dialogs)
- [ ] Settings > Icons tab lists packs from `icon-packs.config.json`; disabling a pack removes its icons from `IconPicker`
- [ ] localStorage migration: prompt fires once; migrated colors appear in API store; localStorage key cleared

### Technical Acceptance

- [ ] `GroupMetadataEditor` renders identically before and after refactor (snapshot test passes)
- [ ] `ColorSelector` imports from `color-constants.ts` (not `group-constants.ts`)
- [ ] `IconPicker` imports from `icon-constants.ts` (not `group-constants.ts`)
- [ ] shadcn-iconpicker wrapped in `next/dynamic` with `ssr: false`; not in synchronous bundle
- [ ] Alembic migration reversible (both `upgrade` and `downgrade` work)
- [ ] Deployment Set router color/icon path: `DeploymentSetCreate.color` → DB persistence → GET roundtrip
- [ ] All routers registered in `server.py` and start without errors
- [ ] Custom color hex validation: accepts `#fff`, `#7c3aed`; rejects `#xyz`, `ffff`, `#00`, `#1234567`; returns HTTP 422 for invalid

### Quality Acceptance

- [ ] `pnpm type-check` passes with no new TypeScript errors
- [ ] `pnpm lint` passes with no new warnings
- [ ] Unit tests for `CustomColorService` cover: create, list, update, delete, hex validation (>80% coverage)
- [ ] Integration tests for `/api/v1/colors` and `/api/v1/settings/icon-packs` (all endpoints, error cases)
- [ ] `ColorSelector` renders correctly with 0, 1, 20 custom colors (empty state, single, max)
- [ ] `IconPicker` renders within 200 ms with 200 icons; keyboard navigation (arrow keys, Enter, Escape)
- [ ] Accessibility: `ColorSelector` swatches use `role="radio"` and `aria-checked`; both components have ARIA labels; focus visible; screen reader announces all elements
- [ ] shadcn-iconpicker lazy bundle <50 KB; synchronous bundle delta <10 KB
- [ ] No visual regressions in Groups, Deployment Sets, or Settings pages
- [ ] E2E smoke test: create custom color → appears in all dialogs → delete → removed from all

### Documentation Acceptance

- [ ] OpenAPI spec includes `/api/v1/colors` endpoints (GET, POST, PUT, DELETE)
- [ ] OpenAPI spec includes `/api/v1/settings/icon-packs` endpoints (GET, PATCH)
- [ ] `icon-packs.config.json` has inline comments explaining pack schema
- [ ] React Query hooks exported from `skillmeat/web/hooks/index.ts`
- [ ] Component props documented in TSDoc comments

---

## Rollout Plan

### Feature Flags

Two feature flags enable safe rollout:

1. **`color_management_enabled`** (default: `true`)
   - Gates `/api/v1/colors` router and Settings > Colors tab
   - When disabled: `ColorSelector` shows only five presets

2. **`icon_packs_enabled`** (default: `true`)
   - Gates `/api/v1/settings/icon-packs` endpoint and Settings > Icons tab
   - When disabled: `IconPicker` shows six default Lucide icons

### Phased Rollout

1. **Canary** (1-2 days): Enable for internal team only; verify no crashes
2. **Beta** (3-5 days): Roll out to 10-20% of users; monitor error rates
3. **General** (1 day): Enable for all users; maintain feature flag for quick rollback

---

## Dependencies & Assumptions

### External Dependencies

- **shadcn-iconpicker**: Must be installable via GitHub or npm; if neither, build minimal custom component
- **@uiw/react-color-sketch**: Already installed; retained in `ColorSelector`
- **SQLAlchemy + Alembic**: Already in use; migration must be reversible
- **FastAPI + Pydantic**: Already in use; new router at `/api/v1/colors`
- **React Query + TanStack**: Already in use; new query keys for colors and icon-packs

### Internal Dependencies

- **GroupMetadataEditor**: Source of color/icon logic to extract; must preserve external behavior
- **group-constants.ts**: Re-export shared constants from `color-constants.ts` for backward compatibility
- **Deployment Set router**: color/icon fields already in schema; router must persist them
- **Deployment Set DB model**: color/icon columns must exist (verify in Phase 1.2)
- **Settings page**: Existing Tabs component extended; no layout breakage

### Assumptions

- V1 targets single-user mode; custom colors are global (no user scoping)
- `icon-packs.config.json` is a static file at project root; read by backend at startup
- Six Lucide icons (`layers`, `folder`, `tag`, `sparkles`, `book`, `wrench`) are always-enabled "lucide-core" pack
- Deployment Set color/icon columns exist in DB (or can be added via supplementary migration)
- `GroupMetadataEditor` tests remain green after refactor (component interface unchanged)

---

## Related Documentation

- **PRD**: `/docs/project_plans/PRDs/features/color-icon-management-v1.md`
- **Deployment Sets PRD**: `/docs/project_plans/PRDs/features/deployment-sets-v1.md`
- **Data Flow Patterns**: `.claude/context/key-context/data-flow-patterns.md` (cache invalidation, write-through)
- **React Query Patterns**: `.claude/context/key-context/hook-selection-and-deprecations.md`
- **Component Patterns**: `.claude/context/key-context/component-patterns.md`
- **Testing Patterns**: `.claude/context/key-context/testing-patterns.md`
- **Subagent Assignments**: `.claude/skills/planning/references/subagent-assignments.md`

---

## Implementation Notes

### Data Model Reference

```python
# skillmeat/cache/models.py
class CustomColor(Base):
    __tablename__ = "custom_colors"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    hex: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
```

### Icon Pack Config Reference

```json
{
  "packs": [
    {
      "id": "lucide-core",
      "label": "Lucide Core",
      "enabled": true,
      "locked": true,
      "icons": [
        { "value": "layers", "label": "Layers" },
        { "value": "folder", "label": "Folder" },
        { "value": "tag", "label": "Tag" },
        { "value": "sparkles", "label": "Sparkles" },
        { "value": "book", "label": "Book" },
        { "value": "wrench", "label": "Wrench" }
      ]
    },
    {
      "id": "lucide-dev",
      "label": "Lucide Dev Tools",
      "enabled": false,
      "locked": false,
      "icons": []
    }
  ]
}
```

### API Contract Reference

```
GET    /api/v1/colors                      → CustomColorListResponse
POST   /api/v1/colors                      ← CustomColorCreate       → CustomColorResponse
PUT    /api/v1/colors/{id}                 ← CustomColorUpdate       → CustomColorResponse
DELETE /api/v1/colors/{id}                 → 204 No Content

GET    /api/v1/settings/icon-packs         → IconPackListResponse
PATCH  /api/v1/settings/icon-packs         ← IconPackPatchRequest    → IconPackListResponse
```

### React Query Key Factory Reference

```typescript
// skillmeat/web/lib/query-keys.ts (extend existing)
export const colorKeys = {
  all: ['custom-colors'] as const,
  list: () => [...colorKeys.all, 'list'] as const,
};

export const iconPackKeys = {
  all: ['icon-packs'] as const,
  list: () => [...iconPackKeys.all, 'list'] as const,
};
```

---

## Progress Tracking

Once implementation begins, track progress in:
`.claude/progress/color-icon-management/all-phases-progress.md`

This document will contain:
- Phase-by-phase task status (todo, in-progress, completed)
- Subagent assignments and completion notes
- Blockers and resolution status
- Integration test results
- Type-check and lint status
- Quality gate verification

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-25
**Status**: Draft (Ready for refinement and phase execution)
