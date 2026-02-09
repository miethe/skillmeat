---
title: 'Implementation Plan: Platform Defaults Auto-Population'
description: Full auto-population of deployment profile fields when platform is selected,
  with tunable defaults via Settings page and config file
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- deployment-profiles
- platform-defaults
- settings
created: 2026-02-09
updated: '2026-02-09'
category: product-planning
status: completed
related:
- /docs/project_plans/PRDs/features/multi-platform-deployment-upgrade.md
---

# Implementation Plan: Platform Defaults Auto-Population

**Plan ID**: `IMPL-2026-02-09-PLATFORM-DEFAULTS`
**Date**: 2026-02-09
**Author**: Claude (Opus 4.6)
**Branch**: `feat/memory-workflow-enhancements-v3` (or new feature branch)

**Complexity**: Medium
**Total Estimated Effort**: ~38 story points
**Phases**: 5

## Executive Summary

Extends the deployment profile system so selecting a Platform auto-populates ALL fields (Root Dir, Artifact Path Map, Config Filenames, Supported Artifact Types, Context Prefixes) with platform-specific defaults. Defaults are tunable via the Settings page, config file (`~/.skillmeat/config.toml`), or environment variables. Includes a 3-option confirmation dialog for edit-mode platform changes and a custom context prefix system with per-platform targeting.

## Implementation Strategy

### Architecture Sequence

1. **Backend Foundation** - Shared constants module, ConfigManager methods, API endpoints
2. **Frontend Foundation** - TypeScript constants, API client, hooks, barrel exports
3. **Profile Form Logic** - Auto-population, touched-field tracking, edit confirmation dialog
4. **Settings Page UI** - Platform defaults editor, custom context prefixes editor
5. **Custom Context Integration** - Toggle in profile form, per-platform targeting

### Parallel Work Opportunities

- Phase 1 tasks (1.1, 1.2) are independent and can run in parallel
- Phase 2 tasks (2.1, 2.3) can start in parallel with Phase 1
- Phase 4 tasks (4.1, 4.2) are independent and can run in parallel

### Critical Path

Phase 1.3 (endpoints) → Phase 2.2 (API client + hooks) → Phase 3.1 (auto-population) → Phase 5.1 (custom context toggle)

### Data Flow

```
Hardcoded fallbacks (skillmeat/core/platform_defaults.py)
  ↓ deep-merge
ConfigManager TOML overrides (~/.skillmeat/config.toml → "platform.defaults.{platform}")
  ↓ deep-merge
Env var override (SKILLMEAT_PLATFORM_DEFAULTS_JSON → parsed JSON)
  ↓ apply custom context rules
Custom context config (platform.custom_context section)
  ↓ serve via API
GET /api/v1/settings/platform-defaults
  ↓ consumed by
Frontend usePlatformDefaults() hook → Profile form auto-population
```

---

## Phase 1: Backend Foundation

**Duration**: 1 session
**Dependencies**: None

### Task 1.1 — Create shared defaults module

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-1.1 | Platform defaults module | Create `skillmeat/core/platform_defaults.py` with `PLATFORM_DEFAULTS` dict for all 5 platforms and `resolve_platform_defaults()` / `resolve_all_platform_defaults()` functions | All 5 platforms have complete defaults (root_dir, artifact_path_map, config_filenames, supported_artifact_types, context_prefixes). Resolution layers: hardcoded → TOML → env var → custom context merge | 3 pts | python-backend-engineer | None |

**Platform default values:**
- `claude_code`: root=`.claude`, map={skill:skills, command:commands, agent:agents, hook:hooks, mcp:mcp}, configs=[CLAUDE.md], types=[skill,command,agent,hook,mcp], prefixes=[.claude/context/, .claude/]
- `codex`: root=`.codex`, map={skill:skills, command:commands, agent:agents}, configs=[AGENTS.md], types=[skill,command,agent], prefixes=[.codex/context/, .codex/]
- `gemini`: root=`.gemini`, map={skill:skills, command:commands}, configs=[GEMINI.md], types=[skill,command], prefixes=[.gemini/context/, .gemini/]
- `cursor`: root=`.cursor`, map={skill:skills, command:commands, agent:agents}, configs=[.cursorrules], types=[skill,command,agent], prefixes=[.cursor/context/, .cursor/]
- `other`: root=`.custom`, map={}, configs=[], types=[skill], prefixes=[]

### Task 1.2 — Create Pydantic schemas

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-1.2 | Platform defaults schemas | Create `skillmeat/api/schemas/platform_defaults.py` with `PlatformDefaultsEntry`, `PlatformDefaultsResponse`, `PlatformDefaultsUpdateRequest`, `CustomContextConfig`, `CustomContextConfigResponse`, `CustomContextConfigUpdateRequest` | All schemas validate correctly. Response includes all 5 fields per platform. CustomContextConfig has enabled (bool), prefixes (list), mode (override/addendum), platforms (list) | 2 pts | python-backend-engineer (Sonnet) | None |

### Task 1.3 — ConfigManager methods + API endpoints

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-1.3a | ConfigManager methods | Add to `skillmeat/config.py`: `get_platform_defaults(platform)`, `set_platform_defaults(platform, defaults)`, `get_custom_context_config()`, `set_custom_context_config(config)` | Methods read/write to TOML correctly. Default values returned when no overrides exist | 2 pts | python-backend-engineer | None |
| PD-1.3b | Settings API endpoints | Add 6 endpoints to `skillmeat/api/routers/settings.py`: GET/PUT/DELETE `/platform-defaults/{platform}`, GET `/platform-defaults` (all), GET/PUT `/custom-context` | All endpoints return correct data. PUT persists to TOML. DELETE resets to hardcoded. GET returns resolved (merged) defaults | 3 pts | python-backend-engineer | PD-1.1, PD-1.2, PD-1.3a |

**Phase 1 Quality Gates:**
- [ ] `resolve_platform_defaults()` returns correct merged values for each layer
- [ ] All 6 API endpoints return correct responses
- [ ] ConfigManager methods persist to `~/.skillmeat/config.toml`
- [ ] Env var `SKILLMEAT_PLATFORM_DEFAULTS_JSON` override works
- [ ] `pytest tests/test_platform_defaults.py -v` passes

---

## Phase 2: Frontend Foundation

**Duration**: 1 session
**Dependencies**: Phase 1 complete (for API endpoints)

### Task 2.1 — Frontend constants

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-2.1 | Platform defaults constants | Create `skillmeat/web/lib/constants/platform-defaults.ts` with `PlatformDefaults` interface and `PLATFORM_DEFAULTS` const mirroring Python values | TypeScript interface matches backend schema. All 5 platforms have complete defaults. Values match Python `PLATFORM_DEFAULTS` exactly | 1 pt | ui-engineer-enhanced (Sonnet) | None |

### Task 2.2 — API client + hooks

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-2.2a | API client functions | Create `skillmeat/web/lib/api/platform-defaults.ts` with functions: `getPlatformDefaults()`, `getPlatformDefault(platform)`, `updatePlatformDefault(platform, defaults)`, `resetPlatformDefault(platform)`, `getCustomContextConfig()`, `updateCustomContextConfig(config)` | All functions call correct endpoints. Error handling follows existing patterns (throw Error with detail message) | 2 pts | ui-engineer-enhanced | PD-1.3b |
| PD-2.2b | React hooks | Create `skillmeat/web/hooks/use-platform-defaults.ts` with query key factory and hooks: `usePlatformDefaults()`, `useUpdatePlatformDefault()`, `useResetPlatformDefault()`, `useCustomContextConfig()`, `useUpdateCustomContextConfig()` | Hooks use 5-min stale time. Mutations invalidate correct keys. Falls back to constants when API unavailable | 3 pts | ui-engineer-enhanced | PD-2.2a |
| PD-2.2c | Barrel exports | Update `skillmeat/web/hooks/index.ts` and `skillmeat/web/lib/api/index.ts` with new exports | All new hooks and API functions importable via barrel | 0.5 pts | ui-engineer-enhanced (Sonnet) | PD-2.2a, PD-2.2b |

### Task 2.3 — Platform change dialog

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-2.3 | Platform change dialog | Create `skillmeat/web/components/deployments/platform-change-dialog.tsx` using AlertDialog with 3 options: Keep Changes, Overwrite, Append | Dialog shows from→to platform names. All 3 callbacks fire correctly. Append option explained as "adds to multi-value fields" | 2 pts | ui-engineer-enhanced (Sonnet) | None |

**Phase 2 Quality Gates:**
- [ ] `pnpm type-check` passes with new files
- [ ] All hooks return expected data types
- [ ] Dialog renders with correct options
- [ ] Barrel exports resolve correctly

---

## Phase 3: Profile Form Auto-Population

**Duration**: 1 session
**Dependencies**: Phase 2 complete

### Task 3.1 — Create form auto-population

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-3.1 | Auto-populate create form | Modify `skillmeat/web/app/projects/[id]/profiles/page.tsx`: (1) Add `usePlatformDefaults()` hook, (2) Replace `defaultRootDir()` with `getDefaultsForPlatform()` covering all 5 fields, (3) Add `touchedFields: Set<keyof ProfileFormState>` state tracking, (4) Each field onChange adds to touchedFields, (5) Platform onValueChange populates ALL fields — for touched fields, append user content after defaults (multi-value) or replace (single-value), (6) Initial createForm state resolves from defaults | Selecting any platform fills all 5 fields. Manually edited fields have user content appended (not replaced) for multi-value fields. Initial form state matches Claude Code defaults from API/constants | 5 pts | ui-engineer-enhanced | PD-2.2b |

### Task 3.2 — Edit form platform change

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-3.2 | Edit form dialog integration | Modify profiles page edit form: (1) Platform onValueChange opens PlatformChangeDialog, (2) Keep = change platform value only, (3) Overwrite = replace all fields with new defaults, (4) Append = for multi-value fields append new defaults (deduplicate), for single-value use new default, for JSON deep-merge artifact_path_map | Keep leaves other fields unchanged. Overwrite fills all from defaults. Append adds without duplicates. Dialog shows correct from/to platforms | 4 pts | ui-engineer-enhanced | PD-3.1, PD-2.3 |

**Phase 3 Quality Gates:**
- [ ] Create form: selecting each platform fills all 5 fields correctly
- [ ] Create form: manually edited fields preserved (appended) on platform change
- [ ] Edit form: platform change shows 3-option dialog
- [ ] Edit form: Keep, Overwrite, Append all work correctly
- [ ] `pnpm type-check` passes
- [ ] `pnpm lint` passes

---

## Phase 4: Settings Page UI

**Duration**: 1 session
**Dependencies**: Phase 2 complete (hooks available)

### Task 4.1 — Platform defaults settings component

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-4.1 | Platform defaults editor | Create `skillmeat/web/components/settings/platform-defaults-settings.tsx`: Collapsible sections per platform (Accordion pattern). Each section has editable fields: root_dir (Input), artifact_path_map (JSON Textarea), config_filenames (Textarea), supported_artifact_types (Input), context_prefixes (Textarea). Save button and "Reset to Defaults" button per platform. Follows GitHubSettings pattern (client component, local state, useToast feedback) | All 5 platforms editable. Save persists to API. Reset returns hardcoded values. Toast feedback on save/reset. Loading state on initial fetch | 5 pts | ui-engineer-enhanced | PD-2.2b |

### Task 4.2 — Custom context settings component

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-4.2 | Custom context editor | Create `skillmeat/web/components/settings/custom-context-settings.tsx`: Switch toggle "Enable custom context prefixes". When enabled: Textarea for custom prefix list (newline-separated), Radio group for mode (Override/Addendum), Checkboxes for platform selection with "Select All" option. Save button | Toggle enables/disables section. Prefixes textarea accepts newline-separated input. Mode radio selects override or addendum. Platform checkboxes with Select All. Save persists via API | 4 pts | ui-engineer-enhanced | PD-2.2b |

### Task 4.3 — Settings page integration

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-4.3 | Settings page update | Modify `skillmeat/web/app/settings/page.tsx`: Import and render `<PlatformDefaultsSettings />` and `<CustomContextSettings />` in the existing card layout | Both components render on Settings page. Page layout consistent with existing sections | 0.5 pts | ui-engineer-enhanced (Sonnet) | PD-4.1, PD-4.2 |

**Phase 4 Quality Gates:**
- [ ] Platform defaults editor: all platforms editable, save/reset work
- [ ] Custom context editor: toggle, prefixes, mode, platform selection all work
- [ ] Settings page renders both new sections without layout issues
- [ ] `pnpm type-check` passes
- [ ] `pnpm lint` passes

---

## Phase 5: Custom Context Toggle in Profile Form

**Duration**: 0.5 session
**Dependencies**: Phase 3 and Phase 4 complete

### Task 5.1 — Custom context toggle

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| PD-5.1 | Context prefix toggle | Modify profiles page: Add "Use custom prefixes" Switch next to Context Prefixes field. Only visible when `useCustomContextConfig().enabled === true` AND current platform is in the custom context platforms list. When toggled on, applies custom prefixes per mode: override = replace context_prefixes with custom, addendum = append custom after defaults (deduplicate) | Toggle only visible when custom context enabled for platform. Override mode replaces prefixes. Addendum mode appends without duplicates. Toggle state persists during form session | 2 pts | ui-engineer-enhanced | PD-3.1, PD-4.2 |

**Phase 5 Quality Gates:**
- [ ] Toggle hidden when custom context disabled
- [ ] Toggle hidden when current platform not in custom context platforms list
- [ ] Override mode replaces context prefixes completely
- [ ] Addendum mode appends custom prefixes after defaults
- [ ] No duplicate prefixes when appending
- [ ] `pnpm type-check` and `pnpm lint` pass

---

## File Summary

### New Files (8)

| File | Phase | Purpose |
|------|-------|---------|
| `skillmeat/core/platform_defaults.py` | 1 | Hardcoded defaults + resolution logic |
| `skillmeat/api/schemas/platform_defaults.py` | 1 | Pydantic schemas for API endpoints |
| `skillmeat/web/lib/constants/platform-defaults.ts` | 2 | Frontend fallback constants |
| `skillmeat/web/lib/api/platform-defaults.ts` | 2 | API client functions |
| `skillmeat/web/hooks/use-platform-defaults.ts` | 2 | TanStack Query hooks |
| `skillmeat/web/components/deployments/platform-change-dialog.tsx` | 2 | Edit form confirmation dialog |
| `skillmeat/web/components/settings/platform-defaults-settings.tsx` | 4 | Settings page defaults editor |
| `skillmeat/web/components/settings/custom-context-settings.tsx` | 4 | Settings page custom context editor |

### Modified Files (5)

| File | Phase | Changes |
|------|-------|---------|
| `skillmeat/config.py` | 1 | Add 4 convenience methods for platform defaults + custom context |
| `skillmeat/api/routers/settings.py` | 1 | Add 6 new API endpoints |
| `skillmeat/web/app/projects/[id]/profiles/page.tsx` | 3, 5 | Auto-population logic, touchedFields, dialog integration, custom context toggle |
| `skillmeat/web/hooks/index.ts` | 2 | Add barrel exports for new hooks |
| `skillmeat/web/app/settings/page.tsx` | 4 | Import and render 2 new settings components |

---

## Config File Support (CLI Users)

Users can edit `~/.skillmeat/config.toml` directly:

```toml
[platform.defaults.claude_code]
root_dir = ".claude"
config_filenames = ["CLAUDE.md", "RULES.md"]
supported_artifact_types = ["skill", "command", "agent", "hook", "mcp"]
context_prefixes = [".claude/context/", ".claude/"]

[platform.defaults.claude_code.artifact_path_map]
skill = "skills"
command = "commands"
agent = "agents"

[platform.custom_context]
enabled = true
prefixes = ["docs/context/", "notes/"]
mode = "addendum"
platforms = ["claude_code", "codex"]
```

**Env var override**: `SKILLMEAT_PLATFORM_DEFAULTS_JSON='{"claude_code": {"root_dir": ".my-claude"}}'`

---

## Risk Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| FE/BE default values drift | Medium | Medium | Test that verifies FE constants match BE `PLATFORM_DEFAULTS` |
| touchedFields lost on re-render | High | Low | State lives in component, not dependent on re-fetch |
| Large JSON in env var | Low | Low | Validate parse, fallback to TOML on error |
| Settings page performance with 5 accordions | Low | Low | Lazy-load accordion content, debounce saves |

---

## Verification Plan

1. **Backend tests**: `pytest tests/test_platform_defaults.py -v`
2. **Type check**: `pnpm type-check`
3. **Lint**: `pnpm lint`
4. **Manual E2E**:
   - Create profile → select each platform → verify all 5 fields auto-populate
   - Edit profile → change platform → verify 3-option dialog → test each option
   - Settings → modify Claude Code defaults → create profile → verify custom defaults
   - Settings → enable custom context → assign to Codex → create Codex profile → verify
   - Edit `~/.skillmeat/config.toml` directly → verify API returns custom values
   - Set `SKILLMEAT_PLATFORM_DEFAULTS_JSON` env var → verify override applies

---

**Progress Tracking**: `.claude/progress/platform-defaults-auto-population/`

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-09
