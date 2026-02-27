---
title: 'Similar Artifacts — Phase 3–4: Marketplace Tab + Similarity Badges & Settings'
schema_version: 2
doc_type: phase_plan
status: inferred_complete
created: 2026-02-25
updated: 2026-02-25
feature_slug: similar-artifacts
feature_version: v1
phase: 3
phase_title: Marketplace Tab + Similarity Badges & Settings
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similar-artifacts-v1.md
entry_criteria:
- 'Phase 1 complete: GET /api/v1/artifacts/{id}/similar endpoint merged'
- 'Phase 2 complete: SimilarArtifactsTab component stable and tested'
exit_criteria:
- All Phase 3 and Phase 4 tasks marked completed
- SimilarArtifactsTab visible in marketplace artifact detail panel (Phase 3)
- SimilarityBadge renders on SourceCard with correct color and aria-label (Phase 4)
- Threshold settings persist and badge updates immediately after change (Phase 4)
- Marketplace badge E2E test passes
- task-completion-validator sign-off
priority: medium
risk_level: medium
category: product-planning
tags:
- phase-plan
- frontend
- marketplace
- badges
- settings
- similar-artifacts
---
# Phase 3–4: Marketplace Tab + Similarity Badges & Settings

**Parent Plan**: [similar-artifacts-v1.md](../similar-artifacts-v1.md)
**Phases Covered**: Phase 3 (Similar Artifacts Tab — Marketplace) + Phase 4 (Marketplace Similarity Badges)
**Combined Effort**: 12 story points
**Estimated Duration**: 3–5 days
**Assigned Primary Subagents**: `ui-engineer-enhanced`, `frontend-developer`, `python-backend-engineer`

---

## Entry Criteria

- Phase 1 complete: `GET /api/v1/artifacts/{id}/similar` merged and integrated tests green.
- Phase 2 complete: `SimilarArtifactsTab` component tested and merged.
- `useSimilarArtifacts` hook and `SimilaritySource` types available in `skillmeat/web/hooks/similarity.ts`.

---

## Phase 3: Similar Artifacts Tab — Marketplace

### Overview

Phase 3 is a minimal lift. The `SimilarArtifactsTab` built in Phase 2 is configured with `source='collection'` and inserted into the marketplace artifact detail panel. This allows users browsing a marketplace artifact to immediately see which artifacts in their own collection are similar.

**Duration**: 1 day
**Dependencies**: Phase 2 `SimilarArtifactsTab` stable and merged.

### Parallelization Opportunities

- Phase 3 and Phase 4 can run in parallel: Phase 3 is frontend-only (reusing existing component), while Phase 4 starts with badge infrastructure.
- A single `ui-engineer-enhanced` can handle Phase 3 independently of Phase 4 badge work.

### Task Table — Phase 3

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---|---|---|---|---|---|---|
| SA-P3-001 | Identify marketplace artifact detail panel | Locate the marketplace source artifact detail panel/view. Confirm where tabs are registered (similar to `BASE_TABS` pattern in `ArtifactDetailsModal`). If no tab system exists, identify the appropriate slot for the "Similar" section. | File path and tab registration point identified; no code written yet. | 0.5 pt | `ui-engineer-enhanced` | Phase 2 complete |
| SA-P3-002 | Add Similar tab to marketplace detail panel | Register "Similar" tab entry in the marketplace artifact detail panel. Pass the marketplace artifact's ID to `SimilarArtifactsTab` with `source='collection'` and `minScore=0.3`. Use `GitCompare` icon to match collection modal. | "Similar" tab visible in marketplace artifact detail; renders collection results; empty state shows when no match; no badge (threshold handled in Phase 4). | 1.5 pts | `ui-engineer-enhanced` | SA-P3-001 |
| SA-P3-003 | E2E test — marketplace Similar tab | Playwright E2E: navigate to Marketplace Sources page → open a source artifact detail → click "Similar" tab → verify component renders (at minimum: loading state transitions to result or empty state). Requires a marketplace artifact in test fixtures that has a known collection counterpart. | E2E test passes in CI; tab is reachable by keyboard navigation. | 1 pt | `frontend-developer` | SA-P3-002 |

**Phase 3 Story Points**: 3 pts (aligns with PRD SA-006 = 2 pts + E2E = 1 pt)

### Phase 3 Quality Gates

- [ ] "Similar" tab visible in marketplace artifact detail panel.
- [ ] Tab correctly passes `source='collection'` to `useSimilarArtifacts`.
- [ ] Empty state, loading, and result states render correctly (inherited from Phase 2).
- [ ] E2E test passes.
- [ ] `task-completion-validator` sign-off.

---

## Phase 4: Marketplace Similarity Badges + Settings Sub-tab

### Overview

Phase 4 adds color-coded similarity badges to marketplace `SourceCard` components and a Settings > Appearance > Similarity sub-tab for threshold and color configuration. Badge fetches are lazy-loaded via IntersectionObserver to avoid N+1 API calls. Threshold values are persisted via the existing settings/preferences API and consumed via a new `useSimilaritySettings()` hook.

**Duration**: 2–3 days
**Dependencies**: Phase 1 API endpoint merged. Settings infrastructure (existing settings API) confirmed compatible with similarity threshold storage.

### Parallelization Opportunities

- **P4-A** (SimilaritySettings sub-tab + backend settings endpoint): `python-backend-engineer` can work on settings storage in parallel with frontend badge work.
- **P4-B** (SimilarityBadge component + IntersectionObserver): `ui-engineer-enhanced` works in parallel with P4-A.
- **P4-C** (SourceCard integration): blocked until P4-A settings hook and P4-B badge component are ready.
- **P4-D** (Batch fetching optimization): can be done after P4-C as an enhancement; fall back to per-card query if batching is complex.

### Task Table — Phase 4

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---|---|---|---|---|---|---|
| SA-P4-001 | Similarity settings storage | Determine storage mechanism for similarity thresholds (high/partial/low/floor values). If existing user settings/preferences API supports arbitrary key-value config, add `similarity_thresholds` settings entry. Otherwise, extend settings API to accept threshold config. Persist defaults: high=0.80, partial=0.55, low=0.35, floor=0.20. | Threshold values readable/writable via existing or extended settings API; defaults applied on first access; no new DB migration required if using key-value settings store. | 1 pt | `python-backend-engineer` | Phase 1 complete |
| SA-P4-002 | useSimilaritySettings hook | Create `useSimilaritySettings()` hook in `skillmeat/web/hooks/similarity.ts`. Returns `{ thresholds, colors, isLoading }`. Reads from settings API. `staleTime: 5 * 60 * 1000`. Provides `updateThresholds(values)` mutation. | Hook returns correct threshold values from API; mutation updates settings and invalidates query cache; used by both badge and settings components. | 1 pt | `frontend-developer` | SA-P4-001 |
| SA-P4-003 | SimilaritySettings sub-tab component | Create `skillmeat/web/app/settings/components/similarity-settings.tsx`. Adds "Similarity" sub-tab to Settings > Appearance alongside existing "Colors" and "Icons" sub-tabs. UI: four threshold sliders (high/partial/low/floor) with labeled values; three color pickers (high/partial/low) using existing `useCustomColors()` hook; inline help text explaining each threshold; save button with optimistic update. | Sub-tab renders in Settings > Appearance; threshold changes persist; color picker uses existing custom color system; inline help text present for each slider; keyboard accessible. | 3 pts | `ui-engineer-enhanced` | SA-P4-002 |
| SA-P4-004 | Register Similarity sub-tab in Settings page | Update `skillmeat/web/app/settings/page.tsx` to include the new "Similarity" sub-tab in the Appearance tab's sub-tab list alongside Colors and Icons. | "Similarity" sub-tab visible in Settings > Appearance; selecting it renders `SimilaritySettings` component; other existing sub-tabs unaffected. | 0.5 pt | `frontend-developer` | SA-P4-003 |
| SA-P4-005 | SimilarityBadge component | Create `skillmeat/web/components/marketplace/similarity-badge.tsx`. Props: `score: number`, `thresholds: SimilarityThresholds`, `colors: SimilarityColors`. Renders a color-coded badge: green="High Match", yellow="Partial Match", orange="Low Match", hidden if below floor threshold. Includes `aria-label` with score percentage and level (e.g., `aria-label="High similarity: 87%"`). Reuses existing `StatusBadge` pattern from `source-card.tsx` for consistent styling. | Badge renders correct color and label for each threshold range; no badge rendered when score < floor; `aria-label` correct; WCAG 2.1 AA contrast on all badge colors; score percentage displayed on badge. | 2 pts | `ui-engineer-enhanced` | SA-P4-002 |
| SA-P4-006 | SourceCard — badge integration with lazy loading | Integrate `SimilarityBadge` into `skillmeat/web/components/marketplace/source-card.tsx`. Use IntersectionObserver (or React Intersection Observer library) to trigger `useSimilarArtifacts` call only when card enters viewport. Pass highest-scoring result's score to `SimilarityBadge`. If no result meets floor threshold, render nothing. | Badge appears on card within ~200 ms of viewport entry; no badge flicker on scroll; no badge when score < floor; single batched query per viewport batch (not per card) — see SA-P4-007 for batch optimization. | 2 pts | `ui-engineer-enhanced` | SA-P4-005 |
| SA-P4-007 | Badge batch query optimization | Batch the `useSimilarArtifacts` calls from visible SourceCards into a single API request per IntersectionObserver batch. Collect artifact IDs from cards entering viewport within a 200 ms debounce window; issue one batched request. Note: if the existing API does not support batch artifact IDs in one call, this task implements client-side debounce queuing with deduplication instead. | Network tab shows at most one API request per viewport batch scroll event (not N requests for N cards); network behavior documented in component comment. | 1.5 pts | `frontend-developer` | SA-P4-006 |
| SA-P4-008 | E2E test — marketplace badge | Playwright E2E: navigate to Marketplace Sources page with a known matching artifact pair in fixtures → verify `SimilarityBadge` renders on the matching source card with correct color and `aria-label`; verify no badge on a non-matching card. | E2E test passes; badge color matches threshold level; no badge on non-matching card; aria-label text correct. | 1 pt | `frontend-developer` | SA-P4-006 |

**Phase 4 Story Points**: ~12 pts (aligns with PRD SA-007=3 pts, SA-008=2 pts, SA-009=3 pts + settings storage, hooks, E2E)

### Phase 4 Quality Gates

- [ ] Threshold settings persist across page reload.
- [ ] `SimilarityBadge` renders correct color and label for each threshold range.
- [ ] No badge rendered when score < floor threshold.
- [ ] `aria-label` includes score percentage and match level.
- [ ] WCAG 2.1 AA contrast verified on all badge color variants.
- [ ] Badge lazy-loads via IntersectionObserver (not on page render).
- [ ] No N+1 per-card API calls; viewport batch strategy in place.
- [ ] Settings > Appearance > Similarity sub-tab renders and persists changes.
- [ ] E2E badge test passes.
- [ ] `task-completion-validator` sign-off.

---

## Key Files

| File | Role | Change Type |
|---|---|---|
| `skillmeat/web/hooks/similarity.ts` | React Query hooks | Add `useSimilaritySettings()` |
| `skillmeat/web/types/similarity.ts` | TS types | Add `SimilarityThresholds`, `SimilarityColors` |
| `skillmeat/web/components/marketplace/similarity-badge.tsx` | Badge component | New file |
| `skillmeat/web/components/marketplace/source-card.tsx` | Source card | Add badge + lazy loading |
| `skillmeat/web/app/settings/components/similarity-settings.tsx` | Settings sub-tab | New file |
| `skillmeat/web/app/settings/page.tsx` | Settings page | Register Similarity sub-tab |
| Marketplace artifact detail panel | Tab host | Add Similar tab (Phase 3) |

---

## Risk Notes for This Phase

**N+1 badge fetches (High likelihood)**: The IntersectionObserver + debounce batching in SA-P4-007 is the critical risk. If the existing `GET /api/v1/artifacts/{id}/similar` endpoint does not support batch artifact IDs, client-side deduplication and debounce queuing must be implemented. A per-card query with 200 ms debounce is an acceptable fallback that keeps per-viewport-scroll requests bounded.

**Color contrast for badge colors**: The custom color system allows arbitrary user colors. The `SimilaritySettings` sub-tab should warn users if their chosen color fails WCAG AA contrast against the card background. This can be a non-blocking warning rather than a hard validation error.

---

**Back to parent plan**: [similar-artifacts-v1.md](../similar-artifacts-v1.md)
**Previous phase file**: [phase-1-2-backend-and-collection-tab.md](./phase-1-2-backend-and-collection-tab.md)
**Next phase file**: [phase-5-6-consolidation-and-cli.md](./phase-5-6-consolidation-and-cli.md)
