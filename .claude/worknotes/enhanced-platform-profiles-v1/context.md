---
type: context
schema_version: 2
doc_type: context
prd: "enhanced-platform-profiles"
title: "Enhanced Platform Profiles - Development Context"
status: "active"
created: "2026-02-22"
updated: "2026-02-22"

critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []

agents: []
---

# Enhanced Platform Profiles - Development Context

**Status**: Active Development
**Created**: 2026-02-22
**Last Updated**: 2026-02-22

> **Purpose**: This is a shared worknotes file for all AI agents working on this PRD. Add brief observations, decisions, gotchas, and implementation notes that future agents should know. Think of this as a sticky-note pad for the development team.

---

## Quick Reference

**Agent Notes**: 0 notes from 0 agents
**Critical Items**: 0 items requiring attention
**Last Contribution**: N/A

---

## Feature Overview

Enhanced Platform Profiles delivers four cohesive improvements to SkillMeat's deployment-profile system across 4 phases:

| Phase | What | Key Deliverable |
|-------|------|----------------|
| P1 | Backend — description field | Alembic migration + ORM + schema + repo + OpenAPI |
| P2 | Reusable CreateProfileForm | Extracted component with multi-select, tooltips, auto-population |
| P3 | Create Project dialog integration | Accordion + toggle cards + Customize dialog |
| P4 | Settings Platforms tab | Relocated PlatformDefaultsSettings + New Custom Profile button |

**Total effort**: ~38.5 pts across 27 tasks
**PRD**: `docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md`
**Implementation Plan**: `docs/project_plans/implementation_plans/features/enhanced-platform-profiles-v1.md`
**Progress tracking**: `.claude/progress/enhanced-platform-profiles-v1/all-phases-progress.md`

---

## Key Files

### Phase 1 — Backend

| File | Role |
|------|------|
| `skillmeat/cache/migrations/versions/[new].py` | Alembic migration: add nullable description TEXT column |
| `skillmeat/cache/models.py` (~line 399) | ORM: `description: Mapped[Optional[str]]`; `to_dict()` update |
| `skillmeat/api/schemas/deployment_profiles.py` | Pydantic: `description: Optional[str] = Field(None, max_length=500)` on Create/Update/Read |
| `skillmeat/cache/repositories.py` (~line 3062) | Repository: pass `description` in `create_profile()` and `update_profile()` |
| `skillmeat/api/openapi.json` | Regenerate after schema changes |
| `tests/api/test_deployment_profiles.py` | Integration test: description round-trip |

### Phase 2 — CreateProfileForm Component

| File | Role |
|------|------|
| `skillmeat/web/types/deployments.ts` | Add `description?: string` to DeploymentProfile interface |
| `skillmeat/web/components/profiles/create-profile-form.tsx` | New reusable form component (extracted + enhanced) |
| `skillmeat/web/components/profiles/index.ts` | Barrel export: `export { CreateProfileForm }` |
| `skillmeat/web/app/projects/[id]/profiles/page.tsx` | Replace inline form with `<CreateProfileForm contextMode="page" />` |
| `skillmeat/web/lib/constants/platform-defaults.ts` | Source of truth for PLATFORM_DEFAULTS; verify keys match API values |
| `skillmeat/web/hooks/use-deployment-profiles.ts` | Verify mutation accepts `description` in payload |

### Phase 3 — Create Project Dialog

| File | Role |
|------|------|
| `skillmeat/web/app/projects/components/create-project-dialog.tsx` | Add Platform Profiles accordion, toggle state, customize dialog, profile POST calls |

### Phase 4 — Settings Platforms Tab

| File | Role |
|------|------|
| `skillmeat/web/app/settings/page.tsx` | Add Platforms tab trigger + TabsContent |
| `skillmeat/web/components/settings/platform-defaults-settings.tsx` | Relocated to Platforms tab (no structural changes) |
| `skillmeat/web/components/settings/custom-context-settings.tsx` | Verify not displaced by refactor |

---

## Architecture Notes

### 4-Phase Approach and Rationale

The implementation follows SkillMeat's standard layered order (DB → ORM → schema → repo → OpenAPI → frontend types → components → integration → settings) to prevent type drift between backend and frontend.

**Phase 1 must complete before Phase 2** because the frontend type update (EPP-P2-01) must match the final backend schema. Starting Phase 2 before Phase 1 would require rework if schema decisions change.

**Phase 2 must complete before Phases 3 and 4** because both consume `CreateProfileForm` from the barrel export. The barrel (EPP-P2-09) is the gate task.

**Phases 3 and 4 can run in parallel** — they touch entirely disjoint files (`create-project-dialog.tsx` vs `settings/page.tsx`) and share only a read dependency on the barrel export.

```
Phase 1 (Backend)
  └─→ Phase 2 (CreateProfileForm)
        ├─→ Phase 3 (Create Project dialog)  ─┐
        └─→ Phase 4 (Settings Platforms tab) ─┴─→ Cross-phase validation
```

### CreateProfileForm Context Modes

The component accepts `contextMode: 'page' | 'dialog'` to adjust layout:
- `page`: full-width layout on the profiles page
- `dialog`: compact layout for use inside Modal/Dialog containers

`platformLock?: Platform` prevents platform selection when the form is opened from a context that pre-selects a platform (e.g., Customize dialog in Phase 3, or a future per-platform creation flow).

### ORM vs API Field Name Divergence

`DeploymentProfile.supported_types` (ORM column) maps to `supported_artifact_types` (API field). This is an intentional divergence. **Do not rename either field.** The mapping is documented in `to_dict()`. Any agent touching this area must preserve both names.

### Non-Blocking Profile Creation (Phase 3)

Profile POST calls after project creation (EPP-P3-06) are fire-and-forget with error surfacing as a warning toast. The project creation is never rolled back on profile POST failure. Users can complete profile setup via the profiles page. This decision keeps the Create Project dialog's happy path simple.

---

## Phase Dependency Map

```
EPP-P1-01 (migration)
  └─→ EPP-P1-02 (ORM)
        └─→ EPP-P1-03 (schema)
              └─→ EPP-P1-04 (repo)
                    └─→ EPP-P1-05 (openapi)
                          └─→ EPP-P1-06 (test)
                                └─→ EPP-P2-01 (FE types)
                                      └─→ EPP-P2-02 (component extraction)
                                            ├─→ EPP-P2-03 (multi-select)
                                            ├─→ EPP-P2-04 (pre-population)
                                            │     └─→ EPP-P2-05 (path-map sync)
                                            └─→ EPP-P2-06 (field order)
                                                  ├─→ EPP-P2-07 (tooltips)
                                                  └─→ EPP-P2-08 (description textarea)
                                                        └─→ EPP-P2-09 (barrel export)   ← GATE
                                                              ├─→ EPP-P2-10 (unit tests)
                                                              ├─→ EPP-P3-01 → ... → EPP-P3-07
                                                              └─→ EPP-P4-01 → ... → EPP-P4-04
```

---

## Implementation Decisions

*(Add entries as decisions are made during implementation)*

---

## Gotchas & Observations

*(Add entries as gotchas are discovered during implementation)*

---

## Integration Notes

*(Add entries as integration points are discovered)*

---

## Agent Handoff Notes

*(Add entries as phases hand off between agents)*

---

## References

- **PRD**: `docs/project_plans/PRDs/features/enhanced-platform-profiles-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/enhanced-platform-profiles-v1.md`
- **Progress Tracking**: `.claude/progress/enhanced-platform-profiles-v1/all-phases-progress.md`
- **Existing profiles router**: `skillmeat/api/routers/deployment_profiles.py`
- **Existing profiles schemas**: `skillmeat/api/schemas/deployment_profiles.py`
- **Platform constants**: `skillmeat/web/lib/constants/platform-defaults.ts`
- **OpenAPI contract**: `skillmeat/api/openapi.json`
