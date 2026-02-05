# Unified Sync Workflow Plan Review

**Date**: 2026-02-05
**Status**: Review Complete
**Scope**: docs/project_plans/implementation_plans/features/unified-sync-workflow-v1.md

## Executive Summary

The plan is directionally correct but incomplete for the stated goal: a conflict-aware, DiffViewer‑first sync workflow across **all** directions (Source → Collection, Project → Collection, Collection → Project, and Source → Project comparisons). Several critical assumptions are currently false (no backend changes required; Merge available for deploy), and some current‑state notes are outdated. This report documents the gaps and provides a concrete set of plan revisions, including backend changes, updated merge gating logic, and test strategy updates.

## Confirmed Requirements (from stakeholder answers)

1. **Real merge workflow in Sync Status** for every direction. Every flow must offer **Overwrite** and **Merge**, but **Merge is enabled only when the target has changes not already present in the source version history**.
2. **File‑level handling** when diffs exist, using the **DiffViewer**.
3. **Dialogs may be rebuilt** to embed DiffViewer (especially for merge selection and preview), with refactors allowed across the Sync Status tab and related flows.
4. **Backend changes are acceptable** to support the above.

## Findings: Plan Accuracy Gaps

1. **Merge on deploy is not currently possible**.
   - The plan routes “Merge” to the existing SyncDialog, but SyncDialog only handles upstream→collection sync. Deploy only supports `overwrite` and does not merge collection→project.
   - Result: The “Merge” button for deploy would be non‑functional without backend work.

2. **“No backend changes required” is incorrect**.
   - “Source vs Project” diff can’t be accurately rendered from existing `/diff` + `/upstream-diff` responses, because there’s no server-side comparison between upstream source and deployed project.
   - If you need file‑level diffs in DiffViewer for Source vs Project, a new backend endpoint or diff pipeline is required.

3. **Push flow “UI incomplete” is stale**.
   - Sync Status already has a Project → Collection action and confirmation dialog. The plan assumes the button is missing and must be added.

4. **Pull flow isn’t upgraded despite stated goal**.
   - The plan says all sync operations integrate DiffViewer and conflict-aware confirmation, but only deploy/push are scoped for dialog upgrades.

5. **usePrePushCheck logic is directionally wrong**.
   - It’s described as “upstream changes not in project.” For project → collection, the pre-check must compare **collection vs project** and detect **collection‑side** changes.

6. **Estimates don’t reconcile**.
   - The plan says “13 story points,” but phase totals add to 23, and the timeline summary is 10–14 days. These should be reconciled or split into MVP vs extended scope.

## Recommendations: Plan Changes

### A) Add Backend Work (Required for Merge + Source vs Project)

1. **Downstream merge support (collection → project)**
   - Add a backend route to allow merge strategy when deploying to a project.
   - Option A: Extend `/artifacts/{id}/deploy` to accept `strategy` and `merge` behavior (with conflict reporting).
   - Option B: Add a new endpoint (e.g., `/artifacts/{id}/sync-to-project`) backed by the merge engine with strategies `overwrite | merge`.
   - Ensure it returns a response compatible with DiffViewer + conflict resolution steps.

2. **Source vs Project diff**
   - Add a dedicated diff endpoint: `/artifacts/{id}/source-project-diff?project_path=...`.
   - Implementation should fetch upstream source and compare directly against the project deployment for accurate DiffViewer rendering.

3. **Target-side change detection helper**
   - If merge enablement must be gated by “target has changes not in source,” return a derived flag or per-file directionality in diff responses.
   - Alternatively, compute merge‑eligibility in the UI by interpreting `FileDiff.status` against the selected source/target (see gating rules below).

### B) Unify Conflict‑Aware Dialogs Across All Directions

Replace the existing confirmation alerts with a **single DiffViewer‑based dialog** that covers all directions:

- **Pull Source → Collection**: use `/upstream-diff` to show DiffViewer before sync. Provide Overwrite + Merge (merge is enabled if collection contains changes not in source).
- **Push Project → Collection**: use `/diff` for project vs collection. Provide Overwrite + Merge (merge enabled if collection has changes not in project).
- **Deploy Collection → Project**: use `/diff` for collection vs project. Provide Overwrite + Merge (merge enabled if project has local changes).

### C) Merge Enablement Rules (UI Gating)

Use `FileDiff.status` with source/target semantics to enable Merge only when the **target** has changes not in the source:

- **Collection → Project (Deploy)**
  - Target = Project. Enable Merge if any file is **added** or **modified** in the project side.
- **Project → Collection (Push)**
  - Target = Collection. Enable Merge if any file is **deleted** or **modified** relative to project.
- **Source → Collection (Pull)**
  - Target = Collection. Enable Merge if any file is **deleted** or **modified** relative to source.

If the backend can emit explicit “target_has_changes” flags, prefer that over client inference.

### D) DiffViewer as the Primary Conflict UI

- Use DiffViewer in confirmation dialogs for all directions.
- For merge selection, leverage DiffViewer’s resolution actions (or extend it) to operate **file‑by‑file** rather than single global selection.
- If the existing MergeWorkflow is used, it must be extended to support **downstream merge** and updated to drive DiffViewer at file granularity.

### E) Update Plan Phases (Suggested Restructure)

1. **Phase 0 – Plan Alignment (0.5–1 day)**
   - Fix the current-state analysis and estimates.
   - Add backend tasks explicitly (downstream merge, source‑project diff).

2. **Phase 1 – Backend Enablement (2–4 days)**
   - Implement merge-capable deploy endpoint.
   - Implement source‑project diff endpoint.
   - Add any new response fields needed for merge gating.

3. **Phase 2 – Unified Conflict Dialog + DiffViewer (3–4 days)**
   - Replace SyncStatus confirmation dialogs with a unified DiffViewer dialog.
   - Implement merge gating logic and resolution UI.

4. **Phase 3 – Merge Workflow Integration (2–3 days)**
   - Extend MergeWorkflow for downstream directions or implement file‑level merge selection in the new dialog.

5. **Phase 4 – Tests, A11y, Performance (2–3 days)**
   - Add unit tests for hooks/dialogs, a11y checks, and Playwright flows.

### F) Testing and Quality Gates

- Unit tests should live under `skillmeat/web/__tests__/components` and `skillmeat/web/__tests__/hooks`.
- E2E tests should be Playwright `*.spec.ts` under `skillmeat/web/tests/` or `skillmeat/web/tests/e2e/`.
- Add an a11y test for new dialogs (pattern exists in `__tests__/a11y`).
- Perf gate should be based on DiffViewer render time under large diffs, with specific thresholds for >1000 lines.

## Plan Text Updates Recommended

1. **Replace** “No backend changes required” with a backend task list.
2. **Add** Pull flow dialog upgrade to Phase 1/2 scope.
3. **Fix** SyncDialog usage for merge: it is upstream-only; new merge workflow is needed for deploy.
4. **Fix** usePrePushCheck directionality and diff source.
5. **Reconcile** story points (13 vs 23) and timeline (MVP vs full scope).

## Proposed New/Updated Tasks (Insertions)

- **SYNC‑00X**: Implement merge-capable deploy endpoint (backend)
- **SYNC‑00Y**: Implement source‑project diff endpoint (backend)
- **SYNC‑00Z**: Add target-change flags to diff responses or derive merge gating rules in UI
- **SYNC‑01X**: Conflict-aware Pull dialog using DiffViewer + merge gating
- **SYNC‑01Y**: Unify confirmation dialogs into a single component with direction config
- **SYNC‑01Z**: Extend MergeWorkflow (or new file‑level merge UI) to handle downstream merge

## Risks if Not Addressed

- Merge buttons will appear but be non-functional for deploy.
- Source vs Project comparison will remain inaccurate or summary-only, undermining DiffViewer requirements.
- Users will experience inconsistent flows across directions, contradicting the “unified workflow” goal.

## Recommendation Summary

Proceed only after updating the plan to include backend merge support and a source‑project diff endpoint, then move the UI work to a unified DiffViewer-driven dialog for **all** directions. Merge gating rules must be explicit and based on target‑side changes. This aligns the plan with the confirmed requirements and makes the conflict‑aware workflow feasible end‑to‑end.
