---
title: 'Phase 4: Discovery, Cache, and UI/UX'
parent: ../multi-platform-project-deployments-v1.md
status: inferred_complete
---
# Phase 4: Discovery, Cache, and UI/UX

**Duration**: 1.5 weeks
**Dependencies**: Phase 2 (deployment engine), Phase 3 (context entity); Phase 2 task P2-T5 (discovery) particularly critical
**Total Effort**: 20 story points

## Overview

Phase 4 brings project discovery and cache infrastructure into the multi-platform world, and creates frontend UX for managing deployments across platforms. It expands the FileWatcher to monitor all profile roots, updates project stats aggregation, adds platform detection on artifact import, and builds UI components for profile selection and cross-platform sync visualization.

## Task Breakdown

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|--------------|
| P4-T1 | Extend FileWatcher to all profile roots | Update `skillmeat/cache/watcher.py` lines 204-205, 317 to monitor not just `.claude/` but all configured profile roots (`.codex/`, `.gemini/`, custom); emit events for changes in any profile root | FileWatcher starts watching all profile roots; file events include profile info; changes in any profile trigger cache invalidation | 2 pts | python-backend-engineer | P2-T5 |
| P4-T2 | Update cache invalidation for profile-aware changes | Modify cache invalidation logic in `skillmeat/cache/` to handle changes in any profile; ensure `refresh_single_artifact_cache()` accepts profile parameter; update project stats aggregation to sum across all profiles | Cache invalidation covers all profiles; project stats show totals across profiles and per-profile breakdown | 1.5 pts | python-backend-engineer | P4-T1 |
| P4-T3 | Implement platform detection on artifact import | When importing from repos with `.codex/` or `.gemini/` directories, scan source structure and auto-tag artifacts with `target_platforms` based on source (e.g., Codex-sourced artifacts tagged with `[CODEX]`); update import workflow | Import detects source platform; artifacts inherit `target_platforms` from source; users can override | 1.5 pts | python-backend-engineer | P1-T2, P2-T5 |
| P4-T4 | Create DeploymentProfile selector component | Build React component in `skillmeat/web/components/` for profile selection in deploy dialogs; dropdown showing available profiles (Claude, Codex, Gemini, custom); default to primary profile; clear descriptions per platform | Component renders list of profiles; shows platform, description; integrates with deployment dialog | 2 pts | ui-engineer-enhanced | P1-T6 |
| P4-T5 | Update deploy-dialog component for profile support | Modify `skillmeat/web/components/collection/deploy-dialog.tsx` to include profile selector (P4-T4); add `--all-profiles` checkbox for one-click deploy to all | Deploy dialog shows profile selector; form submits `deployment_profile_id` to backend; all-profiles checkbox works | 1.5 pts | frontend-developer | P4-T4 |
| P4-T6 | Update template-deploy-wizard for profile awareness | Modify `skillmeat/web/components/templates/template-deploy-wizard.tsx` to accept profile during template deployment; ensure context entities in template deploy to correct profile | Template wizard includes profile selector in deployment step; context entities in template respect profile | 1.5 pts | frontend-developer | P4-T4 |
| P4-T7 | Add profile parameter to API client deployment calls | Update `skillmeat/web/lib/api/deployments.ts` to send `deployment_profile_id` in deploy requests; update all artifact and context entity deploy functions to accept profile parameter | API client methods include profile parameter; deploy requests send it to backend | 1 pt | frontend-developer | P2-T10 |
| P4-T8 | Generate CLI commands with profile support | Update `skillmeat/web/lib/cli-commands.ts` to generate `skillmeat deploy <artifact> --profile <id>` and `skillmeat deploy <artifact> --all-profiles` commands based on user selections | Generated CLI commands include `--profile` flags correctly; `--all-profiles` generates correct command | 1 pt | frontend-developer | P2-T6 |
| P4-T9 | Create deployment status component showing profiles | Build component displaying deployment status segmented by profile; show artifact name, version, deployed profiles (checkmarks per profile), last deployed time per profile | Component shows artifacts and which profiles they're deployed to; respects platform filtering | 2 pts | ui-engineer-enhanced | P2-T11 |
| P4-T10 | Create cross-platform sync comparison view | Build UI showing sync state across profiles (e.g., "Claude: v1.2, Codex: v1.1, Gemini: none"); highlight mismatches; suggest sync actions per profile | Component compares versions across profiles; highlights out-of-sync platforms; UI intuitive | 2 pts | ui-engineer-enhanced | P2-T11, P3-T13 |
| P4-T11 | Add artifact filter by target_platforms | Extend artifact list/search UI to support filtering by `target_platforms` (e.g., "show only Codex artifacts", "show universal"); implement in `skillmeat/web/components/artifact-list.tsx` | Artifact list shows platform tags; filter dropdown filters by target platforms; works in search results | 1.5 pts | frontend-developer | P1-T4 |
| P4-T12 | Create deployment profile management UI | Build page/modal in `skillmeat/web/app/projects/[id]/profiles` for viewing/editing project profiles; allow adding new profiles, updating artifact path maps, configuring context prefixes | Profile management UI shows all profiles; edit profile details; forms validate JSON artifact path maps | 2 pts | ui-engineer-enhanced | P1-T11 |
| P4-T13 | Create hooks for profile-aware deployment state | Build custom React hooks: `useDeploymentProfiles(projectId)`, `useDeploymentStatus(artifactId, projectId)` (returns per-profile status), `useProfileSelector()` (manages profile selection state); add to `skillmeat/web/hooks/index.ts` | Hooks abstract profile querying logic; components consume hooks; state management clean | 1.5 pts | frontend-developer | P2-T10, P2-T11 |
| P4-T14 | Update frontend types for profile info | Extend `skillmeat/web/types/deployments.ts` with `DeploymentProfile`, `DeploymentStatus` (with per-profile breakdown); update `skillmeat/web/types/artifacts.ts` to include `target_platforms`; ensure TS types match backend schemas | Types mirror backend Pydantic models; OpenAPI-generated types match runtime | 1 pt | frontend-developer | P1-T7, P4-T7 |
| P4-T15 | Add profile selection to context entity deploy UI | Extend context entity deployment UI (likely in modal or sidebar) to show profile selector; allow deploying to specific profile or all profiles | Context deploy UI includes profile selector; matches artifact deploy UX | 1 pt | frontend-developer | P3-T7 |
| P4-T16 | Design platform badge/icon component | Create small reusable component showing platform badges (Claude Code icon, Codex icon, Gemini icon); used in profile selector, status displays, artifact filters | Component renders consistent icons for each platform; integrates with other UI elements | 0.5 pts | ui-designer | None |
| P4-T17 | Update API endpoints to return profile info | Ensure all relevant API responses include profile data: `GET /projects/{id}` returns `deployment_profiles` list, `GET /artifacts/{id}` returns `target_platforms`, `GET /projects/{id}/status` returns per-profile deployment breakdown | API responses have profile info; OpenAPI docs updated | 1 pt | python-backend-engineer | P2-T10, P2-T11 |
| P4-T18 | Frontend integration tests: profile selection and deploy | Test deploying artifact with profile selector in UI; test deploying to all profiles; test sync status view; test artifact filter by platform | Integration tests cover: profile selection, deploy with selected profile, all-profiles deploy, sync view rendering | 2 pts | frontend-developer | P4-T5, P4-T9, P4-T10 |
| P4-T19 | End-to-end test: multi-platform deployment workflow | Full E2E test: create project, set up multiple profiles, deploy artifacts to different profiles via UI, verify status, verify CLI commands match UI state | E2E test covers full user journey: project setup, multi-profile deployment, status verification | 1.5 pts | testing-specialist | P4-T5, P4-T9, P4-T18 |

## Quality Gates

- [ ] FileWatcher successfully monitors all profile roots; cache invalidation working for all platforms
- [ ] Platform detection on import working; artifacts tagged with source platform
- [ ] Deploy dialog renders profile selector; form submission includes profile ID
- [ ] `--all-profiles` checkbox/flag works; artifacts deploy to all profiles
- [ ] Deployment status component shows per-profile breakdown correctly
- [ ] Cross-platform sync comparison UI renders and highlights mismatches
- [ ] Artifact filtering by `target_platforms` working in search/list
- [ ] Profile management UI allows creating/editing profiles
- [ ] Hooks exported in `skillmeat/web/hooks/index.ts` and documented
- [ ] Frontend types match backend API contracts
- [ ] All integration and E2E tests passing
- [ ] No regressions to existing deployment or discovery workflows
- [ ] Accessibility audit passed for new UI components

## Key Files

**Backend Discovery/Cache** (modified):
- `skillmeat/cache/watcher.py` — Extended to all profile roots (P4-T1)
- `skillmeat/cache/` — Cache invalidation logic updated (P4-T2)
- `skillmeat/core/discovery.py` — (Already profile-aware from Phase 2)

**Backend API** (modified):
- `skillmeat/api/routers/deployments.py` — Returns profile info in responses (P4-T17)
- `skillmeat/api/routers/projects.py` — Returns `deployment_profiles` in project response (P4-T17)

**Frontend Components** (new/modified):
- `skillmeat/web/components/profile-selector.tsx` — New (P4-T4)
- `skillmeat/web/components/platform-badge.tsx` — New (P4-T16)
- `skillmeat/web/components/deployment-status-profile-view.tsx` — New (P4-T9)
- `skillmeat/web/components/sync-comparison-view.tsx` — New (P4-T10)
- `skillmeat/web/components/collection/deploy-dialog.tsx` — Added profile selector (P4-T5)
- `skillmeat/web/components/templates/template-deploy-wizard.tsx` — Added profile selector (P4-T6)
- `skillmeat/web/components/artifact-list.tsx` — Added platform filter (P4-T11)
- `skillmeat/web/app/projects/[id]/profiles` — New profile management page (P4-T12)

**Frontend API/Hooks** (new/modified):
- `skillmeat/web/lib/api/deployments.ts` — Profile parameter added (P4-T7)
- `skillmeat/web/lib/cli-commands.ts` — Profile flag generation (P4-T8)
- `skillmeat/web/hooks/index.ts` — New hooks for profile-aware state (P4-T13)
- `skillmeat/web/types/deployments.ts` — DeploymentProfile, updated DeploymentStatus (P4-T14)
- `skillmeat/web/types/artifacts.ts` — Added `target_platforms` field (P4-T14)

**Tests** (new):
- `tests/test_cache_watcher_profiles.py` — FileWatcher multi-profile tests (P4-T1)
- `tests/test_platform_detection_import.py` — Platform detection on import (P4-T3)
- `tests/web/__tests__/components/profile-selector.test.tsx` — Component tests (P4-T4)
- `tests/web/__tests__/components/deploy-dialog-profile.test.tsx` — Deploy dialog profile tests (P4-T5)
- `tests/web/__tests__/components/sync-comparison-view.test.tsx` — Sync view tests (P4-T10)
- `tests/web/__tests__/hooks/useDeploymentProfiles.test.ts` — Hook tests (P4-T13)
- `tests/web/e2e/multi-platform-deployment.spec.ts` — E2E tests (P4-T19)

## Integration Notes

**Design Phase Parallel**: UI component design (P4-T16, P4-T4) can start while Phase 3 is finishing; no dependencies on Phase 3 for design work.

**Platform Badges**: P4-T16 should coordinate with product/design team for icon choices (Claude/Codex/Gemini official icons or internal design).

**Profile Management UX**: P4-T12 is a new page; coordinate navigation/menu integration with existing sidebar or project settings.

**Hook Design**: Phase 4 hooks (P4-T13) should follow React Query patterns used elsewhere in codebase (if applicable); ensure consistency with existing `use*` hooks.

**Symlink-Aware FileWatcher**: P4-T1 should coordinate with Phase 2 symlink handling to ensure FileWatcher correctly monitors both symlinked and native profile roots.

**Performance**: FileWatcher monitoring multiple profile roots may increase I/O on projects with many profiles. Consider debouncing or throttling if needed; add observability metrics for FileWatcher performance.

---

**Phase Status**: Awaiting Phase 2 and Phase 3 completion
**Blocks**: Phase 5 (Migration and Compatibility)
**Blocked By**: Phase 2 (Deployment Engine), Phase 3 (Context Entity)
