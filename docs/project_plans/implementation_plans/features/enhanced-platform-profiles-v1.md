---
title: "Implementation Plan: Enhanced Platform Profiles"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-02-22
updated: 2026-02-22
feature_slug: "enhanced-platform-profiles"
feature_version: "v1"
prd_ref: docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md
plan_ref: null
scope: "Add description field to DeploymentProfile, extract reusable CreateProfileForm component with multi-select and tooltips, integrate platform profile selection into Create Project dialog, and add a Platforms tab to Settings."
effort_estimate: "29 pts"
architecture_summary: "Backend-first: Alembic migration + ORM update → schema/repo changes → OpenAPI refresh. Frontend: reusable CreateProfileForm component extraction → dialog integration → settings tab addition."
related_documents:
  - docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md
  - skillmeat/cache/models.py
  - skillmeat/cache/repositories.py
  - skillmeat/api/routers/deployment_profiles.py
  - skillmeat/api/schemas/deployment_profiles.py
  - skillmeat/web/app/projects/[id]/profiles/page.tsx
  - skillmeat/web/app/projects/components/create-project-dialog.tsx
  - skillmeat/web/app/settings/page.tsx
  - skillmeat/web/components/settings/platform-defaults-settings.tsx
  - skillmeat/web/lib/constants/platform-defaults.ts
  - skillmeat/web/types/deployments.ts
owner: null
contributors: []
priority: high
risk_level: medium
category: "product-planning"
tags: [implementation, planning, deployment-profiles, settings, create-project, forms]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - skillmeat/cache/models.py
  - skillmeat/cache/repositories.py
  - skillmeat/cache/migrations/
  - skillmeat/api/schemas/deployment_profiles.py
  - skillmeat/api/routers/deployment_profiles.py
  - skillmeat/api/openapi.json
  - skillmeat/web/components/profiles/create-profile-form.tsx
  - skillmeat/web/components/profiles/index.ts
  - skillmeat/web/app/projects/[id]/profiles/page.tsx
  - skillmeat/web/app/projects/components/create-project-dialog.tsx
  - skillmeat/web/app/settings/page.tsx
  - skillmeat/web/types/deployments.ts
  - skillmeat/web/hooks/use-deployment-profiles.ts
  - tests/api/test_deployment_profiles.py
phases:
  - "Phase 1: Backend — description field"
  - "Phase 2: Reusable CreateProfileForm component"
  - "Phase 3: Create Project dialog — platform profiles section"
  - "Phase 4: Settings Platforms tab"
test_strategy: "API integration test for description round-trip (Phase 1); Jest unit tests for form pre-population and multi-select behavior (Phase 2); component tests for dialog toggle flow (Phase 3); E2E navigation test for Platforms tab (Phase 4). pnpm type-check and pnpm lint must pass after each phase."
---

# Implementation Plan: Enhanced Platform Profiles

**Plan ID**: `IMPL-2026-02-22-ENHANCED-PLATFORM-PROFILES`
**Date**: 2026-02-22
**Author**: Implementation Planning Orchestrator (Sonnet 4.6)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md`
- **Existing router**: `skillmeat/api/routers/deployment_profiles.py`
- **Existing schemas**: `skillmeat/api/schemas/deployment_profiles.py`
- **Platform constants**: `skillmeat/web/lib/constants/platform-defaults.ts`

**Complexity**: Medium
**Total Estimated Effort**: 29 story points
**Target Timeline**: 6–9 days (4 sequential phases with limited parallelism)

---

## Executive Summary

This plan delivers four cohesive improvements to SkillMeat's deployment-profile system. Phase 1 adds an optional `description` TEXT column to the `deployment_profiles` table via Alembic migration and surfaces it through the Pydantic schemas and repository layer. Phase 2 extracts the inline Create Profile form from the project profiles page into a reusable `CreateProfileForm` component with multi-select artifact types, auto-population from `PLATFORM_DEFAULTS`, and informational tooltips on every field. Phase 3 integrates platform profile selection into the Create Project dialog using accordion UI, toggle cards, and a nested "Customize" dialog that embeds the reusable form. Phase 4 adds a new Platforms tab to Settings by moving `PlatformDefaultsSettings` and adding a custom profile creation entry point.

Success is defined by: `DeploymentProfileRead` responses include `description`; `CreateProfileForm` renders correctly in page, dialog, and settings contexts; projects created via the dialog can have deployment profiles attached at creation time; and the Settings Platforms tab is navigable and functional.

---

## Implementation Strategy

### Architecture Sequence

The implementation follows SkillMeat's standard layered order:

1. **Database** — Alembic migration adds `description` column (backward-compatible, nullable).
2. **ORM Model** — `DeploymentProfile` class gains `description: Mapped[Optional[str]]` and `to_dict()` update.
3. **API Schemas** — `DeploymentProfileCreate`, `DeploymentProfileUpdate`, `DeploymentProfileRead` gain `description: Optional[str] = Field(None, max_length=500)`.
4. **Repository** — `create_profile()` and `update_profile()` pass `description` through.
5. **OpenAPI spec** — Regenerate `skillmeat/api/openapi.json` after schema changes.
6. **Frontend types** — `types/deployments.ts` adds `description?: string` to profile interface.
7. **Reusable form component** — Extract and enhance `CreateProfileForm` with multi-select, tooltips, auto-population.
8. **Dialog integration** — Create Project dialog gains Platform Profiles accordion and customize flow.
9. **Settings tab** — Platforms tab added to Settings page.

### Parallel Work Opportunities

- **Phase 1 and Phase 2 pre-work**: The frontend `types/deployments.ts` update (EPP-P2-05) can be done in parallel with Phase 1 backend work since it is purely additive.
- **Phase 2 sub-tasks**: Component extraction (EPP-P2-01), multi-select implementation (EPP-P2-02), and tooltip markup (EPP-P2-03) can be parallelised by separate agents if needed, but the component file is shared so sequential batching within a single agent run is safer.
- **Phase 3 and Phase 4**: These phases touch distinct files (`create-project-dialog.tsx` vs `settings/page.tsx`) and can be executed in parallel once Phase 2 is complete and `CreateProfileForm` is published from its barrel export.

### Critical Path

```
Phase 1 (Backend) → Phase 2 (CreateProfileForm) → Phase 3 (Dialog) ─┐
                                                                      ├→ Phase validation
                                                  → Phase 4 (Settings)┘
```

Phase 1 must complete before Phase 2 (frontend type must match backend schema). Phase 2 must complete before Phase 3 and Phase 4 (both consume `CreateProfileForm`). Phases 3 and 4 can run in parallel.

---

## Phase Breakdown

### Phase 1: Backend — description field

**Duration**: 1–2 days
**Dependencies**: None
**Assigned Subagent(s)**: `data-layer-expert` (migration + ORM), `python-backend-engineer` (schemas + repository)
**Entry Criteria**: Alembic migration history clean; no other branches actively modifying `deployment_profiles` table.
**Exit Criteria**: Migration applies and reverts cleanly; `DeploymentProfileRead` response body includes `description`; integration test passes.

#### Key Files

| Layer | File | Change |
|-------|------|--------|
| Migration | `skillmeat/cache/migrations/versions/[new].py` | Add `description` TEXT nullable column; `downgrade` drops it |
| ORM Model | `skillmeat/cache/models.py` (~line 399) | Add `description: Mapped[Optional[str]]`; update `to_dict()` |
| Schemas | `skillmeat/api/schemas/deployment_profiles.py` | Add `description: Optional[str] = Field(None, max_length=500)` to Create/Update/Read |
| Repository | `skillmeat/cache/repositories.py` (~line 3062) | Pass `description` in `create_profile()` and `update_profile()` |
| OpenAPI | `skillmeat/api/openapi.json` | Regenerate after schema changes |
| Tests | `tests/api/test_deployment_profiles.py` | Integration test: create with description → GET → assert round-trip |

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------------|--------------|
| EPP-P1-01 | Alembic migration | Add nullable `description` TEXT column to `deployment_profiles`; implement reversible `downgrade()` | `alembic upgrade head` succeeds; `alembic downgrade -1` removes column without error | 2 pts | data-layer-expert | None |
| EPP-P1-02 | ORM model update | Add `description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)` to `DeploymentProfile`; update `to_dict()` to include `description` | `to_dict()` output contains `description` key; existing tests still pass | 1 pt | data-layer-expert | EPP-P1-01 |
| EPP-P1-03 | API schema update | Add `description: Optional[str] = Field(None, max_length=500, description="...")` to `DeploymentProfileCreate`, `DeploymentProfileUpdate`, `DeploymentProfileRead` | All three schema classes include `description`; FastAPI validation rejects values > 500 chars | 1 pt | python-backend-engineer | EPP-P1-02 |
| EPP-P1-04 | Repository update | Update `create_profile()` and `update_profile()` in `DeploymentProfileRepository` to accept and persist `description` | Repository methods pass `description` to ORM object; existing CRUD tests unaffected | 1 pt | python-backend-engineer | EPP-P1-03 |
| EPP-P1-05 | OpenAPI spec regeneration | Regenerate `skillmeat/api/openapi.json` after schema changes | `openapi.json` contains `description` in `DeploymentProfileCreate`, `DeploymentProfileUpdate`, `DeploymentProfileRead` component schemas | 0.5 pts | python-backend-engineer | EPP-P1-04 |
| EPP-P1-06 | Integration test | Write pytest integration test: POST profile with `description` → GET profile → assert `description` value matches | Test passes; `description` round-trips without data loss; `description=None` is also valid | 0.5 pts | python-backend-engineer | EPP-P1-05 |

**Phase Total**: 6 pts

#### Phase 1 Quality Gates

- [ ] `alembic upgrade head` and `alembic downgrade -1` both succeed on a clean DB
- [ ] `DeploymentProfileRead` response JSON includes `description` field (nullable)
- [ ] `DeploymentProfileCreate` with `description` longer than 500 chars returns HTTP 422
- [ ] `to_dict()` includes `description` key with correct value
- [ ] `openapi.json` updated and committed
- [ ] Integration test (`tests/api/test_deployment_profiles.py`) passes in CI

---

### Phase 2: Reusable CreateProfileForm Component

**Duration**: 2–3 days
**Dependencies**: Phase 1 complete (backend schema must be final before frontend type sync)
**Assigned Subagent(s)**: `ui-engineer-enhanced` (component implementation, multi-select, tooltips, auto-population), `frontend-developer` (page wiring, barrel export, unit tests)
**Entry Criteria**: Phase 1 exit criteria met; `openapi.json` updated with `description` field.
**Exit Criteria**: `CreateProfileForm` renders in page context on existing profiles page; exports from barrel; `pnpm type-check` passes; unit tests pass.

#### Key Files

| Surface | File | Change |
|---------|------|--------|
| New component | `skillmeat/web/components/profiles/create-profile-form.tsx` | New file — extracted and enhanced form |
| Barrel export | `skillmeat/web/components/profiles/index.ts` | New file — exports `CreateProfileForm` |
| Profiles page | `skillmeat/web/app/projects/[id]/profiles/page.tsx` | Replace inline form with `<CreateProfileForm contextMode="page" />` |
| Frontend types | `skillmeat/web/types/deployments.ts` | Add `description?: string` to profile interface |
| Platform constants | `skillmeat/web/lib/constants/platform-defaults.ts` | Verify `PLATFORM_DEFAULTS` keys match API values; update comment |
| Hooks | `skillmeat/web/hooks/use-deployment-profiles.ts` | Verify mutation accepts `description` in payload |

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------------|--------------|
| EPP-P2-01 | Frontend type update | Add `description?: string` to `DeploymentProfile` TypeScript interface in `types/deployments.ts` | `pnpm type-check` passes; hook mutations accept `description` in request payload | 0.5 pts | frontend-developer | Phase 1 complete |
| EPP-P2-02 | CreateProfileForm extraction | Create `components/profiles/create-profile-form.tsx` accepting props: `onSubmit`, `onCancel`, `defaultValues`, `contextMode: 'page' \| 'dialog'`, `platformLock?: Platform`; migrate all field logic from `profiles/page.tsx` inline form | Component renders in `contextMode="page"` matching current visual output; `profiles/page.tsx` inline form replaced with `<CreateProfileForm contextMode="page" />` | 3 pts | ui-engineer-enhanced | EPP-P2-01 |
| EPP-P2-03 | Multi-select for artifact types | Replace free-text `supported_artifact_types` input with a Radix Checkbox group or shadcn multi-select sourced from `ArtifactType` enum values (`skill, command, agent, mcp, hook, composite`); keyboard navigation (Space to toggle, Enter to confirm) | Selecting artifact types produces correct `string[]` value; keyboard-accessible; axe-core reports no critical violations on the field | 3 pts | ui-engineer-enhanced | EPP-P2-02 |
| EPP-P2-04 | Platform pre-population | When `platform` changes in the form, auto-populate `root_dir`, `artifact_path_map`, `config_filenames`, `context_prefixes`, and `supported_artifact_types` from `PLATFORM_DEFAULTS[platform]`; user may override without re-triggering population | Selecting "codex" fills `supported_artifact_types: ['skill','command','agent']` and `artifact_path_map: {"skill":"skills","command":"commands","agent":"agents"}`; subsequent manual edits are preserved | 2 pts | ui-engineer-enhanced | EPP-P2-02 |
| EPP-P2-05 | Artifact type → path map sync | When `supported_artifact_types` changes (and `artifact_path_map` has not been manually edited), auto-update `artifact_path_map` JSON with defaults for selected types from `PLATFORM_DEFAULTS` | Toggling artifact type adds/removes its path entry from JSON; once JSON is manually edited, auto-sync stops | 2 pts | ui-engineer-enhanced | EPP-P2-04 |
| EPP-P2-06 | Field reordering | Enforce field render order: `platform → profile_id → root_dir → supported_artifact_types → artifact_path_map → config_filenames → context_prefixes → description` | Visual inspection confirms field order; no functional regressions | 0.5 pts | ui-engineer-enhanced | EPP-P2-02 |
| EPP-P2-07 | Field tooltips | Add `<Tooltip>` (Radix/shadcn) to every field label: trigger is an `<InfoIcon>` `<button>` with `aria-label="Info: [field name]"`; tooltip content explains purpose and shows example value | All 8 fields have tooltip triggers; Tab + Enter/Space opens tooltip from keyboard; `aria-label` present on each trigger | 2 pts | ui-engineer-enhanced | EPP-P2-06 |
| EPP-P2-08 | Description textarea | Add optional `description` textarea to `CreateProfileForm` (shown below `context_prefixes`): max 500 chars, live character counter, `<label>` with explicit `for` association | Description value included in `onSubmit` payload; character counter shows remaining; 501st char rejected | 1 pt | ui-engineer-enhanced | EPP-P2-06 |
| EPP-P2-09 | Barrel export | Create `skillmeat/web/components/profiles/index.ts` exporting `CreateProfileForm` as named export | `import { CreateProfileForm } from '@/components/profiles'` resolves correctly | 0.5 pts | frontend-developer | EPP-P2-08 |
| EPP-P2-10 | Unit tests | Write Jest/RTL unit tests covering: (a) platform selection triggers pre-population, (b) artifact type toggle updates path map, (c) description character limit enforcement, (d) tooltip triggers are keyboard accessible | All tests pass in `pnpm test`; no type-check errors | 2 pts | frontend-developer | EPP-P2-09 |

**Phase Total**: 16.5 pts (PRD estimate: 12 pts — difference due to finer task granularity; re-estimate with team)

> **Note**: The PRD estimated 12 pts for Phase 2. This plan breaks the work into 9 sub-tasks totalling 16.5 pts. Before starting Phase 2, confirm with team whether EPP-P2-05 (path map sync) and EPP-P2-10 (unit tests) should be included or deferred to reduce scope to ~12 pts. All tasks are included here for completeness.

#### Phase 2 Quality Gates

- [ ] `CreateProfileForm` renders in `contextMode="page"` on the existing project profiles page without visual regression
- [ ] Multi-select for `supported_artifact_types` is keyboard-accessible (Space/Enter navigation)
- [ ] Selecting platform "codex" pre-populates all fields correctly from `PLATFORM_DEFAULTS`
- [ ] Changing artifact types auto-updates `artifact_path_map` (unless manually edited)
- [ ] All 8 form fields have visible tooltip triggers with `aria-label`
- [ ] `description` textarea enforces 500-char limit with live counter
- [ ] `import { CreateProfileForm } from '@/components/profiles'` resolves
- [ ] `pnpm type-check` passes with zero new errors
- [ ] `pnpm lint` passes on new/modified files with zero new warnings
- [ ] Unit tests pass (`pnpm test`)

---

### Phase 3: Create Project Dialog — Platform Profiles Section

**Duration**: 2–3 days
**Dependencies**: Phase 2 complete (`CreateProfileForm` exported from barrel)
**Assigned Subagent(s)**: `frontend-developer` (dialog wiring, accordion, toggle state, API call integration), `ui-engineer-enhanced` (platform card layout, customize dialog shell)
**Entry Criteria**: Phase 2 exit criteria met; `CreateProfileForm` barrel export verified.
**Exit Criteria**: Creating a project with two platforms toggled results in two `DeploymentProfile` rows in DB; profile creation errors surface as non-blocking toast; `pnpm type-check` passes.

#### Key Files

| Surface | File | Change |
|---------|------|--------|
| Create Project dialog | `skillmeat/web/app/projects/components/create-project-dialog.tsx` | Add Platform Profiles accordion section; toggle state management; customize dialog; profile creation API calls |
| Profiles hook | `skillmeat/web/hooks/use-deployment-profiles.ts` | Verify/expose mutation for creating profiles post-project-creation |
| Platform constants | `skillmeat/web/lib/constants/platform-defaults.ts` | Read platform keys to populate toggle cards |

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------------|--------------|
| EPP-P3-01 | Platform Profiles accordion | Add a collapsible `<Accordion>` section labeled "Platform Profiles" to the Create Project dialog below the description field; collapsed by default | Section renders; expand/collapse works; no layout shift | 1 pt | ui-engineer-enhanced | Phase 2 complete |
| EPP-P3-02 | Platform toggle cards | Render one row per `PLATFORM_DEFAULTS` key (5 platforms) inside the accordion; each row shows platform name/badge, a toggle switch, and a "Customize" button | All 5 platforms shown; toggle switch functional; "Customize" button visible but disabled until toggle is ON | 2 pts | ui-engineer-enhanced | EPP-P3-01 |
| EPP-P3-03 | Toggle state management | Toggling a platform ON creates a pending profile entry in local React state pre-populated from `PLATFORM_DEFAULTS[platform]`; toggling OFF removes it from state | State contains correct profile data per toggled platform; no DB calls at this point | 1.5 pts | frontend-developer | EPP-P3-02 |
| EPP-P3-04 | Customize dialog | "Customize" button (enabled only when toggle is ON) opens a `<Dialog>` containing `<CreateProfileForm contextMode="dialog" platformLock={platform} />` pre-populated from the current pending profile state for that platform | Dialog opens with form pre-populated; `platformLock` prevents platform change; dialog closes on save/cancel | 2 pts | frontend-developer | EPP-P3-03 |
| EPP-P3-05 | Custom profile state save | Saving from the Customize dialog updates the pending profile state for that platform and returns to the Create Project dialog; the platform card shows a "Customized" indicator | Pending state updated correctly; "Customized" badge visible on the card | 1 pt | frontend-developer | EPP-P3-04 |
| EPP-P3-06 | Profile creation on project save | After project creation succeeds, iterate toggled platforms and POST each profile to `/api/v1/projects/{project_id}/profiles` using `use-deployment-profiles` hook; profile creation errors are non-fatal (surface as warning toast; project creation is not rolled back) | Integration test confirms profile rows exist in DB after project creation; toast shown on partial failure; project not rolled back on profile POST failure | 2 pts | frontend-developer | EPP-P3-05 |
| EPP-P3-07 | Component tests | Write RTL tests: (a) toggling a platform creates pending state, (b) Customize dialog opens with correct pre-population, (c) form submission updates pending state, (d) project creation triggers profile POST calls | All component tests pass; `pnpm test` green | 1.5 pts | frontend-developer | EPP-P3-06 |

**Phase Total**: 11 pts (PRD estimate: 8 pts — difference accounts for component tests as separate task)

#### Phase 3 Quality Gates

- [ ] "Platform Profiles" accordion is collapsed by default in Create Project dialog
- [ ] All 5 platform toggle cards render with correct platform labels and badges
- [ ] Toggling ON creates correct pending profile state from `PLATFORM_DEFAULTS`
- [ ] "Customize" dialog opens with `CreateProfileForm` pre-populated and `platformLock` applied
- [ ] Creating a project with two platforms toggled ON results in two `DeploymentProfile` rows in DB
- [ ] Profile POST failure shows warning toast; project creation is not rolled back
- [ ] `pnpm type-check` passes with zero new errors
- [ ] Component tests pass

---

### Phase 4: Settings Platforms Tab

**Duration**: 1–2 days
**Dependencies**: Phase 2 complete (`CreateProfileForm` available); can run in parallel with Phase 3
**Assigned Subagent(s)**: `frontend-developer` (tab wiring, PlatformDefaultsSettings relocation), `ui-engineer-enhanced` (custom profile creation button and dialog integration)
**Entry Criteria**: Phase 2 exit criteria met.
**Exit Criteria**: Settings > Platforms tab renders with `PlatformDefaultsSettings`; "New Custom Profile" button opens `CreateProfileForm`; E2E navigation test passes.

#### Key Files

| Surface | File | Change |
|---------|------|--------|
| Settings page | `skillmeat/web/app/settings/page.tsx` | Add "Platforms" tab to `<Tabs>` component; move `PlatformDefaultsSettings` to tab content |
| Platform Defaults component | `skillmeat/web/components/settings/platform-defaults-settings.tsx` | No structural changes; relocated to Platforms tab |
| Custom Context component | `skillmeat/web/components/settings/custom-context-settings.tsx` | Verify still rendered in correct tab after refactor |

#### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Agent | Dependencies |
|---------|-----------|-------------|---------------------|----------|----------------|--------------|
| EPP-P4-01 | Platforms tab skeleton | Add "Platforms" tab trigger to the `<Tabs>` navigation in `settings/page.tsx`; add corresponding `<TabsContent>` panel | Tab renders and is keyboard-navigable; switching tabs works without page reload | 1 pt | frontend-developer | Phase 2 complete |
| EPP-P4-02 | Relocate PlatformDefaultsSettings | Move `<PlatformDefaultsSettings>` from its current inline position to the Platforms `<TabsContent>`; verify `CustomContextSettings` remains in correct existing tab | `PlatformDefaultsSettings` renders only in Platforms tab; `CustomContextSettings` position unchanged; no visual regression in other tabs | 1 pt | frontend-developer | EPP-P4-01 |
| EPP-P4-03 | New Custom Profile button | Add "New Custom Profile" button in the Platforms tab below `PlatformDefaultsSettings`; clicking opens a `<Dialog>` containing `<CreateProfileForm contextMode="dialog" />`; form submission posts profile to API | Button renders; dialog opens with `CreateProfileForm`; successful submission shows success toast and closes dialog | 2 pts | ui-engineer-enhanced | EPP-P4-02 |
| EPP-P4-04 | E2E navigation test | Write Playwright (or equivalent) E2E test: navigate to Settings > Platforms tab → assert `PlatformDefaultsSettings` table renders → assert "New Custom Profile" button is present | E2E test passes in CI | 1 pt | frontend-developer | EPP-P4-03 |

**Phase Total**: 5 pts

#### Phase 4 Quality Gates

- [ ] "Platforms" tab appears in Settings navigation and is keyboard-reachable
- [ ] `PlatformDefaultsSettings` component renders exclusively in the Platforms tab
- [ ] Existing tabs in Settings are unaffected by the refactor
- [ ] "New Custom Profile" button opens `CreateProfileForm` dialog
- [ ] Successful profile creation via Settings Platforms tab shows success toast
- [ ] E2E navigation test passes
- [ ] `pnpm type-check` passes with zero new errors

---

## Cross-Phase Validation

After all phases are complete, run the following end-to-end acceptance checks:

| Check | Steps | Expected Outcome |
|-------|-------|-----------------|
| Description round-trip | POST `/api/v1/projects/{id}/profiles` with `description: "Test desc"` → GET profile | GET response contains `description: "Test desc"` |
| Multi-context rendering | Open `CreateProfileForm` in: (1) profiles page, (2) Create Project customize dialog, (3) Settings Platforms tab | Form renders correctly in all three contexts without layout breakage |
| Platform pre-population | Select "codex" in `CreateProfileForm` | `supported_artifact_types: ['skill','command','agent']`; `artifact_path_map` auto-populated |
| Tooltip keyboard access | Tab to any field label info button → press Enter | Tooltip opens; `aria-label` present |
| Full create-project flow | Open Create Project dialog → expand Platform Profiles → toggle Claude Code ON → click Customize → edit root_dir → Save → fill other fields → Create Project | Project created; one `DeploymentProfile` row in DB for claude_code with custom `root_dir` |
| Settings tab navigation | Navigate to Settings → click Platforms tab | `PlatformDefaultsSettings` visible; "New Custom Profile" button visible |
| Migration reversibility | `alembic downgrade -1` | `description` column removed; no data corruption |

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Alembic migration conflict with active branches modifying `deployment_profiles` | High | Low | Check migration head before starting EPP-P1-01; coordinate with `feat/skill-contained-artifacts-v1` branch if it touches same table |
| ORM field name (`supported_types`) vs API field name (`supported_artifact_types`) drift | High | Medium | Add explicit comment in `DeploymentProfile.to_dict()` documenting the intentional divergence; add schema comment in `DeploymentProfileCreate`; do not change either name |
| Multi-select shadcn component unavailable or incompatible | Medium | Low | Fall back to Radix `Checkbox` list with manual state; implementation detail, not design change |
| Create Project dialog becomes too large with Platform Profiles section | Medium | Medium | Section collapsed by default via `<Accordion>`; run visual QA at end of Phase 3 |
| Partial profile creation after project creation leaves inconsistent state | Medium | Low | Surface as warning toast (non-blocking); user can complete profile setup on profiles page |
| Phase 2 effort overrun (16.5 pts vs PRD's 12 pts estimate) | Medium | Medium | Before starting Phase 2, confirm scope with team; EPP-P2-05 and EPP-P2-10 are candidate deferrals |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Phase 2 scope larger than estimated | Medium | Medium | Parallelize Phases 3 and 4 once Phase 2 is complete to recover timeline |
| Frontend type drift between `openapi.json` and `types/deployments.ts` | Medium | Low | EPP-P2-01 is the first Phase 2 task; validate against updated `openapi.json` from Phase 1 |

---

## Resource Requirements

### Team Composition

| Role | Agent | Phases |
|------|-------|--------|
| Data Layer | data-layer-expert | Phase 1 (EPP-P1-01, EPP-P1-02) |
| Backend Engineer | python-backend-engineer | Phase 1 (EPP-P1-03 through EPP-P1-06) |
| UI Engineer | ui-engineer-enhanced | Phase 2 (EPP-P2-02 through EPP-P2-09), Phase 3 (EPP-P3-01, EPP-P3-02), Phase 4 (EPP-P4-03) |
| Frontend Developer | frontend-developer | Phase 2 (EPP-P2-01, EPP-P2-09, EPP-P2-10), Phase 3 (EPP-P3-03 through EPP-P3-07), Phase 4 (EPP-P4-01, EPP-P4-02, EPP-P4-04) |
| Validator | task-completion-validator | Phase gate checks |
| Code Reviewer | code-reviewer | Post-phase code review gates |

### Skill Requirements

- Python, SQLAlchemy ORM, Alembic, Pydantic v2, FastAPI
- TypeScript, React 18, Next.js 15 App Router, TanStack Query
- Radix UI / shadcn/ui (Accordion, Dialog, Tooltip, Checkbox)
- Jest / React Testing Library, Playwright (E2E)
- `pnpm` workspace tooling

---

## Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Description field persists | Not present | Create → GET round-trip returns identical value | API integration test (EPP-P1-06) |
| Profiles created at project creation time | 0% of new projects | Functional via dialog | DB query after Phase 3 E2E test |
| `CreateProfileForm` context coverage | Page only | Page + dialog + settings | Manual QA in all 3 contexts |
| Artifact type multi-select coverage | Manual JSON | Auto-populated for all 5 platforms | QA: select each platform, verify path map |
| Type-check errors introduced | 0 target | 0 new errors | `pnpm type-check` after each phase |
| Accessibility violations | 0 target | 0 critical axe-core violations on new components | `pnpm test` accessibility assertions |

---

## Post-Implementation

- Monitor `deployment_profiles` table row counts to confirm profiles are being created at project creation time (success metric).
- Check Alembic migration history in production deploy to confirm clean upgrade.
- Collect user feedback on tooltip usefulness and multi-select UX.
- Track any 422 errors on `POST /api/v1/projects/{id}/profiles` to detect edge cases in the dialog flow.
- Deferred for follow-on PRD: cross-project global profile library; real-time platform detection; config file support for platform profiles.

---

**Progress Tracking**: `.claude/progress/enhanced-platform-profiles-v1/all-phases-progress.md`

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-22
