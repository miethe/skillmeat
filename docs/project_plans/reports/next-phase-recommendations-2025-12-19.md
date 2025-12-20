# Next Phase Recommendations Report (2025-12-19)

## Scope

- Reviewed the codebase and current implementation status.
- Focused on documentation cleanup materials in `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1`.
- Cross-checked key areas where docs and code disagree.

## Findings

### 1. Documentation cleanup plan is partially stale

- The delete lists in the cleanup plan mostly reference files that already do not exist.
  - Root-level delete targets: 0/10 remaining.
  - Web frontend delete targets: 0/9 remaining.
  - Web test delete targets: 0/7 remaining.
- Two review items still exist and need a disposition decision:
  - `skillmeat/api/tests/README_PERFORMANCE.md`
  - `skillmeat/cache/WATCHER.md`
- The planned move item does not exist:
  - `docs/worknotes/2025-11-26_nextjs-build-cache-fix.md`
- The nine "docs to review" entries do exist and remain untriaged:
  - `docs/project_plans/bugs/bugs-11-25.md`
  - `docs/project_plans/bugs/bugs-11-29.md`
  - `docs/project_plans/bugs/bugs-12-02.md`
  - `docs/project_plans/ideas/enhancements-11-25.md`
  - `docs/project_plans/ideas/enhancements-11-30.md`
  - `docs/project_plans/ideas/enhancements-12-03.md`
  - `docs/project_plans/ideas/enhancements-12-04.md`
  - `docs/project_plans/ideas/enhancements-12-12-Collections-Nav.md`
  - `docs/project_plans/ideas/agent-context-entities-v1.md`

### 2. Implementation tracking docs are out of sync with the canonical source

- `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/IMPLEMENTATION_TRACKING_SUMMARY.md` is the canonical status source.
- `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/IMPLEMENTATION_QUICK_REFERENCE.md` and `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/EXPLORATION_REPORT.md` still describe Collections Navigation v1 as in progress, and Agent Context Entities v1 as pending.
- These should be updated to mirror the tracking summary or explicitly labeled as historical context.

### 3. Collections API consolidation appears implemented in code

- The web API client now targets `/user-collections` for CRUD and artifacts:
  - `skillmeat/web/lib/api/collections.ts`
- Collection hooks are implemented and no longer stubbed:
  - `skillmeat/web/hooks/use-collections.ts`
- Remaining gap is copy/move which still throws explicit errors:
  - `skillmeat/web/lib/api/collections.ts`

### 4. UI history and sync flows still contain placeholders

- Entity history is generated from mock data rather than an API-backed event log:
  - `skillmeat/web/components/entity/unified-entity-modal.tsx`
- Sync Status still lacks a source-vs-project diff and some actions are no-ops:
  - `skillmeat/web/components/sync-status/sync-status-tab.tsx`

### 5. Tags refactor appears complete end-to-end

- Tags API and service exist (`/api/v1/tags` plus artifact tag endpoints).
- Web UI supports tag creation, assignment, and filtering.
  - `skillmeat/api/routers/tags.py`
  - `skillmeat/web/lib/api/tags.ts`
  - `skillmeat/web/components/entity/entity-form.tsx`
  - `skillmeat/web/components/ui/tag-filter-popover.tsx`

### 6. Context Entities API is still stubbed despite tracking summary completion

- The context entities router returns 501 for core CRUD operations and content access.
  - `skillmeat/api/routers/context_entities.py`

### 7. Phase 6 for Discovery Import Enhancement remains open

- Documentation indicates Phase 6 (Monitoring, Optimization, Release) is pending.
  - `docs/project_plans/implementation_plans/enhancements/discovery-import-enhancement-v1.md`

## Recommendations: Next Phase of Enhancements

### Priority 0: Documentation truthing and cleanup (1-2 weeks)

- Update `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/documentation-cleanup-plan-v1.md` to reflect current repository state (remove already-deleted targets, update the move item, focus on remaining review items).
- Treat `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/IMPLEMENTATION_TRACKING_SUMMARY.md` as canonical, then reconcile or retire the conflicting status docs:
  - `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/IMPLEMENTATION_QUICK_REFERENCE.md`
  - `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/EXPLORATION_REPORT.md`
  - `docs/project_plans/implementation_plans/refactors/documentation-cleanup-plan-v1/IMPLEMENTATION_TRACKING_SUMMARY.md`
- Decide where `skillmeat/cache/WATCHER.md` and `skillmeat/api/tests/README_PERFORMANCE.md` belong (move to `docs/cache` or `docs/testing`, or delete if not needed).
- Triage the nine "docs to review" and consolidate into a single backlog or archive file.
- Update release notes to include tags refactor completion and current status of context entities (per tracking summary and code validation).

### Priority 1: Close remaining consolidation gaps (2-3 weeks)

- Implement or remove collection copy/move to avoid explicit runtime errors:
  - `skillmeat/web/lib/api/collections.ts`
- Replace mock entity history with a real event stream (deploy, sync, rollback). This will support the history and audit UI.
  - `skillmeat/web/components/entity/unified-entity-modal.tsx`
- Finish sync-status functionality (source-vs-project diff, batch actions, push-to-collection or remove button).
  - `skillmeat/web/components/sync-status/sync-status-tab.tsx`
- Confirm context entities backend implementation or update tracking summary if completion was premature:
  - `skillmeat/api/routers/context_entities.py`

### Priority 2: Discovery UX completion (3-4 weeks)

- Complete Phase 6 of Discovery Import Enhancement (monitoring, docs, release readiness).
  - `docs/project_plans/implementation_plans/enhancements/discovery-import-enhancement-v1.md`

### Priority 3: Optional hardening (parallel, as bandwidth allows)

- Review TODOs that block multi-user or marketplace workflows (auth stubs, submission tracking). Focus on productionizing marketplaces and context sync only if those features are part of the near-term roadmap.

## Suggested Next-Phase Theme

"Consolidation and Trust" - align documentation with reality, finish outstanding UX gaps, and solidify artifact sync and tagging so the app feels coherent and dependable before pushing broader platform features.
