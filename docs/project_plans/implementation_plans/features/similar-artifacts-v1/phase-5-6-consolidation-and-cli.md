---
title: "Similar Artifacts \u2014 Phase 5\u20136: Collection Consolidation View + CLI\
  \ Integration"
schema_version: 2
doc_type: phase_plan
status: completed
created: 2026-02-25
updated: '2026-02-25'
feature_slug: similar-artifacts
feature_version: v1
phase: 5
phase_title: Collection Consolidation View + CLI Integration
prd_ref: docs/project_plans/PRDs/features/similar-artifacts-v1.md
plan_ref: docs/project_plans/implementation_plans/features/similar-artifacts-v1.md
entry_criteria:
- 'Phase 1 complete: SimilarityService available; DuplicatePair.ignored migration
  merged'
- 'Phase 1 repository work confirmed: DuplicatePair.ignored mark/unmark methods in
  place'
exit_criteria:
- All Phase 5 and Phase 6 tasks marked completed
- Consolidation page /collection/consolidate renders cluster list with pagination
- Merge, replace, and skip actions complete with auto-snapshot verified
- Ignored pairs hidden by default; un-ignore restores to list
- CLI skillmeat similar and skillmeat consolidate commands exit 0
- task-completion-validator sign-off
priority: medium
risk_level: medium
category: product-planning
tags:
- phase-plan
- frontend
- backend
- consolidation
- cli
- similar-artifacts
---
# Phase 5–6: Collection Consolidation View + CLI Integration

**Parent Plan**: [similar-artifacts-v1.md](../similar-artifacts-v1.md)
**Phases Covered**: Phase 5 (Collection Consolidation View) + Phase 6 (CLI Integration)
**Combined Effort**: 12 story points
**Estimated Duration**: 4–6 days
**Assigned Primary Subagents**: `python-backend-engineer`, `backend-architect`, `ui-engineer-enhanced`, `frontend-developer`

---

## Entry Criteria

- Phase 1 complete: `SimilarityService` available; `DuplicatePair.ignored` column migrated.
- Repository layer has `mark_ignored(pair_id)` and `unmark_ignored(pair_id)` methods.
- `VersionMergeService` confirmed accessible for auto-snapshot and merge actions.

---

## Phase 5: Collection Consolidation View

### Overview

Phase 5 delivers the dedicated Collection Consolidation page at `/collection/consolidate`. It fetches similar artifact clusters from a new API endpoint, displays them in a paginated list, and allows users to perform merge/replace/skip actions — each gated by an auto-snapshot step using the existing `VersionMergeService`. Ignored pairs are tracked via the `DuplicatePair.ignored` column added in Phase 1.

**Duration**: 3–4 days
**Dependencies**: Phase 1 service layer and DB migration.

### Parallelization Opportunities

- **P5-A** (clusters API endpoint + service method): `python-backend-engineer` + `backend-architect` start immediately after Phase 1.
- **P5-B** (consolidation page + components): `ui-engineer-enhanced` + `frontend-developer` can start once P5-A API contract is agreed (can mock the endpoint).
- **P5-C** (merge/replace/skip actions): blocked until both P5-A and P5-B are stable.
- **P5-D** (ignored pairs management): `python-backend-engineer` adds repository methods; frontend wires after P5-C.
- Phase 6 (CLI) can proceed in parallel with Phase 5 frontend work since CLI calls `SimilarityService` directly without UI dependency.

### Task Table — Phase 5

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---|---|---|---|---|---|---|
| SA-P5-001 | SimilarityService — cluster grouping | Extend `SimilarityService` with `get_consolidation_clusters(min_score=0.5, limit=20, cursor=None) -> list[SimilarityCluster]`. Groups `DuplicatePair` records and new `find_similar()` results into clusters. Each cluster: `{ artifacts: list[Artifact], max_score: float, artifact_type: str, pair_count: int }`. Excludes ignored pairs. Sorts by max_score descending. | Returns paginated cluster list; ignored pairs excluded; cursor pagination works; unit tests for cluster grouping logic. | 2 pts | `backend-architect`, `python-backend-engineer` | Phase 1 SA-P1-004 |
| SA-P5-002 | Repository — ignored pair methods | Add `mark_pair_ignored(pair_id: int, db)` and `unmark_pair_ignored(pair_id: int, db)` methods to the `DuplicatePair` repository in `skillmeat/cache/repositories.py`. Used by consolidation skip/un-ignore actions. | Methods update `DuplicatePair.ignored` correctly; unit tests confirm mark/unmark round-trip. | 1 pt | `python-backend-engineer` | Phase 1 SA-P1-001 |
| SA-P5-003 | Consolidation clusters API endpoint | Implement `GET /api/v1/artifacts/consolidation/clusters` in `skillmeat/api/routers/artifacts.py`. Query params: `min_score` (float, default 0.5), `limit` (int, default 20, max 100), `cursor` (str). Calls `SimilarityService.get_consolidation_clusters()`. Returns `SimilarityClusterDTO` list with cursor. Ownership enforced. | 200 with paginated cluster list; cursor pagination works across pages; integration tests cover happy path, empty result, cursor pagination. | 2 pts | `python-backend-engineer` | SA-P5-001 |
| SA-P5-004 | Consolidation skip action endpoint | Implement `POST /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore` and `DELETE /api/v1/artifacts/consolidation/pairs/{pair_id}/ignore` endpoints. Call `mark_pair_ignored` / `unmark_pair_ignored` respectively. | 200 on success; 404 on unknown pair; ownership enforced. | 1 pt | `python-backend-engineer` | SA-P5-002 |
| SA-P5-005 | useConsolidationClusters hook | Create `useConsolidationClusters(options?: { minScore?: number })` hook in `skillmeat/web/hooks/similarity.ts`. Uses React Query infinite query for cursor pagination. `staleTime: 30 * 1000` (30s — interactive freshness per data flow patterns). Provides `ignorePair(pairId)` and `unignorePair(pairId)` mutations that invalidate cluster query cache. | Hook returns paginated cluster data with `fetchNextPage`; ignore/unignore mutations update list immediately via optimistic update. | 1 pt | `frontend-developer` | SA-P5-003, SA-P5-004 |
| SA-P5-006 | Consolidation page route | Create `skillmeat/web/app/collection/consolidate/page.tsx`. Server component; includes `<ConsolidationClusterList>` as client component. Page title "Consolidate Collection". Handles empty state (no clusters found). | Route accessible at `/collection/consolidate`; server component renders correctly; empty state visible when no clusters. | 0.5 pt | `frontend-developer` | SA-P5-005 |
| SA-P5-007 | ConsolidationClusterList component | Create `skillmeat/web/components/consolidation/consolidation-cluster-list.tsx`. Renders a table of clusters: artifact count, type badge, highest similarity score (percentage), primary artifact name. Clicking a row opens `ConsolidationClusterDetail`. Load More button for cursor pagination. Shows ignored-pairs toggle (show/hide ignored). | Cluster table renders all required columns; clicking row opens detail; pagination works; ignored toggle hides/shows ignored pairs; accessible table with correct `aria` attributes. | 2 pts | `ui-engineer-enhanced` | SA-P5-005 |
| SA-P5-008 | ConsolidationClusterDetail component | Create `skillmeat/web/components/consolidation/consolidation-cluster-detail.tsx`. For a selected cluster with two artifacts: renders side-by-side comparison using existing `DiffViewer` component for content diff and metadata diff. Shows three action buttons: "Merge" (keep primary, apply changes from secondary), "Replace" (keep primary, discard secondary), "Skip" (mark pair as ignored). Each destructive action (Merge/Replace) shows a confirmation dialog. | All three actions available; confirmation dialog shown before Merge and Replace; DiffViewer renders content and metadata diffs; Skip marks pair ignored and removes from list. | 3 pts | `ui-engineer-enhanced` | SA-P5-007 |
| SA-P5-009 | Auto-snapshot gate for merge/replace | Before executing Merge or Replace action, call `VersionMergeService` auto-snapshot API. If snapshot fails, abort action and surface blocking error ("Snapshot failed — action aborted"). Never proceed with merge/replace without confirmed snapshot. Success: snapshot created → execute action → show success toast. | Snapshot called before every merge/replace; action aborted on snapshot failure with clear error; success creates snapshot then completes action; unit test for abort-on-snapshot-failure path. | 2 pts | `python-backend-engineer`, `backend-architect` | SA-P5-008 |
| SA-P5-010 | Un-ignore management UI | In `ConsolidationClusterList`, add a "Show ignored pairs" toggle. When toggled on, ignored pairs appear in the list with a visual indicator (e.g., strikethrough or gray badge). Each ignored pair row has an "Un-ignore" button that calls `unignorePair()` mutation, restoring it to the active list. | Toggle shows/hides ignored pairs; un-ignore button visible on ignored rows; un-ignore restores pair to active list; optimistic update reflects change immediately. | 1 pt | `ui-engineer-enhanced` | SA-P5-007 |
| SA-P5-011 | Collection page toolbar button | Add "Consolidate Collection" button to the Collection page toolbar (or relevant navigation area). Button links to `/collection/consolidate` route. | Button visible in collection toolbar; clicking navigates to consolidation page; button has descriptive `aria-label`. | 0.5 pt | `frontend-developer` | SA-P5-006 |
| SA-P5-012 | E2E test — consolidation merge | Playwright E2E test: navigate to `/collection/consolidate` → select a cluster with a known similar pair → click "Merge" → confirm dialog → verify confirmation toast shown → verify auto-snapshot was created (via API check) → verify secondary artifact is removed from collection. | E2E test passes; auto-snapshot verifiable via API; secondary artifact gone from collection after merge. | 1 pt | `frontend-developer` | SA-P5-009 |
| SA-P5-013 | Integration tests — consolidation API | pytest integration tests for: `GET /api/v1/artifacts/consolidation/clusters` (happy path, empty, cursor pagination), `POST /ignore` (mark ignored), `DELETE /ignore` (unmark). Use test DB with known-similar fixtures. | All integration tests pass; ignored pairs excluded from cluster list by default. | 1 pt | `python-backend-engineer` | SA-P5-003, SA-P5-004 |

**Phase 5 Story Points**: ~18 pts raw → PRD estimate: SA-010=3 pts, SA-011=3 pts, SA-012=5 pts, SA-013=2 pts = 13 pts + auto-snapshot gate and E2E = ~18 pts. Aligned to combined Phase 5 budget of 10 pts at task level; adjust estimates during sprint planning if needed.

> Implementation note: Phase 5 reuses `DiffViewer` from `skillmeat/web/components/entity/diff-viewer.tsx` and `VersionMergeService` from the existing Discovery tab. Do not reimplement — import and configure.

### Phase 5 Quality Gates

- [ ] `GET /api/v1/artifacts/consolidation/clusters` returns correct paginated clusters.
- [ ] Ignored pairs excluded from cluster list by default; toggle reveals them.
- [ ] Merge and Replace actions abort if auto-snapshot fails (never destructive without snapshot).
- [ ] Skip marks pair ignored; un-ignore restores to active list.
- [ ] Consolidation page accessible from Collection page toolbar.
- [ ] E2E merge test passes with auto-snapshot verification.
- [ ] Integration tests for cluster and ignore/unignore endpoints pass.
- [ ] WCAG 2.1 AA contrast on all cluster table and detail view elements.
- [ ] `task-completion-validator` sign-off.

---

## Phase 6: CLI Integration

### Overview

Phase 6 adds two Click commands to `skillmeat/cli.py`: `skillmeat similar <artifact>` and `skillmeat consolidate`. Both call `SimilarityService` directly (Python import, not HTTP) for performance. The consolidate command supports interactive (TTY) and non-interactive (`--non-interactive --output=json`) modes.

**Duration**: 1–2 days
**Dependencies**: Phase 1 `SimilarityService` available. Phase 5 clusters endpoint available for `consolidate` command cluster fetching.

### Parallelization Opportunities

- Phase 6 can run in parallel with all Phase 5 frontend work since it depends only on `SimilarityService` (Phase 1) and the consolidation cluster service method (SA-P5-001).
- Unit tests for CLI commands can be written in parallel with implementation.

### Task Table — Phase 6

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Dependencies |
|---|---|---|---|---|---|---|
| SA-P6-001 | `skillmeat similar` CLI command | Add `@cli.command()` `similar` to `skillmeat/cli.py`. Arguments: `artifact` (name or ID). Options: `--limit` (int, default 10), `--min-score` (float, default 0.3), `--source` (choice: collection/marketplace/all, default collection). Calls `SimilarityService.find_similar()` directly. Renders results as a Rich table with columns: Rank, Name, Type, Score %, Match Type. Handles empty results with a descriptive message. | Command exits 0; Rich table renders in TTY with correct columns; empty result prints informative message (not error); `--help` shows all options with descriptions; non-TTY output is clean (no Rich color codes in piped output). | 2 pts | `python-backend-engineer` | Phase 1 SA-P1-004 |
| SA-P6-002 | `skillmeat consolidate` — interactive wizard | Add `@cli.command()` `consolidate` to `skillmeat/cli.py`. Detects TTY. In TTY mode: fetches cluster list via `SimilarityService.get_consolidation_clusters()`; presents each cluster one by one using Rich Panel; prompts user (Merge / Replace / Skip / Quit) using Click `prompt()`; executes chosen action. For Merge/Replace: confirms auto-snapshot via `VersionMergeService` before proceeding; aborts if snapshot fails. Skip marks pair ignored. Quit exits loop cleanly. | TTY wizard presents all clusters; user can action each; auto-snapshot fires before Merge/Replace; snapshot failure aborts with error message; Quit exits cleanly; `--help` renders correctly. | 2 pts | `python-backend-engineer` | SA-P5-001, Phase 1 SA-P1-004 |
| SA-P6-003 | `skillmeat consolidate` — non-interactive mode | Add `--non-interactive` / `-n` flag to `consolidate` command. When set, outputs JSON report to stdout: `{ "clusters": [...], "total_count": N }` where each cluster includes artifact IDs, names, scores, and types. `--output=text` produces human-readable plain text instead. Non-TTY auto-detects and falls back to non-interactive mode with warning. | `--non-interactive` flag exits 0 with valid JSON on stdout; JSON validates against expected schema; `--output=text` produces plain text; auto-detect non-TTY triggers non-interactive with warning message on stderr. | 1 pt | `python-backend-engineer` | SA-P6-002 |
| SA-P6-004 | Unit tests — CLI commands | pytest unit tests for `similar` and `consolidate` commands using Click's `CliRunner`. Mock `SimilarityService`. Test cases: `similar` happy path (table output), empty result, invalid artifact name (404 equivalent). `consolidate` non-interactive JSON output, non-interactive text output, mock TTY wizard flow (one cycle). | All CLI unit tests pass; `CliRunner` invocations exit 0 on happy paths; error exits produce exit code 1 with message. | 1 pt | `python-backend-engineer` | SA-P6-001, SA-P6-002, SA-P6-003 |
| SA-P6-005 | Manual smoke test — help strings | Manual verification: `skillmeat similar --help` and `skillmeat consolidate --help` render correctly with all options documented. `skillmeat similar canvas-skill` produces output matching UI results within expected variance. | Both `--help` strings render all options with descriptions; output is visually aligned in Rich table format. | 0 pts (manual gate) | Orchestrator | SA-P6-001, SA-P6-002 |

**Phase 6 Story Points**: ~6 pts (aligns with PRD SA-014=2 pts, SA-015=3 pts + unit tests = ~6 pts). Aligned to Phase 6 budget.

### Phase 6 Quality Gates

- [ ] `skillmeat similar <artifact>` exits 0 and renders Rich table.
- [ ] `skillmeat similar --help` and `skillmeat consolidate --help` render all options.
- [ ] `skillmeat consolidate --non-interactive` exits 0 with valid JSON.
- [ ] Non-TTY auto-detected; falls back to non-interactive with stderr warning.
- [ ] Auto-snapshot fires before Merge/Replace in interactive wizard.
- [ ] Unit tests pass using Click's `CliRunner` with mocked `SimilarityService`.
- [ ] `task-completion-validator` sign-off.

---

## Key Files

| File | Role | Change Type |
|---|---|---|
| `skillmeat/core/similarity.py` | SimilarityService | Add `get_consolidation_clusters()` |
| `skillmeat/cache/repositories.py` | DuplicatePair repository | Add ignore/unignore methods |
| `skillmeat/api/routers/artifacts.py` | API router | Add clusters + ignore endpoints |
| `skillmeat/api/schemas/artifacts.py` | Pydantic schemas | Add `SimilarityClusterDTO` |
| `skillmeat/api/openapi.json` | OpenAPI contract | Update with new endpoints |
| `skillmeat/web/hooks/similarity.ts` | React Query hooks | Add `useConsolidationClusters()` |
| `skillmeat/web/app/collection/consolidate/page.tsx` | Page route | New file |
| `skillmeat/web/components/consolidation/consolidation-cluster-list.tsx` | Cluster list | New file |
| `skillmeat/web/components/consolidation/consolidation-cluster-detail.tsx` | Cluster detail + actions | New file |
| `skillmeat/cli.py` | CLI entry point | Add `similar` and `consolidate` commands |
| `tests/test_consolidation_api.py` | Integration tests | New file |
| `tests/test_cli_similar.py` | CLI unit tests | New file |

---

## Risk Notes for This Phase

**Auto-snapshot failure handling (Critical)**: The auto-snapshot gate (SA-P5-009) is the highest-risk task in this phase. `VersionMergeService` must be callable from the consolidation action handler and must return a confirmation before proceeding. If the existing `VersionMergeService` API does not expose a synchronous snapshot-then-confirm flow, this task requires a design spike before implementation.

**CLI interactive wizard in CI**: Click's `CliRunner` simulates TTY for unit tests, but the interactive `prompt()` calls must be mockable. Ensure all user prompts use `click.prompt()` with `default` values for test-mode compatibility.

**Cluster grouping performance**: `SimilarityService.get_consolidation_clusters()` calls `find_similar()` for each artifact and groups results. For large collections this is O(N^2). Implement with a keyword-score pre-filter (top-K candidates only) to keep runtime within 5 s for 500 artifacts.

---

**Back to parent plan**: [similar-artifacts-v1.md](../similar-artifacts-v1.md)
**Previous phase file**: [phase-3-4-marketplace.md](./phase-3-4-marketplace.md)
