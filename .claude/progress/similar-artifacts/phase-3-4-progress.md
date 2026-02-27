---
type: progress
schema_version: 2
doc_type: progress
prd: similar-artifacts
feature_slug: similar-artifacts
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similar-artifacts-v1.md
phase: 3
title: Marketplace Tab + Similarity Badges & Settings
status: completed
started: '2026-02-25'
completed: null
commit_refs: []
pr_refs: []
overall_progress: 0
completion_estimate: on-track
total_tasks: 11
completed_tasks: 11
in_progress_tasks: 0
blocked_tasks: 0
at_risk_tasks: 0
owners:
- ui-engineer-enhanced
- python-backend-engineer
contributors:
- frontend-developer
tasks:
- id: SA-P3-001
  description: Identify marketplace artifact detail panel
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies: []
  estimated_effort: 0.5pt
  priority: high
- id: SA-P3-002
  description: Add Similar tab to marketplace detail panel
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P3-001
  estimated_effort: 1.5pt
  priority: high
- id: SA-P3-003
  description: E2E test — marketplace Similar tab
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P3-002
  estimated_effort: 1pt
  priority: high
- id: SA-P4-001
  description: Similarity settings storage (backend)
  status: completed
  assigned_to:
  - python-backend-engineer
  dependencies: []
  estimated_effort: 1pt
  priority: high
- id: SA-P4-002
  description: useSimilaritySettings hook
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P4-001
  estimated_effort: 1pt
  priority: high
- id: SA-P4-003
  description: SimilaritySettings sub-tab component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P4-002
  estimated_effort: 3pt
  priority: high
- id: SA-P4-004
  description: Register Similarity sub-tab in Settings page
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P4-003
  estimated_effort: 0.5pt
  priority: high
- id: SA-P4-005
  description: SimilarityBadge component
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P4-002
  estimated_effort: 2pt
  priority: high
- id: SA-P4-006
  description: SourceCard — badge integration with lazy loading
  status: completed
  assigned_to:
  - ui-engineer-enhanced
  dependencies:
  - SA-P4-005
  estimated_effort: 2pt
  priority: high
- id: SA-P4-007
  description: Badge batch query optimization
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P4-006
  estimated_effort: 1.5pt
  priority: medium
- id: SA-P4-008
  description: E2E test — marketplace badge
  status: completed
  assigned_to:
  - frontend-developer
  dependencies:
  - SA-P4-006
  estimated_effort: 1pt
  priority: high
parallelization:
  batch_1:
  - SA-P3-001
  - SA-P4-001
  batch_2:
  - SA-P3-002
  - SA-P4-002
  batch_3:
  - SA-P3-003
  - SA-P4-003
  - SA-P4-005
  batch_4:
  - SA-P4-004
  - SA-P4-006
  batch_5:
  - SA-P4-007
  - SA-P4-008
  critical_path:
  - SA-P4-001
  - SA-P4-002
  - SA-P4-005
  - SA-P4-006
  - SA-P4-007
  estimated_total_time: 3-5 days
blockers: []
success_criteria:
- id: SC-1
  description: Similar tab visible in marketplace artifact detail panel
  status: pending
- id: SC-2
  description: SimilarityBadge renders with correct color and aria-label for each
    threshold range
  status: pending
- id: SC-3
  description: No badge rendered when score below floor threshold
  status: pending
- id: SC-4
  description: Threshold settings persist across page reload
  status: pending
- id: SC-5
  description: WCAG 2.1 AA contrast verified on all badge color variants
  status: pending
- id: SC-6
  description: Badge lazy-loads via IntersectionObserver (not on page render)
  status: pending
- id: SC-7
  description: No N+1 per-card API calls; viewport batch strategy in place
  status: pending
- id: SC-8
  description: Settings > Appearance > Similarity sub-tab renders and persists changes
  status: pending
- id: SC-9
  description: E2E test passes for marketplace Similar tab
  status: pending
- id: SC-10
  description: E2E test passes for marketplace badge
  status: pending
- id: SC-11
  description: task-completion-validator sign-off
  status: pending
files_modified:
- skillmeat/web/hooks/similarity.ts
- skillmeat/web/types/similarity.ts
- skillmeat/web/components/marketplace/similarity-badge.tsx
- skillmeat/web/components/marketplace/source-card.tsx
- skillmeat/web/app/settings/components/similarity-settings.tsx
- skillmeat/web/app/settings/page.tsx
- skillmeat/web/__tests__/marketplace/similarity-badge.test.tsx
- skillmeat/web/__tests__/e2e/marketplace-similar-tab.e2e.ts
- skillmeat/web/__tests__/e2e/marketplace-badge.e2e.ts
progress: 100
updated: '2026-02-25'
---

# similar-artifacts - Phase 3-4: Marketplace Tab + Similarity Badges & Settings

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate task details in markdown.

Use CLI to update progress:

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py \
  -f .claude/progress/similar-artifacts/phase-3-4-progress.md \
  -t SA-P3-001 -s in_progress
```

Batch update multiple tasks:

```bash
python .claude/skills/artifact-tracking/scripts/update-batch.py \
  -f .claude/progress/similar-artifacts/phase-3-4-progress.md \
  --updates "SA-P3-001:in_progress,SA-P3-002:pending,SA-P4-001:in_progress"
```

---

## Objective

Phase 3-4 builds marketplace-specific similarity features on top of the collection-focused work from Phase 1-2. Phase 3 reuses the `SimilarArtifactsTab` in the marketplace artifact detail panel so users can discover similar items in their collection while browsing marketplace sources. Phase 4 adds color-coded similarity badges to marketplace source cards with a threshold/color configuration sub-tab in Settings.

---

## Entry Criteria

- Phase 1 complete: `GET /api/v1/artifacts/{id}/similar` endpoint merged and integration tests green.
- Phase 2 complete: `SimilarArtifactsTab` component tested and merged to main.
- `useSimilarArtifacts` hook and `SimilaritySource` types available in `skillmeat/web/hooks/similarity.ts`.

---

## Phase 3 Overview

### Phase 3: Similar Artifacts Tab — Marketplace (3 pts, ~1 day)

**Objective**: Reuse the `SimilarArtifactsTab` built in Phase 2 by registering it in the marketplace artifact detail panel. This is a minimal lift that exposes the existing component in a new context.

#### Task Breakdown

**SA-P3-001** (0.5 pt): Identify the marketplace artifact detail panel location and tab registration point. Confirm existing tab system compatibility or identify the appropriate integration slot.

**SA-P3-002** (1.5 pts): Register "Similar" tab entry in the marketplace artifact detail panel. Pass the marketplace artifact's ID to `SimilarArtifactsTab` with `source='collection'` and `minScore=0.3`. Use `GitCompare` icon to match collection modal aesthetic.

**SA-P3-003** (1 pt): Playwright E2E test. Navigate to Marketplace Sources → open a source artifact detail → click "Similar" tab → verify component renders (loading state transitions to result or empty state). Requires test fixtures with a known collection/marketplace artifact pair.

#### Phase 3 Quality Gates

- "Similar" tab visible in marketplace artifact detail panel.
- Tab correctly passes `source='collection'` to `useSimilarArtifacts`.
- Empty state, loading, and result states render correctly (inherited from Phase 2).
- E2E test passes.
- `task-completion-validator` sign-off.

---

## Phase 4 Overview

### Phase 4: Marketplace Similarity Badges + Settings Sub-tab (8 pts, ~2-3 days)

**Objective**: Add color-coded similarity badges to marketplace `SourceCard` components and a Settings > Appearance > Similarity sub-tab for threshold and color configuration. Badge fetches are lazy-loaded via IntersectionObserver to avoid N+1 API calls. Threshold values persist via the settings API.

#### Task Breakdown

**SA-P4-001** (1 pt): Similarity settings storage. Add `similarity_thresholds` settings entry to the existing settings API with defaults: high=0.80, partial=0.55, low=0.35, floor=0.20. No new DB migration if using key-value settings store.

**SA-P4-002** (1 pt): Create `useSimilaritySettings()` hook in `skillmeat/web/hooks/similarity.ts`. Returns `{ thresholds, colors, isLoading }` from settings API with `staleTime: 5 * 60 * 1000`. Provides `updateThresholds(values)` mutation.

**SA-P4-003** (3 pts): Create `skillmeat/web/app/settings/components/similarity-settings.tsx`. Adds "Similarity" sub-tab to Settings > Appearance. UI: four threshold sliders (high/partial/low/floor) with labeled values; three color pickers (high/partial/low); inline help text; save button with optimistic update.

**SA-P4-004** (0.5 pt): Register Similarity sub-tab in `skillmeat/web/app/settings/page.tsx`. Include in Appearance tab's sub-tab list alongside Colors and Icons.

**SA-P4-005** (2 pts): Create `skillmeat/web/components/marketplace/similarity-badge.tsx`. Props: `score: number`, `thresholds: SimilarityThresholds`, `colors: SimilarityColors`. Renders color-coded badge (green=High, yellow=Partial, orange=Low, hidden if below floor). Includes `aria-label` with score percentage and level.

**SA-P4-006** (2 pts): Integrate `SimilarityBadge` into `skillmeat/web/components/marketplace/source-card.tsx`. Use IntersectionObserver to trigger `useSimilarArtifacts` call only when card enters viewport. Pass highest-scoring result's score to badge. No badge if score < floor threshold.

**SA-P4-007** (1.5 pts): Batch the `useSimilarArtifacts` calls from visible SourceCards into a single API request per IntersectionObserver batch using 200 ms debounce. Fallback: client-side deduplication and debounce queuing if API doesn't support batch artifact IDs.

**SA-P4-008** (1 pt): Playwright E2E test. Navigate to Marketplace Sources with known matching artifact pair in fixtures → verify `SimilarityBadge` renders on matching source card with correct color and `aria-label`; verify no badge on non-matching card.

#### Phase 4 Quality Gates

- Threshold settings persist across page reload.
- `SimilarityBadge` renders correct color and label for each threshold range.
- No badge rendered when score < floor threshold.
- `aria-label` includes score percentage and match level.
- WCAG 2.1 AA contrast verified on all badge color variants.
- Badge lazy-loads via IntersectionObserver (not on page render).
- No N+1 per-card API calls; viewport batch strategy in place.
- Settings > Appearance > Similarity sub-tab renders and persists changes.
- E2E badge test passes.
- `task-completion-validator` sign-off.

---

## Key Risks & Mitigations

### Risk: N+1 Badge Fetches (High likelihood)

**Mitigation**: IntersectionObserver + debounce batching in SA-P4-007. If the existing `GET /api/v1/artifacts/{id}/similar` endpoint does not support batch artifact IDs, implement client-side deduplication and debounce queuing. A per-card query with 200 ms debounce is an acceptable fallback that keeps per-viewport-scroll requests bounded.

### Risk: Badge Color Contrast

**Mitigation**: The `SimilaritySettings` sub-tab should warn users if their chosen custom color fails WCAG AA contrast against the card background. Non-blocking warning rather than hard error.

---

## Implementation Notes

### Architectural Decisions

- **Component Reuse**: Phase 3 leverages the Phase 2 `SimilarArtifactsTab` by configuring `source='collection'` instead of duplicating logic.
- **Settings Integration**: Threshold configuration piggybacks on the existing settings/preferences API to avoid adding new endpoints.
- **Lazy Badge Loading**: IntersectionObserver prevents N+1 requests on page render; badges only fetch when cards enter viewport.
- **Icon Consistency**: Phase 3 uses `GitCompare` icon (from Phase 2) to maintain visual consistency across Similar tabs.

### Patterns and Best Practices

- **React Query Hooks**: `useSimilaritySettings()` follows the same pattern as existing hooks (staleTime, gcTime, invalidation on mutation).
- **Accessibility**: Badges include `aria-label` with percentage and match level. Similar tab supports keyboard navigation (inherited from Phase 2).
- **StatusBadge Reuse**: `SimilarityBadge` reuses existing `StatusBadge` pattern from `source-card.tsx` for consistent styling and spacing.
- **Settings Sub-tabs**: Similarity sub-tab follows the existing pattern in Settings > Appearance (Colors/Icons).

### Known Gotchas

- **Marketplace Detail Panel**: The marketplace artifact detail panel may use a different tab registration system than `ArtifactDetailsModal` (which uses `BASE_TABS`). SA-P3-001 must confirm the integration point before proceeding.
- **Color Picker Integration**: The `SimilaritySettings` component should reuse the existing `useCustomColors()` hook if available, to maintain consistency with color management across the app.
- **Badge Position**: Consider placement of badge on `SourceCard` — ensure it doesn't obscure critical information and remains visible at all card sizes.
- **Empty State Handling**: If a marketplace artifact has no similar items in the collection, the Similar tab should display a clear empty state message (inherited from Phase 2).

### Development Setup

1. Ensure Phase 1 and Phase 2 are merged to main.
2. Verify API endpoint `GET /api/v1/artifacts/{id}/similar` is live and responding.
3. Confirm test fixtures include a marketplace artifact and a collection artifact pair with known similarity.
4. Settings API endpoint for threshold persistence must be confirmed compatible (SA-P4-001).

---

## Orchestration Quick Reference

Execute phases 3-4 using the following batch strategy. Each batch represents a set of tasks that can run in parallel:

### Batch 1: Foundation (Parallel)

```bash
Task("ui-engineer-enhanced", "
  Phase 3-4: SA-P3-001 — Identify marketplace artifact detail panel.

  Identify the file path and tab registration pattern for the marketplace artifact detail panel.
  Look for equivalent patterns to BASE_TABS in ArtifactDetailsModal.
  Confirm the integration point for registering a new 'Similar' tab.

  File path for tab host: [PATH_TO_FIND]
  Tab registration pattern: [PATTERN_TO_FIND]

  Dependencies: Phase 2 complete
  Effort: 0.5pt
  Blocking: SA-P3-002
")

Task("python-backend-engineer", "
  Phase 4: SA-P4-001 — Similarity settings storage.

  Add similarity_thresholds to the existing settings API. Use the key-value settings store
  if available; no new DB migration needed.

  Defaults: high=0.80, partial=0.55, low=0.35, floor=0.20

  Verify the settings API can persist and retrieve threshold values.
  Write integration test: set threshold → fetch → verify value persisted.

  Files:
  - Identify settings API endpoint (likely in skillmeat/api/routers/settings.py or similar)
  - Add threshold defaults to settings initialization

  Dependencies: Phase 1 complete
  Effort: 1pt
  Blocking: SA-P4-002
")
```

### Batch 2: Frontend Hooks + Marketplace Tab (Parallel)

```bash
Task("ui-engineer-enhanced", "
  Phase 3-4: SA-P3-002 — Add Similar tab to marketplace detail panel.

  Register 'Similar' tab in the marketplace artifact detail panel.
  Pass the marketplace artifact's ID to SimilarArtifactsTab with source='collection'.
  Use GitCompare icon to match Phase 2 aesthetic.
  Set minScore=0.3.

  File: [PATH_FROM_SA-P3-001]
  Component: SimilarArtifactsTab (from Phase 2)

  Acceptance: Tab visible, renders results/empty state correctly, keyboard accessible.

  Dependencies: SA-P3-001
  Effort: 1.5pt
  Blocking: SA-P3-003
")

Task("frontend-developer", "
  Phase 4: SA-P4-002 — useSimilaritySettings hook.

  Create useSimilaritySettings() hook in skillmeat/web/hooks/similarity.ts.

  Returns: { thresholds, colors, isLoading }
  API source: settings endpoint (from SA-P4-001)
  staleTime: 5 * 60 * 1000 (5 minutes)
  Provides updateThresholds(values) mutation

  Acceptance:
  - Hook reads correct threshold values from API
  - Mutation updates settings and invalidates cache
  - Used by both SimilaritySettings and SimilarityBadge

  Dependencies: SA-P4-001
  Effort: 1pt
  Blocking: SA-P4-003, SA-P4-005
")
```

### Batch 3: Settings Sub-tab + Badge Component (Parallel)

```bash
Task("ui-engineer-enhanced", "
  Phase 4: SA-P4-003 — SimilaritySettings sub-tab component.

  Create skillmeat/web/app/settings/components/similarity-settings.tsx

  Adds 'Similarity' sub-tab to Settings > Appearance (alongside Colors/Icons).

  UI components:
  - Four threshold sliders (high/partial/low/floor) with labeled values
  - Three color pickers (high/partial/low) using useCustomColors() hook
  - Inline help text for each threshold
  - Save button with optimistic update

  Acceptance:
  - Sub-tab renders in Settings > Appearance
  - Threshold changes persist
  - Color picker uses existing custom color system
  - Inline help text present
  - Keyboard accessible

  Dependencies: SA-P4-002
  Effort: 3pt
  Blocking: SA-P4-004
")

Task("ui-engineer-enhanced", "
  Phase 4: SA-P4-005 — SimilarityBadge component.

  Create skillmeat/web/components/marketplace/similarity-badge.tsx

  Props: score: number, thresholds: SimilarityThresholds, colors: SimilarityColors

  Renders color-coded badge:
  - Green: 'High Match' (score >= high threshold)
  - Yellow: 'Partial Match' (score >= partial threshold)
  - Orange: 'Low Match' (score >= low threshold)
  - Hidden if score < floor threshold

  aria-label format: 'High similarity: 87%' (includes level + percentage)

  Reuses StatusBadge pattern from source-card.tsx for consistent styling.

  Acceptance:
  - Badge renders correct color/label for each range
  - No badge when score < floor
  - aria-label correct
  - WCAG 2.1 AA contrast verified
  - Score percentage displayed on badge

  Dependencies: SA-P4-002
  Effort: 2pt
  Blocking: SA-P4-006
")

Task("frontend-developer", "
  Phase 3-4: SA-P3-003 — E2E test for marketplace Similar tab.

  Playwright E2E test: navigate to Marketplace Sources → open source artifact detail
  → click 'Similar' tab → verify component renders.

  Test path: skillmeat/web/__tests__/e2e/marketplace-similar-tab.e2e.ts

  Requires test fixtures with:
  - A marketplace artifact
  - A collection artifact known to be similar

  Acceptance:
  - E2E test passes in CI
  - Tab reachable by keyboard navigation
  - Loading state transitions to result or empty state

  Dependencies: SA-P3-002
  Effort: 1pt
  Status: Tests later in batch
")
```

### Batch 4: Card Integration + Sub-tab Registration (Parallel)

```bash
Task("frontend-developer", "
  Phase 4: SA-P4-004 — Register Similarity sub-tab in Settings page.

  Update skillmeat/web/app/settings/page.tsx

  Include 'Similarity' sub-tab in Appearance tab's sub-tab list
  Alongside existing 'Colors' and 'Icons' sub-tabs.

  Acceptance:
  - 'Similarity' sub-tab visible in Settings > Appearance
  - Selecting it renders SimilaritySettings component
  - Other existing sub-tabs unaffected

  Dependencies: SA-P4-003
  Effort: 0.5pt
  Blocking: None (but SA-P4-003 must be complete)
")

Task("ui-engineer-enhanced", "
  Phase 4: SA-P4-006 — SourceCard badge integration with lazy loading.

  Integrate SimilarityBadge into skillmeat/web/components/marketplace/source-card.tsx

  Use IntersectionObserver (or react-intersection-observer library) to trigger
  useSimilarArtifacts call only when card enters viewport.

  Pass highest-scoring result's score to SimilarityBadge.
  No badge if score < floor threshold.

  Acceptance:
  - Badge appears within ~200 ms of viewport entry
  - No badge flicker on scroll
  - No badge when score < floor
  - Single batched query per viewport batch (not per card) — SA-P4-007 handles optimization

  Dependencies: SA-P4-005
  Effort: 2pt
  Blocking: SA-P4-007, SA-P4-008
")
```

### Batch 5: Optimization + E2E Tests (Parallel)

```bash
Task("frontend-developer", "
  Phase 4: SA-P4-007 — Badge batch query optimization.

  Batch useSimilarArtifacts calls from visible SourceCards into a single API request
  per IntersectionObserver batch.

  Strategy:
  - Collect artifact IDs from cards entering viewport within 200 ms debounce window
  - Issue one batched request
  - If API doesn't support batch artifact IDs: implement client-side dedup + debounce queuing

  Acceptance:
  - Network tab shows at most one API request per viewport batch scroll (not N requests for N cards)
  - Network behavior documented in component comment

  Dependencies: SA-P4-006
  Effort: 1.5pt
  Blocking: SA-P4-008
")

Task("frontend-developer", "
  Phase 4: SA-P4-008 — E2E test for marketplace badge.

  Playwright E2E test: navigate to Marketplace Sources with known matching artifact pair
  in fixtures → verify SimilarityBadge renders on matching source card with correct color
  and aria-label → verify no badge on non-matching card.

  Test path: skillmeat/web/__tests__/e2e/marketplace-badge.e2e.ts

  Acceptance:
  - E2E test passes
  - Badge color matches threshold level
  - No badge on non-matching card
  - aria-label text correct

  Dependencies: SA-P4-006
  Effort: 1pt
")
```

---

## Completion Notes

To be filled in when phase is complete:

- What was built
- Key learnings
- Unexpected challenges
- Recommendations for next phase
