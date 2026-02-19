---
title: 'Implementation Plan: Sync/Diff Modal Standardization'
description: Fix sync/diff inconsistencies, add project context to /manage, extract
  modal foundation, wire mutations
audience:
- ai-agents
- developers
tags:
- implementation
- planning
- refactor
- sync
- diff
- modal
created: 2026-02-04
updated: 2026-02-04
category: product-planning
status: inferred_complete
related:
- /docs/project_plans/PRDs/refactors/sync-diff-modal-standardization-v1.md
- /docs/project_plans/reports/sync-diff-modal-inconsistency-analysis-2026-02-04.md
---
# Implementation Plan: Sync/Diff Modal Standardization

**Plan ID**: `IMPL-2026-02-04-SYNC-DIFF-MODAL`
**Date**: 2026-02-04
**Author**: Claude Opus 4.5

**Complexity**: High
**Total Estimated Effort**: 34 pts
**Risk**: Medium (cross-cutting modal refactor touches shared sync component)

## Executive Summary

The `/manage` page sync tab produces 400 errors for marketplace artifacts and cannot show collection-vs-project diffs due to four root causes: frontend-backend source validation mismatch, missing `projectPath` in collection mode, divergent modal architectures, and stubbed mutations. This plan fixes all four issues across 5 phases, extracting a `BaseArtifactModal` foundation for future convergence. No backend changes required -- all API endpoints already exist.

## Critical Path

```
Phase 1 (validation) --> Phase 2 (project context) --> Phase 3 (modal foundation) --> Phase 5 (testing)
                                                   \-> Phase 4 (mutations)       --> Phase 5 (testing)
```

## Parallel Work Opportunities

- Phase 1 and TASK-3.1 (analysis only) can start simultaneously
- Phase 4 starts after Phase 2 completes, independent of Phase 3
- Phase 5 testing tasks overlap with late Phase 3 and Phase 4

---

## Phase 1: Fix Frontend Validation

**Priority**: HIGH
**Dependencies**: None
**Assigned Subagent(s)**: ui-engineer-enhanced (Opus)

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| TASK-1.1 | Update `hasValidUpstreamSource()` | In `sync-status-tab.tsx` (lines 98-104), change signature from `(source: string)` to `(entity: Artifact)`. Add checks: `entity.origin === 'github'` AND `entity.upstream?.tracking_enabled`. Keep source URL validation as secondary check. | Function returns false for marketplace/local artifacts; true only for github+tracking | 2 pts | ui-engineer-enhanced | None |
| TASK-1.2 | Update upstream-diff query enablement | In `sync-status-tab.tsx` (lines 238-239), change `hasValidUpstreamSource(entity.source)` to `hasValidUpstreamSource(entity)`. Add `retry: false` to query options to prevent retry loops on 400s. | Query only fires for github-origin artifacts with tracking; no retries on failure | 1 pt | ui-engineer-enhanced | TASK-1.1 |
| TASK-1.3 | Remove duplicate validation | In `artifact-operations-modal.tsx` (lines 435-441), remove duplicate `hasValidUpstreamSource()`. Import from sync-status-tab or extract to `web/lib/sync-utils.ts`. | Single source of truth for upstream validation logic | 1 pt | ui-engineer-enhanced | TASK-1.1 |
| TASK-1.4 | Verify validation fix | Test marketplace (codex), GitHub (3d-graphics), and local artifacts on /manage. Check browser console for 400 errors and TanStack Query retry behavior. | Zero 400 errors; upstream diff fires only for github+tracking artifacts; marketplace/local show "no upstream" state | 1 pt | ui-engineer-enhanced | TASK-1.2, TASK-1.3 |

**Key Files Modified**:
- `skillmeat/web/components/sync-status/sync-status-tab.tsx` lines 98-104, 238-239
- `skillmeat/web/components/manage/artifact-operations-modal.tsx` lines 435-441
- `skillmeat/web/lib/sync-utils.ts` (new, if extracting shared util)

**Phase 1 Quality Gates:**
- [ ] Zero 400 errors on /manage for any artifact type
- [ ] GitHub artifacts with tracking show upstream diff
- [ ] Marketplace/local artifacts show appropriate "no upstream" state
- [ ] No TanStack Query retry loops (confirm with DevTools)

---

## Phase 2: Add Project Context to /manage

**Priority**: HIGH
**Dependencies**: Phase 1 complete
**Assigned Subagent(s)**: ui-engineer-enhanced (Opus)

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| TASK-2.1 | Add `selectedProjectForDiff` state | In `ArtifactOperationsModal`, add `selectedProjectForDiff` state (similar to `UnifiedEntityModal` line 619-622). Derive initial value from `artifact.deployments` -- auto-detect when exactly one deployment exists. | State initializes with auto-detected project or null; updates when user selects | 2 pts | ui-engineer-enhanced | Phase 1 |
| TASK-2.2 | Integrate `ProjectSelectorForDiff` | Import `ProjectSelectorForDiff` from `web/components/entity/project-selector-for-diff.tsx`. Render above or within sync tab when in collection mode. Pass `onProjectSelected` callback to update state. | Project selector visible on /manage sync tab; lists deployed projects | 3 pts | ui-engineer-enhanced | TASK-2.1 |
| TASK-2.3 | Pass `projectPath` to `SyncStatusTab` | Update `artifact-operations-modal.tsx` lines 1185-1191 to include `projectPath={selectedProjectForDiff}`. Keep `mode="collection"` but now WITH project context for diff queries. | SyncStatusTab receives projectPath; project diff query enables when path is set | 2 pts | ui-engineer-enhanced | TASK-2.2 |
| TASK-2.4 | Update `ComparisonSelector` enablement | In `comparison-selector.tsx`, verify `hasProject` flag is true when `projectPath` is available. Ensure all three comparison scopes (source, collection-vs-project, source-vs-project) are enabled when both source and project are available. | All applicable comparison scopes enabled based on available data | 1 pt | ui-engineer-enhanced | TASK-2.3 |
| TASK-2.5 | Verify project context | Test with deployed artifacts on /manage: collection-vs-project diff loads, flow banner shows correct deployment status, source-vs-project diff works for GitHub artifacts. | Diffs load; flow banner accurate; all three scopes work when applicable | 1 pt | ui-engineer-enhanced | TASK-2.4 |

**Key Files Modified**:
- `skillmeat/web/components/manage/artifact-operations-modal.tsx` lines 1185-1191 (props), new state
- `skillmeat/web/components/sync-status/comparison-selector.tsx` (enablement logic)

**Phase 2 Quality Gates:**
- [ ] Project selector visible on /manage sync tab
- [ ] Auto-detection works for single-deployment artifacts
- [ ] All three comparison scopes available when applicable
- [ ] Flow banner shows accurate deployment status

---

## Phase 3: Extract BaseArtifactModal Foundation

**Priority**: MEDIUM
**Dependencies**: Phase 2 complete (TASK-3.1 can start during Phase 1)
**Assigned Subagent(s)**: codebase-explorer (Haiku) for analysis, ui-engineer-enhanced (Opus) for implementation

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| TASK-3.1 | Analyze shared modal patterns | Compare `ArtifactOperationsModal` (1,411 lines) and `UnifiedEntityModal` (2,566 lines). Identify common: header rendering, tab bar, modal container, lifecycle provider setup, close handling, query/mutation hooks. Document extraction targets with line references. | Written analysis with specific shared patterns and extraction boundaries | 2 pts | codebase-explorer (Haiku) | None |
| TASK-3.2 | Create `BaseArtifactModal` component | File: `web/components/shared/BaseArtifactModal.tsx`. Props: `artifact`, `open`, `onClose`, `initialTab`, `mode`, `projectPath?`, `tabs` (config array), `children` (render function or slots). Encapsulate: modal container, header with artifact info, tab navigation, lifecycle provider wrapping. Use composition pattern for tab content. | Component renders modal shell with configurable tabs; accepts content via composition | 5 pts | ui-engineer-enhanced | TASK-3.1 |
| TASK-3.3 | Refactor `ArtifactOperationsModal` | Replace boilerplate with `BaseArtifactModal` composition. Keep custom tab content implementations. Target: reduce from 1,411 lines to ~600-800 lines. | All existing tabs function correctly; line count reduced 30%+; no TypeScript errors | 5 pts | ui-engineer-enhanced | TASK-3.2 |
| TASK-3.4 | Verify modal refactor | Test all tabs on /manage (status, overview, files, sync, deploy, settings). Test all tabs on /projects (regression). Verify no visual or functional regressions. | All tabs work on both pages; no console errors; no visual regressions | 1 pt | ui-engineer-enhanced | TASK-3.3 |

**Key Files Modified**:
- `skillmeat/web/components/shared/BaseArtifactModal.tsx` (new)
- `skillmeat/web/components/manage/artifact-operations-modal.tsx` (major refactor)

**Phase 3 Quality Gates:**
- [ ] `BaseArtifactModal` handles 60%+ of modal boilerplate
- [ ] `ArtifactOperationsModal` reduced by 30%+ lines
- [ ] All tabs function correctly on both pages
- [ ] No TypeScript errors (`pnpm tsc --noEmit`)

---

## Phase 4: Wire Up Missing Mutations

**Priority**: MEDIUM
**Dependencies**: Phase 2 complete (independent of Phase 3)
**Assigned Subagent(s)**: ui-engineer-enhanced (Opus)

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| TASK-4.1 | Implement `keepLocalMutation` | In `sync-status-tab.tsx` (lines 357-369), replace `Promise.resolve()` with: dismiss drift banner via local state, optionally create a "reviewed" marker timestamp. No API call needed. Invalidate drift-related query state after dismissal. | Keep-local action dismisses diff; drift banner clears; no API call fired | 2 pts | ui-engineer-enhanced | Phase 2 |
| TASK-4.2 | Implement batch actions | In `sync-status-tab.tsx` (lines 403-406), replace toast with actual batch operation. Call `POST /context-sync/push` with entity IDs for push operations, `POST /context-sync/pull` for pull operations. Invalidate: `['context-sync-status']`, `['artifact-files']`, `['context-entities']`, `['deployments']`. | Batch actions execute; correct endpoint called; cache invalidated per graph | 3 pts | ui-engineer-enhanced | Phase 2 |
| TASK-4.3 | Implement push-to-collection | In `sync-status-tab.tsx` (lines 483, 519), replace "Coming Soon" toast with `POST /context-sync/pull` call (pull from project to collection). Requires `projectPath` from Phase 2. Invalidate: `['context-sync-status']`, `['artifact-files']`, `['context-entities']`, `['deployments']`. | Push-to-collection syncs project changes back; correct cache invalidation | 2 pts | ui-engineer-enhanced | Phase 2 |
| TASK-4.4 | Verify all mutations | Test keep-local dismisses drift. Test batch actions execute with correct endpoints. Test push-to-collection syncs. Verify cache invalidation with TanStack Query DevTools. Test on both /manage and /projects pages. | All mutations work end-to-end; no stubs remain; cache consistent | 1 pt | ui-engineer-enhanced | TASK-4.1, TASK-4.2, TASK-4.3 |

**Key Files Modified**:
- `skillmeat/web/components/sync-status/sync-status-tab.tsx` lines 357-369, 403-406, 483, 519

**Cache Invalidation Reference** (must follow):

| Mutation | Must Invalidate |
|----------|----------------|
| Deploy/Undeploy | `['deployments']`, `['artifacts']`, `['projects']` |
| Context sync push/pull | `['context-sync-status']`, `['artifact-files']`, `['context-entities']`, `['deployments']` |

**Phase 4 Quality Gates:**
- [ ] No "coming soon" or "not yet implemented" toasts remain
- [ ] All mutations call correct endpoints
- [ ] Cache invalidation follows data-flow-patterns graph
- [ ] Mutations work on both /manage and /projects pages

---

## Phase 5: Testing and Documentation

**Priority**: MEDIUM
**Dependencies**: Phases 1-4 complete (can overlap with late Phase 3 and Phase 4)
**Assigned Subagent(s)**: ui-engineer-enhanced (Opus), documentation-writer (Haiku)

| Task ID | Task Name | Description | Acceptance Criteria | Est | Subagent | Deps |
|---------|-----------|-------------|---------------------|-----|----------|------|
| TASK-5.1 | Unit tests for `hasValidUpstreamSource()` | File: `web/__tests__/sync-utils.test.ts` (or `sync-status-tab.test.tsx`). Test cases: github+tracking (true), github-no-tracking (false), marketplace (false), local (false), null origin (false), null upstream (false). | 6+ test cases covering all origin/tracking combinations; all pass | 2 pts | ui-engineer-enhanced | Phase 1 |
| TASK-5.2 | Integration tests for modal sync workflows | Test /manage modal: upstream diff query enablement, project diff query enablement. Test /projects modal: regression (no behavioral change). Mock API responses, verify query enablement logic. | 4+ integration tests covering both modals; all pass | 3 pts | ui-engineer-enhanced | Phase 2, Phase 4 |
| TASK-5.3 | Update CLAUDE.md with modal patterns | Document `BaseArtifactModal` composition pattern in `skillmeat/web/CLAUDE.md`. Add sync tab data flow diagram. Document `hasValidUpstreamSource()` validation logic. | web/CLAUDE.md reflects new patterns; findable by future agents | 1 pt | documentation-writer (Haiku) | Phase 3 |
| TASK-5.4 | Update API endpoint mapping | Ensure `.claude/context/api-endpoint-mapping.md` includes sync/diff endpoints with required params and cache invalidation keys. | Endpoint mapping complete for all sync/diff endpoints | 1 pt | documentation-writer (Haiku) | Phase 4 |

**Phase 5 Quality Gates:**
- [ ] 80%+ coverage for new/modified code
- [ ] All tests pass (`pnpm test`)
- [ ] CLAUDE.md updated with modal patterns
- [ ] API endpoint mapping includes sync/diff endpoints
- [ ] No regressions on either page

---

## Files Changed Summary

| File | Change Type | Phase |
|------|-------------|-------|
| `web/components/sync-status/sync-status-tab.tsx` | MODIFY validation, query enablement, mutations | 1, 4 |
| `web/components/manage/artifact-operations-modal.tsx` | MODIFY props, state; REFACTOR to use base | 1, 2, 3 |
| `web/lib/sync-utils.ts` | ADD shared validation util (if extracted) | 1 |
| `web/components/sync-status/comparison-selector.tsx` | MODIFY enablement logic | 2 |
| `web/components/shared/BaseArtifactModal.tsx` | ADD new component | 3 |
| `web/__tests__/sync-utils.test.ts` | ADD unit tests | 5 |
| `web/__tests__/sync-modal-integration.test.tsx` | ADD integration tests | 5 |
| `web/CLAUDE.md` | UPDATE modal patterns | 5 |
| `.claude/context/api-endpoint-mapping.md` | UPDATE sync/diff endpoints | 5 |

## Risk Mitigation

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Breaking /manage modal during refactor | HIGH | Medium | Phase 3 refactor is additive; verify all tabs after each task |
| Cache invalidation bugs from new mutations | HIGH | Medium | Audit against invalidation graph; verify with TanStack Query DevTools |
| ProjectSelectorForDiff not reusable in /manage | MEDIUM | Low | Component already accepts generic `onProjectSelected` callback |
| Entity type confusion during implementation | MEDIUM | Low | All new code uses `Artifact` type; existing `Entity` refs untouched |
| BaseArtifactModal abstraction doesn't fit both modals | MEDIUM | Medium | TASK-3.1 analysis confirms extraction targets before coding |

## Subagent Assignment Summary

| Agent | Model | Tasks | Rationale |
|-------|-------|-------|-----------|
| ui-engineer-enhanced | Opus | TASK-1.1 through 1.4, 2.1 through 2.5, 3.2 through 3.4, 4.1 through 4.4, 5.1, 5.2 | Complex cross-cutting React/TypeScript changes requiring component design judgment |
| codebase-explorer | Haiku | TASK-3.1 | Mechanical pattern comparison between two files |
| documentation-writer | Haiku | TASK-5.3, TASK-5.4 | Template-based documentation updates |

---

## Quick Reference: Orchestration Commands

### Phase 1 Execution

```text
# TASK-1.1 + TASK-1.3 can run in parallel (both modify different files)
Task("ui-engineer-enhanced", "
  TASK-1.1: Update hasValidUpstreamSource() in sync-status-tab.tsx (lines 98-104).
  Change signature from (source: string) to (entity: Artifact).
  Add checks: entity.origin === 'github' AND entity.upstream?.tracking_enabled.
  Keep existing source URL validation as secondary check.
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx

  TASK-1.3: Remove duplicate hasValidUpstreamSource() from artifact-operations-modal.tsx (lines 435-441).
  Import from sync-status-tab or extract to web/lib/sync-utils.ts.
  File: skillmeat/web/components/manage/artifact-operations-modal.tsx
")

# TASK-1.2 (depends on TASK-1.1)
Task("ui-engineer-enhanced", "
  TASK-1.2: Update upstream-diff query enablement in sync-status-tab.tsx (lines 238-239).
  Change hasValidUpstreamSource(entity.source) to hasValidUpstreamSource(entity).
  Add retry: false to query options.
  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
")
```

### Phase 2 Execution

```text
# TASK-2.1 through 2.3 are sequential
Task("ui-engineer-enhanced", "
  TASK-2.1: Add selectedProjectForDiff state to ArtifactOperationsModal.
  Similar to UnifiedEntityModal line 619-622. Derive initial value from artifact.deployments.
  Auto-detect when exactly one deployment exists.

  TASK-2.2: Import ProjectSelectorForDiff from web/components/entity/project-selector-for-diff.tsx.
  Render in sync tab area when in collection mode. Pass onProjectSelected callback.

  TASK-2.3: Pass projectPath={selectedProjectForDiff} to SyncStatusTab at lines 1185-1191.
  Keep mode='collection'.

  File: skillmeat/web/components/manage/artifact-operations-modal.tsx
")

# TASK-2.4 (can run after 2.3)
Task("ui-engineer-enhanced", "
  TASK-2.4: Verify ComparisonSelector enablement in comparison-selector.tsx.
  hasProject should be true when projectPath is available.
  All three scopes should enable when both source and project are available.
  File: skillmeat/web/components/sync-status/comparison-selector.tsx
")
```

### Phase 3 Execution

```text
# TASK-3.1 (can start during Phase 1)
Task("codebase-explorer", "
  TASK-3.1: Compare ArtifactOperationsModal (1411 lines) and UnifiedEntityModal (2566 lines).
  Identify shared patterns: header, tab bar, modal container, lifecycle provider, close handling.
  Document extraction targets with line references.
  Files: skillmeat/web/components/manage/artifact-operations-modal.tsx
         skillmeat/web/components/entity/unified-entity-modal.tsx
", model="haiku")

# TASK-3.2 + TASK-3.3 (sequential, depend on 3.1)
Task("ui-engineer-enhanced", "
  TASK-3.2: Create BaseArtifactModal component.
  File: skillmeat/web/components/shared/BaseArtifactModal.tsx
  Props: artifact, open, onClose, initialTab, mode, projectPath?, tabs (config), children (render).
  Encapsulate modal container, header, tab navigation, lifecycle provider wrapping.
  Use composition pattern for tab content.

  TASK-3.3: Refactor ArtifactOperationsModal to compose from BaseArtifactModal.
  Keep custom tab content. Target: reduce from 1411 to 600-800 lines.
  File: skillmeat/web/components/manage/artifact-operations-modal.tsx
")
```

### Phase 4 Execution

```text
# TASK-4.1, 4.2, 4.3 can run in parallel (different line ranges in same file)
# OR batch into single task for safety since same file
Task("ui-engineer-enhanced", "
  TASK-4.1: Implement keepLocalMutation (lines 357-369). Replace Promise.resolve() with
  drift banner dismissal via local state. No API call. Invalidate drift query state.

  TASK-4.2: Implement batch actions (lines 403-406). Replace toast with
  POST /context-sync/push (entity IDs) for push, POST /context-sync/pull for pull.
  Invalidate: ['context-sync-status'], ['artifact-files'], ['context-entities'], ['deployments'].

  TASK-4.3: Implement push-to-collection (lines 483, 519). Replace 'Coming Soon' toast with
  POST /context-sync/pull call. Requires projectPath.
  Invalidate: ['context-sync-status'], ['artifact-files'], ['context-entities'], ['deployments'].

  File: skillmeat/web/components/sync-status/sync-status-tab.tsx
")
```

### Phase 5 Execution

```text
# TASK-5.1 + TASK-5.2 in parallel (different test files)
Task("ui-engineer-enhanced", "
  TASK-5.1: Unit tests for hasValidUpstreamSource().
  File: skillmeat/web/__tests__/sync-utils.test.ts
  Cases: github+tracking (true), github-no-tracking (false), marketplace (false),
  local (false), null origin (false), null upstream (false).
")

Task("ui-engineer-enhanced", "
  TASK-5.2: Integration tests for modal sync workflows.
  File: skillmeat/web/__tests__/sync-modal-integration.test.tsx
  Test /manage modal upstream diff enablement, project diff enablement.
  Test /projects modal regression. Mock API responses.
")

# TASK-5.3 + TASK-5.4 in parallel (different doc files)
Task("documentation-writer", "
  TASK-5.3: Update skillmeat/web/CLAUDE.md with BaseArtifactModal composition pattern,
  sync tab data flow, hasValidUpstreamSource() validation logic.
", model="haiku")

Task("documentation-writer", "
  TASK-5.4: Update .claude/context/api-endpoint-mapping.md with sync/diff endpoints,
  required params, and cache invalidation keys.
", model="haiku")
```

### Post-Implementation

```bash
# Verify no TypeScript errors
cd /Users/miethe/dev/homelab/development/skillmeat/skillmeat/web && pnpm tsc --noEmit

# Run tests
cd /Users/miethe/dev/homelab/development/skillmeat/skillmeat/web && pnpm test

# Verify no console errors (manual)
# Open /manage, click marketplace artifact, check Sync tab - zero 400s
# Open /manage, click GitHub artifact with tracking, check Sync tab - diff loads
# Open /projects/{id}, click artifact, check Sync tab - no regressions
```

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-02-04
