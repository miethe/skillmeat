# Sync/Diff Modal Standardization - Context

## PRD Reference

`docs/project_plans/PRDs/refactors/sync-diff-modal-standardization-v1.md`

## Implementation Plan

`docs/project_plans/implementation_plans/refactors/sync-diff-modal-standardization-v1.md`

## Investigation Report

`docs/project_plans/reports/sync-diff-modal-inconsistency-analysis-2026-02-04.md`

## Problem Summary

Four root causes make sync/diff workflows fail on `/manage`:
1. Frontend `hasValidUpstreamSource()` checks URL, backend checks `origin` enum -> 400 errors
2. `/manage` modal passes no `projectPath` -> collection-vs-project diffs always disabled
3. Two 1000+ line modal components diverge in behavior
4. Mutations stubbed with "coming soon" toasts

## Key Architecture Decisions

- **No backend changes needed** - all API endpoints exist
- **Hybrid auto-detection** for project selector: single deployment auto-selects; multiple shows picker
- **BaseArtifactModal** extracts shared patterns; full unification deferred to Q3 2026
- **Artifact type only** in new code; Entity is deprecated alias
- **Cache invalidation** must follow `.claude/context/key-context/data-flow-patterns.md`

## Critical File Map

| File | Why It Matters |
|------|---------------|
| `web/components/sync-status/sync-status-tab.tsx:98-104` | hasValidUpstreamSource() - THE bug |
| `web/components/sync-status/sync-status-tab.tsx:238-239` | upstream-diff query enablement |
| `web/components/sync-status/sync-status-tab.tsx:254-256` | project-diff query enablement |
| `web/components/sync-status/sync-status-tab.tsx:357-369` | keepLocalMutation (stub) |
| `web/components/sync-status/sync-status-tab.tsx:403-406` | batch actions (stub) |
| `web/components/sync-status/sync-status-tab.tsx:483,519` | push-to-collection (stub) |
| `web/components/manage/artifact-operations-modal.tsx:435-441` | Duplicate validation |
| `web/components/manage/artifact-operations-modal.tsx:1185-1191` | Missing projectPath |
| `web/components/entity/unified-entity-modal.tsx:619-622` | selectedProjectForDiff pattern |
| `web/components/entity/unified-entity-modal.tsx:2111-2116` | Working SyncStatusTab props |
| `web/components/entity/project-selector-for-diff.tsx` | Reusable project picker |

## Phase Dependencies

```
Phase 1 (validation) -> Phase 2 (project context) -> Phase 3 (foundation) -> Phase 5 (testing)
                                                  \-> Phase 4 (mutations) -> Phase 5 (testing)
```

TASK-3.1 (analysis) can start during Phase 1 as early work.

## Related PRDs and Plans

- `docs/project_plans/PRDs/enhancements/artifact-flow-modal-redesign.md` - 3-panel sync design spec
- `docs/project_plans/implementation_plans/refactors/modal-architecture-improvements-r2r3.md` - Wrapper components (ProjectArtifactModal done)
- `.claude/guides/entity-to-artifact-migration.md` - Type migration guide

## Session Notes

_(append notes from implementation sessions here)_
